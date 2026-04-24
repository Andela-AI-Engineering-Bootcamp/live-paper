"""Chat endpoint — multi-turn conversation grounded in ingested papers."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents import retrieval, gap_detector, expert_router

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

# In-memory session store: session_id → list of {role, content}
_sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    escalated: bool = False
    passages: list[dict] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Multi-turn chat grounded in the paper knowledge base.

    Maintains conversation history per session (last 20 messages).
    Routes through the retrieval agent and escalates to expert router
    when confidence is below the gap threshold.
    """
    sid = request.session_id or str(uuid.uuid4())
    history = _sessions.setdefault(sid, [])

    history.append({"role": "user", "content": request.message})
    # Keep last 20 messages to bound context size
    if len(history) > 20:
        history[:] = history[-20:]

    try:
        result = await retrieval.run(request.message)
        # gap_detector.run is async and returns a bool — True ⇒ escalate.
        # The previous code did `gap_detector.run(result)` (no await) and then
        # `gap.escalate`, which threw "'coroutine' object has no attribute 'escalate'"
        # and swallowed every chat in the generic except below.
        should_escalate = await gap_detector.run(result)

        if should_escalate:
            # expert_router.run signature is (question: str, retrieval: RetrievalResult)
            card = await expert_router.run(request.message, result)
            response_text = (
                f"I found a knowledge gap on this topic. "
                f"Your question has been escalated to {card.candidate_authors[0].name if card.candidate_authors else 'a domain expert'}. "
                f"Gap: {card.gap_description}"
            )
            escalated = True
        else:
            passages = result.passages
            if passages:
                top = passages[0]
                response_text = (
                    f"{top.text}\n\n"
                    f"— {top.paper_title} ({', '.join(top.authors)})"
                    f", confidence {round(top.confidence * 100)}%"
                )
            else:
                response_text = "I couldn't find relevant passages for that question in the current knowledge base."
            escalated = False

        history.append({"role": "assistant", "content": response_text})

        return ChatResponse(
            session_id=sid,
            response=response_text,
            escalated=escalated,
            passages=[p.model_dump() for p in result.passages[:3]],
        )

    except Exception as exc:
        logger.error("Chat error for session %s: %s", sid, exc)
        return ChatResponse(
            session_id=sid,
            response="Sorry, I encountered an error processing your question. Please try again.",
        )
