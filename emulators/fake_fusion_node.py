"""A fake BSI Flex 335 v2.0 fusion node that connects to Apex as its Peer.

What it does:
  - acknowledges every node registration itself (v2.0 "transparent middleware": set
    "sendRegistrationAck": false in Apex so Apex does not answer for it);
  - logs status reports, detections, task acks and errors, and accepts every alert with an AlertAck;
  - toy fusion: joins detections that fall within 100 m of an existing track into that track, and
    publishes each track as its own DetectionReport (no destination, so Apex sends it to Parents);
  - tasks the nodes, every --task-interval seconds, cycling through --auto-task:
      look_at  -> sensors and pointable platforms, at the newest track
      move_to  -> mobile platforms, 200 m north-east of where they are
      patrol   -> mobile platforms, a 150 m square around where they are
      follow   -> mobile platforms, the newest track
      request:Status, mode_change:<mode>, detection_threshold, ... -> every node
  - reads commands from stdin (attach to the container): nodes, tracks, task <kind> [node], help.

With --transport zenoh Apex is not on the path, so the node also validates every message with
Apex's own validator (replying with an Error), asks every live node to re-register, and sends its
own status reports. It registers upward as a child Fusion_Node (BSI Flex 335 v2.0 clause 4.11) with
the union of its sensors' capabilities and task commands, once the first sensor has registered and
again whenever the registered sensors change, and mirrors its tracks onto the pod's fusion keys.
A node whose liveliness token stays gone for the hold window (--node-hold-seconds) is forgotten.

Usage: python fake_fusion_node.py --port 5001 --auto-task look_at,move_to,follow
"""
import argparse
import asyncio
import math
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import zenoh
from google.protobuf.message import DecodeError

from fake_sensor import use_lat_lng
from sapient_apex_server.validate_proto import ValidationOptions, Validator
from sapient_link import (
    Link,
    ZenohFusionLink,
    lat_lng,
    load_template,
    new_ulid,
    offset,
    setup_logging,
    stamp,
    summary,
)
from sapient_msg.bsi_flex_335_v2_0.alert_ack_pb2 import AlertAck
from sapient_msg.bsi_flex_335_v2_0.error_pb2 import Error
from sapient_msg.bsi_flex_335_v2_0.registration_pb2 import Registration
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from sapient_msg.bsi_flex_335_v2_0.status_report_pb2 import StatusReport
from zenoh_io import open_session
from zenoh_keys import LIVE_ALL, node_id_from_live_key, parse_key

TRANSPORTS = ("tcp", "zenoh")
GATE_M = 100.0  # toy association gate
TRACK_PUBLISH_SECONDS = 1.0
REQUESTS = {"Registration", "Reset", "Start", "Status", "Stop"}
TASK_TEMPLATES = {
    "look_at": "Task.LookAt",
    "move_to": "Task.MoveTo",
    "patrol": "Task.Patrol",
    "follow": "Task.Follow",
    "mode_change": "Task.Mode",
    "detection_threshold": "Task.DetectionThreshold.Medium",
    "detection_report_rate": "Task.DetectionReportRate.Medium",
    "classification_threshold": "Task.ClassificationThreshold.Medium",
}
OWN_MODE = "Default"
REGISTRATION_DEBOUNCE_SECONDS = 5
REQUEST_GRACE_SECONDS = 3.0  # a node that has just appeared gets this long to register by itself
# The validationOptions block of apex_config.emulators.json.
VALIDATION_OPTIONS = ValidationOptions.from_config_dict({
    "validationTypes": [
        "mandatory_fields_present",
        "mandatory_oneof_present",
        "mandatory_repeated_present",
        "no_unknown_fields",
        "no_unknown_enum_values",
        "id_format_valid",
        "message_timestamp_reasonable",
        "detection_timestamp_reasonable",
        "supported_icd_version",
    ],
    "strictIdFormat": True,
    "messageTimestampRange": [-0.9, 0.1],
    "detectionMinimumGap": 0.08,
    "supportedIcdVersions": ["BSI Flex 335 v1.0", "BSI Flex 335 v2.0"],
})


