"""JC ScrapMap Prototype 0A.

Reads Scrap Mechanic save metadata in SQLite read-only mode, writes normalized
local state, and optionally serves the offline browser interface on localhost.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from terrain_reader import (
    TERRAIN_DATA_UID,
    TerrainObjectReader,
    read_terrain_blob,
    unpack_script_data,
)


APP_VERSION = "0.9.7"
DEFAULT_PORT = 8765
PROJECT_DIR = Path(__file__).resolve().parent
INSTANCE_ID = hashlib.sha256(
    str(PROJECT_DIR).casefold().encode("utf-8")
).hexdigest()[:16]
WEB_DIR = PROJECT_DIR / "web"
GENERATED_DIR = PROJECT_DIR / "generated"
MAPPER_DATA_DIR = PROJECT_DIR / "mapper-data"
IMPORT_DIR = PROJECT_DIR / "imports"
LOG_DIR = PROJECT_DIR / "logs"
OVERLAY_SETTINGS_PATH = PROJECT_DIR / "settings" / "overlay-browser.json"
CELL_SIZE_METERS = 64
ENGINE_UUIDS = {
    "f56d7788-122e-421a-b63b-2938466125e9": "Gas engine",
    "48563128-f84a-4342-8d9f-190c633a6ea9": "Electric engine",
    "c96ab903-f238-4bae-a614-28a758716d00": "Scrap gas engine",
    "1bfccc0a-828f-475c-882c-87d5a96054c9": "Gas engine",
    "33d01ddd-f32b-4a9a-87d6-efb6710b389c": "Gas engine",
    "470b9a92-ed94-4ef2-b1ea-b45f47ef0982": "Gas engine",
    "bfcaac1a-5a7f-4fba-9980-1159617a7212": "Gas engine",
    "3091926a-9340-46d9-83d6-4fd7c68ad950": "Gas engine",
    "5e5d231e-405e-4f45-9bd0-b3557dbb42eb": "Electric engine",
    "0c9cc5bb-af2f-4023-b8d8-cd7d52a60efe": "Electric engine",
    "56cea967-a685-494d-85ef-3aa121a0c193": "Electric engine",
    "5e57e0f7-e87c-4269-b274-146fe40e1b44": "Electric engine",
    "22f3e797-82f5-4819-a085-c3cc28ec9025": "Electric engine",
    "d5e36413-b3c1-4636-8447-3410c352ec7b": "Creative gas engine",
    "6546c293-a5aa-4442-80d5-a2819f077746": "Creative electric engine",
}
ENGINE_UUID_BYTES = {
    uuid.UUID(identifier).bytes[::-1]: label
    for identifier, label in ENGINE_UUIDS.items()
}
DRIVER_SEAT_UUIDS = {
    "bd597ac9-6640-43ba-9bd8-ed584a794f13": "Scrap driver's seat",
    "cf3fdcfc-a7e5-4497-b000-ffda67dd8db7": "Creative driver's seat",
    "77c2687c-2e13-4df8-996a-96fb26d75ee0": "Driver's seat",
    "efbf45f8-62ec-4541-9eb1-d529966f6a29": "Driver's seat",
    "c3ef3008-9367-4ab7-813a-24195d63e5a3": "Driver's seat",
    "d30dcd12-ec39-43b9-a115-44c08e1b9091": "Driver's seat",
    "ffa3a47e-fc0d-4977-802f-bd15683bbe5c": "Driver's seat",
    "38ee0516-abc5-4e46-9195-c763610d7ec4": "Creative driver's saddle",
    "7d601a5a-796d-4cae-be88-b47479d38d11": "Driver's saddle",
    "bb2ed406-f0d3-4fd6-b3f9-7caadfa8e4e4": "Driver's saddle",
    "6953b17e-0a38-4107-8c56-5ee97e68bee3": "Driver's saddle",
    "41960868-6245-47b5-97c4-f446e199812f": "Driver's saddle",
    "9dd1ccea-1e44-430d-b706-3ff45416583e": "Driver's saddle",
    "20f59114-5964-451f-bb47-820da3ebbc3b": "Creative saddle",
    "2d3016f7-febe-416e-93bc-41d80ca3910d": "Saddle",
    "c39b3537-d9b2-45f8-b2ea-0e9002c896d9": "Saddle",
    "797e07a3-6d56-4b74-949b-9492c7946e0d": "Saddle",
    "7516f5b8-9a15-4606-92bb-ea9a96a16594": "Saddle",
    "42f70341-207d-4e9d-b8ed-37962603a926": "Saddle",
    "1786e265-cebe-4ef1-9d13-02c104c6207b": "Turret seat",
    "05f3a5a4-532a-4642-b648-e0dd60ce9f4d": "Turret seat",
    "c227ba7c-171c-4a7c-b5e4-faa84d44f03a": "Turret seat",
    "7f3eae8d-3dd1-47f6-94de-0450c86e4af0": "Turret seat",
    "42b4c02e-2de5-431e-981a-f42cb7829e68": "Turret seat",
}
DRIVER_SEAT_UUID_BYTES = {
    uuid.UUID(identifier).bytes[::-1]: label
    for identifier, label in DRIVER_SEAT_UUIDS.items()
}
SUSPENSION_UUIDS = {
    "aa8d89eb-919b-42f4-8b58-af6f0d5856bc": "Creative sport suspension",
    "a481138b-fae9-47c9-9bc2-91b6d2e2bf52": "Creative off-road suspension",
    "67da25c9-3825-41f6-9724-4546a11cb2a5": "Sport suspension",
    "aae686a2-0eb3-43b3-b998-def282de79e9": "Sport suspension",
    "d0aa2676-5266-432a-bf7e-3887e6ddedd5": "Sport suspension",
    "d9adddcc-972d-4726-a376-67f950b99a44": "Sport suspension",
    "52855106-a95c-4427-9970-3f227109b66d": "Sport suspension",
    "f3cfef9d-faef-4be8-9283-476eb99614d7": "Off-road suspension",
    "00284190-1484-4286-a198-b2ddef768c2e": "Off-road suspension",
    "a9658eaf-0dd8-46a6-8cac-be6978f19b79": "Off-road suspension",
    "4c3f6a7c-45c6-4ed8-bf13-c247c3db6b81": "Off-road suspension",
    "73f838db-783e-4a41-bc0f-9008967780f3": "Off-road suspension",
    "3cdbbefe-43b4-4ad7-af47-af0b2e7563c9": "Sport suspension with bearing",
    "81211639-f02c-43ff-b3b5-70d6ba8f2e9b": "Sport suspension with bearing",
    "5f63541f-f6be-4acc-8948-ba9d30a58d78": "Sport suspension with bearing",
    "f4d77a3b-6568-4630-9d4d-888323b325f8": "Sport suspension with bearing",
    "4cb6aaf3-a807-4ad6-aaa0-0d0e321b8253": "Sport suspension with bearing",
    "fdfcdb68-af22-4bb3-87d6-bd44b3c8b671": "Off-road suspension with bearing",
    "ad9e5936-ecf0-4d2e-a96b-6c1413d3aba2": "Off-road suspension with bearing",
    "ad3654b9-f64c-411b-8c70-32c2ba83e2cf": "Off-road suspension with bearing",
    "515dd68d-9371-49c0-b9ef-79036b8486b2": "Off-road suspension with bearing",
    "18055540-6cb7-4c03-857d-1414d410f309": "Off-road suspension with bearing",
}
SUSPENSION_UUID_BYTES = {
    uuid.UUID(identifier).bytes[::-1]: label
    for identifier, label in SUSPENSION_UUIDS.items()
}
ACCESS_CARD_UUIDS = {
    1: "7cd0faee-77bb-4afc-a2e2-d198a5c16200",
    2: "ae6773eb-c842-4dd8-8421-d83ed7069ace",
    3: "d8239bc7-7232-4d66-9d7f-893cd3b45dcd",
    4: "63ad737c-e03e-4c64-a8de-86cac9e5e6b7",
}
VAULT_CARD_TARGETS = {2: 10_000, 3: 100_000, 4: 1_000_000}
UNDERGROUND_DEPTHS = (
    (1, "Mining Hub", 1),
    (2, "Onboarding", 1),
    (3, "Station 1", 2),
    (4, "Drill 1", 2),
    (5, "Scrapyard", 3),
    (6, "Drill 2", 3),
    (7, "Station 2", 4),
    (8, "Final Boss Lobby", None),
)
UNDERGROUND_WORLD_FILES = {
    1: "undergroundworld_mininghub.world",
    2: "undergroundworld_onboarding.world",
    3: "undergroundworld_station_01.world",
    4: "undergroundworld_drill_01.world",
    5: "undergroundworld_scrapyard.world",
    6: "undergroundworld_drill_02.world",
    7: "undergroundworld_station_02.world",
    8: "undergroundworld_final_boss_lobby.world",
}
QUARTZ_HARVESTABLE_UUID = "a98a1502-7c9e-4dae-b7f9-30f31fc99496"
UNDERGROUND_CHUNK_SHAPES = {
    "26e7cb39-f380-4203-80c8-b1bf1b4f598d": "Loose Tier-1 ore chunk",
}
UNDERGROUND_MATERIALS = {
    "ce7b8345-9f10-42fe-a185-aa229d05f473": "Tier-1 ore material",
}
OVERWORLD_BOUNDS = {"xMin": -64, "xMax": 63, "yMin": -48, "yMax": 47}
UNDERGROUND_ENTRANCE_MESSAGE = (
    "Entrance identified, but this underground areas map will be added in "
    "future versions of JC_ScrapMap."
)
UNDERGROUND_ENTRANCE_TYPES = {
    "POI_RUINCITY_XL": ("Scrap City underground entrance", "MAIN"),
    "POI_MECHANICSTATION_MEDIUM": ("Mechanic station underground entrance", "MECHANICSTATION"),
    "POI_SERVICE_ELEVATOR": ("Small underground elevator", "SERVICE"),
    "POI_EXCAVATION": ("Excavation underground entrance", "EXCAVATION"),
    "POI_MEADOW_GROWLAB_QUEST_LARGE": ("Quest Grow Lab entrance", "MINIDUNGEON"),
    "POI_MEADOW_GROWLAB_SILODISTRICT_XL": ("Silo District Grow Lab entrance", "MINIDUNGEON"),
    "POI_BURNTFOREST_GROWLAB_FROZEN_LARGE": ("Frozen Grow Lab entrance", "MINIDUNGEON"),
    "POI_FOREST_GROWLAB_STATION_LARGE": ("Forest Grow Lab entrance", "MINIDUNGEON"),
    "POI_LAKE_GROWLAB_ISLAND_XL": ("Island Grow Lab entrance", "MINIDUNGEON"),
    "POI_DESERT_GROWLAB_CLIFFTOP_LARGE": ("Clifftop Grow Lab entrance", "MINIDUNGEON"),
}
GLOBAL_STORAGE_UID = bytes.fromhex("2C3699B2FD9C503EA405CF73434E2E88")
PLAYER_DATA_UID = bytes.fromhex("67CE7FE2F7564898B8F076080146A358")
PLAYER_DATA_OFFSET = 31
BEACON_STORAGE_CHANNEL = 35
ROAD_MASK = 0x0F00
ROAD_SHIFT = 8
TERRAIN_MASK = 0xF000
TERRAIN_SHIFT = 12
TERRAIN_DESERT = 3
TERRAIN_BURNT_FOREST = 5
TERRAIN_AUTUMN_FOREST = 6
TERRAIN_LAKE = 8
SCHEMATIC_STATION_UID_RAW = "b5040b3a1a8700aa9a4c679745dd0829"
FIXED_BUILDER_QUEST_TYPES = {
    "POI_BUILDERQUEST_WOCHOUSE",
    "POI_BUILDERQUEST_RESOURCECAR",
}
# Installed terrain tiles whose authored entities include the Caged Farmer
# shape. Values are persisted tile UUIDs; sizes are measured in terrain cells.
PRISONER_CAMP_TILE_SIZES = {
    "00460eb3cd0b2eb0654ce71989f09f13": 1,
    "10ed222c9f01b6931f47e842327cafc1": 8,
    "167dece8372e08852d41605c972686f7": 1,
    "1c9b125e2b6958bf654612bf7979e40d": 1,
    "1e7387e9e63b6d9ab74d8c7c71a6f04d": 2,
    "2430ea9cfa6569a01443c5c9812c8bdd": 1,
    "2781a3ec2ea6b1a59c4d8722e44cf533": 4,
    "2932b1ac1fe2a0b2384c864e51ce8cca": 1,
    "3736c629769057a6b840482cd3280b15": 1,
    "3b91a2c4a0c1e1b7e84f33927b03f008": 8,
    "3ca5bbd66bf2cebbba4901fb93cdac2b": 1,
    "42a3ce6c06b003a3974c976abf81c9ad": 1,
    "552054a85eac4a8a084aec2aa45c35b0": 2,
    "5a2dc211996131889845705de185225b": 1,
    "5d397a2bbbc6e09aec4dc7614ca6bdc3": 1,
    "640fdd0fe46a11a3fa4b4a6dddd2fbe4": 1,
    "667aed059adcd098eb45a65c08b40fc6": 2,
    "7a757034f8cde9ab86417a895e31a616": 1,
    "7feb563cf1de1985c043119c48fda0af": 1,
    "848e5a8ce09ca3928e43f53d1e72119b": 1,
    "8bc218842bb29db9c344a488663a70e7": 2,
    "8c7469f511d34b9c4e40302566e0b7a3": 2,
    "97f9cfe1ebdfe98c3747607fc099c32c": 1,
    "a3ff442d2da1b58ab94b62bde5e6d3bf": 1,
    "ab1f3f8dabe0b0abbe4bb0bac156b9b5": 4,
    "be90d110d5c0ebb74e48f3201216c4dd": 1,
    "ce395d6ffd6c7c8d0244ccca22fb5605": 1,
    "d3fa50ba482da086b54e2c48d07dc02f": 1,
    "ee9a0091005835a08e420eb570faad75": 1,
    "f19ab41e335e8689bd4afa5948d4b605": 1,
    "f670be155726c39a33417ba02f7dca6c": 1,
}
# Ordinary lootable ruin tiles only. Ruin City, crash-site scenery, quest
# ruins, minidungeons, and other special structures are intentionally absent.
RUIN_TILE_SIZES = {
    "0240961ee0337a955a4788a29b1f26c0": 1,
    "04dd8a0c1c185f947049168495e95899": 2,
    "063bb25db681bbaaa547103fddee1e92": 2,
    "077d926a394bc18d684f0fe7d24a7968": 1,
    "1c9b125e2b6958bf654612bf7979e40d": 1,
    "1caa47c0c5850ba71043a17c37f2fb61": 1,
    "2430ea9cfa6569a01443c5c9812c8bdd": 1,
    "2932b1ac1fe2a0b2384c864e51ce8cca": 1,
    "3ba221455cd342aa1449915dd458ee51": 1,
    "47cb5e30d4a41fb6b849078afbfea67b": 1,
    "4eea57661726b69181411724c0fd32a1": 1,
    "4f84736fe46be59fea4aa91a49fdf319": 1,
    "56b32a59b10fdbab9044211f85c40a19": 1,
    "5a2dc211996131889845705de185225b": 1,
    "5d397a2bbbc6e09aec4dc7614ca6bdc3": 1,
    "701658b2a4ac778d064398e2e9280b24": 1,
    "712f58b86d43bfbd9042977c31d9e270": 2,
    "8c7469f511d34b9c4e40302566e0b7a3": 2,
    "8df1252a2f5617a1034a51c39218583d": 2,
    "8e7cf6a0c6668ab4bc4a8055be8f020a": 1,
    "961b1f8ead6398bfec49c14fa41b041f": 1,
    "98aa84fc15b27c9d1a40ac482bc3ba10": 2,
    "a4668447bcb55791a74f60896814da95": 1,
    "b85f55e9d238b3afee40497c17622118": 1,
    "be2dc7febf15eea8ab4406803ce072a3": 1,
    "d3fa50ba482da086b54e2c48d07dc02f": 1,
    "e325e96a5226619c654e861865470036": 2,
    "e402f39adc91f08f3b49a5c18f5fd031": 2,
    "e4a2c23f468439a4954e9408c6dce1af": 1,
    "ea2fb2ff8ad4fd87084542c1e9353f8e": 1,
    "f670be155726c39a33417ba02f7dca6c": 1,
    # Legacy upgrade UUIDs retained for established Survival saves.
    "68794ad2e70f4f688dc14b396a927d07": 1,
    "ca8cce514e864c38b2a0e21facb13229": 1,
    "1f041ba44fc149ecbf9863ad8e1f1b96": 1,
    "240b28e9e29843068d77aca4b2581670": 1,
    "51ee58d45d914914aa42d35c4521a23b": 1,
    "190ac4851f214490abdb0fb1592ab356": 1,
    "9958e99584164970945f181c0c8add04": 2,
    "910e80a5294d41a0930e6887a6cab9cf": 2,
}
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

LOGGER = logging.getLogger("jc-scrapmap")


def configure_logging() -> Path | None:
    """Mirror operational events to the console and a small rolling log."""
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    LOGGER.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)sZ [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    formatter.converter = time.gmtime
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    LOGGER.addHandler(console)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / "jc-scrapmap.log"
        rolling = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        rolling.setFormatter(formatter)
        LOGGER.addHandler(rolling)
        return log_path
    except OSError as error:
        LOGGER.warning(
            "Persistent logging is unavailable (%s); live console logging continues.",
            type(error).__name__,
        )
        return None


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
            if userdata_type == 10001:
                raw = self.read_bytes(16)[::-1]
                return str(uuid.UUID(bytes=raw))
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


def steam_install_roots() -> list[Path]:
    roots: list[Path] = []

    def add(value: str | os.PathLike | None) -> None:
        if not value:
            return
        path = Path(value).expanduser()
        if path not in roots:
            roots.append(path)

    if os.name == "nt":
        try:
            import winreg

            registry_locations = (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
            )
            for hive, key_name in registry_locations:
                try:
                    with winreg.OpenKey(hive, key_name) as key:
                        for value_name in ("SteamPath", "InstallPath"):
                            try:
                                add(winreg.QueryValueEx(key, value_name)[0])
                            except OSError:
                                pass
                except OSError:
                    pass
        except ImportError:
            pass
    add(Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam")
    return roots


def steam_library_roots(steam_roots: list[Path] | None = None) -> list[Path]:
    libraries: list[Path] = []

    def add(path: Path) -> None:
        if path not in libraries:
            libraries.append(path)

    for steam_root in steam_roots or steam_install_roots():
        add(steam_root)
        library_file = steam_root / "steamapps" / "libraryfolders.vdf"
        try:
            text = library_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in re.finditer(r'^\s*"path"\s+"(.+)"\s*$', text, re.MULTILINE):
            add(Path(match.group(1).replace(r"\\", "\\")))
    return libraries


def default_game_path(steam_roots: list[Path] | None = None) -> Path:
    libraries = steam_library_roots(steam_roots)
    for library_root in libraries:
        candidate = library_root / "steamapps" / "common" / "Scrap Mechanic"
        terrain = candidate / "Survival" / "Scripts" / "terrain" / "terrain_overworld.lua"
        if terrain.is_file():
            return candidate.resolve()
    checked = ", ".join(str(path) for path in libraries)
    raise FileNotFoundError(
        "Scrap Mechanic was not found in the registered Steam libraries"
        + (f": {checked}" if checked else ".")
        + " Pass --game-path with the full installation folder."
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
        row = connection.execute("SELECT seed FROM Game").fetchone()
        if row is None:
            raise ValueError(f"Save has no Game metadata row: {path}")
        seed = row[0]
    finally:
        connection.close()

    owner = save_owner_name(path)
    identity_source = b"\0".join(
        (
            owner.casefold().encode("utf-8"),
            path.name.casefold().encode("utf-8"),
            str(seed).encode("ascii"),
        )
    )
    return {
        "id": hashlib.sha256(identity_source).hexdigest()[:20],
        "seed": seed,
        "owner": owner,
    }


def inspect_save_read_only(path: Path) -> dict:
    before = path.stat()
    before_hash = sha256_file(path)
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        game_columns = {
            str(row[1]).casefold()
            for row in connection.execute('PRAGMA table_info("Game")')
        }
        unique_ids_length = (
            'length("uniqueIds")'
            if "uniqueids" in game_columns
            else "NULL"
        )
        game = connection.execute(
            f"""
            SELECT savegameversion, flags, seed, gametick,
                   length(mods), {unique_ids_length}
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


