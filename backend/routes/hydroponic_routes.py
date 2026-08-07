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
    get_db_session,
    get_current_user,
    get_optional_current_user,
)
from services.hydroponic_service import HydroponicService
from schemas.hydroponic import (
    HydroponicIn,
    HydroponicOut,
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
from utils.actuator_control import build_actuator_control_payload
from utils.deps import require_role
from utils.converter import _parse_datetime_input
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
import logging

from services.nutrition_service import NutritionService

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(message)s",
)
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
    response_model=ResponseList[HydroponicOut],
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
) -> ResponseList[HydroponicOut]:
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
    response_model=ResponseList[HydroponicOut],
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
) -> ResponseList[HydroponicOut]:
    require_role(current_user, {"user", "admin", "superadmin"})
    service = HydroponicService(session)
    return await service.get_all_data(page, limit, start_date, end_date)


@router.get(
    "/public",
    response_model=ResponseList[HydroponicOut],
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
) -> ResponseList[HydroponicOut]:
    """Endpoint publik untuk mendapatkan data hidroponik terbaru tanpa autentikasi."""
    service = HydroponicService(session)

    # Maksimum 500 data untuk endpoint publik
    limit = min(limit, 500)
    # Maksimum 7 hari data untuk endpoint publik
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
    """Forward dashboard commands to the actuator via WebSocket or CoAP Observe.

    The command is pushed directly to the actuator based on the requested
    transport protocol. CoAP mode is selected with `?transport=coap` and
    updates the actuator state via the CoAP Observe pattern.
    """
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

        # Perbarui state global di aggregator
        aggregator.update_actuator_state(command_payload)

        # Beritahu observer CoAP (ESP8266) tentang state baru ini
        actuator_res = HydroponicCoAPResource._instances.get("actuator")
        if actuator_res:
            actuator_res.latest_state = json.dumps(command_payload).encode("utf-8")
            actuator_res.updated_state()
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
    """WebSocket endpoint untuk menerima data hidroponik secara real-time."""
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
            data = await websocket.receive_json()

            await websocket.send_json(
                {
                    "status": "ack",
                    "device_type": device_type,
                }
            )

            if validator_model:
                validated_data = validator_model.model_validate(data)

                snapshot = await aggregator.gather_data(
                    source=role,
                    data=validated_data.model_dump(),
                )

                if snapshot:
                    snapshot_payload = snapshot.model_dump()

                    async with get_db_session() as session:
                        nutrition_service = NutritionService(session)
                        active_profile = await nutrition_service.get_active_profile()

                        actuator_message = build_actuator_control_payload(
                            snapshot_payload, active_profile
                        )
                        aggregator.update_actuator_state(actuator_message)
                        snapshot_payload.update(
                            {
                                "pump_status": actuator_message["pump_status"],
                                "light_status": actuator_message["light_status"],
                                "automation_status": actuator_message[
                                    "automation_status"
                                ],
                            }
                        )

                        service = HydroponicService(session)
                        new_data = await service.add_data(
                            HydroponicIn.model_validate(snapshot_payload)
                        )

                    logger.info(f"Snapshot created: {new_data.model_dump()}")
                    await manager.send_to_room(
                        room=room, role="web-client", message=snapshot_payload
                    )

                    await manager.send_to_room(
                        room=room,
                        role="actuator",
                        message=actuator_message,
                    )

                    import json
                    from routes.coap_handler import HydroponicCoAPResource

                    actuator_res = HydroponicCoAPResource._instances.get("actuator")
                    if actuator_res:
                        actuator_res.latest_state = json.dumps(actuator_message).encode(
                            "utf-8"
                        )
                        actuator_res.updated_state()

                    logger.info(
                        f"Snapshot created and sent to actuator clients: {actuator_message}"
                    )
            else:
                # Directly forward commands from dashboard to actuators
                await manager.send_to_room(
                    room=room,
                    role="actuator",
                    message={"type": "command", "payload": data},
                )

    except WebSocketDisconnect:
        await manager.disconnect(room=room, role=role, client_id=session_id)
        logger.info(f"Client {session_id} disconnected")

    except Exception as e:
        await manager.disconnect(room=room, role=role, client_id=session_id)
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass
        logger.error(f"Error: {e}")


@router.get("/test-sensor-data", response_class=HTMLResponse)
async def test_sensor_data(request: Request):
    """Endpoint untuk menguji WebSocket sensor data hidroponik."""
    return templates.TemplateResponse("test_ws_sensor_data.html", {"request": request})
