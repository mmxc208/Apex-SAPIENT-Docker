. <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/dg.sh
W=<workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host
set -x
date -u +%T
dg ps --format '{{.Service}} {{.State}}' | sort
ls zenoh/goat1/pki/pod1/
before=$(docker inspect -f '{{.State.StartedAt}}' apex-goat1-zenohd-pod-1)
echo "$before"
shasum -a 256 zenoh/goat1/router-pod1.json5 zenoh/goat1/router-fabric.json5
python3 -c 'import pathlib; p = pathlib.Path("goat1/registry.toml"); p.write_text(p.read_text().replace("[pod1.slots]\n", "[pod1.slots]\nradar2 = 3\n", 1))'
grep -A4 '^\[pod1.slots\]' goat1/registry.toml
git diff goat1/registry.toml
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1 --frozen-routers
echo "exit $?"
shasum -a 256 zenoh/goat1/router-pod1.json5 zenoh/goat1/router-fabric.json5
ls zenoh/goat1/pki/pod1/
grep RADAR2 zenoh/goat1/goat1.env
source zenoh/goat1/goat1.env
date -u +%T
dg --profile join up -d radar2
sleep 30
date -u +%T
dg logs radar2
dg logs fusion-node | grep "<- registration " | grep -c "Fake second radar"
r2=$(echo "$POD1_RADAR2_ID" | cut -c1-8)
dg logs fusion-node | grep -F "$r2"
dg logs fusion-node | grep -F "<- detection_report $r2" | wc -l
docker inspect -f '{{.State.StartedAt}}' apex-goat1-zenohd-pod-1
test "$before" = "$(docker inspect -f '{{.State.StartedAt}}' apex-goat1-zenohd-pod-1)" && echo "router not restarted"
dg logs --since "$before" zenohd-pod | grep -ci -E 'error|panic'
dg logs zenohd-pod
dg logs host-fusion | grep "<- registration "
dg logs --no-color --timestamps > $W/task-10-g1-09-logs.txt
dg --profile join logs --no-color --timestamps radar2 >> $W/task-10-g1-09-logs.txt
date -u +%T
dg --profile join rm -s -f radar2
git restore goat1/registry.toml
git status --short goat1/registry.toml
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1 --frozen-routers
echo "exit $?"
shasum -a 256 zenoh/goat1/router-pod1.json5 zenoh/goat1/router-fabric.json5
ls zenoh/goat1/pki/pod1/
grep -c RADAR2 zenoh/goat1/goat1.env
dg --profile join ps -a --format '{{.Service}} {{.State}}' | sort
