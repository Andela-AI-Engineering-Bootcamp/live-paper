"""Embedding service — SageMaker → OpenAI → sentence-transformers fallback chain.

Priority:
  1. SageMaker (when SAGEMAKER_ENDPOINT is set and reachable)
  2. OpenAI text-embedding-3-small at 384 dims (when OPENAI_API_KEY is set)
  3. Local sentence-transformers all-MiniLM-L6-v2 (dev only, no API key)

All three paths produce 384-dimensional vectors to match the S3 Vectors
index created with --dimension 384 --distance-metric cosine.
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
    """Return a 384-dimensional embedding for the given text."""
    endpoint = os.getenv("SAGEMAKER_ENDPOINT", "")

    if endpoint:
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
            logger.warning("SageMaker embedding failed, falling back to OpenAI: %s", exc)

    return await _openai_embed(text)


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


async def _openai_embed(text: str) -> list[float]:
    """OpenAI text-embedding-3-small at 384 dims — matches S3 Vectors index dimension."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=384,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.warning("OpenAI embedding failed, falling back to local model: %s", exc)

    return await _local_embed(text)


async def _local_embed(text: str) -> list[float]:
    """Local sentence-transformers fallback — dev only, no API key required."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Embedding service unavailable: no SAGEMAKER_ENDPOINT, no OPENAI_API_KEY, "
            "and sentence-transformers is not installed."
        ) from exc

    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model.encode(text).tolist()
