"""A fake BSI Flex 335 v2.0 edge node (sensor or platform) that talks to Apex.

What it does:
  - connects to an Apex Child port and registers (from the Test Harness template);
  - waits for a RegistrationAck, re-sending the registration every 10 s until one arrives;
  - sends a StatusReport every --status-interval seconds;
  - sensors (radar, camera, ...) report one drone circling a fixed point, once per --detection-interval;
  - platforms (MOBILE_NODE, POINTABLE_NODE) report no detections, but obey their tasks;
  - answers every Task with a TaskAck: accepted if this node type supports the command, else rejected.

Every fake sensor computes the drone's position from the wall clock, so several sensors report
the same drone at the same place (each with its own object ID), as real sensors would.

Usage: python fake_sensor.py --name "Radar 1" --node-type RADAR --port 5020
"""
import argparse
import asyncio
import math
import os
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
from sapient_msg.bsi_flex_335_v2_0.location_pb2 import LOCATION_COORDINATE_SYSTEM_LAT_LNG_DEG_M, LOCATION_DATUM_WGS84_E
from sapient_msg.bsi_flex_335_v2_0.registration_pb2 import Registration
from sapient_msg.bsi_flex_335_v2_0.status_report_pb2 import StatusReport
from sapient_msg.bsi_flex_335_v2_0.task_ack_pb2 import TaskAck
from sapient_msg.bsi_flex_335_v2_0.task_pb2 import Task
from sapient_msg.bsi_flex_335_v2_0.velocity_pb2 import ENUVelocity

PLATFORM_TYPES = {"MOBILE_NODE", "POINTABLE_NODE"}
# Task commands each kind of node accepts; anything else gets "Task not supported".
SUPPORTED_COMMANDS = {
    "MOBILE_NODE": {"request", "move_to", "patrol", "follow"},
    "POINTABLE_NODE": {"request", "look_at"},
    "SENSOR": {
        "request",
        "mode_change",
        "look_at",
        "detection_threshold",
        "detection_report_rate",
        "classification_threshold",
    },
}
# Task command -> Test Harness TaskAck template
ACK_TEMPLATES = {
    "look_at": "TaskAck.LookAt",
    "follow": "TaskAck.Follow",
    "move_to": "TaskAck.MoveTo",
    "patrol": "TaskAck.Patrol",
    "mode_change": "TaskAck.ModeChange",
    "detection_threshold": "TaskAck.DetectionThreshold",
    "detection_report_rate": "TaskAck.DetectionReportRate",
    "classification_threshold": "TaskAck.ClassificationThreshold",
}
REQUESTS = {"Registration", "Reset", "Start", "Status", "Stop"}
PLATFORM_SPEED_MPS = 10.0
REGISTRATION_RETRY_SECONDS = 10


def drone_position(centre_lon: float, centre_lat: float, t: float):
    """A drone circling (centre) at 250 m radius, 120 m altitude, 12 m/s. Returns lon, lat, alt, vE, vN."""
    radius, speed, alt = 250.0, 12.0, 120.0
    angle = (speed / radius) * t
    east, north = radius * math.cos(angle), radius * math.sin(angle)
    v_east, v_north = -speed * math.sin(angle), speed * math.cos(angle)
    lon, lat = offset(centre_lon, centre_lat, east, north)
    return lon, lat, alt, v_east, v_north


def distance_m(lon1, lat1, lon2, lat2) -> tuple[float, float, float]:
    """East, north and total distance in metres from point 1 to point 2."""
    north = math.radians(lat2 - lat1) * 6_371_000.0
    east = math.radians(lon2 - lon1) * 6_371_000.0 * math.cos(math.radians(lat1))
    return east, north, math.hypot(east, north)


