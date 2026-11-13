import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass

from fastapi import WebSocket

from utils.metrics import BROADCAST_FAILURES

logger = logging.getLogger(__name__)

_SEND_TIMEOUT = 5.0

_PER_CLIENT_QUEUE_MAXSIZE = 512


@dataclass(frozen=True)
class BroadcastResult:
    """Outcome of a :meth:`RoomConnectionManager.send_to_room` broadcast.

    A queued message only proves the payload was handed to a client's sender
    task; it is NOT an acknowledgement. Callers that need proof of delivery
    (for example actuator control) must not treat ``queued > 0`` as confirmed
    execution.
    """

    eligible: int
    queued: int
    dropped: int

    @property
    def has_clients(self) -> bool:
        """True when at least one client was connected for the room/role."""
        return self.eligible > 0

    @property
    def fully_delivered(self) -> bool:
        """True when every connected client accepted the message."""
        return self.eligible > 0 and self.dropped == 0


class _ClientState:
    def __init__(self, ws: WebSocket, client_id: str):
        self.ws = ws
        self.client_id = client_id
        self.queue: asyncio.Queue[dict] = asyncio.Queue(
            maxsize=_PER_CLIENT_QUEUE_MAXSIZE
        )
        self.task: asyncio.Task | None = None
        self.stop_event: asyncio.Event = asyncio.Event()

    def start(self, on_dead) -> None:
        if self.task is None or self.task.done():
            self.stop_event.clear()
            self.task = asyncio.create_task(self._send_loop(on_dead))

    async def stop(self) -> None:
        if self.task is not None and not self.task.done():
            self.stop_event.set()
            try:
                await asyncio.wait_for(self.task, timeout=3.0)
            except asyncio.TimeoutError:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            self.task = None

    def enqueue(self, message: dict) -> bool:
        try:
            self.queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            logger.warning(
                "[Manager] Client '%s' send queue full (%d); dropping message.",
                self.client_id,
                self.queue.qsize(),
            )
            return False

    async def _send_loop(self, on_dead) -> None:
        while not self.stop_event.is_set():
            try:
                message = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            try:
                await asyncio.wait_for(
                    self.ws.send_json(message),
                    timeout=_SEND_TIMEOUT,
                )
            except Exception:
                logger.debug(
                    "[Manager] Client '%s' unreachable during send; marking dead.",
                    self.client_id,
                )
                await on_dead(self.client_id)
                return


class RoomConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, dict[str, dict[str, _ClientState]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        self.lock = asyncio.Lock()

    async def connect(
        self, room: str, role: str, client_id: str, websocket: WebSocket
    ) -> None:
        async with self.lock:
            state = _ClientState(websocket, client_id)
            self.rooms[room][role][client_id] = state

            def _make_dead_handler(r, ro, cid):
                async def _handler(dead_cid: str):
                    await self.disconnect(r, ro, dead_cid)

                return _handler

            state.start(_make_dead_handler(room, role, client_id))

    async def disconnect(self, room: str, role: str, client_id: str) -> None:
        async with self.lock:
            role_clients = self.rooms.get(room, {}).get(role, {})
            state = role_clients.pop(client_id, None)

            if not role_clients:
                self.rooms.get(room, {}).pop(role, None)
            if not self.rooms.get(room):
                self.rooms.pop(room, None)

        if state is not None:
            try:
                await state.stop()
            except Exception:
                logger.debug(
                    "[Manager] Exception while stopping client '%s' sender loop.",
                    client_id,
                )

    async def send_to_room(
        self, room: str, role: str, message: dict
    ) -> BroadcastResult:
        """Fan a message out to every client in a room/role.

        Returns an explicit :class:`BroadcastResult` so callers can tell "nobody
        was connected" apart from "the message was queued" and from "some
        queues were full". A queued message is not an acknowledgement.
        """
        async with self.lock:
            clients_snapshot = dict(self.rooms.get(room, {}).get(role, {}))

        eligible = len(clients_snapshot)
        if eligible == 0:
            return BroadcastResult(eligible=0, queued=0, dropped=0)

        failed_clients: list[str] = []

        async def _enqueue_one(cid: str, st: _ClientState):
            if not st.enqueue(message):
                # Per-client send queue full: the message was dropped, not sent.
                BROADCAST_FAILURES.labels(role=role, kind="dropped").inc()
                failed_clients.append(cid)

        tasks = [
            asyncio.create_task(_enqueue_one(cid, st))
            for cid, st in clients_snapshot.items()
        ]

        # return_exceptions=True keeps one client's failure from aborting the
        # broadcast to the others; each result is inspected below so failures
        # are surfaced instead of silently dropped.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for (cid, _st), result in zip(clients_snapshot.items(), results):
            if isinstance(result, BaseException):
                BROADCAST_FAILURES.labels(role=role, kind="error").inc()
                logger.error(
                    "[Manager] Enqueue failed for client '%s' (room='%s', role='%s').",
                    cid,
                    room,
                    role,
                    exc_info=result,
                )
                failed_clients.append(cid)

        failed = set(failed_clients)
        for cid in failed:
            await self.disconnect(room, role, cid)

        return BroadcastResult(
            eligible=eligible,
            queued=eligible - len(failed),
            dropped=len(failed),
        )

    async def send_to_client(
        self, room: str, role: str, client_id: str, message: dict
    ) -> None:
        async with self.lock:
            state = self.rooms.get(room, {}).get(role, {}).get(client_id)

        if state is None:
            return

        if not state.enqueue(message):
            await self.disconnect(room, role, client_id)


manager = RoomConnectionManager()
