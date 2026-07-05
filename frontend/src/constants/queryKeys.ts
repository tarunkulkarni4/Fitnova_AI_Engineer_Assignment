export const QUERY_KEYS = {
  // Lookups
  organizations: 'organizations',
  teamsLookup: (orgId?: string) => ['teams-lookup', orgId || 'all'] as const,
  advisorsLookup: (teamId?: string, orgId?: string) => ['advisors-lookup', teamId || 'all', orgId || 'all'] as const,
  taxonomy: 'taxonomy',

  // Dashboards
  orgDashboard: (orgId: string, startDate?: string, endDate?: string, teamId?: string) => 
    ['org-dashboard', orgId, startDate || '', endDate || '', teamId || 'all'] as const,
  teamDashboard: (teamId: string, startDate?: string, endDate?: string) => 
    ['team-dashboard', teamId, startDate || '', endDate || ''] as const,
  advisorDashboard: (advisorId: string, startDate?: string, endDate?: string) => 
    ['advisor-dashboard', advisorId, startDate || '', endDate || ''] as const,
  advisorList: (filters: { orgId?: string; teamId?: string; search?: string; status?: string; page: number; pageSize: number }) =>
    ['advisor-list', filters] as const,

  // Calls
  callList: (filters: any) => ['calls-list', filters] as const,
  callReview: (callId: string) => ['call-review', callId] as const,

  // Feedback
  feedbackReviewed: (callId: string) => ['feedback-reviewed', callId] as const,
  feedbackHistory: (callId: string) => ['feedback-history', callId] as const,
  feedbackExport: (filters: { type?: string; teamId?: string; startDate?: string; endDate?: string }) => 
    ['feedback-export', filters] as const,
};