def collapse_tile_placements(
    cells_by_uid: dict[str, list[tuple[int, int]]], tile_sizes: dict[str, int]
) -> list[list[float | int]]:
    """Return one cell-center coordinate for each matching tile placement."""
    placements = []
    for tile_uid, cells in cells_by_uid.items():
        if tile_sizes[tile_uid] == 1:
            placements.extend([[cell_x, cell_y] for cell_x, cell_y in cells])
            continue

        remaining = set(cells)
        while remaining:
            pending = [remaining.pop()]
            component = []
            while pending:
                cell = pending.pop()
                component.append(cell)
                cell_x, cell_y = cell
                for neighbor in (
                    (cell_x - 1, cell_y),
                    (cell_x + 1, cell_y),
                    (cell_x, cell_y - 1),
                    (cell_x, cell_y + 1),
                ):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        pending.append(neighbor)
            placements.append(
                [
                    sum(cell[0] for cell in component) / len(component),
                    sum(cell[1] for cell in component) / len(component),
                ]
            )
    return sorted(placements, key=lambda cell: (cell[1], cell[0]))


def collapse_prisoner_camp_cells(
    cells_by_uid: dict[str, list[tuple[int, int]]],
) -> list[list[float | int]]:
    return collapse_tile_placements(cells_by_uid, PRISONER_CAMP_TILE_SIZES)


