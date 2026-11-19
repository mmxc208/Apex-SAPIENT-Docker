# Goat Step 4b: The Host on Its Own Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the host fusion node and the host recorder of the step 4 rig in a third VM, `goathost`, and record eleven acceptance checks (G4B-01 to G4B-11), among them a clock difference and a cut of the real link.

**Architecture:** A new Lima VM holds a Docker engine, the image, the directory `emulators/` and the host's five certificate files. One new overlay compose file changes only the bind-mount sources of the two host services. Two shell helpers run the same three compose files on two engines: the pod services on Colima, the two host services on `goathost`. No program and no step 1 or step 4 file changes.

**Tech Stack:** zsh on macOS, Lima 2.3.0 (`limactl`), Docker Compose on Colima and in the VM, image `apex-sapient:4.2.0` (Python 3.11, `eclipse-zenoh==1.10.2`), `python3` standard library for tests and readers, the `cuaslab` router at `tls/192.168.64.4:7447`.

**Spec:** `docs/superpowers/specs/2026-11-19-goat-step4b-host-vm-design.md`. It cites `docs/goat-roadmap.md`, `docs/goat-context.md`, `docs/acceptance-goat4.md` and the step 4 design. Executors read the spec and `docs/acceptance-goat4.md`.

## Global Constraints

- Work on branch `goat-step4b-host-vm`. Commit after each task. Never push. Each commit message ends with a `Co-Authored-By: Claude <model> <noreply@anthropic.com>` line that names the model that did the work.
- These must not change: every existing file below `emulators/`, `docker-compose.goat1.yml`, `docker-compose.goat4.yml`, every file below `goat4/`. New files go below `goat4b/`, plus `docker-compose.goat4b.yml` at the root.
- If a check can pass only with a change to a program, stop, save the evidence, and report. Do not make the change.
- `cuaslab`: no call to the portal, no enrolment, no revoke, no change to the router. The only change in the `goatlite` VM is the file `/etc/netplan/92-goathost-route.yaml` and the matching `ip route`; Task 2 makes it and the record reports it. Never run `goatbuilder`.
- Never run `sudo` on the Mac. `sudo` inside a VM (`limactl shell <vm> sudo ...`, `colima ssh -- sudo ...`) is allowed.
- In Colima, the only state touched outside the compose project is the route to `192.168.64.4`. Other projects share that VM: stop or remove no container that is not of project `apex-goat4` or `apex-goat1`.
- Never print, log, commit or save in evidence: a private key, a certificate body, the operator key, an API key, a bundle token or link. Never copy `pod1.pem` or `pod1.key` into `goathost`.
- VM name: `goathost`. Path in the VM: `/opt/apex-host/` with `emulators/`, `pki/ca.pem`, `pki/host-fusion.pem`, `pki/host-fusion.key`, `pki/host-recorder.pem`, `pki/host-recorder.key`. Key files: mode 0600, owner root.
- Compose projects: `apex-goat4` on Colima (pod services), `apex-goat4b` on `goathost` (host services). Pod services, exact: `zenohd-pod fusion-node radar camera vehicle bridge-node recorder pod-bridge`. Host services, exact: `host-fusion host-recorder`.
- Router endpoint `tls/192.168.64.4:7447`; the Mac on vzNAT is `192.168.64.1`; Colima is `192.168.64.5`.
- Validator window, read from `emulators/fake_fusion_node.py`: `messageTimestampRange: [-0.9, 0.1]`. "Apparent age" of a message = the recorder's receive time `t` minus the message's `timestamp`. Accepted range of apparent age: -0.1 s to 0.9 s.
- Every test that steps a clock, stops a time service, or replaces a route restores the state in a shell `trap` and then prints a check of the restored state. A task ends only after that check is in an evidence file.
- A check that could not run is recorded as unknown, never as a pass. A quoted output line must be in a file below `docs/evidence/goat4b/`, character for character. Evidence files are named `task-<n>-<what>.txt` and start with the UTC date and `git rev-parse --short HEAD`.
- An agent session cannot read `~/.docker`. Before any docker command against Colima it sources `.superpowers/sdd/2026-11-18-goat-step4-cuaslab/docker-env.sh`.
- A background process that a subagent starts is killed when its turn ends. A subagent that makes a live run stays in its turn until the run has printed its end marker.
- Unit suite, from the repo root: `docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -p no:cacheprovider -q -W error tests`. Expected: `454 passed`.
- The VM is started from the agent's runtime and may stop when that runtime ends. Every task that needs it starts with `limactl list` and starts the VM if it is stopped, then reads its address again.

