import hashlib
import logging
import os

from agent_framework.observability import create_metric_views, create_resource, enable_instrumentation
from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, SimpleLogRecordProcessor

from app.models import Answer, Turn

LOGGER = logging.getLogger("juriscope")


def configure() -> None:
    LOGGER.setLevel(logging.INFO)
    resource = create_resource(service_name="juriscope")
    if connection_string := os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        configure_azure_monitor(
            connection_string=connection_string,
            credential=DefaultAzureCredential(),
            resource=resource,
            views=create_metric_views(),
            logger_name=LOGGER.name,
        )
        enable_instrumentation()
        return
    console = LoggerProvider(resource=resource)
    console.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogRecordExporter()))
    LOGGER.addHandler(LoggingHandler(logger_provider=console))


def user_hash(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def identify(user_id: str) -> None:
    trace.get_current_span().set_attribute("user_hash", user_hash(user_id))


def event(name: str, user_id: str, **properties: str | int | float) -> None:
    LOGGER.info(name, extra={"microsoft.custom_event.name": name, "user_hash": user_hash(user_id), **properties})


def delivered(user_id: str, turn: Turn) -> None:
    outcome = turn.outcome
    claims, dropped = (outcome.claims, outcome.dropped_claims) if isinstance(outcome, Answer) else (0, 0)
    kind = "answer" if isinstance(outcome, Answer) else outcome.reason
    measures = {"claims": claims, "dropped_claims": dropped, "cost_eur": outcome.cost_eur}
    event("AnswerDelivered", user_id, turn_id=turn.id, outcome=kind, **measures)
