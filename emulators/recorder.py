"""Recorder: appends every SAPIENT message seen on Zenoh to one JSON-lines file per UTC day.

RECORD_KEYS picks the keys: "pod" (the default) records a pod's sapient/v2 keys, with the kind and
node of each; "fabric" records the fabric's telemetry, ack and task keys, also with anchor and site.
In fabric mode a line for an undecodable payload holds the parts of its key too (design 4.8).

Each file is opened for each write, which is simple and crash-safe at emulator rates. What goes
wrong with one sample, an undecodable payload or a failing disk, never stops the next one.
"""
import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from google.protobuf.json_format import MessageToDict

import fabric_keys
from sapient_link import setup_logging
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import ZenohSession, open_session
from zenoh_keys import PREFIX, parse_key

log = logging.getLogger("recorder")


def _now() -> datetime:
    return datetime.now(timezone.utc)


Describe = Callable[[str], dict[str, str | None]]


def describe_pod_key(key: str) -> dict[str, str | None]:
    """kind and node_id of a pod key, both None for keys that do not belong to one node."""
    try:
        node_id, _, kind = parse_key(key)
    except ValueError:
        return {"kind": None, "node_id": None}
    return {"kind": kind, "node_id": node_id}


def describe_fabric_key(key: str) -> dict[str, str | None]:
    """kind, node_id, anchor and site of a fabric data key, all None for a malformed key."""
    try:
        parsed = fabric_keys.parse(key)
    except ValueError:
        return {"kind": None, "node_id": None, "anchor": None, "site": None}
    return {"kind": parsed.kind, "node_id": parsed.node_id, "anchor": parsed.anchor, "site": parsed.site}


POD_KEYS: tuple[str, ...] = (f"{PREFIX}sapient/v2/**",)
_MODES: dict[str, tuple[tuple[str, ...], Describe, bool]] = {
    "pod": (POD_KEYS, describe_pod_key, False),
    "fabric": (fabric_keys.subscriptions(), describe_fabric_key, True),
}


def record_keys(mode: str) -> tuple[tuple[str, ...], Describe, bool]:
    """The key expressions, the key description, and whether an error line is described too, of a
    RECORD_KEYS value. ValueError for an unknown one."""
    if mode not in _MODES:
        raise ValueError(f"RECORD_KEYS must be one of {', '.join(_MODES)}, not {mode!r}")
    return _MODES[mode]


def _record(
    received: datetime, key: str, payload: bytes, describe: Describe, describe_errors: bool = False
) -> dict[str, Any]:
    record: dict[str, Any] = {"t": received.isoformat(timespec="milliseconds"), "key": key}
    try:
        msg = MessageToDict(SapientMessage.FromString(payload), preserving_proto_field_name=True)
    except Exception:  # not only DecodeError: a timestamp beyond year 9999 raises OverflowError
        parts = describe(key) if describe_errors else {}
        return record | parts | {"error": "decode", "payload_b64": base64.b64encode(payload).decode("ascii")}
    return record | describe(key) | {"msg": msg}


class Recorder:
    def __init__(
        self,
        session: ZenohSession,
        out_dir: Path,
        expressions: tuple[str, ...] = POD_KEYS,
        describe: Describe = describe_pod_key,
        describe_errors: bool = False,
    ) -> None:
        self.session = session
        self.out_dir = out_dir
        self.expressions = expressions
        self.describe = describe
        self.describe_errors = describe_errors

    async def run(self) -> None:
        subscriptions = [self.session.subscribe(expression) for expression in self.expressions]
        async with asyncio.TaskGroup() as group:
            for samples in subscriptions:
                group.create_task(self._record_from(samples))

    async def _record_from(self, samples: asyncio.Queue[tuple[str, bytes]]) -> None:
        while True:
            key, payload = await samples.get()
            received = _now()
            try:
                self._append(received, _record(received, key, payload, self.describe, self.describe_errors))
            except OSError as e:
                log.info(f"cannot write the sample on {key}: {e}")

    def _append(self, received: datetime, record: dict[str, Any]) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        with (self.out_dir / f"{received:%Y-%m-%d}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


async def run(connect: str, out_dir: Path, log: logging.Logger, keys: str = "pod") -> None:
    """Record until recording fails, which raises, or the session is closed, which returns.

    Either way the process exits and the container's restart policy applies. A lost router ends
    nothing: the session reconnects by itself and restores each subscription.
    """
    session = await open_session(connect, asyncio.get_running_loop(), log)
    recording = asyncio.create_task(Recorder(session, out_dir, *record_keys(keys)).run())
    closed = asyncio.create_task(session.closed.wait())
    tasks = (recording, closed)
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        if recording.done():
            recording.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        session.close()


def main() -> None:
    log = setup_logging("recorder")
    out_dir = Path(os.environ.get("RECORD_DIR", "/data/records"))
    connect = os.environ.get("ZENOH_CONNECT", "tcp/zenohd:7447")
    keys = os.environ.get("RECORD_KEYS", "pod")
    record_keys(keys)  # refuse an unknown value before connecting
    try:
        asyncio.run(run(connect, out_dir, log, keys))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
