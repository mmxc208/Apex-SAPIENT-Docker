# Shared by goat4b/run_g4b_06.sh, run_g4b_07.sh and run_g4b_08.sh (task 4). Sourced by zsh from
# the repo root. Sets the helpers and gives small readers. Changes nothing by itself.

# The Docker environment of the agent session that made the runs of task 4, if it is there. The
# file is git-ignored; without it the shell's own Docker environment is used, and nothing is printed.
_g4b_env=.superpowers/sdd/2026-11-18-goat-step4-cuaslab/docker-env.sh
[ -f "$_g4b_env" ] && . "$_g4b_env"
unset _g4b_env
. goat4/dg4.sh
. goat4b/host-vm.sh
. goat4b/dg4b.sh
set -a; . zenoh/goat4/goat4.env; set +a   # anchors and node IDs, no secret

G4B_HOST_CONTAINERS=(apex-goat4b-host-fusion-1 apex-goat4b-host-recorder-1)

utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
# UTC time <seconds> from now (may be negative or fractional), RFC 3339 with ms.
utc_in() { python3 -c 'import sys, time, datetime as d; print(d.datetime.fromtimestamp(time.time() + float(sys.argv[1]), d.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"))' "$1"; }
# A time plus <seconds>, both as RFC 3339; prints RFC 3339 with ms.
utc_add() { python3 -c 'import sys, datetime as d; t = d.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")) + d.timedelta(seconds=float(sys.argv[2])); print(t.astimezone(d.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"))' "$1" "$2"; }

# A sleep that a trapped signal ends at once (the trap runs then, not after the sleep).
pause() { sleep "$1" & wait $!; }

# Evidence header: UTC time and the commit.
header() { echo "$(utc) $(git rev-parse --short HEAD)"; }

# Through ssh, not the forwarded socket: that is down while lima-guestagent is stopped.
hostdocker() { limactl shell goathost sudo docker "$@" < /dev/null; }
# Today's (UTC on the VM's clock) file of the host recorder.
hostrec() { hostdocker exec apex-goat4b-host-recorder-1 sh -c 'cat /data/records/$(date -u +%Y-%m-%d).jsonl'; }

started_at() {
  hostdocker inspect -f '{{.Name}} {{.State.StartedAt}}' "${G4B_HOST_CONTAINERS[@]}"
  ( export DOCKER_HOST="$(_g4b_colima_sock)"
    docker ps -q --filter label=com.docker.compose.project=apex-goat4 \
      | xargs docker inspect -f '{{.Name}} {{.State.StartedAt}}' ) | sort
}
