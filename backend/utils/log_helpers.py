import logging

logger = logging.getLogger(__name__)


async def best_effort_log(
    *,
    event_type: str,
    severity: str,
    description: str,
    userid: str | None = None,
    data_ref: str | None = None,
) -> None:
    """Fire-and-forget structured log write; never raises into the caller.

    Opens its own short-lived DB session so callers (the CoAP handler, the
    aggregator and the snapshot pipeline) do not need to manage one. Any
    failure is logged and swallowed: a lost log entry must never break data
    ingestion or persistence.
    """
    try:
        from utils.deps import get_db_session
        from services.log_service import LogService

        async with get_db_session() as session:
            service = LogService(session)
            await service.write_log(
                event_type=event_type,
                severity=severity,
                description=description,
                userid=userid,
                data_ref=data_ref,
            )
    except Exception:
        logger.exception("Failed to write log entry: %s", description)
