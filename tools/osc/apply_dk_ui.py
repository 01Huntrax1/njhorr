#!/usr/bin/env python3
"""Adds the Modal Drum source (Source type 10) to patch/index.js: source name, spec rows 2600.., mod destinations 1020..1115, fallback UI section and display.
One-shot; refuses to run twice."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "DK_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
OLD = '["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick", "Waveguide", "JP-8080", "Granular", "Additive"]'
n = s.count(OLD); assert n == 7, n
s = s.replace(OLD, json.dumps(L.SRC_TYPES))
s, k = re.subn(r'(\[\d+, "OSC \d Source", 0, )9(, 0, "", "sel")', r'\g<1>10\2', s); assert k == 6, k
rep('Math.max(0, Math.min(9, Math.round(this.oscVal(o, "type"))))', 'Math.max(0, Math.min(10, Math.round(this.oscVal(o, "type"))))')
rep("const AD_SHAPES = ", "const DK_BASE = %d, DK_STRIDE = %d;\nconst DK_K = %s;\nconst dkId = (o, key) => DK_BASE + DK_STRIDE * o + DK_K[key];\nconst AD_SHAPES = " % (L.DK_BASE, L.DK_STRIDE, json.dumps({p[1]: p[0] for p in L.DK})))
rows = []
for o in range(L.OSC_COUNT):
    for p in L.DK:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.dk_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), "null", json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j].rstrip().rstrip(",") + ",\n" + ",\n".join(rows) + s[j:]
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.DK_DST_BASE, len(d)
for o in range(L.OSC_COUNT):
    for p in L.DK: d.append("OSC %d %s" % (o + 1, p[2]))
assert len(d) == L.N_DST_TOTAL
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.dkdst(o, 0), "OSC %d Modal Drum" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.DK:
        if p[8] == "sld": t[str(L.dk_id(o, p[0]))] = [L.dkdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
rep("        const gx = key => this.controlHTML(grId(o, key), true);\n", "        const gx = key => this.controlHTML(grId(o, key), true);\n        const dx = key => this.controlHTML(dkId(o, key), true);\n")
rep('            ${sh("9", [', '            ${sh("10", [' + ", ".join('"%s"' % p[1] for p in L.DK) + '].map(dx).join(""), "cgrid o-g3 o-pl")}\n            ${sh("9", [')
DISPLAY = '''        } else if (type === 10) {
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
        } else if (type === 9) {'''
rep("        } else if (type === 9) {", DISPLAY)
open(P, "w").write(s)
print("ok")
