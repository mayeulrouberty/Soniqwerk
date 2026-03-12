# SONIQWERK Max for Live Integration

This directory contains the Max for Live device and setup guide for integrating Soniqwerk's AI agent with Ableton Live.

## Prerequisites

- **Ableton Live 11** or **Live 12**
- **Max for Live** installed and licensed
- **Node.js ≥ 18** (for npm)
- **Python 3.9+** (for the backend WebSocket server)

## Installation

### 1. Install npm dependencies

Navigate to the `ableton` directory and install the WebSocket package:

```bash
cd ableton
npm install
```

This installs `ws ^8.0.0`, which is required by the Node.js bridge script.

### 2. Start the WebSocket backend

In a terminal, navigate to the `backend` directory and start the WebSocket bridge server:

```bash
cd backend
python -m ws_bridge
```

The server will start on **port 8001** and listen for WebSocket connections. You should see output confirming the server is running:

```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

### 3. Create the Max for Live Device

1. Open **Ableton Live**
2. Open the **Max for Live device editor** (Ctrl+Shift+M on Windows, Cmd+Shift+M on Mac)
3. Create a new M4L MIDI effect
4. In the Max patcher, add:
   - A `node.script` object with the argument `SONIQWERK_bridge.js`
   - A `LiveAPI` object
   - Connect the outlet of `node.script` (outlet 0) to the inlet of `LiveAPI` (inlet 0)
   - Connect the outlets of `LiveAPI` back to inlets 0 and 1 of `node.script` using message routing for `lom_response` and `lom_error` messages

5. Save the device as a `.amxd` file (e.g., `SONIQWERK.amxd`) in your Max for Live devices folder

**Alternative**: Copy the pre-built device `.amxd` file if available, or use the patcher template included in this repo

### 4. Deploy to Ableton

1. Drag the `.amxd` device onto any **MIDI track** in Ableton
2. The device is now active and will communicate with the backend bridge

## Verification

1. **Check the Max console** in Ableton (Cmd+M on Mac, Ctrl+M on Windows to toggle the Max console)
2. You should see the message:

   ```
   SONIQWERK: Connected to backend
   ```

   This confirms the Max for Live device has successfully connected to the WebSocket bridge.

3. If you see a reconnection message, check that the backend server is running on port 8001

## Using the Agent

Once the device is connected, you can query the AI agent:

1. Send a **POST request** to the backend API:

   ```bash
   curl -X POST http://localhost:8000/v1/agent \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_api_key" \
     -d '{"query": "What plugins are on track 1?"}'
   ```

2. The agent will:
   - Receive your query
   - Interact with Ableton Live via the Max for Live device
   - Execute LOM (Live Object Model) commands
   - Return AI-generated responses with live session data

3. For streaming responses, subscribe to the SSE endpoint:

   ```bash
   curl -N http://localhost:8000/v1/agent/stream \
     -H "X-API-Key: your_api_key" \
     -d 'query=Tell me about my clips'
   ```

## Troubleshooting

### Port 8001 already in use

If you see an error like `Address already in use`, another process is using port 8001:

```bash
# macOS/Linux: find and kill the process
lsof -i :8001
kill -9 <PID>

# Windows: find and kill the process
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

Or specify a different port when starting the backend (see `backend/ws_bridge/` for configuration).

### "ws package not found" error in Max console

Ensure you ran `npm install` in the `ableton` directory. The `ws` module must be installed before Max can load the script.

### Max console shows "WebSocket error" or "Disconnected"

1. Verify the backend server is running on port 8001
2. Check for firewall issues blocking localhost:8001
3. Ensure the `SONIQWERK_bridge.js` path is correct in the `node.script` object
4. Check the backend logs for connection errors

### "Unknown action" error

This means the backend received a command that isn't recognized. Verify:

- The Max for Live device is properly wired
- The backend is up to date with the latest LOM tool implementations
- The agent query is valid

## File Structure

```
ableton/
├── SONIQWERK_bridge.js      # Node.js WebSocket client and LOM interface
├── package.json             # npm dependencies
├── README.md                # This file
└── [optional] SONIQWERK.amxd  # Pre-built Max for Live device (if included)
```

## Next Steps

- Configure your API key for backend authentication
- Test with simple queries like "What's the tempo?"
- Explore more complex agent queries involving track data, devices, and clips
- Integrate the device into your production workflow

## Support

For issues or questions:

1. Check the Max console for error messages
2. Verify backend connectivity on port 8001
3. Ensure all dependencies are installed (`npm install`, Python venv activated)
4. Review the backend logs for detailed error information
