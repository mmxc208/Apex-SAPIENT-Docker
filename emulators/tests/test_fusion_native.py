"""The fusion node's Zenoh-only duties: validation, re-registration requests, its own status."""
import argparse
import asyncio
import io
import logging
import re
import sys

import pytest
from google.protobuf.message import DecodeError

import fake_fusion_node
from conftest import FakeZenohSession
from fake_fusion_node import FakeFusionNode
from sapient_link import ZenohFusionLink, load_template, new_ulid, stamp, summary
from sapient_msg.bsi_flex_335_v2_0.registration_pb2 import Registration
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from sapient_msg.bsi_flex_335_v2_0.status_report_pb2 import StatusReport
from sapient_msg.bsi_flex_335_v2_0.task_ack_pb2 import TaskAck
from zenoh_io import ZenohSession
from zenoh_keys import LIVE_ALL, UP_ALL, down_key, fusion_down_key, fusion_up_key, live_key, qos_for, up_key

NODE = "a0000001-0000-4000-8000-000000000001"
OTHER = "a0000002-0000-4000-8000-000000000002"
FUSION = "f0000001-0000-4000-8000-000000000001"
PEER_FUSION = "f0000002-0000-4000-8000-000000000002"
TIMEOUT = 5
HOLD = 0.05
UNDECODABLE = b"\xff\xff\xff"


def fusion_args(**overrides):
    values = dict(
        node_id=FUSION,
        auto_task="",
        host="apex",
        port=5001,
        transport="zenoh",
        zenoh_connect="tcp/zenohd:7447",
        status_interval=0.01,
        publish_tracks=False,
        node_hold_seconds=HOLD,
    )
    return argparse.Namespace(**{**values, **overrides})


@pytest.fixture
def fake_session():
    return FakeZenohSession()


@pytest.fixture
def fusion(fake_session):
    node = FakeFusionNode(fusion_args())
    node.link = ZenohFusionLink(fake_session, FUSION, fake_session.subscribe(UP_ALL))
    return node


@pytest.fixture
async def receiving(fusion):
    """The fusion node with its receive loop running."""
    task = asyncio.create_task(fusion._receive_loop())
    yield fusion
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.fixture
async def republishing(receiving, monkeypatch):
    """The fusion node re-announcing itself with no debounce delay."""
    monkeypatch.setattr(fake_fusion_node, "REGISTRATION_DEBOUNCE_SECONDS", 0)
    task = asyncio.create_task(receiving._registration_loop())
    yield receiving
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.fixture
async def tracking(republishing, fake_session, monkeypatch):
    """The fusion node following liveliness and the transport, with no grace before a request."""
    monkeypatch.setattr(fake_fusion_node, "REQUEST_GRACE_SECONDS", 0)
    tasks = [
        asyncio.create_task(republishing._track_liveliness(fake_session.liveliness(LIVE_ALL))),
        asyncio.create_task(republishing._track_transport(fake_session.transport_changes)),
        asyncio.create_task(republishing._request_loop()),
    ]
    yield republishing
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def published_on(session, key) -> list[SapientMessage]:
    return [SapientMessage.FromString(payload) for k, payload, _ in session.published if k == key]


async def until(condition):
    async def poll():
        while not condition():
            await asyncio.sleep(0)

    await asyncio.wait_for(poll(), TIMEOUT)


def registration(templates, node_id=NODE):
    return stamp(templates("sensor", "Registration"), node_id)


def with_capabilities(msg, *pairs):
    del msg.registration.capabilities[:]
    for category, capability_type in pairs:
        msg.registration.capabilities.add(category=category, type=capability_type, value="1", units="u")
    return msg


def with_commands(msg, *commands):
    task = msg.registration.mode_definition[0].task
    stock = Registration.Command()
    stock.CopyFrom(task.command[0])
    del task.command[:]
    for command_type, units in commands:
        command = task.command.add()
        command.CopyFrom(stock)
        command.type = command_type
        command.units = units
    return msg


def fusion_typed_registration(templates, node_id=PEER_FUSION):
    msg = registration(templates, node_id)
    del msg.registration.node_definition[:]
    msg.registration.node_definition.add(node_type=Registration.NodeType.NODE_TYPE_FUSION_NODE)
    return msg


def detection(templates, node_id=NODE):
    msg = stamp(templates("sensor", "DetectionReport"), node_id)
    msg.detection_report.report_id = new_ulid()
    msg.detection_report.object_id = new_ulid()
    msg.detection_report.ClearField("task_id")
    return msg


def test_validate_rejects_missing_mandatory_field(fusion, templates):
    msg = registration(templates)
    msg.ClearField("node_id")

    assert "node_id" in fusion.validate(msg)


def test_validate_accepts_template_registration(fusion, templates):
    assert fusion.validate(registration(templates)) is None


def test_validate_is_left_to_apex_on_tcp(templates):
    msg = registration(templates)
    msg.ClearField("node_id")

    assert FakeFusionNode(fusion_args(transport="tcp")).validate(msg) is None


def test_validate_keeps_detection_timing_per_sender(fusion, templates):
    """Apex has one validator per connection; here every sender shares one subscription."""
    assert fusion.validate(detection(templates, NODE)) is None
    assert fusion.validate(detection(templates, OTHER)) is None


def test_validate_still_rejects_detections_too_close_from_one_sender(fusion, templates):
    first, second = detection(templates), detection(templates)
    second.timestamp.FromNanoseconds(first.timestamp.ToNanoseconds() + 1_000_000)

    assert fusion.validate(first) is None
    assert "too small" in fusion.validate(second)


def missing_icd_version(msg):
    msg.registration.ClearField("icd_version")


def absurd_timestamp(msg):
    msg.timestamp.seconds = 2**62


@pytest.mark.parametrize("damage", [missing_icd_version, absurd_timestamp])
def test_validate_reports_a_message_that_crashes_the_validator(fusion, templates, damage):
    msg = registration(templates)
    damage(msg)

    assert fusion.validate(msg)


async def test_invalid_message_gets_error_reply_on_down_key(receiving, fake_session, templates):
    msg = registration(templates)
    msg.registration.ClearField("name")
    msg.registration.ClearField("config_data")
    payload = msg.SerializeToString()

    fake_session.inject(up_key(NODE, "registration"), payload)
    await until(lambda: published_on(fake_session, down_key(NODE, "error")))

    [reply] = published_on(fake_session, down_key(NODE, "error"))
    assert reply.error.packet == payload
    assert len(reply.error.error_message) == 1
    assert "config_data" in reply.error.error_message[0]
    assert (reply.node_id, reply.destination_id) == (FUSION, NODE)
    assert NODE not in receiving.nodes
    assert not published_on(fake_session, down_key(NODE, "registration_ack"))


async def test_valid_registration_resets_the_senders_detection_state(
    receiving, fake_session, templates
):
    errors = lambda: published_on(fake_session, down_key(NODE, "error"))
    ahead = detection(templates)
    ahead.timestamp.FromSeconds(ahead.timestamp.seconds + 3600)

    fake_session.inject(up_key(NODE, "detection_report"), ahead.SerializeToString())
    await until(lambda: len(errors()) == 1)
    fake_session.inject(up_key(NODE, "detection_report"), detection(templates).SerializeToString())
    await until(lambda: len(errors()) == 2)
    assert "earlier than previous" in errors()[1].error.error_message[0]

    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "registration_ack")))
    fake_session.inject(up_key(NODE, "detection_report"), detection(templates).SerializeToString())
    await until(lambda: NODE in receiving.detection_counts)

    assert len(errors()) == 2


