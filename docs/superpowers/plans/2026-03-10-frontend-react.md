# SONIQWERK Frontend — React Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dark-themed React frontend for SONIQWERK — an AI assistant for electronic music production. The frontend consumes the existing FastAPI backend (port 8000) via REST + SSE, providing a chat interface with RAG-powered responses, a document ingestion library, and navigation for future Plugins/Ableton views.

**Architecture:**
```
frontend/
├── .env.example
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── vite.config.ts
├── vitest.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── lib/
│   │   ├── schemas.ts        # Zod request/response schemas
│   │   ├── api.ts            # Axios client + interceptors
│   │   └── utils.ts          # cn() helper
│   ├── stores/
│   │   ├── chatStore.ts      # Zustand chat state
│   │   ├── documentsStore.ts # Zustand documents state
│   │   └── uiStore.ts        # Zustand UI state (activeView, streaming)
│   ├── hooks/
│   │   ├── useSSE.ts         # Server-Sent Events hook
│   │   └── useUpload.ts      # File upload + polling hook
│   ├── components/
│   │   ├── ui/               # shadcn/ui components
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── StreamingMessage.tsx
│   │   │   └── InputBar.tsx
│   │   └── documents/
│   │       ├── DocumentLibrary.tsx
│   │       └── DropZone.tsx
│   └── __tests__/
│       ├── stores/
│       │   ├── chatStore.test.ts
│       │   ├── documentsStore.test.ts
│       │   └── uiStore.test.ts
│       ├── hooks/
│       │   ├── useSSE.test.tsx
│       │   └── useUpload.test.tsx
│       └── components/
│           ├── InputBar.test.tsx
│           └── DocumentLibrary.test.tsx
```

**Tech Stack:** Vite 5 · React 18 · TypeScript · Tailwind CSS · shadcn/ui · Zustand · Axios · Zod · Vitest · @testing-library/react

**Backend API contract (all routes require `X-API-Key` header):**
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat` | SSE stream — events: `chunk`, `sources`, `done`, `error` |
| `POST` | `/v1/documents/ingest` | Multipart upload (file + category) → 202 `{task_id, document_id, status}` |
| `GET` | `/v1/documents/ingest/{task_id}/status` | Poll ingestion → `{status, chunks_count, error}` |
| `GET` | `/health` | Health check → `{status: "ok", version: "2.0.0"}` |

---

## Chunk 1: Project Scaffold + Design System

### Task 1: Vite + React + TS + Tailwind init

- [ ] Scaffold the project and install all dependencies

**Files to create/modify:**

**1. Bootstrap project**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite postcss autoprefixer
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom happy-dom
npm install zustand axios zod react-icons clsx tailwind-merge
npm install -D @types/node
```

**2. `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/v1": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

**3. `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    css: false,
  },
});
```

**4. `frontend/src/test-setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

**5. `frontend/tsconfig.json`** — replace the generated one:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

**6. `frontend/.env.example`**

```
VITE_API_URL=http://localhost:8000
VITE_API_KEY=change-me
```

**7. `frontend/.env`** (local dev, gitignored)

```
VITE_API_URL=http://localhost:8000
VITE_API_KEY=change-me
```

**Verify command:**
```bash
cd frontend && npx tsc --noEmit && npm run build
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/ && git commit -m "feat(frontend): scaffold Vite + React + TS + Tailwind project"
```

---

### Task 2: Design tokens + fonts + global CSS

- [ ] Configure Tailwind colors, fonts, shadcn/ui, and global CSS

**1. `frontend/src/index.css`**

```css
@import "tailwindcss";

@theme {
  --color-bg: #06050b;
  --color-surface: #0d0c16;
  --color-border: #1c1a2e;
  --color-accent: #ff6b35;
  --color-green: #00f5a0;
  --color-text: #edeaf0;
  --color-muted: #8e8aaa;

  --font-display: "Bebas Neue", sans-serif;
  --font-ui: "Outfit", sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

@layer base {
  * {
    @apply border-border;
  }

  body {
    @apply bg-bg text-text font-ui antialiased;
    margin: 0;
    min-height: 100vh;
  }

  /* Custom scrollbar */
  ::-webkit-scrollbar {
    width: 6px;
  }
  ::-webkit-scrollbar-track {
    background: var(--color-bg);
  }
  ::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: var(--color-muted);
  }
}

/* VU meter animation */
@keyframes vu-pulse {
  0%, 100% { height: 20%; }
  50% { height: 80%; }
}

.vu-bar {
  animation: vu-pulse 0.6s ease-in-out infinite;
}
.vu-bar:nth-child(2) {
  animation-delay: 0.15s;
}
.vu-bar:nth-child(3) {
  animation-delay: 0.3s;
}
.vu-bar:nth-child(4) {
  animation-delay: 0.45s;
}

/* Streaming dots animation */
@keyframes dot-bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}
.streaming-dot {
  animation: dot-bounce 1.4s ease-in-out infinite;
}
.streaming-dot:nth-child(2) {
  animation-delay: 0.2s;
}
.streaming-dot:nth-child(3) {
  animation-delay: 0.4s;
}
```

**2. `frontend/index.html`** — replace the Vite default:

