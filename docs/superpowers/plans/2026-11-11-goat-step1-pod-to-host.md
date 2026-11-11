# Goat Step 1: Pod 1 to Host Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the stage 4 pod on a fabric that follows goat's rules: a pod bridge, a fabric router with a slot pool, a host fusion node and recorder, and a slot pool in the pod router, with eleven acceptance checks (G1-01 to G1-11).

**Architecture:** One registry file describes both routers; a stdlib-only generator makes both access lists (in the text form goat's `acl-evaluate.py` parses), the certificates and an env file. The pod bridge is one process with two Zenoh client sessions that forwards payload bytes unchanged and maps keys in each direction. The host fusion node is the existing `fake_fusion_node.py` with a new link class for the fabric keys; the fusion node asks its link for key functions, so it does not know which key scheme is in use.

**Tech Stack:** Python 3.11 in the `apex-sapient:4.2.0` image, asyncio, `eclipse-zenoh==1.10.2`, pod router `eclipse/zenoh:1.10.2`, fabric router `eclipse/zenoh:1.9.0`, protobuf `sapient_msg.bsi_flex_335_v2_0`, Docker Compose on Colima, pytest, `openssl`, host `python3` 3.11 or newer for the generator.

**Spec:** `docs/superpowers/specs/2026-11-11-goat-step1-pod-to-host-design.md`. It cites `docs/goat-context.md`. Executors read both.

## Global Constraints

- Work on branch `goat`. Commit after each task. Never push. Each commit message ends with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.
- These files must not change: `docker-compose.yml`, `docker-compose.emulators.yml`, `docker-compose.elastic.yml`, `docker-compose.zenoh.yml`, `docker-compose.zenoh-sensors.yml`, `docker-compose.native.yml`, `docker-compose.native-sensors.yml`, `docker-compose.pod1.yml`, `zenoh/router-plain.json5`, `zenoh/router-pod1.json5`, `zenoh/pki/make_certs.sh`.
- The payload is the serialised `SapientMessage`. The pod bridge forwards the bytes unchanged in both directions.
- Images: fabric router `${FABRIC_ZENOH_IMAGE:-eclipse/zenoh:1.9.0}`, pod router `eclipse/zenoh:1.10.2`, everything else `apex-sapient:4.2.0`. Task 1 may change the default of `FABRIC_ZENOH_IMAGE`, by its own rule only.
- A key never holds a report ID, a task ID, an object ID or a timestamp (Zenoh issue 2825).
- Fabric keys, exact:
  - `<anchor>/telemetry/sapient/<site>/v2/<kind>/<node_id>` for `registration`, `status_report`, `detection_report`, `alert`, `error`
  - `<anchor>/ack/<site>/sapient/v2/<kind>/<node_id>` for `registration_ack`, `task_ack`, `alert_ack`
  - `<anchor>/task/<site>/sapient/v2/task/<node_id>` for `task`
  - `<anchor>/telemetry/sapient/<site>/v2/live/<node_id>` for the liveliness token
- `<anchor>` is 32 lower-case hexadecimal characters. `<site>` matches `[a-z0-9]+`. `<node_id>` is a canonical UUID. Pod 1's site is `p1`, the host's is `h1`.
- Fabric slot `k`: anchor = `sha256(f"{salt}:{k}").hexdigest()[:32]`. Pod slot `k`: node ID = `str(uuid.UUID(bytes=sha256(f"{salt}:{k}").digest()[:16], version=4))`. The certificate common name is the anchor or the node ID.
- Access list text: blocks in the order `rules`, `subjects`, `policies`; each rule and subject starts with `id: "<id>",` and ends with `},`; each policy is `{ rules: [...], subjects: [...] },`; comments only on their own lines.
- `emulators/slots.py`, `emulators/fabric_keys.py` and `emulators/goatgen.py` import only the standard library, because they also run with the Mac's `python3`.
- Unit tests run in the emulator image, from the repo root:
  `docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -p no:cacheprovider -q -W error tests`
  The image is built with `docker compose -f docker-compose.yml build`.
- All tests need Docker (Colima). If Docker is not running, stop and report. Do not work around it.
- A check that could not run is recorded as unknown, never as a pass. Each line of `docs/acceptance-goat1.md` says what was measured and where it falls short.
- No goat software is installed. One goat file is copied in: `acl-evaluate.py`.

## Review Focus

1. Two tracks from one pod fusion node less than 80 ms apart: the host must accept both, not answer with an Error. Test in Task 6.
2. A malformed fabric key (upper-case anchor, site with a slash, node ID that is not a UUID, unknown kind) at the bridge or the host: the sample is dropped and counted or logged, and the receive loop continues. Tests in Tasks 3, 5 and 6.
3. A registry edit that puts two aliases on one slot, or a slot index outside the pool: the generator refuses with a message that names the alias, and writes no file. Test in Task 2.
4. The host fusion node restarts while the pod runs: it finds the pod from its liveliness token and asks it to register. Test in Task 6, live check in Task 9.
5. The pod bridge starts before a router is reachable: it retries both sessions and does not exit. Test in Task 5.

---

## File structure

```
Apex-SAPIENT-Docker/
├─ goat1/registry.toml                     new   the one registry for both routers
├─ docker-compose.pairing.yml              new   Task 1 probe rig
├─ docker-compose.goat1.yml                new   the step 1 rig
├─ zenoh/router-pairing.json5              new   minimal mutual TLS router for the probe
├─ zenoh/goat1/                            generated, git-ignored: router files, pki/, goat1.env, bin/
├─ emulators/
│  ├─ slots.py                             new   slot maths and registry loader (stdlib)
│  ├─ fabric_keys.py                       new   fabric key scheme (stdlib)
│  ├─ goatgen.py                           new   generator: access lists, certificates, env file (stdlib)
│  ├─ probe_pairing.py                     new   G1-01 probe
│  ├─ pod_bridge.py                        new   the pod bridge
│  ├─ fabric_link.py                       new   FabricFusionLink
│  ├─ zenoh_io.py                          change publish_raw, TLS from a named env prefix
│  ├─ zenoh_keys.py                        change FUSION_UP_ALL, FUSION_DOWN_ALL
│  ├─ sapient_link.py                      change ZenohFusionLink: key functions, messages from above
│  ├─ fake_fusion_node.py                  change link key functions, child rule, fabric transport, parent tasks
│  ├─ recorder.py                          change fabric key mode
│  ├─ third_party/goat/acl-evaluate.py     copied from goatcore, unchanged
│  ├─ third_party/goat/NOTICE.md           new
│  └─ tests/                               new test files named in each task; golden/ for the access lists
├─ docs/acceptance-goat1.md                new
├─ NOTICE, .gitignore, README.md           change
```

---

### Task 1: Version pairing probe (G1-01)

**Files:**
- Create: `zenoh/router-pairing.json5`, `docker-compose.pairing.yml`, `emulators/probe_pairing.py`, `docs/acceptance-goat1.md`

**Interfaces:**
- Consumes: `zenoh_io.open_session`, `ZenohSession` (existing); the stage 4 certificates from `zenoh/pki/make_certs.sh zenoh/pki/out`.
- Produces: the value of `FABRIC_ZENOH_IMAGE` that later tasks use as the default in `docker-compose.goat1.yml`.

- [ ] **Step 1: Prepare.** Run `docker compose -f docker-compose.yml build` and `zenoh/pki/make_certs.sh zenoh/pki/out`. Run `docker pull eclipse/zenoh:1.9.0`. Expected: the pull succeeds for the VM's architecture.

- [ ] **Step 2: Write `zenoh/router-pairing.json5`.** `mode: "router"`, `listen.endpoints: ["tls/0.0.0.0:7447"]`, multicast and gossip scouting off, `transport.link.tls` with `root_ca_certificate: "/certs/ca.pem"`, `listen_certificate: "/certs/router.p1.h1.pem"`, `listen_private_key: "/certs/router.p1.h1.key"`, `enable_mtls: true`. No access control.

- [ ] **Step 3: Write `docker-compose.pairing.yml`.** Project name `apex-pairing`. Service `zenohd`: image `${FABRIC_ZENOH_IMAGE:-eclipse/zenoh:1.9.0}`, command `["-c", "/config/router.json5"]`, the config and the three certificate files mounted read-only, network alias `router.p1.h1`. Service `probe`: image `apex-sapient:4.2.0`, `working_dir: /emulators`, `./emulators:/emulators:ro`, command `python probe_pairing.py`, environment `ZENOH_CONNECT: tls/router.p1.h1:7447`, `ZENOH_TLS_CA: /certs/ca.pem`, `ZENOH_TLS_CERT: /certs/radar.p1.h1.pem`, `ZENOH_TLS_KEY: /certs/radar.p1.h1.key`, `PROBE_WAIT_RESTART: ${PROBE_WAIT_RESTART:-0}`, with those three files mounted.

- [ ] **Step 4: Write `emulators/probe_pairing.py`.** It opens one session with `open_session`, then:
  1. subscribes to `probe/**`, publishes the `sensor` `StatusReport` template on `probe/a`, and must receive the same bytes within 5 s;
  2. declares the token `probe/live/x`, and `alive("probe/live/*")` must return it within 5 s;
  3. prints `PAIRING OK put-sub liveliness`;
  4. if `PROBE_WAIT_RESTART` is `1`: waits up to 90 s for `transport_changes` to give `False` then `True`, repeats checks 1 and 2 with no new subscribe or declare call, and prints `PAIRING OK after router restart`.
  On a timeout it prints `PAIRING FAILED: <which check>` and exits with code 1.

- [ ] **Step 5: Run the probe.**

```bash
dcp() { docker compose -f docker-compose.pairing.yml "$@"; }
dcp up -d zenohd && sleep 3
dcp run --rm probe
# expected last line: PAIRING OK put-sub liveliness
PROBE_WAIT_RESTART=1 dcp run --rm -d --name pairing-probe probe
sleep 5 && dcp restart zenohd && sleep 20
docker logs pairing-probe | tail -2
# expected: PAIRING OK put-sub liveliness / PAIRING OK after router restart
docker rm -f pairing-probe; dcp down
```

- [ ] **Step 6: Apply the decision rule.** If both lines print with the 1.9.0 image, G1-01 passes and the default stays `eclipse/zenoh:1.9.0`. If the pull fails or a line is missing: save the output, run Step 5 again with `FABRIC_ZENOH_IMAGE=eclipse/zenoh:1.10.2`, and from now on use `eclipse/zenoh:1.10.2` as the default of `FABRIC_ZENOH_IMAGE`. Report this in the task report, because later tasks depend on it.

- [ ] **Step 7: Start `docs/acceptance-goat1.md`.** Give it the header and style of `docs/acceptance.md`: what the file covers, the commit, and one line for G1-01 with the commands' printed lines. If the fallback was used, add the saved failure output and an open item for step 4.

- [ ] **Step 8: Commit.** `git add zenoh/router-pairing.json5 docker-compose.pairing.yml emulators/probe_pairing.py docs/acceptance-goat1.md && git commit -m "test: version pairing probe for the 1.10.2 binding and the fabric router image (G1-01)"`

---

### Task 2: Slot maths and registry

**Files:**
- Create: `emulators/slots.py`, `emulators/tests/test_slots.py`

**Interfaces:**
- Produces:

```python
class RegistryError(ValueError): ...

def fabric_anchor(salt: str, k: int) -> str
def pod_node_id(salt: str, k: int) -> str

@dataclass(frozen=True)
class Router:
    name: str            # table name in the registry, e.g. "pod1", "fabric"
    kind: str            # "pod" or "fabric"
    salt: str
    pool_size: int
    site: str
    router_cn: str
    slots: dict[str, int]          # alias -> slot index
    prefix: str = ""               # pod only, ends with "/"
    fusion_cn: str = ""            # pod only
    fusion_node_id: str = ""       # pod only
    recorder_cn: str = ""          # pod only
    bridge_cn: str = ""            # pod only
    def slot_id(self, k: int) -> str       # anchor for a fabric router, node ID for a pod router
    def alias_id(self, alias: str) -> str  # slot_id of the alias; RegistryError if unknown

def parse_registry(text: str) -> dict[str, Router]      # TOML text
def load_registry(path) -> dict[str, Router]
```

- [ ] **Step 1: Write the failing tests** in `emulators/tests/test_slots.py`:

```python
REGISTRY = '''
[pod1]
kind = "pod"
salt = "goat1-pod1"
pool_size = 8
site = "p1"
prefix = "h1/p1/"
router_cn = "router.p1.h1"
fusion_cn = "fusion.p1.h1"
fusion_node_id = "f0000001-0000-4000-8000-000000000001"
recorder_cn = "recorder.p1.h1"
bridge_cn = "podbridge.p1.h1"
[pod1.slots]
radar = 0
camera = 1
vehicle = 2

[fabric]
kind = "fabric"
salt = "goat1-fabric"
pool_size = 8
site = "h1"
router_cn = "router.fabric.h1"
[fabric.slots]
pod1 = 0
host-fusion = 1
host-recorder = 2
goat-cli = 3
'''

def test_fabric_anchor_is_goats_formula():
    assert fabric_anchor("goat1-fabric", 0) == "18214b1a34e3c722d1cac283b272a62c"
    assert fabric_anchor("goat1-fabric", 1) == "b005ae3a8f2baf89160bd71632902672"

def test_pod_node_id_is_a_canonical_version_4_uuid():
    assert pod_node_id("goat1-pod1", 0) == "1aef1b86-9b67-47a8-b565-2e40f235d2ba"
    assert pod_node_id("goat1-pod1", 2) == "341b9172-dc37-467a-add2-3ac5625e8682"
    assert uuid.UUID(pod_node_id("goat1-pod1", 5)).version == 4

def test_registry_resolves_aliases():
    routers = parse_registry(REGISTRY)
    assert routers["fabric"].alias_id("host-fusion") == "b005ae3a8f2baf89160bd71632902672"
    assert routers["pod1"].alias_id("camera") == "86ca6000-1c36-4aed-875f-ac18ec0b5ab2"
    assert routers["pod1"].slot_id(3) == "83ff6077-6265-4c97-9085-efcdbc04ebc0"

@pytest.mark.parametrize("old, new, names", [
    ("camera = 1", "camera = 0", "camera"),             # two aliases on one slot
    ("vehicle = 2", "vehicle = 8", "vehicle"),          # outside the pool
    ('site = "p1"', 'site = "P/1"', "site"),            # not [a-z0-9]+
    ('prefix = "h1/p1/"', 'prefix = "h1/p1"', "prefix"),  # must end with "/"
    ('salt = "goat1-fabric"', 'salt = "goat1-pod1"', "salt"),  # salts must differ
    ('kind = "fabric"', 'kind = "broker"', "kind"),
])
def test_registry_refuses_and_names_the_problem(old, new, names):
    with pytest.raises(RegistryError, match=names):
        parse_registry(REGISTRY.replace(old, new))

def test_registry_refuses_a_non_uuid_fusion_node_id():
    with pytest.raises(RegistryError, match="fusion_node_id"):
        parse_registry(REGISTRY.replace("f0000001-0000-4000-8000-000000000001", "not-a-uuid"))
```

- [ ] **Step 2: Run them.** Expected: FAIL, `No module named 'slots'`.
- [ ] **Step 3: Implement `emulators/slots.py`** with `tomllib`, `hashlib`, `uuid`, `dataclasses`, `re`. A pod table requires `prefix`, `fusion_cn`, `fusion_node_id`, `recorder_cn`, `bridge_cn`; a fabric table must not have them.
- [ ] **Step 4: Run the tests.** Expected: PASS, and the whole suite still passes.
- [ ] **Step 5: Commit.** `git commit -m "feat: slot maths and the registry loader"`

---

### Task 3: Fabric key scheme

**Files:**
- Create: `emulators/fabric_keys.py`, `emulators/tests/test_fabric_keys.py`

**Interfaces:**
- Produces:

```python
TELEMETRY_KINDS = frozenset({"registration", "status_report", "detection_report", "alert", "error"})
ACK_KINDS = frozenset({"registration_ack", "task_ack", "alert_ack"})
KINDS = TELEMETRY_KINDS | ACK_KINDS | {"task"}
MAX_KEY_BYTES = 256

@dataclass(frozen=True)
class FabricKey:
    anchor: str
    site: str
    kind: str        # a member of KINDS, or "live"
    node_id: str

def key_for(anchor: str, site: str, kind: str, node_id: str) -> str   # ValueError on any bad part
def live_key(anchor: str, site: str, node_id: str) -> str
def parse(key: str) -> FabricKey          # data keys only; ValueError otherwise, also for a live key
def parse_live(key: str) -> FabricKey     # kind == "live"; ValueError otherwise
def subscriptions(anchor: str = "*", site: str = "*") -> tuple[str, str, str]   # telemetry, ack, task
def live_subscription(anchor: str = "*", site: str = "*") -> str
```

- [ ] **Step 1: Write the failing tests:**

```python
A = "18214b1a34e3c722d1cac283b272a62c"
N = "f0000001-0000-4000-8000-000000000001"

def test_each_class_has_its_exact_shape():
    assert key_for(A, "p1", "detection_report", N) == f"{A}/telemetry/sapient/p1/v2/detection_report/{N}"
    assert key_for(A, "p1", "task_ack", N) == f"{A}/ack/p1/sapient/v2/task_ack/{N}"
    assert key_for(A, "p1", "task", N) == f"{A}/task/p1/sapient/v2/task/{N}"
    assert live_key(A, "p1", N) == f"{A}/telemetry/sapient/p1/v2/live/{N}"

@pytest.mark.parametrize("kind", sorted(KINDS))
def test_parse_reverses_key_for(kind):
    assert parse(key_for(A, "p1", kind, N)) == FabricKey(A, "p1", kind, N)

def test_parse_live():
    assert parse_live(live_key(A, "p1", N)) == FabricKey(A, "p1", "live", N)

@pytest.mark.parametrize("key", [
    f"{A.upper()}/telemetry/sapient/p1/v2/alert/{N}",      # upper-case anchor
    f"{A[:-1]}/telemetry/sapient/p1/v2/alert/{N}",         # short anchor
    f"{A}/telemetry/sapient/P1/v2/alert/{N}",              # bad site
    f"{A}/telemetry/sapient/p1/v1/alert/{N}",              # wrong version
    f"{A}/telemetry/sapient/p1/v2/task/{N}",               # task in the telemetry class
    f"{A}/ack/p1/sapient/v2/alert/{N}",                    # alert in the ack class
    f"{A}/telemetry/sapient/p1/v2/alert/{N.upper()}",      # node ID not canonical
    f"{A}/telemetry/sapient/p1/v2/alert/{N}/extra",
    f"{A}/telemetry/sapient/p1/v2/live/{N}",               # a live key is not a data key
    "h1/p1/sapient/v2/x/up/alert",
])
def test_parse_refuses(key):
    with pytest.raises(ValueError):
        parse(key)

def test_key_for_refuses_bad_parts():
    for bad in [("zz", "p1", "alert", N), (A, "p/1", "alert", N), (A, "p1", "live", N), (A, "p1", "alert", "x")]:
        with pytest.raises(ValueError):
            key_for(*bad)

def test_subscriptions_have_the_wildcard_in_the_first_part_only():
    assert subscriptions() == ("*/telemetry/sapient/*/v2/*/*", "*/ack/*/sapient/v2/*/*", "*/task/*/sapient/v2/task/*")
    assert subscriptions(A, "p1") == (f"{A}/telemetry/sapient/p1/v2/*/*", f"{A}/ack/p1/sapient/v2/*/*", f"{A}/task/p1/sapient/v2/task/*")
    assert live_subscription() == "*/telemetry/sapient/*/v2/live/*"
```

- [ ] **Step 2: Run them.** Expected: FAIL, `No module named 'fabric_keys'`.
- [ ] **Step 3: Implement `emulators/fabric_keys.py`**, standard library only. `"*"` is accepted for anchor and site only by `subscriptions` and `live_subscription`.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat: fabric key scheme in goat's taxonomy"`

---

### Task 4: Generator: access lists, checker, certificates, env file

**Files:**
- Create: `emulators/goatgen.py`, `emulators/third_party/goat/acl-evaluate.py` (copied unchanged from `../usareur-af/goatcore/ops/ansible/roles/goat-zenoh/files/acl-evaluate.py` at commit `cbf2cb7f`), `emulators/third_party/goat/NOTICE.md`, `emulators/tests/test_goatgen.py`, `emulators/tests/golden/router-fabric.json5`, `emulators/tests/golden/router-pod1.json5`, `goat1/registry.toml`
- Modify: `NOTICE` (one line for the copied file), `.gitignore` (add `zenoh/goat1/`)

**Interfaces:**
- Consumes: `slots.Router`, `slots.load_registry`, `slots.parse_registry` (Task 2).
- Produces:

```python
def render_fabric_router(router: Router) -> str     # the whole JSON5 file
def render_pod_router(router: Router) -> str
def env_lines(routers: dict[str, Router]) -> list[str]
def main(argv: list[str] | None = None) -> int      # goatgen.py <registry.toml> <out_dir> [--frozen-routers]
```

  Output tree of `main`: `<out>/router-<name>.json5` for each router; `<out>/pki/<name>/ca.pem`, `ca.key`, `router.pem`, `router.key`; for a pod also `fusion`, `recorder`, `bridge`; one `<alias>.pem` and `<alias>.key` for each alias; `<out>/goat1.env`.
  Env names: `<ROUTER>_<ALIAS>_ID` in upper case with `-` as `_`, for example `POD1_RADAR_ID`, `FABRIC_POD1_ID`, `FABRIC_HOST_FUSION_ID`; plus `POD1_FUSION_NODE_ID`.
  Exit codes: 0 done; 2 usage or registry error (nothing written); 3 with `--frozen-routers` when an existing router file would change (nothing written, the changed file is named). On success with `--frozen-routers` it prints `router files unchanged`.

- [ ] **Step 1: Copy the checker and write the notices.** `NOTICE.md` names the source repository, path, commit `cbf2cb7f` and licence (public domain in the United States, Apache-2.0 elsewhere). Run `python3 emulators/third_party/goat/acl-evaluate.py --self-test`. Expected: exit code 0.

- [ ] **Step 2: Write the failing tests** in `emulators/tests/test_goatgen.py`. Load the checker with `importlib.util.spec_from_file_location`. Use the registry text of Task 2 (import `REGISTRY` from `test_slots`).

```python
FA, HA = "18214b1a34e3c722d1cac283b272a62c", "b005ae3a8f2baf89160bd71632902672"   # pod1 and host-fusion anchors
FREE = fabric_anchor("goat1-fabric", 7)                                            # a slot nobody holds
RADAR, CAMERA = "1aef1b86-9b67-47a8-b565-2e40f235d2ba", "86ca6000-1c36-4aed-875f-ac18ec0b5ab2"
FUSION = "f0000001-0000-4000-8000-000000000001"

def test_checker_self_test_passes():          # subprocess, exit code 0

def test_fabric_list_decisions(fabric_acl):   # fabric_acl = checker Acl of render_fabric_router
    d = fabric_acl.decide_cn
    assert fabric_acl.unusable_key_exprs() == []
    assert d(FA, "put", "ingress", f"{FA}/telemetry/sapient/p1/v2/detection_report/{FUSION}") == "allow"
    assert d(FA, "liveliness_token", "ingress", f"{FA}/telemetry/sapient/p1/v2/live/{FUSION}") == "allow"
    assert d(FA, "put", "ingress", f"{HA}/task/p1/sapient/v2/task/{FUSION}") == "deny"
    assert d(HA, "put", "ingress", f"{HA}/task/p1/sapient/v2/task/{FUSION}") == "allow"
    assert d(HA, "put", "ingress", f"{FA}/telemetry/sapient/p1/v2/alert/{FUSION}") == "deny"
    assert d(FREE, "put", "ingress", f"{FREE}/telemetry/sapient/p2/v2/alert/{FUSION}") == "allow"
    assert d(HA, "declare_subscriber", "ingress", "*/telemetry/sapient/*/v2/*/*") == "allow"
    assert d(HA, "declare_subscriber", "ingress", "**") == "deny"
    assert d(HA, "declare_liveliness_subscriber", "ingress", "*/telemetry/sapient/*/v2/live/*") == "allow"
    assert d(HA, "put", "egress", f"{FA}/telemetry/sapient/p1/v2/alert/{FUSION}") == "allow"
    assert d("no-such-cn", "put", "ingress", f"{FA}/x") == "deny"

def test_pod_list_decisions(pod_acl):
    d = pod_acl.decide_cn
    assert pod_acl.unusable_key_exprs() == []
    assert d(RADAR, "put", "ingress", f"h1/p1/sapient/v2/{RADAR}/up/detection_report") == "allow"
    assert d(RADAR, "liveliness_token", "ingress", f"h1/p1/sapient/v2/live/{RADAR}") == "allow"
    assert d(RADAR, "put", "ingress", f"h1/p1/sapient/v2/{CAMERA}/up/detection_report") == "deny"
    assert d(RADAR, "declare_subscriber", "ingress", f"h1/p1/sapient/v2/{RADAR}/down/**") == "allow"
    assert d(RADAR, "declare_subscriber", "ingress", f"h1/p1/sapient/v2/{CAMERA}/down/**") == "deny"
    assert d(pod_node_id("goat1-pod1", 7), "put", "ingress", f"h1/p1/sapient/v2/{pod_node_id('goat1-pod1', 7)}/up/status_report") == "allow"
    assert d("fusion.p1.h1", "put", "ingress", f"h1/p1/sapient/v2/{RADAR}/down/task") == "allow"
    assert d("fusion.p1.h1", "put", "ingress", "h1/p1/fusion/up/registration") == "allow"
    assert d("fusion.p1.h1", "put", "ingress", "h1/p1/fusion/down/task") == "deny"
    assert d("fusion.p1.h1", "declare_subscriber", "ingress", "h1/p1/fusion/down/**") == "allow"
    assert d("podbridge.p1.h1", "declare_subscriber", "ingress", "h1/p1/fusion/up/**") == "allow"
    assert d("podbridge.p1.h1", "put", "ingress", "h1/p1/fusion/down/task") == "allow"
    assert d("podbridge.p1.h1", "put", "ingress", "h1/p1/fusion/up/registration") == "deny"
    assert d("podbridge.p1.h1", "declare_subscriber", "ingress", "h1/p1/sapient/v2/**") == "deny"
    assert d("recorder.p1.h1", "declare_subscriber", "ingress", "h1/p1/sapient/v2/**") == "allow"
    assert d("recorder.p1.h1", "put", "ingress", f"h1/p1/sapient/v2/{RADAR}/up/alert") == "deny"

def test_rendered_lists_match_the_golden_files():       # exact text, both routers
def test_env_lines():
    assert "POD1_RADAR_ID=1aef1b86-9b67-47a8-b565-2e40f235d2ba" in lines
    assert "FABRIC_HOST_FUSION_ID=b005ae3a8f2baf89160bd71632902672" in lines
    assert "POD1_FUSION_NODE_ID=f0000001-0000-4000-8000-000000000001" in lines

# The next tests call main() with tmp_path and are skipped when shutil.which("openssl") is None.
def test_main_writes_router_files_env_and_verifiable_certificates(tmp_path):
    # exit 0; `openssl verify -CAfile pki/pod1/ca.pem pki/pod1/radar.pem` succeeds;
    # the subject common name of pki/pod1/radar.pem is RADAR, of pki/fabric/pod1.pem is FA,
    # of pki/fabric/router.pem is "router.fabric.h1" with that name as a DNS subject alternative name
def test_second_run_keeps_every_certificate(tmp_path):          # file bytes unchanged
def test_new_alias_gets_only_its_certificate_and_routers_stay_frozen(tmp_path, capsys):
    # add `radar2 = 3` to [pod1.slots]; main(..., "--frozen-routers") == 0; prints "router files unchanged";
    # pki/pod1/radar2.pem exists; radar.pem bytes unchanged; both router files bytes unchanged
def test_frozen_routers_refuses_a_pool_change(tmp_path, capsys):
    # change pool_size to 9; main(..., "--frozen-routers") == 3; output names router-pod1.json5; no file changed
def test_registry_error_writes_nothing(tmp_path):               # exit 2, out dir empty
```

- [ ] **Step 3: Run them.** Expected: FAIL, `No module named 'goatgen'`.

- [ ] **Step 4: Implement the render functions.** Both files have `mode: "router"`, `listen.endpoints: ["tls/0.0.0.0:7447"]`, multicast and gossip scouting off, `transport.link.tls` with `/certs/ca.pem`, `/certs/router.pem`, `/certs/router.key` and `enable_mtls: true`, and `access_control` with `enabled: true`, `default_permission: "deny"`. The pod file also has, as in `zenoh/router-pod1.json5`: the read-only adminspace, `transport.link.tx.lease: 5000` and `close_link_on_expiration: true`.

  Fabric rules, in this order. `P` is each slot's anchor.

  | id | messages | flows | key_exprs | subjects |
  |---|---|---|---|---|
  | `peer-r-scoped` | `declare_subscriber`, `query`, `declare_queryable`, `reply`, `declare_liveliness_subscriber`, `liveliness_query` | `egress`, `ingress` | `*/**`, `**/@adv/**` | `mtls-peer` |
  | `peer-deliver-scoped` | `put`, `delete`, `liveliness_token` | `egress` | `*/**`, `**/@adv/**` | `mtls-peer` |
  | `slot-w-<P>` for each slot | `put`, `delete`, `liveliness_token` | `ingress` | `<P>/**`, `volatile/<P>/**`, `<P>/**/@adv/**` | `slot-<P>` |

  Fabric subjects: `{ id: "mtls-peer", link_protocols: ["tls"], },` and `{ id: "slot-<P>", cert_common_names: ["<P>"], },` for each slot.

  Pod rules. `X` is the prefix, `F` the fusion node ID, `N` each slot's node ID.

  | id | messages | flows | key_exprs | subjects |
  |---|---|---|---|---|
  | `fusion-down` | `put` | `ingress` | `<X>sapient/v2/*/down/**`, `<X>fusion/up/**` | `fusion` |
  | `fusion-own-up` | `put`, `liveliness_token` | `ingress` | `<X>sapient/v2/<F>/up/**`, `<X>sapient/v2/live/<F>` | `fusion` |
  | `read-all` | `declare_subscriber`, `query`, `liveliness_query`, `declare_liveliness_subscriber` | `ingress` | `<X>**` | `fusion`, `recorder` |
  | `bridge-r` | `declare_subscriber` | `ingress` | `<X>fusion/up/**` | `bridge` |
  | `bridge-w` | `put` | `ingress` | `<X>fusion/down/**` | `bridge` |
  | `slot-w-<N>` for each slot | `put`, `liveliness_token` | `ingress` | `<X>sapient/v2/<N>/up/**`, `<X>sapient/v2/live/<N>` | `slot-<N>` |
  | `slot-r-<N>` for each slot | `declare_subscriber` | `ingress` | `<X>sapient/v2/<N>/down/**` | `slot-<N>` |
  | `egress-all` | the nine messages of the `egress-all` rule in `zenoh/router-pod1.json5` | `egress` | `<X>**` | every subject |

  Pod subjects: `fusion`, `recorder`, `bridge` with their common names from the registry, and `slot-<N>` with common name `<N>`.

- [ ] **Step 5: Implement `env_lines` and `main`.** Certificates: RSA 2048, SHA-256, 825 days for a leaf and 3650 days for a CA, extended key usage `serverAuth, clientAuth`, subject alternative name `DNS:<common name>`, made with `openssl` through `subprocess`. A file that exists and verifies against its CA is kept. `main` renders and checks everything in memory before it writes.

- [ ] **Step 6: Make the golden files** from the Task 2 registry text, read them against the two tables, and commit them. Run the tests. Expected: PASS.

- [ ] **Step 7: Write `goat1/registry.toml`** with the content of the `REGISTRY` text in Task 2 and one comment line above each table that says what it is. Run on the Mac: `python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1`. Expected: exit code 0 and the output tree above.

- [ ] **Step 8: Start each router with its generated file.**

```bash
for pair in "eclipse/zenoh:1.10.2 pod1" "${FABRIC_ZENOH_IMAGE:-eclipse/zenoh:1.9.0} fabric"; do
  set -- $pair
  docker run -d --name gen-check -v "$PWD/zenoh/goat1/router-$2.json5:/config/router.json5:ro" \
    -v "$PWD/zenoh/goat1/pki/$2/ca.pem:/certs/ca.pem:ro" -v "$PWD/zenoh/goat1/pki/$2/router.pem:/certs/router.pem:ro" \
    -v "$PWD/zenoh/goat1/pki/$2/router.key:/certs/router.key:ro" "$1" -c /config/router.json5
  sleep 4; docker inspect -f '{{.State.Running}}' gen-check; docker logs gen-check 2>&1 | grep -ci -E 'error|panic'; docker rm -f gen-check
done
# expected for each router: true, then 0
```

  If a router refuses a message name or a field, change the render function and the golden file, and say so in the task report.

- [ ] **Step 9: Commit.** `git commit -m "feat: generator for both access lists, certificates and the env file, checked with goat's acl-evaluate"`

---

### Task 5: Pod bridge

**Files:**
- Create: `emulators/pod_bridge.py`, `emulators/tests/test_pod_bridge.py`
- Modify: `emulators/zenoh_io.py`, `emulators/zenoh_keys.py`, `emulators/tests/conftest.py`, `emulators/tests/test_zenoh_io.py`, `emulators/tests/test_zenoh_keys.py`

**Interfaces:**
- Consumes: `fabric_keys` (Task 3).
- Produces, in `zenoh_io.py`:

```python
def tls_from_env(prefix: str = "ZENOH") -> TlsOptions | None      # reads <prefix>_TLS_CA, _CERT, _KEY
async def open_session(connect, loop, log, tls_env_prefix: str = "ZENOH") -> ZenohSession
class ZenohSession:
    async def publish_raw(self, key: str, payload: bytes, kind: str, fused: bool = False) -> None
    # publish(key, msg, fused) keeps its behaviour and calls publish_raw
```

  In `zenoh_keys.py`: `FUSION_UP_ALL = f"{PREFIX}fusion/up/**"`, `FUSION_DOWN_ALL = f"{PREFIX}fusion/down/**"`, and `fusion_kind(key: str) -> tuple[str, str]` that returns `("up" | "down", kind)` for a fusion key and raises `ValueError` otherwise.
  `FakeZenohSession` in `conftest.py` gets `publish_raw` with the same recording as `publish`.

- Produces, in `pod_bridge.py`:

```python
MAX_TASK_AGE_SECONDS = 5.0
PRESENCE_SECONDS = 30.0
QUEUE_LIMIT = 512
UP_KINDS = frozenset({"registration", "status_report", "detection_report", "alert", "error", "task_ack"})
DOWN_KINDS = frozenset({"registration_ack", "task", "alert_ack", "error"})

class PodBridge:
    def __init__(self, pod, fabric, *, anchor: str, site: str, host_anchors: list[str], log, clock=time.time): ...
    forwarded: collections.Counter      # keys "up" and "down"
    dropped: collections.Counter        # keys: "undecodable", "bad_key", "bad_kind", "wrong_destination",
                                        # "unknown_destination", "stale_task", "other_side_down", "queue_full"
    async def forward_up(self, key: str, payload: bytes) -> None      # one sample from the pod
    async def forward_down(self, key: str, payload: bytes) -> None    # one sample from the fabric
    def expire_presence(self) -> None
    def on_transport(self, side: str, up: bool) -> None               # side is "pod" or "fabric"
    async def run(self) -> None                                       # the pumps and timers, until cancelled

async def main_async() -> None    # env: POD_CONNECT, POD_TLS_*, FABRIC_CONNECT, FABRIC_TLS_*, FABRIC_ANCHOR,
                                  # FABRIC_SITE, FABRIC_HOST_ANCHORS (comma list), ZENOH_KEY_PREFIX
```

- [ ] **Step 1: Write the failing tests for the session helpers** (`test_zenoh_io.py`, `test_zenoh_keys.py`): `publish_raw` puts the given bytes with the priority, congestion control and express flag of `qos_for(kind, fused)`; `tls_from_env("FABRIC")` reads `FABRIC_TLS_CA`, `FABRIC_TLS_CERT`, `FABRIC_TLS_KEY` and ignores the `ZENOH_TLS_*` names; `open_session(..., tls_env_prefix="POD")` passes those options; `fusion_kind("h1/p1/fusion/up/alert") == ("up", "alert")` with `ZENOH_KEY_PREFIX=h1/p1/`, and it raises for `h1/p1/fusion/up/nokind` and for a sensor key.

- [ ] **Step 2: Write the failing bridge tests** in `test_pod_bridge.py`, with two `FakeZenohSession` objects, `ANCHOR = "18214b1a34e3c722d1cac283b272a62c"`, `HOST = "b005ae3a8f2baf89160bd71632902672"`, `FUSION = "f0000001-0000-4000-8000-000000000001"`, site `p1`, and a clock the test controls. Use the `sensor` and `fusion_node` templates stamped with `stamp`.

```python
async def test_up_forwards_the_same_bytes_on_the_fabric_key():
    # a detection_report from FUSION on fusion_up_key("detection_report")
    # -> fabric.published == [(f"{ANCHOR}/telemetry/sapient/p1/v2/detection_report/{FUSION}", payload, qos_for("detection_report", True))]
async def test_up_task_ack_goes_to_the_ack_class():
async def test_first_up_message_declares_the_token():
    # f"{ANCHOR}/telemetry/sapient/p1/v2/live/{FUSION}" in fabric.tokens
async def test_token_goes_after_30_s_without_traffic_and_returns_with_traffic():
async def test_token_goes_when_the_pod_router_is_lost():        # bridge.on_transport("pod", False)
async def test_down_task_reaches_the_pod_fusion_keys_unchanged():
    # first forward one up message, then a task on f"{HOST}/task/p1/sapient/v2/task/{FUSION}"
    # -> pod.published[-1][:2] == (fusion_down_key("task"), payload)
async def test_down_drops_and_counts(case):     # parametrised; nothing is published to the pod
    # "undecodable": payload b"\xff\xff"
    # "wrong_destination": destination_id differs from the node ID in the key
    # "unknown_destination": the node never sent anything up
    # "stale_task": task timestamp 6 s before the clock            (G1-08)
    # "bad_key": a key that fabric_keys.parse refuses
    # "bad_kind": a detection_report arriving from the host
async def test_a_task_4_s_old_is_forwarded():
async def test_registration_ack_is_not_subject_to_the_age_limit():
async def test_up_drops_and_counts(case):       # "undecodable", "bad_key" (not a fusion up key), "bad_kind" (a task on fusion/up)
async def test_nothing_crosses_while_the_other_side_is_down():
    # on_transport("fabric", False): forward_up counts "other_side_down", publishes nothing;
    # on_transport("fabric", True): the next sample is forwarded. The same for the pod side and forward_down.
async def test_a_host_that_is_not_allowed_is_not_subscribed():
    # run() subscribes on the fabric to exactly subscriptions(HOST, "p1"), and on the pod to FUSION_UP_ALL
async def test_queue_keeps_512_and_drops_the_oldest():
    # make fabric.publish_raw wait on an event, feed 600 up samples through run(), release:
    # 87 <= dropped["queue_full"] <= 88, at most 513 samples are published, and the last sample fed is among them
async def test_main_survives_routers_that_are_not_there_yet(monkeypatch):
    # ZenohSession.open raises zenoh.ZError twice for each side, then succeeds (patch RECONNECT_SECONDS to 0):
    # main_async reaches bridge.run()
```

- [ ] **Step 3: Run them.** Expected: FAIL, `No module named 'pod_bridge'` and missing `publish_raw`.
- [ ] **Step 4: Implement the session helpers**, then `pod_bridge.py`. `run()` has one pump for each direction: a reader that moves samples from the session's queue into a bounded buffer and counts `queue_full` when it drops the oldest, and a writer that calls `forward_up` or `forward_down`. It also reads both `transport_changes` queues, calls `expire_presence` every 5 s, and logs both counters every 30 s when one changed. No exception from one sample may end a pump.
- [ ] **Step 5: Run the tests.** Expected: PASS, with the whole suite and no warning.
- [ ] **Step 6: Commit.** `git commit -m "feat: pod bridge between the pod router and the fabric"`

---

### Task 6: Fabric link, and the fusion node asks its link for key functions

**Files:**
- Create: `emulators/fabric_link.py`, `emulators/tests/test_fabric_link.py`
- Modify: `emulators/sapient_link.py`, `emulators/fake_fusion_node.py`, `emulators/tests/test_fusion_native.py`

**Interfaces:**
- Consumes: `fabric_keys` (Task 3).
- Produces: both link classes now have these members, and `FakeFusionNode` uses them in place of `LIVE_ALL`, `node_id_from_live_key` and `key_owner`:

```python
class ZenohFusionLink:                      # values that keep today's behaviour
    live_all: str                           # zenoh_keys.LIVE_ALL
    children_are_fusion_nodes = False       # another fusion node is a peer and is ignored
    has_parent = True
    def owner_of(self, key: str) -> str | None
    def node_of_live_key(self, key: str) -> str      # ValueError on a bad key

class FabricFusionLink:
    live_all: str                           # fabric_keys.live_subscription()
    children_are_fusion_nodes = True
    has_parent = False
    last_sample: tuple[str, bytes]
    @classmethod
    async def connect(cls, session, fusion_id: str, anchor: str, site: str, log) -> "FabricFusionLink"
    async def send(self, msg) -> None       # with a destination: that node's key below this anchor, at the node's site;
                                            # with none: this node's own output below this anchor, at this site
    async def send_upward(self, msg) -> None            # does nothing
    async def receive_raw(self) -> tuple[bytes, SapientMessage]
    async def receive(self) -> SapientMessage
    def owner_of(self, key: str) -> str | None
    def node_of_live_key(self, key: str) -> str
    def close(self) -> None
```

  `fake_fusion_node.py`: `TRANSPORTS = ("tcp", "zenoh", "fabric")`; new arguments `--fabric-anchor` (env `FABRIC_ANCHOR`) and `--fabric-site` (env `FABRIC_SITE`, default `h1`), required for the fabric transport; every `transport == "zenoh"` test becomes `transport != "tcp"`.

- [ ] **Step 1: Write the failing link tests** in `test_fabric_link.py` (`HOST`, `ANCHOR`, `FUSION` as in Task 5, `OTHER = "1ab0be0bcfdc3997544545af2235dd6d"`):

```python
async def test_connect_subscribes_to_the_three_classes_with_a_first_part_wildcard():
    # session subscriptions == set(fabric_keys.subscriptions()); never "**"
async def test_receive_gives_a_pod_message_and_its_key():
    # inject a registration on key_for(ANCHOR, "p1", "registration", FUSION) -> receive_raw returns it,
    # last_sample[0] is that key, owner_of(last_sample[0]) == FUSION
async def test_own_output_is_not_received():            # a sample below HOST is skipped
async def test_a_node_id_belongs_to_the_first_anchor_seen(caplog):
    # FUSION first seen below ANCHOR; the same node ID below OTHER is skipped and logged once
async def test_malformed_keys_are_skipped_and_the_loop_continues(caplog):
async def test_send_with_a_destination_uses_the_node_s_site_and_class():
    # after FUSION was seen at p1: a task -> f"{HOST}/task/p1/sapient/v2/task/{FUSION}",
    # a registration_ack -> f"{HOST}/ack/p1/sapient/v2/registration_ack/{FUSION}"
async def test_send_to_an_unknown_node_publishes_nothing_and_logs(caplog):
async def test_own_output_goes_below_the_own_anchor_at_the_own_site():
    # a status_report with no destination from node HOSTFUSION -> f"{HOST}/telemetry/sapient/h1/v2/status_report/{HOSTFUSION}"
async def test_a_live_key_teaches_the_route():
    # node_of_live_key(live_key(ANCHOR, "p1", FUSION)) == FUSION, and a task for FUSION is then sent to site p1
async def test_send_upward_does_nothing():
```

- [ ] **Step 2: Write the failing fusion node tests** in `test_fusion_native.py`:

```python
async def test_on_the_fabric_a_fusion_node_that_registers_is_a_child():
    # transport "fabric": a NODE_TYPE_FUSION_NODE registration from FUSION gets a registration_ack
    # on f"{HOST}/ack/p1/sapient/v2/registration_ack/{FUSION}", and FUSION is in node.nodes
async def test_inside_a_pod_another_fusion_node_is_still_ignored():     # transport "zenoh", as today
async def test_the_host_accepts_two_tracks_20_ms_apart():
    # two detection_reports from FUSION with timestamps 20 ms apart and different object IDs:
    # both reach _on_detection, and no error is published
async def test_inside_a_pod_two_detections_20_ms_apart_still_give_an_error():
async def test_a_restarted_host_asks_a_live_pod_to_register():
    # a token live_key(ANCHOR, "p1", FUSION) exists before the node starts: after REQUEST_GRACE_SECONDS
    # a task with request "Registration" is published on f"{HOST}/task/p1/sapient/v2/task/{FUSION}"
```

- [ ] **Step 3: Run them.** Expected: FAIL, `No module named 'fabric_link'`.
- [ ] **Step 4: Refactor first.** Give `ZenohFusionLink` the five members and change `FakeFusionNode` to use them. Run the suite. Expected: the tests that existed before this task pass with no change to their assertions.
- [ ] **Step 5: Implement `FabricFusionLink` and the fabric transport.** The link keeps `routes: dict[node_id, (anchor, site)]`; the first key or token seen for a node ID sets its route, and bindings last for the life of the process. In `FakeFusionNode`: `_from_other_fusion_node` returns `False` when `link.children_are_fusion_nodes`; the validator options have `detectionMinimumGap` 0 in that case and 0.08 otherwise; `_connect_link` builds a `FabricFusionLink` for the fabric transport.
- [ ] **Step 6: Run the tests.** Expected: PASS, whole suite, no warning.
- [ ] **Step 7: Commit.** `git commit -m "feat: fabric link, and a fusion node that takes its key functions from its link"`

---

### Task 7: Pod fusion node: traffic upward and tasks from above

**Files:**
- Modify: `emulators/sapient_link.py`, `emulators/fake_fusion_node.py`, `emulators/tests/test_fusion_native.py`, `emulators/tests/test_zenoh_link.py`

**Interfaces:**
- Consumes: `zenoh_keys.FUSION_DOWN_ALL` (Task 5), the link members of Task 6.
- Produces: `ZenohFusionLink.receive_from_above(self) -> SapientMessage` (next message on `FUSION_DOWN_ALL`; `ConnectionError` when the session is closed, `DecodeError` for bad bytes). `FakeFusionNode._parent_loop()` runs when `link.has_parent`.

- [ ] **Step 1: Write the failing tests** (transport "zenoh", `PARENT = "f0000002-0000-4000-8000-000000000002"`):

```python
async def test_link_receives_messages_from_above():                 # test_zenoh_link.py
async def test_own_status_also_goes_upward():
    # each own status report is published on up_key(FUSION, "status_report") and on fusion_up_key("status_report")
async def test_a_new_track_raises_one_alert_upward():
    # the first detection that makes a track -> one alert on fusion_up_key("alert") with node_id FUSION;
    # a second detection of the same track -> no second alert
async def test_a_sensor_alert_goes_upward_with_the_fusion_node_as_sender():
    # same alert_id, node_id FUSION, no destination_id; the sensor still gets its alert_ack
async def test_registration_request_from_above():
    # a task with request "Registration" for FUSION from PARENT -> a registration on fusion_up_key("registration")
    # and a task_ack on fusion_up_key("task_ack") with the same task_id, TASK_STATUS_ACCEPTED, destination PARENT
async def test_status_request_from_above():                         # an INFO_NEW status upward, and an accepted ack
async def test_a_command_from_above_goes_to_each_sensor_it_is_meant_for():
    # radar and vehicle registered; a look_at task from PARENT -> one task on down_key(RADAR, "task")
    # with the same look_at command, a new task_id and node_id FUSION; none for the vehicle;
    # one accepted task_ack upward whose reason names 1 node
async def test_a_command_no_sensor_takes_is_rejected_with_a_reason():
    # only the radar registered; a move_to task -> no task inside the pod; TASK_STATUS_REJECTED upward with one reason
async def test_a_task_for_another_node_is_ignored_and_logged(caplog):
async def test_bad_bytes_from_above_do_not_end_the_loop(caplog):
async def test_registration_ack_from_above_is_logged(caplog):
async def test_the_fabric_transport_has_no_parent_loop():           # FabricFusionLink.has_parent is False
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** The command name is the `Task.command` oneof field name, and `_targets(name)` picks the sensors. The task that goes to a sensor is a copy of the incoming task with a new task ID, stamped with this node's ID and the sensor as destination. The upward acknowledgement is built from the `sensor` `TaskAck.Request.Status` template, with the incoming task ID, the status, one reason, and the parent's node ID as destination.
- [ ] **Step 4: Run the tests.** Expected: PASS, whole suite, no warning.
- [ ] **Step 5: Commit.** `git commit -m "feat: pod fusion node sends status and alerts upward and acts on tasks from above"`

---

### Task 8: Recorder with the fabric keys

**Files:**
- Modify: `emulators/recorder.py`, `emulators/tests/test_recorder.py`

**Interfaces:**
- Consumes: `fabric_keys` (Task 3).
- Produces: env `RECORD_KEYS`: `pod` (default, today's behaviour) or `fabric`.

- [ ] **Step 1: Write the failing tests:**

```python
async def test_fabric_mode_subscribes_to_the_three_classes():       # exactly fabric_keys.subscriptions()
async def test_fabric_record_has_anchor_site_kind_and_node_id(tmp_path):
    # a detection_report on key_for(ANCHOR, "p1", "detection_report", FUSION) ->
    # {"key": ..., "kind": "detection_report", "node_id": FUSION, "anchor": ANCHOR, "site": "p1", "msg": {...}}
async def test_fabric_record_of_a_malformed_key_keeps_the_key_only(tmp_path):   # kind, node_id, anchor, site are None
def test_an_unknown_record_keys_value_is_refused():                 # ValueError that names RECORD_KEYS
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** `Recorder` takes the key expressions and a function that describes a key. The pod mode keeps its record fields exactly.
- [ ] **Step 4: Run the tests.** Expected: PASS, whole suite.
- [ ] **Step 5: Commit.** `git commit -m "feat: recorder mode for the fabric keys"`

---

### Task 9: The rig, and checks G1-02 to G1-05 and G1-11

**Files:**
- Create: `docker-compose.goat1.yml`, `emulators/probe_access.py`
- Modify: `README.md` (new section "Goat step 1: pod 1 to host" after the stage 4 section), `docs/acceptance-goat1.md`

**Interfaces:**
- Consumes: the generator output in `zenoh/goat1/` (Task 4), `pod_bridge.py` (Task 5), the fabric transport (Task 6), the parent loop (Task 7), `RECORD_KEYS=fabric` (Task 8), `FABRIC_ZENOH_IMAGE` (Task 1).

- [ ] **Step 1: Write `docker-compose.goat1.yml`.** Project name `apex-goat1`. Networks `pod1`, `mesh`, `host`. It is used as `docker compose --env-file zenoh/goat1/goat1.env -f docker-compose.goat1.yml`.

  | Service | Image, command | Networks | Identity and main settings |
  |---|---|---|---|
  | `zenohd-pod` | `eclipse/zenoh:1.10.2`, `zenoh/goat1/router-pod1.json5` | `pod1`, alias `router.p1.h1` | `pki/pod1/router.*` |
  | `fusion-node` | `fake_fusion_node.py` | `pod1` | `TRANSPORT=zenoh`, `pki/pod1/fusion.*`, `NODE_ID=${POD1_FUSION_NODE_ID}`, `AUTO_TASK=""` |
  | `radar`, `camera` | `fake_sensor.py` | `pod1` | `TRANSPORT=zenoh`, `pki/pod1/radar.*` and `camera.*`, `NODE_ID=${POD1_RADAR_ID}` and `${POD1_CAMERA_ID}` |
  | `vehicle` | `fake_sensor.py` | `pod1` | `TRANSPORT=tcp` to `bridge-node:5020`, `NODE_ID=${POD1_VEHICLE_ID}`, `DEPENDENT_NODES=${POD1_CAMERA_ID}` |
  | `bridge-node` | `bridge_node_side.py` | `pod1` | `pki/pod1/vehicle.*` |
  | `recorder` | `recorder.py` | `pod1` | `pki/pod1/recorder.*`, volume `pod-records` |
  | `radar2` | `fake_sensor.py`, compose profile `join` | `pod1` | `pki/pod1/radar2.*`, `NODE_ID=${POD1_RADAR2_ID:-}`, name "Fake second radar" |
  | `pod-bridge` | `pod_bridge.py` | `pod1`, `mesh` | `POD_CONNECT=tls/router.p1.h1:7447`, `POD_TLS_*` from `pki/pod1/bridge.*`, `FABRIC_CONNECT=tls/router.fabric.h1:7447`, `FABRIC_TLS_*` from `pki/fabric/pod1.*`, `FABRIC_ANCHOR=${FABRIC_POD1_ID}`, `FABRIC_SITE=p1`, `FABRIC_HOST_ANCHORS=${FABRIC_HOST_FUSION_ID}`, `ZENOH_KEY_PREFIX=h1/p1/` |
  | `zenohd-fabric` | `${FABRIC_ZENOH_IMAGE:-eclipse/zenoh:1.9.0}`, `zenoh/goat1/router-fabric.json5` | `mesh`, `host`, alias `router.fabric.h1` on both | `pki/fabric/router.*` |
  | `host-fusion` | `fake_fusion_node.py` | `host` | `TRANSPORT=fabric`, `pki/fabric/host-fusion.*`, `FABRIC_ANCHOR=${FABRIC_HOST_FUSION_ID}`, `FABRIC_SITE=h1`, `NODE_ID=f0000002-0000-4000-8000-000000000002`, `AUTO_TASK=request:Status,look_at`, `TASK_INTERVAL=20`, `NODE_HOLD_SECONDS=${HOST_HOLD_SECONDS:-120}`, `stdin_open`, `tty` |
  | `host-recorder` | `recorder.py` | `host` | `RECORD_KEYS=fabric`, `pki/fabric/host-recorder.*`, volume `host-records` |

  Every pod client has `ZENOH_CONNECT=tls/router.p1.h1:7447` and `ZENOH_KEY_PREFIX=h1/p1/`. Every host client has `ZENOH_CONNECT=tls/router.fabric.h1:7447`. Both routers have `RUST_LOG: ${ZENOHD_RUST_LOG:-info}`. Follow the mounts and the `x-emulator` anchors of `docker-compose.pod1.yml`.

- [ ] **Step 2: Bring the rig up.**

```bash
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1
dg() { docker compose --env-file zenoh/goat1/goat1.env -f docker-compose.goat1.yml "$@"; }
dg up -d && sleep 45
dg ps --format '{{.Service}} {{.State}}' | sort     # expected: 11 services, all running (radar2 is not started)
dg logs zenohd-pod zenohd-fabric | grep -ci -E 'error|panic'    # expected: 0
```

- [ ] **Step 3: G1-03, registration.** `dg logs fusion-node | grep -c "registration_ack"` is 1 or more, and that line shows `acceptance=True`. `dg logs host-fusion | grep -c "<- registration "` is 1 or more.

- [ ] **Step 4: G1-02, tracks and alerts up.** `dg logs host-fusion | grep -c "<- detection_report"` and `grep -c "<- alert"` are both 1 or more. In the host recorder's file (`dg exec host-recorder sh -c 'cat /data/records/*.jsonl'`), with `python3` and the `json` module: each `anchor` is `FABRIC_POD1_ID` or `FABRIC_HOST_FUSION_ID`, and no line has the node ID of the radar, the camera or the vehicle as `msg.node_id`.

- [ ] **Step 5: G1-04, task down.** Within 120 s of start, `dg logs radar camera | grep -c "<- task .* look_at"` is 1 or more, and `dg logs host-fusion | grep "<- task_ack" | grep -c TASK_STATUS_ACCEPTED` is 1 or more.

- [ ] **Step 6: G1-05, access, on the live routers.** Restart both routers with `RUST_LOG=zenoh::net::routing::interceptor=trace` (a compose variable, as `ZENOHD_RUST_LOG` in `docker-compose.pod1.yml`). Then use one-off containers (`dg run --rm --no-deps`) that publish or subscribe with a chosen certificate, and for each case show that the other side saw nothing and that the router logged the denial:
  1. the pod's slot certificate puts on `<FABRIC_HOST_FUSION_ID>/task/p1/sapient/v2/task/<POD1_FUSION_NODE_ID>`;
  2. the host fusion certificate puts on `<FABRIC_POD1_ID>/telemetry/sapient/p1/v2/alert/<POD1_FUSION_NODE_ID>`;
  3. the host recorder certificate subscribes to `**` and receives nothing in 15 s, while a subscription to `*/telemetry/sapient/*/v2/*/*` with the same certificate receives samples;
  4. in the pod, the radar certificate puts on the camera's up key.
  Write the publish and subscribe helper once, as `emulators/probe_access.py` (`put <key>` publishes one status report; `sub <key expression> <seconds>` prints the number of samples received), and use it for all four cases. Return the routers to `info` afterwards.

- [ ] **Step 7: Host restart (Review Focus 4).** `dg restart host-fusion`, wait 40 s. Expected: `dg logs --since 40s fusion-node` shows a task with request "Registration" from the host and a new `registration_ack`.

- [ ] **Step 8: G1-11, no regression.** `dg down`. Run the unit suite: expected all pass, no warning. Run the stage 4 rig as in the README's stage 4 section, steps 1 and 2: expected 3 registrations at the fusion node. Bring it down.

- [ ] **Step 9: Write the README section and the acceptance lines.** The README section has the `dg` helper, the commands of Steps 2 to 7 and what this run printed. `docs/acceptance-goat1.md` gets one line each for G1-02, G1-03, G1-04, G1-05 and G1-11, with what was measured and where it falls short.

- [ ] **Step 10: Commit.** `git commit -m "feat(goat1): the step 1 rig, with checks G1-02 to G1-05 and G1-11"`

---

### Task 10: Outages and a join with no restart (G1-06, G1-07, G1-09)

**Files:**
- Modify: `README.md`, `docs/acceptance-goat1.md`, and the code only if a check fails

**Interfaces:**
- Consumes: the running rig of Task 9; `goatgen.py --frozen-routers` (Task 4).

- [ ] **Step 1: G1-06, short outage.** With the rig up for 60 s:

```bash
docker network disconnect apex-goat1_mesh apex-goat1-pod-bridge-1 && sleep 30
docker network connect apex-goat1_mesh apex-goat1-pod-bridge-1 && sleep 30
```

  Expected: during the outage `dg logs --since 30s radar camera vehicle fusion-node` shows no `lost` and no `cannot reach` line, and the fusion node still logs sensor traffic. After it: `dg logs --since 25s host-fusion | grep -c "<- detection_report"` is 1 or more, and `dg logs --since 60s host-fusion | grep -c "<- registration "` is 0. The pod bridge logs a non-zero `other_side_down` counter.

- [ ] **Step 2: G1-07, long outage.** `dg down`, then `HOST_HOLD_SECONDS=20 dg up -d`, wait 60 s. Disconnect the bridge for 40 s and connect it again, wait 40 s. Expected in `dg logs host-fusion`: a line that the node is removed after 20 s, then a task with request "Registration" to the pod fusion node, then `<- registration`, in that order. Expected in `dg logs fusion-node`: a new `registration_ack` with `acceptance=True`.

- [ ] **Step 3: G1-09, join with no restart.** With the rig up:

```bash
before=$(docker inspect -f '{{.State.StartedAt}}' apex-goat1-zenohd-pod-1)
# add the line `radar2 = 3` under [pod1.slots] in goat1/registry.toml
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1 --frozen-routers   # expected: router files unchanged
dg --profile join up -d radar2 && sleep 30
dg logs fusion-node | grep "<- registration " | grep -c "Fake second radar"     # expected: 1 or more
test "$before" = "$(docker inspect -f '{{.State.StartedAt}}' apex-goat1-zenohd-pod-1)" && echo "router not restarted"
```

  Leave `radar2 = 3` in the registry when the check is recorded, and say in the README that the rig starts without `radar2` unless the `join` profile is named.

- [ ] **Step 4: If a check fails**, find the cause, fix it with a unit test that fails first, and run the check again. Do not change a pass criterion.
- [ ] **Step 5: Record.** Add the commands and printed output of Steps 1 to 3 to the README section, and one line each for G1-06, G1-07, G1-08 (the unit test of Task 5) and G1-09 to `docs/acceptance-goat1.md`.
- [ ] **Step 6: Commit.** `git commit -m "test(goat1): short and long outage, and a sensor that joins with no router restart"`

---

### Task 11: The `goat` test client (G1-10)

**Files:**
- Modify: `README.md`, `docs/acceptance-goat1.md`

**Interfaces:**
- Consumes: the running rig; `zenoh/goat1/pki/fabric/goat-cli.pem`, `goat-cli.key`, `ca.pem`; the goat source at `../usareur-af/goatcore`, commit `cbf2cb7f`.

- [ ] **Step 1: Build `goat` in a container.** Use a Rust image at version 1.88 or newer, the source mounted read-only, a named volume as `CARGO_TARGET_DIR`, and `cargo build --release --locked -j 2 --manifest-path /src/crates/Cargo.toml -p goat-cli`. Copy the binary `goat` to `zenoh/goat1/bin/goat`. Record the build time. If the build fails, keep the last 40 lines of output and go to Step 4.
- [ ] **Step 2: Make the profile directory** `zenoh/goat1/goat-profile/` in the form of `docs/goat-context.md` section 5.1: `config.toml` with `current_context = "goat1"`, and in `contexts/goat1/`: `profile.toml` with `router_endpoint = "tls/router.fabric.h1:7447"` and `device_id = "goat-cli"`, `mtls.cert.pem`, `mtls.key.pem`, `ca-roots.pem`.
- [ ] **Step 3: Run it** in a `debian:bookworm-slim` container on the network `apex-goat1_host`, with `GOAT_PROFILE_DIR` set to the mounted profile: `goat --context goat1 sub '<FABRIC_POD1_ID>/**' --take 1 --for 30s`. Check the flags with `goat sub --help` first. Pass: exit code 0 and one sample or more whose key starts with the pod's anchor.
- [ ] **Step 4: Record.** Pass: the command and its output. Not a pass: record G1-10 as unknown with the evidence, and say whether the cause is in goat or in our keys. If the cause is in our keys, that is a defect: fix it and run again.
- [ ] **Step 5: Commit.** `git commit -m "test(goat1): goat sub reads the pod's tracks on the fabric (G1-10)"`

---

### Task 12: One clean run and the acceptance record

**Files:**
- Modify: `README.md`, `docs/acceptance-goat1.md`, `docs/goat-context.md` (section 8 only)

- [ ] **Step 1: Run everything once from a rig that is down**, at the final code commit: the unit suite, then the README section from its first command to its last. Replace the recorded outputs in the README with the outputs of this run, and name the commit.
- [ ] **Step 2: Complete `docs/acceptance-goat1.md`:** a table of the evidence and the commit of each run, one line for each of G1-01 to G1-11, the list of what is not done (the design's non-goals), and the open items for step 4. Close item T-11 by reference, without editing `docs/acceptance.md`.
- [ ] **Step 3: Update `docs/goat-context.md` section 8:** item 1 (Zenoh versions) gets the measured result of G1-01, and item 6 (key shape) gets the decision.
- [ ] **Step 4: Check the constraints.** `git diff --stat 0cca505 -- <each file of the "must not change" list>` prints nothing. `git status --short` is clean after the commit.
- [ ] **Step 5: Commit.** `git commit -m "docs(goat1): the final run, and the acceptance record for step 1"`
