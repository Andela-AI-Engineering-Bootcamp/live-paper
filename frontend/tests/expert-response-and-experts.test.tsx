// ─────────────────────────────────────────────────────────────────────────────
// expert-response.test.tsx
// ─────────────────────────────────────────────────────────────────────────────
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/router';
import ExpertResponse from '../pages/expert-response';

const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;
global.fetch = jest.fn();
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

const mockPaper = {
    id: 'paper-123',
    title: 'Attention Is All You Need',
    authors: [
        { name: 'Ashish Vaswani', email: 'vaswani@google.com' },
        { name: 'Noam Shazeer', email: '' },
    ],
    abstract: 'The dominant sequence transduction models...',
    paper_url: 'https://arxiv.org/abs/1706.03762',
    pdf_file: '',
};

function setupRouter(query = {}) {
    mockUseRouter.mockReturnValue({
        query: { paper_id: 'paper-123', expert_email: 'expert@university.edu', ...query },
        isReady: true,
        pathname: '/expert-response',
        replace: jest.fn(),
        push: jest.fn(),
    } as any);
}

function mockPaperSuccess() {
    mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPaper,
    } as Response);
}

function mockPaperNotFound() {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({}) } as Response);
}

function mockSubmitSuccess() {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) } as Response);
}

function mockSubmitFailure() {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({}) } as Response);
}

describe('ExpertResponse Page', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        setupRouter();
    });

    describe('Loading State', () => {
        it('shows loading spinner while fetching', () => {
            mockFetch.mockImplementationOnce(() => new Promise(() => {}));
            render(<ExpertResponse />);
            expect(screen.getByText(/Loading paper details/i)).toBeInTheDocument();
        });
    });

    describe('Error State', () => {
        it('shows error card when paper is not found', async () => {
            mockPaperNotFound();
            render(<ExpertResponse />);
            await waitFor(() => {
                expect(screen.getByText('Link Invalid')).toBeInTheDocument();
            });
        });

        it('shows descriptive error message', async () => {
            mockPaperNotFound();
            render(<ExpertResponse />);
            await waitFor(() => {
                expect(
                    screen.getByText(/We could not find the paper associated with this link/i)
                ).toBeInTheDocument();
            });
        });

        it('shows error when fetch throws a network error', async () => {
            mockFetch.mockRejectedValueOnce(new Error('Network error'));
            render(<ExpertResponse />);
            await waitFor(() => {
                expect(screen.getByText('Link Invalid')).toBeInTheDocument();
            });
        });
    });

    describe('Ready State — Form', () => {
        it('renders paper title', async () => {
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => {
                expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument();
            });
        });

        it('renders author names', async () => {
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => {
                expect(screen.getByText('Ashish Vaswani')).toBeInTheDocument();
                expect(screen.getByText('Noam Shazeer')).toBeInTheDocument();
            });
        });

        it('renders author email when present', async () => {
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => {
                expect(screen.getByText(/vaswani@google.com/i)).toBeInTheDocument();
            });
        });

        it('renders expert email in "Responding as" section', async () => {
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => {
                expect(screen.getByText('expert@university.edu')).toBeInTheDocument();
            });
        });

        it('renders the response textarea', async () => {
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => {
                expect(screen.getByPlaceholderText(/Share your expert insights/i)).toBeInTheDocument();
            });
        });

        it('submit button is disabled when textarea is empty', async () => {
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByText(/Submit Expert Response/i));
            const submitBtn = screen.getByRole('button', { name: /Submit Expert Response/i });
            expect(submitBtn).toBeDisabled();
        });

        it('submit button is enabled when textarea has content', async () => {
            const user = userEvent.setup();
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByPlaceholderText(/Share your expert insights/i));
            await user.type(
                screen.getByPlaceholderText(/Share your expert insights/i),
                'My expert response here.'
            );
            const submitBtn = screen.getByRole('button', { name: /Submit Expert Response/i });
            expect(submitBtn).not.toBeDisabled();
        });

        it('shows character count when typing', async () => {
            const user = userEvent.setup();
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByPlaceholderText(/Share your expert insights/i));
            await user.type(screen.getByPlaceholderText(/Share your expert insights/i), 'Hello');
            expect(screen.getByText(/5 characters/i)).toBeInTheDocument();
        });

        it('shows Markdown supported hint', async () => {
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByText('Markdown supported'));
        });

        it('shows disclaimer text', async () => {
            mockPaperSuccess();
            render(<ExpertResponse />);
            await waitFor(() =>
                screen.getByText(/By submitting, you agree your response may be shared/i)
            );
        });
    });

    describe('Submission', () => {
        it('shows success card after successful submission', async () => {
            const user = userEvent.setup();
            mockPaperSuccess();
            mockSubmitSuccess();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByPlaceholderText(/Share your expert insights/i));
            await user.type(
                screen.getByPlaceholderText(/Share your expert insights/i),
                'My detailed expert analysis.'
            );
            await user.click(screen.getByRole('button', { name: /Submit Expert Response/i }));
            await waitFor(() => {
                expect(screen.getByText(/Thank you for your response!/i)).toBeInTheDocument();
            });
        });

        it('shows expert email in success card', async () => {
            const user = userEvent.setup();
            mockPaperSuccess();
            mockSubmitSuccess();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByPlaceholderText(/Share your expert insights/i));
            await user.type(screen.getByPlaceholderText(/Share your expert insights/i), 'Response');
            await user.click(screen.getByRole('button', { name: /Submit Expert Response/i }));
            await waitFor(() => {
                expect(screen.getByText(/expert@university.edu/i)).toBeInTheDocument();
            });
        });

        it('sends correct payload to API', async () => {
            const user = userEvent.setup();
            mockPaperSuccess();
            mockSubmitSuccess();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByPlaceholderText(/Share your expert insights/i));
            await user.type(
                screen.getByPlaceholderText(/Share your expert insights/i),
                'Expert insight here.'
            );
            await user.click(screen.getByRole('button', { name: /Submit Expert Response/i }));
            await waitFor(() => {
                const postCalls = mockFetch.mock.calls.filter(
                    ([url, opts]) => (opts as RequestInit)?.method === 'POST'
                );
                expect(postCalls.length).toBe(1);
                const body = JSON.parse((postCalls[0][1] as RequestInit).body as string);
                expect(body.paper_id).toBe('paper-123');
                expect(body.expert_email).toBe('expert@university.edu');
                expect(body.response).toBe('Expert insight here.');
            });
        });

        it('shows inline submit error when API fails', async () => {
            const user = userEvent.setup();
            mockPaperSuccess();
            mockSubmitFailure();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByPlaceholderText(/Share your expert insights/i));
            await user.type(screen.getByPlaceholderText(/Share your expert insights/i), 'My response');
            await user.click(screen.getByRole('button', { name: /Submit Expert Response/i }));
            await waitFor(() => {
                expect(
                    screen.getByText(/Something went wrong submitting your response/i)
                ).toBeInTheDocument();
            });
        });

        it('re-enables form after failed submission', async () => {
            const user = userEvent.setup();
            mockPaperSuccess();
            mockSubmitFailure();
            render(<ExpertResponse />);
            await waitFor(() => screen.getByPlaceholderText(/Share your expert insights/i));
            await user.type(screen.getByPlaceholderText(/Share your expert insights/i), 'My response');
            await user.click(screen.getByRole('button', { name: /Submit Expert Response/i }));
            await waitFor(() => screen.getByText(/Something went wrong/i));
            const textarea = screen.getByPlaceholderText(/Share your expert insights/i);
            expect(textarea).not.toBeDisabled();
        });
    });

    describe('Nav & Branding', () => {
        it('renders LivePaper logo', () => {
            mockFetch.mockImplementationOnce(() => new Promise(() => {}));
            render(<ExpertResponse />);
            expect(screen.getByText('LivePaper')).toBeInTheDocument();
        });

        it('renders Expert Response label in nav', () => {
            mockFetch.mockImplementationOnce(() => new Promise(() => {}));
            render(<ExpertResponse />);
            expect(screen.getByText('Expert Response')).toBeInTheDocument();
        });
    });
});