```html
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=JetBrains+Mono:wght@400;500&family=Outfit:wght@300;400;500;600;700&display=swap"
      rel="stylesheet"
    />
    <title>SONIQWERK</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**3. `frontend/src/lib/utils.ts`**

```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**4. Initialize shadcn/ui:**

```bash
cd frontend && npx shadcn-ui@latest init
```

When prompted, select:
- Style: Default
- Base color: Slate
- CSS variables: yes
- Tailwind config: tailwind.config.ts (if created by shadcn)
- Components alias: @/components/ui

Then add components:
```bash
npx shadcn-ui@latest add button textarea badge progress tooltip scroll-area
```

> **Note:** shadcn/ui may generate a `tailwind.config.ts` or `components.json`. Keep them but ensure our custom theme tokens in `index.css` take priority. If shadcn overrides `index.css`, re-add our `@theme` block at the top.

**5. `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

**6. `frontend/src/App.tsx`** (placeholder — replaced in Task 11):

```tsx
function App() {
  return (
    <div className="flex h-screen bg-bg">
      <p className="m-auto text-accent font-display text-4xl">SONIQWERK</p>
    </div>
  );
}

export default App;
```

**Verify command:**
```bash
cd frontend && npm run build && npm run dev -- --open
# Visually confirm: dark background (#06050b), orange "SONIQWERK" in Bebas Neue
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/ && git commit -m "feat(frontend): design tokens, fonts, global CSS, and shadcn/ui init"
```

---

## Chunk 2: Stores + API Client

### Task 3: Zod schemas (`lib/schemas.ts`)

- [ ] Define all Zod schemas matching backend API contracts

**File: `frontend/src/lib/schemas.ts`**

```ts
import { z } from "zod";

// ── Chat ────────────────────────────────────────────────────────────────

export const ChatRequestSchema = z.object({
  message: z.string().min(1, "Message cannot be empty"),
  conversation_id: z.string().uuid().optional(),
  model_override: z.string().optional(),
});
export type ChatRequest = z.infer<typeof ChatRequestSchema>;

export const ChunkEventSchema = z.object({
  text: z.string(),
  conversation_id: z.string().uuid(),
});
export type ChunkEvent = z.infer<typeof ChunkEventSchema>;

export const SourceSchema = z.object({
  title: z.string(),
  source: z.string(),
  score: z.number(),
});
export type Source = z.infer<typeof SourceSchema>;

export const SourcesEventSchema = z.object({
  sources: z.array(SourceSchema),
});
export type SourcesEvent = z.infer<typeof SourcesEventSchema>;

export const DoneEventSchema = z.object({
  model_used: z.string(),
  conversation_id: z.string().uuid(),
});
export type DoneEvent = z.infer<typeof DoneEventSchema>;

export const ErrorEventSchema = z.object({
  code: z.string(),
  message: z.string(),
});
export type ErrorEvent = z.infer<typeof ErrorEventSchema>;

// ── Documents ───────────────────────────────────────────────────────────

export const DocumentCategorySchema = z.enum([
  "manuals",
  "plugins",
  "books",
  "articles",
]);
export type DocumentCategory = z.infer<typeof DocumentCategorySchema>;

export const IngestResponseSchema = z.object({
  task_id: z.string(),
  document_id: z.string().uuid(),
  status: z.string(),
});
export type IngestResponse = z.infer<typeof IngestResponseSchema>;

export const IngestStatusSchema = z.object({
  status: z.enum(["queued", "processing", "ready", "error"]),
  chunks_count: z.number().nullable(),
  error: z.string().nullable(),
});
export type IngestStatus = z.infer<typeof IngestStatusSchema>;

// ── Health ──────────────────────────────────────────────────────────────

export const HealthSchema = z.object({
  status: z.string(),
  version: z.string(),
});
export type Health = z.infer<typeof HealthSchema>;

// ── App types (not API) ─────────────────────────────────────────────────

export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  sources?: Source[];
  modelUsed?: string;
  timestamp: number;
}

export interface DocumentItem {
  id: string;
  filename: string;
  category: DocumentCategory;
  status: "queued" | "processing" | "ready" | "error";
  chunksCount?: number;
  taskId: string;
  error?: string;
  addedAt: number;
}
```

**Test: `frontend/src/__tests__/stores/schemas.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import {
  ChatRequestSchema,
  ChunkEventSchema,
  SourcesEventSchema,
  DoneEventSchema,
  ErrorEventSchema,
  IngestResponseSchema,
  IngestStatusSchema,
  HealthSchema,
} from "@/lib/schemas";

