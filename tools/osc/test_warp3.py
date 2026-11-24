#!/usr/bin/env python3
"""Warp 3: new modes 18..26, per-voice Amount modulation (dest 5662+o), modes 0..17 unchanged.
python3 tools/osc/test_warp3.py --host <new dsp_host> [--ref <host built before the change>]"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); ap.add_argument("--ref"); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="warp3"); RATE = 48000; fails = 0; K = {p[1]: p[0] for p in L.PARAMS}
def check(n, ok, x=""):
    global fails; print(("PASS " if ok else "FAIL ") + n + (("  (" + x + ")") if x else "")); fails += (not ok)
def render(host, lines, tag, note=57):
    sc = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    open(sc, "w").write("\n".join(["wt 0 saw", "p %d 0.5" % L.pid(0, K["level"])] + lines + ["run 0.05", "on %d 100" % note, "run 0.6", "off %d" % note, "run 0.1"]))
    subprocess.run([host, sc, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2).astype(np.float64)
def w3(m, a): return ["p 12500 %d" % m, "p 12501 %g" % a]
base = render(args.host, [], "base")
for m in range(18, 27):
    y = render(args.host, w3(m, 0.7), "m%d" % m)
    check("mode %d: finite, bounded, differs from Off" % m, np.all(np.isfinite(y)) and np.max(np.abs(y)) < 3 and np.max(np.abs(y - base)) > 1e-3, "peak %.2f" % np.max(np.abs(y)))
# per-voice modulation of the Warp 3 amount: velocity (source 21) -> dest 5662, amount 1 = +-50% of the range
ms = render(args.host, w3(22, 0.2) + ["p 307 21", "p 308 5662", "p 309 1"], "mod")
st = render(args.host, w3(22, 0.2 + 0.5 * 100 / 127), "static")
s0 = render(args.host, w3(22, 0.2), "nomod")
e = np.max(np.abs(ms - st)); d = np.max(np.abs(ms - s0))
check("amount modulation acts (differs from unmodulated)", d > 1e-2, "%.3f" % d)
check("modulated == static amount with the same value", e < 0.02, "%.4f" % e)
if args.ref:
    same = True
    for k, (a, b, c) in enumerate([(m, 0, 0) for m in range(18)] + [(0, m, 0) for m in range(1, 18)] + [(0, 0, m) for m in range(1, 18)] + [(3, 9, 12)]):
        ln = ["p %d %d" % (L.pid(0, K["w1m"]), a), "p %d 0.6" % L.pid(0, K["w1a"]), "p %d %d" % (L.pid(0, K["w2m"]), b), "p %d 0.4" % L.pid(0, K["w2a"])] + w3(c, 0.55)
        x, y = render(args.host, ln, "n%d" % k), render(args.ref, ln, "r%d" % k)
        if not np.array_equal(x, y): same = False; print("  differs:", a, b, c)
    check("modes 0..17 bit-identical to the previous build", same)
print("%d failures" % fails); sys.exit(1 if fails else 0)
