#!/usr/bin/env python3
"""One-shot migration of patch/index.js from the fixed FX cards to the modular FX rack page (asserts on every edit)."""
import re, sys
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8")
assert "FX_TYPES" not in s, "already patched"

def sub1(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)

# ------------------------------------------------------------------ SPECS: drop the legacy fixed-chain controls
REMOVED = [30, 31, 32, 60, 61, 62] + list(range(164, 175)) + list(range(177, 189)) + [191, 537, 538, 539, 540]
lines, out, dropped = s.split("\n"), [], 0
for ln in lines:
    m = re.match(r"\s*(?:L\.push\()?\[(\d+),\s", ln)
    if m and int(m.group(1)) in REMOVED and ("sld" in ln or "btn" in ln or "sel" in ln):
        dropped += 1
        continue
    out.append(ln)
assert dropped == len(REMOVED), (dropped, len(REMOVED))
s = "\n".join(out)

sub1('''    // fx algorithms
''', '''    // fx algorithm of the synth Drive (the rack effects carry their own mode selector)
''')
sub1('''    // short control names for the FX cards (the card title already says which effect it is)
    const FX_SHORT = { 164: "Mix", 165: "Rate", 166: "Depth", 177: "Fdbk", 185: "Mix", 186: "Rate", 187: "Depth", 188: "Fdbk",
        167: "Mix", 168: "Rate", 169: "Depth", 178: "Fdbk", 170: "Mix", 171: "Size", 172: "Damp", 179: "PreDly", 180: "Width",
        173: "Depth", 174: "Rate", 182: "Stereo", 30: "Time", 31: "Fdbk", 60: "Damp", 183: "Mix", 184: "Ping-Pong",
        61: "Bit Crush", 62: "SR Reduce", 191: "Crush Mix", 175: "Width", 189: "Tone", 28: "Drive" };
''', '''    // FX rack: 10 slots x (type, on, mix, mode, P1..P6) at 541..640, processing order at 641..650
    for (let sl = 0; sl < 10; sl++) {
        const b = 541 + sl * 10, n = sl + 1;
        L.push([b,     "FX " + n + " Type", 0, 11, 0, "", "sel", FX_TYPES.map(t => t.n), 1, "Type"]);
        L.push([b + 1, "FX " + n + " On",   0, 1, 1, "", "btn", ["Off", "On"], 1, "On"]);
        L.push([b + 2, "FX " + n + " Mix",  0, 1, 1, "", "sld", null, 1, "Mix"]);
        L.push([b + 3, "FX " + n + " Mode", 0, 5, 0, "", "sel", ["1", "2", "3", "4", "5", "6"], 1, "Mode"]);
        for (let k = 0; k < 6; k++) L.push([b + 4 + k, "FX " + n + " P" + (k + 1), 0, 1, 0.5, "", "sld", null, 1, "P" + (k + 1)]);
    }
    for (let k = 0; k < 10; k++) L.push([641 + k, "FX Order " + (k + 1), 0, 9, k, "", "stp", null, 1, "Order"]);
    // short control names for the output card
    const FX_SHORT = { 175: "Width", 189: "Tone", 28: "Drive" };
''')

# ------------------------------------------------------------------ FX type table (before SPECS) + helpers
TABLE = r'''// ---------------------------------------------------------------------------------------------------------------
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
    { n: "Filter", mix: 1, modes: ["Low Pass", "High Pass", "Band Pass", "Notch"],
      p: [["Cutoff", fxHz(20, 20000), 0.67], ["Reso", fxPct, 0.2], ["Drive", fxPct, 0]] },
    { n: "EQ", mix: 1, modes: [],
      p: [["Low", fxDb(-12, 12), 0.5], ["Mid", fxDb(-12, 12), 0.5], ["Mid Freq", fxHz(200, 5000), 0.5], ["High", fxDb(-12, 12), 0.5], ["Mid Q", n => "Q " + fxExp(0.3, 4)(n).toFixed(2), 0.5]] },
    { n: "Compressor", mix: 1, modes: ["Peak", "RMS"],
      p: [["Thresh", fxLin(-60, 0, 1, "dB"), 0.6], ["Ratio", n => (1 + 19 * n * n).toFixed(1) + ":1", 0.3], ["Attack", fxMs(0.1, 100), 0.4], ["Release", fxMs(10, 1000), 0.4], ["Makeup", fxLin(0, 24, 1, "dB"), 0.2]] }
];
const FX_CUR_TYPE = new Array(10).fill(0);   // what each slot currently holds, read by fmt()
function fxSlotOf (num) { return num >= 541 && num <= 640 ? Math.floor((num - 541) / 10) : -1; }
function fxFmt (s, v) {
    const slot = fxSlotOf(s.num), off = (s.num - 541) % 10, t = FX_TYPES[FX_CUR_TYPE[slot]] || FX_TYPES[0];
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
    for (let k = 541; k <= 650; k++) if (has(String(k))) return params;
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

'''
sub1("// filter page parameters read by the visualizers\n", TABLE + "// filter page parameters read by the visualizers\n")

