import axios from "axios";
import type { IngestStatus, Health } from "./schemas";
import { IngestStatusSchema, HealthSchema } from "./schemas";

const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const apiKey = import.meta.env.VITE_API_KEY ?? "";

export const api = axios.create({
  baseURL,
  timeout: 30_000,
});

// Attach X-API-Key to every request
api.interceptors.request.use((config) => {
  config.headers["X-API-Key"] = apiKey;
  return config;
});

// ── Health ──────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<Health> {
  const { data } = await api.get("/health");
  return HealthSchema.parse(data);
}

// ── Documents ───────────────────────────────────────────────────────────

export async function uploadDocument(
  file: File,
  category: string
): Promise<{ task_id: string; document_id: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("category", category);
  const { data } = await api.post("/v1/documents/ingest", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60_000,
  });
  return data;
}

export async function pollIngestStatus(taskId: string): Promise<IngestStatus> {
  const { data } = await api.get(`/v1/documents/ingest/${taskId}/status`);
  return IngestStatusSchema.parse(data);
}

// ── Chat SSE URL builder ────────────────────────────────────────────────

export function getChatUrl(): string {
  return `${baseURL}/v1/chat`;
}

export function getApiKey(): string {
  return apiKey;
}
