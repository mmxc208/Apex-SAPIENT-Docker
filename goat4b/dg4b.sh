# Goat step 4b helpers. Source from the repo root, after the Docker environment is set:
#   . goat4/dg4.sh && . goat4b/dg4b.sh && . goat4b/host-vm.sh
#   goat4b_ready && dg4b_pod up-all && dg4b_host up -d host-fusion host-recorder
# Works in bash 3.2 and zsh. Prints nothing secret: no key file is read.
#
# Two engines, one definition: dg4b_pod runs the three compose files on Colima's engine,
# dg4b_host runs the same files on the engine of the goathost VM.
# G4B_ENGINE says how dg4b_host reaches that engine:
#   socket  the Docker socket that Lima forwards to $HOME/.lima/goathost/sock/docker.sock
#   shell   `limactl shell goathost sudo docker compose` on copies in /opt/apex-host/compose/
# DOCKER_HOST is set only inside a function's own subshell; DOCKER_CONFIG is left as the caller
# has it.

# Default socket: Task 2 measured that the forwarded socket works from the agent's shell.
: "${G4B_ENGINE:=socket}"

G4B_POD_SERVICES="zenohd-pod fusion-node radar camera vehicle bridge-node recorder pod-bridge"
G4B_HOST_SERVICES="host-fusion host-recorder"

_g4b_colima_sock() { printf '%s\n' "${G4B_COLIMA_SOCK:-unix://$HOME/.colima/default/docker.sock}"; }
_g4b_vm_sock() { printf '%s\n' "${G4B_VM_SOCK:-unix://$HOME/.lima/goathost/sock/docker.sock}"; }

# Words of $1 (a space-separated list) contain $2?
_g4b_in() { case " $1 " in *" $2 "*) return 0 ;; *) return 1 ;; esac; }

# Prints the service names that the compose subcommand $1 names, one per line. Arguments: the
# subcommand, then the words after it. Options that take a value in a separate word are skipped
# with their value. For `run` only the first name is a service; the words after it are the command.
_g4b_services() {
  local sub=$1 skip=0 a
  shift
  for a in "$@"; do
    if [ "$skip" -eq 1 ]; then skip=0; continue; fi
    case "$a" in
      --scale|-t|--timeout|--pull|--attach|--no-attach|--wait-timeout|--exit-code-from) skip=1 ;;
      -e|--env|--env-from-file|-v|--volume|-l|--label|-p|--publish|-u|--user|-w|--workdir|--name|--entrypoint|--cap-add|--cap-drop)
        [ "$sub" = run ] && skip=1 ;;
      -*) ;;
      *) printf '%s\n' "$a"; [ "$sub" = run ] && return 0 ;;
    esac
  done
  return 0
}

# The first word of the arguments that is not an option: the compose subcommand.
_g4b_subcmd() {
  local a
  for a in "$@"; do
    case "$a" in -*) ;; *) printf '%s\n' "$a"; return 0 ;; esac
  done
}

# Prints the words of the space-separated list $1, one per line (zsh does not split $var).
_g4b_w() { printf '%s\n' "$1" | tr ' ' '\n'; }

# The subcommands that make, start or run containers: each must name at least one service, and
# only services of its engine. (`up` with no service, `start` or `restart` with none, would act
# on every service of the project, the other engine's among them.)
G4B_GUARDED="up run create start restart"

# _g4b_check <allowed services> <who> args...  (args include the subcommand)
# Prints the reason and returns 1 if refused; returns 0 for a subcommand that is not guarded.
_g4b_check() {
  local allowed=$1 who=$2 sub s n=0 a found=0
  local rest=()
  shift 2
  sub=$(_g4b_subcmd "$@")
  _g4b_in "$G4B_GUARDED" "$sub" || return 0
  for a in "$@"; do
    if [ "$found" -eq 1 ]; then rest+=("$a"); elif [ "$a" = "$sub" ]; then found=1; fi
  done
  for s in $(_g4b_services "$sub" ${rest[@]+"${rest[@]}"}); do
    n=$((n + 1))
    if ! _g4b_in "$allowed" "$s"; then
      echo "$who: refused: '$s' is not a service of this engine (allowed: $allowed)" >&2
      return 1
    fi
  done
  if [ "$n" -eq 0 ]; then
    echo "$who: refused: $sub needs at least one service named (allowed: $allowed)" >&2
    return 1
  fi
  return 0
}