async def test_error_goes_to_the_key_owner_when_the_message_has_no_node_id(
    receiving, fake_session, templates
):
    msg = registration(templates)
    msg.ClearField("node_id")

    fake_session.inject(up_key(NODE, "registration"), msg.SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "error")))

    assert "node_id" in published_on(fake_session, down_key(NODE, "error"))[0].error.error_message[0]


async def test_valid_message_after_an_invalid_one_is_processed(receiving, fake_session, templates):
    fake_session.inject(up_key(NODE, "registration"), SapientMessage().SerializeToString())
    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())

    await until(lambda: published_on(fake_session, down_key(NODE, "registration_ack")))

    assert NODE in receiving.nodes


async def test_undecodable_message_gets_error_reply_from_its_key(
    receiving, fake_session, templates
):
    fake_session.inject(up_key(NODE, "registration"), UNDECODABLE)
    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())

    await until(lambda: published_on(fake_session, down_key(NODE, "registration_ack")))

    [reply] = published_on(fake_session, down_key(NODE, "error"))
    assert reply.error.packet == UNDECODABLE
    assert list(reply.error.error_message) == ["undecodable message"]


def status_as(templates, node_id):
    msg = stamp(templates("sensor", "StatusReport"), node_id)
    msg.status_report.report_id = new_ulid()
    msg.status_report.info = StatusReport.INFO_NEW
    msg.status_report.mode = "CLAIMED"
    return msg


@pytest.mark.parametrize(
    "kind, build",
    [("registration", registration), ("status_report", status_as), ("detection_report", detection)],
)
async def test_message_claiming_another_node_is_dropped_and_the_key_owner_told(
    receiving, fake_session, templates, kind, build
):
    await receiving._on_registration(registration(templates, OTHER))
    before = dict(receiving.nodes[OTHER])
    payload = build(templates, OTHER).SerializeToString()

    fake_session.inject(up_key(NODE, kind), payload)
    await until(lambda: published_on(fake_session, down_key(NODE, "error")))

    [reply] = published_on(fake_session, down_key(NODE, "error"))
    assert reply.error.packet == payload
    assert (reply.node_id, reply.destination_id) == (FUSION, NODE)
    assert OTHER in reply.error.error_message[0] and NODE in reply.error.error_message[0]
    assert not published_on(fake_session, down_key(OTHER, "error"))
    assert receiving.nodes[OTHER] == before
    assert NODE not in receiving.nodes
    assert OTHER not in receiving.detection_counts
    assert OTHER not in receiving.validators


async def test_a_node_id_in_another_form_does_not_match_its_key(receiving, fake_session, templates):
    fake_session.inject(up_key(NODE, "status_report"), status_as(templates, NODE.upper()).SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "error")))

    assert not receiving.nodes


async def test_message_with_a_node_id_on_a_malformed_key_is_only_logged(
    receiving, fake_session, templates, caplog
):
    with caplog.at_level(logging.INFO):
        fake_session.inject("sapient/v2/not-a-uuid/up/status_report", status_as(templates, OTHER).SerializeToString())
        fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
        await until(lambda: published_on(fake_session, down_key(NODE, "registration_ack")))

    assert [key for key, _, _ in fake_session.published] == [down_key(NODE, "registration_ack")]
    assert OTHER not in receiving.nodes
    assert "malformed key" in caplog.text


async def test_undecodable_message_on_a_bad_key_is_only_logged(
    receiving, fake_session, templates, caplog
):
    with caplog.at_level(logging.INFO):
        fake_session.inject("sapient/v2/not-a-uuid/up/registration", UNDECODABLE)
        fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
        await until(lambda: published_on(fake_session, down_key(NODE, "registration_ack")))

    assert [key for key, _, _ in fake_session.published] == [down_key(NODE, "registration_ack")]
    assert "undecodable message" in caplog.text


async def test_request_registrations_tasks_each_alive_node(fusion, fake_session):
    fake_session.declare_token(live_key(NODE))
    fake_session.declare_token(live_key(OTHER))

    await fusion.request_registrations()

    for node_id in (NODE, OTHER):
        [task] = published_on(fake_session, down_key(node_id, "task"))
        assert task.task.command.request == "Registration"
        assert (task.node_id, task.destination_id) == (FUSION, node_id)


async def test_request_registrations_skips_a_malformed_token(fusion, fake_session):
    fake_session.declare_token("sapient/v2/live/not-a-uuid")
    fake_session.declare_token(live_key(NODE))

    await fusion.request_registrations()

    assert [key for key, _, _ in fake_session.published] == [down_key(NODE, "task")]


async def test_own_status_new_then_unchanged(fusion, fake_session):
    key = up_key(FUSION, "status_report")
    task = asyncio.create_task(fusion._own_status_loop())

    await until(lambda: len(published_on(fake_session, key)) >= 2)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    first, second = published_on(fake_session, key)[:2]
    assert first.status_report.info == StatusReport.INFO_NEW
    assert second.status_report.info == StatusReport.INFO_UNCHANGED
    assert first.node_id == FUSION
    assert not first.HasField("destination_id")
    assert first.status_report.report_id != second.status_report.report_id
    assert first.status_report.system == StatusReport.SYSTEM_OK
    assert fusion.validate(first) is None


def status_report(templates, info, node_id=NODE):
    msg = stamp(templates("sensor", "StatusReport"), node_id)
    msg.status_report.report_id = new_ulid()
    msg.status_report.info = info
    return msg


async def test_unchanged_status_before_any_new_is_logged(fusion, templates, caplog):
    await fusion._on_registration(registration(templates))
    with caplog.at_level(logging.INFO):
        fusion._on_status(status_report(templates, StatusReport.INFO_UNCHANGED))
    assert re.search("Unchanged.*before", caplog.text)


async def test_unchanged_after_new_is_not_logged(fusion, templates, caplog):
    await fusion._on_registration(registration(templates))
    with caplog.at_level(logging.INFO):
        fusion._on_status(status_report(templates, StatusReport.INFO_NEW))
        fusion._on_status(status_report(templates, StatusReport.INFO_UNCHANGED))
        fusion._on_status(status_report(templates, StatusReport.INFO_UNCHANGED))
    assert "before" not in caplog.text


async def test_unchanged_after_a_re_registration_with_no_new_is_logged(fusion, templates, caplog):
    await fusion._on_registration(registration(templates))
    fusion._on_status(status_report(templates, StatusReport.INFO_NEW))
    await fusion._on_registration(registration(templates))
    with caplog.at_level(logging.INFO):
        fusion._on_status(status_report(templates, StatusReport.INFO_UNCHANGED))
    assert re.search("Unchanged.*before", caplog.text)


def test_unchanged_from_a_node_not_yet_registered_is_not_logged(fusion, templates, caplog):
    """A restarted fusion node hears running sensors before they register again."""
    with caplog.at_level(logging.INFO):
        fusion._on_status(status_report(templates, StatusReport.INFO_UNCHANGED))
    assert "before" not in caplog.text


