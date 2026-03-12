import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useUiStore } from "@/stores/uiStore";
import { useSSE } from "@/hooks/useSSE";
import { MessageBubble } from "./MessageBubble";
import { StreamingMessage } from "./StreamingMessage";
import { InputBar } from "./InputBar";

export function ChatWindow() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useUiStore((s) => s.isStreaming);
  const { sendMessage } = useSSE();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or streaming state changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages area — scrollable */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="flex flex-col gap-4 max-w-3xl mx-auto">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <h2 className="font-display text-5xl text-accent mb-3">SONIQWERK</h2>
              <p className="text-muted text-sm max-w-md">
                AI assistant for electronic music production. Ask about synthesis,
                mixing, sound design, plugins, or anything music-related.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {/* Streaming dots (shown alongside last message being streamed) */}
          <StreamingMessage />

          {/* Scroll anchor */}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input bar */}
      <InputBar onSend={sendMessage} />
    </div>
  );
}
