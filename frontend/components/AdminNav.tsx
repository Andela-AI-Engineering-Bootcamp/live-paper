'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { UserButton } from '@clerk/nextjs';
import { FileText, Users, MessageSquare } from 'lucide-react';

const links = [
    { href: '/chat/',      label: 'Chat',    icon: MessageSquare },
    { href: '/dashboard/', label: 'Papers',  icon: FileText },
    { href: '/experts/',   label: 'Experts', icon: Users },
];

export default function AdminNav() {
    const pathname = usePathname();

    return (
        <nav className="flex items-center gap-6" style={{ fontFamily: 'system-ui, sans-serif' }}>
            {links.map(({ href, label, icon: Icon }) => {
                const isActive = pathname === href;
                return (
                    <Link
                        key={href}
                        href={href}
                        className={`text-sm flex items-center gap-1 transition-colors ${
                            isActive
                                ? 'font-semibold text-[#6b1f2a] border-b border-[#6b1f2a] pb-0.5'
                                : 'text-[#8a7060] hover:text-[#2c2217]'
                        }`}
                    >
                        <Icon className="w-3.5 h-3.5" />
                        {label}
                    </Link>
                );
            })}
            <UserButton showName={true} />
        </nav>
    );
}