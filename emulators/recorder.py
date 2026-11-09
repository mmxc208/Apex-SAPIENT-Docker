"""Recorder: appends every SAPIENT message seen on Zenoh to one JSON-lines file per UTC day.

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
from typing import Any

from google.protobuf.json_format import MessageToDict

from sapient_link import setup_logging
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import ZenohSession, open_session
from zenoh_keys import PREFIX, parse_key

log = logging.getLogger("recorder")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _describe_key(key: str) -> tuple[str | None, str | None]:
    """Return (node_id, kind), both None for keys that do not belong to one node."""
    try:
        node_id, _, kind = parse_key(key)
    except ValueError:
        return None, None
    return node_id, kind


def _record(received: datetime, key: str, payload: bytes) -> dict[str, Any]:
    record: dict[str, Any] = {"t": received.isoformat(timespec="milliseconds"), "key": key}
    try:
        msg = MessageToDict(SapientMessage.FromString(payload), preserving_proto_field_name=True)
    except Exception:  # not only DecodeError: a timestamp beyond year 9999 raises OverflowError
        return record | {"error": "decode", "payload_b64": base64.b64encode(payload).decode("ascii")}
    node_id, kind = _describe_key(key)
    return record | {"kind": kind, "node_id": node_id, "msg": msg}


class Recorder:
    def __init__(self, session: ZenohSession, out_dir: Path) -> None:
        self.session = session
        self.out_dir = out_dir

    async def run(self) -> None:
        samples = self.session.subscribe(f"{PREFIX}sapient/v2/**")
        while True:
            key, payload = await samples.get()
            received = _now()
            try:
                self._append(received, _record(received, key, payload))
            except OSError as e:
                log.info(f"cannot write the sample on {key}: {e}")

    def _append(self, received: datetime, record: dict[str, Any]) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        with (self.out_dir / f"{received:%Y-%m-%d}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


async def run(connect: str, out_dir: Path, log: logging.Logger) -> None:
    """Record until recording fails, which raises, or the session is closed, which returns.

    Either way the process exits and the container's restart policy applies. A lost router ends
    nothing: the session reconnects by itself and restores the subscription.
    """
    session = await open_session(connect, asyncio.get_running_loop(), log)
    recording = asyncio.create_task(Recorder(session, out_dir).run())
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
    try:
        asyncio.run(run(connect, out_dir, log))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
