import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";
import type { Message, Source } from "@/lib/schemas";

interface ChatState {
  messages: Message[];
  conversationId: string | null;
  currentStreamText: string;

  addUserMessage: (content: string) => string;
  startAssistantMessage: () => string;
  appendChunk: (messageId: string, text: string) => void;
  finalizeAssistant: (messageId: string, sources: Source[], modelUsed: string) => void;
  setError: (messageId: string, error: string) => void;
  setConversationId: (id: string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  conversationId: null,
  currentStreamText: "",

  addUserMessage: (content) => {
    const id = uuidv4();
    const msg: Message = {
      id,
      role: "user",
      content,
      timestamp: Date.now(),
    };
    set((state) => ({ messages: [...state.messages, msg] }));
    return id;
  },

  startAssistantMessage: () => {
    const id = uuidv4();
    const msg: Message = {
      id,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    };
    set((state) => ({
      messages: [...state.messages, msg],
      currentStreamText: "",
    }));
    return id;
  },

  appendChunk: (messageId, text) => {
    set((state) => ({
      currentStreamText: state.currentStreamText + text,
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, content: m.content + text } : m
      ),
    }));
  },

  finalizeAssistant: (messageId, sources, modelUsed) => {
    set((state) => ({
      currentStreamText: "",
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, sources, modelUsed } : m
      ),
    }));
  },

  setError: (messageId, error) => {
    set((state) => ({
      currentStreamText: "",
      messages: state.messages.map((m) =>
        m.id === messageId
          ? { ...m, content: `Error: ${error}` }
          : m
      ),
    }));
  },

  setConversationId: (id) => set({ conversationId: id }),

  clearMessages: () => set({ messages: [], conversationId: null, currentStreamText: "" }),
}));
