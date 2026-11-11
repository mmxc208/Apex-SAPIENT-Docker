"""G1-01: check that the 1.10.2 Python binding and the fabric router image work together.

Opens two mutual-TLS sessions, A and B. A publishes and declares the token; B subscribes and queries
liveliness. A session delivers its own publications and tokens to itself with no router, so one session
would prove nothing about the router: with two, every sample and token must cross it. With
PROBE_WAIT_RESTART=1 it then waits for both sessions to lose and regain the router and repeats both
checks, with no new subscribe or declare call. Writes no file. Exit code 1 on any failure.
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


async def check_put_sub(a: ZenohSession, b_queue: asyncio.Queue, label: str) -> None:
    """A publishes a StatusReport on PUT_KEY; B must receive the same bytes within CHECK_SECONDS."""
    msg = load_template("sensor", "StatusReport")
    stamp(msg, NODE_ID)
    expected = msg.SerializeToString()
    await a.publish(PUT_KEY, msg)
    try:
        key, got = await asyncio.wait_for(b_queue.get(), CHECK_SECONDS)
    except asyncio.TimeoutError:
        raise Failed(f"{label}: B got no sample on {PUT_KEY} within {CHECK_SECONDS} s") from None
    if key != PUT_KEY or got != expected:
        raise Failed(f"{label}: B's sample on {key} differs from the bytes A sent")


async def check_liveliness(b: ZenohSession, label: str) -> None:
    """B's liveliness query must return A's TOKEN_KEY within CHECK_SECONDS."""
    try:
        keys = await asyncio.wait_for(b.alive("probe/live/*"), CHECK_SECONDS)
    except asyncio.TimeoutError:
        raise Failed(f"{label}: B's liveliness query gave no answer within {CHECK_SECONDS} s") from None
    if TOKEN_KEY not in keys:
        raise Failed(f"{label}: B's liveliness query returned {keys}, not {TOKEN_KEY}")


async def wait_for_restart(session: ZenohSession, name: str) -> None:
    """Wait for the session's transport_changes to give False, then True."""
    for want in (False, True):
        while True:
            try:
                got = await asyncio.wait_for(session.transport_changes.get(), RESTART_SECONDS)
            except asyncio.TimeoutError:
                raise Failed(
                    f"restart: session {name} never reported transport {want} within {RESTART_SECONDS} s"
                ) from None
            if got == want:
                break


async def run() -> None:
    loop = asyncio.get_running_loop()
    connect = os.environ["ZENOH_CONNECT"]
    a = await open_session(connect, loop, log)
    b = await open_session(connect, loop, log)
    try:
        b_queue = b.subscribe("probe/**")
        a.declare_token(TOKEN_KEY)
        await asyncio.sleep(0.5)  # let the subscription and token reach the router
        await check_put_sub(a, b_queue, "put-sub")
        await check_liveliness(b, "liveliness")
        print("PAIRING OK put-sub liveliness", flush=True)
        if os.environ.get("PROBE_WAIT_RESTART") == "1":
            await asyncio.gather(wait_for_restart(a, "A"), wait_for_restart(b, "B"))
            await asyncio.sleep(2)  # replayed declarations need a moment
            while not b_queue.empty():
                b_queue.get_nowait()
            await check_put_sub(a, b_queue, "put-sub after restart")
            await check_liveliness(b, "liveliness after restart")
            print("PAIRING OK after router restart", flush=True)
    finally:
        a.close()
        b.close()


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
