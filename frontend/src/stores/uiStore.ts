import { create } from "zustand";

export type View = "chat" | "documents" | "plugins" | "ableton";

interface UiState {
  activeView: View;
  isStreaming: boolean;
  isConnected: boolean;
  setActiveView: (view: View) => void;
  setStreaming: (val: boolean) => void;
  setConnected: (val: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeView: "chat",
  isStreaming: false,
  isConnected: false,
  setActiveView: (view) => set({ activeView: view }),
  setStreaming: (val) => set({ isStreaming: val }),
  setConnected: (val) => set({ isConnected: val }),
}));