describe("Zod schemas", () => {
  it("validates ChatRequest", () => {
    const valid = { message: "hello" };
    expect(ChatRequestSchema.parse(valid)).toEqual(valid);
  });

  it("rejects empty ChatRequest message", () => {
    expect(() => ChatRequestSchema.parse({ message: "" })).toThrow();
  });

  it("validates ChunkEvent", () => {
    const data = { text: "hi", conversation_id: "550e8400-e29b-41d4-a716-446655440000" };
    expect(ChunkEventSchema.parse(data)).toEqual(data);
  });

  it("validates SourcesEvent", () => {
    const data = {
      sources: [{ title: "Manual", source: "synth.pdf", score: 0.95 }],
    };
    expect(SourcesEventSchema.parse(data)).toEqual(data);
  });

  it("validates DoneEvent", () => {
    const data = {
      model_used: "gpt-4o",
      conversation_id: "550e8400-e29b-41d4-a716-446655440000",
    };
    expect(DoneEventSchema.parse(data)).toEqual(data);
  });

  it("validates ErrorEvent", () => {
    const data = { code: "LLM_TIMEOUT", message: "timed out" };
    expect(ErrorEventSchema.parse(data)).toEqual(data);
  });

  it("validates IngestResponse", () => {
    const data = {
      task_id: "abc-123",
      document_id: "550e8400-e29b-41d4-a716-446655440000",
      status: "queued",
    };
    expect(IngestResponseSchema.parse(data)).toEqual(data);
  });

  it("validates IngestStatus", () => {
    const data = { status: "ready", chunks_count: 42, error: null };
    expect(IngestStatusSchema.parse(data)).toEqual(data);
  });

  it("validates Health", () => {
    const data = { status: "ok", version: "2.0.0" };
    expect(HealthSchema.parse(data)).toEqual(data);
  });
});
```

**Verify command:**
```bash
cd frontend && npx vitest run src/__tests__/stores/schemas.test.ts
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/lib/schemas.ts frontend/src/__tests__/stores/schemas.test.ts && git commit -m "feat(frontend): Zod schemas for all API contracts"
```

---

### Task 4: Axios API client (`lib/api.ts`)

- [ ] Create Axios instance with API key interceptor and typed methods

**File: `frontend/src/lib/api.ts`**

```ts
import axios from "axios";
import type { IngestStatus, Health } from "./schemas";
import { IngestStatusSchema, HealthSchema } from "./schemas";

const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const apiKey = import.meta.env.VITE_API_KEY ?? "";

export const api = axios.create({
  baseURL,
  timeout: 30_000,
});

// Attach X-API-Key to every request
api.interceptors.request.use((config) => {
  config.headers["X-API-Key"] = apiKey;
  return config;
});

// ── Health ──────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<Health> {
  const { data } = await api.get("/health");
  return HealthSchema.parse(data);
}

// ── Documents ───────────────────────────────────────────────────────────

export async function uploadDocument(
  file: File,
  category: string
): Promise<{ task_id: string; document_id: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("category", category);
  const { data } = await api.post("/v1/documents/ingest", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60_000,
  });
  return data;
}

export async function pollIngestStatus(taskId: string): Promise<IngestStatus> {
  const { data } = await api.get(`/v1/documents/ingest/${taskId}/status`);
  return IngestStatusSchema.parse(data);
}

// ── Chat SSE URL builder ────────────────────────────────────────────────

export function getChatUrl(): string {
  return `${baseURL}/v1/chat`;
}

export function getApiKey(): string {
  return apiKey;
}
```

**No separate test file for api.ts** — covered by integration tests in hooks. The interceptor logic is trivial; schema validation is tested in Task 3.

**Verify command:**
```bash
cd frontend && npx tsc --noEmit
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/lib/api.ts && git commit -m "feat(frontend): Axios API client with X-API-Key interceptor"
```

---

### Task 5: Zustand stores

- [ ] Create chatStore, documentsStore, uiStore

**File: `frontend/src/stores/uiStore.ts`**

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

**File: `frontend/src/stores/chatStore.ts`**

```ts
import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";
import type { Message, Source } from "@/lib/schemas";

interface ChatState {
  messages: Message[];
  conversationId: string | null;
  currentStreamText: string;

