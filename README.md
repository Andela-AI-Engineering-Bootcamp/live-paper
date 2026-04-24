# LivePaper

> Research papers, made answerable. Every paper, live. Every expert, reachable.

**Andela AI Engineering Bootcamp — Capstone 2025**

Live demo → **`terraform output frontend_url`** *(available after `terraform apply`)*

---

## The Problem

You read a paper abstract, invest hours (and money behind a paywall), and leave with *more* questions than you started with. The authors who could answer them are unreachable.

## The Solution

LivePaper turns static research papers into live documents. Ask a question — get cited answers from every ingested paper simultaneously. When no paper has the answer, LivePaper routes your question directly to the author in real time. Their response is added to the knowledge base, making every future answer smarter.

---

## Architecture

```
                      ┌─────────────────────────────────┐
                      │         Next.js Frontend         │
                      │  Landing · Search · Trace Panel  │
                      └────────────────┬────────────────┘
                                       │ REST
                      ┌────────────────▼────────────────┐
                      │        FastAPI Backend           │
                      │  /ingest  /ask  /expert-response │
                      └──┬──────────┬──────────┬────────┘
                         │          │          │
              ┌──────────▼──┐  ┌────▼────┐  ┌─▼──────────────┐
              │  Ingestion  │  │Retrieval│  │  Expert Router  │
              │    Agent    │  │  Agent  │  │     Agent       │
              └──────┬──────┘  └────┬────┘  └────────┬───────┘
                     │              │                 │
        ┌────────────▼──────────────▼─────────────────▼──────┐
        │                    Storage Layer                     │
        │  Aurora Serverless v2  ·  Neo4J  ·  S3 Vectors      │
        └─────────────────────────────────────────────────────┘
```

### Five Agents

| Agent | Role |
|---|---|
| **Ingestion** | Downloads PDF, extracts title/authors/concepts/findings via LLM, writes embeddings to S3 Vectors and concept nodes to Neo4J |
| **Retrieval** | Embeds the question, runs cosine search, returns ranked `CitedPassage` list with confidence scores |
| **Gap Detector** | Decides if top confidence < threshold → escalate to expert |
| **Expert Router** | Generates a structured `EscalationCard` with candidate authors identified from paper metadata |
| **Response Ingestion** | Parses expert reply, embeds it, writes `ExpertResponse` node to Neo4J — future queries answer instantly |

### Storage Tiers

| Store | What lives here |
|---|---|
| **Aurora Serverless v2** | Papers, jobs, experts, chat history, escalation audit trail |
| **Neo4J** | Knowledge graph — Paper → Concept, Paper → ExpertResponse relationships |
| **S3 Vectors** | 384-dim all-MiniLM-L6-v2 embeddings for semantic search |

---

## Running Locally

No AWS credentials needed — every service has a dev fallback.

### Backend

```bash
cd backend
pip install ".[dev]"

# Copy and edit env (all AWS vars can stay empty for dev)
cp ../.env.example .env

pytest          # 14 tests, all green
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev     # → http://localhost:3000
```

### Dev Fallbacks

| Env var empty | What happens |
|---|---|
| `AURORA_CLUSTER_ARN` | SQLite in-memory database |
| `VECTOR_BUCKET` | Cosine search over in-memory store |
| `SAGEMAKER_ENDPOINT` | Local `sentence-transformers` model |
| `NEO4J_URI` | No-op logger (graph writes silently skipped) |
| `LANGFUSE_PUBLIC_KEY` | Tracing disabled, app runs normally |

---

## Deployment

### Infrastructure (Terraform)

```bash
cd infra
terraform init
terraform apply \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="langfuse_public_key=$LANGFUSE_PUBLIC_KEY" \
  -var="langfuse_secret_key=$LANGFUSE_SECRET_KEY"
```

Provisions: SQS queues · Aurora Serverless v2 · SageMaker Serverless endpoint · S3 Vectors bucket · ECR repository · App Runner service · Secrets Manager

### CI/CD

Every push to `main` triggers:
1. Backend pytest (14 tests)
2. Frontend `tsc --noEmit`
3. Docker build → push to ECR → App Runner (backend)
4. `next build` → S3 sync → CloudFront cache invalidation (frontend)
5. `/api/health` smoke test

Add these secrets in **GitHub → Settings → Secrets → Actions**:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user with ECR + App Runner + S3 + CloudFront permissions |
| `AWS_SECRET_ACCESS_KEY` | — |
| `BACKEND_URL` | `terraform output backend_url` |
| `FRONTEND_BUCKET` | `terraform output frontend_bucket` |
| `CLOUDFRONT_DISTRIBUTION_ID` | `terraform output cloudfront_distribution_id` |

---

## API Reference

All endpoints are served at `http://localhost:8000` in dev, and at the App Runner URL in production.
Set `NEXT_PUBLIC_API_URL` in the frontend `.env.local` to point to the right backend.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/papers/ingest` | Ingest a paper — accepts `pdf_url` (form), file upload, or `title` + `abstract` |
| `GET` | `/api/papers/jobs/{job_id}` | Poll ingestion job status — `pending / running / completed / failed` |
| `GET` | `/api/papers` | List all papers |
| `PUT` | `/api/papers/{id}` | Update a paper |
| `DELETE` | `/api/papers/{id}` | Delete a paper |
| `POST` | `/api/search/ask` | Ask a question — returns cited passages and escalation card if gap detected |
| `POST` | `/chat` | Multi-turn chat with session history — `{ message, session_id? }` |
| `GET` | `/api/experts` | List all experts |
| `GET` | `/api/experts/{id}` | Get a single expert |
| `POST` | `/api/escalation/respond` | Submit an expert response |
| `GET` | `/api/health` | Health check — returns `{ status, graph_nodes }` |

Interactive docs available at `/docs` in debug mode.

---

## Observability

All five agents are instrumented with LangFuse. Every request produces:
- A root trace with agent name, input, and output
- Child spans per pipeline step (embed → search → rank → threshold)
- Confidence scores recorded as LangFuse metrics
- Trace IDs returned in API responses and displayed in the UI trace panel

View live traces → [cloud.langfuse.com](https://cloud.langfuse.com)

---

## Team

| Name | Role |
|---|---|
| **Stella** | Infrastructure — Terraform, Aurora schema, SQS, SageMaker, LangFuse tracing, CI/CD |
| **Niskan** | Agents — Ingestion Agent (PDF → LLM extraction → Neo4J + S3 Vectors) |
| **Adetayo** | Backend — Gap Detector, Expert Router, Response Ingestion Agent |
| **Seun** | Frontend — Search UI, cited passage display, LangFuse trace panel |

---

## Tech Stack

**AI:** OpenAI Agents SDK · LiteLLM → Amazon Nova Pro (Bedrock) · all-MiniLM-L6-v2 (SageMaker)

**Backend:** FastAPI · SQLAlchemy async · Alembic · Neo4J · LangFuse

**Frontend:** Next.js 15 · Tailwind CSS · TypeScript

**Infrastructure:** AWS App Runner · Aurora Serverless v2 · S3 Vectors · SageMaker Serverless · SQS · ECR · Terraform
