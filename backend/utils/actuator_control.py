from typing import Any

from config.config import settings
from schemas.nutrition import PlantNutritionProfileOut


def _average(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    if len(numbers) != len(values):
        return None
    return sum(numbers) / len(numbers)


def build_actuator_control_payload(
    snapshot: dict[str, Any],
    active_profile: PlantNutritionProfileOut | None = None,
    *,
    profile_available: bool = True,
) -> dict[str, Any]:
    """Derive the actuator payload for a snapshot.

    ``profile_available`` distinguishes a legitimate absence of an active
    nutrition profile (``active_profile is None`` with ``profile_available``
    true — the explicitly configured fallback thresholds are valid) from a
    failed profile lookup (``profile_available`` false). When the profile could
    not be retrieved the automatic actuator decision is skipped entirely: the
    current actuator state is left unchanged and ``automation_degraded`` is
    reported, because acting on an unverified decision could command an unsafe
    state (audit finding H-3).
    """
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

    automation_degraded = False
    skip_reason: str | None = None

    if automation_status:
        if not profile_available:
            # A configured nutrition profile could not be retrieved. Never
            # substitute the generic thresholds here: the fallback would look
            # like a normal decision while silently ignoring the operator's
            # configuration. Fail safe by leaving the actuator state untouched.
            automation_degraded = True
            skip_reason = (
                "active nutrition profile could not be retrieved "
                "(profile lookup failed); automatic actuator decision skipped"
            )
        else:
            if moisture_avg is not None:
                if active_profile:
                    if moisture_avg < active_profile.moisture_min:
                        pump_status = True
                    elif moisture_avg > active_profile.moisture_max:
                        pump_status = False
                else:
                    # Legitimate absence of an active profile: these fallback
                    # thresholds are explicit, valid configuration.
                    if moisture_avg < settings.HYDROPONIC_MOISTURE_THRESHOLD:
                        pump_status = True
                    else:
                        pump_status = False

            if temperature_avg is not None:
                if active_profile:
                    if temperature_avg < active_profile.temperature_min:
                        light_status = True
                    elif temperature_avg > active_profile.temperature_max:
                        light_status = False
                else:
                    if temperature_avg < settings.HYDROPONIC_TEMPERATURE_THRESHOLD:
                        light_status = True
                    else:
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
        "automation_degraded": automation_degraded,
        "automation_skip_reason": skip_reason,
    }