## Review Focus

1. The pod's key reaches the host VM, by a wide copy of `zenoh/goat4/pki/`. Expected: the copy names five files; a test fails if `pod1` appears in the list; `goat4b_ready` fails if a `pod1.*` file is in `/opt/apex-host/`. (Tasks 1 and 2)
2. `dg4b_host` or `dg4b_pod` starts a service on the wrong engine. Expected: `dg4b_pod up` with no service names, or with a host service name, is refused; `dg4b_host up` accepts only the two host services. (Task 1)
3. A test is interrupted with the clock of `goathost` stepped, its time service stopped, or a route replaced by a blackhole. Expected: the trap restores; a separate command `g4b_state` prints the time service state, the clock offset and both routes, and the record holds its output at the end of every live task. (Tasks 3 and 4)
4. The address of `goathost` changes after a restart and the route on `goatlite` points at the old one. Expected: `goat4b_ready` compares the VM's address with the route file on `goatlite` and fails with both values. (Tasks 1 and 2)
5. A clock check is judged from too few messages or from a mixed step. Expected: the reader prints the count and the range of apparent ages of every step; a step with fewer than 20 messages, or with ages on both sides of a limit, is reported as not judged. (Tasks 3 and 4)

---

## File Structure

| File | Responsibility |
|---|---|
| `goat4b/goathost.yaml` | The Lima definition of the host VM |
| `goat4b/host-vm.sh` | Functions that make, fill, check and remove the host VM and its routes |
| `docker-compose.goat4b.yml` | Overlay: bind-mount sources of the two host services |
| `goat4b/dg4b.sh` | `dg4b_pod`, `dg4b_host`, `goat4b_ready`, `g4b_state` |
| `goat4b/readers.py` | Pure functions over recorder files and logs: follow a task, apparent ages, task latency, rejection counts |
| `goat4b/pod_sub.py` | A subscriber for the pod router that prints one line for each sample |
| `goat4b/test_goat4b.py` | Tests of the shell helpers' refusals, the merged configuration and `readers.py` |
| `docs/evidence/goat4b/` | Evidence files, `README.md`, `check-quotes.py` |
| `docs/acceptance-goat4b.md` | The record |
| `docs/explainers/goat-step4b/index.html`, `preview.png` | The interactive page |

---

### Task 1: The VM definition, the overlay and the helpers, tested with no VM

**Files:**
- Create: `goat4b/goathost.yaml`, `goat4b/host-vm.sh`, `docker-compose.goat4b.yml`, `goat4b/dg4b.sh`, `goat4b/test_goat4b.py`

**Interfaces:**
- Consumes: `goat4/dg4.sh` (`dg4`, `goat4_ready`), sourced, not edited.
- Produces, in `goat4b/host-vm.sh` (zsh and bash functions, sourced from the repo root):
  - `g4b_vm_create` — `limactl start --name=goathost --tty=false goat4b/goathost.yaml` if no VM of that name exists; starts it if stopped.
  - `g4b_vm_addr` — prints the VM's `192.168.64.x` address, nothing else; exit 1 if none.
  - `g4b_vm_load_image` — saves `apex-sapient:4.2.0` from Colima and loads it in the VM; prints both image IDs.
  - `g4b_vm_sync` — copies `emulators/` and the five files to `/opt/apex-host/`; sets modes; the file list is the array `G4B_HOST_FILES`.
  - `g4b_routes_up` — sets `192.168.64.4/32 via 192.168.64.1` in the VM (kept over a restart) and `<vm addr>/32 via 192.168.64.1` on `goatlite`, with `/etc/netplan/92-goathost-route.yaml`; prints each file it wrote. `g4b_routes_check` — prints both routes and exits 1 if either is missing or the `goatlite` route names another address.
  - `g4b_vm_remove` — prints what it would remove and removes the route file and route on `goatlite`, then deletes the VM, only when called with the argument `--yes`.
