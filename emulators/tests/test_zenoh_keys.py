import importlib

import pytest
import zenoh

import zenoh_keys
from sapient_link import SapientMessage
from zenoh_keys import (
    DOWN_FOR,
    LIVE_ALL,
    UP_ALL,
    down_key,
    kind_of,
    live_key,
    node_id_from_live_key,
    parse_key,
    qos_for,
    up_key,
)

NODE = "a0000001-0000-4000-8000-000000000001"

HIGH = zenoh.Priority.INTERACTIVE_HIGH
LOW = zenoh.Priority.INTERACTIVE_LOW
DATA = zenoh.Priority.DATA
DATA_HIGH = zenoh.Priority.DATA_HIGH
BLOCK = zenoh.CongestionControl.BLOCK
DROP = zenoh.CongestionControl.DROP


def test_keys_round_trip():
    assert up_key(NODE, "detection_report") == f"sapient/v2/{NODE}/up/detection_report"
    assert down_key(NODE, "task") == f"sapient/v2/{NODE}/down/task"
    assert live_key(NODE) == f"sapient/v2/live/{NODE}"
    assert parse_key(up_key(NODE, "alert")) == (NODE, "up", "alert")
    assert parse_key(down_key(NODE, "task")) == (NODE, "down", "task")
    assert node_id_from_live_key(live_key(NODE)) == NODE


def test_wildcards():
    assert UP_ALL == "sapient/v2/*/up/**"
    assert DOWN_FOR(NODE) == f"sapient/v2/{NODE}/down/**"
    assert LIVE_ALL == "sapient/v2/live/*"


def test_kind_of(templates):
    assert kind_of(templates("sensor", "Registration")) == "registration"


def test_qos_matrix():
    assert qos_for("task") == (zenoh.Priority.INTERACTIVE_HIGH, zenoh.CongestionControl.BLOCK, True)
    assert qos_for("detection_report") == (zenoh.Priority.DATA, zenoh.CongestionControl.DROP, False)
    assert qos_for("detection_report", fused=True) == (zenoh.Priority.DATA_HIGH, zenoh.CongestionControl.BLOCK, False)


@pytest.mark.parametrize(
    "kind, expected",
    [
        ("task", (HIGH, BLOCK, True)),
        ("task_ack", (HIGH, BLOCK, True)),
        ("alert", (HIGH, BLOCK, True)),
        ("alert_ack", (HIGH, BLOCK, True)),
        ("registration", (LOW, BLOCK, False)),
        ("registration_ack", (LOW, BLOCK, False)),
        ("status_report", (DATA, BLOCK, False)),
        ("detection_report", (DATA, DROP, False)),
    ],
)
def test_qos_table_rows(kind, expected):
    assert qos_for(kind) == expected


@pytest.mark.parametrize("kind", ["registration", "status_report", "task", "alert"])
def test_fused_only_changes_detection_reports(kind):
    assert qos_for(kind, fused=True) == qos_for(kind)


def test_every_message_kind_has_qos():
    for field in SapientMessage.DESCRIPTOR.oneofs_by_name["content"].fields:
        qos_for(field.name)


def test_unknown_kind_has_no_qos():
    with pytest.raises(ValueError):
        qos_for("not_a_kind")


def test_bad_node_id_rejected():
    with pytest.raises(ValueError):
        up_key("not-a-uuid", "task")
    with pytest.raises(ValueError):
        up_key(NODE, "x" * 300)


@pytest.mark.parametrize(
    "node_id",
    [
        "",
        NODE.upper(),
        NODE.replace("-", ""),
        "{" + NODE + "}",
        "urn:uuid:" + NODE,
    ],
)
@pytest.mark.parametrize("build", [lambda n: up_key(n, "task"), lambda n: down_key(n, "task"), live_key, DOWN_FOR])
def test_non_canonical_node_id_rejected(build, node_id):
    with pytest.raises(ValueError):
        build(node_id)


@pytest.fixture
def keys_with_prefix(monkeypatch):
    """Reload zenoh_keys under a given ZENOH_KEY_PREFIX; restore the original afterwards."""

    def reload_with(prefix):
        monkeypatch.setenv("ZENOH_KEY_PREFIX", prefix)
        return importlib.reload(zenoh_keys)

    yield reload_with
    monkeypatch.undo()
    importlib.reload(zenoh_keys)


def test_key_length_limit_is_256_bytes(keys_with_prefix):
    room = 256 - len(f"sapient/v2/{NODE}/up/task")
    assert len(keys_with_prefix("p" * (room - 1) + "/").up_key(NODE, "task")) == 256
    with pytest.raises(ValueError):
        keys_with_prefix("p" * room + "/").up_key(NODE, "task")
    # The limit counts encoded bytes, not characters.
    with pytest.raises(ValueError):
        keys_with_prefix("é" * (room - 1) + "/").up_key(NODE, "task")


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        up_key(NODE, None)
    with pytest.raises(ValueError):
        down_key(NODE, "bogus")


def test_kinds_match_the_message_oneof():
    fields = SapientMessage.DESCRIPTOR.oneofs_by_name["content"].fields
    assert zenoh_keys.KINDS == {field.name for field in fields}


@pytest.mark.parametrize(
    "key",
    [
        "",
        "sapient/v2",
        f"other/v2/{NODE}/up/task",
        f"sapient/v1/{NODE}/up/task",
        f"sapient/v2/{NODE}/sideways/task",
        f"sapient/v2/{NODE}/up/",
        f"sapient/v2/{NODE}/up/task/extra",
        "sapient/v2/not-a-uuid/up/task",
        f"sapient/v2/live/{NODE}",
    ],
)
def test_parse_key_rejects_malformed(key):
    with pytest.raises(ValueError):
        parse_key(key)


@pytest.mark.parametrize(
    "key",
    [
        "",
        f"other/v2/live/{NODE}",
        f"sapient/v2/live/{NODE}/extra",
        "sapient/v2/live/not-a-uuid",
        f"sapient/v2/{NODE}/up/task",
    ],
)
def test_node_id_from_live_key_rejects_malformed(key):
    with pytest.raises(ValueError):
        node_id_from_live_key(key)


def test_prefix_from_env(keys_with_prefix):
    keys = keys_with_prefix("h1/p1/")
    assert keys.up_key(NODE, "task").startswith("h1/p1/sapient/v2/")
    assert keys.UP_ALL == "h1/p1/sapient/v2/*/up/**"
    assert keys.parse_key(keys.down_key(NODE, "task")) == (NODE, "down", "task")
    assert keys.node_id_from_live_key(keys.live_key(NODE)) == NODE


def test_prefix_without_trailing_slash_rejected(keys_with_prefix):
    with pytest.raises(ValueError):
        keys_with_prefix("h1/p1")
