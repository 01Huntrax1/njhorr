// AMORPH_CONTEXT_ID: amorph-ui-instrument-5b48a73f78f51616
// AMORPH_END_TOKEN: amorph-end-b49e7ca324b0857f
// WINDOW SIZE: 1180x760
class SliderControl {
    constructor ({ pc, spec, node, onChange }) {
        this.pc = pc; this.param = spec.id; this.spec = spec; this.node = node;
        this.min = spec.min; this.max = spec.max > spec.min ? spec.max : spec.min + 1;
        this.def = spec.init; this.value = spec.init; this.onChange = onChange;
        this.track = node.querySelector(".track");
        this.fill = node.querySelector(".fill");
        this.thumb = node.querySelector(".thumb");
        this.valEl = node.querySelector(".val");
        this.dragging = false; this.pid = null;
        this.track.addEventListener("pointerdown", e => this.down(e));
        this.track.addEventListener("pointermove", e => this.move(e));
        this.track.addEventListener("pointerup", e => this.up(e));
        this.track.addEventListener("pointercancel", e => this.up(e));
        this.track.addEventListener("lostpointercapture", () => { this.dragging = false; node.classList.remove("drag"); });
        this.track.addEventListener("dblclick", () => this.setValue(this.def, true));
        this.setValue(this.def, false);
    }
    setValue (v, notify) {
        v = Number.isFinite(v) ? v : this.def;
        v = Math.max(this.min, Math.min(this.max, v));
        this.value = v;
        const n = (v - this.min) / (this.max - this.min || 1);
        if (this.min < 0 && this.max > 0) {
            const z = -this.min / (this.max - this.min);
            this.fill.style.left = Math.min(n, z) * 100 + "%";
            this.fill.style.width = Math.abs(n - z) * 100 + "%";
        } else { this.fill.style.left = "0%"; this.fill.style.width = n * 100 + "%"; }
        this.thumb.style.left = n * 100 + "%";
        this.valEl.textContent = fmt(this.spec, v);
        if (this.onChange) this.onChange(v, notify === true);
        if (notify === true) this.pc.sendEventOrValue(this.param, v);
    }
    fromX (x) {
        const r = this.track.getBoundingClientRect();
        const n = r.width > 0 ? Math.max(0, Math.min(1, (x - r.left) / r.width)) : 0;
        return this.min + n * (this.max - this.min);
    }
    down (e) {
        this.dragging = true; this.pid = e.pointerId; this.node.classList.add("drag");
        try { this.track.setPointerCapture(e.pointerId); } catch (_) {}
        e.preventDefault();
        this.setValue(this.fromX(e.clientX), true);
    }
    move (e) {
        if (!this.dragging || e.pointerId !== this.pid) return;
        e.preventDefault();
        this.setValue(this.fromX(e.clientX), true);
    }
    up (e) {
        if (!this.dragging) return;
        this.dragging = false; this.node.classList.remove("drag");
        try { this.track.releasePointerCapture(e.pointerId); } catch (_) {}
    }
}

// rotary knob: vertical drag, Shift = fine, double-click resets; Hz parameters use a log taper
class KnobControl {
    constructor ({ pc, spec, node, onChange }) {
        this.pc = pc; this.param = spec.id; this.spec = spec; this.node = node;
        this.min = spec.min; this.max = spec.max > spec.min ? spec.max : spec.min + 1;
        this.def = spec.init; this.value = spec.init; this.onChange = onChange;
        this.log = spec.unit === "Hz" && this.min > 0;
        this.knob = node.querySelector(".knob");
        this.rot = node.querySelector(".kin");
        this.valEl = node.querySelector(".val");
        this.dragging = false; this.pid = null; this.startY = 0; this.startN = 0;
        this.knob.addEventListener("pointerdown", e => this.down(e));
        this.knob.addEventListener("pointermove", e => this.move(e));
        this.knob.addEventListener("pointerup", e => this.up(e));
        this.knob.addEventListener("pointercancel", e => this.up(e));
        this.knob.addEventListener("lostpointercapture", () => { this.dragging = false; node.classList.remove("drag"); });
        this.knob.addEventListener("dblclick", () => this.setValue(this.def, true));
        this.setValue(this.def, false);
    }
    toNorm (v) {
        if (this.log) return Math.log(Math.max(v, this.min) / this.min) / Math.log(this.max / this.min);
        return (v - this.min) / (this.max - this.min || 1);
    }
    fromNorm (n) {
        n = Math.max(0, Math.min(1, n));
        if (this.log) return this.min * Math.pow(this.max / this.min, n);
        return this.min + n * (this.max - this.min);
    }
    setValue (v, notify) {
        v = Number.isFinite(v) ? v : this.def;
        v = Math.max(this.min, Math.min(this.max, v));
        this.value = v;
        const n = this.toNorm(v);
        this.rot.style.transform = "rotate(" + (-135 + n * 270).toFixed(1) + "deg)";
        this.valEl.textContent = fmt(this.spec, v);
        this.knob.title = (this.spec.label || "") + ": " + fmt(this.spec, v);
        if (this.onChange) this.onChange(v, notify === true);
        if (notify === true) this.pc.sendEventOrValue(this.param, v);
    }
    down (e) {
        this.dragging = true; this.pid = e.pointerId; this.startY = e.clientY; this.startN = this.toNorm(this.value);
        this.node.classList.add("drag");
        try { this.knob.setPointerCapture(e.pointerId); } catch (_) {}
        e.preventDefault();
    }
    move (e) {
        if (!this.dragging || e.pointerId !== this.pid) return;
        e.preventDefault();
        const sens = e.shiftKey ? 0.0012 : 0.006;
        this.setValue(this.fromNorm(this.startN + (this.startY - e.clientY) * sens), true);
    }
    up (e) {
        if (!this.dragging) return;
        this.dragging = false; this.node.classList.remove("drag");
        try { this.knob.releasePointerCapture(e.pointerId); } catch (_) {}
    }
}

class FaderControl {
    constructor ({ pc, spec, node, onChange }) {
        this.pc = pc; this.param = spec.id; this.spec = spec; this.node = node;
        this.min = spec.min; this.max = spec.max > spec.min ? spec.max : spec.min + 1;
        this.def = spec.init; this.value = spec.init; this.onChange = onChange;
        this.track = node.querySelector(".ftrack");
        this.fill = node.querySelector(".ffill");
        this.thumb = node.querySelector(".fthumb");
        this.valEl = node.querySelector(".val");
        this.dragging = false; this.pid = null;
        this.track.addEventListener("pointerdown", e => this.down(e));
        this.track.addEventListener("pointermove", e => this.move(e));
        this.track.addEventListener("pointerup", e => this.up(e));
        this.track.addEventListener("pointercancel", e => this.up(e));
        this.track.addEventListener("lostpointercapture", () => { this.dragging = false; node.classList.remove("drag"); });
        this.track.addEventListener("dblclick", () => this.setValue(this.def, true));
        this.setValue(this.def, false);
    }
    setValue (v, notify) {
        v = Number.isFinite(v) ? v : this.def;
        v = Math.max(this.min, Math.min(this.max, v));
        this.value = v;
        const n = (v - this.min) / (this.max - this.min || 1);
        if (this.min < 0 && this.max > 0) {
            const z = -this.min / (this.max - this.min);
            this.fill.style.bottom = Math.min(n, z) * 100 + "%";
            this.fill.style.height = Math.abs(n - z) * 100 + "%";
        } else { this.fill.style.bottom = "0%"; this.fill.style.height = n * 100 + "%"; }
        this.thumb.style.bottom = n * 100 + "%";
        this.valEl.textContent = fmt(this.spec, v);
        if (this.onChange) this.onChange(v, notify === true);
        if (notify === true) this.pc.sendEventOrValue(this.param, v);
    }
    fromY (y) {
        const r = this.track.getBoundingClientRect();
        const n = r.height > 0 ? Math.max(0, Math.min(1, 1 - (y - r.top) / r.height)) : 0;
        return this.min + n * (this.max - this.min);
    }
    down (e) {
        this.dragging = true; this.pid = e.pointerId; this.node.classList.add("drag");
        try { this.track.setPointerCapture(e.pointerId); } catch (_) {}
        e.preventDefault();
        this.setValue(this.fromY(e.clientY), true);
    }
    move (e) {
        if (!this.dragging || e.pointerId !== this.pid) return;
        e.preventDefault();
        this.setValue(this.fromY(e.clientY), true);
    }
    up (e) {
        if (!this.dragging) return;
        this.dragging = false; this.node.classList.remove("drag");
        try { this.track.releasePointerCapture(e.pointerId); } catch (_) {}
    }
}

class ButtonGroupControl {
    constructor ({ pc, spec, node, onChange }) {
        this.pc = pc; this.param = spec.id; this.spec = spec;
        this.min = spec.min; this.max = spec.max; this.def = spec.init; this.value = spec.init;
        this.onChange = onChange;
        this.btns = Array.from(node.querySelectorAll("button"));
        this.valEl = node.querySelector(".val");
        this.btns.forEach((b, i) => {
            b.setAttribute("tabindex", "-1");
            b.addEventListener("click", () => { this.setValue(this.min + i, true); b.blur(); });
        });
        // buttons intentionally ignore double-click reset
        this.setValue(this.def, false);
    }
    setValue (v, notify) {
        v = Number.isFinite(v) ? v : this.def;
        v = Math.round(Math.max(this.min, Math.min(this.max, v)));
        this.value = v;
        this.btns.forEach((b, i) => b.classList.toggle("on", i === v - this.min));
        this.valEl.textContent = fmt(this.spec, v);
        if (this.onChange) this.onChange(v, notify === true);
        if (notify === true) this.pc.sendEventOrValue(this.param, v);
    }
}

class StepperControl {
    constructor ({ pc, spec, node, onChange }) {
        this.pc = pc; this.param = spec.id; this.spec = spec;
        this.min = spec.min; this.max = spec.max; this.def = spec.init; this.value = spec.init;
        this.big = spec.big || 1;
        this.onChange = onChange;
        this.valEl = node.querySelector(".val");
        this.btns = Array.from(node.querySelectorAll("button"));
        this.btns.forEach(b => {
            b.setAttribute("tabindex", "-1");
            b.addEventListener("click", e => {
                const d = parseInt(b.dataset.d, 10) || 0;
                this.setValue(this.value + d * (e.shiftKey ? this.big : 1), true);
                b.blur();
            });
        });
        // steppers (buttons) intentionally ignore double-click reset
        this.setValue(this.def, false);
    }
    setValue (v, notify) {
        v = Number.isFinite(v) ? v : this.def;
        v = Math.round(Math.max(this.min, Math.min(this.max, v)));
        this.value = v;
        this.valEl.textContent = fmt(this.spec, v);
        if (this.onChange) this.onChange(v, notify === true);
        if (notify === true) this.pc.sendEventOrValue(this.param, v);
    }
}

class SelectControl {
    constructor ({ pc, spec, node, onChange }) {
        this.pc = pc; this.param = spec.id; this.spec = spec;
        this.min = spec.min; this.max = spec.max > spec.min ? spec.max : spec.min + 1;
        this.def = spec.init; this.value = spec.init;
        this.onChange = onChange;
        this.sel = node.querySelector("select");
        this.valEl = node.querySelector(".val");
        this.sel.setAttribute("aria-label", spec.label);
        this.sel.addEventListener("change", () => this.setValue(this.min + this.sel.selectedIndex, true));
        this.sel.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === "Escape") this.sel.blur(); });
        this.setValue(this.def, false);
    }
    setValue (v, notify) {
        v = Number.isFinite(v) ? v : this.def;
        v = Math.round(Math.max(this.min, Math.min(this.max, v)));
        this.value = v;
        this.sel.selectedIndex = v - this.min;
        this.valEl.textContent = fmt(this.spec, v);
        if (this.onChange) this.onChange(v, notify === true);
        if (notify === true) this.pc.sendEventOrValue(this.param, v);
    }
}

const UNI_STYLES = ["Lin", "Exp", "Inv", "Rnd"];
const WARP_MODES = ["Off", "Bend +", "Bend \u2212", "Sync", "PWM", "Mirror", "Flip", "Quantize", "Fold"];

const FILTER_TYPES = ["LP24", "LP12", "HP12", "BP12", "LP6", "LP18", "HP6", "HP18", "HP24", "BP24", "Notch12", "Notch24",
    "Peak", "LowShelf", "HighShelf", "Allpass", "Ladder", "Diode", "Acid", "Dirty LP", "Comb+", "Comb-", "Phaser", "Vowel",
    "MG Low 6", "MG Low 12", "MG Low 18", "MG Low 24", "Flange+", "Flange-"];
const FILTER_GROUPS = [[0, "Basic"], [4, "6 / 18 dB"], [8, "24 dB / Notch"], [12, "Peak / Shelf / Allpass"], [16, "Ladder / Dirty"], [20, "Comb / Phaser / Vowel"], [24, "MG Low"], [28, "Flange"]];
// LFO sync divisions, in the order of the DSP table
const SYNC_DIVS = ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"];