def test_fusion_registration_describes_a_fusion_node(fusion):
    msg = fusion.build_fusion_registration()

    reg = msg.registration
    assert msg.node_id == FUSION
    assert not msg.HasField("destination_id")
    assert [d.node_type for d in reg.node_definition] == [Registration.NodeType.NODE_TYPE_FUSION_NODE]
    assert (reg.name, reg.short_name) == ("fake fusion node", "fusion")
    assert reg.icd_version == "BSI Flex 335 v2.0"
    assert not reg.dependent_nodes


def test_fusion_registration_reports_its_status_interval_in_seconds():
    reg = FakeFusionNode(fusion_args(status_interval=10.0)).build_fusion_registration().registration

    assert reg.status_definition.status_interval.value == 10.0
    assert reg.status_definition.status_interval.units == Registration.TIME_UNITS_SECONDS


async def test_fusion_registration_aggregates_capabilities(fusion, templates):
    first = with_capabilities(registration(templates, NODE), ("A", "x"), ("B", "y"))
    second = with_capabilities(registration(templates, OTHER), ("B", "y"), ("C", "z"))
    await fusion._on_registration(first)
    await fusion._on_registration(second)

    reg = fusion.build_fusion_registration().registration

    assert [(c.category, c.type) for c in reg.capabilities] == [("A", "x"), ("B", "y"), ("C", "z")]
    assert [d.node_type for d in reg.node_definition] == [Registration.NodeType.NODE_TYPE_FUSION_NODE]


async def test_fusion_registration_dedupes_on_category_and_type_only(fusion, templates):
    first = with_capabilities(registration(templates, NODE), ("A", "x"), ("A", "y"))
    await fusion._on_registration(first)

    reg = fusion.build_fusion_registration().registration

    assert [(c.category, c.type) for c in reg.capabilities] == [("A", "x"), ("A", "y")]


async def test_fusion_registration_unions_task_commands(fusion, templates):
    patrol, look_at, move_to = (Registration.COMMAND_TYPE_PATROL, Registration.COMMAND_TYPE_LOOK_AT, Registration.COMMAND_TYPE_MOVE_TO)
    await fusion._on_registration(with_commands(registration(templates, NODE), (patrol, "Status"), (look_at, "Status")))
    await fusion._on_registration(with_commands(registration(templates, OTHER), (patrol, "Status"), (move_to, "Status")))

    commands = fusion.build_fusion_registration().registration.mode_definition[0].task.command

    assert [c.type for c in commands] == [patrol, look_at, move_to]


async def test_fusion_registration_passes_apex_validator_once_a_sensor_is_registered(fusion, templates):
    await fusion._on_registration(registration(templates))

    assert fusion.validate(fusion.build_fusion_registration()) is None


def test_fusion_registration_without_sensors_would_fail_validation(fusion):
    """Why nothing is published until the first sensor registers: capabilities are mandatory."""
    assert "registration.capabilities" in fusion.validate(fusion.build_fusion_registration())


async def test_no_registration_published_until_a_sensor_registers(fusion, fake_session):
    await fusion._announce()

    assert not published_on(fake_session, fusion_up_key("registration"))
    assert not published_on(fake_session, up_key(FUSION, "registration"))
    assert not fusion.own_registered.is_set()


async def test_announce_publishes_at_once_when_sensors_are_already_known(fusion, fake_session, templates):
    """After a reconnect the registry is still full, so there is nothing to wait for."""
    await fusion._on_registration(registration(templates))

    await fusion._announce()

    assert len(published_on(fake_session, fusion_up_key("registration"))) == 1
    assert fusion.own_registered.is_set()


async def test_fusion_registration_goes_to_both_keys(fusion, fake_session, templates):
    await fusion._on_registration(registration(templates))

    await fusion._publish_registration()

    [upward] = published_on(fake_session, fusion_up_key("registration"))
    [own] = published_on(fake_session, up_key(FUSION, "registration"))
    assert upward == own
    assert upward.node_id == FUSION


@pytest.mark.usefixtures("republishing")
async def test_fusion_registration_republished_on_new_node(fusion, fake_session):
    key = fusion_up_key("registration")

    fake_session.inject(up_key(NODE, "registration"), registration(load_template, NODE).SerializeToString())
    await until(lambda: len(published_on(fake_session, key)) == 1)
    fake_session.inject(up_key(OTHER, "registration"), registration(load_template, OTHER).SerializeToString())
    await until(lambda: len(published_on(fake_session, key)) == 2)

    assert {NODE, OTHER} <= set(fusion.nodes)


@pytest.mark.usefixtures("republishing")
async def test_fusion_registration_republished_when_a_node_changes_its_capabilities(fusion, fake_session, templates):
    key = fusion_up_key("registration")
    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: len(published_on(fake_session, key)) == 1)

    changed = with_capabilities(registration(templates), ("New", "capability"))
    fake_session.inject(up_key(NODE, "registration"), changed.SerializeToString())
    await until(lambda: len(published_on(fake_session, key)) == 2)

    assert [c.category for c in published_on(fake_session, key)[1].registration.capabilities] == ["New"]


@pytest.mark.usefixtures("republishing")
async def test_identical_re_registration_does_not_republish(fusion, fake_session, templates):
    key = fusion_up_key("registration")
    acks = lambda: published_on(fake_session, down_key(NODE, "registration_ack"))
    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: len(published_on(fake_session, key)) == 1)

    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: len(acks()) == 2)

    assert not fusion.registry_changed.is_set()
    assert len(published_on(fake_session, key)) == 1


def test_registration_debounce_is_five_seconds():
    assert fake_fusion_node.REGISTRATION_DEBOUNCE_SECONDS == 5


async def test_registrations_inside_the_debounce_window_publish_once(receiving, fake_session, templates, monkeypatch):
    monkeypatch.setattr(fake_fusion_node, "REGISTRATION_DEBOUNCE_SECONDS", 0.05)
    key = fusion_up_key("registration")
    task = asyncio.create_task(receiving._registration_loop())

    first = with_capabilities(registration(templates, NODE), ("A", "x"))
    second = with_capabilities(registration(templates, OTHER), ("B", "y"))
    fake_session.inject(up_key(NODE, "registration"), first.SerializeToString())
    fake_session.inject(up_key(OTHER, "registration"), second.SerializeToString())
    await until(lambda: published_on(fake_session, key))
    await asyncio.sleep(0.15)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    [reg] = published_on(fake_session, key)
    assert [c.category for c in reg.registration.capabilities] == ["A", "B"]


async def test_own_status_waits_for_own_registration(fusion, fake_session, templates):
    status_key = up_key(FUSION, "status_report")
    task = asyncio.create_task(fusion._status_once_registered())
    for _ in range(20):
        await asyncio.sleep(0)
    assert not published_on(fake_session, status_key)

    await fusion._on_registration(registration(templates))
    await fusion._publish_registration()
    await until(lambda: published_on(fake_session, status_key))
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    keys = [key for key, _, _ in fake_session.published]
    assert keys.index(up_key(FUSION, "registration")) < keys.index(status_key)


