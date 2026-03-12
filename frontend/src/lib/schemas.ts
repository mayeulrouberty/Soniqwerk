import { z } from "zod";

// ── Chat ────────────────────────────────────────────────────────────────

export const ChatRequestSchema = z.object({
  message: z.string().min(1, "Message cannot be empty"),
  conversation_id: z.string().uuid().optional(),
  model_override: z.string().optional(),
});
export type ChatRequest = z.infer<typeof ChatRequestSchema>;

export const ChunkEventSchema = z.object({
  text: z.string(),
  conversation_id: z.string().uuid(),
});
export type ChunkEvent = z.infer<typeof ChunkEventSchema>;

export const SourceSchema = z.object({
  title: z.string(),
  source: z.string(),
  score: z.number(),
});
export type Source = z.infer<typeof SourceSchema>;

export const SourcesEventSchema = z.object({
  sources: z.array(SourceSchema),
});
export type SourcesEvent = z.infer<typeof SourcesEventSchema>;

export const DoneEventSchema = z.object({
  model_used: z.string(),
  conversation_id: z.string().uuid(),
});
export type DoneEvent = z.infer<typeof DoneEventSchema>;

export const ErrorEventSchema = z.object({
  code: z.string(),
  message: z.string(),
});
export type ErrorEvent = z.infer<typeof ErrorEventSchema>;

// ── Documents ───────────────────────────────────────────────────────────

export const DocumentCategorySchema = z.enum([
  "manuals",
  "plugins",
  "books",
  "articles",
]);
export type DocumentCategory = z.infer<typeof DocumentCategorySchema>;

export const IngestResponseSchema = z.object({
  task_id: z.string(),
  document_id: z.string().uuid(),
  status: z.string(),
});
export type IngestResponse = z.infer<typeof IngestResponseSchema>;

export const IngestStatusSchema = z.object({
  status: z.enum(["queued", "processing", "ready", "error"]),
  chunks_count: z.number().nullable(),
  error: z.string().nullable(),
});
export type IngestStatus = z.infer<typeof IngestStatusSchema>;

// ── Health ──────────────────────────────────────────────────────────────

export const HealthSchema = z.object({
  status: z.string(),
  version: z.string(),
});
export type Health = z.infer<typeof HealthSchema>;

// ── App types (not API) ─────────────────────────────────────────────────

export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  sources?: Source[];
  modelUsed?: string;
  timestamp: number;
}

export interface DocumentItem {
  id: string;
  filename: string;
  category: DocumentCategory;
  status: "queued" | "processing" | "ready" | "error";
  chunksCount?: number;
  taskId: string;
  error?: string;
  addedAt: number;
}
