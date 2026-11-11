import asyncio
import logging

import pytest
import zenoh

import pod_bridge
import zenoh_io
from conftest import FakeZenohSession
from fabric_keys import key_for, live_key, subscriptions
from pod_bridge import PodBridge
from sapient_link import load_template, stamp
from zenoh_keys import FUSION_UP_ALL, fusion_down_key, fusion_up_key, qos_for

ANCHOR = "18214b1a34e3c722d1cac283b272a62c"
HOST = "b005ae3a8f2baf89160bd71632902672"
FUSION = "f0000001-0000-4000-8000-000000000001"
OTHER = "f0000002-0000-4000-8000-000000000002"
SITE = "p1"
NOW = 1_800_000_000.0
TIMEOUT = 5
log = logging.getLogger("test-pod-bridge")


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def pod():
    return FakeZenohSession()


@pytest.fixture
def fabric():
    return FakeZenohSession()


@pytest.fixture
def bridge(pod, fabric, clock):
    return PodBridge(pod, fabric, anchor=ANCHOR, site=SITE, host_anchors=[HOST], log=log, clock=clock)


def from_fusion(group, name, node_id=FUSION):
    return stamp(load_template(group, name), node_id).SerializeToString()


def detection_report() -> bytes:
    return from_fusion("fusion_node", "DetectionReport")


def registration() -> bytes:
    return from_fusion("sensor", "Registration")


def task(age: float = 0.0, destination: str = FUSION) -> bytes:
    msg = stamp(load_template("fusion_node", "Task.Request.Status"), HOST, destination)
    msg.timestamp.FromNanoseconds(int((NOW - age) * 1e9))
    return msg.SerializeToString()


def registration_ack(age: float = 0.0) -> bytes:
    msg = stamp(load_template("fusion_node", "RegistrationAck"), HOST, FUSION)
    msg.timestamp.FromNanoseconds(int((NOW - age) * 1e9))
    return msg.SerializeToString()


def down_key(kind: str, node_id: str = FUSION) -> str:
    return key_for(HOST, SITE, kind, node_id)


async def prime(bridge) -> None:
    """The fusion node has sent something up, so the host may address it."""
    await bridge.forward_up(fusion_up_key("registration"), registration())


async def test_up_forwards_the_same_bytes_on_the_fabric_key(bridge, fabric):
    payload = detection_report()
    await bridge.forward_up(fusion_up_key("detection_report"), payload)
    assert fabric.published == [
        (key_for(ANCHOR, SITE, "detection_report", FUSION), payload, qos_for("detection_report", True))
    ]
    assert bridge.forwarded["up"] == 1
    assert sum(bridge.dropped.values()) == 0


async def test_up_task_ack_goes_to_the_ack_class(bridge, fabric):
    payload = from_fusion("sensor", "TaskAck.Request.Status")
    await bridge.forward_up(fusion_up_key("task_ack"), payload)
    assert fabric.published == [
        (f"{ANCHOR}/ack/p1/sapient/v2/task_ack/{FUSION}", payload, qos_for("task_ack", True))
    ]


async def test_first_up_message_declares_the_token(bridge, fabric):
    assert fabric.tokens == set()
    await prime(bridge)
    assert fabric.tokens == {f"{ANCHOR}/telemetry/sapient/p1/v2/live/{FUSION}"}
    assert fabric.tokens == {live_key(ANCHOR, SITE, FUSION)}


async def test_token_goes_after_30_s_without_traffic_and_returns_with_traffic(bridge, fabric, clock):
    token = live_key(ANCHOR, SITE, FUSION)
    await prime(bridge)
    clock.now += 29.9
    bridge.expire_presence()
    assert token in fabric.tokens
    clock.now += 0.1
    bridge.expire_presence()
    assert token not in fabric.tokens
    await bridge.forward_up(fusion_up_key("detection_report"), detection_report())
    assert token in fabric.tokens


async def test_traffic_keeps_the_token(bridge, fabric, clock):
    await prime(bridge)
    clock.now += 20
    await bridge.forward_up(fusion_up_key("detection_report"), detection_report())
    clock.now += 20
    bridge.expire_presence()
    assert live_key(ANCHOR, SITE, FUSION) in fabric.tokens


