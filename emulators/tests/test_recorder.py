import asyncio
import base64
import json
import logging
from datetime import datetime, timedelta, timezone

import pytest

import recorder
import zenoh_io
from conftest import FakeZenohSession
from recorder import Recorder
import fabric_keys
from zenoh_keys import PREFIX, down_key, live_key, up_key

NODE = "a0000001-0000-4000-8000-000000000001"
TIMEOUT = 5
log = logging.getLogger("test-recorder")


@pytest.fixture
def fake_session():
    return FakeZenohSession()


@pytest.fixture
async def start(fake_session, tmp_path):
    """Start a Recorder on tmp_path, which has subscribed by the time this returns."""
    tasks = []

    async def starter(out_dir=tmp_path):
        task = asyncio.create_task(Recorder(fake_session, out_dir).run())
        tasks.append(task)
        await asyncio.sleep(0)

    yield starter
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def until(condition):
    async with asyncio.timeout(TIMEOUT):
        while not condition():
            await asyncio.sleep(0.01)


def lines_in(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def all_lines(out_dir):
    return [line for path in sorted(out_dir.glob("*.jsonl")) for line in lines_in(path)]


async def lines_after_injecting(fake_session, out_dir, samples):
    for key, payload in samples:
        fake_session.inject(key, payload)
    await until(lambda: len(all_lines(out_dir)) >= len(samples))
    return all_lines(out_dir)


async def test_recorder_writes_one_line_per_sample(tmp_path, fake_session, templates, start):
    await start()
    registration = templates("sensor", "Registration")
    task = templates("fusion_node", "Task.LookAt")

    lines = await lines_after_injecting(fake_session, tmp_path, [
        (up_key(NODE, "registration"), registration.SerializeToString()),
        (down_key(NODE, "task"), task.SerializeToString()),
    ])

    assert [line["kind"] for line in lines] == ["registration", "task"]
    assert [line["node_id"] for line in lines] == [NODE, NODE]
    assert lines[0]["key"] == up_key(NODE, "registration")
    assert "registration" in lines[0]["msg"]
    assert "node_id" in lines[0]["msg"]  # proto field names, not lowerCamelCase
    assert "nodeId" not in lines[0]["msg"]
    assert "error" not in lines[0]


async def test_recorder_stamps_receive_time_in_utc_with_milliseconds(tmp_path, fake_session, templates, start):
    await start()
    before = datetime.now(timezone.utc) - timedelta(milliseconds=1)

    [line] = await lines_after_injecting(fake_session, tmp_path, [
        (up_key(NODE, "alert"), templates("sensor", "Alert").SerializeToString()),
    ])

    stamp = datetime.fromisoformat(line["t"])
    assert stamp.utcoffset() == timedelta(0)
    assert before <= stamp <= datetime.now(timezone.utc)
    assert len(line["t"].split(".")[1].split("+")[0]) == 3


async def test_recorder_keeps_going_on_bad_payload(tmp_path, fake_session, templates, start):
    await start()
    bad = b"\xff\xff\xff"
    good = templates("sensor", "Alert").SerializeToString()

    lines = await lines_after_injecting(fake_session, tmp_path, [
        (up_key(NODE, "alert"), bad),
        (up_key(NODE, "alert"), good),
    ])

    assert lines[0]["error"] == "decode"
    assert lines[0]["key"] == up_key(NODE, "alert")
    assert base64.b64decode(lines[0]["payload_b64"]) == bad
    assert "msg" not in lines[0]
    assert lines[1]["kind"] == "alert"
    assert "msg" in lines[1]


async def test_recorder_treats_a_message_json_cannot_express_as_a_decode_error(
    tmp_path, fake_session, templates, start
):
    await start()
    msg = templates("sensor", "Alert")
    msg.timestamp.seconds = 2**62  # valid on the wire, but no such date exists
    payload = msg.SerializeToString()

    lines = await lines_after_injecting(fake_session, tmp_path, [
        (up_key(NODE, "alert"), payload),
        (up_key(NODE, "alert"), templates("sensor", "Alert").SerializeToString()),
    ])

    assert lines[0]["error"] == "decode"
    assert base64.b64decode(lines[0]["payload_b64"]) == payload
    assert lines[1]["kind"] == "alert"


async def test_recorder_records_keys_that_are_not_node_keys(tmp_path, fake_session, templates, start):
    await start()
    key = f"{PREFIX}sapient/v2/fusion/tracks"

    [line] = await lines_after_injecting(fake_session, tmp_path, [
        (key, templates("fusion_node", "DetectionReport").SerializeToString()),
    ])

    assert line["key"] == key
    assert line["node_id"] is None
    assert line["kind"] is None
    assert "detection_report" in line["msg"]


async def test_recorder_records_a_live_key_without_a_node_id(tmp_path, fake_session, templates, start):
    await start()

    [line] = await lines_after_injecting(fake_session, tmp_path, [
        (live_key(NODE), templates("sensor", "Alert").SerializeToString()),
    ])

    assert line["node_id"] is None
    assert line["kind"] is None


async def test_recorder_starts_a_new_file_each_utc_day(tmp_path, fake_session, templates, start, monkeypatch):
    moments = iter([
        datetime(2026, 11, 8, 23, 59, 59, 999000, tzinfo=timezone.utc),
        datetime(2026, 11, 9, 0, 0, 0, tzinfo=timezone.utc),
    ])
    monkeypatch.setattr(recorder, "_now", lambda: next(moments))
    await start()
    payload = templates("sensor", "Alert").SerializeToString()

    await lines_after_injecting(fake_session, tmp_path, [
        (up_key(NODE, "alert"), payload),
        (up_key(NODE, "alert"), payload),
    ])

    assert sorted(path.name for path in tmp_path.iterdir()) == ["2026-11-08.jsonl", "2026-11-09.jsonl"]
    assert len(lines_in(tmp_path / "2026-11-08.jsonl")) == 1
    assert len(lines_in(tmp_path / "2026-11-09.jsonl")) == 1


async def test_recorder_appends_to_an_existing_file(tmp_path, fake_session, templates, start, monkeypatch):
    moment = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(recorder, "_now", lambda: moment)
    existing = tmp_path / "2026-11-08.jsonl"
    existing.write_text('{"earlier": true}\n')
    await start()

    fake_session.inject(up_key(NODE, "alert"), templates("sensor", "Alert").SerializeToString())
    await until(lambda: len(lines_in(existing)) == 2)

    assert lines_in(existing)[0] == {"earlier": True}


async def test_recorder_creates_a_missing_out_dir(tmp_path, fake_session, templates, start):
    out_dir = tmp_path / "records" / "today"
    await start(out_dir)

    lines = await lines_after_injecting(fake_session, out_dir, [
        (up_key(NODE, "alert"), templates("sensor", "Alert").SerializeToString()),
    ])

    assert len(lines) == 1


async def test_recorder_survives_a_failing_write(tmp_path, fake_session, templates, start, caplog):
    caplog.set_level(logging.INFO)
    out_dir = tmp_path / "records"
    out_dir.write_text("a file where the directory should be")
    await start(out_dir)
    payload = templates("sensor", "Alert").SerializeToString()

    fake_session.inject(up_key(NODE, "alert"), payload)
    await until(lambda: "cannot write" in caplog.text)
    out_dir.unlink()
    lines = await lines_after_injecting(fake_session, out_dir, [(up_key(NODE, "alert"), payload)])

    assert len(lines) == 1


def open_sessions(monkeypatch, sessions):
    """Make the first ZenohSession.open fail, then hand out sessions; returns the attempts."""
    remaining = iter(sessions)
    attempts = []

    async def fake_open(connect, loop, tls=None):
        attempts.append(connect)
        if len(attempts) == 1:
            raise zenoh_io.zenoh.ZError("router unreachable")
        return next(remaining)

    monkeypatch.setattr(zenoh_io.ZenohSession, "open", fake_open)
    monkeypatch.setattr(zenoh_io, "RECONNECT_SECONDS", 0)
    return attempts


async def test_run_retries_the_router_records_and_ends_when_the_session_closes(
    monkeypatch, tmp_path, fake_session, templates
):
    attempts = open_sessions(monkeypatch, [fake_session])
    runner = asyncio.create_task(recorder.run("tcp/router:7447", tmp_path, log))
    try:
        await until(lambda: fake_session._subscriptions)
        assert attempts == ["tcp/router:7447"] * 2

        fake_session.inject(up_key(NODE, "alert"), templates("sensor", "Alert").SerializeToString())
        await until(lambda: all_lines(tmp_path))

        fake_session.closed.set()
        await asyncio.wait_for(runner, TIMEOUT)
    finally:
        runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)


