import asyncio
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid7

from schemas import HydroponicIn

logger = logging.getLogger(__name__)

_PROFILE_CACHE_TTL = 30.0

_RING_BUFFER_SIZE = 256

_PROCESS_QUEUE_MAXSIZE = 4096


@dataclass(order=True)
class PendingPacket:
    priority: float = field(compare=True)
    source: str = field(compare=False)
    data: dict[str, Any] = field(compare=False)
    received_at: float = field(compare=False, default_factory=time.monotonic)


class HydroponicAggregator:
    def __init__(
        self,
        timeout: float = 60.0,
        min_interval: float = 0.1,
        ring_size: int = _RING_BUFFER_SIZE,
        queue_maxsize: int = _PROCESS_QUEUE_MAXSIZE,
    ):
        self.timeout: float = timeout
        self.min_interval: float = min_interval

        self._buffers: dict[str, deque[PendingPacket]] = {
            "plant": deque(maxlen=ring_size),
            "environment": deque(maxlen=ring_size),
        }
        self._buffer_lock: asyncio.Lock = asyncio.Lock()

        self.actuator_state: dict[str, bool] = {
            "pump_status": False,
            "light_status": False,
            "automation_status": False,
        }
        self._actuator_lock: asyncio.Lock = asyncio.Lock()

        self.last_received: dict[str, float] = {}

        self._cached_profile = None
        self._profile_cached_at: float = 0.0
        self._profile_lock: asyncio.Lock = asyncio.Lock()

        self.process_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=queue_maxsize
        )

        self._drain_task: asyncio.Task | None = None
        self._drain_stop_event: asyncio.Event = asyncio.Event()
        self._last_pair_ts: float = 0.0

    # ------------------------------------------------------------------
    # Lifespan helpers
    # ------------------------------------------------------------------

    def start_background_tasks(self) -> None:
        if self._drain_task is None or self._drain_task.done():
            self._drain_stop_event.clear()
            self._drain_task = asyncio.create_task(self._drain_timeout_loop())

    async def stop_background_tasks(self) -> None:
        if self._drain_task is not None and not self._drain_task.done():
            self._drain_stop_event.set()
            try:
                await asyncio.wait_for(self._drain_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._drain_task.cancel()
                try:
                    await self._drain_task
                except asyncio.CancelledError:
                    pass
            self._drain_task = None

    # ------------------------------------------------------------------
    # Actuator state
    # ------------------------------------------------------------------

    def update_actuator_state(self, state: dict) -> None:
        for key in ("pump_status", "light_status", "automation_status"):
            if key in state:
                self.actuator_state[key] = state[key]

    async def update_actuator_state_safe(self, state: dict) -> None:
        async with self._actuator_lock:
            self.update_actuator_state(state)

    # ------------------------------------------------------------------
    # Nutrition profile cache
    # ------------------------------------------------------------------

    async def get_cached_profile(self):
        now = time.monotonic()
        async with self._profile_lock:
            if (now - self._profile_cached_at) < _PROFILE_CACHE_TTL and (
                self._cached_profile is not None or self._profile_cached_at > 0
            ):
                return self._cached_profile

        profile = None
        try:
            from utils.deps import get_db_session
            from services.nutrition_service import NutritionService

            async with get_db_session() as session:
                service = NutritionService(session)
                profile = await service.get_active_profile()
        except Exception:
            logger.exception("[Aggregator] Failed to refresh nutrition profile cache.")

        async with self._profile_lock:
            if profile is not None:
                self._cached_profile = profile
            self._profile_cached_at = time.monotonic()
            return self._cached_profile

    def invalidate_profile_cache(self) -> None:
        self._profile_cached_at = 0.0

    # ------------------------------------------------------------------
    # Data gathering (public entry point)
    # ------------------------------------------------------------------

    async def gather_data(self, source: str, data: dict) -> bool:
        if source not in self._buffers:
            logger.warning("[Aggregator] Unknown source '%s'; dropping packet.", source)
            return False

        now = time.monotonic()
        async with self._buffer_lock:
            last = self.last_received.get(source)
            if last is not None:
                delta = now - last
                if delta < self.min_interval:
                    logger.debug(
                        "[Aggregator] Rate-limit drop for '%s' (%.3fs < %.3fs).",
                        source,
                        delta,
                        self.min_interval,
                    )
                    return False
            self.last_received[source] = now

            buf = self._buffers[source]
            if len(buf) == buf.maxlen:
                dropped = buf.popleft()
                logger.warning(
                    "[Aggregator] Ring buffer full for '%s'; dropped oldest packet "
                    "from %.2fs ago. Consider raising ring_size or lowering "
                    "publish rate.",
                    source,
                    now - dropped.received_at,
                )

            pkt = PendingPacket(
                priority=now,
                source=source,
                data=dict(data),
                received_at=now,
            )
            buf.append(pkt)
            logger.info("[Aggregator] Buffered packet from node: %s", source)

        await self._try_pair_snapshots()
        return True

    # ------------------------------------------------------------------
    # Pairing logic
    # ------------------------------------------------------------------

    async def _try_pair_snapshots(self) -> None:
        async with self._buffer_lock:
            plant_buf = self._buffers["plant"]
            env_buf = self._buffers["environment"]

            paired_count = 0
            while plant_buf and env_buf:
                plant_pkt = plant_buf[0]
                env_pkt = env_buf[0]

                if abs(plant_pkt.received_at - env_pkt.received_at) > self.timeout:
                    if plant_pkt.received_at < env_pkt.received_at:
                        dropped = plant_buf.popleft()
                        logger.warning(
                            "[Aggregator] Stale 'plant' packet dropped "
                            "(%.2fs older than oldest 'environment').",
                            env_pkt.received_at - dropped.received_at,
                        )
                    else:
                        dropped = env_buf.popleft()
                        logger.warning(
                            "[Aggregator] Stale 'environment' packet dropped "
                            "(%.2fs older than oldest 'plant').",
                            plant_pkt.received_at - dropped.received_at,
                        )
                    continue

                plant_buf.popleft()
                env_buf.popleft()
                snapshot = self._build_snapshot(plant_pkt.data, env_pkt.data)
                self._last_pair_ts = time.monotonic()
                await self._enqueue_snapshot(snapshot)
                paired_count += 1

            if paired_count:
                logger.info(
                    "[Aggregator] Paired %d snapshot(s). Queued for processing.",
                    paired_count,
                )

    async def _drain_timeout_loop(self) -> None:
        check_interval = max(1.0, min(self.timeout / 4.0, 10.0))
        while not self._drain_stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._drain_stop_event.wait(),
                    timeout=check_interval,
                )
            except asyncio.TimeoutError:
                pass

            if self._drain_stop_event.is_set():
                return

            try:
                await self._try_pair_snapshots()
                await self._partial_flush_if_stale()
            except Exception:
                logger.exception("[Aggregator] Unexpected error in drain loop.")

    async def _partial_flush_if_stale(self) -> None:
        now = time.monotonic()
        async with self._buffer_lock:
            for source, buf in self._buffers.items():
                if not buf:
                    continue
                oldest = buf[0]
                age = now - oldest.received_at
                if age > self.timeout:
                    count_before = len(buf)
                    buf.clear()
                    logger.warning(
                        "[Aggregator] Partial-flush: cleared %d stale packet(s) "
                        "from '%s' (oldest %.2fs). Partner source silent.",
                        count_before,
                        source,
                        age,
                    )

    async def _enqueue_snapshot(self, snapshot: HydroponicIn) -> None:
        payload = {
            "snapshot": snapshot.model_dump(),
            "ts": time.monotonic(),
        }
        try:
            self.process_queue.put_nowait(payload)
        except asyncio.QueueFull:
            logger.error(
                "[Aggregator] Process queue full (size=%d); snapshot dropped. "
                "DB or broadcast worker is unable to keep up. "
                "Consider increasing queue_maxsize or scaling workers.",
                self.process_queue.qsize(),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_snapshot(self, plant_data: dict, env_data: dict) -> HydroponicIn:
        combined = {
            **plant_data,
            **env_data,
            **self.actuator_state,
        }
        return HydroponicIn(dataid=uuid7(), **combined)


aggregator = HydroponicAggregator(timeout=60.0)
