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
const WT_PAN_IDS = [445, 454, 463];
const WT_PHASE_IDS = [446, 455, 464];

const FILTER_TYPES = ["LP24", "LP12", "HP12", "BP12", "LP6", "LP18", "HP6", "HP18", "HP24", "BP24", "Notch12", "Notch24",
    "Peak", "LowShelf", "HighShelf", "Allpass", "Ladder", "Diode", "Acid", "Dirty LP", "Comb+", "Comb-", "Phaser", "Vowel",
    "MG Low 6", "MG Low 12", "MG Low 18", "MG Low 24", "Flange+", "Flange-"];
const FILTER_GROUPS = [[0, "Basic"], [4, "6 / 18 dB"], [8, "24 dB / Notch"], [12, "Peak / Shelf / Allpass"], [16, "Ladder / Dirty"], [20, "Comb / Phaser / Vowel"], [24, "MG Low"], [28, "Flange"]];
// LFO sync divisions, in the order of the DSP table
const SYNC_DIVS = ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"];

const MOD_WAVES = ["Sin", "Tri", "Sqr", "S&H", "Up", "Dn"];
const MOD_SRC = ["Off"].concat(
    Array.from({ length: 10 }, (_, i) => "LFO " + (i + 1)),
    Array.from({ length: 10 }, (_, i) => "Env " + (i + 1)),
    ["Velocity", "Key", "Random"]
);
const MOD_DST = ["Off", "Pitch", "Cutoff", "Reso", "Amp", "Pan", "OscMix", "PW", "Drive", "WT Pos (all)", "OutGain",
    "Osc1 Pitch", "Osc2 Pitch", "Sub Level", "Noise Level", "SS Pitch", "SS Level",
    "Smp1 Pitch", "Smp1 Level", "Smp2 Pitch", "Smp2 Level"]
    .concat([1, 2, 3].reduce((a, n) => a.concat(["WT" + n + " Pos", "WT" + n + " Pitch", "WT" + n + " Level", "WT" + n + " Pan"]), []))
    .concat([1, 2, 3].reduce((a, n) => a.concat(["WT" + n + " Warp 1", "WT" + n + " Warp 2"]), []))
    .concat([1, 2, 3].map(n => "WT" + n + " Detune"))
    .concat(["F2 Cutoff", "F2 Reso", "F2 Drive", "F2 Mix"]);
// option groups of the dropdowns: [first index, group title]
const MOD_SRC_GROUPS = [[0, ""], [1, "LFO"], [11, "Envelope"], [21, "Note"]];
const MOD_DST_GROUPS = [[0, ""], [1, "Global"], [11, "Oscillators / Samplers"], [21, "Wavetable 1-3"], [33, "Wavetable Warp / Unison"], [42, "Filter 2"]];
const MOD_SLOTS = 20;
// parameter number of the first (source) param of a matrix slot: slots 1-10 are 307.., slots 11-20 are 472..
const slotBase = s => s < 10 ? 307 + 3 * s : 472 + 3 * (s - 10);

// SSL 4000 style channel EQ: per-channel base param and per-band definitions
const EQ_NAMES = ["Osc", "Sub", "Noise", "Supersaw", "Sampler 1", "Sampler 2", "WT1", "WT2", "WT3"];
const EQ_BASE = [337, 348, 359, 370, 381, 392, 403, 414, 425];
// [offset, label suffix, short label, min, max, init, unit, kind]
const EQ_DEF = [
    [0,  "LF Gain",  "Gain", -16, 16, 0, "dB", "knb"],
    [1,  "LF Freq",  "Freq", 30, 450, 100, "Hz", "knb"],
    [2,  "LMF Gain", "Gain", -16, 16, 0, "dB", "knb"],
    [3,  "LMF Freq", "Freq", 200, 2500, 600, "Hz", "knb"],
    [4,  "LMF Q",    "Q", 0.5, 4, 1, "", "knb"],
    [5,  "HMF Gain", "Gain", -16, 16, 0, "dB", "knb"],
    [6,  "HMF Freq", "Freq", 600, 7000, 2500, "Hz", "knb"],
    [7,  "HMF Q",    "Q", 0.5, 4, 1, "", "knb"],
    [8,  "HF Gain",  "Gain", -16, 16, 0, "dB", "knb"],
    [9,  "HF Freq",  "Freq", 1500, 16000, 8000, "Hz", "knb"],
    [10, "In",       "EQ", 0, 1, 1, "", "btn"]
];
const EQ_BANDS = [["LF", [0, 1]], ["LMF", [2, 3, 4]], ["HMF", [5, 6, 7]], ["HF", [8, 9]]];

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

// filter page parameters read by the visualizers
const FLT_VIS_IDS = [12, 13, 14, 525, 526, 527, 528, 529, 531, 534, 535];

