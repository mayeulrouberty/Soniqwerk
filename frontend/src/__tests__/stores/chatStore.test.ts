import { describe, it, expect, beforeEach } from "vitest";
import { useChatStore } from "@/stores/chatStore";

describe("chatStore", () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [],
      conversationId: null,
      currentStreamText: "",
    });
  });

  it("adds a user message", () => {
    const id = useChatStore.getState().addUserMessage("hello");
    const msgs = useChatStore.getState().messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0].role).toBe("user");
    expect(msgs[0].content).toBe("hello");
    expect(msgs[0].id).toBe(id);
  });

  it("starts an assistant message with empty content", () => {
    const id = useChatStore.getState().startAssistantMessage();
    const msgs = useChatStore.getState().messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0].role).toBe("assistant");
    expect(msgs[0].content).toBe("");
    expect(msgs[0].id).toBe(id);
  });

  it("appends chunks to an assistant message", () => {
    const id = useChatStore.getState().startAssistantMessage();
    useChatStore.getState().appendChunk(id, "Hello ");
    useChatStore.getState().appendChunk(id, "world");
    const msg = useChatStore.getState().messages[0];
    expect(msg.content).toBe("Hello world");
    expect(useChatStore.getState().currentStreamText).toBe("Hello world");
  });

  it("finalizes with sources and model", () => {
    const id = useChatStore.getState().startAssistantMessage();
    useChatStore.getState().appendChunk(id, "response");
    useChatStore.getState().finalizeAssistant(
      id,
      [{ title: "Manual", source: "test.pdf", score: 0.9 }],
      "gpt-4o"
    );
    const msg = useChatStore.getState().messages[0];
    expect(msg.sources).toHaveLength(1);
    expect(msg.modelUsed).toBe("gpt-4o");
    expect(useChatStore.getState().currentStreamText).toBe("");
  });

  it("sets error on a message", () => {
    const id = useChatStore.getState().startAssistantMessage();
    useChatStore.getState().setError(id, "timeout");
    expect(useChatStore.getState().messages[0].content).toBe("Error: timeout");
  });

  it("clears all messages", () => {
    useChatStore.getState().addUserMessage("hi");
    useChatStore.getState().clearMessages();
    expect(useChatStore.getState().messages).toHaveLength(0);
    expect(useChatStore.getState().conversationId).toBeNull();
  });
});
