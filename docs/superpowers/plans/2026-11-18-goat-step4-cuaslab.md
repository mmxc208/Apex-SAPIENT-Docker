# Goat Step 4: The Step 1 Rig on cuaslab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the step 1 rig against the real goatnet `cuaslab` with slot identities from its portal, by configuration only, and record thirteen acceptance checks (G4-01 to G4-13).

**Architecture:** An enrolment script on the Mac asks the `cuaslab` portal for three slot identities and writes their files and one env file below `zenoh/goat4/`. An overlay compose file, used on top of `docker-compose.goat1.yml`, points the pod bridge, the host fusion node and the host recorder at the `cuaslab` router and does not start our stand-in router. No existing file below `emulators/` changes.

**Tech Stack:** zsh and `curl` on macOS, `python3` standard library for the script's tests, Docker Compose 5.7.1 on Colima, image `apex-sapient:4.2.0` (Python 3.11, `eclipse-zenoh==1.10.2`), `goat` 0.5.19 on the Mac, the `cuaslab` router `zenohd v1.9.0-modified`.

**Spec:** `docs/superpowers/specs/2026-11-18-goat-step4-cuaslab-design.md`. It cites `docs/goat-roadmap.md`, `docs/goat-context.md` and `docs/acceptance-goat1.md`. Executors read all four.

## Global Constraints

- Work on branch `goat-step4-cuaslab`. Commit after each task. Never push. Each commit message ends with a `Co-Authored-By: Claude <model> <noreply@anthropic.com>` line that names the model that did the work.
- No existing file below `emulators/` is modified, deleted or renamed. New files there are allowed and are listed in the record. `docker-compose.goat1.yml`, `goat1/registry.toml` (as committed) and every file that the step 1 plan froze must not change.
- If a check can pass only with a change to a program, stop, save the evidence, and report. Do not make the change.
- `cuaslab` is written to only by Task 2, and only after Richard says yes in that turn. Every other task makes read-only calls. Never run `goatbuilder teardown`. Never change the router, the portal settings or a file in the goatlite VM.
- Never print, log, commit or save in evidence: the operator key, a slot private key, an API key, a bundle token, a bundle URL, the slot pool salt.
- Router endpoint: `tls/192.168.64.4:7447`. Portal: `https://portal.cuaslab.cuaslab.lan`. Portal calls use `curl` with the header `Authorization: Bearer <operator key>`.
- Operator key source: the line `CUASLAB_PORTAL_OPERATOR_API_KEY=` in `../goatlite-test/goatcore/.envrc.local.d/secrets.env`. Read that one line with `grep`; do not `source` the file.
- Machines, exact: `pod1-bridge` / `POD` / `remote`; `host-fusion` / `FUSION` / `supervised`; `host-recorder` / `FUSION` / `supervised`. Custodian `richard@cuaslab.lan`, quota 5, affiliation `cuaslab-lab`. No fourth machine.
- Files below `zenoh/goat4/` (ignored by git), exact names: `pki/ca.pem`, `pki/pod1.pem`, `pki/pod1.key`, `pki/host-fusion.pem`, `pki/host-fusion.key`, `pki/host-recorder.pem`, `pki/host-recorder.key`, `goat4.env`. Keys have mode 0600.
- `goat4.env` holds exactly `FABRIC_POD1_ID`, `FABRIC_HOST_FUSION_ID`, `FABRIC_HOST_RECORDER_ID`, each a 32-character lower-case hexadecimal anchor.
- Compose project name: `apex-goat4`. The step 1 rig (`apex-goat1`) and this rig run one at a time.
- A check that could not run is recorded as unknown, never as a pass. A quoted output line must be in a file below `docs/evidence/goat4/`, character for character.
- An agent session cannot read `~/.docker`. Before any docker command it sources `.superpowers/sdd/2026-11-18-goat-step4-cuaslab/docker-env.sh`, made in Task 1 in the form of the step 1 file beside it.
- Unit suite, from the repo root: `docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -p no:cacheprovider -q -W error tests`.

## Review Focus

