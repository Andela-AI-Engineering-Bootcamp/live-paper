import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import AdminDashboard from '../pages/dashboard';

const mockUseUser = useUser as jest.MockedFunction<typeof useUser>;
const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;
const mockReplace = jest.fn();
global.fetch = jest.fn();
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

// ── Mock data ─────────────────────────────────────────────────────────────────

const mockPapers = [
    {
        id: '1',
        title: 'Attention Is All You Need',
        authors: [
            { name: 'Ashish Vaswani', email: 'vaswani@google.com' },
            { name: 'Noam Shazeer', email: 'noam@google.com' },
        ],
        abstract: 'The dominant sequence transduction models...',
        paper_url: 'https://arxiv.org/abs/1706.03762',
        pdf_url: 'https://arxiv.org/pdf/1706.03762.pdf',
    },
    {
        id: '2',
        title: 'BERT: Pre-training of Deep Bidirectional Transformers',
        authors: [{ name: 'Jacob Devlin', email: 'devlin@google.com' }],
        abstract: 'We introduce a new language representation model...',
        paper_url: 'https://arxiv.org/abs/1810.04805',
        pdf_url: '',
    },
];

// ── Setup ─────────────────────────────────────────────────────────────────────

function setupAdminUser() {
    mockUseUser.mockReturnValue({
        user: { publicMetadata: { role: 'admin' } } as any,
        isLoaded: true,
        isSignedIn: true,
    } as any);
    mockUseRouter.mockReturnValue({ replace: mockReplace, push: jest.fn() } as any);
}

function setupNonAdminUser() {
    mockUseUser.mockReturnValue({
        user: { publicMetadata: { role: 'user' } } as any,
        isLoaded: true,
        isSignedIn: true,
    } as any);
    mockUseRouter.mockReturnValue({ replace: mockReplace, push: jest.fn() } as any);
}

function mockPapersSuccess(papers = mockPapers) {
    mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => papers,
    } as Response);
}

function mockPapersEmpty() {
    mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
    } as Response);
}

