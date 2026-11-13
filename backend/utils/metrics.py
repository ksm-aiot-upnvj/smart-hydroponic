"""Prometheus application metrics (audit finding M-1).

Deliberately low-cardinality: labels are never user ids, device ids, raw error
messages, or arbitrary request paths. The only label values used anywhere are
fixed, bounded sets defined here or by the calling module's device roles.

These counters describe *failure* signals that were previously only visible in
container logs, so an operator or an alert rule can react to them.
"""

from prometheus_client import Counter, Gauge, generate_latest

SNAPSHOT_PERSISTENCE = Counter(
    "hydroponic_snapshot_persistence_total",
    "Snapshot persistence attempts by outcome.",
    ["result"],  # success | failure
)

SENSOR_REJECTED = Counter(
    "hydroponic_sensor_payload_rejected_total",
    "Sensor payloads rejected before ingestion.",
    ["role", "reason"],
)

AGGREGATOR_DROPS = Counter(
    "hydroponic_aggregator_drops_total",
    "Packets or snapshots dropped inside the aggregator, by reason.",
    ["reason"],  # bounded set defined by the aggregator call sites
)

BROADCAST_FAILURES = Counter(
    "hydroponic_broadcast_failures_total",
    "WebSocket broadcast problems.",
    ["role", "kind"],  # kind: error | dropped
)

ACTUATOR_COMMANDS = Counter(
    "hydroponic_actuator_commands_total",
    "Manual actuator control requests by transport and delivery outcome.",
    ["transport", "outcome"],
)

AUTOMATION_DEGRADED = Gauge(
    "hydroponic_automation_degraded",
    "1 when automatic actuator decisions are suspended because the nutrition "
    "profile could not be resolved, 0 otherwise.",
)

DATABASE_READY = Gauge(
    "hydroponic_database_ready",
    "1 when the readiness probe can reach PostgreSQL, 0 otherwise.",
)


def render_metrics() -> bytes:
    """Render the Prometheus text exposition format."""
    return generate_latest()
