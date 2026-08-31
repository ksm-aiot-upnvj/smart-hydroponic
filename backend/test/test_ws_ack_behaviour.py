# backend/test/test_ws_ack_behaviour.py
"""
NOTE on patching strategy: hydroponic_routes.py does
`from utils.aggregator import aggregator`, which binds a local name
`aggregator` inside the routes.hydroponic_routes module namespace at
import time. The route code then calls `await aggregator.gather_data(...)`
using THAT local name — so patching `routes.hydroponic_routes.aggregator`
correctly intercepts the call. If the import style in hydroponic_routes.py
ever changes (e.g. to `import utils.aggregator` + qualified access), this
patch target must change too, or these tests will silently exercise the
real aggregator instead of the mock.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlib import asynccontextmanager  # <-- add this import
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from main import app

SENSOR_PAYLOAD = {
    "moisture1": 10,
    "moisture2": 10,
    "moisture3": 10,
    "moisture4": 10,
    "moisture5": 10,
    "moisture6": 10,
    "flowrate": 1.0,
    "total_litres": 1.0,
    "distance_cm": 5.0,
}


# <-- add this helper here, near the top-level constants
@asynccontextmanager
async def _noop_lifespan(app):
    """Skip real app startup (CoAP server, aggregator background tasks,
    SnapshotPipeline workers) for tests that don't need them and are
    mocking `aggregator` anyway. Prevents orphaned background tasks from
    a prior event loop colliding with each test's own loop."""
    yield


def test_ws_sends_dropped_status_when_rate_limited():
    with patch("routes.hydroponic_routes.aggregator") as mock_agg:
        mock_agg.gather_data = AsyncMock(return_value=False)

        with TestClient(app) as client:
            with client.websocket_connect("/hydroponics/ws/sensor-data") as ws:
                ws.send_json({"physical_id": "test-device"})
                ws.send_json(SENSOR_PAYLOAD)
                response = ws.receive_json()

                assert response["status"] == "dropped"
                assert response["reason"] == "rate_limited_or_buffer_full"

        mock_agg.gather_data.assert_awaited_once_with(
            source="plant",
            data=SENSOR_PAYLOAD,
        )


def test_ws_sends_ack_when_buffered_successfully():
    with patch("routes.hydroponic_routes.aggregator") as mock_agg:
        mock_agg.gather_data = AsyncMock(return_value=True)

        with TestClient(app) as client:
            with client.websocket_connect("/hydroponics/ws/sensor-data") as ws:
                ws.send_json({"physical_id": "test-device"})
                ws.send_json(SENSOR_PAYLOAD)
                response = ws.receive_json()

                assert response["status"] == "ack"

        mock_agg.gather_data.assert_awaited_once_with(
            source="plant",
            data=SENSOR_PAYLOAD,
        )


def test_ws_environment_role_passes_correct_source():
    with patch("routes.hydroponic_routes.aggregator") as mock_agg:
        mock_agg.gather_data = AsyncMock(return_value=True)

        env_payload = {
            "ph": 6.5,
            "tds": 800.0,
            "temperature_atas": 25.0,
            "temperature_bawah": 24.0,
            "humidity_atas": 60.0,
            "humidity_bawah": 65.0,
        }

        with TestClient(app) as client:
            with client.websocket_connect("/hydroponics/ws/environment-data") as ws:
                ws.send_json({"physical_id": "test-env-device"})
                ws.send_json(env_payload)
                response = ws.receive_json()

                assert response["status"] == "ack"

        mock_agg.gather_data.assert_awaited_once_with(
            source="environment",
            data=env_payload,
        )


def test_ws_closes_with_1011_when_gather_data_raises():
    with (
        patch("routes.hydroponic_routes.aggregator") as mock_agg,
        patch.object(app.router, "lifespan_context", _noop_lifespan),
    ):
        mock_agg.gather_data = AsyncMock(side_effect=RuntimeError("boom"))

        with TestClient(app) as client:
            with client.websocket_connect("/hydroponics/ws/sensor-data") as ws:
                ws.send_json({"physical_id": "test-device"})
                ws.send_json(SENSOR_PAYLOAD)

                with pytest.raises(WebSocketDisconnect) as exc_info:
                    ws.receive_json()

                assert exc_info.value.code == 1011
