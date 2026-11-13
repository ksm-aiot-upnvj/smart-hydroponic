"""M-1: application metrics are exposed and actually count failures.

Audit finding M-1 asked for Prometheus metrics covering the failure signals
that were previously visible only in container logs. These tests verify that

* ``/metrics`` serves the application exposition format, and
* the counters move when a real drop/rejection/command outcome happens
  (an unused metric that never increments would be worse than no metric at
  all).

Counter values are module-level singletons shared across the test session, so
every assertion is expressed as a delta.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main as main_module
from main import app
from schemas.user import UserOut, UserRole
from services.log_service import LogService
from utils.aggregator import HydroponicAggregator
from utils.deps import get_current_user, get_session
from utils.metrics import (
    ACTUATOR_COMMANDS,
    AGGREGATOR_DROPS,
    DATABASE_READY,
)

_METRIC_NAMES = (
    "hydroponic_snapshot_persistence_total",
    "hydroponic_sensor_payload_rejected_total",
    "hydroponic_aggregator_drops_total",
    "hydroponic_broadcast_failures_total",
    "hydroponic_actuator_commands_total",
    "hydroponic_automation_degraded",
    "hydroponic_database_ready",
)


def _value(metric, **labels) -> float:
    """Current value of a metric (series created on demand)."""
    child = metric.labels(**labels) if labels else metric
    return child._value.get()


def test_metrics_endpoint_exposes_application_metrics():
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    for name in _METRIC_NAMES:
        assert name in response.text, f"{name} missing from /metrics output"


@pytest.mark.asyncio
async def test_unknown_source_drop_is_counted():
    aggregator = HydroponicAggregator()
    before = _value(AGGREGATOR_DROPS, reason="unknown_source")

    with patch("utils.aggregator.best_effort_log", new_callable=AsyncMock):
        assert await aggregator.gather_data("not-a-source", {"x": 1}) is False

    assert _value(AGGREGATOR_DROPS, reason="unknown_source") == before + 1


@pytest.mark.asyncio
async def test_rate_limit_drop_is_counted():
    aggregator = HydroponicAggregator(min_interval=60.0, timeout=60.0)
    before = _value(AGGREGATOR_DROPS, reason="rate_limited")

    with patch("utils.aggregator.best_effort_log", new_callable=AsyncMock):
        assert await aggregator.gather_data("plant", {"moisture1": 1}) is True
        assert await aggregator.gather_data("plant", {"moisture1": 2}) is False

    assert _value(AGGREGATOR_DROPS, reason="rate_limited") == before + 1


class _StubSnapshot:
    def model_dump(self) -> dict:
        return {"dataid": None}


@pytest.mark.asyncio
async def test_queue_overflow_is_counted():
    aggregator = HydroponicAggregator(min_interval=1.0, queue_maxsize=1)
    # Pre-fill the queue so the next enqueue overflows it.
    aggregator.process_queue.put_nowait({"snapshot": {}, "ts": 0.0})
    before = _value(AGGREGATOR_DROPS, reason="queue_full")

    with patch("utils.aggregator.best_effort_log", new_callable=AsyncMock):
        await aggregator._enqueue_snapshot(_StubSnapshot())

    assert _value(AGGREGATOR_DROPS, reason="queue_full") == before + 1


class _FailingConnection:
    async def __aenter__(self):
        raise RuntimeError("database down")

    async def __aexit__(self, *_exc):
        return False


class _OkConnection:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def execute(self, *_args, **_kwargs):
        return None


class _FakeEngine:
    def __init__(self, connection):
        self._connection = connection

    def connect(self):
        return self._connection


@pytest.mark.asyncio
async def test_readiness_probe_sets_database_gauge(monkeypatch):
    monkeypatch.setattr(main_module, "engine", _FakeEngine(_FailingConnection()))
    response = await main_module.health_ready()
    assert response.status_code == 503
    assert _value(DATABASE_READY) == 0

    monkeypatch.setattr(main_module, "engine", _FakeEngine(_OkConnection()))
    assert await main_module.health_ready() == {
        "status": "ready",
        "checks": {"database": "ok"},
    }
    assert _value(DATABASE_READY) == 1


@pytest.fixture
def control_client(monkeypatch):
    async def override_get_session():
        yield object()

    async def override_get_current_user():
        return UserOut(
            userid=uuid4(),
            username="tester",
            email="tester@example.com",
            fullname="Test User",
            role=UserRole("admin"),
            created_at=datetime.now(timezone.utc),
        )

    async def _noop_write_log(self, **_kwargs):
        return None

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    monkeypatch.setattr(LogService, "write_log", _noop_write_log)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_undelivered_actuator_command_is_counted(control_client):
    before = _value(ACTUATOR_COMMANDS, transport="websocket", outcome="unavailable")

    response = control_client.post(
        "/hydroponics/control?transport=websocket",
        json={"pump_status": True, "light_status": False, "automation_status": False},
    )

    assert response.status_code == 200
    assert response.json()["delivery_status"] == "unavailable"
    assert (
        _value(ACTUATOR_COMMANDS, transport="websocket", outcome="unavailable")
        == before + 1
    )
