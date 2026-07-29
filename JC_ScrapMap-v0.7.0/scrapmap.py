"""JC ScrapMap Prototype 0A.

Reads Scrap Mechanic save metadata in SQLite read-only mode, writes normalized
local state, and optionally serves the offline browser interface on localhost.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import struct
import sys
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


APP_VERSION = "0.7.0"
DEFAULT_PORT = 8765
PROJECT_DIR = Path(__file__).resolve().parent
WEB_DIR = PROJECT_DIR / "web"
GENERATED_DIR = PROJECT_DIR / "generated"
MAPPER_DATA_DIR = PROJECT_DIR / "mapper-data"
IMPORT_DIR = PROJECT_DIR / "imports"
CELL_SIZE_METERS = 64
OVERWORLD_BOUNDS = {"xMin": -64, "xMax": 63, "yMin": -48, "yMax": 47}
GLOBAL_STORAGE_UID = bytes.fromhex("2C3699B2FD9C503EA405CF73434E2E88")
PLAYER_DATA_UID = bytes.fromhex("67CE7FE2F7564898B8F076080146A358")
PLAYER_DATA_OFFSET = 31
BEACON_STORAGE_CHANNEL = 35
BEACON_COLORS = [
    "#4F6CFF", "#AF7DFF", "#00FFFF", "#90FF78",
    "#FFD046", "#FFFFC0", "#FF6619", "#FF3737",
]
BEACON_ICON_NAMES = [
    "Arrow down", "House", "Exclamation", "Question",
    "Car", "Workshop", "Boat", "Storage",
    "Tree", "Crash", "Boat on water", "Campfire",
    "Wrench", "Flower", "Woc", "Farmer",
    "Scrapbot", "Bearing", "Burger", "Cogwheel",
    "Mask", "Heart", "Water drop", "X",
]


def global_storage_key(channel: int) -> bytes:
    """Return the serialized Lua integer key used by sm.storage channels."""
    if not 0 <= channel <= 255:
        raise ValueError("Only single-byte storage channels are supported.")
    return b"LUA\x00\x00\x00\x01\x08" + bytes((channel,))


class LuaObjectReader:
    """Decode the documented Lua-object subset used by Beacon storage."""

    def __init__(self, data: bytes):
        self.data = data
        self.bit = 0

    def read_bits(self, count: int) -> int:
        if count < 0 or self.bit + count > len(self.data) * 8:
            raise ValueError("Unexpected end of Lua-object data.")
        value = 0
        for _ in range(count):
            byte = self.data[self.bit // 8]
            value = (value << 1) | ((byte >> (7 - self.bit % 8)) & 1)
            self.bit += 1
        return value

    def read_signed(self, count: int) -> int:
        value = self.read_bits(count)
        return value - (1 << count) if value & (1 << (count - 1)) else value

    def align(self) -> None:
        self.bit = (self.bit + 7) // 8 * 8

    def read_bytes(self, count: int) -> bytes:
        self.align()
        start = self.bit // 8
        end = start + count
        if end > len(self.data):
            raise ValueError("Unexpected end of Lua-object byte data.")
        self.bit = end * 8
        return self.data[start:end]

    def read_value(self):
        value_type = self.read_bits(8)
        if value_type == 1:
            return None
        if value_type == 2:
            return bool(self.read_bits(1))
        if value_type == 3:
            return struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0]
        if value_type == 4:
            size = self.read_bits(32)
            if size > 1_000_000:
                raise ValueError("Lua-object string is unreasonably large.")
            return self.read_bytes(size).decode("utf-8")
        if value_type == 5:
            count = self.read_bits(32)
            if count > 100_000:
                raise ValueError("Lua-object table is unreasonably large.")
            is_array = bool(self.read_bits(1))
            if is_array:
                offset = self.read_bits(32)
                return {
                    offset + index: self.read_value()
                    for index in range(count)
                }
            result = {}
            for _ in range(count):
                key = self.read_value()
                result[key] = self.read_value()
            return result
        if value_type == 6:
            return self.read_signed(32)
        if value_type == 7:
            return self.read_signed(16)
        if value_type == 8:
            return self.read_signed(8)
        if value_type == 100:
            userdata_type = self.read_bits(32)
            if userdata_type == 10003:
                values = [
                    struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0]
                    for _ in range(3)
                ]
                return {"type": "vec3", "x": values[0], "y": values[1], "z": values[2]}
            if userdata_type == 10021:
                return {"type": "shape", "id": self.read_bits(32)}
            if userdata_type == 10027:
                return {"type": "world", "id": self.read_bits(32)}
            raise ValueError(f"Unsupported Lua userdata type {userdata_type}.")
        raise ValueError(f"Unsupported Lua-object value type {value_type}.")


def decompress_lz4_block(data: bytes) -> bytes:
    """Decompress a raw LZ4 block without requiring its output size."""
    source = 0
    output = bytearray()
    while source < len(data):
        token = data[source]
        source += 1
        literal_length = token >> 4
        if literal_length == 15:
            while True:
                if source >= len(data):
                    raise ValueError("Truncated LZ4 literal length.")
                extension = data[source]
                source += 1
                literal_length += extension
                if extension != 255:
                    break
        if source + literal_length > len(data):
            raise ValueError("Truncated LZ4 literals.")
        output.extend(data[source:source + literal_length])
        source += literal_length
        if source == len(data):
            break
        if source + 2 > len(data):
            raise ValueError("Truncated LZ4 match offset.")
        offset = int.from_bytes(data[source:source + 2], "little")
        source += 2
        if offset <= 0 or offset > len(output):
            raise ValueError("Invalid LZ4 match offset.")
        match_length = (token & 0x0F) + 4
        if (token & 0x0F) == 15:
            while True:
                if source >= len(data):
                    raise ValueError("Truncated LZ4 match length.")
                extension = data[source]
                source += 1
                match_length += extension
                if extension != 255:
                    break
        for _ in range(match_length):
            output.append(output[-offset])
    return bytes(output)


def decode_lua_object(blob: bytes):
    """Decode the Lua object stored inside a ScriptData BlobData record."""
    if len(blob) < 25:
        raise ValueError("ScriptData blob is too short.")
    key_size = int.from_bytes(blob[16:18], "big")
    header_size = 16 + 2 + key_size + 2 + 1 + 4
    if header_size > len(blob):
        raise ValueError("ScriptData BlobData header is truncated.")
    compressed_size = int.from_bytes(blob[header_size - 4:header_size], "big")
    compressed = blob[header_size:header_size + compressed_size]
    if len(compressed) != compressed_size:
        raise ValueError("ScriptData compressed payload is truncated.")
    data = decompress_lz4_block(compressed)
    if not data.startswith(b"LUA\x00\x00\x00\x01"):
        raise ValueError("Lua-object header was not found.")
    reader = LuaObjectReader(data[7:])
    return reader.read_value()


def default_game_path() -> Path:
    return Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / (
        r"Steam\steamapps\common\Scrap Mechanic"
    )


def default_user_root() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    return appdata / "Axolot Games" / "Scrap Mechanic" / "User"


def discover_user_directories(user_root: Path) -> list[Path]:
    if user_root.name.startswith("User_") and user_root.is_dir():
        return [user_root]
    if not user_root.is_dir():
        return []
    return sorted(
        (entry for entry in user_root.iterdir() if entry.is_dir() and entry.name.startswith("User_")),
        key=lambda entry: entry.name.casefold(),
    )


def is_backup_name(path: Path) -> bool:
    lower = path.name.casefold()
    return any(token in lower for token in ("copia", ".bak", "backup"))


def discover_saves(user_dirs: list[Path]) -> list[Path]:
    saves: list[Path] = []
    for user_dir in user_dirs:
        survival_dir = user_dir / "Save" / "Survival"
        if not survival_dir.is_dir():
            continue
        saves.extend(
            path
            for path in survival_dir.glob("*.db")
            if path.is_file() and not is_backup_name(path)
        )
    return sorted(saves, key=lambda path: path.stat().st_mtime, reverse=True)


def select_save(saves: list[Path], requested: str | None) -> Path:
    if requested:
        candidate = Path(requested).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Selected save does not exist: {candidate}")
        if candidate.suffix.casefold() != ".db" or is_backup_name(candidate):
            raise ValueError(f"Selected file is not an eligible Survival save: {candidate}")
        return candidate
    if not saves:
        raise FileNotFoundError("No Survival .db saves were found.")
    return saves[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_owner_name(path: Path) -> str:
    for parent in path.parents:
        if parent.name.startswith("User_"):
            return parent.name
    return "unknown-user"


def read_save_identity(path: Path) -> dict:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        row = connection.execute("SELECT seed, uniqueIds FROM Game").fetchone()
        if row is None:
            raise ValueError(f"Save has no Game metadata row: {path}")
        seed, unique_ids = row
    finally:
        connection.close()

    identity_source = b"\0".join(
        (
            save_owner_name(path).encode("utf-8"),
            str(seed).encode("ascii"),
            bytes(unique_ids or b""),
        )
    )
    return {
        "id": hashlib.sha256(identity_source).hexdigest()[:20],
        "seed": seed,
        "owner": save_owner_name(path),
    }


def inspect_save_read_only(path: Path) -> dict:
    before = path.stat()
    before_hash = sha256_file(path)
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        game = connection.execute(
            """
            SELECT savegameversion, flags, seed, gametick,
                   length(mods), length(uniqueIds), uniqueIds
            FROM Game
            """
        ).fetchone()
        if game is None:
            raise ValueError("The selected database has no Game metadata row.")

        world_ids: set[int] = set()
        for table, column in (
            ("GenericData", "worldId"),
            ("Harvestable", "worldId"),
            ("RigidBody", "worldId"),
            ("ScriptData", "worldId"),
            ("ScriptableObject", "worldId"),
            ("Unit", "worldId"),
        ):
            try:
                rows = connection.execute(
                    f'SELECT DISTINCT "{column}" FROM "{table}" ORDER BY "{column}"'
                )
                for row in rows:
                    if row[0] is None:
                        continue
                    try:
                        world_ids.add(int(row[0]))
                    except (TypeError, ValueError):
                        # Older or partially migrated saves may contain a
                        # textual column label as a data row.
                        continue
            except sqlite3.OperationalError:
                continue

        row_counts = {}
        for table in ("Harvestable", "RigidBody", "ScriptData", "Unit", "Portal"):
            try:
                row_counts[table] = connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
            except sqlite3.OperationalError:
                row_counts[table] = None
    finally:
        connection.close()

    after = path.stat()
    after_hash = sha256_file(path)
    unchanged = (
        before.st_size == after.st_size
        and before.st_mtime_ns == after.st_mtime_ns
        and before_hash == after_hash
    )
    if not unchanged:
        raise RuntimeError("Save integrity check failed: the selected save changed during inspection.")

    identity = read_save_identity(path)
    return {
        "identity": identity["id"],
        "owner": identity["owner"],
        "filename": path.name,
        "path": str(path),
        "sizeBytes": before.st_size,
        "modifiedUtc": datetime.fromtimestamp(
            before.st_mtime, tz=timezone.utc
        ).isoformat(),
        "sha256": before_hash,
        "readOnlyVerified": True,
        "savegameVersion": game[0],
        "flags": game[1],
        "seed": game[2],
        "gameTick": game[3],
        "modsBlobBytes": game[4],
        "uniqueIdsBlobBytes": game[5],
        "worldIds": sorted(world_ids),
        "rowCounts": row_counts,
    }


def read_saved_player_position(path: Path) -> dict:
    """Read the persisted local-player position from Scrap Mechanic PlayerData."""
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        row = connection.execute(
            """
            SELECT data
            FROM GenericData
            WHERE uid = ? AND worldId = 65534
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (PLAYER_DATA_UID,),
        ).fetchone()
    finally:
        connection.close()

    modified_utc = datetime.fromtimestamp(
        path.stat().st_mtime, tz=timezone.utc
    ).isoformat()
    unavailable = {
        "status": "unavailable",
        "savedUtc": modified_utc,
        "player": None,
    }
    if row is None:
        return {
            **unavailable,
            "message": "Last saved player position is not present in this save.",
        }

    data = bytes(row[0] or b"")
    required_length = PLAYER_DATA_OFFSET + struct.calcsize(">Hfff")
    if len(data) < required_length or data[:16] != PLAYER_DATA_UID:
        return {
            **unavailable,
            "message": "The saved player-position record has an unsupported format.",
        }

    world_id, z, y, x = struct.unpack_from(">Hfff", data, PLAYER_DATA_OFFSET)
    coordinates = (x, y, z)
    if (
        world_id <= 0
        or world_id >= 65534
        or not all(
            math.isfinite(value) and abs(value) < 10_000_000
            for value in coordinates
        )
    ):
        return {
            **unavailable,
            "message": "The saved player-position record did not pass validation.",
        }

    return {
        "status": "available",
        "message": "Showing the last position written to the save; it is not live.",
        "savedUtc": modified_utc,
        "player": {
            "worldId": world_id,
            "x": x,
            "y": y,
            "z": z,
            "cellX": math.floor(x / CELL_SIZE_METERS),
            "cellY": math.floor(y / CELL_SIZE_METERS),
        },
    }


