"""Shared helpers for the fake SAPIENT nodes: framing, templates, IDs and logging.

BSI Flex 335 v2.0 framing: a 4-byte little-endian length, then a serialised SapientMessage.
Nothing Zenoh is imported until a Zenoh link is used, so the TCP path needs no Zenoh binding.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import struct
from pathlib import Path
from typing import TYPE_CHECKING

import ulid
from google.protobuf.json_format import MessageToDict, ParseDict

from sapient_msg.bsi_flex_335_v2_0.location_pb2 import (
    LOCATION_COORDINATE_SYSTEM_LAT_LNG_DEG_M,
    LOCATION_DATUM_WGS84_E,
    Location,
)
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

if TYPE_CHECKING:
    from zenoh_io import ZenohSession

TEMPLATES = Path(__file__).parent / "templates"
EARTH_RADIUS_M = 6_371_000.0
RECONNECT_SECONDS = 10  # BSI Flex 335 v2.0: retry the connection every 10 s


def _zenoh_keys():
    """The zenoh_keys module, imported on first use because it needs the Zenoh binding."""
    import zenoh_keys

    return zenoh_keys


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
    """One line describing a message, for logs. Never raises, whatever the message holds."""
    kind = msg.WhichOneof("content")
    src = msg.node_id[:8]
    dst = f" -> {msg.destination_id[:8]}" if msg.HasField("destination_id") else ""
    if kind is None:
        return f"message with no content {src}{dst}"
    try:
        detail = _detail(kind, MessageToDict(getattr(msg, kind), preserving_proto_field_name=True))
    except Exception as error:  # e.g. a missing mandatory field, or a NaN location
        return f"{kind} {src}{dst} (no summary: {error!r})"
    return f"{kind} {src}{dst} {detail}"


def _detail(kind: str, body: dict) -> str:
    """The kind-specific part of a summary line. May raise on a message that lacks what it reads."""
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
    return detail


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


async def _next_sample(
    session: ZenohSession, samples: asyncio.Queue[tuple[str, bytes]]
) -> tuple[str, bytes]:
    """Next (key, payload) from samples; raises ConnectionError once the session is closed."""
    sample = asyncio.ensure_future(samples.get())
    closed = asyncio.ensure_future(session.closed.wait())
    try:
        await asyncio.wait({sample, closed}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        sample.cancel()
        closed.cancel()
    if session.closed.is_set():
        raise ConnectionError("the Zenoh session is closed")
    return sample.result()


class ZenohLink:
    """A node's Zenoh transport, with the same interface as Link."""

    def __init__(
        self, session: ZenohSession, node_id: str, samples: asyncio.Queue[tuple[str, bytes]]
    ):
        self.session = session
        self.node_id = node_id
        self.samples = samples

    @classmethod
    async def connect(cls, session: ZenohSession, node_id: str, log: logging.Logger) -> "ZenohLink":
        # Subscribe first: the token is what prompts the other side to send down messages.
        keys = _zenoh_keys()
        samples = session.subscribe(keys.DOWN_FOR(node_id))
        session.declare_token(keys.live_key(node_id))
        log.info(f"joined Zenoh as node {node_id}")
        return cls(session, node_id, samples)

    async def send(self, msg: SapientMessage):
        keys = _zenoh_keys()
        await self.session.publish(keys.up_key(self.node_id, keys.kind_of(msg)), msg)

    async def receive(self) -> SapientMessage:
        """Next message for this node; raises ConnectionError when the session is closed."""
        _, payload = await _next_sample(self.session, self.samples)
        return SapientMessage.FromString(payload)

    def close(self):
        self.session.undeclare_token(_zenoh_keys().live_key(self.node_id))


class ZenohFusionLink:
    """A fusion node's Zenoh transport inside a pod, with the same interface as Link.

    It also gives the fusion node the key functions of the pod's scheme, so that the node has no
    knowledge of which scheme is in use.
    """

    children_are_fusion_nodes = False  # inside a pod another fusion node is a peer, and is ignored
    has_parent = True  # it registers upward on the pod's fusion keys

    def __init__(
        self, session: ZenohSession, fusion_id: str, samples: asyncio.Queue[tuple[str, bytes]]
    ):
        self.session = session
        self.fusion_id = fusion_id
        self.samples = samples
        keys = _zenoh_keys()
        self.live_all: str = keys.LIVE_ALL
        self.own_keys = frozenset(keys.up_key(fusion_id, kind) for kind in keys.KINDS)
        self.last_sample: tuple[str, bytes] = ("", b"")  # (key, payload) of the latest message from a node
        self.from_above = session.subscribe(keys.FUSION_DOWN_ALL)  # what a host sends this child

    @classmethod
    async def connect(
        cls, session: ZenohSession, fusion_id: str, log: logging.Logger
    ) -> "ZenohFusionLink":
        samples = session.subscribe(_zenoh_keys().UP_ALL)
        log.info(f"joined Zenoh as fusion node {fusion_id}")
        return cls(session, fusion_id, samples)

    async def send(self, msg: SapientMessage):
        """Publish to msg.destination_id if set; otherwise as this fusion node's own output."""
        keys = _zenoh_keys()
        kind = keys.kind_of(msg)
        if msg.destination_id:
            await self.session.publish(keys.down_key(msg.destination_id, kind), msg)
        else:
            await self.session.publish(keys.up_key(self.fusion_id, kind), msg, fused=True)

    async def send_upward(self, msg: SapientMessage):
        """Publish on the pod's fusion keys, where a host would listen to this child Fusion_Node."""
        keys = _zenoh_keys()
        await self.session.publish(keys.fusion_up_key(keys.kind_of(msg)), msg, fused=True)

    async def receive_raw(self) -> tuple[bytes, SapientMessage]:
        """Next message from a node, with its payload bytes.

        Raises ConnectionError when the session is closed, and DecodeError for an undecodable
        message; last_sample then still holds its key and payload.
        """
        while True:
            key, payload = await _next_sample(self.session, self.samples)
            # UP_ALL also matches this node's own publications, which zenoh delivers back to it.
            if key not in self.own_keys:
                self.last_sample = (key, payload)
                return payload, SapientMessage.FromString(payload)

    async def receive(self) -> SapientMessage:
        _, msg = await self.receive_raw()
        return msg

    async def receive_from_above(self) -> SapientMessage:
        """Next message from the host on the pod's fusion keys.

        Raises ConnectionError when the session is closed, and DecodeError for an undecodable message.
        """
        _, payload = await _next_sample(self.session, self.from_above)
        return SapientMessage.FromString(payload)

    def owner_of(self, key: str) -> str | None:
        """The node a SAPIENT key names, or None for a malformed key."""
        try:
            return _zenoh_keys().parse_key(key)[0]
        except ValueError:
            return None

    def node_of_live_key(self, key: str) -> str:
        """The node a liveliness key names; ValueError for a bad key."""
        return _zenoh_keys().node_id_from_live_key(key)

    def close(self):
        """Nothing to release: a fusion node declares no token, and the session outlives the link."""
