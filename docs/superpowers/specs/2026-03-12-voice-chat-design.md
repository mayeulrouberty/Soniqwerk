# Voice Input for Chat — Design Spec

**Date:** 2026-03-12
**Sub-project:** B — Voice → Chatbot
**Status:** Approved

---

## Goal

Add a microphone toggle button to the chat InputBar so users can dictate messages using the Web Speech API. Transcription inserts into the textarea for review before sending. Language switchable between French and English.

## Architecture

Three files modified, one new hook:

### `frontend/src/hooks/useVoice.ts` *(new)*

Encapsulates Web Speech API:
- Exposes: `isListening: boolean`, `isSupported: boolean`, `transcript: string`, `start()`, `stop()`
- Reads `voiceLang` from `uiStore`
- On `onresult`: updates `transcript` with the latest final result
- On `onerror`: sets `isListening = false`, logs error
- On `onend`: sets `isListening = false`
- If `window.SpeechRecognition` and `window.webkitSpeechRecognition` are both undefined → `isSupported = false`

### `frontend/src/stores/uiStore.ts` *(modified)*

Add `voiceLang: "fr-FR" | "en-US"` field with setter `setVoiceLang()`. Default: `"fr-FR"`. Persist to localStorage via Zustand `persist` middleware (already used or to be added).

### `frontend/src/components/chat/InputBar.tsx` *(modified)*

- Add mic button (icon: `Mic` / `MicOff` from lucide-react) to the right of the textarea, left of the send button
- Button hidden if `isSupported === false`
- Toggle behavior: click starts listening (icon animates with `vu-pulse` CSS class), click stops and inserts `transcript` into the textarea value
- After inserting transcript, `transcript` is reset
- Button disabled during `isStreaming` (same condition as send button)

### `frontend/src/components/layout/Header.tsx` *(modified)*

Add a `FR | EN` language toggle (two small clickable text labels) next to the existing status badges. Updates `voiceLang` in `uiStore`. Active language highlighted with accent color `#ff6b35`.

## Data Flow

```
User clicks mic → useVoice.start(voiceLang)
  → SpeechRecognition.start()
  → interim/final results → transcript updated in hook state
User clicks mic again → useVoice.stop()
  → SpeechRecognition.stop()
  → InputBar inserts transcript into textarea
  → User reviews text → presses Enter or Send button
  → existing chat flow (useSSE)
```

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Browser not supported | Mic button hidden, no error shown |
| Microphone permission denied | `isListening = false`, button returns to idle state |
| Network error (Speech API) | Same as above |
| Empty transcript on stop | Nothing inserted, no visual change |

## Testing

- `tests/useVoice.test.ts`: mock `window.SpeechRecognition`, verify `isSupported`, `start()` sets `isListening=true`, transcript updated on `onresult`, `stop()` sets `isListening=false`
- `tests/InputBar.test.tsx`: mic button renders when supported, hidden when not, inserts transcript on stop
- Manual: test in Chrome with fr-FR and en-US, verify transcript quality

## Constraints

- Web Speech API: Chrome and Edge only. Firefox and Safari → button hidden.
- No backend changes required (transcription is client-side only).
- No new npm dependencies (Web Speech API is native).
