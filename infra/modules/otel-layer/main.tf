# =============================================================================
# OTel Layer Module - Shared OpenTelemetry Instrumentation
# =============================================================================

data "archive_file" "layer" {
  type        = "zip"
  source_dir  = "${path.root}/../layers/otel-common"
  output_path = "${path.module}/.build/otel-layer.zip"
}

resource "aws_lambda_layer_version" "otel" {
  layer_name          = "${var.name_prefix}-otel-common"
  description         = "Shared OpenTelemetry instrumentation for Lambda functions"
  filename            = data.archive_file.layer.output_path
  source_code_hash    = data.archive_file.layer.output_base64sha256
  compatible_runtimes = var.compatible_runtimes

  lifecycle {
    create_before_destroy = true
  }
}
