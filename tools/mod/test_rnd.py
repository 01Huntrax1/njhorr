#!/usr/bin/env python3
"""Tests of the 10 random modulators (sources 23, 44..52; params 7500 + 8 * r).   python3 tools/mod/test_rnd.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="rndTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def render(cmds, notes=1, hold=2.0, tag="x", note=69):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        for i in range(notes): f.write("run 0.05\non %d 100\nrun %s\noff %d\nrun 0.3\n" % (note, hold, note))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def track(a, t0, t1, w=0.01):   # rms in windows of w seconds
    return np.array([rms(a[int((t0 + i * w) * RATE):int((t0 + (i + 1) * w) * RATE)]) for i in range(int((t1 - t0) / w))])
BASE = [(21, 4000.0), "wt 0 sine", (L.pid(0, K["fon"]), 0), (L.pid(0, K["level"]), 0.0)]
def route(src, slot=0, dest=1, amt=1.0): return [(307 + 3 * slot, src), (308 + 3 * slot, L.dst_index(0, dest)), (309 + 3 * slot, amt)]
def rnd(r, mode=0, rate=4.0, smooth=0.0, dist=0, uni=1, seed=0, sync=0, div=8):
    b = 7500 + 8 * r
    return [(b, mode), (b + 1, rate), (b + 2, sync), (b + 3, div), (b + 4, smooth), (b + 5, dist), (b + 6, uni), (b + 7, seed)]
SRC = lambda r: 23 if r == 0 else 43 + r
# Note mode: one value per note, constant while it is held
a = render(BASE + route(23) + rnd(0, 0), tag="note")
t = track(a, 1.0, 1.9)
check("RND 1 (source 23) default: constant value per note", t.max() > 0.01 and t.max() - t.min() < 0.1 * t.max(), "%.3f..%.3f" % (t.min(), t.max()))
# S&H moves
a = render(BASE + route(23) + rnd(0, 1, rate=10.0), tag="sh")
t = track(a, 0.1, 1.9)
check("S&H 10 Hz: the value changes over time", t.max() - t.min() > 0.3 * t.max(), "%.3f..%.3f" % (t.min(), t.max()))
# Glide is smoother than S&H
g = render(BASE + route(23) + rnd(0, 2, rate=10.0), tag="gl")
tg = track(g, 0.1, 1.9, 0.005); ts = track(a, 0.1, 1.9, 0.005)
check("Glide: smaller jumps between neighbouring windows than S&H", np.abs(np.diff(tg)).max() < 0.5 * np.abs(np.diff(ts)).max(), "%.3f %.3f" % (np.abs(np.diff(tg)).max(), np.abs(np.diff(ts)).max()))
# Smooth
sm = render(BASE + route(23) + rnd(0, 1, rate=10.0, smooth=0.6), tag="sm")
tm = track(sm, 0.1, 1.9, 0.005)
check("Smooth slews the steps of S&H", np.abs(np.diff(tm)).max() < 0.5 * np.abs(np.diff(ts)).max(), "%.3f" % np.abs(np.diff(tm)).max())
# Binary distribution: only two levels
b = render(BASE + route(23) + rnd(0, 1, rate=20.0, dist=2), tag="bin")
tb = track(b, 0.1, 1.9, 0.01)
mid = ((tb > 0.15 * tb.max()) & (tb < 0.85 * tb.max())).mean()
check("Binary distribution: values sit at the two extremes", mid < 0.15 and tb.min() < 0.1 * tb.max(), "mid share %.2f" % mid)
# Walk moves in small steps
w = render(BASE + route(23) + rnd(0, 3, rate=10.0, uni=1), tag="walk")
tw = track(w, 0.1, 1.9, 0.005)
check("Walk: small steps (smaller jumps than S&H)", np.abs(np.diff(tw)).max() < 0.8 * np.abs(np.diff(ts)).max() and tw.max() > 0.01, "%.3f" % np.abs(np.diff(tw)).max())
# Seed: same value sequence on every note; without seed the notes differ
SHORT = [(21, 5.0)]
s = render(BASE + SHORT + route(23) + rnd(0, 0, seed=3), notes=2, hold=1.0, tag="seed")
n1 = rms(s[int(0.2 * RATE):int(0.5 * RATE)]); n2 = rms(s[int((0.05 + 1.3 + 0.05 + 0.2) * RATE):int((0.05 + 1.3 + 0.05 + 0.5) * RATE)])
check("Seed 3: both notes get the same value", abs(n1 - n2) < 0.02 * max(n1, 1e-6) and n1 > 0.01, "%.4f %.4f" % (n1, n2))
u = render(BASE + SHORT + route(23) + rnd(0, 0, seed=0), notes=2, hold=1.0, tag="noseed")
m1 = rms(u[int(0.2 * RATE):int(0.5 * RATE)]); m2 = rms(u[int((0.05 + 1.3 + 0.05 + 0.2) * RATE):int((0.05 + 1.3 + 0.05 + 0.5) * RATE)])
check("Seed 0: the notes get different values", abs(m1 - m2) > 0.02 * max(m1, m2), "%.4f %.4f" % (m1, m2))
# seeds differ
s2 = render(BASE + route(23) + rnd(0, 0, seed=5), tag="seed5"); s1 = render(BASE + route(23) + rnd(0, 0, seed=3), tag="seed3")
check("Different seeds give different values", abs(rms(s1[int(0.2 * RATE):int(0.5 * RATE)]) - rms(s2[int(0.2 * RATE):int(0.5 * RATE)])) > 0.01)
# RND 2..10 (sources 44..52) are independent and configured separately
for r in range(1, 10):
    a = render(BASE + route(SRC(r)) + rnd(r, 1, rate=10.0), hold=1.2, tag="r%d" % r)
    t = track(a, 0.1, 1.1)
    ok = t.max() - t.min() > 0.3 * t.max()
    b = render(BASE + route(SRC(r)) + rnd(0, 1, rate=10.0) + rnd(r, 0), hold=1.2, tag="rb%d" % r)   # RND 1 moving, RND r in Note mode
    tb = track(b, 0.1, 1.1)
    check("RND %d (source %d): own settings, S&H moves, other RND does not leak" % (r + 1, SRC(r)), ok and tb.max() - tb.min() < 0.15 * tb.max(), "%.3f..%.3f / %.3f..%.3f" % (t.min(), t.max(), tb.min(), tb.max()))
# bipolar stays inside -1..1 and negative values reach the destination sign (level goes negative -> phase inversion)
bp = render(BASE + route(23) + rnd(0, 1, rate=10.0, uni=0), tag="bip")
check("Bipolar output stays bounded", np.isfinite(bp).all() and np.abs(bp).max() < 1.2)
print("%d failures" % failures); sys.exit(1 if failures else 0)
