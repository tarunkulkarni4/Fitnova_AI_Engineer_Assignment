export interface ScoreCorrectionInput {
  reviewer_name: string;
  dimension: 'rapport' | 'needs_discovery' | 'product_knowledge' | 'objection_handling' | 'compliance' | 'trial_booking' | 'closing';
  corrected_score: number;
  comments?: string | null;
}

export interface TagRejectInput {
  reviewer_name: string;
  comments?: string | null;
}

export interface TagCorrectInput {
  reviewer_name: string;
  category: string;
  timestamp?: number | null;
  quote?: string | null;
  reason?: string | null;
  comments?: string | null;
}

export interface TagAddInput {
  reviewer_name: string;
  category: string;
  timestamp?: number | null;
  quote?: string | null;
  reason?: string | null;
  comments?: string | null;
}

export interface SummaryCorrectionInput {
  reviewer_name: string;
  field: 'executive_summary' | 'customer_goal' | 'objections' | 'recommended_next_step' | 'sentiment';
  corrected_value: string;
  comments?: string | null;
}

export interface TranscriptCorrectionInput {
  reviewer_name: string;
  segment_index: number;
  corrected_speaker: string;
  corrected_text: string;
  comments?: string | null;
}

export interface FeedbackResponseItem {
  feedback_id: string;
  feedback_type: string;
  reviewer_name: string;
  original_value: any;
  corrected_value: any;
  comments: string | null;
  reviewed_at: string;
}

export interface ScoreDetail {
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

export interface SummaryDetail {
  executive_summary: string;
  customer_goal: string | null;
  objections: string | null;
  recommended_next_step: string | null;
  sentiment: string | null;
}

export interface TranscriptSegment {
  speaker: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence: number | null;
}

export interface FeedbackCallReviewResponse {
  call_id: string;
  original_score: ScoreDetail | null;
  effective_score: ScoreDetail | null;
  original_issue_tags: IssueTagDetail[];
  effective_issue_tags: IssueTagDetail[];
  original_summary: SummaryDetail | null;
  effective_summary: SummaryDetail | null;
  original_transcript: TranscriptSegment[];
  effective_transcript: TranscriptSegment[];
  feedback_history: FeedbackResponseItem[];
}

export interface ExportRecordItem {
  call_id: string;
  feedback_type: string;
  original_value: any;
  corrected_value: any;
  comments: string | null;
  reviewed_at: string;
}
