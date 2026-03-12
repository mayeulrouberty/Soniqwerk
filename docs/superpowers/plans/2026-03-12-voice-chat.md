# Voice Input for Chat — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a microphone toggle button to the chat InputBar so users can dictate messages using the Web Speech API, with fr/en language switching.

**Architecture:** New `useVoice` hook wraps the Web Speech API and reads `voiceLang` from `uiStore`. `InputBar` renders a mic toggle button that inserts the transcript into the textarea. `Header` renders a FR/EN toggle that writes to `uiStore`.

**Tech Stack:** React 18, TypeScript, Zustand, Web Speech API (native browser, no npm package), lucide-react (already installed)

---

## Chunk 1: useVoice hook + uiStore

### Task 1: Add `voiceLang` to uiStore

**Files:**
- Modify: `frontend/src/stores/uiStore.ts`

Current file at `frontend/src/stores/uiStore.ts`:
```ts
import { create } from "zustand";

export type View = "chat" | "documents" | "plugins" | "ableton";

interface UiState {
  activeView: View;
  isStreaming: boolean;
  isConnected: boolean;
  setActiveView: (view: View) => void;
  setStreaming: (val: boolean) => void;
  setConnected: (val: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeView: "chat",
  isStreaming: false,
  isConnected: false,
  setActiveView: (view) => set({ activeView: view }),
  setStreaming: (val) => set({ isStreaming: val }),
  setConnected: (val) => set({ isConnected: val }),
}));
```

- [ ] **Step 1: Write the failing test**

Create `frontend/src/stores/__tests__/uiStore.test.ts`:

```ts
import { useUiStore } from "../uiStore";

beforeEach(() => {
  useUiStore.setState({
    voiceLang: "fr-FR",
    activeView: "chat",
    isStreaming: false,
    isConnected: false,
  });
});

test("default voiceLang is fr-FR", () => {
  expect(useUiStore.getState().voiceLang).toBe("fr-FR");
});

test("setVoiceLang updates to en-US", () => {
  useUiStore.getState().setVoiceLang("en-US");
  expect(useUiStore.getState().voiceLang).toBe("en-US");
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx vitest run src/stores/__tests__/uiStore.test.ts
```

Expected: FAIL — `voiceLang` property not found

- [ ] **Step 3: Add voiceLang to uiStore**

Replace `frontend/src/stores/uiStore.ts` with:

```ts
import { create } from "zustand";

export type View = "chat" | "documents" | "plugins" | "ableton";
export type VoiceLang = "fr-FR" | "en-US";

interface UiState {
  activeView: View;
  isStreaming: boolean;
  isConnected: boolean;
  voiceLang: VoiceLang;
  setActiveView: (view: View) => void;
  setStreaming: (val: boolean) => void;
  setConnected: (val: boolean) => void;
  setVoiceLang: (lang: VoiceLang) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeView: "chat",
  isStreaming: false,
  isConnected: false,
  voiceLang: "fr-FR",
  setActiveView: (view) => set({ activeView: view }),
  setStreaming: (val) => set({ isStreaming: val }),
  setConnected: (val) => set({ isConnected: val }),
  setVoiceLang: (lang) => set({ voiceLang: lang }),
}));
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx vitest run src/stores/__tests__/uiStore.test.ts
```

Expected: PASS — 2/2

- [ ] **Step 5: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
git add src/stores/uiStore.ts src/stores/__tests__/uiStore.test.ts
git commit -m "feat(store): add voiceLang to uiStore"
```

---

### Task 2: Create `useVoice` hook

**Files:**
- Create: `frontend/src/hooks/useVoice.ts`
- Test: `frontend/src/hooks/__tests__/useVoice.test.ts`

**Note on testing:** Web Speech API is not available in jsdom (Vitest's test environment). Tests must mock `window.SpeechRecognition`. Use `vi.stubGlobal` to inject a mock constructor.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/hooks/__tests__/useVoice.test.ts`:

```ts
import { renderHook, act } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { useUiStore } from "@/stores/uiStore";

// Minimal SpeechRecognition mock
class MockSpeechRecognition {
  lang = "";
  continuous = false;
  interimResults = false;
  onresult: ((e: { results: SpeechRecognitionResultList }) => void) | null = null;
  onerror: (() => void) | null = null;
  onend: (() => void) | null = null;
  start = vi.fn();
  stop = vi.fn();
}

beforeEach(() => {
  vi.stubGlobal("SpeechRecognition", MockSpeechRecognition);
  vi.stubGlobal("webkitSpeechRecognition", undefined);
  useUiStore.setState({ voiceLang: "fr-FR" });
});

test("isSupported is true when SpeechRecognition exists", async () => {
  const { useVoice } = await import("../useVoice");
  const { result } = renderHook(() => useVoice());
  expect(result.current.isSupported).toBe(true);
});

test("isSupported is false when API is missing", async () => {
  vi.stubGlobal("SpeechRecognition", undefined);
  vi.stubGlobal("webkitSpeechRecognition", undefined);
  const { useVoice } = await import("../useVoice");
  const { result } = renderHook(() => useVoice());
  expect(result.current.isSupported).toBe(false);
});

test("start sets isListening to true", async () => {
  const { useVoice } = await import("../useVoice");
  const { result } = renderHook(() => useVoice());
  act(() => { result.current.start(); });
  expect(result.current.isListening).toBe(true);
});

test("stop sets isListening to false", async () => {
  const { useVoice } = await import("../useVoice");
  const { result } = renderHook(() => useVoice());
  act(() => { result.current.start(); });
  act(() => { result.current.stop(); });
  expect(result.current.isListening).toBe(false);
});
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx vitest run src/hooks/__tests__/useVoice.test.ts
```

