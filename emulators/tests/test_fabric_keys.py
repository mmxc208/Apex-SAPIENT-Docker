import pytest

from fabric_keys import (
    KINDS,
    FabricKey,
    key_for,
    live_key,
    live_subscription,
    parse,
    parse_live,
    subscriptions,
)

A = "18214b1a34e3c722d1cac283b272a62c"
N = "f0000001-0000-4000-8000-000000000001"


def test_each_class_has_its_exact_shape():
    assert key_for(A, "p1", "detection_report", N) == f"{A}/telemetry/sapient/p1/v2/detection_report/{N}"
    assert key_for(A, "p1", "task_ack", N) == f"{A}/ack/p1/sapient/v2/task_ack/{N}"
    assert key_for(A, "p1", "task", N) == f"{A}/task/p1/sapient/v2/task/{N}"
    assert live_key(A, "p1", N) == f"{A}/telemetry/sapient/p1/v2/live/{N}"


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_parse_reverses_key_for(kind):
    assert parse(key_for(A, "p1", kind, N)) == FabricKey(A, "p1", kind, N)


def test_parse_live():
    assert parse_live(live_key(A, "p1", N)) == FabricKey(A, "p1", "live", N)


@pytest.mark.parametrize("key", [
    f"{A.upper()}/telemetry/sapient/p1/v2/alert/{N}",      # upper-case anchor
    f"{A[:-1]}/telemetry/sapient/p1/v2/alert/{N}",         # short anchor
    f"{A}/telemetry/sapient/P1/v2/alert/{N}",              # bad site
    f"{A}/telemetry/sapient/p1/v1/alert/{N}",              # wrong version
    f"{A}/telemetry/sapient/p1/v2/task/{N}",               # task in the telemetry class
    f"{A}/ack/p1/sapient/v2/alert/{N}",                    # alert in the ack class
    f"{A}/telemetry/sapient/p1/v2/alert/{N.upper()}",      # node ID not canonical
    f"{A}/telemetry/sapient/p1/v2/alert/{N}/extra",
    f"{A}/telemetry/sapient/p1/v2/live/{N}",               # a live key is not a data key
    "h1/p1/sapient/v2/x/up/alert",
])
def test_parse_refuses(key):
    with pytest.raises(ValueError):
        parse(key)


@pytest.mark.parametrize("key", [
    f"{A}/telemetry/sapient/p1/v2/alert/{N}",
    f"{A}/telemetry/sapient/p1/v2/live/{N.upper()}",
    f"{A.upper()}/telemetry/sapient/p1/v2/live/{N}",
])
def test_parse_live_refuses(key):
    with pytest.raises(ValueError):
        parse_live(key)


def test_key_for_refuses_bad_parts():
    for bad in [("zz", "p1", "alert", N), (A, "p/1", "alert", N), (A, "p1", "live", N), (A, "p1", "alert", "x")]:
        with pytest.raises(ValueError):
            key_for(*bad)


def test_wildcards_are_only_for_subscriptions():
    with pytest.raises(ValueError):
        key_for("*", "p1", "alert", N)
    with pytest.raises(ValueError):
        live_key(A, "*", N)
    with pytest.raises(ValueError):
        subscriptions("zz")
    with pytest.raises(ValueError):
        live_subscription(site="P1")


def test_subscriptions_have_the_wildcard_in_the_first_part_only():
    assert subscriptions() == ("*/telemetry/sapient/*/v2/*/*", "*/ack/*/sapient/v2/*/*", "*/task/*/sapient/v2/task/*")
    assert subscriptions(A, "p1") == (f"{A}/telemetry/sapient/p1/v2/*/*", f"{A}/ack/p1/sapient/v2/*/*", f"{A}/task/p1/sapient/v2/task/*")
    assert live_subscription() == "*/telemetry/sapient/*/v2/live/*"


SITE_32 = "s" * 32


@pytest.mark.parametrize("site", ["s" * 33, "s" * 200])
def test_parse_and_parse_live_refuse_an_over_long_site(site):
    with pytest.raises(ValueError):
        parse(f"{A}/telemetry/sapient/{site}/v2/alert/{N}")
    with pytest.raises(ValueError):
        parse(f"{A}/ack/{site}/sapient/v2/task_ack/{N}")
    with pytest.raises(ValueError):
        parse_live(f"{A}/telemetry/sapient/{site}/v2/live/{N}")


def test_a_site_of_32_characters_is_accepted():
    assert parse(f"{A}/task/{SITE_32}/sapient/v2/task/{N}") == FabricKey(A, SITE_32, "task", N)
    assert parse_live(f"{A}/telemetry/sapient/{SITE_32}/v2/live/{N}") == FabricKey(A, SITE_32, "live", N)


def test_for_a_site_of_32_characters_every_kind_has_a_key():
    """The host builds its reply keys from a site it parsed: that must never raise."""
    for kind in sorted(KINDS):
        assert parse(key_for(A, SITE_32, kind, N)) == FabricKey(A, SITE_32, kind, N)
    assert parse_live(live_key(A, SITE_32, N)) == FabricKey(A, SITE_32, "live", N)


def test_key_for_and_the_subscriptions_refuse_an_over_long_site():
    with pytest.raises(ValueError):
        key_for(A, "s" * 33, "alert", N)
    with pytest.raises(ValueError):
        subscriptions(A, "s" * 33)
    with pytest.raises(ValueError):
        live_subscription(site="s" * 33)


def test_parse_refuses_a_key_longer_than_max_key_bytes(monkeypatch):
    import fabric_keys

    data, live = key_for(A, "p1", "alert", N), live_key(A, "p1", N)
    monkeypatch.setattr(fabric_keys, "MAX_KEY_BYTES", 64)
    with pytest.raises(ValueError, match="longer"):
        parse(data)
    with pytest.raises(ValueError, match="longer"):
        parse_live(live)
