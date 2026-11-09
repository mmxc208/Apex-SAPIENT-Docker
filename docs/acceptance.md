# SAPIENT over Zenoh: stage acceptance

This checklist covers the four stages of the plan in `docs/superpowers/plans/2026-11-08-sapient-over-zenoh.md`, up to commit `a04d411` on branch `zenoh`. The stage sections named below are in `README.md`, and each holds the commands and what one run printed.

A ticked box means a run recorded the evidence named on that line. It doesn't mean the spec's whole wording was met, so each line says what was measured and where it falls short. Nothing is signed until the sign-off at the end is filled in.

The rigs were not re-run for this document. Each stage's evidence dates from its last README update, listed below, and later commits changed shared emulator code. The unit suite was run on this tree.

| Evidence | Last updated at |
|---|---|
| Stage 1 | `03c1282` |
| Stage 2 | `5ffd4e5` |
| Stage 3 | `ab0311c` |
| Stage 4, steps 1 to 7 | `a65614e` |
| Stage 4, step 8 (T-11 partial) | `2335831`, before `a04d411` changed the fusion node's own status after a re-announced registration |

## Unit suite

- [x] `python -m pytest -p no:cacheprovider -q -W error tests`, in the emulator image: **240 passed**, no warnings.

## Router defaults changed (spec §5)

All values are in `zenoh/router-pod1.json5`, used by stage 4. Defaults are from `DEFAULT_CONFIG.json5` at zenoh 1.10.2. Stages 1 to 3 use `zenoh/router-plain.json5`, which has no TLS or access control by design and changes only the listen endpoint (`tcp/0.0.0.0:7447`), multicast and gossip scouting (off) and the adminspace (read-only).

| | Setting | Default | Pod 1 value | Line | Live evidence |
|---|---|---|---|---|---|
| [x] | Listen endpoint | `tcp/[::]:7447` | `tls/0.0.0.0:7447` | 6 | Every client in Stage 4 connects over `tls/`. |
| [x] | Multicast scouting | on | off | 9 | Configuration only, not observed separately. |
| [x] | Gossip scouting | on | off | 10 | Configuration only. The spec's sketch leaves gossip on; a pod with one router has no use for it. |
| [x] | Adminspace | off | on, read-only | 13, 14 | Configuration only. |
| [x] | Link lease | 10000 ms | 5000 ms | 19 | Configuration only: the router starts with it (Stage 4 step 1), but the 5 s lease was not timed. |
| [x] | TLS certificates | none | CA, router key and certificate | 22 to 24 | Stage 4 step 1 and every later step. |
| [x] | Mutual TLS | off | on | 25 | Stage 4 clients connect with their own certificates. No README step tries a client without one. During Task 11 a client that withheld its certificate was refused (`peer sent no certificates`). |
| [x] | Close link on certificate expiry | off | on | 26 | Configuration only. |
| [x] | Access control | off | on | 31 | Stage 4 step 6 (T-07). |
| [x] | Default permission | deny | deny, stated explicitly | 32 | Stage 4 step 6 (T-07). The rules, subjects and policies are at lines 33 to 110, 111 to 117 and 118 to 124. |

Differences from the spec's sketch:

- The lease is `transport.link.tx.lease`. The sketch's `transport.unicast.lease` doesn't exist in 1.10.2, and zenohd refuses to start with it.
- Each certificate has its own rules for its own keys, in place of the sketch's shared `node-uplink` and `anyone-reads` rules.
- An `egress-all` rule (line 101) is needed because deny by default also filters egress in 1.10.2.
- `keep_alive` stays at the default of 4, which is the sketch's value.
- `connect`, the outbound TLS settings, `verify_name_on_connect`, `downsampling` and `gateway` are left out, because they belong to the host tier, which is out of scope.

## Measured

### Stage 1: T-01 to T-05 (README "Stage 1: Option A bridge")

- [x] **T-01, round trip.** The fusion node logged 3 registrations and the radar received its `registration_ack`. The spec also asks for the registration, status and detections to be confirmed in Apex's SQLite, and for the 30 s limit, which the README check doesn't test: it counts log lines after 60 s.
- [x] **T-02, task path.** The radar logged 2 `task_ack` lines in 120 s, from auto-tasks. The count isn't filtered to `look_at` or to the fusion node (see the deferred list).
- [x] **T-03, node loss.** After `dc stop radar`, the Apex socket closed at the end of the 120 s hold, not at 15 s, and Apex recorded one fewer open connection (`rows 4 open 3`). The spec's "within 2 × lease" doesn't hold for this design, by ruling: the hold is what §4.9's reconnect window requires. After restart, the radar registered again.
- [x] **T-04, short outage.** A 20 s router pause gave 0 socket closes and 0 new registrations.
- [x] **T-05, long outage.** A 150 s pause closed 3 sockets at the end of the hold, and each sensor registered again through a request from `bridge-apex`. Sensors stayed connected to `bridge-node`. The spec's "no hijacked errors" wasn't checked.

