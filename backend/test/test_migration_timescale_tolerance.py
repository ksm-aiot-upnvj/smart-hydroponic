"""M-7: the TimescaleDB calls in revision 1a2b3c4d5e6f must not swallow errors.

The migration used to wrap `create_hypertable`, `add_compression_policy` and
`remove_compression_policy` in a bare ``except Exception: pass``, which hid every
error - including genuine ones such as a lost connection. These tests pin the
narrowed contract:

* the tolerated error families (ProgrammingError / NotSupportedError, i.e. "this
  server has no such function or feature") are logged as warnings and let the
  migration continue, because the schema change itself does not depend on
  TimescaleDB, and
* anything else still propagates and fails the migration loudly.

The test drives `upgrade()`/`downgrade()` with a stub `alembic.op`, so it needs
no database.
"""

import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "1a2b3c4d5e6f_add_system_log_columns_and_hypertable.py"
)

# The migration logs at Alembic's own logger so operators see the warning in the
# same output as the rest of the migration run.
LOGGER_NAME = "alembic.runtime.migration"


class _StubBatchOperations:
    """Accepts every `batch_op.<something>(...)` call without doing anything."""

    def __getattr__(self, _name: str) -> Any:
        def _noop(*_args: Any, **_kwargs: Any) -> None:
            return None

        return _noop


class _StubBatchContext:
    def __enter__(self) -> _StubBatchOperations:
        return _StubBatchOperations()

    def __exit__(self, *_exc_info: Any) -> bool:
        return False


class _StubBind:
    class dialect:  # noqa: N801 - mirrors SQLAlchemy's attribute access
        name = "postgresql"


class _StubOp:
    """Minimal stand-in for `alembic.op`.

    `behaviour` maps a substring of a statement to the error that statement must
    raise; every statement that matches nothing simply succeeds.
    """

    def __init__(self, behaviour: dict[str, BaseException] | None = None) -> None:
        self._behaviour = behaviour or {}
        self.executed: list[str] = []

    def get_bind(self) -> _StubBind:
        return _StubBind()

    def batch_alter_table(self, *_args: Any, **_kwargs: Any) -> _StubBatchContext:
        return _StubBatchContext()

    def execute(self, statement: Any) -> None:
        sql = str(statement)
        self.executed.append(sql)
        for fragment, error in self._behaviour.items():
            if fragment in sql:
                raise error


def _load_migration(
    monkeypatch: pytest.MonkeyPatch,
    *,
    behaviour: dict[str, BaseException] | None = None,
) -> ModuleType:
    """Load the revision in isolation and install the stub `op`.

    The enum DDL is stubbed at the class level (not by replacing the module
    globals) because the revision also passes the real `postgresql.ENUM` objects
    to `sa.Column` as column types.
    """
    spec = importlib.util.spec_from_file_location(
        "migration_1a2b3c4d5e6f", MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(postgresql.ENUM, "create", lambda self, **_: None)
    monkeypatch.setattr(postgresql.ENUM, "drop", lambda self, **_: None)
    module.op = _StubOp(behaviour)
    return module


def _programming_error(message: str) -> sa.exc.ProgrammingError:
    return sa.exc.ProgrammingError("SELECT ...", {}, Exception(message))


def _messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == LOGGER_NAME]


def test_missing_timescale_functions_are_logged_not_swallowed(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration(
        monkeypatch,
        behaviour={
            "create_hypertable": _programming_error(
                "function create_hypertable(...) does not exist"
            ),
            "add_compression_policy": _programming_error(
                "function add_compression_policy(...) does not exist"
            ),
        },
    )

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        module.upgrade()

    warnings = _messages(caplog)
    assert any("create_hypertable" in message for message in warnings)
    assert any("add_compression_policy" in message for message in warnings)

    # The schema migration still completed and kept going past the failures.
    assert any(
        "ALTER TABLE logs SET (timescaledb.compress" in statement
        for statement in module.op.executed
    )


def test_downgrade_logs_a_missing_compression_policy(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration(
        monkeypatch,
        behaviour={
            "remove_compression_policy": _programming_error(
                "function remove_compression_policy(...) does not exist"
            )
        },
    )

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        module.downgrade()

    assert any("remove_compression_policy" in message for message in _messages(caplog))


def test_connection_failure_during_upgrade_still_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only "no such function/feature" is tolerated; an unrelated error is not."""
    module = _load_migration(
        monkeypatch,
        behaviour={
            "create_hypertable": sa.exc.OperationalError(
                "SELECT ...", {}, Exception("server closed the connection")
            )
        },
    )

    with pytest.raises(sa.exc.OperationalError):
        module.upgrade()


def test_compression_statement_failure_is_not_tolerated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ALTER TABLE ... timescaledb.compress` is essential, so it fails loudly."""
    module = _load_migration(
        monkeypatch,
        behaviour={
            "SET (timescaledb.compress": _programming_error(
                'unrecognized parameter "timescaledb.compress"'
            )
        },
    )

    with pytest.raises(sa.exc.ProgrammingError):
        module.upgrade()