1. The enrolment script is run again after a run that failed half way: a handle has a live slot at the portal and its files are missing. Expected: the script names the handle, enrols nothing, and exits non-zero. (Task 1)
2. A secret reaches the script's output or an evidence file. Expected: the script's output holds only handles and anchors; the quote checker fails on a secret pattern. (Tasks 1 and 7)
3. `goat4.env` is missing or stale and the step 1 anchors from `goat1.env` reach the clients. Expected: the rig does not start; the start helper refuses unless each anchor in `goat4.env` matches the common name of its certificate. (Task 4)
4. The route between the two VMs is gone (Colima has another address, or the Mac stopped forwarding). Expected: the reachability check fails with the address it tried, before any container starts. (Task 4)
5. A denied write cannot be told from a lost write. Expected: the access check counts as measured only when the control write of the same run arrived; otherwise it is unknown. (Task 5)

---

## File Structure

| File | Responsibility |
|---|---|
| `goat4/enroll.sh` | Create: grant, three enrolments, bundle download, files and `goat4.env`. The only writer to `cuaslab`. |
| `goat4/test_enroll.py` | Create: tests of `enroll.sh` against a fake portal on localhost. Standard library only. |
| `goat4/dg4.sh` | Create: defines `dg4`, the compose command of this rig, and `goat4_ready`, the checks before a start. |
| `docker-compose.goat4.yml` | Create: the overlay. Configuration only. |
| `emulators/probe_fabric_pairing.py` | Create: the G4-01 probe. |
| `.gitignore` | Modify: add `zenoh/goat4/`. |
| `docs/acceptance-goat4.md`, `docs/evidence/goat4/` | Create: the record, the evidence, `README.md` index, `check-quotes.py`. |
| `README-goat.md`, `docs/goat-context.md`, `docs/goat-roadmap.md` | Modify: step 4 section; the corrections of spec section 6.6; status and decisions. |

---

### Task 1: The enrolment script, tested against a fake portal

**Files:**
- Create: `goat4/enroll.sh`, `goat4/test_enroll.py`, `.superpowers/sdd/2026-11-18-goat-step4-cuaslab/docker-env.sh`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `goat4/enroll.sh <secrets-file> [--portal <url>] [--out <dir>]`. Defaults: portal `https://portal.cuaslab.cuaslab.lan`, out `zenoh/goat4`. Exit 0 when all three machines have their files and `goat4.env` is written. Output on success, exactly three lines of the form `<handle> <anchor>` and one line `wrote <out>/goat4.env`.
- Produces: the file names of Global Constraints.

