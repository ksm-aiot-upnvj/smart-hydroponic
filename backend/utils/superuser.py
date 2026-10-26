import asyncio
import logging

import bcrypt
from sqlalchemy import text

from config.config import settings
from config.db import Session
from models.user import User
from schemas.user import UserRole


logger = logging.getLogger(__name__)


async def create_superuser():
    logger.info("Create Superuser Account")
    username = settings.SUPERUSER_USERNAME
    email = settings.SUPERUSER_EMAIL
    password = settings.SUPERUSER_PASSWORD
    role = UserRole.SUPERADMIN.value

    if not username or not password:
        logger.error("Missing environment variables for superuser creation.")
        return

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    async with Session() as session:
        async with session.begin():
            existing_user = await session.execute(
                text("SELECT * FROM user_data WHERE username = :username"),
                {"username": username},
            )
            if existing_user.first():
                logger.error("Username already exists.")
                return

            new_user = User(
                username=username,
                email=email,
                password=hashed_password.decode("utf-8"),
                role=role,
                is_superuser=True,
            )
            session.add(new_user)
            await session.commit()

    logger.info(f"Superuser '{username}' created successfully.")


if __name__ == "__main__":
    asyncio.run(create_superuser())
