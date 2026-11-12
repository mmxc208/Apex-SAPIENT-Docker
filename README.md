# Apex SAPIENT in Docker, with fake v2.0 nodes

This repo runs Dstl's [Apex SAPIENT middleware](https://github.com/dstl/Apex-SAPIENT-Middleware) headless (no Qt GUI) in a Linux container on a Mac, through [Colima](https://github.com/abiosoft/colima).
It also has a fake BSI Flex 335 v2.0 fusion node, radar, camera and vehicle, for testing the whole v2.0 message flow through Apex without real hardware.

The Apex source is not part of this repo. The build takes it from a separate checkout, by default `../Apex-SAPIENT-Middleware`:

```
cuas/
├── Apex-SAPIENT-Middleware/   # Apex source (unchanged)
└── Apex-SAPIENT-Docker/       # this repo
```

To use a checkout somewhere else, set `APEX_DIR` before building, for example `export APEX_DIR=~/src/Apex-SAPIENT-Middleware`.
It was tested on an Apple Silicon Mac (arm64) with Colima 0.10.3, Docker 29.9.0 and Docker Compose 5.6.0.
It should also work on Linux, and with Docker Desktop instead of Colima.

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the image: Python 3.11, Apex's `requirements.txt`, then Apex itself, taken from `APEX_DIR` |
| `docker-compose.yml` | Runs Apex, maps its ports, keeps the SQLite archive in a volume |
| `docker-compose.elastic.yml` | Adds Elasticsearch, which the REST API's data endpoints need (see "Optional: Elasticsearch and the REST API") |
| `apex_config.json` | Apex config for the container (see "Differences from the repo config") |
| `smoke_test.py` | Sends one v2.0 Registration and prints Apex's reply |
| `docker-compose.emulators.yml` | Adds a fake fusion node, radar, camera and vehicle (see "Fake sensors and fusion node") |
| `apex_config.emulators.json` | Apex config for the emulators: v2.0 Peer port, `sendRegistrationAck: false` |
| `emulators/` | The fake nodes (`fake_sensor.py`, `fake_fusion_node.py`, `sapient_link.py`), the Test Harness message templates they use, the Zenoh bridges (`bridge_node_side.py`, `bridge_apex_side.py`), `recorder.py`, the Zenoh helpers (`zenoh_io.py`, `zenoh_keys.py`) and the unit tests |
| `docker-compose.zenoh.yml` | Adds the `zenohd` router and both bridges (stages 1 and 2) |
| `docker-compose.zenoh-sensors.yml` | Points the TCP sensors at `bridge-node` (stage 1) |
| `docker-compose.native-sensors.yml` | Makes the sensors speak Zenoh directly (stage 2) |
| `docker-compose.native.yml` | Standalone Zenoh-only rig, no Apex (stage 3) |
| `docker-compose.pod1.yml` | Standalone pod with mutual TLS and access control (stage 4) |
| `zenoh/` | Router configs (`router-plain.json5`, `router-pod1.json5`) and `pki/make_certs.sh` |
| `docs/acceptance.md` | What has been measured for each stage, what is still open, and the sign-off |

## SAPIENT over Zenoh: the four stages

Stages 1 to 4 move the rig from TCP to a hardened Zenoh pod, one change at a time. Each stage has its own section below, with the commands to run and what one run printed. Bring a stage down before starting the next. `docs/acceptance.md` records what passed and what is open.