### Stage 2: T-01, T-02 (README "Stage 2: native Zenoh sensors")

- [x] **T-01, round trip.** 3 registrations at the fusion node, and the radar received its `registration_ack`. The same limits as stage 1 apply.
- [x] **T-02, task path.** 3 `task_ack` lines in 120 s. This can include the ack for a re-registration request, as the README says.

### Stage 3 (README "Stage 3: Zenoh-native rig without Apex")

- [x] **Registrations and acknowledgements.** 3 registrations and the radar's `registration_ack`.
- [x] **Late joiner.** After a fusion node restart, 3 registrations came in through requests to live nodes, with 0 sensor reconnects.
- [x] **Recorder.** The record count grew from 765 to 802 lines in 10 s.
- [x] **Validation.** A `StatusReport` with no `node_id` got one `Error` on the radar's down key.

### Stage 4 (README "Stage 4: pod 1 with mutual TLS and access control")

- [x] **Stage 3 checks over mutual TLS (steps 1 to 5).** The router logged 0 errors at bring-up, and the vehicle registered through the bridge.
- [x] **T-07, access control (step 6).** The radar's certificate was refused when it tried to publish on the camera's down key, report as the camera, and subscribe to the camera's down key. Controls with allowed certificates arrived, and the router logged each denial by certificate name.
- [x] **T-08, status ordering (step 7).** 0 `Unchanged ... before` lines and 216 logged detections (every 10th per sensor), with 0 invalid messages, over about 2 minutes at 10 Hz per sensor. The plan's 50 Hz can't run: the validator rejects detections less than 80 ms apart. The check can fire only on the first status after a registration, so a pass is limited evidence. The spec names Apex as the judge; here the fusion node makes the check, because stage 4 has no Apex.
- [x] **T-11, partial (step 8).** One `NODE_TYPE_FUSION_NODE` registration, which Apex's Validator accepted, then 21 detection reports from the fusion node's own ID, and no raw sensor detections on `h1/p1/fusion/up/**`. There is no host fusion node, so the spec's "host fusion acks" is still open.

## Open

- [ ] **T-06, congestion.** 20 sensors at 10 Hz over a 1 Mbit/s link. Needs a shaped link.
- [ ] **T-09, soak.** 24 h with sensors joining and leaving. Needs hardware.
- [ ] **T-10, router failover.** Two routers in a pod. Needs hardware.
- [ ] **T-11, remainder.** A host fusion node acknowledges the pod and sees only fused tracks. Needs the host tier.
- [ ] **T-12, conformance.** BSI Flex 335 v2 test harness against the bridge's TCP side.
- [ ] **T-13, Stone Soup adapter.** Replay a trial through `SapientDetectionReader`. Task 13 added the pod's upward registration, which this will need, but the adapter itself isn't built.

## Known gaps deferred to review

Items for the final review to triage. "Closed:" marks an item that the current tree already resolves.

### Compose, operations and README

- Orphan-warning note and `--remove-orphans`.
- Port 7447 is published on all interfaces. Bind it to 127.0.0.1 unless there are off-host peers. This also applies to `docker-compose.native.yml`, where it is plan-mandated.
- `zenohd` is left running.
- Sensors lack `depends_on` for `bridge-node`, so their first retry takes 10 s.
- The pod 1 compose comment says `zenoh=debug` shows denials, which needs the interceptor trace level.
- T-05 `--since 200s` window overlaps T-04. Closed: the README now uses `--since 185s`.
- "Each output is what that run printed" is loose in three places in stage 1.
- T-04 and T-05 README text goes stale after the code fix. Closed: rewritten from new observations in `03c1282`.
- The T-02 README check counts bridge-issued request acks too. Filter on the fusion node's ID.
- The README's host-side venv lacks `eclipse-zenoh` for running `fake_sensor.py` natively.
- The fusion node's `--status-interval` is missing from the README.
- The stage 3 README `# 3` bring-up count reads as deterministic, but can be 3 to 6.
- The stage 3 README softens "never `down -v`" and drops the `--remove-orphans` warning.
- The README's "rejects every one" is overstated relative to the every-10th log.
- The plan text still says `RUST_LOG=zenoh=debug` and `DETECTION_INTERVAL=0.02`, superseded by rulings. The plan wasn't edited.

### Test tooling

- Pin pytest exactly. Closed: the `Dockerfile` pins `pytest==8.4.2`.
- `pythonpath=.` and `addopts=-p no:cacheprovider` in `pytest.ini`.
- Unprefixed tests depend on an ambient `ZENOH_KEY_PREFIX`. Clear it in `conftest`.

### `emulators/zenoh_keys.py`

- Add an `error` row to `test_qos_table_rows`.
- `parse_key` returns kinds outside the nine.
- `PREFIX` is not validated for a trailing slash.
- `kind_of` is annotated `-> str` but may return `None`.
- `qos_for(None)` and `kind_of(SapientMessage())` are untested.
- `test_every_message_kind_has_qos` is subsumed.

