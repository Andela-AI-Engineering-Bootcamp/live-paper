# ── SageMaker Serverless Inference — all-MiniLM-L6-v2 embeddings ─────────────
# Serverless (not real-time) — zero cost when idle, cold-start ~3 s.
# The embeddings service falls back to sentence-transformers locally.

resource "aws_iam_role" "sagemaker" {
  name = "${var.app_name}-sagemaker-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_full" {
  role       = aws_iam_role.sagemaker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy_attachment" "sagemaker_s3" {
  role       = aws_iam_role.sagemaker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_sagemaker_model" "embeddings" {
  name               = "${var.app_name}-embeddings-model"
  execution_role_arn = aws_iam_role.sagemaker.arn

  primary_container {
    image = var.sagemaker_model_image
    environment = {
      HF_MODEL_ID   = "sentence-transformers/all-MiniLM-L6-v2"
      HF_TASK       = "feature-extraction"
      SAGEMAKER_CONTAINER_LOG_LEVEL = "20"
    }
  }
}

resource "aws_sagemaker_endpoint_configuration" "embeddings" {
  name = "${var.app_name}-embedding-endpoint-config"

  production_variants {
    variant_name = "AllTraffic"
    model_name   = aws_sagemaker_model.embeddings.name

    serverless_config {
      memory_size_in_mb = 2048
      max_concurrency   = var.sagemaker_max_concurrency
    }
  }
}

resource "aws_sagemaker_endpoint" "embeddings" {
  name                 = "${var.app_name}-embedding-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.embeddings.name
}

# ── IAM — allow App Runner to invoke the endpoint ────────────────────────────

data "aws_iam_policy_document" "sagemaker_invoke" {
  statement {
    actions   = ["sagemaker:InvokeEndpoint"]
    resources = [aws_sagemaker_endpoint.embeddings.arn]
  }
}

resource "aws_iam_policy" "sagemaker_invoke" {
  name   = "${var.app_name}-sagemaker-invoke"
  policy = data.aws_iam_policy_document.sagemaker_invoke.json
}
