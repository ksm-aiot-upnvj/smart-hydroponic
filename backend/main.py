from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from utils.deps import get_session
import tomllib
from pathlib import Path
from routes.user_routes import router as user_router
from routes.hydroponic_routes import router as hydroponic_router
from routes.nutrition_routes import router as nutrition_router


import aiocoap
import aiocoap.resource as resource
from contextlib import asynccontextmanager
from routes.coap_handler import HydroponicCoAPResource
from utils.aggregator import aggregator
from utils.pipeline import SnapshotPipeline
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


def get_project_version():
    try:
        pyproject_path = Path(__file__).parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
            return pyproject_data["project"].get("version", "2.0.0")
    except Exception:
        return "2.0.0"


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

    import os

    coap_host = os.getenv("COAP_HOST", "127.0.0.1")
    coap_context = await aiocoap.Context.create_server_context(
        root, bind=(coap_host, 8683)
    )

    logger.info(
        "Pipeline ready: aggregator drain-loop + %d snapshot workers running.",
        2,
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

templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(hydroponic_router)
app.include_router(nutrition_router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/db-test")
async def db_test(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("SELECT 1"))
    return {"result": result.scalar()}