def find_road_connected_large_pois(
    cells_by_uid: dict[str, list[tuple[int, int]]], flags: dict
) -> list[list[int]]:
    """Return exact 4x4 tile footprints that connect directly to a road."""
    placements = []
    for cells in cells_by_uid.values():
        remaining = set(cells)
        while remaining:
            pending = [remaining.pop()]
            component = []
            while pending:
                cell = pending.pop()
                component.append(cell)
                cell_x, cell_y = cell
                for neighbor in (
                    (cell_x - 1, cell_y),
                    (cell_x + 1, cell_y),
                    (cell_x, cell_y - 1),
                    (cell_x, cell_y + 1),
                ):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        pending.append(neighbor)
            xs = [cell[0] for cell in component]
            ys = [cell[1] for cell in component]
            if len(component) != 16 or max(xs) - min(xs) != 3 or max(ys) - min(ys) != 3:
                continue
            cell_x = min(xs)
            cell_y = min(ys)
            perimeter = (
                [(x, y) for x in range(cell_x - 1, cell_x + 5) for y in (cell_y - 1, cell_y + 4)]
                + [(x, y) for x in (cell_x - 1, cell_x + 4) for y in range(cell_y, cell_y + 4)]
            )
            if any((flags.get(y, {}).get(x, 0) & ROAD_MASK) != 0 for x, y in perimeter):
                placements.append([cell_x, cell_y])
    return sorted(placements, key=lambda cell: (cell[1], cell[0]))


def collapse_exact_tile_origins(
    cells: list[tuple[int, int]], size: int
) -> list[list[int]]:
    origins = []
    remaining = set(cells)
    while remaining:
        pending = [remaining.pop()]
        component = []
        while pending:
            cell = pending.pop()
            component.append(cell)
            cell_x, cell_y = cell
            for neighbor in (
                (cell_x - 1, cell_y),
                (cell_x + 1, cell_y),
                (cell_x, cell_y - 1),
                (cell_x, cell_y + 1),
            ):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
        xs = [cell[0] for cell in component]
        ys = [cell[1] for cell in component]
        if (
            len(component) == size * size
            and max(xs) - min(xs) == size - 1
            and max(ys) - min(ys) == size - 1
        ):
            origins.append([min(xs), min(ys)])
    return sorted(origins, key=lambda cell: (cell[1], cell[0]))


