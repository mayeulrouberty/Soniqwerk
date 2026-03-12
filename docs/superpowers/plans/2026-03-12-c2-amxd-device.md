# C2 — Native .amxd Device Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a self-contained Max for Live device (`SONIQWERK.amxd`) with a scrollable chat history + text input, so the user can control the Soniqwerk agent directly from inside Ableton — no browser needed.

**Architecture:** Three files in `ableton/`: the `.amxd` patch JSON (Max 8 format), a `jsui` JavaScript renderer (`SONIQWERK_ui.js`), and an extension to `SONIQWERK_bridge.js` that adds an HTTP client for agent queries. No backend changes needed.

**Tech Stack:** Max for Live 8 (Live 11/12), Max `mgraphics` API, Node.js `http` module (built-in to max-api)

---

## Chunk 1: Bridge extension

### Task 1: Extend `SONIQWERK_bridge.js` with `agent_query` HTTP handler

**Files:**
- Modify: `ableton/SONIQWERK_bridge.js`

No automated tests — requires Ableton Live + Max for Live.

- [ ] **Step 1: Read `ableton/SONIQWERK_bridge.js` to understand the structure**

Key things to find:
- Where `maxApi` is imported
- Where existing `maxApi.addHandler` calls are (if any)
- The end of the file

- [ ] **Step 2: Add `sendAgentQuery` function**

Add this function near the top of the file, after the existing `require` statements and constants:

```javascript
// ── Agent HTTP client ────────────────────────────────────────────────────────

/**
 * POST a natural language query to the Soniqwerk backend /v1/agent endpoint.
 * Parses the SSE stream and returns the final answer text.
 * @param {string} text - The user's query
 * @param {string} backendUrl - e.g. "localhost:8000"
 * @param {string} apiKey - X-API-Key header value
 * @returns {Promise<string>} - The agent's final answer
 */
function sendAgentQuery(text, backendUrl, apiKey) {
    return new Promise(function(resolve, reject) {
        const parts = (backendUrl || "localhost:8000").split(":");
        const hostname = parts[0] || "localhost";
        const port = parts[1] ? parseInt(parts[1]) : 8000;
        const body = JSON.stringify({ query: text });
        const http = require("http");

        const options = {
            hostname: hostname,
            port: port,
            path: "/v1/agent",
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": apiKey || "test",
                "Content-Length": Buffer.byteLength(body),
            },
        };

        let finalAnswer = "";
        const req = http.request(options, function(res) {
            res.setEncoding("utf8");
            res.on("data", function(chunk) {
                chunk.split("\n").forEach(function(line) {
                    const trimmed = line.trim();
                    if (trimmed.startsWith("data: ")) {
                        try {
                            const data = JSON.parse(trimmed.slice(6));
                            if (data.type === "done" && data.content) {
                                finalAnswer = data.content;
                            }
                        } catch (e) {}
                    }
                });
            });
            res.on("end", function() {
                resolve(finalAnswer || "Pas de réponse reçue.");
            });
        });

        req.on("error", function(err) {
            reject(err);
        });

        req.setTimeout(60000, function() {
            req.destroy();
            reject(new Error("Timeout: agent did not respond within 60s"));
        });

        req.write(body);
        req.end();
    });
}
```

- [ ] **Step 3: Add `maxApi.addHandler` for `agent_query`**

At the end of the file, add:

```javascript
// ── Max message handler for jsui agent queries ───────────────────────────────

maxApi.addHandler("agent_query", async function(text, backendUrl, apiKey) {
    try {
        maxApi.outlet(0, "connecting");
        const response = await sendAgentQuery(text, backendUrl, apiKey);
        maxApi.outlet(0, "agent_response", response);
        maxApi.outlet(0, "connected", 1);
    } catch (err) {
        maxApi.outlet(0, "agent_error", err.message || String(err));
        maxApi.outlet(0, "connected", 0);
    }
});
```

**Important:** In Max node.script, `maxApi.outlet(0, "agent_response", text)` sends a Max list message `[agent_response, text]` to the patch outlet. The jsui receives this via its `list()` function.

- [ ] **Step 4: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add ableton/SONIQWERK_bridge.js
git commit -m "feat(bridge): add agent_query HTTP handler for .amxd device UI"
```

---

## Chunk 2: jsui renderer

### Task 2: Create `SONIQWERK_ui.js` (jsui canvas UI)

**Files:**
- Create: `ableton/SONIQWERK_ui.js`

No automated tests — manual testing in Max for Live.

- [ ] **Step 1: Create `ableton/SONIQWERK_ui.js`**

```javascript
// SONIQWERK_ui.js — Max for Live jsui interface
// Uses Max mgraphics API (not browser Canvas)
// Renders: status bar + scrollable chat history + text input

