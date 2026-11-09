# SAPIENT over Zenoh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the Apex-SAPIENT-Docker learning rig from TCP-only to a hardened single-pod Zenoh deployment in four runnable stages: a sidecar bridge (Option A), Zenoh-native emulators, removal of Apex from the message path, and Pod 1 of Option B with mTLS, ACL and the QoS matrix.

**Architecture:** All transport code stays behind the emulators' existing `Link` interface (`send`, `receive`, `close`), so a `ZenohLink` swaps in without touching message logic. A `zenohd` router runs as a compose service; Zenoh's synchronous Python binding is adapted to asyncio through one `ZenohSession` wrapper that hands callbacks to the loop with `call_soon_threadsafe`. Apex's own `Validator` class, already installed in the emulator image, is reused when Apex leaves the path.

**Tech Stack:** Python 3.11 (`python:3.11-slim` image), asyncio, `eclipse-zenoh==1.10.2` (wheel `cp39-abi3-manylinux_2_28_aarch64`, verified on PyPI 2026-11-08), `eclipse/zenoh:1.10.2` router image (linux/arm64 verified on Docker Hub 2026-11-08), protobuf `sapient_msg.bsi_flex_335_v2_0`, Docker Compose, pytest.

**Spec:** `/Users/xiaoduo/code/research/cuas/explainer-zenoh/architecture.html` (sections 2 to 5 and 9), plus BSI Flex 335 v2.0 clauses 4.1, 4.2, 4.9, 4.11, 6.2.5.5 in `/Users/xiaoduo/code/research/cuas/doc/bsi-flex-335.pdf`.

## Global Constraints

- Every stage leaves `docker compose ... up` producing a working rig; no stage may break the TCP-only path in `docker-compose.yml` + `docker-compose.emulators.yml`.
- Payloads are the serialised `SapientMessage`, unchanged; no 4-byte prefix on Zenoh links; the prefix is re-added only where bytes hit a TCP socket (spec §2, BSI 4.2).
- Keys contain only fixed-width node UUIDs; never a report ID, task ID or timestamp (spec §8, Zenoh issue 2825).
- Key namespace, stages 1 to 3: `sapient/v2/<node_id>/up/<kind>`, `sapient/v2/<node_id>/down/<kind>`, `sapient/v2/live/<node_id>`. Stage 4 prefixes `h1/p1/` (spec §4).
- `<kind>` is the `SapientMessage.content` oneof field name: `registration`, `registration_ack`, `status_report`, `detection_report`, `task`, `task_ack`, `alert`, `alert_ack`, `error`.
- QoS matrix (spec §4): `task`, `task_ack`, `alert`, `alert_ack` → priority INTERACTIVE_HIGH, congestion BLOCK, express True; `registration`, `registration_ack` → INTERACTIVE_LOW, BLOCK; `status_report` → DATA, BLOCK; `detection_report` → DATA, DROP; fused tracks from a fusion node → DATA_HIGH, BLOCK.
- Zenoh sessions for emulators and bridges run in `client` mode with `scouting.multicast.enabled=false` and an explicit `connect` endpoint.
- Apex constraints that bridges must respect: one TCP connection per `node_id` (Apex rejects a mismatch as "hijacked"); the first message on any new Child connection must be a `registration`; Apex Child port for v2.0 is 5020, Peer port 5001.
- BSI timers: node retries connection every 10 s; re-registration not required if reconnected within 2 min; registration ack expected within 30 s.
- Tests run inside the emulator image: `docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -q tests` (working dir `/emulators`).
- Commit after each task on branch `zenoh`; never force-push; `main` stays TCP-only until stage 4 is accepted.

## Review Focus

