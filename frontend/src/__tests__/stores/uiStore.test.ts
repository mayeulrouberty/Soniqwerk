import { describe, it, expect, beforeEach } from "vitest";
import { useUiStore } from "@/stores/uiStore";

describe("uiStore", () => {
  beforeEach(() => {
    useUiStore.setState({
      activeView: "chat",
      isStreaming: false,
      isConnected: false,
    });
  });

  it("changes active view", () => {
    useUiStore.getState().setActiveView("documents");
    expect(useUiStore.getState().activeView).toBe("documents");
  });

  it("toggles streaming state", () => {
    useUiStore.getState().setStreaming(true);
    expect(useUiStore.getState().isStreaming).toBe(true);
    useUiStore.getState().setStreaming(false);
    expect(useUiStore.getState().isStreaming).toBe(false);
  });

  it("sets connected state", () => {
    useUiStore.getState().setConnected(true);
    expect(useUiStore.getState().isConnected).toBe(true);
  });
});
