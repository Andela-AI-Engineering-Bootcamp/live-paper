import os
from typing import List, Dict
import re

from openai import OpenAI

from database_manager import DatabaseManager

class ResearchVetter:
    """
    A class to generate academic-level questions from research summaries
    and verify user comprehension.
    """
    
    def __init__(self, llm_client: OpenAI):
        """
        :param llm_client: An instance of your preferred LLM API (e.g., OpenAI, Anthropic, Gemini)
        """
        self.llm = llm_client

    def generate_assessment_questions(self, title: str, summary: str, db: DatabaseManager, paper_id: str, user_id: str) -> List[str]:
        """
        Generates three high-level questions designed to test deep understanding 
        rather than just surface-level facts.
        """ 
        prompt = f"""
        Act as a senior academic reviewer. Based on the research title and summary below, 
        generate exactly three challenging questions that test a reader's deep understanding 
        of the methodology, implications, and core findings.
        
        Title: {title}
        Summary: {summary}
        
        Format: Return only the three questions, one per line.
        """
        
        # This is a placeholder for your specific LLM call logic
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        questions = response.choices[0].message.content.strip().split("\n") # type: ignore
        return questions[:3]
    
    def create_author_profile(self, session_id, author_info: Dict[str, str]) -> str:
        name = author_info.get("name", "Unknown Author")
        title = author_info.get("title", "Unknown Title")
        email = author_info.get("email", "Unknown Email")
        organization = author_info.get("organization", "Unknown Organization")
        affiliation = author_info.get("affiliation", "Unknown Institution")
        profile = f"{name}, {title} from {affiliation} (Email: {email})"
        return profile

    def verify_multiple_answers(self, questions: List[str], user_answers: List[str], context: str) -> Dict[str, any]: # type: ignore
        """
        Evaluates the user's answers and returns a numerical score out of 100.
        """
        submission_text = ""
        for i, (q, a) in enumerate(zip(questions, user_answers), 1):
            submission_text += f"\n--- Question {i} ---\nQ: {q}\nA: {a}\n"

        print(f"Debug: Verifying answers with context:\n{context}\nAnd submission:\n{submission_text}")
        prompt = f"""
        Act as an Academic Examiner. Grade the following user responses based on the provided research context.
        
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
        ACADEMIC FEEDBACK: [Brief analysis of strengths and weaknesses]
        """

        evaluation = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        evaluation_text = (evaluation.choices[0].message.content or "").strip()
         
        # Extract the numerical score using a simple Regular Expression
        score_match = re.search(r"TOTAL\s*SCORE\D*(\d+)", evaluation_text, re.IGNORECASE)
        score = 0
        if score_match:
            try:
                score = int(score_match.group(1))
            except (ValueError, IndexError):
                score = 0

         
        data = {
            "score": score,
            "passed": score >= 75,
            "feedback": evaluation_text.split("\n\nACADEMIC FEEDBACK: ")[-1],
            "full_report": evaluation_text
        } 
        
        # print(f"Debug: Final evaluation data:\n{data}")
        return data
    
    def send_mail_notification(self, email: str, subject: str, body: str, first_name: str = ""):
        """
        Send an email notification using Mailjet.
        """
        import requests
        MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
        MAILJET_API_SECRET = os.getenv("MAILJET_API_SECRET")
        MAILJET_SENDER = os.getenv("MAILJET_SENDER")
        if not (MAILJET_API_KEY and MAILJET_API_SECRET and MAILJET_SENDER):
            print("Mailjet credentials not set. Email not sent.")
            return
        data = {
            'Messages': [
                {
                    "From": {"Email": MAILJET_SENDER, "Name": "Research Assessment"},
                    "To": [{"Email": email}],
                    "Subject": subject,
                    "TextPart": body,
                    "HTMLPart": body
                }
            ]
        }
        response = requests.post(
            "https://api.mailjet.com/v3.1/send",
            auth=(MAILJET_API_KEY, MAILJET_API_SECRET),
            json=data
        )
        if response.status_code == 200:
            print(f"Mailjet: Email sent to {email}")
        else:
            print(f"Mailjet: Failed to send email to {email}. Response: {response.text}")
            
    def send_question_email(self, email: str, subject: str, body: str):
        """
        Send an email with the generated questions to the user.
        """
        self.send_mail_notification(email, subject, body)
        
    def check_question_is_relevant(self, question: str, context: str) -> bool:
        """
        Checks if the user's question is relevant to the paper's content.
        """
        prompt = f"""
        Act as a relevance filter. Given the research context and a user's question, determine if the question is relevant to the paper's content.

        [RESEARCH CONTEXT]
        {context}

        [USER QUESTION]
        {question}

        Is this question relevant to the research paper? Answer with "Yes" or "No" and provide a brief explanation.
        """
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message.content.strip().lower() # type: ignore
        return answer.lower().startswith("yes")