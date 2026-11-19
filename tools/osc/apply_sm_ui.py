#!/usr/bin/env python3
"""Adds the Sampler parameters (ids 12300 + 16 * slot + j, tools/osc/build_sm.py) to patch/index.js: spec rows and the controls of the fallback UI.  Idempotent."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
src = open(os.path.join(HERE, "build_sm.py")).read().split("DSP = r'''")[0].replace("PATCH = sys.argv[1] if len(sys.argv) > 1 else", "PATCH =")
ns = {"os": os, "re": re, "sys": sys, "__file__": os.path.join(HERE, "build_sm.py")}; exec(compile(src, "bsm", "exec"), ns)
SM, SM_BASE, SM_STRIDE, sm_id = ns["SM"], ns["SM_BASE"], ns["SM_STRIDE"], ns["sm_id"]
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
rows = []
for o in range(6):
    for j, key, label, short, lo, hi, init, unit, kind, labels in SM:
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (sm_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
body = s[i:j]
body = re.sub(r"\n    // SM-BEGIN.*?// SM-END", "", body, flags=re.S)
s = s[:i] + body + ",\n    // SM-BEGIN\n" + ",\n".join(rows) + "\n    // SM-END" + s[j:]
s = re.sub(r"const SM_BASE = .*?\nconst smId = [^\n]*\n", "", s, flags=re.S)
s = s.replace("const SF_BASE = ", "const SM_BASE = %d, SM_STRIDE = %d;\nconst SM_K = %s;\nconst smId = (o, key) => SM_BASE + SM_STRIDE * o + SM_K[key];\nconst SF_BASE = " % (SM_BASE, SM_STRIDE, json.dumps({p[1]: p[0] for p in SM})), 1)
if "const mx = key => this.controlHTML(smId(o, key), true);" not in s:
    old = "        const sx = key => this.controlHTML(spId(o, key), true);\n"
    assert s.count(old) == 1
    s = s.replace(old, old + "        const mx = key => this.controlHTML(smId(o, key), true);\n")
s = re.sub(r'\$\{sh\("1", \["root", "sstart", "sloop"\]\.map\(c\)\.join\(""\)[^\n]*"cgrid o-g3"\)\}', '${sh("1", ["root", "sstart", "sloop"].map(c).join("") + [' + ", ".join('"%s"' % p[1] for p in SM) + '].map(mx).join(""), "cgrid o-g3")}', s)
assert "].map(mx).join" in s
open(P, "w").write(s)
print("ok")
