# Step 4 design: the step 1 rig on a real goatnet, by configuration only

Date: 2026-11-18. Branch: `goat-step4-cuaslab`, made from `goat` at `8b536f9`. Status: built on 2026-11-18 to 19 UTC; the record is `docs/acceptance-goat4.md`.

Read first: `docs/goat-roadmap.md`, `docs/goat-context.md`, `docs/acceptance-goat1.md`, and the step 1 design `docs/superpowers/specs/2026-11-11-goat-step1-pod-to-host-design.md`. This document uses the words of those files and does not repeat them.

## 1. Intent

Step 1 ran pod 1 against a stand-in host: our own fabric router with goat's rules, and a test CA. Step 1 made one promise for this step: each fabric client takes five facts from configuration (the CA file, its certificate, its key, the router endpoint, its anchor), so a move to a real goatnet changes configuration only.

Step 4 tests that promise. The stand-in fabric router and its test CA are replaced by a real goatnet. The three fabric clients (the pod bridge, the host fusion node, the host recorder) get their identity from that goatnet and connect to its router. No program changes.

Richard chose this scope on 2026-11-18: move the rig as it is, and do nothing more. If a program must change to make a check pass, that is a finding. It is recorded, and the change is not made in this step without a new decision.

## 2. The goatnet

The goatnet is `cuaslab`, a goatlite that was stood up on 2026-11-18 from `goatcore` at `e44e893d`. It is not on a cloud VM, as the roadmap expected. It runs in a Lima VM on the same Mac as the rig. Measured on 2026-11-18, read-only:

| Subject | Fact |
|---|---|
| Machine | Lima VM `goatlite`, Ubuntu 24.04, arm64, address `192.168.64.4` |
| Fabric router | `zenohd v1.9.0-modified`, image `ghcr.io/usareur-af/zenoh-pqc-fips`. Listens on `tls/0.0.0.0:7447`, mutual TLS required. |
| Router certificate | Names `zenoh.cuaslab.cuaslab.lan` and `goat-zenoh-router`, and the address `192.168.64.4`. A client may connect by address. |
| CA | `cuaslab goatlite CA`. The root is in every slot bundle. |
| Slot pool | 1000 slots, none in use. An anchor is 32 hexadecimal characters. |
| Slot write rule | `put`, `delete` and `liveliness_token`, ingress, on `<anchor>/**`, `volatile/<anchor>/**` and `<anchor>/**/@adv/**`. Each slot may also write `attest/schema/**`. |
| Read rule | Every TLS client may subscribe, query and declare a liveliness subscriber on `**`. |
| Default | `deny`. A denied write is dropped with no error to the writer. |
| Router log | Level `info`. It does not log access decisions. |
| Portal | `https://portal.cuaslab.cuaslab.lan`. The operator key answers `GET /api/whoami` with `operator: true`. No machine is enrolled and no custodian has a quota. |
| Mesh key mint | Off (`PORTAL_MESH_KEY_MINT_ENABLED=false`). An enrolment makes a fabric identity and no mesh setup key. |
| Mesh | The goatlite box is not a mesh peer. The only peer is the Mac. |
| Path from the rig | Colima VM `192.168.64.5` to `192.168.64.4` through the Mac (`192.168.64.1`), by a route on each VM. No WireGuard on this path. |
| Pairing | A session from the image `apex-sapient:4.2.0` (Zenoh binding 1.10.2) to the router opened with the founder's certificate, subscribe only. Publish and liveliness are not yet measured. |

What changed in goat between `cbf2cb7f` and `e44e893d` does not touch the slot write rule, the read rule, the anchor, or the portal's enrolment API.

## 3. Goals, non-goals, anti-goals

### Goals

1. The three fabric clients run against `cuaslab` with slot identities that the `cuaslab` portal minted.
2. The results of step 1 are shown again on `cuaslab`: tracks and alerts at the host, registration, a task down to a sensor, a refused write outside a slot, a short and a long outage, a sensor that joins with no router restart, and goat's own client reading the pod's tracks.
3. The proof that only configuration changed: no existing file below `emulators/` is modified (check G4-12).
4. The step 1 rig and the earlier rigs run as before.

