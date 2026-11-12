"""Pod bridge: the one process that joins a pod's Zenoh router to the host's fabric router.

It holds one client session to each router and forwards payload bytes unchanged. A message is
decoded only to read its header (node_id, destination_id, timestamp); it is never serialised again.

    pod    <prefix>fusion/up/<kind>   ->  fabric  <anchor>/.../<site>/.../<kind>/<node_id>
    fabric <host>/.../<site>/.../<kind>/<node_id>  ->  pod  <prefix>fusion/down/<kind>

Presence follows traffic: the liveliness token of a pod node is declared on the fabric when its
first message is forwarded and dropped after PRESENCE_SECONDS without one, or when the pod router
is lost. While one router is away, what arrives from the other side is dropped and counted.
Each direction buffers at most QUEUE_LIMIT samples and drops the oldest.
"""
from __future__ import annotations

import asyncio
import collections
import logging
import os
import time

from google.protobuf.message import DecodeError

import fabric_keys
from sapient_link import setup_logging
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_io import ZenohSession, open_session
from zenoh_keys import FUSION_UP_ALL, fusion_down_key, fusion_kind, kind_of

MAX_TASK_AGE_SECONDS = 5.0
PRESENCE_SECONDS = 30.0
QUEUE_LIMIT = 512
EXPIRE_INTERVAL_SECONDS = 5.0
COUNTER_LOG_SECONDS = 30.0
UP_KINDS = frozenset({"registration", "status_report", "detection_report", "alert", "error", "task_ack"})
DOWN_KINDS = frozenset({"registration_ack", "task", "alert_ack", "error"})

Sample = tuple[str, bytes]


class _DropOldest:
    """A buffer of at most QUEUE_LIMIT samples; adding to a full one drops the oldest."""

    def __init__(self) -> None:
        self._items: collections.deque[Sample] = collections.deque()
        self._ready = asyncio.Event()

    def put(self, sample: Sample) -> bool:
        """Add a sample; return False when the oldest had to be dropped to make room."""
        kept = len(self._items) < QUEUE_LIMIT
        if not kept:
            self._items.popleft()
        self._items.append(sample)
        self._ready.set()
        return kept

    async def get(self) -> Sample:
        while not self._items:
            self._ready.clear()
            await self._ready.wait()
        return self._items.popleft()


