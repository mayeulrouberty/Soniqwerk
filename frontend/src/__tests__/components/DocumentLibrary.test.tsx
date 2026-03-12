import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { DocumentLibrary } from "@/components/documents/DocumentLibrary";
import { useDocumentsStore } from "@/stores/documentsStore";

// Mock the upload hook to avoid API calls in tests
vi.mock("@/hooks/useUpload", () => ({
  useUpload: () => ({
    upload: vi.fn(),
    isUploading: false,
  }),
}));

describe("DocumentLibrary", () => {
  beforeEach(() => {
    useDocumentsStore.setState({ documents: [] });
  });

  it("renders empty state", () => {
    render(<DocumentLibrary />);
    expect(screen.getByText(/No documents ingested/)).toBeInTheDocument();
  });

  it("renders document list with status badges", () => {
    useDocumentsStore.setState({
      documents: [
        {
          id: "doc-1",
          filename: "Serum Manual.pdf",
          category: "manuals",
          status: "ready",
          chunksCount: 42,
          taskId: "task-1",
          addedAt: Date.now(),
        },
        {
          id: "doc-2",
          filename: "Synthesis Guide.pdf",
          category: "books",
          status: "processing",
          taskId: "task-2",
          addedAt: Date.now(),
        },
      ],
    });

    render(<DocumentLibrary />);
    expect(screen.getByText("Serum Manual.pdf")).toBeInTheDocument();
    expect(screen.getByText("Synthesis Guide.pdf")).toBeInTheDocument();
    expect(screen.getByText("42 chunks")).toBeInTheDocument();
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(screen.getByText("processing")).toBeInTheDocument();
  });

  it("shows upload drop zone", () => {
    render(<DocumentLibrary />);
    expect(screen.getByText(/Drop a PDF here/)).toBeInTheDocument();
  });
});