async def test_token_goes_when_the_pod_router_is_lost(bridge, fabric):
    await prime(bridge)
    bridge.on_transport("pod", False)
    assert fabric.tokens == set()
    bridge.on_transport("pod", True)
    assert fabric.tokens == set()  # presence follows traffic: it returns with the next message
    await bridge.forward_up(fusion_up_key("detection_report"), detection_report())
    assert live_key(ANCHOR, SITE, FUSION) in fabric.tokens


async def test_the_token_is_kept_when_only_the_fabric_router_is_lost(bridge, fabric):
    await prime(bridge)
    bridge.on_transport("fabric", False)
    assert live_key(ANCHOR, SITE, FUSION) in fabric.tokens  # the session replays it on return


async def test_down_task_reaches_the_pod_fusion_keys_unchanged(bridge, pod):
    await prime(bridge)
    payload = task()
    await bridge.forward_down(down_key("task"), payload)
    assert pod.published[-1][:2] == (fusion_down_key("task"), payload)
    assert bridge.forwarded["down"] == 1


@pytest.mark.parametrize(
    "kind, payload",
    [("registration_ack", registration_ack), ("task", task)],
)
async def test_down_kinds_land_on_their_own_fusion_key(bridge, pod, kind, payload):
    await prime(bridge)
    body = payload()
    await bridge.forward_down(down_key(kind), body)
    assert pod.published[-1][:2] == (fusion_down_key(kind), body)


@pytest.mark.parametrize(
    "case",
    ["undecodable", "wrong_destination", "unknown_destination", "stale_task", "bad_key", "bad_kind"],
)
async def test_down_drops_and_counts(bridge, pod, case):
    key, payload = down_key("task"), task()
    if case != "unknown_destination":
        await prime(bridge)
    if case == "undecodable":
        payload = b"\xff\xff"
    elif case == "wrong_destination":
        payload = task(destination=OTHER)
    elif case == "stale_task":
        payload = task(age=6)
    elif case == "bad_key":
        key = f"{HOST}/task/p1/sapient/v2/task/not-a-uuid"
    elif case == "bad_kind":
        key, payload = down_key("detection_report"), detection_report()
    await bridge.forward_down(key, payload)
    assert bridge.dropped == {case: 1}
    assert pod.published == []
    assert bridge.forwarded["down"] == 0


async def test_down_from_an_anchor_that_is_not_allowed_is_bad_key(bridge, pod):
    await prime(bridge)
    stranger = "0" * 32
    await bridge.forward_down(key_for(stranger, SITE, "task", FUSION), task())
    await bridge.forward_down(key_for(HOST, "p2", "task", FUSION), task())
    assert bridge.dropped == {"bad_key": 2}
    assert pod.published == []


async def test_a_content_that_does_not_match_the_key_kind_is_bad_kind(bridge, pod, fabric):
    await prime(bridge)
    await bridge.forward_down(down_key("task"), registration_ack())
    await bridge.forward_up(fusion_up_key("alert"), detection_report())
    assert bridge.dropped == {"bad_kind": 2}
    assert pod.published == []
    assert len(fabric.published) == 1  # only the priming registration


async def test_a_task_4_s_old_is_forwarded(bridge, pod):
    await prime(bridge)
    await bridge.forward_down(down_key("task"), task(age=4))
    assert len(pod.published) == 1
    assert bridge.dropped == {}


async def test_a_task_without_a_timestamp_is_stale(bridge, pod):
    await prime(bridge)
    msg = stamp(load_template("fusion_node", "Task.Request.Status"), HOST, FUSION)
    msg.ClearField("timestamp")
    await bridge.forward_down(down_key("task"), msg.SerializeToString())
    assert bridge.dropped == {"stale_task": 1}


async def test_registration_ack_is_not_subject_to_the_age_limit(bridge, pod):
    await prime(bridge)
    await bridge.forward_down(down_key("registration_ack"), registration_ack(age=60))
    assert len(pod.published) == 1
    assert bridge.dropped == {}


@pytest.mark.parametrize("case", ["undecodable", "bad_key", "bad_kind"])
async def test_up_drops_and_counts(bridge, fabric, case):
    key, payload = fusion_up_key("detection_report"), detection_report()
    if case == "undecodable":
        payload = b"\xff\xff"
    elif case == "bad_key":
        key = "sapient/v2/%s/up/alert" % FUSION  # a sensor key, not a fusion up key
    elif case == "bad_kind":
        key, payload = fusion_up_key("task"), task()
    await bridge.forward_up(key, payload)
    assert bridge.dropped == {case: 1}
    assert fabric.published == []
    assert fabric.tokens == set()