class PodBridge:
    def __init__(
        self,
        pod: ZenohSession,
        fabric: ZenohSession,
        *,
        anchor: str,
        site: str,
        host_anchors: list[str],
        log: logging.Logger,
        clock=time.time,
    ) -> None:
        self.pod = pod
        self.fabric = fabric
        self.anchor = anchor
        self.site = site
        self.host_anchors = list(host_anchors)
        self.log = log
        self.clock = clock
        # Fail now, not at the first sample, on a bad anchor or site.
        fabric_keys.subscriptions(anchor, site)
        self._subscriptions = [
            expr for host in self.host_anchors for expr in fabric_keys.subscriptions(host, site)
        ]
        self.forwarded: collections.Counter = collections.Counter()
        self.dropped: collections.Counter = collections.Counter()
        self._up = {"pod": True, "fabric": True}
        self._known: set[str] = set()          # nodes whose messages went up: the host may address them
        self._last_seen: dict[str, float] = {}  # nodes that hold a token on the fabric

    # --- one sample -------------------------------------------------------------------------

    async def forward_up(self, key: str, payload: bytes) -> None:
        """One sample from the pod.

        Checks run from what is wrong with the sample itself to what is wrong with the link, so
        every counter says what was wrong first; other_side_down counts only samples that were
        otherwise good.
        """
        try:
            direction, kind = fusion_kind(key)
        except ValueError:
            return self._drop("bad_key", key)
        if direction != "up":
            return self._drop("bad_key", key)
        if kind not in UP_KINDS:
            return self._drop("bad_kind", key)
        msg = self._decode(payload)
        if msg is None:
            return self._drop("undecodable", key)
        if kind_of(msg) != kind:
            return self._drop("bad_kind", key)
        try:
            fabric_key = fabric_keys.key_for(self.anchor, self.site, kind, msg.node_id)
        except ValueError:
            return self._drop("undecodable", key)  # a header without a usable node ID
        if not self._up["fabric"]:
            return self._drop("other_side_down", key)
        try:
            await self.fabric.publish_raw(fabric_key, payload, kind, fused=True)
        except Exception as e:
            self.log.info(f"cannot publish {fabric_key}: {e!r}")
            return self._drop("publish_error", key)
        self.forwarded["up"] += 1
        self._known.add(msg.node_id)
        self._last_seen[msg.node_id] = self.clock()
        self.fabric.declare_token(fabric_keys.live_key(self.anchor, self.site, msg.node_id))

    async def forward_down(self, key: str, payload: bytes) -> None:
        """One sample from the fabric; the order of the checks is the one of forward_up."""
        try:
            parsed = fabric_keys.parse(key)
        except ValueError:
            return self._drop("bad_key", key)
        if parsed.anchor not in self.host_anchors or parsed.site != self.site:
            return self._drop("bad_key", key)
        kind = parsed.kind
        if kind not in DOWN_KINDS:
            return self._drop("bad_kind", key)
        msg = self._decode(payload)
        if msg is None:
            return self._drop("undecodable", key)
        if kind_of(msg) != kind:
            return self._drop("bad_kind", key)
        if msg.destination_id != parsed.node_id:
            return self._drop("wrong_destination", key)
        if parsed.node_id not in self._known:
            return self._drop("unknown_destination", key)
        if kind == "task" and self._age(msg) > MAX_TASK_AGE_SECONDS:
            return self._drop("stale_task", key)
        if not self._up["pod"]:
            return self._drop("other_side_down", key)
        try:
            await self.pod.publish_raw(fusion_down_key(kind), payload, kind)
        except Exception as e:
            self.log.info(f"cannot publish {fusion_down_key(kind)}: {e!r}")
            return self._drop("publish_error", key)
        self.forwarded["down"] += 1

    def _decode(self, payload: bytes) -> SapientMessage | None:
        try:
            return SapientMessage.FromString(payload)
        except DecodeError:
            return None

    def _age(self, msg: SapientMessage) -> float:
        """Seconds since the message's timestamp; a message with none is as old as can be."""
        if not msg.HasField("timestamp"):
            return float("inf")
        return self.clock() - (msg.timestamp.seconds + msg.timestamp.nanos / 1e9)

    def _drop(self, reason: str, key: str) -> None:
        self.dropped[reason] += 1
        self.log.debug(f"dropped ({reason}) {key}")

    # --- presence and transport -------------------------------------------------------------

    def expire_presence(self) -> None:
        """Remove the token of every node that has sent nothing for PRESENCE_SECONDS."""
        now = self.clock()
        for node_id in [n for n, seen in self._last_seen.items() if now - seen >= PRESENCE_SECONDS]:
            del self._last_seen[node_id]
            self.fabric.undeclare_token(fabric_keys.live_key(self.anchor, self.site, node_id))
            self.log.info(f"no traffic from {node_id} for {PRESENCE_SECONDS:.0f} s; token removed")

    def on_transport(self, side: str, up: bool) -> None:
        """A router came back or went. Side is "pod" or "fabric"."""
        if side not in self._up:
            raise ValueError(f"unknown side: {side!r}")
        self._up[side] = up
        self.log.info(f"{side} router {'back' if up else 'lost'}")
        if side == "pod" and not up:
            for node_id in list(self._last_seen):
                self.fabric.undeclare_token(fabric_keys.live_key(self.anchor, self.site, node_id))
            self._last_seen.clear()

    # --- the pumps --------------------------------------------------------------------------

    async def run(self) -> None:
        """Pump both directions and run the timers, until cancelled, a session is closed or a task fails.

        A closed session logs a line and returns. Any other task that ends is a fault: it is logged
        and raised, so the process ends with an error and compose starts it again. A lost router is
        not a reason to end; on_transport handles it.
        """
        up, down = _DropOldest(), _DropOldest()
        named = {
            "pod session": self.pod.closed.wait(),
            "fabric session": self.fabric.closed.wait(),
            "pod reader": self._read(self.pod.subscribe(FUSION_UP_ALL), up),
            "up writer": self._write(up, self.forward_up),
            "down writer": self._write(down, self.forward_down),
            "pod transport": self._transport("pod", self.pod),
            "fabric transport": self._transport("fabric", self.fabric),
            "timers": self._timers(),
        }
        for expr in self._subscriptions:
            named[f"fabric reader {expr}"] = self._read(self.fabric.subscribe(expr), down)
        tasks = {asyncio.create_task(coroutine, name=name): name for name, coroutine in named.items()}
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            faults = [task for task in tasks if task in done and not tasks[task].endswith(" session")]
            if not faults:
                side = tasks[next(iter(done))].split()[0]
                self.log.info(f"{side} session closed; the bridge stops")
                return
            task = faults[0]
            error = (None if task.cancelled() else task.exception()) or RuntimeError(f"the {tasks[task]} task ended")
            self.log.error(f"the {tasks[task]} task ended with {error!r}; the bridge stops")
            raise error
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _read(self, source: asyncio.Queue, buffer: _DropOldest) -> None:
        """Move samples from a session's queue into the bounded buffer."""
        while True:
            sample = await source.get()
            if not buffer.put(sample):
                self.dropped["queue_full"] += 1

    async def _write(self, buffer: _DropOldest, forward) -> None:
        while True:
            key, payload = await buffer.get()
            try:
                await forward(key, payload)
            except Exception as e:
                self.log.info(f"error on {key}: {e!r}")

    async def _transport(self, side: str, session: ZenohSession) -> None:
        while True:
            up = await session.transport_changes.get()
            try:
                self.on_transport(side, up)
            except Exception as e:
                self.log.info(f"error on the {side} transport change: {e!r}")

    async def _timers(self) -> None:
        shown = self._counts()
        since_log = 0.0
        while True:
            await asyncio.sleep(EXPIRE_INTERVAL_SECONDS)
            since_log += EXPIRE_INTERVAL_SECONDS
            try:
                self.expire_presence()
                if since_log >= COUNTER_LOG_SECONDS and self._counts() != shown:
                    shown = self._counts()
                    self.log.info(f"forwarded {dict(self.forwarded)}; dropped {dict(self.dropped)}")
                if since_log >= COUNTER_LOG_SECONDS:
                    since_log = 0.0
            except Exception as e:
                self.log.info(f"error in the timers: {e!r}")

    def _counts(self) -> tuple[dict, dict]:
        return dict(self.forwarded), dict(self.dropped)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} must be set")
    return value


async def main_async() -> None:
    log = setup_logging("pod-bridge")
    pod_connect = _required("POD_CONNECT")
    fabric_connect = _required("FABRIC_CONNECT")
    anchor = _required("FABRIC_ANCHOR")
    site = _required("FABRIC_SITE")
    host_anchors = [a.strip() for a in os.environ.get("FABRIC_HOST_ANCHORS", "").split(",") if a.strip()]
    if not host_anchors:
        raise ValueError("FABRIC_HOST_ANCHORS must list at least one host anchor")
    loop = asyncio.get_running_loop()
    pod = fabric = None
    try:
        pod = await open_session(pod_connect, loop, log, "POD")
        fabric = await open_session(fabric_connect, loop, log, "FABRIC")
        bridge = PodBridge(pod, fabric, anchor=anchor, site=site, host_anchors=host_anchors, log=log)
        log.info(f"bridging {pod_connect} and {fabric_connect} as {anchor} site {site}")
        await bridge.run()
    finally:
        for session in (pod, fabric):
            if session is not None:
                session.close()


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