- Produces, in `goat4b/dg4b.sh`:
  - `dg4b_pod <compose args>` — project `apex-goat4`, Colima's engine, files goat1, goat4, goat4b. For `up`: refused unless every service named is a pod service and at least one is named; `dg4b_pod up-all` is `up -d` with the eight pod services.
  - `dg4b_host <compose args>` — project `apex-goat4b`, the VM's engine. For `up`: refused unless every service named is a host service; always adds `--no-deps`. `HOST_HOLD_SECONDS` in the caller's environment reaches the service.
  - `goat4b_ready` — the conditions of spec section 6.3, one line for each failure, exit 0 only if all hold.
  - `g4b_state` — prints, one per line: the time service state of `goathost`, the offset of each VM from the Mac in ms, the route from Colima to `192.168.64.4`, the route from `goathost` to `192.168.64.4`. Changes nothing.
  - `G4B_ENGINE` — `socket` or `shell`: how `dg4b_host` reaches the engine (spec 6.3). Task 2 measures which works and sets the default.

- [ ] **Step 1: Write the failing tests** in `goat4b/test_goat4b.py` (`unittest`, run with `python3 -m unittest goat4b/test_goat4b.py`; shell functions are called through `zsh -fc '. goat4/dg4.sh; . goat4b/dg4b.sh; . goat4b/host-vm.sh; ...'` with `docker`, `limactl` and `colima` replaced by stubs on `PATH` that record their arguments):
  - `test_host_files_are_exactly_five_and_no_pod_key`: `G4B_HOST_FILES` equals the five names of Global Constraints; no element contains `pod1`.
  - `test_dg4b_pod_up_refuses_no_service`, `test_dg4b_pod_up_refuses_host_service` (`host-fusion`), `test_dg4b_pod_up_all_names_eight_services`.
  - `test_dg4b_host_up_refuses_pod_service` (`radar`), `test_dg4b_host_up_adds_no_deps`, `test_dg4b_host_passes_hold_seconds`.
  - `test_projects_differ`: the recorded `-p` is `apex-goat4` for the pod and `apex-goat4b` for the host.
  - `test_overlay_changes_only_host_mount_sources`: parse `docker-compose.goat4b.yml` with a minimal reader (or `docker compose config` if the stub is not in use for this test); its services are exactly `host-fusion` and `host-recorder`; each has only the key `volumes`; every source starts with `/opt/apex-host/`; the targets are `/emulators`, `/certs/ca.pem`, and the service's `.pem` and `.key`.
  - `test_vm_remove_needs_yes`: `g4b_vm_remove` with no argument calls no `limactl delete`.
  - `test_ready_fails_on_pod_key_in_vm`, `test_ready_fails_on_route_address_mismatch` (stubs print a `pod1.key` listing, and two different addresses); each expects exit 1 and a line that names the problem.
- [ ] **Step 2: Run them.** Expected: FAIL, the files do not exist.
- [ ] **Step 3: Write the five files.** `goathost.yaml`: Ubuntu 24.04 arm64 image as in `~/.lima/goatlite/lima.yaml`, `cpus: 2`, `memory: 4GiB`, `disk: 20GiB`, `networks: [{vzNAT: true}]`, `mounts: []`, containerd off, a system provision script that installs rootful Docker and writes the route as a netplan file. The overlay holds only the two services' `volumes`.
- [ ] **Step 4: Run the tests.** Expected: all pass. Also run `python3 -m unittest goat4/test_enroll.py` (26 OK) and `git diff goat-step4-cuaslab --stat -- emulators/ docker-compose.goat1.yml docker-compose.goat4.yml goat4/` (prints nothing).
- [ ] **Step 5: Commit** — `feat(goat4b): the host VM definition, the overlay and the two-engine helpers`.

### Task 2: Make the host VM; checks G4B-01 and G4B-02

**Files:**
- Modify: `goat4b/host-vm.sh`, `goat4b/dg4b.sh`, `goat4b/goathost.yaml` only where the live run shows a defect; `goat4b/test_goat4b.py` for each such fix
- Create: `docs/evidence/goat4b/task-2-*.txt`

