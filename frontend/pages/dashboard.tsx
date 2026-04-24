"use client"

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useUser, UserButton } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import {
    BookOpen, Plus, Trash2, Pencil, X, ExternalLink,
    FileText, Users, ChevronRight, AlertCircle, Loader2
} from 'lucide-react';
import Footer from '../components/Footer';

interface Paper {
    id: string;
    title: string;
    authors: string;
    abstract: string;
    paper_url: string;
    pdf_file: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const emptyForm = { title: '', authors: '', abstract: '', paper_url: '', pdf_file: '' };

export default function AdminDashboard() {
    const { user, isLoaded } = useUser();
    const router = useRouter();

    const [papers, setPapers] = useState<Paper[]>([]);
    const [loading, setLoading] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    const [editingPaper, setEditingPaper] = useState<Paper | null>(null);
    const [form, setForm] = useState(emptyForm);
    const [submitting, setSubmitting] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [error, setError] = useState('');

    // Guard: only admins
    useEffect(() => {
        if (isLoaded && user?.publicMetadata?.role !== 'admin') {
            router.replace('/');
        }
    }, [isLoaded, user, router]);

    useEffect(() => {
        fetchPapers();
    }, []);

    async function fetchPapers() {
        setLoading(true);
        try {
            const res = await fetch(`${API}/api/papers`);
            const data = await res.json();
            setPapers(data);
        } catch {
            setError('Failed to load papers.');
        } finally {
            setLoading(false);
        }
    }

    function openAdd() {
        setEditingPaper(null);
        setForm(emptyForm);
        setModalOpen(true);
    }

    function openEdit(paper: Paper) {
        setEditingPaper(paper);
        setForm({
            title: paper.title,
            authors: paper.authors,
            abstract: paper.abstract,
            paper_url: paper.paper_url,
            pdf_file: paper.pdf_file,
        });
        setModalOpen(true);
    }

    function closeModal() {
        setModalOpen(false);
        setEditingPaper(null);
        setForm(emptyForm);
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setSubmitting(true);
        try {
            if (editingPaper) {
                await fetch(`${API}/api/papers/${editingPaper.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(form),
                });
            } else {
                // New paper — use FormData so the unified ingest endpoint
                // can handle pdf_url, file upload, or manual fields
                const fd = new FormData();
                fd.append('title', form.title);
                fd.append('authors', form.authors);
                fd.append('abstract', form.abstract);
                if (form.paper_url) fd.append('pdf_url', form.paper_url);
                await fetch(`${API}/api/papers/ingest`, {
                    method: 'POST',
                    body: fd,
                });
            }
            await fetchPapers();
            closeModal();
        } catch {
            setError('Failed to save paper.');
        } finally {
            setSubmitting(false);
        }
    }

    async function handleDelete(id: string) {
        setDeleteId(id);
        try {
            await fetch(`${API}/api/papers/${id}`, { method: 'DELETE' });
            setPapers(prev => prev.filter(p => p.id !== id));
        } catch {
            setError('Failed to delete paper.');
        } finally {
            setDeleteId(null);
        }
    }

    if (!isLoaded) return null;

    return (
        <div
            className="min-h-screen bg-[#f5f0eb] text-[#2c2217] flex flex-col"
            style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
        >
            {/* Nav */}
            <header className="flex items-center justify-between px-6 py-3 border-b border-[#e0d8cf] bg-[#f5f0eb] shrink-0">
                <Link href="/" className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-md bg-[#6b1f2a] flex items-center justify-center">
                        <BookOpen className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-[15px] font-semibold tracking-tight">LivePaper</span>
                </Link>
                <nav className="flex items-center gap-6" style={{ fontFamily: 'system-ui, sans-serif' }}>
                    <Link
                        href="/dashboard"
                        className="text-sm font-semibold text-[#6b1f2a] border-b border-[#6b1f2a] pb-0.5"
                    >
                        Papers
                    </Link>
                    <Link
                        href="/experts"
                        className="text-sm text-[#8a7060] hover:text-[#2c2217] transition-colors flex items-center gap-1"
                    >
                        <Users className="w-3.5 h-3.5" /> Experts
                    </Link>
                    <UserButton showName={true} />
                </nav>
            </header>

            {/* Main */}
            <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-10">

                {/* Page heading */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <div className="flex items-center gap-2 text-xs text-[#8a7060] mb-1" style={{ fontFamily: 'system-ui, sans-serif' }}>
                            <span>Admin</span>
                            <ChevronRight className="w-3 h-3" />
                            <span>Papers</span>
                        </div>
                        <h1 className="text-2xl font-bold text-[#2c2217]">Research Papers</h1>
                    </div>
                    <button
                        onClick={openAdd}
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#6b1f2a] text-white text-sm font-semibold hover:bg-[#b8860b] active:scale-95 transition-all duration-150 shadow-sm"
                        style={{ fontFamily: 'system-ui, sans-serif' }}
                    >
                        <Plus className="w-4 h-4" /> Add Paper
                    </button>
                </div>

                {/* Error */}
                {error && (
                    <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 mb-6 text-sm" style={{ fontFamily: 'system-ui, sans-serif' }}>
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        {error}
                        <button onClick={() => setError('')} className="ml-auto"><X className="w-4 h-4" /></button>
                    </div>
                )}

                {/* Table */}
                <div className="bg-white rounded-2xl border border-[#e0d8cf] overflow-hidden shadow-sm">
                    {loading ? (
                        <div className="flex items-center justify-center py-20 text-[#8a7060]" style={{ fontFamily: 'system-ui, sans-serif' }}>
                            <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading papers…
                        </div>
                    ) : papers.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-20 text-[#8a7060]" style={{ fontFamily: 'system-ui, sans-serif' }}>
                            <FileText className="w-10 h-10 mb-3 text-[#d4c8bc]" />
                            <p className="text-sm">No papers yet. Add your first paper.</p>
                        </div>
                    ) : (
                        <table className="w-full text-sm" style={{ fontFamily: 'system-ui, sans-serif' }}>
                            <thead>
                                <tr className="border-b border-[#e0d8cf] bg-[#faf7f4]">
                                    <th className="text-left px-5 py-3.5 text-xs font-semibold text-[#8a7060] uppercase tracking-wider">Title</th>
                                    <th className="text-left px-5 py-3.5 text-xs font-semibold text-[#8a7060] uppercase tracking-wider hidden md:table-cell">Authors</th>
                                    <th className="text-left px-5 py-3.5 text-xs font-semibold text-[#8a7060] uppercase tracking-wider hidden lg:table-cell">Abstract</th>
                                    <th className="text-left px-5 py-3.5 text-xs font-semibold text-[#8a7060] uppercase tracking-wider">Links</th>
                                    <th className="px-5 py-3.5 text-xs font-semibold text-[#8a7060] uppercase tracking-wider text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {papers.map((paper, i) => (
                                    <tr
                                        key={paper.id}
                                        className={`border-b border-[#f0e8e0] hover:bg-[#faf7f4] transition-colors ${i === papers.length - 1 ? 'border-0' : ''}`}
                                    >
                                        <td className="px-5 py-4 max-w-[200px]">
                                            <p className="font-semibold text-[#2c2217] line-clamp-2 leading-snug" style={{ fontFamily: "'Georgia', serif" }}>
                                                {paper.title}
                                            </p>
                                        </td>
                                        <td className="px-5 py-4 text-[#5a4535] hidden md:table-cell max-w-[160px]">
                                            <p className="line-clamp-2">{paper.authors}</p>
                                        </td>
                                        <td className="px-5 py-4 text-[#8a7060] hidden lg:table-cell max-w-[260px]">
                                            <p className="line-clamp-2 text-xs leading-relaxed">{paper.abstract}</p>
                                        </td>
                                        <td className="px-5 py-4">
                                            <div className="flex flex-col gap-1">
                                                {paper.paper_url && (
                                                    <a href={paper.paper_url} target="_blank" rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1 text-xs text-[#6b1f2a] hover:underline">
                                                        <ExternalLink className="w-3 h-3" /> URL
                                                    </a>
                                                )}
                                                {paper.pdf_file && (
                                                    <a href={paper.pdf_file} target="_blank" rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1 text-xs text-[#6b1f2a] hover:underline">
                                                        <FileText className="w-3 h-3" /> PDF
                                                    </a>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-5 py-4">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => openEdit(paper)}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#d4c8bc] text-[#5a4535] text-xs font-medium hover:bg-[#ede6dc] hover:border-[#6b1f2a] transition-all duration-150"
                                                >
                                                    <Pencil className="w-3 h-3" /> Edit
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(paper.id)}
                                                    disabled={deleteId === paper.id}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-200 text-red-600 text-xs font-medium hover:bg-red-50 transition-all duration-150 disabled:opacity-40"
                                                >
                                                    {deleteId === paper.id
                                                        ? <Loader2 className="w-3 h-3 animate-spin" />
                                                        : <Trash2 className="w-3 h-3" />}
                                                    Delete
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                <p
                    className="text-center text-xs text-[#b0a090] mt-6"
                    style={{ fontFamily: 'system-ui, sans-serif' }}
                >
                    {papers.length} paper{papers.length !== 1 ? 's' : ''} total
                </p>
            </main>

            {/* Footer */}
            <div className="border-t border-[#e0d8cf]">
                <Footer />
            </div>

            {/* Add / Edit Modal */}
            {modalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-[#2c2217]/40 backdrop-blur-sm"
                        onClick={closeModal}
                    />

                    {/* Modal card */}
                    <div
                        className="relative bg-[#f5f0eb] rounded-2xl border border-[#e0d8cf] shadow-xl w-full max-w-xl max-h-[90vh] overflow-y-auto"
                        style={{ fontFamily: 'system-ui, sans-serif' }}
                    >
                        {/* Modal header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-[#e0d8cf]">
                            <h2 className="text-[15px] font-semibold text-[#2c2217]" style={{ fontFamily: "'Georgia', serif" }}>
                                {editingPaper ? 'Update Paper' : 'Add New Paper'}
                            </h2>
                            <button onClick={closeModal} className="text-[#8a7060] hover:text-[#2c2217] transition-colors">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
                            {[
                                { label: 'Title', key: 'title', placeholder: 'Full paper title', required: true },
                                { label: 'Authors', key: 'authors', placeholder: 'e.g. Smith, J., Doe, A.', required: true },
                                { label: 'Paper URL', key: 'paper_url', placeholder: 'https://…', required: false },
                                { label: 'PDF File URL', key: 'pdf_file', placeholder: 'https://…/paper.pdf', required: false },
                            ].map(({ label, key, placeholder, required }) => (
                                <div key={key}>
                                    <label className="block text-xs font-semibold text-[#5a4535] uppercase tracking-wider mb-1.5">
                                        {label} {required && <span className="text-[#6b1f2a]">*</span>}
                                    </label>
                                    <input
                                        type="text"
                                        value={form[key as keyof typeof form]}
                                        onChange={e => setForm(prev => ({ ...prev, [key]: e.target.value }))}
                                        placeholder={placeholder}
                                        required={required}
                                        className="w-full px-4 py-2.5 rounded-lg border border-[#d4c8bc] bg-white text-[#2c2217] placeholder-[#b0a090] text-sm focus:outline-none focus:border-[#6b1f2a] focus:ring-1 focus:ring-[#6b1f2a] transition-all"
                                    />
                                </div>
                            ))}

                            {/* Abstract textarea */}
                            <div>
                                <label className="block text-xs font-semibold text-[#5a4535] uppercase tracking-wider mb-1.5">
                                    Abstract <span className="text-[#6b1f2a]">*</span>
                                </label>
                                <textarea
                                    value={form.abstract}
                                    onChange={e => setForm(prev => ({ ...prev, abstract: e.target.value }))}
                                    placeholder="Paper abstract…"
                                    required
                                    rows={4}
                                    className="w-full px-4 py-2.5 rounded-lg border border-[#d4c8bc] bg-white text-[#2c2217] placeholder-[#b0a090] text-sm focus:outline-none focus:border-[#6b1f2a] focus:ring-1 focus:ring-[#6b1f2a] transition-all resize-none"
                                />
                            </div>

                            {/* Actions */}
                            <div className="flex gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={closeModal}
                                    className="flex-1 px-4 py-2.5 rounded-lg border border-[#d4c8bc] text-[#5a4535] text-sm font-medium hover:bg-[#ede6dc] transition-all duration-150"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className="flex-1 px-4 py-2.5 rounded-lg bg-[#6b1f2a] text-white text-sm font-semibold hover:bg-[#b8860b] active:scale-95 transition-all duration-150 disabled:opacity-50 inline-flex items-center justify-center gap-2"
                                >
                                    {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingPaper ? 'Update Paper' : 'Add Paper'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
