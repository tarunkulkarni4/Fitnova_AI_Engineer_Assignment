import { apiClient } from './client';
import {
  OrganizationDashboardResponse,
  TeamDashboardResponse,
  AdvisorDashboardResponse,
  CallReviewResponse,
  PaginatedCallListResponse,
  PaginatedAdvisorListResponse,
} from '../types/dashboard';

export async function getOrgDashboard(
  orgId: string,
  startDate?: string,
  endDate?: string,
  teamId?: string,
): Promise<OrganizationDashboardResponse> {
  const response = await apiClient.get<OrganizationDashboardResponse>(`/dashboard/org/${orgId}`, {
    params: { start_date: startDate, end_date: endDate, team_id: teamId || undefined },
  });
  return response.data;
}

export async function getTeamDashboard(
  teamId: string,
  startDate?: string,
  endDate?: string
): Promise<TeamDashboardResponse> {
  const response = await apiClient.get<TeamDashboardResponse>(`/dashboard/team/${teamId}`, {
    params: { start_date: startDate, end_date: endDate },
  });
  return response.data;
}

export async function getAdvisorDashboard(
  advisorId: string,
  startDate?: string,
  endDate?: string
): Promise<AdvisorDashboardResponse> {
  const response = await apiClient.get<AdvisorDashboardResponse>(`/dashboard/advisor/${advisorId}`, {
    params: { start_date: startDate, end_date: endDate },
  });
  return response.data;
}

export async function getCallReview(callId: string): Promise<CallReviewResponse> {
  const response = await apiClient.get<CallReviewResponse>(`/dashboard/calls/${callId}`);
  return response.data;
}

export async function getCallList(params: {
  page?: number;
  page_size?: number;
  organization_id?: string;
  team_id?: string;
  advisor_id?: string;
  processing_status?: string;
  severity?: string;
  issue_category?: string;
  min_score?: number;
  max_score?: number;
  start_date?: string;
  end_date?: string;
  has_source_reference?: boolean;
  sort?: string;
}): Promise<PaginatedCallListResponse> {
  const response = await apiClient.get<PaginatedCallListResponse>('/dashboard/calls', {
    params,
  });
  return response.data;
}

export async function getAdvisorList(params: {
  page?: number;
  page_size?: number;
  organization_id?: string;
  team_id?: string;
  search?: string;
  status?: string;
}): Promise<PaginatedAdvisorListResponse> {
  const response = await apiClient.get<PaginatedAdvisorListResponse>('/dashboard/advisors', {
    params,
  });
  return response.data;
}