async def test_up_refuses_a_down_key(bridge, fabric):
    await bridge.forward_up(fusion_down_key("task"), task())
    assert bridge.dropped == {"bad_key": 1}
    assert fabric.published == []


async def test_nothing_crosses_while_the_other_side_is_down(bridge, pod, fabric):
    await prime(bridge)
    published = len(fabric.published)

    bridge.on_transport("fabric", False)
    await bridge.forward_up(fusion_up_key("detection_report"), detection_report())
    assert bridge.dropped == {"other_side_down": 1}
    assert len(fabric.published) == published
    bridge.on_transport("fabric", True)
    await bridge.forward_up(fusion_up_key("detection_report"), detection_report())
    assert len(fabric.published) == published + 1

    bridge.on_transport("pod", False)
    await bridge.forward_down(down_key("task"), task())
    assert bridge.dropped == {"other_side_down": 2}
    assert pod.published == []
    bridge.on_transport("pod", True)
    await bridge.forward_down(down_key("task"), task())
    assert len(pod.published) == 1


async def test_a_bad_sample_keeps_its_own_reason_while_the_other_side_is_down(bridge):
    bridge.on_transport("fabric", False)
    await bridge.forward_up(fusion_up_key("detection_report"), b"\xff\xff")
    assert bridge.dropped == {"undecodable": 1}


async def test_a_failed_publish_is_counted_and_not_raised(bridge, fabric):
    async def refuse(*args, **kwargs):
        raise zenoh.ZError("congested")

    fabric.publish_raw = refuse
    await bridge.forward_up(fusion_up_key("detection_report"), detection_report())
    assert bridge.dropped == {"publish_error": 1}
    assert bridge.forwarded["up"] == 0
    assert fabric.tokens == set()


async def until(condition, timeout=TIMEOUT):
    async def poll():
        while not condition():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(poll(), timeout)


async def running(bridge):
    task_ = asyncio.create_task(bridge.run())
    await asyncio.sleep(0)
    return task_


async def stop(task_):
    task_.cancel()
    await asyncio.gather(task_, return_exceptions=True)


async def test_a_host_that_is_not_allowed_is_not_subscribed(pod, fabric, clock):
    bridge = PodBridge(pod, fabric, anchor=ANCHOR, site=SITE, host_anchors=[HOST], log=log, clock=clock)
    runner = await running(bridge)
    try:
        assert [keyexpr for keyexpr, _ in fabric._subscriptions] == list(subscriptions(HOST, "p1"))
        assert [keyexpr for keyexpr, _ in pod._subscriptions] == [FUSION_UP_ALL]
    finally:
        await stop(runner)


async def test_run_carries_both_directions(bridge, pod, fabric):
    runner = await running(bridge)
    try:
        payload = registration()
        pod.inject(fusion_up_key("registration"), payload)
        await until(lambda: fabric.published)
        assert fabric.published[0][:2] == (key_for(ANCHOR, SITE, "registration", FUSION), payload)

        down = task()
        fabric.inject(down_key("task"), down)
        await until(lambda: pod.published)
        assert pod.published[0][:2] == (fusion_down_key("task"), down)
    finally:
        await stop(runner)


async def test_run_keeps_going_after_a_bad_sample_and_applies_transport_changes(bridge, pod, fabric):
    runner = await running(bridge)
    try:
        pod.inject(fusion_up_key("detection_report"), b"\xff\xff")
        pod.inject(fusion_up_key("registration"), registration())
        await until(lambda: fabric.published)
        assert bridge.dropped["undecodable"] == 1

        pod.lose_transport()
        await until(lambda: not fabric.tokens)
        pod.restore_transport()
        fabric.lose_transport()
        pod.inject(fusion_up_key("detection_report"), detection_report())
        await until(lambda: bridge.dropped["other_side_down"] == 1)
        assert not runner.done()
    finally:
        await stop(runner)


