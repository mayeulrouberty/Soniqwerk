import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useUpload } from "@/hooks/useUpload";
import { useDocumentsStore } from "@/stores/documentsStore";

vi.mock("@/lib/api", () => ({
  uploadDocument: vi.fn(),
  pollIngestStatus: vi.fn(),
}));

import { uploadDocument, pollIngestStatus } from "@/lib/api";

describe("useUpload", () => {
  beforeEach(() => {
    useDocumentsStore.setState({ documents: [] });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("uploads a file and adds it to the store", async () => {
    const mockUpload = vi.mocked(uploadDocument);
    mockUpload.mockResolvedValueOnce({
      task_id: "task-1",
      document_id: "doc-1",
      status: "queued",
    });

    const mockPoll = vi.mocked(pollIngestStatus);
    mockPoll.mockResolvedValue({
      status: "ready",
      chunks_count: 10,
      error: null,
    });

    const { result } = renderHook(() => useUpload());
    const file = new File(["pdf content"], "test.pdf", { type: "application/pdf" });

    await act(async () => {
      await result.current.upload(file, "manuals");
    });

    const docs = useDocumentsStore.getState().documents;
    expect(docs).toHaveLength(1);
    expect(docs[0].filename).toBe("test.pdf");
    expect(docs[0].status).toBe("queued");

    // Advance timer for polling
    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve(); // flush microtasks
    });

    const updatedDocs = useDocumentsStore.getState().documents;
    expect(updatedDocs[0].status).toBe("ready");
    expect(updatedDocs[0].chunksCount).toBe(10);
  });

  it("handles upload failure", async () => {
    const mockUpload = vi.mocked(uploadDocument);
    mockUpload.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useUpload());
    const file = new File(["pdf content"], "test.pdf", { type: "application/pdf" });

    await act(async () => {
      await result.current.upload(file, "manuals");
    });

    const docs = useDocumentsStore.getState().documents;
    expect(docs).toHaveLength(1);
    expect(docs[0].status).toBe("error");
    expect(docs[0].error).toBe("Network error");
  });
});