# ------------------------------------------------------------------ cards / mixer
sub1('''const FX_DELAY = [537, 30, 31, 60, 183, 184];
const FX_CRUSH = [536, 28, 61, 62, 191];
const FX_CHORUS = [538, 164, 165, 166, 177];
const FX_FLANGER = [185, 186, 187, 188];
const FX_PHASER = [539, 167, 168, 169, 178];
const FX_REVERB = [540, 170, 171, 172, 179, 180];
const FX_TREM = [173, 174, 181, 182];
const FX_OUT = [175, 189, 221, 222];
''', '''const FX_OUT = [28, 536, 175, 189, 221, 222];
''')
sub1('''    { p: 32,  n: "Dly Send",  s: 0,   cls: "out" },
''', '')

# fmt(): rack parameters
sub1('''function fmt (s, v) {
''', '''function fmt (s, v) {
    if (s.num >= 541 && s.num <= 640) return fxFmt(s, v);
    if (s.num >= 641 && s.num <= 650) return String(Math.round(v) + 1);
''')

# ------------------------------------------------------------------ page html
sub1('''        const fxPage = this.card("Delay", FX_DELAY, "f-dly")
                     + this.card("Drive / Crush", FX_CRUSH, "f-crush")
                     + this.card("Chorus", FX_CHORUS, "f-cho")
                     + this.card("Flanger", FX_FLANGER, "f-fla")
                     + this.card("Phaser", FX_PHASER, "f-pha")
                     + this.card("Reverb", FX_REVERB, "f-rev")
                     + this.card("Tremolo", FX_TREM, "f-trm")
                     + this.card("Output", FX_OUT, "f-out");''', '''        const fxPage = this.fxPageHTML();''')

sub1('''    card (title, ids, cls, extra, pre) {''', '''    // FX rack page: 10 slots (any effect in any slot, drag the grip or use the arrows to change the order) + output strip
    fxPageHTML () {
        let rows = "";
        for (let sl = 0; sl < 10; sl++) {
            const b = 541 + sl * 10;
            let ks = "";
            for (let k = 0; k < 6; k++) ks += this.controlHTML(b + 4 + k, true);
            rows += `<div class="fxrow empty" data-slot="${sl}">`
                + `<div class="fxord"><button type="button" class="fxup" title="Move up">&#9650;</button><span class="fxpos">${sl + 1}</span><button type="button" class="fxdn" title="Move down">&#9660;</button></div>`
                + `<div class="fxgrip" title="Drag to change the processing order">&#10303;</div>`
                + `<div class="fxon">${this.controlHTML(b + 1)}</div>`
                + `<div class="fxty">${this.controlHTML(b)}</div>`
                + `<div class="fxmd">${this.controlHTML(b + 3)}</div>`
                + `<div class="fxmx">${this.controlHTML(b + 2, true)}</div>`
                + `<div class="fxps">${ks}</div></div>`;
        }
        let hid = "";
        for (let k = 0; k < 10; k++) hid += this.controlHTML(641 + k);
        const out = FX_OUT.map(i => `<div class="fxo">${this.controlHTML(i, true)}</div>`).join("");
        return `<section class="card f-rack"><h2>FX Rack <span class="fxhint">signal runs top to bottom</span></h2><div class="fxlist">${rows}</div><div class="fx-hid">${hid}</div></section>`
            + `<section class="card f-out"><h2>Output</h2><div class="fxoutrow">${out}</div></section>`;
    }

    card (title, ids, cls, extra, pre) {''')