@pytest.mark.usefixtures("republishing")
async def test_own_status_is_new_after_a_re_announced_registration(fusion, fake_session, templates):
    reg_key, status_key = fusion_up_key("registration"), up_key(FUSION, "status_report")

    def statuses_after_last_registration():
        keys_and_payloads = [(key, payload) for key, payload, _ in fake_session.published]
        last = max(i for i, (key, _) in enumerate(keys_and_payloads) if key == reg_key)
        return [SapientMessage.FromString(p).status_report.info for k, p in keys_and_payloads[last:] if k == status_key]

    fake_session.inject(up_key(NODE, "registration"), registration(templates, NODE).SerializeToString())
    await until(lambda: len(published_on(fake_session, reg_key)) == 1)
    task = asyncio.create_task(fusion._status_once_registered())
    await until(lambda: len(statuses_after_last_registration()) >= 2)

    fake_session.inject(up_key(OTHER, "registration"), registration(templates, OTHER).SerializeToString())
    await until(lambda: len(published_on(fake_session, reg_key)) == 2)
    await until(lambda: len(statuses_after_last_registration()) >= 2)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert statuses_after_last_registration()[:2] == [StatusReport.INFO_NEW, StatusReport.INFO_UNCHANGED]


async def test_no_track_before_own_registration(receiving, fake_session, templates):
    """A restarted node hears detections during the debounce, before it has registered upward."""
    receiving.args.publish_tracks = True

    fake_session.inject(up_key(NODE, "detection_report"), detection(templates).SerializeToString())
    await until(lambda: NODE in receiving.detection_counts)

    assert not published_on(fake_session, fusion_up_key("detection_report"))
    assert not published_on(fake_session, up_key(FUSION, "detection_report"))


async def test_tracks_flow_once_registered(receiving, fake_session, templates):
    receiving.args.publish_tracks = True
    await receiving._on_registration(registration(templates))
    await receiving._publish_registration()

    fake_session.inject(up_key(NODE, "detection_report"), detection(templates).SerializeToString())
    await until(lambda: published_on(fake_session, fusion_up_key("detection_report")))

    keys = [key for key, _, _ in fake_session.published]
    assert keys.index(fusion_up_key("registration")) < keys.index(fusion_up_key("detection_report"))


async def test_tcp_tracks_do_not_wait_for_an_own_registration(fake_session, templates):
    """Over TCP, Apex is the parent and this node publishes no Registration of its own."""
    node = FakeFusionNode(fusion_args(transport="tcp", publish_tracks=True))
    node.link = ZenohFusionLink(fake_session, FUSION, fake_session.subscribe(UP_ALL))

    await node._on_detection(detection(templates))

    assert published_on(fake_session, up_key(FUSION, "detection_report"))
    assert not published_on(fake_session, fusion_up_key("detection_report"))


async def test_fused_track_is_mirrored_to_the_fusion_key(receiving, fake_session, templates):
    receiving.args.publish_tracks = True
    await receiving._on_registration(registration(templates))
    await receiving._publish_registration()
    raw = detection(templates)

    fake_session.inject(up_key(NODE, "detection_report"), raw.SerializeToString())
    await until(lambda: published_on(fake_session, fusion_up_key("detection_report")))

    [mirrored] = published_on(fake_session, fusion_up_key("detection_report"))
    [own] = published_on(fake_session, up_key(FUSION, "detection_report"))
    assert mirrored == own
    assert mirrored.node_id == FUSION
    assert mirrored.detection_report.report_id != raw.detection_report.report_id
    qos = [q for key, _, q in fake_session.published if key == fusion_up_key("detection_report")]
    assert qos == [qos_for("detection_report", fused=True)]


async def test_raw_detection_with_tracks_off_reaches_no_fusion_key(receiving, fake_session, templates):
    fake_session.inject(up_key(NODE, "detection_report"), detection(templates).SerializeToString())
    await until(lambda: NODE in receiving.detection_counts)

    assert not published_on(fake_session, fusion_up_key("detection_report"))


async def test_other_fusion_nodes_registration_is_not_validated(receiving, fake_session, templates):
    """Its registration is no sensor joining this node: no Error, no ack, no share of the aggregate."""
    invalid = fusion_typed_registration(templates)
    invalid.registration.ClearField("capabilities")

    fake_session.inject(up_key(PEER_FUSION, "registration"), invalid.SerializeToString())
    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "registration_ack")))

    assert not published_on(fake_session, down_key(PEER_FUSION, "error"))
    assert not published_on(fake_session, down_key(PEER_FUSION, "registration_ack"))
    assert PEER_FUSION not in receiving.nodes


async def test_other_fusion_nodes_later_messages_are_not_validated(receiving, fake_session, templates):
    fake_session.inject(up_key(PEER_FUSION, "registration"), fusion_typed_registration(templates).SerializeToString())
    bad = detection(templates, PEER_FUSION)
    bad.ClearField("timestamp")
    fake_session.inject(up_key(PEER_FUSION, "detection_report"), bad.SerializeToString())
    fake_session.inject(up_key(PEER_FUSION, "status_report"), UNDECODABLE)
    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "registration_ack")))

    assert not published_on(fake_session, down_key(PEER_FUSION, "error"))
    assert PEER_FUSION not in receiving.detection_counts


async def test_fusion_typed_registration_without_node_id_filters_only_its_key_owner(receiving, fake_session, templates):
    """A missing node_id must not silence every other message that lacks one."""
    nameless = fusion_typed_registration(templates)
    nameless.ClearField("node_id")
    broken = registration(templates)
    broken.ClearField("node_id")

    fake_session.inject(up_key(PEER_FUSION, "registration"), nameless.SerializeToString())
    fake_session.inject(up_key(NODE, "registration"), broken.SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "error")))

    assert not published_on(fake_session, down_key(PEER_FUSION, "error"))


async def join(session, templates, node_id, *capabilities):
    """A node declares its token and registers; returns once the fusion node has it."""
    session.declare_token(live_key(node_id))
    msg = with_capabilities(registration(templates, node_id), *capabilities)
    session.inject(up_key(node_id, "registration"), msg.SerializeToString())
    await until(lambda: published_on(session, down_key(node_id, "registration_ack")))


def registration_requests(session, node_id):
    return [t for t in published_on(session, down_key(node_id, "task")) if t.task.command.request == "Registration"]


async def test_token_loss_then_hold_expiry_removes_the_node_and_republishes(tracking, fake_session, templates):
    key = fusion_up_key("registration")
    await join(fake_session, templates, NODE, ("A", "x"))
    await join(fake_session, templates, OTHER, ("B", "y"))
    await until(lambda: published_on(fake_session, key))
    tracking.validate(detection(templates, NODE))
    published = len(published_on(fake_session, key))

    fake_session.undeclare_token(live_key(NODE))
    await until(lambda: NODE not in tracking.nodes)
    await until(lambda: len(published_on(fake_session, key)) > published)

    assert [c.category for c in published_on(fake_session, key)[-1].registration.capabilities] == ["B"]
    assert NODE not in tracking.validators
    assert OTHER in tracking.nodes


async def test_node_is_kept_until_the_hold_ends(tracking, fake_session, templates):
    tracking.args.node_hold_seconds = 60
    await join(fake_session, templates, NODE, ("A", "x"))

    fake_session.undeclare_token(live_key(NODE))
    await until(lambda: NODE in tracking._hold_timers)
    await asyncio.sleep(HOLD * 2)

    assert NODE in tracking.nodes


async def test_token_flap_within_the_hold_keeps_the_node(tracking, fake_session, templates):
    await join(fake_session, templates, NODE, ("A", "x"))

    fake_session.undeclare_token(live_key(NODE))
    fake_session.declare_token(live_key(NODE))
    await asyncio.sleep(HOLD * 3)

    assert NODE in tracking.nodes
    assert not tracking._hold_timers


