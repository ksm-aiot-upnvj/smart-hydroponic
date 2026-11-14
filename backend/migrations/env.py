from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# --- Load app settings
from config.config import settings
from config.db import Base

config = context.config


# Optionally override from env rather than alembic.ini
if settings.DATABASE_URL:
    # Alembic stores options in a ``configparser`` instance whose default
    # interpolation treats ``%`` as the start of a substitution escape.
    # Credentials are percent-encoded (``#`` -> ``%23``), so setting the URL
    # verbatim raises "invalid interpolation syntax". Doubling the ``%`` masks
    # it from the parser; ``get_main_option`` un-escapes it again on read.
    config.set_main_option(
        "sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%")
    )

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    # TimescaleDB commonly creates these indexes automatically for hypertables.
    # They exist in the database but are not declared in SQLAlchemy models,
    # so Alembic autogenerate would otherwise try to drop them.
    if type_ == "index" and reflected and name and name.endswith("_timestamp_idx"):
        return False
    return True


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,  # Enable type comparison
        compare_server_default=True,  # Enable server default comparison
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
