from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST
from sqlalchemy import text
from config.db import engine
from utils.templates import templates
import tomllib
from pathlib import Path
from routes.user_routes import router as user_router
from routes.hydroponic_routes import router as hydroponic_router
from routes.nutrition_routes import router as nutrition_router
from routes.log_routes import router as log_router
from config.config import settings


import aiocoap
import aiocoap.resource as resource
from contextlib import asynccontextmanager
from routes.coap_handler import HydroponicCoAPResource
from utils.aggregator import aggregator
from utils.pipeline import SnapshotPipeline, _NUM_WORKERS
from utils.metrics import DATABASE_READY, render_metrics
import logging
import colorlog

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
)
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)

logging.getLogger("coap-server").setLevel(logging.WARNING)
logging.getLogger("aiocoap").setLevel(logging.WARNING)

# Last-resort version shown in the OpenAPI document when `pyproject.toml` cannot
# be read. Keep it in sync with `backend/pyproject.toml`; a mismatch is reported
# by the warning in get_project_version().
FALLBACK_PROJECT_VERSION = "1.5.0"


def get_project_version() -> str:
    """Read the API version from `backend/pyproject.toml`.

    The fallback is deliberate and harmless: the version is only used for the
    OpenAPI document (`FastAPI(version=...)`), so a missing or malformed
    `pyproject.toml` must not prevent the API from starting. It is never
    silent - the exception is logged as a warning - so a stale value in
    `/docs` or the generated clients is traceable to this message instead of
    being mistaken for a real release version.
    """
    try:
        pyproject_path = Path(__file__).parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        return pyproject_data["project"]["version"]
    except Exception:
        logger.warning(
            "Could not read the version from %s; falling back to %s for the "
            "OpenAPI document. The reported API version may not match the "
            "running release.",
            Path(__file__).parent / "pyproject.toml",
            FALLBACK_PROJECT_VERSION,
            exc_info=True,
        )
        return FALLBACK_PROJECT_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting real-time monitoring pipeline...")

    aggregator.start_background_tasks()

    pipeline = SnapshotPipeline(aggregator=aggregator, room="hydroponics")
    pipeline.start()
    app.state.snapshot_pipeline = pipeline

    logger.info("Starting CoAP server...")

    root = resource.Site()

    root.add_resource(
        ["coap", "hydroponics", "plant"],
        HydroponicCoAPResource(
            role="plant",
            aggregator=aggregator,
        ),
    )
    root.add_resource(
        ["coap", "hydroponics", "environment"],
        HydroponicCoAPResource(
            role="environment",
            aggregator=aggregator,
        ),
    )
    root.add_resource(
        ["coap", "hydroponics", "actuator"],
        HydroponicCoAPResource(
            role="actuator",
            aggregator=aggregator,
        ),
    )

    coap_context = await aiocoap.Context.create_server_context(
        root, bind=(settings.COAP_HOST, 8683)
    )

    logger.info(
        "Pipeline ready: aggregator drain-loop + %d snapshot workers running.",
        _NUM_WORKERS,
    )

    yield

    logger.info("Shutting down real-time monitoring pipeline...")

    await coap_context.shutdown()

    await pipeline.stop()
    await aggregator.stop_background_tasks()

    logger.info("Pipeline shutdown complete.")


app = FastAPI(
    title="Smart Hydroponic API",
    version=get_project_version(),
    root_path="/smart-hydroponic/api/v2",
    redoc_url=None,
    lifespan=lifespan,
    servers=[
        {
            "url": "http://localhost:8000/smart-hydroponic/api/v2",
            "description": "Local Development Server",
        },
    ],
)

cors_origins = settings.cors_allow_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Browsers reject "Access-Control-Allow-Origin: *" together with
    # credentials, so credentials are only enabled for an explicit origin list.
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(hydroponic_router)
app.include_router(nutrition_router)
app.include_router(log_router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Liveness probe: the process is up and serving HTTP.

    Deliberately independent of PostgreSQL: a database outage must not make the
    container look dead, otherwise the orchestrator would kill and restart a
    perfectly healthy process instead of surfacing the dependency problem.
    """
    return {"status": "healthy"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe: the API can serve requests that require its dependencies.

    Performs a lightweight ``SELECT 1`` against the configured database (the
    same engine used by the request path, so the bundled and external database
    topologies are both covered). Returns HTTP 503 when the database is
    unreachable. The response never contains connection strings or credentials.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        DATABASE_READY.set(0)
        logger.exception("[Health] Readiness probe failed: database unreachable.")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "checks": {"database": "unreachable"},
            },
        )

    DATABASE_READY.set(1)
    return {"status": "ready", "checks": {"database": "ok"}}


@app.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint for the application metrics (audit M-1).

    Plain-text exposition format. Unauthenticated on purpose: it exposes only
    low-cardinality counters/gauges (no user ids, device ids, or secrets) and
    is meant to be reachable from the monitoring network, not the public
    internet.
    """
    return Response(content=render_metrics(), media_type=CONTENT_TYPE_LATEST)
