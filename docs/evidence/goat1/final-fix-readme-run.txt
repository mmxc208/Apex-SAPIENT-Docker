%   aidev-1% %   aidev-1% %   aidev-1% === start 2026-11-12T02:15:44Z
%   aidev-1% === block helper 02:15:44
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% === block 1 02:15:44
%   aidev-1% %   aidev-1% %   aidev-1%  Network apex-goat1_pod1 Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_host Created 
 Network apex-goat1_host Created 
 Network apex-goat1_pod1 Created 
 Network apex-goat1_pod1 Created 
 Container apex-goat1-zenohd-pod-1 Creating 
 Network apex-goat1_mesh Created 
 Network apex-goat1_mesh Created 
 Container apex-goat1-zenohd-fabric-1 Creating 
 Container apex-goat1-zenohd-pod-1 Created 
 Container apex-goat1-recorder-1 Creating 
 Container apex-goat1-bridge-node-1 Creating 
 Container apex-goat1-fusion-node-1 Creating 
 Container apex-goat1-radar-1 Creating 
 Container apex-goat1-camera-1 Creating 
 Container apex-goat1-zenohd-fabric-1 Created 
 Container apex-goat1-host-recorder-1 Creating 
 Container apex-goat1-host-fusion-1 Creating 
 Container apex-goat1-pod-bridge-1 Creating 
 Container apex-goat1-bridge-node-1 Created 
 Container apex-goat1-vehicle-1 Creating 
 Container apex-goat1-camera-1 Created 
 Container apex-goat1-radar-1 Created 
 Container apex-goat1-pod-bridge-1 Created 
 Container apex-goat1-fusion-node-1 Created 
 Container apex-goat1-recorder-1 Created 
 Container apex-goat1-host-recorder-1 Created 
 Container apex-goat1-host-fusion-1 Created 
 Container apex-goat1-vehicle-1 Created 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
 Container apex-goat1-host-recorder-1 Starting 
 Container apex-goat1-host-fusion-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-bridge-node-1 Starting 
 Container apex-goat1-recorder-1 Starting 
 Container apex-goat1-pod-bridge-1 Starting 
 Container apex-goat1-fusion-node-1 Starting 
 Container apex-goat1-radar-1 Starting 
 Container apex-goat1-camera-1 Starting 
 Container apex-goat1-host-recorder-1 Started 
 Container apex-goat1-host-fusion-1 Started 
 Container apex-goat1-bridge-node-1 Started 
 Container apex-goat1-vehicle-1 Starting 
 Container apex-goat1-recorder-1 Started 
 Container apex-goat1-pod-bridge-1 Started 
 Container apex-goat1-fusion-node-1 Started 
 Container apex-goat1-radar-1 Started 
 Container apex-goat1-camera-1 Started 
 Container apex-goat1-vehicle-1 Started 
