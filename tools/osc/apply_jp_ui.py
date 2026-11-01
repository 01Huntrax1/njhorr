#!/usr/bin/env python3
"""Adds the JP-8080 source (Source type 7) to patch/index.js: source names, spec rows 2300.., mod destinations 732..827, fallback UI section and display.
The native UI takes its tables from this file (tools/nativeui/gen_data.js).  One-shot; refuses to run twice."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "JP_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
OLD = '["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide"]'
n = s.count(OLD); assert n == 7, n
s = s.replace(OLD, json.dumps(L.SRC_TYPES))
s, k = re.subn(r'(\[\d+, "OSC \d Source", 0, )6(, 0, "", "sel")', r'\g<1>7\2', s); assert k == 6, k
rep('Math.max(0, Math.min(6, Math.round(this.oscVal(o, "type"))))', 'Math.max(0, Math.min(7, Math.round(this.oscVal(o, "type"))))')
rep("const wgId = (o, key) => WG_BASE + WG_STRIDE * o + WG_K[key];\n",
    "const wgId = (o, key) => WG_BASE + WG_STRIDE * o + WG_K[key];\nconst JP_BASE = %d, JP_STRIDE = %d;\nconst JP_K = %s;\nconst jpId = (o, key) => JP_BASE + JP_STRIDE * o + JP_K[key];\nconst JP_WAVES = %s;\nconst JP_LABELS = %s;\n"
    % (L.JP_BASE, L.JP_STRIDE, json.dumps({p[1]: p[0] for p in L.JP}), json.dumps(L.JP_WAVES), json.dumps(L.JP_LABELS)))
rows = []
for o in range(L.OSC_COUNT):
    for p in L.JP:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.jp_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), "JP_WAVES" if labels else "null", json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j].rstrip().rstrip(",") + ",\n" + ",\n".join(rows) + s[j:]
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.JP_DST_BASE, len(d)
for o in range(L.OSC_COUNT):
    for p in L.JP: d.append("OSC %d %s" % (o + 1, p[2]))
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.jpdst(o, 0), "OSC %d JP-8080" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.JP:
        if p[8] == "sld": t[str(L.jp_id(o, p[0]))] = [L.jpdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
rep("        const wx = key => this.controlHTML(wgId(o, key), true);\n", "        const wx = key => this.controlHTML(wgId(o, key), true);\n        const jx = key => this.controlHTML(jpId(o, key), true);\n")
rep('            ${sh("6", `<div class="o-uh">Model</div>`',
    '            ${sh("7", `<div class="o-uh">Waveform</div>` + ["jpwave", "jppw", "jppwm", "jppwr", "jpdet", "jpmix", "jpwid", "jpfb", "jpfbc", "jptmd", "jptmr", "jpstilt", "jpspk"].map(jx).join("") + `<div class="o-uh">Common</div>` + ["jpnz", "jpsub", "jpdrv"].map(jx).join(""), "cgrid o-g3 o-pl")}\n            ${sh("6", `<div class="o-uh">Model</div>`')
rep("        } else if (type === 6) {\n            // Waveguide",
    '''        } else if (type === 7) {
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
            // Waveguide''')
open(P, "w").write(s)
print("ok")
