"""Unit tests for Gap Detector Agent."""

import pytest
from app.agents import gap_detector
from app.models.paper import CitedPassage, RetrievalResult


def make_result(confidence: float, passages: int = 1) -> RetrievalResult:
    p = [
        CitedPassage(
            text="Sample passage",
            paper_title="Test Paper",
            authors=["Author A"],
            confidence=confidence,
        )
    ] * passages
    return RetrievalResult(
        question="test question",
        passages=p,
        top_confidence=confidence,
        escalate=confidence < 0.55,
    )


@pytest.mark.asyncio
async def test_no_escalation_above_threshold():
    result = make_result(confidence=0.85)
    assert await gap_detector.run(result) is False


@pytest.mark.asyncio
async def test_escalation_below_threshold():
    result = make_result(confidence=0.40)
    assert await gap_detector.run(result) is True


@pytest.mark.asyncio
async def test_escalation_on_empty_passages():
    result = RetrievalResult(question="q", passages=[], top_confidence=0.0, escalate=True)
    assert await gap_detector.run(result) is True


@pytest.mark.asyncio
async def test_escalation_at_threshold_boundary():
    result = make_result(confidence=0.55)
    # At exactly the threshold — should NOT escalate (threshold is strict <)
    assert await gap_detector.run(result) is False
