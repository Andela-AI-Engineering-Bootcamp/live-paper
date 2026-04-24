
import { UserButton, useUser } from '@clerk/nextjs';
import { BookOpen } from 'lucide-react';
import ResearchChat from '../components/ResearchChat';
import Link from 'next/link';
import AdminNav from '@/components/AdminNav';

export default function Chat() {
    const { isLoaded, isSignedIn, user } = useUser()

    if (!isLoaded || !isSignedIn) {
        return null
    }

    const isAdmin = user.publicMetadata.role === 'admin';

    return (
        <div
            className="min-h-screen bg-[#f5f0eb] text-[#2c2217] flex flex-col"
            style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
        >
            <header className="flex items-center justify-between px-6 py-3 border-b border-[#e0d8cf] bg-[#f5f0eb] shrink-0">
                <Link href="/" className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-md bg-[#6b1f2a] flex items-center justify-center">
                        <BookOpen className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-[15px] font-semibold text-[#2c2217] tracking-tight">LivePaper</span>
                </Link>

                {isAdmin ? <AdminNav /> : <UserButton showName={true} />}
            </header>

            <div className="flex flex-col min-h-0">
                <ResearchChat />
            </div>
        </div>
    );
}
