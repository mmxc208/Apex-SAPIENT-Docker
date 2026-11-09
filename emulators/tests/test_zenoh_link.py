import argparse
import asyncio
import io
import logging
import struct
import sys

import pytest
import zenoh
from google.protobuf.message import DecodeError

import fake_fusion_node
import fake_sensor
import zenoh_io
from conftest import FakeZenohSession
from fake_fusion_node import FakeFusionNode
from fake_sensor import FakeSensor
from sapient_link import ZenohFusionLink, ZenohLink, stamp
from zenoh_io import ZenohSession
from zenoh_keys import down_key, live_key, qos_for, up_key

NODE = "a0000001-0000-4000-8000-000000000001"
OTHER_NODE = "a0000002-0000-4000-8000-000000000002"
FUSION = "f0000000-0000-4000-8000-00000000000f"
TIMEOUT = 3
log = logging.getLogger("test-zenoh-link")


async def test_zenoh_link_send_publishes_on_up_key_and_declares_token(templates):
    session = FakeZenohSession()
    link = await ZenohLink.connect(session, NODE, log)
    assert session.tokens == {live_key(NODE)}

    msg = stamp(templates("sensor", "Registration"), NODE)
    await link.send(msg)

    assert session.published == [
        (up_key(NODE, "registration"), msg.SerializeToString(), qos_for("registration"))
    ]


async def test_zenoh_link_close_undeclares_the_token():
    session = FakeZenohSession()
    link = await ZenohLink.connect(session, NODE, log)
    link.close()
    assert session.tokens == set()


async def test_zenoh_link_receive_gets_down_messages(templates):
    session = FakeZenohSession()
    link = await ZenohLink.connect(session, NODE, log)

    # the Apex-side bridge asks a node to re-register with exactly this message
    msg = stamp(templates("fusion_node", "Task.Request.Registration"), FUSION, NODE)
    session.inject(down_key(NODE, "task"), msg.SerializeToString())

    assert await asyncio.wait_for(link.receive(), TIMEOUT) == msg


async def test_zenoh_link_ignores_down_messages_for_other_nodes(templates):
    session = FakeZenohSession()
    link = await ZenohLink.connect(session, NODE, log)

    other = stamp(templates("fusion_node", "Task.Request.Status"), FUSION, OTHER_NODE)
    session.inject(down_key(OTHER_NODE, "task"), other.SerializeToString())
    mine = stamp(templates("fusion_node", "Task.Request.Status"), FUSION, NODE)
    session.inject(down_key(NODE, "task"), mine.SerializeToString())

    assert await asyncio.wait_for(link.receive(), TIMEOUT) == mine


class AnswersTokenSession(FakeZenohSession):
    """Sends a down message the moment the token appears, as the Apex-side bridge can."""

    def __init__(self, reply: bytes) -> None:
        super().__init__()
        self.reply = reply

    def declare_token(self, key: str) -> None:
        super().declare_token(key)
        self.inject(down_key(NODE, "task"), self.reply)


async def test_zenoh_link_subscribes_before_announcing_itself(templates):
    msg = stamp(templates("fusion_node", "Task.Request.Registration"), FUSION, NODE)
    session = AnswersTokenSession(msg.SerializeToString())
    link = await ZenohLink.connect(session, NODE, log)
    assert await asyncio.wait_for(link.receive(), TIMEOUT) == msg


@pytest.mark.parametrize(
    "link_class, node_id", [(ZenohLink, NODE), (ZenohFusionLink, FUSION)]
)
async def test_receive_raises_connection_error_when_session_closes_while_waiting(
    link_class, node_id
):
    session = FakeZenohSession()
    link = await link_class.connect(session, node_id, log)
    waiting = asyncio.create_task(link.receive())
    await asyncio.sleep(0)
    assert not waiting.done()

    session.close()

    with pytest.raises(ConnectionError):
        await asyncio.wait_for(waiting, TIMEOUT)


@pytest.mark.parametrize(
    "link_class, node_id", [(ZenohLink, NODE), (ZenohFusionLink, FUSION)]
)
async def test_receive_raises_connection_error_on_a_closed_session_with_samples_queued(
    link_class, node_id, templates
):
    session = FakeZenohSession()
    link = await link_class.connect(session, node_id, log)
    payload = templates("sensor", "Registration").SerializeToString()
    session.inject(down_key(NODE, "registration_ack"), payload)
    session.inject(up_key(NODE, "registration"), payload)
    session.close()

    with pytest.raises(ConnectionError):
        await asyncio.wait_for(link.receive(), TIMEOUT)


