# ── Aurora Serverless v2 (Postgres) ──────────────────────────────────────────
# Scales from 0.5 ACU (paused at idle) to 4 ACU under load.
# Costs nothing when the team isn't using it between demo sessions.

resource "aws_db_subnet_group" "aurora" {
  name       = "${var.app_name}-aurora-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_security_group" "aurora" {
  name        = "${var.app_name}-aurora-sg"
  description = "Aurora Serverless v2 — allow Postgres from App Runner"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.apprunner.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier      = "${var.app_name}-cluster"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "16.1"
  database_name           = var.aurora_db_name
  master_username         = var.aurora_username
  manage_master_user_password = true   # stores password in Secrets Manager automatically

  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_acu
    max_capacity = var.aurora_max_acu
  }

  db_subnet_group_name   = aws_db_subnet_group.aurora.name
  vpc_security_group_ids = [aws_security_group.aurora.id]

  skip_final_snapshot = true  # fine for capstone; set false for real prod

  lifecycle {
    ignore_changes = [master_password]
  }
}

resource "aws_rds_cluster_instance" "aurora_writer" {
  identifier         = "${var.app_name}-writer"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version
}

# ── IAM — allow App Runner to read the Aurora-generated Secrets Manager secret

data "aws_iam_policy_document" "aurora_secret_access" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_rds_cluster.aurora.master_user_secret[0].secret_arn,
      "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.app_name}/*",
    ]
  }
}

resource "aws_iam_policy" "aurora_secret_access" {
  name   = "${var.app_name}-aurora-secret-access"
  policy = data.aws_iam_policy_document.aurora_secret_access.json
}
