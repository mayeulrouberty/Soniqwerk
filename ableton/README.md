# Soniqwerk — Ableton integration

Bridge between the Soniqwerk backend and Ableton Live via Max for Live.

## Quick start

1. `cd ableton && npm install` — installs the `ws` WebSocket package
2. Start the WS bridge: `cd backend && python -m ws_bridge` (port 8001)
3. Drag `SONIQWERK.amxd` onto a MIDI track in Ableton

The bridge connects automatically and reconnects if it drops.

## SONIQWERK.amxd — built-in chat panel

The M4L device gives you an 800×240px chat panel directly in the device area. No browser needed.

- Type a command and hit Enter to query the agent
- The status dot shows connection state (red/orange/green)
- Click the URL or key fields in the top bar to edit them
- Scroll the history with the mouse wheel

All three files need to be in the same folder: `SONIQWERK.amxd`, `SONIQWERK_bridge.js`, `SONIQWERK_ui.js`.

Requires the backend on `localhost:8000` and the WS bridge on `localhost:8001`.

## Files

```
ableton/
├── SONIQWERK.amxd        # M4L device — drag into Ableton
├── SONIQWERK_bridge.js   # node.script: WS bridge + HTTP agent client
├── SONIQWERK_ui.js       # jsui canvas: status bar, chat history, input
├── package.json          # npm dep (ws)
└── README.md
```

## Troubleshooting

**Port 8001 in use:**
```bash
lsof -i :8001
kill -9 <PID>
```

**"ws package not found" in Max console:** run `npm install` in the `ableton` folder.

**Device connects but queries hang:** check that the FastAPI backend is up on port 8000, not just the WS bridge.
