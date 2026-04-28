"""Expert Router Agent — identifies the best author to answer a question.

When the Gap Detector fires, this agent:
1. Scores candidate authors from retrieved paper metadata
2. Generates a structured EscalationCard
3. Logs the full escalation trace in LangFuse

Email dispatch is handled by chat.py via ResearchVetter.send_question_email
so this module stays pure: it only builds and returns the EscalationCard.
"""

import logging
from datetime import datetime

from app.agents.base import get_langfuse
from app.models.paper import Author, EscalationCard, RetrievalResult

logger = logging.getLogger(__name__)


async def run(question: str, retrieval: RetrievalResult) -> EscalationCard:
    """Build an EscalationCard for the most relevant authors."""
    lf = get_langfuse()
    trace_obj = lf.trace(name="expert-router", input={"question": question}) if lf else None

    try:
        authors = _score_authors(retrieval)
        gap_description = _describe_gap(question, retrieval)

        card = EscalationCard(
            question=question,
            gap_description=gap_description,
            candidate_authors=authors[:3],
            source_paper_ids=[p.paper_title for p in retrieval.passages[:3]],
            generated_at=datetime.utcnow(),
        )

        if trace_obj:
            trace_obj.update(output={
                "authors": [a.name for a in card.candidate_authors],
                "gap": gap_description,
            })

        logger.info("Escalation card generated for %d candidates", len(card.candidate_authors))
        return card

    except Exception as exc:
        if trace_obj:
            trace_obj.update(status="error", error=str(exc))
        logger.error("Expert router failed: %s", exc)
        raise


def _score_authors(retrieval: RetrievalResult) -> list[Author]:
    """Score candidate authors by passage confidence.

    Each passage carries a list of author name strings. We parse out
    name + email (if the string contains '@') and accumulate the max
    confidence score seen per name so the highest-relevance author
    floats to the top of the candidate list.
    """
    author_scores: dict[str, dict] = {}   # name → {score, email}

    for passage in retrieval.passages:
        for raw in passage.authors:
            raw = raw.strip()
            if not raw:
                continue

            # Support "Name <email>" or "Name (email)" or plain "Name"
            email: str | None = None
            name = raw
            if "<" in raw and ">" in raw:
                name = raw[:raw.index("<")].strip()
                email = raw[raw.index("<") + 1: raw.index(">")].strip()
            elif "(" in raw and "@" in raw and ")" in raw:
                name = raw[:raw.index("(")].strip()
                email = raw[raw.index("(") + 1: raw.index(")")].strip()
            elif "@" in raw:
                # bare email address used as author identifier
                email = raw
                name = raw.split("@")[0].replace(".", " ").title()

            existing = author_scores.get(name, {})
            new_score = max(existing.get("score", 0.0), passage.confidence)
            author_scores[name] = {
                "score": new_score,
                "email": email or existing.get("email"),
            }

    return [
        Author(
            name=name,
            email=info.get("email"),
            relevance_score=round(info["score"], 3),
        )
        for name, info in sorted(
            author_scores.items(), key=lambda x: x[1]["score"], reverse=True
        )
    ]


def _describe_gap(question: str, retrieval: RetrievalResult) -> str:
    if not retrieval.passages:
        return f"No papers in the corpus address: {question}"
    return (
        f"The top matching passage has a confidence of {retrieval.top_confidence:.2f}, "
        f"which is below the threshold required for a reliable answer. "
        f"The question may require domain expertise beyond what is captured in these papers."
    )
