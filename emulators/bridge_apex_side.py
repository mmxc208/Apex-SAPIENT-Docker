"""Apex-side bridge: gives every Zenoh SAPIENT node its own TCP connection to Apex's Child port.

Apex binds a node's identity to its connection and requires a registration first, so each node_id
gets exactly one socket, opened by its first registration. Apex's replies go back on the node's
down keys. A socket outlives a liveliness flap: it is closed only after the token has been gone
for the whole hold window. A node seen alive with no socket is asked to register again, after a
short grace in which its own registration may arrive; this covers nodes that registered before
this bridge started or whose socket was closed. Each such request produces a TaskAck that Apex
did not solicit.
"""
import asyncio
import logging
import os
import uuid

from google.protobuf.message import DecodeError

from bridge_node_side import open_session
from sapient_link import Link, new_ulid, setup_logging, stamp
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from sapient_msg.bsi_flex_335_v2_0.task_pb2 import Task
from zenoh_io import ZenohSession
from zenoh_keys import LIVE_ALL, UP_ALL, down_key, kind_of, node_id_from_live_key, parse_key


class ApexSideBridge:
    def __init__(
        self,
        session: ZenohSession,
        apex_host: str,
        apex_port: int,
        hold_seconds: float = 120,
        max_bytes: int = 1024 * 1024,
        *,
        log: logging.Logger,
        bridge_node_id: str,
        request_grace_seconds: float = 3.0,
    ) -> None:
        self.session = session
        self.apex_host = apex_host
        self.apex_port = apex_port
        self.hold_seconds = hold_seconds
        self.max_bytes = max_bytes
        self.log = log
        self.bridge_node_id = bridge_node_id
        self.request_grace_seconds = request_grace_seconds
        self.links: dict[str, Link] = {}
        self._readers: dict[str, asyncio.Task] = {}
        self._hold_timers: dict[str, asyncio.TimerHandle] = {}
        self._token_alive: dict[str, bool] = {}  # the last state reported; absent until first reported
        self._pending_requests: dict[str, asyncio.Task] = {}
        self._task_failed: asyncio.Future[None] | None = None

    async def run(self) -> None:
        """Bridge until the Zenoh session closes, then close every link and return.

        Raises if forwarding fails for a reason other than one link's socket, so the process exits.
        """
        self._task_failed = asyncio.get_running_loop().create_future()
        samples = self.session.subscribe(UP_ALL)
        changes = self.session.liveliness(LIVE_ALL)
        # Before the loops start, so the same tokens replayed by the subscription count as known.
        for key in await self.session.alive(LIVE_ALL):
            self._on_liveliness(key, True)
        up = asyncio.create_task(self._forward_up(samples))
        live = asyncio.create_task(self._track_liveliness(changes))
        closed = asyncio.create_task(self.session.closed.wait())
        watched = {up, live, closed, self._task_failed}
        try:
            await asyncio.wait(watched, return_when=asyncio.FIRST_COMPLETED)
            for failable in (up, live, self._task_failed):
                if failable.done():
                    failable.result()
        finally:
            for waiting in watched:
                waiting.cancel()
            await asyncio.gather(up, live, closed, return_exceptions=True)
            await self._close_all()

    async def _forward_up(self, samples: asyncio.Queue[tuple[str, bytes]]) -> None:
        """Handle samples strictly in order, so a node's messages cannot overtake its registration.

        All nodes share this loop: while Apex is unreachable or one node's socket stops draining,
        every node waits and samples queue without limit.
        """
        while True:
            key, payload = await samples.get()
            await self._handle_sample(key, payload)

    async def _handle_sample(self, key: str, payload: bytes) -> None:
        try:
            node_id, _, _ = parse_key(key)
        except ValueError:
            self.log.info(f"ignoring sample on bad key {key!r}")
            return
        if len(payload) > self.max_bytes:
            self.log.info(f"dropping oversized payload ({len(payload)} bytes) from {node_id}")
            return
        try:
            msg = SapientMessage.FromString(payload)
        except DecodeError:
            self.log.info(f"dropping undecodable payload from {node_id}")
            return

        kind = kind_of(msg)
        if kind == "registration":
            self._cancel_request(node_id)
        link = self.links.get(node_id)
        if link is None:
            if kind != "registration":
                self.log.info(f"dropping {kind} from unregistered {node_id}")
                return
            link = await self._open_link(node_id)
        try:
            await link.send(msg)
        except OSError as e:
            self.log.info(f"lost Apex socket for {node_id} ({e!r})")
            self._link_lost(node_id)

    async def _open_link(self, node_id: str) -> Link:
        link = await Link.connect(self.apex_host, self.apex_port, self.log)
        self.links[node_id] = link
        reader = asyncio.create_task(self._forward_replies(node_id, link))
        reader.add_done_callback(self._on_task_done)
        self._readers[node_id] = reader
        if self._token_alive.get(node_id) is False:
            # The token went during the connect, and its hold window may already have run out.
            self._start_hold(node_id)
        return link

    async def _forward_replies(self, node_id: str, link: Link) -> None:
        while True:
            try:
                reply = await link.receive()
                key = down_key(node_id, kind_of(reply))
            except (asyncio.IncompleteReadError, OSError):
                self.log.info(f"Apex closed the socket for {node_id}")
                break
            except (DecodeError, ValueError) as e:
                self.log.info(f"bad reply from Apex for {node_id} ({e!r}); dropping its socket")
                break
            # Outside the try: a failed publish is the bridge's failure, not this link's.
            await self.session.publish(key, reply)
        self._link_lost(node_id)

    def _on_task_done(self, task: asyncio.Task) -> None:
        if not task.cancelled() and task.exception() and not self._task_failed.done():
            self._task_failed.set_exception(task.exception())

    def _link_lost(self, node_id: str) -> None:
        """The socket failed under a node: without a request, a live node would never come back."""
        self._forget_link(node_id)
        if self._token_alive.get(node_id) is True:
            self._schedule_request(node_id)

    def _forget_link(self, node_id: str) -> None:
        link = self.links.pop(node_id, None)
        reader = self._readers.pop(node_id, None)
        if link is not None:
            link.close()
        if reader is not None and reader is not asyncio.current_task():
            reader.cancel()

    def _close_link(self, node_id: str) -> None:
        if node_id in self.links:
            self.log.info(f"closing Apex socket for {node_id}")
            self._forget_link(node_id)

    async def _track_liveliness(self, changes: asyncio.Queue[tuple[str, bool]]) -> None:
        while True:
            key, alive = await changes.get()
            self._on_liveliness(key, alive)

    def _on_liveliness(self, key: str, alive: bool) -> None:
        try:
            node_id = node_id_from_live_key(key)
        except ValueError:
            self.log.info(f"ignoring liveliness on bad key {key!r}")
            return
        already_alive = self._token_alive.get(node_id) is True
        self._token_alive[node_id] = alive
        if not alive:
            self._cancel_request(node_id)
            self._start_hold(node_id)
            return
        self._stop_hold(node_id)
        if not already_alive and node_id not in self.links:
            self._schedule_request(node_id)

    def _schedule_request(self, node_id: str) -> None:
        if node_id not in self._pending_requests:
            pending = asyncio.create_task(self._request_after_grace(node_id))
            pending.add_done_callback(self._on_task_done)
            self._pending_requests[node_id] = pending

    def _cancel_request(self, node_id: str) -> None:
        pending = self._pending_requests.pop(node_id, None)
        if pending is not None:
            pending.cancel()

    async def _request_after_grace(self, node_id: str) -> None:
        await asyncio.sleep(self.request_grace_seconds)
        # A registration handled just before the token was reported leaves a link and no cancel.
        if node_id not in self.links:
            await self._request_registration(node_id)
        del self._pending_requests[node_id]

    async def _request_registration(self, node_id: str) -> None:
        task = Task(
            task_id=new_ulid(),
            task_name="bridge: request registration",
            command=Task.Command(request="Registration"),
        )
        request = stamp(SapientMessage(task=task), self.bridge_node_id, node_id)
        await self.session.publish(down_key(node_id, "task"), request)
        self.log.info(f"requested registration from {node_id}")

    def _start_hold(self, node_id: str) -> None:
        # Armed even with no link yet: a registration still in flight may open one after the token went.
        if node_id not in self._hold_timers:
            self._hold_timers[node_id] = asyncio.get_running_loop().call_later(
                self.hold_seconds, self._hold_expired, node_id
            )

    def _stop_hold(self, node_id: str) -> None:
        timer = self._hold_timers.pop(node_id, None)
        if timer is not None:
            timer.cancel()

    def _hold_expired(self, node_id: str) -> None:
        del self._hold_timers[node_id]
        self._close_link(node_id)

    async def _close_all(self) -> None:
        for timer in self._hold_timers.values():
            timer.cancel()
        self._hold_timers.clear()
        tasks = [*self._readers.values(), *self._pending_requests.values()]
        for node_id in list(self.links):
            self._close_link(node_id)
        for node_id in list(self._pending_requests):
            self._cancel_request(node_id)
        await asyncio.gather(*tasks, return_exceptions=True)


