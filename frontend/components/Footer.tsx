'use client';

export default function Footer() {
    return (
        <footer className="py-8 text-center text-sm text-gray-400 border-t border-gray-100">
          LivePaper · Andela AI Engineering Capstone {new Date().getFullYear()}
        </footer>
    );
}