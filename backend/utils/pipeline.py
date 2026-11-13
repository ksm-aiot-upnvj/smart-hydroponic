import asyncio
import json
import logging
import time
from typing import Any

from utils.log_helpers import best_effort_log
from utils.metrics import AUTOMATION_DEGRADED, BROADCAST_FAILURES, SNAPSHOT_PERSISTENCE

logger = logging.getLogger(__name__)

_MAX_DB_RETRIES = 8
_DB_RETRY_BASE_DELAY = 0.1

_NUM_WORKERS = 2


class SnapshotPipeline:
    def __init__(self, aggregator, room: str = "hydroponics"):
        self.aggregator = aggregator
        self.room = room
        self._workers: list[asyncio.Task] = []
        self._stop_event: asyncio.Event = asyncio.Event()
        # Tracks whether automatic actuator decisions are currently suspended
        # because the nutrition profile could not be resolved (H-3). Only the
        # transitions are logged, so a sustained outage cannot flood the logs.
        self._automation_degraded: bool = False

    # ------------------------------------------------------------------
    # Lifespan
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._workers and not all(w.done() for w in self._workers):
            return
        self._stop_event.clear()
        for idx in range(_NUM_WORKERS):
            t = asyncio.create_task(self._worker_loop(worker_id=idx))
            self._workers.append(t)

    async def stop(self) -> None:
        if not self._workers:
            return
        self._stop_event.set()
        for w in self._workers:
            if not w.done():
                w.cancel()
        done, pending = await asyncio.wait(self._workers, timeout=10.0)
        for w in pending:
            w.cancel()
            try:
                await w
            except asyncio.CancelledError:
                pass
        self._workers = []

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    async def _worker_loop(self, worker_id: int) -> None:
        logger.info("[Pipeline] Worker %d started.", worker_id)
        while not self._stop_event.is_set():
            try:
                payload = await asyncio.wait_for(
                    self.aggregator.process_queue.get(), timeout=0.5
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                return

            try:
                await self._process_snapshot(payload)
            except Exception:
                logger.exception(
                    "[Pipeline] Worker %d: unhandled error processing snapshot.",
                    worker_id,
                )
                try:
                    await best_effort_log(
                        event_type="system",
                        severity="critical",
                        description=(
                            "Unhandled pipeline worker error while processing "
                            f"snapshot: {payload.get('snapshot', {}).get('dataid')}"
                        ),
                    )
                except Exception:
                    logger.exception(
                        "[Pipeline] Worker %d: error while writing critical log.",
                        worker_id,
                    )
            finally:
                try:
                    self.aggregator.process_queue.task_done()
                except ValueError:
                    pass
        logger.info("[Pipeline] Worker %d stopped.", worker_id)

    async def _process_snapshot(self, payload: dict[str, Any]) -> None:
        snapshot_dict = payload["snapshot"]
        queued_ts = payload.get("ts", time.monotonic())
        lag = time.monotonic() - queued_ts
        if lag > 5.0:
            logger.warning(
                "[Pipeline] Snapshot lagged %.2fs in queue before processing.",
                lag,
            )

        resolution = await self.aggregator.get_cached_profile()

        from utils.actuator_control import build_actuator_control_payload

        actuator_payload = build_actuator_control_payload(
            snapshot_dict,
            resolution.profile,
            profile_available=resolution.available,
        )

        await self._report_automation_degradation(actuator_payload, snapshot_dict)

        for k in ("pump_status", "light_status", "automation_status"):
            if k in actuator_payload:
                snapshot_dict[k] = actuator_payload[k]

        self.aggregator.update_actuator_state(
            {
                "pump_status": actuator_payload.get("pump_status", False),
                "light_status": actuator_payload.get("light_status", False),
                "automation_status": actuator_payload.get("automation_status", False),
            }
        )

        persisted = await self._persist_with_retry(snapshot_dict)

        if persisted:
            dataid = snapshot_dict.get("dataid")
            try:
                await best_effort_log(
                    event_type="system",
                    severity="info",
                    description="Snapshot recorded",
                    data_ref=str(dataid) if dataid is not None else None,
                )
            except Exception:
                logger.exception("[Pipeline] Failed to write 'snapshot recorded' log.")

            if actuator_payload.get("change_detected") and actuator_payload.get(
                "automation_status"
            ):
                change_summary = actuator_payload.get(
                    "change_summary", "actuator change"
                )
                try:
                    await best_effort_log(
                        event_type="automation",
                        severity="info",
                        description=f"Automation toggled: {change_summary}",
                        data_ref=str(dataid) if dataid is not None else None,
                    )
                except Exception:
                    logger.exception(
                        "[Pipeline] Failed to write automation change log."
                    )

        await self._broadcast_snapshot(
            snapshot_dict, actuator_payload, persisted=persisted
        )

        if persisted:
            logger.info(
                "[Pipeline] Snapshot %s persisted & broadcast. "
                "Actuators: pump=%s, light=%s, auto=%s",
                snapshot_dict.get("dataid"),
                actuator_payload.get("pump_status"),
                actuator_payload.get("light_status"),
                actuator_payload.get("automation_status"),
            )
        else:
            # Persistence already logged an ERROR/CRITICAL with the failure
            # context. This line must never claim the snapshot was persisted.
            logger.error(
                "[Pipeline] Snapshot %s NOT persisted (retries exhausted); "
                "broadcast as transient, unpersisted data. "
                "Actuators: pump=%s, light=%s, auto=%s",
                snapshot_dict.get("dataid"),
                actuator_payload.get("pump_status"),
                actuator_payload.get("light_status"),
                actuator_payload.get("automation_status"),
            )

    async def _report_automation_degradation(
        self, actuator_payload: dict[str, Any], snapshot_dict: dict[str, Any]
    ) -> None:
        """Log automation being suspended or resumed (audit finding H-3).

        Only state transitions are logged: while the nutrition profile cannot be
        resolved every snapshot is degraded, and logging each one would flood
        both stdout and the logs table. The skipped decision is never silently
        swallowed — the transition itself is reported with full context.
        """
        degraded = bool(actuator_payload.get("automation_degraded"))
        if degraded == self._automation_degraded:
            return

        self._automation_degraded = degraded
        AUTOMATION_DEGRADED.set(1 if degraded else 0)
        dataid = snapshot_dict.get("dataid")

        if degraded:
            reason = (
                actuator_payload.get("automation_skip_reason")
                or "nutrition profile unavailable"
            )
            logger.error(
                "[Pipeline] Automation degraded (dataid=%s): %s. Automatic "
                "actuator decisions are suspended; actuator state left unchanged.",
                dataid,
                reason,
            )
            try:
                await best_effort_log(
                    event_type="automation",
                    severity="error",
                    description=(
                        f"Automation degraded: {reason}. Automatic actuator "
                        "decisions are suspended; actuator state left unchanged."
                    ),
                    data_ref=str(dataid) if dataid is not None else None,
                )
            except Exception:
                logger.exception("[Pipeline] Failed to write automation-degraded log.")
        else:
            logger.info(
                "[Pipeline] Automation recovered (dataid=%s); automatic actuator "
                "decisions resumed.",
                dataid,
            )
            try:
                await best_effort_log(
                    event_type="automation",
                    severity="info",
                    description=(
                        "Automation recovered: nutrition profile resolution "
                        "succeeded; automatic actuator decisions resumed."
                    ),
                    data_ref=str(dataid) if dataid is not None else None,
                )
            except Exception:
                logger.exception("[Pipeline] Failed to write automation-recovered log.")

    async def _persist_with_retry(self, snapshot_dict: dict[str, Any]) -> bool:
        from schemas import HydroponicIn
        from utils.deps import get_db_session
        from services.hydroponic_service import HydroponicService

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_DB_RETRIES + 1):
            try:
                async with get_db_session() as session:
                    service = HydroponicService(session)
                    validated = HydroponicIn.model_validate(snapshot_dict)
                    await service.add_data(validated)
                SNAPSHOT_PERSISTENCE.labels(result="success").inc()
                return True
            except Exception as exc:
                last_exc = exc
                delay = _DB_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                if attempt == _MAX_DB_RETRIES:
                    logger.error(
                        "[Pipeline] DB persist failed after %d attempts. "
                        "Snapshot %s WILL BE LOST.",
                        _MAX_DB_RETRIES,
                        snapshot_dict.get("dataid"),
                        exc_info=True,
                    )
                    try:
                        await best_effort_log(
                            event_type="system",
                            severity="critical",
                            description=(
                                f"DB persist failed after {_MAX_DB_RETRIES} attempts. "
                                f"Snapshot lost: dataid={snapshot_dict.get('dataid')}. "
                                f"Last error: {exc!r}"
                            ),
                            data_ref=str(snapshot_dict.get("dataid"))
                            if snapshot_dict.get("dataid") is not None
                            else None,
                        )
                    except Exception:
                        logger.exception(
                            "[Pipeline] Failed to write DB-failure critical log."
                        )
                    break
                logger.warning(
                    "[Pipeline] DB persist attempt %d/%d failed: %s. "
                    "Retrying in %.2fs.",
                    attempt,
                    _MAX_DB_RETRIES,
                    exc,
                    delay,
                )
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass

        if last_exc is not None:
            from schemas import HydroponicIn

            SNAPSHOT_PERSISTENCE.labels(result="failure").inc()
            try:
                HydroponicIn.model_validate(snapshot_dict)
            except Exception:
                logger.exception("[Pipeline] Snapshot rejected due to invalid schema.")
        return False

    async def _broadcast_snapshot(
        self,
        snapshot_dict: dict[str, Any],
        actuator_payload: dict[str, Any],
        persisted: bool = True,
    ) -> None:
        from utils.manager import manager

        # `persisted` is part of the real-time message contract so web clients
        # can tell durable readings apart from transient, unpersisted data.
        web_message = {**snapshot_dict, "persisted": persisted}

        actuator_broadcast = {
            k: v
            for k, v in actuator_payload.items()
            if k
            in (
                "pump_status",
                "light_status",
                "automation_status",
                "moisture_avg",
                "temperature_avg",
                # Exposed so consumers can tell a suspended automation
                # (nutrition profile unavailable) from a normal decision.
                "automation_degraded",
            )
        }

        targets = [
            ("web-client", web_message),
            ("actuator", actuator_broadcast),
        ]
        tasks = [
            asyncio.create_task(
                manager.send_to_room(room=self.room, role=role, message=message)
            )
            for role, message in targets
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for (role, _message), result in zip(targets, results):
            if isinstance(result, BaseException):
                # `send_to_room` itself raised before returning a result; the
                # manager's own per-client counters never ran for this call.
                BROADCAST_FAILURES.labels(role=role, kind="error").inc()
                logger.error(
                    "[Pipeline] WS broadcast to role='%s' failed.",
                    role,
                    exc_info=result,
                )
                continue
            if not result.has_clients:
                logger.debug(
                    "[Pipeline] No '%s' clients connected; snapshot not delivered.",
                    role,
                )
            elif result.dropped:
                logger.warning(
                    "[Pipeline] Broadcast to role='%s' dropped %d/%d client(s) "
                    "(send queue full).",
                    role,
                    result.dropped,
                    result.eligible,
                )

        try:
            from routes.coap_handler import HydroponicCoAPResource

            actuator_res = HydroponicCoAPResource._instances.get("actuator")
            if actuator_res:
                actuator_res.latest_state = json.dumps(actuator_broadcast).encode(
                    "utf-8"
                )
                actuator_res.updated_state()
        except Exception:
            logger.exception("[Pipeline] Error updating CoAP actuator Observe state.")
