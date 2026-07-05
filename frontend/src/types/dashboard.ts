export interface DimensionAverages {
  rapport: number | null;
  needs_discovery: number | null;
  product_knowledge: number | null;
  objection_handling: number | null;
  compliance: number | null;
  trial_booking: number | null;
  closing: number | null;
}

export interface IssueTagCount {
  category: string;
  count: number;
  severity: string;
}

export interface TeamPerformanceSummary {
  team_id: string;
  team_name: string;
  average_score: number | null;
  completed_calls: number;
}

export interface AdvisorPerformanceSummary {
  advisor_id: string;
  advisor_name: string;
  completed_calls: number;
  average_score: number | null;
  critical_issue_count: number;
}

export interface ImprovementArea {
  dimension: string;
  average_score: number | null;
}

export interface RecentCall {
  call_id: string;
  upload_time: string;
  duration: number | null;
  overall_score: number | null;
  issue_count: number;
  processing_status: string;
}

export interface TranscriptSegment {
  speaker: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence: number | null;
}

export interface CallScoreDetail {
  rapport: number | null;
  needs_discovery: number | null;
  product_knowledge: number | null;
  objection_handling: number | null;
  compliance: number | null;
  trial_booking: number | null;
  closing: number | null;
  overall: number | null;
}

export interface IssueTagDetail {
  id: string | null;
  category: string;
  severity: string;
  timestamp: number | null;
  speaker: string | null;
  quote: string | null;
  reason: string | null;
  confidence: number | null;
}

export interface AISummaryDetail {
  executive_summary: string;
  customer_goal: string | null;
  objections: string | null;
  recommended_next_step: string | null;
  sentiment: string | null;
}

export interface CallMetadata {
  call_id: string;
  advisor_id: string;
  advisor_name: string;
  team_id: string;
  team_name: string;
  upload_time: string;
  processing_status: string;
  language: string | null;
  duration: number | null;
  source_type: string;
  call_type?: string;
  is_sales_call?: boolean;
  non_sales_reason?: string | null;
  classification_confidence?: number | null;
}

export interface OrganizationDashboardResponse {
  organization_id: string;
  organization_name: string;
  total_teams: number;
  total_advisors: number;
  total_calls: number;
  completed_calls: number;
  failed_calls: number;
  processing_calls: number;
  average_quality_score: number | null;
  average_dimension_scores: DimensionAverages;
  top_issue_tags: IssueTagCount[];
  team_performance: TeamPerformanceSummary[];
}

export interface TeamDashboardResponse {
  team_id: string;
  team_name: string;
  organization_id: string;
  organization_name: string;
  total_advisors: number;
  total_calls: number;
  completed_calls: number;
  failed_calls: number;
  processing_calls: number;
  average_quality_score: number | null;
  average_dimension_scores: DimensionAverages;
  top_issue_tags: IssueTagCount[];
  advisor_leaderboard: AdvisorPerformanceSummary[];
}

export interface AdvisorDashboardResponse {
  advisor_id: string;
  advisor_name: string;
  advisor_email: string;
  advisor_status: string;
  team_id: string;
  team_name: string;
  organization_id: string;
  organization_name: string;
  total_calls: number;
  completed_calls: number;
  failed_calls: number;
  processing_calls: number;
  average_quality_score: number | null;
  average_dimension_scores: DimensionAverages;
  top_issue_tags: IssueTagCount[];
  recent_calls: RecentCall[];
  improvement_areas: ImprovementArea[];
}

export interface CallReviewResponse {
  metadata: CallMetadata;
  score: CallScoreDetail | null;
  issue_tags: IssueTagDetail[];
  summary: AISummaryDetail | null;
  transcript_available: boolean;
  transcript: TranscriptSegment[];
}

export interface CallListItem {
  call_id: string;
  advisor_id: string;
  advisor_name: string;
  team_id: string;
  team_name: string;
  upload_time: string;
  processing_status: string;
  duration: number | null;
  overall_score: number | null;
  issue_count: number;
  call_type?: string;
  is_sales_call?: boolean;
  non_sales_reason?: string | null;
  classification_confidence?: number | null;
}

export interface PaginatedCallListResponse {
  items: CallListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface AdvisorListItem {
  advisor_id: string;
  advisor_name: string;
  advisor_email: string;
  advisor_status: string;
  team_id: string;
  team_name: string;
  organization_id: string;
  organization_name: string;
  completed_calls: number;
  average_score: number | null;
  critical_issue_count: number;
}

export interface PaginatedAdvisorListResponse {
  items: AdvisorListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}
