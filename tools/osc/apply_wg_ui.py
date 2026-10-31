#!/usr/bin/env python3
"""Adds the Waveguide source (Source type 6) to patch/index.js: source names, spec rows 2200.., mod destinations 636..731, fallback UI section and display.
The native UI takes its tables from this file (tools/nativeui/gen_data.js).  One-shot; refuses to run twice."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "WG_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
OLD = '["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick"]'
n = s.count(OLD); assert n == 7, n
s = s.replace(OLD, json.dumps(L.SRC_TYPES))
s, k = re.subn(r'(\[\d+, "OSC \d Source", 0, )5(, 0, "", "sel")', r'\g<1>6\2', s); assert k == 6, k
rep('Math.max(0, Math.min(5, Math.round(this.oscVal(o, "type"))))', 'Math.max(0, Math.min(6, Math.round(this.oscVal(o, "type"))))')
# constants
rep("const terId = (o, key) => TER_BASE + TER_STRIDE * o + TER_K[key];\n",
    "const terId = (o, key) => TER_BASE + TER_STRIDE * o + TER_K[key];\nconst WG_BASE = %d, WG_STRIDE = %d;\nconst WG_K = %s;\nconst wgId = (o, key) => WG_BASE + WG_STRIDE * o + WG_K[key];\nconst WG_MODELS = %s;\nconst WG_LABELS = %s;\n"
    % (L.WG_BASE, L.WG_STRIDE, json.dumps({p[1]: p[0] for p in L.WG}), json.dumps(L.WG_MODELS), json.dumps(L.WG_LABELS)))
# spec rows
rows = []
for o in range(L.OSC_COUNT):
    for p in L.WG:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.wg_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), "WG_MODELS" if labels else "null", json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j].rstrip().rstrip(",") + ",\n" + ",\n".join(rows) + s[j:]
# mod destinations
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.WG_DST_BASE, len(d)
for o in range(L.OSC_COUNT):
    for p in L.WG: d.append("OSC %d %s" % (o + 1, p[2]))
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.wgdst(o, 0), "OSC %d Waveguide" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.WG:
        if p[8] == "sld": t[str(L.wg_id(o, p[0]))] = [L.wgdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
# fallback UI: the model's own labels replace the generic ones
rep("        const px = key => this.controlHTML(terId(o, key), true);\n", "        const px = key => this.controlHTML(terId(o, key), true);\n        const wx = key => this.controlHTML(wgId(o, key), true);\n")
rep('            ${sh("5", `<div class="o-uh">Body</div>`',
    '            ${sh("6", `<div class="o-uh">Model</div>` + ["wmodel", "wdecay", "wtone", "wexc", "wpos", "wnoise", "wnl", "wstretch", "watk"].map(wx).join("") + `<div class="o-uh">Drum / body / output</div>` + ["wsnare", "wbody", "wbodyf", "wvel", "wdrive", "wglide", "wktrack"].map(wx).join(""), "cgrid o-g3 o-pl")}\n            ${sh("5", `<div class="o-uh">Body</div>`')
rep("        } else if (type === 5) {\n            // the body of the kick",
    '''        } else if (type === 6) {
            // Waveguide: envelope of the sound (decay time of the model) with the model's name
            const V = key => { const id = wgId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const mdl = Math.max(0, Math.min(4, Math.round(V("wmodel")))), t60 = 0.05 * Math.pow(400, V("wdecay")), arr = new Array(W);
            const sust = mdl === 1 || mdl === 2, T = Math.min(2.5, Math.max(0.3, t60 * 1.2));
            for (let x = 0; x < W; x++) { const t = x / W * T; arr[x] = (sust ? (1 - Math.exp(-t / (0.005 * Math.pow(200, V("watk"))))) : Math.exp(-t * 6.9 / t60)) * Math.sin(2 * Math.PI * 110 * t * (1 + (mdl === 4 ? V("wglide") * 0.5 * Math.exp(-t * 6.9 / t60) : 0))) * 0.8; }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = "WAVEGUIDE / " + WG_MODELS[mdl].toUpperCase() + " / T60 " + t60.toFixed(2) + " S";
        } else if (type === 5) {
            // the body of the kick''')
rep("if (k === OSC_K.type) { this.updateOscUi(o); return; }", "if (k === OSC_K.type || k === WG_K.wmodel + 100000) { this.updateOscUi(o); return; }") if False else None
open(P, "w").write(s)
print("ok")