// ─────────────────────────────────────────────────────────────────────────────
// experts.test.tsx
// ─────────────────────────────────────────────────────────────────────────────
import Experts from '../pages/experts';
import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

const mockUseUserExperts = useUser as jest.MockedFunction<typeof useUser>;
const mockUseRouterExperts = useRouter as jest.MockedFunction<typeof useRouter>;
const mockReplaceExperts = jest.fn();

const mockExperts = [
    {
        id: 'e1',
        name: 'Dr. Sarah Chen',
        email: 'sarah.chen@mit.edu',
        bio: 'Expert in machine learning and natural language processing.',
        papers: [
            {
                id: 'p1',
                title: 'Attention Is All You Need',
                authors: 'Vaswani et al.',
                abstract: 'The dominant sequence transduction...',
                paper_url: 'https://arxiv.org/abs/1706.03762',
                pdf_file: '',
            },
        ],
    },
    {
        id: 'e2',
        name: 'Prof. James Wilson',
        email: 'jwilson@stanford.edu',
        bio: '',
        papers: [],
    },
];

function setupExpertsAdmin() {
    mockUseUserExperts.mockReturnValue({
        user: { publicMetadata: { role: 'admin' } } as any,
        isLoaded: true,
        isSignedIn: true,
    } as any);
    mockUseRouterExperts.mockReturnValue({ replace: mockReplaceExperts, push: jest.fn() } as any);
}

function setupExpertsNonAdmin() {
    mockUseUserExperts.mockReturnValue({
        user: { publicMetadata: { role: 'user' } } as any,
        isLoaded: true,
        isSignedIn: true,
    } as any);
    mockUseRouterExperts.mockReturnValue({ replace: mockReplaceExperts, push: jest.fn() } as any);
}

