"""Sovereign Observability Core
Provides decoupling from low-level telemetry clients, fulfilling SOLID principle
of single responsibility for backend metrics storage and reporting.
"""

import logging
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger('SovereignMetrics')

# ---------------------------------------------------------
# Metrics Declarations
# ---------------------------------------------------------

# Gauge tracking active connected clients
GAMESPY_ACTIVE_CONNECTIONS = Gauge(
    'gamespy_active_connections',
    'Number of concurrent connections',
    ['service']
)

# Counter tracking total received GameSpy protocol packet packets
GAMESPY_PACKETS_TOTAL = Counter(
    'gamespy_packets_total',
    'Cumulative count of protocol packets ingested',
    ['service', 'cmd']
)

# Counter tracking HTTP hits
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Cumulative count of HTTP hits',
    ['service', 'endpoint', 'status']
)

# Histogram monitoring underlying DB request latency
DB_QUERY_LATENCY = Histogram(
    'db_query_latency_seconds',
    'Latency tracking in seconds for Postgres and Redis storage routines',
    ['engine', 'operation']
)

# ---------------------------------------------------------
# De-coupled Interface Routines (SOLID Wrapper)
# ---------------------------------------------------------

def increment_connections(service_name: str):
    """Track active socket increase."""
    try:
        GAMESPY_ACTIVE_CONNECTIONS.labels(service=service_name).inc()
    except Exception as e:
        logger.error("Telemetry collection error: %s", e)

def decrement_connections(service_name: str):
    """Track active socket release."""
    try:
        GAMESPY_ACTIVE_CONNECTIONS.labels(service=service_name).dec()
    except Exception as e:
        logger.error("Telemetry collection error: %s", e)

def record_packet(service_name: str, command_name: str):
    """Aggregate received network protocol opcodes."""
    try:
        GAMESPY_PACKETS_TOTAL.labels(service=service_name, cmd=command_name).inc()
    except Exception as e:
        logger.error("Telemetry collection error: %s", e)

def record_http_request(service_name: str, endpoint: str, status_code: int):
    """Record endpoint hits with response mapping."""
    try:
        HTTP_REQUESTS_TOTAL.labels(
            service=service_name, 
            endpoint=endpoint, 
            status=str(status_code)
        ).inc()
    except Exception as e:
        logger.error("Telemetry collection error: %s", e)

def time_db_query(engine_type: str, operation: str):
    """Returns context manager tracking operational latency."""
    return DB_QUERY_LATENCY.labels(engine=engine_type, operation=operation).time()

def launch_metrics_endpoint(port: int):
    """Exposes prometheus metrics scraping thread."""
    try:
        logger.info("Launching centralized telemetry scraper endpoint on port %d", port)
        start_http_server(port)
    except Exception as e:
        logger.critical("CRITICAL: Failed establishing metrics scraping endpoint: %s", e)
