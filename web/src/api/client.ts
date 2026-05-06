import axios from 'axios';
import type { ApiError } from '@/types/api';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.error) {
      const apiError: ApiError = error.response.data;
      console.error(`[${apiError.error.code}] ${apiError.error.message}`);
    }
    return Promise.reject(error);
  },
);

export default client;
