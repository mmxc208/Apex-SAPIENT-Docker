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
import uuid

from zenoh_io import ZenohSession, open_session

log = logging.getLogger("probe-fabric-pairing")

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


async def exchange(anchor: str, writer: ZenohSession, reader: ZenohSession, run: str, result: dict) -> None:
    """Fill result["received"] and result["token"]; may raise, the caller still reports."""
    node = run  # a per-run UUID is a canonical node ID, so the key form is unchanged
    key = f"{anchor}/telemetry/sapient/p1/v2/status_report/{node}"
    live_key = f"{anchor}/telemetry/sapient/p1/v2/live/{node}"
    payloads = {f"probe {run} {i}".encode() for i in range(PUTS)}
    data = reader.subscribe(f"{anchor}/**")
    live = reader.liveliness(f"{anchor}/**")
    await asyncio.sleep(SETTLE_SECONDS)
    writer.declare_token(live_key)
    await asyncio.sleep(SETTLE_SECONDS)
    for payload in sorted(payloads):
        await writer.publish_raw(key, payload, "status_report")
    await asyncio.sleep(SETTLE_SECONDS)
    seen = set()
    while not data.empty():
        k, payload = data.get_nowait()
        if k == key and payload in payloads:
            seen.add(payload)
    result["received"] = len(seen)
    while not live.empty():
        k, appeared = live.get_nowait()
        result["token"] |= appeared and k == live_key


async def run(anchor: str) -> bool:
    run_id = str(uuid.uuid4())
    writer, reader = await asyncio.gather(try_open("ZENOH"), try_open("READER"))
    result = {"received": 0, "token": False}
    try:
        if writer and reader:
            await exchange(anchor, writer, reader, run_id, result)
    except Exception as e:
        log.info(f"exchange failed: {type(e).__name__}: {e}")
    finally:
        for session in (writer, reader):
            if session:
                session.close()
    print(f"session: writer {str(writer is not None).lower()} reader {str(reader is not None).lower()}")
    print(f"put below anchor received: {result['received']} of {PUTS}")
    print(f"liveliness token seen by reader: {str(result['token']).lower()}")
    return bool(writer and reader) and result["received"] == PUTS and result["token"]


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", stream=sys.stderr)
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        code = 0 if asyncio.run(run(argv[0])) else 1
    except BaseException as e:
        log.info(f"probe failed: {type(e).__name__}: {e}")
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    # A thread stuck in zenoh.open cannot be cancelled and would hold the interpreter at exit
    # (asyncio.run waits for the default executor), so end the process here, lines flushed.
    os._exit(code)


if __name__ == "__main__":
    main(sys.argv[1:])
