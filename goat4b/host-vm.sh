# Goat step 4b: make, fill, check and remove the goathost VM. Source from the repo root:
#   . goat4b/host-vm.sh
# Works in bash 3.2 and zsh. Needs limactl; the image copy needs Colima's engine
# (DOCKER_HOST set as for any docker command against Colima). Prints no key or certificate body.
# Everything in the VMs is done with the VM's own sudo; nothing needs sudo on the Mac.

G4B_VM=goathost
G4B_IMAGE=apex-sapient:4.2.0
G4B_PKI_DIR=zenoh/goat4/pki
G4B_GATEWAY=192.168.64.1
G4B_ROUTER_IP=192.168.64.4
G4B_ROUTE_FILE=/etc/netplan/92-goathost-route.yaml
G4B_VM_ROUTE_FILE=/etc/netplan/90-cuaslab-route.yaml

# The five files of the host's identity. Never pod1.pem or pod1.key.
G4B_HOST_FILES=(ca.pem host-fusion.pem host-fusion.key host-recorder.pem host-recorder.key)
# What `dg4b_host` needs in the VM when G4B_ENGINE=shell (no secret in them).
G4B_COMPOSE_FILES=(docker-compose.goat1.yml docker-compose.goat4.yml docker-compose.goat4b.yml zenoh/goat1/goat1.env zenoh/goat4/goat4.env)

# Makes the VM if none of that name exists; starts it if stopped.
g4b_vm_create() {
  local st
  if ! limactl list -q 2>/dev/null | grep -qx "$G4B_VM"; then
    limactl start --name="$G4B_VM" --tty=false goat4b/goathost.yaml
    return
  fi
  st=$(limactl list --format '{{.Status}}' "$G4B_VM" 2>/dev/null)
  if [ "$st" != Running ]; then
    limactl start --tty=false "$G4B_VM"
  fi
}

# The 192.168.64.x address of the VM, nothing else; exit 1 if it has none.
g4b_vm_addr() {
  local a
  a=$(limactl shell "$G4B_VM" ip -4 -o addr show 2>/dev/null \
      | sed -n 's/.* inet \(192\.168\.64\.[0-9][0-9]*\)\/.*/\1/p' | head -n 1)
  [ -n "$a" ] || return 1
  printf '%s\n' "$a"
}

# Saves the image from Colima's engine, loads it in the VM, prints both image IDs.
# Exit 1 if they differ.
# Colima's engine is used in a subshell of its own, whatever DOCKER_HOST the caller has.
g4b_vm_load_image() {
  local id_c id_v colima="${G4B_COLIMA_SOCK:-unix://$HOME/.colima/default/docker.sock}"
  ( export DOCKER_HOST="$colima"; docker save "$G4B_IMAGE" ) \
    | limactl shell "$G4B_VM" sudo docker load >/dev/null || return 1
  id_c=$( export DOCKER_HOST="$colima"; docker image inspect -f '{{.Id}}' "$G4B_IMAGE" )
  id_v=$(limactl shell "$G4B_VM" sudo docker image inspect -f '{{.Id}}' "$G4B_IMAGE")
  echo "colima:   $id_c"
  echo "$G4B_VM: $id_v"
  [ -n "$id_c" ] && [ "$id_c" = "$id_v" ]
}

# Copies emulators/ and the five files to /opt/apex-host/ in the VM; sets modes. The compose
# files of G4B_COMPOSE_FILES go to /opt/apex-host/compose/ for G4B_ENGINE=shell.
# Refused while a container of project apex-goat4b runs: replacing emulators/ under a running
# host service leaves its working directory outside the mount (seen live: host-fusion stalled).
g4b_vm_sync() {
  local f base mode running
  if ! running=$(limactl shell "$G4B_VM" sudo docker ps -q --filter label=com.docker.compose.project=apex-goat4b 2>/dev/null); then
    echo "g4b_vm_sync: refused: cannot list the containers of apex-goat4b in $G4B_VM (is the VM and its engine up?)" >&2
    return 1
  fi
  if [ -n "$running" ]; then
    echo "g4b_vm_sync: refused: host services of apex-goat4b run in $G4B_VM; dg4b_host stop first, dg4b_host up -d host-fusion host-recorder after" >&2
    return 1
  fi
  limactl shell "$G4B_VM" sudo install -d -m 0755 /opt/apex-host /opt/apex-host/pki /opt/apex-host/compose || return 1
  limactl shell "$G4B_VM" sudo rm -rf /opt/apex-host/emulators || return 1
  # no macOS metadata in the stream: GNU tar in the VM warns once per file on such headers
  COPYFILE_DISABLE=1 tar -cf - --no-xattrs --no-mac-metadata --exclude __pycache__ --exclude '*.pyc' emulators \
    | limactl shell "$G4B_VM" sudo tar -C /opt/apex-host --no-same-owner -xf - || return 1
  for f in "${G4B_HOST_FILES[@]}"; do
    base=$f
    # umask 077 first: a key file is never readable by others, not even before the chmod
    case "$base" in *.key) mode=0600 ;; *) mode=0644 ;; esac
    limactl shell "$G4B_VM" sudo sh -c "umask 077; cat > /opt/apex-host/pki/$base && chmod $mode /opt/apex-host/pki/$base && chown root:root /opt/apex-host/pki/$base" \
      < "$G4B_PKI_DIR/$f" || return 1
  done
  for f in "${G4B_COMPOSE_FILES[@]}"; do
    base=${f##*/}
    limactl shell "$G4B_VM" sudo sh -c "cat > /opt/apex-host/compose/$base && chmod 0644 /opt/apex-host/compose/$base" \
      < "$f" || return 1
  done
  echo "synced emulators/, ${#G4B_HOST_FILES[@]} identity files and ${#G4B_COMPOSE_FILES[@]} compose files to /opt/apex-host/ in $G4B_VM"
}

