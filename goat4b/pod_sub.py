"""A subscriber on the pod router that prints one line for each sample, and no payload.

    pod_sub.py <key expression> <seconds>

Runs in a one-off container of the `recorder` service (its certificate, its router), with
PYTHONPATH=/emulators and this file mounted, for example:

    dg4b_pod run --rm --no-deps -T -e PYTHONPATH=/emulators -v "$PWD/goat4b/pod_sub.py:/w/pod_sub.py:ro" \
      recorder python /w/pod_sub.py 'h1/p1/fusion/down/**' 45 < /dev/null

Each line: `HH:MM:SS.mmm <key> | from <8> to <8> | <content> <task_id>` (UTC, the receive time
on this container's clock; task_id `-` when the message is no task or acknowledgement). At the end:
`pod sub: <n> samples on <expr> in <s> s`.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import open_session

log = logging.getLogger("pod-sub")


def describe(key: str, payload: bytes, now: datetime) -> str:
    stamp = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
    try:
        msg = SapientMessage.FromString(payload)
    except Exception:
        return f"{stamp} {key} | undecodable ({len(payload)} bytes)"
    content = msg.WhichOneof("content") or "-"
    task_id = "-"
    if content in ("task", "task_ack"):
        task_id = getattr(msg, content).task_id or "-"
    return f"{stamp} {key} | from {msg.node_id[:8] or '-'} to {msg.destination_id[:8] or '-'} | {content} {task_id}"


async def run(expr: str, seconds: float) -> int:
    loop = asyncio.get_running_loop()
    session = await open_session(os.environ["ZENOH_CONNECT"], loop, log)
    n = 0
    try:
        samples = session.subscribe(expr)
        end = loop.time() + seconds
        while (left := end - loop.time()) > 0:
            try:
                key, payload = await asyncio.wait_for(samples.get(), left)
            except asyncio.TimeoutError:
                break
            n += 1
            print(describe(key, payload, datetime.now(timezone.utc)), flush=True)
    finally:
        session.close()
    print(f"pod sub: {n} samples on {expr} in {seconds:g} s", flush=True)
    return n


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(name)s %(message)s")
    if len(argv) != 2:
        print("usage: pod_sub.py <key expression> <seconds>", file=sys.stderr)
        return 2
    asyncio.run(run(argv[0], float(argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
