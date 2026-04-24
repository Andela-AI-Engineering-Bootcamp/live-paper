# Academic Vetting API

This API provides endpoints for academic assessment, question submission, and expert Q&A workflows.

## Endpoints

### 1. Start Assessment
- **POST** `/assessment/start`
- **Request Body:**
```json
{
  "name": "John Doe",
  "title": "Professor",
  "email": "john@example.com",
  "organization": "University X",
  "affiliation": "Department Y",
  "paper_id": "123456",
  "summary": "A summary of the research paper."
}
```
- **Response:** `{ "assessment_id": int, "questions": ["..."] }`

---

### 2. Submit Assessment Answers
- **POST** `/assessment/submit`
- **Request Body:**
```json
{
  "assessment_id": 1,
  "user_answers": ["Answer 1", "Answer 2", "Answer 3"],
  "summary": "A summary of the research paper."
}
```
- **Response:** `{ "score": int, "passed": bool, "feedback": str, "full_report": ["..."] }`

---

### 3. Ask a Question About a Paper
- **POST** `/paper/ask-question`
- **Request Body:**
```json
{
  "paper_id": "123456",
  "summary": "A summary of the research paper.",
  "question": "What is the main contribution?"
}
```
- **Response:** `{ "detail": str }`

---

### 4. Answer a Question About a Paper
- **POST** `/paper/answer-question`
- **Request Body:**
```json
{
  "question": "What is the main contribution?",
  "question_id": "789",
  "summary": "A summary of the research paper.",
  "answer": "The main contribution is..."
}
```
- **Response:** `{ "detail": str }`

---

## Notes
- All endpoints return JSON.
- The assessment workflow enforces a maximum of 2 attempts per paper per user.
- Email notifications are sent to experts for new questions and successful assessments.
- For more details, see the code and docstrings in each endpoint.
