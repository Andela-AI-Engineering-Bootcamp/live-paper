"""Retrieval Agent — semantic search across ingested papers.

Pipeline:
  1. Expand the user question for better recall
  2. Embed expanded query via SageMaker
  3. Query S3 Vectors for top-k similar passages
  4. Score and return CitedPassages with confidence
  5. Signal escalation if top confidence < threshold
"""

import logging
import os

from agents import Agent, Runner, trace

from app.agents.base import get_langfuse, get_model
from app.models.paper import CitedPassage, RetrievalResult
from app.services import embeddings as embed_svc
from app.services import storage

logger = logging.getLogger(__name__)

EXPANSION_INSTRUCTIONS = """You are a retrieval query optimizer.
Given a user's question, rewrite it in 2-3 different phrasings to maximize recall
in a semantic search over academic papers. Return only the expanded queries as a
JSON array of strings."""

THRESHOLD = float(os.getenv("GAP_CONFIDENCE_THRESHOLD", "0.55"))


async def run(question: str, paper_ids: list[str] | None = None) -> RetrievalResult:
    """Search ingested papers for passages that answer the question."""
    lf = get_langfuse()
    trace_obj = lf.trace(name="retrieval-agent", input={"question": question}) if lf else None

    try:
        expanded = await _expand_query(question)
        all_results: list[dict] = []

        for q in [question] + expanded[:2]:
            vector = await embed_svc.embed(q)
            results = await storage.query_similar(vector, top_k=5)
            all_results.extend(results)

        # Deduplicate by paper key, keep highest score
        seen: dict[str, dict] = {}
        for r in all_results:
            key = r.get("key", "")
            if key not in seen or r.get("score", 0) > seen[key].get("score", 0):
                seen[key] = r

        ranked = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)[:5]

        passages = [
            CitedPassage(
                text=r.get("metadata", {}).get("findings", "See paper for details"),
                paper_title=r.get("metadata", {}).get("title", "Unknown"),
                authors=r.get("metadata", {}).get("authors", "").split(", "),
                confidence=round(float(r.get("score", 0)), 3),
            )
            for r in ranked
        ]

        top_confidence = passages[0].confidence if passages else 0.0
        escalate = top_confidence < THRESHOLD

        result = RetrievalResult(
            question=question,
            passages=passages,
            top_confidence=top_confidence,
            escalate=escalate,
        )

        if trace_obj:
            trace_obj.update(output={"top_confidence": top_confidence, "escalate": escalate})

        logger.info("Retrieval: top_confidence=%.3f escalate=%s", top_confidence, escalate)
        return result

    except Exception as exc:
        if trace_obj:
            trace_obj.update(status="error", error=str(exc))
        logger.error("Retrieval failed for question '%s': %s", question, exc)
        raise


async def _expand_query(question: str) -> list[str]:
    """Use LLM to generate alternative phrasings of the question."""
    try:
        import json
        model = get_model()
        agent = Agent(
            name="QueryExpander",
            instructions=EXPANSION_INSTRUCTIONS,
            model=model,
        )
        with trace("QueryExpansion"):
            result = await Runner.run(agent, input=question, max_turns=1)
        expanded = json.loads(result.final_output or "[]")
        return expanded if isinstance(expanded, list) else []
    except Exception:
        return []
