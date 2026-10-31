#!/usr/bin/env python3
"""Replaces the Plaits source of patch/index.js by the Wave Terrain source (specs, mod destinations, fallback UI, display).  Run once on the Plaits version."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "TER_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
# source names / OSC_K keys
s = s.replace('["Wavetable", "Sampler", "Plaits", "Physical", "Alpha Juno", "Kick"]', json.dumps(L.SRC_TYPES))
for a, b in (("pleng", "tterr"), ("pharm", "tscale"), ("ptimb", "twarp"), ("pmorph", "tfold")):
    s = s.replace('"%s": %d' % (a, {"pleng": 24, "pharm": 25, "ptimb": 26, "pmorph": 27}[a]), '"%s": %d' % (b, {"pleng": 24, "pharm": 25, "ptimb": 26, "pmorph": 27}[a]))
# constants
i = s.index("const PLX_BASE"); j = s.index("\n", s.index("const plxId")) + 1
s = s[:i] + 'const TER_BASE = %d, TER_STRIDE = %d;\nconst TER_K = %s;\nconst terId = (o, key) => TER_BASE + TER_STRIDE * o + TER_K[key];\n' % (L.TER_BASE, L.TER_STRIDE, json.dumps({p[1]: p[0] for p in L.TER})) + s[j:]
s = s.replace('const OSC_SRC_TYPES = ["Wavetable", "Sampler", "Plaits", "Physical", "Alpha Juno", "Kick"];', 'const OSC_SRC_TYPES = %s;' % json.dumps(L.SRC_TYPES))
i = s.index("const PLAITS_ENGINES"); j = s.index("\n", s.index("const PLAITS_PARAMS")) + 1
s = s[:i] + "const TERRAINS = %s;\n" % json.dumps(L.TERRAINS) + s[j:]
# spec rows 24..27 of every slot
for o in range(L.OSC_COUNT):
    b = L.BASE + 64 * o
    rows = ['    [%d, "OSC %d Terrain A", 0, 11, 0, "", "sel", TERRAINS, 1, "Terrain", null],' % (b + 24, o + 1),
            '    [%d, "OSC %d Terrain Scale", 0, 1, 0.5, "", "sld", null, 1, "Scale", null],' % (b + 25, o + 1),
            '    [%d, "OSC %d Terrain Warp", 0, 1, 0, "", "sld", null, 1, "Warp", null],' % (b + 26, o + 1),
            '    [%d, "OSC %d Terrain Fold", 0, 1, 0, "", "sld", null, 1, "Fold", null],' % (b + 27, o + 1)]
    pat = re.compile(r'    \[%d, "OSC %d Plaits Engine".*?\n    \[%d, "OSC %d Plaits Morph"[^\n]*\n' % (b + 24, o + 1, b + 27, o + 1), re.S)
    assert pat.search(s), o
    s = pat.sub("\n".join(rows) + "\n", s, 1)
# extras rows 2100..2195
s = re.sub(r'    \[21\d\d, "OSC \d Plaits [^\n]*\n', "", s)
rows = []
for o in range(L.OSC_COUNT):
    for p in L.TER:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.ter_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), "TERRAINS" if labels else "null", json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j].rstrip().rstrip(",") + ",\n" + ",\n".join(rows) + s[j:]
# mod destinations
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.TER_DST_BASE + 96, len(d)
d = d[:L.TER_DST_BASE]
for o in range(L.OSC_COUNT):
    for p in L.TER: d.append("OSC %d %s" % (o + 1, p[2]))
d = [x.replace("Position / Harm", "Position / Terrain Scale").replace("Warp 1 / Timbre", "Warp 1 / Terrain Warp").replace("Warp 2 / Morph", "Warp 2 / Terrain Fold") for x in d]
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1)); g = [x for x in g if "Plaits" not in x[1]]
for o in range(L.OSC_COUNT): g.append([L.terdst(o, 0), "OSC %d Wave Terrain" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for k in [k for k in t if 2100 <= int(k) < 2200]: del t[k]
for o in range(L.OSC_COUNT):
    for p in L.TER:
        if p[8] == "sld": t[str(L.ter_id(o, p[0]))] = [L.terdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
# UI logic
rep('''        const eng = Math.max(0, Math.min(PLAITS_ENGINES.length - 1, Math.round(this.oscVal(o, "pleng"))));
        ["pharm", "ptimb", "pmorph"].forEach((key, i) => {
            const lbl = this.querySelector(".n" + oscId(o, key) + " .lbl");
            if (lbl) lbl.textContent = PLAITS_PARAMS[eng][i];
        });
''', '')
rep("if (k === OSC_K.type || k === OSC_K.pleng) { this.updateOscUi(o); return; }", "if (k === OSC_K.type) { this.updateOscUi(o); return; }")
i = s.index('            const eng = Math.max(0, Math.min(PLAITS_ENGINES.length - 1, Math.round(this.oscVal(o, "pleng"))));\n            ctx.fillStyle')
j = s.index("            if (info) info.textContent = PLAITS_ENGINES[eng]", i); j = s.index("\n", j) + 1
DISPLAY = r'''            // Wave Terrain: one cycle of the output along the orbit (the terrain formulas of the DSP)
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
'''
s = s[:i] + DISPLAY + s[j:]
rep("        const px = key => this.controlHTML(plxId(o, key), true);\n", "        const px = key => this.controlHTML(terId(o, key), true);\n")
i = s.index('            ${sh("2", ["pleng"'); j = s.index("\n            ${sh(\"4\"", i)
s = s[:i] + '''            ${sh("2", ["tterr", "tscale", "twarp", "tfold"].map(c).join("") + `<div class="o-uh">Orbit</div>` + ["tcx", "tcy", "trx", "try", "trot", "tratio", "tphase", "tshape"].map(px).join("")
                + `<div class="o-uh">Movement / second terrain</div>` + ["tmrate", "tmdep", "tterr2", "tmorph"].map(px).join("") + `<div class="o-uh">Output</div>` + ["tsmooth", "tdrive", "tbits", "tvel"].map(px).join(""), "cgrid o-g3 o-pl")}''' + s[j:]
open(P, "w").write(s)
print("ok")