  addUserMessage: (content: string) => string;
  startAssistantMessage: () => string;
  appendChunk: (messageId: string, text: string) => void;
  finalizeAssistant: (messageId: string, sources: Source[], modelUsed: string) => void;
  setError: (messageId: string, error: string) => void;
  setConversationId: (id: string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  conversationId: null,
  currentStreamText: "",

  addUserMessage: (content) => {
    const id = uuidv4();
    const msg: Message = {
      id,
      role: "user",
      content,
      timestamp: Date.now(),
    };
    set((state) => ({ messages: [...state.messages, msg] }));
    return id;
  },

  startAssistantMessage: () => {
    const id = uuidv4();
    const msg: Message = {
      id,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    };
    set((state) => ({
      messages: [...state.messages, msg],
      currentStreamText: "",
    }));
    return id;
  },

  appendChunk: (messageId, text) => {
    set((state) => ({
      currentStreamText: state.currentStreamText + text,
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, content: m.content + text } : m
      ),
    }));
  },

  finalizeAssistant: (messageId, sources, modelUsed) => {
    set((state) => ({
      currentStreamText: "",
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, sources, modelUsed } : m
      ),
    }));
  },

  setError: (messageId, error) => {
    set((state) => ({
      currentStreamText: "",
      messages: state.messages.map((m) =>
        m.id === messageId
          ? { ...m, content: `Error: ${error}` }
          : m
      ),
    }));
  },

  setConversationId: (id) => set({ conversationId: id }),

  clearMessages: () => set({ messages: [], conversationId: null, currentStreamText: "" }),
}));
```

> **Note:** Install uuid: `npm install uuid && npm install -D @types/uuid`

**File: `frontend/src/stores/documentsStore.ts`**

```ts
import { create } from "zustand";
import type { DocumentItem, DocumentCategory } from "@/lib/schemas";

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
```

**Test: `frontend/src/__tests__/stores/chatStore.test.ts`**

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { useChatStore } from "@/stores/chatStore";

describe("chatStore", () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [],
      conversationId: null,
      currentStreamText: "",
    });
  });

  it("adds a user message", () => {
    const id = useChatStore.getState().addUserMessage("hello");
    const msgs = useChatStore.getState().messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0].role).toBe("user");
    expect(msgs[0].content).toBe("hello");
    expect(msgs[0].id).toBe(id);
  });

  it("starts an assistant message with empty content", () => {
    const id = useChatStore.getState().startAssistantMessage();
    const msgs = useChatStore.getState().messages;
    expect(msgs).toHaveLength(1);
    expect(msgs[0].role).toBe("assistant");
    expect(msgs[0].content).toBe("");
    expect(msgs[0].id).toBe(id);
  });

  it("appends chunks to an assistant message", () => {
    const id = useChatStore.getState().startAssistantMessage();
    useChatStore.getState().appendChunk(id, "Hello ");
    useChatStore.getState().appendChunk(id, "world");
    const msg = useChatStore.getState().messages[0];
    expect(msg.content).toBe("Hello world");
    expect(useChatStore.getState().currentStreamText).toBe("Hello world");
  });

  it("finalizes with sources and model", () => {
    const id = useChatStore.getState().startAssistantMessage();
    useChatStore.getState().appendChunk(id, "response");
    useChatStore.getState().finalizeAssistant(
      id,
      [{ title: "Manual", source: "test.pdf", score: 0.9 }],
      "gpt-4o"
    );
    const msg = useChatStore.getState().messages[0];
    expect(msg.sources).toHaveLength(1);
    expect(msg.modelUsed).toBe("gpt-4o");
    expect(useChatStore.getState().currentStreamText).toBe("");
  });

  it("sets error on a message", () => {
    const id = useChatStore.getState().startAssistantMessage();
    useChatStore.getState().setError(id, "timeout");
    expect(useChatStore.getState().messages[0].content).toBe("Error: timeout");
  });

  it("clears all messages", () => {
    useChatStore.getState().addUserMessage("hi");
    useChatStore.getState().clearMessages();
    expect(useChatStore.getState().messages).toHaveLength(0);
    expect(useChatStore.getState().conversationId).toBeNull();
  });
});
```

**Test: `frontend/src/__tests__/stores/documentsStore.test.ts`**

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { useDocumentsStore } from "@/stores/documentsStore";

describe("documentsStore", () => {
  beforeEach(() => {
    useDocumentsStore.setState({ documents: [] });
  });

  it("adds a document", () => {
    useDocumentsStore.getState().addDocument({
      id: "doc-1",
      filename: "test.pdf",
      category: "manuals",
      status: "queued",
      taskId: "task-1",
      addedAt: Date.now(),
    });
    expect(useDocumentsStore.getState().documents).toHaveLength(1);
  });

  it("updates document status", () => {
    useDocumentsStore.getState().addDocument({
      id: "doc-1",
      filename: "test.pdf",
      category: "manuals",
      status: "queued",
      taskId: "task-1",
      addedAt: Date.now(),
    });
    useDocumentsStore.getState().updateStatus("task-1", "ready", 42);
    const doc = useDocumentsStore.getState().documents[0];
    expect(doc.status).toBe("ready");
    expect(doc.chunksCount).toBe(42);
  });

  it("removes a document", () => {
    useDocumentsStore.getState().addDocument({
      id: "doc-1",
      filename: "test.pdf",
      category: "manuals",
      status: "ready",
      taskId: "task-1",
      addedAt: Date.now(),
    });
    useDocumentsStore.getState().removeDocument("doc-1");
    expect(useDocumentsStore.getState().documents).toHaveLength(0);
  });
});
```

**Test: `frontend/src/__tests__/stores/uiStore.test.ts`**

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { useUiStore } from "@/stores/uiStore";

describe("uiStore", () => {
  beforeEach(() => {
    useUiStore.setState({
      activeView: "chat",
      isStreaming: false,
      isConnected: false,
    });
  });

  it("changes active view", () => {
    useUiStore.getState().setActiveView("documents");
    expect(useUiStore.getState().activeView).toBe("documents");
  });

  it("toggles streaming state", () => {
    useUiStore.getState().setStreaming(true);
    expect(useUiStore.getState().isStreaming).toBe(true);
    useUiStore.getState().setStreaming(false);
    expect(useUiStore.getState().isStreaming).toBe(false);
  });

  it("sets connected state", () => {
    useUiStore.getState().setConnected(true);
    expect(useUiStore.getState().isConnected).toBe(true);
  });
});
```

**Verify command:**
```bash
cd frontend && npm install uuid @types/uuid && npx vitest run src/__tests__/stores/
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/stores/ frontend/src/__tests__/stores/ && git commit -m "feat(frontend): Zustand stores — chat, documents, UI"
```

---

## Chunk 3: Hooks

### Task 6: `useSSE` hook

- [ ] Implement SSE hook with full event handling and reconnection

**File: `frontend/src/hooks/useSSE.ts`**

