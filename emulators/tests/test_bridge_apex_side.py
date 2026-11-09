import asyncio
import logging
import struct
import uuid
from contextlib import asynccontextmanager

import pytest

import bridge_apex_side
from bridge_apex_side import ApexSideBridge
from conftest import FakeZenohSession
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import ZenohSession
from zenoh_keys import down_key, live_key, qos_for, up_key

NODE = "a0000001-0000-4000-8000-000000000001"
OTHER_NODE = "a0000002-0000-4000-8000-000000000002"
BRIDGE = "b0000000-0000-4000-8000-00000000000b"
MAX_BYTES = 1024 * 1024
HOLD = 0.2
TIMEOUT = 5
log = logging.getLogger("test-bridge")


class ApexConnection:
    """One accepted socket: records every frame, and can reply or hang up."""

    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self.writer = writer
        self.frames: list[SapientMessage] = []
        self.open = True

    def reply(self, msg: SapientMessage) -> None:
        body = msg.SerializeToString()
        self.writer.write(struct.pack("<I", len(body)) + body)

    def kinds(self) -> list[str]:
        return [frame.WhichOneof("content") for frame in self.frames]


class FakeApex:
    """Apex's Child port on an ephemeral TCP port."""

    def __init__(self) -> None:
        self.connections: list[ApexConnection] = []  # every socket ever accepted, in order
        self.server: asyncio.Server | None = None

    @property
    def open_count(self) -> int:
        return sum(connection.open for connection in self.connections)

    @property
    def port(self) -> int:
        return self.server.sockets[0].getsockname()[1]

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        connection = ApexConnection(writer)
        self.connections.append(connection)
        try:
            while True:
                (length,) = struct.unpack("<I", await reader.readexactly(4))
                connection.frames.append(SapientMessage.FromString(await reader.readexactly(length)))
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            connection.open = False
            writer.close()

    async def __aenter__(self) -> "FakeApex":
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc_info) -> None:
        for connection in self.connections:
            connection.writer.close()
        self.server.close()
        await self.server.wait_closed()


@pytest.fixture
def fake_session():
    return FakeZenohSession()


async def until(condition):
    async def poll():
        while not condition():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(poll(), TIMEOUT)


@asynccontextmanager
async def bridged(session, hold_seconds=HOLD):
    """A fake Apex and a running bridge wired to it; yields (bridge, apex)."""
    async with FakeApex() as apex:
        bridge = ApexSideBridge(session, "127.0.0.1", apex.port, hold_seconds, log=log, bridge_node_id=BRIDGE)
        runner = asyncio.create_task(bridge.run())
        try:
            await until(lambda: session._subscriptions and session._liveliness)
            yield bridge, apex
        finally:
            runner.cancel()
            await asyncio.gather(runner, return_exceptions=True)


def registration(templates, node_id=NODE):
    msg = templates("sensor", "Registration")
    msg.node_id = node_id
    return msg


def status_report(templates, node_id=NODE):
    msg = templates("sensor", "StatusReport")
    msg.node_id = node_id
    return msg


def registration_of_size(templates, size):
    """A valid registration whose serialized form is exactly size bytes."""
    msg = registration(templates)
    msg.registration.name = ""
    while (missing := size - msg.ByteSize()) != 0:
        msg.registration.name = "x" * (len(msg.registration.name) + missing)
    return msg


def inject_up(session, msg, node_id=NODE):
    session.inject(up_key(node_id, msg.WhichOneof("content")), msg.SerializeToString())


async def register(session, templates, apex):
    """Register NODE and wait until Apex has seen it; returns its socket."""
    inject_up(session, registration(templates))
    await until(lambda: apex.connections and apex.connections[0].frames)
    return apex.connections[0]


async def test_registration_opens_one_apex_socket_and_forwards(fake_session, templates):
    async with bridged(fake_session) as (bridge, apex):
        connection = await register(fake_session, templates, apex)

        assert len(apex.connections) == 1
        assert connection.kinds() == ["registration"]
        assert connection.frames[0].node_id == NODE
        assert set(bridge.links) == {NODE}


