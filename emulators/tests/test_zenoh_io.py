import asyncio
import logging

import pytest
import zenoh

from conftest import FakeZenohSession
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import ZenohSession
from zenoh_keys import live_key, parse_key, qos_for, up_key

NODE = "a0000001-0000-4000-8000-000000000001"


@pytest.mark.integration
async def test_two_sessions_pub_sub_and_liveliness(templates):
    # a peer-mode listener on loopback plays the router for this test
    a = await ZenohSession.open_peer_listen("tcp/127.0.0.1:17447", asyncio.get_running_loop())
    b = await ZenohSession.open("tcp/127.0.0.1:17447", asyncio.get_running_loop())
    q = a.subscribe("sapient/v2/*/up/**"); live = a.liveliness("sapient/v2/live/*")
    await asyncio.sleep(0.5)
    b.declare_token(live_key(NODE))
    await b.publish(up_key(NODE, "registration"), templates("sensor", "Registration"))
    key, payload = await asyncio.wait_for(q.get(), 3)
    assert parse_key(key) == (NODE, "up", "registration")
    assert SapientMessage.FromString(payload).WhichOneof("content") == "registration"
    assert await asyncio.wait_for(live.get(), 3) == (live_key(NODE), True)
    b.close()
    assert await asyncio.wait_for(live.get(), 15) == (live_key(NODE), False)
    a.close()


@pytest.mark.integration
async def test_publish_applies_qos_and_protobuf_encoding(templates):
    loop = asyncio.get_running_loop()
    a = await ZenohSession.open_peer_listen("tcp/127.0.0.1:17448", loop)
    b = await ZenohSession.open("tcp/127.0.0.1:17448", loop)
    samples: asyncio.Queue = asyncio.Queue()
    subscriber = a._session.declare_subscriber(
        "sapient/v2/*/up/**", lambda s: loop.call_soon_threadsafe(samples.put_nowait, s)
    )
    await asyncio.sleep(0.5)
    await b.publish(up_key(NODE, "registration"), templates("sensor", "Registration"))
    sample = await asyncio.wait_for(samples.get(), 3)
    assert (sample.priority, sample.congestion_control, sample.express) == qos_for("registration")
    assert sample.encoding == zenoh.Encoding.APPLICATION_PROTOBUF
    subscriber.undeclare()
    b.close()
    a.close()


@pytest.mark.integration
async def test_liveliness_history_alive_and_undeclare():
    loop = asyncio.get_running_loop()
    a = await ZenohSession.open_peer_listen("tcp/127.0.0.1:17449", loop)
    b = await ZenohSession.open("tcp/127.0.0.1:17449", loop)
    b.declare_token(live_key(NODE))
    await asyncio.sleep(0.5)
    live = a.liveliness("sapient/v2/live/*")  # declared after the token already exists
    assert await asyncio.wait_for(live.get(), 3) == (live_key(NODE), True)
    assert await a.alive("sapient/v2/live/*") == [live_key(NODE)]
    b.undeclare_token(live_key(NODE))
    assert await asyncio.wait_for(live.get(), 3) == (live_key(NODE), False)
    assert await a.alive("sapient/v2/live/*") == []
    b.close()
    a.close()


@pytest.mark.integration
async def test_closed_is_set_only_by_close():
    loop = asyncio.get_running_loop()
    router = await ZenohSession.open_peer_listen("tcp/127.0.0.1:17450", loop)
    leaving = await ZenohSession.open("tcp/127.0.0.1:17450", loop)
    staying = await ZenohSession.open("tcp/127.0.0.1:17450", loop)
    leaving.close()
    assert leaving.closed.is_set()
    await asyncio.sleep(0.5)
    assert not staying.closed.is_set()  # another client leaving is not this client's transport
    assert staying.transport_changes.empty()
    assert not router.closed.is_set()
    router.close()
    assert await asyncio.wait_for(staying.transport_changes.get(), 15) is False
    assert not staying.closed.is_set()  # losing the router is not a close
    staying.close()
    assert staying.closed.is_set()


async def open_router_when_port_is_free(listen, loop):
    for _ in range(50):
        try:
            return await ZenohSession.open_peer_listen(listen, loop)
        except zenoh.ZError:
            await asyncio.sleep(0.2)
    raise AssertionError(f"could not listen on {listen} again")


