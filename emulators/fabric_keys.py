"""Key scheme of the host's fabric, in goat's taxonomy.

Keys hold only an anchor, a site and a fixed-width node UUID, never report IDs,
task IDs, object IDs or timestamps:
    <anchor>/telemetry/sapient/<site>/v2/<kind>/<node_id>   registration, status_report,
                                                            detection_report, alert, error
    <anchor>/ack/<site>/sapient/v2/<kind>/<node_id>         registration_ack, task_ack, alert_ack
    <anchor>/task/<site>/sapient/v2/task/<node_id>          task
    <anchor>/telemetry/sapient/<site>/v2/live/<node_id>     liveliness token
<anchor> is 32 lower-case hex characters, <site> is 1 to MAX_SITE_CHARS characters of
[a-z0-9], <node_id> is a canonical UUID. The cap on the site makes every key of every kind
fit in MAX_KEY_BYTES, so a reply to a site that parsed can always be built. <kind> is the SapientMessage.content oneof field name.

Standard library only: this module also runs with the Mac's python3.
"""
import re
import uuid
from dataclasses import dataclass

TELEMETRY_KINDS = frozenset({"registration", "status_report", "detection_report", "alert", "error"})
ACK_KINDS = frozenset({"registration_ack", "task_ack", "alert_ack"})
KINDS = TELEMETRY_KINDS | ACK_KINDS | {"task"}
MAX_KEY_BYTES = 256
MAX_SITE_CHARS = 32

_ANCHOR = re.compile(r"[0-9a-f]{32}")
_SITE = re.compile(r"[a-z0-9]{1,%d}" % MAX_SITE_CHARS)


@dataclass(frozen=True)
class FabricKey:
    anchor: str
    site: str
    kind: str        # a member of KINDS, or "live"
    node_id: str


def _checked_anchor(anchor: str) -> str:
    if not isinstance(anchor, str) or not _ANCHOR.fullmatch(anchor):
        raise ValueError(f"anchor is not 32 lower-case hex characters: {anchor!r}")
    return anchor


def _checked_site(site: str) -> str:
    if not isinstance(site, str) or not _SITE.fullmatch(site):
        raise ValueError(f"site is not 1 to {MAX_SITE_CHARS} characters of [a-z0-9]: {site!r}")
    return site


def _checked_node_id(node_id: str) -> str:
    """Return node_id if it is a canonical UUID: 36 chars, hyphenated, lowercase."""
    try:
        canonical = str(uuid.UUID(node_id)) == node_id
    except (ValueError, AttributeError, TypeError):
        canonical = False
    if not canonical:
        raise ValueError(f"node_id is not a canonical UUID: {node_id!r}")
    return node_id


def _checked_kind(kind: str) -> str:
    if kind not in KINDS:
        raise ValueError(f"unknown message kind: {kind!r}")
    return kind


def _sized(key: str) -> str:
    if len(key.encode()) > MAX_KEY_BYTES:
        raise ValueError(f"key is longer than {MAX_KEY_BYTES} bytes: {key!r}")
    return key


def _assemble(anchor: str, site: str, kind: str, node_id: str) -> str:
    if kind == "live" or kind in TELEMETRY_KINDS:
        return f"{anchor}/telemetry/sapient/{site}/v2/{kind}/{node_id}"
    if kind in ACK_KINDS:
        return f"{anchor}/ack/{site}/sapient/v2/{kind}/{node_id}"
    return f"{anchor}/task/{site}/sapient/v2/task/{node_id}"


def key_for(anchor: str, site: str, kind: str, node_id: str) -> str:
    """Data key of a message kind. ValueError on any bad part, and on kind 'live'."""
    return _sized(_assemble(_checked_anchor(anchor), _checked_site(site),
                            _checked_kind(kind), _checked_node_id(node_id)))


def live_key(anchor: str, site: str, node_id: str) -> str:
    """Key of the liveliness token of a node."""
    return _sized(_assemble(_checked_anchor(anchor), _checked_site(site), "live",
                            _checked_node_id(node_id)))


def _parse_any(key: str) -> FabricKey:
    """Parse a data key or a live key, accepting only the exact shapes."""
    _sized(key)
    parts = key.split("/")
    if len(parts) != 7:
        raise ValueError(f"not a fabric key: {key!r}")
    anchor, cls = parts[0], parts[1]
    if cls == "ack":
        site, kind, node_id = parts[2], parts[5], parts[6]
        shape = (parts[3], parts[4]) == ("sapient", "v2")
        allowed = ACK_KINDS
    elif cls == "task":
        site, kind, node_id = parts[2], parts[5], parts[6]
        shape = (parts[3], parts[4], parts[5]) == ("sapient", "v2", "task")
        allowed = frozenset({"task"})
    elif cls == "telemetry":
        site, kind, node_id = parts[3], parts[5], parts[6]
        shape = (parts[2], parts[4]) == ("sapient", "v2")
        allowed = TELEMETRY_KINDS | {"live"}
    else:
        raise ValueError(f"not a fabric key: {key!r}")
    if not shape or kind not in allowed:
        raise ValueError(f"not a fabric key: {key!r}")
    return FabricKey(_checked_anchor(anchor), _checked_site(site), kind, _checked_node_id(node_id))


def parse(key: str) -> FabricKey:
    """Parse a data key. ValueError otherwise, also for a live key."""
    parsed = _parse_any(key)
    if parsed.kind == "live":
        raise ValueError(f"a live key is not a data key: {key!r}")
    return parsed


def parse_live(key: str) -> FabricKey:
    """Parse a liveliness key. ValueError otherwise."""
    parsed = _parse_any(key)
    if parsed.kind != "live":
        raise ValueError(f"not a live key: {key!r}")
    return parsed


def _wild_anchor(anchor: str) -> str:
    return anchor if anchor == "*" else _checked_anchor(anchor)


def _wild_site(site: str) -> str:
    return site if site == "*" else _checked_site(site)


def subscriptions(anchor: str = "*", site: str = "*") -> tuple[str, str, str]:
    """Subscription expressions for telemetry, acks and tasks. '*' is allowed here only."""
    a, s = _wild_anchor(anchor), _wild_site(site)
    return (
        f"{a}/telemetry/sapient/{s}/v2/*/*",
        f"{a}/ack/{s}/sapient/v2/*/*",
        f"{a}/task/{s}/sapient/v2/task/*",
    )


def live_subscription(anchor: str = "*", site: str = "*") -> str:
    return f"{_wild_anchor(anchor)}/telemetry/sapient/{_wild_site(site)}/v2/live/*"