def node_types(registration) -> set[str]:
    return {Registration.NodeType.Name(d.node_type).removeprefix("NODE_TYPE_") for d in registration.node_definition}


def key_owner(key: str) -> str | None:
    """The node a SAPIENT key names, or None for a malformed key."""
    try:
        return parse_key(key)[0]
    except ValueError:
        return None


def identity_error(node_id: str, key: str) -> str | None:
    """Why a message claiming node_id may not arrive on key, or None if it may.

    The router authenticates only the key, so a node_id naming anyone else is a forgery. A message
    with no node_id is left to validation, which reports the missing field.
    """
    if not node_id:
        return None
    owner = key_owner(key)
    if owner is None:
        return f"malformed key {key!r}"
    if node_id != owner:
        return f"node_id {node_id} does not match the owner of its key, {owner}"
    return None


def declares_fusion_node(msg: SapientMessage) -> bool:
    """Whether msg is a Registration of a fusion node. Safe on a message not yet validated."""
    return msg.WhichOneof("content") == "registration" and any(
        d.node_type == Registration.NodeType.NODE_TYPE_FUSION_NODE for d in msg.registration.node_definition
    )


def unique(items, key) -> list:
    """items without repeats of key(item), keeping the first of each in order."""
    seen = {}
    for item in items:
        seen.setdefault(key(item), item)
    return list(seen.values())


def distance_m(a, b) -> float:
    north = math.radians(b.y - a.y) * 6_371_000.0
    east = math.radians(b.x - a.x) * 6_371_000.0 * math.cos(math.radians(a.y))
    return math.hypot(east, north)


class Track:
    def __init__(self, detection):
        self.track_id = new_ulid()
        self.detection = detection
        self.sources = set()
        self.updated = time.time()
        self.published = 0.0


