#!/usr/bin/env python3
"""Parametric EQ band types 15..24 against their analytical responses (a sine at several notes through one band).   python3 tools/fx/test_eqtypes.py --host <dsp_host>"""
import argparse, math, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="eqt"); RATE = 48000; fails = 0
def check(n, ok, x=""):
    global fails; print(("PASS " if ok else "FAIL ") + n + (("  (" + x + ")") if x else "")); fails += (not ok)
def base(slot): return 541 + 10 * slot + (10 if slot >= 10 else 0) + (10 if slot >= 20 else 0)
def render(cmds, note, tag):
    sc = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    b = base(0)
    with open(sc, "w") as f:
        f.write("wt 0 sine\np %d 0\n" % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        f.write("p %d 13\np %d 1\np %d 1.0\np %d 0\n" % (b, b + 1, b + 2, b + 3))
        for i in range(6): f.write("p %d 0.5\n" % (b + 4 + i))
        f.write("run 0.6\non %d 110\nrun 0.3\noff %d\nrun 0.2\n" % (note, note))
    subprocess.run([args.host, sc, out], check=True)
    a = np.fromfile(out, dtype=np.float32).reshape(-1, 2)
    return float(np.sqrt(np.mean(a[int(0.7 * RATE):int(0.9 * RATE), 0].astype(np.float64) ** 2)))
def hz(n): return 440.0 * 2 ** ((n - 69) / 12)
def mag(b, a, f):
    z = np.exp(-1j * 2 * math.pi * f / RATE); zz = [z ** 0, z ** -0 * z, z * z]
    return abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))
def sec(kind, f0, g, q, f):
    w0 = 2 * math.pi * f0 / RATE; cw, sw = math.cos(w0), math.sin(w0); al = sw / (2 * q); A = 10 ** (g / 40); V = 10 ** (g / 20); K = math.tan(w0 / 2)
    if kind == 0: b, a = [1 + al * A, -2 * cw, 1 - al * A], [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == 1:
        t = 2 * math.sqrt(A) * al; b = [A * ((A + 1) - (A - 1) * cw + t), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - t)]; a = [(A + 1) + (A - 1) * cw + t, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - t]
    elif kind == 2:
        t = 2 * math.sqrt(A) * al; b = [A * ((A + 1) + (A - 1) * cw + t), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - t)]; a = [(A + 1) - (A - 1) * cw + t, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - t]
    elif kind == 3: b, a = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2], [1 + al, -2 * cw, 1 - al]
    elif kind == 4: b, a = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2], [1 + al, -2 * cw, 1 - al]
    elif kind == 5: gl = 10 ** (g / 20); b, a = [al * gl, 0, -al * gl], [1 + al, -2 * cw, 1 - al]
    elif kind == 6: b, a = [1, -2 * cw, 1], [1 + al, -2 * cw, 1 - al]
    elif kind == 8: b, a = [K, K, 0], [1 + K, K - 1, 0]
    elif kind == 9: b, a = [1, -1, 0], [1 + K, K - 1, 0]
    elif kind == 10: b, a = [1 + V * K, V * K - 1, 0], [1 + K, K - 1, 0]
    else: b, a = [V + K, K - V, 0], [1 + K, K - 1, 0]
    return mag(b, a, f)
def model(ty, f0, g, q, f):
    if ty == 15: return sec(9, f0, 0, q, f)
    if ty == 16: return sec(8, f0, 0, q, f)
    if ty == 17: return sec(10, f0, g, q, f)
    if ty == 18: return sec(11, f0, g, q, f)
    if ty == 19: return sec(1, f0, g / 2, q, f) ** 2
    if ty == 20: return sec(2, f0, g / 2, q, f) ** 2
    if ty == 21: return sec(6, f0, 0, q, f) ** 2
    if ty == 22: return sec(5, f0, g / 2, q, f) ** 2
    if ty == 23:
        r = min(max(2 ** (0.5 / q), 1.01), 8); return sec(3, max(f0 / r, 10), 0, 0.7071, f) * sec(4, f0 * r, 0, 0.7071, f)
    return sec(0, f0, g, q, f) * sec(0, f0 * 2.5, g * 0.8, q, f) * sec(0, f0 * 3.6, g * 0.64, q, f)
dry = {}
def meas(ty, f0, g, q, note):
    if note not in dry: dry[note] = render([], note, "d%d" % note)
    w = render(["eqband 0 0 1 %d %s %s %s 0 0.5 0 0" % (ty, f0, g, q), "eqsend 0"], note, "t%d_%d" % (ty, note))
    return 20 * math.log10(max(w, 1e-9) / max(dry[note], 1e-9))
cases = [(15, "Low Cut 6", 700, 0, 0.7071, (55, 64, 76)), (16, "High Cut 6", 400, 0, 0.7071, (60, 72, 84)), (17, "Low Shelf 6 +9", 400, 9, 0.7, (45, 60, 76)),
         (18, "High Shelf 6 -9", 400, -9, 0.7, (52, 69, 84)), (19, "Low Shelf 24 +10", 400, 10, 0.7, (45, 60, 76)), (20, "High Shelf 24 -10", 400, -10, 0.7, (52, 69, 84)),
         (21, "Notch 24", 440, 0, 2.0, (63, 69, 75)), (22, "Band Pass 24", 440, 6, 1.5, (60, 69, 78)), (23, "Band Pass Flat", 600, 0, 1.0, (55, 66, 77, 88)),
         (24, "Formant", 500, 8, 3.0, (58, 70, 82, 87))]
for ty, name, f0, g, q, notes in cases:
    err = []
    for nt in notes:
        got = meas(ty, f0, g, q, nt); exp = 20 * math.log10(max(model(ty, f0, g, q, hz(nt)), 1e-9))
        err.append(0.0 if exp < -40 and got < -25 else round(abs(got - max(exp, -50)), 2))
    check("%s matches its analytical response" % name, max(err) < 1.0, str(err))
print("%d failures" % fails); sys.exit(1 if fails else 0)
