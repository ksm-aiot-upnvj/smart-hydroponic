from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, AliasChoices, computed_field
import datetime
from uuid import UUID, uuid7
from typing import Generic, TypeVar, List

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
    moisture1: int = Field(0, ge=0)
    moisture2: int = Field(0, ge=0)
    moisture3: int = Field(0, ge=0)
    moisture4: int = Field(0, ge=0)
    moisture5: int = Field(0, ge=0)
    moisture6: int = Field(0, ge=0)
    flowrate: float = Field(0.0, ge=0.0)
    total_litres: float = Field(0.0, ge=0.0)
    # The ESP32 plant firmware sends this reading under the key `water_level`,
    # while the stored column/field name is `distance_cm`. Accept both keys so
    # the sensor-to-water-surface distance is populated instead of silently
    # defaulting to 0 (see audit finding AB-01).
    distance_cm: float = Field(
        0.0,
        ge=0.0,
        validation_alias=AliasChoices("distance_cm", "water_level"),
    )


class HydroponicDataEnvironment(BaseModel):
    ph: float = Field(0.0, ge=0.0)
    tds: float = Field(0.0, ge=0.0)
    temperature_atas: float = Field(0.0, ge=0.0)
    temperature_bawah: float = Field(0.0, ge=0.0)
    humidity_atas: float = Field(0.0, ge=0.0)
    humidity_bawah: float = Field(0.0, ge=0.0)


class HydroponicDataActuator(BaseModel):
    pump_status: bool = Field(False)
    light_status: bool = Field(False)
    automation_status: bool = Field(False)


class HydroponicControlResult(HydroponicDataActuator):
    command_id: str
    confirmed: bool = False


class HydroponicAggregate(
    HydroponicDataActuator, HydroponicDataEnvironment, HydroponicDataPlant
):
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
