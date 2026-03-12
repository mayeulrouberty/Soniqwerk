// SONIQWERK_bridge.js — Max for Live WebSocket bridge
// Compatible with Ableton Live 11 and Live 12
// Install: place in Max search path, add node.script to M4L device

const maxApi = require("max-api");
const WebSocket = require("ws");

const BACKEND_URL = "ws://localhost:8001/ws";
const RECONNECT_DELAY_MS = 3000;

// Instrument name → Live browser path mapping (Live 11 + Live 12 compatible)
const INSTRUMENT_PATHS = {
    "drift":      "Instruments/Drift/Drift.adv",
    "operator":   "Instruments/Operator/Operator.adv",
    "wavetable":  "Instruments/Wavetable/Wavetable.adv",
    "simpler":    "Instruments/Simpler/Simpler.adv",
    "sampler":    "Instruments/Sampler/Sampler.adv",
    "drum rack":  "Instruments/Drum Rack/Drum Rack.adv",
};

const EFFECT_PATHS = {
    "reverb":      "Audio Effects/Reverb/Reverb.adv",
    "delay":       "Audio Effects/Delay/Delay.adv",
    "compressor":  "Audio Effects/Compressor/Compressor.adv",
    "eq eight":    "Audio Effects/EQ Eight/EQ Eight.adv",
    "eq3":         "Audio Effects/EQ Three/EQ Three.adv",
    "auto filter": "Audio Effects/Auto Filter/Auto Filter.adv",
    "saturator":   "Audio Effects/Saturator/Saturator.adv",
    "chorus":      "Audio Effects/Chorus-Ensemble/Chorus-Ensemble.adv",
    "phaser":      "Audio Effects/Phaser-Flanger/Phaser-Flanger.adv",
    "redux":       "Audio Effects/Redux/Redux.adv",
    "limiter":     "Audio Effects/Limiter/Limiter.adv",
};

