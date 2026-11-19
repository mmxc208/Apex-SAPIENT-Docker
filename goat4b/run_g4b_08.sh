#!/bin/zsh -f
# G4B-08, the host's link cut (task 4 step 4). Run from the repo root: zsh -f goat4b/run_g4b_08.sh
# In goathost the live route to 192.168.64.4/32 is replaced by a blackhole for 30 s, then the line
# read before is put back (the netplan file 90-cuaslab-route.yaml is not touched by either). The
# trap restores it on EXIT, INT and TERM and prints the state.
# Pass (spec 6.4): a detection line at the host within 60 s of the restore, StartedAt unchanged.
# On a fail: the logs are saved, the check is marked failed, the two host services are restarted
# and the lines of G4B-03 are read again. No program is changed.
cd "${0:A:h}/.." || exit 1
. goat4b/run_lib.sh

route_line() { limactl shell goathost ip route show 192.168.64.4/32 < /dev/null | head -n 1 | tr -s ' ' | sed 's/ *$//'; }
ROUTE=$(route_line)
case "$ROUTE" in
  "192.168.64.4 via 192.168.64.1 "*) ;;
  *) echo "refused: the route in goathost to 192.168.64.4 is '$ROUTE', not the normal one; restore it first" >&2; exit 1 ;;
esac
TMPD=$(mktemp -d /tmp/g4b08.XXXXXX)

cut_on=0 done_cleanup=0
restore_route() {
  echo "\$ limactl shell goathost sudo ip route replace $ROUTE"
  limactl shell goathost sudo ip route replace ${=ROUTE} < /dev/null
  echo "route in goathost now: $(route_line)"
}
cleanup() {
  [ "$done_cleanup" = 1 ] && return
  done_cleanup=1
  echo "## trap ($1) at $(utc)"
  if [ "$cut_on" = 1 ] || [ "$(route_line)" != "$ROUTE" ]; then restore_route; else echo "route in goathost unchanged: $(route_line)"; fi
  echo "\$ g4b_routes_check"; g4b_routes_check; echo "g4b_routes_check exit $?"
  echo "\$ g4b_state"; g4b_state
  echo "(end of trap)"
}
trap 'cleanup EXIT' EXIT
trap 'cleanup INT; exit 130' INT
trap 'cleanup TERM; exit 143' TERM

header
echo "# G4B-08 (task 4 step 4): the route in goathost to 192.168.64.4 replaced by a blackhole for 30 s."
echo "# Script goat4b/run_g4b_08.sh (this commit). Times are UTC; goathost's clock is disciplined (offset in g4b_state)."
echo "# host-fusion logs every 10th detection report of each node; the host recorder's records give the first one exactly."
echo "## before"
echo "\$ g4b_state"; g4b_state
echo "route in goathost before (restored exactly): $ROUTE"
echo "\$ host containers' StartedAt"; hostdocker inspect -f '{{.Name}} {{.State.StartedAt}}' "${G4B_HOST_CONTAINERS[@]}" | tee "$TMPD/started-before.txt"
pause 20
t_cut=$(utc_in 0)
echo
echo "## cut at $t_cut"
echo "\$ limactl shell goathost sudo ip route replace blackhole 192.168.64.4/32"
cut_on=1
limactl shell goathost sudo ip route replace blackhole 192.168.64.4/32 < /dev/null
echo "route in goathost now: $(route_line)"
pause 30
restore_route; cut_on=0
t_back=$(utc_in 0)
echo "## restored at $t_back"

