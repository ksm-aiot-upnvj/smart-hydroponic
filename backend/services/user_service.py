from datetime import datetime, timedelta, timezone
import re
import uuid
from fastapi import HTTPException
from authlib.jose import jwt
from config.config import settings
from utils.crypto import load_signing_key, load_verification_key
from utils.security import hash_password, verify_password
from schemas.user import UserLogin, UserUpdate, UserOut, TokenPayload

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text


class UserService:
    """Data access + auth logic for user accounts.

    All user queries use raw SQL via ``sqlalchemy.text()`` on purpose: it keeps
    the user-query surface area explicit and easy to audit. This differs from
    the ORM-based services (e.g. ``HydroponicService``) by intentional choice,
    not oversight.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _parse_expiry_seconds(self, expiry_value: str) -> int:
        value = expiry_value.strip().lower()
        if value.isdigit():
            return int(value)

        match = re.fullmatch(r"(\d+)\s*([smhd])", value)
        if not match:
            return 3600

        amount = int(match.group(1))
        unit = match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return amount * multipliers[unit]

    async def authenticate_user(self, user_credentials: UserLogin):
        user = None

        if user_credentials.username:
            user = await self.get_user_by_username(user_credentials.username)
        elif user_credentials.email:
            user = await self.get_user_by_email(user_credentials.email)

        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if not verify_password(user_credentials.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        return UserOut.model_validate(user)

    def create_access_token(self, data: dict):
        now = datetime.now(timezone.utc)
        expiry_seconds = self._parse_expiry_seconds(settings.ACCESS_TOKEN_EXPIRE)
        payload = TokenPayload(
            **data,
            iat=int(now.timestamp()),
            exp=int((now + timedelta(seconds=expiry_seconds)).timestamp()),
        )
        key = load_signing_key()
        return jwt.encode(
            {"alg": settings.ALGORITHM}, payload.model_dump(), key
        ).decode("utf-8")

    def verify_token(self, token: str):
        key = load_verification_key()
        claims = jwt.decode(token, key)
        claims.validate()

        return claims

    async def add_user(self, user_data: dict):
        role = user_data.get("role", "user")
        if hasattr(role, "value"):
            role = role.value

        user_id = user_data.get("userid", uuid.uuid4())

        stmt = text(
            """
            INSERT INTO user_data (userid, username, email, password, role, is_superuser, fullname, phone_number)
            VALUES (:userid, :username, :email, :password, :role, :is_superuser, :fullname, :phone_number)
            RETURNING *
            """
        )
        params = {
            "userid": user_id,
            "username": user_data["username"],
            "email": user_data["email"],
            "password": hash_password(user_data["password"]),
            "role": role,
            "is_superuser": bool(user_data.get("is_superuser", False)),
            "fullname": user_data.get("fullname"),
            "phone_number": user_data.get("phone_number"),
        }
        result = await self.session.execute(stmt, params)
        await self.session.commit()
        return result.mappings().first()

    async def get_user_by_username(self, username: str):
        stmt = text(
            """
            SELECT * FROM user_data WHERE username = :username
            """
        )
        result = await self.session.execute(stmt, {"username": username})
        return result.mappings().first()

    async def get_user_by_email(self, email: str):
        stmt = text(
            """
            SELECT * FROM user_data WHERE email = :email
            """
        )
        result = await self.session.execute(stmt, {"email": email})
        return result.mappings().first()

    async def get_user_by_id(self, user_id: str):
        stmt = text(
            """
            SELECT * FROM user_data WHERE userid = :user_id
            """
        )

        result = await self.session.execute(stmt, {"user_id": user_id})

        return result.mappings().first()

    async def get_all_users(self):
        stmt = text(
            """
            SELECT * FROM user_data
            """
        )
        result = await self.session.execute(stmt)
        return result.mappings().all()

    async def update_user(self, user_id: str, user_update: UserUpdate):
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            return user

        if "password" in update_data:
            update_data["password"] = hash_password(update_data["password"])
            update_data["token_version"] = int(user.get("token_version", 0)) + 1

        update_data = {
            key: value.value if hasattr(value, "value") else value
            for key, value in update_data.items()
        }

        set_clause = ", ".join(f"{key} = :{key}" for key in update_data.keys())
        stmt = text(
            f"""
            UPDATE user_data
            SET {set_clause}
            WHERE userid = :user_id
            """
        )
        params = {**update_data, "user_id": user_id}

        try:
            await self.session.execute(stmt, params)
            await self.session.commit()
            return await self.get_user_by_id(user_id)
        except IntegrityError:
            await self.session.rollback()
            raise

    async def delete_user(self, user_id: str):
        stmt = text(
            """
            DELETE FROM user_data
            WHERE userid = :user_id
            RETURNING userid
            """
        )
        result = await self.session.execute(stmt, {"user_id": user_id})
        await self.session.commit()
        return result.scalar_one_or_none() is not None

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        stored_password = user["password"]
        if not verify_password(current_password, stored_password):
            raise HTTPException(status_code=400, detail="Current password is invalid")

        if verify_password(new_password, stored_password):
            raise HTTPException(
                status_code=400,
                detail="New password must be different from current password",
            )

        hashed = hash_password(new_password)
        stmt = text(
            """
            UPDATE user_data
            SET password = :password,
                token_version = token_version + 1
            WHERE userid = :user_id
            """
        )
        await self.session.execute(stmt, {"password": hashed, "user_id": user_id})
        await self.session.commit()
        return True
