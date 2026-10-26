from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from uuid import UUID


class PlantNutritionProfileBase(BaseModel):
    plant_name: str = Field(min_length=2, max_length=120)
    moisture_min: float = Field(ge=0, le=100)
    moisture_max: float = Field(ge=0, le=100)
    ph_min: float = Field(ge=0, le=14)
    ph_max: float = Field(ge=0, le=14)
    tds_min: float = Field(ge=0)
    tds_max: float = Field(ge=0)
    temperature_min: float = Field(ge=-10, le=60)
    temperature_max: float = Field(ge=-10, le=60)
    humidity_min: float = Field(ge=0, le=100)
    humidity_max: float = Field(ge=0, le=100)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.moisture_min > self.moisture_max:
            raise ValueError("moisture_min must be less than or equal to moisture_max")
        if self.ph_min > self.ph_max:
            raise ValueError("ph_min must be less than or equal to ph_max")
        if self.tds_min > self.tds_max:
            raise ValueError("tds_min must be less than or equal to tds_max")
        if self.temperature_min > self.temperature_max:
            raise ValueError(
                "temperature_min must be less than or equal to temperature_max"
            )
        if self.humidity_min > self.humidity_max:
            raise ValueError("humidity_min must be less than or equal to humidity_max")
        return self


class PlantNutritionProfileCreate(PlantNutritionProfileBase):
    pass


class PlantNutritionProfileUpdate(BaseModel):
    plant_name: str | None = Field(default=None, min_length=2, max_length=120)
    moisture_min: float | None = Field(default=None, ge=0, le=100)
    moisture_max: float | None = Field(default=None, ge=0, le=100)
    ph_min: float | None = Field(default=None, ge=0, le=14)
    ph_max: float | None = Field(default=None, ge=0, le=14)
    tds_min: float | None = Field(default=None, ge=0)
    tds_max: float | None = Field(default=None, ge=0)
    temperature_min: float | None = Field(default=None, ge=-10, le=60)
    temperature_max: float | None = Field(default=None, ge=-10, le=60)
    humidity_min: float | None = Field(default=None, ge=0, le=100)
    humidity_max: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=1000)


class PlantNutritionProfileOut(PlantNutritionProfileBase):
    nutrition_id: UUID

    is_active: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
