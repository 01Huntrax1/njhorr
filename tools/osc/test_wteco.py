#!/usr/bin/env python3
"""Wavetable Eco quality mode: sounds like Clean (low aliasing, similar spectrum) and the Alias mode is unchanged.  python3 tools/osc/test_wteco.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="wteco"); RATE = 48000; fails = 0; K = {p[1]: p[0] for p in L.PARAMS}
def check(n, ok, x=""):
    global fails; print(("PASS " if ok else "FAIL ") + n + (("  (" + x + ")") if x else "")); fails += (not ok)
def render(q, note, tag):
    sc = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    open(sc, "w").write("\n".join(["wt 0 saw", "p %d 0.5" % L.pid(0, K["level"]), "p 2000 %d" % q, "run 0.05", "on %d 100" % note, "run 1.0", "off %d" % note, "run 0.2"]) + "\n")
    subprocess.run([args.host, sc, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)[:, 0][int(0.3 * RATE):int(1.0 * RATE)].astype(np.float64)
def spec(x): return np.abs(np.fft.rfft(x * np.hanning(len(x))))
for note in (45, 69, 93):
    c, e, a = render(0, note, "c%d" % note), render(2, note, "e%d" % note), render(1, note, "a%d" % note)
    rc, re_ = np.sqrt(np.mean(c ** 2)), np.sqrt(np.mean(e ** 2))
    check("note %d: Eco level close to Clean" % note, abs(re_ / rc - 1) < 0.08, "%.3f" % (re_ / rc))
    sc_, se = spec(c), spec(e); lo = len(sc_) // 8   # error below 3 kHz relative to the signal
    err = np.sqrt(np.sum((se[:lo] - sc_[:lo]) ** 2) / np.sum(sc_[:lo] ** 2))
    check("note %d: Eco spectrum below 3 kHz close to Clean" % note, err < 0.25, "%.3f" % err)
    check("note %d: Alias differs from Clean (mode intact)" % note, np.max(np.abs(a - c)) > 1e-4 or note < 60)
print("%d failures" % fails); sys.exit(1 if fails else 0)
