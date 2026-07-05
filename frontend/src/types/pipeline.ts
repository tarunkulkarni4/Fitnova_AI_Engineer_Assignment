// Existing response shape (kept for any legacy references)
export interface PipelineResponse {
  success: boolean;
  message: string;
  call_id: string;
  stages_completed: string[];
  resumed_from: string | null;
  overall_score: number | null;
  issue_tags_count: number | null;
  processing_status: string;
}

// --- Async pipeline types ---

/** HTTP 202 response from POST /pipeline/{call_id}/run */
export interface PipelineStartedResponse {
  call_id: string;
  /** 'accepted' | 'already_processing' */
  pipeline_status: string;
  message: string;
}

/** Per-stage status returned by the polling endpoint */
export interface PipelineStageStatus {
  stage: string;
  status: 'Waiting' | 'Processing' | 'Completed' | 'Failed' | 'Cancelled';
  error: string | null;
}

/** Full response from GET /pipeline/{call_id}/status */
export interface PipelineStatusResponse {
  call_id: string;
  /** 'pending' | 'processing' | 'completed' | 'failed' */
  pipeline_status: string;
  current_stage: string | null;
  stages: PipelineStageStatus[];
  overall_score: number | null;
  issue_tags_count: number | null;
  error_message: string | null;
}