# The address that the route file on goatlite names, nothing else (empty if no file).
_g4b_goatlite_route_addr() {
  limactl shell goatlite sudo cat "$G4B_ROUTE_FILE" 2>/dev/null \
    | sed -n 's/^ *- to: *\([0-9.]*\)\/32.*/\1/p' | head -n 1
}

# Routes: in the VM to the router via the Mac (kept over a restart by the provision file, set
# live here), and on goatlite to the VM via the Mac (file and live route). Prints each file written.
g4b_routes_up() {
  local addr old
  addr=$(g4b_vm_addr) || { echo "g4b_routes_up: the VM $G4B_VM has no 192.168.64.x address" >&2; return 1; }

  # the VM's file is written here too (same content as the provision script), so it exists
  # whatever the provision did
  printf '%s\n' \
    "# goathost: the cuaslab router ($G4B_ROUTER_IP) is reached via the Mac; vzNAT isolates VMs at L2" \
    "network:" "  version: 2" "  ethernets:" "    lima0:" "      routes:" \
    "        - to: $G4B_ROUTER_IP/32" "          via: $G4B_GATEWAY" \
    | limactl shell "$G4B_VM" sudo sh -c "umask 077; cat > $G4B_VM_ROUTE_FILE && chmod 0600 $G4B_VM_ROUTE_FILE" || return 1
  echo "wrote $G4B_VM_ROUTE_FILE in $G4B_VM: $G4B_ROUTER_IP/32 via $G4B_GATEWAY"
  limactl shell "$G4B_VM" sudo ip route replace "$G4B_ROUTER_IP/32" via "$G4B_GATEWAY" || return 1

  old=$(_g4b_goatlite_route_addr)
  if [ -n "$old" ] && [ "$old" != "$addr" ]; then
    limactl shell goatlite sudo ip route del "$old/32" 2>/dev/null || true
  fi
  printf '%s\n' \
    "# goathost: the host VM ($addr) is reached via the Mac; vzNAT isolates VMs at L2" \
    "network:" "  version: 2" "  ethernets:" "    lima0:" "      routes:" \
    "        - to: $addr/32" "          via: $G4B_GATEWAY" \
    | limactl shell goatlite sudo sh -c "cat > $G4B_ROUTE_FILE && chmod 0600 $G4B_ROUTE_FILE" || return 1
  old=$(_g4b_goatlite_route_addr)
  if [ "$old" != "$addr" ]; then
    echo "g4b_routes_up: $G4B_ROUTE_FILE on goatlite reads back ${old:-nothing}, not $addr" >&2
    return 1
  fi
  echo "wrote $G4B_ROUTE_FILE on goatlite: $addr/32 via $G4B_GATEWAY"
  limactl shell goatlite sudo ip route replace "$addr/32" via "$G4B_GATEWAY" || return 1
}

