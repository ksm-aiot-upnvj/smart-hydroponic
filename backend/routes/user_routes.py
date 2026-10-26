from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from schemas.user import (
    UserCreate,
    UserOut,
    UserLogin,
    LoginResponse,
    AccountSummary,
    UserUpdate,
    PasswordChange,
)
from services.user_service import UserService
from utils.deps import (
    get_current_user,
    get_session,
    require_role,
)
from schemas.responses import (
    MessageResponse,
    responses_400,
    responses_401,
    responses_403,
    responses_404,
    responses_500,
)
import bcrypt
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


def _integrity_error_detail(error: IntegrityError) -> str:
    lowered = str(error).lower()
    if "username" in lowered:
        return "Username already registered"
    if "email" in lowered:
        return "Email already registered"
    return "Data integrity violation"


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    operation_id="registerUser",
    responses={
        **responses_400,
        **responses_500,
    },
)
async def register_user(
    user: UserCreate,
    current_user: UserOut = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_role(current_user, {"superadmin"})
    service = UserService(session)
    try:
        existing_user = await service.get_user_by_username(user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        hashed_password = bcrypt.hashpw(
            user.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user_payload = user.model_copy(update={"password": hashed_password})
        created_user = await service.add_user(user_payload.model_dump())
        return UserOut.model_validate(created_user)
    except IntegrityError as e:
        logger.error("Integrity error: %s", e)
        await session.rollback()
        raise HTTPException(status_code=400, detail=_integrity_error_detail(e))
    except SQLAlchemyError as e:
        logger.error("Database error: %s", e)
        await session.rollback()
        raise HTTPException(status_code=500, detail="Database error")


@router.post(
    "/login",
    response_model=LoginResponse,
    operation_id="loginUser",
    responses={
        **responses_400,
        **responses_401,
        **responses_500,
    },
)
async def login_user(
    user_credentials: UserLogin, session: AsyncSession = Depends(get_session)
):
    service = UserService(session)
    try:
        user = await service.authenticate_user(user_credentials)
        db_user = await service.get_user_by_id(str(user.userid))
        token_version = int(db_user.get("token_version", 0)) if db_user else 0
        access_token = service.create_access_token(
            data={
                "sub": user.username,
                "id": str(user.userid),
                "role": user.role,
                "tv": token_version,
            }
        )
        return LoginResponse(
            access_token=access_token,
            user=AccountSummary(
                userid=user.userid,
                username=user.username,
                email=user.email,
                fullname=user.fullname,
                role=user.role,
            ),
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get(
    "/me",
    response_model=UserOut,
    operation_id="getCurrentUser",
    responses={
        **responses_401,
        **responses_404,
        **responses_500,
    },
)
async def read_current_user(
    current_user: UserOut = Depends(get_current_user),
):
    try:
        return current_user
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get(
    "",
    response_model=list[UserOut],
    operation_id="getAllUsers",
    responses={
        **responses_401,
        **responses_403,
        **responses_500,
    },
)
async def read_users(
    current_user: UserOut = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_role(current_user, {"admin", "superadmin"})
    service = UserService(session)
    try:
        users = await service.get_all_users()
        return [UserOut.model_validate(user) for user in users]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    operation_id="updateUser",
    responses={
        **responses_400,
        **responses_401,
        **responses_403,
        **responses_404,
        **responses_500,
    },
)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: UserOut = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_role(current_user, {"user", "admin", "superadmin"})
    if current_user.role == "user" and str(current_user.userid) != user_id:
        raise HTTPException(status_code=403, detail="Permission denied")

    if current_user.role == "user" and (
        user_update.role == "admin" or user_update.role == "superadmin"
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = UserService(session)
    try:
        updated_user = await service.update_user(user_id, user_update)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserOut.model_validate(updated_user)

    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=_integrity_error_detail(e))
    except SQLAlchemyError as e:
        logger.error("Database error: %s", e)
        raise HTTPException(status_code=500, detail="Database error")


@router.delete(
    "/{user_id}",
    status_code=200,
    operation_id="deleteUser",
    responses={
        **responses_401,
        **responses_403,
        **responses_404,
        **responses_500,
    },
)
async def delete_user(
    user_id: str,
    current_user: UserOut = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_role(current_user, {"admin", "superadmin"})
    service = UserService(session)
    try:
        user = await service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await service.delete_user(user_id)
        return {"detail": "User deleted successfully"}
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error("Database error: %s", e)
        raise HTTPException(status_code=500, detail="Database error")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    operation_id="changePassword",
    responses={
        **responses_400,
        **responses_401,
        **responses_404,
        **responses_500,
    },
)
async def change_password(
    payload: PasswordChange,
    current_user: UserOut = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = UserService(session)
    try:
        await service.change_password(
            str(current_user.userid),
            payload.current_password,
            payload.new_password,
        )
        return MessageResponse(detail="Password updated successfully")
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error("Database error: %s", e)
        raise HTTPException(status_code=500, detail="Database error")
