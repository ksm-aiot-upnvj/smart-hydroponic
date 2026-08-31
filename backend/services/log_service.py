import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.log import LogEventType, LogSeverity
from schemas.hydroponic import MetaData, ResponseList
from schemas.log import LogCreate, LogFilter, LogOut
from utils.converter import get_uuidv7_from_timestamp


class LogService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_log(self, entry: LogCreate) -> LogOut:
        data_dict = entry.model_dump()
        if "logid" not in data_dict:
            data_dict["logid"] = uuid.uuid7()

        columns = ", ".join(f'"{k}"' for k in data_dict.keys())
        placeholders = ", ".join(f":{k}" for k in data_dict.keys())

        stmt = text(f"""
            INSERT INTO logs ({columns})
            VALUES ({placeholders})
            RETURNING *
        """)

        result = await self.session.execute(stmt, data_dict)
        await self.session.commit()
        record = result.mappings().first()
        return LogOut.model_validate(record)

    async def write_log(
        self,
        *,
        event_type: LogEventType | str,
        severity: LogSeverity | str,
        description: str,
        userid: UUID | str | None = None,
        data_ref: UUID | str | None = None,
    ) -> LogOut:
        """Convenience helper that accepts primitive values, enums, and string IDs."""
        if isinstance(event_type, str):
            event_type = LogEventType(event_type)
        if isinstance(severity, str):
            severity = LogSeverity(severity)

        entry = LogCreate(
            event_type=event_type,
            severity=severity,
            description=description,
            userid=UUID(str(userid)) if userid is not None else None,
            data_ref=UUID(str(data_ref)) if data_ref is not None else None,
        )
        return await self.add_log(entry)

    async def _apply_filters(
        self, filters: LogFilter
    ) -> tuple[list[str], dict[str, Any]]:
        conditions: list[str] = []
        params: dict[str, Any] = {}

        if filters.event_type is not None:
            conditions.append("event_type = :event_type")
            params["event_type"] = filters.event_type.value
        if filters.severity is not None:
            conditions.append("severity = :severity")
            params["severity"] = filters.severity.value

        if filters.start_date:
            _start = get_uuidv7_from_timestamp(filters.start_date)
            conditions.append("logid >= :start_date")
            params["start_date"] = _start
        if filters.end_date:
            _end = get_uuidv7_from_timestamp(filters.end_date, is_end=True)
            conditions.append("logid < :end_date")
            params["end_date"] = _end

        return conditions, params

    async def get_logs(self, filters: LogFilter) -> ResponseList[LogOut]:
        offset = (filters.page - 1) * filters.limit
        conditions, params = await self._apply_filters(filters)
        params["limit"] = filters.limit
        params["offset"] = offset

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        query_data = f"""
            SELECT * FROM logs
            {where_clause}
            ORDER BY logid DESC
            LIMIT :limit OFFSET :offset
        """

        query_count = f"""
            SELECT COUNT(*) FROM logs
            {where_clause}
        """

        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}

        data_result = await self.session.execute(text(query_data), params)
        count_result = await self.session.execute(text(query_count), count_params)

        return ResponseList(
            meta=MetaData(
                total_rows=count_result.scalar_one_or_none(),
                limit=filters.limit,
                offset=offset,
            ),
            data=[LogOut.model_validate(row) for row in data_result.mappings().all()],
        )

    async def get_recent_logs(self, limit: int = 50) -> list[LogOut]:
        limit = max(1, min(limit, 500))
        stmt = text("""
            SELECT * FROM logs ORDER BY logid DESC LIMIT :limit
        """)
        result = await self.session.execute(stmt, {"limit": limit})
        return [LogOut.model_validate(row) for row in result.mappings().all()]

    async def delete_log(self, logid: UUID | str) -> bool:
        stmt = text("DELETE FROM logs WHERE logid = :id RETURNING logid")
        result = await self.session.execute(stmt, {"id": logid})
        deleted = result.first() is not None
        if deleted:
            await self.session.commit()
        return deleted

    async def get_log_by_id(self, logid: UUID | str) -> LogOut | None:
        stmt = text("SELECT * FROM logs WHERE logid = :id")
        result = await self.session.execute(stmt, {"id": logid})
        record = result.mappings().first()
        if record:
            return LogOut.model_validate(record)
        return None
