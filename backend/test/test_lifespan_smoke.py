"""Smoke test for the real application lifespan.

Every other test runs with a neutralised lifespan (see conftest.py) so it stays
fast, isolated, and independent of COAP_HOST/.env and the CoAP port. This is
the single place that verifies the real startup path still works: the CoAP
server bind, the aggregator drain-loop, and the SnapshotPipeline workers.
"""

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app


@pytest.mark.real_lifespan
def test_real_lifespan_starts_and_serves_health(monkeypatch: pytest.MonkeyPatch):
    # The dev .env sets COAP_HOST=0.0.0.0 (correct for Docker), which aiocoap
    # refuses to bind to. Pin it to loopback so the test is deterministic.
    monkeypatch.setenv("COAP_HOST", "127.0.0.1")

    with TestClient(app) as client:
        # Real lifespan only: app.state.snapshot_pipeline is set during startup.
        # If the neutralised lifespan were used instead, this would not exist.
        assert hasattr(app.state, "snapshot_pipeline")
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
