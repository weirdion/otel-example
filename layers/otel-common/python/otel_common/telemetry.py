"""
Telemetry initialization and utilities.

Provides functions to initialize the OTel SDK with appropriate
exporters for Lambda environments.
"""

import logging
import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

from otel_common.exporters import KinesisSpanExporter

logger = logging.getLogger(__name__)

_tracer_provider: Optional[TracerProvider] = None
_kinesis_exporter: Optional[KinesisSpanExporter] = None


def init_telemetry(
    service_name: str | None = None,
    service_version: str = "1.0.0",
    use_batch_processor: bool = False,
) -> TracerProvider:
    """
    Initialize OpenTelemetry with Kinesis exporter.

    Should be called once at Lambda cold start (outside the handler).

    Args:
        service_name: Service name for resource attributes.
                      Defaults to POWERTOOLS_SERVICE_NAME env var.
        service_version: Service version for resource attributes.
        use_batch_processor: Use BatchSpanProcessor instead of SimpleSpanProcessor.
                             SimpleSpanProcessor is better for Lambda (immediate export).

    Returns:
        The configured TracerProvider.
    """
    global _tracer_provider, _kinesis_exporter

    if _tracer_provider is not None:
        return _tracer_provider

    # Determine service name
    svc_name = service_name or os.environ.get("POWERTOOLS_SERVICE_NAME", "unknown")

    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: svc_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.environ.get("ENVIRONMENT", "dev"),
        "cloud.provider": "aws",
        "cloud.platform": "aws_lambda",
        "faas.name": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "unknown"),
        "faas.version": os.environ.get("AWS_LAMBDA_FUNCTION_VERSION", "$LATEST"),
    })

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Create Kinesis exporter
    try:
        _kinesis_exporter = KinesisSpanExporter()

        # Use SimpleSpanProcessor for Lambda (immediate export before timeout)
        # BatchSpanProcessor can lose spans if Lambda freezes before flush
        if use_batch_processor:
            processor = BatchSpanProcessor(
                _kinesis_exporter,
                max_queue_size=256,
                max_export_batch_size=64,
                schedule_delay_millis=1000,
            )
        else:
            processor = SimpleSpanProcessor(_kinesis_exporter)

        _tracer_provider.add_span_processor(processor)
        logger.info("OTel telemetry initialized with Kinesis exporter")

    except ValueError as e:
        # Kinesis not configured - log warning but continue
        logger.warning("Kinesis exporter not configured: %s", e)

    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    return _tracer_provider


def get_tracer(name: str | None = None) -> trace.Tracer:
    """
    Get a tracer instance.

    Initializes telemetry if not already done.

    Args:
        name: Tracer name. Defaults to POWERTOOLS_SERVICE_NAME.

    Returns:
        A Tracer instance.
    """
    if _tracer_provider is None:
        init_telemetry()

    tracer_name = name or os.environ.get("POWERTOOLS_SERVICE_NAME", "otel-demo")
    return trace.get_tracer(tracer_name)


def flush_telemetry(timeout_millis: int = 5000) -> bool:
    """
    Force flush all pending spans.

    Should be called at the end of each Lambda invocation to ensure
    spans are exported before the function freezes.

    Args:
        timeout_millis: Maximum time to wait for flush.

    Returns:
        True if flush succeeded, False otherwise.
    """
    if _tracer_provider is None:
        return True

    try:
        return _tracer_provider.force_flush(timeout_millis)
    except Exception as e:
        logger.warning("Failed to flush telemetry: %s", e)
        return False


def shutdown_telemetry() -> None:
    """
    Shutdown the telemetry system.

    Should be called when the Lambda execution environment is terminating.
    In practice, this is rarely needed in Lambda.
    """
    global _tracer_provider, _kinesis_exporter

    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None

    if _kinesis_exporter is not None:
        _kinesis_exporter.shutdown()
        _kinesis_exporter = None