# ------------------------------------------------------------------ css
CSS = '''  /* fx page: the rack */
  .p-fx { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr) auto; }
  .f-rack { grid-column: 1; grid-row: 1; min-height: 0; }
  .f-out { grid-column: 1; grid-row: 2; }
  .fxhint { font-size: calc(var(--u) * 8); letter-spacing: 0.12em; color: var(--dim); font-weight: 700; font-family: "Bahnschrift", "Arial Narrow", sans-serif; }
  .fxlist { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: calc(var(--u) * 2); }
  .fxrow { flex: 1 1 0; min-height: 0; display: grid; align-items: center; column-gap: calc(var(--u) * 8); padding: 0 calc(var(--u) * 6);
           grid-template-columns: calc(var(--u) * 22) calc(var(--u) * 16) calc(var(--u) * 34) calc(var(--u) * 112) calc(var(--u) * 92) calc(var(--u) * 74) minmax(0, 1fr);
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

'''
a = s.index("  /* fx page */")
b = s.index("  .control { min-width: 0; }", a)
s = s[:a] + CSS + s[b:]
sub1(", .w-warp .cgrid, .x-f1 .cgrid, .x-f2 .cgrid, .x-feg .cgrid, .p-fx .cgrid {", ", .w-warp .cgrid, .x-f1 .cgrid, .x-f2 .cgrid, .x-feg .cgrid {")

# ------------------------------------------------------------------ behaviour
sub1('''    onValue (spec, v, user) {
        const n = spec.num;
''', '''    onValue (spec, v, user) {
        const n = spec.num;
        if (n >= 541 && n <= 650) this.onFxValue(spec, v, user);
''')

