import json
import logging

from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider

# Trace SDK
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

# Metrics SDK
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    MetricExporter,
    MetricExportResult,
)

# Logs SDK
# LoggerProvider and LoggingHandler both live in opentelemetry.sdk._logs
# (confirmed from installed SDK source at .venv/Lib/site-packages/opentelemetry/sdk/_logs/__init__.py)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogRecordExporter

# Resource
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

# Auto-instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Bug 1 fixed: removed duplicate OTLPSpanExporter imports (grpc + http both imported
# under the same name — second silently overwrote first). Neither is needed here
# since we are using the custom JSONL file exporters.


# ══════════════════════════════════════════════════════════════════════════════
# Custom JSONL Span Exporter — writes traces to a local file
# ══════════════════════════════════════════════════════════════════════════════

class JSONLSpanExporter(SpanExporter):
    """Writes every finished span as one JSON line to a local JSONL file."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def export(self, spans):
        with open(self.filepath, "a", encoding="utf-8") as f:
            for span in spans:
                record = {
                    "trace_id":   format(span.context.trace_id, "032x"),
                    "span_id":    format(span.context.span_id, "016x"),
                    "name":       span.name,
                    "start_time": span.start_time,
                    "end_time":   span.end_time,
                    "duration_ms": (span.end_time - span.start_time) / 1_000_000,
                    "status":     span.status.status_code.name,
                    "attributes": dict(span.attributes or {}),
                    "events": [
                        {"name": e.name, "attributes": dict(e.attributes or {})}
                        for e in span.events
                    ],
                }
                f.write(json.dumps(record) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Custom JSONL Metric Exporter — writes metrics to a local file
# ══════════════════════════════════════════════════════════════════════════════

class JSONLMetricExporter(MetricExporter):
    """Writes every metric data point as one JSON line to a local JSONL file."""

    def __init__(self, filepath: str):
        # super().__init__() MUST be called — MetricExporter.__init__() sets
        # _preferred_temporality and _preferred_aggregation on the instance.
        # PeriodicExportingMetricReader reads exporter._preferred_temporality
        # immediately in its own __init__(), so if super() is not called first
        # Python raises AttributeError before the app even starts.
        super().__init__()
        self.filepath = filepath

    def export(self, metrics_data, timeout_millis: int = 10_000) -> MetricExportResult:
        with open(self.filepath, "a", encoding="utf-8") as f:
            # MetricsData structure: ResourceMetrics → ScopeMetrics → Metric → DataPoints
            for resource_metric in metrics_data.resource_metrics:
                service_name = resource_metric.resource.attributes.get(
                    "service.name", "unknown"
                )
                for scope_metric in resource_metric.scope_metrics:
                    for metric in scope_metric.metrics:
                        data_points = (
                            metric.data.data_points
                            if hasattr(metric.data, "data_points")
                            else []
                        )
                        for point in data_points:
                            record = {
                                "service":     service_name,
                                "metric_name": metric.name,
                                "description": metric.description,
                                "attributes":  dict(point.attributes or {}),
                                # Counters expose .value, Histograms expose .sum
                                "value":       (
                                    getattr(point, "value", None)
                                    or getattr(point, "sum", None)
                                ),
                                "start_time":  point.start_time_unix_nano,
                                "time":        point.time_unix_nano,
                            }
                            f.write(json.dumps(record) + "\n")
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: int = 30_000) -> None:
        pass

    def force_flush(self, timeout_millis: int = 10_000) -> bool:
        return True


# ══════════════════════════════════════════════════════════════════════════════
# setup_telemetry — called once after the FastAPI app is created
# ══════════════════════════════════════════════════════════════════════════════

# Module-level guard — prevents setup_telemetry() running more than once.
# Uvicorn --reload spawns a reloader process AND a server process, both of
# which import app.main and call create_app() → setup_telemetry().
# Without this guard the OTel SDK emits:
#   "Overriding of current TracerProvider is not allowed"
#   "Attempting to instrument while already instrumented"
# because its own Once() flags block the second registration.
_telemetry_initialised = False


def setup_telemetry(app, engine):
    """
    Initialise all three OTel signals:
      - Traces  → written to dev_traces.jsonl
      - Metrics → written to dev_metrics.jsonl  (flushed every 60s)
      - Logs    → printed to terminal console via ConsoleLogExporter

    Auto-instruments FastAPI (HTTP spans), SQLAlchemy (DB spans),
    and Python logging (injects trace_id into every log record).
    """
    global _telemetry_initialised
    if _telemetry_initialised:
        return                          # already set up in this process — skip
    _telemetry_initialised = True

    resource = Resource.create({
        SERVICE_NAME: "todo-backend",
        "service.version": "0.1.0",
        "deployment.environment": "development",
    })

    # ── Traces ────────────────────────────────────────────────────────────────
    # Bug 3 fixed: raw string (r"...") prevents \t in \tracesandmetrics being
    # interpreted as a tab character by Python's string parser.
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            JSONLSpanExporter(
                r"C:\GCP-DataEngineering\Project_ToDo\tracesandmetrics\dev_traces.jsonl"
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ───────────────────────────────────────────────────────────────
    # Bug 4 fixed: same raw string fix applied here.
    metric_reader = PeriodicExportingMetricReader(
        JSONLMetricExporter(
            r"C:\GCP-DataEngineering\Project_ToDo\tracesandmetrics\dev_metrics.jsonl"
        ),
        export_interval_millis=60_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # ── Logs ──────────────────────────────────────────────────────────────────
    # Bug 2 fixed: the logging block was indented with TABs inside a
    # spaces-indented function — Python 3 raises TabError. All spaces now.
    # Bug 5 fixed: OTLPHandler does not exist in opentelemetry.sdk._logs.
    #              The correct bridge class is LoggingHandler from the same module.

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(ConsoleLogRecordExporter())
    )
    set_logger_provider(logger_provider)

    # Bridge: makes Python's logging.getLogger() calls flow into OTel log pipeline
    otel_log_handler = LoggingHandler(
        level=logging.DEBUG,
        logger_provider=logger_provider,
    )
    logging.getLogger().addHandler(otel_log_handler)

    # ── Auto-instrumentation ──────────────────────────────────────────────────
    # Bug 7 fixed: instrument_app() is called here — inside setup_telemetry()
    # which is called once after create_app() finishes. The call order in main.py
    # is now safe: create_app() → setup_telemetry(app) rather than being called
    # at module level where uvicorn --reload would call it multiple times.
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    LoggingInstrumentor().instrument(set_logging_format=True)
