"""G1-01: check that the 1.10.2 Python binding and the fabric router image work together.

Opens one mutual-TLS session and checks put/subscribe and liveliness. With PROBE_WAIT_RESTART=1 it then
waits for the router to go away and come back, and checks both again on the same session, with no new
subscribe or declare call. Writes no file. Exit code 1 on any failure.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

from sapient_link import load_template, stamp
from zenoh_io import ZenohSession, open_session

log = logging.getLogger("probe-pairing")

CHECK_SECONDS = 5
RESTART_SECONDS = 90
NODE_ID = "a0000001-0000-4000-8000-000000000001"
PUT_KEY = "probe/a"
TOKEN_KEY = "probe/live/x"


class Failed(Exception):
    pass


async def check_put_sub(session: ZenohSession, queue: asyncio.Queue, label: str) -> None:
    """Publish a StatusReport on PUT_KEY and require the same bytes back within CHECK_SECONDS."""
    msg = load_template("sensor", "StatusReport")
    stamp(msg, NODE_ID)
    expected = msg.SerializeToString()
    await session.publish(PUT_KEY, msg)
    try:
        key, got = await asyncio.wait_for(queue.get(), CHECK_SECONDS)
    except asyncio.TimeoutError:
        raise Failed(f"{label}: no sample on {PUT_KEY} within {CHECK_SECONDS} s") from None
    if key != PUT_KEY or got != expected:
        raise Failed(f"{label}: sample on {key} differs from the bytes sent")


async def check_liveliness(session: ZenohSession, label: str) -> None:
    """Require alive() to return TOKEN_KEY within CHECK_SECONDS."""
    try:
        keys = await asyncio.wait_for(session.alive("probe/live/*"), CHECK_SECONDS)
    except asyncio.TimeoutError:
        raise Failed(f"{label}: liveliness query gave no answer within {CHECK_SECONDS} s") from None
    if TOKEN_KEY not in keys:
        raise Failed(f"{label}: liveliness query returned {keys}, not {TOKEN_KEY}")


async def wait_for_restart(session: ZenohSession) -> None:
    """Wait for transport_changes to give False, then True."""
    for want in (False, True):
        while True:
            try:
                got = await asyncio.wait_for(session.transport_changes.get(), RESTART_SECONDS)
            except asyncio.TimeoutError:
                raise Failed(f"restart: transport never reported {want} within {RESTART_SECONDS} s") from None
            if got == want:
                break


async def run() -> None:
    loop = asyncio.get_running_loop()
    session = await open_session(os.environ["ZENOH_CONNECT"], loop, log)
    try:
        queue = session.subscribe("probe/**")
        session.declare_token(TOKEN_KEY)
        await asyncio.sleep(0.5)  # let the subscription and token reach the router
        await check_put_sub(session, queue, "put-sub")
        await check_liveliness(session, "liveliness")
        print("PAIRING OK put-sub liveliness", flush=True)
        if os.environ.get("PROBE_WAIT_RESTART") == "1":
            await wait_for_restart(session)
            await asyncio.sleep(2)  # replayed declarations need a moment
            while not queue.empty():
                queue.get_nowait()
            await check_put_sub(session, queue, "put-sub after restart")
            await check_liveliness(session, "liveliness after restart")
            print("PAIRING OK after router restart", flush=True)
    finally:
        session.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    try:
        asyncio.run(run())
    except Failed as e:
        print(f"PAIRING FAILED: {e}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
