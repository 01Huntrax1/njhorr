#!/usr/bin/env python3
"""Checks that every parameter declared in patch/Eisenpuls_Synth.cmajor has the same min / max / init as the UI spec table
(native_ui/NjoData.gen.cpp, generated from patch/index.js), and the other way round.  The host clamps values to the declared
range, so a declaration that is too small silently cuts a UI value (this once turned Seq 1-10 into Freq 10 in the matrix).
python3 tools/check_params.py"""
import os, re, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
c = open(os.path.join(R, 'patch', 'Eisenpuls_Synth.cmajor')).read()
decl = {}
for m in re.finditer(r'input event float param(\d+)\s*\[\[(.*?)\]\]', c, re.S):
    a = m.group(2); g = lambda k: (re.search(r'\b' + k + r':\s*(-?[\d.]+)', a) or [None, None])[1]
    decl[int(m.group(1))] = (g('min'), g('max'), g('init'))
spec = {}
for m in re.finditer(r'Spec \{ (\d+), NJ_S\("([^"]*)"\), (-?[\d.e+-]+), (-?[\d.e+-]+), (-?[\d.e+-]+),', open(os.path.join(R, 'native_ui', 'NjoData.gen.cpp')).read()):
    spec[int(m.group(1))] = (m.group(2), float(m.group(3)), float(m.group(4)), float(m.group(5)))
bad = []
for n, (nm, lo, hi, ini) in spec.items():
    if n not in decl: bad.append("no declaration for %d %s" % (n, nm)); continue
    dl, dh, di = decl[n]
    if dl is None or dh is None: continue
    if abs(float(dl) - lo) > 1e-6 or abs(float(dh) - hi) > 1e-6 or (di is not None and abs(float(di) - ini) > 1e-3):
        bad.append("%d %s: declared %s..%s init %s, UI %s..%s init %s" % (n, nm, dl, dh, di, lo, hi, ini))
bad += ["no UI spec for %d" % n for n in decl if n not in spec]
for b in bad[:50]: print("FAIL", b)
print("%d declarations, %d specs: %s" % (len(decl), len(spec), "%d problems" % len(bad) if bad else "all match"))
sys.exit(1 if bad else 0)
