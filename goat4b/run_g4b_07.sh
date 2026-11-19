#!/bin/zsh -f
# G4B-07, the pod's link cut (task 4 steps 2 and 3). Run from the repo root:
#   zsh -f goat4b/run_g4b_07.sh short    # 30 s blackhole, host hold time as it is (default 120 s)
#   zsh -f goat4b/run_g4b_07.sh long     # host services again with HOST_HOLD_SECONDS=20, 40 s blackhole,
#                                         # then back with the default hold time
# In Colima only the route to 192.168.64.4/32 is touched: it is read first and that exact line is put
# back. The trap restores it on EXIT, INT and TERM (and, for long, the default hold time) and prints
# the state.
cd "${0:A:h}/.." || exit 1
. goat4b/run_lib.sh

MODE=${1:-}
case "$MODE" in short) CUT=30 ;; long) CUT=40 ;; *) echo "usage: $0 short|long" >&2; exit 2 ;; esac

ROUTE=$(colima ssh -- ip route show 192.168.64.4/32 < /dev/null | head -n 1 | tr -s ' ' | sed 's/ *$//')
case "$ROUTE" in
  "192.168.64.4 via 192.168.64.1 "*) ;;
  *) echo "refused: the route from Colima to 192.168.64.4 is '$ROUTE', not the normal one; restore it first:" >&2
     echo "  colima ssh -- sudo ip route replace 192.168.64.4/32 via 192.168.64.1 dev col0" >&2; exit 1 ;;
esac

route_line() { colima ssh -- ip route show 192.168.64.4/32 < /dev/null | head -n 1; }
cut_on=0 hold_changed=0 done_cleanup=0
restore_route() {
  echo "\$ colima ssh -- sudo ip route replace $ROUTE"
  colima ssh -- sudo ip route replace ${=ROUTE} < /dev/null
  echo "route in Colima now: $(route_line)"
}
default_hold() {
  echo "\$ dg4b_host down; dg4b_host up -d host-fusion host-recorder   (HOST_HOLD_SECONDS unset)"
  dg4b_host down ; ( unset HOST_HOLD_SECONDS; dg4b_host up -d host-fusion host-recorder )
  echo "\$ dg4b_host exec -T host-fusion env | grep HOLD"
  dg4b_host exec -T host-fusion env < /dev/null | grep HOLD
}
cleanup() {
  [ "$done_cleanup" = 1 ] && return
  done_cleanup=1
  echo "## trap ($1) at $(utc)"
  if [ "$cut_on" = 1 ] || [ "$(route_line | tr -s ' ' | sed 's/ *$//')" != "$ROUTE" ]; then restore_route; else echo "route in Colima unchanged: $(route_line)"; fi
  [ "$hold_changed" = 1 ] && default_hold
  echo "\$ g4b_state"; g4b_state
  echo "(end of trap)"
}
trap 'cleanup EXIT' EXIT
trap 'cleanup INT; exit 130' INT
trap 'cleanup TERM; exit 143' TERM

# wait_for <seconds> <command...>: polls every 2 s; prints the seconds it took or "timeout".
wait_for() {
  local n=$1 s; shift
  for ((s = 0; s <= n; s += 2)); do
    if eval "$*" >/dev/null 2>&1; then echo "$s s"; return 0; fi
    pause 2
  done
  echo "timeout after $n s"; return 1
}

header
echo "# G4B-07 $MODE (task 4): the route from Colima to 192.168.64.4 replaced by a blackhole for $CUT s."
echo "# Script goat4b/run_g4b_07.sh (this commit). Times are UTC (Mac); docker log windows by --since (engine clocks, disciplined)."
echo "## before"
echo "\$ g4b_state"; g4b_state
echo "route in Colima before (restored exactly): $ROUTE"
echo "\$ containers' StartedAt"; started_at