@pytest.mark.parametrize(
    "link_class, node_id", [(ZenohLink, NODE), (ZenohFusionLink, FUSION)]
)
async def test_receive_keeps_waiting_through_a_router_outage(link_class, node_id, templates):
    session = FakeZenohSession()
    link = await link_class.connect(session, node_id, log)
    waiting = asyncio.create_task(link.receive())
    session.lose_transport()
    await asyncio.sleep(0.05)
    assert not waiting.done()

    session.restore_transport()
    msg = templates("sensor", "Registration")
    session.inject(down_key(NODE, "registration_ack"), msg.SerializeToString())
    session.inject(up_key(NODE, "registration"), msg.SerializeToString())

    assert await asyncio.wait_for(waiting, TIMEOUT) == msg


async def test_fusion_link_routes_by_destination(templates):
    session = FakeZenohSession()
    link = await ZenohFusionLink.connect(session, FUSION, log)

    msg = stamp(templates("fusion_node", "Task.Request.Status"), FUSION, NODE)
    await link.send(msg)

    assert session.published == [(down_key(NODE, "task"), msg.SerializeToString(), qos_for("task"))]


async def test_fusion_link_publishes_tracks_as_fused(templates):
    session = FakeZenohSession()
    link = await ZenohFusionLink.connect(session, FUSION, log)

    msg = stamp(templates("fusion_node", "DetectionReport"), FUSION)
    await link.send(msg)

    assert session.published == [
        (
            up_key(FUSION, "detection_report"),
            msg.SerializeToString(),
            qos_for("detection_report", fused=True),
        )
    ]


async def test_fusion_link_receive_gets_up_messages_from_every_node(templates):
    session = FakeZenohSession()
    link = await ZenohFusionLink.connect(session, FUSION, log)

    first = stamp(templates("sensor", "Registration"), NODE)
    second = stamp(templates("sensor", "StatusReport"), OTHER_NODE)
    session.inject(up_key(NODE, "registration"), first.SerializeToString())
    session.inject(up_key(OTHER_NODE, "status_report"), second.SerializeToString())

    assert await asyncio.wait_for(link.receive(), TIMEOUT) == first
    assert await asyncio.wait_for(link.receive(), TIMEOUT) == second


async def test_fusion_link_receive_raw_returns_the_payload_bytes(templates):
    session = FakeZenohSession()
    link = await ZenohFusionLink.connect(session, FUSION, log)

    msg = stamp(templates("sensor", "Registration"), NODE)
    payload = msg.SerializeToString()
    session.inject(up_key(NODE, "registration"), payload)

    assert await asyncio.wait_for(link.receive_raw(), TIMEOUT) == (payload, msg)


async def test_fusion_link_does_not_receive_its_own_publications(templates):
    # zenoh delivers a session's own puts to its own matching subscribers, and UP_ALL matches
    session = FakeZenohSession()
    link = await ZenohFusionLink.connect(session, FUSION, log)

    await link.send(stamp(templates("fusion_node", "DetectionReport"), FUSION))
    report = stamp(templates("sensor", "StatusReport"), NODE)
    session.inject(up_key(NODE, "status_report"), report.SerializeToString())

    assert await asyncio.wait_for(link.receive(), TIMEOUT) == report


async def test_fusion_link_close_leaves_the_session_open():
    session = FakeZenohSession()
    link = await ZenohFusionLink.connect(session, FUSION, log)
    link.close()
    assert not session.closed.is_set()


@pytest.mark.integration
async def test_zenoh_link_on_real_sessions_closes_safely_after_the_session(templates):
    # run() always calls link.close() in a finally, usually after the session has gone
    loop = asyncio.get_running_loop()
    router = await ZenohSession.open_peer_listen("tcp/127.0.0.1:17460", loop)
    session = await ZenohSession.open("tcp/127.0.0.1:17460", loop)
    link = await ZenohLink.connect(session, NODE, log)
    await asyncio.sleep(0.5)
    msg = stamp(templates("fusion_node", "Task.Request.Registration"), FUSION, NODE)
    await router.publish(down_key(NODE, "task"), msg)
    assert await asyncio.wait_for(link.receive(), TIMEOUT) == msg

    session.close()
    with pytest.raises(ConnectionError):
        await asyncio.wait_for(link.receive(), TIMEOUT)
    link.close()
    router.close()


async def test_receive_leaves_no_pending_tasks(templates):
    session = FakeZenohSession()
    link = await ZenohLink.connect(session, NODE, log)
    msg = stamp(templates("fusion_node", "Task.Request.Status"), FUSION, NODE)
    session.inject(down_key(NODE, "task"), msg.SerializeToString())

    await asyncio.wait_for(link.receive(), TIMEOUT)
    await asyncio.sleep(0)

    assert asyncio.all_tasks() == {asyncio.current_task()}


