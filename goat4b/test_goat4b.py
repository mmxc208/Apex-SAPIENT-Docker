"""Tests for goat4b/dg4b.sh, goat4b/host-vm.sh and docker-compose.goat4b.yml, with no VM.

Run from the repo root: python3 -m unittest goat4b/test_goat4b.py -v
The shell functions run in zsh with `docker`, `limactl` and `colima` replaced by stubs on PATH
that record their arguments. No real engine or VM is touched.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OVERLAY = os.path.join(ROOT, "docker-compose.goat4b.yml")

POD_SERVICES = "zenohd-pod fusion-node radar camera vehicle bridge-node recorder pod-bridge".split()
HOST_SERVICES = ["host-fusion", "host-recorder"]
FIVE = ["ca.pem", "host-fusion.pem", "host-fusion.key", "host-recorder.pem", "host-recorder.key"]

STUB = r'''#!/bin/sh
# Records "<tool> <args>  DOCKER_HOST=<..> HOLD=<..> CONFIG=<..>" and answers from environment
# variables. Standard input, if any is piped, is appended to "$STUB_LOG.stdin".
tool=$(basename "$0")
echo "$tool $* DOCKER_HOST=${DOCKER_HOST-unset} HOLD=${HOST_HOLD_SECONDS-unset} CONFIG=${DOCKER_CONFIG-unset}" >> "$STUB_LOG"
[ -t 0 ] || cat >> "$STUB_LOG.stdin"
case "$tool $*" in
  "docker image inspect"*) echo sha256:aaa ;;
  "docker ps"*) ;;
  "docker save"*) echo layer-bytes ;;
  "limactl list --format"*) echo "${STUB_STATUS:-Running}" ;;
  "limactl list -q"*) printf '%s\n' ${STUB_LIST:-goathost goatlite} ;;
  "limactl shell goathost ip -4 -o addr show"*)
    echo "2: lima0    inet ${STUB_VM_ADDR:-192.168.64.7}/24 brd 192.168.64.255 scope global lima0" ;;
  "limactl shell goathost sudo ls -1 /opt/apex-host/pki"*)
    printf '%s\n' ${STUB_PKI_LS:-ca.pem host-fusion.pem host-fusion.key host-recorder.pem host-recorder.key} ;;
  "limactl shell goathost sudo docker ps"*) printf '%s\n' ${STUB_VM_PS:-}; exit ${STUB_VM_PS_RC:-0} ;;
  "limactl shell goathost sudo find"*) printf '%s\n' ${STUB_FIND:-} ;;
  "limactl shell goathost sudo sh -c stat"*)
    printf '%s\n' "${STUB_KEY_STAT:-600 root host-fusion.key}" "600 root host-recorder.key" ;;
  "limactl shell goathost sudo docker image inspect"*) echo sha256:aaa ;;
  "limactl shell goathost ip route show"*) echo "192.168.64.4 via 192.168.64.1 dev lima0" ;;
  "limactl shell goathost systemctl is-active lima-guestagent"*) echo "${STUB_GA:-active}" ;;
  "limactl shell goathost systemctl"*) echo "${STUB_TS:-active}" ;;
  "limactl shell goathost date"*) [ -n "${STUB_VM_DATE:-}" ] && echo "$STUB_VM_DATE" ;;
  "limactl shell goathost ip route get"*) echo "192.168.64.4 via 192.168.64.1 dev lima0 src 192.168.64.7" ;;
  "limactl shell goatlite ip route show"*) echo "${STUB_VM_ADDR:-192.168.64.7} via 192.168.64.1 dev lima0" ;;
  "limactl shell goatlite sudo cat"*)
    printf 'network:\n  ethernets:\n    lima0:\n      routes:\n        - to: %s/32\n          via: 192.168.64.1\n' "${STUB_GL_ADDR:-192.168.64.7}" ;;
esac
exit 0
'''


class Shell:
    def __init__(self, tc):
        self.tmp = tempfile.mkdtemp()
        tc.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = os.path.join(self.tmp, "bin")
        os.mkdir(self.bin)
        for tool in ("docker", "limactl", "colima"):
            path = os.path.join(self.bin, tool)
            with open(path, "w") as f:
                f.write(STUB)
            os.chmod(path, 0o755)
        self.log = os.path.join(self.tmp, "calls.log")
        open(self.log, "w").close()

    def run(self, body, **env):
        script = (". goat4/dg4.sh; . goat4b/dg4b.sh; . goat4b/host-vm.sh; "
                  "goat4_ready() { return 0; }; " + body)
        e = dict(os.environ, STUB_LOG=self.log, PATH=self.bin + os.pathsep + os.environ["PATH"])
        e.pop("HOST_HOLD_SECONDS", None)
        e.pop("G4B_ENGINE", None)
        e.update(env)
        p = subprocess.run(["zsh", "-fc", script], cwd=ROOT, env=e, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def calls(self):
        with open(self.log) as f:
            return f.read().splitlines()


def read_overlay():
    """Minimal reader of the overlay: {service: {key: [list items]}}."""
    out, svc, key = {}, None, None
    in_services = False
    with open(OVERLAY) as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            text = line.strip()
            if indent == 0:
                in_services = text == "services:"
            elif in_services and indent == 2 and text.endswith(":"):
                svc, key = text[:-1], None
                out[svc] = {}
            elif in_services and indent == 4 and text.endswith(":"):
                key = text[:-1]
                out[svc][key] = []
            elif in_services and indent == 6 and text.startswith("- "):
                out[svc][key].append(text[2:])
            else:
                raise AssertionError("overlay line not understood: " + line)
    return out


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.sh = Shell(self)

    def test_host_files_are_exactly_five_and_no_pod_key(self):
        rc, out = self.sh.run('printf "%s\\n" "${G4B_HOST_FILES[@]}"')
        self.assertEqual(rc, 0, out)
        names = out.split()
        self.assertEqual(sorted(names), sorted(FIVE))
        self.assertFalse([n for n in names if "pod1" in n])

    def test_dg4b_pod_up_refuses_no_service(self):
        rc, out = self.sh.run("dg4b_pod up -d")
        self.assertEqual(rc, 1)
        self.assertIn("refused", out)
        self.assertEqual(self.sh.calls(), [])

    def test_dg4b_pod_up_refuses_host_service(self):
        rc, out = self.sh.run("dg4b_pod up -d radar host-fusion")
        self.assertEqual(rc, 1)
        self.assertIn("host-fusion", out)
        self.assertEqual(self.sh.calls(), [])

    def test_dg4b_pod_up_all_names_eight_services(self):
        rc, out = self.sh.run("dg4b_pod up-all")
        self.assertEqual(rc, 0, out)
        (call,) = self.sh.calls()
        words = call.split()
        self.assertEqual(words[words.index("up"):words.index("up") + 2], ["up", "-d"])
        tail = words[words.index("-d") + 1:-3]  # drop DOCKER_HOST=, HOLD= and CONFIG=
        self.assertEqual(sorted(tail), sorted(POD_SERVICES))
        self.assertNotIn("host-recorder", words)

    def test_dg4b_pod_passes_other_subcommands_unchanged(self):
        rc, out = self.sh.run("dg4b_pod logs --tail 5 radar")
        self.assertEqual(rc, 0, out)
        (call,) = self.sh.calls()
        self.assertIn(" logs --tail 5 radar DOCKER_HOST=", call)

    def test_dg4b_host_up_refuses_pod_service(self):
        rc, out = self.sh.run("dg4b_host up -d radar")
        self.assertEqual(rc, 1)
        self.assertIn("radar", out)
        self.assertEqual(self.sh.calls(), [])

    def test_dg4b_host_up_refuses_no_service(self):
        rc, _ = self.sh.run("dg4b_host up -d")
        self.assertEqual(rc, 1)
        self.assertEqual(self.sh.calls(), [])

    def test_dg4b_host_up_adds_no_deps(self):
        rc, out = self.sh.run("dg4b_host up -d host-fusion host-recorder")
        self.assertEqual(rc, 0, out)
        (call,) = self.sh.calls()
        self.assertIn(" up --no-deps -d host-fusion host-recorder ", call)

    def test_dg4b_host_passes_hold_seconds(self):
        rc, _ = self.sh.run("dg4b_host up -d host-fusion", HOST_HOLD_SECONDS="45")
        self.assertEqual(rc, 0)
        self.assertIn(" HOLD=45 ", self.sh.calls()[0])
        # shell engine: passed through sudo env
        self.sh = Shell(self)
        rc, _ = self.sh.run("G4B_ENGINE=shell; dg4b_host up -d host-fusion", HOST_HOLD_SECONDS="45")
        self.assertEqual(rc, 0)
        (call,) = self.sh.calls()
        self.assertIn("limactl shell --workdir /opt/apex-host/compose goathost sudo env HOST_HOLD_SECONDS=45 docker compose", call)

    def test_projects_differ(self):
        self.sh.run("dg4b_pod ps")
        self.sh.run("dg4b_host ps")
        pod, host = self.sh.calls()
        self.assertIn("-p apex-goat4 ", pod)
        self.assertIn("-p apex-goat4b ", host)

    def test_engines_differ_and_caller_shell_is_unchanged(self):
        rc, out = self.sh.run('dg4b_pod ps; dg4b_host ps; echo "after=${DOCKER_HOST-unset}"',
                              DOCKER_HOST="unix:///caller.sock")
        pod, host = self.sh.calls()
        self.assertIn("DOCKER_HOST=unix://%s/.colima/default/docker.sock" % os.environ["HOME"], pod)
        self.assertIn("DOCKER_HOST=unix://%s/.lima/goathost/sock/docker.sock" % os.environ["HOME"], host)
        self.assertIn("after=unix:///caller.sock", out)

    def test_docker_config_of_caller_is_kept(self):
        rc, out = self.sh.run("dg4b_pod ps; dg4b_host ps", DOCKER_CONFIG="/x/cfg")
        self.assertEqual(rc, 0, out)
        pod, host = self.sh.calls()
        self.assertTrue(pod.endswith(" CONFIG=/x/cfg"), pod)
        self.assertTrue(host.endswith(" CONFIG=/x/cfg"), host)

    def test_key_files_are_written_under_umask_077(self):
        rc, out = self.sh.run("g4b_vm_sync")
        self.assertEqual(rc, 0, out)
        keys = [c for c in self.sh.calls() if ".key" in c and "cat >" in c]
        self.assertEqual(len(keys), 2, keys)
        for c in keys:
            self.assertIn("umask 077", c)
            self.assertLess(c.index("umask 077"), c.index("cat >"), c)

    def test_sync_refuses_while_host_services_run(self):
        # seen live: replacing /opt/apex-host/emulators under a running host-fusion left its
        # working directory outside the mount, and it stopped logging
        rc, out = self.sh.run("g4b_vm_sync", STUB_VM_PS="0123abcd")
        self.assertEqual(rc, 1, out)
        self.assertIn("dg4b_host stop", out)
        calls = "\n".join(self.sh.calls())
        self.assertIn("label=com.docker.compose.project=apex-goat4b", calls)
        for bad in ("rm -rf", "tar", "cat >"):
            self.assertNotIn(bad, calls)

    def test_sync_refuses_when_running_services_cannot_be_listed(self):
        rc, out = self.sh.run("g4b_vm_sync", STUB_VM_PS_RC="1")
        self.assertEqual(rc, 1, out)
        self.assertIn("cannot list", out)
        calls = "\n".join(self.sh.calls())
        for bad in ("rm -rf", "tar", "cat >"):
            self.assertNotIn(bad, calls)

    def test_sync_tar_stream_holds_no_mac_metadata(self):
        # GNU tar in the VM warns once per file on macOS extended headers (seen live)
        rc, out = self.sh.run("g4b_vm_sync")
        self.assertEqual(rc, 0, out)
        with open(self.sh.log + ".stdin", "rb") as f:
            stream = f.read()
        self.assertIn(b"fake_fusion_node.py", stream)
        self.assertFalse(b"LIBARCHIVE.xattr" in stream or b"SCHILY.xattr" in stream,
                         "the tar stream carries macOS extended attributes")

    def test_load_image_uses_colima_engine_not_callers(self):
        rc, out = self.sh.run("g4b_vm_load_image", DOCKER_HOST="unix:///caller.sock")
        self.assertEqual(rc, 0, out)
        colima = "DOCKER_HOST=unix://%s/.colima/default/docker.sock" % os.environ["HOME"]
        docker_calls = [c for c in self.sh.calls() if c.startswith("docker ")]
        self.assertEqual([c.split()[1] for c in docker_calls], ["save", "image"])
        for c in docker_calls:
            self.assertIn(colima, c)

    def test_routes_up_writes_the_vm_route_file_and_reads_goatlite_back(self):
        rc, out = self.sh.run("g4b_routes_up", STUB_VM_ADDR="192.168.64.7", STUB_GL_ADDR="192.168.64.7")
        self.assertEqual(rc, 0, out)
        calls = "\n".join(self.sh.calls())
        self.assertIn("limactl shell goathost sudo sh -c", calls)
        self.assertIn("/etc/netplan/90-cuaslab-route.yaml", calls)
        with open(self.sh.log + ".stdin") as f:
            written = f.read()
        self.assertIn("- to: 192.168.64.4/32", written)
        self.assertIn("- to: 192.168.64.7/32", written)

    def test_routes_up_fails_when_goatlite_file_does_not_read_back(self):
        rc, out = self.sh.run("g4b_routes_up", STUB_VM_ADDR="192.168.64.7", STUB_GL_ADDR="192.168.64.9")
        self.assertEqual(rc, 1, out)
        self.assertIn("192.168.64.9", out)

    def test_engine_default_is_socket(self):
        # Task 2 measured that the forwarded socket works from the agent's shell
        rc, out = self.sh.run('dg4b_host ps; echo "engine=$G4B_ENGINE"')
        self.assertEqual(rc, 0, out)
        self.assertIn("engine=socket", out)
        (call,) = self.sh.calls()
        self.assertTrue(call.startswith("docker compose -p apex-goat4b "), call)
        self.assertIn("DOCKER_HOST=unix://%s/.lima/goathost/sock/docker.sock" % os.environ["HOME"], call)

    def test_bad_engine_is_refused(self):
        rc, out = self.sh.run("G4B_ENGINE=bogus; dg4b_host ps")
        self.assertEqual(rc, 1)
        self.assertEqual(self.sh.calls(), [])

    def test_vm_remove_needs_yes(self):
        rc, out = self.sh.run("g4b_vm_remove")
        self.assertEqual(rc, 0, out)
        self.assertIn("would remove", out)
        calls = "\n".join(self.sh.calls())
        for bad in ("limactl delete", "limactl stop", "rm -f", "route del"):
            self.assertNotIn(bad, calls)
        rc, out = self.sh.run("g4b_vm_remove --yes")
        self.assertEqual(rc, 0, out)
        self.assertIn("limactl delete --force goathost", "\n".join(self.sh.calls()))

    def test_ready_passes_with_everything_in_place(self):
        rc, out = self.sh.run("goat4b_ready")
        self.assertEqual(rc, 0, out)

    def test_ready_fails_on_pod_key_in_vm(self):
        rc, out = self.sh.run("goat4b_ready",
                              STUB_PKI_LS="ca.pem host-fusion.pem host-fusion.key host-recorder.pem host-recorder.key pod1.key",
                              STUB_FIND="/opt/apex-host/pki/pod1.key")
        self.assertEqual(rc, 1)
        self.assertIn("pod1 file is in goathost", out)

    def test_ready_fails_on_key_not_0600(self):
        rc, out = self.sh.run("goat4b_ready", STUB_KEY_STAT="644 root host-fusion.key")
        self.assertEqual(rc, 1)
        self.assertIn("host-fusion.key is mode 644 owner root", out)

    def test_ready_fails_on_key_not_owned_by_root(self):
        rc, out = self.sh.run("goat4b_ready", STUB_KEY_STAT="600 lima host-fusion.key")
        self.assertEqual(rc, 1)
        self.assertIn("host-fusion.key is mode 600 owner lima", out)

    def test_ready_fails_on_missing_identity_file(self):
        rc, out = self.sh.run("goat4b_ready", STUB_PKI_LS="ca.pem")
        self.assertEqual(rc, 1)
        self.assertIn("host-fusion.key is missing", out)

    def test_ready_fails_on_route_address_mismatch(self):
        rc, out = self.sh.run("goat4b_ready", STUB_VM_ADDR="192.168.64.7", STUB_GL_ADDR="192.168.64.9")
        self.assertEqual(rc, 1)
        self.assertIn("address mismatch", out)
        self.assertIn("192.168.64.7", out)
        self.assertIn("192.168.64.9", out)

    def test_ready_fails_when_vm_is_stopped(self):
        rc, out = self.sh.run("goat4b_ready", STUB_STATUS="Stopped")
        self.assertEqual(rc, 1)
        self.assertIn("not running", out)

    def test_state_prints_six_lines_and_changes_nothing(self):
        rc, out = self.sh.run("g4b_state")
        self.assertEqual(rc, 0, out)
        lines = [l for l in out.splitlines() if l.strip()]
        # time service, Lima's time sync, two offsets, two routes
        self.assertEqual(len(lines), 6, out)
        self.assertIn("active", lines[0])
        for c in self.sh.calls():
            for bad in ("sudo", "date -s", "route add", "route replace", " stop", "restart", "delete"):
                self.assertNotIn(bad, c)

    def test_state_shows_time_service_and_lima_sync(self):
        rc, out = self.sh.run("g4b_state", STUB_TS="inactive", STUB_GA="inactive")
        self.assertEqual(rc, 0, out)
        self.assertIn("goathost time service (systemd-timesyncd): inactive", out)
        self.assertIn("goathost Lima time sync (lima-guestagent): inactive", out)
        rc, out = self.sh.run("g4b_state")
        self.assertIn("goathost Lima time sync (lima-guestagent): active", out)

    def test_state_offset_has_a_bound(self):
        rc, out = self.sh.run("g4b_state", STUB_VM_DATE="1000.5")
        self.assertEqual(rc, 0, out)
        line = [l for l in out.splitlines() if l.startswith("offset of goathost")][0]
        self.assertRegex(line, r"^offset of goathost from the Mac \(ms\): [-+]\d+ \(bound \+/-\d+, best of \d+\)$")
        # no answer: unknown, not a number
        self.assertIn("offset of colima from the Mac (ms): unknown", out)

    def test_vm_addr_prints_only_the_address(self):
        rc, out = self.sh.run("g4b_vm_addr", STUB_VM_ADDR="192.168.64.12")
        self.assertEqual((rc, out.strip()), (0, "192.168.64.12"))


class OverlayTests(unittest.TestCase):
    def test_overlay_changes_only_host_mount_sources(self):
        ov = read_overlay()
        self.assertEqual(sorted(ov), sorted(HOST_SERVICES))
        for svc, body in ov.items():
            self.assertEqual(list(body), ["volumes"], svc)
            targets = []
            for item in body["volumes"]:
                src, tgt = item.split(":")[:2]
                self.assertTrue(src.startswith("/opt/apex-host/"), item)
                targets.append(tgt)
            self.assertEqual(sorted(targets),
                             sorted(["/emulators", "/certs/ca.pem", "/certs/%s.pem" % svc, "/certs/%s.key" % svc]))

    @unittest.skipUnless(shutil.which("docker") and os.path.exists(os.path.join(ROOT, "zenoh/goat4/goat4.env")),
                         "needs the docker compose CLI and the gitignored env files")
    def test_merged_config_has_no_mac_path_in_host_mounts(self):
        e = dict(os.environ)
        e.pop("DOCKER_HOST", None)
        p = subprocess.run(
            ["docker", "compose", "-p", "apex-goat4b",
             "--env-file", "zenoh/goat1/goat1.env", "--env-file", "zenoh/goat4/goat4.env",
             "-f", "docker-compose.goat1.yml", "-f", "docker-compose.goat4.yml",
             "-f", "docker-compose.goat4b.yml", "config", "--format", "json"],
            cwd=ROOT, env=e, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        services = json.loads(p.stdout)["services"]
        for svc in HOST_SERVICES:
            binds = [v for v in services[svc]["volumes"] if v["type"] == "bind"]
            self.assertEqual(len(binds), 4, svc)
            for v in binds:
                self.assertTrue(v["source"].startswith("/opt/apex-host/"), (svc, v["source"]))
                self.assertFalse(v["source"].startswith(ROOT))
        # pod services still mount from the Mac's repository
        self.assertTrue(any(v["source"].startswith(ROOT)
                            for v in services["pod-bridge"]["volumes"] if v["type"] == "bind"))


# ------------------------------------------------------------------ readers.py (no rig needed)
import sys
sys.path.insert(0, HERE)
import readers  # noqa: E402

POD = "7a640b349ac2e03848531fce2000fc57"
HOSTA = "cd42939f9c6719ea485ed176909d6d64"


def rec(t, kind, ts=None, task_id=None, frm="f0000002-x", to="f0000001-x", anchor=POD):
    """A recorder record: t is HH:MM:SS.fff on 2026-11-19; ts the message time, same form."""
    msg = {"timestamp": "2026-11-19T%sZ" % (ts or t), "node_id": frm, "destination_id": to}
    if kind == "task":
        msg["task"] = {"task_id": task_id, "task_name": "x"}
    elif kind == "task_ack":
        msg["task_ack"] = {"task_id": task_id, "task_status": "TASK_STATUS_ACCEPTED"}
    else:
        msg[kind] = {"report_id": "r"}
    return {"t": "2026-11-19T%s+00:00" % t, "key": "%s/x/%s" % (anchor, kind), "kind": kind,
            "node_id": to, "anchor": anchor, "site": "p1", "msg": msg}


class ReaderTests(unittest.TestCase):
    def test_follow_task_finds_task_and_ack_by_suffix(self):
        rows = [rec("12:00:00.000", "task", task_id="01M7SWAAAAAAAAAAAAAAN5KW8C", anchor=HOSTA),
                rec("12:00:00.010", "detection_report"),
                rec("12:00:00.020", "task_ack", task_id="01M7SWAAAAAAAAAAAAAAN5KW8C",
                    frm="f0000001-x", to="f0000002-x"),
                rec("12:00:20.000", "task", task_id="01M7SWBBBBBBBBBBBBBBZZZZZZ", anchor=HOSTA)]
        got = readers.follow_task(rows, "N5KW8C")
        self.assertEqual([g["content"] for g in got], ["task", "task_ack"])
        self.assertEqual(got[0]["task_id"], "01M7SWAAAAAAAAAAAAAAN5KW8C")
        self.assertEqual((got[0]["from"], got[0]["to"]), ("f0000002-x", "f0000001-x"))
        self.assertEqual((got[1]["from"], got[1]["to"]), ("f0000001-x", "f0000002-x"))
        self.assertEqual(got[1]["t"], "2026-11-19T12:00:00.020+00:00")
        self.assertTrue(got[0]["key"].startswith(HOSTA))

    def test_apparent_ages(self):
        rows = [rec("12:00:00.000", "detection_report", ts="12:00:00.050"),   # -0.05
                rec("12:00:01.000", "detection_report", ts="12:00:00.800"),   # 0.2
                rec("12:00:03.000", "status_report", ts="12:00:02.000")]      # 1.0
        a = readers.apparent_ages(rows)
        self.assertEqual(a["count"], 3)
        self.assertAlmostEqual(a["min"], -0.05)
        self.assertAlmostEqual(a["median"], 0.2)
        self.assertAlmostEqual(a["max"], 1.0)
        self.assertEqual((a["below_zero"], a["outside_window"]), (1, 1))

    def test_apparent_ages_since_until_and_kinds(self):
        rows = [rec("12:00:00.000", "detection_report", ts="11:59:59.900"),
                rec("12:00:01.000", "status_report", ts="12:00:00.700"),
                rec("12:00:02.000", "detection_report", ts="12:00:01.000")]
        a = readers.apparent_ages(rows, since="2026-11-19T12:00:00.500+00:00")
        self.assertEqual(a["count"], 2)
        a = readers.apparent_ages(rows, until="2026-11-19T12:00:01.500+00:00")
        self.assertEqual(a["count"], 2)
        a = readers.apparent_ages(rows, kinds=["detection_report"])
        self.assertEqual(a["count"], 2)
        self.assertAlmostEqual(a["max"], 1.0)
        self.assertEqual(readers.apparent_ages([])["count"], 0)

    def test_apparent_ages_skips_undecoded_records(self):
        rows = [rec("12:00:00.000", "detection_report", ts="11:59:59.900"),
                {"t": "2026-11-19T12:00:00.100+00:00", "key": "k", "error": "decode", "payload_b64": ""}]
        self.assertEqual(readers.apparent_ages(rows)["count"], 1)

    def test_task_latency(self):
        rows = [rec("12:00:00.000", "task", task_id="A1", anchor=HOSTA),
                rec("12:00:00.007", "task_ack", task_id="A1"),
                rec("12:00:20.000", "task", task_id="B2", anchor=HOSTA)]
        lat = readers.task_latency(rows)
        self.assertEqual(lat["count"], 1)
        self.assertAlmostEqual(lat["median"], 7)
        self.assertAlmostEqual(lat["min"], 7)
        self.assertAlmostEqual(lat["max"], 7)
        self.assertEqual(lat["unacknowledged"], 1)

    def test_rejections_counts_both_forms_and_honours_since(self):
        lines = [
            "host-fusion-1  | 12:00:01 fusion: invalid message from 'f0000001' dropped: too old",
            "host-fusion-1  | 12:00:05 fusion: <- detection_report f0000001",
            "fusion-node-1  | 12:00:09 fusion: invalid message from above dropped: too old",
            "fusion-node-1  | 12:00:12 fusion: invalid message from above dropped: too new",
        ]
        r = readers.rejections(lines)
        self.assertEqual(r["invalid message from"], 3)
        self.assertEqual(r["invalid message from above dropped"], 2)
        r = readers.rejections(lines, since="12:00:05")
        self.assertEqual(r["invalid message from"], 2)
        self.assertEqual(r["invalid message from above dropped"], 2)
        r = readers.rejections(lines, since="12:00:05", until="12:00:10")
        self.assertEqual(r["invalid message from above dropped"], 1)

    def test_judge_step(self):
        inside = {"count": 40, "min": 0.1, "median": 0.3, "max": 0.5}
        outside = {"count": 40, "min": 1.0, "median": 1.2, "max": 1.4}
        both = {"count": 40, "min": 0.5, "median": 0.9, "max": 1.3}
        self.assertEqual(readers.judge_step(inside, accepted=40, rejected=0), "pass")
        self.assertEqual(readers.judge_step(inside, accepted=37, rejected=3), "fail")
        self.assertEqual(readers.judge_step(outside, accepted=0, rejected=40), "pass")
        self.assertEqual(readers.judge_step(outside, accepted=5, rejected=35), "fail")
        self.assertEqual(readers.judge_step(both, accepted=20, rejected=20), "not judged")
        few = dict(inside, count=5)
        self.assertEqual(readers.judge_step(few, accepted=5, rejected=0), "not judged")
        future = {"count": 40, "min": -0.4, "median": -0.3, "max": -0.2}
        self.assertEqual(readers.judge_step(future, accepted=0, rejected=40), "pass")
        straddle_low = {"count": 40, "min": -0.2, "median": 0.0, "max": 0.1}
        self.assertEqual(readers.judge_step(straddle_low, accepted=30, rejected=10), "not judged")

    def test_main_ages_by_anchor_from_stdin(self):
        rows = [rec("12:00:00.300", "detection_report", ts="12:00:00.000"),
                rec("12:00:00.300", "detection_report", ts="12:00:00.300", anchor=HOSTA)]
        p = subprocess.run([sys.executable, os.path.join(HERE, "readers.py"), "ages", "--anchor", POD],
                           input="\n".join(json.dumps(r) for r in rows) + "\n",
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("count 1", p.stdout)
        self.assertIn("median 0.300", p.stdout)


if __name__ == "__main__":
    unittest.main()
