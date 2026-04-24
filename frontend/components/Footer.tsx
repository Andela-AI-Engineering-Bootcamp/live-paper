'use client';

export default function Footer() {
    return (
        <footer className="py-8 text-center text-sm text-gray-400 border-t border-gray-100">
                    <p
                        className="text-xs text-[#b0a090]"
                        style={{ fontFamily: 'system-ui, sans-serif' }}
                    >
                        © {new Date().getFullYear()} LivePaper · Connecting researchers with the experts behind the papers
                    </p>
        </footer>
    );
}

