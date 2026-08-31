import aiocoap.resource as resource
import aiocoap
import json
import logging
from schemas import (
    HydroponicDataPlant,
    HydroponicDataEnvironment,
    HydroponicDataActuator,
)
from utils.aggregator import HydroponicAggregator

logger = logging.getLogger(__name__)

COAP_CONFIG = {
    "plant": HydroponicDataPlant,
    "environment": HydroponicDataEnvironment,
    "actuator": HydroponicDataActuator,
    "web-client": None,
}


async def _coap_write_log(
    *,
    event_type: str,
    severity: str,
    description: str,
    client_ip: str,
) -> None:
    try:
        from services.log_service import LogService
        from utils.deps import get_db_session

        async with get_db_session() as session:
            svc = LogService(session)
            await svc.write_log(
                event_type=event_type,
                severity=severity,
                description=f"[{client_ip}] {description}",
            )
    except Exception:
        logger.exception(
            "[CoAP][%s] Failed to write log entry: %s", client_ip, description
        )


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
        client_ip = (
            request.remote.sockaddr[0]
            if request.remote and hasattr(request.remote, "sockaddr")
            else "Unknown"
        )
        try:
            try:
                payload = request.payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                logger.warning(
                    "[CoAP] Non-UTF-8 payload from %s/%s: %s",
                    client_ip,
                    self.role,
                    exc,
                )
                await _coap_write_log(
                    event_type="system",
                    severity="warning",
                    description=(f"Non-UTF-8 payload on {self.role}: {exc!r}"),
                    client_ip=client_ip,
                )
                return aiocoap.Message(
                    code=aiocoap.BAD_REQUEST, payload=b"Invalid payload encoding"
                )

            try:
                data_json = json.loads(payload)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "[CoAP] Invalid JSON from %s/%s: %s",
                    client_ip,
                    self.role,
                    exc,
                )
                await _coap_write_log(
                    event_type="system",
                    severity="warning",
                    description=f"Invalid JSON on {self.role}: {exc!r}",
                    client_ip=client_ip,
                )
                return aiocoap.Message(
                    code=aiocoap.BAD_REQUEST, payload=b"Invalid JSON"
                )

            logger.info(
                f"[CoAP Handler] Menerima payload dari node '{self.role}' ({client_ip}): {data_json}"
            )

            if self.validator is None:
                ack_payload = json.dumps({"status": "ack", "role": self.role}).encode(
                    "utf-8"
                )
                return aiocoap.Message(code=aiocoap.CHANGED, payload=ack_payload)

            try:
                data = self.validator.model_validate(data_json)
            except Exception as exc:
                logger.warning(
                    "[CoAP] Schema validation failed for %s/%s: %s. Payload: %s",
                    client_ip,
                    self.role,
                    exc,
                    data_json,
                )
                await _coap_write_log(
                    event_type="sensor_anomaly",
                    severity="warning",
                    description=(
                        f"Schema validation failed on {self.role}: "
                        f"{exc!r}. Keys received: {list(data_json.keys())!r}"
                    ),
                    client_ip=client_ip,
                )
                err_body = json.dumps(
                    {"status": "error", "detail": "Validation failed"}
                ).encode("utf-8")
                return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=err_body)

            logger.info(
                f"[CoAP Handler] Data dari node '{self.role}' sedang divalidasi"
            )

            buffered = await self.aggregator.gather_data(self.role, data.model_dump())

            if not buffered:
                rate_limited_body = json.dumps(
                    {"status": "dropped", "reason": "rate_limited_or_ring_full"}
                ).encode("utf-8")
                return aiocoap.Message(
                    code=aiocoap.SERVICE_UNAVAILABLE,
                    payload=rate_limited_body,
                )

            ack_payload = json.dumps(
                {
                    "status": "ack",
                    "queued": self.aggregator.process_queue.qsize(),
                }
            ).encode("utf-8")
            return aiocoap.Message(code=aiocoap.CHANGED, payload=ack_payload)

        except Exception as exc:
            logger.exception(
                "[CoAP][ERROR] Unhandled error in render_put for role='%s' (%s)",
                self.role,
                client_ip,
            )
            try:
                await _coap_write_log(
                    event_type="system",
                    severity="critical",
                    description=(f"Unhandled CoAP PUT error on {self.role}: {exc!r}"),
                    client_ip=client_ip,
                )
            except Exception:
                logger.exception(
                    "[CoAP][%s][%s] Failed to write critical log for render_put.",
                    client_ip,
                    self.role,
                )
            return aiocoap.Message(
                code=aiocoap.INTERNAL_SERVER_ERROR,
                payload=b"Internal server error",
            )
