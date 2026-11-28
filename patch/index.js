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

const UNI_STYLES = ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"];
const WARP_MODES = ["Off", "Bend +", "Bend \u2212", "Sync", "PWM", "Mirror", "Flip", "Quantize", "Fold", "Smear", "Ripple", "Stairs", "Fold Phase", "Clip", "Rectify", "Wrap", "Asym", "Drive", "Pinch", "Spread", "Slice", "Twin", "Cheby 3", "Cheby 5", "Deadzone", "Expand", "Compress"];

const FILTER_TYPES = ["LP24", "LP12", "HP12", "BP12", "LP6", "LP18", "HP6", "HP18", "HP24", "BP24", "Notch12", "Notch24",
    "Peak", "LowShelf", "HighShelf", "Allpass", "Ladder", "Diode", "Acid", "Dirty LP", "Comb+", "Comb-", "Phaser", "Vowel",
    "MG Low 6", "MG Low 12", "MG Low 18", "MG Low 24", "Flange+", "Flange-"];
const FILTER_GROUPS = [[0, "Basic"], [4, "6 / 18 dB"], [8, "24 dB / Notch"], [12, "Peak / Shelf / Allpass"], [16, "Ladder / Dirty"], [20, "Comb / Phaser / Vowel"], [24, "MG Low"], [28, "Flange"]];
const TBL_FL = 512, TBL_MAX_FR = 64;   // Wavefilter / Wavedistortion tables
const FX_FILTER_TYPES = FILTER_TYPES.concat(["Korg35 LP", "Korg35 HP", "Scream", "Polivoks LP", "Polivoks BP", "Polivoks HP", "OTA LP24 (Jupiter)", "CEM LP24 (Prophet)", "SSM LP24", "SEM LP", "SEM BP", "SEM Notch", "SEM HP", "Diode LP (303)", "Steiner LP", "Steiner HP"]);   // FX-FILTERS   // the Filter effect has three more types than the oscillator filter
const FX_FILTER_GROUPS = FILTER_GROUPS.concat([[30, "Korg / Scream"], [33, "Polivoks"], [36, "OTA / CEM / SSM"], [39, "Oberheim SEM"], [43, "Diode / Steiner-Parker"]]);
const OSC_FILTER_TYPES = FILTER_TYPES.concat(["Wavefilter"]);
const OSC_FILTER_GROUPS = FILTER_GROUPS.concat([[30, "Table"]]);
// LFO sync divisions, in the order of the DSP table
const SEQ_SHAPES = ["Flat", "Ramp down", "Ramp up", "Triangle", "Half sine", "Gate 50%", "Gate 25%", "Decay"];   // MOD-SEQ2
const SYNC_DIVS = ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"];

const LFO_STEPS = ["Off", "Off"].concat(Array.from({ length: 31 }, (_, k) => String(k + 2)));
const LFO_OCT = ["-4 oct", "-3 oct", "-2 oct", "-1 oct", "0", "+1 oct", "+2 oct", "+3 oct", "+4 oct"];
const LFO_SEMI = Array.from({ length: 25 }, (_, k) => (k - 12 > 0 ? "+" : "") + (k - 12) + " st");
const MOD_WAVES = ["Sin", "Tri", "Sqr", "S&H", "Up", "Dn", "Drawn", "Table"];
const MOD_SRC = ["Off"].concat(
    Array.from({ length: 10 }, (_, i) => "LFO " + (i + 1)),
    Array.from({ length: 10 }, (_, i) => "Env " + (i + 1)),
    ["Velocity", "Key", "Random 1"],
    Array.from({ length: 10 }, (_, i) => "Freq " + (i + 1)),
    Array.from({ length: 10 }, (_, i) => "Seq " + (i + 1)),   // MOD-SEQ
    Array.from({ length: 9 }, (_, i) => "Random " + (i + 2))   // RND-DSP
);
// ---- generated by tools/osc/gen_ui_consts.py from tools/osc/layout.py: do not edit by hand ----
/*AUDIODEC-BEGIN*/
// Native audio decoders for the sampler / wavetable loader: no dependency on what the plugin's web view can decode.
// decodeNative(arrayBuffer, maxFrames) -> { ch: [Float32Array, ...], rate, format } or null when the container is not recognised.
// Containers: WAV (PCM 8-32, float, A-law, mu-law, IMA / MS ADPCM, extensible, RF64), Wave64, AIFF / AIFF-C (PCM, float, sowt, ulaw, alaw),
// Sun / NeXT .au, Core Audio .caf (lpcm, ulaw, alaw), FLAC. Anything else (mp3, ogg, m4a ...) is left to the web view's decoder.
const AudioDecode = (() => {
    const fcc = (u8, o) => String.fromCharCode(u8[o], u8[o + 1], u8[o + 2], u8[o + 3]);
    const ALAW = new Float32Array(256), ULAW = new Float32Array(256);
    for (let i = 0; i < 256; i++) {
        let a = i ^ 0x55, s = a & 0x80 ? 1 : -1, e = (a & 0x70) >> 4, m = a & 0x0f;
        let v = e === 0 ? (m << 4) + 8 : ((m << 4) + 0x108) << (e - 1);
        ALAW[i] = s * v / 32768;
        let u = ~i & 0xff; s = u & 0x80 ? -1 : 1; e = (u & 0x70) >> 4; m = u & 0x0f;
        v = (((m << 3) + 0x84) << e) - 0x84;
        ULAW[i] = s * v / 32768;
    }
    const limit = (frames, maxFrames) => (maxFrames > 0 ? Math.min(frames, maxFrames) : frames);

    // interleaved PCM / float -> channel arrays. kind: "int" | "uint8" | "float" | "alaw" | "ulaw"
    function pcm(dv, off, bytes, nch, bps, kind, le, maxFrames) {
        const bw = kind === "alaw" || kind === "ulaw" ? 1 : bps >> 3;
        const frames = limit(Math.floor(bytes / (bw * nch)), maxFrames);
        const ch = [];
        for (let c = 0; c < nch; c++) ch.push(new Float32Array(frames));
        let p = off;
        for (let i = 0; i < frames; i++) for (let c = 0; c < nch; c++, p += bw) {
            let v;
            if (kind === "alaw") v = ALAW[dv.getUint8(p)];
            else if (kind === "ulaw") v = ULAW[dv.getUint8(p)];
            else if (kind === "uint8") v = (dv.getUint8(p) - 128) / 128;
            else if (kind === "float") v = bw === 4 ? dv.getFloat32(p, le) : dv.getFloat64(p, le);
            else if (bw === 1) v = dv.getInt8(p) / 128;
            else if (bw === 2) v = dv.getInt16(p, le) / 32768;
            else if (bw === 3) { const x = le ? dv.getUint8(p) | (dv.getUint8(p + 1) << 8) | (dv.getUint8(p + 2) << 16) : (dv.getUint8(p) << 16) | (dv.getUint8(p + 1) << 8) | dv.getUint8(p + 2); v = ((x << 8) >> 8) / 8388608; }
            else v = dv.getInt32(p, le) / 2147483648;
            ch[c][i] = v;
        }
        return ch;
    }

    // ---- ADPCM (inside WAV) ----
    const IMA_STEP = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767];
    const IMA_IDX = [-1, -1, -1, -1, 2, 4, 6, 8];
    function imaAdpcm(dv, off, bytes, nch, blockAlign, spb, maxFrames) {
        const out = []; for (let c = 0; c < nch; c++) out.push([]);
        const blocks = Math.floor(bytes / blockAlign);
        for (let b = 0; b < blocks; b++) {
            const bo = off + b * blockAlign;
            const pred = [], idx = [];
            for (let c = 0; c < nch; c++) { pred.push(dv.getInt16(bo + 4 * c, true)); idx.push(Math.min(88, dv.getUint8(bo + 4 * c + 2))); out[c].push(pred[c] / 32768); }
            const dec = (c, nib) => {
                const step = IMA_STEP[idx[c]];
                const diff = ((2 * (nib & 7) + 1) * step) >> 3;
                pred[c] = Math.max(-32768, Math.min(32767, pred[c] + (nib & 8 ? -diff : diff)));
                idx[c] = Math.max(0, Math.min(88, idx[c] + IMA_IDX[nib & 7]));
                out[c].push(pred[c] / 32768);
            };
            let p = bo + 4 * nch;
            const end = bo + blockAlign;
            while (p + 4 * nch <= end) {
                // each channel gets 4 bytes (8 samples) in turn
                for (let c = 0; c < nch; c++) for (let k = 0; k < 4; k++) { const v = dv.getUint8(p + c * 4 + k); dec(c, v & 15); dec(c, v >> 4); }
                p += 4 * nch;
            }
            if (maxFrames > 0 && out[0].length >= maxFrames) break;
        }
        return out.map(a => Float32Array.from(a.length > limit(a.length, maxFrames) ? a.slice(0, limit(a.length, maxFrames)) : a));
    }
    const MS_ADAPT = [230, 230, 230, 230, 307, 409, 512, 614, 768, 614, 512, 409, 307, 230, 230, 230];
    function msAdpcm(dv, off, bytes, nch, blockAlign, coefs, maxFrames) {
        const out = []; for (let c = 0; c < nch; c++) out.push([]);
        const blocks = Math.floor(bytes / blockAlign);
        for (let b = 0; b < blocks; b++) {
            let p = off + b * blockAlign;
            const end = p + blockAlign;
            const pi = [], delta = [], s1 = [], s2 = [];
            for (let c = 0; c < nch; c++) { pi.push(Math.min(coefs.length - 1, dv.getUint8(p++))); }
            for (let c = 0; c < nch; c++) { delta.push(dv.getInt16(p, true)); p += 2; }
            for (let c = 0; c < nch; c++) { s1.push(dv.getInt16(p, true)); p += 2; }
            for (let c = 0; c < nch; c++) { s2.push(dv.getInt16(p, true)); p += 2; }
            for (let c = 0; c < nch; c++) out[c].push(s2[c] / 32768);
            for (let c = 0; c < nch; c++) out[c].push(s1[c] / 32768);
            const dec = (c, nib) => {
                const co = coefs[pi[c]];
                let v = ((s1[c] * co[0] + s2[c] * co[1]) >> 8) + (nib >= 8 ? nib - 16 : nib) * delta[c];
                v = Math.max(-32768, Math.min(32767, v));
                s2[c] = s1[c]; s1[c] = v;
                delta[c] = Math.max(16, (MS_ADAPT[nib] * delta[c]) >> 8);
                out[c].push(v / 32768);
            };
            while (p < end) {
                const v = dv.getUint8(p++);
                if (nch === 1) { dec(0, v >> 4); dec(0, v & 15); }
                else { dec(0, v >> 4); dec(1, v & 15); }
            }
            if (maxFrames > 0 && out[0].length >= maxFrames) break;
        }
        return out.map(a => Float32Array.from(maxFrames > 0 && a.length > maxFrames ? a.slice(0, maxFrames) : a));
    }

    // ---- WAV / RF64 / Wave64 ----
    function wav(buf, maxFrames) {
        const u8 = new Uint8Array(buf), dv = new DataView(buf), id = fcc(u8, 0);
        const w64 = id === "riff" && u8.length > 40 && fcc(u8, 24) === "wave";
        if (!(id === "RIFF" || id === "RF64" || id === "BW64") && !w64) return null;
        if (!w64 && fcc(u8, 8) !== "WAVE") return null;
        let fmt = null, dataOff = -1, dataLen = 0, ds64 = 0;
        if (w64) {
            let p = 40;
            while (p + 24 <= u8.length) {
                const cid = fcc(u8, p), sz = Number(dv.getBigUint64(p + 16, true)) - 24;
                const body = p + 24;
                if (cid === "fmt ") fmt = body; else if (cid === "data") { dataOff = body; dataLen = Math.min(sz, u8.length - body); break; }
                p = body + sz + ((8 - (sz & 7)) & 7);
            }
        } else {
            let p = 12;
            while (p + 8 <= u8.length) {
                const cid = fcc(u8, p); let sz = dv.getUint32(p + 4, true);
                const body = p + 8;
                if (cid === "ds64") ds64 = Number(dv.getBigUint64(body + 8, true));
                else if (cid === "fmt ") fmt = body;
                else if (cid === "data") {
                    if (sz === 0xffffffff && ds64) sz = ds64;
                    dataOff = body; dataLen = Math.min(sz, u8.length - body); if (sz === 0xffffffff || sz === 0) dataLen = u8.length - body;
                    break;
                }
                p = body + sz + (sz & 1);
            }
        }
        if (fmt === null || dataOff < 0) return null;
        let tag = dv.getUint16(fmt, true); const nch = dv.getUint16(fmt + 2, true), rate = dv.getUint32(fmt + 4, true);
        const blockAlign = dv.getUint16(fmt + 12, true), bps = dv.getUint16(fmt + 14, true);
        const cb = w64 ? 0 : 0, ext = fmt + 16 <= u8.length - 2 ? dv.getUint16(fmt + 16, true) : 0;
        if (tag === 0xfffe && ext >= 22) tag = dv.getUint16(fmt + 24, true);
        if (!nch || !rate) return null;
        let ch;
        if (tag === 1) ch = pcm(dv, dataOff, dataLen, nch, bps === 8 ? 8 : Math.ceil(bps / 8) * 8, bps === 8 ? "uint8" : "int", true, maxFrames);
        else if (tag === 3) ch = pcm(dv, dataOff, dataLen, nch, bps, "float", true, maxFrames);
        else if (tag === 6) ch = pcm(dv, dataOff, dataLen, nch, 8, "alaw", true, maxFrames);
        else if (tag === 7) ch = pcm(dv, dataOff, dataLen, nch, 8, "ulaw", true, maxFrames);
        else if (tag === 0x11) ch = imaAdpcm(dv, dataOff, dataLen, nch, blockAlign, ext >= 2 ? dv.getUint16(fmt + 18, true) : 0, maxFrames);
        else if (tag === 2) {
            const nc = dv.getUint16(fmt + 20, true), coefs = [];
            for (let i = 0; i < nc; i++) coefs.push([dv.getInt16(fmt + 22 + 4 * i, true), dv.getInt16(fmt + 24 + 4 * i, true)]);
            if (!coefs.length) coefs.push([256, 0], [512, -256], [0, 0], [192, 64], [240, 0], [460, -208], [392, -232]);
            ch = msAdpcm(dv, dataOff, dataLen, nch, blockAlign, coefs, maxFrames);
        } else return null;   // mp3 in wav, etc.: leave to the web view
        return { ch, rate, format: w64 ? "Wave64" : "WAV" };
    }

    // ---- AIFF / AIFF-C ----
    function ext80(dv, o) {
        const se = dv.getUint16(o, false), hi = dv.getUint32(o + 2, false), lo = dv.getUint32(o + 6, false);
        const e = (se & 0x7fff) - 16383;
        return (se & 0x8000 ? -1 : 1) * (hi * Math.pow(2, e - 31) + lo * Math.pow(2, e - 63));
    }
    function aiff(buf, maxFrames) {
        const u8 = new Uint8Array(buf), dv = new DataView(buf);
        if (fcc(u8, 0) !== "FORM") return null;
        const ty = fcc(u8, 8);
        if (ty !== "AIFF" && ty !== "AIFC") return null;
        let nch = 0, frames = 0, bits = 0, rate = 0, comp = "NONE", ssnd = -1, ssndLen = 0;
        let p = 12;
        while (p + 8 <= u8.length) {
            const cid = fcc(u8, p), sz = dv.getUint32(p + 4, false), body = p + 8;
            if (cid === "COMM") {
                nch = dv.getUint16(body, false); frames = dv.getUint32(body + 2, false); bits = dv.getUint16(body + 6, false); rate = ext80(dv, body + 8);
                if (ty === "AIFC" && sz >= 22) comp = fcc(u8, body + 18);
            } else if (cid === "SSND") { const o = dv.getUint32(body, false); ssnd = body + 8 + o; ssndLen = Math.min(sz - 8 - o, u8.length - ssnd); break; }
            p = body + sz + (sz & 1);
        }
        if (ssnd < 0 || !nch || !rate) return null;
        const c = comp.toLowerCase();
        let ch;
        if (c === "none" || c === "twos" || c === "in24" || c === "in32" || c === "42ni") ch = pcm(dv, ssnd, ssndLen, nch, Math.ceil(bits / 8) * 8, "int", false, maxFrames);
        else if (c === "sowt") ch = pcm(dv, ssnd, ssndLen, nch, Math.ceil(bits / 8) * 8, "int", true, maxFrames);
        else if (c === "raw ") ch = pcm(dv, ssnd, ssndLen, nch, 8, "uint8", false, maxFrames);
        else if (c === "fl32") ch = pcm(dv, ssnd, ssndLen, nch, 32, "float", false, maxFrames);
        else if (c === "fl64") ch = pcm(dv, ssnd, ssndLen, nch, 64, "float", false, maxFrames);
        else if (c === "ulaw") ch = pcm(dv, ssnd, ssndLen, nch, 8, "ulaw", false, maxFrames);
        else if (c === "alaw") ch = pcm(dv, ssnd, ssndLen, nch, 8, "alaw", false, maxFrames);
        else return null;
        return { ch, rate, format: ty };
    }

    // ---- Sun / NeXT .au ----
    function au(buf, maxFrames) {
        const u8 = new Uint8Array(buf), dv = new DataView(buf);
        const m = fcc(u8, 0);
        if (m !== ".snd" && m !== "dns.") return null;
        const le = m === "dns.";
        const off = dv.getUint32(4, le), enc = dv.getUint32(12, le), rate = dv.getUint32(16, le), nch = dv.getUint32(20, le);
        let size = dv.getUint32(8, le); if (size === 0xffffffff || off + size > u8.length) size = u8.length - off;
        let ch;
        if (enc === 1) ch = pcm(dv, off, size, nch, 8, "ulaw", le, maxFrames);
        else if (enc === 2) ch = pcm(dv, off, size, nch, 8, "int", le, maxFrames);
        else if (enc === 3) ch = pcm(dv, off, size, nch, 16, "int", le, maxFrames);
        else if (enc === 4) ch = pcm(dv, off, size, nch, 24, "int", le, maxFrames);
        else if (enc === 5) ch = pcm(dv, off, size, nch, 32, "int", le, maxFrames);
        else if (enc === 6) ch = pcm(dv, off, size, nch, 32, "float", le, maxFrames);
        else if (enc === 7) ch = pcm(dv, off, size, nch, 64, "float", le, maxFrames);
        else if (enc === 27) ch = pcm(dv, off, size, nch, 8, "alaw", le, maxFrames);
        else return null;
        return { ch, rate, format: "AU" };
    }

    // ---- Core Audio Format ----
    function caf(buf, maxFrames) {
        const u8 = new Uint8Array(buf), dv = new DataView(buf);
        if (fcc(u8, 0) !== "caff") return null;
        let p = 8, desc = null, dOff = -1, dLen = 0;
        while (p + 12 <= u8.length) {
            const cid = fcc(u8, p); let sz = Number(dv.getBigInt64(p + 4, false)); const body = p + 12;
            if (cid === "desc") desc = { rate: dv.getFloat64(body, false), fid: fcc(u8, body + 8), flags: dv.getUint32(body + 12, false), nch: dv.getUint32(body + 24, false), bits: dv.getUint32(body + 28, false) };
            else if (cid === "data") { if (sz < 0 || body + sz > u8.length) sz = u8.length - body; dOff = body + 4; dLen = sz - 4; break; }
            p = body + sz;
        }
        if (!desc || dOff < 0 || !desc.nch) return null;
        const le = !!(desc.flags & 2); let ch;
        if (desc.fid === "lpcm") ch = desc.flags & 1 ? pcm(dv, dOff, dLen, desc.nch, desc.bits, "float", le, maxFrames) : pcm(dv, dOff, dLen, desc.nch, Math.ceil(desc.bits / 8) * 8, "int", le, maxFrames);
        else if (desc.fid === "ulaw") ch = pcm(dv, dOff, dLen, desc.nch, 8, "ulaw", false, maxFrames);
        else if (desc.fid === "alaw") ch = pcm(dv, dOff, dLen, desc.nch, 8, "alaw", false, maxFrames);
        else return null;
        return { ch, rate: desc.rate, format: "CAF" };
    }

    // ---- FLAC ----
    function flac(buf, maxFrames) {
        const u8 = new Uint8Array(buf);
        let p = 0;
        if (u8[0] === 0x49 && u8[1] === 0x44 && u8[2] === 0x33) p = 10 + ((u8[6] << 21) | (u8[7] << 14) | (u8[8] << 7) | u8[9]);   // ID3v2
        if (fcc(u8, p) !== "fLaC") return null;
        p += 4;
        let rate = 0, nch = 0, bps = 0, total = 0, last = false;
        while (!last && p + 4 <= u8.length) {
            const h = u8[p]; last = !!(h & 0x80); const type = h & 0x7f, len = (u8[p + 1] << 16) | (u8[p + 2] << 8) | u8[p + 3];
            if (type === 0) {
                rate = (u8[p + 14] << 12) | (u8[p + 15] << 4) | (u8[p + 16] >> 4);
                nch = ((u8[p + 16] >> 1) & 7) + 1; bps = (((u8[p + 16] & 1) << 4) | (u8[p + 17] >> 4)) + 1;
                total = (u8[p + 17] & 15) * 4294967296 + ((u8[p + 18] << 24) >>> 0) + ((u8[p + 19] << 16) | (u8[p + 20] << 8) | u8[p + 21]);
            }
            p += 4 + len;
        }
        if (!rate) return null;
        // bit reader
        let pos = p * 8;
        const bitsLeft = () => u8.length * 8 - pos;
        const rd = n => { let v = 0; while (n > 0) { const byte = u8[pos >> 3] | 0, avail = 8 - (pos & 7), take = Math.min(avail, n); v = v * Math.pow(2, take) + ((byte >> (avail - take)) & ((1 << take) - 1)); pos += take; n -= take; } return v; };
        const rds = n => { const v = rd(n); return n === 0 ? 0 : (v >= Math.pow(2, n - 1) ? v - Math.pow(2, n) : v); };
        const unary = () => { let n = 0; while (rd(1) === 0 && bitsLeft() > 0) n++; return n; };
        const out = []; for (let c = 0; c < nch; c++) out.push([]);
        const cap = maxFrames > 0 ? maxFrames : Infinity;
        let done = 0;
        const FIXED = [[], [1], [2, -1], [3, -3, 1], [4, -6, 4, -1]];
        const BS = [0, 192, 576, 1152, 2304, 4608, -1, -2, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768];
        const SR = [0, 88200, 176400, 192000, 8000, 16000, 22050, 24000, 32000, 44100, 48000, 96000, -1, -2, -3, 0];
        const BPS = [0, 8, 12, 0, 16, 20, 24, 32];
        try {
            while (done < cap && bitsLeft() > 64) {
                pos = (pos + 7) & ~7;
                if (rd(14) !== 0x3ffe) { pos -= 14; pos += 8; continue; }   // resync byte-wise
                rd(1); const varBs = rd(1);
                const bsc = rd(4), src = rd(4), cha = rd(4), bpc = rd(3); rd(1);
                let b0 = rd(8); let extra = 0; if (b0 >= 0xc0) { extra = b0 >= 0xfe ? 6 : b0 >= 0xfc ? 5 : b0 >= 0xf8 ? 4 : b0 >= 0xf0 ? 3 : b0 >= 0xe0 ? 2 : 1; } for (let i = 0; i < extra; i++) rd(8);
                let bs = BS[bsc]; if (bs === -1) bs = rd(8) + 1; else if (bs === -2) bs = rd(16) + 1;
                if (SR[src] === -1) rd(8); else if (SR[src] === -2) rd(16); else if (SR[src] === -3) rd(16);
                rd(8);   // header crc
                const fb = BPS[bpc] || bps;
                const nc = cha < 8 ? cha + 1 : 2;
                const sub = [];
                for (let c = 0; c < nc; c++) {
                    let sb = fb; if (cha === 8 && c === 1) sb++; else if (cha === 9 && c === 0) sb++; else if (cha === 10 && c === 1) sb++;
                    rd(1); const type = rd(6); let wasted = 0;
                    if (rd(1)) { wasted = unary() + 1; }
                    sb -= wasted;
                    const s = new Array(bs);
                    if (type === 0) { const v = rds(sb); for (let i = 0; i < bs; i++) s[i] = v; }
                    else if (type === 1) { for (let i = 0; i < bs; i++) s[i] = rds(sb); }
                    else {
                        let order, coefs, shift = 0;
                        if (type >= 8 && type <= 12) { order = type - 8; coefs = FIXED[order]; }
                        else if (type >= 32) {
                            order = type - 31;
                        } else throw new Error("bad subframe");
                        for (let i = 0; i < order; i++) s[i] = rds(sb);
                        if (type >= 32) {
                            const prec = rd(4) + 1; shift = rds(5); coefs = [];
                            for (let i = 0; i < order; i++) coefs.push(rds(prec));
                        }
                        // residual
                        const method = rd(2), pbits = method === 0 ? 4 : 5, pord = rd(pbits);
                        const parts = 1 << pord;
                        let i = order;
                        for (let pt = 0; pt < parts; pt++) {
                            const rice = rd(pbits);
                            const n = pord === 0 ? bs - order : (pt === 0 ? (bs >> pord) - order : (bs >> pord));
                            const esc = rice === (method === 0 ? 15 : 31);
                            const eb = esc ? rd(5) : 0;
                            for (let k = 0; k < n; k++, i++) {
                                let r;
                                if (esc) r = eb ? rds(eb) : 0;
                                else { const q = unary(); const low = rice ? rd(rice) : 0; const u = q * Math.pow(2, rice) + low; r = (u % 2) ? -(u + 1) / 2 : u / 2; }
                                let pred = 0;
                                if (type >= 32) { for (let j = 0; j < order; j++) pred += coefs[j] * s[i - 1 - j]; pred = Math.floor(pred / Math.pow(2, shift)); }
                                else for (let j = 0; j < order; j++) pred += coefs[j] * s[i - 1 - j];
                                s[i] = pred + r;
                            }
                        }
                    }
                    if (wasted) for (let i = 0; i < bs; i++) s[i] *= Math.pow(2, wasted);
                    sub.push(s);
                }
                pos = (pos + 7) & ~7; rd(16);   // frame crc
                if (cha === 8) for (let i = 0; i < bs; i++) sub[1][i] = sub[0][i] - sub[1][i];
                else if (cha === 9) for (let i = 0; i < bs; i++) sub[0][i] = sub[0][i] + sub[1][i];
                else if (cha === 10) for (let i = 0; i < bs; i++) { const m = sub[0][i], sd = sub[1][i]; const mm = m * 2 + (sd & 1); sub[0][i] = (mm + sd) / 2; sub[1][i] = (mm - sd) / 2; }
                const sc = Math.pow(2, fb - 1);
                for (let c = 0; c < Math.min(nc, nch); c++) { const dst = out[c]; for (let i = 0; i < bs; i++) dst.push(sub[c][i] / sc); }
                done += bs;
            }
        } catch (e) { /* truncated / damaged stream: keep what was decoded */ }
        if (!out[0].length) return null;
        return { ch: out.map(a => Float32Array.from(a.length > cap ? a.slice(0, cap) : a)), rate, format: "FLAC" };
    }

    // ---- raw PCM fallback (16 bit little endian, mono) for headerless dumps ----
    function raw(buf, maxFrames) {
        const dv = new DataView(buf), n = limit(Math.floor(buf.byteLength / 2), maxFrames), a = new Float32Array(n);
        for (let i = 0; i < n; i++) a[i] = dv.getInt16(i * 2, true) / 32768;
        return { ch: [a], rate: 44100, format: "RAW" };
    }

    function decodeNative(buf, maxFrames) {
        const tries = [wav, aiff, au, caf, flac];
        for (const f of tries) { let r = null; try { r = f(buf, maxFrames); } catch (_) { r = null; } if (r && r.ch && r.ch.length && r.ch[0].length) return r; }
        return null;
    }
    return { decodeNative, raw, wav, aiff, au, caf, flac };
})();
/*AUDIODEC-END*/
const OSC_N = 6, OSC_BASE = 1000, OSC_STRIDE = 64, FM_BASE = 1400, PM_BASE = 1440, PD_BASE = 1480, RM_BASE = 1520, AM_BASE = 1560, TZ_BASE = 2900, MX_BASE = 5300;
const OSC_K = {"type": 0, "level": 1, "pan": 2, "out": 3, "oct": 4, "semi": 5, "fine": 6, "track": 7, "phase": 8, "rphase": 9, "wpos": 10, "wsize": 11, "root": 12, "uvox": 13, "udet": 14, "ublend": 15, "uwid": 16, "ustyle": 17, "udrift": 28, "uphase": 29, "w1m": 18, "w1a": 19, "w2m": 20, "w2a": 21, "sstart": 22, "sloop": 23, "tterr": 24, "tscale": 25, "twarp": 26, "tfold": 27, "fon": 30, "ftype": 31, "fcut": 32, "fres": 33, "fdrv": 34, "fkey": 35, "feg": 36, "fvel": 37, "fatk": 38, "fdec": 39, "fsus": 40, "frel": 41, "dtype": 42, "ddrv": 43, "dmix": 44, "freq": 48, "wfpos": 46, "wdpos": 47, "wfmix": 49, "wfrange": 50, "wfwarp": 51, "wfcont": 52, "wftilt": 53, "wfspr": 54, "wflaw": 55, "dpos": 45, "rson": 56, "rsmod": 57, "rsdec": 58, "rsmat": 59, "rshit": 60, "rsinh": 61, "rstune": 62, "rsmix": 63};
const oscId = (o, k) => OSC_BASE + OSC_STRIDE * o + (typeof k === "string" ? OSC_K[k] : k);
const fmId = (s, d) => FM_BASE + 6 * s + d;
const pmId = (s, d) => PM_BASE + 6 * s + d;
const pdId = (s, d) => PD_BASE + 6 * s + d;
const rmId = (s, d) => RM_BASE + 6 * s + d;
const amId = (s, d) => AM_BASE + 6 * s + d;
const tzId = (s, d) => TZ_BASE + 6 * s + d;   // through-zero FM matrix
const OSC_SRC_TYPES = ["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080", "Granular", "Additive", "Modal Drum", "Spectral", "SoundFont", "Bagpipe"];
const PHY_BASE = 1700, PHY_STRIDE = 32;
const PHY_K = {"phmix": 0, "phhard": 1, "phntim": 2, "phmodA": 3, "phdecA": 4, "phmatA": 5, "phhitA": 6, "phinhA": 7, "phmodB": 8, "phdecB": 9, "phmatB": 10, "phhitB": 11, "phinhB": 12, "phtunB": 13, "phbal": 14, "phser": 15, "jsaw": 16, "jpulse": 17, "jwidth": 18, "jpwm": 19, "jpwmr": 20, "jsub": 21, "jnoise": 22, "jrange": 23, "jdrift": 24, "jcurve": 25, "jptype": 26, "jstype": 27, "jbtype": 28, "jpwms": 29, "jvib": 30};
const phyId = (o, key) => PHY_BASE + PHY_STRIDE * o + PHY_K[key];
const KICK_BASE = 1900, KICK_STRIDE = 16;
const KICK_K = {"kmode": 0, "ksweep": 1, "kstime": 2, "kscurve": 3, "kdec": 4, "ktone": 5, "kclick": 6, "kcltone": 7, "knoise": 8, "kdrive": 9, "kdtype": 10, "ksub": 11, "kpunch": 12, "ktune": 13, "kcldec": 14, "kchar": 15};
const kickId = (o, key) => KICK_BASE + KICK_STRIDE * o + KICK_K[key];
const TER_BASE = 2100, TER_STRIDE = 16;
const TER_K = {"tcx": 0, "tcy": 1, "trx": 2, "try": 3, "trot": 4, "tratio": 5, "tphase": 6, "tshape": 7, "tmrate": 8, "tmdep": 9, "tterr2": 10, "tmorph": 11, "tsmooth": 12, "tdrive": 13, "tbits": 14, "tvel": 15};
const terId = (o, key) => TER_BASE + TER_STRIDE * o + TER_K[key];
const WG_BASE = 2200, WG_STRIDE = 16;
const WG_K = {"wmodel": 0, "wdecay": 1, "wtone": 2, "wexc": 3, "wpos": 4, "wnoise": 5, "wnl": 6, "wstretch": 7, "watk": 8, "wsnare": 9, "wbody": 10, "wbodyf": 11, "wvel": 12, "wdrive": 13, "wglide": 14, "wktrack": 15};
const wgId = (o, key) => WG_BASE + WG_STRIDE * o + WG_K[key];
const JP_BASE = 2300, JP_STRIDE = 16;
const JP_K = {"jpwave": 0, "jppw": 1, "jppwm": 2, "jppwr": 3, "jpdet": 4, "jpmix": 5, "jpwid": 6, "jpfb": 7, "jpfbc": 8, "jptmd": 9, "jptmr": 10, "jpstilt": 11, "jpspk": 12, "jpnz": 13, "jpdrv": 14, "jpsub": 15};
const jpId = (o, key) => JP_BASE + JP_STRIDE * o + JP_K[key];
const GR_BASE = 2400, GR_STRIDE = 16;
const GR_K = {"gpos": 0, "gsize": 1, "gdens": 2, "gspray": 3, "gpitch": 4, "gpan": 5, "gshape": 6, "grev": 7, "gscan": 8, "gjit": 9, "gdrive": 10, "gvel": 11};
const grId = (o, key) => GR_BASE + GR_STRIDE * o + GR_K[key];
const AD_BASE = 2500, AD_STRIDE = 16;
const AD_K = {"ashape": 0, "ashapeb": 1, "amorph": 2, "acount": 3, "atilt": 4, "aodd": 5, "ainh": 6, "aform": 7, "aformg": 8, "ashim": 9, "ashimr": 10, "adec": 11, "adrive": 12, "awid": 13, "avel": 14};
const adId = (o, key) => AD_BASE + AD_STRIDE * o + AD_K[key];
const SP_BASE = 2700, SP_STRIDE = 16;
const SP_K = {"smode": 0, "spos": 1, "spos2": 2, "smorph": 3, "sscan": 4, "sblur": 5, "sshift": 6, "stilt": 7, "sharm": 8, "sodd": 9, "scomb": 10, "scont": 11, "sjit": 12, "sspr": 13, "swid": 14, "svel": 15};
const spId = (o, key) => SP_BASE + SP_STRIDE * o + SP_K[key];
const BP_BASE = 3500, BP_STRIDE = 16;
const BP_K = {"bpscale": 0, "bpreed": 1, "bpdouble": 2, "bpconic": 3, "bpcoup": 4, "bpbore": 5, "bpfluct": 6, "bpair": 7, "bpcolmix": 8, "bpcolf": 9, "bpdrone": 10, "bpchord": 11, "bpkey": 12, "bpstrike": 13, "bpvib": 14, "bpblow": 15};
const bpId = (o, key) => BP_BASE + BP_STRIDE * o + BP_K[key];
const SM_BASE = 12300, SM_STRIDE = 16;
const SM_K = {"send": 0, "slps": 1, "slpe": 2, "spp": 3, "sxf": 4, "srev": 5, "sint": 6, "sgain": 7, "svst": 8, "sslice": 9, "swid": 10};
const smId = (o, key) => SM_BASE + SM_STRIDE * o + SM_K[key];
const WT_BASE = 12500, WT_STRIDE = 16;
const WT_K = {"w3m": 0, "w3a": 1, "wmorph": 2, "wtone": 3};
const wtId = (o, key) => WT_BASE + WT_STRIDE * o + WT_K[key];
const SF_BASE = 2800, SF_STRIDE = 16;
const SF_K = {"sfgain": 0, "sfvel": 1, "sfatk": 2, "sfdec": 3, "sfsus": 4, "sfrel": 5, "sfloop": 6, "sfpan": 7, "sfstart": 8, "sfdrive": 9};
const sfId = (o, key) => SF_BASE + SF_STRIDE * o + SF_K[key];
const DK_BASE = 2600, DK_STRIDE = 16;
const DK_K = {"ddecay": 0, "dtone": 1, "dhit": 2, "dstick": 3, "dedge": 4, "dres": 5, "drtune": 6, "dshell": 7, "ddepth": 8, "dsnare": 9, "dsten": 10, "dsym": 11, "dtens": 12, "dvel": 13, "ddrive": 14, "dsize": 15};
const dkId = (o, key) => DK_BASE + DK_STRIDE * o + DK_K[key];
const AD_SHAPES = ["Saw", "Square", "Triangle", "Organ", "Bell", "Vowel", "Brass", "Hollow"];
const JP_WAVES = ["Saw", "Square", "Triangle", "Sine", "Noise", "Spectrum", "Super Saw", "Feedback Osc", "Tri Mod"];
const JP_LABELS = [["", "", "", "", "", "", "", "", "", "", "", "", "Noise", "Drive", "Sub"], ["Pulse Width", "PWM Depth", "PWM Rate", "", "", "", "", "", "", "", "", "", "Noise", "Drive", "Sub"], ["", "", "", "", "", "", "", "", "", "", "", "", "Noise", "Drive", "Sub"], ["", "", "", "", "", "", "", "", "", "", "", "", "Noise", "Drive", "Sub"], ["", "", "", "", "", "", "", "", "", "", "", "", "", "Drive", ""], ["", "", "", "", "", "", "", "", "", "", "Tilt", "Peak", "Noise", "Drive", "Sub"], ["", "", "", "Detune", "Mix", "Width", "", "", "", "", "", "", "Noise", "Drive", "Sub"], ["", "", "", "", "", "", "Feedback", "Color", "", "", "", "", "Noise", "Drive", "Sub"], ["", "", "", "", "", "", "", "", "Mod Depth", "Mod Ratio", "", "", "Noise", "Drive", "Sub"]];
const WG_MODELS = ["Karplus-Strong", "Bowed String", "Clarinet", "Banded Waveguide", "Drum", "Lute", "Psaltery", "Dulcimer", "Rebec", "Hurdy-Gurdy", "Shawm", "Crumhorn", "Bagpipe", "Recorder", "Tabor", "Handbell", "Medieval Harp"];
const WG_LABELS = [["Decay", "Tone", "Hardness", "Pluck Pos", "Pluck Noise", "Saturation", "Stiffness", "", "", "Body", "Body Tune", "Vel > Excite", "Drive", "Tension", "Key Decay"], ["Loss", "Bridge Tone", "Bow Pressure", "Bow Pos", "Bow Noise", "Bow Offset", "", "Bow Attack", "", "Body", "Body Tune", "Vel > Bow", "Drive", "", "Key Decay"], ["Loss", "Bore Tone", "Breath", "Reed Stiff", "Breath Noise", "Reed Offset", "", "Breath Attack", "", "Body", "Body Tune", "Vel > Breath", "Drive", "", "Key Decay"], ["Decay", "Tone", "Hardness", "Strike Pos", "Strike Noise", "", "Mode Ratios", "", "", "Body", "Body Tune", "Vel > Strike", "Drive", "", "Key Decay"], ["Decay", "Tone", "Mallet", "Strike Pos", "Stick Noise", "", "Stiffness", "", "Snare", "Shell", "Shell Tune", "Vel > Strike", "Drive", "Tension", "Key Decay"], ["Decay", "Tone", "Hardness", "Pluck Pos", "Pluck Noise", "Saturation", "Stiffness", "", "", "Body", "Body Tune", "Vel > Excite", "Drive", "Tension", "Key Decay"], ["Decay", "Tone", "Hardness", "Pluck Pos", "Pluck Noise", "Saturation", "Stiffness", "", "", "Body", "Body Tune", "Vel > Excite", "Drive", "Tension", "Key Decay"], ["Decay", "Tone", "Hardness", "Pluck Pos", "Pluck Noise", "Saturation", "Stiffness", "", "", "Body", "Body Tune", "Vel > Excite", "Drive", "Tension", "Key Decay"], ["Loss", "Bridge Tone", "Bow Pressure", "Bow Pos", "Bow Noise", "Bow Offset", "", "Bow Attack", "", "Body", "Body Tune", "Vel > Bow", "Drive", "", "Key Decay"], ["Loss", "Bridge Tone", "Bow Pressure", "Bow Pos", "Bow Noise", "Bow Offset", "", "Bow Attack", "", "Body", "Body Tune", "Vel > Bow", "Drive", "", "Key Decay"], ["Loss", "Bore Tone", "Breath", "Reed Stiff", "Breath Noise", "Reed Offset", "", "Breath Attack", "", "Body", "Body Tune", "Vel > Breath", "Drive", "", "Key Decay"], ["Loss", "Bore Tone", "Breath", "Reed Stiff", "Breath Noise", "Reed Offset", "", "Breath Attack", "", "Body", "Body Tune", "Vel > Breath", "Drive", "", "Key Decay"], ["Loss", "Bore Tone", "Breath", "Reed Stiff", "Breath Noise", "Reed Offset", "", "Breath Attack", "", "Body", "Body Tune", "Vel > Breath", "Drive", "", "Key Decay"], ["Decay", "Bore Tone", "Breath", "", "Air Noise", "Saturation", "", "Breath Attack", "", "Body", "Body Tune", "Vel > Breath", "Drive", "", "Key Decay"], ["Decay", "Tone", "Mallet", "Strike Pos", "Stick Noise", "", "Stiffness", "", "Snare", "Shell", "Shell Tune", "Vel > Strike", "Drive", "Tension", "Key Decay"], ["Decay", "Tone", "Hardness", "Strike Pos", "Strike Noise", "", "Mode Ratios", "", "", "Body", "Body Tune", "Vel > Strike", "Drive", "", "Key Decay"], ["Decay", "Tone", "Hardness", "Pluck Pos", "Pluck Noise", "Saturation", "Stiffness", "", "", "Body", "Body Tune", "Vel > Excite", "Drive", "Tension", "Key Decay"]];
const PHY_MODELS = ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"];
const PHY_RAT = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0], [1.0, 2.7778, 5.4444, 9.0, 13.4444, 18.7778, 25.0, 32.1111, 40.1111, 49.0, 58.7778, 69.4444, 81.0, 93.4444, 106.7778, 121.0], [1.0, 1.5811, 2.0, 2.2361, 2.5495, 2.9155, 3.0, 3.1623, 3.5355, 3.6056, 3.8079, 4.0, 4.1231, 4.3012, 4.4721, 4.5277], [1.0, 1.5934, 2.1356, 2.2955, 2.6531, 2.9173, 3.1555, 3.5002, 3.5985, 3.6475, 4.059, 4.1318, 4.2305, 4.6011, 4.6101, 4.8319], [1.0, 2.1152, 2.8848, 3.974, 4.0, 5.8587, 6.026, 6.5762, 7.1413, 8.461, 9.0, 9.9219, 10.4238, 11.539, 11.6022, 11.8067], [1.0, 1.2967, 1.5678, 1.6477, 1.8266, 1.9587, 2.0777, 2.2501, 2.2993, 2.3237, 2.5295, 2.5659, 2.6152, 2.8005, 2.8051, 2.916], [1, 4, 10, 17.82, 26.62, 37.18, 49.5, 63.58, 79.42, 97.02, 116.38, 137.5, 160.38, 185.02, 211.42, 239.58], [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0], [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0, 19.0, 21.0, 23.0, 25.0, 27.0, 29.0, 31.0]];
const PHY_AEXP = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.35, 1.0, 1.0];

const DIST_TYPES = ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Wavedistortion"];
const OSC_OUTS = ["Main", "Bus 1", "Bus 2"];
const TERRAINS = ["Sine Product", "Ripples", "Saddle", "Chebyshev", "Checker", "Spiral", "Diamond", "Interference", "Lattice", "Bumps", "Fractal", "Twist"];
const MOD_DST = ["Off", "Pitch (all)", "Amp", "Pan", "Drive", "Out Gain", "OSC 1 Pitch", "OSC 1 Level", "OSC 1 Pan", "OSC 1 Position / Terrain Scale", "OSC 1 Warp 1 / Terrain Warp", "OSC 1 Warp 2 / Terrain Fold", "OSC 1 Cutoff", "OSC 1 Reso", "OSC 1 Dist Drive", "OSC 2 Pitch", "OSC 2 Level", "OSC 2 Pan", "OSC 2 Position / Terrain Scale", "OSC 2 Warp 1 / Terrain Warp", "OSC 2 Warp 2 / Terrain Fold", "OSC 2 Cutoff", "OSC 2 Reso", "OSC 2 Dist Drive", "OSC 3 Pitch", "OSC 3 Level", "OSC 3 Pan", "OSC 3 Position / Terrain Scale", "OSC 3 Warp 1 / Terrain Warp", "OSC 3 Warp 2 / Terrain Fold", "OSC 3 Cutoff", "OSC 3 Reso", "OSC 3 Dist Drive", "OSC 4 Pitch", "OSC 4 Level", "OSC 4 Pan", "OSC 4 Position / Terrain Scale", "OSC 4 Warp 1 / Terrain Warp", "OSC 4 Warp 2 / Terrain Fold", "OSC 4 Cutoff", "OSC 4 Reso", "OSC 4 Dist Drive", "OSC 5 Pitch", "OSC 5 Level", "OSC 5 Pan", "OSC 5 Position / Terrain Scale", "OSC 5 Warp 1 / Terrain Warp", "OSC 5 Warp 2 / Terrain Fold", "OSC 5 Cutoff", "OSC 5 Reso", "OSC 5 Dist Drive", "OSC 6 Pitch", "OSC 6 Level", "OSC 6 Pan", "OSC 6 Position / Terrain Scale", "OSC 6 Warp 1 / Terrain Warp", "OSC 6 Warp 2 / Terrain Fold", "OSC 6 Cutoff", "OSC 6 Reso", "OSC 6 Dist Drive", "FM A > A", "FM A > B", "FM A > C", "FM A > D", "FM A > E", "FM A > F", "FM B > A", "FM B > B", "FM B > C", "FM B > D", "FM B > E", "FM B > F", "FM C > A", "FM C > B", "FM C > C", "FM C > D", "FM C > E", "FM C > F", "FM D > A", "FM D > B", "FM D > C", "FM D > D", "FM D > E", "FM D > F", "FM E > A", "FM E > B", "FM E > C", "FM E > D", "FM E > E", "FM E > F", "FM F > A", "FM F > B", "FM F > C", "FM F > D", "FM F > E", "FM F > F", "PM A > A", "PM A > B", "PM A > C", "PM A > D", "PM A > E", "PM A > F", "PM B > A", "PM B > B", "PM B > C", "PM B > D", "PM B > E", "PM B > F", "PM C > A", "PM C > B", "PM C > C", "PM C > D", "PM C > E", "PM C > F", "PM D > A", "PM D > B", "PM D > C", "PM D > D", "PM D > E", "PM D > F", "PM E > A", "PM E > B", "PM E > C", "PM E > D", "PM E > E", "PM E > F", "PM F > A", "PM F > B", "PM F > C", "PM F > D", "PM F > E", "PM F > F", "PD A > A", "PD A > B", "PD A > C", "PD A > D", "PD A > E", "PD A > F", "PD B > A", "PD B > B", "PD B > C", "PD B > D", "PD B > E", "PD B > F", "PD C > A", "PD C > B", "PD C > C", "PD C > D", "PD C > E", "PD C > F", "PD D > A", "PD D > B", "PD D > C", "PD D > D", "PD D > E", "PD D > F", "PD E > A", "PD E > B", "PD E > C", "PD E > D", "PD E > E", "PD E > F", "PD F > A", "PD F > B", "PD F > C", "PD F > D", "PD F > E", "PD F > F", "OSC 1 Wavefilter Pos", "OSC 1 Wavedistortion Pos", "OSC 2 Wavefilter Pos", "OSC 2 Wavedistortion Pos", "OSC 3 Wavefilter Pos", "OSC 3 Wavedistortion Pos", "OSC 4 Wavefilter Pos", "OSC 4 Wavedistortion Pos", "OSC 5 Wavefilter Pos", "OSC 5 Wavedistortion Pos", "OSC 6 Wavefilter Pos", "OSC 6 Wavedistortion Pos", "OSC 1 Frequency", "OSC 2 Frequency", "OSC 3 Frequency", "OSC 4 Frequency", "OSC 5 Frequency", "OSC 6 Frequency", "RM A > A", "RM A > B", "RM A > C", "RM A > D", "RM A > E", "RM A > F", "RM B > A", "RM B > B", "RM B > C", "RM B > D", "RM B > E", "RM B > F", "RM C > A", "RM C > B", "RM C > C", "RM C > D", "RM C > E", "RM C > F", "RM D > A", "RM D > B", "RM D > C", "RM D > D", "RM D > E", "RM D > F", "RM E > A", "RM E > B", "RM E > C", "RM E > D", "RM E > E", "RM E > F", "RM F > A", "RM F > B", "RM F > C", "RM F > D", "RM F > E", "RM F > F", "AM A > A", "AM A > B", "AM A > C", "AM A > D", "AM A > E", "AM A > F", "AM B > A", "AM B > B", "AM B > C", "AM B > D", "AM B > E", "AM B > F", "AM C > A", "AM C > B", "AM C > C", "AM C > D", "AM C > E", "AM C > F", "AM D > A", "AM D > B", "AM D > C", "AM D > D", "AM D > E", "AM D > F", "AM E > A", "AM E > B", "AM E > C", "AM E > D", "AM E > E", "AM E > F", "AM F > A", "AM F > B", "AM F > C", "AM F > D", "AM F > E", "AM F > F", "OSC 1 Physical Noise vs Mallet", "OSC 1 Physical Mallet Hardness", "OSC 1 Physical Noise Time", "OSC 1 Physical A Model", "OSC 1 Physical A Decay", "OSC 1 Physical A Material", "OSC 1 Physical A Hit Position", "OSC 1 Physical A Inharmonicity", "OSC 1 Physical B Model", "OSC 1 Physical B Decay", "OSC 1 Physical B Material", "OSC 1 Physical B Hit Position", "OSC 1 Physical B Inharmonicity", "OSC 1 Physical B Tune", "OSC 1 Physical A / B Balance", "OSC 1 Physical Coupling", "OSC 1 Juno Saw Level", "OSC 1 Juno Pulse Level", "OSC 1 Juno Pulse Width", "OSC 1 Juno PWM Depth", "OSC 1 Juno PWM Rate", "OSC 1 Juno Sub Level", "OSC 1 Juno Noise Level", "OSC 1 Juno Range", "OSC 1 Juno Drift", "OSC 1 Juno Saw Curve", "OSC 1 Juno Pulse Wave", "OSC 1 Juno Saw Wave", "OSC 1 Juno Sub Wave", "OSC 1 Juno PWM Source", "OSC 1 Juno Vibrato", "OSC 2 Physical Noise vs Mallet", "OSC 2 Physical Mallet Hardness", "OSC 2 Physical Noise Time", "OSC 2 Physical A Model", "OSC 2 Physical A Decay", "OSC 2 Physical A Material", "OSC 2 Physical A Hit Position", "OSC 2 Physical A Inharmonicity", "OSC 2 Physical B Model", "OSC 2 Physical B Decay", "OSC 2 Physical B Material", "OSC 2 Physical B Hit Position", "OSC 2 Physical B Inharmonicity", "OSC 2 Physical B Tune", "OSC 2 Physical A / B Balance", "OSC 2 Physical Coupling", "OSC 2 Juno Saw Level", "OSC 2 Juno Pulse Level", "OSC 2 Juno Pulse Width", "OSC 2 Juno PWM Depth", "OSC 2 Juno PWM Rate", "OSC 2 Juno Sub Level", "OSC 2 Juno Noise Level", "OSC 2 Juno Range", "OSC 2 Juno Drift", "OSC 2 Juno Saw Curve", "OSC 2 Juno Pulse Wave", "OSC 2 Juno Saw Wave", "OSC 2 Juno Sub Wave", "OSC 2 Juno PWM Source", "OSC 2 Juno Vibrato", "OSC 3 Physical Noise vs Mallet", "OSC 3 Physical Mallet Hardness", "OSC 3 Physical Noise Time", "OSC 3 Physical A Model", "OSC 3 Physical A Decay", "OSC 3 Physical A Material", "OSC 3 Physical A Hit Position", "OSC 3 Physical A Inharmonicity", "OSC 3 Physical B Model", "OSC 3 Physical B Decay", "OSC 3 Physical B Material", "OSC 3 Physical B Hit Position", "OSC 3 Physical B Inharmonicity", "OSC 3 Physical B Tune", "OSC 3 Physical A / B Balance", "OSC 3 Physical Coupling", "OSC 3 Juno Saw Level", "OSC 3 Juno Pulse Level", "OSC 3 Juno Pulse Width", "OSC 3 Juno PWM Depth", "OSC 3 Juno PWM Rate", "OSC 3 Juno Sub Level", "OSC 3 Juno Noise Level", "OSC 3 Juno Range", "OSC 3 Juno Drift", "OSC 3 Juno Saw Curve", "OSC 3 Juno Pulse Wave", "OSC 3 Juno Saw Wave", "OSC 3 Juno Sub Wave", "OSC 3 Juno PWM Source", "OSC 3 Juno Vibrato", "OSC 4 Physical Noise vs Mallet", "OSC 4 Physical Mallet Hardness", "OSC 4 Physical Noise Time", "OSC 4 Physical A Model", "OSC 4 Physical A Decay", "OSC 4 Physical A Material", "OSC 4 Physical A Hit Position", "OSC 4 Physical A Inharmonicity", "OSC 4 Physical B Model", "OSC 4 Physical B Decay", "OSC 4 Physical B Material", "OSC 4 Physical B Hit Position", "OSC 4 Physical B Inharmonicity", "OSC 4 Physical B Tune", "OSC 4 Physical A / B Balance", "OSC 4 Physical Coupling", "OSC 4 Juno Saw Level", "OSC 4 Juno Pulse Level", "OSC 4 Juno Pulse Width", "OSC 4 Juno PWM Depth", "OSC 4 Juno PWM Rate", "OSC 4 Juno Sub Level", "OSC 4 Juno Noise Level", "OSC 4 Juno Range", "OSC 4 Juno Drift", "OSC 4 Juno Saw Curve", "OSC 4 Juno Pulse Wave", "OSC 4 Juno Saw Wave", "OSC 4 Juno Sub Wave", "OSC 4 Juno PWM Source", "OSC 4 Juno Vibrato", "OSC 5 Physical Noise vs Mallet", "OSC 5 Physical Mallet Hardness", "OSC 5 Physical Noise Time", "OSC 5 Physical A Model", "OSC 5 Physical A Decay", "OSC 5 Physical A Material", "OSC 5 Physical A Hit Position", "OSC 5 Physical A Inharmonicity", "OSC 5 Physical B Model", "OSC 5 Physical B Decay", "OSC 5 Physical B Material", "OSC 5 Physical B Hit Position", "OSC 5 Physical B Inharmonicity", "OSC 5 Physical B Tune", "OSC 5 Physical A / B Balance", "OSC 5 Physical Coupling", "OSC 5 Juno Saw Level", "OSC 5 Juno Pulse Level", "OSC 5 Juno Pulse Width", "OSC 5 Juno PWM Depth", "OSC 5 Juno PWM Rate", "OSC 5 Juno Sub Level", "OSC 5 Juno Noise Level", "OSC 5 Juno Range", "OSC 5 Juno Drift", "OSC 5 Juno Saw Curve", "OSC 5 Juno Pulse Wave", "OSC 5 Juno Saw Wave", "OSC 5 Juno Sub Wave", "OSC 5 Juno PWM Source", "OSC 5 Juno Vibrato", "OSC 6 Physical Noise vs Mallet", "OSC 6 Physical Mallet Hardness", "OSC 6 Physical Noise Time", "OSC 6 Physical A Model", "OSC 6 Physical A Decay", "OSC 6 Physical A Material", "OSC 6 Physical A Hit Position", "OSC 6 Physical A Inharmonicity", "OSC 6 Physical B Model", "OSC 6 Physical B Decay", "OSC 6 Physical B Material", "OSC 6 Physical B Hit Position", "OSC 6 Physical B Inharmonicity", "OSC 6 Physical B Tune", "OSC 6 Physical A / B Balance", "OSC 6 Physical Coupling", "OSC 6 Juno Saw Level", "OSC 6 Juno Pulse Level", "OSC 6 Juno Pulse Width", "OSC 6 Juno PWM Depth", "OSC 6 Juno PWM Rate", "OSC 6 Juno Sub Level", "OSC 6 Juno Noise Level", "OSC 6 Juno Range", "OSC 6 Juno Drift", "OSC 6 Juno Saw Curve", "OSC 6 Juno Pulse Wave", "OSC 6 Juno Saw Wave", "OSC 6 Juno Sub Wave", "OSC 6 Juno PWM Source", "OSC 6 Juno Vibrato", "OSC 1 Kick Mode", "OSC 1 Kick Pitch Sweep", "OSC 1 Kick Sweep Time", "OSC 1 Kick Sweep Curve", "OSC 1 Kick Decay", "OSC 1 Kick Tone", "OSC 1 Kick Click Level", "OSC 1 Kick Click Tone", "OSC 1 Kick Noise Level", "OSC 1 Kick Drive", "OSC 1 Kick Drive Curve", "OSC 1 Kick Sub Level", "OSC 1 Kick Punch", "OSC 1 Kick Tune", "OSC 1 Kick Click Decay", "OSC 1 Kick Character", "OSC 2 Kick Mode", "OSC 2 Kick Pitch Sweep", "OSC 2 Kick Sweep Time", "OSC 2 Kick Sweep Curve", "OSC 2 Kick Decay", "OSC 2 Kick Tone", "OSC 2 Kick Click Level", "OSC 2 Kick Click Tone", "OSC 2 Kick Noise Level", "OSC 2 Kick Drive", "OSC 2 Kick Drive Curve", "OSC 2 Kick Sub Level", "OSC 2 Kick Punch", "OSC 2 Kick Tune", "OSC 2 Kick Click Decay", "OSC 2 Kick Character", "OSC 3 Kick Mode", "OSC 3 Kick Pitch Sweep", "OSC 3 Kick Sweep Time", "OSC 3 Kick Sweep Curve", "OSC 3 Kick Decay", "OSC 3 Kick Tone", "OSC 3 Kick Click Level", "OSC 3 Kick Click Tone", "OSC 3 Kick Noise Level", "OSC 3 Kick Drive", "OSC 3 Kick Drive Curve", "OSC 3 Kick Sub Level", "OSC 3 Kick Punch", "OSC 3 Kick Tune", "OSC 3 Kick Click Decay", "OSC 3 Kick Character", "OSC 4 Kick Mode", "OSC 4 Kick Pitch Sweep", "OSC 4 Kick Sweep Time", "OSC 4 Kick Sweep Curve", "OSC 4 Kick Decay", "OSC 4 Kick Tone", "OSC 4 Kick Click Level", "OSC 4 Kick Click Tone", "OSC 4 Kick Noise Level", "OSC 4 Kick Drive", "OSC 4 Kick Drive Curve", "OSC 4 Kick Sub Level", "OSC 4 Kick Punch", "OSC 4 Kick Tune", "OSC 4 Kick Click Decay", "OSC 4 Kick Character", "OSC 5 Kick Mode", "OSC 5 Kick Pitch Sweep", "OSC 5 Kick Sweep Time", "OSC 5 Kick Sweep Curve", "OSC 5 Kick Decay", "OSC 5 Kick Tone", "OSC 5 Kick Click Level", "OSC 5 Kick Click Tone", "OSC 5 Kick Noise Level", "OSC 5 Kick Drive", "OSC 5 Kick Drive Curve", "OSC 5 Kick Sub Level", "OSC 5 Kick Punch", "OSC 5 Kick Tune", "OSC 5 Kick Click Decay", "OSC 5 Kick Character", "OSC 6 Kick Mode", "OSC 6 Kick Pitch Sweep", "OSC 6 Kick Sweep Time", "OSC 6 Kick Sweep Curve", "OSC 6 Kick Decay", "OSC 6 Kick Tone", "OSC 6 Kick Click Level", "OSC 6 Kick Click Tone", "OSC 6 Kick Noise Level", "OSC 6 Kick Drive", "OSC 6 Kick Drive Curve", "OSC 6 Kick Sub Level", "OSC 6 Kick Punch", "OSC 6 Kick Tune", "OSC 6 Kick Click Decay", "OSC 6 Kick Character", "OSC 1 Terrain Orbit Center X", "OSC 1 Terrain Orbit Center Y", "OSC 1 Terrain Orbit Radius X", "OSC 1 Terrain Orbit Radius Y", "OSC 1 Terrain Orbit Rotation", "OSC 1 Terrain Orbit Ratio", "OSC 1 Terrain Orbit Phase", "OSC 1 Terrain Orbit Shape", "OSC 1 Terrain Move Rate", "OSC 1 Terrain Move Depth", "OSC 1 Terrain B", "OSC 1 Terrain Morph A to B", "OSC 1 Terrain Smooth", "OSC 1 Terrain Drive", "OSC 1 Terrain Bit Depth", "OSC 1 Terrain Velocity to Radius", "OSC 2 Terrain Orbit Center X", "OSC 2 Terrain Orbit Center Y", "OSC 2 Terrain Orbit Radius X", "OSC 2 Terrain Orbit Radius Y", "OSC 2 Terrain Orbit Rotation", "OSC 2 Terrain Orbit Ratio", "OSC 2 Terrain Orbit Phase", "OSC 2 Terrain Orbit Shape", "OSC 2 Terrain Move Rate", "OSC 2 Terrain Move Depth", "OSC 2 Terrain B", "OSC 2 Terrain Morph A to B", "OSC 2 Terrain Smooth", "OSC 2 Terrain Drive", "OSC 2 Terrain Bit Depth", "OSC 2 Terrain Velocity to Radius", "OSC 3 Terrain Orbit Center X", "OSC 3 Terrain Orbit Center Y", "OSC 3 Terrain Orbit Radius X", "OSC 3 Terrain Orbit Radius Y", "OSC 3 Terrain Orbit Rotation", "OSC 3 Terrain Orbit Ratio", "OSC 3 Terrain Orbit Phase", "OSC 3 Terrain Orbit Shape", "OSC 3 Terrain Move Rate", "OSC 3 Terrain Move Depth", "OSC 3 Terrain B", "OSC 3 Terrain Morph A to B", "OSC 3 Terrain Smooth", "OSC 3 Terrain Drive", "OSC 3 Terrain Bit Depth", "OSC 3 Terrain Velocity to Radius", "OSC 4 Terrain Orbit Center X", "OSC 4 Terrain Orbit Center Y", "OSC 4 Terrain Orbit Radius X", "OSC 4 Terrain Orbit Radius Y", "OSC 4 Terrain Orbit Rotation", "OSC 4 Terrain Orbit Ratio", "OSC 4 Terrain Orbit Phase", "OSC 4 Terrain Orbit Shape", "OSC 4 Terrain Move Rate", "OSC 4 Terrain Move Depth", "OSC 4 Terrain B", "OSC 4 Terrain Morph A to B", "OSC 4 Terrain Smooth", "OSC 4 Terrain Drive", "OSC 4 Terrain Bit Depth", "OSC 4 Terrain Velocity to Radius", "OSC 5 Terrain Orbit Center X", "OSC 5 Terrain Orbit Center Y", "OSC 5 Terrain Orbit Radius X", "OSC 5 Terrain Orbit Radius Y", "OSC 5 Terrain Orbit Rotation", "OSC 5 Terrain Orbit Ratio", "OSC 5 Terrain Orbit Phase", "OSC 5 Terrain Orbit Shape", "OSC 5 Terrain Move Rate", "OSC 5 Terrain Move Depth", "OSC 5 Terrain B", "OSC 5 Terrain Morph A to B", "OSC 5 Terrain Smooth", "OSC 5 Terrain Drive", "OSC 5 Terrain Bit Depth", "OSC 5 Terrain Velocity to Radius", "OSC 6 Terrain Orbit Center X", "OSC 6 Terrain Orbit Center Y", "OSC 6 Terrain Orbit Radius X", "OSC 6 Terrain Orbit Radius Y", "OSC 6 Terrain Orbit Rotation", "OSC 6 Terrain Orbit Ratio", "OSC 6 Terrain Orbit Phase", "OSC 6 Terrain Orbit Shape", "OSC 6 Terrain Move Rate", "OSC 6 Terrain Move Depth", "OSC 6 Terrain B", "OSC 6 Terrain Morph A to B", "OSC 6 Terrain Smooth", "OSC 6 Terrain Drive", "OSC 6 Terrain Bit Depth", "OSC 6 Terrain Velocity to Radius", "OSC 1 Waveguide Model", "OSC 1 Waveguide Decay", "OSC 1 Waveguide Tone", "OSC 1 Waveguide Excite", "OSC 1 Waveguide Position", "OSC 1 Waveguide Noise", "OSC 1 Waveguide Nonlinear", "OSC 1 Waveguide Stretch", "OSC 1 Waveguide Attack", "OSC 1 Waveguide Snare", "OSC 1 Waveguide Body", "OSC 1 Waveguide Body Tune", "OSC 1 Waveguide Velocity", "OSC 1 Waveguide Drive", "OSC 1 Waveguide Tension", "OSC 1 Waveguide Key Decay", "OSC 2 Waveguide Model", "OSC 2 Waveguide Decay", "OSC 2 Waveguide Tone", "OSC 2 Waveguide Excite", "OSC 2 Waveguide Position", "OSC 2 Waveguide Noise", "OSC 2 Waveguide Nonlinear", "OSC 2 Waveguide Stretch", "OSC 2 Waveguide Attack", "OSC 2 Waveguide Snare", "OSC 2 Waveguide Body", "OSC 2 Waveguide Body Tune", "OSC 2 Waveguide Velocity", "OSC 2 Waveguide Drive", "OSC 2 Waveguide Tension", "OSC 2 Waveguide Key Decay", "OSC 3 Waveguide Model", "OSC 3 Waveguide Decay", "OSC 3 Waveguide Tone", "OSC 3 Waveguide Excite", "OSC 3 Waveguide Position", "OSC 3 Waveguide Noise", "OSC 3 Waveguide Nonlinear", "OSC 3 Waveguide Stretch", "OSC 3 Waveguide Attack", "OSC 3 Waveguide Snare", "OSC 3 Waveguide Body", "OSC 3 Waveguide Body Tune", "OSC 3 Waveguide Velocity", "OSC 3 Waveguide Drive", "OSC 3 Waveguide Tension", "OSC 3 Waveguide Key Decay", "OSC 4 Waveguide Model", "OSC 4 Waveguide Decay", "OSC 4 Waveguide Tone", "OSC 4 Waveguide Excite", "OSC 4 Waveguide Position", "OSC 4 Waveguide Noise", "OSC 4 Waveguide Nonlinear", "OSC 4 Waveguide Stretch", "OSC 4 Waveguide Attack", "OSC 4 Waveguide Snare", "OSC 4 Waveguide Body", "OSC 4 Waveguide Body Tune", "OSC 4 Waveguide Velocity", "OSC 4 Waveguide Drive", "OSC 4 Waveguide Tension", "OSC 4 Waveguide Key Decay", "OSC 5 Waveguide Model", "OSC 5 Waveguide Decay", "OSC 5 Waveguide Tone", "OSC 5 Waveguide Excite", "OSC 5 Waveguide Position", "OSC 5 Waveguide Noise", "OSC 5 Waveguide Nonlinear", "OSC 5 Waveguide Stretch", "OSC 5 Waveguide Attack", "OSC 5 Waveguide Snare", "OSC 5 Waveguide Body", "OSC 5 Waveguide Body Tune", "OSC 5 Waveguide Velocity", "OSC 5 Waveguide Drive", "OSC 5 Waveguide Tension", "OSC 5 Waveguide Key Decay", "OSC 6 Waveguide Model", "OSC 6 Waveguide Decay", "OSC 6 Waveguide Tone", "OSC 6 Waveguide Excite", "OSC 6 Waveguide Position", "OSC 6 Waveguide Noise", "OSC 6 Waveguide Nonlinear", "OSC 6 Waveguide Stretch", "OSC 6 Waveguide Attack", "OSC 6 Waveguide Snare", "OSC 6 Waveguide Body", "OSC 6 Waveguide Body Tune", "OSC 6 Waveguide Velocity", "OSC 6 Waveguide Drive", "OSC 6 Waveguide Tension", "OSC 6 Waveguide Key Decay", "OSC 1 JP Waveform", "OSC 1 JP Pulse Width", "OSC 1 JP PWM Depth", "OSC 1 JP PWM Rate", "OSC 1 JP Super Saw Detune", "OSC 1 JP Super Saw Mix", "OSC 1 JP Stereo Width", "OSC 1 JP Feedback", "OSC 1 JP Feedback Color", "OSC 1 JP Tri Mod Depth", "OSC 1 JP Tri Mod Ratio", "OSC 1 JP Spectrum Tilt", "OSC 1 JP Spectrum Peak", "OSC 1 JP Noise Mix", "OSC 1 JP Drive", "OSC 1 JP Sub Oscillator", "OSC 2 JP Waveform", "OSC 2 JP Pulse Width", "OSC 2 JP PWM Depth", "OSC 2 JP PWM Rate", "OSC 2 JP Super Saw Detune", "OSC 2 JP Super Saw Mix", "OSC 2 JP Stereo Width", "OSC 2 JP Feedback", "OSC 2 JP Feedback Color", "OSC 2 JP Tri Mod Depth", "OSC 2 JP Tri Mod Ratio", "OSC 2 JP Spectrum Tilt", "OSC 2 JP Spectrum Peak", "OSC 2 JP Noise Mix", "OSC 2 JP Drive", "OSC 2 JP Sub Oscillator", "OSC 3 JP Waveform", "OSC 3 JP Pulse Width", "OSC 3 JP PWM Depth", "OSC 3 JP PWM Rate", "OSC 3 JP Super Saw Detune", "OSC 3 JP Super Saw Mix", "OSC 3 JP Stereo Width", "OSC 3 JP Feedback", "OSC 3 JP Feedback Color", "OSC 3 JP Tri Mod Depth", "OSC 3 JP Tri Mod Ratio", "OSC 3 JP Spectrum Tilt", "OSC 3 JP Spectrum Peak", "OSC 3 JP Noise Mix", "OSC 3 JP Drive", "OSC 3 JP Sub Oscillator", "OSC 4 JP Waveform", "OSC 4 JP Pulse Width", "OSC 4 JP PWM Depth", "OSC 4 JP PWM Rate", "OSC 4 JP Super Saw Detune", "OSC 4 JP Super Saw Mix", "OSC 4 JP Stereo Width", "OSC 4 JP Feedback", "OSC 4 JP Feedback Color", "OSC 4 JP Tri Mod Depth", "OSC 4 JP Tri Mod Ratio", "OSC 4 JP Spectrum Tilt", "OSC 4 JP Spectrum Peak", "OSC 4 JP Noise Mix", "OSC 4 JP Drive", "OSC 4 JP Sub Oscillator", "OSC 5 JP Waveform", "OSC 5 JP Pulse Width", "OSC 5 JP PWM Depth", "OSC 5 JP PWM Rate", "OSC 5 JP Super Saw Detune", "OSC 5 JP Super Saw Mix", "OSC 5 JP Stereo Width", "OSC 5 JP Feedback", "OSC 5 JP Feedback Color", "OSC 5 JP Tri Mod Depth", "OSC 5 JP Tri Mod Ratio", "OSC 5 JP Spectrum Tilt", "OSC 5 JP Spectrum Peak", "OSC 5 JP Noise Mix", "OSC 5 JP Drive", "OSC 5 JP Sub Oscillator", "OSC 6 JP Waveform", "OSC 6 JP Pulse Width", "OSC 6 JP PWM Depth", "OSC 6 JP PWM Rate", "OSC 6 JP Super Saw Detune", "OSC 6 JP Super Saw Mix", "OSC 6 JP Stereo Width", "OSC 6 JP Feedback", "OSC 6 JP Feedback Color", "OSC 6 JP Tri Mod Depth", "OSC 6 JP Tri Mod Ratio", "OSC 6 JP Spectrum Tilt", "OSC 6 JP Spectrum Peak", "OSC 6 JP Noise Mix", "OSC 6 JP Drive", "OSC 6 JP Sub Oscillator", "OSC 1 Granular Position", "OSC 1 Granular Grain Size", "OSC 1 Granular Density", "OSC 1 Granular Spray", "OSC 1 Granular Pitch Spread", "OSC 1 Granular Pan Spread", "OSC 1 Granular Window", "OSC 1 Granular Reverse", "OSC 1 Granular Scan", "OSC 1 Granular Timing", "OSC 1 Granular Drive", "OSC 1 Granular Velocity", "OSC 1 (unused 840)", "OSC 1 (unused 841)", "OSC 1 (unused 842)", "OSC 1 (unused 843)", "OSC 2 Granular Position", "OSC 2 Granular Grain Size", "OSC 2 Granular Density", "OSC 2 Granular Spray", "OSC 2 Granular Pitch Spread", "OSC 2 Granular Pan Spread", "OSC 2 Granular Window", "OSC 2 Granular Reverse", "OSC 2 Granular Scan", "OSC 2 Granular Timing", "OSC 2 Granular Drive", "OSC 2 Granular Velocity", "OSC 2 (unused 856)", "OSC 2 (unused 857)", "OSC 2 (unused 858)", "OSC 2 (unused 859)", "OSC 3 Granular Position", "OSC 3 Granular Grain Size", "OSC 3 Granular Density", "OSC 3 Granular Spray", "OSC 3 Granular Pitch Spread", "OSC 3 Granular Pan Spread", "OSC 3 Granular Window", "OSC 3 Granular Reverse", "OSC 3 Granular Scan", "OSC 3 Granular Timing", "OSC 3 Granular Drive", "OSC 3 Granular Velocity", "OSC 3 (unused 872)", "OSC 3 (unused 873)", "OSC 3 (unused 874)", "OSC 3 (unused 875)", "OSC 4 Granular Position", "OSC 4 Granular Grain Size", "OSC 4 Granular Density", "OSC 4 Granular Spray", "OSC 4 Granular Pitch Spread", "OSC 4 Granular Pan Spread", "OSC 4 Granular Window", "OSC 4 Granular Reverse", "OSC 4 Granular Scan", "OSC 4 Granular Timing", "OSC 4 Granular Drive", "OSC 4 Granular Velocity", "OSC 4 (unused 888)", "OSC 4 (unused 889)", "OSC 4 (unused 890)", "OSC 4 (unused 891)", "OSC 5 Granular Position", "OSC 5 Granular Grain Size", "OSC 5 Granular Density", "OSC 5 Granular Spray", "OSC 5 Granular Pitch Spread", "OSC 5 Granular Pan Spread", "OSC 5 Granular Window", "OSC 5 Granular Reverse", "OSC 5 Granular Scan", "OSC 5 Granular Timing", "OSC 5 Granular Drive", "OSC 5 Granular Velocity", "OSC 5 (unused 904)", "OSC 5 (unused 905)", "OSC 5 (unused 906)", "OSC 5 (unused 907)", "OSC 6 Granular Position", "OSC 6 Granular Grain Size", "OSC 6 Granular Density", "OSC 6 Granular Spray", "OSC 6 Granular Pitch Spread", "OSC 6 Granular Pan Spread", "OSC 6 Granular Window", "OSC 6 Granular Reverse", "OSC 6 Granular Scan", "OSC 6 Granular Timing", "OSC 6 Granular Drive", "OSC 6 Granular Velocity", "OSC 6 (unused 920)", "OSC 6 (unused 921)", "OSC 6 (unused 922)", "OSC 6 (unused 923)", "OSC 1 Additive Spectrum A", "OSC 1 Additive Spectrum B", "OSC 1 Additive Morph", "OSC 1 Additive Partials", "OSC 1 Additive Tilt", "OSC 1 Additive Odd / Even", "OSC 1 Additive Inharmonicity", "OSC 1 Additive Formant", "OSC 1 Additive Formant Gain", "OSC 1 Additive Shimmer", "OSC 1 Additive Shimmer Rate", "OSC 1 Additive Partial Decay", "OSC 1 Additive Drive", "OSC 1 Additive Stereo Spread", "OSC 1 Additive Velocity", "OSC 1 (unused 939)", "OSC 2 Additive Spectrum A", "OSC 2 Additive Spectrum B", "OSC 2 Additive Morph", "OSC 2 Additive Partials", "OSC 2 Additive Tilt", "OSC 2 Additive Odd / Even", "OSC 2 Additive Inharmonicity", "OSC 2 Additive Formant", "OSC 2 Additive Formant Gain", "OSC 2 Additive Shimmer", "OSC 2 Additive Shimmer Rate", "OSC 2 Additive Partial Decay", "OSC 2 Additive Drive", "OSC 2 Additive Stereo Spread", "OSC 2 Additive Velocity", "OSC 2 (unused 955)", "OSC 3 Additive Spectrum A", "OSC 3 Additive Spectrum B", "OSC 3 Additive Morph", "OSC 3 Additive Partials", "OSC 3 Additive Tilt", "OSC 3 Additive Odd / Even", "OSC 3 Additive Inharmonicity", "OSC 3 Additive Formant", "OSC 3 Additive Formant Gain", "OSC 3 Additive Shimmer", "OSC 3 Additive Shimmer Rate", "OSC 3 Additive Partial Decay", "OSC 3 Additive Drive", "OSC 3 Additive Stereo Spread", "OSC 3 Additive Velocity", "OSC 3 (unused 971)", "OSC 4 Additive Spectrum A", "OSC 4 Additive Spectrum B", "OSC 4 Additive Morph", "OSC 4 Additive Partials", "OSC 4 Additive Tilt", "OSC 4 Additive Odd / Even", "OSC 4 Additive Inharmonicity", "OSC 4 Additive Formant", "OSC 4 Additive Formant Gain", "OSC 4 Additive Shimmer", "OSC 4 Additive Shimmer Rate", "OSC 4 Additive Partial Decay", "OSC 4 Additive Drive", "OSC 4 Additive Stereo Spread", "OSC 4 Additive Velocity", "OSC 4 (unused 987)", "OSC 5 Additive Spectrum A", "OSC 5 Additive Spectrum B", "OSC 5 Additive Morph", "OSC 5 Additive Partials", "OSC 5 Additive Tilt", "OSC 5 Additive Odd / Even", "OSC 5 Additive Inharmonicity", "OSC 5 Additive Formant", "OSC 5 Additive Formant Gain", "OSC 5 Additive Shimmer", "OSC 5 Additive Shimmer Rate", "OSC 5 Additive Partial Decay", "OSC 5 Additive Drive", "OSC 5 Additive Stereo Spread", "OSC 5 Additive Velocity", "OSC 5 (unused 1003)", "OSC 6 Additive Spectrum A", "OSC 6 Additive Spectrum B", "OSC 6 Additive Morph", "OSC 6 Additive Partials", "OSC 6 Additive Tilt", "OSC 6 Additive Odd / Even", "OSC 6 Additive Inharmonicity", "OSC 6 Additive Formant", "OSC 6 Additive Formant Gain", "OSC 6 Additive Shimmer", "OSC 6 Additive Shimmer Rate", "OSC 6 Additive Partial Decay", "OSC 6 Additive Drive", "OSC 6 Additive Stereo Spread", "OSC 6 Additive Velocity", "OSC 6 (unused 1019)", "OSC 1 Drum Decay", "OSC 1 Drum Head Tone", "OSC 1 Drum Hit Position", "OSC 1 Drum Stick", "OSC 1 Drum Edge", "OSC 1 Drum Reso Head", "OSC 1 Drum Reso Tune", "OSC 1 Drum Shell", "OSC 1 Drum Shell Depth", "OSC 1 Drum Snare", "OSC 1 Drum Snare Tension", "OSC 1 Drum Sympathetic", "OSC 1 Drum Tension", "OSC 1 Drum Velocity", "OSC 1 Drum Drive", "OSC 1 Drum Size", "OSC 2 Drum Decay", "OSC 2 Drum Head Tone", "OSC 2 Drum Hit Position", "OSC 2 Drum Stick", "OSC 2 Drum Edge", "OSC 2 Drum Reso Head", "OSC 2 Drum Reso Tune", "OSC 2 Drum Shell", "OSC 2 Drum Shell Depth", "OSC 2 Drum Snare", "OSC 2 Drum Snare Tension", "OSC 2 Drum Sympathetic", "OSC 2 Drum Tension", "OSC 2 Drum Velocity", "OSC 2 Drum Drive", "OSC 2 Drum Size", "OSC 3 Drum Decay", "OSC 3 Drum Head Tone", "OSC 3 Drum Hit Position", "OSC 3 Drum Stick", "OSC 3 Drum Edge", "OSC 3 Drum Reso Head", "OSC 3 Drum Reso Tune", "OSC 3 Drum Shell", "OSC 3 Drum Shell Depth", "OSC 3 Drum Snare", "OSC 3 Drum Snare Tension", "OSC 3 Drum Sympathetic", "OSC 3 Drum Tension", "OSC 3 Drum Velocity", "OSC 3 Drum Drive", "OSC 3 Drum Size", "OSC 4 Drum Decay", "OSC 4 Drum Head Tone", "OSC 4 Drum Hit Position", "OSC 4 Drum Stick", "OSC 4 Drum Edge", "OSC 4 Drum Reso Head", "OSC 4 Drum Reso Tune", "OSC 4 Drum Shell", "OSC 4 Drum Shell Depth", "OSC 4 Drum Snare", "OSC 4 Drum Snare Tension", "OSC 4 Drum Sympathetic", "OSC 4 Drum Tension", "OSC 4 Drum Velocity", "OSC 4 Drum Drive", "OSC 4 Drum Size", "OSC 5 Drum Decay", "OSC 5 Drum Head Tone", "OSC 5 Drum Hit Position", "OSC 5 Drum Stick", "OSC 5 Drum Edge", "OSC 5 Drum Reso Head", "OSC 5 Drum Reso Tune", "OSC 5 Drum Shell", "OSC 5 Drum Shell Depth", "OSC 5 Drum Snare", "OSC 5 Drum Snare Tension", "OSC 5 Drum Sympathetic", "OSC 5 Drum Tension", "OSC 5 Drum Velocity", "OSC 5 Drum Drive", "OSC 5 Drum Size", "OSC 6 Drum Decay", "OSC 6 Drum Head Tone", "OSC 6 Drum Hit Position", "OSC 6 Drum Stick", "OSC 6 Drum Edge", "OSC 6 Drum Reso Head", "OSC 6 Drum Reso Tune", "OSC 6 Drum Shell", "OSC 6 Drum Shell Depth", "OSC 6 Drum Snare", "OSC 6 Drum Snare Tension", "OSC 6 Drum Sympathetic", "OSC 6 Drum Tension", "OSC 6 Drum Velocity", "OSC 6 Drum Drive", "OSC 6 Drum Size", "OSC 1 Spectral Mode", "OSC 1 Spectral Position", "OSC 1 Spectral Position B", "OSC 1 Spectral Morph", "OSC 1 Spectral Scan", "OSC 1 Spectral Blur", "OSC 1 Spectral Shift", "OSC 1 Spectral Tilt", "OSC 1 Spectral Harmonics", "OSC 1 Spectral Odd Even", "OSC 1 Spectral Comb", "OSC 1 Spectral Contrast", "OSC 1 Spectral Jitter", "OSC 1 Spectral Spread", "OSC 1 Spectral Width", "OSC 1 Spectral Velocity", "OSC 2 Spectral Mode", "OSC 2 Spectral Position", "OSC 2 Spectral Position B", "OSC 2 Spectral Morph", "OSC 2 Spectral Scan", "OSC 2 Spectral Blur", "OSC 2 Spectral Shift", "OSC 2 Spectral Tilt", "OSC 2 Spectral Harmonics", "OSC 2 Spectral Odd Even", "OSC 2 Spectral Comb", "OSC 2 Spectral Contrast", "OSC 2 Spectral Jitter", "OSC 2 Spectral Spread", "OSC 2 Spectral Width", "OSC 2 Spectral Velocity", "OSC 3 Spectral Mode", "OSC 3 Spectral Position", "OSC 3 Spectral Position B", "OSC 3 Spectral Morph", "OSC 3 Spectral Scan", "OSC 3 Spectral Blur", "OSC 3 Spectral Shift", "OSC 3 Spectral Tilt", "OSC 3 Spectral Harmonics", "OSC 3 Spectral Odd Even", "OSC 3 Spectral Comb", "OSC 3 Spectral Contrast", "OSC 3 Spectral Jitter", "OSC 3 Spectral Spread", "OSC 3 Spectral Width", "OSC 3 Spectral Velocity", "OSC 4 Spectral Mode", "OSC 4 Spectral Position", "OSC 4 Spectral Position B", "OSC 4 Spectral Morph", "OSC 4 Spectral Scan", "OSC 4 Spectral Blur", "OSC 4 Spectral Shift", "OSC 4 Spectral Tilt", "OSC 4 Spectral Harmonics", "OSC 4 Spectral Odd Even", "OSC 4 Spectral Comb", "OSC 4 Spectral Contrast", "OSC 4 Spectral Jitter", "OSC 4 Spectral Spread", "OSC 4 Spectral Width", "OSC 4 Spectral Velocity", "OSC 5 Spectral Mode", "OSC 5 Spectral Position", "OSC 5 Spectral Position B", "OSC 5 Spectral Morph", "OSC 5 Spectral Scan", "OSC 5 Spectral Blur", "OSC 5 Spectral Shift", "OSC 5 Spectral Tilt", "OSC 5 Spectral Harmonics", "OSC 5 Spectral Odd Even", "OSC 5 Spectral Comb", "OSC 5 Spectral Contrast", "OSC 5 Spectral Jitter", "OSC 5 Spectral Spread", "OSC 5 Spectral Width", "OSC 5 Spectral Velocity", "OSC 6 Spectral Mode", "OSC 6 Spectral Position", "OSC 6 Spectral Position B", "OSC 6 Spectral Morph", "OSC 6 Spectral Scan", "OSC 6 Spectral Blur", "OSC 6 Spectral Shift", "OSC 6 Spectral Tilt", "OSC 6 Spectral Harmonics", "OSC 6 Spectral Odd Even", "OSC 6 Spectral Comb", "OSC 6 Spectral Contrast", "OSC 6 Spectral Jitter", "OSC 6 Spectral Spread", "OSC 6 Spectral Width", "OSC 6 Spectral Velocity", "OSC 1 SoundFont Gain", "OSC 1 SoundFont Velocity", "OSC 1 SoundFont Attack", "OSC 1 SoundFont Decay", "OSC 1 SoundFont Sustain", "OSC 1 SoundFont Release", "OSC 1 SoundFont Loop", "OSC 1 SoundFont Stereo", "OSC 1 SoundFont Start", "OSC 1 SoundFont Drive", "OSC 1 (unused 1222)", "OSC 1 (unused 1223)", "OSC 1 (unused 1224)", "OSC 1 (unused 1225)", "OSC 1 (unused 1226)", "OSC 1 (unused 1227)", "OSC 2 SoundFont Gain", "OSC 2 SoundFont Velocity", "OSC 2 SoundFont Attack", "OSC 2 SoundFont Decay", "OSC 2 SoundFont Sustain", "OSC 2 SoundFont Release", "OSC 2 SoundFont Loop", "OSC 2 SoundFont Stereo", "OSC 2 SoundFont Start", "OSC 2 SoundFont Drive", "OSC 2 (unused 1238)", "OSC 2 (unused 1239)", "OSC 2 (unused 1240)", "OSC 2 (unused 1241)", "OSC 2 (unused 1242)", "OSC 2 (unused 1243)", "OSC 3 SoundFont Gain", "OSC 3 SoundFont Velocity", "OSC 3 SoundFont Attack", "OSC 3 SoundFont Decay", "OSC 3 SoundFont Sustain", "OSC 3 SoundFont Release", "OSC 3 SoundFont Loop", "OSC 3 SoundFont Stereo", "OSC 3 SoundFont Start", "OSC 3 SoundFont Drive", "OSC 3 (unused 1254)", "OSC 3 (unused 1255)", "OSC 3 (unused 1256)", "OSC 3 (unused 1257)", "OSC 3 (unused 1258)", "OSC 3 (unused 1259)", "OSC 4 SoundFont Gain", "OSC 4 SoundFont Velocity", "OSC 4 SoundFont Attack", "OSC 4 SoundFont Decay", "OSC 4 SoundFont Sustain", "OSC 4 SoundFont Release", "OSC 4 SoundFont Loop", "OSC 4 SoundFont Stereo", "OSC 4 SoundFont Start", "OSC 4 SoundFont Drive", "OSC 4 (unused 1270)", "OSC 4 (unused 1271)", "OSC 4 (unused 1272)", "OSC 4 (unused 1273)", "OSC 4 (unused 1274)", "OSC 4 (unused 1275)", "OSC 5 SoundFont Gain", "OSC 5 SoundFont Velocity", "OSC 5 SoundFont Attack", "OSC 5 SoundFont Decay", "OSC 5 SoundFont Sustain", "OSC 5 SoundFont Release", "OSC 5 SoundFont Loop", "OSC 5 SoundFont Stereo", "OSC 5 SoundFont Start", "OSC 5 SoundFont Drive", "OSC 5 (unused 1286)", "OSC 5 (unused 1287)", "OSC 5 (unused 1288)", "OSC 5 (unused 1289)", "OSC 5 (unused 1290)", "OSC 5 (unused 1291)", "OSC 6 SoundFont Gain", "OSC 6 SoundFont Velocity", "OSC 6 SoundFont Attack", "OSC 6 SoundFont Decay", "OSC 6 SoundFont Sustain", "OSC 6 SoundFont Release", "OSC 6 SoundFont Loop", "OSC 6 SoundFont Stereo", "OSC 6 SoundFont Start", "OSC 6 SoundFont Drive", "OSC 6 (unused 1302)", "OSC 6 (unused 1303)", "OSC 6 (unused 1304)", "OSC 6 (unused 1305)", "OSC 6 (unused 1306)", "OSC 6 (unused 1307)", "TZFM A > A", "TZFM A > B", "TZFM A > C", "TZFM A > D", "TZFM A > E", "TZFM A > F", "TZFM B > A", "TZFM B > B", "TZFM B > C", "TZFM B > D", "TZFM B > E", "TZFM B > F", "TZFM C > A", "TZFM C > B", "TZFM C > C", "TZFM C > D", "TZFM C > E", "TZFM C > F", "TZFM D > A", "TZFM D > B", "TZFM D > C", "TZFM D > D", "TZFM D > E", "TZFM D > F", "TZFM E > A", "TZFM E > B", "TZFM E > C", "TZFM E > D", "TZFM E > E", "TZFM E > F", "TZFM F > A", "TZFM F > B", "TZFM F > C", "TZFM F > D", "TZFM F > E", "TZFM F > F", "XF A > A", "XF A > B", "XF A > C", "XF A > D", "XF A > E", "XF A > F", "XF B > A", "XF B > B", "XF B > C", "XF B > D", "XF B > E", "XF B > F", "XF C > A", "XF C > B", "XF C > C", "XF C > D", "XF C > E", "XF C > F", "XF D > A", "XF D > B", "XF D > C", "XF D > D", "XF D > E", "XF D > F", "XF E > A", "XF E > B", "XF E > C", "XF E > D", "XF E > E", "XF E > F", "XF F > A", "XF F > B", "XF F > C", "XF F > D", "XF F > E", "XF F > F", "FD A > A", "FD A > B", "FD A > C", "FD A > D", "FD A > E", "FD A > F", "FD B > A", "FD B > B", "FD B > C", "FD B > D", "FD B > E", "FD B > F", "FD C > A", "FD C > B", "FD C > C", "FD C > D", "FD C > E", "FD C > F", "FD D > A", "FD D > B", "FD D > C", "FD D > D", "FD D > E", "FD D > F", "FD E > A", "FD E > B", "FD E > C", "FD E > D", "FD E > E", "FD E > F", "FD F > A", "FD F > B", "FD F > C", "FD F > D", "FD F > E", "FD F > F", "XR A > A", "XR A > B", "XR A > C", "XR A > D", "XR A > E", "XR A > F", "XR B > A", "XR B > B", "XR B > C", "XR B > D", "XR B > E", "XR B > F", "XR C > A", "XR C > B", "XR C > C", "XR C > D", "XR C > E", "XR C > F", "XR D > A", "XR D > B", "XR D > C", "XR D > D", "XR D > E", "XR D > F", "XR E > A", "XR E > B", "XR E > C", "XR E > D", "XR E > E", "XR E > F", "XR F > A", "XR F > B", "XR F > C", "XR F > D", "XR F > E", "XR F > F", "CP A > A", "CP A > B", "CP A > C", "CP A > D", "CP A > E", "CP A > F", "CP B > A", "CP B > B", "CP B > C", "CP B > D", "CP B > E", "CP B > F", "CP C > A", "CP C > B", "CP C > C", "CP C > D", "CP C > E", "CP C > F", "CP D > A", "CP D > B", "CP D > C", "CP D > D", "CP D > E", "CP D > F", "CP E > A", "CP E > B", "CP E > C", "CP E > D", "CP E > E", "CP E > F", "CP F > A", "CP F > B", "CP F > C", "CP F > D", "CP F > E", "CP F > F", "OSC 1 Bagpipe Scale", "OSC 1 Bagpipe Reed", "OSC 1 Bagpipe Reed Type", "OSC 1 Bagpipe Bore Shape", "OSC 1 Bagpipe Coupling", "OSC 1 Bagpipe Bore", "OSC 1 Bagpipe Fluctuation", "OSC 1 Bagpipe Air", "OSC 1 Bagpipe Colour Mix", "OSC 1 Bagpipe Colour Freq", "OSC 1 Bagpipe Drone Level", "OSC 1 Bagpipe Drone Chord", "OSC 1 Bagpipe Drone Key", "OSC 1 Bagpipe Strike-In", "OSC 1 Bagpipe Vibrato", "OSC 1 Bagpipe Blow", "OSC 2 Bagpipe Scale", "OSC 2 Bagpipe Reed", "OSC 2 Bagpipe Reed Type", "OSC 2 Bagpipe Bore Shape", "OSC 2 Bagpipe Coupling", "OSC 2 Bagpipe Bore", "OSC 2 Bagpipe Fluctuation", "OSC 2 Bagpipe Air", "OSC 2 Bagpipe Colour Mix", "OSC 2 Bagpipe Colour Freq", "OSC 2 Bagpipe Drone Level", "OSC 2 Bagpipe Drone Chord", "OSC 2 Bagpipe Drone Key", "OSC 2 Bagpipe Strike-In", "OSC 2 Bagpipe Vibrato", "OSC 2 Bagpipe Blow", "OSC 3 Bagpipe Scale", "OSC 3 Bagpipe Reed", "OSC 3 Bagpipe Reed Type", "OSC 3 Bagpipe Bore Shape", "OSC 3 Bagpipe Coupling", "OSC 3 Bagpipe Bore", "OSC 3 Bagpipe Fluctuation", "OSC 3 Bagpipe Air", "OSC 3 Bagpipe Colour Mix", "OSC 3 Bagpipe Colour Freq", "OSC 3 Bagpipe Drone Level", "OSC 3 Bagpipe Drone Chord", "OSC 3 Bagpipe Drone Key", "OSC 3 Bagpipe Strike-In", "OSC 3 Bagpipe Vibrato", "OSC 3 Bagpipe Blow", "OSC 4 Bagpipe Scale", "OSC 4 Bagpipe Reed", "OSC 4 Bagpipe Reed Type", "OSC 4 Bagpipe Bore Shape", "OSC 4 Bagpipe Coupling", "OSC 4 Bagpipe Bore", "OSC 4 Bagpipe Fluctuation", "OSC 4 Bagpipe Air", "OSC 4 Bagpipe Colour Mix", "OSC 4 Bagpipe Colour Freq", "OSC 4 Bagpipe Drone Level", "OSC 4 Bagpipe Drone Chord", "OSC 4 Bagpipe Drone Key", "OSC 4 Bagpipe Strike-In", "OSC 4 Bagpipe Vibrato", "OSC 4 Bagpipe Blow", "OSC 5 Bagpipe Scale", "OSC 5 Bagpipe Reed", "OSC 5 Bagpipe Reed Type", "OSC 5 Bagpipe Bore Shape", "OSC 5 Bagpipe Coupling", "OSC 5 Bagpipe Bore", "OSC 5 Bagpipe Fluctuation", "OSC 5 Bagpipe Air", "OSC 5 Bagpipe Colour Mix", "OSC 5 Bagpipe Colour Freq", "OSC 5 Bagpipe Drone Level", "OSC 5 Bagpipe Drone Chord", "OSC 5 Bagpipe Drone Key", "OSC 5 Bagpipe Strike-In", "OSC 5 Bagpipe Vibrato", "OSC 5 Bagpipe Blow", "OSC 6 Bagpipe Scale", "OSC 6 Bagpipe Reed", "OSC 6 Bagpipe Reed Type", "OSC 6 Bagpipe Bore Shape", "OSC 6 Bagpipe Coupling", "OSC 6 Bagpipe Bore", "OSC 6 Bagpipe Fluctuation", "OSC 6 Bagpipe Air", "OSC 6 Bagpipe Colour Mix", "OSC 6 Bagpipe Colour Freq", "OSC 6 Bagpipe Drone Level", "OSC 6 Bagpipe Drone Chord", "OSC 6 Bagpipe Drone Key", "OSC 6 Bagpipe Strike-In", "OSC 6 Bagpipe Vibrato", "OSC 6 Bagpipe Blow", "Attack", "Decay", "Sustain", "Release", "Velocity", "Synth Drive", "Master", "Pitch EG", "P.EG Decay", "Master Tune", "Stereo Width", "Tone", "Out Gain", "DC Block Freq", "LFO 1 Rate", "LFO 2 Rate", "LFO 3 Rate", "LFO 4 Rate", "LFO 5 Rate", "LFO 6 Rate", "LFO 7 Rate", "LFO 8 Rate", "LFO 9 Rate", "LFO 10 Rate", "Env 1 Attack", "Env 1 Decay", "Env 1 Sustain", "Env 1 Release", "Env 2 Attack", "Env 2 Decay", "Env 2 Sustain", "Env 2 Release", "Env 3 Attack", "Env 3 Decay", "Env 3 Sustain", "Env 3 Release", "Env 4 Attack", "Env 4 Decay", "Env 4 Sustain", "Env 4 Release", "Env 5 Attack", "Env 5 Decay", "Env 5 Sustain", "Env 5 Release", "Env 6 Attack", "Env 6 Decay", "Env 6 Sustain", "Env 6 Release", "Env 7 Attack", "Env 7 Decay", "Env 7 Sustain", "Env 7 Release", "Env 8 Attack", "Env 8 Decay", "Env 8 Sustain", "Env 8 Release", "Env 9 Attack", "Env 9 Decay", "Env 9 Sustain", "Env 9 Release", "Env 10 Attack", "Env 10 Decay", "Env 10 Sustain", "Env 10 Release", "Sync BPM", "OSC 1 Level", "OSC 1 Pan", "OSC 1 Fine", "OSC 1 Start Phase", "OSC 1 WT Position", "OSC 1 Unison Detune", "OSC 1 Unison Blend", "OSC 1 Unison Width", "OSC 1 Warp 1 Amount", "OSC 1 Warp 2 Amount", "OSC 1 Sample Start", "OSC 1 Terrain Scale", "OSC 1 Terrain Warp", "OSC 1 Terrain Fold", "OSC 1 Unison Drift", "OSC 1 Unison Phase", "OSC 1 Filter Cutoff", "OSC 1 Filter Resonance", "OSC 1 Filter Drive", "OSC 1 Filter Key Track", "OSC 1 Filter EG Int", "OSC 1 Filter Velocity", "OSC 1 Filter EG Attack", "OSC 1 Filter EG Decay", "OSC 1 Filter EG Sustain", "OSC 1 Filter EG Release", "OSC 1 Distortion Drive", "OSC 1 Distortion Mix", "OSC 1 Wavefilter Position", "OSC 1 Wavedistortion Position", "OSC 1 Frequency", "OSC 1 Wavefilter Mix", "OSC 1 Wavefilter Range", "OSC 1 Wavefilter Warp", "OSC 1 Wavefilter Contrast", "OSC 1 Wavefilter Tilt", "OSC 1 Wavefilter Spread", "OSC 1 Resonator Decay", "OSC 1 Resonator Material", "OSC 1 Resonator Position", "OSC 1 Resonator Inharmonicity", "OSC 1 Resonator Tune", "OSC 1 Resonator Mix", "OSC 2 Level", "OSC 2 Pan", "OSC 2 Fine", "OSC 2 Start Phase", "OSC 2 WT Position", "OSC 2 Unison Detune", "OSC 2 Unison Blend", "OSC 2 Unison Width", "OSC 2 Warp 1 Amount", "OSC 2 Warp 2 Amount", "OSC 2 Sample Start", "OSC 2 Terrain Scale", "OSC 2 Terrain Warp", "OSC 2 Terrain Fold", "OSC 2 Unison Drift", "OSC 2 Unison Phase", "OSC 2 Filter Cutoff", "OSC 2 Filter Resonance", "OSC 2 Filter Drive", "OSC 2 Filter Key Track", "OSC 2 Filter EG Int", "OSC 2 Filter Velocity", "OSC 2 Filter EG Attack", "OSC 2 Filter EG Decay", "OSC 2 Filter EG Sustain", "OSC 2 Filter EG Release", "OSC 2 Distortion Drive", "OSC 2 Distortion Mix", "OSC 2 Wavefilter Position", "OSC 2 Wavedistortion Position", "OSC 2 Frequency", "OSC 2 Wavefilter Mix", "OSC 2 Wavefilter Range", "OSC 2 Wavefilter Warp", "OSC 2 Wavefilter Contrast", "OSC 2 Wavefilter Tilt", "OSC 2 Wavefilter Spread", "OSC 2 Resonator Decay", "OSC 2 Resonator Material", "OSC 2 Resonator Position", "OSC 2 Resonator Inharmonicity", "OSC 2 Resonator Tune", "OSC 2 Resonator Mix", "OSC 3 Level", "OSC 3 Pan", "OSC 3 Fine", "OSC 3 Start Phase", "OSC 3 WT Position", "OSC 3 Unison Detune", "OSC 3 Unison Blend", "OSC 3 Unison Width", "OSC 3 Warp 1 Amount", "OSC 3 Warp 2 Amount", "OSC 3 Sample Start", "OSC 3 Terrain Scale", "OSC 3 Terrain Warp", "OSC 3 Terrain Fold", "OSC 3 Unison Drift", "OSC 3 Unison Phase", "OSC 3 Filter Cutoff", "OSC 3 Filter Resonance", "OSC 3 Filter Drive", "OSC 3 Filter Key Track", "OSC 3 Filter EG Int", "OSC 3 Filter Velocity", "OSC 3 Filter EG Attack", "OSC 3 Filter EG Decay", "OSC 3 Filter EG Sustain", "OSC 3 Filter EG Release", "OSC 3 Distortion Drive", "OSC 3 Distortion Mix", "OSC 3 Wavefilter Position", "OSC 3 Wavedistortion Position", "OSC 3 Frequency", "OSC 3 Wavefilter Mix", "OSC 3 Wavefilter Range", "OSC 3 Wavefilter Warp", "OSC 3 Wavefilter Contrast", "OSC 3 Wavefilter Tilt", "OSC 3 Wavefilter Spread", "OSC 3 Resonator Decay", "OSC 3 Resonator Material", "OSC 3 Resonator Position", "OSC 3 Resonator Inharmonicity", "OSC 3 Resonator Tune", "OSC 3 Resonator Mix", "OSC 4 Level", "OSC 4 Pan", "OSC 4 Fine", "OSC 4 Start Phase", "OSC 4 WT Position", "OSC 4 Unison Detune", "OSC 4 Unison Blend", "OSC 4 Unison Width", "OSC 4 Warp 1 Amount", "OSC 4 Warp 2 Amount", "OSC 4 Sample Start", "OSC 4 Terrain Scale", "OSC 4 Terrain Warp", "OSC 4 Terrain Fold", "OSC 4 Unison Drift", "OSC 4 Unison Phase", "OSC 4 Filter Cutoff", "OSC 4 Filter Resonance", "OSC 4 Filter Drive", "OSC 4 Filter Key Track", "OSC 4 Filter EG Int", "OSC 4 Filter Velocity", "OSC 4 Filter EG Attack", "OSC 4 Filter EG Decay", "OSC 4 Filter EG Sustain", "OSC 4 Filter EG Release", "OSC 4 Distortion Drive", "OSC 4 Distortion Mix", "OSC 4 Wavefilter Position", "OSC 4 Wavedistortion Position", "OSC 4 Frequency", "OSC 4 Wavefilter Mix", "OSC 4 Wavefilter Range", "OSC 4 Wavefilter Warp", "OSC 4 Wavefilter Contrast", "OSC 4 Wavefilter Tilt", "OSC 4 Wavefilter Spread", "OSC 4 Resonator Decay", "OSC 4 Resonator Material", "OSC 4 Resonator Position", "OSC 4 Resonator Inharmonicity", "OSC 4 Resonator Tune", "OSC 4 Resonator Mix", "OSC 5 Level", "OSC 5 Pan", "OSC 5 Fine", "OSC 5 Start Phase", "OSC 5 WT Position", "OSC 5 Unison Detune", "OSC 5 Unison Blend", "OSC 5 Unison Width", "OSC 5 Warp 1 Amount", "OSC 5 Warp 2 Amount", "OSC 5 Sample Start", "OSC 5 Terrain Scale", "OSC 5 Terrain Warp", "OSC 5 Terrain Fold", "OSC 5 Unison Drift", "OSC 5 Unison Phase", "OSC 5 Filter Cutoff", "OSC 5 Filter Resonance", "OSC 5 Filter Drive", "OSC 5 Filter Key Track", "OSC 5 Filter EG Int", "OSC 5 Filter Velocity", "OSC 5 Filter EG Attack", "OSC 5 Filter EG Decay", "OSC 5 Filter EG Sustain", "OSC 5 Filter EG Release", "OSC 5 Distortion Drive", "OSC 5 Distortion Mix", "OSC 5 Wavefilter Position", "OSC 5 Wavedistortion Position", "OSC 5 Frequency", "OSC 5 Wavefilter Mix", "OSC 5 Wavefilter Range", "OSC 5 Wavefilter Warp", "OSC 5 Wavefilter Contrast", "OSC 5 Wavefilter Tilt", "OSC 5 Wavefilter Spread", "OSC 5 Resonator Decay", "OSC 5 Resonator Material", "OSC 5 Resonator Position", "OSC 5 Resonator Inharmonicity", "OSC 5 Resonator Tune", "OSC 5 Resonator Mix", "OSC 6 Level", "OSC 6 Pan", "OSC 6 Fine", "OSC 6 Start Phase", "OSC 6 WT Position", "OSC 6 Unison Detune", "OSC 6 Unison Blend", "OSC 6 Unison Width", "OSC 6 Warp 1 Amount", "OSC 6 Warp 2 Amount", "OSC 6 Sample Start", "OSC 6 Terrain Scale", "OSC 6 Terrain Warp", "OSC 6 Terrain Fold", "OSC 6 Unison Drift", "OSC 6 Unison Phase", "OSC 6 Filter Cutoff", "OSC 6 Filter Resonance", "OSC 6 Filter Drive", "OSC 6 Filter Key Track", "OSC 6 Filter EG Int", "OSC 6 Filter Velocity", "OSC 6 Filter EG Attack", "OSC 6 Filter EG Decay", "OSC 6 Filter EG Sustain", "OSC 6 Filter EG Release", "OSC 6 Distortion Drive", "OSC 6 Distortion Mix", "OSC 6 Wavefilter Position", "OSC 6 Wavedistortion Position", "OSC 6 Frequency", "OSC 6 Wavefilter Mix", "OSC 6 Wavefilter Range", "OSC 6 Wavefilter Warp", "OSC 6 Wavefilter Contrast", "OSC 6 Wavefilter Tilt", "OSC 6 Wavefilter Spread", "OSC 6 Resonator Decay", "OSC 6 Resonator Material", "OSC 6 Resonator Position", "OSC 6 Resonator Inharmonicity", "OSC 6 Resonator Tune", "OSC 6 Resonator Mix", "Freq 1 Rate", "Freq 1 Transpose", "Freq 2 Rate", "Freq 2 Transpose", "Freq 3 Rate", "Freq 3 Transpose", "Freq 4 Rate", "Freq 4 Transpose", "Freq 5 Rate", "Freq 5 Transpose", "Freq 6 Rate", "Freq 6 Transpose", "Freq 7 Rate", "Freq 7 Transpose", "Freq 8 Rate", "Freq 8 Transpose", "Freq 9 Rate", "Freq 9 Transpose", "Freq 10 Rate", "Freq 10 Transpose", "OSC 1 Physical Noise vs Mallet", "OSC 1 Physical Mallet Hardness", "OSC 1 Physical Noise Time", "OSC 1 Physical A Decay", "OSC 1 Physical A Material", "OSC 1 Physical A Hit Position", "OSC 1 Physical A Inharmonicity", "OSC 1 Physical B Decay", "OSC 1 Physical B Material", "OSC 1 Physical B Hit Position", "OSC 1 Physical B Inharmonicity", "OSC 1 Physical B Tune", "OSC 1 Physical A / B Balance", "OSC 1 Juno Saw Level", "OSC 1 Juno Pulse Level", "OSC 1 Juno Pulse Width", "OSC 1 Juno PWM Depth", "OSC 1 Juno PWM Rate", "OSC 1 Juno Sub Level", "OSC 1 Juno Noise Level", "OSC 1 Juno Drift", "OSC 1 Juno Saw Curve", "OSC 1 Juno Vibrato", "OSC 2 Physical Noise vs Mallet", "OSC 2 Physical Mallet Hardness", "OSC 2 Physical Noise Time", "OSC 2 Physical A Decay", "OSC 2 Physical A Material", "OSC 2 Physical A Hit Position", "OSC 2 Physical A Inharmonicity", "OSC 2 Physical B Decay", "OSC 2 Physical B Material", "OSC 2 Physical B Hit Position", "OSC 2 Physical B Inharmonicity", "OSC 2 Physical B Tune", "OSC 2 Physical A / B Balance", "OSC 2 Juno Saw Level", "OSC 2 Juno Pulse Level", "OSC 2 Juno Pulse Width", "OSC 2 Juno PWM Depth", "OSC 2 Juno PWM Rate", "OSC 2 Juno Sub Level", "OSC 2 Juno Noise Level", "OSC 2 Juno Drift", "OSC 2 Juno Saw Curve", "OSC 2 Juno Vibrato", "OSC 3 Physical Noise vs Mallet", "OSC 3 Physical Mallet Hardness", "OSC 3 Physical Noise Time", "OSC 3 Physical A Decay", "OSC 3 Physical A Material", "OSC 3 Physical A Hit Position", "OSC 3 Physical A Inharmonicity", "OSC 3 Physical B Decay", "OSC 3 Physical B Material", "OSC 3 Physical B Hit Position", "OSC 3 Physical B Inharmonicity", "OSC 3 Physical B Tune", "OSC 3 Physical A / B Balance", "OSC 3 Juno Saw Level", "OSC 3 Juno Pulse Level", "OSC 3 Juno Pulse Width", "OSC 3 Juno PWM Depth", "OSC 3 Juno PWM Rate", "OSC 3 Juno Sub Level", "OSC 3 Juno Noise Level", "OSC 3 Juno Drift", "OSC 3 Juno Saw Curve", "OSC 3 Juno Vibrato", "OSC 4 Physical Noise vs Mallet", "OSC 4 Physical Mallet Hardness", "OSC 4 Physical Noise Time", "OSC 4 Physical A Decay", "OSC 4 Physical A Material", "OSC 4 Physical A Hit Position", "OSC 4 Physical A Inharmonicity", "OSC 4 Physical B Decay", "OSC 4 Physical B Material", "OSC 4 Physical B Hit Position", "OSC 4 Physical B Inharmonicity", "OSC 4 Physical B Tune", "OSC 4 Physical A / B Balance", "OSC 4 Juno Saw Level", "OSC 4 Juno Pulse Level", "OSC 4 Juno Pulse Width", "OSC 4 Juno PWM Depth", "OSC 4 Juno PWM Rate", "OSC 4 Juno Sub Level", "OSC 4 Juno Noise Level", "OSC 4 Juno Drift", "OSC 4 Juno Saw Curve", "OSC 4 Juno Vibrato", "OSC 5 Physical Noise vs Mallet", "OSC 5 Physical Mallet Hardness", "OSC 5 Physical Noise Time", "OSC 5 Physical A Decay", "OSC 5 Physical A Material", "OSC 5 Physical A Hit Position", "OSC 5 Physical A Inharmonicity", "OSC 5 Physical B Decay", "OSC 5 Physical B Material", "OSC 5 Physical B Hit Position", "OSC 5 Physical B Inharmonicity", "OSC 5 Physical B Tune", "OSC 5 Physical A / B Balance", "OSC 5 Juno Saw Level", "OSC 5 Juno Pulse Level", "OSC 5 Juno Pulse Width", "OSC 5 Juno PWM Depth", "OSC 5 Juno PWM Rate", "OSC 5 Juno Sub Level", "OSC 5 Juno Noise Level", "OSC 5 Juno Drift", "OSC 5 Juno Saw Curve", "OSC 5 Juno Vibrato", "OSC 6 Physical Noise vs Mallet", "OSC 6 Physical Mallet Hardness", "OSC 6 Physical Noise Time", "OSC 6 Physical A Decay", "OSC 6 Physical A Material", "OSC 6 Physical A Hit Position", "OSC 6 Physical A Inharmonicity", "OSC 6 Physical B Decay", "OSC 6 Physical B Material", "OSC 6 Physical B Hit Position", "OSC 6 Physical B Inharmonicity", "OSC 6 Physical B Tune", "OSC 6 Physical A / B Balance", "OSC 6 Juno Saw Level", "OSC 6 Juno Pulse Level", "OSC 6 Juno Pulse Width", "OSC 6 Juno PWM Depth", "OSC 6 Juno PWM Rate", "OSC 6 Juno Sub Level", "OSC 6 Juno Noise Level", "OSC 6 Juno Drift", "OSC 6 Juno Saw Curve", "OSC 6 Juno Vibrato", "OSC 1 Kick Pitch Sweep", "OSC 1 Kick Sweep Time", "OSC 1 Kick Sweep Curve", "OSC 1 Kick Decay", "OSC 1 Kick Tone", "OSC 1 Kick Click Level", "OSC 1 Kick Click Tone", "OSC 1 Kick Noise Level", "OSC 1 Kick Drive", "OSC 1 Kick Sub Level", "OSC 1 Kick Punch", "OSC 1 Kick Tune", "OSC 1 Kick Click Decay", "OSC 1 Kick Character", "OSC 2 Kick Pitch Sweep", "OSC 2 Kick Sweep Time", "OSC 2 Kick Sweep Curve", "OSC 2 Kick Decay", "OSC 2 Kick Tone", "OSC 2 Kick Click Level", "OSC 2 Kick Click Tone", "OSC 2 Kick Noise Level", "OSC 2 Kick Drive", "OSC 2 Kick Sub Level", "OSC 2 Kick Punch", "OSC 2 Kick Tune", "OSC 2 Kick Click Decay", "OSC 2 Kick Character", "OSC 3 Kick Pitch Sweep", "OSC 3 Kick Sweep Time", "OSC 3 Kick Sweep Curve", "OSC 3 Kick Decay", "OSC 3 Kick Tone", "OSC 3 Kick Click Level", "OSC 3 Kick Click Tone", "OSC 3 Kick Noise Level", "OSC 3 Kick Drive", "OSC 3 Kick Sub Level", "OSC 3 Kick Punch", "OSC 3 Kick Tune", "OSC 3 Kick Click Decay", "OSC 3 Kick Character", "OSC 4 Kick Pitch Sweep", "OSC 4 Kick Sweep Time", "OSC 4 Kick Sweep Curve", "OSC 4 Kick Decay", "OSC 4 Kick Tone", "OSC 4 Kick Click Level", "OSC 4 Kick Click Tone", "OSC 4 Kick Noise Level", "OSC 4 Kick Drive", "OSC 4 Kick Sub Level", "OSC 4 Kick Punch", "OSC 4 Kick Tune", "OSC 4 Kick Click Decay", "OSC 4 Kick Character", "OSC 5 Kick Pitch Sweep", "OSC 5 Kick Sweep Time", "OSC 5 Kick Sweep Curve", "OSC 5 Kick Decay", "OSC 5 Kick Tone", "OSC 5 Kick Click Level", "OSC 5 Kick Click Tone", "OSC 5 Kick Noise Level", "OSC 5 Kick Drive", "OSC 5 Kick Sub Level", "OSC 5 Kick Punch", "OSC 5 Kick Tune", "OSC 5 Kick Click Decay", "OSC 5 Kick Character", "OSC 6 Kick Pitch Sweep", "OSC 6 Kick Sweep Time", "OSC 6 Kick Sweep Curve", "OSC 6 Kick Decay", "OSC 6 Kick Tone", "OSC 6 Kick Click Level", "OSC 6 Kick Click Tone", "OSC 6 Kick Noise Level", "OSC 6 Kick Drive", "OSC 6 Kick Sub Level", "OSC 6 Kick Punch", "OSC 6 Kick Tune", "OSC 6 Kick Click Decay", "OSC 6 Kick Character", "OSC 1 Terrain Orbit Center X", "OSC 1 Terrain Orbit Center Y", "OSC 1 Terrain Orbit Radius X", "OSC 1 Terrain Orbit Radius Y", "OSC 1 Terrain Orbit Rotation", "OSC 1 Terrain Orbit Ratio", "OSC 1 Terrain Orbit Phase", "OSC 1 Terrain Orbit Shape", "OSC 1 Terrain Move Rate", "OSC 1 Terrain Move Depth", "OSC 1 Terrain Morph A to B", "OSC 1 Terrain Smooth", "OSC 1 Terrain Drive", "OSC 1 Terrain Bit Depth", "OSC 1 Terrain Velocity to Radius", "OSC 2 Terrain Orbit Center X", "OSC 2 Terrain Orbit Center Y", "OSC 2 Terrain Orbit Radius X", "OSC 2 Terrain Orbit Radius Y", "OSC 2 Terrain Orbit Rotation", "OSC 2 Terrain Orbit Ratio", "OSC 2 Terrain Orbit Phase", "OSC 2 Terrain Orbit Shape", "OSC 2 Terrain Move Rate", "OSC 2 Terrain Move Depth", "OSC 2 Terrain Morph A to B", "OSC 2 Terrain Smooth", "OSC 2 Terrain Drive", "OSC 2 Terrain Bit Depth", "OSC 2 Terrain Velocity to Radius", "OSC 3 Terrain Orbit Center X", "OSC 3 Terrain Orbit Center Y", "OSC 3 Terrain Orbit Radius X", "OSC 3 Terrain Orbit Radius Y", "OSC 3 Terrain Orbit Rotation", "OSC 3 Terrain Orbit Ratio", "OSC 3 Terrain Orbit Phase", "OSC 3 Terrain Orbit Shape", "OSC 3 Terrain Move Rate", "OSC 3 Terrain Move Depth", "OSC 3 Terrain Morph A to B", "OSC 3 Terrain Smooth", "OSC 3 Terrain Drive", "OSC 3 Terrain Bit Depth", "OSC 3 Terrain Velocity to Radius", "OSC 4 Terrain Orbit Center X", "OSC 4 Terrain Orbit Center Y", "OSC 4 Terrain Orbit Radius X", "OSC 4 Terrain Orbit Radius Y", "OSC 4 Terrain Orbit Rotation", "OSC 4 Terrain Orbit Ratio", "OSC 4 Terrain Orbit Phase", "OSC 4 Terrain Orbit Shape", "OSC 4 Terrain Move Rate", "OSC 4 Terrain Move Depth", "OSC 4 Terrain Morph A to B", "OSC 4 Terrain Smooth", "OSC 4 Terrain Drive", "OSC 4 Terrain Bit Depth", "OSC 4 Terrain Velocity to Radius", "OSC 5 Terrain Orbit Center X", "OSC 5 Terrain Orbit Center Y", "OSC 5 Terrain Orbit Radius X", "OSC 5 Terrain Orbit Radius Y", "OSC 5 Terrain Orbit Rotation", "OSC 5 Terrain Orbit Ratio", "OSC 5 Terrain Orbit Phase", "OSC 5 Terrain Orbit Shape", "OSC 5 Terrain Move Rate", "OSC 5 Terrain Move Depth", "OSC 5 Terrain Morph A to B", "OSC 5 Terrain Smooth", "OSC 5 Terrain Drive", "OSC 5 Terrain Bit Depth", "OSC 5 Terrain Velocity to Radius", "OSC 6 Terrain Orbit Center X", "OSC 6 Terrain Orbit Center Y", "OSC 6 Terrain Orbit Radius X", "OSC 6 Terrain Orbit Radius Y", "OSC 6 Terrain Orbit Rotation", "OSC 6 Terrain Orbit Ratio", "OSC 6 Terrain Orbit Phase", "OSC 6 Terrain Orbit Shape", "OSC 6 Terrain Move Rate", "OSC 6 Terrain Move Depth", "OSC 6 Terrain Morph A to B", "OSC 6 Terrain Smooth", "OSC 6 Terrain Drive", "OSC 6 Terrain Bit Depth", "OSC 6 Terrain Velocity to Radius", "OSC 1 Waveguide Decay", "OSC 1 Waveguide Tone", "OSC 1 Waveguide Excite", "OSC 1 Waveguide Position", "OSC 1 Waveguide Noise", "OSC 1 Waveguide Nonlinear", "OSC 1 Waveguide Stretch", "OSC 1 Waveguide Attack", "OSC 1 Waveguide Snare", "OSC 1 Waveguide Body", "OSC 1 Waveguide Body Tune", "OSC 1 Waveguide Velocity", "OSC 1 Waveguide Drive", "OSC 1 Waveguide Tension", "OSC 1 Waveguide Key Decay", "OSC 2 Waveguide Decay", "OSC 2 Waveguide Tone", "OSC 2 Waveguide Excite", "OSC 2 Waveguide Position", "OSC 2 Waveguide Noise", "OSC 2 Waveguide Nonlinear", "OSC 2 Waveguide Stretch", "OSC 2 Waveguide Attack", "OSC 2 Waveguide Snare", "OSC 2 Waveguide Body", "OSC 2 Waveguide Body Tune", "OSC 2 Waveguide Velocity", "OSC 2 Waveguide Drive", "OSC 2 Waveguide Tension", "OSC 2 Waveguide Key Decay", "OSC 3 Waveguide Decay", "OSC 3 Waveguide Tone", "OSC 3 Waveguide Excite", "OSC 3 Waveguide Position", "OSC 3 Waveguide Noise", "OSC 3 Waveguide Nonlinear", "OSC 3 Waveguide Stretch", "OSC 3 Waveguide Attack", "OSC 3 Waveguide Snare", "OSC 3 Waveguide Body", "OSC 3 Waveguide Body Tune", "OSC 3 Waveguide Velocity", "OSC 3 Waveguide Drive", "OSC 3 Waveguide Tension", "OSC 3 Waveguide Key Decay", "OSC 4 Waveguide Decay", "OSC 4 Waveguide Tone", "OSC 4 Waveguide Excite", "OSC 4 Waveguide Position", "OSC 4 Waveguide Noise", "OSC 4 Waveguide Nonlinear", "OSC 4 Waveguide Stretch", "OSC 4 Waveguide Attack", "OSC 4 Waveguide Snare", "OSC 4 Waveguide Body", "OSC 4 Waveguide Body Tune", "OSC 4 Waveguide Velocity", "OSC 4 Waveguide Drive", "OSC 4 Waveguide Tension", "OSC 4 Waveguide Key Decay", "OSC 5 Waveguide Decay", "OSC 5 Waveguide Tone", "OSC 5 Waveguide Excite", "OSC 5 Waveguide Position", "OSC 5 Waveguide Noise", "OSC 5 Waveguide Nonlinear", "OSC 5 Waveguide Stretch", "OSC 5 Waveguide Attack", "OSC 5 Waveguide Snare", "OSC 5 Waveguide Body", "OSC 5 Waveguide Body Tune", "OSC 5 Waveguide Velocity", "OSC 5 Waveguide Drive", "OSC 5 Waveguide Tension", "OSC 5 Waveguide Key Decay", "OSC 6 Waveguide Decay", "OSC 6 Waveguide Tone", "OSC 6 Waveguide Excite", "OSC 6 Waveguide Position", "OSC 6 Waveguide Noise", "OSC 6 Waveguide Nonlinear", "OSC 6 Waveguide Stretch", "OSC 6 Waveguide Attack", "OSC 6 Waveguide Snare", "OSC 6 Waveguide Body", "OSC 6 Waveguide Body Tune", "OSC 6 Waveguide Velocity", "OSC 6 Waveguide Drive", "OSC 6 Waveguide Tension", "OSC 6 Waveguide Key Decay", "OSC 1 JP Pulse Width", "OSC 1 JP PWM Depth", "OSC 1 JP PWM Rate", "OSC 1 JP Super Saw Detune", "OSC 1 JP Super Saw Mix", "OSC 1 JP Stereo Width", "OSC 1 JP Feedback", "OSC 1 JP Feedback Color", "OSC 1 JP Tri Mod Depth", "OSC 1 JP Tri Mod Ratio", "OSC 1 JP Spectrum Tilt", "OSC 1 JP Spectrum Peak", "OSC 1 JP Noise Mix", "OSC 1 JP Drive", "OSC 1 JP Sub Oscillator", "OSC 2 JP Pulse Width", "OSC 2 JP PWM Depth", "OSC 2 JP PWM Rate", "OSC 2 JP Super Saw Detune", "OSC 2 JP Super Saw Mix", "OSC 2 JP Stereo Width", "OSC 2 JP Feedback", "OSC 2 JP Feedback Color", "OSC 2 JP Tri Mod Depth", "OSC 2 JP Tri Mod Ratio", "OSC 2 JP Spectrum Tilt", "OSC 2 JP Spectrum Peak", "OSC 2 JP Noise Mix", "OSC 2 JP Drive", "OSC 2 JP Sub Oscillator", "OSC 3 JP Pulse Width", "OSC 3 JP PWM Depth", "OSC 3 JP PWM Rate", "OSC 3 JP Super Saw Detune", "OSC 3 JP Super Saw Mix", "OSC 3 JP Stereo Width", "OSC 3 JP Feedback", "OSC 3 JP Feedback Color", "OSC 3 JP Tri Mod Depth", "OSC 3 JP Tri Mod Ratio", "OSC 3 JP Spectrum Tilt", "OSC 3 JP Spectrum Peak", "OSC 3 JP Noise Mix", "OSC 3 JP Drive", "OSC 3 JP Sub Oscillator", "OSC 4 JP Pulse Width", "OSC 4 JP PWM Depth", "OSC 4 JP PWM Rate", "OSC 4 JP Super Saw Detune", "OSC 4 JP Super Saw Mix", "OSC 4 JP Stereo Width", "OSC 4 JP Feedback", "OSC 4 JP Feedback Color", "OSC 4 JP Tri Mod Depth", "OSC 4 JP Tri Mod Ratio", "OSC 4 JP Spectrum Tilt", "OSC 4 JP Spectrum Peak", "OSC 4 JP Noise Mix", "OSC 4 JP Drive", "OSC 4 JP Sub Oscillator", "OSC 5 JP Pulse Width", "OSC 5 JP PWM Depth", "OSC 5 JP PWM Rate", "OSC 5 JP Super Saw Detune", "OSC 5 JP Super Saw Mix", "OSC 5 JP Stereo Width", "OSC 5 JP Feedback", "OSC 5 JP Feedback Color", "OSC 5 JP Tri Mod Depth", "OSC 5 JP Tri Mod Ratio", "OSC 5 JP Spectrum Tilt", "OSC 5 JP Spectrum Peak", "OSC 5 JP Noise Mix", "OSC 5 JP Drive", "OSC 5 JP Sub Oscillator", "OSC 6 JP Pulse Width", "OSC 6 JP PWM Depth", "OSC 6 JP PWM Rate", "OSC 6 JP Super Saw Detune", "OSC 6 JP Super Saw Mix", "OSC 6 JP Stereo Width", "OSC 6 JP Feedback", "OSC 6 JP Feedback Color", "OSC 6 JP Tri Mod Depth", "OSC 6 JP Tri Mod Ratio", "OSC 6 JP Spectrum Tilt", "OSC 6 JP Spectrum Peak", "OSC 6 JP Noise Mix", "OSC 6 JP Drive", "OSC 6 JP Sub Oscillator", "OSC 1 Granular Position", "OSC 1 Granular Grain Size", "OSC 1 Granular Density", "OSC 1 Granular Spray", "OSC 1 Granular Pitch Spread", "OSC 1 Granular Pan Spread", "OSC 1 Granular Window", "OSC 1 Granular Reverse", "OSC 1 Granular Scan", "OSC 1 Granular Timing", "OSC 1 Granular Drive", "OSC 1 Granular Velocity", "OSC 2 Granular Position", "OSC 2 Granular Grain Size", "OSC 2 Granular Density", "OSC 2 Granular Spray", "OSC 2 Granular Pitch Spread", "OSC 2 Granular Pan Spread", "OSC 2 Granular Window", "OSC 2 Granular Reverse", "OSC 2 Granular Scan", "OSC 2 Granular Timing", "OSC 2 Granular Drive", "OSC 2 Granular Velocity", "OSC 3 Granular Position", "OSC 3 Granular Grain Size", "OSC 3 Granular Density", "OSC 3 Granular Spray", "OSC 3 Granular Pitch Spread", "OSC 3 Granular Pan Spread", "OSC 3 Granular Window", "OSC 3 Granular Reverse", "OSC 3 Granular Scan", "OSC 3 Granular Timing", "OSC 3 Granular Drive", "OSC 3 Granular Velocity", "OSC 4 Granular Position", "OSC 4 Granular Grain Size", "OSC 4 Granular Density", "OSC 4 Granular Spray", "OSC 4 Granular Pitch Spread", "OSC 4 Granular Pan Spread", "OSC 4 Granular Window", "OSC 4 Granular Reverse", "OSC 4 Granular Scan", "OSC 4 Granular Timing", "OSC 4 Granular Drive", "OSC 4 Granular Velocity", "OSC 5 Granular Position", "OSC 5 Granular Grain Size", "OSC 5 Granular Density", "OSC 5 Granular Spray", "OSC 5 Granular Pitch Spread", "OSC 5 Granular Pan Spread", "OSC 5 Granular Window", "OSC 5 Granular Reverse", "OSC 5 Granular Scan", "OSC 5 Granular Timing", "OSC 5 Granular Drive", "OSC 5 Granular Velocity", "OSC 6 Granular Position", "OSC 6 Granular Grain Size", "OSC 6 Granular Density", "OSC 6 Granular Spray", "OSC 6 Granular Pitch Spread", "OSC 6 Granular Pan Spread", "OSC 6 Granular Window", "OSC 6 Granular Reverse", "OSC 6 Granular Scan", "OSC 6 Granular Timing", "OSC 6 Granular Drive", "OSC 6 Granular Velocity", "OSC 1 Additive Morph", "OSC 1 Additive Partials", "OSC 1 Additive Tilt", "OSC 1 Additive Odd / Even", "OSC 1 Additive Inharmonicity", "OSC 1 Additive Formant", "OSC 1 Additive Formant Gain", "OSC 1 Additive Shimmer", "OSC 1 Additive Shimmer Rate", "OSC 1 Additive Partial Decay", "OSC 1 Additive Drive", "OSC 1 Additive Stereo Spread", "OSC 1 Additive Velocity", "OSC 2 Additive Morph", "OSC 2 Additive Partials", "OSC 2 Additive Tilt", "OSC 2 Additive Odd / Even", "OSC 2 Additive Inharmonicity", "OSC 2 Additive Formant", "OSC 2 Additive Formant Gain", "OSC 2 Additive Shimmer", "OSC 2 Additive Shimmer Rate", "OSC 2 Additive Partial Decay", "OSC 2 Additive Drive", "OSC 2 Additive Stereo Spread", "OSC 2 Additive Velocity", "OSC 3 Additive Morph", "OSC 3 Additive Partials", "OSC 3 Additive Tilt", "OSC 3 Additive Odd / Even", "OSC 3 Additive Inharmonicity", "OSC 3 Additive Formant", "OSC 3 Additive Formant Gain", "OSC 3 Additive Shimmer", "OSC 3 Additive Shimmer Rate", "OSC 3 Additive Partial Decay", "OSC 3 Additive Drive", "OSC 3 Additive Stereo Spread", "OSC 3 Additive Velocity", "OSC 4 Additive Morph", "OSC 4 Additive Partials", "OSC 4 Additive Tilt", "OSC 4 Additive Odd / Even", "OSC 4 Additive Inharmonicity", "OSC 4 Additive Formant", "OSC 4 Additive Formant Gain", "OSC 4 Additive Shimmer", "OSC 4 Additive Shimmer Rate", "OSC 4 Additive Partial Decay", "OSC 4 Additive Drive", "OSC 4 Additive Stereo Spread", "OSC 4 Additive Velocity", "OSC 5 Additive Morph", "OSC 5 Additive Partials", "OSC 5 Additive Tilt", "OSC 5 Additive Odd / Even", "OSC 5 Additive Inharmonicity", "OSC 5 Additive Formant", "OSC 5 Additive Formant Gain", "OSC 5 Additive Shimmer", "OSC 5 Additive Shimmer Rate", "OSC 5 Additive Partial Decay", "OSC 5 Additive Drive", "OSC 5 Additive Stereo Spread", "OSC 5 Additive Velocity", "OSC 6 Additive Morph", "OSC 6 Additive Partials", "OSC 6 Additive Tilt", "OSC 6 Additive Odd / Even", "OSC 6 Additive Inharmonicity", "OSC 6 Additive Formant", "OSC 6 Additive Formant Gain", "OSC 6 Additive Shimmer", "OSC 6 Additive Shimmer Rate", "OSC 6 Additive Partial Decay", "OSC 6 Additive Drive", "OSC 6 Additive Stereo Spread", "OSC 6 Additive Velocity", "OSC 1 Drum Decay", "OSC 1 Drum Head Tone", "OSC 1 Drum Hit Position", "OSC 1 Drum Stick", "OSC 1 Drum Edge", "OSC 1 Drum Reso Head", "OSC 1 Drum Reso Tune", "OSC 1 Drum Shell", "OSC 1 Drum Shell Depth", "OSC 1 Drum Snare", "OSC 1 Drum Snare Tension", "OSC 1 Drum Sympathetic", "OSC 1 Drum Tension", "OSC 1 Drum Velocity", "OSC 1 Drum Drive", "OSC 1 Drum Size", "OSC 2 Drum Decay", "OSC 2 Drum Head Tone", "OSC 2 Drum Hit Position", "OSC 2 Drum Stick", "OSC 2 Drum Edge", "OSC 2 Drum Reso Head", "OSC 2 Drum Reso Tune", "OSC 2 Drum Shell", "OSC 2 Drum Shell Depth", "OSC 2 Drum Snare", "OSC 2 Drum Snare Tension", "OSC 2 Drum Sympathetic", "OSC 2 Drum Tension", "OSC 2 Drum Velocity", "OSC 2 Drum Drive", "OSC 2 Drum Size", "OSC 3 Drum Decay", "OSC 3 Drum Head Tone", "OSC 3 Drum Hit Position", "OSC 3 Drum Stick", "OSC 3 Drum Edge", "OSC 3 Drum Reso Head", "OSC 3 Drum Reso Tune", "OSC 3 Drum Shell", "OSC 3 Drum Shell Depth", "OSC 3 Drum Snare", "OSC 3 Drum Snare Tension", "OSC 3 Drum Sympathetic", "OSC 3 Drum Tension", "OSC 3 Drum Velocity", "OSC 3 Drum Drive", "OSC 3 Drum Size", "OSC 4 Drum Decay", "OSC 4 Drum Head Tone", "OSC 4 Drum Hit Position", "OSC 4 Drum Stick", "OSC 4 Drum Edge", "OSC 4 Drum Reso Head", "OSC 4 Drum Reso Tune", "OSC 4 Drum Shell", "OSC 4 Drum Shell Depth", "OSC 4 Drum Snare", "OSC 4 Drum Snare Tension", "OSC 4 Drum Sympathetic", "OSC 4 Drum Tension", "OSC 4 Drum Velocity", "OSC 4 Drum Drive", "OSC 4 Drum Size", "OSC 5 Drum Decay", "OSC 5 Drum Head Tone", "OSC 5 Drum Hit Position", "OSC 5 Drum Stick", "OSC 5 Drum Edge", "OSC 5 Drum Reso Head", "OSC 5 Drum Reso Tune", "OSC 5 Drum Shell", "OSC 5 Drum Shell Depth", "OSC 5 Drum Snare", "OSC 5 Drum Snare Tension", "OSC 5 Drum Sympathetic", "OSC 5 Drum Tension", "OSC 5 Drum Velocity", "OSC 5 Drum Drive", "OSC 5 Drum Size", "OSC 6 Drum Decay", "OSC 6 Drum Head Tone", "OSC 6 Drum Hit Position", "OSC 6 Drum Stick", "OSC 6 Drum Edge", "OSC 6 Drum Reso Head", "OSC 6 Drum Reso Tune", "OSC 6 Drum Shell", "OSC 6 Drum Shell Depth", "OSC 6 Drum Snare", "OSC 6 Drum Snare Tension", "OSC 6 Drum Sympathetic", "OSC 6 Drum Tension", "OSC 6 Drum Velocity", "OSC 6 Drum Drive", "OSC 6 Drum Size", "OSC 1 Spectral Position", "OSC 1 Spectral Position B", "OSC 1 Spectral Morph", "OSC 1 Spectral Scan", "OSC 1 Spectral Blur", "OSC 1 Spectral Shift", "OSC 1 Spectral Tilt", "OSC 1 Spectral Harmonics", "OSC 1 Spectral Odd Even", "OSC 1 Spectral Comb", "OSC 1 Spectral Contrast", "OSC 1 Spectral Jitter", "OSC 1 Spectral Spread", "OSC 1 Spectral Width", "OSC 1 Spectral Velocity", "OSC 2 Spectral Position", "OSC 2 Spectral Position B", "OSC 2 Spectral Morph", "OSC 2 Spectral Scan", "OSC 2 Spectral Blur", "OSC 2 Spectral Shift", "OSC 2 Spectral Tilt", "OSC 2 Spectral Harmonics", "OSC 2 Spectral Odd Even", "OSC 2 Spectral Comb", "OSC 2 Spectral Contrast", "OSC 2 Spectral Jitter", "OSC 2 Spectral Spread", "OSC 2 Spectral Width", "OSC 2 Spectral Velocity", "OSC 3 Spectral Position", "OSC 3 Spectral Position B", "OSC 3 Spectral Morph", "OSC 3 Spectral Scan", "OSC 3 Spectral Blur", "OSC 3 Spectral Shift", "OSC 3 Spectral Tilt", "OSC 3 Spectral Harmonics", "OSC 3 Spectral Odd Even", "OSC 3 Spectral Comb", "OSC 3 Spectral Contrast", "OSC 3 Spectral Jitter", "OSC 3 Spectral Spread", "OSC 3 Spectral Width", "OSC 3 Spectral Velocity", "OSC 4 Spectral Position", "OSC 4 Spectral Position B", "OSC 4 Spectral Morph", "OSC 4 Spectral Scan", "OSC 4 Spectral Blur", "OSC 4 Spectral Shift", "OSC 4 Spectral Tilt", "OSC 4 Spectral Harmonics", "OSC 4 Spectral Odd Even", "OSC 4 Spectral Comb", "OSC 4 Spectral Contrast", "OSC 4 Spectral Jitter", "OSC 4 Spectral Spread", "OSC 4 Spectral Width", "OSC 4 Spectral Velocity", "OSC 5 Spectral Position", "OSC 5 Spectral Position B", "OSC 5 Spectral Morph", "OSC 5 Spectral Scan", "OSC 5 Spectral Blur", "OSC 5 Spectral Shift", "OSC 5 Spectral Tilt", "OSC 5 Spectral Harmonics", "OSC 5 Spectral Odd Even", "OSC 5 Spectral Comb", "OSC 5 Spectral Contrast", "OSC 5 Spectral Jitter", "OSC 5 Spectral Spread", "OSC 5 Spectral Width", "OSC 5 Spectral Velocity", "OSC 6 Spectral Position", "OSC 6 Spectral Position B", "OSC 6 Spectral Morph", "OSC 6 Spectral Scan", "OSC 6 Spectral Blur", "OSC 6 Spectral Shift", "OSC 6 Spectral Tilt", "OSC 6 Spectral Harmonics", "OSC 6 Spectral Odd Even", "OSC 6 Spectral Comb", "OSC 6 Spectral Contrast", "OSC 6 Spectral Jitter", "OSC 6 Spectral Spread", "OSC 6 Spectral Width", "OSC 6 Spectral Velocity", "OSC 1 SoundFont Gain", "OSC 1 SoundFont Velocity", "OSC 1 SoundFont Attack", "OSC 1 SoundFont Decay", "OSC 1 SoundFont Sustain", "OSC 1 SoundFont Release", "OSC 1 SoundFont Stereo", "OSC 1 SoundFont Start", "OSC 1 SoundFont Drive", "OSC 2 SoundFont Gain", "OSC 2 SoundFont Velocity", "OSC 2 SoundFont Attack", "OSC 2 SoundFont Decay", "OSC 2 SoundFont Sustain", "OSC 2 SoundFont Release", "OSC 2 SoundFont Stereo", "OSC 2 SoundFont Start", "OSC 2 SoundFont Drive", "OSC 3 SoundFont Gain", "OSC 3 SoundFont Velocity", "OSC 3 SoundFont Attack", "OSC 3 SoundFont Decay", "OSC 3 SoundFont Sustain", "OSC 3 SoundFont Release", "OSC 3 SoundFont Stereo", "OSC 3 SoundFont Start", "OSC 3 SoundFont Drive", "OSC 4 SoundFont Gain", "OSC 4 SoundFont Velocity", "OSC 4 SoundFont Attack", "OSC 4 SoundFont Decay", "OSC 4 SoundFont Sustain", "OSC 4 SoundFont Release", "OSC 4 SoundFont Stereo", "OSC 4 SoundFont Start", "OSC 4 SoundFont Drive", "OSC 5 SoundFont Gain", "OSC 5 SoundFont Velocity", "OSC 5 SoundFont Attack", "OSC 5 SoundFont Decay", "OSC 5 SoundFont Sustain", "OSC 5 SoundFont Release", "OSC 5 SoundFont Stereo", "OSC 5 SoundFont Start", "OSC 5 SoundFont Drive", "OSC 6 SoundFont Gain", "OSC 6 SoundFont Velocity", "OSC 6 SoundFont Attack", "OSC 6 SoundFont Decay", "OSC 6 SoundFont Sustain", "OSC 6 SoundFont Release", "OSC 6 SoundFont Stereo", "OSC 6 SoundFont Start", "OSC 6 SoundFont Drive", "Main FX 1 Env Sustain", "Main FX 2 Env Sustain", "Main FX 3 Env Sustain", "Main FX 4 Env Sustain", "Main FX 5 Env Sustain", "Main FX 6 Env Sustain", "Main FX 7 Env Sustain", "Main FX 8 Env Sustain", "Main FX 9 Env Sustain", "Main FX 10 Env Sustain", "Bus 1 FX 1 Env Sustain", "Bus 1 FX 2 Env Sustain", "Bus 1 FX 3 Env Sustain", "Bus 1 FX 4 Env Sustain", "Bus 1 FX 5 Env Sustain", "Bus 1 FX 6 Env Sustain", "Bus 1 FX 7 Env Sustain", "Bus 1 FX 8 Env Sustain", "Bus 1 FX 9 Env Sustain", "Bus 1 FX 10 Env Sustain", "Bus 2 FX 1 Env Sustain", "Bus 2 FX 2 Env Sustain", "Bus 2 FX 3 Env Sustain", "Bus 2 FX 4 Env Sustain", "Bus 2 FX 5 Env Sustain", "Bus 2 FX 6 Env Sustain", "Bus 2 FX 7 Env Sustain", "Bus 2 FX 8 Env Sustain", "Bus 2 FX 9 Env Sustain", "Bus 2 FX 10 Env Sustain", "Main FX 1 Env Release", "Main FX 2 Env Release", "Main FX 3 Env Release", "Main FX 4 Env Release", "Main FX 5 Env Release", "Main FX 6 Env Release", "Main FX 7 Env Release", "Main FX 8 Env Release", "Main FX 9 Env Release", "Main FX 10 Env Release", "Bus 1 FX 1 Env Release", "Bus 1 FX 2 Env Release", "Bus 1 FX 3 Env Release", "Bus 1 FX 4 Env Release", "Bus 1 FX 5 Env Release", "Bus 1 FX 6 Env Release", "Bus 1 FX 7 Env Release", "Bus 1 FX 8 Env Release", "Bus 1 FX 9 Env Release", "Bus 1 FX 10 Env Release", "Bus 2 FX 1 Env Release", "Bus 2 FX 2 Env Release", "Bus 2 FX 3 Env Release", "Bus 2 FX 4 Env Release", "Bus 2 FX 5 Env Release", "Bus 2 FX 6 Env Release", "Bus 2 FX 7 Env Release", "Bus 2 FX 8 Env Release", "Bus 2 FX 9 Env Release", "Bus 2 FX 10 Env Release", "Main FX 11 Mix", "Main FX 11 P1", "Main FX 11 P2", "Main FX 11 P3", "Main FX 11 P4", "Main FX 11 P5", "Main FX 11 P6", "Main FX 12 Mix", "Main FX 12 P1", "Main FX 12 P2", "Main FX 12 P3", "Main FX 12 P4", "Main FX 12 P5", "Main FX 12 P6", "Main FX 13 Mix", "Main FX 13 P1", "Main FX 13 P2", "Main FX 13 P3", "Main FX 13 P4", "Main FX 13 P5", "Main FX 13 P6", "Main FX 14 Mix", "Main FX 14 P1", "Main FX 14 P2", "Main FX 14 P3", "Main FX 14 P4", "Main FX 14 P5", "Main FX 14 P6", "Main FX 15 Mix", "Main FX 15 P1", "Main FX 15 P2", "Main FX 15 P3", "Main FX 15 P4", "Main FX 15 P5", "Main FX 15 P6", "Main FX 16 Mix", "Main FX 16 P1", "Main FX 16 P2", "Main FX 16 P3", "Main FX 16 P4", "Main FX 16 P5", "Main FX 16 P6", "Bus 1 FX 11 Mix", "Bus 1 FX 11 P1", "Bus 1 FX 11 P2", "Bus 1 FX 11 P3", "Bus 1 FX 11 P4", "Bus 1 FX 11 P5", "Bus 1 FX 11 P6", "Bus 1 FX 12 Mix", "Bus 1 FX 12 P1", "Bus 1 FX 12 P2", "Bus 1 FX 12 P3", "Bus 1 FX 12 P4", "Bus 1 FX 12 P5", "Bus 1 FX 12 P6", "Bus 1 FX 13 Mix", "Bus 1 FX 13 P1", "Bus 1 FX 13 P2", "Bus 1 FX 13 P3", "Bus 1 FX 13 P4", "Bus 1 FX 13 P5", "Bus 1 FX 13 P6", "Bus 1 FX 14 Mix", "Bus 1 FX 14 P1", "Bus 1 FX 14 P2", "Bus 1 FX 14 P3", "Bus 1 FX 14 P4", "Bus 1 FX 14 P5", "Bus 1 FX 14 P6", "Bus 1 FX 15 Mix", "Bus 1 FX 15 P1", "Bus 1 FX 15 P2", "Bus 1 FX 15 P3", "Bus 1 FX 15 P4", "Bus 1 FX 15 P5", "Bus 1 FX 15 P6", "Bus 1 FX 16 Mix", "Bus 1 FX 16 P1", "Bus 1 FX 16 P2", "Bus 1 FX 16 P3", "Bus 1 FX 16 P4", "Bus 1 FX 16 P5", "Bus 1 FX 16 P6", "Bus 2 FX 11 Mix", "Bus 2 FX 11 P1", "Bus 2 FX 11 P2", "Bus 2 FX 11 P3", "Bus 2 FX 11 P4", "Bus 2 FX 11 P5", "Bus 2 FX 11 P6", "Bus 2 FX 12 Mix", "Bus 2 FX 12 P1", "Bus 2 FX 12 P2", "Bus 2 FX 12 P3", "Bus 2 FX 12 P4", "Bus 2 FX 12 P5", "Bus 2 FX 12 P6", "Bus 2 FX 13 Mix", "Bus 2 FX 13 P1", "Bus 2 FX 13 P2", "Bus 2 FX 13 P3", "Bus 2 FX 13 P4", "Bus 2 FX 13 P5", "Bus 2 FX 13 P6", "Bus 2 FX 14 Mix", "Bus 2 FX 14 P1", "Bus 2 FX 14 P2", "Bus 2 FX 14 P3", "Bus 2 FX 14 P4", "Bus 2 FX 14 P5", "Bus 2 FX 14 P6", "Bus 2 FX 15 Mix", "Bus 2 FX 15 P1", "Bus 2 FX 15 P2", "Bus 2 FX 15 P3", "Bus 2 FX 15 P4", "Bus 2 FX 15 P5", "Bus 2 FX 15 P6", "Bus 2 FX 16 Mix", "Bus 2 FX 16 P1", "Bus 2 FX 16 P2", "Bus 2 FX 16 P3", "Bus 2 FX 16 P4", "Bus 2 FX 16 P5", "Bus 2 FX 16 P6", "OSC 1 Bagpipe Reed Type", "OSC 1 Bagpipe Bore Shape", "OSC 1 Bagpipe Coupling", "OSC 1 Bagpipe Bore", "OSC 1 Bagpipe Fluctuation", "OSC 1 Bagpipe Air", "OSC 1 Bagpipe Colour Mix", "OSC 1 Bagpipe Colour Freq", "OSC 1 Bagpipe Drone Level", "OSC 1 Bagpipe Strike-In", "OSC 1 Bagpipe Vibrato", "OSC 1 Bagpipe Blow", "OSC 2 Bagpipe Reed Type", "OSC 2 Bagpipe Bore Shape", "OSC 2 Bagpipe Coupling", "OSC 2 Bagpipe Bore", "OSC 2 Bagpipe Fluctuation", "OSC 2 Bagpipe Air", "OSC 2 Bagpipe Colour Mix", "OSC 2 Bagpipe Colour Freq", "OSC 2 Bagpipe Drone Level", "OSC 2 Bagpipe Strike-In", "OSC 2 Bagpipe Vibrato", "OSC 2 Bagpipe Blow", "OSC 3 Bagpipe Reed Type", "OSC 3 Bagpipe Bore Shape", "OSC 3 Bagpipe Coupling", "OSC 3 Bagpipe Bore", "OSC 3 Bagpipe Fluctuation", "OSC 3 Bagpipe Air", "OSC 3 Bagpipe Colour Mix", "OSC 3 Bagpipe Colour Freq", "OSC 3 Bagpipe Drone Level", "OSC 3 Bagpipe Strike-In", "OSC 3 Bagpipe Vibrato", "OSC 3 Bagpipe Blow", "OSC 4 Bagpipe Reed Type", "OSC 4 Bagpipe Bore Shape", "OSC 4 Bagpipe Coupling", "OSC 4 Bagpipe Bore", "OSC 4 Bagpipe Fluctuation", "OSC 4 Bagpipe Air", "OSC 4 Bagpipe Colour Mix", "OSC 4 Bagpipe Colour Freq", "OSC 4 Bagpipe Drone Level", "OSC 4 Bagpipe Strike-In", "OSC 4 Bagpipe Vibrato", "OSC 4 Bagpipe Blow", "OSC 5 Bagpipe Reed Type", "OSC 5 Bagpipe Bore Shape", "OSC 5 Bagpipe Coupling", "OSC 5 Bagpipe Bore", "OSC 5 Bagpipe Fluctuation", "OSC 5 Bagpipe Air", "OSC 5 Bagpipe Colour Mix", "OSC 5 Bagpipe Colour Freq", "OSC 5 Bagpipe Drone Level", "OSC 5 Bagpipe Strike-In", "OSC 5 Bagpipe Vibrato", "OSC 5 Bagpipe Blow", "OSC 6 Bagpipe Reed Type", "OSC 6 Bagpipe Bore Shape", "OSC 6 Bagpipe Coupling", "OSC 6 Bagpipe Bore", "OSC 6 Bagpipe Fluctuation", "OSC 6 Bagpipe Air", "OSC 6 Bagpipe Colour Mix", "OSC 6 Bagpipe Colour Freq", "OSC 6 Bagpipe Drone Level", "OSC 6 Bagpipe Strike-In", "OSC 6 Bagpipe Vibrato", "OSC 6 Bagpipe Blow", "Seq 1 Rate", "Seq 1 Glide", "Seq 2 Rate", "Seq 2 Glide", "Seq 3 Rate", "Seq 3 Glide", "Seq 4 Rate", "Seq 4 Glide", "Seq 5 Rate", "Seq 5 Glide", "Seq 6 Rate", "Seq 6 Glide", "Seq 7 Rate", "Seq 7 Glide", "Seq 8 Rate", "Seq 8 Glide", "Seq 9 Rate", "Seq 9 Glide", "Seq 10 Rate", "Seq 10 Glide", "OSC 1 FX 1 Mix", "OSC 1 FX 1 P1", "OSC 1 FX 1 P2", "OSC 1 FX 1 P3", "OSC 1 FX 1 P4", "OSC 1 FX 1 P5", "OSC 1 FX 1 P6", "OSC 1 FX 1 Env Sustain", "OSC 1 FX 1 Env Release", "OSC 1 FX 2 Mix", "OSC 1 FX 2 P1", "OSC 1 FX 2 P2", "OSC 1 FX 2 P3", "OSC 1 FX 2 P4", "OSC 1 FX 2 P5", "OSC 1 FX 2 P6", "OSC 1 FX 2 Env Sustain", "OSC 1 FX 2 Env Release", "OSC 1 FX 3 Mix", "OSC 1 FX 3 P1", "OSC 1 FX 3 P2", "OSC 1 FX 3 P3", "OSC 1 FX 3 P4", "OSC 1 FX 3 P5", "OSC 1 FX 3 P6", "OSC 1 FX 3 Env Sustain", "OSC 1 FX 3 Env Release", "OSC 1 FX 4 Mix", "OSC 1 FX 4 P1", "OSC 1 FX 4 P2", "OSC 1 FX 4 P3", "OSC 1 FX 4 P4", "OSC 1 FX 4 P5", "OSC 1 FX 4 P6", "OSC 1 FX 4 Env Sustain", "OSC 1 FX 4 Env Release", "OSC 1 FX 5 Mix", "OSC 1 FX 5 P1", "OSC 1 FX 5 P2", "OSC 1 FX 5 P3", "OSC 1 FX 5 P4", "OSC 1 FX 5 P5", "OSC 1 FX 5 P6", "OSC 1 FX 5 Env Sustain", "OSC 1 FX 5 Env Release", "OSC 1 FX 6 Mix", "OSC 1 FX 6 P1", "OSC 1 FX 6 P2", "OSC 1 FX 6 P3", "OSC 1 FX 6 P4", "OSC 1 FX 6 P5", "OSC 1 FX 6 P6", "OSC 1 FX 6 Env Sustain", "OSC 1 FX 6 Env Release", "OSC 1 FX 7 Mix", "OSC 1 FX 7 P1", "OSC 1 FX 7 P2", "OSC 1 FX 7 P3", "OSC 1 FX 7 P4", "OSC 1 FX 7 P5", "OSC 1 FX 7 P6", "OSC 1 FX 7 Env Sustain", "OSC 1 FX 7 Env Release", "OSC 1 FX 8 Mix", "OSC 1 FX 8 P1", "OSC 1 FX 8 P2", "OSC 1 FX 8 P3", "OSC 1 FX 8 P4", "OSC 1 FX 8 P5", "OSC 1 FX 8 P6", "OSC 1 FX 8 Env Sustain", "OSC 1 FX 8 Env Release", "OSC 1 FX 9 Mix", "OSC 1 FX 9 P1", "OSC 1 FX 9 P2", "OSC 1 FX 9 P3", "OSC 1 FX 9 P4", "OSC 1 FX 9 P5", "OSC 1 FX 9 P6", "OSC 1 FX 9 Env Sustain", "OSC 1 FX 9 Env Release", "OSC 1 FX 10 Mix", "OSC 1 FX 10 P1", "OSC 1 FX 10 P2", "OSC 1 FX 10 P3", "OSC 1 FX 10 P4", "OSC 1 FX 10 P5", "OSC 1 FX 10 P6", "OSC 1 FX 10 Env Sustain", "OSC 1 FX 10 Env Release", "OSC 1 FX 11 Mix", "OSC 1 FX 11 P1", "OSC 1 FX 11 P2", "OSC 1 FX 11 P3", "OSC 1 FX 11 P4", "OSC 1 FX 11 P5", "OSC 1 FX 11 P6", "OSC 1 FX 11 Env Sustain", "OSC 1 FX 11 Env Release", "OSC 1 FX 12 Mix", "OSC 1 FX 12 P1", "OSC 1 FX 12 P2", "OSC 1 FX 12 P3", "OSC 1 FX 12 P4", "OSC 1 FX 12 P5", "OSC 1 FX 12 P6", "OSC 1 FX 12 Env Sustain", "OSC 1 FX 12 Env Release", "OSC 1 FX 13 Mix", "OSC 1 FX 13 P1", "OSC 1 FX 13 P2", "OSC 1 FX 13 P3", "OSC 1 FX 13 P4", "OSC 1 FX 13 P5", "OSC 1 FX 13 P6", "OSC 1 FX 13 Env Sustain", "OSC 1 FX 13 Env Release", "OSC 1 FX 14 Mix", "OSC 1 FX 14 P1", "OSC 1 FX 14 P2", "OSC 1 FX 14 P3", "OSC 1 FX 14 P4", "OSC 1 FX 14 P5", "OSC 1 FX 14 P6", "OSC 1 FX 14 Env Sustain", "OSC 1 FX 14 Env Release", "OSC 1 FX 15 Mix", "OSC 1 FX 15 P1", "OSC 1 FX 15 P2", "OSC 1 FX 15 P3", "OSC 1 FX 15 P4", "OSC 1 FX 15 P5", "OSC 1 FX 15 P6", "OSC 1 FX 15 Env Sustain", "OSC 1 FX 15 Env Release", "OSC 1 FX 16 Mix", "OSC 1 FX 16 P1", "OSC 1 FX 16 P2", "OSC 1 FX 16 P3", "OSC 1 FX 16 P4", "OSC 1 FX 16 P5", "OSC 1 FX 16 P6", "OSC 1 FX 16 Env Sustain", "OSC 1 FX 16 Env Release", "OSC 2 FX 1 Mix", "OSC 2 FX 1 P1", "OSC 2 FX 1 P2", "OSC 2 FX 1 P3", "OSC 2 FX 1 P4", "OSC 2 FX 1 P5", "OSC 2 FX 1 P6", "OSC 2 FX 1 Env Sustain", "OSC 2 FX 1 Env Release", "OSC 2 FX 2 Mix", "OSC 2 FX 2 P1", "OSC 2 FX 2 P2", "OSC 2 FX 2 P3", "OSC 2 FX 2 P4", "OSC 2 FX 2 P5", "OSC 2 FX 2 P6", "OSC 2 FX 2 Env Sustain", "OSC 2 FX 2 Env Release", "OSC 2 FX 3 Mix", "OSC 2 FX 3 P1", "OSC 2 FX 3 P2", "OSC 2 FX 3 P3", "OSC 2 FX 3 P4", "OSC 2 FX 3 P5", "OSC 2 FX 3 P6", "OSC 2 FX 3 Env Sustain", "OSC 2 FX 3 Env Release", "OSC 2 FX 4 Mix", "OSC 2 FX 4 P1", "OSC 2 FX 4 P2", "OSC 2 FX 4 P3", "OSC 2 FX 4 P4", "OSC 2 FX 4 P5", "OSC 2 FX 4 P6", "OSC 2 FX 4 Env Sustain", "OSC 2 FX 4 Env Release", "OSC 2 FX 5 Mix", "OSC 2 FX 5 P1", "OSC 2 FX 5 P2", "OSC 2 FX 5 P3", "OSC 2 FX 5 P4", "OSC 2 FX 5 P5", "OSC 2 FX 5 P6", "OSC 2 FX 5 Env Sustain", "OSC 2 FX 5 Env Release", "OSC 2 FX 6 Mix", "OSC 2 FX 6 P1", "OSC 2 FX 6 P2", "OSC 2 FX 6 P3", "OSC 2 FX 6 P4", "OSC 2 FX 6 P5", "OSC 2 FX 6 P6", "OSC 2 FX 6 Env Sustain", "OSC 2 FX 6 Env Release", "OSC 2 FX 7 Mix", "OSC 2 FX 7 P1", "OSC 2 FX 7 P2", "OSC 2 FX 7 P3", "OSC 2 FX 7 P4", "OSC 2 FX 7 P5", "OSC 2 FX 7 P6", "OSC 2 FX 7 Env Sustain", "OSC 2 FX 7 Env Release", "OSC 2 FX 8 Mix", "OSC 2 FX 8 P1", "OSC 2 FX 8 P2", "OSC 2 FX 8 P3", "OSC 2 FX 8 P4", "OSC 2 FX 8 P5", "OSC 2 FX 8 P6", "OSC 2 FX 8 Env Sustain", "OSC 2 FX 8 Env Release", "OSC 2 FX 9 Mix", "OSC 2 FX 9 P1", "OSC 2 FX 9 P2", "OSC 2 FX 9 P3", "OSC 2 FX 9 P4", "OSC 2 FX 9 P5", "OSC 2 FX 9 P6", "OSC 2 FX 9 Env Sustain", "OSC 2 FX 9 Env Release", "OSC 2 FX 10 Mix", "OSC 2 FX 10 P1", "OSC 2 FX 10 P2", "OSC 2 FX 10 P3", "OSC 2 FX 10 P4", "OSC 2 FX 10 P5", "OSC 2 FX 10 P6", "OSC 2 FX 10 Env Sustain", "OSC 2 FX 10 Env Release", "OSC 2 FX 11 Mix", "OSC 2 FX 11 P1", "OSC 2 FX 11 P2", "OSC 2 FX 11 P3", "OSC 2 FX 11 P4", "OSC 2 FX 11 P5", "OSC 2 FX 11 P6", "OSC 2 FX 11 Env Sustain", "OSC 2 FX 11 Env Release", "OSC 2 FX 12 Mix", "OSC 2 FX 12 P1", "OSC 2 FX 12 P2", "OSC 2 FX 12 P3", "OSC 2 FX 12 P4", "OSC 2 FX 12 P5", "OSC 2 FX 12 P6", "OSC 2 FX 12 Env Sustain", "OSC 2 FX 12 Env Release", "OSC 2 FX 13 Mix", "OSC 2 FX 13 P1", "OSC 2 FX 13 P2", "OSC 2 FX 13 P3", "OSC 2 FX 13 P4", "OSC 2 FX 13 P5", "OSC 2 FX 13 P6", "OSC 2 FX 13 Env Sustain", "OSC 2 FX 13 Env Release", "OSC 2 FX 14 Mix", "OSC 2 FX 14 P1", "OSC 2 FX 14 P2", "OSC 2 FX 14 P3", "OSC 2 FX 14 P4", "OSC 2 FX 14 P5", "OSC 2 FX 14 P6", "OSC 2 FX 14 Env Sustain", "OSC 2 FX 14 Env Release", "OSC 2 FX 15 Mix", "OSC 2 FX 15 P1", "OSC 2 FX 15 P2", "OSC 2 FX 15 P3", "OSC 2 FX 15 P4", "OSC 2 FX 15 P5", "OSC 2 FX 15 P6", "OSC 2 FX 15 Env Sustain", "OSC 2 FX 15 Env Release", "OSC 2 FX 16 Mix", "OSC 2 FX 16 P1", "OSC 2 FX 16 P2", "OSC 2 FX 16 P3", "OSC 2 FX 16 P4", "OSC 2 FX 16 P5", "OSC 2 FX 16 P6", "OSC 2 FX 16 Env Sustain", "OSC 2 FX 16 Env Release", "OSC 3 FX 1 Mix", "OSC 3 FX 1 P1", "OSC 3 FX 1 P2", "OSC 3 FX 1 P3", "OSC 3 FX 1 P4", "OSC 3 FX 1 P5", "OSC 3 FX 1 P6", "OSC 3 FX 1 Env Sustain", "OSC 3 FX 1 Env Release", "OSC 3 FX 2 Mix", "OSC 3 FX 2 P1", "OSC 3 FX 2 P2", "OSC 3 FX 2 P3", "OSC 3 FX 2 P4", "OSC 3 FX 2 P5", "OSC 3 FX 2 P6", "OSC 3 FX 2 Env Sustain", "OSC 3 FX 2 Env Release", "OSC 3 FX 3 Mix", "OSC 3 FX 3 P1", "OSC 3 FX 3 P2", "OSC 3 FX 3 P3", "OSC 3 FX 3 P4", "OSC 3 FX 3 P5", "OSC 3 FX 3 P6", "OSC 3 FX 3 Env Sustain", "OSC 3 FX 3 Env Release", "OSC 3 FX 4 Mix", "OSC 3 FX 4 P1", "OSC 3 FX 4 P2", "OSC 3 FX 4 P3", "OSC 3 FX 4 P4", "OSC 3 FX 4 P5", "OSC 3 FX 4 P6", "OSC 3 FX 4 Env Sustain", "OSC 3 FX 4 Env Release", "OSC 3 FX 5 Mix", "OSC 3 FX 5 P1", "OSC 3 FX 5 P2", "OSC 3 FX 5 P3", "OSC 3 FX 5 P4", "OSC 3 FX 5 P5", "OSC 3 FX 5 P6", "OSC 3 FX 5 Env Sustain", "OSC 3 FX 5 Env Release", "OSC 3 FX 6 Mix", "OSC 3 FX 6 P1", "OSC 3 FX 6 P2", "OSC 3 FX 6 P3", "OSC 3 FX 6 P4", "OSC 3 FX 6 P5", "OSC 3 FX 6 P6", "OSC 3 FX 6 Env Sustain", "OSC 3 FX 6 Env Release", "OSC 3 FX 7 Mix", "OSC 3 FX 7 P1", "OSC 3 FX 7 P2", "OSC 3 FX 7 P3", "OSC 3 FX 7 P4", "OSC 3 FX 7 P5", "OSC 3 FX 7 P6", "OSC 3 FX 7 Env Sustain", "OSC 3 FX 7 Env Release", "OSC 3 FX 8 Mix", "OSC 3 FX 8 P1", "OSC 3 FX 8 P2", "OSC 3 FX 8 P3", "OSC 3 FX 8 P4", "OSC 3 FX 8 P5", "OSC 3 FX 8 P6", "OSC 3 FX 8 Env Sustain", "OSC 3 FX 8 Env Release", "OSC 3 FX 9 Mix", "OSC 3 FX 9 P1", "OSC 3 FX 9 P2", "OSC 3 FX 9 P3", "OSC 3 FX 9 P4", "OSC 3 FX 9 P5", "OSC 3 FX 9 P6", "OSC 3 FX 9 Env Sustain", "OSC 3 FX 9 Env Release", "OSC 3 FX 10 Mix", "OSC 3 FX 10 P1", "OSC 3 FX 10 P2", "OSC 3 FX 10 P3", "OSC 3 FX 10 P4", "OSC 3 FX 10 P5", "OSC 3 FX 10 P6", "OSC 3 FX 10 Env Sustain", "OSC 3 FX 10 Env Release", "OSC 3 FX 11 Mix", "OSC 3 FX 11 P1", "OSC 3 FX 11 P2", "OSC 3 FX 11 P3", "OSC 3 FX 11 P4", "OSC 3 FX 11 P5", "OSC 3 FX 11 P6", "OSC 3 FX 11 Env Sustain", "OSC 3 FX 11 Env Release", "OSC 3 FX 12 Mix", "OSC 3 FX 12 P1", "OSC 3 FX 12 P2", "OSC 3 FX 12 P3", "OSC 3 FX 12 P4", "OSC 3 FX 12 P5", "OSC 3 FX 12 P6", "OSC 3 FX 12 Env Sustain", "OSC 3 FX 12 Env Release", "OSC 3 FX 13 Mix", "OSC 3 FX 13 P1", "OSC 3 FX 13 P2", "OSC 3 FX 13 P3", "OSC 3 FX 13 P4", "OSC 3 FX 13 P5", "OSC 3 FX 13 P6", "OSC 3 FX 13 Env Sustain", "OSC 3 FX 13 Env Release", "OSC 3 FX 14 Mix", "OSC 3 FX 14 P1", "OSC 3 FX 14 P2", "OSC 3 FX 14 P3", "OSC 3 FX 14 P4", "OSC 3 FX 14 P5", "OSC 3 FX 14 P6", "OSC 3 FX 14 Env Sustain", "OSC 3 FX 14 Env Release", "OSC 3 FX 15 Mix", "OSC 3 FX 15 P1", "OSC 3 FX 15 P2", "OSC 3 FX 15 P3", "OSC 3 FX 15 P4", "OSC 3 FX 15 P5", "OSC 3 FX 15 P6", "OSC 3 FX 15 Env Sustain", "OSC 3 FX 15 Env Release", "OSC 3 FX 16 Mix", "OSC 3 FX 16 P1", "OSC 3 FX 16 P2", "OSC 3 FX 16 P3", "OSC 3 FX 16 P4", "OSC 3 FX 16 P5", "OSC 3 FX 16 P6", "OSC 3 FX 16 Env Sustain", "OSC 3 FX 16 Env Release", "OSC 4 FX 1 Mix", "OSC 4 FX 1 P1", "OSC 4 FX 1 P2", "OSC 4 FX 1 P3", "OSC 4 FX 1 P4", "OSC 4 FX 1 P5", "OSC 4 FX 1 P6", "OSC 4 FX 1 Env Sustain", "OSC 4 FX 1 Env Release", "OSC 4 FX 2 Mix", "OSC 4 FX 2 P1", "OSC 4 FX 2 P2", "OSC 4 FX 2 P3", "OSC 4 FX 2 P4", "OSC 4 FX 2 P5", "OSC 4 FX 2 P6", "OSC 4 FX 2 Env Sustain", "OSC 4 FX 2 Env Release", "OSC 4 FX 3 Mix", "OSC 4 FX 3 P1", "OSC 4 FX 3 P2", "OSC 4 FX 3 P3", "OSC 4 FX 3 P4", "OSC 4 FX 3 P5", "OSC 4 FX 3 P6", "OSC 4 FX 3 Env Sustain", "OSC 4 FX 3 Env Release", "OSC 4 FX 4 Mix", "OSC 4 FX 4 P1", "OSC 4 FX 4 P2", "OSC 4 FX 4 P3", "OSC 4 FX 4 P4", "OSC 4 FX 4 P5", "OSC 4 FX 4 P6", "OSC 4 FX 4 Env Sustain", "OSC 4 FX 4 Env Release", "OSC 4 FX 5 Mix", "OSC 4 FX 5 P1", "OSC 4 FX 5 P2", "OSC 4 FX 5 P3", "OSC 4 FX 5 P4", "OSC 4 FX 5 P5", "OSC 4 FX 5 P6", "OSC 4 FX 5 Env Sustain", "OSC 4 FX 5 Env Release", "OSC 4 FX 6 Mix", "OSC 4 FX 6 P1", "OSC 4 FX 6 P2", "OSC 4 FX 6 P3", "OSC 4 FX 6 P4", "OSC 4 FX 6 P5", "OSC 4 FX 6 P6", "OSC 4 FX 6 Env Sustain", "OSC 4 FX 6 Env Release", "OSC 4 FX 7 Mix", "OSC 4 FX 7 P1", "OSC 4 FX 7 P2", "OSC 4 FX 7 P3", "OSC 4 FX 7 P4", "OSC 4 FX 7 P5", "OSC 4 FX 7 P6", "OSC 4 FX 7 Env Sustain", "OSC 4 FX 7 Env Release", "OSC 4 FX 8 Mix", "OSC 4 FX 8 P1", "OSC 4 FX 8 P2", "OSC 4 FX 8 P3", "OSC 4 FX 8 P4", "OSC 4 FX 8 P5", "OSC 4 FX 8 P6", "OSC 4 FX 8 Env Sustain", "OSC 4 FX 8 Env Release", "OSC 4 FX 9 Mix", "OSC 4 FX 9 P1", "OSC 4 FX 9 P2", "OSC 4 FX 9 P3", "OSC 4 FX 9 P4", "OSC 4 FX 9 P5", "OSC 4 FX 9 P6", "OSC 4 FX 9 Env Sustain", "OSC 4 FX 9 Env Release", "OSC 4 FX 10 Mix", "OSC 4 FX 10 P1", "OSC 4 FX 10 P2", "OSC 4 FX 10 P3", "OSC 4 FX 10 P4", "OSC 4 FX 10 P5", "OSC 4 FX 10 P6", "OSC 4 FX 10 Env Sustain", "OSC 4 FX 10 Env Release", "OSC 4 FX 11 Mix", "OSC 4 FX 11 P1", "OSC 4 FX 11 P2", "OSC 4 FX 11 P3", "OSC 4 FX 11 P4", "OSC 4 FX 11 P5", "OSC 4 FX 11 P6", "OSC 4 FX 11 Env Sustain", "OSC 4 FX 11 Env Release", "OSC 4 FX 12 Mix", "OSC 4 FX 12 P1", "OSC 4 FX 12 P2", "OSC 4 FX 12 P3", "OSC 4 FX 12 P4", "OSC 4 FX 12 P5", "OSC 4 FX 12 P6", "OSC 4 FX 12 Env Sustain", "OSC 4 FX 12 Env Release", "OSC 4 FX 13 Mix", "OSC 4 FX 13 P1", "OSC 4 FX 13 P2", "OSC 4 FX 13 P3", "OSC 4 FX 13 P4", "OSC 4 FX 13 P5", "OSC 4 FX 13 P6", "OSC 4 FX 13 Env Sustain", "OSC 4 FX 13 Env Release", "OSC 4 FX 14 Mix", "OSC 4 FX 14 P1", "OSC 4 FX 14 P2", "OSC 4 FX 14 P3", "OSC 4 FX 14 P4", "OSC 4 FX 14 P5", "OSC 4 FX 14 P6", "OSC 4 FX 14 Env Sustain", "OSC 4 FX 14 Env Release", "OSC 4 FX 15 Mix", "OSC 4 FX 15 P1", "OSC 4 FX 15 P2", "OSC 4 FX 15 P3", "OSC 4 FX 15 P4", "OSC 4 FX 15 P5", "OSC 4 FX 15 P6", "OSC 4 FX 15 Env Sustain", "OSC 4 FX 15 Env Release", "OSC 4 FX 16 Mix", "OSC 4 FX 16 P1", "OSC 4 FX 16 P2", "OSC 4 FX 16 P3", "OSC 4 FX 16 P4", "OSC 4 FX 16 P5", "OSC 4 FX 16 P6", "OSC 4 FX 16 Env Sustain", "OSC 4 FX 16 Env Release", "OSC 5 FX 1 Mix", "OSC 5 FX 1 P1", "OSC 5 FX 1 P2", "OSC 5 FX 1 P3", "OSC 5 FX 1 P4", "OSC 5 FX 1 P5", "OSC 5 FX 1 P6", "OSC 5 FX 1 Env Sustain", "OSC 5 FX 1 Env Release", "OSC 5 FX 2 Mix", "OSC 5 FX 2 P1", "OSC 5 FX 2 P2", "OSC 5 FX 2 P3", "OSC 5 FX 2 P4", "OSC 5 FX 2 P5", "OSC 5 FX 2 P6", "OSC 5 FX 2 Env Sustain", "OSC 5 FX 2 Env Release", "OSC 5 FX 3 Mix", "OSC 5 FX 3 P1", "OSC 5 FX 3 P2", "OSC 5 FX 3 P3", "OSC 5 FX 3 P4", "OSC 5 FX 3 P5", "OSC 5 FX 3 P6", "OSC 5 FX 3 Env Sustain", "OSC 5 FX 3 Env Release", "OSC 5 FX 4 Mix", "OSC 5 FX 4 P1", "OSC 5 FX 4 P2", "OSC 5 FX 4 P3", "OSC 5 FX 4 P4", "OSC 5 FX 4 P5", "OSC 5 FX 4 P6", "OSC 5 FX 4 Env Sustain", "OSC 5 FX 4 Env Release", "OSC 5 FX 5 Mix", "OSC 5 FX 5 P1", "OSC 5 FX 5 P2", "OSC 5 FX 5 P3", "OSC 5 FX 5 P4", "OSC 5 FX 5 P5", "OSC 5 FX 5 P6", "OSC 5 FX 5 Env Sustain", "OSC 5 FX 5 Env Release", "OSC 5 FX 6 Mix", "OSC 5 FX 6 P1", "OSC 5 FX 6 P2", "OSC 5 FX 6 P3", "OSC 5 FX 6 P4", "OSC 5 FX 6 P5", "OSC 5 FX 6 P6", "OSC 5 FX 6 Env Sustain", "OSC 5 FX 6 Env Release", "OSC 5 FX 7 Mix", "OSC 5 FX 7 P1", "OSC 5 FX 7 P2", "OSC 5 FX 7 P3", "OSC 5 FX 7 P4", "OSC 5 FX 7 P5", "OSC 5 FX 7 P6", "OSC 5 FX 7 Env Sustain", "OSC 5 FX 7 Env Release", "OSC 5 FX 8 Mix", "OSC 5 FX 8 P1", "OSC 5 FX 8 P2", "OSC 5 FX 8 P3", "OSC 5 FX 8 P4", "OSC 5 FX 8 P5", "OSC 5 FX 8 P6", "OSC 5 FX 8 Env Sustain", "OSC 5 FX 8 Env Release", "OSC 5 FX 9 Mix", "OSC 5 FX 9 P1", "OSC 5 FX 9 P2", "OSC 5 FX 9 P3", "OSC 5 FX 9 P4", "OSC 5 FX 9 P5", "OSC 5 FX 9 P6", "OSC 5 FX 9 Env Sustain", "OSC 5 FX 9 Env Release", "OSC 5 FX 10 Mix", "OSC 5 FX 10 P1", "OSC 5 FX 10 P2", "OSC 5 FX 10 P3", "OSC 5 FX 10 P4", "OSC 5 FX 10 P5", "OSC 5 FX 10 P6", "OSC 5 FX 10 Env Sustain", "OSC 5 FX 10 Env Release", "OSC 5 FX 11 Mix", "OSC 5 FX 11 P1", "OSC 5 FX 11 P2", "OSC 5 FX 11 P3", "OSC 5 FX 11 P4", "OSC 5 FX 11 P5", "OSC 5 FX 11 P6", "OSC 5 FX 11 Env Sustain", "OSC 5 FX 11 Env Release", "OSC 5 FX 12 Mix", "OSC 5 FX 12 P1", "OSC 5 FX 12 P2", "OSC 5 FX 12 P3", "OSC 5 FX 12 P4", "OSC 5 FX 12 P5", "OSC 5 FX 12 P6", "OSC 5 FX 12 Env Sustain", "OSC 5 FX 12 Env Release", "OSC 5 FX 13 Mix", "OSC 5 FX 13 P1", "OSC 5 FX 13 P2", "OSC 5 FX 13 P3", "OSC 5 FX 13 P4", "OSC 5 FX 13 P5", "OSC 5 FX 13 P6", "OSC 5 FX 13 Env Sustain", "OSC 5 FX 13 Env Release", "OSC 5 FX 14 Mix", "OSC 5 FX 14 P1", "OSC 5 FX 14 P2", "OSC 5 FX 14 P3", "OSC 5 FX 14 P4", "OSC 5 FX 14 P5", "OSC 5 FX 14 P6", "OSC 5 FX 14 Env Sustain", "OSC 5 FX 14 Env Release", "OSC 5 FX 15 Mix", "OSC 5 FX 15 P1", "OSC 5 FX 15 P2", "OSC 5 FX 15 P3", "OSC 5 FX 15 P4", "OSC 5 FX 15 P5", "OSC 5 FX 15 P6", "OSC 5 FX 15 Env Sustain", "OSC 5 FX 15 Env Release", "OSC 5 FX 16 Mix", "OSC 5 FX 16 P1", "OSC 5 FX 16 P2", "OSC 5 FX 16 P3", "OSC 5 FX 16 P4", "OSC 5 FX 16 P5", "OSC 5 FX 16 P6", "OSC 5 FX 16 Env Sustain", "OSC 5 FX 16 Env Release", "OSC 6 FX 1 Mix", "OSC 6 FX 1 P1", "OSC 6 FX 1 P2", "OSC 6 FX 1 P3", "OSC 6 FX 1 P4", "OSC 6 FX 1 P5", "OSC 6 FX 1 P6", "OSC 6 FX 1 Env Sustain", "OSC 6 FX 1 Env Release", "OSC 6 FX 2 Mix", "OSC 6 FX 2 P1", "OSC 6 FX 2 P2", "OSC 6 FX 2 P3", "OSC 6 FX 2 P4", "OSC 6 FX 2 P5", "OSC 6 FX 2 P6", "OSC 6 FX 2 Env Sustain", "OSC 6 FX 2 Env Release", "OSC 6 FX 3 Mix", "OSC 6 FX 3 P1", "OSC 6 FX 3 P2", "OSC 6 FX 3 P3", "OSC 6 FX 3 P4", "OSC 6 FX 3 P5", "OSC 6 FX 3 P6", "OSC 6 FX 3 Env Sustain", "OSC 6 FX 3 Env Release", "OSC 6 FX 4 Mix", "OSC 6 FX 4 P1", "OSC 6 FX 4 P2", "OSC 6 FX 4 P3", "OSC 6 FX 4 P4", "OSC 6 FX 4 P5", "OSC 6 FX 4 P6", "OSC 6 FX 4 Env Sustain", "OSC 6 FX 4 Env Release", "OSC 6 FX 5 Mix", "OSC 6 FX 5 P1", "OSC 6 FX 5 P2", "OSC 6 FX 5 P3", "OSC 6 FX 5 P4", "OSC 6 FX 5 P5", "OSC 6 FX 5 P6", "OSC 6 FX 5 Env Sustain", "OSC 6 FX 5 Env Release", "OSC 6 FX 6 Mix", "OSC 6 FX 6 P1", "OSC 6 FX 6 P2", "OSC 6 FX 6 P3", "OSC 6 FX 6 P4", "OSC 6 FX 6 P5", "OSC 6 FX 6 P6", "OSC 6 FX 6 Env Sustain", "OSC 6 FX 6 Env Release", "OSC 6 FX 7 Mix", "OSC 6 FX 7 P1", "OSC 6 FX 7 P2", "OSC 6 FX 7 P3", "OSC 6 FX 7 P4", "OSC 6 FX 7 P5", "OSC 6 FX 7 P6", "OSC 6 FX 7 Env Sustain", "OSC 6 FX 7 Env Release", "OSC 6 FX 8 Mix", "OSC 6 FX 8 P1", "OSC 6 FX 8 P2", "OSC 6 FX 8 P3", "OSC 6 FX 8 P4", "OSC 6 FX 8 P5", "OSC 6 FX 8 P6", "OSC 6 FX 8 Env Sustain", "OSC 6 FX 8 Env Release", "OSC 6 FX 9 Mix", "OSC 6 FX 9 P1", "OSC 6 FX 9 P2", "OSC 6 FX 9 P3", "OSC 6 FX 9 P4", "OSC 6 FX 9 P5", "OSC 6 FX 9 P6", "OSC 6 FX 9 Env Sustain", "OSC 6 FX 9 Env Release", "OSC 6 FX 10 Mix", "OSC 6 FX 10 P1", "OSC 6 FX 10 P2", "OSC 6 FX 10 P3", "OSC 6 FX 10 P4", "OSC 6 FX 10 P5", "OSC 6 FX 10 P6", "OSC 6 FX 10 Env Sustain", "OSC 6 FX 10 Env Release", "OSC 6 FX 11 Mix", "OSC 6 FX 11 P1", "OSC 6 FX 11 P2", "OSC 6 FX 11 P3", "OSC 6 FX 11 P4", "OSC 6 FX 11 P5", "OSC 6 FX 11 P6", "OSC 6 FX 11 Env Sustain", "OSC 6 FX 11 Env Release", "OSC 6 FX 12 Mix", "OSC 6 FX 12 P1", "OSC 6 FX 12 P2", "OSC 6 FX 12 P3", "OSC 6 FX 12 P4", "OSC 6 FX 12 P5", "OSC 6 FX 12 P6", "OSC 6 FX 12 Env Sustain", "OSC 6 FX 12 Env Release", "OSC 6 FX 13 Mix", "OSC 6 FX 13 P1", "OSC 6 FX 13 P2", "OSC 6 FX 13 P3", "OSC 6 FX 13 P4", "OSC 6 FX 13 P5", "OSC 6 FX 13 P6", "OSC 6 FX 13 Env Sustain", "OSC 6 FX 13 Env Release", "OSC 6 FX 14 Mix", "OSC 6 FX 14 P1", "OSC 6 FX 14 P2", "OSC 6 FX 14 P3", "OSC 6 FX 14 P4", "OSC 6 FX 14 P5", "OSC 6 FX 14 P6", "OSC 6 FX 14 Env Sustain", "OSC 6 FX 14 Env Release", "OSC 6 FX 15 Mix", "OSC 6 FX 15 P1", "OSC 6 FX 15 P2", "OSC 6 FX 15 P3", "OSC 6 FX 15 P4", "OSC 6 FX 15 P5", "OSC 6 FX 15 P6", "OSC 6 FX 15 Env Sustain", "OSC 6 FX 15 Env Release", "OSC 6 FX 16 Mix", "OSC 6 FX 16 P1", "OSC 6 FX 16 P2", "OSC 6 FX 16 P3", "OSC 6 FX 16 P4", "OSC 6 FX 16 P5", "OSC 6 FX 16 P6", "OSC 6 FX 16 Env Sustain", "OSC 6 FX 16 Env Release", "Patch M1 Cable 1 Gain", "Patch M1 Cable 2 Gain", "Patch M1 Cable 3 Gain", "Patch M1 Cable 4 Gain", "Patch M2 Cable 1 Gain", "Patch M2 Cable 2 Gain", "Patch M2 Cable 3 Gain", "Patch M2 Cable 4 Gain", "Patch M3 Cable 1 Gain", "Patch M3 Cable 2 Gain", "Patch M3 Cable 3 Gain", "Patch M3 Cable 4 Gain", "Patch M4 Cable 1 Gain", "Patch M4 Cable 2 Gain", "Patch M4 Cable 3 Gain", "Patch M4 Cable 4 Gain", "Patch M5 Cable 1 Gain", "Patch M5 Cable 2 Gain", "Patch M5 Cable 3 Gain", "Patch M5 Cable 4 Gain", "Patch M6 Cable 1 Gain", "Patch M6 Cable 2 Gain", "Patch M6 Cable 3 Gain", "Patch M6 Cable 4 Gain", "Patch M7 Cable 1 Gain", "Patch M7 Cable 2 Gain", "Patch M7 Cable 3 Gain", "Patch M7 Cable 4 Gain", "Patch M8 Cable 1 Gain", "Patch M8 Cable 2 Gain", "Patch M8 Cable 3 Gain", "Patch M8 Cable 4 Gain", "Patch M9 Cable 1 Gain", "Patch M9 Cable 2 Gain", "Patch M9 Cable 3 Gain", "Patch M9 Cable 4 Gain", "Patch M10 Cable 1 Gain", "Patch M10 Cable 2 Gain", "Patch M10 Cable 3 Gain", "Patch M10 Cable 4 Gain", "Patch M11 Cable 1 Gain", "Patch M11 Cable 2 Gain", "Patch M11 Cable 3 Gain", "Patch M11 Cable 4 Gain", "Patch M12 Cable 1 Gain", "Patch M12 Cable 2 Gain", "Patch M12 Cable 3 Gain", "Patch M12 Cable 4 Gain", "Patch M13 Cable 1 Gain", "Patch M13 Cable 2 Gain", "Patch M13 Cable 3 Gain", "Patch M13 Cable 4 Gain", "Patch M14 Cable 1 Gain", "Patch M14 Cable 2 Gain", "Patch M14 Cable 3 Gain", "Patch M14 Cable 4 Gain", "Patch M15 Cable 1 Gain", "Patch M15 Cable 2 Gain", "Patch M15 Cable 3 Gain", "Patch M15 Cable 4 Gain", "Patch M16 Cable 1 Gain", "Patch M16 Cable 2 Gain", "Patch M16 Cable 3 Gain", "Patch M16 Cable 4 Gain", "Patch Out Cable 1 Gain", "Patch Out Cable 2 Gain", "Patch Out Cable 3 Gain", "Patch Out Cable 4 Gain", "Euro M1 Knob 1", "Euro M1 Knob 2", "Euro M1 Knob 3", "Euro M1 Knob 4", "Euro M1 Knob 5", "Euro M1 Knob 6", "Euro M1 Knob 7", "Euro M1 Knob 8", "Euro M1 In 1 Gain", "Euro M1 In 2 Gain", "Euro M1 In 3 Gain", "Euro M1 In 4 Gain", "Euro M2 Knob 1", "Euro M2 Knob 2", "Euro M2 Knob 3", "Euro M2 Knob 4", "Euro M2 Knob 5", "Euro M2 Knob 6", "Euro M2 Knob 7", "Euro M2 Knob 8", "Euro M2 In 1 Gain", "Euro M2 In 2 Gain", "Euro M2 In 3 Gain", "Euro M2 In 4 Gain", "Euro M3 Knob 1", "Euro M3 Knob 2", "Euro M3 Knob 3", "Euro M3 Knob 4", "Euro M3 Knob 5", "Euro M3 Knob 6", "Euro M3 Knob 7", "Euro M3 Knob 8", "Euro M3 In 1 Gain", "Euro M3 In 2 Gain", "Euro M3 In 3 Gain", "Euro M3 In 4 Gain", "Euro M4 Knob 1", "Euro M4 Knob 2", "Euro M4 Knob 3", "Euro M4 Knob 4", "Euro M4 Knob 5", "Euro M4 Knob 6", "Euro M4 Knob 7", "Euro M4 Knob 8", "Euro M4 In 1 Gain", "Euro M4 In 2 Gain", "Euro M4 In 3 Gain", "Euro M4 In 4 Gain", "Euro M5 Knob 1", "Euro M5 Knob 2", "Euro M5 Knob 3", "Euro M5 Knob 4", "Euro M5 Knob 5", "Euro M5 Knob 6", "Euro M5 Knob 7", "Euro M5 Knob 8", "Euro M5 In 1 Gain", "Euro M5 In 2 Gain", "Euro M5 In 3 Gain", "Euro M5 In 4 Gain", "Euro M6 Knob 1", "Euro M6 Knob 2", "Euro M6 Knob 3", "Euro M6 Knob 4", "Euro M6 Knob 5", "Euro M6 Knob 6", "Euro M6 Knob 7", "Euro M6 Knob 8", "Euro M6 In 1 Gain", "Euro M6 In 2 Gain", "Euro M6 In 3 Gain", "Euro M6 In 4 Gain", "Euro M7 Knob 1", "Euro M7 Knob 2", "Euro M7 Knob 3", "Euro M7 Knob 4", "Euro M7 Knob 5", "Euro M7 Knob 6", "Euro M7 Knob 7", "Euro M7 Knob 8", "Euro M7 In 1 Gain", "Euro M7 In 2 Gain", "Euro M7 In 3 Gain", "Euro M7 In 4 Gain", "Euro M8 Knob 1", "Euro M8 Knob 2", "Euro M8 Knob 3", "Euro M8 Knob 4", "Euro M8 Knob 5", "Euro M8 Knob 6", "Euro M8 Knob 7", "Euro M8 Knob 8", "Euro M8 In 1 Gain", "Euro M8 In 2 Gain", "Euro M8 In 3 Gain", "Euro M8 In 4 Gain", "Euro M9 Knob 1", "Euro M9 Knob 2", "Euro M9 Knob 3", "Euro M9 Knob 4", "Euro M9 Knob 5", "Euro M9 Knob 6", "Euro M9 Knob 7", "Euro M9 Knob 8", "Euro M9 In 1 Gain", "Euro M9 In 2 Gain", "Euro M9 In 3 Gain", "Euro M9 In 4 Gain", "Euro M10 Knob 1", "Euro M10 Knob 2", "Euro M10 Knob 3", "Euro M10 Knob 4", "Euro M10 Knob 5", "Euro M10 Knob 6", "Euro M10 Knob 7", "Euro M10 Knob 8", "Euro M10 In 1 Gain", "Euro M10 In 2 Gain", "Euro M10 In 3 Gain", "Euro M10 In 4 Gain", "Euro M11 Knob 1", "Euro M11 Knob 2", "Euro M11 Knob 3", "Euro M11 Knob 4", "Euro M11 Knob 5", "Euro M11 Knob 6", "Euro M11 Knob 7", "Euro M11 Knob 8", "Euro M11 In 1 Gain", "Euro M11 In 2 Gain", "Euro M11 In 3 Gain", "Euro M11 In 4 Gain", "Euro M12 Knob 1", "Euro M12 Knob 2", "Euro M12 Knob 3", "Euro M12 Knob 4", "Euro M12 Knob 5", "Euro M12 Knob 6", "Euro M12 Knob 7", "Euro M12 Knob 8", "Euro M12 In 1 Gain", "Euro M12 In 2 Gain", "Euro M12 In 3 Gain", "Euro M12 In 4 Gain", "Euro M13 Knob 1", "Euro M13 Knob 2", "Euro M13 Knob 3", "Euro M13 Knob 4", "Euro M13 Knob 5", "Euro M13 Knob 6", "Euro M13 Knob 7", "Euro M13 Knob 8", "Euro M13 In 1 Gain", "Euro M13 In 2 Gain", "Euro M13 In 3 Gain", "Euro M13 In 4 Gain", "Euro M14 Knob 1", "Euro M14 Knob 2", "Euro M14 Knob 3", "Euro M14 Knob 4", "Euro M14 Knob 5", "Euro M14 Knob 6", "Euro M14 Knob 7", "Euro M14 Knob 8", "Euro M14 In 1 Gain", "Euro M14 In 2 Gain", "Euro M14 In 3 Gain", "Euro M14 In 4 Gain", "Euro M15 Knob 1", "Euro M15 Knob 2", "Euro M15 Knob 3", "Euro M15 Knob 4", "Euro M15 Knob 5", "Euro M15 Knob 6", "Euro M15 Knob 7", "Euro M15 Knob 8", "Euro M15 In 1 Gain", "Euro M15 In 2 Gain", "Euro M15 In 3 Gain", "Euro M15 In 4 Gain", "Euro M16 Knob 1", "Euro M16 Knob 2", "Euro M16 Knob 3", "Euro M16 Knob 4", "Euro M16 Knob 5", "Euro M16 Knob 6", "Euro M16 Knob 7", "Euro M16 Knob 8", "Euro M16 In 1 Gain", "Euro M16 In 2 Gain", "Euro M16 In 3 Gain", "Euro M16 In 4 Gain", "Euro M17 Knob 1", "Euro M17 Knob 2", "Euro M17 Knob 3", "Euro M17 Knob 4", "Euro M17 Knob 5", "Euro M17 Knob 6", "Euro M17 Knob 7", "Euro M17 Knob 8", "Euro M17 In 1 Gain", "Euro M17 In 2 Gain", "Euro M17 In 3 Gain", "Euro M17 In 4 Gain", "Euro M18 Knob 1", "Euro M18 Knob 2", "Euro M18 Knob 3", "Euro M18 Knob 4", "Euro M18 Knob 5", "Euro M18 Knob 6", "Euro M18 Knob 7", "Euro M18 Knob 8", "Euro M18 In 1 Gain", "Euro M18 In 2 Gain", "Euro M18 In 3 Gain", "Euro M18 In 4 Gain", "Euro M19 Knob 1", "Euro M19 Knob 2", "Euro M19 Knob 3", "Euro M19 Knob 4", "Euro M19 Knob 5", "Euro M19 Knob 6", "Euro M19 Knob 7", "Euro M19 Knob 8", "Euro M19 In 1 Gain", "Euro M19 In 2 Gain", "Euro M19 In 3 Gain", "Euro M19 In 4 Gain", "Euro M20 Knob 1", "Euro M20 Knob 2", "Euro M20 Knob 3", "Euro M20 Knob 4", "Euro M20 Knob 5", "Euro M20 Knob 6", "Euro M20 Knob 7", "Euro M20 Knob 8", "Euro M20 In 1 Gain", "Euro M20 In 2 Gain", "Euro M20 In 3 Gain", "Euro M20 In 4 Gain", "Main FX 1 Low Cut", "Main FX 1 High Cut", "Main FX 1 Width", "Main FX 1 Sat", "Main FX 2 Low Cut", "Main FX 2 High Cut", "Main FX 2 Width", "Main FX 2 Sat", "Main FX 3 Low Cut", "Main FX 3 High Cut", "Main FX 3 Width", "Main FX 3 Sat", "Main FX 4 Low Cut", "Main FX 4 High Cut", "Main FX 4 Width", "Main FX 4 Sat", "Main FX 5 Low Cut", "Main FX 5 High Cut", "Main FX 5 Width", "Main FX 5 Sat", "Main FX 6 Low Cut", "Main FX 6 High Cut", "Main FX 6 Width", "Main FX 6 Sat", "Main FX 7 Low Cut", "Main FX 7 High Cut", "Main FX 7 Width", "Main FX 7 Sat", "Main FX 8 Low Cut", "Main FX 8 High Cut", "Main FX 8 Width", "Main FX 8 Sat", "Main FX 9 Low Cut", "Main FX 9 High Cut", "Main FX 9 Width", "Main FX 9 Sat", "Main FX 10 Low Cut", "Main FX 10 High Cut", "Main FX 10 Width", "Main FX 10 Sat", "Bus 1 FX 1 Low Cut", "Bus 1 FX 1 High Cut", "Bus 1 FX 1 Width", "Bus 1 FX 1 Sat", "Bus 1 FX 2 Low Cut", "Bus 1 FX 2 High Cut", "Bus 1 FX 2 Width", "Bus 1 FX 2 Sat", "Bus 1 FX 3 Low Cut", "Bus 1 FX 3 High Cut", "Bus 1 FX 3 Width", "Bus 1 FX 3 Sat", "Bus 1 FX 4 Low Cut", "Bus 1 FX 4 High Cut", "Bus 1 FX 4 Width", "Bus 1 FX 4 Sat", "Bus 1 FX 5 Low Cut", "Bus 1 FX 5 High Cut", "Bus 1 FX 5 Width", "Bus 1 FX 5 Sat", "Bus 1 FX 6 Low Cut", "Bus 1 FX 6 High Cut", "Bus 1 FX 6 Width", "Bus 1 FX 6 Sat", "Bus 1 FX 7 Low Cut", "Bus 1 FX 7 High Cut", "Bus 1 FX 7 Width", "Bus 1 FX 7 Sat", "Bus 1 FX 8 Low Cut", "Bus 1 FX 8 High Cut", "Bus 1 FX 8 Width", "Bus 1 FX 8 Sat", "Bus 1 FX 9 Low Cut", "Bus 1 FX 9 High Cut", "Bus 1 FX 9 Width", "Bus 1 FX 9 Sat", "Bus 1 FX 10 Low Cut", "Bus 1 FX 10 High Cut", "Bus 1 FX 10 Width", "Bus 1 FX 10 Sat", "Bus 2 FX 1 Low Cut", "Bus 2 FX 1 High Cut", "Bus 2 FX 1 Width", "Bus 2 FX 1 Sat", "Bus 2 FX 2 Low Cut", "Bus 2 FX 2 High Cut", "Bus 2 FX 2 Width", "Bus 2 FX 2 Sat", "Bus 2 FX 3 Low Cut", "Bus 2 FX 3 High Cut", "Bus 2 FX 3 Width", "Bus 2 FX 3 Sat", "Bus 2 FX 4 Low Cut", "Bus 2 FX 4 High Cut", "Bus 2 FX 4 Width", "Bus 2 FX 4 Sat", "Bus 2 FX 5 Low Cut", "Bus 2 FX 5 High Cut", "Bus 2 FX 5 Width", "Bus 2 FX 5 Sat", "Bus 2 FX 6 Low Cut", "Bus 2 FX 6 High Cut", "Bus 2 FX 6 Width", "Bus 2 FX 6 Sat", "Bus 2 FX 7 Low Cut", "Bus 2 FX 7 High Cut", "Bus 2 FX 7 Width", "Bus 2 FX 7 Sat", "Bus 2 FX 8 Low Cut", "Bus 2 FX 8 High Cut", "Bus 2 FX 8 Width", "Bus 2 FX 8 Sat", "Bus 2 FX 9 Low Cut", "Bus 2 FX 9 High Cut", "Bus 2 FX 9 Width", "Bus 2 FX 9 Sat", "Bus 2 FX 10 Low Cut", "Bus 2 FX 10 High Cut", "Bus 2 FX 10 Width", "Bus 2 FX 10 Sat", "Main FX 11 Low Cut", "Main FX 11 High Cut", "Main FX 11 Width", "Main FX 11 Sat", "Main FX 12 Low Cut", "Main FX 12 High Cut", "Main FX 12 Width", "Main FX 12 Sat", "Main FX 13 Low Cut", "Main FX 13 High Cut", "Main FX 13 Width", "Main FX 13 Sat", "Main FX 14 Low Cut", "Main FX 14 High Cut", "Main FX 14 Width", "Main FX 14 Sat", "Main FX 15 Low Cut", "Main FX 15 High Cut", "Main FX 15 Width", "Main FX 15 Sat", "Main FX 16 Low Cut", "Main FX 16 High Cut", "Main FX 16 Width", "Main FX 16 Sat", "Bus 1 FX 11 Low Cut", "Bus 1 FX 11 High Cut", "Bus 1 FX 11 Width", "Bus 1 FX 11 Sat", "Bus 1 FX 12 Low Cut", "Bus 1 FX 12 High Cut", "Bus 1 FX 12 Width", "Bus 1 FX 12 Sat", "Bus 1 FX 13 Low Cut", "Bus 1 FX 13 High Cut", "Bus 1 FX 13 Width", "Bus 1 FX 13 Sat", "Bus 1 FX 14 Low Cut", "Bus 1 FX 14 High Cut", "Bus 1 FX 14 Width", "Bus 1 FX 14 Sat", "Bus 1 FX 15 Low Cut", "Bus 1 FX 15 High Cut", "Bus 1 FX 15 Width", "Bus 1 FX 15 Sat", "Bus 1 FX 16 Low Cut", "Bus 1 FX 16 High Cut", "Bus 1 FX 16 Width", "Bus 1 FX 16 Sat", "Bus 2 FX 11 Low Cut", "Bus 2 FX 11 High Cut", "Bus 2 FX 11 Width", "Bus 2 FX 11 Sat", "Bus 2 FX 12 Low Cut", "Bus 2 FX 12 High Cut", "Bus 2 FX 12 Width", "Bus 2 FX 12 Sat", "Bus 2 FX 13 Low Cut", "Bus 2 FX 13 High Cut", "Bus 2 FX 13 Width", "Bus 2 FX 13 Sat", "Bus 2 FX 14 Low Cut", "Bus 2 FX 14 High Cut", "Bus 2 FX 14 Width", "Bus 2 FX 14 Sat", "Bus 2 FX 15 Low Cut", "Bus 2 FX 15 High Cut", "Bus 2 FX 15 Width", "Bus 2 FX 15 Sat", "Bus 2 FX 16 Low Cut", "Bus 2 FX 16 High Cut", "Bus 2 FX 16 Width", "Bus 2 FX 16 Sat", "OSC 1 FX 1 Low Cut", "OSC 1 FX 1 High Cut", "OSC 1 FX 1 Width", "OSC 1 FX 1 Sat", "OSC 1 FX 2 Low Cut", "OSC 1 FX 2 High Cut", "OSC 1 FX 2 Width", "OSC 1 FX 2 Sat", "OSC 1 FX 3 Low Cut", "OSC 1 FX 3 High Cut", "OSC 1 FX 3 Width", "OSC 1 FX 3 Sat", "OSC 1 FX 4 Low Cut", "OSC 1 FX 4 High Cut", "OSC 1 FX 4 Width", "OSC 1 FX 4 Sat", "OSC 1 FX 5 Low Cut", "OSC 1 FX 5 High Cut", "OSC 1 FX 5 Width", "OSC 1 FX 5 Sat", "OSC 1 FX 6 Low Cut", "OSC 1 FX 6 High Cut", "OSC 1 FX 6 Width", "OSC 1 FX 6 Sat", "OSC 1 FX 7 Low Cut", "OSC 1 FX 7 High Cut", "OSC 1 FX 7 Width", "OSC 1 FX 7 Sat", "OSC 1 FX 8 Low Cut", "OSC 1 FX 8 High Cut", "OSC 1 FX 8 Width", "OSC 1 FX 8 Sat", "OSC 1 FX 9 Low Cut", "OSC 1 FX 9 High Cut", "OSC 1 FX 9 Width", "OSC 1 FX 9 Sat", "OSC 1 FX 10 Low Cut", "OSC 1 FX 10 High Cut", "OSC 1 FX 10 Width", "OSC 1 FX 10 Sat", "OSC 1 FX 11 Low Cut", "OSC 1 FX 11 High Cut", "OSC 1 FX 11 Width", "OSC 1 FX 11 Sat", "OSC 1 FX 12 Low Cut", "OSC 1 FX 12 High Cut", "OSC 1 FX 12 Width", "OSC 1 FX 12 Sat", "OSC 1 FX 13 Low Cut", "OSC 1 FX 13 High Cut", "OSC 1 FX 13 Width", "OSC 1 FX 13 Sat", "OSC 1 FX 14 Low Cut", "OSC 1 FX 14 High Cut", "OSC 1 FX 14 Width", "OSC 1 FX 14 Sat", "OSC 1 FX 15 Low Cut", "OSC 1 FX 15 High Cut", "OSC 1 FX 15 Width", "OSC 1 FX 15 Sat", "OSC 1 FX 16 Low Cut", "OSC 1 FX 16 High Cut", "OSC 1 FX 16 Width", "OSC 1 FX 16 Sat", "OSC 2 FX 1 Low Cut", "OSC 2 FX 1 High Cut", "OSC 2 FX 1 Width", "OSC 2 FX 1 Sat", "OSC 2 FX 2 Low Cut", "OSC 2 FX 2 High Cut", "OSC 2 FX 2 Width", "OSC 2 FX 2 Sat", "OSC 2 FX 3 Low Cut", "OSC 2 FX 3 High Cut", "OSC 2 FX 3 Width", "OSC 2 FX 3 Sat", "OSC 2 FX 4 Low Cut", "OSC 2 FX 4 High Cut", "OSC 2 FX 4 Width", "OSC 2 FX 4 Sat", "OSC 2 FX 5 Low Cut", "OSC 2 FX 5 High Cut", "OSC 2 FX 5 Width", "OSC 2 FX 5 Sat", "OSC 2 FX 6 Low Cut", "OSC 2 FX 6 High Cut", "OSC 2 FX 6 Width", "OSC 2 FX 6 Sat", "OSC 2 FX 7 Low Cut", "OSC 2 FX 7 High Cut", "OSC 2 FX 7 Width", "OSC 2 FX 7 Sat", "OSC 2 FX 8 Low Cut", "OSC 2 FX 8 High Cut", "OSC 2 FX 8 Width", "OSC 2 FX 8 Sat", "OSC 2 FX 9 Low Cut", "OSC 2 FX 9 High Cut", "OSC 2 FX 9 Width", "OSC 2 FX 9 Sat", "OSC 2 FX 10 Low Cut", "OSC 2 FX 10 High Cut", "OSC 2 FX 10 Width", "OSC 2 FX 10 Sat", "OSC 2 FX 11 Low Cut", "OSC 2 FX 11 High Cut", "OSC 2 FX 11 Width", "OSC 2 FX 11 Sat", "OSC 2 FX 12 Low Cut", "OSC 2 FX 12 High Cut", "OSC 2 FX 12 Width", "OSC 2 FX 12 Sat", "OSC 2 FX 13 Low Cut", "OSC 2 FX 13 High Cut", "OSC 2 FX 13 Width", "OSC 2 FX 13 Sat", "OSC 2 FX 14 Low Cut", "OSC 2 FX 14 High Cut", "OSC 2 FX 14 Width", "OSC 2 FX 14 Sat", "OSC 2 FX 15 Low Cut", "OSC 2 FX 15 High Cut", "OSC 2 FX 15 Width", "OSC 2 FX 15 Sat", "OSC 2 FX 16 Low Cut", "OSC 2 FX 16 High Cut", "OSC 2 FX 16 Width", "OSC 2 FX 16 Sat", "OSC 3 FX 1 Low Cut", "OSC 3 FX 1 High Cut", "OSC 3 FX 1 Width", "OSC 3 FX 1 Sat", "OSC 3 FX 2 Low Cut", "OSC 3 FX 2 High Cut", "OSC 3 FX 2 Width", "OSC 3 FX 2 Sat", "OSC 3 FX 3 Low Cut", "OSC 3 FX 3 High Cut", "OSC 3 FX 3 Width", "OSC 3 FX 3 Sat", "OSC 3 FX 4 Low Cut", "OSC 3 FX 4 High Cut", "OSC 3 FX 4 Width", "OSC 3 FX 4 Sat", "OSC 3 FX 5 Low Cut", "OSC 3 FX 5 High Cut", "OSC 3 FX 5 Width", "OSC 3 FX 5 Sat", "OSC 3 FX 6 Low Cut", "OSC 3 FX 6 High Cut", "OSC 3 FX 6 Width", "OSC 3 FX 6 Sat", "OSC 3 FX 7 Low Cut", "OSC 3 FX 7 High Cut", "OSC 3 FX 7 Width", "OSC 3 FX 7 Sat", "OSC 3 FX 8 Low Cut", "OSC 3 FX 8 High Cut", "OSC 3 FX 8 Width", "OSC 3 FX 8 Sat", "OSC 3 FX 9 Low Cut", "OSC 3 FX 9 High Cut", "OSC 3 FX 9 Width", "OSC 3 FX 9 Sat", "OSC 3 FX 10 Low Cut", "OSC 3 FX 10 High Cut", "OSC 3 FX 10 Width", "OSC 3 FX 10 Sat", "OSC 3 FX 11 Low Cut", "OSC 3 FX 11 High Cut", "OSC 3 FX 11 Width", "OSC 3 FX 11 Sat", "OSC 3 FX 12 Low Cut", "OSC 3 FX 12 High Cut", "OSC 3 FX 12 Width", "OSC 3 FX 12 Sat", "OSC 3 FX 13 Low Cut", "OSC 3 FX 13 High Cut", "OSC 3 FX 13 Width", "OSC 3 FX 13 Sat", "OSC 3 FX 14 Low Cut", "OSC 3 FX 14 High Cut", "OSC 3 FX 14 Width", "OSC 3 FX 14 Sat", "OSC 3 FX 15 Low Cut", "OSC 3 FX 15 High Cut", "OSC 3 FX 15 Width", "OSC 3 FX 15 Sat", "OSC 3 FX 16 Low Cut", "OSC 3 FX 16 High Cut", "OSC 3 FX 16 Width", "OSC 3 FX 16 Sat", "OSC 4 FX 1 Low Cut", "OSC 4 FX 1 High Cut", "OSC 4 FX 1 Width", "OSC 4 FX 1 Sat", "OSC 4 FX 2 Low Cut", "OSC 4 FX 2 High Cut", "OSC 4 FX 2 Width", "OSC 4 FX 2 Sat", "OSC 4 FX 3 Low Cut", "OSC 4 FX 3 High Cut", "OSC 4 FX 3 Width", "OSC 4 FX 3 Sat", "OSC 4 FX 4 Low Cut", "OSC 4 FX 4 High Cut", "OSC 4 FX 4 Width", "OSC 4 FX 4 Sat", "OSC 4 FX 5 Low Cut", "OSC 4 FX 5 High Cut", "OSC 4 FX 5 Width", "OSC 4 FX 5 Sat", "OSC 4 FX 6 Low Cut", "OSC 4 FX 6 High Cut", "OSC 4 FX 6 Width", "OSC 4 FX 6 Sat", "OSC 4 FX 7 Low Cut", "OSC 4 FX 7 High Cut", "OSC 4 FX 7 Width", "OSC 4 FX 7 Sat", "OSC 4 FX 8 Low Cut", "OSC 4 FX 8 High Cut", "OSC 4 FX 8 Width", "OSC 4 FX 8 Sat", "OSC 4 FX 9 Low Cut", "OSC 4 FX 9 High Cut", "OSC 4 FX 9 Width", "OSC 4 FX 9 Sat", "OSC 4 FX 10 Low Cut", "OSC 4 FX 10 High Cut", "OSC 4 FX 10 Width", "OSC 4 FX 10 Sat", "OSC 4 FX 11 Low Cut", "OSC 4 FX 11 High Cut", "OSC 4 FX 11 Width", "OSC 4 FX 11 Sat", "OSC 4 FX 12 Low Cut", "OSC 4 FX 12 High Cut", "OSC 4 FX 12 Width", "OSC 4 FX 12 Sat", "OSC 4 FX 13 Low Cut", "OSC 4 FX 13 High Cut", "OSC 4 FX 13 Width", "OSC 4 FX 13 Sat", "OSC 4 FX 14 Low Cut", "OSC 4 FX 14 High Cut", "OSC 4 FX 14 Width", "OSC 4 FX 14 Sat", "OSC 4 FX 15 Low Cut", "OSC 4 FX 15 High Cut", "OSC 4 FX 15 Width", "OSC 4 FX 15 Sat", "OSC 4 FX 16 Low Cut", "OSC 4 FX 16 High Cut", "OSC 4 FX 16 Width", "OSC 4 FX 16 Sat", "OSC 5 FX 1 Low Cut", "OSC 5 FX 1 High Cut", "OSC 5 FX 1 Width", "OSC 5 FX 1 Sat", "OSC 5 FX 2 Low Cut", "OSC 5 FX 2 High Cut", "OSC 5 FX 2 Width", "OSC 5 FX 2 Sat", "OSC 5 FX 3 Low Cut", "OSC 5 FX 3 High Cut", "OSC 5 FX 3 Width", "OSC 5 FX 3 Sat", "OSC 5 FX 4 Low Cut", "OSC 5 FX 4 High Cut", "OSC 5 FX 4 Width", "OSC 5 FX 4 Sat", "OSC 5 FX 5 Low Cut", "OSC 5 FX 5 High Cut", "OSC 5 FX 5 Width", "OSC 5 FX 5 Sat", "OSC 5 FX 6 Low Cut", "OSC 5 FX 6 High Cut", "OSC 5 FX 6 Width", "OSC 5 FX 6 Sat", "OSC 5 FX 7 Low Cut", "OSC 5 FX 7 High Cut", "OSC 5 FX 7 Width", "OSC 5 FX 7 Sat", "OSC 5 FX 8 Low Cut", "OSC 5 FX 8 High Cut", "OSC 5 FX 8 Width", "OSC 5 FX 8 Sat", "OSC 5 FX 9 Low Cut", "OSC 5 FX 9 High Cut", "OSC 5 FX 9 Width", "OSC 5 FX 9 Sat", "OSC 5 FX 10 Low Cut", "OSC 5 FX 10 High Cut", "OSC 5 FX 10 Width", "OSC 5 FX 10 Sat", "OSC 5 FX 11 Low Cut", "OSC 5 FX 11 High Cut", "OSC 5 FX 11 Width", "OSC 5 FX 11 Sat", "OSC 5 FX 12 Low Cut", "OSC 5 FX 12 High Cut", "OSC 5 FX 12 Width", "OSC 5 FX 12 Sat", "OSC 5 FX 13 Low Cut", "OSC 5 FX 13 High Cut", "OSC 5 FX 13 Width", "OSC 5 FX 13 Sat", "OSC 5 FX 14 Low Cut", "OSC 5 FX 14 High Cut", "OSC 5 FX 14 Width", "OSC 5 FX 14 Sat", "OSC 5 FX 15 Low Cut", "OSC 5 FX 15 High Cut", "OSC 5 FX 15 Width", "OSC 5 FX 15 Sat", "OSC 5 FX 16 Low Cut", "OSC 5 FX 16 High Cut", "OSC 5 FX 16 Width", "OSC 5 FX 16 Sat", "OSC 6 FX 1 Low Cut", "OSC 6 FX 1 High Cut", "OSC 6 FX 1 Width", "OSC 6 FX 1 Sat", "OSC 6 FX 2 Low Cut", "OSC 6 FX 2 High Cut", "OSC 6 FX 2 Width", "OSC 6 FX 2 Sat", "OSC 6 FX 3 Low Cut", "OSC 6 FX 3 High Cut", "OSC 6 FX 3 Width", "OSC 6 FX 3 Sat", "OSC 6 FX 4 Low Cut", "OSC 6 FX 4 High Cut", "OSC 6 FX 4 Width", "OSC 6 FX 4 Sat", "OSC 6 FX 5 Low Cut", "OSC 6 FX 5 High Cut", "OSC 6 FX 5 Width", "OSC 6 FX 5 Sat", "OSC 6 FX 6 Low Cut", "OSC 6 FX 6 High Cut", "OSC 6 FX 6 Width", "OSC 6 FX 6 Sat", "OSC 6 FX 7 Low Cut", "OSC 6 FX 7 High Cut", "OSC 6 FX 7 Width", "OSC 6 FX 7 Sat", "OSC 6 FX 8 Low Cut", "OSC 6 FX 8 High Cut", "OSC 6 FX 8 Width", "OSC 6 FX 8 Sat", "OSC 6 FX 9 Low Cut", "OSC 6 FX 9 High Cut", "OSC 6 FX 9 Width", "OSC 6 FX 9 Sat", "OSC 6 FX 10 Low Cut", "OSC 6 FX 10 High Cut", "OSC 6 FX 10 Width", "OSC 6 FX 10 Sat", "OSC 6 FX 11 Low Cut", "OSC 6 FX 11 High Cut", "OSC 6 FX 11 Width", "OSC 6 FX 11 Sat", "OSC 6 FX 12 Low Cut", "OSC 6 FX 12 High Cut", "OSC 6 FX 12 Width", "OSC 6 FX 12 Sat", "OSC 6 FX 13 Low Cut", "OSC 6 FX 13 High Cut", "OSC 6 FX 13 Width", "OSC 6 FX 13 Sat", "OSC 6 FX 14 Low Cut", "OSC 6 FX 14 High Cut", "OSC 6 FX 14 Width", "OSC 6 FX 14 Sat", "OSC 6 FX 15 Low Cut", "OSC 6 FX 15 High Cut", "OSC 6 FX 15 Width", "OSC 6 FX 15 Sat", "OSC 6 FX 16 Low Cut", "OSC 6 FX 16 High Cut", "OSC 6 FX 16 Width", "OSC 6 FX 16 Sat", "Out Ceiling", "Main FX 1 Ext 1", "Main FX 1 Ext 2", "Main FX 1 Ext 3", "Main FX 1 Ext 4", "Main FX 2 Ext 1", "Main FX 2 Ext 2", "Main FX 2 Ext 3", "Main FX 2 Ext 4", "Main FX 3 Ext 1", "Main FX 3 Ext 2", "Main FX 3 Ext 3", "Main FX 3 Ext 4", "Main FX 4 Ext 1", "Main FX 4 Ext 2", "Main FX 4 Ext 3", "Main FX 4 Ext 4", "Main FX 5 Ext 1", "Main FX 5 Ext 2", "Main FX 5 Ext 3", "Main FX 5 Ext 4", "Main FX 6 Ext 1", "Main FX 6 Ext 2", "Main FX 6 Ext 3", "Main FX 6 Ext 4", "Main FX 7 Ext 1", "Main FX 7 Ext 2", "Main FX 7 Ext 3", "Main FX 7 Ext 4", "Main FX 8 Ext 1", "Main FX 8 Ext 2", "Main FX 8 Ext 3", "Main FX 8 Ext 4", "Main FX 9 Ext 1", "Main FX 9 Ext 2", "Main FX 9 Ext 3", "Main FX 9 Ext 4", "Main FX 10 Ext 1", "Main FX 10 Ext 2", "Main FX 10 Ext 3", "Main FX 10 Ext 4", "Bus 1 FX 1 Ext 1", "Bus 1 FX 1 Ext 2", "Bus 1 FX 1 Ext 3", "Bus 1 FX 1 Ext 4", "Bus 1 FX 2 Ext 1", "Bus 1 FX 2 Ext 2", "Bus 1 FX 2 Ext 3", "Bus 1 FX 2 Ext 4", "Bus 1 FX 3 Ext 1", "Bus 1 FX 3 Ext 2", "Bus 1 FX 3 Ext 3", "Bus 1 FX 3 Ext 4", "Bus 1 FX 4 Ext 1", "Bus 1 FX 4 Ext 2", "Bus 1 FX 4 Ext 3", "Bus 1 FX 4 Ext 4", "Bus 1 FX 5 Ext 1", "Bus 1 FX 5 Ext 2", "Bus 1 FX 5 Ext 3", "Bus 1 FX 5 Ext 4", "Bus 1 FX 6 Ext 1", "Bus 1 FX 6 Ext 2", "Bus 1 FX 6 Ext 3", "Bus 1 FX 6 Ext 4", "Bus 1 FX 7 Ext 1", "Bus 1 FX 7 Ext 2", "Bus 1 FX 7 Ext 3", "Bus 1 FX 7 Ext 4", "Bus 1 FX 8 Ext 1", "Bus 1 FX 8 Ext 2", "Bus 1 FX 8 Ext 3", "Bus 1 FX 8 Ext 4", "Bus 1 FX 9 Ext 1", "Bus 1 FX 9 Ext 2", "Bus 1 FX 9 Ext 3", "Bus 1 FX 9 Ext 4", "Bus 1 FX 10 Ext 1", "Bus 1 FX 10 Ext 2", "Bus 1 FX 10 Ext 3", "Bus 1 FX 10 Ext 4", "Bus 2 FX 1 Ext 1", "Bus 2 FX 1 Ext 2", "Bus 2 FX 1 Ext 3", "Bus 2 FX 1 Ext 4", "Bus 2 FX 2 Ext 1", "Bus 2 FX 2 Ext 2", "Bus 2 FX 2 Ext 3", "Bus 2 FX 2 Ext 4", "Bus 2 FX 3 Ext 1", "Bus 2 FX 3 Ext 2", "Bus 2 FX 3 Ext 3", "Bus 2 FX 3 Ext 4", "Bus 2 FX 4 Ext 1", "Bus 2 FX 4 Ext 2", "Bus 2 FX 4 Ext 3", "Bus 2 FX 4 Ext 4", "Bus 2 FX 5 Ext 1", "Bus 2 FX 5 Ext 2", "Bus 2 FX 5 Ext 3", "Bus 2 FX 5 Ext 4", "Bus 2 FX 6 Ext 1", "Bus 2 FX 6 Ext 2", "Bus 2 FX 6 Ext 3", "Bus 2 FX 6 Ext 4", "Bus 2 FX 7 Ext 1", "Bus 2 FX 7 Ext 2", "Bus 2 FX 7 Ext 3", "Bus 2 FX 7 Ext 4", "Bus 2 FX 8 Ext 1", "Bus 2 FX 8 Ext 2", "Bus 2 FX 8 Ext 3", "Bus 2 FX 8 Ext 4", "Bus 2 FX 9 Ext 1", "Bus 2 FX 9 Ext 2", "Bus 2 FX 9 Ext 3", "Bus 2 FX 9 Ext 4", "Bus 2 FX 10 Ext 1", "Bus 2 FX 10 Ext 2", "Bus 2 FX 10 Ext 3", "Bus 2 FX 10 Ext 4", "Main FX 11 Ext 1", "Main FX 11 Ext 2", "Main FX 11 Ext 3", "Main FX 11 Ext 4", "Main FX 12 Ext 1", "Main FX 12 Ext 2", "Main FX 12 Ext 3", "Main FX 12 Ext 4", "Main FX 13 Ext 1", "Main FX 13 Ext 2", "Main FX 13 Ext 3", "Main FX 13 Ext 4", "Main FX 14 Ext 1", "Main FX 14 Ext 2", "Main FX 14 Ext 3", "Main FX 14 Ext 4", "Main FX 15 Ext 1", "Main FX 15 Ext 2", "Main FX 15 Ext 3", "Main FX 15 Ext 4", "Main FX 16 Ext 1", "Main FX 16 Ext 2", "Main FX 16 Ext 3", "Main FX 16 Ext 4", "Bus 1 FX 11 Ext 1", "Bus 1 FX 11 Ext 2", "Bus 1 FX 11 Ext 3", "Bus 1 FX 11 Ext 4", "Bus 1 FX 12 Ext 1", "Bus 1 FX 12 Ext 2", "Bus 1 FX 12 Ext 3", "Bus 1 FX 12 Ext 4", "Bus 1 FX 13 Ext 1", "Bus 1 FX 13 Ext 2", "Bus 1 FX 13 Ext 3", "Bus 1 FX 13 Ext 4", "Bus 1 FX 14 Ext 1", "Bus 1 FX 14 Ext 2", "Bus 1 FX 14 Ext 3", "Bus 1 FX 14 Ext 4", "Bus 1 FX 15 Ext 1", "Bus 1 FX 15 Ext 2", "Bus 1 FX 15 Ext 3", "Bus 1 FX 15 Ext 4", "Bus 1 FX 16 Ext 1", "Bus 1 FX 16 Ext 2", "Bus 1 FX 16 Ext 3", "Bus 1 FX 16 Ext 4", "Bus 2 FX 11 Ext 1", "Bus 2 FX 11 Ext 2", "Bus 2 FX 11 Ext 3", "Bus 2 FX 11 Ext 4", "Bus 2 FX 12 Ext 1", "Bus 2 FX 12 Ext 2", "Bus 2 FX 12 Ext 3", "Bus 2 FX 12 Ext 4", "Bus 2 FX 13 Ext 1", "Bus 2 FX 13 Ext 2", "Bus 2 FX 13 Ext 3", "Bus 2 FX 13 Ext 4", "Bus 2 FX 14 Ext 1", "Bus 2 FX 14 Ext 2", "Bus 2 FX 14 Ext 3", "Bus 2 FX 14 Ext 4", "Bus 2 FX 15 Ext 1", "Bus 2 FX 15 Ext 2", "Bus 2 FX 15 Ext 3", "Bus 2 FX 15 Ext 4", "Bus 2 FX 16 Ext 1", "Bus 2 FX 16 Ext 2", "Bus 2 FX 16 Ext 3", "Bus 2 FX 16 Ext 4", "OSC 1 FX 1 Ext 1", "OSC 1 FX 1 Ext 2", "OSC 1 FX 1 Ext 3", "OSC 1 FX 1 Ext 4", "OSC 1 FX 2 Ext 1", "OSC 1 FX 2 Ext 2", "OSC 1 FX 2 Ext 3", "OSC 1 FX 2 Ext 4", "OSC 1 FX 3 Ext 1", "OSC 1 FX 3 Ext 2", "OSC 1 FX 3 Ext 3", "OSC 1 FX 3 Ext 4", "OSC 1 FX 4 Ext 1", "OSC 1 FX 4 Ext 2", "OSC 1 FX 4 Ext 3", "OSC 1 FX 4 Ext 4", "OSC 1 FX 5 Ext 1", "OSC 1 FX 5 Ext 2", "OSC 1 FX 5 Ext 3", "OSC 1 FX 5 Ext 4", "OSC 1 FX 6 Ext 1", "OSC 1 FX 6 Ext 2", "OSC 1 FX 6 Ext 3", "OSC 1 FX 6 Ext 4", "OSC 1 FX 7 Ext 1", "OSC 1 FX 7 Ext 2", "OSC 1 FX 7 Ext 3", "OSC 1 FX 7 Ext 4", "OSC 1 FX 8 Ext 1", "OSC 1 FX 8 Ext 2", "OSC 1 FX 8 Ext 3", "OSC 1 FX 8 Ext 4", "OSC 1 FX 9 Ext 1", "OSC 1 FX 9 Ext 2", "OSC 1 FX 9 Ext 3", "OSC 1 FX 9 Ext 4", "OSC 1 FX 10 Ext 1", "OSC 1 FX 10 Ext 2", "OSC 1 FX 10 Ext 3", "OSC 1 FX 10 Ext 4", "OSC 1 FX 11 Ext 1", "OSC 1 FX 11 Ext 2", "OSC 1 FX 11 Ext 3", "OSC 1 FX 11 Ext 4", "OSC 1 FX 12 Ext 1", "OSC 1 FX 12 Ext 2", "OSC 1 FX 12 Ext 3", "OSC 1 FX 12 Ext 4", "OSC 1 FX 13 Ext 1", "OSC 1 FX 13 Ext 2", "OSC 1 FX 13 Ext 3", "OSC 1 FX 13 Ext 4", "OSC 1 FX 14 Ext 1", "OSC 1 FX 14 Ext 2", "OSC 1 FX 14 Ext 3", "OSC 1 FX 14 Ext 4", "OSC 1 FX 15 Ext 1", "OSC 1 FX 15 Ext 2", "OSC 1 FX 15 Ext 3", "OSC 1 FX 15 Ext 4", "OSC 1 FX 16 Ext 1", "OSC 1 FX 16 Ext 2", "OSC 1 FX 16 Ext 3", "OSC 1 FX 16 Ext 4", "OSC 2 FX 1 Ext 1", "OSC 2 FX 1 Ext 2", "OSC 2 FX 1 Ext 3", "OSC 2 FX 1 Ext 4", "OSC 2 FX 2 Ext 1", "OSC 2 FX 2 Ext 2", "OSC 2 FX 2 Ext 3", "OSC 2 FX 2 Ext 4", "OSC 2 FX 3 Ext 1", "OSC 2 FX 3 Ext 2", "OSC 2 FX 3 Ext 3", "OSC 2 FX 3 Ext 4", "OSC 2 FX 4 Ext 1", "OSC 2 FX 4 Ext 2", "OSC 2 FX 4 Ext 3", "OSC 2 FX 4 Ext 4", "OSC 2 FX 5 Ext 1", "OSC 2 FX 5 Ext 2", "OSC 2 FX 5 Ext 3", "OSC 2 FX 5 Ext 4", "OSC 2 FX 6 Ext 1", "OSC 2 FX 6 Ext 2", "OSC 2 FX 6 Ext 3", "OSC 2 FX 6 Ext 4", "OSC 2 FX 7 Ext 1", "OSC 2 FX 7 Ext 2", "OSC 2 FX 7 Ext 3", "OSC 2 FX 7 Ext 4", "OSC 2 FX 8 Ext 1", "OSC 2 FX 8 Ext 2", "OSC 2 FX 8 Ext 3", "OSC 2 FX 8 Ext 4", "OSC 2 FX 9 Ext 1", "OSC 2 FX 9 Ext 2", "OSC 2 FX 9 Ext 3", "OSC 2 FX 9 Ext 4", "OSC 2 FX 10 Ext 1", "OSC 2 FX 10 Ext 2", "OSC 2 FX 10 Ext 3", "OSC 2 FX 10 Ext 4", "OSC 2 FX 11 Ext 1", "OSC 2 FX 11 Ext 2", "OSC 2 FX 11 Ext 3", "OSC 2 FX 11 Ext 4", "OSC 2 FX 12 Ext 1", "OSC 2 FX 12 Ext 2", "OSC 2 FX 12 Ext 3", "OSC 2 FX 12 Ext 4", "OSC 2 FX 13 Ext 1", "OSC 2 FX 13 Ext 2", "OSC 2 FX 13 Ext 3", "OSC 2 FX 13 Ext 4", "OSC 2 FX 14 Ext 1", "OSC 2 FX 14 Ext 2", "OSC 2 FX 14 Ext 3", "OSC 2 FX 14 Ext 4", "OSC 2 FX 15 Ext 1", "OSC 2 FX 15 Ext 2", "OSC 2 FX 15 Ext 3", "OSC 2 FX 15 Ext 4", "OSC 2 FX 16 Ext 1", "OSC 2 FX 16 Ext 2", "OSC 2 FX 16 Ext 3", "OSC 2 FX 16 Ext 4", "OSC 3 FX 1 Ext 1", "OSC 3 FX 1 Ext 2", "OSC 3 FX 1 Ext 3", "OSC 3 FX 1 Ext 4", "OSC 3 FX 2 Ext 1", "OSC 3 FX 2 Ext 2", "OSC 3 FX 2 Ext 3", "OSC 3 FX 2 Ext 4", "OSC 3 FX 3 Ext 1", "OSC 3 FX 3 Ext 2", "OSC 3 FX 3 Ext 3", "OSC 3 FX 3 Ext 4", "OSC 3 FX 4 Ext 1", "OSC 3 FX 4 Ext 2", "OSC 3 FX 4 Ext 3", "OSC 3 FX 4 Ext 4", "OSC 3 FX 5 Ext 1", "OSC 3 FX 5 Ext 2", "OSC 3 FX 5 Ext 3", "OSC 3 FX 5 Ext 4", "OSC 3 FX 6 Ext 1", "OSC 3 FX 6 Ext 2", "OSC 3 FX 6 Ext 3", "OSC 3 FX 6 Ext 4", "OSC 3 FX 7 Ext 1", "OSC 3 FX 7 Ext 2", "OSC 3 FX 7 Ext 3", "OSC 3 FX 7 Ext 4", "OSC 3 FX 8 Ext 1", "OSC 3 FX 8 Ext 2", "OSC 3 FX 8 Ext 3", "OSC 3 FX 8 Ext 4", "OSC 3 FX 9 Ext 1", "OSC 3 FX 9 Ext 2", "OSC 3 FX 9 Ext 3", "OSC 3 FX 9 Ext 4", "OSC 3 FX 10 Ext 1", "OSC 3 FX 10 Ext 2", "OSC 3 FX 10 Ext 3", "OSC 3 FX 10 Ext 4", "OSC 3 FX 11 Ext 1", "OSC 3 FX 11 Ext 2", "OSC 3 FX 11 Ext 3", "OSC 3 FX 11 Ext 4", "OSC 3 FX 12 Ext 1", "OSC 3 FX 12 Ext 2", "OSC 3 FX 12 Ext 3", "OSC 3 FX 12 Ext 4", "OSC 3 FX 13 Ext 1", "OSC 3 FX 13 Ext 2", "OSC 3 FX 13 Ext 3", "OSC 3 FX 13 Ext 4", "OSC 3 FX 14 Ext 1", "OSC 3 FX 14 Ext 2", "OSC 3 FX 14 Ext 3", "OSC 3 FX 14 Ext 4", "OSC 3 FX 15 Ext 1", "OSC 3 FX 15 Ext 2", "OSC 3 FX 15 Ext 3", "OSC 3 FX 15 Ext 4", "OSC 3 FX 16 Ext 1", "OSC 3 FX 16 Ext 2", "OSC 3 FX 16 Ext 3", "OSC 3 FX 16 Ext 4", "OSC 4 FX 1 Ext 1", "OSC 4 FX 1 Ext 2", "OSC 4 FX 1 Ext 3", "OSC 4 FX 1 Ext 4", "OSC 4 FX 2 Ext 1", "OSC 4 FX 2 Ext 2", "OSC 4 FX 2 Ext 3", "OSC 4 FX 2 Ext 4", "OSC 4 FX 3 Ext 1", "OSC 4 FX 3 Ext 2", "OSC 4 FX 3 Ext 3", "OSC 4 FX 3 Ext 4", "OSC 4 FX 4 Ext 1", "OSC 4 FX 4 Ext 2", "OSC 4 FX 4 Ext 3", "OSC 4 FX 4 Ext 4", "OSC 4 FX 5 Ext 1", "OSC 4 FX 5 Ext 2", "OSC 4 FX 5 Ext 3", "OSC 4 FX 5 Ext 4", "OSC 4 FX 6 Ext 1", "OSC 4 FX 6 Ext 2", "OSC 4 FX 6 Ext 3", "OSC 4 FX 6 Ext 4", "OSC 4 FX 7 Ext 1", "OSC 4 FX 7 Ext 2", "OSC 4 FX 7 Ext 3", "OSC 4 FX 7 Ext 4", "OSC 4 FX 8 Ext 1", "OSC 4 FX 8 Ext 2", "OSC 4 FX 8 Ext 3", "OSC 4 FX 8 Ext 4", "OSC 4 FX 9 Ext 1", "OSC 4 FX 9 Ext 2", "OSC 4 FX 9 Ext 3", "OSC 4 FX 9 Ext 4", "OSC 4 FX 10 Ext 1", "OSC 4 FX 10 Ext 2", "OSC 4 FX 10 Ext 3", "OSC 4 FX 10 Ext 4", "OSC 4 FX 11 Ext 1", "OSC 4 FX 11 Ext 2", "OSC 4 FX 11 Ext 3", "OSC 4 FX 11 Ext 4", "OSC 4 FX 12 Ext 1", "OSC 4 FX 12 Ext 2", "OSC 4 FX 12 Ext 3", "OSC 4 FX 12 Ext 4", "OSC 4 FX 13 Ext 1", "OSC 4 FX 13 Ext 2", "OSC 4 FX 13 Ext 3", "OSC 4 FX 13 Ext 4", "OSC 4 FX 14 Ext 1", "OSC 4 FX 14 Ext 2", "OSC 4 FX 14 Ext 3", "OSC 4 FX 14 Ext 4", "OSC 4 FX 15 Ext 1", "OSC 4 FX 15 Ext 2", "OSC 4 FX 15 Ext 3", "OSC 4 FX 15 Ext 4", "OSC 4 FX 16 Ext 1", "OSC 4 FX 16 Ext 2", "OSC 4 FX 16 Ext 3", "OSC 4 FX 16 Ext 4", "OSC 5 FX 1 Ext 1", "OSC 5 FX 1 Ext 2", "OSC 5 FX 1 Ext 3", "OSC 5 FX 1 Ext 4", "OSC 5 FX 2 Ext 1", "OSC 5 FX 2 Ext 2", "OSC 5 FX 2 Ext 3", "OSC 5 FX 2 Ext 4", "OSC 5 FX 3 Ext 1", "OSC 5 FX 3 Ext 2", "OSC 5 FX 3 Ext 3", "OSC 5 FX 3 Ext 4", "OSC 5 FX 4 Ext 1", "OSC 5 FX 4 Ext 2", "OSC 5 FX 4 Ext 3", "OSC 5 FX 4 Ext 4", "OSC 5 FX 5 Ext 1", "OSC 5 FX 5 Ext 2", "OSC 5 FX 5 Ext 3", "OSC 5 FX 5 Ext 4", "OSC 5 FX 6 Ext 1", "OSC 5 FX 6 Ext 2", "OSC 5 FX 6 Ext 3", "OSC 5 FX 6 Ext 4", "OSC 5 FX 7 Ext 1", "OSC 5 FX 7 Ext 2", "OSC 5 FX 7 Ext 3", "OSC 5 FX 7 Ext 4", "OSC 5 FX 8 Ext 1", "OSC 5 FX 8 Ext 2", "OSC 5 FX 8 Ext 3", "OSC 5 FX 8 Ext 4", "OSC 5 FX 9 Ext 1", "OSC 5 FX 9 Ext 2", "OSC 5 FX 9 Ext 3", "OSC 5 FX 9 Ext 4", "OSC 5 FX 10 Ext 1", "OSC 5 FX 10 Ext 2", "OSC 5 FX 10 Ext 3", "OSC 5 FX 10 Ext 4", "OSC 5 FX 11 Ext 1", "OSC 5 FX 11 Ext 2", "OSC 5 FX 11 Ext 3", "OSC 5 FX 11 Ext 4", "OSC 5 FX 12 Ext 1", "OSC 5 FX 12 Ext 2", "OSC 5 FX 12 Ext 3", "OSC 5 FX 12 Ext 4", "OSC 5 FX 13 Ext 1", "OSC 5 FX 13 Ext 2", "OSC 5 FX 13 Ext 3", "OSC 5 FX 13 Ext 4", "OSC 5 FX 14 Ext 1", "OSC 5 FX 14 Ext 2", "OSC 5 FX 14 Ext 3", "OSC 5 FX 14 Ext 4", "OSC 5 FX 15 Ext 1", "OSC 5 FX 15 Ext 2", "OSC 5 FX 15 Ext 3", "OSC 5 FX 15 Ext 4", "OSC 5 FX 16 Ext 1", "OSC 5 FX 16 Ext 2", "OSC 5 FX 16 Ext 3", "OSC 5 FX 16 Ext 4", "OSC 6 FX 1 Ext 1", "OSC 6 FX 1 Ext 2", "OSC 6 FX 1 Ext 3", "OSC 6 FX 1 Ext 4", "OSC 6 FX 2 Ext 1", "OSC 6 FX 2 Ext 2", "OSC 6 FX 2 Ext 3", "OSC 6 FX 2 Ext 4", "OSC 6 FX 3 Ext 1", "OSC 6 FX 3 Ext 2", "OSC 6 FX 3 Ext 3", "OSC 6 FX 3 Ext 4", "OSC 6 FX 4 Ext 1", "OSC 6 FX 4 Ext 2", "OSC 6 FX 4 Ext 3", "OSC 6 FX 4 Ext 4", "OSC 6 FX 5 Ext 1", "OSC 6 FX 5 Ext 2", "OSC 6 FX 5 Ext 3", "OSC 6 FX 5 Ext 4", "OSC 6 FX 6 Ext 1", "OSC 6 FX 6 Ext 2", "OSC 6 FX 6 Ext 3", "OSC 6 FX 6 Ext 4", "OSC 6 FX 7 Ext 1", "OSC 6 FX 7 Ext 2", "OSC 6 FX 7 Ext 3", "OSC 6 FX 7 Ext 4", "OSC 6 FX 8 Ext 1", "OSC 6 FX 8 Ext 2", "OSC 6 FX 8 Ext 3", "OSC 6 FX 8 Ext 4", "OSC 6 FX 9 Ext 1", "OSC 6 FX 9 Ext 2", "OSC 6 FX 9 Ext 3", "OSC 6 FX 9 Ext 4", "OSC 6 FX 10 Ext 1", "OSC 6 FX 10 Ext 2", "OSC 6 FX 10 Ext 3", "OSC 6 FX 10 Ext 4", "OSC 6 FX 11 Ext 1", "OSC 6 FX 11 Ext 2", "OSC 6 FX 11 Ext 3", "OSC 6 FX 11 Ext 4", "OSC 6 FX 12 Ext 1", "OSC 6 FX 12 Ext 2", "OSC 6 FX 12 Ext 3", "OSC 6 FX 12 Ext 4", "OSC 6 FX 13 Ext 1", "OSC 6 FX 13 Ext 2", "OSC 6 FX 13 Ext 3", "OSC 6 FX 13 Ext 4", "OSC 6 FX 14 Ext 1", "OSC 6 FX 14 Ext 2", "OSC 6 FX 14 Ext 3", "OSC 6 FX 14 Ext 4", "OSC 6 FX 15 Ext 1", "OSC 6 FX 15 Ext 2", "OSC 6 FX 15 Ext 3", "OSC 6 FX 15 Ext 4", "OSC 6 FX 16 Ext 1", "OSC 6 FX 16 Ext 2", "OSC 6 FX 16 Ext 3", "OSC 6 FX 16 Ext 4", "OSC 1 Sample End", "OSC 1 Sample Loop Start", "OSC 1 Sample Loop End", "OSC 1 Sample Loop Crossfade", "OSC 1 Sample Gain", "OSC 1 Sample Vel Start", "OSC 1 Sample Width", "OSC 2 Sample End", "OSC 2 Sample Loop Start", "OSC 2 Sample Loop End", "OSC 2 Sample Loop Crossfade", "OSC 2 Sample Gain", "OSC 2 Sample Vel Start", "OSC 2 Sample Width", "OSC 3 Sample End", "OSC 3 Sample Loop Start", "OSC 3 Sample Loop End", "OSC 3 Sample Loop Crossfade", "OSC 3 Sample Gain", "OSC 3 Sample Vel Start", "OSC 3 Sample Width", "OSC 4 Sample End", "OSC 4 Sample Loop Start", "OSC 4 Sample Loop End", "OSC 4 Sample Loop Crossfade", "OSC 4 Sample Gain", "OSC 4 Sample Vel Start", "OSC 4 Sample Width", "OSC 5 Sample End", "OSC 5 Sample Loop Start", "OSC 5 Sample Loop End", "OSC 5 Sample Loop Crossfade", "OSC 5 Sample Gain", "OSC 5 Sample Vel Start", "OSC 5 Sample Width", "OSC 6 Sample End", "OSC 6 Sample Loop Start", "OSC 6 Sample Loop End", "OSC 6 Sample Loop Crossfade", "OSC 6 Sample Gain", "OSC 6 Sample Vel Start", "OSC 6 Sample Width", "OSC 1 Warp 3 Amount", "OSC 1 WT Tone", "OSC 2 Warp 3 Amount", "OSC 2 WT Tone", "OSC 3 Warp 3 Amount", "OSC 3 WT Tone", "OSC 4 Warp 3 Amount", "OSC 4 WT Tone", "OSC 5 Warp 3 Amount", "OSC 5 WT Tone", "OSC 6 Warp 3 Amount", "OSC 6 WT Tone", "LFO 1 Key Fine", "LFO 1 Skew", "LFO 1 Jitter", "LFO 1 Voice Spread", "LFO 1 Depth", "LFO 1 Table Pos", "LFO 2 Key Fine", "LFO 2 Skew", "LFO 2 Jitter", "LFO 2 Voice Spread", "LFO 2 Depth", "LFO 2 Table Pos", "LFO 3 Key Fine", "LFO 3 Skew", "LFO 3 Jitter", "LFO 3 Voice Spread", "LFO 3 Depth", "LFO 3 Table Pos", "LFO 4 Key Fine", "LFO 4 Skew", "LFO 4 Jitter", "LFO 4 Voice Spread", "LFO 4 Depth", "LFO 4 Table Pos", "LFO 5 Key Fine", "LFO 5 Skew", "LFO 5 Jitter", "LFO 5 Voice Spread", "LFO 5 Depth", "LFO 5 Table Pos", "LFO 6 Key Fine", "LFO 6 Skew", "LFO 6 Jitter", "LFO 6 Voice Spread", "LFO 6 Depth", "LFO 6 Table Pos", "LFO 7 Key Fine", "LFO 7 Skew", "LFO 7 Jitter", "LFO 7 Voice Spread", "LFO 7 Depth", "LFO 7 Table Pos", "LFO 8 Key Fine", "LFO 8 Skew", "LFO 8 Jitter", "LFO 8 Voice Spread", "LFO 8 Depth", "LFO 8 Table Pos", "LFO 9 Key Fine", "LFO 9 Skew", "LFO 9 Jitter", "LFO 9 Voice Spread", "LFO 9 Depth", "LFO 9 Table Pos", "LFO 10 Key Fine", "LFO 10 Skew", "LFO 10 Jitter", "LFO 10 Voice Spread", "LFO 10 Depth", "LFO 10 Table Pos", "Mod Env 1 Delay", "Mod Env 1 Hold", "Mod Env 1 Attack Curve", "Mod Env 1 Decay Curve", "Mod Env 1 Release Curve", "Mod Env 1 Velocity", "Mod Env 1 Key Track", "Mod Env 1 Level", "Mod Env 2 Delay", "Mod Env 2 Hold", "Mod Env 2 Attack Curve", "Mod Env 2 Decay Curve", "Mod Env 2 Release Curve", "Mod Env 2 Velocity", "Mod Env 2 Key Track", "Mod Env 2 Level", "Mod Env 3 Delay", "Mod Env 3 Hold", "Mod Env 3 Attack Curve", "Mod Env 3 Decay Curve", "Mod Env 3 Release Curve", "Mod Env 3 Velocity", "Mod Env 3 Key Track", "Mod Env 3 Level", "Mod Env 4 Delay", "Mod Env 4 Hold", "Mod Env 4 Attack Curve", "Mod Env 4 Decay Curve", "Mod Env 4 Release Curve", "Mod Env 4 Velocity", "Mod Env 4 Key Track", "Mod Env 4 Level", "Mod Env 5 Delay", "Mod Env 5 Hold", "Mod Env 5 Attack Curve", "Mod Env 5 Decay Curve", "Mod Env 5 Release Curve", "Mod Env 5 Velocity", "Mod Env 5 Key Track", "Mod Env 5 Level", "Mod Env 6 Delay", "Mod Env 6 Hold", "Mod Env 6 Attack Curve", "Mod Env 6 Decay Curve", "Mod Env 6 Release Curve", "Mod Env 6 Velocity", "Mod Env 6 Key Track", "Mod Env 6 Level", "Mod Env 7 Delay", "Mod Env 7 Hold", "Mod Env 7 Attack Curve", "Mod Env 7 Decay Curve", "Mod Env 7 Release Curve", "Mod Env 7 Velocity", "Mod Env 7 Key Track", "Mod Env 7 Level", "Mod Env 8 Delay", "Mod Env 8 Hold", "Mod Env 8 Attack Curve", "Mod Env 8 Decay Curve", "Mod Env 8 Release Curve", "Mod Env 8 Velocity", "Mod Env 8 Key Track", "Mod Env 8 Level", "Mod Env 9 Delay", "Mod Env 9 Hold", "Mod Env 9 Attack Curve", "Mod Env 9 Decay Curve", "Mod Env 9 Release Curve", "Mod Env 9 Velocity", "Mod Env 9 Key Track", "Mod Env 9 Level", "Mod Env 10 Delay", "Mod Env 10 Hold", "Mod Env 10 Attack Curve", "Mod Env 10 Decay Curve", "Mod Env 10 Release Curve", "Mod Env 10 Velocity", "Mod Env 10 Key Track", "Mod Env 10 Level", "Amp Env Delay", "Amp Env Hold", "Amp Env Attack Curve", "Amp Env Decay Curve", "Amp Env Release Curve", "Amp Env Velocity", "Amp Env Key Track", "Amp Env Level", "OSC 1 Filter Env Delay", "OSC 1 Filter Env Hold", "OSC 1 Filter Env Attack Curve", "OSC 1 Filter Env Decay Curve", "OSC 1 Filter Env Release Curve", "OSC 1 Filter Env Velocity", "OSC 1 Filter Env Key Track", "OSC 1 Filter Env Level", "OSC 2 Filter Env Delay", "OSC 2 Filter Env Hold", "OSC 2 Filter Env Attack Curve", "OSC 2 Filter Env Decay Curve", "OSC 2 Filter Env Release Curve", "OSC 2 Filter Env Velocity", "OSC 2 Filter Env Key Track", "OSC 2 Filter Env Level", "OSC 3 Filter Env Delay", "OSC 3 Filter Env Hold", "OSC 3 Filter Env Attack Curve", "OSC 3 Filter Env Decay Curve", "OSC 3 Filter Env Release Curve", "OSC 3 Filter Env Velocity", "OSC 3 Filter Env Key Track", "OSC 3 Filter Env Level", "OSC 4 Filter Env Delay", "OSC 4 Filter Env Hold", "OSC 4 Filter Env Attack Curve", "OSC 4 Filter Env Decay Curve", "OSC 4 Filter Env Release Curve", "OSC 4 Filter Env Velocity", "OSC 4 Filter Env Key Track", "OSC 4 Filter Env Level", "OSC 5 Filter Env Delay", "OSC 5 Filter Env Hold", "OSC 5 Filter Env Attack Curve", "OSC 5 Filter Env Decay Curve", "OSC 5 Filter Env Release Curve", "OSC 5 Filter Env Velocity", "OSC 5 Filter Env Key Track", "OSC 5 Filter Env Level", "OSC 6 Filter Env Delay", "OSC 6 Filter Env Hold", "OSC 6 Filter Env Attack Curve", "OSC 6 Filter Env Decay Curve", "OSC 6 Filter Env Release Curve", "OSC 6 Filter Env Velocity", "OSC 6 Filter Env Key Track", "OSC 6 Filter Env Level", "OSC 1 Warp 3 Amount", "OSC 2 Warp 3 Amount", "OSC 3 Warp 3 Amount", "OSC 4 Warp 3 Amount", "OSC 5 Warp 3 Amount", "OSC 6 Warp 3 Amount"];
const MOD_DST_GROUPS = [[0, ""], [1, "Global"], [6, "OSC 1"], [15, "OSC 2"], [24, "OSC 3"], [33, "OSC 4"], [42, "OSC 5"], [51, "OSC 6"], [60, "FM matrix (amount)"], [96, "PM matrix (amount)"], [132, "PD matrix (amount)"], [168, "Tables"], [180, "Frequency"], [186, "RM matrix (amount)"], [222, "AM matrix (amount)"], [258, "OSC 1 Physical / Alpha Juno"], [289, "OSC 2 Physical / Alpha Juno"], [320, "OSC 3 Physical / Alpha Juno"], [351, "OSC 4 Physical / Alpha Juno"], [382, "OSC 5 Physical / Alpha Juno"], [413, "OSC 6 Physical / Alpha Juno"], [444, "OSC 1 Kick"], [460, "OSC 2 Kick"], [476, "OSC 3 Kick"], [492, "OSC 4 Kick"], [508, "OSC 5 Kick"], [524, "OSC 6 Kick"], [540, "OSC 1 Wave Terrain"], [556, "OSC 2 Wave Terrain"], [572, "OSC 3 Wave Terrain"], [588, "OSC 4 Wave Terrain"], [604, "OSC 5 Wave Terrain"], [620, "OSC 6 Wave Terrain"], [636, "OSC 1 Waveguide"], [652, "OSC 2 Waveguide"], [668, "OSC 3 Waveguide"], [684, "OSC 4 Waveguide"], [700, "OSC 5 Waveguide"], [716, "OSC 6 Waveguide"], [732, "OSC 1 JP-8080"], [748, "OSC 2 JP-8080"], [764, "OSC 3 JP-8080"], [780, "OSC 4 JP-8080"], [796, "OSC 5 JP-8080"], [812, "OSC 6 JP-8080"], [828, "OSC 1 Granular"], [844, "OSC 2 Granular"], [860, "OSC 3 Granular"], [876, "OSC 4 Granular"], [892, "OSC 5 Granular"], [908, "OSC 6 Granular"], [924, "OSC 1 Additive"], [940, "OSC 2 Additive"], [956, "OSC 3 Additive"], [972, "OSC 4 Additive"], [988, "OSC 5 Additive"], [1004, "OSC 6 Additive"], [1020, "OSC 1 Modal Drum"], [1036, "OSC 2 Modal Drum"], [1052, "OSC 3 Modal Drum"], [1068, "OSC 4 Modal Drum"], [1084, "OSC 5 Modal Drum"], [1100, "OSC 6 Modal Drum"], [1116, "OSC 1 Spectral"], [1132, "OSC 2 Spectral"], [1148, "OSC 3 Spectral"], [1164, "OSC 4 Spectral"], [1180, "OSC 5 Spectral"], [1196, "OSC 6 Spectral"], [1212, "OSC 1 SoundFont"], [1228, "OSC 2 SoundFont"], [1244, "OSC 3 SoundFont"], [1260, "OSC 4 SoundFont"], [1276, "OSC 5 SoundFont"], [1292, "OSC 6 SoundFont"], [1308, "TZFM matrix (amount)"], [1344, "XF matrix (amount)"], [1380, "FD matrix (amount)"], [1416, "XR matrix (amount)"], [1452, "CP matrix (amount)"], [1488, "OSC 1 Bagpipe"], [1504, "OSC 2 Bagpipe"], [1520, "OSC 3 Bagpipe"], [1536, "OSC 4 Bagpipe"], [1552, "OSC 5 Bagpipe"], [1568, "OSC 6 Bagpipe"], [1584, "Param Attack"], [1585, "Param Decay"], [1586, "Param Sustain"], [1587, "Param Release"], [1588, "Param Velocity"], [1589, "Param Synth"], [1590, "Param Master"], [1591, "Param Pitch"], [1592, "Param P.EG"], [1593, "Param Master"], [1594, "Param Stereo"], [1595, "Param Tone"], [1596, "Param Out"], [1597, "Param DC"], [1598, "Param LFO 1"], [1599, "Param LFO 2"], [1600, "Param LFO 3"], [1601, "Param LFO 4"], [1602, "Param LFO 5"], [1603, "Param LFO 6"], [1604, "Param LFO 7"], [1605, "Param LFO 8"], [1606, "Param LFO 9"], [1607, "Param LFO 10"], [1608, "Param Env 1"], [1612, "Param Env 2"], [1616, "Param Env 3"], [1620, "Param Env 4"], [1624, "Param Env 5"], [1628, "Param Env 6"], [1632, "Param Env 7"], [1636, "Param Env 8"], [1640, "Param Env 9"], [1644, "Param Env 10"], [1648, "Param Sync"], [1649, "Param OSC 1 Level"], [1650, "Param OSC 1 Pan"], [1651, "Param OSC 1 Fine"], [1652, "Param OSC 1 Start"], [1653, "Param OSC 1 WT"], [1654, "Param OSC 1 Unison"], [1657, "Param OSC 1 Warp"], [1659, "Param OSC 1 Sample"], [1660, "Param OSC 1 Terrain"], [1663, "Param OSC 1 Unison"], [1665, "Param OSC 1 Filter"], [1675, "Param OSC 1 Distortion"], [1677, "Param OSC 1 Wavefilter"], [1678, "Param OSC 1 Wavedistortion"], [1679, "Param OSC 1 Frequency"], [1680, "Param OSC 1 Wavefilter"], [1686, "Param OSC 1 Resonator"], [1692, "Param OSC 2 Level"], [1693, "Param OSC 2 Pan"], [1694, "Param OSC 2 Fine"], [1695, "Param OSC 2 Start"], [1696, "Param OSC 2 WT"], [1697, "Param OSC 2 Unison"], [1700, "Param OSC 2 Warp"], [1702, "Param OSC 2 Sample"], [1703, "Param OSC 2 Terrain"], [1706, "Param OSC 2 Unison"], [1708, "Param OSC 2 Filter"], [1718, "Param OSC 2 Distortion"], [1720, "Param OSC 2 Wavefilter"], [1721, "Param OSC 2 Wavedistortion"], [1722, "Param OSC 2 Frequency"], [1723, "Param OSC 2 Wavefilter"], [1729, "Param OSC 2 Resonator"], [1735, "Param OSC 3 Level"], [1736, "Param OSC 3 Pan"], [1737, "Param OSC 3 Fine"], [1738, "Param OSC 3 Start"], [1739, "Param OSC 3 WT"], [1740, "Param OSC 3 Unison"], [1743, "Param OSC 3 Warp"], [1745, "Param OSC 3 Sample"], [1746, "Param OSC 3 Terrain"], [1749, "Param OSC 3 Unison"], [1751, "Param OSC 3 Filter"], [1761, "Param OSC 3 Distortion"], [1763, "Param OSC 3 Wavefilter"], [1764, "Param OSC 3 Wavedistortion"], [1765, "Param OSC 3 Frequency"], [1766, "Param OSC 3 Wavefilter"], [1772, "Param OSC 3 Resonator"], [1778, "Param OSC 4 Level"], [1779, "Param OSC 4 Pan"], [1780, "Param OSC 4 Fine"], [1781, "Param OSC 4 Start"], [1782, "Param OSC 4 WT"], [1783, "Param OSC 4 Unison"], [1786, "Param OSC 4 Warp"], [1788, "Param OSC 4 Sample"], [1789, "Param OSC 4 Terrain"], [1792, "Param OSC 4 Unison"], [1794, "Param OSC 4 Filter"], [1804, "Param OSC 4 Distortion"], [1806, "Param OSC 4 Wavefilter"], [1807, "Param OSC 4 Wavedistortion"], [1808, "Param OSC 4 Frequency"], [1809, "Param OSC 4 Wavefilter"], [1815, "Param OSC 4 Resonator"], [1821, "Param OSC 5 Level"], [1822, "Param OSC 5 Pan"], [1823, "Param OSC 5 Fine"], [1824, "Param OSC 5 Start"], [1825, "Param OSC 5 WT"], [1826, "Param OSC 5 Unison"], [1829, "Param OSC 5 Warp"], [1831, "Param OSC 5 Sample"], [1832, "Param OSC 5 Terrain"], [1835, "Param OSC 5 Unison"], [1837, "Param OSC 5 Filter"], [1847, "Param OSC 5 Distortion"], [1849, "Param OSC 5 Wavefilter"], [1850, "Param OSC 5 Wavedistortion"], [1851, "Param OSC 5 Frequency"], [1852, "Param OSC 5 Wavefilter"], [1858, "Param OSC 5 Resonator"], [1864, "Param OSC 6 Level"], [1865, "Param OSC 6 Pan"], [1866, "Param OSC 6 Fine"], [1867, "Param OSC 6 Start"], [1868, "Param OSC 6 WT"], [1869, "Param OSC 6 Unison"], [1872, "Param OSC 6 Warp"], [1874, "Param OSC 6 Sample"], [1875, "Param OSC 6 Terrain"], [1878, "Param OSC 6 Unison"], [1880, "Param OSC 6 Filter"], [1890, "Param OSC 6 Distortion"], [1892, "Param OSC 6 Wavefilter"], [1893, "Param OSC 6 Wavedistortion"], [1894, "Param OSC 6 Frequency"], [1895, "Param OSC 6 Wavefilter"], [1901, "Param OSC 6 Resonator"], [1907, "Param Freq 1"], [1909, "Param Freq 2"], [1911, "Param Freq 3"], [1913, "Param Freq 4"], [1915, "Param Freq 5"], [1917, "Param Freq 6"], [1919, "Param Freq 7"], [1921, "Param Freq 8"], [1923, "Param Freq 9"], [1925, "Param Freq 10"], [1927, "Param OSC 1 Physical"], [1940, "Param OSC 1 Juno"], [1950, "Param OSC 2 Physical"], [1963, "Param OSC 2 Juno"], [1973, "Param OSC 3 Physical"], [1986, "Param OSC 3 Juno"], [1996, "Param OSC 4 Physical"], [2009, "Param OSC 4 Juno"], [2019, "Param OSC 5 Physical"], [2032, "Param OSC 5 Juno"], [2042, "Param OSC 6 Physical"], [2055, "Param OSC 6 Juno"], [2065, "Param OSC 1 Kick"], [2079, "Param OSC 2 Kick"], [2093, "Param OSC 3 Kick"], [2107, "Param OSC 4 Kick"], [2121, "Param OSC 5 Kick"], [2135, "Param OSC 6 Kick"], [2149, "Param OSC 1 Terrain"], [2164, "Param OSC 2 Terrain"], [2179, "Param OSC 3 Terrain"], [2194, "Param OSC 4 Terrain"], [2209, "Param OSC 5 Terrain"], [2224, "Param OSC 6 Terrain"], [2239, "Param OSC 1 Waveguide"], [2254, "Param OSC 2 Waveguide"], [2269, "Param OSC 3 Waveguide"], [2284, "Param OSC 4 Waveguide"], [2299, "Param OSC 5 Waveguide"], [2314, "Param OSC 6 Waveguide"], [2329, "Param OSC 1 JP"], [2344, "Param OSC 2 JP"], [2359, "Param OSC 3 JP"], [2374, "Param OSC 4 JP"], [2389, "Param OSC 5 JP"], [2404, "Param OSC 6 JP"], [2419, "Param OSC 1 Granular"], [2431, "Param OSC 2 Granular"], [2443, "Param OSC 3 Granular"], [2455, "Param OSC 4 Granular"], [2467, "Param OSC 5 Granular"], [2479, "Param OSC 6 Granular"], [2491, "Param OSC 1 Additive"], [2504, "Param OSC 2 Additive"], [2517, "Param OSC 3 Additive"], [2530, "Param OSC 4 Additive"], [2543, "Param OSC 5 Additive"], [2556, "Param OSC 6 Additive"], [2569, "Param OSC 1 Drum"], [2585, "Param OSC 2 Drum"], [2601, "Param OSC 3 Drum"], [2617, "Param OSC 4 Drum"], [2633, "Param OSC 5 Drum"], [2649, "Param OSC 6 Drum"], [2665, "Param OSC 1 Spectral"], [2680, "Param OSC 2 Spectral"], [2695, "Param OSC 3 Spectral"], [2710, "Param OSC 4 Spectral"], [2725, "Param OSC 5 Spectral"], [2740, "Param OSC 6 Spectral"], [2755, "Param OSC 1 SoundFont"], [2764, "Param OSC 2 SoundFont"], [2773, "Param OSC 3 SoundFont"], [2782, "Param OSC 4 SoundFont"], [2791, "Param OSC 5 SoundFont"], [2800, "Param OSC 6 SoundFont"], [2809, "Param Main FX 1"], [2810, "Param Main FX 2"], [2811, "Param Main FX 3"], [2812, "Param Main FX 4"], [2813, "Param Main FX 5"], [2814, "Param Main FX 6"], [2815, "Param Main FX 7"], [2816, "Param Main FX 8"], [2817, "Param Main FX 9"], [2818, "Param Main FX 10"], [2819, "Param Bus 1"], [2829, "Param Bus 2"], [2839, "Param Main FX 1"], [2840, "Param Main FX 2"], [2841, "Param Main FX 3"], [2842, "Param Main FX 4"], [2843, "Param Main FX 5"], [2844, "Param Main FX 6"], [2845, "Param Main FX 7"], [2846, "Param Main FX 8"], [2847, "Param Main FX 9"], [2848, "Param Main FX 10"], [2849, "Param Bus 1"], [2859, "Param Bus 2"], [2869, "Param Main FX 11"], [2876, "Param Main FX 12"], [2883, "Param Main FX 13"], [2890, "Param Main FX 14"], [2897, "Param Main FX 15"], [2904, "Param Main FX 16"], [2911, "Param Bus 1"], [2953, "Param Bus 2"], [2995, "Param OSC 1 Bagpipe"], [3007, "Param OSC 2 Bagpipe"], [3019, "Param OSC 3 Bagpipe"], [3031, "Param OSC 4 Bagpipe"], [3043, "Param OSC 5 Bagpipe"], [3055, "Param OSC 6 Bagpipe"], [3067, "Param Seq 1"], [3069, "Param Seq 2"], [3071, "Param Seq 3"], [3073, "Param Seq 4"], [3075, "Param Seq 5"], [3077, "Param Seq 6"], [3079, "Param Seq 7"], [3081, "Param Seq 8"], [3083, "Param Seq 9"], [3085, "Param Seq 10"], [3087, "Param OSC 1 FX 1"], [3096, "Param OSC 1 FX 2"], [3105, "Param OSC 1 FX 3"], [3114, "Param OSC 1 FX 4"], [3123, "Param OSC 1 FX 5"], [3132, "Param OSC 1 FX 6"], [3141, "Param OSC 1 FX 7"], [3150, "Param OSC 1 FX 8"], [3159, "Param OSC 1 FX 9"], [3168, "Param OSC 1 FX 10"], [3177, "Param OSC 1 FX 11"], [3186, "Param OSC 1 FX 12"], [3195, "Param OSC 1 FX 13"], [3204, "Param OSC 1 FX 14"], [3213, "Param OSC 1 FX 15"], [3222, "Param OSC 1 FX 16"], [3231, "Param OSC 2 FX 1"], [3240, "Param OSC 2 FX 2"], [3249, "Param OSC 2 FX 3"], [3258, "Param OSC 2 FX 4"], [3267, "Param OSC 2 FX 5"], [3276, "Param OSC 2 FX 6"], [3285, "Param OSC 2 FX 7"], [3294, "Param OSC 2 FX 8"], [3303, "Param OSC 2 FX 9"], [3312, "Param OSC 2 FX 10"], [3321, "Param OSC 2 FX 11"], [3330, "Param OSC 2 FX 12"], [3339, "Param OSC 2 FX 13"], [3348, "Param OSC 2 FX 14"], [3357, "Param OSC 2 FX 15"], [3366, "Param OSC 2 FX 16"], [3375, "Param OSC 3 FX 1"], [3384, "Param OSC 3 FX 2"], [3393, "Param OSC 3 FX 3"], [3402, "Param OSC 3 FX 4"], [3411, "Param OSC 3 FX 5"], [3420, "Param OSC 3 FX 6"], [3429, "Param OSC 3 FX 7"], [3438, "Param OSC 3 FX 8"], [3447, "Param OSC 3 FX 9"], [3456, "Param OSC 3 FX 10"], [3465, "Param OSC 3 FX 11"], [3474, "Param OSC 3 FX 12"], [3483, "Param OSC 3 FX 13"], [3492, "Param OSC 3 FX 14"], [3501, "Param OSC 3 FX 15"], [3510, "Param OSC 3 FX 16"], [3519, "Param OSC 4 FX 1"], [3528, "Param OSC 4 FX 2"], [3537, "Param OSC 4 FX 3"], [3546, "Param OSC 4 FX 4"], [3555, "Param OSC 4 FX 5"], [3564, "Param OSC 4 FX 6"], [3573, "Param OSC 4 FX 7"], [3582, "Param OSC 4 FX 8"], [3591, "Param OSC 4 FX 9"], [3600, "Param OSC 4 FX 10"], [3609, "Param OSC 4 FX 11"], [3618, "Param OSC 4 FX 12"], [3627, "Param OSC 4 FX 13"], [3636, "Param OSC 4 FX 14"], [3645, "Param OSC 4 FX 15"], [3654, "Param OSC 4 FX 16"], [3663, "Param OSC 5 FX 1"], [3672, "Param OSC 5 FX 2"], [3681, "Param OSC 5 FX 3"], [3690, "Param OSC 5 FX 4"], [3699, "Param OSC 5 FX 5"], [3708, "Param OSC 5 FX 6"], [3717, "Param OSC 5 FX 7"], [3726, "Param OSC 5 FX 8"], [3735, "Param OSC 5 FX 9"], [3744, "Param OSC 5 FX 10"], [3753, "Param OSC 5 FX 11"], [3762, "Param OSC 5 FX 12"], [3771, "Param OSC 5 FX 13"], [3780, "Param OSC 5 FX 14"], [3789, "Param OSC 5 FX 15"], [3798, "Param OSC 5 FX 16"], [3807, "Param OSC 6 FX 1"], [3816, "Param OSC 6 FX 2"], [3825, "Param OSC 6 FX 3"], [3834, "Param OSC 6 FX 4"], [3843, "Param OSC 6 FX 5"], [3852, "Param OSC 6 FX 6"], [3861, "Param OSC 6 FX 7"], [3870, "Param OSC 6 FX 8"], [3879, "Param OSC 6 FX 9"], [3888, "Param OSC 6 FX 10"], [3897, "Param OSC 6 FX 11"], [3906, "Param OSC 6 FX 12"], [3915, "Param OSC 6 FX 13"], [3924, "Param OSC 6 FX 14"], [3933, "Param OSC 6 FX 15"], [3942, "Param OSC 6 FX 16"], [3951, "Param Patch"], [4019, "Param Euro"], [4259, "Param Main FX 1"], [4263, "Param Main FX 2"], [4267, "Param Main FX 3"], [4271, "Param Main FX 4"], [4275, "Param Main FX 5"], [4279, "Param Main FX 6"], [4283, "Param Main FX 7"], [4287, "Param Main FX 8"], [4291, "Param Main FX 9"], [4295, "Param Main FX 10"], [4299, "Param Bus 1"], [4339, "Param Bus 2"], [4379, "Param Main FX 11"], [4383, "Param Main FX 12"], [4387, "Param Main FX 13"], [4391, "Param Main FX 14"], [4395, "Param Main FX 15"], [4399, "Param Main FX 16"], [4403, "Param Bus 1"], [4427, "Param Bus 2"], [4451, "Param OSC 1 FX 1"], [4455, "Param OSC 1 FX 2"], [4459, "Param OSC 1 FX 3"], [4463, "Param OSC 1 FX 4"], [4467, "Param OSC 1 FX 5"], [4471, "Param OSC 1 FX 6"], [4475, "Param OSC 1 FX 7"], [4479, "Param OSC 1 FX 8"], [4483, "Param OSC 1 FX 9"], [4487, "Param OSC 1 FX 10"], [4491, "Param OSC 1 FX 11"], [4495, "Param OSC 1 FX 12"], [4499, "Param OSC 1 FX 13"], [4503, "Param OSC 1 FX 14"], [4507, "Param OSC 1 FX 15"], [4511, "Param OSC 1 FX 16"], [4515, "Param OSC 2 FX 1"], [4519, "Param OSC 2 FX 2"], [4523, "Param OSC 2 FX 3"], [4527, "Param OSC 2 FX 4"], [4531, "Param OSC 2 FX 5"], [4535, "Param OSC 2 FX 6"], [4539, "Param OSC 2 FX 7"], [4543, "Param OSC 2 FX 8"], [4547, "Param OSC 2 FX 9"], [4551, "Param OSC 2 FX 10"], [4555, "Param OSC 2 FX 11"], [4559, "Param OSC 2 FX 12"], [4563, "Param OSC 2 FX 13"], [4567, "Param OSC 2 FX 14"], [4571, "Param OSC 2 FX 15"], [4575, "Param OSC 2 FX 16"], [4579, "Param OSC 3 FX 1"], [4583, "Param OSC 3 FX 2"], [4587, "Param OSC 3 FX 3"], [4591, "Param OSC 3 FX 4"], [4595, "Param OSC 3 FX 5"], [4599, "Param OSC 3 FX 6"], [4603, "Param OSC 3 FX 7"], [4607, "Param OSC 3 FX 8"], [4611, "Param OSC 3 FX 9"], [4615, "Param OSC 3 FX 10"], [4619, "Param OSC 3 FX 11"], [4623, "Param OSC 3 FX 12"], [4627, "Param OSC 3 FX 13"], [4631, "Param OSC 3 FX 14"], [4635, "Param OSC 3 FX 15"], [4639, "Param OSC 3 FX 16"], [4643, "Param OSC 4 FX 1"], [4647, "Param OSC 4 FX 2"], [4651, "Param OSC 4 FX 3"], [4655, "Param OSC 4 FX 4"], [4659, "Param OSC 4 FX 5"], [4663, "Param OSC 4 FX 6"], [4667, "Param OSC 4 FX 7"], [4671, "Param OSC 4 FX 8"], [4675, "Param OSC 4 FX 9"], [4679, "Param OSC 4 FX 10"], [4683, "Param OSC 4 FX 11"], [4687, "Param OSC 4 FX 12"], [4691, "Param OSC 4 FX 13"], [4695, "Param OSC 4 FX 14"], [4699, "Param OSC 4 FX 15"], [4703, "Param OSC 4 FX 16"], [4707, "Param OSC 5 FX 1"], [4711, "Param OSC 5 FX 2"], [4715, "Param OSC 5 FX 3"], [4719, "Param OSC 5 FX 4"], [4723, "Param OSC 5 FX 5"], [4727, "Param OSC 5 FX 6"], [4731, "Param OSC 5 FX 7"], [4735, "Param OSC 5 FX 8"], [4739, "Param OSC 5 FX 9"], [4743, "Param OSC 5 FX 10"], [4747, "Param OSC 5 FX 11"], [4751, "Param OSC 5 FX 12"], [4755, "Param OSC 5 FX 13"], [4759, "Param OSC 5 FX 14"], [4763, "Param OSC 5 FX 15"], [4767, "Param OSC 5 FX 16"], [4771, "Param OSC 6 FX 1"], [4775, "Param OSC 6 FX 2"], [4779, "Param OSC 6 FX 3"], [4783, "Param OSC 6 FX 4"], [4787, "Param OSC 6 FX 5"], [4791, "Param OSC 6 FX 6"], [4795, "Param OSC 6 FX 7"], [4799, "Param OSC 6 FX 8"], [4803, "Param OSC 6 FX 9"], [4807, "Param OSC 6 FX 10"], [4811, "Param OSC 6 FX 11"], [4815, "Param OSC 6 FX 12"], [4819, "Param OSC 6 FX 13"], [4823, "Param OSC 6 FX 14"], [4827, "Param OSC 6 FX 15"], [4831, "Param OSC 6 FX 16"], [4835, "Param Out"], [4836, "Param Main FX 1"], [4840, "Param Main FX 2"], [4844, "Param Main FX 3"], [4848, "Param Main FX 4"], [4852, "Param Main FX 5"], [4856, "Param Main FX 6"], [4860, "Param Main FX 7"], [4864, "Param Main FX 8"], [4868, "Param Main FX 9"], [4872, "Param Main FX 10"], [4876, "Param Bus 1"], [4916, "Param Bus 2"], [4956, "Param Main FX 11"], [4960, "Param Main FX 12"], [4964, "Param Main FX 13"], [4968, "Param Main FX 14"], [4972, "Param Main FX 15"], [4976, "Param Main FX 16"], [4980, "Param Bus 1"], [5004, "Param Bus 2"], [5028, "Param OSC 1 FX 1"], [5032, "Param OSC 1 FX 2"], [5036, "Param OSC 1 FX 3"], [5040, "Param OSC 1 FX 4"], [5044, "Param OSC 1 FX 5"], [5048, "Param OSC 1 FX 6"], [5052, "Param OSC 1 FX 7"], [5056, "Param OSC 1 FX 8"], [5060, "Param OSC 1 FX 9"], [5064, "Param OSC 1 FX 10"], [5068, "Param OSC 1 FX 11"], [5072, "Param OSC 1 FX 12"], [5076, "Param OSC 1 FX 13"], [5080, "Param OSC 1 FX 14"], [5084, "Param OSC 1 FX 15"], [5088, "Param OSC 1 FX 16"], [5092, "Param OSC 2 FX 1"], [5096, "Param OSC 2 FX 2"], [5100, "Param OSC 2 FX 3"], [5104, "Param OSC 2 FX 4"], [5108, "Param OSC 2 FX 5"], [5112, "Param OSC 2 FX 6"], [5116, "Param OSC 2 FX 7"], [5120, "Param OSC 2 FX 8"], [5124, "Param OSC 2 FX 9"], [5128, "Param OSC 2 FX 10"], [5132, "Param OSC 2 FX 11"], [5136, "Param OSC 2 FX 12"], [5140, "Param OSC 2 FX 13"], [5144, "Param OSC 2 FX 14"], [5148, "Param OSC 2 FX 15"], [5152, "Param OSC 2 FX 16"], [5156, "Param OSC 3 FX 1"], [5160, "Param OSC 3 FX 2"], [5164, "Param OSC 3 FX 3"], [5168, "Param OSC 3 FX 4"], [5172, "Param OSC 3 FX 5"], [5176, "Param OSC 3 FX 6"], [5180, "Param OSC 3 FX 7"], [5184, "Param OSC 3 FX 8"], [5188, "Param OSC 3 FX 9"], [5192, "Param OSC 3 FX 10"], [5196, "Param OSC 3 FX 11"], [5200, "Param OSC 3 FX 12"], [5204, "Param OSC 3 FX 13"], [5208, "Param OSC 3 FX 14"], [5212, "Param OSC 3 FX 15"], [5216, "Param OSC 3 FX 16"], [5220, "Param OSC 4 FX 1"], [5224, "Param OSC 4 FX 2"], [5228, "Param OSC 4 FX 3"], [5232, "Param OSC 4 FX 4"], [5236, "Param OSC 4 FX 5"], [5240, "Param OSC 4 FX 6"], [5244, "Param OSC 4 FX 7"], [5248, "Param OSC 4 FX 8"], [5252, "Param OSC 4 FX 9"], [5256, "Param OSC 4 FX 10"], [5260, "Param OSC 4 FX 11"], [5264, "Param OSC 4 FX 12"], [5268, "Param OSC 4 FX 13"], [5272, "Param OSC 4 FX 14"], [5276, "Param OSC 4 FX 15"], [5280, "Param OSC 4 FX 16"], [5284, "Param OSC 5 FX 1"], [5288, "Param OSC 5 FX 2"], [5292, "Param OSC 5 FX 3"], [5296, "Param OSC 5 FX 4"], [5300, "Param OSC 5 FX 5"], [5304, "Param OSC 5 FX 6"], [5308, "Param OSC 5 FX 7"], [5312, "Param OSC 5 FX 8"], [5316, "Param OSC 5 FX 9"], [5320, "Param OSC 5 FX 10"], [5324, "Param OSC 5 FX 11"], [5328, "Param OSC 5 FX 12"], [5332, "Param OSC 5 FX 13"], [5336, "Param OSC 5 FX 14"], [5340, "Param OSC 5 FX 15"], [5344, "Param OSC 5 FX 16"], [5348, "Param OSC 6 FX 1"], [5352, "Param OSC 6 FX 2"], [5356, "Param OSC 6 FX 3"], [5360, "Param OSC 6 FX 4"], [5364, "Param OSC 6 FX 5"], [5368, "Param OSC 6 FX 6"], [5372, "Param OSC 6 FX 7"], [5376, "Param OSC 6 FX 8"], [5380, "Param OSC 6 FX 9"], [5384, "Param OSC 6 FX 10"], [5388, "Param OSC 6 FX 11"], [5392, "Param OSC 6 FX 12"], [5396, "Param OSC 6 FX 13"], [5400, "Param OSC 6 FX 14"], [5404, "Param OSC 6 FX 15"], [5408, "Param OSC 6 FX 16"], [5412, "Param OSC 1 Sample"], [5419, "Param OSC 2 Sample"], [5426, "Param OSC 3 Sample"], [5433, "Param OSC 4 Sample"], [5440, "Param OSC 5 Sample"], [5447, "Param OSC 6 Sample"], [5454, "Param OSC 1 Warp"], [5455, "Param OSC 1 WT"], [5456, "Param OSC 2 Warp"], [5457, "Param OSC 2 WT"], [5458, "Param OSC 3 Warp"], [5459, "Param OSC 3 WT"], [5460, "Param OSC 4 Warp"], [5461, "Param OSC 4 WT"], [5462, "Param OSC 5 Warp"], [5463, "Param OSC 5 WT"], [5464, "Param OSC 6 Warp"], [5465, "Param OSC 6 WT"], [5466, "Param LFO 1"], [5472, "Param LFO 2"], [5478, "Param LFO 3"], [5484, "Param LFO 4"], [5490, "Param LFO 5"], [5496, "Param LFO 6"], [5502, "Param LFO 7"], [5508, "Param LFO 8"], [5514, "Param LFO 9"], [5520, "Param LFO 10"], [5526, "Param Mod"], [5606, "Param Amp"], [5614, "Param OSC 1 Filter"], [5622, "Param OSC 2 Filter"], [5630, "Param OSC 3 Filter"], [5638, "Param OSC 4 Filter"], [5646, "Param OSC 5 Filter"], [5654, "Param OSC 6 Filter"], [5662, "Warp 3 (per voice)"]];
const MOD_TARGET = {"63": [1, 0.5], "29": [3, 0.5], "28": [4, 0.5], "190": [5, 0.5], "1006": [6, 0.5], "1001": [7, 1], "1002": [8, 0.5], "1010": [9, 0.5], "1025": [9, 0.5], "1019": [10, 0.5], "1026": [10, 0.5], "1021": [11, 0.5], "1027": [11, 0.5], "1032": [12, 0.41], "1033": [13, 0.5], "1043": [14, 0.5], "1046": [168, 0.5], "1047": [169, 0.5], "1048": [180, 1.0], "1070": [15, 0.5], "1065": [16, 1], "1066": [17, 0.5], "1074": [18, 0.5], "1089": [18, 0.5], "1083": [19, 0.5], "1090": [19, 0.5], "1085": [20, 0.5], "1091": [20, 0.5], "1096": [21, 0.41], "1097": [22, 0.5], "1107": [23, 0.5], "1110": [170, 0.5], "1111": [171, 0.5], "1112": [181, 1.0], "1134": [24, 0.5], "1129": [25, 1], "1130": [26, 0.5], "1138": [27, 0.5], "1153": [27, 0.5], "1147": [28, 0.5], "1154": [28, 0.5], "1149": [29, 0.5], "1155": [29, 0.5], "1160": [30, 0.41], "1161": [31, 0.5], "1171": [32, 0.5], "1174": [172, 0.5], "1175": [173, 0.5], "1176": [182, 1.0], "1198": [33, 0.5], "1193": [34, 1], "1194": [35, 0.5], "1202": [36, 0.5], "1217": [36, 0.5], "1211": [37, 0.5], "1218": [37, 0.5], "1213": [38, 0.5], "1219": [38, 0.5], "1224": [39, 0.41], "1225": [40, 0.5], "1235": [41, 0.5], "1238": [174, 0.5], "1239": [175, 0.5], "1240": [183, 1.0], "1262": [42, 0.5], "1257": [43, 1], "1258": [44, 0.5], "1266": [45, 0.5], "1281": [45, 0.5], "1275": [46, 0.5], "1282": [46, 0.5], "1277": [47, 0.5], "1283": [47, 0.5], "1288": [48, 0.41], "1289": [49, 0.5], "1299": [50, 0.5], "1302": [176, 0.5], "1303": [177, 0.5], "1304": [184, 1.0], "1326": [51, 0.5], "1321": [52, 1], "1322": [53, 0.5], "1330": [54, 0.5], "1345": [54, 0.5], "1339": [55, 0.5], "1346": [55, 0.5], "1341": [56, 0.5], "1347": [56, 0.5], "1352": [57, 0.41], "1353": [58, 0.5], "1363": [59, 0.5], "1366": [178, 0.5], "1367": [179, 0.5], "1368": [185, 1.0], "1400": [60, 0.125], "1401": [61, 0.125], "1402": [62, 0.125], "1403": [63, 0.125], "1404": [64, 0.125], "1405": [65, 0.125], "1406": [66, 0.125], "1407": [67, 0.125], "1408": [68, 0.125], "1409": [69, 0.125], "1410": [70, 0.125], "1411": [71, 0.125], "1412": [72, 0.125], "1413": [73, 0.125], "1414": [74, 0.125], "1415": [75, 0.125], "1416": [76, 0.125], "1417": [77, 0.125], "1418": [78, 0.125], "1419": [79, 0.125], "1420": [80, 0.125], "1421": [81, 0.125], "1422": [82, 0.125], "1423": [83, 0.125], "1424": [84, 0.125], "1425": [85, 0.125], "1426": [86, 0.125], "1427": [87, 0.125], "1428": [88, 0.125], "1429": [89, 0.125], "1430": [90, 0.125], "1431": [91, 0.125], "1432": [92, 0.125], "1433": [93, 0.125], "1434": [94, 0.125], "1435": [95, 0.125], "1440": [96, 0.125], "1441": [97, 0.125], "1442": [98, 0.125], "1443": [99, 0.125], "1444": [100, 0.125], "1445": [101, 0.125], "1446": [102, 0.125], "1447": [103, 0.125], "1448": [104, 0.125], "1449": [105, 0.125], "1450": [106, 0.125], "1451": [107, 0.125], "1452": [108, 0.125], "1453": [109, 0.125], "1454": [110, 0.125], "1455": [111, 0.125], "1456": [112, 0.125], "1457": [113, 0.125], "1458": [114, 0.125], "1459": [115, 0.125], "1460": [116, 0.125], "1461": [117, 0.125], "1462": [118, 0.125], "1463": [119, 0.125], "1464": [120, 0.125], "1465": [121, 0.125], "1466": [122, 0.125], "1467": [123, 0.125], "1468": [124, 0.125], "1469": [125, 0.125], "1470": [126, 0.125], "1471": [127, 0.125], "1472": [128, 0.125], "1473": [129, 0.125], "1474": [130, 0.125], "1475": [131, 0.125], "1480": [132, 0.5], "1481": [133, 0.5], "1482": [134, 0.5], "1483": [135, 0.5], "1484": [136, 0.5], "1485": [137, 0.5], "1486": [138, 0.5], "1487": [139, 0.5], "1488": [140, 0.5], "1489": [141, 0.5], "1490": [142, 0.5], "1491": [143, 0.5], "1492": [144, 0.5], "1493": [145, 0.5], "1494": [146, 0.5], "1495": [147, 0.5], "1496": [148, 0.5], "1497": [149, 0.5], "1498": [150, 0.5], "1499": [151, 0.5], "1500": [152, 0.5], "1501": [153, 0.5], "1502": [154, 0.5], "1503": [155, 0.5], "1504": [156, 0.5], "1505": [157, 0.5], "1506": [158, 0.5], "1507": [159, 0.5], "1508": [160, 0.5], "1509": [161, 0.5], "1510": [162, 0.5], "1511": [163, 0.5], "1512": [164, 0.5], "1513": [165, 0.5], "1514": [166, 0.5], "1515": [167, 0.5], "1520": [186, 0.5], "1521": [187, 0.5], "1522": [188, 0.5], "1523": [189, 0.5], "1524": [190, 0.5], "1525": [191, 0.5], "1526": [192, 0.5], "1527": [193, 0.5], "1528": [194, 0.5], "1529": [195, 0.5], "1530": [196, 0.5], "1531": [197, 0.5], "1532": [198, 0.5], "1533": [199, 0.5], "1534": [200, 0.5], "1535": [201, 0.5], "1536": [202, 0.5], "1537": [203, 0.5], "1538": [204, 0.5], "1539": [205, 0.5], "1540": [206, 0.5], "1541": [207, 0.5], "1542": [208, 0.5], "1543": [209, 0.5], "1544": [210, 0.5], "1545": [211, 0.5], "1546": [212, 0.5], "1547": [213, 0.5], "1548": [214, 0.5], "1549": [215, 0.5], "1550": [216, 0.5], "1551": [217, 0.5], "1552": [218, 0.5], "1553": [219, 0.5], "1554": [220, 0.5], "1555": [221, 0.5], "1560": [222, 0.5], "1561": [223, 0.5], "1562": [224, 0.5], "1563": [225, 0.5], "1564": [226, 0.5], "1565": [227, 0.5], "1566": [228, 0.5], "1567": [229, 0.5], "1568": [230, 0.5], "1569": [231, 0.5], "1570": [232, 0.5], "1571": [233, 0.5], "1572": [234, 0.5], "1573": [235, 0.5], "1574": [236, 0.5], "1575": [237, 0.5], "1576": [238, 0.5], "1577": [239, 0.5], "1578": [240, 0.5], "1579": [241, 0.5], "1580": [242, 0.5], "1581": [243, 0.5], "1582": [244, 0.5], "1583": [245, 0.5], "1584": [246, 0.5], "1585": [247, 0.5], "1586": [248, 0.5], "1587": [249, 0.5], "1588": [250, 0.5], "1589": [251, 0.5], "1590": [252, 0.5], "1591": [253, 0.5], "1592": [254, 0.5], "1593": [255, 0.5], "1594": [256, 0.5], "1595": [257, 0.5], "1700": [258, 0.5], "1701": [259, 0.5], "1702": [260, 0.5], "1704": [262, 0.5], "1705": [263, 0.5], "1706": [264, 0.5], "1707": [265, 0.5], "1709": [267, 0.5], "1710": [268, 0.5], "1711": [269, 0.5], "1712": [270, 0.5], "1713": [271, 0.5], "1714": [272, 0.5], "1716": [274, 0.5], "1717": [275, 0.5], "1718": [276, 0.5], "1719": [277, 0.5], "1720": [278, 0.5], "1721": [279, 0.5], "1722": [280, 0.5], "1724": [282, 0.5], "1725": [283, 0.5], "1730": [288, 0.5], "1732": [289, 0.5], "1733": [290, 0.5], "1734": [291, 0.5], "1736": [293, 0.5], "1737": [294, 0.5], "1738": [295, 0.5], "1739": [296, 0.5], "1741": [298, 0.5], "1742": [299, 0.5], "1743": [300, 0.5], "1744": [301, 0.5], "1745": [302, 0.5], "1746": [303, 0.5], "1748": [305, 0.5], "1749": [306, 0.5], "1750": [307, 0.5], "1751": [308, 0.5], "1752": [309, 0.5], "1753": [310, 0.5], "1754": [311, 0.5], "1756": [313, 0.5], "1757": [314, 0.5], "1762": [319, 0.5], "1764": [320, 0.5], "1765": [321, 0.5], "1766": [322, 0.5], "1768": [324, 0.5], "1769": [325, 0.5], "1770": [326, 0.5], "1771": [327, 0.5], "1773": [329, 0.5], "1774": [330, 0.5], "1775": [331, 0.5], "1776": [332, 0.5], "1777": [333, 0.5], "1778": [334, 0.5], "1780": [336, 0.5], "1781": [337, 0.5], "1782": [338, 0.5], "1783": [339, 0.5], "1784": [340, 0.5], "1785": [341, 0.5], "1786": [342, 0.5], "1788": [344, 0.5], "1789": [345, 0.5], "1794": [350, 0.5], "1796": [351, 0.5], "1797": [352, 0.5], "1798": [353, 0.5], "1800": [355, 0.5], "1801": [356, 0.5], "1802": [357, 0.5], "1803": [358, 0.5], "1805": [360, 0.5], "1806": [361, 0.5], "1807": [362, 0.5], "1808": [363, 0.5], "1809": [364, 0.5], "1810": [365, 0.5], "1812": [367, 0.5], "1813": [368, 0.5], "1814": [369, 0.5], "1815": [370, 0.5], "1816": [371, 0.5], "1817": [372, 0.5], "1818": [373, 0.5], "1820": [375, 0.5], "1821": [376, 0.5], "1826": [381, 0.5], "1828": [382, 0.5], "1829": [383, 0.5], "1830": [384, 0.5], "1832": [386, 0.5], "1833": [387, 0.5], "1834": [388, 0.5], "1835": [389, 0.5], "1837": [391, 0.5], "1838": [392, 0.5], "1839": [393, 0.5], "1840": [394, 0.5], "1841": [395, 0.5], "1842": [396, 0.5], "1844": [398, 0.5], "1845": [399, 0.5], "1846": [400, 0.5], "1847": [401, 0.5], "1848": [402, 0.5], "1849": [403, 0.5], "1850": [404, 0.5], "1852": [406, 0.5], "1853": [407, 0.5], "1858": [412, 0.5], "1860": [413, 0.5], "1861": [414, 0.5], "1862": [415, 0.5], "1864": [417, 0.5], "1865": [418, 0.5], "1866": [419, 0.5], "1867": [420, 0.5], "1869": [422, 0.5], "1870": [423, 0.5], "1871": [424, 0.5], "1872": [425, 0.5], "1873": [426, 0.5], "1874": [427, 0.5], "1876": [429, 0.5], "1877": [430, 0.5], "1878": [431, 0.5], "1879": [432, 0.5], "1880": [433, 0.5], "1881": [434, 0.5], "1882": [435, 0.5], "1884": [437, 0.5], "1885": [438, 0.5], "1890": [443, 0.5], "1901": [445, 0.5], "1902": [446, 0.5], "1903": [447, 0.5], "1904": [448, 0.5], "1905": [449, 0.5], "1906": [450, 0.5], "1907": [451, 0.5], "1908": [452, 0.5], "1909": [453, 0.5], "1911": [455, 0.5], "1912": [456, 0.5], "1913": [457, 0.5], "1914": [458, 0.5], "1915": [459, 0.5], "1917": [461, 0.5], "1918": [462, 0.5], "1919": [463, 0.5], "1920": [464, 0.5], "1921": [465, 0.5], "1922": [466, 0.5], "1923": [467, 0.5], "1924": [468, 0.5], "1925": [469, 0.5], "1927": [471, 0.5], "1928": [472, 0.5], "1929": [473, 0.5], "1930": [474, 0.5], "1931": [475, 0.5], "1933": [477, 0.5], "1934": [478, 0.5], "1935": [479, 0.5], "1936": [480, 0.5], "1937": [481, 0.5], "1938": [482, 0.5], "1939": [483, 0.5], "1940": [484, 0.5], "1941": [485, 0.5], "1943": [487, 0.5], "1944": [488, 0.5], "1945": [489, 0.5], "1946": [490, 0.5], "1947": [491, 0.5], "1949": [493, 0.5], "1950": [494, 0.5], "1951": [495, 0.5], "1952": [496, 0.5], "1953": [497, 0.5], "1954": [498, 0.5], "1955": [499, 0.5], "1956": [500, 0.5], "1957": [501, 0.5], "1959": [503, 0.5], "1960": [504, 0.5], "1961": [505, 0.5], "1962": [506, 0.5], "1963": [507, 0.5], "1965": [509, 0.5], "1966": [510, 0.5], "1967": [511, 0.5], "1968": [512, 0.5], "1969": [513, 0.5], "1970": [514, 0.5], "1971": [515, 0.5], "1972": [516, 0.5], "1973": [517, 0.5], "1975": [519, 0.5], "1976": [520, 0.5], "1977": [521, 0.5], "1978": [522, 0.5], "1979": [523, 0.5], "1981": [525, 0.5], "1982": [526, 0.5], "1983": [527, 0.5], "1984": [528, 0.5], "1985": [529, 0.5], "1986": [530, 0.5], "1987": [531, 0.5], "1988": [532, 0.5], "1989": [533, 0.5], "1991": [535, 0.5], "1992": [536, 0.5], "1993": [537, 0.5], "1994": [538, 0.5], "1995": [539, 0.5], "2100": [540, 0.5], "2101": [541, 0.5], "2102": [542, 0.5], "2103": [543, 0.5], "2104": [544, 0.5], "2105": [545, 0.5], "2106": [546, 0.5], "2107": [547, 0.5], "2108": [548, 0.5], "2109": [549, 0.5], "2111": [551, 0.5], "2112": [552, 0.5], "2113": [553, 0.5], "2114": [554, 0.5], "2115": [555, 0.5], "2116": [556, 0.5], "2117": [557, 0.5], "2118": [558, 0.5], "2119": [559, 0.5], "2120": [560, 0.5], "2121": [561, 0.5], "2122": [562, 0.5], "2123": [563, 0.5], "2124": [564, 0.5], "2125": [565, 0.5], "2127": [567, 0.5], "2128": [568, 0.5], "2129": [569, 0.5], "2130": [570, 0.5], "2131": [571, 0.5], "2132": [572, 0.5], "2133": [573, 0.5], "2134": [574, 0.5], "2135": [575, 0.5], "2136": [576, 0.5], "2137": [577, 0.5], "2138": [578, 0.5], "2139": [579, 0.5], "2140": [580, 0.5], "2141": [581, 0.5], "2143": [583, 0.5], "2144": [584, 0.5], "2145": [585, 0.5], "2146": [586, 0.5], "2147": [587, 0.5], "2148": [588, 0.5], "2149": [589, 0.5], "2150": [590, 0.5], "2151": [591, 0.5], "2152": [592, 0.5], "2153": [593, 0.5], "2154": [594, 0.5], "2155": [595, 0.5], "2156": [596, 0.5], "2157": [597, 0.5], "2159": [599, 0.5], "2160": [600, 0.5], "2161": [601, 0.5], "2162": [602, 0.5], "2163": [603, 0.5], "2164": [604, 0.5], "2165": [605, 0.5], "2166": [606, 0.5], "2167": [607, 0.5], "2168": [608, 0.5], "2169": [609, 0.5], "2170": [610, 0.5], "2171": [611, 0.5], "2172": [612, 0.5], "2173": [613, 0.5], "2175": [615, 0.5], "2176": [616, 0.5], "2177": [617, 0.5], "2178": [618, 0.5], "2179": [619, 0.5], "2180": [620, 0.5], "2181": [621, 0.5], "2182": [622, 0.5], "2183": [623, 0.5], "2184": [624, 0.5], "2185": [625, 0.5], "2186": [626, 0.5], "2187": [627, 0.5], "2188": [628, 0.5], "2189": [629, 0.5], "2191": [631, 0.5], "2192": [632, 0.5], "2193": [633, 0.5], "2194": [634, 0.5], "2195": [635, 0.5], "2201": [637, 0.5], "2202": [638, 0.5], "2203": [639, 0.5], "2204": [640, 0.5], "2205": [641, 0.5], "2206": [642, 0.5], "2207": [643, 0.5], "2208": [644, 0.5], "2209": [645, 0.5], "2210": [646, 0.5], "2211": [647, 0.5], "2212": [648, 0.5], "2213": [649, 0.5], "2214": [650, 0.5], "2215": [651, 0.5], "2217": [653, 0.5], "2218": [654, 0.5], "2219": [655, 0.5], "2220": [656, 0.5], "2221": [657, 0.5], "2222": [658, 0.5], "2223": [659, 0.5], "2224": [660, 0.5], "2225": [661, 0.5], "2226": [662, 0.5], "2227": [663, 0.5], "2228": [664, 0.5], "2229": [665, 0.5], "2230": [666, 0.5], "2231": [667, 0.5], "2233": [669, 0.5], "2234": [670, 0.5], "2235": [671, 0.5], "2236": [672, 0.5], "2237": [673, 0.5], "2238": [674, 0.5], "2239": [675, 0.5], "2240": [676, 0.5], "2241": [677, 0.5], "2242": [678, 0.5], "2243": [679, 0.5], "2244": [680, 0.5], "2245": [681, 0.5], "2246": [682, 0.5], "2247": [683, 0.5], "2249": [685, 0.5], "2250": [686, 0.5], "2251": [687, 0.5], "2252": [688, 0.5], "2253": [689, 0.5], "2254": [690, 0.5], "2255": [691, 0.5], "2256": [692, 0.5], "2257": [693, 0.5], "2258": [694, 0.5], "2259": [695, 0.5], "2260": [696, 0.5], "2261": [697, 0.5], "2262": [698, 0.5], "2263": [699, 0.5], "2265": [701, 0.5], "2266": [702, 0.5], "2267": [703, 0.5], "2268": [704, 0.5], "2269": [705, 0.5], "2270": [706, 0.5], "2271": [707, 0.5], "2272": [708, 0.5], "2273": [709, 0.5], "2274": [710, 0.5], "2275": [711, 0.5], "2276": [712, 0.5], "2277": [713, 0.5], "2278": [714, 0.5], "2279": [715, 0.5], "2281": [717, 0.5], "2282": [718, 0.5], "2283": [719, 0.5], "2284": [720, 0.5], "2285": [721, 0.5], "2286": [722, 0.5], "2287": [723, 0.5], "2288": [724, 0.5], "2289": [725, 0.5], "2290": [726, 0.5], "2291": [727, 0.5], "2292": [728, 0.5], "2293": [729, 0.5], "2294": [730, 0.5], "2295": [731, 0.5], "2301": [733, 0.5], "2302": [734, 0.5], "2303": [735, 0.5], "2304": [736, 0.5], "2305": [737, 0.5], "2306": [738, 0.5], "2307": [739, 0.5], "2308": [740, 0.5], "2309": [741, 0.5], "2310": [742, 0.5], "2311": [743, 0.5], "2312": [744, 0.5], "2313": [745, 0.5], "2314": [746, 0.5], "2315": [747, 0.5], "2317": [749, 0.5], "2318": [750, 0.5], "2319": [751, 0.5], "2320": [752, 0.5], "2321": [753, 0.5], "2322": [754, 0.5], "2323": [755, 0.5], "2324": [756, 0.5], "2325": [757, 0.5], "2326": [758, 0.5], "2327": [759, 0.5], "2328": [760, 0.5], "2329": [761, 0.5], "2330": [762, 0.5], "2331": [763, 0.5], "2333": [765, 0.5], "2334": [766, 0.5], "2335": [767, 0.5], "2336": [768, 0.5], "2337": [769, 0.5], "2338": [770, 0.5], "2339": [771, 0.5], "2340": [772, 0.5], "2341": [773, 0.5], "2342": [774, 0.5], "2343": [775, 0.5], "2344": [776, 0.5], "2345": [777, 0.5], "2346": [778, 0.5], "2347": [779, 0.5], "2349": [781, 0.5], "2350": [782, 0.5], "2351": [783, 0.5], "2352": [784, 0.5], "2353": [785, 0.5], "2354": [786, 0.5], "2355": [787, 0.5], "2356": [788, 0.5], "2357": [789, 0.5], "2358": [790, 0.5], "2359": [791, 0.5], "2360": [792, 0.5], "2361": [793, 0.5], "2362": [794, 0.5], "2363": [795, 0.5], "2365": [797, 0.5], "2366": [798, 0.5], "2367": [799, 0.5], "2368": [800, 0.5], "2369": [801, 0.5], "2370": [802, 0.5], "2371": [803, 0.5], "2372": [804, 0.5], "2373": [805, 0.5], "2374": [806, 0.5], "2375": [807, 0.5], "2376": [808, 0.5], "2377": [809, 0.5], "2378": [810, 0.5], "2379": [811, 0.5], "2381": [813, 0.5], "2382": [814, 0.5], "2383": [815, 0.5], "2384": [816, 0.5], "2385": [817, 0.5], "2386": [818, 0.5], "2387": [819, 0.5], "2388": [820, 0.5], "2389": [821, 0.5], "2390": [822, 0.5], "2391": [823, 0.5], "2392": [824, 0.5], "2393": [825, 0.5], "2394": [826, 0.5], "2395": [827, 0.5], "2400": [828, 0.5], "2401": [829, 0.5], "2402": [830, 0.5], "2403": [831, 0.5], "2404": [832, 0.5], "2405": [833, 0.5], "2406": [834, 0.5], "2407": [835, 0.5], "2408": [836, 0.5], "2409": [837, 0.5], "2410": [838, 0.5], "2411": [839, 0.5], "2502": [926, 0.5], "2503": [927, 0.5], "2504": [928, 0.5], "2505": [929, 0.5], "2506": [930, 0.5], "2507": [931, 0.5], "2508": [932, 0.5], "2509": [933, 0.5], "2510": [934, 0.5], "2511": [935, 0.5], "2512": [936, 0.5], "2513": [937, 0.5], "2514": [938, 0.5], "2416": [844, 0.5], "2417": [845, 0.5], "2418": [846, 0.5], "2419": [847, 0.5], "2420": [848, 0.5], "2421": [849, 0.5], "2422": [850, 0.5], "2423": [851, 0.5], "2424": [852, 0.5], "2425": [853, 0.5], "2426": [854, 0.5], "2427": [855, 0.5], "2518": [942, 0.5], "2519": [943, 0.5], "2520": [944, 0.5], "2521": [945, 0.5], "2522": [946, 0.5], "2523": [947, 0.5], "2524": [948, 0.5], "2525": [949, 0.5], "2526": [950, 0.5], "2527": [951, 0.5], "2528": [952, 0.5], "2529": [953, 0.5], "2530": [954, 0.5], "2432": [860, 0.5], "2433": [861, 0.5], "2434": [862, 0.5], "2435": [863, 0.5], "2436": [864, 0.5], "2437": [865, 0.5], "2438": [866, 0.5], "2439": [867, 0.5], "2440": [868, 0.5], "2441": [869, 0.5], "2442": [870, 0.5], "2443": [871, 0.5], "2534": [958, 0.5], "2535": [959, 0.5], "2536": [960, 0.5], "2537": [961, 0.5], "2538": [962, 0.5], "2539": [963, 0.5], "2540": [964, 0.5], "2541": [965, 0.5], "2542": [966, 0.5], "2543": [967, 0.5], "2544": [968, 0.5], "2545": [969, 0.5], "2546": [970, 0.5], "2448": [876, 0.5], "2449": [877, 0.5], "2450": [878, 0.5], "2451": [879, 0.5], "2452": [880, 0.5], "2453": [881, 0.5], "2454": [882, 0.5], "2455": [883, 0.5], "2456": [884, 0.5], "2457": [885, 0.5], "2458": [886, 0.5], "2459": [887, 0.5], "2550": [974, 0.5], "2551": [975, 0.5], "2552": [976, 0.5], "2553": [977, 0.5], "2554": [978, 0.5], "2555": [979, 0.5], "2556": [980, 0.5], "2557": [981, 0.5], "2558": [982, 0.5], "2559": [983, 0.5], "2560": [984, 0.5], "2561": [985, 0.5], "2562": [986, 0.5], "2464": [892, 0.5], "2465": [893, 0.5], "2466": [894, 0.5], "2467": [895, 0.5], "2468": [896, 0.5], "2469": [897, 0.5], "2470": [898, 0.5], "2471": [899, 0.5], "2472": [900, 0.5], "2473": [901, 0.5], "2474": [902, 0.5], "2475": [903, 0.5], "2566": [990, 0.5], "2567": [991, 0.5], "2568": [992, 0.5], "2569": [993, 0.5], "2570": [994, 0.5], "2571": [995, 0.5], "2572": [996, 0.5], "2573": [997, 0.5], "2574": [998, 0.5], "2575": [999, 0.5], "2576": [1000, 0.5], "2577": [1001, 0.5], "2578": [1002, 0.5], "2480": [908, 0.5], "2481": [909, 0.5], "2482": [910, 0.5], "2483": [911, 0.5], "2484": [912, 0.5], "2485": [913, 0.5], "2486": [914, 0.5], "2487": [915, 0.5], "2488": [916, 0.5], "2489": [917, 0.5], "2490": [918, 0.5], "2491": [919, 0.5], "2582": [1006, 0.5], "2583": [1007, 0.5], "2584": [1008, 0.5], "2585": [1009, 0.5], "2586": [1010, 0.5], "2587": [1011, 0.5], "2588": [1012, 0.5], "2589": [1013, 0.5], "2590": [1014, 0.5], "2591": [1015, 0.5], "2592": [1016, 0.5], "2593": [1017, 0.5], "2594": [1018, 0.5], "2600": [1020, 0.5], "2601": [1021, 0.5], "2602": [1022, 0.5], "2603": [1023, 0.5], "2604": [1024, 0.5], "2605": [1025, 0.5], "2606": [1026, 0.5], "2607": [1027, 0.5], "2608": [1028, 0.5], "2609": [1029, 0.5], "2610": [1030, 0.5], "2611": [1031, 0.5], "2612": [1032, 0.5], "2613": [1033, 0.5], "2614": [1034, 0.5], "2615": [1035, 0.5], "2616": [1036, 0.5], "2617": [1037, 0.5], "2618": [1038, 0.5], "2619": [1039, 0.5], "2620": [1040, 0.5], "2621": [1041, 0.5], "2622": [1042, 0.5], "2623": [1043, 0.5], "2624": [1044, 0.5], "2625": [1045, 0.5], "2626": [1046, 0.5], "2627": [1047, 0.5], "2628": [1048, 0.5], "2629": [1049, 0.5], "2630": [1050, 0.5], "2631": [1051, 0.5], "2632": [1052, 0.5], "2633": [1053, 0.5], "2634": [1054, 0.5], "2635": [1055, 0.5], "2636": [1056, 0.5], "2637": [1057, 0.5], "2638": [1058, 0.5], "2639": [1059, 0.5], "2640": [1060, 0.5], "2641": [1061, 0.5], "2642": [1062, 0.5], "2643": [1063, 0.5], "2644": [1064, 0.5], "2645": [1065, 0.5], "2646": [1066, 0.5], "2647": [1067, 0.5], "2648": [1068, 0.5], "2649": [1069, 0.5], "2650": [1070, 0.5], "2651": [1071, 0.5], "2652": [1072, 0.5], "2653": [1073, 0.5], "2654": [1074, 0.5], "2655": [1075, 0.5], "2656": [1076, 0.5], "2657": [1077, 0.5], "2658": [1078, 0.5], "2659": [1079, 0.5], "2660": [1080, 0.5], "2661": [1081, 0.5], "2662": [1082, 0.5], "2663": [1083, 0.5], "2664": [1084, 0.5], "2665": [1085, 0.5], "2666": [1086, 0.5], "2667": [1087, 0.5], "2668": [1088, 0.5], "2669": [1089, 0.5], "2670": [1090, 0.5], "2671": [1091, 0.5], "2672": [1092, 0.5], "2673": [1093, 0.5], "2674": [1094, 0.5], "2675": [1095, 0.5], "2676": [1096, 0.5], "2677": [1097, 0.5], "2678": [1098, 0.5], "2679": [1099, 0.5], "2680": [1100, 0.5], "2681": [1101, 0.5], "2682": [1102, 0.5], "2683": [1103, 0.5], "2684": [1104, 0.5], "2685": [1105, 0.5], "2686": [1106, 0.5], "2687": [1107, 0.5], "2688": [1108, 0.5], "2689": [1109, 0.5], "2690": [1110, 0.5], "2691": [1111, 0.5], "2692": [1112, 0.5], "2693": [1113, 0.5], "2694": [1114, 0.5], "2695": [1115, 0.5], "2701": [1117, 0.5], "2702": [1118, 0.5], "2703": [1119, 0.5], "2704": [1120, 0.5], "2705": [1121, 0.5], "2706": [1122, 0.5], "2707": [1123, 0.5], "2708": [1124, 0.5], "2709": [1125, 0.5], "2710": [1126, 0.5], "2711": [1127, 0.5], "2712": [1128, 0.5], "2713": [1129, 0.5], "2714": [1130, 0.5], "2715": [1131, 0.5], "2717": [1133, 0.5], "2718": [1134, 0.5], "2719": [1135, 0.5], "2720": [1136, 0.5], "2721": [1137, 0.5], "2722": [1138, 0.5], "2723": [1139, 0.5], "2724": [1140, 0.5], "2725": [1141, 0.5], "2726": [1142, 0.5], "2727": [1143, 0.5], "2728": [1144, 0.5], "2729": [1145, 0.5], "2730": [1146, 0.5], "2731": [1147, 0.5], "2733": [1149, 0.5], "2734": [1150, 0.5], "2735": [1151, 0.5], "2736": [1152, 0.5], "2737": [1153, 0.5], "2738": [1154, 0.5], "2739": [1155, 0.5], "2740": [1156, 0.5], "2741": [1157, 0.5], "2742": [1158, 0.5], "2743": [1159, 0.5], "2744": [1160, 0.5], "2745": [1161, 0.5], "2746": [1162, 0.5], "2747": [1163, 0.5], "2749": [1165, 0.5], "2750": [1166, 0.5], "2751": [1167, 0.5], "2752": [1168, 0.5], "2753": [1169, 0.5], "2754": [1170, 0.5], "2755": [1171, 0.5], "2756": [1172, 0.5], "2757": [1173, 0.5], "2758": [1174, 0.5], "2759": [1175, 0.5], "2760": [1176, 0.5], "2761": [1177, 0.5], "2762": [1178, 0.5], "2763": [1179, 0.5], "2765": [1181, 0.5], "2766": [1182, 0.5], "2767": [1183, 0.5], "2768": [1184, 0.5], "2769": [1185, 0.5], "2770": [1186, 0.5], "2771": [1187, 0.5], "2772": [1188, 0.5], "2773": [1189, 0.5], "2774": [1190, 0.5], "2775": [1191, 0.5], "2776": [1192, 0.5], "2777": [1193, 0.5], "2778": [1194, 0.5], "2779": [1195, 0.5], "2781": [1197, 0.5], "2782": [1198, 0.5], "2783": [1199, 0.5], "2784": [1200, 0.5], "2785": [1201, 0.5], "2786": [1202, 0.5], "2787": [1203, 0.5], "2788": [1204, 0.5], "2789": [1205, 0.5], "2790": [1206, 0.5], "2791": [1207, 0.5], "2792": [1208, 0.5], "2793": [1209, 0.5], "2794": [1210, 0.5], "2795": [1211, 0.5], "2800": [1212, 0.5], "2801": [1213, 0.5], "2802": [1214, 0.5], "2803": [1215, 0.5], "2804": [1216, 0.5], "2805": [1217, 0.5], "2807": [1219, 0.5], "2808": [1220, 0.5], "2809": [1221, 0.5], "2816": [1228, 0.5], "2817": [1229, 0.5], "2818": [1230, 0.5], "2819": [1231, 0.5], "2820": [1232, 0.5], "2821": [1233, 0.5], "2823": [1235, 0.5], "2824": [1236, 0.5], "2825": [1237, 0.5], "2832": [1244, 0.5], "2833": [1245, 0.5], "2834": [1246, 0.5], "2835": [1247, 0.5], "2836": [1248, 0.5], "2837": [1249, 0.5], "2839": [1251, 0.5], "2840": [1252, 0.5], "2841": [1253, 0.5], "2848": [1260, 0.5], "2849": [1261, 0.5], "2850": [1262, 0.5], "2851": [1263, 0.5], "2852": [1264, 0.5], "2853": [1265, 0.5], "2855": [1267, 0.5], "2856": [1268, 0.5], "2857": [1269, 0.5], "2864": [1276, 0.5], "2865": [1277, 0.5], "2866": [1278, 0.5], "2867": [1279, 0.5], "2868": [1280, 0.5], "2869": [1281, 0.5], "2871": [1283, 0.5], "2872": [1284, 0.5], "2873": [1285, 0.5], "2880": [1292, 0.5], "2881": [1293, 0.5], "2882": [1294, 0.5], "2883": [1295, 0.5], "2884": [1296, 0.5], "2885": [1297, 0.5], "2887": [1299, 0.5], "2888": [1300, 0.5], "2889": [1301, 0.5], "2900": [1308, 0.125], "2901": [1309, 0.125], "2902": [1310, 0.125], "2903": [1311, 0.125], "2904": [1312, 0.125], "2905": [1313, 0.125], "2906": [1314, 0.125], "2907": [1315, 0.125], "2908": [1316, 0.125], "2909": [1317, 0.125], "2910": [1318, 0.125], "2911": [1319, 0.125], "2912": [1320, 0.125], "2913": [1321, 0.125], "2914": [1322, 0.125], "2915": [1323, 0.125], "2916": [1324, 0.125], "2917": [1325, 0.125], "2918": [1326, 0.125], "2919": [1327, 0.125], "2920": [1328, 0.125], "2921": [1329, 0.125], "2922": [1330, 0.125], "2923": [1331, 0.125], "2924": [1332, 0.125], "2925": [1333, 0.125], "2926": [1334, 0.125], "2927": [1335, 0.125], "2928": [1336, 0.125], "2929": [1337, 0.125], "2930": [1338, 0.125], "2931": [1339, 0.125], "2932": [1340, 0.125], "2933": [1341, 0.125], "2934": [1342, 0.125], "2935": [1343, 0.125], "5300": [1344, 0.5], "5301": [1345, 0.5], "5302": [1346, 0.5], "5303": [1347, 0.5], "5304": [1348, 0.5], "5305": [1349, 0.5], "5306": [1350, 0.5], "5307": [1351, 0.5], "5308": [1352, 0.5], "5309": [1353, 0.5], "5310": [1354, 0.5], "5311": [1355, 0.5], "5312": [1356, 0.5], "5313": [1357, 0.5], "5314": [1358, 0.5], "5315": [1359, 0.5], "5316": [1360, 0.5], "5317": [1361, 0.5], "5318": [1362, 0.5], "5319": [1363, 0.5], "5320": [1364, 0.5], "5321": [1365, 0.5], "5322": [1366, 0.5], "5323": [1367, 0.5], "5324": [1368, 0.5], "5325": [1369, 0.5], "5326": [1370, 0.5], "5327": [1371, 0.5], "5328": [1372, 0.5], "5329": [1373, 0.5], "5330": [1374, 0.5], "5331": [1375, 0.5], "5332": [1376, 0.5], "5333": [1377, 0.5], "5334": [1378, 0.5], "5335": [1379, 0.5], "5336": [1380, 0.5], "5337": [1381, 0.5], "5338": [1382, 0.5], "5339": [1383, 0.5], "5340": [1384, 0.5], "5341": [1385, 0.5], "5342": [1386, 0.5], "5343": [1387, 0.5], "5344": [1388, 0.5], "5345": [1389, 0.5], "5346": [1390, 0.5], "5347": [1391, 0.5], "5348": [1392, 0.5], "5349": [1393, 0.5], "5350": [1394, 0.5], "5351": [1395, 0.5], "5352": [1396, 0.5], "5353": [1397, 0.5], "5354": [1398, 0.5], "5355": [1399, 0.5], "5356": [1400, 0.5], "5357": [1401, 0.5], "5358": [1402, 0.5], "5359": [1403, 0.5], "5360": [1404, 0.5], "5361": [1405, 0.5], "5362": [1406, 0.5], "5363": [1407, 0.5], "5364": [1408, 0.5], "5365": [1409, 0.5], "5366": [1410, 0.5], "5367": [1411, 0.5], "5368": [1412, 0.5], "5369": [1413, 0.5], "5370": [1414, 0.5], "5371": [1415, 0.5], "5372": [1416, 0.5], "5373": [1417, 0.5], "5374": [1418, 0.5], "5375": [1419, 0.5], "5376": [1420, 0.5], "5377": [1421, 0.5], "5378": [1422, 0.5], "5379": [1423, 0.5], "5380": [1424, 0.5], "5381": [1425, 0.5], "5382": [1426, 0.5], "5383": [1427, 0.5], "5384": [1428, 0.5], "5385": [1429, 0.5], "5386": [1430, 0.5], "5387": [1431, 0.5], "5388": [1432, 0.5], "5389": [1433, 0.5], "5390": [1434, 0.5], "5391": [1435, 0.5], "5392": [1436, 0.5], "5393": [1437, 0.5], "5394": [1438, 0.5], "5395": [1439, 0.5], "5396": [1440, 0.5], "5397": [1441, 0.5], "5398": [1442, 0.5], "5399": [1443, 0.5], "5400": [1444, 0.5], "5401": [1445, 0.5], "5402": [1446, 0.5], "5403": [1447, 0.5], "5404": [1448, 0.5], "5405": [1449, 0.5], "5406": [1450, 0.5], "5407": [1451, 0.5], "5408": [1452, 0.5], "5409": [1453, 0.5], "5410": [1454, 0.5], "5411": [1455, 0.5], "5412": [1456, 0.5], "5413": [1457, 0.5], "5414": [1458, 0.5], "5415": [1459, 0.5], "5416": [1460, 0.5], "5417": [1461, 0.5], "5418": [1462, 0.5], "5419": [1463, 0.5], "5420": [1464, 0.5], "5421": [1465, 0.5], "5422": [1466, 0.5], "5423": [1467, 0.5], "5424": [1468, 0.5], "5425": [1469, 0.5], "5426": [1470, 0.5], "5427": [1471, 0.5], "5428": [1472, 0.5], "5429": [1473, 0.5], "5430": [1474, 0.5], "5431": [1475, 0.5], "5432": [1476, 0.5], "5433": [1477, 0.5], "5434": [1478, 0.5], "5435": [1479, 0.5], "5436": [1480, 0.5], "5437": [1481, 0.5], "5438": [1482, 0.5], "5439": [1483, 0.5], "5440": [1484, 0.5], "5441": [1485, 0.5], "5442": [1486, 0.5], "5443": [1487, 0.5], "3502": [1490, 0.5], "3503": [1491, 0.5], "3504": [1492, 0.5], "3505": [1493, 0.5], "3506": [1494, 0.5], "3507": [1495, 0.5], "3508": [1496, 0.5], "3509": [1497, 0.5], "3510": [1498, 0.5], "3513": [1501, 0.5], "3514": [1502, 0.5], "3515": [1503, 0.5], "3518": [1506, 0.5], "3519": [1507, 0.5], "3520": [1508, 0.5], "3521": [1509, 0.5], "3522": [1510, 0.5], "3523": [1511, 0.5], "3524": [1512, 0.5], "3525": [1513, 0.5], "3526": [1514, 0.5], "3529": [1517, 0.5], "3530": [1518, 0.5], "3531": [1519, 0.5], "3534": [1522, 0.5], "3535": [1523, 0.5], "3536": [1524, 0.5], "3537": [1525, 0.5], "3538": [1526, 0.5], "3539": [1527, 0.5], "3540": [1528, 0.5], "3541": [1529, 0.5], "3542": [1530, 0.5], "3545": [1533, 0.5], "3546": [1534, 0.5], "3547": [1535, 0.5], "3550": [1538, 0.5], "3551": [1539, 0.5], "3552": [1540, 0.5], "3553": [1541, 0.5], "3554": [1542, 0.5], "3555": [1543, 0.5], "3556": [1544, 0.5], "3557": [1545, 0.5], "3558": [1546, 0.5], "3561": [1549, 0.5], "3562": [1550, 0.5], "3563": [1551, 0.5], "3566": [1554, 0.5], "3567": [1555, 0.5], "3568": [1556, 0.5], "3569": [1557, 0.5], "3570": [1558, 0.5], "3571": [1559, 0.5], "3572": [1560, 0.5], "3573": [1561, 0.5], "3574": [1562, 0.5], "3577": [1565, 0.5], "3578": [1566, 0.5], "3579": [1567, 0.5], "3582": [1570, 0.5], "3583": [1571, 0.5], "3584": [1572, 0.5], "3585": [1573, 0.5], "3586": [1574, 0.5], "3587": [1575, 0.5], "3588": [1576, 0.5], "3589": [1577, 0.5], "3590": [1578, 0.5], "3593": [1581, 0.5], "3594": [1582, 0.5], "3595": [1583, 0.5], "18": [1584, 0.5], "19": [1585, 0.5], "20": [1586, 0.5], "21": [1587, 0.5], "22": [1588, 0.5], "36": [1590, 0.5], "45": [1591, 0.5], "46": [1592, 0.5], "175": [1594, 0.5], "189": [1595, 0.5], "222": [1597, 0.5], "248": [1598, 0.5], "250": [1599, 0.5], "252": [1600, 0.5], "254": [1601, 0.5], "256": [1602, 0.5], "258": [1603, 0.5], "260": [1604, 0.5], "262": [1605, 0.5], "264": [1606, 0.5], "266": [1607, 0.5], "267": [1608, 0.5], "268": [1609, 0.5], "269": [1610, 0.5], "270": [1611, 0.5], "271": [1612, 0.5], "272": [1613, 0.5], "273": [1614, 0.5], "274": [1615, 0.5], "275": [1616, 0.5], "276": [1617, 0.5], "277": [1618, 0.5], "278": [1619, 0.5], "279": [1620, 0.5], "280": [1621, 0.5], "281": [1622, 0.5], "282": [1623, 0.5], "283": [1624, 0.5], "284": [1625, 0.5], "285": [1626, 0.5], "286": [1627, 0.5], "287": [1628, 0.5], "288": [1629, 0.5], "289": [1630, 0.5], "290": [1631, 0.5], "291": [1632, 0.5], "292": [1633, 0.5], "293": [1634, 0.5], "294": [1635, 0.5], "295": [1636, 0.5], "296": [1637, 0.5], "297": [1638, 0.5], "298": [1639, 0.5], "299": [1640, 0.5], "300": [1641, 0.5], "301": [1642, 0.5], "302": [1643, 0.5], "303": [1644, 0.5], "304": [1645, 0.5], "305": [1646, 0.5], "306": [1647, 0.5], "522": [1648, 0.5], "1008": [1652, 0.5], "1014": [1654, 0.5], "1015": [1655, 0.5], "1016": [1656, 0.5], "1022": [1659, 0.5], "1028": [1663, 0.5], "1029": [1664, 0.5], "1034": [1667, 0.5], "1035": [1668, 0.5], "1036": [1669, 0.5], "1037": [1670, 0.5], "1038": [1671, 0.5], "1039": [1672, 0.5], "1040": [1673, 0.5], "1041": [1674, 0.5], "1044": [1676, 0.5], "1049": [1680, 0.5], "1050": [1681, 0.5], "1051": [1682, 0.5], "1052": [1683, 0.5], "1053": [1684, 0.5], "1054": [1685, 0.5], "1058": [1686, 0.5], "1059": [1687, 0.5], "1060": [1688, 0.5], "1061": [1689, 0.5], "1062": [1690, 0.5], "1063": [1691, 0.5], "1072": [1695, 0.5], "1078": [1697, 0.5], "1079": [1698, 0.5], "1080": [1699, 0.5], "1086": [1702, 0.5], "1092": [1706, 0.5], "1093": [1707, 0.5], "1098": [1710, 0.5], "1099": [1711, 0.5], "1100": [1712, 0.5], "1101": [1713, 0.5], "1102": [1714, 0.5], "1103": [1715, 0.5], "1104": [1716, 0.5], "1105": [1717, 0.5], "1108": [1719, 0.5], "1113": [1723, 0.5], "1114": [1724, 0.5], "1115": [1725, 0.5], "1116": [1726, 0.5], "1117": [1727, 0.5], "1118": [1728, 0.5], "1122": [1729, 0.5], "1123": [1730, 0.5], "1124": [1731, 0.5], "1125": [1732, 0.5], "1126": [1733, 0.5], "1127": [1734, 0.5], "1136": [1738, 0.5], "1142": [1740, 0.5], "1143": [1741, 0.5], "1144": [1742, 0.5], "1150": [1745, 0.5], "1156": [1749, 0.5], "1157": [1750, 0.5], "1162": [1753, 0.5], "1163": [1754, 0.5], "1164": [1755, 0.5], "1165": [1756, 0.5], "1166": [1757, 0.5], "1167": [1758, 0.5], "1168": [1759, 0.5], "1169": [1760, 0.5], "1172": [1762, 0.5], "1177": [1766, 0.5], "1178": [1767, 0.5], "1179": [1768, 0.5], "1180": [1769, 0.5], "1181": [1770, 0.5], "1182": [1771, 0.5], "1186": [1772, 0.5], "1187": [1773, 0.5], "1188": [1774, 0.5], "1189": [1775, 0.5], "1190": [1776, 0.5], "1191": [1777, 0.5], "1200": [1781, 0.5], "1206": [1783, 0.5], "1207": [1784, 0.5], "1208": [1785, 0.5], "1214": [1788, 0.5], "1220": [1792, 0.5], "1221": [1793, 0.5], "1226": [1796, 0.5], "1227": [1797, 0.5], "1228": [1798, 0.5], "1229": [1799, 0.5], "1230": [1800, 0.5], "1231": [1801, 0.5], "1232": [1802, 0.5], "1233": [1803, 0.5], "1236": [1805, 0.5], "1241": [1809, 0.5], "1242": [1810, 0.5], "1243": [1811, 0.5], "1244": [1812, 0.5], "1245": [1813, 0.5], "1246": [1814, 0.5], "1250": [1815, 0.5], "1251": [1816, 0.5], "1252": [1817, 0.5], "1253": [1818, 0.5], "1254": [1819, 0.5], "1255": [1820, 0.5], "1264": [1824, 0.5], "1270": [1826, 0.5], "1271": [1827, 0.5], "1272": [1828, 0.5], "1278": [1831, 0.5], "1284": [1835, 0.5], "1285": [1836, 0.5], "1290": [1839, 0.5], "1291": [1840, 0.5], "1292": [1841, 0.5], "1293": [1842, 0.5], "1294": [1843, 0.5], "1295": [1844, 0.5], "1296": [1845, 0.5], "1297": [1846, 0.5], "1300": [1848, 0.5], "1305": [1852, 0.5], "1306": [1853, 0.5], "1307": [1854, 0.5], "1308": [1855, 0.5], "1309": [1856, 0.5], "1310": [1857, 0.5], "1314": [1858, 0.5], "1315": [1859, 0.5], "1316": [1860, 0.5], "1317": [1861, 0.5], "1318": [1862, 0.5], "1319": [1863, 0.5], "1328": [1867, 0.5], "1334": [1869, 0.5], "1335": [1870, 0.5], "1336": [1871, 0.5], "1342": [1874, 0.5], "1348": [1878, 0.5], "1349": [1879, 0.5], "1354": [1882, 0.5], "1355": [1883, 0.5], "1356": [1884, 0.5], "1357": [1885, 0.5], "1358": [1886, 0.5], "1359": [1887, 0.5], "1360": [1888, 0.5], "1361": [1889, 0.5], "1364": [1891, 0.5], "1369": [1895, 0.5], "1370": [1896, 0.5], "1371": [1897, 0.5], "1372": [1898, 0.5], "1373": [1899, 0.5], "1374": [1900, 0.5], "1378": [1901, 0.5], "1379": [1902, 0.5], "1380": [1903, 0.5], "1381": [1904, 0.5], "1382": [1905, 0.5], "1383": [1906, 0.5], "1600": [1907, 0.5], "1601": [1908, 0.5], "1604": [1909, 0.5], "1605": [1910, 0.5], "1608": [1911, 0.5], "1609": [1912, 0.5], "1612": [1913, 0.5], "1613": [1914, 0.5], "1616": [1915, 0.5], "1617": [1916, 0.5], "1620": [1917, 0.5], "1621": [1918, 0.5], "1624": [1919, 0.5], "1625": [1920, 0.5], "1628": [1921, 0.5], "1629": [1922, 0.5], "1632": [1923, 0.5], "1633": [1924, 0.5], "1636": [1925, 0.5], "1637": [1926, 0.5], "3000": [2809, 0.5], "3001": [2810, 0.5], "3002": [2811, 0.5], "3003": [2812, 0.5], "3004": [2813, 0.5], "3005": [2814, 0.5], "3006": [2815, 0.5], "3007": [2816, 0.5], "3008": [2817, 0.5], "3009": [2818, 0.5], "3010": [2819, 0.5], "3011": [2820, 0.5], "3012": [2821, 0.5], "3013": [2822, 0.5], "3014": [2823, 0.5], "3015": [2824, 0.5], "3016": [2825, 0.5], "3017": [2826, 0.5], "3018": [2827, 0.5], "3019": [2828, 0.5], "3020": [2829, 0.5], "3021": [2830, 0.5], "3022": [2831, 0.5], "3023": [2832, 0.5], "3024": [2833, 0.5], "3025": [2834, 0.5], "3026": [2835, 0.5], "3027": [2836, 0.5], "3028": [2837, 0.5], "3029": [2838, 0.5], "3030": [2839, 0.5], "3031": [2840, 0.5], "3032": [2841, 0.5], "3033": [2842, 0.5], "3034": [2843, 0.5], "3035": [2844, 0.5], "3036": [2845, 0.5], "3037": [2846, 0.5], "3038": [2847, 0.5], "3039": [2848, 0.5], "3040": [2849, 0.5], "3041": [2850, 0.5], "3042": [2851, 0.5], "3043": [2852, 0.5], "3044": [2853, 0.5], "3045": [2854, 0.5], "3046": [2855, 0.5], "3047": [2856, 0.5], "3048": [2857, 0.5], "3049": [2858, 0.5], "3050": [2859, 0.5], "3051": [2860, 0.5], "3052": [2861, 0.5], "3053": [2862, 0.5], "3054": [2863, 0.5], "3055": [2864, 0.5], "3056": [2865, 0.5], "3057": [2866, 0.5], "3058": [2867, 0.5], "3059": [2868, 0.5], "3202": [2869, 0.5], "3204": [2870, 0.5], "3205": [2871, 0.5], "3206": [2872, 0.5], "3207": [2873, 0.5], "3208": [2874, 0.5], "3209": [2875, 0.5], "3212": [2876, 0.5], "3214": [2877, 0.5], "3215": [2878, 0.5], "3216": [2879, 0.5], "3217": [2880, 0.5], "3218": [2881, 0.5], "3219": [2882, 0.5], "3222": [2883, 0.5], "3224": [2884, 0.5], "3225": [2885, 0.5], "3226": [2886, 0.5], "3227": [2887, 0.5], "3228": [2888, 0.5], "3229": [2889, 0.5], "3232": [2890, 0.5], "3234": [2891, 0.5], "3235": [2892, 0.5], "3236": [2893, 0.5], "3237": [2894, 0.5], "3238": [2895, 0.5], "3239": [2896, 0.5], "3242": [2897, 0.5], "3244": [2898, 0.5], "3245": [2899, 0.5], "3246": [2900, 0.5], "3247": [2901, 0.5], "3248": [2902, 0.5], "3249": [2903, 0.5], "3252": [2904, 0.5], "3254": [2905, 0.5], "3255": [2906, 0.5], "3256": [2907, 0.5], "3257": [2908, 0.5], "3258": [2909, 0.5], "3259": [2910, 0.5], "3262": [2911, 0.5], "3264": [2912, 0.5], "3265": [2913, 0.5], "3266": [2914, 0.5], "3267": [2915, 0.5], "3268": [2916, 0.5], "3269": [2917, 0.5], "3272": [2918, 0.5], "3274": [2919, 0.5], "3275": [2920, 0.5], "3276": [2921, 0.5], "3277": [2922, 0.5], "3278": [2923, 0.5], "3279": [2924, 0.5], "3282": [2925, 0.5], "3284": [2926, 0.5], "3285": [2927, 0.5], "3286": [2928, 0.5], "3287": [2929, 0.5], "3288": [2930, 0.5], "3289": [2931, 0.5], "3292": [2932, 0.5], "3294": [2933, 0.5], "3295": [2934, 0.5], "3296": [2935, 0.5], "3297": [2936, 0.5], "3298": [2937, 0.5], "3299": [2938, 0.5], "3302": [2939, 0.5], "3304": [2940, 0.5], "3305": [2941, 0.5], "3306": [2942, 0.5], "3307": [2943, 0.5], "3308": [2944, 0.5], "3309": [2945, 0.5], "3312": [2946, 0.5], "3314": [2947, 0.5], "3315": [2948, 0.5], "3316": [2949, 0.5], "3317": [2950, 0.5], "3318": [2951, 0.5], "3319": [2952, 0.5], "3322": [2953, 0.5], "3324": [2954, 0.5], "3325": [2955, 0.5], "3326": [2956, 0.5], "3327": [2957, 0.5], "3328": [2958, 0.5], "3329": [2959, 0.5], "3332": [2960, 0.5], "3334": [2961, 0.5], "3335": [2962, 0.5], "3336": [2963, 0.5], "3337": [2964, 0.5], "3338": [2965, 0.5], "3339": [2966, 0.5], "3342": [2967, 0.5], "3344": [2968, 0.5], "3345": [2969, 0.5], "3346": [2970, 0.5], "3347": [2971, 0.5], "3348": [2972, 0.5], "3349": [2973, 0.5], "3352": [2974, 0.5], "3354": [2975, 0.5], "3355": [2976, 0.5], "3356": [2977, 0.5], "3357": [2978, 0.5], "3358": [2979, 0.5], "3359": [2980, 0.5], "3362": [2981, 0.5], "3364": [2982, 0.5], "3365": [2983, 0.5], "3366": [2984, 0.5], "3367": [2985, 0.5], "3368": [2986, 0.5], "3369": [2987, 0.5], "3372": [2988, 0.5], "3374": [2989, 0.5], "3375": [2990, 0.5], "3376": [2991, 0.5], "3377": [2992, 0.5], "3378": [2993, 0.5], "3379": [2994, 0.5], "3617": [3067, 0.5], "3620": [3068, 0.5], "3649": [3069, 0.5], "3652": [3070, 0.5], "3681": [3071, 0.5], "3684": [3072, 0.5], "3713": [3073, 0.5], "3716": [3074, 0.5], "3745": [3075, 0.5], "3748": [3076, 0.5], "3777": [3077, 0.5], "3780": [3078, 0.5], "3809": [3079, 0.5], "3812": [3080, 0.5], "3841": [3081, 0.5], "3844": [3082, 0.5], "3873": [3083, 0.5], "3876": [3084, 0.5], "3905": [3085, 0.5], "3908": [3086, 0.5], "8002": [3087, 0.5], "8004": [3088, 0.5], "8005": [3089, 0.5], "8006": [3090, 0.5], "8007": [3091, 0.5], "8008": [3092, 0.5], "8009": [3093, 0.5], "8011": [3094, 0.5], "8012": [3095, 0.5], "8018": [3096, 0.5], "8020": [3097, 0.5], "8021": [3098, 0.5], "8022": [3099, 0.5], "8023": [3100, 0.5], "8024": [3101, 0.5], "8025": [3102, 0.5], "8027": [3103, 0.5], "8028": [3104, 0.5], "8034": [3105, 0.5], "8036": [3106, 0.5], "8037": [3107, 0.5], "8038": [3108, 0.5], "8039": [3109, 0.5], "8040": [3110, 0.5], "8041": [3111, 0.5], "8043": [3112, 0.5], "8044": [3113, 0.5], "8050": [3114, 0.5], "8052": [3115, 0.5], "8053": [3116, 0.5], "8054": [3117, 0.5], "8055": [3118, 0.5], "8056": [3119, 0.5], "8057": [3120, 0.5], "8059": [3121, 0.5], "8060": [3122, 0.5], "8066": [3123, 0.5], "8068": [3124, 0.5], "8069": [3125, 0.5], "8070": [3126, 0.5], "8071": [3127, 0.5], "8072": [3128, 0.5], "8073": [3129, 0.5], "8075": [3130, 0.5], "8076": [3131, 0.5], "8082": [3132, 0.5], "8084": [3133, 0.5], "8085": [3134, 0.5], "8086": [3135, 0.5], "8087": [3136, 0.5], "8088": [3137, 0.5], "8089": [3138, 0.5], "8091": [3139, 0.5], "8092": [3140, 0.5], "8098": [3141, 0.5], "8100": [3142, 0.5], "8101": [3143, 0.5], "8102": [3144, 0.5], "8103": [3145, 0.5], "8104": [3146, 0.5], "8105": [3147, 0.5], "8107": [3148, 0.5], "8108": [3149, 0.5], "8114": [3150, 0.5], "8116": [3151, 0.5], "8117": [3152, 0.5], "8118": [3153, 0.5], "8119": [3154, 0.5], "8120": [3155, 0.5], "8121": [3156, 0.5], "8123": [3157, 0.5], "8124": [3158, 0.5], "8130": [3159, 0.5], "8132": [3160, 0.5], "8133": [3161, 0.5], "8134": [3162, 0.5], "8135": [3163, 0.5], "8136": [3164, 0.5], "8137": [3165, 0.5], "8139": [3166, 0.5], "8140": [3167, 0.5], "8146": [3168, 0.5], "8148": [3169, 0.5], "8149": [3170, 0.5], "8150": [3171, 0.5], "8151": [3172, 0.5], "8152": [3173, 0.5], "8153": [3174, 0.5], "8155": [3175, 0.5], "8156": [3176, 0.5], "8162": [3177, 0.5], "8164": [3178, 0.5], "8165": [3179, 0.5], "8166": [3180, 0.5], "8167": [3181, 0.5], "8168": [3182, 0.5], "8169": [3183, 0.5], "8171": [3184, 0.5], "8172": [3185, 0.5], "8178": [3186, 0.5], "8180": [3187, 0.5], "8181": [3188, 0.5], "8182": [3189, 0.5], "8183": [3190, 0.5], "8184": [3191, 0.5], "8185": [3192, 0.5], "8187": [3193, 0.5], "8188": [3194, 0.5], "8194": [3195, 0.5], "8196": [3196, 0.5], "8197": [3197, 0.5], "8198": [3198, 0.5], "8199": [3199, 0.5], "8200": [3200, 0.5], "8201": [3201, 0.5], "8203": [3202, 0.5], "8204": [3203, 0.5], "8210": [3204, 0.5], "8212": [3205, 0.5], "8213": [3206, 0.5], "8214": [3207, 0.5], "8215": [3208, 0.5], "8216": [3209, 0.5], "8217": [3210, 0.5], "8219": [3211, 0.5], "8220": [3212, 0.5], "8226": [3213, 0.5], "8228": [3214, 0.5], "8229": [3215, 0.5], "8230": [3216, 0.5], "8231": [3217, 0.5], "8232": [3218, 0.5], "8233": [3219, 0.5], "8235": [3220, 0.5], "8236": [3221, 0.5], "8242": [3222, 0.5], "8244": [3223, 0.5], "8245": [3224, 0.5], "8246": [3225, 0.5], "8247": [3226, 0.5], "8248": [3227, 0.5], "8249": [3228, 0.5], "8251": [3229, 0.5], "8252": [3230, 0.5], "8274": [3231, 0.5], "8276": [3232, 0.5], "8277": [3233, 0.5], "8278": [3234, 0.5], "8279": [3235, 0.5], "8280": [3236, 0.5], "8281": [3237, 0.5], "8283": [3238, 0.5], "8284": [3239, 0.5], "8290": [3240, 0.5], "8292": [3241, 0.5], "8293": [3242, 0.5], "8294": [3243, 0.5], "8295": [3244, 0.5], "8296": [3245, 0.5], "8297": [3246, 0.5], "8299": [3247, 0.5], "8300": [3248, 0.5], "8306": [3249, 0.5], "8308": [3250, 0.5], "8309": [3251, 0.5], "8310": [3252, 0.5], "8311": [3253, 0.5], "8312": [3254, 0.5], "8313": [3255, 0.5], "8315": [3256, 0.5], "8316": [3257, 0.5], "8322": [3258, 0.5], "8324": [3259, 0.5], "8325": [3260, 0.5], "8326": [3261, 0.5], "8327": [3262, 0.5], "8328": [3263, 0.5], "8329": [3264, 0.5], "8331": [3265, 0.5], "8332": [3266, 0.5], "8338": [3267, 0.5], "8340": [3268, 0.5], "8341": [3269, 0.5], "8342": [3270, 0.5], "8343": [3271, 0.5], "8344": [3272, 0.5], "8345": [3273, 0.5], "8347": [3274, 0.5], "8348": [3275, 0.5], "8354": [3276, 0.5], "8356": [3277, 0.5], "8357": [3278, 0.5], "8358": [3279, 0.5], "8359": [3280, 0.5], "8360": [3281, 0.5], "8361": [3282, 0.5], "8363": [3283, 0.5], "8364": [3284, 0.5], "8370": [3285, 0.5], "8372": [3286, 0.5], "8373": [3287, 0.5], "8374": [3288, 0.5], "8375": [3289, 0.5], "8376": [3290, 0.5], "8377": [3291, 0.5], "8379": [3292, 0.5], "8380": [3293, 0.5], "8386": [3294, 0.5], "8388": [3295, 0.5], "8389": [3296, 0.5], "8390": [3297, 0.5], "8391": [3298, 0.5], "8392": [3299, 0.5], "8393": [3300, 0.5], "8395": [3301, 0.5], "8396": [3302, 0.5], "8402": [3303, 0.5], "8404": [3304, 0.5], "8405": [3305, 0.5], "8406": [3306, 0.5], "8407": [3307, 0.5], "8408": [3308, 0.5], "8409": [3309, 0.5], "8411": [3310, 0.5], "8412": [3311, 0.5], "8418": [3312, 0.5], "8420": [3313, 0.5], "8421": [3314, 0.5], "8422": [3315, 0.5], "8423": [3316, 0.5], "8424": [3317, 0.5], "8425": [3318, 0.5], "8427": [3319, 0.5], "8428": [3320, 0.5], "8434": [3321, 0.5], "8436": [3322, 0.5], "8437": [3323, 0.5], "8438": [3324, 0.5], "8439": [3325, 0.5], "8440": [3326, 0.5], "8441": [3327, 0.5], "8443": [3328, 0.5], "8444": [3329, 0.5], "8450": [3330, 0.5], "8452": [3331, 0.5], "8453": [3332, 0.5], "8454": [3333, 0.5], "8455": [3334, 0.5], "8456": [3335, 0.5], "8457": [3336, 0.5], "8459": [3337, 0.5], "8460": [3338, 0.5], "8466": [3339, 0.5], "8468": [3340, 0.5], "8469": [3341, 0.5], "8470": [3342, 0.5], "8471": [3343, 0.5], "8472": [3344, 0.5], "8473": [3345, 0.5], "8475": [3346, 0.5], "8476": [3347, 0.5], "8482": [3348, 0.5], "8484": [3349, 0.5], "8485": [3350, 0.5], "8486": [3351, 0.5], "8487": [3352, 0.5], "8488": [3353, 0.5], "8489": [3354, 0.5], "8491": [3355, 0.5], "8492": [3356, 0.5], "8498": [3357, 0.5], "8500": [3358, 0.5], "8501": [3359, 0.5], "8502": [3360, 0.5], "8503": [3361, 0.5], "8504": [3362, 0.5], "8505": [3363, 0.5], "8507": [3364, 0.5], "8508": [3365, 0.5], "8514": [3366, 0.5], "8516": [3367, 0.5], "8517": [3368, 0.5], "8518": [3369, 0.5], "8519": [3370, 0.5], "8520": [3371, 0.5], "8521": [3372, 0.5], "8523": [3373, 0.5], "8524": [3374, 0.5], "8546": [3375, 0.5], "8548": [3376, 0.5], "8549": [3377, 0.5], "8550": [3378, 0.5], "8551": [3379, 0.5], "8552": [3380, 0.5], "8553": [3381, 0.5], "8555": [3382, 0.5], "8556": [3383, 0.5], "8562": [3384, 0.5], "8564": [3385, 0.5], "8565": [3386, 0.5], "8566": [3387, 0.5], "8567": [3388, 0.5], "8568": [3389, 0.5], "8569": [3390, 0.5], "8571": [3391, 0.5], "8572": [3392, 0.5], "8578": [3393, 0.5], "8580": [3394, 0.5], "8581": [3395, 0.5], "8582": [3396, 0.5], "8583": [3397, 0.5], "8584": [3398, 0.5], "8585": [3399, 0.5], "8587": [3400, 0.5], "8588": [3401, 0.5], "8594": [3402, 0.5], "8596": [3403, 0.5], "8597": [3404, 0.5], "8598": [3405, 0.5], "8599": [3406, 0.5], "8600": [3407, 0.5], "8601": [3408, 0.5], "8603": [3409, 0.5], "8604": [3410, 0.5], "8610": [3411, 0.5], "8612": [3412, 0.5], "8613": [3413, 0.5], "8614": [3414, 0.5], "8615": [3415, 0.5], "8616": [3416, 0.5], "8617": [3417, 0.5], "8619": [3418, 0.5], "8620": [3419, 0.5], "8626": [3420, 0.5], "8628": [3421, 0.5], "8629": [3422, 0.5], "8630": [3423, 0.5], "8631": [3424, 0.5], "8632": [3425, 0.5], "8633": [3426, 0.5], "8635": [3427, 0.5], "8636": [3428, 0.5], "8642": [3429, 0.5], "8644": [3430, 0.5], "8645": [3431, 0.5], "8646": [3432, 0.5], "8647": [3433, 0.5], "8648": [3434, 0.5], "8649": [3435, 0.5], "8651": [3436, 0.5], "8652": [3437, 0.5], "8658": [3438, 0.5], "8660": [3439, 0.5], "8661": [3440, 0.5], "8662": [3441, 0.5], "8663": [3442, 0.5], "8664": [3443, 0.5], "8665": [3444, 0.5], "8667": [3445, 0.5], "8668": [3446, 0.5], "8674": [3447, 0.5], "8676": [3448, 0.5], "8677": [3449, 0.5], "8678": [3450, 0.5], "8679": [3451, 0.5], "8680": [3452, 0.5], "8681": [3453, 0.5], "8683": [3454, 0.5], "8684": [3455, 0.5], "8690": [3456, 0.5], "8692": [3457, 0.5], "8693": [3458, 0.5], "8694": [3459, 0.5], "8695": [3460, 0.5], "8696": [3461, 0.5], "8697": [3462, 0.5], "8699": [3463, 0.5], "8700": [3464, 0.5], "8706": [3465, 0.5], "8708": [3466, 0.5], "8709": [3467, 0.5], "8710": [3468, 0.5], "8711": [3469, 0.5], "8712": [3470, 0.5], "8713": [3471, 0.5], "8715": [3472, 0.5], "8716": [3473, 0.5], "8722": [3474, 0.5], "8724": [3475, 0.5], "8725": [3476, 0.5], "8726": [3477, 0.5], "8727": [3478, 0.5], "8728": [3479, 0.5], "8729": [3480, 0.5], "8731": [3481, 0.5], "8732": [3482, 0.5], "8738": [3483, 0.5], "8740": [3484, 0.5], "8741": [3485, 0.5], "8742": [3486, 0.5], "8743": [3487, 0.5], "8744": [3488, 0.5], "8745": [3489, 0.5], "8747": [3490, 0.5], "8748": [3491, 0.5], "8754": [3492, 0.5], "8756": [3493, 0.5], "8757": [3494, 0.5], "8758": [3495, 0.5], "8759": [3496, 0.5], "8760": [3497, 0.5], "8761": [3498, 0.5], "8763": [3499, 0.5], "8764": [3500, 0.5], "8770": [3501, 0.5], "8772": [3502, 0.5], "8773": [3503, 0.5], "8774": [3504, 0.5], "8775": [3505, 0.5], "8776": [3506, 0.5], "8777": [3507, 0.5], "8779": [3508, 0.5], "8780": [3509, 0.5], "8786": [3510, 0.5], "8788": [3511, 0.5], "8789": [3512, 0.5], "8790": [3513, 0.5], "8791": [3514, 0.5], "8792": [3515, 0.5], "8793": [3516, 0.5], "8795": [3517, 0.5], "8796": [3518, 0.5], "8818": [3519, 0.5], "8820": [3520, 0.5], "8821": [3521, 0.5], "8822": [3522, 0.5], "8823": [3523, 0.5], "8824": [3524, 0.5], "8825": [3525, 0.5], "8827": [3526, 0.5], "8828": [3527, 0.5], "8834": [3528, 0.5], "8836": [3529, 0.5], "8837": [3530, 0.5], "8838": [3531, 0.5], "8839": [3532, 0.5], "8840": [3533, 0.5], "8841": [3534, 0.5], "8843": [3535, 0.5], "8844": [3536, 0.5], "8850": [3537, 0.5], "8852": [3538, 0.5], "8853": [3539, 0.5], "8854": [3540, 0.5], "8855": [3541, 0.5], "8856": [3542, 0.5], "8857": [3543, 0.5], "8859": [3544, 0.5], "8860": [3545, 0.5], "8866": [3546, 0.5], "8868": [3547, 0.5], "8869": [3548, 0.5], "8870": [3549, 0.5], "8871": [3550, 0.5], "8872": [3551, 0.5], "8873": [3552, 0.5], "8875": [3553, 0.5], "8876": [3554, 0.5], "8882": [3555, 0.5], "8884": [3556, 0.5], "8885": [3557, 0.5], "8886": [3558, 0.5], "8887": [3559, 0.5], "8888": [3560, 0.5], "8889": [3561, 0.5], "8891": [3562, 0.5], "8892": [3563, 0.5], "8898": [3564, 0.5], "8900": [3565, 0.5], "8901": [3566, 0.5], "8902": [3567, 0.5], "8903": [3568, 0.5], "8904": [3569, 0.5], "8905": [3570, 0.5], "8907": [3571, 0.5], "8908": [3572, 0.5], "8914": [3573, 0.5], "8916": [3574, 0.5], "8917": [3575, 0.5], "8918": [3576, 0.5], "8919": [3577, 0.5], "8920": [3578, 0.5], "8921": [3579, 0.5], "8923": [3580, 0.5], "8924": [3581, 0.5], "8930": [3582, 0.5], "8932": [3583, 0.5], "8933": [3584, 0.5], "8934": [3585, 0.5], "8935": [3586, 0.5], "8936": [3587, 0.5], "8937": [3588, 0.5], "8939": [3589, 0.5], "8940": [3590, 0.5], "8946": [3591, 0.5], "8948": [3592, 0.5], "8949": [3593, 0.5], "8950": [3594, 0.5], "8951": [3595, 0.5], "8952": [3596, 0.5], "8953": [3597, 0.5], "8955": [3598, 0.5], "8956": [3599, 0.5], "8962": [3600, 0.5], "8964": [3601, 0.5], "8965": [3602, 0.5], "8966": [3603, 0.5], "8967": [3604, 0.5], "8968": [3605, 0.5], "8969": [3606, 0.5], "8971": [3607, 0.5], "8972": [3608, 0.5], "8978": [3609, 0.5], "8980": [3610, 0.5], "8981": [3611, 0.5], "8982": [3612, 0.5], "8983": [3613, 0.5], "8984": [3614, 0.5], "8985": [3615, 0.5], "8987": [3616, 0.5], "8988": [3617, 0.5], "8994": [3618, 0.5], "8996": [3619, 0.5], "8997": [3620, 0.5], "8998": [3621, 0.5], "8999": [3622, 0.5], "9000": [3623, 0.5], "9001": [3624, 0.5], "9003": [3625, 0.5], "9004": [3626, 0.5], "9010": [3627, 0.5], "9012": [3628, 0.5], "9013": [3629, 0.5], "9014": [3630, 0.5], "9015": [3631, 0.5], "9016": [3632, 0.5], "9017": [3633, 0.5], "9019": [3634, 0.5], "9020": [3635, 0.5], "9026": [3636, 0.5], "9028": [3637, 0.5], "9029": [3638, 0.5], "9030": [3639, 0.5], "9031": [3640, 0.5], "9032": [3641, 0.5], "9033": [3642, 0.5], "9035": [3643, 0.5], "9036": [3644, 0.5], "9042": [3645, 0.5], "9044": [3646, 0.5], "9045": [3647, 0.5], "9046": [3648, 0.5], "9047": [3649, 0.5], "9048": [3650, 0.5], "9049": [3651, 0.5], "9051": [3652, 0.5], "9052": [3653, 0.5], "9058": [3654, 0.5], "9060": [3655, 0.5], "9061": [3656, 0.5], "9062": [3657, 0.5], "9063": [3658, 0.5], "9064": [3659, 0.5], "9065": [3660, 0.5], "9067": [3661, 0.5], "9068": [3662, 0.5], "9090": [3663, 0.5], "9092": [3664, 0.5], "9093": [3665, 0.5], "9094": [3666, 0.5], "9095": [3667, 0.5], "9096": [3668, 0.5], "9097": [3669, 0.5], "9099": [3670, 0.5], "9100": [3671, 0.5], "9106": [3672, 0.5], "9108": [3673, 0.5], "9109": [3674, 0.5], "9110": [3675, 0.5], "9111": [3676, 0.5], "9112": [3677, 0.5], "9113": [3678, 0.5], "9115": [3679, 0.5], "9116": [3680, 0.5], "9122": [3681, 0.5], "9124": [3682, 0.5], "9125": [3683, 0.5], "9126": [3684, 0.5], "9127": [3685, 0.5], "9128": [3686, 0.5], "9129": [3687, 0.5], "9131": [3688, 0.5], "9132": [3689, 0.5], "9138": [3690, 0.5], "9140": [3691, 0.5], "9141": [3692, 0.5], "9142": [3693, 0.5], "9143": [3694, 0.5], "9144": [3695, 0.5], "9145": [3696, 0.5], "9147": [3697, 0.5], "9148": [3698, 0.5], "9154": [3699, 0.5], "9156": [3700, 0.5], "9157": [3701, 0.5], "9158": [3702, 0.5], "9159": [3703, 0.5], "9160": [3704, 0.5], "9161": [3705, 0.5], "9163": [3706, 0.5], "9164": [3707, 0.5], "9170": [3708, 0.5], "9172": [3709, 0.5], "9173": [3710, 0.5], "9174": [3711, 0.5], "9175": [3712, 0.5], "9176": [3713, 0.5], "9177": [3714, 0.5], "9179": [3715, 0.5], "9180": [3716, 0.5], "9186": [3717, 0.5], "9188": [3718, 0.5], "9189": [3719, 0.5], "9190": [3720, 0.5], "9191": [3721, 0.5], "9192": [3722, 0.5], "9193": [3723, 0.5], "9195": [3724, 0.5], "9196": [3725, 0.5], "9202": [3726, 0.5], "9204": [3727, 0.5], "9205": [3728, 0.5], "9206": [3729, 0.5], "9207": [3730, 0.5], "9208": [3731, 0.5], "9209": [3732, 0.5], "9211": [3733, 0.5], "9212": [3734, 0.5], "9218": [3735, 0.5], "9220": [3736, 0.5], "9221": [3737, 0.5], "9222": [3738, 0.5], "9223": [3739, 0.5], "9224": [3740, 0.5], "9225": [3741, 0.5], "9227": [3742, 0.5], "9228": [3743, 0.5], "9234": [3744, 0.5], "9236": [3745, 0.5], "9237": [3746, 0.5], "9238": [3747, 0.5], "9239": [3748, 0.5], "9240": [3749, 0.5], "9241": [3750, 0.5], "9243": [3751, 0.5], "9244": [3752, 0.5], "9250": [3753, 0.5], "9252": [3754, 0.5], "9253": [3755, 0.5], "9254": [3756, 0.5], "9255": [3757, 0.5], "9256": [3758, 0.5], "9257": [3759, 0.5], "9259": [3760, 0.5], "9260": [3761, 0.5], "9266": [3762, 0.5], "9268": [3763, 0.5], "9269": [3764, 0.5], "9270": [3765, 0.5], "9271": [3766, 0.5], "9272": [3767, 0.5], "9273": [3768, 0.5], "9275": [3769, 0.5], "9276": [3770, 0.5], "9282": [3771, 0.5], "9284": [3772, 0.5], "9285": [3773, 0.5], "9286": [3774, 0.5], "9287": [3775, 0.5], "9288": [3776, 0.5], "9289": [3777, 0.5], "9291": [3778, 0.5], "9292": [3779, 0.5], "9298": [3780, 0.5], "9300": [3781, 0.5], "9301": [3782, 0.5], "9302": [3783, 0.5], "9303": [3784, 0.5], "9304": [3785, 0.5], "9305": [3786, 0.5], "9307": [3787, 0.5], "9308": [3788, 0.5], "9314": [3789, 0.5], "9316": [3790, 0.5], "9317": [3791, 0.5], "9318": [3792, 0.5], "9319": [3793, 0.5], "9320": [3794, 0.5], "9321": [3795, 0.5], "9323": [3796, 0.5], "9324": [3797, 0.5], "9330": [3798, 0.5], "9332": [3799, 0.5], "9333": [3800, 0.5], "9334": [3801, 0.5], "9335": [3802, 0.5], "9336": [3803, 0.5], "9337": [3804, 0.5], "9339": [3805, 0.5], "9340": [3806, 0.5], "9362": [3807, 0.5], "9364": [3808, 0.5], "9365": [3809, 0.5], "9366": [3810, 0.5], "9367": [3811, 0.5], "9368": [3812, 0.5], "9369": [3813, 0.5], "9371": [3814, 0.5], "9372": [3815, 0.5], "9378": [3816, 0.5], "9380": [3817, 0.5], "9381": [3818, 0.5], "9382": [3819, 0.5], "9383": [3820, 0.5], "9384": [3821, 0.5], "9385": [3822, 0.5], "9387": [3823, 0.5], "9388": [3824, 0.5], "9394": [3825, 0.5], "9396": [3826, 0.5], "9397": [3827, 0.5], "9398": [3828, 0.5], "9399": [3829, 0.5], "9400": [3830, 0.5], "9401": [3831, 0.5], "9403": [3832, 0.5], "9404": [3833, 0.5], "9410": [3834, 0.5], "9412": [3835, 0.5], "9413": [3836, 0.5], "9414": [3837, 0.5], "9415": [3838, 0.5], "9416": [3839, 0.5], "9417": [3840, 0.5], "9419": [3841, 0.5], "9420": [3842, 0.5], "9426": [3843, 0.5], "9428": [3844, 0.5], "9429": [3845, 0.5], "9430": [3846, 0.5], "9431": [3847, 0.5], "9432": [3848, 0.5], "9433": [3849, 0.5], "9435": [3850, 0.5], "9436": [3851, 0.5], "9442": [3852, 0.5], "9444": [3853, 0.5], "9445": [3854, 0.5], "9446": [3855, 0.5], "9447": [3856, 0.5], "9448": [3857, 0.5], "9449": [3858, 0.5], "9451": [3859, 0.5], "9452": [3860, 0.5], "9458": [3861, 0.5], "9460": [3862, 0.5], "9461": [3863, 0.5], "9462": [3864, 0.5], "9463": [3865, 0.5], "9464": [3866, 0.5], "9465": [3867, 0.5], "9467": [3868, 0.5], "9468": [3869, 0.5], "9474": [3870, 0.5], "9476": [3871, 0.5], "9477": [3872, 0.5], "9478": [3873, 0.5], "9479": [3874, 0.5], "9480": [3875, 0.5], "9481": [3876, 0.5], "9483": [3877, 0.5], "9484": [3878, 0.5], "9490": [3879, 0.5], "9492": [3880, 0.5], "9493": [3881, 0.5], "9494": [3882, 0.5], "9495": [3883, 0.5], "9496": [3884, 0.5], "9497": [3885, 0.5], "9499": [3886, 0.5], "9500": [3887, 0.5], "9506": [3888, 0.5], "9508": [3889, 0.5], "9509": [3890, 0.5], "9510": [3891, 0.5], "9511": [3892, 0.5], "9512": [3893, 0.5], "9513": [3894, 0.5], "9515": [3895, 0.5], "9516": [3896, 0.5], "9522": [3897, 0.5], "9524": [3898, 0.5], "9525": [3899, 0.5], "9526": [3900, 0.5], "9527": [3901, 0.5], "9528": [3902, 0.5], "9529": [3903, 0.5], "9531": [3904, 0.5], "9532": [3905, 0.5], "9538": [3906, 0.5], "9540": [3907, 0.5], "9541": [3908, 0.5], "9542": [3909, 0.5], "9543": [3910, 0.5], "9544": [3911, 0.5], "9545": [3912, 0.5], "9547": [3913, 0.5], "9548": [3914, 0.5], "9554": [3915, 0.5], "9556": [3916, 0.5], "9557": [3917, 0.5], "9558": [3918, 0.5], "9559": [3919, 0.5], "9560": [3920, 0.5], "9561": [3921, 0.5], "9563": [3922, 0.5], "9564": [3923, 0.5], "9570": [3924, 0.5], "9572": [3925, 0.5], "9573": [3926, 0.5], "9574": [3927, 0.5], "9575": [3928, 0.5], "9576": [3929, 0.5], "9577": [3930, 0.5], "9579": [3931, 0.5], "9580": [3932, 0.5], "9586": [3933, 0.5], "9588": [3934, 0.5], "9589": [3935, 0.5], "9590": [3936, 0.5], "9591": [3937, 0.5], "9592": [3938, 0.5], "9593": [3939, 0.5], "9595": [3940, 0.5], "9596": [3941, 0.5], "9602": [3942, 0.5], "9604": [3943, 0.5], "9605": [3944, 0.5], "9606": [3945, 0.5], "9607": [3946, 0.5], "9608": [3947, 0.5], "9609": [3948, 0.5], "9611": [3949, 0.5], "9612": [3950, 0.5], "9701": [3951, 0.5], "9703": [3952, 0.5], "9705": [3953, 0.5], "9707": [3954, 0.5], "9709": [3955, 0.5], "9711": [3956, 0.5], "9713": [3957, 0.5], "9715": [3958, 0.5], "9717": [3959, 0.5], "9719": [3960, 0.5], "9721": [3961, 0.5], "9723": [3962, 0.5], "9725": [3963, 0.5], "9727": [3964, 0.5], "9729": [3965, 0.5], "9731": [3966, 0.5], "9733": [3967, 0.5], "9735": [3968, 0.5], "9737": [3969, 0.5], "9739": [3970, 0.5], "9741": [3971, 0.5], "9743": [3972, 0.5], "9745": [3973, 0.5], "9747": [3974, 0.5], "9749": [3975, 0.5], "9751": [3976, 0.5], "9753": [3977, 0.5], "9755": [3978, 0.5], "9757": [3979, 0.5], "9759": [3980, 0.5], "9761": [3981, 0.5], "9763": [3982, 0.5], "9765": [3983, 0.5], "9767": [3984, 0.5], "9769": [3985, 0.5], "9771": [3986, 0.5], "9773": [3987, 0.5], "9775": [3988, 0.5], "9777": [3989, 0.5], "9779": [3990, 0.5], "9781": [3991, 0.5], "9783": [3992, 0.5], "9785": [3993, 0.5], "9787": [3994, 0.5], "9789": [3995, 0.5], "9791": [3996, 0.5], "9793": [3997, 0.5], "9795": [3998, 0.5], "9797": [3999, 0.5], "9799": [4000, 0.5], "9801": [4001, 0.5], "9803": [4002, 0.5], "9805": [4003, 0.5], "9807": [4004, 0.5], "9809": [4005, 0.5], "9811": [4006, 0.5], "9813": [4007, 0.5], "9815": [4008, 0.5], "9817": [4009, 0.5], "9819": [4010, 0.5], "9821": [4011, 0.5], "9823": [4012, 0.5], "9825": [4013, 0.5], "9827": [4014, 0.5], "9829": [4015, 0.5], "9831": [4016, 0.5], "9833": [4017, 0.5], "9835": [4018, 0.5], "10001": [4019, 0.5], "10002": [4020, 0.5], "10003": [4021, 0.5], "10004": [4022, 0.5], "10005": [4023, 0.5], "10006": [4024, 0.5], "10007": [4025, 0.5], "10008": [4026, 0.5], "10014": [4027, 0.5], "10015": [4028, 0.5], "10016": [4029, 0.5], "10017": [4030, 0.5], "10033": [4031, 0.5], "10034": [4032, 0.5], "10035": [4033, 0.5], "10036": [4034, 0.5], "10037": [4035, 0.5], "10038": [4036, 0.5], "10039": [4037, 0.5], "10040": [4038, 0.5], "10046": [4039, 0.5], "10047": [4040, 0.5], "10048": [4041, 0.5], "10049": [4042, 0.5], "10065": [4043, 0.5], "10066": [4044, 0.5], "10067": [4045, 0.5], "10068": [4046, 0.5], "10069": [4047, 0.5], "10070": [4048, 0.5], "10071": [4049, 0.5], "10072": [4050, 0.5], "10078": [4051, 0.5], "10079": [4052, 0.5], "10080": [4053, 0.5], "10081": [4054, 0.5], "10097": [4055, 0.5], "10098": [4056, 0.5], "10099": [4057, 0.5], "10100": [4058, 0.5], "10101": [4059, 0.5], "10102": [4060, 0.5], "10103": [4061, 0.5], "10104": [4062, 0.5], "10110": [4063, 0.5], "10111": [4064, 0.5], "10112": [4065, 0.5], "10113": [4066, 0.5], "10129": [4067, 0.5], "10130": [4068, 0.5], "10131": [4069, 0.5], "10132": [4070, 0.5], "10133": [4071, 0.5], "10134": [4072, 0.5], "10135": [4073, 0.5], "10136": [4074, 0.5], "10142": [4075, 0.5], "10143": [4076, 0.5], "10144": [4077, 0.5], "10145": [4078, 0.5], "10161": [4079, 0.5], "10162": [4080, 0.5], "10163": [4081, 0.5], "10164": [4082, 0.5], "10165": [4083, 0.5], "10166": [4084, 0.5], "10167": [4085, 0.5], "10168": [4086, 0.5], "10174": [4087, 0.5], "10175": [4088, 0.5], "10176": [4089, 0.5], "10177": [4090, 0.5], "10193": [4091, 0.5], "10194": [4092, 0.5], "10195": [4093, 0.5], "10196": [4094, 0.5], "10197": [4095, 0.5], "10198": [4096, 0.5], "10199": [4097, 0.5], "10200": [4098, 0.5], "10206": [4099, 0.5], "10207": [4100, 0.5], "10208": [4101, 0.5], "10209": [4102, 0.5], "10225": [4103, 0.5], "10226": [4104, 0.5], "10227": [4105, 0.5], "10228": [4106, 0.5], "10229": [4107, 0.5], "10230": [4108, 0.5], "10231": [4109, 0.5], "10232": [4110, 0.5], "10238": [4111, 0.5], "10239": [4112, 0.5], "10240": [4113, 0.5], "10241": [4114, 0.5], "10257": [4115, 0.5], "10258": [4116, 0.5], "10259": [4117, 0.5], "10260": [4118, 0.5], "10261": [4119, 0.5], "10262": [4120, 0.5], "10263": [4121, 0.5], "10264": [4122, 0.5], "10270": [4123, 0.5], "10271": [4124, 0.5], "10272": [4125, 0.5], "10273": [4126, 0.5], "10289": [4127, 0.5], "10290": [4128, 0.5], "10291": [4129, 0.5], "10292": [4130, 0.5], "10293": [4131, 0.5], "10294": [4132, 0.5], "10295": [4133, 0.5], "10296": [4134, 0.5], "10302": [4135, 0.5], "10303": [4136, 0.5], "10304": [4137, 0.5], "10305": [4138, 0.5], "10321": [4139, 0.5], "10322": [4140, 0.5], "10323": [4141, 0.5], "10324": [4142, 0.5], "10325": [4143, 0.5], "10326": [4144, 0.5], "10327": [4145, 0.5], "10328": [4146, 0.5], "10334": [4147, 0.5], "10335": [4148, 0.5], "10336": [4149, 0.5], "10337": [4150, 0.5], "10353": [4151, 0.5], "10354": [4152, 0.5], "10355": [4153, 0.5], "10356": [4154, 0.5], "10357": [4155, 0.5], "10358": [4156, 0.5], "10359": [4157, 0.5], "10360": [4158, 0.5], "10366": [4159, 0.5], "10367": [4160, 0.5], "10368": [4161, 0.5], "10369": [4162, 0.5], "10385": [4163, 0.5], "10386": [4164, 0.5], "10387": [4165, 0.5], "10388": [4166, 0.5], "10389": [4167, 0.5], "10390": [4168, 0.5], "10391": [4169, 0.5], "10392": [4170, 0.5], "10398": [4171, 0.5], "10399": [4172, 0.5], "10400": [4173, 0.5], "10401": [4174, 0.5], "10417": [4175, 0.5], "10418": [4176, 0.5], "10419": [4177, 0.5], "10420": [4178, 0.5], "10421": [4179, 0.5], "10422": [4180, 0.5], "10423": [4181, 0.5], "10424": [4182, 0.5], "10430": [4183, 0.5], "10431": [4184, 0.5], "10432": [4185, 0.5], "10433": [4186, 0.5], "10449": [4187, 0.5], "10450": [4188, 0.5], "10451": [4189, 0.5], "10452": [4190, 0.5], "10453": [4191, 0.5], "10454": [4192, 0.5], "10455": [4193, 0.5], "10456": [4194, 0.5], "10462": [4195, 0.5], "10463": [4196, 0.5], "10464": [4197, 0.5], "10465": [4198, 0.5], "10481": [4199, 0.5], "10482": [4200, 0.5], "10483": [4201, 0.5], "10484": [4202, 0.5], "10485": [4203, 0.5], "10486": [4204, 0.5], "10487": [4205, 0.5], "10488": [4206, 0.5], "10494": [4207, 0.5], "10495": [4208, 0.5], "10496": [4209, 0.5], "10497": [4210, 0.5], "10513": [4211, 0.5], "10514": [4212, 0.5], "10515": [4213, 0.5], "10516": [4214, 0.5], "10517": [4215, 0.5], "10518": [4216, 0.5], "10519": [4217, 0.5], "10520": [4218, 0.5], "10526": [4219, 0.5], "10527": [4220, 0.5], "10528": [4221, 0.5], "10529": [4222, 0.5], "10545": [4223, 0.5], "10546": [4224, 0.5], "10547": [4225, 0.5], "10548": [4226, 0.5], "10549": [4227, 0.5], "10550": [4228, 0.5], "10551": [4229, 0.5], "10552": [4230, 0.5], "10558": [4231, 0.5], "10559": [4232, 0.5], "10560": [4233, 0.5], "10561": [4234, 0.5], "10577": [4235, 0.5], "10578": [4236, 0.5], "10579": [4237, 0.5], "10580": [4238, 0.5], "10581": [4239, 0.5], "10582": [4240, 0.5], "10583": [4241, 0.5], "10584": [4242, 0.5], "10590": [4243, 0.5], "10591": [4244, 0.5], "10592": [4245, 0.5], "10593": [4246, 0.5], "10609": [4247, 0.5], "10610": [4248, 0.5], "10611": [4249, 0.5], "10612": [4250, 0.5], "10613": [4251, 0.5], "10614": [4252, 0.5], "10615": [4253, 0.5], "10616": [4254, 0.5], "10622": [4255, 0.5], "10623": [4256, 0.5], "10624": [4257, 0.5], "10625": [4258, 0.5], "11000": [4259, 0.5], "11001": [4260, 0.5], "11002": [4261, 0.5], "11003": [4262, 0.5], "11004": [4263, 0.5], "11005": [4264, 0.5], "11006": [4265, 0.5], "11007": [4266, 0.5], "11008": [4267, 0.5], "11009": [4268, 0.5], "11010": [4269, 0.5], "11011": [4270, 0.5], "11012": [4271, 0.5], "11013": [4272, 0.5], "11014": [4273, 0.5], "11015": [4274, 0.5], "11016": [4275, 0.5], "11017": [4276, 0.5], "11018": [4277, 0.5], "11019": [4278, 0.5], "11020": [4279, 0.5], "11021": [4280, 0.5], "11022": [4281, 0.5], "11023": [4282, 0.5], "11024": [4283, 0.5], "11025": [4284, 0.5], "11026": [4285, 0.5], "11027": [4286, 0.5], "11028": [4287, 0.5], "11029": [4288, 0.5], "11030": [4289, 0.5], "11031": [4290, 0.5], "11032": [4291, 0.5], "11033": [4292, 0.5], "11034": [4293, 0.5], "11035": [4294, 0.5], "11036": [4295, 0.5], "11037": [4296, 0.5], "11038": [4297, 0.5], "11039": [4298, 0.5], "11040": [4299, 0.5], "11041": [4300, 0.5], "11042": [4301, 0.5], "11043": [4302, 0.5], "11044": [4303, 0.5], "11045": [4304, 0.5], "11046": [4305, 0.5], "11047": [4306, 0.5], "11048": [4307, 0.5], "11049": [4308, 0.5], "11050": [4309, 0.5], "11051": [4310, 0.5], "11052": [4311, 0.5], "11053": [4312, 0.5], "11054": [4313, 0.5], "11055": [4314, 0.5], "11056": [4315, 0.5], "11057": [4316, 0.5], "11058": [4317, 0.5], "11059": [4318, 0.5], "11060": [4319, 0.5], "11061": [4320, 0.5], "11062": [4321, 0.5], "11063": [4322, 0.5], "11064": [4323, 0.5], "11065": [4324, 0.5], "11066": [4325, 0.5], "11067": [4326, 0.5], "11068": [4327, 0.5], "11069": [4328, 0.5], "11070": [4329, 0.5], "11071": [4330, 0.5], "11072": [4331, 0.5], "11073": [4332, 0.5], "11074": [4333, 0.5], "11075": [4334, 0.5], "11076": [4335, 0.5], "11077": [4336, 0.5], "11078": [4337, 0.5], "11079": [4338, 0.5], "11080": [4339, 0.5], "11081": [4340, 0.5], "11082": [4341, 0.5], "11083": [4342, 0.5], "11084": [4343, 0.5], "11085": [4344, 0.5], "11086": [4345, 0.5], "11087": [4346, 0.5], "11088": [4347, 0.5], "11089": [4348, 0.5], "11090": [4349, 0.5], "11091": [4350, 0.5], "11092": [4351, 0.5], "11093": [4352, 0.5], "11094": [4353, 0.5], "11095": [4354, 0.5], "11096": [4355, 0.5], "11097": [4356, 0.5], "11098": [4357, 0.5], "11099": [4358, 0.5], "11100": [4359, 0.5], "11101": [4360, 0.5], "11102": [4361, 0.5], "11103": [4362, 0.5], "11104": [4363, 0.5], "11105": [4364, 0.5], "11106": [4365, 0.5], "11107": [4366, 0.5], "11108": [4367, 0.5], "11109": [4368, 0.5], "11110": [4369, 0.5], "11111": [4370, 0.5], "11112": [4371, 0.5], "11113": [4372, 0.5], "11114": [4373, 0.5], "11115": [4374, 0.5], "11116": [4375, 0.5], "11117": [4376, 0.5], "11118": [4377, 0.5], "11119": [4378, 0.5], "11120": [4379, 0.5], "11121": [4380, 0.5], "11122": [4381, 0.5], "11123": [4382, 0.5], "11124": [4383, 0.5], "11125": [4384, 0.5], "11126": [4385, 0.5], "11127": [4386, 0.5], "11128": [4387, 0.5], "11129": [4388, 0.5], "11130": [4389, 0.5], "11131": [4390, 0.5], "11132": [4391, 0.5], "11133": [4392, 0.5], "11134": [4393, 0.5], "11135": [4394, 0.5], "11136": [4395, 0.5], "11137": [4396, 0.5], "11138": [4397, 0.5], "11139": [4398, 0.5], "11140": [4399, 0.5], "11141": [4400, 0.5], "11142": [4401, 0.5], "11143": [4402, 0.5], "11144": [4403, 0.5], "11145": [4404, 0.5], "11146": [4405, 0.5], "11147": [4406, 0.5], "11148": [4407, 0.5], "11149": [4408, 0.5], "11150": [4409, 0.5], "11151": [4410, 0.5], "11152": [4411, 0.5], "11153": [4412, 0.5], "11154": [4413, 0.5], "11155": [4414, 0.5], "11156": [4415, 0.5], "11157": [4416, 0.5], "11158": [4417, 0.5], "11159": [4418, 0.5], "11160": [4419, 0.5], "11161": [4420, 0.5], "11162": [4421, 0.5], "11163": [4422, 0.5], "11164": [4423, 0.5], "11165": [4424, 0.5], "11166": [4425, 0.5], "11167": [4426, 0.5], "11168": [4427, 0.5], "11169": [4428, 0.5], "11170": [4429, 0.5], "11171": [4430, 0.5], "11172": [4431, 0.5], "11173": [4432, 0.5], "11174": [4433, 0.5], "11175": [4434, 0.5], "11176": [4435, 0.5], "11177": [4436, 0.5], "11178": [4437, 0.5], "11179": [4438, 0.5], "11180": [4439, 0.5], "11181": [4440, 0.5], "11182": [4441, 0.5], "11183": [4442, 0.5], "11184": [4443, 0.5], "11185": [4444, 0.5], "11186": [4445, 0.5], "11187": [4446, 0.5], "11188": [4447, 0.5], "11189": [4448, 0.5], "11190": [4449, 0.5], "11191": [4450, 0.5], "11192": [4451, 0.5], "11193": [4452, 0.5], "11194": [4453, 0.5], "11195": [4454, 0.5], "11196": [4455, 0.5], "11197": [4456, 0.5], "11198": [4457, 0.5], "11199": [4458, 0.5], "11200": [4459, 0.5], "11201": [4460, 0.5], "11202": [4461, 0.5], "11203": [4462, 0.5], "11204": [4463, 0.5], "11205": [4464, 0.5], "11206": [4465, 0.5], "11207": [4466, 0.5], "11208": [4467, 0.5], "11209": [4468, 0.5], "11210": [4469, 0.5], "11211": [4470, 0.5], "11212": [4471, 0.5], "11213": [4472, 0.5], "11214": [4473, 0.5], "11215": [4474, 0.5], "11216": [4475, 0.5], "11217": [4476, 0.5], "11218": [4477, 0.5], "11219": [4478, 0.5], "11220": [4479, 0.5], "11221": [4480, 0.5], "11222": [4481, 0.5], "11223": [4482, 0.5], "11224": [4483, 0.5], "11225": [4484, 0.5], "11226": [4485, 0.5], "11227": [4486, 0.5], "11228": [4487, 0.5], "11229": [4488, 0.5], "11230": [4489, 0.5], "11231": [4490, 0.5], "11232": [4491, 0.5], "11233": [4492, 0.5], "11234": [4493, 0.5], "11235": [4494, 0.5], "11236": [4495, 0.5], "11237": [4496, 0.5], "11238": [4497, 0.5], "11239": [4498, 0.5], "11240": [4499, 0.5], "11241": [4500, 0.5], "11242": [4501, 0.5], "11243": [4502, 0.5], "11244": [4503, 0.5], "11245": [4504, 0.5], "11246": [4505, 0.5], "11247": [4506, 0.5], "11248": [4507, 0.5], "11249": [4508, 0.5], "11250": [4509, 0.5], "11251": [4510, 0.5], "11252": [4511, 0.5], "11253": [4512, 0.5], "11254": [4513, 0.5], "11255": [4514, 0.5], "11256": [4515, 0.5], "11257": [4516, 0.5], "11258": [4517, 0.5], "11259": [4518, 0.5], "11260": [4519, 0.5], "11261": [4520, 0.5], "11262": [4521, 0.5], "11263": [4522, 0.5], "11264": [4523, 0.5], "11265": [4524, 0.5], "11266": [4525, 0.5], "11267": [4526, 0.5], "11268": [4527, 0.5], "11269": [4528, 0.5], "11270": [4529, 0.5], "11271": [4530, 0.5], "11272": [4531, 0.5], "11273": [4532, 0.5], "11274": [4533, 0.5], "11275": [4534, 0.5], "11276": [4535, 0.5], "11277": [4536, 0.5], "11278": [4537, 0.5], "11279": [4538, 0.5], "11280": [4539, 0.5], "11281": [4540, 0.5], "11282": [4541, 0.5], "11283": [4542, 0.5], "11284": [4543, 0.5], "11285": [4544, 0.5], "11286": [4545, 0.5], "11287": [4546, 0.5], "11288": [4547, 0.5], "11289": [4548, 0.5], "11290": [4549, 0.5], "11291": [4550, 0.5], "11292": [4551, 0.5], "11293": [4552, 0.5], "11294": [4553, 0.5], "11295": [4554, 0.5], "11296": [4555, 0.5], "11297": [4556, 0.5], "11298": [4557, 0.5], "11299": [4558, 0.5], "11300": [4559, 0.5], "11301": [4560, 0.5], "11302": [4561, 0.5], "11303": [4562, 0.5], "11304": [4563, 0.5], "11305": [4564, 0.5], "11306": [4565, 0.5], "11307": [4566, 0.5], "11308": [4567, 0.5], "11309": [4568, 0.5], "11310": [4569, 0.5], "11311": [4570, 0.5], "11312": [4571, 0.5], "11313": [4572, 0.5], "11314": [4573, 0.5], "11315": [4574, 0.5], "11316": [4575, 0.5], "11317": [4576, 0.5], "11318": [4577, 0.5], "11319": [4578, 0.5], "11320": [4579, 0.5], "11321": [4580, 0.5], "11322": [4581, 0.5], "11323": [4582, 0.5], "11324": [4583, 0.5], "11325": [4584, 0.5], "11326": [4585, 0.5], "11327": [4586, 0.5], "11328": [4587, 0.5], "11329": [4588, 0.5], "11330": [4589, 0.5], "11331": [4590, 0.5], "11332": [4591, 0.5], "11333": [4592, 0.5], "11334": [4593, 0.5], "11335": [4594, 0.5], "11336": [4595, 0.5], "11337": [4596, 0.5], "11338": [4597, 0.5], "11339": [4598, 0.5], "11340": [4599, 0.5], "11341": [4600, 0.5], "11342": [4601, 0.5], "11343": [4602, 0.5], "11344": [4603, 0.5], "11345": [4604, 0.5], "11346": [4605, 0.5], "11347": [4606, 0.5], "11348": [4607, 0.5], "11349": [4608, 0.5], "11350": [4609, 0.5], "11351": [4610, 0.5], "11352": [4611, 0.5], "11353": [4612, 0.5], "11354": [4613, 0.5], "11355": [4614, 0.5], "11356": [4615, 0.5], "11357": [4616, 0.5], "11358": [4617, 0.5], "11359": [4618, 0.5], "11360": [4619, 0.5], "11361": [4620, 0.5], "11362": [4621, 0.5], "11363": [4622, 0.5], "11364": [4623, 0.5], "11365": [4624, 0.5], "11366": [4625, 0.5], "11367": [4626, 0.5], "11368": [4627, 0.5], "11369": [4628, 0.5], "11370": [4629, 0.5], "11371": [4630, 0.5], "11372": [4631, 0.5], "11373": [4632, 0.5], "11374": [4633, 0.5], "11375": [4634, 0.5], "11376": [4635, 0.5], "11377": [4636, 0.5], "11378": [4637, 0.5], "11379": [4638, 0.5], "11380": [4639, 0.5], "11381": [4640, 0.5], "11382": [4641, 0.5], "11383": [4642, 0.5], "11384": [4643, 0.5], "11385": [4644, 0.5], "11386": [4645, 0.5], "11387": [4646, 0.5], "11388": [4647, 0.5], "11389": [4648, 0.5], "11390": [4649, 0.5], "11391": [4650, 0.5], "11392": [4651, 0.5], "11393": [4652, 0.5], "11394": [4653, 0.5], "11395": [4654, 0.5], "11396": [4655, 0.5], "11397": [4656, 0.5], "11398": [4657, 0.5], "11399": [4658, 0.5], "11400": [4659, 0.5], "11401": [4660, 0.5], "11402": [4661, 0.5], "11403": [4662, 0.5], "11404": [4663, 0.5], "11405": [4664, 0.5], "11406": [4665, 0.5], "11407": [4666, 0.5], "11408": [4667, 0.5], "11409": [4668, 0.5], "11410": [4669, 0.5], "11411": [4670, 0.5], "11412": [4671, 0.5], "11413": [4672, 0.5], "11414": [4673, 0.5], "11415": [4674, 0.5], "11416": [4675, 0.5], "11417": [4676, 0.5], "11418": [4677, 0.5], "11419": [4678, 0.5], "11420": [4679, 0.5], "11421": [4680, 0.5], "11422": [4681, 0.5], "11423": [4682, 0.5], "11424": [4683, 0.5], "11425": [4684, 0.5], "11426": [4685, 0.5], "11427": [4686, 0.5], "11428": [4687, 0.5], "11429": [4688, 0.5], "11430": [4689, 0.5], "11431": [4690, 0.5], "11432": [4691, 0.5], "11433": [4692, 0.5], "11434": [4693, 0.5], "11435": [4694, 0.5], "11436": [4695, 0.5], "11437": [4696, 0.5], "11438": [4697, 0.5], "11439": [4698, 0.5], "11440": [4699, 0.5], "11441": [4700, 0.5], "11442": [4701, 0.5], "11443": [4702, 0.5], "11444": [4703, 0.5], "11445": [4704, 0.5], "11446": [4705, 0.5], "11447": [4706, 0.5], "11448": [4707, 0.5], "11449": [4708, 0.5], "11450": [4709, 0.5], "11451": [4710, 0.5], "11452": [4711, 0.5], "11453": [4712, 0.5], "11454": [4713, 0.5], "11455": [4714, 0.5], "11456": [4715, 0.5], "11457": [4716, 0.5], "11458": [4717, 0.5], "11459": [4718, 0.5], "11460": [4719, 0.5], "11461": [4720, 0.5], "11462": [4721, 0.5], "11463": [4722, 0.5], "11464": [4723, 0.5], "11465": [4724, 0.5], "11466": [4725, 0.5], "11467": [4726, 0.5], "11468": [4727, 0.5], "11469": [4728, 0.5], "11470": [4729, 0.5], "11471": [4730, 0.5], "11472": [4731, 0.5], "11473": [4732, 0.5], "11474": [4733, 0.5], "11475": [4734, 0.5], "11476": [4735, 0.5], "11477": [4736, 0.5], "11478": [4737, 0.5], "11479": [4738, 0.5], "11480": [4739, 0.5], "11481": [4740, 0.5], "11482": [4741, 0.5], "11483": [4742, 0.5], "11484": [4743, 0.5], "11485": [4744, 0.5], "11486": [4745, 0.5], "11487": [4746, 0.5], "11488": [4747, 0.5], "11489": [4748, 0.5], "11490": [4749, 0.5], "11491": [4750, 0.5], "11492": [4751, 0.5], "11493": [4752, 0.5], "11494": [4753, 0.5], "11495": [4754, 0.5], "11496": [4755, 0.5], "11497": [4756, 0.5], "11498": [4757, 0.5], "11499": [4758, 0.5], "11500": [4759, 0.5], "11501": [4760, 0.5], "11502": [4761, 0.5], "11503": [4762, 0.5], "11504": [4763, 0.5], "11505": [4764, 0.5], "11506": [4765, 0.5], "11507": [4766, 0.5], "11508": [4767, 0.5], "11509": [4768, 0.5], "11510": [4769, 0.5], "11511": [4770, 0.5], "11512": [4771, 0.5], "11513": [4772, 0.5], "11514": [4773, 0.5], "11515": [4774, 0.5], "11516": [4775, 0.5], "11517": [4776, 0.5], "11518": [4777, 0.5], "11519": [4778, 0.5], "11520": [4779, 0.5], "11521": [4780, 0.5], "11522": [4781, 0.5], "11523": [4782, 0.5], "11524": [4783, 0.5], "11525": [4784, 0.5], "11526": [4785, 0.5], "11527": [4786, 0.5], "11528": [4787, 0.5], "11529": [4788, 0.5], "11530": [4789, 0.5], "11531": [4790, 0.5], "11532": [4791, 0.5], "11533": [4792, 0.5], "11534": [4793, 0.5], "11535": [4794, 0.5], "11536": [4795, 0.5], "11537": [4796, 0.5], "11538": [4797, 0.5], "11539": [4798, 0.5], "11540": [4799, 0.5], "11541": [4800, 0.5], "11542": [4801, 0.5], "11543": [4802, 0.5], "11544": [4803, 0.5], "11545": [4804, 0.5], "11546": [4805, 0.5], "11547": [4806, 0.5], "11548": [4807, 0.5], "11549": [4808, 0.5], "11550": [4809, 0.5], "11551": [4810, 0.5], "11552": [4811, 0.5], "11553": [4812, 0.5], "11554": [4813, 0.5], "11555": [4814, 0.5], "11556": [4815, 0.5], "11557": [4816, 0.5], "11558": [4817, 0.5], "11559": [4818, 0.5], "11560": [4819, 0.5], "11561": [4820, 0.5], "11562": [4821, 0.5], "11563": [4822, 0.5], "11564": [4823, 0.5], "11565": [4824, 0.5], "11566": [4825, 0.5], "11567": [4826, 0.5], "11568": [4827, 0.5], "11569": [4828, 0.5], "11570": [4829, 0.5], "11571": [4830, 0.5], "11572": [4831, 0.5], "11573": [4832, 0.5], "11574": [4833, 0.5], "11575": [4834, 0.5], "11601": [4835, 0.5], "11700": [4836, 0.5], "11701": [4837, 0.5], "11702": [4838, 0.5], "11703": [4839, 0.5], "11704": [4840, 0.5], "11705": [4841, 0.5], "11706": [4842, 0.5], "11707": [4843, 0.5], "11708": [4844, 0.5], "11709": [4845, 0.5], "11710": [4846, 0.5], "11711": [4847, 0.5], "11712": [4848, 0.5], "11713": [4849, 0.5], "11714": [4850, 0.5], "11715": [4851, 0.5], "11716": [4852, 0.5], "11717": [4853, 0.5], "11718": [4854, 0.5], "11719": [4855, 0.5], "11720": [4856, 0.5], "11721": [4857, 0.5], "11722": [4858, 0.5], "11723": [4859, 0.5], "11724": [4860, 0.5], "11725": [4861, 0.5], "11726": [4862, 0.5], "11727": [4863, 0.5], "11728": [4864, 0.5], "11729": [4865, 0.5], "11730": [4866, 0.5], "11731": [4867, 0.5], "11732": [4868, 0.5], "11733": [4869, 0.5], "11734": [4870, 0.5], "11735": [4871, 0.5], "11736": [4872, 0.5], "11737": [4873, 0.5], "11738": [4874, 0.5], "11739": [4875, 0.5], "11740": [4876, 0.5], "11741": [4877, 0.5], "11742": [4878, 0.5], "11743": [4879, 0.5], "11744": [4880, 0.5], "11745": [4881, 0.5], "11746": [4882, 0.5], "11747": [4883, 0.5], "11748": [4884, 0.5], "11749": [4885, 0.5], "11750": [4886, 0.5], "11751": [4887, 0.5], "11752": [4888, 0.5], "11753": [4889, 0.5], "11754": [4890, 0.5], "11755": [4891, 0.5], "11756": [4892, 0.5], "11757": [4893, 0.5], "11758": [4894, 0.5], "11759": [4895, 0.5], "11760": [4896, 0.5], "11761": [4897, 0.5], "11762": [4898, 0.5], "11763": [4899, 0.5], "11764": [4900, 0.5], "11765": [4901, 0.5], "11766": [4902, 0.5], "11767": [4903, 0.5], "11768": [4904, 0.5], "11769": [4905, 0.5], "11770": [4906, 0.5], "11771": [4907, 0.5], "11772": [4908, 0.5], "11773": [4909, 0.5], "11774": [4910, 0.5], "11775": [4911, 0.5], "11776": [4912, 0.5], "11777": [4913, 0.5], "11778": [4914, 0.5], "11779": [4915, 0.5], "11780": [4916, 0.5], "11781": [4917, 0.5], "11782": [4918, 0.5], "11783": [4919, 0.5], "11784": [4920, 0.5], "11785": [4921, 0.5], "11786": [4922, 0.5], "11787": [4923, 0.5], "11788": [4924, 0.5], "11789": [4925, 0.5], "11790": [4926, 0.5], "11791": [4927, 0.5], "11792": [4928, 0.5], "11793": [4929, 0.5], "11794": [4930, 0.5], "11795": [4931, 0.5], "11796": [4932, 0.5], "11797": [4933, 0.5], "11798": [4934, 0.5], "11799": [4935, 0.5], "11800": [4936, 0.5], "11801": [4937, 0.5], "11802": [4938, 0.5], "11803": [4939, 0.5], "11804": [4940, 0.5], "11805": [4941, 0.5], "11806": [4942, 0.5], "11807": [4943, 0.5], "11808": [4944, 0.5], "11809": [4945, 0.5], "11810": [4946, 0.5], "11811": [4947, 0.5], "11812": [4948, 0.5], "11813": [4949, 0.5], "11814": [4950, 0.5], "11815": [4951, 0.5], "11816": [4952, 0.5], "11817": [4953, 0.5], "11818": [4954, 0.5], "11819": [4955, 0.5], "11820": [4956, 0.5], "11821": [4957, 0.5], "11822": [4958, 0.5], "11823": [4959, 0.5], "11824": [4960, 0.5], "11825": [4961, 0.5], "11826": [4962, 0.5], "11827": [4963, 0.5], "11828": [4964, 0.5], "11829": [4965, 0.5], "11830": [4966, 0.5], "11831": [4967, 0.5], "11832": [4968, 0.5], "11833": [4969, 0.5], "11834": [4970, 0.5], "11835": [4971, 0.5], "11836": [4972, 0.5], "11837": [4973, 0.5], "11838": [4974, 0.5], "11839": [4975, 0.5], "11840": [4976, 0.5], "11841": [4977, 0.5], "11842": [4978, 0.5], "11843": [4979, 0.5], "11844": [4980, 0.5], "11845": [4981, 0.5], "11846": [4982, 0.5], "11847": [4983, 0.5], "11848": [4984, 0.5], "11849": [4985, 0.5], "11850": [4986, 0.5], "11851": [4987, 0.5], "11852": [4988, 0.5], "11853": [4989, 0.5], "11854": [4990, 0.5], "11855": [4991, 0.5], "11856": [4992, 0.5], "11857": [4993, 0.5], "11858": [4994, 0.5], "11859": [4995, 0.5], "11860": [4996, 0.5], "11861": [4997, 0.5], "11862": [4998, 0.5], "11863": [4999, 0.5], "11864": [5000, 0.5], "11865": [5001, 0.5], "11866": [5002, 0.5], "11867": [5003, 0.5], "11868": [5004, 0.5], "11869": [5005, 0.5], "11870": [5006, 0.5], "11871": [5007, 0.5], "11872": [5008, 0.5], "11873": [5009, 0.5], "11874": [5010, 0.5], "11875": [5011, 0.5], "11876": [5012, 0.5], "11877": [5013, 0.5], "11878": [5014, 0.5], "11879": [5015, 0.5], "11880": [5016, 0.5], "11881": [5017, 0.5], "11882": [5018, 0.5], "11883": [5019, 0.5], "11884": [5020, 0.5], "11885": [5021, 0.5], "11886": [5022, 0.5], "11887": [5023, 0.5], "11888": [5024, 0.5], "11889": [5025, 0.5], "11890": [5026, 0.5], "11891": [5027, 0.5], "11892": [5028, 0.5], "11893": [5029, 0.5], "11894": [5030, 0.5], "11895": [5031, 0.5], "11896": [5032, 0.5], "11897": [5033, 0.5], "11898": [5034, 0.5], "11899": [5035, 0.5], "11900": [5036, 0.5], "11901": [5037, 0.5], "11902": [5038, 0.5], "11903": [5039, 0.5], "11904": [5040, 0.5], "11905": [5041, 0.5], "11906": [5042, 0.5], "11907": [5043, 0.5], "11908": [5044, 0.5], "11909": [5045, 0.5], "11910": [5046, 0.5], "11911": [5047, 0.5], "11912": [5048, 0.5], "11913": [5049, 0.5], "11914": [5050, 0.5], "11915": [5051, 0.5], "11916": [5052, 0.5], "11917": [5053, 0.5], "11918": [5054, 0.5], "11919": [5055, 0.5], "11920": [5056, 0.5], "11921": [5057, 0.5], "11922": [5058, 0.5], "11923": [5059, 0.5], "11924": [5060, 0.5], "11925": [5061, 0.5], "11926": [5062, 0.5], "11927": [5063, 0.5], "11928": [5064, 0.5], "11929": [5065, 0.5], "11930": [5066, 0.5], "11931": [5067, 0.5], "11932": [5068, 0.5], "11933": [5069, 0.5], "11934": [5070, 0.5], "11935": [5071, 0.5], "11936": [5072, 0.5], "11937": [5073, 0.5], "11938": [5074, 0.5], "11939": [5075, 0.5], "11940": [5076, 0.5], "11941": [5077, 0.5], "11942": [5078, 0.5], "11943": [5079, 0.5], "11944": [5080, 0.5], "11945": [5081, 0.5], "11946": [5082, 0.5], "11947": [5083, 0.5], "11948": [5084, 0.5], "11949": [5085, 0.5], "11950": [5086, 0.5], "11951": [5087, 0.5], "11952": [5088, 0.5], "11953": [5089, 0.5], "11954": [5090, 0.5], "11955": [5091, 0.5], "11956": [5092, 0.5], "11957": [5093, 0.5], "11958": [5094, 0.5], "11959": [5095, 0.5], "11960": [5096, 0.5], "11961": [5097, 0.5], "11962": [5098, 0.5], "11963": [5099, 0.5], "11964": [5100, 0.5], "11965": [5101, 0.5], "11966": [5102, 0.5], "11967": [5103, 0.5], "11968": [5104, 0.5], "11969": [5105, 0.5], "11970": [5106, 0.5], "11971": [5107, 0.5], "11972": [5108, 0.5], "11973": [5109, 0.5], "11974": [5110, 0.5], "11975": [5111, 0.5], "11976": [5112, 0.5], "11977": [5113, 0.5], "11978": [5114, 0.5], "11979": [5115, 0.5], "11980": [5116, 0.5], "11981": [5117, 0.5], "11982": [5118, 0.5], "11983": [5119, 0.5], "11984": [5120, 0.5], "11985": [5121, 0.5], "11986": [5122, 0.5], "11987": [5123, 0.5], "11988": [5124, 0.5], "11989": [5125, 0.5], "11990": [5126, 0.5], "11991": [5127, 0.5], "11992": [5128, 0.5], "11993": [5129, 0.5], "11994": [5130, 0.5], "11995": [5131, 0.5], "11996": [5132, 0.5], "11997": [5133, 0.5], "11998": [5134, 0.5], "11999": [5135, 0.5], "12000": [5136, 0.5], "12001": [5137, 0.5], "12002": [5138, 0.5], "12003": [5139, 0.5], "12004": [5140, 0.5], "12005": [5141, 0.5], "12006": [5142, 0.5], "12007": [5143, 0.5], "12008": [5144, 0.5], "12009": [5145, 0.5], "12010": [5146, 0.5], "12011": [5147, 0.5], "12012": [5148, 0.5], "12013": [5149, 0.5], "12014": [5150, 0.5], "12015": [5151, 0.5], "12016": [5152, 0.5], "12017": [5153, 0.5], "12018": [5154, 0.5], "12019": [5155, 0.5], "12020": [5156, 0.5], "12021": [5157, 0.5], "12022": [5158, 0.5], "12023": [5159, 0.5], "12024": [5160, 0.5], "12025": [5161, 0.5], "12026": [5162, 0.5], "12027": [5163, 0.5], "12028": [5164, 0.5], "12029": [5165, 0.5], "12030": [5166, 0.5], "12031": [5167, 0.5], "12032": [5168, 0.5], "12033": [5169, 0.5], "12034": [5170, 0.5], "12035": [5171, 0.5], "12036": [5172, 0.5], "12037": [5173, 0.5], "12038": [5174, 0.5], "12039": [5175, 0.5], "12040": [5176, 0.5], "12041": [5177, 0.5], "12042": [5178, 0.5], "12043": [5179, 0.5], "12044": [5180, 0.5], "12045": [5181, 0.5], "12046": [5182, 0.5], "12047": [5183, 0.5], "12048": [5184, 0.5], "12049": [5185, 0.5], "12050": [5186, 0.5], "12051": [5187, 0.5], "12052": [5188, 0.5], "12053": [5189, 0.5], "12054": [5190, 0.5], "12055": [5191, 0.5], "12056": [5192, 0.5], "12057": [5193, 0.5], "12058": [5194, 0.5], "12059": [5195, 0.5], "12060": [5196, 0.5], "12061": [5197, 0.5], "12062": [5198, 0.5], "12063": [5199, 0.5], "12064": [5200, 0.5], "12065": [5201, 0.5], "12066": [5202, 0.5], "12067": [5203, 0.5], "12068": [5204, 0.5], "12069": [5205, 0.5], "12070": [5206, 0.5], "12071": [5207, 0.5], "12072": [5208, 0.5], "12073": [5209, 0.5], "12074": [5210, 0.5], "12075": [5211, 0.5], "12076": [5212, 0.5], "12077": [5213, 0.5], "12078": [5214, 0.5], "12079": [5215, 0.5], "12080": [5216, 0.5], "12081": [5217, 0.5], "12082": [5218, 0.5], "12083": [5219, 0.5], "12084": [5220, 0.5], "12085": [5221, 0.5], "12086": [5222, 0.5], "12087": [5223, 0.5], "12088": [5224, 0.5], "12089": [5225, 0.5], "12090": [5226, 0.5], "12091": [5227, 0.5], "12092": [5228, 0.5], "12093": [5229, 0.5], "12094": [5230, 0.5], "12095": [5231, 0.5], "12096": [5232, 0.5], "12097": [5233, 0.5], "12098": [5234, 0.5], "12099": [5235, 0.5], "12100": [5236, 0.5], "12101": [5237, 0.5], "12102": [5238, 0.5], "12103": [5239, 0.5], "12104": [5240, 0.5], "12105": [5241, 0.5], "12106": [5242, 0.5], "12107": [5243, 0.5], "12108": [5244, 0.5], "12109": [5245, 0.5], "12110": [5246, 0.5], "12111": [5247, 0.5], "12112": [5248, 0.5], "12113": [5249, 0.5], "12114": [5250, 0.5], "12115": [5251, 0.5], "12116": [5252, 0.5], "12117": [5253, 0.5], "12118": [5254, 0.5], "12119": [5255, 0.5], "12120": [5256, 0.5], "12121": [5257, 0.5], "12122": [5258, 0.5], "12123": [5259, 0.5], "12124": [5260, 0.5], "12125": [5261, 0.5], "12126": [5262, 0.5], "12127": [5263, 0.5], "12128": [5264, 0.5], "12129": [5265, 0.5], "12130": [5266, 0.5], "12131": [5267, 0.5], "12132": [5268, 0.5], "12133": [5269, 0.5], "12134": [5270, 0.5], "12135": [5271, 0.5], "12136": [5272, 0.5], "12137": [5273, 0.5], "12138": [5274, 0.5], "12139": [5275, 0.5], "12140": [5276, 0.5], "12141": [5277, 0.5], "12142": [5278, 0.5], "12143": [5279, 0.5], "12144": [5280, 0.5], "12145": [5281, 0.5], "12146": [5282, 0.5], "12147": [5283, 0.5], "12148": [5284, 0.5], "12149": [5285, 0.5], "12150": [5286, 0.5], "12151": [5287, 0.5], "12152": [5288, 0.5], "12153": [5289, 0.5], "12154": [5290, 0.5], "12155": [5291, 0.5], "12156": [5292, 0.5], "12157": [5293, 0.5], "12158": [5294, 0.5], "12159": [5295, 0.5], "12160": [5296, 0.5], "12161": [5297, 0.5], "12162": [5298, 0.5], "12163": [5299, 0.5], "12164": [5300, 0.5], "12165": [5301, 0.5], "12166": [5302, 0.5], "12167": [5303, 0.5], "12168": [5304, 0.5], "12169": [5305, 0.5], "12170": [5306, 0.5], "12171": [5307, 0.5], "12172": [5308, 0.5], "12173": [5309, 0.5], "12174": [5310, 0.5], "12175": [5311, 0.5], "12176": [5312, 0.5], "12177": [5313, 0.5], "12178": [5314, 0.5], "12179": [5315, 0.5], "12180": [5316, 0.5], "12181": [5317, 0.5], "12182": [5318, 0.5], "12183": [5319, 0.5], "12184": [5320, 0.5], "12185": [5321, 0.5], "12186": [5322, 0.5], "12187": [5323, 0.5], "12188": [5324, 0.5], "12189": [5325, 0.5], "12190": [5326, 0.5], "12191": [5327, 0.5], "12192": [5328, 0.5], "12193": [5329, 0.5], "12194": [5330, 0.5], "12195": [5331, 0.5], "12196": [5332, 0.5], "12197": [5333, 0.5], "12198": [5334, 0.5], "12199": [5335, 0.5], "12200": [5336, 0.5], "12201": [5337, 0.5], "12202": [5338, 0.5], "12203": [5339, 0.5], "12204": [5340, 0.5], "12205": [5341, 0.5], "12206": [5342, 0.5], "12207": [5343, 0.5], "12208": [5344, 0.5], "12209": [5345, 0.5], "12210": [5346, 0.5], "12211": [5347, 0.5], "12212": [5348, 0.5], "12213": [5349, 0.5], "12214": [5350, 0.5], "12215": [5351, 0.5], "12216": [5352, 0.5], "12217": [5353, 0.5], "12218": [5354, 0.5], "12219": [5355, 0.5], "12220": [5356, 0.5], "12221": [5357, 0.5], "12222": [5358, 0.5], "12223": [5359, 0.5], "12224": [5360, 0.5], "12225": [5361, 0.5], "12226": [5362, 0.5], "12227": [5363, 0.5], "12228": [5364, 0.5], "12229": [5365, 0.5], "12230": [5366, 0.5], "12231": [5367, 0.5], "12232": [5368, 0.5], "12233": [5369, 0.5], "12234": [5370, 0.5], "12235": [5371, 0.5], "12236": [5372, 0.5], "12237": [5373, 0.5], "12238": [5374, 0.5], "12239": [5375, 0.5], "12240": [5376, 0.5], "12241": [5377, 0.5], "12242": [5378, 0.5], "12243": [5379, 0.5], "12244": [5380, 0.5], "12245": [5381, 0.5], "12246": [5382, 0.5], "12247": [5383, 0.5], "12248": [5384, 0.5], "12249": [5385, 0.5], "12250": [5386, 0.5], "12251": [5387, 0.5], "12252": [5388, 0.5], "12253": [5389, 0.5], "12254": [5390, 0.5], "12255": [5391, 0.5], "12256": [5392, 0.5], "12257": [5393, 0.5], "12258": [5394, 0.5], "12259": [5395, 0.5], "12260": [5396, 0.5], "12261": [5397, 0.5], "12262": [5398, 0.5], "12263": [5399, 0.5], "12264": [5400, 0.5], "12265": [5401, 0.5], "12266": [5402, 0.5], "12267": [5403, 0.5], "12268": [5404, 0.5], "12269": [5405, 0.5], "12270": [5406, 0.5], "12271": [5407, 0.5], "12272": [5408, 0.5], "12273": [5409, 0.5], "12274": [5410, 0.5], "12275": [5411, 0.5], "12300": [5412, 0.5], "12301": [5413, 0.5], "12302": [5414, 0.5], "12304": [5415, 0.5], "12307": [5416, 0.5], "12308": [5417, 0.5], "12310": [5418, 0.5], "12316": [5419, 0.5], "12317": [5420, 0.5], "12318": [5421, 0.5], "12320": [5422, 0.5], "12323": [5423, 0.5], "12324": [5424, 0.5], "12326": [5425, 0.5], "12332": [5426, 0.5], "12333": [5427, 0.5], "12334": [5428, 0.5], "12336": [5429, 0.5], "12339": [5430, 0.5], "12340": [5431, 0.5], "12342": [5432, 0.5], "12348": [5433, 0.5], "12349": [5434, 0.5], "12350": [5435, 0.5], "12352": [5436, 0.5], "12355": [5437, 0.5], "12356": [5438, 0.5], "12358": [5439, 0.5], "12364": [5440, 0.5], "12365": [5441, 0.5], "12366": [5442, 0.5], "12368": [5443, 0.5], "12371": [5444, 0.5], "12372": [5445, 0.5], "12374": [5446, 0.5], "12380": [5447, 0.5], "12381": [5448, 0.5], "12382": [5449, 0.5], "12384": [5450, 0.5], "12387": [5451, 0.5], "12388": [5452, 0.5], "12390": [5453, 0.5], "12501": [5662, 0.5], "12503": [5455, 0.5], "12517": [5663, 0.5], "12519": [5457, 0.5], "12533": [5664, 0.5], "12535": [5459, 0.5], "12549": [5665, 0.5], "12551": [5461, 0.5], "12565": [5666, 0.5], "12567": [5463, 0.5], "12581": [5667, 0.5], "12583": [5465, 0.5], "13002": [5466, 0.5], "13003": [5467, 0.5], "13005": [5468, 0.5], "13006": [5469, 0.5], "13007": [5470, 0.5], "13008": [5471, 0.5], "13018": [5472, 0.5], "13019": [5473, 0.5], "13021": [5474, 0.5], "13022": [5475, 0.5], "13023": [5476, 0.5], "13024": [5477, 0.5], "13034": [5478, 0.5], "13035": [5479, 0.5], "13037": [5480, 0.5], "13038": [5481, 0.5], "13039": [5482, 0.5], "13040": [5483, 0.5], "13050": [5484, 0.5], "13051": [5485, 0.5], "13053": [5486, 0.5], "13054": [5487, 0.5], "13055": [5488, 0.5], "13056": [5489, 0.5], "13066": [5490, 0.5], "13067": [5491, 0.5], "13069": [5492, 0.5], "13070": [5493, 0.5], "13071": [5494, 0.5], "13072": [5495, 0.5], "13082": [5496, 0.5], "13083": [5497, 0.5], "13085": [5498, 0.5], "13086": [5499, 0.5], "13087": [5500, 0.5], "13088": [5501, 0.5], "13098": [5502, 0.5], "13099": [5503, 0.5], "13101": [5504, 0.5], "13102": [5505, 0.5], "13103": [5506, 0.5], "13104": [5507, 0.5], "13114": [5508, 0.5], "13115": [5509, 0.5], "13117": [5510, 0.5], "13118": [5511, 0.5], "13119": [5512, 0.5], "13120": [5513, 0.5], "13130": [5514, 0.5], "13131": [5515, 0.5], "13133": [5516, 0.5], "13134": [5517, 0.5], "13135": [5518, 0.5], "13136": [5519, 0.5], "13146": [5520, 0.5], "13147": [5521, 0.5], "13149": [5522, 0.5], "13150": [5523, 0.5], "13151": [5524, 0.5], "13152": [5525, 0.5], "13300": [5526, 0.5], "13301": [5527, 0.5], "13302": [5528, 0.5], "13303": [5529, 0.5], "13304": [5530, 0.5], "13305": [5531, 0.5], "13306": [5532, 0.5], "13308": [5533, 0.5], "13316": [5534, 0.5], "13317": [5535, 0.5], "13318": [5536, 0.5], "13319": [5537, 0.5], "13320": [5538, 0.5], "13321": [5539, 0.5], "13322": [5540, 0.5], "13324": [5541, 0.5], "13332": [5542, 0.5], "13333": [5543, 0.5], "13334": [5544, 0.5], "13335": [5545, 0.5], "13336": [5546, 0.5], "13337": [5547, 0.5], "13338": [5548, 0.5], "13340": [5549, 0.5], "13348": [5550, 0.5], "13349": [5551, 0.5], "13350": [5552, 0.5], "13351": [5553, 0.5], "13352": [5554, 0.5], "13353": [5555, 0.5], "13354": [5556, 0.5], "13356": [5557, 0.5], "13364": [5558, 0.5], "13365": [5559, 0.5], "13366": [5560, 0.5], "13367": [5561, 0.5], "13368": [5562, 0.5], "13369": [5563, 0.5], "13370": [5564, 0.5], "13372": [5565, 0.5], "13380": [5566, 0.5], "13381": [5567, 0.5], "13382": [5568, 0.5], "13383": [5569, 0.5], "13384": [5570, 0.5], "13385": [5571, 0.5], "13386": [5572, 0.5], "13388": [5573, 0.5], "13396": [5574, 0.5], "13397": [5575, 0.5], "13398": [5576, 0.5], "13399": [5577, 0.5], "13400": [5578, 0.5], "13401": [5579, 0.5], "13402": [5580, 0.5], "13404": [5581, 0.5], "13412": [5582, 0.5], "13413": [5583, 0.5], "13414": [5584, 0.5], "13415": [5585, 0.5], "13416": [5586, 0.5], "13417": [5587, 0.5], "13418": [5588, 0.5], "13420": [5589, 0.5], "13428": [5590, 0.5], "13429": [5591, 0.5], "13430": [5592, 0.5], "13431": [5593, 0.5], "13432": [5594, 0.5], "13433": [5595, 0.5], "13434": [5596, 0.5], "13436": [5597, 0.5], "13444": [5598, 0.5], "13445": [5599, 0.5], "13446": [5600, 0.5], "13447": [5601, 0.5], "13448": [5602, 0.5], "13449": [5603, 0.5], "13450": [5604, 0.5], "13452": [5605, 0.5], "13460": [5606, 0.5], "13461": [5607, 0.5], "13462": [5608, 0.5], "13463": [5609, 0.5], "13464": [5610, 0.5], "13465": [5611, 0.5], "13466": [5612, 0.5], "13468": [5613, 0.5], "13476": [5614, 0.5], "13477": [5615, 0.5], "13478": [5616, 0.5], "13479": [5617, 0.5], "13480": [5618, 0.5], "13481": [5619, 0.5], "13482": [5620, 0.5], "13484": [5621, 0.5], "13492": [5622, 0.5], "13493": [5623, 0.5], "13494": [5624, 0.5], "13495": [5625, 0.5], "13496": [5626, 0.5], "13497": [5627, 0.5], "13498": [5628, 0.5], "13500": [5629, 0.5], "13508": [5630, 0.5], "13509": [5631, 0.5], "13510": [5632, 0.5], "13511": [5633, 0.5], "13512": [5634, 0.5], "13513": [5635, 0.5], "13514": [5636, 0.5], "13516": [5637, 0.5], "13524": [5638, 0.5], "13525": [5639, 0.5], "13526": [5640, 0.5], "13527": [5641, 0.5], "13528": [5642, 0.5], "13529": [5643, 0.5], "13530": [5644, 0.5], "13532": [5645, 0.5], "13540": [5646, 0.5], "13541": [5647, 0.5], "13542": [5648, 0.5], "13543": [5649, 0.5], "13544": [5650, 0.5], "13545": [5651, 0.5], "13546": [5652, 0.5], "13548": [5653, 0.5], "13556": [5654, 0.5], "13557": [5655, 0.5], "13558": [5656, 0.5], "13559": [5657, 0.5], "13560": [5658, 0.5], "13561": [5659, 0.5], "13562": [5660, 0.5], "13564": [5661, 0.5]};
const OSC_SPEC_ROWS = [
    [1000, "OSC 1 Source", 0, 13, 0, "", "sel", ["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080", "Granular", "Additive", "Modal Drum", "Spectral", "SoundFont", "Bagpipe"], 1, "Source", null],
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
    [1013, "OSC 1 Unison Voices", 1, 16, 1, "", "stp", null, 1, "Voices", null],
    [1014, "OSC 1 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1015, "OSC 1 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1016, "OSC 1 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1017, "OSC 1 Unison Style", 0, 5, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"], 1, "Detune Curve", null],
    [1028, "OSC 1 Unison Drift", 0, 1, 0, "", "sld", null, 1, "Drift", null],
    [1029, "OSC 1 Unison Phase", 0, 1, 0, "", "sld", null, 1, "Phase Spread", null],
    [1018, "OSC 1 Warp 1 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1019, "OSC 1 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1020, "OSC 1 Warp 2 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1021, "OSC 1 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1022, "OSC 1 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1023, "OSC 1 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1024, "OSC 1 Terrain A", 0, 11, 0, "", "sel", TERRAINS, 1, "Terrain", null],
    [1025, "OSC 1 Terrain Scale", 0, 1, 0.5, "", "sld", null, 1, "Scale", null],
    [1026, "OSC 1 Terrain Warp", 0, 1, 0, "", "sld", null, 1, "Warp", null],
    [1027, "OSC 1 Terrain Fold", 0, 1, 0, "", "sld", null, 1, "Fold", null],
    [1030, "OSC 1 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1031, "OSC 1 Filter Type", 0, 30, 0, "", "sel", OSC_FILTER_TYPES, 1, "Type", OSC_FILTER_GROUPS],
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
    [1042, "OSC 1 Distortion Type", 0, 7, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Wavedistortion"], 1, "Type", null],
    [1043, "OSC 1 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1044, "OSC 1 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1048, "OSC 1 Frequency", 0, 1, 0, "", "sld", null, 1, "Frequency", null],
    [1046, "OSC 1 Wavefilter Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1047, "OSC 1 Wavedistortion Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1049, "OSC 1 Wavefilter Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1050, "OSC 1 Wavefilter Range", 2, 14, 8, "oct", "sld", null, 1, "Range", null],
    [1051, "OSC 1 Wavefilter Warp", -1, 1, 0, "", "sld", null, 1, "Warp", null],
    [1052, "OSC 1 Wavefilter Contrast", -1, 1, 0, "", "sld", null, 1, "Contrast", null],
    [1053, "OSC 1 Wavefilter Tilt", -1, 1, 0, "", "sld", null, 1, "Tilt", null],
    [1054, "OSC 1 Wavefilter Spread", 0, 1, 0, "", "sld", null, 1, "Spread", null],
    [1055, "OSC 1 Wavefilter Gain Law", 0, 2, 0, "", "sel", ["Linear", "Bipolar", "dB"], 1, "Gain Law", null],
    [7000, "Inspirator On", 0, 1, 0, "", "btn", ["Off", "On"], 1, "On", null],
    [7001, "Insp Mode", 0, 4, 0, "", "sel", ["Chords", "Lead", "Bass", "Arp", "Drums"], 1, "Mode", null],
    [7002, "Insp Style", 0, 31, 0, "", "sel", ["Pop", "Rock", "Hip-Hop", "Trap", "Lo-Fi", "House", "Techno", "Jazz", "Neo-Soul", "Reggaeton", "Drum & Bass", "Afrobeats", "Funk", "Dub", "Disco", "Bossa Nova", "Synthwave", "Dubstep", "Trance", "Drill", "UK Garage", "Salsa", "Metal", "Country", "Blues", "Ambient", "Ska", "Amapiano", "Breakbeat", "Gospel", "Hardstyle", "Moombahton"], 1, "Style", null],
    [7003, "Insp Key", 0, 11, 0, "", "sel", ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"], 1, "Key", null],
    [7004, "Insp Scale", 0, 6, 0, "", "sel", ["Major", "Minor", "Dorian", "Mixolydian", "Phrygian", "Lydian", "Harm Minor"], 1, "Scale", null],
    [7005, "Insp Song Seed", 0, 9999, 1234, "", "knb", null, 1, "Song Seed", null],
    [7006, "Insp Part Seed", 0, 9999, 1, "", "knb", null, 1, "Part Seed", null],
    [7007, "Insp Variation", 0, 99, 0, "", "knb", null, 1, "Variation", null],
    [7008, "Insp Bars", 0, 3, 2, "", "sel", ["1", "2", "4", "8"], 1, "Bars", null],
    [7009, "Insp Swing", 0, 100, 0, "", "knb", null, 1, "Swing", null],
    [7010, "Insp MIDI In", 0, 2, 0, "", "sel", ["Transpose", "Hold", "Off"], 1, "MIDI In", null],
    [7011, "Insp Lock Chords", 0, 63, 0, "", "knb", null, 1, "Lock Chords", null],
    [7012, "Insp Chord Bar 1", 0, 255, 0, "", "knb", null, 1, "Chord Bar 1", null],
    [7013, "Insp Chord Bar 2", 0, 255, 0, "", "knb", null, 1, "Chord Bar 2", null],
    [7014, "Insp Chord Bar 3", 0, 255, 0, "", "knb", null, 1, "Chord Bar 3", null],
    [7015, "Insp Chord Bar 4", 0, 255, 0, "", "knb", null, 1, "Chord Bar 4", null],
    [7016, "Insp Chord Bar 5", 0, 255, 0, "", "knb", null, 1, "Chord Bar 5", null],
    [7017, "Insp Chord Bar 6", 0, 255, 0, "", "knb", null, 1, "Chord Bar 6", null],
    [7018, "Insp Chord Bar 7", 0, 255, 0, "", "knb", null, 1, "Chord Bar 7", null],
    [7019, "Insp Chord Bar 8", 0, 255, 0, "", "knb", null, 1, "Chord Bar 8", null],
    [7020, "Insp Edit Kick A", 0, 16777215, 0, "", "knb", null, 1, "Edit Kick A", null],
    [7021, "Insp Edit Kick B", 0, 16777215, 0, "", "knb", null, 1, "Edit Kick B", null],
    [7022, "Insp Edit Snare A", 0, 16777215, 0, "", "knb", null, 1, "Edit Snare A", null],
    [7023, "Insp Edit Snare B", 0, 16777215, 0, "", "knb", null, 1, "Edit Snare B", null],
    [7024, "Insp Edit Clap A", 0, 16777215, 0, "", "knb", null, 1, "Edit Clap A", null],
    [7025, "Insp Edit Clap B", 0, 16777215, 0, "", "knb", null, 1, "Edit Clap B", null],
    [7026, "Insp Edit Hat A", 0, 16777215, 0, "", "knb", null, 1, "Edit Hat A", null],
    [7027, "Insp Edit Hat B", 0, 16777215, 0, "", "knb", null, 1, "Edit Hat B", null],
    [7028, "Insp Edit Open Hat A", 0, 16777215, 0, "", "knb", null, 1, "Edit Open Hat A", null],
    [7029, "Insp Edit Open Hat B", 0, 16777215, 0, "", "knb", null, 1, "Edit Open Hat B", null],
    [7030, "Insp Edit Rim A", 0, 16777215, 0, "", "knb", null, 1, "Edit Rim A", null],
    [7031, "Insp Edit Rim B", 0, 16777215, 0, "", "knb", null, 1, "Edit Rim B", null],
    [7032, "Insp Edit Tom A", 0, 16777215, 0, "", "knb", null, 1, "Edit Tom A", null],
    [7033, "Insp Edit Tom B", 0, 16777215, 0, "", "knb", null, 1, "Edit Tom B", null],
    [7034, "Insp Edit Ride A", 0, 16777215, 0, "", "knb", null, 1, "Edit Ride A", null],
    [7035, "Insp Edit Ride B", 0, 16777215, 0, "", "knb", null, 1, "Edit Ride B", null],
    [7036, "Insp Kick Random", 0, 100, 0, "", "knb", null, 1, "Kick Random", null],
    [7037, "Insp Snare Random", 0, 100, 10, "", "knb", null, 1, "Snare Random", null],
    [7038, "Insp Clap Random", 0, 100, 0, "", "knb", null, 1, "Clap Random", null],
    [7039, "Insp Hat Random", 0, 100, 35, "", "knb", null, 1, "Hat Random", null],
    [7040, "Insp Open Hat Random", 0, 100, 15, "", "knb", null, 1, "Open Hat Random", null],
    [7041, "Insp Rim Random", 0, 100, 20, "", "knb", null, 1, "Rim Random", null],
    [7042, "Insp Tom Random", 0, 100, 10, "", "knb", null, 1, "Tom Random", null],
    [7043, "Insp Ride Random", 0, 100, 30, "", "knb", null, 1, "Ride Random", null],
    [7044, "Insp Chords Complexity", 0, 100, 40, "", "knb", null, 1, "Complexity", null],
    [7045, "Insp Chords Density", 0, 100, 50, "", "knb", null, 1, "Density", null],
    [7046, "Insp Chords Humanize", 0, 100, 15, "", "knb", null, 1, "Humanize", null],
    [7047, "Insp Chords Octave", -2, 2, 0, "", "knb", null, 1, "Octave", null],
    [7048, "Insp Chords Range", 0, 100, 50, "", "knb", null, 1, "Range", null],
    [7049, "Insp Chords Gate", 10, 100, 80, "", "knb", null, 1, "Gate", null],
    [7050, "Insp Chords Velocity", 1, 127, 96, "", "knb", null, 1, "Velocity", null],
    [7051, "Insp Chords Vel Random", 0, 100, 10, "", "knb", null, 1, "Vel Random", null],
    [7052, "Insp Chords Dur Random", 0, 100, 0, "", "knb", null, 1, "Dur Random", null],
    [7053, "Insp Lead Complexity", 0, 100, 40, "", "knb", null, 1, "Complexity", null],
    [7054, "Insp Lead Density", 0, 100, 50, "", "knb", null, 1, "Density", null],
    [7055, "Insp Lead Humanize", 0, 100, 15, "", "knb", null, 1, "Humanize", null],
    [7056, "Insp Lead Octave", -2, 2, 0, "", "knb", null, 1, "Octave", null],
    [7057, "Insp Lead Range", 0, 100, 50, "", "knb", null, 1, "Range", null],
    [7058, "Insp Lead Gate", 10, 100, 80, "", "knb", null, 1, "Gate", null],
    [7059, "Insp Lead Velocity", 1, 127, 100, "", "knb", null, 1, "Velocity", null],
    [7060, "Insp Lead Vel Random", 0, 100, 20, "", "knb", null, 1, "Vel Random", null],
    [7061, "Insp Lead Dur Random", 0, 100, 15, "", "knb", null, 1, "Dur Random", null],
    [7062, "Insp Bass Complexity", 0, 100, 40, "", "knb", null, 1, "Complexity", null],
    [7063, "Insp Bass Density", 0, 100, 50, "", "knb", null, 1, "Density", null],
    [7064, "Insp Bass Humanize", 0, 100, 10, "", "knb", null, 1, "Humanize", null],
    [7065, "Insp Bass Octave", -2, 2, 0, "", "knb", null, 1, "Octave", null],
    [7066, "Insp Bass Range", 0, 100, 50, "", "knb", null, 1, "Range", null],
    [7067, "Insp Bass Gate", 10, 100, 80, "", "knb", null, 1, "Gate", null],
    [7068, "Insp Bass Velocity", 1, 127, 100, "", "knb", null, 1, "Velocity", null],
    [7069, "Insp Bass Vel Random", 0, 100, 10, "", "knb", null, 1, "Vel Random", null],
    [7070, "Insp Bass Dur Random", 0, 100, 0, "", "knb", null, 1, "Dur Random", null],
    [7071, "Insp Arp Complexity", 0, 100, 40, "", "knb", null, 1, "Complexity", null],
    [7072, "Insp Arp Density", 0, 100, 50, "", "knb", null, 1, "Density", null],
    [7073, "Insp Arp Humanize", 0, 100, 10, "", "knb", null, 1, "Humanize", null],
    [7074, "Insp Arp Octave", -2, 2, 0, "", "knb", null, 1, "Octave", null],
    [7075, "Insp Arp Range", 0, 100, 50, "", "knb", null, 1, "Range", null],
    [7076, "Insp Arp Gate", 10, 100, 70, "", "knb", null, 1, "Gate", null],
    [7077, "Insp Arp Velocity", 1, 127, 92, "", "knb", null, 1, "Velocity", null],
    [7078, "Insp Arp Vel Random", 0, 100, 15, "", "knb", null, 1, "Vel Random", null],
    [7079, "Insp Arp Dur Random", 0, 100, 0, "", "knb", null, 1, "Dur Random", null],
    [7080, "Insp Drums Complexity", 0, 100, 40, "", "knb", null, 1, "Complexity", null],
    [7081, "Insp Drums Density", 0, 100, 50, "", "knb", null, 1, "Density", null],
    [7082, "Insp Drums Humanize", 0, 100, 10, "", "knb", null, 1, "Humanize", null],
    [7083, "Insp Fill Edit 1", 0, 16777215, 0, "", "knb", null, 1, "Fill Edit 1", null],
    [7084, "Insp Fill Edit 2", 0, 16777215, 0, "", "knb", null, 1, "Fill Edit 2", null],
    [7085, "Insp Fill Edit 3", 0, 16777215, 0, "", "knb", null, 1, "Fill Edit 3", null],
    [7086, "Insp Drums Velocity", 1, 127, 96, "", "knb", null, 1, "Velocity", null],
    [7087, "Insp Drums Vel Random", 0, 100, 0, "", "knb", null, 1, "Vel Random", null],
    [7088, "Insp Fill Edit 4", 0, 16777215, 0, "", "knb", null, 1, "Fill Edit 4", null],
    [7089, "Insp Timing Offset", -50, 50, 0, "ms", "knb", null, 1, "Timing Offset", null],
    [7090, "Insp Edit Pedal Hat A", 0, 16777215, 0, "", "knb", null, 1, "Edit Pedal Hat A", null],
    [7091, "Insp Edit Pedal Hat B", 0, 16777215, 0, "", "knb", null, 1, "Edit Pedal Hat B", null],
    [7092, "Insp Edit Low Tom A", 0, 16777215, 0, "", "knb", null, 1, "Edit Low Tom A", null],
    [7093, "Insp Edit Low Tom B", 0, 16777215, 0, "", "knb", null, 1, "Edit Low Tom B", null],
    [7094, "Insp Edit High Tom A", 0, 16777215, 0, "", "knb", null, 1, "Edit High Tom A", null],
    [7095, "Insp Edit High Tom B", 0, 16777215, 0, "", "knb", null, 1, "Edit High Tom B", null],
    [7096, "Insp Edit Crash A", 0, 16777215, 0, "", "knb", null, 1, "Edit Crash A", null],
    [7097, "Insp Edit Crash B", 0, 16777215, 0, "", "knb", null, 1, "Edit Crash B", null],
    [7098, "Insp Pedal Hat Random", 0, 100, 20, "", "knb", null, 1, "Pedal Hat Random", null],
    [7099, "Insp Low Tom Random", 0, 100, 10, "", "knb", null, 1, "Low Tom Random", null],
    [7100, "Insp High Tom Random", 0, 100, 10, "", "knb", null, 1, "High Tom Random", null],
    [7101, "Insp Crash Random", 0, 100, 0, "", "knb", null, 1, "Crash Random", null],
    [7102, "Insp Kick Density", 0, 100, 50, "", "knb", null, 1, "Kick Density", null],
    [7103, "Insp Snare Density", 0, 100, 50, "", "knb", null, 1, "Snare Density", null],
    [7104, "Insp Clap Density", 0, 100, 50, "", "knb", null, 1, "Clap Density", null],
    [7105, "Insp Hat Density", 0, 100, 50, "", "knb", null, 1, "Hat Density", null],
    [7106, "Insp Open Hat Density", 0, 100, 50, "", "knb", null, 1, "Open Hat Density", null],
    [7107, "Insp Rim Density", 0, 100, 50, "", "knb", null, 1, "Rim Density", null],
    [7108, "Insp Mid Tom Density", 0, 100, 50, "", "knb", null, 1, "Mid Tom Density", null],
    [7109, "Insp Ride Density", 0, 100, 50, "", "knb", null, 1, "Ride Density", null],
    [7110, "Insp Pedal Hat Density", 0, 100, 50, "", "knb", null, 1, "Pedal Hat Density", null],
    [7111, "Insp Low Tom Density", 0, 100, 50, "", "knb", null, 1, "Low Tom Density", null],
    [7112, "Insp High Tom Density", 0, 100, 50, "", "knb", null, 1, "High Tom Density", null],
    [7113, "Insp Crash Density", 0, 100, 50, "", "knb", null, 1, "Crash Density", null],
    [7114, "Insp Push", 0, 100, 0, "", "knb", null, 1, "Push", null],
    [7115, "Insp Kick Note", 0, 127, 36, "", "knb", null, 1, "Kick Note", null],
    [7116, "Insp Snare Note", 0, 127, 38, "", "knb", null, 1, "Snare Note", null],
    [7117, "Insp Clap Note", 0, 127, 39, "", "knb", null, 1, "Clap Note", null],
    [7118, "Insp Hat Note", 0, 127, 42, "", "knb", null, 1, "Hat Note", null],
    [7119, "Insp Open Hat Note", 0, 127, 46, "", "knb", null, 1, "Open Hat Note", null],
    [7120, "Insp Rim Note", 0, 127, 37, "", "knb", null, 1, "Rim Note", null],
    [7121, "Insp Mid Tom Note", 0, 127, 45, "", "knb", null, 1, "Mid Tom Note", null],
    [7122, "Insp Ride Note", 0, 127, 51, "", "knb", null, 1, "Ride Note", null],
    [7123, "Insp Pedal Hat Note", 0, 127, 44, "", "knb", null, 1, "Pedal Hat Note", null],
    [7124, "Insp Low Tom Note", 0, 127, 41, "", "knb", null, 1, "Low Tom Note", null],
    [7125, "Insp High Tom Note", 0, 127, 50, "", "knb", null, 1, "High Tom Note", null],
    [7126, "Insp Crash Note", 0, 127, 49, "", "knb", null, 1, "Crash Note", null],
    [7127, "Insp Chord Rate", 0, 2, 1, "", "sel", ["Half", "Normal", "Double"], 1, "Chord Rate", null],
    [7128, "Insp Fill Every", 0, 3, 2, "", "sel", ["Off", "2 Bars", "4 Bars", "8 Bars"], 1, "Fill Every", null],
    [7129, "Insp Lock Bars", 0, 255, 0, "", "knb", null, 1, "Lock Bars", null],
    [7130, "Insp Inversion", 0, 3, 0, "", "knb", null, 1, "Inversion", null],
    [7131, "Insp Spread", 0, 2, 0, "", "sel", ["Close", "Open", "Wide"], 1, "Spread", null],
    [7132, "Insp Strum", 0, 100, 0, "", "knb", null, 1, "Strum", null],
    [7133, "Insp Figure", 0, 4, 0, "", "sel", ["Block", "Up", "Down", "Up-Down", "Alberti"], 1, "Figure", null],
    [7134, "Insp Ghost Notes", 0, 100, 0, "", "knb", null, 1, "Ghost Notes", null],
    [7135, "Insp Chord Pull", 0, 100, 0, "", "knb", null, 1, "Chord Pull", null],
    [7136, "Insp Max Leap", 1, 12, 12, "", "knb", null, 1, "Max Leap", null],
    [7137, "Insp Mutate", 0, 100, 0, "", "knb", null, 1, "Mutate", null],
    [7138, "Insp Melody Degree", 0, 7, 0, "", "sel", ["Free", "I", "II", "III", "IV", "V", "VI", "VII"], 1, "Degree", null],
    [7139, "Insp Generator", 0, 9, 0, "", "sel", ["Classic", "Euclid", "Markov", "Cellular", "L-System", "Import", "Walk", "Permute", "Trance", "Genre"], 1, "Generator", null],
    [7140, "Insp Gen Variant", 0, 15, 0, "", "knb", null, 1, "Variant", null],
    [7141, "Insp Chord Bass", 0, 2, 0, "", "sel", ["Off", "Root", "Root+Oct"], 1, "Chord Bass", null],
    [7142, "Insp Drum Chance", 0, 100, 100, "", "knb", null, 1, "Chance", null],
    [7143, "Insp Ratchet", 0, 100, 0, "", "knb", null, 1, "Ratchet", null],
    [7144, "Insp Poly", 0, 3, 0, "", "sel", ["Off", "A 12:5:7", "B 10:7:9", "C 14:5:11"], 1, "Poly", null],
    [7200, "MSEG1 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7201, "MSEG1 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7202, "MSEG1 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7203, "MSEG1 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7204, "MSEG1 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7205, "MSEG1 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7206, "MSEG1 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7207, "MSEG1 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7208, "MSEG1 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7209, "MSEG1 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7210, "MSEG1 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7211, "MSEG1 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7212, "MSEG1 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7213, "MSEG1 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7214, "MSEG1 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7215, "MSEG1 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7216, "MSEG1 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7217, "MSEG1 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7218, "MSEG1 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7219, "MSEG1 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7220, "MSEG1 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7221, "MSEG1 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7222, "MSEG1 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7223, "MSEG1 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7224, "MSEG1 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7225, "MSEG1 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7226, "MSEG1 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7227, "MSEG1 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7228, "MSEG1 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7229, "MSEG1 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7230, "MSEG2 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7231, "MSEG2 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7232, "MSEG2 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7233, "MSEG2 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7234, "MSEG2 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7235, "MSEG2 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7236, "MSEG2 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7237, "MSEG2 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7238, "MSEG2 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7239, "MSEG2 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7240, "MSEG2 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7241, "MSEG2 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7242, "MSEG2 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7243, "MSEG2 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7244, "MSEG2 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7245, "MSEG2 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7246, "MSEG2 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7247, "MSEG2 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7248, "MSEG2 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7249, "MSEG2 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7250, "MSEG2 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7251, "MSEG2 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7252, "MSEG2 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7253, "MSEG2 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7254, "MSEG2 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7255, "MSEG2 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7256, "MSEG2 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7257, "MSEG2 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7258, "MSEG2 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7259, "MSEG2 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7260, "MSEG3 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7261, "MSEG3 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7262, "MSEG3 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7263, "MSEG3 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7264, "MSEG3 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7265, "MSEG3 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7266, "MSEG3 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7267, "MSEG3 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7268, "MSEG3 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7269, "MSEG3 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7270, "MSEG3 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7271, "MSEG3 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7272, "MSEG3 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7273, "MSEG3 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7274, "MSEG3 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7275, "MSEG3 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7276, "MSEG3 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7277, "MSEG3 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7278, "MSEG3 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7279, "MSEG3 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7280, "MSEG3 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7281, "MSEG3 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7282, "MSEG3 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7283, "MSEG3 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7284, "MSEG3 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7285, "MSEG3 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7286, "MSEG3 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7287, "MSEG3 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7288, "MSEG3 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7289, "MSEG3 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7290, "MSEG4 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7291, "MSEG4 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7292, "MSEG4 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7293, "MSEG4 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7294, "MSEG4 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7295, "MSEG4 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7296, "MSEG4 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7297, "MSEG4 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7298, "MSEG4 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7299, "MSEG4 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7300, "MSEG4 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7301, "MSEG4 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7302, "MSEG4 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7303, "MSEG4 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7304, "MSEG4 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7305, "MSEG4 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7306, "MSEG4 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7307, "MSEG4 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7308, "MSEG4 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7309, "MSEG4 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7310, "MSEG4 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7311, "MSEG4 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7312, "MSEG4 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7313, "MSEG4 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7314, "MSEG4 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7315, "MSEG4 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7316, "MSEG4 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7317, "MSEG4 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7318, "MSEG4 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7319, "MSEG4 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7320, "MSEG5 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7321, "MSEG5 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7322, "MSEG5 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7323, "MSEG5 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7324, "MSEG5 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7325, "MSEG5 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7326, "MSEG5 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7327, "MSEG5 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7328, "MSEG5 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7329, "MSEG5 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7330, "MSEG5 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7331, "MSEG5 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7332, "MSEG5 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7333, "MSEG5 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7334, "MSEG5 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7335, "MSEG5 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7336, "MSEG5 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7337, "MSEG5 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7338, "MSEG5 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7339, "MSEG5 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7340, "MSEG5 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7341, "MSEG5 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7342, "MSEG5 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7343, "MSEG5 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7344, "MSEG5 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7345, "MSEG5 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7346, "MSEG5 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7347, "MSEG5 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7348, "MSEG5 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7349, "MSEG5 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7350, "MSEG6 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7351, "MSEG6 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7352, "MSEG6 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7353, "MSEG6 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7354, "MSEG6 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7355, "MSEG6 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7356, "MSEG6 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7357, "MSEG6 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7358, "MSEG6 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7359, "MSEG6 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7360, "MSEG6 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7361, "MSEG6 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7362, "MSEG6 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7363, "MSEG6 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7364, "MSEG6 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7365, "MSEG6 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7366, "MSEG6 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7367, "MSEG6 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7368, "MSEG6 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7369, "MSEG6 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7370, "MSEG6 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7371, "MSEG6 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7372, "MSEG6 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7373, "MSEG6 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7374, "MSEG6 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7375, "MSEG6 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7376, "MSEG6 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7377, "MSEG6 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7378, "MSEG6 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7379, "MSEG6 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7380, "MSEG7 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7381, "MSEG7 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7382, "MSEG7 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7383, "MSEG7 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7384, "MSEG7 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7385, "MSEG7 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7386, "MSEG7 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7387, "MSEG7 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7388, "MSEG7 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7389, "MSEG7 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7390, "MSEG7 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7391, "MSEG7 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7392, "MSEG7 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7393, "MSEG7 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7394, "MSEG7 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7395, "MSEG7 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7396, "MSEG7 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7397, "MSEG7 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7398, "MSEG7 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7399, "MSEG7 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7400, "MSEG7 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7401, "MSEG7 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7402, "MSEG7 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7403, "MSEG7 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7404, "MSEG7 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7405, "MSEG7 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7406, "MSEG7 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7407, "MSEG7 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7408, "MSEG7 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7409, "MSEG7 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7410, "MSEG8 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7411, "MSEG8 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7412, "MSEG8 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7413, "MSEG8 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7414, "MSEG8 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7415, "MSEG8 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7416, "MSEG8 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7417, "MSEG8 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7418, "MSEG8 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7419, "MSEG8 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7420, "MSEG8 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7421, "MSEG8 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7422, "MSEG8 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7423, "MSEG8 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7424, "MSEG8 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7425, "MSEG8 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7426, "MSEG8 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7427, "MSEG8 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7428, "MSEG8 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7429, "MSEG8 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7430, "MSEG8 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7431, "MSEG8 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7432, "MSEG8 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7433, "MSEG8 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7434, "MSEG8 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7435, "MSEG8 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7436, "MSEG8 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7437, "MSEG8 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7438, "MSEG8 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7439, "MSEG8 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7440, "MSEG9 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7441, "MSEG9 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7442, "MSEG9 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7443, "MSEG9 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7444, "MSEG9 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7445, "MSEG9 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7446, "MSEG9 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7447, "MSEG9 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7448, "MSEG9 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7449, "MSEG9 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7450, "MSEG9 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7451, "MSEG9 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7452, "MSEG9 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7453, "MSEG9 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7454, "MSEG9 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7455, "MSEG9 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7456, "MSEG9 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7457, "MSEG9 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7458, "MSEG9 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7459, "MSEG9 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7460, "MSEG9 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7461, "MSEG9 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7462, "MSEG9 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7463, "MSEG9 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7464, "MSEG9 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7465, "MSEG9 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7466, "MSEG9 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7467, "MSEG9 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7468, "MSEG9 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7469, "MSEG9 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7470, "MSEG10 Mode", 0.0, 1.0, 0.0, "", "sel", ["ADSR", "MSEG"], 1, "Mode", null],
    [7471, "MSEG10 Nodes", 2.0, 8.0, 3.0, "", "knb", null, 1, "Nodes", null],
    [7472, "MSEG10 Sustain", 0.0, 8.0, 2.0, "", "knb", null, 1, "Sustain", null],
    [7473, "MSEG10 Loop", 0.0, 1.0, 0.0, "", "sel", ["Off", "On"], 1, "Loop", null],
    [7474, "MSEG10 Loop Start", 1.0, 8.0, 1.0, "", "knb", null, 1, "Loop Start", null],
    [7475, "MSEG10 Loop End", 1.0, 8.0, 2.0, "", "knb", null, 1, "Loop End", null],
    [7476, "MSEG10 Node 1 Time", 0.0, 10000.0, 10.0, "", "knb", null, 1, "Time", null],
    [7477, "MSEG10 Node 1 Level", 0.0, 1.0, 1.00, "", "knb", null, 1, "Level", null],
    [7478, "MSEG10 Node 1 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7479, "MSEG10 Node 2 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7480, "MSEG10 Node 2 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7481, "MSEG10 Node 2 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7482, "MSEG10 Node 3 Time", 0.0, 10000.0, 300.0, "", "knb", null, 1, "Time", null],
    [7483, "MSEG10 Node 3 Level", 0.0, 1.0, 0.00, "", "knb", null, 1, "Level", null],
    [7484, "MSEG10 Node 3 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7485, "MSEG10 Node 4 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7486, "MSEG10 Node 4 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7487, "MSEG10 Node 4 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7488, "MSEG10 Node 5 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7489, "MSEG10 Node 5 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7490, "MSEG10 Node 5 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7491, "MSEG10 Node 6 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7492, "MSEG10 Node 6 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7493, "MSEG10 Node 6 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7494, "MSEG10 Node 7 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7495, "MSEG10 Node 7 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7496, "MSEG10 Node 7 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7497, "MSEG10 Node 8 Time", 0.0, 10000.0, 100.0, "", "knb", null, 1, "Time", null],
    [7498, "MSEG10 Node 8 Level", 0.0, 1.0, 0.50, "", "knb", null, 1, "Level", null],
    [7499, "MSEG10 Node 8 Curve", -1.0, 1.0, 0.0, "", "knb", null, 1, "Curve", null],
    [7500, "RND1 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7501, "RND1 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7502, "RND1 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7503, "RND1 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7504, "RND1 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7505, "RND1 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7506, "RND1 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7507, "RND1 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7508, "RND2 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7509, "RND2 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7510, "RND2 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7511, "RND2 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7512, "RND2 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7513, "RND2 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7514, "RND2 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7515, "RND2 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7516, "RND3 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7517, "RND3 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7518, "RND3 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7519, "RND3 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7520, "RND3 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7521, "RND3 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7522, "RND3 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7523, "RND3 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7524, "RND4 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7525, "RND4 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7526, "RND4 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7527, "RND4 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7528, "RND4 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7529, "RND4 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7530, "RND4 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7531, "RND4 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7532, "RND5 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7533, "RND5 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7534, "RND5 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7535, "RND5 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7536, "RND5 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7537, "RND5 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7538, "RND5 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7539, "RND5 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7540, "RND6 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7541, "RND6 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7542, "RND6 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7543, "RND6 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7544, "RND6 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7545, "RND6 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7546, "RND6 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7547, "RND6 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7548, "RND7 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7549, "RND7 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7550, "RND7 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7551, "RND7 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7552, "RND7 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7553, "RND7 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7554, "RND7 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7555, "RND7 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7556, "RND8 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7557, "RND8 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7558, "RND8 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7559, "RND8 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7560, "RND8 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7561, "RND8 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7562, "RND8 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7563, "RND8 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7564, "RND9 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7565, "RND9 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7566, "RND9 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7567, "RND9 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7568, "RND9 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7569, "RND9 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7570, "RND9 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7571, "RND9 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [7572, "RND10 Mode", 0.0, 3.0, 0.0, "", "sel", ["Note", "S&H", "Glide", "Walk"], 1, "Mode", null],
    [7573, "RND10 Rate", 0.05, 50.0, 4.0, "", "knb", null, 1, "Rate", null],
    [7574, "RND10 Sync", 0.0, 1.0, 0.0, "", "sel", ["Free", "Sync"], 1, "Sync", null],
    [7575, "RND10 Division", 0.0, 17.0, 8.0, "", "sel", ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"], 1, "", null],
    [7576, "RND10 Smooth", 0.0, 1.0, 0.0, "", "knb", null, 1, "Smooth", null],
    [7577, "RND10 Distribution", 0.0, 3.0, 0.0, "", "sel", ["Uniform", "Gauss", "Binary", "Steps"], 1, "Distribution", null],
    [7578, "RND10 Polarity", 0.0, 1.0, 0.0, "", "sel", ["Bipolar", "Unipolar"], 1, "Polarity", null],
    [7579, "RND10 Seed", 0.0, 16.0, 0.0, "", "knb", null, 1, "Seed", null],
    [1045, "OSC 1 Pre-Matrix Order", 0, 5, 0, "", "sel", ["Filter > Dist > Reso", "Dist > Filter > Reso", "Filter > Reso > Dist", "Reso > Filter > Dist", "Dist > Reso > Filter", "Reso > Dist > Filter"], 1, "Order", null],
    [1056, "OSC 1 Resonator On", 0, 1, 0, "", "btn", ["Off", "On"], 1, "On", null],
    [1057, "OSC 1 Resonator Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1058, "OSC 1 Resonator Decay", 0.02, 20, 1.0, "s", "sld", null, 1, "Decay", null],
    [1059, "OSC 1 Resonator Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1060, "OSC 1 Resonator Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [1061, "OSC 1 Resonator Inharmonicity", 0, 1, 0, "", "sld", null, 1, "Inharm", null],
    [1062, "OSC 1 Resonator Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1063, "OSC 1 Resonator Mix", 0, 1, 0.5, "", "sld", null, 1, "Mix", null],
    [1064, "OSC 2 Source", 0, 13, 0, "", "sel", ["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080", "Granular", "Additive", "Modal Drum", "Spectral", "SoundFont", "Bagpipe"], 1, "Source", null],
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
    [1077, "OSC 2 Unison Voices", 1, 16, 1, "", "stp", null, 1, "Voices", null],
    [1078, "OSC 2 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1079, "OSC 2 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1080, "OSC 2 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1081, "OSC 2 Unison Style", 0, 5, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"], 1, "Detune Curve", null],
    [1092, "OSC 2 Unison Drift", 0, 1, 0, "", "sld", null, 1, "Drift", null],
    [1093, "OSC 2 Unison Phase", 0, 1, 0, "", "sld", null, 1, "Phase Spread", null],
    [1082, "OSC 2 Warp 1 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1083, "OSC 2 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1084, "OSC 2 Warp 2 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1085, "OSC 2 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1086, "OSC 2 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1087, "OSC 2 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1088, "OSC 2 Terrain A", 0, 11, 0, "", "sel", TERRAINS, 1, "Terrain", null],
    [1089, "OSC 2 Terrain Scale", 0, 1, 0.5, "", "sld", null, 1, "Scale", null],
    [1090, "OSC 2 Terrain Warp", 0, 1, 0, "", "sld", null, 1, "Warp", null],
    [1091, "OSC 2 Terrain Fold", 0, 1, 0, "", "sld", null, 1, "Fold", null],
    [1094, "OSC 2 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1095, "OSC 2 Filter Type", 0, 30, 0, "", "sel", OSC_FILTER_TYPES, 1, "Type", OSC_FILTER_GROUPS],
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
    [1106, "OSC 2 Distortion Type", 0, 7, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Wavedistortion"], 1, "Type", null],
    [1107, "OSC 2 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1108, "OSC 2 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1112, "OSC 2 Frequency", 0, 1, 0, "", "sld", null, 1, "Frequency", null],
    [1110, "OSC 2 Wavefilter Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1111, "OSC 2 Wavedistortion Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1113, "OSC 2 Wavefilter Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1114, "OSC 2 Wavefilter Range", 2, 14, 8, "oct", "sld", null, 1, "Range", null],
    [1115, "OSC 2 Wavefilter Warp", -1, 1, 0, "", "sld", null, 1, "Warp", null],
    [1116, "OSC 2 Wavefilter Contrast", -1, 1, 0, "", "sld", null, 1, "Contrast", null],
    [1117, "OSC 2 Wavefilter Tilt", -1, 1, 0, "", "sld", null, 1, "Tilt", null],
    [1118, "OSC 2 Wavefilter Spread", 0, 1, 0, "", "sld", null, 1, "Spread", null],
    [1119, "OSC 2 Wavefilter Gain Law", 0, 2, 0, "", "sel", ["Linear", "Bipolar", "dB"], 1, "Gain Law", null],
    [1109, "OSC 2 Pre-Matrix Order", 0, 5, 0, "", "sel", ["Filter > Dist > Reso", "Dist > Filter > Reso", "Filter > Reso > Dist", "Reso > Filter > Dist", "Dist > Reso > Filter", "Reso > Dist > Filter"], 1, "Order", null],
    [1120, "OSC 2 Resonator On", 0, 1, 0, "", "btn", ["Off", "On"], 1, "On", null],
    [1121, "OSC 2 Resonator Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1122, "OSC 2 Resonator Decay", 0.02, 20, 1.0, "s", "sld", null, 1, "Decay", null],
    [1123, "OSC 2 Resonator Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1124, "OSC 2 Resonator Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [1125, "OSC 2 Resonator Inharmonicity", 0, 1, 0, "", "sld", null, 1, "Inharm", null],
    [1126, "OSC 2 Resonator Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1127, "OSC 2 Resonator Mix", 0, 1, 0.5, "", "sld", null, 1, "Mix", null],
    [1128, "OSC 3 Source", 0, 13, 0, "", "sel", ["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080", "Granular", "Additive", "Modal Drum", "Spectral", "SoundFont", "Bagpipe"], 1, "Source", null],
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
    [1141, "OSC 3 Unison Voices", 1, 16, 1, "", "stp", null, 1, "Voices", null],
    [1142, "OSC 3 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1143, "OSC 3 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1144, "OSC 3 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1145, "OSC 3 Unison Style", 0, 5, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"], 1, "Detune Curve", null],
    [1156, "OSC 3 Unison Drift", 0, 1, 0, "", "sld", null, 1, "Drift", null],
    [1157, "OSC 3 Unison Phase", 0, 1, 0, "", "sld", null, 1, "Phase Spread", null],
    [1146, "OSC 3 Warp 1 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1147, "OSC 3 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1148, "OSC 3 Warp 2 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1149, "OSC 3 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1150, "OSC 3 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1151, "OSC 3 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1152, "OSC 3 Terrain A", 0, 11, 0, "", "sel", TERRAINS, 1, "Terrain", null],
    [1153, "OSC 3 Terrain Scale", 0, 1, 0.5, "", "sld", null, 1, "Scale", null],
    [1154, "OSC 3 Terrain Warp", 0, 1, 0, "", "sld", null, 1, "Warp", null],
    [1155, "OSC 3 Terrain Fold", 0, 1, 0, "", "sld", null, 1, "Fold", null],
    [1158, "OSC 3 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1159, "OSC 3 Filter Type", 0, 30, 0, "", "sel", OSC_FILTER_TYPES, 1, "Type", OSC_FILTER_GROUPS],
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
    [1170, "OSC 3 Distortion Type", 0, 7, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Wavedistortion"], 1, "Type", null],
    [1171, "OSC 3 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1172, "OSC 3 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1176, "OSC 3 Frequency", 0, 1, 0, "", "sld", null, 1, "Frequency", null],
    [1174, "OSC 3 Wavefilter Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1175, "OSC 3 Wavedistortion Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1177, "OSC 3 Wavefilter Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1178, "OSC 3 Wavefilter Range", 2, 14, 8, "oct", "sld", null, 1, "Range", null],
    [1179, "OSC 3 Wavefilter Warp", -1, 1, 0, "", "sld", null, 1, "Warp", null],
    [1180, "OSC 3 Wavefilter Contrast", -1, 1, 0, "", "sld", null, 1, "Contrast", null],
    [1181, "OSC 3 Wavefilter Tilt", -1, 1, 0, "", "sld", null, 1, "Tilt", null],
    [1182, "OSC 3 Wavefilter Spread", 0, 1, 0, "", "sld", null, 1, "Spread", null],
    [1183, "OSC 3 Wavefilter Gain Law", 0, 2, 0, "", "sel", ["Linear", "Bipolar", "dB"], 1, "Gain Law", null],
    [1173, "OSC 3 Pre-Matrix Order", 0, 5, 0, "", "sel", ["Filter > Dist > Reso", "Dist > Filter > Reso", "Filter > Reso > Dist", "Reso > Filter > Dist", "Dist > Reso > Filter", "Reso > Dist > Filter"], 1, "Order", null],
    [1184, "OSC 3 Resonator On", 0, 1, 0, "", "btn", ["Off", "On"], 1, "On", null],
    [1185, "OSC 3 Resonator Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1186, "OSC 3 Resonator Decay", 0.02, 20, 1.0, "s", "sld", null, 1, "Decay", null],
    [1187, "OSC 3 Resonator Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1188, "OSC 3 Resonator Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [1189, "OSC 3 Resonator Inharmonicity", 0, 1, 0, "", "sld", null, 1, "Inharm", null],
    [1190, "OSC 3 Resonator Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1191, "OSC 3 Resonator Mix", 0, 1, 0.5, "", "sld", null, 1, "Mix", null],
    [1192, "OSC 4 Source", 0, 13, 0, "", "sel", ["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080", "Granular", "Additive", "Modal Drum", "Spectral", "SoundFont", "Bagpipe"], 1, "Source", null],
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
    [1205, "OSC 4 Unison Voices", 1, 16, 1, "", "stp", null, 1, "Voices", null],
    [1206, "OSC 4 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1207, "OSC 4 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1208, "OSC 4 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1209, "OSC 4 Unison Style", 0, 5, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"], 1, "Detune Curve", null],
    [1220, "OSC 4 Unison Drift", 0, 1, 0, "", "sld", null, 1, "Drift", null],
    [1221, "OSC 4 Unison Phase", 0, 1, 0, "", "sld", null, 1, "Phase Spread", null],
    [1210, "OSC 4 Warp 1 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1211, "OSC 4 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1212, "OSC 4 Warp 2 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1213, "OSC 4 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1214, "OSC 4 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1215, "OSC 4 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1216, "OSC 4 Terrain A", 0, 11, 0, "", "sel", TERRAINS, 1, "Terrain", null],
    [1217, "OSC 4 Terrain Scale", 0, 1, 0.5, "", "sld", null, 1, "Scale", null],
    [1218, "OSC 4 Terrain Warp", 0, 1, 0, "", "sld", null, 1, "Warp", null],
    [1219, "OSC 4 Terrain Fold", 0, 1, 0, "", "sld", null, 1, "Fold", null],
    [1222, "OSC 4 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1223, "OSC 4 Filter Type", 0, 30, 0, "", "sel", OSC_FILTER_TYPES, 1, "Type", OSC_FILTER_GROUPS],
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
    [1234, "OSC 4 Distortion Type", 0, 7, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Wavedistortion"], 1, "Type", null],
    [1235, "OSC 4 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1236, "OSC 4 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1240, "OSC 4 Frequency", 0, 1, 0, "", "sld", null, 1, "Frequency", null],
    [1238, "OSC 4 Wavefilter Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1239, "OSC 4 Wavedistortion Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1241, "OSC 4 Wavefilter Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1242, "OSC 4 Wavefilter Range", 2, 14, 8, "oct", "sld", null, 1, "Range", null],
    [1243, "OSC 4 Wavefilter Warp", -1, 1, 0, "", "sld", null, 1, "Warp", null],
    [1244, "OSC 4 Wavefilter Contrast", -1, 1, 0, "", "sld", null, 1, "Contrast", null],
    [1245, "OSC 4 Wavefilter Tilt", -1, 1, 0, "", "sld", null, 1, "Tilt", null],
    [1246, "OSC 4 Wavefilter Spread", 0, 1, 0, "", "sld", null, 1, "Spread", null],
    [1247, "OSC 4 Wavefilter Gain Law", 0, 2, 0, "", "sel", ["Linear", "Bipolar", "dB"], 1, "Gain Law", null],
    [1237, "OSC 4 Pre-Matrix Order", 0, 5, 0, "", "sel", ["Filter > Dist > Reso", "Dist > Filter > Reso", "Filter > Reso > Dist", "Reso > Filter > Dist", "Dist > Reso > Filter", "Reso > Dist > Filter"], 1, "Order", null],
    [1248, "OSC 4 Resonator On", 0, 1, 0, "", "btn", ["Off", "On"], 1, "On", null],
    [1249, "OSC 4 Resonator Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1250, "OSC 4 Resonator Decay", 0.02, 20, 1.0, "s", "sld", null, 1, "Decay", null],
    [1251, "OSC 4 Resonator Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1252, "OSC 4 Resonator Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [1253, "OSC 4 Resonator Inharmonicity", 0, 1, 0, "", "sld", null, 1, "Inharm", null],
    [1254, "OSC 4 Resonator Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1255, "OSC 4 Resonator Mix", 0, 1, 0.5, "", "sld", null, 1, "Mix", null],
    [1256, "OSC 5 Source", 0, 13, 0, "", "sel", ["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080", "Granular", "Additive", "Modal Drum", "Spectral", "SoundFont", "Bagpipe"], 1, "Source", null],
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
    [1269, "OSC 5 Unison Voices", 1, 16, 1, "", "stp", null, 1, "Voices", null],
    [1270, "OSC 5 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1271, "OSC 5 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1272, "OSC 5 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1273, "OSC 5 Unison Style", 0, 5, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"], 1, "Detune Curve", null],
    [1284, "OSC 5 Unison Drift", 0, 1, 0, "", "sld", null, 1, "Drift", null],
    [1285, "OSC 5 Unison Phase", 0, 1, 0, "", "sld", null, 1, "Phase Spread", null],
    [1274, "OSC 5 Warp 1 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1275, "OSC 5 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1276, "OSC 5 Warp 2 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1277, "OSC 5 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1278, "OSC 5 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1279, "OSC 5 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1280, "OSC 5 Terrain A", 0, 11, 0, "", "sel", TERRAINS, 1, "Terrain", null],
    [1281, "OSC 5 Terrain Scale", 0, 1, 0.5, "", "sld", null, 1, "Scale", null],
    [1282, "OSC 5 Terrain Warp", 0, 1, 0, "", "sld", null, 1, "Warp", null],
    [1283, "OSC 5 Terrain Fold", 0, 1, 0, "", "sld", null, 1, "Fold", null],
    [1286, "OSC 5 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1287, "OSC 5 Filter Type", 0, 30, 0, "", "sel", OSC_FILTER_TYPES, 1, "Type", OSC_FILTER_GROUPS],
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
    [1298, "OSC 5 Distortion Type", 0, 7, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Wavedistortion"], 1, "Type", null],
    [1299, "OSC 5 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1300, "OSC 5 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1304, "OSC 5 Frequency", 0, 1, 0, "", "sld", null, 1, "Frequency", null],
    [1302, "OSC 5 Wavefilter Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1303, "OSC 5 Wavedistortion Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1305, "OSC 5 Wavefilter Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1306, "OSC 5 Wavefilter Range", 2, 14, 8, "oct", "sld", null, 1, "Range", null],
    [1307, "OSC 5 Wavefilter Warp", -1, 1, 0, "", "sld", null, 1, "Warp", null],
    [1308, "OSC 5 Wavefilter Contrast", -1, 1, 0, "", "sld", null, 1, "Contrast", null],
    [1309, "OSC 5 Wavefilter Tilt", -1, 1, 0, "", "sld", null, 1, "Tilt", null],
    [1310, "OSC 5 Wavefilter Spread", 0, 1, 0, "", "sld", null, 1, "Spread", null],
    [1311, "OSC 5 Wavefilter Gain Law", 0, 2, 0, "", "sel", ["Linear", "Bipolar", "dB"], 1, "Gain Law", null],
    [1301, "OSC 5 Pre-Matrix Order", 0, 5, 0, "", "sel", ["Filter > Dist > Reso", "Dist > Filter > Reso", "Filter > Reso > Dist", "Reso > Filter > Dist", "Dist > Reso > Filter", "Reso > Dist > Filter"], 1, "Order", null],
    [1312, "OSC 5 Resonator On", 0, 1, 0, "", "btn", ["Off", "On"], 1, "On", null],
    [1313, "OSC 5 Resonator Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1314, "OSC 5 Resonator Decay", 0.02, 20, 1.0, "s", "sld", null, 1, "Decay", null],
    [1315, "OSC 5 Resonator Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1316, "OSC 5 Resonator Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [1317, "OSC 5 Resonator Inharmonicity", 0, 1, 0, "", "sld", null, 1, "Inharm", null],
    [1318, "OSC 5 Resonator Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1319, "OSC 5 Resonator Mix", 0, 1, 0.5, "", "sld", null, 1, "Mix", null],
    [1320, "OSC 6 Source", 0, 13, 0, "", "sel", ["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080", "Granular", "Additive", "Modal Drum", "Spectral", "SoundFont", "Bagpipe"], 1, "Source", null],
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
    [1333, "OSC 6 Unison Voices", 1, 16, 1, "", "stp", null, 1, "Voices", null],
    [1334, "OSC 6 Unison Detune", 0, 1, 0.25, "", "sld", null, 1, "Detune", null],
    [1335, "OSC 6 Unison Blend", 0, 1, 1, "", "sld", null, 1, "Blend", null],
    [1336, "OSC 6 Unison Width", 0, 1, 0.75, "", "sld", null, 1, "Width", null],
    [1337, "OSC 6 Unison Style", 0, 5, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"], 1, "Detune Curve", null],
    [1348, "OSC 6 Unison Drift", 0, 1, 0, "", "sld", null, 1, "Drift", null],
    [1349, "OSC 6 Unison Phase", 0, 1, 0, "", "sld", null, 1, "Phase Spread", null],
    [1338, "OSC 6 Warp 1 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 1", null],
    [1339, "OSC 6 Warp 1 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 1 Amt", null],
    [1340, "OSC 6 Warp 2 Mode", 0, 26, 0, "", "sel", WARP_MODES, 1, "Warp 2", null],
    [1341, "OSC 6 Warp 2 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 2 Amt", null],
    [1342, "OSC 6 Sample Start", 0, 1, 0, "", "sld", null, 1, "Start", null],
    [1343, "OSC 6 Sample Loop", 0, 1, 0, "", "btn", ["Off", "On"], 1, "Loop", null],
    [1344, "OSC 6 Terrain A", 0, 11, 0, "", "sel", TERRAINS, 1, "Terrain", null],
    [1345, "OSC 6 Terrain Scale", 0, 1, 0.5, "", "sld", null, 1, "Scale", null],
    [1346, "OSC 6 Terrain Warp", 0, 1, 0, "", "sld", null, 1, "Warp", null],
    [1347, "OSC 6 Terrain Fold", 0, 1, 0, "", "sld", null, 1, "Fold", null],
    [1350, "OSC 6 Filter On", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Filter", null],
    [1351, "OSC 6 Filter Type", 0, 30, 0, "", "sel", OSC_FILTER_TYPES, 1, "Type", OSC_FILTER_GROUPS],
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
    [1362, "OSC 6 Distortion Type", 0, 7, 0, "", "sel", ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Wavedistortion"], 1, "Type", null],
    [1363, "OSC 6 Distortion Drive", 0, 1, 0.3, "", "sld", null, 1, "Drive", null],
    [1364, "OSC 6 Distortion Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1368, "OSC 6 Frequency", 0, 1, 0, "", "sld", null, 1, "Frequency", null],
    [1366, "OSC 6 Wavefilter Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1367, "OSC 6 Wavedistortion Position", 0, 1, 0, "", "sld", null, 1, "Table Pos", null],
    [1369, "OSC 6 Wavefilter Mix", 0, 1, 1, "", "sld", null, 1, "Mix", null],
    [1370, "OSC 6 Wavefilter Range", 2, 14, 8, "oct", "sld", null, 1, "Range", null],
    [1371, "OSC 6 Wavefilter Warp", -1, 1, 0, "", "sld", null, 1, "Warp", null],
    [1372, "OSC 6 Wavefilter Contrast", -1, 1, 0, "", "sld", null, 1, "Contrast", null],
    [1373, "OSC 6 Wavefilter Tilt", -1, 1, 0, "", "sld", null, 1, "Tilt", null],
    [1374, "OSC 6 Wavefilter Spread", 0, 1, 0, "", "sld", null, 1, "Spread", null],
    [1375, "OSC 6 Wavefilter Gain Law", 0, 2, 0, "", "sel", ["Linear", "Bipolar", "dB"], 1, "Gain Law", null],
    [1365, "OSC 6 Pre-Matrix Order", 0, 5, 0, "", "sel", ["Filter > Dist > Reso", "Dist > Filter > Reso", "Filter > Reso > Dist", "Reso > Filter > Dist", "Dist > Reso > Filter", "Reso > Dist > Filter"], 1, "Order", null],
    [1376, "OSC 6 Resonator On", 0, 1, 0, "", "btn", ["Off", "On"], 1, "On", null],
    [1377, "OSC 6 Resonator Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1378, "OSC 6 Resonator Decay", 0.02, 20, 1.0, "s", "sld", null, 1, "Decay", null],
    [1379, "OSC 6 Resonator Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1380, "OSC 6 Resonator Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [1381, "OSC 6 Resonator Inharmonicity", 0, 1, 0, "", "sld", null, 1, "Inharm", null],
    [1382, "OSC 6 Resonator Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1383, "OSC 6 Resonator Mix", 0, 1, 0.5, "", "sld", null, 1, "Mix", null],
    [1400, "FM 1 to 1", 0, 400, 0, "", "knb", null, 1, "1→1", null],
    [1440, "PM 1 to 1", 0, 400, 0, "", "knb", null, 1, "1→1", null],
    [1480, "PD 1 to 1", 0, 100, 0, "", "knb", null, 1, "1→1", null],
    [1520, "RM 1 to 1", 0, 100, 0, "", "knb", null, 1, "1→1", null],
    [1560, "AM 1 to 1", 0, 100, 0, "", "knb", null, 1, "1→1", null],
    [1401, "FM 1 to 2", 0, 400, 0, "", "knb", null, 1, "1→2", null],
    [1441, "PM 1 to 2", 0, 400, 0, "", "knb", null, 1, "1→2", null],
    [1481, "PD 1 to 2", 0, 100, 0, "", "knb", null, 1, "1→2", null],
    [1521, "RM 1 to 2", 0, 100, 0, "", "knb", null, 1, "1→2", null],
    [1561, "AM 1 to 2", 0, 100, 0, "", "knb", null, 1, "1→2", null],
    [1402, "FM 1 to 3", 0, 400, 0, "", "knb", null, 1, "1→3", null],
    [1442, "PM 1 to 3", 0, 400, 0, "", "knb", null, 1, "1→3", null],
    [1482, "PD 1 to 3", 0, 100, 0, "", "knb", null, 1, "1→3", null],
    [1522, "RM 1 to 3", 0, 100, 0, "", "knb", null, 1, "1→3", null],
    [1562, "AM 1 to 3", 0, 100, 0, "", "knb", null, 1, "1→3", null],
    [1403, "FM 1 to 4", 0, 400, 0, "", "knb", null, 1, "1→4", null],
    [1443, "PM 1 to 4", 0, 400, 0, "", "knb", null, 1, "1→4", null],
    [1483, "PD 1 to 4", 0, 100, 0, "", "knb", null, 1, "1→4", null],
    [1523, "RM 1 to 4", 0, 100, 0, "", "knb", null, 1, "1→4", null],
    [1563, "AM 1 to 4", 0, 100, 0, "", "knb", null, 1, "1→4", null],
    [1404, "FM 1 to 5", 0, 400, 0, "", "knb", null, 1, "1→5", null],
    [1444, "PM 1 to 5", 0, 400, 0, "", "knb", null, 1, "1→5", null],
    [1484, "PD 1 to 5", 0, 100, 0, "", "knb", null, 1, "1→5", null],
    [1524, "RM 1 to 5", 0, 100, 0, "", "knb", null, 1, "1→5", null],
    [1564, "AM 1 to 5", 0, 100, 0, "", "knb", null, 1, "1→5", null],
    [1405, "FM 1 to 6", 0, 400, 0, "", "knb", null, 1, "1→6", null],
    [1445, "PM 1 to 6", 0, 400, 0, "", "knb", null, 1, "1→6", null],
    [1485, "PD 1 to 6", 0, 100, 0, "", "knb", null, 1, "1→6", null],
    [1525, "RM 1 to 6", 0, 100, 0, "", "knb", null, 1, "1→6", null],
    [1565, "AM 1 to 6", 0, 100, 0, "", "knb", null, 1, "1→6", null],
    [1406, "FM 2 to 1", 0, 400, 0, "", "knb", null, 1, "2→1", null],
    [1446, "PM 2 to 1", 0, 400, 0, "", "knb", null, 1, "2→1", null],
    [1486, "PD 2 to 1", 0, 100, 0, "", "knb", null, 1, "2→1", null],
    [1526, "RM 2 to 1", 0, 100, 0, "", "knb", null, 1, "2→1", null],
    [1566, "AM 2 to 1", 0, 100, 0, "", "knb", null, 1, "2→1", null],
    [1407, "FM 2 to 2", 0, 400, 0, "", "knb", null, 1, "2→2", null],
    [1447, "PM 2 to 2", 0, 400, 0, "", "knb", null, 1, "2→2", null],
    [1487, "PD 2 to 2", 0, 100, 0, "", "knb", null, 1, "2→2", null],
    [1527, "RM 2 to 2", 0, 100, 0, "", "knb", null, 1, "2→2", null],
    [1567, "AM 2 to 2", 0, 100, 0, "", "knb", null, 1, "2→2", null],
    [1408, "FM 2 to 3", 0, 400, 0, "", "knb", null, 1, "2→3", null],
    [1448, "PM 2 to 3", 0, 400, 0, "", "knb", null, 1, "2→3", null],
    [1488, "PD 2 to 3", 0, 100, 0, "", "knb", null, 1, "2→3", null],
    [1528, "RM 2 to 3", 0, 100, 0, "", "knb", null, 1, "2→3", null],
    [1568, "AM 2 to 3", 0, 100, 0, "", "knb", null, 1, "2→3", null],
    [1409, "FM 2 to 4", 0, 400, 0, "", "knb", null, 1, "2→4", null],
    [1449, "PM 2 to 4", 0, 400, 0, "", "knb", null, 1, "2→4", null],
    [1489, "PD 2 to 4", 0, 100, 0, "", "knb", null, 1, "2→4", null],
    [1529, "RM 2 to 4", 0, 100, 0, "", "knb", null, 1, "2→4", null],
    [1569, "AM 2 to 4", 0, 100, 0, "", "knb", null, 1, "2→4", null],
    [1410, "FM 2 to 5", 0, 400, 0, "", "knb", null, 1, "2→5", null],
    [1450, "PM 2 to 5", 0, 400, 0, "", "knb", null, 1, "2→5", null],
    [1490, "PD 2 to 5", 0, 100, 0, "", "knb", null, 1, "2→5", null],
    [1530, "RM 2 to 5", 0, 100, 0, "", "knb", null, 1, "2→5", null],
    [1570, "AM 2 to 5", 0, 100, 0, "", "knb", null, 1, "2→5", null],
    [1411, "FM 2 to 6", 0, 400, 0, "", "knb", null, 1, "2→6", null],
    [1451, "PM 2 to 6", 0, 400, 0, "", "knb", null, 1, "2→6", null],
    [1491, "PD 2 to 6", 0, 100, 0, "", "knb", null, 1, "2→6", null],
    [1531, "RM 2 to 6", 0, 100, 0, "", "knb", null, 1, "2→6", null],
    [1571, "AM 2 to 6", 0, 100, 0, "", "knb", null, 1, "2→6", null],
    [1412, "FM 3 to 1", 0, 400, 0, "", "knb", null, 1, "3→1", null],
    [1452, "PM 3 to 1", 0, 400, 0, "", "knb", null, 1, "3→1", null],
    [1492, "PD 3 to 1", 0, 100, 0, "", "knb", null, 1, "3→1", null],
    [1532, "RM 3 to 1", 0, 100, 0, "", "knb", null, 1, "3→1", null],
    [1572, "AM 3 to 1", 0, 100, 0, "", "knb", null, 1, "3→1", null],
    [1413, "FM 3 to 2", 0, 400, 0, "", "knb", null, 1, "3→2", null],
    [1453, "PM 3 to 2", 0, 400, 0, "", "knb", null, 1, "3→2", null],
    [1493, "PD 3 to 2", 0, 100, 0, "", "knb", null, 1, "3→2", null],
    [1533, "RM 3 to 2", 0, 100, 0, "", "knb", null, 1, "3→2", null],
    [1573, "AM 3 to 2", 0, 100, 0, "", "knb", null, 1, "3→2", null],
    [1414, "FM 3 to 3", 0, 400, 0, "", "knb", null, 1, "3→3", null],
    [1454, "PM 3 to 3", 0, 400, 0, "", "knb", null, 1, "3→3", null],
    [1494, "PD 3 to 3", 0, 100, 0, "", "knb", null, 1, "3→3", null],
    [1534, "RM 3 to 3", 0, 100, 0, "", "knb", null, 1, "3→3", null],
    [1574, "AM 3 to 3", 0, 100, 0, "", "knb", null, 1, "3→3", null],
    [1415, "FM 3 to 4", 0, 400, 0, "", "knb", null, 1, "3→4", null],
    [1455, "PM 3 to 4", 0, 400, 0, "", "knb", null, 1, "3→4", null],
    [1495, "PD 3 to 4", 0, 100, 0, "", "knb", null, 1, "3→4", null],
    [1535, "RM 3 to 4", 0, 100, 0, "", "knb", null, 1, "3→4", null],
    [1575, "AM 3 to 4", 0, 100, 0, "", "knb", null, 1, "3→4", null],
    [1416, "FM 3 to 5", 0, 400, 0, "", "knb", null, 1, "3→5", null],
    [1456, "PM 3 to 5", 0, 400, 0, "", "knb", null, 1, "3→5", null],
    [1496, "PD 3 to 5", 0, 100, 0, "", "knb", null, 1, "3→5", null],
    [1536, "RM 3 to 5", 0, 100, 0, "", "knb", null, 1, "3→5", null],
    [1576, "AM 3 to 5", 0, 100, 0, "", "knb", null, 1, "3→5", null],
    [1417, "FM 3 to 6", 0, 400, 0, "", "knb", null, 1, "3→6", null],
    [1457, "PM 3 to 6", 0, 400, 0, "", "knb", null, 1, "3→6", null],
    [1497, "PD 3 to 6", 0, 100, 0, "", "knb", null, 1, "3→6", null],
    [1537, "RM 3 to 6", 0, 100, 0, "", "knb", null, 1, "3→6", null],
    [1577, "AM 3 to 6", 0, 100, 0, "", "knb", null, 1, "3→6", null],
    [1418, "FM 4 to 1", 0, 400, 0, "", "knb", null, 1, "4→1", null],
    [1458, "PM 4 to 1", 0, 400, 0, "", "knb", null, 1, "4→1", null],
    [1498, "PD 4 to 1", 0, 100, 0, "", "knb", null, 1, "4→1", null],
    [1538, "RM 4 to 1", 0, 100, 0, "", "knb", null, 1, "4→1", null],
    [1578, "AM 4 to 1", 0, 100, 0, "", "knb", null, 1, "4→1", null],
    [1419, "FM 4 to 2", 0, 400, 0, "", "knb", null, 1, "4→2", null],
    [1459, "PM 4 to 2", 0, 400, 0, "", "knb", null, 1, "4→2", null],
    [1499, "PD 4 to 2", 0, 100, 0, "", "knb", null, 1, "4→2", null],
    [1539, "RM 4 to 2", 0, 100, 0, "", "knb", null, 1, "4→2", null],
    [1579, "AM 4 to 2", 0, 100, 0, "", "knb", null, 1, "4→2", null],
    [1420, "FM 4 to 3", 0, 400, 0, "", "knb", null, 1, "4→3", null],
    [1460, "PM 4 to 3", 0, 400, 0, "", "knb", null, 1, "4→3", null],
    [1500, "PD 4 to 3", 0, 100, 0, "", "knb", null, 1, "4→3", null],
    [1540, "RM 4 to 3", 0, 100, 0, "", "knb", null, 1, "4→3", null],
    [1580, "AM 4 to 3", 0, 100, 0, "", "knb", null, 1, "4→3", null],
    [1421, "FM 4 to 4", 0, 400, 0, "", "knb", null, 1, "4→4", null],
    [1461, "PM 4 to 4", 0, 400, 0, "", "knb", null, 1, "4→4", null],
    [1501, "PD 4 to 4", 0, 100, 0, "", "knb", null, 1, "4→4", null],
    [1541, "RM 4 to 4", 0, 100, 0, "", "knb", null, 1, "4→4", null],
    [1581, "AM 4 to 4", 0, 100, 0, "", "knb", null, 1, "4→4", null],
    [1422, "FM 4 to 5", 0, 400, 0, "", "knb", null, 1, "4→5", null],
    [1462, "PM 4 to 5", 0, 400, 0, "", "knb", null, 1, "4→5", null],
    [1502, "PD 4 to 5", 0, 100, 0, "", "knb", null, 1, "4→5", null],
    [1542, "RM 4 to 5", 0, 100, 0, "", "knb", null, 1, "4→5", null],
    [1582, "AM 4 to 5", 0, 100, 0, "", "knb", null, 1, "4→5", null],
    [1423, "FM 4 to 6", 0, 400, 0, "", "knb", null, 1, "4→6", null],
    [1463, "PM 4 to 6", 0, 400, 0, "", "knb", null, 1, "4→6", null],
    [1503, "PD 4 to 6", 0, 100, 0, "", "knb", null, 1, "4→6", null],
    [1543, "RM 4 to 6", 0, 100, 0, "", "knb", null, 1, "4→6", null],
    [1583, "AM 4 to 6", 0, 100, 0, "", "knb", null, 1, "4→6", null],
    [1424, "FM 5 to 1", 0, 400, 0, "", "knb", null, 1, "5→1", null],
    [1464, "PM 5 to 1", 0, 400, 0, "", "knb", null, 1, "5→1", null],
    [1504, "PD 5 to 1", 0, 100, 0, "", "knb", null, 1, "5→1", null],
    [1544, "RM 5 to 1", 0, 100, 0, "", "knb", null, 1, "5→1", null],
    [1584, "AM 5 to 1", 0, 100, 0, "", "knb", null, 1, "5→1", null],
    [1425, "FM 5 to 2", 0, 400, 0, "", "knb", null, 1, "5→2", null],
    [1465, "PM 5 to 2", 0, 400, 0, "", "knb", null, 1, "5→2", null],
    [1505, "PD 5 to 2", 0, 100, 0, "", "knb", null, 1, "5→2", null],
    [1545, "RM 5 to 2", 0, 100, 0, "", "knb", null, 1, "5→2", null],
    [1585, "AM 5 to 2", 0, 100, 0, "", "knb", null, 1, "5→2", null],
    [1426, "FM 5 to 3", 0, 400, 0, "", "knb", null, 1, "5→3", null],
    [1466, "PM 5 to 3", 0, 400, 0, "", "knb", null, 1, "5→3", null],
    [1506, "PD 5 to 3", 0, 100, 0, "", "knb", null, 1, "5→3", null],
    [1546, "RM 5 to 3", 0, 100, 0, "", "knb", null, 1, "5→3", null],
    [1586, "AM 5 to 3", 0, 100, 0, "", "knb", null, 1, "5→3", null],
    [1427, "FM 5 to 4", 0, 400, 0, "", "knb", null, 1, "5→4", null],
    [1467, "PM 5 to 4", 0, 400, 0, "", "knb", null, 1, "5→4", null],
    [1507, "PD 5 to 4", 0, 100, 0, "", "knb", null, 1, "5→4", null],
    [1547, "RM 5 to 4", 0, 100, 0, "", "knb", null, 1, "5→4", null],
    [1587, "AM 5 to 4", 0, 100, 0, "", "knb", null, 1, "5→4", null],
    [1428, "FM 5 to 5", 0, 400, 0, "", "knb", null, 1, "5→5", null],
    [1468, "PM 5 to 5", 0, 400, 0, "", "knb", null, 1, "5→5", null],
    [1508, "PD 5 to 5", 0, 100, 0, "", "knb", null, 1, "5→5", null],
    [1548, "RM 5 to 5", 0, 100, 0, "", "knb", null, 1, "5→5", null],
    [1588, "AM 5 to 5", 0, 100, 0, "", "knb", null, 1, "5→5", null],
    [1429, "FM 5 to 6", 0, 400, 0, "", "knb", null, 1, "5→6", null],
    [1469, "PM 5 to 6", 0, 400, 0, "", "knb", null, 1, "5→6", null],
    [1509, "PD 5 to 6", 0, 100, 0, "", "knb", null, 1, "5→6", null],
    [1549, "RM 5 to 6", 0, 100, 0, "", "knb", null, 1, "5→6", null],
    [1589, "AM 5 to 6", 0, 100, 0, "", "knb", null, 1, "5→6", null],
    [1430, "FM 6 to 1", 0, 400, 0, "", "knb", null, 1, "6→1", null],
    [1470, "PM 6 to 1", 0, 400, 0, "", "knb", null, 1, "6→1", null],
    [1510, "PD 6 to 1", 0, 100, 0, "", "knb", null, 1, "6→1", null],
    [1550, "RM 6 to 1", 0, 100, 0, "", "knb", null, 1, "6→1", null],
    [1590, "AM 6 to 1", 0, 100, 0, "", "knb", null, 1, "6→1", null],
    [1431, "FM 6 to 2", 0, 400, 0, "", "knb", null, 1, "6→2", null],
    [1471, "PM 6 to 2", 0, 400, 0, "", "knb", null, 1, "6→2", null],
    [1511, "PD 6 to 2", 0, 100, 0, "", "knb", null, 1, "6→2", null],
    [1551, "RM 6 to 2", 0, 100, 0, "", "knb", null, 1, "6→2", null],
    [1591, "AM 6 to 2", 0, 100, 0, "", "knb", null, 1, "6→2", null],
    [1432, "FM 6 to 3", 0, 400, 0, "", "knb", null, 1, "6→3", null],
    [1472, "PM 6 to 3", 0, 400, 0, "", "knb", null, 1, "6→3", null],
    [1512, "PD 6 to 3", 0, 100, 0, "", "knb", null, 1, "6→3", null],
    [1552, "RM 6 to 3", 0, 100, 0, "", "knb", null, 1, "6→3", null],
    [1592, "AM 6 to 3", 0, 100, 0, "", "knb", null, 1, "6→3", null],
    [1433, "FM 6 to 4", 0, 400, 0, "", "knb", null, 1, "6→4", null],
    [1473, "PM 6 to 4", 0, 400, 0, "", "knb", null, 1, "6→4", null],
    [1513, "PD 6 to 4", 0, 100, 0, "", "knb", null, 1, "6→4", null],
    [1553, "RM 6 to 4", 0, 100, 0, "", "knb", null, 1, "6→4", null],
    [1593, "AM 6 to 4", 0, 100, 0, "", "knb", null, 1, "6→4", null],
    [1434, "FM 6 to 5", 0, 400, 0, "", "knb", null, 1, "6→5", null],
    [1474, "PM 6 to 5", 0, 400, 0, "", "knb", null, 1, "6→5", null],
    [1514, "PD 6 to 5", 0, 100, 0, "", "knb", null, 1, "6→5", null],
    [1554, "RM 6 to 5", 0, 100, 0, "", "knb", null, 1, "6→5", null],
    [1594, "AM 6 to 5", 0, 100, 0, "", "knb", null, 1, "6→5", null],
    [1435, "FM 6 to 6", 0, 400, 0, "", "knb", null, 1, "6→6", null],
    [1475, "PM 6 to 6", 0, 400, 0, "", "knb", null, 1, "6→6", null],
    [1515, "PD 6 to 6", 0, 100, 0, "", "knb", null, 1, "6→6", null],
    [1555, "RM 6 to 6", 0, 100, 0, "", "knb", null, 1, "6→6", null],
    [1595, "AM 6 to 6", 0, 100, 0, "", "knb", null, 1, "6→6", null],
    [2900, "TZFM 1 to 1", 0, 400, 0, "", "knb", null, 1, "1→1", null],
    [2901, "TZFM 1 to 2", 0, 400, 0, "", "knb", null, 1, "1→2", null],
    [2902, "TZFM 1 to 3", 0, 400, 0, "", "knb", null, 1, "1→3", null],
    [2903, "TZFM 1 to 4", 0, 400, 0, "", "knb", null, 1, "1→4", null],
    [2904, "TZFM 1 to 5", 0, 400, 0, "", "knb", null, 1, "1→5", null],
    [2905, "TZFM 1 to 6", 0, 400, 0, "", "knb", null, 1, "1→6", null],
    [2906, "TZFM 2 to 1", 0, 400, 0, "", "knb", null, 1, "2→1", null],
    [2907, "TZFM 2 to 2", 0, 400, 0, "", "knb", null, 1, "2→2", null],
    [2908, "TZFM 2 to 3", 0, 400, 0, "", "knb", null, 1, "2→3", null],
    [2909, "TZFM 2 to 4", 0, 400, 0, "", "knb", null, 1, "2→4", null],
    [2910, "TZFM 2 to 5", 0, 400, 0, "", "knb", null, 1, "2→5", null],
    [2911, "TZFM 2 to 6", 0, 400, 0, "", "knb", null, 1, "2→6", null],
    [2912, "TZFM 3 to 1", 0, 400, 0, "", "knb", null, 1, "3→1", null],
    [2913, "TZFM 3 to 2", 0, 400, 0, "", "knb", null, 1, "3→2", null],
    [2914, "TZFM 3 to 3", 0, 400, 0, "", "knb", null, 1, "3→3", null],
    [2915, "TZFM 3 to 4", 0, 400, 0, "", "knb", null, 1, "3→4", null],
    [2916, "TZFM 3 to 5", 0, 400, 0, "", "knb", null, 1, "3→5", null],
    [2917, "TZFM 3 to 6", 0, 400, 0, "", "knb", null, 1, "3→6", null],
    [2918, "TZFM 4 to 1", 0, 400, 0, "", "knb", null, 1, "4→1", null],
    [2919, "TZFM 4 to 2", 0, 400, 0, "", "knb", null, 1, "4→2", null],
    [2920, "TZFM 4 to 3", 0, 400, 0, "", "knb", null, 1, "4→3", null],
    [2921, "TZFM 4 to 4", 0, 400, 0, "", "knb", null, 1, "4→4", null],
    [2922, "TZFM 4 to 5", 0, 400, 0, "", "knb", null, 1, "4→5", null],
    [2923, "TZFM 4 to 6", 0, 400, 0, "", "knb", null, 1, "4→6", null],
    [2924, "TZFM 5 to 1", 0, 400, 0, "", "knb", null, 1, "5→1", null],
    [2925, "TZFM 5 to 2", 0, 400, 0, "", "knb", null, 1, "5→2", null],
    [2926, "TZFM 5 to 3", 0, 400, 0, "", "knb", null, 1, "5→3", null],
    [2927, "TZFM 5 to 4", 0, 400, 0, "", "knb", null, 1, "5→4", null],
    [2928, "TZFM 5 to 5", 0, 400, 0, "", "knb", null, 1, "5→5", null],
    [2929, "TZFM 5 to 6", 0, 400, 0, "", "knb", null, 1, "5→6", null],
    [2930, "TZFM 6 to 1", 0, 400, 0, "", "knb", null, 1, "6→1", null],
    [2931, "TZFM 6 to 2", 0, 400, 0, "", "knb", null, 1, "6→2", null],
    [2932, "TZFM 6 to 3", 0, 400, 0, "", "knb", null, 1, "6→3", null],
    [2933, "TZFM 6 to 4", 0, 400, 0, "", "knb", null, 1, "6→4", null],
    [2934, "TZFM 6 to 5", 0, 400, 0, "", "knb", null, 1, "6→5", null],
    [2935, "TZFM 6 to 6", 0, 400, 0, "", "knb", null, 1, "6→6", null],
    [5300, "XF 1 to 1", 0, 100, 0, "", "knb", null, 1, "1→1", null],
    [5301, "XF 1 to 2", 0, 100, 0, "", "knb", null, 1, "1→2", null],
    [5302, "XF 1 to 3", 0, 100, 0, "", "knb", null, 1, "1→3", null],
    [5303, "XF 1 to 4", 0, 100, 0, "", "knb", null, 1, "1→4", null],
    [5304, "XF 1 to 5", 0, 100, 0, "", "knb", null, 1, "1→5", null],
    [5305, "XF 1 to 6", 0, 100, 0, "", "knb", null, 1, "1→6", null],
    [5306, "XF 2 to 1", 0, 100, 0, "", "knb", null, 1, "2→1", null],
    [5307, "XF 2 to 2", 0, 100, 0, "", "knb", null, 1, "2→2", null],
    [5308, "XF 2 to 3", 0, 100, 0, "", "knb", null, 1, "2→3", null],
    [5309, "XF 2 to 4", 0, 100, 0, "", "knb", null, 1, "2→4", null],
    [5310, "XF 2 to 5", 0, 100, 0, "", "knb", null, 1, "2→5", null],
    [5311, "XF 2 to 6", 0, 100, 0, "", "knb", null, 1, "2→6", null],
    [5312, "XF 3 to 1", 0, 100, 0, "", "knb", null, 1, "3→1", null],
    [5313, "XF 3 to 2", 0, 100, 0, "", "knb", null, 1, "3→2", null],
    [5314, "XF 3 to 3", 0, 100, 0, "", "knb", null, 1, "3→3", null],
    [5315, "XF 3 to 4", 0, 100, 0, "", "knb", null, 1, "3→4", null],
    [5316, "XF 3 to 5", 0, 100, 0, "", "knb", null, 1, "3→5", null],
    [5317, "XF 3 to 6", 0, 100, 0, "", "knb", null, 1, "3→6", null],
    [5318, "XF 4 to 1", 0, 100, 0, "", "knb", null, 1, "4→1", null],
    [5319, "XF 4 to 2", 0, 100, 0, "", "knb", null, 1, "4→2", null],
    [5320, "XF 4 to 3", 0, 100, 0, "", "knb", null, 1, "4→3", null],
    [5321, "XF 4 to 4", 0, 100, 0, "", "knb", null, 1, "4→4", null],
    [5322, "XF 4 to 5", 0, 100, 0, "", "knb", null, 1, "4→5", null],
    [5323, "XF 4 to 6", 0, 100, 0, "", "knb", null, 1, "4→6", null],
    [5324, "XF 5 to 1", 0, 100, 0, "", "knb", null, 1, "5→1", null],
    [5325, "XF 5 to 2", 0, 100, 0, "", "knb", null, 1, "5→2", null],
    [5326, "XF 5 to 3", 0, 100, 0, "", "knb", null, 1, "5→3", null],
    [5327, "XF 5 to 4", 0, 100, 0, "", "knb", null, 1, "5→4", null],
    [5328, "XF 5 to 5", 0, 100, 0, "", "knb", null, 1, "5→5", null],
    [5329, "XF 5 to 6", 0, 100, 0, "", "knb", null, 1, "5→6", null],
    [5330, "XF 6 to 1", 0, 100, 0, "", "knb", null, 1, "6→1", null],
    [5331, "XF 6 to 2", 0, 100, 0, "", "knb", null, 1, "6→2", null],
    [5332, "XF 6 to 3", 0, 100, 0, "", "knb", null, 1, "6→3", null],
    [5333, "XF 6 to 4", 0, 100, 0, "", "knb", null, 1, "6→4", null],
    [5334, "XF 6 to 5", 0, 100, 0, "", "knb", null, 1, "6→5", null],
    [5335, "XF 6 to 6", 0, 100, 0, "", "knb", null, 1, "6→6", null],
    [5336, "FD 1 to 1", 0, 100, 0, "", "knb", null, 1, "1→1", null],
    [5337, "FD 1 to 2", 0, 100, 0, "", "knb", null, 1, "1→2", null],
    [5338, "FD 1 to 3", 0, 100, 0, "", "knb", null, 1, "1→3", null],
    [5339, "FD 1 to 4", 0, 100, 0, "", "knb", null, 1, "1→4", null],
    [5340, "FD 1 to 5", 0, 100, 0, "", "knb", null, 1, "1→5", null],
    [5341, "FD 1 to 6", 0, 100, 0, "", "knb", null, 1, "1→6", null],
    [5342, "FD 2 to 1", 0, 100, 0, "", "knb", null, 1, "2→1", null],
    [5343, "FD 2 to 2", 0, 100, 0, "", "knb", null, 1, "2→2", null],
    [5344, "FD 2 to 3", 0, 100, 0, "", "knb", null, 1, "2→3", null],
    [5345, "FD 2 to 4", 0, 100, 0, "", "knb", null, 1, "2→4", null],
    [5346, "FD 2 to 5", 0, 100, 0, "", "knb", null, 1, "2→5", null],
    [5347, "FD 2 to 6", 0, 100, 0, "", "knb", null, 1, "2→6", null],
    [5348, "FD 3 to 1", 0, 100, 0, "", "knb", null, 1, "3→1", null],
    [5349, "FD 3 to 2", 0, 100, 0, "", "knb", null, 1, "3→2", null],
    [5350, "FD 3 to 3", 0, 100, 0, "", "knb", null, 1, "3→3", null],
    [5351, "FD 3 to 4", 0, 100, 0, "", "knb", null, 1, "3→4", null],
    [5352, "FD 3 to 5", 0, 100, 0, "", "knb", null, 1, "3→5", null],
    [5353, "FD 3 to 6", 0, 100, 0, "", "knb", null, 1, "3→6", null],
    [5354, "FD 4 to 1", 0, 100, 0, "", "knb", null, 1, "4→1", null],
    [5355, "FD 4 to 2", 0, 100, 0, "", "knb", null, 1, "4→2", null],
    [5356, "FD 4 to 3", 0, 100, 0, "", "knb", null, 1, "4→3", null],
    [5357, "FD 4 to 4", 0, 100, 0, "", "knb", null, 1, "4→4", null],
    [5358, "FD 4 to 5", 0, 100, 0, "", "knb", null, 1, "4→5", null],
    [5359, "FD 4 to 6", 0, 100, 0, "", "knb", null, 1, "4→6", null],
    [5360, "FD 5 to 1", 0, 100, 0, "", "knb", null, 1, "5→1", null],
    [5361, "FD 5 to 2", 0, 100, 0, "", "knb", null, 1, "5→2", null],
    [5362, "FD 5 to 3", 0, 100, 0, "", "knb", null, 1, "5→3", null],
    [5363, "FD 5 to 4", 0, 100, 0, "", "knb", null, 1, "5→4", null],
    [5364, "FD 5 to 5", 0, 100, 0, "", "knb", null, 1, "5→5", null],
    [5365, "FD 5 to 6", 0, 100, 0, "", "knb", null, 1, "5→6", null],
    [5366, "FD 6 to 1", 0, 100, 0, "", "knb", null, 1, "6→1", null],
    [5367, "FD 6 to 2", 0, 100, 0, "", "knb", null, 1, "6→2", null],
    [5368, "FD 6 to 3", 0, 100, 0, "", "knb", null, 1, "6→3", null],
    [5369, "FD 6 to 4", 0, 100, 0, "", "knb", null, 1, "6→4", null],
    [5370, "FD 6 to 5", 0, 100, 0, "", "knb", null, 1, "6→5", null],
    [5371, "FD 6 to 6", 0, 100, 0, "", "knb", null, 1, "6→6", null],
    [5372, "XR 1 to 1", 0, 100, 0, "", "knb", null, 1, "1→1", null],
    [5373, "XR 1 to 2", 0, 100, 0, "", "knb", null, 1, "1→2", null],
    [5374, "XR 1 to 3", 0, 100, 0, "", "knb", null, 1, "1→3", null],
    [5375, "XR 1 to 4", 0, 100, 0, "", "knb", null, 1, "1→4", null],
    [5376, "XR 1 to 5", 0, 100, 0, "", "knb", null, 1, "1→5", null],
    [5377, "XR 1 to 6", 0, 100, 0, "", "knb", null, 1, "1→6", null],
    [5378, "XR 2 to 1", 0, 100, 0, "", "knb", null, 1, "2→1", null],
    [5379, "XR 2 to 2", 0, 100, 0, "", "knb", null, 1, "2→2", null],
    [5380, "XR 2 to 3", 0, 100, 0, "", "knb", null, 1, "2→3", null],
    [5381, "XR 2 to 4", 0, 100, 0, "", "knb", null, 1, "2→4", null],
    [5382, "XR 2 to 5", 0, 100, 0, "", "knb", null, 1, "2→5", null],
    [5383, "XR 2 to 6", 0, 100, 0, "", "knb", null, 1, "2→6", null],
    [5384, "XR 3 to 1", 0, 100, 0, "", "knb", null, 1, "3→1", null],
    [5385, "XR 3 to 2", 0, 100, 0, "", "knb", null, 1, "3→2", null],
    [5386, "XR 3 to 3", 0, 100, 0, "", "knb", null, 1, "3→3", null],
    [5387, "XR 3 to 4", 0, 100, 0, "", "knb", null, 1, "3→4", null],
    [5388, "XR 3 to 5", 0, 100, 0, "", "knb", null, 1, "3→5", null],
    [5389, "XR 3 to 6", 0, 100, 0, "", "knb", null, 1, "3→6", null],
    [5390, "XR 4 to 1", 0, 100, 0, "", "knb", null, 1, "4→1", null],
    [5391, "XR 4 to 2", 0, 100, 0, "", "knb", null, 1, "4→2", null],
    [5392, "XR 4 to 3", 0, 100, 0, "", "knb", null, 1, "4→3", null],
    [5393, "XR 4 to 4", 0, 100, 0, "", "knb", null, 1, "4→4", null],
    [5394, "XR 4 to 5", 0, 100, 0, "", "knb", null, 1, "4→5", null],
    [5395, "XR 4 to 6", 0, 100, 0, "", "knb", null, 1, "4→6", null],
    [5396, "XR 5 to 1", 0, 100, 0, "", "knb", null, 1, "5→1", null],
    [5397, "XR 5 to 2", 0, 100, 0, "", "knb", null, 1, "5→2", null],
    [5398, "XR 5 to 3", 0, 100, 0, "", "knb", null, 1, "5→3", null],
    [5399, "XR 5 to 4", 0, 100, 0, "", "knb", null, 1, "5→4", null],
    [5400, "XR 5 to 5", 0, 100, 0, "", "knb", null, 1, "5→5", null],
    [5401, "XR 5 to 6", 0, 100, 0, "", "knb", null, 1, "5→6", null],
    [5402, "XR 6 to 1", 0, 100, 0, "", "knb", null, 1, "6→1", null],
    [5403, "XR 6 to 2", 0, 100, 0, "", "knb", null, 1, "6→2", null],
    [5404, "XR 6 to 3", 0, 100, 0, "", "knb", null, 1, "6→3", null],
    [5405, "XR 6 to 4", 0, 100, 0, "", "knb", null, 1, "6→4", null],
    [5406, "XR 6 to 5", 0, 100, 0, "", "knb", null, 1, "6→5", null],
    [5407, "XR 6 to 6", 0, 100, 0, "", "knb", null, 1, "6→6", null],
    [5408, "CP 1 to 1", 0, 100, 0, "", "knb", null, 1, "1→1", null],
    [5409, "CP 1 to 2", 0, 100, 0, "", "knb", null, 1, "1→2", null],
    [5410, "CP 1 to 3", 0, 100, 0, "", "knb", null, 1, "1→3", null],
    [5411, "CP 1 to 4", 0, 100, 0, "", "knb", null, 1, "1→4", null],
    [5412, "CP 1 to 5", 0, 100, 0, "", "knb", null, 1, "1→5", null],
    [5413, "CP 1 to 6", 0, 100, 0, "", "knb", null, 1, "1→6", null],
    [5414, "CP 2 to 1", 0, 100, 0, "", "knb", null, 1, "2→1", null],
    [5415, "CP 2 to 2", 0, 100, 0, "", "knb", null, 1, "2→2", null],
    [5416, "CP 2 to 3", 0, 100, 0, "", "knb", null, 1, "2→3", null],
    [5417, "CP 2 to 4", 0, 100, 0, "", "knb", null, 1, "2→4", null],
    [5418, "CP 2 to 5", 0, 100, 0, "", "knb", null, 1, "2→5", null],
    [5419, "CP 2 to 6", 0, 100, 0, "", "knb", null, 1, "2→6", null],
    [5420, "CP 3 to 1", 0, 100, 0, "", "knb", null, 1, "3→1", null],
    [5421, "CP 3 to 2", 0, 100, 0, "", "knb", null, 1, "3→2", null],
    [5422, "CP 3 to 3", 0, 100, 0, "", "knb", null, 1, "3→3", null],
    [5423, "CP 3 to 4", 0, 100, 0, "", "knb", null, 1, "3→4", null],
    [5424, "CP 3 to 5", 0, 100, 0, "", "knb", null, 1, "3→5", null],
    [5425, "CP 3 to 6", 0, 100, 0, "", "knb", null, 1, "3→6", null],
    [5426, "CP 4 to 1", 0, 100, 0, "", "knb", null, 1, "4→1", null],
    [5427, "CP 4 to 2", 0, 100, 0, "", "knb", null, 1, "4→2", null],
    [5428, "CP 4 to 3", 0, 100, 0, "", "knb", null, 1, "4→3", null],
    [5429, "CP 4 to 4", 0, 100, 0, "", "knb", null, 1, "4→4", null],
    [5430, "CP 4 to 5", 0, 100, 0, "", "knb", null, 1, "4→5", null],
    [5431, "CP 4 to 6", 0, 100, 0, "", "knb", null, 1, "4→6", null],
    [5432, "CP 5 to 1", 0, 100, 0, "", "knb", null, 1, "5→1", null],
    [5433, "CP 5 to 2", 0, 100, 0, "", "knb", null, 1, "5→2", null],
    [5434, "CP 5 to 3", 0, 100, 0, "", "knb", null, 1, "5→3", null],
    [5435, "CP 5 to 4", 0, 100, 0, "", "knb", null, 1, "5→4", null],
    [5436, "CP 5 to 5", 0, 100, 0, "", "knb", null, 1, "5→5", null],
    [5437, "CP 5 to 6", 0, 100, 0, "", "knb", null, 1, "5→6", null],
    [5438, "CP 6 to 1", 0, 100, 0, "", "knb", null, 1, "6→1", null],
    [5439, "CP 6 to 2", 0, 100, 0, "", "knb", null, 1, "6→2", null],
    [5440, "CP 6 to 3", 0, 100, 0, "", "knb", null, 1, "6→3", null],
    [5441, "CP 6 to 4", 0, 100, 0, "", "knb", null, 1, "6→4", null],
    [5442, "CP 6 to 5", 0, 100, 0, "", "knb", null, 1, "6→5", null],
    [5443, "CP 6 to 6", 0, 100, 0, "", "knb", null, 1, "6→6", null],
    [1700, "OSC 1 Physical Noise vs Mallet", 0, 1, 0.25, "", "sld", null, 1, "Noise", null],
    [1701, "OSC 1 Physical Mallet Hardness", 0, 1, 0.6, "", "sld", null, 1, "Hardness", null],
    [1702, "OSC 1 Physical Noise Time", 2, 3000, 60, "ms", "sld", null, 1, "Noise Time", null],
    [1703, "OSC 1 Physical A Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1704, "OSC 1 Physical A Decay", 0.02, 20, 2.5, "s", "sld", null, 1, "Decay", null],
    [1705, "OSC 1 Physical A Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1706, "OSC 1 Physical A Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1707, "OSC 1 Physical A Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1708, "OSC 1 Physical B Model", 0, 8, 3, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1709, "OSC 1 Physical B Decay", 0.02, 20, 1.5, "s", "sld", null, 1, "Decay", null],
    [1710, "OSC 1 Physical B Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1711, "OSC 1 Physical B Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1712, "OSC 1 Physical B Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1713, "OSC 1 Physical B Tune", -24, 24, 12, "st", "sld", null, 1, "Tune", null],
    [1714, "OSC 1 Physical A / B Balance", 0, 1, 0.35, "", "sld", null, 1, "A / B", null],
    [1715, "OSC 1 Physical Coupling", 0, 1, 0, "", "btn", ["Parallel", "Serial"], 1, "Coupling", null],
    [1732, "OSC 2 Physical Noise vs Mallet", 0, 1, 0.25, "", "sld", null, 1, "Noise", null],
    [1733, "OSC 2 Physical Mallet Hardness", 0, 1, 0.6, "", "sld", null, 1, "Hardness", null],
    [1734, "OSC 2 Physical Noise Time", 2, 3000, 60, "ms", "sld", null, 1, "Noise Time", null],
    [1735, "OSC 2 Physical A Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1736, "OSC 2 Physical A Decay", 0.02, 20, 2.5, "s", "sld", null, 1, "Decay", null],
    [1737, "OSC 2 Physical A Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1738, "OSC 2 Physical A Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1739, "OSC 2 Physical A Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1740, "OSC 2 Physical B Model", 0, 8, 3, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1741, "OSC 2 Physical B Decay", 0.02, 20, 1.5, "s", "sld", null, 1, "Decay", null],
    [1742, "OSC 2 Physical B Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1743, "OSC 2 Physical B Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1744, "OSC 2 Physical B Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1745, "OSC 2 Physical B Tune", -24, 24, 12, "st", "sld", null, 1, "Tune", null],
    [1746, "OSC 2 Physical A / B Balance", 0, 1, 0.35, "", "sld", null, 1, "A / B", null],
    [1747, "OSC 2 Physical Coupling", 0, 1, 0, "", "btn", ["Parallel", "Serial"], 1, "Coupling", null],
    [1764, "OSC 3 Physical Noise vs Mallet", 0, 1, 0.25, "", "sld", null, 1, "Noise", null],
    [1765, "OSC 3 Physical Mallet Hardness", 0, 1, 0.6, "", "sld", null, 1, "Hardness", null],
    [1766, "OSC 3 Physical Noise Time", 2, 3000, 60, "ms", "sld", null, 1, "Noise Time", null],
    [1767, "OSC 3 Physical A Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1768, "OSC 3 Physical A Decay", 0.02, 20, 2.5, "s", "sld", null, 1, "Decay", null],
    [1769, "OSC 3 Physical A Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1770, "OSC 3 Physical A Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1771, "OSC 3 Physical A Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1772, "OSC 3 Physical B Model", 0, 8, 3, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1773, "OSC 3 Physical B Decay", 0.02, 20, 1.5, "s", "sld", null, 1, "Decay", null],
    [1774, "OSC 3 Physical B Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1775, "OSC 3 Physical B Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1776, "OSC 3 Physical B Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1777, "OSC 3 Physical B Tune", -24, 24, 12, "st", "sld", null, 1, "Tune", null],
    [1778, "OSC 3 Physical A / B Balance", 0, 1, 0.35, "", "sld", null, 1, "A / B", null],
    [1779, "OSC 3 Physical Coupling", 0, 1, 0, "", "btn", ["Parallel", "Serial"], 1, "Coupling", null],
    [1796, "OSC 4 Physical Noise vs Mallet", 0, 1, 0.25, "", "sld", null, 1, "Noise", null],
    [1797, "OSC 4 Physical Mallet Hardness", 0, 1, 0.6, "", "sld", null, 1, "Hardness", null],
    [1798, "OSC 4 Physical Noise Time", 2, 3000, 60, "ms", "sld", null, 1, "Noise Time", null],
    [1799, "OSC 4 Physical A Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1800, "OSC 4 Physical A Decay", 0.02, 20, 2.5, "s", "sld", null, 1, "Decay", null],
    [1801, "OSC 4 Physical A Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1802, "OSC 4 Physical A Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1803, "OSC 4 Physical A Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1804, "OSC 4 Physical B Model", 0, 8, 3, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1805, "OSC 4 Physical B Decay", 0.02, 20, 1.5, "s", "sld", null, 1, "Decay", null],
    [1806, "OSC 4 Physical B Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1807, "OSC 4 Physical B Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1808, "OSC 4 Physical B Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1809, "OSC 4 Physical B Tune", -24, 24, 12, "st", "sld", null, 1, "Tune", null],
    [1810, "OSC 4 Physical A / B Balance", 0, 1, 0.35, "", "sld", null, 1, "A / B", null],
    [1811, "OSC 4 Physical Coupling", 0, 1, 0, "", "btn", ["Parallel", "Serial"], 1, "Coupling", null],
    [1828, "OSC 5 Physical Noise vs Mallet", 0, 1, 0.25, "", "sld", null, 1, "Noise", null],
    [1829, "OSC 5 Physical Mallet Hardness", 0, 1, 0.6, "", "sld", null, 1, "Hardness", null],
    [1830, "OSC 5 Physical Noise Time", 2, 3000, 60, "ms", "sld", null, 1, "Noise Time", null],
    [1831, "OSC 5 Physical A Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1832, "OSC 5 Physical A Decay", 0.02, 20, 2.5, "s", "sld", null, 1, "Decay", null],
    [1833, "OSC 5 Physical A Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1834, "OSC 5 Physical A Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1835, "OSC 5 Physical A Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1836, "OSC 5 Physical B Model", 0, 8, 3, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1837, "OSC 5 Physical B Decay", 0.02, 20, 1.5, "s", "sld", null, 1, "Decay", null],
    [1838, "OSC 5 Physical B Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1839, "OSC 5 Physical B Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1840, "OSC 5 Physical B Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1841, "OSC 5 Physical B Tune", -24, 24, 12, "st", "sld", null, 1, "Tune", null],
    [1842, "OSC 5 Physical A / B Balance", 0, 1, 0.35, "", "sld", null, 1, "A / B", null],
    [1843, "OSC 5 Physical Coupling", 0, 1, 0, "", "btn", ["Parallel", "Serial"], 1, "Coupling", null],
    [1860, "OSC 6 Physical Noise vs Mallet", 0, 1, 0.25, "", "sld", null, 1, "Noise", null],
    [1861, "OSC 6 Physical Mallet Hardness", 0, 1, 0.6, "", "sld", null, 1, "Hardness", null],
    [1862, "OSC 6 Physical Noise Time", 2, 3000, 60, "ms", "sld", null, 1, "Noise Time", null],
    [1863, "OSC 6 Physical A Model", 0, 8, 0, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1864, "OSC 6 Physical A Decay", 0.02, 20, 2.5, "s", "sld", null, 1, "Decay", null],
    [1865, "OSC 6 Physical A Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1866, "OSC 6 Physical A Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1867, "OSC 6 Physical A Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1868, "OSC 6 Physical B Model", 0, 8, 3, "", "sel", ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"], 1, "Model", null],
    [1869, "OSC 6 Physical B Decay", 0.02, 20, 1.5, "s", "sld", null, 1, "Decay", null],
    [1870, "OSC 6 Physical B Material", 0, 1, 0.5, "", "sld", null, 1, "Material", null],
    [1871, "OSC 6 Physical B Hit Position", 0, 1, 0.3, "", "sld", null, 1, "Hit", null],
    [1872, "OSC 6 Physical B Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [1873, "OSC 6 Physical B Tune", -24, 24, 12, "st", "sld", null, 1, "Tune", null],
    [1874, "OSC 6 Physical A / B Balance", 0, 1, 0.35, "", "sld", null, 1, "A / B", null],
    [1875, "OSC 6 Physical Coupling", 0, 1, 0, "", "btn", ["Parallel", "Serial"], 1, "Coupling", null],
    [1716, "OSC 1 Juno Saw Level", 0, 1, 0.8, "", "sld", null, 1, "Saw", null],
    [1717, "OSC 1 Juno Pulse Level", 0, 1, 0.0, "", "sld", null, 1, "Pulse", null],
    [1718, "OSC 1 Juno Pulse Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [1719, "OSC 1 Juno PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [1720, "OSC 1 Juno PWM Rate", 0.1, 20, 1.5, "Hz", "sld", null, 1, "PWM Rate", null],
    [1721, "OSC 1 Juno Sub Level", 0, 1, 0.5, "", "sld", null, 1, "Sub", null],
    [1722, "OSC 1 Juno Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1723, "OSC 1 Juno Range", 0, 2, 1, "", "btn", ["16'", "8'", "4'"], 1, "Range", null],
    [1724, "OSC 1 Juno Drift", 0, 1, 0.2, "", "sld", null, 1, "Drift", null],
    [1725, "OSC 1 Juno Saw Curve", 0, 1, 0.3, "", "sld", null, 1, "Curve", null],
    [1748, "OSC 2 Juno Saw Level", 0, 1, 0.8, "", "sld", null, 1, "Saw", null],
    [1749, "OSC 2 Juno Pulse Level", 0, 1, 0.0, "", "sld", null, 1, "Pulse", null],
    [1750, "OSC 2 Juno Pulse Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [1751, "OSC 2 Juno PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [1752, "OSC 2 Juno PWM Rate", 0.1, 20, 1.5, "Hz", "sld", null, 1, "PWM Rate", null],
    [1753, "OSC 2 Juno Sub Level", 0, 1, 0.5, "", "sld", null, 1, "Sub", null],
    [1754, "OSC 2 Juno Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1755, "OSC 2 Juno Range", 0, 2, 1, "", "btn", ["16'", "8'", "4'"], 1, "Range", null],
    [1756, "OSC 2 Juno Drift", 0, 1, 0.2, "", "sld", null, 1, "Drift", null],
    [1757, "OSC 2 Juno Saw Curve", 0, 1, 0.3, "", "sld", null, 1, "Curve", null],
    [1780, "OSC 3 Juno Saw Level", 0, 1, 0.8, "", "sld", null, 1, "Saw", null],
    [1781, "OSC 3 Juno Pulse Level", 0, 1, 0.0, "", "sld", null, 1, "Pulse", null],
    [1782, "OSC 3 Juno Pulse Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [1783, "OSC 3 Juno PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [1784, "OSC 3 Juno PWM Rate", 0.1, 20, 1.5, "Hz", "sld", null, 1, "PWM Rate", null],
    [1785, "OSC 3 Juno Sub Level", 0, 1, 0.5, "", "sld", null, 1, "Sub", null],
    [1786, "OSC 3 Juno Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1787, "OSC 3 Juno Range", 0, 2, 1, "", "btn", ["16'", "8'", "4'"], 1, "Range", null],
    [1788, "OSC 3 Juno Drift", 0, 1, 0.2, "", "sld", null, 1, "Drift", null],
    [1789, "OSC 3 Juno Saw Curve", 0, 1, 0.3, "", "sld", null, 1, "Curve", null],
    [1812, "OSC 4 Juno Saw Level", 0, 1, 0.8, "", "sld", null, 1, "Saw", null],
    [1813, "OSC 4 Juno Pulse Level", 0, 1, 0.0, "", "sld", null, 1, "Pulse", null],
    [1814, "OSC 4 Juno Pulse Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [1815, "OSC 4 Juno PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [1816, "OSC 4 Juno PWM Rate", 0.1, 20, 1.5, "Hz", "sld", null, 1, "PWM Rate", null],
    [1817, "OSC 4 Juno Sub Level", 0, 1, 0.5, "", "sld", null, 1, "Sub", null],
    [1818, "OSC 4 Juno Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1819, "OSC 4 Juno Range", 0, 2, 1, "", "btn", ["16'", "8'", "4'"], 1, "Range", null],
    [1820, "OSC 4 Juno Drift", 0, 1, 0.2, "", "sld", null, 1, "Drift", null],
    [1821, "OSC 4 Juno Saw Curve", 0, 1, 0.3, "", "sld", null, 1, "Curve", null],
    [1844, "OSC 5 Juno Saw Level", 0, 1, 0.8, "", "sld", null, 1, "Saw", null],
    [1845, "OSC 5 Juno Pulse Level", 0, 1, 0.0, "", "sld", null, 1, "Pulse", null],
    [1846, "OSC 5 Juno Pulse Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [1847, "OSC 5 Juno PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [1848, "OSC 5 Juno PWM Rate", 0.1, 20, 1.5, "Hz", "sld", null, 1, "PWM Rate", null],
    [1849, "OSC 5 Juno Sub Level", 0, 1, 0.5, "", "sld", null, 1, "Sub", null],
    [1850, "OSC 5 Juno Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1851, "OSC 5 Juno Range", 0, 2, 1, "", "btn", ["16'", "8'", "4'"], 1, "Range", null],
    [1852, "OSC 5 Juno Drift", 0, 1, 0.2, "", "sld", null, 1, "Drift", null],
    [1853, "OSC 5 Juno Saw Curve", 0, 1, 0.3, "", "sld", null, 1, "Curve", null],
    [1876, "OSC 6 Juno Saw Level", 0, 1, 0.8, "", "sld", null, 1, "Saw", null],
    [1877, "OSC 6 Juno Pulse Level", 0, 1, 0.0, "", "sld", null, 1, "Pulse", null],
    [1878, "OSC 6 Juno Pulse Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [1879, "OSC 6 Juno PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [1880, "OSC 6 Juno PWM Rate", 0.1, 20, 1.5, "Hz", "sld", null, 1, "PWM Rate", null],
    [1881, "OSC 6 Juno Sub Level", 0, 1, 0.5, "", "sld", null, 1, "Sub", null],
    [1882, "OSC 6 Juno Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1883, "OSC 6 Juno Range", 0, 2, 1, "", "btn", ["16'", "8'", "4'"], 1, "Range", null],
    [1884, "OSC 6 Juno Drift", 0, 1, 0.2, "", "sld", null, 1, "Drift", null],
    [1885, "OSC 6 Juno Saw Curve", 0, 1, 0.3, "", "sld", null, 1, "Curve", null],
    [1726, "OSC 1 Juno Pulse Wave", 0, 2, 0, "", "sel", ["Pulse 1", "Pulse 2", "Pulse 3"], 1, "Pulse Wave", null],
    [1727, "OSC 1 Juno Saw Wave", 0, 4, 0, "", "sel", ["Saw 1", "Saw 2", "Saw 3", "Saw 4", "Saw 5"], 1, "Saw Wave", null],
    [1728, "OSC 1 Juno Sub Wave", 0, 5, 0, "", "sel", ["Sub 1", "Sub 2", "Sub 3", "Sub 4", "Sub 5", "Sub 6"], 1, "Sub Wave", null],
    [1729, "OSC 1 Juno PWM Source", 0, 2, 0, "", "btn", ["LFO", "Env", "Manual"], 1, "PWM Source", null],
    [1730, "OSC 1 Juno Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [1758, "OSC 2 Juno Pulse Wave", 0, 2, 0, "", "sel", ["Pulse 1", "Pulse 2", "Pulse 3"], 1, "Pulse Wave", null],
    [1759, "OSC 2 Juno Saw Wave", 0, 4, 0, "", "sel", ["Saw 1", "Saw 2", "Saw 3", "Saw 4", "Saw 5"], 1, "Saw Wave", null],
    [1760, "OSC 2 Juno Sub Wave", 0, 5, 0, "", "sel", ["Sub 1", "Sub 2", "Sub 3", "Sub 4", "Sub 5", "Sub 6"], 1, "Sub Wave", null],
    [1761, "OSC 2 Juno PWM Source", 0, 2, 0, "", "btn", ["LFO", "Env", "Manual"], 1, "PWM Source", null],
    [1762, "OSC 2 Juno Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [1790, "OSC 3 Juno Pulse Wave", 0, 2, 0, "", "sel", ["Pulse 1", "Pulse 2", "Pulse 3"], 1, "Pulse Wave", null],
    [1791, "OSC 3 Juno Saw Wave", 0, 4, 0, "", "sel", ["Saw 1", "Saw 2", "Saw 3", "Saw 4", "Saw 5"], 1, "Saw Wave", null],
    [1792, "OSC 3 Juno Sub Wave", 0, 5, 0, "", "sel", ["Sub 1", "Sub 2", "Sub 3", "Sub 4", "Sub 5", "Sub 6"], 1, "Sub Wave", null],
    [1793, "OSC 3 Juno PWM Source", 0, 2, 0, "", "btn", ["LFO", "Env", "Manual"], 1, "PWM Source", null],
    [1794, "OSC 3 Juno Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [1822, "OSC 4 Juno Pulse Wave", 0, 2, 0, "", "sel", ["Pulse 1", "Pulse 2", "Pulse 3"], 1, "Pulse Wave", null],
    [1823, "OSC 4 Juno Saw Wave", 0, 4, 0, "", "sel", ["Saw 1", "Saw 2", "Saw 3", "Saw 4", "Saw 5"], 1, "Saw Wave", null],
    [1824, "OSC 4 Juno Sub Wave", 0, 5, 0, "", "sel", ["Sub 1", "Sub 2", "Sub 3", "Sub 4", "Sub 5", "Sub 6"], 1, "Sub Wave", null],
    [1825, "OSC 4 Juno PWM Source", 0, 2, 0, "", "btn", ["LFO", "Env", "Manual"], 1, "PWM Source", null],
    [1826, "OSC 4 Juno Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [1854, "OSC 5 Juno Pulse Wave", 0, 2, 0, "", "sel", ["Pulse 1", "Pulse 2", "Pulse 3"], 1, "Pulse Wave", null],
    [1855, "OSC 5 Juno Saw Wave", 0, 4, 0, "", "sel", ["Saw 1", "Saw 2", "Saw 3", "Saw 4", "Saw 5"], 1, "Saw Wave", null],
    [1856, "OSC 5 Juno Sub Wave", 0, 5, 0, "", "sel", ["Sub 1", "Sub 2", "Sub 3", "Sub 4", "Sub 5", "Sub 6"], 1, "Sub Wave", null],
    [1857, "OSC 5 Juno PWM Source", 0, 2, 0, "", "btn", ["LFO", "Env", "Manual"], 1, "PWM Source", null],
    [1858, "OSC 5 Juno Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [1886, "OSC 6 Juno Pulse Wave", 0, 2, 0, "", "sel", ["Pulse 1", "Pulse 2", "Pulse 3"], 1, "Pulse Wave", null],
    [1887, "OSC 6 Juno Saw Wave", 0, 4, 0, "", "sel", ["Saw 1", "Saw 2", "Saw 3", "Saw 4", "Saw 5"], 1, "Saw Wave", null],
    [1888, "OSC 6 Juno Sub Wave", 0, 5, 0, "", "sel", ["Sub 1", "Sub 2", "Sub 3", "Sub 4", "Sub 5", "Sub 6"], 1, "Sub Wave", null],
    [1889, "OSC 6 Juno PWM Source", 0, 2, 0, "", "btn", ["LFO", "Env", "Manual"], 1, "PWM Source", null],
    [1890, "OSC 6 Juno Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [1900, "OSC 1 Kick Mode", 0, 3, 0, "", "sel", ["Classic", "808", "Punch", "Hardstyle"], 1, "Mode", null],
    [1901, "OSC 1 Kick Pitch Sweep", 0, 6, 2.5, "oct", "sld", null, 1, "Sweep", null],
    [1902, "OSC 1 Kick Sweep Time", 5, 1000, 60, "ms", "sld", null, 1, "Sweep Time", null],
    [1903, "OSC 1 Kick Sweep Curve", 0, 1, 0.5, "", "sld", null, 1, "Curve", null],
    [1904, "OSC 1 Kick Decay", 20, 3000, 450, "ms", "sld", null, 1, "Decay", null],
    [1905, "OSC 1 Kick Tone", 0, 1, 0.3, "", "sld", null, 1, "Tone", null],
    [1906, "OSC 1 Kick Click Level", 0, 1, 0.35, "", "sld", null, 1, "Click", null],
    [1907, "OSC 1 Kick Click Tone", 0, 1, 0.5, "", "sld", null, 1, "Click Tone", null],
    [1908, "OSC 1 Kick Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1909, "OSC 1 Kick Drive", 0, 1, 0.2, "", "sld", null, 1, "Drive", null],
    [1910, "OSC 1 Kick Drive Curve", 0, 5, 1, "", "sel", ["Hard Clip", "Tanh", "Atan", "Log", "Exp", "Poly"], 1, "Curve", null],
    [1911, "OSC 1 Kick Sub Level", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [1912, "OSC 1 Kick Punch", 0, 1, 0.3, "", "sld", null, 1, "Punch", null],
    [1913, "OSC 1 Kick Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1914, "OSC 1 Kick Click Decay", 1, 40, 6, "ms", "sld", null, 1, "Click Decay", null],
    [1915, "OSC 1 Kick Character", 0, 1, 0.5, "", "sld", null, 1, "Character", null],
    [1916, "OSC 2 Kick Mode", 0, 3, 0, "", "sel", ["Classic", "808", "Punch", "Hardstyle"], 1, "Mode", null],
    [1917, "OSC 2 Kick Pitch Sweep", 0, 6, 2.5, "oct", "sld", null, 1, "Sweep", null],
    [1918, "OSC 2 Kick Sweep Time", 5, 1000, 60, "ms", "sld", null, 1, "Sweep Time", null],
    [1919, "OSC 2 Kick Sweep Curve", 0, 1, 0.5, "", "sld", null, 1, "Curve", null],
    [1920, "OSC 2 Kick Decay", 20, 3000, 450, "ms", "sld", null, 1, "Decay", null],
    [1921, "OSC 2 Kick Tone", 0, 1, 0.3, "", "sld", null, 1, "Tone", null],
    [1922, "OSC 2 Kick Click Level", 0, 1, 0.35, "", "sld", null, 1, "Click", null],
    [1923, "OSC 2 Kick Click Tone", 0, 1, 0.5, "", "sld", null, 1, "Click Tone", null],
    [1924, "OSC 2 Kick Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1925, "OSC 2 Kick Drive", 0, 1, 0.2, "", "sld", null, 1, "Drive", null],
    [1926, "OSC 2 Kick Drive Curve", 0, 5, 1, "", "sel", ["Hard Clip", "Tanh", "Atan", "Log", "Exp", "Poly"], 1, "Curve", null],
    [1927, "OSC 2 Kick Sub Level", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [1928, "OSC 2 Kick Punch", 0, 1, 0.3, "", "sld", null, 1, "Punch", null],
    [1929, "OSC 2 Kick Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1930, "OSC 2 Kick Click Decay", 1, 40, 6, "ms", "sld", null, 1, "Click Decay", null],
    [1931, "OSC 2 Kick Character", 0, 1, 0.5, "", "sld", null, 1, "Character", null],
    [1932, "OSC 3 Kick Mode", 0, 3, 0, "", "sel", ["Classic", "808", "Punch", "Hardstyle"], 1, "Mode", null],
    [1933, "OSC 3 Kick Pitch Sweep", 0, 6, 2.5, "oct", "sld", null, 1, "Sweep", null],
    [1934, "OSC 3 Kick Sweep Time", 5, 1000, 60, "ms", "sld", null, 1, "Sweep Time", null],
    [1935, "OSC 3 Kick Sweep Curve", 0, 1, 0.5, "", "sld", null, 1, "Curve", null],
    [1936, "OSC 3 Kick Decay", 20, 3000, 450, "ms", "sld", null, 1, "Decay", null],
    [1937, "OSC 3 Kick Tone", 0, 1, 0.3, "", "sld", null, 1, "Tone", null],
    [1938, "OSC 3 Kick Click Level", 0, 1, 0.35, "", "sld", null, 1, "Click", null],
    [1939, "OSC 3 Kick Click Tone", 0, 1, 0.5, "", "sld", null, 1, "Click Tone", null],
    [1940, "OSC 3 Kick Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1941, "OSC 3 Kick Drive", 0, 1, 0.2, "", "sld", null, 1, "Drive", null],
    [1942, "OSC 3 Kick Drive Curve", 0, 5, 1, "", "sel", ["Hard Clip", "Tanh", "Atan", "Log", "Exp", "Poly"], 1, "Curve", null],
    [1943, "OSC 3 Kick Sub Level", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [1944, "OSC 3 Kick Punch", 0, 1, 0.3, "", "sld", null, 1, "Punch", null],
    [1945, "OSC 3 Kick Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1946, "OSC 3 Kick Click Decay", 1, 40, 6, "ms", "sld", null, 1, "Click Decay", null],
    [1947, "OSC 3 Kick Character", 0, 1, 0.5, "", "sld", null, 1, "Character", null],
    [1948, "OSC 4 Kick Mode", 0, 3, 0, "", "sel", ["Classic", "808", "Punch", "Hardstyle"], 1, "Mode", null],
    [1949, "OSC 4 Kick Pitch Sweep", 0, 6, 2.5, "oct", "sld", null, 1, "Sweep", null],
    [1950, "OSC 4 Kick Sweep Time", 5, 1000, 60, "ms", "sld", null, 1, "Sweep Time", null],
    [1951, "OSC 4 Kick Sweep Curve", 0, 1, 0.5, "", "sld", null, 1, "Curve", null],
    [1952, "OSC 4 Kick Decay", 20, 3000, 450, "ms", "sld", null, 1, "Decay", null],
    [1953, "OSC 4 Kick Tone", 0, 1, 0.3, "", "sld", null, 1, "Tone", null],
    [1954, "OSC 4 Kick Click Level", 0, 1, 0.35, "", "sld", null, 1, "Click", null],
    [1955, "OSC 4 Kick Click Tone", 0, 1, 0.5, "", "sld", null, 1, "Click Tone", null],
    [1956, "OSC 4 Kick Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1957, "OSC 4 Kick Drive", 0, 1, 0.2, "", "sld", null, 1, "Drive", null],
    [1958, "OSC 4 Kick Drive Curve", 0, 5, 1, "", "sel", ["Hard Clip", "Tanh", "Atan", "Log", "Exp", "Poly"], 1, "Curve", null],
    [1959, "OSC 4 Kick Sub Level", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [1960, "OSC 4 Kick Punch", 0, 1, 0.3, "", "sld", null, 1, "Punch", null],
    [1961, "OSC 4 Kick Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1962, "OSC 4 Kick Click Decay", 1, 40, 6, "ms", "sld", null, 1, "Click Decay", null],
    [1963, "OSC 4 Kick Character", 0, 1, 0.5, "", "sld", null, 1, "Character", null],
    [1964, "OSC 5 Kick Mode", 0, 3, 0, "", "sel", ["Classic", "808", "Punch", "Hardstyle"], 1, "Mode", null],
    [1965, "OSC 5 Kick Pitch Sweep", 0, 6, 2.5, "oct", "sld", null, 1, "Sweep", null],
    [1966, "OSC 5 Kick Sweep Time", 5, 1000, 60, "ms", "sld", null, 1, "Sweep Time", null],
    [1967, "OSC 5 Kick Sweep Curve", 0, 1, 0.5, "", "sld", null, 1, "Curve", null],
    [1968, "OSC 5 Kick Decay", 20, 3000, 450, "ms", "sld", null, 1, "Decay", null],
    [1969, "OSC 5 Kick Tone", 0, 1, 0.3, "", "sld", null, 1, "Tone", null],
    [1970, "OSC 5 Kick Click Level", 0, 1, 0.35, "", "sld", null, 1, "Click", null],
    [1971, "OSC 5 Kick Click Tone", 0, 1, 0.5, "", "sld", null, 1, "Click Tone", null],
    [1972, "OSC 5 Kick Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1973, "OSC 5 Kick Drive", 0, 1, 0.2, "", "sld", null, 1, "Drive", null],
    [1974, "OSC 5 Kick Drive Curve", 0, 5, 1, "", "sel", ["Hard Clip", "Tanh", "Atan", "Log", "Exp", "Poly"], 1, "Curve", null],
    [1975, "OSC 5 Kick Sub Level", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [1976, "OSC 5 Kick Punch", 0, 1, 0.3, "", "sld", null, 1, "Punch", null],
    [1977, "OSC 5 Kick Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1978, "OSC 5 Kick Click Decay", 1, 40, 6, "ms", "sld", null, 1, "Click Decay", null],
    [1979, "OSC 5 Kick Character", 0, 1, 0.5, "", "sld", null, 1, "Character", null],
    [1980, "OSC 6 Kick Mode", 0, 3, 0, "", "sel", ["Classic", "808", "Punch", "Hardstyle"], 1, "Mode", null],
    [1981, "OSC 6 Kick Pitch Sweep", 0, 6, 2.5, "oct", "sld", null, 1, "Sweep", null],
    [1982, "OSC 6 Kick Sweep Time", 5, 1000, 60, "ms", "sld", null, 1, "Sweep Time", null],
    [1983, "OSC 6 Kick Sweep Curve", 0, 1, 0.5, "", "sld", null, 1, "Curve", null],
    [1984, "OSC 6 Kick Decay", 20, 3000, 450, "ms", "sld", null, 1, "Decay", null],
    [1985, "OSC 6 Kick Tone", 0, 1, 0.3, "", "sld", null, 1, "Tone", null],
    [1986, "OSC 6 Kick Click Level", 0, 1, 0.35, "", "sld", null, 1, "Click", null],
    [1987, "OSC 6 Kick Click Tone", 0, 1, 0.5, "", "sld", null, 1, "Click Tone", null],
    [1988, "OSC 6 Kick Noise Level", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [1989, "OSC 6 Kick Drive", 0, 1, 0.2, "", "sld", null, 1, "Drive", null],
    [1990, "OSC 6 Kick Drive Curve", 0, 5, 1, "", "sel", ["Hard Clip", "Tanh", "Atan", "Log", "Exp", "Poly"], 1, "Curve", null],
    [1991, "OSC 6 Kick Sub Level", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [1992, "OSC 6 Kick Punch", 0, 1, 0.3, "", "sld", null, 1, "Punch", null],
    [1993, "OSC 6 Kick Tune", -24, 24, 0, "st", "sld", null, 1, "Tune", null],
    [1994, "OSC 6 Kick Click Decay", 1, 40, 6, "ms", "sld", null, 1, "Click Decay", null],
    [1995, "OSC 6 Kick Character", 0, 1, 0.5, "", "sld", null, 1, "Character", null],
    [2000, "OSC 1 WT Quality", 0, 2, 0, "", "sel", ["Clean", "Alias", "Eco"], 1, "Quality", null],
    [2001, "OSC 2 WT Quality", 0, 2, 0, "", "sel", ["Clean", "Alias", "Eco"], 1, "Quality", null],
    [2002, "OSC 3 WT Quality", 0, 2, 0, "", "sel", ["Clean", "Alias", "Eco"], 1, "Quality", null],
    [2003, "OSC 4 WT Quality", 0, 2, 0, "", "sel", ["Clean", "Alias", "Eco"], 1, "Quality", null],
    [2004, "OSC 5 WT Quality", 0, 2, 0, "", "sel", ["Clean", "Alias", "Eco"], 1, "Quality", null],
    [2005, "OSC 6 WT Quality", 0, 2, 0, "", "sel", ["Clean", "Alias", "Eco"], 1, "Quality", null],
    [2100, "OSC 1 Terrain Orbit Center X", -1, 1, 0.0, "", "sld", null, 1, "Center X", null],
    [2101, "OSC 1 Terrain Orbit Center Y", -1, 1, 0.0, "", "sld", null, 1, "Center Y", null],
    [2102, "OSC 1 Terrain Orbit Radius X", 0, 1, 0.6, "", "sld", null, 1, "Radius X", null],
    [2103, "OSC 1 Terrain Orbit Radius Y", 0, 1, 0.6, "", "sld", null, 1, "Radius Y", null],
    [2104, "OSC 1 Terrain Orbit Rotation", 0, 1, 0.0, "", "sld", null, 1, "Rotation", null],
    [2105, "OSC 1 Terrain Orbit Ratio", 0.25, 8, 1.0, "", "sld", null, 1, "Y : X", null],
    [2106, "OSC 1 Terrain Orbit Phase", 0, 1, 0.0, "", "sld", null, 1, "Phase", null],
    [2107, "OSC 1 Terrain Orbit Shape", 0, 1, 0.0, "", "sld", null, 1, "Shape", null],
    [2108, "OSC 1 Terrain Move Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "Move Rate", null],
    [2109, "OSC 1 Terrain Move Depth", 0, 1, 0.0, "", "sld", null, 1, "Move Depth", null],
    [2110, "OSC 1 Terrain B", 0, 11, 1, "", "sel", TERRAINS, 1, "Terrain B", null],
    [2111, "OSC 1 Terrain Morph A to B", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2112, "OSC 1 Terrain Smooth", 0, 1, 0.3, "", "sld", null, 1, "Smooth", null],
    [2113, "OSC 1 Terrain Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2114, "OSC 1 Terrain Bit Depth", 2, 16, 16, "", "sld", null, 1, "Bits", null],
    [2115, "OSC 1 Terrain Velocity to Radius", -1, 1, 0.0, "", "sld", null, 1, "Vel > Radius", null],
    [2116, "OSC 2 Terrain Orbit Center X", -1, 1, 0.0, "", "sld", null, 1, "Center X", null],
    [2117, "OSC 2 Terrain Orbit Center Y", -1, 1, 0.0, "", "sld", null, 1, "Center Y", null],
    [2118, "OSC 2 Terrain Orbit Radius X", 0, 1, 0.6, "", "sld", null, 1, "Radius X", null],
    [2119, "OSC 2 Terrain Orbit Radius Y", 0, 1, 0.6, "", "sld", null, 1, "Radius Y", null],
    [2120, "OSC 2 Terrain Orbit Rotation", 0, 1, 0.0, "", "sld", null, 1, "Rotation", null],
    [2121, "OSC 2 Terrain Orbit Ratio", 0.25, 8, 1.0, "", "sld", null, 1, "Y : X", null],
    [2122, "OSC 2 Terrain Orbit Phase", 0, 1, 0.0, "", "sld", null, 1, "Phase", null],
    [2123, "OSC 2 Terrain Orbit Shape", 0, 1, 0.0, "", "sld", null, 1, "Shape", null],
    [2124, "OSC 2 Terrain Move Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "Move Rate", null],
    [2125, "OSC 2 Terrain Move Depth", 0, 1, 0.0, "", "sld", null, 1, "Move Depth", null],
    [2126, "OSC 2 Terrain B", 0, 11, 1, "", "sel", TERRAINS, 1, "Terrain B", null],
    [2127, "OSC 2 Terrain Morph A to B", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2128, "OSC 2 Terrain Smooth", 0, 1, 0.3, "", "sld", null, 1, "Smooth", null],
    [2129, "OSC 2 Terrain Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2130, "OSC 2 Terrain Bit Depth", 2, 16, 16, "", "sld", null, 1, "Bits", null],
    [2131, "OSC 2 Terrain Velocity to Radius", -1, 1, 0.0, "", "sld", null, 1, "Vel > Radius", null],
    [2132, "OSC 3 Terrain Orbit Center X", -1, 1, 0.0, "", "sld", null, 1, "Center X", null],
    [2133, "OSC 3 Terrain Orbit Center Y", -1, 1, 0.0, "", "sld", null, 1, "Center Y", null],
    [2134, "OSC 3 Terrain Orbit Radius X", 0, 1, 0.6, "", "sld", null, 1, "Radius X", null],
    [2135, "OSC 3 Terrain Orbit Radius Y", 0, 1, 0.6, "", "sld", null, 1, "Radius Y", null],
    [2136, "OSC 3 Terrain Orbit Rotation", 0, 1, 0.0, "", "sld", null, 1, "Rotation", null],
    [2137, "OSC 3 Terrain Orbit Ratio", 0.25, 8, 1.0, "", "sld", null, 1, "Y : X", null],
    [2138, "OSC 3 Terrain Orbit Phase", 0, 1, 0.0, "", "sld", null, 1, "Phase", null],
    [2139, "OSC 3 Terrain Orbit Shape", 0, 1, 0.0, "", "sld", null, 1, "Shape", null],
    [2140, "OSC 3 Terrain Move Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "Move Rate", null],
    [2141, "OSC 3 Terrain Move Depth", 0, 1, 0.0, "", "sld", null, 1, "Move Depth", null],
    [2142, "OSC 3 Terrain B", 0, 11, 1, "", "sel", TERRAINS, 1, "Terrain B", null],
    [2143, "OSC 3 Terrain Morph A to B", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2144, "OSC 3 Terrain Smooth", 0, 1, 0.3, "", "sld", null, 1, "Smooth", null],
    [2145, "OSC 3 Terrain Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2146, "OSC 3 Terrain Bit Depth", 2, 16, 16, "", "sld", null, 1, "Bits", null],
    [2147, "OSC 3 Terrain Velocity to Radius", -1, 1, 0.0, "", "sld", null, 1, "Vel > Radius", null],
    [2148, "OSC 4 Terrain Orbit Center X", -1, 1, 0.0, "", "sld", null, 1, "Center X", null],
    [2149, "OSC 4 Terrain Orbit Center Y", -1, 1, 0.0, "", "sld", null, 1, "Center Y", null],
    [2150, "OSC 4 Terrain Orbit Radius X", 0, 1, 0.6, "", "sld", null, 1, "Radius X", null],
    [2151, "OSC 4 Terrain Orbit Radius Y", 0, 1, 0.6, "", "sld", null, 1, "Radius Y", null],
    [2152, "OSC 4 Terrain Orbit Rotation", 0, 1, 0.0, "", "sld", null, 1, "Rotation", null],
    [2153, "OSC 4 Terrain Orbit Ratio", 0.25, 8, 1.0, "", "sld", null, 1, "Y : X", null],
    [2154, "OSC 4 Terrain Orbit Phase", 0, 1, 0.0, "", "sld", null, 1, "Phase", null],
    [2155, "OSC 4 Terrain Orbit Shape", 0, 1, 0.0, "", "sld", null, 1, "Shape", null],
    [2156, "OSC 4 Terrain Move Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "Move Rate", null],
    [2157, "OSC 4 Terrain Move Depth", 0, 1, 0.0, "", "sld", null, 1, "Move Depth", null],
    [2158, "OSC 4 Terrain B", 0, 11, 1, "", "sel", TERRAINS, 1, "Terrain B", null],
    [2159, "OSC 4 Terrain Morph A to B", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2160, "OSC 4 Terrain Smooth", 0, 1, 0.3, "", "sld", null, 1, "Smooth", null],
    [2161, "OSC 4 Terrain Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2162, "OSC 4 Terrain Bit Depth", 2, 16, 16, "", "sld", null, 1, "Bits", null],
    [2163, "OSC 4 Terrain Velocity to Radius", -1, 1, 0.0, "", "sld", null, 1, "Vel > Radius", null],
    [2164, "OSC 5 Terrain Orbit Center X", -1, 1, 0.0, "", "sld", null, 1, "Center X", null],
    [2165, "OSC 5 Terrain Orbit Center Y", -1, 1, 0.0, "", "sld", null, 1, "Center Y", null],
    [2166, "OSC 5 Terrain Orbit Radius X", 0, 1, 0.6, "", "sld", null, 1, "Radius X", null],
    [2167, "OSC 5 Terrain Orbit Radius Y", 0, 1, 0.6, "", "sld", null, 1, "Radius Y", null],
    [2168, "OSC 5 Terrain Orbit Rotation", 0, 1, 0.0, "", "sld", null, 1, "Rotation", null],
    [2169, "OSC 5 Terrain Orbit Ratio", 0.25, 8, 1.0, "", "sld", null, 1, "Y : X", null],
    [2170, "OSC 5 Terrain Orbit Phase", 0, 1, 0.0, "", "sld", null, 1, "Phase", null],
    [2171, "OSC 5 Terrain Orbit Shape", 0, 1, 0.0, "", "sld", null, 1, "Shape", null],
    [2172, "OSC 5 Terrain Move Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "Move Rate", null],
    [2173, "OSC 5 Terrain Move Depth", 0, 1, 0.0, "", "sld", null, 1, "Move Depth", null],
    [2174, "OSC 5 Terrain B", 0, 11, 1, "", "sel", TERRAINS, 1, "Terrain B", null],
    [2175, "OSC 5 Terrain Morph A to B", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2176, "OSC 5 Terrain Smooth", 0, 1, 0.3, "", "sld", null, 1, "Smooth", null],
    [2177, "OSC 5 Terrain Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2178, "OSC 5 Terrain Bit Depth", 2, 16, 16, "", "sld", null, 1, "Bits", null],
    [2179, "OSC 5 Terrain Velocity to Radius", -1, 1, 0.0, "", "sld", null, 1, "Vel > Radius", null],
    [2180, "OSC 6 Terrain Orbit Center X", -1, 1, 0.0, "", "sld", null, 1, "Center X", null],
    [2181, "OSC 6 Terrain Orbit Center Y", -1, 1, 0.0, "", "sld", null, 1, "Center Y", null],
    [2182, "OSC 6 Terrain Orbit Radius X", 0, 1, 0.6, "", "sld", null, 1, "Radius X", null],
    [2183, "OSC 6 Terrain Orbit Radius Y", 0, 1, 0.6, "", "sld", null, 1, "Radius Y", null],
    [2184, "OSC 6 Terrain Orbit Rotation", 0, 1, 0.0, "", "sld", null, 1, "Rotation", null],
    [2185, "OSC 6 Terrain Orbit Ratio", 0.25, 8, 1.0, "", "sld", null, 1, "Y : X", null],
    [2186, "OSC 6 Terrain Orbit Phase", 0, 1, 0.0, "", "sld", null, 1, "Phase", null],
    [2187, "OSC 6 Terrain Orbit Shape", 0, 1, 0.0, "", "sld", null, 1, "Shape", null],
    [2188, "OSC 6 Terrain Move Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "Move Rate", null],
    [2189, "OSC 6 Terrain Move Depth", 0, 1, 0.0, "", "sld", null, 1, "Move Depth", null],
    [2190, "OSC 6 Terrain B", 0, 11, 1, "", "sel", TERRAINS, 1, "Terrain B", null],
    [2191, "OSC 6 Terrain Morph A to B", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2192, "OSC 6 Terrain Smooth", 0, 1, 0.3, "", "sld", null, 1, "Smooth", null],
    [2193, "OSC 6 Terrain Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2194, "OSC 6 Terrain Bit Depth", 2, 16, 16, "", "sld", null, 1, "Bits", null],
    [2195, "OSC 6 Terrain Velocity to Radius", -1, 1, 0.0, "", "sld", null, 1, "Vel > Radius", null],
    [2200, "OSC 1 Waveguide Model", 0, 16, 0, "", "sel", WG_MODELS, 1, "Model", null],
    [2201, "OSC 1 Waveguide Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2202, "OSC 1 Waveguide Tone", 0, 1, 0.6, "", "sld", null, 1, "Tone", null],
    [2203, "OSC 1 Waveguide Excite", 0, 1, 0.6, "", "sld", null, 1, "Excite", null],
    [2204, "OSC 1 Waveguide Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2205, "OSC 1 Waveguide Noise", 0, 1, 0.2, "", "sld", null, 1, "Noise", null],
    [2206, "OSC 1 Waveguide Nonlinear", 0, 1, 0.0, "", "sld", null, 1, "Nonlinear", null],
    [2207, "OSC 1 Waveguide Stretch", 0, 1, 0.0, "", "sld", null, 1, "Stretch", null],
    [2208, "OSC 1 Waveguide Attack", 0, 1, 0.2, "", "sld", null, 1, "Attack", null],
    [2209, "OSC 1 Waveguide Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2210, "OSC 1 Waveguide Body", 0, 1, 0.0, "", "sld", null, 1, "Body", null],
    [2211, "OSC 1 Waveguide Body Tune", 0, 1, 0.4, "", "sld", null, 1, "Body Tune", null],
    [2212, "OSC 1 Waveguide Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Excite", null],
    [2213, "OSC 1 Waveguide Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2214, "OSC 1 Waveguide Tension", 0, 1, 0.0, "", "sld", null, 1, "Tension", null],
    [2215, "OSC 1 Waveguide Key Decay", 0, 1, 0.3, "", "sld", null, 1, "Key Decay", null],
    [2216, "OSC 2 Waveguide Model", 0, 16, 0, "", "sel", WG_MODELS, 1, "Model", null],
    [2217, "OSC 2 Waveguide Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2218, "OSC 2 Waveguide Tone", 0, 1, 0.6, "", "sld", null, 1, "Tone", null],
    [2219, "OSC 2 Waveguide Excite", 0, 1, 0.6, "", "sld", null, 1, "Excite", null],
    [2220, "OSC 2 Waveguide Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2221, "OSC 2 Waveguide Noise", 0, 1, 0.2, "", "sld", null, 1, "Noise", null],
    [2222, "OSC 2 Waveguide Nonlinear", 0, 1, 0.0, "", "sld", null, 1, "Nonlinear", null],
    [2223, "OSC 2 Waveguide Stretch", 0, 1, 0.0, "", "sld", null, 1, "Stretch", null],
    [2224, "OSC 2 Waveguide Attack", 0, 1, 0.2, "", "sld", null, 1, "Attack", null],
    [2225, "OSC 2 Waveguide Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2226, "OSC 2 Waveguide Body", 0, 1, 0.0, "", "sld", null, 1, "Body", null],
    [2227, "OSC 2 Waveguide Body Tune", 0, 1, 0.4, "", "sld", null, 1, "Body Tune", null],
    [2228, "OSC 2 Waveguide Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Excite", null],
    [2229, "OSC 2 Waveguide Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2230, "OSC 2 Waveguide Tension", 0, 1, 0.0, "", "sld", null, 1, "Tension", null],
    [2231, "OSC 2 Waveguide Key Decay", 0, 1, 0.3, "", "sld", null, 1, "Key Decay", null],
    [2232, "OSC 3 Waveguide Model", 0, 16, 0, "", "sel", WG_MODELS, 1, "Model", null],
    [2233, "OSC 3 Waveguide Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2234, "OSC 3 Waveguide Tone", 0, 1, 0.6, "", "sld", null, 1, "Tone", null],
    [2235, "OSC 3 Waveguide Excite", 0, 1, 0.6, "", "sld", null, 1, "Excite", null],
    [2236, "OSC 3 Waveguide Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2237, "OSC 3 Waveguide Noise", 0, 1, 0.2, "", "sld", null, 1, "Noise", null],
    [2238, "OSC 3 Waveguide Nonlinear", 0, 1, 0.0, "", "sld", null, 1, "Nonlinear", null],
    [2239, "OSC 3 Waveguide Stretch", 0, 1, 0.0, "", "sld", null, 1, "Stretch", null],
    [2240, "OSC 3 Waveguide Attack", 0, 1, 0.2, "", "sld", null, 1, "Attack", null],
    [2241, "OSC 3 Waveguide Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2242, "OSC 3 Waveguide Body", 0, 1, 0.0, "", "sld", null, 1, "Body", null],
    [2243, "OSC 3 Waveguide Body Tune", 0, 1, 0.4, "", "sld", null, 1, "Body Tune", null],
    [2244, "OSC 3 Waveguide Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Excite", null],
    [2245, "OSC 3 Waveguide Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2246, "OSC 3 Waveguide Tension", 0, 1, 0.0, "", "sld", null, 1, "Tension", null],
    [2247, "OSC 3 Waveguide Key Decay", 0, 1, 0.3, "", "sld", null, 1, "Key Decay", null],
    [2248, "OSC 4 Waveguide Model", 0, 16, 0, "", "sel", WG_MODELS, 1, "Model", null],
    [2249, "OSC 4 Waveguide Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2250, "OSC 4 Waveguide Tone", 0, 1, 0.6, "", "sld", null, 1, "Tone", null],
    [2251, "OSC 4 Waveguide Excite", 0, 1, 0.6, "", "sld", null, 1, "Excite", null],
    [2252, "OSC 4 Waveguide Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2253, "OSC 4 Waveguide Noise", 0, 1, 0.2, "", "sld", null, 1, "Noise", null],
    [2254, "OSC 4 Waveguide Nonlinear", 0, 1, 0.0, "", "sld", null, 1, "Nonlinear", null],
    [2255, "OSC 4 Waveguide Stretch", 0, 1, 0.0, "", "sld", null, 1, "Stretch", null],
    [2256, "OSC 4 Waveguide Attack", 0, 1, 0.2, "", "sld", null, 1, "Attack", null],
    [2257, "OSC 4 Waveguide Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2258, "OSC 4 Waveguide Body", 0, 1, 0.0, "", "sld", null, 1, "Body", null],
    [2259, "OSC 4 Waveguide Body Tune", 0, 1, 0.4, "", "sld", null, 1, "Body Tune", null],
    [2260, "OSC 4 Waveguide Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Excite", null],
    [2261, "OSC 4 Waveguide Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2262, "OSC 4 Waveguide Tension", 0, 1, 0.0, "", "sld", null, 1, "Tension", null],
    [2263, "OSC 4 Waveguide Key Decay", 0, 1, 0.3, "", "sld", null, 1, "Key Decay", null],
    [2264, "OSC 5 Waveguide Model", 0, 16, 0, "", "sel", WG_MODELS, 1, "Model", null],
    [2265, "OSC 5 Waveguide Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2266, "OSC 5 Waveguide Tone", 0, 1, 0.6, "", "sld", null, 1, "Tone", null],
    [2267, "OSC 5 Waveguide Excite", 0, 1, 0.6, "", "sld", null, 1, "Excite", null],
    [2268, "OSC 5 Waveguide Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2269, "OSC 5 Waveguide Noise", 0, 1, 0.2, "", "sld", null, 1, "Noise", null],
    [2270, "OSC 5 Waveguide Nonlinear", 0, 1, 0.0, "", "sld", null, 1, "Nonlinear", null],
    [2271, "OSC 5 Waveguide Stretch", 0, 1, 0.0, "", "sld", null, 1, "Stretch", null],
    [2272, "OSC 5 Waveguide Attack", 0, 1, 0.2, "", "sld", null, 1, "Attack", null],
    [2273, "OSC 5 Waveguide Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2274, "OSC 5 Waveguide Body", 0, 1, 0.0, "", "sld", null, 1, "Body", null],
    [2275, "OSC 5 Waveguide Body Tune", 0, 1, 0.4, "", "sld", null, 1, "Body Tune", null],
    [2276, "OSC 5 Waveguide Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Excite", null],
    [2277, "OSC 5 Waveguide Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2278, "OSC 5 Waveguide Tension", 0, 1, 0.0, "", "sld", null, 1, "Tension", null],
    [2279, "OSC 5 Waveguide Key Decay", 0, 1, 0.3, "", "sld", null, 1, "Key Decay", null],
    [2280, "OSC 6 Waveguide Model", 0, 16, 0, "", "sel", WG_MODELS, 1, "Model", null],
    [2281, "OSC 6 Waveguide Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2282, "OSC 6 Waveguide Tone", 0, 1, 0.6, "", "sld", null, 1, "Tone", null],
    [2283, "OSC 6 Waveguide Excite", 0, 1, 0.6, "", "sld", null, 1, "Excite", null],
    [2284, "OSC 6 Waveguide Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2285, "OSC 6 Waveguide Noise", 0, 1, 0.2, "", "sld", null, 1, "Noise", null],
    [2286, "OSC 6 Waveguide Nonlinear", 0, 1, 0.0, "", "sld", null, 1, "Nonlinear", null],
    [2287, "OSC 6 Waveguide Stretch", 0, 1, 0.0, "", "sld", null, 1, "Stretch", null],
    [2288, "OSC 6 Waveguide Attack", 0, 1, 0.2, "", "sld", null, 1, "Attack", null],
    [2289, "OSC 6 Waveguide Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2290, "OSC 6 Waveguide Body", 0, 1, 0.0, "", "sld", null, 1, "Body", null],
    [2291, "OSC 6 Waveguide Body Tune", 0, 1, 0.4, "", "sld", null, 1, "Body Tune", null],
    [2292, "OSC 6 Waveguide Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Excite", null],
    [2293, "OSC 6 Waveguide Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2294, "OSC 6 Waveguide Tension", 0, 1, 0.0, "", "sld", null, 1, "Tension", null],
    [2295, "OSC 6 Waveguide Key Decay", 0, 1, 0.3, "", "sld", null, 1, "Key Decay", null],
    [2300, "OSC 1 JP Waveform", 0, 8, 6, "", "sel", JP_WAVES, 1, "Waveform", null],
    [2301, "OSC 1 JP Pulse Width", 0.05, 0.95, 0.5, "", "sld", null, 1, "Pulse Width", null],
    [2302, "OSC 1 JP PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [2303, "OSC 1 JP PWM Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "PWM Rate", null],
    [2304, "OSC 1 JP Super Saw Detune", 0, 1, 0.4, "", "sld", null, 1, "Detune", null],
    [2305, "OSC 1 JP Super Saw Mix", 0, 1, 0.7, "", "sld", null, 1, "Mix", null],
    [2306, "OSC 1 JP Stereo Width", 0, 1, 0.7, "", "sld", null, 1, "Width", null],
    [2307, "OSC 1 JP Feedback", 0, 1, 0.5, "", "sld", null, 1, "Feedback", null],
    [2308, "OSC 1 JP Feedback Color", 0, 1, 0.3, "", "sld", null, 1, "Color", null],
    [2309, "OSC 1 JP Tri Mod Depth", 0, 1, 0.5, "", "sld", null, 1, "Mod Depth", null],
    [2310, "OSC 1 JP Tri Mod Ratio", 0, 1, 0.2, "", "sld", null, 1, "Mod Ratio", null],
    [2311, "OSC 1 JP Spectrum Tilt", 0, 1, 0.5, "", "sld", null, 1, "Tilt", null],
    [2312, "OSC 1 JP Spectrum Peak", 0, 1, 0.3, "", "sld", null, 1, "Peak", null],
    [2313, "OSC 1 JP Noise Mix", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [2314, "OSC 1 JP Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2315, "OSC 1 JP Sub Oscillator", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [2316, "OSC 2 JP Waveform", 0, 8, 6, "", "sel", JP_WAVES, 1, "Waveform", null],
    [2317, "OSC 2 JP Pulse Width", 0.05, 0.95, 0.5, "", "sld", null, 1, "Pulse Width", null],
    [2318, "OSC 2 JP PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [2319, "OSC 2 JP PWM Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "PWM Rate", null],
    [2320, "OSC 2 JP Super Saw Detune", 0, 1, 0.4, "", "sld", null, 1, "Detune", null],
    [2321, "OSC 2 JP Super Saw Mix", 0, 1, 0.7, "", "sld", null, 1, "Mix", null],
    [2322, "OSC 2 JP Stereo Width", 0, 1, 0.7, "", "sld", null, 1, "Width", null],
    [2323, "OSC 2 JP Feedback", 0, 1, 0.5, "", "sld", null, 1, "Feedback", null],
    [2324, "OSC 2 JP Feedback Color", 0, 1, 0.3, "", "sld", null, 1, "Color", null],
    [2325, "OSC 2 JP Tri Mod Depth", 0, 1, 0.5, "", "sld", null, 1, "Mod Depth", null],
    [2326, "OSC 2 JP Tri Mod Ratio", 0, 1, 0.2, "", "sld", null, 1, "Mod Ratio", null],
    [2327, "OSC 2 JP Spectrum Tilt", 0, 1, 0.5, "", "sld", null, 1, "Tilt", null],
    [2328, "OSC 2 JP Spectrum Peak", 0, 1, 0.3, "", "sld", null, 1, "Peak", null],
    [2329, "OSC 2 JP Noise Mix", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [2330, "OSC 2 JP Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2331, "OSC 2 JP Sub Oscillator", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [2332, "OSC 3 JP Waveform", 0, 8, 6, "", "sel", JP_WAVES, 1, "Waveform", null],
    [2333, "OSC 3 JP Pulse Width", 0.05, 0.95, 0.5, "", "sld", null, 1, "Pulse Width", null],
    [2334, "OSC 3 JP PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [2335, "OSC 3 JP PWM Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "PWM Rate", null],
    [2336, "OSC 3 JP Super Saw Detune", 0, 1, 0.4, "", "sld", null, 1, "Detune", null],
    [2337, "OSC 3 JP Super Saw Mix", 0, 1, 0.7, "", "sld", null, 1, "Mix", null],
    [2338, "OSC 3 JP Stereo Width", 0, 1, 0.7, "", "sld", null, 1, "Width", null],
    [2339, "OSC 3 JP Feedback", 0, 1, 0.5, "", "sld", null, 1, "Feedback", null],
    [2340, "OSC 3 JP Feedback Color", 0, 1, 0.3, "", "sld", null, 1, "Color", null],
    [2341, "OSC 3 JP Tri Mod Depth", 0, 1, 0.5, "", "sld", null, 1, "Mod Depth", null],
    [2342, "OSC 3 JP Tri Mod Ratio", 0, 1, 0.2, "", "sld", null, 1, "Mod Ratio", null],
    [2343, "OSC 3 JP Spectrum Tilt", 0, 1, 0.5, "", "sld", null, 1, "Tilt", null],
    [2344, "OSC 3 JP Spectrum Peak", 0, 1, 0.3, "", "sld", null, 1, "Peak", null],
    [2345, "OSC 3 JP Noise Mix", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [2346, "OSC 3 JP Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2347, "OSC 3 JP Sub Oscillator", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [2348, "OSC 4 JP Waveform", 0, 8, 6, "", "sel", JP_WAVES, 1, "Waveform", null],
    [2349, "OSC 4 JP Pulse Width", 0.05, 0.95, 0.5, "", "sld", null, 1, "Pulse Width", null],
    [2350, "OSC 4 JP PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [2351, "OSC 4 JP PWM Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "PWM Rate", null],
    [2352, "OSC 4 JP Super Saw Detune", 0, 1, 0.4, "", "sld", null, 1, "Detune", null],
    [2353, "OSC 4 JP Super Saw Mix", 0, 1, 0.7, "", "sld", null, 1, "Mix", null],
    [2354, "OSC 4 JP Stereo Width", 0, 1, 0.7, "", "sld", null, 1, "Width", null],
    [2355, "OSC 4 JP Feedback", 0, 1, 0.5, "", "sld", null, 1, "Feedback", null],
    [2356, "OSC 4 JP Feedback Color", 0, 1, 0.3, "", "sld", null, 1, "Color", null],
    [2357, "OSC 4 JP Tri Mod Depth", 0, 1, 0.5, "", "sld", null, 1, "Mod Depth", null],
    [2358, "OSC 4 JP Tri Mod Ratio", 0, 1, 0.2, "", "sld", null, 1, "Mod Ratio", null],
    [2359, "OSC 4 JP Spectrum Tilt", 0, 1, 0.5, "", "sld", null, 1, "Tilt", null],
    [2360, "OSC 4 JP Spectrum Peak", 0, 1, 0.3, "", "sld", null, 1, "Peak", null],
    [2361, "OSC 4 JP Noise Mix", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [2362, "OSC 4 JP Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2363, "OSC 4 JP Sub Oscillator", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [2364, "OSC 5 JP Waveform", 0, 8, 6, "", "sel", JP_WAVES, 1, "Waveform", null],
    [2365, "OSC 5 JP Pulse Width", 0.05, 0.95, 0.5, "", "sld", null, 1, "Pulse Width", null],
    [2366, "OSC 5 JP PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [2367, "OSC 5 JP PWM Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "PWM Rate", null],
    [2368, "OSC 5 JP Super Saw Detune", 0, 1, 0.4, "", "sld", null, 1, "Detune", null],
    [2369, "OSC 5 JP Super Saw Mix", 0, 1, 0.7, "", "sld", null, 1, "Mix", null],
    [2370, "OSC 5 JP Stereo Width", 0, 1, 0.7, "", "sld", null, 1, "Width", null],
    [2371, "OSC 5 JP Feedback", 0, 1, 0.5, "", "sld", null, 1, "Feedback", null],
    [2372, "OSC 5 JP Feedback Color", 0, 1, 0.3, "", "sld", null, 1, "Color", null],
    [2373, "OSC 5 JP Tri Mod Depth", 0, 1, 0.5, "", "sld", null, 1, "Mod Depth", null],
    [2374, "OSC 5 JP Tri Mod Ratio", 0, 1, 0.2, "", "sld", null, 1, "Mod Ratio", null],
    [2375, "OSC 5 JP Spectrum Tilt", 0, 1, 0.5, "", "sld", null, 1, "Tilt", null],
    [2376, "OSC 5 JP Spectrum Peak", 0, 1, 0.3, "", "sld", null, 1, "Peak", null],
    [2377, "OSC 5 JP Noise Mix", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [2378, "OSC 5 JP Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2379, "OSC 5 JP Sub Oscillator", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [2380, "OSC 6 JP Waveform", 0, 8, 6, "", "sel", JP_WAVES, 1, "Waveform", null],
    [2381, "OSC 6 JP Pulse Width", 0.05, 0.95, 0.5, "", "sld", null, 1, "Pulse Width", null],
    [2382, "OSC 6 JP PWM Depth", 0, 1, 0.0, "", "sld", null, 1, "PWM Depth", null],
    [2383, "OSC 6 JP PWM Rate", 0.05, 20, 1.0, "Hz", "sld", null, 1, "PWM Rate", null],
    [2384, "OSC 6 JP Super Saw Detune", 0, 1, 0.4, "", "sld", null, 1, "Detune", null],
    [2385, "OSC 6 JP Super Saw Mix", 0, 1, 0.7, "", "sld", null, 1, "Mix", null],
    [2386, "OSC 6 JP Stereo Width", 0, 1, 0.7, "", "sld", null, 1, "Width", null],
    [2387, "OSC 6 JP Feedback", 0, 1, 0.5, "", "sld", null, 1, "Feedback", null],
    [2388, "OSC 6 JP Feedback Color", 0, 1, 0.3, "", "sld", null, 1, "Color", null],
    [2389, "OSC 6 JP Tri Mod Depth", 0, 1, 0.5, "", "sld", null, 1, "Mod Depth", null],
    [2390, "OSC 6 JP Tri Mod Ratio", 0, 1, 0.2, "", "sld", null, 1, "Mod Ratio", null],
    [2391, "OSC 6 JP Spectrum Tilt", 0, 1, 0.5, "", "sld", null, 1, "Tilt", null],
    [2392, "OSC 6 JP Spectrum Peak", 0, 1, 0.3, "", "sld", null, 1, "Peak", null],
    [2393, "OSC 6 JP Noise Mix", 0, 1, 0.0, "", "sld", null, 1, "Noise", null],
    [2394, "OSC 6 JP Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2395, "OSC 6 JP Sub Oscillator", 0, 1, 0.0, "", "sld", null, 1, "Sub", null],
    [2400, "OSC 1 Granular Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2401, "OSC 1 Granular Grain Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2402, "OSC 1 Granular Density", 0, 1, 0.5, "", "sld", null, 1, "Density", null],
    [2403, "OSC 1 Granular Spray", 0, 1, 0.1, "", "sld", null, 1, "Spray", null],
    [2404, "OSC 1 Granular Pitch Spread", 0, 1, 0.0, "", "sld", null, 1, "Pitch Spread", null],
    [2405, "OSC 1 Granular Pan Spread", 0, 1, 0.5, "", "sld", null, 1, "Pan Spread", null],
    [2406, "OSC 1 Granular Window", 0, 1, 0.0, "", "sld", null, 1, "Window", null],
    [2407, "OSC 1 Granular Reverse", 0, 1, 0.0, "", "sld", null, 1, "Reverse", null],
    [2408, "OSC 1 Granular Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2409, "OSC 1 Granular Timing", 0, 1, 0.3, "", "sld", null, 1, "Timing Jitter", null],
    [2410, "OSC 1 Granular Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2411, "OSC 1 Granular Velocity", -1, 1, 0.0, "", "sld", null, 1, "Vel > Position", null],
    [2416, "OSC 2 Granular Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2417, "OSC 2 Granular Grain Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2418, "OSC 2 Granular Density", 0, 1, 0.5, "", "sld", null, 1, "Density", null],
    [2419, "OSC 2 Granular Spray", 0, 1, 0.1, "", "sld", null, 1, "Spray", null],
    [2420, "OSC 2 Granular Pitch Spread", 0, 1, 0.0, "", "sld", null, 1, "Pitch Spread", null],
    [2421, "OSC 2 Granular Pan Spread", 0, 1, 0.5, "", "sld", null, 1, "Pan Spread", null],
    [2422, "OSC 2 Granular Window", 0, 1, 0.0, "", "sld", null, 1, "Window", null],
    [2423, "OSC 2 Granular Reverse", 0, 1, 0.0, "", "sld", null, 1, "Reverse", null],
    [2424, "OSC 2 Granular Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2425, "OSC 2 Granular Timing", 0, 1, 0.3, "", "sld", null, 1, "Timing Jitter", null],
    [2426, "OSC 2 Granular Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2427, "OSC 2 Granular Velocity", -1, 1, 0.0, "", "sld", null, 1, "Vel > Position", null],
    [2432, "OSC 3 Granular Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2433, "OSC 3 Granular Grain Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2434, "OSC 3 Granular Density", 0, 1, 0.5, "", "sld", null, 1, "Density", null],
    [2435, "OSC 3 Granular Spray", 0, 1, 0.1, "", "sld", null, 1, "Spray", null],
    [2436, "OSC 3 Granular Pitch Spread", 0, 1, 0.0, "", "sld", null, 1, "Pitch Spread", null],
    [2437, "OSC 3 Granular Pan Spread", 0, 1, 0.5, "", "sld", null, 1, "Pan Spread", null],
    [2438, "OSC 3 Granular Window", 0, 1, 0.0, "", "sld", null, 1, "Window", null],
    [2439, "OSC 3 Granular Reverse", 0, 1, 0.0, "", "sld", null, 1, "Reverse", null],
    [2440, "OSC 3 Granular Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2441, "OSC 3 Granular Timing", 0, 1, 0.3, "", "sld", null, 1, "Timing Jitter", null],
    [2442, "OSC 3 Granular Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2443, "OSC 3 Granular Velocity", -1, 1, 0.0, "", "sld", null, 1, "Vel > Position", null],
    [2448, "OSC 4 Granular Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2449, "OSC 4 Granular Grain Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2450, "OSC 4 Granular Density", 0, 1, 0.5, "", "sld", null, 1, "Density", null],
    [2451, "OSC 4 Granular Spray", 0, 1, 0.1, "", "sld", null, 1, "Spray", null],
    [2452, "OSC 4 Granular Pitch Spread", 0, 1, 0.0, "", "sld", null, 1, "Pitch Spread", null],
    [2453, "OSC 4 Granular Pan Spread", 0, 1, 0.5, "", "sld", null, 1, "Pan Spread", null],
    [2454, "OSC 4 Granular Window", 0, 1, 0.0, "", "sld", null, 1, "Window", null],
    [2455, "OSC 4 Granular Reverse", 0, 1, 0.0, "", "sld", null, 1, "Reverse", null],
    [2456, "OSC 4 Granular Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2457, "OSC 4 Granular Timing", 0, 1, 0.3, "", "sld", null, 1, "Timing Jitter", null],
    [2458, "OSC 4 Granular Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2459, "OSC 4 Granular Velocity", -1, 1, 0.0, "", "sld", null, 1, "Vel > Position", null],
    [2464, "OSC 5 Granular Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2465, "OSC 5 Granular Grain Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2466, "OSC 5 Granular Density", 0, 1, 0.5, "", "sld", null, 1, "Density", null],
    [2467, "OSC 5 Granular Spray", 0, 1, 0.1, "", "sld", null, 1, "Spray", null],
    [2468, "OSC 5 Granular Pitch Spread", 0, 1, 0.0, "", "sld", null, 1, "Pitch Spread", null],
    [2469, "OSC 5 Granular Pan Spread", 0, 1, 0.5, "", "sld", null, 1, "Pan Spread", null],
    [2470, "OSC 5 Granular Window", 0, 1, 0.0, "", "sld", null, 1, "Window", null],
    [2471, "OSC 5 Granular Reverse", 0, 1, 0.0, "", "sld", null, 1, "Reverse", null],
    [2472, "OSC 5 Granular Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2473, "OSC 5 Granular Timing", 0, 1, 0.3, "", "sld", null, 1, "Timing Jitter", null],
    [2474, "OSC 5 Granular Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2475, "OSC 5 Granular Velocity", -1, 1, 0.0, "", "sld", null, 1, "Vel > Position", null],
    [2480, "OSC 6 Granular Position", 0, 1, 0.3, "", "sld", null, 1, "Position", null],
    [2481, "OSC 6 Granular Grain Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2482, "OSC 6 Granular Density", 0, 1, 0.5, "", "sld", null, 1, "Density", null],
    [2483, "OSC 6 Granular Spray", 0, 1, 0.1, "", "sld", null, 1, "Spray", null],
    [2484, "OSC 6 Granular Pitch Spread", 0, 1, 0.0, "", "sld", null, 1, "Pitch Spread", null],
    [2485, "OSC 6 Granular Pan Spread", 0, 1, 0.5, "", "sld", null, 1, "Pan Spread", null],
    [2486, "OSC 6 Granular Window", 0, 1, 0.0, "", "sld", null, 1, "Window", null],
    [2487, "OSC 6 Granular Reverse", 0, 1, 0.0, "", "sld", null, 1, "Reverse", null],
    [2488, "OSC 6 Granular Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2489, "OSC 6 Granular Timing", 0, 1, 0.3, "", "sld", null, 1, "Timing Jitter", null],
    [2490, "OSC 6 Granular Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2491, "OSC 6 Granular Velocity", -1, 1, 0.0, "", "sld", null, 1, "Vel > Position", null],
    [2500, "OSC 1 Additive Spectrum A", 0, 7, 0, "", "sel", AD_SHAPES, 1, "Spectrum A", null],
    [2501, "OSC 1 Additive Spectrum B", 0, 7, 3, "", "sel", AD_SHAPES, 1, "Spectrum B", null],
    [2502, "OSC 1 Additive Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2503, "OSC 1 Additive Partials", 1, 64, 32, "", "sld", null, 1, "Partials", null],
    [2504, "OSC 1 Additive Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2505, "OSC 1 Additive Odd / Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2506, "OSC 1 Additive Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [2507, "OSC 1 Additive Formant", 0, 1, 0.4, "", "sld", null, 1, "Formant", null],
    [2508, "OSC 1 Additive Formant Gain", 0, 1, 0.0, "", "sld", null, 1, "Form. Gain", null],
    [2509, "OSC 1 Additive Shimmer", 0, 1, 0.0, "", "sld", null, 1, "Shimmer", null],
    [2510, "OSC 1 Additive Shimmer Rate", 0.1, 20, 2.0, "Hz", "sld", null, 1, "Shim. Rate", null],
    [2511, "OSC 1 Additive Partial Decay", 0, 1, 0.0, "", "sld", null, 1, "Partial Decay", null],
    [2512, "OSC 1 Additive Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2513, "OSC 1 Additive Stereo Spread", 0, 1, 0.3, "", "sld", null, 1, "Width", null],
    [2514, "OSC 1 Additive Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Bright", null],
    [2516, "OSC 2 Additive Spectrum A", 0, 7, 0, "", "sel", AD_SHAPES, 1, "Spectrum A", null],
    [2517, "OSC 2 Additive Spectrum B", 0, 7, 3, "", "sel", AD_SHAPES, 1, "Spectrum B", null],
    [2518, "OSC 2 Additive Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2519, "OSC 2 Additive Partials", 1, 64, 32, "", "sld", null, 1, "Partials", null],
    [2520, "OSC 2 Additive Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2521, "OSC 2 Additive Odd / Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2522, "OSC 2 Additive Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [2523, "OSC 2 Additive Formant", 0, 1, 0.4, "", "sld", null, 1, "Formant", null],
    [2524, "OSC 2 Additive Formant Gain", 0, 1, 0.0, "", "sld", null, 1, "Form. Gain", null],
    [2525, "OSC 2 Additive Shimmer", 0, 1, 0.0, "", "sld", null, 1, "Shimmer", null],
    [2526, "OSC 2 Additive Shimmer Rate", 0.1, 20, 2.0, "Hz", "sld", null, 1, "Shim. Rate", null],
    [2527, "OSC 2 Additive Partial Decay", 0, 1, 0.0, "", "sld", null, 1, "Partial Decay", null],
    [2528, "OSC 2 Additive Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2529, "OSC 2 Additive Stereo Spread", 0, 1, 0.3, "", "sld", null, 1, "Width", null],
    [2530, "OSC 2 Additive Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Bright", null],
    [2532, "OSC 3 Additive Spectrum A", 0, 7, 0, "", "sel", AD_SHAPES, 1, "Spectrum A", null],
    [2533, "OSC 3 Additive Spectrum B", 0, 7, 3, "", "sel", AD_SHAPES, 1, "Spectrum B", null],
    [2534, "OSC 3 Additive Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2535, "OSC 3 Additive Partials", 1, 64, 32, "", "sld", null, 1, "Partials", null],
    [2536, "OSC 3 Additive Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2537, "OSC 3 Additive Odd / Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2538, "OSC 3 Additive Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [2539, "OSC 3 Additive Formant", 0, 1, 0.4, "", "sld", null, 1, "Formant", null],
    [2540, "OSC 3 Additive Formant Gain", 0, 1, 0.0, "", "sld", null, 1, "Form. Gain", null],
    [2541, "OSC 3 Additive Shimmer", 0, 1, 0.0, "", "sld", null, 1, "Shimmer", null],
    [2542, "OSC 3 Additive Shimmer Rate", 0.1, 20, 2.0, "Hz", "sld", null, 1, "Shim. Rate", null],
    [2543, "OSC 3 Additive Partial Decay", 0, 1, 0.0, "", "sld", null, 1, "Partial Decay", null],
    [2544, "OSC 3 Additive Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2545, "OSC 3 Additive Stereo Spread", 0, 1, 0.3, "", "sld", null, 1, "Width", null],
    [2546, "OSC 3 Additive Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Bright", null],
    [2548, "OSC 4 Additive Spectrum A", 0, 7, 0, "", "sel", AD_SHAPES, 1, "Spectrum A", null],
    [2549, "OSC 4 Additive Spectrum B", 0, 7, 3, "", "sel", AD_SHAPES, 1, "Spectrum B", null],
    [2550, "OSC 4 Additive Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2551, "OSC 4 Additive Partials", 1, 64, 32, "", "sld", null, 1, "Partials", null],
    [2552, "OSC 4 Additive Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2553, "OSC 4 Additive Odd / Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2554, "OSC 4 Additive Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [2555, "OSC 4 Additive Formant", 0, 1, 0.4, "", "sld", null, 1, "Formant", null],
    [2556, "OSC 4 Additive Formant Gain", 0, 1, 0.0, "", "sld", null, 1, "Form. Gain", null],
    [2557, "OSC 4 Additive Shimmer", 0, 1, 0.0, "", "sld", null, 1, "Shimmer", null],
    [2558, "OSC 4 Additive Shimmer Rate", 0.1, 20, 2.0, "Hz", "sld", null, 1, "Shim. Rate", null],
    [2559, "OSC 4 Additive Partial Decay", 0, 1, 0.0, "", "sld", null, 1, "Partial Decay", null],
    [2560, "OSC 4 Additive Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2561, "OSC 4 Additive Stereo Spread", 0, 1, 0.3, "", "sld", null, 1, "Width", null],
    [2562, "OSC 4 Additive Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Bright", null],
    [2564, "OSC 5 Additive Spectrum A", 0, 7, 0, "", "sel", AD_SHAPES, 1, "Spectrum A", null],
    [2565, "OSC 5 Additive Spectrum B", 0, 7, 3, "", "sel", AD_SHAPES, 1, "Spectrum B", null],
    [2566, "OSC 5 Additive Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2567, "OSC 5 Additive Partials", 1, 64, 32, "", "sld", null, 1, "Partials", null],
    [2568, "OSC 5 Additive Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2569, "OSC 5 Additive Odd / Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2570, "OSC 5 Additive Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [2571, "OSC 5 Additive Formant", 0, 1, 0.4, "", "sld", null, 1, "Formant", null],
    [2572, "OSC 5 Additive Formant Gain", 0, 1, 0.0, "", "sld", null, 1, "Form. Gain", null],
    [2573, "OSC 5 Additive Shimmer", 0, 1, 0.0, "", "sld", null, 1, "Shimmer", null],
    [2574, "OSC 5 Additive Shimmer Rate", 0.1, 20, 2.0, "Hz", "sld", null, 1, "Shim. Rate", null],
    [2575, "OSC 5 Additive Partial Decay", 0, 1, 0.0, "", "sld", null, 1, "Partial Decay", null],
    [2576, "OSC 5 Additive Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2577, "OSC 5 Additive Stereo Spread", 0, 1, 0.3, "", "sld", null, 1, "Width", null],
    [2578, "OSC 5 Additive Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Bright", null],
    [2580, "OSC 6 Additive Spectrum A", 0, 7, 0, "", "sel", AD_SHAPES, 1, "Spectrum A", null],
    [2581, "OSC 6 Additive Spectrum B", 0, 7, 3, "", "sel", AD_SHAPES, 1, "Spectrum B", null],
    [2582, "OSC 6 Additive Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2583, "OSC 6 Additive Partials", 1, 64, 32, "", "sld", null, 1, "Partials", null],
    [2584, "OSC 6 Additive Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2585, "OSC 6 Additive Odd / Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2586, "OSC 6 Additive Inharmonicity", 0, 1, 0.0, "", "sld", null, 1, "Inharm", null],
    [2587, "OSC 6 Additive Formant", 0, 1, 0.4, "", "sld", null, 1, "Formant", null],
    [2588, "OSC 6 Additive Formant Gain", 0, 1, 0.0, "", "sld", null, 1, "Form. Gain", null],
    [2589, "OSC 6 Additive Shimmer", 0, 1, 0.0, "", "sld", null, 1, "Shimmer", null],
    [2590, "OSC 6 Additive Shimmer Rate", 0.1, 20, 2.0, "Hz", "sld", null, 1, "Shim. Rate", null],
    [2591, "OSC 6 Additive Partial Decay", 0, 1, 0.0, "", "sld", null, 1, "Partial Decay", null],
    [2592, "OSC 6 Additive Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2593, "OSC 6 Additive Stereo Spread", 0, 1, 0.3, "", "sld", null, 1, "Width", null],
    [2594, "OSC 6 Additive Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Bright", null],
    [2600, "OSC 1 Drum Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2601, "OSC 1 Drum Head Tone", 0, 1, 0.6, "", "sld", null, 1, "Head Tone", null],
    [2602, "OSC 1 Drum Hit Position", 0, 1, 0.25, "", "sld", null, 1, "Hit Position", null],
    [2603, "OSC 1 Drum Stick", 0, 1, 0.5, "", "sld", null, 1, "Stick", null],
    [2604, "OSC 1 Drum Edge", 0, 1, 0.3, "", "sld", null, 1, "Edge", null],
    [2605, "OSC 1 Drum Reso Head", 0, 1, 0.6, "", "sld", null, 1, "Reso Head", null],
    [2606, "OSC 1 Drum Reso Tune", -1, 1, 0.0, "", "sld", null, 1, "Reso Tune", null],
    [2607, "OSC 1 Drum Shell", 0, 1, 0.4, "", "sld", null, 1, "Shell", null],
    [2608, "OSC 1 Drum Shell Depth", 0, 1, 0.5, "", "sld", null, 1, "Shell Depth", null],
    [2609, "OSC 1 Drum Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2610, "OSC 1 Drum Snare Tension", 0, 1, 0.5, "", "sld", null, 1, "Snare Tension", null],
    [2611, "OSC 1 Drum Sympathetic", 0, 1, 0.0, "", "sld", null, 1, "Sympathetic", null],
    [2612, "OSC 1 Drum Tension", 0, 1, 0.3, "", "sld", null, 1, "Tension", null],
    [2613, "OSC 1 Drum Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Stick", null],
    [2614, "OSC 1 Drum Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2615, "OSC 1 Drum Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2616, "OSC 2 Drum Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2617, "OSC 2 Drum Head Tone", 0, 1, 0.6, "", "sld", null, 1, "Head Tone", null],
    [2618, "OSC 2 Drum Hit Position", 0, 1, 0.25, "", "sld", null, 1, "Hit Position", null],
    [2619, "OSC 2 Drum Stick", 0, 1, 0.5, "", "sld", null, 1, "Stick", null],
    [2620, "OSC 2 Drum Edge", 0, 1, 0.3, "", "sld", null, 1, "Edge", null],
    [2621, "OSC 2 Drum Reso Head", 0, 1, 0.6, "", "sld", null, 1, "Reso Head", null],
    [2622, "OSC 2 Drum Reso Tune", -1, 1, 0.0, "", "sld", null, 1, "Reso Tune", null],
    [2623, "OSC 2 Drum Shell", 0, 1, 0.4, "", "sld", null, 1, "Shell", null],
    [2624, "OSC 2 Drum Shell Depth", 0, 1, 0.5, "", "sld", null, 1, "Shell Depth", null],
    [2625, "OSC 2 Drum Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2626, "OSC 2 Drum Snare Tension", 0, 1, 0.5, "", "sld", null, 1, "Snare Tension", null],
    [2627, "OSC 2 Drum Sympathetic", 0, 1, 0.0, "", "sld", null, 1, "Sympathetic", null],
    [2628, "OSC 2 Drum Tension", 0, 1, 0.3, "", "sld", null, 1, "Tension", null],
    [2629, "OSC 2 Drum Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Stick", null],
    [2630, "OSC 2 Drum Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2631, "OSC 2 Drum Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2632, "OSC 3 Drum Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2633, "OSC 3 Drum Head Tone", 0, 1, 0.6, "", "sld", null, 1, "Head Tone", null],
    [2634, "OSC 3 Drum Hit Position", 0, 1, 0.25, "", "sld", null, 1, "Hit Position", null],
    [2635, "OSC 3 Drum Stick", 0, 1, 0.5, "", "sld", null, 1, "Stick", null],
    [2636, "OSC 3 Drum Edge", 0, 1, 0.3, "", "sld", null, 1, "Edge", null],
    [2637, "OSC 3 Drum Reso Head", 0, 1, 0.6, "", "sld", null, 1, "Reso Head", null],
    [2638, "OSC 3 Drum Reso Tune", -1, 1, 0.0, "", "sld", null, 1, "Reso Tune", null],
    [2639, "OSC 3 Drum Shell", 0, 1, 0.4, "", "sld", null, 1, "Shell", null],
    [2640, "OSC 3 Drum Shell Depth", 0, 1, 0.5, "", "sld", null, 1, "Shell Depth", null],
    [2641, "OSC 3 Drum Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2642, "OSC 3 Drum Snare Tension", 0, 1, 0.5, "", "sld", null, 1, "Snare Tension", null],
    [2643, "OSC 3 Drum Sympathetic", 0, 1, 0.0, "", "sld", null, 1, "Sympathetic", null],
    [2644, "OSC 3 Drum Tension", 0, 1, 0.3, "", "sld", null, 1, "Tension", null],
    [2645, "OSC 3 Drum Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Stick", null],
    [2646, "OSC 3 Drum Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2647, "OSC 3 Drum Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2648, "OSC 4 Drum Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2649, "OSC 4 Drum Head Tone", 0, 1, 0.6, "", "sld", null, 1, "Head Tone", null],
    [2650, "OSC 4 Drum Hit Position", 0, 1, 0.25, "", "sld", null, 1, "Hit Position", null],
    [2651, "OSC 4 Drum Stick", 0, 1, 0.5, "", "sld", null, 1, "Stick", null],
    [2652, "OSC 4 Drum Edge", 0, 1, 0.3, "", "sld", null, 1, "Edge", null],
    [2653, "OSC 4 Drum Reso Head", 0, 1, 0.6, "", "sld", null, 1, "Reso Head", null],
    [2654, "OSC 4 Drum Reso Tune", -1, 1, 0.0, "", "sld", null, 1, "Reso Tune", null],
    [2655, "OSC 4 Drum Shell", 0, 1, 0.4, "", "sld", null, 1, "Shell", null],
    [2656, "OSC 4 Drum Shell Depth", 0, 1, 0.5, "", "sld", null, 1, "Shell Depth", null],
    [2657, "OSC 4 Drum Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2658, "OSC 4 Drum Snare Tension", 0, 1, 0.5, "", "sld", null, 1, "Snare Tension", null],
    [2659, "OSC 4 Drum Sympathetic", 0, 1, 0.0, "", "sld", null, 1, "Sympathetic", null],
    [2660, "OSC 4 Drum Tension", 0, 1, 0.3, "", "sld", null, 1, "Tension", null],
    [2661, "OSC 4 Drum Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Stick", null],
    [2662, "OSC 4 Drum Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2663, "OSC 4 Drum Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2664, "OSC 5 Drum Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2665, "OSC 5 Drum Head Tone", 0, 1, 0.6, "", "sld", null, 1, "Head Tone", null],
    [2666, "OSC 5 Drum Hit Position", 0, 1, 0.25, "", "sld", null, 1, "Hit Position", null],
    [2667, "OSC 5 Drum Stick", 0, 1, 0.5, "", "sld", null, 1, "Stick", null],
    [2668, "OSC 5 Drum Edge", 0, 1, 0.3, "", "sld", null, 1, "Edge", null],
    [2669, "OSC 5 Drum Reso Head", 0, 1, 0.6, "", "sld", null, 1, "Reso Head", null],
    [2670, "OSC 5 Drum Reso Tune", -1, 1, 0.0, "", "sld", null, 1, "Reso Tune", null],
    [2671, "OSC 5 Drum Shell", 0, 1, 0.4, "", "sld", null, 1, "Shell", null],
    [2672, "OSC 5 Drum Shell Depth", 0, 1, 0.5, "", "sld", null, 1, "Shell Depth", null],
    [2673, "OSC 5 Drum Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2674, "OSC 5 Drum Snare Tension", 0, 1, 0.5, "", "sld", null, 1, "Snare Tension", null],
    [2675, "OSC 5 Drum Sympathetic", 0, 1, 0.0, "", "sld", null, 1, "Sympathetic", null],
    [2676, "OSC 5 Drum Tension", 0, 1, 0.3, "", "sld", null, 1, "Tension", null],
    [2677, "OSC 5 Drum Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Stick", null],
    [2678, "OSC 5 Drum Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2679, "OSC 5 Drum Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2680, "OSC 6 Drum Decay", 0, 1, 0.5, "", "sld", null, 1, "Decay", null],
    [2681, "OSC 6 Drum Head Tone", 0, 1, 0.6, "", "sld", null, 1, "Head Tone", null],
    [2682, "OSC 6 Drum Hit Position", 0, 1, 0.25, "", "sld", null, 1, "Hit Position", null],
    [2683, "OSC 6 Drum Stick", 0, 1, 0.5, "", "sld", null, 1, "Stick", null],
    [2684, "OSC 6 Drum Edge", 0, 1, 0.3, "", "sld", null, 1, "Edge", null],
    [2685, "OSC 6 Drum Reso Head", 0, 1, 0.6, "", "sld", null, 1, "Reso Head", null],
    [2686, "OSC 6 Drum Reso Tune", -1, 1, 0.0, "", "sld", null, 1, "Reso Tune", null],
    [2687, "OSC 6 Drum Shell", 0, 1, 0.4, "", "sld", null, 1, "Shell", null],
    [2688, "OSC 6 Drum Shell Depth", 0, 1, 0.5, "", "sld", null, 1, "Shell Depth", null],
    [2689, "OSC 6 Drum Snare", 0, 1, 0.0, "", "sld", null, 1, "Snare", null],
    [2690, "OSC 6 Drum Snare Tension", 0, 1, 0.5, "", "sld", null, 1, "Snare Tension", null],
    [2691, "OSC 6 Drum Sympathetic", 0, 1, 0.0, "", "sld", null, 1, "Sympathetic", null],
    [2692, "OSC 6 Drum Tension", 0, 1, 0.3, "", "sld", null, 1, "Tension", null],
    [2693, "OSC 6 Drum Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel > Stick", null],
    [2694, "OSC 6 Drum Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2695, "OSC 6 Drum Size", 0, 1, 0.5, "", "sld", null, 1, "Size", null],
    [2700, "OSC 1 Spectral Mode", 0, 1, 0, "", "btn", ["Resynth", "Spectrum"], 1, "Mode", null],
    [2701, "OSC 1 Spectral Position", 0, 1, 0.0, "", "sld", null, 1, "Position", null],
    [2702, "OSC 1 Spectral Position B", 0, 1, 0.5, "", "sld", null, 1, "Position B", null],
    [2703, "OSC 1 Spectral Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2704, "OSC 1 Spectral Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2705, "OSC 1 Spectral Blur", 0, 1, 0.3, "", "sld", null, 1, "Blur", null],
    [2706, "OSC 1 Spectral Shift", -1, 1, 0.0, "", "sld", null, 1, "Shift", null],
    [2707, "OSC 1 Spectral Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2708, "OSC 1 Spectral Harmonics", 0, 1, 1.0, "", "sld", null, 1, "Harmonics", null],
    [2709, "OSC 1 Spectral Odd Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2710, "OSC 1 Spectral Comb", 0, 1, 0.0, "", "sld", null, 1, "Comb", null],
    [2711, "OSC 1 Spectral Contrast", 0, 1, 0.0, "", "sld", null, 1, "Contrast", null],
    [2712, "OSC 1 Spectral Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null],
    [2713, "OSC 1 Spectral Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null],
    [2714, "OSC 1 Spectral Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [2715, "OSC 1 Spectral Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel > Pos", null],
    [2716, "OSC 2 Spectral Mode", 0, 1, 0, "", "btn", ["Resynth", "Spectrum"], 1, "Mode", null],
    [2717, "OSC 2 Spectral Position", 0, 1, 0.0, "", "sld", null, 1, "Position", null],
    [2718, "OSC 2 Spectral Position B", 0, 1, 0.5, "", "sld", null, 1, "Position B", null],
    [2719, "OSC 2 Spectral Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2720, "OSC 2 Spectral Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2721, "OSC 2 Spectral Blur", 0, 1, 0.3, "", "sld", null, 1, "Blur", null],
    [2722, "OSC 2 Spectral Shift", -1, 1, 0.0, "", "sld", null, 1, "Shift", null],
    [2723, "OSC 2 Spectral Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2724, "OSC 2 Spectral Harmonics", 0, 1, 1.0, "", "sld", null, 1, "Harmonics", null],
    [2725, "OSC 2 Spectral Odd Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2726, "OSC 2 Spectral Comb", 0, 1, 0.0, "", "sld", null, 1, "Comb", null],
    [2727, "OSC 2 Spectral Contrast", 0, 1, 0.0, "", "sld", null, 1, "Contrast", null],
    [2728, "OSC 2 Spectral Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null],
    [2729, "OSC 2 Spectral Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null],
    [2730, "OSC 2 Spectral Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [2731, "OSC 2 Spectral Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel > Pos", null],
    [2732, "OSC 3 Spectral Mode", 0, 1, 0, "", "btn", ["Resynth", "Spectrum"], 1, "Mode", null],
    [2733, "OSC 3 Spectral Position", 0, 1, 0.0, "", "sld", null, 1, "Position", null],
    [2734, "OSC 3 Spectral Position B", 0, 1, 0.5, "", "sld", null, 1, "Position B", null],
    [2735, "OSC 3 Spectral Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2736, "OSC 3 Spectral Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2737, "OSC 3 Spectral Blur", 0, 1, 0.3, "", "sld", null, 1, "Blur", null],
    [2738, "OSC 3 Spectral Shift", -1, 1, 0.0, "", "sld", null, 1, "Shift", null],
    [2739, "OSC 3 Spectral Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2740, "OSC 3 Spectral Harmonics", 0, 1, 1.0, "", "sld", null, 1, "Harmonics", null],
    [2741, "OSC 3 Spectral Odd Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2742, "OSC 3 Spectral Comb", 0, 1, 0.0, "", "sld", null, 1, "Comb", null],
    [2743, "OSC 3 Spectral Contrast", 0, 1, 0.0, "", "sld", null, 1, "Contrast", null],
    [2744, "OSC 3 Spectral Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null],
    [2745, "OSC 3 Spectral Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null],
    [2746, "OSC 3 Spectral Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [2747, "OSC 3 Spectral Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel > Pos", null],
    [2748, "OSC 4 Spectral Mode", 0, 1, 0, "", "btn", ["Resynth", "Spectrum"], 1, "Mode", null],
    [2749, "OSC 4 Spectral Position", 0, 1, 0.0, "", "sld", null, 1, "Position", null],
    [2750, "OSC 4 Spectral Position B", 0, 1, 0.5, "", "sld", null, 1, "Position B", null],
    [2751, "OSC 4 Spectral Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2752, "OSC 4 Spectral Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2753, "OSC 4 Spectral Blur", 0, 1, 0.3, "", "sld", null, 1, "Blur", null],
    [2754, "OSC 4 Spectral Shift", -1, 1, 0.0, "", "sld", null, 1, "Shift", null],
    [2755, "OSC 4 Spectral Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2756, "OSC 4 Spectral Harmonics", 0, 1, 1.0, "", "sld", null, 1, "Harmonics", null],
    [2757, "OSC 4 Spectral Odd Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2758, "OSC 4 Spectral Comb", 0, 1, 0.0, "", "sld", null, 1, "Comb", null],
    [2759, "OSC 4 Spectral Contrast", 0, 1, 0.0, "", "sld", null, 1, "Contrast", null],
    [2760, "OSC 4 Spectral Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null],
    [2761, "OSC 4 Spectral Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null],
    [2762, "OSC 4 Spectral Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [2763, "OSC 4 Spectral Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel > Pos", null],
    [2764, "OSC 5 Spectral Mode", 0, 1, 0, "", "btn", ["Resynth", "Spectrum"], 1, "Mode", null],
    [2765, "OSC 5 Spectral Position", 0, 1, 0.0, "", "sld", null, 1, "Position", null],
    [2766, "OSC 5 Spectral Position B", 0, 1, 0.5, "", "sld", null, 1, "Position B", null],
    [2767, "OSC 5 Spectral Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2768, "OSC 5 Spectral Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2769, "OSC 5 Spectral Blur", 0, 1, 0.3, "", "sld", null, 1, "Blur", null],
    [2770, "OSC 5 Spectral Shift", -1, 1, 0.0, "", "sld", null, 1, "Shift", null],
    [2771, "OSC 5 Spectral Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2772, "OSC 5 Spectral Harmonics", 0, 1, 1.0, "", "sld", null, 1, "Harmonics", null],
    [2773, "OSC 5 Spectral Odd Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2774, "OSC 5 Spectral Comb", 0, 1, 0.0, "", "sld", null, 1, "Comb", null],
    [2775, "OSC 5 Spectral Contrast", 0, 1, 0.0, "", "sld", null, 1, "Contrast", null],
    [2776, "OSC 5 Spectral Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null],
    [2777, "OSC 5 Spectral Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null],
    [2778, "OSC 5 Spectral Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [2779, "OSC 5 Spectral Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel > Pos", null],
    [2780, "OSC 6 Spectral Mode", 0, 1, 0, "", "btn", ["Resynth", "Spectrum"], 1, "Mode", null],
    [2781, "OSC 6 Spectral Position", 0, 1, 0.0, "", "sld", null, 1, "Position", null],
    [2782, "OSC 6 Spectral Position B", 0, 1, 0.5, "", "sld", null, 1, "Position B", null],
    [2783, "OSC 6 Spectral Morph", 0, 1, 0.0, "", "sld", null, 1, "Morph", null],
    [2784, "OSC 6 Spectral Scan", -1, 1, 0.0, "", "sld", null, 1, "Scan", null],
    [2785, "OSC 6 Spectral Blur", 0, 1, 0.3, "", "sld", null, 1, "Blur", null],
    [2786, "OSC 6 Spectral Shift", -1, 1, 0.0, "", "sld", null, 1, "Shift", null],
    [2787, "OSC 6 Spectral Tilt", -1, 1, 0.0, "", "sld", null, 1, "Tilt", null],
    [2788, "OSC 6 Spectral Harmonics", 0, 1, 1.0, "", "sld", null, 1, "Harmonics", null],
    [2789, "OSC 6 Spectral Odd Even", -1, 1, 0.0, "", "sld", null, 1, "Odd / Even", null],
    [2790, "OSC 6 Spectral Comb", 0, 1, 0.0, "", "sld", null, 1, "Comb", null],
    [2791, "OSC 6 Spectral Contrast", 0, 1, 0.0, "", "sld", null, 1, "Contrast", null],
    [2792, "OSC 6 Spectral Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null],
    [2793, "OSC 6 Spectral Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null],
    [2794, "OSC 6 Spectral Width", 0, 1, 0.5, "", "sld", null, 1, "Width", null],
    [2795, "OSC 6 Spectral Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel > Pos", null],
    [2800, "OSC 1 SoundFont Gain", -1, 1, 0.0, "", "sld", null, 1, "Gain", null],
    [2801, "OSC 1 SoundFont Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel Sens", null],
    [2802, "OSC 1 SoundFont Attack", -1, 1, 0.0, "", "sld", null, 1, "Attack", null],
    [2803, "OSC 1 SoundFont Decay", -1, 1, 0.0, "", "sld", null, 1, "Decay", null],
    [2804, "OSC 1 SoundFont Sustain", -1, 1, 0.0, "", "sld", null, 1, "Sustain", null],
    [2805, "OSC 1 SoundFont Release", -1, 1, 0.0, "", "sld", null, 1, "Release", null],
    [2806, "OSC 1 SoundFont Loop", 0, 2, 0, "", "btn", ["Zone", "Off", "On"], 1, "Loop", null],
    [2807, "OSC 1 SoundFont Stereo", 0, 1, 1.0, "", "sld", null, 1, "Stereo", null],
    [2808, "OSC 1 SoundFont Start", 0, 1, 0.0, "", "sld", null, 1, "Start", null],
    [2809, "OSC 1 SoundFont Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2816, "OSC 2 SoundFont Gain", -1, 1, 0.0, "", "sld", null, 1, "Gain", null],
    [2817, "OSC 2 SoundFont Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel Sens", null],
    [2818, "OSC 2 SoundFont Attack", -1, 1, 0.0, "", "sld", null, 1, "Attack", null],
    [2819, "OSC 2 SoundFont Decay", -1, 1, 0.0, "", "sld", null, 1, "Decay", null],
    [2820, "OSC 2 SoundFont Sustain", -1, 1, 0.0, "", "sld", null, 1, "Sustain", null],
    [2821, "OSC 2 SoundFont Release", -1, 1, 0.0, "", "sld", null, 1, "Release", null],
    [2822, "OSC 2 SoundFont Loop", 0, 2, 0, "", "btn", ["Zone", "Off", "On"], 1, "Loop", null],
    [2823, "OSC 2 SoundFont Stereo", 0, 1, 1.0, "", "sld", null, 1, "Stereo", null],
    [2824, "OSC 2 SoundFont Start", 0, 1, 0.0, "", "sld", null, 1, "Start", null],
    [2825, "OSC 2 SoundFont Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2832, "OSC 3 SoundFont Gain", -1, 1, 0.0, "", "sld", null, 1, "Gain", null],
    [2833, "OSC 3 SoundFont Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel Sens", null],
    [2834, "OSC 3 SoundFont Attack", -1, 1, 0.0, "", "sld", null, 1, "Attack", null],
    [2835, "OSC 3 SoundFont Decay", -1, 1, 0.0, "", "sld", null, 1, "Decay", null],
    [2836, "OSC 3 SoundFont Sustain", -1, 1, 0.0, "", "sld", null, 1, "Sustain", null],
    [2837, "OSC 3 SoundFont Release", -1, 1, 0.0, "", "sld", null, 1, "Release", null],
    [2838, "OSC 3 SoundFont Loop", 0, 2, 0, "", "btn", ["Zone", "Off", "On"], 1, "Loop", null],
    [2839, "OSC 3 SoundFont Stereo", 0, 1, 1.0, "", "sld", null, 1, "Stereo", null],
    [2840, "OSC 3 SoundFont Start", 0, 1, 0.0, "", "sld", null, 1, "Start", null],
    [2841, "OSC 3 SoundFont Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2848, "OSC 4 SoundFont Gain", -1, 1, 0.0, "", "sld", null, 1, "Gain", null],
    [2849, "OSC 4 SoundFont Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel Sens", null],
    [2850, "OSC 4 SoundFont Attack", -1, 1, 0.0, "", "sld", null, 1, "Attack", null],
    [2851, "OSC 4 SoundFont Decay", -1, 1, 0.0, "", "sld", null, 1, "Decay", null],
    [2852, "OSC 4 SoundFont Sustain", -1, 1, 0.0, "", "sld", null, 1, "Sustain", null],
    [2853, "OSC 4 SoundFont Release", -1, 1, 0.0, "", "sld", null, 1, "Release", null],
    [2854, "OSC 4 SoundFont Loop", 0, 2, 0, "", "btn", ["Zone", "Off", "On"], 1, "Loop", null],
    [2855, "OSC 4 SoundFont Stereo", 0, 1, 1.0, "", "sld", null, 1, "Stereo", null],
    [2856, "OSC 4 SoundFont Start", 0, 1, 0.0, "", "sld", null, 1, "Start", null],
    [2857, "OSC 4 SoundFont Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2864, "OSC 5 SoundFont Gain", -1, 1, 0.0, "", "sld", null, 1, "Gain", null],
    [2865, "OSC 5 SoundFont Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel Sens", null],
    [2866, "OSC 5 SoundFont Attack", -1, 1, 0.0, "", "sld", null, 1, "Attack", null],
    [2867, "OSC 5 SoundFont Decay", -1, 1, 0.0, "", "sld", null, 1, "Decay", null],
    [2868, "OSC 5 SoundFont Sustain", -1, 1, 0.0, "", "sld", null, 1, "Sustain", null],
    [2869, "OSC 5 SoundFont Release", -1, 1, 0.0, "", "sld", null, 1, "Release", null],
    [2870, "OSC 5 SoundFont Loop", 0, 2, 0, "", "btn", ["Zone", "Off", "On"], 1, "Loop", null],
    [2871, "OSC 5 SoundFont Stereo", 0, 1, 1.0, "", "sld", null, 1, "Stereo", null],
    [2872, "OSC 5 SoundFont Start", 0, 1, 0.0, "", "sld", null, 1, "Start", null],
    [2873, "OSC 5 SoundFont Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [2880, "OSC 6 SoundFont Gain", -1, 1, 0.0, "", "sld", null, 1, "Gain", null],
    [2881, "OSC 6 SoundFont Velocity", 0, 1, 0.5, "", "sld", null, 1, "Vel Sens", null],
    [2882, "OSC 6 SoundFont Attack", -1, 1, 0.0, "", "sld", null, 1, "Attack", null],
    [2883, "OSC 6 SoundFont Decay", -1, 1, 0.0, "", "sld", null, 1, "Decay", null],
    [2884, "OSC 6 SoundFont Sustain", -1, 1, 0.0, "", "sld", null, 1, "Sustain", null],
    [2885, "OSC 6 SoundFont Release", -1, 1, 0.0, "", "sld", null, 1, "Release", null],
    [2886, "OSC 6 SoundFont Loop", 0, 2, 0, "", "btn", ["Zone", "Off", "On"], 1, "Loop", null],
    [2887, "OSC 6 SoundFont Stereo", 0, 1, 1.0, "", "sld", null, 1, "Stereo", null],
    [2888, "OSC 6 SoundFont Start", 0, 1, 0.0, "", "sld", null, 1, "Start", null],
    [2889, "OSC 6 SoundFont Drive", 0, 1, 0.0, "", "sld", null, 1, "Drive", null],
    [3500, "OSC 1 Bagpipe Scale", 0, 2, 2, "", "sel", ["Equal", "Just", "Highland"], 1, "Scale", null],
    [3501, "OSC 1 Bagpipe Reed", 0, 8, 3, "", "sel", ["Narrow", "Wide", "Saw Spike", "Sharp Spike", "Half Sine", "Triangle", "Double Pulse", "Buzzy", "Rounded"], 1, "Reed", null],
    [3502, "OSC 1 Bagpipe Reed Type", 0, 1, 0.0, "", "sld", null, 1, "Reed Type", null],
    [3503, "OSC 1 Bagpipe Bore Shape", 0, 1, 0.0, "", "sld", null, 1, "Bore Shape", null],
    [3504, "OSC 1 Bagpipe Coupling", 0, 1, 0.22, "", "sld", null, 1, "Coupling", null],
    [3505, "OSC 1 Bagpipe Bore", 0, 1, 0.5, "", "sld", null, 1, "Bore", null],
    [3506, "OSC 1 Bagpipe Fluctuation", 0, 1, 0.18, "", "sld", null, 1, "Fluct.", null],
    [3507, "OSC 1 Bagpipe Air", 0, 1, 0.05, "", "sld", null, 1, "Air", null],
    [3508, "OSC 1 Bagpipe Colour Mix", 0, 1, 0.4, "", "sld", null, 1, "Colour Mix", null],
    [3509, "OSC 1 Bagpipe Colour Freq", 0, 1, 0.3, "", "sld", null, 1, "Colour Freq", null],
    [3510, "OSC 1 Bagpipe Drone Level", 0, 1, 0.5, "", "sld", null, 1, "Drone Level", null],
    [3511, "OSC 1 Bagpipe Drone Chord", 0, 4, 1, "", "sel", ["Off", "Octaves", "Oct + Fifth", "Fifth", "Minor"], 1, "Drones", null],
    [3512, "OSC 1 Bagpipe Drone Key", 0, 11, 9, "", "sel", ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], 1, "Key", null],
    [3513, "OSC 1 Bagpipe Strike-In", 0, 1, 0.4, "", "sld", null, 1, "Strike-In", null],
    [3514, "OSC 1 Bagpipe Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [3515, "OSC 1 Bagpipe Blow", 0, 1, 0.0, "", "sld", null, 1, "Blow", null],
    [3516, "OSC 2 Bagpipe Scale", 0, 2, 2, "", "sel", ["Equal", "Just", "Highland"], 1, "Scale", null],
    [3517, "OSC 2 Bagpipe Reed", 0, 8, 3, "", "sel", ["Narrow", "Wide", "Saw Spike", "Sharp Spike", "Half Sine", "Triangle", "Double Pulse", "Buzzy", "Rounded"], 1, "Reed", null],
    [3518, "OSC 2 Bagpipe Reed Type", 0, 1, 0.0, "", "sld", null, 1, "Reed Type", null],
    [3519, "OSC 2 Bagpipe Bore Shape", 0, 1, 0.0, "", "sld", null, 1, "Bore Shape", null],
    [3520, "OSC 2 Bagpipe Coupling", 0, 1, 0.22, "", "sld", null, 1, "Coupling", null],
    [3521, "OSC 2 Bagpipe Bore", 0, 1, 0.5, "", "sld", null, 1, "Bore", null],
    [3522, "OSC 2 Bagpipe Fluctuation", 0, 1, 0.18, "", "sld", null, 1, "Fluct.", null],
    [3523, "OSC 2 Bagpipe Air", 0, 1, 0.05, "", "sld", null, 1, "Air", null],
    [3524, "OSC 2 Bagpipe Colour Mix", 0, 1, 0.4, "", "sld", null, 1, "Colour Mix", null],
    [3525, "OSC 2 Bagpipe Colour Freq", 0, 1, 0.3, "", "sld", null, 1, "Colour Freq", null],
    [3526, "OSC 2 Bagpipe Drone Level", 0, 1, 0.5, "", "sld", null, 1, "Drone Level", null],
    [3527, "OSC 2 Bagpipe Drone Chord", 0, 4, 1, "", "sel", ["Off", "Octaves", "Oct + Fifth", "Fifth", "Minor"], 1, "Drones", null],
    [3528, "OSC 2 Bagpipe Drone Key", 0, 11, 9, "", "sel", ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], 1, "Key", null],
    [3529, "OSC 2 Bagpipe Strike-In", 0, 1, 0.4, "", "sld", null, 1, "Strike-In", null],
    [3530, "OSC 2 Bagpipe Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [3531, "OSC 2 Bagpipe Blow", 0, 1, 0.0, "", "sld", null, 1, "Blow", null],
    [3532, "OSC 3 Bagpipe Scale", 0, 2, 2, "", "sel", ["Equal", "Just", "Highland"], 1, "Scale", null],
    [3533, "OSC 3 Bagpipe Reed", 0, 8, 3, "", "sel", ["Narrow", "Wide", "Saw Spike", "Sharp Spike", "Half Sine", "Triangle", "Double Pulse", "Buzzy", "Rounded"], 1, "Reed", null],
    [3534, "OSC 3 Bagpipe Reed Type", 0, 1, 0.0, "", "sld", null, 1, "Reed Type", null],
    [3535, "OSC 3 Bagpipe Bore Shape", 0, 1, 0.0, "", "sld", null, 1, "Bore Shape", null],
    [3536, "OSC 3 Bagpipe Coupling", 0, 1, 0.22, "", "sld", null, 1, "Coupling", null],
    [3537, "OSC 3 Bagpipe Bore", 0, 1, 0.5, "", "sld", null, 1, "Bore", null],
    [3538, "OSC 3 Bagpipe Fluctuation", 0, 1, 0.18, "", "sld", null, 1, "Fluct.", null],
    [3539, "OSC 3 Bagpipe Air", 0, 1, 0.05, "", "sld", null, 1, "Air", null],
    [3540, "OSC 3 Bagpipe Colour Mix", 0, 1, 0.4, "", "sld", null, 1, "Colour Mix", null],
    [3541, "OSC 3 Bagpipe Colour Freq", 0, 1, 0.3, "", "sld", null, 1, "Colour Freq", null],
    [3542, "OSC 3 Bagpipe Drone Level", 0, 1, 0.5, "", "sld", null, 1, "Drone Level", null],
    [3543, "OSC 3 Bagpipe Drone Chord", 0, 4, 1, "", "sel", ["Off", "Octaves", "Oct + Fifth", "Fifth", "Minor"], 1, "Drones", null],
    [3544, "OSC 3 Bagpipe Drone Key", 0, 11, 9, "", "sel", ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], 1, "Key", null],
    [3545, "OSC 3 Bagpipe Strike-In", 0, 1, 0.4, "", "sld", null, 1, "Strike-In", null],
    [3546, "OSC 3 Bagpipe Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [3547, "OSC 3 Bagpipe Blow", 0, 1, 0.0, "", "sld", null, 1, "Blow", null],
    [3548, "OSC 4 Bagpipe Scale", 0, 2, 2, "", "sel", ["Equal", "Just", "Highland"], 1, "Scale", null],
    [3549, "OSC 4 Bagpipe Reed", 0, 8, 3, "", "sel", ["Narrow", "Wide", "Saw Spike", "Sharp Spike", "Half Sine", "Triangle", "Double Pulse", "Buzzy", "Rounded"], 1, "Reed", null],
    [3550, "OSC 4 Bagpipe Reed Type", 0, 1, 0.0, "", "sld", null, 1, "Reed Type", null],
    [3551, "OSC 4 Bagpipe Bore Shape", 0, 1, 0.0, "", "sld", null, 1, "Bore Shape", null],
    [3552, "OSC 4 Bagpipe Coupling", 0, 1, 0.22, "", "sld", null, 1, "Coupling", null],
    [3553, "OSC 4 Bagpipe Bore", 0, 1, 0.5, "", "sld", null, 1, "Bore", null],
    [3554, "OSC 4 Bagpipe Fluctuation", 0, 1, 0.18, "", "sld", null, 1, "Fluct.", null],
    [3555, "OSC 4 Bagpipe Air", 0, 1, 0.05, "", "sld", null, 1, "Air", null],
    [3556, "OSC 4 Bagpipe Colour Mix", 0, 1, 0.4, "", "sld", null, 1, "Colour Mix", null],
    [3557, "OSC 4 Bagpipe Colour Freq", 0, 1, 0.3, "", "sld", null, 1, "Colour Freq", null],
    [3558, "OSC 4 Bagpipe Drone Level", 0, 1, 0.5, "", "sld", null, 1, "Drone Level", null],
    [3559, "OSC 4 Bagpipe Drone Chord", 0, 4, 1, "", "sel", ["Off", "Octaves", "Oct + Fifth", "Fifth", "Minor"], 1, "Drones", null],
    [3560, "OSC 4 Bagpipe Drone Key", 0, 11, 9, "", "sel", ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], 1, "Key", null],
    [3561, "OSC 4 Bagpipe Strike-In", 0, 1, 0.4, "", "sld", null, 1, "Strike-In", null],
    [3562, "OSC 4 Bagpipe Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [3563, "OSC 4 Bagpipe Blow", 0, 1, 0.0, "", "sld", null, 1, "Blow", null],
    [3564, "OSC 5 Bagpipe Scale", 0, 2, 2, "", "sel", ["Equal", "Just", "Highland"], 1, "Scale", null],
    [3565, "OSC 5 Bagpipe Reed", 0, 8, 3, "", "sel", ["Narrow", "Wide", "Saw Spike", "Sharp Spike", "Half Sine", "Triangle", "Double Pulse", "Buzzy", "Rounded"], 1, "Reed", null],
    [3566, "OSC 5 Bagpipe Reed Type", 0, 1, 0.0, "", "sld", null, 1, "Reed Type", null],
    [3567, "OSC 5 Bagpipe Bore Shape", 0, 1, 0.0, "", "sld", null, 1, "Bore Shape", null],
    [3568, "OSC 5 Bagpipe Coupling", 0, 1, 0.22, "", "sld", null, 1, "Coupling", null],
    [3569, "OSC 5 Bagpipe Bore", 0, 1, 0.5, "", "sld", null, 1, "Bore", null],
    [3570, "OSC 5 Bagpipe Fluctuation", 0, 1, 0.18, "", "sld", null, 1, "Fluct.", null],
    [3571, "OSC 5 Bagpipe Air", 0, 1, 0.05, "", "sld", null, 1, "Air", null],
    [3572, "OSC 5 Bagpipe Colour Mix", 0, 1, 0.4, "", "sld", null, 1, "Colour Mix", null],
    [3573, "OSC 5 Bagpipe Colour Freq", 0, 1, 0.3, "", "sld", null, 1, "Colour Freq", null],
    [3574, "OSC 5 Bagpipe Drone Level", 0, 1, 0.5, "", "sld", null, 1, "Drone Level", null],
    [3575, "OSC 5 Bagpipe Drone Chord", 0, 4, 1, "", "sel", ["Off", "Octaves", "Oct + Fifth", "Fifth", "Minor"], 1, "Drones", null],
    [3576, "OSC 5 Bagpipe Drone Key", 0, 11, 9, "", "sel", ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], 1, "Key", null],
    [3577, "OSC 5 Bagpipe Strike-In", 0, 1, 0.4, "", "sld", null, 1, "Strike-In", null],
    [3578, "OSC 5 Bagpipe Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [3579, "OSC 5 Bagpipe Blow", 0, 1, 0.0, "", "sld", null, 1, "Blow", null],
    [3580, "OSC 6 Bagpipe Scale", 0, 2, 2, "", "sel", ["Equal", "Just", "Highland"], 1, "Scale", null],
    [3581, "OSC 6 Bagpipe Reed", 0, 8, 3, "", "sel", ["Narrow", "Wide", "Saw Spike", "Sharp Spike", "Half Sine", "Triangle", "Double Pulse", "Buzzy", "Rounded"], 1, "Reed", null],
    [3582, "OSC 6 Bagpipe Reed Type", 0, 1, 0.0, "", "sld", null, 1, "Reed Type", null],
    [3583, "OSC 6 Bagpipe Bore Shape", 0, 1, 0.0, "", "sld", null, 1, "Bore Shape", null],
    [3584, "OSC 6 Bagpipe Coupling", 0, 1, 0.22, "", "sld", null, 1, "Coupling", null],
    [3585, "OSC 6 Bagpipe Bore", 0, 1, 0.5, "", "sld", null, 1, "Bore", null],
    [3586, "OSC 6 Bagpipe Fluctuation", 0, 1, 0.18, "", "sld", null, 1, "Fluct.", null],
    [3587, "OSC 6 Bagpipe Air", 0, 1, 0.05, "", "sld", null, 1, "Air", null],
    [3588, "OSC 6 Bagpipe Colour Mix", 0, 1, 0.4, "", "sld", null, 1, "Colour Mix", null],
    [3589, "OSC 6 Bagpipe Colour Freq", 0, 1, 0.3, "", "sld", null, 1, "Colour Freq", null],
    [3590, "OSC 6 Bagpipe Drone Level", 0, 1, 0.5, "", "sld", null, 1, "Drone Level", null],
    [3591, "OSC 6 Bagpipe Drone Chord", 0, 4, 1, "", "sel", ["Off", "Octaves", "Oct + Fifth", "Fifth", "Minor"], 1, "Drones", null],
    [3592, "OSC 6 Bagpipe Drone Key", 0, 11, 9, "", "sel", ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], 1, "Key", null],
    [3593, "OSC 6 Bagpipe Strike-In", 0, 1, 0.4, "", "sld", null, 1, "Strike-In", null],
    [3594, "OSC 6 Bagpipe Vibrato", 0, 1, 0.0, "", "sld", null, 1, "Vibrato", null],
    [3595, "OSC 6 Bagpipe Blow", 0, 1, 0.0, "", "sld", null, 1, "Blow", null],,
    // SM-BEGIN
    [12300, "OSC 1 Sample End", 0, 1, 1.0, "", "sld", null, 1, "End", null],
    [12301, "OSC 1 Sample Loop Start", 0, 1, 0.0, "", "sld", null, 1, "Loop Start", null],
    [12302, "OSC 1 Sample Loop End", 0, 1, 1.0, "", "sld", null, 1, "Loop End", null],
    [12303, "OSC 1 Sample Loop Mode", 0, 1, 0.0, "", "btn", ["Forward", "Ping-Pong"], 1, "Loop Mode", null],
    [12304, "OSC 1 Sample Loop Crossfade", 0, 1, 0.0, "", "sld", null, 1, "Crossfade", null],
    [12305, "OSC 1 Sample Reverse", 0, 1, 0.0, "", "btn", ["Off", "On"], 1, "Reverse", null],
    [12306, "OSC 1 Sample Interpolation", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null],
    [12307, "OSC 1 Sample Gain", -24, 12, 0.0, "dB", "sld", null, 1, "Gain", null],
    [12308, "OSC 1 Sample Vel Start", 0, 1, 0.0, "", "sld", null, 1, "Vel > Start", null],
    [12309, "OSC 1 Sample Slices", 1, 64, 1.0, "", "stp", null, 1, "Slices", null],
    [12310, "OSC 1 Sample Width", 0, 2, 1.0, "", "sld", null, 1, "Width", null],
    [12316, "OSC 2 Sample End", 0, 1, 1.0, "", "sld", null, 1, "End", null],
    [12317, "OSC 2 Sample Loop Start", 0, 1, 0.0, "", "sld", null, 1, "Loop Start", null],
    [12318, "OSC 2 Sample Loop End", 0, 1, 1.0, "", "sld", null, 1, "Loop End", null],
    [12319, "OSC 2 Sample Loop Mode", 0, 1, 0.0, "", "btn", ["Forward", "Ping-Pong"], 1, "Loop Mode", null],
    [12320, "OSC 2 Sample Loop Crossfade", 0, 1, 0.0, "", "sld", null, 1, "Crossfade", null],
    [12321, "OSC 2 Sample Reverse", 0, 1, 0.0, "", "btn", ["Off", "On"], 1, "Reverse", null],
    [12322, "OSC 2 Sample Interpolation", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null],
    [12323, "OSC 2 Sample Gain", -24, 12, 0.0, "dB", "sld", null, 1, "Gain", null],
    [12324, "OSC 2 Sample Vel Start", 0, 1, 0.0, "", "sld", null, 1, "Vel > Start", null],
    [12325, "OSC 2 Sample Slices", 1, 64, 1.0, "", "stp", null, 1, "Slices", null],
    [12326, "OSC 2 Sample Width", 0, 2, 1.0, "", "sld", null, 1, "Width", null],
    [12332, "OSC 3 Sample End", 0, 1, 1.0, "", "sld", null, 1, "End", null],
    [12333, "OSC 3 Sample Loop Start", 0, 1, 0.0, "", "sld", null, 1, "Loop Start", null],
    [12334, "OSC 3 Sample Loop End", 0, 1, 1.0, "", "sld", null, 1, "Loop End", null],
    [12335, "OSC 3 Sample Loop Mode", 0, 1, 0.0, "", "btn", ["Forward", "Ping-Pong"], 1, "Loop Mode", null],
    [12336, "OSC 3 Sample Loop Crossfade", 0, 1, 0.0, "", "sld", null, 1, "Crossfade", null],
    [12337, "OSC 3 Sample Reverse", 0, 1, 0.0, "", "btn", ["Off", "On"], 1, "Reverse", null],
    [12338, "OSC 3 Sample Interpolation", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null],
    [12339, "OSC 3 Sample Gain", -24, 12, 0.0, "dB", "sld", null, 1, "Gain", null],
    [12340, "OSC 3 Sample Vel Start", 0, 1, 0.0, "", "sld", null, 1, "Vel > Start", null],
    [12341, "OSC 3 Sample Slices", 1, 64, 1.0, "", "stp", null, 1, "Slices", null],
    [12342, "OSC 3 Sample Width", 0, 2, 1.0, "", "sld", null, 1, "Width", null],
    [12348, "OSC 4 Sample End", 0, 1, 1.0, "", "sld", null, 1, "End", null],
    [12349, "OSC 4 Sample Loop Start", 0, 1, 0.0, "", "sld", null, 1, "Loop Start", null],
    [12350, "OSC 4 Sample Loop End", 0, 1, 1.0, "", "sld", null, 1, "Loop End", null],
    [12351, "OSC 4 Sample Loop Mode", 0, 1, 0.0, "", "btn", ["Forward", "Ping-Pong"], 1, "Loop Mode", null],
    [12352, "OSC 4 Sample Loop Crossfade", 0, 1, 0.0, "", "sld", null, 1, "Crossfade", null],
    [12353, "OSC 4 Sample Reverse", 0, 1, 0.0, "", "btn", ["Off", "On"], 1, "Reverse", null],
    [12354, "OSC 4 Sample Interpolation", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null],
    [12355, "OSC 4 Sample Gain", -24, 12, 0.0, "dB", "sld", null, 1, "Gain", null],
    [12356, "OSC 4 Sample Vel Start", 0, 1, 0.0, "", "sld", null, 1, "Vel > Start", null],
    [12357, "OSC 4 Sample Slices", 1, 64, 1.0, "", "stp", null, 1, "Slices", null],
    [12358, "OSC 4 Sample Width", 0, 2, 1.0, "", "sld", null, 1, "Width", null],
    [12364, "OSC 5 Sample End", 0, 1, 1.0, "", "sld", null, 1, "End", null],
    [12365, "OSC 5 Sample Loop Start", 0, 1, 0.0, "", "sld", null, 1, "Loop Start", null],
    [12366, "OSC 5 Sample Loop End", 0, 1, 1.0, "", "sld", null, 1, "Loop End", null],
    [12367, "OSC 5 Sample Loop Mode", 0, 1, 0.0, "", "btn", ["Forward", "Ping-Pong"], 1, "Loop Mode", null],
    [12368, "OSC 5 Sample Loop Crossfade", 0, 1, 0.0, "", "sld", null, 1, "Crossfade", null],
    [12369, "OSC 5 Sample Reverse", 0, 1, 0.0, "", "btn", ["Off", "On"], 1, "Reverse", null],
    [12370, "OSC 5 Sample Interpolation", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null],
    [12371, "OSC 5 Sample Gain", -24, 12, 0.0, "dB", "sld", null, 1, "Gain", null],
    [12372, "OSC 5 Sample Vel Start", 0, 1, 0.0, "", "sld", null, 1, "Vel > Start", null],
    [12373, "OSC 5 Sample Slices", 1, 64, 1.0, "", "stp", null, 1, "Slices", null],
    [12374, "OSC 5 Sample Width", 0, 2, 1.0, "", "sld", null, 1, "Width", null],
    [12380, "OSC 6 Sample End", 0, 1, 1.0, "", "sld", null, 1, "End", null],
    [12381, "OSC 6 Sample Loop Start", 0, 1, 0.0, "", "sld", null, 1, "Loop Start", null],
    [12382, "OSC 6 Sample Loop End", 0, 1, 1.0, "", "sld", null, 1, "Loop End", null],
    [12383, "OSC 6 Sample Loop Mode", 0, 1, 0.0, "", "btn", ["Forward", "Ping-Pong"], 1, "Loop Mode", null],
    [12384, "OSC 6 Sample Loop Crossfade", 0, 1, 0.0, "", "sld", null, 1, "Crossfade", null],
    [12385, "OSC 6 Sample Reverse", 0, 1, 0.0, "", "btn", ["Off", "On"], 1, "Reverse", null],
    [12386, "OSC 6 Sample Interpolation", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null],
    [12387, "OSC 6 Sample Gain", -24, 12, 0.0, "dB", "sld", null, 1, "Gain", null],
    [12388, "OSC 6 Sample Vel Start", 0, 1, 0.0, "", "sld", null, 1, "Vel > Start", null],
    [12389, "OSC 6 Sample Slices", 1, 64, 1.0, "", "stp", null, 1, "Slices", null],
    [12390, "OSC 6 Sample Width", 0, 2, 1.0, "", "sld", null, 1, "Width", null],
    // SM-END
    // WT2-BEGIN
    [12500, "OSC 1 Warp 3 Mode", 0, 26, 0.0, "", "sel", WARP_MODES, 1, "Warp 3", null],
    [12501, "OSC 1 Warp 3 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 3 Amt", null],
    [12502, "OSC 1 WT Morph", 0, 2, 0.0, "", "btn", ["Fade", "Smooth", "Stepped"], 1, "Morph", null],
    [12503, "OSC 1 WT Tone", 0, 1, 1.0, "", "sld", null, 1, "Tone", null],
    [12516, "OSC 2 Warp 3 Mode", 0, 26, 0.0, "", "sel", WARP_MODES, 1, "Warp 3", null],
    [12517, "OSC 2 Warp 3 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 3 Amt", null],
    [12518, "OSC 2 WT Morph", 0, 2, 0.0, "", "btn", ["Fade", "Smooth", "Stepped"], 1, "Morph", null],
    [12519, "OSC 2 WT Tone", 0, 1, 1.0, "", "sld", null, 1, "Tone", null],
    [12532, "OSC 3 Warp 3 Mode", 0, 26, 0.0, "", "sel", WARP_MODES, 1, "Warp 3", null],
    [12533, "OSC 3 Warp 3 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 3 Amt", null],
    [12534, "OSC 3 WT Morph", 0, 2, 0.0, "", "btn", ["Fade", "Smooth", "Stepped"], 1, "Morph", null],
    [12535, "OSC 3 WT Tone", 0, 1, 1.0, "", "sld", null, 1, "Tone", null],
    [12548, "OSC 4 Warp 3 Mode", 0, 26, 0.0, "", "sel", WARP_MODES, 1, "Warp 3", null],
    [12549, "OSC 4 Warp 3 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 3 Amt", null],
    [12550, "OSC 4 WT Morph", 0, 2, 0.0, "", "btn", ["Fade", "Smooth", "Stepped"], 1, "Morph", null],
    [12551, "OSC 4 WT Tone", 0, 1, 1.0, "", "sld", null, 1, "Tone", null],
    [12564, "OSC 5 Warp 3 Mode", 0, 26, 0.0, "", "sel", WARP_MODES, 1, "Warp 3", null],
    [12565, "OSC 5 Warp 3 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 3 Amt", null],
    [12566, "OSC 5 WT Morph", 0, 2, 0.0, "", "btn", ["Fade", "Smooth", "Stepped"], 1, "Morph", null],
    [12567, "OSC 5 WT Tone", 0, 1, 1.0, "", "sld", null, 1, "Tone", null],
    [12580, "OSC 6 Warp 3 Mode", 0, 26, 0.0, "", "sel", WARP_MODES, 1, "Warp 3", null],
    [12581, "OSC 6 Warp 3 Amount", 0, 1, 0.5, "", "sld", null, 1, "Warp 3 Amt", null],
    [12582, "OSC 6 WT Morph", 0, 2, 0.0, "", "btn", ["Fade", "Smooth", "Stepped"], 1, "Morph", null],
    [12583, "OSC 6 WT Tone", 0, 1, 1.0, "", "sld", null, 1, "Tone", null]
    // WT2-END
];

// option groups of the dropdowns: [first index, group title]
const MOD_SRC_GROUPS = [[0, ""], [1, "LFO"], [11, "Envelope"], [21, "Note"], [24, "Freq"], [34, "Sequencer"], [44, "Random"]];
const MOD_SLOTS = 20;   // slots shown by this fallback UI
const MOD_SLOTS_MAX = 256;   // slots the DSP has (the native editor shows them all)
// parameter number of the first (source) param of a matrix slot: slots 1-10 are 307.., slots 11-20 are 472..
const slotBase = s => s < 10 ? 307 + 3 * s : (s < 20 ? 472 + 3 * (s - 10) : 4000 + 3 * (s - 20));

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
// trance gate patterns: 16 steps, '#' open, '+' 45 %, '.' closed (the DSP table is generated from the same list by tools/fx/build_fx3.py)
const FX_GATE_PATTERNS = [
    ["Eighths", "#.#.#.#.#.#.#.#."], ["Quarters", "#...#...#...#..."], ["Off-beat", "..#...#...#...#."], ["Accented 16ths", "#+#+#+#+#+#+#+#+"],
    ["3-3-2", "#..#..#.#..#..#."], ["Dotted", "#..#..#...#..#.."], ["Rolling", "#.##.#.##.##.#.#"], ["Syncopated", "#..#.#..#..#.#.."],
    ["Stutter", "####............"], ["Half time", "#.......#......."], ["Gallop", "#.###.#.###.#.##"], ["Trance", "#.##.##.#.##.##."],
    ["Double", "##..##..##..##.."], ["Ghost notes", "#+.+#+.+#+.+#+.+"], ["Build", "#...#...#.#.####"], ["Break", "#.#.#.#.##..##.."],
    ["Pulse", "#...#...#...#.#."], ["Skip", "#.#...#.#.#...#."], ["Rapid", "####.###.###.###"], ["Sparse", "#.....#...#....."],
    ["Pump", "#.+.#.+.#.+.#.+."], ["Bounce", "#.#..#.#.#..#.#."], ["Triplet feel", "#..#..#..#..#..#"], ["Full", "################"]
];
const fxPat = n => FX_GATE_PATTERNS[Math.max(0, Math.min(23, Math.floor(n * 24)))][0];
// [label, formatter, default (normalised)]
const FX_TYPES = [
    { n: "None", mix: 1, modes: [], p: [] },
    { n: "Distortion", mix: 1, modes: ["Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Rectify", "Fuzz", "Tanh", "Diode", "Chebyshev", "Tape", "Gated"],
      p: [["Drive", fxPct, 0.4], ["Tone", fxHz(500, 20000), 1], ["Output", n => (n * 2).toFixed(2) + "x", 0.5], ["Bias", fxLin(-100, 100, 0, "%"), 0.5], ["Low Cut", fxHz(10, 800), 0], ["Presence", fxPct, 0]] },
    { n: "Bit Crush", mix: 1, modes: ["Round", "Mu-law", "Floor", "Bits Only", "Rate Only", "Noise Shaped"],
      p: [["Bits", n => (16 - 12 * n).toFixed(1) + " bit", 0.5], ["Rate", n => "1/" + (1 + Math.round(n * 31)), 0.1], ["Dither", fxPct, 0], ["Jitter", fxPct, 0]] },
    { n: "Delay", mix: 0.35, modes: ["Digital", "Tape", "Dual", "Ducking", "Reverse", "Multi-tap"],
      p: [["Time", fxMs(10, 1000), fxExpN(375, 10, 1000)], ["Feedback", fxPctOf(0.95), 0.37], ["Damp", fxHz(500, 18000), 1], ["Ping-Pong", fxPct, 1], ["Mod", fxPct, 0], ["Low Cut", fxHz(20, 1000), 0]] },
    { n: "Chorus", mix: 0.5, modes: ["Classic", "Dimension", "Vibrato", "Ensemble", "Wide"],
      p: [["Rate", fxHz(0.05, 5), fxExpN(0.8, 0.05, 5)], ["Depth", fxPct, 0.5], ["Feedback", fxPctOf(0.9), 0], ["Width", fxPctOf(2), 0.5]] },
    { n: "Flanger", mix: 0.5, modes: ["Positive", "Negative", "Through-Zero", "Stereo"],
      p: [["Rate", fxHz(0.05, 5), fxExpN(0.3, 0.05, 5)], ["Depth", fxPct, 0.6], ["Feedback", fxPctOf(0.95), 0.53], ["Width", fxPctOf(2), 0.5]] },
    { n: "Phaser", mix: 0.5, modes: ["2 Stages", "4 Stages", "6 Stages", "8 Stages", "10 Stages", "12 Stages", "Inverted 4", "Inverted 8"],
      p: [["Rate", fxHz(0.05, 8), fxExpN(0.4, 0.05, 8)], ["Depth", fxPct, 0.5], ["Feedback", fxPctOf(0.9), 0.55], ["Width", fxPctOf(2), 0.5]] },
    { n: "Tremolo", mix: 1, modes: ["Sin", "Tri", "Sqr", "Saw Dn", "Saw Up", "Trance Gate", "Auto-Pan", "Random S&H", "Smooth Random"],
      p: [["Rate", fxHz(0.1, 20), fxExpN(5, 0.1, 20)], ["Depth", fxPct, 0.7], ["Stereo", fxPct, 0], ["Pattern", fxPat, 1.5 / 24], ["Smooth", fxMs(0.3, 40), 0.3], ["Swing", fxPctOf(0.5), 0]] },
    { n: "Reverb", mix: 0.3, modes: ["Hall", "Room", "Plate", "Cathedral", "Chamber", "Ambience", "Dark", "Bright", "Infinite"],
      p: [["Size", fxPct, 0.5], ["Damp", fxPct, 0.5], ["PreDly", n => Math.round(n * 100) + " ms", 0.2], ["Width", fxPct, 1], ["Low Cut", fxHz(20, 800), 0], ["High Cut", fxHz(1500, 20000), 1]] },
    { n: "Filter", mix: 1, modes: FX_FILTER_TYPES, groups: FX_FILTER_GROUPS,
      p: [["Cutoff", fxHz(20, 20000), 0.67], ["Reso", fxPct, 0.2], ["Drive", fxPct, 0], ["Env Amt", fxLin(-100, 100, 0, "%"), 0.5], ["Env Src", fxLin(1, 10, 0, ""), 0], ["Key Track", fxPct, 0]] },   // the envelope takes its times from a modulation envelope (ENV 1-10)
    { n: "EQ", mix: 1, modes: ["Classic", "Tilt", "Loudness", "Presence"],
      p: [["Low", fxDb(-12, 12), 0.5], ["Mid", fxDb(-12, 12), 0.5], ["Mid Freq", fxHz(200, 5000), 0.5], ["High", fxDb(-12, 12), 0.5], ["Mid Q", n => "Q " + fxExp(0.3, 4)(n).toFixed(2), 0.5], ["High Freq", fxHz(4000, 16000), 0.5]] },
    { n: "Compressor", mix: 1, modes: ["Peak", "RMS", "Limiter", "Expander", "Gate"],
      p: [["Thresh", fxLin(-60, 0, 1, "dB"), 0.6], ["Ratio", n => (1 + 19 * n * n).toFixed(1) + ":1", 0.3], ["Attack", fxMs(0.1, 100), 0.4], ["Release", fxMs(10, 1000), 0.4], ["Makeup", fxLin(0, 24, 1, "dB"), 0.2], ["Knee", fxLin(0, 12, 1, "dB"), 0]] },
    { n: "Convolution", mix: 0.3, modes: ["Room", "Hall", "Plate", "Cathedral", "Chamber", "Reverse", "Gated", "Ambience", "User IR"],
      p: [["Size", fxPct, 0.5], ["Decay", fxPct, 0.5], ["Damp", fxPct, 0.4], ["PreDly", fxLin(0, 200, 0, "ms"), 0], ["Width", fxPctOf(2), 0.5], ["Tone", fxLin(-100, 100, 0, "%"), 0.5]] },
    // bands live in the sound memory (native editor); these are the slot-wide controls
    { n: "Parametric EQ", mix: 1, modes: [],
      p: [["Output", fxDb(-18, 18), 0.5], ["Gain Scale", fxPctOf(2), 0.5], ["Freq Shift", fxLin(-1, 1, 2, "oct"), 0.5], ["Q Scale", n => "x" + (0.25 * Math.pow(16, n)).toFixed(2), 0.5]] },
    { n: "Saturator", mix: 1, modes: ["Tube", "Tape", "Transformer", "Diode", "Fuzz", "Soft Clip", "Hard Clip", "Rectifier", "Sine Fold", "Rational", "Exciter", "Arctan"],
      p: [["Drive", fxLin(0, 36, 1, "dB"), 0.3], ["Tone", fxLin(-100, 100, 0, "%"), 0.5], ["Bias", fxLin(-100, 100, 0, "%"), 0.5], ["Output", fxDb(-12, 12), 0.5], ["Low Cut", fxHz(10, 800), 0], ["Sag", fxPct, 0]] },
    // transfer-curve nodes live in the sound memory (native editor)
    { n: "Waveshaper", mix: 1, modes: ["Curve", "Mirror", "Rectified"],
      p: [["Drive", fxLin(0, 30, 1, "dB"), 0.3], ["Bias", fxLin(-100, 100, 0, "%"), 0.5], ["Output", fxDb(-12, 12), 0.5], ["Tone", fxHz(500, 20000), 1], ["Low Cut", fxHz(10, 800), 0]] },
    // Unison: detuned pitch-shifted copies of the input (two-tap crossfading delay lines)
    { n: "Unison", mix: 0.5, modes: ["Classic", "Super", "Hyper", "Octaves"],
      p: [["Voices", fxLin(2, 8, 0, ""), 0.5], ["Detune", fxLin(0, 100, 0, "ct"), 0.25], ["Spread", fxPct, 0.7], ["Drift", fxLin(0, 12, 1, "ct"), 0.2], ["Window", fxLin(10, 60, 0, "ms"), 0.5], ["Tone", fxHz(800, 20000), 1]] },
    // Console: channel strip with transformer drive and two sweepable mid bands (mode = bandwidth, +4 = EQ before the saturation)
    { n: "Console", mix: 1, modes: ["Wide", "Medium", "Narrow", "Surgical", "Wide, EQ first", "Medium, EQ first", "Narrow, EQ first", "Surgical, EQ first"],
      p: [["Lo-Mid Freq", fxHz(45, 3000), 0.45], ["Lo-Mid Gain", fxDb(-15, 15), 0.5], ["Hi-Mid Freq", fxHz(500, 18000), 0.55], ["Hi-Mid Gain", fxDb(-15, 15), 0.5], ["Drive", fxPct, 0.2], ["Age", fxPct, 0]] },
    // Filterbank (after the Sherman Filterbank): two multimode filters, response LP-BP-HP, anti-mix to the notch, filter 2 tuned in semitones
    { n: "Filterbank", mix: 1, modes: ["Parallel", "Series", "Blend", "Parallel Mirror", "Series Mirror", "Blend Mirror"],
      p: [["Freq", fxHz(20, 20000), 0.5], ["Reso", fxPct, 0.4], ["Response", fxPct, 0.5], ["Anti-Mix", fxPct, 0], ["Drive", fxPct, 0.1], ["F2 Offset", fxLin(-24, 24, 0, "st"), 0.5]] },
    // FX-AW: ports of Airwindows plugins by Chris Johnson (MIT licence, https://github.com/airwindows/airwindows), types 19..26
    { n: "AW PurestDrive", mix: 1, modes: [],
      p: [["Drive", fxPct, 1]] },
    { n: "AW Spiral", mix: 1, modes: [],
      p: [["Input", fxPct, 0.5], ["Highpass", fxPct, 0], ["Presence", fxPct, 0.5], ["Output", fxPct, 1]] },
    { n: "AW Drive", mix: 1, modes: [],
      p: [["Drive", fxPct, 0.5], ["Highpass", fxPct, 0], ["Output", fxPct, 1]] },
    { n: "AW Tube", mix: 1, modes: [],
      p: [["Input", fxPct, 0.5], ["Tube", fxPct, 0.5]] },
    { n: "AW Density", mix: 1, modes: [],
      p: [["Density", fxPct, 0.4], ["Highpass", fxPct, 0], ["Output", fxPct, 1]] },
    { n: "AW Console 7", mix: 1, modes: [],
      p: [["Fader", fxPct, 0.772]] },
    { n: "AW Channel", mix: 1, modes: ["Neve", "API", "SSL", "Teac", "Mackie"],
      p: [["Drive", fxPct, 0.3], ["Output", fxPct, 1]] },
    { n: "AW ToTape", mix: 1, modes: [],
      p: [["Input", fxDb(-12, 12), 0.5], ["Soften", fxPct, 0.5], ["Head Bump", fxPct, 0.5], ["Flutter", fxPct, 0.5], ["Output", fxDb(-12, 12), 0.5]] },
    { n: "AW MackEQ", mix: 1, modes: [],
      p: [["Trim", fxPct, 0.1], ["Hi", fxPct, 0.5], ["Lo", fxPct, 0.5], ["Gain", fxPct, 1]] },
    // FX-PLASMA: asymmetric distortion in the style of Dimethoxy's Plasma (own implementation): 12 styles, bias, girth noise, resonant filter after the shaper
    { n: "Plasma", mix: 1, modes: ["Soft", "Hard", "Fold", "Half", "Fuzz", "Diode", "Arctan", "Rational", "Soft Exp", "Ripple", "Tri Fold", "Cubic"],
      p: [["Drive", fxLin(0, 40, 1, "dB"), 0.4], ["Asym", fxLin(-100, 100, 0, "%"), 0.5], ["Girth", fxPct, 0], ["Filter", n => ["HP", "LP", "Dual", "Peak"][Math.min(3, Math.floor(n * 4))], 0.375], ["Freq", fxHz(20, 20000), 1], ["Reso", fxPct, 0]] },
    // FX-MUTABLE: two effects in the spirit of Mutable Instruments Clouds and Warps (own implementations after the manuals)
    { n: "Granular", mix: 0.5, modes: ["Granular", "Freeze", "Pitch Shifter", "Looping Delay"],
      p: [["Position", fxPct, 0.3], ["Size", fxMs(20, 600), fxExpN(150, 20, 600)], ["Pitch", fxLin(-24, 24, 1, "st"), 0.5], ["Density", fxPct, 0.5], ["Texture", fxPct, 0.5], ["Feedback", fxPct, 0]] },
    { n: "Warp", mix: 1, modes: ["Analog RM", "Digital RM", "Vocoder", "Freq Shift"],
      p: [["Amount", fxPct, 0.5], ["Level", n => (n * 2).toFixed(2) + "x", 0.5], ["Pitch", fxHz(20, 4000), fxExpN(220, 20, 4000)], ["Shape", fxPct, 0], ["Drive", fxDb(-12, 12), 0.5], ["Release", fxPct, 0.3]] },
    // FX-CLOUDSEED: port of the CloudSeed reverb core (Ghost Note Audio, MIT licence), FX type 31
    { n: "CloudSeed", mix: 0.3, modes: ["Dark Plate", "Hall", "Room", "Chamber", "Cathedral", "Cloud", "Ambience", "Echo Space"],
      p: [["Decay", fxMs(200, 30000), 0.45], ["Size", fxPct, 0.5], ["Damp", fxPct, 0.4], ["PreDly", fxLin(0, 80, 0, "ms"), 0.1], ["Mod", fxPct, 0.3], ["Early", fxPct, 0.3]] },
    // FX-WAVEGUIDE: the input excites resonating delay loops (FX type 32)
    { n: "Waveguide", mix: 0.5, modes: ["String", "Tube", "Dual Strings", "Fifth Drone", "Octave Drone", "String Key", "Tube Key", "Dual Strings Key", "Fifth Drone Key", "Octave Drone Key"],
      p: [["Pitch", fxHz(30, 2000), 0.45], ["Decay", fxMs(50, 8000), 0.5], ["Damp", fxHz(500, 16000), 0.7], ["Detune", fxLin(0, 50, 0, "ct"), 0.1], ["Excite", fxPct, 0.5], ["Drive", fxPct, 0]] },
    // FX-YAYBAHAR: string -> two springs -> two drum membranes (FX type 33)
    { n: "Yaybahar", mix: 0.6, modes: ["Classic", "Stereo", "Deep", "Classic Key", "Stereo Key", "Deep Key"],
      p: [["Pitch", fxHz(40, 800), 0.4], ["Spring", fxMs(20, 250), 0.5], ["Decay", fxPct, 0.5], ["Disper", fxPct, 0.5], ["Membran", fxHz(40, 250), 0.35], ["Damp", fxHz(500, 8000), 0.6]] },
    // FX-SHTAB: distortion with the transfer curve of a shaper table frame (FX type 34)
    { n: "Shaper Table", mix: 1, modes: ["Clip", "Fold", "Wrap", "Rect"],
      p: [["Drive", fxLin(0, 36, 1, "dB"), 0.3], ["Pos", fxPct, 0], ["Table", fxLin(1, 6, 0, ""), 0], ["Bias", fxLin(-100, 100, 0, "%"), 0.5], ["Tone", fxHz(500, 20000), 1], ["Level", fxLin(-24, 12, 1, "dB"), 0.667]] },
    // FX-YBPARTS: the elements of the Yaybahar as effects of their own (FX types 35..37)
    { n: "Yb Spring", mix: 0.6, modes: ["Single", "Dual", "Stereo"],
      p: [["Length", fxMs(20, 250), 0.5], ["Decay", fxPct, 0.6], ["Disper", fxPct, 0.5], ["Damp", fxHz(500, 8000), 0.6], ["Boing", fxPct, 0.2], ["Level", fxLin(-12, 12, 1, "dB"), 0.5]] },
    { n: "Yb Drum", mix: 0.6, modes: ["Rect", "Two Drums", "Stereo", "Rect Key", "Two Drums Key", "Stereo Key"],
      p: [["Tune", fxHz(40, 250), 0.5], ["Decay", fxPct, 0.5], ["Aspect", fxLin(0.6, 1.6, 2, ""), 0.52], ["Strike", fxPct, 0.83], ["Pickup", fxPct, 0.63], ["Damp", fxPct, 0.3]] },
    { n: "Yb String", mix: 0.6, modes: ["Mono", "Stereo", "Octave", "Mono Key", "Stereo Key", "Octave Key"],
      p: [["Pitch", fxHz(40, 800), 0.4], ["Decay", fxPct, 0.6], ["Damp", fxHz(500, 8000), 0.5], ["Bow", fxPct, 0.4], ["Detune", fxLin(-25, 25, 0, "ct"), 0.5], ["Level", fxLin(-12, 12, 1, "dB"), 0.5]] },
    // PHASEQ: phase-only EQ (FX type 38), the band editor shows the phase response
    { n: "Phase EQ", mix: 1, modes: [],
      p: [["Output", fxDb(-18, 18), 0.5], ["Spread Scale", fxPctOf(2), 0.5], ["Freq Shift", fxLin(-1, 1, 2, "oct"), 0.5], ["Q Scale", n => "x" + (0.25 * Math.pow(16, n)).toFixed(2), 0.5]] },
    // FX-WFILT: the Wavefilter of the oscillators as an effect (FX type 39), table = filter table of an oscillator
    { n: "Wavefilter", mix: 1, modes: ["Linear", "Bipolar", "dB"],
      p: [["Cutoff", fxHz(20, 20000), 0.5], ["Reso", fxPct, 0.2], ["Pos", fxPct, 0], ["Table", fxLin(1, 6, 0, ""), 0], ["Range", fxLin(2, 14, 1, "oct"), 0.5], ["Contrast", fxLin(-100, 100, 0, "%"), 0.5]] },
    // FX-SPEC: FFT effect (FX type 40), STFT with 512 points, latency 512 samples
    { n: "Spectral", mix: 1, modes: ["Shape", "Freeze", "Gate", "Robot", "Whisper"],
      p: [["Amount", fxPct, 0.5], ["Tilt", fxLin(-100, 100, 0, "%"), 0.5], ["Shift", fxLin(-12, 12, 0, "st"), 0.5], ["Lo Cut", fxPct, 0], ["Hi Cut", fxPct, 0], ["Floor", fxPct, 0]] },
    // FX-FTAB: Filter Table as in the Kilohearts original: the spectrum of a table frame is the filter response (FFT filter, FX type 41)
    { n: "Filter Table", mix: 1, modes: ["Linear", "dB"],
      p: [["Cutoff", fxHz(20, 20000), 0.5], ["Reso", fxPct, 0], ["Frame", fxPct, 0], ["Table", fxLin(1, 6, 0, ""), 0], ["Range", fxLin(2, 14, 1, "oct"), 0.583], ["Gain", fxDb(-12, 12), 0.5]] },
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
const FRQ_STATE_KEY = "njo.frq";
const FRQ_BASE = 1600;                 // Freq modulator m: rate (ms), transpose (st), retrig, loop = FRQ_BASE + 4 * m + 0..3
const FRQ_OCT = 9.9658;                // the curve axis 20 Hz .. 20 kHz in octaves
const FRQ_AXIS = [[20, "20"], [50, "50"], [100, "100"], [200, "200"], [500, "500"], [1000, "1k"], [2000, "2k"], [5000, "5k"], [10000, "10k"], [20000, "20k"]];
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

const MOD_SRC_SHORT = n => n >= 1 && n <= 10 ? "LFO " + n : n >= 11 && n <= 20 ? "ENV " + (n - 10) : ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "VEL", "KEY", "RND"][n] || (n >= 24 && n <= 33 ? "FRQ " + (n - 23) : n >= 34 && n <= 43 ? "SEQ " + (n - 33) : "");
const MOD_SRC_COLOR = n => n >= 1 && n <= 10 ? "#ff6a4d" : n >= 11 && n <= 20 ? "#4db8ff" : n >= 34 ? "#5be08a" : n >= 24 ? "#b57bff" : "#c9c24a";


const SPECS = (() => {
    const L = [
        [2,  "Voice",        0, 1, 0, "", "btn", ["Poly", "Mono"]],
        [4,  "Legato",       0, 1, 1, "", "btn", ["Off", "On"]],
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
        L.push([247 + 2 * i, "LFO " + (i + 1) + " Wave", 0, 7, 0, "", "btn", MOD_WAVES]);
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
    for (let i = 0; i < 10; i++) {   // Freq modulators: rate, transpose, retrig, loop
        const b = FRQ_BASE + 4 * i;
        L.push([b,     "Freq " + (i + 1) + " Rate",      5, 10000, 300, "ms", "sld"]);
        L.push([b + 1, "Freq " + (i + 1) + " Transpose", -48, 48, 0, "st", "sld"]);
        L.push([b + 2, "Freq " + (i + 1) + " Retrig",    0, 1, 1, "", "btn", ["Off", "On"]]);
        L.push([b + 3, "Freq " + (i + 1) + " Loop",      0, 1, 0, "", "btn", ["Off", "On"]]);
    }
    for (let i = 0; i < MOD_SLOTS_MAX; i++) {
        const b = slotBase(i);
        L.push([b,     "Slot " + (i + 1) + " Source", 0, 52, 0, "", "sel", MOD_SRC, 10, "", MOD_SRC_GROUPS]);
        L.push([b + 1, "Slot " + (i + 1) + " Dest",   0, MOD_DST.length - 1, 0, "", "sel", MOD_DST, 5, "", MOD_DST_GROUPS]);
        L.push([b + 2, "Slot " + (i + 1) + " Amount", -4, 4, 0, "", "sld"]);
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
            L.push([b,     n + " Type", 0, FX_TYPES.length - 1, 0, "", "sel", FX_TYPES.map(t => t.n), 1, "Type"]);
            L.push([b + 1, n + " On",   0, 1, 1, "", "btn", ["Off", "On"], 1, "On"]);
            L.push([b + 2, n + " Mix",  0, 1, 1, "", "sld", null, 1, "Mix"]);
            L.push([b + 3, n + " Mode", 0, FX_FILTER_TYPES.length - 1, 0, "", "sel", FX_FILTER_TYPES, 1, "Mode"]);
            for (let k = 0; k < 6; k++) L.push([b + 4 + k, n + " P" + (k + 1), 0, 1, 0.5, "", "sld", null, 1, "P" + (k + 1)]);
        }
        for (let k = 0; k < 10; k++) L.push([rack.ord + k, rack.name + " FX Order " + (k + 1), 0, 15, k, "", "stp", null, 1, "Order"]);
    });
    // FX-SLOTS: slots 11-16 of every rack (global slots 30..47): parameters 3200 + (rk * 6 + j) * 10, order 3380 + rk * 6 + j, sync 3400 + rk * 6 + j
    // (the web UI shows slots 1-10 only; the native editor and the DSP have 16 per rack)
    FX_RACKS.forEach((rack, rk) => {
        for (let j = 0; j < 6; j++) {
            const b = 3200 + (rk * 6 + j) * 10, n = rack.name + " FX " + (11 + j);
            L.push([b,     n + " Type", 0, FX_TYPES.length - 1, 0, "", "sel", FX_TYPES.map(t => t.n), 1, "Type"]);
            L.push([b + 1, n + " On",   0, 1, 1, "", "btn", ["Off", "On"], 1, "On"]);
            L.push([b + 2, n + " Mix",  0, 1, 1, "", "sld", null, 1, "Mix"]);
            L.push([b + 3, n + " Mode", 0, FX_FILTER_TYPES.length - 1, 0, "", "sel", FX_FILTER_TYPES, 1, "Mode"]);
            for (let k = 0; k < 6; k++) L.push([b + 4 + k, n + " P" + (k + 1), 0, 1, 0.5, "", "sld", null, 1, "P" + (k + 1)]);
            L.push([3380 + rk * 6 + j, rack.name + " FX Order " + (11 + j), 0, 15, 10 + j, "", "stp", null, 1, "Order"]);
            L.push([3400 + rk * 6 + j, n + " Sync", 0, 18, 0, "", "sel", ["Off"].concat(SYNC_DIVS), 1, "Sync"]);
        }
    });
    // tempo sync of the effect slots: 0 = free, 1.. = the division (the Rate / Time knob is ignored while it is on)
    // OSCFX4-DSP: oscillator FX racks: ids 8000 + 272 * osc + 16 * slot + k, order 8000 + 272 * osc + 256 + pos
    for (let o = 0; o < 6; o++) {
        for (let sl = 0; sl < 16; sl++) {
            const b = 8000 + 272 * o + 16 * sl, n = "OSC " + (o + 1) + " FX " + (sl + 1);
            L.push([b,     n + " Type", 0, FX_TYPES.length - 1, 0, "", "sel", FX_TYPES.map(t => t.n), 1, "Type"]);
            L.push([b + 1, n + " On",   0, 1, 1, "", "btn", ["Off", "On"], 1, "On"]);
            L.push([b + 2, n + " Mix",  0, 1, 1, "", "sld", null, 1, "Mix"]);
            L.push([b + 3, n + " Mode", 0, FX_FILTER_TYPES.length - 1, 0, "", "sel", FX_FILTER_TYPES, 1, "Mode"]);
            for (let k = 0; k < 6; k++) L.push([b + 4 + k, n + " P" + (k + 1), 0, 1, 0.5, "", "sld", null, 1, "P" + (k + 1)]);
            L.push([b + 10, n + " Sync", 0, 18, 0, "", "sel", ["Off"].concat(SYNC_DIVS), 1, "Sync"]);
            L.push([b + 11, n + " Env Sustain", 0, 1, 1, "", "sld", null, 1, "Sustain"]);
            L.push([b + 12, n + " Env Release", 0, 1, 0.3, "", "sld", null, 1, "Release"]);
        }
        for (let k = 0; k < 16; k++) L.push([8000 + 272 * o + 256 + k, "OSC " + (o + 1) + " FX Order " + (k + 1), 0, 15, k, "", "stp", null, 1, "Order"]);
    }
    L.push([9890, "FX Monitor (editor: 0 = none, 1 + slot)", 0, 48, 0, "", "stp", null, 1, "Monitor"]);   // FX-VIZ
    // FX-WET: P7..P10 of every effect slot: ids 11000 + 4 * g + k (g = global slot: 0..47 racks, 48 + 16 * osc + slot for the oscillator racks)
    const wetName = g => g < 30 ? FX_RACKS[Math.floor(g / 10)].name + " FX " + (g % 10 + 1) : g < 48 ? FX_RACKS[Math.floor((g - 30) / 6)].name + " FX " + (11 + (g - 30) % 6) : "OSC " + (Math.floor((g - 48) / 16) + 1) + " FX " + ((g - 48) % 16 + 1);
    for (let g = 0; g < 144; g++) [["Low Cut", 0], ["High Cut", 1], ["Width", 0.5], ["Sat", 0]].forEach((w, k) => L.push([11000 + 4 * g + k, wetName(g) + " " + w[0], 0, 1, w[1], "", "sld", null, 1, w[0]]));
    L.push([11600, "Out Limiter", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Limiter"]);   // MASTER-OUT
    L.push([11601, "Out Ceiling", -6, 0, -0.3, "dB", "sld", null, 1, "Ceiling"]);
    // FX-EX: effect specific extra parameters, ids 11700 + 4 * g + k (g like FX-WET); the meaning follows the effect type (native_ui/NjoFxEx.h)
    for (let g = 0; g < 144; g++) for (let k = 0; k < 4; k++) L.push([11700 + 4 * g + k, wetName(g) + " Ext " + (k + 1), 0, 1, 0, "", "sld", null, 1, "Ext " + (k + 1)]);
    // EURO: Eurorack rack of Njohrr Modular
    {
        const ESRC = ["Off", "Synth L", "Synth R", "Audio In L", "Audio In R"];
        for (let m = 0; m < 20; m++) ESRC.push("M" + (m + 1) + " A", "M" + (m + 1) + " B");
        const ETYPE = ["Empty", "MIDI-CV", "VCO", "LFO", "ADSR", "VCF", "VCA", "Mixer", "Noise", "S&H", "Sequencer", "Clock", "Attenuverter", "Slew", "Folder", "FX", "Output", "Ring Mod"];
        for (let m = 0; m < 20; m++) {
            const b = 10000 + 32 * m, n = "Euro M" + (m + 1);
            L.push([b, n + " Type", 0, 17, 0, "", "sel", ETYPE, 1, "Type"]);
            for (let k = 0; k < 8; k++) L.push([b + 1 + k, n + " Knob " + (k + 1), 0, 1, 0.5, "", "sld", null, 1, "K" + (k + 1)]);
            L.push([b + 9, n + " Mode", 0, 7, 0, "", "sel", ["1", "2", "3", "4", "5", "6", "7", "8"], 1, "Mode"]);
            for (let c = 0; c < 4; c++) {
                L.push([b + 10 + c, n + " In " + (c + 1) + " Src", 0, 44, 0, "", "sel", ESRC, 1, "Src"]);
                L.push([b + 14 + c, n + " In " + (c + 1) + " Gain", 0, 2, 1, "", "sld", null, 1, "Gain"]);
            }
            L.push([b + 18, n + " FX Type", 0, FX_TYPES.length - 1, 0, "", "sel", FX_TYPES.map(t => t.n), 1, "FX"]);
        }
    }
    // MODMAT: patch matrix of Njohrr Modular
    {
        const MSRC = ["Off", "Synth", "Audio In"].concat(Array.from({ length: 16 }, (_, i) => "Module " + (i + 1)));
        const MPOS = [[0.0, 0.2], [0.0, 0.7], [0.2, 0.08], [0.4, 0.08], [0.6, 0.08], [0.8, 0.08], [0.2, 0.32], [0.4, 0.32], [0.6, 0.32], [0.8, 0.32], [0.2, 0.56], [0.4, 0.56], [0.6, 0.56], [0.8, 0.56], [0.2, 0.8], [0.4, 0.8], [0.6, 0.8], [0.8, 0.8], [1.0, 0.45]];
        for (let d = 0; d < 17; d++) for (let c = 0; c < 4; c++) {
            const nm = d === 16 ? "Out" : "M" + (d + 1), i = 9700 + 8 * d + 2 * c;
            L.push([i,     "Patch " + nm + " Cable " + (c + 1) + " Src", 0, 18, d === 16 && c < 2 ? c + 1 : 0, "", "sel", MSRC, 1, "Src"]);
            L.push([i + 1, "Patch " + nm + " Cable " + (c + 1) + " Gain", 0, 2, 1, "", "sld", null, 1, "Gain"]);
        }
        for (let n = 0; n < 19; n++) for (let a = 0; a < 2; a++)
            L.push([9850 + 2 * n + a, "Patch Node " + (n + 1) + " " + "XY"[a], 0, 1, MPOS[n][a], "", "sld", null, 1, "XY"[a]]);
    }
    FX_RACKS.forEach((rack, rk) => { for (let sl = 0; sl < 10; sl++) L.push([940 + rk * 10 + sl, rack.name + " FX " + (sl + 1) + " Sync", 0, 18, 0, "", "sel", ["Off"].concat(SYNC_DIVS), 1, "Sync"]); });
    // ADSR of the Filter effect: Sustain and Release (ids 3000+g / 3030+g); Env Amt, Attack and Decay are P4..P6
    FX_RACKS.forEach((rack, rk) => { for (let sl = 0; sl < 10; sl++) { L.push([3000 + rk * 10 + sl, rack.name + " FX " + (sl + 1) + " Env Sustain", 0, 1, 1, "", "sld", null, 1, "Sustain"]); L.push([3030 + rk * 10 + sl, rack.name + " FX " + (sl + 1) + " Env Release", 0, 1, 0.3, "", "sld", null, 1, "Release"]); } });
    // MOD-BIP: Bipolar switch of every envelope (3100 + i) and of Velocity (3110): Unipolar 0..1 / Bipolar -1..1
    for (let i = 0; i < 10; i++) L.push([3100 + i, "Env " + (i + 1) + " Polarity", 0, 1, 0, "", "btn", ["Unipolar", "Bipolar"], 1, "Polarity", null]);
    L.push([3110, "Velocity Polarity", 0, 1, 0, "", "btn", ["Unipolar", "Bipolar"], 1, "Velocity Polarity", null]);
    // MOD-ARP: arpeggiator, ids 3920..3927
    L.push([3920, "Arp On",       0, 1, 0, "", "btn", ["Off", "On"], 1, "Arp"]);
    L.push([3921, "Arp Mode",     0, 14, 0, "", "sel", ["Up", "Down", "Up / Down", "Random", "As played", "303", "Euclid / Poly", "Melodic", "Generative", "Galton", "Bounce", "Cellular", "Plinko", "Hanenbow", "Luminaria"], 1, "Mode"]);
    L.push([3922, "Arp Octaves",  1, 4, 1, "", "stp", null, 1, "Octaves"]);
    L.push([3923, "Arp Sync",     0, 1, 1, "", "btn", ["Free", "Sync"], 1, "Sync"]);
    L.push([3924, "Arp Division", 0, 17, 11, "", "sel", SYNC_DIVS, 1, "Division"]);
    L.push([3925, "Arp Rate",     0.25, 30, 6, "Hz", "sld", null, 1, "Rate"]);
    L.push([3926, "Arp Gate",     0.05, 1, 0.6, "", "sld", null, 1, "Gate"]);
    L.push([3927, "Arp Latch",    0, 1, 0, "", "btn", ["Off", "On"], 1, "Latch"]);
    L.push([3928, "Seq Monitor (editor: 0 = none, 1-10 = sequencer shown)", 0, 10, 0, "", "stp", null, 1, "Monitor"]);   // MOD-SEQ3
    L.push([3929, "Seq Key Start (1 = the sequencers only run while a note sounds)", 0, 1, 1, "", "btn", ["Free", "Key"], 1, "Start"]);   // MOD-SEQ4
    // MOD-ARP303: 303 pattern of the arpeggiator
    {
        const N = [0, 0, 12, 0, 0, 10, 0, 7, 0, 12, 0, 0, 3, 5, 0, 0], AC = [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0], SL = [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0], GT = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0];
        for (let k = 0; k < 16; k++) {
            L.push([5200 + k, "303 Step " + (k + 1) + " Note",   -12, 24, N[k], "st", "stp", null, 1, "Note"]);
            L.push([5216 + k, "303 Step " + (k + 1) + " Accent", 0, 1, AC[k], "", "btn", ["Off", "On"], 1, "Accent"]);
            L.push([5232 + k, "303 Step " + (k + 1) + " Slide",  0, 1, SL[k], "", "btn", ["Off", "On"], 1, "Slide"]);
            L.push([5248 + k, "303 Step " + (k + 1) + " Gate",   0, 1, GT[k], "", "btn", ["Off", "On"], 1, "Gate"]);
        }
        // MOD-ARP64: steps 17-64 (repeat of the default pattern)
        [[5500, "Note", -12, 24, N, "st", "stp", null], [5548, "Accent", 0, 1, AC, "", "btn", ["Off", "On"]], [5596, "Slide", 0, 1, SL, "", "btn", ["Off", "On"]], [5644, "Gate", 0, 1, GT, "", "btn", ["Off", "On"]]].forEach(r => {
            for (let k = 16; k < 64; k++) L.push([r[0] + k - 16, "303 Step " + (k + 1) + " " + r[1], r[2], r[3], r[4][k % 16], r[5], r[6], r[7], 1, r[1]]);
        });
        L.push([5264, "303 Length", 1, 64, 16, "", "stp", null, 1, "Length"]);
    }
    // MOD-SQM: Euclid / Poly (4 lanes), Generative and Melodic modes of the arpeggiator
    {
        const LANES = [[1, 16, 5, 0, 0], [0, 12, 3, 0, 7], [0, 7, 2, 0, 12], [0, 5, 1, 0, -12]];
        for (let l = 0; l < 4; l++) {
            const b = 5710 + 8 * l, n = "Euclid Lane " + (l + 1) + " ", q = LANES[l];
            L.push([b,     n + "On",          0, 1, q[0], "", "btn", ["Off", "On"], 1, "On"]);
            L.push([b + 1, n + "Steps",       1, 64, q[1], "", "knb", null, 1, "Steps"]);
            L.push([b + 2, n + "Pulses",      0, 64, q[2], "", "knb", null, 1, "Pulses"]);
            L.push([b + 3, n + "Rotation",    0, 63, q[3], "", "knb", null, 1, "Rotation"]);
            L.push([b + 4, n + "Offset",      -24, 24, q[4], "st", "knb", null, 1, "Offset"]);
            L.push([b + 5, n + "Probability", 0, 100, 100, "%", "knb", null, 1, "Prob"]);
            L.push([b + 6, n + "Ratchet",     1, 4, 1, "", "knb", null, 1, "Ratchet"]);
        }
        const SCALES = ["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"];
        L.push([5750, "Generative Type",     0, 1, 0, "", "sel", ["Turing Machine", "Random Walk"], 1, "Type"]);
        L.push([5751, "Generative Scale",    0, 11, 2, "", "sel", SCALES, 1, "Scale"]);
        L.push([5752, "Generative Range",    12, 48, 24, "st", "knb", null, 1, "Range"]);
        L.push([5753, "Generative Shift",    -24, 24, 0, "st", "knb", null, 1, "Shift"]);
        L.push([5754, "Generative Loop",     2, 16, 8, "", "knb", null, 1, "Loop"]);
        L.push([5755, "Generative Mutation", 0, 100, 20, "%", "knb", null, 1, "Mutation"]);
        L.push([5756, "Generative Max Step", 1, 7, 2, "", "knb", null, 1, "Max Step"]);
        L.push([5757, "Generative Bias",     -100, 100, 0, "%", "knb", null, 1, "Bias"]);
        L.push([5758, "Generative Rest",     0, 100, 10, "%", "knb", null, 1, "Rest"]);
        L.push([5759, "Generative Ratchet",  1, 4, 1, "", "knb", null, 1, "Ratchet"]);
        // MOD-PLINKO
        L.push([6300, "Plinko Rows", 2, 12, 8, "", "knb", null, 1, "Rows"]);
        L.push([6301, "Plinko Scale", 0, 11, 9, "", "sel", ["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"], 1, "Scale"]);
        L.push([6302, "Plinko Range", 12, 48, 24, "st", "knb", null, 1, "Range"]);
        L.push([6303, "Plinko Shift", -24, 24, 0, "st", "knb", null, 1, "Shift"]);
        L.push([6304, "Plinko Drop X", -100, 100, 0, "%", "knb", null, 1, "Drop X"]);
        L.push([6305, "Plinko Bias", -100, 100, 0, "%", "knb", null, 1, "Bias"]);
        L.push([6306, "Plinko Momentum", 0, 100, 0, "%", "knb", null, 1, "Momentum"]);
        L.push([6307, "Plinko Balls", 1, 4, 1, "", "knb", null, 1, "Balls"]);
        L.push([6308, "Plinko Gate", 10, 400, 80, "%", "knb", null, 1, "Gate"]);
        L.push([6309, "Plinko Loop", 0, 64, 0, "", "knb", null, 1, "Loop"]);
        L.push([6310, "Plinko Chord", 0, 8, 0, "", "sel", ["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"], 1, "Chord"]);
        L.push([6311, "Plinko Velocity", 1, 127, 100, "", "knb", null, 1, "Velocity"]);
        L.push([6312, "Plinko Rest", 0, 100, 0, "%", "knb", null, 1, "Rest"]);
        L.push([6313, "Plinko Seed", 0, 999, 0, "", "knb", null, 1, "Seed"]);
        L.push([6314, "Plinko Vel Spread", 0, 100, 20, "%", "knb", null, 1, "Vel Spread"]);
        L.push([6320, "Bounce Start Gap", 25, 400, 100, "%", "knb", null, 1, "Start Gap"]);
        L.push([6321, "Bounce Decay", 50, 98, 80, "%", "knb", null, 1, "Decay"]);
        L.push([6322, "Bounce Bounces", 2, 16, 8, "", "knb", null, 1, "Bounces"]);
        L.push([6323, "Bounce Pitch Step", -4, 4, 1, "", "knb", null, 1, "Pitch Step"]);
        L.push([6324, "Bounce Scale", 0, 11, 2, "", "sel", ["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"], 1, "Scale"]);
        L.push([6325, "Bounce Range", 12, 48, 24, "st", "knb", null, 1, "Range"]);
        L.push([6326, "Bounce Shift", -24, 24, 0, "st", "knb", null, 1, "Shift"]);
        L.push([6327, "Bounce Vel Decay", 50, 100, 85, "%", "knb", null, 1, "Vel Decay"]);
        L.push([6328, "Bounce Pause", 0, 8, 1, "", "knb", null, 1, "Pause"]);
        L.push([6329, "Bounce Gate", 10, 100, 60, "%", "knb", null, 1, "Gate"]);
        L.push([6330, "Bounce Chord", 0, 8, 0, "", "sel", ["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"], 1, "Chord"]);
        L.push([6331, "Bounce Velocity", 1, 127, 100, "", "knb", null, 1, "Velocity"]);
        L.push([6332, "Bounce Rest", 0, 100, 0, "%", "knb", null, 1, "Rest"]);
        L.push([6333, "Bounce Direction", 0, 2, 0, "", "sel", ["Up", "Down", "Ping Pong"], 1, "Direction"]);
        L.push([6340, "Cellular Rule", 0, 255, 90, "", "knb", null, 1, "Rule"]);
        L.push([6341, "Cellular Cells", 4, 16, 8, "", "knb", null, 1, "Cells"]);
        L.push([6342, "Cellular Scale", 0, 11, 2, "", "sel", ["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"], 1, "Scale"]);
        L.push([6343, "Cellular Range", 12, 48, 24, "st", "knb", null, 1, "Range"]);
        L.push([6344, "Cellular Shift", -24, 24, 0, "st", "knb", null, 1, "Shift"]);
        L.push([6345, "Cellular Mutation", 0, 100, 5, "%", "knb", null, 1, "Mutation"]);
        L.push([6346, "Cellular Gate", 10, 400, 70, "%", "knb", null, 1, "Gate"]);
        L.push([6347, "Cellular Velocity", 1, 127, 100, "", "knb", null, 1, "Velocity"]);
        L.push([6348, "Cellular Max Notes", 1, 8, 3, "", "knb", null, 1, "Max Notes"]);
        L.push([6349, "Cellular Rest", 0, 100, 0, "%", "knb", null, 1, "Rest"]);
        L.push([6350, "Cellular Every", 1, 4, 1, "", "knb", null, 1, "Every"]);
        L.push([6351, "Cellular Chord", 0, 8, 0, "", "sel", ["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"], 1, "Chord"]);
        // MOD-PLKP
        L.push([6360, "Plinko Balls", 1, 8, 3, "", "knb", null, 1, "Balls"]);
        L.push([6361, "Plinko Speed", 25, 300, 100, "%", "knb", null, 1, "Speed"]);
        L.push([6362, "Plinko Bounce", 20, 110, 75, "%", "knb", null, 1, "Bounce"]);
        L.push([6363, "Plinko Sway", 0, 100, 0, "%", "knb", null, 1, "Sway"]);
        L.push([6364, "Plinko Gravity", 20, 300, 100, "%", "knb", null, 1, "Gravity"]);
        L.push([6365, "Plinko Scale", 0, 11, 9, "", "sel", ["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"], 1, "Scale"]);
        L.push([6366, "Plinko Range", 12, 48, 24, "st", "knb", null, 1, "Range"]);
        L.push([6367, "Plinko Shift", -24, 24, 0, "st", "knb", null, 1, "Shift"]);
        L.push([6368, "Plinko Gate", 10, 400, 60, "%", "knb", null, 1, "Gate"]);
        L.push([6369, "Plinko Velocity", 1, 127, 100, "", "knb", null, 1, "Velocity"]);
        L.push([6370, "Plinko Chord", 0, 8, 0, "", "sel", ["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"], 1, "Chord"]);
        L.push([6371, "Plinko Rest", 0, 100, 0, "%", "knb", null, 1, "Rest"]);
        L.push([6372, "Plinko Drop X", 0, 100, 50, "%", "knb", null, 1, "Drop X"]);
        L.push([6373, "Plinko Spread", 0, 100, 20, "%", "knb", null, 1, "Spread"]);
        L.push([6374, "Plinko Size", 5, 30, 12, "", "knb", null, 1, "Size"]);
        L.push([6400, "Plinko Obstacle 1 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6401, "Plinko Obstacle 1 X1", 0, 1, 0.36, "", "knb", null, 1, "X1"]);
        L.push([6402, "Plinko Obstacle 1 Y1", 0, 1, 0.22, "", "knb", null, 1, "Y1"]);
        L.push([6403, "Plinko Obstacle 1 X2", 0, 1, 0.36, "", "knb", null, 1, "X2"]);
        L.push([6404, "Plinko Obstacle 1 Y2", 0, 1, 0.22, "", "knb", null, 1, "Y2"]);
        L.push([6405, "Plinko Obstacle 1 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6406, "Plinko Obstacle 2 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6407, "Plinko Obstacle 2 X1", 0, 1, 0.5, "", "knb", null, 1, "X1"]);
        L.push([6408, "Plinko Obstacle 2 Y1", 0, 1, 0.22, "", "knb", null, 1, "Y1"]);
        L.push([6409, "Plinko Obstacle 2 X2", 0, 1, 0.5, "", "knb", null, 1, "X2"]);
        L.push([6410, "Plinko Obstacle 2 Y2", 0, 1, 0.22, "", "knb", null, 1, "Y2"]);
        L.push([6411, "Plinko Obstacle 2 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6412, "Plinko Obstacle 3 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6413, "Plinko Obstacle 3 X1", 0, 1, 0.64, "", "knb", null, 1, "X1"]);
        L.push([6414, "Plinko Obstacle 3 Y1", 0, 1, 0.22, "", "knb", null, 1, "Y1"]);
        L.push([6415, "Plinko Obstacle 3 X2", 0, 1, 0.64, "", "knb", null, 1, "X2"]);
        L.push([6416, "Plinko Obstacle 3 Y2", 0, 1, 0.22, "", "knb", null, 1, "Y2"]);
        L.push([6417, "Plinko Obstacle 3 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6418, "Plinko Obstacle 4 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6419, "Plinko Obstacle 4 X1", 0, 1, 0.29, "", "knb", null, 1, "X1"]);
        L.push([6420, "Plinko Obstacle 4 Y1", 0, 1, 0.33999999999999997, "", "knb", null, 1, "Y1"]);
        L.push([6421, "Plinko Obstacle 4 X2", 0, 1, 0.29, "", "knb", null, 1, "X2"]);
        L.push([6422, "Plinko Obstacle 4 Y2", 0, 1, 0.33999999999999997, "", "knb", null, 1, "Y2"]);
        L.push([6423, "Plinko Obstacle 4 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6424, "Plinko Obstacle 5 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6425, "Plinko Obstacle 5 X1", 0, 1, 0.43, "", "knb", null, 1, "X1"]);
        L.push([6426, "Plinko Obstacle 5 Y1", 0, 1, 0.33999999999999997, "", "knb", null, 1, "Y1"]);
        L.push([6427, "Plinko Obstacle 5 X2", 0, 1, 0.43, "", "knb", null, 1, "X2"]);
        L.push([6428, "Plinko Obstacle 5 Y2", 0, 1, 0.33999999999999997, "", "knb", null, 1, "Y2"]);
        L.push([6429, "Plinko Obstacle 5 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6430, "Plinko Obstacle 6 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6431, "Plinko Obstacle 6 X1", 0, 1, 0.5700000000000001, "", "knb", null, 1, "X1"]);
        L.push([6432, "Plinko Obstacle 6 Y1", 0, 1, 0.33999999999999997, "", "knb", null, 1, "Y1"]);
        L.push([6433, "Plinko Obstacle 6 X2", 0, 1, 0.5700000000000001, "", "knb", null, 1, "X2"]);
        L.push([6434, "Plinko Obstacle 6 Y2", 0, 1, 0.33999999999999997, "", "knb", null, 1, "Y2"]);
        L.push([6435, "Plinko Obstacle 6 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6436, "Plinko Obstacle 7 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6437, "Plinko Obstacle 7 X1", 0, 1, 0.71, "", "knb", null, 1, "X1"]);
        L.push([6438, "Plinko Obstacle 7 Y1", 0, 1, 0.33999999999999997, "", "knb", null, 1, "Y1"]);
        L.push([6439, "Plinko Obstacle 7 X2", 0, 1, 0.71, "", "knb", null, 1, "X2"]);
        L.push([6440, "Plinko Obstacle 7 Y2", 0, 1, 0.33999999999999997, "", "knb", null, 1, "Y2"]);
        L.push([6441, "Plinko Obstacle 7 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6442, "Plinko Obstacle 8 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6443, "Plinko Obstacle 8 X1", 0, 1, 0.21999999999999997, "", "knb", null, 1, "X1"]);
        L.push([6444, "Plinko Obstacle 8 Y1", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y1"]);
        L.push([6445, "Plinko Obstacle 8 X2", 0, 1, 0.21999999999999997, "", "knb", null, 1, "X2"]);
        L.push([6446, "Plinko Obstacle 8 Y2", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y2"]);
        L.push([6447, "Plinko Obstacle 8 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6448, "Plinko Obstacle 9 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6449, "Plinko Obstacle 9 X1", 0, 1, 0.36, "", "knb", null, 1, "X1"]);
        L.push([6450, "Plinko Obstacle 9 Y1", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y1"]);
        L.push([6451, "Plinko Obstacle 9 X2", 0, 1, 0.36, "", "knb", null, 1, "X2"]);
        L.push([6452, "Plinko Obstacle 9 Y2", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y2"]);
        L.push([6453, "Plinko Obstacle 9 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6454, "Plinko Obstacle 10 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6455, "Plinko Obstacle 10 X1", 0, 1, 0.5, "", "knb", null, 1, "X1"]);
        L.push([6456, "Plinko Obstacle 10 Y1", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y1"]);
        L.push([6457, "Plinko Obstacle 10 X2", 0, 1, 0.5, "", "knb", null, 1, "X2"]);
        L.push([6458, "Plinko Obstacle 10 Y2", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y2"]);
        L.push([6459, "Plinko Obstacle 10 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6460, "Plinko Obstacle 11 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6461, "Plinko Obstacle 11 X1", 0, 1, 0.64, "", "knb", null, 1, "X1"]);
        L.push([6462, "Plinko Obstacle 11 Y1", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y1"]);
        L.push([6463, "Plinko Obstacle 11 X2", 0, 1, 0.64, "", "knb", null, 1, "X2"]);
        L.push([6464, "Plinko Obstacle 11 Y2", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y2"]);
        L.push([6465, "Plinko Obstacle 11 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6466, "Plinko Obstacle 12 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6467, "Plinko Obstacle 12 X1", 0, 1, 0.78, "", "knb", null, 1, "X1"]);
        L.push([6468, "Plinko Obstacle 12 Y1", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y1"]);
        L.push([6469, "Plinko Obstacle 12 X2", 0, 1, 0.78, "", "knb", null, 1, "X2"]);
        L.push([6470, "Plinko Obstacle 12 Y2", 0, 1, 0.45999999999999996, "", "knb", null, 1, "Y2"]);
        L.push([6471, "Plinko Obstacle 12 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6472, "Plinko Obstacle 13 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6473, "Plinko Obstacle 13 X1", 0, 1, 0.14999999999999997, "", "knb", null, 1, "X1"]);
        L.push([6474, "Plinko Obstacle 13 Y1", 0, 1, 0.58, "", "knb", null, 1, "Y1"]);
        L.push([6475, "Plinko Obstacle 13 X2", 0, 1, 0.14999999999999997, "", "knb", null, 1, "X2"]);
        L.push([6476, "Plinko Obstacle 13 Y2", 0, 1, 0.58, "", "knb", null, 1, "Y2"]);
        L.push([6477, "Plinko Obstacle 13 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6478, "Plinko Obstacle 14 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6479, "Plinko Obstacle 14 X1", 0, 1, 0.29, "", "knb", null, 1, "X1"]);
        L.push([6480, "Plinko Obstacle 14 Y1", 0, 1, 0.58, "", "knb", null, 1, "Y1"]);
        L.push([6481, "Plinko Obstacle 14 X2", 0, 1, 0.29, "", "knb", null, 1, "X2"]);
        L.push([6482, "Plinko Obstacle 14 Y2", 0, 1, 0.58, "", "knb", null, 1, "Y2"]);
        L.push([6483, "Plinko Obstacle 14 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6484, "Plinko Obstacle 15 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6485, "Plinko Obstacle 15 X1", 0, 1, 0.43, "", "knb", null, 1, "X1"]);
        L.push([6486, "Plinko Obstacle 15 Y1", 0, 1, 0.58, "", "knb", null, 1, "Y1"]);
        L.push([6487, "Plinko Obstacle 15 X2", 0, 1, 0.43, "", "knb", null, 1, "X2"]);
        L.push([6488, "Plinko Obstacle 15 Y2", 0, 1, 0.58, "", "knb", null, 1, "Y2"]);
        L.push([6489, "Plinko Obstacle 15 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6490, "Plinko Obstacle 16 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6491, "Plinko Obstacle 16 X1", 0, 1, 0.5700000000000001, "", "knb", null, 1, "X1"]);
        L.push([6492, "Plinko Obstacle 16 Y1", 0, 1, 0.58, "", "knb", null, 1, "Y1"]);
        L.push([6493, "Plinko Obstacle 16 X2", 0, 1, 0.5700000000000001, "", "knb", null, 1, "X2"]);
        L.push([6494, "Plinko Obstacle 16 Y2", 0, 1, 0.58, "", "knb", null, 1, "Y2"]);
        L.push([6495, "Plinko Obstacle 16 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6496, "Plinko Obstacle 17 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6497, "Plinko Obstacle 17 X1", 0, 1, 0.71, "", "knb", null, 1, "X1"]);
        L.push([6498, "Plinko Obstacle 17 Y1", 0, 1, 0.58, "", "knb", null, 1, "Y1"]);
        L.push([6499, "Plinko Obstacle 17 X2", 0, 1, 0.71, "", "knb", null, 1, "X2"]);
        L.push([6500, "Plinko Obstacle 17 Y2", 0, 1, 0.58, "", "knb", null, 1, "Y2"]);
        L.push([6501, "Plinko Obstacle 17 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6502, "Plinko Obstacle 18 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6503, "Plinko Obstacle 18 X1", 0, 1, 0.8500000000000001, "", "knb", null, 1, "X1"]);
        L.push([6504, "Plinko Obstacle 18 Y1", 0, 1, 0.58, "", "knb", null, 1, "Y1"]);
        L.push([6505, "Plinko Obstacle 18 X2", 0, 1, 0.8500000000000001, "", "knb", null, 1, "X2"]);
        L.push([6506, "Plinko Obstacle 18 Y2", 0, 1, 0.58, "", "knb", null, 1, "Y2"]);
        L.push([6507, "Plinko Obstacle 18 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6508, "Plinko Obstacle 19 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6509, "Plinko Obstacle 19 X1", 0, 1, 0.07999999999999996, "", "knb", null, 1, "X1"]);
        L.push([6510, "Plinko Obstacle 19 Y1", 0, 1, 0.7, "", "knb", null, 1, "Y1"]);
        L.push([6511, "Plinko Obstacle 19 X2", 0, 1, 0.07999999999999996, "", "knb", null, 1, "X2"]);
        L.push([6512, "Plinko Obstacle 19 Y2", 0, 1, 0.7, "", "knb", null, 1, "Y2"]);
        L.push([6513, "Plinko Obstacle 19 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6514, "Plinko Obstacle 20 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6515, "Plinko Obstacle 20 X1", 0, 1, 0.21999999999999997, "", "knb", null, 1, "X1"]);
        L.push([6516, "Plinko Obstacle 20 Y1", 0, 1, 0.7, "", "knb", null, 1, "Y1"]);
        L.push([6517, "Plinko Obstacle 20 X2", 0, 1, 0.21999999999999997, "", "knb", null, 1, "X2"]);
        L.push([6518, "Plinko Obstacle 20 Y2", 0, 1, 0.7, "", "knb", null, 1, "Y2"]);
        L.push([6519, "Plinko Obstacle 20 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6520, "Plinko Obstacle 21 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6521, "Plinko Obstacle 21 X1", 0, 1, 0.36, "", "knb", null, 1, "X1"]);
        L.push([6522, "Plinko Obstacle 21 Y1", 0, 1, 0.7, "", "knb", null, 1, "Y1"]);
        L.push([6523, "Plinko Obstacle 21 X2", 0, 1, 0.36, "", "knb", null, 1, "X2"]);
        L.push([6524, "Plinko Obstacle 21 Y2", 0, 1, 0.7, "", "knb", null, 1, "Y2"]);
        L.push([6525, "Plinko Obstacle 21 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6526, "Plinko Obstacle 22 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6527, "Plinko Obstacle 22 X1", 0, 1, 0.5, "", "knb", null, 1, "X1"]);
        L.push([6528, "Plinko Obstacle 22 Y1", 0, 1, 0.7, "", "knb", null, 1, "Y1"]);
        L.push([6529, "Plinko Obstacle 22 X2", 0, 1, 0.5, "", "knb", null, 1, "X2"]);
        L.push([6530, "Plinko Obstacle 22 Y2", 0, 1, 0.7, "", "knb", null, 1, "Y2"]);
        L.push([6531, "Plinko Obstacle 22 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6532, "Plinko Obstacle 23 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6533, "Plinko Obstacle 23 X1", 0, 1, 0.64, "", "knb", null, 1, "X1"]);
        L.push([6534, "Plinko Obstacle 23 Y1", 0, 1, 0.7, "", "knb", null, 1, "Y1"]);
        L.push([6535, "Plinko Obstacle 23 X2", 0, 1, 0.64, "", "knb", null, 1, "X2"]);
        L.push([6536, "Plinko Obstacle 23 Y2", 0, 1, 0.7, "", "knb", null, 1, "Y2"]);
        L.push([6537, "Plinko Obstacle 23 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6538, "Plinko Obstacle 24 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6539, "Plinko Obstacle 24 X1", 0, 1, 0.78, "", "knb", null, 1, "X1"]);
        L.push([6540, "Plinko Obstacle 24 Y1", 0, 1, 0.7, "", "knb", null, 1, "Y1"]);
        L.push([6541, "Plinko Obstacle 24 X2", 0, 1, 0.78, "", "knb", null, 1, "X2"]);
        L.push([6542, "Plinko Obstacle 24 Y2", 0, 1, 0.7, "", "knb", null, 1, "Y2"]);
        L.push([6543, "Plinko Obstacle 24 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6544, "Plinko Obstacle 25 Type", 0, 2, 1, "", "knb", null, 1, "Type"]);
        L.push([6545, "Plinko Obstacle 25 X1", 0, 1, 0.92, "", "knb", null, 1, "X1"]);
        L.push([6546, "Plinko Obstacle 25 Y1", 0, 1, 0.7, "", "knb", null, 1, "Y1"]);
        L.push([6547, "Plinko Obstacle 25 X2", 0, 1, 0.92, "", "knb", null, 1, "X2"]);
        L.push([6548, "Plinko Obstacle 25 Y2", 0, 1, 0.7, "", "knb", null, 1, "Y2"]);
        L.push([6549, "Plinko Obstacle 25 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6550, "Plinko Obstacle 26 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6551, "Plinko Obstacle 26 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6552, "Plinko Obstacle 26 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6553, "Plinko Obstacle 26 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6554, "Plinko Obstacle 26 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6555, "Plinko Obstacle 26 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6556, "Plinko Obstacle 27 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6557, "Plinko Obstacle 27 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6558, "Plinko Obstacle 27 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6559, "Plinko Obstacle 27 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6560, "Plinko Obstacle 27 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6561, "Plinko Obstacle 27 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6562, "Plinko Obstacle 28 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6563, "Plinko Obstacle 28 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6564, "Plinko Obstacle 28 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6565, "Plinko Obstacle 28 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6566, "Plinko Obstacle 28 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6567, "Plinko Obstacle 28 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6568, "Plinko Obstacle 29 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6569, "Plinko Obstacle 29 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6570, "Plinko Obstacle 29 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6571, "Plinko Obstacle 29 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6572, "Plinko Obstacle 29 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6573, "Plinko Obstacle 29 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6574, "Plinko Obstacle 30 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6575, "Plinko Obstacle 30 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6576, "Plinko Obstacle 30 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6577, "Plinko Obstacle 30 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6578, "Plinko Obstacle 30 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6579, "Plinko Obstacle 30 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6580, "Plinko Obstacle 31 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6581, "Plinko Obstacle 31 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6582, "Plinko Obstacle 31 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6583, "Plinko Obstacle 31 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6584, "Plinko Obstacle 31 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6585, "Plinko Obstacle 31 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6586, "Plinko Obstacle 32 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6587, "Plinko Obstacle 32 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6588, "Plinko Obstacle 32 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6589, "Plinko Obstacle 32 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6590, "Plinko Obstacle 32 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6591, "Plinko Obstacle 32 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6592, "Plinko Obstacle 33 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6593, "Plinko Obstacle 33 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6594, "Plinko Obstacle 33 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6595, "Plinko Obstacle 33 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6596, "Plinko Obstacle 33 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6597, "Plinko Obstacle 33 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6598, "Plinko Obstacle 34 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6599, "Plinko Obstacle 34 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6600, "Plinko Obstacle 34 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6601, "Plinko Obstacle 34 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6602, "Plinko Obstacle 34 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6603, "Plinko Obstacle 34 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6604, "Plinko Obstacle 35 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6605, "Plinko Obstacle 35 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6606, "Plinko Obstacle 35 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6607, "Plinko Obstacle 35 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6608, "Plinko Obstacle 35 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6609, "Plinko Obstacle 35 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6610, "Plinko Obstacle 36 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6611, "Plinko Obstacle 36 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6612, "Plinko Obstacle 36 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6613, "Plinko Obstacle 36 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6614, "Plinko Obstacle 36 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6615, "Plinko Obstacle 36 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6616, "Plinko Obstacle 37 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6617, "Plinko Obstacle 37 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6618, "Plinko Obstacle 37 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6619, "Plinko Obstacle 37 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6620, "Plinko Obstacle 37 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6621, "Plinko Obstacle 37 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6622, "Plinko Obstacle 38 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6623, "Plinko Obstacle 38 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6624, "Plinko Obstacle 38 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6625, "Plinko Obstacle 38 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6626, "Plinko Obstacle 38 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6627, "Plinko Obstacle 38 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6628, "Plinko Obstacle 39 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6629, "Plinko Obstacle 39 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6630, "Plinko Obstacle 39 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6631, "Plinko Obstacle 39 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6632, "Plinko Obstacle 39 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6633, "Plinko Obstacle 39 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6634, "Plinko Obstacle 40 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6635, "Plinko Obstacle 40 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6636, "Plinko Obstacle 40 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6637, "Plinko Obstacle 40 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6638, "Plinko Obstacle 40 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6639, "Plinko Obstacle 40 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6640, "Plinko Obstacle 41 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6641, "Plinko Obstacle 41 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6642, "Plinko Obstacle 41 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6643, "Plinko Obstacle 41 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6644, "Plinko Obstacle 41 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6645, "Plinko Obstacle 41 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6646, "Plinko Obstacle 42 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6647, "Plinko Obstacle 42 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6648, "Plinko Obstacle 42 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6649, "Plinko Obstacle 42 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6650, "Plinko Obstacle 42 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6651, "Plinko Obstacle 42 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6652, "Plinko Obstacle 43 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6653, "Plinko Obstacle 43 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6654, "Plinko Obstacle 43 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6655, "Plinko Obstacle 43 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6656, "Plinko Obstacle 43 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6657, "Plinko Obstacle 43 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6658, "Plinko Obstacle 44 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6659, "Plinko Obstacle 44 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6660, "Plinko Obstacle 44 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6661, "Plinko Obstacle 44 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6662, "Plinko Obstacle 44 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6663, "Plinko Obstacle 44 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6664, "Plinko Obstacle 45 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6665, "Plinko Obstacle 45 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6666, "Plinko Obstacle 45 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6667, "Plinko Obstacle 45 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6668, "Plinko Obstacle 45 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6669, "Plinko Obstacle 45 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6670, "Plinko Obstacle 46 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6671, "Plinko Obstacle 46 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6672, "Plinko Obstacle 46 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6673, "Plinko Obstacle 46 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6674, "Plinko Obstacle 46 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6675, "Plinko Obstacle 46 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6676, "Plinko Obstacle 47 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6677, "Plinko Obstacle 47 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6678, "Plinko Obstacle 47 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6679, "Plinko Obstacle 47 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6680, "Plinko Obstacle 47 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6681, "Plinko Obstacle 47 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        L.push([6682, "Plinko Obstacle 48 Type", 0, 2, 0, "", "knb", null, 1, "Type"]);
        L.push([6683, "Plinko Obstacle 48 X1", 0, 1, 0, "", "knb", null, 1, "X1"]);
        L.push([6684, "Plinko Obstacle 48 Y1", 0, 1, 0, "", "knb", null, 1, "Y1"]);
        L.push([6685, "Plinko Obstacle 48 X2", 0, 1, 0, "", "knb", null, 1, "X2"]);
        L.push([6686, "Plinko Obstacle 48 Y2", 0, 1, 0, "", "knb", null, 1, "Y2"]);
        L.push([6687, "Plinko Obstacle 48 Kind", 0, 4, 0, "", "knb", null, 1, "Kind"]);
        // MOD-HBLM
        L.push([6700, "Hanenbow Frogs", 1, 8, 3, "", "knb", null, 1, "Frogs"]);
        L.push([6701, "Hanenbow Speed", 25, 300, 100, "%", "knb", null, 1, "Speed"]);
        L.push([6702, "Hanenbow Gravity", 20, 300, 100, "%", "knb", null, 1, "Gravity"]);
        L.push([6703, "Hanenbow Jump", 40, 200, 120, "%", "knb", null, 1, "Jump"]);
        L.push([6704, "Hanenbow Bounce", 20, 110, 60, "%", "knb", null, 1, "Bounce"]);
        L.push([6705, "Hanenbow Scale", 0, 11, 8, "", "sel", ["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"], 1, "Scale"]);
        L.push([6706, "Hanenbow Range", 12, 48, 24, "st", "knb", null, 1, "Range"]);
        L.push([6707, "Hanenbow Shift", -24, 24, 0, "st", "knb", null, 1, "Shift"]);
        L.push([6708, "Hanenbow Gate", 10, 400, 60, "%", "knb", null, 1, "Gate"]);
        L.push([6709, "Hanenbow Velocity", 1, 127, 100, "", "knb", null, 1, "Velocity"]);
        L.push([6710, "Hanenbow Chord", 0, 8, 0, "", "sel", ["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"], 1, "Chord"]);
        L.push([6711, "Hanenbow Rest", 0, 100, 0, "%", "knb", null, 1, "Rest"]);
        L.push([6712, "Hanenbow Spawn X", 0, 100, 7, "%", "knb", null, 1, "Spawn X"]);
        L.push([6713, "Hanenbow Spread", 0, 100, 5, "%", "knb", null, 1, "Spread"]);
        L.push([6714, "Hanenbow Hits", 1, 8, 2, "", "knb", null, 1, "Hits"]);
        L.push([6715, "Hanenbow Step", -4, 4, 2, "", "knb", null, 1, "Step"]);
        L.push([6716, "Hanenbow Leaf Size", 8, 50, 35, "%", "knb", null, 1, "Leaf Size"]);
        L.push([6717, "Hanenbow Aim", -80, 80, 30, "deg", "knb", null, 1, "Aim"]);
        L.push([6718, "Hanenbow Stem X", 0, 100, 64, "", "knb", null, 1, "Stem X"]);
        L.push([6720, "Hanenbow Leaf 1 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6721, "Hanenbow Leaf 1 X", 0, 1, 0.0, "", "knb", null, 1, "X"]);
        L.push([6722, "Hanenbow Leaf 1 Y", 0, 1, 0.69, "", "knb", null, 1, "Y"]);
        L.push([6723, "Hanenbow Leaf 1 Angle", 0, 1, 0.725, "", "knb", null, 1, "Angle"]);
        L.push([6724, "Hanenbow Leaf 1 Note", 0, 24, 0, "", "knb", null, 1, "Note"]);
        L.push([6725, "Hanenbow Leaf 2 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6726, "Hanenbow Leaf 2 X", 0, 1, 1.0, "", "knb", null, 1, "X"]);
        L.push([6727, "Hanenbow Leaf 2 Y", 0, 1, 0.69, "", "knb", null, 1, "Y"]);
        L.push([6728, "Hanenbow Leaf 2 Angle", 0, 1, 0.725, "", "knb", null, 1, "Angle"]);
        L.push([6729, "Hanenbow Leaf 2 Note", 0, 24, 2, "", "knb", null, 1, "Note"]);
        L.push([6730, "Hanenbow Leaf 3 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6731, "Hanenbow Leaf 3 X", 0, 1, 0.0, "", "knb", null, 1, "X"]);
        L.push([6732, "Hanenbow Leaf 3 Y", 0, 1, 0.5, "", "knb", null, 1, "Y"]);
        L.push([6733, "Hanenbow Leaf 3 Angle", 0, 1, 0.73, "", "knb", null, 1, "Angle"]);
        L.push([6734, "Hanenbow Leaf 3 Note", 0, 24, 4, "", "knb", null, 1, "Note"]);
        L.push([6735, "Hanenbow Leaf 4 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6736, "Hanenbow Leaf 4 X", 0, 1, 1.0, "", "knb", null, 1, "X"]);
        L.push([6737, "Hanenbow Leaf 4 Y", 0, 1, 0.5, "", "knb", null, 1, "Y"]);
        L.push([6738, "Hanenbow Leaf 4 Angle", 0, 1, 0.73, "", "knb", null, 1, "Angle"]);
        L.push([6739, "Hanenbow Leaf 4 Note", 0, 24, 5, "", "knb", null, 1, "Note"]);
        L.push([6740, "Hanenbow Leaf 5 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6741, "Hanenbow Leaf 5 X", 0, 1, 0.0, "", "knb", null, 1, "X"]);
        L.push([6742, "Hanenbow Leaf 5 Y", 0, 1, 0.33, "", "knb", null, 1, "Y"]);
        L.push([6743, "Hanenbow Leaf 5 Angle", 0, 1, 0.84, "", "knb", null, 1, "Angle"]);
        L.push([6744, "Hanenbow Leaf 5 Note", 0, 24, 7, "", "knb", null, 1, "Note"]);
        L.push([6745, "Hanenbow Leaf 6 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6746, "Hanenbow Leaf 6 X", 0, 1, 1.0, "", "knb", null, 1, "X"]);
        L.push([6747, "Hanenbow Leaf 6 Y", 0, 1, 0.33, "", "knb", null, 1, "Y"]);
        L.push([6748, "Hanenbow Leaf 6 Angle", 0, 1, 0.84, "", "knb", null, 1, "Angle"]);
        L.push([6749, "Hanenbow Leaf 6 Note", 0, 24, 9, "", "knb", null, 1, "Note"]);
        L.push([6750, "Hanenbow Leaf 7 On", 0, 1, 0, "", "knb", null, 1, "On"]);
        L.push([6751, "Hanenbow Leaf 7 X", 0, 1, 0.0, "", "knb", null, 1, "X"]);
        L.push([6752, "Hanenbow Leaf 7 Y", 0, 1, 0.2, "", "knb", null, 1, "Y"]);
        L.push([6753, "Hanenbow Leaf 7 Angle", 0, 1, 0.85, "", "knb", null, 1, "Angle"]);
        L.push([6754, "Hanenbow Leaf 7 Note", 0, 24, 3, "", "knb", null, 1, "Note"]);
        L.push([6755, "Hanenbow Leaf 8 On", 0, 1, 0, "", "knb", null, 1, "On"]);
        L.push([6756, "Hanenbow Leaf 8 X", 0, 1, 1.0, "", "knb", null, 1, "X"]);
        L.push([6757, "Hanenbow Leaf 8 Y", 0, 1, 0.2, "", "knb", null, 1, "Y"]);
        L.push([6758, "Hanenbow Leaf 8 Angle", 0, 1, 0.85, "", "knb", null, 1, "Angle"]);
        L.push([6759, "Hanenbow Leaf 8 Note", 0, 24, 6, "", "knb", null, 1, "Note"]);
        L.push([6760, "Luminaria Every", 1, 8, 1, "", "knb", null, 1, "Every"]);
        L.push([6761, "Luminaria Scale", 0, 11, 8, "", "sel", ["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"], 1, "Scale"]);
        L.push([6762, "Luminaria Range", 12, 48, 24, "st", "knb", null, 1, "Range"]);
        L.push([6763, "Luminaria Shift", -24, 24, 0, "st", "knb", null, 1, "Shift"]);
        L.push([6764, "Luminaria Gate", 10, 400, 70, "%", "knb", null, 1, "Gate"]);
        L.push([6765, "Luminaria Velocity", 1, 127, 100, "", "knb", null, 1, "Velocity"]);
        L.push([6766, "Luminaria Chord", 0, 8, 0, "", "sel", ["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"], 1, "Chord"]);
        L.push([6767, "Luminaria Rest", 0, 100, 0, "%", "knb", null, 1, "Rest"]);
        L.push([6768, "Luminaria Rotate", 0, 1, 0, "", "sel", ["Off", "On"], 1, "Rotate"]);
        L.push([6769, "Luminaria Pitch By", 0, 2, 0, "", "sel", ["Column", "Row", "Both"], 1, "Pitch By"]);
        L.push([6770, "Luminaria Wrap", 0, 1, 1, "", "sel", ["Off", "On"], 1, "Wrap"]);
        L.push([6780, "Luminaria Walker 1 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6781, "Luminaria Walker 1 X", 0, 7, 1, "", "knb", null, 1, "X"]);
        L.push([6782, "Luminaria Walker 1 Y", 0, 7, 1, "", "knb", null, 1, "Y"]);
        L.push([6783, "Luminaria Walker 1 Direction", 1, 4, 2, "", "knb", null, 1, "Direction"]);
        L.push([6784, "Luminaria Walker 1 Octave", -2, 2, 0, "", "knb", null, 1, "Octave"]);
        L.push([6785, "Luminaria Walker 2 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6786, "Luminaria Walker 2 X", 0, 7, 3, "", "knb", null, 1, "X"]);
        L.push([6787, "Luminaria Walker 2 Y", 0, 7, 3, "", "knb", null, 1, "Y"]);
        L.push([6788, "Luminaria Walker 2 Direction", 1, 4, 2, "", "knb", null, 1, "Direction"]);
        L.push([6789, "Luminaria Walker 2 Octave", -2, 2, 1, "", "knb", null, 1, "Octave"]);
        L.push([6790, "Luminaria Walker 3 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6791, "Luminaria Walker 3 X", 0, 7, 6, "", "knb", null, 1, "X"]);
        L.push([6792, "Luminaria Walker 3 Y", 0, 7, 6, "", "knb", null, 1, "Y"]);
        L.push([6793, "Luminaria Walker 3 Direction", 1, 4, 4, "", "knb", null, 1, "Direction"]);
        L.push([6794, "Luminaria Walker 3 Octave", -2, 2, 0, "", "knb", null, 1, "Octave"]);
        L.push([6795, "Luminaria Walker 4 On", 0, 1, 1, "", "knb", null, 1, "On"]);
        L.push([6796, "Luminaria Walker 4 X", 0, 7, 5, "", "knb", null, 1, "X"]);
        L.push([6797, "Luminaria Walker 4 Y", 0, 7, 5, "", "knb", null, 1, "Y"]);
        L.push([6798, "Luminaria Walker 4 Direction", 1, 4, 4, "", "knb", null, 1, "Direction"]);
        L.push([6799, "Luminaria Walker 4 Octave", -2, 2, -1, "", "knb", null, 1, "Octave"]);
        L.push([6800, "Luminaria Cell 1", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6801, "Luminaria Cell 2", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6802, "Luminaria Cell 3", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6803, "Luminaria Cell 4", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6804, "Luminaria Cell 5", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6805, "Luminaria Cell 6", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6806, "Luminaria Cell 7", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6807, "Luminaria Cell 8", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6808, "Luminaria Cell 9", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6809, "Luminaria Cell 10", 0, 4, 2, "", "knb", null, 1, "Cell"]);
        L.push([6810, "Luminaria Cell 11", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6811, "Luminaria Cell 12", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6812, "Luminaria Cell 13", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6813, "Luminaria Cell 14", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6814, "Luminaria Cell 15", 0, 4, 3, "", "knb", null, 1, "Cell"]);
        L.push([6815, "Luminaria Cell 16", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6816, "Luminaria Cell 17", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6817, "Luminaria Cell 18", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6818, "Luminaria Cell 19", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6819, "Luminaria Cell 20", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6820, "Luminaria Cell 21", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6821, "Luminaria Cell 22", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6822, "Luminaria Cell 23", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6823, "Luminaria Cell 24", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6824, "Luminaria Cell 25", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6825, "Luminaria Cell 26", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6826, "Luminaria Cell 27", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6827, "Luminaria Cell 28", 0, 4, 2, "", "knb", null, 1, "Cell"]);
        L.push([6828, "Luminaria Cell 29", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6829, "Luminaria Cell 30", 0, 4, 3, "", "knb", null, 1, "Cell"]);
        L.push([6830, "Luminaria Cell 31", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6831, "Luminaria Cell 32", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6832, "Luminaria Cell 33", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6833, "Luminaria Cell 34", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6834, "Luminaria Cell 35", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6835, "Luminaria Cell 36", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6836, "Luminaria Cell 37", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6837, "Luminaria Cell 38", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6838, "Luminaria Cell 39", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6839, "Luminaria Cell 40", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6840, "Luminaria Cell 41", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6841, "Luminaria Cell 42", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6842, "Luminaria Cell 43", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6843, "Luminaria Cell 44", 0, 4, 1, "", "knb", null, 1, "Cell"]);
        L.push([6844, "Luminaria Cell 45", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6845, "Luminaria Cell 46", 0, 4, 4, "", "knb", null, 1, "Cell"]);
        L.push([6846, "Luminaria Cell 47", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6847, "Luminaria Cell 48", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6848, "Luminaria Cell 49", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6849, "Luminaria Cell 50", 0, 4, 1, "", "knb", null, 1, "Cell"]);
        L.push([6850, "Luminaria Cell 51", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6851, "Luminaria Cell 52", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6852, "Luminaria Cell 53", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6853, "Luminaria Cell 54", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6854, "Luminaria Cell 55", 0, 4, 4, "", "knb", null, 1, "Cell"]);
        L.push([6855, "Luminaria Cell 56", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6856, "Luminaria Cell 57", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6857, "Luminaria Cell 58", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6858, "Luminaria Cell 59", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6859, "Luminaria Cell 60", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6860, "Luminaria Cell 61", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6861, "Luminaria Cell 62", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6862, "Luminaria Cell 63", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([6863, "Luminaria Cell 64", 0, 4, 0, "", "knb", null, 1, "Cell"]);
        L.push([5800, "Melodic Length",      1, 64, 16, "", "stp", null, 1, "Length"]);
        const NOTE = [0, 0, 12, 0, 7, 0, 12, 0, 0, 0, 10, 0, 7, 0, 5, 0], GATE = [1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1];
        const CHORDS = ["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"];
        const ROWS = [["Note", -24, 24, i => NOTE[i % 16], "st", "stp", null], ["Velocity", 1, 127, () => 100, "", "stp", null], ["Length", 10, 400, () => 80, "%", "stp", null],
                      ["Chord", 0, 8, () => 0, "", "sel", CHORDS], ["Probability", 0, 100, () => 100, "%", "stp", null], ["Ratchet", 1, 4, () => 1, "", "stp", null], ["Gate", 0, 1, i => GATE[i % 16], "", "btn", ["Off", "On"]]];
        ROWS.forEach((r, ri) => { for (let k = 0; k < 64; k++) L.push([5810 + 64 * ri + k, "Melodic Step " + (k + 1) + " " + r[0], r[1], r[2], r[3](k), r[4], r[5], r[6], 1, r[0]]); });
    }
    // ENV2-BEGIN
    L.push([13300, "Mod Env 1 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13301, "Mod Env 1 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13302, "Mod Env 1 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13303, "Mod Env 1 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13304, "Mod Env 1 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13305, "Mod Env 1 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13306, "Mod Env 1 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13307, "Mod Env 1 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13308, "Mod Env 1 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13316, "Mod Env 2 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13317, "Mod Env 2 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13318, "Mod Env 2 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13319, "Mod Env 2 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13320, "Mod Env 2 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13321, "Mod Env 2 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13322, "Mod Env 2 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13323, "Mod Env 2 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13324, "Mod Env 2 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13332, "Mod Env 3 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13333, "Mod Env 3 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13334, "Mod Env 3 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13335, "Mod Env 3 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13336, "Mod Env 3 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13337, "Mod Env 3 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13338, "Mod Env 3 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13339, "Mod Env 3 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13340, "Mod Env 3 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13348, "Mod Env 4 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13349, "Mod Env 4 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13350, "Mod Env 4 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13351, "Mod Env 4 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13352, "Mod Env 4 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13353, "Mod Env 4 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13354, "Mod Env 4 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13355, "Mod Env 4 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13356, "Mod Env 4 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13364, "Mod Env 5 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13365, "Mod Env 5 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13366, "Mod Env 5 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13367, "Mod Env 5 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13368, "Mod Env 5 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13369, "Mod Env 5 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13370, "Mod Env 5 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13371, "Mod Env 5 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13372, "Mod Env 5 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13380, "Mod Env 6 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13381, "Mod Env 6 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13382, "Mod Env 6 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13383, "Mod Env 6 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13384, "Mod Env 6 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13385, "Mod Env 6 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13386, "Mod Env 6 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13387, "Mod Env 6 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13388, "Mod Env 6 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13396, "Mod Env 7 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13397, "Mod Env 7 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13398, "Mod Env 7 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13399, "Mod Env 7 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13400, "Mod Env 7 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13401, "Mod Env 7 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13402, "Mod Env 7 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13403, "Mod Env 7 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13404, "Mod Env 7 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13412, "Mod Env 8 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13413, "Mod Env 8 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13414, "Mod Env 8 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13415, "Mod Env 8 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13416, "Mod Env 8 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13417, "Mod Env 8 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13418, "Mod Env 8 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13419, "Mod Env 8 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13420, "Mod Env 8 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13428, "Mod Env 9 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13429, "Mod Env 9 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13430, "Mod Env 9 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13431, "Mod Env 9 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13432, "Mod Env 9 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13433, "Mod Env 9 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13434, "Mod Env 9 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13435, "Mod Env 9 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13436, "Mod Env 9 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13444, "Mod Env 10 Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13445, "Mod Env 10 Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13446, "Mod Env 10 Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13447, "Mod Env 10 Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13448, "Mod Env 10 Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13449, "Mod Env 10 Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13450, "Mod Env 10 Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13451, "Mod Env 10 Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13452, "Mod Env 10 Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13460, "Amp Env Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13461, "Amp Env Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13462, "Amp Env Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13463, "Amp Env Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13464, "Amp Env Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13465, "Amp Env Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13466, "Amp Env Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13467, "Amp Env Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13468, "Amp Env Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13476, "OSC 1 Filter Env Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13477, "OSC 1 Filter Env Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13478, "OSC 1 Filter Env Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13479, "OSC 1 Filter Env Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13480, "OSC 1 Filter Env Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13481, "OSC 1 Filter Env Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13482, "OSC 1 Filter Env Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13483, "OSC 1 Filter Env Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13484, "OSC 1 Filter Env Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13492, "OSC 2 Filter Env Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13493, "OSC 2 Filter Env Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13494, "OSC 2 Filter Env Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13495, "OSC 2 Filter Env Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13496, "OSC 2 Filter Env Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13497, "OSC 2 Filter Env Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13498, "OSC 2 Filter Env Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13499, "OSC 2 Filter Env Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13500, "OSC 2 Filter Env Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13508, "OSC 3 Filter Env Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13509, "OSC 3 Filter Env Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13510, "OSC 3 Filter Env Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13511, "OSC 3 Filter Env Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13512, "OSC 3 Filter Env Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13513, "OSC 3 Filter Env Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13514, "OSC 3 Filter Env Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13515, "OSC 3 Filter Env Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13516, "OSC 3 Filter Env Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13524, "OSC 4 Filter Env Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13525, "OSC 4 Filter Env Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13526, "OSC 4 Filter Env Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13527, "OSC 4 Filter Env Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13528, "OSC 4 Filter Env Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13529, "OSC 4 Filter Env Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13530, "OSC 4 Filter Env Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13531, "OSC 4 Filter Env Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13532, "OSC 4 Filter Env Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13540, "OSC 5 Filter Env Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13541, "OSC 5 Filter Env Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13542, "OSC 5 Filter Env Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13543, "OSC 5 Filter Env Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13544, "OSC 5 Filter Env Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13545, "OSC 5 Filter Env Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13546, "OSC 5 Filter Env Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13547, "OSC 5 Filter Env Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13548, "OSC 5 Filter Env Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    L.push([13556, "OSC 6 Filter Env Delay", 0, 5000, 0.0, "ms", "sld", null, 1, "Delay", null]);
    L.push([13557, "OSC 6 Filter Env Hold", 0, 5000, 0.0, "ms", "sld", null, 1, "Hold", null]);
    L.push([13558, "OSC 6 Filter Env Attack Curve", -1, 1, 0.0, "", "sld", null, 1, "A Curve", null]);
    L.push([13559, "OSC 6 Filter Env Decay Curve", -1, 1, 0.0, "", "sld", null, 1, "D Curve", null]);
    L.push([13560, "OSC 6 Filter Env Release Curve", -1, 1, 0.0, "", "sld", null, 1, "R Curve", null]);
    L.push([13561, "OSC 6 Filter Env Velocity", 0, 1, 0.0, "", "sld", null, 1, "Vel", null]);
    L.push([13562, "OSC 6 Filter Env Key Track", -1, 1, 0.0, "", "sld", null, 1, "Key", null]);
    L.push([13563, "OSC 6 Filter Env Loop", 0, 1, 0.0, "", "btn", ["Loop Off", "Loop On"], 1, "Loop", null]);
    L.push([13564, "OSC 6 Filter Env Level", 0, 1, 1.0, "", "sld", null, 1, "Level", null]);
    // ENV2-END
    // LFO2-BEGIN
    L.push([13000, "LFO 1 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13010, "LFO 1 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13011, "LFO 1 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13002, "LFO 1 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13003, "LFO 1 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13004, "LFO 1 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13005, "LFO 1 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13006, "LFO 1 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13007, "LFO 1 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13008, "LFO 1 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13009, "LFO 1 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13016, "LFO 2 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13026, "LFO 2 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13027, "LFO 2 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13018, "LFO 2 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13019, "LFO 2 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13020, "LFO 2 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13021, "LFO 2 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13022, "LFO 2 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13023, "LFO 2 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13024, "LFO 2 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13025, "LFO 2 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13032, "LFO 3 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13042, "LFO 3 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13043, "LFO 3 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13034, "LFO 3 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13035, "LFO 3 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13036, "LFO 3 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13037, "LFO 3 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13038, "LFO 3 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13039, "LFO 3 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13040, "LFO 3 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13041, "LFO 3 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13048, "LFO 4 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13058, "LFO 4 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13059, "LFO 4 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13050, "LFO 4 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13051, "LFO 4 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13052, "LFO 4 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13053, "LFO 4 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13054, "LFO 4 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13055, "LFO 4 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13056, "LFO 4 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13057, "LFO 4 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13064, "LFO 5 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13074, "LFO 5 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13075, "LFO 5 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13066, "LFO 5 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13067, "LFO 5 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13068, "LFO 5 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13069, "LFO 5 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13070, "LFO 5 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13071, "LFO 5 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13072, "LFO 5 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13073, "LFO 5 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13080, "LFO 6 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13090, "LFO 6 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13091, "LFO 6 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13082, "LFO 6 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13083, "LFO 6 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13084, "LFO 6 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13085, "LFO 6 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13086, "LFO 6 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13087, "LFO 6 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13088, "LFO 6 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13089, "LFO 6 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13096, "LFO 7 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13106, "LFO 7 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13107, "LFO 7 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13098, "LFO 7 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13099, "LFO 7 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13100, "LFO 7 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13101, "LFO 7 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13102, "LFO 7 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13103, "LFO 7 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13104, "LFO 7 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13105, "LFO 7 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13112, "LFO 8 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13122, "LFO 8 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13123, "LFO 8 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13114, "LFO 8 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13115, "LFO 8 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13116, "LFO 8 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13117, "LFO 8 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13118, "LFO 8 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13119, "LFO 8 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13120, "LFO 8 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13121, "LFO 8 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13128, "LFO 9 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13138, "LFO 9 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13139, "LFO 9 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13130, "LFO 9 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13131, "LFO 9 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13132, "LFO 9 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13133, "LFO 9 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13134, "LFO 9 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13135, "LFO 9 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13136, "LFO 9 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13137, "LFO 9 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    L.push([13144, "LFO 10 Key Follow", 0, 1, 0.0, "", "btn", ["Key Off", "Key On"], 1, "Key", null]);
    L.push([13154, "LFO 10 Key Octave", 0, 8, 4.0, "", "sel", LFO_OCT, 1, "Octave", null]);
    L.push([13155, "LFO 10 Key Semi", 0, 24, 12.0, "", "sel", LFO_SEMI, 1, "Semi", null]);
    L.push([13146, "LFO 10 Key Fine", -100, 100, 0.0, "ct", "sld", null, 1, "Fine", null]);
    L.push([13147, "LFO 10 Skew", -1, 1, 0.0, "", "sld", null, 1, "Skew", null]);
    L.push([13148, "LFO 10 Steps", 0, 32, 0.0, "", "sel", LFO_STEPS, 1, "Steps", null]);
    L.push([13149, "LFO 10 Jitter", 0, 1, 0.0, "", "sld", null, 1, "Jitter", null]);
    L.push([13150, "LFO 10 Voice Spread", 0, 1, 0.0, "", "sld", null, 1, "Spread", null]);
    L.push([13151, "LFO 10 Depth", 0, 1, 1.0, "", "sld", null, 1, "Depth", null]);
    L.push([13152, "LFO 10 Table Pos", 0, 1, 0.0, "", "sld", null, 1, "Pos", null]);
    L.push([13153, "LFO 10 Interp", 0, 1, 1.0, "", "btn", ["Linear", "Cubic"], 1, "Interp", null]);
    // LFO2-END
    // MOD-LFOBIP: Polarity of every LFO (3111 + i), default Bipolar
    for (let i = 0; i < 10; i++) L.push([3111 + i, "LFO " + (i + 1) + " Polarity", 0, 1, 1, "", "btn", ["Unipolar", "Bipolar"], 1, "Polarity", null]);
    // MOD-SEQ: 10 step sequencers (modulation sources 34..43), ids 3600 + 32 * m + k
    for (let m = 0; m < 10; m++) {
        const b = 3600 + 32 * m, n = "Seq " + (m + 1);
        for (let k = 0; k < 16; k++) L.push([b + k, n + " Step " + (k + 1), 0, 1, [0.5, 1, 0.25, 0.75, 0, 0.6, 0.3, 0.9][k % 8], "", "sld", null, 1, "Step " + (k + 1)]);
        L.push([b + 16, n + " Length",    1, 16, 8, "", "stp", null, 1, "Length"]);
        L.push([b + 17, n + " Rate",      0.05, 40, 4, "Hz", "sld", null, 1, "Rate"]);
        L.push([b + 18, n + " Sync",      0, 2, 0, "", "sel", ["Free", "Sync", "Spos"], 1, "Sync"]);
        L.push([b + 19, n + " Division",  0, 17, 11, "", "sel", SYNC_DIVS, 1, "Division"]);
        L.push([b + 20, n + " Glide",     0, 1, 0, "", "sld", null, 1, "Glide"]);
        L.push([b + 21, n + " Direction", 0, 3, 0, "", "sel", ["Forward", "Backward", "Ping-Pong", "Random"], 1, "Direction"]);
        L.push([b + 22, n + " Retrig",    0, 1, 0, "", "btn", ["Free", "Note"], 1, "Retrig"]);
        L.push([b + 23, n + " Bipolar",    0, 1, 1, "", "btn", ["Unipolar", "Bipolar"], 1, "Polarity"]);
        L.push([b + 24, n + " Time",      0, 3, 0, "", "sel", ["x1", "x2", "x3", "x4"], 1, "Time"]);   // MOD-SEQ2
        L.push([b + 25, n + " Loop",      1, 16, 1, "", "stp", null, 1, "Loop"]);
        L.push([b + 26, n + " Hold",      0, 1, 0, "", "btn", ["Off", "On"], 1, "Hold"]);
        for (let k = 0; k < 16; k++) L.push([5000 + 16 * m + k, n + " Step " + (k + 1) + " Shape", 0, 7, 0, "", "sel", SEQ_SHAPES, 1, "Shape"]);
    }
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
const FX_OUT = [175, 221, 222, 11600, 11601];   // MASTER-OUT: Synth Drive, Drive Algorithm and Tone are gone

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const CHUNK = 256;
const MAX_SMP = 524288;
const MAX_WT = 524288, MAX_WT_FRAMES = 256;   // wavetables: up to 256 frames of 2048 samples (Vital style)
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
    if ((s.num >= FM_BASE && s.num < AM_BASE + 36) || (s.num >= TZ_BASE && s.num < TZ_BASE + 36) || (s.num >= MX_BASE && s.num < MX_BASE + 144)) return Math.round(v) + "%";
    if (s.num >= OSC_BASE && s.num < OSC_BASE + OSC_STRIDE * OSC_N) {
        const k = (s.num - OSC_BASE) % OSC_STRIDE;
        if (k === OSC_K.pan) { const p = Math.round(v * 50); return p === 0 ? "C" : (p < 0 ? "L" + (-p) : "R" + p); }
        if (k === OSC_K.phase) return Math.round(v * 360) + "\u00b0";
        if (k === OSC_K.freq) { if (v < 0.001) return "Off"; const f = 20 * Math.pow(1000, v); return f >= 1000 ? (f / 1000).toFixed(2) + " kHz" : f.toFixed(f < 100 ? 1 : 0) + " Hz"; }
        if (k === OSC_K.root) { const n = Math.round(v); return NOTE_NAMES[n % 12] + (Math.floor(n / 12) - 1); }
        if (k === OSC_K.uvox) { const n = Math.round(v); return n + (n === 1 ? " voice" : " voices"); }
        if (k === OSC_K.udet) return "\u00b1" + Math.round(v * 50) + " ct";
        if (k === OSC_K.semi) return (v > 0 ? "+" : "") + Math.round(v) + " st";
    }
    if (s.labels.length) return s.labels[Math.max(0, Math.min(s.labels.length - 1, Math.round(v - s.min)))];
    if (s.unit === "oct") { const o = Math.round(v); return (o > 0 ? "+" : "") + o + " oct"; }
    if (s.unit === "Hz") return v >= 1000 ? (v / 1000).toFixed(2) + " kHz" : v.toFixed(v < 10 ? 2 : 0) + " Hz";
    if (s.unit === "Hz" && s.num >= PHY_BASE && s.num < PHY_BASE + PHY_STRIDE * OSC_N) return v.toFixed(2) + " Hz";
    if (s.unit === "s") return v.toFixed(v < 10 ? 2 : 1) + " s";
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
        this._mem = { wt: new Array(OSC_N).fill(null), sm: new Array(OSC_N).fill(null), ft: new Array(OSC_N).fill(null), sh: new Array(OSC_N).fill(null) };
        this._memTimer = { wt: new Array(OSC_N).fill(null), sm: new Array(OSC_N).fill(null), ft: new Array(OSC_N).fill(null), sh: new Array(OSC_N).fill(null) };
        this._memStart = [];
        this._oscReady = false;
        this._lfoPts = new Array(10).fill(null);
        this._frqPts = new Array(10).fill(null);
        this._frqSel = 0;
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
        this.buildFmx();
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
            this.restoreFrq();
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
        if (this._page === "fm" || this._page === "rm") this.fmxDraw();
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
        this.querySelectorAll(".rb").forEach(t => {
            t.setAttribute("tabindex", "-1");
            t.addEventListener("click", () => { this.setGroup(t.dataset.group); t.blur(); });
        });
        this.querySelectorAll(".stab").forEach(t => {
            t.setAttribute("tabindex", "-1");
            t.addEventListener("click", () => {
                const g = t.dataset.grp;   // FILTER / DIST tabs reopen the oscillator last shown there
                this._oscPage = g ? g + (this._fdOsc[g] || 0) : t.dataset.page;
                this.setGroup("synth"); t.blur();
            });
        });
        this._fdOsc = { f: 0, d: 0 };
        this.querySelectorAll(".otab").forEach(t => t.addEventListener("click", () => {
            const g = t.dataset.pg, k = Number(t.dataset.oo);
            this._fdOsc[g] = k; this._oscPage = g + k; this.setGroup("synth"); t.blur();
        }));
        // Filter / Wavefilter and Distortion / Wavedistortion switches: the table types are the last entries of the type lists
        this.querySelectorAll(".o-mode").forEach(md => {
            const o = Number(md.dataset.o), f = md.dataset.k === "f", key = f ? "ftype" : "dtype", tv = f ? 30 : 7;
            this._lastNormal = this._lastNormal || {};
            md.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
                const c = this._controls.get("param" + oscId(o, key));
                if (!c) return;
                const cur = Math.round(this.oscVal(o, key));
                if (Number(b.dataset.m) === 1) { if (cur !== tv) { this._lastNormal[key + o] = cur; c.setValue(tv, true); } }
                else if (cur === tv) c.setValue(this._lastNormal[key + o] || (f ? 0 : 1), true);
                b.blur();
            }));
        });
        this.setGroup("synth");
    }

    // three pages, top to bottom in the rail: synth, effects, modulation
    setGroup (g) {
        this._group = g;
        this.setAttribute("data-group", g);
        this.querySelectorAll(".rb").forEach(t => t.classList.toggle("on", t.dataset.group === g));
        this.setPage(g === "synth" ? this._oscPage : g);
        // the matrix page shows the matrix and the envelope / LFO editors together; the other pages keep only the editors
        if (g !== "mod" && this._bs !== "mod") this.showStrip("mod");
        if (g === "mod") { this._stripWas = this._stripOpen; if (!this._stripOpen) this.setStripOpen(true); }
        else if (this._stripWas === false) { this._stripWas = undefined; this.setStripOpen(false); }
        if (this._stripOpen) { this.drawLfo(); this.drawEnv(); this.drawFrq(); }
    }

    setPage (p) {
        this._page = p;
        this.setAttribute("data-page", p);
        this.querySelectorAll(".stab").forEach(t => t.classList.toggle("on", t.dataset.page === p || (t.dataset.grp && p.charAt(0) === t.dataset.grp && /^[fd]\d$/.test(p))));
        this.querySelectorAll(".otab").forEach(t => t.classList.toggle("on", t.dataset.pg === p.charAt(0) && "ABCDEF"[Number(p.charAt(1))] === t.textContent));
        this.drawAllOsc();
        if (p === "fm" || p === "rm") requestAnimationFrame(() => this.fmxDraw());
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
    async decodeFile (file, kind) {
        const AC = window.AudioContext || window.webkitAudioContext;
        let ctx = null;
        try { if (AC) ctx = new AC(); } catch (_) { ctx = null; }
        const sr = (ctx && ctx.sampleRate) || 48000;
        try {
            const ab = await file.arrayBuffer();
            if (kind === "wt" && (/\.vitaltable$/i.test(file.name || "") || (new Uint8Array(ab, 0, 1)[0] === 123))) {
                const vt = this.decodeVitalTable(ab);
                if (vt) return vt;
            }
            let ch = null, rate = 0;
            // 1. our own decoders (WAV family, AIFF, AU, CAF, FLAC) do not depend on the web view's codecs
            const maxIn = Math.ceil((kind === "wt" ? MAX_WT : MAX_SMP) * 4);
            const nat = AudioDecode.decodeNative(ab, maxIn);
            if (nat) { ch = nat.ch; rate = nat.rate; }
            // 2. mp3 / ogg / opus / aac / m4a ...: whatever the web view can decode
            if (!ch && ctx) {
                try {
                    const buf = await new Promise((res, rej) => { const p = ctx.decodeAudioData(ab.slice(0), res, rej); if (p && p.then) p.then(res, rej); });
                    ch = []; for (let c = 0; c < buf.numberOfChannels; c++) ch.push(buf.getChannelData(c));
                    rate = buf.sampleRate;
                } catch (_) { ch = null; }
            }
            // 3. headerless dumps: 16 bit little endian mono
            if (!ch && /\.(raw|pcm|sam|smp|dat|bin|sd|s16)$/i.test(file.name || "")) { const r = AudioDecode.raw(ab, maxIn); ch = r.ch; rate = r.rate; }
            if (!ch || !ch.length || !ch[0].length) throw new Error("unsupported audio format");
            let frames = ch[0].length;
            let mono = new Float32Array(frames);
            for (let c = 0; c < ch.length; c++) { const d = ch[c]; for (let i = 0; i < frames; i++) mono[i] += d[i] / ch.length; }
            // samples are converted to the host rate; wavetables are not: their frames are single cycles of N samples
            if (kind !== "wt" && rate && Math.abs(rate - sr) > 0.5) { mono = await this.resampleMono(mono, rate, sr); frames = mono.length; }
            if (kind === "wt") { mono = this.trimWavetable(mono); frames = mono.length; }
            const len = Math.min(frames, kind === "wt" ? MAX_WT : MAX_SMP);
            if (len < 1) throw new Error("empty");
            if (mono.length !== len) mono = mono.subarray(0, len);
            let peak = 0;
            for (let i = 0; i < len; i++) peak = Math.max(peak, Math.abs(mono[i]));
            const g = peak > 0.0001 ? 0.9 / peak : 1;
            const out = new Float32Array(len);
            for (let i = 0; i < len; i++) out[i] = mono[i] * g;
            return { mono: out, len, rate: sr, sr, dur: len / sr };
        } finally { if (ctx && ctx.close) { try { ctx.close(); } catch (_) {} } }
    }

    // Vital style frame count: more than 128 frames are thinned out evenly (first and last frame are kept)
    trimWavetable (x) {
        const fl = x.length % 4096 === 0 ? 4096 : (x.length >= 2048 ? 2048 : 0);
        if (!fl) return x;
        const nF = Math.floor(x.length / fl);
        if (nF <= MAX_WT_FRAMES) return x;
        const out = new Float32Array(MAX_WT_FRAMES * fl);
        for (let t = 0; t < MAX_WT_FRAMES; t++) out.set(x.subarray(Math.round(t * (nF - 1) / (MAX_WT_FRAMES - 1)) * fl).subarray(0, fl), t * fl);
        return out;
    }

    // Vital wavetable (.vitaltable, JSON): the keyframes of the first "Wave Source" component (2048 float samples each, base64) are
    // interpolated linearly over 128 frames (Vital positions run 0..255). Other modifier components are not applied.
    decodeVitalTable (ab) {
        let j;
        try {
            let txt;
            if (typeof TextDecoder !== "undefined") txt = new TextDecoder("utf-8").decode(ab);
            else { const u = new Uint8Array(ab); let b = ""; for (let i = 0; i < u.length; i += 8192) b += String.fromCharCode.apply(null, u.subarray(i, i + 8192)); txt = decodeURIComponent(escape(b)); }
            j = JSON.parse(txt);
        } catch (_) { return null; }
        if (!j || !Array.isArray(j.groups)) return null;
        let kfs = null;
        for (const g of j.groups) for (const c of (g.components || [])) if (!kfs && c.type === "Wave Source" && Array.isArray(c.keyframes) && c.keyframes.length) kfs = c.keyframes;
        if (!kfs) return null;
        const frames = kfs.map(k => {
            const bin = atob(k.wave_data || ""), n = Math.min(2048, bin.length >> 2), w = new Float32Array(2048);
            const dv = new DataView(new ArrayBuffer(4));
            for (let i = 0; i < n; i++) { for (let b = 0; b < 4; b++) dv.setUint8(b, bin.charCodeAt(i * 4 + b)); w[i] = dv.getFloat32(0, true); }
            return { pos: +k.position || 0, w };
        }).sort((a, b) => a.pos - b.pos);
        const out = new Float32Array(MAX_WT_FRAMES * 2048);
        const nOut = frames.length === 1 ? 1 : MAX_WT_FRAMES;
        for (let t = 0; t < nOut; t++) {
            const p = nOut === 1 ? 0 : t * 255 / (MAX_WT_FRAMES - 1);
            let a = frames[0], b = frames[frames.length - 1];
            for (let i = 0; i < frames.length; i++) { if (frames[i].pos <= p) a = frames[i]; }
            for (let i = frames.length - 1; i >= 0; i--) { if (frames[i].pos >= p) b = frames[i]; }
            const f = b.pos > a.pos ? (p - a.pos) / (b.pos - a.pos) : 0;
            for (let i = 0; i < 2048; i++) out[t * 2048 + i] = a.w[i] + (b.w[i] - a.w[i]) * f;
        }
        const len = nOut * 2048;
        let peak = 0; for (let i = 0; i < len; i++) peak = Math.max(peak, Math.abs(out[i]));
        const g = peak > 0.0001 ? 0.9 / peak : 1;
        const m = new Float32Array(len); for (let i = 0; i < len; i++) m[i] = out[i] * g;
        return { mono: m, len, rate: 48000, sr: 48000, dur: len / 48000, name: j.name };
    }

    // sample rate conversion to the web audio rate (the web view's decoder resamples the same way)
    async resampleMono (x, from, to) {
        const n = Math.max(1, Math.round(x.length * to / from));
        try {
            const OC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
            if (OC) {
                const oc = new OC(1, n, to), b = oc.createBuffer(1, x.length, from);
                b.copyToChannel(x, 0);
                const src = oc.createBufferSource(); src.buffer = b; src.connect(oc.destination); src.start();
                const r = await oc.startRendering();
                return r.getChannelData(0).slice(0, n);
            }
        } catch (_) {}
        const y = new Float32Array(n), k = from / to;
        for (let i = 0; i < n; i++) {   // Catmull-Rom
            const t = i * k, j = Math.floor(t), f = t - j;
            const p0 = x[Math.max(0, j - 1)], p1 = x[Math.min(x.length - 1, j)], p2 = x[Math.min(x.length - 1, j + 1)], p3 = x[Math.min(x.length - 1, j + 2)];
            y[i] = p1 + 0.5 * f * (p2 - p0 + f * (2 * p0 - 5 * p1 + 4 * p2 - p3 + f * (3 * (p1 - p2) + p3 - p0)));
        }
        return y;
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

    memEndpoint (kind) { return kind === "wt" ? "wtBankLoad" : (kind === "ft" || kind === "sh") ? "tblLoad" : "smpBankLoad"; }

    // DSP bank of a memory: wavetable / sample = slot, Wavefilter table = slot, Wavedistortion table = 6 + slot
    memBank (kind, o) { return kind === "sh" ? OSC_N + o : o; }

    oscVal (o, key) {
        const id = oscId(o, key);
        const c = this._controls.get("param" + id);
        return c ? c.value : SPEC_BY_NUM.get(id).init;
    }

    srcKind (o) { const t = Math.round(this.oscVal(o, "type")); return t === 1 || t === 8 || t === 11 ? "sm" : "wt"; }

    setMgr (text) {
        const el = this.querySelector(".mgr-status");
        if (el) el.textContent = text;
    }

    loadMemStore () {
        for (const kind of ["wt", "sm", "ft", "sh"]) {
            for (let o = 0; o < OSC_N; o++) {
                if (this._mem[kind][o]) continue;   // loaded by the user since startup: newer than the saved copy
                try { const m = decodeMem(this.kvGet(this.memKey(kind, o)), kind === "sm" ? "SAMPLE" : "TABLE"); if (m) this._mem[kind][o] = m; } catch (_) {}
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
            for (let k = 0; k < 4 && offset < total; k++) {
                const count = Math.min(CHUNK, total - offset);
                const data = new Array(CHUNK).fill(0);
                for (let i = 0; i < count; i++) data[i] = s.data[offset + i];
                this.pc.sendEventOrValue(ep, { bank: this.memBank(kind, o), offset, count, total, data });
                offset += count;
            }
            if (this.srcKind(o) === kind && (kind === "wt" || kind === "sm")) this.setDz(o, "LOADING " + Math.round(offset / total * 100) + "%", "busy");
            if (offset >= total) { this.memCancel(kind, o); if (done) done(); }
        }, 6);
    }

    // UI -> DSP: stream every saved memory back, staggered
    startMemRestore () {
        let n = 0;
        for (const kind of ["wt", "sm", "ft", "sh"]) {
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
            const dec = await this.decodeFile(file, kind);
            this.libTrack(kind + o, file, libId, dec);
            const name = (dec.name || file.name || (kind === "wt" ? "TABLE" : "SAMPLE")).replace(/\.[^.]+$/, "").slice(0, 14).toUpperCase();
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

    // ---------- Wavefilter / Wavedistortion tables (512 points per frame, up to 64 frames) ----------
    // built-in tables (mirror of tblDefault in the DSP): kind "ft" gain = (value + 1) / 2 over 8 octaves around the cutoff, "sh" = transfer curve
    tblDefault (kind, f, i) {
        const u = i / 511;
        if (kind === "ft") {
            const o = (u - 0.5) * 8, sig = z => 1 / (1 + Math.exp(z)), ga = (c) => Math.exp(-(o - c) * (o - c) * 2);
            const g = [sig(o * 2), sig(o * 6), Math.exp(-o * o * 0.5), Math.exp(-o * o * 3), sig(-o * 6), sig(-o * 2), 1 - Math.exp(-o * o * 3),
                Math.min(1, sig(o * 3) + 0.9 * Math.exp(-o * o * 8)), 0.5 + 0.5 * Math.cos(o * 6.2831853), 0.5 + 0.5 * Math.cos(o * 12.566371),
                Math.min(1, ga(-1.6) + ga(-0.3)), Math.min(1, ga(-1.9) + ga(0.7)), Math.min(1, ga(-2.4) + ga(1)), Math.min(1, ga(-1.5) + ga(-0.6)),
                Math.min(1, ga(-2.2) + ga(-0.9)), sig(-o * 0.8)][f];
            return g * 2 - 1;
        }
        const x = u * 2 - 1, PI = Math.PI, ax = Math.abs(x);
        const v = [x, Math.tanh(2 * x) / 0.9640276, Math.tanh(5 * x) / 0.9999092, Math.max(-1, Math.min(1, 2 * x)), Math.sin(x * PI / 2), Math.sin(x * 1.5 * PI), Math.sin(x * 2.5 * PI),
            Math.sin(x * 4.5 * PI), 4 * x * x * x - 3 * x, 16 * Math.pow(x, 5) - 20 * x * x * x + 5 * x, 2 * ax - 1, (Math.min(Math.floor((x + 1) * 2), 3) + 0.5) * 0.5 - 1,
            (Math.min(Math.floor((x + 1) * 4), 7) + 0.5) * 0.25 - 1, (Math.tanh(2 * x + 0.6) - 0.5370496) / 0.4524, Math.sin(x * 2 * PI), Math.sin(x * 4 * PI)][f];
        return Math.max(-1, Math.min(1, v));
    }

    // frame at position pos (0..1) of the table of kind / slot o as 512 values (loaded file or built-in)
    tblFrame (kind, o, pos) {
        const s = this._mem[kind][o];
        const nF = s ? Math.max(1, Math.min(TBL_MAX_FR, Math.floor(s.total / TBL_FL))) : 16;
        const fp = Math.max(0, Math.min(1, pos)) * (nF - 1), f0 = Math.floor(fp), f1 = Math.min(f0 + 1, nF - 1), ff = fp - f0;
        const at = (f, i) => s ? Math.max(-1, Math.min(1, s.data[f * TBL_FL + i] || 0)) : this.tblDefault(kind, f, i);
        const out = new Float32Array(TBL_FL);
        for (let i = 0; i < TBL_FL; i++) { const a = at(f0, i); out[i] = a + (at(f1, i) - a) * ff; }
        return out;
    }

    // a wavetable file cut into frames (Vital rule: 4096 / 2048 samples; shorter files are one frame), every frame reduced to 512 points
    tblFromMono (mono) {
        const fl = mono.length % 4096 === 0 ? 4096 : (mono.length >= 2048 ? 2048 : mono.length);
        const nF = Math.max(1, Math.floor(mono.length / fl)), take = Math.min(nF, TBL_MAX_FR);
        const out = new Float32Array(take * TBL_FL);
        for (let t = 0; t < take; t++) {
            const f = take === 1 ? 0 : Math.round(t * (nF - 1) / (take - 1)), b = f * fl;
            for (let i = 0; i < TBL_FL; i++) {
                const x = i * (fl - 1) / (TBL_FL - 1), i0 = Math.floor(x), i1 = Math.min(i0 + 1, fl - 1), xf = x - i0;
                out[t * TBL_FL + i] = mono[b + i0] + (mono[b + i1] - mono[b + i0]) * xf;
            }
        }
        return out;
    }

    setTblDz (kind, o, text, cls) {
        const dz = this.querySelector('.dz-tbl[data-o="' + o + '"][data-k="' + kind + '"]');
        if (!dz) return;
        dz.querySelector(".dz-txt").textContent = text;
        dz.classList.toggle("loaded", cls === "loaded");
        dz.classList.toggle("busy", cls === "busy");
        dz.classList.toggle("err", cls === "err");
    }

    async loadTbl (kind, o, file) {
        this.memCancel(kind, o);
        this.setTblDz(kind, o, "DECODING...", "busy");
        try {
            const dec = await this.decodeFile(file, "wt");
            const data = this.tblFromMono(dec.mono);
            const name = (dec.name || file.name || "TABLE").replace(/\.[^.]+$/, "").slice(0, 14).toUpperCase();
            const m = { name, total: data.length, data };
            this.memStream(kind, o, m, () => {
                this._mem[kind][o] = m;
                this.memPersist(kind, o);
                this.updateOscUi(o);
                this.setMgr("LOADED " + name);
            });
        } catch (err) {
            this.memCancel(kind, o);
            this.setTblDz(kind, o, "UNSUPPORTED FILE", "err");
        }
    }

    clearTbl (kind, o) {
        this.memCancel(kind, o);
        this.pc.sendEventOrValue("tblLoad", { bank: this.memBank(kind, o), offset: 0, count: 0, total: 0, data: new Array(CHUNK).fill(0) });
        this._mem[kind][o] = null;
        this.memPersist(kind, o);
        this.updateOscUi(o);
    }

    buildTblZones () {
        for (let o = 0; o < OSC_N; o++) for (const kind of ["ft", "sh"]) {
            const dz = this.querySelector('.dz-tbl[data-o="' + o + '"][data-k="' + kind + '"]');
            if (!dz) continue;
            dz.addEventListener("dragover", ev => { ev.preventDefault(); dz.classList.add("over"); });
            dz.addEventListener("dragleave", () => dz.classList.remove("over"));
            dz.addEventListener("drop", ev => {
                ev.preventDefault(); dz.classList.remove("over");
                const f = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
                if (f) this.loadTbl(kind, o, f);
            });
            dz.addEventListener("click", () => {
                const inp = document.createElement("input");
                inp.type = "file"; inp.accept = ".vitaltable,audio/*,.wav,.w64,.rf64,.aif,.aiff,.aifc,.au,.caf,.flac,.mp3,.ogg,.opus,.m4a,.aac";
                inp.onchange = () => { if (inp.files && inp.files[0]) this.loadTbl(kind, o, inp.files[0]); };
                inp.click();
            });
            const clr = dz.querySelector(".dz-clr");
            if (clr) clr.addEventListener("click", ev => { ev.stopPropagation(); this.clearTbl(kind, o); });
        }
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
                inp.type = "file"; inp.accept = ".vitaltable,audio/*,video/mp4,video/webm,.wav,.w64,.rf64,.bwf,.aif,.aiff,.aifc,.au,.snd,.caf,.flac,.mp3,.mp2,.ogg,.oga,.opus,.m4a,.aac,.webm,.raw,.pcm";
                inp.onchange = () => { if (inp.files && inp.files[0]) this.loadMem(this.srcKind(o), o, inp.files[0]); };
                inp.click();
            });
            const clr = dz.querySelector(".dz-clr");
            if (clr) clr.addEventListener("click", ev => { ev.stopPropagation(); this.clearMem(o); });
            const lib = this.querySelector('.dz-lib[data-o="' + o + '"]');
            if (lib) lib.addEventListener("click", () => { lib.dataset.slot = this.srcKind(o) + o; });
            this.updateOscUi(o);
        }
        this.buildTblZones();
        this._oscReady = true;
    }

    // refreshes everything that depends on the source type / engine of one slot
    updateOscUi (o) {
        const type = Math.max(0, Math.min(13, Math.round(this.oscVal(o, "type"))));
        const pg = this.querySelector(".p-o" + o);
        if (pg) pg.setAttribute("data-src", String(type));
        this.querySelectorAll('[data-o="' + o + '"][data-show]').forEach(el => {
            el.style.display = el.dataset.show.split(",").indexOf(String(type)) >= 0 ? "" : "none";
        });
        const kind = type === 1 || type === 8 || type === 11 ? "sm" : "wt";
        const s = this._mem[kind][o];
        if (!this._memTimer[kind][o]) this.setDz(o, s ? s.name : (kind === "wt" ? WT_DZ_EMPTY : SMP_DZ_EMPTY), s ? "loaded" : "");
        // Wavefilter / Wavedistortion: table drop zone and position knob are live only while that type is selected
        for (const [kind, tkey, pkey, tv] of [["ft", "ftype", "wfpos", 30], ["sh", "dtype", "wdpos", 7]]) {
            const on = Math.round(this.oscVal(o, tkey)) === tv, m = this._mem[kind][o];
            for (const key of (kind === "ft" ? [pkey, "wfmix", "wfrange", "wfwarp", "wfcont", "wftilt", "wfspr", "wflaw"] : [pkey])) {
                const pc = this.querySelector(".n" + oscId(o, key));
                if (pc) pc.classList.toggle("dim", !on);
            }
            const tb = this.querySelector('.o-tb[data-o="' + o + '"][data-k="' + kind + '"]');
            if (tb) tb.classList.toggle("off", !on);
            const md = this.querySelector('.o-mode[data-o="' + o + '"][data-k="' + (kind === "ft" ? "f" : "d") + '"]');
            if (md) md.querySelectorAll("button").forEach(b => b.classList.toggle("on", (Number(b.dataset.m) === 1) === on));
            if (!this._memTimer[kind][o]) this.setTblDz(kind, o, m ? m.name : (kind === "ft" ? "DROP TABLE" : "DROP SHAPER TABLE"), m ? "loaded" : "");
        }
        this.drawOsc(o);
        this.drawOscFlt(o);
        this.drawTblViews(o);
    }

    onOscValue (o, k) {
        if (!this._oscReady) return;   // controls are still being created
        if (k === OSC_K.type) { this.updateOscUi(o); return; }
        if (k === OSC_K.wpos || k === OSC_K.wsize || k === OSC_K.w1m || k === OSC_K.w1a || k === OSC_K.w2m || k === OSC_K.w2a
            || k === OSC_K.sstart || k === OSC_K.sloop || k === OSC_K.root) this.drawOsc(o);
        if (k >= OSC_K.fon && k <= OSC_K.fkey || (k >= OSC_K.wfmix && k <= OSC_K.wflaw)) this.drawOscFlt(o);
        if (k === OSC_K.ftype || k === OSC_K.dtype) this.updateOscUi(o);
        if (k === OSC_K.wfpos) { this.drawOscFlt(o); this.drawTblViews(o); }
        if (k === OSC_K.dtype || k === OSC_K.ddrv || k === OSC_K.dmix || k === OSC_K.wdpos || k === OSC_K.dpos) this.drawTblViews(o);
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
        } else if (type === 1 || type === 8) {
            const s = this._mem.sm[o];
            if (!s) { if (info) info.textContent = "NO SAMPLE LOADED"; return; }
            const n = s.total, step = Math.max(1, Math.floor(n / W));
            const start = Math.max(0, Math.min(1, type === 8 ? (() => { const c = this._controls.get("param" + grId(o, "gpos")); return c ? c.value : SPEC_BY_NUM.get(grId(o, "gpos")).init; })() : this.oscVal(o, "sstart")));
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
        } else if (type === 13) {
            if (info) info.textContent = "BAGPIPE / CHANTER + DRONES";
        } else if (type === 12) {
            if (info) info.textContent = "SOUNDFONT / LOAD .SF2 IN THE NATIVE UI";
        } else if (type === 11) {
            // Spectral: the envelope the partials follow (two formant peaks in Spectrum mode; Resynth shows the loaded sample on the memory card)
            const V = key => { const id = spId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const arr = new Array(W), sg = 0.12 + V("sblur") * 0.9, c1 = 100 * Math.pow(2, V("spos") * 6.6), c2 = 100 * Math.pow(2, V("spos2") * 6.6), m = V("smorph");
            for (let x = 0; x < W; x++) {
                const l = Math.log2(40 * Math.pow(2, x / W * 9)), d1 = (l - Math.log2(c1)) / sg, d2 = (l - Math.log2(c2)) / sg;
                arr[x] = Math.min(1, (1 - m) * Math.exp(-0.5 * d1 * d1) + m * Math.exp(-0.5 * d2 * d2)) * 1.6 - 0.8;
            }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = (V("smode") < 0.5 ? "SPECTRAL RESYNTH / " : "SPECTRUM / ") + Math.round(c1) + " HZ" + (m > 0.01 ? " > " + Math.round(c2) + " HZ" : "");
        } else if (type === 10) {
            // Modal Drum: the first 300 ms of the batter head modes (110 Hz) with the damping of Decay / Head Tone
            const V = key => { const id = dkId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const R = [1, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501, 3.6, 3.652, 4.06, 4.231], arr = new Array(W);
            const t60 = 0.05 * Math.pow(160, V("ddecay")), it = 1 - V("dtone"), T = 0.3;
            for (let x = 0; x < W; x++) {
                const t = x / W * T; let y = 0;
                R.forEach((r, k) => { y += Math.sin(2 * Math.PI * 110 * r * t * (1 + 0.3 * V("dtens") * Math.exp(-t * 20))) * Math.exp(-t * 6.9 / Math.max(0.01, t60 * Math.pow(r, -2 * it))) / (1 + 0.35 * k); });
                arr[x] = Math.max(-1, Math.min(1, y * 0.35));
            }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = "MODAL DRUM / T60 " + t60.toFixed(2) + " S" + (V("dsnare") > 0.01 ? " / SNARE" : "") + (V("dsym") > 0.01 ? " / SYMPATHETIC" : "");
        } else if (type === 9) {
            // Additive: one cycle of the two morphed spectra (the partials of the DSP at 110 Hz)
            const V = key => { const id = adId(o, key), c = this._controls.get("param" + id), r = c ? c.value : SPEC_BY_NUM.get(id).init; return r; };
            const shape = (sh, n) => { const od = n % 2; switch (sh) { case 0: return 1 / n; case 1: return od ? 1 / n : 0; case 2: return od ? 1.6 / (n * n) : 0; case 3: return ({ 1: 1, 2: 0.8, 3: 0.7, 4: 0.6, 6: 0.5, 8: 0.4 })[n] || 0; case 4: return Math.pow(n, -0.8) * (0.15 + Math.pow(Math.sin(n * 2.3), 2)); case 5: { const f = n * 110, gs = (m, w) => Math.exp(-0.5 * (f - m) * (f - m) / (w * w)); return (0.04 + gs(650, 150) + 0.7 * gs(1100, 200) + 0.4 * gs(2600, 300)) / Math.sqrt(n); } case 6: return Math.pow(n, -0.5) * (1 - Math.exp(-0.6 * n)); default: return n % 3 === 0 ? 0 : 1 / n; } };
            const cnt = Math.round(V("acount")), mo = V("amorph"), ex = V("atilt") * 1.5, odd = V("aodd"), fc = V("aform") * 6, fg = V("aformg") * 3, arr = new Array(W);
            const a = []; let ss = 0;
            for (let n = 1; n <= 64; n++) { let v = 0; if (n <= cnt && n * 110 < 20000) { v = shape(Math.round(V("ashape")), n) * (1 - mo) + shape(Math.round(V("ashapeb")), n) * mo; v *= Math.pow(n, -ex) * (n % 2 ? 1 + odd : 1 - odd); if (fg > 0) { const dd = (Math.log2(n) - fc) / 0.35; v *= 1 + fg * Math.exp(-0.5 * dd * dd); } v = Math.max(0, v); } a.push(v); ss += v * v; }
            const g = 0.45 / Math.sqrt(ss * 0.5 + 1e-6);
            for (let x = 0; x < W; x++) { let y = 0; for (let n = 1; n <= 64; n++) y += a[n - 1] * Math.sin(2 * Math.PI * n * x / W); arr[x] = Math.max(-1, Math.min(1, y * g * 1.6)); }
            const dr = V("adrive"); if (dr > 0.001) { const gd = 1 + dr * 6; for (let x = 0; x < W; x++) arr[x] = Math.tanh(arr[x] * gd) / Math.tanh(gd); }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = "ADDITIVE / " + AD_SHAPES[Math.round(V("ashape"))].toUpperCase() + (mo > 0.001 ? " > " + AD_SHAPES[Math.round(V("ashapeb"))].toUpperCase() : "") + " / " + cnt + " PARTIALS";
        } else if (type === 7) {
            // JP-8080: one cycle of the selected waveform
            const V = key => { const id = jpId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const wv = Math.max(0, Math.min(8, Math.round(V("jpwave")))), arr = new Array(W), tp = 2 * Math.PI;
            const tri = q => { q -= Math.floor(q); return q < 0.5 ? 4 * q - 1 : 3 - 4 * q; };
            const offs = [-0.11002313, -0.06288439, -0.01952356, 0, 0.01991221, 0.06216538, 0.10745242], dt = V("jpdet") * V("jpdet") * 0.6;
            const cG = -0.55366 * V("jpmix") + 0.99785, sG = -0.73764 * V("jpmix") * V("jpmix") + 1.2841 * V("jpmix") + 0.044372;
            let seed = 7; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 * 2 - 1; };
            for (let x = 0; x < W; x++) {
                const q = x / W; let y = 0;
                if (wv === 0) y = 2 * q - 1;
                else if (wv === 1) y = q < Math.max(0.05, Math.min(0.95, V("jppw"))) ? 0.9 : -0.9;
                else if (wv === 2) y = tri(q);
                else if (wv === 3) y = Math.sin(tp * q);
                else if (wv === 4) y = rnd() * 0.7;
                else if (wv === 5) { const ex = 0.3 + 2.2 * V("jpstilt"), pk = 2 + 20 * V("jpspk"); let s = 0; for (let n = 1; n <= 32; n++) { const dd = (n - pk) / (1 + 0.15 * pk); s += Math.pow(n, -ex) * (1 + 3 * Math.exp(-0.5 * dd * dd)) * Math.sin(tp * n * q); } y = s * 0.6; }
                else if (wv === 6) { let s = 0; offs.forEach((of, k) => { const qq = (q * (1 + of * dt * 6) * 4) % 1; s += (2 * qq - 1) * (k === 3 ? cG : sG); }); y = s * 0.35; }
                else if (wv === 7) { const k = V("jpfb") * 4.5; let yy = Math.sin(tp * q); for (let i = 0; i < 4; i++) yy = Math.sin(tp * q + k * yy + V("jpfbc") * 1.5 * Math.sin(2 * tp * q)); y = yy; }
                else y = tri(q + V("jptmd") * 0.35 * Math.sin(tp * (1 + Math.round(V("jptmr") * 7)) * q));
                arr[x] = Math.max(-1, Math.min(1, y * 0.9));
            }
            const dr = V("jpdrv"); if (dr > 0.001) { const g = 1 + dr * 6; for (let x = 0; x < W; x++) arr[x] = Math.tanh(arr[x] * g) / Math.tanh(g); }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = "JP-8080 / " + JP_WAVES[wv].toUpperCase();
        } else if (type === 6) {
            // Waveguide: envelope of the sound (decay time of the model) with the model's name
            const V = key => { const id = wgId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const mdl = Math.max(0, Math.min(4, Math.round(V("wmodel")))), t60 = 0.05 * Math.pow(400, V("wdecay")), arr = new Array(W);
            const sust = mdl === 1 || mdl === 2, T = Math.min(2.5, Math.max(0.3, t60 * 1.2));
            for (let x = 0; x < W; x++) { const t = x / W * T; arr[x] = (sust ? (1 - Math.exp(-t / (0.005 * Math.pow(200, V("watk"))))) : Math.exp(-t * 6.9 / t60)) * Math.sin(2 * Math.PI * 110 * t * (1 + (mdl === 4 ? V("wglide") * 0.5 * Math.exp(-t * 6.9 / t60) : 0))) * 0.8; }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = "WAVEGUIDE / " + WG_MODELS[mdl].toUpperCase() + " / T60 " + t60.toFixed(2) + " S";
        } else if (type === 5) {
            // the body of the kick: pitch fall and decay over 250 ms at a 60 Hz note
            const V = key => { const id = kickId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const sw = V("ksweep"), tp = Math.max(0.0005, V("kstime") * 0.001 / (1 + 3 * V("kscurve"))), dec = V("kdec") * 0.001, arr = new Array(W);
            let ph = 0; const T = 0.25;
            for (let x = 0; x < W; x++) {
                const t = x / W * T, f = 60 * Math.pow(2, sw * Math.exp(-t / tp));
                ph += f * T / W;
                arr[x] = Math.sin(2 * Math.PI * ph) * Math.exp(-t * 4.6 / dec) * (1 + V("kpunch") * 3 * Math.exp(-t / 0.006)) * 0.6;
            }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = "KICK / " + ["CLASSIC", "808", "PUNCH", "HARDSTYLE"][Math.round(V("kmode"))] + " / SWEEP " + sw.toFixed(1) + " OCT / DECAY " + Math.round(dec * 1000) + " MS";
        } else if (type === 4) {
            // two cycles of the DCO mix (saw + pulse + sub, not band-limited), noise as a level bar
            const V = key => { const id = phyId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const range = Math.round(V("jrange")), cyc = 2, cv = V("jcurve") * 4, wd = Math.max(0.05, Math.min(0.95, V("jwidth")));
            const stp = Math.round(V("jstype")), ptp = Math.round(V("jptype")), btp = Math.round(V("jbtype"));
            const fr = x => x - Math.floor(x), ramp = q => 2 * q - 1;
            const arr = new Array(W);
            for (let x = 0; x < W; x++) {
                const t = x / W * cyc, ph = fr(t), q2 = fr(t / 2), q4 = fr(t / 4);
                let saw;
                if (stp === 1) saw = (ph < wd ? ramp(ph / wd) : -1) + (1 - wd);
                else if (stp === 2) saw = 0.75 * ramp(ph) + 0.25 * ramp(fr(ph * 2));
                else if (stp === 3) saw = 0.7 * ramp(ph) + 0.3 * ramp(fr(ph * 3));
                else { saw = cv > 0.01 ? 2 * (Math.exp(cv * ph) - 1) / (Math.exp(cv) - 1) - 1 : ramp(ph); if (stp === 4) saw = Math.tanh(1.7 * saw) * 1.12; }
                const pul = ph < (ptp === 0 ? wd : (ptp === 1 ? 0.25 : 0.125)) ? 1 : -1;
                const sq = (q, w) => q < w ? 1 : -1;
                const sub = [sq(q2, 0.5), sq(q2, 0.25), sq(q4, 0.5), sq(q4, 0.25), 0.5 * (sq(q2, 0.5) + sq(q4, 0.5)), q2 < 0.5 ? 4 * q2 - 1 : 3 - 4 * q2][btp];
                arr[x] = (saw * V("jsaw") + pul * V("jpulse") + sub * V("jsub")) * 0.55;
            }
            trace(arr, "#ff3b30", 2);
            ctx.fillStyle = "rgba(255,160,64,0.5)"; ctx.fillRect(W - 14, H - 6 - V("jnoise") * (H - 12), 8, V("jnoise") * (H - 12));
            if (info) info.textContent = "ALPHA JUNO / " + ["SAW 1", "SAW 2", "SAW 3", "SAW 4", "SAW 5"][stp] + " + PULSE " + (ptp + 1) + " + SUB " + (btp + 1) + " / " + ["16'", "8'", "4'"][range] + " / WIDTH " + Math.round(wd * 100) + " %" + (V("jpwm") > 0 ? " / PWM " + V("jpwmr").toFixed(1) + " HZ" : "");
        } else if (type === 3) {
            // mode spectrum of resonator A (red) and B (orange): position = frequency ratio on a log axis, height = amplitude
            const V = key => { const id = phyId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const bal = V("phbal"), tune = Math.pow(2, V("phtunB") / 12);
            ctx.fillStyle = "rgba(255,200,190,0.45)"; ctx.font = "bold " + Math.round(H * 0.07) + "px sans-serif";
            const xo = r => 14 + (W - 28) * Math.log2(Math.max(r, 0.5) / 0.5) / Math.log2(80 / 0.5);
            for (const f of [1, 2, 4, 8, 16, 32, 64]) { ctx.fillText(f + "x", xo(f) - 6, H - 3); ctx.fillRect(xo(f), 4, 1, H - 18); }
            for (const [res, col, mul, vol] of [["A", "#ff3b30", 1, 1 - bal], ["B", "#ffa040", tune, bal]]) {
                const md = Math.max(0, Math.min(8, Math.round(V("phmod" + res)))), hit = V("phhit" + res), inh = V("phinh" + res), mat = V("phmat" + res), dec = V("phdec" + res);
                let sum = 0; const am = [];
                for (let i = 0; i < 16; i++) { const a = Math.abs(Math.sin(Math.PI * hit * (i + 1))) / Math.pow(i + 1, PHY_AEXP[md]); am.push(a); sum += a * a; }
                const nr = 1 / Math.sqrt(Math.max(sum, 0.05));
                ctx.fillStyle = col; ctx.globalAlpha = 0.35 + 0.65 * Math.min(1, vol * 1.5);
                for (let i = 0; i < 16; i++) {
                    const r = PHY_RAT[md][i] * (1 + inh * 0.004 * i * i) * mul;
                    const t60 = Math.min(1, Math.pow(PHY_RAT[md][i], -1.6 * (1 - mat)));
                    const h = Math.min(1, am[i] * nr * 1.2) * (H - 24) * (0.35 + 0.65 * t60);
                    ctx.fillRect(xo(r * (res === "B" ? 1 : 1)) - 1.5 + (res === "B" ? 2 : 0), H - 16 - h, 3, h);
                }
                ctx.globalAlpha = 1;
            }
            if (info) info.textContent = "PHYSICAL / A " + PHY_MODELS[Math.round(V("phmodA"))].toUpperCase() + " + B " + PHY_MODELS[Math.round(V("phmodB"))].toUpperCase() + (V("phser") > 0.5 ? " / SERIAL" : "");
        } else {
            // Wave Terrain: one cycle of the output along the orbit (the terrain formulas of the DSP)
            const V = key => { const id = terId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const tt = Math.max(0, Math.min(11, Math.round(this.oscVal(o, "tterr")))), tb = Math.max(0, Math.min(11, Math.round(V("tterr2"))));
            const sc = 0.25 * Math.pow(16, this.oscVal(o, "tscale")), wp = this.oscVal(o, "twarp"), fo = this.oscVal(o, "tfold"), mo = V("tmorph");
            const tf = (n, x, y) => {
                const u = x * sc, v = y * sc, tp = 2 * Math.PI, r = Math.sqrt(x * x + y * y);
                const cl = a => Math.max(-1, Math.min(1, a));
                let z = 0;
                switch (n) {
                    case 0: z = Math.sin(tp * u) * Math.sin(tp * v); break;
                    case 1: z = Math.sin(tp * 1.5 * sc * r); break;
                    case 2: z = u * u - v * v; break;
                    case 3: { const a = cl(u), b = cl(v); z = (4 * a * a * a - 3 * a) * (2 * b * b - 1); break; }
                    case 4: z = Math.tanh(4 * Math.sin(tp * u) * Math.sin(tp * v)); break;
                    case 5: z = Math.sin(3 * Math.atan2(y, x) + tp * 1.5 * sc * r); break;
                    case 6: z = Math.sin(tp * 1.5 * sc * (Math.abs(x) + Math.abs(y))); break;
                    case 7: z = (Math.sin(tp * u) + Math.sin(tp * 1.37 * v) + Math.sin(tp * 0.71 * (u + v))) / 3; break;
                    case 8: z = (Math.cos(tp * u) + Math.cos(tp * v)) * 0.5; break;
                    case 9: { const g = (a, b) => Math.exp(-((u - a) * (u - a) + (v - b) * (v - b)) * 6); z = (g(0.5, 0.5) - g(-0.5, 0.5) + g(-0.5, -0.5) - g(0.5, -0.5)) * 1.6; break; }
                    case 10: { let a = 1; for (let k = 0; k < 4; k++) { z += Math.sin(tp * a * u + k * 1.7) * Math.sin(tp * a * v + k * 0.9) / a; a *= 2; } z *= 0.5333; break; }
                    default: z = Math.sin(tp * u + 3 * Math.sin(tp * v));
                }
                return cl(z);
            };
            const arr = new Array(W), shp = V("tshape"), ex = 1 - 0.75 * shp, rot = 2 * Math.PI * V("trot"), ph0 = 2 * Math.PI * V("tphase");
            const sp = q => shp > 0.001 ? Math.sign(q) * Math.pow(Math.abs(q), ex) : q;
            for (let i = 0; i < W; i++) {
                const a = 2 * Math.PI * i / W, dx = V("trx") * sp(Math.cos(a)), dy = V("try") * sp(Math.sin(V("tratio") * a + ph0));
                let x = V("tcx") + dx * Math.cos(rot) - dy * Math.sin(rot), y = V("tcy") + dx * Math.sin(rot) + dy * Math.cos(rot);
                x = Math.max(-1, Math.min(1, x)); y = Math.max(-1, Math.min(1, y));
                if (wp > 0.001) { const x2 = x + wp * 0.5 * Math.sin(2 * Math.PI * (y + 0.13)), y2 = y + wp * 0.5 * Math.sin(2 * Math.PI * (1.3 * x + 0.4)); x = Math.max(-1, Math.min(1, x2)); y = Math.max(-1, Math.min(1, y2)); }
                let z = mo < 0.001 ? tf(tt, x, y) : tf(tt, x, y) * (1 - mo) + tf(tb, x, y) * mo;
                if (fo > 0.001) z = z * (1 - fo) + fo * Math.sin(z * (1 + 4 * fo) * 1.5708);
                const dr = V("tdrive"); if (dr > 0.001) { const g = 1 + dr * 6; z = Math.tanh(z * g) / Math.tanh(g); }
                arr[i] = z * 0.8;
            }
            const mean = arr.reduce((p, q) => p + q, 0) / W; for (let i = 0; i < W; i++) arr[i] -= mean;
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = "WAVE TERRAIN / " + TERRAINS[tt].toUpperCase() + (mo > 0.001 ? " > " + TERRAINS[tb].toUpperCase() : "") + " / SCALE " + sc.toFixed(2);
        }
    }

    // magnitude response (complex) of the filter of slot o on a log frequency grid
    oscFltCurve (o, N, sweep) {
        const ft = Math.round(this.oscVal(o, "ftype")), fc = this.oscVal(o, "fcut"), res = this.oscVal(o, "fres");
        const out = [];
        if (ft === 30) {   // Wavefilter: the table frame along Range octaves around the cutoff, with Warp / Law / Contrast / Tilt / Mix
            const fr = this.tblFrame("ft", o, this.oscVal(o, "wfpos"));
            const W = Math.max(2, Math.min(14, this.oscVal(o, "wfrange"))), pw = Math.pow(2, this.oscVal(o, "wfwarp")), ex = Math.pow(2, 1.5 * this.oscVal(o, "wfcont"));
            const tilt = this.oscVal(o, "wftilt"), law = Math.round(this.oscVal(o, "wflaw")), mix = this.oscVal(o, "wfmix");
            for (let i = 0; i < N; i++) {
                const r = Math.log2(20 * Math.pow(1000, i / (N - 1)) / fc);
                const t = Math.max(-1, Math.min(1, 2 * r / W));
                const u = 0.5 + (t < 0 ? -0.5 : 0.5) * Math.pow(Math.abs(t), pw);
                const x = u * 511, i0 = Math.floor(x), i1 = Math.min(i0 + 1, 511);
                const v = fr[i0] + (fr[i1] - fr[i0]) * (x - i0);
                let g = law === 0 ? v * 0.5 + 0.5 : law === 1 ? v : Math.pow(10, (v - 1) * 1.5);
                if (ex !== 1) g = Math.sign(g) * Math.pow(Math.abs(g), ex);
                if (tilt !== 0) g = Math.min(g * Math.pow(2, tilt * r), 4);
                out.push([Math.abs(1 + (g - 1) * mix), 0]);
            }
            return out;
        }
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

    // transfer function of the distortion of slot o (mirror of oscDist / shapeSigAlg in the DSP), x in -1..1
    distY (o, x) {
        const ty = Math.round(this.oscVal(o, "dtype")), d = this.oscVal(o, "ddrv"), mix = this.oscVal(o, "dmix");
        if (ty <= 0 || mix <= 0.0005) return x;
        let y;
        if (ty === 7) {
            const fr = this.tblFrame("sh", o, this.oscVal(o, "wdpos"));
            const u = (Math.max(-1, Math.min(1, x * (1 + d * 3))) * 0.5 + 0.5) * 511, i0 = Math.floor(u), i1 = Math.min(i0 + 1, 511);
            y = fr[i0] + (fr[i1] - fr[i0]) * (u - i0);
        } else {
            const al = ty - 1, xx = x * (1 + d * 8);
            y = xx / (1 + Math.abs(xx));
            if (al === 1) { const bias = 0.3 * d, yb = xx + bias; y = yb / (1 + Math.abs(yb)) - bias / (1 + Math.abs(bias)); }
            else if (al === 2) y = Math.max(-0.9, Math.min(0.9, xx));
            else if (al === 3) y = Math.sin(xx * 1.5) * 0.8;
            else if (al === 4) y = Math.sin(Math.max(-1.5708, Math.min(1.5708, xx)));
            else if (al === 5) { const lv = 6 + (1 - d) * 26; y = Math.round(y * lv) / lv; }
            y *= 1 + d * 0.5;
        }
        return x * (1 - mix) + y * mix;
    }

    drawDist (o) {
        const cv = this.querySelector('.dist-canvas[data-o="' + o + '"]');
        if (!cv) return;
        const fr = this.hudFrame(cv);
        if (!fr) return;
        const { ctx, W, H } = fr;
        ctx.strokeStyle = "rgba(255,255,255,0.10)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2); ctx.moveTo(W / 2, 0); ctx.lineTo(W / 2, H); ctx.stroke();
        ctx.strokeStyle = "rgba(255,200,190,0.25)"; ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(0, H); ctx.lineTo(W, 0); ctx.stroke(); ctx.setLineDash([]);
        const on = Math.round(this.oscVal(o, "dtype")) > 0;
        ctx.strokeStyle = on ? "#ff3b30" : "rgba(180,170,165,0.45)"; ctx.lineWidth = 2.5;
        ctx.shadowColor = "rgba(255,59,48,0.9)"; ctx.shadowBlur = on ? 8 : 0;
        ctx.beginPath();
        for (let px = 0; px < W; px++) {
            const x = px / (W - 1) * 2 - 1, y = Math.max(-1.2, Math.min(1.2, this.distY(o, x)));
            const py = H / 2 - y * (H / 2 - 4);
            if (px === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.stroke(); ctx.shadowBlur = 0;
    }

    // frames of a Wavefilter / Wavedistortion table drawn behind each other, the frame at Table Pos in front
    drawTbl (kind, o) {
        const cv = this.querySelector('.tbl-canvas[data-o="' + o + '"][data-k="' + kind + '"]');
        const info = this.querySelector('.osc-info[data-o="' + o + '"][data-k="' + kind + '"]');
        if (!cv) return;
        const fr = this.hudFrame(cv);
        if (!fr) return;
        const { ctx, W, H } = fr;
        const s = this._mem[kind][o], nF = s ? Math.max(1, Math.min(TBL_MAX_FR, Math.floor(s.total / TBL_FL))) : 16;
        const pos = this.oscVal(o, kind === "ft" ? "wfpos" : "wdpos");
        const on = Math.round(this.oscVal(o, kind === "ft" ? "ftype" : "dtype")) === (kind === "ft" ? 30 : 7);
        const at = (f, i) => s ? Math.max(-1, Math.min(1, s.data[f * TBL_FL + i] || 0)) : this.tblDefault(kind, f, i);
        const show = Math.min(nF, 24), dx = W * 0.16, dy = H * 0.42, pw = W - dx - 6, ph = H - dy - 8;
        const line = (f, color, lw) => {
            ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.beginPath();
            const t = nF === 1 ? 0 : f / (nF - 1), ox = 3 + dx * t, oy = 4 + dy * (1 - t);
            for (let i = 0; i < 128; i++) {
                const v = at(f, Math.min(511, Math.round(i * 511 / 127)));
                const x = ox + pw * i / 127, y = oy + ph * (0.5 - v * 0.5);
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
        };
        for (let k = show - 1; k >= 0; k--) {
            const f = show === 1 ? 0 : Math.round(k * (nF - 1) / (show - 1));
            line(f, on ? "rgba(255,120,100," + (0.18 + 0.3 * (1 - k / show)).toFixed(2) + ")" : "rgba(160,150,145,0.22)", 1);
        }
        // the interpolated frame at Table Pos
        const cur = this.tblFrame(kind, o, pos), t = Math.max(0, Math.min(1, pos)), ox = 3 + dx * t, oy = 4 + dy * (1 - t);
        ctx.strokeStyle = on ? "#ff3b30" : "rgba(200,190,185,0.6)"; ctx.lineWidth = 2.5;
        ctx.shadowColor = "rgba(255,59,48,0.9)"; ctx.shadowBlur = on ? 8 : 0; ctx.beginPath();
        for (let i = 0; i < 128; i++) {
            const v = cur[Math.min(511, Math.round(i * 511 / 127))];
            const x = ox + pw * i / 127, y = oy + ph * (0.5 - v * 0.5);
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke(); ctx.shadowBlur = 0;
        if (info) info.textContent = (s ? s.name : "BUILT-IN TABLE") + " / FRAME " + (t * (nF - 1) + 1).toFixed(1) + " OF " + nF + (on ? "" : " / NOT ACTIVE");
    }

    drawTblViews (o) { this.drawDist(o); this.drawTbl("ft", o); this.drawTbl("sh", o); }

    drawAllOsc () { for (let o = 0; o < OSC_N; o++) { this.drawOsc(o); this.drawOscFlt(o); this.drawTblViews(o); } }

    // ---------- page HTML ----------
    oscPageHTML (o) {
        const c = key => this.controlHTML(oscId(o, key), true);
        const p = key => this.controlHTML(phyId(o, key), true);
        const kk = key => this.controlHTML(kickId(o, key), true);
        const px = key => this.controlHTML(terId(o, key), true);
        const wx = key => this.controlHTML(wgId(o, key), true);
        const jx = key => this.controlHTML(jpId(o, key), true);
        const gx = key => this.controlHTML(grId(o, key), true);
        const dx = key => this.controlHTML(dkId(o, key), true);
        const sx = key => this.controlHTML(spId(o, key), true);
        const wtc = key => this.controlHTML(wtId(o, key), true);
        const mx = key => this.controlHTML(smId(o, key), true);
        const fx = key => this.controlHTML(sfId(o, key), true);
        const bx = key => this.controlHTML(bpId(o, key), true);
        const ax = key => this.controlHTML(adId(o, key), true);
        const sh = (list, inner, cls) => `<div class="${cls || "cgrid"}" data-o="${o}" data-show="${list}">${inner}</div>`;
        const src = `<section class="card o-src"><h2>OSC ${o + 1} Source</h2>
            <div class="o-type">${c("type")}</div>
            <canvas class="osc-canvas" data-o="${o}" width="640" height="190"></canvas>
            <div class="osc-info" data-o="${o}">--</div>
            <div class="o-mem" data-o="${o}" data-show="0,1,8,11"><div class="dz dz-osc" data-o="${o}"><span class="dz-txt"></span><span class="dz-clr" title="Clear this memory">&times;</span></div><button type="button" class="pb dz-lib" data-o="${o}" data-slot="wt${o}" title="Open the sound vault">VAULT</button></div>
            ${sh("0", ["wpos", "wsize", "w1m", "w1a", "w2m", "w2a"].map(c).join("") + this.controlHTML(2000 + o, true) + ["w3m", "w3a", "wmorph", "wtone"].map(wtc).join(""), "cgrid o-g2")}
            ${sh("1", ["root", "sstart", "sloop"].map(c).join("") + ["send", "slps", "slpe", "spp", "sxf", "srev", "sint", "sgain", "svst", "sslice", "swid"].map(mx).join(""), "cgrid o-g3")}
            ${sh("8", ["root"].map(c).join("") + ["gpos", "gsize", "gdens", "gspray", "gpitch", "gpan", "gshape", "grev", "gscan", "gjit", "gvel", "gdrive"].map(gx).join(""), "cgrid o-g3 o-pl")}
            ${sh("13", ["bpscale", "bpreed", "bpdouble", "bpconic", "bpcoup", "bpbore", "bpfluct", "bpair", "bpcolmix", "bpcolf", "bpdrone", "bpchord", "bpkey", "bpstrike", "bpvib", "bpblow"].map(bx).join(""), "cgrid o-g3 o-pl")}
            ${sh("12", ["sfgain", "sfvel", "sfatk", "sfdec", "sfsus", "sfrel", "sfloop", "sfpan", "sfstart", "sfdrive"].map(fx).join(""), "cgrid o-g3 o-pl")}
            ${sh("11", ["smode", "spos", "spos2", "smorph", "sscan", "sblur", "sshift", "stilt", "sharm", "sodd", "scomb", "scont", "sjit", "sspr", "swid", "svel"].map(sx).join(""), "cgrid o-g3 o-pl")}
            ${sh("10", ["ddecay", "dtone", "dhit", "dstick", "dedge", "dres", "drtune", "dshell", "ddepth", "dsnare", "dsten", "dsym", "dtens", "dvel", "ddrive", "dsize"].map(dx).join(""), "cgrid o-g3 o-pl")}
            ${sh("9", ["ashape", "ashapeb", "amorph", "acount", "atilt", "aodd", "ainh", "aform", "aformg", "ashim", "ashimr", "adec", "awid", "avel", "adrive"].map(ax).join(""), "cgrid o-g3 o-pl")}
            ${sh("2", ["tterr", "tscale", "twarp", "tfold"].map(c).join("") + `<div class="o-uh">Orbit</div>` + ["tcx", "tcy", "trx", "try", "trot", "tratio", "tphase", "tshape"].map(px).join("")
                + `<div class="o-uh">Movement / second terrain</div>` + ["tmrate", "tmdep", "tterr2", "tmorph"].map(px).join("") + `<div class="o-uh">Output</div>` + ["tsmooth", "tdrive", "tbits", "tvel"].map(px).join(""), "cgrid o-g3 o-pl")}
            ${sh("4", `<div class="o-uh">Waves</div>` + ["jstype", "jptype", "jbtype", "jsaw", "jpulse", "jsub"].map(p).join("") + `<div class="o-uh">Pulse width</div>` + ["jwidth", "jpwm", "jpwmr", "jpwms", "jrange"].map(p).join("")
                + `<div class="o-uh">Character</div>` + ["jnoise", "jcurve", "jdrift", "jvib"].map(p).join(""), "cgrid o-g3 o-phy o-juno")}
            ${sh("7", `<div class="o-uh">Waveform</div>` + ["jpwave", "jppw", "jppwm", "jppwr", "jpdet", "jpmix", "jpwid", "jpfb", "jpfbc", "jptmd", "jptmr", "jpstilt", "jpspk"].map(jx).join("") + `<div class="o-uh">Common</div>` + ["jpnz", "jpsub", "jpdrv"].map(jx).join(""), "cgrid o-g3 o-pl")}
            ${sh("6", `<div class="o-uh">Model</div>` + ["wmodel", "wdecay", "wtone", "wexc", "wpos", "wnoise", "wnl", "wstretch", "watk"].map(wx).join("") + `<div class="o-uh">Drum / body / output</div>` + ["wsnare", "wbody", "wbodyf", "wvel", "wdrive", "wglide", "wktrack"].map(wx).join(""), "cgrid o-g3 o-pl")}
            ${sh("5", `<div class="o-uh">Body</div>` + ["kmode", "ksweep", "kstime", "kscurve", "kdec", "ktone", "kchar", "ktune"].map(kk).join("") + `<div class="o-uh">Click / noise / sub</div>` + ["kclick", "kcltone", "kcldec", "knoise", "ksub", "kpunch"].map(kk).join("")
                + `<div class="o-uh">Drive</div>` + ["kdrive", "kdtype"].map(kk).join(""), "cgrid o-g3 o-phy o-kick")}
            ${sh("3", `<div class="o-uh">Exciter</div>` + ["phmix", "phhard", "phntim"].map(p).join("") + `<div class="o-uh">Resonator A</div>` + ["phmodA", "phdecA", "phmatA", "phhitA", "phinhA"].map(p).join("")
                + `<div class="o-uh">Resonator B</div>` + ["phmodB", "phdecB", "phmatB", "phhitB", "phinhB", "phtunB"].map(p).join("") + `<div class="o-uh">Mix</div>` + ["phbal", "phser"].map(p).join(""), "cgrid o-g3 o-phy")}
          </section>`;
        const tune = `<section class="card o-tune"><h2>Tune</h2>
            <div class="cgrid o-g2">${["oct", "semi", "fine", "track", "freq"].map(c).join("")}${sh("0,1", ["phase", "rphase"].map(c).join(""), "o-sub o-g2")}</div>
            ${sh("0,1,2,3,4,5,6,7,8,9,10,11,12", "<div class=\"o-uh\">Unison</div>" + ["uvox", "udet", "ublend", "uwid", "udrift", "uphase", "ustyle"].map(c).join(""), "cgrid o-g2 o-uni")}
          </section>`;
        const out = `<section class="card o-out"><h2>Output</h2>
            <div class="cgrid o-g2">${["level", "pan"].map(c).join("")}</div>
            <div class="cgrid o-g2">${c("out")}</div>
            <div class="o-note">Filter and distortion of this oscillator have their own pages (FILTER, DIST).</div>
          </section>`;
        return src + tune + out;
    }

    // chips A-F that switch the oscillator shown on the FILTER / DIST page
    oscChips (kind, o) {
        return `<span class="fxtabs">${"ABCDEF".split("").map((l, k) => `<button type="button" class="otab${k === o ? " on" : ""}" data-pg="${kind}" data-oo="${k}" title="OSC ${k + 1}">${l}</button>`).join("")}</span>`;
    }

    // FILTER page of oscillator o: response display, Filter / Wavefilter switch, controls; the table card shows the frames of the Wavefilter table
    fltPageHTML (o) {
        const c = key => this.controlHTML(oscId(o, key), true);
        return `<section class="card o-fl"><h2>OSC ${o + 1} Filter ${this.oscChips("f", o)}</h2>
            <canvas class="flt-canvas" data-o="${o}" width="900" height="260"></canvas>
            <div class="o-frow">${["fon", "ftype"].map(c).join("")}<div class="o-mode" data-o="${o}" data-k="f"><button type="button" data-m="0">FILTER</button><button type="button" data-m="1">WAVEFILTER</button></div></div>
            <div class="cgrid o-g5">${["fcut", "fres", "fdrv", "fkey", "feg", "fvel", "fatk", "fdec", "fsus", "frel"].map(c).join("")}</div>
          </section>
          <section class="card o-tb" data-o="${o}" data-k="ft"><h2>Wavefilter table</h2>
            <canvas class="tbl-canvas" data-o="${o}" data-k="ft" width="520" height="300"></canvas>
            <div class="osc-info" data-o="${o}" data-k="ft">--</div>
            <div class="o-tbl"><div class="dz dz-tbl" data-o="${o}" data-k="ft" title="Wavefilter table: a wavetable file whose frames are filter curves"><span class="dz-txt"></span><span class="dz-clr" title="Back to the built-in table">&times;</span></div>${c("wfpos")}</div>
            <div class="cgrid o-g3 o-wfc">${["wfmix", "wfrange", "wfwarp", "wfcont", "wftilt", "wfspr", "wflaw"].map(c).join("")}</div>
            <div class="o-note">Every frame is a gain curve along <b>Range</b> octaves around the cutoff (<b>Warp</b> bends that axis). Table Pos morphs between the frames; drop a wavetable file to use your own. <b>Gain Law</b>: Linear = (value + 1) / 2, Bipolar = value (negative gains invert the band), dB = -60 .. 0 dB. <b>Contrast</b> deepens or flattens the curve, <b>Tilt</b> adds +-6 dB per octave, <b>Spread</b> shifts the curve down on the left and up on the right channel, <b>Mix</b> blends with the dry signal.</div>
          </section>`;
    }

    // DIST page of oscillator o: transfer curve, Distortion / Wavedistortion switch, controls; the table card shows the shaper frames
    distPageHTML (o) {
        const c = key => this.controlHTML(oscId(o, key), true);
        return `<section class="card o-fl"><h2>OSC ${o + 1} Distortion ${this.oscChips("d", o)}</h2>
            <canvas class="dist-canvas" data-o="${o}" width="900" height="260"></canvas>
            <div class="o-frow">${["dtype", "dpos"].map(c).join("")}<div class="o-mode" data-o="${o}" data-k="d"><button type="button" data-m="0">DISTORTION</button><button type="button" data-m="1">WAVEDISTORTION</button></div></div>
            <div class="cgrid o-g2">${["ddrv", "dmix"].map(c).join("")}</div>
            <h2>OSC ${o + 1} Resonator (pre-matrix stage, order above)</h2>
            <div class="cgrid o-g4">${["rson", "rsmod", "rsdec", "rsmat", "rshit", "rsinh", "rstune", "rsmix"].map(c).join("")}</div>
          </section>
          <section class="card o-tb" data-o="${o}" data-k="sh"><h2>Wavedistortion table</h2>
            <canvas class="tbl-canvas" data-o="${o}" data-k="sh" width="520" height="300"></canvas>
            <div class="osc-info" data-o="${o}" data-k="sh">--</div>
            <div class="o-tbl"><div class="dz dz-tbl" data-o="${o}" data-k="sh" title="Wavedistortion table: a wavetable file whose frames are transfer curves"><span class="dz-txt"></span><span class="dz-clr" title="Back to the built-in table">&times;</span></div>${c("wdpos")}</div>
            <div class="o-note">Every frame is a transfer curve (input -1..1 to output). Drive scales the input, Mix blends with the dry signal, Table Pos morphs between the frames.</div>
          </section>`;
    }

    // FM / PM matrices: graphical node matrices. Row = modulator, column = carrier; the diagonal holds the oscillator nodes (and their
    // self feedback). A connection is drawn from the modulator node along its row, then down / up its column into the carrier node.
    // The first matrix is frequency modulation (exponential, +-4 octaves at 100%), the second is phase modulation, the third is phase
    // distortion (the modulator bends the carrier's phase, Casio CZ style). All amounts run from 0 (off) to 100 (%).
    fmxKinds () {
        return [{ key: "fm", base: FM_BASE, title: "FM", sub: "frequency modulation", page: "fm" }, { key: "pm", base: PM_BASE, title: "PM", sub: "phase modulation", page: "fm" }, { key: "pd", base: PD_BASE, title: "PD", sub: "phase distortion", page: "fm" },
            { key: "rm", base: RM_BASE, title: "RM", sub: "ring modulation", page: "rm" }, { key: "am", base: AM_BASE, title: "AM", sub: "amplitude modulation", page: "rm" },
            { key: "tz", base: TZ_BASE, title: "TZFM", sub: "through-zero FM", page: "rm" }];
    }

    fmPageHTML (page) {
        const L = "ABCDEF";
        const panels = this.fmxKinds().filter(k => k.page === page).map(k => {
            let cells = "", hid = "";
            for (let sr = 0; sr < OSC_N; sr++) for (let d = 0; d < OSC_N; d++) {
                hid += this.controlHTML(k.base + 6 * sr + d, true);
                if (sr === d) cells += `<div class="fmx-c fmx-d" data-s="${sr}" data-d="${d}"><button type="button" class="fmx-n" data-osc="${sr}" title="Open OSC ${sr + 1}">${L[sr]}</button><div class="fmx-fb" data-s="${sr}" data-d="${d}" title="Self feedback: drag up / down, double-click to reset"><span class="fmx-fbl">FB</span><span class="fmx-v">0</span></div></div>`;
                else cells += `<div class="fmx-c" data-s="${sr}" data-d="${d}" title="${L[sr]} modulates ${L[d]}: click to connect, drag up / down to set the amount, double-click to clear"><i class="fmx-dot"></i><span class="fmx-v"></span></div>`;
            }
            return `<div class="fmx-panel" data-k="${k.key}"><div class="fmx-title"><b>${k.title}</b> ${k.sub}</div><div class="fmx"><svg class="fmx-svg"></svg><div class="fmx-grid">${cells}</div></div><div class="fmx-hid">${hid}</div></div>`;
        }).join("");
        const title = page === "rm" ? "Ring / Amplitude / Through-Zero FM Matrix" : "FM / PM / PD Matrix";
        const note = page === "rm"
            ? "The letter in a row modulates the letter in the column it meets. RM multiplies the carrier with the modulator (ring modulation: the carrier and modulator themselves disappear, sum and difference tones remain), AM multiplies it with the modulator turned into a 0..1 control (amplitude modulation / tremolo: the carrier stays). The modulators are the slots' processed outputs. Amounts run from 0 (off) to 100%. Click a dot to connect, drag a value up / down (Shift = fine), double-click to clear. A letter on the diagonal is the slot itself (a slot can modulate itself). Click a letter to open that oscillator."
            : "The letter in a row modulates the letter in the column it meets. FM changes the carrier's pitch (exponential, +-4 octaves at 100%), PM shifts its phase, PD bends its phase (phase distortion). Amounts run from 0 (off) to 100%. Click a dot to connect, drag a value up / down (Shift = fine), double-click to clear. FB is self feedback. Click a letter to open that oscillator.";
        return `<section class="card fm-card"><h2>${title}</h2><div class="fmx-row">${panels}</div>`
            + `<div class="fm-note">${note}</div></section>`;
    }

    fmxCtl (k, sr, d) { return this._controls.get("param" + (k.base + 6 * sr + d)); }
    fmxSet (k, sr, d, v) { const c = this.fmxCtl(k, sr, d); if (c) c.setValue(Math.max(0, Math.min(100, Math.round(v))), true); }

    buildFmx () {
        this.querySelectorAll(".fmx-n").forEach(n => n.addEventListener("click", () => { this._oscPage = "o" + n.dataset.osc; this.setGroup("synth"); }));
        this.fmxKinds().forEach(k => {
            const panel = this.querySelector('.fmx-panel[data-k="' + k.key + '"]');
            if (!panel) return;
            const hook = (el, sr, d) => {
                let st = null;
                el.addEventListener("pointerdown", e => {
                    if (e.button !== 0) return;
                    const c = this.fmxCtl(k, sr, d); if (!c) return;
                    st = { y: e.clientY, v: c.value, moved: false, id: e.pointerId };
                    try { el.setPointerCapture(e.pointerId); } catch (_) {}
                    e.preventDefault(); e.stopPropagation();
                });
                el.addEventListener("pointermove", e => {
                    if (!st || e.pointerId !== st.id) return;
                    if (Math.abs(e.clientY - st.y) > 3) st.moved = true;
                    if (st.moved) this.fmxSet(k, sr, d, Math.round(st.v + (st.y - e.clientY) * (e.shiftKey ? 0.2 : 0.8)));
                });
                el.addEventListener("pointerup", e => {
                    if (!st || e.pointerId !== st.id) return;
                    const c = this.fmxCtl(k, sr, d);
                    if (!st.moved && c && c.value < 0.5) this.fmxSet(k, sr, d, 50);
                    st = null;
                });
                el.addEventListener("pointercancel", () => { st = null; });
                el.addEventListener("dblclick", e => { this.fmxSet(k, sr, d, 0); e.preventDefault(); });
                el.addEventListener("contextmenu", e => { this.fmxSet(k, sr, d, 0); e.preventDefault(); });
                el.addEventListener("wheel", e => { const c = this.fmxCtl(k, sr, d); if (c) { this.fmxSet(k, sr, d, c.value - Math.sign(e.deltaY) * 2); e.preventDefault(); } }, { passive: false });
            };
            panel.querySelectorAll(".fmx-c:not(.fmx-d)").forEach(el => hook(el, Number(el.dataset.s), Number(el.dataset.d)));
            panel.querySelectorAll(".fmx-fb").forEach(el => hook(el, Number(el.dataset.s), Number(el.dataset.d)));
        });
        this.fmxRefresh();
    }

    fmxRefresh () {
        const txt = v => String(Math.round(v));
        this.fmxKinds().forEach(k => {
            const panel = this.querySelector('.fmx-panel[data-k="' + k.key + '"]');
            if (!panel) return;
            panel.querySelectorAll(".fmx-c").forEach(el => {
                const sr = Number(el.dataset.s), d = Number(el.dataset.d), c = this.fmxCtl(k, sr, d);
                const v = c ? c.value : 0, on = v >= 0.5;
                const box = el.classList.contains("fmx-d") ? el.querySelector(".fmx-fb") : el;
                box.classList.toggle("on", on);
                box.querySelector(".fmx-v").textContent = el.classList.contains("fmx-d") ? txt(v) : (on ? txt(v) : "");
            });
            for (let i = 0; i < OSC_N; i++) {
                let act = false;
                for (let j = 0; j < OSC_N; j++) { const a = this.fmxCtl(k, i, j), b = this.fmxCtl(k, j, i); if ((a && a.value >= 0.5) || (b && b.value >= 0.5)) act = true; }
                const n = panel.querySelector('.fmx-n[data-osc="' + i + '"]'); if (n) n.classList.toggle("act", act);
            }
        });
        this.fmxDraw();
    }

    fmxDraw () {
        this.fmxKinds().forEach(k => {
            const panel = this.querySelector('.fmx-panel[data-k="' + k.key + '"]');
            if (!panel) return;
            const svg = panel.querySelector(".fmx-svg"), grid = panel.querySelector(".fmx-grid");
            const gr = grid.getBoundingClientRect();
            if (!gr.width) return;
            const sc = gr.width / (grid.offsetWidth || gr.width);
            const ctr = (sr, d, which) => {
                const el = grid.querySelector('.fmx-c[data-s="' + sr + '"][data-d="' + d + '"]');
                const r = (which ? el.querySelector(which) || el : el).getBoundingClientRect();
                return [(r.left + r.width / 2 - gr.left) / sc, (r.top + r.height / 2 - gr.top) / sc];
            };
            svg.setAttribute("viewBox", "0 0 " + (gr.width / sc).toFixed(1) + " " + (gr.height / sc).toFixed(1));
            const f = n => n.toFixed(1);
            let out = "";
            for (let sr = 0; sr < OSC_N; sr++) for (let d = 0; d < OSC_N; d++) {
                if (sr === d) continue;
                const c = this.fmxCtl(k, sr, d); if (!c || c.value < 0.5) continue;
                const a = ctr(sr, sr, ".fmx-n"), m = ctr(sr, d), z = ctr(d, d, ".fmx-n");
                const col = "#ff5a4a", w = (1.2 + 2.2 * c.value / 100).toFixed(1);
                out += `<path d="M${f(a[0])} ${f(a[1])} L${f(m[0])} ${f(m[1])} L${f(z[0])} ${f(z[1])}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round" opacity="${(0.45 + 0.5 * c.value / 100).toFixed(2)}"/>`;
            }
            svg.innerHTML = out;
        });
    }

    globalPageHTML () {
        const k = ids => ids.map(i => this.controlHTML(i, true)).join("");
        return this.card("Voice", [2, 4, 3, 63], "g-voice") + this.card("Amp EG", [18, 19, 20, 21, 22], "g-amp") + this.card("Pitch EG", [45, 46], "g-peg")
            + this.card("Output", [29, 190, 36, 522], "g-out");
    }

    // ---------- parameter hooks ----------
    onValue (spec, v, user) {
        const n = spec.num;
        if (((n >= FM_BASE && n < AM_BASE + 36) || (n >= TZ_BASE && n < TZ_BASE + 36)) && this._modReady) this.fmxRefresh();
        if (fxLocate(n)) this.onFxValue(spec, v, user);
        if (n >= PHY_BASE && n < PHY_BASE + PHY_STRIDE * OSC_N && this._oscReady) this.drawOsc(Math.floor((n - PHY_BASE) / PHY_STRIDE));
        if (n >= OSC_BASE && n < OSC_BASE + OSC_STRIDE * OSC_N) this.onOscValue(Math.floor((n - OSC_BASE) / OSC_STRIDE), (n - OSC_BASE) % OSC_STRIDE);
        if ((n >= 307 && n <= 336) || (n >= 472 && n <= 501)) { this.updateSlots(); if (this._modReady) this.updateModRings(); }
        if (this._modReady) {
            if (MOD_TARGET[n]) this.updateModRings(n);
            if (n >= FRQ_BASE && n < FRQ_BASE + 40) { if (n === FRQ_BASE + 4 * this._frqSel) this.drawFrq(); }
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
        row.classList.toggle("nosync", ![3, 4, 5, 6, 7].includes(this._fxTypes[g]));      // delay time, chorus / flanger / phaser / tremolo rate
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
                    + `<div class="fxsy">${this.controlHTML(940 + rk * 10 + sl)}</div>`
                    + `<div class="fxmx">${this.controlHTML(b + 2, true)}</div>`
                    + `<div class="fxps">${ks}</div></div>`;
            }
            let hid = "";
            for (let k = 0; k < 10; k++) hid += this.controlHTML(R.ord + k);
            racks += `<div class="fxlist f-rack" data-rack="${rk}">${rows}<div class="fx-hid">${hid}</div></div>`;
        });
        // only the Main rack is left (Bus 1 / Bus 2 were removed)
        const tabs = [0].map(rk => `<button type="button" class="fxtab" data-rack="${rk}">${FX_RACKS[rk].name}<i class="fxdot"></i></button>`).join("");
        const out = FX_OUT.map(i => `<div class="fxo">${this.controlHTML(i, true)}</div>`).join("");
        return `<section class="card f-main"><h2>FX <span class="fxtabs">${tabs}</span><span class="fxhint">signal runs top to bottom</span></h2>${racks}</section>`
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
            sets += `<div class="env-set" data-env="${i}">${[0, 1, 2, 3].map(k => this.controlHTML(b + k, true)).join("")}<div class="env-pol">${this.controlHTML(3100 + i)}</div></div>`;
        }
        return `<section class="bs-env"><div class="bs-chips">${chips}<span class="bs-gap"></span>${others}</div>`
            + `<div class="bs-envbody"><canvas class="env-canvas" width="360" height="130"></canvas><div class="env-knobs">${sets}</div></div><div class="env-pol env-vel"><span class="lbl">VEL</span>${this.controlHTML(3110)}</div></section>`;
    }

    lfoPanelHTML () {
        const chips = Array.from({ length: 10 }, (_, i) => `<button type="button" class="msrc" data-src="${1 + i}" title="Drag onto a knob to modulate it">LFO ${i + 1}</button>`).join("");
        const opts = LFO_PRESETS.map((p, i) => `<option value="${i}">${p.n}</option>`).join("") + `<option value="-1">Drawn</option>`;
        let sets = "";
        for (let i = 0; i < 10; i++) {
            sets += `<div class="lfo-set" data-lfo="${i}">`
                + `<div class="ls-top"><div class="ls-shape"><span class="lbl">Shape</span><select class="dd lfo-preset">${opts}</select></div>`
                + `<div class="ls-mode">${this.controlHTML(882 + 5 * i)}</div><div class="ls-sync">${this.controlHTML(502 + 2 * i)}</div><div class="ls-div">${this.controlHTML(503 + 2 * i)}</div><div class="ls-pol">${this.controlHTML(3111 + i)}</div></div>`
                + `<div class="ls-knobs">${[248 + 2 * i, 883 + 5 * i, 884 + 5 * i, 885 + 5 * i, 886 + 5 * i].map(id => this.controlHTML(id, true)).join("")}</div>`
                + `<div class="ls-hid">${this.controlHTML(247 + 2 * i)}</div></div>`;
        }
        return `<section class="bs-lfo"><div class="bs-chips">${chips}<span class="bs-gap"></span><button type="button" class="bs-btn lfo-grid" title="Grid snap">GRID OFF</button></div>`
            + `<div class="bs-lfobody"><div class="lfo-cv"><canvas class="lfo-canvas" width="640" height="150"></canvas><div class="lfo-help">click: add point &middot; drag: move &middot; dbl-click point: delete &middot; drag the diamond: curve</div></div>`
            + `<div class="lfo-sets">${sets}</div></div></section>`;
    }

    // Freq modulators: a curve of frequency over time; they only reach the cutoff knobs and the oscillator Frequency knobs
    frqPanelHTML () {
        const chips = Array.from({ length: 10 }, (_, i) => `<button type="button" class="msrc" data-src="${24 + i}" title="Drag onto a cutoff or Frequency knob">FREQ ${i + 1}</button>`).join("");
        let sets = "";
        for (let i = 0; i < 10; i++) {
            const b = FRQ_BASE + 4 * i;
            sets += `<div class="frq-set" data-frq="${i}"><div class="fs-btns">${this.controlHTML(b + 2)}${this.controlHTML(b + 3)}</div><div class="fs-knobs">${this.controlHTML(b, true)}${this.controlHTML(b + 1, true)}</div></div>`;
        }
        return `<section class="bs-frqs"><div class="bs-chips">${chips}<span class="bs-gap"></span><span class="frq-note">only onto cutoff and Frequency knobs</span></div>`
            + `<div class="bs-frqbody"><div class="lfo-cv"><canvas class="frq-canvas" width="640" height="150"></canvas><div class="lfo-help">click: add point &middot; drag: move &middot; dbl-click point: delete &middot; drag the diamond: curve</div></div>`
            + `<div class="frq-sets">${sets}</div></div></section>`;
    }

    modStripHTML () {
        return `<div class="bstrip"><div class="bs-tabs"><button type="button" class="bst on" data-bs="mod">MOD</button><button type="button" class="bst" data-bs="frq">FREQ</button><button type="button" class="bst" data-bs="mtx">MATRIX</button>`
            + `<span class="bs-hint">drag an LFO / ENV handle onto a knob &middot; click a knob's dot to set the amount</span><button type="button" class="bs-toggle" title="Show / hide the strip">&#9662;</button></div>`
            + `<div class="bs-body"><div class="bs-pane bs-mod on">${this.envPanelHTML()}${this.lfoPanelHTML()}</div><div class="bs-pane bs-frq">${this.frqPanelHTML()}</div><div class="bs-pane bs-mtx">${this.matrixHTML()}</div></div></div>`;
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
        if (open) { this.drawLfo(); this.drawEnv(); this.drawFrq(); }
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

    // ---- Freq modulators: curve points {x 0..1 (time), y 0..1 (20 Hz .. 20 kHz, log), c curve}; the DSP reads a 256 value table ----
    frqDefaultPts () { return [1, 0.5625, 0.25, 0.0625, 0].map((y, k) => ({ x: k / 4, y, c: 0 })); }   // falling curve like the built-in table
    frqEnsurePts (i) {
        if (!this._frqPts[i]) this._frqPts[i] = this.frqDefaultPts();
        return this._frqPts[i];
    }
    frqSend (i) {
        const pts = this._frqPts[i];
        const data = pts ? lfoTableFromPts(pts).map(v => Math.max(0, Math.min(1, v))) : null;
        if (data) try { this.pc.sendEventOrValue("frqShapeLoad", { lfo: i, data }); } catch (_) {}
    }
    frqRound (p) { return p ? p.map(q => ({ x: Math.round(q.x * 1e4) / 1e4, y: Math.round(q.y * 1e4) / 1e4, c: Math.round((q.c || 0) * 1e3) / 1e3 })) : null; }
    frqCommit (i, final) {
        if (final) {
            this.frqSend(i);
            try { this.kvSet(FRQ_STATE_KEY, this._frqPts.map(p => this.frqRound(p))); } catch (_) {}
            if (this.presetDirty) this.presetDirty();
        } else if (!this._frqSendTimer) {
            this._frqSendTimer = setTimeout(() => { this._frqSendTimer = null; this.frqSend(i); }, 60);
        }
        this.drawFrq();
    }
    collectFrq () { return this._frqPts.map(p => this.frqRound(p)); }
    applyFrq (list) {
        const ok = p => Array.isArray(p) && p.length >= 2 && p.every(q => q && Number.isFinite(q.x) && Number.isFinite(q.y));
        for (let i = 0; i < 10; i++) {
            const p = list && ok(list[i]) ? list[i].map(q => ({ x: Math.max(0, Math.min(1, q.x)), y: Math.max(0, Math.min(1, q.y)), c: Math.max(-1, Math.min(1, Number(q.c) || 0)) })) : null;
            this._frqPts[i] = p;
            if (p) this.frqSend(i);
            else this.pc.sendEventOrValue("frqShapeLoad", { lfo: i, data: Array.from({ length: 256 }, (_, k) => Math.pow(1 - k / 255, 2)) });
        }
        try { this.kvSet(FRQ_STATE_KEY, this._frqPts.map(p => this.frqRound(p))); } catch (_) {}
        this.drawFrq();
    }
    restoreFrq () {
        const v = this.kvGet(FRQ_STATE_KEY);
        if (Array.isArray(v)) this.applyFrq(v);
    }
    selectFrq (i) {
        this._frqSel = i;
        this.querySelectorAll(".bs-frqs .msrc").forEach(c => c.classList.toggle("on", Number(c.dataset.src) === i + 24));
        this.querySelectorAll(".frq-set").forEach(s => s.classList.toggle("on", Number(s.dataset.frq) === i));
        this.drawFrq();
    }
    frqGeom (cv) {
        const W = cv.width, H = cv.height, padL = 34, padR = 10, padT = 10, padB = 18;
        return { W, H, px: x => padL + x * (W - padL - padR), py: y => H - padB - y * (H - padT - padB),
            ix: X => (X - padL) / (W - padL - padR), iy: Y => (H - padB - Y) / (H - padT - padB), padL, padB, padR, padT };
    }
    drawFrq () {
        const cv = this.querySelector(".frq-canvas");
        if (!cv || !this._stripOpen) return;
        const ctx = cv.getContext("2d"), g = this.frqGeom(cv), i = this._frqSel, P = this._frqPts[i] || this.frqDefaultPts();
        const rateCtl = this.fxCtl(FRQ_BASE + 4 * i), rate = rateCtl ? rateCtl.value : 300;
        ctx.clearRect(0, 0, g.W, g.H);
        ctx.fillStyle = "#0b0405"; ctx.fillRect(0, 0, g.W, g.H);
        ctx.lineWidth = 1; ctx.font = "9px sans-serif"; ctx.textBaseline = "middle";
        FRQ_AXIS.forEach(([f, t]) => {
            const y = Math.round(g.py(Math.log(f / 20) / Math.log(1000))) + 0.5;
            ctx.strokeStyle = "rgba(255,255,255,0.07)"; ctx.beginPath(); ctx.moveTo(g.padL, y); ctx.lineTo(g.W - g.padR, y); ctx.stroke();
            ctx.fillStyle = "rgba(255,255,255,0.45)"; ctx.textAlign = "right"; ctx.fillText(t, g.padL - 4, y);
        });
        ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
        for (let k = 1; k <= 5; k++) {
            const x = Math.round(g.px(k / 6)) + 0.5, ms = rate * k / 6;
            ctx.strokeStyle = "rgba(255,255,255,0.07)"; ctx.beginPath(); ctx.moveTo(x, g.padT); ctx.lineTo(x, g.H - g.padB); ctx.stroke();
            ctx.fillStyle = "rgba(255,255,255,0.45)"; ctx.fillText(ms >= 1000 ? (ms / 1000).toFixed(1) + " s" : Math.round(ms) + " ms", x, g.H - 5);
        }
        const path = () => { ctx.beginPath(); for (let k = 0; k <= 400; k++) { const p = k / 400, X = g.px(p), Y = g.py(lfoSampleAt(P, p)); if (k === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y); } };
        path(); ctx.lineTo(g.px(1), g.py(0)); ctx.lineTo(g.px(0), g.py(0)); ctx.closePath(); ctx.fillStyle = "rgba(255,90,60,0.16)"; ctx.fill();
        path(); ctx.strokeStyle = "#ff6a4d"; ctx.lineWidth = 2; ctx.stroke();
        for (let k = 0; k + 1 < P.length; k++) {
            const a = P[k], b = P[k + 1];
            if (b.x - a.x < 0.02) continue;
            ctx.beginPath(); ctx.arc(g.px((a.x + b.x) / 2), g.py(lfoCurve(a.y, b.y, a.c || 0, 0.5)), 3, 0, 7);
            ctx.fillStyle = "#2a1210"; ctx.fill(); ctx.strokeStyle = "#ffb09e"; ctx.lineWidth = 1.2; ctx.stroke();
        }
        P.forEach(q => { ctx.beginPath(); ctx.arc(g.px(q.x), g.py(q.y), 5, 0, 7); ctx.fillStyle = "#ff8068"; ctx.fill(); ctx.strokeStyle = "#ffd9cf"; ctx.lineWidth = 1.5; ctx.stroke(); });
    }
    buildFrqCanvas () {
        const cv = this.querySelector(".frq-canvas");
        if (!cv) return;
        let drag = null;
        const pos = e => { const r = cv.getBoundingClientRect(); return { X: (e.clientX - r.left) * cv.width / r.width, Y: (e.clientY - r.top) * cv.height / r.height }; };
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
            const i = this._frqSel, g = this.frqGeom(cv), { X, Y } = pos(e), P = this.frqEnsurePts(i);
            let h = hit(P, g, X, Y);
            if (!h) {
                const x = Math.max(0.004, Math.min(0.996, g.ix(X))), y = Math.max(0, Math.min(1, g.iy(Y)));
                let k = 0;
                while (k < P.length && P[k].x < x) k++;
                if (k === 0 || k >= P.length) return;
                P.splice(k, 0, { x, y, c: 0 });
                h = { kind: "pt", k };
                this.frqCommit(i, false);
            }
            drag = { pid: e.pointerId, h, y0: Y, c0: h.kind === "cv" ? (P[h.k].c || 0) : 0 };
            try { cv.setPointerCapture(e.pointerId); } catch (_) {}
            e.preventDefault();
        });
        cv.addEventListener("pointermove", e => {
            if (!drag || e.pointerId !== drag.pid) return;
            const i = this._frqSel, g = this.frqGeom(cv), P = this.frqEnsurePts(i), { X, Y } = pos(e), h = drag.h;
            if (h.kind === "pt") {
                const q = P[h.k];
                q.y = Math.max(0, Math.min(1, g.iy(Y)));
                if (h.k > 0 && h.k < P.length - 1) q.x = Math.max(P[h.k - 1].x + 0.002, Math.min(P[h.k + 1].x - 0.002, g.ix(X)));
            } else {
                const a = P[h.k], b = P[h.k + 1], dir = Math.sign(b.y - a.y) || 1;
                a.c = Math.max(-1, Math.min(1, drag.c0 + (Y - drag.y0) / 70 * dir));
            }
            this.frqCommit(i, false);
        });
        const end = e => {
            if (!drag || e.pointerId !== drag.pid) return;
            drag = null;
            try { cv.releasePointerCapture(e.pointerId); } catch (_) {}
            if (this._frqSendTimer) { clearTimeout(this._frqSendTimer); this._frqSendTimer = null; }
            this.frqCommit(this._frqSel, true);
        };
        cv.addEventListener("pointerup", end);
        cv.addEventListener("pointercancel", end);
        cv.addEventListener("dblclick", e => {
            const i = this._frqSel, g = this.frqGeom(cv), P = this.frqEnsurePts(i), { X, Y } = pos(e), h = hit(P, g, X, Y);
            if (!h) return;
            if (h.kind === "pt" && h.k > 0 && h.k < P.length - 1) P.splice(h.k, 1);
            else if (h.kind === "cv") P[h.k].c = 0;
            else return;
            this.frqCommit(i, true);
        });
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
    // src: a Freq modulator (24..33) only reaches the cutoff knobs and the oscillator Frequency knobs
    modTargetOf (node, src) {
        const t = this.modTargetOf0(node);
        if (t && src >= 24) {
            const k = (t.num - OSC_BASE) % OSC_STRIDE;
            if (!(t.num >= OSC_BASE && t.num < OSC_BASE + OSC_STRIDE * OSC_N && (k === OSC_K.fcut || k === OSC_K.freq))) return null;
        }
        return t;
    }

    modTargetOf0 (node) {
        const cell = node && node.closest ? node.closest(".fmx-c") : null;
        if (cell) {   // a cell of the FM / PM / PD matrix: modulates its amount
            const panel = cell.closest(".fmx-panel"), k = panel ? this.fmxKinds().find(x => x.key === panel.dataset.k) : null;
            if (k) {
                const num = k.base + 6 * Number(cell.dataset.s) + Number(cell.dataset.d), t = MOD_TARGET[num];
                if (t) return { node: cell.classList.contains("fmx-d") ? cell.querySelector(".fmx-fb") : cell, num, dst: t[0], scale: t[1] };
            }
            return null;
        }
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
            if (!t || (num >= FM_BASE && num < AM_BASE + 36) || (num >= TZ_BASE && num < TZ_BASE + 36)) return;   // matrix cells have their own marks (fmxModMarks)
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
        if (!onlyNum || (onlyNum >= FM_BASE && onlyNum < AM_BASE + 36) || (onlyNum >= TZ_BASE && onlyNum < TZ_BASE + 36)) this.fmxModMarks();
    }

    // little dots on the FM / PM / PD cells that are modulated (click = amount popup)
    fmxModMarks () {
        this.fmxKinds().forEach(k => {
            const panel = this.querySelector('.fmx-panel[data-k="' + k.key + '"]');
            if (!panel) return;
            panel.querySelectorAll(".fmx-c").forEach(el => {
                const sr = Number(el.dataset.s), d = Number(el.dataset.d), num = k.base + 6 * sr + d, t = MOD_TARGET[num];
                const box = el.classList.contains("fmx-d") ? el.querySelector(".fmx-fb") : el;
                if (!t || !box) return;
                const mods = this.modsFor(t[0]).filter(m => Math.abs(m.amt) > 0.0005);
                let dot = box.querySelector(".fmx-md");
                if (!mods.length) { if (dot) dot.remove(); box.classList.remove("modded"); return; }
                box.classList.add("modded");
                if (!dot) {
                    dot = document.createElement("span"); dot.className = "fmx-md"; dot.title = "Modulation amount";
                    dot.addEventListener("pointerdown", e => e.stopPropagation());
                    dot.addEventListener("click", e => { e.stopPropagation(); this.showModPop(box, num); });
                    box.appendChild(dot);
                }
                dot.style.background = MOD_SRC_COLOR(mods[0].src);
                dot.textContent = mods.length > 1 ? String(mods.length) : "";
            });
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
        const sp0 = SPEC_BY_NUM.get(num) || {};
        const label = ((num >= FM_BASE && num < AM_BASE + 36) || (num >= TZ_BASE && num < TZ_BASE + 36)) ? sp0.label : (sp0.short || sp0.label || "");
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
                const tg = this.modTargetOf(el, src);
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
                } else if (src >= 24) { this.selectFrq(src - 24); }
                else if (src >= 1 && src <= 10) { this.selectLfo(src - 1); }
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
        this.buildFrqCanvas();
        this.buildModDrag();
        this.showStrip("mod");
        this.setStripOpen(open);
        this.selectLfo(0);
        this.selectEnv(0);
        this.selectFrq(0);
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
        const oscPages = Array.from({ length: OSC_N }, (_, o) => `<div class="page p-o${o}" data-src="0">${this.oscPageHTML(o)}</div>`).join("\n    ")
            + "\n    " + Array.from({ length: OSC_N }, (_, o) => `<div class="page p-f${o}" data-src="f">${this.fltPageHTML(o)}</div>`).join("\n    ")
            + "\n    " + Array.from({ length: OSC_N }, (_, o) => `<div class="page p-d${o}" data-src="d">${this.distPageHTML(o)}</div>`).join("\n    ");
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
  eisenpuls-view[data-page="f0"] .p-f0, eisenpuls-view[data-page="f1"] .p-f1, eisenpuls-view[data-page="f2"] .p-f2, eisenpuls-view[data-page="f3"] .p-f3,
  eisenpuls-view[data-page="f4"] .p-f4, eisenpuls-view[data-page="f5"] .p-f5, eisenpuls-view[data-page="d0"] .p-d0, eisenpuls-view[data-page="d1"] .p-d1,
  eisenpuls-view[data-page="d2"] .p-d2, eisenpuls-view[data-page="d3"] .p-d3, eisenpuls-view[data-page="d4"] .p-d4, eisenpuls-view[data-page="d5"] .p-d5 { display: grid; }
  eisenpuls-view[data-page="fm"] .p-fm { display: grid; }
  eisenpuls-view[data-page="rm"] .p-rm { display: grid; }
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

  .mgr-status, .wt-status, .s2-status { flex: 0 0 auto; margin-top: calc(var(--u) * 6); padding: calc(var(--u) * 4) calc(var(--u) * 6); border: 1px solid var(--line); border-radius: 1px; background: #110505; box-shadow: inset 0 0 6px rgba(0,0,0,0.9); }
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
           grid-template-columns: calc(var(--u) * 34) calc(var(--u) * 18) calc(var(--u) * 34) calc(var(--u) * 112) calc(var(--u) * 70) calc(var(--u) * 92) calc(var(--u) * 74) minmax(0, 1fr);
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
  .fxon .control .row, .fxty .control .row, .fxmd .control .row, .fxsy .control .row { display: none; }
  .fxon .grp { display: flex; }
  .fxon .grp button { padding: calc(var(--u) * 5) calc(var(--u) * 3); font-size: calc(var(--u) * 8); }
  .fxty select, .fxmd select, .fxsy select { width: 100%; }
  .fxrow.empty .fxmd, .fxrow.nomode .fxmd, .fxrow.empty .fxsy, .fxrow.nosync .fxsy { visibility: hidden; }
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
  eisenpuls-view[data-group="synth"] .subtabs { display: flex; }
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
  .bs-frqs { flex: 1 1 0; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .bs-frqs .msrc { border-color: #5b3a85; } .bs-frqs .msrc.on { background: #b57bff; color: #111; }
  .bs-frqbody { flex: 1 1 0; min-height: 0; display: flex; gap: calc(var(--u) * 8); }
  .frq-canvas { width: 100%; flex: 1 1 0; min-height: 0; display: block; background: #0b0405; border: 1px solid var(--line); border-radius: 2px; touch-action: none; }
  .frq-sets { flex: 0 0 calc(var(--u) * 190); display: flex; flex-direction: column; justify-content: center; }
  .frq-note { font-size: calc(var(--u) * 8); color: var(--dim); letter-spacing: 0.05em; align-self: center; }
  .frq-set { display: none; } .frq-set.on { display: flex; flex-direction: column; gap: calc(var(--u) * 10); }
  .fs-btns { display: flex; flex-direction: column; gap: calc(var(--u) * 4); } .fs-knobs { display: grid; grid-template-columns: 1fr 1fr; gap: calc(var(--u) * 6); }
  .bs-frqs .knb .knob { width: calc(var(--u) * 28); height: calc(var(--u) * 28); }
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
  .o-src { grid-column: 1 / span 5; } .o-tune { grid-column: 6 / span 4; } .o-out { grid-column: 10 / span 3; }
  .o-fl { grid-column: 1 / span 8; } .o-tb { grid-column: 9 / span 4; } .o-tb.off .tbl-canvas, .o-tb.off .o-tbl { opacity: 0.45; }
  .o-note { flex: 0 0 auto; margin-top: calc(var(--u) * 6); font-size: calc(var(--u) * 8); line-height: 1.35; color: var(--dim); letter-spacing: 0.04em; }
  .o-frow { flex: 0 0 auto; display: flex; gap: calc(var(--u) * 8); align-items: center; margin-top: calc(var(--u) * 6); }
  .o-frow .control { flex: 1 1 0; min-width: 0; }
  .o-mode { display: flex; flex: 0 0 auto; gap: 0; }
  .o-mode button { font-family: inherit; font-size: calc(var(--u) * 9); font-weight: 800; letter-spacing: 0.08em; padding: calc(var(--u) * 6) calc(var(--u) * 12); border: 1px solid var(--line); background: var(--panel2); color: var(--ink); cursor: pointer; }
  .o-mode button.on { background: var(--yel); color: #111; border-color: var(--yel); }
  .o-g5 { grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .o-fl .cgrid { margin-top: calc(var(--u) * 4); }
  .o-fl .flt-canvas, .o-fl .dist-canvas { height: calc(var(--u) * 150); } .tbl-canvas, .dist-canvas { display: block; flex: 0 0 auto; width: 100%; background: #0d0404; border: 1px solid #7a1d18; border-radius: calc(var(--u) * 4); margin-top: calc(var(--u) * 5); }
  .o-tb .tbl-canvas { height: calc(var(--u) * 190); }
  .otab { font-family: inherit; font-size: calc(var(--u) * 9.5); font-weight: 800; letter-spacing: 0.08em; padding: calc(var(--u) * 3) calc(var(--u) * 9); border: 1px solid var(--line); border-radius: 1px; background: var(--panel2); color: var(--ink); cursor: pointer; }
  .otab.on { background: var(--yel); color: #111; border-color: var(--yel); }
  .o-tbl { display: flex; flex-direction: column; gap: calc(var(--u) * 4); margin-top: calc(var(--u) * 4); } .o-tbl .dz { margin: 0; } .control.dim { opacity: 0.45; }
  .o-g2 { grid-template-columns: repeat(2, minmax(0, 1fr)); } .o-g3 { grid-template-columns: repeat(3, minmax(0, 1fr)); } .o-g4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .card .cgrid { flex: 1 1 auto; align-content: space-evenly; align-items: center; row-gap: calc(var(--u) * 3); }
  .o-src .cgrid, .o-tune .cgrid { margin-top: calc(var(--u) * 4); }
  .o-type { flex: 0 0 auto; } .o-type .control .row { display: none; }
  .osc-canvas, .flt-canvas { display: block; flex: 0 0 auto; width: 100%; height: calc(var(--u) * 96); margin-top: calc(var(--u) * 5); background: #0d0404; border: 1px solid #7a1d18; border-radius: calc(var(--u) * 4); box-shadow: inset 0 0 14px rgba(0,0,0,0.95), 0 0 14px rgba(255,59,48,0.25); }
  .osc-info { flex: 0 0 auto; margin-top: calc(var(--u) * 3); font-family: ui-monospace, Menlo, Consolas, monospace; font-size: calc(var(--u) * 7.5); letter-spacing: 0.06em; color: var(--dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .o-mem { flex: 0 0 auto; display: flex; gap: calc(var(--u) * 6); align-items: stretch; margin-top: calc(var(--u) * 4); }
  .o-mem .dz { flex: 1 1 auto; margin: 0; height: calc(var(--u) * 26); font-size: calc(var(--u) * 9); }
  .o-sub, .o-uni { display: contents; }
  .o-uni { display: grid; margin-top: calc(var(--u) * 2); }
  .o-uh { grid-column: 1 / -1; font-size: calc(var(--u) * 8); font-weight: 800; letter-spacing: 0.16em; color: var(--org); text-transform: uppercase; }
  .o-h2 { margin-top: calc(var(--u) * 8); }
  .o-fl .cgrid.o-g2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .page[data-src] .cgrid > .control.w2, .page[data-src] .cgrid > .control.wide { grid-column: auto; }
  .page[data-src] .o-out .cgrid > .control.sel, .page[data-src] .o-out .cgrid > .control.btns, .page[data-src] .o-pl > .control.sel,
  .page[data-src] .o-tune .cgrid > .control.btns.wide, .page[data-src] .o-g3 > .control.btns { grid-column: 1 / -1; }
  .o-phy > .o-uh { grid-column: 1 / -1; margin-top: 4px; } .page[data-src] .o-phy:not(.o-juno) > .control.sel { grid-column: 1 / -1; }
  .page[data-src] .knb .knob { width: calc(var(--u) * 32); height: calc(var(--u) * 32); }
  .osc-canvas, .flt-canvas { height: calc(var(--u) * 72); }
  /* FM matrix */
  .p-fm, .p-rm { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
  .fmx-row { flex: 1 1 0; min-height: 0; display: flex; gap: calc(var(--u) * 8); margin-top: calc(var(--u) * 4); }
  .fmx-panel { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; min-height: 0; }
  .fmx-title { flex: 0 0 auto; font-size: calc(var(--u) * 8); letter-spacing: 0.1em; text-transform: uppercase; color: var(--dim); padding: 0 0 calc(var(--u) * 3) calc(var(--u) * 2); }
  .fmx-title b { font-family: Impact, "Arial Black", sans-serif; font-size: calc(var(--u) * 14); font-weight: 400; color: var(--yel); letter-spacing: 0.08em; margin-right: calc(var(--u) * 4); }
  .fmx { position: relative; flex: 1 1 0; min-height: 0; border: 1px solid var(--line); border-radius: calc(var(--u) * 3); background: radial-gradient(ellipse at center, #1c0a0a, #0b0404); box-shadow: inset 0 0 14px #000; }
  .fmx-grid { position: absolute; inset: calc(var(--u) * 6); display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); grid-template-rows: repeat(6, minmax(0, 1fr)); }
  .fmx-svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; filter: drop-shadow(0 0 3px rgba(255,59,48,0.35)); }
  .fmx-c { position: relative; display: flex; align-items: center; justify-content: center; cursor: ns-resize; touch-action: none; }
  .fmx-c:not(.fmx-d):hover { background: rgba(255,255,255,0.04); }
  .fmx-dot { width: calc(var(--u) * 5); height: calc(var(--u) * 5); border-radius: 50%; background: #5a2a26; box-shadow: 0 0 0 1px #000; }
  .fmx-c:has(.fmx-v:empty) .fmx-v { display: none; }
  .fmx-c .fmx-v, .fmx-fb .fmx-v { position: relative; z-index: 3; font-size: calc(var(--u) * 8.5); font-weight: 800; color: #fff; padding: calc(var(--u) * 1.5) calc(var(--u) * 4); border-radius: calc(var(--u) * 3); background: #7d1a14; border: 1px solid #ff5a4a; box-shadow: 0 0 8px rgba(255,59,48,0.45); min-width: calc(var(--u) * 22); text-align: center; }
  .fmx-c.on .fmx-dot { display: none; }
  .fmx-fb { position: relative; }
  .fmx-md { position: absolute; top: calc(var(--u) * 2); right: calc(var(--u) * 2); min-width: calc(var(--u) * 11); height: calc(var(--u) * 11); border-radius: 50%; z-index: 5; cursor: pointer; font-size: calc(var(--u) * 7); font-weight: 800; color: #000; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 6px rgba(0,0,0,0.8); }
  .fmx-c.neg .fmx-v { background: #163e66; border-color: #59b7ff; box-shadow: 0 0 8px rgba(89,183,255,0.45); }
  .fmx-d { gap: calc(var(--u) * 6); cursor: default; }
  .fmx-n { position: relative; z-index: 3; font-family: Impact, "Arial Black", sans-serif; font-size: calc(var(--u) * 16); width: calc(var(--u) * 30); height: calc(var(--u) * 30); color: var(--dim); background: linear-gradient(#303134, #17181a); border: 1px solid #4c4d51; border-radius: calc(var(--u) * 6); cursor: pointer; }
  .fmx-n.act { color: #fff; background: linear-gradient(#ff4a3a, #a3140c); border-color: #ff6a5c; box-shadow: 0 0 10px var(--glow); }
  .fmx-fb { position: relative; z-index: 3; display: flex; flex-direction: column; align-items: center; gap: calc(var(--u) * 2); cursor: ns-resize; touch-action: none; }
  .fmx-fbl { font-size: calc(var(--u) * 7); letter-spacing: 0.1em; color: var(--dim); }
  .fmx-fb .fmx-v { background: rgba(0,0,0,0.5); border-color: #4c4d51; box-shadow: none; color: var(--dim); }
  .fmx-fb.on .fmx-v { background: #7d1a14; border-color: #ff5a4a; color: #fff; box-shadow: 0 0 8px rgba(255,59,48,0.45); }
  .fmx-fb.on.neg .fmx-v { background: #163e66; border-color: #59b7ff; box-shadow: 0 0 8px rgba(89,183,255,0.45); }
  .fmx-hid { display: none; }
  .fm-note { flex: 0 0 auto; margin-top: calc(var(--u) * 5); font-size: calc(var(--u) * 8); color: var(--dim); letter-spacing: 0.04em; }
  /* global page */
  .p-glob { grid-template-columns: repeat(12, minmax(0, 1fr)); grid-template-rows: minmax(0, 1fr); }
  .g-voice { grid-column: 1 / span 2; } .g-amp { grid-column: 3 / span 3; } .g-peg { grid-column: 6 / span 2; } .g-out { grid-column: 8 / span 5; }
  .g-voice .cgrid, .g-peg .cgrid { grid-template-columns: minmax(0, 1fr); } .g-amp .cgrid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .g-out .cgrid { grid-template-columns: repeat(3, minmax(0, 1fr)); }

  /* left page rail: synth / effects / modulation, top to bottom */
  .body { flex: 1 1 0; min-height: 0; display: flex; gap: calc(var(--u) * 8); }
  .main { flex: 1 1 0; min-width: 0; min-height: 0; display: flex; flex-direction: column; gap: calc(var(--u) * 6); }
  .prail { flex: 0 0 calc(var(--u) * 66); display: flex; flex-direction: column; gap: calc(var(--u) * 6); }
  .rb { flex: 1 1 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: calc(var(--u) * 6); font-family: inherit; font-size: calc(var(--u) * 8); font-weight: 800; letter-spacing: 0.06em; color: var(--ink); cursor: pointer; background: linear-gradient(#303134, #17181a); border: 1px solid #4c4d51; border-radius: calc(var(--u) * 8) 1px calc(var(--u) * 8) 1px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.12); }
  .rb b { font-family: Impact, "Arial Black", sans-serif; font-size: calc(var(--u) * 26); font-weight: 400; color: var(--dim); letter-spacing: 0; }
  .rb:hover { border-color: #ff3b30; color: #fff; }
  .rb.on { background: linear-gradient(#ff4a3a, #a3140c); color: #fff; border-color: #ff6a5c; text-shadow: 0 1px 0 rgba(0,0,0,0.6); box-shadow: 0 0 10px var(--glow), inset 0 1px 0 rgba(255,255,255,0.35); }
  .rb.on b { color: rgba(255,255,255,0.85); }
  .stab-x { margin-left: auto; }
  .stab-x + .stab { margin-left: 0; }
  /* modulation page: matrix and editors fill the window, the stage is hidden */
  eisenpuls-view[data-group="mod"] .stage { display: none; }
  eisenpuls-view[data-group="mod"] .bstrip { flex: 1 1 0; height: auto; min-height: 0; }
  eisenpuls-view[data-group="mod"] .bs-tabs .bst, eisenpuls-view[data-group="mod"] .bs-toggle, eisenpuls-view[data-group="mod"] .bs-hint { display: none; }
  eisenpuls-view[data-group="mod"] .bs-tabs::before { content: "MODULATION MATRIX"; font-family: Impact, "Arial Black", sans-serif; letter-spacing: 0.12em; font-size: calc(var(--u) * 11); color: var(--yel); }
  eisenpuls-view[data-group="mod"] .bs-body { display: flex; flex-direction: column; gap: calc(var(--u) * 6); }
  eisenpuls-view[data-group="mod"] .bs-pane { position: relative; inset: auto; display: flex !important; flex: 1 1 0; min-height: 0; }
  eisenpuls-view[data-group="mod"] .bs-mtx { display: block !important; overflow: auto; flex: 1.1 1 0; }
  eisenpuls-view:not([data-group="mod"]) .bst[data-bs="mtx"] { display: none; }
</style>
<div class="shell">
  <div class="top">
    <span class="logo">NJOHRR</span><span class="model">SYNTH</span><span class="version">V1.0.0</span>
    <div class="vu"><div class="vu-fill"></div></div>
    <select class="dd sizesel" title="Window size" style="display:none"><option value="0.75">75%</option><option value="1">100%</option><option value="1.25">125%</option><option value="1.5">150%</option><option value="1.75">175%</option><option value="2">200%</option><option value="custom" hidden>Custom</option></select>
    <div class="lcd"><span class="lcd-mode">OSC</span><span class="lcd-name">--</span><span class="lcd-val">--</span></div><span class="led"></span>
  </div>
  <div class="hz"></div>
  <div class="body">
    <nav class="prail"><button type="button" class="rb on" data-group="synth"><b>1</b>SYNTH</button><button type="button" class="rb" data-group="fx"><b>2</b>EFFECTS</button><button type="button" class="rb" data-group="mod"><b>3</b>MODULATION</button></nav>
    <div class="main">
    <div class="subtabs"><button type="button" class="stab on" data-page="o0">OSC 1</button><button type="button" class="stab" data-page="o1">OSC 2</button><button type="button" class="stab" data-page="o2">OSC 3</button><button type="button" class="stab" data-page="o3">OSC 4</button><button type="button" class="stab" data-page="o4">OSC 5</button><button type="button" class="stab" data-page="o5">OSC 6</button><button type="button" class="stab stab-x" data-page="f0" data-grp="f">FILTER</button><button type="button" class="stab" data-page="d0" data-grp="d">DIST</button><button type="button" class="stab" data-page="fm">FM / PM / PD</button><button type="button" class="stab stab-x" data-page="rm">RM / AM</button><button type="button" class="stab" data-page="glob">GLOBAL</button></div>
      ${MGR_HTML}
      <div class="stage">
        ${oscPages}
        <div class="page p-fm">${this.fmPageHTML("fm")}</div>
        <div class="page p-rm">${this.fmPageHTML("rm")}</div>
        <div class="page p-glob">${this.globalPageHTML()}</div>
        <div class="page p-fx">${fxPage}</div>
      </div>
      ${strip}
    </div>
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
const AUDIO_EXT = /\.(wav|wave|w64|rf64|bwf|aif|aiff|aifc|afc|au|snd|caf|flac|mp3|mp2|mpga|ogg|oga|opus|spx|m4a|m4b|mp4|aac|adts|webm|mka|3gp|amr|wma|raw|pcm|sam|smp|dat|bin|sd|s16)$/i;
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
        const rec = { name, saved: Date.now(), params: this.collectParams(), refs: this.collectRefs(), lfo: this.collectLfo(), frq: this.collectFrq() };
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
            this.applyFrq(rec.frq);
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
                const dec = await this.decodeFile(f, this._libKind === "sample" ? "sm" : "wt");
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
                inp.type = "file"; inp.multiple = true; inp.accept = ".vitaltable,audio/*,video/mp4,video/webm,.wav,.w64,.rf64,.bwf,.aif,.aiff,.aifc,.au,.snd,.caf,.flac,.mp3,.mp2,.ogg,.oga,.opus,.m4a,.aac,.webm,.raw,.pcm";
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