def use_lat_lng(message):
    """Switch every LocationType in a registration to WGS84 lat/long, recursively."""
    for field, value in message.ListFields():
        if field.message_type is None:
            continue
        items = value if field.label == field.LABEL_REPEATED else [value]
        for item in items:
            if field.message_type.name == "LocationType":
                item.location_units = LOCATION_COORDINATE_SYSTEM_LAT_LNG_DEG_M
                item.location_datum = LOCATION_DATUM_WGS84_E
                item.ClearField("zone")
            else:
                use_lat_lng(item)


class FakeSensor:
    def __init__(self, args):
        self.args = args
        self.node_id = args.node_id
        self.node_type = args.node_type
        self.kind = self.node_type if self.node_type in PLATFORM_TYPES else "SENSOR"
        self.log = setup_logging(args.short_name)
        self.lon, self.lat = args.lon, args.lat
        self.link = None
        self.registered = asyncio.Event()
        self.detecting = True
        self.status_changed = True  # the next status report is INFO_NEW
        self.active_task = None
        self.route = []  # platform waypoints still to visit
        self.patrol = False
        self.follow_object = None
        self.drone_object_id = new_ulid()
        self.registration = self._build_registration()
        self.mode = self.registration.registration.mode_definition[0].mode_name

    # ---- messages ------------------------------------------------------------------------

    def _build_registration(self):
        msg = load_template("sensor", "Registration")
        reg = msg.registration
        del reg.node_definition[:]
        reg.node_definition.add(node_type=Registration.NodeType.Value(f"NODE_TYPE_{self.node_type}"))
        reg.name = self.args.name
        reg.short_name = self.args.short_name
        del reg.config_data[:]
        reg.config_data.add(
            manufacturer="Apex docker emulator",
            model=f"fake-{self.node_type.lower()}",
            serial_number=self.node_id[:8],
            software_version="1.0",
        )
        reg.dependent_nodes[:] = self.args.dependent_node
        use_lat_lng(reg)
        return msg

    def _status(self) -> StatusReport:
        msg = load_template("sensor", "StatusReport")
        report = msg.status_report
        report.report_id = new_ulid()
        report.system = StatusReport.SYSTEM_OK
        report.info = StatusReport.INFO_NEW if self.status_changed else StatusReport.INFO_UNCHANGED
        report.mode = self.mode
        report.ClearField("active_task_id")
        if self.active_task:
            report.active_task_id = self.active_task
        report.node_location.CopyFrom(lat_lng(self.lon, self.lat, 0, error_m=5))
        # Field of view and coverage: a 1 km square around the node
        corners = [offset(self.lon, self.lat, e, n) for e, n in ((-500, -500), (500, -500), (500, 500), (-500, 500))]
        for area in (report.field_of_view, report.coverage[0]):
            del area.location_list.locations[:]
            area.location_list.locations.extend(lat_lng(lon, lat) for lon, lat in corners)
        del report.obscuration[:]
        del report.status[:]
        if self.kind == "MOBILE_NODE":
            moving = "moving" if self.route or self.follow_object else "holding"
            report.status.add(
                status_level=StatusReport.STATUS_LEVEL_INFORMATION_STATUS,
                status_type=StatusReport.STATUS_TYPE_PLATFORM,
                status_value=moving,
            )
        self.status_changed = False
        return stamp(msg, self.node_id)

    def _detection(self):
        msg = load_template("sensor", "DetectionReport")
        det = msg.detection_report
        for name in ("task_id", "state", "track_info", "prediction_location", "object_info", "behaviour",
                     "associated_file", "signal", "associated_detection", "derived_detection", "colour", "id"):
            det.ClearField(name)
        lon, lat, alt, v_east, v_north = drone_position(self.args.drone_lon, self.args.drone_lat, time.time())
        det.report_id = new_ulid()
        det.object_id = self.drone_object_id
        det.location.CopyFrom(lat_lng(lon, lat, alt, error_m=10))
        det.detection_confidence = 0.9
        del det.classification[:]
        cls = det.classification.add(type="Air Vehicle", confidence=0.9)
        cls.sub_class.add(type="UAV Rotary Wing", confidence=0.8, level=1)
        cls.sub_class[0].sub_class.add(type="Commercial", confidence=0.6, level=2)
        det.enu_velocity.CopyFrom(ENUVelocity(east_rate=v_east, north_rate=v_north, up_rate=0,
                                              east_rate_error=1, north_rate_error=1))
        if self.active_task:
            det.task_id = self.active_task
        return stamp(msg, self.node_id)

    def _task_ack(self, task_msg, accepted: bool, reason: str):
        command = task_msg.task.command.WhichOneof("command")
        if not accepted:
            name = "TaskAck.NotSupported"
        elif command == "request":
            request = task_msg.task.command.request
            name = f"TaskAck.Request.{request if request in REQUESTS else 'Unknown'}"
        else:
            name = ACK_TEMPLATES[command]
        msg = load_template("sensor", name)
        msg.task_ack.task_id = task_msg.task.task_id
        msg.task_ack.ClearField("associated_file")
        msg.task_ack.reason[:] = [reason]
        return stamp(msg, self.node_id, task_msg.node_id)

    # ---- task handling -------------------------------------------------------------------

    def _apply_task(self, task: Task) -> tuple[bool, str]:
        """Carry out a task; return (accepted, reason)."""
        command = task.command.WhichOneof("command")
        if command not in SUPPORTED_COMMANDS[self.kind]:
            return False, f"Task not supported: {self.node_type} nodes cannot do {command}"
        if task.control in (Task.CONTROL_STOP, Task.CONTROL_PAUSE):
            self.route, self.patrol, self.follow_object, self.active_task = [], False, None, None
            self.status_changed = True
            return True, f"{command} stopped"
        self.active_task = task.task_id
        self.status_changed = True
        if command == "request":
            request = task.command.request
            if request == "Stop":
                self.detecting = False
            elif request in ("Start", "Reset"):
                self.detecting = True
            elif request == "Registration":
                asyncio.get_running_loop().create_task(self.link.send(stamp(self.registration, self.node_id)))
            elif request not in REQUESTS:
                return False, f"Unknown request {request!r}"
            return True, f"Request {request} done"
        if command == "mode_change":
            self.mode = task.command.mode_change
            return True, f"Mode changed to {self.mode}"
        if command == "look_at":
            target = task.command.look_at.location_list.locations
            where = f"({target[0].y:.5f}, {target[0].x:.5f})" if target else "range/bearing"
            return True, f"Pointing at {where}"
        if command in ("move_to", "patrol"):
            locations = getattr(task.command, command).locations
            if not locations:
                return False, f"{command} has no locations"
            self.route = [(loc.x, loc.y) for loc in locations]
            self.patrol, self.follow_object = command == "patrol", None
            return True, f"{command} accepted: {len(self.route)} waypoint(s)"
        if command == "follow":
            self.follow_object, self.route, self.patrol = task.command.follow.follow_object_id, [], False
            return True, f"Following object {self.follow_object}"
        return True, f"{command} accepted"

    # ---- loops ---------------------------------------------------------------------------

    async def _receive_loop(self):
        while True:
            msg = await self.link.receive()
            kind = msg.WhichOneof("content")
            self.log.info(f"<- {summary(msg)}")
            if kind == "registration_ack":
                if msg.registration_ack.acceptance:
                    self.registered.set()
                else:
                    self.log.info("registration rejected; will retry")
            elif kind == "task":
                accepted, reason = self._apply_task(msg.task)
                ack = self._task_ack(msg, accepted, reason)
                await self.link.send(ack)
                self.log.info(f"-> {summary(ack)}")

    async def _register(self):
        """Send the registration until it is accepted (re-sending every 10 s)."""
        while not self.registered.is_set():
            msg = stamp(self.registration, self.node_id)
            await self.link.send(msg)
            self.log.info(f"-> {summary(msg)}")
            try:
                await asyncio.wait_for(self.registered.wait(), REGISTRATION_RETRY_SECONDS)
            except asyncio.TimeoutError:
                self.log.info(f"no RegistrationAck after {REGISTRATION_RETRY_SECONDS} s (is a fusion node connected?)")
        self.status_changed = True

    async def _status_loop(self):
        while True:
            msg = self._status()
            await self.link.send(msg)
            if msg.status_report.info == StatusReport.INFO_NEW:
                self.log.info(f"-> {summary(msg)}")
            await asyncio.sleep(self.args.status_interval)

    async def _detection_loop(self):
        count = 0
        while True:
            if self.detecting:
                msg = self._detection()
                await self.link.send(msg)
                if count % 10 == 0:
                    self.log.info(f"-> {summary(msg)}  (logging every 10th)")
                count += 1
            await asyncio.sleep(self.args.detection_interval)

    async def _motion_loop(self):
        """Move a mobile platform along its route, or after the drone, at 10 m/s."""
        while True:
            await asyncio.sleep(1)
            if self.follow_object:
                lon, lat, *_ = drone_position(self.args.drone_lon, self.args.drone_lat, time.time())
                target = (lon, lat)
            elif self.route:
                target = self.route[0]
            else:
                continue
            east, north, dist = distance_m(self.lon, self.lat, *target)
            if dist <= PLATFORM_SPEED_MPS:
                self.lon, self.lat = target
                if self.route and not self.follow_object:
                    reached = self.route.pop(0)
                    self.log.info(f"reached waypoint ({reached[1]:.5f}, {reached[0]:.5f})")
                    if self.patrol:
                        self.route.append(reached)
                    elif not self.route:
                        self.active_task = None
                    self.status_changed = True
            else:
                step = PLATFORM_SPEED_MPS / dist
                self.lon, self.lat = offset(self.lon, self.lat, east * step, north * step)

    async def run(self):
        while True:
            self.link = await Link.connect(self.args.host, self.args.port, self.log)
            self.registered.clear()
            try:
                async with asyncio.TaskGroup() as group:
                    group.create_task(self._receive_loop())
                    await self._register()
                    group.create_task(self._status_loop())
                    if self.kind == "SENSOR":
                        group.create_task(self._detection_loop())
                    if self.kind == "MOBILE_NODE":
                        group.create_task(self._motion_loop())
            except* (asyncio.IncompleteReadError, ConnectionError):
                self.log.info("connection to Apex lost; reconnecting")
            finally:
                self.link.close()
            await asyncio.sleep(10)


