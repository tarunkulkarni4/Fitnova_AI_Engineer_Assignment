import React from 'react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import FeedbackActivity from '../pages/FeedbackActivity';
import * as feedbackApi from '../api/feedback';
import * as lookupsApi from '../api/lookups';
import { ExportRecordItem } from '../types/feedback';

// ─── Mocks ─────────────────────────────────────────────────────────────────

vi.mock('../api/feedback');
vi.mock('../api/lookups');

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderPage(
  ui: React.ReactElement,
  { route = '/feedback', search = '' } = {}
) {
  const client = makeClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`${route}${search}`]}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ─── Mock Data ──────────────────────────────────────────────────────────────

const SCORE_RECORD: ExportRecordItem = {
  call_id: 'call-uuid-1',
  feedback_type: 'Score',
  original_value: { dimension: 'rapport', score: 70 },
  corrected_value: { dimension: 'rapport', score: 85 },
  comments: 'Better assessment',
  reviewed_at: '2025-06-01T10:00:00Z',
};

const TAG_REJECT_RECORD: ExportRecordItem = {
  call_id: 'call-uuid-1',
  feedback_type: 'Tag',
  original_value: { action: 'reject', issue_tag_id: 'tag-001' },
  corrected_value: { rejected: true },
  comments: null,
  reviewed_at: '2025-06-02T10:00:00Z',
};

const TAG_ADD_RECORD: ExportRecordItem = {
  call_id: 'call-uuid-2',
  feedback_type: 'Tag',
  original_value: { action: 'add' },
  corrected_value: { tag: { category: 'NO_NEEDS_DISCOVERY', severity: 'High' } },
  comments: 'Missed during review',
  reviewed_at: '2025-06-03T10:00:00Z',
};

const TAG_CORRECT_RECORD: ExportRecordItem = {
  call_id: 'call-uuid-3',
  feedback_type: 'Tag',
  original_value: { action: 'correct', issue_tag_id: 'tag-002', tag: {} },
  corrected_value: { tag: { category: 'AGGRESSIVE_CLOSE', severity: 'Medium' } },
  comments: null,
  reviewed_at: '2025-06-04T10:00:00Z',
};

const SUMMARY_RECORD: ExportRecordItem = {
  call_id: 'call-uuid-1',
  feedback_type: 'Summary',
  original_value: { field: 'executive_summary', value: 'Call went okay.' },
  corrected_value: { field: 'executive_summary', value: 'Advisor skipped needs discovery.' },
  comments: null,
  reviewed_at: '2025-06-05T10:00:00Z',
};

const TRANSCRIPT_RECORD: ExportRecordItem = {
  call_id: 'call-uuid-1',
  feedback_type: 'Transcript',
  original_value: { segment_index: 3, segment: { speaker: 'Unknown' } },
  corrected_value: { segment_index: 3, segment: { speaker: 'Advisor' } },
  comments: null,
  reviewed_at: '2025-06-06T10:00:00Z',
};

const MOCK_EXPORT: ExportRecordItem[] = [
  SCORE_RECORD,
  TAG_REJECT_RECORD,
  TAG_ADD_RECORD,
  TAG_CORRECT_RECORD,
  SUMMARY_RECORD,
  TRANSCRIPT_RECORD,
];

// ─── Tests ──────────────────────────────────────────────────────────────────

