"""Node-side bridge: carries a legacy TCP SAPIENT sensor's traffic over Zenoh.

Accepts length-prefixed SapientMessages, republishes them on the node's up keys and declares a
liveliness token per node. Messages on the node's down keys are written back to the socket.
Losing the router leaves every sensor connected: the session restores the tokens and subscriptions
when the router returns, and what the sensors send meanwhile is lost.
"""
import asyncio
import logging
import os
import struct

import zenoh
from google.protobuf.message import DecodeError

from sapient_link import Link, setup_logging
from zenoh_io import ZenohSession, open_session
from zenoh_keys import DOWN_FOR, kind_of, live_key, up_key

Down = asyncio.Queue[tuple[str, bytes]]


class NodeSideBridge:
    def __init__(self, session: ZenohSession, log: logging.Logger) -> None:
        self.session = session
        self.log = log
        self.nodes: dict[str, asyncio.StreamWriter] = {}
        # ZenohSession cannot unsubscribe, so a reconnecting node reuses its first subscription.
        self._down: dict[str, Down] = {}
        self._handlers: set[asyncio.Task] = set()

    async def serve(self, port: int) -> None:
        server = await asyncio.start_server(self.handle, "0.0.0.0", port)
        self.log.info(f"listening for SAPIENT nodes on port {port}")
        async with server:
            await server.serve_forever()

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        handler = asyncio.current_task()
        self._handlers.add(handler)
        try:
            await self._serve_connection(Link(reader, writer))
        finally:
            self._handlers.discard(handler)
            writer.close()

    async def close_all(self) -> None:
        """Drop every connection, undeclaring its token, and wait until that has happened."""
        handlers = list(self._handlers)
        for handler in handlers:
            handler.cancel()
        await asyncio.gather(*handlers, return_exceptions=True)

    async def _serve_connection(self, link: Link) -> None:
        try:
            registration = await link.receive()
        except (asyncio.IncompleteReadError, ConnectionError):
            self.log.info("connection closed before registering")
            return
        except DecodeError:
            self.log.info("first message must be a registration")
            return
        if kind_of(registration) != "registration":
            self.log.info("first message must be a registration")
            return

        node_id = registration.node_id
        try:
            token = live_key(node_id)
            registration_key = up_key(node_id, "registration")
        except ValueError:
            self.log.info(f"invalid node_id {node_id!r}; refusing")
            return
        if node_id in self.nodes:
            self.log.info(f"node_id already connected; refusing {node_id}")
            return

        self.nodes[node_id] = link.writer
        try:
            self.session.declare_token(token)
            down = self._down_queue(node_id)
            await self.session.publish(registration_key, registration)
            self.log.info(f"node {node_id} registered")
            await self._forward(link, node_id, down)
        except (asyncio.IncompleteReadError, ConnectionError):
            self.log.info(f"node {node_id} disconnected")
        except Exception as e:
            self.log.info(f"node {node_id} dropped: {e!r}")
        finally:
            try:
                self.session.undeclare_token(token)
            finally:
                del self.nodes[node_id]

    def _down_queue(self, node_id: str) -> Down:
        """The node's down queue, emptied of anything sent while it was away."""
        down = self._down.get(node_id)
        if down is None:
            down = self._down[node_id] = self.session.subscribe(DOWN_FOR(node_id))
        while not down.empty():
            down.get_nowait()
        return down

    async def _forward(self, link: Link, node_id: str, down: Down) -> None:
        """Run both directions until one fails, then raise why it did."""
        tasks = {
            asyncio.create_task(self._forward_up(link, node_id)),
            asyncio.create_task(self._forward_down(link.writer, down)),
        }
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        done.pop().result()

    async def _forward_up(self, link: Link, node_id: str) -> None:
        while True:
            msg = await link.receive()
            try:
                await self.session.publish(up_key(node_id, kind_of(msg)), msg)
            except zenoh.ZError as e:
                self.log.info(f"lost a message from {node_id}: {e}")

    async def _forward_down(self, writer: asyncio.StreamWriter, down: Down) -> None:
        while True:
            _, payload = await down.get()
            writer.write(struct.pack("<I", len(payload)) + payload)
            await writer.drain()


async def log_transport_changes(session: ZenohSession, log: logging.Logger) -> None:
    while True:
        if await session.transport_changes.get():
            log.info("Zenoh transport back; tokens and subscriptions restored by the session")
        else:
            log.info("Zenoh transport lost; keeping every sensor connected")


async def run(port: int, connect: str, log: logging.Logger) -> None:
    """Serve until the listener fails, which raises, or the session is closed, which returns.

    Either way the process exits and the container's restart policy applies. A lost router ends
    nothing: the session reconnects by itself.
    """
    session = await open_session(connect, asyncio.get_running_loop(), log)
    bridge = NodeSideBridge(session, log)
    server = asyncio.create_task(bridge.serve(port))
    transport = asyncio.create_task(log_transport_changes(session, log))
    closed = asyncio.create_task(session.closed.wait())
    tasks = (server, transport, closed)
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for failable in (server, transport):
            if failable.done():
                failable.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, bridge.close_all(), return_exceptions=True)
        session.close()


def main() -> None:
    log = setup_logging("bridge-node-side")
    port = int(os.environ.get("LISTEN_PORT", "5020"))
    connect = os.environ.get("ZENOH_CONNECT", "tcp/zenohd:7447")
    try:
        asyncio.run(run(port, connect, log))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