### Non-goals

- No session ID, no schema declaration at `attest/schema`, no topic registration at the portal. They are the next small step.
- No mesh. The pod does not become a mesh peer, and the goatlite box does not join the mesh.
- No change to `cuaslab`: no router log level, no access rule, no portal setting. Enrolments and a quota are the only things this step writes there.
- (Added after the build.) One portal setting of `cuaslab` was changed after all, by Richard's decision on 2026-11-18: bundle-create was turned off (see `docs/acceptance-goat4.md`).
- No move of the host fusion node or the recorder into the goatlite VM.
- No Stone Soup, no Billie adapter, no second pod.

### Anti-goals

- A check that passes because a rule of `cuaslab` was widened, or because a program was changed without a recorded decision.
- A secret in git or in a document: the operator key, a slot key, an API key, a bundle token, the slot pool salt.
- A statement in the record that no saved evidence file holds (roadmap section 2).

## 4. Constraints

- Roadmap section 2 applies, with one exception that Richard made on 2026-11-18: this step uses the branch `goat-step4-cuaslab`, not `goat`. Nothing is pushed.
- `goatbuilder teardown` is never run. `cuaslab` is changed only through the portal's enrolment API.
- The `goat` command line tool cannot call the `cuaslab` portal from the Mac: its portal client does not trust a private CA. Portal calls use `curl`, which reads the macOS keychain where the root is installed.
- An agent session cannot read `~/.docker`. It sets `DOCKER_HOST=unix://$HOME/.colima/default/docker.sock` and its own `DOCKER_CONFIG`.
- Colima mounts only paths below `/Users`. Files that a container mounts must be below the repository.
- Docker Compose is the version in Colima's Docker; the overlay must use only what that version supports.

## 5. Approaches

| | Approach | Trade-off |
|---|---|---|
| A | A new overlay compose file beside the step 1 file, and a small enrolment script. The step 1 file is not edited. | Some service names repeat in two files. The step 1 rig and its evidence stay as they are, and the overlay holds configuration only. |
| B | Make the step 1 compose file switchable by variables and a profile. | One file. But the step 1 file changes, and each README command of step 1 is checked against saved evidence, so the step 1 record must be proven again. |
| C | Teach the generator `goatgen.py` to call the portal. | One entry point. But the generator is an offline tool with unit tests, and it would hold a live key and make network calls. This is the largest change and it is not configuration. |

Richard chose A on 2026-11-18.

## 6. Design

### 6.1 Parts

| Part | Step 1 | Step 4 |
|---|---|---|
| Pod router, sensors, pod fusion node, pod recorder, node bridge | as built | unchanged, same pod CA and generator |
| Pod bridge, pod side | pod CA, `tls/router.p1.h1:7447` | unchanged |
| Pod bridge, fabric side | test fabric CA, `tls/router.fabric.h1:7447`, slot `pod1` | `cuaslab` root, `tls/192.168.64.4:7447`, the slot of machine `pod1-bridge` |
| Fabric router `zenohd-fabric` | our container | not started. The router is `cuaslab`'s. |
| Host fusion node | test fabric CA, slot `host-fusion` | `cuaslab` root, the slot of machine `host-fusion` |
| Host recorder | test fabric CA, slot `host-recorder` | `cuaslab` root, the slot of machine `host-recorder` |
| `goat` test client | built from source, slot `goat-cli` | the installed `goat` 0.5.19 on the Mac, context `cuaslab`, the founder's identity |

### 6.2 Identity

Three machines are enrolled at the `cuaslab` portal. Designer's calls:

