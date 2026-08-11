from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from schemas.user import UserOut
from services.hydroponic_service import HydroponicService
from services.user_service import UserService
from utils.deps import get_current_user, get_optional_current_user, get_session
from schemas.hydroponic import HydroponicOut, MetaData, ResponseList
from uuid import uuid7


class _DummySession:
    async def execute(self, *_args, **_kwargs):
        return None


@pytest.fixture
def client():
    async def override_get_session():
        yield _DummySession()

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _set_current_user_override(role: str = "admin"):
    async def override_get_current_user():
        return UserOut(
            userid=uuid4(),
            username="tester",
            email="tester@example.com",
            fullname="Test User",
            role=role,
            created_at=datetime.now(timezone.utc),
        )

    app.dependency_overrides[get_current_user] = override_get_current_user


def test_login_requires_username_or_email(client: TestClient):
    response = client.post(
        "/users/login",
        json={
            "password": "supersecret123",
        },
    )

    assert response.status_code == 422


def test_login_invalid_credentials(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    async def fake_authenticate_user(_self, _credentials):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    monkeypatch.setattr(UserService, "authenticate_user", fake_authenticate_user)

    response = client.post(
        "/users/login",
        json={
            "username": "newuser",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_register_duplicate_username(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    _set_current_user_override(role="superadmin")

    async def fake_get_user_by_username(_self, _username):
        return {
            "userid": uuid4(),
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "hashed",
            "role": "user",
            "created_at": datetime.now(timezone.utc),
            "is_superuser": False,
        }

    monkeypatch.setattr(UserService, "get_user_by_username", fake_get_user_by_username)

    response = client.post(
        "/users/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "supersecret123",
            "role": "user",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"


def test_register_requires_auth(client: TestClient):
    response = client.post(
        "/users/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "supersecret123",
            "role": "user",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_users_endpoint_requires_auth(client: TestClient):
    response = client.get("/users")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_delete_user_forbidden_for_user_role(client: TestClient):
    _set_current_user_override(role="user")

    response = client.delete(f"/users/{uuid4()}")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_hydroponic_latest_no_data(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _set_current_user_override(role="admin")

    async def fake_get_latest_data(_self):
        return None

    monkeypatch.setattr(HydroponicService, "get_latest_data", fake_get_latest_data)

    response = client.get("/hydroponics/data/latest")

    assert response.status_code == 204


def test_hydroponic_latest_with_actuator_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    _set_current_user_override(role="admin")

    dummy_out = HydroponicOut(
        dataid=uuid7(),
        flowrate=1.5,
        distance_cm=10.0,
        total_litres=5.0,
        ph=6.5,
        tds=800.0,
        pump_status=True,
        light_status=False,
        automation_status=True,
    )

    async def fake_get_latest_data(_self):
        return dummy_out

    monkeypatch.setattr(HydroponicService, "get_latest_data", fake_get_latest_data)

    response = client.get("/hydroponics/data/latest")

    assert response.status_code == 200
    data = response.json()
    assert data["pump_status"] is True
    assert data["light_status"] is False
    assert data["automation_status"] is True


def test_hydroponic_specific_forbidden_for_user_role(client: TestClient):
    _set_current_user_override(role="user")

    response = client.get("/hydroponics/data/ph")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_hydroponic_specific_invalid_parameter(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    _set_current_user_override(role="admin")

    async def fake_get_specific_data(
        _self,
        _parameter,
        _page=1,
        _limit=25,
        _start_date=None,
        _end_date=None,
    ):
        raise ValueError("Invalid parameter: invalid_field")

    monkeypatch.setattr(HydroponicService, "get_specific_data", fake_get_specific_data)

    response = client.get("/hydroponics/data/invalid_field")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid parameter: invalid_field"


def test_public_hydroponic_data_rejects_range_over_7_days_for_anonymous(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    start_date = "2026-05-01T00:00:00Z"
    end_date = "2026-05-10T00:00:00Z"

    async def override_optional_current_user():
        return None

    app.dependency_overrides[get_optional_current_user] = override_optional_current_user

    response = client.get(
        "/hydroponics/public",
        params={"start_date": start_date, "end_date": end_date},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Date range cannot exceed 7 days for public endpoint"
    )


def test_public_hydroponic_data_allows_range_over_7_days_for_admin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    start_date = "2026-05-01T00:00:00Z"
    end_date = "2026-05-10T00:00:00Z"

    async def override_optional_current_user():
        return UserOut(
            userid=uuid4(),
            username="admin-user",
            email="admin@example.com",
            fullname="Admin User",
            role="admin",
            created_at=datetime.now(timezone.utc),
        )

    async def fake_get_all_data(
        _self, _page=1, _limit=25, _start_date=None, _end_date=None
    ):
        sample = HydroponicOut(
            dataid=uuid7(),
            moisture1=1,
            moisture2=2,
            moisture3=3,
            moisture4=4,
            moisture5=5,
            moisture6=6,
            flowrate=1.0,
            total_litres=1.0,
            distance_cm=1.0,
            ph=6.0,
            tds=500.0,
            temperature_atas=25.0,
            temperature_bawah=24.0,
            humidity_atas=50.0,
            humidity_bawah=49.0,
            pump_status=True,
            light_status=True,
            automation_status=False,
        )

        return ResponseList(
            meta=MetaData(total_rows=1, limit=_limit, offset=0),
            data=[sample],
        )

    app.dependency_overrides[get_optional_current_user] = override_optional_current_user
    monkeypatch.setattr(HydroponicService, "get_all_data", fake_get_all_data)

    response = client.get(
        "/hydroponics/public",
        params={"start_date": start_date, "end_date": end_date},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total_rows"] == 1
    assert len(body["data"]) == 1
