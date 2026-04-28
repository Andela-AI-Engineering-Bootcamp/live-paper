"""ResearchVetter — LLM-powered comprehension assessment and email dispatch.

Used by the chat pipeline to notify experts when a knowledge gap is detected.
The send_question_email method is the primary integration point called from
chat.py during escalation.
"""

import os
import re
from typing import List, Dict, Any, Optional

from openai import OpenAI


class ResearchVetter:
    """
    Generates academic assessment questions, evaluates user answers,
    and dispatches email notifications via Mailjet.
    """

    def __init__(self, llm_client: OpenAI):
        self.llm = llm_client

    # ── Question generation ───────────────────────────────────────────────────

    def generate_assessment_questions(
        self,
        title: str,
        summary: str,
    ) -> List[str]:
        """
        Generate three challenging questions that test deep understanding
        of the paper's methodology, implications, and core findings.
        """
        prompt = f"""Act as a senior academic reviewer. Based on the research title and summary below,
generate exactly three challenging questions that test a reader's deep understanding
of the methodology, implications, and core findings.

Title: {title}
Summary: {summary}

Format: Return only the three questions, one per line."""

        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        questions = (response.choices[0].message.content or "").strip().split("\n")
        return [q.strip() for q in questions if q.strip()][:3]

    # ── Answer verification ───────────────────────────────────────────────────

    def verify_multiple_answers(
        self,
        questions: List[str],
        user_answers: List[str],
        context: str,
    ) -> Dict[str, Any]:
        """
        Evaluate user answers and return a score out of 100 with feedback.
        """
        submission_text = ""
        for i, (q, a) in enumerate(zip(questions, user_answers), 1):
            submission_text += f"\n--- Question {i} ---\nQ: {q}\nA: {a}\n"

        prompt = f"""Act as an Academic Examiner. Grade the following user responses based on the provided research context.

[RESEARCH CONTEXT]
{context}

[USER SUBMISSION]
{submission_text}

[GRADING RUBRIC]
- Accuracy (40 pts): Do the answers align with the research facts?
- Depth (40 pts): Does the user show high-level conceptual understanding?
- Clarity (20 pts): Is the terminology used correctly?

[OUTPUT FORMAT]
TOTAL SCORE: [0-100]
ACADEMIC FEEDBACK: [Brief analysis of strengths and weaknesses]"""

        evaluation = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        evaluation_text = (evaluation.choices[0].message.content or "").strip()

        score_match = re.search(r"TOTAL\s*SCORE\D*(\d+)", evaluation_text, re.IGNORECASE)
        score = 0
        if score_match:
            try:
                score = int(score_match.group(1))
            except (ValueError, IndexError):
                score = 0

        feedback_parts = evaluation_text.split("ACADEMIC FEEDBACK:")
        feedback = feedback_parts[-1].strip() if len(feedback_parts) > 1 else evaluation_text

        return {
            "score": score,
            "passed": score >= 75,
            "feedback": feedback,
            "full_report": evaluation_text,
        }

    # ── Relevance check ───────────────────────────────────────────────────────

    def check_question_is_relevant(self, question: str, context: str) -> bool:
        """Return True if the user's question is relevant to the paper context."""
        prompt = f"""Act as a relevance filter. Given the research context and a user's question,
determine if the question is relevant to the paper's content.

[RESEARCH CONTEXT]
{context}

[USER QUESTION]
{question}

Is this question relevant to the research paper? Answer with "Yes" or "No" and provide a brief explanation."""

        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        answer = (response.choices[0].message.content or "").strip().lower()
        return answer.startswith("yes")

    # ── Author profile ────────────────────────────────────────────────────────

    def create_author_profile(self, author_info: Dict[str, str]) -> str:
        name         = author_info.get("name", "Unknown Author")
        title        = author_info.get("title", "")
        email        = author_info.get("email", "")
        affiliation  = author_info.get("affiliation", "Unknown Institution")
        parts = [name]
        if title:
            parts.append(title)
        parts.append(f"from {affiliation}")
        if email:
            parts.append(f"(Email: {email})")
        return ", ".join(parts)

    # ── Email dispatch ────────────────────────────────────────────────────────

    def send_mail_notification(
        self,
        email: str,
        subject: str,
        body: str,
        first_name: str = "",
    ) -> bool:
        """
        Send an email via Mailjet. Returns True on success, False on failure.
        Requires env vars: MAILJET_API_KEY, MAILJET_API_SECRET, MAILJET_SENDER.
        """
        import requests

        api_key    = os.getenv("MAILJET_API_KEY")
        api_secret = os.getenv("MAILJET_API_SECRET")
        sender     = os.getenv("MAILJET_SENDER")

        if not (api_key and api_secret and sender):
            import logging
            logging.getLogger(__name__).warning(
                "Mailjet credentials not configured — email to %s not sent", email
            )
            return False

        data = {
            "Messages": [
                {
                    "From":     {"Email": sender, "Name": "LivePaper"},
                    "To":       [{"Email": email}],
                    "Subject":  subject,
                    "TextPart": body,
                    "HTMLPart": body.replace("\n", "<br>"),
                }
            ]
        }

        response = requests.post(
            "https://api.mailjet.com/v3.1/send",
            auth=(api_key, api_secret),
            json=data,
            timeout=15,
        )

        if response.status_code == 200:
            import logging
            logging.getLogger(__name__).info("Email sent to %s", email)
            return True

        import logging
        logging.getLogger(__name__).error(
            "Mailjet failed for %s: %s", email, response.text
        )
        return False

    def send_question_email(self, email: str, subject: str, body: str) -> bool:
        """
        Send an escalation question email to an expert.
        Called by chat.py during gap-detected escalation.
        Returns True if the email was dispatched successfully.
        """
        return self.send_mail_notification(email=email, subject=subject, body=body)