const MOD_WAVES = ["Sin", "Tri", "Sqr", "S&H", "Up", "Dn", "Drawn"];
const MOD_SRC = ["Off"].concat(
    Array.from({ length: 10 }, (_, i) => "LFO " + (i + 1)),
    Array.from({ length: 10 }, (_, i) => "Env " + (i + 1)),
    ["Velocity", "Key", "Random"]
);
// ---- generated by tools/osc/gen_ui_consts.py from tools/osc/layout.py: do not edit by hand ----
const OSC_N = 6, OSC_BASE = 1000, OSC_STRIDE = 64, FM_BASE = 1400;
const OSC_K = {"type": 0, "level": 1, "pan": 2, "out": 3, "oct": 4, "semi": 5, "fine": 6, "track": 7, "phase": 8, "rphase": 9, "wpos": 10, "wsize": 11, "root": 12, "uvox": 13, "udet": 14, "ublend": 15, "uwid": 16, "ustyle": 17, "w1m": 18, "w1a": 19, "w2m": 20, "w2a": 21, "sstart": 22, "sloop": 23, "pleng": 24, "pharm": 25, "ptimb": 26, "pmorph": 27, "fon": 30, "ftype": 31, "fcut": 32, "fres": 33, "fdrv": 34, "fkey": 35, "feg": 36, "fvel": 37, "fatk": 38, "fdec": 39, "fsus": 40, "frel": 41, "dtype": 42, "ddrv": 43, "dmix": 44};
const oscId = (o, k) => OSC_BASE + OSC_STRIDE * o + (typeof k === "string" ? OSC_K[k] : k);
const fmId = (s, d) => FM_BASE + 6 * s + d;
const OSC_SRC_TYPES = ["Wavetable", "Sampler", "Plaits"];
const DIST_TYPES = ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"];
const OSC_OUTS = ["Main", "Bus 1", "Bus 2"];
const PLAITS_ENGINES = ["VA + Filter", "Phase Distortion", "6-Op FM A", "6-Op FM B", "6-Op FM C", "Wave Terrain", "String Machine", "Chiptune", "Virtual Analog", "Waveshaper", "FM", "Formant / Grain", "Additive", "Wavetable", "Chords", "Speech", "Swarm", "Filtered Noise", "Particle", "String", "Modal", "Bass Drum", "Snare Drum", "Hi-Hat"];
const PLAITS_GROUPS = [[0, "Classic"], [2, "FM"], [5, "Classic"], [10, "FM"], [11, "Classic"], [15, "Texture"], [19, "Physical"], [21, "Drums"]];
const PLAITS_PARAMS = [["Detune", "Cutoff", "Shape"], ["Detune", "Distortion", "Shape"], ["Patch", "Mod Level", "Env / Pitch"], ["Patch", "Mod Level", "Env / Pitch"], ["Patch", "Mod Level", "Env / Pitch"], ["Terrain", "Radius", "Offset"], ["Chord", "Registration", "Waveform"], ["Chord", "Pulse Width", "Arp / Env"], ["Detune", "Pulse Width", "Saw Shape"], ["Waveform", "Fold", "Asymmetry"], ["Ratio", "Mod Amount", "Feedback"], ["Formant Ratio", "Formant Freq", "Formant Shape"], ["Bumps", "Prominence", "Bump Shape"], ["Bank", "Row", "Column"], ["Chord", "Inversion", "Waveform"], ["Species", "Phoneme", "Word / Vowel"], ["Pitch Random", "Density", "Overlap"], ["Filter Type", "Clock Freq", "Resonance"], ["Freq Random", "Density", "Filter"], ["Inharmonicity", "Brightness", "Decay"], ["Material", "Brightness", "Decay"], ["Attack", "Brightness", "Decay"], ["Mode Balance", "Excitation", "Decay"], ["Metallic", "High-Pass", "Decay"]];
const MOD_DST = ["Off", "Pitch (all)", "Amp", "Pan", "Drive", "Out Gain", "OSC 1 Pitch", "OSC 1 Level", "OSC 1 Pan", "OSC 1 Position / Harm", "OSC 1 Warp 1 / Timbre", "OSC 1 Warp 2 / Morph", "OSC 1 Cutoff", "OSC 1 Reso", "OSC 1 Dist Drive", "OSC 2 Pitch", "OSC 2 Level", "OSC 2 Pan", "OSC 2 Position / Harm", "OSC 2 Warp 1 / Timbre", "OSC 2 Warp 2 / Morph", "OSC 2 Cutoff", "OSC 2 Reso", "OSC 2 Dist Drive", "OSC 3 Pitch", "OSC 3 Level", "OSC 3 Pan", "OSC 3 Position / Harm", "OSC 3 Warp 1 / Timbre", "OSC 3 Warp 2 / Morph", "OSC 3 Cutoff", "OSC 3 Reso", "OSC 3 Dist Drive", "OSC 4 Pitch", "OSC 4 Level", "OSC 4 Pan", "OSC 4 Position / Harm", "OSC 4 Warp 1 / Timbre", "OSC 4 Warp 2 / Morph", "OSC 4 Cutoff", "OSC 4 Reso", "OSC 4 Dist Drive", "OSC 5 Pitch", "OSC 5 Level", "OSC 5 Pan", "OSC 5 Position / Harm", "OSC 5 Warp 1 / Timbre", "OSC 5 Warp 2 / Morph", "OSC 5 Cutoff", "OSC 5 Reso", "OSC 5 Dist Drive", "OSC 6 Pitch", "OSC 6 Level", "OSC 6 Pan", "OSC 6 Position / Harm", "OSC 6 Warp 1 / Timbre", "OSC 6 Warp 2 / Morph", "OSC 6 Cutoff", "OSC 6 Reso", "OSC 6 Dist Drive"];
const MOD_DST_GROUPS = [[0, ""], [1, "Global"], [6, "OSC 1"], [15, "OSC 2"], [24, "OSC 3"], [33, "OSC 4"], [42, "OSC 5"], [51, "OSC 6"]];
const MOD_TARGET = {"63": [1, 0.5], "29": [3, 0.5], "28": [4, 0.5], "190": [5, 0.5], "1006": [6, 0.5], "1001": [7, 1], "1002": [8, 0.5], "1010": [9, 0.5], "1025": [9, 0.5], "1019": [10, 0.5], "1026": [10, 0.5], "1021": [11, 0.5], "1027": [11, 0.5], "1032": [12, 0.41], "1033": [13, 0.5], "1043": [14, 0.5], "1070": [15, 0.5], "1065": [16, 1], "1066": [17, 0.5], "1074": [18, 0.5], "1089": [18, 0.5], "1083": [19, 0.5], "1090": [19, 0.5], "1085": [20, 0.5], "1091": [20, 0.5], "1096": [21, 0.41], "1097": [22, 0.5], "1107": [23, 0.5], "1134": [24, 0.5], "1129": [25, 1], "1130": [26, 0.5], "1138": [27, 0.5], "1153": [27, 0.5], "1147": [28, 0.5], "1154": [28, 0.5], "1149": [29, 0.5], "1155": [29, 0.5], "1160": [30, 0.41], "1161": [31, 0.5], "1171": [32, 0.5], "1198": [33, 0.5], "1193": [34, 1], "1194": [35, 0.5], "1202": [36, 0.5], "1217": [36, 0.5], "1211": [37, 0.5], "1218": [37, 0.5], "1213": [38, 0.5], "1219": [38, 0.5], "1224": [39, 0.41], "1225": [40, 0.5], "1235": [41, 0.5], "1262": [42, 0.5], "1257": [43, 1], "1258": [44, 0.5], "1266": [45, 0.5], "1281": [45, 0.5], "1275": [46, 0.5], "1282": [46, 0.5], "1277": [47, 0.5], "1283": [47, 0.5], "1288": [48, 0.41], "1289": [49, 0.5], "1299": [50, 0.5], "1326": [51, 0.5], "1321": [52, 1], "1322": [53, 0.5], "1330": [54, 0.5], "1345": [54, 0.5], "1339": [55, 0.5], "1346": [55, 0.5], "1341": [56, 0.5], "1347": [56, 0.5], "1352": [57, 0.41], "1353": [58, 0.5], "1363": [59, 0.5]};
const OSC_SPEC_ROWS = [
    [1000, "OSC 1 Source", 0, 2, 0, "", "btn", ["Wavetable", "Sampler", "Plaits"], 1, "Source", null],
    [1001, "OSC 1 Level", 0, 1, 0.8, "", "sld", null, 1, "Level", null],
    [1002, "OSC 1 Pan", -1, 1, 0, "", "sld", null, 1, "Pan", null],
    [1003, "OSC 1 Output", 0, 2, 0, "", "btn", ["Main", "Bus 1", "Bus 2"], 1, "Output", null],
    [1004, "OSC 1 Octave", -4, 4, 0, "oct", "stp", null, 1, "Octave", null],
    [1005, "OSC 1 Semi", -12, 12, 0, "", "stp", null, 1, "Semi", null],
    [1006, "OSC 1 Fine", -100, 100, 0, "ct", "sld", null, 1, "Fine", null],
    [1007, "OSC 1 Key Track", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Key Track", null],
    [1008, "OSC 1 Start Phase", 0, 1, 0, "", "sld", null, 1, "Phase", null],
    [1009, "OSC 1 Random Phase", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Rand Phase", null],
    [1010, "OSC 1 WT Position", 0, 1, 0, "", "sld", null, 1, "Position", null],
    [1011, "OSC 1 WT Frame Size", 0, 4, 3, "", "sel", ["256", "512", "1024", "2048", "4096"], 1, "Frame Size", null],
    [1012, "OSC 1 Root Note", 0, 127, 60, "", "stp", null, 1, "Root Note", null],
    [1013, "OSC 1 Unison Voices", 1, 7, 1, "", "stp", null, 1, "Voices", null],
    [1014, "OSC 1 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1015, "OSC 1 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1016, "OSC 1 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1017, "OSC 1 Unison Style", 0, 3, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd"], 1, "Detune Curve", null],
    [1018, "OSC 1 Warp 1 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1019, "OSC 1 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1020, "OSC 1 Warp 2 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1021, "OSC 1 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1022, "OSC 1 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1023, "OSC 1 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1024, "OSC 1 Plaits Engine", 0, 23, 8, "", "sel", PLAITS_ENGINES, 1, "Engine", PLAITS_GROUPS],
    [1025, "OSC 1 Plaits Harmonics", 0, 1, 0.5, "", "sld", null, 1, "Harmonics", null],
    [1026, "OSC 1 Plaits Timbre", 0, 1, 0.5, "", "sld", null, 1, "Timbre", null],
    [1027, "OSC 1 Plaits Morph", 0, 1, 0.5, "", "sld", null, 1, "Morph", null],
    [1030, "OSC 1 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1031, "OSC 1 Filter Type", 0, 29, 0, "", "sel", FILTER_TYPES, 1, "Type", FILTER_GROUPS],
    [1032, "OSC 1 Filter Cutoff", 20, 18000, 8000, "Hz", "sld", null, 1, "Cutoff", null],
    [1033, "OSC 1 Filter Resonance", 0, 1, 0.25, "", "sld", null, 1, "Resonance", null],
    [1034, "OSC 1 Filter Drive", 0, 1, 0, "", "sld", null, 1, "Drive", null],
    [1035, "OSC 1 Filter Key Track", 0, 1, 0.5, "", "sld", null, 1, "Key Track", null],
    [1036, "OSC 1 Filter EG Int", -1, 1, 0, "", "sld", null, 1, "EG Int", null],
    [1037, "OSC 1 Filter Velocity", 0, 1, 0, "", "sld", null, 1, "Velocity", null],
    [1038, "OSC 1 Filter EG Attack", 0, 5000, 0, "ms", "sld", null, 1, "Attack", null],
    [1039, "OSC 1 Filter EG Decay", 10, 5000, 300, "ms", "sld", null, 1, "Decay", null],
    [1040, "OSC 1 Filter EG Sustain", 0, 1, 0, "", "sld", null, 1, "Sustain", null],
    [1041, "OSC 1 Filter EG Release", 5, 5000, 250, "ms", "sld", null, 1, "Release", null],
    [1042, "OSC 1 Distortion Type", 0, 6, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"], 1, "Type", null],
    [1043, "OSC 1 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1044, "OSC 1 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1064, "OSC 2 Source", 0, 2, 0, "", "btn", ["Wavetable", "Sampler", "Plaits"], 1, "Source", null],
    [1065, "OSC 2 Level", 0, 1, 0.0, "", "sld", null, 1, "Level", null],
    [1066, "OSC 2 Pan", -1, 1, 0, "", "sld", null, 1, "Pan", null],
    [1067, "OSC 2 Output", 0, 2, 0, "", "btn", ["Main", "Bus 1", "Bus 2"], 1, "Output", null],
    [1068, "OSC 2 Octave", -4, 4, 0, "oct", "stp", null, 1, "Octave", null],
    [1069, "OSC 2 Semi", -12, 12, 0, "", "stp", null, 1, "Semi", null],
    [1070, "OSC 2 Fine", -100, 100, 0, "ct", "sld", null, 1, "Fine", null],
    [1071, "OSC 2 Key Track", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Key Track", null],
    [1072, "OSC 2 Start Phase", 0, 1, 0, "", "sld", null, 1, "Phase", null],
    [1073, "OSC 2 Random Phase", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Rand Phase", null],
    [1074, "OSC 2 WT Position", 0, 1, 0, "", "sld", null, 1, "Position", null],
    [1075, "OSC 2 WT Frame Size", 0, 4, 3, "", "sel", ["256", "512", "1024", "2048", "4096"], 1, "Frame Size", null],
    [1076, "OSC 2 Root Note", 0, 127, 60, "", "stp", null, 1, "Root Note", null],
    [1077, "OSC 2 Unison Voices", 1, 7, 1, "", "stp", null, 1, "Voices", null],
    [1078, "OSC 2 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1079, "OSC 2 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1080, "OSC 2 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1081, "OSC 2 Unison Style", 0, 3, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd"], 1, "Detune Curve", null],
    [1082, "OSC 2 Warp 1 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1083, "OSC 2 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1084, "OSC 2 Warp 2 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1085, "OSC 2 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1086, "OSC 2 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1087, "OSC 2 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1088, "OSC 2 Plaits Engine", 0, 23, 8, "", "sel", PLAITS_ENGINES, 1, "Engine", PLAITS_GROUPS],
    [1089, "OSC 2 Plaits Harmonics", 0, 1, 0.5, "", "sld", null, 1, "Harmonics", null],
    [1090, "OSC 2 Plaits Timbre", 0, 1, 0.5, "", "sld", null, 1, "Timbre", null],
    [1091, "OSC 2 Plaits Morph", 0, 1, 0.5, "", "sld", null, 1, "Morph", null],
    [1094, "OSC 2 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1095, "OSC 2 Filter Type", 0, 29, 0, "", "sel", FILTER_TYPES, 1, "Type", FILTER_GROUPS],
    [1096, "OSC 2 Filter Cutoff", 20, 18000, 8000, "Hz", "sld", null, 1, "Cutoff", null],
    [1097, "OSC 2 Filter Resonance", 0, 1, 0.25, "", "sld", null, 1, "Resonance", null],
    [1098, "OSC 2 Filter Drive", 0, 1, 0, "", "sld", null, 1, "Drive", null],
    [1099, "OSC 2 Filter Key Track", 0, 1, 0.5, "", "sld", null, 1, "Key Track", null],
    [1100, "OSC 2 Filter EG Int", -1, 1, 0, "", "sld", null, 1, "EG Int", null],
    [1101, "OSC 2 Filter Velocity", 0, 1, 0, "", "sld", null, 1, "Velocity", null],
    [1102, "OSC 2 Filter EG Attack", 0, 5000, 0, "ms", "sld", null, 1, "Attack", null],
    [1103, "OSC 2 Filter EG Decay", 10, 5000, 300, "ms", "sld", null, 1, "Decay", null],
    [1104, "OSC 2 Filter EG Sustain", 0, 1, 0, "", "sld", null, 1, "Sustain", null],
    [1105, "OSC 2 Filter EG Release", 5, 5000, 250, "ms", "sld", null, 1, "Release", null],
    [1106, "OSC 2 Distortion Type", 0, 6, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"], 1, "Type", null],
    [1107, "OSC 2 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1108, "OSC 2 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1128, "OSC 3 Source", 0, 2, 0, "", "btn", ["Wavetable", "Sampler", "Plaits"], 1, "Source", null],
    [1129, "OSC 3 Level", 0, 1, 0.0, "", "sld", null, 1, "Level", null],
    [1130, "OSC 3 Pan", -1, 1, 0, "", "sld", null, 1, "Pan", null],
    [1131, "OSC 3 Output", 0, 2, 0, "", "btn", ["Main", "Bus 1", "Bus 2"], 1, "Output", null],
    [1132, "OSC 3 Octave", -4, 4, 0, "oct", "stp", null, 1, "Octave", null],
    [1133, "OSC 3 Semi", -12, 12, 0, "", "stp", null, 1, "Semi", null],
    [1134, "OSC 3 Fine", -100, 100, 0, "ct", "sld", null, 1, "Fine", null],
    [1135, "OSC 3 Key Track", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Key Track", null],
    [1136, "OSC 3 Start Phase", 0, 1, 0, "", "sld", null, 1, "Phase", null],
    [1137, "OSC 3 Random Phase", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Rand Phase", null],
    [1138, "OSC 3 WT Position", 0, 1, 0, "", "sld", null, 1, "Position", null],
    [1139, "OSC 3 WT Frame Size", 0, 4, 3, "", "sel", ["256", "512", "1024", "2048", "4096"], 1, "Frame Size", null],
    [1140, "OSC 3 Root Note", 0, 127, 60, "", "stp", null, 1, "Root Note", null],
    [1141, "OSC 3 Unison Voices", 1, 7, 1, "", "stp", null, 1, "Voices", null],
    [1142, "OSC 3 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1143, "OSC 3 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1144, "OSC 3 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1145, "OSC 3 Unison Style", 0, 3, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd"], 1, "Detune Curve", null],
    [1146, "OSC 3 Warp 1 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1147, "OSC 3 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1148, "OSC 3 Warp 2 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1149, "OSC 3 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1150, "OSC 3 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1151, "OSC 3 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1152, "OSC 3 Plaits Engine", 0, 23, 8, "", "sel", PLAITS_ENGINES, 1, "Engine", PLAITS_GROUPS],
    [1153, "OSC 3 Plaits Harmonics", 0, 1, 0.5, "", "sld", null, 1, "Harmonics", null],
    [1154, "OSC 3 Plaits Timbre", 0, 1, 0.5, "", "sld", null, 1, "Timbre", null],
    [1155, "OSC 3 Plaits Morph", 0, 1, 0.5, "", "sld", null, 1, "Morph", null],
    [1158, "OSC 3 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1159, "OSC 3 Filter Type", 0, 29, 0, "", "sel", FILTER_TYPES, 1, "Type", FILTER_GROUPS],
    [1160, "OSC 3 Filter Cutoff", 20, 18000, 8000, "Hz", "sld", null, 1, "Cutoff", null],
    [1161, "OSC 3 Filter Resonance", 0, 1, 0.25, "", "sld", null, 1, "Resonance", null],
    [1162, "OSC 3 Filter Drive", 0, 1, 0, "", "sld", null, 1, "Drive", null],
    [1163, "OSC 3 Filter Key Track", 0, 1, 0.5, "", "sld", null, 1, "Key Track", null],
    [1164, "OSC 3 Filter EG Int", -1, 1, 0, "", "sld", null, 1, "EG Int", null],
    [1165, "OSC 3 Filter Velocity", 0, 1, 0, "", "sld", null, 1, "Velocity", null],
    [1166, "OSC 3 Filter EG Attack", 0, 5000, 0, "ms", "sld", null, 1, "Attack", null],
    [1167, "OSC 3 Filter EG Decay", 10, 5000, 300, "ms", "sld", null, 1, "Decay", null],
    [1168, "OSC 3 Filter EG Sustain", 0, 1, 0, "", "sld", null, 1, "Sustain", null],
    [1169, "OSC 3 Filter EG Release", 5, 5000, 250, "ms", "sld", null, 1, "Release", null],
    [1170, "OSC 3 Distortion Type", 0, 6, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"], 1, "Type", null],
    [1171, "OSC 3 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1172, "OSC 3 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1192, "OSC 4 Source", 0, 2, 0, "", "btn", ["Wavetable", "Sampler", "Plaits"], 1, "Source", null],
    [1193, "OSC 4 Level", 0, 1, 0.0, "", "sld", null, 1, "Level", null],
    [1194, "OSC 4 Pan", -1, 1, 0, "", "sld", null, 1, "Pan", null],
    [1195, "OSC 4 Output", 0, 2, 0, "", "btn", ["Main", "Bus 1", "Bus 2"], 1, "Output", null],
    [1196, "OSC 4 Octave", -4, 4, 0, "oct", "stp", null, 1, "Octave", null],
    [1197, "OSC 4 Semi", -12, 12, 0, "", "stp", null, 1, "Semi", null],
    [1198, "OSC 4 Fine", -100, 100, 0, "ct", "sld", null, 1, "Fine", null],
    [1199, "OSC 4 Key Track", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Key Track", null],
    [1200, "OSC 4 Start Phase", 0, 1, 0, "", "sld", null, 1, "Phase", null],
    [1201, "OSC 4 Random Phase", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Rand Phase", null],
    [1202, "OSC 4 WT Position", 0, 1, 0, "", "sld", null, 1, "Position", null],
    [1203, "OSC 4 WT Frame Size", 0, 4, 3, "", "sel", ["256", "512", "1024", "2048", "4096"], 1, "Frame Size", null],
    [1204, "OSC 4 Root Note", 0, 127, 60, "", "stp", null, 1, "Root Note", null],
    [1205, "OSC 4 Unison Voices", 1, 7, 1, "", "stp", null, 1, "Voices", null],
    [1206, "OSC 4 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1207, "OSC 4 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1208, "OSC 4 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1209, "OSC 4 Unison Style", 0, 3, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd"], 1, "Detune Curve", null],
    [1210, "OSC 4 Warp 1 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1211, "OSC 4 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1212, "OSC 4 Warp 2 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1213, "OSC 4 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1214, "OSC 4 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1215, "OSC 4 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1216, "OSC 4 Plaits Engine", 0, 23, 8, "", "sel", PLAITS_ENGINES, 1, "Engine", PLAITS_GROUPS],
    [1217, "OSC 4 Plaits Harmonics", 0, 1, 0.5, "", "sld", null, 1, "Harmonics", null],
    [1218, "OSC 4 Plaits Timbre", 0, 1, 0.5, "", "sld", null, 1, "Timbre", null],
    [1219, "OSC 4 Plaits Morph", 0, 1, 0.5, "", "sld", null, 1, "Morph", null],
    [1222, "OSC 4 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1223, "OSC 4 Filter Type", 0, 29, 0, "", "sel", FILTER_TYPES, 1, "Type", FILTER_GROUPS],
    [1224, "OSC 4 Filter Cutoff", 20, 18000, 8000, "Hz", "sld", null, 1, "Cutoff", null],
    [1225, "OSC 4 Filter Resonance", 0, 1, 0.25, "", "sld", null, 1, "Resonance", null],
    [1226, "OSC 4 Filter Drive", 0, 1, 0, "", "sld", null, 1, "Drive", null],
    [1227, "OSC 4 Filter Key Track", 0, 1, 0.5, "", "sld", null, 1, "Key Track", null],
    [1228, "OSC 4 Filter EG Int", -1, 1, 0, "", "sld", null, 1, "EG Int", null],
    [1229, "OSC 4 Filter Velocity", 0, 1, 0, "", "sld", null, 1, "Velocity", null],
    [1230, "OSC 4 Filter EG Attack", 0, 5000, 0, "ms", "sld", null, 1, "Attack", null],
    [1231, "OSC 4 Filter EG Decay", 10, 5000, 300, "ms", "sld", null, 1, "Decay", null],
    [1232, "OSC 4 Filter EG Sustain", 0, 1, 0, "", "sld", null, 1, "Sustain", null],
    [1233, "OSC 4 Filter EG Release", 5, 5000, 250, "ms", "sld", null, 1, "Release", null],
    [1234, "OSC 4 Distortion Type", 0, 6, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"], 1, "Type", null],
    [1235, "OSC 4 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1236, "OSC 4 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1256, "OSC 5 Source", 0, 2, 0, "", "btn", ["Wavetable", "Sampler", "Plaits"], 1, "Source", null],
    [1257, "OSC 5 Level", 0, 1, 0.0, "", "sld", null, 1, "Level", null],
    [1258, "OSC 5 Pan", -1, 1, 0, "", "sld", null, 1, "Pan", null],
    [1259, "OSC 5 Output", 0, 2, 0, "", "btn", ["Main", "Bus 1", "Bus 2"], 1, "Output", null],
    [1260, "OSC 5 Octave", -4, 4, 0, "oct", "stp", null, 1, "Octave", null],
    [1261, "OSC 5 Semi", -12, 12, 0, "", "stp", null, 1, "Semi", null],
    [1262, "OSC 5 Fine", -100, 100, 0, "ct", "sld", null, 1, "Fine", null],
    [1263, "OSC 5 Key Track", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Key Track", null],
    [1264, "OSC 5 Start Phase", 0, 1, 0, "", "sld", null, 1, "Phase", null],
    [1265, "OSC 5 Random Phase", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Rand Phase", null],
    [1266, "OSC 5 WT Position", 0, 1, 0, "", "sld", null, 1, "Position", null],
    [1267, "OSC 5 WT Frame Size", 0, 4, 3, "", "sel", ["256", "512", "1024", "2048", "4096"], 1, "Frame Size", null],
    [1268, "OSC 5 Root Note", 0, 127, 60, "", "stp", null, 1, "Root Note", null],
    [1269, "OSC 5 Unison Voices", 1, 7, 1, "", "stp", null, 1, "Voices", null],
    [1270, "OSC 5 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1271, "OSC 5 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1272, "OSC 5 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1273, "OSC 5 Unison Style", 0, 3, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd"], 1, "Detune Curve", null],
    [1274, "OSC 5 Warp 1 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1275, "OSC 5 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1276, "OSC 5 Warp 2 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1277, "OSC 5 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1278, "OSC 5 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1279, "OSC 5 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1280, "OSC 5 Plaits Engine", 0, 23, 8, "", "sel", PLAITS_ENGINES, 1, "Engine", PLAITS_GROUPS],
    [1281, "OSC 5 Plaits Harmonics", 0, 1, 0.5, "", "sld", null, 1, "Harmonics", null],
    [1282, "OSC 5 Plaits Timbre", 0, 1, 0.5, "", "sld", null, 1, "Timbre", null],
    [1283, "OSC 5 Plaits Morph", 0, 1, 0.5, "", "sld", null, 1, "Morph", null],
    [1286, "OSC 5 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1287, "OSC 5 Filter Type", 0, 29, 0, "", "sel", FILTER_TYPES, 1, "Type", FILTER_GROUPS],
    [1288, "OSC 5 Filter Cutoff", 20, 18000, 8000, "Hz", "sld", null, 1, "Cutoff", null],
    [1289, "OSC 5 Filter Resonance", 0, 1, 0.25, "", "sld", null, 1, "Resonance", null],
    [1290, "OSC 5 Filter Drive", 0, 1, 0, "", "sld", null, 1, "Drive", null],
    [1291, "OSC 5 Filter Key Track", 0, 1, 0.5, "", "sld", null, 1, "Key Track", null],
    [1292, "OSC 5 Filter EG Int", -1, 1, 0, "", "sld", null, 1, "EG Int", null],
    [1293, "OSC 5 Filter Velocity", 0, 1, 0, "", "sld", null, 1, "Velocity", null],
    [1294, "OSC 5 Filter EG Attack", 0, 5000, 0, "ms", "sld", null, 1, "Attack", null],
    [1295, "OSC 5 Filter EG Decay", 10, 5000, 300, "ms", "sld", null, 1, "Decay", null],
    [1296, "OSC 5 Filter EG Sustain", 0, 1, 0, "", "sld", null, 1, "Sustain", null],
    [1297, "OSC 5 Filter EG Release", 5, 5000, 250, "ms", "sld", null, 1, "Release", null],
    [1298, "OSC 5 Distortion Type", 0, 6, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"], 1, "Type", null],
    [1299, "OSC 5 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1300, "OSC 5 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1320, "OSC 6 Source", 0, 2, 0, "", "btn", ["Wavetable", "Sampler", "Plaits"], 1, "Source", null],
    [1321, "OSC 6 Level", 0, 1, 0.0, "", "sld", null, 1, "Level", null],
    [1322, "OSC 6 Pan", -1, 1, 0, "", "sld", null, 1, "Pan", null],
    [1323, "OSC 6 Output", 0, 2, 0, "", "btn", ["Main", "Bus 1", "Bus 2"], 1, "Output", null],
    [1324, "OSC 6 Octave", -4, 4, 0, "oct", "stp", null, 1, "Octave", null],
    [1325, "OSC 6 Semi", -12, 12, 0, "", "stp", null, 1, "Semi", null],
    [1326, "OSC 6 Fine", -100, 100, 0, "ct", "sld", null, 1, "Fine", null],
    [1327, "OSC 6 Key Track", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Key Track", null],
    [1328, "OSC 6 Start Phase", 0, 1, 0, "", "sld", null, 1, "Phase", null],
    [1329, "OSC 6 Random Phase", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Rand Phase", null],
    [1330, "OSC 6 WT Position", 0, 1, 0, "", "sld", null, 1, "Position", null],
    [1331, "OSC 6 WT Frame Size", 0, 4, 3, "", "sel", ["256", "512", "1024", "2048", "4096"], 1, "Frame Size", null],
    [1332, "OSC 6 Root Note", 0, 127, 60, "", "stp", null, 1, "Root Note", null],
    [1333, "OSC 6 Unison Voices", 1, 7, 1, "", "stp", null, 1, "Voices", null],
    [1334, "OSC 6 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1335, "OSC 6 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1336, "OSC 6 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1337, "OSC 6 Unison Style", 0, 3, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd"], 1, "Detune Curve", null],
    [1338, "OSC 6 Warp 1 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1339, "OSC 6 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1340, "OSC 6 Warp 2 Mode", 0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1341, "OSC 6 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1342, "OSC 6 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1343, "OSC 6 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1344, "OSC 6 Plaits Engine", 0, 23, 8, "", "sel", PLAITS_ENGINES, 1, "Engine", PLAITS_GROUPS],
    [1345, "OSC 6 Plaits Harmonics", 0, 1, 0.5, "", "sld", null, 1, "Harmonics", null],
    [1346, "OSC 6 Plaits Timbre", 0, 1, 0.5, "", "sld", null, 1, "Timbre", null],
    [1347, "OSC 6 Plaits Morph", 0, 1, 0.5, "", "sld", null, 1, "Morph", null],
    [1350, "OSC 6 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1351, "OSC 6 Filter Type", 0, 29, 0, "", "sel", FILTER_TYPES, 1, "Type", FILTER_GROUPS],
    [1352, "OSC 6 Filter Cutoff", 20, 18000, 8000, "Hz", "sld", null, 1, "Cutoff", null],
    [1353, "OSC 6 Filter Resonance", 0, 1, 0.25, "", "sld", null, 1, "Resonance", null],
    [1354, "OSC 6 Filter Drive", 0, 1, 0, "", "sld", null, 1, "Drive", null],
    [1355, "OSC 6 Filter Key Track", 0, 1, 0.5, "", "sld", null, 1, "Key Track", null],
    [1356, "OSC 6 Filter EG Int", -1, 1, 0, "", "sld", null, 1, "EG Int", null],
    [1357, "OSC 6 Filter Velocity", 0, 1, 0, "", "sld", null, 1, "Velocity", null],
    [1358, "OSC 6 Filter EG Attack", 0, 5000, 0, "ms", "sld", null, 1, "Attack", null],
    [1359, "OSC 6 Filter EG Decay", 10, 5000, 300, "ms", "sld", null, 1, "Decay", null],
    [1360, "OSC 6 Filter EG Sustain", 0, 1, 0, "", "sld", null, 1, "Sustain", null],
    [1361, "OSC 6 Filter EG Release", 5, 5000, 250, "ms", "sld", null, 1, "Release", null],
    [1362, "OSC 6 Distortion Type", 0, 6, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"], 1, "Type", null],
    [1363, "OSC 6 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1364, "OSC 6 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1400, "FM 1 to 1", -1, 1, 0, "", "knb", null, 1, "1→1", null],
    [1401, "FM 1 to 2", -1, 1, 0, "", "knb", null, 1, "1→2", null],
    [1402, "FM 1 to 3", -1, 1, 0, "", "knb", null, 1, "1→3", null],
    [1403, "FM 1 to 4", -1, 1, 0, "", "knb", null, 1, "1→4", null],
    [1404, "FM 1 to 5", -1, 1, 0, "", "knb", null, 1, "1→5", null],
    [1405, "FM 1 to 6", -1, 1, 0, "", "knb", null, 1, "1→6", null],
    [1406, "FM 2 to 1", -1, 1, 0, "", "knb", null, 1, "2→1", null],
    [1407, "FM 2 to 2", -1, 1, 0, "", "knb", null, 1, "2→2", null],
    [1408, "FM 2 to 3", -1, 1, 0, "", "knb", null, 1, "2→3", null],
    [1409, "FM 2 to 4", -1, 1, 0, "", "knb", null, 1, "2→4", null],
    [1410, "FM 2 to 5", -1, 1, 0, "", "knb", null, 1, "2→5", null],
    [1411, "FM 2 to 6", -1, 1, 0, "", "knb", null, 1, "2→6", null],
    [1412, "FM 3 to 1", -1, 1, 0, "", "knb", null, 1, "3→1", null],
    [1413, "FM 3 to 2", -1, 1, 0, "", "knb", null, 1, "3→2", null],
    [1414, "FM 3 to 3", -1, 1, 0, "", "knb", null, 1, "3→3", null],
    [1415, "FM 3 to 4", -1, 1, 0, "", "knb", null, 1, "3→4", null],
    [1416, "FM 3 to 5", -1, 1, 0, "", "knb", null, 1, "3→5", null],
    [1417, "FM 3 to 6", -1, 1, 0, "", "knb", null, 1, "3→6", null],
    [1418, "FM 4 to 1", -1, 1, 0, "", "knb", null, 1, "4→1", null],
    [1419, "FM 4 to 2", -1, 1, 0, "", "knb", null, 1, "4→2", null],
    [1420, "FM 4 to 3", -1, 1, 0, "", "knb", null, 1, "4→3", null],
    [1421, "FM 4 to 4", -1, 1, 0, "", "knb", null, 1, "4→4", null],
    [1422, "FM 4 to 5", -1, 1, 0, "", "knb", null, 1, "4→5", null],
    [1423, "FM 4 to 6", -1, 1, 0, "", "knb", null, 1, "4→6", null],
    [1424, "FM 5 to 1", -1, 1, 0, "", "knb", null, 1, "5→1", null],
    [1425, "FM 5 to 2", -1, 1, 0, "", "knb", null, 1, "5→2", null],
    [1426, "FM 5 to 3", -1, 1, 0, "", "knb", null, 1, "5→3", null],
    [1427, "FM 5 to 4", -1, 1, 0, "", "knb", null, 1, "5→4", null],
    [1428, "FM 5 to 5", -1, 1, 0, "", "knb", null, 1, "5→5", null],
    [1429, "FM 5 to 6", -1, 1, 0, "", "knb", null, 1, "5→6", null],
    [1430, "FM 6 to 1", -1, 1, 0, "", "knb", null, 1, "6→1", null],
    [1431, "FM 6 to 2", -1, 1, 0, "", "knb", null, 1, "6→2", null],
    [1432, "FM 6 to 3", -1, 1, 0, "", "knb", null, 1, "6→3", null],
    [1433, "FM 6 to 4", -1, 1, 0, "", "knb", null, 1, "6→4", null],
    [1434, "FM 6 to 5", -1, 1, 0, "", "knb", null, 1, "6→5", null],
    [1435, "FM 6 to 6", -1, 1, 0, "", "knb", null, 1, "6→6", null]
];

// option groups of the dropdowns: [first index, group title]
const MOD_SRC_GROUPS = [[0, ""], [1, "LFO"], [11, "Envelope"], [21, "Note"]];
const MOD_SLOTS = 20;
// parameter number of the first (source) param of a matrix slot: slots 1-10 are 307.., slots 11-20 are 472..
const slotBase = s => s < 10 ? 307 + 3 * s : 472 + 3 * (s - 10);

// ---------- filter response model (analog approximation of the DSP filter types, used by the visualizers) ----------
const cMul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
const cAdd = (a, b) => [a[0] + b[0], a[1] + b[1]];
const cSc = (a, k) => [a[0] * k, a[1] * k];
const cDiv = (a, b) => { const d = b[0] * b[0] + b[1] * b[1] || 1e-12; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; };
const cPow = (a, n) => { let r = [1, 0]; for (let i = 0; i < n; i++) r = cMul(r, a); return r; };
const VOWEL_F = [[800, 1150, 2900], [400, 1600, 2700], [350, 1700, 2700], [450, 800, 2830], [325, 700, 2530]];

// two-pole state-variable response (mode 0 LP, 1 BP, 2 HP, 3 notch, 4 allpass) at s = j f / fc
function svfH (s, k, mode) {
    const s2 = cMul(s, s);
    const den = [s2[0] + k * s[0] + 1, s2[1] + k * s[1]];
    let num = [1, 0];
    if (mode === 1) num = cSc(s, k);
    else if (mode === 2) num = s2;
    else if (mode === 3) num = [s2[0] + 1, s2[1]];
    else if (mode === 4) num = [s2[0] - k * s[0] + 1, s2[1] - k * s[1]];
    return cDiv(num, den);
}

// complex response of filter type ft (0-29) at frequency f; cutoff fc, resonance res (0-1)
function filterH (ft, fc, res, f, sweep) {
    const s = [0, f / fc];
    const k = 2 - 1.96 * res;
    const one = cDiv([1, 0], [1 + s[0], s[1]]);
    const oneHP = cMul(s, one);
    const lp = (kk) => svfH(s, kk, 0), hp = (kk) => svfH(s, kk, 2), bp = (kk) => svfH(s, kk, 1);
    const p1 = [1 + s[0], s[1]];
    switch (ft) {
        case 0: return cMul(lp(k), lp(1.2));
        case 1: return lp(k);
        case 2: return hp(k);
        case 3: return bp(k);
        case 4: return one;
        case 5: return cMul(one, lp(k));
        case 6: return oneHP;
        case 7: return cMul(oneHP, hp(k));
        case 8: return cMul(hp(k), hp(1.2));
        case 9: return cMul(bp(k), bp(k));
        case 10: return svfH(s, k, 3);
        case 11: return cMul(svfH(s, k, 3), svfH(s, k, 3));
        case 12: return cAdd([1, 0], cSc(bp(0.6), res * 4));
        case 13: return cAdd([1, 0], cSc(lp(1.4), res * 3));
        case 14: return cAdd([1, 0], cSc(hp(1.4), res * 3));
        case 15: return svfH(s, k, 4);
        case 16: { const kr = res * 3.9; return cSc(cDiv([1, 0], cAdd(cPow(p1, 4), [kr, 0])), 1 + 0.4 * kr); }
        case 17: { const kr = res * 3.2; return cMul(cDiv([1, 0], cAdd(cPow(p1, 4), [kr, 0])), cSc(cAdd(p1, [1, 0]), 0.5)); }
        case 18: { const kr = res * 3.6; return cSc(cDiv([1, 0], cAdd(cPow(p1, 3), [kr, 0])), 1 + res); }
        case 19: return cSc(cMul(lp(k), lp(1.2)), 1.3);
        case 20: case 21: case 28: case 29: {
            const sw = sweep || 1;
            const th = 2 * Math.PI * f / (fc / sw);
            const fb = res * ((ft >= 28) ? 0.95 : 0.97) * ((ft === 21 || ft === 29) ? -1 : 1);
            return cSc(cDiv([1, 0], [1 - fb * Math.cos(th), fb * Math.sin(th)]), 0.7);
        }
        case 22: {
            const A = cPow(cDiv([1 - s[0], -s[1]], p1), 4);
            const w = 2 * Math.PI * f / 48000;
            const fbk = res * 0.85;
            const den = cAdd([1, 0], cSc(cMul(A, [Math.cos(w), -Math.sin(w)]), -fbk));
            return cSc(cAdd([1, 0], cDiv(A, den)), 0.5);
        }
        case 23: {
            const p = Math.min(1, Math.max(0, Math.log(Math.max(fc, 100) / 100) / Math.log(30))) * 4;
            const v0 = Math.min(3, Math.floor(p)), vf = p - v0;
            const kq = 2 - 1.96 * Math.min(0.98, Math.max(0, 0.5 + res * 0.45));
            const w = [1, 0.7, 0.5];
            let acc = [0, 0];
            for (let i = 0; i < 3; i++) {
                const fi = VOWEL_F[v0][i] * (1 - vf) + VOWEL_F[v0 + 1][i] * vf;
                acc = cAdd(acc, cSc(svfH([0, f / fi], kq, 1), w[i]));
            }
            return cSc(acc, 1.4);
        }
        default: {   // 24-27: MG Low 6 / 12 / 18 / 24, ladder tapped after stage 1-4
            const kr = res * 3.9, n = ft - 23;
            const y4 = cDiv([1.2, 0], cAdd(cPow(p1, 4), [kr, 0]));
            return cSc(cMul(y4, cPow(p1, 4 - n)), 1.1 * (1 + 0.4 * kr));
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// FX rack: what every effect type is called and what its six normalised knobs (P1-P6) mean. Keep in step with the
// table at the top of the rack section in Eisenpuls_Synth.cmajor.
// ---------------------------------------------------------------------------------------------------------------
const fxLin = (lo, hi, dec, unit) => n => (lo + n * (hi - lo)).toFixed(dec) + (unit ? " " + unit : "");
const fxExp = (lo, hi) => n => lo * Math.pow(hi / lo, Math.max(0, Math.min(1, n)));
const fxExpN = (v, lo, hi) => Math.log(v / lo) / Math.log(hi / lo);
const fxHz = (lo, hi) => n => { const v = fxExp(lo, hi)(n); return v >= 1000 ? (v / 1000).toFixed(2) + " kHz" : v.toFixed(v < 10 ? 2 : 0) + " Hz"; };
const fxMs = (lo, hi) => n => { const v = fxExp(lo, hi)(n); return v >= 1000 ? (v / 1000).toFixed(2) + " s" : v.toFixed(v < 10 ? 1 : 0) + " ms"; };
const fxPct = n => Math.round(n * 100) + "%";
const fxPctOf = max => n => Math.round(n * max * 100) + "%";
const fxDb = (lo, hi) => n => { const v = lo + n * (hi - lo); return (v > 0 ? "+" : "") + v.toFixed(1) + " dB"; };
// [label, formatter, default (normalised)]
const FX_TYPES = [
    { n: "None", mix: 1, modes: [], p: [] },
    { n: "Distortion", mix: 1, modes: ["Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"],
      p: [["Drive", fxPct, 0.4], ["Tone", fxHz(500, 20000), 1], ["Output", n => (n * 2).toFixed(2) + "x", 0.5]] },
    { n: "Bit Crush", mix: 1, modes: [],
      p: [["Bits", n => (16 - 12 * n).toFixed(1) + " bit", 0.5], ["Rate", n => "1/" + (1 + Math.round(n * 31)), 0.1]] },
    { n: "Delay", mix: 0.35, modes: ["Digital", "Tape", "Dual"],
      p: [["Time", fxMs(10, 1000), fxExpN(375, 10, 1000)], ["Feedback", fxPctOf(0.95), 0.37], ["Damp", fxHz(500, 18000), 1], ["Ping-Pong", fxPct, 1]] },
    { n: "Chorus", mix: 0.5, modes: ["Classic", "Dimension", "Vibrato"],
      p: [["Rate", fxHz(0.05, 5), fxExpN(0.8, 0.05, 5)], ["Depth", fxPct, 0.5], ["Feedback", fxPctOf(0.9), 0]] },
    { n: "Flanger", mix: 0.5, modes: [],
      p: [["Rate", fxHz(0.05, 5), fxExpN(0.3, 0.05, 5)], ["Depth", fxPct, 0.6], ["Feedback", fxPctOf(0.95), 0.53]] },
    { n: "Phaser", mix: 0.5, modes: ["2 Stages", "4 Stages", "6 Stages", "8 Stages"],
      p: [["Rate", fxHz(0.05, 8), fxExpN(0.4, 0.05, 8)], ["Depth", fxPct, 0.5], ["Feedback", fxPctOf(0.9), 0.55]] },
    { n: "Tremolo", mix: 1, modes: ["Sin", "Tri", "Sqr", "Saw Dn", "Saw Up"],
      p: [["Rate", fxHz(0.1, 20), fxExpN(5, 0.1, 20)], ["Depth", fxPct, 0.7], ["Stereo", fxPct, 0]] },
    { n: "Reverb", mix: 0.3, modes: ["Hall", "Room", "Plate", "Cathedral"],
      p: [["Size", fxPct, 0.5], ["Damp", fxPct, 0.5], ["PreDly", n => Math.round(n * 100) + " ms", 0.2], ["Width", fxPct, 1]] },
    { n: "Filter", mix: 1, modes: FILTER_TYPES, groups: FILTER_GROUPS,
      p: [["Cutoff", fxHz(20, 20000), 0.67], ["Reso", fxPct, 0.2], ["Drive", fxPct, 0]] },
    { n: "EQ", mix: 1, modes: [],
      p: [["Low", fxDb(-12, 12), 0.5], ["Mid", fxDb(-12, 12), 0.5], ["Mid Freq", fxHz(200, 5000), 0.5], ["High", fxDb(-12, 12), 0.5], ["Mid Q", n => "Q " + fxExp(0.3, 4)(n).toFixed(2), 0.5]] },
    { n: "Compressor", mix: 1, modes: ["Peak", "RMS"],
      p: [["Thresh", fxLin(-60, 0, 1, "dB"), 0.6], ["Ratio", n => (1 + 19 * n * n).toFixed(1) + ":1", 0.3], ["Attack", fxMs(0.1, 100), 0.4], ["Release", fxMs(10, 1000), 0.4], ["Makeup", fxLin(0, 24, 1, "dB"), 0.2]] }
];
// the three racks: slot parameters start at id, the processing-order parameters at ord (Main keeps the ids of the first rack release)
var FX_RACKS = [{ name: "Main", id: 541, ord: 641 }, { name: "Bus 1", id: 651, ord: 751 }, { name: "Bus 2", id: 761, ord: 861 }];
// where a parameter number sits in the racks: { rk, sl, off } for a slot parameter (global slot rk * 10 + sl), { rk, ord } for an order parameter
function fxLocate (num) {
    for (let rk = 0; rk < FX_RACKS.length; rk++) {
        const R = FX_RACKS[rk];
        if (num >= R.id && num < R.id + 100) return { rk, sl: Math.floor((num - R.id) / 10), off: (num - R.id) % 10, g: rk * 10 + Math.floor((num - R.id) / 10) };
        if (num >= R.ord && num < R.ord + 10) return { rk, ord: num - R.ord };
    }
    return null;
}
function fxFmt (s, v) {
    const loc = fxLocate(s.num), slot = loc.g, off = loc.off, t = FX_TYPES[(s.fxTypes || [])[slot] || 0] || FX_TYPES[0];
    if (off === 0) return FX_TYPES[Math.max(0, Math.min(FX_TYPES.length - 1, Math.round(v)))].n;
    if (off === 1) return v > 0.5 ? "On" : "Off";
    if (off === 2) return fxPct(v);
    if (off === 3) return t.modes[Math.max(0, Math.min(t.modes.length - 1, Math.round(v)))] || "-";
    const p = t.p[off - 4];
    return p ? p[1](v) : "-";
}

// Presets saved before the rack existed carry the old fixed-chain parameters; turn them into rack slots
function fxMigrateLegacy (params) {
    const has = k => Object.prototype.hasOwnProperty.call(params, k);
    for (let k = 541; k <= 881; k++) if (has(String(k))) return params;
    const g = (k, d) => (has(String(k)) && Number.isFinite(Number(params[k])) ? Number(params[k]) : d);
    const out = Object.assign({}, params);
    ["30", "31", "32", "60", "61", "62", "164", "165", "166", "167", "168", "169", "170", "171", "172", "173", "174", "177", "178", "179", "180", "181",
     "182", "183", "184", "185", "186", "187", "188", "191", "537", "538", "539", "540"].forEach(k => delete out[k]);
    const slots = [];
    const dMix = g(32, 0) * g(183, 1);
    if (dMix > 0.001) slots.push({ t: 3, mix: dMix, mode: g(537, 0), p: [fxExpN(Math.max(10, g(30, 375)), 10, 1000), g(31, 0.35) / 0.95, fxExpN(Math.max(500, g(60, 18000)), 500, 18000), g(184, 1)] });
    if (g(164, 0) > 0.001) slots.push({ t: 4, mix: g(164, 0), mode: g(538, 0), p: [fxExpN(g(165, 0.8), 0.05, 5), g(166, 0.5), g(177, 0) / 0.9] });
    if (g(185, 0) > 0.001) slots.push({ t: 5, mix: g(185, 0), mode: 0, p: [fxExpN(g(186, 0.3), 0.05, 5), g(187, 0.6), g(188, 0.5) / 0.95] });
    if (g(167, 0) > 0.001) slots.push({ t: 6, mix: g(167, 0), mode: g(539, 1), p: [fxExpN(g(168, 0.4), 0.05, 8), g(169, 0.5), g(178, 0.5) / 0.9] });
    if (g(173, 0) > 0.001) slots.push({ t: 7, mix: 1, mode: g(181, 0), p: [fxExpN(Math.max(0.1, g(174, 5)), 0.1, 20), g(173, 0), g(182, 0)] });
    if (g(170, 0) > 0.001) slots.push({ t: 8, mix: g(170, 0), mode: g(540, 0), p: [g(171, 0.5), g(172, 0.5), g(179, 0) / 100, g(180, 1)] });
    if ((g(61, 16) < 15.99 || g(62, 1) > 1.001) && g(191, 1) > 0.001) slots.push({ t: 2, mix: g(191, 1), mode: 0, p: [(16 - g(61, 16)) / 12, (g(62, 1) - 1) / 31] });
    slots.forEach((sl, i) => {
        const b = 541 + i * 10;
        out[b] = sl.t; out[b + 1] = 1; out[b + 2] = Math.max(0, Math.min(1, sl.mix)); out[b + 3] = sl.mode;
        sl.p.forEach((v, k) => { out[b + 4 + k] = Math.max(0, Math.min(1, v)); });
    });
    for (let i = slots.length; i < 10; i++) { const b = 541 + i * 10; out[b] = 0; out[b + 1] = 1; }
    for (let k = 0; k < 10; k++) out[641 + k] = k;
    return out;
}

const BASE_W = 1180, BASE_H = 760;
const LFO_STATE_KEY = "njo.lfo";
const LFO_MODES = ["Free", "Trig", "Env"];
// ---------------------------------------------------------------------------------------------------------------
// LFO shapes: a shape is a list of points {x 0..1, y -1..1, c curve -1..1 of the segment that follows}; the DSP reads a 256 value table
// ---------------------------------------------------------------------------------------------------------------
const LFO_DRAWN = 6;                 // wave value of "Drawn" (0-5 are the built-in shapes Sin Tri Sqr S&H Up Dn)
const LFO_GRIDS = [0, 4, 8, 16, 32];
function lfoCurve (y0, y1, c, t) {
    if (c > 0.001) t = Math.pow(t, 1 + 4 * c);
    else if (c < -0.001) t = 1 - Math.pow(1 - t, 1 - 4 * c);
    return y0 + (y1 - y0) * t;
}
function lfoSampleAt (pts, p) {
    p = Math.max(0, Math.min(1, p));
    for (let i = 0; i + 1 < pts.length; i++) {
        const a = pts[i], b = pts[i + 1];
        if (p <= b.x || i + 2 === pts.length) {
            const span = b.x - a.x;
            const t = span > 1e-9 ? (p - a.x) / span : 1;
            return lfoCurve(a.y, b.y, a.c || 0, Math.max(0, Math.min(1, t)));
        }
    }
    return pts.length ? pts[0].y : 0;
}
function lfoTableFromPts (pts) {
    const t = new Array(256);
    for (let i = 0; i < 256; i++) t[i] = Math.round(lfoSampleAt(pts, i / 256) * 1e5) / 1e5;
    return t;
}
// built-in shapes as point lists (what "edit" starts from) and as plain functions (what the canvas shows)
function lfoBuiltinPts (w) {
    if (w === 0) { const p = []; for (let i = 0; i <= 32; i++) p.push({ x: i / 32, y: Math.sin(2 * Math.PI * i / 32), c: 0 }); return p; }
    if (w === 1) return [{ x: 0, y: 1, c: 0 }, { x: 0.5, y: -1, c: 0 }, { x: 1, y: 1, c: 0 }];
    if (w === 2) return [{ x: 0, y: 1, c: 0 }, { x: 0.4985, y: 1, c: 0 }, { x: 0.5, y: -1, c: 0 }, { x: 1, y: -1, c: 0 }];
    if (w === 3) {
        const v = [0.55, -0.4, 0.8, -0.75, 0.1, 0.9, -0.2, -0.9], p = [];
        v.forEach((y, i) => { p.push({ x: i / 8, y, c: 0 }); p.push({ x: (i + 1) / 8 - 0.0025, y, c: 0 }); });
        p[p.length - 1].x = 1;
        return p;
    }
    if (w === 4) return [{ x: 0, y: -1, c: 0 }, { x: 1, y: 1, c: 0 }];
    return [{ x: 0, y: 1, c: 0 }, { x: 1, y: -1, c: 0 }];
}
function lfoBuiltinAt (w, p) {
    if (w === 0) return Math.sin(2 * Math.PI * p);
    if (w === 1) return 4 * Math.abs(p - 0.5) - 1;
    if (w === 2) return p < 0.5 ? 1 : -1;
    if (w === 4) return 2 * p - 1;
    if (w === 5) return 1 - 2 * p;
    return lfoSampleAt(lfoBuiltinPts(3), p);
}
// the Shape menu: built-in waves first (w), then drawn presets (pts)
const LFO_PRESETS = [
    { n: "Sine", w: 0 }, { n: "Triangle", w: 1 }, { n: "Square", w: 2 }, { n: "S&H", w: 3 }, { n: "Saw Up", w: 4 }, { n: "Saw Down", w: 5 },
    { n: "Pulse 25%", pts: [{ x: 0, y: 1, c: 0 }, { x: 0.2485, y: 1, c: 0 }, { x: 0.25, y: -1, c: 0 }, { x: 1, y: -1, c: 0 }] },
    { n: "Half Sine", pts: (() => { const p = []; for (let i = 0; i <= 16; i++) p.push({ x: i / 32, y: Math.sin(Math.PI * i / 16), c: 0 }); p.push({ x: 0.5015, y: -1, c: 0 }); p.push({ x: 1, y: -1, c: 0 }); return p; })() },
    { n: "Exp Decay", pts: [{ x: 0, y: 1, c: 0.8 }, { x: 1, y: -1, c: 0 }] },
    { n: "Ramp + Hold", pts: [{ x: 0, y: -1, c: 0 }, { x: 0.5, y: 1, c: 0 }, { x: 1, y: 1, c: 0 }] },
    { n: "Bounce", pts: [{ x: 0, y: -1, c: -0.8 }, { x: 0.25, y: 1, c: 0.8 }, { x: 0.5, y: -1, c: -0.8 }, { x: 0.75, y: 0.4, c: 0.8 }, { x: 1, y: -1, c: 0 }] },
    { n: "Steps 4", pts: [{ x: 0, y: -1, c: 0 }, { x: 0.2485, y: -1, c: 0 }, { x: 0.25, y: -0.33, c: 0 }, { x: 0.4985, y: -0.33, c: 0 }, { x: 0.5, y: 0.33, c: 0 }, { x: 0.7485, y: 0.33, c: 0 }, { x: 0.75, y: 1, c: 0 }, { x: 1, y: 1, c: 0 }] },
    { n: "Double Hump", pts: [{ x: 0, y: -1, c: 0 }, { x: 0.25, y: 1, c: 0 }, { x: 0.5, y: -0.2, c: 0 }, { x: 0.75, y: 0.7, c: 0 }, { x: 1, y: -1, c: 0 }] }
];

const MOD_SRC_SHORT = n => n >= 1 && n <= 10 ? "LFO " + n : n >= 11 && n <= 20 ? "ENV " + (n - 10) : ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "VEL", "KEY", "RND"][n] || "";
const MOD_SRC_COLOR = n => n >= 1 && n <= 10 ? "#ff6a4d" : n >= 11 && n <= 20 ? "#4db8ff" : "#c9c24a";


const SPECS = (() => {
    const L = [
        [2,  "Voice",        0, 1, 0, "", "btn", ["Poly", "Mono"]],
        [3,  "Glide",        0, 1000, 0, "ms", "sld"],
        [18, "Attack",       0, 2000, 2, "ms", "sld"],
        [19, "Decay",        10, 4000, 500, "ms", "sld"],
        [20, "Sustain",      0, 1, 0.8, "", "sld"],
        [21, "Release",      5, 4000, 250, "ms", "sld"],
        [22, "Velocity",     0, 1, 0.6, "", "sld"],
        [28, "Synth Drive",  0, 1, 0.1, "", "sld"],
        [29, "Synth Pan",    -1, 1, 0, "", "sld"],
        [36, "Master",       0, 1, 0.8, "", "sld"],
        [45, "Pitch EG",     -24, 24, 0, "st", "sld"],
        [46, "P.EG Decay",   10, 2000, 150, "ms", "sld"],
        [63, "Master Tune",  -100, 100, 0, "ct", "sld"],
        [175, "Stereo Width", 0, 2, 1, "", "sld"],
        [189, "Tone",        -1, 1, 0, "", "sld"],
        [190, "Out Gain",    0, 2, 1, "", "sld"]
    ];
    // mod page: 10 LFOs (wave stepper + rate), 10 ADSR envelopes, 10 matrix slots
    for (let i = 0; i < 10; i++) {
        L.push([247 + 2 * i, "LFO " + (i + 1) + " Wave", 0, 6, 0, "", "btn", MOD_WAVES]);
        const lb = 882 + 5 * i, ln = "LFO " + (i + 1);
        L.push([lb,     ln + " Mode",   0, 2, 0, "", "btn", LFO_MODES, 1, "Mode"]);
        L.push([lb + 1, ln + " Delay",  0, 5000, 0, "ms", "sld", null, 1, "Delay"]);
        L.push([lb + 2, ln + " Rise",   0, 5000, 0, "ms", "sld", null, 1, "Rise"]);
        L.push([lb + 3, ln + " Smooth", 0, 1, 0, "", "sld", null, 1, "Smooth"]);
        L.push([lb + 4, ln + " Phase",  0, 1, 0, "", "sld", null, 1, "Phase"]);
        L.push([248 + 2 * i, "LFO " + (i + 1) + " Rate", 0.01, 50, 1, "Hz", "sld"]);
    }
    for (let i = 0; i < 10; i++) {
        const b = 267 + 4 * i;
        L.push([b,     "Env " + (i + 1) + " Attack",  0, 5000, 10, "ms", "sld"]);
        L.push([b + 1, "Env " + (i + 1) + " Decay",   10, 5000, 300, "ms", "sld"]);
        L.push([b + 2, "Env " + (i + 1) + " Sustain", 0, 1, 0.5, "", "sld"]);
        L.push([b + 3, "Env " + (i + 1) + " Release", 5, 5000, 300, "ms", "sld"]);
    }
    for (let i = 0; i < MOD_SLOTS; i++) {
        const b = slotBase(i);
        L.push([b,     "Slot " + (i + 1) + " Source", 0, 23, 0, "", "sel", MOD_SRC, 10, "", MOD_SRC_GROUPS]);
        L.push([b + 1, "Slot " + (i + 1) + " Dest",   0, MOD_DST.length - 1, 0, "", "sel", MOD_DST, 5, "", MOD_DST_GROUPS]);
        L.push([b + 2, "Slot " + (i + 1) + " Amount", -1, 1, 0, "", "sld"]);
    }
    // LFO beat sync: per mod LFO sync switch + division, global tempo override, main LFO sync
    for (let i = 0; i < 10; i++) {
        L.push([502 + 2 * i, "LFO " + (i + 1) + " Sync", 0, 1, 0, "", "btn", ["Free", "Sync"], 1, "Sync"]);
        L.push([503 + 2 * i, "LFO " + (i + 1) + " Division", 0, 17, 8, "", "sel", SYNC_DIVS, 1, "Division"]);
    }
    L.push([221, "DC Block", 0, 1, 0, "", "btn", ["Off", "On"], 1, "DC Block"]);
    L.push([222, "DC Block Freq", 5, 200, 20, "Hz", "sld", null, 1, "DC Freq"]);
    L.push([522, "Sync BPM", 0, 300, 0, "BPM", "sld", null, 1, "Sync Tempo"]);
    // fx algorithm of the synth Drive (the rack effects carry their own mode selector)
    L.push([536, "Drive Algorithm", 0, 5, 0, "", "sel", ["Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"], 1, "Algorithm"]);
    // FX rack: 10 slots x (type, on, mix, mode, P1..P6) at 541..640, processing order at 641..650
    FX_RACKS.forEach(rack => {
        for (let sl = 0; sl < 10; sl++) {
            const b = rack.id + sl * 10, n = rack.name + " FX " + (sl + 1);
            L.push([b,     n + " Type", 0, 11, 0, "", "sel", FX_TYPES.map(t => t.n), 1, "Type"]);
            L.push([b + 1, n + " On",   0, 1, 1, "", "btn", ["Off", "On"], 1, "On"]);
            L.push([b + 2, n + " Mix",  0, 1, 1, "", "sld", null, 1, "Mix"]);
            L.push([b + 3, n + " Mode", 0, 29, 0, "", "sel", FILTER_TYPES, 1, "Mode"]);
            for (let k = 0; k < 6; k++) L.push([b + 4 + k, n + " P" + (k + 1), 0, 1, 0.5, "", "sld", null, 1, "P" + (k + 1)]);
        }
        for (let k = 0; k < 10; k++) L.push([rack.ord + k, rack.name + " FX Order " + (k + 1), 0, 9, k, "", "stp", null, 1, "Order"]);
    });
    L.push([880, "Bus 1 Level", 0, 1.5, 1, "", "sld", null, 1, "Bus 1"]);
    L.push([881, "Bus 2 Level", 0, 1.5, 1, "", "sld", null, 1, "Bus 2"]);
    OSC_SPEC_ROWS.forEach(r => L.push(r));
    // short control names for the output card
    const FX_SHORT = { 175: "Width", 189: "Tone", 28: "Drive" };
    L.forEach(a => { if (FX_SHORT[a[0]] && !a[9]) { a[8] = a[8] || 1; a[9] = FX_SHORT[a[0]]; } });
    return L.map(a => ({ id: "param" + a[0], num: a[0], label: a[1], min: a[2], max: a[3], init: a[4], unit: a[5], kind: a[6], labels: a[7] || [], big: a[8] || 1, short: a[9] || "", groups: a[10] || null }));
})();

const SPEC_BY_NUM = new Map(SPECS.map(s => [s.num, s]));

// FX page
const FX_OUT = [28, 536, 175, 189, 221, 222];

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const CHUNK = 256;
const FRAME_SIZES = [256, 512, 1024, 2048, 4096];
const SMP_DZ_EMPTY = "DROP A SAMPLE / CLICK TO LOAD";
const WT_DZ_EMPTY = "DROP A WAVETABLE / CLICK TO LOAD";
// ---------- per-instance sample / wavetable persistence ----------
// Samples and wavetables are kept in the patch's own stored state (patchConnection.sendStoredStateValue),
// which the host saves with THIS plugin instance (inside the DAW project). They must never be kept in
// window.localStorage: the web views of all plugin instances share one localStorage, so a sample loaded in
// one instance would be restored into (and overwritten by) every other instance.
// Each memory is stored as { name, total, pcm16 } where pcm16 is base64 of little-endian signed 16-bit samples.
const SLOTS_STATE_KEY = "njo.slots";

function encodeMem (s) {
    const n = s.total | 0;
    const bytes = new Uint8Array(n * 2);
    for (let i = 0; i < n; i++) {
        const v = Math.round(Math.max(-1, Math.min(1, s.data[i] || 0)) * 32767);
        bytes[i * 2] = v & 255;
        bytes[i * 2 + 1] = (v >> 8) & 255;
    }
    let bin = "";
    for (let i = 0; i < bytes.length; i += 8192)
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
    return { name: s.name, total: n, pcm16: btoa(bin) };
}

function decodeMem (o, fallbackName) {
    if (!o || typeof o !== "object" || typeof o.pcm16 !== "string" || !(o.total > 0)) return null;
    let bin;
    try { bin = atob(o.pcm16); } catch (_) { return null; }
    const n = Math.min(o.total | 0, bin.length >> 1);
    if (n <= 0) return null;
    const data = new Float32Array(n);
    for (let i = 0; i < n; i++) {
        let v = bin.charCodeAt(i * 2) | (bin.charCodeAt(i * 2 + 1) << 8);
        if (v & 0x8000) v -= 0x10000;
        data[i] = v / 32767;
    }
    return { name: o.name || fallbackName, total: n, data };
}

function fmt (s, v) {
    if (fxLocate(s.num)) return fxLocate(s.num).ord !== undefined ? String(Math.round(v) + 1) : fxFmt(s, v);
    if (s.num === 880 || s.num === 881) return Math.round(v * 100) + "%";
    if (s.num === 522) return v < 1 ? "HOST" : Math.round(v) + " BPM";
    if (s.num >= FM_BASE && s.num < FM_BASE + 36) { const p = Math.round(v * 100); return (p > 0 ? "+" : "") + p + "%"; }
    if (s.num >= OSC_BASE && s.num < OSC_BASE + OSC_STRIDE * OSC_N) {
        const k = (s.num - OSC_BASE) % OSC_STRIDE;
        if (k === OSC_K.pan) { const p = Math.round(v * 50); return p === 0 ? "C" : (p < 0 ? "L" + (-p) : "R" + p); }
        if (k === OSC_K.phase) return Math.round(v * 360) + "\u00b0";
        if (k === OSC_K.root) { const n = Math.round(v); return NOTE_NAMES[n % 12] + (Math.floor(n / 12) - 1); }
        if (k === OSC_K.uvox) { const n = Math.round(v); return n + (n === 1 ? " voice" : " voices"); }
        if (k === OSC_K.udet) return "\u00b1" + Math.round(v * 50) + " ct";
        if (k === OSC_K.semi) return (v > 0 ? "+" : "") + Math.round(v) + " st";
    }
    if (s.labels.length) return s.labels[Math.max(0, Math.min(s.labels.length - 1, Math.round(v - s.min)))];
    if (s.unit === "oct") { const o = Math.round(v); return (o > 0 ? "+" : "") + o + " oct"; }
    if (s.unit === "Hz") return v >= 1000 ? (v / 1000).toFixed(2) + " kHz" : v.toFixed(v < 10 ? 2 : 0) + " Hz";
    if (s.unit === "ms") return v >= 1000 ? (v / 1000).toFixed(2) + " s" : v.toFixed(0) + " ms";
    if (s.unit === "st") return (v > 0 ? "+" : "") + v.toFixed(s.kind === "stp" ? 0 : 1) + " st";
    if (s.unit === "ct") return (v > 0 ? "+" : "") + v.toFixed(0) + " ct";
    if (s.unit === "dB") return (v > 0 ? "+" : "") + v.toFixed(1) + " dB";
    if (s.unit === "x") return v.toFixed(2) + "x";
    if (s.unit === "bit") return v.toFixed(0) + " bit";
    if (s.kind === "knb") return v.toFixed(2);
    if (s.min >= -1 && s.max <= 1) return Math.round(v * 100) + "%";
    return v.toFixed(2);
}

// wavetable warp maths, identical to the DSP so the waveform window shows what is played
function warpPhase (mode, amt, ph) {
    if (mode === 1) return Math.pow(ph, 1 + 3 * amt);
    if (mode === 2) return 1 - Math.pow(1 - ph, 1 + 3 * amt);
    if (mode === 3) { const x = ph * (1 + 7 * amt); return x - Math.floor(x); }
    if (mode === 4) { const w = 0.5 - 0.45 * amt; return ph < w ? ph * 0.5 / w : 0.5 + (ph - w) * 0.5 / (1 - w); }
    if (mode === 5) { let x = ph * (1 + amt); if (x > 1) x = 2 - x; return Math.max(0, Math.min(1, x)); }
    if (mode === 6) return ph * (1 - amt) + (1 - ph) * amt;
    return ph;
}
function warpAmp (mode, amt, y) {
    if (mode === 7) { const s = 2 + (1 - amt) * 254; return Math.floor(y * s + 0.5) / s; }
    if (mode === 8) return y * (1 - amt) + amt * Math.sin(y * (1 + 4 * amt) * 1.5708);
    return y;
}

class EisenpulsPatchView extends HTMLElement {
    constructor (patchConnection) {
        super();
        this.pc = patchConnection;
        // This instance's saved memories (key -> value), mirrored from the patch's stored state.
        this._kv = new Map();
        this._hydrateTimer = null;
        this._ready = new Promise(resolve => { this._readyResolve = resolve; });
        this._controls = new Map();
        this._animFrame = null;
        this._paramListener = null;
        this._resizeObs = null;
        this._active = new Map();
        this._smpTimer = null;
        this._fxTypes = new Array(30).fill(0);   // effect type held by each rack slot
        this._page = "o0";
        this._mem = { wt: new Array(OSC_N).fill(null), sm: new Array(OSC_N).fill(null) };
        this._memTimer = { wt: new Array(OSC_N).fill(null), sm: new Array(OSC_N).fill(null) };
        this._memStart = [];
        this._oscReady = false;
        this._lfoPts = new Array(10).fill(null);
        this._lfoGrid = 0;
        this._modReady = false;
        this.innerHTML = this.getHTML();
    }

    connectedCallback () {
        this._disconnected = false;
        this.querySelectorAll(".control").forEach(node => {
            let spec = SPECS.find(s => s.id === node.dataset.param);
            if (!spec) return;
            { const lc = fxLocate(spec.num); if (lc && lc.ord === undefined) spec = Object.assign({}, spec, { fxTypes: this._fxTypes }); }   // per-instance formatting context
            const opts = { pc: this.pc, spec, node, onChange: (v, user) => this.onValue(spec, v, user) };
            const kind = node.dataset.widget || node.dataset.control;
            const ctrl = kind === "buttons" ? new ButtonGroupControl(opts)
                       : kind === "stepper" ? new StepperControl(opts)
                       : kind === "select" ? new SelectControl(opts)
                       : kind === "fader" ? new FaderControl(opts)
                       : kind === "knob" ? new KnobControl(opts)
                       : new SliderControl(opts);
            this._controls.set(spec.id, ctrl);
            ctrl.setValue(spec.init, false);
        });
        this.buildTabs();
        this.buildFxRack();
        this.buildOscPages();
        this.updateSlots();
        this.buildModStrip();
        this.buildSizeSelect();
        this._modReady = true;
        this.buildManager();

        this._paramListener = ({ endpointID: id, value: v }) => {
            const c = this._controls.get(id);
            if (c) c.setValue(Number(v), false);
        };
        this.pc.addAllParameterListener(this._paramListener);

        window.__amorphProcessMidi = (messages) => {
            messages.forEach(m => {
                const t = m.s & 0xF0;
                if (t === 0x90 && m.d2 > 0) this._active.set(m.d1, m.d2 / 127);
                else if (t === 0x80 || (t === 0x90 && m.d2 === 0)) this._active.delete(m.d1);
            });
        };

        this.fit();
        requestAnimationFrame(() => this.fit());
        if (typeof ResizeObserver !== "undefined") {
            this._resizeObs = new ResizeObserver(() => this.fit());
            this._resizeObs.observe(this);
        }

        this._controls.forEach((_, id) => this.pc.requestParameterValue(id));
        this.startAnimationLoop();

        // Fetch THIS instance's saved samples / wavetables from the patch's stored state, then load them
        // into the UI and stream them back into the DSP (staggered, as before).
        this.hydrateInstanceState();
        this._ready.then(() => {
            if (this._disconnected) return;
            this.restoreLfo();
            this.loadMemStore();
            for (let o = 0; o < OSC_N; o++) this.updateOscUi(o);
            this.startMemRestore();
        });
    }

    // Reads the instance's stored state once. Resolves this._ready (also when the host cannot supply any state,
    // so a plain browser or an older host still works with empty memories).
    hydrateInstanceState () {
        let finished = false;
        const finish = values => {
            if (finished) return;
            finished = true;
            if (this._hydrateTimer) { clearTimeout(this._hydrateTimer); this._hydrateTimer = null; }
            if (values && typeof values === "object") {
                Object.keys(values).forEach(k => {
                    // never let old saved data replace something the user has already loaded since startup
                    if (!this._kv.has(k) && values[k] !== null && values[k] !== undefined) this._kv.set(k, values[k]);
                });
            }
            this._readyResolve();
        };
        if (!this.pc || typeof this.pc.requestFullStoredState !== "function") { finish(null); return; }
        this._hydrateTimer = setTimeout(() => finish(null), 3000);
        try { this.pc.requestFullStoredState(msg => finish(msg && msg.values)); } catch (_) { finish(null); }
    }

    kvGet (key) { return this._kv.has(key) ? this._kv.get(key) : null; }

    // Saves a value in this instance's stored state (the host keeps it with the project)
    kvSet (key, value) {
        this._kv.set(key, value);
        if (this.pc && typeof this.pc.sendStoredStateValue === "function") this.pc.sendStoredStateValue(key, value);
    }

    kvRemove (key) {
        this._kv.delete(key);
        if (this.pc && typeof this.pc.sendStoredStateValue === "function") this.pc.sendStoredStateValue(key, null);
    }

    disconnectedCallback () {
        this._disconnected = true;
        if (this._hydrateTimer) { clearTimeout(this._hydrateTimer); this._hydrateTimer = null; }
        if (this.teardownManager) this.teardownManager();
        if (this._paramListener) this.pc.removeAllParameterListener(this._paramListener);
        if (this._animFrame) cancelAnimationFrame(this._animFrame);
        if (this._resizeObs) this._resizeObs.disconnect();
        for (const kind of ["wt", "sm"]) this._memTimer[kind].forEach(t => { if (t) clearInterval(t); });
        this._memStart.forEach(t => clearTimeout(t));
        delete window.__amorphProcessMidi;
    }

    // window size presets: the host window is resized through the native njoResize hook (not available in a plain browser)
    buildSizeSelect () {
        const sel = this.querySelector(".sizesel");
        if (!sel) return;
        if (typeof window.njoResize === "function") sel.style.display = "";
        sel.addEventListener("change", () => {
            const f = Number(sel.value);
            if (!(f > 0)) return;
            try { window.njoResize(Math.round(BASE_W * f), Math.round(BASE_H * f)); } catch (_) {}
        });
        sel.addEventListener("keydown", e => e.stopPropagation());
        this.syncSizeSelect();
    }

    syncSizeSelect () {
        const sel = this.querySelector(".sizesel");
        if (!sel) return;
        const w = this.offsetWidth || 0, h = this.offsetHeight || 0;
        let pick = "custom";
        for (const o of sel.options) {
            const f = Number(o.value);
            if (f > 0 && Math.abs(w - BASE_W * f) <= 3 && Math.abs(h - BASE_H * f) <= 3) pick = o.value;
        }
        sel.value = pick;
    }

    fit () {
        const w = this.offsetWidth || window.innerWidth || 1180;
        const h = this.offsetHeight || window.innerHeight || 760;
        const u = Math.max(0.5, Math.min(w / 1180, h / 760));
        this.style.setProperty("--u", u.toFixed(4) + "px");
        this.syncSizeSelect();
    }

    // ---------- tabs ----------
    buildTabs () {
        this._oscPage = "o0";
        this.querySelectorAll(".tab").forEach(t => {
            t.setAttribute("tabindex", "-1");
            t.addEventListener("click", () => { this.setGroup(t.dataset.group); t.blur(); });
        });
        this.querySelectorAll(".stab").forEach(t => {
            t.setAttribute("tabindex", "-1");
            t.addEventListener("click", () => { this._oscPage = t.dataset.page; this.setGroup("osc"); t.blur(); });
        });
        this.setGroup("osc");
    }

    setGroup (g) {
        this._group = g;
        this.setAttribute("data-group", g);
        this.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.dataset.group === g));
        this.setPage(g === "osc" ? this._oscPage : g);
    }

    setPage (p) {
        this._page = p;
        this.setAttribute("data-page", p);
        this.querySelectorAll(".stab").forEach(t => t.classList.toggle("on", t.dataset.page === p));
        this.drawAllOsc();
    }

    // highlight matrix rows that have both a source and a destination assigned
    updateSlots () {
        for (let s = 0; s < MOD_SLOTS; s++) {
            const a = this._controls.get("param" + slotBase(s));
            const b = this._controls.get("param" + (slotBase(s) + 1));
            const row = this.querySelector('.mrow[data-slot="' + s + '"]');
            if (row) row.classList.toggle("act", !!a && !!b && a.value > 0 && b.value > 0);
        }
    }

    // ---------- file decoding ----------
    async decodeFile (file) {
        const AC = window.AudioContext || window.webkitAudioContext;
        const ctx = new AC();
        const sr = ctx.sampleRate || 48000;
        const ab = await file.arrayBuffer();
        const buf = await new Promise((res, rej) => {
            const p = ctx.decodeAudioData(ab, res, rej);
            if (p && p.then) p.then(res, rej);
        });
        if (ctx.close) ctx.close();
        const len = Math.min(buf.length, MAX_SMP);
        const mono = new Float32Array(len);
        const nc = buf.numberOfChannels;
        for (let c = 0; c < nc; c++) {
            const d = buf.getChannelData(c);
            for (let i = 0; i < len; i++) mono[i] += d[i] / nc;
        }
        let peak = 0;
        for (let i = 0; i < len; i++) peak = Math.max(peak, Math.abs(mono[i]));
        const g = peak > 0.0001 ? 0.9 / peak : 1;
        for (let i = 0; i < len; i++) mono[i] *= g;
        if (len < 1) throw new Error("empty");
        return { mono, len, rate: buf.sampleRate || 44100, sr, dur: buf.duration || (buf.length / (buf.sampleRate || 44100)) };
    }

    // ---------- filter visualizers ----------
    fltVal (id) { const c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; }

    fltFrame (cv) {
        const ctx = cv.getContext("2d");
        if (!ctx) return null;
        const W = cv.width, H = cv.height;
        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = "#0d0404";
        ctx.fillRect(0, 0, W, H);
        const yOf = db => H * (1 - (Math.max(-48, Math.min(24, db)) + 48) / 72);
        ctx.lineWidth = 1;
        ctx.strokeStyle = "rgba(255,59,48,0.10)";
        ctx.beginPath();
        [100, 1000, 10000].forEach(fx => { const x = W * Math.log(fx / 20) / Math.log(1000); ctx.moveTo(x, 0); ctx.lineTo(x, H); });
        [-36, -24, -12, 12].forEach(d => { const y = yOf(d); ctx.moveTo(0, y); ctx.lineTo(W, y); });
        ctx.stroke();
        ctx.strokeStyle = "rgba(255,59,48,0.40)";
        ctx.beginPath(); ctx.moveTo(0, yOf(0)); ctx.lineTo(W, yOf(0)); ctx.stroke();
        ctx.fillStyle = "rgba(255,120,100,0.55)";
        ctx.font = "bold 15px sans-serif";
        [[100, "100"], [1000, "1k"], [10000, "10k"]].forEach(a => ctx.fillText(a[1], W * Math.log(a[0] / 20) / Math.log(1000) + 4, H - 6));
        ctx.fillText("0 dB", 6, yOf(0) - 5);
        // corner brackets
        ctx.strokeStyle = "rgba(255,80,66,0.85)";
        ctx.lineWidth = 2;
        const bl = 14, bm = 3;
        ctx.beginPath();
        ctx.moveTo(bm, bm + bl); ctx.lineTo(bm, bm); ctx.lineTo(bm + bl, bm);
        ctx.moveTo(W - bm - bl, bm); ctx.lineTo(W - bm, bm); ctx.lineTo(W - bm, bm + bl);
        ctx.moveTo(bm, H - bm - bl); ctx.lineTo(bm, H - bm); ctx.lineTo(bm + bl, H - bm);
        ctx.moveTo(W - bm - bl, H - bm); ctx.lineTo(W - bm, H - bm); ctx.lineTo(W - bm, H - bm - bl);
        ctx.stroke();
        return { ctx, W, H, yOf };
    }

    fltTrace (fr, curve, color, lw, fill, dim) {
        const { ctx, W, H, yOf } = fr;
        const N = curve.length;
        ctx.beginPath();
        for (let i = 0; i < N; i++) {
            const x = W * i / (N - 1);
            const y = yOf(20 * Math.log10(Math.max(1e-5, Math.hypot(curve[i][0], curve[i][1]))));
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        if (fill) {
            ctx.save();
            ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
            const g = ctx.createLinearGradient(0, 0, 0, H);
            g.addColorStop(0, "rgba(255,59,48,0.38)"); g.addColorStop(1, "rgba(255,59,48,0.02)");
            ctx.fillStyle = g; ctx.fill();
            ctx.restore();
            ctx.beginPath();
            for (let i = 0; i < N; i++) {
                const x = W * i / (N - 1);
                const y = yOf(20 * Math.log10(Math.max(1e-5, Math.hypot(curve[i][0], curve[i][1]))));
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
        }
        ctx.strokeStyle = color; ctx.lineWidth = lw;
        ctx.shadowColor = "rgba(255,59,48,0.9)"; ctx.shadowBlur = dim ? 0 : 8;
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    fltCutMark (fr, fc) {
        const { ctx, W, H } = fr;
        const x = W * Math.log(Math.max(20, fc) / 20) / Math.log(1000);
        ctx.strokeStyle = "rgba(255,200,190,0.55)"; ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        ctx.setLineDash([]);
    }

    // ======================================================================
    // Oscillator slots: sample / wavetable memory (one of each per slot), display, filter response
    // The UI keeps the audio data (in this instance's stored state) and streams it into the DSP banks.
    // ======================================================================
    memKey (kind, o) { return "njo.mem.osc" + o + "." + kind; }

    memEndpoint (kind) { return kind === "wt" ? "wtBankLoad" : "smpBankLoad"; }

    oscVal (o, key) {
        const id = oscId(o, key);
        const c = this._controls.get("param" + id);
        return c ? c.value : SPEC_BY_NUM.get(id).init;
    }

    srcKind (o) { return Math.round(this.oscVal(o, "type")) === 1 ? "sm" : "wt"; }

    setMgr (text) {
        const el = this.querySelector(".mgr-status");
        if (el) el.textContent = text;
    }

    loadMemStore () {
        for (const kind of ["wt", "sm"]) {
            for (let o = 0; o < OSC_N; o++) {
                if (this._mem[kind][o]) continue;   // loaded by the user since startup: newer than the saved copy
                try { const m = decodeMem(this.kvGet(this.memKey(kind, o)), kind === "wt" ? "TABLE" : "SAMPLE"); if (m) this._mem[kind][o] = m; } catch (_) {}
            }
        }
    }

    memPersist (kind, o) {
        const s = this._mem[kind][o];
        try {
            if (!s) { this.kvRemove(this.memKey(kind, o)); return; }
            this.kvSet(this.memKey(kind, o), encodeMem(s));
        } catch (_) { this.setMgr("STORAGE FULL"); }
    }

    memCancel (kind, o) {
        const t = this._memTimer[kind][o];
        if (t) { clearInterval(t); this._memTimer[kind][o] = null; }
    }

    // streams one memory into its DSP bank in chunks (the event queue is small)
    memStream (kind, o, s, done) {
        this.memCancel(kind, o);
        const ep = this.memEndpoint(kind), total = s.total;
        let offset = 0;
        this._memTimer[kind][o] = setInterval(() => {
            for (let k = 0; k < 6 && offset < total; k++) {
                const count = Math.min(CHUNK, total - offset);
                const data = new Array(CHUNK).fill(0);
                for (let i = 0; i < count; i++) data[i] = s.data[offset + i];
                this.pc.sendEventOrValue(ep, { bank: o, offset, count, total, data });
                offset += count;
            }
            if (this.srcKind(o) === kind) this.setDz(o, "LOADING " + Math.round(offset / total * 100) + "%", "busy");
            if (offset >= total) { this.memCancel(kind, o); if (done) done(); }
        }, 6);
    }

    // UI -> DSP: stream every saved memory back, staggered
    startMemRestore () {
        let n = 0;
        for (const kind of ["wt", "sm"]) {
            for (let o = 0; o < OSC_N; o++) {
                const s = this._mem[kind][o];
                if (!s) continue;
                this._memStart.push(setTimeout(() => this.memStream(kind, o, s, () => this.updateOscUi(o)), 150 * n++));
            }
        }
    }

    setDz (o, text, cls) {
        const dz = this.querySelector('.dz-osc[data-o="' + o + '"]');
        if (!dz) return;
        dz.querySelector(".dz-txt").textContent = text;
        dz.classList.toggle("loaded", cls === "loaded");
        dz.classList.toggle("busy", cls === "busy");
        dz.classList.toggle("err", cls === "err");
    }

    pickFrameIndex (len) {
        if (len % 4096 === 0) return 4;
        if (len % 2048 === 0) return 3;
        if (len >= 2048) return 3;
        const rest = [2, 1, 0];
        for (let i = 0; i < rest.length; i++) if (len % FRAME_SIZES[rest[i]] === 0) return rest[i];
        let k = 0;
        for (let j = 0; j < FRAME_SIZES.length; j++) if (FRAME_SIZES[j] <= len) k = j;
        return k;
    }

    async loadMem (kind, o, file, libId) {
        this.memCancel(kind, o);
        this.setDz(o, "DECODING...", "busy");
        try {
            const dec = await this.decodeFile(file);
            this.libTrack(kind + o, file, libId, dec);
            const name = (file.name || (kind === "wt" ? "TABLE" : "SAMPLE")).replace(/\.[^.]+$/, "").slice(0, 14).toUpperCase();
            const s = { name, total: dec.len, data: dec.mono };
            if (kind === "wt") { const fc = this._controls.get("param" + oscId(o, "wsize")); if (fc) fc.setValue(this.pickFrameIndex(s.total), true); }
            this.memStream(kind, o, s, () => {
                this._mem[kind][o] = s;
                this.memPersist(kind, o);
                this.updateOscUi(o);
                this.setMgr("LOADED " + name);
                const lvl = this._controls.get("param" + oscId(o, "level"));
                if (lvl && lvl.value < 0.05) lvl.setValue(0.8, true);
            });
        } catch (err) {
            this.memCancel(kind, o);
            this.setDz(o, "UNSUPPORTED FILE", "err");
        }
    }

    clearMem (o) {
        const kind = this.srcKind(o);
        this.memCancel(kind, o);
        this.pc.sendEventOrValue(this.memEndpoint(kind), { bank: o, offset: 0, count: 0, total: 0, data: new Array(CHUNK).fill(0) });
        this.libUntrack(kind + o);
        this._mem[kind][o] = null;
        this.memPersist(kind, o);
        this.updateOscUi(o);
        this.setMgr("OSC " + (o + 1) + " CLEARED");
    }

    buildOscPages () {
        for (let o = 0; o < OSC_N; o++) {
            const dz = this.querySelector('.dz-osc[data-o="' + o + '"]');
            if (!dz) continue;
            dz.addEventListener("dragover", ev => { ev.preventDefault(); dz.classList.add("over"); });
            dz.addEventListener("dragleave", () => dz.classList.remove("over"));
            dz.addEventListener("drop", ev => {
                ev.preventDefault(); dz.classList.remove("over");
                const f = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
                if (f) this.loadMem(this.srcKind(o), o, f);
            });
            dz.addEventListener("click", () => {
                const inp = document.createElement("input");
                inp.type = "file"; inp.accept = "audio/*,.wav,.aif,.aiff,.mp3,.ogg,.flac";
                inp.onchange = () => { if (inp.files && inp.files[0]) this.loadMem(this.srcKind(o), o, inp.files[0]); };
                inp.click();
            });
            const clr = dz.querySelector(".dz-clr");
            if (clr) clr.addEventListener("click", ev => { ev.stopPropagation(); this.clearMem(o); });
            const lib = this.querySelector('.dz-lib[data-o="' + o + '"]');
            if (lib) lib.addEventListener("click", () => { lib.dataset.slot = this.srcKind(o) + o; });
            this.updateOscUi(o);
        }
        this._oscReady = true;
    }

    // refreshes everything that depends on the source type / engine of one slot
    updateOscUi (o) {
        const type = Math.max(0, Math.min(2, Math.round(this.oscVal(o, "type"))));
        const pg = this.querySelector(".p-o" + o);
        if (pg) pg.setAttribute("data-src", String(type));
        this.querySelectorAll('[data-o="' + o + '"][data-show]').forEach(el => {
            el.style.display = el.dataset.show.split(",").indexOf(String(type)) >= 0 ? "" : "none";
        });
        const kind = type === 1 ? "sm" : "wt";
        const s = this._mem[kind][o];
        if (!this._memTimer[kind][o]) this.setDz(o, s ? s.name : (kind === "wt" ? WT_DZ_EMPTY : SMP_DZ_EMPTY), s ? "loaded" : "");
        const eng = Math.max(0, Math.min(PLAITS_ENGINES.length - 1, Math.round(this.oscVal(o, "pleng"))));
        ["pharm", "ptimb", "pmorph"].forEach((key, i) => {
            const lbl = this.querySelector(".n" + oscId(o, key) + " .lbl");
            if (lbl) lbl.textContent = PLAITS_PARAMS[eng][i];
        });
        this.drawOsc(o);
        this.drawOscFlt(o);
    }

    onOscValue (o, k) {
        if (!this._oscReady) return;   // controls are still being created
        if (k === OSC_K.type || k === OSC_K.pleng) { this.updateOscUi(o); return; }
        if (k === OSC_K.wpos || k === OSC_K.wsize || k === OSC_K.w1m || k === OSC_K.w1a || k === OSC_K.w2m || k === OSC_K.w2a
            || k === OSC_K.sstart || k === OSC_K.sloop || k === OSC_K.root) this.drawOsc(o);
        if (k >= OSC_K.fon && k <= OSC_K.fkey) this.drawOscFlt(o);
    }

    // interpolated single cycle of slot o at the current position / frame size
    wtCycle (o, W) {
        const s = this._mem.wt[o];
        if (!s || s.total < 2) return null;
        const fl = Math.max(2, Math.min(FRAME_SIZES[Math.max(0, Math.min(4, Math.round(this.oscVal(o, "wsize"))))], s.total));
        const nF = Math.max(1, Math.floor(s.total / fl));
        const p = Math.max(0, Math.min(1, this.oscVal(o, "wpos"))) * (nF - 1);
        const fa = Math.max(0, Math.min(nF - 1, Math.floor(p)));
        const fb = Math.min(nF - 1, fa + 1);
        const ff = p - fa;
        const out = new Float32Array(W);
        for (let x = 0; x < W; x++) {
            const i = Math.min(fl - 1, Math.floor(x / W * fl));
            out[x] = (s.data[fa * fl + i] || 0) * (1 - ff) + (s.data[fb * fl + i] || 0) * ff;
        }
        let mean = 0;
        for (let x = 0; x < W; x++) mean += out[x];
        mean /= W;
        for (let x = 0; x < W; x++) out[x] -= mean;   // the DSP removes the DC of every frame
        return { cyc: out, nF, frame: p + 1, name: s.name };
    }

    // the same cycle after both warp slots (null when no warp is active)
    warpCycle (cyc, ws) {
        const m1 = ws[0], a1 = ws[1], m2 = ws[2], a2 = ws[3];
        if (m1 === 0 && m2 === 0) return null;
        const W = cyc.length;
        const out = new Float32Array(W);
        let mean = 0;
        for (let x = 0; x < W; x++) {
            let rp = x / W;
            if (m1 >= 1 && m1 <= 6) rp = warpPhase(m1, a1, rp);
            if (m2 >= 1 && m2 <= 6) rp = warpPhase(m2, a2, rp);
            rp = Math.max(0, Math.min(0.99999, rp));
            const fi = rp * W, i0 = Math.floor(fi), fr = fi - i0;
            let y = cyc[i0] * (1 - fr) + cyc[(i0 + 1) % W] * fr;
            if (m1 >= 7) y = warpAmp(m1, a1, y);
            if (m2 >= 7) y = warpAmp(m2, a2, y);
            out[x] = y;
            mean += y;
        }
        mean /= W;
        for (let x = 0; x < W; x++) out[x] -= mean;
        return out;
    }

    // HUD style frame shared by the display canvases
    hudFrame (cv) {
        const ctx = cv.getContext("2d");
        if (!ctx) return null;
        const W = cv.width, H = cv.height;
        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = "#0d0404";
        ctx.fillRect(0, 0, W, H);
        ctx.strokeStyle = "rgba(255,59,48,0.10)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let gx = 0; gx <= W; gx += W / 16) { ctx.moveTo(gx, 0); ctx.lineTo(gx, H); }
        for (let gy = 0; gy <= H; gy += H / 4) { ctx.moveTo(0, gy); ctx.lineTo(W, gy); }
        ctx.stroke();
        ctx.strokeStyle = "rgba(255,59,48,0.38)";
        ctx.beginPath(); ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2); ctx.stroke();
        ctx.strokeStyle = "rgba(255,80,66,0.85)";
        ctx.lineWidth = 2;
        const bl = 16, bm = 3;
        ctx.beginPath();
        ctx.moveTo(bm, bm + bl); ctx.lineTo(bm, bm); ctx.lineTo(bm + bl, bm);
        ctx.moveTo(W - bm - bl, bm); ctx.lineTo(W - bm, bm); ctx.lineTo(W - bm, bm + bl);
        ctx.moveTo(bm, H - bm - bl); ctx.lineTo(bm, H - bm); ctx.lineTo(bm + bl, H - bm);
        ctx.moveTo(W - bm - bl, H - bm); ctx.lineTo(W - bm, H - bm); ctx.lineTo(W - bm, H - bm - bl);
        ctx.stroke();
        ctx.lineWidth = 1;
        return { ctx, W, H };
    }

    drawOsc (o) {
        const cv = this.querySelector('.osc-canvas[data-o="' + o + '"]');
        const info = this.querySelector('.osc-info[data-o="' + o + '"]');
        if (!cv) return;
        const fr = this.hudFrame(cv);
        if (!fr) return;
        const { ctx, W, H } = fr;
        const type = Math.round(this.oscVal(o, "type"));
        const trace = (arr, color, lw) => {
            ctx.strokeStyle = color; ctx.lineWidth = lw;
            ctx.shadowColor = "rgba(255,59,48,0.9)"; ctx.shadowBlur = lw > 1 ? 8 : 0;
            ctx.beginPath();
            for (let x = 0; x < W; x++) {
                const y = H / 2 - Math.max(-1.2, Math.min(1.2, arr[x])) * (H / 2 - 4);
                if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
            ctx.shadowBlur = 0;
        };
        if (type === 0) {
            const r = this.wtCycle(o, W);
            if (!r) { if (info) info.textContent = "NO WAVETABLE LOADED"; return; }
            const ws = [Math.round(this.oscVal(o, "w1m")), this.oscVal(o, "w1a"), Math.round(this.oscVal(o, "w2m")), this.oscVal(o, "w2a")];
            const warped = this.warpCycle(r.cyc, ws);
            let tag = "";
            if (warped) tag = " / WARP " + [0, 2].filter(k => ws[k] > 0).map(k => WARP_MODES[ws[k]]).join(" + ");
            if (info) info.textContent = r.name + " / FRAME " + r.frame.toFixed(1) + " OF " + r.nF + tag;
            if (warped) { trace(r.cyc, "rgba(255,150,140,0.40)", 1); trace(warped, "#ff7a45", 2); }
            else trace(r.cyc, "#ff3b30", 2);
        } else if (type === 1) {
            const s = this._mem.sm[o];
            if (!s) { if (info) info.textContent = "NO SAMPLE LOADED"; return; }
            const n = s.total, step = Math.max(1, Math.floor(n / W));
            const start = Math.max(0, Math.min(1, this.oscVal(o, "sstart")));
            ctx.fillStyle = "rgba(255,59,48,0.12)";
            ctx.fillRect(0, 0, W * start, H);
            ctx.strokeStyle = "#ff3b30"; ctx.lineWidth = 1.5;
            ctx.beginPath();
            for (let x = 0; x < W; x++) {
                const a = Math.floor(x / W * n);
                let mn = 1, mx = -1;
                for (let i = a; i < Math.min(n, a + step); i++) { const v = s.data[i]; if (v < mn) mn = v; if (v > mx) mx = v; }
                if (mx < mn) { mn = mx = 0; }
                ctx.moveTo(x, H / 2 - mx * (H / 2 - 4)); ctx.lineTo(x, H / 2 - mn * (H / 2 - 4));
            }
            ctx.stroke();
            ctx.strokeStyle = "rgba(255,200,190,0.7)"; ctx.setLineDash([4, 4]);
            ctx.beginPath(); ctx.moveTo(W * start, 0); ctx.lineTo(W * start, H); ctx.stroke();
            ctx.setLineDash([]);
            if (info) info.textContent = s.name + " / " + (n / 48000).toFixed(2) + " S" + (this.oscVal(o, "sloop") > 0.5 ? " / LOOP" : "");
        } else {
            const eng = Math.max(0, Math.min(PLAITS_ENGINES.length - 1, Math.round(this.oscVal(o, "pleng"))));
            ctx.fillStyle = "rgba(255,120,100,0.85)";
            ctx.font = "bold " + Math.round(H * 0.2) + "px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(PLAITS_ENGINES[eng].toUpperCase(), W / 2, H / 2 + H * 0.05);
            ctx.font = "bold " + Math.round(H * 0.1) + "px sans-serif";
            ctx.fillStyle = "rgba(255,200,190,0.5)";
            ctx.fillText("PLAITS / " + (eng + 1) + " OF " + PLAITS_ENGINES.length, W / 2, H / 2 + H * 0.25);
            ctx.textAlign = "left";
            if (info) info.textContent = PLAITS_ENGINES[eng] + " / " + PLAITS_PARAMS[eng].join(" - ");
        }
    }

    // magnitude response (complex) of the filter of slot o on a log frequency grid
    oscFltCurve (o, N, sweep) {
        const ft = Math.round(this.oscVal(o, "ftype")), fc = this.oscVal(o, "fcut"), res = this.oscVal(o, "fres");
        const out = [];
        for (let i = 0; i < N; i++) out.push(filterH(ft, fc, res, 20 * Math.pow(1000, i / (N - 1)), sweep));
        return out;
    }

    drawOscFlt (o) {
        const cv = this.querySelector('.flt-canvas[data-o="' + o + '"]');
        if (!cv) return;
        const fr = this.fltFrame(cv);
        if (!fr) return;
        const N = 220, ft = Math.round(this.oscVal(o, "ftype"));
        if (this.oscVal(o, "fon") < 0.5) { this.fltTrace(fr, this.oscFltCurve(o, N), "rgba(180,170,165,0.45)", 1.5, false, true); return; }
        if (ft === 28 || ft === 29) {
            this.fltTrace(fr, this.oscFltCurve(o, N, 0.5), "rgba(255,150,130,0.35)", 1, false, true);
            this.fltTrace(fr, this.oscFltCurve(o, N, 1.5), "rgba(255,150,130,0.35)", 1, false, true);
        }
        this.fltTrace(fr, this.oscFltCurve(o, N), "#ff3b30", 2.5, true, false);
        this.fltCutMark(fr, this.oscVal(o, "fcut"));
    }

    drawAllOsc () { for (let o = 0; o < OSC_N; o++) { this.drawOsc(o); this.drawOscFlt(o); } }

    // ---------- page HTML ----------
    oscPageHTML (o) {
        const c = key => this.controlHTML(oscId(o, key), true);
        const sh = (list, inner, cls) => `<div class="${cls || "cgrid"}" data-o="${o}" data-show="${list}">${inner}</div>`;
        const src = `<section class="card o-src"><h2>OSC ${o + 1} Source</h2>
            <div class="o-type">${c("type")}</div>
            <canvas class="osc-canvas" data-o="${o}" width="640" height="190"></canvas>
            <div class="osc-info" data-o="${o}">--</div>
            <div class="o-mem" data-o="${o}" data-show="0,1"><div class="dz dz-osc" data-o="${o}"><span class="dz-txt"></span><span class="dz-clr" title="Clear this memory">&times;</span></div><button type="button" class="pb dz-lib" data-o="${o}" data-slot="wt${o}" title="Open the sound vault">VAULT</button></div>
            ${sh("0", ["wpos", "wsize", "w1m", "w1a", "w2m", "w2a"].map(c).join(""), "cgrid o-g2")}
            ${sh("1", ["root", "sstart", "sloop"].map(c).join(""), "cgrid o-g3")}
            ${sh("2", ["pleng", "pharm", "ptimb", "pmorph"].map(c).join(""), "cgrid o-g3 o-pl")}
          </section>`;
        const tune = `<section class="card o-tune"><h2>Tune</h2>
            <div class="cgrid o-g2">${["oct", "semi", "fine", "track"].map(c).join("")}${sh("0,1", ["phase", "rphase"].map(c).join(""), "o-sub o-g2")}</div>
            ${sh("0", "<div class=\"o-uh\">Unison</div>" + ["uvox", "udet", "ublend", "uwid", "ustyle"].map(c).join(""), "cgrid o-g2 o-uni")}
          </section>`;
        const flt = `<section class="card o-flt"><h2>Filter</h2>
            <canvas class="flt-canvas" data-o="${o}" width="600" height="200"></canvas>
            <div class="cgrid o-g3">${["fon", "ftype"].map(c).join("")}${["fcut", "fres", "fdrv", "fkey", "feg", "fvel", "fatk", "fdec", "fsus", "frel"].map(c).join("")}</div>
          </section>`;
        const out = `<section class="card o-out"><h2>Distortion / Out</h2>
            <div class="cgrid o-g2">${["dtype", "ddrv", "dmix"].map(c).join("")}</div>
            <h2 class="o-h2">Output</h2>
            <div class="cgrid o-g2">${["level", "pan", "out"].map(c).join("")}</div>
          </section>`;
        return src + tune + flt + out;
    }

    fmPageHTML () {
        let head = `<div class="fm-corner">MOD \u2193 / CARRIER \u2192</div>` + Array.from({ length: OSC_N }, (_, d) => `<div class="fm-h">OSC ${d + 1}</div>`).join("");
        let rows = "";
        for (let s = 0; s < OSC_N; s++) {
            rows += `<div class="fm-h fm-r">OSC ${s + 1}</div>`;
            for (let d = 0; d < OSC_N; d++) rows += `<div class="fm-c${s === d ? " fb" : ""}">${this.controlHTML(fmId(s, d), true)}</div>`;
        }
        return `<section class="card fm-card"><h2>FM Matrix</h2><div class="fm-grid">${head}${rows}</div><div class="fm-note">Row = modulator, column = carrier (phase modulation). The diagonal is self feedback. A modulator with Level 0 still modulates, so you can use it as a pure FM operator. Level, pan and output of every oscillator are on its own page.</div></section>`;
    }

    globalPageHTML () {
        const k = ids => ids.map(i => this.controlHTML(i, true)).join("");
        return this.card("Voice", [2, 3, 63], "g-voice") + this.card("Amp EG", [18, 19, 20, 21, 22], "g-amp") + this.card("Pitch EG", [45, 46], "g-peg")
            + this.card("Output", [29, 190, 36, 880, 881, 522], "g-out");
    }

    // ---------- parameter hooks ----------
    onValue (spec, v, user) {
        const n = spec.num;
        if (fxLocate(n)) this.onFxValue(spec, v, user);
        if (n >= OSC_BASE && n < OSC_BASE + OSC_STRIDE * OSC_N) this.onOscValue(Math.floor((n - OSC_BASE) / OSC_STRIDE), (n - OSC_BASE) % OSC_STRIDE);
        if ((n >= 307 && n <= 336) || (n >= 472 && n <= 501)) { this.updateSlots(); if (this._modReady) this.updateModRings(); }
        if (this._modReady) {
            if (MOD_TARGET[n]) this.updateModRings(n);
            if (n >= 247 && n <= 266) { const li = Math.floor((n - 247) / 2); if (n % 2 === 1) this.refreshLfoUi(li); if (li === this._lfoSel) this.drawLfo(); }
            if (n >= 502 && n <= 521) this.refreshLfoUi(Math.floor((n - 502) / 2));
            if (n >= 267 && n <= 306 && Math.floor((n - 267) / 4) === this._envSel) this.drawEnv();
        }
        if (user && this.presetDirty) this.presetDirty();
        if (user) {
            const a = this.querySelector(".lcd-name");
            const b = this.querySelector(".lcd-val");
            if (a) a.textContent = spec.label.toUpperCase();
            if (b) b.textContent = fmt(spec, v);
        }
    }

    // ---------- FX racks (Main, Bus 1, Bus 2) ----------
    fxCtl (num) { return this._controls.get("param" + num); }
    fxRow (g) { const c = this._fxRowCache || (this._fxRowCache = []); return c[g] || (c[g] = this.querySelector('.fxrow[data-g="' + g + '"]')); }

    // refresh labels / visibility / dimming of one slot (global index g) after its type or on/off changed
    updateFxRow (g) {
        const row = this.fxRow(g);
        if (!row) return;
        const rk = Math.floor(g / 10), sl = g % 10;
        const t = FX_TYPES[this._fxTypes[g]] || FX_TYPES[0];
        const b = FX_RACKS[rk].id + sl * 10;
        row.classList.toggle("empty", this._fxTypes[g] === 0);
        row.classList.toggle("nomode", t.modes.length === 0);
        const on = this.fxCtl(b + 1);
        row.classList.toggle("off", !!on && on.value < 0.5);
        const mc = this.fxCtl(b + 3);
        if (mc && mc.sel) {
            const cur = mc.value;
            mc.sel.innerHTML = this.optionsHTML({ labels: t.modes, groups: t.groups || null });
            mc.sel.selectedIndex = Math.min(cur, Math.max(0, t.modes.length - 1));
            mc.setValue(cur, false);
        }
        for (let k = 0; k < 6; k++) {
            const c = this.fxCtl(b + 4 + k);
            if (!c) continue;
            const p = t.p[k];
            c.node.classList.toggle("nop", !p);
            const lbl = c.node.querySelector(".lbl");
            if (lbl) lbl.textContent = p ? p[0] : "";
            c.setValue(c.value, false);     // re-format the value text for the new type
        }
        const mx = this.fxCtl(b + 2);
        if (mx) mx.setValue(mx.value, false);
        this.updateFxTabs();
    }

    // tab buttons: a dot marks racks that hold at least one effect
    updateFxTabs () {
        FX_RACKS.forEach((R, rk) => {
            const t = this.querySelector('.fxtab[data-rack="' + rk + '"]');
            if (t) t.classList.toggle("used", this._fxTypes.slice(rk * 10, rk * 10 + 10).some(x => x > 0));
        });
    }

    showFxRack (rk) {
        this._fxRack = rk;
        this.querySelectorAll(".f-rack").forEach(sec => sec.classList.toggle("on", Number(sec.dataset.rack) === rk));
        this.querySelectorAll(".fxtab").forEach(t => t.classList.toggle("on", Number(t.dataset.rack) === rk));
    }

    onFxValue (spec, v, user) {
        const loc = fxLocate(spec.num);
        if (loc.ord !== undefined) { this.fxApplyOrder(loc.rk); return; }
        const g = loc.g, off = loc.off;
        if (off === 0) {
            this._fxTypes[g] = Math.max(0, Math.min(FX_TYPES.length - 1, Math.round(v)));
            this.updateFxRow(g);
            if (user && !this._applying) {            // a new effect starts from its own sensible settings
                const t = FX_TYPES[this._fxTypes[g]], b = FX_RACKS[loc.rk].id + loc.sl * 10;
                const set = (num, val) => { const c = this.fxCtl(num); if (c) c.setValue(val, true); };
                set(b + 1, 1); set(b + 2, t.mix); set(b + 3, 0);
                t.p.forEach((p, k) => set(b + 4 + k, p[2]));
                this.updateFxRow(g);
            }
        } else if (off === 1) this.updateFxRow(g);
    }

    // processing order of one rack: positions -> local slots, taken from its 10 hidden order parameters
    fxOrderNow (rk) {
        const o = [];
        for (let k = 0; k < 10; k++) { const c = this.fxCtl(FX_RACKS[rk].ord + k); o.push(c ? Math.round(c.value) : k); }
        return o;
    }

    fxApplyOrder (rk, preview) {
        if (rk === undefined) { for (let r = 0; r < FX_RACKS.length; r++) this.fxApplyOrder(r); return; }
        const order = preview || this.fxOrderNow(rk);
        const pos = new Array(10).fill(-1);
        order.forEach((sl, k) => { if (sl >= 0 && sl < 10 && pos[sl] < 0) pos[sl] = k; });
        let spare = order.length;
        for (let sl = 0; sl < 10; sl++) if (pos[sl] < 0) pos[sl] = spare++;     // transient, while a preset is being applied
        for (let sl = 0; sl < 10; sl++) {
            const row = this.fxRow(rk * 10 + sl);
            if (!row) continue;
            row.style.order = String(pos[sl]);
            const pe = row.querySelector(".fxpos");
            if (pe) pe.textContent = String(pos[sl] + 1);
        }
    }

    fxCommit (rk, order) {
        const cur = this.fxOrderNow(rk);
        for (let k = 0; k < 10; k++) if (order[k] !== cur[k]) { const c = this.fxCtl(FX_RACKS[rk].ord + k); if (c) c.setValue(order[k], true); }
        this.fxApplyOrder(rk);
    }

    fxMove (rk, sl, to) {
        const order = this.fxOrderNow(rk);
        const from = order.indexOf(sl);
        if (from < 0) return;
        to = Math.max(0, Math.min(9, to));
        if (to === from) return;
        order.splice(from, 1);
        order.splice(to, 0, sl);
        this.fxCommit(rk, order);
    }

    buildFxRack () {
        this.querySelectorAll(".fxtab").forEach(t => t.addEventListener("click", () => this.showFxRack(Number(t.dataset.rack))));
        this.querySelectorAll(".fxrow").forEach(row => {
            const rk = Number(row.dataset.rack), sl = Number(row.dataset.slot);
            row.querySelector(".fxup").addEventListener("click", () => this.fxMove(rk, sl, this.fxOrderNow(rk).indexOf(sl) - 1));
            row.querySelector(".fxdn").addEventListener("click", () => this.fxMove(rk, sl, this.fxOrderNow(rk).indexOf(sl) + 1));
            const grip = row.querySelector(".fxgrip");
            let drag = null;
            grip.addEventListener("pointerdown", e => {
                drag = { pid: e.pointerId };
                row.classList.add("dragging");
                try { grip.setPointerCapture(e.pointerId); } catch (_) {}
                e.preventDefault();
            });
            grip.addEventListener("pointermove", e => {
                if (!drag || e.pointerId !== drag.pid) return;
                // target position = number of other rows of this rack whose centre is above the pointer
                let to = 0;
                this.querySelectorAll('.fxrow[data-rack="' + rk + '"]').forEach(r => {
                    if (r === row) return;
                    const bb = r.getBoundingClientRect();
                    if (bb.top + bb.height / 2 < e.clientY) to++;
                });
                const order = this.fxOrderNow(rk);
                order.splice(order.indexOf(sl), 1);
                order.splice(to, 0, sl);
                drag.next = order;
                this.fxApplyOrder(rk, order);
            });
            const end = e => {
                if (!drag || e.pointerId !== drag.pid) return;
                row.classList.remove("dragging");
                try { grip.releasePointerCapture(e.pointerId); } catch (_) {}
                const next = drag.next;
                drag = null;
                if (next) this.fxCommit(rk, next); else this.fxApplyOrder(rk);
            };
            grip.addEventListener("pointerup", end);
            grip.addEventListener("pointercancel", end);
        });
        for (let g = 0; g < 30; g++) this.updateFxRow(g);
        this.fxApplyOrder();
        this.showFxRack(this._fxRack || 0);
    }

    startAnimationLoop () {
        const loop = () => {
            const count = this._active.size;
            const any = count > 0;
            const dot = this.querySelector(".led");
            if (dot) dot.classList.toggle("on", any);
            const vu = this.querySelector(".vu-fill");
            if (vu) {
                const cur = parseFloat(vu.dataset.v || "0");
                const target = Math.min(1, count * 0.35);
                const nv = target > cur ? target : cur * 0.93;
                vu.dataset.v = String(nv);
                vu.style.width = (nv * 100).toFixed(1) + "%";
            }
            this._animFrame = requestAnimationFrame(loop);
        };
        this._animFrame = requestAnimationFrame(loop);
    }

    // ---------- html ----------
    controlHTML (id, knobs) {
        const s = SPEC_BY_NUM.get(id);
        const attrs = `data-param="${s.id}" data-min="${s.min}" data-max="${s.max}" data-step="${(s.kind === "sld" || s.kind === "knb") ? 0 : 1}" data-init="${s.init}"`;
        const head = `<div class="row"><span class="lbl">${s.short || s.label}</span><span class="val">--</span></div>`;
        if (knobs && s.kind === "sld")
            return `<div class="control knb n${s.num}" ${attrs} data-control="dial" data-widget="knob"><div class="knob"><div class="kin"></div></div>${head}</div>`;
        if (s.kind === "btn")
            return `<div class="control btns n${s.num}${s.labels.length > 3 ? " wide" : " w2"}" ${attrs} data-control="buttons">${head}<div class="grp">${s.labels.map(l => `<button type="button">${l}</button>`).join("")}</div></div>`;
        if (s.kind === "sel")
            return `<div class="control sel n${s.num} wide" ${attrs} data-control="buttons" data-widget="select">${head}<select class="dd">${this.optionsHTML(s)}</select></div>`;
        if (s.kind === "stp")
            return `<div class="control stpr n${s.num} w2" ${attrs} data-control="stepper">${head}<div class="grp"><button type="button" data-d="-1">&minus;</button><button type="button" data-d="1">+</button></div></div>`;
        if (s.kind === "knb")
            return `<div class="control knb n${s.num}" ${attrs} data-control="dial" data-widget="knob"><div class="knob"><div class="kin"></div></div>${head}</div>`;
        return `<div class="control sld n${s.num}" ${attrs} data-control="slider">${head}<div class="track"><div class="rail"></div><div class="fill"></div><div class="thumb"></div></div></div>`;
    }

    // <option> list of a dropdown, split into <optgroup>s when the spec defines groups
    optionsHTML (s) {
        if (!s.groups) return s.labels.map(l => `<option>${l}</option>`).join("");
        return s.groups.map((g, gi) => {
            const end = gi + 1 < s.groups.length ? s.groups[gi + 1][0] : s.labels.length;
            const opts = s.labels.slice(g[0], end).map(l => `<option>${l}</option>`).join("");
            return g[1] ? `<optgroup label="${g[1]}">${opts}</optgroup>` : opts;
        }).join("");
    }

    // FX rack page: 10 slots (any effect in any slot, drag the grip or use the arrows to change the order) + output strip
    fxPageHTML () {
        let racks = "";
        FX_RACKS.forEach((R, rk) => {
            let rows = "";
            for (let sl = 0; sl < 10; sl++) {
                const b = R.id + sl * 10;
                let ks = "";
                for (let k = 0; k < 6; k++) ks += this.controlHTML(b + 4 + k, true);
                rows += `<div class="fxrow empty" data-rack="${rk}" data-slot="${sl}" data-g="${rk * 10 + sl}">`
                    + `<div class="fxord"><button type="button" class="fxup" title="Move up">&#9650;</button><span class="fxpos">${sl + 1}</span><button type="button" class="fxdn" title="Move down">&#9660;</button></div>`
                    + `<div class="fxgrip" title="Drag to change the processing order">&#10303;</div>`
                    + `<div class="fxon">${this.controlHTML(b + 1)}</div>`
                    + `<div class="fxty">${this.controlHTML(b)}</div>`
                    + `<div class="fxmd">${this.controlHTML(b + 3)}</div>`
                    + `<div class="fxmx">${this.controlHTML(b + 2, true)}</div>`
                    + `<div class="fxps">${ks}</div></div>`;
            }
            let hid = "";
            for (let k = 0; k < 10; k++) hid += this.controlHTML(R.ord + k);
            racks += `<div class="fxlist f-rack" data-rack="${rk}">${rows}<div class="fx-hid">${hid}</div></div>`;
        });
        // tab order follows the signal: the buses feed Main
        const tabs = [1, 2, 0].map(rk => `<button type="button" class="fxtab" data-rack="${rk}">${FX_RACKS[rk].name}<i class="fxdot"></i></button>`).join("");
        const out = FX_OUT.map(i => `<div class="fxo">${this.controlHTML(i, true)}</div>`).join("");
        return `<section class="card f-main"><h2>FX <span class="fxtabs">${tabs}</span><span class="fxhint">Bus 1 + Bus 2 feed Main &middot; signal runs top to bottom</span></h2>${racks}</section>`
            + `<section class="card f-out"><h2>Output</h2><div class="fxoutrow">${out}</div></section>`;
    }

    card (title, ids, cls, extra, pre) {
        return `<section class="card ${cls || ""}"><h2>${title}</h2>${pre || ""}<div class="cgrid">${ids.map(i => this.controlHTML(i, true)).join("")}</div>${extra || ""}</section>`;
    }

    // ---------- modulation strip: envelopes, LFO shape editor, drag and drop modulation ----------
    envPanelHTML () {
        const chips = Array.from({ length: 10 }, (_, i) => `<button type="button" class="msrc" data-src="${11 + i}" title="Drag onto a knob to modulate it">ENV ${i + 1}</button>`).join("");
        const others = [21, 22, 23].map(n => `<button type="button" class="msrc misc" data-src="${n}" title="Drag onto a knob to modulate it">${MOD_SRC_SHORT(n)}</button>`).join("");
        let sets = "";
        for (let i = 0; i < 10; i++) {
            const b = 267 + 4 * i;
            sets += `<div class="env-set" data-env="${i}">${[0, 1, 2, 3].map(k => this.controlHTML(b + k, true)).join("")}</div>`;
        }
        return `<section class="bs-env"><div class="bs-chips">${chips}<span class="bs-gap"></span>${others}</div>`
            + `<div class="bs-envbody"><canvas class="env-canvas" width="360" height="130"></canvas><div class="env-knobs">${sets}</div></div></section>`;
    }

    lfoPanelHTML () {
        const chips = Array.from({ length: 10 }, (_, i) => `<button type="button" class="msrc" data-src="${1 + i}" title="Drag onto a knob to modulate it">LFO ${i + 1}</button>`).join("");
        const opts = LFO_PRESETS.map((p, i) => `<option value="${i}">${p.n}</option>`).join("") + `<option value="-1">Drawn</option>`;
        let sets = "";
        for (let i = 0; i < 10; i++) {
            sets += `<div class="lfo-set" data-lfo="${i}">`
                + `<div class="ls-top"><div class="ls-shape"><span class="lbl">Shape</span><select class="dd lfo-preset">${opts}</select></div>`
                + `<div class="ls-mode">${this.controlHTML(882 + 5 * i)}</div><div class="ls-sync">${this.controlHTML(502 + 2 * i)}</div><div class="ls-div">${this.controlHTML(503 + 2 * i)}</div></div>`
                + `<div class="ls-knobs">${[248 + 2 * i, 883 + 5 * i, 884 + 5 * i, 885 + 5 * i, 886 + 5 * i].map(id => this.controlHTML(id, true)).join("")}</div>`
                + `<div class="ls-hid">${this.controlHTML(247 + 2 * i)}</div></div>`;
        }
        return `<section class="bs-lfo"><div class="bs-chips">${chips}<span class="bs-gap"></span><button type="button" class="bs-btn lfo-grid" title="Grid snap">GRID OFF</button></div>`
            + `<div class="bs-lfobody"><div class="lfo-cv"><canvas class="lfo-canvas" width="640" height="150"></canvas><div class="lfo-help">click: add point &middot; drag: move &middot; dbl-click point: delete &middot; drag the diamond: curve</div></div>`
            + `<div class="lfo-sets">${sets}</div></div></section>`;
    }

    modStripHTML () {
        return `<div class="bstrip"><div class="bs-tabs"><button type="button" class="bst on" data-bs="mod">MOD</button><button type="button" class="bst" data-bs="mtx">MATRIX</button>`
            + `<span class="bs-hint">drag an LFO / ENV handle onto a knob &middot; click a knob's dot to set the amount</span><button type="button" class="bs-toggle" title="Show / hide the strip">&#9662;</button></div>`
            + `<div class="bs-body"><div class="bs-pane bs-mod on">${this.envPanelHTML()}${this.lfoPanelHTML()}</div><div class="bs-pane bs-mtx">${this.matrixHTML()}</div></div></div>`;
    }

    // ---- selection ----
    selectLfo (i) {
        this._lfoSel = i;
        this.querySelectorAll(".bs-lfo .msrc").forEach(c => c.classList.toggle("on", Number(c.dataset.src) === i + 1));
        this.querySelectorAll(".lfo-set").forEach(s => s.classList.toggle("on", Number(s.dataset.lfo) === i));
        this.refreshLfoUi(i);
        this.drawLfo();
    }
    selectEnv (i) {
        this._envSel = i;
        this.querySelectorAll(".bs-env .msrc:not(.misc)").forEach(c => c.classList.toggle("on", Number(c.dataset.src) === i + 11));
        this.querySelectorAll(".env-set").forEach(s => s.classList.toggle("on", Number(s.dataset.env) === i));
        this.drawEnv();
    }
    showStrip (which) {
        this._bs = which;
        this.querySelectorAll(".bst").forEach(b => b.classList.toggle("on", b.dataset.bs === which));
        this.querySelectorAll(".bs-pane").forEach(p => p.classList.toggle("on", p.classList.contains("bs-" + which)));
    }
    setStripOpen (open) {
        this._stripOpen = open;
        this.classList.toggle("strip-closed", !open);
        const t = this.querySelector(".bs-toggle");
        if (t) t.innerHTML = open ? "&#9662;" : "&#9652;";
        if (this._modReady) { try { this.kvSet("njo.ui.strip", open ? 1 : 0); } catch (_) {} }
        if (open) { this.drawLfo(); this.drawEnv(); }
    }

    // ---- LFO model ----
    lfoWave (i) { const c = this.fxCtl(247 + 2 * i); return c ? Math.round(c.value) : 0; }

    // the shape of LFO i as points (a built-in shape is converted the first time it is edited)
    lfoEnsurePts (i) {
        if (!this._lfoPts[i]) {
            const w = this.lfoWave(i);
            this._lfoPts[i] = lfoBuiltinPts(w >= LFO_DRAWN ? 0 : w).map(p => Object.assign({}, p));
        }
        return this._lfoPts[i];
    }

    lfoSend (i) {
        const pts = this._lfoPts[i];
        if (!pts) return;
        try { this.pc.sendEventOrValue("lfoShapeLoad", { lfo: i, data: lfoTableFromPts(pts) }); } catch (_) {}
    }

    // called after every edit of a drawn shape: table to the DSP, wave = Drawn, saved with the instance
    lfoCommit (i, final) {
        const w = this.fxCtl(247 + 2 * i);
        if (w && Math.round(w.value) !== LFO_DRAWN) w.setValue(LFO_DRAWN, true);
        if (final) {
            this.lfoSend(i);
            this.lfoPersist();
            if (this.presetDirty) this.presetDirty();
        } else if (!this._lfoSendTimer) {
            this._lfoSendTimer = setTimeout(() => { this._lfoSendTimer = null; this.lfoSend(i); }, 60);
        }
        this.refreshLfoUi(i);
        this.drawLfo();
    }

    lfoPersist () {
        try {
            const out = this._lfoPts.map(p => p ? p.map(q => ({ x: Math.round(q.x * 1e4) / 1e4, y: Math.round(q.y * 1e4) / 1e4, c: Math.round((q.c || 0) * 1e3) / 1e3 })) : null);
            this.kvSet(LFO_STATE_KEY, out);
        } catch (_) {}
    }

    // shapes in presets / stored state
    collectLfo () {
        return this._lfoPts.map(p => p ? p.map(q => ({ x: Math.round(q.x * 1e4) / 1e4, y: Math.round(q.y * 1e4) / 1e4, c: Math.round((q.c || 0) * 1e3) / 1e3 })) : null);
    }
    applyLfo (list) {
        const ok = p => Array.isArray(p) && p.length >= 2 && p.every(q => q && Number.isFinite(q.x) && Number.isFinite(q.y));
        for (let i = 0; i < 10; i++) {
            const p = list && ok(list[i]) ? list[i].map(q => ({ x: Math.max(0, Math.min(1, q.x)), y: Math.max(-1, Math.min(1, q.y)), c: Math.max(-1, Math.min(1, Number(q.c) || 0)) })) : null;
            this._lfoPts[i] = p;
            if (p) this.lfoSend(i);
        }
        this.lfoPersist();
        for (let i = 0; i < 10; i++) this.refreshLfoUi(i);
        this.drawLfo();
    }
    restoreLfo () {
        const v = this.kvGet(LFO_STATE_KEY);
        if (Array.isArray(v)) this.applyLfo(v);
    }

    // preset menu text, rate / division dimming
    refreshLfoUi (i) {
        const set = this.querySelector('.lfo-set[data-lfo="' + i + '"]');
        if (!set) return;
        const w = this.lfoWave(i);
        const sel = set.querySelector(".lfo-preset");
        if (sel) sel.value = w >= LFO_DRAWN || this._lfoPts[i] ? "-1" : String(w);
        const sync = this.fxCtl(502 + 2 * i);
        set.classList.toggle("synced", !!sync && sync.value > 0.5);
    }

    setLfoPreset (i, idx) {
        const w = this.fxCtl(247 + 2 * i);
        if (idx < 0) { this.lfoEnsurePts(i); this.lfoCommit(i, true); return; }
        const p = LFO_PRESETS[idx];
        if (p.w !== undefined) {
            this._lfoPts[i] = null;
            if (w) w.setValue(p.w, true);
            this.lfoPersist();
            if (this.presetDirty) this.presetDirty();
            this.refreshLfoUi(i); this.drawLfo();
        } else {
            this._lfoPts[i] = p.pts.map(q => Object.assign({}, q));
            this.lfoCommit(i, true);
        }
    }

    // ---- LFO canvas ----
    lfoGeom (cv) {
        const W = cv.width, H = cv.height, pad = 10;
        return { W, H, pad, px: x => pad + x * (W - 2 * pad), py: y => H / 2 - y * (H / 2 - pad), ix: X => (X - pad) / (W - 2 * pad), iy: Y => (H / 2 - Y) / (H / 2 - pad) };
    }

    drawLfo () {
        const cv = this.querySelector(".lfo-canvas");
        if (!cv || !this._stripOpen) return;
        const ctx = cv.getContext("2d");
        const g = this.lfoGeom(cv), i = this._lfoSel, w = this.lfoWave(i), pts = this._lfoPts[i];
        const drawn = !!pts || w >= LFO_DRAWN;
        const P = drawn ? this.lfoEnsurePts(i) : null;
        ctx.clearRect(0, 0, g.W, g.H);
        ctx.fillStyle = "#0b0405"; ctx.fillRect(0, 0, g.W, g.H);
        const grid = LFO_GRIDS[this._lfoGrid || 0], xs = grid || 8, ys = grid ? Math.max(2, grid / 2) : 4;
        ctx.lineWidth = 1;
        for (let k = 0; k <= xs; k++) { ctx.strokeStyle = k % (grid ? Math.max(1, xs / 4) : 2) === 0 ? "rgba(255,255,255,0.13)" : "rgba(255,255,255,0.05)"; const x = Math.round(g.px(k / xs)) + 0.5; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, g.H); ctx.stroke(); }
        for (let k = -ys; k <= ys; k++) { ctx.strokeStyle = k === 0 ? "rgba(255,255,255,0.22)" : "rgba(255,255,255,0.05)"; const y = Math.round(g.py(k / ys)) + 0.5; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(g.W, y); ctx.stroke(); }
        // curve
        const fn = drawn ? (p => lfoSampleAt(P, p)) : (p => lfoBuiltinAt(w, p));
        ctx.beginPath();
        for (let k = 0; k <= 400; k++) { const p = k / 400, X = g.px(p), Y = g.py(fn(p)); if (k === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y); }
        ctx.lineTo(g.px(1), g.py(0)); ctx.lineTo(g.px(0), g.py(0)); ctx.closePath();
        ctx.fillStyle = drawn ? "rgba(255,90,60,0.16)" : "rgba(160,160,170,0.10)"; ctx.fill();
        ctx.beginPath();
        for (let k = 0; k <= 400; k++) { const p = k / 400, X = g.px(p), Y = g.py(fn(p)); if (k === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y); }
        ctx.strokeStyle = drawn ? "#ff6a4d" : "#9a9aa2"; ctx.lineWidth = 2; ctx.stroke();
        if (drawn) {
            for (let k = 0; k + 1 < P.length; k++) {      // curve handles at the middle of every segment
                const a = P[k], b = P[k + 1];
                if (b.x - a.x < 0.02) continue;
                const mx = (a.x + b.x) / 2, my = lfoCurve(a.y, b.y, a.c || 0, 0.5);
                ctx.save(); ctx.translate(g.px(mx), g.py(my)); ctx.rotate(Math.PI / 4);
                ctx.fillStyle = "#2a1210"; ctx.strokeStyle = "#ffb09e"; ctx.lineWidth = 1.5; ctx.fillRect(-4, -4, 8, 8); ctx.strokeRect(-4, -4, 8, 8); ctx.restore();
            }
            P.forEach(q => { ctx.beginPath(); ctx.arc(g.px(q.x), g.py(q.y), 5.5, 0, 7); ctx.fillStyle = "#ffd9cf"; ctx.fill(); ctx.strokeStyle = "#ff3b30"; ctx.lineWidth = 2; ctx.stroke(); });
        } else {
            ctx.fillStyle = "rgba(255,255,255,0.35)"; ctx.font = "11px sans-serif"; ctx.fillText("built-in shape - click to draw your own", 14, g.H - 10);
        }
    }

    buildLfoCanvas () {
        const cv = this.querySelector(".lfo-canvas");
        if (!cv) return;
        let drag = null;
        const pos = e => { const r = cv.getBoundingClientRect(); return { X: (e.clientX - r.left) * cv.width / r.width, Y: (e.clientY - r.top) * cv.height / r.height }; };
        const snapX = x => { const gr = LFO_GRIDS[this._lfoGrid || 0]; return gr ? Math.round(x * gr) / gr : x; };
        const snapY = y => { const gr = LFO_GRIDS[this._lfoGrid || 0]; if (!gr) return y; const s = Math.max(2, gr / 2); return Math.round(y * s) / s; };
        const hit = (P, g, X, Y) => {
            for (let k = 0; k < P.length; k++) if (Math.hypot(g.px(P[k].x) - X, g.py(P[k].y) - Y) < 11) return { kind: "pt", k };
            for (let k = 0; k + 1 < P.length; k++) {
                const a = P[k], b = P[k + 1];
                if (b.x - a.x < 0.02) continue;
                if (Math.hypot(g.px((a.x + b.x) / 2) - X, g.py(lfoCurve(a.y, b.y, a.c || 0, 0.5)) - Y) < 10) return { kind: "cv", k };
            }
            return null;
        };
        cv.addEventListener("pointerdown", e => {
            const i = this._lfoSel, g = this.lfoGeom(cv), { X, Y } = pos(e);
            const P = this.lfoEnsurePts(i);
            let h = hit(P, g, X, Y);
            if (!h) {                                      // empty spot: new point
                const x = Math.max(0.004, Math.min(0.996, snapX(g.ix(X)))), y = Math.max(-1, Math.min(1, snapY(g.iy(Y))));
                let k = 0;
                while (k < P.length && P[k].x < x) k++;
                if (k === 0 || k >= P.length) return;
                const a = P[k - 1], b = P[k];
                P.splice(k, 0, { x, y, c: 0 });
                h = { kind: "pt", k };
                this.lfoCommit(i, false);
            }
            drag = { pid: e.pointerId, h, y0: Y, c0: h.kind === "cv" ? (P[h.k].c || 0) : 0 };
            try { cv.setPointerCapture(e.pointerId); } catch (_) {}
            e.preventDefault();
        });
        cv.addEventListener("pointermove", e => {
            if (!drag || e.pointerId !== drag.pid) return;
            const i = this._lfoSel, g = this.lfoGeom(cv), P = this.lfoEnsurePts(i), { X, Y } = pos(e), h = drag.h;
            if (h.kind === "pt") {
                const q = P[h.k];
                q.y = Math.max(-1, Math.min(1, snapY(g.iy(Y))));
                if (h.k > 0 && h.k < P.length - 1) q.x = Math.max(P[h.k - 1].x + 0.002, Math.min(P[h.k + 1].x - 0.002, snapX(g.ix(X))));
            } else {
                const a = P[h.k], b = P[h.k + 1], dir = Math.sign(b.y - a.y) || 1;
                a.c = Math.max(-1, Math.min(1, drag.c0 + (Y - drag.y0) / 70 * dir));
            }
            this.lfoCommit(i, false);
        });
        const end = e => {
            if (!drag || e.pointerId !== drag.pid) return;
            drag = null;
            try { cv.releasePointerCapture(e.pointerId); } catch (_) {}
            if (this._lfoSendTimer) { clearTimeout(this._lfoSendTimer); this._lfoSendTimer = null; }
            this.lfoCommit(this._lfoSel, true);
        };
        cv.addEventListener("pointerup", end);
        cv.addEventListener("pointercancel", end);
        cv.addEventListener("dblclick", e => {
            const i = this._lfoSel, g = this.lfoGeom(cv), P = this.lfoEnsurePts(i), { X, Y } = pos(e), h = hit(P, g, X, Y);
            if (!h) return;
            if (h.kind === "pt" && h.k > 0 && h.k < P.length - 1) P.splice(h.k, 1);
            else if (h.kind === "cv") P[h.k].c = 0;
            else return;
            this.lfoCommit(i, true);
        });
        const grid = this.querySelector(".lfo-grid");
        if (grid) grid.addEventListener("click", () => {
            this._lfoGrid = ((this._lfoGrid || 0) + 1) % LFO_GRIDS.length;
            grid.textContent = LFO_GRIDS[this._lfoGrid] ? "GRID 1/" + LFO_GRIDS[this._lfoGrid] : "GRID OFF";
            this.drawLfo();
        });
        this.querySelectorAll(".lfo-preset").forEach(sel => sel.addEventListener("change", () => {
            const set = sel.closest(".lfo-set");
            this.setLfoPreset(Number(set.dataset.lfo), Number(sel.value));
        }));
    }

    // ---- envelope canvas ----
    drawEnv () {
        const cv = this.querySelector(".env-canvas");
        if (!cv || !this._stripOpen) return;
        const ctx = cv.getContext("2d"), W = cv.width, H = cv.height, pad = 10, b = 267 + 4 * this._envSel;
        const v = k => { const c = this.fxCtl(b + k); return c ? c.value : 0; };
        const A = v(0), D = v(1), S = v(2), R = v(3);
        const t = ms => Math.sqrt(Math.max(ms, 0) / 5000);               // compressed time axis
        const seg = [Math.max(t(A), 0.03), Math.max(t(D), 0.05), 0.18, Math.max(t(R), 0.05)];
        const tot = seg[0] + seg[1] + seg[2] + seg[3];
        const X = f => pad + f / tot * (W - 2 * pad), Y = a => H - pad - a * (H - 2 * pad);
        ctx.fillStyle = "#0b0405"; ctx.fillRect(0, 0, W, H);
        ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 1;
        for (let k = 1; k < 4; k++) { ctx.beginPath(); ctx.moveTo(pad, Y(k / 4)); ctx.lineTo(W - pad, Y(k / 4)); ctx.stroke(); }
        const x1 = seg[0], x2 = x1 + seg[1], x3 = x2 + seg[2], x4 = x3 + seg[3];
        ctx.beginPath(); ctx.moveTo(X(0), Y(0)); ctx.lineTo(X(x1), Y(1));
        for (let k = 1; k <= 20; k++) { const f = k / 20; ctx.lineTo(X(x1 + seg[1] * f), Y(S + (1 - S) * Math.exp(-4 * f))); }
        ctx.lineTo(X(x3), Y(S));
        for (let k = 1; k <= 20; k++) { const f = k / 20; ctx.lineTo(X(x3 + seg[3] * f), Y(S * Math.exp(-4 * f))); }
        ctx.lineTo(X(x4), Y(0));
        const grad = ctx.createLinearGradient(0, 0, 0, H); grad.addColorStop(0, "rgba(77,184,255,0.30)"); grad.addColorStop(1, "rgba(77,184,255,0.03)");
        ctx.fillStyle = grad; ctx.fill();
        ctx.strokeStyle = "#4db8ff"; ctx.lineWidth = 2; ctx.stroke();
        ctx.fillStyle = "rgba(255,255,255,0.4)"; ctx.font = "11px sans-serif";
        ["A", "D", "S", "R"].forEach((l, k) => ctx.fillText(l, X([0, x1, x2, x3][k]) + 4, H - 14));
    }

    // ---- drag and drop modulation ----
    modTargetOf (node) {
        const c = node && node.closest ? node.closest(".control[data-param]") : null;
        if (!c) return null;
        const num = Number(String(c.dataset.param).replace("param", ""));
        const t = MOD_TARGET[num];
        return t ? { node: c, num, dst: t[0], scale: t[1] } : null;
    }

    modSlots () {
        const out = [];
        for (let s = 0; s < MOD_SLOTS; s++) {
            const a = this.fxCtl(slotBase(s)), b = this.fxCtl(slotBase(s) + 1), m = this.fxCtl(slotBase(s) + 2);
            out.push({ s, src: a ? Math.round(a.value) : 0, dst: b ? Math.round(b.value) : 0, amt: m ? m.value : 0 });
        }
        return out;
    }

    // creates or updates the matrix slot for (src, dst); returns the slot index or -1 when the matrix is full
    modAssign (src, dst, amt) {
        const slots = this.modSlots();
        let hit = slots.find(x => x.src === src && x.dst === dst);
        if (!hit) hit = slots.find(x => x.src === 0 || x.dst === 0);
        if (!hit) return -1;
        const set = (off, v) => { const c = this.fxCtl(slotBase(hit.s) + off); if (c) c.setValue(v, true); };
        if (hit.src !== src || hit.dst !== dst) { set(0, src); set(1, dst); set(2, amt); }
        else if (amt !== undefined && amt !== null) set(2, amt);
        return hit.s;
    }

    modClear (s) {
        const set = (off, v) => { const c = this.fxCtl(slotBase(s) + off); if (c) c.setValue(v, true); };
        set(2, 0); set(0, 0); set(1, 0);
    }

    modsFor (dst) { return this.modSlots().filter(x => x.src > 0 && x.dst === dst); }

    // modulation rings on the knobs / bars on the sliders that are mod targets
    updateModRings (onlyNum) {
        const nums = onlyNum ? [onlyNum] : Object.keys(MOD_TARGET).map(Number);
        nums.forEach(num => {
            const t = MOD_TARGET[num];
            if (!t) return;
            const ctl = this.fxCtl(num);
            if (!ctl || !ctl.node) return;
            const node = ctl.node, mods = this.modsFor(t[0]).filter(m => Math.abs(m.amt) > 0.0005);
            node.classList.toggle("modded", mods.length > 0);
            let ring = node.querySelector(".mring");
            let dot = node.querySelector(".mdot");
            if (!mods.length) { if (ring) ring.remove(); if (dot) dot.remove(); return; }
            const norm = ctl.toNorm ? ctl.toNorm(ctl.value) : (ctl.value - ctl.min) / ((ctl.max - ctl.min) || 1);
            const isKnob = !!node.querySelector(".knob");
            if (isKnob) {
                const host = node.querySelector(".knob");
                if (!ring) { ring = document.createElementNS("http://www.w3.org/2000/svg", "svg"); ring.setAttribute("class", "mring"); ring.setAttribute("viewBox", "-50 -50 100 100"); host.appendChild(ring); }
                const ang = n => (-135 + n * 270 - 90) * Math.PI / 180;
                const arc = (n0, n1, r, col) => {
                    const a0 = ang(n0), a1 = ang(n1), large = Math.abs(n1 - n0) * 270 > 180 ? 1 : 0, sweep = n1 >= n0 ? 1 : 0;
                    return `<path d="M ${r * Math.cos(a0)} ${r * Math.sin(a0)} A ${r} ${r} 0 ${large} ${sweep} ${r * Math.cos(a1)} ${r * Math.sin(a1)}" stroke="${col}" stroke-width="5" fill="none" stroke-linecap="round" opacity="0.95"/>`;
                };
                ring.innerHTML = mods.slice(0, 3).map((m, k) => arc(norm, Math.max(0, Math.min(1, norm + m.amt * t[1])), 54 + k * 0, MOD_SRC_COLOR(m.src))).join("");
            } else {
                const track = node.querySelector(".track");
                if (track) {
                    if (!ring) { ring = document.createElement("div"); ring.className = "mring mbar"; track.appendChild(ring); }
                    const m = mods[0], a = Math.max(0, Math.min(1, norm)), b = Math.max(0, Math.min(1, norm + m.amt * t[1]));
                    ring.style.left = (Math.min(a, b) * 100) + "%"; ring.style.width = (Math.abs(b - a) * 100) + "%"; ring.style.background = MOD_SRC_COLOR(m.src);
                }
            }
            if (!dot) { dot = document.createElement("button"); dot.type = "button"; dot.className = "mdot"; dot.title = "Modulation amount"; node.appendChild(dot); dot.addEventListener("pointerdown", e => e.stopPropagation()); dot.addEventListener("click", e => { e.stopPropagation(); this.showModPop(node, num); }); }
            dot.style.background = MOD_SRC_COLOR(mods[0].src);
            dot.textContent = mods.length > 1 ? String(mods.length) : "";
        });
    }

    closeModPop () { if (this._modPop) { this._modPop.remove(); this._modPop = null; } }

    showModPop (node, num) {
        this.closeModPop();
        const t = MOD_TARGET[num];
        if (!t) return;
        const mods = this.modsFor(t[0]).filter(m => m.src > 0);
        if (!mods.length) return;
        const pop = document.createElement("div");
        pop.className = "modpop";
        const label = (SPEC_BY_NUM.get(num) || {}).short || (SPEC_BY_NUM.get(num) || {}).label || "";
        pop.innerHTML = `<div class="mp-title">${label} modulation</div>` + mods.map(m => `<div class="mp-row" data-s="${m.s}"><span class="mp-src" style="background:${MOD_SRC_COLOR(m.src)}">${MOD_SRC_SHORT(m.src)}</span>`
            + `<input type="range" min="-100" max="100" step="1" value="${Math.round(m.amt * 100)}"><span class="mp-val">${Math.round(m.amt * 100)}%</span><button type="button" class="mp-x" title="Remove">&times;</button></div>`).join("");
        this.appendChild(pop);
        const hb = this.getBoundingClientRect(), nb = node.getBoundingClientRect();
        const left = Math.max(4, Math.min(hb.width - pop.offsetWidth - 4, nb.left - hb.left + nb.width / 2 - pop.offsetWidth / 2));
        const top = nb.top - hb.top + nb.height + 6;
        pop.style.left = left + "px";
        pop.style.top = Math.min(hb.height - pop.offsetHeight - 4, top) + "px";
        pop.addEventListener("pointerdown", e => e.stopPropagation());
        pop.querySelectorAll(".mp-row").forEach(row => {
            const s = Number(row.dataset.s), rng = row.querySelector("input"), val = row.querySelector(".mp-val");
            rng.addEventListener("input", () => { const a = Number(rng.value) / 100; val.textContent = Math.round(a * 100) + "%"; const c = this.fxCtl(slotBase(s) + 2); if (c) c.setValue(a, true); });
            row.querySelector(".mp-x").addEventListener("click", () => { this.modClear(s); this.closeModPop(); });
        });
        this._modPop = pop;
        this._modPopClose = e => { if (!pop.contains(e.target)) { this.closeModPop(); this.removeEventListener("pointerdown", this._modPopClose, true); } };
        setTimeout(() => this.addEventListener("pointerdown", this._modPopClose, true), 0);
    }

    buildModDrag () {
        this.querySelectorAll(".msrc").forEach(chip => {
            let st = null;
            chip.addEventListener("pointerdown", e => {
                st = { pid: e.pointerId, x: e.clientX, y: e.clientY, drag: false, ghost: null, target: null };
                try { chip.setPointerCapture(e.pointerId); } catch (_) {}
            });
            chip.addEventListener("pointermove", e => {
                if (!st || e.pointerId !== st.pid) return;
                const src = Number(chip.dataset.src);
                if (!st.drag && Math.hypot(e.clientX - st.x, e.clientY - st.y) > 5) {
                    st.drag = true;
                    st.ghost = document.createElement("div");
                    st.ghost.className = "mod-ghost";
                    st.ghost.textContent = MOD_SRC_SHORT(src);
                    st.ghost.style.background = MOD_SRC_COLOR(src);
                    this.appendChild(st.ghost);
                    this.classList.add("modding");
                    this.closeModPop();
                }
                if (!st.drag) return;
                const hb = this.getBoundingClientRect();
                st.ghost.style.left = (e.clientX - hb.left + 10) + "px";
                st.ghost.style.top = (e.clientY - hb.top + 10) + "px";
                st.ghost.style.pointerEvents = "none";
                const el = this.ownerDocument.elementFromPoint(e.clientX, e.clientY);
                const tg = this.modTargetOf(el);
                if (st.target && (!tg || tg.node !== st.target.node)) st.target.node.classList.remove("modhover");
                if (tg) tg.node.classList.add("modhover");
                st.target = tg;
            });
            const end = e => {
                if (!st || e.pointerId !== st.pid) return;
                const s = st; st = null;
                try { chip.releasePointerCapture(e.pointerId); } catch (_) {}
                const src = Number(chip.dataset.src);
                if (s.ghost) s.ghost.remove();
                this.classList.remove("modding");
                if (s.target) s.target.node.classList.remove("modhover");
                if (s.drag) {
                    if (s.target) {
                        const slot = this.modAssign(src, s.target.dst, 0.5);
                        if (slot < 0) this.barInfo && this.barInfo("MOD MATRIX FULL (20 SLOTS)");
                        else { this.updateModRings(); this.showModPop(s.target.node, s.target.num); }
                    }
                } else if (src >= 1 && src <= 10) { this.selectLfo(src - 1); }
                else if (src >= 11 && src <= 20) { this.selectEnv(src - 11); }
            };
            chip.addEventListener("pointerup", end);
            chip.addEventListener("pointercancel", end);
        });
    }

    buildModStrip () {
        this._lfoSel = 0; this._envSel = 0;
        this.querySelectorAll(".bst").forEach(b => b.addEventListener("click", () => {
            if (this._stripOpen && this._bs === b.dataset.bs && false) return;
            this.showStrip(b.dataset.bs);
            if (!this._stripOpen) this.setStripOpen(true);
        }));
        const tg = this.querySelector(".bs-toggle");
        if (tg) tg.addEventListener("click", () => this.setStripOpen(!this._stripOpen));
        let open = true;
        this.buildLfoCanvas();
        this.buildModDrag();
        this.showStrip("mod");
        this.setStripOpen(open);
        this.selectLfo(0);
        this.selectEnv(0);
        for (let i = 0; i < 10; i++) this.refreshLfoUi(i);
        this.updateModRings();
    }

    // mod page: the 20-slot modulation matrix, two columns of 10 slots
    matrixHTML () {
        const head = `<div class="mhead mtx-c"><span></span><span>Source</span><span>Destination</span><span>Amount</span></div>`;
        const cols = [0, 1].map(c => {
            let mtx = head;
            for (let k = 0; k < 10; k++) {
                const i = c * 10 + k;
                const m = slotBase(i);
                mtx += `<div class="mrow mtx-c" data-slot="${i}"><span class="mn">${i + 1}</span>${this.controlHTML(m)}${this.controlHTML(m + 1)}${this.controlHTML(m + 2)}</div>`;
            }
            return `<div class="mgrid">${mtx}</div>`;
        }).join("");
        return `<div class="mtx2">${cols}</div>`;
    }

    getHTML () {
        const oscPages = Array.from({ length: OSC_N }, (_, o) => `<div class="page p-o${o}" data-src="0">${this.oscPageHTML(o)}</div>`).join("\n    ");
        const fxPage = this.fxPageHTML();
        const strip = this.modStripHTML();
        return `
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; } body, html { overflow: hidden; margin: 0; height: 100%; }
  eisenpuls-view {
    --u: 1px; display: block; width: 100%; height: 100%; overflow: hidden;
    --bg: #0a0c0d; --panel: #1b1c1e; --panel2: #26272a; --steel: #3a3b3e; --ink: #ddd6d2; --dim: #8f8886;
    --line: #4a4a4d; --deep: #0b0404; --yel: #ff3b30; --org: #ff7a45; --glow: rgba(255,59,48,0.55);
    --hz: linear-gradient(90deg, transparent, #7a100c 12%, #ff3b30 50%, #7a100c 88%, transparent);
    font-family: "Bahnschrift", "Arial Narrow", "Roboto Condensed", "Segoe UI", Arial, sans-serif; color: var(--ink);
    background: var(--bg) repeating-linear-gradient(45deg, rgba(255,255,255,0.022) 0 2px, transparent 2px 7px);
    user-select: none; -webkit-user-select: none;
  }
  .shell { width: 100%; height: 100%; display: flex; flex-direction: column; gap: calc(var(--u) * 6); padding: calc(var(--u) * 8) calc(var(--u) * 10); overflow: hidden; }
  .top { display: flex; align-items: center; gap: calc(var(--u) * 8); min-width: 0; flex: 0 0 auto; padding: calc(var(--u) * 5) calc(var(--u) * 14); border-radius: calc(var(--u) * 2);
         background: linear-gradient(#2c3035, #1b1d20); border: 2px solid var(--line); box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 2px 6px rgba(0,0,0,0.6); }
  .logo { font-weight: 900; font-size: calc(var(--u) * 19); letter-spacing: 0.12em; color: var(--yel); text-transform: uppercase; text-shadow: 0 2px 0 #000; font-family: Impact, "Arial Black", "Bahnschrift", sans-serif; }
  .model { font-weight: 800; font-size: calc(var(--u) * 10); letter-spacing: 0.3em; color: #111; background: var(--yel); padding: calc(var(--u) * 2) calc(var(--u) * 9); border-radius: 1px; }
  .version { flex: 0 0 auto; align-self: center; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 8); font-weight: 700; letter-spacing: 0.08em; color: var(--dim); border: 1px solid var(--line); padding: calc(var(--u) * 2) calc(var(--u) * 5); border-radius: 2px; }
  .tabs { display: flex; gap: calc(var(--u) * 3); flex: 0 0 auto; }
  .tab { font-family: inherit; font-size: calc(var(--u) * 9.5); font-weight: 800; letter-spacing: 0.06em; padding: calc(var(--u) * 5) calc(var(--u) * 7); border: 1px solid var(--line); border-radius: 1px; background: var(--panel2); color: var(--ink); cursor: pointer; white-space: nowrap; }
  .tab.on { background: var(--yel); color: #111; border-color: var(--yel); }
  .sub { font-size: calc(var(--u) * 8.5); letter-spacing: 0.14em; color: var(--dim); text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex: 0 1 auto; }
  .vu { width: calc(var(--u) * 36); height: calc(var(--u) * 8); border-radius: 1px; background: var(--deep); overflow: hidden; flex: 0 0 auto; border: 1px solid var(--line); }
  .vu-fill { height: 100%; width: 0%; background: linear-gradient(90deg, var(--yel), var(--org)); }
  .lcd { margin-left: auto; display: flex; align-items: baseline; gap: calc(var(--u) * 10); padding: calc(var(--u) * 4) calc(var(--u) * 12); border-radius: 1px;
         background: #110505; border: 1px solid var(--line); box-shadow: inset 0 0 8px rgba(0,0,0,0.9);
         font-family: ui-monospace, Menlo, Consolas, monospace; color: var(--yel); white-space: nowrap; flex: 0 0 auto; }
  .lcd-mode { font-size: calc(var(--u) * 9); opacity: 0.7; letter-spacing: 0.1em; }
  .lcd-name { font-size: calc(var(--u) * 11); font-weight: 700; min-width: calc(var(--u) * 90); white-space: nowrap; }
  .lcd-val { font-size: calc(var(--u) * 12); min-width: calc(var(--u) * 52); white-space: nowrap; text-align: right; color: var(--org); }
  .led { width: calc(var(--u) * 11); height: calc(var(--u) * 11); border-radius: 50%; background: #2a1408; border: 2px solid #777; flex: 0 0 auto; }
  .led.on { background: var(--org); box-shadow: 0 0 12px var(--org); }
  .hz { flex: 0 0 auto; height: calc(var(--u) * 5); background: var(--hz); border-top: 1px solid #000; border-bottom: 1px solid #000; opacity: 0.9; }

  .stage { flex: 1 1 0; min-height: 0; position: relative; }
  .page { position: absolute; inset: 0; display: none; gap: calc(var(--u) * 6); min-height: 0; }
  eisenpuls-view[data-page="o0"] .p-o0 { display: grid; }
  eisenpuls-view[data-page="o1"] .p-o1 { display: grid; }
  eisenpuls-view[data-page="o2"] .p-o2 { display: grid; }
  eisenpuls-view[data-page="o3"] .p-o3 { display: grid; }
  eisenpuls-view[data-page="o4"] .p-o4 { display: grid; }
  eisenpuls-view[data-page="o5"] .p-o5 { display: grid; }
  eisenpuls-view[data-page="fm"] .p-fm { display: grid; }
  eisenpuls-view[data-page="glob"] .p-glob { display: grid; }
  eisenpuls-view[data-page="fx"] .p-fx { display: grid; }

  .card { position: relative; background: linear-gradient(#292c31, #1f2225); border: 1px solid var(--line); border-radius: calc(var(--u) * 2);
          padding: calc(var(--u) * 9) calc(var(--u) * 12) calc(var(--u) * 10); min-height: 0; min-width: 0; overflow: hidden; display: flex; flex-direction: column;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 2px 5px rgba(0,0,0,0.5); }
  .card::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: calc(var(--u) * 4); background: var(--hz); }
  .card::after { content: ""; position: absolute; inset: 0; pointer-events: none;
          background:
            radial-gradient(circle at calc(var(--u) * 6) calc(100% - var(--u) * 6), #9aa0a8 0 calc(var(--u) * 1.4), #17181a calc(var(--u) * 2.2), transparent calc(var(--u) * 2.8)),
            radial-gradient(circle at calc(100% - var(--u) * 6) calc(100% - var(--u) * 6), #9aa0a8 0 calc(var(--u) * 1.4), #17181a calc(var(--u) * 2.2), transparent calc(var(--u) * 2.8)); }
  .card h2 { font-size: calc(var(--u) * 10); letter-spacing: 0.24em; text-transform: uppercase; color: var(--yel); margin-bottom: calc(var(--u) * 3); font-weight: 900; display: flex; align-items: center; gap: calc(var(--u) * 6); flex: 0 0 auto; white-space: nowrap; font-family: Impact, "Arial Black", "Bahnschrift", sans-serif; }
  .card h2::before { content: ""; width: calc(var(--u) * 7); height: calc(var(--u) * 7); background: var(--yel); flex: 0 0 auto; }
  .card h2::after { content: ""; flex: 1; height: 2px; background: repeating-linear-gradient(90deg, var(--line) 0 4px, transparent 4px 7px); }
  .cgrid { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr); align-content: space-between; align-items: end; gap: calc(var(--u) * 2) calc(var(--u) * 12); }

  .mgr-status, .wt-status, .s2-status { flex: 0 0 auto; margin-top: calc(var(--u) * 6); padding: calc(var(--u) * 4) calc(var(--u) * 6); border: 1px solid var(--line); border-radius: 1px; background: #110505; box-shadow: inset 0 0 6px rgba(0,0,0,0.9);
  /* mod page */
  .p-lfo, .p-env, .p-mod { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 1fr); }
  .m-lfo { grid-column: 2 / span 10; grid-row: 1; }
  .m-env { grid-column: 1 / span 12; grid-row: 1; }
  .m-mtx { grid-column: 1 / span 12; grid-row: 1; }
  .mtx2 { flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: calc(var(--u) * 14); }
  .mgrid { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr); grid-template-rows: auto repeat(10, minmax(0, 1fr)); gap: calc(var(--u) * 2); padding-top: calc(var(--u) * 2); }
  .mhead, .mrow { display: grid; align-items: center; column-gap: calc(var(--u) * 8); min-width: 0; min-height: 0; }
  .mhead { font-size: calc(var(--u) * 8); font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; color: var(--dim); text-align: center; }
  .mrow { padding: 0 calc(var(--u) * 4); border: 1px solid transparent; border-radius: 1px; background: rgba(0,0,0,0.22); }
  .mrow.act { background: rgba(255,59,48,0.10); border-color: #8a1d18; }
  .mrow.act .mn { color: var(--org); }
  .mn { font-family: Impact, "Arial Black", "Bahnschrift", sans-serif; font-size: calc(var(--u) * 10); letter-spacing: 0.08em; color: var(--yel); text-align: center; }
  .lfo-c { grid-template-columns: calc(var(--u) * 24) minmax(0, 1.5fr) minmax(0, 1fr) minmax(0, 0.55fr) minmax(0, 0.6fr); }
  .lfoft { flex: 0 0 auto; width: 42%; margin-left: auto; padding: calc(var(--u) * 4) calc(var(--u) * 4) 0; }
  .s-lfo .n523, .s-lfo .n524 { min-width: 0; }
  .env-c { grid-template-columns: calc(var(--u) * 20) repeat(4, minmax(0, 1fr)); }
  .mtx-c { grid-template-columns: calc(var(--u) * 18) minmax(0, 1.1fr) minmax(0, 1.3fr) minmax(0, 0.9fr); }
  .mrow .lbl { display: none; }
  .mrow .btns .row { display: none; }
  .mrow .btns .grp button { padding: calc(var(--u) * 7) 0; font-size: calc(var(--u) * 10); }
  .p-lfo .mrow .val, .p-env .mrow .val { font-size: calc(var(--u) * 10); }
  .p-lfo .mhead, .p-env .mhead { font-size: calc(var(--u) * 9); }
  .p-lfo .mn, .p-env .mn { font-size: calc(var(--u) * 12); }
  .mrow .row { justify-content: center; }
  .mrow .val { font-size: calc(var(--u) * 8.5); }
  .mrow .track { height: calc(var(--u) * 12); }
  .mrow .sel { display: block; min-width: 0; }
  .mrow .sel .row { display: none; }
  .dd { display: block; width: 100%; min-width: 0; height: calc(var(--u) * 26); padding: 0 calc(var(--u) * 22) 0 calc(var(--u) * 8); border: 1px solid #000; border-radius: 1px; cursor: pointer;
        font-family: inherit; font-size: calc(var(--u) * 12); font-weight: 800; letter-spacing: 0.02em; color: var(--ink); outline: none;
        -webkit-appearance: none; appearance: none; color-scheme: dark;
        background-color: #3a3f46;
        background-image: linear-gradient(45deg, transparent 50%, var(--yel) 50%), linear-gradient(135deg, var(--yel) 50%, transparent 50%), linear-gradient(#4a5058, #30343a);
        background-position: calc(100% - var(--u) * 13) 55%, calc(100% - var(--u) * 7) 55%, 0 0;
        background-size: calc(var(--u) * 6) calc(var(--u) * 6), calc(var(--u) * 6) calc(var(--u) * 6), 100% 100%; background-repeat: no-repeat;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.18); }
  .dd:hover { color: #fff; }
  .dd:focus { border-color: var(--yel); }
  .dd option { background: #23262a; color: var(--ink); font-size: calc(var(--u) * 14); font-weight: 700; }
  .dd optgroup { background: #15171a; color: var(--yel); font-size: calc(var(--u) * 11); font-style: normal; }
  .mrow .stpr { display: flex; align-items: center; gap: calc(var(--u) * 2); }
  .mrow .stpr .grp { display: contents; }
  .mrow .stpr .row { order: 1; flex: 1 1 0; min-width: 0; }
  .mrow .stpr .grp button { flex: 0 0 auto; width: calc(var(--u) * 16); height: calc(var(--u) * 16); padding: 0; font-size: calc(var(--u) * 10); }
  .mrow .stpr .grp button:first-child { order: 0; }
  .mrow .stpr .grp button:last-child { order: 2; }

  .memgrid { flex: 0 0 auto; display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: calc(var(--u) * 2); margin-top: calc(var(--u) * 4); }
  .mc { height: calc(var(--u) * 12); padding: 0; border: 1px solid #000; border-radius: 1px; background: linear-gradient(#3a3f46, #2a2d32); color: var(--dim);
        font-family: inherit; font-size: calc(var(--u) * 7); font-weight: 800; cursor: pointer; }
  .mc:hover { background: linear-gradient(#4a5058, #34383e); }
  .mc.has { color: var(--yel); background: linear-gradient(#4a1c1a, #2f1311); }
  .mc.sel { background: var(--yel); color: #111; box-shadow: inset 0 0 5px rgba(0,0,0,0.35); }

  .dz { flex: 0 0 auto; margin-top: calc(var(--u) * 4); height: calc(var(--u) * 22); border: 2px dashed var(--line); border-radius: 1px; display: flex; align-items: center; justify-content: center; position: relative; cursor: pointer;
        background: var(--deep); font-size: calc(var(--u) * 8); font-weight: 700; letter-spacing: 0.08em; color: var(--dim); text-align: center; padding: 0 calc(var(--u) * 18); }
  .dz-txt { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .dz:hover, .dz.over { border-color: var(--yel); color: var(--yel); background: rgba(255,59,48,0.1); }
  .dz.busy { border-style: solid; border-color: var(--org); color: var(--org); }
  .dz.loaded { border-style: solid; border-color: var(--yel); color: var(--yel); background: rgba(255,59,48,0.08); }
  .dz.err { border-style: solid; border-color: #d33; color: #f66; }
  .dz-clr { position: absolute; right: calc(var(--u) * 6); top: 50%; transform: translateY(-50%); font-size: calc(var(--u) * 14); color: var(--ink); line-height: 1; padding: 0 calc(var(--u) * 3); }
  .dz-clr:hover { color: var(--org); }

  /* mixer page */
        background: linear-gradient(#1b1d20, #141517); border: 1px solid var(--line); border-radius: 1px; box-shadow: inset 0 0 8px rgba(0,0,0,0.7); }
  .ftrack { position: relative; flex: 1 1 0; min-height: 0; margin-bottom: calc(var(--u) * 8); width: 100%; cursor: ns-resize; touch-action: none; }
  .frail { position: absolute; left: 50%; top: 0; bottom: 0; width: calc(var(--u) * 8); margin-left: calc(var(--u) * -4); background: var(--deep); border: 1px solid #000; border-radius: 1px;
           box-shadow: inset 0 1px 3px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.06); pointer-events: none;
           background-image: repeating-linear-gradient(0deg, transparent 0 calc(var(--u) * 14), rgba(255,255,255,0.12) calc(var(--u) * 14) calc(var(--u) * 15)); }
  .ffill { position: absolute; left: 50%; width: calc(var(--u) * 5); margin-left: calc(var(--u) * -2.5); bottom: 0; height: 0; background: linear-gradient(0deg, var(--yel), var(--org)); pointer-events: none; }
  .fthumb { position: absolute; left: 50%; bottom: 0; width: calc(var(--u) * 36); height: calc(var(--u) * 16); margin: 0 0 calc(var(--u) * -8) calc(var(--u) * -18); border: 1px solid #000; border-radius: 1px;
            background: linear-gradient(#7a8089 0 38%, var(--yel) 38% 62%, #5a6068 62%); box-shadow: 0 2px 5px rgba(0,0,0,0.8); pointer-events: none; }

  /* SSL 4000 style channel EQ (rotary knobs) */
  .control.knb { display: flex; flex-direction: column; align-items: center; gap: calc(var(--u) * 3); width: 100%; }
  .knob { position: relative; width: min(100%, calc(var(--u) * 30)); aspect-ratio: 1 / 1; height: auto; border-radius: 50%; cursor: ns-resize; touch-action: none;
          background: radial-gradient(circle at 35% 30%, #6a717b 0, #3a3f46 45%, #1d1f23 100%);
          border: 1px solid #000; box-shadow: 0 2px 4px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.22), 0 0 0 calc(var(--u) * 2) #14151a; }
  .knob:hover { box-shadow: 0 2px 4px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.3), 0 0 0 calc(var(--u) * 2) #4a1a16; }
  .kin { position: absolute; inset: 0; border-radius: 50%; pointer-events: none; transform: rotate(0deg); }
  .kin::before { content: ""; position: absolute; left: 50%; top: calc(var(--u) * 2.5); width: calc(var(--u) * 3); height: calc(var(--u) * 9); margin-left: calc(var(--u) * -1.5); background: var(--yel); border-radius: 1px; box-shadow: 0 0 3px rgba(255,59,48,0.7); }
  .control.knb.drag .knob { box-shadow: 0 2px 4px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.3), 0 0 0 calc(var(--u) * 2) var(--org); }
  .control.knb .row { justify-content: center; gap: 0; }
  .control.knb .lbl { font-size: calc(var(--u) * 8.5); letter-spacing: 0.06em; color: #d6cdc9; }
  .control.knb .val { display: none; font-size: calc(var(--u) * 8.5); color: var(--org); }
  .control.knb.drag .lbl { display: none; }
  .control.knb.drag .val { display: block; }

  /* fx page: the rack */
  .p-fx { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr) auto; }
  .f-main { grid-column: 1; grid-row: 1; min-height: 0; }
  .f-rack { display: none; }
  .f-rack.on { display: flex; }
  .fxtabs { display: inline-flex; gap: calc(var(--u) * 4); margin-left: calc(var(--u) * 4); font-family: "Bahnschrift", "Arial Narrow", sans-serif; }
  .fxtab { font-family: inherit; font-size: calc(var(--u) * 9.5); font-weight: 800; letter-spacing: 0.08em; padding: calc(var(--u) * 3) calc(var(--u) * 10); border: 1px solid var(--line); border-radius: 1px; background: var(--panel2); color: var(--ink); cursor: pointer; display: inline-flex; align-items: center; gap: calc(var(--u) * 5); text-transform: uppercase; }
  .fxtab.on { background: var(--yel); color: #111; border-color: var(--yel); }
  .fxdot { width: calc(var(--u) * 6); height: calc(var(--u) * 6); border-radius: 50%; background: transparent; }
  .fxtab.used .fxdot { background: var(--org); box-shadow: 0 0 5px var(--org); }
  .fxtab.on.used .fxdot { background: #111; box-shadow: none; }
  .f-out { grid-column: 1; grid-row: 2; }
  .fxhint { font-size: calc(var(--u) * 8); letter-spacing: 0.12em; color: var(--dim); font-weight: 700; font-family: "Bahnschrift", "Arial Narrow", sans-serif; }
  .fxlist { flex: 1; min-height: 0; flex-direction: column; gap: calc(var(--u) * 2); }
  .fxrow { flex: 1 1 0; min-height: 0; display: grid; align-items: center; column-gap: calc(var(--u) * 8); padding: 0 calc(var(--u) * 6);
           grid-template-columns: calc(var(--u) * 34) calc(var(--u) * 18) calc(var(--u) * 34) calc(var(--u) * 112) calc(var(--u) * 92) calc(var(--u) * 74) minmax(0, 1fr);
           background: rgba(0,0,0,0.34); border: 1px solid transparent; border-radius: calc(var(--u) * 4) 1px calc(var(--u) * 4) 1px; position: relative; }
  .fxrow:not(.empty) { background: rgba(255,59,48,0.07); border-color: #5b1a16; }
  .fxrow.off { opacity: 0.45; }
  .fxrow.dragging { z-index: 3; border-color: var(--org); box-shadow: 0 4px 14px rgba(0,0,0,0.7); opacity: 0.95; }
  .fxord { display: flex; align-items: center; justify-content: space-between; gap: calc(var(--u) * 1); }
  .fxord button { font-family: inherit; font-size: calc(var(--u) * 7); line-height: 1; padding: calc(var(--u) * 3) calc(var(--u) * 2); background: var(--panel2); color: var(--dim); border: 1px solid var(--line); border-radius: 1px; cursor: pointer; }
  .fxord button:hover { color: var(--yel); border-color: var(--yel); }
  .fxpos { font-family: Impact, "Arial Black", sans-serif; font-size: calc(var(--u) * 11); color: var(--yel); min-width: calc(var(--u) * 10); text-align: center; }
  .fxgrip { cursor: grab; text-align: center; font-size: calc(var(--u) * 16); line-height: 1; color: var(--dim); touch-action: none; }
  .fxgrip:hover { color: var(--yel); }
  .fxrow.dragging .fxgrip { cursor: grabbing; color: var(--org); }
  .fxon .control .row, .fxty .control .row, .fxmd .control .row { display: none; }
  .fxon .grp { display: flex; }
  .fxon .grp button { padding: calc(var(--u) * 5) calc(var(--u) * 3); font-size: calc(var(--u) * 8); }
  .fxty select, .fxmd select { width: 100%; }
  .fxrow.empty .fxmd, .fxrow.nomode .fxmd { visibility: hidden; }
  .fxrow.empty .fxon, .fxrow.empty .fxmx, .fxrow.empty .fxps { visibility: hidden; }
  .fxps { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); column-gap: calc(var(--u) * 6); min-width: 0; }
  .fxps .control.knb, .fxmx .control.knb { flex-direction: row; justify-content: flex-start; gap: calc(var(--u) * 4); width: auto; min-width: 0; }
  .fxps .control.knb .knob, .fxmx .control.knb .knob { width: calc(var(--u) * 24); flex: 0 0 auto; }
  .fxps .control.knb .row, .fxmx .control.knb .row { flex-direction: column; align-items: flex-start; justify-content: center; gap: 0; min-width: 0; }
  .fxps .control.knb .val, .fxmx .control.knb .val { display: block; font-size: calc(var(--u) * 8); }
  .fxps .control.knb .lbl, .fxmx .control.knb .lbl { font-size: calc(var(--u) * 7.5); }
  .fxps .control.knb.drag .lbl, .fxmx .control.knb.drag .lbl { display: block; }
  .fxps .control.knb.nop { visibility: hidden; }
  .fx-hid { display: none !important; }
  .fxoutrow { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: calc(var(--u) * 12); align-items: end; padding-top: calc(var(--u) * 2); }
  .fxo { min-width: 0; }
  .fxo .control.sel .row { display: none; }

  .control { min-width: 0; }
  .row { display: flex; justify-content: space-between; align-items: baseline; gap: calc(var(--u) * 4); }
  .lbl { font-size: calc(var(--u) * 8.5); font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
  .val { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 9.5); color: var(--yel); white-space: nowrap; flex: 0 0 auto; }
  .control.drag .lbl { color: var(--yel); }
  .track { position: relative; height: calc(var(--u) * 14); cursor: ew-resize; touch-action: none; }
  .rail { position: absolute; left: 0; right: 0; top: 50%; height: calc(var(--u) * 6); margin-top: calc(var(--u) * -3); border-radius: 1px; background: var(--deep); border: 1px solid #000; box-shadow: inset 0 1px 3px rgba(0,0,0,0.9), 0 1px 0 rgba(255,255,255,0.1); pointer-events: none; }
  .fill { position: absolute; top: 50%; height: calc(var(--u) * 4); margin-top: calc(var(--u) * -2); background: linear-gradient(90deg, var(--yel), var(--org)); pointer-events: none; }
  .thumb { position: absolute; top: 50%; width: calc(var(--u) * 10); height: calc(var(--u) * 14); margin: calc(var(--u) * -7) 0 0 calc(var(--u) * -5); border-radius: 1px; border: 1px solid #000;
           background: linear-gradient(90deg, #5a6068 0 35%, var(--yel) 35% 65%, #5a6068 65%); pointer-events: none; box-shadow: 0 2px 4px rgba(0,0,0,0.7); }
  .grp { display: flex; gap: calc(var(--u) * 2); margin-top: calc(var(--u) * 1); }
  .grp button { flex: 1; min-width: 0; font-size: calc(var(--u) * 8.5); font-weight: 800; letter-spacing: 0.04em; padding: calc(var(--u) * 3.5) 0; border: 1px solid #000; border-radius: 1px;
                background: linear-gradient(#4a5058, #30343a); color: var(--ink); cursor: pointer; font-family: inherit; box-shadow: inset 0 1px 0 rgba(255,255,255,0.18); }
  .grp button:hover { background: linear-gradient(#5a616a, #3a3f46); }
  .grp button:active { background: #23262a; }
  .grp button.on { background: var(--yel); color: #111; box-shadow: inset 0 0 6px rgba(0,0,0,0.35); }


  /* ===== bio-mechanical skin: gunmetal shells, red-lit controls ===== */
  eisenpuls-view {
    background:
      radial-gradient(ellipse at 6% 96%, rgba(28,96,74,0.30), transparent 42%),
      radial-gradient(ellipse at 96% 4%, rgba(130,18,14,0.28), transparent 48%),
      radial-gradient(ellipse at 50% 50%, rgba(255,255,255,0.025), transparent 70%),
      repeating-linear-gradient(115deg, rgba(255,255,255,0.012) 0 1px, transparent 1px 5px),
      #080a0b;
  }
  .top { border: 1px solid #55565a; border-radius: calc(var(--u) * 22) calc(var(--u) * 6) calc(var(--u) * 22) calc(var(--u) * 6);
         background: radial-gradient(ellipse at 20% 0%, rgba(255,255,255,0.10), transparent 55%), linear-gradient(#2a2b2e, #131415);
         box-shadow: inset 0 1px 0 rgba(255,255,255,0.14), inset 0 -8px 18px rgba(0,0,0,0.55), 0 3px 10px rgba(0,0,0,0.75), 0 0 14px rgba(255,59,48,0.10); }
  .logo { color: #d9d2cf; font-family: "Bahnschrift", "Arial Narrow", Impact, sans-serif; font-weight: 900; letter-spacing: 0.22em;
          text-shadow: 0 0 10px var(--glow), 0 2px 0 #000; }
  .model { color: #ffd9d4; background: linear-gradient(#a8180f, #5a0b07); border: 1px solid #ff3b30; box-shadow: 0 0 8px var(--glow); border-radius: calc(var(--u) * 6) 1px calc(var(--u) * 6) 1px; }
  .tab { background: linear-gradient(#303134, #17181a); border: 1px solid #4c4d51; border-radius: calc(var(--u) * 5) 1px calc(var(--u) * 5) 1px; color: var(--ink); box-shadow: inset 0 1px 0 rgba(255,255,255,0.12); }
  .tab:hover { border-color: #ff3b30; color: #fff; }
  .tab.on { background: linear-gradient(#ff4a3a, #a3140c); color: #fff; border-color: #ff6a5c; text-shadow: 0 1px 0 rgba(0,0,0,0.6); box-shadow: 0 0 10px var(--glow), inset 0 1px 0 rgba(255,255,255,0.35); }
  .vu { background: #0c0404; border-color: #5a1a16; box-shadow: inset 0 0 6px #000; }
  .vu-fill { background: linear-gradient(90deg, #7a100c, #ff3b30 70%, #ffb199); box-shadow: 0 0 8px var(--glow); }
  .lcd { background: #0e0303; border: 1px solid #6a1b16; border-radius: calc(var(--u) * 4); box-shadow: inset 0 0 12px rgba(0,0,0,0.95), 0 0 12px rgba(255,59,48,0.22); }
  .lcd-mode, .lcd-name, .lcd-val { text-shadow: 0 0 6px var(--glow); letter-spacing: 0.12em; }
  .lcd-val { color: #ff6d5e; }
  .led { background: #2a0707; border: 2px solid #6a6a6e; }
  .led.on { background: #ff3b30; box-shadow: 0 0 14px #ff3b30, 0 0 4px #fff inset; }
  .hz { height: calc(var(--u) * 3); background: var(--hz); border: 0; opacity: 1; box-shadow: 0 0 10px var(--glow); }

  .card { background:
            radial-gradient(ellipse at 15% 0%, rgba(255,255,255,0.075), transparent 50%),
            radial-gradient(ellipse at 90% 110%, rgba(140,20,16,0.20), transparent 55%),
            repeating-linear-gradient(100deg, rgba(255,255,255,0.016) 0 1px, transparent 1px 4px),
            linear-gradient(#242527, #131415);
          border: 1px solid #505155; border-radius: calc(var(--u) * 26) calc(var(--u) * 6) calc(var(--u) * 20) calc(var(--u) * 6);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.10), inset 0 0 26px rgba(0,0,0,0.65), 0 3px 8px rgba(0,0,0,0.7); }
  .card:nth-child(even) { border-radius: calc(var(--u) * 6) calc(var(--u) * 24) calc(var(--u) * 6) calc(var(--u) * 20); }
  .card::before { left: 14%; right: 14%; height: calc(var(--u) * 2); background: var(--hz); box-shadow: 0 0 8px var(--glow); border-radius: 0 0 4px 4px; }
  .card::after { background:
            radial-gradient(circle at calc(var(--u) * 7) calc(100% - var(--u) * 7), #8c8d92 0 calc(var(--u) * 1.4), #121212 calc(var(--u) * 2.2), transparent calc(var(--u) * 2.8)),
            radial-gradient(circle at calc(100% - var(--u) * 7) calc(100% - var(--u) * 7), #ff6a5c 0 calc(var(--u) * 1.2), rgba(255,59,48,0.55) calc(var(--u) * 2.4), transparent calc(var(--u) * 4.6)); }
  .card h2 { font-family: "Bahnschrift", "Arial Narrow", Impact, sans-serif; letter-spacing: 0.3em; color: #e8dedb; text-shadow: 0 0 8px var(--glow); font-weight: 800; }
  .card h2::before { width: calc(var(--u) * 7); height: calc(var(--u) * 7); background: #ff3b30; transform: rotate(45deg); box-shadow: 0 0 8px #ff3b30; }
  .card h2::after { height: 1px; background: linear-gradient(90deg, rgba(255,59,48,0.7), rgba(255,59,48,0.05)); }

  .lbl { color: #d6cdc9; }
  .val { color: #ff6d5e; text-shadow: 0 0 5px rgba(255,59,48,0.45); }
  .rail { background: #090303; border: 1px solid #000; box-shadow: inset 0 1px 3px #000, 0 0 0 1px rgba(255,59,48,0.12); }
  .fill { background: linear-gradient(90deg, #8a120c, #ff3b30 70%, #ff9b86); box-shadow: 0 0 7px var(--glow); }
  .thumb { background: linear-gradient(90deg, #4a4b4f 0 30%, #ff3b30 30% 70%, #4a4b4f 70%); border: 1px solid #000; border-radius: 2px; box-shadow: 0 2px 4px rgba(0,0,0,0.85), 0 0 6px rgba(255,59,48,0.45); }
  .control.drag .thumb { box-shadow: 0 2px 4px #000, 0 0 12px #ff3b30; }
  .grp button { background: linear-gradient(#3a3b3e, #1a1b1d); color: #d6cdc9; border: 1px solid #000; border-radius: calc(var(--u) * 3) 1px calc(var(--u) * 3) 1px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.14); }
  .grp button:hover { background: linear-gradient(#4a4b4f, #222326); color: #fff; }
  .grp button.on { background: linear-gradient(#ff4a3a, #9d130b); color: #fff; text-shadow: 0 1px 0 rgba(0,0,0,0.55); box-shadow: 0 0 8px var(--glow), inset 0 1px 0 rgba(255,255,255,0.3); }
  .dd { background-color: #232427; background-image: linear-gradient(45deg, transparent 50%, #ff3b30 50%), linear-gradient(135deg, #ff3b30 50%, transparent 50%), linear-gradient(#35363a, #17181a);
        border: 1px solid #000; border-radius: calc(var(--u) * 4) 1px calc(var(--u) * 4) 1px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 0 0 1px rgba(255,59,48,0.12); }
  .dd:focus { box-shadow: 0 0 8px var(--glow); }
  .dd option { background: #1a1b1d; } .dd optgroup { background: #0d0e0f; }

  /* rotary knobs: toothed bezel, red pointer */
  .knob { isolation: isolate; background: radial-gradient(circle at 36% 30%, #7b7c82 0, #3d3e42 42%, #17181a 100%);
          box-shadow: 0 3px 5px rgba(0,0,0,0.9), inset 0 1px 0 rgba(255,255,255,0.25), 0 0 0 calc(var(--u) * 1.5) #0d0d0e; }
  .knob::before { content: ""; position: absolute; inset: calc(var(--u) * -4); border-radius: 50%; z-index: -1;
          background: repeating-conic-gradient(#0c0c0d 0 7deg, #5d5e63 7deg 15deg);
          -webkit-mask: radial-gradient(circle, transparent 0 66%, #000 68%); mask: radial-gradient(circle, transparent 0 66%, #000 68%); }
  .knob:hover { box-shadow: 0 3px 5px rgba(0,0,0,0.9), inset 0 1px 0 rgba(255,255,255,0.3), 0 0 0 calc(var(--u) * 1.5) #5a1a16; }
  .kin::before { background: #ff3b30; box-shadow: 0 0 6px #ff3b30, 0 0 2px #fff; width: calc(var(--u) * 2.5); }
  .control.knb.drag .knob { box-shadow: 0 3px 5px #000, 0 0 12px #ff3b30, 0 0 0 calc(var(--u) * 1.5) #ff3b30; }

  /* mixer */
  .frail { background-color: #080303; box-shadow: inset 0 1px 3px #000, 0 0 0 1px rgba(255,59,48,0.14); }
  .ffill { box-shadow: 0 0 8px var(--glow); }
  .fthumb { background: linear-gradient(#85868b 0 36%, #ff3b30 36% 64%, #4f5055 64%); box-shadow: 0 2px 5px #000, 0 0 8px rgba(255,59,48,0.5); border-radius: 2px; }

  /* waveform windows: HUD screen */
  .wt-canvas { background: #0d0404; border: 1px solid #7a1d18; border-radius: calc(var(--u) * 4);
        box-shadow: inset 0 0 14px rgba(0,0,0,0.95), 0 0 14px rgba(255,59,48,0.30); }
  .mrow { background: rgba(0,0,0,0.34); border-radius: calc(var(--u) * 4) 1px calc(var(--u) * 4) 1px; }
  .mrow.act { background: rgba(255,59,48,0.10); border-color: #8a1d18; box-shadow: 0 0 8px rgba(255,59,48,0.22); }
  .mn { font-family: "Bahnschrift", "Arial Narrow", Impact, sans-serif; color: #ff6d5e; text-shadow: 0 0 5px rgba(255,59,48,0.5); }
  .dz { background: #0d0404; border-color: #5a1a16; } .dz.err { border-color: #ff3b30; }
  .mc, .wc, .sc { background: linear-gradient(#303134, #17181a); border-radius: 2px; }
  .mc.sel, .wc.sel, .sc.sel { background: linear-gradient(#ff4a3a, #9d130b); color: #fff; box-shadow: 0 0 7px var(--glow); }

  /* knob grids (sound, filter, sampler, wavetable and FX pages) */
  .cgrid { --kc: 3; grid-template-columns: repeat(var(--kc), minmax(0, 1fr)); align-content: space-evenly; align-items: center; justify-items: stretch; gap: calc(var(--u) * 8) calc(var(--u) * 6); }
  .cgrid > .wide { grid-column: 1 / -1; }
  .cgrid > .w2 { grid-column: span 2; }
  .cgrid .control.knb { gap: calc(var(--u) * 6); }
  .cgrid .knob { width: min(100%, calc(var(--u) * 44)); margin: calc(var(--u) * 4) 0 0; }
  .cgrid .control.knb .lbl { font-size: calc(var(--u) * 9); letter-spacing: 0.08em; text-align: center; }
  .cgrid .control.knb .val { font-size: calc(var(--u) * 9); text-align: center; }
  .cgrid .control.knb .row { display: flex; justify-content: center; }
  .s-voice .cgrid, .s-amp .cgrid, .x-rt .cgrid, .w-uni .cgrid { --kc: 2; }
  .s-osc .cgrid, .s-lfo .cgrid, .s-ss .cgrid, .m-osc .cgrid, .s2-osc .cgrid, .w-osc .cgrid, .w-warp .cgrid { --kc: 4; }
  .s-osc .cgrid { --kc: 5; }
  .s-voice .cgrid, .s-amp .cgrid, .x-rt .cgrid, .w-uni .cgrid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .s-osc .cgrid, .s-lfo .cgrid, .s-ss .cgrid, .m-osc .cgrid, .s2-osc .cgrid, .w-osc .cgrid, .w-warp .cgrid, .x-f1 .cgrid, .x-f2 .cgrid, .x-feg .cgrid { grid-template-columns: repeat(var(--kc), minmax(0, 1fr)); }
  .s-osc .cgrid { grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .s-lfo .cgrid, .s-ss .cgrid, .m-osc .cgrid, .s2-osc .cgrid, .w-osc .cgrid, .w-warp .cgrid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .m-mem .cgrid { grid-template-columns: repeat(3, minmax(0, 1fr)); }

  .s-osc .cgrid, .s-lfo .cgrid, .s-ss .cgrid { --kc: 6; grid-template-columns: repeat(6, minmax(0, 1fr)); grid-auto-flow: row dense; gap: calc(var(--u) * 4) calc(var(--u) * 6); }
  .s-osc .cgrid > .wide, .s-lfo .cgrid > .wide, .s-ss .cgrid > .wide { grid-column: span 3; }
  .s-ss .cgrid > .n144, .s-ss .cgrid > .n141 { grid-column: span 3; }
  .cgrid .knob { width: min(100%, calc(var(--u) * 38)); margin-top: calc(var(--u) * 3); }
  .cgrid .control.knb { gap: calc(var(--u) * 4); }

  .w-warp .cgrid { --kc: 6; grid-template-columns: repeat(6, minmax(0, 1fr)); align-items: center; }
  .w-warp .cgrid > .wide { grid-column: span 2; }

  .m-osc .cgrid, .s2-osc .cgrid { --kc: 6; grid-template-columns: repeat(6, minmax(0, 1fr)); grid-auto-flow: row dense; gap: calc(var(--u) * 6) calc(var(--u) * 10); }
  .m-osc .cgrid > .wide, .s2-osc .cgrid > .wide { grid-column: span 3; }

  /* memory strip lives inside the oscillator cards */
  .m-osc, .s2-osc { grid-column: 1 / span 12; grid-row: 1; }
  .w-osc { grid-column: 1 / span 9; grid-row: 1; }
  .w-uni { grid-column: 10 / span 3; grid-row: 1; }
  .w-warp { grid-column: 1 / span 12; grid-row: 2; }
  .memstrip { flex: 0 0 auto; display: flex; align-items: stretch; gap: calc(var(--u) * 10); margin-top: calc(var(--u) * 6); padding: calc(var(--u) * 6); border: 1px solid var(--line); border-radius: 1px; background: rgba(0,0,0,0.25); box-shadow: inset 0 0 8px rgba(0,0,0,0.6); }
  .memstrip .ms-main { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
  .memstrip .dz { flex: 0 0 auto; height: calc(var(--u) * 38); min-height: 0; margin: 0; font-size: calc(var(--u) * 9); white-space: normal; text-align: center; padding: 0 calc(var(--u) * 16) 0 calc(var(--u) * 6); }
  .memstrip .dz-txt { white-space: normal; text-align: center; }
  .memstrip .mgr-status, .memstrip .s2-status, .memstrip .wt-status { font-size: calc(var(--u) * 7); margin-top: calc(var(--u) * 4); }
  .memstrip .ms-ctl { flex: 0 0 auto; display: flex !important; align-items: center; gap: calc(var(--u) * 8); margin: 0; }
  .memstrip .ms-ctl > * { flex: 0 0 auto; width: auto; min-width: calc(var(--u) * 70); }
  .memstrip .ms-hid { display: none !important; }
  .wt-top { flex: 0 0 auto; display: flex; gap: calc(var(--u) * 10); align-items: stretch; margin-top: calc(var(--u) * 6); }
  .wt-top .memstrip { flex: 0 0 44%; margin-top: 0; }
  .wt-top .wt-cv { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
  .wt-top .wt-canvas { height: calc(var(--u) * 54); margin-top: 0; }
  .w-osc .cgrid { --kc: 6; grid-template-columns: repeat(6, minmax(0, 1fr)); grid-auto-flow: row dense; gap: calc(var(--u) * 6) calc(var(--u) * 10); }
  .w-osc .cgrid > .wide { grid-column: span 3; }
  .w-osc .n212, .w-osc .n226, .w-osc .n238 { grid-column: span 6; }

  /* preset bar + library / preset manager windows */
  eisenpuls-view { position: relative; }
  .bar { flex: 0 0 auto; display: flex; align-items: center; gap: calc(var(--u) * 5); min-width: 0; padding: 0 calc(var(--u) * 6); height: calc(var(--u) * 24); }
  .bar-l { font-size: calc(var(--u) * 8); font-weight: 800; letter-spacing: 0.2em; color: var(--dim); }
  .bar-sp { flex: 1 1 auto; }
  .bar-info { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 8); letter-spacing: 0.08em; color: var(--org); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: calc(var(--u) * 420); text-shadow: 0 0 6px var(--glow); }
  .pb { font-family: inherit; font-size: calc(var(--u) * 8.5); font-weight: 800; letter-spacing: 0.08em; padding: calc(var(--u) * 3) calc(var(--u) * 8); border: 1px solid #4c4d51; border-radius: calc(var(--u) * 4) 1px calc(var(--u) * 4) 1px;
        background: linear-gradient(#303134, #17181a); color: var(--ink); cursor: pointer; white-space: nowrap; box-shadow: inset 0 1px 0 rgba(255,255,255,0.12); }
  .pb:hover { background: linear-gradient(#4a1c1a, #2a0f0d); border-color: #ff3b30; }
  .pb.arm { background: #a8180f; border-color: #ff6d5e; color: #fff; }
  .pb.on { background: linear-gradient(#a8180f, #5a0b07); border-color: #ff3b30; color: #fff; }
  .pb-name { flex: 0 0 auto; width: calc(var(--u) * 230); height: calc(var(--u) * 20); padding: 0 calc(var(--u) * 10); font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 10.5); letter-spacing: 0.1em; text-align: center; color: #ff6d5e; text-shadow: 0 0 6px var(--glow);
        background: #0e0303; border: 1px solid #6a1b16; border-radius: calc(var(--u) * 3); box-shadow: inset 0 0 10px rgba(0,0,0,0.95); cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .dz-lib { align-self: stretch; flex: 0 0 auto; }
  .mgr-ov { position: absolute; inset: 0; z-index: 50; display: none; align-items: center; justify-content: center; background: rgba(4,1,1,0.78); }
  .mgr-ov.on { display: flex; }
  .mgr-box { width: calc(var(--u) * 760); max-width: 96%; max-height: 94%; display: flex; flex-direction: column; gap: calc(var(--u) * 8); padding: calc(var(--u) * 12); background: linear-gradient(#232426, #121314); border: 1px solid #6a1b16; border-radius: calc(var(--u) * 6);
        box-shadow: 0 0 0 1px #000, 0 0 30px rgba(255,59,48,0.28), inset 0 1px 0 rgba(255,255,255,0.08); }
  .mgr-h { display: flex; align-items: center; justify-content: space-between; }
  .mgr-t { font-size: calc(var(--u) * 12); font-weight: 900; letter-spacing: 0.3em; color: var(--yel); text-shadow: 0 0 8px var(--glow); }
  .mgr-x { font-size: calc(var(--u) * 13); padding: 0 calc(var(--u) * 9); }
  .mgr-row { display: flex; align-items: center; gap: calc(var(--u) * 6); flex: 0 0 auto; }
  .mgr-in { flex: 1 1 auto; min-width: 0; height: calc(var(--u) * 22); padding: 0 calc(var(--u) * 8); font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 10); color: var(--ink); background: #0e0303; border: 1px solid #6a1b16; border-radius: calc(var(--u) * 2); outline: none; user-select: text; -webkit-user-select: text; }
  .mgr-in:focus { border-color: #ff3b30; box-shadow: 0 0 8px var(--glow); }
  .mgr-list { flex: 1 1 auto; min-height: calc(var(--u) * 140); max-height: calc(var(--u) * 360); overflow-y: auto; border: 1px solid #3a1210; background: #0b0404; border-radius: calc(var(--u) * 2); box-shadow: inset 0 0 10px #000; }
  .mgr-item { display: flex; align-items: center; gap: calc(var(--u) * 8); padding: calc(var(--u) * 5) calc(var(--u) * 8); border-bottom: 1px solid #1c0b0a; cursor: pointer; font-size: calc(var(--u) * 10); }
  .mgr-item:hover { background: #1a0908; }
  .mgr-item.sel { background: #2a0f0d; box-shadow: inset 2px 0 0 #ff3b30; }
  .mi-dot { flex: 0 0 auto; width: calc(var(--u) * 7); height: calc(var(--u) * 7); border-radius: 50%; background: #2a0707; border: 1px solid #5a1a16; }
  .mgr-item.cur .mi-dot, .mi-dot.on { background: #ff3b30; box-shadow: 0 0 8px #ff3b30; }
  .mi-name { flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; letter-spacing: 0.04em; }
  .mi-sub { flex: 0 0 auto; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 8); color: var(--dim); }
  .mi-btns { flex: 0 0 auto; display: flex; gap: calc(var(--u) * 4); }
  .mi-btns .pb { padding: calc(var(--u) * 2) calc(var(--u) * 6); font-size: calc(var(--u) * 8); }
  .mgr-empty { padding: calc(var(--u) * 24); text-align: center; font-size: calc(var(--u) * 9); letter-spacing: 0.1em; color: var(--dim); }
  .mgr-st, .lb-target { flex: 0 0 auto; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 8); letter-spacing: 0.06em; color: var(--yel); min-height: calc(var(--u) * 12); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .lb-target { color: var(--dim); }
  .mgr-ta { width: 100%; height: calc(var(--u) * 90); resize: none; padding: calc(var(--u) * 6); font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 8); color: var(--ink); background: #0e0303; border: 1px solid #6a1b16; outline: none; user-select: text; -webkit-user-select: text; }
  .mgr-io[hidden] { display: none; }
  .mgr-io { display: flex; flex-direction: column; gap: calc(var(--u) * 6); }

  .fs-folder .only-browser, .fs-browser .only-folder { display: none !important; }
  .mgr-path { flex: 0 0 auto; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 7.5); letter-spacing: 0.04em; color: var(--dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; user-select: text; -webkit-user-select: text; }
  /* one memory slot per sampler / wavetable: no slot selectors or slot buttons */

  /* serum style layout: top groups, oscillator sub tabs, bottom modulation strip */
  .subtabs { display: none; flex: 0 0 auto; gap: calc(var(--u) * 3); }
  eisenpuls-view[data-group="osc"] .subtabs { display: flex; }
  .stab { font-family: inherit; font-size: calc(var(--u) * 9); font-weight: 800; letter-spacing: 0.06em; padding: calc(var(--u) * 4) calc(var(--u) * 10); border: 1px solid var(--line); border-radius: 1px; background: var(--panel); color: var(--dim); cursor: pointer; }
  .stab.on { background: var(--panel2); color: var(--yel); border-color: var(--yel); }
  .bstrip { flex: 0 0 auto; height: calc(var(--u) * 190); display: flex; flex-direction: column; background: linear-gradient(#25282c, #1a1c1f); border: 1px solid var(--line); border-radius: calc(var(--u) * 2); min-height: 0; }
  eisenpuls-view.strip-closed .bstrip { height: calc(var(--u) * 26); }
  eisenpuls-view.strip-closed .bs-body { display: none; }
  .bs-tabs { flex: 0 0 auto; display: flex; align-items: center; gap: calc(var(--u) * 4); padding: calc(var(--u) * 3) calc(var(--u) * 8); }
  .bst, .bs-btn, .bs-toggle { font-family: inherit; font-size: calc(var(--u) * 9); font-weight: 800; letter-spacing: 0.08em; padding: calc(var(--u) * 3) calc(var(--u) * 9); border: 1px solid var(--line); border-radius: 1px; background: var(--panel2); color: var(--ink); cursor: pointer; }
  .bst.on { background: var(--yel); color: #111; border-color: var(--yel); }
  .bs-hint { flex: 1; text-align: right; font-size: calc(var(--u) * 8); color: var(--dim); letter-spacing: 0.06em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bs-body { flex: 1 1 0; min-height: 0; position: relative; }
  .bs-pane { position: absolute; inset: 0; display: none; padding: 0 calc(var(--u) * 8) calc(var(--u) * 6); min-height: 0; }
  .bs-pane.on { display: flex; gap: calc(var(--u) * 8); }
  .bs-mtx.on { display: block; overflow: hidden; }
  .bs-mtx .mtx2 { height: 100%; }
  .bs-env { flex: 0 0 36%; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .bs-lfo { flex: 1 1 0; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .bs-chips { flex: 0 0 auto; display: flex; flex-wrap: wrap; gap: calc(var(--u) * 3); align-items: center; margin-bottom: calc(var(--u) * 4); }
  .bs-gap { flex: 1; }
  .msrc { font-family: inherit; font-size: calc(var(--u) * 8); font-weight: 800; letter-spacing: 0.05em; padding: calc(var(--u) * 3) calc(var(--u) * 5); border: 1px solid var(--line); border-radius: calc(var(--u) * 8); background: #14161a; color: var(--ink); cursor: grab; touch-action: none; }
  .bs-lfo .msrc { border-color: #7a2d20; } .bs-env .msrc { border-color: #1f5d85; } .msrc.misc { border-color: #6b6828; }
  .bs-lfo .msrc.on { background: #ff6a4d; color: #111; } .bs-env .msrc.on { background: #4db8ff; color: #111; }
  .bs-envbody, .bs-lfobody { flex: 1 1 0; min-height: 0; display: flex; gap: calc(var(--u) * 8); }
  .bs-envbody { flex-direction: column; }
  .env-canvas, .lfo-canvas { width: 100%; flex: 1 1 0; min-height: 0; display: block; background: #0b0405; border: 1px solid var(--line); border-radius: 2px; touch-action: none; }
  .lfo-cv { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; }
  .lfo-help { flex: 0 0 auto; font-size: calc(var(--u) * 7); color: var(--dim); margin-top: calc(var(--u) * 2); }
  .lfo-sets { flex: 0 0 38%; min-width: 0; position: relative; }
  .lfo-set, .env-set { display: none; }
  .lfo-set.on { display: grid; grid-template-rows: auto 1fr; gap: calc(var(--u) * 4); height: 100%; }
  .env-set.on { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: calc(var(--u) * 6); }
  .ls-top { display: grid; grid-template-columns: 1fr 1fr; gap: calc(var(--u) * 4) calc(var(--u) * 8); }
  .ls-shape { grid-column: 1 / -1; display: flex; flex-direction: column; }
  .ls-knobs { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: calc(var(--u) * 4); align-items: center; }
  .ls-hid { display: none; }
  .lfo-set.synced .n248 { opacity: 0.35; } .lfo-set:not(.synced) .ls-div { opacity: 0.35; }
  .lfo-set .btns .row, .lfo-set .sel .row { display: none; }
  .lfo-set .control .lbl { font-size: calc(var(--u) * 7.5); }
  .bs-env .knb .knob, .bs-lfo .knb .knob { width: calc(var(--u) * 30); height: calc(var(--u) * 30); }
  /* modulation rings, handles, popover */
  .knb .knob { position: relative; }
  .mring { position: absolute; inset: -4px; width: calc(100% + 8px); height: calc(100% + 8px); pointer-events: none; overflow: visible; }
  .mbar { position: absolute; top: 0; height: 100%; opacity: 0.55; pointer-events: none; border-radius: 2px; }
  .control { position: relative; }
  .mdot { position: absolute; top: 0; right: 0; width: calc(var(--u) * 10); height: calc(var(--u) * 10); padding: 0; border: 1px solid #000; border-radius: 50%; font-size: calc(var(--u) * 7); font-weight: 800; color: #111; cursor: pointer; line-height: 1; }
  .modding .control[data-param] { cursor: copy; }
  .modhover { outline: 2px solid var(--yel); outline-offset: 1px; border-radius: 3px; }
  .mod-ghost { position: absolute; z-index: 50; padding: calc(var(--u) * 3) calc(var(--u) * 7); border-radius: calc(var(--u) * 8); color: #111; font-size: calc(var(--u) * 9); font-weight: 800; pointer-events: none; box-shadow: 0 2px 8px rgba(0,0,0,0.6); }
  .modpop { position: absolute; z-index: 60; min-width: calc(var(--u) * 190); padding: calc(var(--u) * 6); background: #17191c; border: 1px solid var(--yel); border-radius: 3px; box-shadow: 0 4px 14px rgba(0,0,0,0.7); }
  .mp-title { font-size: calc(var(--u) * 8); letter-spacing: 0.1em; color: var(--dim); text-transform: uppercase; margin-bottom: calc(var(--u) * 4); }
  .mp-row { display: flex; align-items: center; gap: calc(var(--u) * 5); margin-top: calc(var(--u) * 3); }
  .mp-src { font-size: calc(var(--u) * 8); font-weight: 800; color: #111; padding: calc(var(--u) * 2) calc(var(--u) * 5); border-radius: calc(var(--u) * 6); }
  .mp-row input { flex: 1; min-width: 0; } .mp-val { width: calc(var(--u) * 32); font-size: calc(var(--u) * 8.5); text-align: right; font-family: ui-monospace, Menlo, monospace; }
  .mp-x { background: none; border: 1px solid var(--line); color: var(--ink); cursor: pointer; border-radius: 2px; }
  .lfo-set .dd { width: 100%; }
  .top .sizesel { flex: 0 0 auto; width: calc(var(--u) * 74); padding: calc(var(--u) * 3) calc(var(--u) * 6); font-size: calc(var(--u) * 9); }
  .x-f1 .flt-canvas, .x-f2 .flt-canvas { height: calc(var(--u) * 120); }
  .x-rt .flt-canvas { height: calc(var(--u) * 70); }
  .bs-env .knb .knob, .bs-lfo .knb .knob { width: calc(var(--u) * 26); height: calc(var(--u) * 26); }

  /* oscillator slot pages */
  .page[data-src] { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 1fr); }
  .o-src { grid-column: 1 / span 4; } .o-tune { grid-column: 5 / span 2; } .o-flt { grid-column: 7 / span 4; } .o-out { grid-column: 11 / span 2; }
  .o-g2 { grid-template-columns: repeat(2, minmax(0, 1fr)); } .o-g3 { grid-template-columns: repeat(3, minmax(0, 1fr)); } .o-g4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .card .cgrid { flex: 1 1 auto; align-content: space-evenly; align-items: center; row-gap: calc(var(--u) * 3); }
  .o-src .cgrid, .o-flt .cgrid, .o-tune .cgrid { margin-top: calc(var(--u) * 4); }
  .o-type { flex: 0 0 auto; } .o-type .control .row { display: none; }
  .osc-canvas, .flt-canvas { display: block; flex: 0 0 auto; width: 100%; height: calc(var(--u) * 96); margin-top: calc(var(--u) * 5); background: #0d0404; border: 1px solid #7a1d18; border-radius: calc(var(--u) * 4); box-shadow: inset 0 0 14px rgba(0,0,0,0.95), 0 0 14px rgba(255,59,48,0.25); }
  .osc-info { flex: 0 0 auto; margin-top: calc(var(--u) * 3); font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 7.5); letter-spacing: 0.06em; color: var(--dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .o-mem { flex: 0 0 auto; display: flex; gap: calc(var(--u) * 6); align-items: stretch; margin-top: calc(var(--u) * 4); }
  .o-mem .dz { flex: 1 1 auto; margin: 0; height: calc(var(--u) * 26); font-size: calc(var(--u) * 9); }
  .o-sub, .o-uni { display: contents; }
  .o-uni { display: grid; margin-top: calc(var(--u) * 2); }
  .o-uh { grid-column: 1 / -1; font-size: calc(var(--u) * 8); font-weight: 800; letter-spacing: 0.16em; color: var(--org); text-transform: uppercase; }
  .o-h2 { margin-top: calc(var(--u) * 8); }
  .o-flt .cgrid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .page[data-src] .cgrid > .control.w2, .page[data-src] .cgrid > .control.wide { grid-column: auto; }
  .page[data-src] .o-flt .cgrid > .control.sel, .page[data-src] .o-flt .cgrid > .control.btns { grid-column: span 2; }
  .page[data-src] .o-out .cgrid > .control.sel, .page[data-src] .o-out .cgrid > .control.btns, .page[data-src] .o-pl > .control.sel,
  .page[data-src] .o-tune .cgrid > .control.btns.wide, .page[data-src] .o-g3 > .control.btns { grid-column: 1 / -1; }
  .page[data-src] .knb .knob { width: calc(var(--u) * 32); height: calc(var(--u) * 32); }
  .osc-canvas, .flt-canvas { height: calc(var(--u) * 72); }
  /* FM matrix */
  .p-fm { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
  .fm-grid { flex: 1 1 0; min-height: 0; display: grid; grid-template-columns: calc(var(--u) * 76) repeat(6, minmax(0, 1fr)); grid-template-rows: auto repeat(6, minmax(0, 1fr)); gap: calc(var(--u) * 3); margin-top: calc(var(--u) * 4); }
  .fm-corner { font-size: calc(var(--u) * 7); letter-spacing: 0.08em; color: var(--dim); align-self: end; }
  .fm-h { font-family: Impact, "Arial Black", "Bahnschrift", sans-serif; font-size: calc(var(--u) * 10); letter-spacing: 0.1em; color: var(--yel); text-align: center; align-self: center; }
  .fm-r { text-align: left; }
  .fm-c { display: flex; align-items: center; justify-content: center; min-height: 0; background: rgba(0,0,0,0.25); border: 1px solid transparent; border-radius: 2px; }
  .fm-c.fb { border-color: #6a2a22; background: rgba(255,59,48,0.07); }
  .fm-c .control { width: 100%; }
  .fm-note { flex: 0 0 auto; margin-top: calc(var(--u) * 5); font-size: calc(var(--u) * 8); color: var(--dim); letter-spacing: 0.04em; }
  /* global page */
  .p-glob { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 1fr); }
  .g-voice { grid-column: 1 / span 2; } .g-amp { grid-column: 3 / span 3; } .g-peg { grid-column: 6 / span 2; } .g-out { grid-column: 8 / span 5; }
  .g-voice .cgrid, .g-peg .cgrid { grid-template-columns: minmax(0, 1fr); } .g-amp .cgrid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .g-out .cgrid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
</style>
<div class="shell">
  <div class="top">
    <span class="logo">NJOHRR</span><span class="model">SYNTH</span><span class="version">V1.0.0</span>
    <div class="tabs"><button type="button" class="tab on" data-group="osc">OSC</button><button type="button" class="tab" data-group="fm">FM</button><button type="button" class="tab" data-group="fx">FX</button><button type="button" class="tab" data-group="glob">GLOBAL</button></div>
    <div class="vu"><div class="vu-fill"></div></div>
    <select class="dd sizesel" title="Window size" style="display:none"><option value="0.75">75%</option><option value="1">100%</option><option value="1.25">125%</option><option value="1.5">150%</option><option value="1.75">175%</option><option value="2">200%</option><option value="custom" hidden>Custom</option></select>
    <div class="lcd"><span class="lcd-mode">OSC</span><span class="lcd-name">--</span><span class="lcd-val">--</span></div><span class="led"></span>
  </div>
  <div class="hz"></div>
  <div class="subtabs"><button type="button" class="stab on" data-page="o0">OSC 1</button><button type="button" class="stab" data-page="o1">OSC 2</button><button type="button" class="stab" data-page="o2">OSC 3</button><button type="button" class="stab" data-page="o3">OSC 4</button><button type="button" class="stab" data-page="o4">OSC 5</button><button type="button" class="stab" data-page="o5">OSC 6</button></div>
  ${MGR_HTML}
  <div class="stage">
    ${oscPages}
    <div class="page p-fm">${this.fmPageHTML()}</div>
    <div class="page p-glob">${this.globalPageHTML()}</div>
    <div class="page p-fx">${fxPage}</div>
  </div>
  ${strip}
  ${MGR_OVERLAY_HTML}
</div>`;
    }
}

// ======================================================================
// PRESET BANK + SOUND VAULT
// Folder mode (inside the plugin): files live in <Documents>/Njohrr/{Presets,Samples,Wavetables}
// Browser mode (no native bridge): the same data is kept in IndexedDB.
// ======================================================================
const NAME_BANK = "PRESET BANK";
const NAME_VAULT = "SOUND VAULT";
const BANK_BTN = "BANK";
const VAULT_BTN = "VAULT";

const LIB_DB = "eisenpuls-lib";
const PRESET_EXT = ".njopreset";
const AUDIO_EXT = /\.(wav|wave|aif|aiff|mp3|ogg|flac|m4a)$/i;
const PRESET_SKIP = new Set();
const SLOT_DEFS = [].concat(
    Array.from({ length: OSC_N }, (_, o) => ({ key: "wt" + o, label: "OSC " + (o + 1) + " WAVETABLE", short: "OSC" + (o + 1) + " WT", kind: "wavetable" })),
    Array.from({ length: OSC_N }, (_, o) => ({ key: "sm" + o, label: "OSC " + (o + 1) + " SAMPLER", short: "OSC" + (o + 1) + " SMP", kind: "sample" }))
);
const KIND_FOLDER = { sample: "samples", wavetable: "wavetables" };

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmtBytes = n => n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : n <= 0 ? "0 KB" : Math.max(1, Math.round(n / 1024)) + " KB";
const splitExt = f => { const m = /^(.*?)(\.[^.]*)?$/.exec(String(f)); return [m[1], m[2] || ""]; };
// a name that is safe as a file name on Windows, macOS and Linux
const safeFile = (name, max) => {
    let n = String(name || "").replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_").replace(/^[.\s]+/, "").replace(/[.\s]+$/, "").slice(0, max || 100);
    if (/^(con|prn|aux|nul|com\d|lpt\d)$/i.test(n)) n = "_" + n;
    return n;
};
const bytesToB64 = bytes => {
    let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
};
const b64ToBuf = b64 => {
    const s = atob(b64), out = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
    return out.buffer;
};

// ---------------- backend 1: real folders through the plugin ----------------
class FolderBackend {
    constructor () {
        this.mode = "folder";
        this.root = "";
        this.persistent = true;
        this.ready = this.call("info").then(r => { this.root = r.root || ""; return !!r.ok; }).catch(() => false);
    }
    async call (op, kind, name, arg) {
        const raw = await window.njo(op, kind || "", name || "", arg || "");
        return JSON.parse(raw);
    }
    async list (kind) { const r = await this.call("list", kind); return Array.isArray(r) ? r : []; }

    async presetsList () {
        const files = (await this.list("presets")).filter(f => f.name.toLowerCase().endsWith(PRESET_EXT));
        const rows = await Promise.all(files.map(async f => {
            try {
                const r = await this.call("read", "presets", f.name);
                if (!r.ok) return null;
                const o = JSON.parse(new TextDecoder().decode(new Uint8Array(b64ToBuf(r.data))));
                if (!o || typeof o.params !== "object") return null;
                return { id: f.name, name: String(o.name || splitExt(f.name)[0]), saved: o.saved || f.mtime * 1000, params: o.params, refs: o.refs && typeof o.refs === "object" ? o.refs : {} };
            } catch (_) { return null; }
        }));
        return rows.filter(Boolean);
    }
    async presetSave (rec, prevId) {
        const fname = safeFile(rec.name) + PRESET_EXT;
        const json = JSON.stringify({ format: "njohrr-preset", version: 1, name: rec.name, saved: rec.saved, params: rec.params, refs: rec.refs });
        const r = await this.call("write", "presets", fname, bytesToB64(new TextEncoder().encode(json)));
        if (!r.ok) return null;
        if (prevId && prevId !== fname) await this.call("delete", "presets", prevId);
        return fname;
    }
    async presetDelete (id) { return !!(await this.call("delete", "presets", id)).ok; }

    async libList (durCache) {
        const out = [];
        for (const kind of ["sample", "wavetable"]) {
            const folder = KIND_FOLDER[kind];
            (await this.list(folder)).forEach(f => {
                if (!AUDIO_EXT.test(f.name)) return;
                const id = folder + "/" + f.name;
                out.push({ id, kind, fname: f.name, label: splitExt(f.name)[0], size: f.size, added: f.mtime * 1000, dur: durCache.get(id) || 0 });
            });
        }
        return out;
    }
    parse (id) { const i = id.indexOf("/"); return [id.slice(0, i), id.slice(i + 1)]; }
    async libRead (id) { const [k, n] = this.parse(id); const r = await this.call("read", k, n); return r.ok ? b64ToBuf(r.data) : null; }
    async libWrite (kind, fname, buf) {
        const folder = KIND_FOLDER[kind];
        const r = await this.call("write", folder, fname, bytesToB64(new Uint8Array(buf)));
        return r.ok ? folder + "/" + fname : null;
    }
    async libDelete (id) { const [k, n] = this.parse(id); return !!(await this.call("delete", k, n)).ok; }
    async libMoveTo (id, kind, fname) {
        const [k, n] = this.parse(id);
        const folder = KIND_FOLDER[kind];
        const r = await this.call("move", k, n, folder + "/" + fname);
        return r.ok ? folder + "/" + fname : null;
    }
    async libRename (id, label) {
        const [k, n] = this.parse(id);
        const fname = safeFile(label, 120) + splitExt(n)[1];
        if (!safeFile(label)) return null;
        if (fname === n) return id;
        const r = await this.call("move", k, n, k + "/" + fname);
        return r.ok ? k + "/" + fname : null;
    }
    async libMoveKind (id, kind) {
        const [, n] = this.parse(id);
        return this.libMoveTo(id, kind, n);
    }
    async metaGet () {
        try {
            const r = await this.call("read", "root", "state.json");
            return r.ok ? JSON.parse(new TextDecoder().decode(new Uint8Array(b64ToBuf(r.data)))) : null;
        } catch (_) { return null; }
    }
    async metaPut (obj) { await this.call("write", "root", "state.json", bytesToB64(new TextEncoder().encode(JSON.stringify(obj)))); }
    reveal (what) { return this.call("reveal", what); }
    where (what) { return this.root ? this.root + (what === "root" ? "" : "/" + ({ presets: "Presets", samples: "Samples", wavetables: "Wavetables" })[what]) : ""; }
}

// ---------------- backend 2: IndexedDB (used outside the plugin, e.g. in a browser) ----------------
class BrowserBackend {
    constructor () {
        this.mode = "browser";
        this.db = null;
        this.persistent = false;
        this.mem = { presets: new Map(), files: new Map(), meta: new Map() };
        this.ready = new Promise(res => {
            try {
                const r = window.indexedDB.open(LIB_DB, 1);
                r.onupgradeneeded = () => {
                    const d = r.result;
                    ["presets", "files", "meta"].forEach(n => { if (!d.objectStoreNames.contains(n)) d.createObjectStore(n, { keyPath: "id" }); });
                };
                r.onsuccess = () => { this.db = r.result; this.persistent = true; res(true); };
                r.onerror = () => res(false);
                r.onblocked = () => res(false);
            } catch (_) { res(false); }
        });
    }
    tx (store, mode, fn) {
        return new Promise(res => {
            try {
                const t = this.db.transaction(store, mode);
                const st = t.objectStore(store);
                let out;
                t.oncomplete = () => res(out);
                t.onerror = t.onabort = () => res(undefined);
                const rq = fn(st);
                if (rq && typeof rq.onsuccess !== "undefined") rq.onsuccess = () => { out = rq.result; };
                else out = rq;
            } catch (_) { res(undefined); }
        });
    }
    async all (store) { await this.ready; return this.db ? ((await this.tx(store, "readonly", st => st.getAll())) || []) : Array.from(this.mem[store].values()); }
    async get (store, id) { await this.ready; return this.db ? await this.tx(store, "readonly", st => st.get(id)) : this.mem[store].get(id); }
    async put (store, rec) {
        await this.ready;
        if (!this.db) { this.mem[store].set(rec.id, rec); return true; }
        return (await this.tx(store, "readwrite", st => { st.put(rec); return true; })) === true;
    }
    async del (store, id) {
        await this.ready;
        if (!this.db) { this.mem[store].delete(id); return true; }
        await this.tx(store, "readwrite", st => { st.delete(id); return true; });
        return true;
    }

    async presetsList () { return await this.all("presets"); }
    async presetSave (rec, prevId) { const id = prevId || uid(); return (await this.put("presets", Object.assign({}, rec, { id }))) ? id : null; }
    async presetDelete (id) { return await this.del("presets", id); }

    async libList (durCache) {
        return (await this.all("files")).map(r => ({ id: r.id, kind: r.kind, fname: r.fname, label: r.label, size: r.size, added: r.added, dur: r.dur || durCache.get(r.id) || 0 }));
    }
    async libRead (id) { const r = await this.get("files", id); return r ? r.buf : null; }
    async libWrite (kind, fname, buf) {
        const rec = { id: uid(), kind, fname, label: splitExt(fname)[0].slice(0, 40), size: buf.byteLength, added: Date.now(), dur: 0, buf };
        return (await this.put("files", rec)) ? rec.id : null;
    }
    async libDelete (id) { return await this.del("files", id); }
    async libRename (id, label) {
        const r = await this.get("files", id);
        if (!r || !label.trim()) return null;
        r.label = label.trim().slice(0, 40);
        return (await this.put("files", r)) ? id : null;
    }
    async libMoveKind (id, kind) {
        const r = await this.get("files", id);
        if (!r) return null;
        r.kind = kind;
        return (await this.put("files", r)) ? id : null;
    }
    async metaGet () { const r = await this.get("meta", "slots"); return r ? { slots: r.slots } : null; }
    async metaPut (obj) { await this.put("meta", { id: "slots", slots: obj.slots }); }
    reveal () { return Promise.resolve({ ok: false }); }
    where () { return ""; }
}

const MGR_HTML = `
<div class="bar">
  <span class="bar-l">PRESET</span>
  <button type="button" class="pb pb-prev" title="Previous preset">&#9664;</button>
  <button type="button" class="pb-name" title="Open the ${NAME_BANK.toLowerCase()}">Init</button>
  <button type="button" class="pb pb-next" title="Next preset">&#9654;</button>
  <button type="button" class="pb pb-save" title="Save the current sound">SAVE</button>
  <button type="button" class="pb pb-pm" title="${NAME_BANK}: save, rename, delete and organise presets">${BANK_BTN}</button>
  <span class="bar-sp"></span>
  <span class="bar-info"></span>
  <button type="button" class="pb pb-lib" title="${NAME_VAULT}: your samples and wavetables">${VAULT_BTN}</button>
</div>`;

const MGR_OVERLAY_HTML = `
<div class="mgr-ov" data-ov="presets">
  <div class="mgr-box">
    <div class="mgr-h"><span class="mgr-t">${NAME_BANK}</span><button type="button" class="pb mgr-x" data-act="close">&times;</button></div>
    <div class="mgr-row">
      <input type="text" class="mgr-in pm-name" maxlength="40" placeholder="Preset name" spellcheck="false">
      <button type="button" class="pb" data-act="pm-new">SAVE AS NEW</button>
      <button type="button" class="pb" data-act="pm-over">OVERWRITE</button>
      <button type="button" class="pb" data-act="pm-ren">RENAME</button>
      <button type="button" class="pb" data-act="pm-del">DELETE</button>
    </div>
    <div class="mgr-list pm-list"></div>
    <div class="mgr-row">
      <button type="button" class="pb" data-act="pm-load">LOAD</button>
      <button type="button" class="pb" data-act="pm-init">INIT SOUND</button>
      <span class="bar-sp"></span>
      <button type="button" class="pb only-folder" data-act="open-folder" data-what="presets">OPEN FOLDER</button>
      <button type="button" class="pb only-folder" data-act="pm-rescan">RESCAN</button>
      <button type="button" class="pb only-browser" data-act="pm-export">EXPORT</button>
      <button type="button" class="pb only-browser" data-act="pm-import">IMPORT</button>
    </div>
    <div class="mgr-io" hidden>
      <textarea class="mgr-ta" spellcheck="false" placeholder="Paste exported presets here"></textarea>
      <div class="mgr-row">
        <button type="button" class="pb" data-act="io-copy">COPY</button>
        <button type="button" class="pb" data-act="io-down">DOWNLOAD FILE</button>
        <button type="button" class="pb" data-act="io-file">OPEN FILE...</button>
        <button type="button" class="pb" data-act="io-apply">IMPORT TEXT</button>
        <button type="button" class="pb" data-act="io-close">HIDE</button>
      </div>
    </div>
    <div class="mgr-path pm-path"></div>
    <div class="mgr-st pm-st"></div>
  </div>
</div>
<div class="mgr-ov" data-ov="library">
  <div class="mgr-box">
    <div class="mgr-h"><span class="mgr-t">${NAME_VAULT}</span><button type="button" class="pb mgr-x" data-act="close">&times;</button></div>
    <div class="mgr-row">
      <button type="button" class="pb lb-tab on" data-act="lb-tab" data-kind="sample">SAMPLES</button>
      <button type="button" class="pb lb-tab" data-act="lb-tab" data-kind="wavetable">WAVETABLES</button>
      <input type="text" class="mgr-in lb-search" placeholder="Search" spellcheck="false">
      <button type="button" class="pb" data-act="lb-import">ADD FILES</button>
      <button type="button" class="pb only-folder" data-act="open-folder" data-what="lib">OPEN FOLDER</button>
      <button type="button" class="pb only-folder" data-act="lb-rescan">RESCAN</button>
    </div>
    <div class="lb-target"></div>
    <div class="mgr-list lb-list"></div>
    <div class="mgr-path lb-path"></div>
    <div class="mgr-st lb-st"></div>
  </div>
</div>`;

const mgrMethods = {
    buildManager () {
        this._be = (typeof window.njo === "function") ? new FolderBackend() : new BrowserBackend();
        this.classList.add(this._be.mode === "folder" ? "fs-folder" : "fs-browser");
        this._presets = [];
        this._lib = [];
        this._dur = new Map();
        this._slotLib = Object.fromEntries(SLOT_DEFS.map(d => [d.key, null]));
        this._preset = { id: null, name: "Init", dirty: false };
        this._applying = false;
        this._sel = null;
        this._libKind = "sample";
        this._libTarget = null;
        this._armed = null;
        this._mgrTimers = [];
        this._onDrop = ev => {
            const ov = this.querySelector('.mgr-ov.on[data-ov="library"]');
            if (!ov) return;
            ev.preventDefault();
            const fl = ev.dataTransfer && ev.dataTransfer.files;
            if (fl && fl.length) this.libImport(Array.from(fl));
        };
        this._onOver = ev => { if (this.querySelector('.mgr-ov.on[data-ov="library"]')) ev.preventDefault(); };
        this.addEventListener("drop", this._onDrop);
        this.addEventListener("dragover", this._onOver);
        this._onKey = ev => { if (ev.key === "Escape" && this.querySelector(".mgr-ov.on")) this.closeMgr(); };
        this.addEventListener("keydown", this._onKey);

        const q = s => this.querySelector(s);
        q(".pb-prev").addEventListener("click", () => this.presetStep(-1));
        q(".pb-next").addEventListener("click", () => this.presetStep(1));
        q(".pb-name").addEventListener("click", () => this.openMgr("presets"));
        q(".pb-pm").addEventListener("click", () => this.openMgr("presets"));
        q(".pb-lib").addEventListener("click", () => { this._libTarget = null; this.openMgr("library"); });
        q(".pb-save").addEventListener("click", () => this.presetQuickSave());
        this.querySelectorAll(".mgr-ov").forEach(ov => {
            ov.addEventListener("click", ev => {
                if (ev.target === ov) { this.closeMgr(); return; }
                const b = ev.target.closest("[data-act]");
                if (b) this.mgrAct(b.dataset.act, b, ev);
                const row = ev.target.closest(".mgr-item");
                if (row && !b) this.mgrRowClick(ov.dataset.ov, row);
            });
            ov.addEventListener("dblclick", ev => {
                const row = ev.target.closest(".mgr-item");
                if (row && ov.dataset.ov === "presets" && !ev.target.closest("input,button")) { this._sel = row.dataset.id; this.presetLoad(this._sel); }
            });
        });
        q(".lb-search").addEventListener("input", () => this.renderLib());
        q(".pm-name").addEventListener("keydown", ev => { ev.stopPropagation(); if (ev.key === "Enter") this.mgrAct("pm-new"); else if (ev.key === "Escape") this.closeMgr(); });
        q(".lb-search").addEventListener("keydown", ev => { ev.stopPropagation(); if (ev.key === "Escape") this.closeMgr(); });
        this.querySelectorAll(".dz-lib").forEach(b => b.addEventListener("click", ev => {
            ev.stopPropagation();
            this._libTarget = b.dataset.slot;
            const def = SLOT_DEFS.find(s => s.key === b.dataset.slot);
            this._libKind = def ? def.kind : "sample";
            this.openMgr("library");
        }));

        this._be.ready.then(async ok => {
            if (this._be.mode === "folder" && !ok) {
                // folder access failed: fall back so the manager still works
                this._be = new BrowserBackend();
                this.classList.remove("fs-folder"); this.classList.add("fs-browser");
                await this._be.ready;
                this.barInfo("FOLDERS UNAVAILABLE - USING TEMPORARY STORAGE");
            }
            await this.presetsRefresh();
            await this.libRefresh();
            // which vault file each oscillator uses is per plugin instance (never the shared vault meta file)
            await this._ready;
            const m = { slots: this.kvGet(SLOTS_STATE_KEY) };
            if (m.slots && typeof m.slots === "object") Object.keys(this._slotLib).forEach(k => { if (m.slots[k] && this._lib.some(r => r.id === m.slots[k])) this._slotLib[k] = m.slots[k]; });
            this.updateBar();
            if (this._be.mode === "browser" && !this._be.persistent) this.barInfo("STORAGE UNAVAILABLE - TEMPORARY");
        });
        this.updateBar();
    },

    teardownManager () {
        this.removeEventListener("drop", this._onDrop);
        this.removeEventListener("dragover", this._onOver);
        this.removeEventListener("keydown", this._onKey);
        (this._mgrTimers || []).forEach(t => clearTimeout(t));
        this._mgrTimers = [];
        if (this._infoTimer) clearTimeout(this._infoTimer);
    },

    barInfo (t) {
        const el = this.querySelector(".bar-info");
        if (!el) return;
        el.textContent = t || "";
        if (this._infoTimer) clearTimeout(this._infoTimer);
        if (t) this._infoTimer = setTimeout(() => { el.textContent = ""; }, 4000);
    },

    updateBar () {
        const b = this.querySelector(".pb-name");
        if (b) b.textContent = this._preset.name + (this._preset.dirty ? " *" : "");
    },

    presetDirty () {
        if (this._applying || this._preset.dirty) return;
        this._preset.dirty = true;
        this.updateBar();
    },

    // ---------------- presets ----------------
    async presetsRefresh () {
        const all = await this._be.presetsList();
        this._presets = all.sort((a, b) => a.name.toLowerCase() < b.name.toLowerCase() ? -1 : a.name.toLowerCase() > b.name.toLowerCase() ? 1 : 0);
        if (this._preset.id && !this._presets.some(p => p.id === this._preset.id)) this._preset.id = null;
        this.renderPresets();
    },

    collectParams () {
        const p = {};
        this._controls.forEach((c, id) => {
            if (PRESET_SKIP.has(id)) return;
            p[id.replace("param", "")] = Math.round(c.value * 1e6) / 1e6;
        });
        return p;
    },

    collectRefs () {
        const r = {};
        SLOT_DEFS.forEach(s => {
            const rec = this._lib.find(x => x.id === this._slotLib[s.key]);
            r[s.key] = rec ? { name: rec.fname, size: rec.size } : null;
        });
        return r;
    },

    nameTaken (name, exceptId) {
        const k = safeFile(name).toLowerCase();
        return this._presets.some(p => p.id !== exceptId && (p.name.toLowerCase() === name.toLowerCase() || safeFile(p.name).toLowerCase() === k));
    },

    async presetSaveAs (name, id) {
        name = String(name || "").trim().slice(0, 40);
        if (!name) { this.pmStatus("TYPE A NAME FIRST"); return null; }
        if (!safeFile(name)) { this.pmStatus("THAT NAME HAS NO USABLE CHARACTERS"); return null; }
        if (name.toLowerCase() === "init") { this.pmStatus("'INIT' IS RESERVED"); return null; }
        if (this.nameTaken(name, id)) { this.pmStatus("NAME ALREADY USED"); return null; }
        const rec = { name, saved: Date.now(), params: this.collectParams(), refs: this.collectRefs(), lfo: this.collectLfo() };
        const newId = await this._be.presetSave(rec, id);
        if (!newId) { this.pmStatus("SAVE FAILED"); return null; }
        this._preset = { id: newId, name, dirty: false };
        this._sel = newId;
        await this.presetsRefresh();
        this.updateBar();
        this.pmStatus("SAVED '" + name + "'");
        this.barInfo("SAVED " + name);
        return newId;
    },

    async presetQuickSave () {
        if (this._preset.id) await this.presetSaveAs(this._preset.name, this._preset.id);
        else { this.openMgr("presets"); const i = this.querySelector(".pm-name"); if (i) { i.value = ""; i.focus(); } this.pmStatus("NAME YOUR PRESET AND PRESS SAVE AS NEW"); }
    },

    async presetApply (rec, label) {
        this._applying = true;
        try {
            const params = fxMigrateLegacy(rec.params || {});
            this._controls.forEach((c, id) => {
                if (PRESET_SKIP.has(id)) return;
                const k = id.replace("param", "");
                const v = Object.prototype.hasOwnProperty.call(params, k) ? Number(params[k]) : c.def;
                c.setValue(Number.isFinite(v) ? v : c.def, true);
            });
            this.applyLfo(rec.lfo);
            this.updateSlots();
            this.updateModRings();
            this.drawAllOsc();
            for (let o = 0; o < OSC_N; o++) this.updateOscUi(o);
            for (let g = 0; g < 30; g++) this.updateFxRow(g);
            this.fxApplyOrder();
        } finally { this._applying = false; }
        this._preset = { id: rec.id || null, name: label || rec.name, dirty: false };
        this.updateBar();
        // reload referenced samples / wavetables from the vault
        const refs = rec.refs || {};
        let missing = 0;
        for (const s of SLOT_DEFS) {
            const r = refs[s.key];
            if (!r) continue;
            const item = this._lib.find(x => x.fname === r.name && x.size === r.size);
            if (item) { if (this._slotLib[s.key] !== item.id) await this.libLoad(item.id, s.key); }
            else missing++;
        }
        this.barInfo((label || rec.name) + (missing ? " (" + missing + " FILE(S) NOT IN " + NAME_VAULT + ")" : " LOADED"));
        this.renderPresets();
    },

    presetLoad (id) {
        const rec = this._presets.find(p => p.id === id);
        if (rec) return this.presetApply(rec);
    },

    presetInit () {
        const params = {};
        this._controls.forEach((c, id) => { params[id.replace("param", "")] = c.def; });
        return this.presetApply({ id: null, name: "Init", params, refs: {} });
    },

    presetStep (dir) {
        const list = this._presets;
        if (!list.length) { this.barInfo("NO SAVED PRESETS"); return; }
        let i = list.findIndex(p => p.id === this._preset.id);
        i = i < 0 ? (dir > 0 ? 0 : list.length - 1) : (i + dir + list.length) % list.length;
        this._sel = list[i].id;
        this.presetApply(list[i]);
    },

    pmStatus (t) { const el = this.querySelector(".pm-st"); if (el) el.textContent = t || ""; },

    renderPresets () {
        const el = this.querySelector(".pm-list");
        if (!el) return;
        const items = [{ id: "__init", name: "Init", builtin: true }].concat(this._presets);
        el.innerHTML = items.map(p => '<div class="mgr-item' + (p.id === this._sel ? " sel" : "") + (p.id === this._preset.id || (p.builtin && !this._preset.id && this._preset.name === "Init") ? " cur" : "") + '" data-id="' + esc(p.id) + '">'
            + '<span class="mi-dot"></span><span class="mi-name">' + esc(p.name) + '</span>'
            + '<span class="mi-sub">' + (p.builtin ? "factory" : new Date(p.saved || 0).toLocaleDateString()) + '</span></div>').join("");
        const pe = this.querySelector(".pm-path");
        if (pe) pe.textContent = this._be.mode === "folder" ? "FOLDER  " + this._be.where("presets") : "";
    },

    // ---------------- vault (samples + wavetables) ----------------
    async libRefresh () {
        this._lib = await this._be.libList(this._dur);
        this.renderLib();
    },

    uniqueFname (kind, fname) {
        const [stem, ext] = splitExt(fname);
        let n = 2, out = fname;
        const taken = f => this._lib.some(r => r.kind === kind && r.fname.toLowerCase() === f.toLowerCase());
        while (taken(out)) out = stem + " (" + (n++) + ")" + ext;
        return out;
    },

    async libAdd (file, kind, dur) {
        let fname = safeFile(file.name || "file", 120) || "file";
        if (!AUDIO_EXT.test(fname)) fname += ".wav";
        const dup = this._lib.find(r => r.kind === kind && r.size === file.size && (r.fname === fname || r.fname === (file.name || "")));
        if (dup) return dup.id;
        let buf;
        try { buf = await file.arrayBuffer(); } catch (_) { return null; }
        const name = this.uniqueFname(kind, fname);
        const id = await this._be.libWrite(kind, name, buf);
        if (!id) { this.libStatus("COULD NOT SAVE THE FILE (DISK FULL OR FOLDER NOT WRITABLE)"); return null; }
        if (dur) this._dur.set(id, dur);
        this._lib.push({ id, kind, fname: name, label: splitExt(name)[0], size: buf.byteLength, added: Date.now(), dur: dur || 0 });
        this.renderLib();
        return id;
    },

    // called by the oscillator loaders once a file decoded successfully
    libTrack (slot, file, libId, dec) {
        this._slotLib[slot] = libId || null;
        if (libId && dec && dec.dur) { this._dur.set(libId, dec.dur); const r = this._lib.find(x => x.id === libId); if (r) r.dur = dec.dur; }
        this.saveSlots();
        if (!libId) {
            const def = SLOT_DEFS.find(s => s.key === slot);
            this.libAdd(file, def ? def.kind : "sample", dec ? dec.dur : 0).then(id => {
                if (id && this._slotLib[slot] === null) { this._slotLib[slot] = id; this.saveSlots(); this.renderLib(); }
            });
        } else this.renderLib();
        if (!this._applying) this.presetDirty();
    },

    libUntrack (slot) {
        this._slotLib[slot] = null;
        this.saveSlots();
        this.renderLib();
    },

    saveSlots () { try { this.kvSet(SLOTS_STATE_KEY, Object.assign({}, this._slotLib)); } catch (_) {} },

    async libLoad (id, slot) {
        const rec = this._lib.find(r => r.id === id);
        const buf = rec ? await this._be.libRead(id) : null;
        if (!rec || !buf) { this.libStatus("FILE MISSING - PRESS RESCAN"); return; }
        const file = new File([buf], rec.fname, { type: "" });
        if (/^(wt|sm)\d$/.test(slot)) await this.loadMem(slot.slice(0, 2), parseInt(slot.slice(2), 10), file, id);
        const def = SLOT_DEFS.find(s => s.key === slot);
        this.libStatus("LOADED '" + rec.label + "' INTO " + (def ? def.label : slot));
    },

    async libImport (files) {
        let n = 0, bad = 0;
        for (const f of files) {
            try {
                const dec = await this.decodeFile(f);
                const id = await this.libAdd(f, this._libKind, dec.dur);
                if (id) n++; else bad++;
            } catch (_) { bad++; }
        }
        this.libStatus("ADDED " + n + " FILE(S)" + (bad ? ", " + bad + " UNSUPPORTED/FAILED" : ""));
    },

    libStatus (t) { const el = this.querySelector(".lb-st"); if (el) { el.dataset.msg = t || ""; this.renderLibStatus(); } },

    renderLibStatus () {
        const el = this.querySelector(".lb-st");
        if (!el) return;
        const total = this._lib.reduce((a, r) => a + (r.size || 0), 0);
        el.textContent = (el.dataset.msg ? el.dataset.msg + "  |  " : "") + this._lib.length + " FILES, " + fmtBytes(total);
    },

    renderLib () {
        const el = this.querySelector(".lb-list");
        if (!el) return;
        const kind = this._libKind;
        const term = (this.querySelector(".lb-search").value || "").toLowerCase();
        this.querySelectorAll(".lb-tab").forEach(b => b.classList.toggle("on", b.dataset.kind === kind));
        const tgt = this._libTarget ? SLOT_DEFS.find(s => s.key === this._libTarget) : null;
        const tEl = this.querySelector(".lb-target");
        if (tEl) tEl.textContent = tgt ? "LOADING INTO: " + tgt.label : "CHOOSE A TARGET BUTTON ON EACH ROW";
        const pe = this.querySelector(".lb-path");
        if (pe) pe.textContent = this._be.mode === "folder" ? "FOLDER  " + this._be.where(KIND_FOLDER[kind]) : "";
        const slots = tgt ? [tgt] : SLOT_DEFS.filter(s => s.kind === kind);
        const rows = this._lib.filter(r => r.kind === kind && (!term || r.label.toLowerCase().indexOf(term) >= 0 || r.fname.toLowerCase().indexOf(term) >= 0))
            .sort((a, b) => a.label.toLowerCase() < b.label.toLowerCase() ? -1 : 1);
        el.innerHTML = rows.length ? rows.map(r => {
            const inUse = SLOT_DEFS.filter(s => this._slotLib[s.key] === r.id).map(s => s.short).join(" ");
            const btns = slots.map(s => '<button type="button" class="pb" data-act="lb-load" data-slot="' + s.key + '">' + (tgt ? "LOAD" : s.short) + '</button>').join("");
            return '<div class="mgr-item" data-id="' + esc(r.id) + '">'
                + '<span class="mi-dot' + (inUse ? " on" : "") + '" title="' + (inUse ? "loaded in " + inUse : "") + '"></span>'
                + '<span class="mi-name" title="' + esc(r.fname) + '">' + (this._renaming === r.id ? '<input type="text" class="mgr-in mi-edit" maxlength="60" value="' + esc(r.label) + '" spellcheck="false">' : esc(r.label)) + '</span>'
                + '<span class="mi-sub">' + (inUse ? inUse + "  " : "") + (r.dur ? r.dur.toFixed(2) + " s  " : "") + fmtBytes(r.size) + '</span>'
                + '<span class="mi-btns">' + btns
                + '<button type="button" class="pb" data-act="lb-ren" title="Rename">REN</button>'
                + '<button type="button" class="pb" data-act="lb-kind" title="Move to the ' + (kind === "sample" ? "wavetables" : "samples") + ' folder">' + (kind === "sample" ? "&rarr; WT" : "&rarr; SMP") + '</button>'
                + '<button type="button" class="pb' + (this._armed === "lb:" + r.id ? " arm" : "") + '" data-act="lb-del" title="Delete the file">' + (this._armed === "lb:" + r.id ? "SURE?" : "DEL") + '</button></span></div>';
        }).join("") : '<div class="mgr-empty">' + (this._lib.length ? "NOTHING MATCHES" : "EMPTY - ADD FILES, DROP THEM HERE, OR LOAD ONE INTO AN OSCILLATOR AND IT APPEARS HERE") + '</div>';
        const ed = el.querySelector(".mi-edit");
        if (ed) {
            const done = ok => this.libRenameDone(ed.closest(".mgr-item").dataset.id, ok ? ed.value : null);
            ed.addEventListener("keydown", ev => { ev.stopPropagation(); if (ev.key === "Enter") done(true); else if (ev.key === "Escape") done(false); });
            ed.addEventListener("blur", () => done(true));
            ed.focus(); ed.select();
        }
        this.renderLibStatus();
    },

    swapId (oldId, newId) {
        Object.keys(this._slotLib).forEach(k => { if (this._slotLib[k] === oldId) this._slotLib[k] = newId; });
        if (this._dur.has(oldId)) { this._dur.set(newId, this._dur.get(oldId)); this._dur.delete(oldId); }
        this.saveSlots();
    },

    async libRenameDone (id, val) {
        if (this._renaming !== id) return;
        this._renaming = null;
        const r = this._lib.find(x => x.id === id);
        if (r && val != null && val.trim() && val.trim() !== r.label) {
            const clash = this._lib.some(x => x.id !== id && x.kind === r.kind && safeFile(x.label).toLowerCase() === safeFile(val).toLowerCase());
            if (clash) this.libStatus("NAME ALREADY USED");
            else {
                const nid = await this._be.libRename(id, val.trim());
                if (nid) { if (nid !== id) this.swapId(id, nid); await this.libRefresh(); this.libStatus("RENAMED"); }
                else this.libStatus("RENAME FAILED");
            }
        }
        this.renderLib();
    },

    arm (key) {
        this._armed = key;
        (this._mgrTimers = this._mgrTimers || []).push(setTimeout(() => { if (this._armed === key) { this._armed = null; this.renderLib(); this.renderPmArm(); } }, 2500));
    },

    renderPmArm () {
        const b = this.querySelector('[data-act="pm-del"]');
        if (b) { b.textContent = this._armed === "pm" ? "SURE?" : "DELETE"; b.classList.toggle("arm", this._armed === "pm"); }
    },

    // ---------------- shared window plumbing ----------------
    async openMgr (which) {
        this.querySelectorAll(".mgr-ov").forEach(ov => ov.classList.toggle("on", ov.dataset.ov === which));
        if (which === "presets") {
            this._sel = this._preset.id || "__init";
            this.renderPresets();
            const n = this.querySelector(".pm-name");
            if (n) n.value = this._preset.id ? this._preset.name : "";
            this.pmStatus("");
            await this.presetsRefresh();
            this.pmStatus(this._presets.length + " SAVED PRESET(S)");
        } else {
            this.querySelector(".lb-search").value = "";
            this.renderLib();
            this.libStatus("");
            await this.libRefresh();
        }
    },

    closeMgr () {
        this.querySelectorAll(".mgr-ov").forEach(ov => ov.classList.remove("on"));
        this._armed = null;
        this._renaming = null;
    },

    mgrRowClick (which, row) {
        if (which === "presets") {
            this._sel = row.dataset.id;
            const p = this._presets.find(x => x.id === this._sel);
            this.querySelector(".pm-name").value = p ? p.name : "";
            this.renderPresets();
        }
    },

    selPreset () { return this._presets.find(p => p.id === this._sel) || null; },

    async mgrAct (act, btn) {
        const name = () => this.querySelector(".pm-name").value;
        switch (act) {
            case "close": this.closeMgr(); break;
            case "open-folder": {
                const what = btn.dataset.what === "lib" ? KIND_FOLDER[this._libKind] : btn.dataset.what;
                const r = await this._be.reveal(what);
                const msg = r && r.ok ? "OPENED " + this._be.where(what) : "COULD NOT OPEN THE FOLDER: " + this._be.where(what);
                if (btn.dataset.what === "lib") this.libStatus(msg); else this.pmStatus(msg);
                break;
            }
            case "pm-rescan": await this.presetsRefresh(); this.pmStatus(this._presets.length + " SAVED PRESET(S)"); break;
            case "lb-rescan": await this.libRefresh(); this.libStatus("RESCANNED"); break;
            case "pm-new": await this.presetSaveAs(name(), null); break;
            case "pm-over": {
                const p = this.selPreset();
                if (!p) { this.pmStatus("SELECT A SAVED PRESET FIRST"); break; }
                await this.presetSaveAs(p.name, p.id);
                break;
            }
            case "pm-ren": {
                const p = this.selPreset();
                if (!p) { this.pmStatus("SELECT A SAVED PRESET FIRST"); break; }
                const nn = name().trim().slice(0, 40);
                if (!nn || !safeFile(nn)) { this.pmStatus("TYPE THE NEW NAME FIRST"); break; }
                if (nn.toLowerCase() === "init" || this.nameTaken(nn, p.id)) { this.pmStatus("NAME ALREADY USED"); break; }
                const nid = await this._be.presetSave({ name: nn, saved: p.saved, params: p.params, refs: p.refs }, p.id);
                if (!nid) { this.pmStatus("RENAME FAILED"); break; }
                if (this._preset.id === p.id) this._preset = { id: nid, name: nn, dirty: this._preset.dirty };
                this._sel = nid;
                await this.presetsRefresh(); this.updateBar();
                this.pmStatus("RENAMED");
                break;
            }
            case "pm-del": {
                const p = this.selPreset();
                if (!p) { this.pmStatus("SELECT A SAVED PRESET FIRST"); break; }
                if (this._armed !== "pm") { this._armed = "pm"; this.renderPmArm(); this.arm("pm"); break; }
                this._armed = null;
                await this._be.presetDelete(p.id);
                if (this._preset.id === p.id) this._preset.id = null;
                this._sel = null;
                await this.presetsRefresh(); this.updateBar(); this.renderPmArm();
                this.pmStatus("DELETED '" + p.name + "'");
                break;
            }
            case "pm-load": {
                if (this._sel === "__init") { await this.presetInit(); break; }
                const p = this.selPreset();
                if (p) await this.presetApply(p); else this.pmStatus("SELECT A PRESET FIRST");
                break;
            }
            case "pm-init": await this.presetInit(); this.pmStatus("INIT SOUND LOADED"); break;
            case "pm-export": {
                const p = this.selPreset();
                const list = p ? [p] : this._presets;
                const io = this.querySelector(".mgr-io");
                io.hidden = false;
                this.querySelector(".mgr-ta").value = JSON.stringify({ format: "eisenpuls-presets", version: 1, presets: list.map(x => ({ name: x.name, params: x.params, refs: x.refs })) });
                this.pmStatus("EXPORTED " + list.length + " PRESET(S) - " + (p ? "SELECTED ONE" : "ALL") + ". COPY THE TEXT OR DOWNLOAD");
                break;
            }
            case "pm-import": {
                const io = this.querySelector(".mgr-io");
                io.hidden = false;
                this.querySelector(".mgr-ta").value = "";
                this.querySelector(".mgr-ta").focus();
                this.pmStatus("PASTE EXPORTED TEXT, THEN PRESS IMPORT TEXT (OR OPEN A FILE)");
                break;
            }
            case "io-close": this.querySelector(".mgr-io").hidden = true; break;
            case "io-copy": {
                const ta = this.querySelector(".mgr-ta");
                ta.focus(); ta.select();
                let ok = false;
                try { ok = document.execCommand("copy"); } catch (_) {}
                if (!ok) { try { await navigator.clipboard.writeText(ta.value); ok = true; } catch (_) {} }
                this.pmStatus(ok ? "COPIED" : "PRESS CTRL+C / CMD+C TO COPY THE SELECTED TEXT");
                break;
            }
            case "io-down": {
                try {
                    const blob = new Blob([this.querySelector(".mgr-ta").value], { type: "application/json" });
                    const a = document.createElement("a");
                    a.href = URL.createObjectURL(blob); a.download = "njohrr-presets.json";
                    document.body.appendChild(a); a.click(); a.remove();
                    this.pmStatus("DOWNLOAD STARTED - IF NOTHING HAPPENS, USE COPY");
                } catch (_) { this.pmStatus("DOWNLOAD NOT AVAILABLE HERE - USE COPY"); }
                break;
            }
            case "io-file": {
                const inp = document.createElement("input");
                inp.type = "file"; inp.accept = ".json,application/json,text/plain";
                inp.onchange = async () => {
                    const f = inp.files && inp.files[0];
                    if (f) { this.querySelector(".mgr-ta").value = await f.text(); await this.mgrAct("io-apply"); }
                };
                inp.click();
                break;
            }
            case "io-apply": {
                let obj;
                try { obj = JSON.parse(this.querySelector(".mgr-ta").value); } catch (_) { this.pmStatus("THAT TEXT IS NOT VALID PRESET DATA"); break; }
                const list = obj && (obj.format === "eisenpuls-presets" || obj.format === "njohrr-presets") && Array.isArray(obj.presets) ? obj.presets : null;
                if (!list) { this.pmStatus("THAT TEXT IS NOT VALID PRESET DATA"); break; }
                let n = 0;
                for (const x of list) {
                    if (!x || typeof x.name !== "string" || !x.params || typeof x.params !== "object") continue;
                    let nm = x.name.trim().slice(0, 40) || "Imported";
                    if (nm.toLowerCase() === "init") nm = "Init 2";
                    const base = nm;
                    let k = 2;
                    while (this.nameTaken(nm, null)) nm = base.slice(0, 36) + " " + k++;
                    const params = {};
                    Object.keys(x.params).forEach(key => { const v = Number(x.params[key]); if (/^\d+$/.test(key) && Number.isFinite(v)) params[key] = v; });
                    await this._be.presetSave({ name: nm, saved: Date.now(), params, refs: x.refs && typeof x.refs === "object" ? x.refs : {} }, null);
                    await this.presetsRefresh();
                    n++;
                }
                this.pmStatus("IMPORTED " + n + " PRESET(S)");
                break;
            }
            case "lb-tab": this._libKind = btn.dataset.kind; this._libTarget = null; this.renderLib(); break;
            case "lb-import": {
                const inp = document.createElement("input");
                inp.type = "file"; inp.multiple = true; inp.accept = "audio/*,.wav,.aif,.aiff,.mp3,.ogg,.flac";
                inp.onchange = () => { if (inp.files && inp.files.length) this.libImport(Array.from(inp.files)); };
                inp.click();
                break;
            }
            case "lb-load": {
                const id = btn.closest(".mgr-item").dataset.id;
                await this.libLoad(id, btn.dataset.slot);
                break;
            }
            case "lb-ren": this._renaming = btn.closest(".mgr-item").dataset.id; this.renderLib(); break;
            case "lb-kind": {
                const id = btn.closest(".mgr-item").dataset.id;
                const r = this._lib.find(x => x.id === id);
                if (!r) break;
                const to = r.kind === "sample" ? "wavetable" : "sample";
                if (this._lib.some(x => x.kind === to && x.fname.toLowerCase() === r.fname.toLowerCase())) { this.libStatus("A FILE WITH THAT NAME IS ALREADY IN THE OTHER FOLDER"); break; }
                const nid = await this._be.libMoveKind(id, to);
                if (nid) { if (nid !== id) this.swapId(id, nid); await this.libRefresh(); this.libStatus("MOVED TO " + (to === "sample" ? "SAMPLES" : "WAVETABLES")); }
                else this.libStatus("MOVE FAILED");
                break;
            }
            case "lb-del": {
                const id = btn.closest(".mgr-item").dataset.id;
                if (this._armed !== "lb:" + id) { this.arm("lb:" + id); this.renderLib(); break; }
                this._armed = null;
                const ok = await this._be.libDelete(id);
                this._lib = this._lib.filter(x => x.id !== id);
                Object.keys(this._slotLib).forEach(k => { if (this._slotLib[k] === id) this._slotLib[k] = null; });
                this.saveSlots();
                this.renderLib();
                this.libStatus(ok ? "DELETED (A SOUND ALREADY LOADED IN AN OSCILLATOR STAYS THERE)" : "DELETE FAILED");
                break;
            }
        }
    }
};
Object.assign(EisenpulsPatchView.prototype, mgrMethods);


export default function createPatchView (patchConnection) {
    const name = "eisenpuls-view";
    if (!window.customElements.get(name))
        window.customElements.define(name, class extends EisenpulsPatchView {
            constructor () { super(null); }
        });

    // The custom-element class is registered only once per WebView. Do not close
    // over the first patchConnection here: every plugin instance must receive its
    // own connection on the element returned by this factory. All of an instance's saved
    // samples live in that connection's stored state, so nothing is shared between instances.
    const view = new (window.customElements.get(name))();
    view.pc = patchConnection;
    return view;
}
