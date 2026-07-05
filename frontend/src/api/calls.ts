import { apiClient } from './client';

export interface UploadResponse {
  success: boolean;
  message: string;
  call_id: string;
  processing_status: string;
}

export async function uploadCall(
  audioFile: File,
  advisorId: string,
  sourceType: string
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('audio', audioFile);
  formData.append('advisor_id', advisorId);
  formData.append('source_type', sourceType);

  const response = await apiClient.post<UploadResponse>('/calls/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

export async function simulateTelephonyCall(
  audioFile: File,
  advisorId: string,
  externalCallId: string,
  vendor: string
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('audio', audioFile);
  formData.append('advisor_id', advisorId);
  formData.append('external_call_id', externalCallId);
  formData.append('source', vendor);

  try {
    const response = await apiClient.post<UploadResponse>('/ingestion/telephony', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 409) {
      throw new Error('Duplicate blocked — this external call was already ingested.');
    }
    throw error;
  }
}