# the first detection line at the host after the restore, polled for up to 90 s
first_log='' first_rec=''
for ((s = 0; s <= 90; s += 3)); do
  [ -z "$first_log" ] && first_log=$(hostdocker logs --since "$t_back" apex-goat4b-host-fusion-1 2>&1 | grep -m 1 '<- detection_report')
  [ -z "$first_rec" ] && first_rec=$(hostrec | python3 -c '
import json, sys
since, pod = sys.argv[1], sys.argv[2]
sys.path.insert(0, "goat4b"); import readers
t0 = readers.parse_time(since)
for r in map(json.loads, sys.stdin):
    if r.get("anchor") == pod and r.get("kind") == "detection_report" and readers.parse_time(r["t"]) >= t0:
        print(r["t"]); break' "$t_back" "$FABRIC_POD1_ID")
  [ -n "$first_log" ] && [ -n "$first_rec" ] && break
  pause 3
done
pause 20
t_end=$(utc_in 0)
echo
echo "## the host services' logs from 10 s before the cut to $t_end"
for c in "${G4B_HOST_CONTAINERS[@]}"; do
  echo "\$ docker logs --since $(utc_add "$t_cut" -10) $c | grep -v 'detection_report\\|status_report\\|-> task\\|<- task_ack\\|auto-task'   (routine lines left out; counted below)"
  hostdocker logs --since "$(utc_add "$t_cut" -10)" "$c" > "$TMPD/$c.log" 2>&1
  grep -v -e 'detection_report' -e 'status_report' -e '-> task' -e '<- task_ack' -e 'auto-task' "$TMPD/$c.log" | cut -c1-220
done
echo "\$ host-fusion '<- detection_report' lines, by 10 s bucket of the log time (cut $t_cut, restore $t_back)"
grep '<- detection_report' "$TMPD/apex-goat4b-host-fusion-1.log" | awk '{print substr($1,1,7) "0"}' | uniq -c
echo "\$ host recorder: records of the pod's anchor, by 5 s bucket of t"
hostrec | python3 -c '
import collections, json, sys
sys.path.insert(0, "goat4b"); import readers
t0, t1, pod = readers.parse_time(sys.argv[1]), readers.parse_time(sys.argv[2]), sys.argv[3]
c = collections.Counter()
for r in map(json.loads, sys.stdin):
    if r.get("anchor") != pod: continue
    t = readers.parse_time(r["t"])
    if t0 <= t <= t1:
        s = int((t - t0).total_seconds()) // 5 * 5
        c[s] += 1
for s in range(0, int((t1 - t0).total_seconds()) + 1, 5):
    print("  t0+%3d s: %d" % (s, c[s]))' "$(utc_add "$t_cut" -10)" "$t_end" "$FABRIC_POD1_ID"
echo "  (t0 = 10 s before the cut: cut at t0+10, restore at t0+$(python3 -c 'import sys,datetime as d; f=lambda x: d.datetime.fromisoformat(x.replace("Z","+00:00")); print(round((f(sys.argv[2])-f(sys.argv[1])).total_seconds()))' "$(utc_add "$t_cut" -10)" "$t_back"))"

echo
echo "## result"
echo "first '<- detection_report' log line at the host after the restore: ${first_log:-none within 90 s}"
echo "first detection_report record of the pod's anchor at the host recorder after the restore: ${first_rec:-none within 90 s}"
secs=''
[ -n "$first_rec" ] && secs=$(python3 -c 'import sys; sys.path.insert(0, "goat4b"); import readers; print("%.1f" % (readers.parse_time(sys.argv[1]) - readers.parse_time(sys.argv[2])).total_seconds())' "$first_rec" "$t_back")
echo "seconds from the restore to the first detection record: ${secs:-none}"
lsecs=''
if [ -n "$first_log" ]; then
  lt=$(printf '%s\n' "$first_log" | grep -o '[0-9][0-9]:[0-9][0-9]:[0-9][0-9]' | head -n 1)
  lsecs=$(python3 -c 'import sys; h,m,s=map(int,sys.argv[1].split(":")); b=sys.argv[2][11:19].split(":"); print(h*3600+m*60+s-(int(b[0])*3600+int(b[1])*60+int(b[2])))' "$lt" "$t_back")
fi
echo "seconds from the restore to the first detection log line (log time in whole seconds): ${lsecs:-none}"
echo "\$ host containers' StartedAt after"
hostdocker inspect -f '{{.Name}} {{.State.StartedAt}}' "${G4B_HOST_CONTAINERS[@]}" | tee "$TMPD/started-after.txt"
same=no; cmp -s "$TMPD/started-before.txt" "$TMPD/started-after.txt" && same=yes
echo "StartedAt unchanged: $same"
if [ -n "$lsecs" ] && [ "$lsecs" -le 60 ] && [ "$same" = yes ]; then
  echo "G4B-08: PASS (a detection line within 60 s of the restore, no restart)"
else
  echo "G4B-08: FAIL (detection line after ${lsecs:-none} s; StartedAt unchanged: $same)"
  echo
  echo "## after the fail: the two host services restarted, then the lines of G4B-03"
  echo "\$ dg4b_host restart host-fusion host-recorder"
  t_rs=$(utc); dg4b_host restart host-fusion host-recorder 2>&1
  pause 45
  echo "\$ dg4b_host logs --since $t_rs host-fusion | grep -c '<- detection_report'"
  dg4b_host logs --since "$t_rs" host-fusion | grep -c '<- detection_report'
  echo "\$ dg4b_host logs --since $t_rs host-fusion | grep -E '<- alert|<- registration '"
  dg4b_host logs --since "$t_rs" host-fusion | grep -E '<- alert|<- registration '
fi
echo "(end of run)"
