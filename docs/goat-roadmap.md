# goat proof of concept: the six steps

This file records the whole plan of work, so that a later session can continue from it. It holds what was decided, what is open, and how a step is started. It was written on 2026-11-11 and must be updated when a step ends. It was last updated on 2026-11-12, at the end of step 1.

Related files:

| File | Content |
|---|---|
| `docs/goat-context.md` | The goat rules that this work follows, with a source for each rule |
| `docs/superpowers/specs/2026-11-11-goat-step1-pod-to-host-design.md` | The design of step 1 |
| `docs/superpowers/plans/2026-11-11-goat-step1-pod-to-host.md` | The plan of step 1: 12 tasks, checks G1-01 to G1-11 |
| `README-goat.md` | The entry page of the goat work: the drawings and the run steps of each step |
| `docs/explainers/` | The explainer pages: SAPIENT, SAPIENT over Zenoh, goat, and an interactive page on step 1 for a new team member. Open them in a browser. |
| `docs/acceptance-goat1.md` | The acceptance record of step 1: checks G1-01 to G1-11, the known limits, the open items |
| `docs/evidence/goat1/` | The saved outputs and logs that the record of step 1 quotes, with an index and a quote checker |
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
- A quoted log line or output line, in a record or in a README, must be in a saved evidence file, character for character. The evidence files of a step go into `docs/evidence/<step>/`, with an index and a quote checker (rule made in step 1, after a record quoted lines that no file held).
- A record says for each statement whether it was measured in a run, read from a trace, or taken from source code. It names, for each run, the commit it was made on top of and the first commit that holds what ran.
- The run steps of each step go into `README-goat.md`, as commands that run as they are when pasted into zsh.

## 3. The steps

| Step | Content | Host side | Status on 2026-11-12 |
|---|---|---|---|
| 1 | Pod 1 to host | Our stand-in that follows goat's rules, on the Mac | Done. Checks G1-01 to G1-11 pass (G1-08 by unit test only). The record lists the known limits. |
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
- **Result (2026-11-12).** All eleven checks pass in two whole runs with newly generated certificates. The first built the `goat` tool from an empty cache. The second, after the fixes of the final review, used the cached build. `goat sub`, built from goat's source at commit `cbf2cb7f`, read the pod's tracks from our fabric router with a slot certificate. A second radar joined the pod with a new certificate only; the pod router did not restart and its file did not change. The unit suite went from 265 to 454 tests. `docs/acceptance-goat1.md` has the evidence and the list of known limits.

### Step 2: Stone Soup in the fusion node

- **What exists.** The Stone Soup source is in `../Stone-Soup` (version 1.9.1 plus 103 commits). The fusion node today is `emulators/fake_fusion_node.py`, which joins detections within 100 m into one track.
- **Earlier note.** Acceptance item T-13 of `docs/acceptance.md`: replay a trial through Stone Soup's `SapientDetectionReader`. The adapter is not built.
- **Open questions for Richard.**
  1. Which fusion node gets Stone Soup: the pod fusion node, the host fusion node, or both? The drawing of 11 November shows the pod fusion node. That is a guess.
  2. What must the step show: better tracks than the toy fusion, or only that Stone Soup operates in the rig?
  3. Is the input live emulator data or a recorded trial?