def main():
    env = os.environ.get
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=env("APEX_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(env("APEX_PORT", "5020")), help="Apex Child port (v2.0)")
    parser.add_argument("--node-id", default=env("NODE_ID") or str(uuid.uuid4()))
    parser.add_argument("--name", default=env("NODE_NAME", "Fake radar"))
    parser.add_argument("--short-name", default=env("NODE_SHORT_NAME", "radar"))
    parser.add_argument("--node-type", default=env("NODE_TYPE", "RADAR"),
                        help="RADAR, CAMERA, PASSIVE_RF, ... or MOBILE_NODE / POINTABLE_NODE for a platform")
    parser.add_argument("--dependent-node", action="append", default=[n for n in env("DEPENDENT_NODES", "").split(",") if n],
                        help="node ID carried by this platform (repeatable)")
    parser.add_argument("--lat", type=float, default=float(env("NODE_LAT", "51.1739")), help="node latitude")
    parser.add_argument("--lon", type=float, default=float(env("NODE_LON", "-1.8224")), help="node longitude")
    parser.add_argument("--drone-lat", type=float, default=float(env("DRONE_LAT", "51.1760")))
    parser.add_argument("--drone-lon", type=float, default=float(env("DRONE_LON", "-1.8180")))
    parser.add_argument("--status-interval", type=float, default=float(env("STATUS_INTERVAL", "5")))
    parser.add_argument("--detection-interval", type=float, default=float(env("DETECTION_INTERVAL", "1")))
    args = parser.parse_args()
    args.node_type = args.node_type.upper().removeprefix("NODE_TYPE_")
    try:
        asyncio.run(FakeSensor(args).run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
