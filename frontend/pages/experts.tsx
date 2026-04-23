"use client"

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useUser, UserButton } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import {
    BookOpen, Users, ChevronRight, AlertCircle,
    Loader2, X, FileText, ChevronDown, ChevronUp, Mail
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

interface Expert {
    id: string;
    name: string;
    email: string;
    bio: string;
    papers: Paper[];
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Experts() {
    const { user, isLoaded } = useUser();
    const router = useRouter();

    const [experts, setExperts] = useState<Expert[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [expandedId, setExpandedId] = useState<string | null>(null);

    // Guard: only admins
    useEffect(() => {
        if (isLoaded && user?.publicMetadata?.role !== 'admin') {
            router.replace('/');
        }
    }, [isLoaded, user, router]);

    useEffect(() => {
        fetchExperts();
    }, []);

    async function fetchExperts() {
        setLoading(true);
        try {
            const res = await fetch(`${API}/experts`);
            const data = await res.json();
            //setExperts(data);
        } catch {
            setError('Failed to load experts.');
        } finally {
            setLoading(false);
        }
    }

    function toggleExpand(id: string) {
        setExpandedId(prev => prev === id ? null : id);
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
                        className="text-sm text-[#8a7060] hover:text-[#2c2217] transition-colors flex items-center gap-1"
                    >
                        <FileText className="w-3.5 h-3.5" /> Papers
                    </Link>
                    <Link
                        href="/experts"
                        className="text-sm font-semibold text-[#6b1f2a] border-b border-[#6b1f2a] pb-0.5 flex items-center gap-1"
                    >
                        <Users className="w-3.5 h-3.5" /> Experts
                    </Link>
                    <UserButton showName={true} />
                </nav>
            </header>

            {/* Main */}
            <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-10">

                {/* Page heading */}
                <div className="mb-8">
                    <div className="flex items-center gap-2 text-xs text-[#8a7060] mb-1" style={{ fontFamily: 'system-ui, sans-serif' }}>
                        <span>Admin</span>
                        <ChevronRight className="w-3 h-3" />
                        <span>Experts</span>
                    </div>
                    <h1 className="text-2xl font-bold text-[#2c2217]">Subject Experts</h1>
                    <p className="text-sm text-[#8a7060] mt-1" style={{ fontFamily: 'system-ui, sans-serif' }}>
                        Experts and the research papers they are associated with.
                    </p>
                </div>

                {/* Error */}
                {error && (
                    <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 mb-6 text-sm" style={{ fontFamily: 'system-ui, sans-serif' }}>
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        {error}
                        <button onClick={() => setError('')} className="ml-auto"><X className="w-4 h-4" /></button>
                    </div>
                )}

                {/* Content */}
                {loading ? (
                    <div className="flex items-center justify-center py-24 text-[#8a7060]" style={{ fontFamily: 'system-ui, sans-serif' }}>
                        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading experts…
                    </div>
                ) : experts.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-24 text-[#8a7060]" style={{ fontFamily: 'system-ui, sans-serif' }}>
                        <Users className="w-10 h-10 mb-3 text-[#d4c8bc]" />
                        <p className="text-sm">No experts found.</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {experts.map((expert) => {
                            const isExpanded = expandedId === expert.id;
                            return (
                                <div
                                    key={expert.id}
                                    className="bg-white rounded-2xl border border-[#e0d8cf] overflow-hidden shadow-sm transition-all duration-200"
                                >
                                    {/* Expert row — click to expand */}
                                    <button
                                        onClick={() => toggleExpand(expert.id)}
                                        className="w-full flex items-center gap-4 px-6 py-4 hover:bg-[#faf7f4] transition-colors text-left"
                                    >
                                        {/* Avatar */}
                                        <div className="w-10 h-10 rounded-full bg-[#6b1f2a] flex items-center justify-center shrink-0 text-white font-semibold text-sm">
                                            {expert.name?.charAt(0)?.toUpperCase() || 'E'}
                                        </div>

                                        {/* Info */}
                                        <div className="flex-1 min-w-0">
                                            <p className="font-semibold text-[#2c2217] text-[15px]" style={{ fontFamily: "'Georgia', serif" }}>
                                                {expert.name}
                                            </p>
                                            <div className="flex items-center gap-1 text-xs text-[#8a7060] mt-0.5" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                                <Mail className="w-3 h-3" />
                                                {expert.email}
                                            </div>
                                        </div>

                                        {/* Paper count badge */}
                                        <div
                                            className="shrink-0 flex items-center gap-2"
                                            style={{ fontFamily: 'system-ui, sans-serif' }}
                                        >
                                            <span className="px-2.5 py-1 rounded-full bg-[#fdf6f0] border border-[#f0e4d8] text-xs text-[#6b1f2a] font-medium">
                                                {expert.papers?.length || 0} paper{expert.papers?.length !== 1 ? 's' : ''}
                                            </span>
                                            {isExpanded
                                                ? <ChevronUp className="w-4 h-4 text-[#8a7060]" />
                                                : <ChevronDown className="w-4 h-4 text-[#8a7060]" />}
                                        </div>
                                    </button>

                                    {/* Expanded — bio + papers */}
                                    {isExpanded && (
                                        <div className="border-t border-[#f0e8e0]">

                                            {/* Bio */}
                                            {expert.bio && (
                                                <div className="px-6 py-4 bg-[#faf7f4] border-b border-[#f0e8e0]">
                                                    <p className="text-xs font-semibold text-[#8a7060] uppercase tracking-wider mb-1.5" style={{ fontFamily: 'system-ui, sans-serif' }}>Bio</p>
                                                    <p className="text-sm text-[#5a4535] leading-relaxed" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                                        {expert.bio}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Papers list */}
                                            <div className="px-6 py-4">
                                                <p className="text-xs font-semibold text-[#8a7060] uppercase tracking-wider mb-3" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                                    Associated Papers
                                                </p>

                                                {!expert.papers?.length ? (
                                                    <p className="text-sm text-[#b0a090] italic" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                                        No papers associated with this expert yet.
                                                    </p>
                                                ) : (
                                                    <div className="space-y-3">
                                                        {expert.papers.map((paper) => (
                                                            <div
                                                                key={paper.id}
                                                                className="rounded-xl border border-[#e0d8cf] bg-[#faf7f4] p-4"
                                                            >
                                                                <p className="font-semibold text-[#2c2217] text-sm leading-snug mb-1" style={{ fontFamily: "'Georgia', serif" }}>
                                                                    {paper.title}
                                                                </p>
                                                                <p className="text-xs text-[#8a7060] mb-2" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                                                    {paper.authors}
                                                                </p>
                                                                {paper.abstract && (
                                                                    <p className="text-xs text-[#8a7060] leading-relaxed line-clamp-2 mb-2" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                                                        {paper.abstract}
                                                                    </p>
                                                                )}
                                                                <div className="flex items-center gap-4" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                                                    {paper.paper_url && (
                                                                        <a
                                                                            href={paper.paper_url}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            className="text-xs text-[#6b1f2a] hover:underline inline-flex items-center gap-1"
                                                                        >
                                                                            <FileText className="w-3 h-3" /> View Paper
                                                                        </a>
                                                                    )}
                                                                    {paper.pdf_file && (
                                                                        <a
                                                                            href={paper.pdf_file}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            className="text-xs text-[#6b1f2a] hover:underline inline-flex items-center gap-1"
                                                                        >
                                                                            <FileText className="w-3 h-3" /> PDF
                                                                        </a>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}

                <p
                    className="text-center text-xs text-[#b0a090] mt-8"
                    style={{ fontFamily: 'system-ui, sans-serif' }}
                >
                    {experts.length} expert{experts.length !== 1 ? 's' : ''} total
                </p>
            </main>

            {/* Footer */}
            <div className="border-t border-[#e0d8cf]">
                <Footer />
            </div>
        </div>
    );
}