| Handle | Node class | Autonomy | Reason |
|---|---|---|---|
| `pod1-bridge` | `POD` | `remote` | ADR 1092: a node inside our identity planes with its own local router. The enrolment SOP gives this command for a pod. `KID` (a gateway for devices that do not speak the fabric) was considered and not chosen: the pod has a router of its own, which is the mark of `POD`. |
| `host-fusion` | `FUSION` | `supervised` | The SOP: a system that produces derived data from other systems' data. |
| `host-recorder` | `FUSION` | `supervised` | No class describes a reader that writes nothing. The recorder needs a certificate from this CA to connect at all. `FUSION` is the nearest class and the recorder belongs to the host's fusion function. This is recorded as a gap in goat's vocabulary, not as a fit. |

- The custodian is `richard@cuaslab.lan`. The operator sets a grant first: quota 5, affiliation `cuaslab-lab`. The affiliation is a free label; the portal requires one and checks only that one custodian always spells it the same way.
- Each enrolment returns the anchor, an API key, a bundle URL and a bundle token. The bundle is a `.tar.gz` that holds `<anchor>-cert.pem`, `<anchor>-key.pem`, the root certificate and, when the portal is configured for it, a `.cbor` profile (read from `ops/goat-zenoh-portal/internal/certmint/certmint.go` at `e44e893d`; not yet run).
- The portal contract, read from `ops/goat-zenoh-portal/internal/api/` in the checkout `../goatlite-test/goatcore` at `e44e893d`, and not yet run except where noted:

  | Call | Body or path | Answer |
  |---|---|---|
  | every call | header `Authorization: Bearer <operator key>` | `GET /api/whoami` and `GET /api/machines` were run with this header and answered 200. |
  | `GET /api/machines/grant/<custodian>` | | 404 `no_grant` when there is none (run). |
  | `POST /api/machines/grant` | `{"custodian", "quota", "affiliation"}` | 200 with the quota. Operator only. |
  | `POST /api/machines/enroll` | `{"machine_handle", "node_class", "autonomy", "custodian"}` | `slot_id` (the anchor), `api_key`, `bundle_url`, `bundle_token`, `mesh_groups`, `mesh_note`. An operator may name a custodian other than itself. |
  | `GET <portal><bundle_url>` | the path is `/api/org-bundle/<anchor>/<token>` and carries the token; no header is needed | the `.tar.gz` |

- The certificate's common name is the anchor. That is what the router's slot subject matches.
- With mesh key minting off, the response carries no setup key. The script must accept that.
- Enrolment is not repeatable for free: a handle that holds a live slot is refused with `alias_taken`. The script therefore reads `GET /api/machines` first and skips a handle that exists and whose files are present. Revoking a machine is not part of the script.

### 6.3 The enrolment script

