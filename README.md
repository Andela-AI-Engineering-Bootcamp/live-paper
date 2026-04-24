# LivePaper

> Research papers, made answerable. Every paper, live. Every expert, reachable.

**Andela AI Engineering Bootcamp — Capstone 2025**

### Live deployment

| Endpoint | URL |
|---|---|
| Frontend | [https://d1xrrwd5ltx7wh.cloudfront.net](https://d1xrrwd5ltx7wh.cloudfront.net) (CloudFront → S3 static export) |
| Backend API | [https://tdiwu3dznt.us-east-1.awsapprunner.com](https://tdiwu3dznt.us-east-1.awsapprunner.com) (App Runner) |
| Health check | `GET /api/health` → `{"status":"ok","service":"livepaper-api","graph_nodes":0}` |

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
| **Aurora Serverless v2** | (provisioned) Papers, jobs, experts, chat history, escalation audit trail. *Currently the API still uses in-memory dicts in `app/api/papers.py` for the MVP loop — Aurora schema is deployed and reachable, full ORM wire-up is the next step.* |
| **Neo4J** | (optional) Knowledge graph — Paper → Concept, Paper → ExpertResponse relationships. App falls back to a no-op when `NEO4J_URI` is empty. |
| **S3 Vectors** | 384-dim `all-MiniLM-L6-v2` embeddings, mean-pooled from token outputs. Bucket `livepaper-vectors`, index `papers`. |

### LLM and Embeddings

| Component | Implementation |
|---|---|
| **LLM** (extraction, retrieval reasoning, expert routing) | **Amazon Nova Pro** via Bedrock, called through `LiteLLM` with the cross-region inference profile `us.amazon.nova-pro-v1:0`. The App Runner task role is granted `bedrock:InvokeModel` on the profile ARN in `us-east-1 / us-east-2 / us-west-2` plus the underlying foundation-model ARN in each. |
| **Embeddings** | `all-MiniLM-L6-v2` on a SageMaker Serverless endpoint. The `livepaper-embedding-endpoint` resource is left as a Terraform stub (deploying it requires `iam:PassRole` on the operator); production currently calls the existing `alex-embedding-endpoint` in the same account, mean-pooling the token-level Hugging Face output into a single 384-dim sentence vector. |

---

## Running Locally

No AWS credentials needed — every service has a dev fallback.

### Backend

```bash
cd backend
pip install ".[dev]"

# Copy and edit env (all AWS vars can stay empty for dev)
cp ../.env.example .env

pytest          # unit + integration suites, all green
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

`OPENAI_API_KEY` is the only secret hard-required when `DEBUG=false` (see `app/core/config.py`). Everything else degrades gracefully:

| Env var empty | What happens |
|---|---|
| `AURORA_CLUSTER_ARN` / `AURORA_HOST` | SQLite (`aiosqlite`) in-memory database |
| `VECTOR_BUCKET` | Cosine search over an in-memory dict |
| `SAGEMAKER_ENDPOINT` | Local `sentence-transformers` if installed, otherwise a zero vector (which S3 Vectors will reject — only safe in tests with `VECTOR_BUCKET=""`) |
| `NEO4J_URI` | No-op logger (graph writes silently skipped) |
| `LANGFUSE_PUBLIC_KEY` | Tracing disabled, app runs normally |
| `BEDROCK_MODEL_ID` | LiteLLM falls back to `gpt-4o-mini` (requires `OPENAI_API_KEY`) |
| `CORS_ORIGINS` | Defaults to `http://localhost:3000` only |

---

## Deployment

### Infrastructure (Terraform)

State lives in S3 (`s3://livepaper-terraform-state-...`). All commands run from `infra/`:

```bash
cd infra
terraform init -reconfigure
terraform apply \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="langfuse_public_key=$LANGFUSE_PUBLIC_KEY" \
  -var="langfuse_secret_key=$LANGFUSE_SECRET_KEY"
```

Secrets are written to AWS Secrets Manager once at create time and then ignored on subsequent applies (`lifecycle { ignore_changes = [secret_string] }`), so omitting `-var` flags on later runs **will not blank out** existing secrets — rotate them out-of-band with `aws secretsmanager put-secret-value`.

Provisions:
- VPC data sources (default VPC) + Aurora Serverless v2 cluster (publicly accessible, ingress restricted to App Runner's published egress IP ranges + the App Runner SG)
- ECR repository, App Runner service (DEFAULT egress, HTTP `/api/health` health check), task and access IAM roles
- S3 bucket + CloudFront distribution for the frontend (Origin Access Control)
- S3 bucket for raw PDF storage; S3 Vectors policy granting the task role read/write to `livepaper-vectors`
- SQS queues (`ingestion`, `escalation`) with DLQs
- Secrets Manager entries for OpenAI / LangFuse / Neo4J
- Bedrock IAM policy covering both the inference profile and the underlying foundation-model ARNs in `us-east-1 / us-east-2 / us-west-2`
- SageMaker IAM policy granting `InvokeEndpoint` on `livepaper-embedding-endpoint` *and* `alex-embedding-endpoint` (the latter is what's actually wired in production)
- IAM user + access key for the GitHub Actions CI pipeline (ECR push + S3 deploy + CloudFront invalidation)

The S3 Vectors bucket and its `papers` index are created out-of-band via `aws s3vectors create-vector-bucket` / `create-index` because the AWS Terraform provider does not yet expose those resources.

Outputs after apply:

```bash
terraform output frontend_url            # https://d1xrrwd5ltx7wh.cloudfront.net
terraform output backend_url             # https://tdiwu3dznt.us-east-1.awsapprunner.com
terraform output ecr_repository_url      # 375510692572.dkr.ecr.us-east-1.amazonaws.com/livepaper-backend
terraform output frontend_bucket         # livepaper-frontend-375510692572
terraform output cloudfront_distribution_id
```

### Backend image

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 375510692572.dkr.ecr.us-east-1.amazonaws.com

cd backend
docker build --platform linux/amd64 \
  -t 375510692572.dkr.ecr.us-east-1.amazonaws.com/livepaper-backend:latest .
docker push 375510692572.dkr.ecr.us-east-1.amazonaws.com/livepaper-backend:latest
```

App Runner has `auto_deployments_enabled = true`, so a push to `:latest` triggers a rolling deploy. Watch with:

```bash
aws apprunner list-services --region us-east-1 \
  --query 'ServiceSummaryList[?ServiceName==`livepaper-backend`].Status' --output text
```

### Frontend

```bash
cd frontend
cat > .env.local <<EOF
NEXT_PUBLIC_API_URL=$(cd ../infra && terraform output -raw backend_url)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...
CLERK_SECRET_KEY=...
EOF

npm ci
npm run build                                                           # produces frontend/out/
aws s3 sync out s3://$(cd ../infra && terraform output -raw frontend_bucket) --delete
aws cloudfront create-invalidation \
  --distribution-id $(cd ../infra && terraform output -raw cloudfront_distribution_id) \
  --paths "/*"
```

### CI/CD

`.github/workflows/deploy.yml` is wired up to do all of the above on push to `main`:

1. Backend `pytest` (uses the dev fallbacks — `VECTOR_BUCKET=""`, `NEO4J_URI=""`, `SAGEMAKER_ENDPOINT=""`)
2. Frontend `npm run type-check`
3. Docker build → push to ECR with both `:latest` and `:git-<sha>` tags (App Runner auto-deploys)
4. `npm run build` → `s3 sync` → CloudFront invalidation
5. `/api/health` smoke test (10 retries × 15s)

Required GitHub repo secrets:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | `terraform output ci_access_key_id` / `ci_secret_access_key` (the IAM user Terraform provisioned) |
| `BACKEND_URL` | `terraform output backend_url` |
| `FRONTEND_BUCKET` | `terraform output frontend_bucket` |
| `CLOUDFRONT_DISTRIBUTION_ID` | `terraform output cloudfront_distribution_id` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` / `CLERK_SECRET_KEY` | Clerk dashboard |

> **Status:** the workflow file is committed but the current production deploy was run manually with the commands above (CI secrets not yet wired). Wiring them is a one-time setup.

---

## API Reference

All endpoints are served at `http://localhost:8000` in dev, and at `https://tdiwu3dznt.us-east-1.awsapprunner.com` in production.
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

## Production Runtime

### App Runner environment

The container runs `uvicorn app.main:app --workers 1` (single worker — the in-memory `_jobs` / `_papers` dicts in `app/api/papers.py` would otherwise diverge across worker processes; this goes away when the API is wired to Aurora). Notable env vars set by Terraform:

| Variable | Value | Purpose |
|---|---|---|
| `DEBUG` | `false` | Enables prod validators in `app/core/config.py` |
| `CORS_ORIGINS` | `https://<cloudfront-domain>,http://localhost:3000` | Allow the deployed frontend (and dev) to call the API |
| `BEDROCK_MODEL_ID` | `us.amazon.nova-pro-v1:0` | Cross-region inference profile used by LiteLLM |
| `BEDROCK_REGION` | `us-west-2` | LiteLLM region hint (the inference profile may route elsewhere) |
| `SAGEMAKER_ENDPOINT` | `alex-embedding-endpoint` | Embedding endpoint (see Architecture → LLM and Embeddings) |
| `VECTOR_BUCKET` | `livepaper-vectors` | S3 Vectors bucket name |
| `VECTOR_INDEX` | `papers` | Required by `s3vectors:PutVectors` / `QueryVectors` |
| `AURORA_CLUSTER_ARN` / `AURORA_HOST` / `AURORA_PORT` / `AURORA_DATABASE` / `AURORA_USERNAME` | from Aurora outputs | DB connection |
| `AURORA_PASSWORD` | injected from Secrets Manager | Aurora's managed master-user password is JSON-encoded; `app/services/database.py:_resolve_password()` parses it before handing to asyncpg |
| `OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | Secrets Manager | Application secrets |

### Networking

- App Runner uses `egress_type = "DEFAULT"` (public egress over the App Runner service network) so it can reach OpenAI / Bedrock / LangFuse without a NAT gateway.
- Aurora is `publicly_accessible = true` but its security group only ingresses on 5432/tcp from (a) the App Runner SG and (b) App Runner's currently published egress CIDR ranges (fetched dynamically via `data "aws_ip_ranges" "apprunner"`).
- TLS terminates at CloudFront (frontend) and the App Runner service URL (backend).

### Health check

App Runner's HTTP health check hits `/api/health` every 10 seconds. The endpoint also reports `graph_nodes` (Neo4J node count) so degradation in the optional graph store surfaces in the response.

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