def load_exact_roads(
    save_path: Path, save_data: dict, game_path: Path | None = None
) -> dict:
    """Read exact roads and terrain regions from persisted overworld terrain."""
    try:
        encoded = read_terrain_blob(save_path, 1)
        terrain = TerrainObjectReader(unpack_script_data(encoded)).read_value()
    except (
        ValueError,
        IndexError,
        struct.error,
        sqlite3.DatabaseError,
        OSError,
    ) as error:
        LOGGER.warning(
            "Persisted overworld terrain unavailable category=%s.",
            type(error).__name__,
        )
        return {
            "status": "unavailable",
            "seed": save_data["seed"],
            "worldId": 1,
            "cells": [],
            "cellCount": 0,
            "waterCells": [],
            "waterCellCount": 0,
            "desertCells": [],
            "desertCellCount": 0,
            "burntForestCells": [],
            "burntForestCellCount": 0,
            "autumnForestCells": [],
            "autumnForestCellCount": 0,
            "schematicStationCells": [],
            "schematicStationCount": 0,
            "_builderQuestPlacements": [],
            "_resourcePitPlacements": [],
            "roadConnectedLargePoiCells": [],
            "prisonerCampCells": [],
            "prisonerCampCount": 0,
            "ruinCells": [],
            "ruinCount": 0,
            "source": "selected-save-terrain",
            "message": f"Persisted overworld terrain is unavailable: {error}",
        }
    if not isinstance(terrain, dict):
        raise ValueError("Persisted overworld terrain is not a Lua table.")
    if int(terrain.get("seed", -1)) != int(save_data["seed"]):
        raise ValueError("Persisted overworld terrain seed does not match the save.")
    bounds = terrain.get("bounds")
    flags = terrain.get("flags")
    if not isinstance(bounds, dict) or not isinstance(flags, dict):
        raise ValueError("Persisted overworld terrain has no valid bounds or flags.")
    required_bounds = ("xMin", "xMax", "yMin", "yMax")
    if not all(isinstance(bounds.get(key), int) for key in required_bounds):
        raise ValueError("Persisted overworld terrain bounds are malformed.")

    if game_path is None:
        try:
            game_path = default_game_path()
        except FileNotFoundError:
            game_path = Path()

    cells = []
    water = []
    desert = []
    burnt_forest = []
    autumn_forest = []
    schematic_stations = []
    schematic_station_uids = load_schematic_station_uids(game_path)
    builder_quest_specs = load_builder_quest_tile_specs(game_path)
    builder_quest_cells = {uid: [] for uid in builder_quest_specs}
    resource_pit_specs = load_resource_pit_tile_specs(game_path)
    resource_pit_cells = {uid: [] for uid in resource_pit_specs}
    large_poi_cells_by_uid: dict[str, list[tuple[int, int]]] = {}
    prisoner_cells_by_uid = {
        tile_uid: [] for tile_uid in PRISONER_CAMP_TILE_SIZES
    }
    ruin_cells_by_uid = {tile_uid: [] for tile_uid in RUIN_TILE_SIZES}
    terrain_uids = terrain.get("uid")
    if not isinstance(terrain_uids, dict):
        raise ValueError("Persisted overworld terrain has no valid UID matrix.")
    for cell_y in range(bounds["yMin"], bounds["yMax"] + 1):
        row = flags.get(cell_y)
        uid_row = terrain_uids.get(cell_y)
        if not isinstance(row, dict):
            raise ValueError(f"Persisted terrain is missing flag row {cell_y}.")
        if not isinstance(uid_row, dict):
            raise ValueError(f"Persisted terrain is missing UID row {cell_y}.")
        for cell_x in range(bounds["xMin"], bounds["xMax"] + 1):
            raw_flag = row.get(cell_x)
            if not isinstance(raw_flag, int):
                raise ValueError(
                    f"Persisted terrain flag at ({cell_x}, {cell_y}) is malformed."
                )
            road = (raw_flag & ROAD_MASK) >> ROAD_SHIFT
            if road:
                cells.append([cell_x, cell_y, road])
            terrain_type = (raw_flag & TERRAIN_MASK) >> TERRAIN_SHIFT
            if terrain_type == TERRAIN_LAKE:
                water.append([cell_x, cell_y])
            elif terrain_type == TERRAIN_DESERT:
                desert.append([cell_x, cell_y])
            elif terrain_type == TERRAIN_BURNT_FOREST:
                burnt_forest.append([cell_x, cell_y])
            elif terrain_type == TERRAIN_AUTUMN_FOREST:
                autumn_forest.append([cell_x, cell_y])
            cell_uid = uid_row.get(cell_x)
            if (
                isinstance(cell_uid, dict)
                and cell_uid.get("type") == "uuid"
            ):
                tile_uid = cell_uid.get("raw")
                if tile_uid in schematic_station_uids:
                    schematic_stations.append([cell_x, cell_y])
                if tile_uid in builder_quest_cells:
                    builder_quest_cells[tile_uid].append((cell_x, cell_y))
                if tile_uid in resource_pit_cells:
                    resource_pit_cells[tile_uid].append((cell_x, cell_y))
                large_poi_cells_by_uid.setdefault(tile_uid, []).append((cell_x, cell_y))
                if tile_uid in prisoner_cells_by_uid:
                    prisoner_cells_by_uid[tile_uid].append((cell_x, cell_y))
                if tile_uid in ruin_cells_by_uid:
                    ruin_cells_by_uid[tile_uid].append((cell_x, cell_y))

    prisoner_camps = collapse_prisoner_camp_cells(prisoner_cells_by_uid)
    ruins = collapse_tile_placements(ruin_cells_by_uid, RUIN_TILE_SIZES)
    road_connected_large_pois = find_road_connected_large_pois(
        large_poi_cells_by_uid, flags
    )
    builder_quest_placements = []
    for tile_uid, spec in builder_quest_specs.items():
        for cell_x, cell_y in collapse_exact_tile_origins(
            builder_quest_cells[tile_uid], spec["sizeCells"]
        ):
            builder_quest_placements.append(
                {**spec, "cellX": cell_x, "cellY": cell_y}
            )
    builder_quest_placements.sort(
        key=lambda item: (item["cellY"], item["cellX"], item["poiType"])
    )
    resource_pit_placements = []
    for tile_uid, spec in resource_pit_specs.items():
        for cell_x, cell_y in collapse_exact_tile_origins(
            resource_pit_cells[tile_uid], spec["sizeCells"]
        ):
            resource_pit_placements.append(
                {**spec, "cellX": cell_x, "cellY": cell_y}
            )
    resource_pit_placements.sort(
        key=lambda item: (item["cellY"], item["cellX"], item["poiType"])
    )

    LOGGER.info(
        "Terrain decoded seed=%s roads=%s water=%s desert=%s burntForest=%s autumnForest=%s stations=%s roadConnectedLargePois=%s prisonerCamps=%s ruins=%s.",
        int(terrain["seed"]),
        len(cells),
        len(water),
        len(desert),
        len(burnt_forest),
        len(autumn_forest),
        len(schematic_stations),
        len(road_connected_large_pois),
        len(prisoner_camps),
        len(ruins),
    )
    return {
        "status": "available",
        "protocol": "jc-scrapmap-save-terrain-v1",
        "seed": int(terrain["seed"]),
        "worldId": 1,
        "bounds": bounds,
        "encoding": ["cellX", "cellY", "E=1 N=2 W=4 S=8"],
        "cells": cells,
        "cellCount": len(cells),
        "waterCells": water,
        "waterCellCount": len(water),
        "desertCells": desert,
        "desertCellCount": len(desert),
        "burntForestCells": burnt_forest,
        "burntForestCellCount": len(burnt_forest),
        "autumnForestCells": autumn_forest,
        "autumnForestCellCount": len(autumn_forest),
        "schematicStationCells": schematic_stations,
        "schematicStationCount": len(schematic_stations),
        "_builderQuestPlacements": builder_quest_placements,
        "_resourcePitPlacements": resource_pit_placements,
        "roadConnectedLargePoiCells": road_connected_large_pois,
        "prisonerCampCells": prisoner_camps,
        "prisonerCampCount": len(prisoner_camps),
        "ruinCells": ruins,
        "ruinCount": len(ruins),
        "source": f"{save_path}:ScriptData/terrain/world-1",
        "message": (
            f"Read {len(cells)} exact engine-generated road cells directly "
            "from the selected save."
        ),
    }