```ts
import { useCallback, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useUiStore } from "@/stores/uiStore";
import {
  ChunkEventSchema,
  SourcesEventSchema,
  DoneEventSchema,
  ErrorEventSchema,
} from "@/lib/schemas";
import { getChatUrl, getApiKey } from "@/lib/api";

interface UseSSEReturn {
  sendMessage: (message: string, modelOverride?: string) => void;
  abort: () => void;
}

export function useSSE(): UseSSEReturn {
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    (message: string, modelOverride?: string) => {
      const chatStore = useChatStore.getState();
      const uiStore = useUiStore.getState();

      // Add user message
      chatStore.addUserMessage(message);

      // Start assistant message placeholder
      const assistantId = chatStore.startAssistantMessage();
      uiStore.setStreaming(true);

      // Abort any existing request
      if (abortRef.current) {
        abortRef.current.abort();
      }
      abortRef.current = new AbortController();

      const body = JSON.stringify({
        message,
        conversation_id: chatStore.conversationId ?? undefined,
        model_override: modelOverride,
      });

      fetch(getChatUrl(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": getApiKey(),
        },
        body,
        signal: abortRef.current.signal,
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const reader = response.body?.getReader();
          if (!reader) throw new Error("No response body");

          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            // Keep the last potentially incomplete line in buffer
            buffer = lines.pop() ?? "";

            let eventType = "";
            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith("data: ") && eventType) {
                const jsonStr = line.slice(6);
                try {
                  const payload = JSON.parse(jsonStr);
                  handleEvent(eventType, payload, assistantId);
                } catch {
                  // Malformed JSON line — skip
                }
                eventType = "";
              }
            }
          }
        })
        .catch((err) => {
          if (err.name === "AbortError") return;
          useChatStore.getState().setError(assistantId, err.message);
        })
        .finally(() => {
          useUiStore.getState().setStreaming(false);
        });
    },
    []
  );

  const abort = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    useUiStore.getState().setStreaming(false);
  }, []);

  return { sendMessage, abort };
}

function handleEvent(
  eventType: string,
  payload: unknown,
  assistantId: string
): void {
  const chatStore = useChatStore.getState();

  switch (eventType) {
    case "chunk": {
      const parsed = ChunkEventSchema.safeParse(payload);
      if (parsed.success) {
        chatStore.appendChunk(assistantId, parsed.data.text);
        // Set conversation ID from first chunk
        if (!chatStore.conversationId) {
          chatStore.setConversationId(parsed.data.conversation_id);
        }
      }
      break;
    }
    case "sources": {
      const parsed = SourcesEventSchema.safeParse(payload);
      if (parsed.success) {
        // Sources are stored but finalization happens on "done"
        // Temporarily hold them on the message
        const msg = chatStore.messages.find((m) => m.id === assistantId);
        if (msg) {
          useChatStore.setState((state) => ({
            messages: state.messages.map((m) =>
              m.id === assistantId ? { ...m, sources: parsed.data.sources } : m
            ),
          }));
        }
      }
      break;
    }
    case "done": {
      const parsed = DoneEventSchema.safeParse(payload);
      if (parsed.success) {
        const msg = useChatStore.getState().messages.find((m) => m.id === assistantId);
        chatStore.finalizeAssistant(
          assistantId,
          msg?.sources ?? [],
          parsed.data.model_used
        );
        chatStore.setConversationId(parsed.data.conversation_id);
      }
      break;
    }
    case "error": {
      const parsed = ErrorEventSchema.safeParse(payload);
      if (parsed.success) {
        chatStore.setError(assistantId, `${parsed.data.code}: ${parsed.data.message}`);
      }
      break;
    }
  }
}
```

**Test: `frontend/src/__tests__/hooks/useSSE.test.tsx`**

```tsx
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSSE } from "@/hooks/useSSE";
import { useChatStore } from "@/stores/chatStore";
import { useUiStore } from "@/stores/uiStore";

// Mock fetch with SSE response
function createSSEResponse(events: Array<{ event: string; data: string }>) {
  const text = events
    .map((e) => `event: ${e.event}\ndata: ${e.data}\n\n`)
    .join("");
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("useSSE", () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [],
      conversationId: null,
      currentStreamText: "",
    });
    useUiStore.setState({
      activeView: "chat",
      isStreaming: false,
      isConnected: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends a message and processes chunk + done events", async () => {
    const convId = "550e8400-e29b-41d4-a716-446655440000";
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      createSSEResponse([
        {
          event: "chunk",
          data: JSON.stringify({ text: "Hello ", conversation_id: convId }),
        },
        {
          event: "chunk",
          data: JSON.stringify({ text: "world", conversation_id: convId }),
        },
        {
          event: "sources",
          data: JSON.stringify({ sources: [] }),
        },
        {
          event: "done",
          data: JSON.stringify({ model_used: "gpt-4o", conversation_id: convId }),
        },
      ])
    );

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      result.current.sendMessage("test");
      // Let microtasks settle
      await new Promise((r) => setTimeout(r, 50));
    });

    const state = useChatStore.getState();
    expect(state.messages).toHaveLength(2); // user + assistant
    expect(state.messages[0].role).toBe("user");
    expect(state.messages[0].content).toBe("test");
    expect(state.messages[1].role).toBe("assistant");
    expect(state.messages[1].content).toBe("Hello world");
    expect(state.conversationId).toBe(convId);
    expect(useUiStore.getState().isStreaming).toBe(false);
  });

  it("handles error events", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      createSSEResponse([
        {
          event: "error",
          data: JSON.stringify({ code: "LLM_TIMEOUT", message: "timed out" }),
        },
      ])
    );

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      result.current.sendMessage("test");
      await new Promise((r) => setTimeout(r, 50));
    });

    const msgs = useChatStore.getState().messages;
    expect(msgs[1].content).toContain("LLM_TIMEOUT");
  });

  it("handles fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useSSE());

    await act(async () => {
      result.current.sendMessage("test");
      await new Promise((r) => setTimeout(r, 50));
    });

    const msgs = useChatStore.getState().messages;
    expect(msgs[1].content).toContain("Network error");
    expect(useUiStore.getState().isStreaming).toBe(false);
  });
});
```

