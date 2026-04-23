
import { Protect, PricingTable, UserButton, useUser } from '@clerk/nextjs';
import {
    BookOpen, Users, FileText
} from 'lucide-react';
import Footer from '../components/Footer';
import ResearchChat from '../components/ResearchChat';
import Link from 'next/link';

export default function Chat() {
    const { isLoaded, isSignedIn, user } = useUser()

    if (!isLoaded || !isSignedIn) {
        return null
    }

    const isAdmin = user.publicMetadata.role === 'admin';
    console.log('User:', user); // Debugging line to check the user's role
    return (
        <div
            className="min-h-screen bg-[#f5f0eb] text-[#2c2217] flex flex-col"
            style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
        >
            <Protect
                plan="premium_subscription"
                fallback={
                    <div className="flex flex-col min-h-screen bg-[#f5f0eb]">

                        {/* Nav */}
                        <header className="flex items-center justify-between px-6 py-3 border-b border-[#e0d8cf] bg-[#f5f0eb] shrink-0">
                            <Link href="/" className="flex items-center gap-2">
                                <div className="w-7 h-7 rounded-md bg-[#6b1f2a] flex items-center justify-center">
                                    <BookOpen className="w-4 h-4 text-white" />
                                </div>
                                <span className="text-[15px] font-semibold text-[#2c2217] tracking-tight">LivePaper</span>
                            </Link>

                            {isAdmin && (
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
                        )}

                                                    
                        
                        
                            <div className="z-10">
                                <UserButton showName={true} />
                            </div>
                        </header>

                        {/* Paywall content */}
                        <div className="flex-1 overflow-y-auto">
                            <div className="max-w-3xl mx-auto px-6 py-16">

                                {/* Badge */}
                                <div className="flex justify-center mb-8">
                                    <div
                                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#d4c8bc] bg-white text-[#8a7060] text-xs"
                                        style={{ fontFamily: 'system-ui, sans-serif' }}
                                    >
                                        <div className="w-1.5 h-1.5 rounded-full bg-[#6b1f2a]" />
                                        Premium access required
                                    </div>
                                </div>

                                <header className="text-center mb-12">
                                    <h1 className="text-4xl font-bold text-[#2c2217] mb-5 leading-tight">
                                        Instantly find high-relevance papers simply by asking questions in plain English
                                    </h1>
                                    <div className="space-y-4 max-w-2xl mx-auto" style={{ fontFamily: 'system-ui, sans-serif' }}>
                                        <p className="text-[#8a7060] text-base leading-relaxed">
                                            Move beyond reading — start a dynamic conversation with your focus papers to extract deep insights.
                                        </p>
                                        <p className="text-[#8a7060] text-base leading-relaxed">
                                            When the text hits a wall, LivePaper bridges the gap by connecting your query to the authors or subject experts in real-time.
                                        </p>
                                        <p className="text-[#8a7060] text-base leading-relaxed">
                                            Every expert response feeds back into our system, making the intelligence pool deeper and more accurate for every researcher who follows.
                                        </p>
                                    </div>
                                </header>

                                {/* Pricing */}
                                <div className="bg-white rounded-2xl border border-[#e0d8cf] p-8 shadow-sm">
                                    <PricingTable />
                                </div>

                                <p
                                    className="text-center text-xs text-[#b0a090] mt-6"
                                    style={{ fontFamily: 'system-ui, sans-serif' }}
                                >
                                    Cancel anytime · No hidden fees · Instant access
                                </p>
                            </div>
                        </div>

                        <div className="border-t border-[#e0d8cf] shrink-0">
                            <Footer />
                        </div>
                    </div>
                }
            >
                {/* Authenticated — full height chat */}
                <header className="flex items-center justify-between px-6 py-3 border-b border-[#e0d8cf] bg-[#f5f0eb] shrink-0">
                    <Link href="/" className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-md bg-[#6b1f2a] flex items-center justify-center">
                            <BookOpen className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-[15px] font-semibold text-[#2c2217] tracking-tight">LivePaper</span>
                    </Link>

                        {isAdmin && (
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
                        )}

            
                </header>

                <div className="flex flex-col min-h-0">
                    <ResearchChat />
                </div>
            </Protect>
        </div>
    );
}