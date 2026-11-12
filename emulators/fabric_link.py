"""The host fusion node's link to the fabric, with the same interface as ZenohFusionLink.

Its children are the fusion nodes of pods, which the pod bridges put on the fabric below each
pod's anchor and site (fabric_keys). The link learns where each node lives from the first key or
liveliness token that names it, and keeps that route for the life of the process: a node ID belongs
to the anchor that brought it first, and a sample naming it below any other anchor is dropped.
"""
from __future__ import annotations

import asyncio
import collections
import logging
from typing import TYPE_CHECKING, NamedTuple

import fabric_keys
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

if TYPE_CHECKING:
    from zenoh_io import ZenohSession


class Route(NamedTuple):
    anchor: str
    site: str


class FabricFusionLink:
    """A fusion node's transport on the fabric's keys."""

    children_are_fusion_nodes = True  # on the fabric a fusion node is a child of the host
    has_parent = False  # the host has no parent in step 1

    def __init__(
        self,
        session: ZenohSession,
        fusion_id: str,
        anchor: str,
        site: str,
        samples: list[asyncio.Queue[tuple[str, bytes]]],
        log: logging.Logger,
    ):
        # Check the own anchor and site now, so a bad configuration fails at start and not at first send.
        fabric_keys.key_for(anchor, site, "status_report", fusion_id)
        self.session = session
        self.fusion_id = fusion_id
        self.anchor = anchor
        self.site = site
        self.samples = samples
        self.log = log
        self.live_all: str = fabric_keys.live_subscription()
        self.routes: dict[str, Route] = {}  # node_id -> where it lives, set once
        self.last_sample: tuple[str, bytes] = ("", b"")  # (key, payload) of the latest message from a node
        self._ready: collections.deque[tuple[str, bytes]] = collections.deque()
        self._refused: set[tuple[str, str]] = set()  # (node_id, anchor) pairs already logged

    @classmethod
    async def connect(
        cls, session: ZenohSession, fusion_id: str, anchor: str, site: str, log: logging.Logger
    ) -> "FabricFusionLink":
        # A wildcard in the first part only: never "**" on the fabric.
        samples = [session.subscribe(expr) for expr in fabric_keys.subscriptions()]
        log.info(f"joined the fabric as fusion node {fusion_id} below anchor {anchor}, site {site}")
        return cls(session, fusion_id, anchor, site, samples, log)

    # ---- routes ------------------------------------------------------------------------------

    def _learn(self, node_id: str, anchor: str, site: str) -> bool:
        """Record where node_id lives if it is new; False if it already belongs to another anchor."""
        route = self.routes.setdefault(node_id, Route(anchor, site))
        if route.anchor == anchor:
            return True
        if (node_id, anchor) not in self._refused:
            self._refused.add((node_id, anchor))
            self.log.info(
                f"node {node_id} belongs to anchor {route.anchor}; dropping what names it below anchor {anchor}"
            )
        return False

    def owner_of(self, key: str) -> str | None:
        """The node a data key names, or None for a malformed key."""
        try:
            return fabric_keys.parse(key).node_id
        except ValueError:
            return None

    def node_of_live_key(self, key: str) -> str:
        """The node a liveliness key names. ValueError for a bad key or one below another anchor."""
        parsed = fabric_keys.parse_live(key)
        if not self._learn(parsed.node_id, parsed.anchor, parsed.site):
            raise ValueError(f"node {parsed.node_id} belongs to another anchor than that of {key!r}")
        return parsed.node_id

    # ---- outgoing ----------------------------------------------------------------------------

    async def send(self, msg: SapientMessage) -> bool:
        """Publish to msg.destination_id if set, at that node's site; otherwise as this node's own output.

        Both go below this node's own anchor. False when nothing was sent: no route, a kind with no key,
        or a key that cannot be built. This never raises for a key, so a bad route cannot end the node.
        """
        kind = msg.WhichOneof("content")
        if msg.destination_id:
            node = msg.destination_id
            route = self.routes.get(node)
            if route is None:
                self.log.info(f"no route to node {node}; {kind} not sent")
                return False
            site, fused = route.site, False
        elif kind in fabric_keys.TELEMETRY_KINDS:
            node, site, fused = self.fusion_id, self.site, True
        else:
            self.log.info(f"a {kind} with no destination has no key on the fabric; not sent")
            return False
        try:
            key = fabric_keys.key_for(self.anchor, site, kind, node)
        except ValueError as e:
            self.log.info(f"no key for a {kind} to node {node}: {e}; not sent")
            return False
        await self.session.publish(key, msg, fused=fused)
        return True

    async def send_upward(self, msg: SapientMessage):
        """Nothing: the host has no parent."""

    # ---- incoming ----------------------------------------------------------------------------

    async def _next_sample(self) -> tuple[str, bytes]:
        """Next (key, payload) from any of the subscriptions; ConnectionError once the session is closed."""
        while not self._ready:
            if self.session.closed.is_set():
                raise ConnectionError("the Zenoh session is closed")
            gets = [asyncio.ensure_future(queue.get()) for queue in self.samples]
            closed = asyncio.ensure_future(self.session.closed.wait())
            try:
                await asyncio.wait([*gets, closed], return_when=asyncio.FIRST_COMPLETED)
            finally:
                for waiter in (*gets, closed):
                    waiter.cancel()  # a cancelled get leaves its item in the queue
            self._ready.extend(get.result() for get in gets if get.done() and not get.cancelled())
            if self.session.closed.is_set():
                raise ConnectionError("the Zenoh session is closed")
        return self._ready.popleft()

    def _accept(self, key: str) -> bool:
        """Whether a sample on key is a node's message for this link to give out."""
        if key.split("/", 1)[0] == self.anchor:
            return False  # the wildcard also matches this node's own output
        try:
            parsed = fabric_keys.parse(key)
        except ValueError as e:
            self.log.info(f"sample on malformed key {key!r} dropped: {e}")
            return False
        return self._learn(parsed.node_id, parsed.anchor, parsed.site)

    async def receive_raw(self) -> tuple[bytes, SapientMessage]:
        """Next message from a node, with its payload bytes.

        Raises ConnectionError when the session is closed, and DecodeError for an undecodable
        message; last_sample then still holds its key and payload.
        """
        while True:
            key, payload = await self._next_sample()
            if self._accept(key):
                self.last_sample = (key, payload)
                return payload, SapientMessage.FromString(payload)

    async def receive(self) -> SapientMessage:
        _, msg = await self.receive_raw()
        return msg

    def close(self):
        """Nothing to release: the host declares no token, and the session outlives the link."""
