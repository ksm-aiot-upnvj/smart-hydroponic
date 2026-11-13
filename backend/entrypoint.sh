#!/bin/sh
set -e

# Bounded database wait. The previous revision retried forever, so a
# misconfigured or unreachable database left the container "starting" instead
# of failing loudly. Both values are overridable from the environment.
DB_STARTUP_MAX_ATTEMPTS="${DB_STARTUP_MAX_ATTEMPTS:-30}"
DB_STARTUP_RETRY_INTERVAL="${DB_STARTUP_RETRY_INTERVAL:-2}"

echo "Waiting for database (max ${DB_STARTUP_MAX_ATTEMPTS} attempts, ${DB_STARTUP_RETRY_INTERVAL}s apart)..."

attempt=1
while [ "${attempt}" -le "${DB_STARTUP_MAX_ATTEMPTS}" ]; do
	if python - <<'EOF'
import asyncio
import os
import sys

import asyncpg

dsn = (
    f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}"
    f"@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
)


async def main() -> None:
    try:
        connection = await asyncpg.connect(dsn)
    except Exception as exc:
        # Sanitized on purpose: never echo the DSN or credentials.
        print(f"database connection failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)
    await connection.close()


asyncio.run(main())
EOF
	then
		echo "Database is reachable."
		break
	fi

	if [ "${attempt}" -ge "${DB_STARTUP_MAX_ATTEMPTS}" ]; then
		echo "ERROR: database still unavailable after ${DB_STARTUP_MAX_ATTEMPTS} attempts. Aborting startup." >&2
		exit 1
	fi

	echo "Database not reachable yet (attempt ${attempt}/${DB_STARTUP_MAX_ATTEMPTS}); retrying in ${DB_STARTUP_RETRY_INTERVAL}s..." >&2
	attempt=$((attempt + 1))
	sleep "${DB_STARTUP_RETRY_INTERVAL}"
done

# `set -e` makes any of the following steps abort startup on a non-zero exit.
echo "Running migrations..."
python -m alembic upgrade head

echo "Create superuser if not exists..."
python -m utils.superuser

exec "$@"