**Verify command:**
```bash
cd frontend && npx vitest run src/__tests__/hooks/useSSE.test.tsx
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/hooks/useSSE.ts frontend/src/__tests__/hooks/useSSE.test.tsx && git commit -m "feat(frontend): useSSE hook with chunk/sources/done/error handling"
```

---

### Task 7: `useUpload` hook

- [ ] Implement file upload hook with polling

**File: `frontend/src/hooks/useUpload.ts`**

```ts
import { useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { uploadDocument, pollIngestStatus } from "@/lib/api";
import { useDocumentsStore } from "@/stores/documentsStore";
import type { DocumentCategory } from "@/lib/schemas";

interface UseUploadReturn {
  upload: (file: File, category: DocumentCategory) => Promise<void>;
  isUploading: boolean;
}

export function useUpload(): UseUploadReturn {
  const isUploadingRef = useRef(false);

  const upload = useCallback(async (file: File, category: DocumentCategory) => {
    const store = useDocumentsStore.getState();
    const docId = uuidv4();

    isUploadingRef.current = true;

    try {
      // Call upload API
      const response = await uploadDocument(file, category);

      // Add to store
      store.addDocument({
        id: response.document_id,
        filename: file.name,
        category,
        status: "queued",
        taskId: response.task_id,
        addedAt: Date.now(),
      });

      // Start polling
      pollUntilDone(response.task_id);
    } catch (err) {
      // Add as errored document
      store.addDocument({
        id: docId,
        filename: file.name,
        category,
        status: "error",
        taskId: "",
        error: err instanceof Error ? err.message : "Upload failed",
        addedAt: Date.now(),
      });
    } finally {
      isUploadingRef.current = false;
    }
  }, []);

  return {
    upload,
    get isUploading() {
      return isUploadingRef.current;
    },
  };
}

function pollUntilDone(taskId: string): void {
  const interval = setInterval(async () => {
    try {
      const status = await pollIngestStatus(taskId);
      const store = useDocumentsStore.getState();

      if (status.status === "ready") {
        store.updateStatus(taskId, "ready", status.chunks_count ?? undefined);
        clearInterval(interval);
      } else if (status.status === "error") {
        store.updateStatus(taskId, "error", undefined, status.error ?? "Ingestion failed");
        clearInterval(interval);
      } else {
        store.updateStatus(taskId, status.status as "queued" | "processing");
      }
    } catch {
      // On poll error, just keep trying (server might be temporarily unavailable)
    }
  }, 2000);

  // Safety: stop polling after 5 minutes
  setTimeout(() => clearInterval(interval), 5 * 60 * 1000);
}
```

**Test: `frontend/src/__tests__/hooks/useUpload.test.tsx`**

```tsx
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useUpload } from "@/hooks/useUpload";
import { useDocumentsStore } from "@/stores/documentsStore";

vi.mock("@/lib/api", () => ({
  uploadDocument: vi.fn(),
  pollIngestStatus: vi.fn(),
}));

import { uploadDocument, pollIngestStatus } from "@/lib/api";

describe("useUpload", () => {
  beforeEach(() => {
    useDocumentsStore.setState({ documents: [] });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("uploads a file and adds it to the store", async () => {
    const mockUpload = vi.mocked(uploadDocument);
    mockUpload.mockResolvedValueOnce({
      task_id: "task-1",
      document_id: "doc-1",
      status: "queued",
    });

    const mockPoll = vi.mocked(pollIngestStatus);
    mockPoll.mockResolvedValue({
      status: "ready",
      chunks_count: 10,
      error: null,
    });

    const { result } = renderHook(() => useUpload());
    const file = new File(["pdf content"], "test.pdf", { type: "application/pdf" });

    await act(async () => {
      await result.current.upload(file, "manuals");
    });

    const docs = useDocumentsStore.getState().documents;
    expect(docs).toHaveLength(1);
    expect(docs[0].filename).toBe("test.pdf");
    expect(docs[0].status).toBe("queued");

    // Advance timer for polling
    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve(); // flush microtasks
    });

    const updatedDocs = useDocumentsStore.getState().documents;
    expect(updatedDocs[0].status).toBe("ready");
    expect(updatedDocs[0].chunksCount).toBe(10);
  });

  it("handles upload failure", async () => {
    const mockUpload = vi.mocked(uploadDocument);
    mockUpload.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useUpload());
    const file = new File(["pdf content"], "test.pdf", { type: "application/pdf" });

    await act(async () => {
      await result.current.upload(file, "manuals");
    });

    const docs = useDocumentsStore.getState().documents;
    expect(docs).toHaveLength(1);
    expect(docs[0].status).toBe("error");
    expect(docs[0].error).toBe("Network error");
  });
});
```

