#!/usr/bin/env python3
"""Rewrites patch/index.js for the 6-slot oscillator architecture (run once on the pre-slot UI)."""
import re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = sys.argv[1] if len(sys.argv) > 1 else "patch/index.js"
s = open(P).read()
consts = open(os.path.join(HERE, "ui_consts.js")).read()
methods = open(os.path.join(HERE, "ui_methods.js")).read()

def cut(a, b, repl="", incl_b=False):
    """replace the text from anchor a up to (not including) anchor b"""
    global s
    i = s.index(a); assert s.count(a) == 1, a
    j = s.index(b, i + len(a))
    s = s[:i] + repl + s[(j + len(b)) if incl_b else j:]

def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)

def method(name):
    """delete one class method (4 space indent) incl. a directly preceding // comment line"""
    global s
    m = re.search(r"\n((?:    //[^\n]*\n)*)    (?:async )?" + re.escape(name) + r" \([^\n]*\{\n", s)
    assert m, name
    i = m.start() + 1
    j = s.index("\n    }\n", m.end()) + len("\n    }\n")
    # swallow one following blank line
    if s[j] == "\n": j += 1
    s = s[:i] + s[j:]

# ---- constants -------------------------------------------------------------------------------------------------
cut("// SSL 4000 style channel EQ", "// ---------- filter response model", "")
cut("const MOD_DST = [", "// option groups of the dropdowns", consts + "\n")
s = re.sub(r"const MOD_DST_GROUPS = \[\[0, \"\"\], \[1, \"Global\"\], \[11, [^\n]*\n", "", s)
cut("// ---------------------------------------------------------------------------------------------------------------\n// Modulation targets", "const MOD_SRC_SHORT", "")
cut("// filter page parameters read by the visualizers", "const BASE_W", "")
rep("const WT_PAN_IDS = [445, 454, 463];\n", "")
s = re.sub(r"const WT_PHASE_IDS = \[[^\]]*\];\n", "", s)

# ---- SPECS -------------------------------------------------------------------------------------------------------
KEEP = {2, 3, 18, 19, 20, 21, 22, 28, 29, 36, 45, 46, 63, 175, 189, 190}
i = s.index("const SPECS = (() => {\n    const L = [\n")
j = s.index("    ];\n", i)
blk = s[i:j]
out = []
for ln in blk.split("\n"):
    m = re.match(r"\s+\[(\d+),", ln)
    if m and int(m.group(1)) not in KEEP: continue
    out.append(ln)
