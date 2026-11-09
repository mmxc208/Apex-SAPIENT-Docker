import asyncio

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
async def test_closed_is_set_by_close_and_by_losing_the_transport():
    loop = asyncio.get_running_loop()
    router = await ZenohSession.open_peer_listen("tcp/127.0.0.1:17450", loop)
    leaving = await ZenohSession.open("tcp/127.0.0.1:17450", loop)
    staying = await ZenohSession.open("tcp/127.0.0.1:17450", loop)
    leaving.close()
    assert leaving.closed.is_set()
    await asyncio.sleep(0.5)
    assert not staying.closed.is_set()  # another client leaving is not this client's transport
    assert not router.closed.is_set()
    router.close()
    await asyncio.wait_for(staying.closed.wait(), 15)
    staying.close()


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
