"""Read Scrap Mechanic's persisted overworld terrain in SQLite read-only mode."""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path


TERRAIN_DATA_UID = bytes.fromhex("61aa13d7e7154153a2694d338c0c5bd4")
MAX_DECOMPRESSED_BYTES = 16 * 1024 * 1024


def decompress_lz4_block(data: bytes) -> bytes:
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
                value = data[source]
                source += 1
                literal_length += value
                if value != 255:
                    break
        if source + literal_length > len(data):
            raise ValueError("Truncated LZ4 literal data.")
        output.extend(data[source : source + literal_length])
        source += literal_length
        if len(output) > MAX_DECOMPRESSED_BYTES:
            raise ValueError("Terrain payload exceeds the safe decompression limit.")
        if source >= len(data):
            break
        if source + 2 > len(data):
            raise ValueError("Truncated LZ4 match offset.")
        offset = int.from_bytes(data[source : source + 2], "little")
        source += 2
        if offset == 0 or offset > len(output):
            raise ValueError("Invalid LZ4 match offset.")
        match_length = token & 0x0F
        if match_length == 15:
            while True:
                if source >= len(data):
                    raise ValueError("Truncated LZ4 match length.")
                value = data[source]
                source += 1
                match_length += value
                if value != 255:
                    break
        match_length += 4
        for _ in range(match_length):
            output.append(output[-offset])
            if len(output) > MAX_DECOMPRESSED_BYTES:
                raise ValueError("Terrain payload exceeds the safe decompression limit.")
    return bytes(output)


def unpack_script_data(blob: bytes) -> bytes:
    if len(blob) < 25:
        raise ValueError("Terrain ScriptData blob is too short.")
    key_size = int.from_bytes(blob[16:18], "big")
    header_size = 25 + key_size
    if header_size > len(blob):
        raise ValueError("Terrain ScriptData header is truncated.")
    compressed_size = int.from_bytes(blob[header_size - 4 : header_size], "big")
    if compressed_size <= 0 or header_size + compressed_size > len(blob):
        raise ValueError("Terrain ScriptData compressed payload is truncated.")
    payload = decompress_lz4_block(blob[header_size : header_size + compressed_size])
    if not payload.startswith(b"LUA\x00\x00\x00\x01"):
        raise ValueError("Terrain payload is not a version-1 Lua object.")
    return payload[7:]


class TerrainObjectReader:
    """Decode the bounded Lua-object subset used by persisted terrain."""

    def __init__(self, data: bytes):
        self.data = data
        self.bit = 0

    def read_bits(self, count: int) -> int:
        if self.bit + count > len(self.data) * 8:
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

    def read_value(self, path: str = "$"):
        type_start = self.bit
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
                offset = self.read_signed(32)
                return {
                    offset + index: self.read_value(f"{path}[{offset + index}]")
                    for index in range(count)
                }
            result = {}
            for index in range(count):
                key = self.read_value(f"{path}.<key:{index}>")
                result[key] = self.read_value(f"{path}[{key!r}]")
            return result
        if value_type == 6:
            return self.read_signed(32)
        if value_type == 7:
            return self.read_signed(16)
        if value_type == 8:
            return self.read_signed(8)
        if value_type == 11:
            return struct.unpack(">d", self.read_bits(64).to_bytes(8, "big"))[0]
        if value_type == 100:
            userdata_type = self.read_bits(32)
            if userdata_type == 10001:
                return {
                    "type": "uuid",
                    "raw": self.read_bits(128).to_bytes(16, "big").hex(),
                }
            if userdata_type == 10003:
                return {
                    "type": "vec3",
                    "x": struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0],
                    "y": struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0],
                    "z": struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0],
                }
            if userdata_type == 10004:
                return {
                    "type": "quat",
                    "x": struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0],
                    "y": struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0],
                    "z": struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0],
                    "w": struct.unpack(">f", self.read_bits(32).to_bytes(4, "big"))[0],
                }
            raise ValueError(
                f"Unsupported userdata {userdata_type} at {path}, "
                f"bit {type_start}, byte {type_start // 8}"
            )
        raise ValueError(
            f"Unsupported type {value_type} at {path}, bit {type_start}, "
            f"byte {type_start // 8}."
        )


def read_terrain_blob(save_path: Path, world_id: int) -> bytes:
    uri = f"{save_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        row = connection.execute(
            "SELECT data FROM ScriptData WHERE uid = ? AND worldId = ?",
            (TERRAIN_DATA_UID, world_id),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError(f"No terrain data exists for world {world_id}.")
    return row[0]