1. A sensor whose first message on a new TCP connection is a `status_report`, not a `registration`: the node-side bridge must drop the connection with a logged reason rather than publish under an unknown node_id. Test added to Task 3.
2. A liveliness token that disappears and reappears inside the 120 s hold window: the Apex-side bridge must keep the same Apex socket and must not open a second one. Test added to Task 4.
3. Two TCP connections presenting the same `node_id` at once: the node-side bridge keeps the first and refuses the second (mirrors Apex's hijack rule). Test added to Task 3.
4. A `node_id` that is not a UUID string, or a key longer than 256 bytes: `zenoh_keys` must raise `ValueError` so nothing malformed reaches the router (spec §8, issue 2840). Test added to Task 1.
5. A message larger than Apex's `messageMaxSizeKb` (1024 KB) arriving over Zenoh: the Apex-side bridge must drop it and log, because Apex would close the socket and the node would appear to flap. Test added to Task 4.

---

## File structure

```
Apex-SAPIENT-Docker/
├── Dockerfile                      modify: add eclipse-zenoh==1.10.2, pytest
├── docker-compose.zenoh.yml        new: zenohd, bridge-node, bridge-apex services (stage 1)
├── docker-compose.native.yml       new: emulators on Zenoh, no Apex (stage 3)
├── docker-compose.pod1.yml         new: hardened router, certs, legacy sensor via bridge (stage 4)
├── zenoh/
│   ├── router-plain.json5          stage 1 router config (TCP listen, scouting off)
│   ├── router-pod1.json5           stage 4 router config (TLS, mTLS, ACL, lease 5000)
│   └── pki/make_certs.sh           stage 4 local CA and per-node certs
├── emulators/
│   ├── sapient_link.py             modify: add ZenohLink, ZenohFusionLink beside Link
│   ├── zenoh_keys.py               new: key builders/parsers, kind_of(), qos_for()
│   ├── zenoh_io.py                 new: ZenohSession (sync binding → asyncio), FakeZenohSession lives in tests
│   ├── bridge_node_side.py         new: TCP sensor ↔ Zenoh (stage 1, reused in stage 4)
│   ├── bridge_apex_side.py         new: Zenoh ↔ Apex Child port (stage 1, removed from compose in stage 3)
│   ├── recorder.py                 new: subscribe ** → JSONL archive (stage 3)
│   ├── fake_sensor.py              modify: --transport tcp|zenoh
│   ├── fake_fusion_node.py         modify: --transport tcp|zenoh, validation, re-registration request, own status, Fusion_Node registration
│   └── tests/
│       ├── conftest.py             FakeZenohSession, message builders from templates
│       ├── test_zenoh_keys.py
│       ├── test_zenoh_io.py        real two-session loopback test (marked `integration`)
│       ├── test_bridge_node_side.py
│       ├── test_bridge_apex_side.py
│       ├── test_zenoh_link.py
│       ├── test_fusion_native.py
│       └── test_recorder.py
└── README.md                       modify: one section per stage with the checks to run
```

---

## Stage 1: Option A sidecar bridge

### Task 0: Toolchain in the image and a router service

**Files:**
- Modify: `Dockerfile` (after the `pip install --no-cache-dir --no-deps .` line)
- Create: `zenoh/router-plain.json5`
- Create: `docker-compose.zenoh.yml`
- Create: `emulators/tests/conftest.py`, `emulators/tests/test_smoke_env.py`

**Interfaces:**
- Produces: compose service `zenohd` reachable from emulators at `tcp/zenohd:7447`; image `apex-sapient:4.2.0` with `import zenoh` working; `tests/conftest.py` fixture `templates()` returning the loaded `SapientMessage` templates via `sapient_link.load_template`.

- [ ] **Step 1: Write the failing environment test** in `emulators/tests/test_smoke_env.py`

```python
def test_zenoh_importable():
    import zenoh
    assert zenoh.__version__.startswith("1.10")

def test_templates_load(templates):
    assert templates("sensor", "Registration").WhichOneof("content") == "registration"
```

- [ ] **Step 2: Run it inside the current image to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -q tests`
Expected: FAIL, `ModuleNotFoundError: No module named 'zenoh'` (and `pytest` may itself be missing: same failure class).

- [ ] **Step 3: Add to `Dockerfile`:** `RUN pip install --no-cache-dir eclipse-zenoh==1.10.2 pytest==8.*`. Write `conftest.py` with the `templates` fixture wrapping `sapient_link.load_template`.

- [ ] **Step 4: Write `zenoh/router-plain.json5`**: `mode: "router"`, `listen.endpoints: ["tcp/0.0.0.0:7447"]`, `scouting.multicast.enabled: false`, `scouting.gossip.enabled: false`, `adminspace.enabled: true` with `permissions.read: true, write: false`.

- [ ] **Step 5: Write `docker-compose.zenoh.yml`** with service `zenohd`: `image: eclipse/zenoh:1.10.2`, `command: ["-c", "/config/router.json5"]`, volume `./zenoh/router-plain.json5:/config/router.json5:ro`, port `7447:7447`, `restart: unless-stopped`. Check the image's entrypoint first with `docker run --rm eclipse/zenoh:1.10.2 --help`; if the entrypoint is not `zenohd`, set `entrypoint: ["zenohd"]`.

- [ ] **Step 6: Rebuild and run the test**

Run: `docker compose -f docker-compose.yml -f docker-compose.emulators.yml build && docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -q tests`
Expected: `2 passed`.

- [ ] **Step 7: Verify the router starts and answers its adminspace**

Run: `docker compose -f docker-compose.yml -f docker-compose.zenoh.yml up -d zenohd && sleep 2 && docker compose -f docker-compose.yml -f docker-compose.zenoh.yml logs zenohd | tail -5`
Expected: a line containing `zenohd` and `Listening on tcp/0.0.0.0:7447` (wording may differ; any listen confirmation and no `ERROR`).

- [ ] **Step 8: Commit**

```bash
git checkout -b zenoh
git add Dockerfile zenoh/router-plain.json5 docker-compose.zenoh.yml emulators/tests
git commit -m "build: zenoh python binding, pytest and a zenohd router service"
```

### Task 1: Key namespace and QoS table

**Files:**
- Create: `emulators/zenoh_keys.py`
- Test: `emulators/tests/test_zenoh_keys.py`

**Interfaces:**
- Produces:
  - `PREFIX: str` read from env `ZENOH_KEY_PREFIX`, default `""` (stage 4 sets `h1/p1/`).
  - `up_key(node_id: str, kind: str) -> str`, `down_key(node_id: str, kind: str) -> str`, `live_key(node_id: str) -> str`
  - `UP_ALL: str` = `f"{PREFIX}sapient/v2/*/up/**"`, `DOWN_FOR(node_id) -> str` = `.../down/**`, `LIVE_ALL: str` = `.../live/*`
  - `parse_key(key: str) -> tuple[str, str, str]` returning `(node_id, direction, kind)`; `node_id_from_live_key(key: str) -> str`
  - `kind_of(msg: SapientMessage) -> str` = `msg.WhichOneof("content")`
  - `qos_for(kind: str, fused: bool = False) -> tuple[zenoh.Priority, zenoh.CongestionControl, bool]` per Global Constraints.
  - Raises `ValueError` for a `node_id` that is not `uuid.UUID(node_id)`-parseable, or a produced key longer than 256 bytes.

- [ ] **Step 1: Write the failing tests**

```python
NODE = "a0000001-0000-4000-8000-000000000001"

def test_keys_round_trip():
    assert up_key(NODE, "detection_report") == f"sapient/v2/{NODE}/up/detection_report"
    assert parse_key(down_key(NODE, "task")) == (NODE, "down", "task")
    assert node_id_from_live_key(live_key(NODE)) == NODE

def test_kind_of(templates):
    assert kind_of(templates("sensor", "Registration")) == "registration"

def test_qos_matrix():
    import zenoh
    assert qos_for("task") == (zenoh.Priority.INTERACTIVE_HIGH, zenoh.CongestionControl.BLOCK, True)
    assert qos_for("detection_report") == (zenoh.Priority.DATA, zenoh.CongestionControl.DROP, False)
    assert qos_for("detection_report", fused=True) == (zenoh.Priority.DATA_HIGH, zenoh.CongestionControl.BLOCK, False)

def test_bad_node_id_rejected():
    with pytest.raises(ValueError):
        up_key("not-a-uuid", "task")
    with pytest.raises(ValueError):
        up_key(NODE, "x" * 300)
```

- [ ] **Step 2: Run to verify they fail** (same pytest command as Task 0). Expected: `ModuleNotFoundError: zenoh_keys`.
- [ ] **Step 3: Implement `emulators/zenoh_keys.py`** with the signatures above. Check the exact enum names `zenoh.Priority.INTERACTIVE_HIGH`, `zenoh.CongestionControl.BLOCK` against `python -c "import zenoh; print(list(zenoh.Priority), list(zenoh.CongestionControl))"` in the image and adjust the test if the binding spells them differently.
- [ ] **Step 4: Run tests.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: zenoh key namespace and QoS table`.

### Task 2: ZenohSession, the sync-to-asyncio adapter

**Files:**
- Create: `emulators/zenoh_io.py`
- Test: `emulators/tests/test_zenoh_io.py` (real binding, two sessions, marked `@pytest.mark.integration`)
- Modify: `emulators/tests/conftest.py` (add `FakeZenohSession`)

**Interfaces:**
- Consumes: `zenoh_keys.qos_for`, `zenoh_keys.kind_of`.
- Produces class `ZenohSession` in `zenoh_io.py`:
  - `@classmethod async def open(cls, connect: str, loop: asyncio.AbstractEventLoop) -> ZenohSession` where `connect` is like `tcp/zenohd:7447`; config: `mode=client`, `connect.endpoints=[connect]`, `scouting.multicast.enabled=false`.
  - `async def publish(self, key: str, msg: SapientMessage, fused: bool = False) -> None` applying `qos_for(kind_of(msg), fused)` and encoding `application/protobuf`.
  - `def subscribe(self, keyexpr: str) -> asyncio.Queue[tuple[str, bytes]]` delivering `(key, payload)` via `loop.call_soon_threadsafe(queue.put_nowait, ...)`.
  - `def declare_token(self, key: str) -> None` (keeps the token object alive in `self._tokens`), `def undeclare_token(self, key: str) -> None`.
  - `def liveliness(self, keyexpr: str) -> asyncio.Queue[tuple[str, bool]]` delivering `(key, True)` on token appear, `(key, False)` on disappear; the subscriber is declared with history so already-present tokens are reported. Confirm the exact names (`session.liveliness().declare_token`, `.declare_subscriber(..., history=True)`, `.get`) in the installed binding's `zenoh/__init__.pyi` before coding.
  - `async def alive(self, keyexpr: str) -> list[str]` using `session.liveliness().get(keyexpr)`.
  - `def close(self) -> None`; `self.closed: asyncio.Event` set by `close()` and by the binding's transport-closed callback.
- `FakeZenohSession` in `conftest.py` implements the same methods in-memory: `publish` appends `(key, bytes, qos)` to `self.published` and fans out to matching `subscribe` queues using `zenoh.KeyExpr.intersects` if available, else a simple glob; `declare_token`/`undeclare_token` push to `liveliness` queues; `alive` returns current token keys; `inject(key: str, payload: bytes)` delivers a sample to matching `subscribe` queues as if it came from the router; `self.tokens: set[str]`.

- [ ] **Step 1: Write the failing integration test**

```python
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
```

`open_peer_listen(listen: str, loop)` is a test-only classmethod: `mode=peer`, `listen.endpoints=[listen]`, scouting off. Add `asyncio_mode = auto` to a `pytest.ini` in `emulators/`, and `pip install pytest-asyncio` in the Dockerfile.

- [ ] **Step 2: Run to verify it fails.** Expected: `ModuleNotFoundError: zenoh_io`.
- [ ] **Step 3: Implement `ZenohSession`.** Build the config with `zenoh.Config()` and `insert_json5` for each key. Callbacks arrive on binding threads: never touch asyncio objects directly in them; always `loop.call_soon_threadsafe`.
- [ ] **Step 4: Run the integration test.** Expected: PASS within 20 s (token loss is detected when the session closes; closing undeclares tokens promptly, so this is well under the 10 s lease).
- [ ] **Step 5: Write `FakeZenohSession` in `conftest.py`** and a unit test `test_fake_session_fans_out()` that publishes once and sees the sample on two overlapping subscriptions.
- [ ] **Step 6: Run all tests.** Expected: all pass.
- [ ] **Step 7: Commit** `feat: ZenohSession adapter from the sync binding to asyncio`.

### Task 3: Node-side bridge

**Files:**
- Create: `emulators/bridge_node_side.py`
- Test: `emulators/tests/test_bridge_node_side.py`

**Interfaces:**
- Consumes: `ZenohSession` (or `FakeZenohSession`), `sapient_link.Link` framing, `zenoh_keys`.
- Produces: `class NodeSideBridge(session, log)` with `async def serve(self, port: int)` (asyncio `start_server`) and `async def handle(self, reader, writer)`; state `self.nodes: dict[str, asyncio.StreamWriter]`. Behaviour:
  1. Read the first framed message. If `kind_of(msg) != "registration"`: log `first message must be a registration`, close, return.
  2. If `msg.node_id` already in `self.nodes`: log `node_id already connected; refusing`, close, return.
  3. `session.declare_token(live_key(node_id))`; subscribe `DOWN_FOR(node_id)`; publish the registration on `up_key`.
  4. Loop: each further framed message → `publish(up_key(node_id, kind))`; each `(key, payload)` from the down queue → write framed to the socket.
  5. On socket EOF or error: `undeclare_token`, remove from `self.nodes`, close writer.
- CLI/env: `LISTEN_PORT` (default 5020), `ZENOH_CONNECT` (default `tcp/zenohd:7447`).

- [ ] **Step 1: Write the failing tests** (use `asyncio.start_server` on port 0 and a raw client that writes `struct.pack("<I", len(b)) + b`)

```python
async def test_registration_is_published_and_token_declared(fake_session, templates): ...
    # assert fake_session.published[0][0] == up_key(NODE, "registration"); live_key(NODE) in fake_session.tokens
async def test_down_messages_are_written_to_socket(fake_session, templates): ...
    # fake_session.inject(down_key(NODE, "task"), task_bytes); read 4-byte prefix + body from the client; kind == "task"
async def test_first_message_not_registration_is_refused(fake_session, templates): ...
    # send a StatusReport first; expect EOF on the client; fake_session.published == []
async def test_duplicate_node_id_refused(fake_session, templates): ...
    # second client registering NODE gets EOF; len(fake_session.tokens) == 1
async def test_disconnect_undeclares_token(fake_session, templates): ...
```

- [ ] **Step 2: Run to verify they fail.** Expected: `ModuleNotFoundError: bridge_node_side`.
- [ ] **Step 3: Implement `NodeSideBridge`** and a `main()` that opens the session and serves.
- [ ] **Step 4: Run tests.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: node-side bridge, TCP sensor to Zenoh keys`.

### Task 4: Apex-side bridge

**Files:**
- Create: `emulators/bridge_apex_side.py`
- Test: `emulators/tests/test_bridge_apex_side.py`

**Interfaces:**
- Consumes: `ZenohSession`, `Link`, `zenoh_keys`.
- Produces: `class ApexSideBridge(session, apex_host, apex_port, hold_seconds=120, max_bytes=1024*1024, log)` with `async def run(self)`. Behaviour:
  1. Subscribe `UP_ALL` and `liveliness(LIVE_ALL)`.
  2. First `up` sample for an unknown `node_id`: if its kind is not `registration`, buffer nothing and log `dropping <kind> from unregistered <node_id>`; if it is, open `Link.connect(apex_host, apex_port)`, store in `self.links[node_id]`, start a reader task that publishes every Apex reply on `down_key(node_id, kind_of(reply))`.
  3. Each later `up` sample for a known node → `link.send`. A payload longer than `max_bytes` is dropped with a log line.
  4. Liveliness `(key, False)` → start a timer of `hold_seconds`; if `(key, True)` arrives first, cancel it; else close the link and delete it.
  5. If Apex closes a link (IncompleteReadError): delete it; the next `registration` from that node reopens it.
- CLI/env: `APEX_HOST` (default `apex`), `APEX_PORT` (5020), `ZENOH_CONNECT`, `HOLD_SECONDS` (120).

- [ ] **Step 1: Write the failing tests** (a fake Apex is `asyncio.start_server` on port 0 that records framed messages and can reply)

```python
async def test_registration_opens_one_apex_socket_and_forwards(...)      # fake Apex sees 1 connection, 1 registration
async def test_reply_from_apex_is_published_on_down_key(...)            # fake Apex writes RegistrationAck → published key == down_key(NODE,"registration_ack")
async def test_non_registration_first_sample_is_dropped(...)            # no Apex connection opened
async def test_token_loss_closes_socket_after_hold(...)                 # hold_seconds=0.2; connection count drops to 0
async def test_token_flap_within_hold_keeps_socket(...)                 # False then True within 0.2 s; still 1 connection, never 2
async def test_oversized_payload_dropped(...)                           # 1024*1024+1 bytes; fake Apex receives nothing further; link stays open
```

- [ ] **Step 2: Run to verify they fail.** Expected: `ModuleNotFoundError: bridge_apex_side`.
- [ ] **Step 3: Implement `ApexSideBridge`.**
- [ ] **Step 4: Run tests.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: Apex-side bridge, Zenoh keys to one Child socket per node`.

### Task 5: Wire stage 1 in compose and run T-01 to T-05

**Files:**
- Modify: `docker-compose.zenoh.yml` (add `bridge-node`, `bridge-apex`)
- Modify: `README.md` (new section "Stage 1: Option A bridge")

**Interfaces:**
- Produces: services `bridge-node` (image `apex-sapient:4.2.0`, `command: python bridge_node_side.py`, env `ZENOH_CONNECT=tcp/zenohd:7447`, `LISTEN_PORT=5020`) and `bridge-apex` (`command: python bridge_apex_side.py`, env `APEX_HOST=apex`, `APEX_PORT=5020`). Sensors from `docker-compose.emulators.yml` are re-pointed with `APEX_HOST=bridge-node`. The fusion node stays on Apex's Peer port 5001 over TCP.

- [ ] **Step 1: Add the services and the override** `radar/camera/vehicle: environment: APEX_HOST: bridge-node`.
- [ ] **Step 2: Bring everything up**

Run: `docker compose -f docker-compose.yml -f docker-compose.emulators.yml -f docker-compose.zenoh.yml up -d --build`

- [ ] **Step 3: T-01 round trip.** Run: `docker compose ... logs --since 60s fusion-node | grep -c "Registration"`. Expected: `3` (radar, camera, vehicle) within 60 s, and `docker compose ... logs radar | grep -c "RegistrationAck"` ≥ 1.
- [ ] **Step 4: T-02 task path.** Run: `docker compose ... logs --since 120s radar | grep -c "TaskAck"`. Expected: ≥ 1 after the fusion node's first auto-task (20 s interval).
- [ ] **Step 5: T-03 node loss.** Run: `docker compose ... stop radar && sleep 15 && docker compose ... logs --since 30s bridge-apex | grep "closing Apex socket"`. Expected: one line naming the radar's node_id. Confirm in Apex: `docker compose ... exec apex python -c "import sqlite3,glob;c=sqlite3.connect(glob.glob('/apex/data/*.sqlite*')[-1]);print(c.execute('select count(*) from Connection').fetchone())"` shows the count unchanged after restart plus one (table name per Apex manual; adjust if the schema names differ).
- [ ] **Step 6: T-04 short outage.** Run: `docker compose ... pause zenohd && sleep 20 && docker compose ... unpause zenohd && sleep 20 && docker compose ... logs --since 60s bridge-apex | grep -c "closing Apex socket"`. Expected: `0`, and sensors keep sending without a new registration in Apex (`docker compose ... logs --since 60s fusion-node | grep -c Registration` is `0`).
- [ ] **Step 7: T-05 long outage.** Same as step 6 with `sleep 150` while paused. Expected: sockets closed, then one new `Registration` per sensor in the fusion node log after unpause.
- [ ] **Step 8: Write the README section** listing exactly these seven commands and expected outputs.
- [ ] **Step 9: Commit** `feat(stage1): compose wiring for the sidecar bridge and T-01..T-05 checks`.

---

## Stage 2: Emulators speak Zenoh natively

### Task 6: ZenohLink and ZenohFusionLink behind the Link interface

**Files:**
- Modify: `emulators/sapient_link.py` (append two classes; `Link` unchanged)
- Test: `emulators/tests/test_zenoh_link.py`

**Interfaces:**
- Produces:
  - `class ZenohLink` with `@classmethod async def connect(cls, session: ZenohSession, node_id: str, log) -> ZenohLink`, `async def send(self, msg)`, `async def receive(self) -> SapientMessage`, `def close(self)`. `connect` declares `live_key(node_id)` and subscribes `DOWN_FOR(node_id)`; `send` publishes on `up_key(node_id, kind_of(msg))`; `receive` awaits the down queue and parses; `close` undeclares the token.
  - `class ZenohFusionLink` with the same three methods plus `connect(session, fusion_id, log)`: subscribes `UP_ALL`; `send(msg)` publishes on `down_key(msg.destination_id, kind)` when `destination_id` is set, else on `up_key(fusion_id, kind)` with `fused=True` (tracks, own status, own registration).
  - `ZenohFusionLink.receive_raw(self) -> tuple[bytes, SapientMessage]` returns the payload bytes with the parsed message (Task 8 needs them for `Error.packet`); `receive` calls it and returns the message only.
  - Both raise `ConnectionError` from `receive` when `session.closed` is set, so the emulators' `except* (asyncio.IncompleteReadError, ConnectionError)` reconnect logic keeps working.

- [ ] **Step 1: Write the failing tests** with `FakeZenohSession`

```python
async def test_zenoh_link_send_publishes_on_up_key_and_declares_token(...)
async def test_zenoh_link_receive_gets_down_messages(...)
async def test_fusion_link_routes_by_destination(...)      # task with destination_id → down_key(NODE,"task")
async def test_fusion_link_publishes_tracks_as_fused(...)  # no destination_id → up_key(FUSION,"detection_report"), qos BLOCK/DATA_HIGH
```

- [ ] **Step 2: Run to verify they fail.** Expected: `ImportError: cannot import name 'ZenohLink'`.
- [ ] **Step 3: Implement both classes.**
- [ ] **Step 4: Run tests.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: ZenohLink and ZenohFusionLink with the Link interface`.

### Task 7: `--transport` flag in both emulators and the stage 2 compose

**Files:**
- Modify: `emulators/fake_sensor.py` (`run()`, `main()` argparse)
- Modify: `emulators/fake_fusion_node.py` (`run()`, `main()`)
- Create: `docker-compose.native-sensors.yml`
- Modify: `README.md` ("Stage 2")

**Interfaces:**
- Consumes: `ZenohLink`, `ZenohFusionLink`, `ZenohSession.open`.
- Produces: argparse `--transport {tcp,zenoh}` (env `TRANSPORT`, default `tcp`) and `--zenoh-connect` (env `ZENOH_CONNECT`, default `tcp/zenohd:7447`) in both emulators. In `run()`, `self.link = await Link.connect(...)` becomes a call to a new `async def _connect_link(self)` that picks by transport. The `except*` reconnect block and the 10 s sleep stay.

- [ ] **Step 1: Write the failing test** `test_sensor_connect_link_picks_zenoh(monkeypatch)` in `test_zenoh_link.py`: construct `FakeSensor(args)` with `args.transport="zenoh"` and a patched `ZenohSession.open` returning `FakeZenohSession`; assert `await sensor._connect_link()` is a `ZenohLink`. Same for `FakeFusionNode` → `ZenohFusionLink`.
- [ ] **Step 2: Run to verify it fails.** Expected: `AttributeError: _connect_link`.
- [ ] **Step 3: Implement the flag and `_connect_link` in both emulators.**
- [ ] **Step 4: Run tests.** Expected: pass.
- [ ] **Step 5: Write `docker-compose.native-sensors.yml`**: sensors get `TRANSPORT: zenoh`, `ZENOH_CONNECT: tcp/zenohd:7447`; `bridge-node` is removed; `bridge-apex` and Apex remain; the fusion node stays on TCP 5001.
- [ ] **Step 6: Run T-01 and T-02 again** with `-f docker-compose.yml -f docker-compose.emulators.yml -f docker-compose.zenoh.yml -f docker-compose.native-sensors.yml`. Expected: same outputs as Task 5 steps 3 and 4.
- [ ] **Step 7: README section and commit** `feat(stage2): emulators publish and subscribe on Zenoh directly`.

---

## Stage 3: Apex leaves the message path

### Task 8: Fusion node takes over validation, re-registration and its own status

**Files:**
- Modify: `emulators/fake_fusion_node.py`
- Test: `emulators/tests/test_fusion_native.py`

**Interfaces:**
- Consumes: `sapient_apex_server.validate_proto.Validator`, `ValidationOptions` (installed in the image; constructed as in `apex_server.py`: `ValidationOptions.from_config_dict({...})` with the `validationOptions` block copied from `apex_config.emulators.json`), `ZenohFusionLink`, `ZenohSession.alive`.
- Produces in `FakeFusionNode`:
  - `def validate(self, msg: SapientMessage) -> str | None` returning an error description or `None`. Uses Apex's `Validator` in zenoh transport only (`tcp` keeps relying on Apex).
  - On a validation error: publish an `Error` message to `down_key(msg.node_id, "error")` and do not process the message. `Error.packet` (mandatory) is the raw payload bytes that failed, `Error.error_message = [desc]`; so `receive` paths must keep the raw bytes alongside the parsed message (`ZenohFusionLink.receive_raw() -> tuple[bytes, SapientMessage]`).
  - `async def request_registrations(self)`: called once after connect in zenoh mode; `for node_id in await session.alive(LIVE_ALL): send Task request "Registration" to node_id` (reuse `_task("request:Registration", node_id)`).
  - `async def _own_status_loop(self)`: every `--status-interval` (default 10 s) publish a `StatusReport` from `self.node_id` with `info=INFO_NEW` the first time then `INFO_UNCHANGED`, via `ZenohFusionLink.send` (no `destination_id`).
  - On zenoh connect, send the fusion node's own `Registration` (template `sensor/Registration` adapted: `node_definition = [NODE_TYPE_FUSION_NODE]`, `name="fake fusion node"`); stage 4 fills the aggregated capabilities.

- [ ] **Step 1: Write the failing tests**

```python
def test_validate_rejects_missing_mandatory_field(fusion, templates):   # strip node_id → description mentions node_id
def test_validate_accepts_template_registration(fusion, templates):     # None
async def test_invalid_message_gets_error_reply_on_down_key(fusion, fake_session, templates)
async def test_request_registrations_tasks_each_alive_node(fusion, fake_session)  # two tokens → two tasks on down_key(..,"task") with request == "Registration"
async def test_own_status_new_then_unchanged(fusion, fake_session)      # first INFO_NEW, second INFO_UNCHANGED, key == up_key(FUSION,"status_report")
```

- [ ] **Step 2: Run to verify they fail.** Expected: `AttributeError: validate`.
- [ ] **Step 3: Implement.** The entry point is `Validator.validate_sapient_message(...)` in `/Users/xiaoduo/code/research/cuas/Apex-SAPIENT-Middleware/sapient_apex_server/validate_proto.py` (line 395); read its parameters and the `ValidationError` list it fills, then join the error descriptions into the `str | None` that `validate` returns.
- [ ] **Step 4: Run tests.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: fusion node validates, requests registrations and reports its own status`.

### Task 9: Recorder

**Files:**
- Create: `emulators/recorder.py`
- Test: `emulators/tests/test_recorder.py`

**Interfaces:**
- Consumes: `ZenohSession.subscribe`.
- Produces: `class Recorder(session, out_dir: Path)` with `async def run(self)` subscribing `f"{PREFIX}sapient/v2/**"` and appending one JSON line per sample to `out_dir / f"{date:%Y-%m-%d}.jsonl"`: `{"t": iso8601 receive time, "key": key, "kind": kind, "node_id": node_id, "msg": MessageToDict(msg)}`. Unparseable payloads are written with `"error": "decode"` and the base64 payload. Env: `RECORD_DIR` (default `/data/records`), `ZENOH_CONNECT`.

- [ ] **Step 1: Write the failing tests** `test_recorder_writes_one_line_per_sample(tmp_path, fake_session, templates)` (two samples → two lines, `kind` fields correct) and `test_recorder_keeps_going_on_bad_payload(...)`.
- [ ] **Step 2: Run to verify they fail.** Expected: `ModuleNotFoundError: recorder`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests.** Expected: pass.
- [ ] **Step 5: Commit** `feat: JSONL recorder of all SAPIENT traffic on Zenoh`.

### Task 10: Stage 3 compose, no Apex

**Files:**
- Create: `docker-compose.native.yml`
- Modify: `README.md` ("Stage 3")

**Interfaces:**
- Produces: a standalone compose file (not layered on `docker-compose.yml`) with services `zenohd`, `fusion-node` (`TRANSPORT=zenoh`), `radar`, `camera`, `vehicle` (`TRANSPORT=zenoh`), `recorder` (volume `records:/data/records`). No `apex`, no bridges. Image stays `apex-sapient:4.2.0` (built by the stage 1 file) because it carries `sapient_msg`, `zenoh` and Apex's `Validator`.

- [ ] **Step 1: Write the compose file.**
- [ ] **Step 2: Run:** `docker compose -f docker-compose.native.yml up -d`.
- [ ] **Step 3: Check registrations and acks.** Run: `sleep 30 && docker compose -f docker-compose.native.yml logs radar | grep -c RegistrationAck`. Expected: ≥ 1; `logs fusion-node | grep -c "<- Registration"` is `3`.
- [ ] **Step 4: Check the late-joiner path.** Run: `docker compose -f docker-compose.native.yml restart fusion-node && sleep 20 && docker compose -f docker-compose.native.yml logs --since 30s fusion-node | grep -c "<- Registration"`. Expected: `3` (requested via `request_registrations`, not from sensor reconnects).
- [ ] **Step 5: Check the recorder.** Run: `docker compose -f docker-compose.native.yml exec recorder sh -c 'wc -l /data/records/*.jsonl && head -c 300 /data/records/*.jsonl'`. Expected: a growing line count and a JSON line with `"kind"`.
- [ ] **Step 6: Check validation.** Run: `docker compose -f docker-compose.native.yml run --rm --no-deps radar python -c "..."` publishing a `StatusReport` with no `node_id` on `up_key(NODE,'status_report')` and subscribing `down_key(NODE,'error')` for 5 s. Expected: one `Error` message received.
- [ ] **Step 7: README section and commit** `feat(stage3): Zenoh-native rig without Apex, with recorder`.

---

## Stage 4: Pod 1 of Option B

### Task 11: PKI, hardened router config, prefixed keys

**Files:**
- Create: `zenoh/pki/make_certs.sh`
- Create: `zenoh/router-pod1.json5`
- Modify: `emulators/zenoh_io.py` (TLS client options)
- Modify: `emulators/zenoh_keys.py` (nothing beyond honouring `ZENOH_KEY_PREFIX`; verify)
- Test: `emulators/tests/test_zenoh_keys.py::test_prefix_from_env`

**Interfaces:**
- Produces:
  - `make_certs.sh OUT_DIR`: creates `ca.pem`, `ca.key`, and for each name in `router.p1.h1 fusion.p1.h1 radar.p1.h1 camera.p1.h1 vehicle.p1.h1 recorder.p1.h1 bridge.p1.h1` a key and a CA-signed cert with CN = name and SAN DNS = name (so `verify_name_on_connect` passes against compose service names aliased to those DNS names). Uses `openssl` only.
  - `router-pod1.json5`: `listen.endpoints: ["tls/0.0.0.0:7447"]`; `transport.link.tls` with `root_ca_certificate`, `listen_private_key`, `listen_certificate`, `enable_mtls: true`, `close_link_on_expiration: true`; `transport.unicast.lease: 5000`; `scouting.multicast.enabled: false`; `access_control` with `enabled: true`, `default_permission: "deny"`, rules: `fusion-down` (put on `h1/p1/sapient/v2/*/down/**` and `h1/p1/fusion/**`, ingress), `node-up` (put + liveliness_token on `h1/p1/sapient/v2/*/up/**` and `h1/p1/sapient/v2/live/*`, ingress), `read-all` (declare_subscriber, query, liveliness_query, declare_liveliness_subscriber on `h1/p1/**`, ingress); subjects `fusion` (CN `fusion.p1.h1`), `nodes` (CNs radar/camera/vehicle/bridge), `recorder`; policies: fusion → fusion-down + read-all, nodes → node-up + read-all, recorder → read-all. Egress is left allowed.
  - `ZenohSession.open(connect, loop, tls: TlsOptions | None = None)` where `TlsOptions(root_ca: str, cert: str, key: str)` sets `transport.link.tls.root_ca_certificate`, `connect_certificate`, `connect_private_key`; env `ZENOH_TLS_CA`, `ZENOH_TLS_CERT`, `ZENOH_TLS_KEY` picked up by the emulators' `_connect_link`.

- [ ] **Step 1: Write the failing test** `test_prefix_from_env(monkeypatch)`: `ZENOH_KEY_PREFIX=h1/p1/` → `up_key(NODE,"task").startswith("h1/p1/sapient/v2/")`; reload the module in the test.
- [ ] **Step 2: Run to verify.** Expected: FAIL if `PREFIX` is read at import and not reloadable; make `PREFIX` a function `prefix()` reading env on each call if needed, then PASS.
- [ ] **Step 3: Write `make_certs.sh` and run it:** `zenoh/pki/make_certs.sh zenoh/pki/out && openssl verify -CAfile zenoh/pki/out/ca.pem zenoh/pki/out/radar.p1.h1.pem`. Expected: `OK`. Add `zenoh/pki/out/` to `.gitignore`.
- [ ] **Step 4: Write `router-pod1.json5`** and validate it loads: `docker run --rm -v $PWD/zenoh:/z eclipse/zenoh:1.10.2 -c /z/router-pod1.json5 --help` is not a validator; instead start it (Task 12 step 2) and look for `ERROR` lines about config.
- [ ] **Step 5: Add `TlsOptions` to `ZenohSession.open`.** No unit test (needs the real router); covered by Task 12.
- [ ] **Step 6: Commit** `feat(stage4): local PKI, hardened pod router config, TLS client options`.

### Task 12: Pod 1 compose with ACL checks (T-07, T-08) and a legacy sensor

**Files:**
- Create: `docker-compose.pod1.yml`
- Modify: `emulators/bridge_node_side.py` (TLS env, unchanged logic)
- Modify: `README.md` ("Stage 4")

**Interfaces:**
- Produces: standalone compose with `zenohd` (image `eclipse/zenoh:1.10.2`, `router-pod1.json5`, certs volume, network alias `router.p1.h1`), `fusion-node`, `radar`, `camera` (native, TLS env, `ZENOH_KEY_PREFIX=h1/p1/`), `vehicle` kept on TCP as the legacy node behind `bridge-node` (cert `bridge.p1.h1`), `recorder`.

- [ ] **Step 1: Write the compose file** with per-service `ZENOH_TLS_*` env pointing at the mounted `zenoh/pki/out` files and `ZENOH_CONNECT=tls/router.p1.h1:7447`.
- [ ] **Step 2: Start and check the router accepted the config.** Run: `docker compose -f docker-compose.pod1.yml up -d && sleep 3 && docker compose -f docker-compose.pod1.yml logs zenohd | grep -ci error`. Expected: `0`.
- [ ] **Step 3: Repeat the stage 3 checks** (Task 10 steps 3 to 5) with this file. Expected: same results; the vehicle registers via the bridge.
- [ ] **Step 4: T-07 ACL violation.** Run a one-off container with the radar's cert that publishes a `Task` on `down_key(CAMERA,"task")` while the camera log is watched for 10 s. Expected: the camera log shows no `<- Task` from that node; the router log (set `RUST_LOG=zenoh=debug` on `zenohd` for this test) shows a deny for `cert_common_name radar.p1.h1`.
- [ ] **Step 5: T-08 ordering under load.** Set `DETECTION_INTERVAL=0.02` on radar and camera for 2 minutes. Run: `docker compose -f docker-compose.pod1.yml logs --since 2m fusion-node | grep -c "Unchanged.*before"`. Expected: `0` (the emulators only log that phrase if the fusion node's `_on_status` sees UNCHANGED with no prior NEW; add that log line to `_on_status` as part of this task).
- [ ] **Step 6: Commit** `feat(stage4): pod 1 compose with mTLS, ACL and a legacy sensor via bridge`.

### Task 13: Pod fusion registers upward as a child Fusion_Node (T-11 partial, T-13 partial)

**Files:**
- Modify: `emulators/fake_fusion_node.py`
- Test: `emulators/tests/test_fusion_native.py`

**Interfaces:**
- Consumes: `self.nodes` registry (names, types, locations), `ZenohFusionLink`.
- Produces: `def build_fusion_registration(self) -> SapientMessage`: `node_definition = [NODE_TYPE_FUSION_NODE]`, `capabilities` = the union of registered sensors' `capabilities` (deduplicated on `(category, type)`), `mode_definition[0].task` = union of supported task commands, `status_definition.status_interval = 10 s`. Published on `f"{prefix()}h1/p1/fusion/up/registration"` after connect and again whenever `self.nodes` changes (debounced 5 s). Fused tracks already go to `up_key(fusion_id, "detection_report")`; in stage 4 the fusion link additionally mirrors them to `.../fusion/up/detection_report` for a future host.

- [ ] **Step 1: Write the failing tests** `test_fusion_registration_aggregates_capabilities(fusion, templates)` (two registered nodes with overlapping capabilities → deduplicated union; `node_type == NODE_TYPE_FUSION_NODE`) and `test_fusion_registration_republished_on_new_node(fusion, fake_session)`.
- [ ] **Step 2: Run to verify they fail.** Expected: `AttributeError: build_fusion_registration`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests.** Expected: pass.
- [ ] **Step 5: Live check (T-11 partial).** Run a one-off subscriber on `h1/p1/fusion/up/**` for 30 s against the pod 1 rig. Expected: one `registration` with `node_type FUSION_NODE`, then `detection_report`s whose `node_id` is the fusion node's, and no raw sensor detections on that prefix.
- [ ] **Step 6: Commit** `feat(stage4): pod fusion node registers upward as a child Fusion_Node`.

### Task 14: Documentation and stage acceptance

**Files:**
- Modify: `README.md` (table of the four stages, which compose files, which checks)
- Create: `docs/acceptance.md`

- [ ] **Step 1: Write `docs/acceptance.md`** as a checklist: every router default in spec §5 changed (listen TLS, scouting off, mTLS, ACL deny-by-default, lease 5000); T-01 to T-05 pass on stage 1; T-01, T-02 pass on stage 2; stage 3 checks pass; T-07, T-08, T-11 partial pass on stage 4; open items: T-06 (needs a shaped link), T-09, T-10 (hardware), T-12 (BSI harness), T-13 (Stone Soup).
- [ ] **Step 2: Run the full unit test suite one last time.** Expected: all pass.
- [ ] **Step 3: Commit** `docs: stage guide and acceptance checklist` and open a PR from `zenoh` to `main` for review; do not merge until the acceptance checklist is signed.

---

## Out of scope for this plan

The Stone Soup adapter (spec §7), the host and external-host tiers, the WAN downsampling test T-06, soak and failover tests T-09 and T-10, and the BSI test harness run T-12. Each is a separate plan once this one is accepted.
