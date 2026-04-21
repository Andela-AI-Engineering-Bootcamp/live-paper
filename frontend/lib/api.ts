import { API_URL } from "./config";

export interface CitedPassage {
  text: string;
  paper_title: string;
  authors: string[];
  page?: number;
  confidence: number;
}

export interface EscalationCard {
  question: string;
  gap_description: string;
  candidate_authors: { name: string; affiliation?: string; relevance_score: number }[];
  source_paper_ids: string[];
  generated_at: string;
}

export interface AskResponse {
  question: string;
  passages: CitedPassage[];
  escalated: boolean;
  escalation_card?: EscalationCard;
}

export interface IngestResponse {
  job_id: string;
  status: string;
  message: string;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export const api = {
  ingest: (pdf_url: string) =>
    post<IngestResponse>("/api/papers/ingest", { pdf_url }),

  getJob: (job_id: string) =>
    get<{ job_id: string; status: string; result?: unknown; error?: string }>(
      `/api/papers/jobs/${job_id}`
    ),

  ask: (question: string, paper_ids?: string[]) =>
    post<AskResponse>("/api/search/ask", { question, paper_ids }),

  ingestExpertResponse: (response: {
    expert_name: string;
    affiliation?: string;
    response_text: string;
    source_paper_id: string;
  }, question: string) =>
    post("/api/escalation/respond", response),

  health: () => get<{ status: string; graph_nodes: number }>("/api/health"),
};
