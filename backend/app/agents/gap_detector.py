"""Gap Detector Agent — decides whether to escalate to a human expert.

This is the hinge of the LivePaper system. It receives a RetrievalResult
and fires an escalation event when confidence is below the threshold.

The agent that knows what it doesn't know.
"""

import logging

from app.models.paper import RetrievalResult

logger = logging.getLogger(__name__)


async def run(result: RetrievalResult) -> bool:
    """Return True if the question should be escalated to an expert.

    Escalation fires when:
    - No passages were found, OR
    - The top confidence score is below GAP_CONFIDENCE_THRESHOLD

    The threshold is set in config (default 0.55) and tuned via LangFuse
    metrics after the first 100 queries.
    """
    if not result.passages:
        logger.info("Gap detected: no passages found for question")
        return True

    if result.escalate:
        logger.info(
            "Gap detected: top_confidence=%.3f below threshold — escalating",
            result.top_confidence,
        )
        return True

    logger.info("No gap: top_confidence=%.3f — answer found in corpus", result.top_confidence)
    return False
