import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';
import { BookOpen, CheckCircle, AlertCircle, Loader2, FileText, Users, Send } from 'lucide-react';
import Footer from '@/components/Footer';

interface Author {
    name: string;
    email: string;
}

interface Paper {
    id: string;
    title: string;
    authors: Author[];
    abstract: string;
    paper_url: string;
    pdf_file: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type PageState = 'loading' | 'ready' | 'submitting' | 'success' | 'error';

export default function ExpertResponse() {
    const router = useRouter();
    const { paper_id, expert_email, question_id } = router.query;

    const [paper, setPaper] = useState<Paper | null>(null);
    const [response, setResponse] = useState('');
    const [pageState, setPageState] = useState<PageState>('loading');
    const [fetchError, setFetchError] = useState('');
    const [submitError, setSubmitError] = useState('');

    // Fetch paper details once query params are available
    useEffect(() => {
        if (!router.isReady || !paper_id) return;

        async function fetchPaper() {
            try {
                const res = await fetch(`${API}/api/papers/${paper_id}`);
                if (!res.ok) throw new Error('Paper not found');
                const data = await res.json();
                setPaper(data);
                setPageState('ready');
            } catch (e) {
                setFetchError('We could not find the paper associated with this link. Please contact support.');
                setPageState('error');
            }
        }

        fetchPaper();
    }, [router.isReady, paper_id]);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!response.trim() || !paper || !expert_email) return;

        setPageState('submitting');
        setSubmitError('');

