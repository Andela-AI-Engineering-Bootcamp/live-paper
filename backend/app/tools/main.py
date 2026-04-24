import os
import re
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from openai import OpenAI  
from dotenv import load_dotenv
 
from research_vetter import ResearchVetter
from database_manager import DatabaseManager

load_dotenv()

app = FastAPI(title="Academic Vetting API")

# --- Pydantic Models ---
class AssessmentRequest(BaseModel): 
    name: str
    title: str
    email: str
    organization: Optional[str] = None
    affiliation: Optional[str] = None
    paper_id: str
    summary: str

class SubmissionRequest(BaseModel):
    assessment_id: int
    user_answers: List[str]
    summary: str

class QuestionRequest(BaseModel):
    paper_id: str
    summary: str
    question: str

class AnswerQuestionRequest(BaseModel):
    question: str 
    question_id: str 
    summary: str
    answer: str

# --- Dependency Injection ---
# Initialize DB Manager as a singleton
db_manager = DatabaseManager()

def get_vetter():
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("Warning: OPENAI_API_KEY is not set.")
    llm_client = OpenAI(api_key=api_key)
    return ResearchVetter(llm_client=llm_client)

# --- API Endpoints ---

@app.post("/assessment/start")
async def start_assessment(
    req: AssessmentRequest, 
    vetter: ResearchVetter = Depends(get_vetter)
):
    """
    Step 1: Create expert, generate questions, and initialize the assessment record.
    """
    try:
        # 1. Get or Create Expert Profile
        expert = db_manager.get_expert_by_email(req.email)
        if expert is None:
            expert = db_manager.create_expert(
                name=req.name,
                title=req.title,
                email=req.email,
                organization=req.organization,
                affiliation=req.affiliation
            )
        
        if not expert.id:
            raise HTTPException(status_code=500, detail="Expert profile could not be verified.")

        # 2. Generate questions via LLM first (to ensure we have them before DB entry)
        get_question: Optional[List] = db_manager.get_questions_by_paper_id(req.paper_id, req.email)
        assessment_id = None
        if get_question is not None:
            questions = get_question[0].split("\n") # type: ignore
            assessment_id = get_question[1] # type: ignore
            
            if get_question[2]: 
                return HTTPException(status_code=200, detail="This paper has already been passed in a previous attempt.")
            
        else:
            questions = vetter.generate_assessment_questions(
                req.title, req.summary, db_manager, req.paper_id, req.email
            )
            # 3. Create/Retrieve record in AssessmentQA (handles the 2-try limit logic)
            assessment_id = db_manager.start_new_assessment(
                author_id=expert.id,
                paper_id=req.paper_id,
                user_id=req.email,
                questions=questions
            )

        return HTTPException(status_code=200, detail= {
            "assessment_id": assessment_id,
            "questions": questions
        })
    except Exception as e:
        print(f"Error in start_assessment: {e}")
        # Return the actual exception message if it's our "Max tries" limit
        detail = str(e) if "Maximum number of tries" in str(e) else "Failed to initialize assessment."
        raise HTTPException(status_code=400, detail=detail)

@app.post("/assessment/submit")
async def submit_assessment(
    req: SubmissionRequest, 
    vetter: ResearchVetter = Depends(get_vetter)
):
    """
    Step 2: User submits answers. We score them and update the single QA record.
    """
    try:
        # 1. Retrieve the question text for this assessment
        questions_block = db_manager.get_questions_by_id(req.assessment_id)
        if not questions_block:
            raise HTTPException(status_code=404, detail="Assessment not found.")

        if questions_block[1]:
            return HTTPException(status_code=200, detail="You have already passed this assessment.")
        
        questions_list = questions_block[0].split("\n")
        
        # 2. Combine answers into a single string for storage if needed, 
        # but vetter usually takes the list and user summary.
        full_answer_text = "\n".join(req.user_answers)

        # 3. Verify and Score via LLM
        results = vetter.verify_multiple_answers(questions_list, req.user_answers, req.summary)

        # 4. Update the combined record
        db_manager.update_results(
            assessment_id=req.assessment_id, 
            results=results, 
            answer_text=full_answer_text
        )
        
        if results.get('passed'):
            email_template = os.path.join(os.path.dirname(__file__), "email_templates", "welcome_researcher_email.html")
            with open(email_template, 'r') as f:
                email_content = f.read()
                vetter.send_mail_notification(questions_block[2], "Paper Passed", email_content)

        # Cleanup whitespace for cleaner JSON response
        feedback = re.sub(r'\n\s*\n', '\n\n', results.get('feedback', '').strip()) 
        
        return {
            "score": results.get('score'),
            "passed": results.get('passed'),
            "feedback": feedback,
            "full_report": results.get('full_report', '').strip().split("\n")
        }
    except Exception as e:
        print(f"Error in submit_assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/paper/ask-question")
