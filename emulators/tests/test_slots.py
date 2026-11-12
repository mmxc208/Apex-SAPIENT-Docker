import uuid

import pytest

from slots import RegistryError, fabric_anchor, parse_registry, pod_node_id

REGISTRY = '''
[pod1]
kind = "pod"
salt = "goat1-pod1"
pool_size = 8
site = "p1"
prefix = "h1/p1/"
router_cn = "router.p1.h1"
fusion_cn = "fusion.p1.h1"
fusion_node_id = "f0000001-0000-4000-8000-000000000001"
recorder_cn = "recorder.p1.h1"
bridge_cn = "podbridge.p1.h1"
[pod1.slots]
radar = 0
camera = 1
vehicle = 2

[fabric]
kind = "fabric"
salt = "goat1-fabric"
pool_size = 8
site = "h1"
router_cn = "router.fabric.h1"
[fabric.slots]
pod1 = 0
host-fusion = 1
host-recorder = 2
goat-cli = 3
'''


def test_fabric_anchor_is_goats_formula():
    assert fabric_anchor("goat1-fabric", 0) == "18214b1a34e3c722d1cac283b272a62c"
    assert fabric_anchor("goat1-fabric", 1) == "b005ae3a8f2baf89160bd71632902672"


def test_pod_node_id_is_a_canonical_version_4_uuid():
    assert pod_node_id("goat1-pod1", 0) == "1aef1b86-9b67-47a8-b565-2e40f235d2ba"
    assert pod_node_id("goat1-pod1", 2) == "341b9172-dc37-467a-add2-3ac5625e8682"
    assert uuid.UUID(pod_node_id("goat1-pod1", 5)).version == 4


def test_registry_resolves_aliases():
    routers = parse_registry(REGISTRY)
    assert routers["fabric"].alias_id("host-fusion") == "b005ae3a8f2baf89160bd71632902672"
    assert routers["pod1"].alias_id("camera") == "86ca6000-1c36-4aed-875f-ac18ec0b5ab2"
    assert routers["pod1"].slot_id(3) == "83ff6077-6265-4c97-9085-efcdbc04ebc0"


def test_unknown_alias_is_refused():
    with pytest.raises(RegistryError, match="nosuch"):
        parse_registry(REGISTRY)["pod1"].alias_id("nosuch")


@pytest.mark.parametrize("old, new, names", [
    ("camera = 1", "camera = 0", "camera"),             # two aliases on one slot
    ("vehicle = 2", "vehicle = 8", "vehicle"),          # outside the pool
    ('site = "p1"', 'site = "P/1"', "site"),            # not [a-z0-9]+
    ('site = "p1"', 'site = "' + "s" * 33 + '"', "site"),  # longer than 32 characters
    ('prefix = "h1/p1/"', 'prefix = "h1/p1"', "prefix"),  # must end with "/"
    ('salt = "goat1-fabric"', 'salt = "goat1-pod1"', "salt"),  # salts must differ
    ('kind = "fabric"', 'kind = "broker"', "kind"),
])
def test_registry_refuses_and_names_the_problem(old, new, names):
    with pytest.raises(RegistryError, match=names):
        parse_registry(REGISTRY.replace(old, new))


def test_registry_refuses_a_non_uuid_fusion_node_id():
    with pytest.raises(RegistryError, match="fusion_node_id"):
        parse_registry(REGISTRY.replace("f0000001-0000-4000-8000-000000000001", "not-a-uuid"))


def test_pod_table_missing_a_field_is_refused():
    with pytest.raises(RegistryError, match="bridge_cn"):
        parse_registry(REGISTRY.replace('bridge_cn = "podbridge.p1.h1"\n', ""))


def test_fabric_table_with_a_pod_field_is_refused():
    with pytest.raises(RegistryError, match="prefix"):
        parse_registry(REGISTRY.replace('site = "h1"', 'site = "h1"\nprefix = "x/"'))


def test_registry_accepts_a_site_of_32_characters():
    assert parse_registry(REGISTRY.replace('site = "p1"', 'site = "' + "s" * 32 + '"'))["pod1"].site == "s" * 32