@pytest.mark.integration
async def test_router_returning_restores_subscriptions_and_tokens_with_no_redeclare():
    loop = asyncio.get_running_loop()
    listen = "tcp/127.0.0.1:17451"
    router = await ZenohSession.open_peer_listen(listen, loop)
    client = await ZenohSession.open(listen, loop)
    client.declare_token(live_key(NODE))
    samples = client.subscribe("probe/**")
    router.close()
    assert await asyncio.wait_for(client.transport_changes.get(), 15) is False

    router = await open_router_when_port_is_free(listen, loop)
    assert await asyncio.wait_for(client.transport_changes.get(), 15) is True

    async def tokens_replayed():
        while live_key(NODE) not in await router.alive("sapient/v2/live/*"):
            await asyncio.sleep(0.1)

    await asyncio.wait_for(tokens_replayed(), 10)

    async def subscription_replayed():
        while samples.empty():
            router._session.put("probe/x", b"1")
            await asyncio.sleep(0.1)

    await asyncio.wait_for(subscription_replayed(), 10)
    assert await samples.get() == ("probe/x", b"1")
    assert not client.closed.is_set()
    client.close()
    router.close()


async def test_close_never_raises_and_still_marks_the_session_closed(caplog):
    class TimingOut:
        def is_closed(self):
            return False

        def close(self):
            raise zenoh.ZError("close operation timed out!")

    session = ZenohSession(TimingOut(), asyncio.get_running_loop())
    with caplog.at_level(logging.INFO):
        session.close()
    assert session.closed.is_set()
    assert "close operation timed out!" in caplog.text


async def test_fake_session_fans_out(templates):
    fake = FakeZenohSession()
    every_up = fake.subscribe("sapient/v2/*/up/**")
    this_kind = fake.subscribe(up_key(NODE, "registration"))
    elsewhere = fake.subscribe(up_key(NODE, "alert"))
    msg = templates("sensor", "Registration")
    key = up_key(NODE, "registration")
    await fake.publish(key, msg)
    payload = msg.SerializeToString()
    assert every_up.get_nowait() == (key, payload)
    assert this_kind.get_nowait() == (key, payload)
    assert elsewhere.empty()
    assert fake.published == [(key, payload, qos_for("registration"))]


async def test_fake_session_inject_tokens_and_close():
    fake = FakeZenohSession()
    q = fake.subscribe("sapient/v2/*/down/**")
    fake.inject("sapient/v2/x/up/alert", b"no")
    fake.inject("sapient/v2/x/down/task", b"yes")
    assert q.get_nowait() == ("sapient/v2/x/down/task", b"yes")
    assert q.empty()
    assert fake.published == []

    key = live_key(NODE)
    early = fake.liveliness("sapient/v2/live/*")
    fake.declare_token(key)
    late = fake.liveliness("sapient/v2/live/*")  # already-present tokens are reported
    assert fake.tokens == {key}
    assert early.get_nowait() == (key, True)
    assert late.get_nowait() == (key, True)
    assert await fake.alive("sapient/v2/live/*") == [key]

    fake.undeclare_token(key)
    assert early.get_nowait() == (key, False)
    assert await fake.alive("sapient/v2/live/*") == []

    fake.declare_token(key)
    early.get_nowait()
    fake.close()
    assert early.get_nowait() == (key, False)  # closing a session drops its tokens
    assert fake.tokens == set()
    assert fake.closed.is_set()


async def test_fake_session_simulates_transport_loss_and_return():
    fake = FakeZenohSession()
    key = live_key(NODE)
    fake.declare_token(key)
    live = fake.liveliness("sapient/v2/live/*")
    assert live.get_nowait() == (key, True)

    fake.lose_transport()
    assert live.get_nowait() == (key, False)
    assert fake.transport_changes.get_nowait() is False
    assert await fake.alive("sapient/v2/live/*") == []
    assert fake.tokens == {key}  # the declaration survives the outage
    assert not fake.closed.is_set()

    fake.restore_transport()
    assert live.get_nowait() == (key, True)
    assert fake.transport_changes.get_nowait() is True
    assert await fake.alive("sapient/v2/live/*") == [key]
