# =============================================================================
# Lambda Module - Generic Lambda Function
# =============================================================================

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.build/${var.function_name}.zip"
}

resource "aws_lambda_function" "this" {
  function_name    = "${var.name_prefix}-${var.function_name}"
  role             = aws_iam_role.lambda.arn
  handler          = var.handler
  runtime          = var.runtime
  architectures    = ["arm64"]
  timeout          = var.timeout
  memory_size      = var.memory_size
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  layers           = var.layers

  environment {
    variables = var.environment_variables
  }

  tags = {
    Name = "${var.name_prefix}-${var.function_name}"
  }
}

# CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.this.function_name}"
  retention_in_days = var.cloudwatch_retention_days

  tags = {
    Name = "${var.name_prefix}-${var.function_name}-logs"
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.name_prefix}-${var.function_name}-role"
  }
}

# Basic Lambda execution policy (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Kinesis write policy (for API Lambdas)
resource "aws_iam_role_policy_attachment" "kinesis_write" {
  count      = var.enable_kinesis_write ? 1 : 0
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.kinesis_write[0].arn
}

resource "aws_iam_policy" "kinesis_write" {
  count       = var.enable_kinesis_write ? 1 : 0
  name        = "${var.name_prefix}-${var.function_name}-kinesis-write"
  description = "Allow Lambda to write to Kinesis"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = var.kinesis_stream_arn
      }
    ]
  })
}

# Kinesis read policy (for consumers)
resource "aws_iam_role_policy_attachment" "kinesis_read" {
  count      = var.is_kinesis_consumer ? 1 : 0
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.kinesis_read[0].arn
}

resource "aws_iam_policy" "kinesis_read" {
  count       = var.is_kinesis_consumer ? 1 : 0
  name        = "${var.name_prefix}-${var.function_name}-kinesis-read"
  description = "Allow Lambda to read from Kinesis"

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
        Resource = var.kinesis_stream_arn
      }
    ]
  })
}

# Kinesis event source mapping (for consumers)
resource "aws_lambda_event_source_mapping" "kinesis" {
  count             = var.is_kinesis_consumer ? 1 : 0
  event_source_arn  = var.kinesis_stream_arn
  function_name     = aws_lambda_function.this.arn
  starting_position = "LATEST"
  batch_size        = var.kinesis_batch_size

  # Retry configuration
  maximum_retry_attempts       = 3
  bisect_batch_on_function_error = true
}

# Additional policies
resource "aws_iam_role_policy_attachment" "additional" {
  count      = length(var.additional_policies)
  role       = aws_iam_role.lambda.name
  policy_arn = var.additional_policies[count.index]
}
