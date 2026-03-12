import { describe, it, expect, beforeEach } from "vitest";
import { useDocumentsStore } from "@/stores/documentsStore";

describe("documentsStore", () => {
  beforeEach(() => {
    useDocumentsStore.setState({ documents: [] });
  });

  it("adds a document", () => {
    useDocumentsStore.getState().addDocument({
      id: "doc-1",
      filename: "test.pdf",
      category: "manuals",
      status: "queued",
      taskId: "task-1",
      addedAt: Date.now(),
    });
    expect(useDocumentsStore.getState().documents).toHaveLength(1);
  });

  it("updates document status", () => {
    useDocumentsStore.getState().addDocument({
      id: "doc-1",
      filename: "test.pdf",
      category: "manuals",
      status: "queued",
      taskId: "task-1",
      addedAt: Date.now(),
    });
    useDocumentsStore.getState().updateStatus("task-1", "ready", 42);
    const doc = useDocumentsStore.getState().documents[0];
    expect(doc.status).toBe("ready");
    expect(doc.chunksCount).toBe(42);
  });

  it("removes a document", () => {
    useDocumentsStore.getState().addDocument({
      id: "doc-1",
      filename: "test.pdf",
      category: "manuals",
      status: "ready",
      taskId: "task-1",
      addedAt: Date.now(),
    });
    useDocumentsStore.getState().removeDocument("doc-1");
    expect(useDocumentsStore.getState().documents).toHaveLength(0);
  });
});
