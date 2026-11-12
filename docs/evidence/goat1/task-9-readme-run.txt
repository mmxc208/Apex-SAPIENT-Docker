%   aidev-1% %   aidev-1% %   aidev-1% === block helper
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% === block 1
%   aidev-1% %   aidev-1%  Network apex-goat1_mesh Creating 
 Network apex-goat1_mesh Creating 
 Volume apex-goat1_host-records Creating 
 Volume apex-goat1_host-records Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_host Creating 
 Volume apex-goat1_pod-records Creating 
 Volume apex-goat1_pod-records Creating 
 Volume apex-goat1_host-records Created 
 Volume apex-goat1_host-records Created 
 Volume apex-goat1_pod-records Created 
 Volume apex-goat1_pod-records Created 
 Network apex-goat1_mesh Created 
 Network apex-goat1_mesh Created 
 Network apex-goat1_pod1 Created 
 Network apex-goat1_pod1 Created 
 Container apex-goat1-zenohd-pod-1 Creating 
 Network apex-goat1_host Created 
 Network apex-goat1_host Created 
 Container apex-goat1-zenohd-fabric-1 Creating 
 Container apex-goat1-zenohd-pod-1 Created 
 Container apex-goat1-camera-1 Creating 
 Container apex-goat1-fusion-node-1 Creating 
 Container apex-goat1-radar-1 Creating 
 Container apex-goat1-bridge-node-1 Creating 
 Container apex-goat1-recorder-1 Creating 
 Container apex-goat1-zenohd-fabric-1 Created 
 Container apex-goat1-pod-bridge-1 Creating 
 Container apex-goat1-host-fusion-1 Creating 
 Container apex-goat1-host-recorder-1 Creating 
 Container apex-goat1-radar-1 Created 
 Container apex-goat1-camera-1 Created 
 Container apex-goat1-bridge-node-1 Created 
 Container apex-goat1-vehicle-1 Creating 
 Container apex-goat1-fusion-node-1 Created 
 Container apex-goat1-recorder-1 Created 
 Container apex-goat1-host-fusion-1 Created 
 Container apex-goat1-pod-bridge-1 Created 
 Container apex-goat1-host-recorder-1 Created 
 Container apex-goat1-vehicle-1 Created 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-bridge-node-1 Starting 
 Container apex-goat1-recorder-1 Starting 
 Container apex-goat1-radar-1 Starting 
 Container apex-goat1-camera-1 Starting 
 Container apex-goat1-fusion-node-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
 Container apex-goat1-pod-bridge-1 Starting 
 Container apex-goat1-host-recorder-1 Starting 
 Container apex-goat1-host-fusion-1 Starting 
 Container apex-goat1-bridge-node-1 Started 
 Container apex-goat1-vehicle-1 Starting 
 Container apex-goat1-recorder-1 Started 
 Container apex-goat1-radar-1 Started 
 Container apex-goat1-camera-1 Started 
 Container apex-goat1-fusion-node-1 Started 
 Container apex-goat1-pod-bridge-1 Started 
 Container apex-goat1-host-recorder-1 Started 
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
%   aidev-1% fusion-node-1  | 23:47:51 fusion: -> registration_ack f0000001 -> 341b9172 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:47:53 fusion: -> registration_ack f0000001 -> 1aef1b86 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:47:53 fusion: -> registration_ack f0000001 -> 86ca6000 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 23:47:56 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% host-fusion-1  | 23:47:56 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
%   aidev-1% === block 3
%   aidev-1% 4
%   aidev-1% host-fusion-1  | 23:47:56 fusion: <- alert f0000001 ALERT_TYPE_INFORMATION "new track 6TR3WR"
%   aidev-1% pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> records: 93
anchor not the pod or the host fusion node: 0
msg.node_id of the radar, camera or vehicle: 0
%   aidev-1% === block 4
%   aidev-1% radar-1   | 23:48:31 radar: <- task f0000001 -> 1aef1b86 AG2327 look_at {"location_list": 
camera-1  | 23:48:31 camera: <- task f0000001 -> 86ca6000 VPS33S look_at {"location_list":
%   aidev-1% host-fusion-1  | 23:48:11 fusion: <- task_ack f0000001 -> f0000002 9WWS9Q TASK_STATUS_ACCEPTED ['Status report sent']
host-fusion-1  | 23:48:31 fusion: <- task_ack f0000001 -> f0000002 SBNACR TASK_STATUS_ACCEPTED ['look_at sent to 2 nodes']
%   aidev-1% === block 5
%   aidev-1%  Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% %   aidev-1% pod-bridge-1  | 23:48:46 pod-bridge: fabric router lost
pod-bridge-1  | 23:48:46 pod-bridge: pod router lost
pod-bridge-1  | 23:48:47 pod-bridge: fabric router back
pod-bridge-1  | 23:48:47 pod-bridge: pod router back
pod-bridge-1  | 23:48:51 pod-bridge: forwarded {'up': 64, 'down': 4}; dropped {}
%   aidev-1% === block 5.1
%   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-a595a8a45407 Creating 
 Container apex-goat1-host-recorder-run-a595a8a45407 Created 
2026-11-11 23:49:07,421 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
%   aidev-1%  Container apex-goat1-pod-bridge-run-502fbfba1841 Creating 
 Container apex-goat1-pod-bridge-run-502fbfba1841 Created 
2026-11-11 23:49:12,457 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
put: 1 status report on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
%   aidev-1% samples: 1 on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
  e.g. b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
%   aidev-1% 2
%   aidev-1% 0
%   aidev-1% === block 5.2
%   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-791d03fcc7cd Creating 
 Container apex-goat1-host-recorder-run-791d03fcc7cd Created 
2026-11-11 23:49:22,884 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
%   aidev-1%  Container apex-goat1-host-fusion-run-5a7f0f59497c Creating 
 Container apex-goat1-host-fusion-run-5a7f0f59497c Created 
2026-11-11 23:49:27,919 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
put: 1 status report on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001
%   aidev-1% samples: 0 on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
%   aidev-1% 2
%   aidev-1% 0
%   aidev-1% === block 5.3
%   aidev-1%  Container apex-goat1-host-recorder-run-39158eed54a5 Creating 
 Container apex-goat1-host-recorder-run-39158eed54a5 Created 
2026-11-11 23:49:38,348 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
samples: 0 on ** in 15 s; from this probe: 0
%   aidev-1%  Container apex-goat1-host-recorder-run-880a200a4e3d Creating 
 Container apex-goat1-host-recorder-run-880a200a4e3d Created 
2026-11-11 23:49:53,698 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
samples: 31 on */telemetry/sapient/*/v2/*/* in 15 s; from this probe: 0
  e.g. 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
  e.g. 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/status_report/f0000001-0000-4000-8000-000000000001
  e.g. b005ae3a8f2baf89160bd71632902672/telemetry/sapient/h1/v2/detection_report/f0000002-0000-4000-8000-000000000002
  e.g. b005ae3a8f2baf89160bd71632902672/telemetry/sapient/h1/v2/status_report/f0000002-0000-4000-8000-000000000002
%   aidev-1% 2
%   aidev-1% === block 5.4
%   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-recorder-run-0a815324b162 Creating 
 Container apex-goat1-recorder-run-0a815324b162 Created 
2026-11-11 23:50:09,087 probe-access connected to Zenoh router at tls/router.p1.h1:7447
%   aidev-1%  Container apex-goat1-radar-run-d7f2fc7a241a Creating 
 Container apex-goat1-radar-run-d7f2fc7a241a Created 
2026-11-11 23:50:14,126 probe-access connected to Zenoh router at tls/router.p1.h1:7447
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
%   aidev-1% %   aidev-1% fusion-node-1  | 23:50:45 fusion: <- task f0000002 -> f0000001 K2JYBJ request "Registration"
fusion-node-1  | 23:50:45 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% === block 7
%   aidev-1%  Container apex-goat1-vehicle-1 Stopping 
 Container apex-goat1-host-recorder-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopping 
 Container apex-goat1-fusion-node-1 Stopping 
 Container apex-goat1-recorder-1 Stopping 
 Container apex-goat1-radar-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopping 
 Container apex-goat1-camera-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopped 
 Container apex-goat1-host-fusion-1 Removing 
 Container apex-goat1-host-fusion-1 Removed 
 Container apex-goat1-vehicle-1 Stopped 
 Container apex-goat1-vehicle-1 Removing 
 Container apex-goat1-vehicle-1 Removed 
 Container apex-goat1-bridge-node-1 Stopping 
 Container apex-goat1-camera-1 Stopped 
 Container apex-goat1-camera-1 Removing 
 Container apex-goat1-camera-1 Removed 
 Container apex-goat1-recorder-1 Stopped 
 Container apex-goat1-recorder-1 Removing 
 Container apex-goat1-recorder-1 Removed 
 Container apex-goat1-radar-1 Stopped 
 Container apex-goat1-radar-1 Removing 
 Container apex-goat1-radar-1 Removed 
 Container apex-goat1-fusion-node-1 Stopped 
 Container apex-goat1-fusion-node-1 Removing 
 Container apex-goat1-fusion-node-1 Removed 
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
 Network apex-goat1_host Removing 
 Network apex-goat1_mesh Removing 
 Network apex-goat1_host Removed 
 Network apex-goat1_mesh Removed 
 Network apex-goat1_pod1 Removed 
%   aidev-1% 