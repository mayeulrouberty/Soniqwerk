import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/schemas";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-accent/15 text-text border border-accent/20"
            : "bg-surface text-text border border-border"
        )}
      >
        {/* Message content */}
        <p className="whitespace-pre-wrap text-sm leading-relaxed break-words">
          {message.content}
        </p>

        {/* Sources chips */}
        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-2 border-t border-border/50">
            {message.sources.map((source, idx) => (
              <Badge
                key={idx}
                variant="outline"
                className="text-[10px] border-green/30 text-green/80 font-mono"
              >
                {source.title} ({(source.score * 100).toFixed(0)}%)
              </Badge>
            ))}
          </div>
        )}

        {/* Model used tag */}
        {message.modelUsed && (
          <div className="mt-2">
            <span className="text-[10px] text-muted font-mono">
              {message.modelUsed}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