- [ ] **Step 1: Write the failing tests** in `goat4/test_enroll.py` (`unittest`, run with the Mac's `python3`). A fake portal is a `http.server` on `127.0.0.1` that implements `GET /api/machines`, `GET /api/machines/grant/<c>`, `POST /api/machines/grant`, `POST /api/machines/enroll` and `GET /api/org-bundle/<anchor>/<token>`, checks the `Authorization: Bearer` header, records each request, and serves a `.tar.gz` with `<anchor>-cert.pem`, `<anchor>-key.pem` and `root-cert.pem`. The test certificate is made with `openssl` and has the anchor as common name. Tests and their assertions:

  - `test_fresh_run`: three enrol requests with the exact bodies of Global Constraints; one grant request `{"custodian":"richard@cuaslab.lan","quota":5,"affiliation":"cuaslab-lab"}`; the seven files exist; each key has mode 0600; `goat4.env` has the three variables with the fake anchors; exit 0.
  - `test_output_has_no_secret`: stdout and stderr hold none of: the operator key, each `api_key`, each `bundle_token`, the string `/api/org-bundle/`, `PRIVATE KEY`.
  - `test_second_run_enrols_nothing`: with the files present and the portal listing the three handles, zero enrol requests and exit 0.
  - `test_grant_exists_is_not_set_again`: when `GET /api/machines/grant/<c>` answers 200, zero grant requests.
  - `test_handle_live_but_files_missing`: the portal lists `host-fusion`, its files are absent. Exit non-zero, stderr names `host-fusion`, zero enrol requests for any handle.
  - `test_enrol_refused_stops`: the portal answers 409 `alias_taken` on the second enrolment. Exit non-zero, stderr names the handle and the portal's `code`, no third enrol request, no `goat4.env`.
  - `test_bundle_without_pem_stops`: the bundle holds no `-key.pem`. Exit non-zero after the first enrolment, no second enrol request.
  - `test_no_mesh_key_is_accepted`: the enrol answer has no `mesh_setup_key`. Exit 0.
  - `test_secrets_file_without_key`: the secrets file has no `CUASLAB_PORTAL_OPERATOR_API_KEY` line. Exit non-zero, no request made.

- [ ] **Step 2: Run** `python3 -m unittest goat4/test_enroll.py -v`. Expected: every test fails because `goat4/enroll.sh` does not exist.

- [ ] **Step 3: Implement `goat4/enroll.sh`** to the interface above. zsh or bash 3.2, `curl`, `tar`, `openssl`, `python3 -c` for JSON only. Order of work: read the key; list machines; decide per handle (present with files: skip; present without files: stop; absent: enrol); set the grant only if at least one handle must be enrolled and no grant exists; for each enrolment download and unpack into a temporary directory that is removed on exit, check that the certificate's common name equals `slot_id`, then move the files into place; write `goat4.env` last. The root goes to `pki/ca.pem` from the first bundle. Pass the key to `curl` through a header file or stdin, not on the command line.

- [ ] **Step 4: Run** `python3 -m unittest goat4/test_enroll.py -v`. Expected: 9 tests, OK.

- [ ] **Step 5: Add `zenoh/goat4/` to `.gitignore`** and make `docker-env.sh` (two `export` lines for `DOCKER_HOST` and `DOCKER_CONFIG`, with a `dockercfg/cli-plugins/docker-compose` link to `/opt/homebrew/bin/docker-compose`). Run `. .superpowers/sdd/2026-11-18-goat-step4-cuaslab/docker-env.sh && docker compose version`. Expected: `Docker Compose version 5.7.1` or newer.

- [ ] **Step 6: Commit** `goat4/enroll.sh`, `goat4/test_enroll.py`, `.gitignore`. Message: `feat(goat4): the enrolment script for a goatnet portal, with tests against a fake portal`.

### Task 2: Enrol the three machines on cuaslab (gated)

**Files:**
- Create: `docs/evidence/goat4/task-2-enrol.txt`, `docs/evidence/goat4/task-2-machines.txt`

**Interfaces:**
- Consumes: `goat4/enroll.sh` of Task 1.
- Produces: the files and `goat4.env` of Global Constraints, with real anchors.

- [ ] **Step 1: Read-only checks.** `GET /api/whoami` answers `operator: true`; `GET /api/machines` lists no machine with one of the three handles; `curl` reaches `192.168.64.4:7447`. Save nothing secret.
- [ ] **Step 2: Stop and ask Richard.** State that the next command sets a quota of 5 for `richard@cuaslab.lan` and uses three of the 1000 slots, and that an enrolment is undone only by a revoke. Continue only on a yes in that turn.
- [ ] **Step 3: Run** `goat4/enroll.sh ../goatlite-test/goatcore/.envrc.local.d/secrets.env 2>&1 | tee docs/evidence/goat4/task-2-enrol.txt`. Expected: the four lines of the Task 1 interface, exit 0. On any other result, stop and report (spec section 8); do not run it a second time.
- [ ] **Step 4: Verify.** For each of the three certificates: issuer `cuaslab goatlite CA`, common name equal to the anchor in `goat4.env`, `openssl verify -CAfile zenoh/goat4/pki/ca.pem` says OK. Save `GET /api/machines` with only `system_handle`, `slot_id`, `node_class`, `autonomy`, `custodian` and the quota fields to `task-2-machines.txt`. Run `grep -rEl 'PRIVATE KEY|sbq_|api_key|bundle_token|org-bundle' docs/evidence/goat4/`. Expected: no file.
- [ ] **Step 5: Commit** the two evidence files. Message: `docs(goat4): evidence of the enrolment of three machines on cuaslab`.

### Task 3: The pairing probe and check G4-01

**Files:**
- Create: `emulators/probe_fabric_pairing.py`, `docs/evidence/goat4/task-3-g4-01.txt`

**Interfaces:**
- Consumes: `open_session(connect, loop, log, tls_env_prefix)` and `ZenohSession.publish_raw`, `subscribe`, `declare_token`, `liveliness` of `emulators/zenoh_io.py`; the files of Task 2.
- Produces: `python probe_fabric_pairing.py <writer anchor>`. The writer's certificate comes from `ZENOH_TLS_CA`, `ZENOH_TLS_CERT`, `ZENOH_TLS_KEY`; the reader's from `READER_TLS_CA`, `READER_TLS_CERT`, `READER_TLS_KEY`; the router from `ZENOH_CONNECT`. It prints exactly three result lines and exits 0 only if all three are true:

  ```text
  session: writer <true|false> reader <true|false>
  put below anchor received: <n> of 5
  liveliness token seen by reader: <true|false>
  ```

- [ ] **Step 1: Write the probe.** The writer publishes five payloads on `<anchor>/telemetry/sapient/p1/v2/status_report/a0000009-0000-4000-8000-000000000009` and declares a token on `<anchor>/telemetry/sapient/p1/v2/live/a0000009-0000-4000-8000-000000000009`. The reader subscribes to `<anchor>/**` and to liveliness on the same expression before the writer starts. Wait 1 s after each declaration, as `probe_access.py` does. A session that does not open within 20 s is `false`, not a hang. The probe writes no file.
- [ ] **Step 2: Run it** in the image with the certificate of `pod1-bridge` as writer and of `host-recorder` as reader, on a Docker network with outbound access, with `zenoh/goat4/pki` and `emulators` mounted read-only. Save the whole output to `task-3-g4-01.txt`. Expected: `writer true reader true`, `5 of 5`, `true`.
- [ ] **Step 3: Decide.** If a line is not as expected, G4-01 fails: stop the plan here, keep the evidence, report. Otherwise continue.
- [ ] **Step 4: Commit** the probe and the evidence. Message: `feat(goat4): a pairing probe for a goatnet router, and check G4-01 on cuaslab`.

### Task 4: The overlay, the start helper, and checks G4-02 to G4-04

**Files:**
- Create: `docker-compose.goat4.yml`, `goat4/dg4.sh`, `docs/evidence/goat4/task-4-*.txt`

**Interfaces:**
- Consumes: the files of Task 2.
- Produces: after `. goat4/dg4.sh`, two functions:
  - `dg4 <compose args>` = `docker compose -p apex-goat4 --env-file zenoh/goat1/goat1.env --env-file zenoh/goat4/goat4.env -f docker-compose.goat1.yml -f docker-compose.goat4.yml <args>`
  - `goat4_ready`: exit 0 only if (a) the seven files and `goat4.env` exist, (b) each of the three anchors in `goat4.env` equals the common name of its certificate, (c) no anchor in `goat4.env` equals a `FABRIC_*_ID` of `goat1.env`, (d) a TCP connection from a container on the Colima VM to `192.168.64.4:7447` opens within 5 s, (e) no container of project `apex-goat1` runs. Each failure prints one line that names what failed and, for (d), the address.
- Produces: container names `apex-goat4-pod-bridge-1`, `apex-goat4-host-fusion-1`, `apex-goat4-host-recorder-1`; network `apex-goat4_mesh`.

- [ ] **Step 1: Write the overlay.** It holds only:
  - `zenohd-fabric`: `profiles: ["standin"]`, so it does not start.
  - `pod-bridge`: `depends_on: !override [zenohd-pod]`; `FABRIC_CONNECT: tls/192.168.64.4:7447`; the three fabric mounts with the same container paths as step 1 (`/certs/fabric/ca.pem`, `/certs/fabric/pod1.pem`, `/certs/fabric/pod1.key`) and sources below `./zenoh/goat4/pki/`.
  - `host-fusion` and `host-recorder`: `depends_on: !reset []`; `ZENOH_CONNECT: tls/192.168.64.4:7447`; the mounts `/certs/ca.pem`, `/certs/host-fusion.pem`, `/certs/host-fusion.key` (and the recorder's) with sources below `./zenoh/goat4/pki/`.
  - `networks: pod1: internal: true`.

  If Compose refuses a `!override` or `!reset` tag, use another way that leaves `docker-compose.goat1.yml` unchanged (spec section 7), and say which in the record.
- [ ] **Step 2: Check the merged configuration without starting anything.** `dg4 config` must show: no `zenohd-fabric` among the services that `dg4 config --services` lists; for `pod-bridge`, `FABRIC_CONNECT` as above and `FABRIC_ANCHOR` equal to `FABRIC_POD1_ID` of `goat4.env`; for `host-fusion`, `FABRIC_ANCHOR` equal to `FABRIC_HOST_FUSION_ID` of `goat4.env`; no mount source below `zenoh/goat1/pki/fabric/` in any of the three services; network `pod1` internal. Then move `goat4.env` aside and confirm that `goat4_ready` exits non-zero and names it; move it back. Then test (c) and (d) of `goat4_ready` with a copy of `goat1.env` as `goat4.env` and with a wrong address. Save the outputs.
- [ ] **Step 3: Start the rig.** `python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1`, `goat4_ready`, `dg4 up -d`. Wait as the step 1 README section does.
- [ ] **Step 4: G4-02, G4-03, G4-04.** Use the commands of steps 2 to 4 of the step 1 section of `README-goat.md`, with `dg4` for `dg` and the `apex-goat4` names. Pass rules are those of G1-02 to G1-04 in the step 1 design, section 5. The recorder line check of G4-02 uses the anchors of `goat4.env`. Save each output.
- [ ] **Step 5: Commit** the overlay, the helper and the evidence. Message: `feat(goat4): the overlay that puts the rig on cuaslab, and checks G4-02 to G4-04`.

### Task 5: Checks G4-05 to G4-10 and G4-13

**Files:**
- Create: `docs/evidence/goat4/task-5-*.txt`

**Interfaces:**
- Consumes: `dg4`, the rig of Task 4, `emulators/probe_access.py put <key>` and `sub <key expression> <seconds>` (unchanged).

- [ ] **Step 1: G4-05, fabric part.** Stop `pod-bridge`, `host-fusion` and `host-recorder`. With the certificate of `host-recorder`, run `probe_access.py sub '<host anchor>/**' 20` and, in the same 20 s, with the certificate of `pod1-bridge`, `put` once on `<host anchor>/task/p1/sapient/v2/task/<POD1_FUSION_NODE_ID>` (the denied write) and once on `<pod anchor>/telemetry/sapient/p1/v2/status_report/<probe node id>` while a second `sub '<pod anchor>/**' 20` runs (the control). Then the mirror: `host-fusion` writes below the pod's anchor, with its control below its own anchor. Result of each direction: `refused` if the reader counted 0 probe samples on the foreign anchor and 1 on the control; `unknown` if the control counted 0; `fail` if the foreign anchor counted 1 or more. Start the three clients again.
- [ ] **Step 2: G4-05, pod part.** As G1-05 inside the pod, with the step 1 commands and `dg4`.
- [ ] **Step 3: G4-06 and G4-07.** As steps 6 and 7 of the step 1 README section, with `docker network disconnect apex-goat4_mesh apex-goat4-pod-bridge-1` and the matching `connect`. Before the first disconnect, confirm that with `mesh` disconnected the bridge container cannot open `192.168.64.4:7447` (the `pod1` network is internal); if it can, stop and report.
- [ ] **Step 4: G4-08.** Run the unit test that step 1 names for G1-08 and save its output.
- [ ] **Step 5: G4-09.** As step 9 of the step 1 README section, with `dg4`. End with `git restore goat1/registry.toml` and `git status --short goat1/registry.toml` printing nothing.
- [ ] **Step 6: G4-10.** On the Mac, after `. ../goatlite-test/env.sh` in a subshell, subscribe with `goat --context cuaslab sub` to `<pod anchor>/**` for 30 s while the rig runs (take the exact flags from `goat sub --help`). Pass: one sample or more whose key starts with the pod's anchor. Save the output with payload bytes left out.
- [ ] **Step 7: G4-13.** Measure the clock offset of the Colima VM and of the goatlite VM against the Mac: 30 rounds each of reading the VM's clock (`date +%s.%N` through `colima ssh` and `limactl shell goatlite`) between two readings of the Mac's clock; keep the round with the shortest round trip; offset = VM time minus the middle of the two Mac readings; bound = half that round trip. Record both offsets, both bounds and their difference. If a bound is above 50 ms, record the value as measured with that bound, and say so.
- [ ] **Step 8: Stop the rig** with `dg4 down`. Commit the evidence. Message: `docs(goat4): evidence of checks G4-05 to G4-10 and G4-13`.

### Task 6: Checks G4-11 and G4-12

**Files:**
- Create: `docs/evidence/goat4/task-6-*.txt`

- [ ] **Step 1: The unit suite.** Run the command of Global Constraints. Expected: the same count of passed tests as on `goat` (454), no warning.
- [ ] **Step 2: The step 1 rig.** With `apex-goat4` down, start the step 1 rig with the commands of its README section and run its checks for G1-02 and G1-03. Stop it. Expected: both pass as in `docs/acceptance-goat1.md`.
- [ ] **Step 3: G4-12.** `git diff goat --diff-filter=MDR --stat -- emulators/` prints nothing. `git diff goat --name-status` lists only: the overlay, `goat4/`, `emulators/probe_fabric_pairing.py`, `.gitignore`, and files below `docs/` and `README-goat.md`. Save both outputs.
- [ ] **Step 4: Commit** the evidence. Message: `docs(goat4): evidence of checks G4-11 and G4-12`.

### Task 7: The record, the quote checker and the documents

**Files:**
- Create: `docs/acceptance-goat4.md`, `docs/evidence/goat4/README.md`, `docs/evidence/goat4/check-quotes.py`
- Modify: `README-goat.md`, `docs/goat-context.md`, `docs/goat-roadmap.md`

- [ ] **Step 1: The quote checker.** Copy the method of `docs/evidence/goat1/check-quotes.py` for `docs/acceptance-goat4.md` and the step 4 section of `README-goat.md`. Add one rule: exit non-zero if any file below `docs/evidence/goat4/` matches `PRIVATE KEY`, `sbq_[A-Za-z0-9_-]{20,}`, `api_key`, `bundle_token` or `/api/org-bundle/`. Test the rule once with a scratch file that holds `bundle_token`, see it fail, remove the file.
- [ ] **Step 2: `docs/acceptance-goat4.md`**, in the form of `docs/acceptance-goat1.md`: the runs with their commits, a summary table of G4-01 to G4-13 with pass, fail or unknown, one entry for each check with what was measured and where it falls short, the differences from step 1 (spec 6.5), the known limits (spec 9), and what stays on `cuaslab`: the grant and the three machines with their anchors, so that a later session can revoke them. Each statement says measured, read from a trace, or taken from source.
- [ ] **Step 3: `README-goat.md`**, a step 4 section: the reachability check and the two route files first, then the commands of this rig as they run when pasted into zsh. The enrolment command is shown with a note that it writes to the goatnet.
- [ ] **Step 4: `docs/goat-context.md`**: the corrections named in spec 6.6, each with its source file and the commit `e44e893d`. `docs/goat-roadmap.md`: the status of step 4 in section 3, the result in section 4, the decisions of 2026-11-18 in section 6 (the branch, the scope "as it is", approach A, the three classes, absence as the proof of a refusal), a line in section 7, and which of the nine gaps of step 4 are closed, measured or open.
- [ ] **Step 5: Run** `python3 docs/evidence/goat4/check-quotes.py` and `python3 docs/evidence/goat1/check-quotes.py`. Expected: both exit 0.
- [ ] **Step 6: Commit.** Message: `docs(goat4): the acceptance record of step 4, the run steps, and the updates to the context and the roadmap`.

### After the tasks

One review of the whole branch by a fresh reviewer on the most capable model: the diff against `goat`, the record against the evidence, and the five lines of Review Focus. Fixes go in as new commits. Nothing is pushed.
