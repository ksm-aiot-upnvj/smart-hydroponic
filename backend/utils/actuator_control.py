import os
from typing import Any

from models.nutrition import PlantNutritionProfile

MOISTURE_THRESHOLD = float(os.getenv("HYDROPONIC_MOISTURE_THRESHOLD", "60"))
TEMPERATURE_THRESHOLD = float(os.getenv("HYDROPONIC_TEMPERATURE_THRESHOLD", "30.0"))


def _average(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    if len(numbers) != len(values):
        return None
    return sum(numbers) / len(numbers)


def build_actuator_control_payload(
    snapshot: dict[str, Any], active_profile: PlantNutritionProfile | None = None
) -> dict[str, Any]:
    moisture_avg = snapshot.get("moisture_avg")
    if moisture_avg is None:
        moisture_avg = _average(
            [
                snapshot.get("moisture1"),
                snapshot.get("moisture2"),
                snapshot.get("moisture3"),
                snapshot.get("moisture4"),
                snapshot.get("moisture5"),
                snapshot.get("moisture6"),
            ]
        )

    temperature_avg = snapshot.get("temperature_avg")
    if temperature_avg is None:
        temperature_avg = _average(
            [
                snapshot.get("temperature_atas"),
                snapshot.get("temperature_bawah"),
            ]
        )

    automation_status = bool(snapshot.get("automation_status", False))
    current_pump = bool(snapshot.get("pump_status", False))
    current_light = bool(snapshot.get("light_status", False))

    pump_status = current_pump
    light_status = current_light

    if automation_status:
        if moisture_avg is not None:
            if active_profile:
                if moisture_avg < active_profile.moisture_min:
                    pump_status = True
                elif moisture_avg > active_profile.moisture_max:
                    pump_status = False
            else:
                if moisture_avg < MOISTURE_THRESHOLD:
                    pump_status = True
                elif moisture_avg >= MOISTURE_THRESHOLD:
                    pump_status = False

        if temperature_avg is not None:
            if active_profile:
                if temperature_avg < active_profile.temperature_min:
                    light_status = True
                elif temperature_avg > active_profile.temperature_max:
                    light_status = False
            else:
                if temperature_avg < TEMPERATURE_THRESHOLD:
                    light_status = True
                elif temperature_avg >= TEMPERATURE_THRESHOLD:
                    light_status = False

    pump_changed = pump_status != current_pump
    light_changed = light_status != current_light
    change_detected = pump_changed or light_changed

    changes: list[str] = []
    if pump_changed:
        changes.append(f"pump={'ON' if pump_status else 'OFF'}")
    if light_changed:
        changes.append(f"light={'ON' if light_status else 'OFF'}")
    change_summary = ", ".join(changes) if changes else ""

    return {
        "moisture_avg": moisture_avg,
        "temperature_avg": temperature_avg,
        "pump_status": pump_status,
        "light_status": light_status,
        "automation_status": automation_status,
        "change_detected": change_detected,
        "pump_changed": pump_changed,
        "light_changed": light_changed,
        "change_summary": change_summary,
    }
