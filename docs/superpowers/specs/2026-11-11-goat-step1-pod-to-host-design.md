# Step 1 design: pod 1 to host, on a fabric with goat's rules

Date: 2026-11-11. Branch: `goat`. Status: approved in conversation by Richard ("Step 1 is right, write the design"); the decisions marked "our call" were made by the designer and are open to correction.

Read `docs/goat-context.md` first. It holds the goat rules that this design follows, with a source for each rule. Section numbers of that file are cited here as "context 2.3".

## 1. Intent

The end goal is a real goatnet: pod 1 at the edge, a host in a cloud or a data centre, and an external host that belongs to a different sovereign. The work has six steps:

| Step | Content |
|---|---|
| 1 | Pod 1 to host. This document. |
| 2 | Stone Soup in the fusion node |
| 3 | Billie adapter for a sensor with a vendor protocol |
| 4 | The host on a real goatnet (goatlite on a cloud VM) |
| 5 | Pod 2 |
| 6 | External host, the second sovereign |

Step 1 shows that the pod from stage 4 of this repository can operate on a fabric that follows goat's rules. It adds the host tier as a stand-in that we build ourselves. The stand-in must follow the rules closely enough that step 4 can replace it with a real goatnet by a change of configuration.

Step 1 also closes a gap in stage 4. There, a new sensor needs new rules in the router file and a restart of the router. goat solves this with a pool of slots that is made in advance (context 2.1). Step 1 uses the same idea at both routers.

## 2. Goals, non-goals, anti-goals

### Goals

A run of the step 1 rig must show these results:

1. The host shows the pod's fused tracks and alerts below the pod's slot. No raw sensor data is on the fabric.
2. The host acknowledges the registration of the pod fusion node. This closes acceptance item T-11 of `docs/acceptance.md`.
3. A task from the host reaches a sensor in the pod, and an acknowledgement returns to the host.
4. A write outside the writer's slot is denied, in the checker and on the live router.
5. With the host link down, the pod continues to operate. After a short outage the session continues with no new registration. After an outage that is longer than the host's hold time, the host asks and the pod registers again. A task that is older than the limit is not delivered.
6. `goat sub` reads the pod's tracks on the fabric.
7. A new sensor joins a pod that is running, and the pod router does not restart.

### Non-goals

Stone Soup, the Billie adapter, a real goatnet, pod 2, the external host, release lanes, WireGuard and IPsec, router storage and `get`, schema declarations at `attest/schema/`, quality of service by key prefix, certificate renewal, removal of a node, and goat's signed bundle format.

### Anti-goals

- The earlier rigs must not break: the TCP-only rig and stages 1 to 4, with their compose files, their README sections and the unit suite.
- No invented goat format. Where goat has a format that we do not copy exactly (the signed bundle), we do not make a look-alike. We use plain configuration.
- No key on the fabric that a goat router would refuse to accept from a slot.

## 3. Constraints

- All work is on branch `goat`. Nothing is pushed.
- The rig runs on the Mac in Docker Compose (Colima). It needs no new tool on the Mac beyond Docker, `openssl` and `python3`.
- The payload is the serialised `SapientMessage`. The pod bridge forwards the bytes unchanged in both directions.
- The fabric router uses the image `eclipse/zenoh:1.9.0`, which is goat's pin. The pod router and the Python binding stay at 1.10.2.
- Key cardinality stays bounded. A key never holds a report ID, a task ID, an object ID or a timestamp. The reason is Zenoh issue 2825: a router can freeze when the 16-bit expression ID space of a face is used up.
- The unit suite runs in the emulator image, as before. New Python code that the suite tests must be importable there (the image mounts `./emulators` at `/emulators`).
- No goat software is installed. One goat file is copied into this repository: `acl-evaluate.py`.

## 4. Design

### 4.1 Parts

```text
 pod 1 (network pod1)                    host (network host)
 ---------------------                   -------------------
 radar, camera     \                      host fusion node / display
 vehicle - node bridge - pod router       host recorder
 pod fusion node   /        |                   |
 recorder                pod bridge ---- fabric router (zenohd 1.9.0)
                                (network mesh)
```

| Part | State | What changes |
|---|---|---|
| Radar, camera, vehicle with its node bridge | exist | Their certificates and node IDs now come from the pod's slot pool. Their code does not change. |
| Pod recorder | exists | It stays a named identity. Its certificate now comes from the generator. Its code does not change. |
| Pod router | exists | Its access list is generated, with a slot pool. One new named identity: the pod bridge. |
| Pod fusion node | exists | It reads messages from above, it sends status reports and alerts upward, and it acts on tasks from above. |
| Pod bridge | new | One process with two Zenoh sessions |
| Fabric router | new | Stock `zenohd` 1.9.0 with a generated access list in goat's shape |
| Host fusion node / display | new | The same program as the pod fusion node, with a link for the fabric keys |
| Host recorder | new | The existing recorder, with the fabric keys |
| Registry and generator | new | One file describes both routers. One tool makes the router files and the certificates. |