async def test_run_survives_a_pump_error(bridge, pod, fabric):
    calls = []

    async def flaky(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise RuntimeError("boom")
        fabric.published.append(args)

    fabric.publish_raw = flaky
    runner = await running(bridge)
    try:
        pod.inject(fusion_up_key("registration"), registration())
        pod.inject(fusion_up_key("registration"), registration())
        await until(lambda: len(calls) == 2)
        assert not runner.done()
    finally:
        await stop(runner)


async def test_run_expires_presence_and_logs_counters(bridge, pod, fabric, clock, monkeypatch, caplog):
    monkeypatch.setattr(pod_bridge, "EXPIRE_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(pod_bridge, "COUNTER_LOG_SECONDS", 0.01)
    caplog.set_level(logging.INFO, logger=log.name)
    await prime(bridge)
    runner = await running(bridge)
    try:
        clock.now += 31
        await until(lambda: not fabric.tokens)
        assert "forwarded" not in caplog.text  # nothing has changed since the run began
        pod.inject(fusion_up_key("detection_report"), detection_report())
        await until(lambda: "forwarded {'up': 2}" in caplog.text)
    finally:
        await stop(runner)


async def test_queue_keeps_512_and_drops_the_oldest(bridge, pod, fabric):
    release = asyncio.Event()
    published = []

    async def slow(key, payload, kind, fused=False):
        await release.wait()
        published.append(payload)

    fabric.publish_raw = slow
    runner = await running(bridge)
    try:
        samples = []
        for n in range(600):
            msg = stamp(load_template("fusion_node", "DetectionReport"), FUSION)
            msg.timestamp.FromNanoseconds(n + 1)
            samples.append(msg.SerializeToString())
            pod.inject(fusion_up_key("detection_report"), samples[-1])
        await until(lambda: bridge.dropped["queue_full"] >= 87)
        release.set()
        await until(lambda: len(published) >= 512)
        await asyncio.sleep(0.05)
    finally:
        await stop(runner)
    assert 87 <= bridge.dropped["queue_full"] <= 88
    assert len(published) <= 513
    assert samples[-1] in published
    assert samples[0] not in published


def open_failing(monkeypatch, failures_per_side):
    attempts = []
    remaining = {"tcp/pod:7447": failures_per_side, "tcp/fabric:7447": failures_per_side}
    sessions = {"tcp/pod:7447": FakeZenohSession(), "tcp/fabric:7447": FakeZenohSession()}

    async def fake_open(connect, loop, tls=None):
        attempts.append((connect, tls))
        if remaining[connect]:
            remaining[connect] -= 1
            raise zenoh.ZError("router unreachable")
        return sessions[connect]

    monkeypatch.setattr(zenoh_io.ZenohSession, "open", fake_open)
    monkeypatch.setattr(zenoh_io, "RECONNECT_SECONDS", 0)
    return attempts, sessions


async def test_main_survives_routers_that_are_not_there_yet(monkeypatch):
    attempts, sessions = open_failing(monkeypatch, 2)
    for name, value in {
        "POD_CONNECT": "tcp/pod:7447",
        "FABRIC_CONNECT": "tcp/fabric:7447",
        "FABRIC_ANCHOR": ANCHOR,
        "FABRIC_SITE": SITE,
        "FABRIC_HOST_ANCHORS": f" {HOST} ,",
        "POD_TLS_CA": "/pod/ca.pem",
        "POD_TLS_CERT": "/pod/c.pem",
        "POD_TLS_KEY": "/pod/c.key",
    }.items():
        monkeypatch.setenv(name, value)
    for name in ("FABRIC_TLS_CA", "FABRIC_TLS_CERT", "FABRIC_TLS_KEY"):
        monkeypatch.delenv(name, raising=False)
    reached = []

    async def fake_run(self):
        reached.append(self)

    monkeypatch.setattr(PodBridge, "run", fake_run)
    await asyncio.wait_for(pod_bridge.main_async(), TIMEOUT)
    assert len(attempts) == 6
    assert len(reached) == 1
    assert reached[0].host_anchors == [HOST]
    assert reached[0].anchor == ANCHOR
    assert dict(attempts)["tcp/pod:7447"] == zenoh_io.TlsOptions("/pod/ca.pem", "/pod/c.pem", "/pod/c.key")
    assert dict(attempts)["tcp/fabric:7447"] is None
    assert all(session.closed.is_set() for session in sessions.values())


async def test_main_refuses_an_empty_host_list(monkeypatch):
    open_failing(monkeypatch, 0)
    for name, value in {
        "POD_CONNECT": "tcp/pod:7447",
        "FABRIC_CONNECT": "tcp/fabric:7447",
        "FABRIC_ANCHOR": ANCHOR,
        "FABRIC_SITE": SITE,
        "FABRIC_HOST_ANCHORS": " , ",
    }.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="FABRIC_HOST_ANCHORS"):
        await pod_bridge.main_async()
