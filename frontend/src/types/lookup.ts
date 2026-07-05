export interface OrganizationLookup {
  id: string;
  name: string;
  industry?: string | null;
}

export interface TeamLookup {
  id: string;
  name: string;
  organization_id: string;
  organization_name: string;
}

export interface AdvisorLookup {
  id: string;
  name: string;
  email: string;
  status: string;
  team_id: string;
  team_name: string;
}

export interface IssueTaxonomyItem {
  category: string;
  label: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  absence_based: boolean;
}
