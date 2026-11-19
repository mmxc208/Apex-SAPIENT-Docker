#!/bin/zsh -f
# G4B-06, clock tolerance (task 4 step 1). Run from the repo root: zsh -f goat4b/run_g4b_06.sh
# Steps the clock of goathost to each offset (from its disciplined state; negative = behind), waits
# 5 s, takes 40 s of traffic and reads both directions; then restores and reads 60 s more.
# The trap restores the clock on EXIT, INT and TERM and prints g4b_state.
cd "${0:A:h}/.." || exit 1
. goat4b/run_lib.sh

OFFSETS=(${=G4B_06_OFFSETS:--0.05 -0.15 -0.30 +0.5 +0.8 +1.2})
TMPD=$(mktemp -d /tmp/g4b06.XXXXXX)

done_cleanup=0
cleanup() {
  [ "$done_cleanup" = 1 ] && return
  done_cleanup=1
  echo "## trap ($1) at $(utc): restore if a step is left, then the state"
  if [ -f "${G4B_CLOCK_STATE:-$G4B_CLOCK_STATE_DEFAULT}" ] || ! _g4b_syncs >/dev/null; then
    echo "\$ g4b_clock_restore"
    g4b_clock_restore; echo "restore exit=$?"
  else
    echo "nothing to restore: no step state file, $(_g4b_syncs)"
  fi
  echo "\$ g4b_state"
  g4b_state
  echo "(end of trap)"
}
trap 'cleanup EXIT' EXIT
trap 'cleanup INT; exit 130' INT
trap 'cleanup TERM; exit 143' TERM

# window <label> <target offset s> <Mac start> <Mac end>: the numbers of one window.
# Host-side times (recorder t, docker logs) are on the stepped clock: Mac time + target.
window() {
  local label=$1 target=$2 w0=$3 w1=$4 h0 h1 f=$TMPD/rec.jsonl
  h0=$(utc_add "$w0" "$target"); h1=$(utc_add "$w1" "$target")
  echo "### window $label: Mac $w0 to $w1; on the host's clock $h0 to $h1"
  hostrec > "$f"
  hostdocker logs --since "$h0" --until "$h1" apex-goat4b-host-fusion-1 > "$TMPD/host.log" 2>&1
  dg4b_pod logs --no-log-prefix --since "$w0" --until "$w1" fusion-node > "$TMPD/pod.log" 2>&1
  echo "-- up: the pod's messages at the host recorder (anchor FABRIC_POD1_ID), all kinds; then detection reports only"
  python3 goat4b/readers.py ages --anchor "$FABRIC_POD1_ID" --since "$h0" --until "$h1" "$f"
  python3 goat4b/readers.py ages --anchor "$FABRIC_POD1_ID" --since "$h0" --until "$h1" --kinds detection_report "$f"
  echo "-- up: the host fusion node's rejections in the window"
  python3 goat4b/readers.py rejections "$TMPD/host.log"
  grep 'invalid message from' "$TMPD/host.log" | head -n 3 | cut -c1-200
  echo "-- down: host tasks sent and acknowledged (host log)"
  echo "tasks sent: $(grep -c -- '-> task f0000002 -> f0000001' "$TMPD/host.log")  task acks received: $(grep -c -- '<- task_ack f0000001' "$TMPD/host.log")"
  echo "-- down: the pod fusion node's messages from above (pod log): accepted '<- <kind> f0000002' and dropped"
  grep -E -- '<- [a-z_]+ f0000002' "$TMPD/pod.log" | cut -c1-110
  grep -- 'invalid message from above dropped' "$TMPD/pod.log" | cut -c1-200
  python3 - "$label" "$FABRIC_POD1_ID" "$h0" "$h1" "$f" "$TMPD/host.log" "$TMPD/pod.log" "$TMPD" <<'PY'
import json, re, sys
sys.path.insert(0, "goat4b")
import readers
label, pod, h0, h1, f, hl, pl, tmpd = sys.argv[1:]
rows = [r for r in map(json.loads, open(f)) if r.get("anchor") == pod]
up = readers.apparent_ages(rows, h0, h1)
rej_up = readers.rejections(open(hl))["invalid message from"]
acc_up = up["count"] - rej_up
pod_lines = open(pl).read().splitlines()
acc_dn = sum(bool(re.search(r"<- [a-z_]+ f0000002", l)) for l in pod_lines)
drop = [l for l in pod_lines if "invalid message from above dropped" in l]

def delta_s(text):  # str(timedelta): "0:00:00.493293" or "-1 day, 23:59:59.100000"
    neg = 0
    m = re.match(r"-(\d+) days?, (.*)", text)
    if m:
        neg, text = int(m.group(1)), m.group(2)
    h, mi, s = text.split(":")
    return int(h) * 3600 + int(mi) * 60 + float(s) - neg * 86400

ages_dn = []
for l in drop:
    m = re.search(r"Timestamp delta (\S+(?: days?, \S+)?)", l)
    if m:
        ages_dn.append(-delta_s(m.group(1)))  # age = receive time - message time = -delta
n_dn = acc_dn + len(drop)
dn = {"count": n_dn, "min": min(ages_dn) if ages_dn and not acc_dn else None,
      "max": max(ages_dn) if ages_dn and not acc_dn else None}
v_up = readers.judge_step(up, acc_up, rej_up)
if n_dn >= readers.MIN_MESSAGES and dn["min"] is None:
    v_dn = "not judged (no age logged for an accepted message)"
else:
    v_dn = readers.judge_step(dn, acc_dn, len(drop))
f3 = lambda v: "-" if v is None else "%.3f" % v
print(f"SUMMARY {label} | up: ages {up['count']} min {f3(up['min'])} median {f3(up['median'])} max {f3(up['max'])}"
      f" accepted {acc_up} rejected {rej_up} judge_step {v_up}"
      f" | down: messages {n_dn} accepted {acc_dn} rejected {len(drop)}"
      f" ages of the rejected {','.join('%.3f' % a for a in ages_dn) or '-'} judge_step {v_dn}")
if up["median"] is not None:
    open(f"{tmpd}/median-{label}", "w").write("%.6f\n" % up["median"])
PY
}

