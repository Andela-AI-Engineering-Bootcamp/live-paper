"""Expert response endpoints.

Two flows live here because they're two halves of the same workflow:

  POST /api/papers/{paper_id}/invite-expert
      An admin (today: anyone — auth happens in the frontend) mints an
      invite link for an expert. We upsert the expert row so they show up
      in the experts list immediately, and return the URL the admin can
      paste into whatever email/messaging tool they want. Sending real
      email is intentionally NOT done here — see the design note below.

  POST /api/expert-responses
      The expert opens the invite link, fills the form on
      /expert-response, and submits. We embed their response, store it in
      S3 Vectors, write it to Neo4j, and persist a row in Aurora — all by
      delegating to the existing response_ingestion agent so the legacy
      escalation flow and this new paper-level review flow share one
      pipeline.

Design note on email: a CopyPasteEmailer (return the link) is good enough
for the demo and avoids signing up for SES sandboxing or a third-party
provider. To send real email later, add a services/email.py with a
provider-shaped interface and call it from invite_expert; the endpoint
contract here doesn't change.
"""

import logging
import os
from urllib.parse import quote_plus

from fastapi import APIRouter, HTTPException

from app.agents import response_ingestion
from app.models.paper import (
    ExpertInviteRequest,
    ExpertInviteResponse,
    ExpertResponse,
    ExpertResponseSubmission,
)
from app.services import database as db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["expert-responses"])

# Question placeholder for paper-level reviews — the schema requires a
# question on every ExpertResponseRecord row, but the form doesn't ask one.
PAPER_REVIEW_QUESTION = "General expert review of this paper"


@router.post("/expert-responses")
async def submit_expert_response(payload: ExpertResponseSubmission) -> dict:
    """Persist an expert's paper-level review.

    Returns the embedding vector_id and the expert/response row IDs so the
    frontend can confirm and (in the future) link to the response detail page.
    """
    paper = await db.get_paper(payload.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    expert_name = payload.expert_name or payload.expert_email.split("@")[0]

    expert_response = ExpertResponse(
        expert_name=expert_name,
        affiliation=None,
        response_text=payload.response,
        source_paper_id=payload.paper_id,
    )

    try:
        vector_id = await response_ingestion.run(
            response=expert_response,
            question=PAPER_REVIEW_QUESTION,
            expert_email=payload.expert_email,
        )
    except Exception as exc:
        logger.exception("Expert response ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to ingest response") from exc

    # response_ingestion already upserted the expert and wrote the
    # ExpertResponseRecord; pull the id back out so the response is useful.
    return {
        "status": "success",
        "vector_id": vector_id,
        "paper_id": payload.paper_id,
        "expert_email": payload.expert_email,
    }


@router.post("/papers/{paper_id}/invite-expert", response_model=ExpertInviteResponse)
async def invite_expert(paper_id: str, payload: ExpertInviteRequest) -> ExpertInviteResponse:
    """Create an invite for an expert to review a paper.

    Upserts the expert (so they show up in the experts list as `is_registered=False`
    until they actually submit), builds an /expert-response link off FRONTEND_URL,
    and returns it. The admin is responsible for delivering the link.
    """
    paper = await db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    frontend_url = os.getenv("FRONTEND_URL", "")
    if not frontend_url:
        # Without FRONTEND_URL we can still upsert and return a relative path,
        # but the admin would have to paste a domain in front of it themselves.
        # Failing loudly is more honest than silently returning a half-link.
        raise HTTPException(
            status_code=500,
            detail="FRONTEND_URL is not configured on the server.",
        )

    expert_id = await db.upsert_expert(
        email=payload.expert_email,
        name=payload.expert_name,
        affiliation=payload.affiliation,
        is_registered=False,
    )

    invite_url = (
        f"{frontend_url.rstrip('/')}/expert-response"
        f"?paper_id={quote_plus(paper_id)}"
        f"&expert_email={quote_plus(payload.expert_email)}"
    )

    return ExpertInviteResponse(
        expert_id=expert_id,
        invite_url=invite_url,
        paper_id=paper_id,
        expert_email=payload.expert_email,
        message="Invite link generated. Send this URL to the expert.",
    )