class FakeFusionNode:
    def __init__(self, args):
        self.args = args
        self.node_id = args.node_id
        self.log = setup_logging("fusion")
        self.link = None
        self.zenoh_session = None
        self.nodes = {}  # node_id -> {"name", "types", "location", "registration"}
        self.tracks = []
        self.detection_counts = {}
        self.auto_tasks = [t for t in args.auto_task.split(",") if t]
        self.validators = {}  # node_id -> Validator
        self.other_fusion_nodes = set()  # owners of up keys that have declared a fusion node
        self.registry_changed = asyncio.Event()  # the registered sensors differ from the last announcement
        self.own_registered = asyncio.Event()  # this connection has published this node's Registration
        self.status_changed = True  # the next own status report is INFO_NEW
        self._token_alive = {}  # node_id -> the last liveliness state reported; absent until first reported
        self._hold_timers = {}  # node_id -> the TimerHandle that forgets the node
        self._pending_requests = {}  # node_id -> the TimerHandle that asks it to register
        self._requests_due = asyncio.Queue()  # node_ids whose grace has ended

    # ---- outgoing ------------------------------------------------------------------------

    async def send(self, msg):
        await self.link.send(msg)
        self.log.info(f"-> {summary(msg)}")

    def _task(self, kind: str, node_id: str):
        """Build a Task for one node from the Test Harness template, or None if it can't be built."""
        name, _, argument = kind.partition(":")
        if name == "request":
            request = argument or "Status"
            msg = load_template("fusion_node", f"Task.Request.{request if request in REQUESTS else 'Status'}")
            msg.task.command.request = request
        elif name in TASK_TEMPLATES:
            msg = load_template("fusion_node", TASK_TEMPLATES[name])
        else:
            self.log.info(f"unknown task kind {kind!r}; try: {', '.join(['request'] + list(TASK_TEMPLATES))}")
            return None
        task = msg.task
        task.task_id = new_ulid()
        task.task_name = f"fake fusion node: {kind}"
        task.task_description = f"{kind} for {self.nodes.get(node_id, {}).get('name', node_id)}"
        task.task_start_time.GetCurrentTime()
        task.ClearField("task_end_time")
        del task.region[:]
        command = task.command
        command.ClearField("command_parameter")
        newest = max(self.tracks, key=lambda t: t.updated, default=None)
        here = self.nodes.get(node_id, {}).get("location")
        if name == "look_at":
            if newest is None:
                self.log.info("look_at: no track to look at yet")
                return None
            del command.look_at.location_list.locations[:]
            command.look_at.location_list.locations.append(newest.detection.location)
        elif name == "follow":
            if newest is None:
                self.log.info("follow: no track to follow yet")
                return None
            command.follow.follow_object_id = newest.track_id
        elif name in ("move_to", "patrol"):
            if here is None:
                self.log.info(f"{name}: no status report with a location from that node yet")
                return None
            corners = [(200, 200)] if name == "move_to" else [(150, 0), (150, 150), (0, 150), (0, 0)]
            route = getattr(command, name)
            del route.locations[:]
            for east, north in corners:
                lon, lat = offset(here.x, here.y, east, north)
                route.locations.append(lat_lng(lon, lat))
        elif name == "mode_change":
            command.mode_change = argument or "Default"
        return stamp(msg, self.node_id, node_id)

    def _targets(self, kind: str) -> list[str]:
        """Which registered nodes a task kind is meant for."""
        name = kind.partition(":")[0]
        result = []
        for node_id, node in self.nodes.items():
            types = node["types"]
            if name in ("move_to", "patrol", "follow"):
                wanted = "MOBILE_NODE" in types
            elif name == "look_at":
                wanted = "MOBILE_NODE" not in types
            else:
                wanted = True
            if wanted:
                result.append(node_id)
        return result

    def _find_nodes(self, text: str) -> list[str]:
        """Nodes whose ID starts with text or whose short name is text; else whose name contains it."""
        text = text.lower()
        exact = [
            node_id for node_id, node in self.nodes.items()
            if node_id.startswith(text) or node.get("short_name", "").lower() == text
        ]
        return exact or [node_id for node_id, node in self.nodes.items() if text in node.get("name", "").lower()]

    async def send_task(self, kind: str, node_ids: list[str]):
        for node_id in node_ids:
            msg = self._task(kind, node_id)
            if msg is not None:
                await self.send(msg)

    def _registrations(self) -> list:
        """The Registration of every node that has registered (a status report alone doesn't count)."""
        return [node["registration"] for node in self.nodes.values() if "registration" in node]

    def build_fusion_registration(self) -> SapientMessage:
        """This node's Registration as a child Fusion_Node, standing for its registered sensors."""
        registrations = self._registrations()
        msg = load_template("sensor", "Registration")
        reg = msg.registration
        del reg.node_definition[:]
        reg.node_definition.add(node_type=Registration.NodeType.NODE_TYPE_FUSION_NODE)
        reg.icd_version = "BSI Flex 335 v2.0"
        reg.name = "fake fusion node"
        reg.short_name = "fusion"
        del reg.capabilities[:]
        reg.capabilities.extend(
            unique((c for r in registrations for c in r.capabilities), lambda c: (c.category, c.type))
        )
        reg.status_definition.status_interval.units = Registration.TIME_UNITS_SECONDS
        reg.status_definition.status_interval.value = self.args.status_interval
        mode = reg.mode_definition[0]
        mode.mode_name = OWN_MODE
        del mode.task.command[:]
        mode.task.command.extend(
            unique(
                (c for r in registrations for m in r.mode_definition for c in m.task.command),
                lambda c: (c.type, c.units),
            )
        )
        del reg.dependent_nodes[:]
        del reg.config_data[:]
        reg.config_data.add(
            manufacturer="Apex docker emulator",
            model="fake-fusion-node",
            serial_number=self.node_id[:8],
            software_version="1.0",
        )
        use_lat_lng(reg)
        return stamp(msg, self.node_id)

    def _own_status(self, info):
        msg = load_template("sensor", "StatusReport")
        report = msg.status_report
        report.report_id = new_ulid()
        report.system = StatusReport.SYSTEM_OK
        report.info = info
        report.mode = OWN_MODE
        # A fusion node has no position or sensor coverage of its own to report
        for field in ("active_task_id", "power", "node_location", "field_of_view", "coverage", "obscuration", "status"):
            report.ClearField(field)
        return stamp(msg, self.node_id)

    async def _own_status_loop(self):
        while True:
            info = StatusReport.INFO_NEW if self.status_changed else StatusReport.INFO_UNCHANGED
            self.status_changed = False
            await self.send(self._own_status(info))
            await asyncio.sleep(self.args.status_interval)

    async def request_registrations(self):
        """Ask every live node to register again, since this node has just (re)started."""
        node_ids = []
        for key in await self.link.session.alive(LIVE_ALL):
            try:
                node_ids.append(node_id_from_live_key(key))
            except ValueError:
                self.log.info(f"ignoring malformed liveliness token {key!r}")
        await self.send_task("request:Registration", node_ids)

    async def _publish_registration(self):
        """Publish this node's Registration, unless no sensor has registered yet.

        Capabilities are mandatory, so until then there is nothing valid to say.
        """
        self.registry_changed.clear()
        if not self._registrations():
            return
        msg = self.build_fusion_registration()
        await self.send(msg)
        await self.link.send_upward(msg)
        self.status_changed = True  # a status report following a Registration must be INFO_NEW
        self.own_registered.set()

    async def _announce(self):
        await self._publish_registration()  # after a reconnect the sensors are already known
        await self.request_registrations()

    async def _registration_loop(self):
        """Publish this node's Registration again when the registered sensors change, debounced."""
        while True:
            await self.registry_changed.wait()
            await asyncio.sleep(REGISTRATION_DEBOUNCE_SECONDS)
            await self._publish_registration()

    async def _status_once_registered(self):
        """A node's first status report must not overtake its Registration."""
        await self.own_registered.wait()
        await self._own_status_loop()

    async def _send_error(self, packet: bytes, description: str, key: str):
        """Tell the node that owns key, the only sender identity the router vouches for."""
        recipient = key_owner(key)
        if recipient is None:
            self.log.info(f"nobody to tell about a message on {key!r}: {description}")
            return
        reply = SapientMessage(error=Error(packet=packet, error_message=[description]))
        await self.send(stamp(reply, self.node_id, recipient))

    # ---- who is still there (Zenoh only) ---------------------------------------------------
    # The same hold and transport handling as the Apex-side bridge: tokens all report gone while the
    # router is away, so nothing is forgotten until a whole hold has passed without the token.

    def _is_registered(self, node_id: str) -> bool:
        return "registration" in self.nodes.get(node_id, {})

    async def _track_liveliness(self, changes: asyncio.Queue):
        while True:
            key, alive = await changes.get()
            self._on_liveliness(key, alive)

    def _on_liveliness(self, key: str, alive: bool):
        try:
            node_id = node_id_from_live_key(key)
        except ValueError:
            self.log.info(f"ignoring liveliness on bad key {key!r}")
            return
        if not alive:
            self._token_gone(node_id)
            return
        already_alive = self._token_alive.get(node_id) is True
        self._token_alive[node_id] = True
        self._stop_hold(node_id)
        if not already_alive and not self._is_registered(node_id):
            self._schedule_request(node_id)

    def _token_gone(self, node_id: str):
        self._token_alive[node_id] = False
        self._cancel_request(node_id)
        self._start_hold(node_id)

    async def _track_transport(self, changes: asyncio.Queue):
        while True:
            if await changes.get():
                self.log.info("Zenoh transport back; checking node tokens")
                await self._consult_alive_tokens()
            else:
                self.log.info("Zenoh transport lost; holding every node")
                for node_id in {*self.nodes, *self._token_alive}:
                    self._token_gone(node_id)

    async def _consult_alive_tokens(self):
        """Count the tokens alive now as reported. One missing here just keeps its hold running."""
        try:
            keys = await self.link.session.alive(LIVE_ALL)
        except zenoh.ZError as e:
            self.log.info(f"could not query the node tokens: {e}")
            return
        for key in keys:
            self._on_liveliness(key, True)

    def _hold_if_token_gone(self, node_id: str):
        """A message still in flight when the token went must not bring the node back for good."""
        if self._token_alive.get(node_id) is False:
            self._start_hold(node_id)

    def _start_hold(self, node_id: str):
        if node_id not in self._hold_timers:
            self._hold_timers[node_id] = asyncio.get_running_loop().call_later(
                self.args.node_hold_seconds, self._hold_expired, node_id
            )

    def _stop_hold(self, node_id: str):
        timer = self._hold_timers.pop(node_id, None)
        if timer is not None:
            timer.cancel()

    def _hold_expired(self, node_id: str):
        del self._hold_timers[node_id]
        self.validators.pop(node_id, None)
        node = self.nodes.pop(node_id, None)
        if node is None:
            return
        self.log.info(f"node {node_id[:8]} gone for {self.args.node_hold_seconds:g} s; removed")
        if "registration" in node:
            self.registry_changed.set()

    def _schedule_request(self, node_id: str):
        if node_id not in self._pending_requests:
            self._pending_requests[node_id] = asyncio.get_running_loop().call_later(
                REQUEST_GRACE_SECONDS, self._requests_due.put_nowait, node_id
            )

    def _cancel_request(self, node_id: str):
        timer = self._pending_requests.pop(node_id, None)
        if timer is not None:
            timer.cancel()

    async def _request_loop(self):
        """Ask each live node that has not registered by the end of its grace to register."""
        while True:
            node_id = await self._requests_due.get()
            self._pending_requests.pop(node_id, None)
            if self._token_alive.get(node_id) and not self._is_registered(node_id):
                await self.send_task("request:Registration", [node_id])

    # ---- incoming ------------------------------------------------------------------------

    def validate(self, msg: SapientMessage) -> str | None:
        """Apex's checks on a message just received: an error description, or None if it passes."""
        if self.args.transport != "zenoh":
            return None  # Apex validates on TCP
        # One Validator per sender, as Apex has one per connection: it remembers the last detection time.
        validator = self.validators.setdefault(msg.node_id, Validator(VALIDATION_OPTIONS))
        errors = []
        received = datetime.now(timezone.utc).replace(tzinfo=None)  # protobuf timestamps convert to naive UTC
        try:
            validator.validate_sapient_message(msg, received, errors)
        except Exception as e:  # e.g. no icd_version, or a timestamp too big to convert
            return f"message could not be validated: {e!r}"
        return "; ".join(error.full_str() for error in errors) or None

    async def _next_message(self):
        """The next message to act on. Over Zenoh, a bad message is answered with an Error and skipped."""
        if self.args.transport == "tcp":
            return await self.link.receive()  # a DecodeError ends the node; compose restarts it
        while True:
            try:
                packet, msg = await self.link.receive_raw()
            except DecodeError:
                key, packet = self.link.last_sample
                if key_owner(key) in self.other_fusion_nodes:
                    continue
                self.log.info(f"undecodable message dropped (key {key})")
                await self._send_error(packet, "undecodable message", key)
                continue
            if self._from_other_fusion_node(msg):
                continue
            key, _ = self.link.last_sample
            description = identity_error(msg.node_id, key) or self.validate(msg)
            if description is None:
                return msg
            self.log.info(f"invalid message from {msg.node_id[:8]!r} dropped: {description}")
            await self._send_error(packet, description, key)

    def _from_other_fusion_node(self, msg) -> bool:
        """Whether the latest sample is another fusion node's: it is a peer, not a sensor of this one.

        Goes by the key's owner, which the router authenticates, because node_id may be missing.
        """
        owner = key_owner(self.link.last_sample[0])
        if owner is None:
            return False
        if declares_fusion_node(msg) and owner not in self.other_fusion_nodes:
            self.other_fusion_nodes.add(owner)
            self.log.info(f"ignoring another fusion node {owner[:8]}")
        return owner in self.other_fusion_nodes

    async def _on_registration(self, msg):
        reg = msg.registration
        self.validators.pop(msg.node_id, None)  # a (re)registering sender starts afresh, as on a new Apex connection
        known = msg.node_id in self.nodes
        self._hold_if_token_gone(msg.node_id)
        self.nodes.setdefault(msg.node_id, {"location": None})
        if self.nodes[msg.node_id].get("registration") != reg:
            self.registry_changed.set()
        self.nodes[msg.node_id].update(
            name=reg.name, short_name=reg.short_name, types=node_types(reg), awaiting_new_status=True, registration=reg
        )
        ack = load_template("fusion_node", "RegistrationAck")
        ack.registration_ack.acceptance = True
        ack.registration_ack.ack_response_reason[:] = ["Accepted by fake fusion node" + (" (re-registration)" if known else "")]
        await self.send(stamp(ack, self.node_id, msg.node_id))

    def _on_status(self, msg):
        report = msg.status_report
        self._hold_if_token_gone(msg.node_id)
        node = self.nodes.setdefault(msg.node_id, {"name": msg.node_id[:8], "types": set(), "location": None})
        if report.HasField("node_location"):
            node["location"] = report.node_location
        if report.info == StatusReport.INFO_NEW:
            node["awaiting_new_status"] = False
        elif report.info == StatusReport.INFO_UNCHANGED and node.get("awaiting_new_status"):
            self.log.info(f"Unchanged status from {msg.node_id[:8]} before any New status since it registered")
        return report.info == StatusReport.INFO_NEW

    def _may_publish_tracks(self) -> bool:
        """Over Zenoh, as with status reports, tracks wait until this node has registered upward."""
        return self.args.publish_tracks and (self.args.transport == "tcp" or self.own_registered.is_set())

    async def _on_detection(self, msg):
        det = msg.detection_report
        count = self.detection_counts.get(msg.node_id, 0)
        self.detection_counts[msg.node_id] = count + 1
        if not det.HasField("location"):
            return count % 10 == 0
        # Toy association: nearest track within the gate, else a new track
        nearest = min(self.tracks, key=lambda t: distance_m(t.detection.location, det.location), default=None)
        if nearest is None or distance_m(nearest.detection.location, det.location) > GATE_M:
            nearest = Track(det)
            self.tracks.append(nearest)
            self.log.info(f"new track {nearest.track_id[-6:]} from {self.nodes.get(msg.node_id, {}).get('name', msg.node_id[:8])}")
        nearest.detection = det
        nearest.sources.add(msg.node_id)
        nearest.updated = time.time()
        if self._may_publish_tracks() and time.time() - nearest.published >= TRACK_PUBLISH_SECONDS:
            nearest.published = time.time()
            track = load_template("sensor", "DetectionReport")
            track.detection_report.CopyFrom(det)
            track.detection_report.report_id = new_ulid()
            track.detection_report.object_id = nearest.track_id
            track.detection_report.ClearField("task_id")
            await self.link.send(stamp(track, self.node_id))
            if self.args.transport == "zenoh":
                await self.link.send_upward(track)
        return count % 10 == 0

    async def _receive_loop(self):
        while True:
            msg = await self._next_message()
            kind = msg.WhichOneof("content")
            show = True
            if kind == "registration":
                self.log.info(f"<- {summary(msg)}")
                await self._on_registration(msg)
                continue
            if kind == "status_report":
                show = self._on_status(msg)
            elif kind == "detection_report":
                show = await self._on_detection(msg)
            if show:
                note = "  (logging every 10th per node)" if kind == "detection_report" else ""
                self.log.info(f"<- {summary(msg)}{note}")
            if kind == "alert":
                ack = load_template("fusion_node", "AlertAck")
                ack.alert_ack.alert_id = msg.alert.alert_id
                ack.alert_ack.alert_ack_status = AlertAck.ALERT_ACK_STATUS_ACCEPTED
                await self.send(stamp(ack, self.node_id, msg.node_id))

    async def _auto_task_loop(self):
        if not self.auto_tasks:
            return
        await asyncio.sleep(self.args.task_interval)
        i = 0
        while True:
            kind = self.auto_tasks[i % len(self.auto_tasks)]
            targets = self._targets(kind)
            if targets:
                self.log.info(f"auto-task {kind} -> {len(targets)} node(s)")
                await self.send_task(kind, targets)
            i += 1
            await asyncio.sleep(self.args.task_interval)

    async def _stdin_loop(self):
        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                return  # stdin closed (not attached): no console
            words = line.split()
            if not words:
                continue
            if words[0] == "nodes":
                for node_id, node in self.nodes.items():
                    print(f"  {node_id}  {node.get('short_name', '')}  {node.get('name')}  "
                          f"{sorted(node.get('types', []))}", flush=True)
            elif words[0] == "tracks":
                for t in self.tracks:
                    loc = t.detection.location
                    print(f"  {t.track_id}  ({loc.y:.5f}, {loc.x:.5f})  from {len(t.sources)} node(s), "
                          f"{time.time() - t.updated:.0f} s ago", flush=True)
            elif words[0] == "task" and len(words) >= 2:
                if len(words) >= 3:
                    targets = self._find_nodes(" ".join(words[2:]))
                else:
                    targets = self._targets(words[1])
                if not targets:
                    print("  no matching node; type 'nodes'", flush=True)
                await self.send_task(words[1], targets)
            else:
                print("  commands: nodes | tracks | task <kind> [node: ID prefix, short name or part of name]\n"
                      "  kinds: look_at move_to patrol follow mode_change[:<mode>] "
                      "request[:Status|Start|Stop|Reset|Registration] detection_threshold "
                      "detection_report_rate classification_threshold", flush=True)

    async def _connect_link(self):
        """Connect over the chosen transport; every Zenoh connection gets a fresh session."""
        if self.args.transport == "tcp":
            return await Link.connect(self.args.host, self.args.port, self.log)
        if self.zenoh_session is not None:
            self.zenoh_session.close()  # no unsubscribe exists, so a reused session keeps stale queues
        self.zenoh_session = await open_session(
            self.args.zenoh_connect, asyncio.get_running_loop(), self.log
        )
        return await ZenohFusionLink.connect(self.zenoh_session, self.node_id, self.log)

    async def run(self):
        asyncio.get_running_loop().create_task(self._stdin_loop())
        while True:
            self.link = await self._connect_link()
            try:
                async with asyncio.TaskGroup() as group:
                    group.create_task(self._receive_loop())
                    group.create_task(self._auto_task_loop())
                    if self.args.transport == "zenoh":
                        self.own_registered.clear()
                        # Before _announce, so a node that appears meanwhile is not missed.
                        changes = self.zenoh_session.liveliness(LIVE_ALL)
                        group.create_task(self._track_liveliness(changes))
                        group.create_task(self._track_transport(self.zenoh_session.transport_changes))
                        group.create_task(self._request_loop())
                        group.create_task(self._announce())
                        group.create_task(self._registration_loop())
                        group.create_task(self._status_once_registered())
            except* (asyncio.IncompleteReadError, ConnectionError):
                self.log.info("connection to Apex lost; reconnecting")
            finally:
                self.link.close()
            await asyncio.sleep(10)


