# Goat step 4 helper. Source it from the repo root, after the Docker environment is set:
#   . goat4/dg4.sh && goat4_ready && dg4 up -d
# Works in bash and zsh. Prints nothing secret: no key file is read.

dg4() {
  docker compose -p apex-goat4 \
    --env-file zenoh/goat1/goat1.env --env-file zenoh/goat4/goat4.env \
    -f docker-compose.goat1.yml -f docker-compose.goat4.yml "$@"
}

# Exit 0 only if the rig can start on cuaslab. Each failure prints one line and the function
# goes on, so one run names every problem.
goat4_ready() {
  local bad=0 f id cn pair name var rc
  local pki=zenoh/goat4/pki env4=zenoh/goat4/goat4.env env1=zenoh/goat1/goat1.env
  # GOAT4_FABRIC_ADDR is a test hook: it changes the address that check (d) tries, not the
  # address in the overlay, which stays tls/192.168.64.4:7447.
  local addr=${GOAT4_FABRIC_ADDR:-192.168.64.4:7447}

  # (a) the seven files and goat4.env, each a regular file (Docker makes a directory where
  # a bind-mount source is missing; such a directory counts as a missing file)
  for f in "$env4" $pki/ca.pem $pki/pod1.pem $pki/pod1.key $pki/host-fusion.pem \
           $pki/host-fusion.key $pki/host-recorder.pem $pki/host-recorder.key; do
    [ -f "$f" ] || { echo "goat4_ready: missing file $f (or not a regular file)"; bad=1; }
  done

  # (b) each anchor equals the common name of its certificate
  if [ -f "$env4" ]; then
    for pair in FABRIC_POD1_ID:pod1 FABRIC_HOST_FUSION_ID:host-fusion FABRIC_HOST_RECORDER_ID:host-recorder; do
      var=${pair%%:*}; name=${pair#*:}
      id=$(sed -n "s/^$var=//p" "$env4" | tail -n 1)
      if [ -z "$id" ]; then echo "goat4_ready: $var is not set in $env4"; bad=1; continue; fi
      # compose takes a variable of the shell environment before both env files
      if printenv "$var" >/dev/null && [ "$(printenv "$var")" != "$id" ]; then
        echo "goat4_ready: $var is set in the shell environment to another value than in $env4; compose would use the shell's value (unset it, or source $env4)"; bad=1
      fi
      [ -f "$pki/$name.pem" ] || continue
      cn=$(openssl x509 -in "$pki/$name.pem" -noout -subject -nameopt multiline 2>/dev/null \
           | sed -n 's/^ *commonName *= *//p' | head -n 1)
      [ "$cn" = "$id" ] || { echo "goat4_ready: $var in $env4 is not the common name of $pki/$name.pem"; bad=1; }
    done

    # (c) no anchor equals a FABRIC_*_ID of goat1.env
    if [ -f "$env1" ]; then
      for var in FABRIC_POD1_ID FABRIC_HOST_FUSION_ID FABRIC_HOST_RECORDER_ID; do
        id=$(sed -n "s/^$var=//p" "$env4" | tail -n 1)
        [ -n "$id" ] || continue
        if sed -n 's/^FABRIC_[A-Z0-9_]*_ID=//p' "$env1" | grep -qxF -- "$id"; then
          echo "goat4_ready: $var in $env4 equals a FABRIC_*_ID of $env1 (step 1 ids, not cuaslab anchors)"; bad=1
        fi
      done
    else
      echo "goat4_ready: missing file $env1"; bad=1
    fi
  fi

  # (d) a container on the Colima VM opens TCP to the fabric router within 5 s. The probe
  # exits 3 when the connection fails; any other failure is Docker's (no DOCKER_HOST, no
  # daemon, image missing), and is reported apart.
  if ! docker image inspect apex-sapient:4.2.0 >/dev/null 2>&1; then
    echo "goat4_ready: docker cannot be used, or the image apex-sapient:4.2.0 is missing (check DOCKER_HOST); TCP to $addr not tried"; bad=1
  else
    docker run --rm --network bridge -e ADDR="$addr" apex-sapient:4.2.0 python -c '
import os, socket, sys
host, port = os.environ["ADDR"].rsplit(":", 1)
try:
    socket.create_connection((host, int(port)), timeout=5).close()
except OSError:
    sys.exit(3)' >/dev/null 2>&1
    rc=$?
    if [ "$rc" -eq 3 ]; then
      echo "goat4_ready: no TCP connection to $addr within 5 s from a container on the Colima VM"; bad=1
    elif [ "$rc" -ne 0 ]; then
      echo "goat4_ready: the probe container did not run (docker exit $rc); TCP to $addr not tried"; bad=1
    fi
  fi

  # (e) no container of the step 1 project runs
  if [ -n "$(docker ps -q --filter label=com.docker.compose.project=apex-goat1 2>/dev/null)" ]; then
    echo "goat4_ready: containers of project apex-goat1 are running; stop them first (docker compose -p apex-goat1 down)"; bad=1
  fi

  [ "$bad" -eq 0 ]
}