# Prints both routes; exit 1 if either is missing or goatlite's route names another address.
g4b_routes_check() {
  local bad=0 addr file_addr r_vm r_gl
  addr=$(g4b_vm_addr) || { echo "routes: the VM $G4B_VM has no 192.168.64.x address"; return 1; }

  r_vm=$(limactl shell "$G4B_VM" ip route show "$G4B_ROUTER_IP/32" 2>/dev/null | head -n 1)
  echo "route in $G4B_VM: ${r_vm:-none}"
  case "$r_vm" in *"via $G4B_GATEWAY"*) ;; *) echo "routes: $G4B_VM has no route $G4B_ROUTER_IP/32 via $G4B_GATEWAY"; bad=1 ;; esac

  r_gl=$(limactl shell goatlite ip route show "$addr/32" 2>/dev/null | head -n 1)
  echo "route in goatlite: ${r_gl:-none}"
  case "$r_gl" in *"via $G4B_GATEWAY"*) ;; *) echo "routes: goatlite has no live route $addr/32 via $G4B_GATEWAY"; bad=1 ;; esac

  file_addr=$(_g4b_goatlite_route_addr)
  echo "file $G4B_ROUTE_FILE on goatlite names: ${file_addr:-none}"
  if [ "$file_addr" != "$addr" ]; then
    echo "routes: address mismatch: $G4B_VM is $addr, $G4B_ROUTE_FILE on goatlite names ${file_addr:-nothing} (g4b_routes_up)"; bad=1
  fi
  [ "$bad" -eq 0 ]
}

# Without --yes: prints what it would remove and changes nothing. With --yes: removes the route
# file and the route on goatlite, then deletes the VM.
g4b_vm_remove() {
  local old
  old=$(_g4b_goatlite_route_addr)
  echo "would remove: the route ${old:-(none)}/32 and the file $G4B_ROUTE_FILE on goatlite; the VM $G4B_VM with its disk"
  if [ "${1:-}" != "--yes" ]; then
    echo "nothing removed; call g4b_vm_remove --yes"
    return 0
  fi
  if [ -n "$old" ]; then
    limactl shell goatlite sudo ip route del "$old/32" 2>/dev/null || true
  fi
  limactl shell goatlite sudo rm -f "$G4B_ROUTE_FILE" || return 1
  echo "removed $G4B_ROUTE_FILE and its route on goatlite"
  limactl stop "$G4B_VM" 2>/dev/null || true
  limactl delete --force "$G4B_VM"
}

# Clock of goathost (G4B-06). Two things set it: systemd-timesyncd, and Lima's host agent, which
# about every 10 s reads the drift through the guest agent (lima-guestagent) and sets the guest
# clock when it is off (seen at boot: "guest clock adjusted (was 312ms off)"). A step holds only
# while both are stopped. While the guest agent is stopped, Lima's forwarded Docker socket may be
# down: use `limactl shell goathost ...` (ssh) for commands in the VM in that window.
# A caller that steps the clock restores it in a trap: trap g4b_clock_restore EXIT INT TERM.

# State of a step, kept in a file so that a restore from another shell (after an interruption)
# knows it: "before_ms=<offset of the VM from the Mac before the first step> stepped_s=<sum of
# the steps>". Written by g4b_clock_step, read and then removed by g4b_clock_restore.
G4B_CLOCK_STATE_DEFAULT=/tmp/g4b-clock-state

# Both clock syncs of the VM active? Prints "systemd-timesyncd <state>, lima-guestagent <state>".
_g4b_syncs() {
  local ts ga
  ts=$(limactl shell "$G4B_VM" systemctl is-active systemd-timesyncd < /dev/null 2>/dev/null | head -n 1)
  ga=$(limactl shell "$G4B_VM" systemctl is-active lima-guestagent < /dev/null 2>/dev/null | head -n 1)
  echo "systemd-timesyncd ${ts:-unknown}, lima-guestagent ${ga:-unknown}"
  [ "$ts" = active ] && [ "$ga" = active ]
}

# Moves the clock of the VM by <seconds> (a number); exit status of the set.
_g4b_clock_move() {
  limactl shell "$G4B_VM" sudo python3 -c "import time; time.clock_settime(time.CLOCK_REALTIME, time.clock_gettime(time.CLOCK_REALTIME) + ($1))" < /dev/null
}

