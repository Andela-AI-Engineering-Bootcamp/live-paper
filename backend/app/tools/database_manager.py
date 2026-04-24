import os
from typing import List, Dict, Optional, Any
from sqlmodel import Session, create_engine, SQLModel, select, func
from models import AskedQuestion, AssessmentQA, ExpertProfile

class DatabaseManager:
    def __init__(self):
        self.db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
        self.engine = create_engine(self.db_url)
        SQLModel.metadata.create_all(self.engine)

    def create_expert(self, name: str, title: str, email: str, organization: Optional[str] = None, affiliation: Optional[str] = None) -> ExpertProfile:
        with Session(self.engine) as session:
            expert = ExpertProfile(
                name=name, title=title, email=email,
                organization=organization, affiliation=affiliation
            )
            session.add(expert)
            session.commit()
            session.refresh(expert)
            return expert

    def start_new_assessment(self, author_id: int, paper_id: str, user_id: str, questions: List[str]) -> int:
        """
        Handles logic for tries and returns the ID of the assessment record.
        If an incomplete assessment exists, it returns that.
        """
        with Session(self.engine) as session:
            # 1. Check for existing incomplete attempts (no answer yet)
            stmt = select(AssessmentQA).where(
                AssessmentQA.author_id == author_id, 
                AssessmentQA.paper_id == paper_id,
                AssessmentQA.answer_text == None
            )
            incomplete = session.exec(stmt).first()
            print(f"Found incomplete assessment: {incomplete}") # Debugging log
            if incomplete:
                return incomplete.id # type: ignore

            # 2. Count existing completed attempts
            count_stmt = select(func.count(AssessmentQA.id) # type: ignore
).where(
                AssessmentQA.author_id == author_id, 
                AssessmentQA.paper_id == paper_id
            )
            try_count = session.exec(count_stmt).one() # type: ignore

            if try_count >= 2:
                raise Exception("Maximum number of tries (2) reached for this paper.")

            # 3. Create new record
            new_assessment = AssessmentQA(
                author_id=author_id,
                paper_id=paper_id,
                user_id=user_id,
                question_text="\n".join(questions),
                tries=try_count + 1
            )
            session.add(new_assessment)
            session.commit()
            session.refresh(new_assessment)
            return new_assessment.id # type: ignore

    def update_results(self, assessment_id: int, results: Dict[str, Any], answer_text: str):
        """Saves the user's answer and the final calculated score/feedback."""
        with Session(self.engine) as session:
            assessment = session.get(AssessmentQA, assessment_id)
            if not assessment:
                raise Exception("Assessment record not found.")
            
            assessment.answer_text = answer_text
            assessment.overall_score = results.get('score')
            assessment.is_passed = results.get('passed', False)
            assessment.feedback = results.get('full_report')
            
            session.add(assessment)
            session.commit()
            
    def get_questions_by_paper_id(self, paper_id: str, user_id: str) -> Optional[List]:
        with Session(self.engine) as session:
            stmt = select(AssessmentQA).where(
                AssessmentQA.paper_id == paper_id,
                AssessmentQA.user_id == user_id,
                AssessmentQA.answer_text == None
            )
            assessment = session.exec(stmt).first()
            return [assessment.question_text, assessment.id, assessment.is_passed] if assessment else None

    def get_questions_by_id(self, assessment_id: int) -> Optional[List]:
        with Session(self.engine) as session:
            assessment = session.get(AssessmentQA, assessment_id)
            return [assessment.question_text, assessment.is_passed, assessment.user_id] if assessment else None

    def get_expert_by_email(self, email: str) -> Optional[ExpertProfile]:
        with Session(self.engine) as session:
            return session.exec(select(ExpertProfile).where(ExpertProfile.email == email)).first()

    def get_history_by_expert(self, expert_id: int) -> List[AssessmentQA]:
        with Session(self.engine) as session:
            return list(session.exec(select(AssessmentQA).where(AssessmentQA.author_id == expert_id)).all())
    
    def get_expert_by_paper(self, paper_id: str) -> Optional[ExpertProfile]:
        with Session(self.engine) as session:
            stmt = select(ExpertProfile).join(AssessmentQA).where(AssessmentQA.paper_id == paper_id)
            return session.exec(stmt).first()
    
    def store_asked_question(self, question: str, paper_id: str, send_to: str, answer: str | None = None):
        with Session(self.engine) as session:
            asked_q = AskedQuestion(
                question=question,
                paper_id=paper_id,
                answer=answer,
                send_to=send_to
            )
            session.add(asked_q)
            session.commit()
            return asked_q.id
            
    def update_asked_question_answer(self, question_id: str, answer: str):
        with Session(self.engine) as session:
            asked_q = session.exec(select(AskedQuestion).where(AskedQuestion.id == question_id)).first()
            if not asked_q:
                raise Exception("Asked question not found.")
            asked_q.answer = answer
            session.add(asked_q)
            session.commit()