async def test_malformed_token_is_ignored(tracking, fake_session, templates, caplog):
    with caplog.at_level(logging.INFO):
        fake_session.declare_token("sapient/v2/live/not-a-uuid")
        await join(fake_session, templates, NODE, ("A", "x"))
        await until(lambda: "bad key" in caplog.text)


async def test_transport_return_keeps_nodes_whose_tokens_are_present(tracking, fake_session, templates):
    await join(fake_session, templates, NODE, ("A", "x"))
    await join(fake_session, templates, OTHER, ("B", "y"))

    fake_session.lose_transport()
    await until(lambda: len(tracking._hold_timers) == 2)
    fake_session.undeclare_token(live_key(OTHER))  # goes during the outage, so nothing reports it
    fake_session.restore_transport(report_tokens=False)
    await until(lambda: OTHER not in tracking.nodes)
    await asyncio.sleep(HOLD * 2)

    assert NODE in tracking.nodes


async def test_transport_loss_holds_a_node_that_never_showed_a_token(tracking, fake_session, templates):
    await tracking._on_registration(registration(templates))

    fake_session.lose_transport()

    await until(lambda: NODE not in tracking.nodes)


async def test_node_removed_by_a_long_outage_is_asked_to_register_on_return(tracking, fake_session, templates):
    await join(fake_session, templates, NODE, ("A", "x"))

    fake_session.lose_transport()
    await until(lambda: NODE not in tracking.nodes)
    assert not registration_requests(fake_session, NODE)
    fake_session.restore_transport()

    await until(lambda: registration_requests(fake_session, NODE))


async def test_status_from_a_returning_node_does_not_stop_the_request(tracking, fake_session, templates, monkeypatch):
    """Status arrives first after an outage; only a Registration counts as registered."""
    monkeypatch.setattr(fake_fusion_node, "REQUEST_GRACE_SECONDS", HOLD)
    await join(fake_session, templates, NODE, ("A", "x"))
    fake_session.lose_transport()
    await until(lambda: NODE not in tracking.nodes)

    fake_session.restore_transport()
    fake_session.inject(up_key(NODE, "status_report"), status_as(templates, NODE).SerializeToString())

    await until(lambda: registration_requests(fake_session, NODE))


async def test_no_request_when_the_registration_arrives_within_the_grace(tracking, fake_session, templates, monkeypatch):
    monkeypatch.setattr(fake_fusion_node, "REQUEST_GRACE_SECONDS", HOLD)

    await join(fake_session, templates, NODE, ("A", "x"))
    await asyncio.sleep(HOLD * 3)

    assert not registration_requests(fake_session, NODE)


async def test_no_request_once_the_token_has_gone_again(tracking, fake_session, monkeypatch):
    monkeypatch.setattr(fake_fusion_node, "REQUEST_GRACE_SECONDS", HOLD)

    fake_session.declare_token(live_key(NODE))
    await until(lambda: NODE in tracking._pending_requests)
    fake_session.undeclare_token(live_key(NODE))
    await asyncio.sleep(HOLD * 3)

    assert not registration_requests(fake_session, NODE)


async def test_registration_in_flight_when_the_hold_ended_is_removed_again(tracking, fake_session, templates):
    fake_session.declare_token(live_key(NODE))
    await until(lambda: tracking._token_alive.get(NODE) is True)
    fake_session.undeclare_token(live_key(NODE))
    await until(lambda: tracking._token_alive.get(NODE) is False)
    await until(lambda: NODE not in tracking._hold_timers)

    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: NODE in tracking.nodes)

    await until(lambda: NODE not in tracking.nodes)


async def test_status_after_removal_does_not_leave_a_node_behind(tracking, fake_session, templates):
    await join(fake_session, templates, NODE, ("A", "x"))
    fake_session.undeclare_token(live_key(NODE))
    await until(lambda: NODE not in tracking.nodes)

    fake_session.inject(up_key(NODE, "status_report"), status_as(templates, NODE).SerializeToString())
    await until(lambda: NODE in tracking.nodes)

    await until(lambda: NODE not in tracking.nodes)


async def test_last_node_leaving_publishes_no_empty_registration(tracking, fake_session, templates):
    """Capabilities are mandatory, so the last announcement stands until a sensor registers."""
    key = fusion_up_key("registration")
    await join(fake_session, templates, NODE, ("A", "x"))
    await until(lambda: published_on(fake_session, key))
    published = len(published_on(fake_session, key))

    fake_session.undeclare_token(live_key(NODE))
    await until(lambda: NODE not in tracking.nodes)
    await asyncio.sleep(HOLD * 2)

    assert len(published_on(fake_session, key)) == published


async def test_run_on_zenoh_removes_a_departed_node(monkeypatch, fake_session, templates):
    async def fake_open(connect, loop, tls=None):
        return fake_session

    monkeypatch.setattr(ZenohSession, "open", fake_open)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    node = FakeFusionNode(fusion_args())
    task = asyncio.create_task(node.run())
    await until(lambda: fake_session._subscriptions and fake_session._liveliness)

    await join(fake_session, templates, NODE, ("A", "x"))
    assert NODE in node.nodes
    fake_session.undeclare_token(live_key(NODE))
    await until(lambda: NODE not in node.nodes)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def test_run_on_zenoh_registers_and_requests_registrations(monkeypatch, fake_session, templates):
    async def fake_open(connect, loop, tls=None):
        return fake_session

    monkeypatch.setattr(ZenohSession, "open", fake_open)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    monkeypatch.setattr(fake_fusion_node, "REGISTRATION_DEBOUNCE_SECONDS", 0)
    fake_session.declare_token(live_key(NODE))
    task = asyncio.create_task(FakeFusionNode(fusion_args()).run())

    await until(lambda: published_on(fake_session, down_key(NODE, "task")))
    assert not published_on(fake_session, up_key(FUSION, "status_report"))
    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: published_on(fake_session, up_key(FUSION, "status_report")))
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(published_on(fake_session, up_key(FUSION, "registration"))) == 1
    assert len(published_on(fake_session, fusion_up_key("registration"))) == 1


async def test_receive_raw_still_raises_decode_error_and_keeps_the_sample(fake_session):
    link = await ZenohFusionLink.connect(fake_session, FUSION, logging.getLogger("test"))
    key = up_key(NODE, "registration")

    fake_session.inject(key, UNDECODABLE)

    with pytest.raises(DecodeError):
        await asyncio.wait_for(link.receive_raw(), TIMEOUT)
    assert link.last_sample == (key, UNDECODABLE)


@pytest.mark.parametrize(
    "argv, env, expected",
    [([], None, 120.0), ([], "3", 3.0), (["--node-hold-seconds", "7"], "3", 7.0)],
)
def test_main_reads_the_node_hold(monkeypatch, argv, env, expected):
    captured = []

    class Capture:
        def __init__(self, args):
            captured.append(args)

        async def run(self):
            pass

    monkeypatch.setattr(fake_fusion_node, "FakeFusionNode", Capture)
    monkeypatch.setattr(asyncio, "run", lambda coroutine: coroutine.close())
    monkeypatch.setattr(sys, "argv", ["prog", *argv])
    if env is None:
        monkeypatch.delenv("NODE_HOLD_SECONDS", raising=False)
    else:
        monkeypatch.setenv("NODE_HOLD_SECONDS", env)

    fake_fusion_node.main()

    assert captured[0].node_hold_seconds == expected


