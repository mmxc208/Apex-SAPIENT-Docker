"""The fusion node's Zenoh-only duties: validation, re-registration requests, its own status."""
import argparse
import asyncio
import io
import logging
import sys

import pytest
from google.protobuf.message import DecodeError

import fake_fusion_node
from conftest import FakeZenohSession
from fake_fusion_node import FakeFusionNode
from sapient_link import ZenohFusionLink, new_ulid, stamp
from sapient_msg.bsi_flex_335_v2_0.registration_pb2 import Registration
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from sapient_msg.bsi_flex_335_v2_0.status_report_pb2 import StatusReport
from zenoh_io import ZenohSession
from zenoh_keys import UP_ALL, down_key, live_key, up_key

NODE = "a0000001-0000-4000-8000-000000000001"
OTHER = "a0000002-0000-4000-8000-000000000002"
FUSION = "f0000001-0000-4000-8000-000000000001"
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


def published_on(session, key) -> list[SapientMessage]:
    return [SapientMessage.FromString(payload) for k, payload, _ in session.published if k == key]


async def until(condition):
    async def poll():
        while not condition():
            await asyncio.sleep(0)

    await asyncio.wait_for(poll(), TIMEOUT)


def registration(templates, node_id=NODE):
    return stamp(templates("sensor", "Registration"), node_id)


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


def test_own_registration_describes_a_fusion_node(fusion):
    msg = fusion._own_registration()

    reg = msg.registration
    assert msg.node_id == FUSION
    assert not msg.HasField("destination_id")
    assert [d.node_type for d in reg.node_definition] == [Registration.NodeType.NODE_TYPE_FUSION_NODE]
    assert (reg.name, reg.short_name) == ("fake fusion node", "fusion")
    assert reg.icd_version == "BSI Flex 335 v2.0"
    assert reg.status_definition.status_interval.value == pytest.approx(0.01)
    assert not reg.capabilities
    assert not reg.dependent_nodes


def test_own_registration_only_lacks_the_capabilities_stage_4_fills(fusion):
    description = fusion.validate(fusion._own_registration())

    assert description.count("Missing") == 1
    assert "registration.capabilities" in description


async def test_run_on_zenoh_registers_and_requests_registrations(monkeypatch, fake_session):
    async def fake_open(connect, loop, tls=None):
        return fake_session

    monkeypatch.setattr(ZenohSession, "open", fake_open)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    fake_session.declare_token(live_key(NODE))
    task = asyncio.create_task(FakeFusionNode(fusion_args()).run())

    await until(
        lambda: published_on(fake_session, up_key(FUSION, "status_report"))
        and published_on(fake_session, down_key(NODE, "task"))
    )
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(published_on(fake_session, up_key(FUSION, "registration"))) == 1


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
