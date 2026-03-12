# C2 — Native .amxd Device Design Spec

**Date:** 2026-03-12
**Sub-project:** C2 — Max for Live native device
**Status:** Approved

---

## Goal

Create a self-contained Max for Live device (`SONIQWERK.amxd`) that lets the user control the Soniqwerk agent directly from inside Ableton Live — no browser needed. The device provides a text input, a scrollable chat history, and a connection status indicator.

## Architecture

**Three files in `ableton/`:**

### `ableton/SONIQWERK.amxd` *(new)*

A Max patch JSON file (Max 8 format). Contains two objects:
- `node.script @file SONIQWERK_bridge.js` — reuses the existing bridge for all LOM operations and HTTP communication
- `jsui @file SONIQWERK_ui.js` — Canvas-based UI (800×240px)

The patch wires:
- jsui outlet 0 → node.script inlet 0 (send query text)
- node.script outlet 0 → jsui inlet 0 (receive response/status)

Device type: **Max MIDI Effect** (works on any track, no audio processing needed).

Presentation mode: `openinpresentation 1`, device panel size 800×240.

### `ableton/SONIQWERK_ui.js` *(new)*

jsui JavaScript file using Max's `mgraphics` API. Renders:

**Layout (800×240px):**
```
┌─────────────────────────────────────────────────────────┐
│  ● SONIQWERK              [localhost:8000]  [api: test]  │  h=32px
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Toi : crée un DnB à 174 BPM                            │
│  Agent : Session réglée. 3 pistes créées.                │
│  Toi : ajoute un reverb sur le pad                       │
│  Agent : Reverb chargé sur "Pad".                        │
│  ▼                                                       │  h=160px
├─────────────────────────────────────────────────────────┤
│  > ___________________________________ [Enter to send]   │  h=48px
└─────────────────────────────────────────────────────────┘
```

**Colors:** Background `#1a1a1a`, text `#e0e0e0`, user label `#7ec8e3`, agent label `#a8e6a3`, status green `#4caf50`, orange `#ff9800`, red `#f44336`.

**Input handling:** jsui receives `key` messages from Max. Printable characters appended to input buffer. Backspace removes last char. Enter (keycode 13) emits the buffer content on outlet 0, clears buffer.

**URL/API config fields:** Two small editable areas in the top bar. Click → `settextfield` Max message activates editing. Default values: `localhost:8000` and `test`.

**History:** List of `{role, text}` objects, max 100 entries. Auto-scrolls to bottom on new entry. Mouse wheel scrolls up/down.

**Status dot:** Reflects last message received from node.script:
- `connected 1` → green
- `connected 0` → red
- `connecting` → orange

### `ableton/SONIQWERK_bridge.js` *(modified)*

Add `agent_query` handler. When the UI sends a text query:

```javascript
// New: handle UI agent queries
function handleAgentQuery(text, backendUrl, apiKey) {
    const url = new URL("/v1/agent", "http://" + backendUrl);
    const body = JSON.stringify({ query: text, stream: false });
    // Uses Node.js https/http module to POST
    // Parses SSE stream, finds "done" event, extracts content
    // Sends maxApi.outlet(0, "agent_response", content) when done
    // Sends maxApi.outlet(0, "connected", 1) / ("connected", 0) based on connection state
}
```

The bridge uses Node.js built-in `http` module (already available in node.script). Parses the SSE stream line by line, extracts `data: {...}` JSON, yields text chunks until `{"type": "done"}` event.

---

## Data Flow

```
User types text + Enter
  → jsui outlet 0: ["agent_query", text, backendUrl, apiKey]
  → node.script receives message
  → HTTP POST http://{backendUrl}/v1/agent  {query: text}
  → SSE stream: chunks of {"type":"text","content":"..."} + {"type":"done","content":"final"}
  → node.script outlet 0: ["agent_response", finalText]
  → jsui receives, appends to history, scrolls to bottom
  → node.script outlet 0: ["connected", 1]  (or 0 on error)
  → jsui updates status dot
```

---

## Constraints

- Max for Live 8 (Live 11 / Live 12)
- jsui `mgraphics` API (not browser Canvas)
- No external npm packages — only `max-api` + Node.js built-ins (`http`, `https`)
- `SONIQWERK.amxd` must be self-contained: references `SONIQWERK_bridge.js` and `SONIQWERK_ui.js` by relative filename (Max searches its own folder)
- Max patch JSON uses `"fileversion": 1` format (Max 8)

---

## Testing

Manual testing only (requires Ableton Live + Max for Live):
1. Drag `SONIQWERK.amxd` into Ableton — device loads without errors
2. Status dot shows green when backend is running
3. Type a command, press Enter — response appears in history
4. Status dot shows red when backend is stopped
5. History scrolls correctly with mouse wheel
6. URL field defaults to `localhost:8000`, editable

---

## Out of Scope

- Audio/MIDI processing in the device
- Plugin scanning or preset browsing
- Real-time streaming (show text word-by-word) — final answer only
