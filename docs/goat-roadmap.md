# goat proof of concept: the six steps

This file records the whole plan of work, so that a later session can continue from it. It holds what was decided, what is open, and how a step is started. It was written on 2026-11-11 and must be updated when a step ends.

Related files:

| File | Content |
|---|---|
| `docs/goat-context.md` | The goat rules that this work follows, with a source for each rule |
| `docs/superpowers/specs/2026-11-11-goat-step1-pod-to-host-design.md` | The design of step 1 |
| `docs/superpowers/plans/2026-11-11-goat-step1-pod-to-host.md` | The plan of step 1: 12 tasks, checks G1-01 to G1-11 |
| `docs/acceptance-goat1.md` | The evidence of step 1 (made during step 1) |
| `docs/acceptance.md` | The evidence of the earlier work, stages 1 to 4 |

## 1. End goal

A real goatnet with three parts:

- **Pod 1** operates at the edge. It has sensors, effectors, a pod fusion node and its own local Zenoh router.
- **The host** operates in a cloud or a data centre. It has the fabric router, a host fusion node with a display, and a recorder.
- **The external host** operates in another cloud. It belongs to a different sovereign and gets only the data that the host releases.

goat is the open source project of United States Army Europe and Africa. Its source is in `../usareur-af/`.

## 2. Rules for all steps

- All steps use the branch `goat`. Nothing is pushed unless Richard says so.
- Each step is its own project: one design, one plan, one acceptance file.
- The earlier rigs must continue to work: the TCP-only rig and stages 1 to 4.
- The key rules of goat are the most important part (Richard, 2026-11-11). Read `docs/goat-context.md` before each design.
- Real goat software comes in where it helps and where the effort is manageable. Step 1 uses only goat's rules, goat's Zenoh version, goat's access list checker and the `goat` command line tool. The real goatnet comes in step 4.
- A check that could not run is recorded as unknown. It is never recorded as a pass.

## 3. The steps

| Step | Content | Host side | Status on 2026-11-11 |
|---|---|---|---|
| 1 | Pod 1 to host | Our stand-in that follows goat's rules, on the Mac | Designed and planned. Execution started. |
| 2 | Stone Soup in the fusion node | Same | Not started |
| 3 | Billie adapter for a sensor with a vendor protocol | Same | Not started |
| 4 | The host on a real goatnet | goatlite on a cloud VM | Not started |
| 5 | Pod 2 | Real goatnet | Not started |
| 6 | External host, the second sovereign | goat federation | Not started |

Richard gave this order on 2026-11-11. One point is open: his message put the Billie adapter third in one place and second in another. This file uses third.

## 4. Each step

### Step 1: pod 1 to host

- **Purpose.** Show that the pod of stage 4 operates on a fabric that follows goat's rules.
- **New parts.** A pod bridge, a fabric router, a host fusion node with a display, a host recorder, one registry file and a generator for both routers.
- **Changed parts.** The pod fusion node sends status and alerts upward and acts on tasks from above. The pod router gets a slot pool, so a new sensor needs only a certificate and the router does not restart.
- **Results to show.** Tracks and alerts at the host, registration acknowledged by the host, a task from the host that reaches a sensor, a denied write outside a slot, a short and a long outage, `goat sub` reading the pod's tracks, and a sensor that joins with no router restart.
- **Decisions.** Section 6 lists them.
- **Details.** The design and the plan named above.

### Step 2: Stone Soup in the fusion node

- **What exists.** The Stone Soup source is in `../Stone-Soup` (version 1.9.1 plus 103 commits). The fusion node today is `emulators/fake_fusion_node.py`, which joins detections within 100 m into one track.
- **Earlier note.** Acceptance item T-13 of `docs/acceptance.md`: replay a trial through Stone Soup's `SapientDetectionReader`. The adapter is not built.
- **Open questions for Richard.**
  1. Which fusion node gets Stone Soup: the pod fusion node, the host fusion node, or both? The drawing of 11 November shows the pod fusion node. That is a guess.
  2. What must the step show: better tracks than the toy fusion, or only that Stone Soup operates in the rig?
  3. Is the input live emulator data or a recorded trial?

### Step 3: Billie adapter

- **What exists.** Open Billie is in `../usareur-af/open-billie`. Its SAPIENT encoder makes detection reports only. It makes no registration, status report, task or alert. Its data goes one way.
- **What is needed.** An adapter with a registration shim: it gives the Billie sensor a registration, status reports and presence in the pod, and it rejects tasks.
- **Known problem.** A pod slot gives a sensor its node ID. Billie makes its own node ID. The step must decide how the two fit. Section 4.2 of the step 1 design has this limit.
- **Earlier test plan** (notes of 9 November): first build Billie's translator and a synthetic sensor package, capture its SAPIENT output and validate it with Apex's validator. Then connect it to the pod router, see the fusion node accept its detections, stop the node and see it removed, and confirm that a task is refused.
- **Link to step 1.** The Billie sensor is the first real test of "join with no router restart".

### Step 4: the host on a real goatnet

