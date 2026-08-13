"""Export structural summaries from persisted underground terrain data."""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
import uuid
from collections import Counter
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from terrain_reader import TerrainObjectReader, read_terrain_blob, unpack_script_data


def indexed_values(value: object) -> list:
    if not isinstance(value, dict):
        return []
    return [value[key] for key in sorted(value) if isinstance(key, int)]


def decoded_uuid(value: object) -> str | None:
    if not isinstance(value, dict) or value.get("type") != "uuid":
        return None
    serialized = bytes.fromhex(value["raw"])
    return str(uuid.UUID(bytes=serialized[::-1]))


def decode_cave(value: int, tiles: list[str | None]) -> dict:
    tile_index = value & 0xFF
    return {
        "tileIndex": tile_index,
        "tileUuid": tiles[tile_index - 1] if 0 < tile_index <= len(tiles) else None,
        "zChunk": (value >> 8) & 0xF,
        "heightChunks": ((value >> 12) & 0xF) + 1,
        "sourceOffsetX": (value >> 16) & 0x3,
        "sourceOffsetY": (value >> 18) & 0x3,
        "rotationQuarterTurns": (value >> 20) & 0x3,
    }


def decode_pocket(value: int, tiles: list[str | None]) -> dict:
    tile_index = value & 0xFF
    return {
        "tileIndex": tile_index,
        "tileUuid": tiles[tile_index - 1] if 0 < tile_index <= len(tiles) else None,
        "xChunkWithinCell": (value >> 8) & 0x3,
        "yChunkWithinCell": (value >> 10) & 0x3,
        "zChunk": (value >> 12) & 0xF,
        "sizeXChunks": ((value >> 16) & 0x3) + 1,
        "sizeYChunks": ((value >> 18) & 0x3) + 1,
        "sizeZChunks": ((value >> 20) & 0xF) + 1,
        "sourceOffsetX": (value >> 24) & 0x3,
        "sourceOffsetY": (value >> 26) & 0x3,
        "rotationQuarterTurns": (value >> 28) & 0x3,
    }


def populated_cells(grid: object, decoder, tiles: list[str | None]) -> list[dict]:
    result = []
    if not isinstance(grid, dict):
        return result
    for cell_y, row in grid.items():
        if not isinstance(cell_y, int) or not isinstance(row, dict):
            continue
        for cell_x, records in row.items():
            values = indexed_values(records)
            if values:
                result.append({
                    "cellX": cell_x,
                    "cellY": cell_y,
                    "records": [decoder(int(value), tiles) for value in values],
                })
    return result


def pocket_category(path: str | None) -> str:
    name = (path or "").casefold()
    if any(word in name for word in ("gold", "quartz", "tier1", "orerich", "coralium", "corralium", "nimbolium", "t3deposit", "crystal")):
        return "resource"
    if any(word in name for word in ("underwater", "dungeon", "minerbot", "drillspawner", "cablebots")):
        return "special"
    if "empty" in name or "passage" in name:
        return "passage"
    return "chamber"


def saved_voxel_cells(save_path: Path, world_id: int) -> list[dict]:
    uri = f"{save_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        return [
            {"cellX": int(x), "cellY": int(y), "recordCount": int(count)}
            for x, y, count in connection.execute(
                "SELECT x, y, COUNT(*) FROM VoxelTerrain WHERE worldId = ? GROUP BY x, y ORDER BY x, y",
                (world_id,),
            )
        ]
    finally:
        connection.close()


def elevator_markers(caves: list[dict], tile_paths: list[str | None], game_path: Path | None) -> list[dict]:
    if game_path is None:
        return []
    markers = []
    for tile_index, relative_path in enumerate(tile_paths, 1):
        if not relative_path or "elevator" not in relative_path.casefold():
            continue
        document = json.loads((game_path / relative_path).read_text(encoding="utf-8-sig"))
        entities = document.get("entities", {})
        nodes = [
            item for item in entities.get("blueprints", [])
            if any(str(tag).startswith("UNDERGROUND_ELEVATOR") for tag in item.get("tags", []))
        ]
        centers = [
            item for item in entities.get("prefabs", [])
            if any(str(tag).startswith("UNDERGROUND_ELEVATOR") for tag in item.get("tags", []))
        ]
        for cell in caves:
            for record in cell["records"]:
                if record["tileIndex"] != tile_index or record["sourceOffsetX"] or record["sourceOffsetY"]:
                    continue
                anchor_x = cell["cellX"] * 64
                anchor_y = cell["cellY"] * 64
                for node in nodes:
                    local = node["transform"]["position"]
                    center = centers[0]["transform"]["position"] if centers else local
                    markers.append({
                        "tag": node["tags"][0],
                        "x": anchor_x + float(local[0]),
                        "y": anchor_y + float(local[1]),
                        "z": record["zChunk"] * 16 + float(local[2]),
                        "facingX": float(local[0]) - float(center[0]),
                        "facingY": float(local[1]) - float(center[1]),
                        "sourceTile": relative_path,
                        "positionAccuracy": "Exact transformed authored connection node",
                    })
    return markers


