# The goat network work: SAPIENT pods on a goat fabric

This file is the entry page for the goat work in this repository. [`README.md`](README.md) covers the base rig (Apex in Docker and the fake nodes) and the four Zenoh stages that this work builds on.

**New to this work?** Start with the explainer page, [`docs/explainers/goat-step1/index.html`](docs/explainers/goat-step1/index.html). It explains SAPIENT, Zenoh and the goat network in plain words, then the end goal and step 1, and you can click through the rig and the message flows. Open the file in a browser from your clone, for example with `open docs/explainers/goat-step1/index.html` on a Mac. A code hosting site shows only the source of an HTML file. The page is one file, loads nothing else and needs no network.

[![The explainer page of step 1](docs/explainers/goat-step1/preview.png)](docs/explainers/goat-step1/index.html)

For more on goat itself, two background pages are in the same folder: [goat in plain language](docs/explainers/goatcore/overview.html) and [goatcore: the technical note](docs/explainers/goatcore/architecture.html). They are studies of goat's source from before step 1. [`docs/explainers/README.md`](docs/explainers/README.md) lists all the explainer pages.

goat is the open source network of United States Army Europe and Africa: a mesh, a Zenoh data fabric, identities and a CA. The goal of this work is a real goatnet with three parts: pod 1 at the edge, a host in a cloud or a data centre, and an external host that belongs to a different sovereign. The work has six steps.

| Step | Content | Status |
|---|---|---|
| 1 | Pod 1 to host, on a stand-in fabric that follows goat's rules | Done on 2026-11-12 (UTC). The section below has the drawings and the run steps. |
| 2 | Stone Soup in the fusion node | Not started |
| 3 | Billie adapter for a sensor with a vendor protocol | Not started |
| 4 | The host on a real goatnet (a goatlite) | Done on 2026-11-18 to 19 UTC against the goatlite `cuaslab`, on branch `goat-step4-cuaslab`. The section "Goat step 4" below has the run steps. |
| 5 | Pod 2 | Not started |
| 6 | External host, the second sovereign | Not started |

## Documents

| File | Content |
|---|---|
| `docs/explainers/goat-step1/index.html` | An interactive page for a new team member: the background, the end goal, the rig of step 1 and its message flows |
| `docs/explainers/goatcore/` | Two background pages on goat: one in plain language, one technical |
| `docs/goat-roadmap.md` | The six steps: what is decided, what is open, and how a step is started |
| `docs/goat-context.md` | The goat rules that this work follows, with a source for each rule |
| `docs/superpowers/specs/2026-11-11-goat-step1-pod-to-host-design.md` | The design of step 1 |
| `docs/superpowers/plans/2026-11-11-goat-step1-pod-to-host.md` | The plan of step 1 |
| `docs/acceptance-goat1.md` | The acceptance record of step 1: checks G1-01 to G1-11, the known limits, and the open items for step 4 |
| `docs/evidence/goat1/` | The saved outputs and logs that the record and this file quote, with an index and a quote checker |
| `docs/superpowers/specs/2026-11-18-goat-step4-cuaslab-design.md` | The design of step 4 |
| `docs/superpowers/plans/2026-11-18-goat-step4-cuaslab.md` | The plan of step 4 |
| `docs/acceptance-goat4.md` | The acceptance record of step 4: checks G4-01 to G4-13, what was not shown, and what stays on `cuaslab` |
| `docs/evidence/goat4/` | The saved outputs of step 4 that the record and this file quote, with an index and a quote checker that also searches for secrets |

## Before you start

Build the image `apex-sapient:4.2.0` and start Colima as sections 1 to 3 of [`README.md`](README.md) describe. Step 10 below also needs the goat source in `../usareur-af/goatcore` and a network connection.

## Goat step 1: pod 1 to host

This step carries pod 1's SAPIENT traffic to a host over a fabric that follows the goat network's rules. `docker-compose.goat1.yml` runs two routers and the nodes around them:

- **Pod 1** (network `pod1`): the pod router `zenohd-pod` (`eclipse/zenoh:1.10.2`, `zenoh/goat1/router-pod1.json5`), the fusion node, radar, camera, the vehicle behind `bridge-node`, and the pod recorder. Pod keys are prefixed `h1/p1/`. Each sensor holds a slot certificate whose common name is its node ID.
- **The pod bridge** (networks `pod1` and `mesh`): `pod_bridge.py` holds the pod's bridge certificate on the pod router and the pod's slot certificate on the fabric router, and forwards the bytes unchanged in both directions. Only the fusion node's traffic goes up.
- **The host** (network `host`): the fabric router `zenohd-fabric` (`${FABRIC_ZENOH_IMAGE:-eclipse/zenoh:1.9.0}`, `zenoh/goat1/router-fabric.json5`), a fusion node with `TRANSPORT=fabric`, and a recorder with `RECORD_KEYS=fabric`. Fabric keys start with the writer's 32-character anchor, and the fabric router lets each certificate write only below its own anchor.

`radar2` sits behind the compose profile `join`: the rig starts without `radar2` unless the profile `join` is named, as step 9 does. The generator writes the router configurations, the certificates and `zenoh/goat1/goat1.env` below `zenoh/goat1/`, which is git-ignored. The compose file is standalone: don't combine it with the other compose files. It uses the project name `apex-goat1` and the image `apex-sapient:4.2.0` built by the earlier stages. No router port is published to the host.

### The rig of step 1

One Docker Compose project, `apex-goat1`, on one machine. Three Docker networks take the place of the pod's local network, the mesh and the host's network.

```
 network pod1: pod 1, site p1                          network host: the host, site h1
+------------------------------------------------+    +----------------------------------------+
|                                                |    |                                        |
|  radar   (slot 0) ----+                        |    |  host-fusion          host-recorder    |
|  camera  (slot 1) ----+                        |    |  (slot 1)             (slot 2)         |
|  fusion-node ---------+--TLS-->  zenohd-pod    |    |       |                    |           |
|  recorder ------------+          Zenoh 1.10.2  |    |       +------- TLS --------+           |
|  bridge-node (slot 2)-+          pod CA        |    |                 |                      |
|       ^                          8 slots       |    |                 v                      |
|       | TCP, no TLS                 ^          |    |           zenohd-fabric                |
|  vehicle (legacy node)              | TLS      |    |           Zenoh 1.9.0                  |
|                                     |          |    |           fabric CA, 8 slots           |
|  radar2 (slot 3) joins         pod-bridge      |    |                 ^                      |
|  later, in step 9              (named cert)    |    |                 | TLS                  |
+-------------------------------------|----------+    +-----------------|----------------------+
                                      |                                 |
                                      +---------------------------------+
                                          network mesh: TLS, the bridge uses fabric slot 0
                                          (in place of the WireGuard mesh of a real goatnet)
```

- **Two CAs.** The pod CA signs everything inside the pod. The fabric CA signs the host side and the bridge's slot certificate.
- **The pod bridge** is the only part on both sides. It has a named pod certificate for `zenohd-pod` and the certificate of fabric slot 0 for `zenohd-fabric`. It copies the bytes unchanged.
- **Slots.** In the pod, a slot gives a sensor its certificate and its node ID. On the fabric, a slot gives a client its certificate and its anchor, the first part of every key that it may write. Fabric slot 3 is the `goat` test client of step 10.
- **Named pod identities**, not in the pool: the pod router, `fusion-node`, `recorder` and `pod-bridge`.

### The data flow of step 1

```
UP: registration, status, tracks, alerts, task acknowledgements

 sensor        pod fusion node       pod bridge         fabric router        host fusion
 (pod 1)                                                                   + host recorder
    |                 |                   |                   |                   |
    |------ (1) ----->|                   |                   |                   |
    |                 |------- (2) ------>|                   |                   |
    |                 |                   |------- (3) ------>|                   |
    |                 |                   |                   |------- (3) ------>|

DOWN: tasks and acknowledgements from the host

 sensor        pod fusion node       pod bridge         fabric router        host fusion
 (pod 1)                                                                   + host recorder
    |                 |                   |                   |                   |
    |                 |                   |                   |<------ (4) -------|
    |                 |                   |<------ (4) -------|                   |
    |                 |<------ (5) -------|                   |                   |
    |<----- (6) ------|                   |                   |                   |
```

