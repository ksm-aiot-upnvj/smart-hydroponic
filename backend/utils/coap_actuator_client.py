import asyncio
import json
from typing import Any

import aiocoap
import logging

from config.config import settings

logger = logging.getLogger(__name__)


def get_actuator_control_uri() -> str:
    """Build the ESP8266 actuator CoAP endpoint URI.

    The target is taken from the centralized ``Settings`` object
    (``COAP_ACTUATOR_HOST`` / ``COAP_ACTUATOR_PORT`` /
    ``COAP_ACTUATOR_CONTROL_PATH``) so there is a single source of truth.
    """

    host = settings.COAP_ACTUATOR_HOST
    port = settings.COAP_ACTUATOR_PORT
    path = settings.COAP_ACTUATOR_CONTROL_PATH
    return f"coap://{host}:{port}/{path}"


def get_actuator_timeout_seconds() -> float:
    return settings.COAP_ACTUATOR_TIMEOUT_SECONDS


async def send_actuator_command_coap(
    payload: dict[str, Any],
    uri: str | None = None,
) -> dict[str, Any]:
    """Send a command/forwarded snapshot to ESP8266 Actuator via CoAP."""

    target_uri = uri or get_actuator_control_uri()
    timeout_seconds = get_actuator_timeout_seconds()

    context = await aiocoap.Context.create_client_context()
    request = aiocoap.Message(
        code=aiocoap.PUT,
        payload=json.dumps(payload).encode("utf-8"),
        uri=target_uri,
    )

    try:
        logger.info(
            "[COAP_FORWARD] Sending actuator command | "
            f"URI: {target_uri} | Timeout: {timeout_seconds}s"
        )
        response = await asyncio.wait_for(
            context.request(request).response,
            timeout=timeout_seconds,
        )

        raw_payload = response.payload.decode("utf-8", errors="ignore")
        try:
            response_payload: dict[str, Any] = json.loads(raw_payload)
        except json.JSONDecodeError:
            response_payload = {"raw_payload": raw_payload}

        return {
            "confirmed": True,
            "response_code": str(response.code),
            "actuator_payload": response_payload,
        }
    except TimeoutError:
        return {
            "confirmed": False,
            "error": f"CoAP actuator request timed out after {timeout_seconds}s",
        }
    except Exception as exc:
        return {
            "confirmed": False,
            "error": str(exc),
        }
    finally:
        await context.shutdown()
