import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { useUser } from '@clerk/nextjs';
import Home from '../pages/index';

const mockUseUser = useUser as jest.MockedFunction<typeof useUser>;

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderSignedOut() {
    // Override Protect/SignedIn/SignedOut for signed-out state
    jest.resetModules();
    jest.mock('@clerk/nextjs', () => ({
        ...jest.requireActual('@clerk/nextjs'),
        SignedIn: () => null,
        SignedOut: ({ children }: { children: React.ReactNode }) => <>{children}</>,
        SignInButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
        UserButton: () => null,
    }));
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Home — Landing Page', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('Layout & Branding', () => {
        it('renders the LivePaper brand name in the nav', () => {
            render(<Home />);
            expect(screen.getAllByText('LivePaper').length).toBeGreaterThan(0);
        });

        it('renders the hero headline', () => {
            render(<Home />);
            expect(
                screen.getByText(/LivePaper turns static research papers into live documents/i)
            ).toBeInTheDocument();
        });

        it('renders the hero subtext', () => {
            render(<Home />);
            expect(
                screen.getByText(/Ask questions across multiple papers simultaneously/i)
            ).toBeInTheDocument();
        });

        it('renders the How it works section label', () => {
            render(<Home />);
            expect(screen.getByText(/How it works/i)).toBeInTheDocument();
        });

        it('renders the footer', () => {
            render(<Home />);
            expect(screen.getByTestId('footer')).toBeInTheDocument();
        });
    });

    describe('Feature Cards', () => {
        it('renders Multi-paper chat feature card', () => {
            render(<Home />);
            expect(screen.getByText('Multi-paper chat')).toBeInTheDocument();
        });

        it('renders Expert escalation feature card', () => {
            render(<Home />);
            expect(screen.getByText('Expert escalation')).toBeInTheDocument();
        });

        it('renders Living knowledge graph feature card', () => {
            render(<Home />);
            expect(screen.getByText('Living knowledge graph')).toBeInTheDocument();
        });
    });

    describe('CTA Strip', () => {
        it('renders the Ready to explore heading', () => {
            render(<Home />);
            expect(screen.getByText(/Ready to explore your research/i)).toBeInTheDocument();
        });
    });

    describe('Signed In State', () => {
        it('renders the Try it Now link when signed in', () => {
            render(<Home />);
            const tryLinks = screen.getAllByText(/Try it Now|Start your research|Open LivePaper/i);
            expect(tryLinks.length).toBeGreaterThan(0);
        });

        it('Try it Now link points to /chat', () => {
            render(<Home />);
            const link = screen.getByRole('link', { name: /Try it Now/i });
            expect(link).toHaveAttribute('href', '/chat');
        });

        it('renders UserButton when signed in', () => {
            render(<Home />);
            expect(screen.getByTestId('user-button')).toBeInTheDocument();
        });
    });
});