| Hop | Key | Who may write it |
|---|---|---|
| (1) | `h1/p1/sapient/v2/<sensor ID>/up/<kind>` | that sensor's slot only |
| (2) | `h1/p1/fusion/up/<kind>` | the pod fusion node |
| (3) | `<pod anchor>/telemetry/sapient/p1/v2/<kind>/<fusion node ID>`, and `<pod anchor>/ack/p1/sapient/v2/task_ack/<fusion node ID>` for a task acknowledgement | fabric slot 0, the pod bridge |
| (4) | `<host anchor>/task/p1/sapient/v2/task/<fusion node ID>`, and `<host anchor>/ack/p1/sapient/v2/<kind>/<fusion node ID>` for an acknowledgement | fabric slot 1, the host fusion node |
| (5) | `h1/p1/fusion/down/<kind>` | the pod bridge |
| (6) | `h1/p1/sapient/v2/<sensor ID>/down/task` | the pod fusion node |

- **Raw sensor data stops at the pod fusion node.** Only what the fusion node sends on (2) reaches the fabric: its registration, its status, its fused tracks and its alerts.
- **The host tasks only the pod fusion node.** At (6) the fusion node sends a copy of the command, with a new task ID, to each registered sensor that the command is meant for.
- **Presence.** While the pod fusion node sends traffic, the bridge holds a liveliness token on `<pod anchor>/telemetry/sapient/p1/v2/live/<fusion node ID>`. The host removes the node when the token has been away for the hold time.
- **Checks on the way down, at the bridge.** It drops a message that does not decode, whose destination is not the node in the key, that is for a node it has not forwarded upward, or that is a task older than 5 seconds. The pod fusion node then validates what arrives; its validator also rejects a message whose timestamp is more than 0.9 s behind its clock.

The values in this rig: the pod anchor is `18214b1a34e3c722d1cac283b272a62c` (fabric slot 0), the host anchor is `b005ae3a8f2baf89160bd71632902672` (fabric slot 1), and the pod fusion node's ID is `f0000001-0000-4000-8000-000000000001`.

### Run it

Run these in order, from the repo root, on a rig that is down. Below each block is what one run printed on 2026-11-12 UTC, with the code of commit `c6a2db1` and the commands of this section as written now (steps 3 and 5 were changed just before the run and committed after it): steps 1 to 10 pasted in order into one zsh, with no generated files below `zenoh/goat1/` and no `apex-goat1-cargo-target` volume at the start. The blocks are shortened: `dg` also prints container lines (`Creating`, `Recreate`, `Started` and the like), the probe prints a `connected to Zenoh router` line, and `sub` prints up to four `e.g.` lines with sample keys; all of these are left out here. The saved output of the run is `docs/evidence/goat1/task-12-readme-run.txt`. After the fixes of the final review, a run of the same steps at commit `e02a289` gave the same results in substance, with other times, IDs and record counts; its output is `docs/evidence/goat1/final-fix-readme-run.txt`, and `docs/acceptance-goat1.md` records it in the section "Run after the review fixes".

```bash
dg() { docker compose --env-file zenoh/goat1/goat1.env -f docker-compose.goat1.yml "$@"; }
probe() { local service=$1; shift; dg run --rm --no-deps -T "$service" python probe_access.py "$@" < /dev/null; }
podfabric() { dg run --rm --no-deps -T -e ZENOH_CONNECT=tls/router.fabric.h1:7447 -e ZENOH_TLS_CA=/certs/fabric/ca.pem -e ZENOH_TLS_CERT=/certs/fabric/pod1.pem -e ZENOH_TLS_KEY=/certs/fabric/pod1.key pod-bridge python probe_access.py "$@" < /dev/null; }
```

`probe` runs `emulators/probe_access.py` in a one-off container of a service, with that service's certificate: `put <key>` publishes one status report, and `sub <key expression> <seconds>` counts what arrives and how much of it came from the probe. `podfabric` does the same with the pod's slot certificate on the fabric router. The `< /dev/null` keeps a one-off container from reading the rest of a pasted block.

**1. Generate and start.** Running the generator again is safe; it rewrites the same files.

```bash
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1
source zenoh/goat1/goat1.env
dg up -d
sleep 45
dg ps --format '{{.Service}} {{.State}}' | sort
dg logs zenohd-pod zenohd-fabric | grep -ci -E 'error|panic'
```

The 11 services were `running` (`bridge-node`, `camera`, `fusion-node`, `host-fusion`, `host-recorder`, `pod-bridge`, `radar`, `recorder`, `vehicle`, `zenohd-fabric`, `zenohd-pod`), and the error count was `0`.

**2. Registration (G1-03).** The pod's fusion node accepts its three sensors, then registers upward and gets the host's acknowledgement.

```bash
dg logs fusion-node | grep registration_ack
dg logs host-fusion | grep "<- registration "
```

```text
fusion-node-1  | 01:23:42 fusion: -> registration_ack f0000001 -> 86ca6000 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 01:23:42 fusion: -> registration_ack f0000001 -> 1aef1b86 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 01:23:42 fusion: -> registration_ack f0000001 -> 341b9172 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 01:23:47 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
host-fusion-1  | 01:23:47 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
```

**3. Tracks and alerts up (G1-02).** The host gets the pod's fused tracks and one alert for each new track. The host recorder holds only messages below the pod's anchor or the host fusion node's anchor, and none of them carries a sensor's node ID.

```bash
dg logs host-fusion | grep -c "<- detection_report"
dg logs host-fusion | grep "<- alert"
dg exec -T host-recorder sh -c 'cat /data/records/*.jsonl' < /dev/null | python3 -c '
import collections, json, sys
anchors, sensors = set(sys.argv[1:3]), set(sys.argv[3:6])
rows = [json.loads(line) for line in sys.stdin if line.strip()]
print("records:", len(rows))
print("anchor not the pod or the host fusion node:", sum(r.get("anchor") not in anchors for r in rows))
print("msg.node_id of the radar, camera or vehicle:", sum(r.get("msg", {}).get("node_id") in sensors for r in rows))
def paths(x, at):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from paths(v, at + "." + k)
    elif isinstance(x, list):
        for v in x:
            yield from paths(v, at + "[]")
    elif isinstance(x, str) and any(s in x for s in sensors):
        yield at
print("records that did not decode:", sum("error" in r for r in rows))
print("records with a sensor node ID anywhere:", sum(any(True for _ in paths(r, "")) for r in rows))
hits = collections.Counter((r.get("kind"), at) for r in rows for at in paths(r, ""))
for (kind, at), n in sorted(hits.items()):
    print(" ", kind, at, n)
' "$FABRIC_POD1_ID" "$FABRIC_HOST_FUSION_ID" "$POD1_RADAR_ID" "$POD1_CAMERA_ID" "$POD1_VEHICLE_ID"
```

```text
5
host-fusion-1  | 01:23:47 fusion: <- alert f0000001 ALERT_TYPE_INFORMATION "new track Z6EWXY"
records: 4656
anchor not the pod or the host fusion node: 0
msg.node_id of the radar, camera or vehicle: 0
records that did not decode: 0
records with a sensor node ID anywhere: 0
```

The detection count is low because the fusion node logs every 10th detection report of each node. The recorder's volume survives `dg down`, so the record count includes any earlier run on the same UTC day. The last three lines search each whole record, not only its top-level `node_id`: a record that did not decode would hold only base64, so it is counted apart; the next line counts the records that hold the node ID of the radar, the camera or the vehicle in any string field; below it each such field would be listed with its message kind. Here there were none.

**4. A task down (G1-04).** The host's fusion node sends `request:Status` and `look_at` in turn, every 20 s. The pod's fusion node passes `look_at` to its registered sensors as a copy with a new task ID, and acknowledges upward.

```bash
dg logs radar camera | grep "<- task .* look_at" | cut -c1-90
dg logs host-fusion | grep "<- task_ack" | grep TASK_STATUS_ACCEPTED
```

```text
camera-1  | 01:24:22 camera: <- task f0000001 -> 86ca6000 ETGGDQ look_at {"location_list":
radar-1   | 01:24:22 radar: <- task f0000001 -> 1aef1b86 CGEN0T look_at {"location_list":
host-fusion-1  | 01:24:02 fusion: <- task_ack f0000001 -> f0000002 9NZKWJ TASK_STATUS_ACCEPTED ['Status report sent']
host-fusion-1  | 01:24:22 fusion: <- task_ack f0000001 -> f0000002 C6A1J0 TASK_STATUS_ACCEPTED ['look_at sent to 2 nodes']
```

