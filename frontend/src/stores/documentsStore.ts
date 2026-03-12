import { create } from "zustand";
import type { DocumentItem } from "@/lib/schemas";

interface DocumentsState {
  documents: DocumentItem[];
  addDocument: (doc: DocumentItem) => void;
  updateStatus: (
    taskId: string,
    status: DocumentItem["status"],
    chunksCount?: number,
    error?: string
  ) => void;
  removeDocument: (id: string) => void;
}

export const useDocumentsStore = create<DocumentsState>((set) => ({
  documents: [],

  addDocument: (doc) =>
    set((state) => ({ documents: [doc, ...state.documents] })),

  updateStatus: (taskId, status, chunksCount, error) =>
    set((state) => ({
      documents: state.documents.map((d) =>
        d.taskId === taskId ? { ...d, status, chunksCount, error } : d
      ),
    })),

  removeDocument: (id) =>
    set((state) => ({
      documents: state.documents.filter((d) => d.id !== id),
    })),
}));
