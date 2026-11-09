from importlib.metadata import version


def test_zenoh_importable():
    import zenoh
    assert callable(zenoh.open)
    assert version("eclipse-zenoh").startswith("1.10")  # the binding has no zenoh.__version__


def test_templates_load(templates):
    assert templates("sensor", "Registration").WhichOneof("content") == "registration"
