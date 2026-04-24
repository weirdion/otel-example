"""
New Relic Consumer Lambda Handler.

Consumes telemetry records from Kinesis and forwards them
to New Relic via the OTLP endpoint.
"""

import base64
import json
import os
from typing import Any

import boto3
import requests
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Configuration
NEWRELIC_ACCOUNT_ID = os.environ.get("NEWRELIC_ACCOUNT_ID", "")
NEWRELIC_API_KEY_PARAM = os.environ.get("NEWRELIC_API_KEY_PARAM", "")

# New Relic OTLP endpoint (US region)
# For EU, use: https://otlp.eu01.nr-data.net
NEWRELIC_OTLP_ENDPOINT = os.environ.get(
    "NEWRELIC_OTLP_ENDPOINT",
    "https://otlp.nr-data.net/v1/traces",
)

# SSM client for retrieving API key
ssm_client = boto3.client("ssm")

# Cache API key
_api_key_cache: str | None = None


def get_api_key() -> str:
    """Get New Relic API key from SSM Parameter Store."""
    global _api_key_cache

    if _api_key_cache:
        return _api_key_cache

    if not NEWRELIC_API_KEY_PARAM:
        raise ValueError("NEWRELIC_API_KEY_PARAM not configured")

    try:
        response = ssm_client.get_parameter(
            Name=NEWRELIC_API_KEY_PARAM,
            WithDecryption=True,
        )
        _api_key_cache = response["Parameter"]["Value"]
        return _api_key_cache
    except Exception as e:
        logger.exception(f"Failed to get API key from SSM: {e}")
        raise


def convert_to_otlp_format(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert our span records to OTLP JSON format.

    This is a simplified conversion - production would use
    the full OTLP protobuf schema.
    """
    spans = []

    for record in records:
        span = {
            "traceId": record.get("trace_id", ""),
            "spanId": record.get("span_id", ""),
            "parentSpanId": record.get("parent_span_id", ""),
            "name": record.get("name", "unknown"),
            "kind": _convert_span_kind(record.get("kind")),
            "startTimeUnixNano": str(record.get("start_time_unix_nano", 0)),
            "endTimeUnixNano": str(record.get("end_time_unix_nano", 0)),
            "attributes": _convert_attributes(record.get("attributes", {})),
            "status": {
                "code": _convert_status_code(
                    record.get("status", {}).get("code", "UNSET")
                ),
            },
        }

        # Add events if present
        events = record.get("events", [])
        if events:
            span["events"] = [
                {
                    "name": event.get("name", ""),
                    "timeUnixNano": str(event.get("timestamp_unix_nano", 0)),
                    "attributes": _convert_attributes(event.get("attributes", {})),
                }
                for event in events
            ]

        spans.append(span)

    # Group by resource (simplified - all spans share same resource)
    resource_attrs = records[0].get("resource", {}) if records else {}

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": _convert_attributes(resource_attrs),
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "otel-demo"},
                        "spans": spans,
                    }
                ],
            }
        ]
    }


def _convert_attributes(attrs: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert attribute dict to OTLP attribute array."""
    result = []
    for key, value in attrs.items():
        attr = {"key": key}
        if isinstance(value, bool):
            attr["value"] = {"boolValue": value}
        elif isinstance(value, int):
            attr["value"] = {"intValue": str(value)}
        elif isinstance(value, float):
            attr["value"] = {"doubleValue": value}
        elif isinstance(value, list):
            attr["value"] = {"arrayValue": {"values": [{"stringValue": str(v)} for v in value]}}
        else:
            attr["value"] = {"stringValue": str(value)}
        result.append(attr)
    return result


def _convert_span_kind(kind: str | None) -> int:
    """Convert span kind string to OTLP integer."""
    kinds = {
        "INTERNAL": 1,
        "SERVER": 2,
        "CLIENT": 3,
        "PRODUCER": 4,
        "CONSUMER": 5,
    }
    return kinds.get(kind or "INTERNAL", 1)


def _convert_status_code(code: str) -> int:
    """Convert status code string to OTLP integer."""
    codes = {
        "UNSET": 0,
        "OK": 1,
        "ERROR": 2,
    }
    return codes.get(code, 0)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Process Kinesis records and forward to New Relic.
    """
    records = event.get("Records", [])

    if not records:
        logger.info("No records to process")
        return {"statusCode": 200, "body": "No records"}

    logger.info(f"Processing {len(records)} records for New Relic")

    # Decode all records
    decoded_records = []
    for record in records:
        try:
            payload = base64.b64decode(record["kinesis"]["data"])
            data = json.loads(payload)
            decoded_records.append(data)
        except Exception as e:
            logger.warning(f"Failed to decode record: {e}")
            metrics.add_metric(
                name="RecordDecodeErrors",
                unit=MetricUnit.Count,
                value=1,
            )

    if not decoded_records:
        logger.warning("No valid records after decoding")
        return {"statusCode": 200, "body": "No valid records"}

    # Convert to OTLP format
    otlp_payload = convert_to_otlp_format(decoded_records)

    # Send to New Relic
    with tracer.provider.in_subsegment("newrelic_export") as subsegment:
        subsegment.put_annotation("record_count", len(decoded_records))

        try:
            api_key = get_api_key()

            response = requests.post(
                NEWRELIC_OTLP_ENDPOINT,
                json=otlp_payload,
                headers={
                    "Api-Key": api_key,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )

            if response.status_code >= 400:
                logger.error(
                    f"New Relic API error: {response.status_code} - {response.text}"
                )
                metrics.add_metric(
                    name="NewRelicExportErrors",
                    unit=MetricUnit.Count,
                    value=1,
                )
                # Don't raise - we don't want to retry on client errors
                if response.status_code >= 500:
                    raise Exception(f"New Relic server error: {response.status_code}")
            else:
                logger.info(
                    "Successfully exported to New Relic",
                    extra={"record_count": len(decoded_records)},
                )

        except requests.exceptions.Timeout:
            logger.error("New Relic request timed out")
            metrics.add_metric(
                name="NewRelicTimeouts",
                unit=MetricUnit.Count,
                value=1,
            )
            raise
        except Exception as e:
            logger.exception(f"Failed to export to New Relic: {e}")
            raise

    # Record metrics
    metrics.add_metric(
        name="RecordsExported",
        unit=MetricUnit.Count,
        value=len(decoded_records),
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"exported": len(decoded_records)}),
    }