**5. Access on the live routers (G1-05).** Restart both routers with the access-control trace. A denial is silent for the client, so each case shows two things: the subscriber, whose certificate may read the key, got nothing from the probe, and the router logged the denial. On the fabric router each certificate matches two subjects (any mutual-TLS peer, and its own slot). The router tries each subject in turn and logs `unauthorized` for each one that denies, and stops at the first that allows with one `authorized` line (function `action` in `zenoh/src/net/routing/interceptor/access_control.rs`, Zenoh 1.9.0 and 1.10.2). So one denied put logs two `unauthorized` lines and no `authorized` line, while an allowed put can also log an `unauthorized` line before its `authorized` line. The test is therefore: no `authorized` line and 0 probe samples. Each count reads only the router's log since `T`, the second just before the probe started, so a line from before the probe is not counted.

```bash
ZENOHD_RUST_LOG=zenoh::net::routing::interceptor=trace dg up -d zenohd-pod zenohd-fabric
sleep 20
dg logs --since 30s pod-bridge
```

```text
pod-bridge-1  | 01:24:38 pod-bridge: pod router lost
pod-bridge-1  | 01:24:38 pod-bridge: fabric router lost
pod-bridge-1  | 01:24:39 pod-bridge: fabric router back
pod-bridge-1  | 01:24:39 pod-bridge: pod router back
pod-bridge-1  | 01:24:42 pod-bridge: forwarded {'up': 67, 'down': 5}; dropped {}
```

Case 1: the pod's slot certificate puts on the host fusion node's task key.

```bash
K="$FABRIC_HOST_FUSION_ID/task/p1/sapient/v2/task/$POD1_FUSION_NODE_ID"
T=$(date +%s)
probe host-recorder sub "$K" 15 &
sleep 5
podfabric put "$K"
wait
dg logs --since "$T" zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_POD1_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs --since "$T" zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_POD1_ID)" | grep -c "is authorized to Put (ingress)"
```

```text
put: 1 status report on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
samples: 1 on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
2
0
```

The one sample is the host's own periodic task on that key; none came from the probe.

Case 2: the host fusion certificate puts on the pod's alert key.

```bash
K="$FABRIC_POD1_ID/telemetry/sapient/p1/v2/alert/$POD1_FUSION_NODE_ID"
T=$(date +%s)
probe host-recorder sub "$K" 15 &
sleep 5
probe host-fusion put "$K"
wait
dg logs --since "$T" zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_HOST_FUSION_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs --since "$T" zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_HOST_FUSION_ID)" | grep -c "is authorized to Put (ingress)"
```

```text
samples: 0 on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
2
0
```

Case 3: the host recorder's certificate may not subscribe to everything, only to the fabric's telemetry.

```bash
T=$(date +%s)
probe host-recorder sub "**" 15
probe host-recorder sub "*/telemetry/sapient/*/v2/*/*" 15
dg logs --since "$T" zenohd-fabric | grep -F "CertCommonName($FABRIC_HOST_RECORDER_ID)" | grep -F "Declare Subscriber (ingress) on **" | grep -c unauthorized
```

```text
samples: 0 on ** in 15 s; from this probe: 0
samples: 33 on */telemetry/sapient/*/v2/*/* in 15 s; from this probe: 0
2
```

Case 4: in the pod, the radar's certificate puts on the camera's up key.

```bash
K="h1/p1/sapient/v2/$POD1_CAMERA_ID/up/status_report"
T=$(date +%s)
probe recorder sub "$K" 15 &
sleep 5
probe radar put "$K"
wait
dg logs --since "$T" zenohd-pod | grep -F "$K" | grep -F "CertCommonName($POD1_RADAR_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs --since "$T" zenohd-pod | grep -F "$K" | grep -F "CertCommonName($POD1_RADAR_ID)" | grep -c "is authorized to Put (ingress)"
```

```text
samples: 3 on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report in 15 s; from this probe: 0
1
0
```

The three samples are the camera's own status reports. The pod router has one subject for each certificate, so one line.

Put the routers back to `info`:

```bash
dg up -d zenohd-pod zenohd-fabric
```

**6. Host restart.** The restarted host fusion node asks the pod to register again, and acknowledges it.

```bash
dg restart host-fusion
sleep 40
dg logs --since 40s fusion-node | grep -E 'request "Registration"|registration_ack'
```

```text
fusion-node-1  | 01:26:37 fusion: <- task f0000002 -> f0000001 Q39T3Z request "Registration"
fusion-node-1  | 01:26:37 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
```

**7. Short outage (G1-06).** Cut the pod bridge off the `mesh` network for 30 s, less than the host's hold time of 120 s. The pod's sensors and fusion node log no loss, and the pod's fusion node still takes the sensors' detections. After the link returns, tracks reach the host again with no new registration. The bridge counts what the pod sent meanwhile as `other_side_down`.

```bash
docker network disconnect apex-goat1_mesh apex-goat1-pod-bridge-1
sleep 30
dg logs --since 30s radar camera vehicle fusion-node | grep -c -E 'lost|cannot reach'
dg logs --since 30s fusion-node | grep -c "<- detection_report"
docker network connect apex-goat1_mesh apex-goat1-pod-bridge-1
sleep 30
dg logs --since 25s host-fusion | grep -c "<- detection_report"
dg logs --since 60s host-fusion | grep -c "<- registration "
dg logs --since 70s pod-bridge
```

```text
0
6
2
0
pod-bridge-1  | 01:27:12 pod-bridge: forwarded {'up': 242, 'down': 13}; dropped {}
pod-bridge-1  | 01:27:27 pod-bridge: fabric router lost
pod-bridge-1  | 01:27:42 pod-bridge: forwarded {'up': 259, 'down': 14}; dropped {'other_side_down': 17}
pod-bridge-1  | 01:27:50 pod-bridge: fabric router back
pod-bridge-1  | 01:28:12 pod-bridge: forwarded {'up': 285, 'down': 15}; dropped {'other_side_down': 25}
```

The bridge notices the loss only when its session to the fabric router times out: in two timed runs of Task 10 it logged `fabric router lost` 9 to 10 s after the disconnect, and `fabric router back` 0 to 2 s after the connect. In the run above the step started at 01:27:17 and the loss was logged at 01:27:27. What it publishes before it notices counts as forwarded; these steps don't show whether it arrived.

**8. Long outage (G1-07).** Restart the rig with a host hold time of 20 s, then cut the bridge off for 40 s. The host removes the pod's fusion node, and when the link returns it asks for a registration, which the pod sends and the host accepts. The rig keeps the 20 s hold until the next `dg up` without `HOST_HOLD_SECONDS`.

```bash
dg down
HOST_HOLD_SECONDS=20 dg up -d
sleep 60
docker network disconnect apex-goat1_mesh apex-goat1-pod-bridge-1
sleep 40
docker network connect apex-goat1_mesh apex-goat1-pod-bridge-1
sleep 40
dg logs host-fusion | grep -E 'removed|request "Registration"|<- registration '
dg logs fusion-node | grep "<- registration_ack f0000002"
```

```text
host-fusion-1  | 01:28:53 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
host-fusion-1  | 01:30:18 fusion: node f0000001 gone for 20 s; removed
host-fusion-1  | 01:30:33 fusion: -> task f0000002 -> f0000001 R5NRPQ request "Registration"
host-fusion-1  | 01:30:33 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
fusion-node-1  | 01:28:53 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 01:30:33 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
```

The first registration is the one at start; the other lines follow the outage.

**9. A sensor joins with no router restart (G1-09).** The rig starts without `radar2` unless the profile `join` is named. Give `radar2` the free slot 3 of the pod's pool in the registry, and run the generator with `--frozen-routers`: it issues the new certificate and exits 0 only if neither router file changes. Then start `radar2`. The pod's fusion node accepts it, and the pod router keeps running.

```bash
before=$(docker inspect -f '{{.State.StartedAt}}' apex-goat1-zenohd-pod-1)
shasum -a 256 zenoh/goat1/router-pod1.json5 zenoh/goat1/router-fabric.json5
python3 -c 'import pathlib; p = pathlib.Path("goat1/registry.toml"); p.write_text(p.read_text().replace("[pod1.slots]\n", "[pod1.slots]\nradar2 = 3\n", 1))'
grep -A4 '^\[pod1.slots\]' goat1/registry.toml
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1 --frozen-routers
echo "exit $?"
shasum -a 256 zenoh/goat1/router-pod1.json5 zenoh/goat1/router-fabric.json5
source zenoh/goat1/goat1.env
dg --profile join up -d radar2
sleep 30
dg logs fusion-node | grep "<- registration " | grep -c "Fake second radar"
dg logs fusion-node | grep "registration_ack f0000001 -> ${POD1_RADAR2_ID:0:8}"
dg logs fusion-node | grep -c "<- detection_report ${POD1_RADAR2_ID:0:8}"
test "$before" = "$(docker inspect -f '{{.State.StartedAt}}' apex-goat1-zenohd-pod-1)" && echo "router not restarted"
dg logs zenohd-pod | grep -ci -E 'error|panic'
```

