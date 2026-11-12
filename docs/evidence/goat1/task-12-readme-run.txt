%   aidev-1% %   aidev-1% %   aidev-1% === start 2026-11-12T01:23:41Z
%   aidev-1% === block helper 01:23:41
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% === block 1 01:23:41
%   aidev-1% %   aidev-1% %   aidev-1%  Network apex-goat1_pod1 Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_mesh Created 
 Network apex-goat1_mesh Created 
 Network apex-goat1_host Created 
 Network apex-goat1_host Created 
 Container apex-goat1-zenohd-fabric-1 Creating 
 Network apex-goat1_pod1 Created 
 Network apex-goat1_pod1 Created 
 Container apex-goat1-zenohd-pod-1 Creating 
 Container apex-goat1-zenohd-fabric-1 Created 
 Container apex-goat1-host-fusion-1 Creating 
 Container apex-goat1-host-recorder-1 Creating 
 Container apex-goat1-zenohd-pod-1 Created 
 Container apex-goat1-fusion-node-1 Creating 
 Container apex-goat1-camera-1 Creating 
 Container apex-goat1-radar-1 Creating 
 Container apex-goat1-pod-bridge-1 Creating 
 Container apex-goat1-recorder-1 Creating 
 Container apex-goat1-bridge-node-1 Creating 
 Container apex-goat1-host-fusion-1 Created 
 Container apex-goat1-host-recorder-1 Created 
 Container apex-goat1-fusion-node-1 Created 
 Container apex-goat1-recorder-1 Created 
 Container apex-goat1-bridge-node-1 Created 
 Container apex-goat1-vehicle-1 Creating 
 Container apex-goat1-camera-1 Created 
 Container apex-goat1-pod-bridge-1 Created 
 Container apex-goat1-radar-1 Created 
 Container apex-goat1-vehicle-1 Created 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
 Container apex-goat1-host-fusion-1 Starting 
 Container apex-goat1-host-recorder-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-fusion-node-1 Starting 
 Container apex-goat1-recorder-1 Starting 
 Container apex-goat1-camera-1 Starting 
 Container apex-goat1-pod-bridge-1 Starting 
 Container apex-goat1-bridge-node-1 Starting 
 Container apex-goat1-radar-1 Starting 
 Container apex-goat1-host-fusion-1 Started 
 Container apex-goat1-host-recorder-1 Started 
 Container apex-goat1-fusion-node-1 Started 
 Container apex-goat1-recorder-1 Started 
 Container apex-goat1-camera-1 Started 
 Container apex-goat1-pod-bridge-1 Started 
 Container apex-goat1-bridge-node-1 Started 
 Container apex-goat1-vehicle-1 Starting 
 Container apex-goat1-radar-1 Started 
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
%   aidev-1% === block 2 01:24:27
%   aidev-1% fusion-node-1  | 01:23:42 fusion: -> registration_ack f0000001 -> 86ca6000 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 01:23:42 fusion: -> registration_ack f0000001 -> 1aef1b86 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 01:23:42 fusion: -> registration_ack f0000001 -> 341b9172 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 01:23:47 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% host-fusion-1  | 01:23:47 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
%   aidev-1% === block 3 01:24:28
%   aidev-1% 5
%   aidev-1% host-fusion-1  | 01:23:47 fusion: <- alert f0000001 ALERT_TYPE_INFORMATION "new track Z6EWXY"
%   aidev-1% pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> pipe quote> records: 4656
anchor not the pod or the host fusion node: 0
msg.node_id of the radar, camera or vehicle: 0
records that did not decode: 0
records with a sensor node ID anywhere: 0
%   aidev-1% === block 4 01:24:28
%   aidev-1% camera-1  | 01:24:22 camera: <- task f0000001 -> 86ca6000 ETGGDQ look_at {"location_list":
radar-1   | 01:24:22 radar: <- task f0000001 -> 1aef1b86 CGEN0T look_at {"location_list": 
%   aidev-1% host-fusion-1  | 01:24:02 fusion: <- task_ack f0000001 -> f0000002 9NZKWJ TASK_STATUS_ACCEPTED ['Status report sent']
host-fusion-1  | 01:24:22 fusion: <- task_ack f0000001 -> f0000002 C6A1J0 TASK_STATUS_ACCEPTED ['look_at sent to 2 nodes']
%   aidev-1% %   aidev-1% === block 5 01:24:28
%   aidev-1%  Container apex-goat1-zenohd-pod-1 Recreate 
 Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% %   aidev-1% pod-bridge-1  | 01:24:38 pod-bridge: pod router lost
pod-bridge-1  | 01:24:38 pod-bridge: fabric router lost
pod-bridge-1  | 01:24:39 pod-bridge: fabric router back
pod-bridge-1  | 01:24:39 pod-bridge: pod router back
pod-bridge-1  | 01:24:42 pod-bridge: forwarded {'up': 67, 'down': 5}; dropped {}
%   aidev-1% === block 5.1 01:24:59
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-2e36066f7cfd Creating 
 Container apex-goat1-host-recorder-run-2e36066f7cfd Created 
2026-11-12 01:24:59,324 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
%   aidev-1%  Container apex-goat1-pod-bridge-run-2c7375c05471 Creating 
 Container apex-goat1-pod-bridge-run-2c7375c05471 Created 
2026-11-12 01:25:04,375 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
put: 1 status report on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
%   aidev-1% samples: 1 on b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
  e.g. b005ae3a8f2baf89160bd71632902672/task/p1/sapient/v2/task/f0000001-0000-4000-8000-000000000001
%   aidev-1% 2
%   aidev-1% 0
%   aidev-1% === block 5.2 01:25:14
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-b78e2dd70a54 Creating 
 Container apex-goat1-host-recorder-run-b78e2dd70a54 Created 
2026-11-12 01:25:14,801 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
%   aidev-1%  Container apex-goat1-host-fusion-run-caca8a9b3c3a Creating 
 Container apex-goat1-host-fusion-run-caca8a9b3c3a Created 
2026-11-12 01:25:19,834 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
put: 1 status report on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001
%   aidev-1% samples: 0 on 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/alert/f0000001-0000-4000-8000-000000000001 in 15 s; from this probe: 0
%   aidev-1% 2
%   aidev-1% 0
%   aidev-1% === block 5.3 01:25:30
%   aidev-1% %   aidev-1%  Container apex-goat1-host-recorder-run-ac75b553755f Creating 
 Container apex-goat1-host-recorder-run-ac75b553755f Created 
2026-11-12 01:25:30,275 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
samples: 0 on ** in 15 s; from this probe: 0
%   aidev-1%  Container apex-goat1-host-recorder-run-e5393e090de2 Creating 
 Container apex-goat1-host-recorder-run-e5393e090de2 Created 
2026-11-12 01:25:45,633 probe-access connected to Zenoh router at tls/router.fabric.h1:7447
samples: 33 on */telemetry/sapient/*/v2/*/* in 15 s; from this probe: 0
  e.g. 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001
  e.g. 18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/status_report/f0000001-0000-4000-8000-000000000001
  e.g. b005ae3a8f2baf89160bd71632902672/telemetry/sapient/h1/v2/detection_report/f0000002-0000-4000-8000-000000000002
  e.g. b005ae3a8f2baf89160bd71632902672/telemetry/sapient/h1/v2/status_report/f0000002-0000-4000-8000-000000000002
%   aidev-1% 2
%   aidev-1% === block 5.4 01:26:00
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1%  Container apex-goat1-recorder-run-e095bd6061f3 Creating 
 Container apex-goat1-recorder-run-e095bd6061f3 Created 
2026-11-12 01:26:01,047 probe-access connected to Zenoh router at tls/router.p1.h1:7447
%   aidev-1%  Container apex-goat1-radar-run-5b4e073f23ff Creating 
 Container apex-goat1-radar-run-5b4e073f23ff Created 
2026-11-12 01:26:06,079 probe-access connected to Zenoh router at tls/router.p1.h1:7447
put: 1 status report on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report
%   aidev-1% samples: 3 on h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report in 15 s; from this probe: 0
  e.g. h1/p1/sapient/v2/86ca6000-1c36-4aed-875f-ac18ec0b5ab2/up/status_report
%   aidev-1% 1
%   aidev-1% 0
%   aidev-1% %   aidev-1% === block 5.5 01:26:16
%   aidev-1%  Container apex-goat1-zenohd-pod-1 Recreate 
 Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-pod-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% === block 6 01:26:26
%   aidev-1%  Container apex-goat1-host-fusion-1 Restarting 
 Container apex-goat1-host-fusion-1 Started 
%   aidev-1% %   aidev-1% fusion-node-1  | 01:26:37 fusion: <- task f0000002 -> f0000001 Q39T3Z request "Registration"
fusion-node-1  | 01:26:37 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% === block 7 01:27:17
%   aidev-1% %   aidev-1% %   aidev-1% 0
%   aidev-1% 6
%   aidev-1% %   aidev-1% %   aidev-1% 2
%   aidev-1% 0
%   aidev-1% pod-bridge-1  | 01:27:12 pod-bridge: forwarded {'up': 242, 'down': 13}; dropped {}
pod-bridge-1  | 01:27:27 pod-bridge: fabric router lost
pod-bridge-1  | 01:27:42 pod-bridge: forwarded {'up': 259, 'down': 14}; dropped {'other_side_down': 17}
pod-bridge-1  | 01:27:50 pod-bridge: fabric router back
pod-bridge-1  | 01:28:12 pod-bridge: forwarded {'up': 285, 'down': 15}; dropped {'other_side_down': 25}
%   aidev-1% %   aidev-1% === block 8 01:28:17
%   aidev-1%  Container apex-goat1-recorder-1 Stopping 
 Container apex-goat1-fusion-node-1 Stopping 
 Container apex-goat1-camera-1 Stopping 
 Container apex-goat1-host-recorder-1 Stopping 
 Container apex-goat1-vehicle-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopping 
 Container apex-goat1-radar-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopping 
 Container apex-goat1-radar-1 Stopped 
 Container apex-goat1-radar-1 Removing 
 Container apex-goat1-radar-1 Removed 
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
 Container apex-goat1-host-recorder-1 Stopped 
 Container apex-goat1-host-recorder-1 Removing 
 Container apex-goat1-host-recorder-1 Removed 
 Container apex-goat1-fusion-node-1 Stopped 
 Container apex-goat1-fusion-node-1 Removing 
 Container apex-goat1-fusion-node-1 Removed 
 Container apex-goat1-recorder-1 Stopped 
 Container apex-goat1-recorder-1 Removing 
 Container apex-goat1-recorder-1 Removed 
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
 Network apex-goat1_mesh Removing 
 Network apex-goat1_pod1 Removing 
 Network apex-goat1_host Removing 
 Network apex-goat1_mesh Removed 
 Network apex-goat1_host Removed 
 Network apex-goat1_pod1 Removed 
%   aidev-1%  Network apex-goat1_host Creating 
 Network apex-goat1_host Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_mesh Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_pod1 Creating 
 Network apex-goat1_mesh Created 
 Network apex-goat1_mesh Created 
 Network apex-goat1_host Created 
 Network apex-goat1_host Created 
 Container apex-goat1-zenohd-fabric-1 Creating 
 Network apex-goat1_pod1 Created 
 Network apex-goat1_pod1 Created 
 Container apex-goat1-zenohd-pod-1 Creating 
 Container apex-goat1-zenohd-fabric-1 Created 
 Container apex-goat1-host-recorder-1 Creating 
 Container apex-goat1-host-fusion-1 Creating 
 Container apex-goat1-zenohd-pod-1 Created 
 Container apex-goat1-recorder-1 Creating 
 Container apex-goat1-camera-1 Creating 
 Container apex-goat1-radar-1 Creating 
 Container apex-goat1-bridge-node-1 Creating 
 Container apex-goat1-pod-bridge-1 Creating 
 Container apex-goat1-fusion-node-1 Creating 
 Container apex-goat1-host-fusion-1 Created 
 Container apex-goat1-host-recorder-1 Created 
 Container apex-goat1-recorder-1 Created 
 Container apex-goat1-radar-1 Created 
 Container apex-goat1-bridge-node-1 Created 
 Container apex-goat1-vehicle-1 Creating 
 Container apex-goat1-camera-1 Created 
 Container apex-goat1-pod-bridge-1 Created 
 Container apex-goat1-fusion-node-1 Created 
 Container apex-goat1-vehicle-1 Created 
 Container apex-goat1-zenohd-pod-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-pod-1 Started 
 Container apex-goat1-fusion-node-1 Starting 
 Container apex-goat1-camera-1 Starting 
 Container apex-goat1-radar-1 Starting 
 Container apex-goat1-recorder-1 Starting 
 Container apex-goat1-bridge-node-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
 Container apex-goat1-host-recorder-1 Starting 
 Container apex-goat1-pod-bridge-1 Starting 
 Container apex-goat1-host-fusion-1 Starting 
 Container apex-goat1-fusion-node-1 Started 
 Container apex-goat1-camera-1 Started 
 Container apex-goat1-radar-1 Started 
 Container apex-goat1-recorder-1 Started 
 Container apex-goat1-bridge-node-1 Started 
 Container apex-goat1-vehicle-1 Starting 
 Container apex-goat1-host-recorder-1 Started 
 Container apex-goat1-pod-bridge-1 Started 
 Container apex-goat1-host-fusion-1 Started 
 Container apex-goat1-vehicle-1 Started 
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% host-fusion-1  | 01:28:53 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
host-fusion-1  | 01:30:18 fusion: node f0000001 gone for 20 s; removed
host-fusion-1  | 01:30:33 fusion: -> task f0000002 -> f0000001 R5NRPQ request "Registration"
host-fusion-1  | 01:30:33 fusion: <- registration f0000001 "fake fusion node" [FUSION_NODE]
%   aidev-1% fusion-node-1  | 01:28:53 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
fusion-node-1  | 01:30:33 fusion: <- registration_ack f0000002 -> f0000001 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% === block 9 01:31:09
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
%   aidev-1% fusion-node-1  | 01:31:10 fusion: -> registration_ack f0000001 -> 83ff6077 acceptance=True ['Accepted by fake fusion node']
%   aidev-1% 3
%   aidev-1% router not restarted
%   aidev-1% 0
%   aidev-1% === block 9.1 01:31:40
%   aidev-1%  Container apex-goat1-radar2-1 Stopping 
 Container apex-goat1-radar2-1 Stopped 
Going to remove apex-goat1-radar2-1
 Container apex-goat1-radar2-1 Removing 
 Container apex-goat1-radar2-1 Removed 
%   aidev-1% %   aidev-1% %   aidev-1% router files unchanged
%   aidev-1% exit 0
%   aidev-1% %   aidev-1% === build start 2026-11-12T01:31:51Z 1794447111
%   aidev-1% === block 10a 01:31:51
%   aidev-1%     Updating crates.io index
 Downloading crates ...
  Downloaded aead v0.5.2
  Downloaded async-trait v0.1.89
  Downloaded asn1-rs-impl v0.2.0
  Downloaded cpufeatures v0.2.17
  Downloaded atomic-waker v1.1.2
  Downloaded bech32 v0.9.1
  Downloaded dyn-clone v1.0.20
  Downloaded asn1-rs-derive v0.6.0
  Downloaded array-init v2.1.0
  Downloaded adler2 v2.0.1
  Downloaded data-encoding v2.11.0
  Downloaded flagset v0.4.7
  Downloaded dunce v1.0.5
  Downloaded crossbeam-queue v0.3.12
  Downloaded block-buffer v0.12.1
  Downloaded anstyle-query v1.1.5
  Downloaded autocfg v1.5.1
  Downloaded crossbeam-deque v0.8.6
  Downloaded ciborium-ll v0.2.2
  Downloaded age-core v0.11.0
  Downloaded crossbeam v0.8.4
  Downloaded futures-core v0.3.32
  Downloaded find-crate v0.6.3
  Downloaded cpufeatures v0.3.1
  Downloaded dirs-sys v0.5.0
  Downloaded crypto-common v0.1.7
  Downloaded i18n-embed-fl v0.9.4
  Downloaded darling_macro v0.23.0
  Downloaded colorchoice v1.0.5
  Downloaded cfg_aliases v0.2.1
  Downloaded digest v0.10.7
  Downloaded cmake v0.1.58
  Downloaded deranged v0.5.8
  Downloaded clap_lex v1.1.0
  Downloaded byteorder v1.5.0
  Downloaded cipher v0.4.4
  Downloaded castaway v0.2.4
  Downloaded base64ct v1.8.3
  Downloaded asn1-rs v0.7.2
  Downloaded home v0.5.12
  Downloaded foldhash v0.1.5
  Downloaded ctr v0.9.2
  Downloaded json5 v0.4.1
  Downloaded bs58 v0.5.1
  Downloaded bit-vec v0.9.1
  Downloaded crossbeam-epoch v0.9.20
  Downloaded is_terminal_polyfill v1.70.2
  Downloaded chacha20 v0.10.2
  Downloaded futures-macro v0.3.32
  Downloaded dirs v6.0.0
  Downloaded crossbeam-utils v0.8.21
  Downloaded basic-toml v0.1.10
  Downloaded leb128 v0.2.6
  Downloaded lazy_static v1.5.0
  Downloaded keyed-set v1.1.0
  Downloaded const_format_proc_macros v0.2.34
  Downloaded bytes v1.11.1
  Downloaded der-parser v10.0.0
  Downloaded fluent-langneg v0.13.1
  Downloaded errno v0.3.14
  Downloaded crossbeam-channel v0.5.15
  Downloaded libloading v0.8.9
  Downloaded digest v0.11.3
  Downloaded idna_adapter v1.2.2
  Downloaded form_urlencoded v1.2.2
  Downloaded heck v0.5.0
  Downloaded num-conv v0.2.2
  Downloaded git-version-macro v0.3.9
  Downloaded der v0.7.10
  Downloaded base64 v0.22.1
  Downloaded ident_case v1.0.1
  Downloaded async-compression v0.4.51
  Downloaded num-iter v0.1.45
  Downloaded const_format v0.2.36
  Downloaded compact_str v0.8.2
  Downloaded futures-executor v0.3.32
  Downloaded ecdsa v0.17.0
  Downloaded oid-registry v0.7.1
  Downloaded fnv v1.0.7
  Downloaded cc v1.2.62
  Downloaded ghash v0.5.1
  Downloaded phf_shared v0.13.1
  Downloaded matchers v0.2.0
  Downloaded opaque-debug v0.3.1
  Downloaded parking v2.2.1
  Downloaded locale_config v0.3.0
  Downloaded oid-registry v0.8.1
  Downloaded nu-ansi-term v0.50.3
  Downloaded nanorand v0.7.0
  Downloaded percent-encoding v2.3.2
  Downloaded aho-corasick v1.1.4
  Downloaded pnet_base v0.35.0
  Downloaded num-traits v0.2.19
  Downloaded crossterm v0.28.1
  Downloaded prost-derive v0.13.5
  Downloaded pem-rfc7468 v1.0.0
  Downloaded phf v0.13.1
  Downloaded parking_lot v0.12.5
  Downloaded log v0.4.30
  Downloaded pest_generator v2.8.6
  Downloaded lz4_flex v0.10.0
  Downloaded pin-project-lite v0.2.17
  Downloaded phf_generator v0.13.1
  Downloaded primeorder v0.14.0
  Downloaded poly1305 v0.8.0
  Downloaded memchr v2.8.0
  Downloaded pem-rfc7468 v0.7.0
  Downloaded ordered-float v2.10.1
  Downloaded fluent v0.16.1
  Downloaded pem v3.0.6
  Downloaded pin-project-internal v1.1.13
  Downloaded pkcs8 v0.11.0
  Downloaded num-bigint-dig v0.8.6
  Downloaded pin-project v1.1.13
  Downloaded rand_chacha v0.3.1
  Downloaded proc-macro-error-attr2 v2.0.0
  Downloaded proc-macro-crate v3.5.0
  Downloaded primefield v0.14.0
  Downloaded http-body v1.0.1
  Downloaded ppv-lite86 v0.2.21
  Downloaded libm v0.2.16
  Downloaded rand_core v0.6.4
  Downloaded prost v0.13.5
  Downloaded curve25519-dalek v4.1.3
  Downloaded quinn-udp v0.5.14
  Downloaded prost-types v0.13.5
  Downloaded rand_core v0.10.1
  Downloaded pkg-config v0.3.33
  Downloaded hybrid-array v0.2.3
  Downloaded rustc_version v0.4.1
  Downloaded konst v0.2.20
  Downloaded proc-macro2 v1.0.106
  Downloaded proc-macro-error2 v2.0.1
  Downloaded polyval v0.6.2
  Downloaded pnet_sys v0.35.0
  Downloaded pnet_datalink v0.35.0
  Downloaded hmac v0.12.1
  Downloaded futures-io v0.3.32
  Downloaded futures-channel v0.3.32
  Downloaded rusticata-macros v4.1.0
  Downloaded humantime v2.3.0
  Downloaded event-listener v5.4.1
  Downloaded parking_lot_core v0.9.12
  Downloaded crypto-bigint v0.7.6
  Downloaded pest v2.8.6
  Downloaded nonempty-collections v0.3.1
  Downloaded instability v0.3.12
  Downloaded hex v0.4.3
  Downloaded ipnetwork v0.20.0
  Downloaded rust-embed-utils v8.11.0
  Downloaded ringbuffer-spsc v0.1.15
  Downloaded serde-value v0.7.0
  Downloaded rust-embed-impl v8.11.0
  Downloaded futures-sink v0.3.32
  Downloaded pest_meta v2.8.6
  Downloaded secrecy v0.8.0
  Downloaded intl_pluralrules v7.0.2
  Downloaded fastrand v2.4.1
  Downloaded schemars_derive v1.2.1
  Downloaded salsa20 v0.10.2
  Downloaded rustc-hash v2.1.2
  Downloaded ref-cast-impl v1.0.25
  Downloaded serde_spanned v1.1.1
  Downloaded rustc-hash v1.1.0
  Downloaded quinn v0.11.9
  Downloaded rustls-native-certs v0.8.3
  Downloaded powerfmt v0.2.0
  Downloaded rustversion v1.0.22
  Downloaded pkcs8 v0.10.2
  Downloaded rustls-pki-types v1.14.1
  Downloaded rand v0.10.3
  Downloaded serde_derive_internals v0.29.1
  Downloaded self_cell v1.2.2
  Downloaded rustls-platform-verifier v0.7.1
  Downloaded ryu v1.0.23
  Downloaded secrecy v0.10.3
  Downloaded scopeguard v1.2.0
  Downloaded intl-memoizer v0.5.3
  Downloaded generic-array v0.14.7
  Downloaded futures v0.3.32
  Downloaded rustls-webpki v0.103.16
  Downloaded sec1 v0.8.1
  Downloaded rusty-s3 v0.10.2
  Downloaded regex v1.12.3
  Downloaded portable-atomic v1.13.1
  Downloaded scrypt v0.11.0
  Downloaded mime v0.3.17
  Downloaded futures-task v0.3.32
  Downloaded stable_deref_trait v1.2.1
  Downloaded semver v1.0.28
  Downloaded self_cell v0.10.3
  Downloaded serde_derive v1.0.228
  Downloaded signature v2.2.0
  Downloaded quick-xml v0.42.0
  Downloaded thiserror v1.0.69
  Downloaded sharded-slab v0.1.7
  Downloaded icu_normalizer v2.2.0
  Downloaded potential_utf v0.1.5
  Downloaded jiff v0.2.27
  Downloaded subtle v2.6.1
  Downloaded signal-hook-mio v0.2.5
  Downloaded lru v0.12.5
  Downloaded schemars v0.9.0
  Downloaded tls_codec_derive v0.4.2
  Downloaded regex-syntax v0.8.10
  Downloaded time-core v0.1.8
  Downloaded terminal_size v0.4.4
  Downloaded stabby v72.1.1
  Downloaded tokio-macros v2.7.0
  Downloaded smallvec v1.15.1
  Downloaded typeid v1.0.3
  Downloaded thiserror-impl v2.0.18
  Downloaded thiserror v2.0.18
  Downloaded tracing-log v0.2.0
  Downloaded toml_parser v1.1.2+spec-1.1.0
  Downloaded tls_codec v0.4.2
  Downloaded token-cell v2.1.1
  Downloaded unicode-truncate v1.1.0
  Downloaded time-macros v0.2.27
  Downloaded ron v0.12.1
  Downloaded socket2 v0.6.3
  Downloaded thread_local v1.1.9
  Downloaded thiserror-impl v1.0.69
  Downloaded tower-service v0.3.3
  Downloaded toml_writer v1.1.1+spec-1.1.0
  Downloaded shellexpand v3.1.2
  Downloaded toml v0.8.23
  Downloaded rand_pcg v0.10.2
  Downloaded serde_yaml v0.9.34+deprecated
  Downloaded toml_write v0.1.2
  Downloaded static_assertions v1.1.0
  Downloaded rfc6979 v0.6.0
  Downloaded socket2 v0.5.10
  Downloaded tracing-attributes v0.1.31
  Downloaded same-file v1.0.6
  Downloaded petgraph v0.8.3
  Downloaded unicode-xid v0.2.6
  Downloaded uhlc v0.8.2
  Downloaded try-lock v0.2.5
  Downloaded stabby-abi v72.1.1
  Downloaded instant-xml v0.7.6
  Downloaded unic-langid v0.9.6
  Downloaded ucd-trie v0.1.7
  Downloaded validated_struct v2.2.0
  Downloaded indoc v2.0.7
  Downloaded httpdate v1.0.3
  Downloaded twox-hash v1.6.3
  Downloaded tungstenite v0.24.0
  Downloaded tls-listener v0.11.2
  Downloaded serde_json v1.0.150
  Downloaded tracing-core v0.1.36
  Downloaded type-map v0.5.1
  Downloaded fs_extra v1.3.0
  Downloaded http-body-util v0.1.3
  Downloaded elliptic-curve v0.14.1
  Downloaded serde_urlencoded v0.7.1
  Downloaded utf-8 v0.7.6
  Downloaded serde v1.0.228
  Downloaded ref-cast v1.0.25
  Downloaded untrusted v0.9.0
  Downloaded rustix v0.38.44
  Downloaded wnaf v0.14.1
  Downloaded unsafe-libyaml v0.2.11
  Downloaded rustix v1.1.4
  Downloaded zenoh-buffers v1.9.0
  Downloaded xmlparser v0.13.6
  Downloaded vec_map v0.8.2
  Downloaded validated_struct_macros v2.2.0
  Downloaded either v1.16.0
  Downloaded unzip-n v0.1.4
  Downloaded time v0.3.47
  Downloaded iana-time-zone v0.1.65
  Downloaded getrandom v0.4.2
  Downloaded tower v0.5.3
  Downloaded find-msvc-tools v0.1.9
  Downloaded tokio-util v0.7.18
  Downloaded zenoh-macros v1.9.0
  Downloaded tower-http v0.6.11
  Downloaded quote v1.0.45
  Downloaded age v0.11.3
  Downloaded toml_datetime v0.6.11
  Downloaded zenoh-link-quic_datagram v1.9.0
  Downloaded zerofrom-derive v0.1.7
  Downloaded flate2 v1.1.9
  Downloaded zenoh-sync v1.9.0
  Downloaded zenoh-crypto v1.9.0
  Downloaded tracing-serde v0.2.0
  Downloaded flume v0.11.1
  Downloaded zerofrom v0.1.8
  Downloaded pkcs1 v0.7.5
  Downloaded zenoh-task v1.9.0
  Downloaded zenoh-link-tcp v1.9.0
  Downloaded zenoh-result v1.9.0
  Downloaded zenoh-link-tls v1.9.0
  Downloaded zenoh-link-quic v1.9.0
  Downloaded zenoh-collections v1.9.0
  Downloaded zenoh-core v1.9.0
  Downloaded hyper-util v0.1.20
  Downloaded zmij v1.0.21
  Downloaded zerovec-derive v0.11.3
  Downloaded zenoh-link-ws v1.9.0
  Downloaded zenoh-link-udp v1.9.0
  Downloaded zeroize v1.8.2
  Downloaded unic-langid-impl v0.9.6
  Downloaded fluent-bundle v0.15.3
  Downloaded zenoh-plugin-trait v1.9.0
  Downloaded zenoh-keyexpr v1.9.0
  Downloaded unicode-segmentation v1.13.2
  Downloaded typenum v1.20.0
  Downloaded zeroize_derive v1.5.0
  Downloaded zenoh-util v1.9.0
  Downloaded zenoh-protocol v1.9.0
  Downloaded tower-layer v0.3.3
  Downloaded zenoh-link-unixsock_stream v1.9.0
  Downloaded tracing-subscriber v0.3.23
  Downloaded half v2.7.1
  Downloaded tracing v0.1.44
  Downloaded serde_with v3.21.0
  Downloaded url v2.5.8
  Downloaded ureq v2.12.1
  Downloaded tinystr v0.8.3
  Downloaded synstructure v0.13.2
  Downloaded shlex v1.3.0
  Downloaded yoke-derive v0.8.2
  Downloaded writeable v0.6.3
  Downloaded walkdir v2.5.0
  Downloaded version_check v0.9.5
  Downloaded sync_wrapper v1.0.2
  Downloaded rustls v0.23.46
  Downloaded webpki-roots v0.26.11
  Downloaded utf8_iter v1.0.4
  Downloaded uuid v1.23.1
  Downloaded want v0.3.1
  Downloaded tinyvec_macros v0.1.1
  Downloaded syn v1.0.109
  Downloaded strum v0.26.3
  Downloaded sha3 v0.10.9
  Downloaded linux-raw-sys v0.4.15
  Downloaded httparse v1.10.1
  Downloaded x509-parser v0.16.0
  Downloaded zenoh-ext v1.9.0
  Downloaded x509-parser v0.18.1
  Downloaded zerovec v0.11.6
  Downloaded webpki-roots v1.0.11
  Downloaded indexmap v1.9.3
  Downloaded icu_provider v2.2.0
  Downloaded getrandom v0.2.17
  Downloaded idna v1.1.0
  Downloaded zenoh v1.9.0
  Downloaded utf8parse v0.2.2
  Downloaded zerocopy-derive v0.8.48
  Downloaded zenoh-runtime v1.9.0
  Downloaded toml_datetime v0.7.5+spec-1.1.0
  Downloaded winnow v0.7.15
  Downloaded tokio-tungstenite v0.24.0
  Downloaded fluent-syntax v0.11.1
  Downloaded lru-slab v0.1.2
  Downloaded spin v0.9.8
  Downloaded siphasher v1.0.3
  Downloaded simd-adler32 v0.3.9
  Downloaded zerotrie v0.2.4
  Downloaded linux-raw-sys v0.12.1
  Downloaded unicase v2.9.0
  Downloaded toml_datetime v1.1.1+spec-1.1.0
  Downloaded stabby-macros v72.1.1
  Downloaded rcgen v0.14.8
  Downloaded icu_properties v2.2.0
  Downloaded spki v0.8.1
  Downloaded zenoh-transport v1.9.0
  Downloaded signal-hook-registry v1.4.8
  Downloaded sha2 v0.11.1
  Downloaded zerocopy v0.8.48
  Downloaded sha2 v0.10.9
  Downloaded serdect v0.4.3
  Downloaded serde_with_macros v3.21.0
  Downloaded tokio-rustls v0.26.4
  Downloaded schemars v1.2.1
  Downloaded icu_normalizer_data v2.2.0
  Downloaded hybrid-array v0.4.15
  Downloaded strum_macros v0.26.4
  Downloaded spki v0.7.3
  Downloaded slab v0.4.12
  Downloaded universal-hash v0.5.1
  Downloaded foldhash v0.2.0
  Downloaded ff v0.14.0
  Downloaded fastbloom v0.17.0
  Downloaded sha1 v0.10.6
  Downloaded serde_spanned v0.6.9
  Downloaded strsim v0.11.1
  Downloaded signature v3.0.0
  Downloaded icu_locale_core v2.2.0
  Downloaded hyper-rustls v0.27.9
  Downloaded group v0.14.0
  Downloaded i18n-config v0.4.8
  Downloaded io_tee v0.1.1
  Downloaded inout v0.1.4
  Downloaded quinn-proto v0.11.19
  Downloaded rustls-pemfile v2.2.0
  Downloaded zenoh-link v1.9.0
  Downloaded instant-xml-macros v0.7.2
  Downloaded hmac v0.13.0
  Downloaded prost-reflect v0.14.7
  Downloaded jobserver v0.1.35
  Downloaded ipnet v2.12.0
  Downloaded i18n-embed v0.15.4
  Downloaded ed25519 v2.2.3
  Downloaded hashbrown v0.12.3
  Downloaded chrono v0.4.44
  Downloaded git-version v0.3.9
  Downloaded aws-lc-rs v1.18.1
  Downloaded signal-hook v0.3.18
  Downloaded toml v0.5.11
  Downloaded tinyvec v1.11.0
  Downloaded spin v0.10.0
  Downloaded nom v7.1.3
  Downloaded mio v1.2.0
  Downloaded pest_derive v2.8.6
  Downloaded itertools v0.14.0
  Downloaded pbkdf2 v0.12.2
  Downloaded paste v1.0.15
  Downloaded num-bigint v0.4.6
  Downloaded http v1.4.1
  Downloaded minimal-lexical v0.2.1
  Downloaded phf_macros v0.13.1
  Downloaded itertools v0.13.0
  Downloaded miniz_oxide v0.8.9
  Downloaded clap_builder v4.6.0
  Downloaded p256 v0.14.0
  Downloaded ml-kem v0.2.3
  Downloaded litemap v0.8.2
  Downloaded getrandom v0.3.4
  Downloaded aes-gcm v0.10.3
  Downloaded once_cell v1.21.4
  Downloaded num-integer v0.1.46
  Downloaded yoke v0.8.2
  Downloaded yasna v0.6.0
  Downloaded serde_core v1.0.228
  Downloaded lock_api v0.4.14
  Downloaded displaydoc v0.2.5
  Downloaded icu_collections v2.2.0
  Downloaded mime_guess v2.0.5
  Downloaded md-5 v0.11.0
  Downloaded no-std-net v0.6.0
  Downloaded der v0.8.2
  Downloaded chacha20poly1305 v0.10.1
  Downloaded aes v0.8.4
  Downloaded option-ext v0.2.0
  Downloaded zenoh-link-commons v1.9.0
  Downloaded openssl-probe v0.2.1
  Downloaded num_cpus v1.17.0
  Downloaded fixedbitset v0.5.7
  Downloaded base64 v0.21.7
  Downloaded asn1-rs v0.6.2
  Downloaded darling_core v0.23.0
  Downloaded clap_complete v4.6.5
  Downloaded konst_macro_rules v0.2.19
  Downloaded keccak v0.1.6
  Downloaded itoa v1.0.18
  Downloaded const-oid v0.10.2
  Downloaded unicode-ident v1.0.24
  Downloaded kem v0.3.0-pre.0
  Downloaded i18n-embed-impl v0.8.4
  Downloaded toml v0.9.12+spec-1.1.0
  Downloaded ed25519-dalek v2.2.0
  Downloaded rsa v0.9.10
  Downloaded der-parser v9.0.0
  Downloaded crypto-common v0.2.2
  Downloaded clap v4.6.1
  Downloaded indexmap v2.14.0
  Downloaded hashbrown v0.16.1
  Downloaded toml_edit v0.22.27
  Downloaded base64 v0.23.1
  Downloaded zenoh-config v1.9.0
  Downloaded zenoh-codec v1.9.0
  Downloaded toml_edit v0.25.11+spec-1.1.0
  Downloaded allocator-api2 v0.2.21
  Downloaded ctutils v0.4.5
  Downloaded compression-codecs v0.4.46
  Downloaded ciborium-io v0.2.2
  Downloaded bitflags v2.11.1
  Downloaded crc32fast v1.5.0
  Downloaded const-oid v0.9.6
  Downloaded clap_derive v4.6.1
  Downloaded ciborium v0.2.2
  Downloaded cassowary v0.3.0
  Downloaded bincode v1.3.3
  Downloaded der_derive v0.7.3
  Downloaded concurrent-queue v2.5.0
  Downloaded cookie-factory v0.3.3
  Downloaded darling v0.23.0
  Downloaded x25519-dalek v2.0.1
  Downloaded cmov v0.5.4
  Downloaded anyhow v1.0.102
  Downloaded cfg-if v1.0.4
  Downloaded sha2-const-stable v0.1.0
  Downloaded rand v0.8.6
  Downloaded x509-cert v0.2.5
  Downloaded hyper v1.9.0
  Downloaded hkdf v0.13.0
  Downloaded reqwest v0.12.28
  Downloaded winnow v1.0.3
  Downloaded hkdf v0.12.4
  Downloaded h2 v0.4.20
  Downloaded hashbrown v0.17.1
  Downloaded futures-util v0.3.32
  Downloaded icu_properties_data v2.2.0
  Downloaded hashbrown v0.15.5
  Downloaded hashbrown v0.14.5
  Downloaded cpubits v0.1.1
  Downloaded block-buffer v0.10.4
  Downloaded arc-swap v1.9.1
  Downloaded anstream v1.0.0
  Downloaded unicode-width v0.1.14
  Downloaded unicode-width v0.2.0
  Downloaded syn v3.0.9
  Downloaded nix v0.29.0
  Downloaded syn v2.0.117
  Downloaded ahash v0.8.12
  Downloaded chacha20 v0.9.1
  Downloaded anstyle-parse v1.0.0
  Downloaded anstyle v1.0.14
  Downloaded equivalent v1.0.2
  Downloaded compression-core v0.4.34
  Downloaded base16ct v1.0.0
  Downloaded asn1-rs-derive v0.5.1
  Downloaded aws-lc-sys v0.45.0
  Downloaded ratatui v0.29.0
  Downloaded regex-automata v0.4.14
  Downloaded libc v0.2.186
  Downloaded rust-embed v8.11.0
  Downloaded tokio v1.52.3
  Downloaded ring v0.17.14
   Compiling proc-macro2 v1.0.106
   Compiling quote v1.0.45
   Compiling unicode-ident v1.0.24
   Compiling libc v0.2.186
   Compiling syn v2.0.117
   Compiling cfg-if v1.0.4
   Compiling serde_core v1.0.228
   Compiling version_check v0.9.5
   Compiling getrandom v0.2.17
   Compiling subtle v2.6.1
   Compiling serde v1.0.228
   Compiling zeroize_derive v1.5.0
   Compiling serde_derive v1.0.228
   Compiling zeroize v1.8.2
   Compiling typenum v1.20.0
   Compiling memchr v2.8.0
   Compiling rand_core v0.6.4
   Compiling generic-array v0.14.7
   Compiling displaydoc v0.2.5
   Compiling synstructure v0.13.2
   Compiling itoa v1.0.18
   Compiling log v0.4.30
   Compiling once_cell v1.21.4
   Compiling libm v0.2.16
   Compiling crypto-common v0.1.7
   Compiling pin-project-lite v0.2.17
   Compiling autocfg v1.5.1
   Compiling num-traits v0.2.19
   Compiling rustversion v1.0.22
   Compiling zmij v1.0.21
   Compiling bytes v1.11.1
   Compiling scopeguard v1.2.0
   Compiling smallvec v1.15.1
   Compiling lock_api v0.4.14
   Compiling zerocopy v0.8.48
   Compiling rand_core v0.10.1
   Compiling zerocopy-derive v0.8.48
   Compiling errno v0.3.14
   Compiling const-oid v0.9.6
   Compiling signal-hook-registry v1.4.8
   Compiling jobserver v0.1.35
   Compiling find-msvc-tools v0.1.9
   Compiling shlex v1.3.0
   Compiling cc v1.2.62
   Compiling mio v1.2.0
   Compiling getrandom v0.4.2
   Compiling anyhow v1.0.102
   Compiling futures-core v0.3.32
   Compiling spin v0.9.8
   Compiling zerofrom-derive v0.1.7
   Compiling futures-sink v0.3.32
   Compiling block-buffer v0.10.4
   Compiling yoke-derive v0.8.2
   Compiling zerofrom v0.1.8
   Compiling bitflags v2.11.1
   Compiling socket2 v0.6.3
   Compiling portable-atomic v1.13.1
   Compiling stable_deref_trait v1.2.1
   Compiling yoke v0.8.2
   Compiling digest v0.10.7
   Compiling lazy_static v1.5.0
   Compiling tokio-macros v2.7.0
   Compiling tokio v1.52.3
   Compiling zerovec-derive v0.11.3
   Compiling zerovec v0.11.6
   Compiling tracing-core v0.1.36
   Compiling equivalent v1.0.2
   Compiling ref-cast v1.0.25
   Compiling slab v0.4.12
   Compiling serde_json v1.0.150
   Compiling futures-channel v0.3.32
   Compiling ring v0.17.14
   Compiling cmake v0.1.58
   Compiling cpufeatures v0.2.17
   Compiling pkg-config v0.3.33
   Compiling dunce v1.0.5
   Compiling fs_extra v1.3.0
   Compiling paste v1.0.15
   Compiling thiserror v1.0.69
   Compiling either v1.16.0
   Compiling aws-lc-sys v0.45.0
   Compiling ppv-lite86 v0.2.21
   Compiling rustls-pki-types v1.14.1
   Compiling futures-macro v0.3.32
   Compiling tracing-attributes v0.1.31
   Compiling ref-cast-impl v1.0.25
   Compiling futures-io v0.3.32
   Compiling futures-task v0.3.32
   Compiling futures-util v0.3.32
   Compiling tracing v0.1.44
   Compiling rand_chacha v0.3.1
   Compiling tinystr v0.8.3
   Compiling thiserror-impl v1.0.69
   Compiling serde_derive_internals v0.29.1
   Compiling ahash v0.8.12
   Compiling untrusted v0.9.0
   Compiling schemars_derive v1.2.1
   Compiling rand v0.8.6
   Compiling allocator-api2 v0.2.21
   Compiling aws-lc-rs v1.18.1
   Compiling minimal-lexical v0.2.1
   Compiling time-core v0.1.8
   Compiling powerfmt v0.2.0
   Compiling num-conv v0.2.2
   Compiling getrandom v0.3.4
   Compiling time-macros v0.2.27
   Compiling deranged v0.5.8
   Compiling nom v7.1.3
   Compiling hashbrown v0.14.5
   Compiling dyn-clone v1.0.20
   Compiling base64ct v1.8.3
   Compiling foldhash v0.2.0
   Compiling hashbrown v0.16.1
   Compiling time v0.3.47
   Compiling schemars v1.2.1
   Compiling keyed-set v1.1.0
   Compiling token-cell v2.1.1
   Compiling zenoh-result v1.9.0
   Compiling aho-corasick v1.1.4
   Compiling rustls v0.23.46
   Compiling regex-syntax v0.8.10
   Compiling strsim v0.11.1
   Compiling zenoh-macros v1.9.0
   Compiling thiserror v2.0.18
   Compiling regex-automata v0.4.14
   Compiling zenoh-keyexpr v1.9.0
   Compiling thiserror-impl v2.0.18
   Compiling typeid v1.0.3
   Compiling base64 v0.22.1
   Compiling rusticata-macros v4.1.0
   Compiling num-integer v0.1.46
   Compiling asn1-rs-impl v0.2.0
   Compiling cfg_aliases v0.2.1
   Compiling hashbrown v0.17.1
   Compiling ident_case v1.0.1
   Compiling rustc-hash v2.1.2
   Compiling darling_core v0.23.0
   Compiling indexmap v2.14.0
   Compiling hybrid-array v0.4.15
   Compiling ryu v1.0.23
   Compiling ucd-trie v0.1.7
   Compiling pest v2.8.6
   Compiling ron v0.12.1
   Compiling darling_macro v0.23.0
   Compiling unicode-xid v0.2.6
   Compiling semver v1.0.28
   Compiling cmov v0.5.4
   Compiling konst_macro_rules v0.2.19
   Compiling konst v0.2.20
   Compiling ctutils v0.4.5
   Compiling rustc_version v0.4.1
   Compiling const_format_proc_macros v0.2.34
   Compiling darling v0.23.0
   Compiling zenoh-runtime v1.9.0
   Compiling pest_meta v2.8.6
   Compiling zenoh-collections v1.9.0
   Compiling futures-executor v0.3.32
   Compiling option-ext v0.2.0
   Compiling winnow v0.7.15
   Compiling humantime v2.3.0
   Compiling const-oid v0.10.2
   Compiling dirs-sys v0.5.0
   Compiling futures v0.3.32
   Compiling zenoh-buffers v1.9.0
   Compiling pest_generator v2.8.6
   Compiling zenoh-core v1.9.0
   Compiling const_format v0.2.36
   Compiling num-bigint v0.4.6
   Compiling webpki-roots v1.0.11
   Compiling spin v0.10.0
   Compiling no-std-net v0.6.0
   Compiling data-encoding v2.11.0
   Compiling litemap v0.8.2
   Compiling siphasher v1.0.3
   Compiling writeable v0.6.3
   Compiling icu_locale_core v2.2.0
   Compiling pnet_base v0.35.0
   Compiling uhlc v0.8.2
   Compiling pest_derive v2.8.6
   Compiling dirs v6.0.0
   Compiling crypto-common v0.2.2
   Compiling matchers v0.2.0
   Compiling tracing-serde v0.2.0
   Compiling tracing-log v0.2.0
   Compiling potential_utf v0.1.5
   Compiling sharded-slab v0.1.7
   Compiling zerotrie v0.2.4
   Compiling inout v0.1.4
   Compiling ipnetwork v0.20.0
   Compiling asn1-rs-derive v0.6.0
   Compiling unzip-n v0.1.4
   Compiling nanorand v0.7.0
   Compiling thread_local v1.1.9
   Compiling pnet_sys v0.35.0
   Compiling icu_properties_data v2.2.0
   Compiling nu-ansi-term v0.50.3
   Compiling crossbeam-utils v0.8.21
   Compiling unsafe-libyaml v0.2.11
   Compiling winnow v1.0.3
   Compiling openssl-probe v0.2.1
   Compiling utf8_iter v1.0.4
   Compiling icu_normalizer_data v2.2.0
   Compiling icu_collections v2.2.0
   Compiling rustls-native-certs v0.8.3
   Compiling toml_parser v1.1.2+spec-1.1.0
   Compiling serde_yaml v0.9.34+deprecated
   Compiling tracing-subscriber v0.3.23
   Compiling pnet_datalink v0.35.0
   Compiling flume v0.11.1
   Compiling validated_struct_macros v2.2.0
   Compiling asn1-rs v0.7.2
   Compiling cipher v0.4.4
   Compiling icu_provider v2.2.0
   Compiling shellexpand v3.1.2
   Compiling json5 v0.4.1
   Compiling zenoh-protocol v1.9.0
   Compiling serde_with_macros v3.21.0
   Compiling quinn-udp v0.5.14
   Compiling tokio-util v0.7.18
   Compiling chacha20 v0.10.2
   Compiling async-trait v0.1.89
   Compiling serde_spanned v1.1.1
   Compiling toml_datetime v0.7.5+spec-1.1.0
   Compiling libloading v0.8.9
   Compiling tinyvec_macros v0.1.1
   Compiling percent-encoding v2.3.2
   Compiling toml_writer v1.1.1+spec-1.1.0
   Compiling home v0.5.12
   Compiling oid-registry v0.8.1
   Compiling zenoh-util v1.9.0
   Compiling toml v0.9.12+spec-1.1.0
   Compiling tinyvec v1.11.0
   Compiling rand v0.10.3
   Compiling serde_with v3.21.0
   Compiling validated_struct v2.2.0
   Compiling fastbloom v0.17.0
   Compiling block-buffer v0.12.1
   Compiling quinn v0.11.9
   Compiling pem v3.0.6
   Compiling rand_pcg v0.10.2
   Compiling http v1.4.1
   Compiling nonempty-collections v0.3.1
   Compiling secrecy v0.8.0
   Compiling num_cpus v1.17.0
   Compiling lru-slab v0.1.2
   Compiling zenoh-config v1.9.0
   Compiling rustls-webpki v0.103.16
   Compiling digest v0.11.3
   Compiling icu_normalizer v2.2.0
   Compiling rustls-platform-verifier v0.7.1
   Compiling quinn-proto v0.11.19
   Compiling icu_properties v2.2.0
   Compiling der-parser v10.0.0
   Compiling yasna v0.6.0
   Compiling pem-rfc7468 v0.7.0
   Compiling der_derive v0.7.3
   Compiling flagset v0.4.7
   Compiling httparse v1.10.1
   Compiling der v0.7.10
   Compiling rcgen v0.14.8
   Compiling x509-parser v0.18.1
   Compiling idna_adapter v1.2.2
   Compiling form_urlencoded v1.2.2
   Compiling zenoh-codec v1.9.0
   Compiling rustls-pemfile v2.2.0
   Compiling socket2 v0.5.10
   Compiling parking_lot_core v0.9.12
   Compiling unic-langid-impl v0.9.6
   Compiling zenoh-link-commons v1.9.0
   Compiling idna v1.1.0
   Compiling spki v0.7.3
   Compiling sha2 v0.10.9
   Compiling hmac v0.12.1
   Compiling crc32fast v1.5.0
   Compiling url v2.5.8
   Compiling unic-langid v0.9.6
   Compiling adler2 v2.0.1
   Compiling heck v0.5.0
   Compiling simd-adler32 v0.3.9
   Compiling miniz_oxide v0.8.9
   Compiling hmac v0.13.0
   Compiling pem-rfc7468 v1.0.0
   Compiling same-file v1.0.6
   Compiling cpubits v0.1.1
   Compiling crypto-bigint v0.7.6
   Compiling walkdir v2.5.0
   Compiling der v0.8.2
   Compiling flate2 v1.1.9
   Compiling pkcs8 v0.10.2
   Compiling tokio-rustls v0.26.4
   Compiling keccak v0.1.6
   Compiling ff v0.14.0
   Compiling arc-swap v1.9.1
   Compiling universal-hash v0.5.1
   Compiling toml_datetime v1.1.1+spec-1.1.0
   Compiling crossbeam-epoch v0.9.20
   Compiling opaque-debug v0.3.1
   Compiling syn v1.0.109
   Compiling toml_edit v0.25.11+spec-1.1.0
   Compiling sha3 v0.10.9
   Compiling rust-embed-utils v8.11.0
   Compiling concurrent-queue v2.5.0
   Compiling aes v0.8.4
   Compiling curve25519-dalek v4.1.3
   Compiling nix v0.29.0
   Compiling sha1 v0.10.6
   Compiling signature v2.2.0
   Compiling utf-8 v0.7.6
   Compiling byteorder v1.5.0
   Compiling parking v2.2.1
   Compiling static_assertions v1.1.0
   Compiling stabby-macros v72.1.1
   Compiling tungstenite v0.24.0
   Compiling event-listener v5.4.1
   Compiling rust-embed-impl v8.11.0
   Compiling proc-macro-crate v3.5.0
   Compiling group v0.14.0
   Compiling spki v0.8.1
   Compiling zenoh-link-quic_datagram v1.9.0
   Compiling http-body v1.0.1
   Compiling stabby-abi v72.1.1
   Compiling rustix v1.1.4
   Compiling num-bigint-dig v0.8.6
   Compiling base16ct v1.0.0
   Compiling foldhash v0.1.5
   Compiling type-map v0.5.1
   Compiling hashbrown v0.15.5
   Compiling sec1 v0.8.1
   Compiling phf_shared v0.13.1
   Compiling pkcs8 v0.11.0
   Compiling crossbeam-deque v0.8.6
   Compiling tokio-tungstenite v0.24.0
   Compiling zenoh-sync v1.9.0
   Compiling tls-listener v0.11.2
   Compiling hkdf v0.13.0
   Compiling crossbeam-queue v0.3.12
   Compiling crossbeam-channel v0.5.15
   Compiling num-iter v0.1.45
   Compiling uuid v1.23.1
   Compiling toml v0.5.11
   Compiling basic-toml v0.1.10
   Compiling aead v0.5.2
   Compiling cpufeatures v0.3.1
   Compiling sha2-const-stable v0.1.0
   Compiling fastrand v2.4.1
   Compiling try-lock v0.2.5
   Compiling stabby v72.1.1
   Compiling signal-hook v0.3.18
   Compiling self_cell v1.2.2
   Compiling utf8parse v0.2.2
   Compiling tower-service v0.3.3
   Compiling linux-raw-sys v0.12.1
   Compiling self_cell v0.10.3
   Compiling anstyle-parse v1.0.0
   Compiling i18n-config v0.4.8
   Compiling want v0.3.1
   Compiling phf_generator v0.13.1
   Compiling sha2 v0.11.1
   Compiling find-crate v0.6.3
   Compiling zenoh-link-unixsock_stream v1.9.0
   Compiling intl-memoizer v0.5.3
   Compiling crossbeam v0.8.4
   Compiling elliptic-curve v0.14.1
   Compiling zenoh-link-tls v1.9.0
   Compiling zenoh-link-udp v1.9.0
   Compiling zenoh-link-ws v1.9.0
   Compiling parking_lot v0.12.5
   Compiling zenoh-link-quic v1.9.0
   Compiling twox-hash v1.6.3
   Compiling intl_pluralrules v7.0.2
   Compiling fluent-langneg v0.13.1
   Compiling primefield v0.14.0
   Compiling pkcs1 v0.7.5
   Compiling fluent-syntax v0.11.1
   Compiling zenoh-link-tcp v1.9.0
   Compiling asn1-rs-derive v0.5.1
   Compiling git-version-macro v0.3.9
   Compiling atomic-waker v1.1.2
   Compiling rustix v0.38.44
   Compiling colorchoice v1.0.5
   Compiling array-init v2.1.0
   Compiling anstyle v1.0.14
   Compiling rustc-hash v1.1.0
   Compiling compression-core v0.4.34
   Compiling anstyle-query v1.1.5
   Compiling unicase v2.9.0
   Compiling is_terminal_polyfill v1.70.2
   Compiling anstream v1.0.0
   Compiling mime_guess v2.0.5
   Compiling compression-codecs v0.4.46
   Compiling fluent-bundle v0.15.3
   Compiling ringbuffer-spsc v0.1.15
   Compiling hyper v1.9.0
   Compiling git-version v0.3.9
   Compiling asn1-rs v0.6.2
   Compiling zenoh-link v1.9.0
   Compiling rsa v0.9.10
   Compiling wnaf v0.14.1
   Compiling lz4_flex v0.10.0
   Compiling i18n-embed-impl v0.8.4
   Compiling phf_macros v0.13.1
   Compiling terminal_size v0.4.4
   Compiling zenoh-crypto v1.9.0
   Compiling polyval v0.6.2
   Compiling rfc6979 v0.6.0
   Compiling hkdf v0.12.4
   Compiling signature v3.0.0
   Compiling zenoh-task v1.9.0
   Compiling zenoh v1.9.0
   Compiling regex v1.12.3
   Compiling itertools v0.14.0
   Compiling sync_wrapper v1.0.2
   Compiling syn v3.0.9
   Compiling clap_lex v1.1.0
   Compiling ipnet v2.12.0
   Compiling oid-registry v0.7.1
   Compiling tower-layer v0.3.3
   Compiling fixedbitset v0.5.7
   Compiling linux-raw-sys v0.4.15
   Compiling instant-xml-macros v0.7.2
   Compiling petgraph v0.8.3
   Compiling tower v0.5.3
   Compiling clap_builder v4.6.0
   Compiling hyper-util v0.1.20
   Compiling prost-derive v0.13.5
   Compiling phf v0.13.1
   Compiling zenoh-transport v1.9.0
   Compiling ecdsa v0.17.0
   Compiling ghash v0.5.1
   Compiling rust-embed v8.11.0
   Compiling signal-hook-mio v0.2.5
   Compiling zenoh-plugin-trait v1.9.0
   Compiling primeorder v0.14.0
   Compiling fluent v0.16.1
   Compiling async-compression v0.4.51
   Compiling x25519-dalek v2.0.1
   Compiling http-body-util v0.1.3
   Compiling poly1305 v0.8.0
   Compiling clap_derive v4.6.1
   Compiling ctr v0.9.2
   Compiling chacha20 v0.9.1
   Compiling toml_datetime v0.6.11
   Compiling serde_spanned v0.6.9
   Compiling kem v0.3.0-pre.0
   Compiling hybrid-array v0.2.3
   Compiling proc-macro-error-attr2 v2.0.0
   Compiling instability v0.3.12
   Compiling iana-time-zone v0.1.65
   Compiling vec_map v0.8.2
   Compiling mime v0.3.17
   Compiling toml_write v0.1.2
   Compiling xmlparser v0.13.6
   Compiling instant-xml v0.7.6
   Compiling toml_edit v0.22.27
   Compiling chrono v0.4.44
   Compiling proc-macro-error2 v2.0.1
   Compiling ml-kem v0.2.3
   Compiling i18n-embed v0.15.4
   Compiling chacha20poly1305 v0.10.1
   Compiling aes-gcm v0.10.3
   Compiling clap v4.6.1
   Compiling tower-http v0.6.11
   Compiling p256 v0.14.0
   Compiling crossterm v0.28.1
   Compiling prost v0.13.5
   Compiling hyper-rustls v0.27.9
   Compiling locale_config v0.3.0
   Compiling der-parser v9.0.0
   Compiling ed25519 v2.2.3
   Compiling strum_macros v0.26.4
   Compiling pbkdf2 v0.12.2
   Compiling serde_urlencoded v0.7.1
   Compiling md-5 v0.11.0
   Compiling salsa20 v0.10.2
   Compiling webpki-roots v0.26.11
   Compiling cookie-factory v0.3.3
   Compiling itertools v0.13.0
   Compiling half v2.7.1
   Compiling castaway v0.2.4
   Compiling ordered-float v2.10.1
   Compiling bincode v1.3.3
   Compiling secrecy v0.10.3
   Compiling pin-project-internal v1.1.13
   Compiling jiff v0.2.27
   Compiling unicode-width v0.1.14
   Compiling hex v0.4.3
   Compiling base64 v0.21.7
   Compiling leb128 v0.2.6
   Compiling indoc v2.0.7
   Compiling io_tee v0.1.1
   Compiling ciborium-io v0.2.2
   Compiling base64 v0.23.1
   Compiling unicode-segmentation v1.13.2
   Compiling unicode-truncate v1.1.0
   Compiling rusty-s3 v0.10.2
   Compiling ciborium-ll v0.2.2
   Compiling age-core v0.11.0
   Compiling zenoh-ext v1.9.0
   Compiling grant-crypto v0.1.0 (/src/ops/grant-crypto/sdk/core)
   Compiling pin-project v1.1.13
   Compiling serde-value v0.7.0
   Compiling compact_str v0.8.2
   Compiling ureq v2.12.1
   Compiling scrypt v0.11.0
   Compiling reqwest v0.12.28
   Compiling strum v0.26.3
   Compiling ed25519-dalek v2.2.0
   Compiling x509-parser v0.16.0
   Compiling prost-types v0.13.5
   Compiling i18n-embed-fl v0.9.4
   Compiling toml v0.8.23
   Compiling lru v0.12.5
   Compiling x509-cert v0.2.5
   Compiling quick-xml v0.42.0
   Compiling bech32 v0.9.1
   Compiling unicode-width v0.2.0
   Compiling cassowary v0.3.0
   Compiling ratatui v0.29.0
   Compiling age v0.11.3
   Compiling panoscope-core v0.1.0 (/src/crates/panoscope-core)
   Compiling grant-keyd v0.1.0 (/src/ops/grant-crypto/keyd)
   Compiling goat-federation v0.5.18 (/src/crates/goat-federation)
   Compiling prost-reflect v0.14.7
   Compiling ciborium v0.2.2
   Compiling goat-fun v0.1.0 (/src/crates/goat-fun)
   Compiling clap_complete v4.6.5
   Compiling goat-errors v0.1.0 (/src/crates/goat-errors)
   Compiling goat-selfupdate v0.1.0 (/src/crates/goat-selfupdate)
   Compiling goat-cli v0.5.19 (/src/crates/goat-cli)
    Finished `release` profile [optimized] target(s) in 4m 35s
%   aidev-1% %   aidev-1% %   aidev-1% goat 0.5.19
%   aidev-1% === build end 2026-11-12T01:36:27Z 1794447387
%   aidev-1% === block 10b 01:36:27
%   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% %   aidev-1% === block 10c 01:36:27
%   aidev-1% %   aidev-1%  Container apex-goat1-zenohd-fabric-1 Recreate 
 Container apex-goat1-zenohd-fabric-1 Recreated 
 Container apex-goat1-zenohd-fabric-1 Starting 
 Container apex-goat1-zenohd-fabric-1 Started 
%   aidev-1% %   aidev-1% listening on `18214b1a34e3c722d1cac283b272a62c/**` via tls/router.fabric.h1:7447 — stopping after 1 event(s). Ctrl-C to stop.
18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001 hex:0a0c08bab0d4d70610b8d0bd8603122466303030303030312d303030302d343030302d383030302d3030303030303030303030313aec010a1a30314d37365044394532345046534539514e354a3059565a524e121a30314d37364e5941564747333751413035453257574d4b325033323a09b4a6b9002c25fdbf11df29fcf18c964940190000000000005e402163b85e7059cd223f29b88b20c13e93173f310000000000002440380140013d6666663f5a410a0b4169722056656869636c65156666663f1a2d0a0f55415620526f746172792057696e6715cdcc4c3f180122130a0a436f6d6d65726369616c159a99193f18029a012d09420604e3d01ceebf11bf176b7414ed27c019000000000000000021000000000000f03f29000000000000f03f
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
%   aidev-1% %   aidev-1% === end 2026-11-12T01:37:12Z
%   aidev-1%  Container apex-goat1-vehicle-1 Stopping 
 Container apex-goat1-host-recorder-1 Stopping 
 Container apex-goat1-radar-1 Stopping 
 Container apex-goat1-recorder-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopping 
 Container apex-goat1-fusion-node-1 Stopping 
 Container apex-goat1-camera-1 Stopping 
 Container apex-goat1-pod-bridge-1 Stopping 
 Container apex-goat1-vehicle-1 Stopped 
 Container apex-goat1-vehicle-1 Removing 
 Container apex-goat1-vehicle-1 Removed 
 Container apex-goat1-bridge-node-1 Stopping 
 Container apex-goat1-host-fusion-1 Stopped 
 Container apex-goat1-host-fusion-1 Removing 
 Container apex-goat1-host-fusion-1 Removed 
 Container apex-goat1-host-recorder-1 Stopped 
 Container apex-goat1-host-recorder-1 Removing 
 Container apex-goat1-host-recorder-1 Removed 
 Container apex-goat1-fusion-node-1 Stopped 
 Container apex-goat1-fusion-node-1 Removing 
 Container apex-goat1-fusion-node-1 Removed 
 Container apex-goat1-camera-1 Stopped 
 Container apex-goat1-camera-1 Removing 
 Container apex-goat1-camera-1 Removed 
 Container apex-goat1-recorder-1 Stopped 
 Container apex-goat1-recorder-1 Removing 
 Container apex-goat1-recorder-1 Removed 
 Container apex-goat1-pod-bridge-1 Stopped 
 Container apex-goat1-pod-bridge-1 Removing 
 Container apex-goat1-pod-bridge-1 Removed 
 Container apex-goat1-zenohd-fabric-1 Stopping 
 Container apex-goat1-radar-1 Stopped 
 Container apex-goat1-radar-1 Removing 
 Container apex-goat1-radar-1 Removed 
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
 Network apex-goat1_mesh Removing 
 Network apex-goat1_host Removing 
 Network apex-goat1_pod1 Removing 
 Network apex-goat1_host Removed 
 Network apex-goat1_mesh Removed 
 Network apex-goat1_pod1 Removed 
%   aidev-1% 