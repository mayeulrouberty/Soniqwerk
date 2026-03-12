import { useUiStore } from "@/stores/uiStore";
import { useChatStore } from "@/stores/chatStore";
import { Badge } from "@/components/ui/badge";
import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

export function Header() {
  const isConnected = useUiStore((s) => s.isConnected);
  const setConnected = useUiStore((s) => s.setConnected);
  const isStreaming = useUiStore((s) => s.isStreaming);
  const [version, setVersion] = useState<string>("");

  // Poll health every 30 seconds
  useEffect(() => {
    let mounted = true;

    async function check() {
      try {
        const health = await checkHealth();
        if (mounted) {
          setConnected(true);
          setVersion(health.version);
        }
      } catch {
        if (mounted) setConnected(false);
      }
    }

    check();
    const interval = setInterval(check, 30_000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [setConnected]);

  // Find latest model used
  const messages = useChatStore((s) => s.messages);
  const lastModel = [...messages].reverse().find((m) => m.modelUsed)?.modelUsed;

  return (
    <header className="flex items-center justify-between px-6 h-14 bg-surface border-b border-border">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-2xl text-accent tracking-wide">SONIQWERK</h1>
        {version && (
          <span className="text-xs text-muted font-mono">v{version}</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Model badge */}
        {lastModel && (
          <Badge variant="outline" className="border-border text-muted font-mono text-xs">
            {lastModel}
          </Badge>
        )}

        {/* Streaming indicator */}
        {isStreaming && (
          <Badge className="bg-accent/20 text-accent border-accent/30 text-xs">
            streaming
          </Badge>
        )}

        {/* Connection status */}
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? "bg-green" : "bg-red-500"
            }`}
          />
          <span className="text-xs text-muted">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>
    </header>
  );
}