# Colima's engine.
dg4b_pod() {
  if [ "${1:-}" = up-all ]; then
    shift
    set -- up -d "$@" $(_g4b_w "$G4B_POD_SERVICES")
  fi
  _g4b_check "$G4B_POD_SERVICES" dg4b_pod "$@" || return 1
  (
    export DOCKER_HOST="$(_g4b_colima_sock)"
    docker compose -p apex-goat4 \
      --env-file zenoh/goat1/goat1.env --env-file zenoh/goat4/goat4.env \
      -f docker-compose.goat1.yml -f docker-compose.goat4.yml -f docker-compose.goat4b.yml "$@"
  )
}

# The engine of the goathost VM. `up`, `run`, `create`, `start` and `restart` may name only host
# services; `up` adds --no-deps.
dg4b_host() {
  local sub
  _g4b_check "$G4B_HOST_SERVICES" dg4b_host "$@" || return 1
  sub=$(_g4b_subcmd "$@")
  if [ "$sub" = up ]; then
    # --no-deps goes right after `up`
    local out=() a added=0
    for a in "$@"; do
      out+=("$a")
      if [ "$added" -eq 0 ] && [ "$a" = up ]; then out+=(--no-deps); added=1; fi
    done
    set -- "${out[@]}"
  fi
  case "${G4B_ENGINE:-socket}" in
    socket)
      (
        export DOCKER_HOST="$(_g4b_vm_sock)"
        docker compose -p apex-goat4b \
          --env-file zenoh/goat1/goat1.env --env-file zenoh/goat4/goat4.env \
          -f docker-compose.goat1.yml -f docker-compose.goat4.yml -f docker-compose.goat4b.yml "$@"
      )
      ;;
    shell)
      # The files were copied by g4b_vm_sync. Variables of the caller that the compose files
      # read are passed on explicitly.
      local envs=()
      [ -n "${HOST_HOLD_SECONDS+x}" ] && envs+=("HOST_HOLD_SECONDS=$HOST_HOLD_SECONDS")
      limactl shell --workdir /opt/apex-host/compose goathost sudo env ${envs[@]+"${envs[@]}"} \
        docker compose -p apex-goat4b \
        --env-file goat1.env --env-file goat4.env \
        -f docker-compose.goat1.yml -f docker-compose.goat4.yml -f docker-compose.goat4b.yml "$@"
      ;;
    *)
      echo "dg4b_host: G4B_ENGINE must be socket or shell, not '${G4B_ENGINE}'" >&2
      return 1
      ;;
  esac
}

# Exit 0 only if the two-engine rig can start (spec 6.3). One line for each failure.
goat4b_ready() {
  local bad=0 f out id_c id_v addr ls_out
  local want="ca.pem host-fusion.pem host-fusion.key host-recorder.pem host-recorder.key"

  # step 4's own conditions, on Colima's engine
  out=$( ( export DOCKER_HOST="$(_g4b_colima_sock)"; goat4_ready ) 2>&1 ) \
    || { printf '%s\n' "$out"; echo "goat4b_ready: goat4_ready of step 4 fails (lines above)"; bad=1; }

  # the VM runs
  if [ "$(limactl list --format '{{.Status}}' goathost 2>/dev/null)" != Running ]; then
    echo "goat4b_ready: the VM goathost is not running (g4b_vm_create)"; bad=1
    return 1
  fi

  # the image, with the same ID on both engines
  id_c=$( ( export DOCKER_HOST="$(_g4b_colima_sock)"; docker image inspect -f '{{.Id}}' apex-sapient:4.2.0 ) 2>/dev/null )
  id_v=$(limactl shell goathost sudo docker image inspect -f '{{.Id}}' apex-sapient:4.2.0 2>/dev/null)
  if [ -z "$id_v" ]; then
    echo "goat4b_ready: the image apex-sapient:4.2.0 is missing in goathost (g4b_vm_load_image)"; bad=1
  elif [ "$id_c" != "$id_v" ]; then
    echo "goat4b_ready: image ID differs: colima=$id_c goathost=$id_v"; bad=1
  fi

  # the five files are there; no pod1 file is anywhere below /opt/apex-host
  ls_out=$(limactl shell goathost sudo ls -1 /opt/apex-host/pki 2>/dev/null)
  for f in $(_g4b_w "$want"); do
    printf '%s\n' "$ls_out" | grep -qxF -- "$f" || { echo "goat4b_ready: /opt/apex-host/pki/$f is missing in goathost (g4b_vm_sync)"; bad=1; }
  done
  # each key file in /opt/apex-host/pki: mode 0600, owner root
  out=$(limactl shell goathost sudo sh -c 'stat -c "%a %U %n" /opt/apex-host/pki/*.key' 2>/dev/null \
    | while read -r m o n; do
        [ "$m" = 600 ] && [ "$o" = root ] \
          || echo "goat4b_ready: ${n##*/} is mode $m owner $o in goathost; must be 600 root (g4b_vm_sync)"
      done)
  [ -z "$out" ] || { printf '%s\n' "$out"; bad=1; }
  out=$(limactl shell goathost sudo find /opt/apex-host -name 'pod1*' 2>/dev/null)
  if [ -n "$out" ] || printf '%s\n' "$ls_out" | grep -q '^pod1'; then
    echo "goat4b_ready: a pod1 file is in goathost: the pod's key must never be there"; bad=1
  fi

  # the VM's address and the route on goatlite agree; both routes exist
  out=$(g4b_routes_check 2>&1) || { printf '%s\n' "$out" | sed 's/^/goat4b_ready: /'; bad=1; }

  # TCP from the VM to the router
  limactl shell goathost timeout 5 bash -c 'exec 3<>/dev/tcp/192.168.64.4/7447' >/dev/null 2>&1 \
    || { echo "goat4b_ready: no TCP connection to 192.168.64.4:7447 within 5 s from goathost"; bad=1; }

  # no host service of project apex-goat4 runs in Colima
  for f in $(_g4b_w "$G4B_HOST_SERVICES"); do
    out=$( ( export DOCKER_HOST="$(_g4b_colima_sock)"
             docker ps -q --filter label=com.docker.compose.project=apex-goat4 \
               --filter "label=com.docker.compose.service=$f" ) 2>/dev/null )
    [ -z "$out" ] || { echo "goat4b_ready: $f of project apex-goat4 runs in Colima; stop it (dg4b_pod stop $f)"; bad=1; }
  done

  [ "$bad" -eq 0 ]
}

