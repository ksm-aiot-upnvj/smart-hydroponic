"""Unit tests for Settings parsing and CORS wiring.

These guard the two failures that made a containerised deployment behave
differently from a host run:

* a `.env` holding a host-oriented `DATABASE_URL` (for example
  ``localhost:5433``) leaking into a container, and
* `allow_origins=["*"]` combined with `allow_credentials=True`, which browsers
  reject outright.

No database or network access is required.
"""

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.config import Settings
from main import app

# Values required by Settings that this module does not exercise.
_REQUIRED = {
    "PGHOST": "db",
    "PGPORT": "5432",
    "PGUSER": "user",
    "PGPASSWORD": "password",
    "PGDATABASE": "hydroponic",
    "JWT_EXPIRES_IN": "1h",
    "JWT_PRIVATE_KEY": "keys/private.pem",
    "JWT_PUBLIC_KEY": "keys/public.pem",
    "SUPERUSER_USERNAME": "admin",
    "SUPERUSER_EMAIL": "admin@example.com",
    "SUPERUSER_PASSWORD": "password",
    "SUPERUSER_ROLE": "superadmin",
}


@pytest.fixture(autouse=True)
def _drop_dotenv_leak(monkeypatch: pytest.MonkeyPatch):
    """Keep these tests hermetic.

    Several sibling test modules call ``dotenv.load_dotenv()`` at import time,
    which copies the developer's real ``.env`` into ``os.environ``. ``Settings``
    reads ``os.environ`` even with ``_env_file=None``, so a host-oriented
    ``DATABASE_URL``/``PGPORT`` would leak in and mask the behaviour under test.
    """
    for key in (
        "DATABASE_URL",
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGPASSWORD",
        "PGDATABASE",
        "CORS_ALLOW_ORIGINS",
    ):
        monkeypatch.delenv(key, raising=False)


def make_settings(**overrides) -> Settings:
    """Build Settings without reading any `.env` file."""
    return Settings(_env_file=None, **{**_REQUIRED, **overrides})


def test_database_url_is_built_from_parts_when_unset():
    settings = make_settings()

    assert (
        settings.DATABASE_URL == "postgresql+asyncpg://user:password@db:5432/hydroponic"
    )


def test_blank_database_url_is_treated_as_unset():
    # docker-compose sets DATABASE_URL="" on the containers so that a
    # host-oriented value from .env cannot win.
    settings = make_settings(DATABASE_URL="")

    assert (
        settings.DATABASE_URL == "postgresql+asyncpg://user:password@db:5432/hydroponic"
    )


def test_whitespace_database_url_is_treated_as_unset():
    settings = make_settings(DATABASE_URL="   ")

    assert (
        settings.DATABASE_URL == "postgresql+asyncpg://user:password@db:5432/hydroponic"
    )


def test_explicit_database_url_wins_over_parts():
    explicit = "postgresql+asyncpg://someone:else@far-host:5555/other"

    settings = make_settings(DATABASE_URL=explicit)

    assert settings.DATABASE_URL == explicit


def test_missing_database_parts_report_which_are_missing():
    with pytest.raises(ValidationError) as excinfo:
        make_settings(PGHOST="", PGDATABASE="")

    message = str(excinfo.value)
    assert "PGHOST" in message
    assert "PGDATABASE" in message


def test_cors_origins_default_to_wildcard():
    assert make_settings().cors_allow_origins == ["*"]


def test_cors_origins_are_split_and_trimmed():
    settings = make_settings(CORS_ALLOW_ORIGINS="https://a.test, https://b.test ,")

    assert settings.cors_allow_origins == ["https://a.test", "https://b.test"]


def test_wildcard_origin_disables_credentials():
    """A wildcard origin must never be combined with credentials."""
    response = TestClient(app).options(
        "/health",
        headers={
            "Origin": "https://example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") == "*"
    assert "access-control-allow-credentials" not in response.headers