async def ask_question(
    req: QuestionRequest,  
    vetter: ResearchVetter = Depends(get_vetter)
):
    """
    Step 3: User asks a question about the paper. We store it and can optionally have the LLM answer it.
    """
    try:
        check_relevance = vetter.check_question_is_relevant(req.question, req.summary)
        if not check_relevance:
            return {"detail": "Your question does not seem relevant to the paper's content. Please ask a question related to the paper."}
        
        get_expert = db_manager.get_expert_by_paper(req.paper_id)
        print(get_expert)
        if not get_expert:
            raise HTTPException(status_code=400, detail="We would not be able to answer your question at the moment as we could not find an expert associated with this paper.")
        
        id = db_manager.store_asked_question(
            question=req.question, 
            paper_id=req.paper_id,
            send_to=get_expert.email
        )
        if not id:
            raise HTTPException(status_code=500, detail="Failed to store your question. Please try again later.")
        
        # https://d1xrrwd5ltx7wh.cloudfront.net/expert-response?paper_id=abc123&expert_email=expert@university.edu?id=456
        answer_url = f"https://d1xrrwd5ltx7wh.cloudfront.net/expert-response?paper_id={req.paper_id}&expert_email={get_expert.email}&question_id={id}"
        html_body = f"""
        <html>
        <body>
            <p>Dear {get_expert.name},</p>
            <p>You have received a new question about the paper <b>{req.paper_id}</b>:</p>
            <blockquote style='background:#f9f9f9;border-left:5px solid #ccc;margin:1em 0;padding:1em;'>{req.question}</blockquote>
            <p>Please click the button below to log in and answer this question:</p>
            <p>
                <a href="{answer_url}" style="display:inline-block;padding:10px 20px;background:#007bff;color:#fff;text-decoration:none;border-radius:5px;font-weight:bold;">Answer Question</a>
            </p>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p><a href="{answer_url}">{answer_url}</a></p>
            <br>
            <p>Best regards,<br>Research Assessment Team</p>
        </body>
        </html>
        """
        vetter.send_question_email(
            email=get_expert.email,
            subject=f"New Question about Paper {req.paper_id}",
            body=html_body
        )
        return {"detail": "Your question has been received. An expert will get back to you soon."}
    except Exception as e:
        print(f"Error in ask_question: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit your question.")

@app.post("/paper/answer-question")
async def answer_question(
    req: AnswerQuestionRequest,  
    vetter: ResearchVetter = Depends(get_vetter)
):
    """
    Step 3: User answers a question about the paper. We store it and can optionally have the LLM answer it.
    """
    try:
        context = f"Summary {req.summary} \n\nQuestion: {req.question}\n\nAnswer: {req.answer}"
        check_relevance = vetter.check_question_is_relevant(req.answer, context)
        if not check_relevance:
            return {"detail": "Your answer does not seem relevant to the paper's content. Please provide an answer related to the paper and question asked."}
         
        db_manager.update_asked_question_answer(
            question_id=req.question_id,  
            answer=req.answer
        )
        return {"detail": "Your answer has been recorded successfully."}
    except Exception as e:
        print(f"Error in answer_question: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit your answer.")