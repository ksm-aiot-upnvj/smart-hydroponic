"""C-4 — sensor payload validation must not silently default missing readings.

Covers audit finding C-4:

* A measurement omitted by the device is rejected instead of becoming ``0``.
* A measurement genuinely reported as ``0`` is preserved as ``0``.
* ``null``, negative and non-numeric measurements are rejected.
* A rejected payload never reaches the aggregator, so it is never persisted.
* Rejections emit a ``sensor_anomaly`` diagnostic that names the offending
  fields without writing raw measurement values.

No database or network access is required.
"""

from pathlib import Path
import sys
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from routes.hydroponic_routes import _validation_error_summary
from schemas.hydroponic import (
    HydroponicDataActuator,
    HydroponicDataEnvironment,
    HydroponicDataPlant,
    HydroponicIn,
)

# Mirrors what the deployed ESP32 plant firmware reports.
# See esp/esp32_plant/esp32_plant.ino -> sendSensorData().
PLANT_PAYLOAD = {
    "moisture1": 10,
    "moisture2": 11,
    "moisture3": 12,
    "moisture4": 13,
    "moisture5": 14,
    "moisture6": 15,
    "flowrate": 1.2,
    "total_litres": 20.5,
    "distance_cm": 30.0,
}

# Mirrors what the deployed ESP32 environment firmware reports.
# See esp/esp32_environment/esp32_environment.ino -> sendData().
ENVIRONMENT_PAYLOAD = {
    "ph": 6.2,
    "tds": 500.0,
    "temperature_atas": 25.0,
    "temperature_bawah": 24.0,
    "humidity_atas": 60.0,
    "humidity_bawah": 61.0,
}


def _without(payload: dict, *keys: str) -> dict:
    return {k: v for k, v in payload.items() if k not in keys}


def _error_locations(exc: ValidationError) -> set[str]:
    return {".".join(str(part) for part in error["loc"]) for error in exc.errors()}


# ---------------------------------------------------------------------------
# Schema contract: mandatory measurements
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", sorted(HydroponicDataPlant.model_fields))
def test_plant_payload_rejects_missing_measurement(field):
    with pytest.raises(ValidationError) as exc_info:
        HydroponicDataPlant.model_validate(_without(PLANT_PAYLOAD, field))

    assert field in _error_locations(exc_info.value)


@pytest.mark.parametrize("field", sorted(HydroponicDataEnvironment.model_fields))
def test_environment_payload_rejects_missing_measurement(field):
    with pytest.raises(ValidationError) as exc_info:
        HydroponicDataEnvironment.model_validate(_without(ENVIRONMENT_PAYLOAD, field))

    assert field in _error_locations(exc_info.value)


def test_complete_plant_payload_is_accepted():
    plant = HydroponicDataPlant.model_validate(PLANT_PAYLOAD)

    assert plant.model_dump() == PLANT_PAYLOAD


def test_complete_environment_payload_is_accepted():
    environment = HydroponicDataEnvironment.model_validate(ENVIRONMENT_PAYLOAD)

    assert environment.model_dump() == ENVIRONMENT_PAYLOAD


# ---------------------------------------------------------------------------
# Distinguishing zero / omitted / null / invalid
# ---------------------------------------------------------------------------


def test_explicit_zero_measurements_are_preserved():
    plant = HydroponicDataPlant.model_validate({key: 0 for key in PLANT_PAYLOAD})
    environment = HydroponicDataEnvironment.model_validate(
        {key: 0 for key in ENVIRONMENT_PAYLOAD}
    )

    assert plant.model_dump() == {key: 0 for key in PLANT_PAYLOAD}
    assert environment.model_dump() == {key: 0 for key in ENVIRONMENT_PAYLOAD}


def test_null_measurement_is_rejected():
    with pytest.raises(ValidationError) as exc_info:
        HydroponicDataPlant.model_validate({**PLANT_PAYLOAD, "moisture3": None})

    assert "moisture3" in _error_locations(exc_info.value)


@pytest.mark.parametrize(
    "field",
    ["moisture1", "moisture6", "flowrate", "total_litres", "distance_cm"],
)
def test_negative_plant_measurement_is_rejected(field):
    with pytest.raises(ValidationError) as exc_info:
        HydroponicDataPlant.model_validate({**PLANT_PAYLOAD, field: -1})

    assert field in _error_locations(exc_info.value)


@pytest.mark.parametrize("field", ["ph", "tds", "temperature_atas", "humidity_bawah"])
def test_negative_environment_measurement_is_rejected(field):
    with pytest.raises(ValidationError) as exc_info:
        HydroponicDataEnvironment.model_validate({**ENVIRONMENT_PAYLOAD, field: -0.5})

    assert field in _error_locations(exc_info.value)


def test_non_numeric_measurement_is_rejected():
    with pytest.raises(ValidationError) as exc_info:
        HydroponicDataPlant.model_validate(
            {**PLANT_PAYLOAD, "moisture1": "not-a-number"}
        )

    assert "moisture1" in _error_locations(exc_info.value)


def test_water_level_alias_still_populates_distance_cm():
    payload = _without(PLANT_PAYLOAD, "distance_cm")
    payload["water_level"] = 42.0

    plant = HydroponicDataPlant.model_validate(payload)

    assert plant.distance_cm == 42.0


# ---------------------------------------------------------------------------
# Omission that the device protocol explicitly supports
# ---------------------------------------------------------------------------