def readable_poi_name(poi_type: str) -> str:
    overrides = {
        "POI_MECHANICSTATION_QUEST_MEDIUM": "Quest mechanic station",
        "POI_PACKINGSTATIONVEG_MEDIUM": "Vegetable packing station",
        "POI_PACKINGSTATIONFRUIT_MEDIUM": "Fruit packing station",
        "POI_BUILDERQUEST_WOCHOUSE": "Builder quest: Woc house",
        "POI_BUILDERQUEST_RESOURCECAR": "Builder quest: resource car",
        "POI_BUILDERQUEST_CARDBOARDPOOP": "Builder quest: cardboard poop",
        "POI_BURNTFOREST_BUILDERQUEST_TOTEBOTKEY": "Builder quest: Totebot key",
        "POI_FIELD_BUILDERQUEST_CORNHEART": "Builder quest: corn heart",
        "POI_FIELD_BUILDERQUEST_COZYBED": "Builder quest: cozy bed",
        "POI_BUILDERQUEST_XYLOPHONE": "Builder quest: xylophone",
        "POI_BUILDERQUEST_BEESUIT": "Builder quest: bee suit",
        "POI_DESERT_BUILDERQUEST_BIGFAN": "Builder quest: big fan",
        "POI_BUILDERQUEST_CAROUSEL": "Builder quest: carousel",
        "POI_BURNTFOREST_BUILDERQUEST_CATAPULT_MEDIUM": "Builder quest: catapult",
        "POI_BUILDERQUEST_CROWBAR": "Builder quest: crowbar",
        "POI_BUILDERQUEST_COMPASS": "Builder quest: compass",
        "POI_DESERT_BUILDERQUEST_GARDEN": "Builder quest: garden",
        "POI_FOREST_BUILDERQUEST_SAWBLADEARM": "Builder quest: sawblade arm",
        "POI_AUTUMNFOREST_BUILDERQUEST_POPCORN": "Builder quest: popcorn",
        "POI_AUTUMNFOREST_BUILDERQUEST_MUSICBOX_MEDIUM": "Builder quest: music box",
        "POI_BUILDERQUEST_NICEHOUSE_MEDIUM": "Builder quest: nice house",
        "POI_BUILDERQUEST_SLEDGEHAMMER_MEDIUM": "Builder quest: sledgehammer",
        "POI_BUILDERQUEST_STEELBRIDGE_MEDIUM": "Builder quest: steel bridge",
        "POI_BUILDERQUEST_BAGUETTE_MEDIUM": "Builder quest: baguette",
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


def persisted_tileson_uuid(tileson_path: Path) -> str | None:
    """Return a terrain UUID in the byte order stored by the save."""
    try:
        document = json.loads(tileson_path.read_text(encoding="utf-8-sig"))
        value = document.get("info", {}).get("uuid")
        if not isinstance(value, str):
            return None
        uuid_bytes = bytes.fromhex(value.replace("-", ""))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return uuid_bytes[::-1].hex() if len(uuid_bytes) == 16 else None


def load_schematic_station_uids(game_path: Path) -> set[str]:
    tile_directory = game_path / "Survival" / "Terrain" / "Tiles" / "poi"
    uids = {
        uid
        for path in tile_directory.glob("SchematicStation*.tileson")
        if (uid := persisted_tileson_uuid(path)) is not None
    }
    return uids or {SCHEMATIC_STATION_UID_RAW}


def load_resource_pit_tile_specs(game_path: Path) -> dict[str, dict]:
    """Map exact installed chemical/oil pit tiles to persisted UUIDs."""
    tile_directory = game_path / "Survival" / "Terrain" / "Tiles" / "poi"
    families = {
        "ChemicalLake*.tileson": (
            "POI_CHEMLAKE_MEDIUM",
            "Chemical pit",
            "chemical",
        ),
        "ChemicalPlant*.tileson": (
            "POI_ROAD_CHEMPOOL",
            "Chemical pit",
            "chemical",
        ),
        "OilLake*.tileson": (
            "POI_OILLAKE_MEDIUM",
            "Crude oil pit",
            "oil",
        ),
        "OilPool*.tileson": (
            "POI_DESERT_OILPOOL",
            "Crude oil pit",
            "oil",
        ),
    }
    specs = {}
    for pattern, (poi_type, title, resource) in families.items():
        for path in tile_directory.glob(pattern):
            try:
                document = json.loads(path.read_text(encoding="utf-8-sig"))
                info = document.get("info", {})
                size_x = int(info.get("cellsX", 0))
                size_y = int(info.get("cellsY", 0))
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            uid = persisted_tileson_uuid(path)
            if uid and size_x == size_y and size_x in {1, 2}:
                specs[uid] = {
                    "poiType": poi_type,
                    "title": title,
                    "resource": resource,
                    "sizeCells": size_x,
                    "developerTile": path.stem,
                }
    return specs


def load_builder_quest_tile_specs(game_path: Path) -> dict[str, dict]:
    """Map persisted tile UUIDs to dynamically placed builder quests."""
    generator_path = (
        game_path
        / "Survival"
        / "Scripts"
        / "terrain"
        / "overworld"
        / "generate_cells.lua"
    )
    if not generator_path.is_file():
        return {}
    text = generator_path.read_text(encoding="utf-8", errors="replace")
    start = text.find("local mustHavePois")
    end = text.find("--", start + len("local mustHavePois"))
    section = text[start:end] if start >= 0 and end > start else ""
    pattern = re.compile(
        r"mustHavePois\[#mustHavePois\s*\+\s*1\]\s*=\s*\{\s*"
        r"type\s*=\s*(POI_[A-Z0-9_]*BUILDERQUEST[A-Z0-9_]*)"
        r"(?P<rest>[^}]*)\}"
    )
    tile_mappings = load_poi_tile_mappings(game_path)
    specs = {}
    for match in pattern.finditer(section):
        poi_type = match.group(1)
        size_match = re.search(r"\bsize\s*=\s*(\d+)", match.group("rest"))
        virtual_path = tile_mappings.get(poi_type)
        if not size_match or not virtual_path:
            continue
        relative = virtual_path.replace("$SURVIVAL_DATA/", "")
        tileson_path = game_path / "Survival" / Path(relative).with_suffix(".tileson")
        uid = persisted_tileson_uuid(tileson_path)
        if uid:
            specs[uid] = {
                "poiType": poi_type,
                "sizeCells": int(size_match.group(1)),
                "virtualTile": virtual_path,
            }
    return specs


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

    for feature in features:
        if feature.get("poiType") in FIXED_BUILDER_QUEST_TYPES:
            feature["mapLayer"] = "builder-quests"

    excavation_origin = re.search(
        r"ExcavationIsland\s*=\s*\{\s*x\s*=\s*(-?\d+)\s*,\s*y\s*=\s*(-?\d+)",
        generator_text,
    )
    entrance_features = []
    for feature in features:
        entrance = UNDERGROUND_ENTRANCE_TYPES.get(feature.get("poiType"))
        if entrance:
            title, entrance_system = entrance
            entrance_feature = dict(feature)
            entrance_feature["id"] = f"underground-entrance-{feature['id']}"
            entrance_feature["mapLayer"] = "underground-entrances"
            entrance_feature["title"] = title
            entrance_feature["undergroundEntrance"] = True
            entrance_feature["undergroundSystem"] = entrance_system
            entrance_feature["undergroundMapStatus"] = "planned"
            entrance_feature["undergroundMessage"] = UNDERGROUND_ENTRANCE_MESSAGE
            entrance_features.append(entrance_feature)

    if excavation_origin:
        island_x, island_y = (int(value) for value in excavation_origin.groups())
        cell_x, cell_y, size = island_x + 16, island_y + 16, 32
        entrance_features.append(
            {
                "id": "underground-entrance-poi-excavation",
                "kind": "poi",
                "mapLayer": "underground-entrances",
                "poiType": "POI_EXCAVATION",
                "title": "Excavation underground entrance",
                "cellX": cell_x,
                "cellY": cell_y,
                "x": (cell_x + size / 2) * CELL_SIZE_METERS,
                "y": (cell_y + size / 2) * CELL_SIZE_METERS,
                "sizeCells": size,
                "rotation": None,
                "roadRequired": None,
                "confidence": "confirmed",
                "visibilityClass": "generator-known",
                "discoveryStatus": "unknown",
                "source": "Survival/Scripts/terrain/overworld/generate_cells.lua",
                "details": "Generator-defined excavation island area.",
                "developerLabel": "POI_EXCAVATION",
                "tile": None,
                "undergroundEntrance": True,
                "undergroundSystem": "EXCAVATION",
                "undergroundMapStatus": "planned",
                "undergroundMessage": UNDERGROUND_ENTRANCE_MESSAGE,
            }
        )

    features.extend(entrance_features)

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


def migrate_mapper_data(save_data: dict) -> None:
    """Copy mapper-owned user data from an older mutable save identity."""
    target_dir = MAPPER_DATA_DIR / save_data["identity"]
    candidates = []
    if MAPPER_DATA_DIR.is_dir():
        for state_path in MAPPER_DATA_DIR.glob("*/state.json"):
            if state_path.parent == target_dir:
                continue
            try:
                document = json.loads(state_path.read_text(encoding="utf-8"))
                old_save = document.get("save", {})
                if (
                    old_save.get("filename", "").casefold()
                    == save_data["filename"].casefold()
                    and int(old_save.get("seed", -1)) == int(save_data["seed"])
                    and old_save.get("owner", "").casefold()
                    == save_data["owner"].casefold()
                ):
                    candidates.append(state_path.parent)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
    for filename in ("markers.json", "discoveries.json"):
        target = target_dir / filename
        if target.is_file():
            continue
        sources = [
            directory / filename
            for directory in candidates
            if (directory / filename).is_file()
        ]
        if not sources:
            continue
        source = max(sources, key=lambda path: path.stat().st_mtime_ns)
        target_dir.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_bytes(source.read_bytes())
        temporary.replace(target)


def read_underground_progression(path: Path, game_path: Path) -> dict:
    """Read underground world mapping, access cards, Vault total, and floor cells."""
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")

        def load_channel(channel: int):
            row = connection.execute(
                "SELECT data FROM ScriptData WHERE uid = ? AND key = ? LIMIT 1",
                (GLOBAL_STORAGE_UID, global_storage_key(channel)),
            ).fetchone()
            return decode_lua_object(bytes(row[0])) if row else {}

        logs = load_channel(60)
        progression = load_channel(79)
        world_refs = load_channel(41)
        owned_logs = set(logs.values()) if isinstance(logs, dict) else set()
        owned_cards = [
            tier for tier, identifier in ACCESS_CARD_UUIDS.items()
            if identifier in owned_logs
        ]
        reached = progression.get("reachedUndergroundDepths", {})
        reached_depths = {
            int(depth) for depth, value in reached.items() if value is True
        } if isinstance(reached, dict) else set()
        vault_total = int(progression.get("vaultTotal", 0))
        worlds = {
            int(depth): int(reference["id"])
            for depth, reference in world_refs.items()
            if isinstance(reference, dict) and "id" in reference
        } if isinstance(world_refs, dict) else {}

        floors = []
        for depth, name, card_tier in UNDERGROUND_DEPTHS:
            world_id = worlds.get(depth)
            generated = world_id is not None
            accessible = card_tier in owned_cards if card_tier is not None else depth in reached_depths
            world_file = game_path / "Survival" / "Terrain" / "Worlds" / UNDERGROUND_WORLD_FILES[depth]
            cells = []
            if world_file.is_file():
                document = json.loads(world_file.read_text(encoding="utf-8-sig"))
                cells = [
                    {"x": int(cell["x"]), "y": int(cell["y"]), "authored": bool(cell.get("path"))}
                    for cell in document.get("cellData", [])
                ]
            voxel_cells = []
            resources = []
            if generated:
                voxel_cells = [
                    {"x": int(x), "y": int(y), "recordCount": int(count)}
                    for x, y, count in connection.execute(
                        "SELECT x, y, COUNT(*) FROM VoxelTerrain WHERE worldId = ? "
                        "GROUP BY x, y ORDER BY x, y",
                        (world_id,),
                    )
                ]
                quartz_rows = list(connection.execute(
                    "SELECT rowid, x, y FROM Harvestable WHERE worldId = ? AND instr(data, ?) > 0 "
                    "ORDER BY x, y, rowid",
                    (world_id, uuid.UUID(QUARTZ_HARVESTABLE_UUID).bytes[::-1]),
                ))
                quartz_per_cell = {}
                for _, cell_x, cell_y in quartz_rows:
                    key = (int(cell_x), int(cell_y))
                    index = quartz_per_cell.get(key, 0)
                    quartz_per_cell[key] = index + 1
                    offsets = ((0.0, 0.0), (-0.20, -0.16), (0.20, 0.16), (-0.20, 0.18), (0.20, -0.18))
                    offset_x, offset_y = offsets[index % len(offsets)]
                    resources.append({
                        "kind": "quartz",
                        "name": "Quartz formation",
                        "quantity": 3,
                        "quantityLabel": "3 Quartz when harvested",
                        "tool": "Hammer or plasma drill",
                        "cellX": key[0],
                        "cellY": key[1],
                        "mapX": key[0] + 0.5 + offset_x,
                        "mapY": key[1] + 0.5 + offset_y,
                        "positionAccuracy": "Saved cell (marker position within the cell is approximate)",
                    })

                chunk_needles = {
                    uuid.UUID(identifier).bytes[::-1]: label
                    for identifier, label in UNDERGROUND_CHUNK_SHAPES.items()
                }
                for shape_id, controller_id, min_x, max_x, min_y, max_y, shape_data in connection.execute(
                    "SELECT s.id, c.id, b.minX, b.maxX, b.minY, b.maxY, s.data "
                    "FROM ChildShape s JOIN RigidBody r ON r.id = s.bodyId "
                    "JOIN RigidBodyBounds b ON b.id = r.id JOIN Controller c ON c.hostId = s.id "
                    "WHERE r.worldId = ?",
                    (world_id,),
                ):
                    chunk_name = next(
                        (label for needle, label in chunk_needles.items() if needle in bytes(shape_data)),
                        None,
                    )
                    if not chunk_name:
                        continue
                    storage = connection.execute(
                        "SELECT data FROM ScriptData WHERE worldId = ? AND key = ? LIMIT 1",
                        (world_id, int(controller_id).to_bytes(4, "little")),
                    ).fetchone()
                    if not storage:
                        continue
                    decoded = decode_lua_object(bytes(storage[0]))
                    material_uuid = str(decoded.get("uuid", "")) if isinstance(decoded, dict) else ""
                    quantity = int(decoded.get("quantity", 0)) if isinstance(decoded, dict) else 0
                    world_x = (float(min_x) + float(max_x)) / 2
                    world_y = (float(min_y) + float(max_y)) / 2
                    resources.append({
                        "kind": "tier1",
                        "name": chunk_name,
                        "material": UNDERGROUND_MATERIALS.get(material_uuid, material_uuid or "Unknown material"),
                        "quantity": quantity,
                        "quantityLabel": f"Saved material quantity: {quantity}",
                        "tool": "Plasma drill required",
                        "cellX": math.floor(world_x / CELL_SIZE_METERS),
                        "cellY": math.floor(world_y / CELL_SIZE_METERS),
                        "mapX": world_x / CELL_SIZE_METERS,
                        "mapY": world_y / CELL_SIZE_METERS,
                        "worldX": world_x,
                        "worldY": world_y,
                        "positionAccuracy": "Exact saved rigid-body position",
                        "shapeId": int(shape_id),
                    })
            target = VAULT_CARD_TARGETS.get(card_tier) if card_tier not in owned_cards else None
            floors.append({
                "depth": depth,
                "name": name,
                "worldId": world_id,
                "generated": generated,
                "accessible": accessible,
                "reached": depth in reached_depths,
                "requiredCard": card_tier,
                "vaultTarget": target,
                "cells": cells,
                "voxelCells": voxel_cells,
                "resources": resources,
                "resourceSummary": {
                    "markers": len(resources),
                    "quartzFormations": sum(item["kind"] == "quartz" for item in resources),
                    "quartzYield": sum(item["quantity"] for item in resources if item["kind"] == "quartz"),
                    "looseOreChunks": sum(item["kind"] == "tier1" for item in resources),
                },
            })
        next_card = next((tier for tier in (2, 3, 4) if tier not in owned_cards), None)
        next_target = VAULT_CARD_TARGETS.get(next_card)
        return {
            "status": "available",
            "vaultTotal": vault_total,
            "nextCard": next_card,
            "nextVaultTarget": next_target,
            "vaultRemaining": max(0, next_target - vault_total) if next_target else 0,
            "ownedCards": owned_cards,
            "reachedDepths": sorted(reached_depths),
            "floors": floors,
            "generatedCount": sum(floor["generated"] for floor in floors),
        }
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, sqlite3.OperationalError) as error:
        return {
            "status": "unavailable",
            "message": f"Underground progression has an unsupported format: {error}",
            "floors": [],
        }
    finally:
        connection.close()


