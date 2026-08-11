from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, computed_field
import datetime
from typing import Optional
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


class HydroponicInternalResult(BaseModel):
    data: List[HydroponicOut]
    total: int | None


class HydroponicDataPlant(BaseModel):
    moisture1: int = Field(0, ge=0)
    moisture2: int = Field(0, ge=0)
    moisture3: int = Field(0, ge=0)
    moisture4: int = Field(0, ge=0)
    moisture5: int = Field(0, ge=0)
    moisture6: int = Field(0, ge=0)
    flowrate: float = Field(0.0, ge=0.0)
    total_litres: float = Field(0.0, ge=0.0)
    distance_cm: float = Field(0.0, ge=0.0)


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
                "light_intensity_atas": 700,
                "light_intensity_bawah": 650,
                "pump_status": 1,
                "light_status": 1,
                "automation_status": 1,
            }
        }
    )


class HydroponicOut(HydroponicAggregate):
    moisture1: Optional[int] = None
    moisture2: Optional[int] = None
    moisture3: Optional[int] = None
    moisture4: Optional[int] = None
    moisture5: Optional[int] = None
    moisture6: Optional[int] = None
    moisture_avg: Optional[float] = None
    flowrate: Optional[float] = None
    total_litres: Optional[float] = None
    distance_cm: Optional[float] = None

    ph: Optional[float] = None
    tds: Optional[float] = None
    temperature_atas: Optional[float] = None
    temperature_bawah: Optional[float] = None
    temperature_avg: Optional[float] = None
    humidity_atas: Optional[float] = None
    humidity_bawah: Optional[float] = None
    humidity_avg: Optional[float] = None

    pump_status: Optional[bool] = None
    light_status: Optional[bool] = None
    automation_status: Optional[bool] = None

    @computed_field
    @property
    def timestamp(self) -> datetime.datetime:
        timestamp_int = UUID(str(self.dataid)).time
        date = datetime.datetime.fromtimestamp(
            timestamp_int / 1_000,
            tz=datetime.datetime.now(datetime.timezone.utc).tzinfo,
        )
        return date

    model_config = ConfigDict(from_attributes=True)


class HydroponicDashboardOut(BaseModel):
    flowrate: Optional[float] = None
    distance_cm: Optional[float] = None
    total_litres: Optional[float] = None
    moisture_avg: Optional[float] = None
    temperature_avg: Optional[float] = None
    humidity_avg: Optional[float] = None
    ph: Optional[float] = None
    tds: Optional[float] = None
    pump_status: Optional[bool] = None
    light_status: Optional[bool] = None
    automation_status: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)
