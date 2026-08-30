from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from utils.deps import (
    get_session,
    get_current_user,
    get_optional_current_user,
)
from services.hydroponic_service import HydroponicService
from schemas.hydroponic import (
    HydroponicDashboardOut,
    HydroponicDataPlant,
    HydroponicDataEnvironment,
    HydroponicDataActuator,
    HydroponicControlResult,
    ResponseList,
)
from schemas.user import UserOut
from uuid import uuid4
from utils.manager import manager
from utils.aggregator import aggregator
from utils.deps import require_role
from utils.converter import _parse_datetime_input
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hydroponics", tags=["Hydroponics"])

templates = Jinja2Templates(directory="./templates")

DEVICE_CONFIG = {
    "sensor-data": {
        "role": "plant",
        "room": "hydroponics",
        "model": HydroponicDataPlant,
    },
    "environment-data": {
        "role": "environment",
        "room": "hydroponics",
        "model": HydroponicDataEnvironment,
    },
    "actuator-data": {
        "role": "actuator",
        "room": "hydroponics",
        "model": HydroponicDataActuator,
    },
    "web-client": {
        "role": "web-client",
        "room": "hydroponics",
        "model": None,
    },
}


@router.get(
    "/data/latest",
    response_model=HydroponicDashboardOut | None,
    status_code=200,
    operation_id="getLatestHydroponicData",
)
async def get_latest_hydroponic_data(
    session: AsyncSession = Depends(get_session),
) -> HydroponicDashboardOut | None:
    service = HydroponicService(session)
    data = await service.get_latest_data()

    if data is None:
        return Response(status_code=204)

    return HydroponicDashboardOut.model_validate(data)


