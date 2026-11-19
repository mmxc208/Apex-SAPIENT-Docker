# Step 4b design: the host on its own machine

Date: 2026-11-19. Branch: `goat-step4b-host-vm`, made from `goat-step4-cuaslab` at `311b304`. Status: designed.

Read first: `docs/goat-roadmap.md`, `docs/goat-context.md` (sections 2.7, 4.1 and gap 14), `docs/acceptance-goat4.md`, and the step 4 design `docs/superpowers/specs/2026-11-18-goat-step4-cuaslab-design.md`. This document uses the words of those files and does not repeat them.

## 1. Intent

Step 4 ran the pod, the host fusion node and the host recorder in one VM (Colima). Its record names this as a limit: the two fusion nodes share one clock, one Docker engine and one route to the router. So three things were never tested: a clock difference between the pod and the host, a cut of the real link, and a host that loses its own link.

Step 4b moves the host fusion node and the host recorder to a third VM. The pod stays in Colima. The goatnet `cuaslab` stays as it is. Then pod, goatnet and host are on three machines, as in a deployment, and the three untested things can be measured.

Step 4b is about realism of the test. It does not make the rig conform to more of goat's ADRs: the four points of `docs/goat-context.md` gap 14 stay as they are (section 9).

Richard's instruction of 2026-11-19: where the design has an open question, take the designer's recommendation. Each such call is marked "designer's call" below and listed in section 8.

## 2. The three machines

| Machine | VM | Address | Runs |
|---|---|---|---|
| Pod | Colima `default` | `192.168.64.5` | the pod router, the pod fusion node, the sensors, the pod recorder, the pod bridge |
| Goatnet | Lima `goatlite` | `192.168.64.4` | `cuaslab`: the fabric router on `tls/192.168.64.4:7447`, the portal and the rest |
| Host | Lima `goathost` (new) | given by vzNAT, `192.168.64.x` | the host fusion node, the host recorder |

All three are on one Mac, on the vzNAT network. vzNAT isolates the VMs from each other at layer 2, so each pair that must talk needs a route through the Mac at `192.168.64.1` on both VMs (measured in step 4). The pairs:

- Colima and goatlite: the routes of step 4, unchanged.
- goathost and goatlite: two new routes.
- Colima and goathost: **no route**. The pod and the host have no direct path. Everything between them crosses the fabric router.

## 3. Goals, non-goals, anti-goals

### Goals

1. The host fusion node and the host recorder run in `goathost` and nowhere else; the pod services run in Colima and nowhere else.
2. The rig works as in step 4: tracks, alerts and the registration go up, and a task comes down and is acknowledged.
3. One host task is followed hop by hop, with a different observer at each hop, and a control with the bridge stopped.
4. The clock difference between the pod and the host is measured from the data itself, and the tolerance of the rig to a clock difference is measured by setting one.
5. A cut of the real link on the pod's side, short and long, and a cut on the host's side.
6. The step 4 rig and the step 1 rig still work.

### Non-goals

- No mesh, no WireGuard. On a goatlite the router listens on the LAN address and the box is not a mesh peer, so a mesh join would not carry the data (`docs/goat-context.md` gap 14).
- No revocation test. No new enrolment. No change to the portal or the router of `cuaslab`.
- No fabric identity for the sensors or the pod fusion node. That is a later step.
- No change to a program below `emulators/`, and no change to `docker-compose.goat1.yml` or `docker-compose.goat4.yml`.
- No Stone Soup, no Billie adapter, no second pod.

### Anti-goals

- The pod's key in the host VM, or a host key that the pod's containers can read as a result of this step.
- A direct path between the pod and the host.
- A test that leaves a clock set wrong, a route removed, or a time service stopped. Each such test restores the state in a trap and checks it afterwards.
- A change that disturbs the other projects that share the Colima VM. The only route touched in Colima is the one to `192.168.64.4`.

## 4. Constraints

- Sudo on the Mac is Richard's. Nothing in this design needs it: Lima creates a VM without it, and the commands inside a VM use that VM's own sudo.
- A change on the goatlite box outside goatbuilder is reported. This design makes one: a route file (section 6.2).
- No key, token, certificate body or bundle link is printed or saved in evidence.
- Nothing is pushed.
- The rules of `docs/goat-roadmap.md` section 2 hold: evidence files with a quote checker, a record that says how each statement is known, README commands that run when pasted into zsh.

## 5. Approaches