@pytest.mark.parametrize(
    "argv, env, expected",
    [([], None, 10.0), ([], "3", 3.0), (["--status-interval", "7"], "3", 7.0)],
)
def test_main_reads_the_status_interval(monkeypatch, argv, env, expected):
    captured = []

    class Capture:
        def __init__(self, args):
            captured.append(args)

        async def run(self):
            pass

    monkeypatch.setattr(fake_fusion_node, "FakeFusionNode", Capture)
    monkeypatch.setattr(asyncio, "run", lambda coroutine: coroutine.close())  # a real run leaks a loop under pytest-asyncio
    monkeypatch.setattr(sys, "argv", ["prog", *argv])
    if env is None:
        monkeypatch.delenv("STATUS_INTERVAL", raising=False)
    else:
        monkeypatch.setenv("STATUS_INTERVAL", env)

    fake_fusion_node.main()

    assert captured[0].status_interval == expected


# ---- the host fusion node, on the fabric -----------------------------------------------------

POD_ANCHOR = "18214b1a34e3c722d1cac283b272a62c"
HOST_ANCHOR = "b005ae3a8f2baf89160bd71632902672"
HOST_FUSION = "b0000001-0000-4000-8000-000000000001"


def host_args(**overrides):
    return fusion_args(
        node_id=HOST_FUSION, transport="fabric", fabric_anchor=HOST_ANCHOR, fabric_site="h1", **overrides
    )


@pytest.fixture
async def host(fake_session):
    """The host fusion node with its receive loop running on the fabric."""
    from fabric_link import FabricFusionLink

    node = FakeFusionNode(host_args())
    node.link = await FabricFusionLink.connect(
        fake_session, HOST_FUSION, HOST_ANCHOR, "h1", logging.getLogger("test")
    )
    task = asyncio.create_task(node._receive_loop())
    yield node
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def pod_key(kind, node_id=FUSION):
    from fabric_keys import key_for

    return key_for(POD_ANCHOR, "p1", kind, node_id)


def detections_20_ms_apart(templates, node_id):
    first, second = detection(templates, node_id), detection(templates, node_id)
    second.timestamp.FromNanoseconds(first.timestamp.ToNanoseconds() + 20_000_000)
    return first, second


async def test_on_the_fabric_a_fusion_node_that_registers_is_a_child(host, fake_session, templates):
    ack_key = f"{HOST_ANCHOR}/ack/p1/sapient/v2/registration_ack/{FUSION}"

    fake_session.inject(pod_key("registration"), fusion_typed_registration(templates, FUSION).SerializeToString())
    await until(lambda: published_on(fake_session, ack_key))

    [ack] = published_on(fake_session, ack_key)
    assert ack.registration_ack.acceptance
    assert FUSION in host.nodes


async def test_inside_a_pod_another_fusion_node_is_still_ignored(receiving, fake_session, templates):
    fake_session.inject(up_key(PEER_FUSION, "registration"), fusion_typed_registration(templates).SerializeToString())
    fake_session.inject(up_key(NODE, "registration"), registration(templates).SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "registration_ack")))

    assert not published_on(fake_session, down_key(PEER_FUSION, "registration_ack"))
    assert PEER_FUSION not in receiving.nodes


async def test_the_host_accepts_two_tracks_20_ms_apart(host, fake_session, templates):
    for msg in detections_20_ms_apart(templates, FUSION):
        fake_session.inject(pod_key("detection_report"), msg.SerializeToString())
    await until(lambda: host.detection_counts.get(FUSION) == 2)

    assert not [key for key, _, _ in fake_session.published if "/error/" in key]


async def test_inside_a_pod_two_detections_20_ms_apart_still_give_an_error(receiving, fake_session, templates):
    for msg in detections_20_ms_apart(templates, NODE):
        fake_session.inject(up_key(NODE, "detection_report"), msg.SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "error")))

    [reply] = published_on(fake_session, down_key(NODE, "error"))
    assert "too small" in reply.error.error_message[0]
    assert receiving.detection_counts[NODE] == 1


async def test_a_restarted_host_asks_a_live_pod_to_register(monkeypatch, fake_session):
    from fabric_keys import live_key as fabric_live_key

    opened = []

    async def fake_open(connect, loop, tls=None):
        opened.append(connect)
        return fake_session

    monkeypatch.setattr(ZenohSession, "open", fake_open)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    monkeypatch.setattr(fake_fusion_node, "REQUEST_GRACE_SECONDS", 0)
    fake_session.declare_token(fabric_live_key(POD_ANCHOR, "p1", FUSION))
    task = asyncio.create_task(FakeFusionNode(host_args()).run())
    task_key = f"{HOST_ANCHOR}/task/p1/sapient/v2/task/{FUSION}"

    await until(lambda: published_on(fake_session, task_key))
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert opened == ["tcp/zenohd:7447"]
    assert all(t.task.command.request == "Registration" for t in published_on(fake_session, task_key))


