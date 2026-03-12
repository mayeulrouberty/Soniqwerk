import { useDocumentsStore } from "@/stores/documentsStore";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { DropZone } from "./DropZone";
import type { DocumentItem } from "@/lib/schemas";

const STATUS_STYLES: Record<DocumentItem["status"], { bg: string; text: string }> = {
  queued: { bg: "bg-muted/20", text: "text-muted" },
  processing: { bg: "bg-accent/20", text: "text-accent" },
  ready: { bg: "bg-green/20", text: "text-green" },
  error: { bg: "bg-red-500/20", text: "text-red-400" },
};

function DocumentRow({ doc }: { doc: DocumentItem }) {
  const styles = STATUS_STYLES[doc.status];

  return (
    <div className="flex items-center justify-between p-3 bg-surface rounded-lg border border-border">
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="text-sm text-text truncate">{doc.filename}</span>
        <span className="text-xs text-muted font-mono">{doc.category}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {doc.chunksCount != null && (
          <span className="text-xs text-muted font-mono">{doc.chunksCount} chunks</span>
        )}
        <Badge
          className={cn("text-[10px] border-none", styles.bg, styles.text)}
        >
          {doc.status}
        </Badge>
      </div>
    </div>
  );
}

export function DocumentLibrary() {
  const documents = useDocumentsStore((s) => s.documents);

  return (
    <div className="flex flex-col gap-6 p-6 max-w-2xl mx-auto">
      <div>
        <h2 className="font-display text-3xl text-accent mb-1">Documents</h2>
        <p className="text-sm text-muted">
          Upload PDF manuals, books, and articles to enrich the AI knowledge base.
        </p>
      </div>

      {/* Upload zone */}
      <DropZone />

      {/* Document list */}
      <div className="flex flex-col gap-2">
        {documents.length === 0 && (
          <p className="text-sm text-muted text-center py-8">
            No documents ingested yet. Upload a PDF to get started.
          </p>
        )}
        {documents.map((doc) => (
          <DocumentRow key={doc.id} doc={doc} />
        ))}
      </div>
    </div>
  );
}
