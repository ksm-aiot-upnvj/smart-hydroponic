"""Superuser bootstrap failure handling (M-5).

A missing credential must abort startup (non-zero exit) instead of silently
booting an API with no administrator account, while a pre-existing superuser
must remain an idempotent no-op. No real database is required.
"""

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import utils.superuser as superuser_module


class _FakeBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeSession:
    def __init__(self, existing_row):
        self._existing_row = existing_row
        self.added: list = []
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def begin(self):
        return _FakeBegin()

    async def execute(self, *_args, **_kwargs):
        return _FakeResult(self._existing_row)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True


def _patch_settings(monkeypatch, **overrides):
    base = {
        "SUPERUSER_USERNAME": "admin",
        "SUPERUSER_EMAIL": "admin@example.com",
        "SUPERUSER_PASSWORD": "secret",
    }
    base.update(overrides)
    monkeypatch.setattr(superuser_module, "settings", SimpleNamespace(**base))
    monkeypatch.setattr(superuser_module, "hash_password", lambda _p: "hashed")


@pytest.mark.asyncio
async def test_missing_username_aborts_bootstrap(monkeypatch):
    _patch_settings(monkeypatch, SUPERUSER_USERNAME="")

    with pytest.raises(RuntimeError):
        await superuser_module.create_superuser()


@pytest.mark.asyncio
async def test_missing_password_aborts_bootstrap(monkeypatch):
    _patch_settings(monkeypatch, SUPERUSER_PASSWORD="")

    with pytest.raises(RuntimeError):
        await superuser_module.create_superuser()


@pytest.mark.asyncio
async def test_existing_superuser_is_idempotent(monkeypatch):
    _patch_settings(monkeypatch)
    session = _FakeSession(existing_row={"username": "admin"})
    monkeypatch.setattr(superuser_module, "Session", lambda: session)

    await superuser_module.create_superuser()

    assert session.added == []
    assert session.committed is False


@pytest.mark.asyncio
async def test_superuser_is_created_when_absent(monkeypatch):
    _patch_settings(monkeypatch)
    session = _FakeSession(existing_row=None)
    monkeypatch.setattr(superuser_module, "Session", lambda: session)

    await superuser_module.create_superuser()

    assert len(session.added) == 1
    created = session.added[0]
    assert created.username == "admin"
    assert created.is_superuser is True
    assert created.password == "hashed"
    assert session.committed is True