Expected: FAIL — module not found

- [ ] **Step 3: Implement `useVoice.ts`**

Create `frontend/src/hooks/useVoice.ts`:

```ts
import { useCallback, useRef, useState } from "react";
import { useUiStore } from "@/stores/uiStore";

type SpeechRecognitionAPI = typeof window.SpeechRecognition;

function getSpeechRecognition(): SpeechRecognitionAPI | null {
  if (typeof window === "undefined") return null;
  return (window.SpeechRecognition ?? window.webkitSpeechRecognition) ?? null;
}

export interface UseVoiceReturn {
  isSupported: boolean;
  isListening: boolean;
  transcript: string;
  start: () => void;
  stop: () => void;
  resetTranscript: () => void;
}

export function useVoice(): UseVoiceReturn {
  const voiceLang = useUiStore((s) => s.voiceLang);
  const SpeechRecognitionCtor = getSpeechRecognition();
  const isSupported = SpeechRecognitionCtor !== null;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef<InstanceType<SpeechRecognitionAPI> | null>(null);

  const start = useCallback(() => {
    if (!SpeechRecognitionCtor || isListening) return;

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = voiceLang;
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      const results = Array.from(event.results);
      const final = results
        .filter((r) => r.isFinal)
        .map((r) => r[0].transcript)
        .join(" ");
      if (final) setTranscript(final);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [SpeechRecognitionCtor, isListening, voiceLang]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const resetTranscript = useCallback(() => {
    setTranscript("");
  }, []);

  return { isSupported, isListening, transcript, start, stop, resetTranscript };
}
```

Also add the browser type augmentation at the top if TypeScript complains about `window.webkitSpeechRecognition`. Add to `frontend/src/vite-env.d.ts` or inline in the hook:

```ts
// At the top of useVoice.ts, before imports if needed:
declare global {
  interface Window {
    webkitSpeechRecognition?: typeof SpeechRecognition;
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx vitest run src/hooks/__tests__/useVoice.test.ts
```

Expected: PASS — 4/4

- [ ] **Step 5: Commit**

```bash
git add src/hooks/useVoice.ts src/hooks/__tests__/useVoice.test.ts
git commit -m "feat(hooks): add useVoice hook wrapping Web Speech API"
```

---

## Chunk 2: UI integration

### Task 3: Add mic button to InputBar

**Files:**
- Modify: `frontend/src/components/chat/InputBar.tsx`

The mic button sits between the attach button and the textarea. When `isListening`, the icon shows a pulse animation using the existing `vu-pulse` CSS class. On stop, the transcript is appended to the current textarea value.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/chat/__tests__/InputBar.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

// Mock useVoice
vi.mock("@/hooks/useVoice", () => ({
  useVoice: vi.fn(() => ({
    isSupported: true,
    isListening: false,
    transcript: "",
    start: vi.fn(),
    stop: vi.fn(),
    resetTranscript: vi.fn(),
  })),
}));

import { InputBar } from "../InputBar";

test("renders mic button when voice is supported", () => {
  render(<InputBar onSend={vi.fn()} />);
  expect(screen.getByLabelText("Voice input")).toBeInTheDocument();
});