| Stage | What changes | Compose files | Project | Checks |
|---|---|---|---|---|
| [1](#stage-1-option-a-bridge) | TCP sensors reach Apex over Zenoh through two bridges | `docker-compose.yml`, `docker-compose.emulators.yml`, `docker-compose.zenoh.yml`, `docker-compose.zenoh-sensors.yml` | `apex` | T-01 to T-05 |
| [2](#stage-2-native-zenoh-sensors) | Sensors speak Zenoh directly; start with `--scale bridge-node=0` | `docker-compose.yml`, `docker-compose.emulators.yml`, `docker-compose.zenoh.yml`, `docker-compose.native-sensors.yml` | `apex` | T-01, T-02 |
| [3](#stage-3-zenoh-native-rig-without-apex) | No Apex and no bridges; the fusion node validates, and a recorder keeps every message | `docker-compose.native.yml` | `apex-native` | Registrations, late joiner, recorder, validation |
| [4](#stage-4-pod-1-with-mutual-tls-and-access-control) | Mutual TLS, access control per certificate, a legacy sensor behind the bridge, and the pod registering upward | `docker-compose.pod1.yml` | `apex-pod1` | The stage 3 checks, T-07, T-08, T-11 (partial) |

Unit tests: `docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -p no:cacheprovider -q -W error tests`.

## 1. Install the tools (once)

You need [Homebrew](https://brew.sh). Then:

```bash
brew install colima docker docker-compose docker-buildx
```

Homebrew installs Compose and Buildx as Docker CLI plugins, but the `docker` command must be told where they are.
Add this to `~/.docker/config.json` (create the file if needed, and merge it with any keys already there):

```json
{
  "cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]
}
```

Check:

```bash
docker compose version
docker buildx version
```

## 2. Start Colima

Colima runs a small Linux VM that hosts the Docker engine. Nothing runs until you start it:

```bash
colima start
```

The first start downloads the VM image and takes a few minutes. Later starts take seconds.
The defaults (2 CPUs, 2 GiB memory) are enough for Apex. To run Elasticsearch as well, give the VM more memory:

```bash
colima start --cpu 4 --memory 6
```

Check that Docker can reach the engine:

```bash
docker info --format '{{.ServerVersion}} {{.Architecture}}'
```

If this prints `failed to connect to the docker API`, Colima isn't running, or Docker is using another context. Run `docker context use colima`.

Wait until the VM's clock is synchronized. This should print `yes`:

```bash
colima ssh -- timedatectl show -p NTPSynchronized --value
```

This matters because Apex rejects a message whose timestamp is more than 0.1 s ahead of its own clock (see Troubleshooting).
Just after `colima start`, the VM clock can be that far behind the Mac's.

## 3. Build and start Apex

Run every command below from this repo's folder:

```bash
cd Apex-SAPIENT-Docker
docker compose up -d --build
```

The first build takes a minute or two. Watch Apex start:

```bash
docker compose logs -f apex
```

Apex is ready when you see:

```
INFO apex: Database opened and tables created
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

Press Ctrl+C to stop watching; Apex keeps running.

## 4. Check that it works

Send a v2.0 Registration and expect a `registration_ack` with `acceptance: true`.

Run the test from inside the container. This needs no Python on the Mac:

```bash
docker compose exec -T apex python - < smoke_test.py
```

Or run it from the Mac, through the published port. This needs Python 3.9–3.11 with protobuf:

```bash
python3 -m venv .venv && .venv/bin/pip install protobuf==4.25.1 ulid-py==1.1.0
export PYTHONPATH=${APEX_DIR:-../Apex-SAPIENT-Middleware}   # for sapient_msg
.venv/bin/python smoke_test.py 5020
```

Expected output:

```
reply type: registration_ack
node_id: "5913c0f4-9f89-4c01-ab90-939099797c4f"
registration_ack {
  acceptance: true
}
```

If a field is missing, Apex replies with an `error` and names the field, for example `Missing mandatory repeated field: mode_definition`.
That also means the connection works. Apex validated the message and rejected it.

To check the REST API, open <http://127.0.0.1:8080/docs>. The data endpoints return 503 until you add Elasticsearch (see "Optional: Elasticsearch and the REST API"). To check the archive:

```bash
docker compose exec apex sh -c 'ls -l data/'
```

## Ports

| Mac port | Container port | Connection type | Format |
|---|---|---|---|
| **5050** | 5000 | Child (sensors) | XML, ICD v6 |
| 5010 | 5010 | Child (sensors) | BSI Flex 335 v1.0 |
| 5020 | 5020 | Child (sensors) | BSI Flex 335 v2.0 |
| 5001 | 5001 | Peer (fusion node) | BSI Flex 335 v1.0 |
| 5002 | 5002 | Parent (C2) | BSI Flex 335 v1.0 |
| 5003 | 5003 | Recorder | BSI Flex 335 v1.0 |
| 5004 | 5004 | Parent, forwardAll | Proto, no conversion |
| 8080 | 8080 | REST API; data endpoints need Elasticsearch | HTTP |

The XML port is **5050 on the Mac**, because macOS's AirPlay Receiver already listens on port 5000.
Other containers on the same Compose network still reach it as `apex:5000`.

## Changing the config

Edit `apex_config.json` in this repo, then restart. The file is mounted into the container, so no rebuild is needed:

```bash
docker compose restart apex
```

If you add a connection on a new port, also add it under `ports:` in `docker-compose.yml`, then run `docker compose up -d`.

### Differences from the repo config

`apex_config.json` here is a copy of the `apex_config.json` in the Apex repo, with three changes:

1. **`apiConfig.host` is `0.0.0.0`.** With `127.0.0.1`, the REST API is reachable only from inside the container.
2. **The outbound Parent connection to `127.0.0.1:10000` is removed.** Inside a container, `127.0.0.1` is the container itself. To connect to a C2 system running on the Mac, add the connection back with `"host": "host.docker.internal"`.
3. **`elasticConfig` points at the `elasticsearch` container, without SSL.** It stays disabled (`"enabled": false`); `docker-compose.elastic.yml` turns it on at startup.

### Testing a v2.0 fusion node

The Peer connection (port 5001) is set to **v1.0**, as in the repo config.
For a v2.0 fusion node, change that connection's `icd_version` to `"BSI Flex 335 v2.0"`.
Otherwise Apex converts v2.0 messages down to v1.0, and v2.0-only content (platforms, hierarchy, follow and patrol tasks) is lost.
For BSI Flex 335 v2.0's "transparent middleware" rule, also set `"sendRegistrationAck": false` at the top level of the config (not inside a connection), so that the fusion node sends the acknowledgements itself.

## Fake sensors and fusion node

Dstl's SAPIENT Test Harness has its own sensor (ASM) and fusion-node (DMM) simulators, but they are Windows Forms apps and need PostgreSQL 12.
The `emulators/` folder has small Python stand-ins that run next to Apex in Docker.
They build every message from the Test Harness's own v2.0 JSON templates (`emulators/templates/`), and fill in live IDs, times, positions and commands.

### What runs

```
 radar  ─┐                                 ┌─> fusion-node  (Peer 5001, v2.0)
 camera ─┼─> Apex  (Child 5020, v2.0) ─────┤
 vehicle─┘    │                            └─< tasks, RegistrationAcks, fused tracks
              └─> Parent 5002: fused tracks only (for a C2 display)
```

| Service | Node ID | Node type | Behaviour |
|---|---|---|---|
| `fusion-node` | `f0000001-…` | Fusion node | Sends every RegistrationAck itself. Merges detections within 100 m into one track and publishes it about once a second. Accepts alerts. Tasks the nodes every 20 s (see below). |
| `radar` | `a0000001-…` | `RADAR` | Registers, sends a status report every 5 s and a detection every second. Accepts `look_at`, `mode_change`, thresholds and requests. |
| `camera` | `a0000002-…` | `CAMERA` | Same as the radar, from a different place. |
| `vehicle` | `a0000003-…` | `MOBILE_NODE` | A v2.0 platform that lists the camera in `dependent_nodes`. It sends no detections. It accepts `move_to`, `patrol`, `follow` and requests, and moves at 10 m/s. Its status reports carry a `STATUS_TYPE_PLATFORM` entry: `moving` or `holding`. |

Each node rejects any other command with a `TaskAck` of `TASK_STATUS_REJECTED`, `"Task not supported: … nodes cannot do …"`.

There is one drone. It circles a fixed point at 250 m radius, 120 m altitude and 12 m/s, classed as `Air Vehicle` / `UAV Rotary Wing` / `Commercial`.
Every sensor works out the drone's position from the clock, so the radar and camera report the same drone, each with its own object ID. The fusion node joins them into one track.

The fusion node cycles through these tasks, sending one every 20 s:

| Task | Sent to | Content |
|---|---|---|
| `look_at` | sensors (not mobile platforms) | the newest track's position |
| `move_to` | mobile platforms | 200 m north-east of the platform |
| `follow` | mobile platforms | the newest track's ID |
| `patrol` | mobile platforms | a 150 m square, starting at the platform |
| `request:Status` | every node | asks for a status report |

### Start them

From this repo's folder, with Colima running (steps 1–2):

```bash
docker compose -f docker-compose.yml -f docker-compose.emulators.yml up -d --build
```

This starts Apex with `apex_config.emulators.json`, which differs from `apex_config.json` in two ways:

- The Peer connection (port 5001) uses `BSI Flex 335 v2.0`, so v2.0 tasks reach the fusion node unconverted.
- `sendRegistrationAck` is `false`. BSI Flex 335 v2.0 says middleware must be transparent, so the fusion node, not Apex, accepts each node.
  Until a fusion node connects, sensors get no acknowledgement. They re-send their registration every 10 s.

Watch the conversation:

```bash
docker compose -f docker-compose.yml -f docker-compose.emulators.yml logs -f fusion-node radar camera vehicle
```

A shorter command: `export COMPOSE_FILE=docker-compose.yml:docker-compose.emulators.yml`, then plain `docker compose logs -f`, `docker compose ps` and so on.

Expected output (shortened):

```
fusion: <- registration a0000003 "Fake vehicle (mobile platform)" [MOBILE_NODE] carries ['a0000002']
fusion: -> registration_ack f0000001 -> a0000003 acceptance=True ['Accepted by fake fusion node']
fusion: new track PQ90BT from Fake radar
fusion: auto-task look_at -> 2 node(s)
radar: <- task f0000001 -> a0000001 Y5VB9D look_at {"location_list": ...}
radar: -> task_ack a0000001 -> f0000001 Y5VB9D TASK_STATUS_ACCEPTED ['Pointing at (51.17391, -1.81934)']
vehicle: -> task_ack a0000003 -> f0000001 5XVSTM TASK_STATUS_ACCEPTED ['Following object 01M5W7AREHRRHBY1W6P39XJH2J']
vehicle: reached waypoint (51.17570, -1.81868)
```

Detections are logged every 10th message. Status reports are logged only when something changed (`INFO_NEW`).

### Send tasks by hand

Attach to the fusion node's console:

```bash
docker attach --detach-keys="ctrl-x" apex-fusion-node-1
```

Type `help`, or:

| Command | Effect |
|---|---|
| `nodes` | List registered nodes: ID, short name, name, type |
| `tracks` | List fused tracks |
| `task look_at vehicle` | Send a task to one node: an ID prefix, a short name (`radar`, `camera`, `vehicle`), or part of a name |
| `task move_to` | With no node: send to the nodes the task is meant for (see the table above) |
| `task mode_change:Night camera` | Mode change, with the mode name after `:` |
| `task request:Stop radar` | `request:Status`, `Start`, `Stop`, `Reset` or `Registration` (`Stop` pauses detections) |
| `task detection_threshold radar` | Also `detection_report_rate` and `classification_threshold` (Test Harness "Medium" templates) |

Press **Ctrl+X** to detach. Ctrl+C would stop the fusion node; it then restarts automatically.

To turn off automatic tasking, set `AUTO_TASK: ""` for `fusion-node` in `docker-compose.emulators.yml`, then run `up -d` again.

### See what a C2 display gets

The fusion node's tracks have no destination, so Apex sends them to its Parent connections. Listen on Parent port 5002 (v1.0) from the Mac:

```bash
PYTHONPATH=${APEX_DIR:-../Apex-SAPIENT-Middleware} .venv/bin/python - <<'EOF'
import socket, struct
from sapient_msg.bsi_flex_335_v1_0.sapient_message_pb2 import SapientMessage
s = socket.create_connection(("127.0.0.1", 5002))
for _ in range(5):
    n = struct.unpack("<I", s.recv(4, socket.MSG_WAITALL))[0]
    m = SapientMessage.FromString(s.recv(n, socket.MSG_WAITALL))
    print(m.WhichOneof("content"), m.node_id[:8], m.detection_report.object_id)
EOF
```

In testing, this got only `detection_report` messages from `f0000001`, the fused tracks, about one a second. Raw sensor detections don't reach Parent connections.

### Change the scenario

Each emulated node takes command-line options, or the matching environment variables in `docker-compose.emulators.yml`:

| `fake_sensor.py` option | Variable | Default |
|---|---|---|
| `--node-type` | `NODE_TYPE` | `RADAR`. Any v2.0 node type: `CAMERA`, `PASSIVE_RF`, `MOBILE_NODE`, `POINTABLE_NODE`, … |
| `--node-id`, `--name`, `--short-name` | `NODE_ID`, `NODE_NAME`, `NODE_SHORT_NAME` | random UUID, `Fake radar`, `radar` |
| `--dependent-node` | `DEPENDENT_NODES` (comma-separated) | none. For platforms: the node IDs they carry |
| `--lat`, `--lon` | `NODE_LAT`, `NODE_LON` | `51.1739`, `-1.8224` |
| `--drone-lat`, `--drone-lon` | `DRONE_LAT`, `DRONE_LON` | `51.1760`, `-1.8180` (centre of the drone's circle) |
| `--status-interval`, `--detection-interval` | `STATUS_INTERVAL`, `DETECTION_INTERVAL` | 5 s, 1 s |
| `--port` | `APEX_PORT` | 5020 |

| `fake_fusion_node.py` option | Variable | Default |
|---|---|---|
| `--auto-task` | `AUTO_TASK` | `look_at,move_to,follow,patrol,request:Status` |
| `--task-interval` | `TASK_INTERVAL` | 20 s |
| `--no-publish-tracks` | `PUBLISH_TRACKS=0` | tracks are published |
| `--port` | `APEX_PORT` | 5001 |
| `--node-hold-seconds` | `NODE_HOLD_SECONDS` | 120 s, how long a node's liveliness token may be gone before it is forgotten (`--transport zenoh` only) |

To add a node, copy a service block in `docker-compose.emulators.yml` and give it a new `NODE_ID`.
To run a node on the Mac instead, use the venv from step 4:

```bash
PYTHONPATH=${APEX_DIR:-../Apex-SAPIENT-Middleware}:emulators .venv/bin/python emulators/fake_sensor.py \
    --node-type PASSIVE_RF --name "Fake RF" --short-name rf
```

Mac clocks can differ from the VM by more than Apex's 0.1 s limit (see Troubleshooting), so the containers are the safer choice.

### Swapping in a real fusion node

The `fusion-node` service shows what a Stone Soup fusion node has to do on the wire: connect to the Peer port, acknowledge registrations and alerts, read detections, publish tracks, and send tasks.
To test a real one, stop the fake (`docker compose … stop fusion-node`) and point the real one at `localhost:5001`.
The fake sensors keep running. When the new fusion node connects, Apex replays each node's registration and latest status to it, so it can acknowledge them and start tasking.

### Limits of the emulators

- The fusion node's "fusion" only joins detections within 100 m of each other. It's there to exercise the messages, not to track well.
- The camera doesn't move with the vehicle that carries it. `dependent_nodes` is only declared.
- `follow` steers the vehicle to the drone's true position, worked out from the shared clock, not from detections.
- Hierarchy (a child fusion node registering upward as `FUSION_NODE`) isn't emulated on the Apex and TCP rig. Stage 4 publishes that registration on the pod's `fusion/up` keys, but nothing consumes it yet.
- Apex logs `ERROR … translate_v2_to_v1 failed` for the vehicle's registration and for `move_to`, `follow` and `patrol` tasks.
  Apex converts every message to v1.0 to fill the `xml` column of its archive (`sapient_apex_server/parse_proto.py` in the Apex repo), and v2.0-only content can't convert.
  The messages themselves are forwarded unchanged; only the archive's XML copy is missing.

## Stage 1: Option A bridge

This stage carries the fake TCP sensors over Eclipse Zenoh without changing them.
Each sensor connects to `bridge-node` instead of Apex. `bridge-node` publishes its traffic to the `zenohd` router, and `bridge-apex` opens one Child socket per node to Apex's port 5020.
The fusion node stays on Apex's Peer port 5001 over TCP.

The router alone needs only `docker-compose.yml` and `docker-compose.zenoh.yml`. The sensors reach Apex over Zenoh with `docker-compose.zenoh-sensors.yml` added, which is what the commands below use.

The steps below form one sequence, with the default `HOLD_SECONDS` of 120. Run them in order, from the repo root, on a rig that is down. `counts` prints totals since bring-up. The comments show what one run of exactly these commands printed on 2026-11-09 UTC, at commit `1aa4ba8`.

```bash
dc() { docker compose -f docker-compose.yml -f docker-compose.emulators.yml -f docker-compose.zenoh.yml -f docker-compose.zenoh-sensors.yml "$@"; }
counts() { echo "closes=$(dc logs bridge-apex | grep -c 'closing Apex socket') registrations=$(dc logs fusion-node | grep -c '<- registration ') requests=$(dc logs bridge-apex | grep -c 'requested registration')"; }
connections() { dc exec -T apex python -c "import sqlite3,glob;p=sorted(glob.glob('/apex/data/*.sqlite'))[-1];c=sqlite3.connect(f'file:{p}?mode=ro',uri=True);print('rows',c.execute('select count(*) from Connection').fetchone()[0],'open',c.execute('select count(*) from Connection where disconnect_time is null').fetchone()[0])"; }
```

**1. Start everything.**

```bash
dc up -d --build
sleep 60
```

**2. T-01, round trip.**

```bash
dc logs fusion-node | grep -c "<- registration "
# 3
dc logs radar | grep -c "registration_ack"
# 1
```

**3. T-02, task path.** The fusion node sends auto-tasks every 20 s, and each acceptance has to come back to it.

```bash
sleep 60
dc logs --since 120s fusion-node | grep -c "<- task_ack"
# 8
```

**4. T-03, node loss.** The Apex socket closes when the hold window ends, 120 s after the sensor goes, so nothing shows at 15 s.

```bash
counts; connections
# closes=0 registrations=3 requests=0
# rows 4 open 4
dc stop radar
sleep 15;  dc logs --since 30s bridge-apex | grep "closing Apex socket"
# no output
sleep 115; dc logs --since 150s bridge-apex | grep "closing Apex socket"
# bridge-apex-1  | 06:45:54 bridge-apex-side: closing Apex socket for a0000001-0000-4000-8000-000000000001
counts; connections
# closes=1 registrations=3 requests=0
# rows 4 open 3
dc start radar
sleep 30
counts; connections
# closes=1 registrations=4 requests=0
# rows 5 open 4
```

**5. T-04, short outage.** A router pause of 20 s leaves every socket open.

```bash
counts
# closes=1 registrations=4 requests=0
dc pause zenohd; sleep 20; dc unpause zenohd; sleep 30
counts
# closes=1 registrations=4 requests=0
dc logs --since 55s bridge-apex
# bridge-apex-1  | 06:46:51 bridge-apex-side: Zenoh transport lost; holding every Apex socket
# bridge-apex-1  | 06:47:02 bridge-apex-side: Zenoh transport back; checking node tokens
dc logs --since 55s bridge-node
# bridge-node-1  | 06:46:50 bridge-node-side: Zenoh transport lost; keeping every sensor connected
# bridge-node-1  | 06:47:04 bridge-node-side: Zenoh transport back; tokens and subscriptions restored by the session
```

The bridges lose the router about 10 s into the pause, when its lease ends. The Zenoh session reconnects by itself when the router returns and restores its tokens and subscriptions, so the sensors never notice. Messages sent during the outage are lost. A reconnect can show an extra lost and back pair within the same second.

**6. T-05, long outage.** A pause of 150 s outlasts the 120 s hold.

```bash
dc pause zenohd; sleep 150; dc unpause zenohd; sleep 40
counts
# closes=4 registrations=7 requests=3
dc logs --since 185s bridge-apex | grep -c "closing Apex socket"
# 3
dc logs --since 185s fusion-node | grep -c "<- registration "
# 3
dc logs --since 185s bridge-apex | grep -v dropping
# bridge-apex-1  | 06:47:42 bridge-apex-side: Zenoh transport lost; holding every Apex socket
# bridge-apex-1  | 06:49:42 bridge-apex-side: closing Apex socket for a0000003-0000-4000-8000-000000000003
# bridge-apex-1  | 06:49:42 bridge-apex-side: closing Apex socket for a0000002-0000-4000-8000-000000000002
# bridge-apex-1  | 06:49:42 bridge-apex-side: closing Apex socket for a0000001-0000-4000-8000-000000000001
# bridge-apex-1  | 06:50:02 bridge-apex-side: Zenoh transport back; checking node tokens
# bridge-apex-1  | 06:50:05 bridge-apex-side: requested registration from a0000002-0000-4000-8000-000000000002
# bridge-apex-1  | 06:50:05 bridge-apex-side: requested registration from a0000003-0000-4000-8000-000000000003
# bridge-apex-1  | 06:50:05 bridge-apex-side: requested registration from a0000001-0000-4000-8000-000000000001
# bridge-apex-1  | 06:50:05 bridge-apex-side: connected to Apex at apex:5020   (three lines, one per sensor)
```

Each Apex socket closes when the hold ends, 120 s after the router was lost. `bridge-apex` asks each sensor to register again 3 s after the router returns. The sensors stay connected to `bridge-node` throughout and are not restarted. The `--since 185s` window starts after the pause began, so it cannot include anything from T-04.

To stop the stage, run `dc down`. Don't add `--remove-orphans` or `-v`: the first would remove a running Elasticsearch container that shares this compose project, and the second would delete the archive.

## Stage 2: native Zenoh sensors

In this stage the fake sensors speak Zenoh themselves, so `bridge-node` isn't used.
`docker-compose.native-sensors.yml` sets `TRANSPORT=zenoh` and `ZENOH_CONNECT=tcp/zenohd:7447` on the radar, camera and vehicle. `bridge-apex` still opens one Child socket per node to Apex's port 5020, and the fusion node stays on Apex's Peer port 5001 over TCP.

Both emulators take `--transport {tcp,zenoh}` (env `TRANSPORT`, default `tcp`) and `--zenoh-connect` (env `ZENOH_CONNECT`, default `tcp/zenohd:7447`).

`docker-compose.zenoh.yml` still defines `bridge-node`, so the start command below uses `--scale bridge-node=0` to leave it out. Don't add `docker-compose.zenoh-sensors.yml` here.

Run these in order, from the repo root, on a rig that is down. This `dc` replaces the stage 1 one. The comments show what one run of these commands printed on 2026-11-09 UTC, at commit `1aa4ba8`.

```bash
dc() { docker compose -f docker-compose.yml -f docker-compose.emulators.yml -f docker-compose.zenoh.yml -f docker-compose.native-sensors.yml "$@"; }
```

**1. Start everything.**

```bash
dc up -d --build --scale bridge-node=0
sleep 60
```

**2. T-01, round trip.**

```bash
dc logs fusion-node | grep -c "<- registration "
# 3
dc logs radar | grep -c "registration_ack"
# 1
```

**3. T-02, task path.** The fusion node sends auto-tasks every 20 s, and each acceptance has to come back to it.

```bash
sleep 60
dc logs --since 120s fusion-node | grep -c "<- task_ack"
# 8
```

A sensor that registers before `bridge-apex` is subscribed loses that first registration. `bridge-apex` sees the sensor's liveliness token and asks it to register again about 3 s later. This run made 3 such requests, and the count was the same 8 as stage 1, which made none: these are the auto-tasks' acknowledgements (2 `look_at`, 1 `move_to`, 1 `follow`, 1 `patrol`, 3 `request:Status`).

To stop the stage, run `dc down`. Don't add `--remove-orphans` or `-v`, for the reasons given in stage 1. If Elasticsearch is running, `dc down` reports that the `apex_default` network is still in use, which is harmless.

## Stage 3: Zenoh-native rig without Apex

In this stage nothing speaks TCP SAPIENT. The radar, camera, vehicle and fusion node all use `TRANSPORT=zenoh` through the `zenohd` router. There is no Apex and there are no bridges.
The fusion node takes over what Apex did: it checks each incoming message with Apex's `Validator`, and answers a bad one with an `Error`. When it starts, it asks every live node to register again.
`recorder` writes every message on Zenoh to one JSON-lines file per UTC day in the `records` volume, at `/data/records/<date>.jsonl`.

`docker-compose.native.yml` is standalone, so don't combine it with the other compose files. It uses the project name `apex-native`, and takes the image `apex-sapient:4.2.0` built by the earlier stages. If that image is missing, run `docker compose -f docker-compose.yml -f docker-compose.emulators.yml build`. The router publishes port 7447, so stop stages 1 and 2 first.

Run these in order, from the repo root, on a rig that is down. The comments show what one run of these commands printed on 2026-11-08 (UTC 2026-11-09).

```bash
dc() { docker compose -f docker-compose.native.yml "$@"; }
```

**1. Start everything.**

```bash
dc up -d
sleep 30
```

**2. Registrations and acknowledgements.**

```bash
dc logs radar | grep -c registration_ack
# 1
dc logs fusion-node | grep -c "<- registration "
# 3
```

**3. Late joiner.** The restart takes about 10 s, because Python as PID 1 ignores `SIGTERM` until Docker kills it. The new fusion node finds the sensors from their liveliness tokens and requests a registration from each one. The sensors stay connected throughout.

```bash
dc restart fusion-node
sleep 20
dc logs --since 30s fusion-node | grep -c "<- registration "
# 3
dc logs --since 30s radar camera vehicle | grep 'request "Registration"'
# vehicle-1  | 04:52:47 vehicle: <- task f0000001 -> a0000003 9VYE7F request "Registration"
# radar-1    | 04:52:47 radar: <- task f0000001 -> a0000001 PWFZZ4 request "Registration"
# camera-1   | 04:52:47 camera: <- task f0000001 -> a0000002 RVDJ7P request "Registration"
dc logs radar camera vehicle | grep -c "lost; reconnecting"
# 0
```

**4. Recorder.** Run the first command, then the second to see the count grow. The volume survives `dc down`, so the count includes any earlier run on the same UTC day, as it did here.

```bash
dc exec recorder sh -c 'wc -l /data/records/*.jsonl && head -c 300 /data/records/*.jsonl'
# 765 /data/records/2026-11-09.jsonl
# {"t": "2026-11-09T04:49:44.865+00:00", "key": "sapient/v2/a0000002-0000-4000-8000-000000000002/up/registration", "kind": "registration", "node_id": "a0000002-0000-4000-8000-000000000002", "msg": {"timestamp": "2026-11-09T04:49:44.864976Z", "node_id": "a0000002-0000-4000-8000-000000000002", "registra
sleep 10
dc exec recorder sh -c 'wc -l /data/records/*.jsonl'
# 802 /data/records/2026-11-09.jsonl
```

**5. Validation.** This publishes a `StatusReport` with no `node_id` on the radar's up key, then listens on the radar's `error` key for 5 s. The fusion node takes the recipient from the key, because the message doesn't name a sender.

```bash
dc run --rm --no-deps -T radar python -c '
import asyncio, time
from sapient_link import load_template, new_ulid
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import ZenohSession
from zenoh_keys import up_key, down_key
NODE = "a0000001-0000-4000-8000-000000000001"
async def main():
    session = await ZenohSession.open("tcp/zenohd:7447", asyncio.get_running_loop())
    errors = session.subscribe(down_key(NODE, "error"))
    await asyncio.sleep(1)
    msg = load_template("sensor", "StatusReport")
    msg.status_report.report_id = new_ulid()
    msg.timestamp.GetCurrentTime()
    msg.ClearField("node_id")
    await session.publish(up_key(NODE, "status_report"), msg)
    count, deadline = 0, time.monotonic() + 5
    while (left := deadline - time.monotonic()) > 0:
        try:
            key, payload = await asyncio.wait_for(errors.get(), left)
        except asyncio.TimeoutError:
            break
        count += 1
        print(key, list(SapientMessage.FromString(payload).error.error_message))
    print("errors received:", count)
    session.close()
asyncio.run(main())
'
# sapient/v2/a0000001-0000-4000-8000-000000000001/down/error ['node_id (mandatory fields present): Missing mandatory field: node_id']
# errors received: 1
```

To stop the stage, run `dc down`. The recordings stay in the `apex-native_records` volume. Don't add `-v` unless you mean to delete them.

## Stage 4: pod 1 with mutual TLS and access control

This stage hardens the Zenoh router and gives every node its own identity. `docker-compose.pod1.yml` runs the router from `zenoh/router-pod1.json5`, the fusion node, radar, camera and recorder over mutual TLS, and the vehicle as a legacy TCP node behind `bridge-node`, which holds the certificate on its behalf. Keys are prefixed `h1/p1/`.

The router denies by default and binds each certificate to its own keys. A sensor can publish only on its own up keys and liveliness token, and can subscribe only to its own down keys. Only the fusion node can publish on down keys. Only the fusion node and the recorder can read everything. Each container mounts `ca.pem` and its own certificate and key, and `ca.key` is mounted nowhere. The node IDs in the router rules must match the `NODE_ID` values in the compose file.

The compose file is standalone, so don't combine it with the other compose files. It uses the project name `apex-pod1` and takes the image `apex-sapient:4.2.0` built by the earlier stages. The router's port isn't published to the host.

Run these in order, from the repo root, on a rig that is down. The comments show what one run of these commands printed on 2026-11-09 UTC, at commit `1aa4ba8`. `dc run` also prints container creation lines, which are left out here.

```bash
dc() { docker compose -f docker-compose.pod1.yml "$@"; }
```

**1. Certificates and start.** The output directory is git-ignored, and the script keeps certificates that are still valid.

```bash
zenoh/pki/make_certs.sh zenoh/pki/out
# certificates in zenoh/pki/out
dc up -d
sleep 3
dc logs zenohd | grep -ci error
# 0
```

**2. Registrations and acknowledgements**, including the vehicle through the bridge.

```bash
sleep 27
dc logs radar | grep -c registration_ack
# 1
dc logs fusion-node | grep -c "<- registration "
# 3
dc logs vehicle | grep registration_ack | head -1
# vehicle-1  | 06:53:55 vehicle: <- registration_ack f0000001 -> a0000003 acceptance=True ['Accepted by fake fusion node']
dc logs bridge-node | grep registered
# bridge-node-1  | 06:53:55 bridge-node-side: node a0000003-0000-4000-8000-000000000003 registered
```

**3. Late joiner.** The restarted fusion node finds the sensors from their liveliness tokens, and the request reaches the vehicle through the bridge.

```bash
dc restart fusion-node
sleep 20
dc logs --since 30s fusion-node | grep -c "<- registration "
# 3
dc logs --since 30s radar camera vehicle | grep 'request "Registration"'
# camera-1   | 06:54:39 camera: <- task f0000001 -> a0000002 QC41ZM request "Registration"
# vehicle-1  | 06:54:39 vehicle: <- task f0000001 -> a0000003 4KR6PH request "Registration"
# radar-1    | 06:54:39 radar: <- task f0000001 -> a0000001 6FDBM6 request "Registration"
dc logs radar camera vehicle | grep -c "lost; reconnecting"
# 0
```

**4. Recorder.** The volume survives `dc down`, so the count includes any earlier run on the same UTC day, as it did here.

```bash
dc exec -T recorder sh -c 'wc -l /data/records/*.jsonl'
# 127657 /data/records/2026-11-09.jsonl
sleep 10
dc exec -T recorder sh -c 'wc -l /data/records/*.jsonl'
# 127694 /data/records/2026-11-09.jsonl
dc exec -T recorder sh -c 'head -c 120 /data/records/*.jsonl'; echo
# {"t": "2026-11-09T05:11:40.211+00:00", "key": "h1/p1/sapient/v2/f0000001-0000-4000-8000-000000000001/up/registration", "
```

**5. Validation.** As in stage 3, with the radar's certificate on its own keys.

```bash
dc run --rm --no-deps -T radar python -c '
import asyncio, logging, os, time
from sapient_link import load_template, new_ulid
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import open_session
from zenoh_keys import up_key, down_key
NODE = "a0000001-0000-4000-8000-000000000001"
async def main():
    session = await open_session(os.environ["ZENOH_CONNECT"], asyncio.get_running_loop(), logging.getLogger("probe"))
    errors = session.subscribe(down_key(NODE, "error"))
    await asyncio.sleep(1)
    msg = load_template("sensor", "StatusReport")
    msg.status_report.report_id = new_ulid()
    msg.timestamp.GetCurrentTime()
    msg.ClearField("node_id")
    await session.publish(up_key(NODE, "status_report"), msg)
    count, deadline = 0, time.monotonic() + 5
    while (left := deadline - time.monotonic()) > 0:
        try:
            key, payload = await asyncio.wait_for(errors.get(), left)
        except asyncio.TimeoutError:
            break
        count += 1
        print(key, list(SapientMessage.FromString(payload).error.error_message))
    print("errors received:", count)
    session.close()
asyncio.run(main())
'
# h1/p1/sapient/v2/a0000001-0000-4000-8000-000000000001/down/error ['node_id (mandatory fields present): Missing mandatory field: node_id']
# errors received: 1
```

**6. T-07: access control.** A denied publication looks like a success to the publisher, so the proof is what the other side saw and what the router logged. The router names denials only at trace level, so this step restarts it with that filter, and the last command returns it to `info`.

```bash
ZENOHD_RUST_LOG=zenoh=debug,zenoh::net::routing::interceptor=trace dc up -d zenohd
sleep 25
PROBE='
import asyncio, logging, os, sys
from sapient_link import load_template, new_ulid, stamp
from zenoh_io import open_session
from zenoh_keys import down_key, up_key
CAMERA = "a0000002-0000-4000-8000-000000000002"
sender, kind = sys.argv[1], sys.argv[2]
async def main():
    session = await open_session(os.environ["ZENOH_CONNECT"], asyncio.get_running_loop(), logging.getLogger("probe"))
    await asyncio.sleep(1)
    if kind == "task":  # a Task from sender to the camera, on the camera key
        msg = stamp(load_template("fusion_node", "Task.Request.Status"), sender, CAMERA)
        msg.task.task_id = new_ulid()
        await session.publish(down_key(CAMERA, "task"), msg)
        print("published task", msg.task.task_id[-6:])
    elif kind == "listen":  # count what this certificate can hear on the camera down key
        heard = session.subscribe(down_key(CAMERA, "task"))
        await asyncio.sleep(8)
        print("heard on the camera down key:", heard.qsize())
    elif kind == "forge":  # a StatusReport naming the camera, on the up key of sender
        msg = stamp(load_template("sensor", "StatusReport"), CAMERA)
        msg.status_report.report_id = new_ulid()
        msg.status_report.info = msg.status_report.INFO_NEW
        msg.status_report.mode = "T07-FORGED"
        await session.publish(up_key(sender, "status_report"), msg)
        print("published status naming", CAMERA[:8], "on the up key of", sender[:8])
    elif kind == "unchanged":  # registers as sender, then reports Unchanged with no New
        msg = stamp(load_template("sensor", "Registration"), sender)
        await session.publish(up_key(sender, "registration"), msg)
        await asyncio.sleep(0.5)
        msg = stamp(load_template("sensor", "StatusReport"), sender)
        msg.status_report.report_id = new_ulid()
        msg.status_report.info = msg.status_report.INFO_UNCHANGED
        await session.publish(up_key(sender, "status_report"), msg)
        print("registered and reported Unchanged as", sender[:8])
    else:  # a StatusReport from sender, on the up key of sender
        msg = stamp(load_template("sensor", "StatusReport"), sender)
        msg.status_report.report_id = new_ulid()
        msg.status_report.info = msg.status_report.INFO_NEW
        msg.status_report.mode = "T07-PROBE"
        await session.publish(up_key(sender, "status_report"), msg)
        print("published status as", sender[:8])
    await asyncio.sleep(1)
    session.close()
asyncio.run(main())
'
RADAR=a0000001-0000-4000-8000-000000000001
CAMERA=a0000002-0000-4000-8000-000000000002
FUSION=f0000001-0000-4000-8000-000000000001
```

The radar's certificate tries to task the camera. The camera must not log it.

```bash
dc run --rm --no-deps -T radar python -c "$PROBE" $RADAR task
# published task JVW8CZ
sleep 10
dc logs --since 20s camera | grep -c "<- task a0000001"
# 0
```

The radar's certificate tries to report as the camera, on the camera's up key. Neither the fusion node nor the recorder may see it.

```bash
dc run --rm --no-deps -T radar python -c "$PROBE" $CAMERA status
# published status as a0000002
sleep 3
dc logs --since 15s fusion-node | grep -c "a0000002.*T07-PROBE"
# 0
dc exec -T recorder sh -c 'cat /data/records/*.jsonl | grep -c "a0000002.*T07-PROBE"'
# 0
```

The radar's certificate may publish on its own up key, so the router lets this one through. The fusion node compares the message's `node_id` with the owner of the key, drops the forgery, and tells the radar.

```bash
dc run --rm --no-deps -T radar python -c "$PROBE" $RADAR forge
# published status naming a0000002 on the up key of a0000001
sleep 3
dc logs --since 15s fusion-node | grep -c "a0000002.*T07-FORGED"
# 0
dc logs --since 15s fusion-node | grep "does not match"
# fusion-node-1  | 06:56:07 fusion: invalid message from 'a0000002' dropped: node_id a0000002-0000-4000-8000-000000000002 does not match the owner of its key, a0000001-0000-4000-8000-000000000001
# fusion-node-1  | 06:56:07 fusion: -> error f0000001 -> a0000001 node_id a0000002-0000-4000-8000-000000000002 does not match the owner of its key, a0000001-0000-4000-8000-000000000001
dc logs --since 15s radar | grep -c "<- error"
# 1
```

Two controls show the same probes do arrive when the certificate is allowed. The radar reports as itself, and the fusion certificate tasks the camera while the radar's certificate tries to listen on the camera's down key.

```bash
dc run --rm --no-deps -T radar python -c "$PROBE" $RADAR status
# published status as a0000001
sleep 3
dc logs --since 15s fusion-node | grep "a0000001.*T07-PROBE"
# fusion-node-1  | 06:56:13 fusion: <- status_report a0000001 SYSTEM_OK INFO_NEW mode=T07-PROBE
dc run --rm --no-deps -T radar python -c "$PROBE" $RADAR listen &
sleep 3
TASK=$(dc run --rm --no-deps -T fusion-node python -c "$PROBE" $FUSION task | awk '{print $3}')
wait
# heard on the camera down key: 0
dc logs --since 20s camera | grep -c "$TASK"   # the task and the camera's ack
# 2
```

The router's own record of the denials, by certificate:

```bash
dc logs --no-color zenohd | grep 'CertCommonName(radar.p1.h1)' | grep a0000002 | grep -E 'unauthorized to (Put|Declare/Undeclare Subscriber) ' | sed -E 's/.*CertCommonName\(([^)]*)\).* is (unauthorized.*)/\1 \2/' | sort -u
# radar.p1.h1 unauthorized to Declare/Undeclare Subscriber (ingress) on h1/p1/sapient/v2/a0000002-0000-4000-8000-000000000002/down/task
# radar.p1.h1 unauthorized to Put (ingress) on h1/p1/sapient/v2/a0000002-0000-4000-8000-000000000002/down/task
# radar.p1.h1 unauthorized to Put (ingress) on h1/p1/sapient/v2/a0000002-0000-4000-8000-000000000002/up/status_report
dc up -d zenohd
sleep 25
```

**7. T-08: status ordering under load.** The radar and camera report detections every 100 ms (10 Hz each) for about 2 minutes. The fusion node logs `Unchanged status ... before any New status` when a node reports `INFO_UNCHANGED` after registering and before any `INFO_NEW`. The window covers the sensors' start, which is when that order can go wrong.

```bash
DETECTION_INTERVAL=0.1 dc up -d radar camera
sleep 115
dc logs --since 2m fusion-node | grep -c "Unchanged.*before"
# 0
dc logs --since 2m fusion-node | grep -c "invalid message from"
# 0
dc logs --since 2m fusion-node | grep -c "<- detection_report"   # the fusion node logs every 10th per sensor
# 216
```

The check passes with 0 `Unchanged` lines and accepted detections in the log. An interval of 0.02 s can't be run here, because the fusion node's validator requires 80 ms between detections from one sensor and rejects every one sent faster.

This confirms the check can fire. A probe registers as the radar and then reports `INFO_UNCHANGED` with no `INFO_NEW`. The second log line is the real radar's next status, which also arrives before a New.

```bash
dc run --rm --no-deps -T radar python -c "$PROBE" $RADAR unchanged
# registered and reported Unchanged as a0000001
sleep 3
dc logs --since 15s fusion-node | grep "Unchanged.*before"
# fusion-node-1  | 06:59:17 fusion: Unchanged status from a0000001 before any New status since it registered
# fusion-node-1  | 06:59:20 fusion: Unchanged status from a0000001 before any New status since it registered
```

Return the sensors to their normal rate.

```bash
dc up -d radar camera
```

**8. T-11 (partial): the pod registers upward.** Zenoh keeps no history, so a subscriber that joins a settled rig would never see the registration. This stops the fusion node, starts a subscriber on the pod's upward keys with the recorder's certificate, and starts the fusion node again 4 s later. There is no host fusion node in this rig, so this shows only what the pod publishes.

```bash
docker compose -f docker-compose.pod1.yml stop fusion-node
( sleep 4; docker compose -f docker-compose.pod1.yml start fusion-node ) &
PKI=$PWD/zenoh/pki/out
docker run --rm -i --network apex-pod1_default --entrypoint python -w /emulators \
  -v "$PWD/emulators:/emulators:ro" \
  -v "$PKI/ca.pem:/certs/ca.pem:ro" \
  -v "$PKI/recorder.p1.h1.pem:/certs/recorder.p1.h1.pem:ro" \
  -v "$PKI/recorder.p1.h1.key:/certs/recorder.p1.h1.key:ro" \
  -e ZENOH_KEY_PREFIX=h1/p1/ -e ZENOH_TLS_CA=/certs/ca.pem \
  -e ZENOH_TLS_CERT=/certs/recorder.p1.h1.pem -e ZENOH_TLS_KEY=/certs/recorder.p1.h1.key \
  -e PYTHONDONTWRITEBYTECODE=1 \
  apex-sapient:4.2.0 - <<'EOF'
import asyncio, collections, time
from datetime import datetime, timezone
from fake_fusion_node import VALIDATION_OPTIONS
from sapient_apex_server.validate_proto import Validator
from sapient_msg.bsi_flex_335_v2_0.registration_pb2 import Registration
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import ZenohSession, tls_from_env

FUSION = "f0000001-0000-4000-8000-000000000001"

async def main():
    session = await ZenohSession.open("tls/router.p1.h1:7447", asyncio.get_running_loop(), tls_from_env())
    samples = session.subscribe("h1/p1/fusion/up/**")
    print(f"subscribed h1/p1/fusion/up/** at {datetime.now(timezone.utc):%H:%M:%S}", flush=True)
    start, counts, senders, order = time.monotonic(), collections.Counter(), collections.Counter(), []
    while (left := 30 - (time.monotonic() - start)) > 0:
        try:
            key, payload = await asyncio.wait_for(samples.get(), left)
        except asyncio.TimeoutError:
            break
        msg = SapientMessage.FromString(payload)
        kind = msg.WhichOneof("content")
        counts[key] += 1
        senders[(kind, msg.node_id)] += 1
        order.append(kind)
        at = time.monotonic() - start
        if kind == "registration":
            reg = msg.registration
            errors = []
            Validator(VALIDATION_OPTIONS).validate_sapient_message(msg, datetime.now(timezone.utc).replace(tzinfo=None), errors)
            print(f"+{at:5.1f}s {key} node_id={msg.node_id}", flush=True)
            print(f"  node_type={[Registration.NodeType.Name(d.node_type) for d in reg.node_definition]}"
                  f" capabilities={[(c.category, c.type[:24]) for c in reg.capabilities]}"
                  f" commands={[Registration.CommandType.Name(c.type) for c in reg.mode_definition[0].task.command]}"
                  f" status_interval={reg.status_definition.status_interval.value}"
                  f" {Registration.TimeUnits.Name(reg.status_definition.status_interval.units)}"
                  f" validator_errors={[e.full_str() for e in errors]}", flush=True)
        elif counts[key] <= 3:
            print(f"+{at:5.1f}s {key} node_id={msg.node_id} object={msg.detection_report.object_id[-6:]}", flush=True)
    print("counts by key:", dict(counts))
    print("(kind, node_id):", {f"{k}/{n}": v for (k, n), v in senders.items()})
    print("every sender is the fusion node:", all(n == FUSION for (_, n) in senders))
    print("first message is the registration:", order[:1] == ["registration"])
    session.close()

asyncio.run(main())
EOF
# subscribed h1/p1/fusion/up/** at 06:59:42
# + 12.1s h1/p1/fusion/up/registration node_id=f0000001-0000-4000-8000-000000000001
#   node_type=['NODE_TYPE_FUSION_NODE'] capabilities=[('EMS', 'Chaff, noise jamming, fa')] commands=['COMMAND_TYPE_PATROL'] status_interval=10.0 TIME_UNITS_SECONDS validator_errors=[]
# + 12.9s h1/p1/fusion/up/detection_report node_id=f0000001-0000-4000-8000-000000000001 object=CFQ5J0
# + 13.9s h1/p1/fusion/up/detection_report node_id=f0000001-0000-4000-8000-000000000001 object=CFQ5J0
# + 14.9s h1/p1/fusion/up/detection_report node_id=f0000001-0000-4000-8000-000000000001 object=CFQ5J0
# counts by key: {'h1/p1/fusion/up/registration': 1, 'h1/p1/fusion/up/detection_report': 17}
# (kind, node_id): {'registration/f0000001-0000-4000-8000-000000000001': 1, 'detection_report/f0000001-0000-4000-8000-000000000001': 17}
# every sender is the fusion node: True
# first message is the registration: True
```

**9. A departed node is forgotten.** The radar's token goes when it stops. After the 120 s hold the fusion node removes it and, 5 s later, announces the registration again. The log shows only that it did; a unit test pins that the radar's capabilities are gone from it. Restarting the radar brings it back.

```bash
dc stop radar
sleep 15
dc logs --since 30s fusion-node | grep -c "removed"
# 0
sleep 115
dc logs --since 135s fusion-node | grep -E "removed|-> registration f0000001"
# fusion-node-1  | 07:02:22 fusion: node a0000001 gone for 120 s; removed
# fusion-node-1  | 07:02:27 fusion: -> registration f0000001 "fake fusion node" [FUSION_NODE]
dc start radar
sleep 15
dc logs --since 20s fusion-node | grep -c "<- registration a0000001"
# 1
```

To stop the stage, run `dc down`. The recordings stay in the `apex-pod1_records` volume. Don't add `-v` unless you mean to delete them.

## Goat step 1: pod 1 to host

This step carries pod 1's SAPIENT traffic to a host over a fabric that follows the goat network's rules. `docker-compose.goat1.yml` runs two routers and the nodes around them:

- **Pod 1** (network `pod1`): the pod router `zenohd-pod` (`eclipse/zenoh:1.10.2`, `zenoh/goat1/router-pod1.json5`), the fusion node, radar, camera, the vehicle behind `bridge-node`, and the pod recorder. Pod keys are prefixed `h1/p1/`. Each sensor holds a slot certificate whose common name is its node ID.
- **The pod bridge** (networks `pod1` and `mesh`): `pod_bridge.py` holds the pod's bridge certificate on the pod router and the pod's slot certificate on the fabric router, and forwards the bytes unchanged in both directions. Only the fusion node's traffic goes up.
- **The host** (network `host`): the fabric router `zenohd-fabric` (`${FABRIC_ZENOH_IMAGE:-eclipse/zenoh:1.9.0}`, `zenoh/goat1/router-fabric.json5`), a fusion node with `TRANSPORT=fabric`, and a recorder with `RECORD_KEYS=fabric`. Fabric keys start with the writer's 32-character anchor, and the fabric router lets each certificate write only below its own anchor.

`radar2` sits behind the compose profile `join`: the rig starts without `radar2` unless the profile `join` is named, as step 9 does. The generator writes the router configurations, the certificates and `zenoh/goat1/goat1.env` below `zenoh/goat1/`, which is git-ignored. The compose file is standalone: don't combine it with the other compose files. It uses the project name `apex-goat1` and the image `apex-sapient:4.2.0` built by the earlier stages. No router port is published to the host.

Run these in order, from the repo root, on a rig that is down. Below each block is what one run printed on 2026-11-11 UTC, on top of commit `08ef7c2`. `dg run` also prints container lines, and the probe prints a `connected to Zenoh router` line; both are left out here.

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
fusion-node-1  | 23:47:51 fusion: -> registration_ack f0000001 -> 341b9172 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:47:53 fusion: -> registration_ack f0000001 -> 1aef1b86 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:47:53 fusion: -> registration_ack f0000001 -> 86ca6000 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:47:56 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
host-fusion-1  | 23:47:56 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
```

**3. Tracks and alerts up (G1-02).** The host gets the pod's fused tracks and one alert for each new track. The host recorder holds only messages below the pod's anchor or the host fusion node's anchor, and none of them carries a sensor's node ID.

```bash
dg logs host-fusion | grep -c "<- detection_report"
dg logs host-fusion | grep "<- alert"
dg exec -T host-recorder sh -c 'cat /data/records/*.jsonl' < /dev/null | python3 -c '
import json, sys
anchors, sensors = set(sys.argv[1:3]), set(sys.argv[3:6])
rows = [json.loads(line) for line in sys.stdin if line.strip()]
print("records:", len(rows))
print("anchor not the pod or the host fusion node:", sum(r.get("anchor") not in anchors for r in rows))
print("msg.node_id of the radar, camera or vehicle:", sum(r.get("msg", {}).get("node_id") in sensors for r in rows))
' "$FABRIC_POD1_ID" "$FABRIC_HOST_FUSION_ID" "$POD1_RADAR_ID" "$POD1_CAMERA_ID" "$POD1_VEHICLE_ID"
```

```text
4
host-fusion-1  | 23:47:56 fusion: <- alert f0000001 ALERT_TYPE_INFORMATION "new track 6TR3WR"
records: 93
anchor not the pod or the host fusion node: 0
msg.node_id of the radar, camera or vehicle: 0
```

The detection count is low because the fusion node logs every 10th detection report of each node. The recorder's volume survives `dg down`, so the record count includes any earlier run on the same UTC day.

**4. A task down (G1-04).** The host's fusion node sends `request:Status` and `look_at` in turn, every 20 s. The pod's fusion node passes `look_at` to its registered sensors as a copy with a new task ID, and acknowledges upward.

```bash
dg logs radar camera | grep "<- task .* look_at" | cut -c1-90
dg logs host-fusion | grep "<- task_ack" | grep TASK_STATUS_ACCEPTED
```

```text
radar-1   | 23:48:31 radar: <- task f0000001 -> 1aef1b86 AG2327 look_at {"location_list":
camera-1  | 23:48:31 camera: <- task f0000001 -> 86ca6000 VPS33S look_at {"location_list":
host-fusion-1  | 23:48:11 fusion: <- task_ack f0000001 -> f0000002 9WWS9Q TASK_STATUS_ACCEPTED ['Status report sent']
host-fusion-1  | 23:48:31 fusion: <- task_ack f0000001 -> f0000002 SBNACR TASK_STATUS_ACCEPTED ['look_at sent to 2 nodes']
```

**5. Access on the live routers (G1-05).** Restart both routers with the access-control trace. A denial is silent for the client, so each case shows two things: the subscriber, whose certificate may read the key, got nothing from the probe, and the router logged the denial. On the fabric router each certificate matches two subjects (any mutual-TLS peer, and its own slot). The router tries each subject in turn and logs `unauthorized` for each one that denies, and stops at the first that allows with one `authorized` line (function `action` in `zenoh/src/net/routing/interceptor/access_control.rs`, Zenoh 1.9.0 and 1.10.2). So one denied put logs two `unauthorized` lines and no `authorized` line, while an allowed put can also log an `unauthorized` line before its `authorized` line. The test is therefore: no `authorized` line and 0 probe samples.

```bash
ZENOHD_RUST_LOG=zenoh::net::routing::interceptor=trace dg up -d zenohd-pod zenohd-fabric
sleep 20
dg logs --since 30s pod-bridge
```

```text
pod-bridge-1  | 23:48:46 pod-bridge: fabric router lost
pod-bridge-1  | 23:48:46 pod-bridge: pod router lost
pod-bridge-1  | 23:48:47 pod-bridge: fabric router back
pod-bridge-1  | 23:48:47 pod-bridge: pod router back
pod-bridge-1  | 23:48:51 pod-bridge: forwarded {'up': 64, 'down': 4}; dropped {}
```

Case 1: the pod's slot certificate puts on the host fusion node's task key.

```bash
K="$FABRIC_HOST_FUSION_ID/task/p1/sapient/v2/task/$POD1_FUSION_NODE_ID"
probe host-recorder sub "$K" 15 &
sleep 5
podfabric put "$K"
wait
dg logs zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_POD1_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_POD1_ID)" | grep -c "is authorized to Put (ingress)"
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
probe host-recorder sub "$K" 15 &
sleep 5
probe host-fusion put "$K"
wait
dg logs zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_HOST_FUSION_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_HOST_FUSION_ID)" | grep -c "is authorized to Put (ingress)"
```

```text
samples: 0 on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
2
0
```

Case 3: the host recorder's certificate may not subscribe to everything, only to the fabric's telemetry.

```bash
probe host-recorder sub "**" 15
probe host-recorder sub "*/telemetry/sapient/*/v2/*/*" 15
dg logs zenohd-fabric | grep -F "CertCommonName($FABRIC_HOST_RECORDER_ID)" | grep -F "Declare Subscriber (ingress) on **" | grep -c unauthorized
```

```text
samples: 0 on ** in 15 s; from this probe: 0
samples: 31 on */telemetry/sapient/*/v2/*/* in 15 s; from this probe: 0
2
```

Case 4: in the pod, the radar's certificate puts on the camera's up key.

```bash
K="h1/p1/sapient/v2/$POD1_CAMERA_ID/up/status_report"
probe recorder sub "$K" 15 &
sleep 5
probe radar put "$K"
wait
dg logs zenohd-pod | grep -F "$K" | grep -F "CertCommonName($POD1_RADAR_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs zenohd-pod | grep -F "$K" | grep -F "CertCommonName($POD1_RADAR_ID)" | grep -c "is authorized to Put (ingress)"
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
fusion-node-1  | 23:50:45 fusion: <- task f0000002 -> f0000001 K2JYBJ request "Registration"
fusion-node-1  | 23:50:45 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
```

Steps 7 to 9 were added later. What is printed below them comes from one run on 2026-11-12 UTC, on top of commit `8db9951`, that pasted steps 1 to 9 in order into one zsh.

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
pod-bridge-1  | 00:22:48 pod-bridge: forwarded {'up': 242, 'down': 13}; dropped {}
pod-bridge-1  | 00:23:02 pod-bridge: fabric router lost
pod-bridge-1  | 00:23:18 pod-bridge: forwarded {'up': 258, 'down': 14}; dropped {'other_side_down': 18}
pod-bridge-1  | 00:23:25 pod-bridge: fabric router back
pod-bridge-1  | 00:23:48 pod-bridge: forwarded {'up': 283, 'down': 15}; dropped {'other_side_down': 26}
```

The bridge notices the loss only when its session to the fabric router times out: in two timed runs it logged `fabric router lost` 9 to 10 s after the disconnect, and `fabric router back` 0 to 2 s after the connect. What it publishes before it notices counts as forwarded; these steps don't show whether it arrived.

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
host-fusion-1  | 00:24:29 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
host-fusion-1  | 00:25:54 fusion: node f0000001 gone for 20 s; removed
host-fusion-1  | 00:26:09 fusion: -> task f0000002 -> f0000001 FWNQRB request "Registration"
host-fusion-1  | 00:26:09 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
fusion-node-1  | 00:24:29 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 00:26:09 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
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
fusion-node-1  | 00:26:45 fusion: -> registration_ack f0000001 -> 83ff6077 acceptance=True ['Accepted by fake fusion node']
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

**10. A real goat client reads the pod's tracks (G1-10).** This is the one check with goat's own software. Build goat's command line tool `goat` from the goat source in `../usareur-af/goatcore`, at commit `cbf2cb7f` (`goat-cli` 0.5.19), give it the certificate of fabric slot 3 (`FABRIC_GOAT_CLI_ID`), and let `goat sub` read below the pod's anchor from the fabric router. Step 10 was added after step 9; what is printed below it comes from one run on 2026-11-12 UTC, on top of commit `4df6e2f`, with the rig of step 1 up and the build already cached.

The build runs in `rust:1.95.0-bookworm`, with the goat source mounted read-only, and needs the network for the image and for the crates. The first build took 265 s (4 min 25 s) on a Colima VM with 4 CPUs and 6 GiB; a later build takes seconds. The build output and the downloaded crates stay in the Docker volume `apex-goat1-cargo-target`; remove it with `docker volume rm apex-goat1-cargo-target`. The binary goes to `zenoh/goat1/bin/goat` (git-ignored) and runs in `debian:bookworm-slim`.

```bash
docker run --rm -v "$PWD/../usareur-af/goatcore:/src:ro" -v apex-goat1-cargo-target:/target -e CARGO_TARGET_DIR=/target -e CARGO_HOME=/target/cargo-home rust:1.95.0-bookworm cargo build --release --locked -j 2 --manifest-path /src/crates/Cargo.toml -p goat-cli < /dev/null
mkdir -p zenoh/goat1/bin
docker run --rm -v apex-goat1-cargo-target:/target:ro -v "$PWD/zenoh/goat1/bin:/out" debian:bookworm-slim cp /target/release/goat /out/goat < /dev/null
docker run --rm -v "$PWD/zenoh/goat1/bin/goat:/usr/local/bin/goat:ro" debian:bookworm-slim goat --version < /dev/null
```

```text
    Finished `release` profile [optimized] target(s) in 0.15s
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
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001 hex:0a0b08b19cd4d706...
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

The block is shortened: it leaves out the compose lines (`Recreate`, `Started` and the like) that the two `dg up` commands print, and the hex payload of the first sample is cut after its first bytes, marked `...`. The payload differs on each run.

Both runs exit 0, and every key starts with the pod's anchor `18214b1a34e3c722d1cac283b272a62c`. The three counts are measured: the router allowed two subscriber declarations, delivered four samples (the four that goat printed), and allowed no put, delete or liveliness token from slot 3. A count made afterwards on the saved router log of this run, not by a command of this step, found no put, delete, query, liveliness token or liveliness query from goat at all. The router's other lines for slot 3 come in one burst for each session, all on one key expression: read from the trace, they are the decisions it works out for all nine actions when it caches a client's key expression (see step 5), not requests from goat. The last command puts the fabric router back to `info`.

To stop the step, run `dg down`. The recordings stay in the `apex-goat1_pod-records` and `apex-goat1_host-records` volumes. Don't add `-v` unless you mean to delete them. `docs/acceptance-goat1.md` records what passed and where each check falls short.

## Optional: Elasticsearch and the REST API

The REST API on port 8080 reads from Elasticsearch. Without it, every data endpoint returns `503 {"detail":"Database Service Unavailable or not started."}`, and only `/` and `/docs` work. Apex doesn't need Elasticsearch to route or record messages, because SQLite always records everything.

`docker-compose.elastic.yml` adds Elasticsearch 8.11.1 (single node, security off) and makes these changes to Apex:

- Apex waits until Elasticsearch is healthy. Apex connects to Elasticsearch once at startup and doesn't retry, so this order matters.
- Apex runs with the mounted config, but with `elasticConfig.enabled` set to `true`. You don't have to edit `apex_config.json`.

1. Give Colima at least 6 GiB of memory (see step 2). Elasticsearch uses about 1 GiB.
2. Add the file after the others:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.emulators.yml -f docker-compose.elastic.yml up -d
   ```

   Leave out `-f docker-compose.emulators.yml` if you don't want the fake nodes. The first start pulls a 700 MB image, then waits about 30 s for Elasticsearch to become healthy.

3. Query the API:

   ```bash
   curl -s http://127.0.0.1:8080/registered
   curl -s http://127.0.0.1:8080/node_definitions
   curl -s 'http://127.0.0.1:8080/detections?node_ids=all&detection_count=2'
   ```

   Open <http://127.0.0.1:8080/docs> for the full list of endpoints.

`/registered` lists the nodes that registered on the Child ports. It returns `400 No Registered Nodes found.` until a node registers. The messages are kept in the `es-data` volume. To go back to running without Elasticsearch, run `up -d` again without the elastic file.

## The SQLite archive

Apex writes `data/data-<UTC time>.sqlite` inside the container, in the named volume `apex_apex-data`. The volume survives `docker compose down` and rebuilds.

To copy the archive files to the Mac:

```bash
docker compose cp apex:/apex/data ./data-export
```

## Stopping

```bash
docker compose -f docker-compose.yml -f docker-compose.emulators.yml down   # if the emulators are running
docker compose down        # stop and remove the container; keep the archive
docker compose down -v     # also delete the archive volume
colima stop                # stop the VM and free its memory
```

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `failed to connect to the docker API at unix:///var/run/docker.sock` | Colima isn't running: `colima start`. Or select its context: `docker context use colima`. |
| `docker: 'compose' is not a docker command` | Docker can't find the plugin. Add `cliPluginsExtraDirs` (step 1). |
| `IsADirectoryError: '/config/apex_config.json'` | Colima shares only your home folder with the VM. A bind-mounted file outside `~` (for example in `/tmp`) appears as an empty folder. Keep this repo and the Apex checkout under your home folder. |
| `Bind for 0.0.0.0:5000 failed` | Something on the Mac uses that port; on macOS it's AirPlay Receiver. Keep the `5050:5000` mapping, or turn off AirPlay Receiver in System Settings → General → AirDrop & Handoff. |
| Reply is an `error` with `Timestamp delta 0:00:00.149068 > 0:00:00.100000` | The sender's clock (the Mac) is ahead of the container's clock (the Colima VM). This happened in testing right after `colima start`. Wait for `NTPSynchronized=yes` (step 2), then send again. For local testing only, you can widen `validationOptions.messageTimestampRange` in `apex_config.json`, for example to `[-0.9, 0.5]`. Real SAPIENT nodes must use NTP. |
| The smoke test hangs, or the connection is refused | Apex isn't ready yet, or it exited. Check `docker compose ps` and `docker compose logs apex`. |

## License

Apache License 2.0; see [LICENSE](LICENSE). [NOTICE](NOTICE) lists the files that come from Apex SAPIENT Middleware and the SAPIENT Test Harness, which are also Apache 2.0. This repo does not include the Apex source. The Docker build reads it from your own checkout.