const SPECS = (() => {
    const L = [
        [2,  "Voice",        0, 1, 0, "", "btn", ["Poly", "Mono"]],
        [3,  "Glide",        0, 1000, 0, "ms", "sld"],
        [4,  "Osc1 Wave",    0, 5, 0, "", "btn", ["Saw", "Sqr", "Tri", "Sin", "Nse", "Pls"]],
        [5,  "Osc2 Wave",    0, 5, 0, "", "btn", ["Saw", "Sqr", "Tri", "Sin", "Nse", "Pls"]],
        [6,  "Osc1 Semi",    -24, 24, 0, "st", "sld"],
        [7,  "Osc2 Semi",    -24, 24, 0, "st", "sld"],
        [8,  "Osc2 Detune",  -100, 100, 7, "ct", "sld"],
        [9,  "Osc Mix",      0, 1, 0.5, "", "sld"],
        [10, "Osc Sync",     0, 1, 0, "", "btn", ["Off", "On"]],
        [11, "Ring Mod",     0, 1, 0, "", "sld"],
        [12, "Type",         0, 29, 0, "", "sel", FILTER_TYPES, 1, "", FILTER_GROUPS],
        [13, "Cutoff",       20, 18000, 4000, "Hz", "sld"],
        [14, "Resonance",    0, 1, 0.25, "", "sld"],
        [15, "EG Int",       -1, 1, 0.4, "", "sld"],
        [16, "EG Decay",     10, 3000, 300, "ms", "sld"],
        [17, "Key Track",    0, 1, 0.5, "", "sld"],
        [18, "Attack",       0, 2000, 2, "ms", "sld"],
        [19, "Decay",        10, 4000, 500, "ms", "sld"],
        [20, "Sustain",      0, 1, 0.8, "", "sld"],
        [21, "Release",      5, 4000, 250, "ms", "sld"],
        [22, "Velocity",     0, 1, 0.6, "", "sld"],
        [23, "LFO Wave",     0, 3, 0, "", "btn", ["Sin", "Tri", "Sqr", "S&H"]],
        [24, "Rate",         0.05, 30, 4, "Hz", "sld"],
        [25, "To Pitch",     0, 1, 0, "", "sld"],
        [26, "To Cutoff",    0, 1, 0, "", "sld"],
        [27, "To Amp",       0, 1, 0, "", "sld"],
        [28, "Synth Drive",  0, 1, 0.1, "", "sld"],
        [29, "Synth Pan",    -1, 1, 0, "", "sld"],
        [30, "Delay Time",   10, 1000, 375, "ms", "sld"],
        [31, "Feedback",     0, 0.95, 0.35, "", "sld"],
        [32, "Synth Delay",  0, 1, 0, "", "sld"],
        [36, "Master",       0, 1, 0.8, "", "sld"],
        [37, "Sub Osc",      0, 1, 0, "", "sld"],
        [38, "Noise",        0, 1, 0, "", "sld"],
        [39, "Pulse Width",  0.05, 0.95, 0.25, "", "sld"],
        [40, "F.EG Attack",  0, 2000, 0, "ms", "sld"],
        [41, "F.EG Sustain", 0, 1, 0, "", "sld"],
        [42, "F.EG Release", 5, 4000, 250, "ms", "sld"],
        [43, "Filt Drive",   0, 1, 0, "", "sld"],
        [44, "Filt Vel",     0, 1, 0, "", "sld"],
        [45, "Pitch EG",     -24, 24, 0, "st", "sld"],
        [46, "P.EG Decay",   10, 2000, 150, "ms", "sld"],
        [47, "Key Sync",     0, 1, 0, "", "btn", ["Off", "On"]],
        [48, "To PW",        0, 1, 0, "", "sld"],
        [60, "Delay Damp",   500, 18000, 18000, "Hz", "sld"],
        [61, "Bit Crush",    4, 16, 16, "bit", "sld"],
        [62, "SR Reduce",    1, 32, 1, "x", "sld"],
        [63, "Master Tune",  -100, 100, 0, "ct", "sld"],
        [138, "SS Level",    0, 1, 0, "", "sld"],
        [139, "SS Detune",   0, 1, 0.5, "", "sld"],
        [140, "SS Mix",      0, 1, 0.6, "", "sld"],
        [141, "SS Voices",   1, 7, 7, "", "btn", ["1", "2", "3", "4", "5", "6", "7"]],
        [142, "SS Spread",   0, 1, 0.7, "", "sld"],
        [143, "SS Semi",     -24, 24, 0, "st", "sld"],
        [144, "Rand Phase",  0, 1, 1, "", "btn", ["Off", "On"]],
        [145, "SS Solo",     0, 1, 0, "", "btn", ["Off", "On"]],
        [146, "Autosave",    0, 1, 1, "", "btn", ["Off", "On"]],
        [147, "Save All",    0, 1, 0, "", "btn", ["Idle", "Save"]],
        [148, "Osc1 Oct",    -4, 4, 0, "oct", "stp"],
        [149, "Osc1 Fine",   -100, 100, 0, "ct", "sld"],
        [150, "Osc2 Oct",    -4, 4, 0, "oct", "stp"],
        [151, "SS Oct",      -4, 4, 0, "oct", "stp"],
        [152, "SS Fine",     -100, 100, 0, "ct", "sld"],
        [153, "Smp Level",   0, 1, 0, "", "sld"],
        [154, "Memory",      0, 0, 0, "", "stp", null, 4],
        [155, "Root Note",   0, 127, 60, "", "stp", null, 12],
        [156, "Smp Oct",     -4, 4, 0, "oct", "stp"],
        [157, "Smp Semi",    -12, 12, 0, "st", "stp", null, 12],
        [158, "Smp Fine",    -100, 100, 0, "ct", "sld"],
        [159, "Loop",        0, 1, 0, "", "btn", ["Off", "On"]],
        [160, "Start",       0, 1, 0, "", "sld"],
        [161, "Key Track",   0, 1, 1, "", "btn", ["Off", "On"]],
        [162, "Route",       0, 1, 1, "", "btn", ["Dry", "Filter"]],
        [163, "Smp Solo",    0, 1, 0, "", "btn", ["Off", "On"]],
        [164, "Chorus Mix",  0, 1, 0, "", "sld"],
        [165, "Chorus Rate", 0.05, 5, 0.8, "Hz", "sld"],
        [166, "Chorus Depth", 0, 1, 0.5, "", "sld"],
        [167, "Phaser Mix",  0, 1, 0, "", "sld"],
        [168, "Phaser Rate", 0.05, 8, 0.4, "Hz", "sld"],
        [169, "Phaser Depth", 0, 1, 0.5, "", "sld"],
        [170, "Reverb Mix",  0, 1, 0, "", "sld"],
        [171, "Reverb Size", 0, 1, 0.5, "", "sld"],
        [172, "Reverb Damp", 0, 1, 0.5, "", "sld"],
        [173, "Trem Depth",  0, 1, 0, "", "sld"],
        [174, "Trem Rate",   0.1, 20, 5, "Hz", "sld"],
        [175, "Stereo Width", 0, 2, 1, "", "sld"],
        [176, "Osc Volume",  0, 1, 1, "", "sld"],
        [177, "Chorus Fdbk", 0, 0.9, 0, "", "sld"],
        [178, "Phaser Fdbk", 0, 0.9, 0.5, "", "sld"],
        [179, "Rev PreDly",  0, 100, 0, "ms", "sld"],
        [180, "Rev Width",   0, 1, 1, "", "sld"],
        [181, "Trem Wave",   0, 4, 0, "", "btn", ["Sin", "Tri", "Sqr", "Saw Dn", "Saw Up"]],
        [182, "Trem Stereo", 0, 1, 0, "", "sld"],
        [183, "Delay Mix",   0, 1, 1, "", "sld"],
        [184, "Ping-Pong",   0, 1, 1, "", "sld"],
        [185, "Flanger Mix", 0, 1, 0, "", "sld"],
        [186, "Flanger Rate", 0.05, 5, 0.3, "Hz", "sld"],
        [187, "Flanger Depth", 0, 1, 0.6, "", "sld"],
        [188, "Flanger Fdbk", 0, 0.95, 0.5, "", "sld"],
        [189, "Tone",        -1, 1, 0, "", "sld"],
        [190, "Out Gain",    0, 2, 1, "", "sld"],
        [191, "Crush Mix",   0, 1, 1, "", "sld"],
        [192, "S2 Level",    0, 1, 0, "", "sld"],
        [193, "S2 Memory",   0, 0, 0, "", "stp", null, 4],
        [194, "Root Note",   0, 127, 60, "", "stp", null, 12],
        [195, "S2 Oct",      -4, 4, 0, "oct", "stp"],
        [196, "S2 Semi",     -12, 12, 0, "st", "stp", null, 12],
        [197, "S2 Fine",     -100, 100, 0, "ct", "sld"],
        [198, "Loop",        0, 1, 0, "", "btn", ["Off", "On"]],
        [199, "Start",       0, 1, 0, "", "sld"],
        [200, "Key Track",   0, 1, 1, "", "btn", ["Off", "On"]],
        [201, "Route",       0, 1, 1, "", "btn", ["Dry", "Filter"]],
        [202, "S2 Solo",     0, 1, 0, "", "btn", ["Off", "On"]],
        [209, "WT Level",    0, 1, 0, "", "sld"],
        [210, "WT Memory",   0, 0, 0, "", "stp", null, 4],
        [211, "Position",    0, 1, 0, "", "sld"],
        [212, "Frame Size",  0, 4, 3, "", "btn", ["256", "512", "1024", "2048", "4096"]],
        [213, "WT Oct",      -4, 4, 0, "oct", "stp"],
        [214, "WT Semi",     -12, 12, 0, "st", "stp", null, 12],
        [215, "WT Fine",     -100, 100, 0, "ct", "sld"],
        [216, "Key Track",   0, 1, 1, "", "btn", ["Off", "On"]],
        [217, "Route",       0, 1, 1, "", "btn", ["Dry", "Filter"]],
        [218, "WT Solo",     0, 1, 0, "", "btn", ["Off", "On"]],
        [219, "Root Note",   0, 127, 60, "", "stp", null, 12],
        [220, "LFO > Pos",   0, 1, 0, "", "sld"],
        [221, "DC Block",    0, 1, 0, "", "btn", ["Off", "On"]],
        [222, "DC Freq",     5, 200, 20, "Hz", "sld"],
        [223, "W2 Level",    0, 1, 0, "", "sld"],
        [224, "W2 Memory",   0, 0, 0, "", "stp", null, 4],
        [225, "Position",    0, 1, 0, "", "sld"],
        [226, "Frame Size",  0, 4, 3, "", "btn", ["256", "512", "1024", "2048", "4096"]],
        [227, "W2 Oct",      -4, 4, 0, "oct", "stp"],
        [228, "W2 Semi",     -12, 12, 0, "st", "stp", null, 12],
        [229, "W2 Fine",     -100, 100, 0, "ct", "sld"],
        [230, "Key Track",   0, 1, 1, "", "btn", ["Off", "On"]],
        [231, "Route",       0, 1, 1, "", "btn", ["Dry", "Filter"]],
        [232, "W2 Solo",     0, 1, 0, "", "btn", ["Off", "On"]],
        [233, "Root Note",   0, 127, 60, "", "stp", null, 12],
        [234, "LFO > Pos",   0, 1, 0, "", "sld"],
        [235, "W3 Level",    0, 1, 0, "", "sld"],
        [236, "W3 Memory",   0, 0, 0, "", "stp", null, 4],
        [237, "Position",    0, 1, 0, "", "sld"],
        [238, "Frame Size",  0, 4, 3, "", "btn", ["256", "512", "1024", "2048", "4096"]],
        [239, "W3 Oct",      -4, 4, 0, "oct", "stp"],
        [240, "W3 Semi",     -12, 12, 0, "st", "stp", null, 12],
        [241, "W3 Fine",     -100, 100, 0, "ct", "sld"],
        [242, "Key Track",   0, 1, 1, "", "btn", ["Off", "On"]],
        [243, "Route",       0, 1, 1, "", "btn", ["Dry", "Filter"]],
        [244, "W3 Solo",     0, 1, 0, "", "btn", ["Off", "On"]],
        [245, "Root Note",   0, 127, 60, "", "stp", null, 12],
        [246, "LFO > Pos",   0, 1, 0, "", "sld"]
    ];
    // mod page: 10 LFOs (wave stepper + rate), 10 ADSR envelopes, 10 matrix slots
    for (let i = 0; i < 10; i++) {
        L.push([247 + 2 * i, "LFO " + (i + 1) + " Wave", 0, 5, 0, "", "btn", MOD_WAVES]);
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
        L.push([b + 1, "Slot " + (i + 1) + " Dest",   0, 45, 0, "", "sel", MOD_DST, 5, "", MOD_DST_GROUPS]);
        L.push([b + 2, "Slot " + (i + 1) + " Amount", -1, 1, 0, "", "sld"]);
    }
    // mixer page: SSL 4000 style EQ on every channel (LF shelf, LMF bell, HMF bell, HF shelf)
    for (let c = 0; c < EQ_NAMES.length; c++) {
        for (let k = 0; k < EQ_DEF.length; k++) {
            const d = EQ_DEF[k];
            L.push([EQ_BASE[c] + d[0], "EQ " + EQ_NAMES[c] + " " + d[1], d[3], d[4], d[5], d[6], d[7],
                    d[7] === "btn" ? ["Byp", "In"] : null, 1, d[2]]);
        }
    }
    // wavetable unison per engine: voices (1-7), detune (0-1 = up to +/-50 ct), random start phase (off/on)
    [[436, "WT"], [439, "W2"], [442, "W3"]].forEach(u => {
        L.push([u[0],     u[1] + " Unison Voices",     1, 7, 1, "", "stp", null, 1, "Voices"]);
        L.push([u[0] + 1, u[1] + " Unison Detune",     0, 1, 0.25, "", "sld", null, 1, "Detune"]);
        L.push([u[0] + 2, u[1] + " Unison Rand Phase", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Rand Phase"]);
    });
    // LFO beat sync: per mod LFO sync switch + division, global tempo override, main LFO sync
    for (let i = 0; i < 10; i++) {
        L.push([502 + 2 * i, "LFO " + (i + 1) + " Sync", 0, 1, 0, "", "btn", ["Free", "Sync"], 1, "Sync"]);
        L.push([503 + 2 * i, "LFO " + (i + 1) + " Division", 0, 17, 8, "", "sel", SYNC_DIVS, 1, "Division"]);
    }
    L.push([221, "DC Block", 0, 1, 0, "", "btn", ["Off", "On"], 1, "DC Block"]);
    L.push([222, "DC Block Freq", 5, 200, 20, "Hz", "sld", null, 1, "DC Freq"]);
    L.push([522, "Sync BPM", 0, 300, 0, "BPM", "sld", null, 1, "Sync Tempo"]);
    L.push([523, "Main LFO Sync", 0, 1, 0, "", "btn", ["Free", "Sync"], 1, "LFO Sync"]);
    L.push([524, "Main LFO Division", 0, 17, 8, "", "sel", SYNC_DIVS, 1, "Division"]);
    // filter 1 mix, filter 2 and routing
    L.push([525, "Filter 1 Mix",   0, 1, 1, "", "sld", null, 1, "Mix"]);
    L.push([526, "Filter 2",       0, 1, 0, "", "btn", ["Off", "On"], 1, "Filter 2"]);
    L.push([527, "Filter 2 Type",  0, 29, 1, "", "sel", FILTER_TYPES, 1, "Type", FILTER_GROUPS]);
    L.push([528, "Filter 2 Cutoff", 20, 18000, 4000, "Hz", "sld", null, 1, "Cutoff"]);
    L.push([529, "Filter 2 Resonance", 0, 1, 0.25, "", "sld", null, 1, "Resonance"]);
    L.push([530, "Filter 2 Drive", 0, 1, 0, "", "sld", null, 1, "Drive"]);
    L.push([531, "Filter 2 Mix",   0, 1, 1, "", "sld", null, 1, "Mix"]);
    L.push([532, "Filter 2 Key Track", 0, 1, 0, "", "sld", null, 1, "Key Track"]);
    L.push([533, "Filter 2 EG Int", -1, 1, 0, "", "sld", null, 1, "EG Int"]);
    L.push([534, "Filter Routing", 0, 1, 0, "", "btn", ["Serial", "Parallel"], 1, "Routing"]);
    L.push([535, "Parallel Blend", 0, 1, 0.5, "", "sld", null, 1, "F1 / F2 Blend"]);
    // FX module power switches; default On preserves the current sound.
    L.push([541, "Delay Module", 0, 1, 1, "", "btn", ["Bypass", "On"], 1, "Power"]);
    L.push([542, "Drive / Crush Module", 0, 1, 1, "", "btn", ["Bypass", "On"], 1, "Power"]);
    L.push([543, "Chorus Module", 0, 1, 1, "", "btn", ["Bypass", "On"], 1, "Power"]);
    L.push([544, "Flanger Module", 0, 1, 1, "", "btn", ["Bypass", "On"], 1, "Power"]);
    L.push([545, "Phaser Module", 0, 1, 1, "", "btn", ["Bypass", "On"], 1, "Power"]);
    L.push([546, "Reverb Module", 0, 1, 1, "", "btn", ["Bypass", "On"], 1, "Power"]);
    L.push([547, "Tremolo Module", 0, 1, 1, "", "btn", ["Bypass", "On"], 1, "Power"]);
    // fx algorithms
    L.push([536, "Drive Algorithm", 0, 5, 0, "", "sel", ["Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"], 1, "Algorithm"]);
    L.push([537, "Delay Type",      0, 2, 0, "", "sel", ["Digital", "Tape", "Dual"], 1, "Type"]);
    L.push([538, "Chorus Mode",     0, 2, 0, "", "sel", ["Classic", "Dimension", "Vibrato"], 1, "Mode"]);
    L.push([539, "Phaser Stages",   0, 3, 1, "", "sel", ["2 Stages", "4 Stages", "6 Stages", "8 Stages"], 1, "Stages"]);
    L.push([540, "Reverb Type",     0, 3, 0, "", "sel", ["Hall", "Room", "Plate", "Cathedral"], 1, "Type"]);
    // Twenty independent rack slots and a separate variation selector per slot.
    L.push([600, "FX 1 Type", 0, 9, 2, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([601, "FX 1 Power", 0, 1, 1, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([602, "FX 1 Order", 0, 19, 1, "", "sld", null, 1, "Order"]);
    L.push([603, "FX 1 Macro A", 0, 1, 0.3687, "", "sld", null, 1, "Macro A"]);
    L.push([604, "FX 1 Macro B", 0, 1, 0.3684, "", "sld", null, 1, "Macro B"]);
    L.push([605, "FX 1 Macro C", 0, 1, 1, "", "sld", null, 1, "Macro C"]);
    L.push([606, "FX 1 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([607, "FX 1 Macro E", 0, 1, 1, "", "sld", null, 1, "Macro E"]);
    L.push([608, "FX 1 Macro F", 0, 1, 1, "", "sld", null, 1, "Macro F"]);
    L.push([800, "FX 1 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([609, "FX 2 Type", 0, 9, 1, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([610, "FX 2 Power", 0, 1, 1, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([611, "FX 2 Order", 0, 19, 0, "", "sld", null, 1, "Order"]);
    L.push([612, "FX 2 Macro A", 0, 1, 0.1, "", "sld", null, 1, "Macro A"]);
    L.push([613, "FX 2 Macro B", 0, 1, 1, "", "sld", null, 1, "Macro B"]);
    L.push([614, "FX 2 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([615, "FX 2 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([616, "FX 2 Macro E", 0, 1, 0.5, "", "sld", null, 1, "Macro E"]);
    L.push([617, "FX 2 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([801, "FX 2 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([618, "FX 3 Type", 0, 9, 3, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([619, "FX 3 Power", 0, 1, 1, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([620, "FX 3 Order", 0, 19, 2, "", "sld", null, 1, "Order"]);
    L.push([621, "FX 3 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([622, "FX 3 Macro B", 0, 1, 0.1515, "", "sld", null, 1, "Macro B"]);
    L.push([623, "FX 3 Macro C", 0, 1, 0.5, "", "sld", null, 1, "Macro C"]);
    L.push([624, "FX 3 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([625, "FX 3 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([626, "FX 3 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([802, "FX 3 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([627, "FX 4 Type", 0, 9, 4, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([628, "FX 4 Power", 0, 1, 1, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([629, "FX 4 Order", 0, 19, 3, "", "sld", null, 1, "Order"]);
    L.push([630, "FX 4 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([631, "FX 4 Macro B", 0, 1, 0.0505, "", "sld", null, 1, "Macro B"]);
    L.push([632, "FX 4 Macro C", 0, 1, 0.6, "", "sld", null, 1, "Macro C"]);
    L.push([633, "FX 4 Macro D", 0, 1, 0.5, "", "sld", null, 1, "Macro D"]);
    L.push([634, "FX 4 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([635, "FX 4 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([803, "FX 4 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([636, "FX 5 Type", 0, 9, 5, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([637, "FX 5 Power", 0, 1, 1, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([638, "FX 5 Order", 0, 19, 4, "", "sld", null, 1, "Order"]);
    L.push([639, "FX 5 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([640, "FX 5 Macro B", 0, 1, 0.044, "", "sld", null, 1, "Macro B"]);
    L.push([641, "FX 5 Macro C", 0, 1, 0.5, "", "sld", null, 1, "Macro C"]);
    L.push([642, "FX 5 Macro D", 0, 1, 0.5, "", "sld", null, 1, "Macro D"]);
    L.push([643, "FX 5 Macro E", 0, 1, 0.3333, "", "sld", null, 1, "Macro E"]);
    L.push([644, "FX 5 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([804, "FX 5 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([645, "FX 6 Type", 0, 9, 6, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([646, "FX 6 Power", 0, 1, 1, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([647, "FX 6 Order", 0, 19, 6, "", "sld", null, 1, "Order"]);
    L.push([648, "FX 6 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([649, "FX 6 Macro B", 0, 1, 0.5, "", "sld", null, 1, "Macro B"]);
    L.push([650, "FX 6 Macro C", 0, 1, 0.5, "", "sld", null, 1, "Macro C"]);
    L.push([651, "FX 6 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([652, "FX 6 Macro E", 0, 1, 1, "", "sld", null, 1, "Macro E"]);
    L.push([653, "FX 6 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([805, "FX 6 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([654, "FX 7 Type", 0, 9, 7, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([655, "FX 7 Power", 0, 1, 1, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([656, "FX 7 Order", 0, 19, 5, "", "sld", null, 1, "Order"]);
    L.push([657, "FX 7 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([658, "FX 7 Macro B", 0, 1, 0.246, "", "sld", null, 1, "Macro B"]);
    L.push([659, "FX 7 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([660, "FX 7 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([661, "FX 7 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([662, "FX 7 Macro F", 0, 1, 1, "", "sld", null, 1, "Macro F"]);
    L.push([806, "FX 7 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([663, "FX 8 Type", 0, 9, 8, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([664, "FX 8 Power", 0, 1, 1, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([665, "FX 8 Order", 0, 19, 7, "", "sld", null, 1, "Order"]);
    L.push([666, "FX 8 Macro A", 0, 1, 1, "", "sld", null, 1, "Macro A"]);
    L.push([667, "FX 8 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([668, "FX 8 Macro C", 0, 1, 1, "", "sld", null, 1, "Macro C"]);
    L.push([669, "FX 8 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([670, "FX 8 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([671, "FX 8 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([807, "FX 8 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([672, "FX 9 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([673, "FX 9 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([674, "FX 9 Order", 0, 19, 8, "", "sld", null, 1, "Order"]);
    L.push([675, "FX 9 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([676, "FX 9 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([677, "FX 9 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([678, "FX 9 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([679, "FX 9 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([680, "FX 9 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([808, "FX 9 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([681, "FX 10 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([682, "FX 10 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([683, "FX 10 Order", 0, 19, 9, "", "sld", null, 1, "Order"]);
    L.push([684, "FX 10 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([685, "FX 10 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([686, "FX 10 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([687, "FX 10 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([688, "FX 10 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([689, "FX 10 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([809, "FX 10 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([690, "FX 11 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([691, "FX 11 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([692, "FX 11 Order", 0, 19, 10, "", "sld", null, 1, "Order"]);
    L.push([693, "FX 11 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([694, "FX 11 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([695, "FX 11 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([696, "FX 11 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([697, "FX 11 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([698, "FX 11 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([810, "FX 11 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([699, "FX 12 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([700, "FX 12 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([701, "FX 12 Order", 0, 19, 11, "", "sld", null, 1, "Order"]);
    L.push([702, "FX 12 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([703, "FX 12 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([704, "FX 12 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([705, "FX 12 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([706, "FX 12 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([707, "FX 12 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([811, "FX 12 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([708, "FX 13 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([709, "FX 13 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([710, "FX 13 Order", 0, 19, 12, "", "sld", null, 1, "Order"]);
    L.push([711, "FX 13 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([712, "FX 13 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([713, "FX 13 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([714, "FX 13 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([715, "FX 13 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([716, "FX 13 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([812, "FX 13 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([717, "FX 14 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([718, "FX 14 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([719, "FX 14 Order", 0, 19, 13, "", "sld", null, 1, "Order"]);
    L.push([720, "FX 14 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([721, "FX 14 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([722, "FX 14 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([723, "FX 14 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([724, "FX 14 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([725, "FX 14 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([813, "FX 14 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([726, "FX 15 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([727, "FX 15 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([728, "FX 15 Order", 0, 19, 14, "", "sld", null, 1, "Order"]);
    L.push([729, "FX 15 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([730, "FX 15 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([731, "FX 15 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([732, "FX 15 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([733, "FX 15 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([734, "FX 15 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([814, "FX 15 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([735, "FX 16 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([736, "FX 16 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([737, "FX 16 Order", 0, 19, 15, "", "sld", null, 1, "Order"]);
    L.push([738, "FX 16 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([739, "FX 16 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([740, "FX 16 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([741, "FX 16 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([742, "FX 16 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([743, "FX 16 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([815, "FX 16 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([744, "FX 17 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([745, "FX 17 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([746, "FX 17 Order", 0, 19, 16, "", "sld", null, 1, "Order"]);
    L.push([747, "FX 17 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([748, "FX 17 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([749, "FX 17 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([750, "FX 17 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([751, "FX 17 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([752, "FX 17 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([816, "FX 17 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([753, "FX 18 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([754, "FX 18 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([755, "FX 18 Order", 0, 19, 17, "", "sld", null, 1, "Order"]);
    L.push([756, "FX 18 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([757, "FX 18 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([758, "FX 18 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([759, "FX 18 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([760, "FX 18 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([761, "FX 18 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([817, "FX 18 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([762, "FX 19 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([763, "FX 19 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([764, "FX 19 Order", 0, 19, 18, "", "sld", null, 1, "Order"]);
    L.push([765, "FX 19 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([766, "FX 19 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([767, "FX 19 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([768, "FX 19 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([769, "FX 19 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([770, "FX 19 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([818, "FX 19 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    L.push([771, "FX 20 Type", 0, 9, 0, "", "sel", ["Off","Drive","Delay","Chorus","Flanger","Phaser","Reverb","Tremolo","Bitcrush","Filter"], 1, "Type"]);
    L.push([772, "FX 20 Power", 0, 1, 0, "", "btn", ["Bypass","On"], 1, "Power"]);
    L.push([773, "FX 20 Order", 0, 19, 19, "", "sld", null, 1, "Order"]);
    L.push([774, "FX 20 Macro A", 0, 1, 0, "", "sld", null, 1, "Macro A"]);
    L.push([775, "FX 20 Macro B", 0, 1, 0, "", "sld", null, 1, "Macro B"]);
    L.push([776, "FX 20 Macro C", 0, 1, 0, "", "sld", null, 1, "Macro C"]);
    L.push([777, "FX 20 Macro D", 0, 1, 0, "", "sld", null, 1, "Macro D"]);
    L.push([778, "FX 20 Macro E", 0, 1, 0, "", "sld", null, 1, "Macro E"]);
    L.push([779, "FX 20 Macro F", 0, 1, 0, "", "sld", null, 1, "Macro F"]);
    L.push([819, "FX 20 Variation", 0, 5, 0, "", "sel", ["Classic", "Warm", "Bright", "Wide", "Lo-Fi", "Wild"], 1, "Variation"]);
    // Serum style wavetable controls per engine: pan, phase, unison blend / width / style, two warp slots
    [[445, "WT"], [454, "W2"], [463, "W3"]].forEach(u => {
        const b = u[0], n = u[1];
        L.push([b,     n + " Pan",             -1, 1, 0, "", "sld", null, 1, "Pan"]);
        L.push([b + 1, n + " Phase",            0, 1, 0, "", "sld", null, 1, "Phase"]);
        L.push([b + 2, n + " Unison Blend",     0, 1, 1, "", "sld", null, 1, "Blend"]);
        L.push([b + 3, n + " Unison Width",     0, 1, 0.75, "", "sld", null, 1, "Width"]);
        L.push([b + 4, n + " Unison Style",     0, 3, 0, "", "btn", UNI_STYLES, 1, "Detune Curve"]);
        L.push([b + 5, n + " Warp 1 Mode",      0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 1"]);
        L.push([b + 6, n + " Warp 1 Amount",    0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt"]);
        L.push([b + 7, n + " Warp 2 Mode",      0, 8, 0, "", "sel", WARP_MODES, 1, "Warp 2"]);
        L.push([b + 8, n + " Warp 2 Amount",    0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt"]);
    });
    // short control names for the FX cards (the card title already says which effect it is)
    const FX_SHORT = { 164: "Mix", 165: "Rate", 166: "Depth", 177: "Fdbk", 185: "Mix", 186: "Rate", 187: "Depth", 188: "Fdbk",
        167: "Mix", 168: "Rate", 169: "Depth", 178: "Fdbk", 170: "Mix", 171: "Size", 172: "Damp", 179: "PreDly", 180: "Width",
        173: "Depth", 174: "Rate", 182: "Stereo", 30: "Time", 31: "Fdbk", 60: "Damp", 183: "Mix", 184: "Ping-Pong",
        61: "Bit Crush", 62: "SR Reduce", 191: "Crush Mix", 175: "Width", 189: "Tone", 28: "Drive" };
    L.forEach(a => { if (FX_SHORT[a[0]] && !a[9]) { a[8] = a[8] || 1; a[9] = FX_SHORT[a[0]]; } });
    return L.map(a => ({ id: "param" + a[0], num: a[0], label: a[1], min: a[2], max: a[3], init: a[4], unit: a[5], kind: a[6], labels: a[7] || [], big: a[8] || 1, short: a[9] || "", groups: a[10] || null }));
})();

const SPEC_BY_NUM = new Map(SPECS.map(s => [s.num, s]));

// Sound page (samplers, wavetables, memory, mixer and FX controls live on their own pages)
const SYNTH_CARDS = [
    ["Voice",        "s-voice",  [2, 3, 63]],
    ["Oscillators",  "s-osc",    [4, 5, 6, 148, 149, 7, 150, 8, 10, 39]],
    ["Amp EG",       "s-amp",    [18, 19, 20, 21, 22]],
    ["Pitch EG / LFO", "s-lfo",  [45, 46, 23, 24, 523, 524, 47, 25, 26, 27, 48]],
    ["Supersaw",     "s-ss",     [139, 140, 142, 143, 151, 152, 141, 144]]
];
// Filter page
const FLT_CARDS = [
    ["Filter 1",  "x-f1",  [12, 13, 14, 43, 17, 44, 525]],
    ["Filter 2",  "x-f2",  [526, 527, 528, 529, 530, 531, 532, 533]],
    ["Routing",   "x-rt",  [534, 535]],
    ["Filter EG", "x-feg", [15, 40, 16, 41, 42]]
];
// Sampler page
const MEM_IDS = [154, 146, 147];
const SMP_IDS = [155, 156, 157, 158, 159, 160, 161, 162];
// Sampler 2 page
const S2_IDS = [194, 195, 196, 197, 198, 199, 200, 201];
// Wavetable engines (three dedicated wavetable oscillators, each with its own memory bank)
const WT_ENG = [
    { name: "WT", chan: "WT 1", page: "wt1", prefix: "njo.mem.wt1.",  ep: "wavetableBankV2Load",  mem: 210, lvl: 209, pos: 211, size: 212, root: 219, solo: 218,
      ids: [211, 220, 212, 213, 214, 215, 219, 216, 217, 445, 446], uni: [436, 437, 447, 448, 449, 438], warp: [450, 451, 452, 453] },
    { name: "W2", chan: "WT 2", page: "wt2", prefix: "njo.mem.wt2.", ep: "wavetableBank2V2Load", mem: 224, lvl: 223, pos: 225, size: 226, root: 233, solo: 232,
      ids: [225, 234, 226, 227, 228, 229, 233, 230, 231, 454, 455], uni: [439, 440, 456, 457, 458, 441], warp: [459, 460, 461, 462] },
    { name: "W3", chan: "WT 3", page: "wt3", prefix: "njo.mem.wt3.", ep: "wavetableBank3V2Load", mem: 236, lvl: 235, pos: 237, size: 238, root: 245, solo: 244,
      ids: [237, 246, 238, 239, 240, 241, 245, 242, 243, 463, 464], uni: [442, 443, 465, 466, 467, 444], warp: [468, 469, 470, 471] }
];
// Mixer page: every volume/level fader lives here. p = fader param, s = solo param, eq = EQ channel index
const MIX_CH = [
    { p: 176, n: "Osc",       s: 0,   eq: 0 },
    { p: 37,  n: "Sub",       s: 0,   eq: 1 },
    { p: 38,  n: "Noise",     s: 0,   eq: 2 },
    { p: 138, n: "Supersaw",  s: 145, eq: 3 },
    { p: 153, n: "Sampler 1", s: 163, eq: 4 },
    { p: 192, n: "Sampler 2", s: 202, eq: 5 },
    { p: 209, n: "WT 1",      s: 218, eq: 6 },
    { p: 223, n: "WT 2",      s: 232, eq: 7 },
    { p: 235, n: "WT 3",      s: 244, eq: 8 },
    { p: 9,   n: "Osc 1/2",   s: 0,   cls: "pl gap" },
    { p: 11,  n: "Ring",      s: 0,   cls: "pl" },
    { p: 29,  n: "Pan",       s: 0,   cls: "out gap" },
    { p: 32,  n: "Dly Send",  s: 0,   cls: "out" },
    { p: 190, n: "Out Gain",  s: 0,   cls: "out" },
    { p: 36,  n: "Master",    s: 0,   cls: "out" }
];
// FX page
const FX_DELAY = [541, 537, 30, 31, 60, 183, 184];
const FX_CRUSH = [542, 536, 28, 61, 62, 191];
const FX_CHORUS = [543, 538, 164, 165, 166, 177];
const FX_FLANGER = [544, 185, 186, 187, 188];
const FX_PHASER = [545, 539, 167, 168, 169, 178];
const FX_REVERB = [546, 540, 170, 171, 172, 179, 180];
const FX_TREM = [547, 173, 174, 181, 182];
const FX_OUT = [175, 189, 221, 222];
const FX_SLOT_COUNT = 20;
const FX_SLOT_BASE = slot => 600 + slot * 9;
const FX_SLOT_VARIATION_BASE = 800;
const FX_SLOT_TYPES = ["Off", "Drive", "Delay", "Chorus", "Flanger", "Phaser", "Reverb", "Tremolo", "Bitcrush", "Filter"];
const FX_SLOT_VARIATIONS_BY_TYPE = {
    0: ["None", "None", "None", "None", "None", "None"],
    1: ["Use Algorithm", "Tube", "Hard", "Fold", "Sine", "Crunch"],
    2: ["Classic", "Half Time", "Dotted", "Triplet", "Tape Wow", "Ping-Pong"],
    3: ["Classic", "Wide", "Triangle", "Ensemble", "Feedback", "Vibrato"],
    4: ["Classic", "Fast Sweep", "Slow Sweep", "Feedback", "Negative FB", "Stereo"],
    5: ["Use Macros", "4 Stage", "6 Stage", "8 Stage", "Feedback", "Fast Sweep"],
    6: ["Use Type", "Room", "Plate", "Cathedral", "Dark", "Bright"],
    7: ["Use Wave", "Sine", "Triangle", "Square", "Ramp Down", "Ramp Up"],
    8: ["Classic", "Downsample", "Saturate", "Rectify", "Invert", "Wavefold"],
    9: ["Low-pass", "High-pass", "Band-pass", "Notch", "Peak", "Dirty LP"]
};
const FX_SLOT_DEFAULT_ORDER = [1, 0, 2, 3, 4, 6, 5, 7, 8, 9, ...Array.from({ length: 10 }, (_, i) => i + 10)];
const FX_SLOT_INIT = [
    { type: 2, enabled: 1, order: 1, macros: [0.3687, 0.3684, 1, 0, 1, 1] },
    { type: 1, enabled: 1, order: 0, macros: [0.1, 1, 0, 0, 0.5, 0] },
    { type: 3, enabled: 1, order: 2, macros: [0, 0.1515, 0.5, 0, 0, 0] },
    { type: 4, enabled: 1, order: 3, macros: [0, 0.0505, 0.6, 0.5, 0, 0] },
    { type: 5, enabled: 1, order: 4, macros: [0, 0.044, 0.5, 0.5, 0.3333, 0] },
    { type: 6, enabled: 1, order: 6, macros: [0, 0.5, 0.5, 0, 1, 0] },
    { type: 7, enabled: 1, order: 5, macros: [0, 0.246, 0, 0, 0, 1] },
    { type: 8, enabled: 1, order: 7, macros: [1, 0, 1, 0, 0, 0] },
    { type: 0, enabled: 0, order: 8, macros: [0, 0, 0, 0, 0, 0] },
    { type: 0, enabled: 0, order: 9, macros: [0, 0, 0, 0, 0, 0] },
    ...Array.from({ length: 10 }, (_, i) => ({ type: 0, enabled: 0, order: i + 10, macros: [0, 0, 0, 0, 0, 0] }))
];
const FX_SLOT_MACROS = {
    0: ["—", "—", "—", "—", "—", "—"],
    1: ["Amount", "Mix", "Algorithm", "Saturation", "Bias", "Output"],
    2: ["Time", "Feedback", "Mix", "Send", "Ping-Pong", "Damping"],
    3: ["Mix", "Rate", "Depth", "Feedback", "Character", "Width"],
    4: ["Mix", "Rate", "Depth", "Feedback", "Character", "Width"],
    5: ["Mix", "Rate", "Depth", "Feedback", "Stages", "Width"],
    6: ["Mix", "Size", "Damping", "Pre-Delay", "Width", "Type"],
    7: ["Depth", "Rate", "Wave", "Stereo", "Shape", "Output"],
    8: ["Mix", "SR Reduce", "Bits", "Rate", "Character", "Output"],
    9: ["Cutoff", "Resonance", "Mix", "Drive", "Slope", "Output"]
};

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const MAX_SMP = 96000;
const CHUNK = 256;
const MEM_COUNT = 1;
const WT_COUNT = 1;
const S2_COUNT = 1;
const FRAME_SIZES = [256, 512, 1024, 2048, 4096];
const SMP_DZ_EMPTY = "DROP AUDIO / CLICK TO LOAD";
const S2_DZ_EMPTY = "DROP AUDIO / CLICK TO LOAD";
const WT_DZ_EMPTY = "DROP WAVETABLE / CLICK TO LOAD";
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

const STORE_PREFIX = "njo.mem.sampler1.";
const S2_PREFIX = "njo.mem.sampler2.";
const WT_MEM_NAMES = { 210: "WT", 224: "W2", 236: "W3" };
const WT_UNI_VOICES = [436, 439, 442];
const WT_UNI_DETUNE = [437, 440, 443];
const WT_ROOT_IDS = ["param155", "param194", "param219", "param233", "param245"];

function fmt (s, v) {
    if (s.id === "param154") { const m = Math.max(0, Math.min(MEM_COUNT - 1, Math.round(v))); return "MEM " + String(m + 1).padStart(2, "0"); }
    if (s.id === "param193") { const m = Math.max(0, Math.min(S2_COUNT - 1, Math.round(v))); return "S2 " + String(m + 1).padStart(2, "0"); }
    if (WT_MEM_NAMES[s.num]) { const m = Math.max(0, Math.min(WT_COUNT - 1, Math.round(v))); return WT_MEM_NAMES[s.num] + " " + String(m + 1).padStart(2, "0"); }
    if (WT_ROOT_IDS.indexOf(s.id) >= 0) { const n = Math.round(v); return NOTE_NAMES[n % 12] + (Math.floor(n / 12) - 1); }
    if (s.num === 522) return v < 1 ? "HOST" : Math.round(v) + " BPM";
    if (WT_PAN_IDS.indexOf(s.num) >= 0) { const p = Math.round(v * 50); return p === 0 ? "C" : (p < 0 ? "L" + (-p) : "R" + p); }
    if (WT_PHASE_IDS.indexOf(s.num) >= 0) return Math.round(v * 360) + "\u00b0";
    if (WT_UNI_VOICES.indexOf(s.num) >= 0) { const n = Math.round(v); return n + (n === 1 ? " voice" : " voices"); }
    if (WT_UNI_DETUNE.indexOf(s.num) >= 0) return "\u00b1" + Math.round(v * 50) + " ct";
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
        this._smpState = new Array(MEM_COUNT).fill(null);
        this._page = "sound";
        this._store = new Map();
        this._incoming = new Map();
        this._saveHandler = null;
        this._restoreTimer = null;
        this._saveTimer = null;
        // dedicated sampler 2 engine state
        this._s2Store = new Map();
        this._s2State = new Array(S2_COUNT).fill(null);
        this._s2Timer = null;
        this._s2RestoreTimer = null;
        this._s2RestoreStart = null;
        this._s2Restoring = false;
        // dedicated wavetable engines state (3 engines, each with its own memory bank)
        this._wt = WT_ENG.map(() => ({
            store: new Map(), state: new Array(WT_COUNT).fill(null),
            timer: null, restoreTimer: null, restoreStart: null, restoring: false
        }));
        this.innerHTML = this.getHTML();
    }

    connectedCallback () {
        this._disconnected = false;
        this.querySelectorAll(".control").forEach(node => {
            const spec = SPECS.find(s => s.id === node.dataset.param);
            if (!spec) return;
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
        this.bindFxRackDnD();
        this.updateFxRack();
        this.buildSmpLoader();
        this.buildS2Page();
        this.buildMemGrid();
        for (let e = 0; e < WT_ENG.length; e++) this.buildWtPage(e);
        this.updateSmpName();
        this.updateS2Ui();
        for (let e = 0; e < WT_ENG.length; e++) this.updateWtUi(e);
        this.updateSlots();
        this.buildManager();

        this._paramListener = ({ endpointID: id, value: v }) => {
            for (let e = 0; e < WT_ENG.length; e++) {
                if (this._wt[e].restoring && id === "param" + WT_ENG[e].mem) return;
            }
            if (this._s2Restoring && id === "param193") return;
            const c = this._controls.get(id);
            if (c) c.setValue(Number(v), false);
        };
        this.pc.addAllParameterListener(this._paramListener);

        // sample manager: DSP -> UI autosave stream
        this._saveHandler = c => this.onSampleOut(c);
        try { this.pc.addEndpointListener("sampleBankV2Save", this._saveHandler); } catch (_) {}

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
            this.loadStore();
            this.loadS2Store();
            for (let e = 0; e < WT_ENG.length; e++) this.loadWtStore(e);
            this.updateSmpName();
            this.updateS2Ui();
            for (let e = 0; e < WT_ENG.length; e++) this.updateWtUi(e);
            this.startRestore();
            this._s2RestoreStart = setTimeout(() => { this._s2RestoreStart = null; this.startS2Restore(); }, 400);
            for (let e = 0; e < WT_ENG.length; e++) {
                this._wt[e].restoreStart = setTimeout(() => { this._wt[e].restoreStart = null; this.startWtRestore(e); }, 800 + e * 400);
            }
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
        if (this._saveHandler) { try { this.pc.removeEndpointListener("sampleBankV2Save", this._saveHandler); } catch (_) {} }
        if (this._animFrame) cancelAnimationFrame(this._animFrame);
        if (this._resizeObs) this._resizeObs.disconnect();
        if (this._restoreTimer) clearInterval(this._restoreTimer);
        for (let e = 0; e < this._wt.length; e++) {
            const w = this._wt[e];
            if (w.restoreTimer) { clearInterval(w.restoreTimer); w.restoreTimer = null; }
            if (w.restoreStart) { clearTimeout(w.restoreStart); w.restoreStart = null; }
            if (w.timer) { clearInterval(w.timer); w.timer = null; }
        }
        if (this._s2RestoreTimer) clearInterval(this._s2RestoreTimer);
        if (this._s2RestoreStart) clearTimeout(this._s2RestoreStart);
        if (this._saveTimer) clearTimeout(this._saveTimer);
        if (this._s2Timer) { clearInterval(this._s2Timer); this._s2Timer = null; }
        if (this._smpTimer) { clearInterval(this._smpTimer); this._smpTimer = null; }
        delete window.__amorphProcessMidi;
    }

    fit () {
        const w = this.offsetWidth || window.innerWidth || 1180;
        const h = this.offsetHeight || window.innerHeight || 760;
        const u = Math.max(0.5, Math.min(w / 1180, h / 760));
        this.style.setProperty("--u", u.toFixed(4) + "px");
    }

    // ---------- sample memory (autosave to browser storage) ----------
    key (idx) { return STORE_PREFIX + idx; }

    loadStore () {
        for (let i = 0; i < MEM_COUNT; i++) {
            try {
                if (this._store.has(i)) continue;   // loaded by the user since startup: newer than the saved copy
                const m = decodeMem(this.kvGet(this.key(i)), "SAMPLE");
                if (!m) continue;
                this._store.set(i, m);
                this._smpState[i] = m.name;
            } catch (_) {}
        }
    }

    persist (idx) {
        const s = this._store.get(idx);
        try {
            if (!s) { this.kvRemove(this.key(idx)); return; }
            this.kvSet(this.key(idx), encodeMem(s));
        } catch (_) {
            this.setMgr("STORAGE FULL");
        }
    }

    setMgr (text) {
        const el = this.querySelector(".mgr-status");
        if (el) el.textContent = text;
    }

    curMem () {
        const c = this._controls.get("param154");
        return Math.max(0, Math.min(MEM_COUNT - 1, c ? Math.round(c.value) : 0));
    }

    // 24-cell memory bank: click a cell to select that memory
    buildMemGrid () {
        this.querySelectorAll(".mc").forEach(b => {
            b.setAttribute("tabindex", "-1");
            b.addEventListener("click", () => {
                const i = parseInt(b.dataset.i, 10);
                const c = this._controls.get("param154");
                if (c && Number.isFinite(i)) c.setValue(i, true);
                b.blur();
            });
        });
        this.updateSmpName();
    }

    updateSmpName () {
        const idx = this.curMem();
        const nm = this._smpState[idx];
        this.querySelectorAll(".mc").forEach(b => {
            const i = parseInt(b.dataset.i, 10);
            const has = !!this._smpState[i];
            b.classList.toggle("has", has);
            b.classList.toggle("sel", i === idx);
            b.title = "MEM " + (i + 1) + (has ? " / " + this._smpState[i] : " / EMPTY");
        });
        if (!this._smpTimer) this.setSmpDz(nm ? "MEM " + (idx + 1) + " / " + nm : SMP_DZ_EMPTY, nm ? "loaded" : "");
    }

    // DSP -> UI: assemble incoming chunks and persist when a memory is complete
    onSampleOut (c) {
        if (!c) return;
        const idx = Math.max(0, Math.min(MEM_COUNT - 1, (Math.max(0, Math.min(5, c.part | 0)) * 4) + Math.max(0, Math.min(3, c.slot | 0))));
        if (c.total <= 0) {
            this._store.delete(idx);
            this._incoming.delete(idx);
            this._smpState[idx] = null;
            this.persist(idx);
            this.updateSmpName();
            this.setMgr("MEM " + (idx + 1) + " CLEARED");
            return;
        }
        let acc = this._incoming.get(idx);
        if (c.offset === 0 || !acc || acc.total !== c.total) {
            acc = { total: c.total, data: new Float32Array(c.total), got: 0 };
            this._incoming.set(idx, acc);
        }
        const cnt = Math.max(0, Math.min(CHUNK, c.count | 0));
        for (let i = 0; i < cnt && c.offset + i < acc.total; i++) acc.data[c.offset + i] = c.data[i];
        acc.got = c.offset + cnt;
        this.setMgr("SAVING MEM " + (idx + 1) + " " + Math.round(acc.got / acc.total * 100) + "%");
        if (acc.got >= acc.total) {
            const old = this._store.get(idx);
            const name = this._smpState[idx] || (old && old.name) || "SAMPLE " + (idx + 1);
            this._smpState[idx] = name;
            this._store.set(idx, { name, total: acc.total, data: acc.data });
            this._incoming.delete(idx);
            this.persist(idx);
            this.updateSmpName();
            this.setMgr("SAVED MEM " + (idx + 1));
        }
    }

    // UI -> DSP: stream persisted samples back, one at a time
    startRestore () {
        const queue = Array.from(this._store.keys());
        if (!queue.length) { this.setMgr("NO SAVED SAMPLES"); return; }
        let cur = null, off = 0;
        this.setMgr("RESTORING " + queue.length + " MEMORY(S)");
        this._restoreTimer = setInterval(() => {
            if (!cur) {
                if (!queue.length) {
                    clearInterval(this._restoreTimer); this._restoreTimer = null;
                    this.setMgr("RESTORED");
                    return;
                }
                const idx = queue.shift();
                cur = { idx, s: this._store.get(idx) };
                off = 0;
                if (!cur.s) { cur = null; return; }
            }
            for (let k = 0; k < 4 && cur && off < cur.s.total; k++) {
                const count = Math.min(CHUNK, cur.s.total - off);
                const data = new Array(CHUNK).fill(0);
                for (let i = 0; i < count; i++) data[i] = cur.s.data[off + i];
                this.pc.sendEventOrValue("sampleBankV2Restore", {
                    part: Math.floor(cur.idx / 4), slot: cur.idx % 4,
                    offset: off, count, total: cur.s.total, data
                });
                off += count;
            }
            if (cur && off >= cur.s.total) {
                this.updateSmpName();
                cur = null;
            }
        }, 8);
    }

    // ---------- tabs ----------
    buildTabs () {
        this.querySelectorAll(".tab").forEach(t => {
            t.setAttribute("tabindex", "-1");
            t.addEventListener("click", () => { this.setPage(t.dataset.page); t.blur(); });
        });
        this.setPage("sound");
    }

    setPage (p) {
        this._page = p;
        this.setAttribute("data-page", p);
        this.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.dataset.page === p));
        for (let e = 0; e < WT_ENG.length; e++) if (p === WT_ENG[e].page) this.drawWt(e);
        if (p === "flt") this.drawFlt();
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

    // ---------- dedicated sample osc loader (sampleBankV2Load) ----------
    buildSmpLoader () {
        const dz = this.querySelector(".dz-smp");
        if (!dz) return;
        dz.addEventListener("dragover", e => { e.preventDefault(); dz.classList.add("over"); });
        dz.addEventListener("dragleave", () => dz.classList.remove("over"));
        dz.addEventListener("drop", e => {
            e.preventDefault(); dz.classList.remove("over");
            const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
            if (f) this.loadSynthSample(f);
        });
        dz.addEventListener("click", () => {
            const inp = document.createElement("input");
            inp.type = "file"; inp.accept = "audio/*,.wav,.aif,.aiff,.mp3,.ogg,.flac";
            inp.onchange = () => { if (inp.files && inp.files[0]) this.loadSynthSample(inp.files[0]); };
            inp.click();
        });
        const clr = dz.querySelector(".dz-clr");
        if (clr) clr.addEventListener("click", e => { e.stopPropagation(); this.clearSynthSample(); });
    }

    setSmpDz (text, cls) {
        this.querySelectorAll(".dz-smp").forEach(dz => {
            dz.querySelector(".dz-txt").textContent = text;
            dz.classList.toggle("loaded", cls === "loaded");
            dz.classList.toggle("busy", cls === "busy");
            dz.classList.toggle("err", cls === "err");
        });
    }

    cancelSmpLoad () {
        if (this._smpTimer) { clearInterval(this._smpTimer); this._smpTimer = null; }
    }

    clearSynthSample () {
        this.cancelSmpLoad();
        const idx = this.curMem();
        this.pc.sendEventOrValue("sampleBankV2Load", { offset: 0, count: 0, total: 0, data: new Array(CHUNK).fill(0) });
        this.libUntrack("smp");
        this._smpState[idx] = null;
        this._store.delete(idx);
        this.persist(idx);
        this.updateSmpName();
        this.setMgr("MEM " + (idx + 1) + " CLEARED");
    }

    async loadSynthSample (file, libId) {
        this.cancelSmpLoad();
        const idx = this.curMem();
        this.setSmpDz("DECODING...", "busy");
        try {
            const dec = await this.decodeFile(file);
            this.libTrack("smp", file, libId, dec);
            const mono = dec.mono;
            let offset = 0;
            const total = dec.len;
            const name = (file.name || "SAMPLE").replace(/\.[^.]+$/, "").slice(0, 14).toUpperCase();
            this.setSmpDz("LOADING MEM " + (idx + 1) + " 0%", "busy");
            this._smpTimer = setInterval(() => {
                for (let k = 0; k < 6 && offset < total; k++) {
                    const count = Math.min(CHUNK, total - offset);
                    const data = new Array(CHUNK).fill(0);
                    for (let i = 0; i < count; i++) data[i] = mono[offset + i];
                    this.pc.sendEventOrValue("sampleBankV2Load", { offset, count, total, data });
                    offset += count;
                }
                if (offset >= total) {
                    this.cancelSmpLoad();
                    const secs = (total / dec.rate).toFixed(2);
                    this._smpState[idx] = name + " " + secs + "s";
                    this._store.set(idx, { name: this._smpState[idx], total, data: mono });
                    this.persist(idx);
                    this.updateSmpName();
                    const lvl = this._controls.get("param153");
                    if (lvl && lvl.value < 0.05) lvl.setValue(0.8, true);
                } else {
                    this.setSmpDz("LOADING MEM " + (idx + 1) + " " + Math.round(offset / total * 100) + "%", "busy");
                }
            }, 6);
        } catch (err) {
            this.cancelSmpLoad();
            this.setSmpDz("UNSUPPORTED FILE", "err");
        }
    }

    // ---------- sampler 2 (own page, level and memory bank) ----------
    s2Key (idx) { return S2_PREFIX + idx; }

    curS2 () {
        const c = this._controls.get("param193");
        return Math.max(0, Math.min(S2_COUNT - 1, c ? Math.round(c.value) : 0));
    }

    setS2Status (text) {
        const el = this.querySelector(".s2-status");
        if (el) el.textContent = text;
    }

    setS2Dz (text, cls) {
        this.querySelectorAll(".dz-s2").forEach(dz => {
            dz.querySelector(".dz-txt").textContent = text;
            dz.classList.toggle("loaded", cls === "loaded");
            dz.classList.toggle("busy", cls === "busy");
            dz.classList.toggle("err", cls === "err");
        });
    }

    loadS2Store () {
        for (let i = 0; i < S2_COUNT; i++) {
            try {
                if (this._s2Store.has(i)) continue;
                const m = decodeMem(this.kvGet(this.s2Key(i)), "SAMPLE");
                if (!m) continue;
                this._s2Store.set(i, m);
                this._s2State[i] = m.name;
            } catch (_) {}
        }
    }

    persistS2 (idx) {
        const s = this._s2Store.get(idx);
        try {
            if (!s) { this.kvRemove(this.s2Key(idx)); return; }
            this.kvSet(this.s2Key(idx), encodeMem(s));
        } catch (_) {
            this.setS2Status("STORAGE FULL");
        }
    }

    buildS2Page () {
        this.querySelectorAll(".sc").forEach(b => {
            b.setAttribute("tabindex", "-1");
            b.addEventListener("click", () => {
                const i = parseInt(b.dataset.i, 10);
                const c = this._controls.get("param193");
                if (c && Number.isFinite(i)) c.setValue(i, true);
                b.blur();
            });
        });
        const dz = this.querySelector(".dz-s2");
        if (!dz) return;
        dz.addEventListener("dragover", e => { e.preventDefault(); dz.classList.add("over"); });
        dz.addEventListener("dragleave", () => dz.classList.remove("over"));
        dz.addEventListener("drop", e => {
            e.preventDefault(); dz.classList.remove("over");
            const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
            if (f) this.loadSampler2(f);
        });
        dz.addEventListener("click", () => {
            const inp = document.createElement("input");
            inp.type = "file"; inp.accept = "audio/*,.wav,.aif,.aiff,.mp3,.ogg,.flac";
            inp.onchange = () => { if (inp.files && inp.files[0]) this.loadSampler2(inp.files[0]); };
            inp.click();
        });
        const clr = dz.querySelector(".dz-clr");
        if (clr) clr.addEventListener("click", e => { e.stopPropagation(); this.clearSampler2(); });
    }

    updateS2Ui () {
        const idx = this.curS2();
        const nm = this._s2State[idx];
        this.querySelectorAll(".sc").forEach(b => {
            const i = parseInt(b.dataset.i, 10);
            const has = !!this._s2State[i];
            b.classList.toggle("has", has);
            b.classList.toggle("sel", i === idx);
            b.title = "S2 " + (i + 1) + (has ? " / " + this._s2State[i] : " / EMPTY");
        });
        if (!this._s2Timer) this.setS2Dz(nm ? "S2 " + (idx + 1) + " / " + nm : S2_DZ_EMPTY, nm ? "loaded" : "");
    }

    cancelS2Load () {
        if (this._s2Timer) { clearInterval(this._s2Timer); this._s2Timer = null; }
    }

    clearSampler2 () {
        this.cancelS2Load();
        const idx = this.curS2();
        this.pc.sendEventOrValue("sampleBank2V2Load", { offset: 0, count: 0, total: 0, data: new Array(CHUNK).fill(0) });
        this.libUntrack("s2");
        this._s2State[idx] = null;
        this._s2Store.delete(idx);
        this.persistS2(idx);
        this.updateS2Ui();
        this.setS2Status("S2 " + (idx + 1) + " CLEARED");
    }

    async loadSampler2 (file, libId) {
        this.cancelS2Load();
        const idx = this.curS2();
        this.setS2Dz("DECODING...", "busy");
        try {
            const dec = await this.decodeFile(file);
            this.libTrack("s2", file, libId, dec);
            const mono = dec.mono;
            let offset = 0;
            const total = dec.len;
            const name = (file.name || "SAMPLE").replace(/\.[^.]+$/, "").slice(0, 14).toUpperCase();
            this.setS2Dz("LOADING S2 " + (idx + 1) + " 0%", "busy");
            this._s2Timer = setInterval(() => {
                for (let k = 0; k < 6 && offset < total; k++) {
                    const count = Math.min(CHUNK, total - offset);
                    const data = new Array(CHUNK).fill(0);
                    for (let i = 0; i < count; i++) data[i] = mono[offset + i];
                    this.pc.sendEventOrValue("sampleBank2V2Load", { offset, count, total, data });
                    offset += count;
                }
                if (offset >= total) {
                    this.cancelS2Load();
                    const secs = (total / dec.rate).toFixed(2);
                    const label = name + " " + secs + "s";
                    this._s2State[idx] = label;
                    this._s2Store.set(idx, { name: label, total, data: mono });
                    this.persistS2(idx);
                    this.updateS2Ui();
                    this.setS2Status("LOADED S2 " + (idx + 1));
                    const lvl = this._controls.get("param192");
                    if (lvl && lvl.value < 0.05) lvl.setValue(0.8, true);
                } else {
                    this.setS2Dz("LOADING S2 " + (idx + 1) + " " + Math.round(offset / total * 100) + "%", "busy");
                }
            }, 6);
        } catch (err) {
            this.cancelS2Load();
            this.setS2Dz("UNSUPPORTED FILE", "err");
        }
    }

    // UI -> DSP: stream persisted sampler 2 memories back, selecting each memory in turn
    startS2Restore () {
        const queue = Array.from(this._s2Store.keys());
        if (!queue.length) { this.setS2Status("NO SAVED SAMPLES"); return; }
        const orig = this.curS2();
        let cur = null, off = 0;
        this._s2Restoring = true;
        this.setS2Status("RESTORING " + queue.length + " MEMORY(S)");
        this._s2RestoreTimer = setInterval(() => {
            if (!cur) {
                if (!queue.length) {
                    clearInterval(this._s2RestoreTimer); this._s2RestoreTimer = null;
                    this._s2Restoring = false;
                    this.pc.sendEventOrValue("param193", orig);
                    const c = this._controls.get("param193");
                    if (c) c.setValue(orig, false);
                    this.updateS2Ui();
                    this.setS2Status("RESTORED");
                    return;
                }
                const idx = queue.shift();
                const s = this._s2Store.get(idx);
                if (!s) return;
                cur = { idx, s };
                off = 0;
                this.pc.sendEventOrValue("param193", idx);
            }
            for (let k = 0; k < 4 && cur && off < cur.s.total; k++) {
                const count = Math.min(CHUNK, cur.s.total - off);
                const data = new Array(CHUNK).fill(0);
                for (let i = 0; i < count; i++) data[i] = cur.s.data[off + i];
                this.pc.sendEventOrValue("sampleBank2V2Load", { offset: off, count, total: cur.s.total, data });
                off += count;
            }
            if (cur && off >= cur.s.total) cur = null;
        }, 8);
    }

    // ---------- dedicated wavetable oscillators (3 engines: own page, level and memory bank each) ----------
    wtKey (e, idx) { return WT_ENG[e].prefix + idx; }

    curWt (e) {
        const c = this._controls.get("param" + WT_ENG[e].mem);
        return Math.max(0, Math.min(WT_COUNT - 1, c ? Math.round(c.value) : 0));
    }

    curFrameLen (e) {
        const c = this._controls.get("param" + WT_ENG[e].size);
        const k = Math.max(0, Math.min(4, c ? Math.round(c.value) : 3));
        return FRAME_SIZES[k];
    }

    setWtStatus (e, text) {
        const el = this.querySelector('.wt-status[data-e="' + e + '"]');
        if (el) el.textContent = text;
    }

    setWtDz (e, text, cls) {
        this.querySelectorAll('.dz-wtl[data-e="' + e + '"]').forEach(dz => {
            dz.querySelector(".dz-txt").textContent = text;
            dz.classList.toggle("loaded", cls === "loaded");
            dz.classList.toggle("busy", cls === "busy");
            dz.classList.toggle("err", cls === "err");
        });
    }

    loadWtStore (e) {
        const w = this._wt[e];
        for (let i = 0; i < WT_COUNT; i++) {
            try {
                if (w.store.has(i)) continue;
                const m = decodeMem(this.kvGet(this.wtKey(e, i)), "TABLE");
                if (!m) continue;
                w.store.set(i, m);
                w.state[i] = m.name;
            } catch (_) {}
        }
    }

    persistWt (e, idx) {
        const s = this._wt[e].store.get(idx);
        try {
            if (!s) { this.kvRemove(this.wtKey(e, idx)); return; }
            this.kvSet(this.wtKey(e, idx), encodeMem(s));
        } catch (_) {
            this.setWtStatus(e, "STORAGE FULL");
        }
    }

    buildWtPage (e) {
        const cfg = WT_ENG[e];
        this.querySelectorAll('.wc[data-e="' + e + '"]').forEach(b => {
            b.setAttribute("tabindex", "-1");
            b.addEventListener("click", () => {
                const i = parseInt(b.dataset.i, 10);
                const c = this._controls.get("param" + cfg.mem);
                if (c && Number.isFinite(i)) c.setValue(i, true);
                b.blur();
            });
        });
        const dz = this.querySelector('.dz-wtl[data-e="' + e + '"]');
        if (!dz) return;
        dz.addEventListener("dragover", ev => { ev.preventDefault(); dz.classList.add("over"); });
        dz.addEventListener("dragleave", () => dz.classList.remove("over"));
        dz.addEventListener("drop", ev => {
            ev.preventDefault(); dz.classList.remove("over");
            const f = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
            if (f) this.loadWavetable(e, f);
        });
        dz.addEventListener("click", () => {
            const inp = document.createElement("input");
            inp.type = "file"; inp.accept = "audio/*,.wav,.aif,.aiff,.mp3,.ogg,.flac";
            inp.onchange = () => { if (inp.files && inp.files[0]) this.loadWavetable(e, inp.files[0]); };
            inp.click();
        });
        const clr = dz.querySelector(".dz-clr");
        if (clr) clr.addEventListener("click", ev => { ev.stopPropagation(); this.clearWavetable(e); });
    }

    updateWtUi (e) {
        const cfg = WT_ENG[e];
        const w = this._wt[e];
        const idx = this.curWt(e);
        const nm = w.state[idx];
        this.querySelectorAll('.wc[data-e="' + e + '"]').forEach(b => {
            const i = parseInt(b.dataset.i, 10);
            const has = !!w.state[i];
            b.classList.toggle("has", has);
            b.classList.toggle("sel", i === idx);
            b.title = cfg.name + " " + (i + 1) + (has ? " / " + w.state[i] : " / EMPTY");
        });
        if (!w.timer) this.setWtDz(e, nm ? cfg.name + " " + (idx + 1) + " / " + nm : WT_DZ_EMPTY, nm ? "loaded" : "");
        this.drawWt(e);
    }

    // interpolated single cycle at the current position / frame size
    wtCycle (e, W) {
        const s = this._wt[e].store.get(this.curWt(e));
        if (!s || s.total < 2) return null;
        const fl = Math.max(2, Math.min(this.curFrameLen(e), s.total));
        const nF = Math.max(1, Math.floor(s.total / fl));
        const pc = this._controls.get("param" + WT_ENG[e].pos);
        const pos = pc ? pc.value : 0;
        const p = Math.max(0, Math.min(1, pos)) * (nF - 1);
        const fa = Math.max(0, Math.min(nF - 1, Math.floor(p)));
        const fb = Math.min(nF - 1, fa + 1);
        const ff = p - fa;
        const out = new Float32Array(W);
        for (let x = 0; x < W; x++) {
            const i = Math.min(fl - 1, Math.floor(x / W * fl));
            const a = s.data[fa * fl + i] || 0;
            const b = s.data[fb * fl + i] || 0;
            out[x] = a * (1 - ff) + b * ff;
        }
        // the DSP removes the DC of every frame, so show the cycle without it
        let mean = 0;
        for (let x = 0; x < W; x++) mean += out[x];
        mean /= W;
        for (let x = 0; x < W; x++) out[x] -= mean;
        return { cyc: out, nF, frame: p + 1, name: s.name };
    }

    // current warp slots of an engine: [mode1, amount1, mode2, amount2]
    wtWarpState (e) {
        const w = WT_ENG[e].warp;
        const v = i => { const c = this._controls.get("param" + w[i]); return c ? c.value : 0; };
        return [Math.round(v(0)), v(1), Math.round(v(2)), v(3)];
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

    // ---------- filter visualizers ----------
    fltVal (id) {
        const c = this._controls.get("param" + id);
        return c ? c.value : SPEC_BY_NUM.get(id).init;
    }

    // magnitude response (dB) of one filter (type id, cutoff id, reso id, mix id) on a log frequency grid
    fltCurve (tId, cId, rId, mId, N, sweep) {
        const ft = Math.round(this.fltVal(tId)), fc = this.fltVal(cId), res = this.fltVal(rId), mix = this.fltVal(mId);
        const out = [];
        for (let i = 0; i < N; i++) {
            const f = 20 * Math.pow(1000, i / (N - 1));
            let h = filterH(ft, fc, res, f, sweep);
            h = cAdd([1 - mix, 0], cSc(h, mix));
            out.push(h);
        }
        return out;
    }

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

    drawFlt () {
        const N = 220;
        const c1 = this.querySelector('.flt-canvas[data-f="1"]');
        const c2 = this.querySelector('.flt-canvas[data-f="2"]');
        const cc = this.querySelector('.flt-canvas[data-f="c"]');
        const on2 = this.fltVal(526) > 0.5;
        const h1 = this.fltCurve(12, 13, 14, 525, N);
        const h2 = this.fltCurve(527, 528, 529, 531, N);
        if (c1) {
            const fr = this.fltFrame(c1);
            if (fr) {
                const ft = Math.round(this.fltVal(12));
                if (ft === 28 || ft === 29) {
                    this.fltTrace(fr, this.fltCurve(12, 13, 14, 525, N, 0.5), "rgba(255,150,130,0.35)", 1, false, true);
                    this.fltTrace(fr, this.fltCurve(12, 13, 14, 525, N, 1.5), "rgba(255,150,130,0.35)", 1, false, true);
                }
                this.fltTrace(fr, h1, "#ff3b30", 2.5, true, false);
                this.fltCutMark(fr, this.fltVal(13));
            }
        }
        if (c2) {
            const fr = this.fltFrame(c2);
            if (fr) {
                const ft = Math.round(this.fltVal(527));
                if (ft === 28 || ft === 29) {
                    this.fltTrace(fr, this.fltCurve(527, 528, 529, 531, N, 0.5), "rgba(255,150,130,0.35)", 1, false, true);
                    this.fltTrace(fr, this.fltCurve(527, 528, 529, 531, N, 1.5), "rgba(255,150,130,0.35)", 1, false, true);
                }
                if (on2) { this.fltTrace(fr, h2, "#ff3b30", 2.5, true, false); this.fltCutMark(fr, this.fltVal(528)); }
                else this.fltTrace(fr, h2, "rgba(180,170,165,0.45)", 1.5, false, true);
            }
        }
        if (cc) {
            const fr = this.fltFrame(cc);
            if (fr) {
                const par = this.fltVal(534) > 0.5, bl = this.fltVal(535);
                const tot = h1.map((a, i) => {
                    if (!on2) return a;
                    if (par) return cAdd(cSc(a, 1 - bl), cSc(h2[i], bl));
                    return cMul(a, h2[i]);
                });
                // in parallel mode filter 2 is fed from the unfiltered signal; in serial it follows filter 1
                this.fltTrace(fr, h1, "rgba(255,150,130,0.40)", 1, false, true);
                if (on2) this.fltTrace(fr, h2, "rgba(255,190,120,0.40)", 1, false, true);
                this.fltTrace(fr, tot, "#ff3b30", 2.5, true, false);
            }
        }
    }

    drawWt (e) {
        const cv = this.querySelector('.wt-canvas[data-e="' + e + '"]');
        const info = this.querySelector('.wt-info[data-e="' + e + '"]');
        if (!cv) return;
        const ctx = cv.getContext("2d");
        if (!ctx) return;
        const W = cv.width, H = cv.height;
        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = "#0d0404";
        ctx.fillRect(0, 0, W, H);
        // HUD grid, centre line and corner brackets
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
        const r = this.wtCycle(e, W);
        if (!r) { if (info) info.textContent = "EMPTY"; return; }
        const ws = this.wtWarpState(e);
        const warped = this.warpCycle(r.cyc, ws);
        let tag = "";
        if (warped) tag = " / WARP " + [0, 2].filter(k => ws[k] > 0).map(k => WARP_MODES[ws[k]]).join(" + ");
        if (info) info.textContent = r.name + " / FRAME " + r.frame.toFixed(1) + " OF " + r.nF + tag;
        const trace = (arr, color, lw) => {
            ctx.strokeStyle = color;
            ctx.lineWidth = lw;
            ctx.shadowColor = "rgba(255,59,48,0.9)";
            ctx.shadowBlur = lw > 1 ? 8 : 0;
            ctx.beginPath();
            for (let x = 0; x < W; x++) {
                const y = H / 2 - Math.max(-1.2, Math.min(1.2, arr[x])) * (H / 2 - 4);
                if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
            ctx.shadowBlur = 0;
        };
        if (warped) {
            trace(r.cyc, "rgba(255,150,140,0.40)", 1);
            trace(warped, "#ff7a45", 2);
        } else {
            trace(r.cyc, "#ff3b30", 2);
        }
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

    cancelWtLoad (e) {
        const w = this._wt[e];
        if (w.timer) { clearInterval(w.timer); w.timer = null; }
    }

    clearWavetable (e) {
        const cfg = WT_ENG[e];
        const w = this._wt[e];
        this.cancelWtLoad(e);
        const idx = this.curWt(e);
        this.pc.sendEventOrValue(cfg.ep, { offset: 0, count: 0, total: 0, data: new Array(CHUNK).fill(0) });
        this.libUntrack("wt" + e);
        w.state[idx] = null;
        w.store.delete(idx);
        this.persistWt(e, idx);
        this.updateWtUi(e);
        this.setWtStatus(e, cfg.name + " " + (idx + 1) + " CLEARED");
    }

    async loadWavetable (e, file, libId) {
        const cfg = WT_ENG[e];
        const w = this._wt[e];
        this.cancelWtLoad(e);
        const idx = this.curWt(e);
        this.setWtDz(e, "DECODING...", "busy");
        try {
            const dec = await this.decodeFile(file);
            this.libTrack("wt" + e, file, libId, dec);
            const mono = dec.mono;
            const total = dec.len;
            const name = (file.name || "TABLE").replace(/\.[^.]+$/, "").slice(0, 14).toUpperCase();
            const fc = this._controls.get("param" + cfg.size);
            if (fc) fc.setValue(this.pickFrameIndex(total), true);
            let offset = 0;
            this.setWtDz(e, "LOADING " + cfg.name + " " + (idx + 1) + " 0%", "busy");
            w.timer = setInterval(() => {
                for (let k = 0; k < 6 && offset < total; k++) {
                    const count = Math.min(CHUNK, total - offset);
                    const data = new Array(CHUNK).fill(0);
                    for (let i = 0; i < count; i++) data[i] = mono[offset + i];
                    this.pc.sendEventOrValue(cfg.ep, { offset, count, total, data });
                    offset += count;
                }
                if (offset >= total) {
                    this.cancelWtLoad(e);
                    w.state[idx] = name;
                    w.store.set(idx, { name, total, data: mono });
                    this.persistWt(e, idx);
                    this.updateWtUi(e);
                    this.setWtStatus(e, "LOADED " + cfg.name + " " + (idx + 1));
                    const lvl = this._controls.get("param" + cfg.lvl);
                    if (lvl && lvl.value < 0.05) lvl.setValue(0.8, true);
                } else {
                    this.setWtDz(e, "LOADING " + cfg.name + " " + (idx + 1) + " " + Math.round(offset / total * 100) + "%", "busy");
                }
            }, 6);
        } catch (err) {
            this.cancelWtLoad(e);
            this.setWtDz(e, "UNSUPPORTED FILE", "err");
        }
    }

    // UI -> DSP: stream persisted wavetables back, selecting each memory in turn
    startWtRestore (e) {
        const cfg = WT_ENG[e];
        const w = this._wt[e];
        const memId = "param" + cfg.mem;
        const queue = Array.from(w.store.keys());
        if (!queue.length) { this.setWtStatus(e, "NO SAVED TABLES"); return; }
        const orig = this.curWt(e);
        let cur = null, off = 0;
        w.restoring = true;
        this.setWtStatus(e, "RESTORING " + queue.length + " TABLE(S)");
        w.restoreTimer = setInterval(() => {
            if (!cur) {
                if (!queue.length) {
                    clearInterval(w.restoreTimer); w.restoreTimer = null;
                    w.restoring = false;
                    this.pc.sendEventOrValue(memId, orig);
                    const c = this._controls.get(memId);
                    if (c) c.setValue(orig, false);
                    this.updateWtUi(e);
                    this.setWtStatus(e, "RESTORED");
                    return;
                }
                const idx = queue.shift();
                const s = w.store.get(idx);
                if (!s) return;
                cur = { idx, s };
                off = 0;
                this.pc.sendEventOrValue(memId, idx);
            }
            for (let k = 0; k < 4 && cur && off < cur.s.total; k++) {
                const count = Math.min(CHUNK, cur.s.total - off);
                const data = new Array(CHUNK).fill(0);
                for (let i = 0; i < count; i++) data[i] = cur.s.data[off + i];
                this.pc.sendEventOrValue(cfg.ep, { offset: off, count, total: cur.s.total, data });
                off += count;
            }
            if (cur && off >= cur.s.total) cur = null;
        }, 8);
    }

    // ---------- parameter hooks ----------
    onValue (spec, v, user) {
        const n = spec.num;
        if (n >= 600 && n < 780 && (n - 600) % 9 === 0) this.updateFxRack();
        if (n >= 600 && n < 780 && (n - 600) % 9 === 0 && user && !this._applying) this.activateFxSlot((n - 600) / 9, v);
        if (FLT_VIS_IDS.indexOf(n) >= 0) this.drawFlt();
        if (n === 154) this.updateSmpName();
        if (n === 193) this.updateS2Ui();
        if ((n >= 307 && n <= 336) || (n >= 472 && n <= 501)) this.updateSlots();
        for (let e = 0; e < WT_ENG.length; e++) {
            const cfg = WT_ENG[e];
            if (n === cfg.mem) this.updateWtUi(e);
            if (n === cfg.pos || n === cfg.size || cfg.warp.indexOf(n) >= 0) this.drawWt(e);
        }
        if (n === 147 && v > 0.5 && user) {
            this.setMgr("SAVING ALL...");
            const c = this._controls.get("param147");
            if (this._saveTimer) clearTimeout(this._saveTimer);
            this._saveTimer = setTimeout(() => { if (c) c.setValue(0, true); }, 400);
        }
        if (user && this.presetDirty) this.presetDirty();
        if (user) {
            const a = this.querySelector(".lcd-name");
            const b = this.querySelector(".lcd-val");
            if (a) a.textContent = spec.label.toUpperCase();
            if (b) b.textContent = fmt(spec, v);
        }
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

    faderHTML (id) {
        const s = SPEC_BY_NUM.get(id);
        const attrs = `data-param="${s.id}" data-min="${s.min}" data-max="${s.max}" data-step="0" data-init="${s.init}"`;
        return `<div class="control fdr" ${attrs} data-control="slider" data-widget="fader"><span class="val">--</span><div class="ftrack"><div class="frail"></div><div class="ffill"></div><div class="fthumb"></div></div></div>`;
    }

    // SSL 4000 style EQ block for one mixer channel (rotary knobs, one row per band)
    eqHTML (ei) {
        const base = EQ_BASE[ei];
        let h = `<div class="eq"><div class="eqin">${this.controlHTML(base + 10)}</div>`;
        EQ_BANDS.forEach(b => {
            h += `<div class="eqb">${b[0]}</div><div class="eqrow k${b[1].length}">`;
            b[1].forEach(off => { h += `<div class="eqk">${this.controlHTML(base + off)}</div>`; });
            h += `</div>`;
        });
        return h + `</div>`;
    }

    channelHTML (c) {
        const solo = c.s ? this.controlHTML(c.s) : `<div class="solo-sp"></div>`;
        const eq = c.eq !== undefined ? this.eqHTML(c.eq) : "";
        return `<div class="ch ${c.cls || ""}"><div class="chname">${c.n}</div>${eq}${this.faderHTML(c.p)}${solo}</div>`;
    }

    card (title, ids, cls, extra, pre) {
        return `<section class="card ${cls || ""}"><h2>${title}</h2>${pre || ""}<div class="cgrid">${ids.map(i => this.controlHTML(i, true)).join("")}</div>${extra || ""}</section>`;
    }

    fxSlotHTML (slot) {
        const base = FX_SLOT_BASE(slot);
        const cfg = FX_SLOT_INIT[slot];
        const macros = Array.from({ length: 6 }, (_, i) => this.controlHTML(base + 3 + i, true)).join("");
        return `<section class="card fx-slot" data-fx-slot="${slot}">
            <header class="fxslot-head" draggable="true" data-fx-handle="${slot}">
                <span class="fxslot-number">${String(slot + 1).padStart(2, "0")}</span>
                <b class="fxslot-title" data-fx-title="${slot}">${FX_SLOT_TYPES[cfg.type]}</b>
                <span class="fxslot-grip" title="Drag to reorder">⠿</span>
            </header>
            <div class="fxslot-config cgrid">${this.controlHTML(base, true)}${this.controlHTML(base + 1, true)}</div>
            <div class="fxslot-variation cgrid">${this.controlHTML(FX_SLOT_VARIATION_BASE + slot, true)}</div>
            <div class="fxslot-macros cgrid">${macros}</div>
            <div class="fx-order-hidden">${this.controlHTML(base + 2)}</div>
        </section>`;
    }

    fxOrder (slot) {
        const c = this._controls.get("param" + (FX_SLOT_BASE(slot) + 2));
        return c ? c.value : slot;
    }

    activateFxSlot (slot, type) {
        if (type <= 0 || type > 9 || slot < 0 || slot >= FX_SLOT_COUNT) return;
        const base = FX_SLOT_BASE(slot);
        const power = this._controls.get("param" + (base + 1));
        if (power && power.value < 0.5) power.setValue(1, true);
        const macros = Array.from({ length: 6 }, (_, i) => this._controls.get("param" + (base + 3 + i)));
        if (macros.some(c => !c)) return;
        // A freshly activated empty slot receives useful defaults. Existing configured modules keep their settings.
        if (macros.every(c => Math.abs(c.value) < 0.000001)) {
            const defaults = {
                1: [0.25, 1, 0, 0, 0.5, 0],
                2: [0.35, 0.25, 0.5, 0.5, 0.5, 0.8],
                3: [0.35, 0.2, 0.5, 0.1, 0, 0],
                4: [0.25, 0.15, 0.6, 0.4, 0, 0.5],
                5: [0.3, 0.1, 0.5, 0.25, 0.3333, 0.5],
                6: [0.25, 0.5, 0.5, 0.1, 1, 0],
                7: [0.35, 0.25, 0, 0, 0.5, 1],
                8: [0.6, 0.1, 0.8, 0, 0, 0],
                9: [0.5, 0.2, 1, 0, 0.33, 0]
            }[Math.round(type)];
            if (defaults) defaults.forEach((v, i) => macros[i].setValue(v, true));
        }
        this.updateFxRack();
    }

    updateFxRack () {
        const grid = this.querySelector(".fx-slot-grid");
        if (!grid) return;
        const cards = Array.from(grid.querySelectorAll(".fx-slot"));
        cards.forEach(card => {
            const slot = Number(card.dataset.fxSlot);
            const base = FX_SLOT_BASE(slot);
            const ctrl = this._controls.get("param" + base);
            const type = Math.max(0, Math.min(9, Math.round(ctrl ? ctrl.value : FX_SLOT_INIT[slot].type)));
            const title = card.querySelector("[data-fx-title]");
            if (title) title.textContent = type === 0 ? "EMPTY SLOT" : FX_SLOT_TYPES[type].toUpperCase();
            const labels = FX_SLOT_MACROS[type] || FX_SLOT_MACROS[0];
            for (let m = 0; m < 6; m++) {
                const label = card.querySelector('[data-param="param' + (base + 3 + m) + '"] .lbl');
                if (label) label.textContent = labels[m] || ("Macro " + String.fromCharCode(65 + m));
            }
            const variation = this._controls.get("param" + (FX_SLOT_VARIATION_BASE + slot));
            const variantLabels = FX_SLOT_VARIATIONS_BY_TYPE[type] || FX_SLOT_VARIATIONS_BY_TYPE[0];
            if (variation && variation.sel) {
                variation.spec.labels = variantLabels;
                variation.sel.innerHTML = variantLabels.map(label => '<option>' + label + '</option>').join("");
                variation.sel.selectedIndex = Math.max(0, Math.min(5, Math.round(variation.value)));
                if (variation.valEl) variation.valEl.textContent = fmt(variation.spec, variation.value);
            }
            const power = this._controls.get("param" + (base + 1));
            card.classList.toggle("fx-slot-off", type === 0 || (power ? power.value : FX_SLOT_INIT[slot].enabled) < 0.5);
        });
        const sorted = cards.slice().sort((a, b) =>
            this.fxOrder(Number(a.dataset.fxSlot)) - this.fxOrder(Number(b.dataset.fxSlot)) ||
            Number(a.dataset.fxSlot) - Number(b.dataset.fxSlot));
        sorted.forEach((card, index) => {
            grid.appendChild(card);
            const ordinal = card.querySelector(".fxslot-number");
            if (ordinal) ordinal.textContent = String(index + 1).padStart(2, "0");
        });
        const chain = this.querySelector(".fx-chain");
        if (chain) chain.innerHTML = sorted.map((card, i) => {
            const slot = Number(card.dataset.fxSlot);
            const base = FX_SLOT_BASE(slot);
            const c = this._controls.get("param" + base);
            const power = this._controls.get("param" + (base + 1));
            const type = Math.round(c ? c.value : FX_SLOT_INIT[slot].type);
            const title = type === 0 ? "EMPTY" : FX_SLOT_TYPES[type].toUpperCase();
            const enabled = type !== 0 && (power ? power.value : FX_SLOT_INIT[slot].enabled) >= 0.5;
            const variation = this._controls.get("param" + (FX_SLOT_VARIATION_BASE + slot));
            const variantLabels = FX_SLOT_VARIATIONS_BY_TYPE[type] || FX_SLOT_VARIATIONS_BY_TYPE[0];
            const variantName = variation ? variantLabels[Math.max(0, Math.min(5, Math.round(variation.value)))] : variantLabels[0];
            return '<span class="fx-chain-node' + (!enabled ? ' disabled' : '') + '"><b>' +
                String(i + 1).padStart(2, "0") + '</b>' + title + '<small>' + variantName + '</small></span>';
        }).join("");
    }

    bindFxRackDnD () {
        const grid = this.querySelector(".fx-slot-grid");
        if (!grid || grid.dataset.dndBound) return;
        grid.dataset.dndBound = "1";
        grid.addEventListener("dragstart", ev => {
            const handle = ev.target.closest("[data-fx-handle]");
            if (!handle) { ev.preventDefault(); return; }
            this._fxDragSlot = Number(handle.dataset.fxHandle);
            if (ev.dataTransfer) {
                ev.dataTransfer.effectAllowed = "move";
                ev.dataTransfer.setData("text/plain", String(this._fxDragSlot));
            }
            const card = handle.closest(".fx-slot");
            if (card) card.classList.add("fx-dragging");
        });
        grid.addEventListener("dragover", ev => {
            const card = ev.target.closest(".fx-slot");
            if (this._fxDragSlot === undefined || !card) return;
            ev.preventDefault();
            if (ev.dataTransfer) ev.dataTransfer.dropEffect = "move";
            grid.querySelectorAll(".fx-drop-target").forEach(n => n.classList.remove("fx-drop-target"));
            card.classList.add("fx-drop-target");
        });
        grid.addEventListener("dragleave", ev => {
            const card = ev.target.closest(".fx-slot");
            if (card && !card.contains(ev.relatedTarget)) card.classList.remove("fx-drop-target");
        });
        grid.addEventListener("drop", ev => {
            const card = ev.target.closest(".fx-slot");
            if (this._fxDragSlot === undefined || !card) return;
            ev.preventDefault();
            const from = this._fxDragSlot;
            const to = Number(card.dataset.fxSlot);
            this._fxDragSlot = undefined;
            grid.querySelectorAll(".fx-dragging,.fx-drop-target").forEach(n =>
                n.classList.remove("fx-dragging", "fx-drop-target"));
            if (from !== to) this.reorderFxSlots(from, to);
        });
        grid.addEventListener("dragend", () => {
            this._fxDragSlot = undefined;
            grid.querySelectorAll(".fx-dragging,.fx-drop-target").forEach(n =>
                n.classList.remove("fx-dragging", "fx-drop-target"));
        });
    }

    reorderFxSlots (fromSlot, toSlot) {
        const grid = this.querySelector(".fx-slot-grid");
        if (!grid) return;
        const ordered = Array.from(grid.querySelectorAll(".fx-slot"))
            .sort((a, b) => this.fxOrder(Number(a.dataset.fxSlot)) - this.fxOrder(Number(b.dataset.fxSlot)) ||
                Number(a.dataset.fxSlot) - Number(b.dataset.fxSlot))
            .map(card => Number(card.dataset.fxSlot));
        const from = ordered.indexOf(fromSlot), to = ordered.indexOf(toSlot);
        if (from < 0 || to < 0 || from === to) return;
        ordered.splice(to, 0, ordered.splice(from, 1)[0]);
        ordered.forEach((slot, position) => {
            const c = this._controls.get("param" + (FX_SLOT_BASE(slot) + 2));
            if (c) c.setValue(position, true);
        });
        this.updateFxRack();
        this.presetDirty();
    }

    wtPageHTML (e) {
        const cfg = WT_ENG[e];
        const wcells = Array.from({ length: WT_COUNT }, (_, i) => `<button type="button" class="wc" data-e="${e}" data-i="${i}">${i + 1}</button>`).join("");
        const label = "Wavetable " + (e + 1);
        const strip = `<div class="wt-top"><div class="memstrip"><div class="ms-main"><div class="dz dz-wtl" data-e="${e}"><span class="dz-txt">${WT_DZ_EMPTY}</span><span class="dz-clr" title="Clear selected wavetable">&times;</span></div><div class="wt-status" data-e="${e}">READY</div></div><button type="button" class="pb dz-lib" data-slot="wt${e}" title="Open the sound vault">VAULT</button><div class="cgrid ms-hid">${this.controlHTML(cfg.mem)}</div><div class="wmem">${wcells}</div></div><div class="wt-cv"><canvas class="wt-canvas" data-e="${e}" width="600" height="120"></canvas><div class="wtrow"><span class="lbl">Table</span><span class="val wt-info" data-e="${e}">--</span></div></div></div>`;
        return `<section class="card w-osc"><h2>${label} Oscillator</h2>${strip}<div class="cgrid">${cfg.ids.map(i => this.controlHTML(i, true)).join("")}</div></section>`
            + `<section class="card w-uni"><h2>${label} Unison</h2><div class="cgrid">${cfg.uni.map(i => this.controlHTML(i, true)).join("")}</div></section>`
            + `<section class="card w-warp"><h2>${label} Warp</h2><div class="cgrid">${cfg.warp.map(i => this.controlHTML(i, true)).join("")}</div></section>`;
    }

    // LFO page: 10 LFOs (wave selector + rate)
    lfoPageHTML () {
        let lfo = `<div class="mhead lfo-c"><span></span><span>Wave</span><span>Rate</span><span>Sync</span><span>Division</span></div>`;
        for (let i = 0; i < 10; i++)
            lfo += `<div class="mrow lfo-c"><span class="mn">L${i + 1}</span>${this.controlHTML(247 + 2 * i)}${this.controlHTML(248 + 2 * i)}${this.controlHTML(502 + 2 * i)}${this.controlHTML(503 + 2 * i)}</div>`;
        return `<section class="card m-lfo"><h2>LFOs</h2><div class="mgrid">${lfo}</div><div class="lfoft">${this.controlHTML(522)}</div></section>`;
    }

    // envelope page: 10 ADSR envelopes
    envPageHTML () {
        let env = `<div class="mhead env-c"><span></span><span>Attack</span><span>Decay</span><span>Sustain</span><span>Release</span></div>`;
        for (let i = 0; i < 10; i++) {
            const b = 267 + 4 * i;
            env += `<div class="mrow env-c"><span class="mn">E${i + 1}</span>${this.controlHTML(b)}${this.controlHTML(b + 1)}${this.controlHTML(b + 2)}${this.controlHTML(b + 3)}</div>`;
        }
        return `<section class="card m-env"><h2>Envelopes</h2><div class="mgrid">${env}</div></section>`;
    }

    // mod page: the 20-slot modulation matrix, two columns of 10 slots
    modPageHTML () {
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
        return `<section class="card m-mtx"><h2>Mod Matrix</h2><div class="mtx2">${cols}</div></section>`;
    }

    getHTML () {
        const cells = Array.from({ length: MEM_COUNT }, (_, i) => `<button type="button" class="mc" data-i="${i}">${i + 1}</button>`).join("");
        const memStrip = `<div class="memstrip"><div class="ms-main"><div class="dz dz-smp"><span class="dz-txt">${SMP_DZ_EMPTY}</span><span class="dz-clr" title="Clear selected memory">&times;</span></div><div class="mgr-status">READY</div></div><button type="button" class="pb dz-lib" data-slot="smp" title="Open the sound vault">VAULT</button><div class="cgrid ms-ctl">${MEM_IDS.map(i => this.controlHTML(i, true)).join("")}</div><div class="memgrid">${cells}</div></div>`;
        const synth = SYNTH_CARDS.map(c => this.card(c[0], c[2], c[1])).join("");
        const fcv = k => `<canvas class="flt-canvas" data-f="${k}" width="600" height="${k === "c" ? 200 : 290}"></canvas>`;
        const fltPage = this.card("Filter 1", FLT_CARDS[0][2], "x-f1", "", fcv("1"))
                      + this.card("Routing / Output", FLT_CARDS[2][2], "x-rt", "", fcv("c"))
                      + this.card("Filter EG", FLT_CARDS[3][2], "x-feg")
                      + this.card("Filter 2", FLT_CARDS[1][2], "x-f2", "", fcv("2"));
        const oscCard = `<section class="card m-osc"><h2><span class="osc-title">Sample Oscillator</span></h2>${memStrip}<div class="cgrid">${SMP_IDS.map(i => this.controlHTML(i, true)).join("")}</div></section>`;
        const smpPage = oscCard;
        const scells = Array.from({ length: S2_COUNT }, (_, i) => `<button type="button" class="sc" data-i="${i}">${i + 1}</button>`).join("");
        const s2Strip = `<div class="memstrip"><div class="ms-main"><div class="dz dz-s2"><span class="dz-txt">${S2_DZ_EMPTY}</span><span class="dz-clr" title="Clear selected memory">&times;</span></div><div class="s2-status">READY</div></div><button type="button" class="pb dz-lib" data-slot="s2" title="Open the sound vault">VAULT</button><div class="cgrid ms-hid">${this.controlHTML(193)}</div><div class="smem">${scells}</div></div>`;
        const s2Page = `<section class="card s2-osc"><h2>Sampler 2 Oscillator</h2>${s2Strip}<div class="cgrid">${S2_IDS.map(i => this.controlHTML(i, true)).join("")}</div></section>`;
        const wtPages = WT_ENG.map((cfg, e) => `<div class="page p-${cfg.page}">${this.wtPageHTML(e)}</div>`).join("\n    ");
        const mixPage = `<section class="card m-mix"><h2>Mixer / SSL 4000 EQ</h2><div class="chs">${MIX_CH.map(c => this.channelHTML(c)).join("")}</div></section>`;
        const fxRackBar = `<div class="fx-rackbar"><div class="fx-rack-title"><span class="fx-rack-led"></span><span>FX RACK</span><small>20 SLOTS · DRAG TO REORDER · TYPE ADDS MODULE · VARIATION CHANGES CHARACTER</small></div><div class="fx-chain"></div></div>`;
        const fxPage = fxRackBar
                     + `<div class="fx-slot-grid">${Array.from({ length: FX_SLOT_COUNT }, (_, i) => this.fxSlotHTML(i)).join("")}</div>`
                     + this.card("Output", FX_OUT, "f-out");
        const lfoPage = this.lfoPageHTML();
        const envPage = this.envPageHTML();
        const modPage = this.modPageHTML();
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
  eisenpuls-view[data-page="sound"] .p-synth { display: grid; }
  eisenpuls-view[data-page="flt"] .p-flt { display: grid; }
  eisenpuls-view[data-page="smp"] .p-smp { display: grid; }
  eisenpuls-view[data-page="s2"] .p-s2 { display: grid; }
  eisenpuls-view[data-page="wt1"] .p-wt1 { display: grid; }
  eisenpuls-view[data-page="wt2"] .p-wt2 { display: grid; }
  eisenpuls-view[data-page="wt3"] .p-wt3 { display: grid; }
  eisenpuls-view[data-page="lfo"] .p-lfo { display: grid; }
  eisenpuls-view[data-page="env"] .p-env { display: grid; }
  eisenpuls-view[data-page="mod"] .p-mod { display: grid; }
  eisenpuls-view[data-page="mix"] .p-mix { display: grid; }
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

  /* sound page */
  .p-synth { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 1fr) minmax(0, 1fr); }
  .s-voice  { grid-column: 1 / span 2;  grid-row: 1; }
  .s-osc    { grid-column: 3 / span 7;  grid-row: 1; } .s-osc .cgrid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .s-amp    { grid-column: 10 / span 3; grid-row: 1; } .s-amp .cgrid { grid-template-columns: 1fr 1fr; }
  .s-lfo    { grid-column: 1 / span 6;  grid-row: 2; } .s-lfo .cgrid { grid-template-columns: 1fr 1fr; }
  .s-ss     { grid-column: 7 / span 6;  grid-row: 2; } .s-ss .cgrid { grid-template-columns: 1fr 1fr; }

  /* filter page */
  .p-flt { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 1fr) minmax(0, 1fr); }
  .x-f1  { grid-column: 1 / span 4;  grid-row: 1 / span 2; } .x-f1 .cgrid, .x-f2 .cgrid { grid-template-columns: 1fr 1fr; align-content: space-evenly; align-items: center; }
  .x-rt  { grid-column: 5 / span 4;  grid-row: 1; }
  .x-feg { grid-column: 5 / span 4;  grid-row: 2; } .x-feg .cgrid { grid-template-columns: 1fr 1fr; }
  .x-f2  { grid-column: 9 / span 4;  grid-row: 1 / span 2; }
  .flt-canvas { display: block; flex: 0 0 auto; width: 100%; height: calc(var(--u) * 118); margin: calc(var(--u) * 6) 0 calc(var(--u) * 4); background: #0d0404; border: 1px solid #7a1d18; border-radius: calc(var(--u) * 4);
        box-shadow: inset 0 0 14px rgba(0,0,0,0.95), 0 0 14px rgba(255,59,48,0.30); }
  .x-f1 .flt-canvas, .x-f2 .flt-canvas { height: calc(var(--u) * 170); }
  .x-f1 .n12, .x-f2 .n527, .x-f2 .n526 { grid-column: 1 / -1; }

  /* sampler page */
  .p-smp { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 1fr); }
  .m-mem { grid-column: 1 / span 5; grid-row: 1; }
  .m-mem .cgrid { flex: 0 0 auto; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: calc(var(--u) * 4); }
  .m-mem .memgrid { grid-template-columns: repeat(8, minmax(0, 1fr)); gap: calc(var(--u) * 4); margin-top: calc(var(--u) * 8); }
  .m-mem .mc { height: calc(var(--u) * 40); font-size: calc(var(--u) * 11); }
  .m-mem .dz { flex: 1 1 auto; height: auto; min-height: calc(var(--u) * 50); margin-top: calc(var(--u) * 8); font-size: calc(var(--u) * 10); }
  .m-osc { grid-column: 6 / span 7; grid-row: 1; } .m-osc .cgrid { grid-template-columns: 1fr 1fr; align-content: space-evenly; }
  .mgr-status, .wt-status, .s2-status { flex: 0 0 auto; margin-top: calc(var(--u) * 6); padding: calc(var(--u) * 4) calc(var(--u) * 6); border: 1px solid var(--line); border-radius: 1px; background: #110505; box-shadow: inset 0 0 6px rgba(0,0,0,0.9);
          font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 8); letter-spacing: 0.06em; color: var(--yel); text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* sampler 2 page */
  .p-s2 { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 1fr); }
  .s2-mem { grid-column: 1 / span 3; grid-row: 1; }
  .s2-mem .cgrid { flex: 0 0 auto; margin-bottom: calc(var(--u) * 4); }
  .s2-mem .dz { flex: 1 1 auto; height: auto; min-height: calc(var(--u) * 50); margin-top: calc(var(--u) * 8); font-size: calc(var(--u) * 10); }
  .smem { flex: 0 0 auto; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: calc(var(--u) * 4); margin-top: calc(var(--u) * 8); }
  .s2-osc { grid-column: 4 / span 9; grid-row: 1; }
  .s2-osc .cgrid { grid-template-columns: 1fr 1fr; align-content: space-evenly; margin-top: calc(var(--u) * 6); }

  /* wavetable pages (3 engines share the same layout) */
  .p-wt1, .p-wt2, .p-wt3 { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 2.3fr) minmax(0, 1fr); }
  .w-mem { grid-column: 1 / span 3; grid-row: 1 / span 2; }
  .w-mem .cgrid { flex: 0 0 auto; margin-bottom: calc(var(--u) * 4); }
  .w-mem .dz { flex: 1 1 auto; height: auto; min-height: calc(var(--u) * 50); margin-top: calc(var(--u) * 8); font-size: calc(var(--u) * 10); }
  .wmem { flex: 0 0 auto; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: calc(var(--u) * 4); margin-top: calc(var(--u) * 8); }
  .wc, .sc { height: calc(var(--u) * 40); padding: 0; border: 1px solid #000; border-radius: 1px; background: linear-gradient(#3a3f46, #2a2d32); color: var(--dim);
        font-family: inherit; font-size: calc(var(--u) * 11); font-weight: 800; cursor: pointer; }
  .wc:hover, .sc:hover { background: linear-gradient(#4a5058, #34383e); }
  .wc.has, .sc.has { color: var(--yel); background: linear-gradient(#4a1c1a, #2f1311); }
  .wc.sel, .sc.sel { background: var(--yel); color: #111; box-shadow: inset 0 0 5px rgba(0,0,0,0.35); }
  .w-osc { grid-column: 4 / span 6; grid-row: 1; }
  .w-uni { grid-column: 10 / span 3; grid-row: 1; }
  .w-warp { grid-column: 4 / span 9; grid-row: 2; }
  .w-warp .cgrid { grid-template-columns: repeat(4, minmax(0, 1fr)); align-content: center; align-items: center; margin-top: calc(var(--u) * 6); }
  .w-uni .cgrid { grid-template-columns: minmax(0, 1fr); align-content: space-evenly; align-items: center; margin-top: calc(var(--u) * 6); }
  .w-osc .cgrid { grid-template-columns: 1fr 1fr; align-content: space-evenly; margin-top: calc(var(--u) * 6); }
  .w-osc .n212, .w-osc .n226, .w-osc .n238 { grid-column: 1 / -1; }
  .wt-canvas { display: block; flex: 0 0 auto; width: 100%; height: calc(var(--u) * 80); margin-top: calc(var(--u) * 4); background: var(--deep); border: 1px solid var(--line); border-radius: 1px; box-shadow: inset 0 0 8px rgba(0,0,0,0.9); }
  .wtrow { flex: 0 0 auto; display: flex; justify-content: space-between; align-items: baseline; gap: calc(var(--u) * 4); margin-top: calc(var(--u) * 4); }

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
  .p-mix { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
  .chs { flex: 1; min-height: 0; display: flex; gap: calc(var(--u) * 5); padding-top: calc(var(--u) * 4); }
  .ch { flex: 1 1 0; min-width: 0; min-height: 0; display: flex; flex-direction: column; align-items: stretch; gap: calc(var(--u) * 4); padding: calc(var(--u) * 6) calc(var(--u) * 4);
        background: linear-gradient(#1b1d20, #141517); border: 1px solid var(--line); border-radius: 1px; box-shadow: inset 0 0 8px rgba(0,0,0,0.7); }
  .ch.pl { flex: 0.5 1 0; }
  .ch.out { flex: 0.6 1 0; background: linear-gradient(#2b1717, #190d0d); border-color: #8a1d18; }
  .ch.gap { margin-left: calc(var(--u) * 8); }
  .chname { flex: 0 0 auto; text-align: center; font-family: Impact, "Arial Black", "Bahnschrift", sans-serif; font-size: calc(var(--u) * 9.5); letter-spacing: 0.1em; text-transform: uppercase; color: var(--yel); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .solo-sp { flex: 0 0 auto; height: calc(var(--u) * 38); }
  .ch .control.btns { flex: 0 0 auto; }
  .ch .control.btns .row { justify-content: center; }
  .ch .control.btns .val { display: none; }
  .ch .control.btns .lbl { text-align: center; }
  .ch .control.btns .grp button { padding: calc(var(--u) * 6) 0; }
  .fdr { flex: 1 1 0; min-height: 0; display: flex; flex-direction: column; align-items: center; gap: calc(var(--u) * 5); }
  .fdr .val { flex: 0 0 auto; padding: calc(var(--u) * 2) calc(var(--u) * 6); background: #110505; border: 1px solid var(--line); border-radius: 1px; font-size: calc(var(--u) * 10); }
  .fdr.drag .val { color: var(--org); }
  .ftrack { position: relative; flex: 1 1 0; min-height: 0; margin-bottom: calc(var(--u) * 8); width: 100%; cursor: ns-resize; touch-action: none; }
  .frail { position: absolute; left: 50%; top: 0; bottom: 0; width: calc(var(--u) * 8); margin-left: calc(var(--u) * -4); background: var(--deep); border: 1px solid #000; border-radius: 1px;
           box-shadow: inset 0 1px 3px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.06); pointer-events: none;
           background-image: repeating-linear-gradient(0deg, transparent 0 calc(var(--u) * 14), rgba(255,255,255,0.12) calc(var(--u) * 14) calc(var(--u) * 15)); }
  .ffill { position: absolute; left: 50%; width: calc(var(--u) * 5); margin-left: calc(var(--u) * -2.5); bottom: 0; height: 0; background: linear-gradient(0deg, var(--yel), var(--org)); pointer-events: none; }
  .fthumb { position: absolute; left: 50%; bottom: 0; width: calc(var(--u) * 36); height: calc(var(--u) * 16); margin: 0 0 calc(var(--u) * -8) calc(var(--u) * -18); border: 1px solid #000; border-radius: 1px;
            background: linear-gradient(#7a8089 0 38%, var(--yel) 38% 62%, #5a6068 62%); box-shadow: 0 2px 5px rgba(0,0,0,0.8); pointer-events: none; }

  /* SSL 4000 style channel EQ (rotary knobs) */
  .eq { flex: 0 0 auto; display: flex; flex-direction: column; gap: calc(var(--u) * 2); padding: calc(var(--u) * 4) calc(var(--u) * 2); background: rgba(0,0,0,0.32); border: 1px solid #2c2f34; border-radius: 1px; }
  .eqin .control.btns .row { display: none; }
  .eqin .grp { margin-top: 0; }
  .eqin .grp button { padding: calc(var(--u) * 4) 0; font-size: calc(var(--u) * 10); }
  .eqb { font-size: calc(var(--u) * 8.5); font-weight: 800; letter-spacing: 0.16em; color: var(--org); text-align: center; margin-top: calc(var(--u) * 2); border-bottom: 1px dashed #3b3f46; }
  .eqrow { display: grid; column-gap: calc(var(--u) * 3); justify-items: center; }
  .eqrow.k2 { grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 0 calc(var(--u) * 2); }
  .eqrow.k3 { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: calc(var(--u) * 3); }
  .eqrow.k3 .eqk:nth-child(3) { grid-column: 1 / -1; }
  .eqk { min-width: 0; width: 100%; display: flex; justify-content: center; }
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

  /* Serum-inspired modular FX rack */
  .p-fx { grid-template-columns: repeat(4, minmax(0, 1fr)); grid-template-rows: auto minmax(0, 1fr) auto; gap: calc(var(--u) * 7); overflow-y: auto; align-content: start; }
  .fx-rackbar { grid-column: 1 / -1; display: flex; flex-direction: column; gap: calc(var(--u) * 6); padding: calc(var(--u) * 8) calc(var(--u) * 12); min-width: 0; border: 1px solid #4b4e53; border-radius: calc(var(--u) * 5); background: linear-gradient(180deg, #24272b, #111315); box-shadow: inset 0 1px 0 rgba(255,255,255,.07), 0 3px 10px rgba(0,0,0,.25); }
  .fx-rack-title { display: flex; align-items: center; gap: calc(var(--u) * 7); color: #f0e9e6; font-size: calc(var(--u) * 10); font-weight: 900; letter-spacing: .22em; }
  .fx-rack-title small { margin-left: auto; color: #858b91; font-size: calc(var(--u) * 7); font-weight: 700; letter-spacing: .12em; }
  .fx-rack-led { width: calc(var(--u) * 6); height: calc(var(--u) * 6); border-radius: 50%; background: #ff5145; box-shadow: 0 0 8px rgba(255,70,55,.75); }
  .fx-chain { display: flex; align-items: center; gap: calc(var(--u) * 4); overflow-x: auto; padding-bottom: calc(var(--u) * 2); }
  .fx-chain-node { position: relative; flex: 1 0 auto; display: flex; align-items: center; gap: calc(var(--u) * 5); padding: calc(var(--u) * 5) calc(var(--u) * 8); color: #b9bdc2; background: #17191c; border: 1px solid #34383d; border-radius: calc(var(--u) * 3); font-size: calc(var(--u) * 7); font-weight: 800; letter-spacing: .08em; white-space: nowrap; }
  .fx-chain-node b { color: #ff7669; font-family: ui-monospace, monospace; font-size: calc(var(--u) * 7); }
  .fx-chain-node i { position: absolute; right: calc(var(--u) * -5); top: 50%; transform: translate(50%,-50%); z-index: 2; color: #ff6d5e; font-size: calc(var(--u) * 14); font-style: normal; }
  .fx-slot-grid { grid-column: 1 / -1; min-width: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); grid-auto-rows: minmax(0, 1fr); gap: calc(var(--u) * 7); }
  .fxslot-variation { margin-top: calc(var(--u) * 7); }
  .fxslot-variation .control { min-width: 0; }
  .fx-slot { min-width: 0; transition: border-color .12s, opacity .12s, transform .12s; }
  .fxslot-head { display: flex; align-items: center; gap: calc(var(--u) * 7); margin-bottom: calc(var(--u) * 8); cursor: grab; user-select: none; border-bottom: 1px solid #45494f; padding-bottom: calc(var(--u) * 5); }
  .fxslot-head:active { cursor: grabbing; }
  .fxslot-number { color: #ff7b6f; font: 800 calc(var(--u) * 9)/1 ui-monospace, monospace; }
  .fxslot-title { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #f3eae5; font-size: calc(var(--u) * 9); letter-spacing: .14em; }
  .fxslot-grip { margin-left: auto; color: #92999f; font-size: calc(var(--u) * 14); }
  .fxslot-config { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: calc(var(--u) * 7); }
  .fxslot-config .control, .fxslot-macros .control { min-width: 0; }
  .fxslot-macros { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: calc(var(--u) * 7) calc(var(--u) * 6); margin-top: calc(var(--u) * 8); }
  .fx-order-hidden { display: none !important; }
  .fx-slot-off { border-color: #34383c; opacity: .72; }
  .fx-slot.fx-dragging { opacity: .48; transform: scale(.985); }
  .fx-slot.fx-drop-target { border-color: #ff6d5e; box-shadow: 0 0 0 1px rgba(255,109,94,.22), 0 0 15px rgba(255,65,48,.12); }
  .fx-chain-node.disabled { opacity: .4; }
  .fx-chain-node small { margin-left: auto; color: #8b9097; font-size: calc(var(--u) * 6.5); letter-spacing: .06em; }
  .f-out { grid-column: 1 / -1; }
  .p-fx .card { padding: calc(var(--u) * 8) calc(var(--u) * 9); border-radius: calc(var(--u) * 5); }
  .p-fx .card h2 { font-size: calc(var(--u) * 9); letter-spacing: .16em; margin-bottom: calc(var(--u) * 6); }
  .p-fx .cgrid { align-content: start; align-items: center; gap: calc(var(--u) * 6) calc(var(--u) * 8); }

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
  .ch { background: linear-gradient(#1b1b1d, #0f1011); border: 1px solid #3f4044; border-radius: calc(var(--u) * 6) 1px calc(var(--u) * 6) 1px; }
  .ch.out { background: linear-gradient(#2a1514, #150a0a); border-color: #7a1d18; }
  .chname { font-family: "Bahnschrift", "Arial Narrow", Impact, sans-serif; color: #e8dedb; text-shadow: 0 0 6px rgba(255,59,48,0.5); }
  .frail { background-color: #080303; box-shadow: inset 0 1px 3px #000, 0 0 0 1px rgba(255,59,48,0.14); }
  .ffill { box-shadow: 0 0 8px var(--glow); }
  .fthumb { background: linear-gradient(#85868b 0 36%, #ff3b30 36% 64%, #4f5055 64%); box-shadow: 0 2px 5px #000, 0 0 8px rgba(255,59,48,0.5); border-radius: 2px; }
  .eq { background: rgba(0,0,0,0.38); border-color: #2d1a19; }
  .eqb { color: #ff6d5e; border-bottom-color: #4a1d1a; }

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
  .s-osc .cgrid, .s-lfo .cgrid, .s-ss .cgrid, .m-osc .cgrid, .s2-osc .cgrid, .w-osc .cgrid, .w-warp .cgrid, .x-f1 .cgrid, .x-f2 .cgrid, .x-feg .cgrid, .p-fx .cgrid { grid-template-columns: repeat(var(--kc), minmax(0, 1fr)); }
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
  .n154, .n193, .n210, .n224, .n236, .memgrid, .smem, .wmem { display: none !important; }
</style>
<div class="shell">
  <div class="top">
    <span class="logo">NJOHRR</span><span class="model">SYNTH</span><span class="version">V1.0.0</span>
    <div class="tabs"><button type="button" class="tab on" data-page="sound">SOUND</button><button type="button" class="tab" data-page="flt">FILTER</button><button type="button" class="tab" data-page="smp">SAMPLER</button><button type="button" class="tab" data-page="s2">SAMPLER 2</button><button type="button" class="tab" data-page="wt1">WT 1</button><button type="button" class="tab" data-page="wt2">WT 2</button><button type="button" class="tab" data-page="wt3">WT 3</button><button type="button" class="tab" data-page="lfo">LFO</button><button type="button" class="tab" data-page="env">ENV</button><button type="button" class="tab" data-page="mod">MOD</button><button type="button" class="tab" data-page="mix">MIXER</button><button type="button" class="tab" data-page="fx">FX</button></div>
    <div class="vu"><div class="vu-fill"></div></div>
    <div class="lcd"><span class="lcd-mode">SYNTH</span><span class="lcd-name">--</span><span class="lcd-val">--</span></div><span class="led"></span>
  </div>
  <div class="hz"></div>
  ${MGR_HTML}
  <div class="stage">
    <div class="page p-synth">${synth}</div>
    <div class="page p-flt">${fltPage}</div>
    <div class="page p-smp">${smpPage}</div>
    <div class="page p-s2">${s2Page}</div>
    ${wtPages}
    <div class="page p-lfo">${lfoPage}</div>
    <div class="page p-env">${envPage}</div>
    <div class="page p-mod">${modPage}</div>
    <div class="page p-mix">${mixPage}</div>
    <div class="page p-fx">${fxPage}</div>
  </div>
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
const PRESET_SKIP = new Set(["param146", "param147", "param154", "param193"].concat(WT_ENG.map(c => "param" + c.mem)));
const SLOT_DEFS = [
    { key: "smp", label: "SAMPLER 1",  kind: "sample" },
    { key: "s2",  label: "SAMPLER 2",  kind: "sample" },
    { key: "wt0", label: "WAVETABLE 1", kind: "wavetable" },
    { key: "wt1", label: "WAVETABLE 2", kind: "wavetable" },
    { key: "wt2", label: "WAVETABLE 3", kind: "wavetable" }
];
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
        this._slotLib = { smp: null, s2: null, wt0: null, wt1: null, wt2: null };
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
        const rec = { name, saved: Date.now(), params: this.collectParams(), refs: this.collectRefs() };
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
            const params = Object.assign({}, rec.params || {});
            const hasRackParams = Array.from({ length: FX_SLOT_COUNT * 9 }, (_, i) =>
                Object.prototype.hasOwnProperty.call(params, String(600 + i))).some(Boolean);
            if (!hasRackParams) {
                const get = (id, fallback) => params[String(id)] !== undefined && Number.isFinite(Number(params[String(id)]))
                    ? Number(params[String(id)]) : fallback;
                const norm = (v, min, max) => Math.max(0, Math.min(1, (v - min) / (max - min)));
                const setSlot = (slot, type, enabled, macros) => {
                    const b = FX_SLOT_BASE(slot);
                    [type, enabled, FX_SLOT_DEFAULT_ORDER[slot], ...macros].forEach((v, i) => { params[String(b + i)] = v; });
                };
                setSlot(0, 2, get(541, 1), [norm(get(30, 375), 10, 1000), norm(get(31, 0.35), 0, 0.95),
                    get(183, 1), get(32, 0), get(184, 1), norm(get(60, 18000), 500, 18000)]);
                setSlot(1, 1, get(542, 1), [get(28, 0.1), 1, norm(get(536, 0), 0, 5), 0, 0.5, 0]);
                setSlot(2, 3, get(543, 1), [get(164, 0), norm(get(165, 0.8), 0.05, 5), get(166, 0.5),
                    norm(get(177, 0), 0, 0.9), norm(get(538, 0), 0, 2), 0]);
                setSlot(3, 4, get(544, 1), [get(185, 0), norm(get(186, 0.3), 0.05, 5), get(187, 0.6),
                    norm(get(188, 0.5), 0, 0.95), 0, 0]);
                setSlot(4, 5, get(545, 1), [get(167, 0), norm(get(168, 0.4), 0.05, 8), get(169, 0.5),
                    norm(get(178, 0.5), 0, 0.9), norm(get(539, 1), 0, 3), 0]);
                setSlot(5, 6, get(546, 1), [get(170, 0), get(171, 0.5), get(172, 0.5),
                    norm(get(179, 0), 0, 100), get(180, 1), norm(get(540, 0), 0, 3)]);
                setSlot(6, 7, get(547, 1), [get(173, 0), norm(get(174, 5), 0.1, 20),
                    norm(get(181, 0), 0, 4), get(182, 0), 0, 1]);
                setSlot(7, 8, get(542, 1), [get(191, 1), norm(get(62, 1), 1, 32), norm(get(61, 16), 4, 16), 0, 0, 0]);
                setSlot(8, 0, 0, [0, 0, 0, 0, 0, 0]);
                setSlot(9, 0, 0, [0, 0, 0, 0, 0, 0]);
            }
            this._controls.forEach((c, id) => {
                if (PRESET_SKIP.has(id)) return;
                const k = id.replace("param", "");
                const v = Object.prototype.hasOwnProperty.call(params, k) ? Number(params[k]) : c.def;
                c.setValue(Number.isFinite(v) ? v : c.def, true);
            });
            this.updateSlots();
            this.updateFxRack();
            this.drawFlt();
            for (let e = 0; e < WT_ENG.length; e++) this.drawWt(e);
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
        if (slot === "smp") await this.loadSynthSample(file, id);
        else if (slot === "s2") await this.loadSampler2(file, id);
        else if (slot.indexOf("wt") === 0) await this.loadWavetable(parseInt(slot.slice(2), 10), file, id);
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
            const inUse = SLOT_DEFS.filter(s => this._slotLib[s.key] === r.id).map(s => s.label.replace("SAMPLER ", "S").replace("WAVETABLE ", "WT")).join(" ");
            const btns = slots.map(s => '<button type="button" class="pb" data-act="lb-load" data-slot="' + s.key + '">' + (tgt ? "LOAD" : s.label.replace("SAMPLER ", "SMP ").replace("WAVETABLE ", "WT ")) + '</button>').join("");
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