async def test_each_node_gets_its_own_socket(fake_session, templates):
    async with bridged(fake_session) as (bridge, apex):
        inject_up(fake_session, registration(templates))
        inject_up(fake_session, registration(templates, OTHER_NODE), OTHER_NODE)
        await until(lambda: len(apex.connections) == 2 and all(c.frames for c in apex.connections))

        assert sorted(c.frames[0].node_id for c in apex.connections) == sorted([NODE, OTHER_NODE])
        assert set(bridge.links) == {NODE, OTHER_NODE}


async def test_later_samples_use_the_same_socket_in_order(fake_session, templates):
    async with bridged(fake_session) as (bridge, apex):
        connection = await register(fake_session, templates, apex)
        link = bridge.links[NODE]

        inject_up(fake_session, status_report(templates))
        inject_up(fake_session, templates("sensor", "Alert"))
        await until(lambda: len(connection.frames) == 3)

        assert connection.kinds() == ["registration", "status_report", "alert"]
        assert len(apex.connections) == 1
        assert bridge.links[NODE] is link


async def test_reply_from_apex_is_published_on_down_key(fake_session, templates):
    ack = templates("fusion_node", "RegistrationAck")
    async with bridged(fake_session) as (_, apex):
        connection = await register(fake_session, templates, apex)

        connection.reply(ack)
        await until(lambda: fake_session.published)

        assert fake_session.published == [
            (down_key(NODE, "registration_ack"), ack.SerializeToString(), qos_for("registration_ack"))
        ]


