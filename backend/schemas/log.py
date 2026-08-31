from __future__ import annotations

import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from models.log import LogEventType, LogSeverity


class LogBase(BaseModel):
    event_type: LogEventType = Field(..., description="Kategori event log")
    severity: LogSeverity = Field(..., description="Tingkat keparahan")
    description: str = Field(..., min_length=1, description="Detail log")
    userid: Optional[UUID] = Field(
        None, description="User yang memicu event (jika user-triggered)"
    )
    data_ref: Optional[UUID] = Field(
        None, description="UUID data hidroponik terkait (opsional)"
    )


class LogCreate(LogBase):
    pass


class LogOut(LogBase):
    logid: UUID

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def timestamp(self) -> datetime.datetime:
        timestamp_int = UUID(str(self.logid)).time
        date = datetime.datetime.fromtimestamp(
            timestamp_int / 1_000,
            tz=datetime.datetime.now(datetime.timezone.utc).tzinfo,
        )
        return date


class LogFilter(BaseModel):
    event_type: Optional[LogEventType] = None
    severity: Optional[LogSeverity] = None
    page: int = Field(1, ge=1)
    limit: int = Field(25, ge=1, le=500)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


__all__ = [
    "LogBase",
    "LogCreate",
    "LogOut",
    "LogFilter",
]