async def test_cancelling_receive_keeps_later_samples_available(templates):
    session = FakeZenohSession()
    link = await ZenohLink.connect(session, NODE, log)
    waiting = asyncio.create_task(link.receive())
    await asyncio.sleep(0)
    waiting.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiting

    msg = stamp(templates("fusion_node", "Task.Request.Status"), FUSION, NODE)
    session.inject(down_key(NODE, "task"), msg.SerializeToString())

    assert await asyncio.wait_for(link.receive(), TIMEOUT) == msg


def sensor_args(**overrides):
    values = dict(
        node_id=NODE,
        node_type="RADAR",
        name="Fake radar",
        short_name="radar",
        lon=-1.8224,
        lat=51.1739,
        dependent_node=[],
        host="apex",
        port=5020,
        transport="zenoh",
        zenoh_connect="tcp/zenohd:7447",
    )
    return argparse.Namespace(**{**values, **overrides})


def fusion_args(**overrides):
    values = dict(
        node_id=FUSION,
        auto_task="",
        host="apex",
        port=5001,
        transport="zenoh",
        zenoh_connect="tcp/zenohd:7447",
    )
    return argparse.Namespace(**{**values, **overrides})


def patch_open(monkeypatch, *outcomes):
    """Make ZenohSession.open produce outcomes in turn (an exception is raised); returns its calls."""
    remaining = list(outcomes)
    calls = []

    async def fake_open(connect, loop):
        calls.append(connect)
        outcome = remaining.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(ZenohSession, "open", fake_open)
    return calls


async def test_sensor_connect_link_picks_zenoh(monkeypatch):
    session = FakeZenohSession()
    calls = patch_open(monkeypatch, session)
    sensor = FakeSensor(sensor_args())

    link = await sensor._connect_link()

    assert isinstance(link, ZenohLink)
    assert link.session is session
    assert calls == ["tcp/zenohd:7447"]
    assert session.tokens == {live_key(NODE)}


async def test_fusion_connect_link_picks_zenoh(monkeypatch):
    session = FakeZenohSession()
    calls = patch_open(monkeypatch, session)
    fusion = FakeFusionNode(fusion_args())

    link = await fusion._connect_link()

    assert isinstance(link, ZenohFusionLink)
    assert link.session is session
    assert calls == ["tcp/zenohd:7447"]


@pytest.mark.parametrize(
    "module, node_class, make_args, port",
    [
        (fake_sensor, FakeSensor, sensor_args, 5020),
        (fake_fusion_node, FakeFusionNode, fusion_args, 5001),
    ],
)
async def test_connect_link_on_tcp_uses_link(monkeypatch, module, node_class, make_args, port):
    calls = patch_open(monkeypatch)
    connected = []

    async def fake_connect(host, port, log):
        connected.append((host, port))
        return "tcp link"

    monkeypatch.setattr(module.Link, "connect", fake_connect)
    node = node_class(make_args(transport="tcp"))

    assert await node._connect_link() == "tcp link"
    assert connected == [("apex", port)]
    assert calls == []


@pytest.mark.parametrize(
    "node_class, make_args",
    [(FakeSensor, sensor_args), (FakeFusionNode, fusion_args)],
)
async def test_connect_link_opens_a_fresh_session_and_closes_the_previous(
    monkeypatch, node_class, make_args
):
    first, second = FakeZenohSession(), FakeZenohSession()
    patch_open(monkeypatch, first, second)
    node = node_class(make_args())

    await node._connect_link()
    assert not first.closed.is_set()
    link = await node._connect_link()

    assert first.closed.is_set()
    assert not second.closed.is_set()
    assert link.session is second


@pytest.mark.parametrize(
    "node_class, make_args",
    [(FakeSensor, sensor_args), (FakeFusionNode, fusion_args)],
)
async def test_connect_link_retries_until_the_router_is_reachable(
    monkeypatch, node_class, make_args
):
    session = FakeZenohSession()
    calls = patch_open(monkeypatch, zenoh.ZError("unreachable"), session)
    monkeypatch.setattr(zenoh_io, "RECONNECT_SECONDS", 0)
    node = node_class(make_args())

    link = await asyncio.wait_for(node._connect_link(), TIMEOUT)

    assert link.session is session
    assert len(calls) == 2


UNDECODABLE = b"\xff\xff\xff"


async def test_sensor_drops_an_undecodable_message_and_keeps_receiving(
    monkeypatch, templates, caplog
):
    session = FakeZenohSession()
    patch_open(monkeypatch, session)
    sensor = FakeSensor(sensor_args())
    sensor.link = await sensor._connect_link()
    loop_task = asyncio.create_task(sensor._receive_loop())

    with caplog.at_level(logging.INFO):
        session.inject(down_key(NODE, "registration_ack"), UNDECODABLE)
        ack = templates("fusion_node", "RegistrationAck")
        ack.registration_ack.acceptance = True
        session.inject(down_key(NODE, "registration_ack"), stamp(ack, FUSION, NODE).SerializeToString())
        await asyncio.wait_for(sensor.registered.wait(), TIMEOUT)

    loop_task.cancel()
    await asyncio.gather(loop_task, return_exceptions=True)
    assert "undecodable message dropped" in caplog.text