All parts run in one compose project with three Docker networks: `pod1`, `mesh` and `host`. The pod bridge joins `pod1` and `mesh`. The fabric router joins `mesh` and `host`. The `mesh` network stands in for the WireGuard mesh.

### 4.2 Identity and slots

There are two certificate authorities: the pod CA for pod 1 and the fabric CA for the host. Each is a local test CA, made by the generator.

**Fabric slots** follow goat exactly (context 2.1). Slot `k` has the anchor `sha256("<salt>:<k>")`, cut to the first 32 hexadecimal characters. The common name of the certificate is the anchor. Each fabric client holds a slot: the pod bridge, the host fusion node, the host recorder and the `goat` test client. Only the fabric router has a named certificate.

**Pod slots** are our own design, because goat does not govern the inside of a pod. Slot `k` of a pod has a SAPIENT node ID that is derived from the pod's salt: the first 16 bytes of `sha256("<salt>:<k>")`, formed into a version 4 UUID. The common name of the certificate is that node ID. A sensor that takes the slot must use that node ID. (Our call. The keys inside the pod do not change, so the earlier stages continue to work. The limit is that a device with a fixed node ID cannot take a slot directly; step 3 must deal with that for Billie.)

The pod keeps a small set of named identities that are not in the pool: the pod router, the pod fusion node, the pod recorder and the pod bridge.

A legacy node behind a node bridge also takes one slot. The node bridge holds the certificate of that slot, and the legacy node uses the node ID of that slot. One node bridge carries one legacy node. (Our call. A second legacy node gets its own node bridge and its own slot, so it also joins with no router restart.) In the step 1 rig the slots are: radar 0, camera 1, vehicle 2, and the fourth sensor of check G1-09 takes slot 3. Each place that names a node ID, such as the vehicle's list of dependent nodes, takes the value from the generator's output. The stage 4 files keep their fixed node IDs and do not change.

**Registry.** One file names, for each router: the salt, the pool size, the site name, and which alias holds which slot (for example `radar = 0`). To onboard a new member you add one line to the registry and run the generator again. The generator then makes only the missing certificate. It must also prove that the router file did not change, and exit with an error if it did.

**The five facts.** Each fabric client takes five facts from configuration and nothing else: the CA file, its certificate, its key, the router endpoint and its anchor (context 5.1).

### 4.3 Access lists

Both lists deny by default and are generated from the registry. The generator writes them in the text form that goat's `acl-evaluate.py` can parse:

- the blocks in the order `rules`, `subjects`, `policies`;
- each rule and each subject starts with `id: "<id>",` and ends with `},`;
- each policy has the form `{ rules: [...], subjects: [...] },`;
- comments only on their own lines.

**Fabric router.** The rules have goat's names and shapes (context 2.2 and 2.4):

| Rule | Messages | Flow | Key expressions | Subjects |
|---|---|---|---|---|
| `slot-w-<anchor>` | `put`, `delete`, `liveliness_token` | ingress | `<anchor>/**`, `volatile/<anchor>/**`, `<anchor>/**/@adv/**` | the slot |
| `peer-r-scoped` | `declare_subscriber`, `query`, `declare_queryable`, `reply`, `declare_liveliness_subscriber`, `liveliness_query` | ingress and egress | `*/**`, `**/@adv/**` | each mutual TLS peer |
| `peer-deliver-scoped` | `put`, `delete`, `liveliness_token` | egress | `*/**`, `**/@adv/**` | each mutual TLS peer |

**Pod router.** For each slot there are two rules: the slot may `put` and declare a liveliness token on its own up keys and its own live key, and it may subscribe to its own down keys. The named identities have these rights:

| Identity | Rights |
|---|---|
| Pod fusion node | As in stage 4, with one change: it may write `fusion/up/**` but not `fusion/down/**`. |
| Pod recorder | Reads all keys of the pod |
| Pod bridge | Subscribes to `fusion/up/**`. Writes `fusion/down/**`. Nothing else. |

**Checks.** The unit suite runs `acl-evaluate.py` on both generated files. It must test allowed cases as well as denied cases, because a file that the checker cannot parse denies everything. A golden test pins the generated text for a fixed test registry.

### 4.4 Keys on the fabric