test("mic button is hidden when voice not supported", () => {
  const { useVoice } = await import("@/hooks/useVoice");
  vi.mocked(useVoice).mockReturnValue({
    isSupported: false,
    isListening: false,
    transcript: "",
    start: vi.fn(),
    stop: vi.fn(),
    resetTranscript: vi.fn(),
  });
  render(<InputBar onSend={vi.fn()} />);
  expect(screen.queryByLabelText("Voice input")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx vitest run src/components/chat/__tests__/InputBar.test.tsx
```

Expected: FAIL

- [ ] **Step 3: Update InputBar.tsx**

Replace `frontend/src/components/chat/InputBar.tsx` with:

```tsx
import { useState, useRef, useCallback, useEffect, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { RiSendPlaneFill, RiAttachmentLine } from "react-icons/ri";
import { Mic, MicOff } from "lucide-react";
import { useUiStore } from "@/stores/uiStore";
import { useVoice } from "@/hooks/useVoice";

interface InputBarProps {
  onSend: (message: string) => void;
  onFileSelect?: (file: File) => void;
}

export function InputBar({ onSend, onFileSelect }: InputBarProps) {
  const [value, setValue] = useState("");
  const isStreaming = useUiStore((s) => s.isStreaming);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { isSupported, isListening, transcript, start, stop, resetTranscript } = useVoice();

  // When transcript arrives and we were listening, insert it
  useEffect(() => {
    if (transcript && !isListening) {
      setValue((prev) => (prev ? `${prev} ${transcript}` : transcript));
      resetTranscript();
    }
  }, [transcript, isListening, resetTranscript]);

  const handleMicToggle = useCallback(() => {
    if (isListening) {
      stop();
    } else {
      start();
    }
  }, [isListening, start, stop]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
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

      {/* Mic button — hidden if browser not supported */}
      {isSupported && (
        <Button
          variant="ghost"
          size="icon"
          onClick={handleMicToggle}
          disabled={isStreaming}
          className={`shrink-0 ${isListening ? "text-accent animate-[vu-pulse_1s_ease-in-out_infinite]" : "text-muted hover:text-text"}`}
          aria-label="Voice input"
        >
          {isListening ? <MicOff size={18} /> : <Mic size={18} />}
        </Button>
      )}

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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx vitest run src/components/chat/__tests__/InputBar.test.tsx
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/chat/InputBar.tsx src/components/chat/__tests__/InputBar.test.tsx
git commit -m "feat(ui): add mic toggle button to InputBar"
```

---

### Task 4: Add FR/EN toggle to Header

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx`

Add a `FR | EN` toggle next to the status badges. Active language highlighted in accent color.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/layout/__tests__/Header.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { test, expect, vi } from "vitest";
import { useUiStore } from "@/stores/uiStore";
import { Header } from "../Header";

vi.mock("@/lib/api", () => ({
  checkHealth: vi.fn().mockResolvedValue({ version: "1.0.0" }),
}));

test("renders FR and EN buttons", () => {
  render(<Header />);
  expect(screen.getByText("FR")).toBeInTheDocument();
  expect(screen.getByText("EN")).toBeInTheDocument();
});

test("clicking EN sets voiceLang to en-US", () => {
  render(<Header />);
  fireEvent.click(screen.getByText("EN"));
  expect(useUiStore.getState().voiceLang).toBe("en-US");
});

test("clicking FR sets voiceLang to fr-FR", () => {
  useUiStore.setState({ voiceLang: "en-US" });
  render(<Header />);
  fireEvent.click(screen.getByText("FR"));
  expect(useUiStore.getState().voiceLang).toBe("fr-FR");
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx vitest run src/components/layout/__tests__/Header.test.tsx
```

Expected: FAIL

- [ ] **Step 3: Update Header.tsx**

Replace `frontend/src/components/layout/Header.tsx` with:

```tsx
import { useUiStore, type VoiceLang } from "@/stores/uiStore";
import { useChatStore } from "@/stores/chatStore";
import { Badge } from "@/components/ui/badge";
import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

export function Header() {
  const isConnected = useUiStore((s) => s.isConnected);
  const setConnected = useUiStore((s) => s.setConnected);
  const isStreaming = useUiStore((s) => s.isStreaming);
  const voiceLang = useUiStore((s) => s.voiceLang);
  const setVoiceLang = useUiStore((s) => s.setVoiceLang);
  const [version, setVersion] = useState<string>("");

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

  const messages = useChatStore((s) => s.messages);
  const lastModel = [...messages].reverse().find((m) => m.modelUsed)?.modelUsed;

  const langs: { label: string; value: VoiceLang }[] = [
    { label: "FR", value: "fr-FR" },
    { label: "EN", value: "en-US" },
  ];

  return (
    <header className="flex items-center justify-between px-6 h-14 bg-surface border-b border-border">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-2xl text-accent tracking-wide">SONIQWERK</h1>
        {version && (
          <span className="text-xs text-muted font-mono">v{version}</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Voice language toggle */}
        <div className="flex items-center gap-1">
          {langs.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => setVoiceLang(value)}
              className={`text-xs font-mono px-1.5 py-0.5 rounded transition-colors ${
                voiceLang === value
                  ? "text-accent border border-accent/40"
                  : "text-muted hover:text-text"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx vitest run src/components/layout/__tests__/Header.test.tsx
```

Expected: PASS — 3/3

- [ ] **Step 5: Build check**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/frontend
npx tsc --noEmit && npx vite build
```

Expected: zero TypeScript errors, successful build

- [ ] **Step 6: Commit**

```bash
git add src/components/layout/Header.tsx src/components/layout/__tests__/Header.test.tsx
git commit -m "feat(ui): add FR/EN voice language toggle to Header"
```