def read_saved_vehicles(path: Path) -> dict:
    """Read movable overworld creations that match a vehicle signature."""
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        bodies = {
            int(body_id): {
                "worldId": int(world_id),
                "movable": len(data) > 1 and data[1] == 2,
            }
            for body_id, world_id, data in connection.execute(
                "SELECT id, worldId, data FROM RigidBody"
            )
        }
        shape_bodies = {
            int(shape_id): int(body_id)
            for shape_id, body_id in connection.execute(
                "SELECT id, bodyId FROM ChildShape"
            )
        }
        graph = {body_id: set() for body_id in bodies}
        suspension_joints: list[tuple[int | None, int | None, str]] = []
        for shape_a, shape_b, data in connection.execute(
            "SELECT childShapeIdA, childShapeIdB, data FROM Joint"
        ):
            body_a = shape_bodies.get(int(shape_a)) if shape_a is not None else None
            body_b = shape_bodies.get(int(shape_b)) if shape_b is not None else None
            label = (
                SUSPENSION_UUID_BYTES.get(data[15:31])
                if data is not None and len(data) >= 31
                else None
            )
            if label:
                suspension_joints.append((body_a, body_b, label))
            if body_a is not None and body_b is not None and body_a != body_b:
                # Fixed bodies terminate the movable creation graph. This
                # prevents an adjacent world/lift body from making a vehicle
                # itself appear anchored.
                if bodies[body_a]["movable"] and bodies[body_b]["movable"]:
                    graph[body_a].add(body_b)
                    graph[body_b].add(body_a)

        engines_by_body: dict[int, list[str]] = {}
        driver_seats_by_body: dict[int, list[str]] = {}
        for body_id, data in connection.execute("SELECT bodyId, data FROM ChildShape"):
            if len(data) < 27:
                continue
            identifier = data[11:27]
            engine_label = ENGINE_UUID_BYTES.get(identifier)
            if engine_label:
                engines_by_body.setdefault(int(body_id), []).append(engine_label)
            seat_label = DRIVER_SEAT_UUID_BYTES.get(identifier)
            if seat_label:
                driver_seats_by_body.setdefault(int(body_id), []).append(seat_label)

        visited: set[int] = set()
        vehicles = []
        candidate_bodies = set(engines_by_body) | set(driver_seats_by_body)
        for candidate_body in candidate_bodies:
            if candidate_body in visited:
                continue
            if not bodies.get(candidate_body, {}).get("movable"):
                visited.add(candidate_body)
                continue
            component = set()
            pending = [candidate_body]
            while pending:
                body_id = pending.pop()
                if body_id in component:
                    continue
                component.add(body_id)
                pending.extend(graph.get(body_id, ()))
            visited.update(component)
            component_engines = [
                label
                for body_id in component
                for label in engines_by_body.get(body_id, ())
            ]
            component_driver_seats = [
                label
                for body_id in component
                for label in driver_seats_by_body.get(body_id, ())
            ]
            component_suspensions = [
                label
                for body_a, body_b, label in suspension_joints
                if body_a in component or body_b in component
            ]
            component_bodies = [bodies[body_id] for body_id in component if body_id in bodies]
            suspension_vehicle = bool(
                component_driver_seats and component_suspensions
            )
            if not (component_engines or suspension_vehicle) or not component_bodies:
                continue
            if any(body["worldId"] != 1 for body in component_bodies):
                continue
            # Type 2 is a freely simulated rigid body. Type 1 is fixed to the
            # world. Fixed bodies have already been excluded from traversal,
            # including fixed lift/world neighbors.
            placeholders = ",".join("?" for _ in component)
            bounds = connection.execute(
                f"SELECT min(minX), max(maxX), min(minY), max(maxY) "
                f"FROM RigidBodyBounds WHERE id IN ({placeholders})",
                tuple(component),
            ).fetchone()
            if bounds is None or any(value is None for value in bounds):
                continue
            min_x, max_x, min_y, max_y = map(float, bounds)
            engine_counts = {
                label: component_engines.count(label)
                for label in sorted(set(component_engines))
            }
            suspension_counts = {
                label: component_suspensions.count(label)
                for label in sorted(set(component_suspensions))
            }
            details = ", ".join(
                f"{label} x{count}" if count > 1 else label
                for label, count in engine_counts.items()
            )
            if not details:
                seat_counts = {
                    label: component_driver_seats.count(label)
                    for label in sorted(set(component_driver_seats))
                }
                details = ", ".join(
                    f"{label} x{count}" if count > 1 else label
                    for label, count in seat_counts.items()
                ) + " + " + ", ".join(
                    f"{label} x{count}" if count > 1 else label
                    for label, count in suspension_counts.items()
                )
            vehicles.append(
                {
                    "id": f"vehicle-{min(component)}",
                    "x": (min_x + max_x) / 2,
                    "y": (min_y + max_y) / 2,
                    "worldId": 1,
                    "bodyCount": len(component),
                    "engineCount": len(component_engines),
                    "engineTypes": engine_counts,
                    "driverSeatCount": len(component_driver_seats),
                    "suspensionCount": len(component_suspensions),
                    "suspensionTypes": suspension_counts,
                    "detectionType": (
                        "engine" if component_engines else "driver-seat-suspension"
                    ),
                    "details": details,
                }
            )
        vehicles.sort(key=lambda item: item["id"])
        return {
            "status": "available",
            "vehicles": vehicles,
            "count": len(vehicles),
            "message": f"Found {len(vehicles)} movable vehicle-like creations.",
        }
    except sqlite3.OperationalError as error:
        return {
            "status": "unavailable",
            "vehicles": [],
            "count": 0,
            "message": f"Vehicle records are unavailable: {error}",
        }
    finally:
        connection.close()


