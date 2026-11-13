import logging

logger = logging.getLogger(__name__)

# Deliberate exception to the Fail Fast / Fail Loud principle (audit finding
# M-6). Writing a row into the database-backed `logs` table is an *optional*
# side effect of ingesting and persisting sensor data. Letting it fail the
# caller would mean a logging outage stops sensor ingestion, which is worse
# than losing a log entry: the measurements themselves are the valuable data.
#
# The failure is never hidden, though:
#   * the exception (with traceback) is written to the standard application
#     log, so it is visible in `docker compose logs` / journald and can be
#     alerted on, and
#   * this helper never re-enters itself: log records go to stdout through the
#     process logging handler, not back into the database sink, so a failed
#     write cannot recursively trigger another failing write.
#
# Everything else in the ingestion path fails loudly.


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
    failure is logged to the standard application log and swallowed: a lost
    log entry must never break data ingestion or persistence.

    See the module docstring for why this one operation is allowed to fail
    quietly, and why that cannot hide a failure or recurse.
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
