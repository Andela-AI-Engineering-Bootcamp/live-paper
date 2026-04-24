# ── SageMaker Serverless Inference ───────────────────────────────────────────
# Requires iam:PassRole which the deploy IAM user may not have.
# Backend falls back to local sentence-transformers when SAGEMAKER_ENDPOINT=""
# so this is left as a stub — IAM policy still created for the task role.

data "aws_iam_policy_document" "sagemaker_invoke" {
  statement {
    actions = ["sagemaker:InvokeEndpoint"]
    resources = [
      "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:endpoint/${var.app_name}-embedding-endpoint",
      "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:endpoint/alex-embedding-endpoint",
    ]
  }
}

resource "aws_iam_policy" "sagemaker_invoke" {
  name   = "${var.app_name}-sagemaker-invoke"
  policy = data.aws_iam_policy_document.sagemaker_invoke.json
}
