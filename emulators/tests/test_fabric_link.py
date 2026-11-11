"""The host fusion node's link to the fabric: goat's keys, routes learnt from pods, own output skipped."""
import asyncio
import logging

import pytest

import fabric_keys
from conftest import FakeZenohSession
from fabric_keys import key_for, live_key
from fabric_link import FabricFusionLink
from sapient_link import load_template, stamp
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

ANCHOR = "18214b1a34e3c722d1cac283b272a62c"
HOST = "b005ae3a8f2baf89160bd71632902672"
OTHER = "1ab0be0bcfdc3997544545af2235dd6d"
FUSION = "f0000001-0000-4000-8000-000000000001"
HOSTFUSION = "b0000001-0000-4000-8000-000000000001"
TIMEOUT = 5
log = logging.getLogger("test-fabric-link")


@pytest.fixture
def session():
    return FakeZenohSession()


@pytest.fixture
async def link(session):
    return await FabricFusionLink.connect(session, HOSTFUSION, HOST, "h1", log)


def message(group, name, node_id=FUSION, destination=None) -> SapientMessage:
    return stamp(load_template(group, name), node_id, destination)


def published_keys(session) -> list[str]:
    return [key for key, _, _ in session.published]


async def received(link):
    return await asyncio.wait_for(link.receive_raw(), TIMEOUT)


async def test_connect_subscribes_to_the_three_classes_with_a_first_part_wildcard(session, link):
    expressions = {expr for expr, _ in session._subscriptions}

    assert expressions == set(fabric_keys.subscriptions())
    assert all(expr.split("/")[0] == "*" and "**" not in expr for expr in expressions)
    assert link.live_all == fabric_keys.live_subscription()


async def test_receive_gives_a_pod_message_and_its_key(session, link):
    key = key_for(ANCHOR, "p1", "registration", FUSION)
    payload = message("sensor", "Registration").SerializeToString()

    session.inject(key, payload)
    packet, msg = await received(link)

    assert packet == payload
    assert msg.node_id == FUSION
    assert link.last_sample == (key, payload)
    assert link.owner_of(link.last_sample[0]) == FUSION


async def test_own_output_is_not_received(session, link):
    session.inject(key_for(HOST, "h1", "status_report", HOSTFUSION), message("sensor", "StatusReport").SerializeToString())
    key = key_for(ANCHOR, "p1", "status_report", FUSION)
    session.inject(key, message("sensor", "StatusReport").SerializeToString())

    await received(link)

    assert link.last_sample[0] == key


async def test_a_node_id_belongs_to_the_first_anchor_seen(session, link, caplog):
    first = key_for(ANCHOR, "p1", "status_report", FUSION)
    stranger = key_for(OTHER, "p1", "status_report", FUSION)
    payload = message("sensor", "StatusReport").SerializeToString()

    session.inject(first, payload)
    await received(link)
    with caplog.at_level(logging.INFO):
        session.inject(stranger, payload)
        session.inject(stranger, payload)
        session.inject(first, payload)
        await received(link)

    assert link.last_sample[0] == first
    assert sum(OTHER in r.getMessage() and FUSION in r.getMessage() for r in caplog.records) == 1


@pytest.mark.parametrize(
    "bad",
    [
        f"{ANCHOR}/telemetry/sapient/p1/v2/registration/not-a-uuid",
        f"{ANCHOR}/telemetry/sapient/P1/v2/registration/{FUSION}",
        f"{ANCHOR}/telemetry/sapient/p1/v2/nokind/{FUSION}",
        f"{ANCHOR[:-1]}/telemetry/sapient/p1/v2/registration/{FUSION}",
    ],
)
async def test_malformed_keys_are_skipped_and_the_loop_continues(session, link, caplog, bad):
    good = key_for(ANCHOR, "p1", "registration", FUSION)
    payload = message("sensor", "Registration").SerializeToString()

    with caplog.at_level(logging.INFO):
        session.inject(bad, payload)
        session.inject(good, payload)
        await received(link)

    assert link.last_sample[0] == good
    assert any(bad in r.getMessage() for r in caplog.records)


async def test_send_with_a_destination_uses_the_node_s_site_and_class(session, link):
    session.inject(key_for(ANCHOR, "p1", "registration", FUSION), message("sensor", "Registration").SerializeToString())
    await received(link)

    await link.send(message("fusion_node", "Task.LookAt", HOSTFUSION, FUSION))
    await link.send(message("fusion_node", "RegistrationAck", HOSTFUSION, FUSION))

    assert published_keys(session) == [
        f"{HOST}/task/p1/sapient/v2/task/{FUSION}",
        f"{HOST}/ack/p1/sapient/v2/registration_ack/{FUSION}",
    ]


async def test_send_to_an_unknown_node_publishes_nothing_and_logs(session, link, caplog):
    with caplog.at_level(logging.INFO):
        await link.send(message("fusion_node", "Task.LookAt", HOSTFUSION, FUSION))

    assert session.published == []
    assert any(FUSION in r.getMessage() for r in caplog.records)


async def test_own_output_goes_below_the_own_anchor_at_the_own_site(session, link):
    await link.send(message("sensor", "StatusReport", HOSTFUSION))

    assert published_keys(session) == [f"{HOST}/telemetry/sapient/h1/v2/status_report/{HOSTFUSION}"]


async def test_own_output_of_a_kind_that_goes_down_only_publishes_nothing(session, link, caplog):
    with caplog.at_level(logging.INFO):
        await link.send(message("fusion_node", "Task.LookAt", HOSTFUSION))

    assert session.published == []
    assert any("task" in r.getMessage() for r in caplog.records)


async def test_a_live_key_teaches_the_route(session, link):
    assert link.node_of_live_key(live_key(ANCHOR, "p1", FUSION)) == FUSION

    await link.send(message("fusion_node", "Task.LookAt", HOSTFUSION, FUSION))

    assert published_keys(session) == [f"{HOST}/task/p1/sapient/v2/task/{FUSION}"]


async def test_a_live_key_below_another_anchor_than_the_route_is_refused(link):
    link.node_of_live_key(live_key(ANCHOR, "p1", FUSION))

    with pytest.raises(ValueError):
        link.node_of_live_key(live_key(OTHER, "p1", FUSION))


def test_a_malformed_live_key_is_refused(session):
    link = FabricFusionLink(session, HOSTFUSION, HOST, "h1", [], log)

    with pytest.raises(ValueError):
        link.node_of_live_key(key_for(ANCHOR, "p1", "registration", FUSION))


async def test_owner_of_a_malformed_key_is_none(link):
    assert link.owner_of("sapient/v2/x/up/registration") is None


async def test_send_upward_does_nothing(session, link):
    await link.send_upward(message("sensor", "Registration", HOSTFUSION))

    assert session.published == []


async def test_receive_raises_connection_error_once_the_session_is_closed(session, link):
    session.close()

    with pytest.raises(ConnectionError):
        await received(link)
