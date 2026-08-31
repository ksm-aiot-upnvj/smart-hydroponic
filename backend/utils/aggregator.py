import asyncio
import os
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

_DEFAULT_MIN_INTERVAL = float(os.getenv("HYDROPONIC_MIN_INTERVAL_SECONDS", "0.1"))
_DEFAULT_PAIR_TIMEOUT = float(os.getenv("HYDROPONIC_PAIR_TIMEOUT_SECONDS", "60.0"))


@dataclass(order=True)
class PendingPacket:
    priority: float = field(compare=True)
    source: str = field(compare=False)
    data: dict[str, Any] = field(compare=False)
    received_at: float = field(compare=False, default_factory=time.monotonic)


async def _best_effort_log(
    *, event_type: str, severity: str, description: str, data_ref: str | None = None
) -> None:
    """Fire-and-forget structured log write; never raises into caller."""
    try:
        from utils.deps import get_db_session
        from services.log_service import LogService

        async with get_db_session() as session:
            svc = LogService(session)
            await svc.write_log(
                event_type=event_type,
                severity=severity,
                description=description,
                data_ref=data_ref,
            )
    except Exception:
        logger.exception("[Aggregator] Failed to write log entry: %s", description)


class HydroponicAggregator:
    def __init__(
        self,
        timeout: float = _DEFAULT_PAIR_TIMEOUT,
        min_interval: float = _DEFAULT_MIN_INTERVAL,
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

        self._last_drop_log_at: dict[str, float] = {}
        self._drop_log_min_interval: float = 5.0

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
    # Drop-log throttling helper
    # ------------------------------------------------------------------

    def _should_log_drop(self, key: str) -> bool:
        """Rate-limit our own drop-logging so a sustained flood doesn't
        also flood the logs table. Returns True if enough time has passed
        since we last wrote a log entry for this drop `key`."""
        now = time.monotonic()
        last = self._last_drop_log_at.get(key, 0.0)
        if now - last >= self._drop_log_min_interval:
            self._last_drop_log_at[key] = now
            return True
        return False

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
                    if self._should_log_drop(f"rate_limit:{source}"):
                        asyncio.create_task(
                            _best_effort_log(
                                event_type="system",
                                severity="warning",
                                description=(
                                    f"Rate-limit drop on '{source}' "
                                    f"({delta:.3f}s < {self.min_interval:.3f}s min interval). "
                                    "Further repeats in the next "
                                    f"{self._drop_log_min_interval:.0f}s window are suppressed."
                                ),
                            )
                        )
                    return False
            self.last_received[source] = now

            buf = self._buffers[source]
            if len(buf) == buf.maxlen:
                dropped = buf.popleft()
                age = now - dropped.received_at
                logger.warning(
                    "[Aggregator] Ring buffer full for '%s'; dropped oldest packet "
                    "from %.2fs ago. Consider raising ring_size or lowering "
                    "publish rate.",
                    source,
                    age,
                )
                if self._should_log_drop(f"ring_full:{source}"):
                    asyncio.create_task(
                        _best_effort_log(
                            event_type="system",
                            severity="error",
                            description=(
                                f"Ring buffer full for '{source}'; oldest packet "
                                f"({age:.2f}s old) dropped. Consumer may be falling "
                                "behind or publish rate is too high."
                            ),
                        )
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
        stale_events: list[tuple[str, float]] = []

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
                        age = env_pkt.received_at - dropped.received_at
                        logger.warning(
                            "[Aggregator] Stale 'plant' packet dropped "
                            "(%.2fs older than oldest 'environment').",
                            age,
                        )
                        stale_events.append(("plant", age))
                    else:
                        dropped = env_buf.popleft()
                        age = plant_pkt.received_at - dropped.received_at
                        logger.warning(
                            "[Aggregator] Stale 'environment' packet dropped "
                            "(%.2fs older than oldest 'plant').",
                            age,
                        )
                        stale_events.append(("environment", age))
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

        for source, age in stale_events:
            if self._should_log_drop(f"stale_pair:{source}"):
                asyncio.create_task(
                    _best_effort_log(
                        event_type="system",
                        severity="warning",
                        description=(
                            f"Stale '{source}' packet dropped during pairing "
                            f"({age:.2f}s beyond pairing timeout of {self.timeout:.0f}s). "
                            "Partner source may be silent or delayed."
                        ),
                    )
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
        flush_events: list[tuple[str, int, float]] = []

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
                    flush_events.append((source, count_before, age))

        for source, count, age in flush_events:
            if self._should_log_drop(f"partial_flush:{source}"):
                asyncio.create_task(
                    _best_effort_log(
                        event_type="system",
                        severity="error",
                        description=(
                            f"Partial-flush cleared {count} stale packet(s) from "
                            f"'{source}' (oldest {age:.2f}s old). Partner source "
                            "appears silent — check device connectivity."
                        ),
                    )
                )

    async def _enqueue_snapshot(self, snapshot: HydroponicIn) -> None:
        payload = {
            "snapshot": snapshot.model_dump(),
            "ts": time.monotonic(),
        }
        try:
            self.process_queue.put_nowait(payload)
        except asyncio.QueueFull:
            qsize = self.process_queue.qsize()
            logger.error(
                "[Aggregator] Process queue full (size=%d); snapshot dropped. "
                "DB or broadcast worker is unable to keep up. "
                "Consider increasing queue_maxsize or scaling workers.",
                qsize,
            )
            if self._should_log_drop("queue_full"):
                asyncio.create_task(
                    _best_effort_log(
                        event_type="system",
                        severity="critical",
                        description=(
                            f"Process queue full (maxsize reached, size={qsize}); "
                            f"snapshot dropped (dataid={payload['snapshot'].get('dataid')}). "
                            "Pipeline workers cannot keep up with ingestion rate."
                        ),
                    )
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


aggregator = HydroponicAggregator()