@pytest.mark.parametrize(
    "argv, env, expected",
    [([], {}, (None, "h1")), ([], {"FABRIC_ANCHOR": HOST_ANCHOR, "FABRIC_SITE": "h2"}, (HOST_ANCHOR, "h2")),
     (["--fabric-anchor", POD_ANCHOR, "--fabric-site", "h3"], {"FABRIC_ANCHOR": HOST_ANCHOR}, (POD_ANCHOR, "h3"))],
)
def test_main_reads_the_fabric_anchor_and_site(monkeypatch, argv, env, expected):
    captured = []

    class Capture:
        def __init__(self, args):
            captured.append(args)

        async def run(self):
            pass

    monkeypatch.setattr(fake_fusion_node, "FakeFusionNode", Capture)
    monkeypatch.setattr(asyncio, "run", lambda coroutine: coroutine.close())
    monkeypatch.setattr(sys, "argv", ["prog", *argv])
    monkeypatch.delenv("FABRIC_ANCHOR", raising=False)
    monkeypatch.delenv("FABRIC_SITE", raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    fake_fusion_node.main()

    assert (captured[0].fabric_anchor, captured[0].fabric_site) == expected


def test_main_refuses_the_fabric_without_an_anchor(monkeypatch):
    monkeypatch.setattr(asyncio, "run", lambda coroutine: coroutine.close())
    monkeypatch.setattr(sys, "argv", ["prog", "--transport", "fabric"])
    monkeypatch.delenv("FABRIC_ANCHOR", raising=False)

    with pytest.raises(SystemExit):
        fake_fusion_node.main()


# ---- the pod fusion node as a child: traffic upward and tasks from above ---------------------

PARENT = "f0000002-0000-4000-8000-000000000002"
RADAR, VEHICLE = NODE, OTHER


@pytest.fixture
async def parented(receiving, caplog):
    """The pod fusion node also acting on what comes from above, logging at INFO."""
    caplog.set_level(logging.INFO, logger=receiving.log.name)
    task = asyncio.create_task(receiving._parent_loop())
    yield receiving
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def registered_upward(node, templates, *members):
    """Register (node_id, node_type) sensors with node and publish its own Registration."""
    for node_id, node_type in members or [(RADAR, "RADAR")]:
        msg = registration(templates, node_id)
        msg.registration.node_definition[0].node_type = Registration.NodeType.Value(f"NODE_TYPE_{node_type}")
        await node._on_registration(msg)
    await node._publish_registration()


def from_parent(templates, template, destination=FUSION):
    msg = stamp(templates("fusion_node", template), PARENT, destination)
    if msg.WhichOneof("content") == "task":
        msg.task.task_id = new_ulid()
    return msg


def send_down(session, msg):
    session.inject(fusion_down_key(msg.WhichOneof("content")), msg.SerializeToString())


async def ack_from_above(session):
    await until(lambda: published_on(session, fusion_up_key("task_ack")))
    [ack] = published_on(session, fusion_up_key("task_ack"))
    return ack


async def test_own_status_also_goes_upward(fusion, fake_session):
    task = asyncio.create_task(fusion._own_status_loop())
    await until(lambda: len(published_on(fake_session, fusion_up_key("status_report"))) >= 2)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    inside = published_on(fake_session, up_key(FUSION, "status_report"))
    upward = published_on(fake_session, fusion_up_key("status_report"))
    assert upward == inside[: len(upward)]


async def test_a_new_track_raises_one_alert_upward(receiving, fake_session, templates):
    await registered_upward(receiving, templates)
    first, second = detection(templates), detection(templates)
    first.timestamp.FromNanoseconds(second.timestamp.ToNanoseconds() - 500_000_000)  # past the minimum gap

    fake_session.inject(up_key(NODE, "detection_report"), first.SerializeToString())
    await until(lambda: published_on(fake_session, fusion_up_key("alert")))
    fake_session.inject(up_key(NODE, "detection_report"), second.SerializeToString())
    await until(lambda: receiving.detection_counts.get(NODE) == 2)

    [alert] = published_on(fake_session, fusion_up_key("alert"))
    [track] = receiving.tracks
    template = templates("sensor", "Alert").alert
    assert alert.node_id == FUSION
    assert not alert.HasField("destination_id")
    assert track.track_id[-6:] in alert.alert.description
    assert alert.alert.alert_id != template.alert_id
    assert alert.alert.location == first.detection_report.location
    [associated] = alert.alert.associated_detection
    assert associated.node_id == FUSION
    assert associated.object_id == track.track_id
    assert associated.timestamp == alert.timestamp
    assert associated.association_type == template.associated_detection[0].association_type
    kept = {field.name for field, _ in alert.alert.ListFields()}
    assert not kept & {"region_id", "associated_file", "additional_information", "ranking", "confidence"}
    assert (alert.alert.alert_type, alert.alert.status, alert.alert.priority) == (
        template.alert_type, template.status, template.priority
    )
    assert receiving.validate(alert) is None
    assert not published_on(fake_session, up_key(FUSION, "alert"))


async def test_a_track_made_before_registration_gets_its_alert_with_its_next_detection(
    receiving, fake_session, templates
):
    first, second, third = detection(templates), detection(templates), detection(templates)
    first.timestamp.FromNanoseconds(third.timestamp.ToNanoseconds() - 600_000_000)
    second.timestamp.FromNanoseconds(third.timestamp.ToNanoseconds() - 300_000_000)
    second.detection_report.location.z += 1  # a later position, within the gate

    fake_session.inject(up_key(NODE, "detection_report"), first.SerializeToString())
    await until(lambda: receiving.detection_counts.get(NODE) == 1)
    await registered_upward(receiving, templates)
    assert not published_on(fake_session, fusion_up_key("alert"))
    fake_session.inject(up_key(NODE, "detection_report"), second.SerializeToString())
    await until(lambda: published_on(fake_session, fusion_up_key("alert")))
    fake_session.inject(up_key(NODE, "detection_report"), third.SerializeToString())
    await until(lambda: receiving.detection_counts.get(NODE) == 3)

    [alert] = published_on(fake_session, fusion_up_key("alert"))
    [track] = receiving.tracks
    assert alert.alert.associated_detection[0].object_id == track.track_id
    assert alert.alert.location == second.detection_report.location


async def test_a_sensor_alert_goes_upward_with_the_fusion_node_as_sender(receiving, fake_session, templates):
    await registered_upward(receiving, templates)
    alert = stamp(templates("sensor", "Alert"), NODE, FUSION)
    alert.alert.alert_id = new_ulid()

    fake_session.inject(up_key(NODE, "alert"), alert.SerializeToString())
    await until(lambda: published_on(fake_session, fusion_up_key("alert")))
    await until(lambda: published_on(fake_session, down_key(NODE, "alert_ack")))

    [upward] = published_on(fake_session, fusion_up_key("alert"))
    assert upward.alert.alert_id == alert.alert.alert_id
    assert upward.node_id == FUSION
    assert not upward.HasField("destination_id")
    [ack] = published_on(fake_session, down_key(NODE, "alert_ack"))
    assert ack.alert_ack.alert_id == alert.alert.alert_id


async def test_a_sensor_alert_before_registration_is_held_back_and_logged(
    receiving, fake_session, templates, caplog
):
    caplog.set_level(logging.INFO, logger=receiving.log.name)
    alert = stamp(templates("sensor", "Alert"), NODE, FUSION)
    alert.alert.alert_id = new_ulid()

    fake_session.inject(up_key(NODE, "alert"), alert.SerializeToString())
    await until(lambda: published_on(fake_session, down_key(NODE, "alert_ack")))

    assert not published_on(fake_session, fusion_up_key("alert"))
    assert f"alert from {NODE[:8]} not sent upward: this node has not registered yet" in caplog.text


async def test_registration_request_from_above(parented, fake_session, templates):
    await registered_upward(parented, templates)
    request = from_parent(templates, "Task.Request.Registration")

    send_down(fake_session, request)
    ack = await ack_from_above(fake_session)

    assert len(published_on(fake_session, fusion_up_key("registration"))) == 2
    assert len(published_on(fake_session, up_key(FUSION, "registration"))) == 2
    assert ack.task_ack.task_id == request.task.task_id
    assert ack.task_ack.task_status == TaskAck.TASK_STATUS_ACCEPTED
    assert ack.node_id == FUSION
    assert ack.destination_id == PARENT
    assert len(ack.task_ack.reason) == 1


async def test_status_request_from_above(parented, fake_session, templates):
    await registered_upward(parented, templates)
    request = from_parent(templates, "Task.Request.Status")

    send_down(fake_session, request)
    ack = await ack_from_above(fake_session)

    [status] = published_on(fake_session, fusion_up_key("status_report"))
    assert status.node_id == FUSION
    assert status.status_report.info == StatusReport.INFO_NEW
    assert parented.validate(status) is None
    assert ack.task_ack.task_id == request.task.task_id
    assert ack.task_ack.task_status == TaskAck.TASK_STATUS_ACCEPTED
    assert ack.destination_id == PARENT


def without_header_and_task_id(msg):
    copy = SapientMessage()
    copy.CopyFrom(msg)
    for field in ("node_id", "destination_id", "timestamp"):
        copy.ClearField(field)
    copy.task.ClearField("task_id")
    return copy


async def test_a_command_from_above_goes_to_each_sensor_it_is_meant_for(parented, fake_session, templates):
    await registered_upward(parented, templates, (RADAR, "RADAR"), (VEHICLE, "MOBILE_NODE"))
    command = from_parent(templates, "Task.LookAt")

    send_down(fake_session, command)
    ack = await ack_from_above(fake_session)

    [sent] = published_on(fake_session, down_key(RADAR, "task"))
    assert sent.task.task_id != command.task.task_id
    assert without_header_and_task_id(sent) == without_header_and_task_id(command)
    assert sent.node_id == FUSION
    assert sent.destination_id == RADAR
    assert not published_on(fake_session, down_key(VEHICLE, "task"))
    assert ack.task_ack.task_id == command.task.task_id
    assert ack.task_ack.task_status == TaskAck.TASK_STATUS_ACCEPTED
    assert ack.destination_id == PARENT
    [reason] = ack.task_ack.reason
    assert "1 node" in reason


async def test_a_command_no_sensor_takes_is_rejected_with_a_reason(parented, fake_session, templates):
    await registered_upward(parented, templates, (RADAR, "RADAR"))
    command = from_parent(templates, "Task.MoveTo")

    send_down(fake_session, command)
    ack = await ack_from_above(fake_session)

    assert not published_on(fake_session, down_key(RADAR, "task"))
    assert ack.task_ack.task_id == command.task.task_id
    assert ack.task_ack.task_status == TaskAck.TASK_STATUS_REJECTED
    assert ack.destination_id == PARENT
    assert len(ack.task_ack.reason) == 1


async def test_a_task_for_another_node_is_ignored_and_logged(parented, fake_session, templates, caplog):
    await registered_upward(parented, templates)
    send_down(fake_session, from_parent(templates, "Task.Request.Status", destination=OTHER))
    send_down(fake_session, from_parent(templates, "RegistrationAck"))  # marks the end of the first

    await until(lambda: "<- registration_ack" in caplog.text)

    assert "<- task" in caplog.text
    assert re.search("task for .*ignored", caplog.text)
    assert not published_on(fake_session, fusion_up_key("task_ack"))
    assert not published_on(fake_session, fusion_up_key("status_report"))


async def test_a_task_with_no_destination_is_ignored_and_logged(parented, fake_session, templates, caplog):
    await registered_upward(parented, templates)
    command = from_parent(templates, "Task.Request.Start")
    command.ClearField("destination_id")
    send_down(fake_session, command)
    send_down(fake_session, from_parent(templates, "RegistrationAck"))  # marks the end of the first

    await until(lambda: "<- registration_ack" in caplog.text)

    assert len(re.findall("task for no node ignored", caplog.text)) == 1
    assert not published_on(fake_session, fusion_up_key("task_ack"))
    assert not published_on(fake_session, down_key(RADAR, "task"))


async def test_a_task_from_above_skips_a_node_known_only_from_its_status(parented, fake_session, templates):
    await registered_upward(parented, templates, (RADAR, "RADAR"))
    parented._on_status(status_report(templates, StatusReport.INFO_NEW, OTHER))
    command = from_parent(templates, "Task.Request.Start")

    send_down(fake_session, command)
    ack = await ack_from_above(fake_session)

    assert len(published_on(fake_session, down_key(RADAR, "task"))) == 1
    assert not published_on(fake_session, down_key(OTHER, "task"))
    assert "1 node" in ack.task_ack.reason[0]


async def test_a_malformed_message_from_above_is_dropped_and_the_loop_goes_on(
    parented, fake_session, templates, caplog
):
    await registered_upward(parented, templates)
    malformed = from_parent(templates, "Task.Request.Status")
    malformed.task.ClearField("task_id")
    send_down(fake_session, malformed)
    request = from_parent(templates, "Task.Request.Status")
    send_down(fake_session, request)

    ack = await ack_from_above(fake_session)

    assert ack.task_ack.task_id == request.task.task_id
    assert "invalid message from above dropped" in caplog.text


@pytest.mark.parametrize("kind", ["task", "task_ack", "detection_report"])
def test_the_validator_rejects_each_message_summary_would_fail_on(fusion, templates, kind):
    if kind == "task":
        msg = from_parent(templates, "Task.Request.Status")
        msg.task.ClearField("task_id")
    elif kind == "task_ack":
        msg = stamp(templates("sensor", "TaskAck.Request.Status"), PARENT, FUSION)
        msg.task_ack.ClearField("task_id")
    else:
        msg = stamp(templates("fusion_node", "DetectionReport"), PARENT)
        msg.detection_report.ClearField("object_id")
    assert "(no summary: KeyError" in summary(msg)

    assert fusion.validate(msg)


def nan_detection(templates, node_id):
    msg = detection(templates, node_id)
    msg.detection_report.location.x = float("nan")
    return msg


async def test_a_nan_detection_from_above_does_not_end_the_loop(parented, fake_session, templates):
    await registered_upward(parented, templates)
    send_down(fake_session, nan_detection(templates, PARENT))
    request = from_parent(templates, "Task.Request.Status")
    send_down(fake_session, request)

    ack = await ack_from_above(fake_session)

    assert ack.task_ack.task_id == request.task.task_id


async def test_a_nan_detection_from_a_sensor_does_not_end_the_receive_loop(receiving, fake_session, templates):
    fake_session.inject(up_key(NODE, "detection_report"), nan_detection(templates, NODE).SerializeToString())
    fake_session.inject(up_key(OTHER, "registration"), registration(templates, OTHER).SerializeToString())

    await until(lambda: published_on(fake_session, down_key(OTHER, "registration_ack")))


async def test_a_message_from_above_has_a_validator_of_its_own(parented, fake_session, templates):
    await registered_upward(parented, templates)
    assert parented.validate(status_report(templates, StatusReport.INFO_NEW, OTHER)) is None
    before = {node_id: id(validator) for node_id, validator in parented.validators.items()}
    request = from_parent(templates, "Task.Request.Status")
    request.node_id = RADAR  # a message from above that carries the radar's node ID

    send_down(fake_session, request)
    await ack_from_above(fake_session)

    assert {node_id: id(validator) for node_id, validator in parented.validators.items()} == before


async def test_bad_bytes_from_above_do_not_end_the_loop(parented, fake_session, templates, caplog):
    await registered_upward(parented, templates)
    fake_session.inject(fusion_down_key("task"), UNDECODABLE)
    send_down(fake_session, from_parent(templates, "Task.Request.Status"))

    ack = await ack_from_above(fake_session)

    assert "undecodable message from above" in caplog.text
    assert ack.task_ack.task_status == TaskAck.TASK_STATUS_ACCEPTED


async def test_registration_ack_from_above_is_logged(parented, fake_session, templates, caplog):
    send_down(fake_session, from_parent(templates, "RegistrationAck"))

    await until(lambda: "<- registration_ack" in caplog.text)

    assert not published_on(fake_session, fusion_up_key("task_ack"))


async def test_the_fabric_transport_has_no_parent_loop(monkeypatch, templates):
    from fabric_link import FabricFusionLink

    sessions = [FakeZenohSession(), FakeZenohSession()]
    started = []

    async def fake_open(connect, loop, tls=None):
        return sessions.pop(0)

    async def parent_loop(self):
        started.append(self.args.transport)

    monkeypatch.setattr(ZenohSession, "open", fake_open)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    monkeypatch.setattr(FakeFusionNode, "_parent_loop", parent_loop)
    nodes = [FakeFusionNode(host_args()), FakeFusionNode(fusion_args())]
    tasks = [asyncio.create_task(node.run()) for node in nodes]
    await until(lambda: all(node.link is not None for node in nodes))
    await until(lambda: started)
    for _ in range(20):
        await asyncio.sleep(0)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    assert FabricFusionLink.has_parent is False
    assert started == ["zenoh"]