header
echo "# G4B-06 (task 4 step 1): clock tolerance. Script goat4b/run_g4b_06.sh (this commit). Offsets: ${OFFSETS[*]} s."
echo "# Sign: a NEGATIVE offset sets the clock of goathost BEHIND: the pod's messages reach the host looking as if"
echo "# from the future, the host's tasks reach the pod looking old. A positive offset is the reverse."
echo "# up = pod -> host: apparent age = host recorder's t minus msg.timestamp (readers.py ages), all records of the pod's"
echo "#   anchor; accepted = those records minus the host fusion node's 'invalid message from' lines (each rejected"
echo "#   message logs one such line; accepted detection reports are logged only every 10th)."
echo "# down = host -> pod: the pod side has no recorder of the down key. Read from the pod fusion node's log: accepted ="
echo "#   '<- <kind> f0000002' lines, rejected = 'invalid message from above dropped' lines; their 'Timestamp delta' is"
echo "#   the message's time minus the receive time, so age = -delta. An accepted message logs no age."
echo "# Window rule (spec 6.4): age inside -0.1..0.9 s accepted. judge_step of goat4b/readers.py, fewer than 20 messages: not judged."
echo "# Each step: g4b_clock_step <target minus the sum so far>, 5 s, then a 40 s window. Host-side times are on the stepped clock."
echo
echo "## before"
echo "\$ g4b_state"; g4b_state
echo "\$ containers' StartedAt"; started_at | tee "$TMPD/started-before.txt"
echo
echo "## base: 40 s with no clock touched"
w0=$(utc_in 0); pause 40; w1=$(utc_in 0)
window base 0 "$w0" "$w1"

cum=0
for target in "${OFFSETS[@]}"; do
  d=$(awk -v t="$target" -v c="$cum" 'BEGIN { printf "%.6g", t - c }')
  echo
  echo "## step to $target s (move $d s) at $(utc)"
  echo "\$ g4b_clock_step $d"
  if ! g4b_clock_step "$d"; then
    echo "g4b_clock_step failed: G4B-06 unknown from here"; exit 1
  fi
  cum=$target
  echo "offset of goathost from the Mac just after: $(_g4b_offset 3 limactl shell goathost date +%s.%N) (offset bound rtt-min rtt-med rtt-max best rounds; ms)"
  pause 5
  w0=$(utc_in 0); pause 40; w1=$(utc_in 0)
  echo "offset of goathost from the Mac 45 s after: $(_g4b_offset 3 limactl shell goathost date +%s.%N); $(_g4b_syncs)"
  window "$target" "$target" "$w0" "$w1"
done

echo
echo "## restore at $(utc)"
echo "\$ g4b_clock_restore"
g4b_clock_restore; echo "restore exit=$?"
pause 5
w0=$(utc_in 0); pause 60; w1=$(utc_in 0)
window after-restore 0 "$w0" "$w1"
python3 - "$TMPD" <<'PY'
import sys
t = sys.argv[1]
try:
    b, a = (float(open(f"{t}/median-{n}").read()) for n in ("base", "after-restore"))
except OSError:
    print("clock back by the traffic: unknown (a median is missing)")
else:
    print("clock back by the traffic: median age after the restore %.3f s, base %.3f s, difference %.3f s: %s"
          % (a, b, a - b, "yes (within 0.05 s)" if abs(a - b) <= 0.05 else "NO (more than 0.05 s)"))
PY
echo "\$ containers' StartedAt after"
started_at > "$TMPD/started-after.txt"; cat "$TMPD/started-after.txt"
if cmp -s "$TMPD/started-before.txt" "$TMPD/started-after.txt"; then echo "StartedAt: unchanged for all $(wc -l < "$TMPD/started-after.txt" | tr -d ' ') containers"; else echo "StartedAt: CHANGED"; diff "$TMPD/started-before.txt" "$TMPD/started-after.txt"; fi
echo "(end of run)"
