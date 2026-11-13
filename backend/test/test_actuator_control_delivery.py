"""C-2 / H-4: actuator control must report delivery truthfully.

A WebSocket broadcast only queues the payload for a connected client, and a
CoAP Observe notification only pushes the payload to the transport. Neither is
proof that the physical actuator executed the command, so the control endpoint
must never answer ``confirmed=True`` and must state what was actually
established via ``delivery_status``.

H-4 resolved the unused outbound CoAP client (``send_actuator_command_coap``)
by removing it: the deployed protocol is Observe-only, so the tests below also
assert that the dead outbound client and its orphaned settings are gone.
"""

from datetime import datetime, timezone
from pathlib import Path
import importlib
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from schemas.hydroponic import HydroponicControlResult
from schemas.user import UserOut, UserRole
from services.log_service import LogService
from utils.deps import get_current_user, get_session
from utils.manager import BroadcastResult, manager


class _DummyResult:
    def scalar(self):
        return 1


class _DummySession:
    async def execute(self, *_args, **_kwargs):
        return _DummyResult()


@pytest.fixture
def client(monkeypatch):
    async def override_get_session():
        yield _DummySession()

    async def override_get_current_user():
        return UserOut(
            userid=uuid4(),
            username="tester",
            email="tester@example.com",
            fullname="Test User",
            role=UserRole("admin"),
            created_at=datetime.now(timezone.utc),
        )

    async def _noop_write_log(self, **kwargs):
        return None

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    monkeypatch.setattr(LogService, "write_log", _noop_write_log)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _post(client: TestClient, transport: str, **overrides):
    body = {
        "pump_status": True,
        "light_status": False,
        "automation_status": False,
    }
    body.update(overrides)
    return client.post(f"/hydroponics/control?transport={transport}", json=body)


class _FakeCoAPActuator:
    """Minimal stand-in for ``HydroponicCoAPResource`` on role 'actuator'."""

    def __init__(self, observers: int):
        self._observations = {f"obs-{i}": object() for i in range(observers)}
        self.latest_state = b"{}"
        self.notified = False

    def updated_state(self):
        self.notified = True


def _patch_coap_instances(monkeypatch, instances):
    from routes.coap_handler import HydroponicCoAPResource

    monkeypatch.setattr(HydroponicCoAPResource, "_instances", instances)


# ---------------------------------------------------------------------------
# WebSocket transport
# ---------------------------------------------------------------------------


def test_websocket_no_connected_actuator_is_unavailable(client, monkeypatch):
    async def fake_send_to_room(room, role, message):
        return BroadcastResult(eligible=0, queued=0, dropped=0)

    monkeypatch.setattr(manager, "send_to_room", fake_send_to_room)

    response = _post(client, "websocket")

    assert response.status_code == 200
    data = response.json()
    assert data["delivery_status"] == "unavailable"
    assert data["confirmed"] is False
    assert data["command_id"]


def test_websocket_queued_is_dispatched_not_confirmed(client, monkeypatch):
    async def fake_send_to_room(room, role, message):
        return BroadcastResult(eligible=1, queued=1, dropped=0)

    monkeypatch.setattr(manager, "send_to_room", fake_send_to_room)

    response = _post(client, "websocket")

    data = response.json()
    assert data["delivery_status"] == "dispatched"
    assert data["confirmed"] is False


def test_websocket_all_dropped_is_failed(client, monkeypatch):
    async def fake_send_to_room(room, role, message):
        return BroadcastResult(eligible=2, queued=0, dropped=2)

    monkeypatch.setattr(manager, "send_to_room", fake_send_to_room)

    response = _post(client, "websocket")

    data = response.json()
    assert data["delivery_status"] == "failed"
    assert data["confirmed"] is False


def test_websocket_partial_delivery_is_dispatched(client, monkeypatch):
    async def fake_send_to_room(room, role, message):
        return BroadcastResult(eligible=2, queued=1, dropped=1)

    monkeypatch.setattr(manager, "send_to_room", fake_send_to_room)

    response = _post(client, "websocket")

    data = response.json()
    assert data["delivery_status"] == "dispatched"
    assert data["confirmed"] is False


# ---------------------------------------------------------------------------
# CoAP transport
# ---------------------------------------------------------------------------


def test_coap_without_registered_resource_is_unavailable(client, monkeypatch):
    _patch_coap_instances(monkeypatch, {})

    response = _post(client, "coap")

    data = response.json()
    assert data["delivery_status"] == "unavailable"
    assert data["confirmed"] is False


def test_coap_without_observer_is_unavailable(client, monkeypatch):
    fake = _FakeCoAPActuator(observers=0)
    _patch_coap_instances(monkeypatch, {"actuator": fake})

    response = _post(client, "coap")

    data = response.json()
    assert fake.notified is True
    assert data["delivery_status"] == "unavailable"
    assert data["confirmed"] is False


def test_coap_observer_notification_is_dispatched_not_confirmed(client, monkeypatch):
    fake = _FakeCoAPActuator(observers=1)
    _patch_coap_instances(monkeypatch, {"actuator": fake})

    response = _post(client, "coap")

    data = response.json()
    assert fake.notified is True
    assert data["delivery_status"] == "dispatched"
    # An Observe notification is not an acknowledgement of execution.
    assert data["confirmed"] is False


def test_invalid_transport_is_rejected(client):
    response = _post(client, "carrier-pigeon")

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Schema defaults stay conservative
# ---------------------------------------------------------------------------


def test_control_result_defaults_never_imply_confirmation():
    result = HydroponicControlResult(command_id="c-1")

    assert result.confirmed is False
    assert result.delivery_status == "dispatched"


# ---------------------------------------------------------------------------
# H-4: unused outbound CoAP client removed, Observe-only protocol retained
# ---------------------------------------------------------------------------


def test_unused_outbound_coap_client_module_is_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("utils.coap_actuator_client")


def test_orphaned_coap_actuator_settings_are_removed():
    from config.config import Settings

    for field in (
        "COAP_ACTUATOR_HOST",
        "COAP_ACTUATOR_PORT",
        "COAP_ACTUATOR_CONTROL_PATH",
        "COAP_ACTUATOR_TIMEOUT_SECONDS",
    ):
        assert field not in Settings.model_fields
