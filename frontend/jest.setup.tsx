// jest.setup.ts
import React from 'react';                // ✅ add this at the top
import '@testing-library/jest-dom';

// rest of the file unchanged...

// Mock next/router for pages router
jest.mock('next/router', () => ({
    useRouter: jest.fn(() => ({
        pathname: '/',
        query: {},
        isReady: true,
        replace: jest.fn(),
        push: jest.fn(),
    })),
}));

// Mock next/navigation (used by some components)
jest.mock('next/navigation', () => ({
    useRouter: jest.fn(() => ({
        replace: jest.fn(),
        push: jest.fn(),
    })),
    usePathname: jest.fn(() => '/'),
}));

// Mock Clerk
jest.mock('@clerk/nextjs', () => ({
    useUser: jest.fn(() => ({
        user: {
            publicMetadata: { role: 'admin' },
            firstName: 'Admin',
            emailAddresses: [{ emailAddress: 'admin@test.com' }],
        },
        isLoaded: true,
        isSignedIn: true,
    })),
    UserButton: () => <div data-testid="user-button" />,
    Protect: ({ children, fallback }: { children: React.ReactNode; fallback: React.ReactNode }) => (
        <>{children}</>
    ),
    PricingTable: () => <div data-testid="pricing-table" />,
    SignInButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    SignedIn: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    SignedOut: () => null,
}));

// Mock lucide-react icons to avoid SVG rendering issues
jest.mock('lucide-react', () => {
    const icons = [
        'BookOpen', 'Plus', 'Trash2', 'Pencil', 'X', 'ExternalLink',
        'FileText', 'Users', 'ChevronRight', 'AlertCircle', 'Loader2',
        'UserPlus', 'Send', 'Bot', 'User', 'Square', 'CheckCircle',
        'ChevronDown', 'ChevronUp', 'Mail', 'MessageSquare', 'Zap',
        'TrendingUp', 'ArrowRight',
    ];
    return icons.reduce((acc, name) => ({
        ...acc,
        [name]: ({ className }: { className?: string }) => (
            <span data-testid={`icon-${name}`} className={className} />
        ),
    }), {});
});

// Mock Footer and AdminNav components
jest.mock('@/components/Footer', () => () => <footer data-testid="footer" />);
jest.mock('@/components/AdminNav', () => () => <nav data-testid="admin-nav" />);
jest.mock('@/components/ResearchChat', () => () => <div data-testid="research-chat" />);
