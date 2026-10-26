from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Boolean, Computed
from sqlalchemy.dialects.postgresql import UUID, DOUBLE_PRECISION
from config.db import Base
from uuid import uuid7


class HydroponicData(Base):
    __tablename__ = "hydroponic_data"

    dataid: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    # Plant Data
    moisture1: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moisture2: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moisture3: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moisture4: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moisture5: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moisture6: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    moisture_avg: Mapped[float] = mapped_column(
        DOUBLE_PRECISION,
        Computed(
            "((moisture1 + moisture2 + moisture3 + moisture4 + moisture5 + moisture6) / 6.0)",
            persisted=True,
        ),
    )
    flowrate: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, nullable=False, default=0.0
    )
    total_litres: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, nullable=False, default=0.0
    )
    distance_cm: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, nullable=False, default=0.0
    )
    ph: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False, default=0.0)
    tds: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False, default=0.0)

    # Environment Data
    temperature_atas: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, nullable=False, default=0.0
    )
    temperature_bawah: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, nullable=False, default=0.0
    )
    temperature_avg: Mapped[float] = mapped_column(
        DOUBLE_PRECISION,
        Computed("((temperature_atas + temperature_bawah) / 2.0)", persisted=True),
    )
    humidity_atas: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, nullable=False, default=0.0
    )
    humidity_bawah: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, nullable=False, default=0.0
    )
    humidity_avg: Mapped[float] = mapped_column(
        DOUBLE_PRECISION,
        Computed("((humidity_atas + humidity_bawah) / 2.0)", persisted=True),
    )
    light_intensity_atas: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    light_intensity_bawah: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    light_intensity_avg: Mapped[float] = mapped_column(
        DOUBLE_PRECISION,
        Computed(
            "((light_intensity_atas + light_intensity_bawah) / 2.0)", persisted=True
        ),
    )

    # Actuator Data
    pump_status: Mapped[bool] = mapped_column(Boolean, nullable=False)
    light_status: Mapped[bool] = mapped_column(Boolean, nullable=False)
    automation_status: Mapped[bool] = mapped_column(Boolean, nullable=False)