Our call: the keys follow goat's taxonomy and goat's order of parts (context 2.3 and 2.10), and the last part is the SAPIENT node ID, not a track ID or a task ID. goat's own pattern for a track puts the track ID last. We do not follow that pattern in step 1, because of the bounded cardinality constraint, and because the stand-in router has no storage that could use it. Canonical tracks below `data/entity/track/` are a decision for step 4.

```text
<anchor>/telemetry/sapient/<site>/v2/<kind>/<node_id>     registration, status_report, detection_report, alert, error
<anchor>/ack/<site>/sapient/v2/<kind>/<node_id>           registration_ack, task_ack, alert_ack
<anchor>/task/<site>/sapient/v2/task/<node_id>            task
<anchor>/telemetry/sapient/<site>/v2/live/<node_id>       liveliness token
```

- `<anchor>` is the slot of the writer. The pod bridge writes below the pod's anchor. The host fusion node writes below its own anchor.
- `<site>` is one lower-case word for the pod's site. Pod 1 uses `p1`. The host's own site is `h1`.
- `<kind>` is the field name of the `SapientMessage.content` oneof, as inside the pod.
- `<node_id>` is the pod-side node that the message is about: the sender for a message that goes up, and the destination for a message that goes down.
- The host subscribes with a wildcard in the first part only, for example `*/telemetry/sapient/*/v2/*/*`. It never subscribes to `**` (context 2.4).
- A node ID belongs to the anchor that registered it. The host drops a message for a known node ID that arrives below a different anchor, and logs it.

The priority and congestion settings for each message kind stay as in `emulators/zenoh_keys.py`.

### 4.5 Pod bridge

The bridge has one session to the pod router (pod CA) and one session to the fabric router (slot certificate). Its configuration is: the pod endpoint and certificate, the five facts for the fabric, the pod's key prefix, the site name, and the list of host anchors that may send to this pod.

**Up.** It subscribes to `<prefix>fusion/up/**` in the pod. For each sample it reads the kind from the key and the node ID from the message, and it publishes the same bytes on the fabric key.

**Down.** For each allowed host anchor it subscribes to that anchor's `task/`, `ack/` and `telemetry/` keys for its own site. For each sample it publishes the same bytes on `<prefix>fusion/down/<kind>`. It drops the sample, and counts the drop, in these cases:

- the message cannot be decoded;
- the destination in the message is not the node ID in the key;
- the destination is not a node whose messages this bridge has forwarded up (in step 1 that is the pod fusion node only, so the host cannot address a sensor directly);
- the message is a task and its timestamp is older than 5 seconds.

**Presence.** The bridge declares the liveliness token for a pod node on the fabric when it forwards the first message of that node. It removes the token when it has forwarded nothing from that node for 30 seconds, or when its pod session loses the router. (Our call: presence follows traffic. The pod fusion node declares no token of its own today, and we do not change that.)

**No backlog.** While one session is down, the bridge drops what arrives on the other session and counts it. Each direction has one queue with a limit of 512 samples that drops the oldest sample. This is octo-pod's rule (context 3.3). The bridge logs its counters at an interval when a counter changed.

**Survival.** The bridge does not exit when a router is away. Each session reconnects by itself.

### 4.6 Pod fusion node

The node gets three additions, all for the Zenoh transport only:

1. **Upward traffic.** Its own status reports and its sensors' alerts also go upward. An alert that goes upward carries the pod fusion node's ID as sender.
2. **Messages from above.** It subscribes to `<prefix>fusion/down/**` and logs each message.
3. **Tasks from above.**
   - A request for registration: it publishes its registration again, upward and inside the pod, and sends an accepted acknowledgement upward.
   - A request for status: it sends a status report upward with the "new" flag, and an accepted acknowledgement.
   - Any other command: it sends a task with the same command, a new task ID and its own node ID to each of its sensors that the command is meant for. It then sends one acknowledgement upward: accepted if it tasked one sensor or more, rejected with a reason if it tasked none. It does not relay the acknowledgements of the sensors.

These additions publish more on `fusion/up/**`. Nothing reads those keys in stages 3 and 4, and their access rules permit it.

### 4.7 Host fusion node and display

Our call: the host fusion node is the same program as the pod fusion node, started with a third transport value for the fabric. A new link class has the same interface as `ZenohFusionLink` and uses the keys of section 4.4. The fusion node takes its key functions from its link, so that it has no knowledge of which key scheme is in use.

- On the fabric, a sender that registers as a fusion node is a child of the host: the host acknowledges it, validates it and fuses its tracks. Inside a pod the rule of stage 4 stays: another fusion node is a peer and is ignored. The link says which rule applies, so stage 3 and stage 4 behave as before. (Our call.)
- The host's wildcard subscription also matches the host's own output. The fabric link drops each sample whose first key part is the host's own anchor.
- The display is the log and the console of that program (`nodes`, `tracks`, `task`), as in the pod.
- It acknowledges the registration of each pod fusion node, validates each message with Apex's validator, joins pod tracks into host tracks, and acknowledges alerts.
- It sends tasks to the pod fusion node from its console and from its automatic task list.
- It has no parent in step 1, so its upward send does nothing.
- Its hold time for a node whose token is gone is configuration, as today.

