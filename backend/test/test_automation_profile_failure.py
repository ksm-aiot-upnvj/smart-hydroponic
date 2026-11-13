"""H-3: automation must not act on an unavailable nutrition profile.

Covers audit finding H-3. Two distinct states must be told apart:

* a legitimate absence of an active nutrition profile — the explicitly
  configured fallback thresholds are valid and are used as before;
* a *failed* profile lookup (for example the database is unreachable) — the
  automatic actuator decision must be skipped, automation reported as
  degraded, and no generic threshold substituted.

A transient failure must neither poison the cache nor prevent recovery.

No database or network access is required.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schemas.nutrition import PlantNutritionProfileOut
from utils.actuator_control import build_actuator_control_payload
from utils.aggregator import (
    HydroponicAggregator,
    ProfileResolution,
    _PROFILE_CACHE_TTL,
)
from utils.manager import BroadcastResult
from utils.pipeline import SnapshotPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(
    *,
    moisture_min: float = 40.0,
    moisture_max: float = 70.0,
    temperature_min: float = 18.0,
    temperature_max: float = 28.0,
) -> PlantNutritionProfileOut:
    now = datetime.now(timezone.utc)
    return PlantNutritionProfileOut(
        nutrition_id=uuid4(),
        plant_name="Selada",
        moisture_min=moisture_min,
        moisture_max=moisture_max,
        ph_min=5.5,
        ph_max=6.5,
        tds_min=400.0,
        tds_max=800.0,
        temperature_min=temperature_min,
        temperature_max=temperature_max,
        humidity_min=50.0,
        humidity_max=80.0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def _snapshot(**overrides) -> dict:
    base = {
        "dataid": "019b76da-a800-7000-8000-000000000000",
        "moisture1": 20,
        "moisture2": 20,
        "moisture3": 20,
        "moisture4": 20,
        "moisture5": 20,
        "moisture6": 20,
        "temperature_atas": 20.0,
        "temperature_bawah": 20.0,
        "pump_status": False,
        "light_status": False,
        "automation_status": True,
    }
    base.update(overrides)
    return base


@asynccontextmanager
async def _fake_db_session():
    yield object()


def _install_fake_service(monkeypatch, *, profile=None, error=None, calls=None):
    class _FakeNutritionService:
        def __init__(self, session):
            self.session = session

        async def get_active_profile(self):
            if calls is not None:
                calls.append(1)
            if error is not None:
                raise error
            return profile

    monkeypatch.setattr(
        "services.nutrition_service.NutritionService", _FakeNutritionService
    )
    monkeypatch.setattr("utils.deps.get_db_session", lambda: _fake_db_session())


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


# ---------------------------------------------------------------------------
# build_actuator_control_payload
# ---------------------------------------------------------------------------


def test_valid_profile_uses_profile_bounds():
    payload = build_actuator_control_payload(
        _snapshot(), _profile(moisture_min=40.0, moisture_max=70.0)
    )

    assert payload["pump_status"] is True  # 20 %RH < moisture_min
    assert payload["automation_degraded"] is False
    assert payload["automation_skip_reason"] is None


def test_profile_bounds_take_precedence_over_generic_thresholds():
    # 20 %RH is below the fallback threshold (60) but inside the profile band,
    # so the pump must NOT be switched on.
    payload = build_actuator_control_payload(
        _snapshot(), _profile(moisture_min=10.0, moisture_max=30.0)
    )

    assert payload["pump_status"] is False
    assert payload["change_detected"] is False


def test_no_active_profile_uses_configured_thresholds():
    # Legitimate absence: available=True, profile=None -> explicit fallback.
    payload = build_actuator_control_payload(_snapshot(), None, profile_available=True)

    assert payload["pump_status"] is True  # 20 < settings.HYDROPONIC_MOISTURE_THRESHOLD
    assert payload["automation_degraded"] is False


def test_unavailable_profile_skips_decision_and_does_not_substitute_thresholds():
    # moisture below the fallback threshold: without the guard the pump would
    # be switched on. With the profile unavailable the decision must be skipped.
    payload = build_actuator_control_payload(
        _snapshot(pump_status=False), None, profile_available=False
    )

    assert payload["pump_status"] is False
    assert payload["light_status"] is False
    assert payload["change_detected"] is False
    assert payload["automation_degraded"] is True
    assert payload["automation_skip_reason"]


def test_unavailable_profile_never_forces_actuator_off():
    # High moisture would normally switch the pump off; that decision must also
    # be skipped, leaving the currently-on pump untouched.
    payload = build_actuator_control_payload(
        _snapshot(
            moisture1=95,
            moisture2=95,
            moisture3=95,
            moisture4=95,
            moisture5=95,
            moisture6=95,
            pump_status=True,
        ),
        None,
        profile_available=False,
    )

    assert payload["pump_status"] is True
    assert payload["change_detected"] is False
    assert payload["automation_degraded"] is True


def test_unavailable_profile_is_irrelevant_when_automation_is_off():
    payload = build_actuator_control_payload(
        _snapshot(automation_status=False), None, profile_available=False
    )

    assert payload["automation_degraded"] is False
    assert payload["automation_skip_reason"] is None


# ---------------------------------------------------------------------------
# HydroponicAggregator.get_cached_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_legitimate_absence_is_available_and_cached(monkeypatch):
    calls: list[int] = []
    _install_fake_service(monkeypatch, profile=None, calls=calls)
    aggregator = HydroponicAggregator()

    first = await aggregator.get_cached_profile()
    second = await aggregator.get_cached_profile()

    assert first.available is True and first.profile is None
    assert second.available is True and second.profile is None
    assert len(calls) == 1  # a legitimate absence is a cacheable resolution


@pytest.mark.asyncio
async def test_fetch_failure_reports_unavailable_without_caching_absence(monkeypatch):
    _install_fake_service(monkeypatch, error=RuntimeError("db down"))
    aggregator = HydroponicAggregator()

    resolved = await aggregator.get_cached_profile()

    assert resolved.available is False
    assert resolved.profile is None
    # A failure must never be recorded as a resolution: doing so previously
    # made the outage indistinguishable from "no profile configured".
    assert aggregator._profile_cached_at == 0.0


@pytest.mark.asyncio
async def test_repeated_failures_within_window_are_not_retried(monkeypatch):
    calls: list[int] = []
    _install_fake_service(monkeypatch, error=RuntimeError("db down"), calls=calls)
    aggregator = HydroponicAggregator()

    first = await aggregator.get_cached_profile()
    second = await aggregator.get_cached_profile()

    assert first.available is False and second.available is False
    assert len(calls) == 1  # short negative cache avoids hammering a down DB


@pytest.mark.asyncio
async def test_recovery_after_database_availability_returns(monkeypatch):
    _install_fake_service(monkeypatch, error=RuntimeError("db down"))
    aggregator = HydroponicAggregator()

    failed = await aggregator.get_cached_profile()
    assert failed.available is False

    # Simulate the retry window elapsing, then the database coming back.
    aggregator._profile_failure_at = 0.0
    recovered_profile = _profile()
    _install_fake_service(monkeypatch, profile=recovered_profile)

    recovered = await aggregator.get_cached_profile()

    assert recovered.available is True
    assert recovered.profile is recovered_profile


@pytest.mark.asyncio
async def test_expired_cache_is_refreshed(monkeypatch):
    first_profile = _profile(moisture_min=10.0)
    _install_fake_service(monkeypatch, profile=first_profile)
    aggregator = HydroponicAggregator()

    cached = await aggregator.get_cached_profile()
    assert cached.profile is first_profile

    # Simulate the cache TTL elapsing.
    aggregator._profile_cached_at -= _PROFILE_CACHE_TTL + 1.0
    refreshed_profile = _profile(moisture_min=55.0)
    _install_fake_service(monkeypatch, profile=refreshed_profile)

    refreshed = await aggregator.get_cached_profile()

    assert refreshed.available is True
    assert refreshed.profile is refreshed_profile


@pytest.mark.asyncio
async def test_expired_cache_with_failing_refresh_is_unavailable_not_stale(monkeypatch):
    stale_profile = _profile()
    _install_fake_service(monkeypatch, profile=stale_profile)
    aggregator = HydroponicAggregator()

    assert (await aggregator.get_cached_profile()).profile is stale_profile

    # Expire the cache and make the next refresh fail.
    aggregator._profile_cached_at -= _PROFILE_CACHE_TTL + 1.0
    _install_fake_service(monkeypatch, error=RuntimeError("db down"))

    resolved = await aggregator.get_cached_profile()

    assert resolved.available is False
    # The stale profile must not be served as if it were a fresh resolution.
    assert resolved.profile is None


# ---------------------------------------------------------------------------
# SnapshotPipeline reporting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_reports_and_broadcasts_automation_degraded(caplog):
    pipeline = SnapshotPipeline(
        aggregator=_StubAggregator(profile=None, profile_available=False),
        room="hydroponics",
    )
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
        caplog.at_level("ERROR"),
    ):
        await pipeline._process_snapshot({"snapshot": _snapshot(), "ts": 0.0})

    assert "Automation degraded" in caplog.text
    assert captured["actuator"]["automation_degraded"] is True
    assert captured["actuator"]["pump_status"] is False


@pytest.mark.asyncio
async def test_pipeline_logs_recovery_transition_once(caplog):
    stub = _StubAggregator(profile=None, profile_available=False)
    pipeline = SnapshotPipeline(aggregator=stub, room="hydroponics")

    async def fake_send_to_room(room, role, message):
        return BroadcastResult(eligible=0, queued=0, dropped=0)

    with (
        patch.object(
            SnapshotPipeline, "_persist_with_retry", AsyncMock(return_value=True)
        ),
        patch("utils.manager.manager.send_to_room", side_effect=fake_send_to_room),
        patch("utils.pipeline.best_effort_log", AsyncMock()),
        caplog.at_level("INFO"),
    ):
        await pipeline._process_snapshot({"snapshot": _snapshot(), "ts": 0.0})
        assert "Automation degraded" in caplog.text

        stub._profile_available = True
        caplog.clear()
        # Two healthy snapshots; the recovery transition must be logged once.
        await pipeline._process_snapshot({"snapshot": _snapshot(), "ts": 0.0})
        await pipeline._process_snapshot({"snapshot": _snapshot(), "ts": 0.0})

    assert caplog.text.count("Automation recovered") == 1
