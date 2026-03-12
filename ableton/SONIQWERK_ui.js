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