if [ "$MODE" = long ]; then
  echo
  echo "## the host services again with HOST_HOLD_SECONDS=20"
  # the flag first: an interrupt during or right after the down still brings the services back
  hold_changed=1
  echo "\$ dg4b_host down"; dg4b_host down
  echo "\$ goat4b_ready"; goat4b_ready; echo "goat4b_ready exit $?"
  echo "\$ HOST_HOLD_SECONDS=20 dg4b_host up -d host-fusion host-recorder"
  HOST_HOLD_SECONDS=20 dg4b_host up -d host-fusion host-recorder
  t_up=$(utc); echo "$t_up"
  echo "\$ dg4b_host exec -T host-fusion env | grep HOLD"
  dg4b_host exec -T host-fusion env < /dev/null | grep HOLD
  echo "waiting for the pod fusion node's registration at the host: $(wait_for 90 "dg4b_host logs host-fusion | grep -q '<- registration f0000001'")"
  dg4b_host logs host-fusion | grep '<- registration f0000001'
fi

echo
echo "## wait 60 s before the cut (as the README of step 4 does)"
pause 60
t_cut=$(utc)
echo "$t_cut"
echo "\$ colima ssh -- sudo ip route replace blackhole 192.168.64.4/32"
cut_on=1
colima ssh -- sudo ip route replace blackhole 192.168.64.4/32 < /dev/null
echo "route in Colima now: $(route_line)"
pause "$CUT"
if [ "$MODE" = short ]; then
  echo "\$ dg4b_pod logs --since $t_cut radar camera vehicle fusion-node | grep -c -E 'lost|cannot reach'  (expect 0)"
  dg4b_pod logs --since "$t_cut" radar camera vehicle fusion-node | grep -c -E 'lost|cannot reach'
  echo "\$ dg4b_pod logs --since $t_cut fusion-node | grep '<- detection_report'  (during the cut; every 10th per node is logged)"
  dg4b_pod logs --since "$t_cut" fusion-node | grep '<- detection_report' | cut -c1-90
  echo "count: $(dg4b_pod logs --since "$t_cut" fusion-node | grep -c '<- detection_report')"
fi
restore_route; cut_on=0
t_back=$(utc); echo "$t_back"

if [ "$MODE" = short ]; then
  pause 25
  echo "\$ dg4b_host logs --since $t_back host-fusion | grep '<- detection_report'  (25 s after; expect >0)"
  dg4b_host logs --since "$t_back" host-fusion | grep '<- detection_report' | cut -c1-90
  echo "count: $(dg4b_host logs --since "$t_back" host-fusion | grep -c '<- detection_report')"
  echo "\$ dg4b_host logs --since $t_cut host-fusion | grep -c '<- registration '  (expect 0)"
  dg4b_host logs --since "$t_cut" host-fusion | grep -c '<- registration '
  echo "\$ dg4b_pod logs --since $t_cut radar camera vehicle fusion-node | grep -c -E 'lost|cannot reach'  (cut and 25 s after; expect 0)"
  dg4b_pod logs --since "$t_cut" radar camera vehicle fusion-node | grep -c -E 'lost|cannot reach'
  echo "\$ dg4b_pod logs --since $t_cut pod-bridge"
  dg4b_pod logs --since "$t_cut" pod-bridge
else
  echo "waiting for the registration again at the host: $(wait_for 90 "[ \$(dg4b_host logs host-fusion | grep -c '<- registration f0000001') -ge 2 ]")"
  pause 5
  echo "\$ dg4b_host logs host-fusion | grep -E 'removed|request \"Registration\"|<- registration |transport'"
  dg4b_host logs host-fusion | grep -E 'removed|request "Registration"|<- registration |transport'
  echo "\$ dg4b_pod logs --since $t_up fusion-node | grep '<- registration_ack f0000002'"
  dg4b_pod logs --since "$t_up" fusion-node | grep '<- registration_ack f0000002'
  echo "\$ dg4b_pod logs --since $t_cut pod-bridge | grep -E 'lost|back'"
  dg4b_pod logs --since "$t_cut" pod-bridge | grep -E 'lost|back'
  echo
  echo "## the host services back with the default hold time"
  default_hold; hold_changed=0
  echo "waiting for the registration at the host: $(wait_for 90 "dg4b_host logs host-fusion | grep -q '<- registration f0000001'")"
  dg4b_host logs host-fusion | grep '<- registration f0000001'
fi
echo "(end of run)"
