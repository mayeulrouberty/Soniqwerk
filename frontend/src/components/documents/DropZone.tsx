import { useState, useCallback, useRef, type DragEvent } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { RiUploadCloud2Line } from "react-icons/ri";
import { useUpload } from "@/hooks/useUpload";
import type { DocumentCategory } from "@/lib/schemas";
import { cn } from "@/lib/utils";

const CATEGORIES: { value: DocumentCategory; label: string }[] = [
  { value: "manuals", label: "Manuals" },
  { value: "plugins", label: "Plugins" },
  { value: "books", label: "Books" },
  { value: "articles", label: "Articles" },
];

export function DropZone() {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [category, setCategory] = useState<DocumentCategory>("manuals");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { upload } = useUpload();

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith(".pdf")) {
      setSelectedFile(file);
    }
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) setSelectedFile(file);
      e.target.value = "";
    },
    []
  );

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;
    setUploading(true);
    try {
      await upload(selectedFile, category);
      setSelectedFile(null);
    } finally {
      setUploading(false);
    }
  }, [selectedFile, category, upload]);

  return (
    <div className="flex flex-col gap-4">
      {/* Drop area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "flex flex-col items-center justify-center gap-3 p-8 border-2 border-dashed rounded-xl cursor-pointer transition-colors",
          isDragging
            ? "border-accent bg-accent/5"
            : "border-border hover:border-muted"
        )}
      >
        <RiUploadCloud2Line size={40} className="text-muted" />
        <div className="text-center">
          <p className="text-sm text-text">
            Drop a PDF here or <span className="text-accent underline">browse</span>
          </p>
          <p className="text-xs text-muted mt-1">Max 50 MB</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileSelect}
        />
      </div>

      {/* Selected file info + category + upload button */}
      {selectedFile && (
        <div className="flex flex-col gap-3 p-4 bg-surface rounded-lg border border-border">
          <div className="flex items-center justify-between">
            <span className="text-sm text-text truncate max-w-[200px]">
              {selectedFile.name}
            </span>
            <span className="text-xs text-muted font-mono">
              {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
            </span>
          </div>

          {/* Category select */}
          <div className="flex gap-2 flex-wrap">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setCategory(cat.value)}
                className={cn(
                  "px-3 py-1 rounded-full text-xs transition-colors",
                  category === cat.value
                    ? "bg-accent text-white"
                    : "bg-border text-muted hover:text-text"
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Upload button */}
          <Button
            onClick={handleUpload}
            disabled={uploading}
            className="bg-accent hover:bg-accent/80 text-white"
          >
            {uploading ? "Uploading..." : "Upload"}
          </Button>

          {uploading && <Progress value={null} className="h-1" />}
        </div>
      )}
    </div>
  );
}