def read_saved_beacons(path: Path) -> dict:
    """Read physical Beacon positions and icon settings from storage channel 35."""
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        row = connection.execute(
            """
            SELECT data FROM ScriptData
            WHERE uid = ? AND key = ?
            LIMIT 1
            """,
            (GLOBAL_STORAGE_UID, global_storage_key(BEACON_STORAGE_CHANNEL)),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return {
            "status": "unavailable",
            "message": "Physical Beacon storage is not present in this save.",
            "beacons": [],
            "overworldCount": 0,
            "otherWorldCount": 0,
        }

    try:
        saved = decode_lua_object(bytes(row[0] or b""))
        raw_beacons = saved.get("beacons", {}) if isinstance(saved, dict) else {}
        if not isinstance(raw_beacons, dict):
            raise ValueError("Beacon registry is not a table.")
        beacons = []
        for registry_id, beacon in raw_beacons.items():
            if not isinstance(beacon, dict):
                raise ValueError("Beacon entry is not a table.")
            position = beacon.get("position")
            shape = beacon.get("shape")
            world = beacon.get("world")
            icon_data = beacon.get("iconData")
            if not all(isinstance(item, dict) for item in (position, shape, world, icon_data)):
                raise ValueError("Beacon entry is missing required fields.")
            coordinates = [position.get(axis) for axis in ("x", "y", "z")]
            if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in coordinates):
                raise ValueError("Beacon position is invalid.")
            shape_id = int(shape.get("id"))
            world_id = int(world.get("id"))
            icon_index = int(icon_data.get("iconIndex"))
            color_index = int(icon_data.get("colorIndex"))
            if str(shape_id) != str(registry_id):
                raise ValueError("Beacon registry and shape IDs do not agree.")
            if not 0 <= icon_index < len(BEACON_ICON_NAMES):
                raise ValueError("Beacon icon index is outside the supported range.")
            if not 1 <= color_index <= len(BEACON_COLORS):
                raise ValueError("Beacon color index is outside the supported range.")
            x, y, z = (float(value) for value in coordinates)
            beacons.append(
                {
                    "id": shape_id,
                    "worldId": world_id,
                    "x": x,
                    "y": y,
                    "z": z,
                    "cellX": math.floor(x / CELL_SIZE_METERS),
                    "cellY": math.floor(y / CELL_SIZE_METERS),
                    "iconIndex": icon_index,
                    "iconName": BEACON_ICON_NAMES[icon_index],
                    "colorIndex": color_index,
                    "color": BEACON_COLORS[color_index - 1],
                }
            )
        beacons.sort(key=lambda item: item["id"])
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as error:
        return {
            "status": "unavailable",
            "message": f"Physical Beacon storage has an unsupported format: {error}",
            "beacons": [],
            "overworldCount": 0,
            "otherWorldCount": 0,
        }

    overworld_count = sum(item["worldId"] == 1 for item in beacons)
    return {
        "status": "available",
        "message": (
            f"Loaded {len(beacons)} saved physical Beacons "
            f"({overworld_count} in the overworld)."
        ),
        "beacons": beacons,
        "overworldCount": overworld_count,
        "otherWorldCount": len(beacons) - overworld_count,
    }