async def test_non_registration_first_sample_is_dropped(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    async with bridged(fake_session) as (bridge, apex):
        inject_up(fake_session, status_report(templates))
        # Samples are handled in order, so once this one has arrived the first has been dealt with.
        inject_up(fake_session, registration(templates, OTHER_NODE), OTHER_NODE)
        await until(lambda: apex.connections and apex.connections[0].frames)

        assert len(apex.connections) == 1
        assert apex.connections[0].frames[0].node_id == OTHER_NODE
        assert set(bridge.links) == {OTHER_NODE}
        assert f"dropping status_report from unregistered {NODE}" in caplog.text


async def test_token_loss_closes_socket_after_hold(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    fake_session.declare_token(live_key(NODE))
    async with bridged(fake_session) as (bridge, apex):
        connection = await register(fake_session, templates, apex)

        fake_session.undeclare_token(live_key(NODE))
        await asyncio.sleep(HOLD / 4)
        assert connection.open  # the hold window is still running
        assert NODE in bridge.links

        await until(lambda: apex.open_count == 0)

        assert bridge.links == {}
        assert len(apex.connections) == 1
        assert f"closing Apex socket for {NODE}" in caplog.text


async def test_token_flap_within_hold_keeps_socket(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    fake_session.declare_token(live_key(NODE))
    async with bridged(fake_session) as (bridge, apex):
        connection = await register(fake_session, templates, apex)
        link = bridge.links[NODE]

        fake_session.undeclare_token(live_key(NODE))
        await asyncio.sleep(HOLD / 4)
        fake_session.declare_token(live_key(NODE))
        await asyncio.sleep(HOLD * 1.5)  # well past when an uncancelled timer would have fired

        assert len(apex.connections) == 1  # never a second socket
        assert connection.open
        assert bridge.links[NODE] is link
        assert "closing Apex socket" not in caplog.text

        inject_up(fake_session, status_report(templates))
        await until(lambda: len(connection.frames) == 2)
        assert connection.kinds() == ["registration", "status_report"]
        assert len(apex.connections) == 1


async def test_token_lost_before_registration_arrives_still_closes_after_hold(fake_session, templates):
    fake_session.declare_token(live_key(NODE))
    async with bridged(fake_session) as (bridge, apex):
        fake_session.undeclare_token(live_key(NODE))
        connection = await register(fake_session, templates, apex)
        assert connection.open

        await until(lambda: apex.open_count == 0)

        assert bridge.links == {}


async def test_oversized_payload_dropped(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    oversized = registration_of_size(templates, MAX_BYTES + 1)
    async with bridged(fake_session) as (bridge, apex):
        connection = await register(fake_session, templates, apex)
        link = bridge.links[NODE]

        fake_session.inject(up_key(NODE, "registration"), oversized.SerializeToString())
        inject_up(fake_session, status_report(templates))  # delivered next if the big one was dropped
        await until(lambda: len(connection.frames) >= 2)

        assert connection.kinds() == ["registration", "status_report"]
        assert connection.open
        assert bridge.links[NODE] is link
        assert f"dropping oversized payload ({MAX_BYTES + 1} bytes) from {NODE}" in caplog.text


async def test_payload_of_exactly_max_bytes_is_forwarded(fake_session, templates):
    largest = registration_of_size(templates, MAX_BYTES)
    async with bridged(fake_session) as (_, apex):
        connection = await register(fake_session, templates, apex)

        fake_session.inject(up_key(NODE, "registration"), largest.SerializeToString())
        await until(lambda: len(connection.frames) == 2)

        assert connection.frames[1] == largest


async def test_apex_closing_deletes_link_and_next_registration_reopens(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    async with bridged(fake_session) as (bridge, apex):
        first = await register(fake_session, templates, apex)

        first.writer.close()
        await until(lambda: not bridge.links)

        inject_up(fake_session, status_report(templates))
        inject_up(fake_session, registration(templates))
        await until(lambda: len(apex.connections) == 2 and apex.connections[1].frames)

        assert apex.connections[1].kinds() == ["registration"]
        assert first.kinds() == ["registration"]
        assert set(bridge.links) == {NODE}
        assert f"dropping status_report from unregistered {NODE}" in caplog.text


async def test_bad_samples_are_dropped_and_the_bridge_keeps_running(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    async with bridged(fake_session) as (_, apex):
        fake_session.inject("sapient/v2/not-a-uuid/up/registration", b"")
        fake_session.inject(up_key(NODE, "registration"), b"\xff\xff\xff")
        fake_session._report_liveliness("sapient/v2/live/not-a-uuid", False)

        connection = await register(fake_session, templates, apex)

        assert connection.kinds() == ["registration"]
        assert "ignoring sample on bad key" in caplog.text
        assert f"dropping undecodable payload from {NODE}" in caplog.text
        assert "ignoring liveliness on bad key" in caplog.text


async def test_undecodable_reply_from_apex_drops_only_that_link(fake_session, templates):
    async with bridged(fake_session) as (bridge, apex):
        connection = await register(fake_session, templates, apex)

        connection.writer.write(struct.pack("<I", 3) + b"\xff\xff\xff")

        await until(lambda: not bridge.links)
        assert fake_session.published == []

        inject_up(fake_session, registration(templates))
        await until(lambda: len(apex.connections) == 2 and apex.connections[1].frames)


async def test_session_closed_returns_and_closes_every_link(fake_session, templates):
    async with FakeApex() as apex:
        bridge = ApexSideBridge(fake_session, "127.0.0.1", apex.port, log=log, bridge_node_id=BRIDGE)
        runner = asyncio.create_task(bridge.run())
        await until(lambda: fake_session._subscriptions and fake_session._liveliness)
        await register(fake_session, templates, apex)

        fake_session.closed.set()

        await asyncio.wait_for(runner, TIMEOUT)
        await until(lambda: apex.open_count == 0)
        assert bridge.links == {}


async def test_publish_failure_surfaces_from_run(templates):
    class Broken(Exception):
        pass

    class BrokenPublishSession(FakeZenohSession):
        async def publish(self, key, msg, fused=False):
            raise Broken

    session = BrokenPublishSession()
    async with FakeApex() as apex:
        bridge = ApexSideBridge(session, "127.0.0.1", apex.port, log=log, bridge_node_id=BRIDGE)
        runner = asyncio.create_task(bridge.run())
        await until(lambda: session._subscriptions and session._liveliness)
        connection = await register(session, templates, apex)

        connection.reply(templates("fusion_node", "RegistrationAck"))

        with pytest.raises(Broken):
            await asyncio.wait_for(runner, TIMEOUT)
        await until(lambda: apex.open_count == 0)
        assert bridge.links == {}


async def test_run_reopens_the_session_after_it_is_lost(monkeypatch, templates):
    sessions = [FakeZenohSession(), FakeZenohSession()]
    remaining = iter(sessions)

    async def fake_open(connect, loop):
        assert connect == "tcp/router:7447"
        return next(remaining)

    monkeypatch.setattr(ZenohSession, "open", fake_open)
    async with FakeApex() as apex:
        runner = asyncio.create_task(
            bridge_apex_side.run("127.0.0.1", apex.port, "tcp/router:7447", HOLD, log, BRIDGE)
        )
        try:
            await until(lambda: sessions[0]._subscriptions and sessions[0]._liveliness)
            first = await register(sessions[0], templates, apex)

            sessions[0].closed.set()
            await until(lambda: not first.open)

            await until(lambda: sessions[1]._subscriptions and sessions[1]._liveliness)
            inject_up(sessions[1], registration(templates))
            await until(lambda: len(apex.connections) == 2 and apex.connections[1].frames)
        finally:
            runner.cancel()
            await asyncio.gather(runner, return_exceptions=True)


async def test_run_raises_when_the_bridge_fails(monkeypatch, templates):
    class Broken(Exception):
        pass

    class BrokenLivelinessSession(FakeZenohSession):
        def liveliness(self, keyexpr):
            queue = asyncio.Queue()
            queue.get = self._fail
            return queue

        async def _fail(self):
            raise Broken

    session = BrokenLivelinessSession()

    async def fake_open(connect, loop):
        return session

    monkeypatch.setattr(ZenohSession, "open", fake_open)
    with pytest.raises(Broken):
        await asyncio.wait_for(bridge_apex_side.run("127.0.0.1", 1, "tcp/router:7447", HOLD, log, BRIDGE), TIMEOUT)
    assert session.closed.is_set()


def requests_published(session):
    """Every published registration request, as (key, message)."""
    return [(key, SapientMessage.FromString(payload)) for key, payload, _ in session.published]


def assert_is_registration_request(msg, node_id):
    assert msg.WhichOneof("content") == "task"
    assert msg.node_id == BRIDGE
    assert msg.destination_id == node_id
    assert msg.timestamp.seconds > 0
    assert msg.task.task_name == "bridge: request registration"
    assert msg.task.task_id
    assert msg.task.command.WhichOneof("command") == "request"
    assert msg.task.command.request == "Registration"


async def test_startup_requests_registration_once_from_every_alive_node(fake_session):
    fake_session.declare_token(live_key(NODE))
    fake_session.declare_token(live_key(OTHER_NODE))
    async with bridged(fake_session):
        await until(lambda: len(fake_session.published) >= 2)
        await asyncio.sleep(0.05)  # room for a duplicate from the liveliness history

        published = requests_published(fake_session)
        assert sorted(key for key, _ in published) == sorted(
            [down_key(NODE, "task"), down_key(OTHER_NODE, "task")]
        )
        for key, msg in published:
            assert_is_registration_request(msg, NODE if key == down_key(NODE, "task") else OTHER_NODE)
        assert published[0][1].task.task_id != published[1][1].task.task_id


async def test_startup_asks_for_alive_tokens_directly(templates):
    class NoHistorySession(FakeZenohSession):
        def liveliness(self, keyexpr):
            queue = asyncio.Queue()
            self._liveliness.append((keyexpr, queue))
            return queue

    session = NoHistorySession()
    session.declare_token(live_key(NODE))
    async with bridged(session):
        await until(lambda: session.published)
        await asyncio.sleep(0.05)

        assert [key for key, _, _ in session.published] == [down_key(NODE, "task")]


async def test_token_returning_after_link_closed_requests_registration_once(fake_session, templates):
    async with bridged(fake_session) as (bridge, apex):
        await register(fake_session, templates, apex)
        fake_session.declare_token(live_key(NODE))  # link open: no request
        fake_session.undeclare_token(live_key(NODE))
        await until(lambda: not bridge.links)
        assert fake_session.published == []

        fake_session.declare_token(live_key(NODE))
        await until(lambda: fake_session.published)
        await asyncio.sleep(0.05)

        published = requests_published(fake_session)
        assert [key for key, _ in published] == [down_key(NODE, "task")]
        assert_is_registration_request(published[0][1], NODE)


async def test_token_flap_with_link_open_requests_nothing(fake_session, templates):
    async with bridged(fake_session) as (bridge, apex):
        connection = await register(fake_session, templates, apex)
        fake_session.declare_token(live_key(NODE))
        fake_session.undeclare_token(live_key(NODE))
        await asyncio.sleep(HOLD / 4)
        fake_session.declare_token(live_key(NODE))
        await asyncio.sleep(0.05)

        assert fake_session.published == []
        assert connection.open
        assert NODE in bridge.links


def gate_link_connect(monkeypatch):
    """Hold Link.connect until the returned gate is set; returns (started, gate)."""
    started, gate = asyncio.Event(), asyncio.Event()
    real_connect = bridge_apex_side.Link.connect

    async def slow_connect(host, port, connect_log):
        started.set()
        await gate.wait()
        return await real_connect(host, port, connect_log)

    monkeypatch.setattr(bridge_apex_side.Link, "connect", slow_connect)
    return started, gate


async def test_link_connecting_past_its_hold_window_closes_one_hold_after_connect(
    monkeypatch, fake_session, templates
):
    started, gate = gate_link_connect(monkeypatch)
    fake_session.declare_token(live_key(NODE))
    async with bridged(fake_session) as (bridge, apex):
        inject_up(fake_session, registration(templates))
        await asyncio.wait_for(started.wait(), TIMEOUT)
        fake_session.undeclare_token(live_key(NODE))
        await asyncio.sleep(HOLD * 1.5)  # the window from the token loss has now expired
        assert apex.connections == []

        loop = asyncio.get_running_loop()
        connect_completed = loop.time()
        gate.set()
        await until(lambda: apex.connections and apex.connections[0].frames)
        assert apex.connections[0].open

        await until(lambda: apex.open_count == 0)

        assert HOLD / 2 <= loop.time() - connect_completed <= HOLD * 2
        assert bridge.links == {}


async def test_token_back_before_slow_connect_completes_keeps_the_link(monkeypatch, fake_session, templates):
    started, gate = gate_link_connect(monkeypatch)
    fake_session.declare_token(live_key(NODE))
    async with bridged(fake_session) as (bridge, apex):
        inject_up(fake_session, registration(templates))
        await asyncio.wait_for(started.wait(), TIMEOUT)
        fake_session.undeclare_token(live_key(NODE))
        await asyncio.sleep(HOLD * 1.5)
        fake_session.declare_token(live_key(NODE))
        await asyncio.sleep(0.05)

        gate.set()
        await until(lambda: apex.connections and apex.connections[0].frames)
        await asyncio.sleep(HOLD * 1.5)

        assert apex.connections[0].open
        assert NODE in bridge.links


def captured_main_arguments(monkeypatch):
    captured = []

    async def fake_run(*args):
        captured.append(args)

    monkeypatch.setattr(bridge_apex_side, "run", fake_run)
    # Drives the coroutine by hand: a real asyncio.run here leaves pytest-asyncio's loop unclosed.
    monkeypatch.setattr(bridge_apex_side.asyncio, "run", lambda coroutine: coroutine.send(None))
    with pytest.raises(StopIteration):
        bridge_apex_side.main()
    return captured[0]


def test_main_uses_bridge_node_id_from_the_environment(monkeypatch):
    monkeypatch.setenv("BRIDGE_NODE_ID", BRIDGE)
    assert captured_main_arguments(monkeypatch)[-1] == BRIDGE


def test_main_generates_a_uuid4_bridge_node_id_by_default(monkeypatch):
    monkeypatch.delenv("BRIDGE_NODE_ID", raising=False)
    assert uuid.UUID(captured_main_arguments(monkeypatch)[-1]).version == 4
