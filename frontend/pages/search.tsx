import { useState } from "react";
import Head from "next/head";
import Link from "next/link";
import { BookOpen, Upload, Search, AlertCircle, CheckCircle, ChevronDown, ChevronUp } from "lucide-react";
import { api, AskResponse, CitedPassage } from "../lib/api";

type AppState = "idle" | "uploading" | "searching" | "done" | "error";

export default function SearchPage() {
  const [pdfUrl, setPdfUrl] = useState("");
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<AppState>("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [graphNodes, setGraphNodes] = useState<number | null>(null);
  const [showTrace, setShowTrace] = useState(false);
  const [ingestedPapers, setIngestedPapers] = useState<string[]>([]);

  const handleIngest = async () => {
    if (!pdfUrl.trim()) return;
    setState("uploading");
    setError("");
    try {
      const job = await api.ingest(pdfUrl);
      // Poll until complete
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const status = await api.getJob(job.job_id);
        if (status.status === "completed") {
          clearInterval(poll);
          setIngestedPapers((prev) => [...prev, pdfUrl]);
          setState("idle");
          setPdfUrl("");
        } else if (status.status === "failed" || attempts > 30) {
          clearInterval(poll);
          setError(status.error || "Ingestion failed");
          setState("error");
        }
      }, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setState("error");
    }
  };

  const handleAsk = async () => {
    if (!question.trim()) return;
    setState("searching");
    setError("");
    setResult(null);
    try {
      const data = await api.ask(question);
      setResult(data);
      const health = await api.health();
      setGraphNodes(health.graph_nodes);
      setState("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setState("error");
    }
  };

  const handleIngestExpertResponse = async () => {
    if (!result?.escalation_card) return;
    const author = result.escalation_card.candidate_authors[0];
    const mockResponse = {
      expert_name: author?.name || "Dr. Expert",
      affiliation: author?.affiliation || "Research Institute",
      response_text: `Based on current evidence, the most effective artemisinin combination therapy (ACT) for children under 5 in high-transmission zones is artemether-lumefantrine (AL). Dosing should be weight-based at 1.7/10 mg/kg twice daily for 3 days. This recommendation is supported by WHO 2023 guidelines.`,
      source_paper_id: result.escalation_card.source_paper_ids[0] || "paper-1",
    };
    await api.ingestExpertResponse(mockResponse);
    // Re-ask same question to show instant answer
    const newResult = await api.ask(question);
    setResult(newResult);
    const health = await api.health();
    setGraphNodes(health.graph_nodes);
  };

  return (
    <>
      <Head><title>Search — LivePaper</title></Head>
      <div className="min-h-screen bg-surface">
        {/* Nav */}
        <nav className="px-8 py-4 bg-white border-b border-gray-100 flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 font-bold text-gray-900">
            <BookOpen size={20} className="text-primary" />
            LivePaper
          </Link>
        </nav>

        <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">

          {/* Ingest panel */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Upload size={18} className="text-primary" /> Upload a Paper
            </h2>
            <div className="flex gap-3">
              <input
                value={pdfUrl}
                onChange={(e) => setPdfUrl(e.target.value)}
                placeholder="Paste a PDF URL (e.g. https://arxiv.org/pdf/...)"
                className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                onClick={handleIngest}
                disabled={state === "uploading" || !pdfUrl.trim()}
                className="px-5 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {state === "uploading" ? "Ingesting..." : "Ingest"}
              </button>
            </div>
            {ingestedPapers.length > 0 && (
              <div className="mt-3 space-y-1">
                {ingestedPapers.map((url, i) => (
                  <p key={i} className="text-xs text-success flex items-center gap-1">
                    <CheckCircle size={12} /> {url}
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Search panel */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Search size={18} className="text-primary" /> Ask a Question
            </h2>
            <div className="flex gap-3">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                placeholder="What is the most effective treatment for malaria in children under 5?"
                className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                onClick={handleAsk}
                disabled={state === "searching" || !question.trim()}
                className="px-5 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {state === "searching" ? "Searching..." : "Ask"}
              </button>
            </div>
          </div>

          {/* Error */}
          {state === "error" && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle size={18} className="text-danger mt-0.5" />
              <p className="text-sm text-danger">{error}</p>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4">
              {/* Passages */}
              {result.passages.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h3 className="font-semibold text-gray-800 mb-4">
                    {result.passages.length} Relevant Passage{result.passages.length > 1 ? "s" : ""} Found
                  </h3>
                  <div className="space-y-4">
                    {result.passages.map((p: CitedPassage, i: number) => (
                      <div key={i} className="border-l-4 border-primary pl-4 py-2">
                        <p className="text-sm text-gray-700 mb-2">{p.text}</p>
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <span className="font-medium">{p.paper_title} — {p.authors.join(", ")}</span>
                          <span className="bg-blue-50 text-primary px-2 py-0.5 rounded-full">
                            {Math.round(p.confidence * 100)}% confident
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Gap detected */}
              {result.escalated && result.escalation_card && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
                  <div className="flex items-start gap-3 mb-4">
                    <AlertCircle size={20} className="text-warning mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-gray-900">Gap Detected</h3>
                      <p className="text-sm text-gray-600 mt-1">{result.escalation_card.gap_description}</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-3">
                    Question sent to <strong>{result.escalation_card.candidate_authors[0]?.name || "domain expert"}</strong>.
                  </p>
                  <button
                    onClick={handleIngestExpertResponse}
                    className="px-4 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Simulate Expert Response
                  </button>
                </div>
              )}

              {/* Graph node counter */}
              {graphNodes !== null && (
                <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between">
                  <span className="text-sm text-gray-600">Knowledge graph nodes</span>
                  <span className="font-bold text-primary text-lg">{graphNodes}</span>
                </div>
              )}

              {/* Trace toggle */}
              <div className="bg-gray-900 rounded-xl p-4">
                <button
                  onClick={() => setShowTrace(!showTrace)}
                  className="flex items-center gap-2 text-gray-300 text-sm font-mono w-full"
                >
                  {showTrace ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  LangFuse Trace
                </button>
                {showTrace && (
                  <div className="mt-3 space-y-1 text-xs font-mono text-green-400">
                    <p>→ retrieval-agent  confidence={result.passages[0]?.confidence?.toFixed(3) ?? "0.000"}  passages={result.passages.length}</p>
                    <p>→ gap-detector     escalate={String(result.escalated)}</p>
                    {result.escalated && <p>→ expert-router    authors={result.escalation_card?.candidate_authors.length ?? 0}</p>}
                    <p className="text-gray-500 mt-2">Full trace → cloud.langfuse.com</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
