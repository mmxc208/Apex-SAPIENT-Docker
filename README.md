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
| `docker-compose.yml` | Runs Apex, maps its ports, keeps the SQLite archive in a volume; optional Elasticsearch |
| `apex_config.json` | Apex config for the container (see "Differences from the repo config") |
| `smoke_test.py` | Sends one v2.0 Registration and prints Apex's reply |
| `docker-compose.emulators.yml` | Adds a fake fusion node, radar, camera and vehicle (see "Fake sensors and fusion node") |
| `apex_config.emulators.json` | Apex config for the emulators: v2.0 Peer port, `sendRegistrationAck: false` |
| `emulators/` | The fake nodes (`fake_sensor.py`, `fake_fusion_node.py`, `sapient_link.py`) and the Test Harness message templates they use |

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

To check the REST API, open <http://127.0.0.1:8080/docs>. To check the archive:

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
| 8080 | 8080 | REST API | HTTP |

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
3. **`elasticConfig` points at the `elasticsearch` container, without SSL.** It stays disabled (`"enabled": false`).

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
- Hierarchy (a child fusion node registering upward as `FUSION_NODE`) isn't emulated.
- Apex logs `ERROR … translate_v2_to_v1 failed` for the vehicle's registration and for `move_to`, `follow` and `patrol` tasks.
  Apex converts every message to v1.0 to fill the `xml` column of its archive (`sapient_apex_server/parse_proto.py` in the Apex repo), and v2.0-only content can't convert.
  The messages themselves are forwarded unchanged; only the archive's XML copy is missing.

## Optional: Elasticsearch

The REST API's data endpoints need Elasticsearch. Apex doesn't need it to route or record messages: SQLite always records everything.

1. Start Colima with at least 6 GiB of memory (see step 2).
2. Set `"enabled": true` under `elasticConfig` in `apex_config.json`.
3. Start both services:

   ```bash
   docker compose --profile elastic up -d
   ```

This setup has not been tested yet. Elasticsearch may need a minute to start, and Apex may log connection errors until it is ready.

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
