"""Snapshot pipeline persistence semantics and broadcast observability.

Covers audit findings:

* C-3 — the pipeline must never claim a snapshot was persisted when
  ``_persist_with_retry`` returned ``False``.
* H-2 — exceptions raised while broadcasting must be surfaced in the logs
  instead of being discarded by ``return_exceptions=True``.

No database or network access is required.
"""

from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.aggregator import ProfileResolution
from utils.manager import BroadcastResult, RoomConnectionManager, _ClientState
from utils.pipeline import SnapshotPipeline


class _StubAggregator:
    def __init__(self, profile=None, profile_available: bool = True):
        self._profile = profile
        self._profile_available = profile_available
        self.actuator_states: list[dict] = []

    async def get_cached_profile(self):
        return ProfileResolution(
            profile=self._profile, available=self._profile_available
        )

    def update_actuator_state(self, state: dict) -> None:
        self.actuator_states.append(state)


class _FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


def _snapshot(**overrides) -> dict:
    base = {
        "dataid": "019b76da-a800-7000-8000-000000000000",
        "moisture1": 10,
        "moisture2": 11,
        "moisture3": 12,
        "moisture4": 13,
        "moisture5": 14,
        "moisture6": 15,
        "flowrate": 1.2,
        "total_litres": 20.5,
        "distance_cm": 30.0,
        "ph": 6.2,
        "tds": 500.0,
        "temperature_atas": 25.0,
        "temperature_bawah": 24.0,
        "humidity_atas": 60.0,
        "humidity_bawah": 61.0,
        "pump_status": False,
        "light_status": False,
        "automation_status": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# C-3: persistence status must be truthful
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persistence_failure_is_never_logged_as_success(caplog):
    pipeline = SnapshotPipeline(aggregator=_StubAggregator(), room="hydroponics")
    captured: dict[str, dict] = {}

    async def fake_send_to_room(room, role, message):
        captured[role] = message
        return BroadcastResult(eligible=1, queued=1, dropped=0)

    with (
        patch.object(
            SnapshotPipeline, "_persist_with_retry", AsyncMock(return_value=False)
        ),
        patch("utils.manager.manager.send_to_room", side_effect=fake_send_to_room),
        patch("utils.pipeline.best_effort_log", AsyncMock()),
        caplog.at_level("INFO"),
    ):
        await pipeline._process_snapshot({"snapshot": _snapshot(), "ts": 0.0})

    assert "persisted & broadcast" not in caplog.text
    assert "NOT persisted" in caplog.text
    # Real-time delivery is preserved, but the message is flagged as transient.
    assert captured["web-client"]["persisted"] is False


@pytest.mark.asyncio
async def test_persistence_success_logs_and_flags_persisted(caplog):
    pipeline = SnapshotPipeline(aggregator=_StubAggregator(), room="hydroponics")
    captured: dict[str, dict] = {}

    async def fake_send_to_room(room, role, message):
        captured[role] = message
        return BroadcastResult(eligible=1, queued=1, dropped=0)

    with (
        patch.object(
            SnapshotPipeline, "_persist_with_retry", AsyncMock(return_value=True)
        ),
        patch("utils.manager.manager.send_to_room", side_effect=fake_send_to_room),
        patch("utils.pipeline.best_effort_log", AsyncMock()),
        caplog.at_level("INFO"),
    ):
        await pipeline._process_snapshot({"snapshot": _snapshot(), "ts": 0.0})

    assert "persisted & broadcast" in caplog.text
    assert "NOT persisted" not in caplog.text
    assert captured["web-client"]["persisted"] is True


# ---------------------------------------------------------------------------
# H-2: broadcast failures must be observable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_exception_is_logged(caplog):
    pipeline = SnapshotPipeline(aggregator=_StubAggregator(), room="hydroponics")

    async def boom(room, role, message):
        if role == "web-client":
            raise RuntimeError("socket exploded")
        return BroadcastResult(eligible=0, queued=0, dropped=0)

    with (
        patch("utils.manager.manager.send_to_room", side_effect=boom),
        caplog.at_level("ERROR"),
    ):
        await pipeline._broadcast_snapshot(
            _snapshot(), {"pump_status": False}, persisted=True
        )

    assert "broadcast to role='web-client' failed" in caplog.text


@pytest.mark.asyncio
async def test_broadcast_queue_full_is_logged_as_warning(caplog):
    pipeline = SnapshotPipeline(aggregator=_StubAggregator(), room="hydroponics")

    async def full_queue(room, role, message):
        return BroadcastResult(eligible=2, queued=1, dropped=1)

    with (
        patch("utils.manager.manager.send_to_room", side_effect=full_queue),
        caplog.at_level("WARNING"),
    ):
        await pipeline._broadcast_snapshot(
            _snapshot(), {"pump_status": False}, persisted=True
        )

    assert "dropped 1/2 client(s)" in caplog.text


# ---------------------------------------------------------------------------
# RoomConnectionManager.send_to_room delivery reporting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_to_room_reports_no_clients():
    manager = RoomConnectionManager()

    result = await manager.send_to_room("room", "actuator", {"type": "command"})

    assert result == BroadcastResult(eligible=0, queued=0, dropped=0)
    assert result.has_clients is False


@pytest.mark.asyncio
async def test_send_to_room_reports_queued_clients():
    manager = RoomConnectionManager()
    await manager.connect("room", "actuator", "c1", _FakeWebSocket())

    try:
        result = await manager.send_to_room("room", "actuator", {"type": "command"})

        assert result.has_clients is True
        assert result.queued == 1
        assert result.dropped == 0
        assert result.fully_delivered is True
    finally:
        await manager.disconnect("room", "actuator", "c1")


@pytest.mark.asyncio
async def test_send_to_room_reports_dropped_client_when_queue_full():
    manager = RoomConnectionManager()
    await manager.connect("room", "actuator", "c1", _FakeWebSocket())

    try:
        with patch.object(_ClientState, "enqueue", return_value=False):
            result = await manager.send_to_room("room", "actuator", {"type": "command"})

        assert result.eligible == 1
        assert result.queued == 0
        assert result.dropped == 1
        assert result.fully_delivered is False
        # A client that cannot accept messages is pruned.
        assert "c1" not in manager.rooms.get("room", {}).get("actuator", {})
    finally:
        await manager.disconnect("room", "actuator", "c1")


@pytest.mark.asyncio
async def test_send_to_room_logs_enqueue_exception(caplog):
    manager = RoomConnectionManager()
    await manager.connect("room", "actuator", "c1", _FakeWebSocket())

    try:
        with (
            patch.object(_ClientState, "enqueue", side_effect=RuntimeError("boom")),
            caplog.at_level("ERROR"),
        ):
            result = await manager.send_to_room("room", "actuator", {"type": "command"})

        assert result.dropped == 1
        assert "Enqueue failed for client 'c1'" in caplog.text
    finally:
        await manager.disconnect("room", "actuator", "c1")
