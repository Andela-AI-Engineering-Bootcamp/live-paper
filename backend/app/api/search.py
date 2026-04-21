"""Search endpoint — ask a question across ingested papers."""

import logging
from fastapi import APIRouter

from app.agents import gap_detector, expert_router, retrieval
from app.models.paper import AskRequest, AskResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Run retrieval, gap detection, and optional escalation for a question."""
    result = await retrieval.run(request.question, request.paper_ids)
    should_escalate = await gap_detector.run(result)

    escalation_card = None
    if should_escalate:
        escalation_card = await expert_router.run(request.question, result)

    return AskResponse(
        question=request.question,
        passages=result.passages,
        escalated=should_escalate,
        escalation_card=escalation_card,
    )
