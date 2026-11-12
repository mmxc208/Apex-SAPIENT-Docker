# Runs one G1-05 case: a subscriber with an allowed certificate, a put with the chosen one, then
# the router's trace lines for the key. Usage: case <router service> <sub service> <put service> <key> [put env...]
. <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/dg.sh
set -a; . zenoh/goat1/goat1.env; set +a
trace() { dg logs --no-color --no-log-prefix --since "$1" "$2" | sed 's/\x1b\[[0-9;]*m//g' | grep -F "$3" | grep -E 'authorized to (Put|DeclareSubscriber)' | sed -E 's/^([^ ]+) .*access_control: [0-9a-f]{32} on [^ ]*CertCommonName\(([^)]*)\)[^ ]*/\1 CN=\2/; s/^([^ ]+) .*access_control: /\1 /' ; }
case_run() {
  router=$1; subsvc=$2; putsvc=$3; key=$4; shift 4
  since=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "\$ dg run --rm --no-deps -T $subsvc python probe_access.py sub $key 15   (in the background)"
  dg run --rm --no-deps -T $subsvc python probe_access.py sub "$key" 15 2>&1 | grep -v ' INFO \|probe-access' &
  sleep 5
  echo "\$ dg run --rm --no-deps -T $* $putsvc python probe_access.py put $key"
  dg run --rm --no-deps -T "$@" $putsvc python probe_access.py put "$key" 2>&1 | grep -v 'probe-access'
  wait
  sleep 2
  echo "\$ router $router trace for the key since $since (put and subscriber decisions):"
  trace "$since" "$router" "$key" | grep -v 'Put (egress)' | head -12
  echo "  (egress lines omitted; count of Put (egress) lines for the key: $(trace "$since" "$router" "$key" | grep -c 'Put (egress)'))"
}
