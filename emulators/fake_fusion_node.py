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

Usage: python fake_fusion_node.py --port 5001 --auto-task look_at,move_to,follow
"""
import argparse
import asyncio
import math
import os
import sys
import time
import uuid

from sapient_link import (
    Link,
    lat_lng,
    load_template,
    new_ulid,
    offset,
    setup_logging,
    stamp,
    summary,
)
from sapient_msg.bsi_flex_335_v2_0.alert_ack_pb2 import AlertAck
from sapient_msg.bsi_flex_335_v2_0.registration_pb2 import Registration
from sapient_msg.bsi_flex_335_v2_0.status_report_pb2 import StatusReport

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


def node_types(registration) -> set[str]:
    return {Registration.NodeType.Name(d.node_type).removeprefix("NODE_TYPE_") for d in registration.node_definition}


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
        self.nodes = {}  # node_id -> {"name", "types", "location"}
        self.tracks = []
        self.detection_counts = {}
        self.auto_tasks = [t for t in args.auto_task.split(",") if t]

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

    # ---- incoming ------------------------------------------------------------------------

    async def _on_registration(self, msg):
        reg = msg.registration
        known = msg.node_id in self.nodes
        self.nodes.setdefault(msg.node_id, {"location": None})
        self.nodes[msg.node_id].update(name=reg.name, short_name=reg.short_name, types=node_types(reg))
        ack = load_template("fusion_node", "RegistrationAck")
        ack.registration_ack.acceptance = True
        ack.registration_ack.ack_response_reason[:] = ["Accepted by fake fusion node" + (" (re-registration)" if known else "")]
        await self.send(stamp(ack, self.node_id, msg.node_id))

    def _on_status(self, msg):
        report = msg.status_report
        node = self.nodes.setdefault(msg.node_id, {"name": msg.node_id[:8], "types": set(), "location": None})
        if report.HasField("node_location"):
            node["location"] = report.node_location
        return report.info == StatusReport.INFO_NEW

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
        if self.args.publish_tracks and time.time() - nearest.published >= TRACK_PUBLISH_SECONDS:
            nearest.published = time.time()
            track = load_template("sensor", "DetectionReport")
            track.detection_report.CopyFrom(det)
            track.detection_report.report_id = new_ulid()
            track.detection_report.object_id = nearest.track_id
            track.detection_report.ClearField("task_id")
            await self.link.send(stamp(track, self.node_id))
        return count % 10 == 0

    async def _receive_loop(self):
        while True:
            msg = await self.link.receive()
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

    async def run(self):
        asyncio.get_running_loop().create_task(self._stdin_loop())
        while True:
            self.link = await Link.connect(self.args.host, self.args.port, self.log)
            try:
                async with asyncio.TaskGroup() as group:
                    group.create_task(self._receive_loop())
                    group.create_task(self._auto_task_loop())
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
    parser.add_argument("--node-id", default=env("NODE_ID") or str(uuid.uuid4()))
    parser.add_argument("--auto-task", default=env("AUTO_TASK", "look_at,move_to,follow,patrol,request:Status"),
                        help="comma-separated task kinds to cycle through; empty to disable")
    parser.add_argument("--task-interval", type=float, default=float(env("TASK_INTERVAL", "20")))
    parser.add_argument("--no-publish-tracks", dest="publish_tracks", action="store_false",
                        default=env("PUBLISH_TRACKS", "1") != "0")
    args = parser.parse_args()
    try:
        asyncio.run(FakeFusionNode(args).run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