blk = "\n".join(out).rstrip().rstrip(",")
s = s[:i] + blk + "\n" + s[j:]
cut("    // mixer page: SSL 4000 style EQ", "    // LFO beat sync", "")
cut("    // filter 1 mix, filter 2 and routing", "    // fx algorithm of the synth Drive", "")
cut("    // Serum style wavetable controls per engine", "    // FX rack: 10 slots", "")
cut("    // which rack each mixer channel feeds", "    L.push([880,", "")
rep('    L.push([523, "Main LFO Sync", 0, 1, 0, "", "btn", ["Free", "Sync"], 1, "LFO Sync"]);\n', "")
rep('    L.push([524, "Main LFO Division", 0, 17, 8, "", "sel", SYNC_DIVS, 1, "Division"]);\n', "")
rep('"Slot " + (i + 1) + " Dest",   0, 45, 0', '"Slot " + (i + 1) + " Dest",   0, MOD_DST.length - 1, 0')
rep("    // short control names for the output card", "    OSC_SPEC_ROWS.forEach(r => L.push(r));\n    // short control names for the output card")
# the literal list ends with the last kept row: make sure a trailing comma does not matter, and rows follow
# ---- cards / constants -------------------------------------------------------------------------------------------
cut("// Sound page (samplers, wavetables, memory", "// FX page", "")
cut("const NOTE_NAMES", "const FRAME_SIZES", "const NOTE_NAMES = [\"C\", \"C#\", \"D\", \"D#\", \"E\", \"F\", \"F#\", \"G\", \"G#\", \"A\", \"A#\", \"B\"];\nconst CHUNK = 256;\n")
rep('const S2_DZ_EMPTY = "DROP AUDIO / CLICK TO LOAD";\n', "")
rep('const SMP_DZ_EMPTY = "DROP AUDIO / CLICK TO LOAD";', 'const SMP_DZ_EMPTY = "DROP A SAMPLE / CLICK TO LOAD";')
rep('const WT_DZ_EMPTY = "DROP WAVETABLE / CLICK TO LOAD";', 'const WT_DZ_EMPTY = "DROP A WAVETABLE / CLICK TO LOAD";')
cut("const STORE_PREFIX", "function fmt (s, v)", "")
# ---- fmt ---------------------------------------------------------------------------------------------------------
cut("    if (s.num >= 871 && s.num <= 879)", "    if (s.labels.length)", """    if (s.num === 880 || s.num === 881) return Math.round(v * 100) + "%";
    if (s.num === 522) return v < 1 ? "HOST" : Math.round(v) + " BPM";
    if (s.num >= FM_BASE && s.num < FM_BASE + 36) { const p = Math.round(v * 100); return (p > 0 ? "+" : "") + p + "%"; }
    if (s.num >= OSC_BASE && s.num < OSC_BASE + OSC_STRIDE * OSC_N) {
        const k = (s.num - OSC_BASE) % OSC_STRIDE;
        if (k === OSC_K.pan) { const p = Math.round(v * 50); return p === 0 ? "C" : (p < 0 ? "L" + (-p) : "R" + p); }
        if (k === OSC_K.phase) return Math.round(v * 360) + "\\u00b0";
        if (k === OSC_K.root) { const n = Math.round(v); return NOTE_NAMES[n % 12] + (Math.floor(n / 12) - 1); }
        if (k === OSC_K.uvox) { const n = Math.round(v); return n + (n === 1 ? " voice" : " voices"); }
        if (k === OSC_K.udet) return "\\u00b1" + Math.round(v * 50) + " ct";
        if (k === OSC_K.semi) return (v > 0 ? "+" : "") + Math.round(v) + " st";
    }
""")
# ---- class: constructor / lifecycle ----------------------------------------------------------------------------------
cut("        this._smpState = new Array(MEM_COUNT).fill(null);\n", "        this._lfoPts", "        this._page = \"o0\";\n        this._mem = { wt: new Array(OSC_N).fill(null), sm: new Array(OSC_N).fill(null) };\n        this._memTimer = { wt: new Array(OSC_N).fill(null), sm: new Array(OSC_N).fill(null) };\n        this._memStart = [];\n        this._oscReady = false;\n")
cut("        this._store = new Map();\n        this._incoming", "        this.innerHTML = this.getHTML();", "")
# connectedCallback
cut("        this.buildSmpLoader();\n", "        this.updateSlots();\n        this.buildModStrip();", "        this.buildOscPages();\n")
cut("            for (let e = 0; e < WT_ENG.length; e++) {\n                if (this._wt[e].restoring", "            const c = this._controls.get(id);", "")
cut("        // sample manager: DSP -> UI autosave stream", "        window.__amorphProcessMidi", "")
cut("            this.loadStore();\n", "        });\n    }\n\n    // Reads the instance's stored state once", "            this.loadMemStore();\n            for (let o = 0; o < OSC_N; o++) this.updateOscUi(o);\n            this.startMemRestore();\n")
# disconnectedCallback
cut('        if (this._saveHandler) {', "        if (this._animFrame)", "")
cut("        if (this._restoreTimer) clearInterval(this._restoreTimer);\n", "        delete window.__amorphProcessMidi;", "        for (const kind of [\"wt\", \"sm\"]) this._memTimer[kind].forEach(t => { if (t) clearInterval(t); });\n        this._memStart.forEach(t => clearTimeout(t));\n")
# ---- method regions ----------------------------------------------------------------------------------------------
cut("    // ---------- sample memory (autosave to browser storage) ----------", "    // ---------- tabs ----------", "")
cut("    // ---------- tabs ----------", "    // highlight matrix rows", """    // ---------- tabs ----------
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

""")
cut("    // ---------- dedicated sample osc loader (sampleBankV2Load) ----------", "    // ---------- filter visualizers ----------", "")
for n in ("fltVal", "fltCurve", "drawFlt"): method(n)
cut("    drawWt (e) {", "    // ---------- parameter hooks ----------", methods + "\n")
rep("    fltFrame (cv) {\n", "    // ---------- filter visualizers ----------\n    fltVal (id) { const c = this._controls.get(\"param\" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; }\n\n    fltFrame (cv) {\n")
for n in ("faderHTML", "eqHTML", "channelHTML", "wtPageHTML"): method(n)
# ---- onValue -----------------------------------------------------------------------------------------------------
rep("        if (FLT_VIS_IDS.indexOf(n) >= 0) this.drawFlt();\n        if (n === 154) this.updateSmpName();\n        if (n === 193) this.updateS2Ui();\n", "        if (n >= OSC_BASE && n < OSC_BASE + OSC_STRIDE * OSC_N) this.onOscValue(Math.floor((n - OSC_BASE) / OSC_STRIDE), (n - OSC_BASE) % OSC_STRIDE);\n")
cut("        for (let e = 0; e < WT_ENG.length; e++) {\n            const cfg = WT_ENG[e];\n            if (n === cfg.mem)", "        if (user && this.presetDirty)", "")
# ---- getHTML -----------------------------------------------------------------------------------------------------
cut("        const cells = Array.from({ length: MEM_COUNT }", "        const fxPage = this.fxPageHTML();", "        const oscPages = Array.from({ length: OSC_N }, (_, o) => `<div class=\"page p-o${o}\" data-src=\"0\">${this.oscPageHTML(o)}</div>`).join(\"\\n    \");\n")
rep('<div class="tabs"><button type="button" class="tab on" data-group="osc">OSC</button><button type="button" class="tab" data-group="flt">FILTER</button><button type="button" class="tab" data-group="fx">FX</button><button type="button" class="tab" data-group="mix">MIXER</button></div>',
    '<div class="tabs"><button type="button" class="tab on" data-group="osc">OSC</button><button type="button" class="tab" data-group="fm">FM</button><button type="button" class="tab" data-group="fx">FX</button><button type="button" class="tab" data-group="glob">GLOBAL</button></div>')
