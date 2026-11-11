"""Slot identities and the registry file of the goat host tier.

Each router has a pool of slots. Slot k of a fabric router is an anchor, the first
32 hex characters of sha256("<salt>:<k>"). Slot k of a pod router is a node ID, a
version 4 UUID built from the first 16 bytes of the same digest. The certificate
common name of a slot is its anchor or node ID. A registry file (TOML) names each
router, its salt and pool, and gives each alias a slot.

Standard library only: this module also runs with the Mac's python3.
"""
import hashlib
import re
import tomllib
import uuid
from dataclasses import dataclass, field

_SITE = re.compile(r"[a-z0-9]+")
_KINDS = ("pod", "fabric")
_COMMON = {"kind", "salt", "pool_size", "site", "router_cn", "slots"}
_POD_ONLY = ("prefix", "fusion_cn", "fusion_node_id", "recorder_cn", "bridge_cn")


class RegistryError(ValueError):
    """The registry is malformed; the message names the table and the field."""


def _digest(salt: str, k: int) -> bytes:
    return hashlib.sha256(f"{salt}:{k}".encode()).digest()


def fabric_anchor(salt: str, k: int) -> str:
    """Anchor of slot k of a fabric router: 32 lower-case hex characters."""
    return _digest(salt, k).hex()[:32]


def pod_node_id(salt: str, k: int) -> str:
    """Node ID of slot k of a pod router: a canonical version 4 UUID."""
    return str(uuid.UUID(bytes=_digest(salt, k)[:16], version=4))


@dataclass(frozen=True)
class Router:
    name: str            # table name in the registry, e.g. "pod1", "fabric"
    kind: str            # "pod" or "fabric"
    salt: str
    pool_size: int
    site: str
    router_cn: str
    slots: dict[str, int] = field(default_factory=dict)  # alias -> slot index
    prefix: str = ""               # pod only, ends with "/"
    fusion_cn: str = ""            # pod only
    fusion_node_id: str = ""       # pod only
    recorder_cn: str = ""          # pod only
    bridge_cn: str = ""            # pod only

    def slot_id(self, k: int) -> str:
        """Anchor for a fabric router, node ID for a pod router."""
        if not isinstance(k, int) or isinstance(k, bool) or not 0 <= k < self.pool_size:
            raise RegistryError(f"[{self.name}] slot {k!r} is outside the pool of {self.pool_size}")
        return fabric_anchor(self.salt, k) if self.kind == "fabric" else pod_node_id(self.salt, k)

    def alias_id(self, alias: str) -> str:
        if alias not in self.slots:
            raise RegistryError(f"[{self.name}] unknown alias: {alias!r}")
        return self.slot_id(self.slots[alias])


def _string(name: str, table: dict, key: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise RegistryError(f"[{name}] {key} must be a non-empty string")
    return value


def _router(name: str, table: object) -> Router:
    if not isinstance(table, dict):
        raise RegistryError(f"[{name}] must be a table")
    kind = table.get("kind")
    if kind not in _KINDS:
        raise RegistryError(f"[{name}] kind must be one of {_KINDS}, got {kind!r}")
    pod = kind == "pod"
    allowed = _COMMON | set(_POD_ONLY) if pod else _COMMON
    extra = sorted(set(table) - allowed)
    if extra:
        raise RegistryError(f"[{name}] a {kind} table must not have: {', '.join(extra)}")

    salt = _string(name, table, "salt")
    router_cn = _string(name, table, "router_cn")
    site = _string(name, table, "site")
    if not _SITE.fullmatch(site):
        raise RegistryError(f"[{name}] site must match [a-z0-9]+, got {site!r}")
    pool_size = table.get("pool_size")
    if not isinstance(pool_size, int) or isinstance(pool_size, bool) or pool_size < 1:
        raise RegistryError(f"[{name}] pool_size must be a positive integer")

    pod_fields = {}
    if pod:
        for key in _POD_ONLY:
            pod_fields[key] = _string(name, table, key)
        if not pod_fields["prefix"].endswith("/"):
            raise RegistryError(f"[{name}] prefix must end with '/', got {pod_fields['prefix']!r}")
        node_id = pod_fields["fusion_node_id"]
        try:
            canonical = str(uuid.UUID(node_id)) == node_id
        except ValueError:
            canonical = False
        if not canonical:
            raise RegistryError(f"[{name}] fusion_node_id is not a canonical UUID: {node_id!r}")

    raw_slots = table.get("slots")
    if not isinstance(raw_slots, dict) or not raw_slots:
        raise RegistryError(f"[{name}] slots must be a non-empty table of alias = index")
    owner: dict[int, str] = {}
    for alias, k in raw_slots.items():
        if not isinstance(k, int) or isinstance(k, bool):
            raise RegistryError(f"[{name}.slots] {alias} must be an integer, got {k!r}")
        if not 0 <= k < pool_size:
            raise RegistryError(f"[{name}.slots] {alias} = {k} is outside the pool of {pool_size}")
        if k in owner:
            raise RegistryError(f"[{name}.slots] {alias} and {owner[k]} share slot {k}")
        owner[k] = alias

    return Router(name=name, kind=kind, salt=salt, pool_size=pool_size, site=site,
                  router_cn=router_cn, slots=dict(raw_slots), **pod_fields)


def parse_registry(text: str) -> dict[str, Router]:
    """Parse TOML registry text into routers keyed by table name."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise RegistryError(f"registry is not valid TOML: {exc}") from exc
    routers = {name: _router(name, table) for name, table in data.items()}
    salts: dict[str, str] = {}
    for name, router in routers.items():
        if router.salt in salts:
            raise RegistryError(f"[{name}] salt repeats the salt of [{salts[router.salt]}]; salts must differ")
        salts[router.salt] = name
    return routers


def load_registry(path) -> dict[str, Router]:
    with open(path, "rb") as handle:
        return parse_registry(handle.read().decode())