`goat4/enroll.sh` (name is the builder's). It runs on the Mac.

Who runs it (designer's call): the building agent writes the script and may run every read-only call. The first run that writes to `cuaslab` (the grant and the three enrolments) is a gated task: the agent stops and asks Richard, and runs it only after he says yes in that turn. The operator key is read from `CUASLAB_PORTAL_OPERATOR_API_KEY` in `../goatlite-test/goatcore/.envrc.local.d/secrets.env`; the script takes that file path as an argument. An agent session's `curl` trusts the `cuaslab` root through the macOS keychain (measured), and can run `goat --context cuaslab` for G4-10 (measured on 2026-11-18 for `goat hello`).

1. Read the operator key from a file path or an environment variable that the caller gives. It never prints the key and never writes it.
2. `POST /api/machines/grant` for the custodian, if `GET /api/machines/grant/<custodian>` says there is none.
3. For each of the three handles: `POST /api/machines/enroll`, download the bundle, and unpack the certificate, the key and the root.
4. Write the files below `zenoh/goat4/pki/`, with mode 0600 for keys, under fixed names that the overlay mounts: `ca.pem`, `pod1.pem`, `pod1.key`, `host-fusion.pem`, `host-fusion.key`, `host-recorder.pem`, `host-recorder.key`.
5. Write `zenoh/goat4/goat4.env` with `FABRIC_POD1_ID`, `FABRIC_HOST_FUSION_ID` and `FABRIC_HOST_RECORDER_ID`, the same variable names as `goat1.env`. The project name differs from step 1, so the container and network names in the step 1 README commands (`apex-goat1_mesh`, `apex-goat1-pod-bridge-1`, `apex-goat1_host`) change with it.
6. Print the three handles with their anchors and nothing secret.

`zenoh/goat4/` is added to `.gitignore`. API keys and bundle tokens are not kept: the rig does not use them.

### 6.4 The overlay

`docker-compose.goat4.yml`, used as `docker compose --env-file zenoh/goat1/goat1.env --env-file zenoh/goat4/goat4.env -f docker-compose.goat1.yml -f docker-compose.goat4.yml`, with its own project name so that it cannot be confused with the step 1 rig. `goat4.env` comes second so that its three anchors win.

It changes only:

- `pod-bridge`: `FABRIC_CONNECT=tls/192.168.64.4:7447`, the three fabric file mounts, and no dependency on `zenohd-fabric`.
- `host-fusion` and `host-recorder`: `ZENOH_CONNECT=tls/192.168.64.4:7447`, the CA and the certificate mounts, and no dependency on `zenohd-fabric`.
- `zenohd-fabric`: not started.
- Networks: the pod's network `pod1` becomes internal, so that the pod bridge can reach the outside only through `mesh`. Then `docker network disconnect <project>_mesh <pod bridge>` cuts the fabric link as in step 1 and leaves the pod side up. `mesh` and `host` keep outbound access.

The pod side of the rig still needs `goatgen.py` and `goat1/registry.toml` for the pod router, the pod CA and the pod slots. Its fabric output (the stand-in router file and the test fabric certificates) is made and not used.

### 6.5 Acceptance checks

The same checks as step 1, with the same numbers, so the two records can be read side by side.

| ID | Check | Pass on `cuaslab` | Difference from step 1 |
|---|---|---|---|
| G4-01 | Version pairing | A client with the 1.10.2 binding and a slot certificate opens a session to the `cuaslab` router, publishes below its anchor, subscribes, and declares a liveliness token that a second client sees. | The router is `1.9.0-modified`, not stock. No router restart: we do not restart `cuaslab`. |
| G4-02 | Tracks and alerts up | As G1-02. | none |
| G4-03 | Registration | As G1-03. | none |
| G4-04 | Task down | As G1-04. | none |
| G4-05 | Access | The pod's slot writes below the host's anchor, and the host's slot writes below the pod's anchor. In each case a subscriber on that key receives nothing, while a control write below the writer's own anchor arrives. The pod-internal part of G1-05 runs as in step 1. | The proof is absence at a subscriber, not a router log line. A subscription to `**` is allowed on `cuaslab` and is not tested as a refusal. |
| G4-06 | Short outage | As G1-06. | none |
| G4-07 | Long outage | As G1-07. | none |
| G4-08 | Old task | The unit test of G1-08. | none |
| G4-09 | Join with no restart | As G1-09. This is inside the pod. | none |
| G4-10 | `goat` client | `goat --context cuaslab sub` on the Mac, with the founder's identity, receives one sample or more below the pod's anchor. | A real goatnet identity and the released `goat` binary, not a build from source. |
| G4-11 | No regression | The unit suite passes with no warning. The step 1 rig starts and passes its G1-02 and G1-03. | The step 1 rig is the regression target. |
| G4-12 | Configuration only | `git diff goat --diff-filter=MDR --stat -- emulators/` is empty: no existing file below `emulators/` is modified, deleted or renamed. The diff of the branch holds only the overlay, the script, `.gitignore`, documents and new probe files, and the record lists each new file. | New |
| G4-13 | Clocks | The offset between the Colima VM and the goatlite VM is measured with a method that is good to 50 ms, and recorded. No pass value: this is a measurement for roadmap gap 6. | New |

Identities for the probes (designer's call): no machine beyond the three is enrolled. G4-01 runs before the rig starts, with the certificate of `pod1-bridge` as the writer and the certificate of `host-recorder` as the reader. The fabric part of G4-05 runs while the rig's three fabric clients are stopped, with the certificates of `pod1-bridge` and `host-fusion` as writers and `host-recorder` as the reader. Whether `cuaslab` accepts two sessions with one certificate is not measured and no check depends on it.

The step 1 rig and the step 4 rig run one at a time. Both use `zenoh/goat1/` and `goat1/registry.toml`.

A check that cannot run is recorded as unknown. If G4-01 fails on publish or liveliness, the step stops there and the failure is the result.

### 6.6 Documents and evidence

- `docs/acceptance-goat4.md`, in the form of `docs/acceptance-goat1.md`. Each statement says whether it was measured in a run, read from a trace, or taken from source.
- `docs/evidence/goat4/` with an index and a quote checker, as `docs/evidence/goat1/`.
- A step 4 section in `README-goat.md`, with commands that run as pasted into zsh.
- `docs/goat-context.md`: the corrections of phase 0 (sections 2.11, 5.2, 8.2, 8.8, the line numbers of the router template, the `goat` version, the router image).
- `docs/goat-roadmap.md`: section 3 status, section 4 step 4, section 6 decisions, section 7.
- Evidence files hold anchors and handles. They hold no key, token, or salt. The quote checker of this step also fails if an evidence file matches the pattern of an API key or a private key.

## 7. Left to the builder

- File and variable names where this document does not fix them.
- How the overlay removes the dependency on `zenohd-fabric` and keeps that service from starting, with the Compose version in Colima.
- The probes. G4-01 needs a new probe file: `emulators/probe_pairing.py` takes no arguments, writes the fixed keys `probe/a` and `probe/live/x` outside any anchor, and uses one certificate for both sessions, so `cuaslab` would drop its writes. `emulators/probe_access.py` takes its key as an argument and can be used for G4-05 as it is; its pass rule in step 1 read the router's trace, so the step 4 rule of section 6.5 (absence at a subscriber, with a control write) is applied around it. A new probe file below `emulators/` is allowed and is named in the G4-12 record; a change to an existing file is not.
- The method of the clock measurement in G4-13.
- The order and text of the README section.

## 8. Risks and decisions made in advance

| Risk | Decision |
|---|---|
| The bundle does not hold plain PEM files, or the download needs a credential we do not have. | Stop after the first enrolment and report. One slot is used. Do not try a second way without a decision. |
| An enrolment fails half way and leaves a slot with no files. | The script reports the handle and stops. Cleaning it up (`goat machine revoke` or the portal's revoke API) is a separate, approved act. |
| A program must change to pass a check (for example the bridge expects a name, not an address, or a key form is refused). | Record the finding with evidence. Do not change the program. Ask Richard. |
| The router drops a denied write silently, so G4-05 cannot tell "denied" from "lost". | The control write in the same run, by the same client, on its own anchor, must arrive. |
| The route between the two VMs is lost: Colima gets another address, or the Mac stops forwarding. | The README section starts with a reachability check and names the two route files. |
| Clock offset between the VMs makes the router rewrite timestamps and a fusion node reject messages. | Measure first (G4-13). If messages are rejected for time, record it; widening the window is a program change and needs a decision. |
| `cuaslab` keeps the three slots and the grant after the step. | Accepted. They are listed in the record so that a later session can revoke them. |

## 9. Known limits that this step keeps

- The path to the router has no WireGuard, and the pod is not a mesh peer. On a goatnet with a mesh the pod's host would hold class `POD` in the mesh and reach the router through it (ADR 1092).
- Nothing revokes a slot certificate on this path. goat's cut-off at this stage is mesh revocation, and the rig is not on the mesh.
- The pod bridge connects to the core router. goat's moon pod contract names an ingress gateway; a goatlite has none.
- Pod, host clients and the goatnet are on one Mac. The host clients run in the same VM as the pod.
- All the limits of `docs/acceptance-goat1.md` that concern the programs remain, because no program changes.
