"""Tests for goat4/enroll.sh against a fake portal on 127.0.0.1.

Run from the repo root: python3 -m unittest goat4/test_enroll.py -v
Standard library and openssl only. The real portal is never contacted.
"""
import http.server
import io
import json
import os
import stat
import subprocess
import tarfile
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "enroll.sh")

OPERATOR_KEY = "op-key-7f3a91c2d4e65b80"
CUSTODIAN = "richard@cuaslab.lan"
MACHINES = [
    ("pod1-bridge", "pod1", "POD", "remote", "FABRIC_POD1_ID"),
    ("host-fusion", "host-fusion", "FUSION", "supervised", "FABRIC_HOST_FUSION_ID"),
    ("host-recorder", "host-recorder", "FUSION", "supervised", "FABRIC_HOST_RECORDER_ID"),
]
ANCHORS = {
    "pod1-bridge": "a1" * 16,
    "host-fusion": "b2" * 16,
    "host-recorder": "c3" * 16,
}
API_KEYS = {h: "apikey-secret-" + h for h in ANCHORS}
TOKENS = {h: "tok-secret-" + h for h in ANCHORS}


def make_cert(directory, anchor):
    cert = os.path.join(directory, anchor + "-cert.pem")
    key = os.path.join(directory, anchor + "-key.pem")
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
         "-nodes", "-keyout", key, "-out", cert, "-subj", "/CN=" + anchor, "-days", "2"],
        check=True, capture_output=True)
    return cert, key


class FakePortal:
    """State and behaviour of one fake portal; one instance per test."""

    def __init__(self, bundles, listed=(), grant_exists=False, refuse=None, no_mesh_key=False,
                 bundle_without_key=False):
        self.bundles = bundles          # anchor -> (cert path, key path, root path)
        self.listed = list(listed)      # handles that already hold a live slot
        self.grant_exists = grant_exists
        self.refuse = refuse            # (handle, status, code) to refuse
        self.no_mesh_key = no_mesh_key
        self.bundle_without_key = bundle_without_key
        self.requests = []              # (method, path, auth header, parsed body)
        self.lock = threading.Lock()
        portal = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send_json(self, status, obj):
                data = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def handle_any(self, method):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                auth = self.headers.get("Authorization")
                with portal.lock:
                    portal.requests.append((method, self.path, auth, body))
                if self.path.startswith("/api/org-bundle/"):
                    return self.bundle()
                if auth != "Bearer " + OPERATOR_KEY:
                    return self.send_json(401, {"code": "unauthorized"})
                if method == "GET" and self.path == "/api/machines":
                    return self.send_json(200, {"machines": [
                        {"system_handle": h, "slot_id": ANCHORS[h]} for h in portal.listed]})
                if method == "GET" and self.path == "/api/machines/grant/" + CUSTODIAN:
                    if portal.grant_exists:
                        return self.send_json(200, {"custodian": CUSTODIAN, "quota": 5})
                    return self.send_json(404, {"code": "no_grant"})
                if method == "POST" and self.path == "/api/machines/grant":
                    portal.grant_exists = True
                    return self.send_json(200, {"quota": body.get("quota")})
                if method == "POST" and self.path == "/api/machines/enroll":
                    return self.enroll(body)
                return self.send_json(404, {"code": "not_found"})

            def enroll(self, body):
                handle = body["machine_handle"]
                if portal.refuse and portal.refuse[0] == handle:
                    return self.send_json(portal.refuse[1], {"code": portal.refuse[2]})
                anchor = ANCHORS[handle]
                answer = {
                    "slot_id": anchor,
                    "api_key": API_KEYS[handle],
                    "bundle_token": TOKENS[handle],
                    "bundle_url": "/api/org-bundle/%s/%s" % (anchor, TOKENS[handle]),
                    "mesh_groups": [], "mesh_note": "n/a",
                }
                if not portal.no_mesh_key:
                    answer["mesh_setup_key"] = "mesh-secret-" + handle
                self.send_json(200, answer)

            def bundle(self):
                parts = self.path.split("/")
                anchor, token = parts[3], parts[4]
                handle = next((h for h, a in ANCHORS.items() if a == anchor), None)
                if handle is None or TOKENS[handle] != token:
                    return self.send_json(404, {"code": "bad_bundle"})
                cert, key, root = portal.bundles[anchor]
                buf = io.BytesIO()
                with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                    tar.add(cert, arcname=anchor + "-cert.pem")
                    if not portal.bundle_without_key:
                        tar.add(key, arcname=anchor + "-key.pem")
                    tar.add(root, arcname="root-cert.pem")
                    info = tarfile.TarInfo("profile.cbor")
                    info.size = 4
                    tar.addfile(info, io.BytesIO(b"\xa0\xa0\xa0\xa0"))
                data = buf.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", "application/gzip")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self.handle_any("GET")

            def do_POST(self):
                self.handle_any("POST")

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def calls(self, method, path):
        return [r for r in self.requests if r[0] == method and r[1] == path]


class EnrollTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keydir = tempfile.TemporaryDirectory()
        cls.bundles = {}
        root, _ = make_cert(cls.keydir.name, "ee" * 16)
        for anchor in ANCHORS.values():
            cert, key = make_cert(cls.keydir.name, anchor)
            cls.bundles[anchor] = (cert, key, root)

    @classmethod
    def tearDownClass(cls):
        cls.keydir.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "out")
        self.secrets = os.path.join(self.tmp.name, "secrets.env")
        self.write_secrets("OTHER=1\nCUASLAB_PORTAL_OPERATOR_API_KEY=%s\nTAIL=2\n" % OPERATOR_KEY)

    def write_secrets(self, text):
        with open(self.secrets, "w") as f:
            f.write(text)

    def portal(self, **kw):
        return FakePortal(self.bundles, **kw)

    def run_script(self, portal):
        return subprocess.run(
            ["/bin/bash", SCRIPT, self.secrets, "--portal", portal.url, "--out", self.out],
            capture_output=True, text=True, timeout=120)

    def pki(self, name):
        return os.path.join(self.out, "pki", name)

    def place_files(self, handle, with_key=True):
        stem = next(m[1] for m in MACHINES if m[0] == handle)
        cert, key, _ = self.bundles[ANCHORS[handle]]
        os.makedirs(os.path.join(self.out, "pki"), exist_ok=True)
        with open(cert) as s, open(self.pki(stem + ".pem"), "w") as d:
            d.write(s.read())
        if with_key:
            with open(key) as s, open(self.pki(stem + ".key"), "w") as d:
                d.write(s.read())

    def enrol_bodies(self, portal):
        return [r[3] for r in portal.calls("POST", "/api/machines/enroll")]

    def test_fresh_run(self):
        with self.portal() as portal:
            res = self.run_script(portal)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(self.enrol_bodies(portal), [
                {"machine_handle": h, "node_class": c, "autonomy": a, "custodian": CUSTODIAN}
                for h, _, c, a, _ in MACHINES])
            grants = portal.calls("POST", "/api/machines/grant")
            self.assertEqual([g[3] for g in grants], [
                {"custodian": CUSTODIAN, "quota": 5, "affiliation": "cuaslab-lab"}])
            for method, path, auth, _ in portal.requests:
                if not path.startswith("/api/org-bundle/"):
                    self.assertEqual(auth, "Bearer " + OPERATOR_KEY, path)
                else:
                    self.assertIsNone(auth)
        names = ["ca.pem", "pod1.pem", "pod1.key", "host-fusion.pem", "host-fusion.key",
                 "host-recorder.pem", "host-recorder.key"]
        for n in names:
            self.assertTrue(os.path.isfile(self.pki(n)), n)
        for n in names:
            if n.endswith(".key"):
                self.assertEqual(stat.S_IMODE(os.stat(self.pki(n)).st_mode), 0o600, n)
        with open(os.path.join(self.out, "goat4.env")) as f:
            lines = sorted(f.read().split())
        self.assertEqual(lines, sorted([
            "FABRIC_POD1_ID=" + ANCHORS["pod1-bridge"],
            "FABRIC_HOST_FUSION_ID=" + ANCHORS["host-fusion"],
            "FABRIC_HOST_RECORDER_ID=" + ANCHORS["host-recorder"]]))
        self.assertEqual(res.stdout.splitlines(), [
            "pod1-bridge " + ANCHORS["pod1-bridge"],
            "host-fusion " + ANCHORS["host-fusion"],
            "host-recorder " + ANCHORS["host-recorder"],
            "wrote %s/goat4.env" % self.out])
        self.assertEqual(sorted(os.listdir(self.out)), ["goat4.env", "pki"])
        self.assertEqual(len(os.listdir(os.path.join(self.out, "pki"))), 7)

    def test_output_has_no_secret(self):
        with self.portal() as portal:
            res = self.run_script(portal)
            self.assertEqual(res.returncode, 0, res.stderr)
        text = res.stdout + res.stderr
        forbidden = [OPERATOR_KEY, "/api/org-bundle/", "PRIVATE KEY", "mesh-secret-"]
        forbidden += list(API_KEYS.values()) + list(TOKENS.values())
        for s in forbidden:
            self.assertNotIn(s, text)

    def test_no_temp_files_left_behind(self):
        tmpdir = os.path.join(self.tmp.name, "scratch")
        os.mkdir(tmpdir)
        with self.portal() as portal:
            res = subprocess.run(
                ["/bin/bash", SCRIPT, self.secrets, "--portal", portal.url, "--out", self.out],
                capture_output=True, text=True, timeout=120, env=dict(os.environ, TMPDIR=tmpdir))
            self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(os.listdir(tmpdir), [])

    def test_second_run_enrols_nothing(self):
        with self.portal() as first:
            self.assertEqual(self.run_script(first).returncode, 0)
        with self.portal(listed=ANCHORS, grant_exists=True) as portal:
            res = self.run_script(portal)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(self.enrol_bodies(portal), [])
            self.assertEqual(portal.calls("POST", "/api/machines/grant"), [])
        self.assertEqual(len(res.stdout.splitlines()), 4)
        with open(os.path.join(self.out, "goat4.env")) as f:
            self.assertIn("FABRIC_HOST_FUSION_ID=" + ANCHORS["host-fusion"], f.read())

    def test_grant_exists_is_not_set_again(self):
        with self.portal(grant_exists=True) as portal:
            res = self.run_script(portal)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(portal.calls("POST", "/api/machines/grant"), [])
            self.assertEqual(len(self.enrol_bodies(portal)), 3)

    def test_handle_live_but_files_missing(self):
        self.place_files("pod1-bridge")
        with self.portal(listed=["pod1-bridge", "host-fusion"], grant_exists=True) as portal:
            res = self.run_script(portal)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("host-fusion", res.stderr)
            self.assertEqual(self.enrol_bodies(portal), [])
            self.assertEqual(portal.calls("POST", "/api/machines/grant"), [])
        self.assertFalse(os.path.exists(os.path.join(self.out, "goat4.env")))

    def test_handle_live_with_only_cert_file(self):
        self.place_files("host-fusion", with_key=False)
        with self.portal(listed=["host-fusion"]) as portal:
            res = self.run_script(portal)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("host-fusion", res.stderr)
            self.assertEqual(self.enrol_bodies(portal), [])

    def test_enrol_refused_stops(self):
        with self.portal(refuse=("host-fusion", 409, "alias_taken")) as portal:
            res = self.run_script(portal)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("host-fusion", res.stderr)
            self.assertIn("alias_taken", res.stderr)
            self.assertEqual([b["machine_handle"] for b in self.enrol_bodies(portal)],
                             ["pod1-bridge", "host-fusion"])
        self.assertFalse(os.path.exists(os.path.join(self.out, "goat4.env")))

    def test_bundle_without_pem_stops(self):
        with self.portal(bundle_without_key=True) as portal:
            res = self.run_script(portal)
            self.assertNotEqual(res.returncode, 0)
            self.assertEqual([b["machine_handle"] for b in self.enrol_bodies(portal)],
                             ["pod1-bridge"])
        self.assertFalse(os.path.exists(os.path.join(self.out, "goat4.env")))
        self.assertFalse(os.path.exists(self.pki("pod1.key")))

    def test_no_mesh_key_is_accepted(self):
        with self.portal(no_mesh_key=True) as portal:
            res = self.run_script(portal)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_secrets_file_without_key(self):
        self.write_secrets("OTHER=1\n# CUASLAB_PORTAL_OPERATOR_API_KEY=commented\n")
        with self.portal() as portal:
            res = self.run_script(portal)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("CUASLAB_PORTAL_OPERATOR_API_KEY", res.stderr)
            self.assertEqual(portal.requests, [])


if __name__ == "__main__":
    unittest.main()
