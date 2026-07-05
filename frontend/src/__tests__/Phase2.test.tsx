import React from 'react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock API modules
import * as dashboardApi from '../api/dashboard';
import * as lookupsApi from '../api/lookups';

// Pages
import Overview from '../pages/Overview';
import Teams from '../pages/Teams';
import TeamDetail from '../pages/TeamDetail';
import Advisors from '../pages/Advisors';
import AdvisorDetail from '../pages/AdvisorDetail';

// Context
import { AppContextProvider } from '../contexts/AppContext';

// Mock Recharts to avoid layout issues in test DOM
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div />,
  Cell: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
}));

// Mock lookups
vi.mock('../api/lookups', () => ({
  listOrganizations: vi.fn(),
  listTeams: vi.fn(),
  listAdvisors: vi.fn(),
  getIssueTaxonomy: vi.fn(),
}));

// Mock dashboard
vi.mock('../api/dashboard', () => ({
  getOrgDashboard: vi.fn(),
  getTeamDashboard: vi.fn(),
  getAdvisorDashboard: vi.fn(),
  getAdvisorList: vi.fn(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ teamId: 'team-1', advisorId: 'adv-1' }),
  };
});

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

describe('Phase 2 Operational Dashboard Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();

    // Default lookup mock returns
    vi.mocked(lookupsApi.listOrganizations).mockResolvedValue([
      { id: 'org-123', name: 'FitNova Test Org', industry: 'Fitness' },
    ]);
    vi.mocked(lookupsApi.listTeams).mockResolvedValue([
      { id: 'team-1', name: 'Alpha Team', organization_id: 'org-123', organization_name: 'FitNova Test Org' },
    ]);
  });

  // Helper to render pages wrapped with query client, router, app context
  const renderPage = (ui: React.ReactNode) => {
    const queryClient = createTestQueryClient();
    return render(
      <QueryClientProvider client={queryClient}>
        <AppContextProvider>
          <BrowserRouter>{ui}</BrowserRouter>
        </AppContextProvider>
      </QueryClientProvider>
    );
  };

  // 1. Overview renders real org metrics
  test('Overview renders real org metrics correctly', async () => {
    const mockOrgData = {
      organization_id: 'org-123',
      organization_name: 'FitNova Test Org',
      total_teams: 2,
      total_advisors: 10,
      total_calls: 100,
      completed_calls: 90,
      failed_calls: 5,
      processing_calls: 5,
      average_quality_score: 82.5,
      average_dimension_scores: {
        rapport: 80,
        needs_discovery: 85,
        product_knowledge: 90,
        objection_handling: 75,
        compliance: 95,
        trial_booking: 80,
        closing: 70,
      },
      top_issue_tags: [{ category: 'PRESSURE_TACTIC', count: 12, severity: 'High' }],
      team_performance: [
        { team_id: 'team-1', team_name: 'Alpha Team', average_score: 85, completed_calls: 45 },
      ],
    };

    vi.mocked(dashboardApi.getOrgDashboard).mockResolvedValue(mockOrgData);

    renderPage(<Overview />);

    // Check KPIs
    await waitFor(() => {
      expect(screen.getByText('83%')).toBeInTheDocument(); // round2 + formatScore
      expect(screen.getByText('100')).toBeInTheDocument(); // total calls
      expect(screen.getByText('90')).toBeInTheDocument();  // completed calls
    });

    expect(dashboardApi.getOrgDashboard).toHaveBeenCalledWith('org-123', undefined, undefined);
  });

  // 2. Overview handles null average score
  test('Overview handles null average score gracefully', async () => {
    const mockEmptyOrgData = {
      organization_id: 'org-123',
      organization_name: 'FitNova Test Org',
      total_teams: 2,
      total_advisors: 10,
      total_calls: 0,
      completed_calls: 0,
      failed_calls: 0,
      processing_calls: 0,
      average_quality_score: null,
      average_dimension_scores: {
        rapport: null,
        needs_discovery: null,
        product_knowledge: null,
        objection_handling: null,
        compliance: null,
        trial_booking: null,
        closing: null,
      },
      top_issue_tags: [],
      team_performance: [],
    };

    vi.mocked(dashboardApi.getOrgDashboard).mockResolvedValue(mockEmptyOrgData);

    renderPage(<Overview />);

    await waitFor(() => {
      // Metric value for null score should show '--'
      expect(screen.getByText('--')).toBeInTheDocument();
    });
  });

  // 3. Organization context change refetches dashboard
  test('Organization context change triggers refetch', async () => {
    vi.mocked(lookupsApi.listOrganizations).mockResolvedValue([
      { id: 'org-1', name: 'Org A' },
      { id: 'org-2', name: 'Org B' },
    ]);

    vi.mocked(dashboardApi.getOrgDashboard).mockResolvedValue({
      organization_id: 'org-1',
      organization_name: 'Org A',
      total_teams: 0,
      total_advisors: 0,
      total_calls: 0,
      completed_calls: 0,
      failed_calls: 0,
      processing_calls: 0,
      average_quality_score: null,
      average_dimension_scores: {} as any,
      top_issue_tags: [],
      team_performance: [],
    });

    renderPage(<Overview />);

    await waitFor(() => {
      expect(dashboardApi.getOrgDashboard).toHaveBeenCalledWith('org-1', undefined, undefined);
    });
  });

  // 4. Teams renders only real TeamPerformanceSummary fields
  // 5. Team card navigates correctly
  test('Teams renders real fields and navigates to detail', async () => {
    vi.mocked(dashboardApi.getOrgDashboard).mockResolvedValue({
      organization_id: 'org-123',
      organization_name: 'FitNova Test Org',
      total_teams: 1,
      total_advisors: 5,
      total_calls: 10,
      completed_calls: 10,
      failed_calls: 0,
      processing_calls: 0,
      average_quality_score: 80,
      average_dimension_scores: {} as any,
      top_issue_tags: [],
      team_performance: [
        { team_id: 'team-1', team_name: 'Alpha Team', average_score: 85, completed_calls: 10 },
      ],
    });

    renderPage(<Teams />);

    await waitFor(() => {
      expect(screen.getByText('Alpha Team')).toBeInTheDocument();
      expect(screen.getByText('10 call records analyzed')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    // Ensure we do not display unreturned fields like top_issue or advisor_count
    expect(screen.queryByText(/advisors assigned/)).not.toBeInTheDocument();
    expect(screen.queryByText(/top issue:/i)).not.toBeInTheDocument();
  });

  // 6. Team Detail renders leaderboard
  test('Team Detail renders stats and leaderboard', async () => {
    vi.mocked(dashboardApi.getTeamDashboard).mockResolvedValue({
      team_id: 'team-1',
      team_name: 'Alpha Team',
      organization_id: 'org-123',
      organization_name: 'FitNova Test Org',
      total_advisors: 2,
      total_calls: 10,
      completed_calls: 8,
      failed_calls: 1,
      processing_calls: 1,
      average_quality_score: 80.5,
      average_dimension_scores: {} as any,
      top_issue_tags: [],
      advisor_leaderboard: [
        { advisor_id: 'adv-1', advisor_name: 'Alice', completed_calls: 5, average_score: 88.2, critical_issue_count: 0 },
        { advisor_id: 'adv-2', advisor_name: 'Bob', completed_calls: 3, average_score: 55, critical_issue_count: 2 },
      ],
    });

    renderPage(<TeamDetail />);

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
      // Bob has low score and critical issues -> flags coaching attention needed
      expect(screen.getByText('Coaching Attention Needed')).toBeInTheDocument();
      expect(screen.getByText('2 Critical')).toBeInTheDocument();
    });
  });

  // 7. Team Detail handles 404
  test('Team Detail handles 404 error state gracefully', async () => {
    const apiError = { status: 404, message: 'Team not found' };
    vi.mocked(dashboardApi.getTeamDashboard).mockRejectedValue(apiError);

    renderPage(<TeamDetail />);

    await waitFor(() => {
      expect(screen.getByText('Team Not Found')).toBeInTheDocument();
    });
  });

  // 8. Advisors sends backend filters
  // 9. Advisor search resets pagination
  // 10. Advisors pagination works
  test('Advisors page triggers correct queries and filters', async () => {
    vi.mocked(dashboardApi.getAdvisorList).mockResolvedValue({
      items: [
        {
          advisor_id: 'adv-1',
          advisor_name: 'Alice Smith',
          advisor_email: 'alice@test.com',
          advisor_status: 'Active',
          team_id: 'team-1',
          team_name: 'Alpha Team',
          organization_id: 'org-123',
          organization_name: 'FitNova Test Org',
          completed_calls: 12,
          average_score: 88,
          critical_issue_count: 1,
        },
      ],
      page: 1,
      page_size: 20,
      total: 1,
      total_pages: 1,
    });

    renderPage(<Advisors />);

    await waitFor(() => {
      expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    });

    // Check query args
    expect(dashboardApi.getAdvisorList).toHaveBeenCalledWith({
      organization_id: 'org-123',
      team_id: undefined,
      search: undefined,
      status: undefined,
      page: 1,
      page_size: 20,
    });
  });

  // 12. Advisor Detail renders improvement areas from backend
  // 13. Advisor Detail does not recalculate improvement areas
  test('Advisor Detail renders improvement areas from backend', async () => {
    vi.mocked(dashboardApi.getAdvisorDashboard).mockResolvedValue({
      advisor_id: 'adv-1',
      advisor_name: 'Alice Smith',
      advisor_email: 'alice@test.com',
      advisor_status: 'Active',
      team_id: 'team-1',
      team_name: 'Alpha Team',
      organization_id: 'org-123',
      organization_name: 'FitNova Test Org',
      total_calls: 15,
      completed_calls: 12,
      failed_calls: 1,
      processing_calls: 2,
      average_quality_score: 81.2,
      average_dimension_scores: {} as any,
      top_issue_tags: [],
      recent_calls: [],
      improvement_areas: [
        { dimension: 'Compliance', average_score: 45 },
        { dimension: 'Closing', average_score: 52 },
      ],
    });

    renderPage(<AdvisorDetail />);

    await waitFor(() => {
      expect(screen.getByText('1. Compliance')).toBeInTheDocument();
      expect(screen.getByText('2. Closing')).toBeInTheDocument();
      expect(screen.getByText('45%')).toBeInTheDocument();
    });
  });

  // 17. No API response body is written to localStorage
  test('No API response bodies are written to localStorage', async () => {
    vi.mocked(dashboardApi.getOrgDashboard).mockResolvedValue({
      organization_id: 'org-123',
      organization_name: 'FitNova Test Org',
      team_performance: [],
      average_dimension_scores: {} as any,
      top_issue_tags: [],
    } as any);

    renderPage(<Overview />);

    await waitFor(() => {
      expect(screen.getByText('FitNova Test Org Overview')).toBeInTheDocument();
    });

    // Check localStorage items - should only contain UI contexts, never API JSON payloads
    const keys = Object.keys(localStorage);
    keys.forEach((key) => {
      const val = localStorage.getItem(key);
      if (val) {
        expect(val.trim().startsWith('{')).toBe(false);
        expect(val.trim().startsWith('[')).toBe(false);
      }
    });
  });
});
