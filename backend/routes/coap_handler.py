import aiocoap.resource as resource
import aiocoap
import json
import logging
from schemas import (
    HydroponicDataPlant,
    HydroponicDataEnvironment,
    HydroponicDataActuator,
    HydroponicIn,
)
from utils.deps import get_db_session
from utils.aggregator import HydroponicAggregator
from services.hydroponic_service import HydroponicService
from services.nutrition_service import NutritionService
from utils.actuator_control import build_actuator_control_payload

logger = logging.getLogger(__name__)

COAP_CONFIG = {
    "plant": HydroponicDataPlant,
    "environment": HydroponicDataEnvironment,
    "actuator": HydroponicDataActuator,
    "web-client": None,
}


class HydroponicCoAPResource(resource.ObservableResource):
    _instances = {}

    def __init__(
        self,
        role: str,
        aggregator: HydroponicAggregator,
    ):
        super().__init__()
        self.role = role
        self.aggregator = aggregator
        self.validator = COAP_CONFIG.get(role)
        self.latest_state = b"{}"
        HydroponicCoAPResource._instances[role] = self

    async def render_get(self, request):
        client_ip = (
            request.remote.sockaddr[0]
            if request.remote and hasattr(request.remote, "sockaddr")
            else "Unknown"
        )
        if request.opt.observe == 0:
            logger.info(
                f"[CoAP Debug] Node {client_ip} berhasil mendaftar Observe ke '{self.role}'"
            )
        else:
            logger.info(
                f"[CoAP Debug] Node {client_ip} meminta GET (tanpa Observe) ke '{self.role}'"
            )
        return aiocoap.Message(payload=self.latest_state)

    async def render_put(self, request):
        try:
            payload = request.payload.decode("utf-8")
            data_json = json.loads(payload)

            logger.info(
                f"[CoAP Handler] Menerima payload dari node '{self.role}': {data_json}"
            )

            if self.validator:
                data = self.validator.model_validate(data_json)
                logger.info(
                    f"[CoAP Handler] Data dari node '{self.role}' sedang divalidasi"
                )
                snapshot = await self.aggregator.gather_data(
                    self.role, data.model_dump()
                )

                if snapshot:
                    logger.info("[CoAP Handler] Data berhasil digather")
                    snapshot_payload = snapshot.model_dump()

                    async with get_db_session() as session:
                        nutrition_service = NutritionService(session)
                        active_profile = await nutrition_service.get_active_profile()

                        actuator_payload = build_actuator_control_payload(
                            snapshot_payload, active_profile
                        )
                        snapshot_payload.update(
                            {
                                "pump_status": actuator_payload["pump_status"],
                                "light_status": actuator_payload["light_status"],
                                "automation_status": actuator_payload[
                                    "automation_status"
                                ],
                            }
                        )

                        actuator_res = HydroponicCoAPResource._instances.get("actuator")
                        if actuator_res:
                            self.aggregator.update_actuator_state(actuator_payload)
                            actuator_res.latest_state = json.dumps(
                                actuator_payload
                            ).encode("utf-8")
                            actuator_res.updated_state()

                        logger.info(f"[CoAP Handler] Data snapshot: {snapshot_payload}")

                        service = HydroponicService(session)
                        await service.add_data(
                            HydroponicIn.model_validate(snapshot_payload)
                        )

            ack_payload = json.dumps(
                {
                    "status": "ack",
                }
            ).encode("utf-8")
            return aiocoap.Message(code=aiocoap.CHANGED, payload=ack_payload)

        except Exception as e:
            logger.error(f"[COAP][ERROR] {e}")
            return aiocoap.Message(
                code=aiocoap.INTERNAL_SERVER_ERROR, payload=b"Error processing data"
            )
