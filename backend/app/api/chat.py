"""Chat endpoint — multi-turn conversation grounded in ingested papers.

Flow:
  1. User asks a question (with optional focus paper IDs)
  2. Retrieval agent searches the vector store for relevant passages
  3. Gap detector checks if confidence is high enough to answer
  4. If gap: Expert Router identifies the best authors → email sent via
     ResearchVetter.send_question_email → escalation logged in Aurora
  5. If no gap: LLM synthesises a grounded answer from the top passages
  6. Response + cited passages returned to the frontend

The LLM synthesis step is what makes it feel like a real AI chat rather
than raw passage lookup — the user gets a coherent answer, not a JSON blob.
"""

import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI

from app.agents import retrieval, gap_detector, expert_router
from app.agents.base import get_model
from app.models.paper import RetrievalResult
from app.services import database as db
from app.research_vetter import ResearchVetter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

# ── In-memory session store ───────────────────────────────────────────────────
# session_id → list of {role, content}
# Bounded to last 20 messages per session to keep context manageable.
_sessions: dict[str, list[dict]] = {}

# ── ResearchVetter (handles email dispatch) ───────────────────────────────────
# Lazy-init so the app starts even if OPENAI_API_KEY is not set locally.
_vetter: Optional[ResearchVetter] = None


def _get_vetter() -> ResearchVetter:
    global _vetter
    if _vetter is None:
        _vetter = ResearchVetter(llm_client=OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
    return _vetter


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    paper_ids: Optional[list[str]] = None   # focus papers the user has pinned


class ChatResponse(BaseModel):
    session_id: str
    response: str
    escalated: bool = False
    passages: list[dict] = []
    escalation_info: Optional[dict] = None  # surfaced to frontend when escalated


# ── Synthesis prompt ──────────────────────────────────────────────────────────

SYNTHESIS_SYSTEM = """You are LivePaper, an AI research assistant.
Your job is to answer questions about academic papers clearly and precisely.

Rules:
- Ground every claim in the passages provided — do not hallucinate.
- Write in clear, natural prose. Do not use bullet points unless the user asks.
- Cite the paper title inline when you draw from it, e.g. (Smith et al., 2022).
- If the passages only partially answer the question, say so honestly.
- Keep answers concise but complete — aim for 3-5 sentences unless depth is needed.
- Never fabricate author names, findings, or statistics.
"""

SYNTHESIS_USER_TEMPLATE = """Conversation so far:
{history}

Passages retrieved from the knowledge base:
{passages}

User question: {question}

Answer the question using only the passages above."""


async def _synthesise(
    question: str,
    passages: list,
    history: list[dict],
) -> str:
    """Call the LLM to produce a grounded, coherent answer from the passages."""
    try:
        model = get_model()

        history_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}"
            for m in history[-6:]          # last 3 exchanges for context
        ) or "No prior conversation."

        passages_text = "\n\n".join(
            f"[{i+1}] {p.paper_title} ({', '.join(p.authors)}):\n{p.text}"
            for i, p in enumerate(passages)
        ) if passages else "No passages found."

        from agents import Agent, Runner
        agent = Agent(
            name="LivePaperChat",
            instructions=SYNTHESIS_SYSTEM,
            model=model,
        )
        prompt = SYNTHESIS_USER_TEMPLATE.format(
            history=history_text,
            passages=passages_text,
            question=question,
        )
        result = await Runner.run(agent, input=prompt, max_turns=1)
        return result.final_output or "I was unable to generate a response. Please try again."

    except Exception as exc:
        logger.error("Synthesis failed: %s", exc)
        # Graceful fallback — return the raw top passage text
        if passages:
            top = passages[0]
            return (
                f"{top.text}\n\n"
                f"— {top.paper_title} ({', '.join(top.authors)}), "
                f"confidence {round(top.confidence * 100)}%"
            )
        return "I couldn't find relevant information for that question."


