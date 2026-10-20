import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Provide default settings so imports that instantiate Settings() do not fail in tests.
os.environ.setdefault("PGHOST", "localhost")
os.environ.setdefault("PGPORT", "5432")
os.environ.setdefault("PGUSER", "test_user")
import os

# Provide default settings so imports that instantiate Settings() do not fail in tests.
os.environ.setdefault("PGHOST", "localhost")
os.environ.setdefault("PGPORT", "5432")
os.environ.setdefault("PGUSER", "test_user")
os.environ.setdefault("PGPASSWORD", "test_password")
os.environ.setdefault("PGDATABASE", "test_db")
os.environ.setdefault("JWT_EXPIRES_IN", "1h")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("SUPERUSER_USERNAME", "superadmin")
os.environ.setdefault("SUPERUSER_EMAIL", "superadmin@example.com")
os.environ.setdefault("SUPERUSER_PASSWORD", "supersecret123")
os.environ.setdefault("SUPERUSER_ROLE", "superadmin")
os.environ.setdefault("JWT_PRIVATE_KEY", "test/dummy_private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY", "test/dummy_public.pem")


@asynccontextmanager
async def _noop_lifespan(app):
    """Skip the real app startup (CoAP server bind, aggregator drain-loop,
    SnapshotPipeline workers) for tests that mock the aggregator anyway.

    This keeps tests fast, isolated from a prior event loop, and independent
    of COAP_HOST/.env and the CoAP port."""
    yield


@pytest.fixture(autouse=True)
def _isolate_app_lifespan(request):
    """Neutralise the app's real lifespan for every test unless the test opts
    in with @pytest.mark.real_lifespan (see test_lifespan_smoke.py)."""
    if request.node.get_closest_marker("real_lifespan") is not None:
        yield
        return

    from main import app

    with patch.object(app.router, "lifespan_context", _noop_lifespan):
        yield
