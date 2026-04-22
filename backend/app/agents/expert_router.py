"""Expert Router Agent — identifies the best author to answer a question.

When the Gap Detector fires, this agent:
1. Scores candidate authors from retrieved paper metadata
2. Generates a structured EscalationCard
3. Logs the full escalation trace in LangFuse

In MVP, dispatch is logged and surfaced on the frontend.
Real email delivery is wired in post-demo via the escalation queue.
"""

import logging
from datetime import datetime

from app.agents.base import get_langfuse
from app.models.paper import Author, EscalationCard, RetrievalResult

logger = logging.getLogger(__name__)

CARD_TEMPLATE = """Dear {name},

A researcher using LivePaper was unable to find an answer in the existing literature
and your work was identified as most relevant.

Their question:
"{question}"

Gap identified:
"{gap_description}"

Relevant papers from your work:
{papers}

Would you be able to provide a brief response (a few sentences or a paragraph)?
Your answer will be attributed to you and added to the LivePaper knowledge base,
helping future researchers with similar questions.

Thank you,
The LivePaper Team"""


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
    """Score candidate authors by passage confidence (higher = more relevant)."""
    author_scores: dict[str, float] = {}

    for passage in retrieval.passages:
        for author in passage.authors:
            name = author.strip()
            if name:
                existing = author_scores.get(name, 0.0)
                author_scores[name] = max(existing, passage.confidence)

    return [
        Author(name=name, relevance_score=round(score, 3))
        for name, score in sorted(author_scores.items(), key=lambda x: x[1], reverse=True)
    ]


def _describe_gap(question: str, retrieval: RetrievalResult) -> str:
    if not retrieval.passages:
        return f"No papers in the corpus address: {question}"
    return (
        f"The top matching passage has a confidence of {retrieval.top_confidence:.2f}, "
        f"which is below the threshold required for a reliable answer. "
        f"The question may require domain expertise beyond what is captured in these papers."
    )