describe('Experts Page', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        setupExpertsAdmin();
    });

    describe('Admin Guard', () => {
        it('redirects non-admin to /', async () => {
            setupExpertsNonAdmin();
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] } as Response);
            render(<Experts />);
            await waitFor(() => expect(mockReplaceExperts).toHaveBeenCalledWith('/'));
        });

        it('does not redirect admin users', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] } as Response);
            render(<Experts />);
            await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());
            expect(mockReplaceExperts).not.toHaveBeenCalled();
        });
    });

    describe('Layout', () => {
        it('renders Subject Experts heading', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] } as Response);
            render(<Experts />);
            await waitFor(() => expect(screen.getByText('Subject Experts')).toBeInTheDocument());
        });

        it('renders AdminNav', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] } as Response);
            render(<Experts />);
            await waitFor(() => expect(screen.getByTestId('admin-nav')).toBeInTheDocument());
        });

        it('renders footer', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] } as Response);
            render(<Experts />);
            await waitFor(() => expect(screen.getByTestId('footer')).toBeInTheDocument());
        });
    });

    describe('Experts List', () => {
        it('shows loading spinner initially', () => {
            mockFetch.mockImplementationOnce(() => new Promise(() => {}));
            render(<Experts />);
            expect(screen.getByText(/Loading experts/i)).toBeInTheDocument();
        });

        it('shows empty state when no experts', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] } as Response);
            render(<Experts />);
            await waitFor(() => expect(screen.getByText('No experts found.')).toBeInTheDocument());
        });

        it('renders expert names', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => {
                expect(screen.getByText('Dr. Sarah Chen')).toBeInTheDocument();
                expect(screen.getByText('Prof. James Wilson')).toBeInTheDocument();
            });
        });

        it('renders expert emails', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => {
                expect(screen.getByText('sarah.chen@mit.edu')).toBeInTheDocument();
            });
        });

        it('renders correct paper count badge', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => {
                expect(screen.getByText('1 paper')).toBeInTheDocument();
                expect(screen.getByText('0 papers')).toBeInTheDocument();
            });
        });

        it('renders expert initial avatar', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => {
                expect(screen.getByText('D')).toBeInTheDocument(); // Dr. Sarah Chen → D
                expect(screen.getByText('P')).toBeInTheDocument(); // Prof. James Wilson → P
            });
        });

        it('shows correct expert total count', async () => {
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => {
                expect(screen.getByText('2 experts total')).toBeInTheDocument();
            });
        });

        it('shows error when fetch fails', async () => {
            mockFetch.mockRejectedValueOnce(new Error('Network error'));
            render(<Experts />);
            await waitFor(() => {
                expect(screen.getByText('Failed to load experts.')).toBeInTheDocument();
            });
        });

        it('dismisses error when X clicked', async () => {
            const user = userEvent.setup();
            mockFetch.mockRejectedValueOnce(new Error('Network error'));
            render(<Experts />);
            await waitFor(() => screen.getByText('Failed to load experts.'));
            const closeBtn = screen.getByRole('button', { name: '' });
            await user.click(closeBtn);
            expect(screen.queryByText('Failed to load experts.')).not.toBeInTheDocument();
        });
    });

    describe('Expert Expansion', () => {
        it('expands expert card on click to show bio', async () => {
            const user = userEvent.setup();
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => screen.getByText('Dr. Sarah Chen'));
            await user.click(screen.getByText('Dr. Sarah Chen'));
            await waitFor(() => {
                expect(
                    screen.getByText(/Expert in machine learning/i)
                ).toBeInTheDocument();
            });
        });

        it('shows associated papers when expert is expanded', async () => {
            const user = userEvent.setup();
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => screen.getByText('Dr. Sarah Chen'));
            await user.click(screen.getByText('Dr. Sarah Chen'));
            await waitFor(() => {
                expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument();
            });
        });

        it('shows "No papers associated" for expert with no papers', async () => {
            const user = userEvent.setup();
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => screen.getByText('Prof. James Wilson'));
            await user.click(screen.getByText('Prof. James Wilson'));
            await waitFor(() => {
                expect(
                    screen.getByText(/No papers associated with this expert yet/i)
                ).toBeInTheDocument();
            });
        });

        it('collapses expert card on second click', async () => {
            const user = userEvent.setup();
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => screen.getByText('Dr. Sarah Chen'));
            await user.click(screen.getByText('Dr. Sarah Chen'));
            await waitFor(() => screen.getByText(/Expert in machine learning/i));
            await user.click(screen.getByText('Dr. Sarah Chen'));
            await waitFor(() => {
                expect(screen.queryByText(/Expert in machine learning/i)).not.toBeInTheDocument();
            });
        });

        it('only one expert expanded at a time', async () => {
            const user = userEvent.setup();
            mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockExperts } as Response);
            render(<Experts />);
            await waitFor(() => screen.getByText('Dr. Sarah Chen'));

            await user.click(screen.getByText('Dr. Sarah Chen'));
            await waitFor(() => screen.getByText(/Expert in machine learning/i));

            await user.click(screen.getByText('Prof. James Wilson'));
            await waitFor(() => {
                expect(screen.queryByText(/Expert in machine learning/i)).not.toBeInTheDocument();
                expect(screen.getByText(/No papers associated/i)).toBeInTheDocument();
            });
        });
    });
});