%   aidev-1% %   aidev-1% bridge-node running
camera running
fusion-node running
host-fusion running
host-recorder running
pod-bridge running
radar running
recorder running
vehicle running
zenohd-fabric running
zenohd-pod running
%   aidev-1% 0
%   aidev-1% === block 2 02:16:31
%   aidev-1% fusion-node-1  | 02:15:46 fusion: -> registration_ack f0000001 -> 1aef1b86 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 02:15:46 fusion: -> registration_ack f0000001 -> 86ca6000 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 02:15:46 fusion: -> registration_ack f0000001 -> 341b9172 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 02:15:51 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% host-fusion-1  | 02:15:51 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
%   aidev-1% === block 3 02:16:31
%   aidev-1% 5
%   aidev-1% host-fusion-1  | 02:15:51 fusion: <- alert f0000001 ALERT_TYPE_INFORMATION "new track FTB5JT"
%   aidev-1% pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> records: 6304
anchor not the pod or the host fusion node: 0
msg.node_id of the radar, camera or vehicle: 0
records that did not decode: 0
records with a sensor node ID anywhere: 0
%   aidev-1% === block 4 02:16:32
%   aidev-1% radar-1   | 02:16:26 radar: <- task f0000001 -> 1aef1b86 24HS48 look_at {"location_list": 
camera-1  | 02:16:26 camera: <- task f0000001 -> 86ca6000 4RFSDG look_at {"location_list":
%   aidev-1% host-fusion-1  | 02:16:06 fusion: <- task_ack f0000001 -> f0000002 XAJ1KK TASK_STATUS_ACCEPTED ['Status report sent']
host-fusion-1  | 02:16:26 fusion: <- task_ack f0000001 -> f0000002 KWAQQQ TASK_STATUS_ACCEPTED ['look_at sent to 2 nodes']
%   aidev-1% %   aidev-1% === block 5 02:16:32
%   aidev-1%  Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% %   aidev-1% pod-bridge-1  | 02:16:42 pod-bridge: pod router lost
pod-bridge-1  | 02:16:42 pod-bridge: fabric router lost
pod-bridge-1  | 02:16:43 pod-bridge: fabric router back
pod-bridge-1  | 02:16:43 pod-bridge: pod router back
pod-bridge-1  | 02:16:46 pod-bridge: forwarded {'up': 67, 'down': 5}; dropped {}
%   aidev-1% === block 5.1 02:17:02
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-f47b832f1bdc Creating 
 Container apex-goat1-host-recorder-run-f47b832f1bdc Created 
2026-11-12 02:17:03,025 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
%   aidev-1%  Container apex-goat1-pod-bridge-run-7d90fae5369e Creating 
 Container apex-goat1-pod-bridge-run-7d90fae5369e Created 
2026-11-12 02:17:08,040 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
put: 1 status report on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
%   aidev-1% samples: 1 on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
  e.g. b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
%   aidev-1% 2
%   aidev-1% 0
%   aidev-1% === block 5.2 02:17:18
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-dae7d0c34912 Creating 
 Container apex-goat1-host-recorder-run-dae7d0c34912 Created 
2026-11-12 02:17:18,511 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
%   aidev-1%  Container apex-goat1-host-fusion-run-bde42ca7f8f2 Creating 
 Container apex-goat1-host-fusion-run-bde42ca7f8f2 Created 
2026-11-12 02:17:23,524 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
put: 1 status report on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001
%   aidev-1% samples: 0 on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
%   aidev-1% 2
%   aidev-1% 0
%   aidev-1% === block 5.3 02:17:33
%   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-fac41b80bed4 Creating 
 Container apex-goat1-host-recorder-run-fac41b80bed4 Created 
2026-11-12 02:17:33,983 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
samples: 0 on ** in 15 s; from this probe: 0
%   aidev-1%  Container apex-goat1-host-recorder-run-775a4250c950 Creating 
 Container apex-goat1-host-recorder-run-775a4250c950 Created 
2026-11-12 02:17:49,338 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
samples: 33 on */telemetry/sapient/*/v2/*/* in 15 s; from this probe: 0
  e.g. 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
  e.g. 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/status_report/f0000001-0000-4000-8000-000000000001
  e.g. b005ae3a8f2baf89160bd71632902672/telemetry/sapient/h1/v2/detection_report/f0000002-0000-4000-8000-000000000002
  e.g. b005ae3a8f2baf89160bd71632902672/telemetry/sapient/h1/v2/status_report/f0000002-0000-4000-8000-000000000002
%   aidev-1% 2
%   aidev-1% === block 5.4 02:18:04
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-recorder-run-8eff2190183a Creating 
 Container apex-goat1-recorder-run-8eff2190183a Created 
2026-11-12 02:18:04,748 probe-access connected to Zenoh router at tls/router.p1.h1:7447
%   aidev-1%  Container apex-goat1-radar-run-b9a8311d0888 Creating 
 Container apex-goat1-radar-run-b9a8311d0888 Created 
2026-11-12 02:18:09,773 probe-access connected to Zenoh router at tls/router.p1.h1:7447
put: 1 status report on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report
%   aidev-1% samples: 3 on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report in 15 s; from this probe: 0
  e.g. h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report
%   aidev-1% 1
%   aidev-1% 0
%   aidev-1% %   aidev-1% === block 5.5 02:18:20
%   aidev-1%  Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% === block 6 02:18:30
%   aidev-1%  Container apex-goat1-host-fusion-1 Restarting 
 Container apex-goat1-host-fusion-1 Started 
%   aidev-1% %   aidev-1% fusion-node-1  | 02:18:40 fusion: <- task f0000002 -> f0000001 8MJ406 request "Registration"
fusion-node-1  | 02:18:40 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% === block 7 02:19:20
%   aidev-1% %   aidev-1% %   aidev-1% 0
%   aidev-1% 6
%   aidev-1% %   aidev-1% %   aidev-1% 2
%   aidev-1% 0
%   aidev-1% pod-bridge-1  | 02:19:16 pod-bridge: forwarded {'up': 241, 'down': 13}; dropped {}
pod-bridge-1  | 02:19:30 pod-bridge: fabric router lost
pod-bridge-1  | 02:19:46 pod-bridge: forwarded {'up': 258, 'down': 14}; dropped {'other_side_down': 17}
pod-bridge-1  | 02:19:53 pod-bridge: fabric router back
pod-bridge-1  | 02:20:16 pod-bridge: forwarded {'up': 284, 'down': 15}; dropped {'other_side_down': 25}
%   aidev-1% %   aidev-1% === block 8 02:20:21
%   aidev-1%  Container apex-goat1-host-recorder-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopping 
 Container apex-goat1-vehicle-1 Stopping 
 Container apex-goat1-camera-1 Stopping 
 Container apex-goat1-recorder-1 Stopping 
 Container apex-goat1-fusion-node-1 Stopping 
 Container apex-goat1-radar-1 Stopping 
 Container apex-goat1-vehicle-1 Stopped 
 Container apex-goat1-vehicle-1 Removing 
 Container apex-goat1-vehicle-1 Removed 
 Container apex-goat1-bridge-node-1 Stopping 
 Container apex-goat1-camera-1 Stopped 
 Container apex-goat1-camera-1 Removing 
 Container apex-goat1-camera-1 Removed 
 Container apex-goat1-host-fusion-1 Stopped 
 Container apex-goat1-host-fusion-1 Removing 
 Container apex-goat1-host-fusion-1 Removed 
 Container apex-goat1-radar-1 Stopped 
 Container apex-goat1-radar-1 Removing 
 Container apex-goat1-radar-1 Removed 
 Container apex-goat1-recorder-1 Stopped 
 Container apex-goat1-recorder-1 Removing 
 Container apex-goat1-recorder-1 Removed 
 Container apex-goat1-host-recorder-1 Stopped 
 Container apex-goat1-host-recorder-1 Removing 
 Container apex-goat1-host-recorder-1 Removed 
 Container apex-goat1-fusion-node-1 Stopped 
 Container apex-goat1-fusion-node-1 Removing 
 Container apex-goat1-fusion-node-1 Removed 
 Container apex-goat1-pod-bridge-1 Stopped 
 Container apex-goat1-pod-bridge-1 Removing 
 Container apex-goat1-pod-bridge-1 Removed 
 Container apex-goat1-zenohd-fabric-1 Stopping 
 Container apex-goat1-bridge-node-1 Stopped 
 Container apex-goat1-bridge-node-1 Removing 
 Container apex-goat1-bridge-node-1 Removed 
 Container apex-goat1-zenohd-pod-1 Stopping 
 Container apex-goat1-zenohd-fabric-1 Stopped 
 Container apex-goat1-zenohd-fabric-1 Removing 
 Container apex-goat1-zenohd-fabric-1 Removed 
 Container apex-goat1-zenohd-pod-1 Stopped 
 Container apex-goat1-zenohd-pod-1 Removing 
 Container apex-goat1-zenohd-pod-1 Removed 
 Network apex-goat1_pod1 Removing 
 Network apex-goat1_host Removing 
 Network apex-goat1_mesh Removing 
 Network apex-goat1_host Removed 
 Network apex-goat1_mesh Removed 
 Network apex-goat1_pod1 Removed 
%   aidev-1%  Network apex-goat1_host Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_host Created 
 Network apex-goat1_host Created 
 Network apex-goat1_mesh Created 
 Network apex-goat1_mesh Created 
 Container apex-goat1-zenohd-fabric-1 Creating 
 Network apex-goat1_pod1 Created 
 Network apex-goat1_pod1 Created 
 Container apex-goat1-zenohd-pod-1 Creating 
 Container apex-goat1-zenohd-fabric-1 Created 
 Container apex-goat1-host-fusion-1 Creating 
 Container apex-goat1-host-recorder-1 Creating 
 Container apex-goat1-zenohd-pod-1 Created 
 Container apex-goat1-bridge-node-1 Creating 
 Container apex-goat1-fusion-node-1 Creating 
 Container apex-goat1-radar-1 Creating 
 Container apex-goat1-recorder-1 Creating 
 Container apex-goat1-pod-bridge-1 Creating 
 Container apex-goat1-camera-1 Creating 
 Container apex-goat1-host-recorder-1 Created 
 Container apex-goat1-host-fusion-1 Created 
 Container apex-goat1-radar-1 Created 
 Container apex-goat1-pod-bridge-1 Created 
 Container apex-goat1-fusion-node-1 Created 
 Container apex-goat1-camera-1 Created 
 Container apex-goat1-bridge-node-1 Created 
 Container apex-goat1-vehicle-1 Creating 
 Container apex-goat1-recorder-1 Created 
 Container apex-goat1-vehicle-1 Created 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
 Container apex-goat1-host-fusion-1 Starting 
 Container apex-goat1-host-recorder-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-camera-1 Starting 
 Container apex-goat1-radar-1 Starting 
 Container apex-goat1-fusion-node-1 Starting 
 Container apex-goat1-bridge-node-1 Starting 
 Container apex-goat1-pod-bridge-1 Starting 
 Container apex-goat1-recorder-1 Starting 
 Container apex-goat1-host-fusion-1 Started 
 Container apex-goat1-host-recorder-1 Started 
 Container apex-goat1-camera-1 Started 
 Container apex-goat1-radar-1 Started 
 Container apex-goat1-fusion-node-1 Started 
 Container apex-goat1-bridge-node-1 Started 
 Container apex-goat1-vehicle-1 Starting 
 Container apex-goat1-pod-bridge-1 Started 
 Container apex-goat1-recorder-1 Started 
 Container apex-goat1-vehicle-1 Started 
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% host-fusion-1  | 02:20:57 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
host-fusion-1  | 02:22:22 fusion: node f0000001 gone for 20 s; removed
host-fusion-1  | 02:22:37 fusion: -> task f0000002 -> f0000001 6E4AQ6 request "Registration"
host-fusion-1  | 02:22:37 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
%   aidev-1% fusion-node-1  | 02:20:57 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 02:22:37 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% === block 9 02:23:13
%   aidev-1% %   aidev-1% c3a5e2b99a4a843d0322ddddd5dde61cf5c9796a25bb1d962af9c9b519b84627  zenoh/goat1/router-pod1.json5
f7f5e342377767ddcf0e22d754d22236f1417967dcd2891927b6aea54a3bedf8  zenoh/goat1/router-fabric.json5
%   aidev-1% %   aidev-1% [pod1.slots]
radar2 = 3
radar = 0
camera = 1
vehicle = 2
%   aidev-1% router files unchanged
%   aidev-1% exit 0
%   aidev-1% c3a5e2b99a4a843d0322ddddd5dde61cf5c9796a25bb1d962af9c9b519b84627  zenoh/goat1/router-pod1.json5
f7f5e342377767ddcf0e22d754d22236f1417967dcd2891927b6aea54a3bedf8  zenoh/goat1/router-fabric.json5
%   aidev-1% %   aidev-1%  Container apex-goat1-zenohd-pod-1 Running 
 Container apex-goat1-radar2-1 Creating 
 Container apex-goat1-radar2-1 Created 
 Container apex-goat1-radar2-1 Starting 
 Container apex-goat1-radar2-1 Started 
%   aidev-1% %   aidev-1% 1
%   aidev-1% fusion-node-1  | 02:23:13 fusion: -> registration_ack f0000001 -> 83ff6077 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% 3
%   aidev-1% router not restarted
%   aidev-1% 0
%   aidev-1% === block 9.1 02:23:44
%   aidev-1%  Container apex-goat1-radar2-1 Stopping 
 Container apex-goat1-radar2-1 Stopped 
Going to remove apex-goat1-radar2-1
 Container apex-goat1-radar2-1 Removing 
 Container apex-goat1-radar2-1 Removed 
%   aidev-1% %   aidev-1% %   aidev-1% router files unchanged
%   aidev-1% exit 0
%   aidev-1% %   aidev-1% === build start 2026-11-12T02:23:54Z 1794450234
%   aidev-1% === block 10a 02:23:54
%   aidev-1%     Finished `release` profile [optimized] target(s) in 0.35s
%   aidev-1% %   aidev-1% %   aidev-1% goat 0.5.19
%   aidev-1% === build end 2026-11-12T02:23:55Z 1794450235
%   aidev-1% === block 10b 02:23:55
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% === block 10c 02:23:55
%   aidev-1% %   aidev-1%  Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% %   aidev-1% listening on `18214b1a34e3c722d1cac283b272a62c/**` via tls/router.fabric.h1:7447 — stopping after 1 event(s). Ctrl-C to stop.
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001 hex:0a0c08dac6d4d70610e8cecfb902122466303030303030312d303030302d343030302d383030302d3030303030303030303030313aec010a1a30314d373653343648313035563539334e5a4e434336464e484d121a30314d373652585245583552535747515a4350374e4234383048323a097a616808eb15fdbf119786e2c6d0964940190000000000005e4021d74c0bc490cd223f29b88b20c13e93173f310000000000002440380140013d6666663f5a410a0b4169722056656869636c65156666663f1a2d0a0f55415620526f746172792057696e6715cdcc4c3f180122130a0a436f6d6d65726369616c159a99193f18029a012d09d5ca1ea1b3fa27c011f466aa9e4ee3df3f19000000000000000021000000000000f03f29000000000000f03f
done after 0s — 1 event(s) on `18214b1a34e3c722d1cac283b272a62c/**` (the requested 1)
%   aidev-1% exit 0
%   aidev-1% listening on `18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/*` via tls/router.fabric.h1:7447 — stopping after 3 event(s). Ctrl-C to stop.
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
done after 2s — 3 event(s) on `18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/*` (the requested 3)
%   aidev-1% exit 0
%   aidev-1% 2
%   aidev-1% 4
%   aidev-1% 0
%   aidev-1% %   aidev-1%  Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% %   aidev-1% === end 2026-11-12T02:24:40Z
%   aidev-1%  Container apex-goat1-host-recorder-1 Stopping 
 Container apex-goat1-vehicle-1 Stopping 
 Container apex-goat1-radar-1 Stopping 
 Container apex-goat1-recorder-1 Stopping 
 Container apex-goat1-fusion-node-1 Stopping 
 Container apex-goat1-camera-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopping 
 Container apex-goat1-host-recorder-1 Stopped 
 Container apex-goat1-host-recorder-1 Removing 
 Container apex-goat1-host-recorder-1 Removed 
 Container apex-goat1-radar-1 Stopped 
 Container apex-goat1-radar-1 Removing 
 Container apex-goat1-radar-1 Removed 
 Container apex-goat1-recorder-1 Stopped 
 Container apex-goat1-recorder-1 Removing 
 Container apex-goat1-recorder-1 Removed 
 Container apex-goat1-fusion-node-1 Stopped 
 Container apex-goat1-fusion-node-1 Removing 
 Container apex-goat1-fusion-node-1 Removed 
 Container apex-goat1-camera-1 Stopped 
 Container apex-goat1-camera-1 Removing 
 Container apex-goat1-camera-1 Removed 
 Container apex-goat1-host-fusion-1 Stopped 
 Container apex-goat1-host-fusion-1 Removing 
 Container apex-goat1-host-fusion-1 Removed 
 Container apex-goat1-vehicle-1 Stopped 
 Container apex-goat1-vehicle-1 Removing 
 Container apex-goat1-vehicle-1 Removed 
 Container apex-goat1-bridge-node-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopped 
 Container apex-goat1-pod-bridge-1 Removing 
 Container apex-goat1-pod-bridge-1 Removed 
 Container apex-goat1-zenohd-fabric-1 Stopping 
 Container apex-goat1-bridge-node-1 Stopped 
 Container apex-goat1-bridge-node-1 Removing 
 Container apex-goat1-bridge-node-1 Removed 
 Container apex-goat1-zenohd-pod-1 Stopping 
 Container apex-goat1-zenohd-fabric-1 Stopped 
 Container apex-goat1-zenohd-fabric-1 Removing 
 Container apex-goat1-zenohd-fabric-1 Removed 
 Container apex-goat1-zenohd-pod-1 Stopped 
 Container apex-goat1-zenohd-pod-1 Removing 
 Container apex-goat1-zenohd-pod-1 Removed 
 Network apex-goat1_host Removing 
 Network apex-goat1_pod1 Removing 
 Network apex-goat1_mesh Removing 
 Network apex-goat1_host Removed 
 Network apex-goat1_mesh Removed 
 Network apex-goat1_pod1 Removed 
%   aidev-1% 