autowatch = 1;
outlets = 1;
inlets = 1;

// ── Layout ───────────────────────────────────────────────────────────────────
var W = 800;
var H = 240;
var TOP_H = 32;
var INPUT_H = 48;
var HISTORY_H = H - TOP_H - INPUT_H;

// ── State ────────────────────────────────────────────────────────────────────
var history = [];        // [{role: "user"|"agent", text: "..."}]
var inputBuffer = "";
var scrollY = 0;
var statusLevel = 0;     // 0=disconnected 1=connecting 2=connected
var backendUrl = "localhost:8000";
var apiKey = "test";
var editingUrl = false;
var editingKey = false;
var urlEditBuf = "";
var keyEditBuf = "";

// ── Colors (0..1 floats) ─────────────────────────────────────────────────────
function c(r, g, b) { return [r / 255, g / 255, b / 255, 1]; }
var C_BG     = c(26,  26,  26);
var C_BAR    = c(18,  18,  18);
var C_INPUT  = c(20,  20,  20);
var C_TEXT   = c(220, 220, 220);
var C_DIM    = c(120, 120, 120);
var C_USER   = c(126, 200, 227);
var C_AGENT  = c(168, 230, 163);
var C_BORDER = c(50,  50,  50);
var C_RED    = c(244, 67,  54);
var C_ORANGE = c(255, 152, 0);
var C_GREEN  = c(76,  175, 80);

function setColor(g, col) {
    g.set_source_rgba(col[0], col[1], col[2], col[3]);
}

// ── Paint ────────────────────────────────────────────────────────────────────
function paint() {
    var g = mgraphics;
    g.init();
    g.identity_matrix();

    // Background
    setColor(g, C_BG);
    g.rectangle(0, 0, W, H);
    g.fill();

    drawTopBar(g);
    drawHistory(g);
    drawInput(g);
}

function drawTopBar(g) {
    setColor(g, C_BAR);
    g.rectangle(0, 0, W, TOP_H);
    g.fill();

    setColor(g, C_BORDER);
    g.move_to(0, TOP_H - 1);
    g.line_to(W, TOP_H - 1);
    g.set_line_width(1);
    g.stroke();

    // Status dot
    var dotCol = statusLevel === 2 ? C_GREEN : (statusLevel === 1 ? C_ORANGE : C_RED);
    setColor(g, dotCol);
    g.arc(14, 16, 5, 0, 6.2832);
    g.fill();

    // Title
    setColor(g, C_TEXT);
    g.select_font_face("Arial");
    g.set_font_size(12);
    g.move_to(26, 21);
    g.text_path("SONIQWERK");
    g.fill();

    // Status label
    var statusLabel = ["disconnected", "connecting...", "connected"][statusLevel];
    setColor(g, C_DIM);
    g.set_font_size(10);
    g.move_to(108, 20);
    g.text_path(statusLabel);
    g.fill();

    // URL field
    setColor(g, editingUrl ? C_TEXT : C_DIM);
    g.set_font_size(10);
    var urlDisplay = editingUrl ? (urlEditBuf + "|") : backendUrl;
    g.move_to(W - 270, 20);
    g.text_path("http://" + urlDisplay);
    g.fill();

    // API key field
    setColor(g, editingKey ? C_TEXT : C_DIM);
    var keyDisplay = editingKey ? (keyEditBuf + "|") : apiKey;
    g.move_to(W - 80, 20);
    g.text_path("key:" + keyDisplay);
    g.fill();
}

function drawHistory(g) {
    setColor(g, C_BG);
    g.rectangle(0, TOP_H, W, HISTORY_H);
    g.fill();

    // Clip to history area
    g.rectangle(0, TOP_H, W, HISTORY_H);
    g.clip();

    var x = 14;
    var lineH = 18;
    var y = TOP_H + 12 - scrollY;

    g.select_font_face("Arial");
    g.set_font_size(11);

    for (var i = 0; i < history.length; i++) {
        var entry = history[i];
        var isUser = entry.role === "user";
        var label = isUser ? "Toi" : "Agent";
        var labelCol = isUser ? C_USER : C_AGENT;
        var labelW = isUser ? 30 : 40;

        setColor(g, labelCol);
        g.move_to(x, y + 13);
        g.text_path(label + " :");
        g.fill();

        setColor(g, C_TEXT);
        var words = entry.text.split(" ");
        var line = "";
        var maxW = W - x - labelW - 20;
        var firstLine = true;

        for (var w = 0; w < words.length; w++) {
            var test = line ? (line + " " + words[w]) : words[w];
            if (test.length * 5.8 > maxW && line) {
                var lx = firstLine ? x + labelW : x + 8;
                g.move_to(lx, y + 13);
                g.text_path(line);
                g.fill();
                y += lineH;
                line = words[w];
                firstLine = false;
            } else {
                line = test;
            }
        }
        if (line) {
            var lx2 = firstLine ? x + labelW : x + 8;
            g.move_to(lx2, y + 13);
            g.text_path(line);
            g.fill();
        }
        y += lineH + 6;
    }

    g.reset_clip();
}

