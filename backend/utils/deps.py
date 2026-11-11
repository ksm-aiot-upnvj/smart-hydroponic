from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from config.db import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from schemas.user import TokenPayload, UserOut
from services.user_service import UserService
from contextlib import asynccontextmanager
from authlib.jose.errors import JoseError

bearer_scheme = HTTPBearer()
optional_bearer_scheme = HTTPBearer(auto_error=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a SQLAlchemy async session (expire_on_commit=False)"""
    async with Session() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
):
    service = UserService(session)
    try:
        token = credentials.credentials
        payload = service.verify_token(token)
        payload = TokenPayload.model_validate(payload)

        if payload.id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

    except JoseError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = await service.get_user_by_id(payload.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_token_version = int(user.get("token_version", 0))
    if payload.tv != user_token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated",
        )

    return UserOut.model_validate(user)


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> UserOut | None:
    if credentials is None:
        return None

    service = UserService(session)
    try:
        token = credentials.credentials
        payload = service.verify_token(token)
        payload = TokenPayload.model_validate(payload)

        if payload.id is None:
            return None

    except JoseError:
        return None

    user = await service.get_user_by_id(payload.id)
    if not user:
        return None

    user_token_version = int(user.get("token_version", 0))
    if payload.tv != user_token_version:
        return None

    return UserOut.model_validate(user)


# For use outside a Depends context, e.g. WebSocket handlers.
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager to provide a SQLAlchemy async session."""
    async with Session() as session:
        try:
            yield session
        finally:
            await session.close()


def require_role(current_user: UserOut | None, allowed_roles: set[str]) -> None:
    if current_user is None or current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Permission denied")
