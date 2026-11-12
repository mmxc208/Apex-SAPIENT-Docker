. <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/dg.sh
W=<workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host
set -x
dg down
HOST_HOLD_SECONDS=20 dg up -d
sleep 60
date -u +%T
dg ps --format '{{.Service}} {{.State}}' | sort
dg exec -T host-fusion printenv NODE_HOLD_SECONDS < /dev/null
date -u +%T; docker network disconnect apex-goat1_mesh apex-goat1-pod-bridge-1; date -u +%T
sleep 40
date -u +%T; docker network connect apex-goat1_mesh apex-goat1-pod-bridge-1; date -u +%T
sleep 40
date -u +%T
dg logs host-fusion | grep -E 'removed|request "Registration"|<- registration '
dg logs fusion-node | grep -E 'request "Registration"|registration_ack f0000002'
dg logs pod-bridge
dg logs --no-color --timestamps > $W/task-10-g1-07-logs.txt
