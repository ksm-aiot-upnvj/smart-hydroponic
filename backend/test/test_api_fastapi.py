from datetime import datetime, timezone
from uuid import uuid4, uuid7
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from schemas.hydroponic import HydroponicOut, MetaData, ResponseList
from schemas.user import UserOut, UserRole
from services.hydroponic_service import HydroponicService
from services.user_service import UserService
from utils.deps import get_current_user, get_session
from fastapi import HTTPException


class _DummyResult:
    def scalar(self):
        return 1


class _DummySession:
    async def execute(self, *_args, **_kwargs):
        return _DummyResult()


@pytest.fixture
def client():
    async def override_get_session():
        yield _DummySession()

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _set_current_user_override(role: str = "admin"):
    async def override_get_current_user():
        return UserOut(
            userid=uuid4(),
            username="tester",
            email="tester@example.com",
            fullname="Test User",
            role=UserRole(role),
            created_at=datetime.now(timezone.utc),
        )

    app.dependency_overrides[get_current_user] = override_get_current_user


def test_health(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_db_test(client: TestClient):
    response = client.get("/db-test")

    assert response.status_code == 200
    assert response.json() == {"result": 1}


def test_register_user_success(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _set_current_user_override(role="superadmin")

    async def fake_get_user_by_username(_self, _username):
        return None

    async def fake_add_user(_self, payload):
        return {
            "userid": uuid4(),
            "username": payload["username"],
            "email": payload["email"],
            "fullname": payload.get("fullname"),
            "phone_number": payload.get("phone_number"),
            "role": "user",
            "created_at": datetime.now(timezone.utc),
            "password": payload["password"],
            "is_superuser": False,
        }

    monkeypatch.setattr(UserService, "get_user_by_username", fake_get_user_by_username)
    monkeypatch.setattr(UserService, "add_user", fake_add_user)

    response = client.post(
        "/users/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "supersecret123",
            "role": "user",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "newuser"
    assert body["email"] == "newuser@example.com"
    assert "password" not in body


def test_login_user_success(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    user_id = uuid4()

    async def fake_authenticate_user(_self, _credentials):
        return UserOut(
            userid=user_id,
            username="newuser",
            email="newuser@example.com",
            fullname="New User",
            role=UserRole.USER,
            created_at=datetime.now(timezone.utc),
        )

    def fake_create_access_token(_self, data):
        return "token-123"

    async def fake_get_user_by_id(_self, _user_id):
        return {
            "userid": user_id,
            "token_version": 0,
        }

    monkeypatch.setattr(UserService, "authenticate_user", fake_authenticate_user)
    monkeypatch.setattr(UserService, "create_access_token", fake_create_access_token)
    monkeypatch.setattr(UserService, "get_user_by_id", fake_get_user_by_id)

    response = client.post(
        "/users/login",
        json={
            "username": "newuser",
            "password": "supersecret123",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "token-123"
    assert body["token_type"] == "Bearer"
    assert body["user"]["username"] == "newuser"
    assert body["user"]["userid"] == str(user_id)


def test_get_current_user(client: TestClient):
    _set_current_user_override(role="admin")

    response = client.get("/users/me")

    assert response.status_code == 200
    assert response.json()["username"] == "tester"


def test_change_password_success(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _set_current_user_override(role="user")

    async def fake_change_password(_self, _user_id, _current_password, _new_password):
        return True

    monkeypatch.setattr(UserService, "change_password", fake_change_password)

    response = client.post(
        "/users/change-password",
        json={
            "current_password": "supersecret123",
            "new_password": "mynewsecret123",
        },
    )

    assert response.status_code == 200
    assert response.json()["detail"] == "Password updated successfully"


def test_change_password_invalid_current_password(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    _set_current_user_override(role="user")

    async def fake_change_password(_self, _user_id, _current_password, _new_password):
        raise HTTPException(status_code=400, detail="Current password is invalid")

    monkeypatch.setattr(UserService, "change_password", fake_change_password)

    response = client.post(
        "/users/change-password",
        json={
            "current_password": "wrongpass123",
            "new_password": "mynewsecret123",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is invalid"


def test_get_all_users_forbidden_for_user_role(client: TestClient):
    _set_current_user_override(role="user")

    response = client.get("/users")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_update_user_not_found(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _set_current_user_override(role="admin")

    async def fake_update_user(_self, _user_id, _user_update):
        return None

    monkeypatch.setattr(UserService, "update_user", fake_update_user)

    response = client.patch(f"/users/{uuid4()}", json={"fullname": "Updated Name"})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_update_user_forbidden_for_other_user(client: TestClient):
    async def override_get_current_user():
        return UserOut(
            userid=uuid4(),
            username="basic-user",
            email="basic@example.com",
            fullname="Basic User",
            role=UserRole.USER,
            created_at=datetime.now(timezone.utc),
        )

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = client.patch(f"/users/{uuid4()}", json={"fullname": "Hacked Name"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_delete_user_success(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _set_current_user_override(role="admin")

    async def fake_get_user_by_id(_self, _user_id):
        return {
            "userid": uuid4(),
            "username": "delete-me",
            "email": "delete-me@example.com",
            "fullname": "Delete Me",
            "phone_number": None,
            "role": "user",
            "created_at": datetime.now(timezone.utc),
            "password": "hashed",
            "is_superuser": False,
        }

    async def fake_delete_user(_self, _user_id):
        return True

    monkeypatch.setattr(UserService, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(UserService, "delete_user", fake_delete_user)

    response = client.delete(f"/users/{uuid4()}")

    assert response.status_code == 200
    assert response.json()["detail"] == "User deleted successfully"


def test_get_latest_hydroponic_data(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    _set_current_user_override(role="admin")

    sample = HydroponicOut(
        dataid=uuid7(),
        moisture1=10,
        moisture2=11,
        moisture3=12,
        moisture4=13,
        moisture5=14,
        moisture6=15,
        flowrate=1.2,
        total_litres=20.5,
        distance_cm=30.1,
        ph=6.2,
        tds=500.0,
        temperature_atas=25.3,
        temperature_bawah=24.8,
        humidity_atas=60.0,
        humidity_bawah=61.0,
        pump_status=True,
        light_status=False,
        automation_status=True,
    )

    async def fake_get_latest_data(_self):
        return sample

    monkeypatch.setattr(HydroponicService, "get_latest_data", fake_get_latest_data)

    response = client.get("/hydroponics/data/latest")

    assert response.status_code == 200
    assert response.json() == {
        "flowrate": sample.flowrate,
        "distance_cm": sample.distance_cm,
        "total_litres": sample.total_litres,
        "moisture_avg": sample.moisture_avg,
        "temperature_avg": sample.temperature_avg,
        "humidity_avg": sample.humidity_avg,
        "ph": sample.ph,
        "tds": sample.tds,
        "pump_status": sample.pump_status,
        "light_status": sample.light_status,
        "automation_status": sample.automation_status,
    }


def test_get_hydroponic_data_list(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _set_current_user_override(role="admin")

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

    async def fake_get_all_data(
        _self,
        _page=1,
        _limit=25,
        _start_date=None,
        _end_date=None,
    ):
        return ResponseList(
            meta=MetaData(total_rows=1, limit=25, offset=0),
            data=[sample],
        )

    monkeypatch.setattr(HydroponicService, "get_all_data", fake_get_all_data)

    response = client.get("/hydroponics/data")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total_rows"] == 1
    assert len(body["data"]) == 1
