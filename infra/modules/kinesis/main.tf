# =============================================================================
# Kinesis Module - Data Stream for Telemetry Fan-out
# =============================================================================

resource "aws_kinesis_stream" "telemetry" {
  name = "${var.name_prefix}-telemetry"

  # On-demand capacity mode - scales automatically, pay per use
  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  retention_period = var.retention_hours

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  tags = {
    Name = "${var.name_prefix}-telemetry"
  }
}

# IAM policy for Lambda to write to this stream
resource "aws_iam_policy" "write" {
  name        = "${var.name_prefix}-kinesis-write"
  description = "Allow writing telemetry records to the Kinesis stream"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = aws_kinesis_stream.telemetry.arn
      }
    ]
  })
}

# IAM policy for Lambda to read from this stream (for consumers)
resource "aws_iam_policy" "read" {
  name        = "${var.name_prefix}-kinesis-read"
  description = "Allow reading telemetry records from the Kinesis stream"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:ListShards"
        ]
        Resource = aws_kinesis_stream.telemetry.arn
      }
    ]
  })
}