def test_actuator_partial_command_is_still_accepted():
    """The ESP8266 actuator firmware applies only the keys it receives
    (``doc.containsKey``), so a partial command must stay valid."""
    actuator = HydroponicDataActuator.model_validate({"pump_status": True})

    assert actuator.pump_status is True
    assert actuator.light_status is False
    assert actuator.automation_status is False


# ---------------------------------------------------------------------------
# Aggregate snapshot: never persist a missing measurement
# ---------------------------------------------------------------------------


def test_aggregate_snapshot_requires_both_source_payloads():
    with pytest.raises(ValidationError):
        HydroponicIn.model_validate({**PLANT_PAYLOAD})

    snapshot = HydroponicIn.model_validate({**PLANT_PAYLOAD, **ENVIRONMENT_PAYLOAD})

    assert snapshot.moisture1 == PLANT_PAYLOAD["moisture1"]
    assert snapshot.ph == ENVIRONMENT_PAYLOAD["ph"]


def test_aggregate_snapshot_rejects_missing_measurement():
    with pytest.raises(ValidationError) as exc_info:
        HydroponicIn.model_validate(
            {**_without(PLANT_PAYLOAD, "moisture3"), **ENVIRONMENT_PAYLOAD}
        )

    assert "moisture3" in _error_locations(exc_info.value)


# ---------------------------------------------------------------------------
# Safe anomaly diagnostics
# ---------------------------------------------------------------------------


def test_validation_error_summary_names_fields_without_values():
    with pytest.raises(ValidationError) as exc_info:
        HydroponicDataPlant.model_validate(
            {**PLANT_PAYLOAD, "moisture3": None, "moisture4": -5}
        )

    summary = _validation_error_summary(exc_info.value)

    assert any(item.startswith("moisture3:") for item in summary)
    assert any(item.startswith("moisture4:") for item in summary)
    assert all("None" not in item and "-5" not in item for item in summary)


def test_validation_error_summary_is_empty_for_non_pydantic_errors():
    assert _validation_error_summary(RuntimeError("boom")) == []


# ---------------------------------------------------------------------------
# WebSocket ingest: rejected payloads never reach the aggregator
# ---------------------------------------------------------------------------


def test_ws_rejects_payload_missing_measurement_without_buffering():
    with patch("routes.hydroponic_routes.aggregator") as mock_agg:
        mock_agg.gather_data = AsyncMock(return_value=True)

        with TestClient(app) as client:
            with client.websocket_connect("/hydroponics/ws/sensor-data") as ws:
                ws.send_json({"physical_id": "test-device"})
                ws.send_json(_without(PLANT_PAYLOAD, "moisture3"))

                assert ws.receive_json() == {
                    "status": "error",
                    "reason": "validation_failed",
                }

        mock_agg.gather_data.assert_not_awaited()


def test_ws_rejects_null_measurement_without_buffering():
    with patch("routes.hydroponic_routes.aggregator") as mock_agg:
        mock_agg.gather_data = AsyncMock(return_value=True)

        with TestClient(app) as client:
            with client.websocket_connect("/hydroponics/ws/environment-data") as ws:
                ws.send_json({"physical_id": "test-env-device"})
                ws.send_json({**ENVIRONMENT_PAYLOAD, "ph": None})

                assert ws.receive_json() == {
                    "status": "error",
                    "reason": "validation_failed",
                }

        mock_agg.gather_data.assert_not_awaited()


def test_ws_accepts_complete_payload_after_a_rejection():
    with patch("routes.hydroponic_routes.aggregator") as mock_agg:
        mock_agg.gather_data = AsyncMock(return_value=True)

        with TestClient(app) as client:
            with client.websocket_connect("/hydroponics/ws/sensor-data") as ws:
                ws.send_json({"physical_id": "test-device"})
                ws.send_json(_without(PLANT_PAYLOAD, "moisture3"))
                assert ws.receive_json()["status"] == "error"

                ws.send_json(PLANT_PAYLOAD)
                assert ws.receive_json()["status"] == "ack"

        mock_agg.gather_data.assert_awaited_once_with(
            source="plant", data=PLANT_PAYLOAD
        )


def test_ws_rejection_emits_safe_sensor_anomaly_log():
    with (
        patch("routes.hydroponic_routes.aggregator") as mock_agg,
        patch(
            "routes.hydroponic_routes.best_effort_log", new_callable=AsyncMock
        ) as mock_log,
    ):
        mock_agg.gather_data = AsyncMock(return_value=True)

        with TestClient(app) as client:
            with client.websocket_connect("/hydroponics/ws/sensor-data") as ws:
                ws.send_json({"physical_id": "test-device"})
                ws.send_json({**PLANT_PAYLOAD, "moisture3": None})
                assert ws.receive_json()["status"] == "error"

        # The anomaly log is scheduled as a background task so the receive loop
        # is never blocked; give the loop a moment to run it.
        deadline = time.monotonic() + 2.0
        while not mock_log.await_args_list and time.monotonic() < deadline:
            time.sleep(0.02)

        assert mock_log.await_args_list, "expected a sensor_anomaly log entry"
        kwargs = mock_log.await_args_list[0].kwargs
        assert kwargs["event_type"] == "sensor_anomaly"
        assert kwargs["severity"] == "warning"
        assert "moisture3" in kwargs["description"]
        # Raw measurement values must never be written to the anomaly log.
        assert "None" not in kwargs["description"]
        assert str(PLANT_PAYLOAD["moisture1"]) not in kwargs["description"]