**Verify command:**
```bash
cd frontend && npx vitest run src/__tests__/hooks/useUpload.test.tsx
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/hooks/ frontend/src/__tests__/hooks/ && git commit -m "feat(frontend): useUpload hook with polling for ingestion status"
```

---

## Chunk 4: Components + App Integration

### Task 8: Layout components (Sidebar, Header)

- [ ] Build Sidebar with navigation and VU meter indicator
- [ ] Build Header with title, model badge, and connection status

**File: `frontend/src/components/layout/Sidebar.tsx`**

```tsx
import { RiChat1Fill, RiFileList3Fill, RiPlugFill, RiMusic2Fill } from "react-icons/ri";
import { cn } from "@/lib/utils";
import { useUiStore, type View } from "@/stores/uiStore";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface NavItem {
  view: View;
  label: string;
  icon: React.ReactNode;
  locked?: boolean;
}

const navItems: NavItem[] = [
  { view: "chat", label: "Chat", icon: <RiChat1Fill size={22} /> },
  { view: "documents", label: "Documents", icon: <RiFileList3Fill size={22} /> },
  { view: "plugins", label: "Plugins (soon)", icon: <RiPlugFill size={22} />, locked: false },
  { view: "ableton", label: "Ableton (Phase 3)", icon: <RiMusic2Fill size={22} />, locked: true },
];

function VuMeter() {
  const isStreaming = useUiStore((s) => s.isStreaming);

  if (!isStreaming) return null;

  return (
    <div className="flex items-end gap-[3px] h-5 px-2 py-1">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="vu-bar w-[3px] rounded-full bg-green"
          style={{ height: "20%" }}
        />
      ))}
    </div>
  );
}

export function Sidebar() {
  const activeView = useUiStore((s) => s.activeView);
  const setActiveView = useUiStore((s) => s.setActiveView);

  return (
    <TooltipProvider delayDuration={300}>
      <aside className="flex flex-col items-center w-16 bg-surface border-r border-border py-4 gap-2">
        {/* Logo */}
        <div className="text-accent font-display text-lg mb-4 select-none">SQ</div>

        {/* Nav items */}
        <nav className="flex flex-col gap-1 flex-1">
          {navItems.map((item) => (
            <Tooltip key={item.view}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => !item.locked && setActiveView(item.view)}
                  disabled={item.locked}
                  className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-lg transition-colors",
                    activeView === item.view
                      ? "bg-accent/20 text-accent"
                      : "text-muted hover:text-text hover:bg-border/50",
                    item.locked && "opacity-30 cursor-not-allowed"
                  )}
                  aria-label={item.label}
                >
                  {item.icon}
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>{item.label}</p>
              </TooltipContent>
            </Tooltip>
          ))}
        </nav>

        {/* VU meter */}
        <VuMeter />
      </aside>
    </TooltipProvider>
  );
}
```

**File: `frontend/src/components/layout/Header.tsx`**

```tsx
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
```

**Verify command:**
```bash
cd frontend && npx tsc --noEmit
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/components/layout/ && git commit -m "feat(frontend): Sidebar with nav + VU meter, Header with status"
```

---

### Task 9: Chat components

- [ ] Build ChatWindow, MessageBubble, StreamingMessage, InputBar

**File: `frontend/src/components/chat/MessageBubble.tsx`**

```tsx
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
```

**File: `frontend/src/components/chat/StreamingMessage.tsx`**

```tsx
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
```

**File: `frontend/src/components/chat/InputBar.tsx`**

```tsx
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
```

**File: `frontend/src/components/chat/ChatWindow.tsx`**

```tsx
import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useUiStore } from "@/stores/uiStore";
import { useSSE } from "@/hooks/useSSE";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./MessageBubble";
import { StreamingMessage } from "./StreamingMessage";
import { InputBar } from "./InputBar";

export function ChatWindow() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useUiStore((s) => s.isStreaming);
  const { sendMessage } = useSSE();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or chunks
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <ScrollArea className="flex-1 px-6 py-4">
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
      </ScrollArea>

      {/* Input bar */}
      <InputBar onSend={sendMessage} />
    </div>
  );
}
```

**Test: `frontend/src/__tests__/components/InputBar.test.tsx`**

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InputBar } from "@/components/chat/InputBar";
import { useUiStore } from "@/stores/uiStore";