function mockApiSuccess() {
    mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
    } as Response);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AdminDashboard', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        setupAdminUser();
    });

    // ── Guard ─────────────────────────────────────────────────────────────────

    describe('Admin Guard', () => {
        it('redirects non-admin users to /', async () => {
            setupNonAdminUser();
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => {
                expect(mockReplace).toHaveBeenCalledWith('/');
            });
        });

        it('does not redirect admin users', async () => {
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());
            expect(mockReplace).not.toHaveBeenCalled();
        });
    });

    // ── Layout ────────────────────────────────────────────────────────────────

    describe('Layout', () => {
        it('renders the Research Papers heading', async () => {
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => expect(screen.getByText('Research Papers')).toBeInTheDocument());
        });

        it('renders the Admin nav breadcrumb', async () => {
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => expect(screen.getByText('Admin')).toBeInTheDocument());
        });

        it('renders the Add Paper button', async () => {
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => expect(screen.getByText('Add Paper')).toBeInTheDocument());
        });

        it('renders the footer', async () => {
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => expect(screen.getByTestId('footer')).toBeInTheDocument());
        });

        it('renders AdminNav', async () => {
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => expect(screen.getByTestId('admin-nav')).toBeInTheDocument());
        });
    });

    // ── Papers table ──────────────────────────────────────────────────────────

    describe('Papers Table', () => {
        it('shows loading spinner initially', () => {
            mockFetch.mockImplementationOnce(() => new Promise(() => {}));
            render(<AdminDashboard />);
            expect(screen.getByText(/Loading papers/i)).toBeInTheDocument();
        });

        it('shows empty state when no papers', async () => {
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => expect(screen.getByText(/No papers yet/i)).toBeInTheDocument());
        });

        it('renders paper titles in the table', async () => {
            mockPapersSuccess();
            render(<AdminDashboard />);
            await waitFor(() => {
                expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument();
                expect(screen.getByText('BERT: Pre-training of Deep Bidirectional Transformers')).toBeInTheDocument();
            });
        });

        it('renders author names in the table', async () => {
            mockPapersSuccess();
            render(<AdminDashboard />);
            await waitFor(() => {
                expect(screen.getByText('Ashish Vaswani')).toBeInTheDocument();
            });
        });

        it('renders paper URL links', async () => {
            mockPapersSuccess();
            render(<AdminDashboard />);
            await waitFor(() => {
                const urlLinks = screen.getAllByText('URL');
                expect(urlLinks.length).toBeGreaterThan(0);
            });
        });

        it('shows correct paper count', async () => {
            mockPapersSuccess();
            render(<AdminDashboard />);
            await waitFor(() => {
                expect(screen.getByText('2 papers total')).toBeInTheDocument();
            });
        });

        it('shows singular paper count', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => [mockPapers[0]],
            } as Response);
            render(<AdminDashboard />);
            await waitFor(() => {
                expect(screen.getByText('1 paper total')).toBeInTheDocument();
            });
        });

        it('shows error when papers fail to load', async () => {
            mockFetch.mockRejectedValueOnce(new Error('Network error'));
            render(<AdminDashboard />);
            await waitFor(() => {
                expect(screen.getByText('Failed to load papers.')).toBeInTheDocument();
            });
        });

        it('dismisses error when X is clicked', async () => {
            const user = userEvent.setup();
            mockFetch.mockRejectedValueOnce(new Error('Network error'));
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Failed to load papers.'));
            const closeBtn = screen.getByRole('button', { name: '' }); // X icon button in error
            await user.click(closeBtn);
            expect(screen.queryByText('Failed to load papers.')).not.toBeInTheDocument();
        });
    });

    // ── Add Paper Modal ───────────────────────────────────────────────────────

    describe('Add Paper Modal', () => {
        it('opens modal when Add Paper is clicked', async () => {
            const user = userEvent.setup();
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Add Paper'));
            await user.click(screen.getByText('Add Paper'));
            expect(screen.getByText('Add New Paper')).toBeInTheDocument();
        });

        it('renders title input in modal', async () => {
            const user = userEvent.setup();
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Add Paper'));
            await user.click(screen.getByText('Add Paper'));
            expect(screen.getByPlaceholderText('Full paper title')).toBeInTheDocument();
        });

        it('renders author name and email inputs', async () => {
            const user = userEvent.setup();
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Add Paper'));
            await user.click(screen.getByText('Add Paper'));
            expect(screen.getByPlaceholderText('Author name')).toBeInTheDocument();
            expect(screen.getByPlaceholderText('author@email.com (optional)')).toBeInTheDocument();
        });

        it('renders abstract textarea', async () => {
            const user = userEvent.setup();
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Add Paper'));
            await user.click(screen.getByText('Add Paper'));
            expect(screen.getByPlaceholderText('Paper abstract…')).toBeInTheDocument();
        });

        it('closes modal when Cancel is clicked', async () => {
            const user = userEvent.setup();
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Add Paper'));
            await user.click(screen.getByText('Add Paper'));
            await user.click(screen.getByText('Cancel'));
            expect(screen.queryByText('Add New Paper')).not.toBeInTheDocument();
        });

        it('closes modal when backdrop is clicked', async () => {
            const user = userEvent.setup();
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Add Paper'));
            await user.click(screen.getByText('Add Paper'));
            const backdrop = document.querySelector('.absolute.inset-0') as Element;
            await user.click(backdrop);
            expect(screen.queryByText('Add New Paper')).not.toBeInTheDocument();
        });
    });

    // ── Authors ───────────────────────────────────────────────────────────────

    describe('Author Management in Modal', () => {
        async function openModal() {
            const user = userEvent.setup();
            mockPapersEmpty();
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Add Paper'));
            await user.click(screen.getByText('Add Paper'));
            return user;
        }

        it('starts with one author row', async () => {
            await openModal();
            expect(screen.getAllByPlaceholderText('Author name').length).toBe(1);
        });

        it('adds a second author row when Add Author is clicked', async () => {
            const user = await openModal();
            await user.click(screen.getByText('Add Author'));
            expect(screen.getAllByPlaceholderText('Author name').length).toBe(2);
        });

        it('adds author row via Add another author button', async () => {
            const user = await openModal();
            await user.click(screen.getByText('Add another author'));
            expect(screen.getAllByPlaceholderText('Author name').length).toBe(2);
        });

        it('does not show remove button when only one author', async () => {
            await openModal();
            // Only one author — X remove button should not be visible
            const authorInputs = screen.getAllByPlaceholderText('Author name');
            expect(authorInputs.length).toBe(1);
            // The remove X button only renders when authors.length > 1
            const removeButtons = document.querySelectorAll('[data-testid="icon-X"]');
            // X icon is used for modal close too, but not for author remove
            const modalCloseX = screen.getAllByTestId('icon-X');
            // Should only be the modal close button, not an author remove button
            expect(modalCloseX.length).toBe(1);
        });

        it('removes an author when X is clicked with multiple authors', async () => {
            const user = await openModal();
            await user.click(screen.getByText('Add Author'));
            expect(screen.getAllByPlaceholderText('Author name').length).toBe(2);

            // Click the remove button on the second author (appears after adding)
            const removeIcons = screen.getAllByTestId('icon-X');
            // First X is modal close, remaining are author removes
            await user.click(removeIcons[removeIcons.length - 1]);
            expect(screen.getAllByPlaceholderText('Author name').length).toBe(1);
        });

        it('typing in author name input updates value', async () => {
            const user = await openModal();
            const nameInput = screen.getByPlaceholderText('Author name');
            await user.type(nameInput, 'John Smith');
            expect(nameInput).toHaveValue('John Smith');
        });
    });

  
    // ── Delete Paper ──────────────────────────────────────────────────────────

    describe('Delete Paper', () => {
        it('removes paper from list after delete', async () => {
            const user = userEvent.setup();
            mockPapersSuccess();
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Attention Is All You Need'));
            await user.click(screen.getAllByText('Delete')[0]);
            await waitFor(() => {
                expect(screen.queryByText('Attention Is All You Need')).not.toBeInTheDocument();
            });
        });

        it('shows error when delete fails', async () => {
            const user = userEvent.setup();
            mockPapersSuccess();
            mockFetch.mockRejectedValueOnce(new Error('Delete failed'));
            render(<AdminDashboard />);
            await waitFor(() => screen.getByText('Attention Is All You Need'));
            await user.click(screen.getAllByText('Delete')[0]);
            await waitFor(() => {
                expect(screen.getByText('Failed to delete paper.')).toBeInTheDocument();
            });
        });
    });


});