async def test_fusion_drops_an_undecodable_message_and_keeps_receiving(
    monkeypatch, templates, caplog
):
    session = FakeZenohSession()
    patch_open(monkeypatch, session)
    fusion = FakeFusionNode(fusion_args())
    fusion.link = await fusion._connect_link()
    loop_task = asyncio.create_task(fusion._receive_loop())

    async def acknowledged():
        while not session.published:
            await asyncio.sleep(0)

    with caplog.at_level(logging.INFO):
        session.inject(up_key(NODE, "registration"), UNDECODABLE)
        registration = stamp(templates("sensor", "Registration"), NODE)
        session.inject(up_key(NODE, "registration"), registration.SerializeToString())
        await asyncio.wait_for(acknowledged(), TIMEOUT)

    loop_task.cancel()
    await asyncio.gather(loop_task, return_exceptions=True)
    assert session.published[0][0] == down_key(NODE, "registration_ack")
    assert "undecodable message dropped" in caplog.text


@pytest.mark.parametrize(
    "node_class, make_args",
    [(FakeSensor, sensor_args), (FakeFusionNode, fusion_args)],
)
async def test_undecodable_frame_on_tcp_stays_fatal(monkeypatch, caplog, node_class, make_args):
    """On TCP the node exits, and compose restarts it to register again."""

    async def send_bad_frame(reader, writer):
        writer.write(struct.pack("<I", len(UNDECODABLE)) + UNDECODABLE)
        await writer.drain()
        await reader.read()  # stay open until the node hangs up, so only the bad frame can end it
        writer.close()

    monkeypatch.setattr(sys, "stdin", io.StringIO(""))  # the fusion node's console loop
    server = await asyncio.start_server(send_bad_frame, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    node = node_class(make_args(transport="tcp", host="127.0.0.1", port=port))

    with caplog.at_level(logging.INFO):
        with pytest.raises(ExceptionGroup) as failure:
            await asyncio.wait_for(node.run(), TIMEOUT)

    server.close()
    await server.wait_closed()
    assert failure.group_contains(DecodeError)
    assert "undecodable message dropped" not in caplog.text


def run_main(monkeypatch, module, class_name, argv=()):
    """Run module.main() with the node class replaced; returns the parsed args."""
    captured = []

    class Capture:
        def __init__(self, args):
            captured.append(args)

        async def run(self):
            pass

    monkeypatch.setattr(module, class_name, Capture)
    monkeypatch.setattr(sys, "argv", ["prog", *argv])
    module.main()
    return captured[0]


EMULATORS = [(fake_sensor, "FakeSensor"), (fake_fusion_node, "FakeFusionNode")]


@pytest.mark.parametrize("module, class_name", EMULATORS)
def test_main_defaults_to_tcp(monkeypatch, module, class_name):
    monkeypatch.delenv("TRANSPORT", raising=False)
    monkeypatch.delenv("ZENOH_CONNECT", raising=False)

    args = run_main(monkeypatch, module, class_name)

    assert (args.transport, args.zenoh_connect) == ("tcp", "tcp/zenohd:7447")


@pytest.mark.parametrize("module, class_name", EMULATORS)
def test_main_reads_transport_from_the_environment(monkeypatch, module, class_name):
    monkeypatch.setenv("TRANSPORT", "zenoh")
    monkeypatch.setenv("ZENOH_CONNECT", "tcp/router:7447")

    args = run_main(monkeypatch, module, class_name)

    assert (args.transport, args.zenoh_connect) == ("zenoh", "tcp/router:7447")


@pytest.mark.parametrize("module, class_name", EMULATORS)
def test_main_flags_override_the_environment(monkeypatch, module, class_name):
    monkeypatch.setenv("TRANSPORT", "tcp")

    args = run_main(
        monkeypatch, module, class_name, ["--transport", "zenoh", "--zenoh-connect", "tcp/other:7447"]
    )

    assert (args.transport, args.zenoh_connect) == ("zenoh", "tcp/other:7447")


@pytest.mark.parametrize("module, class_name", EMULATORS)
def test_main_rejects_an_unknown_transport_from_the_environment(monkeypatch, module, class_name):
    monkeypatch.setenv("TRANSPORT", "carrier-pigeon")

    with pytest.raises(SystemExit):
        run_main(monkeypatch, module, class_name)
