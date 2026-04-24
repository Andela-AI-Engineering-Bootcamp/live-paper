import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ResearchChat from '../components/ResearchChat';

// ── Global fetch mock ─────────────────────────────────────────────────────────
global.fetch = jest.fn();

const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

// ── Helper: mock a successful chat API response ───────────────────────────────
function mockChatSuccess(response = 'Here is what I found about your query.', session_id = 'session-abc-123') {
    mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ response, session_id }),
    } as Response);
}

// ── Helper: mock a failed chat API response ───────────────────────────────────
function mockChatFailure() {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
}

function mockChatHttpError() {
    mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' }),
    } as Response);
}

// ── Setup / teardown ──────────────────────────────────────────────────────────
beforeEach(() => {
    jest.clearAllMocks();
    // Default: avatar.jpg does not exist
    mockFetch.mockResolvedValue({
        ok: false,
        json: async () => ({}),
    } as Response);
});

// ── Test suites ───────────────────────────────────────────────────────────────

describe('ResearchChat — Empty State', () => {
    it('renders the welcome heading on initial load', () => {
        render(<ResearchChat />);
        expect(screen.getByText('What would you like to explore?')).toBeInTheDocument();
    });

    it('renders the subtitle text', () => {
        render(<ResearchChat />);
        expect(
            screen.getByText(/Ask about research papers, request author connections/i)
        ).toBeInTheDocument();
    });

    it('renders all four suggestion chips', () => {
        render(<ResearchChat />);
        expect(screen.getByText(/Summarize recent papers on transformer architectures/i)).toBeInTheDocument();
        expect(screen.getByText(/Find papers about climate change mitigation/i)).toBeInTheDocument();
        expect(screen.getByText(/Connect me with authors researching CRISPR/i)).toBeInTheDocument();
        expect(screen.getByText(/What are the latest findings in quantum computing/i)).toBeInTheDocument();
    });

    it('renders the textarea input', () => {
        render(<ResearchChat />);
        expect(screen.getByPlaceholderText(/Ask about research papers/i)).toBeInTheDocument();
    });

    it('renders the send button', () => {
        render(<ResearchChat />);
        // Send button is the one with the Send icon — it's a button near the textarea
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThan(0);
    });

    it('send button is disabled when input is empty', () => {
        render(<ResearchChat />);
        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        expect(textarea).toHaveValue('');
        // The send button should be disabled (opacity-30 via disabled state)
        const sendButton = screen.getByRole('button', { name: '' }); // icon-only button
        // It won't be in the DOM as disabled unless we check the actual button
        const allButtons = screen.getAllByRole('button');
        const sendBtn = allButtons[allButtons.length - 1]; // last button is Send
        expect(sendBtn).toBeDisabled();
    });
});

describe('ResearchChat — Suggestion Chips', () => {
    it('clicking a suggestion chip populates the textarea', async () => {
        const user = userEvent.setup();
        render(<ResearchChat />);

        const chip = screen.getByText(/Summarize recent papers on transformer architectures/i);
        await user.click(chip);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        expect(textarea).toHaveValue('Summarize recent papers on transformer architectures');
    });

    it('clicking a chip enables the send button', async () => {
        const user = userEvent.setup();
        render(<ResearchChat />);

        const chip = screen.getByText(/Find papers about climate change mitigation/i);
        await user.click(chip);

        const allButtons = screen.getAllByRole('button');
        const sendBtn = allButtons[allButtons.length - 1];
        expect(sendBtn).not.toBeDisabled();
    });
});

describe('ResearchChat — Textarea Behaviour', () => {
    it('typing in the textarea updates its value', async () => {
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'Tell me about CRISPR');
        expect(textarea).toHaveValue('Tell me about CRISPR');
    });

    it('Shift+Enter does not submit the form', async () => {
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'Hello');
        await user.keyboard('{Shift>}{Enter}{/Shift}');

        // fetch should NOT have been called for chat (only for avatar HEAD check)
        const chatCalls = mockFetch.mock.calls.filter(
            ([url]) => typeof url === 'string' && url.includes('/chat')
        );
        expect(chatCalls.length).toBe(0);
    });

    it('Enter submits the message when input is non-empty', async () => {
        mockChatSuccess();
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'What is CRISPR?');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            const chatCalls = mockFetch.mock.calls.filter(
                ([url]) => typeof url === 'string' && url.includes('/chat')
            );
            expect(chatCalls.length).toBe(1);
        });
    });

    it('Enter does not submit when input is empty', async () => {
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.click(textarea);
        await user.keyboard('{Enter}');

        const chatCalls = mockFetch.mock.calls.filter(
            ([url]) => typeof url === 'string' && url.includes('/chat')
        );
        expect(chatCalls.length).toBe(0);
    });
});

