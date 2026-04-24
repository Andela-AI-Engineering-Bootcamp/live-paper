"use client"

import Link from 'next/link';
import { SignInButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs';
import { BookOpen, Zap, Users, TrendingUp, ArrowRight } from "lucide-react";
import Footer from '../components/Footer';

export default function Home() {
  return (
    <main
      className="min-h-screen bg-[#f5f0eb] text-[#2c2217]"
      style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
    >


      <header className="flex items-center justify-between px-6 py-3 border-b border-[#e0d8cf] bg-[#f5f0eb]">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-[#6b1f2a] flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-white" />
          </div>
          <span className="text-[15px] font-semibold text-[#2c2217] tracking-tight">LivePaper</span>
        </Link>

        <div style={{ fontFamily: 'system-ui, sans-serif' }}>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="px-5 py-2 text-sm font-medium rounded-lg bg-[#2c2217] text-[#f5f0eb] hover:bg-[#3d3020] transition-colors duration-150">
                Sign In
              </button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <div className="flex items-center gap-4">
              <Link
                href="/chat"
                className="px-5 py-2 text-sm font-medium rounded-lg bg-[#6b1f2a] text-white hover:bg-[#b8860b] transition-colors duration-150"
              >
                Try it Now
              </Link>
              <UserButton showName={true} />
            </div>
          </SignedIn>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="max-w-3xl mx-auto px-6 pt-24 pb-20 text-center">
        {/* Badge */}
        <div
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#d4c8bc] bg-white text-[#8a7060] text-xs mb-8"
          style={{ fontFamily: 'system-ui, sans-serif' }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-[#6b1f2a]" />
          Research intelligence, live
        </div>

        <h1 className="text-5xl font-bold text-[#2c2217] mb-6 leading-tight tracking-tight">
          LivePaper turns static research papers into live documents
        </h1>

        <p
          className="text-lg text-[#8a7060] mb-10 max-w-xl mx-auto leading-relaxed"
          style={{ fontFamily: 'system-ui, sans-serif' }}
        >
          Ask questions across multiple papers simultaneously. When no paper has the answer,
          LivePaper routes your question to the author who wrote it.
        </p>

        <div className="flex items-center justify-center gap-4">
          <SignedOut>
            <SignInButton mode="modal">
              <button className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-[#6b1f2a] text-white font-semibold text-[15px] hover:bg-[#b8860b] active:scale-95 transition-all duration-150 shadow-sm" style={{ fontFamily: 'system-ui, sans-serif' }}>
                Start Free Trial
                <ArrowRight className="w-4 h-4" />
              </button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-[#6b1f2a] text-white font-semibold text-[15px] hover:bg-[#b8860b] active:scale-95 transition-all duration-150 shadow-sm"
              style={{ fontFamily: 'system-ui, sans-serif' }}
            >
              Start your research
              <ArrowRight className="w-4 h-4" />
            </Link>
          </SignedIn>
        </div>
      </section>

      {/* ── Divider ── */}
      <div className="max-w-3xl mx-auto px-6">
        <div className="border-t border-[#e0d8cf]" />
      </div>

      {/* ── Features ── */}
      <section className="max-w-3xl mx-auto px-6 py-20">
        <p
          className="text-xs uppercase tracking-widest text-[#6b1f2a] text-center mb-12 font-semibold"
          style={{ fontFamily: 'system-ui, sans-serif' }}
        >
          How it works
        </p>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: <Zap className="w-5 h-5 text-[#6b1f2a]" />,
              title: 'Multi-paper chat',
              body: 'Ask one question, get cited answers from all relevant papers simultaneously.',
            },
            {
              icon: <Users className="w-5 h-5 text-[#6b1f2a]" />,
              title: 'Expert escalation',
              body: "When no paper answers, LivePaper routes your question to the author who can.",
            },
            {
              icon: <TrendingUp className="w-5 h-5 text-[#6b1f2a]" />,
              title: 'Living knowledge graph',
              body: 'Every expert response makes the system smarter. The graph grows with every conversation.',
            },
          ].map(({ icon, title, body }) => (
            <div
              key={title}
              className="bg-white rounded-2xl border border-[#e0d8cf] p-6 hover:border-[#6b1f2a] hover:shadow-sm transition-all duration-200"
            >
              <div className="w-9 h-9 rounded-lg bg-[#fdf6f0] border border-[#f0e4d8] flex items-center justify-center mb-4">
                {icon}
              </div>
              <h3 className="text-[15px] font-semibold text-[#2c2217] mb-2">{title}</h3>
              <p
                className="text-sm text-[#8a7060] leading-relaxed"
                style={{ fontFamily: 'system-ui, sans-serif' }}
              >
                {body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA strip ── */}
      <section className="max-w-3xl mx-auto px-6 pb-20">
        <div className="rounded-2xl bg-[#2c2217] px-8 py-10 text-center">
          <h2 className="text-2xl font-bold text-[#f5f0eb] mb-3">
            Ready to explore your research?
          </h2>
          <p
            className="text-[#b0a090] text-sm mb-7"
            style={{ fontFamily: 'system-ui, sans-serif' }}
          >
            Join researchers who are already using LivePaper to go deeper, faster.
          </p>
          <SignedOut>
            <SignInButton mode="modal">
              <button
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#6b1f2a] text-white font-semibold text-[15px] hover:bg-[#b8860b] transition-colors duration-150"
                style={{ fontFamily: 'system-ui, sans-serif' }}
              >
                Get started free
                <ArrowRight className="w-4 h-4" />
              </button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#6b1f2a] text-white font-semibold text-[15px] hover:bg-[#b8860b] transition-colors duration-150"
              style={{ fontFamily: 'system-ui, sans-serif' }}
            >
              Open LivePaper
              <ArrowRight className="w-4 h-4" />
            </Link>
          </SignedIn>
        </div>
      </section>

      {/* ── Footer ── */}
      <div className="border-t border-[#e0d8cf]">
        <Footer />
      </div>

    </main>
  );
}
