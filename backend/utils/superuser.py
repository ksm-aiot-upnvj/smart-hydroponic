import asyncio
import logging

from sqlalchemy import text

from config.config import settings
from config.db import Session
from models.user import User
from schemas.user import UserRole
from utils.security import hash_password


logger = logging.getLogger(__name__)


async def create_superuser():
    logger.info("Create Superuser Account")
    username = settings.SUPERUSER_USERNAME
    email = settings.SUPERUSER_EMAIL
    password = settings.SUPERUSER_PASSWORD
    role = UserRole.SUPERADMIN.value

    if not username or not password:
        # A blank credential is a configuration error. Exiting non-zero makes
        # entrypoint.sh (`set -e`) abort startup instead of booting an API with
        # no usable administrator account.
        raise RuntimeError(
            "SUPERUSER_USERNAME and SUPERUSER_PASSWORD must both be set; "
            "cannot bootstrap the superuser account."
        )

    hashed_password = hash_password(password)
    async with Session() as session:
        async with session.begin():
            existing_user = await session.execute(
                text("SELECT * FROM user_data WHERE username = :username"),
                {"username": username},
            )
            if existing_user.first():
                logger.info("Superuser '%s' already exists; nothing to do.", username)
                return

            new_user = User(
                username=username,
                email=email,
                password=hashed_password,
                role=role,
                is_superuser=True,
            )
            session.add(new_user)
            await session.commit()

    logger.info(f"Superuser '{username}' created successfully.")


if __name__ == "__main__":
    asyncio.run(create_superuser())