        try {
<<<<<<< HEAD
            const res = await fetch(`${API}/api/paper/answer-question`, {
=======
            const res = await fetch(`${API}/api/expert-responses`, {
>>>>>>> main
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper_id,
                    email: expert_email,
                    question_id,
                    summary: paper.abstract,
                    answer: response.trim(),
                }),
            });

            if (!res.ok) throw new Error('Submission failed');
            setPageState('success');
        } catch {
            setSubmitError('Something went wrong submitting your response. Please try again.');
            setPageState('ready');
        }
    }

    return (
        <>
            <Head>
                <title>Expert Response — LivePaper</title>
                <meta name="description" content="Submit your expert response for a research paper on LivePaper." />
            </Head>

            <div
                className="min-h-screen bg-[#f5f0eb] text-[#2c2217] flex flex-col"
                style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
            >
                {/* Nav — minimal, no auth required */}
                <header className="flex items-center justify-between px-6 py-3 border-b border-[#e0d8cf] bg-[#f5f0eb] shrink-0">
                    <Link href="/" className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-md bg-[#6b1f2a] flex items-center justify-center">
                            <BookOpen className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-[15px] font-semibold tracking-tight">LivePaper</span>
                    </Link>
                    <div
                        className="flex items-center gap-1.5 text-xs text-[#8a7060]"
                        style={{ fontFamily: 'system-ui, sans-serif' }}
                    >
                        <div className="w-1.5 h-1.5 rounded-full bg-[#6b1f2a] opacity-80" />
                        Expert Response
                    </div>
                </header>

                {/* Page content */}
                <main className="flex-1 flex flex-col items-center px-4 py-12">
                    <div className="w-full max-w-2xl">

                        {/* ── Loading ── */}
                        {pageState === 'loading' && (
                            <div className="flex flex-col items-center justify-center py-32 text-[#8a7060]" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                <Loader2 className="w-7 h-7 animate-spin mb-3 text-[#6b1f2a]" />
                                <p className="text-sm">Loading paper details…</p>
                            </div>
                        )}

                        {/* ── Fetch Error ── */}
                        {pageState === 'error' && (
                            <div className="bg-white rounded-2xl border border-[#e0d8cf] p-10 text-center shadow-sm">
                                <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-4" />
                                <h2 className="text-lg font-semibold text-[#2c2217] mb-2">Link Invalid</h2>
                                <p className="text-sm text-[#8a7060] leading-relaxed" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                    {fetchError}
                                </p>
                            </div>
                        )}

                        {/* ── Success ── */}
                        {pageState === 'success' && (
                            <div className="bg-white rounded-2xl border border-[#e0d8cf] p-10 text-center shadow-sm">
                                <div className="w-16 h-16 rounded-full bg-[#f5f0eb] border-2 border-[#6b1f2a] flex items-center justify-center mx-auto mb-6">
                                    <CheckCircle className="w-8 h-8 text-[#6b1f2a]" />
                                </div>
                                <h2 className="text-2xl font-bold text-[#2c2217] mb-3">
                                    Thank you for your response!
                                </h2>
                                <p className="text-[#5a4535] leading-relaxed mb-2" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                    Your expert insight has been received and will be reviewed by our team.
                                </p>
                                <p className="text-sm text-[#8a7060] leading-relaxed" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                    Your contribution helps researchers around the world get accurate,
                                    authoritative answers. We appreciate you taking the time to share
                                    your expertise.
                                </p>
                                <div className="mt-8 pt-6 border-t border-[#e0d8cf]">
                                    <p className="text-xs text-[#b0a090]" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                        Response submitted for{' '}
                                        <span className="font-medium text-[#5a4535]">{expert_email}</span>
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* ── Form ── */}
                        {(pageState === 'ready' || pageState === 'submitting') && paper && (
                            <>
                                {/* Page heading */}
                                <div className="mb-8">
                                    <div
                                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#d4c8bc] bg-white text-[#8a7060] text-xs mb-4"
                                        style={{ fontFamily: 'system-ui, sans-serif' }}
                                    >
                                        <div className="w-1.5 h-1.5 rounded-full bg-[#6b1f2a]" />
                                        Expert Review Request
                                    </div>
                                    <h1 className="text-2xl font-bold text-[#2c2217] leading-snug">
                                        Share your expertise on this paper
                                    </h1>
                                    <p
                                        className="text-sm text-[#8a7060] mt-2 leading-relaxed"
                                        style={{ fontFamily: 'system-ui, sans-serif' }}
                                    >
                                        A researcher has a question about the paper below.
                                        Please share your expert perspective — your response will be
                                        attributed to you and added to our knowledge base.
                                    </p>
                                </div>

                                <form onSubmit={handleSubmit} className="space-y-5">

                                    {/* Paper details card — read only */}
                                    <div className="bg-white rounded-2xl border border-[#e0d8cf] overflow-hidden shadow-sm">
                                        <div className="px-5 py-3.5 border-b border-[#e0d8cf] bg-[#faf7f4] flex items-center gap-2">
                                            <FileText className="w-3.5 h-3.5 text-[#6b1f2a]" />
                                            <span
                                                className="text-xs font-semibold text-[#8a7060] uppercase tracking-wider"
                                                style={{ fontFamily: 'system-ui, sans-serif' }}
                                            >
                                                Paper Details
                                            </span>
                                        </div>

                                        <div className="px-5 py-5 space-y-4">
                                            {/* Title */}
                                            <div>
                                                <label
                                                    className="block text-[10px] font-semibold text-[#8a7060] uppercase tracking-widest mb-1.5"
                                                    style={{ fontFamily: 'system-ui, sans-serif' }}
                                                >
                                                    Title
                                                </label>
                                                <p className="text-[15px] font-semibold text-[#2c2217] leading-snug">
                                                    {paper.title}
                                                </p>
                                            </div>

                                            {/* Authors */}
                                            {paper.authors?.length > 0 && (
                                                <div>
                                                    <label
                                                        className="block text-[10px] font-semibold text-[#8a7060] uppercase tracking-widest mb-1.5 flex items-center gap-1"
                                                        style={{ fontFamily: 'system-ui, sans-serif' }}
                                                    >
                                                        <Users className="w-3 h-3" /> Authors
                                                    </label>
                                                    <div className="flex flex-wrap gap-2">
                                                        {paper.authors.map((author, i) => (
                                                            <div
                                                                key={i}
                                                                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#faf7f4] border border-[#e0d8cf] text-sm"
                                                                style={{ fontFamily: 'system-ui, sans-serif' }}
                                                            >
                                                                <span className="font-medium text-[#2c2217]">{author.name}</span>
                                                                {author.email && (
                                                                    <span className="text-[#8a7060] text-xs">· {author.email}</span>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Responding as */}
                                            <div className="pt-1 border-t border-[#f0e8e0]">
                                                <label
                                                    className="block text-[10px] font-semibold text-[#8a7060] uppercase tracking-widest mb-1"
                                                    style={{ fontFamily: 'system-ui, sans-serif' }}
                                                >
                                                    Responding as
                                                </label>
                                                <p
                                                    className="text-sm text-[#5a4535] font-medium"
                                                    style={{ fontFamily: 'system-ui, sans-serif' }}
                                                >
                                                    {expert_email}
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Response textarea */}
                                    <div className="bg-white rounded-2xl border border-[#e0d8cf] overflow-hidden shadow-sm">
                                        <div className="px-5 py-3.5 border-b border-[#e0d8cf] bg-[#faf7f4] flex items-center gap-2">
                                            <Send className="w-3.5 h-3.5 text-[#6b1f2a]" />
                                            <span
                                                className="text-xs font-semibold text-[#8a7060] uppercase tracking-wider"
                                                style={{ fontFamily: 'system-ui, sans-serif' }}
                                            >
                                                Your Expert Response
                                            </span>
                                        </div>

                                        <div className="px-5 py-4">
                                            <textarea
                                                value={response}
                                                onChange={e => setResponse(e.target.value)}
                                                placeholder="Share your expert insights, clarifications, or additional context about this paper. Be as detailed as you'd like — your response will help researchers around the world."
                                                required
                                                rows={10}
                                                disabled={pageState === 'submitting'}
                                                className="w-full text-[15px] text-[#2c2217] placeholder-[#c0b0a0] bg-transparent resize-none focus:outline-none leading-relaxed disabled:opacity-60"
                                                style={{ fontFamily: "'Georgia', serif" }}
                                            />
                                            <div
                                                className="flex items-center justify-between pt-3 border-t border-[#f0e8e0] mt-2"
                                                style={{ fontFamily: 'system-ui, sans-serif' }}
                                            >
                                                <span className="text-xs text-[#b0a090]">
                                                    {response.length > 0 && `${response.length} characters`}
                                                </span>
                                                <span className="text-xs text-[#b0a090]">
                                                    Markdown supported
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Submit error */}
                                    {submitError && (
                                        <div
                                            className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm"
                                            style={{ fontFamily: 'system-ui, sans-serif' }}
                                        >
                                            <AlertCircle className="w-4 h-4 shrink-0" />
                                            {submitError}
                                        </div>
                                    )}

                                    {/* Submit button */}
                                    <button
                                        type="submit"
                                        disabled={!response.trim() || pageState === 'submitting'}
                                        className="w-full py-3.5 rounded-xl bg-[#6b1f2a] text-white font-semibold text-[15px] hover:bg-[#4e1520] active:scale-[0.99] transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2 shadow-sm"
                                        style={{ fontFamily: 'system-ui, sans-serif' }}
                                    >
                                        {pageState === 'submitting' ? (
                                            <>
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                                Submitting…
                                            </>
                                        ) : (
                                            <>
                                                <Send className="w-4 h-4" />
                                                Submit Expert Response
                                            </>
                                        )}
                                    </button>

                                    <p
                                        className="text-center text-xs text-[#b0a090] pb-4"
                                        style={{ fontFamily: 'system-ui, sans-serif' }}
                                    >
                                        By submitting, you agree your response may be shared with researchers using LivePaper.
                                    </p>
                                </form>
                            </>
                        )}
                    </div>
                </main>

                {/* Footer */}
                <Footer />
            </div>
        </>
    );
}