### `emulators/zenoh_io.py`

- `fused=True` pass-through is untested.
- The publish ordering limit and `closed` latch semantics need docstrings.
- The module docstring overstates threading.
- `alive()` hides query failures.
- Unbounded queues.
- The fake delivers after close, while the real session likely raises.
- The `_call_in_loop` `RuntimeError` branch is untested.
- Integration tests leak sessions on failure (needs a fixture).
- The `__` to `/` kwarg encoding in `_config` is clever.
- TLS config settings have no unit test (monkeypatch `zenoh.open`).

### `emulators/bridge_node_side.py`

- Catch `OSError`, not only `ConnectionError`, before registration.
- Log `undeclare_token` failures.
- `SO_KEEPALIVE` on accepted sockets.
- Unbounded down queue while a node is away (needs `ZenohSession.unsubscribe`).
- Always `fused=False`, so a fusion node behind the bridge gets sensor QoS.
- A test reads the fake's private `_subscriptions`.
- No mid-frame disconnect test.
- No `log.error` before re-raising a listener failure (only a traceback).
- The listener test's blocker binds 127.0.0.1 while `serve` binds 0.0.0.0. It passes in the Linux container and would time out natively on macOS. Bind the blocker to 0.0.0.0.

### `emulators/bridge_apex_side.py`

- Grace does not debounce when a connect outlasts it. On a cold start this gives a redundant request and an unsolicited TaskAck per node. Carry into TaskAck review against real Apex.
- A content-less message is forwarded to Apex.
- The key's `node_id` is never compared with the payload's `node_id`.
- No back-off on the close, grace, request cycle.
- `_token_alive` is never pruned.
- `open_session` imported from the sibling bridge. Closed: it now lives in `zenoh_io.py`.
- Two tight timing assertions (10 ms in a 50 ms grace).
- A 740-line test file with re-inlined setup.
- Two inferred ordering races, neither observed live: a fast lost, back, lost, back flap can strand a live node as gone until the next `alive()`, and a stale `alive()` reply processed after a token-gone event can cancel a valid hold.

### `emulators/sapient_link.py` (Zenoh links)

- `DecodeError` escapes `_receive_loop` (ruled into the Task 7 and 8 notes).
- Send on a closed session is not translated to `ConnectionError`.
- No ordering across coroutines.
- Narrow sample loss if receive is cancelled after the queue get completes.
- The integration test's `router.close()` is not in `finally`.

### `emulators/fake_fusion_node.py`

- Own status may overtake own Registration (await the put first). Closed: `_status_once_registered` waits for it.
- `received` is stamped at dequeue, not arrival, so a stalled BLOCK put can age samples past 0.9 s.
- `Error` goes to the claimed `node_id`, not the key owner.
- Other fusion nodes on `UP_ALL` are not filtered. Closed: `2335831` leaves their keys out of validation.
- A router bounce does not re-announce the own Registration. Moved to the host tier by ruling.
- The `Validator` dict is built per message and never pruned.
- `sapient_apex_server` is imported unconditionally (TCP mode needs it too).
- The file keeps growing. A future split could move Zenoh-only validation and peer filtering out of it.
- The reset test discriminates only through the 80 ms gap check, which is weak on slow hosts. A timestamp-controlled assertion would pin it.
- A peer fusion node is recognised only from its Registration, so a stale `self.nodes` entry is possible.
- Departed sensors stay in the aggregate. Liveliness could drive removal.
- Dedupe on `(category, type)` keeps the first sensor's value and units (plan-mandated).
- The republish trigger compares the whole Registration.
- `dependent_nodes` is not declared.
- Test gaps: `own_registered.clear()` is unpinned, the debounce window is not pinned from the first change, and the TCP track test uses `ZenohFusionLink`.
- A status firing during the re-announce's second put can still go out as Unchanged once. The window is one put; setting `status_changed` right after the first send would shrink it.

### `emulators/recorder.py`

- Decode failures are not logged.
- A partial write can corrupt the next line, though the docstring says crash-safe.
- A disk stall grows the queue without bound (synchronous writes on the loop).
- `t` is dequeue time.
- Write failures are logged at INFO per sample.
- Router loss is not logged (no `transport_changes` consumer).

### `zenoh/pki/make_certs.sh`, `zenoh/router-pod1.json5`

- `cert_is_valid` does not check key and certificate match, or the CN.
- Leaf certificates have no expiry margin.
- `2>/dev/null` hides openssl failures.
- `node-up` is a cross-product. Closed: Task 12 replaced it with one rule per node.
- Sensor ACL rules are cross-products (put on the live key, token on up keys), beyond the ruling.

### Stage 4 checks

- The ordering check fires only on the first status after a registration, so the evidence is limited.

## Sign-off

Do not merge `zenoh` into `main` until this is signed.

- Reviewer:
- Date:
- Decision on the open items and deferred gaps:
