import Head from "next/head";
import Link from "next/link";
import { BookOpen, Zap, Users, TrendingUp } from "lucide-react";

export default function Home() {
  return (
    <>
      <Head>
        <title>LivePaper — Research papers, made answerable</title>
      </Head>
      <div className="min-h-screen bg-white">
        <nav className="px-8 py-5 border-b border-gray-100 flex justify-between items-center">
          <div className="flex items-center gap-2 font-bold text-xl text-gray-900">
            <BookOpen size={24} className="text-primary" />
            LivePaper
          </div>
          <Link
            href="/search"
            className="px-5 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Start Researching
          </Link>
        </nav>

        <section className="max-w-4xl mx-auto px-8 py-24 text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
            Every paper, answerable.<br />
            <span className="text-primary">Every expert, reachable.</span>
          </h1>
          <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
            Ask questions across multiple papers simultaneously. When no paper has the answer,
            LivePaper routes your question to the author who wrote it.
          </p>
          <Link
            href="/search"
            className="px-8 py-4 bg-primary text-white text-lg rounded-lg font-semibold hover:bg-blue-700 transition-colors shadow-lg inline-block"
          >
            Ask Your First Question
          </Link>
        </section>

        <section className="bg-gray-50 py-20">
          <div className="max-w-5xl mx-auto px-8 grid md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-xl shadow-sm">
              <Zap size={28} className="text-primary mb-4" />
              <h3 className="text-lg font-semibold mb-2">Multi-paper chat</h3>
              <p className="text-gray-600 text-sm">Ask one question, get cited answers from all relevant papers simultaneously.</p>
            </div>
            <div className="bg-white p-8 rounded-xl shadow-sm">
              <Users size={28} className="text-accent mb-4" />
              <h3 className="text-lg font-semibold mb-2">Expert escalation</h3>
              <p className="text-gray-600 text-sm">When no paper answers, LivePaper routes your question to the author who can.</p>
            </div>
            <div className="bg-white p-8 rounded-xl shadow-sm">
              <TrendingUp size={28} className="text-success mb-4" />
              <h3 className="text-lg font-semibold mb-2">Living knowledge graph</h3>
              <p className="text-gray-600 text-sm">Every expert response makes the system smarter. The graph grows with every conversation.</p>
            </div>
          </div>
        </section>

        <footer className="py-8 text-center text-sm text-gray-400 border-t border-gray-100">
          LivePaper · Andela AI Engineering Capstone 2025
        </footer>
      </div>
    </>
  );
}