- **Carried from step 1.** Two limits of the toy fusion are left for this step, because Stone Soup replaces that code path:
  1. A fusion node takes a detection from a node that has not registered. It was seen at the host in every long run. A gate must not apply to transport `tcp`, where the fusion node can start after the sensors have registered with Apex.
  2. A location that is not a number (NaN, infinity) passes Apex's validator and moves the first track of the list.

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
  4. The Zenoh version pairing is settled: check G1-01 passed, so our 1.10.2 binding operates with a 1.9.0 router.
  5. Session IDs. goat's ADR 1041 (status "Proposed") asks for a fixed router ID for each host and for source info on goat's own publishers, and goat's command line tool sets a publisher's session ID to its slot anchor. Step 1 sets no session ID. Decide what the pod bridge and the host fusion node do (`docs/goat-context.md` 2.11).
  6. Clocks. Both fusion nodes reject a message whose timestamp is more than 0.9 s behind or 0.1 s ahead of their clock. On a real mesh the two sides need clocks that agree, or a wider window for traffic that crosses the fabric.
  7. The goat client. Only `goat sub` was tried. goat's client does not verify the router's TLS name. A profile from a signed bundle, a portal and a key service do not exist in our rig.
  8. A lost link is noticed after 9 to 10 s. A message sent in that time, and a task sent during an outage, is lost with no count.
  9. Nothing revokes a slot certificate, and every certified peer may read below every anchor (goat's scoped read).
- **Open questions for Richard.** Which cloud account and region, and who pays for the VM.

### Step 5: pod 2

- **What changes.** A second pod with its own router, its own CA, its own salt and the site name `p2`. Its bridge takes a second slot on the fabric.
- **What must be shown.** The host fuses tracks from two pods. A node ID belongs to the anchor that registered it, so one pod cannot speak for the other.
- **Prepared in step 1.** The registry can describe more than one pod, and the fabric pool has free slots.
- **Must be done before a second pod** (found by the final review of step 1):
  1. Node ID ownership. The design of step 1 says that a node ID belongs to the anchor that registered it. The code binds it to the first key or token that names it, before validation, and never releases it. Bind ownership on an accepted registration, or take the node-to-anchor map from the registry.
  2. The host's state is not bounded: one slot can name any number of node IDs.
  3. Only upward kinds should teach the host a route. Today any first key does.
  4. The pod bridge's token cleanup stops early if one `undeclare_token` call fails. With one node this cannot happen.

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
- The Mac has no Rust toolchain. Build goat tools in a container. The Docker volume `apex-goat1-cargo-target` holds the build cache of the `goat` tool (a first build takes about 5 minutes).
- `python3 docs/evidence/goat1/check-quotes.py` checks every quoted line of the step 1 record and of `README-goat.md` against the evidence files. A new step needs the same for its own record.
- A background process that a subagent starts is killed when that subagent's turn ends. A subagent that makes a long live run must stay in its turn until the run has printed its end marker (learned in Task 12 of step 1).
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
| 2026-11-11 | The committed registry never holds `radar2`. The join step adds it and a last step restores the file. | Designer |
| 2026-11-11 | The pod fusion node validates each message from above with a validator of its own, and a log summary never raises. | Designer |
| 2026-11-11 | The new-track alert carries the track's own location and names the track. Each track gets its one alert with its first detection after the node registered upward. | Designer |
| 2026-11-11 | A task from above goes only to registered sensors. | Designer |
| 2026-11-11 | No container mounts a CA key. `radar2` mounts its own files only, and a missing file is an error. | Designer |
| 2026-11-12 | A quoted line must be in a saved evidence file. The evidence of a step is kept in the repository. | Designer |
| 2026-11-12 | The check with the real `goat` tool may end as "unknown" if goat needs a service that our rig has not. No access rule is widened to get a pass. (It passed.) | Designer |
| 2026-11-12 | A site is 1 to 32 characters of `[a-z0-9]`, tighter than the design's `[a-z0-9]+`, so that every reply key can be built. | Designer, after the final review |
| 2026-11-12 | Node ID ownership by first key is recorded as a deviation from the design and is not changed in step 1. It is a condition for step 5. | Designer, after the final review |
| 2026-11-12 | Detections from an unregistered node and locations that are not a number are left for step 2. | Final reviewer, accepted by the designer |
| 2026-11-12 | The goat work gets its own entry page, `README-goat.md`. | Richard |

## 7. What was done, in order

| Date | Work |
|---|---|
| 2026-11-08 to 09 | SAPIENT over Zenoh, stages 1 to 4, on branch `zenoh`. Evidence in `docs/acceptance.md`. |
| 2026-11-09 to 11 | Analysis of goatcore, Open Billie, octo-pod, the moon pod and goat's federation, from source. |
| 2026-11-11 | Brainstorm of this proof of concept. Drawings of the network and the data flow (dashboard artifacts `398f188ae09574fa` and `9e9103c14c8b5b71`; the reference drawing is `03f1c3fc36c6216c`). |
| 2026-11-11 | `docs/goat-context.md` written. Branch `goat` made from `zenoh`. |
| 2026-11-11 | Step 1 design and plan written and committed. Execution of the plan started. |
| 2026-11-11 to 12 | Step 1 executed in twelve tasks, each with its own implementer and reviewer: the pairing probe, slots, fabric keys, the generator, the pod bridge, the fabric link, the pod fusion node's traffic upward, the recorder's fabric mode, the rig, the outage and join checks, the `goat` client check, and the final clean run. |
| 2026-11-12 | Final review of the whole branch, one fix round (a site limit, the bridge's main loop, the recorder's error line, the generator), a second whole run at the new code, and one re-review. Evidence copied to `docs/evidence/goat1/`. `README-goat.md` made. An interactive explainer page for new team members added. Branch `goat` is made from `zenoh` (`0cca505`) and is not pushed. |
