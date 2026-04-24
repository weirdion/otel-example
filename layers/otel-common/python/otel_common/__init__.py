"""
OTel Common - Shared OpenTelemetry instrumentation for Lambda functions.

This layer provides:
- Pre-configured tracer with Kinesis exporter
- Standard attribute helpers for user/org context
- Span utilities for consistent instrumentation
"""

from otel_common.telemetry import (
    init_telemetry,
    get_tracer,
    flush_telemetry,
)
from otel_common.attributes import (
    UserContext,
    ActionAttributes,
    set_user_context,
    set_action_attributes,
)
from otel_common.exporters import KinesisSpanExporter

__all__ = [
    # Telemetry setup
    "init_telemetry",
    "get_tracer",
    "flush_telemetry",
    # Attributes
    "UserContext",
    "ActionAttributes",
    "set_user_context",
    "set_action_attributes",
    # Exporters
    "KinesisSpanExporter",
]

__version__ = "0.1.0"