m = re.search(r'  <div class="subtabs">.*?</div>\n', s)
s = s[:m.start()] + '  <div class="subtabs">' + "".join('<button type="button" class="stab%s" data-page="o%d">OSC %d</button>' % (" on" if o == 0 else "", o, o + 1) for o in range(6)) + '</div>\n' + s[m.end():]
cut('    <div class="page p-synth">${synth}</div>', "    <div class=\"page p-fx\">", "    ${oscPages}\n    <div class=\"page p-fm\">${this.fmPageHTML()}</div>\n    <div class=\"page p-glob\">${this.globalPageHTML()}</div>\n")
rep('<span class="lcd-mode">SYNTH</span>', '<span class="lcd-mode">OSC</span>')
# ---- presets / vault ---------------------------------------------------------------------------------------------
rep('const PRESET_SKIP = new Set(["param146", "param147", "param154", "param193"].concat(WT_ENG.map(c => "param" + c.mem)));', 'const PRESET_SKIP = new Set();')
cut("const SLOT_DEFS = [", "const KIND_FOLDER", "const SLOT_DEFS = [].concat(\n    Array.from({ length: OSC_N }, (_, o) => ({ key: \"wt\" + o, label: \"OSC \" + (o + 1) + \" WAVETABLE\", short: \"OSC\" + (o + 1) + \" WT\", kind: \"wavetable\" })),\n    Array.from({ length: OSC_N }, (_, o) => ({ key: \"sm\" + o, label: \"OSC \" + (o + 1) + \" SAMPLER\", short: \"OSC\" + (o + 1) + \" SMP\", kind: \"sample\" }))\n);\n")
rep('this._slotLib = { smp: null, s2: null, wt0: null, wt1: null, wt2: null };', 'this._slotLib = Object.fromEntries(SLOT_DEFS.map(d => [d.key, null]));')
s = s.replace('s.label.replace("SAMPLER ", "S").replace("WAVETABLE ", "WT")', "s.short")
s = s.replace('s.label.replace("SAMPLER ", "SMP ").replace("WAVETABLE ", "WT ")', "s.short")
cut('        if (slot === "smp") await this.loadSynthSample(file, id);', "        const def = SLOT_DEFS.find(s => s.key === slot);\n        this.libStatus(\"LOADED", '        if (/^(wt|sm)\\d$/.test(slot)) await this.loadMem(slot.slice(0, 2), parseInt(slot.slice(2), 10), file, id);\n')
rep("            this.drawFlt();\n", "            this.drawAllOsc();\n            for (let o = 0; o < OSC_N; o++) this.updateOscUi(o);\n")
rep("            for (let e = 0; e < WT_ENG.length; e++) this.drawWt(e);\n", "")

# the rack rows never change once built: look them up once (the view creates ~900 controls on start)
rep("    fxRow (g) { return this.querySelector('.fxrow[data-g=\"' + g + '\"]'); }", "    fxRow (g) { const c = this._fxRowCache || (this._fxRowCache = []); return c[g] || (c[g] = this.querySelector('.fxrow[data-g=\"' + g + '\"]')); }")

# ---- CSS: drop the rules of the removed pages, add the slot page styles --------------------------------------------------
L = s.split("\n")
a = next(i for i, l in enumerate(L) if l.strip() == "/* sound page */")
b = next(i for i, l in enumerate(L) if l.strip() == "/* mod page */")
keep = [l for l in L[a:b] if ".mgr-status" in l]
pat = re.compile(r"^\s*\.(chs|ch|chname|solo-sp|chrt|fdr|eq|eqin|eqb|eqrow|eqk|p-mix|n154)\b")
s = "\n".join(L[:a] + keep + [l for l in L[b:] if not pat.match(l)])
s = re.sub(r'  eisenpuls-view\[data-page="sound"\] \.p-synth \{ display: grid; \}\n(?:  eisenpuls-view\[data-page="[a-z0-9]+"\] \.p-[a-z0-9]+ \{ display: grid; \}\n)*',
    "".join('  eisenpuls-view[data-page="o%d"] .p-o%d { display: grid; }\n' % (o, o) for o in range(6)) + '  eisenpuls-view[data-page="fm"] .p-fm { display: grid; }\n  eisenpuls-view[data-page="glob"] .p-glob { display: grid; }\n  eisenpuls-view[data-page="fx"] .p-fx { display: grid; }\n', s)
s = s.replace("</style>", open(os.path.join(HERE, "ui_style.css")).read() + "</style>", 1)
s = s.replace("var MIX_ROUTE_NAMES = [\"Osc\", \"Sub\", \"Noise\", \"Supersaw\", \"Sampler 1\", \"Sampler 2\", \"WT 1\", \"WT 2\", \"WT 3\"];\n", "")
open(P, "w").write(s)
print("patched", len(s.splitlines()), "lines")
