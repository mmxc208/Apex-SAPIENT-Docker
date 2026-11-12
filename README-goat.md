# The goat network work: SAPIENT pods on a goat fabric

This file is the entry page for the goat work in this repository. [`README.md`](README.md) covers the base rig (Apex in Docker and the fake nodes) and the four Zenoh stages that this work builds on.

goat is the open source network of United States Army Europe and Africa: a mesh, a Zenoh data fabric, identities and a CA. The goal of this work is a real goatnet with three parts: pod 1 at the edge, a host in a cloud or a data centre, and an external host that belongs to a different sovereign. The work has six steps.

| Step | Content | Status |
|---|---|---|
| 1 | Pod 1 to host, on a stand-in fabric that follows goat's rules | Done on 2026-11-12 (UTC). The section below has the drawings and the run steps. |
| 2 | Stone Soup in the fusion node | Not started |
| 3 | Billie adapter for a sensor with a vendor protocol | Not started |
| 4 | The host on a real goatnet (a goatlite) | Not started |
| 5 | Pod 2 | Not started |
| 6 | External host, the second sovereign | Not started |

## Documents

| File | Content |
|---|---|
| `docs/goat-roadmap.md` | The six steps: what is decided, what is open, and how a step is started |
| `docs/goat-context.md` | The goat rules that this work follows, with a source for each rule |
| `docs/superpowers/specs/2026-11-11-goat-step1-pod-to-host-design.md` | The design of step 1 |
| `docs/superpowers/plans/2026-11-11-goat-step1-pod-to-host.md` | The plan of step 1 |
| `docs/acceptance-goat1.md` | The acceptance record of step 1: checks G1-01 to G1-11, the known limits, and the open items for step 4 |
| `docs/evidence/goat1/` | The saved outputs and logs that the record and this file quote, with an index and a quote checker |

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
