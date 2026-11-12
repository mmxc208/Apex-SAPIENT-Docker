%   aidev-1% %   aidev-1% %   aidev-1% === block helper
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% === block 1
%   aidev-1% %   aidev-1% %   aidev-1%  Network apex-goat1_host Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_pod1 Created 
 Network apex-goat1_pod1 Created 
 Container apex-goat1-zenohd-pod-1 Creating 
 Network apex-goat1_host Created 
 Network apex-goat1_host Created 
 Network apex-goat1_mesh Created 
 Network apex-goat1_mesh Created 
 Container apex-goat1-zenohd-fabric-1 Creating 
 Container apex-goat1-zenohd-pod-1 Created 
 Container apex-goat1-recorder-1 Creating 
 Container apex-goat1-camera-1 Creating 
 Container apex-goat1-bridge-node-1 Creating 
 Container apex-goat1-fusion-node-1 Creating 
 Container apex-goat1-radar-1 Creating 
 Container apex-goat1-zenohd-fabric-1 Created 
 Container apex-goat1-host-recorder-1 Creating 
 Container apex-goat1-pod-bridge-1 Creating 
 Container apex-goat1-host-fusion-1 Creating 
 Container apex-goat1-camera-1 Created 
 Container apex-goat1-radar-1 Created 
 Container apex-goat1-bridge-node-1 Created 
 Container apex-goat1-vehicle-1 Creating 
 Container apex-goat1-recorder-1 Created 
 Container apex-goat1-fusion-node-1 Created 
 Container apex-goat1-host-fusion-1 Created 
 Container apex-goat1-pod-bridge-1 Created 
 Container apex-goat1-host-recorder-1 Created 
 Container apex-goat1-vehicle-1 Created 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-fusion-node-1 Starting 
 Container apex-goat1-camera-1 Starting 
 Container apex-goat1-bridge-node-1 Starting 
 Container apex-goat1-radar-1 Starting 
 Container apex-goat1-recorder-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
 Container apex-goat1-host-recorder-1 Starting 
 Container apex-goat1-pod-bridge-1 Starting 
 Container apex-goat1-host-fusion-1 Starting 
 Container apex-goat1-fusion-node-1 Started 
 Container apex-goat1-camera-1 Started 
 Container apex-goat1-bridge-node-1 Started 
 Container apex-goat1-vehicle-1 Starting 
 Container apex-goat1-radar-1 Started 
 Container apex-goat1-recorder-1 Started 
 Container apex-goat1-host-recorder-1 Started 
 Container apex-goat1-pod-bridge-1 Started 
 Container apex-goat1-host-fusion-1 Started 
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
%   aidev-1% === block 2
%   aidev-1% fusion-node-1  | 00:19:18 fusion: -> registration_ack f0000001 -> 86ca6000 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 00:19:18 fusion: -> registration_ack f0000001 -> 1aef1b86 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 00:19:18 fusion: -> registration_ack f0000001 -> 341b9172 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 00:19:23 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% host-fusion-1  | 00:19:23 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
%   aidev-1% === block 3
%   aidev-1% 5
%   aidev-1% host-fusion-1  | 00:19:23 fusion: <- alert f0000001 ALERT_TYPE_INFORMATION "new track V265FC"
%   aidev-1% pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> records: 1422
anchor not the pod or the host fusion node: 0
msg.node_id of the radar, camera or vehicle: 0
%   aidev-1% === block 4
%   aidev-1% camera-1  | 00:19:58 camera: <- task f0000001 -> 86ca6000 9X78C9 look_at {"location_list":
radar-1   | 00:19:58 radar: <- task f0000001 -> 1aef1b86 DQR6YH look_at {"location_list": 
%   aidev-1% host-fusion-1  | 00:19:38 fusion: <- task_ack f0000001 -> f0000002 2TKEHC TASK_STATUS_ACCEPTED ['Status report sent']
host-fusion-1  | 00:19:58 fusion: <- task_ack f0000001 -> f0000002 R1N3AR TASK_STATUS_ACCEPTED ['look_at sent to 2 nodes']
%   aidev-1% === block 5
%   aidev-1%  Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% %   aidev-1% pod-bridge-1  | 00:20:14 pod-bridge: pod router lost
pod-bridge-1  | 00:20:14 pod-bridge: fabric router lost
pod-bridge-1  | 00:20:15 pod-bridge: fabric router back
pod-bridge-1  | 00:20:15 pod-bridge: pod router back
pod-bridge-1  | 00:20:18 pod-bridge: forwarded {'up': 65, 'down': 4}; dropped {}
%   aidev-1% === block 5.1
%   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-03342d279b65 Creating 
 Container apex-goat1-host-recorder-run-03342d279b65 Created 
2026-11-12 00:20:35,078 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
%   aidev-1%  Container apex-goat1-pod-bridge-run-9ee1233e3813 Creating 
 Container apex-goat1-pod-bridge-run-9ee1233e3813 Created 
2026-11-12 00:20:40,079 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
put: 1 status report on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
%   aidev-1% samples: 1 on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
  e.g. b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
%   aidev-1% 2
%   aidev-1% 0
%   aidev-1% === block 5.2
%   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-3b884e105447 Creating 
 Container apex-goat1-host-recorder-run-3b884e105447 Created 
2026-11-12 00:20:50,542 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
%   aidev-1%  Container apex-goat1-host-fusion-run-2e059ede3fb9 Creating 
 Container apex-goat1-host-fusion-run-2e059ede3fb9 Created 
2026-11-12 00:20:55,575 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
put: 1 status report on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001
%   aidev-1% samples: 0 on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
%   aidev-1% 2
%   aidev-1% 0
%   aidev-1% === block 5.3
%   aidev-1%  Container apex-goat1-host-recorder-run-c02b12b248d3 Creating 
 Container apex-goat1-host-recorder-run-c02b12b248d3 Created 
2026-11-12 00:21:06,014 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
samples: 0 on ** in 15 s; from this probe: 0
%   aidev-1%  Container apex-goat1-host-recorder-run-9c656e9970a4 Creating 
 Container apex-goat1-host-recorder-run-9c656e9970a4 Created 
2026-11-12 00:21:21,350 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
samples: 33 on */telemetry/sapient/*/v2/*/* in 15 s; from this probe: 0
  e.g. 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
  e.g. 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/status_report/f0000001-0000-4000-8000-000000000001
  e.g. b005ae3a8f2baf89160bd71632902672/telemetry/sapient/h1/v2/detection_report/f0000002-0000-4000-8000-000000000002
  e.g. b005ae3a8f2baf89160bd71632902672/telemetry/sapient/h1/v2/status_report/f0000002-0000-4000-8000-000000000002
%   aidev-1% 2
%   aidev-1% === block 5.4
%   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-recorder-run-47017cca9cb9 Creating 
 Container apex-goat1-recorder-run-47017cca9cb9 Created 
2026-11-12 00:21:36,767 probe-access connected to Zenoh router at tls/router.p1.h1:7447
%   aidev-1%  Container apex-goat1-radar-run-b2d135ade2d0 Creating 
 Container apex-goat1-radar-run-b2d135ade2d0 Created 
2026-11-12 00:21:41,775 probe-access connected to Zenoh router at tls/router.p1.h1:7447
put: 1 status report on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report
%   aidev-1% samples: 3 on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report in 15 s; from this probe: 0
  e.g. h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report
%   aidev-1% 1
%   aidev-1% 0
%   aidev-1% === block 5.5
%   aidev-1%  Container apex-goat1-zenohd-pod-1 Recreate 
 Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% === block 6
%   aidev-1%  Container apex-goat1-host-fusion-1 Restarting 
 Container apex-goat1-host-fusion-1 Started 
%   aidev-1% %   aidev-1% fusion-node-1  | 00:22:15 fusion: <- task f0000002 -> f0000001 XPNT5Y request "Registration"
fusion-node-1  | 00:22:15 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node (re-registration)']
%   aidev-1% === block 7
%   aidev-1% %   aidev-1% %   aidev-1% 0
%   aidev-1% 6
%   aidev-1% %   aidev-1% %   aidev-1% 2
%   aidev-1% 0
%   aidev-1% pod-bridge-1  | 00:22:48 pod-bridge: forwarded {'up': 242, 'down': 13}; dropped {}
pod-bridge-1  | 00:23:02 pod-bridge: fabric router lost
pod-bridge-1  | 00:23:18 pod-bridge: forwarded {'up': 258, 'down': 14}; dropped {'other_side_down': 18}
pod-bridge-1  | 00:23:25 pod-bridge: fabric router back
pod-bridge-1  | 00:23:48 pod-bridge: forwarded {'up': 283, 'down': 15}; dropped {'other_side_down': 26}
%   aidev-1% === save logs 7
%   aidev-1% %   aidev-1% === block 8
%   aidev-1%  Container apex-goat1-camera-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopping 
 Container apex-goat1-vehicle-1 Stopping 
 Container apex-goat1-host-recorder-1 Stopping 
 Container apex-goat1-fusion-node-1 Stopping 
 Container apex-goat1-recorder-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopping 
 Container apex-goat1-radar-1 Stopping 
 Container apex-goat1-camera-1 Stopped 
 Container apex-goat1-camera-1 Removing 
 Container apex-goat1-camera-1 Removed 
 Container apex-goat1-radar-1 Stopped 
 Container apex-goat1-radar-1 Removing 
 Container apex-goat1-radar-1 Removed 
 Container apex-goat1-host-recorder-1 Stopped 
 Container apex-goat1-host-recorder-1 Removing 
 Container apex-goat1-host-recorder-1 Removed 
 Container apex-goat1-recorder-1 Stopped 
 Container apex-goat1-recorder-1 Removing 
 Container apex-goat1-recorder-1 Removed 
 Container apex-goat1-fusion-node-1 Stopped 
 Container apex-goat1-fusion-node-1 Removing 
 Container apex-goat1-fusion-node-1 Removed 
 Container apex-goat1-vehicle-1 Stopped 
 Container apex-goat1-vehicle-1 Removing 
 Container apex-goat1-vehicle-1 Removed 
 Container apex-goat1-bridge-node-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopped 
 Container apex-goat1-pod-bridge-1 Removing 
 Container apex-goat1-pod-bridge-1 Removed 
 Container apex-goat1-host-fusion-1 Stopped 
 Container apex-goat1-host-fusion-1 Removing 
 Container apex-goat1-host-fusion-1 Removed 
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
 Network apex-goat1_mesh Removing 
 Network apex-goat1_pod1 Removing 
 Network apex-goat1_host Removed 
 Network apex-goat1_mesh Removed 
 Network apex-goat1_pod1 Removed 
%   aidev-1%  Network apex-goat1_host Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_pod1 Creating 
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
 Container apex-goat1-camera-1 Creating 
 Container apex-goat1-radar-1 Creating 
 Container apex-goat1-zenohd-fabric-1 Created 
 Container apex-goat1-host-recorder-1 Creating 
 Container apex-goat1-host-fusion-1 Creating 
 Container apex-goat1-pod-bridge-1 Creating 
 Container apex-goat1-recorder-1 Created 
 Container apex-goat1-fusion-node-1 Created 
 Container apex-goat1-radar-1 Created 
 Container apex-goat1-bridge-node-1 Created 
 Container apex-goat1-vehicle-1 Creating 
 Container apex-goat1-host-recorder-1 Created 
 Container apex-goat1-camera-1 Created 
 Container apex-goat1-host-fusion-1 Created 
 Container apex-goat1-pod-bridge-1 Created 
 Container apex-goat1-vehicle-1 Created 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
 Container apex-goat1-host-fusion-1 Starting 
 Container apex-goat1-host-recorder-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-bridge-node-1 Starting 
 Container apex-goat1-radar-1 Starting 
 Container apex-goat1-pod-bridge-1 Starting 
 Container apex-goat1-recorder-1 Starting 
 Container apex-goat1-fusion-node-1 Starting 
 Container apex-goat1-camera-1 Starting 
 Container apex-goat1-host-fusion-1 Started 
 Container apex-goat1-host-recorder-1 Started 
 Container apex-goat1-bridge-node-1 Started 
 Container apex-goat1-vehicle-1 Starting 
 Container apex-goat1-radar-1 Started 
 Container apex-goat1-pod-bridge-1 Started 
 Container apex-goat1-recorder-1 Started 
 Container apex-goat1-fusion-node-1 Started 
 Container apex-goat1-camera-1 Started 
 Container apex-goat1-vehicle-1 Started 
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% host-fusion-1  | 00:24:29 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
host-fusion-1  | 00:25:54 fusion: node f0000001 gone for 20 s; removed
host-fusion-1  | 00:26:09 fusion: -> task f0000002 -> f0000001 FWNQRB request "Registration"
host-fusion-1  | 00:26:09 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
%   aidev-1% fusion-node-1  | 00:24:29 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 00:26:09 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% === block 9
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
%   aidev-1% fusion-node-1  | 00:26:45 fusion: -> registration_ack f0000001 -> 83ff6077 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% 3
%   aidev-1% router not restarted
%   aidev-1% 0
%   aidev-1% === block 9.1
%   aidev-1%  Container apex-goat1-radar2-1 Stopping 
 Container apex-goat1-radar2-1 Stopped 
Going to remove apex-goat1-radar2-1
 Container apex-goat1-radar2-1 Removing 
 Container apex-goat1-radar2-1 Removed 
%   aidev-1% %   aidev-1% %   aidev-1% router files unchanged
%   aidev-1% exit 0
%   aidev-1% %   aidev-1% === save logs
%   aidev-1% %   aidev-1% === end
%   aidev-1%  Container apex-goat1-camera-1 Stopping 
 Container apex-goat1-vehicle-1 Stopping 
 Container apex-goat1-fusion-node-1 Stopping 
 Container apex-goat1-recorder-1 Stopping 
 Container apex-goat1-radar-1 Stopping 
 Container apex-goat1-host-recorder-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopping 
 Container apex-goat1-camera-1 Stopped 
 Container apex-goat1-camera-1 Removing 
 Container apex-goat1-camera-1 Removed 
 Container apex-goat1-fusion-node-1 Stopped 
 Container apex-goat1-fusion-node-1 Removing 
 Container apex-goat1-fusion-node-1 Removed 
 Container apex-goat1-vehicle-1 Stopped 
 Container apex-goat1-vehicle-1 Removing 
 Container apex-goat1-vehicle-1 Removed 
 Container apex-goat1-bridge-node-1 Stopping 
 Container apex-goat1-recorder-1 Stopped 
 Container apex-goat1-recorder-1 Removing 
 Container apex-goat1-recorder-1 Removed 
 Container apex-goat1-radar-1 Stopped 
 Container apex-goat1-radar-1 Removing 
 Container apex-goat1-radar-1 Removed 
 Container apex-goat1-host-fusion-1 Stopped 
 Container apex-goat1-host-fusion-1 Removing 
 Container apex-goat1-host-fusion-1 Removed 
 Container apex-goat1-host-recorder-1 Stopped 
 Container apex-goat1-host-recorder-1 Removing 
 Container apex-goat1-host-recorder-1 Removed 
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
 Network apex-goat1_mesh Removing 
 Network apex-goat1_host Removing 
 Network apex-goat1_mesh Removed 
 Network apex-goat1_pod1 Removed 
 Network apex-goat1_host Removed 
%   aidev-1% 