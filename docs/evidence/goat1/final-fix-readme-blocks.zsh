cd <workspace>/Apex-SAPIENT-Docker
. <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/docker-env.sh
echo "=== start $(date -u +%FT%TZ)"
echo "=== block helper $(date -u +%T)"
dg() { docker compose --env-file zenoh/goat1/goat1.env -f docker-compose.goat1.yml "$@"; }
probe() { local service=$1; shift; dg run --rm --no-deps -T "$service" python probe_access.py "$@" < /dev/null; }
podfabric() { dg run --rm --no-deps -T -e ZENOH_CONNECT=tls/router.fabric.h1:7447 -e ZENOH_TLS_CA=/certs/fabric/ca.pem -e ZENOH_TLS_CERT=/certs/fabric/pod1.pem -e ZENOH_TLS_KEY=/certs/fabric/pod1.key pod-bridge python probe_access.py "$@" < /dev/null; }
echo "=== block 1 $(date -u +%T)"
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1
source zenoh/goat1/goat1.env
dg up -d
sleep 45
dg ps --format '{{.Service}} {{.State}}' | sort
dg logs zenohd-pod zenohd-fabric | grep -ci -E 'error|panic'
echo "=== block 2 $(date -u +%T)"
dg logs fusion-node | grep registration_ack
dg logs host-fusion | grep "<- registration "
echo "=== block 3 $(date -u +%T)"
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
echo "=== block 4 $(date -u +%T)"
dg logs radar camera | grep "<- task .* look_at" | cut -c1-90
dg logs host-fusion | grep "<- task_ack" | grep TASK_STATUS_ACCEPTED
dg logs --no-color --timestamps > <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/final-fix-logs-1-4.txt
echo "=== block 5 $(date -u +%T)"
ZENOHD_RUST_LOG=zenoh::net::routing::interceptor=trace dg up -d zenohd-pod zenohd-fabric
sleep 20
dg logs --since 30s pod-bridge
echo "=== block 5.1 $(date -u +%T)"
K="$FABRIC_HOST_FUSION_ID/task/p1/sapient/v2/task/$POD1_FUSION_NODE_ID"
T=$(date +%s)
probe host-recorder sub "$K" 15 &
sleep 5
podfabric put "$K"
wait
dg logs --since "$T" zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_POD1_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs --since "$T" zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_POD1_ID)" | grep -c "is authorized to Put (ingress)"
echo "=== block 5.2 $(date -u +%T)"
K="$FABRIC_POD1_ID/telemetry/sapient/p1/v2/alert/$POD1_FUSION_NODE_ID"
T=$(date +%s)
probe host-recorder sub "$K" 15 &
sleep 5
probe host-fusion put "$K"
wait
dg logs --since "$T" zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_HOST_FUSION_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs --since "$T" zenohd-fabric | grep -F "$K" | grep -F "CertCommonName($FABRIC_HOST_FUSION_ID)" | grep -c "is authorized to Put (ingress)"
echo "=== block 5.3 $(date -u +%T)"
T=$(date +%s)
probe host-recorder sub "**" 15
probe host-recorder sub "*/telemetry/sapient/*/v2/*/*" 15
dg logs --since "$T" zenohd-fabric | grep -F "CertCommonName($FABRIC_HOST_RECORDER_ID)" | grep -F "Declare Subscriber (ingress) on **" | grep -c unauthorized
echo "=== block 5.4 $(date -u +%T)"
K="h1/p1/sapient/v2/$POD1_CAMERA_ID/up/status_report"
T=$(date +%s)
probe recorder sub "$K" 15 &
sleep 5
probe radar put "$K"
wait
dg logs --since "$T" zenohd-pod | grep -F "$K" | grep -F "CertCommonName($POD1_RADAR_ID)" | grep -c "is unauthorized to Put (ingress)"
dg logs --since "$T" zenohd-pod | grep -F "$K" | grep -F "CertCommonName($POD1_RADAR_ID)" | grep -c "is authorized to Put (ingress)"
dg logs --no-color --timestamps > <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/final-fix-logs-5.txt
echo "=== block 5.5 $(date -u +%T)"
dg up -d zenohd-pod zenohd-fabric
echo "=== block 6 $(date -u +%T)"
dg restart host-fusion
sleep 40
dg logs --since 40s fusion-node | grep -E 'request "Registration"|registration_ack'
echo "=== block 7 $(date -u +%T)"
docker network disconnect apex-goat1_mesh apex-goat1-pod-bridge-1
sleep 30
dg logs --since 30s radar camera vehicle fusion-node | grep -c -E 'lost|cannot reach'
dg logs --since 30s fusion-node | grep -c "<- detection_report"
docker network connect apex-goat1_mesh apex-goat1-pod-bridge-1
sleep 30
dg logs --since 25s host-fusion | grep -c "<- detection_report"
dg logs --since 60s host-fusion | grep -c "<- registration "
dg logs --since 70s pod-bridge
dg logs --no-color --timestamps > <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/final-fix-logs-6-7.txt
echo "=== block 8 $(date -u +%T)"
dg down
HOST_HOLD_SECONDS=20 dg up -d
sleep 60
docker network disconnect apex-goat1_mesh apex-goat1-pod-bridge-1
sleep 40
docker network connect apex-goat1_mesh apex-goat1-pod-bridge-1
sleep 40
dg logs host-fusion | grep -E 'removed|request "Registration"|<- registration '
dg logs fusion-node | grep "<- registration_ack f0000002"
echo "=== block 9 $(date -u +%T)"
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
echo "=== block 9.1 $(date -u +%T)"
dg --profile join rm -s -f radar2
git restore goat1/registry.toml
unset POD1_RADAR2_ID
python3 emulators/goatgen.py goat1/registry.toml zenoh/goat1 --frozen-routers
echo "exit $?"
git status --short goat1/registry.toml
echo "=== build start $(date -u +%FT%TZ) $(date +%s)"
echo "=== block 10a $(date -u +%T)"
docker run --rm -v "$PWD/../usareur-af/goatcore:/src:ro" -v apex-goat1-cargo-target:/target -e CARGO_TARGET_DIR=/target -e CARGO_HOME=/target/cargo-home rust:1.95.0-bookworm cargo build --release --locked -j 2 --manifest-path /src/crates/Cargo.toml -p goat-cli < /dev/null
mkdir -p zenoh/goat1/bin
docker run --rm -v apex-goat1-cargo-target:/target:ro -v "$PWD/zenoh/goat1/bin:/out" debian:bookworm-slim cp /target/release/goat /out/goat < /dev/null
docker run --rm -v "$PWD/zenoh/goat1/bin/goat:/usr/local/bin/goat:ro" debian:bookworm-slim goat --version < /dev/null
echo "=== build end $(date -u +%FT%TZ) $(date +%s)"
echo "=== block 10b $(date -u +%T)"
mkdir -p zenoh/goat1/goat-profile/contexts/goat1
printf 'current_context = "goat1"\n' > zenoh/goat1/goat-profile/config.toml
printf 'router_endpoint = "tls/router.fabric.h1:7447"\ndevice_id = "goat-cli"\n' > zenoh/goat1/goat-profile/contexts/goat1/profile.toml
goat() { docker run --rm --network apex-goat1_host -e GOAT_PROFILE_DIR=/goat-profile -v "$PWD/zenoh/goat1/bin/goat:/usr/local/bin/goat:ro" -v "$PWD/zenoh/goat1/goat-profile/config.toml:/goat-profile/config.toml:ro" -v "$PWD/zenoh/goat1/goat-profile/contexts/goat1/profile.toml:/goat-profile/contexts/goat1/profile.toml:ro" -v "$PWD/zenoh/goat1/pki/fabric/goat-cli.pem:/goat-profile/contexts/goat1/mtls.cert.pem:ro" -v "$PWD/zenoh/goat1/pki/fabric/goat-cli.key:/goat-profile/contexts/goat1/mtls.key.pem:ro" -v "$PWD/zenoh/goat1/pki/fabric/ca.pem:/goat-profile/contexts/goat1/ca-roots.pem:ro" debian:bookworm-slim goat "$@" < /dev/null; }
echo "=== block 10c $(date -u +%T)"
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
dg logs --no-color --timestamps zenohd-fabric > <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/final-fix-fabric-trace-10.txt
dg up -d zenohd-fabric
dg logs --no-color --timestamps > <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/final-fix-logs-8-10.txt
echo "=== end $(date -u +%FT%TZ)"
dg down
