import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)

_SEND_TIMEOUT = 5.0

_PER_CLIENT_QUEUE_MAXSIZE = 512


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

    async def send_to_room(self, room: str, role: str, message: dict) -> None:
        async with self.lock:
            clients_snapshot = dict(self.rooms.get(room, {}).get(role, {}))

        if not clients_snapshot:
            return

        dead_clients: list[str] = []

        async def _enqueue_one(cid: str, st: _ClientState):
            if not st.enqueue(message):
                dead_clients.append(cid)

        tasks = [
            asyncio.create_task(_enqueue_one(cid, st))
            for cid, st in clients_snapshot.items()
        ]
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                logger.exception("[Manager] Unexpected error enqueuing broadcast.")

        for cid in dead_clients:
            await self.disconnect(room, role, cid)

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