# g4b_clock_step <seconds>: stops both, then moves the VM's clock by <seconds> (-5 to 5; positive
# = ahead) from its current reading. Refused without a number or beyond 5 s. A first step (both
# syncs active) saves the VM's offset from the Mac in $G4B_CLOCK_STATE; each step adds to the sum
# there. If the set fails, both syncs are started again.
g4b_clock_step() {
  local d=${1-} state=${G4B_CLOCK_STATE:-$G4B_CLOCK_STATE_DEFAULT} m before stepped=0
  if ! printf '%s\n' "$d" | grep -Eq '^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)$'; then
    echo "g4b_clock_step: refused: give the step in seconds as a number, e.g. 0.5 or -0.15 (got '${d}')" >&2
    return 1
  fi
  if ! awk -v d="$d" 'BEGIN { exit !(d <= 5 && d >= -5) }'; then
    echo "g4b_clock_step: refused: $d s is more than 5 s" >&2
    return 1
  fi
  if [ -f "$state" ] && ! _g4b_syncs >/dev/null; then
    # a step on top of a step: keep the offset saved before the first one
    before=$(sed -n 's/^before_ms=\([^ ]*\) .*/\1/p' "$state")
    stepped=$(sed -n 's/.* stepped_s=\([^ ]*\)$/\1/p' "$state")
  else
    m=$(_g4b_offset 5 limactl shell "$G4B_VM" date +%s.%N)
    case "$m" in unknown|'') echo "g4b_clock_step: cannot read the offset of $G4B_VM before the step" >&2; return 1 ;; esac
    before=${m%% *}
  fi
  limactl shell "$G4B_VM" sudo systemctl stop systemd-timesyncd lima-guestagent < /dev/null \
    || { echo "g4b_clock_step: stopping the clock syncs failed in $G4B_VM (g4b_clock_restore)" >&2; return 1; }
  if ! _g4b_clock_move "$d"; then
    limactl shell "$G4B_VM" sudo systemctl start lima-guestagent systemd-timesyncd < /dev/null
    echo "g4b_clock_step: setting the clock failed in $G4B_VM; started both again ($(_g4b_syncs))" >&2
    return 1
  fi
  stepped=$(awk -v a="${stepped:-0}" -v d="$d" 'BEGIN { printf "%.6g", a + d }')
  printf 'before_ms=%s stepped_s=%s\n' "$before" "$stepped" > "$state"
  echo "g4b_clock_step: stopped systemd-timesyncd and lima-guestagent in $G4B_VM; clock moved by $d s (sum of steps $stepped s; offset before $before ms)"
}

# g4b_clock_restore: while both syncs are still stopped, moves the clock back by the sum of the
# steps in $G4B_CLOCK_STATE; starts both again; waits (G4B_RESTORE_TIMEOUT s, default 180) until
# both are active and the VM's offset from the Mac is within G4B_RESTORE_MARGIN_MS (default 30)
# of the offset saved before the first step (with no saved offset: within its own bound plus
# the margin). Needs _g4b_offset of goat4b/dg4b.sh. Exit 1 if not back in time.
g4b_clock_restore() {
  local limit=${G4B_RESTORE_TIMEOUT:-180} margin=${G4B_RESTORE_MARGIN_MS:-30}
  local state=${G4B_CLOCK_STATE:-$G4B_CLOCK_STATE_DEFAULT} before='' stepped=0 start now m off bound syncs ok
  if [ -f "$state" ]; then
    before=$(sed -n 's/^before_ms=\([^ ]*\) .*/\1/p' "$state")
    stepped=$(sed -n 's/.* stepped_s=\([^ ]*\)$/\1/p' "$state")
  fi
  if [ -n "$stepped" ] && [ "$stepped" != 0 ] && ! _g4b_syncs >/dev/null; then
    # "-$stepped" is a Python expression: for a negative sum it reads --0.15, which is 0.15
    if _g4b_clock_move "-$stepped"; then
      echo "g4b_clock_restore: moved the clock of $G4B_VM back by $stepped s"
    else
      echo "g4b_clock_restore: moving the clock back failed in $G4B_VM; the syncs must bring it back" >&2
    fi
  fi
  limactl shell "$G4B_VM" sudo systemctl start lima-guestagent systemd-timesyncd < /dev/null \
    || echo "g4b_clock_restore: starting the services failed in $G4B_VM" >&2
  start=$(date +%s)
  while :; do
    syncs=$(_g4b_syncs); ok=$?
    m=$(_g4b_offset 5 limactl shell "$G4B_VM" date +%s.%N)
    now=$(date +%s)
    case "$m" in
      unknown|'') off=unknown; bound=unknown ;;
      *) off=${m%% *}; bound=${m#* }; bound=${bound%% *}
         if [ "$ok" -eq 0 ] && if [ -n "$before" ]; then
              awk -v o="$off" -v b="$before" -v g="$margin" 'BEGIN { exit !(o - b <= g && b - o <= g) }'
            else
              awk -v o="$off" -v b="$bound" -v g="$margin" 'BEGIN { exit !(o <= b + g && -o <= b + g) }'
            fi; then
           if [ -n "$before" ]; then
             echo "g4b_clock_restore: offset back after $((now - start)) s: ${off} ms, before the step ${before} ms (margin +/-${margin} ms); $syncs"
           else
             echo "g4b_clock_restore: offset back after $((now - start)) s: ${off} ms (no saved offset; bound +/-${bound} ms, margin +/-${margin} ms); $syncs"
           fi
           rm -f "$state"
           return 0
         fi ;;
    esac
    if [ $((now - start)) -ge "$limit" ]; then
      echo "g4b_clock_restore: not back after $((now - start)) s: offset ${off} ms, before the step ${before:-unknown} ms (margin +/-${margin} ms); $syncs" >&2
      return 1
    fi
    sleep 5
  done
}