describe("InputBar", () => {
  const mockSend = vi.fn();

  beforeEach(() => {
    mockSend.mockClear();
    useUiStore.setState({ isStreaming: false });
  });

  it("renders textarea and send button", () => {
    render(<InputBar onSend={mockSend} />);
    expect(screen.getByPlaceholderText(/Ask about music/)).toBeInTheDocument();
    expect(screen.getByLabelText("Send message")).toBeInTheDocument();
  });

  it("sends message on button click", async () => {
    const user = userEvent.setup();
    render(<InputBar onSend={mockSend} />);

    const textarea = screen.getByPlaceholderText(/Ask about music/);
    await user.type(textarea, "hello");
    await user.click(screen.getByLabelText("Send message"));

    expect(mockSend).toHaveBeenCalledWith("hello");
  });

  it("sends message on Ctrl+Enter", async () => {
    const user = userEvent.setup();
    render(<InputBar onSend={mockSend} />);

    const textarea = screen.getByPlaceholderText(/Ask about music/);
    await user.type(textarea, "hello");
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(mockSend).toHaveBeenCalledWith("hello");
  });

  it("does not send empty message", async () => {
    const user = userEvent.setup();
    render(<InputBar onSend={mockSend} />);

    await user.click(screen.getByLabelText("Send message"));
    expect(mockSend).not.toHaveBeenCalled();
  });

  it("disables input when streaming", () => {
    useUiStore.setState({ isStreaming: true });
    render(<InputBar onSend={mockSend} />);

    expect(screen.getByPlaceholderText(/Ask about music/)).toBeDisabled();
  });
});
```

**Verify command:**
```bash
cd frontend && npx vitest run src/__tests__/components/InputBar.test.tsx
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/components/chat/ frontend/src/__tests__/components/InputBar.test.tsx && git commit -m "feat(frontend): chat components — ChatWindow, MessageBubble, StreamingMessage, InputBar"
```

---

### Task 10: Document components (DropZone, DocumentLibrary)

- [ ] Build DropZone with drag-and-drop and progress
- [ ] Build DocumentLibrary with status badges

**File: `frontend/src/components/documents/DropZone.tsx`**

```tsx
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

          {uploading && <Progress value={undefined} className="h-1" />}
        </div>
      )}
    </div>
  );
}
```

**File: `frontend/src/components/documents/DocumentLibrary.tsx`**

```tsx
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
```

**Test: `frontend/src/__tests__/components/DocumentLibrary.test.tsx`**

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { DocumentLibrary } from "@/components/documents/DocumentLibrary";
import { useDocumentsStore } from "@/stores/documentsStore";

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
```

**Verify command:**
```bash
cd frontend && npx vitest run src/__tests__/components/DocumentLibrary.test.tsx
```

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/components/documents/ frontend/src/__tests__/components/DocumentLibrary.test.tsx && git commit -m "feat(frontend): DropZone with drag-and-drop + DocumentLibrary with status badges"
```

---

### Task 11: App.tsx + final integration + build verify

- [ ] Wire everything together in App.tsx
- [ ] Run full test suite
- [ ] Verify production build

**File: `frontend/src/App.tsx`** (replace placeholder from Task 2):

```tsx
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { DocumentLibrary } from "@/components/documents/DocumentLibrary";
import { useUiStore } from "@/stores/uiStore";

function PluginsPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h2 className="font-display text-3xl text-accent mb-2">Plugins</h2>
        <p className="text-muted text-sm">Plugin management coming soon.</p>
      </div>
    </div>
  );
}

function AbletonPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h2 className="font-display text-3xl text-muted mb-2">Ableton Link</h2>
        <p className="text-muted text-sm">Phase 3 — WebSocket bridge to Ableton Live.</p>
      </div>
    </div>
  );
}

function MainContent() {
  const activeView = useUiStore((s) => s.activeView);

  switch (activeView) {
    case "chat":
      return <ChatWindow />;
    case "documents":
      return <DocumentLibrary />;
    case "plugins":
      return <PluginsPlaceholder />;
    case "ableton":
      return <AbletonPlaceholder />;
    default:
      return <ChatWindow />;
  }
}

function App() {
  return (
    <div className="flex h-screen bg-bg overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          <MainContent />
        </main>
      </div>
    </div>
  );
}

export default App;
```

**Full test suite command:**
```bash
cd frontend && npx vitest run
```

**Production build verify:**
```bash
cd frontend && npm run build
```

Expected output: `dist/` folder with `index.html`, `assets/` with JS and CSS bundles, zero errors.

**Git commit:**
```bash
cd /Users/charlotte/Desktop/Soniqwerk && git add frontend/src/App.tsx && git commit -m "feat(frontend): App.tsx final integration — route views through Sidebar"
```

---

## Post-Implementation Checklist

- [ ] All tests pass: `cd frontend && npx vitest run`
- [ ] TypeScript clean: `cd frontend && npx tsc --noEmit`
- [ ] Build succeeds: `cd frontend && npm run build`
- [ ] Dev server starts: `cd frontend && npm run dev`
- [ ] `.env.example` exists with `VITE_API_URL` and `VITE_API_KEY`
- [ ] All 4 views reachable from Sidebar (Chat, Documents, Plugins placeholder, Ableton locked)
- [ ] VU meter animates when `isStreaming === true`
- [ ] Chat sends via SSE and streams response chunks
- [ ] Document upload triggers polling until ready/error
- [ ] Connection status dot reflects `/health` check

## Dependency Summary

```bash
# Production
npm install zustand axios zod react-icons clsx tailwind-merge uuid

# Dev
npm install -D tailwindcss @tailwindcss/vite postcss autoprefixer
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
npm install -D @types/node @types/uuid

# shadcn/ui (via CLI)
npx shadcn-ui@latest init
npx shadcn-ui@latest add button textarea badge progress tooltip scroll-area
```

## File Count

| Chunk | Files | Tests |
|-------|-------|-------|
| 1: Scaffold | 7 | 0 |
| 2: Stores + API | 5 | 4 |
| 3: Hooks | 2 | 2 |
| 4: Components | 8 | 2 |
| **Total** | **22** | **8** |
