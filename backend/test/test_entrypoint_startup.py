"""Bounded database wait in ``backend/entrypoint.sh`` (M-2).

The script is executed with a stub ``python`` placed first on ``PATH`` so the
behaviour can be verified without a real database or interpreter:

* an unreachable database must abort startup with a non-zero exit status and
  never reach the migration step;
* a reachable database must let startup proceed and hand control to the
  container command.

Skipped when no POSIX ``sh`` is available.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENTRYPOINT = BACKEND_DIR / "entrypoint.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("sh") is None,
    reason="requires a POSIX sh to execute entrypoint.sh",
)


def _write_stub_python(directory: Path, exit_code: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    stub = directory / "python"
    stub.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)


def _run_entrypoint(stub_dir: Path):
    env = {
        **os.environ,
        "PATH": f"{stub_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "DB_STARTUP_MAX_ATTEMPTS": "2",
        "DB_STARTUP_RETRY_INTERVAL": "0",
    }
    return subprocess.run(
        ["sh", ENTRYPOINT.name, "echo", "container-command-ran"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_unreachable_database_aborts_with_non_zero_exit(tmp_path):
    stub_dir = tmp_path / "bin"
    _write_stub_python(stub_dir, exit_code=1)

    result = _run_entrypoint(stub_dir)

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "Aborting startup" in combined
    # Startup must not silently continue into migrations.
    assert "Running migrations" not in result.stdout
    assert "container-command-ran" not in combined


def test_reachable_database_proceeds_to_container_command(tmp_path):
    stub_dir = tmp_path / "bin"
    _write_stub_python(stub_dir, exit_code=0)

    result = _run_entrypoint(stub_dir)

    assert result.returncode == 0
    assert "Database is reachable." in result.stdout
    assert "Running migrations..." in result.stdout
    assert "container-command-ran" in result.stdout
