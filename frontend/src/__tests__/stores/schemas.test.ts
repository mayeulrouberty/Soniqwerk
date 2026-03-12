import { describe, it, expect } from "vitest";
import {
  ChatRequestSchema,
  ChunkEventSchema,
  SourcesEventSchema,
  DoneEventSchema,
  ErrorEventSchema,
  IngestResponseSchema,
  IngestStatusSchema,
  HealthSchema,
} from "@/lib/schemas";

describe("Zod schemas", () => {
  it("validates ChatRequest", () => {
    const valid = { message: "hello" };
    expect(ChatRequestSchema.parse(valid)).toEqual(valid);
  });

  it("rejects empty ChatRequest message", () => {
    expect(() => ChatRequestSchema.parse({ message: "" })).toThrow();
  });

  it("validates ChunkEvent", () => {
    const data = { text: "hi", conversation_id: "550e8400-e29b-41d4-a716-446655440000" };
    expect(ChunkEventSchema.parse(data)).toEqual(data);
  });

  it("validates SourcesEvent", () => {
    const data = {
      sources: [{ title: "Manual", source: "synth.pdf", score: 0.95 }],
    };
    expect(SourcesEventSchema.parse(data)).toEqual(data);
  });

  it("validates DoneEvent", () => {
    const data = {
      model_used: "gpt-4o",
      conversation_id: "550e8400-e29b-41d4-a716-446655440000",
    };
    expect(DoneEventSchema.parse(data)).toEqual(data);
  });

  it("validates ErrorEvent", () => {
    const data = { code: "LLM_TIMEOUT", message: "timed out" };
    expect(ErrorEventSchema.parse(data)).toEqual(data);
  });

  it("validates IngestResponse", () => {
    const data = {
      task_id: "abc-123",
      document_id: "550e8400-e29b-41d4-a716-446655440000",
      status: "queued",
    };
    expect(IngestResponseSchema.parse(data)).toEqual(data);
  });

  it("validates IngestStatus", () => {
    const data = { status: "ready", chunks_count: 42, error: null };
    expect(IngestStatusSchema.parse(data)).toEqual(data);
  });

  it("validates Health", () => {
    const data = { status: "ok", version: "2.0.0" };
    expect(HealthSchema.parse(data)).toEqual(data);
  });
});
