"""G1-05: publish or subscribe with one chosen certificate, to show what a router lets through.

    python probe_access.py put <key>
        publishes one status report on <key>, waits a moment for it to leave, and exits
    python probe_access.py sub <key expression> <seconds>
        subscribes, counts the samples received in <seconds>, and prints "samples: <n>", then how
        many of them are this probe's own status reports (node ID PROBE_NODE_ID), because the keys
        under test also carry the rig's real traffic

The router and the certificate come from ZENOH_CONNECT and ZENOH_TLS_CA, ZENOH_TLS_CERT and
ZENOH_TLS_KEY. A denial is silent for the client: the evidence is the other side's count and the
router's trace log (RUST_LOG=zenoh::net::routing::interceptor=trace). Writes no file.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

from sapient_link import load_template, stamp
from zenoh_io import open_session

log = logging.getLogger("probe-access")

PROBE_NODE_ID = "a0000009-0000-4000-8000-000000000009"
SETTLE_SECONDS = 1.0  # time for a declaration to reach the router, and for a put to leave
USAGE = "usage: probe_access.py put <key> | sub <key expression> <seconds>"


async def put(key: str) -> None:
    session = await open_session(os.environ["ZENOH_CONNECT"], asyncio.get_running_loop(), log)
    try:
        msg = load_template("sensor", "StatusReport")
        stamp(msg, PROBE_NODE_ID)
        await asyncio.sleep(SETTLE_SECONDS)
        await session.publish(key, msg)
        await asyncio.sleep(SETTLE_SECONDS)
        print(f"put: 1 status report on {key}", flush=True)
    finally:
        session.close()


async def sub(keyexpr: str, seconds: float) -> None:
    session = await open_session(os.environ["ZENOH_CONNECT"], asyncio.get_running_loop(), log)
    try:
        samples = session.subscribe(keyexpr)
        await asyncio.sleep(seconds)
        keys = set()
        count = probes = 0
        while not samples.empty():
            key, payload = samples.get_nowait()
            keys.add(key)
            count += 1
            probes += _is_probe(payload)
        print(f"samples: {count} on {keyexpr} in {seconds:g} s; from this probe: {probes}", flush=True)
        for key in sorted(keys)[:5]:
            print(f"  e.g. {key}", flush=True)
    finally:
        session.close()


def _is_probe(payload: bytes) -> bool:
    try:
        return SapientMessage.FromString(payload).node_id == PROBE_NODE_ID
    except Exception:
        return False


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if len(argv) == 2 and argv[0] == "put":
        asyncio.run(put(argv[1]))
    elif len(argv) == 3 and argv[0] == "sub":
        asyncio.run(sub(argv[1], float(argv[2])))
    else:
        print(USAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