@router.get(
    "/data/{parameter}",
    response_model=ResponseList[HydroponicDashboardOut] | ResponseList,
    response_model_exclude_none=True,
    status_code=200,
    operation_id="getSpecificHydroponicData",
)
async def get_specific_hydroponic_data(
    parameter: str,
    page: int = 1,
    limit: int = 25,
    start_date: str | None = None,
    end_date: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: UserOut = Depends(get_current_user),
):
    require_role(current_user, {"admin", "superadmin"})
    service = HydroponicService(session)
    try:
        return await service.get_specific_data(
            parameter, page, limit, start_date, end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/data",
    response_model=ResponseList,
    status_code=200,
    operation_id="getHydroponicData",
)
async def get_hydroponic_data(
    page: int = 1,
    limit: int = 25,
    start_date: str | None = None,
    end_date: str | None = None,
    current_user: UserOut = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    require_role(current_user, {"user", "admin", "superadmin"})
    service = HydroponicService(session)
    return await service.get_all_data(page, limit, start_date, end_date)


@router.get(
    "/public",
    response_model=ResponseList,
    status_code=200,
    operation_id="getPublicHydroponicData",
)
async def get_public_hydroponic_data(
    page: int = 1,
    limit: int = 25,
    start_date: str | None = None,
    end_date: str | None = None,
    current_user: UserOut | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Endpoint publik untuk mendapatkan data hidroponik terbaru tanpa autentikasi."""
    service = HydroponicService(session)

    limit = min(limit, 500)
    if start_date and end_date:
        start_dt = _parse_datetime_input(start_date)[0]
        end_dt = _parse_datetime_input(end_date)[0]
        if end_dt - start_dt > timedelta(days=7) and (
            current_user is None or current_user.role not in {"admin", "superadmin"}
        ):
            raise HTTPException(
                status_code=400,
                detail="Date range cannot exceed 7 days for public endpoint",
            )

    return await service.get_all_data(page, limit, start_date, end_date)


@router.post(
    "/control",
    response_model=HydroponicControlResult,
    status_code=200,
    operation_id="controlHydroponicActuators",
)
async def control_hydroponic_actuators(
    command: HydroponicDataActuator,
    transport: str = "websocket",
    current_user: UserOut = Depends(get_current_user),
) -> HydroponicControlResult:
    require_role(current_user, {"admin", "superadmin"})
    if transport not in {"websocket", "coap"}:
        raise HTTPException(
            status_code=400,
            detail="transport must be either 'websocket' or 'coap'",
        )

    command_id = f"dashboard-{uuid4()}"
    command_payload = command.model_dump()

    if transport == "coap":
        import json
        from routes.coap_handler import HydroponicCoAPResource

        aggregator.update_actuator_state(command_payload)

        actuator_res = HydroponicCoAPResource._instances.get("actuator")
        if actuator_res:
            actuator_res.latest_state = json.dumps(command_payload).encode("utf-8")
            actuator_res.updated_state()
            logging.getLogger(__name__).info(
                f"[CoAP Debug] Mengirim notifikasi Observe ke aktuator: {command_payload}"
            )
            confirmed = True
        else:
            confirmed = False

        return HydroponicControlResult(
            **command_payload,
            command_id=command_id,
            confirmed=confirmed,
        )

    logger.info(f"Received control command: {command_payload}")
    await manager.send_to_room(
        room="hydroponics",
        role="actuator",
        message={
            "type": "command",
            "command_id": command_id,
            "payload": command_payload,
        },
    )

    return HydroponicControlResult(
        **command_payload,
        command_id=command_id,
        confirmed=True,
    )


@router.websocket("/ws/{device_type}")
async def hydroponic_data_websocket(device_type: str, websocket: WebSocket):
    """WebSocket endpoint untuk menerima data hidroponik secara real-time.

    Receive loop deliberately avoids blocking work (DB, profile fetches,
    broadcast). It validates, buffers via the aggregator, and acks fast.
    Background pipeline workers handle persistence and fan-out.
    """
    config = DEVICE_CONFIG.get(device_type)
    if not config:
        await websocket.close(code=4000, reason="Unknown device type")
        return

    session_id = str(uuid4())
    await websocket.accept()

    try:
        register = await websocket.receive_json()
        physical_id = register.get("physical_id", "unknown_device")
    except WebSocketDisconnect:
        logger.info(f"Client {session_id} disconnected before registration")
        return
    except Exception as exc:
        logger.warning(f"Invalid registration data from {session_id}: {exc}")
        try:
            await websocket.close(code=4001, reason="Invalid registration data")
        except RuntimeError:
            pass
        return

    role = config["role"]
    room = config["room"]
    validator_model = config["model"]

    await manager.connect(
        room=room, role=role, client_id=session_id, websocket=websocket
    )

    logger.info(
        f"{role.capitalize()}: {physical_id} connected with session ID: {session_id}"
    )

    try:
        while True:
            raw = await websocket.receive()
            if raw["type"] == "websocket.disconnect":
                raise WebSocketDisconnect()
            if raw["type"] != "websocket.receive":
                continue

            try:
                if "text" in raw:
                    import json

                    data = json.loads(raw["text"])
                elif "bytes" in raw:
                    import json

                    data = json.loads(raw["bytes"].decode("utf-8"))
                else:
                    continue
            except Exception:
                logger.warning(
                    "[WS %s] Invalid frame from %s; sending error ack.",
                    session_id,
                    physical_id,
                )
                try:
                    await websocket.send_json(
                        {
                            "status": "error",
                            "reason": "invalid_frame",
                        }
                    )
                except Exception:
                    pass
                continue

            try:
                await websocket.send_json(
                    {
                        "status": "ack",
                        "device_type": device_type,
                    }
                )
            except Exception:
                pass

            if validator_model:
                try:
                    validated_data = validator_model.model_validate(data)
                except Exception as exc:
                    logger.warning(
                        "[WS %s] Schema validation failed for %s/%s: %s",
                        session_id,
                        physical_id,
                        role,
                        exc,
                    )
                    continue

                buffered = await aggregator.gather_data(
                    source=role,
                    data=validated_data.model_dump(),
                )
                if not buffered:
                    logger.debug(
                        "[WS %s] Packet from %s/%s not buffered (rate-limited or ring full).",
                        session_id,
                        physical_id,
                        role,
                    )
            else:
                await manager.send_to_room(
                    room=room,
                    role="actuator",
                    message={"type": "command", "payload": data},
                )

    except WebSocketDisconnect:
        await manager.disconnect(room=room, role=role, client_id=session_id)
        logger.info("Client %s disconnected", session_id)

    except Exception:
        await manager.disconnect(room=room, role=role, client_id=session_id)
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass
        logger.exception(
            "[WebSocket] Unhandled error for client %s (role=%s)", session_id, role
        )


@router.get("/test-sensor-data", response_class=HTMLResponse)
async def test_sensor_data(request: Request):
    """Endpoint untuk menguji WebSocket sensor data hidroponik."""
    return templates.TemplateResponse("test_ws_sensor_data.html", {"request": request})