**Interfaces:**
- Consumes: Task 1's functions.
- Produces: a running `goathost` that `goat4b_ready` passes; the default of `G4B_ENGINE`; evidence files `task-2-vm.txt`, `task-2-ready.txt`, `task-2-g4b-01.txt`, `task-2-g4b-02.txt`, `task-2-goatlite-change.txt`.

- [ ] **Step 1: Make the VM.** `g4b_vm_create`, `g4b_vm_addr`. If the Docker install cannot fetch, set the interface MTU to 1400 in the VM as on `goatlite` and say so in `task-2-vm.txt`.
- [ ] **Step 2: Fill it.** `g4b_vm_load_image` (the two image IDs are equal), `g4b_vm_sync`, `g4b_routes_up`, `g4b_routes_check`. Save to `task-2-goatlite-change.txt` the route file's path and content on `goatlite` and the `ip route` line, with the commands that remove them.
- [ ] **Step 3: Choose the engine path.** Try `G4B_ENGINE=socket`: `dg4b_host version` from the agent's shell. If it fails, use `shell` and record why. Set the default in `dg4b.sh` and add a test for the chosen default.
- [ ] **Step 4: `goat4b_ready`** passes; then make each of these fail once and save the line: a `pod1.key` placed in `/opt/apex-host/pki/` (an empty file of that name, then removed), a wrong address in the `goatlite` route, the VM stopped. Restore after each. → `task-2-ready.txt`.
- [ ] **Step 5: Start the rig.** `dg4b_pod up-all`, then `dg4b_host up -d host-fusion host-recorder`.
- [ ] **Step 6: G4B-01.** Save: the services and states on each engine; that no `host-fusion` or `host-recorder` container exists on Colima and no pod service on `goathost`; `sudo ls -l /opt/apex-host/pki` in the VM (names and modes only). → `task-2-g4b-01.txt`.
- [ ] **Step 7: G4B-02.** Measure and save, each as one line `from -> to: CONNECTED | cannot connect: <error>`:
  - control: from the Mac to Colima's address on a port that answers (find one with `nc -z`; if none, start a one-off listener container on Colima with a published port and remove it after);
  - from `goathost` (VM shell and inside `host-fusion`) to Colima's address on that control port;
  - from `goathost` to the pod router's container address;
  - from the `fusion-node` and `radar` containers to `192.168.64.4:7447`;
  - from the `pod-bridge` container to the address of `goathost` on port 22;
  - the networks of `fusion-node`, `zenohd-pod`, `pod-bridge`, `host-fusion`.
  If Colima and `goathost` reach each other: save that result as `task-2-g4b-02-before.txt`, add `g4b_isolate_up`, `g4b_isolate_down` and `g4b_isolate_check` to `host-vm.sh` (an `iptables` drop in `goathost` for Colima's address, both directions, kept over a restart), make `goat4b_ready` require it, add tests, and measure again.
- [ ] **Step 8: Commit** — `feat(goat4b): the host VM runs the host services; G4B-01 and G4B-02`.

### Task 3: The readers and the pod subscriber; checks G4B-03, G4B-04, G4B-05, G4B-11

**Files:**
- Create: `goat4b/readers.py`, `goat4b/pod_sub.py`, `docs/evidence/goat4b/task-3-*.txt`
- Modify: `goat4b/test_goat4b.py`

**Interfaces:**
- Consumes: the rig of Task 2; the recorder's JSON-lines format (one object per line with `t`, `key`, `kind`, `node_id`, `anchor`, `site`, `msg`; read `emulators/recorder.py`).
- Produces, in `goat4b/readers.py` (standard library only; each function takes an iterable of parsed records or log lines, so it is tested with no rig; a `main` reads a file path or stdin):
  - `follow_task(records, task_id_suffix) -> list[dict]` — the task and its acknowledgement: `t`, `key`, `from`, `to`, `content`, `task_id`.
  - `apparent_ages(records, since=None, until=None, kinds=None) -> dict` — `count`, `min`, `median`, `max`, `below_zero`, `outside_window` (age < -0.1 or > 0.9), in seconds; age = `t` minus `msg.timestamp`.
  - `task_latency(records) -> dict` — for each task with an acknowledgement of the same `task_id`: ack `t` minus task `t`; `count`, `min`, `median`, `max` in ms; `unacknowledged`.
  - `rejections(log_lines, since=None, until=None) -> dict` — counts of lines with `invalid message from` and with `invalid message from above dropped`.
  - `judge_step(ages: dict, accepted: int, rejected: int) -> str` — `pass`, `fail` or `not judged`, by the rule of spec 6.4 for G4B-06 and Review Focus 5 (fewer than 20 messages, or ages on both sides of a limit: `not judged`).
- Produces `goat4b/pod_sub.py <key expression> <seconds>`: run in a one-off container of the `recorder` service with `PYTHONPATH=/emulators` and the file mounted; prints for each sample `HH:MM:SS.mmm <key> | from <8> to <8> | <content> <task_id>` and at the end `pod sub: <n> samples on <expr> in <s> s`. It prints no payload.

- [ ] **Step 1: Write the failing tests** for the five functions, with records built in the test:
  - `follow_task` finds a task and its ack by a 6-character suffix and ignores another task;
  - `apparent_ages`: three records with ages -0.05, 0.2, 1.0 → `count 3`, `min -0.05`, `median 0.2`, `max 1.0`, `below_zero 1`, `outside_window 1`;
  - `task_latency`: two tasks, one acknowledged 7 ms later → `count 1`, `median 7`, `unacknowledged 1`;
  - `rejections` counts each of the two line forms and honours `since`;
  - `judge_step`: all ages inside and 0 rejected → `pass`; all inside and 3 rejected → `fail`; all outside and 0 accepted → `pass`; all outside and 5 accepted → `fail`; ages on both sides → `not judged`; count 5 → `not judged`.
- [ ] **Step 2: Run them** (FAIL), **write `readers.py` and `pod_sub.py`**, run again (pass).
- [ ] **Step 3: The state as the VM came up (G4B-05, first part).** With the rig running 60 s and no clock touched: `g4b_state`; `apparent_ages` over the host recorder's file for the pod's anchor; `rejections` in the logs of `host-fusion` and `fusion-node`. → `task-3-g4b-05-natural.txt`. This is a result whatever it shows.
- [ ] **Step 4: Discipline the clock only if needed.** If Step 3 shows a rejection, or a median age outside 0.2 to 0.4 s would make later checks fail (any `outside_window` > 0): stop the time service of `goathost`, step its clock so the median age is between 0.2 and 0.4 s, and save the commands, the before and after of `g4b_state` and of `apparent_ages`. → `task-3-clock-set.txt`. If Step 3 shows no rejection and `outside_window 0`, leave the clock alone and say so in that file. Add to `host-vm.sh`, with tests of their refusals: `g4b_clock_step <seconds>`, `g4b_clock_restore` (starts the time service again and waits until the offset is back), used by Task 4.
- [ ] **Step 5: G4B-03.** The lines of G4-02 and G4-03 from the two engines, and the host recorder's four counts. → `task-3-g4b-03.txt`.
- [ ] **Step 6: G4B-04.** For one `look_at` task: the host's send line; `follow_task` on the host recorder's file; the bridge's counter line; `pod_sub.py 'h1/p1/fusion/down/**' 45`; the pod fusion node's receive line; the host's acknowledgement line. Then the control: `dg4b_pod stop pod-bridge`, 45 s with `pod_sub.py`, counts of host tasks sent, seen on the pod router, received by the pod fusion node, acknowledged, and the pod's own detection lines; `dg4b_pod start pod-bridge`, 45 s, the same counts. → `task-3-g4b-04.txt`.
- [ ] **Step 7: G4B-05, second part, and G4B-11.** After at least 5 minutes of traffic: the offsets of the three VMs from the Mac by the method of G4-13 (30 rounds each); `apparent_ages` for the pod's anchor; `task_latency`. → `task-3-g4b-05.txt`, `task-3-g4b-11.txt`.
- [ ] **Step 8:** `g4b_state` → `task-3-state-end.txt`. **Commit** — `feat(goat4b): readers and a pod subscriber; G4B-03, 04, 05 and 11`.

### Task 4: Checks G4B-06, G4B-07 and G4B-08

**Files:**
- Create: `docs/evidence/goat4b/task-4-*.txt`
- Modify: `goat4b/host-vm.sh` and `goat4b/test_goat4b.py` only for a defect the runs show

**Interfaces:**
- Consumes: `g4b_clock_step`, `g4b_clock_restore`, `g4b_state`, `readers.py`, the rig.
- Produces: the three checks' evidence, and a rig in the state of the end of Task 3.

- [ ] **Step 1: G4B-06.** From the state of Task 3 (call its median age the base). For each offset in the order `-0.05 -0.15 -0.30 +0.5 +0.8 +1.2` s (negative: the host's clock behind, so the pod's messages look younger or from the future): `g4b_clock_step`, wait 5 s, then 40 s of traffic; save for that window `apparent_ages` (pod's anchor, host recorder), the host's `rejections`, the count of the pod fusion node's detection records that reached the host recorder, the pod's `rejections` of messages from above, the host tasks sent and acknowledged, and `judge_step` for each direction. After the last step: `g4b_clock_restore` (or back to the state of Task 3 Step 4 if the clock was disciplined there), 60 s, and the same numbers: traffic accepted, with the containers' `StartedAt` unchanged. All in a script with a `trap` that restores. → `task-4-g4b-06.txt`. If the clock cannot be stepped or does not stay stepped for 45 s: record what was tried and that G4B-06 is unknown.
- [ ] **Step 2: G4B-07, short.** `colima ssh -- sudo ip route replace blackhole 192.168.64.4/32` for 30 s, then the route of step 4 back (read it first and restore exactly that), in a `trap`. Save: the times; the bridge's lost and back lines; lines with `lost` or `cannot reach` in the pod; the pod fusion node's detection lines during the cut; the host's detection lines in 25 s after; new registrations. Wait 60 s before the cut, as the README of step 4 does. → `task-4-g4b-07-short.txt`.
- [ ] **Step 3: G4B-07, long.** `dg4b_host down`, then `HOST_HOLD_SECONDS=20 dg4b_host up -d host-fusion host-recorder`; wait for the registration; the same blackhole for 40 s; save the host's `gone for 20 s; removed` line, its registration request, the pod's registration and the acknowledgement. Then bring the host services back with the default hold time. → `task-4-g4b-07-long.txt`.
- [ ] **Step 4: G4B-08.** In `goathost`: `sudo ip route replace blackhole 192.168.64.4/32` for 30 s, then the route back, in a `trap`. Save: the host services' log lines during and after; the time of the first detection line at the host after the restore; the containers' `StartedAt` before and after. Pass: a detection line within 60 s of the restore and `StartedAt` unchanged. If it fails: save the logs, mark the check failed, restart the two host services and confirm G4B-03's lines again. → `task-4-g4b-08.txt`.
- [ ] **Step 5:** `g4b_state` and `g4b_routes_check` → `task-4-state-end.txt`. **Commit** — `test(goat4b): G4B-06 clock tolerance, G4B-07 and G4B-08 link cuts`.

### Task 5: Checks G4B-09 and G4B-10

**Files:**
- Create: `docs/evidence/goat4b/task-5-*.txt`

- [ ] **Step 1:** `dg4b_host down`, `dg4b_pod down`. Both projects have no container on either engine.
- [ ] **Step 2: The unit suite.** Expected `454 passed`. → `task-5-unit-suite.txt`. Also `python3 -m unittest goat4/test_enroll.py goat4b/test_goat4b.py`.
- [ ] **Step 3: The step 4 rig.** `. goat4/dg4.sh && goat4_ready && dg4 up -d`; after 90 s the lines of G4-02 and G4-03 and the recorder's four counts; `dg4 down`. → `task-5-step4-rig.txt`.
- [ ] **Step 4: The step 1 rig**, with its own commands from `README-goat.md` steps 1 to 3; G1-02 and G1-03 lines; `dg down`. → `task-5-step1-rig.txt`.
- [ ] **Step 5: G4B-10.** `git diff goat-step4-cuaslab --diff-filter=MDR --stat -- emulators/ docker-compose.goat1.yml docker-compose.goat4.yml goat4/` and `git diff goat-step4-cuaslab --name-status`. → `task-5-g4b-10.txt`.
- [ ] **Step 6: Commit** — `test(goat4b): G4B-09 no regression, G4B-10 configuration only`.

### Task 6: The record, the quote checker and the documents

**Files:**
- Create: `docs/acceptance-goat4b.md`, `docs/evidence/goat4b/README.md`, `docs/evidence/goat4b/check-quotes.py`, `docs/evidence/goat4b/readme-run.txt`
- Modify: `README-goat.md`, `docs/goat-roadmap.md`, `docs/goat-context.md` (only if a run showed something about goat), `docs/superpowers/specs/2026-11-19-goat-step4b-host-vm-design.md` (status line only)

- [ ] **Step 1: `check-quotes.py`**, in the form of `docs/evidence/goat4/check-quotes.py`, with its secret rule; it checks the quoted lines of `docs/acceptance-goat4b.md` and of the step 4b section of `README-goat.md` against `docs/evidence/goat4b/`. It must fail on a line that no file holds (show this once with a scratch copy) and exit 0 on the finished documents.
- [ ] **Step 2: The record**, in the form of `docs/acceptance-goat4.md`: runs and evidence with commits; a summary table of G4B-01 to G4B-11; one entry for each check with what was measured and "Falls short"; differences from step 4; what happened that the plan did not foresee; not done; known limits (spec section 9 and what the runs added); what step 4b left on the machines (the VM, the route file on `goatlite`, any rule in `goathost`) and how to remove it.
- [ ] **Step 3: The README section** "Goat step 4b: the host on its own machine": make the VM, fill it, the gate, start on two engines, each check's commands, stop, remove. Each start block is gated on `goat4b_ready`.
- [ ] **Step 4: Run the README section as written**, as one `zsh -f` script with stdin at `/dev/null`, from a state with the VM present and both projects down, through G4B-04 and the stop. → `readme-run.txt`. Fix the README where a block does not run, and say in the record how many blocks ran and how many printed what the README shows.
- [ ] **Step 5: The roadmap**: a row and an entry for step 4b in sections 3 and 4, the designer's calls in section 6, the order in section 7.
- [ ] **Step 6:** `python3 docs/evidence/goat4b/check-quotes.py` and `python3 docs/evidence/goat4/check-quotes.py` exit 0; both rigs down; `g4b_state`. **Commit** — `docs(goat4b): the acceptance record, the README section and the roadmap`.

### Task 7: The explainer page

**Files:**
- Create: `docs/explainers/goat-step4b/index.html`, `docs/explainers/goat-step4b/preview.png`
- Modify: `docs/explainers/README.md`, `README-goat.md` (one table row)

**Interfaces:**
- Consumes: `docs/acceptance-goat4b.md` (every number on the page comes from it), `docs/explainers/goat-step4/index.html` (the page to follow in look, structure and script style).

- [ ] **Step 1: Write the page.** One self-contained file, no network request, the style and tab script of the step 4 page. Tabs: Overview (why 4b, three machines, the main results); The three machines (a clickable diagram: pod VM, goatnet VM, host VM, the Mac that routes, with a highlight for "no direct path"); A task hop by hop (a step-through with the measured lines of G4B-04 and the control); Clocks (the natural difference, the window, the steps of G4B-06 as a small interactive strip that shows accepted or rejected for each offset, from the measured numbers); Link cuts (G4B-07 and G4B-08 as timelines); What was tested (each check opens to "what was measured", "where it falls short", evidence file, as on the step 4 page); ADR fit (the table of what conforms and the four points that do not, and that 4b changes none of them); Left over (the VM, the route file, how to remove).
- [ ] **Step 2: Check it.** `node --check` on the page's script; no match for a key shape, the Mac's host name, a user path or a mesh address; every number on the page is in `docs/acceptance-goat4b.md`.
- [ ] **Step 3: Render** three tabs with a headless Chromium (software rendering flags as needed) and look at each image; save one as `preview.png`.
- [ ] **Step 4:** the row in `docs/explainers/README.md` and in `README-goat.md`; `check-quotes.py` of both steps still exit 0. **Commit** — `docs: the explainer page for goat step 4b`.
