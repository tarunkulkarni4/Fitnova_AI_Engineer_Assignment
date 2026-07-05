import { apiClient } from './client';
import {
  PipelineStartedResponse,
  PipelineStatusResponse,
} from '../types/pipeline';

/**
 * Start the pipeline for a call.
 * Returns HTTP 202 immediately; the pipeline runs in a backend BackgroundTask.
 * Poll `getPipelineStatus` for live progress.
 */
export async function startPipeline(callId: string): Promise<PipelineStartedResponse> {
  const response = await apiClient.post<PipelineStartedResponse>(`/pipeline/${callId}/run`);
  return response.data;
}

/**
 * Poll this endpoint every 2–3 s after calling `startPipeline`.
 * Returns per-stage status derived from DB state — safe to call frequently.
 */
export async function getPipelineStatus(callId: string): Promise<PipelineStatusResponse> {
  const response = await apiClient.get<PipelineStatusResponse>(`/pipeline/${callId}/status`);
  return response.data;
}

/**
 * Cancel an active pipeline execution for a call.
 */
export async function cancelPipeline(callId: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post<{ success: boolean; message: string }>(`/pipeline/${callId}/cancel`);
  return response.data;
}

// Backward compatibility for existing tests
export const runPipeline = startPipeline as (callId: string) => Promise<any>;
