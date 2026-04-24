"""
S3 Consumer Lambda Handler.

Consumes telemetry records from Kinesis and writes them to S3
for audit and compliance purposes.

Records are partitioned by date: telemetry/YYYY/MM/DD/HH/batch-{id}.jsonl
"""

import base64
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# S3 client
s3_client = boto3.client("s3")

# Configuration
BUCKET_NAME = os.environ.get("AUDIT_BUCKET_NAME", "")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Process Kinesis records and write to S3.

    Each batch of records is written as a single JSONL file
    partitioned by timestamp.
    """
    records = event.get("Records", [])

    if not records:
        logger.info("No records to process")
        return {"statusCode": 200, "body": "No records"}

    if not BUCKET_NAME:
        logger.error("AUDIT_BUCKET_NAME not configured")
        raise ValueError("AUDIT_BUCKET_NAME environment variable not set")

    logger.info(f"Processing {len(records)} records")

    # Decode and collect all records
    decoded_records = []
    for record in records:
        try:
            # Kinesis record data is base64 encoded
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

    # Generate S3 key with date partitioning
    now = datetime.now(timezone.utc)
    batch_id = str(uuid4())[:8]
    s3_key = (
        f"telemetry/{now.year}/{now.month:02d}/{now.day:02d}/"
        f"{now.hour:02d}/batch-{batch_id}.jsonl"
    )

    # Create JSONL content (one JSON object per line)
    jsonl_content = "\n".join(json.dumps(record) for record in decoded_records)

    # Write to S3
    with tracer.provider.in_subsegment("s3_put_object") as subsegment:
        subsegment.put_annotation("bucket", BUCKET_NAME)
        subsegment.put_annotation("key", s3_key)
        subsegment.put_annotation("record_count", len(decoded_records))

        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=jsonl_content.encode("utf-8"),
                ContentType="application/x-ndjson",
                Metadata={
                    "record-count": str(len(decoded_records)),
                    "batch-id": batch_id,
                },
            )
            logger.info(
                "Wrote batch to S3",
                extra={
                    "bucket": BUCKET_NAME,
                    "key": s3_key,
                    "record_count": len(decoded_records),
                },
            )
        except Exception as e:
            logger.exception(f"Failed to write to S3: {e}")
            metrics.add_metric(
                name="S3WriteErrors",
                unit=MetricUnit.Count,
                value=1,
            )
            raise

    # Record metrics
    metrics.add_metric(
        name="RecordsProcessed",
        unit=MetricUnit.Count,
        value=len(decoded_records),
    )
    metrics.add_metric(
        name="BatchesWritten",
        unit=MetricUnit.Count,
        value=1,
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "processed": len(decoded_records),
            "s3_key": s3_key,
        }),
    }
