#!/usr/bin/env python3
"""patch/index.js: the parameters of tools/modall/ids.json become modulation destinations 1584 + k (names, groups, knob drop targets).  Idempotent."""
import os, re, json
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.join(HERE, "..", "..", "patch", "index.js")
s = open(P).read(); ids = json.load(open(os.path.join(HERE, "ids.json"))); FIRST = 1584
def grp(n):
    t = n.split()
    if t[0] == "OSC" and len(t) > 3 and t[2] == "FX": return "Param " + " ".join(t[:4])
    if t[0] == "OSC" and len(t) > 2: return "Param " + " ".join(t[:2]) + " " + t[2]
    if len(t) > 3 and t[:2] == ["Main", "FX"]: return "Param " + " ".join(t[:3])
    if len(t) > 1 and (t[1].isdigit() or t[1] in ("FX", "Bus")): return "Param " + " ".join(t[:2])
    return "Param " + t[0]
m = re.search(r"const MOD_DST = (\[.*?\]);\n", s); d = json.loads(m.group(1))
if len(d) > FIRST: print("already applied"); raise SystemExit
assert len(d) == FIRST
d += [r[1] for r in ids]
s = s[:m.start(1)] + json.dumps(d) + s[m.end(1):]
m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", s); g = json.loads(m.group(1)); last = None
for k, r in enumerate(ids):
    gl = grp(r[1])
    if gl != last: g.append([FIRST + k, gl]); last = gl
s = s[:m.start(1)] + json.dumps(g) + s[m.end(1):]
m = re.search(r"const MOD_TARGET = (\{.*?\});", s); t = json.loads(m.group(1)); n = 0
for k, r in enumerate(ids):
    if str(r[0]) not in t: t[str(r[0])] = [FIRST + k, 0.5]; n += 1
s = s[:m.start(1)] + json.dumps(t) + s[m.end(1):]
open(P, "w").write(s); print("ok", len(ids), "dests,", len(g), "groups,", n, "new drop targets")