async def _dispatch_expert_emails(
    question: str,
    result: RetrievalResult,
    paper_ids: list[str] | None,
) -> dict:
    """
    Build escalation card, notify candidate authors by email, log to Aurora.
    Returns a dict summarising what happened (surfaced to the frontend).
    """
    card = await expert_router.run(question, result)
    vetter = _get_vetter()

    notified: list[str] = []
    frontend_url = os.getenv("FRONTEND_URL", "https://livepaper.app")

    for author in card.candidate_authors:
        if not author.email:
            continue

        # Build the expert-response deep-link
        # The expert-response page reads paper_id + expert_email from query params.
        paper_id = card.source_paper_ids[0] if card.source_paper_ids else "unknown"
        response_url = (
            f"{frontend_url}/expert-response"
            f"?paper_id={paper_id}"
            f"&expert_email={author.email}"
        )

        subject = f"[LivePaper] A researcher needs your expertise"
        body = (
            f"Dear {author.name},\n\n"
            f"A researcher using LivePaper was unable to find a clear answer "
            f"in the existing literature and your work was identified as most relevant.\n\n"
            f"Their question:\n\"{question}\"\n\n"
            f"Gap identified:\n\"{card.gap_description}\"\n\n"
            f"Please share your expert perspective by visiting the link below — "
            f"it takes just a few minutes and your answer will be added to the "
            f"LivePaper knowledge base, helping future researchers:\n\n"
            f"{response_url}\n\n"
            f"Thank you,\nThe LivePaper Team"
        )

        try:
            vetter.send_question_email(
                email=author.email,
                subject=subject,
                body=body,
            )
            notified.append(author.name)
            logger.info("Escalation email sent to %s (%s)", author.name, author.email)

            # Upsert expert into Aurora so they appear in the admin experts list
            await db.upsert_expert(
                email=author.email,
                name=author.name,
            )
        except Exception as exc:
            logger.error("Failed to email %s: %s", author.email, exc)

    return {
        "gap_description": card.gap_description,
        "notified_experts": notified,
        "candidate_count": len(card.candidate_authors),
    }


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Multi-turn AI chat grounded in the paper knowledge base.

    - Maintains per-session conversation history (last 20 messages).
    - Returns synthesised prose answers, not raw passage dumps.
    - Escalates to domain experts when the knowledge base can't answer.
    """
    sid = request.session_id or str(uuid.uuid4())
    history = _sessions.setdefault(sid, [])

    history.append({"role": "user", "content": request.message})
    if len(history) > 20:
        history[:] = history[-20:]

    try:
        # ── Step 1: Retrieve ─────────────────────────────────────────────────
        result = await retrieval.run(
            question=request.message,
            paper_ids=request.paper_ids,
        )

        # ── Step 2: Gap detection ────────────────────────────────────────────
        should_escalate = await gap_detector.run(result)

        # ── Step 3a: Escalation path ─────────────────────────────────────────
        if should_escalate:
            escalation_info = await _dispatch_expert_emails(
                question=request.message,
                result=result,
                paper_ids=request.paper_ids,
            )

            expert_names = escalation_info.get("notified_experts", [])
            if expert_names:
                who = expert_names[0] if len(expert_names) == 1 else \
                      f"{expert_names[0]} and {len(expert_names) - 1} other(s)"
                response_text = (
                    f"I found a knowledge gap on this topic — the available papers "
                    f"don't provide a confident answer.\n\n"
                    f"I've reached out to {who}, whose work is most relevant to your "
                    f"question. Their response will be added to the knowledge base and "
                    f"you'll be able to ask this question again once they reply.\n\n"
                    f"Gap: {escalation_info['gap_description']}"
                )
            else:
                response_text = (
                    f"I found a knowledge gap on this topic and attempted to identify "
                    f"relevant experts, but none had contact details on file.\n\n"
                    f"Gap: {escalation_info['gap_description']}"
                )

            history.append({"role": "assistant", "content": response_text})
            return ChatResponse(
                session_id=sid,
                response=response_text,
                escalated=True,
                passages=[p.model_dump() for p in result.passages[:3]],
                escalation_info=escalation_info,
            )

        # ── Step 3b: Answer path — synthesise a grounded response ────────────
        response_text = await _synthesise(
            question=request.message,
            passages=result.passages,
            history=history[:-1],   # exclude the message we just appended
        )

        history.append({"role": "assistant", "content": response_text})

        return ChatResponse(
            session_id=sid,
            response=response_text,
            escalated=False,
            passages=[p.model_dump() for p in result.passages[:3]],
        )

    except Exception as exc:
        logger.error("Chat error for session %s: %s", sid, exc, exc_info=True)
        return ChatResponse(
            session_id=sid,
            response=(
                "Sorry, I encountered an error processing your question. "
                "Please try again."
            ),
        )