def main():
    env = os.environ.get
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=env("APEX_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(env("APEX_PORT", "5001")), help="Apex Peer port (v2.0)")
    parser.add_argument("--transport", choices=TRANSPORTS, default=env("TRANSPORT", "tcp"))
    parser.add_argument("--zenoh-connect", default=env("ZENOH_CONNECT", "tcp/zenohd:7447"),
                        help="Zenoh router endpoint, used with --transport zenoh")
    parser.add_argument("--node-id", default=env("NODE_ID") or str(uuid.uuid4()))
    parser.add_argument("--auto-task", default=env("AUTO_TASK", "look_at,move_to,follow,patrol,request:Status"),
                        help="comma-separated task kinds to cycle through; empty to disable")
    parser.add_argument("--task-interval", type=float, default=float(env("TASK_INTERVAL", "20")))
    parser.add_argument("--status-interval", type=float, default=float(env("STATUS_INTERVAL", "10")),
                        help="seconds between this node's own status reports, used with --transport zenoh")
    parser.add_argument("--node-hold-seconds", type=float, default=float(env("NODE_HOLD_SECONDS", "120")),
                        help="how long a node's liveliness token may be gone before it is forgotten, "
                             "used with --transport zenoh")
    parser.add_argument("--no-publish-tracks", dest="publish_tracks", action="store_false",
                        default=env("PUBLISH_TRACKS", "1") != "0")
    args = parser.parse_args()
    if args.transport not in TRANSPORTS:
        parser.error(f"TRANSPORT must be one of {', '.join(TRANSPORTS)}, not {args.transport!r}")
    try:
        asyncio.run(FakeFusionNode(args).run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
