"""The TCP path must keep working on a host with only protobuf and ulid installed (README venv)."""
import asyncio
import importlib
import struct
import sys

import pytest

import fake_sensor  # noqa: F401  so that the modules this test re-imports are restored afterwards
import sapient_link  # noqa: F401
import zenoh_io  # noqa: F401
import zenoh_keys  # noqa: F401

NODE = "a0000001-0000-4000-8000-000000000001"


@pytest.fixture
def without_zenoh(monkeypatch):
    monkeypatch.setitem(sys.modules, "zenoh", None)  # import zenoh now raises ImportError
    for name in ("sapient_link", "fake_sensor", "zenoh_io", "zenoh_keys"):
        monkeypatch.delitem(sys.modules, name)


@pytest.mark.usefixtures("without_zenoh")
def test_zenoh_really_is_blocked():
    with pytest.raises(ImportError):
        importlib.import_module("zenoh_io")


@pytest.mark.usefixtures("without_zenoh")
def test_the_tcp_sensor_imports_without_zenoh():
    assert importlib.import_module("fake_sensor").TRANSPORTS == ("tcp", "zenoh")


@pytest.mark.usefixtures("without_zenoh")
async def test_tcp_link_carries_a_message_without_zenoh():
    link_module = importlib.import_module("sapient_link")
    received = asyncio.get_running_loop().create_future()

    async def on_connect(reader, writer):
        (length,) = struct.unpack("<I", await reader.readexactly(4))
        received.set_result(await reader.readexactly(length))
        writer.close()

    server = await asyncio.start_server(on_connect, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    log = link_module.setup_logging("test")
    link = await link_module.Link.connect("127.0.0.1", port, log)
    msg = link_module.stamp(link_module.load_template("sensor", "StatusReport"), NODE)

    await link.send(msg)

    assert await asyncio.wait_for(received, 5) == msg.SerializeToString()
    link.close()
    server.close()
    await server.wait_closed()