**A. A third VM for the host (chosen; designer's call).** Three roles on three machines. `cuaslab` is untouched except for one route file. Cost: one small VM, two routes, the image loaded into it, and a way to start two services on a second Docker engine.

**B. The host in the goatlite box.** No new VM. Rejected: a goatnet's box runs the goatnet's own services, and the host is a user of the goatnet. The host would reach the router on the same machine, so one network hop less would be tested than today. It also installs containers on the box outside goatbuilder.

**C. The host as Python processes on the Mac.** Cheapest. Rejected: the host would not run the image the pod runs, and the Mac is also the router between the VMs, so a cut on the host's side could not be told from a cut of everything.

Within A, how the two host services are defined:

**A1. The same compose files, a second Docker engine (chosen; designer's call).** The step 1 file and the step 4 overlay stay the single definition of every service. A new overlay changes only where the host services' bind mounts come from. One helper starts the pod services on Colima's engine; another starts the two host services on `goathost`'s engine.

**A2. A separate compose file for the host.** Rejected: it copies the definition of two services, and the copy can drift from the one that step 4 tested.

## 6. Design

### 6.1 Parts

| Part | New or changed | What it does |
|---|---|---|
| `goat4b/goathost.yaml` | new | The Lima definition of the host VM: Ubuntu 24.04 arm64, 2 CPUs, 4 GiB, 20 GiB, vzNAT, rootful Docker, no mount of the Mac's files. Its provision script sets the route to `192.168.64.4` through `192.168.64.1` and keeps it over a restart. |
| `goat4b/host-vm.sh` | new | Functions to source: make the VM, load the image, copy the host's files, add and check the routes, and remove all of it again. |
| `docker-compose.goat4b.yml` | new | An overlay over the step 1 file and the step 4 overlay. It changes the bind-mount sources of `host-fusion` and `host-recorder` to paths in the host VM. Nothing else. |
| `goat4b/dg4b.sh` | new | `dg4b_pod` and `dg4b_host` (section 6.3), and `goat4b_ready`. |
| `goat4b/probe_*.py` or one file | new, outside `emulators/` | The observers that the checks need and no service gives: a subscriber on the pod router that prints each sample's key and task ID, and a reader of a recorder's file that follows one task ID. |
| `goat4b/test_*.py` | new | Tests for the shell helpers and the probes that can run with no VM. |
| `.gitignore` | changed | Adds `zenoh/goat4b/` if the step makes local state there. |

### 6.2 The host VM

- **Files in the VM.** `host-vm.sh` copies to `/opt/apex-host/` in the VM: the directory `emulators/`, and from `zenoh/goat4/pki/` exactly five files: `ca.pem`, `host-fusion.pem`, `host-fusion.key`, `host-recorder.pem`, `host-recorder.key`. It never copies `pod1.pem` or `pod1.key`. The key files are readable by root only.
- **The image.** `apex-sapient:4.2.0` is saved from Colima's engine and loaded into the VM's engine. The check is that the image ID is the same on both.
- **Identity.** The two host certificates of step 4 are used again. Nothing is asked of `cuaslab`.
- **Routes.** In `goathost`: `192.168.64.4/32 via 192.168.64.1`. In `goatlite`: `<goathost address>/32 via 192.168.64.1`, in a new file `/etc/netplan/92-goathost-route.yaml`, beside the file of step 4. This is the one change on the goatlite box; the record reports it and says how to remove it.
- **The address.** vzNAT gives the address when the VM is made. `host-vm.sh` reads it from the VM and uses it; no file in git holds it.
- **MTU.** If the VM cannot fetch what Docker's install needs, set the MTU of its interface to 1400 as on `goatlite` (designer's call; the builder tries without first).

### 6.3 Two engines, one definition

```text
dg4b_pod  = docker compose -p apex-goat4  ... -f goat1.yml -f goat4.yml -f goat4b.yml   on Colima's engine
dg4b_host = docker compose -p apex-goat4b ... -f goat1.yml -f goat4.yml -f goat4b.yml   on goathost's engine
```

- `dg4b_pod up -d` names the pod services: `zenohd-pod fusion-node radar camera vehicle bridge-node recorder pod-bridge`. It never names `host-fusion` or `host-recorder`.
- `dg4b_host up -d --no-deps host-fusion host-recorder` starts only those two.
- **How `dg4b_host` reaches the engine (designer's call).** First choice: the Docker socket that Lima forwards to the Mac, with `DOCKER_HOST` set in the function's own subshell. If the agent's sandbox cannot use that socket, the fallback is to copy the three compose files and the two env files to `/opt/apex-host/` and run `docker compose` in the VM through `limactl shell`. The builder measures which one works and the README shows that one.
- `goat4b_ready` exits 0 only if: `goat4_ready` of step 4 passes; the VM runs; the image is there with the same ID; the five files are there and no `pod1.*` file is; a TCP connection from the VM to `192.168.64.4:7447` opens; no `apex-goat4` container of `host-fusion` or `host-recorder` runs in Colima; and no `apex-goat1` container runs.

### 6.4 Acceptance checks

Each check is recorded in `docs/acceptance-goat4b.md` with its evidence file, what was measured and where it falls short. A check that could not run is unknown.

| Check | What | Passes when |
|---|---|---|
| G4B-01 | Placement | `host-fusion` and `host-recorder` run in `goathost` only; the eight pod services run in Colima only; `/opt/apex-host/` holds the five files and no `pod1.*` |
| G4B-02 | No path around the router | From `goathost`: no TCP connection to Colima's address or to the pod router. From the pod fusion node and the radar: none to the fabric router. From a pod container: none to `goathost`. Only the bridge is on both of the pod's networks |
| G4B-03 | Up | As G4-02 and G4-03: the host logs tracks, an alert and the pod fusion node's registration; the host recorder's four counts are 0 |
| G4B-04 | A task, hop by hop | One task ID is seen (1) in the host's send line, (2) by the host recorder on the fabric, (4) by a subscriber on the pod router, (5) in the pod fusion node's receive line, and its acknowledgement is seen at the host. (3) The bridge's `down` count rises. With the bridge stopped for 45 s: host tasks sent ≥ 2, seen on the pod router 0, received by the pod fusion node 0, acknowledged 0; after a start, all resume |
| G4B-05 | Clocks, measured | Two measurements. (a) The offset of each of the three VMs from the Mac, by the method of G4-13. (b) From the host recorder's file: for each record, the time the host received it minus the time in the message. Reported: count, minimum, median, maximum, and how many are below 0 (a message that looks as if from the future). No pass value |
| G4B-06 | Clock tolerance | With the time service of `goathost` stopped, its clock is stepped to a set of offsets. For each, 40 s of traffic: detection reports the host accepted and rejected, tasks the pod accepted and rejected. Judged for each message, not for each step: a message's apparent age is the time the host recorder received it minus the time in the message. A step whose whole range of ages is inside the validator's window (`[-0.9, 0.1]` s, so an age from -0.1 to 0.9 s; read from `emulators/fake_fusion_node.py`) passes with 0 rejections. A step whose whole range is outside passes when no message is accepted. A step with ages on both sides is reported and not judged. Also needed: traffic is accepted again after the clock is restored, with no restart |
| G4B-07 | The pod's link cut | The route from Colima to `192.168.64.4` is replaced by a blackhole. Short (30 s): the pod keeps working, the bridge logs lost and back, no new registration. Long (longer than the host's hold time, which `dg4b_host` sets to 20 s for this check with `HOST_HOLD_SECONDS`): the host removes the node, then the pod registers again |
| G4B-08 | The host's link cut | The route from `goathost` to `192.168.64.4` is replaced by a blackhole for 30 s. Passes when the host receives tracks again within 60 s of the restore, with no restart of a service. If it does not, the check fails and the record says what happened; no program is changed in this step |
| G4B-09 | No regression | The unit suite: 454 passed. The step 4 rig (`dg4`, all in Colima) starts and G4-02's counts hold. The step 1 rig starts and G1-02 and G1-03 hold |
| G4B-10 | Configuration only | `git diff goat-step4-cuaslab --diff-filter=MDR --stat -- emulators/ docker-compose.goat1.yml docker-compose.goat4.yml goat4/` prints nothing |
| G4B-11 | Latency, measured | From the host recorder's file: for each task, the time from the task on the fabric to its acknowledgement on the fabric. Reported: count, minimum, median, maximum. No pass value |

Offsets for G4B-06 (designer's call): host clock behind by 0.05, 0.15 and 0.30 s (the pod's messages look as if from the future; the window allows 0.1 s), and ahead by 0.5, 0.8 and 1.2 s (they look old; the window allows 0.9 s). The natural offset from G4B-05 is added to each when the result is read. The same steps test the other direction: the host's tasks at the pod.

### 6.5 Documents and evidence

- `docs/acceptance-goat4b.md`: the record.
- `docs/evidence/goat4b/`: the evidence files, an index `README.md`, and `check-quotes.py`, with the secret rule of step 4.
- `README-goat.md`: a section "Goat step 4b: the host on its own machine", with commands that run when pasted. The commands are run as written before the step ends.
- `docs/goat-roadmap.md`: a step 4b entry in sections 3 and 4, the decisions in section 6, the order in section 7. `docs/goat-context.md`: only if a run shows something about goat.
- `docs/explainers/goat-step4b/index.html` with `preview.png`, and a row in `docs/explainers/README.md`: an interactive page on what 4b changed, what was measured and what was learned. It follows the page of step 4 and holds no key, token, host name of the Mac or user path.

## 7. Left to the builder

- The exact Lima definition and how Docker is installed in the VM.
- How a clock is stepped and the time service stopped and restored in `goathost`, and how to show that it was restored.
- The form of the probes, as long as they print no payload that holds a secret and no file below `emulators/` changes.
- The order of the live checks, as long as every check starts from a rig that `goat4b_ready` passed.

## 8. Risks and decisions made in advance

| Risk | Decision |
|---|---|
| The clock of the VM cannot be stepped, or the hypervisor sets it back at once | Record G4B-06 as unknown, with what was tried. G4B-05 still stands |
| The forwarded Docker socket cannot be used from the agent's sandbox | Use the fallback of section 6.3 |
| The host services do not reconnect after G4B-08 | The check fails and is recorded; a restart brings the rig back for the checks after it |
| vzNAT gives `goathost` an address that another VM holds, or the address changes after a restart | `host-vm.sh` reads the address each time; the route file on `goatlite` is rewritten by the same function and the change is reported |
| A test is interrupted with a clock stepped or a route removed | Each such test restores in a trap; `goat4b_ready` and a final check in the record show the state |
| The natural clock difference already makes the host or the pod reject messages, before any clock is stepped | This is a result, not a fault of the rig. Run 60 s as the VM came up and record the rejections and the ages (G4B-05) first. Then stop the time service of `goathost` and step its clock so that the median age of the pod's messages is between 0.2 and 0.4 s, inside the window with room on both sides. G4B-03, 04, 07, 08 and 11 run in that state, and the record says so. G4B-06 counts its offsets from that state |
| Colima and `goathost` can reach each other on-link, because vzNAT does not isolate this pair | Record what was measured. Then add a drop rule in `goathost`, in both directions, for Colima's address; `host-vm.sh` sets it, removes it and checks it, and `goat4b_ready` requires it. G4B-02 then passes by this rule and the record says so. Nothing is changed in Colima |
| "No TCP connection to the pod router" passes for the wrong reason, since the pod router publishes no port | G4B-02 also tries a port that does answer on Colima's address from the Mac (a control), so a pass shows the path is closed, not that nothing listens |
| The subscriber on the pod router needs an identity | It uses the pod recorder's certificate, in a one-off container of the `recorder` service. A second session with that certificate worked on the pod router on 2026-11-19 (from the session). No new slot |
| Memory on the Mac | `goathost` takes 4 GiB of 64; no decision needed |

Designer's calls taken under Richard's instruction: approach A and A1; the VM's size and name; reuse of the two host certificates; no route between Colima and `goathost`; the socket first and the shell as fallback; the offsets of G4B-06; a failing G4B-08 is recorded and not fixed; the branch is stacked on `goat-step4-cuaslab`; the four rows above that a reviewer of this design asked about (a clock difference at the start, an on-link path, the control port, the subscriber's certificate), and the rule of G4B-06 for each message.

## 9. Known limits that this step keeps

- **The four points of gap 14.** The pod's machine is not a mesh peer; nothing can cut a machine off; the sensors and the pod fusion node have no fabric identity; every source appears as the pod.
- **One Mac.** Three VMs on one Mac share its clock source and its network stack. A clock difference is set by hand, not met in the field. The Mac routes every packet between the VMs.
- **The keys are on the Mac.** `zenoh/goat4/pki/` on the Mac holds all three keys, and the pod's containers in Colima get theirs by a bind mount from it. Step 4b keeps the pod's key out of the host VM; it does not take the host's keys off the Mac.
- **Reading is not limited on `cuaslab`,** and all limits of `docs/acceptance-goat4.md` that concern the programs remain.