function drawInput(g) {
    var y0 = TOP_H + HISTORY_H;

    setColor(g, C_BORDER);
    g.move_to(0, y0);
    g.line_to(W, y0);
    g.set_line_width(1);
    g.stroke();

    setColor(g, C_INPUT);
    g.rectangle(0, y0, W, INPUT_H);
    g.fill();

    setColor(g, C_DIM);
    g.select_font_face("Arial");
    g.set_font_size(12);
    g.move_to(14, y0 + 30);
    g.text_path(">");
    g.fill();

    if (inputBuffer.length > 0) {
        setColor(g, C_TEXT);
        g.move_to(28, y0 + 30);
        g.text_path(inputBuffer + "|");
        g.fill();
    } else {
        setColor(g, C_DIM);
        g.set_font_size(10);
        g.move_to(28, y0 + 30);
        g.text_path("Tapez une commande et appuyez sur Entrée...");
        g.fill();
    }
}

// ── Keyboard ─────────────────────────────────────────────────────────────────
function key(k, shift, capslock, option, ctrl) {
    if (editingUrl || editingKey) {
        handleFieldKey(k);
        return;
    }

    if (k === 13) { // Enter
        var text = inputBuffer.trim();
        if (text.length > 0) {
            history.push({ role: "user", text: text });
            outlet(0, "agent_query", text, backendUrl, apiKey);
            statusLevel = 1;
            inputBuffer = "";
            scrollToBottom();
        }
    } else if (k === 8) { // Backspace
        inputBuffer = inputBuffer.slice(0, -1);
    } else if (k >= 32 && k < 127) {
        inputBuffer += String.fromCharCode(k);
    }
    refresh();
}

function handleFieldKey(k) {
    var isUrl = editingUrl;
    var buf = isUrl ? urlEditBuf : keyEditBuf;

    if (k === 13 || k === 27) { // Enter or Escape
        if (k === 13) {
            if (isUrl) { backendUrl = buf || backendUrl; }
            else { apiKey = buf || apiKey; }
        }
        editingUrl = false;
        editingKey = false;
    } else if (k === 8) {
        buf = buf.slice(0, -1);
        if (isUrl) urlEditBuf = buf; else keyEditBuf = buf;
    } else if (k >= 32 && k < 127) {
        buf += String.fromCharCode(k);
        if (isUrl) urlEditBuf = buf; else keyEditBuf = buf;
    }
    refresh();
}

function onclick(x, y, btn, cmd, shift, capslock, option, ctrl) {
    if (y < TOP_H) {
        if (x > W - 270 && x < W - 90) {
            editingUrl = true; editingKey = false; urlEditBuf = backendUrl;
        } else if (x > W - 90) {
            editingKey = true; editingUrl = false; keyEditBuf = apiKey;
        } else {
            editingUrl = false; editingKey = false;
        }
        refresh();
    }
}

function onidlescroll(x, y, dx, dy, modifiers) {
    scrollY = Math.max(0, scrollY - dy * 20);
    refresh();
}

// ── Receive from node.script ─────────────────────────────────────────────────
function list() {
    var args = arrayfromargs(arguments);
    var cmd = args[0];

    if (cmd === "agent_response") {
        var text = args.slice(1).join(" ");
        history.push({ role: "agent", text: text });
        scrollToBottom();
        statusLevel = 2;
        refresh();
    } else if (cmd === "agent_error") {
        var err = args.slice(1).join(" ");
        history.push({ role: "agent", text: "Erreur : " + err });
        scrollToBottom();
        statusLevel = 0;
        refresh();
    } else if (cmd === "connected") {
        statusLevel = args[1] ? 2 : 0;
        refresh();
    } else if (cmd === "connecting") {
        statusLevel = 1;
        refresh();
    }
}

