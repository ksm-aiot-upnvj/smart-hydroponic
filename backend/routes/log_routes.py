from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.log import LogEventType, LogSeverity
from schemas.hydroponic import ResponseList
from schemas.responses import (
    MessageResponse,
    responses_400,
    responses_401,
    responses_403,
    responses_404,
)
from schemas.user import UserOut
from schemas.log import LogFilter, LogOut
from services.log_service import LogService
from utils.deps import get_current_user, get_session, require_role

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get(
    "",
    response_model=ResponseList[LogOut],
    status_code=200,
    operation_id="listLogs",
)
async def list_logs(
    event_type: Optional[LogEventType] = None,
    severity: Optional[LogSeverity] = None,
    page: int = 1,
    limit: int = 25,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: UserOut = Depends(get_current_user),
):
    require_role(current_user, {"admin", "superadmin"})
    service = LogService(session)
    filters = LogFilter(
        event_type=event_type,
        severity=severity,
        page=page,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
    )
    return await service.get_logs(filters)


@router.get(
    "/recent",
    response_model=list[LogOut],
    status_code=200,
    operation_id="getRecentLogs",
)
async def get_recent_logs(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    current_user: UserOut = Depends(get_current_user),
):
    require_role(current_user, {"admin", "superadmin"})
    service = LogService(session)
    return await service.get_recent_logs(limit)


@router.delete(
    "/{logid}",
    response_model=MessageResponse,
    status_code=200,
    responses={**responses_400, **responses_401, **responses_403, **responses_404},
    operation_id="deleteLog",
)
async def delete_log(
    logid: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserOut = Depends(get_current_user),
):
    require_role(current_user, {"superadmin"})
    service = LogService(session)
    existing = await service.get_log_by_id(logid)
    if not existing:
        raise HTTPException(status_code=404, detail="Log entry not found")

    deleted = await service.delete_log(logid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Log entry not found")

    await service.write_log(
        event_type="user",
        severity="info",
        description=f"Deleted log entry {logid}",
        userid=current_user.userid,
    )

    return MessageResponse(message=f"Log {logid} has been deleted")