One risk is known. Apex's validator refuses two detections from one sender that are less than 80 ms apart. A fusion node reports many objects, so the host must not apply that minimum gap to a fusion node. The builder must confirm how to do that with the validator's options.

### 4.8 Host recorder

The existing recorder gets the fabric keys. It subscribes to the three key classes with a wildcard in the first part, writes one JSON line for each message as today, and adds the anchor and the site to each line. It has a slot and never writes.

### 4.9 The `goat` test client

This is the last task of the step, and it must not block the other results.

- Build `goat` from `../usareur-af/goatcore/crates/goat-cli` at commit `cbf2cb7f`, in a Rust container, because the Mac has no Rust toolchain. Keep the binary out of git.
- Give it a slot and a profile directory in the form of context 5.1.
- Pass: `goat sub` with the pod's anchor as key prefix receives one sample or more from the running rig.
- If the build or the run fails for a reason that is in goat and not in our keys, record the result as unknown, with the evidence. Unknown is not a pass.

### 4.10 Rig, documents and tests

- A new compose file for step 1. The stage 4 files stay as they are.
- A new README section with the commands and the output of one real run, in the style of the stage sections.
- A new acceptance file `docs/acceptance-goat1.md` in the style of `docs/acceptance.md`: each line says what was measured and where it falls short.
- Unit tests for each new module, in the existing suite.

## 5. Acceptance checks

| ID | Check | Pass |
|---|---|---|
| G1-01 | Version pairing | A client with the 1.10.2 binding opens a mutual TLS session to the 1.9.0 router, publishes, subscribes and declares a liveliness token, and survives a router restart. |
| G1-02 | Tracks and alerts up | The host logs tracks and one alert or more from the pod fusion node. The host recorder has lines only below the pod's anchor and the host's anchor, and no line with a sensor's node ID as sender. |
| G1-03 | Registration | The pod fusion node logs a registration acknowledgement from the host with acceptance true. |
| G1-04 | Task down | A `look_at` task from the host produces a task at one sensor or more, and the host logs an accepted acknowledgement from the pod fusion node. |
| G1-05 | Access | The checker and the live fabric router both refuse: the pod's slot writing below the host's anchor, the host's slot writing below the pod's anchor, and a subscription to `**`. In the pod, the checker and the live router refuse one sensor writing another sensor's keys. |
| G1-06 | Short outage | The pod bridge is disconnected from `mesh` for less than the hold time. The pod's sensors and fusion node log no loss. After the link returns, tracks arrive at the host again, with no new registration. |
| G1-07 | Long outage | With a hold time of 20 seconds, the bridge is disconnected for longer. The host removes the node. After the link returns, the host asks for registration, the pod registers again, and the host accepts. |
| G1-08 | Old task | A task with a timestamp older than 5 seconds does not reach the pod fusion node, and the bridge counts one drop. A unit test is enough for this check. |
| G1-09 | Join with no restart | A fourth sensor is added to the registry while the rig runs. The generator reports that the pod router file did not change. The sensor starts, the pod fusion node accepts its registration, and the start time of the pod router container is unchanged. |
| G1-10 | `goat` client | Section 4.9 |
| G1-11 | No regression | The unit suite passes with no warning. The stage 4 rig starts and its three sensors register. |

## 6. Left to the builder

- File names, class names, log texts, and the layout of the generator and the registry.
- The exact queue sizes and intervals, where this document gives a number only as a default.
- How the fourth sensor of G1-09 is declared in the compose file.
- The text and order of the README section.

## 7. Risks and decisions made in advance

| Risk | Decision |
|---|---|
| The 1.10.2 binding does not operate with the 1.9.0 router, or the 1.9.0 image has no arm64 build. | G1-01 is the first task. If it fails, use `eclipse/zenoh:1.10.2` for the fabric router in step 1, record the evidence as an open item for step 4, and continue. (Our call.) |
| A message name in the access list is not known to 1.9.0. | The generator's output must start on the real 1.9.0 image in the first task that makes it. |
| `acl-evaluate.py` proves Zenoh 1.9.0 behaviour only, and the pod router is 1.10.2. | For the pod router the checker is a first check. The live check G1-05 is the evidence. |
| Docker is not running. | All tests need Colima. Stop and ask for it, do not work around it. |
| The `goat` build needs more memory than the Colima VM has. | Record G1-10 as unknown with the evidence. |
