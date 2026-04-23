# ── SQS Queues ───────────────────────────────────────────────────────────────
# Two queues mirror the two async pipelines:
#   ingestion  — PDF URL → ingestion agent → Neo4J + S3 Vectors
#   escalation — gap detected → expert router → EscalationCard

# ── Dead-letter queues (DLQ) ─────────────────────────────────────────────────

resource "aws_sqs_queue" "ingestion_dlq" {
  name                      = "${var.app_name}-ingestion-dlq"
  message_retention_seconds = 1209600  # 14 days
}

resource "aws_sqs_queue" "escalation_dlq" {
  name                      = "${var.app_name}-escalation-dlq"
  message_retention_seconds = 1209600
}

# ── Main queues ───────────────────────────────────────────────────────────────

resource "aws_sqs_queue" "ingestion" {
  name                       = "${var.app_name}-ingestion"
  visibility_timeout_seconds = 300   # 5 min — allow for slow PDF downloads
  message_retention_seconds  = 86400 # 1 day
  receive_wait_time_seconds  = 20    # long-polling — reduces empty receives

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingestion_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "escalation" {
  name                       = "${var.app_name}-escalation"
  visibility_timeout_seconds = 120
  message_retention_seconds  = 86400
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.escalation_dlq.arn
    maxReceiveCount     = 3
  })
}

# ── IAM policy — let App Runner task role send/receive ────────────────────────

data "aws_iam_policy_document" "sqs_access" {
  statement {
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [
      aws_sqs_queue.ingestion.arn,
      aws_sqs_queue.escalation.arn,
    ]
  }
}

resource "aws_iam_policy" "sqs_access" {
  name   = "${var.app_name}-sqs-access"
  policy = data.aws_iam_policy_document.sqs_access.json
}
