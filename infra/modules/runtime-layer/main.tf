# =============================================================================
# Runtime Dependencies Layer Module
# =============================================================================

data "archive_file" "layer" {
  type        = "zip"
  source_dir  = "${path.root}/../layers/runtime-deps"
  output_path = "${path.module}/.build/runtime-layer.zip"
}

resource "aws_lambda_layer_version" "runtime" {
  layer_name          = "${var.name_prefix}-runtime-deps"
  description         = "Runtime dependencies: FastAPI, Mangum, Powertools, Pydantic"
  filename            = data.archive_file.layer.output_path
  source_code_hash    = data.archive_file.layer.output_base64sha256
  compatible_runtimes = var.compatible_runtimes

  lifecycle {
    create_before_destroy = true
  }
}
