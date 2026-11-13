"""add_system_log_columns_and_hypertable

Revision ID: 1a2b3c4d5e6f
Revises: c6b1a3f4e2d7
Create Date: 2026-08-31 10:00:00.000000

Tolerated conditions (audit finding M-7)
----------------------------------------
The TimescaleDB calls at the end of :func:`upgrade` and the top of
:func:`downgrade` are optional: they turn ``logs`` into a hypertable, enable
compression on it and (un)install the compression policy. The schema change
itself - the new columns, enums, indexes and the nullable ``userid`` - does not
depend on them, so a TimescaleDB build that lacks one of these functions must
not abort the migration.

Only two exception families are tolerated, and only around those calls:

* ``ProgrammingError`` - the function/object does not exist on this server
  (PostgreSQL classes 42xxx), e.g. an older TimescaleDB without
  ``create_hypertable``/``add_compression_policy``.
* ``NotSupportedError`` - the server rejects the feature as unsupported
  (class 0Axxx), e.g. a build compiled without compression.

Both are logged as warnings at Alembic's own logger, never silently discarded,
so the operator can see that ``logs`` ended up without a hypertable and/or
compression policy. Every other error - including a failure of
``CREATE EXTENSION timescaledb`` or of the ``ALTER TABLE ... timescaledb.compress``
statement - still propagates and fails the migration loudly.
"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "c6b1a3f4e2d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# Only these two SQLAlchemy error families are tolerated around the optional
# TimescaleDB calls. See the module docstring for the exact conditions.
TOLERATED_TIMESCALE_ERRORS = (
    sa.exc.ProgrammingError,
    sa.exc.NotSupportedError,
)


EVENT_TYPE_ENUM = postgresql.ENUM(
    "system",
    "user",
    "automation",
    "sensor_anomaly",
    "actuator",
    name="log_event_type_enum",
    create_constraint=True,
)

SEVERITY_ENUM = postgresql.ENUM(
    "info",
    "warning",
    "error",
    "critical",
    name="log_severity_enum",
    create_constraint=True,
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        EVENT_TYPE_ENUM.create(bind=bind, checkfirst=True)
        SEVERITY_ENUM.create(bind=bind, checkfirst=True)

    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.alter_column(
            "userid",
            existing_type=sa.UUID(),
            nullable=True,
            existing_server_default=None,
        )
        batch_op.drop_constraint("fk_logs_userid_user_data", type_="foreignkey")
        batch_op.create_foreign_key(
            batch_op.f("fk_logs_userid_user_data"),
            "user_data",
            ["userid"],
            ["userid"],
            ondelete="SET NULL",
        )

        batch_op.alter_column(
            "description",
            existing_type=sa.VARCHAR(length=255),
            type_=sa.Text(),
            existing_nullable=False,
        )

        batch_op.add_column(
            sa.Column(
                "event_type",
                EVENT_TYPE_ENUM,
                nullable=False,
                server_default="system",
            )
        )
        batch_op.create_index(
            batch_op.f("ix_logs_event_type"), ["event_type"], unique=False
        )

        batch_op.add_column(
            sa.Column(
                "severity",
                SEVERITY_ENUM,
                nullable=False,
                server_default="info",
            )
        )
        batch_op.create_index(
            batch_op.f("ix_logs_severity"), ["severity"], unique=False
        )

        batch_op.add_column(sa.Column("data_ref", sa.UUID(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_logs_data_ref"), ["data_ref"], unique=False
        )

    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.alter_column("event_type", server_default=None)
        batch_op.alter_column("severity", server_default=None)

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        try:
            op.execute(
                "SELECT create_hypertable('logs', 'logid', if_not_exists => TRUE);"
            )
        except TOLERATED_TIMESCALE_ERRORS as exc:
            logger.warning(
                "TimescaleDB create_hypertable('logs') was not applied, so the "
                "logs table stays a regular table (no time partitioning and no "
                "compression). Reason: %s",
                exc,
            )

        op.execute(
            "ALTER TABLE logs SET (timescaledb.compress, timescaledb.compress_orderby = 'logid DESC');"
        )
        try:
            op.execute(
                "SELECT add_compression_policy('logs', compress_after => INTERVAL '7d', if_not_exists => TRUE);"
            )
        except TOLERATED_TIMESCALE_ERRORS as exc:
            logger.warning(
                "TimescaleDB add_compression_policy('logs') was not applied, so "
                "old log rows will not be compressed automatically. Reason: %s",
                exc,
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        try:
            op.execute("SELECT remove_compression_policy('logs', if_exists => TRUE);")
        except TOLERATED_TIMESCALE_ERRORS as exc:
            logger.warning(
                "TimescaleDB remove_compression_policy('logs') was not applied; "
                "a compression policy may still exist on the logs hypertable. "
                "Reason: %s",
                exc,
            )
        op.execute("ALTER TABLE logs SET (timescaledb.compress = false)")

    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_logs_data_ref"))
        batch_op.drop_column("data_ref")

        batch_op.drop_index(batch_op.f("ix_logs_severity"))
        batch_op.drop_column("severity")

        batch_op.drop_index(batch_op.f("ix_logs_event_type"))
        batch_op.drop_column("event_type")

        batch_op.alter_column(
            "description",
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=255),
            existing_nullable=False,
        )

        batch_op.drop_constraint(
            batch_op.f("fk_logs_userid_user_data"), type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_logs_userid_user_data",
            "user_data",
            ["userid"],
            ["userid"],
            ondelete="CASCADE",
        )
        batch_op.alter_column(
            "userid",
            existing_type=sa.UUID(),
            nullable=False,
        )

    if dialect == "postgresql":
        SEVERITY_ENUM.drop(bind=bind, checkfirst=True)
        EVENT_TYPE_ENUM.drop(bind=bind, checkfirst=True)
