from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class AssessmentQA(SQLModel, table=True):
    __tablename__ = "assessment_qa" # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="expert_profiles.id")
    paper_id: str
    user_id: str
    
    # Merged from Assessment table
    tries: int = Field(default=1, ge=1, le=2)
    question_text: str 
    answer_text: Optional[str] = None
    overall_score: Optional[int] = Field(default=None, ge=0, le=100)
    is_passed: bool = Field(default=False)
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to expert
    author: Optional["ExpertProfile"] = Relationship(back_populates="assessments")

class ExpertProfile(SQLModel, table=True):
    __tablename__ = "expert_profiles" # type: ignore
 
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    title: str
    email: str = Field(unique=True, index=True)
    organization: Optional[str] = None  
    affiliation: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to QA records
    assessments: List["AssessmentQA"] = Relationship(back_populates="author")

class AskedQuestion(SQLModel, table=True):
    __tablename__ = "asked_questions" # type: ignore
 
    id: Optional[int] = Field(default=None, primary_key=True)
    question: str
    answer: Optional[str] = None
    paper_id: str
    send_to: str
    created_at: datetime = Field(default_factory=datetime.utcnow) 