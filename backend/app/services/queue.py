"""SQS queue service — same pattern as Alex planner/agent SQS setup.

Sends jobs to the ingestion and escalation queues.
No-ops in dev mode when queue URLs are not set.
"""

import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

_sqs = None


def _get_sqs():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return _sqs


async def enqueue_ingestion(job_id: str, pdf_url: str, paper_id: str) -> None:
    """Send a PDF ingestion job to the ingest queue."""
    queue_url = os.getenv("SQS_INGESTION_QUEUE_URL", "")
    message = {"job_id": job_id, "pdf_url": pdf_url, "paper_id": paper_id}

    if not queue_url:
        logger.info("Dev mode: would enqueue ingestion job %s", job_id)
        return

    _get_sqs().send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
    logger.info("Queued ingestion job %s", job_id)


async def enqueue_escalation(job_id: str, question: str, paper_ids: list[str]) -> None:
    """Send an escalation event to the escalation queue."""
    queue_url = os.getenv("SQS_ESCALATION_QUEUE_URL", "")
    message = {"job_id": job_id, "question": question, "paper_ids": paper_ids}

    if not queue_url:
        logger.info("Dev mode: would enqueue escalation job %s", job_id)
        return

    _get_sqs().send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
    logger.info("Queued escalation job %s", job_id)
