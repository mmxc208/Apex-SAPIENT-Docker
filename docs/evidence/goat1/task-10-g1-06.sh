. <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/dg.sh
W=<workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host
set -x
git rev-parse --short HEAD
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1
dg up -d
sleep 60
date -u +%T
dg ps --format '{{.Service}} {{.State}}' | sort
dg logs pod-bridge
date -u +%T; docker network disconnect apex-goat1_mesh apex-goat1-pod-bridge-1; date -u +%T
sleep 30
date -u +%T
dg logs --since 30s radar camera vehicle fusion-node | grep -c -E 'lost|cannot reach'
dg logs --since 30s fusion-node | grep -c '<- detection_report'
dg logs --since 30s fusion-node | grep '<- detection_report' | head -3
dg logs --since 40s pod-bridge
date -u +%T; docker network connect apex-goat1_mesh apex-goat1-pod-bridge-1; date -u +%T
sleep 30
date -u +%T
dg logs --since 25s host-fusion | grep -c "<- detection_report"
dg logs --since 60s host-fusion | grep -c "<- registration "
dg logs --since 70s pod-bridge
sleep 35
dg logs pod-bridge
dg logs --no-color --timestamps > $W/task-10-g1-06-logs.txt