- **What changes.** A goatlite replaces our stand-in fabric router and its test CA. A goatlite is a real goatnet on one machine: mesh, identity service, CA, fabric router and portal.
- **What it needs.** One Ubuntu 24.04 machine with 4 cores and 16 GB. A workstation with Rust, Go, Ansible and Playwright. A run of fourteen phases.
- **What step 1 prepared.** Each fabric client takes five facts from configuration: the CA file, its certificate, its key, the router endpoint and its anchor. The move must change configuration only.
- **Known gaps** (`docs/goat-context.md` section 8).
  1. No procedure was found that gives a system a slot identity on a goatlite.
  2. A goatlite is a LAN network. The pod and the host must be in one network, for example one VPC.
  3. No statement was found that the machine can be arm64. Use an x86 VM.
  4. If check G1-01 of step 1 failed, the Zenoh version pairing is an open item here.
- **Open questions for Richard.** Which cloud account and region, and who pays for the VM.

### Step 5: pod 2

- **What changes.** A second pod with its own router, its own CA, its own salt and the site name `p2`. Its bridge takes a second slot on the fabric.
- **What must be shown.** The host fuses tracks from two pods. A node ID belongs to the anchor that registered it, so one pod cannot speak for the other.
- **Prepared in step 1.** The registry can describe more than one pod, and the fabric pool has free slots.

### Step 6: the external host

- **What changes.** The host releases a set of data to a second sovereign.
- **goat's method** (`docs/goat-context.md` section 4). The host publishes to `release/<set>/...`. A republisher publishes each sample again as `from/<us>/<set>/...`. One edge router for each partner sends it through a tunnel. The partner's router accepts our writes only below `from/<us>/**`.
- **Where to learn it.** goat's tutorials `03-boundary-node.md` and `04-two-sovereigns.md` in `../usareur-af/goatcore/docs/tutorials/`.
- **Known gaps.** goat's one-command federation is not built. Encryption to grants across the boundary is not usable yet.
- **Open questions for Richard.** Is the second sovereign a second goatnet that we operate, in another account? Which data set is released?

## 5. How to start a step

1. Read this file, `docs/goat-context.md`, and the acceptance file of the step before.
2. Update the goat source in `../usareur-af/` and check what changed in goat since the commit that `docs/goat-context.md` names. goat is before version 1.0.
3. Ask Richard the open questions of the step. Draw the network and the data flow before the design.
4. Write the design in `docs/superpowers/specs/`. Let a fresh reviewer read it as a builder. Settle what the reviewer finds.
5. Write the plan in `docs/superpowers/plans/`, with numbered acceptance checks.
6. Execute the plan with one fresh implementer and one fresh reviewer for each task, and one review of the whole branch at the end.
7. Record the evidence in an acceptance file. Update section 3 and section 6 of this file.

Environment notes:

- Docker runs in Colima. Start it with `colima start`. The profile has 4 CPUs and 6 GiB.
- The unit suite runs in the emulator image:
  `docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -p no:cacheprovider -q -W error tests`
- The Mac has no Rust toolchain. Build goat tools in a container.
- An agent session that cannot read `~/.docker` must set `DOCKER_HOST` to the Colima socket, `unix://$HOME/.colima/default/docker.sock`, and `DOCKER_CONFIG` to a directory of its own.

## 6. Decisions so far

"Richard" means that he decided. "Designer" means that the assistant decided and Richard can overrule it.

| Date | Decision | By |
|---|---|---|
| 2026-11-11 | The end goal is a real goatnet, not only goat's design. | Richard |
| 2026-11-11 | The order of the six steps in section 3 | Richard |
| 2026-11-11 | One new branch, `goat`, for all steps | Richard |
| 2026-11-11 | Step 1 uses a stand-in host with goat's rules. The real goatnet comes in step 4. | Designer, delegated by Richard |
| 2026-11-11 | A slot pool at both routers in step 1 | Richard approved the proposal |
| 2026-11-11 | The pod reaches the fabric through a bridge process, not a router-to-router link. A router cannot rename a key. | Designer |
| 2026-11-11 | Keys on the fabric follow goat's taxonomy. The last part is the SAPIENT node ID, not a track ID or a task ID, to keep the number of keys bounded (Zenoh issue 2825). | Designer |
| 2026-11-11 | A pod slot gives a sensor its node ID together with its certificate. | Designer |
| 2026-11-11 | One node bridge carries one legacy node and holds one slot. | Designer |
| 2026-11-11 | The host fusion node is the same program as the pod fusion node, with a link for the fabric keys. | Designer |
| 2026-11-11 | The host can task only the pod fusion node, which passes the command to its sensors. | Designer |
| 2026-11-11 | The pod fusion node raises one alert for each new track, because the emulator sensors raise none. | Designer |
| 2026-11-11 | If Zenoh 1.9.0 does not operate with the 1.10.2 binding, the fabric router uses 1.10.2 in step 1 and the failure is an open item for step 4. | Designer |
| 2026-11-11 | octo-pod is not used as our pod. It relays opaque bytes and rejects each task. Its bridge design is copied. | Designer |

## 7. What was done, in order

| Date | Work |
|---|---|
| 2026-11-08 to 09 | SAPIENT over Zenoh, stages 1 to 4, on branch `zenoh`. Evidence in `docs/acceptance.md`. |
| 2026-11-09 to 11 | Analysis of goatcore, Open Billie, octo-pod, the moon pod and goat's federation, from source. |
| 2026-11-11 | Brainstorm of this proof of concept. Drawings of the network and the data flow (dashboard artifacts `398f188ae09574fa` and `9e9103c14c8b5b71`; the reference drawing is `03f1c3fc36c6216c`). |
| 2026-11-11 | `docs/goat-context.md` written. Branch `goat` made from `zenoh`. |
| 2026-11-11 | Step 1 design and plan written and committed. Execution of the plan started. |
