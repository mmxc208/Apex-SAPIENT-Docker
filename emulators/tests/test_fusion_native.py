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
from sapient_link import ZenohFusionLink, load_template, new_ulid, stamp
from sapient_msg.bsi_flex_335_v2_0.registration_pb2 import Registration
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from sapient_msg.bsi_flex_335_v2_0.status_report_pb2 import StatusReport
from zenoh_io import ZenohSession
from zenoh_keys import UP_ALL, down_key, fusion_up_key, live_key, qos_for, up_key

NODE = "a0000001-0000-4000-8000-000000000001"
OTHER = "a0000002-0000-4000-8000-000000000002"
FUSION = "f0000001-0000-4000-8000-000000000001"
PEER_FUSION = "f0000002-0000-4000-8000-000000000002"
TIMEOUT = 5
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