async def test_run_raises_and_closes_the_session_when_recording_fails(monkeypatch, tmp_path):
    class CannotSubscribe(FakeZenohSession):
        def subscribe(self, keyexpr):
            raise RuntimeError("no subscription for you")

    session = CannotSubscribe()
    open_sessions(monkeypatch, [session])

    with pytest.raises(RuntimeError, match="no subscription for you"):
        await asyncio.wait_for(recorder.run("tcp/router:7447", tmp_path, log), TIMEOUT)

    assert session.closed.is_set()


# ---- the fabric keys (RECORD_KEYS=fabric) ----------------------------------------------------

ANCHOR = "18214b1a34e3c722d1cac283b272a62c"
FUSION = "f0000001-0000-4000-8000-000000000001"


@pytest.fixture
async def fabric_recorder(fake_session, tmp_path):
    """A Recorder of the fabric keys on tmp_path, which has subscribed by the time this returns."""
    expressions, describe = recorder.record_keys("fabric")
    task = asyncio.create_task(Recorder(fake_session, tmp_path, expressions, describe).run())
    await asyncio.sleep(0)
    yield
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.usefixtures("fabric_recorder")
async def test_fabric_mode_subscribes_to_the_three_classes(fake_session):
    assert [keyexpr for keyexpr, _ in fake_session._subscriptions] == list(fabric_keys.subscriptions())