```text
c3a5e2b99a4a843d0322ddddd5dde61cf5c9796a25bb1d962af9c9b519b84627  zenoh/goat1/router-pod1.json5
f7f5e342377767ddcf0e22d754d22236f1417967dcd2891927b6aea54a3bedf8  zenoh/goat1/router-fabric.json5
[pod1.slots]
radar2 = 3
radar = 0
camera = 1
vehicle = 2
router files unchanged
exit 0
c3a5e2b99a4a843d0322ddddd5dde61cf5c9796a25bb1d962af9c9b519b84627  zenoh/goat1/router-pod1.json5
f7f5e342377767ddcf0e22d754d22236f1417967dcd2891927b6aea54a3bedf8  zenoh/goat1/router-fabric.json5
1
fusion-node-1  | 01:31:10 fusion: -> registration_ack f0000001 -> 83ff6077 acceptance=True ['Accepted by fake fusion node']
3
router not restarted
0
```

The detection count is low because the fusion node logs every 10th detection report of each node.

Take `radar2` out again and put the registry back as committed. The generator leaves the `radar2` certificate and key below `zenoh/goat1/pki/pod1/`, prints `router files unchanged` and exits 0; `goat1.env` no longer has `POD1_RADAR2_ID`.

```bash
dg --profile join rm -s -f radar2
git restore goat1/registry.toml
unset POD1_RADAR2_ID
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1 --frozen-routers
echo "exit $?"
git status --short goat1/registry.toml
```

```text
router files unchanged
exit 0
```

`git status` printed nothing: the registry is as committed.

**10. A real goat client reads the pod's tracks (G1-10).** This is the one check with goat's own software. Build goat's command line tool `goat` from the goat source in `../usareur-af/goatcore`, at commit `cbf2cb7f` (`goat-cli` 0.5.19), give it the certificate of fabric slot 3 (`FABRIC_GOAT_CLI_ID`), and let `goat sub` read below the pod's anchor from the fabric router.

The build runs in `rust:1.95.0-bookworm`, with the goat source mounted read-only, and needs the network for the image and for the crates. On an empty volume the build took 4 min 35 s by cargo's count, and the whole block 276 s, on a Colima VM with 4 CPUs and 6 GiB; a later build takes seconds. The build output and the downloaded crates stay in the Docker volume `apex-goat1-cargo-target`; remove it with `docker volume rm apex-goat1-cargo-target`. The binary goes to `zenoh/goat1/bin/goat` (git-ignored) and runs in `debian:bookworm-slim`.

```bash
docker run --rm -v "$PWD/../usareur-af/goatcore:/src:ro" -v apex-goat1-cargo-target:/target -e CARGO_TARGET_DIR=/target -e CARGO_HOME=/target/cargo-home rust:1.95.0-bookworm cargo build --release --locked -j 2 --manifest-path /src/crates/Cargo.toml -p goat-cli < /dev/null
mkdir -p zenoh/goat1/bin
docker run --rm -v apex-goat1-cargo-target:/target:ro -v "$PWD/zenoh/goat1/bin:/out" debian:bookworm-slim cp /target/release/goat /out/goat < /dev/null
docker run --rm -v "$PWD/zenoh/goat1/bin/goat:/usr/local/bin/goat:ro" debian:bookworm-slim goat --version < /dev/null
```

```text
    Finished `release` profile [optimized] target(s) in 4m 35s
goat 0.5.19
```

goat reads its profile from `GOAT_PROFILE_DIR`: `config.toml` names the context, and `contexts/goat1/` holds `profile.toml` (`router_endpoint`, `device_id`), `mtls.cert.pem`, `mtls.key.pem` and `ca-roots.pem`. Only the two `.toml` files are written below `zenoh/goat1/goat-profile/`. The `goat` helper mounts the slot 3 certificate, its key and the fabric CA read-only under the names goat expects, so the key is not copied. goat runs on the network `apex-goat1_host`, where the fabric router answers as `router.fabric.h1`.

```bash
mkdir -p zenoh/goat1/goat-profile/contexts/goat1
printf 'current_context = "goat1"\n' > zenoh/goat1/goat-profile/config.toml
printf 'router_endpoint = "tls/router.fabric.h1:7447"\ndevice_id = "goat-cli"\n' > zenoh/goat1/goat-profile/contexts/goat1/profile.toml
goat() { docker run --rm --network apex-goat1_host -e GOAT_PROFILE_DIR=/goat-profile -v "$PWD/zenoh/goat1/bin/goat:/usr/local/bin/goat:ro" -v "$PWD/zenoh/goat1/goat-profile/config.toml:/goat-profile/config.toml:ro" -v "$PWD/zenoh/goat1/goat-profile/contexts/goat1/profile.toml:/goat-profile/contexts/goat1/profile.toml:ro" -v "$PWD/zenoh/goat1/pki/fabric/goat-cli.pem:/goat-profile/contexts/goat1/mtls.cert.pem:ro" -v "$PWD/zenoh/goat1/pki/fabric/goat-cli.key:/goat-profile/contexts/goat1/mtls.key.pem:ro" -v "$PWD/zenoh/goat1/pki/fabric/ca.pem:/goat-profile/contexts/goat1/ca-roots.pem:ro" debian:bookworm-slim goat "$@" < /dev/null; }
```

Restart the fabric router with the access-control trace, as step 5 does, and subscribe. `--take` with `--for` makes `goat sub` exit non-zero if the samples don't arrive within 30 s. `--uuid` prints the whole anchor; without it goat shortens it to its first 8 characters. Then count, in the router's trace, slot 3's allowed subscriber declarations below the pod's anchor, the samples the router delivered to it, and its allowed writes of any kind.

```bash
source zenoh/goat1/goat1.env
ZENOHD_RUST_LOG=zenoh::net::routing::interceptor=trace dg up -d zenohd-fabric
sleep 20
goat --context goat1 sub "$FABRIC_POD1_ID/**" --take 1 --for 30s --uuid
echo "exit $?"
goat --context goat1 sub "$FABRIC_POD1_ID/telemetry/sapient/p1/v2/detection_report/*" --take 3 --for 30s --uuid --keys-only
echo "exit $?"
dg logs zenohd-fabric | grep -F "CertCommonName($FABRIC_GOAT_CLI_ID)" | grep -c "is authorized to Declare Subscriber (ingress) on $FABRIC_POD1_ID/"
dg logs zenohd-fabric | grep -F "CertCommonName($FABRIC_GOAT_CLI_ID)" | grep -c -E "is authorized to Put \(egress\) on $FABRIC_POD1_ID/telemetry/sapient/p1/v2/[a-z_]+/"
dg logs zenohd-fabric | grep -F "CertCommonName($FABRIC_GOAT_CLI_ID)" | grep -c -E "is authorized to (Put|Delete|Declare/Undeclare Liveliness Token) \(ingress\)"
dg up -d zenohd-fabric
```

