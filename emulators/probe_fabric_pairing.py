"""G4-01: does a goatnet router carry a writer's data to a reader, with two different certificates.

    python probe_fabric_pairing.py <writer anchor>

The writer (ZENOH_TLS_CA, ZENOH_TLS_CERT, ZENOH_TLS_KEY) puts five payloads and declares one
liveliness token, all below <writer anchor>; the reader (READER_TLS_CA, READER_TLS_CERT,
READER_TLS_KEY) subscribes to <anchor>/** and to liveliness on it before the writer starts. The
router is ZENOH_CONNECT. Prints exactly three result lines and exits 0 only if all are true:

    session: writer <true|false> reader <true|false>
    put below anchor received: <n> of 5
    liveliness token seen by reader: <true|false>

A session that does not open within OPEN_SECONDS counts as false. Writes no file.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

from zenoh_io import ZenohSession, open_session

log = logging.getLogger("probe-fabric-pairing")

NODE_ID = "a0000009-0000-4000-8000-000000000009"
PUTS = 5
SETTLE_SECONDS = 1.0  # time for a declaration to reach the router, and for a put to leave
OPEN_SECONDS = 20.0
USAGE = "usage: probe_fabric_pairing.py <writer anchor>"


async def try_open(prefix: str) -> ZenohSession | None:
    try:
        return await asyncio.wait_for(
            open_session(os.environ["ZENOH_CONNECT"], asyncio.get_running_loop(), log, prefix),
            OPEN_SECONDS,
        )
    except Exception as e:  # timeout, bad certificate or unreadable file
        log.info(f"{prefix}: session did not open: {type(e).__name__}: {e}")
        return None


async def run(anchor: str) -> bool:
    reader = await try_open("READER")
    writer = await try_open("ZENOH") if reader else None
    received = 0
    token_seen = False
    try:
        if reader and writer:
            data = reader.subscribe(f"{anchor}/**")
            live = reader.liveliness(f"{anchor}/**")
            await asyncio.sleep(SETTLE_SECONDS)
            writer.declare_token(f"{anchor}/telemetry/sapient/p1/v2/live/{NODE_ID}")
            await asyncio.sleep(SETTLE_SECONDS)
            key = f"{anchor}/telemetry/sapient/p1/v2/status_report/{NODE_ID}"
            for i in range(PUTS):
                await writer.publish_raw(key, f"probe {i}".encode(), "status_report")
            await asyncio.sleep(SETTLE_SECONDS)
            while not data.empty():
                data.get_nowait()
                received += 1
            while not live.empty():
                k, appeared = live.get_nowait()
                token_seen |= appeared and k.endswith(f"/live/{NODE_ID}")
    finally:
        for session in (writer, reader):
            if session:
                session.close()
    print(f"session: writer {str(writer is not None).lower()} reader {str(reader is not None).lower()}")
    print(f"put below anchor received: {received} of {PUTS}")
    print(f"liveliness token seen by reader: {str(token_seen).lower()}")
    return bool(writer and reader) and received == PUTS and token_seen


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", stream=sys.stderr)
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    return 0 if asyncio.run(run(argv[0])) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
