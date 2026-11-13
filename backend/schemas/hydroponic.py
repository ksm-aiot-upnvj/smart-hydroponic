from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, AliasChoices, computed_field
import datetime
from uuid import UUID, uuid7
from typing import Generic, TypeVar, List, Literal

T = TypeVar("T")


class MetaData(BaseModel):
    total_rows: int | None = None
    limit: int
    offset: int

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.limit == 0 or self.total_rows is None:
            return 0
        return (self.total_rows + self.limit - 1) // self.limit

    @computed_field
    @property
    def current_page(self) -> int:
        if self.limit == 0 or self.total_rows is None:
            return 0
        return (self.offset // self.limit) + 1


class ResponseList(BaseModel, Generic[T]):
    meta: MetaData
    data: List[T]


class HydroponicDataPlant(BaseModel):
    """Plant-device sensor payload.

    All measurement fields are REQUIRED even though every value has a valid
    range starting at zero. The deployed ESP32 plant firmware
    (``esp/esp32_plant/esp32_plant.ino``) always serialises the complete set,
    so an omitted key means the device failed to report that measurement. The
    payload must then be rejected instead of silently becoming ``0``, which
    would be indistinguishable from a genuine zero reading (audit finding
    C-4). A measurement that really is ``0`` is still preserved as ``0``.
    """

    moisture1: int = Field(ge=0)
    moisture2: int = Field(ge=0)
    moisture3: int = Field(ge=0)
    moisture4: int = Field(ge=0)
    moisture5: int = Field(ge=0)
    moisture6: int = Field(ge=0)
    flowrate: float = Field(ge=0.0)
    total_litres: float = Field(ge=0.0)
    # The ESP32 plant firmware sends this reading under the key `water_level`,
    # while the stored column/field name is `distance_cm`. Accept both keys so
    # the sensor-to-water-surface distance is populated instead of silently
    # defaulting to 0 (see audit finding AB-01).
    distance_cm: float = Field(
        ge=0.0,
        validation_alias=AliasChoices("distance_cm", "water_level"),
    )


class HydroponicDataEnvironment(BaseModel):
    """Environment-device sensor payload.

    Every field is REQUIRED for the same reason as ``HydroponicDataPlant``:
    the deployed ESP32 environment firmware always sends the complete set, so
    a missing key is a device/reporting fault, not a valid ``0``.
    """

    ph: float = Field(ge=0.0)
    tds: float = Field(ge=0.0)
    temperature_atas: float = Field(ge=0.0)
    temperature_bawah: float = Field(ge=0.0)
    humidity_atas: float = Field(ge=0.0)
    humidity_bawah: float = Field(ge=0.0)


class HydroponicDataActuator(BaseModel):
    """Actuator command and/or reported actuator state.

    Unlike the sensor payloads, these fields stay OPTIONAL and default to
    ``False`` because omission is explicitly supported by the actuator
    protocol: the ESP8266 actuator firmware only applies keys that are present
    (it guards every field with ``doc.containsKey(...)`` in
    ``esp/esp8266_actuator/esp8266_actuator.ino``). Requiring them would break
    partial control commands without improving data integrity.
    """

    pump_status: bool = Field(False)
    light_status: bool = Field(False)
    automation_status: bool = Field(False)


class HydroponicControlResult(HydroponicDataActuator):
    """Outcome of a manual actuator control request (audit finding C-2).

    ``confirmed`` is ``True`` ONLY when the transport yields a genuine
    acknowledgement that the physical actuator applied the command. None of the
    deployed transports provides one: the WebSocket path merely queues the
    payload for a connected client, and the CoAP path updates an in-process
    observable resource whose ESP8266 observer has no request/response
    acknowledgement. ``confirmed`` therefore remains ``False`` and
    ``delivery_status`` states what could actually be established:

    - ``unavailable``: no eligible actuator transport/receiver is reachable.
    - ``dispatched``: the command was handed to the transport only.
    - ``failed``: the transport reported a delivery failure.
    - ``confirmed``: an actual actuator acknowledgement was received.

    ``dispatched`` must never be presented as successful physical execution.
    """

    command_id: str
    confirmed: bool = False
    delivery_status: Literal["confirmed", "dispatched", "unavailable", "failed"] = (
        "dispatched"
    )


class HydroponicAggregate(
    HydroponicDataActuator, HydroponicDataEnvironment, HydroponicDataPlant
):
    """Complete snapshot: plant + environment measurements + actuator state.

    Inheriting the two required-measurement payloads means a snapshot can never
    be persisted with a missing reading. The aggregator only builds snapshots
    from two already-validated per-source payloads (see
    ``HydroponicAggregator._build_snapshot``), so every required field is
    always present.
    """

    dataid: UUID = Field(default_factory=uuid7)


class HydroponicIn(HydroponicAggregate):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dataid": "019b76da-a800-7000-8000-000000000000",
                "moisture1": 450,
                "moisture2": 460,
                "moisture3": 470,
                "moisture4": 480,
                "moisture5": 490,
                "moisture6": 500,
                "flowrate": 1.5,
                "total_litres": 10.0,
                "distance_cm": 15.0,
                "ph": 6.5,
                "tds": 800.0,
                "temperature_atas": 25.0,
                "temperature_bawah": 24.0,
                "humidity_atas": 60.0,
                "humidity_bawah": 65.0,
                "pump_status": 1,
                "light_status": 1,
                "automation_status": 1,
            }
        }
    )


class HydroponicOut(HydroponicAggregate):
    moisture1: int | None = None
    moisture2: int | None = None
    moisture3: int | None = None
    moisture4: int | None = None
    moisture5: int | None = None
    moisture6: int | None = None
    moisture_avg: float | None = None
    flowrate: float | None = None
    total_litres: float | None = None
    distance_cm: float | None = None

    ph: float | None = None
    tds: float | None = None
    temperature_atas: float | None = None
    temperature_bawah: float | None = None
    temperature_avg: float | None = None
    humidity_atas: float | None = None
    humidity_bawah: float | None = None
    humidity_avg: float | None = None

    pump_status: bool | None = None
    light_status: bool | None = None
    automation_status: bool | None = None

    @computed_field
    @property
    def timestamp(self) -> datetime.datetime:
        timestamp_int = UUID(str(self.dataid)).time
        return datetime.datetime.fromtimestamp(
            timestamp_int / 1_000,
            tz=datetime.timezone.utc,
        )

    model_config = ConfigDict(from_attributes=True)


class HydroponicDashboardOut(BaseModel):
    flowrate: float | None = None
    distance_cm: float | None = None
    total_litres: float | None = None
    moisture_avg: float | None = None
    temperature_avg: float | None = None
    humidity_avg: float | None = None
    ph: float | None = None
    tds: float | None = None
    pump_status: bool | None = None
    light_status: bool | None = None
    automation_status: bool | None = None

    model_config = ConfigDict(from_attributes=True)
