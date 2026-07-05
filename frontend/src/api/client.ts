import axios, { AxiosError } from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ApiError {
  message: string;
  status?: number;
  detail?: any;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const apiError: ApiError = {
      message: 'An unexpected error occurred.',
    };

    if (error.response) {
      apiError.status = error.response.status;
      const data = error.response.data as any;
      if (data && typeof data === 'object') {
        apiError.message = data.message || data.detail || error.message;
        apiError.detail = data.detail || data.errors || null;
      } else {
        apiError.message = error.message;
      }
    } else if (error.request) {
      apiError.message = 'No response received from server. Please check your connection.';
    } else {
      apiError.message = error.message;
    }

    return Promise.reject(apiError);
  }
);