function scrollToBottom() {
    var lineH = 18;
    var total = 0;
    for (var i = 0; i < history.length; i++) {
        var lines = Math.ceil(history[i].text.length / 80) + 1;
        total += lines * lineH + 6;
    }
    scrollY = Math.max(0, total - HISTORY_H + 30);
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add ableton/SONIQWERK_ui.js
git commit -m "feat(ableton): add SONIQWERK_ui.js — jsui canvas chat interface"
```

---

## Chunk 3: .amxd device file

### Task 3: Create `SONIQWERK.amxd` (Max patch JSON)

**Files:**
- Create: `ableton/SONIQWERK.amxd`

- [ ] **Step 1: Create `ableton/SONIQWERK.amxd`**

This is a Max 8 patch JSON file. `classnamespace: "midi.effect"` makes it a MIDI Effect device that can be placed on any track.

```json
{
	"patcher" : 	{
		"fileversion" : 1,
		"appversion" : 		{
			"major" : 8,
			"minor" : 6,
			"revision" : 2,
			"architecture" : "x64",
			"modernui" : 1
		},
		"classnamespace" : "midi.effect",
		"rect" : [ 100.0, 100.0, 900.0, 400.0 ],
		"bglocked" : 0,
		"openrect" : [ 0.0, 0.0, 0.0, 0.0 ],
		"openinpresentation" : 1,
		"default_fontsize" : 12.0,
		"default_fontface" : 0,
		"default_fontname" : "Arial",
		"gridonopen" : 1,
		"gridsize" : [ 15.0, 15.0 ],
		"gridsnaponopen" : 1,
		"objectsnaponopen" : 1,
		"statusbarvisible" : 2,
		"toolbarvisible" : 1,
		"lefttoolbarpinned" : 0,
		"toptoolbarpinned" : 0,
		"righttoolbarpinned" : 0,
		"bottomtoolbarpinned" : 0,
		"devicewidth" : 800.0,
		"deviceheight" : 240.0,
		"description" : "SONIQWERK — AI Music Production Assistant",
		"digest" : "",
		"tags" : "SONIQWERK AI Ableton",
		"style" : "",
		"subpatcher_template" : "",
		"boxes" : [ 			{
				"box" : 				{
					"id" : "obj-1",
					"maxclass" : "newobj",
					"text" : "node.script SONIQWERK_bridge.js",
					"numinlets" : 1,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 20.0, 20.0, 230.0, 22.0 ]
				}
			},
			{
				"box" : 				{
					"id" : "obj-2",
					"maxclass" : "jsui",
					"numinlets" : 1,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 20.0, 60.0, 800.0, 240.0 ],
					"presentation" : 1,
					"presentation_rect" : [ 0.0, 0.0, 800.0, 240.0 ],
					"file" : "SONIQWERK_ui.js"
				}
			}
		],
		"lines" : [ 			{
				"patchline" : 				{
					"source" : [ "obj-2", 0 ],
					"destination" : [ "obj-1", 0 ],
					"midpoints" : [  ]
				}
			},
			{
				"patchline" : 				{
					"source" : [ "obj-1", 0 ],
					"destination" : [ "obj-2", 0 ],
					"midpoints" : [  ]
				}
			}
		],
		"dependency_cache" : [ 			{
				"name" : "SONIQWERK_bridge.js",
				"bootpath" : ".",
				"type" : "TEXT",
				"implicit" : 1
			},
			{
				"name" : "SONIQWERK_ui.js",
				"bootpath" : ".",
				"type" : "TEXT",
				"implicit" : 1
			}
		]
	}
}
```

- [ ] **Step 2: Commit and push**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add ableton/SONIQWERK.amxd
git commit -m "feat(ableton): add SONIQWERK.amxd — native Max for Live device"
git push public phase-3-ableton:main
```

---

## Installation Instructions (for `ableton/README.md`)

Add to `ableton/README.md`:

```markdown
## SONIQWERK Device (C2)

The `SONIQWERK.amxd` device lets you control the AI agent directly inside Ableton.

### Install

1. Start the Soniqwerk backend: `./run.sh`
2. In Ableton Live, drag `ableton/SONIQWERK.amxd` onto any track
3. The device opens in the device panel (800×240px)
4. The status dot turns green when connected to the backend
5. Type a command and press Enter

### Requirements

- Ableton Live 11 or 12 with Max for Live
- Soniqwerk backend running on `localhost:8000`
- All three files must be in the same folder: `SONIQWERK.amxd`, `SONIQWERK_bridge.js`, `SONIQWERK_ui.js`
```

- [ ] **Step 3: Update `ableton/README.md` and commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add ableton/README.md
git commit -m "docs(ableton): add SONIQWERK.amxd installation instructions"
git push public phase-3-ableton:main
```
