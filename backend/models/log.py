from typing import TYPE_CHECKING, Optional
import enum

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from config.db import Base

if TYPE_CHECKING:
    from models.user import User


class LogEventType(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    AUTOMATION = "automation"
    SENSOR_ANOMALY = "sensor_anomaly"
    ACTUATOR = "actuator"
    DEVICE = "device"
    SECURITY = "security"


class LogSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Log(Base):
    __tablename__ = "logs"

    logid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    userid: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_data.userid", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[LogEventType] = mapped_column(
        SQLEnum(
            LogEventType,
            name="log_event_type_enum",
            values_callable=lambda en: [e.value for e in en],
            create_constraint=True,
        ),
        index=True,
    )
    severity: Mapped[LogSeverity] = mapped_column(
        SQLEnum(
            LogSeverity,
            name="log_severity_enum",
            values_callable=lambda en: [e.value for e in en],
            create_constraint=True,
        ),
        index=True,
    )
    data_ref: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    description: Mapped[str] = mapped_column(Text)
    source_ip: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="logs")
