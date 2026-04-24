"""
Custom OTel exporters for the demo.

Provides a Kinesis exporter that sends spans to a Kinesis Data Stream
for fan-out to multiple consumers (S3, New Relic, etc.).
"""

import json
import logging
import os
from typing import Sequence

import boto3
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


class KinesisSpanExporter(SpanExporter):
    """
    Export spans to Kinesis Data Stream.

    Spans are serialized to JSON and written to Kinesis with the
    trace_id as the partition key for ordering within a trace.
    """

    def __init__(
        self,
        stream_name: str | None = None,
        region_name: str | None = None,
    ):
        """
        Initialize the Kinesis exporter.

        Args:
            stream_name: Kinesis stream name. Defaults to KINESIS_STREAM_NAME env var.
            region_name: AWS region. Defaults to AWS_REGION env var.
        """
        self.stream_name = stream_name or os.environ.get("KINESIS_STREAM_NAME")
        if not self.stream_name:
            raise ValueError(
                "stream_name must be provided or KINESIS_STREAM_NAME must be set"
            )

        region = region_name or os.environ.get("AWS_REGION", "us-east-2")
        self._client = boto3.client("kinesis", region_name=region)
        self._shutdown = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans to Kinesis."""
        if self._shutdown:
            return SpanExportResult.FAILURE

        if not spans:
            return SpanExportResult.SUCCESS

        try:
            records = []
            for span in spans:
                record = self._span_to_record(span)
                records.append({
                    "Data": json.dumps(record).encode("utf-8"),
                    "PartitionKey": record["trace_id"],
                })

            # Batch write to Kinesis (max 500 records per call)
            for i in range(0, len(records), 500):
                batch = records[i : i + 500]
                response = self._client.put_records(
                    StreamName=self.stream_name,
                    Records=batch,
                )

                failed_count = response.get("FailedRecordCount", 0)
                if failed_count > 0:
                    logger.warning(
                        "Failed to write %d/%d records to Kinesis",
                        failed_count,
                        len(batch),
                    )

            return SpanExportResult.SUCCESS

        except Exception as e:
            logger.exception("Failed to export spans to Kinesis: %s", e)
            return SpanExportResult.FAILURE

    def _span_to_record(self, span: ReadableSpan) -> dict:
        """Convert a span to a Kinesis record payload."""
        context = span.get_span_context()

        record = {
            "trace_id": format(context.trace_id, "032x"),
            "span_id": format(context.span_id, "016x"),
            "parent_span_id": (
                format(span.parent.span_id, "016x") if span.parent else None
            ),
            "name": span.name,
            "kind": span.kind.name if span.kind else None,
            "start_time_unix_nano": span.start_time,
            "end_time_unix_nano": span.end_time,
            "attributes": dict(span.attributes) if span.attributes else {},
            "status": {
                "code": span.status.status_code.name,
                "description": span.status.description,
            },
            "events": [
                {
                    "name": event.name,
                    "timestamp_unix_nano": event.timestamp,
                    "attributes": dict(event.attributes) if event.attributes else {},
                }
                for event in span.events
            ],
            "resource": (
                dict(span.resource.attributes) if span.resource else {}
            ),
        }

        return record

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        self._shutdown = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush is a no-op for Kinesis (immediate write)."""
        return True
