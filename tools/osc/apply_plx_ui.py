#!/usr/bin/env python3
"""Adds the Plaits extras to patch/index.js (specs, mod destinations, fallback UI).  Run once, after tools/kick/apply_kick_ui.py."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "PLX_K" in s: raise SystemExit("already applied")
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old))
    s = s.replace(old, new)
rep('const kickId = (o, key) => KICK_BASE + KICK_STRIDE * o + KICK_K[key];',
    'const kickId = (o, key) => KICK_BASE + KICK_STRIDE * o + KICK_K[key];\nconst PLX_BASE = %d, PLX_STRIDE = %d;\nconst PLX_K = %s;\nconst plxId = (o, key) => PLX_BASE + PLX_STRIDE * o + PLX_K[key];' % (L.PLX_BASE, L.PLX_STRIDE, json.dumps({p[1]: p[0] for p in L.PLX})))
rows = []
for o in range(L.OSC_COUNT):
    for p in L.PLX:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.plx_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j] + ",\n" + ",\n".join(rows) + s[j:]
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.PLX_DST_BASE, len(d)
for o in range(L.OSC_COUNT):
    for p in L.PLX: d.append("OSC %d %s" % (o + 1, p[2]))
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.plxdst(o, 0), "OSC %d Plaits extras" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.PLX: t[str(L.plx_id(o, p[0]))] = [L.plxdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
rep('        const kk = key => this.controlHTML(kickId(o, key), true);\n', '        const kk = key => this.controlHTML(kickId(o, key), true);\n        const px = key => this.controlHTML(plxId(o, key), true);\n')
rep('${sh("2", ["pleng", "pharm", "ptimb", "pmorph"].map(c).join(""), "cgrid o-g3 o-pl")}',
    '${sh("2", ["pleng", "pharm", "ptimb", "pmorph"].map(c).join("") + `<div class="o-uh">Modulation</div>` + ["xedec", "xeharm", "xetimb", "xemorph", "xvtimb", "xvmorph", "xkey", "xpenv"].map(px).join("")\n                + `<div class="o-uh">Output</div>` + ["xacc", "xaux", "xlpg", "xlpgdec", "xlpgcol", "xdrive", "xbits", "xrate"].map(px).join(""), "cgrid o-g3 o-pl")}')
open(P, "w").write(s)
print("ok", len(rows))