@pytest.mark.usefixtures("fabric_recorder")
async def test_fabric_record_has_anchor_site_kind_and_node_id(tmp_path, fake_session, templates):
    key = fabric_keys.key_for(ANCHOR, "p1", "detection_report", FUSION)

    [line] = await lines_after_injecting(fake_session, tmp_path, [
        (key, templates("fusion_node", "DetectionReport").SerializeToString()),
    ])

    assert list(line) == ["t", "key", "kind", "node_id", "anchor", "site", "msg"]
    assert line["key"] == key
    assert line["kind"] == "detection_report"
    assert line["node_id"] == FUSION
    assert line["anchor"] == ANCHOR
    assert line["site"] == "p1"
    assert "detection_report" in line["msg"]


@pytest.mark.usefixtures("fabric_recorder")
async def test_fabric_record_of_a_malformed_key_keeps_the_key_only(tmp_path, fake_session, templates):
    key = f"{ANCHOR}/telemetry/sapient/p1/v2/detection_report/not-a-uuid"

    [line] = await lines_after_injecting(fake_session, tmp_path, [
        (key, templates("fusion_node", "DetectionReport").SerializeToString()),
    ])

    assert line["key"] == key
    assert [line[field] for field in ("kind", "node_id", "anchor", "site")] == [None] * 4
    assert "detection_report" in line["msg"]


def test_pod_mode_is_the_default(monkeypatch):
    monkeypatch.delenv("RECORD_KEYS", raising=False)
    started = []

    def fake_run(connect, out_dir, log, keys):
        started.append(keys)
        return asyncio.sleep(0)

    monkeypatch.setattr(recorder, "run", fake_run)
    monkeypatch.setattr(asyncio, "run", lambda coroutine: coroutine.close())

    recorder.main()

    assert started == ["pod"]
    assert recorder.record_keys("pod") == ((f"{PREFIX}sapient/v2/**",), recorder.describe_pod_key)


def test_an_unknown_record_keys_value_is_refused(monkeypatch):
    monkeypatch.setenv("RECORD_KEYS", "host")
    monkeypatch.setattr(asyncio, "run", lambda coroutine: coroutine.close())

    with pytest.raises(ValueError, match="RECORD_KEYS"):
        recorder.main()