const COLOR_MAP = {
    "red": 14368691, "orange": 15631116, "yellow": 14785536,
    "green": 5537095, "blue": 4473924, "purple": 8756399,
    "pink": 12450367, "white": 16579836, "": 0,
};

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

        } else if (action === "set_session") {
            const { bpm, time_signature, name } = params;
            if (bpm) await setLom(id + "_bpm", "live_set", "tempo", bpm);
            if (time_signature) {
                const [num, den] = time_signature.split("/").map(Number);
                await setLom(id + "_num", "live_set", "signature_numerator", num);
                await setLom(id + "_den", "live_set", "signature_denominator", den);
            }
            if (name) await setLom(id + "_name", "live_set", "name", name);
            result = { success: true };

        } else if (action === "create_instrument_track") {
            const { name, instrument, color } = params;
            await callLom(id + "_ct", "live_set", "create_midi_track -1");
            const trackIdx = await queryLom(id + "_tidx", "live_set tracks", "length");
            const idx = trackIdx[0] - 1;
            await setLom(id + "_tname", `live_set tracks ${idx}`, "name", name);
            const instrKey = (instrument || "").toLowerCase();
            const instrPath = INSTRUMENT_PATHS[instrKey];
            if (instrPath) {
                await callLom(id + "_ld", `live_set tracks ${idx}`, `load_device "${instrPath}"`);
            }
            if (color && COLOR_MAP[color.toLowerCase()] !== undefined) {
                await setLom(id + "_col", `live_set tracks ${idx}`, "color", COLOR_MAP[color.toLowerCase()]);
            }
            result = { track_index: idx };

        } else if (action === "create_audio_track") {
            const { name, color } = params;
            await callLom(id + "_cat", "live_set", "create_audio_track -1");
            const trackIdx = await queryLom(id + "_atidx", "live_set tracks", "length");
            const idx = trackIdx[0] - 1;
            await setLom(id + "_atname", `live_set tracks ${idx}`, "name", name);
            result = { track_index: idx };

        } else if (action === "delete_track") {
            const { track_index } = params;
            await callLom(id, `live_set tracks ${track_index}`, "delete");
            result = { success: true };

        } else if (action === "set_track_mix") {
            const { track_index, volume, pan, mute } = params;
            if (volume !== undefined)
                await setLom(id + "_vol", `live_set tracks ${track_index} mixer_device volume`, "value", volume);
            if (pan !== undefined)
                await setLom(id + "_pan", `live_set tracks ${track_index} mixer_device panning`, "value", pan);
            if (mute !== undefined)
                await setLom(id + "_mute", `live_set tracks ${track_index}`, "mute", mute ? 1 : 0);
            result = { success: true };

        } else if (action === "create_midi_clip") {
            const { track_index, slot_index, length_bars } = params;
            const lengthBeats = (length_bars || 2) * 4;
            await callLom(id, `live_set tracks ${track_index} clip_slots ${slot_index}`, `create_clip ${lengthBeats}`);
            result = { success: true };

        } else if (action === "write_notes") {
            const { track_index, slot_index, notes } = params;
            const dictName = "soniqwerk_notes_" + id;
            const noteDicts = notes.map(n => ({
                pitch: n.pitch,
                start_time: n.time,
                duration: n.duration,
                velocity: n.velocity,
                mute: n.mute ? 1 : 0,
                probability: 1.0,
                velocity_deviation: 0,
                release_velocity: 64,
            }));
            await maxApi.setDict(dictName, { notes: noteDicts });
            await callLom(id, `live_set tracks ${track_index} clip_slots ${slot_index} clip`,
                `set_notes_extended ${dictName}`);
            result = { success: true, count: notes.length };

        } else if (action === "set_clip_name") {
            const { track_index, slot_index, name } = params;
            await setLom(id, `live_set tracks ${track_index} clip_slots ${slot_index} clip`, "name", name);
            result = { success: true };

        } else if (action === "load_effect") {
            const { track_index, effect_name, position } = params;
            const key = (effect_name || "").toLowerCase();
            const path = EFFECT_PATHS[key];
            if (!path) {
                sendError(id, `Unknown effect: ${effect_name}. Available: ${Object.keys(EFFECT_PATHS).join(", ")}`);
                return;
            }
            await callLom(id, `live_set tracks ${track_index}`, `load_device "${path}"`);
            result = { success: true };

        } else if (action === "create_scene") {
            const { name, scene_index } = params;
            await callLom(id + "_cs", "live_set", `create_scene ${scene_index !== undefined ? scene_index : -1}`);
            const sceneCount = await queryLom(id + "_sc", "live_set scenes", "length");
            const idx = sceneCount[0] - 1;
            await setLom(id + "_sn", `live_set scenes ${idx}`, "name", name);
            result = { scene_index: idx };

        } else if (action === "load_sample") {
            const { track_index, sample_path } = params;
            await callLom(id, `live_set tracks ${track_index} devices 0`,
                `load_sample "${sample_path}"`);
            result = { success: true };

        } else if (action === "get_device_parameters") {
            const { track_index, device_index } = params;
            const devicePath = `live_set tracks ${track_index} devices ${device_index}`;
            const paramCountRes = await queryLom(id + "_pc", devicePath + " parameters", "length");
            const count = parseInt(paramCountRes[0]) || 0;
            const paramList = [];
            for (let i = 0; i < count; i++) {
                const paramPath = `${devicePath} parameters ${i}`;
                const nameRes  = await queryLom(id + `_pn${i}`, paramPath, "name");
                const valRes   = await queryLom(id + `_pv${i}`, paramPath, "value");
                const minRes   = await queryLom(id + `_pm${i}`, paramPath, "min");
                const maxRes   = await queryLom(id + `_px${i}`, paramPath, "max");
                paramList.push({
                    index: i,
                    name:  nameRes[0],
                    value: valRes[0],
                    min:   minRes[0],
                    max:   maxRes[0],
                });
            }
            result = { params: paramList };

        } else if (action === "write_automation") {
            const { track_index, device_index, param_index, points } = params;
            const dictName = "soniqwerk_auto_" + id;
            await maxApi.setDict(dictName, { automation_points: points });
            await callLom(id, `live_set tracks ${track_index} devices ${device_index} parameters ${param_index}`,
                `set_automation_points ${dictName}`);
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
