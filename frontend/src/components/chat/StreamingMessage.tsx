import { useUiStore } from "@/stores/uiStore";

export function StreamingMessage() {
  const isStreaming = useUiStore((s) => s.isStreaming);

  if (!isStreaming) return null;

  return (
    <div className="flex justify-start w-full">
      <div className="bg-surface border border-border rounded-2xl px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="streaming-dot w-2 h-2 rounded-full bg-accent inline-block" />
          <span className="streaming-dot w-2 h-2 rounded-full bg-accent inline-block" />
          <span className="streaming-dot w-2 h-2 rounded-full bg-accent inline-block" />
        </div>
      </div>
    </div>
  );
}
