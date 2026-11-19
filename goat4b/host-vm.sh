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
  running=$(limactl shell "$G4B_VM" sudo docker ps -q --filter label=com.docker.compose.project=apex-goat4b 2>/dev/null)
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
