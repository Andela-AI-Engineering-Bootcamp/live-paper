"""Unit tests for Pydantic model validation."""

import pytest
from pydantic import ValidationError
from app.models.paper import PaperExtraction, CitedPassage, ExpertResponse


def test_paper_extraction_valid():
    p = PaperExtraction(
        title="Test Paper",
        authors=["Alice", "Bob"],
        key_concepts=["malaria", "artemisinin"],
        methods=["RCT"],
        findings=["Combination therapy reduces mortality by 30%"],
        open_questions=["Optimal dosage for children under 5 unclear"],
        confidence=0.9,
    )
    assert p.confidence == 0.9


def test_paper_extraction_confidence_out_of_range():
    with pytest.raises(ValidationError):
        PaperExtraction(
            title="Bad Paper",
            authors=[],
            key_concepts=[],
            methods=[],
            findings=[],
            open_questions=[],
            confidence=1.5,  # invalid: > 1.0
        )


def test_cited_passage_valid():
    p = CitedPassage(
        text="Artemisinin reduces fever in 48 hours.",
        paper_title="Malaria Treatment Study",
        authors=["Dr. Smith"],
        confidence=0.82,
    )
    assert p.page is None


def test_expert_response_requires_fields():
    with pytest.raises(ValidationError):
        ExpertResponse(
            expert_name="",  # empty name
            response_text="",
            source_paper_id="paper-1",
        )
