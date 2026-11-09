"""ZenohSession: the adapter between the synchronous zenoh binding and asyncio.

The binding runs callbacks on its own threads, so they only ever reach asyncio objects through
loop.call_soon_threadsafe. Calls that can block on the network run in worker threads.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import zenoh

from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_keys import kind_of, qos_for


def _config(**settings: Any) -> zenoh.Config:
    """Build a Config from settings; "__" in a name stands for "/" in the zenoh config path."""
    config = zenoh.Config()
    config.insert_json5("scouting/multicast/enabled", "false")
    for name, value in settings.items():
        config.insert_json5(name.replace("__", "/"), json.dumps(value))
    return config


class ZenohSession:
    """An open zenoh session whose samples and liveliness changes arrive on asyncio queues."""

    def __init__(self, session: zenoh.Session, loop: asyncio.AbstractEventLoop) -> None:
        self._session = session
        self._loop = loop
        self._subscribers: list[zenoh.Subscriber] = []
        self._tokens: dict[str, zenoh.LivelinessToken] = {}
        self._transport_listener: zenoh.TransportEventsListener | None = None
        self.closed: asyncio.Event = asyncio.Event()

    @classmethod
    async def open(cls, connect: str, loop: asyncio.AbstractEventLoop) -> ZenohSession:
        """Open a client session to the router at connect, like tcp/zenohd:7447."""
        config = _config(mode="client", connect__endpoints=[connect])
        self = cls(await asyncio.to_thread(zenoh.open, config), loop)
        # A client has exactly one transport, the one to its router, so losing it ends the session.
        self._transport_listener = self._session.info.declare_transport_events_listener(
            self._on_transport_event
        )
        return self

    @classmethod
    async def open_peer_listen(cls, listen: str, loop: asyncio.AbstractEventLoop) -> ZenohSession:
        """Test only: open a peer listening on listen, standing in for the router."""
        config = _config(mode="peer", listen__endpoints=[listen])
        return cls(await asyncio.to_thread(zenoh.open, config), loop)

    def _call_in_loop(self, func: Callable[..., Any], *args: Any) -> None:
        """Run func on the event loop; called from binding threads."""
        try:
            self._loop.call_soon_threadsafe(func, *args)
        except RuntimeError:
            pass  # the loop has shut down, so nobody is left to receive this

    def _on_transport_event(self, event: zenoh.TransportEvent) -> None:
        if event.kind == zenoh.SampleKind.DELETE:
            self._call_in_loop(self.closed.set)

    async def publish(self, key: str, msg: SapientMessage, fused: bool = False) -> None:
        priority, congestion_control, express = qos_for(kind_of(msg), fused)
        # A BLOCK put can stall on a congested link, which must not stall the event loop.
        await asyncio.to_thread(
            self._session.put,
            key,
            msg.SerializeToString(),
            encoding=zenoh.Encoding.APPLICATION_PROTOBUF,
            priority=priority,
            congestion_control=congestion_control,
            express=express,
        )

    def subscribe(self, keyexpr: str) -> asyncio.Queue[tuple[str, bytes]]:
        queue: asyncio.Queue[tuple[str, bytes]] = asyncio.Queue()

        def on_sample(sample: zenoh.Sample) -> None:
            self._call_in_loop(queue.put_nowait, (str(sample.key_expr), sample.payload.to_bytes()))

        self._subscribers.append(self._session.declare_subscriber(keyexpr, on_sample))
        return queue

    def declare_token(self, key: str) -> None:
        if key not in self._tokens:
            self._tokens[key] = self._session.liveliness().declare_token(key)

    def undeclare_token(self, key: str) -> None:
        token = self._tokens.pop(key, None)
        if token is not None:
            token.undeclare()

    def liveliness(self, keyexpr: str) -> asyncio.Queue[tuple[str, bool]]:
        """Report (key, True) when a token appears and (key, False) when it goes.

        Tokens that already exist are reported as appearing.
        """
        queue: asyncio.Queue[tuple[str, bool]] = asyncio.Queue()

        def on_sample(sample: zenoh.Sample) -> None:
            appeared = sample.kind == zenoh.SampleKind.PUT
            self._call_in_loop(queue.put_nowait, (str(sample.key_expr), appeared))

        self._subscribers.append(
            self._session.liveliness().declare_subscriber(keyexpr, on_sample, history=True)
        )
        return queue

    async def alive(self, keyexpr: str) -> list[str]:
        """Return the keys of the tokens currently alive under keyexpr."""

        def query() -> list[str]:
            replies = self._session.liveliness().get(keyexpr)
            return [str(reply.ok.key_expr) for reply in replies if reply.ok is not None]

        return await asyncio.to_thread(query)

    def close(self) -> None:
        self.closed.set()
        if not self._session.is_closed():
            self._session.close()
