#!/usr/bin/env python3
"""Envelope extras (tools/env/build_env2.py) in patch/index.js: spec rows ids 13300 + 16 * k + j.  Idempotent."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "build_env2.py")).read().split("CODE = r'''")[0].replace("PATCH = sys.argv[1] if len(sys.argv) > 1 else", "PATCH =")
ns = {"os": os, "re": re, "sys": sys, "__file__": os.path.join(HERE, "build_env2.py")}; exec(compile(src, "be2", "exec"), ns)
E2, NK, eid, ename = ns["E2"], ns["NK"], ns["eid"], ns["ename"]
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
rows = []
for k in range(NK):
    for j, key, arr, label, short, lo, hi, init, unit, kind, labels in E2:
        rows.append('    L.push([%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]);' % (eid(k, j), json.dumps("%s %s" % (ename(k), label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels) if labels else "null", json.dumps(short)))
blk = "    // ENV2-BEGIN\n" + "\n".join(rows) + "\n    // ENV2-END\n"
s = re.sub(r"    // ENV2-BEGIN\n.*?    // ENV2-END\n", "", s, flags=re.S)
anchor = "    // MOD-LFOBIP: Polarity of every LFO (3111 + i), default Bipolar\n"
assert s.count(anchor) == 1
s = s.replace(anchor, blk + anchor)
open(P, "w").write(s); print("ok")
