import client from './client';

// Inference API - 本地推理
export const inferenceHealth = () =>
  client.get('/v1/inference/health').then((r) => r.data);

export const getModels = () =>
  client.get('/v1/inference/models').then((r) => r.data);

export const getModelDetail = (name: string) =>
  client.get(`/v1/inference/models/${name}`).then((r) => r.data);

export const generateText = (data: { prompt: string; model?: string }) =>
  client.post('/v1/inference/generate', data).then((r) => r.data);

export const chatCompletion = (data: { messages: Array<{ role: string; content: string }>; model?: string }) =>
  client.post('/v1/inference/chat', data).then((r) => r.data);

export const openaiCompatibleChat = (data: { messages: Array<{ role: string; content: string }>; model?: string }) =>
  client.post('/v1/inference/v1/chat/completions', data).then((r) => r.data);
