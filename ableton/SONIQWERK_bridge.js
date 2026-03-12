// SONIQWERK_bridge.js — Max for Live WebSocket bridge
// Compatible with Ableton Live 11 and Live 12
// Install: place in Max search path, add node.script to M4L device

const maxApi = require("max-api");
const WebSocket = require("ws");

const BACKEND_URL = "ws://localhost:8001/ws";
const RECONNECT_DELAY_MS = 3000;

let ws = null;
let pendingRequests = {};

function connect() {
    ws = new WebSocket(BACKEND_URL);

    ws.on("open", () => {
        maxApi.post("SONIQWERK: Connected to backend");
    });

    ws.on("message", (data) => {
        let msg;
        try {
            msg = JSON.parse(data);
        } catch (e) {
            maxApi.post("SONIQWERK: Invalid JSON received: " + e.message);
            return;
        }
        handleCommand(msg);
    });

    ws.on("close", () => {
        maxApi.post("SONIQWERK: Disconnected. Reconnecting in 3s...");
        setTimeout(connect, RECONNECT_DELAY_MS);
    });

    ws.on("error", (err) => {
        maxApi.post("SONIQWERK: WebSocket error: " + err.message);
    });
}

function sendResult(id, result) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ id, result }));
    }
}

function sendError(id, error) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ id, error: String(error) }));
    }
}

// Register a pending request and handle the LOM response
function registerPending(id, resolve, reject) {
    pendingRequests[id] = { resolve, reject };
    // Auto-cleanup after 10s to avoid leaks
    setTimeout(() => {
        if (pendingRequests[id]) {
            delete pendingRequests[id];
            reject(new Error("LOM query timeout"));
        }
    }, 10000);
}

// Max inlet handler — receives LOM query responses from Max patch
maxApi.addHandler("lom_response", (requestId, ...values) => {
    const pending = pendingRequests[requestId];
    if (pending) {
        delete pendingRequests[requestId];
        pending.resolve(values);
    }
});

maxApi.addHandler("lom_error", (requestId, errorMsg) => {
    const pending = pendingRequests[requestId];
    if (pending) {
        delete pendingRequests[requestId];
        pending.reject(new Error(errorMsg));
    }
});

// Send a LiveAPI query via Max outlet and await response
function queryLom(requestId, path, property) {
    return new Promise((resolve, reject) => {
        registerPending(requestId, resolve, reject);
        // outlet 0: path, outlet 1: property, outlet 2: requestId (for correlation)
        maxApi.outlet(0, "query", path, property, requestId);
    });
}

function setLom(requestId, path, property, value) {
    return new Promise((resolve, reject) => {
        registerPending(requestId, resolve, reject);
        maxApi.outlet(0, "set", path, property, value, requestId);
    });
}

function callLom(requestId, path, method) {
    return new Promise((resolve, reject) => {
        registerPending(requestId, resolve, reject);
        maxApi.outlet(0, "call", path, method, requestId);
    });
}

async function handleCommand(msg) {
    const { action, params, id } = msg;

    try {
        let result;

        if (action === "get_session_info") {
            const tempo = await queryLom(id + "_tempo", "live_set", "tempo");
            result = { tempo: tempo[0] };

        } else if (action === "get_tracks") {
            const count = await queryLom(id + "_count", "live_set tracks", "length");
            const tracks = [];
            for (let i = 0; i < count[0]; i++) {
                const name = await queryLom(id + "_name_" + i, `live_set tracks ${i}`, "name");
                tracks.push({ index: i, name: name[0] });
            }
            result = { tracks };

        } else if (action === "get_track_devices") {
            const { track_index } = params;
            const count = await queryLom(id + "_dc", `live_set tracks ${track_index} devices`, "length");
            const devices = [];
            for (let i = 0; i < count[0]; i++) {
                const name = await queryLom(id + "_dn_" + i, `live_set tracks ${track_index} devices ${i}`, "name");
                devices.push({ index: i, name: name[0] });
            }
            result = { devices };

        } else if (action === "set_parameter") {
            const { track_index, device_index, param_index, value } = params;
            await setLom(id, `live_set tracks ${track_index} devices ${device_index} parameters ${param_index}`, "value", value);
            result = { success: true };

        } else if (action === "get_clips") {
            const { track_index } = params;
            const count = await queryLom(id + "_cc", `live_set tracks ${track_index} clip_slots`, "length");
            const clips = [];
            for (let i = 0; i < count[0]; i++) {
                const hasClip = await queryLom(id + "_hc_" + i, `live_set tracks ${track_index} clip_slots ${i}`, "has_clip");
                if (hasClip[0]) {
                    const name = await queryLom(id + "_cn_" + i, `live_set tracks ${track_index} clip_slots ${i} clip`, "name");
                    clips.push({ slot_index: i, name: name[0] });
                }
            }
            result = { clips };

        } else if (action === "fire_clip") {
            const { track_index, slot_index } = params;
            await callLom(id, `live_set tracks ${track_index} clip_slots ${slot_index} clip`, "fire");
            result = { success: true };

        } else {
            sendError(id, `Unknown action: ${action}`);
            return;
        }

        sendResult(id, result);

    } catch (err) {
        sendError(id, err.message);
    }
}

// Start connection
connect();
maxApi.post("SONIQWERK bridge loaded. Connecting to " + BACKEND_URL);