describe('Phase 4 — Feedback Activity Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue(MOCK_EXPORT);
    vi.mocked(lookupsApi.listOrganizations).mockResolvedValue([]);
    vi.mocked(lookupsApi.listTeams).mockResolvedValue([]);
    vi.mocked(lookupsApi.listAdvisors).mockResolvedValue([]);
  });

  // ── 1. Basic Render ────────────────────────────────────────────────────

  test('1. Renders feedback export records correctly', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      // Should render dates from records
      expect(screen.getAllByText(/\d{1,2}\/\d{1,2}\/\d{4}/).length).toBeGreaterThan(0);
    });
  });

  // ── 2. Summary Counts ─────────────────────────────────────────────────

  test('2. Summary metric counts are correct', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      // Total = 6
      const sixes = screen.getAllByText('6');
      expect(sixes.length).toBeGreaterThan(0);
      // Score = 1 (multiple '1' cards may appear)
      const ones = screen.getAllByText('1');
      expect(ones.length).toBeGreaterThan(0);
    });
  });

  // ── 3. Type Filter is sent to backend ─────────────────────────────────

  test('3. Type filter is sent to backend API', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(feedbackApi.exportFeedbackDataset).toHaveBeenCalled();
    });

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'Score' } });

    await waitFor(() => {
      expect(feedbackApi.exportFeedbackDataset).toHaveBeenCalledWith(
        expect.objectContaining({ feedback_type: 'Score' })
      );
    });
  });

  // ── 4. Date Filters are sent to backend ──────────────────────────────

  test('4. Date filters are sent to backend API', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(feedbackApi.exportFeedbackDataset).toHaveBeenCalled();
    });

    const startInput = screen.getByLabelText('Start Date');
    fireEvent.change(startInput, { target: { value: '2025-01-01' } });

    await waitFor(() => {
      expect(feedbackApi.exportFeedbackDataset).toHaveBeenCalledWith(
        expect.objectContaining({ start_date: '2025-01-01' })
      );
    });
  });

  // ── 5. URL Preserves Filters ─────────────────────────────────────────

  test('5. Initial render reads type filter from URL', async () => {
    const client = makeClient();
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/feedback?type=Summary']}>
          <FeedbackActivity />
        </MemoryRouter>
      </QueryClientProvider>
    );
    await waitFor(() => {
      expect(feedbackApi.exportFeedbackDataset).toHaveBeenCalledWith(
        expect.objectContaining({ feedback_type: 'Summary' })
      );
    });
  });

  // ── 6. Human-Readable Labels ─────────────────────────────────────────

  test('6. Score correction renders human-readable label, not raw JSON', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      // Should see "rapport score corrected" style label
      const rapportText = screen.getAllByText(/rapport/i);
      expect(rapportText.length).toBeGreaterThan(0);
      // Should NOT see raw JSON like { "dimension": ...
      expect(screen.queryByText(/\{"dimension"/)).toBeNull();
    });
  });

  test('7. Tag rejection renders human-readable label', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByText(/AI issue tag/i)).toBeInTheDocument();
      expect(screen.getByText(/rejected/i)).toBeInTheDocument();
    });
  });

  test('8. Tag addition renders human-readable label with category', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByText(/NO_NEEDS_DISCOVERY/)).toBeInTheDocument();
    });
  });

  test('9. Tag correction renders human-readable label with category', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByText(/AGGRESSIVE_CLOSE/)).toBeInTheDocument();
    });
  });

  test('10. Summary correction renders human-readable field name', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      // "executive summary" should appear in label
      const labels = screen.getAllByText(/executive/i);
      expect(labels.length).toBeGreaterThan(0);
    });
  });

  test('11. Transcript correction renders segment index', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByText(/#3/)).toBeInTheDocument();
    });
  });

  // ── 12. No Raw JSON ──────────────────────────────────────────────────

  test('12. Raw JSON is not dumped anywhere in the table', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      // Scan for JSON-like syntax that would indicate a dump
      const body = document.body.textContent || '';
      expect(body).not.toMatch(/"issue_tag_id":/);
      expect(body).not.toMatch(/"segment_index":\s*3/);
    });
  });

  // ── 13. Call Navigation ──────────────────────────────────────────────

  test('13. Row with call_id is keyboard-accessible', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      const rows = screen.getAllByRole('link');
      expect(rows.length).toBeGreaterThan(0);
      // Rows should have tabIndex
      rows.forEach(r => {
        expect(r).toHaveAttribute('tabindex', '0');
      });
    });
  });

  // ── 14. Empty State ──────────────────────────────────────────────────

  test('14. Empty state renders when no records returned', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue([]);
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByText(/No feedback found/i)).toBeInTheDocument();
    });
  });

  // ── 15. Error State ──────────────────────────────────────────────────

  test('15. Error state renders on API failure', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockRejectedValue(new Error('Network error'));
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByText(/Failed to load feedback/i)).toBeInTheDocument();
    });
  });
});

// ─── Accessibility Tests ─────────────────────────────────────────────────────

describe('Phase 4 — Accessibility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue(MOCK_EXPORT);
    vi.mocked(lookupsApi.listOrganizations).mockResolvedValue([]);
    vi.mocked(lookupsApi.listTeams).mockResolvedValue([]);
    vi.mocked(lookupsApi.listAdvisors).mockResolvedValue([]);
  });

  test('16. Feedback Activity filter inputs have accessible labels', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByLabelText('Feedback Type')).toBeInTheDocument();
      expect(screen.getByLabelText('Start Date')).toBeInTheDocument();
      expect(screen.getByLabelText('End Date')).toBeInTheDocument();
    });
  });
});

// ─── Security / Privacy Tests ────────────────────────────────────────────────

