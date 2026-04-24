"""Embedding service — SageMaker Serverless endpoint (same as Alex course project).

Falls back to a local sentence-transformers model when SAGEMAKER_ENDPOINT
is not set, so the team can develop without AWS credentials.
"""

import json
import logging
import os
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

_runtime: Optional[object] = None


def _get_runtime():
    global _runtime
    if _runtime is None:
        _runtime = boto3.client("sagemaker-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return _runtime


async def embed(text: str) -> list[float]:
    """Return a 384-dimensional embedding for the given text.

    Uses SageMaker endpoint in production, falls back to local model in dev.
    """
    endpoint = os.getenv("SAGEMAKER_ENDPOINT", "")

    if not endpoint:
        return await _local_embed(text)

    try:
        runtime = _get_runtime()
        payload = json.dumps({"inputs": text})
        response = runtime.invoke_endpoint(
            EndpointName=endpoint,
            ContentType="application/json",
            Body=payload,
        )
        result = json.loads(response["Body"].read())
        return _to_sentence_vector(result)
    except Exception as exc:
        logger.warning("SageMaker embedding failed, using local fallback: %s", exc)
        return await _local_embed(text)


def _to_sentence_vector(result) -> list[float]:
    """Normalise SageMaker output to a flat 384-dim sentence embedding.

    Hugging Face feature-extraction returns [batch][token][hidden]; we mean-pool
    across the token axis. Some endpoints return [batch][hidden] or just [hidden].
    """
    if isinstance(result, dict):
        result = result.get("embeddings") or result.get("vectors") or result.get("data")

    if not isinstance(result, list) or not result:
        raise ValueError(f"Unexpected embedding payload: {type(result).__name__}")

    first = result[0]
    if isinstance(first, (int, float)):
        return [float(x) for x in result]
    if isinstance(first, list) and first and isinstance(first[0], (int, float)):
        return [float(x) for x in first]
    if isinstance(first, list) and first and isinstance(first[0], list):
        tokens = first
        dim = len(tokens[0])
        pooled = [0.0] * dim
        for tok in tokens:
            for i, v in enumerate(tok):
                pooled[i] += float(v)
        n = len(tokens)
        return [v / n for v in pooled]

    raise ValueError("Embedding payload shape not recognised")


async def _local_embed(text: str) -> list[float]:
    """Local fallback using sentence-transformers (dev only)."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        vector = model.encode(text).tolist()
        return vector
    except ImportError:
        logger.warning("sentence-transformers not installed — returning zero vector")
        return [0.0] * 384
