import { useCallback, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useUiStore } from "@/stores/uiStore";
import {
  ChunkEventSchema,
  SourcesEventSchema,
  DoneEventSchema,
  ErrorEventSchema,
} from "@/lib/schemas";
import { getChatUrl, getApiKey } from "@/lib/api";

interface UseSSEReturn {
  sendMessage: (message: string, modelOverride?: string) => void;
  abort: () => void;
}

export function useSSE(): UseSSEReturn {
  const abortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  const sendMessage = useCallback(
    (message: string, modelOverride?: string) => {
      const chatStore = useChatStore.getState();
      const uiStore = useUiStore.getState();

      // Add user message
      chatStore.addUserMessage(message);

      // Start assistant message placeholder
      const assistantId = chatStore.startAssistantMessage();
      uiStore.setStreaming(true);

      // Abort any existing request
      if (abortRef.current) {
        abortRef.current.abort();
      }
      const controller = new AbortController();
      abortRef.current = controller;
      const myRequestId = ++requestIdRef.current;

      const body = JSON.stringify({
        message,
        conversation_id: chatStore.conversationId ?? undefined,
        model_override: modelOverride,
      });

      fetch(getChatUrl(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": getApiKey(),
        },
        body,
        signal: controller.signal,
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const reader = response.body?.getReader();
          if (!reader) throw new Error("No response body");

          const decoder = new TextDecoder();
          let buffer = "";
          let eventType = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            // Keep the last potentially incomplete line in buffer
            buffer = lines.pop() ?? "";
            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith("data: ") && eventType) {
                const jsonStr = line.slice(6);
                try {
                  const payload = JSON.parse(jsonStr);
                  handleEvent(eventType, payload, assistantId);
                } catch {
                  // Malformed JSON line — skip
                }
                eventType = "";
              }
            }
          }
        })
        .catch((err: unknown) => {
          if (err instanceof Error && err.name === "AbortError") return;
          const msg = err instanceof Error ? err.message : "Unknown error";
          useChatStore.getState().setError(assistantId, msg);
        })
        .finally(() => {
          // Only clear streaming if this is still the active request.
          // If requestIdRef has advanced, a newer sendMessage() superseded us.
          if (requestIdRef.current === myRequestId) {
            useUiStore.getState().setStreaming(false);
          }
        });
    },
    []
  );

  const abort = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    useUiStore.getState().setStreaming(false);
  }, []);

  return { sendMessage, abort };
}

function handleEvent(
  eventType: string,
  payload: unknown,
  assistantId: string
): void {
  const chatStore = useChatStore.getState();

  switch (eventType) {
    case "chunk": {
      const parsed = ChunkEventSchema.safeParse(payload);
      if (parsed.success) {
        chatStore.appendChunk(assistantId, parsed.data.text);
        // Set conversation ID from first chunk
        if (!chatStore.conversationId) {
          chatStore.setConversationId(parsed.data.conversation_id);
        }
      }
      break;
    }
    case "sources": {
      const parsed = SourcesEventSchema.safeParse(payload);
      if (parsed.success) {
        useChatStore.setState((state) => ({
          messages: state.messages.map((m) =>
            m.id === assistantId ? { ...m, sources: parsed.data.sources } : m
          ),
        }));
      }
      break;
    }
    case "done": {
      const parsed = DoneEventSchema.safeParse(payload);
      if (parsed.success) {
        const msg = useChatStore.getState().messages.find((m) => m.id === assistantId);
        chatStore.finalizeAssistant(
          assistantId,
          msg?.sources ?? [],
          parsed.data.model_used
        );
        chatStore.setConversationId(parsed.data.conversation_id);
      }
      break;
    }
    case "error": {
      const parsed = ErrorEventSchema.safeParse(payload);
      if (parsed.success) {
        chatStore.setError(assistantId, `${parsed.data.code}: ${parsed.data.message}`);
      }
      break;
    }
  }
}
