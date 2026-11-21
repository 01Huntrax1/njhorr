#!/usr/bin/env python3
"""LFO extras (tools/lfo/build_lfo2.py) in patch/index.js: wave list +Table, spec rows ids 13000 + 16 * lfo + j.  Idempotent."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "build_lfo2.py")).read().split("CODE = r'''")[0].replace("PATCH = sys.argv[1] if len(sys.argv) > 1 else", "PATCH =")
ns = {"os": os, "re": re, "sys": sys, "__file__": os.path.join(HERE, "build_lfo2.py")}; exec(compile(src, "bl2", "exec"), ns)
L2, BASE, lid = ns["L2"], ns["BASE"], ns["lid"]
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
s = s.replace('const MOD_WAVES = ["Sin", "Tri", "Sqr", "S&H", "Up", "Dn", "Drawn"];', 'const MOD_WAVES = ["Sin", "Tri", "Sqr", "S&H", "Up", "Dn", "Drawn", "Table"];')
s = s.replace('L.push([247 + 2 * i, "LFO " + (i + 1) + " Wave", 0, 6, 0,', 'L.push([247 + 2 * i, "LFO " + (i + 1) + " Wave", 0, 7, 0,')
rows = []
for i in range(10):
    for j, key, arr, label, short, lo, hi, init, unit, kind, labels in L2:
        lab = json.dumps(labels) if labels else ("LFO_STEPS" if key == "steps" else "null")
        rows.append('    L.push([%d, "LFO %d %s", %s, %s, %s, %s, %s, %s, 1, %s, null]);' % (lid(i, j), i + 1, label, lo, hi, init, json.dumps(unit), json.dumps(kind), lab, json.dumps(short)))
blk = "    // LFO2-BEGIN\n" + "\n".join(rows) + "\n    // LFO2-END\n"
s = re.sub(r"    // LFO2-BEGIN\n.*?    // LFO2-END\n", "", s, flags=re.S)
anchor = "    // MOD-LFOBIP: Polarity of every LFO (3111 + i), default Bipolar\n"
assert s.count(anchor) == 1
s = s.replace(anchor, blk + anchor)
if "const LFO_STEPS" not in s:
    s = s.replace("const MOD_WAVES = ", 'const LFO_STEPS = ["Off", "Off"].concat(Array.from({ length: 31 }, (_, k) => String(k + 2)));\nconst MOD_WAVES = ', 1)
open(P, "w").write(s); print("ok")
