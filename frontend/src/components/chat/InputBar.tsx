import { useState, useRef, useCallback, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { RiSendPlaneFill, RiAttachmentLine } from "react-icons/ri";
import { useUiStore } from "@/stores/uiStore";

interface InputBarProps {
  onSend: (message: string) => void;
  onFileSelect?: (file: File) => void;
}

export function InputBar({ onSend, onFileSelect }: InputBarProps) {
  const [value, setValue] = useState("");
  const isStreaming = useUiStore((s) => s.isStreaming);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, isStreaming, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleFileClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file && onFileSelect) {
        onFileSelect(file);
      }
      // Reset input so same file can be selected again
      e.target.value = "";
    },
    [onFileSelect]
  );

  return (
    <div className="flex items-end gap-2 p-4 border-t border-border bg-surface">
      {/* File attach button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={handleFileClick}
        className="text-muted hover:text-text shrink-0"
        aria-label="Attach file"
      >
        <RiAttachmentLine size={20} />
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Text input */}
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about music production... (Ctrl+Enter to send)"
        className="flex-1 min-h-[44px] max-h-[160px] resize-none bg-bg border-border text-text placeholder:text-muted/50 focus-visible:ring-accent/50 text-sm"
        rows={1}
        disabled={isStreaming}
      />

      {/* Send button */}
      <Button
        onClick={handleSend}
        disabled={!value.trim() || isStreaming}
        className="bg-accent hover:bg-accent/80 text-white shrink-0"
        size="icon"
        aria-label="Send message"
      >
        <RiSendPlaneFill size={18} />
      </Button>
    </div>
  );
}
