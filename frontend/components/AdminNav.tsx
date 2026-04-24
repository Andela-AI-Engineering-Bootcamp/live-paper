'use client';
import Link from 'next/link';
import { UserButton } from '@clerk/nextjs';
import { FileText, Users } from 'lucide-react';

export default function AdminNav() {
    return (
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
    );
}

