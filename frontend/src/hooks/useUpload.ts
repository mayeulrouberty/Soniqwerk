import { useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { uploadDocument, pollIngestStatus } from "@/lib/api";
import { useDocumentsStore } from "@/stores/documentsStore";
import type { DocumentCategory } from "@/lib/schemas";

interface UseUploadReturn {
  upload: (file: File, category: DocumentCategory) => Promise<void>;
  isUploading: boolean;
}

export function useUpload(): UseUploadReturn {
  const isUploadingRef = useRef(false);

  const upload = useCallback(async (file: File, category: DocumentCategory) => {
    const store = useDocumentsStore.getState();
    const docId = uuidv4();

    isUploadingRef.current = true;

    try {
      // Call upload API
      const response = await uploadDocument(file, category);

      // Add to store
      store.addDocument({
        id: response.document_id,
        filename: file.name,
        category,
        status: "queued",
        taskId: response.task_id,
        addedAt: Date.now(),
      });

      // Start polling
      pollUntilDone(response.task_id);
    } catch (err) {
      // Add as errored document
      store.addDocument({
        id: docId,
        filename: file.name,
        category,
        status: "error",
        taskId: "",
        error: err instanceof Error ? err.message : "Upload failed",
        addedAt: Date.now(),
      });
    } finally {
      isUploadingRef.current = false;
    }
  }, []);

  return {
    upload,
    get isUploading() {
      return isUploadingRef.current;
    },
  };
}

function pollUntilDone(taskId: string): void {
  const interval = setInterval(async () => {
    try {
      const status = await pollIngestStatus(taskId);
      const store = useDocumentsStore.getState();

      if (status.status === "ready") {
        store.updateStatus(taskId, "ready", status.chunks_count ?? undefined);
        clearInterval(interval);
      } else if (status.status === "error") {
        store.updateStatus(taskId, "error", undefined, status.error ?? "Ingestion failed");
        clearInterval(interval);
      } else {
        store.updateStatus(taskId, status.status as "queued" | "processing");
      }
    } catch {
      // On poll error, just keep trying (server might be temporarily unavailable)
    }
  }, 2000);

  // Safety: stop polling after 5 minutes
  setTimeout(() => clearInterval(interval), 5 * 60 * 1000);
}
