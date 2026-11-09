import asyncio

import pytest
import zenoh

from sapient_link import load_template
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage
from zenoh_keys import kind_of, qos_for


@pytest.fixture
def templates():
    """load_template(group, name): a SapientMessage from templates/<group>/Default.<name>.json."""
    return load_template


def _matches(keyexpr: str, key: str) -> bool:
    return zenoh.KeyExpr(keyexpr).intersects(zenoh.KeyExpr(key))


class FakeZenohSession:
    """In-memory stand-in for zenoh_io.ZenohSession."""

    def __init__(self) -> None:
        self.published: list[tuple[str, bytes, tuple]] = []
        self.tokens: set[str] = set()
        self.closed = asyncio.Event()
        self._subscriptions: list[tuple[str, asyncio.Queue]] = []
        self._liveliness: list[tuple[str, asyncio.Queue]] = []

    async def publish(self, key: str, msg: SapientMessage, fused: bool = False) -> None:
        payload = msg.SerializeToString()
        self.published.append((key, payload, qos_for(kind_of(msg), fused)))
        self.inject(key, payload)

    def inject(self, key: str, payload: bytes) -> None:
        """Deliver a sample to matching subscriptions as if it came from the router."""
        for keyexpr, queue in self._subscriptions:
            if _matches(keyexpr, key):
                queue.put_nowait((key, payload))

    def subscribe(self, keyexpr: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscriptions.append((keyexpr, queue))
        return queue

    def _report_liveliness(self, key: str, appeared: bool) -> None:
        for keyexpr, queue in self._liveliness:
            if _matches(keyexpr, key):
                queue.put_nowait((key, appeared))

    def declare_token(self, key: str) -> None:
        if key not in self.tokens:
            self.tokens.add(key)
            self._report_liveliness(key, True)

    def undeclare_token(self, key: str) -> None:
        if key in self.tokens:
            self.tokens.remove(key)
            self._report_liveliness(key, False)

    def liveliness(self, keyexpr: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        for key in self.tokens:
            if _matches(keyexpr, key):
                queue.put_nowait((key, True))
        self._liveliness.append((keyexpr, queue))
        return queue

    async def alive(self, keyexpr: str) -> list[str]:
        return [key for key in self.tokens if _matches(keyexpr, key)]

    def close(self) -> None:
        for key in list(self.tokens):
            self.undeclare_token(key)
        self.closed.set()
