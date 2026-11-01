#!/usr/bin/env python3
"""Adds the Granular (type 8) and Additive (type 9) sources to patch/index.js: source names, spec rows 2400.. / 2500.., mod destinations 828..1019, fallback UI sections and displays.
The native UI takes its tables from this file (tools/nativeui/gen_data.js).  One-shot; refuses to run twice."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "GR_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
OLD = '["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080"]'
n = s.count(OLD); assert n == 7, n
s = s.replace(OLD, json.dumps(L.SRC_TYPES))
s, k = re.subn(r'(\[\d+, "OSC \d Source", 0, )7(, 0, "", "sel")', r'\g<1>9\2', s); assert k == 6, k
rep('Math.max(0, Math.min(7, Math.round(this.oscVal(o, "type"))))', 'Math.max(0, Math.min(9, Math.round(this.oscVal(o, "type"))))')
rep("const jpId = (o, key) => JP_BASE + JP_STRIDE * o + JP_K[key];\n",
    "const jpId = (o, key) => JP_BASE + JP_STRIDE * o + JP_K[key];\nconst GR_BASE = %d, GR_STRIDE = %d;\nconst GR_K = %s;\nconst grId = (o, key) => GR_BASE + GR_STRIDE * o + GR_K[key];\nconst AD_BASE = %d, AD_STRIDE = %d;\nconst AD_K = %s;\nconst adId = (o, key) => AD_BASE + AD_STRIDE * o + AD_K[key];\nconst AD_SHAPES = %s;\n"
    % (L.GR_BASE, L.GR_STRIDE, json.dumps({p[1]: p[0] for p in L.GR}), L.AD_BASE, L.AD_STRIDE, json.dumps({p[1]: p[0] for p in L.AD}), json.dumps(L.AD_SHAPES)))
rows = []
for K, idf, tab in ((L.GR, L.gr_id, None), (L.AD, L.ad_id, "AD_SHAPES")):
    for o in range(L.OSC_COUNT):
        for p in K:
            j, key, label, short, lo, hi, init, unit, kind, labels = p
            rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (idf(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), tab if labels else "null", json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j].rstrip().rstrip(",") + ",\n" + ",\n".join(rows) + s[j:]
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.GR_DST_BASE, len(d)
for K in (L.GR, L.AD):
    for o in range(L.OSC_COUNT):
        for p in K: d.append("OSC %d %s" % (o + 1, p[2]))
        for _ in range(16 - len(K)): d.append("OSC %d (unused %d)" % (o + 1, len(d)))
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
assert len(d) == L.N_DST_TOTAL, len(d)
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.grdst(o, 0), "OSC %d Granular" % (o + 1)])
for o in range(L.OSC_COUNT): g.append([L.addst(o, 0), "OSC %d Additive" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.GR:
        if p[8] == "sld": t[str(L.gr_id(o, p[0]))] = [L.grdst(o, p[0]), 0.5]
    for p in L.AD:
        if p[8] == "sld": t[str(L.ad_id(o, p[0]))] = [L.addst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
# Granular uses the sample memory of its slot (like the Sampler)
rep('srcKind (o) { return Math.round(this.oscVal(o, "type")) === 1 ? "sm" : "wt"; }', 'srcKind (o) { const t = Math.round(this.oscVal(o, "type")); return t === 1 || t === 8 ? "sm" : "wt"; }')
rep('const kind = type === 1 ? "sm" : "wt";', 'const kind = type === 1 || type === 8 ? "sm" : "wt";')
rep('data-show="0,1"><div class="dz dz-osc"', 'data-show="0,1,8"><div class="dz dz-osc"')
rep('${sh("1", ["root", "sstart", "sloop"].map(c).join(""), "cgrid o-g3")}', '${sh("1", ["root", "sstart", "sloop"].map(c).join(""), "cgrid o-g3")}\n            ${sh("8", ["root"].map(c).join("") + ["gpos", "gsize", "gdens", "gspray", "gpitch", "gpan", "gshape", "grev", "gscan", "gjit", "gvel", "gdrive"].map(gx).join(""), "cgrid o-g3 o-pl")}\n            ${sh("9", ["ashape", "ashapeb", "amorph", "acount", "atilt", "aodd", "ainh", "aform", "aformg", "ashim", "ashimr", "adec", "awid", "avel", "adrive"].map(ax).join(""), "cgrid o-g3 o-pl")}')
rep("        const jx = key => this.controlHTML(jpId(o, key), true);\n", "        const jx = key => this.controlHTML(jpId(o, key), true);\n        const gx = key => this.controlHTML(grId(o, key), true);\n        const ax = key => this.controlHTML(adId(o, key), true);\n")
DISPLAY = '''        } else if (type === 9) {
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
        } else if (type === 7) {'''
rep("        } else if (type === 7) {", DISPLAY)
# Granular shows the loaded sample with the grain position
rep("        } else if (type === 1) {\n            const s = this._mem.sm[o];", "        } else if (type === 1 || type === 8) {\n            const s = this._mem.sm[o];")
rep('const start = Math.max(0, Math.min(1, this.oscVal(o, "sstart")));', 'const start = Math.max(0, Math.min(1, type === 8 ? (() => { const c = this._controls.get("param" + grId(o, "gpos")); return c ? c.value : SPEC_BY_NUM.get(grId(o, "gpos")).init; })() : this.oscVal(o, "sstart")));')
open(P, "w").write(s)
print("ok")
