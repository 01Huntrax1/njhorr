#!/usr/bin/env python3
"""Wavetable rework (tools/osc/build_wt2.py) in patch/index.js: warp mode list, Warp 1 / 2 Mode range, spec rows of the extras (ids 12500 + 16 * slot + j), controls of the fallback UI.  Idempotent."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
src = open(os.path.join(HERE, "build_wt2.py")).read().split("WARP = r'''")[0].replace("PATCH = sys.argv[1] if len(sys.argv) > 1 else", "PATCH =")
ns = {"os": os, "re": re, "sys": sys, "__file__": os.path.join(HERE, "build_wt2.py")}; exec(compile(src, "bwt", "exec"), ns)
WT, WT_BASE, WT_STRIDE, wt_id, NMODES, WARP_NAMES = ns["WT"], ns["WT_BASE"], ns["WT_STRIDE"], ns["wt_id"], ns["NMODES"], ns["WARP_NAMES"]
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
s = re.sub(r"const WARP_MODES = \[.*?\];", lambda m: "const WARP_MODES = " + json.dumps(WARP_NAMES) + ";", s, count=1)
s = re.sub(r'(\[\d+, "OSC \d Warp [12] Mode", 0, )\d+', r"\g<1>%d" % (NMODES - 1), s)
rows = []
for o in range(6):
    for j, key, label, short, lo, hi, init, unit, kind, labels in WT:
        lab = "WARP_MODES" if key == "w3m" else json.dumps(labels)
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (wt_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), lab, json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
body = re.sub(r"\n    // WT2-BEGIN.*?// WT2-END", "", s[i:j], flags=re.S)
s = s[:i] + body + ",\n    // WT2-BEGIN\n" + ",\n".join(rows) + "\n    // WT2-END" + s[j:]
s = re.sub(r"const WT_BASE = .*?\nconst wtId = [^\n]*\n", "", s, flags=re.S)
s = s.replace("const SF_BASE = ", "const WT_BASE = %d, WT_STRIDE = %d;\nconst WT_K = %s;\nconst wtId = (o, key) => WT_BASE + WT_STRIDE * o + WT_K[key];\nconst SF_BASE = " % (WT_BASE, WT_STRIDE, json.dumps({p[1]: p[0] for p in WT})), 1)
if "const wtc = key => this.controlHTML(wtId(o, key), true);" not in s:
    old = "        const sx = key => this.controlHTML(spId(o, key), true);\n"
    assert s.count(old) == 1
    s = s.replace(old, old + "        const wtc = key => this.controlHTML(wtId(o, key), true);\n")
old = '${sh("0", ["wpos", "wsize", "w1m", "w1a", "w2m", "w2a"].map(c).join("") + this.controlHTML(2000 + o, true), "cgrid o-g2")}'
new = '${sh("0", ["wpos", "wsize", "w1m", "w1a", "w2m", "w2a"].map(c).join("") + this.controlHTML(2000 + o, true) + ["w3m", "w3a", "wmorph", "wtone"].map(wtc).join(""), "cgrid o-g2")}'
if new not in s:
    assert s.count(old) == 1; s = s.replace(old, new)
open(P, "w").write(s)
print("ok")