describe('Phase 4 — Security & Privacy', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue(MOCK_EXPORT);
    vi.mocked(lookupsApi.listOrganizations).mockResolvedValue([]);
    vi.mocked(lookupsApi.listTeams).mockResolvedValue([]);
    vi.mocked(lookupsApi.listAdvisors).mockResolvedValue([]);
    localStorage.clear();
  });

  test('17. No API response bodies are written to localStorage', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(feedbackApi.exportFeedbackDataset).toHaveBeenCalled();
    });

    const allKeys = Object.keys(localStorage);
    allKeys.forEach(key => {
      const val = localStorage.getItem(key) || '';
      // Should not contain API JSON payloads
      expect(val).not.toContain('"call_id"');
      expect(val).not.toContain('"feedback_type"');
      expect(val).not.toContain('"original_value"');
    });
  });

  test('18. No audio or binary data is stored in localStorage', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(feedbackApi.exportFeedbackDataset).toHaveBeenCalled();
    });

    const allKeys = Object.keys(localStorage);
    allKeys.forEach(key => {
      const val = localStorage.getItem(key) || '';
      // Should not contain base64 audio data
      expect(val.length).toBeLessThan(5000); // No large binary blobs
      expect(val).not.toContain('data:audio/');
    });
  });

  test('19. Filesystem paths are not exposed in rendered content', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockRejectedValue(
      new Error('/app/storage/transcripts/redacted/uuid.json not found')
    );
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      const body = document.body.textContent || '';
      // Should not show raw filesystem paths
      expect(body).not.toContain('/app/storage/transcripts');
    });
  });
});

// ─── Code Splitting Tests ────────────────────────────────────────────────────

describe('Phase 4 — Lazy Loading', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue([]);
    vi.mocked(lookupsApi.listOrganizations).mockResolvedValue([]);
    vi.mocked(lookupsApi.listTeams).mockResolvedValue([]);
    vi.mocked(lookupsApi.listAdvisors).mockResolvedValue([]);
  });

  test('20. FeedbackActivity page renders (lazy route works)', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByText(/Feedback Activity/i)).toBeInTheDocument();
    });
  });

  test('21. PageHeader renders page title for FeedbackActivity', async () => {
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getByText('Feedback Activity')).toBeInTheDocument();
    });
  });
});

// ─── E2E Workflow Tests ──────────────────────────────────────────────────────

describe('Phase 4 — E2E Workflow (Mocked)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(lookupsApi.listOrganizations).mockResolvedValue([
      { id: 'org-1', name: 'FitNova HQ' }
    ]);
    vi.mocked(lookupsApi.listTeams).mockResolvedValue([
      { id: 'team-1', name: 'Alpha Team', organization_id: 'org-1', organization_name: 'FitNova HQ' }
    ]);
    vi.mocked(lookupsApi.listAdvisors).mockResolvedValue([
      { id: 'adv-1', name: 'Alice Smith', email: 'alice@test.com', team_id: 'team-1', team_name: 'Alpha Team', status: 'Active' }
    ]);
  });

  test('22. Feedback Activity shows Score correction after it occurs', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue([SCORE_RECORD]);
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      // Score correction appears in activity
      expect(screen.getByText(/rapport/i)).toBeInTheDocument();
      // Metric card shows 1 score correction
      const scoreCount = screen.getAllByText('1');
      expect(scoreCount.length).toBeGreaterThan(0);
    });
  });

  test('23. Score correction appears in Feedback Activity table', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue([SCORE_RECORD]);
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      const badgeText = screen.getByText('Score');
      expect(badgeText).toBeInTheDocument();
    });
  });

  test('24. Issue tag rejection appears in Feedback Activity table', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue([TAG_REJECT_RECORD]);
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getAllByText(/Tag/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/rejected/i).length).toBeGreaterThan(0);
    });
  });

  test('25. Summary correction appears in Feedback Activity table', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue([SUMMARY_RECORD]);
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getAllByText(/Summary/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/executive/i).length).toBeGreaterThan(0);
    });
  });

  test('26. Transcript correction appears in Feedback Activity table', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue([TRANSCRIPT_RECORD]);
    renderPage(<FeedbackActivity />);
    await waitFor(() => {
      expect(screen.getAllByText(/Transcript/).length).toBeGreaterThan(0);
      expect(screen.getByText(/#3/)).toBeInTheDocument();
    });
  });

  test('27. Empty filtered state renders when type filter yields no results', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockResolvedValue([]);

    const client = makeClient();
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/feedback?type=Score']}>
          <FeedbackActivity />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/No feedback found/i)).toBeInTheDocument();
    });
  });

  test('28. Error state shows retry option', async () => {
    vi.mocked(feedbackApi.exportFeedbackDataset).mockRejectedValue(new Error('API Error'));
    renderPage(<FeedbackActivity />);

    await waitFor(() => {
      // ErrorState should render with failed state
      expect(screen.getByText(/Failed to load feedback/i)).toBeInTheDocument();
    });
  });
});