def authored_resource_points(caves: list[dict], game_path: Path | None) -> list[dict]:
    if game_path is None:
        return []
    quartz_uuid = "a98a1502-7c9e-4dae-b7f9-30f31fc99496"
    cache = {}
    result = []
    for cell in caves:
        for record in cell["records"]:
            relative_path = record.get("tilePath")
            if not relative_path or record["rotationQuarterTurns"] != 0:
                continue
            if relative_path not in cache:
                cache[relative_path] = json.loads((game_path / relative_path).read_text(encoding="utf-8-sig")).get("entities", {})
            entities = cache[relative_path]
            candidates = []
            candidates.extend(("Quartz", item) for item in entities.get("harvestables", []) if str(item.get("uuid", "")).casefold() == quartz_uuid)
            candidates.extend(("Goopite", item) for item in entities.get("voxelMeshes", []) if item.get("materialIndex") == 5)
            for material, item in candidates:
                position = item.get("transform", {}).get("position")
                if not isinstance(position, list) or len(position) < 3:
                    continue
                source_x = math.floor(float(position[0]) / 64)
                source_y = math.floor(float(position[1]) / 64)
                if source_x != record["sourceOffsetX"] or source_y != record["sourceOffsetY"]:
                    continue
                result.append({
                    "material": material,
                    "x": cell["cellX"] * 64 + float(position[0]) - source_x * 64,
                    "y": cell["cellY"] * 64 + float(position[1]) - source_y * 64,
                    "z": record["zChunk"] * 16 + float(position[2]),
                    "source": "authored-harvestable" if material == "Quartz" else "authored-voxel-operation",
                    "currentState": "original placement; depletion not decoded",
                })
    return result


def resolve_tile_paths(game_path: Path, tile_uuids: set[str]) -> dict[str, str]:
    unresolved = set(tile_uuids)
    resolved = {}
    tile_root = game_path / "Survival" / "Terrain" / "Tiles" / "underground"
    uuid_pattern = re.compile(r'"uuid"\s*:\s*"([0-9a-fA-F-]{36})"')
    for path in tile_root.rglob("*.tileson"):
        if not unresolved:
            break
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        identifiers = {match.casefold() for match in uuid_pattern.findall(text)}
        matches = unresolved & identifiers
        for identifier in matches:
            resolved[identifier] = str(path.relative_to(game_path)).replace("\\", "/")
        unresolved -= matches
    return resolved


def summarize_world(save_path: Path, world_id: int, game_path: Path | None = None) -> dict:
    payload = unpack_script_data(read_terrain_blob(save_path, world_id))
    terrain = TerrainObjectReader(payload).read_value()
    tiles = [decoded_uuid(value) for value in indexed_values(terrain.get("tileList"))]
    tile_paths = resolve_tile_paths(game_path, {value for value in tiles if value}) if game_path else {}
    caves = populated_cells(terrain.get("caves"), decode_cave, tiles)
    pockets = populated_cells(terrain.get("pockets"), decode_pocket, tiles)
    ordered_paths = [tile_paths.get(value) for value in tiles]
    for collection in (caves, pockets):
        for cell in collection:
            for record in cell["records"]:
                index = record["tileIndex"] - 1
                record["tilePath"] = ordered_paths[index] if 0 <= index < len(ordered_paths) else None
    for cell in pockets:
        for record in cell["records"]:
            record["category"] = pocket_category(record.get("tilePath"))
    tunnels = []
    tunnel_types = Counter()
    all_tunnel_z = []
    for index, tunnel in enumerate(indexed_values(terrain.get("tunnels")), 1):
        positions = indexed_values(tunnel.get("positions"))
        points = [
            {axis: float(position[axis]) for axis in ("x", "y", "z")}
            for position in positions
        ]
        tunnel_type = str(tunnel.get("tunnelType", "Unknown"))
        tunnel_types[tunnel_type] += 1
        all_tunnel_z.extend(point["z"] for point in points)
        tunnels.append({"index": index, "type": tunnel_type, "positions": points})

    cave_records = [record for cell in caves for record in cell["records"]]
    pocket_records = [record for cell in pockets for record in cell["records"]]
    cave_z = [record["zChunk"] for record in cave_records]
    pocket_z = [record["zChunk"] for record in pocket_records]
    return {
        "worldId": world_id,
        "payloadBytes": len(payload),
        "bounds": terrain.get("bounds"),
        "seed": terrain.get("seed"),
        "tileCount": len(tiles),
        "tileUuids": tiles,
        "tilePaths": ordered_paths,
        "caveRecordCount": len(cave_records),
        "caveZChunkRange": [min(cave_z), max(cave_z)] if cave_z else None,
        "caveCells": caves,
        "pocketRecordCount": len(pocket_records),
        "pocketZChunkRange": [min(pocket_z), max(pocket_z)] if pocket_z else None,
        "pocketCells": pockets,
        "savedVoxelChangeCells": saved_voxel_cells(save_path, world_id),
        "elevatorMarkers": elevator_markers(caves, ordered_paths, game_path),
        "authoredResourcePoints": authored_resource_points(caves, game_path),
        "tunnelCount": len(tunnels),
        "tunnelTypes": dict(sorted(tunnel_types.items())),
        "tunnelZRangeMeters": [min(all_tunnel_z), max(all_tunnel_z)] if all_tunnel_z else None,
        "tunnels": tunnels,
        "spawnerCellCount": sum(
            1 for row in terrain.get("spawners", {}).values()
            for records in row.values() if records
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("save", type=Path)
    parser.add_argument("--world-id", type=int, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--game", type=Path)
    arguments = parser.parse_args()
    report = {
        "save": str(arguments.save.resolve()),
        "worlds": [
            summarize_world(arguments.save, world_id, arguments.game)
            for world_id in arguments.world_id
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for world in report["worlds"]:
        print(
            f"World {world['worldId']}: {world['caveRecordCount']} cave records, "
            f"{world['pocketRecordCount']} pocket records, {world['tunnelCount']} tunnels"
        )
    print(arguments.output.resolve())


if __name__ == "__main__":
    main()
