#!/usr/bin/env python3
"""Adds the Spectral source (Source type 11) to patch/index.js: source name, spec rows 2700.., mod destinations 1116..1211, fallback UI section and display.
One-shot; refuses to run twice."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "SP_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
OLD = json.dumps(L.SRC_TYPES[:-1])
n = s.count(OLD); assert n == 7, n
s = s.replace(OLD, json.dumps(L.SRC_TYPES))
s, k = re.subn(r'(\[\d+, "OSC \d Source", 0, )10(, 0, "", "sel")', r'\g<1>11\2', s); assert k == 6, k
rep('Math.max(0, Math.min(10, Math.round(this.oscVal(o, "type"))))', 'Math.max(0, Math.min(11, Math.round(this.oscVal(o, "type"))))')
rep("const DK_BASE = ", "const SP_BASE = %d, SP_STRIDE = %d;\nconst SP_K = %s;\nconst spId = (o, key) => SP_BASE + SP_STRIDE * o + SP_K[key];\nconst DK_BASE = " % (L.SP_BASE, L.SP_STRIDE, json.dumps({p[1]: p[0] for p in L.SP})))
rows = []
for o in range(L.OSC_COUNT):
    for p in L.SP:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.sp_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j].rstrip().rstrip(",") + ",\n" + ",\n".join(rows) + s[j:]
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.SP_DST_BASE, len(d)
for o in range(L.OSC_COUNT):
    for p in L.SP: d.append("OSC %d %s" % (o + 1, p[2]))
assert len(d) == L.N_DST_TOTAL
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.spdst(o, 0), "OSC %d Spectral" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.SP:
        if p[8] == "sld": t[str(L.sp_id(o, p[0]))] = [L.spdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
rep("        const dx = key => this.controlHTML(dkId(o, key), true);\n", "        const dx = key => this.controlHTML(dkId(o, key), true);\n        const sx = key => this.controlHTML(spId(o, key), true);\n")
rep('            ${sh("10", [', '            ${sh("11", [' + ", ".join('"%s"' % p[1] for p in L.SP) + '].map(sx).join(""), "cgrid o-g3 o-pl")}\n            ${sh("10", [')
# the sample memory is used by Resynth as well
rep('data-show="0,1,8"', 'data-show="0,1,8,11"')
rep('srcKind (o) { const t = Math.round(this.oscVal(o, "type")); return t === 1 || t === 8 ? "sm" : "wt"; }', 'srcKind (o) { const t = Math.round(this.oscVal(o, "type")); return t === 1 || t === 8 || t === 11 ? "sm" : "wt"; }')
rep('const kind = type === 1 || type === 8 ? "sm" : "wt";', 'const kind = type === 1 || type === 8 || type === 11 ? "sm" : "wt";')
DISPLAY = '''        } else if (type === 11) {
            // Spectral: the envelope the partials follow (two formant peaks in Spectrum mode; Resynth shows the loaded sample on the memory card)
            const V = key => { const id = spId(o, key), c = this._controls.get("param" + id); return c ? c.value : SPEC_BY_NUM.get(id).init; };
            const arr = new Array(W), sg = 0.12 + V("sblur") * 0.9, c1 = 100 * Math.pow(2, V("spos") * 6.6), c2 = 100 * Math.pow(2, V("spos2") * 6.6), m = V("smorph");
            for (let x = 0; x < W; x++) {
                const l = Math.log2(40 * Math.pow(2, x / W * 9)), d1 = (l - Math.log2(c1)) / sg, d2 = (l - Math.log2(c2)) / sg;
                arr[x] = Math.min(1, (1 - m) * Math.exp(-0.5 * d1 * d1) + m * Math.exp(-0.5 * d2 * d2)) * 1.6 - 0.8;
            }
            trace(arr, "#ff3b30", 2);
            if (info) info.textContent = (V("smode") < 0.5 ? "SPECTRAL RESYNTH / " : "SPECTRUM / ") + Math.round(c1) + " HZ" + (m > 0.01 ? " > " + Math.round(c2) + " HZ" : "");
        } else if (type === 10) {'''
rep("        } else if (type === 10) {", DISPLAY)
open(P, "w").write(s)
print("ok")