def inspect_discovery_evidence(path: Path) -> dict[str, dict]:
    """Extract conservative POI evidence without decoding proprietary blobs."""
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        quest_manager_rows = connection.execute(
            """
            SELECT data FROM ScriptData
            WHERE instr(data, CAST('completedQuests' AS BLOB)) > 0
            """
        ).fetchall()
        completed_quest_data = b"".join(bytes(row[0] or b"") for row in quest_manager_rows)

        def has_script_token(token: bytes) -> bool:
            row = connection.execute(
                "SELECT 1 FROM ScriptData WHERE instr(data, ?) > 0 LIMIT 1",
                (token,),
            ).fetchone()
            return row is not None

        elevator_row = connection.execute(
            "SELECT data FROM ScriptData WHERE uid = ? AND key = ? LIMIT 1",
            (GLOBAL_STORAGE_UID, global_storage_key(52)),
        ).fetchone()
        elevator_data = bytes(elevator_row[0] or b"") if elevator_row else b""
        # The blob serializer stores the final repeated character through its
        # compact bit stream, so the stable visible prefix ends at "wochous".
        has_woc_house_quest = has_script_token(b"quest_build_wochous")
        has_resource_car_quest = has_script_token(b"quest_build_first_car")
    finally:
        connection.close()

    return {
        "POI_MECHANICSTATION_QUEST_MEDIUM": {
            "status": "discovered" if b"mechanicstation" in completed_quest_data else "unknown",
            "scope": "world",
            "source": "QuestManager completedQuests",
            "reason": (
                "The persisted quest manager records the mechanic-station "
                "quest chain as completed."
            ),
        },
        "POI_BUILDERQUEST_WOCHOUSE": {
            "status": "discovered" if has_woc_house_quest else "unknown",
            "scope": "world",
            "source": "Persisted builder-quest object",
            "reason": (
                "A persisted Woc-house builder quest object proves that this "
                "quest location was encountered."
            ),
        },
        "POI_BUILDERQUEST_RESOURCECAR": {
            "status": "discovered" if has_resource_car_quest else "unknown",
            "scope": "world",
            "source": "Persisted builder-quest object",
            "reason": (
                "A persisted first-car builder quest object proves that this "
                "quest location was encountered."
            ),
        },
        "POI_SERVICE_ELEVATOR": {
            "status": "unknown",
            "observationStatus": "world-loaded" if b"26,-22" in elevator_data else "unconfirmed",
            "scope": "world",
            "source": "UndergroundElevatorManager storage channel 52",
            "reason": (
                "The elevator at cell (-26, -22) is registered in world-level "
                "storage, but registration does not prove a player visit."
            ),
        },
    }


