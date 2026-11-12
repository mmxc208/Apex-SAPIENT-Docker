# Final run, the checks outside README section "Goat step 1": G1-08 (unit tests), G1-11 (stage 4 steps 1 and 2), G1-01 (pairing probe).
cd <workspace>/Apex-SAPIENT-Docker
. <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/docker-env.sh
set -x
git rev-parse --short HEAD
docker compose -f docker-compose.yml -f docker-compose.emulators.yml run --rm --no-deps radar python -m pytest -p no:cacheprovider -v -W error tests/test_pod_bridge.py -k "stale or 4_s_old or age_limit" < /dev/null 2>&1 | grep -E 'PASSED|FAILED|passed|failed'
dc() { docker compose -f docker-compose.pod1.yml "$@"; }
zenoh/pki/make_certs.sh zenoh/pki/out
dc up -d
sleep 3
dc logs zenohd | grep -ci error
sleep 27
dc logs radar | grep -c registration_ack
dc logs fusion-node | grep -c "<- registration "
dc logs vehicle | grep registration_ack | head -1
dc logs bridge-node | grep registered
dc down
dcp() { docker compose -f docker-compose.pairing.yml "$@"; }
dcp up -d zenohd && sleep 3
docker compose -f docker-compose.pairing.yml exec -T zenohd zenohd --version < /dev/null
dcp run --rm probe < /dev/null
echo "exit $?"
PROBE_WAIT_RESTART=1 dcp run -d --name pairing-probe probe < /dev/null
sleep 5 && dcp restart zenohd && sleep 20
docker logs pairing-probe 2>&1 | tail -4
docker wait pairing-probe
docker rm -f pairing-probe; dcp down
