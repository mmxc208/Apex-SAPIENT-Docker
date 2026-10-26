"""Shared helpers for the fake SAPIENT nodes: framing, templates, IDs and logging.

BSI Flex 335 v2.0 framing: a 4-byte little-endian length, then a serialised SapientMessage.
"""
import asyncio
import json
import logging
import math
import struct
from pathlib import Path

import ulid
from google.protobuf.json_format import MessageToDict, ParseDict

from sapient_msg.bsi_flex_335_v2_0.location_pb2 import (
    LOCATION_COORDINATE_SYSTEM_LAT_LNG_DEG_M,
    LOCATION_DATUM_WGS84_E,
    Location,
)
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

TEMPLATES = Path(__file__).parent / "templates"
RECONNECT_SECONDS = 10  # BSI Flex 335 v2.0: retry the connection every 10 s
EARTH_RADIUS_M = 6_371_000.0


def setup_logging(name: str):
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s {name}: %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(name)


def load_template(group: str, name: str) -> SapientMessage:
    """Load templates/<group>/Default.<name>.json as a v2.0 SapientMessage."""
    path = TEMPLATES / group / f"Default.{name}.json"
    with path.open(encoding="utf-8-sig") as f:
        return ParseDict(json.load(f), SapientMessage())


def new_ulid() -> str:
    return str(ulid.new())


def stamp(msg: SapientMessage, node_id: str, destination_id: str = None) -> SapientMessage:
    """Set the header fields: timestamp now, source node and (optional) destination."""
    msg.timestamp.GetCurrentTime()
    msg.node_id = node_id
    if destination_id:
        msg.destination_id = destination_id
    else:
        msg.ClearField("destination_id")
    return msg


def lat_lng(lon: float, lat: float, alt: float = 0.0, error_m: float = 0.0) -> Location:
    """A WGS84 location in degrees/metres. SAPIENT puts longitude in x and latitude in y."""
    loc = Location(
        x=lon,
        y=lat,
        z=alt,
        coordinate_system=LOCATION_COORDINATE_SYSTEM_LAT_LNG_DEG_M,
        datum=LOCATION_DATUM_WGS84_E,
    )
    if error_m:
        # x/y errors are in the same units as x/y (degrees); z error in metres
        loc.x_error = math.degrees(error_m / (EARTH_RADIUS_M * math.cos(math.radians(lat))))
        loc.y_error = math.degrees(error_m / EARTH_RADIUS_M)
        loc.z_error = error_m
    return loc


def offset(lon: float, lat: float, east_m: float, north_m: float) -> tuple[float, float]:
    """Move a lon/lat point by metres east and north (flat-earth approximation)."""
    d_lat = math.degrees(north_m / EARTH_RADIUS_M)
    d_lon = math.degrees(east_m / (EARTH_RADIUS_M * math.cos(math.radians(lat))))
    return lon + d_lon, lat + d_lat


def summary(msg: SapientMessage) -> str:
    """One line describing a message, for logs."""
    kind = msg.WhichOneof("content")
    body = MessageToDict(getattr(msg, kind), preserving_proto_field_name=True)
    src = msg.node_id[:8]
    dst = f" -> {msg.destination_id[:8]}" if msg.HasField("destination_id") else ""
    if kind == "registration":
        types = ",".join(d["node_type"].replace("NODE_TYPE_", "") for d in body.get("node_definition", []))
        detail = f'"{body.get("name")}" [{types}]'
        if body.get("dependent_nodes"):
            detail += f" carries {[n[:8] for n in body['dependent_nodes']]}"
    elif kind == "registration_ack":
        detail = f'acceptance={body.get("acceptance", False)} {body.get("ack_response_reason", [])}'
    elif kind == "status_report":
        detail = f'{body.get("system")} {body.get("info")} mode={body.get("mode")}'
    elif kind == "detection_report":
        loc = body.get("location", {})
        cls = body.get("classification", [{}])[0]
        sub = cls.get("sub_class", [{}])[0].get("type", "")
        detail = (
            f'object {body["object_id"][-6:]} at ({loc.get("y", 0):.5f}, {loc.get("x", 0):.5f}, '
            f'{loc.get("z", 0):.0f} m) {cls.get("type", "?")}/{sub} conf={body.get("detection_confidence", 0):.2f}'
        )
    elif kind == "task":
        command = body.get("command", {})
        name = next((k for k in command if k != "command_parameter"), "?")
        detail = f'{body["task_id"][-6:]} {name} {json.dumps(command[name]) if name != "?" else ""}'[:160]
    elif kind == "task_ack":
        detail = f'{body["task_id"][-6:]} {body.get("task_status")} {body.get("reason", [])}'
    elif kind == "alert":
        detail = f'{body.get("alert_type")} "{body.get("description", "")}"'
    elif kind == "alert_ack":
        detail = f'{body.get("alert_ack_status")}'
    elif kind == "error":
        detail = "; ".join(body.get("error_message", []))
    else:
        detail = ""
    return f"{kind} {src}{dst} {detail}"


class Link:
    """One TCP connection to Apex, carrying length-prefixed SapientMessages."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    @classmethod
    async def connect(cls, host: str, port: int, log: logging.Logger) -> "Link":
        """Connect, retrying every 10 s until Apex is reachable."""
        while True:
            try:
                reader, writer = await asyncio.open_connection(host, port)
                log.info(f"connected to Apex at {host}:{port}")
                return cls(reader, writer)
            except OSError as e:
                log.info(f"cannot reach {host}:{port} ({e.strerror or e}); retrying in {RECONNECT_SECONDS} s")
                await asyncio.sleep(RECONNECT_SECONDS)

    async def send(self, msg: SapientMessage):
        data = msg.SerializeToString()
        self.writer.write(struct.pack("<I", len(data)) + data)
        await self.writer.drain()

    async def receive(self) -> SapientMessage:
        """Next message; raises asyncio.IncompleteReadError when Apex closes the connection."""
        header = await self.reader.readexactly(4)
        (length,) = struct.unpack("<I", header)
        return SapientMessage.FromString(await self.reader.readexactly(length))

    def close(self):
        self.writer.close()
