import asyncio
import errno
import logging
import socket
import struct
from contextlib import asynccontextmanager

import pytest

import bridge_node_side
import zenoh_io
from bridge_node_side import NodeSideBridge
from conftest import FakeZenohSession
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_keys import down_key, live_key, up_key

NODE = "a0000001-0000-4000-8000-000000000001"
TIMEOUT = 5
log = logging.getLogger("test-bridge")


@pytest.fixture
def fake_session():
    return FakeZenohSession()


@asynccontextmanager
async def serving(session):
    """A bridge on an ephemeral port; yields (bridge, connect), where connect opens a client."""
    bridge = NodeSideBridge(session, log)
    server = await asyncio.start_server(bridge.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    clients = []

    async def connect():
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        clients.append(writer)
        return reader, writer

    try:
        yield bridge, connect
    finally:
        for writer in clients:
            writer.close()
        await bridge.close_all()
        server.close()
        await server.wait_closed()


def send(writer, msg):
    body = msg.SerializeToString()
    writer.write(struct.pack("<I", len(body)) + body)


async def read_frame(reader) -> bytes:
    async def read() -> bytes:
        (length,) = struct.unpack("<I", await reader.readexactly(4))
        return await reader.readexactly(length)

    return await asyncio.wait_for(read(), TIMEOUT)


async def read_eof(reader) -> bytes:
    return await asyncio.wait_for(reader.read(), TIMEOUT)


async def until(condition):
    async def poll():
        while not condition():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(poll(), TIMEOUT)


def registration(templates, node_id=NODE):
    msg = templates("sensor", "Registration")
    msg.node_id = node_id
    return msg


def status_report(templates):
    msg = templates("sensor", "StatusReport")
    msg.node_id = NODE
    return msg


async def test_registration_is_published_and_token_declared(fake_session, templates):
    async with serving(fake_session) as (bridge, connect):
        _, writer = await connect()
        send(writer, registration(templates))
        await until(lambda: fake_session.published)

        key, payload, _ = fake_session.published[0]
        assert key == up_key(NODE, "registration")
        assert SapientMessage.FromString(payload).WhichOneof("content") == "registration"
        assert live_key(NODE) in fake_session.tokens
        assert NODE in bridge.nodes


async def test_further_messages_are_published_in_order(fake_session, templates):
    async with serving(fake_session) as (_, connect):
        _, writer = await connect()
        send(writer, registration(templates))
        send(writer, status_report(templates))
        send(writer, templates("sensor", "Alert"))
        await until(lambda: len(fake_session.published) == 3)

        assert [key for key, _, _ in fake_session.published] == [
            up_key(NODE, "registration"),
            up_key(NODE, "status_report"),
            up_key(NODE, "alert"),
        ]


async def test_down_messages_are_written_to_socket(fake_session, templates):
    task_bytes = templates("fusion_node", "Task.Request.Status").SerializeToString()
    async with serving(fake_session) as (_, connect):
        reader, writer = await connect()
        send(writer, registration(templates))
        await until(lambda: fake_session.published)

        fake_session.inject(down_key(NODE, "task"), task_bytes)

        body = await read_frame(reader)
        assert body == task_bytes
        assert SapientMessage.FromString(body).WhichOneof("content") == "task"


async def test_first_message_not_registration_is_refused(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    async with serving(fake_session) as (bridge, connect):
        reader, writer = await connect()
        send(writer, status_report(templates))

        assert await read_eof(reader) == b""
        assert fake_session.published == []
        assert fake_session.tokens == set()
        assert bridge.nodes == {}
        assert "first message must be a registration" in caplog.text


async def test_first_frame_not_a_sapient_message_is_refused(fake_session, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    async with serving(fake_session) as (_, connect):
        reader, writer = await connect()
        writer.write(struct.pack("<I", 3) + b"\xff\xff\xff")

        assert await read_eof(reader) == b""
        assert fake_session.published == []
        assert "first message must be a registration" in caplog.text


async def test_invalid_node_id_is_refused(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    async with serving(fake_session) as (bridge, connect):
        reader, writer = await connect()
        send(writer, registration(templates, node_id="not-a-uuid"))

        assert await read_eof(reader) == b""
        assert fake_session.published == []
        assert fake_session.tokens == set()
        assert bridge.nodes == {}
        assert "invalid node_id" in caplog.text


async def test_duplicate_node_id_refused(fake_session, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    async with serving(fake_session) as (bridge, connect):
        first_reader, first = await connect()
        send(first, registration(templates))
        await until(lambda: fake_session.published)
        first_connection = bridge.nodes[NODE]

        reader, second = await connect()
        send(second, registration(templates))

        assert await read_eof(reader) == b""
        assert len(fake_session.tokens) == 1
        assert bridge.nodes[NODE] is first_connection
        assert len(fake_session.published) == 1
        assert "node_id already connected; refusing" in caplog.text

        # The first connection still works in both directions.
        task_bytes = templates("fusion_node", "Task.Request.Status").SerializeToString()
        fake_session.inject(down_key(NODE, "task"), task_bytes)
        assert await read_frame(first_reader) == task_bytes
        send(first, status_report(templates))
        await until(lambda: len(fake_session.published) == 2)
        assert fake_session.published[1][0] == up_key(NODE, "status_report")


async def test_unknown_message_after_registration_drops_the_connection(fake_session, templates):
    async with serving(fake_session) as (bridge, connect):
        reader, writer = await connect()
        send(writer, registration(templates))
        send(writer, SapientMessage())  # no content, so it has no kind and no key

        assert await read_eof(reader) == b""
        await until(lambda: not bridge.nodes)
        assert fake_session.tokens == set()


async def test_disconnect_undeclares_token(fake_session, templates):
    async with serving(fake_session) as (bridge, connect):
        _, writer = await connect()
        send(writer, registration(templates))
        await until(lambda: fake_session.published)
        assert live_key(NODE) in fake_session.tokens

        writer.close()

        await until(lambda: not fake_session.tokens)
        await until(lambda: not bridge.nodes)


async def test_reconnect_reuses_the_subscription_and_drops_stale_messages(fake_session, templates):
    stale = templates("fusion_node", "Task.Request.Status")
    stale.task.task_id = "01STALE0000000000000000000"
    fresh = templates("fusion_node", "Task.Request.Status")
    fresh.task.task_id = "01FRESH0000000000000000000"

    async with serving(fake_session) as (bridge, connect):
        _, writer = await connect()
        send(writer, registration(templates))
        await until(lambda: fake_session.published)
        writer.close()
        await until(lambda: not bridge.nodes)

        fake_session.inject(down_key(NODE, "task"), stale.SerializeToString())

        reader, writer = await connect()
        send(writer, registration(templates))
        await until(lambda: len(fake_session.published) == 2)
        fake_session.inject(down_key(NODE, "task"), fresh.SerializeToString())

        assert await read_frame(reader) == fresh.SerializeToString()
        assert len(fake_session._subscriptions) == 1


async def test_close_all_drops_every_connection(fake_session, templates):
    async with serving(fake_session) as (bridge, connect):
        reader, writer = await connect()
        send(writer, registration(templates))
        await until(lambda: fake_session.published)
        unregistered_reader, _ = await connect()
        await until(lambda: len(bridge._handlers) == 2)

        await bridge.close_all()

        assert await read_eof(reader) == b""
        assert await read_eof(unregistered_reader) == b""
        assert fake_session.tokens == set()
        assert bridge.nodes == {}


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


async def connect_when_listening(port):
    async def attempt():
        while True:
            try:
                return await asyncio.open_connection("127.0.0.1", port)
            except OSError:
                await asyncio.sleep(0.01)

    return await asyncio.wait_for(attempt(), TIMEOUT)


async def test_run_raises_when_the_port_cannot_be_bound(monkeypatch, fake_session):
    async def fake_open(connect, loop):
        return fake_session

    async def never_called(reader, writer):
        raise AssertionError("no client connects in this test")

    monkeypatch.setattr(bridge_node_side.ZenohSession, "open", fake_open)
    blocker = await asyncio.start_server(never_called, "127.0.0.1", 0)
    port = blocker.sockets[0].getsockname()[1]
    try:
        # Checks errno because wait_for's TimeoutError is an OSError too.
        with pytest.raises(OSError) as failure:
            await asyncio.wait_for(bridge_node_side.run(port, "tcp/router:7447", log), TIMEOUT)
    finally:
        blocker.close()
        await blocker.wait_closed()
    assert failure.value.errno == errno.EADDRINUSE
    assert fake_session.closed.is_set()


def open_sessions(monkeypatch, sessions):
    """Make the first ZenohSession.open fail, then hand out sessions; returns the attempts."""
    remaining = iter(sessions)
    attempts = []

    async def fake_open(connect, loop):
        attempts.append(connect)
        if len(attempts) == 1:
            raise bridge_node_side.zenoh.ZError("router unreachable")
        return next(remaining)

    monkeypatch.setattr(bridge_node_side.ZenohSession, "open", fake_open)
    monkeypatch.setattr(zenoh_io, "RECONNECT_SECONDS", 0)
    return attempts


async def test_run_retries_the_router_and_survives_transport_loss(monkeypatch, templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)
    session = FakeZenohSession()
    attempts = open_sessions(monkeypatch, [session])
    port = free_port()
    runner = asyncio.create_task(bridge_node_side.run(port, "tcp/router:7447", log))
    try:
        reader, writer = await connect_when_listening(port)
        send(writer, registration(templates))
        await until(lambda: session.published)
        assert attempts == ["tcp/router:7447", "tcp/router:7447"]

        session.lose_transport()
        await until(lambda: "transport lost" in caplog.text)
        session.restore_transport()
        await until(lambda: "transport back" in caplog.text)

        assert not runner.done()
        assert live_key(NODE) in session.tokens
        assert len(attempts) == 2  # no reconnect of our own: the binding does it

        # The sensor never noticed: its connection works in both directions.
        task_bytes = templates("fusion_node", "Task.Request.Status").SerializeToString()
        session.inject(down_key(NODE, "task"), task_bytes)
        assert await read_frame(reader) == task_bytes
        send(writer, status_report(templates))
        await until(lambda: len(session.published) == 2)
        writer.close()
    finally:
        runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)


async def test_run_ends_and_drops_nodes_when_the_session_is_closed(monkeypatch, templates):
    session = FakeZenohSession()
    open_sessions(monkeypatch, [session])
    port = free_port()
    runner = asyncio.create_task(bridge_node_side.run(port, "tcp/router:7447", log))
    try:
        reader, writer = await connect_when_listening(port)
        send(writer, registration(templates))
        await until(lambda: session.published)

        session.closed.set()

        await asyncio.wait_for(runner, TIMEOUT)
        assert await read_eof(reader) == b""
        assert session.tokens == set()
        writer.close()
    finally:
        runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)


async def test_failed_publish_keeps_the_sensor_connected(templates, caplog):
    caplog.set_level(logging.INFO, logger=log.name)

    class FlakySession(FakeZenohSession):
        failing = False

        async def publish(self, key, msg, fused=False):
            if self.failing:
                self.failing = False
                raise bridge_node_side.zenoh.ZError("no route")
            await super().publish(key, msg, fused)

    session = FlakySession()
    async with serving(session) as (bridge, connect):
        _, writer = await connect()
        send(writer, registration(templates))
        await until(lambda: session.published)

        session.failing = True
        send(writer, status_report(templates))  # lost to the session error
        send(writer, templates("sensor", "Alert"))
        await until(lambda: len(session.published) == 2)

        assert session.published[1][0] == up_key(NODE, "alert")
        assert NODE in bridge.nodes
        assert "no route" in caplog.text
