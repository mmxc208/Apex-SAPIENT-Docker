import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from goatgen import env_lines, main, render_fabric_router, render_pod_router
from slots import fabric_anchor, parse_registry, pod_node_id
from test_slots import REGISTRY

HERE = Path(__file__).resolve().parent
CHECKER = HERE.parent / "third_party" / "goat" / "acl-evaluate.py"
GOLDEN = HERE / "golden"

FA, HA = "18214b1a34e3c722d1cac283b272a62c", "b005ae3a8f2baf89160bd71632902672"   # pod1 and host-fusion anchors
FREE = fabric_anchor("goat1-fabric", 7)                                            # a slot nobody holds
RADAR, CAMERA = "1aef1b86-9b67-47a8-b565-2e40f235d2ba", "86ca6000-1c36-4aed-875f-ac18ec0b5ab2"
FUSION = "f0000001-0000-4000-8000-000000000001"

needs_openssl = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl not installed")


def _checker():
    spec = importlib.util.spec_from_file_location("acl_evaluate", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def routers():
    return parse_registry(REGISTRY)


@pytest.fixture(scope="module")
def fabric_acl(routers):
    return _checker().Acl(render_fabric_router(routers["fabric"]))


@pytest.fixture(scope="module")
def pod_acl(routers):
    return _checker().Acl(render_pod_router(routers["pod1"]))


def test_checker_self_test_passes():
    result = subprocess.run([sys.executable, str(CHECKER), "--self-test"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-500:]


def test_fabric_list_decisions(fabric_acl):
    d = fabric_acl.decide_cn
    assert fabric_acl.unusable_key_exprs() == []
    assert d(FA, "put", "ingress", f"{FA}/telemetry/sapient/p1/v2/detection_report/{FUSION}") == "allow"
    assert d(FA, "liveliness_token", "ingress", f"{FA}/telemetry/sapient/p1/v2/live/{FUSION}") == "allow"
    assert d(FA, "put", "ingress", f"{HA}/task/p1/sapient/v2/task/{FUSION}") == "deny"
    assert d(HA, "put", "ingress", f"{HA}/task/p1/sapient/v2/task/{FUSION}") == "allow"
    assert d(HA, "put", "ingress", f"{FA}/telemetry/sapient/p1/v2/alert/{FUSION}") == "deny"
    assert d(FREE, "put", "ingress", f"{FREE}/telemetry/sapient/p2/v2/alert/{FUSION}") == "allow"
    assert d(HA, "declare_subscriber", "ingress", "*/telemetry/sapient/*/v2/*/*") == "allow"
    assert d(HA, "declare_subscriber", "ingress", "**") == "deny"
    assert d(HA, "declare_liveliness_subscriber", "ingress", "*/telemetry/sapient/*/v2/live/*") == "allow"
    assert d(HA, "put", "egress", f"{FA}/telemetry/sapient/p1/v2/alert/{FUSION}") == "allow"
    assert d("no-such-cn", "put", "ingress", f"{FA}/x") == "deny"


def test_pod_list_decisions(pod_acl):
    d = pod_acl.decide_cn
    assert pod_acl.unusable_key_exprs() == []
    assert d(RADAR, "put", "ingress", f"h1/p1/sapient/v2/{RADAR}/up/detection_report") == "allow"
    assert d(RADAR, "liveliness_token", "ingress", f"h1/p1/sapient/v2/live/{RADAR}") == "allow"
    assert d(RADAR, "put", "ingress", f"h1/p1/sapient/v2/{CAMERA}/up/detection_report") == "deny"
    assert d(RADAR, "declare_subscriber", "ingress", f"h1/p1/sapient/v2/{RADAR}/down/**") == "allow"
    assert d(RADAR, "declare_subscriber", "ingress", f"h1/p1/sapient/v2/{CAMERA}/down/**") == "deny"
    node = pod_node_id("goat1-pod1", 7)
    assert d(node, "put", "ingress", f"h1/p1/sapient/v2/{node}/up/status_report") == "allow"
    assert d("fusion.p1.h1", "put", "ingress", f"h1/p1/sapient/v2/{RADAR}/down/task") == "allow"
    assert d("fusion.p1.h1", "put", "ingress", "h1/p1/fusion/up/registration") == "allow"
    assert d("fusion.p1.h1", "put", "ingress", "h1/p1/fusion/down/task") == "deny"
    assert d("fusion.p1.h1", "declare_subscriber", "ingress", "h1/p1/fusion/down/**") == "allow"
    assert d("podbridge.p1.h1", "declare_subscriber", "ingress", "h1/p1/fusion/up/**") == "allow"
    assert d("podbridge.p1.h1", "put", "ingress", "h1/p1/fusion/down/task") == "allow"
    assert d("podbridge.p1.h1", "put", "ingress", "h1/p1/fusion/up/registration") == "deny"
    assert d("podbridge.p1.h1", "declare_subscriber", "ingress", "h1/p1/sapient/v2/**") == "deny"
    assert d("recorder.p1.h1", "declare_subscriber", "ingress", "h1/p1/sapient/v2/**") == "allow"
    assert d("recorder.p1.h1", "put", "ingress", f"h1/p1/sapient/v2/{RADAR}/up/alert") == "deny"


def test_rendered_lists_match_the_golden_files(routers):
    assert render_fabric_router(routers["fabric"]) == (GOLDEN / "router-fabric.json5").read_text()
    assert render_pod_router(routers["pod1"]) == (GOLDEN / "router-pod1.json5").read_text()


def test_env_lines(routers):
    lines = env_lines(routers)
    assert "POD1_RADAR_ID=1aef1b86-9b67-47a8-b565-2e40f235d2ba" in lines
    assert "FABRIC_HOST_FUSION_ID=b005ae3a8f2baf89160bd71632902672" in lines
    assert "FABRIC_POD1_ID=18214b1a34e3c722d1cac283b272a62c" in lines
    assert "POD1_FUSION_NODE_ID=f0000001-0000-4000-8000-000000000001" in lines


def _write_registry(tmp_path, text=REGISTRY):
    path = tmp_path / "registry.toml"
    path.write_text(text)
    return path


def _openssl(*args):
    return subprocess.run(["openssl", *args], capture_output=True, text=True)


def _subject_cn(pem):
    out = _openssl("x509", "-noout", "-subject", "-nameopt", "RFC2253", "-in", str(pem)).stdout.strip()
    return out.removeprefix("subject=").removeprefix("CN=")


def _tree(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@needs_openssl
def test_main_writes_router_files_env_and_verifiable_certificates(tmp_path):
    out = tmp_path / "out"
    assert main([str(_write_registry(tmp_path)), str(out)]) == 0
    assert (out / "router-pod1.json5").read_text() == (GOLDEN / "router-pod1.json5").read_text()
    assert (out / "router-fabric.json5").read_text() == (GOLDEN / "router-fabric.json5").read_text()
    assert f"POD1_RADAR_ID={RADAR}" in (out / "goat1.env").read_text().splitlines()
    pod = out / "pki" / "pod1"
    for name in ("ca", "router", "fusion", "recorder", "bridge", "radar", "camera", "vehicle"):
        assert (pod / f"{name}.pem").is_file() and (pod / f"{name}.key").is_file()
    assert _openssl("verify", "-CAfile", str(pod / "ca.pem"), str(pod / "radar.pem")).returncode == 0
    assert _subject_cn(pod / "radar.pem") == RADAR
    assert _subject_cn(out / "pki" / "fabric" / "pod1.pem") == FA
    router = out / "pki" / "fabric" / "router.pem"
    assert _subject_cn(router) == "router.fabric.h1"
    text = _openssl("x509", "-noout", "-ext", "subjectAltName,extendedKeyUsage", "-in", str(router)).stdout
    assert "DNS:router.fabric.h1" in text
    assert "TLS Web Server Authentication" in text and "TLS Web Client Authentication" in text
    # a certificate of one router does not verify under the other router's CA
    assert _openssl("verify", "-CAfile", str(out / "pki" / "fabric" / "ca.pem"), str(pod / "radar.pem")).returncode != 0


@needs_openssl
def test_second_run_keeps_every_certificate(tmp_path):
    registry, out = _write_registry(tmp_path), tmp_path / "out"
    assert main([str(registry), str(out)]) == 0
    before = _tree(out)
    assert main([str(registry), str(out)]) == 0
    assert _tree(out) == before


@needs_openssl
def test_new_alias_gets_only_its_certificate_and_routers_stay_frozen(tmp_path, capsys):
    registry, out = _write_registry(tmp_path), tmp_path / "out"
    assert main([str(registry), str(out)]) == 0
    before = _tree(out)
    _write_registry(tmp_path, REGISTRY.replace("vehicle = 2", "vehicle = 2\nradar2 = 3"))
    capsys.readouterr()
    assert main([str(registry), str(out), "--frozen-routers"]) == 0
    assert "router files unchanged" in capsys.readouterr().out
    after = _tree(out)
    assert _subject_cn(out / "pki" / "pod1" / "radar2.pem") == "83ff6077-6265-4c97-9085-efcdbc04ebc0"
    assert set(after) - set(before) == {"pki/pod1/radar2.pem", "pki/pod1/radar2.key"}
    for name in set(before) - {"goat1.env"}:
        assert after[name] == before[name], name


@needs_openssl
def test_frozen_routers_refuses_a_pool_change(tmp_path, capsys):
    registry, out = _write_registry(tmp_path), tmp_path / "out"
    assert main([str(registry), str(out)]) == 0
    before = _tree(out)
    _write_registry(tmp_path, REGISTRY.replace('salt = "goat1-pod1"\npool_size = 8', 'salt = "goat1-pod1"\npool_size = 9'))
    capsys.readouterr()
    assert main([str(registry), str(out), "--frozen-routers"]) == 3
    assert "router-pod1.json5" in capsys.readouterr().err
    assert _tree(out) == before


def test_registry_error_writes_nothing(tmp_path):
    out = tmp_path / "out"
    registry = _write_registry(tmp_path, REGISTRY.replace("camera = 1", "camera = 0"))
    assert main([str(registry), str(out)]) == 2
    assert not out.exists() or not any(out.iterdir())


@pytest.mark.parametrize("alias, kind_table", [
    ("ca", "fabric"), ("router", "fabric"), ("ca", "pod1"), ("router", "pod1"), ("fusion", "pod1"),
    ('"../x"', "fabric"), ('"a/b"', "pod1"), ('"Radar"', "pod1"), ('"host_fusion"', "fabric"),
])
def test_unsafe_or_reserved_alias_writes_nothing(tmp_path, capsys, alias, kind_table):
    out = tmp_path / "out"
    text = REGISTRY.replace(f"[{kind_table}.slots]\n", f"[{kind_table}.slots]\n{alias} = 7\n")
    assert main([str(_write_registry(tmp_path, text)), str(out)]) == 2
    assert alias.strip('"') in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


def test_a_site_of_33_characters_writes_nothing(tmp_path, capsys):
    out = tmp_path / "out"
    registry = _write_registry(tmp_path, REGISTRY.replace('site = "h1"', 'site = "' + "h" * 33 + '"'))
    assert main([str(registry), str(out)]) == 2
    assert "site" in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())