def load_exact_roads(save_data: dict) -> dict:
    """Load launcher-managed exact road output for the selected save."""
    path = IMPORT_DIR / f"roads-{int(save_data['seed'])}.json"
    if not path.is_file():
        return {
            "status": "unavailable",
            "seed": save_data["seed"],
            "worldId": 1,
            "cells": [],
            "cellCount": 0,
            "source": "managed-road-helper",
            "message": "Exact roads have not been generated for this save yet.",
        }
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "status": "invalid",
            "cells": [],
            "cellCount": 0,
            "message": f"Managed road data could not be read: {error}",
        }
    if document.get("protocol") != "jc-scrapmap-roads-v1":
        raise ValueError("Managed road data uses an unsupported protocol.")
    if int(document.get("seed", -1)) != int(save_data["seed"]):
        raise ValueError("Managed road data does not match the selected save seed.")
    raw_cells = document.get("roads")
    if not isinstance(raw_cells, list):
        raise ValueError("Managed road data has no valid road list.")
    cells = []
    for item in raw_cells:
        if (
            not isinstance(item, list)
            or len(item) != 3
            or not all(isinstance(value, (int, float)) and float(value).is_integer() for value in item)
        ):
            raise ValueError("Managed road data contains a malformed road cell.")
        cell_x, cell_y, flags = (int(value) for value in item)
        if not 0 < flags <= 15:
            raise ValueError("Managed road data contains invalid directional flags.")
        cells.append([cell_x, cell_y, flags])
    water = []
    raw_water = document.get("water", [])
    if not isinstance(raw_water, list):
        raise ValueError("Managed map data has no valid water list.")
    for item in raw_water:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(value, (int, float)) and float(value).is_integer() for value in item)
        ):
            raise ValueError("Managed map data contains a malformed water cell.")
        water.append([int(item[0]), int(item[1])])

    def read_terrain_cells(field: str) -> list[list[int]]:
        raw_items = document.get(field, [])
        if not isinstance(raw_items, list):
            raise ValueError(f"Managed map data has no valid {field} list.")
        result = []
        for item in raw_items:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not all(
                    isinstance(value, (int, float)) and float(value).is_integer()
                    for value in item
                )
            ):
                raise ValueError(
                    f"Managed map data contains a malformed {field} cell."
                )
            result.append([int(item[0]), int(item[1])])
        return result

    desert = read_terrain_cells("desert")
    burnt_forest = read_terrain_cells("burntForest")
    schematic_stations = read_terrain_cells("schematicStations")
    return {
        "status": "available",
        "protocol": document["protocol"],
        "seed": int(document["seed"]),
        "worldId": int(document.get("worldId", 1)),
        "bounds": document.get("bounds"),
        "encoding": ["cellX", "cellY", "E=1 N=2 W=4 S=8"],
        "cells": cells,
        "cellCount": len(cells),
        "waterCells": water,
        "waterCellCount": len(water),
        "desertCells": desert,
        "desertCellCount": len(desert),
        "burntForestCells": burnt_forest,
        "burntForestCellCount": len(burnt_forest),
        "schematicStationCells": schematic_stations,
        "schematicStationCount": len(schematic_stations),
        "source": str(path),
        "message": f"Loaded {len(cells)} exact engine-generated road cells.",
    }


def readable_poi_name(poi_type: str) -> str:
    overrides = {
        "POI_MECHANICSTATION_QUEST_MEDIUM": "Quest mechanic station",
        "POI_PACKINGSTATIONVEG_MEDIUM": "Vegetable packing station",
        "POI_PACKINGSTATIONFRUIT_MEDIUM": "Fruit packing station",
        "POI_BUILDERQUEST_WOCHOUSE": "Builder quest: Woc house",
        "POI_BUILDERQUEST_RESOURCECAR": "Builder quest: resource car",
        "POI_SERVICE_ELEVATOR": "Small underground elevator",
    }
    if poi_type in overrides:
        return overrides[poi_type]
    words = poi_type.removeprefix("POI_").split("_")
    ignored = {"SMALL", "MEDIUM", "LARGE", "XL"}
    return " ".join(word.casefold() for word in words if word not in ignored).capitalize()


def load_poi_tile_mappings(game_path: Path) -> dict[str, str]:
    poi_path = (
        game_path
        / "Survival"
        / "Scripts"
        / "terrain"
        / "overworld"
        / "poi.lua"
    )
    if not poi_path.is_file():
        return {}
    text = poi_path.read_text(encoding="utf-8", errors="replace")
    mappings: dict[str, str] = {}
    pattern = re.compile(
        r"addPoiTile\(\s*(POI_[A-Z0-9_]+)\s*,\s*\"([^\"]+\.tile)\"\s*\)"
    )
    for poi_type, tile_path in pattern.findall(text):
        mappings.setdefault(poi_type, tile_path)
    return mappings


