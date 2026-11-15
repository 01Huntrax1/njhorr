#!/usr/bin/env python3
"""Adds the Bagpipe source (Source type 13) to patch/index.js: source name, spec rows 3500.., mod destinations 1488..1583, fallback UI section and display. One-shot; refuses to run twice."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "BP_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
OLD = json.dumps(L.SRC_TYPES[:-1])
n = s.count(OLD); assert n == 7, n
s = s.replace(OLD, json.dumps(L.SRC_TYPES))
s, k = re.subn(r'(\[\d+, "OSC \d Source", 0, )12(, 0, "", "sel")', r'\g<1>13\2', s); assert k == 6, k
rep('Math.max(0, Math.min(12, Math.round(this.oscVal(o, "type"))))', 'Math.max(0, Math.min(13, Math.round(this.oscVal(o, "type"))))')
rep("const SF_BASE = ", "const BP_BASE = %d, BP_STRIDE = %d;\nconst BP_K = %s;\nconst bpId = (o, key) => BP_BASE + BP_STRIDE * o + BP_K[key];\nconst SF_BASE = " % (L.BP_BASE, L.BP_STRIDE, json.dumps({p[1]: p[0] for p in L.BP})))
rows = []
for o in range(L.OSC_COUNT):
    for p in L.BP:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.bp_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j].rstrip().rstrip(",") + ",\n" + ",\n".join(rows) + s[j:]
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.BP_DST_BASE, len(d)
for o in range(L.OSC_COUNT):
    for p in L.BP: d.append("OSC %d %s" % (o + 1, p[2]))
assert len(d) == L.N_DST_TOTAL
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.bpdst(o, 0), "OSC %d Bagpipe" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.BP:
        if p[8] == "sld": t[str(L.bp_id(o, p[0]))] = [L.bpdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
rep("        const fx = key => this.controlHTML(sfId(o, key), true);\n", "        const fx = key => this.controlHTML(sfId(o, key), true);\n        const bx = key => this.controlHTML(bpId(o, key), true);\n")
rep('            ${sh("12", [', '            ${sh("13", [' + ", ".join('"%s"' % p[1] for p in L.BP) + '].map(bx).join(""), "cgrid o-g3 o-pl")}\n            ${sh("12", [')
rep("        } else if (type === 12) {", '        } else if (type === 13) {\n            if (info) info.textContent = "BAGPIPE / CHANTER + DRONES";\n        } else if (type === 12) {')
open(P, "w").write(s)
print("ok")
