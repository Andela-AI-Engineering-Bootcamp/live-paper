# ── ECR Repository ───────────────────────────────────────────────────────────

resource "aws_ecr_repository" "backend" {
  name                 = "${var.app_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

# ── App Runner IAM ────────────────────────────────────────────────────────────

resource "aws_iam_role" "apprunner_access" {
  name = "${var.app_name}-apprunner-access-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "build.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr" {
  role       = aws_iam_role.apprunner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_security_group" "apprunner" {
  name        = "${var.app_name}-apprunner-sg"
  description = "Outbound access for App Runner VPC connector"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_apprunner_vpc_connector" "backend" {
  vpc_connector_name = "${var.app_name}-vpc-connector"
  subnets            = data.aws_subnets.default.ids
  security_groups    = [aws_security_group.apprunner.id]
}

# ── Task role — attached to running containers ────────────────────────────────

resource "aws_iam_role" "apprunner_task" {
  name = "${var.app_name}-apprunner-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "tasks.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_sqs" {
  role       = aws_iam_role.apprunner_task.name
  policy_arn = aws_iam_policy.sqs_access.arn
}

resource "aws_iam_role_policy_attachment" "task_s3vectors" {
  role       = aws_iam_role.apprunner_task.name
  policy_arn = aws_iam_policy.s3vectors_access.arn
}

resource "aws_iam_role_policy_attachment" "task_sagemaker" {
  role       = aws_iam_role.apprunner_task.name
  policy_arn = aws_iam_policy.sagemaker_invoke.arn
}

resource "aws_iam_role_policy_attachment" "task_aurora_secret" {
  role       = aws_iam_role.apprunner_task.name
  policy_arn = aws_iam_policy.aurora_secret_access.arn
}

# ── Bedrock — allow Nova Pro calls ────────────────────────────────────────────

data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = ["arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-pro-v1:0"]
  }
}

resource "aws_iam_policy" "bedrock_invoke" {
  name   = "${var.app_name}-bedrock-invoke"
  policy = data.aws_iam_policy_document.bedrock_invoke.json
}

resource "aws_iam_role_policy_attachment" "task_bedrock" {
  role       = aws_iam_role.apprunner_task.name
  policy_arn = aws_iam_policy.bedrock_invoke.arn
}

# ── App Runner Service ─────────────────────────────────────────────────────────

resource "aws_apprunner_service" "backend" {
  service_name = "${var.app_name}-backend"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access.arn
    }
    image_repository {
      image_identifier      = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
      image_repository_type = "ECR"
      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          DEBUG                  = "false"
          AWS_REGION             = var.aws_region
          AURORA_CLUSTER_ARN     = aws_rds_cluster.aurora.arn
          AURORA_HOST            = aws_rds_cluster.aurora.endpoint
          AURORA_DATABASE        = var.aurora_db_name
          AURORA_USERNAME        = var.aurora_username
          VECTOR_BUCKET          = aws_s3vectors_vector_bucket.papers.vector_bucket_name
          SAGEMAKER_ENDPOINT     = aws_sagemaker_endpoint.embeddings.name
          SQS_INGESTION_QUEUE_URL  = aws_sqs_queue.ingestion.url
          SQS_ESCALATION_QUEUE_URL = aws_sqs_queue.escalation.url
          BEDROCK_MODEL_ID       = "us.amazon.nova-pro-v1:0"
          BEDROCK_REGION         = "us-west-2"
        }
        runtime_environment_secrets = {
          AURORA_PASSWORD      = aws_rds_cluster.aurora.master_user_secret[0].secret_arn
          OPENAI_API_KEY       = aws_secretsmanager_secret.openai.arn
          LANGFUSE_PUBLIC_KEY  = aws_secretsmanager_secret.langfuse_public.arn
          LANGFUSE_SECRET_KEY  = aws_secretsmanager_secret.langfuse_secret.arn
        }
      }
    }
    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu    = "1 vCPU"
    memory = "2 GB"
    instance_role_arn = aws_iam_role.apprunner_task.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.backend.arn
    }
  }

  health_check_configuration {
    path                = "/api/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 3
  }
}

# ── Secrets Manager — API keys ────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "openai" {
  name = "${var.app_name}/openai-api-key"
}

resource "aws_secretsmanager_secret_version" "openai" {
  secret_id     = aws_secretsmanager_secret.openai.id
  secret_string = var.openai_api_key
}

resource "aws_secretsmanager_secret" "langfuse_public" {
  name = "${var.app_name}/langfuse-public-key"
}

resource "aws_secretsmanager_secret_version" "langfuse_public" {
  secret_id     = aws_secretsmanager_secret.langfuse_public.id
  secret_string = var.langfuse_public_key
}

resource "aws_secretsmanager_secret" "langfuse_secret" {
  name = "${var.app_name}/langfuse-secret-key"
}

resource "aws_secretsmanager_secret_version" "langfuse_secret" {
  secret_id     = aws_secretsmanager_secret.langfuse_secret.id
  secret_string = var.langfuse_secret_key
}
