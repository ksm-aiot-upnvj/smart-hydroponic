# --- STAGE 1: THE CHEF (Build Stage) ---
FROM python:3.14-slim AS builder

ENV UV_SYSTEM_PYTHON=1 \
	PYTHONDONTWRITE_BYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential gcc curl \
	&& rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
	&& ln -s /root/.local/bin/uv /usr/local/bin/uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# --- STAGE 2: THE MODEL (Final Stage) ---
FROM python:3.14-slim AS runner

ENV APP_HOME=/app \
	PORT=8000 \
	HOST=0.0.0.0 \
	PYTHONPATH=/app

WORKDIR ${APP_HOME}

COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"


COPY . .

RUN sed -i 's/\r$//' /app/entrypoint.sh \
	&& chmod +x /app/entrypoint.sh

EXPOSE 8000

# Readiness healthcheck: the container is healthy only when the API can reach
# its database. /health stays a pure liveness probe (see backend/main.py) so a
# database outage is reported as "unhealthy" instead of killing the process.
# The startup grace period covers the bounded database wait in entrypoint.sh
# plus `alembic upgrade head` and the superuser bootstrap.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]

# Pake list format biar gampang dapet sinyal SIGTERM
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]