def build_state(game_path: Path, user_dirs: list[Path], saves: list[Path], selected: Path) -> dict:
    save_data = inspect_save_read_only(selected)
    LOGGER.info(
        "Map refresh identity=%s seed=%s availableSaves=%s integrity=verified.",
        save_data["identity"],
        save_data["seed"],
        len(saves),
    )
    migrate_mapper_data(save_data)
    saved_position = read_saved_player_position(selected)
    saved_beacons = read_saved_beacons(selected)
    saved_vehicles = read_saved_vehicles(selected)
    underground = read_underground_progression(selected, game_path)
    confirmed_map = inspect_generator_confirmed_map(game_path)
    roads = load_exact_roads(selected, save_data, game_path)
    builder_quest_placements = roads.pop("_builderQuestPlacements", [])
    resource_pit_placements = roads.pop("_resourcePitPlacements", [])
    for cell_x, cell_y in roads.get("schematicStationCells", []):
        confirmed_map["features"].append(
            {
                "id": f"schematic-station-{cell_x}-{cell_y}",
                "kind": "poi",
                "mapLayer": "warehouse-schematics",
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
                "source": "persisted selected-save terrain",
                "details": "Exact Schematic Station read from the generated overworld terrain.",
                "developerLabel": "POI_ROAD_SCHEMATICSTATION",
                "tile": None,
            }
        )
    for placement in builder_quest_placements:
        cell_x = placement["cellX"]
        cell_y = placement["cellY"]
        size = placement["sizeCells"]
        poi_type = placement["poiType"]
        confirmed_map["features"].append(
            {
                "id": f"builder-quest-{poi_type.casefold()}-{cell_x}-{cell_y}",
                "kind": "poi",
                "mapLayer": "builder-quests",
                "poiType": poi_type,
                "title": readable_poi_name(poi_type),
                "cellX": cell_x,
                "cellY": cell_y,
                "x": (cell_x + size / 2) * CELL_SIZE_METERS,
                "y": (cell_y + size / 2) * CELL_SIZE_METERS,
                "sizeCells": size,
                "rotation": None,
                "roadRequired": False,
                "confidence": "confirmed",
                "visibilityClass": "generator-known",
                "discoveryStatus": "unknown",
                "source": "persisted selected-save terrain",
                "details": "Exact builder quest read from the generated overworld terrain.",
                "developerLabel": poi_type,
                "tile": tile_reference(game_path, placement["virtualTile"]),
            }
        )
    for placement in resource_pit_placements:
        cell_x = placement["cellX"]
        cell_y = placement["cellY"]
        size = placement["sizeCells"]
        poi_type = placement["poiType"]
        confirmed_map["features"].append(
            {
                "id": f"resource-pit-{placement['developerTile'].casefold()}-{cell_x}-{cell_y}",
                "kind": "poi",
                "mapLayer": "chemical-oil-pits",
                "renderShape": "circle",
                "poiType": poi_type,
                "title": placement["title"],
                "resourceType": placement["resource"],
                "cellX": cell_x,
                "cellY": cell_y,
                "x": (cell_x + size / 2) * CELL_SIZE_METERS,
                "y": (cell_y + size / 2) * CELL_SIZE_METERS,
                "sizeCells": size,
                "rotation": None,
                "roadRequired": None,
                "confidence": "confirmed",
                "visibilityClass": "generator-known",
                "discoveryStatus": "unknown",
                "source": "persisted selected-save terrain",
                "details": "Exact chemical or crude-oil pit read from the generated overworld terrain.",
                "developerLabel": poi_type,
                "developerTile": placement["developerTile"],
                "tile": None,
            }
        )
    fixed_large_poi_origins = {
        (feature["cellX"] - 2, feature["cellY"] - 2)
        for feature in confirmed_map["features"]
        if feature.get("poiType") in {"POI_CAMP_LARGE", "POI_WAREHOUSE4_QUEST_LARGE"}
        and feature.get("sizeCells") == 4
    }
    warehouse_cells = [
        cell
        for cell in roads.get("roadConnectedLargePoiCells", [])
        if tuple(cell) not in fixed_large_poi_origins
    ]
    roads["warehouseCells"] = warehouse_cells
    roads["warehouseCount"] = len(warehouse_cells)
    for cell_x, cell_y in warehouse_cells:
        size = 4
        confirmed_map["features"].append(
            {
                "id": f"regular-warehouse-{cell_x}-{cell_y}",
                "kind": "poi",
                "mapLayer": "warehouse-schematics",
                "poiType": "POI_WAREHOUSE_REGULAR_LARGE",
                "title": "Regular warehouse",
                "cellX": cell_x,
                "cellY": cell_y,
                "x": (cell_x + size / 2) * CELL_SIZE_METERS,
                "y": (cell_y + size / 2) * CELL_SIZE_METERS,
                "sizeCells": size,
                "rotation": None,
                "roadRequired": True,
                "confidence": "confirmed",
                "visibilityClass": "generator-known",
                "discoveryStatus": "unknown",
                "source": "persisted selected-save terrain",
                "details": "Exact regular Warehouse read from the generated overworld terrain.",
                "developerLabel": "POI_WAREHOUSE_REGULAR_LARGE",
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

    state = {
        "schemaVersion": 13,
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
                    else "Persisted water terrain is unavailable for this save."
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
                    else "Persisted desert terrain is unavailable for this save."
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
                    else "Persisted burnt-forest terrain is unavailable for this save."
                ),
            },
            "autumnForest": {
                "status": (
                    "available"
                    if roads.get("autumnForestCells")
                    else "unavailable"
                ),
                "cells": roads.get("autumnForestCells", []),
                "cellCount": roads.get("autumnForestCellCount", 0),
                "message": (
                    f"Loaded {roads.get('autumnForestCellCount', 0)} exact autumn-forest cells."
                    if roads.get("autumnForestCells")
                    else "Persisted autumn-forest terrain is unavailable for this save."
                ),
            },
            "markers": markers,
            "physicalBeacons": saved_beacons,
            "vehicles": saved_vehicles,
        },
        "playerPosition": saved_position,
        "underground": underground,
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
                "label": "Terrain regions (water / desert / burnt forest / autumn forest)",
                "available": any(
                    (
                        roads.get("waterCells"),
                        roads.get("desertCells"),
                        roads.get("burntForestCells"),
                        roads.get("autumnForestCells"),
                    )
                ),
                "visible": False,
            },
            {
                "id": "anchors",
                "label": "All POIs / anchors (spoilers)",
                "available": any(
                    feature.get("mapLayer")
                    not in {"warehouse-schematics", "builder-quests"}
                    for feature in confirmed_map["features"]
                ),
                "visible": False,
            },
            {
                "id": "warehouse-schematics",
                "label": "Warehouses & schematic stations (spoilers)",
                "available": any(
                    feature.get("mapLayer") == "warehouse-schematics"
                    for feature in confirmed_map["features"]
                ),
                "visible": False,
            },
            {
                "id": "builder-quests",
                "label": "Builder Quests",
                "available": any(
                    feature.get("mapLayer") == "builder-quests"
                    for feature in confirmed_map["features"]
                ),
                "visible": False,
            },
            {
                "id": "chemical-oil-pits",
                "label": "Chemical & Oil Pits",
                "available": any(
                    feature.get("mapLayer") == "chemical-oil-pits"
                    for feature in confirmed_map["features"]
                ),
                "visible": False,
            },
            {
                "id": "underground-entrances",
                "label": "Underground entrances (spoilers)",
                "available": any(
                    feature.get("mapLayer") == "underground-entrances"
                    for feature in confirmed_map["features"]
                ),
                "visible": False,
            },
            {
                "id": "prisoner-camps",
                "label": "Prisoner camps",
                "available": roads["status"] == "available",
                "visible": False,
            },
            {
                "id": "ruins",
                "label": "Ruins",
                "available": roads["status"] == "available",
                "visible": False,
            },
            {
                "id": "beacons",
                "label": "Physical beacons",
                "available": saved_beacons["status"] == "available"
                and saved_beacons["overworldCount"] > 0,
                "visible": False,
            },
            {
                "id": "vehicles",
                "label": "Vehicles (engines or seat + suspension)",
                "available": saved_vehicles["status"] == "available"
                and saved_vehicles["count"] > 0,
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
    LOGGER.info(
        "Map state ready identity=%s seed=%s roads=%s.",
        save_data["identity"],
        save_data["seed"],
        roads.get("cellCount", 0),
    )
    return state


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
 
    def refresh_saves(self) -> None:
        refreshed = discover_saves(self.user_dirs)
        if refreshed:
            self.saves = refreshed

    def generate(self) -> dict:
        with self.lock:
            self.refresh_saves()
            state = build_state(
                self.game_path, self.user_dirs, self.saves, self.selected
            )
            write_state(state)
            return state

    def select(self, identity: str) -> dict:
        with self.lock:
            self.refresh_saves()
            candidate = next(
                (
                    path
                    for path in self.saves
                    if read_save_identity(path)["id"] == identity
                ),
                None,
            )
            if candidate is None:
                raise ValueError(
                    "That save changed or moved after the map loaded. "
                    "Refresh the map and try again."
                )
            self.selected = candidate
            state = build_state(
                self.game_path, self.user_dirs, self.saves, self.selected
            )
            write_state(state)
            return state

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

    def select_seed(self, seed: int) -> dict:
        with self.lock:
            self.refresh_saves()
            candidate = next(
                (
                    path
                    for path in self.saves
                    if int(read_save_identity(path)["seed"]) == int(seed)
                ),
                None,
            )
            if candidate is None:
                raise ValueError(
                    f"No Survival save with seed {seed} was found. Keep the save "
                    "in the normal Survival save folder and choose Open map again."
                )
            self.selected = candidate
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

        def end_headers(self) -> None:
            if not urlsplit(self.path).path.startswith("/api/"):
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, format: str, *args) -> None:
            LOGGER.info(
                "HTTP method=%s path=%s.",
                self.command,
                urlsplit(self.path).path,
            )

        def do_GET(self) -> None:
            if self.path != "/api/status":
                super().do_GET()
                return
            response = json.dumps(
                {
                    "ok": True,
                    "service": "jc-scrapmap",
                    "instanceId": INSTANCE_ID,
                    "version": APP_VERSION,
                }
            ).encode("utf-8")
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
                "/api/select-seed",
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
                elif self.path == "/api/select-seed":
                    seed = payload.get("seed")
                    if not isinstance(seed, int):
                        raise ValueError("Missing requested world seed.")
                    state = session.select_seed(seed)
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
                LOGGER.info(
                    "API action=%s result=ok identity=%s.",
                    self.path,
                    state["save"]["identity"],
                )
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
                LOGGER.warning(
                    "API action=%s result=error category=%s.",
                    self.path,
                    type(error).__name__,
                )

    return ScrapMapRequestHandler


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    """Keep harmless browser disconnects out of the player-facing console."""

    def handle_error(self, request, client_address) -> None:
        error = sys.exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def overlay_browser_definitions() -> tuple[dict[str, object], ...]:
    """Return supported Chromium-family browsers and their usual Windows paths."""

    locations = {
        name: Path(value)
        for name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")
        if (value := os.environ.get(name))
    }

    def paths(*items: tuple[str, str]) -> tuple[Path, ...]:
        return tuple(
            locations[root] / relative
            for root, relative in items
            if root in locations
        )

    return (
        {
            "id": "chrome",
            "name": "Google Chrome",
            "paths": paths(
                ("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"),
                ("PROGRAMFILES(X86)", "Google/Chrome/Application/chrome.exe"),
                ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe"),
            ),
        },
        {
            "id": "brave",
            "name": "Brave",
            "paths": paths(
                ("PROGRAMFILES", "BraveSoftware/Brave-Browser/Application/brave.exe"),
                ("PROGRAMFILES(X86)", "BraveSoftware/Brave-Browser/Application/brave.exe"),
                ("LOCALAPPDATA", "BraveSoftware/Brave-Browser/Application/brave.exe"),
            ),
        },
        {
            "id": "vivaldi",
            "name": "Vivaldi",
            "paths": paths(
                ("PROGRAMFILES", "Vivaldi/Application/vivaldi.exe"),
                ("PROGRAMFILES(X86)", "Vivaldi/Application/vivaldi.exe"),
                ("LOCALAPPDATA", "Vivaldi/Application/vivaldi.exe"),
            ),
        },
        {
            "id": "chromium",
            "name": "Chromium",
            "paths": paths(
                ("PROGRAMFILES", "Chromium/Application/chrome.exe"),
                ("PROGRAMFILES(X86)", "Chromium/Application/chrome.exe"),
                ("LOCALAPPDATA", "Chromium/Application/chrome.exe"),
            ),
        },
        {
            "id": "opera",
            "name": "Opera",
            "paths": paths(
                ("PROGRAMFILES", "Opera/launcher.exe"),
                ("PROGRAMFILES(X86)", "Opera/launcher.exe"),
                ("LOCALAPPDATA", "Programs/Opera/launcher.exe"),
            ),
        },
        {
            "id": "edge",
            "name": "Microsoft Edge",
            "paths": paths(
                ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe"),
                ("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"),
                ("LOCALAPPDATA", "Microsoft/Edge/Application/msedge.exe"),
            ),
        },
    )