sub1('''    startAnimationLoop () {''', '''    // ---------- FX rack ----------
    fxCtl (num) { return this._controls.get("param" + num); }

    // refresh labels / visibility / dimming of one slot after its type or on/off changed
    updateFxRow (sl) {
        const row = this.querySelector('.fxrow[data-slot="' + sl + '"]');
        if (!row) return;
        const t = FX_TYPES[FX_CUR_TYPE[sl]] || FX_TYPES[0];
        const b = 541 + sl * 10;
        row.classList.toggle("empty", FX_CUR_TYPE[sl] === 0);
        row.classList.toggle("nomode", t.modes.length === 0);
        const on = this.fxCtl(b + 1);
        row.classList.toggle("off", !!on && on.value < 0.5);
        const mc = this.fxCtl(b + 3);
        if (mc && mc.sel) {
            const cur = mc.value;
            mc.sel.innerHTML = t.modes.map(m => "<option>" + m + "</option>").join("");
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
    }

    onFxValue (spec, v, user) {
        const n = spec.num;
        if (n >= 641) { this.fxApplyOrder(); return; }
        const sl = fxSlotOf(n), off = (n - 541) % 10;
        if (off === 0) {
            FX_CUR_TYPE[sl] = Math.max(0, Math.min(FX_TYPES.length - 1, Math.round(v)));
            this.updateFxRow(sl);
            if (user && !this._applying) {            // a new effect starts from its own sensible settings
                const t = FX_TYPES[FX_CUR_TYPE[sl]], b = 541 + sl * 10;
                const set = (num, val) => { const c = this.fxCtl(num); if (c) c.setValue(val, true); };
                set(b + 1, 1); set(b + 2, t.mix); set(b + 3, 0);
                t.p.forEach((p, k) => set(b + 4 + k, p[2]));
                this.updateFxRow(sl);
            }
        } else if (off === 1) this.updateFxRow(sl);
    }

    // processing order: positions -> slots, taken from the 10 hidden order parameters
    fxOrderNow () {
        const o = [];
        for (let k = 0; k < 10; k++) { const c = this.fxCtl(641 + k); o.push(c ? Math.round(c.value) : k); }
        return o;
    }

    fxApplyOrder (preview) {
        const order = preview || this.fxOrderNow();
        const pos = new Array(10).fill(-1);
        order.forEach((sl, k) => { if (sl >= 0 && sl < 10 && pos[sl] < 0) pos[sl] = k; });
        let spare = order.length;
        for (let sl = 0; sl < 10; sl++) if (pos[sl] < 0) pos[sl] = spare++;     // transient, while a preset is being applied
        this.querySelectorAll(".fxrow").forEach(row => {
            const sl = Number(row.dataset.slot);
            row.style.order = String(pos[sl]);
            const pe = row.querySelector(".fxpos");
            if (pe) pe.textContent = String(pos[sl] + 1);
        });
    }

    fxCommit (order) {
        const cur = this.fxOrderNow();
        for (let k = 0; k < 10; k++) if (order[k] !== cur[k]) { const c = this.fxCtl(641 + k); if (c) c.setValue(order[k], true); }
        this.fxApplyOrder();
    }

    fxMove (sl, to) {
        const order = this.fxOrderNow();
        const from = order.indexOf(sl);
        if (from < 0) return;
        to = Math.max(0, Math.min(9, to));
        if (to === from) return;
        order.splice(from, 1);
        order.splice(to, 0, sl);
        this.fxCommit(order);
    }

    buildFxRack () {
        this.querySelectorAll(".fxrow").forEach(row => {
            const sl = Number(row.dataset.slot);
            row.querySelector(".fxup").addEventListener("click", () => this.fxMove(sl, this.fxOrderNow().indexOf(sl) - 1));
            row.querySelector(".fxdn").addEventListener("click", () => this.fxMove(sl, this.fxOrderNow().indexOf(sl) + 1));
            const grip = row.querySelector(".fxgrip");
            let drag = null;
            grip.addEventListener("pointerdown", e => {
                drag = { pid: e.pointerId, order: this.fxOrderNow() };
                row.classList.add("dragging");
                try { grip.setPointerCapture(e.pointerId); } catch (_) {}
                e.preventDefault();
            });
            grip.addEventListener("pointermove", e => {
                if (!drag || e.pointerId !== drag.pid) return;
                // target position = number of other rows whose centre is above the pointer
                let to = 0;
                this.querySelectorAll(".fxrow").forEach(r => {
                    if (r === row) return;
                    const bb = r.getBoundingClientRect();
                    if (bb.top + bb.height / 2 < e.clientY) to++;
                });
                const order = this.fxOrderNow();
                order.splice(order.indexOf(sl), 1);
                order.splice(to, 0, sl);
                drag.next = order;
                this.fxApplyOrder(order);
            });
            const end = e => {
                if (!drag || e.pointerId !== drag.pid) return;
                row.classList.remove("dragging");
                try { grip.releasePointerCapture(e.pointerId); } catch (_) {}
                const next = drag.next;
                drag = null;
                if (next) this.fxCommit(next); else this.fxApplyOrder();
            };
            grip.addEventListener("pointerup", end);
            grip.addEventListener("pointercancel", end);
        });
        for (let sl = 0; sl < 10; sl++) this.updateFxRow(sl);
        this.fxApplyOrder();
    }

    startAnimationLoop () {''')

sub1('''        this.buildTabs();
        this.buildSmpLoader();''', '''        this.buildTabs();
        this.buildFxRack();
        this.buildSmpLoader();''')

# preset migration
sub1('''            const params = rec.params || {};
            this._controls.forEach((c, id) => {
                if (PRESET_SKIP.has(id)) return;
                const k = id.replace("param", "");''', '''            const params = fxMigrateLegacy(rec.params || {});
            this._controls.forEach((c, id) => {
                if (PRESET_SKIP.has(id)) return;
                const k = id.replace("param", "");''')
sub1('''            this.updateSlots();
            this.drawFlt();
            for (let e = 0; e < WT_ENG.length; e++) this.drawWt(e);
        } finally { this._applying = false; }''', '''            this.updateSlots();
            this.drawFlt();
            for (let sl = 0; sl < 10; sl++) this.updateFxRow(sl);
            this.fxApplyOrder();
            for (let e = 0; e < WT_ENG.length; e++) this.drawWt(e);
        } finally { this._applying = false; }''')

path.write_text(s, encoding="utf-8")
print("ok")