describe('ResearchChat — Sending Messages', () => {
    it('displays the user message after sending', async () => {
        mockChatSuccess();
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'Tell me about transformer models');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            expect(screen.getByText('Tell me about transformer models')).toBeInTheDocument();
        });
    });

    it('clears the textarea after sending', async () => {
        mockChatSuccess();
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'Hello');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            expect(textarea).toHaveValue('');
        });
    });

    it('displays the assistant response after API call', async () => {
        mockChatSuccess('Transformers use self-attention mechanisms.');
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'What are transformers?');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            expect(screen.getByText('Transformers use self-attention mechanisms.')).toBeInTheDocument();
        });
    });

    it('calls the API with the correct payload', async () => {
        mockChatSuccess();
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'What is RAG?');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            const chatCalls = mockFetch.mock.calls.filter(
                ([url]) => typeof url === 'string' && url.includes('/chat')
            );
            expect(chatCalls.length).toBe(1);

            const [, options] = chatCalls[0];
            const body = JSON.parse((options as RequestInit).body as string);
            expect(body.message).toBe('What is RAG?');
        });
    });

    it('includes session_id in subsequent messages', async () => {
        mockChatSuccess('First response', 'session-xyz');
        mockChatSuccess('Second response', 'session-xyz');
        const user = userEvent.setup();
        render(<ResearchChat />);

        // First message
        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'First question');
        await user.keyboard('{Enter}');
        await waitFor(() => screen.getByText('First response'));

        // Second message
        await user.type(textarea, 'Follow up question');
        await user.keyboard('{Enter}');
        await waitFor(() => screen.getByText('Second response'));

        const chatCalls = mockFetch.mock.calls.filter(
            ([url]) => typeof url === 'string' && url.includes('/chat')
        );
        const secondBody = JSON.parse((chatCalls[1][1] as RequestInit).body as string);
        expect(secondBody.session_id).toBe('session-xyz');
    });

    it('shows loading dots while awaiting response', async () => {
        // Never resolve — keeps loading state active
        mockFetch.mockImplementationOnce(
            () => new Promise(() => {})
        );
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'Loading test');
        await user.keyboard('{Enter}');

        // Loading dots are spans with animate-bounce
        await waitFor(() => {
            const bouncingDots = document.querySelectorAll('.animate-bounce');
            expect(bouncingDots.length).toBe(3);
        });
    });

    it('disables textarea while loading', async () => {
        mockFetch.mockImplementationOnce(() => new Promise(() => {}));
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'Test');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            expect(textarea).toBeDisabled();
        });
    });
});

describe('ResearchChat — Error Handling', () => {
    it('shows error message when network request fails', async () => {
        mockChatFailure();
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'This will fail');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            expect(
                screen.getByText(/Sorry, I encountered an error. Please try again./i)
            ).toBeInTheDocument();
        });
    });

    it('shows error message when API returns non-ok response', async () => {
        mockChatHttpError();
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'HTTP error test');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            expect(
                screen.getByText(/Sorry, I encountered an error. Please try again./i)
            ).toBeInTheDocument();
        });
    });

    it('re-enables textarea after an error', async () => {
        mockChatFailure();
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'Error test');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            expect(textarea).not.toBeDisabled();
        });
    });
});

describe('ResearchChat — Multiple Messages', () => {
    it('renders multiple user and assistant messages', async () => {
        mockChatSuccess('Answer one', 'sess-1');
        mockChatSuccess('Answer two', 'sess-1');
        const user = userEvent.setup();
        render(<ResearchChat />);

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);

        await user.type(textarea, 'Question one');
        await user.keyboard('{Enter}');
        await waitFor(() => screen.getByText('Answer one'));

        await user.type(textarea, 'Question two');
        await user.keyboard('{Enter}');
        await waitFor(() => screen.getByText('Answer two'));

        expect(screen.getByText('Question one')).toBeInTheDocument();
        expect(screen.getByText('Question two')).toBeInTheDocument();
        expect(screen.getByText('Answer one')).toBeInTheDocument();
        expect(screen.getByText('Answer two')).toBeInTheDocument();
    });

    it('hides the empty state once a message is sent', async () => {
        mockChatSuccess();
        const user = userEvent.setup();
        render(<ResearchChat />);

        expect(screen.getByText('What would you like to explore?')).toBeInTheDocument();

        const textarea = screen.getByPlaceholderText(/Ask about research papers/i);
        await user.type(textarea, 'First message');
        await user.keyboard('{Enter}');

        await waitFor(() => {
            expect(screen.queryByText('What would you like to explore?')).not.toBeInTheDocument();
        });
    });
});

describe('ResearchChat — Disclaimer', () => {
    it('renders the disclaimer text', () => {
        render(<ResearchChat />);
        expect(
            screen.getByText(/LivePaper may make mistakes/i)
        ).toBeInTheDocument();
    });
});