def discover_overlay_browsers() -> list[dict[str, str]]:
    browsers: list[dict[str, str]] = []
    seen: set[str] = set()
    for definition in overlay_browser_definitions():
        browser_path = next(
            (path for path in definition["paths"] if path.is_file()),
            None,
        )
        if browser_path is None:
            continue
        normalized = str(browser_path.resolve()).casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        browsers.append(
            {
                "id": str(definition["id"]),
                "name": str(definition["name"]),
                "path": str(browser_path.resolve()),
            }
        )
    return browsers


def load_overlay_browser_preference(
    settings_path: Path = OVERLAY_SETTINGS_PATH,
) -> dict[str, str] | None:
    try:
        value = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(value, dict):
        return None
    browser_path = value.get("path")
    if not isinstance(browser_path, str) or not Path(browser_path).is_file():
        return None
    return {
        "id": str(value.get("id", "custom")),
        "name": str(value.get("name", Path(browser_path).stem)),
        "path": str(Path(browser_path).resolve()),
    }


def save_overlay_browser_preference(
    browser: dict[str, str],
    settings_path: Path = OVERLAY_SETTINGS_PATH,
) -> None:
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(browser, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        LOGGER.warning("Could not remember the selected overlay browser.")


def choose_overlay_browser(
    browsers: list[dict[str, str]] | None = None,
    settings_path: Path = OVERLAY_SETTINGS_PATH,
    input_function=input,
) -> dict[str, str] | None:
    """Prompt for an overlay browser; None means ordinary default-browser mode."""

    available = list(browsers if browsers is not None else discover_overlay_browsers())
    preference = load_overlay_browser_preference(settings_path)
    if preference and all(
        Path(item["path"]).resolve() != Path(preference["path"]).resolve()
        for item in available
    ):
        available.append(preference)

    default_index = 0
    if preference:
        for index, browser in enumerate(available):
            if Path(browser["path"]).resolve() == Path(preference["path"]).resolve():
                default_index = index
                break

    print("\nJC ScrapMap overlay browser")
    print("Choose a detected Chromium-family browser:")
    for index, browser in enumerate(available, start=1):
        marker = " (default)" if index - 1 == default_index else ""
        print(f"  {index}. {browser['name']}{marker}")
    print("  M. Choose another Chromium-family browser executable")
    print("  N. Open the regular map in the default browser (not always-on-top)")

    while True:
        default_answer = str(default_index + 1) if available else "M"
        try:
            answer = input_function(f"Selection [{default_answer}]: ").strip()
        except EOFError as error:
            raise RuntimeError("Overlay browser selection was cancelled.") from error
        answer = answer or default_answer
        if answer.casefold() == "n":
            return None
        if answer.casefold() == "m":
            raw_path = input_function("Browser executable path: ").strip().strip('"')
            selected_path = Path(raw_path)
            if not selected_path.is_file() or selected_path.suffix.casefold() != ".exe":
                print("That browser executable was not found. Try again.")
                continue
            selected = {
                "id": "custom",
                "name": selected_path.stem,
                "path": str(selected_path.resolve()),
            }
            save_overlay_browser_preference(selected, settings_path)
            return selected
        if answer.isdigit() and 1 <= int(answer) <= len(available):
            selected = available[int(answer) - 1]
            save_overlay_browser_preference(selected, settings_path)
            return selected
        print("Enter one of the listed numbers, M, or N.")


def keep_overlay_topmost() -> None:
    if os.name != "nt":
        return
    import ctypes

    user32 = ctypes.windll.user32
    enum_callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    hwnd_topmost = ctypes.c_void_p(-1)
    flags = 0x0001 | 0x0002 | 0x0010

    def find_and_pin() -> bool:
        found = False

        def visit(hwnd, _lparam):
            nonlocal found
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                if title.value == "JC ScrapMap Overlay":
                    user32.SetWindowPos(hwnd, hwnd_topmost, 0, 0, 0, 0, flags)
                    found = True
                    return False
            return True

        user32.EnumWindows(enum_callback(visit), 0)
        return found

    for _ in range(100):
        if find_and_pin():
            return
        time.sleep(0.1)
    LOGGER.warning("Overlay window opened but could not be marked always-on-top.")


def launch_overlay(url: str) -> None:
    browser = choose_overlay_browser()
    if browser is None:
        LOGGER.info("Overlay launcher falling back to ordinary default-browser mode.")
        webbrowser.open(url)
        return
    overlay_url = f"{url}?overlay=1"
    LOGGER.info("Opening overlay with browser=%s.", browser["id"])
    try:
        subprocess.Popen([browser["path"], f"--app={overlay_url}"])
    except OSError as error:
        raise RuntimeError(
            f"Could not start the selected overlay browser: {browser['name']}."
        ) from error
    threading.Thread(target=keep_overlay_topmost, daemon=True).start()


def serve(session: ScrapMapSession, port: int, open_browser: bool, overlay: bool) -> None:
    server = QuietThreadingHTTPServer(
        ("127.0.0.1", port), make_request_handler(session)
    )
    url = f"http://127.0.0.1:{port}/web/index.html"
    LOGGER.info("Local map server ready url=%s.", url)
    LOGGER.info("Press Ctrl+C to stop the local server.")
    if overlay:
        launch_overlay(url)
    elif open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Stop requested from the live console.")
    finally:
        server.server_close()
        LOGGER.info("Local map server stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the offline JC ScrapMap application.")
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
    parser.add_argument(
        "--overlay",
        action="store_true",
        help="Open JC ScrapMap in an always-on-top companion window.",
    )
    parser.add_argument("--list-saves", action="store_true", help="List detected saves and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    log_path = configure_logging()
    LOGGER.info(
        "JC ScrapMap starting version=%s python=%s platform=%s.",
        APP_VERSION,
        sys.version.split()[0],
        sys.platform,
    )
    if log_path is not None:
        LOGGER.info("Rolling operational log enabled.")
    game_path = Path(args.game_path).expanduser().resolve() if args.game_path else default_game_path()
    user_root = Path(args.user_path).expanduser().resolve() if args.user_path else default_user_root()
    user_dirs = discover_user_directories(user_root)
    saves = discover_saves(user_dirs)
    LOGGER.info(
        "Auto-detection complete game=%s userProfiles=%s saves=%s.",
        "explicit" if args.game_path else "detected",
        len(user_dirs),
        len(saves),
    )

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

    selected_identity = read_save_identity(selected)
    LOGGER.info(
        "Selected save identity=%s seed=%s.",
        selected_identity["id"],
        selected_identity["seed"],
    )
    state = build_state(game_path, user_dirs, saves, selected)
    state_path = write_state(state)
    LOGGER.info(
        "Generated map state identity=%s readOnlyVerified=%s.",
        state["save"]["identity"],
        state["save"]["readOnlyVerified"],
    )

    if not args.no_server:
        session = ScrapMapSession(game_path, user_dirs, saves, selected)
        serve(session, args.port, not args.no_browser, args.overlay)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, sqlite3.DatabaseError, RuntimeError) as error:
        if LOGGER.handlers:
            LOGGER.error("Fatal application error category=%s.", type(error).__name__)
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