# Six lines: the time service of goathost and Lima's time sync in it (the guest agent, through
# which Lima's host agent sets the guest clock about every 10 s), the offset of each VM from the
# Mac in ms with its bound, the route from Colima and from goathost to 192.168.64.4.
# Reads only; "unknown" where it cannot.
g4b_state() {
  local v

  v=$(limactl shell goathost systemctl is-active systemd-timesyncd 2>/dev/null | head -n 1)
  echo "goathost time service (systemd-timesyncd): ${v:-unknown}"
  v=$(limactl shell goathost systemctl is-active lima-guestagent 2>/dev/null | head -n 1)
  echo "goathost Lima time sync (lima-guestagent): ${v:-unknown}"

  echo "offset of goathost from the Mac (ms): $(_g4b_offset_text 5 limactl shell goathost date +%s.%N)"
  echo "offset of colima from the Mac (ms): $(_g4b_offset_text 5 colima ssh -- date +%s.%N)"

  v=$(colima ssh -- ip route get 192.168.64.4 2>/dev/null | head -n 1 | tr -s ' ')
  echo "route colima to 192.168.64.4: ${v:-unknown}"
  v=$(limactl shell goathost ip route get 192.168.64.4 2>/dev/null | head -n 1 | tr -s ' ')
  echo "route goathost to 192.168.64.4: ${v:-unknown}"
  return 0
}

# Offset of a VM's clock from the Mac's, by the method of G4-13: <rounds> times, the Mac's time,
# the command that prints the VM's epoch seconds, the Mac's time; the round with the shortest
# round trip; offset = VM time minus the middle of the two Mac readings; bound = half the round
# trip. Prints "<offset ms> <bound ms> <rtt min> <rtt median> <rtt max> <best round> <rounds ok>"
# (ms, one decimal), or "unknown" if no round gave a number.
# Arguments: <rounds> <command...>
_g4b_offset() {
  python3 - "$@" <<'PY'
import statistics, subprocess, sys, time
n, cmd = int(sys.argv[1]), sys.argv[2:]
rounds = []
for i in range(1, n + 1):
    a = time.time()
    p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    b = time.time()
    try:
        v = float(p.stdout.split()[0])
    except (IndexError, ValueError):
        continue
    rounds.append((b - a, v - (a + b) / 2, i))
if not rounds:
    print("unknown")
else:
    rtt = [r[0] * 1000 for r in rounds]
    best = min(rounds)
    print("%.1f %.1f %.1f %.1f %.1f %d %d" % (best[1] * 1000, best[0] * 500, min(rtt),
          statistics.median(rtt), max(rtt), best[2], len(rounds)))
PY
}

# "<offset> (bound +/-<bound>, best of <rounds>)" in whole ms, or "unknown".
_g4b_offset_text() {
  local n=$1 out
  out=$(_g4b_offset "$@")
  case "$out" in
    unknown|'') echo unknown ;;
    *) printf '%s\n' "$out" | awk -v n="$n" '{ printf "%+.0f (bound +/-%.0f, best of %d)\n", $1, $2, n }' ;;
  esac
}