def tile_reference(game_path: Path, virtual_tile_path: str | None) -> dict | None:
    if not virtual_tile_path:
        return None
    relative = virtual_tile_path.replace("$SURVIVAL_DATA/", "")
    tileson_relative = str(Path(relative).with_suffix(".tileson")).replace("\\", "/")
    tileson_path = game_path / "Survival" / Path(tileson_relative)
    if not tileson_path.is_file():
        return None
    try:
        document = json.loads(tileson_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None

    info = document.get("info", {})
    entities = document.get("entities", {})
    categories = (
        "assets",
        "blueprints",
        "decals",
        "harvestables",
        "kinematics",
        "nodes",
        "prefabs",
    )
    summary = {
        category: len(entities.get(category, []))
        for category in categories
        if isinstance(entities.get(category, []), list)
    }
    points = []
    schematic_categories = {
        "assets",
        "blueprints",
        "harvestables",
        "kinematics",
        "nodes",
        "prefabs",
    }
    for category in schematic_categories:
        for entity in entities.get(category, []):
            if not isinstance(entity, dict) or entity.get("exclude") is True:
                continue
            position = entity.get("transform", {}).get("position")
            if not isinstance(position, list) or len(position) < 2:
                continue
            points.append(
                {
                    "category": category,
                    "x": round(float(position[0]), 3),
                    "y": round(float(position[1]), 3),
                }
            )

    return {
        "developerTile": Path(virtual_tile_path).stem,
        "virtualPath": virtual_tile_path,
        "source": tileson_relative,
        "uuid": info.get("uuid"),
        "cellsX": info.get("cellsX"),
        "cellsY": info.get("cellsY"),
        "entityCounts": summary,
        "schematicPoints": points,
        "schematic": "Installed entity positions; not a rendered game screenshot.",
    }


def inspect_generator_confirmed_map(game_path: Path) -> dict:
    survival_scripts = game_path / "Survival" / "Scripts"
    generator_path = survival_scripts / "terrain" / "overworld" / "generate_cells.lua"
    constants_path = survival_scripts / "game" / "survival_constants.lua"
    if not generator_path.is_file() or not constants_path.is_file():
        return {
            "status": "unavailable",
            "message": "Active Survival terrain scripts were not found.",
            "worldBounds": OVERWORLD_BOUNDS,
            "features": [],
        }

    generator_text = generator_path.read_text(encoding="utf-8", errors="replace")
    constants_text = constants_path.read_text(encoding="utf-8", errors="replace")
    poi_tiles = load_poi_tile_mappings(game_path)

    spawn_match = re.search(
        r"START_AREA_SPAWN_POINT\s*=\s*sm\.vec3\.new\(\s*"
        r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"(-?\d+(?:\.\d+)?)\s*\)",
        constants_text,
    )
    features = []
    if spawn_match:
        spawn_x, spawn_y, spawn_z = (float(value) for value in spawn_match.groups())
        features.append(
            {
                "id": "confirmed-start-position",
                "kind": "spawn",
                "title": "Starting position",
                "x": spawn_x,
                "y": spawn_y,
                "z": spawn_z,
                "cellX": int(spawn_x // CELL_SIZE_METERS),
                "cellY": int(spawn_y // CELL_SIZE_METERS),
                "sizeCells": 0,
                "confidence": "confirmed",
                "visibilityClass": "generator-known",
                "discoveryStatus": "discovered",
                "source": "Survival/Scripts/game/survival_constants.lua",
                "details": "New-character starting position; not the current player position.",
            }
        )

    fixed_start = generator_text.find("-- Crash site")
    fixed_end = generator_text.find("local largePois", fixed_start)
    fixed_section = (
        generator_text[fixed_start:fixed_end]
        if fixed_start >= 0 and fixed_end > fixed_start
        else ""
    )
    poi_pattern = re.compile(
        r"pois\[#pois\s*\+\s*1\]\s*=\s*\{\s*"
        r"x\s*=\s*(-?\d+)\s*,\s*y\s*=\s*(-?\d+)\s*,\s*"
        r"type\s*=\s*(POI_[A-Z0-9_]+)"
        r"(?P<rest>[^}]*)\}"
    )
    excluded_types = {"POI_CRASHSITE_AREA", "POI_ROAD_RANDOM"}
    for index, match in enumerate(poi_pattern.finditer(fixed_section), start=1):
        cell_x = int(match.group(1))
        cell_y = int(match.group(2))
        poi_type = match.group(3)
        if poi_type in excluded_types:
            continue
        rest = match.group("rest")
        size_match = re.search(r"\bsize\s*=\s*(\d+)", rest)
        rotation_match = re.search(r"\brotation\s*=\s*(\d+)", rest)
        road_match = re.search(r"\broad\s*=\s*(true|false)", rest)
        size = int(size_match.group(1)) if size_match else 1
        features.append(
            {
                "id": f"fixed-poi-{index}-{poi_type.casefold()}",
                "kind": "poi",
                "poiType": poi_type,
                "title": readable_poi_name(poi_type),
                "cellX": cell_x,
                "cellY": cell_y,
                "x": (cell_x + size / 2) * CELL_SIZE_METERS,
                "y": (cell_y + size / 2) * CELL_SIZE_METERS,
                "sizeCells": size,
                "rotation": int(rotation_match.group(1)) if rotation_match else None,
                "roadRequired": (
                    road_match.group(1) == "true" if road_match else None
                ),
                "confidence": "confirmed",
                "visibilityClass": "generator-known",
                "discoveryStatus": "unknown",
                "source": "Survival/Scripts/terrain/overworld/generate_cells.lua",
                "details": "Literal fixed POI from the active overworld generator.",
                "developerLabel": poi_type,
                "tile": tile_reference(game_path, poi_tiles.get(poi_type)),
            }
        )

    return {
        "status": "partial",
        "message": (
            "Showing literal generator-confirmed anchors across the overworld. "
            "Biomes, lakes, and connecting roads are not reconstructed yet."
        ),
        "cellSizeMeters": CELL_SIZE_METERS,
        "worldBounds": OVERWORLD_BOUNDS,
        "features": features,
        "sources": [
            "Survival/Scripts/game/survival_constants.lua",
            "Survival/Scripts/terrain/overworld/generate_cells.lua",
        ],
    }


def discoveries_path(save_identity: str) -> Path:
    return MAPPER_DATA_DIR / save_identity / "discoveries.json"


def load_discoveries(save_identity: str) -> dict[str, set[str]]:
    path = discoveries_path(save_identity)
    if not path.is_file():
        return {"discovered": set(), "undiscovered": set()}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"discovered": set(), "undiscovered": set()}
    feature_ids = document.get("discoveredFeatureIds", [])
    undiscovered_ids = document.get("undiscoveredFeatureIds", [])
    return {
        "discovered": (
            {value for value in feature_ids if isinstance(value, str)}
            if isinstance(feature_ids, list)
            else set()
        ),
        "undiscovered": (
            {value for value in undiscovered_ids if isinstance(value, str)}
            if isinstance(undiscovered_ids, list)
            else set()
        ),
    }


def write_discoveries(
    save_identity: str, discovered_ids: set[str], undiscovered_ids: set[str]
) -> Path:
    path = discoveries_path(save_identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schemaVersion": 2,
        "saveIdentity": save_identity,
        "updatedUtc": datetime.now(timezone.utc).isoformat(),
        "discoveredFeatureIds": sorted(discovered_ids),
        "undiscoveredFeatureIds": sorted(undiscovered_ids),
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temporary.replace(path)
    return path


def markers_path(save_identity: str) -> Path:
    return MAPPER_DATA_DIR / save_identity / "markers.json"


def load_markers(save_identity: str) -> list[dict]:
    path = markers_path(save_identity)
    if not path.is_file():
        return []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    markers = document.get("markers", [])
    return [item for item in markers if isinstance(item, dict) and not item.get("archived")]


def write_markers(save_identity: str, markers: list[dict]) -> Path:
    path = markers_path(save_identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schemaVersion": 1,
        "saveIdentity": save_identity,
        "updatedUtc": datetime.now(timezone.utc).isoformat(),
        "markers": markers,
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
    return path


def build_state(game_path: Path, user_dirs: list[Path], saves: list[Path], selected: Path) -> dict:
    save_data = inspect_save_read_only(selected)
    saved_position = read_saved_player_position(selected)
    saved_beacons = read_saved_beacons(selected)
    confirmed_map = inspect_generator_confirmed_map(game_path)
    roads = load_exact_roads(save_data)
    for cell_x, cell_y in roads.get("schematicStationCells", []):
        confirmed_map["features"].append(
            {
                "id": f"schematic-station-{cell_x}-{cell_y}",
                "kind": "poi",
                "poiType": "POI_ROAD_SCHEMATICSTATION",
                "title": "Schematic station",
                "cellX": cell_x,
                "cellY": cell_y,
                "x": (cell_x + 0.5) * CELL_SIZE_METERS,
                "y": (cell_y + 0.5) * CELL_SIZE_METERS,
                "sizeCells": 1,
                "rotation": None,
                "roadRequired": True,
                "confidence": "confirmed",
                "visibilityClass": "generator-known",
                "discoveryStatus": "unknown",
                "source": "managed terrain-helper capture",
                "details": "Exact Schematic Station captured from the generated overworld.",
                "developerLabel": "POI_ROAD_SCHEMATICSTATION",
                "tile": None,
            }
        )
    markers = load_markers(save_data["identity"])
    evidence = inspect_discovery_evidence(selected)
    manual = load_discoveries(save_data["identity"])
    for feature in confirmed_map["features"]:
        feature_evidence = evidence.get(feature.get("poiType"))
        if feature_evidence:
            feature["discoveryEvidence"] = feature_evidence
        if feature["kind"] == "spawn":
            feature["discoveryStatus"] = "discovered"
            feature["discoverySource"] = "generator-start"
        elif feature["id"] in manual["discovered"]:
            feature["discoveryStatus"] = "discovered"
            feature["discoverySource"] = "manual-override"
        elif feature["id"] in manual["undiscovered"]:
            feature["discoveryStatus"] = "unknown"
            feature["discoverySource"] = "manual-override"
        elif feature_evidence and feature_evidence["status"] == "discovered":
            feature["discoveryStatus"] = "discovered"
            feature["discoverySource"] = "save-evidence"
        else:
            feature["discoveryStatus"] = "unknown"
            feature["discoverySource"] = "unconfirmed"
    save_summaries = []
    for path in saves:
        identity = read_save_identity(path)
        save_summaries.append(
            {
                "identity": identity["id"],
                "filename": path.name,
                "path": str(path),
                "seed": identity["seed"],
                "owner": identity["owner"],
                "sizeBytes": path.stat().st_size,
                "modifiedUtc": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "selected": path.resolve() == selected.resolve(),
            }
        )

    return {
        "schemaVersion": 12,
        "app": {
            "name": "JC ScrapMap",
            "version": APP_VERSION,
            "generatedUtc": datetime.now(timezone.utc).isoformat(),
            "offline": True,
        },
        "paths": {
            "game": str(game_path),
            "gamePathExists": game_path.is_dir(),
            "userDirectories": [str(path) for path in user_dirs],
        },
        "availableSaves": save_summaries,
        "save": save_data,
        "map": {
            "cellSizeMeters": CELL_SIZE_METERS,
            "northUp": True,
            "zoomPresetsMeters": [100, 250, 500, 1000, 2000, 3000],
            **confirmed_map,
            "roads": roads,
            "water": {
                "status": "available" if roads.get("waterCells") else "unavailable",
                "cells": roads.get("waterCells", []),
                "cellCount": roads.get("waterCellCount", 0),
                "message": (
                    f"Loaded {roads.get('waterCellCount', 0)} exact water cells."
                    if roads.get("waterCells")
                    else "Water has not been captured for this save yet; generate the map again."
                ),
            },
            "desert": {
                "status": (
                    "available" if roads.get("desertCells") else "unavailable"
                ),
                "cells": roads.get("desertCells", []),
                "cellCount": roads.get("desertCellCount", 0),
                "message": (
                    f"Loaded {roads.get('desertCellCount', 0)} exact desert cells."
                    if roads.get("desertCells")
                    else "Desert has not been captured for this save yet; generate the map again."
                ),
            },
            "burntForest": {
                "status": (
                    "available"
                    if roads.get("burntForestCells")
                    else "unavailable"
                ),
                "cells": roads.get("burntForestCells", []),
                "cellCount": roads.get("burntForestCellCount", 0),
                "message": (
                    f"Loaded {roads.get('burntForestCellCount', 0)} exact burnt forest cells."
                    if roads.get("burntForestCells")
                    else "Burnt forest has not been captured for this save yet; generate the map again."
                ),
            },
            "markers": markers,
            "physicalBeacons": saved_beacons,
        },
        "playerPosition": saved_position,
        "layers": [
            {"id": "grid", "label": "Cell grid", "available": True, "visible": True},
            {
                "id": "player",
                "label": "Last saved player position",
                "available": saved_position["status"] == "available",
                "visible": True,
            },
            {
                "id": "roads",
                "label": "Roads",
                "available": roads["status"] == "available",
                "visible": True,
            },
            {
                "id": "terrain-regions",
                "label": "Terrain regions (water / desert / burnt forest)",
                "available": any(
                    (
                        roads.get("waterCells"),
                        roads.get("desertCells"),
                        roads.get("burntForestCells"),
                    )
                ),
                "visible": False,
            },
            {
                "id": "anchors",
                "label": "All POIs / anchors (spoilers)",
                "available": bool(confirmed_map["features"]),
                "visible": False,
            },
            {
                "id": "beacons",
                "label": "Physical beacons",
                "available": saved_beacons["status"] == "available"
                and saved_beacons["overworldCount"] > 0,
                "visible": False,
            },
            {"id": "notes", "label": "Custom notes", "available": True, "visible": True},
        ],
        "diagnostics": [
            {"level": "ok", "message": "Selected save opened in SQLite read-only mode."},
            {"level": "ok", "message": "Save hash, size, and timestamp remained unchanged."},
            {
                "level": (
                    "ok" if saved_position["status"] == "available" else "warning"
                ),
                "message": saved_position["message"],
            },
            {
                "level": "ok",
                "message": f"Separate mapper identity: {save_data['identity']}.",
            },
            {
                "level": "ok",
                "message": (
                    "Save evidence classified "
                    f"{sum(item['discoveryStatus'] == 'discovered' and item.get('kind') == 'poi' for item in confirmed_map['features'])} "
                    "diagnostic POIs as discovered."
                ),
            },
            {
                "level": "warning",
                "message": (
                    "Elevator registration proves world loading only; player "
                    "visitation remains unconfirmed."
                ),
            },
            {
                "level": "ok" if roads["status"] == "available" else "warning",
                "message": roads["message"],
            },
            {
                "level": (
                    "ok" if saved_beacons["status"] == "available" else "warning"
                ),
                "message": saved_beacons["message"],
            },
            {
                "level": "ok" if game_path.is_dir() else "warning",
                "message": (
                    "Scrap Mechanic installation path found."
                    if game_path.is_dir()
                    else "Scrap Mechanic installation path was not found."
                ),
            },
        ],
    }


def write_state(state: dict) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(state, indent=2, ensure_ascii=False)

    targets = [
        GENERATED_DIR / "state.json",
        MAPPER_DATA_DIR / state["save"]["identity"] / "state.json",
    ]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(target)
    return targets[0]


class ScrapMapSession:
    def __init__(
        self, game_path: Path, user_dirs: list[Path], saves: list[Path], selected: Path
    ) -> None:
        self.game_path = game_path
        self.user_dirs = user_dirs
        self.saves = saves
        self.selected = selected
        self.lock = threading.Lock()
        self.save_by_identity = {
            read_save_identity(path)["id"]: path for path in self.saves
        }

    def generate(self) -> dict:
        with self.lock:
            state = build_state(
                self.game_path, self.user_dirs, self.saves, self.selected
            )
            write_state(state)
            return state

    def select(self, identity: str) -> dict:
        candidate = self.save_by_identity.get(identity)
        if candidate is None:
            raise ValueError("Unknown save identity.")
        self.selected = candidate
        return self.generate()

    def set_feature_discovery(self, feature_id: str, discovered: bool) -> dict:
        with self.lock:
            current = build_state(
                self.game_path, self.user_dirs, self.saves, self.selected
            )
            valid_features = {
                feature["id"]: feature for feature in current["map"]["features"]
            }
            feature = valid_features.get(feature_id)
            if feature is None:
                raise ValueError("Unknown feature identifier.")
            if feature["kind"] == "spawn" and not discovered:
                raise ValueError("The starting position is always considered discovered.")
            save_identity = current["save"]["identity"]
            manual = load_discoveries(save_identity)
            discovered_ids = manual["discovered"]
            undiscovered_ids = manual["undiscovered"]
            if discovered:
                discovered_ids.add(feature_id)
                undiscovered_ids.discard(feature_id)
            else:
                discovered_ids.discard(feature_id)
                undiscovered_ids.add(feature_id)
            write_discoveries(save_identity, discovered_ids, undiscovered_ids)
            state = build_state(
                self.game_path, self.user_dirs, self.saves, self.selected
            )
            write_state(state)
            return state

    def save_marker(self, payload: dict) -> dict:
        with self.lock:
            identity = read_save_identity(self.selected)["id"]
            markers = load_markers(identity)
            marker_id = payload.get("id")
            if marker_id is not None and not isinstance(marker_id, str):
                raise ValueError("Invalid marker identifier.")
            title = payload.get("title", "")
            note = payload.get("note", "")
            color = payload.get("color", "#f2c94c")
            category = payload.get("category", "note")
            x, y = payload.get("x"), payload.get("y")
            if not isinstance(title, str) or not title.strip() or len(title) > 80:
                raise ValueError("Marker title must contain 1 to 80 characters.")
            if not isinstance(note, str) or len(note) > 2000:
                raise ValueError("Marker note cannot exceed 2000 characters.")
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise ValueError("Marker coordinates are invalid.")
            if color not in {"#f2c94c", "#eb5757", "#56ccf2", "#6fcf97", "#bb6bd9"}:
                raise ValueError("Marker color is invalid.")
            if category not in {"note", "base", "resource", "danger", "vehicle"}:
                raise ValueError("Marker category is invalid.")
            existing = next((item for item in markers if item.get("id") == marker_id), None)
            now = datetime.now(timezone.utc).isoformat()
            marker = existing or {"id": str(uuid.uuid4()), "createdUtc": now}
            marker.update({
                "title": title.strip(), "note": note.strip(), "x": float(x), "y": float(y),
                "color": color, "category": category, "modifiedUtc": now,
            })
            if existing is None:
                markers.append(marker)
            write_markers(identity, markers)
            state = build_state(self.game_path, self.user_dirs, self.saves, self.selected)
            write_state(state)
            return state

    def delete_marker(self, marker_id: str) -> dict:
        with self.lock:
            identity = read_save_identity(self.selected)["id"]
            markers = load_markers(identity)
            filtered = [item for item in markers if item.get("id") != marker_id]
            if len(filtered) == len(markers):
                raise ValueError("Unknown marker identifier.")
            write_markers(identity, filtered)
            state = build_state(self.game_path, self.user_dirs, self.saves, self.selected)
            write_state(state)
            return state


def make_request_handler(session: ScrapMapSession):
    class ScrapMapRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PROJECT_DIR), **kwargs)

        def do_GET(self) -> None:
            if self.path != "/api/status":
                super().do_GET()
                return
            response = json.dumps({"ok": True, "service": "jc-scrapmap"}).encode(
                "utf-8"
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def do_POST(self) -> None:
            if self.path not in {
                "/api/refresh",
                "/api/select-save",
                "/api/set-discovery",
                "/api/save-marker",
                "/api/delete-marker",
            }:
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 8192:
                    raise ValueError("Invalid request size.")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if self.path == "/api/refresh":
                    state = session.generate()
                elif self.path == "/api/select-save":
                    identity = payload.get("identity")
                    if not isinstance(identity, str):
                        raise ValueError("Missing save identity.")
                    state = session.select(identity)
                elif self.path == "/api/set-discovery":
                    feature_id = payload.get("featureId")
                    discovered = payload.get("discovered")
                    if not isinstance(feature_id, str) or not isinstance(
                        discovered, bool
                    ):
                        raise ValueError("Invalid discovery request.")
                    state = session.set_feature_discovery(feature_id, discovered)
                elif self.path == "/api/save-marker":
                    state = session.save_marker(payload)
                else:
                    marker_id = payload.get("id")
                    if not isinstance(marker_id, str):
                        raise ValueError("Missing marker identifier.")
                    state = session.delete_marker(marker_id)
                response = json.dumps(
                    {
                        "ok": True,
                        "identity": state["save"]["identity"],
                        "filename": state["save"]["filename"],
                        "featureId": payload.get("featureId"),
                        "discovered": payload.get("discovered"),
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            except (
                ValueError,
                RuntimeError,
                json.JSONDecodeError,
                sqlite3.DatabaseError,
            ) as error:
                response = json.dumps({"ok": False, "error": str(error)}).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

    return ScrapMapRequestHandler


def serve(session: ScrapMapSession, port: int, open_browser: bool) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), make_request_handler(session))
    url = f"http://127.0.0.1:{port}/web/index.html"
    print(f"JC ScrapMap is available at {url}")
    print("Press Ctrl+C to stop the local server.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping JC ScrapMap.")
    finally:
        server.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the offline JC ScrapMap prototype.")
    parser.add_argument("--game-path", help="Scrap Mechanic installation directory.")
    parser.add_argument(
        "--user-path",
        help="Scrap Mechanic User root or one specific User_<SteamId> directory.",
    )
    parser.add_argument("--save", help="Specific Survival .db save to inspect.")
    parser.add_argument("--seed", type=int, help="Select the Survival save with this world seed.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Localhost port.")
    parser.add_argument("--no-server", action="store_true", help="Generate state and exit.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser.")
    parser.add_argument("--list-saves", action="store_true", help="List detected saves and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    game_path = Path(args.game_path).expanduser().resolve() if args.game_path else default_game_path()
    user_root = Path(args.user_path).expanduser().resolve() if args.user_path else default_user_root()
    user_dirs = discover_user_directories(user_root)
    saves = discover_saves(user_dirs)

    if args.list_saves:
        if not saves:
            print("No Survival saves found.")
            return 1
        for index, path in enumerate(saves, start=1):
            identity = read_save_identity(path)
            print(f"{index}: seed={identity['seed']} path={path}")
        return 0

    if args.seed is not None and args.save:
        raise ValueError("Use either --save or --seed, not both.")
    if args.seed is not None:
        selected = next(
            (path for path in saves if int(read_save_identity(path)["seed"]) == args.seed),
            None,
        )
        if selected is None:
            raise FileNotFoundError(f"No discovered Survival save has seed {args.seed}.")
    else:
        selected = select_save(saves, args.save)
    if selected not in saves:
        saves.insert(0, selected)

    print(f"Game path: {game_path}")
    print(f"Selected save: {selected}")
    state = build_state(game_path, user_dirs, saves, selected)
    state_path = write_state(state)
    print(f"Generated state: {state_path}")
    print(f"Read-only verification: {state['save']['readOnlyVerified']}")

    if not args.no_server:
        session = ScrapMapSession(game_path, user_dirs, saves, selected)
        serve(session, args.port, not args.no_browser)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, sqlite3.DatabaseError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
