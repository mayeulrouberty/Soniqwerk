import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSSE } from "@/hooks/useSSE";
import { useChatStore } from "@/stores/chatStore";
import { useUiStore } from "@/stores/uiStore";

// Mock fetch with SSE response
function createSSEResponse(events: Array<{ event: string; data: string }>) {
  const text = events
    .map((e) => `event: ${e.event}\ndata: ${e.data}\n\n`)
    .join("");
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("useSSE", () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [],
      conversationId: null,
      currentStreamText: "",
    });
    useUiStore.setState({
      activeView: "chat",
      isStreaming: false,
      isConnected: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends a message and processes chunk + done events", async () => {
    const convId = "550e8400-e29b-41d4-a716-446655440000";
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      createSSEResponse([
        {
          event: "chunk",
          data: JSON.stringify({ text: "Hello ", conversation_id: convId }),
        },
        {
          event: "chunk",
          data: JSON.stringify({ text: "world", conversation_id: convId }),
        },
        {
          event: "sources",
          data: JSON.stringify({ sources: [] }),
        },
        {
          event: "done",
          data: JSON.stringify({ model_used: "gpt-4o", conversation_id: convId }),
        },
      ])
    );

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      result.current.sendMessage("test");
      // Let microtasks settle
      await new Promise((r) => setTimeout(r, 50));
    });

    const state = useChatStore.getState();
    expect(state.messages).toHaveLength(2); // user + assistant
    expect(state.messages[0].role).toBe("user");
    expect(state.messages[0].content).toBe("test");
    expect(state.messages[1].role).toBe("assistant");
    expect(state.messages[1].content).toBe("Hello world");
    expect(state.conversationId).toBe(convId);
    expect(useUiStore.getState().isStreaming).toBe(false);
  });

  it("handles error events", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      createSSEResponse([
        {
          event: "error",
          data: JSON.stringify({ code: "LLM_TIMEOUT", message: "timed out" }),
        },
      ])
    );

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      result.current.sendMessage("test");
      await new Promise((r) => setTimeout(r, 50));
    });

    const msgs = useChatStore.getState().messages;
    expect(msgs[1].content).toContain("LLM_TIMEOUT");
  });

  it("handles fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      result.current.sendMessage("test");
      await new Promise((r) => setTimeout(r, 50));
    });

    const msgs = useChatStore.getState().messages;
    expect(msgs[1].content).toContain("Network error");
    expect(useUiStore.getState().isStreaming).toBe(false);
  });
});
