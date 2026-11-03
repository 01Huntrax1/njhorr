#!/usr/bin/env python3
"""Adds the SoundFont source (Source type 12) to patch/index.js: source name, spec rows 2800.., mod destinations 1212..1307, fallback UI section and display.
The fallback UI only offers the controls; loading .sf2 files is done by the native UI. One-shot; refuses to run twice."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read()
if "SF_K" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old))
    s = s.replace(old, new)
OLD = json.dumps(L.SRC_TYPES[:-1])
n = s.count(OLD); assert n == 7, n
s = s.replace(OLD, json.dumps(L.SRC_TYPES))
s, k = re.subn(r'(\[\d+, "OSC \d Source", 0, )11(, 0, "", "sel")', r'\g<1>12\2', s); assert k == 6, k
rep('Math.max(0, Math.min(11, Math.round(this.oscVal(o, "type"))))', 'Math.max(0, Math.min(12, Math.round(this.oscVal(o, "type"))))')
rep("const DK_BASE = ", "const SF_BASE = %d, SF_STRIDE = %d;\nconst SF_K = %s;\nconst sfId = (o, key) => SF_BASE + SF_STRIDE * o + SF_K[key];\nconst DK_BASE = " % (L.SF_BASE, L.SF_STRIDE, json.dumps({p[1]: p[0] for p in L.SF})))
rows = []
for o in range(L.OSC_COUNT):
    for p in L.SF:
        j, key, label, short, lo, hi, init, unit, kind, labels = p
        rows.append("    [%d, %s, %s, %s, %s, %s, %s, %s, 1, %s, null]" % (L.sf_id(o, j), json.dumps("OSC %d %s" % (o + 1, label)), lo, hi, init, json.dumps(unit), json.dumps(kind), json.dumps(labels), json.dumps(short)))
i = s.index("const OSC_SPEC_ROWS = ["); j = s.index("\n];", i)
s = s[:j].rstrip().rstrip(",") + ",\n" + ",\n".join(rows) + s[j:]
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s)
d = json.loads(m.group(1)); assert len(d) == L.SF_DST_BASE, len(d)
for o in range(L.OSC_COUNT):
    for p in L.SF: d.append("OSC %d %s" % (o + 1, p[2]))
    for _ in range(16 - len(L.SF)): d.append("OSC %d (unused %d)" % (o + 1, len(d)))
assert len(d) == L.N_DST_TOTAL
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s)
g = json.loads(m.group(1))
for o in range(L.OSC_COUNT): g.append([L.sfdst(o, 0), "OSC %d SoundFont" % (o + 1)])
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s)
t = json.loads(m.group(1))
for o in range(L.OSC_COUNT):
    for p in L.SF:
        if p[8] == "sld": t[str(L.sf_id(o, p[0]))] = [L.sfdst(o, p[0]), 0.5]
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
rep("        const sx = key => this.controlHTML(spId(o, key), true);\n", "        const sx = key => this.controlHTML(spId(o, key), true);\n        const fx = key => this.controlHTML(sfId(o, key), true);\n")
rep('            ${sh("11", [', '            ${sh("12", [' + ", ".join('"%s"' % p[1] for p in L.SF) + '].map(fx).join(""), "cgrid o-g3 o-pl")}\n            ${sh("11", [')
DISPLAY = '''        } else if (type === 12) {
            if (info) info.textContent = "SOUNDFONT / LOAD .SF2 IN THE NATIVE UI";
        } else if (type === 11) {'''
rep("        } else if (type === 11) {", DISPLAY)
open(P, "w").write(s)
print("ok")