async def run(
    apex_host: str,
    apex_port: int,
    connect: str,
    hold_seconds: float,
    request_grace_seconds: float,
    log: logging.Logger,
    bridge_node_id: str,
) -> None:
    """Bridge until the Zenoh session is lost, drop every link, then reopen and bridge again.

    A bridge failure raises, so the process exits and the container's restart policy applies.
    """
    loop = asyncio.get_running_loop()
    while True:
        session = await open_session(connect, loop, log)
        bridge = ApexSideBridge(
            session,
            apex_host,
            apex_port,
            hold_seconds,
            log=log,
            bridge_node_id=bridge_node_id,
            request_grace_seconds=request_grace_seconds,
        )
        try:
            await bridge.run()
            log.info("Zenoh session lost; dropping all links and reconnecting")
        finally:
            session.close()


def main() -> None:
    log = setup_logging("bridge-apex-side")
    apex_host = os.environ.get("APEX_HOST", "apex")
    apex_port = int(os.environ.get("APEX_PORT", "5020"))
    connect = os.environ.get("ZENOH_CONNECT", "tcp/zenohd:7447")
    hold_seconds = float(os.environ.get("HOLD_SECONDS", "120"))
    request_grace_seconds = float(os.environ.get("REQUEST_GRACE_SECONDS", "3.0"))
    bridge_node_id = os.environ.get("BRIDGE_NODE_ID") or str(uuid.uuid4())
    try:
        asyncio.run(run(apex_host, apex_port, connect, hold_seconds, request_grace_seconds, log, bridge_node_id))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
