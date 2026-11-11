"""Zenoh key namespace and per-message QoS for SAPIENT (BSI Flex 335 v2.0) traffic.

Keys hold only fixed-width node UUIDs, never report IDs, task IDs or timestamps:
    <PREFIX>sapient/v2/<node_id>/up/<kind>
    <PREFIX>sapient/v2/<node_id>/down/<kind>
    <PREFIX>sapient/v2/live/<node_id>
A pod's fusion node also faces a future host on:
    <PREFIX>fusion/up/<kind>
    <PREFIX>fusion/down/<kind>
<kind> is the SapientMessage.content oneof field name.
"""
import os
import uuid

import zenoh

from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

PREFIX: str = os.environ.get("ZENOH_KEY_PREFIX", "")
if PREFIX and not PREFIX.endswith("/"):
    raise ValueError(f"ZENOH_KEY_PREFIX must end with '/': {PREFIX!r}")
MAX_KEY_BYTES = 256

_ROOT = f"{PREFIX}sapient/v2"
_LIVE = f"{_ROOT}/live"

UP_ALL: str = f"{_ROOT}/*/up/**"
LIVE_ALL: str = f"{_LIVE}/*"
FUSION_UP_ALL: str = f"{PREFIX}fusion/up/**"
FUSION_DOWN_ALL: str = f"{PREFIX}fusion/down/**"

_CONTROL = (zenoh.Priority.INTERACTIVE_HIGH, zenoh.CongestionControl.BLOCK, True)
_SESSION = (zenoh.Priority.INTERACTIVE_LOW, zenoh.CongestionControl.BLOCK, False)
_FUSED_TRACK = (zenoh.Priority.DATA_HIGH, zenoh.CongestionControl.BLOCK, False)

_QOS = {
    "task": _CONTROL,
    "task_ack": _CONTROL,
    "alert": _CONTROL,
    "alert_ack": _CONTROL,
    "registration": _SESSION,
    "registration_ack": _SESSION,
    # Errors are control traffic, so they share the registration row and are never dropped.
    "error": _SESSION,
    "status_report": (zenoh.Priority.DATA, zenoh.CongestionControl.BLOCK, False),
    "detection_report": (zenoh.Priority.DATA, zenoh.CongestionControl.DROP, False),
}

# The SapientMessage.content oneof field names.
KINDS: frozenset[str] = frozenset(_QOS)


def _checked_node_id(node_id: str) -> str:
    """Return node_id if it is a canonical UUID: 36 chars, hyphenated, lowercase."""
    if str(uuid.UUID(node_id)) != node_id:
        raise ValueError(f"node_id is not a canonical UUID: {node_id!r}")
    return node_id


def _checked_kind(kind: str) -> str:
    if kind not in KINDS:
        raise ValueError(f"unknown message kind: {kind!r}")
    return kind


def _checked_key(key: str) -> str:
    if len(key.encode()) > MAX_KEY_BYTES:
        raise ValueError(f"key longer than {MAX_KEY_BYTES} bytes: {key!r}")
    return key


def up_key(node_id: str, kind: str) -> str:
    return _checked_key(f"{_ROOT}/{_checked_node_id(node_id)}/up/{_checked_kind(kind)}")


def down_key(node_id: str, kind: str) -> str:
    return _checked_key(f"{_ROOT}/{_checked_node_id(node_id)}/down/{_checked_kind(kind)}")


def live_key(node_id: str) -> str:
    return _checked_key(f"{_LIVE}/{_checked_node_id(node_id)}")


def fusion_up_key(kind: str) -> str:
    return _checked_key(f"{PREFIX}fusion/up/{_checked_kind(kind)}")


def fusion_down_key(kind: str) -> str:
    return _checked_key(f"{PREFIX}fusion/down/{_checked_kind(kind)}")


def fusion_kind(key: str) -> tuple[str, str]:
    """Split a fusion key into ("up" | "down", kind). ValueError for any other key."""
    head = f"{PREFIX}fusion/"
    parts = key[len(head):].split("/") if key.startswith(head) else []
    if len(parts) != 2 or parts[0] not in ("up", "down") or parts[1] not in KINDS:
        raise ValueError(f"not a fusion key: {key!r}")
    return parts[0], parts[1]


def DOWN_FOR(node_id: str) -> str:
    return _checked_key(f"{_ROOT}/{_checked_node_id(node_id)}/down/**")


def parse_key(key: str) -> tuple[str, str, str]:
    """Split an up or down key into (node_id, direction, kind)."""
    if not key.startswith(f"{_ROOT}/"):
        raise ValueError(f"not a SAPIENT key: {key!r}")
    parts = key[len(_ROOT) + 1 :].split("/")
    if len(parts) != 3 or parts[1] not in ("up", "down") or not parts[2]:
        raise ValueError(f"not an up or down key: {key!r}")
    node_id, direction, kind = parts
    return _checked_node_id(node_id), direction, kind


def node_id_from_live_key(key: str) -> str:
    if not key.startswith(f"{_LIVE}/"):
        raise ValueError(f"not a liveliness key: {key!r}")
    return _checked_node_id(key[len(_LIVE) + 1 :])


def kind_of(msg: SapientMessage) -> str:
    return msg.WhichOneof("content")


def qos_for(kind: str, fused: bool = False) -> tuple[zenoh.Priority, zenoh.CongestionControl, bool]:
    """Return (priority, congestion control, express) for a message kind.

    fused marks traffic from a fusion node; only its detection reports (tracks) differ.
    """
    if fused and kind == "detection_report":
        return _FUSED_TRACK
    return _QOS[_checked_kind(kind)]
