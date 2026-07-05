import { apiClient } from './client';
import { OrganizationLookup, TeamLookup, AdvisorLookup, IssueTaxonomyItem } from '../types/lookup';

export async function listOrganizations(): Promise<OrganizationLookup[]> {
  const response = await apiClient.get<OrganizationLookup[]>('/lookups/organizations');
  return response.data;
}

export async function listTeams(organizationId?: string): Promise<TeamLookup[]> {
  const response = await apiClient.get<TeamLookup[]>('/lookups/teams', {
    params: { organization_id: organizationId },
  });
  return response.data;
}

export async function listAdvisors(params?: {
  organization_id?: string;
  team_id?: string;
  search?: string;
  status?: string;
}): Promise<AdvisorLookup[]> {
  const response = await apiClient.get<AdvisorLookup[]>('/lookups/advisors', {
    params,
  });
  return response.data;
}

export async function getIssueTaxonomy(): Promise<IssueTaxonomyItem[]> {
  const response = await apiClient.get<IssueTaxonomyItem[]>('/lookups/issue-taxonomy');
  return response.data;
}
