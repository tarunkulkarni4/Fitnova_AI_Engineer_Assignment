import { apiClient } from './client';
import {
  ScoreCorrectionInput,
  TagRejectInput,
  TagCorrectInput,
  TagAddInput,
  SummaryCorrectionInput,
  TranscriptCorrectionInput,
  FeedbackResponseItem,
  FeedbackCallReviewResponse,
  ExportRecordItem,
} from '../types/feedback';

export async function correctScore(callId: string, input: ScoreCorrectionInput): Promise<FeedbackResponseItem> {
  const response = await apiClient.post<FeedbackResponseItem>(`/feedback/${callId}/score`, input);
  return response.data;
}

export async function rejectTag(callId: string, tagId: string, input: TagRejectInput): Promise<FeedbackResponseItem> {
  const response = await apiClient.post<FeedbackResponseItem>(`/feedback/${callId}/tags/${tagId}/reject`, input);
  return response.data;
}

export async function correctTag(callId: string, tagId: string, input: TagCorrectInput): Promise<FeedbackResponseItem> {
  const response = await apiClient.post<FeedbackResponseItem>(`/feedback/${callId}/tags/${tagId}/correct`, input);
  return response.data;
}

export async function addTag(callId: string, input: TagAddInput): Promise<FeedbackResponseItem> {
  const response = await apiClient.post<FeedbackResponseItem>(`/feedback/${callId}/tags/add`, input);
  return response.data;
}

export async function correctSummary(callId: string, input: SummaryCorrectionInput): Promise<FeedbackResponseItem> {
  const response = await apiClient.post<FeedbackResponseItem>(`/feedback/${callId}/summary`, input);
  return response.data;
}

export async function correctTranscript(callId: string, input: TranscriptCorrectionInput): Promise<FeedbackResponseItem> {
  const response = await apiClient.post<FeedbackResponseItem>(`/feedback/${callId}/transcript`, input);
  return response.data;
}

export async function getFeedbackReviewed(callId: string): Promise<FeedbackCallReviewResponse> {
  const response = await apiClient.get<FeedbackCallReviewResponse>(`/feedback/${callId}/reviewed`);
  return response.data;
}

export async function getFeedbackHistory(callId: string): Promise<FeedbackResponseItem[]> {
  const response = await apiClient.get<FeedbackResponseItem[]>(`/feedback/${callId}`);
  return response.data;
}

export async function exportFeedbackDataset(filters?: {
  feedback_type?: string;
  team_id?: string;
  start_date?: string;
  end_date?: string;
}): Promise<ExportRecordItem[]> {
  const response = await apiClient.get<ExportRecordItem[]>('/feedback/dataset/export', {
    params: {
      feedback_type: filters?.feedback_type,
      team_id: filters?.team_id || undefined,
      start_date: filters?.start_date,
      end_date: filters?.end_date,
    },
  });
  return response.data;
}