```text
listening on `18214b1a34e3c722d1cac283b272a62c/**` via tls/router.fabric.h1:7447 — stopping after 1 event(s). Ctrl-C to stop.
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001 hex:0a0c08bab0d4d706...
done after 0s — 1 event(s) on `18214b1a34e3c722d1cac283b272a62c/**` (the requested 1)
exit 0
listening on `18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/*` via tls/router.fabric.h1:7447 — stopping after 3 event(s). Ctrl-C to stop.
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
done after 2s — 3 event(s) on `18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/*` (the requested 3)
exit 0
2
4
0
```

The hex payload of the first sample is cut after its first bytes, marked `...`. The payload differs on each run.

Both runs exit 0, and every key starts with the pod's anchor `18214b1a34e3c722d1cac283b272a62c`. The three counts are measured: the router allowed two subscriber declarations, delivered four samples (the four that goat printed), and allowed no put, delete or liveliness token from slot 3. A count made afterwards on the saved router log of this run (`docs/evidence/goat1/task-12-g1-10-count.txt`), not by a command of this step, left no line from goat that is not a subscriber declaration, a delivery or a cache block, so it found no put, delete, query, liveliness token or liveliness query from goat at all. The router's other lines for slot 3 come in one burst for each session, all on one key expression: read from the trace, they are the decisions it works out for all nine actions when it caches a client's key expression (see step 5), not requests from goat. In the run above one subscriber declaration and one delivery also have an `unauthorized` line before their `authorized` line, from the first of the two subjects that slot 3 matches (see step 5). The last command puts the fabric router back to `info`.

To stop the step, run `dg down`. The recordings stay in the `apex-goat1_pod-records` and `apex-goat1_host-records` volumes. Don't add `-v` unless you mean to delete them. `docs/acceptance-goat1.md` records what passed and where each check falls short.

## Goat step 4: the step 1 rig on cuaslab

This step runs the rig of step 1 against a real goatnet, by configuration only. The goatnet is `cuaslab`, a goatlite that runs in a Lima VM (`goatlite`, Ubuntu 24.04, arm64, address `192.168.64.4`) on the same Mac as the rig. Its fabric router (`zenohd v1.9.0-modified`, image `ghcr.io/usareur-af/zenoh-pqc-fips`) takes the place of our stand-in `zenohd-fabric`, and its CA takes the place of the test fabric CA. The pod bridge, the host fusion node and the host recorder get slot identities from the `cuaslab` portal and connect to `tls/192.168.64.4:7447`. No program changes, and no existing file below `emulators/` changes.

- **The overlay.** `docker-compose.goat4.yml` is used on top of `docker-compose.goat1.yml`, with its own project name `apex-goat4`. It points the three fabric clients at the `cuaslab` router, mounts their files from `zenoh/goat4/pki/`, keeps `zenohd-fabric` from starting, and makes the pod's network `pod1` internal, so the pod bridge reaches the router only through `mesh`.
- **The helper.** `goat4/dg4.sh` defines `dg4` (the `dg` of step 1 with the overlay and both env files) and `goat4_ready`, which checks the seven files and `goat4.env`, that each anchor is the common name of its certificate, that no anchor is a step 1 ID, that a container reaches the router, and that the step 1 rig is down.
- **The pod side** is that of step 1: the generator `goat1/registry.toml`, the pod CA and the pod router. The step 1 rig and this rig run one at a time.

All the checks of step 4 were run from 2026-11-18 to 19 UTC against `cuaslab` as it was then: stood up from goatcore `e44e893d`, with the portal setting `portal_bundle_create_bin` turned off (see the enrolment below). These task runs were made by scripts in the working directory of the plan, which are not kept. Below each block is what the task runs printed, from the evidence files in `docs/evidence/goat4/` (the file is named with each block). The blocks are shortened.

The commands were written out for zsh after the task runs. Several blocks were rebuilt from the task runs' outputs and working scripts, not copied from a command that ran:

- step 6: `fabprobe`, and the `dg4 stop` and `dg4 up -d` around the probes;
- step 7: the probe and the two counts of the pod part of G4-05;
- step 8: the pre-check of G4-06;
- step 9: the sleeps of G4-07;
- step 11: the commands of G4-09;
- step 12: the path `../goatlite-test/env.sh`;
- step 13: the clock script.

Then the whole section was run as written, in the form it had in commit `5784f38`, on 2026-11-19 UTC (the README run). It was one `zsh -f` script with stdin at `/dev/null`, not a paste into an interactive shell, so a paste was not tested. Its transcript is `docs/evidence/goat4/readme-run.txt`; the blocks there are numbered 1 to 18 in the order of this section. Of the 18 blocks, 17 ran and one, the enrolment, was not run. 15 printed output of the form shown here (counts, times and IDs differ from run to run), 2 printed output of another form (steps 6 and 8, see the notes there), and none failed. The text beneath a block says where the README run differed. One block was changed after the README run (step 8); the note there says so. `docs/acceptance-goat4.md` records what passed and where each check falls short.

### The rig of step 4

```
 Colima VM 192.168.64.5 (Docker, project apex-goat4)          Lima VM goatlite 192.168.64.4
+---------------------------------------------------+        +-----------------------------+
|  network pod1 (internal): pod 1 as in step 1       |        |  cuaslab, a goatlite        |
|  radar, camera, vehicle, fusion-node, recorder,    |        |                             |
|  zenohd-pod (pod CA)                               |        |  fabric router              |
|            |                                       |        |  zenohd v1.9.0-modified     |
|        pod-bridge -- network mesh --+              |        |  tls/0.0.0.0:7447           |
|        (slot of pod1-bridge)        |              |        |  cuaslab goatlite CA        |
|                                     |              |        |                             |
|  network host:                      |              |        |  portal (enrolment)         |
|  host-fusion   (slot of host-fusion)|              |        |                             |
|  host-recorder (slot of host-recorder)             |        |                             |
+-------------------------------------|-------------+        +--------------|--------------+
                                      |      TLS, no WireGuard              |
                                      +---- through the Mac 192.168.64.1 ---+
```

- The three fabric clients hold certificates that the `cuaslab` portal minted. The common name of each is its anchor.
- The path between the two VMs is a route on each VM through the Mac. It is not the goat mesh: the pod is not a mesh peer.
- `goat` on the Mac (check G4-10) reaches the same router with the founder's identity of the `cuaslab` context.

### Before you run it: the path to cuaslab

The rig reaches `192.168.64.4` only through two routes and the Mac's forwarding. They are not made by anything in this repository:

- Colima: `network.address: true`, and a provision step that adds a route to `192.168.64.4` via `192.168.64.1`, in `~/.colima/default/colima.yaml`.
- The goatlite VM: `/etc/netplan/91-colima-route.yaml`, a route to `192.168.64.5` via `192.168.64.1`.
- The Mac: `net.inet.ip.forwarding=1`.

If Colima gets another address or the Mac stops forwarding, the path is lost. These three commands show the state: the first should print the value 1, and the other two a route via `192.168.64.1`. They were not run in the task runs. The README run ran them (block 1 of `readme-run.txt`): the first printed `net.inet.ip.forwarding: 1`, and the other two a route via `192.168.64.1`.

```bash
sysctl net.inet.ip.forwarding
colima ssh -- ip route get 192.168.64.4
limactl shell goatlite -- ip route get 192.168.64.5
```

The check that the runs used is (d) of `goat4_ready` below: a container on the Colima VM opens a TCP connection to `192.168.64.4:7447` within 5 s.

An agent session that cannot read `~/.docker` sets `DOCKER_HOST=unix://$HOME/.colima/default/docker.sock` and a `DOCKER_CONFIG` of its own first, as in step 1.

### Enrolment: this writes to the goatnet

**This command writes to `cuaslab`.** It sets a grant for the custodian `richard@cuaslab.lan` (quota 5, affiliation `cuaslab-lab`) if there is none, and enrols three machines, each of which takes one slot of the pool. An enrolment is undone only by a revoke, which the script does not do. In step 4 it was run twice. The first run was refused (below). The second, after Richard's decision to change a portal setting, enrolled the three machines (`task-2-enrol-refused.txt`, `task-2-decision-and-portal-change.txt`, `task-2-enrol.txt`). The README run did not run it. It does not need to be run again: the three machines are enrolled. Run it again only if you mean to enrol on a goatnet with no such machines.

`goat4/enroll.sh` reads the operator key from the line `CUASLAB_PORTAL_OPERATOR_API_KEY=` of the secrets file that you name, and never prints or keeps it. It writes the certificates, the keys (mode 0600) and the root below `zenoh/goat4/pki/`, and the three anchors to `zenoh/goat4/goat4.env`; `zenoh/goat4/` is git-ignored. It keeps no API key and no bundle token. From its source, not run in step 4: a handle that the portal already holds is skipped if its files are present, and the script stops with nothing enrolled if they are missing.

```bash
goat4/enroll.sh ../goatlite-test/goatcore/.envrc.local.d/secrets.env
```

The first run on `cuaslab` was refused (`task-2-enrol-refused.txt`):

```text
enroll.sh: pod1-bridge: enrolment refused: HTTP 500, code mint
```

The portal could not mint the bundle: the lite preset sets `portal_bundle_create_bin` to `/usr/local/bin/bundle-create`, and on the box that path is an empty directory (`task-2-refusal-diagnosis.txt`). So a goatlite stood up at goatcore `e44e893d` enrols no machine until that setting is turned off or the binary is installed. Richard chose to turn it off in `cuaslab`'s group_vars and redeploy the portal with `goatbuilder` (`task-2-decision-and-portal-change.txt`). The second run printed (`task-2-enrol.txt`):

```text
pod1-bridge 7a640b349ac2e03848531fce2000fc57
host-fusion cd42939f9c6719ea485ed176909d6d64
host-recorder 1a91baed36cf317591d4f636751af357
wrote zenoh/goat4/goat4.env
```

### Run it

Run these in order, from the repo root, with the step 1 rig down.

**1. Version pairing (G4-01), before the rig starts.** `emulators/probe_fabric_pairing.py` opens two sessions to the `cuaslab` router: a writer with the certificate of `pod1-bridge`, which puts five payloads and declares a liveliness token below its anchor, and a reader with the certificate of `host-recorder`, which subscribes to that anchor and to liveliness on it.

```bash
source zenoh/goat4/goat4.env
docker run --rm -v $PWD/zenoh/goat4/pki:/pki:ro -v $PWD/emulators:/emulators:ro  -w /emulators -e ZENOH_CONNECT=tls/192.168.64.4:7447 -e ZENOH_TLS_CA=/pki/ca.pem -e ZENOH_TLS_CERT=/pki/pod1.pem -e ZENOH_TLS_KEY=/pki/pod1.key -e READER_TLS_CA=/pki/ca.pem -e READER_TLS_CERT=/pki/host-recorder.pem -e READER_TLS_KEY=/pki/host-recorder.key apex-sapient:4.2.0 python probe_fabric_pairing.py $FABRIC_POD1_ID
```

```text
session: writer true reader true
put below anchor received: 5 of 5
liveliness token seen by reader: true
```

`task-3-g4-01.txt`; exit 0. The same probe with port 7449, and with the step 1 pod CA for the reader, printed `false` and exited 1 (`task-3-g4-01-unreachable.txt`, `task-3-g4-01-reader-bad-ca.txt`).

**2. Generate and start.** The generator makes the pod side, as in step 1. Its fabric output (the stand-in router file and the test fabric certificates) is made and not used.

```bash
. goat4/dg4.sh
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1
source zenoh/goat1/goat1.env
source zenoh/goat4/goat4.env
goat4_ready; echo "exit=$?"
dg4 up -d
sleep 45
dg4 ps --format "{{.Service}} {{.State}}" | sort
dg4 logs zenohd-pod | grep -ci -E "error|panic"
```

```text
exit=0
bridge-node running
camera running
fusion-node running
host-fusion running
host-recorder running
pod-bridge running
radar running
recorder running
vehicle running
zenohd-pod running
0
```

`task-4-start.txt`. Ten services: `zenohd-fabric` does not start. `goat4.env` is sourced after `goat1.env`, so its three anchors replace the step 1 ones in the shell, as they do in `dg4`. The block's exit status is 1, because its last `grep -c` counts 0, which is the expected output (block 4 of `readme-run.txt`). In a shell with `set -e` the block would stop there.

**3. Registration (G4-03).**

```bash
dg4 logs fusion-node | grep registration_ack
dg4 logs host-fusion | grep "<- registration "
dg4 logs pod-bridge | grep "192.168.64.4"
```

```text
fusion-node-1  | 23:50:51 fusion: -> registration_ack f0000001 -> 86ca6000 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:50:51 fusion: -> registration_ack f0000001 -> 341b9172 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:50:54 fusion: -> registration_ack f0000001 -> 1aef1b86 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:50:56 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
host-fusion-1  | 23:50:56 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
pod-bridge-1  | 23:50:51 pod-bridge: connected to Zenoh router at tls/192.168.64.4:7447
pod-bridge-1  | 23:50:51 pod-bridge: bridging tls/router.p1.h1:7447 and tls/192.168.64.4:7447 as 7a640b349ac2e03848531fce2000fc57 site p1
```

`task-4-g4-03.txt` (the run took the pod bridge's lines with `tail -15`).

**4. Tracks and alerts up (G4-02).** The recorder check is the script of step 3 of the step 1 section, with the anchors of `goat4.env`:

```bash
dg4 logs host-fusion | grep -c "<- detection_report"
dg4 logs host-fusion | grep "<- alert"
dg4 exec -T host-recorder sh -c 'cat /data/records/*.jsonl' < /dev/null | python3 -c '
import collections, json, sys
anchors, sensors = set(sys.argv[1:3]), set(sys.argv[3:6])
rows = [json.loads(line) for line in sys.stdin if line.strip()]
print("records:", len(rows))
print("anchor not the pod or the host fusion node:", sum(r.get("anchor") not in anchors for r in rows))
print("msg.node_id of the radar, camera or vehicle:", sum(r.get("msg", {}).get("node_id") in sensors for r in rows))
def paths(x, at):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from paths(v, at + "." + k)
    elif isinstance(x, list):
        for v in x:
            yield from paths(v, at + "[]")
    elif isinstance(x, str) and any(s in x for s in sensors):
        yield at
print("records that did not decode:", sum("error" in r for r in rows))
print("records with a sensor node ID anywhere:", sum(any(True for _ in paths(r, "")) for r in rows))
hits = collections.Counter((r.get("kind"), at) for r in rows for at in paths(r, ""))
for (kind, at), n in sorted(hits.items()):
    print(" ", kind, at, n)
' "$FABRIC_POD1_ID" "$FABRIC_HOST_FUSION_ID" "$POD1_RADAR_ID" "$POD1_CAMERA_ID" "$POD1_VEHICLE_ID"
```

```text
9
host-fusion-1  | 23:50:56 fusion: <- alert f0000001 ALERT_TYPE_INFORMATION "new track DF0FB8"
records: 192
anchor not the pod or the host fusion node: 0
msg.node_id of the radar, camera or vehicle: 0
records that did not decode: 0
records with a sensor node ID anywhere: 0
```

`task-4-g4-02.txt`. The script that ran also printed the count of each anchor (`anchors seen`: 100 records below the pod's anchor and 92 below the host fusion node's); that line is not in the script above, and the exact text of the script that ran was not saved. With the project name `apex-goat4` the host recorder writes to the volume `apex-goat4_host-records`, not to the step 1 volume (from the compose files; the addendum of Task 6 found only step 1 anchors in the step 1 volume). Whether that volume held records of an earlier start was not recorded.

**5. A task down (G4-04).**

```bash
dg4 logs radar camera | grep "<- task .* look_at" | cut -c1-90
dg4 logs host-fusion | grep "<- task_ack" | grep TASK_STATUS_ACCEPTED
dg4 logs host-fusion | grep -ci -E "reject|stale|too old|timestamp"
```

```text
radar-1  | 23:51:31 radar: <- task f0000001 -> 1aef1b86 8S8H0W look_at {"location_list": {
camera-1  | 23:51:31 camera: <- task f0000001 -> 86ca6000 VSCMPX look_at {"location_list":
host-fusion-1  | 23:51:11 fusion: <- task_ack f0000001 -> f0000002 PGTVNM TASK_STATUS_ACCEPTED ['Status report sent']
host-fusion-1  | 23:51:31 fusion: <- task_ack f0000001 -> f0000002 CZ8V82 TASK_STATUS_ACCEPTED ['look_at sent to 2 nodes']
0
```

`task-4-g4-04.txt`. The last count looks for a message the host rejected for its time; there was none. As in step 2, the block's exit status is 1 because the last count is 0, the expected output (block 7 of `readme-run.txt`).

**6. Access on the fabric (G4-05, fabric part).** The `cuaslab` router logs no access decision, and we do not change its log level. So a refused write is shown by absence: a reader gets nothing below the foreign anchor, while a control write by the same certificate below its own anchor, in the same window, arrives. The rig's three fabric clients are stopped first, so no other traffic is below the two anchors. `fabprobe` runs `emulators/probe_access.py` in a one-off container with one of the three certificates of `zenoh/goat4/pki/`; the reader uses the certificate of `host-recorder`.

```bash
fabprobe() { local cert=$1; shift; docker run --rm --network bridge -v "$PWD/emulators:/emulators:ro" -v "$PWD/zenoh/goat4/pki:/pki:ro" -w /emulators -e ZENOH_CONNECT=tls/192.168.64.4:7447 -e ZENOH_TLS_CA=/pki/ca.pem -e ZENOH_TLS_CERT=/pki/$cert.pem -e ZENOH_TLS_KEY=/pki/$cert.key apex-sapient:4.2.0 python probe_access.py "$@" < /dev/null; }
P=a0000009-0000-4000-8000-000000000009
dg4 stop pod-bridge host-fusion host-recorder
fabprobe host-recorder sub "$FABRIC_HOST_FUSION_ID/**" 20 &
fabprobe host-recorder sub "$FABRIC_POD1_ID/**" 20 &
sleep 8
fabprobe pod1 put "$FABRIC_HOST_FUSION_ID/task/p1/sapient/v2/task/$POD1_FUSION_NODE_ID"
fabprobe pod1 put "$FABRIC_POD1_ID/telemetry/sapient/p1/v2/status_report/$P"
wait
fabprobe host-recorder sub "$FABRIC_POD1_ID/**" 20 &
fabprobe host-recorder sub "$FABRIC_HOST_FUSION_ID/**" 20 &
sleep 8
fabprobe host-fusion put "$FABRIC_POD1_ID/telemetry/sapient/p1/v2/alert/$POD1_FUSION_NODE_ID"
fabprobe host-fusion put "$FABRIC_HOST_FUSION_ID/task/p1/sapient/v2/task/$POD1_FUSION_NODE_ID"
wait
dg4 up -d
```

The run saved each probe's output apart; here they are in the order of the evidence file (`task-5-g4-05-fabric.txt`), without the probes' `connected` lines. Direction 1, the pod's slot certificate writes below the host fusion node's anchor:

```text
put: 1 status report on cd42939f9c6719ea485ed176909d6d64/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
put: 1 status report on 7a640b349ac2e03848531fce2000fc57/telemetry/sapient/p1/v2/status_report/a0000009-0000-4000-8000-000000000009
samples: 0 on cd42939f9c6719ea485ed176909d6d64/** in 20 s; from this probe: 0
samples: 1 on 7a640b349ac2e03848531fce2000fc57/** in 20 s; from this probe: 1
```

Direction 2, the host fusion node's certificate writes below the pod's anchor (`task-5-g4-05-fabric.txt`):

```text
put: 1 status report on 7a640b349ac2e03848531fce2000fc57/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001
put: 1 status report on cd42939f9c6719ea485ed176909d6d64/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
samples: 0 on 7a640b349ac2e03848531fce2000fc57/** in 20 s; from this probe: 0
samples: 1 on cd42939f9c6719ea485ed176909d6d64/** in 20 s; from this probe: 1
```

In each direction the foreign anchor got 0 samples and the control 1, from this probe. `put` prints the same line whether the router took the write or dropped it: a denial is silent for the writer. On `cuaslab` every TLS client may subscribe to `**`, so the step 1 case "a subscription to `**` is refused" does not apply and is not run.

The output above leaves lines out: the evidence file also holds each probe's `connected` line and an `e.g.` line with a key after each `samples: 1` line. In the task run each probe's output was saved apart. Run as the block is written, the probes print to one terminal and the readers run in the background, so the lines come mixed, in the order the probes print them. In the README run (block 8 of `readme-run.txt`) the output held the `connected` and `e.g.` lines, and in direction 1 the control's `samples` line came before the foreign anchor's. The counts were the same: 0 on the foreign anchor and 1 on the control, in both directions.

**7. Access in the pod (G4-05, pod part).** Case 4 of step 1, with `dg4`: the radar's certificate puts on the camera's up key. Restart the pod router with the access-control trace, probe, count, and put the router back to `info`.

```bash
probe() { local service=$1; shift; dg4 run --rm --no-deps -T "$service" python probe_access.py "$@" < /dev/null; }
ZENOHD_RUST_LOG=zenoh::net::routing::interceptor=trace dg4 up -d zenohd-pod
sleep 20
K="h1/p1/sapient/v2/$POD1_CAMERA_ID/up/status_report"
T=$(date +%s)
probe recorder sub "$K" 15 &
sleep 5
probe radar put "$K"
wait
dg4 logs --since "$T" zenohd-pod | grep -F "$K" | grep -F "CertCommonName($POD1_RADAR_ID)" | grep -c "is unauthorized to Put (ingress)"
dg4 logs --since "$T" zenohd-pod | grep -F "$K" | grep -F "CertCommonName($POD1_RADAR_ID)" | grep -c "is authorized to Put (ingress)"
dg4 up -d zenohd-pod
```

```text
put: 1 status report on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report
samples: 3 on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report in 15 s; from this probe: 0
1
0
```

`task-5-g4-05-pod.txt`. The three samples are the camera's own status reports.

**8. Short outage (G4-06).** First confirm that the bridge has no other way out: with `mesh` disconnected, it is on the internal network `pod1` only and cannot open `192.168.64.4:7447`.

```bash
docker network disconnect apex-goat4_mesh apex-goat4-pod-bridge-1
docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' apex-goat4-pod-bridge-1
docker exec apex-goat4-pod-bridge-1 python -c 'import socket
try:
    socket.create_connection(("192.168.64.4", 7447), timeout=5).close(); print("connected")
except OSError as e:
    print("cannot connect:", repr(e))'
docker network connect apex-goat4_mesh apex-goat4-pod-bridge-1
docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' apex-goat4-pod-bridge-1
```

```text
apex-goat4_pod1
cannot connect: OSError(101, 'Network is unreachable')
apex-goat4_mesh apex-goat4_pod1
```

`task-5-g4-06-precheck.txt`. Then step 7 of the step 1 section, with the names of `apex-goat4`. The host's hold time is 120 s. The block starts with a wait of 60 s, so that the pod has settled after step 7, which ends by recreating `zenohd-pod`.

```bash
sleep 60
docker network disconnect apex-goat4_mesh apex-goat4-pod-bridge-1
sleep 30
dg4 logs --since 30s radar camera vehicle fusion-node | grep -c -E "lost|cannot reach"
dg4 logs --since 30s fusion-node | grep -c "<- detection_report"
docker network connect apex-goat4_mesh apex-goat4-pod-bridge-1
sleep 30
dg4 logs --since 25s host-fusion | grep -c "<- detection_report"
dg4 logs --since 60s host-fusion | grep -c "<- registration "
dg4 logs --since 70s pod-bridge
```

```text
0
6
3
0
pod-bridge-1  | 23:59:29 pod-bridge: fabric router lost
pod-bridge-1  | 23:59:36 pod-bridge: forwarded {'up': 164, 'down': 8}; dropped {'other_side_down': 8}
pod-bridge-1  | 23:59:56 pod-bridge: fabric router back
pod-bridge-1  | 00:00:06 pod-bridge: forwarded {'up': 175, 'down': 8}; dropped {'other_side_down': 29}
```

`task-5-g4-06.txt`. The run printed the time `23:59:24` just before the disconnect and `23:59:54` just after the connect.

The first line, `sleep 60`, was added after the README run, and the block with it was not run again. In the README run (block 11 of `readme-run.txt`) the block had no wait and followed step 7 and the pre-check at once. Its first count printed 1, not 0; the other counts were 6, 3 and 0. The bridge's log in that block begins with `pod-bridge-1  | 00:33:14 pod-bridge: pod router lost`, in the second in which the step 7 block, whose last command recreates `zenohd-pod`, ended (00:33:14 in the transcript). That the counted line came from this restart is inferred, not shown: the count prints no line, and the logs were gone when the cause was looked for. Whether 60 s is long enough was not tested.

**9. Long outage (G4-07).** Step 8 of the step 1 section, with `dg4`, and `goat4_ready` before the start. The last line puts the hold time back to 120 s.

```bash
dg4 down
goat4_ready; echo "goat4_ready exit $?"
HOST_HOLD_SECONDS=20 dg4 up -d
sleep 60
docker network disconnect apex-goat4_mesh apex-goat4-pod-bridge-1
sleep 40
docker network connect apex-goat4_mesh apex-goat4-pod-bridge-1
sleep 40
dg4 logs host-fusion | grep -E 'removed|request "Registration"|<- registration '
dg4 logs fusion-node | grep "<- registration_ack f0000002"
dg4 up -d
```

```text
goat4_ready exit 0
host-fusion-1  | 00:01:09 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
host-fusion-1  | 00:02:33 fusion: node f0000001 gone for 20 s; removed
host-fusion-1  | 00:02:51 fusion: -> task f0000002 -> f0000001 XART4Y request "Registration"
host-fusion-1  | 00:02:51 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
fusion-node-1  | 00:01:09 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 00:02:51 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node (re-registration)']
```

`task-5-g4-07.txt`. The first registration is the one at start; the other lines follow the outage.

**10. An old task (G4-08).** The unit test of G1-08, unchanged.

```bash
docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -p no:cacheprovider -v -W error tests/test_pod_bridge.py -k "stale or 4_s_old or age_limit"
```

```text
tests/test_pod_bridge.py::test_down_drops_and_counts[stale_task] PASSED  [ 25%]
tests/test_pod_bridge.py::test_a_task_4_s_old_is_forwarded PASSED        [ 50%]
tests/test_pod_bridge.py::test_a_task_without_a_timestamp_is_stale PASSED [ 75%]
tests/test_pod_bridge.py::test_registration_ack_is_not_subject_to_the_age_limit PASSED [100%]
======================= 4 passed, 35 deselected in 0.03s =======================
```

`task-5-g4-08.txt`.

**11. A sensor joins with no router restart (G4-09).** Step 9 of the step 1 section, with `dg4` and the container `apex-goat4-zenohd-pod-1`. This is inside the pod.

```bash
before=$(docker inspect -f '{{.State.StartedAt}}' apex-goat4-zenohd-pod-1)
shasum -a 256 zenoh/goat1/router-pod1.json5 zenoh/goat1/router-fabric.json5
python3 -c 'import pathlib; p = pathlib.Path("goat1/registry.toml"); p.write_text(p.read_text().replace("[pod1.slots]\n", "[pod1.slots]\nradar2 = 3\n", 1))'
grep -A4 '^\[pod1.slots\]' goat1/registry.toml
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1 --frozen-routers
echo "exit $?"
shasum -a 256 zenoh/goat1/router-pod1.json5 zenoh/goat1/router-fabric.json5
source zenoh/goat1/goat1.env
source zenoh/goat4/goat4.env
dg4 --profile join up -d radar2
sleep 30
dg4 logs fusion-node | grep "<- registration " | grep -c "Fake second radar"
dg4 logs fusion-node | grep "registration_ack f0000001 -> ${POD1_RADAR2_ID:0:8}"
dg4 logs fusion-node | grep -c "<- detection_report ${POD1_RADAR2_ID:0:8}"
test "$before" = "$(docker inspect -f '{{.State.StartedAt}}' apex-goat4-zenohd-pod-1)" && echo "router not restarted"
dg4 logs zenohd-pod | grep -ci -E 'error|panic'
```

```text
c3a5e2b99a4a843d0322ddddd5dde61cf5c9796a25bb1d962af9c9b519b84627  zenoh/goat1/router-pod1.json5
f7f5e342377767ddcf0e22d754d22236f1417967dcd2891927b6aea54a3bedf8  zenoh/goat1/router-fabric.json5
[pod1.slots]
radar2 = 3
radar = 0
camera = 1
vehicle = 2
router files unchanged
exit 0
1
fusion-node-1  | 00:04:23 fusion: -> registration_ack f0000001 -> 83ff6077 acceptance=True ['Accepted by fake fusion node']
4
router not restarted
0
```

`task-5-g4-09.txt` (shortened: it also prints the router's `StartedAt` before and after, and its own headings). As in step 2, the block's exit status is 1 because the last count is 0, the expected output (block 14 of `readme-run.txt`). Take `radar2` out again and put the registry back as committed:

```bash
dg4 --profile join rm -s -f radar2
git restore goat1/registry.toml
unset POD1_RADAR2_ID
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1 --frozen-routers
echo "exit $?"
git status --short goat1/registry.toml
```

```text
router files unchanged
exit 0
```

`task-5-g4-09.txt`. The last command prints nothing when the registry is as committed.

**12. goat's own client reads the pod's tracks (G4-10).** On the Mac, with the released `goat` 0.5.19 and its context `cuaslab`, which holds the founder's identity of the goatlite. `../goatlite-test/env.sh` sets goat's environment for that checkout; it is sourced in a subshell. `--keys-only` keeps the payload out of the output.

```bash
( . ../goatlite-test/env.sh; goat --context cuaslab sub "$FABRIC_POD1_ID/**" --keys-only --uuid --for 30s --color never )
```

```text
listening on `7a640b349ac2e03848531fce2000fc57/**` via tls/192.168.64.4:7447 — streaming live events. Ctrl-C to stop.
done after 30s — 36 event(s) on `7a640b349ac2e03848531fce2000fc57/**`
```

`task-5-g4-10.txt`. goat printed 36 keys, every one below the pod's anchor: 30 detection reports, 4 status reports and 2 task acknowledgements of the pod's fusion node. The evidence file holds their counts, not the 36 lines.

**13. Clocks (G4-13).** A measurement, with no pass value. The script reads each VM's clock 30 times between two readings of the Mac's clock, keeps the round with the shortest round trip, and takes the offset as the VM's time minus the middle of the two Mac readings and the bound as half that round trip.

```bash
python3 - <<'EOF'
import subprocess, time, sys
def run(cmd):
    t0 = time.time()
    out = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[-1]
    t1 = time.time()
    return t0, float(out), t1
vms = {"colima": ["colima","ssh","-p","default","--","date","+%s.%N"],
       "goatlite": ["limactl","shell","goatlite","--","date","+%s.%N"]}
res = {}
for name, cmd in vms.items():
    rounds = []
    for i in range(30):
        t0, v, t1 = run(cmd)
        rounds.append((t1 - t0, v - (t0 + t1) / 2, i))
    rounds.sort()
    rtts = [r[0] for r in rounds]
    print(f"{name}: 30 rounds; rtt min {rtts[0]*1000:.1f} ms, median {rtts[15]*1000:.1f} ms, max {rtts[-1]*1000:.1f} ms")
    rtt, off, i = rounds[0]
    print(f"{name}: best round #{i}: offset (VM - Mac) = {off*1000:+.1f} ms, bound = +/-{rtt/2*1000:.1f} ms")
    res[name] = (off, rtt/2)
d = res["goatlite"][0] - res["colima"][0]
b = res["goatlite"][1] + res["colima"][1]
print(f"goatlite minus colima = {d*1000:+.1f} ms, bound = +/-{b*1000:.1f} ms (sum of bounds)")
for n,(o,bb) in res.items():
    if bb > 0.05: print(f"NOTE: {n} bound {bb*1000:.1f} ms is above 50 ms")
EOF
```

```text
colima: 30 rounds; rtt min 191.8 ms, median 207.6 ms, max 305.4 ms
colima: best round #15: offset (VM - Mac) = +96.3 ms, bound = +/-95.9 ms
goatlite: 30 rounds; rtt min 56.5 ms, median 65.0 ms, max 77.5 ms
goatlite: best round #6: offset (VM - Mac) = +26.5 ms, bound = +/-28.2 ms
goatlite minus colima = -69.8 ms, bound = +/-124.1 ms (sum of bounds)
NOTE: colima bound 95.9 ms is above 50 ms
```

`task-5-g4-13.txt`. The plan asked for a method good to 50 ms. `colima ssh` takes 192 ms at best for a round trip, so the Colima value has a bound of about 96 ms, and the difference between the two VMs is known only to within 124 ms.

**14. No regression (G4-11) and configuration only (G4-12).** Stop this rig, run the unit suite, then run steps 1 to 3 of the step 1 section (the step 1 rig, G1-02 and G1-03) and `dg down`. Last, the diff of the branch:

```bash
dg4 down
docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -p no:cacheprovider -q -W error tests
git diff goat --diff-filter=MDR --stat -- emulators/
git diff goat --name-status
```

```text
454 passed in 15.55s
```

`task-6-unit-suite.txt`. The first `git diff` printed nothing: no existing file below `emulators/` is modified, deleted or renamed. The second, at `11a9db4`, listed `.gitignore` as modified, and as added the overlay, `goat4/dg4.sh`, `goat4/enroll.sh`, `goat4/test_enroll.py`, `emulators/probe_fabric_pairing.py` and files below `docs/` (`task-6-g4-12.txt`). In the README run, on top of `5784f38`, it also listed `README-goat.md` as modified, because that commit added this section, and more files below `docs/` (block 18 of `readme-run.txt`). The plan allows all of these: the overlay, `goat4/`, `emulators/probe_fabric_pairing.py`, `.gitignore`, and files below `docs/` and `README-goat.md`. The step 1 rig's output is in `task-6-step1-rig.txt` and `task-6-addendum.txt`. The README run also ran steps 1 to 3 of the step 1 section and `dg down`, after `apex-goat4` was down, at the end of `readme-run.txt`; they printed output of the form shown in the step 1 section.

To stop the step, run `dg4 down`. The recordings stay in the volumes `apex-goat4_pod-records` and `apex-goat4_host-records`. The grant and the three machines stay on `cuaslab`; `docs/acceptance-goat4.md` lists them, so that they can be revoked later.
