#!/usr/bin/env python3
"""Wavefilter effect (FX type 39): built-in table frames shape the spectrum around the cutoff, the cutoff moves it, Mix / Range / Table work.   python3 tools/fx/test_wfx.py --host <dsp_host>"""
import argparse, math, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="wfx"); RATE = 48000; fails = 0
def check(n, ok, x=""):
    global fails; print(("PASS " if ok else "FAIL ") + n + (("  (" + x + ")") if x else "")); fails += (not ok)
def base(slot): return 541 + 10 * slot + (10 if slot >= 10 else 0) + (10 if slot >= 20 else 0)
def render(tag, p=None, fxon=True, ty=39, mode=0, note=45):
    sc = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32"); b = base(0)
    p = dict(p or {}); vals = [p.get(i, d) for i, d in enumerate([0.5, 0.2, 0.0, 0.0, 0.5, 0.5])]
    with open(sc, "w") as f:
        f.write("wt 0 saw\np %d 0\n" % L.pid(0, L.K["fon"]))
        if fxon:
            f.write("p %d %d\np %d 1\np %d %s\np %d %d\n" % (b, ty, b + 1, b + 2, p.get("mix", 1.0), b + 3, mode))
            for i, v in enumerate(vals): f.write("p %d %s\n" % (b + 4 + i, v))
        f.write("run 0.3\non %d 110\nrun 0.6\noff %d\nrun 0.2\n" % (note, note))
    subprocess.run([args.host, sc, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)[int(0.5 * RATE):int(0.9 * RATE)].astype(np.float64)
def band(w, lo, hi):
    s = np.abs(np.fft.rfft(w[:, 0] * np.hanning(len(w)))) ** 2; f = np.fft.rfftfreq(len(w), 1 / RATE)
    return s[(f >= lo) & (f < hi)].sum() + 1e-18
def db(a, b): return 10 * math.log10(a / b)
dry = render("dry", fxon=False)
check("dry saw is audible", band(dry, 50, 20000) > 1e-4)
# built-in frame 0 of the filter table = low pass around the cutoff
lp = render("lp", dict(zip(range(6), [0.55, 0.1, 0.0, 0.0, 0.5, 0.5])))
lo, hi = band(lp, 100, 600), band(lp, 6000, 16000)
check("frame 0 (low pass): highs are far below lows", db(hi, lo) < -20, "%.1f dB" % db(hi, lo))
# a lower cutoff pushes the whole spectrum down
lp2 = render("lp2", dict(zip(range(6), [0.35, 0.1, 0.0, 0.0, 0.5, 0.5])))
check("lower Cutoff removes more of the highs", band(lp2, 1500, 8000) < 0.3 * band(lp, 1500, 8000), "%.1f dB" % db(band(lp2, 1500, 8000), band(lp, 1500, 8000)))
# frame 5 = gentle high pass
hp = render("hp", dict(zip(range(6), [0.55, 0.1, 5 / 15, 0.0, 0.5, 0.5])))
rl, rh = db(band(hp, 100, 400), band(dry, 100, 400)), db(band(hp, 4000, 12000), band(dry, 4000, 12000))
check("frame 5 (high pass): lows attenuated far more than highs (relative to the dry signal)", rh - rl > 12, "%.1f dB lows, %.1f dB highs" % (rl, rh))
# mix 0 = dry
m0 = render("m0", dict(zip(range(6), [0.55, 0.1, 0, 0, 0.5, 0.5]), mix=0.0))
check("Mix 0 is the dry signal", abs(db(band(m0, 50, 20000), band(dry, 50, 20000))) < 0.5, "%.2f dB" % db(band(m0, 50, 20000), band(dry, 50, 20000)))
# a narrower range makes the slope steeper
nar = render("nar", dict(zip(range(6), [0.55, 0.1, 0, 0, 0.0, 0.5])))
wid = render("wid", dict(zip(range(6), [0.55, 0.1, 0, 0, 1.0, 0.5])))
check("narrow Range: steeper slope", band(nar, 4000, 12000) < 0.8 * band(wid, 4000, 12000), "%.1f dB" % db(band(nar, 4000, 12000), band(wid, 4000, 12000)))
# the table is a different oscillator's table (built-in defaults are the same, so the result stays finite and equal)
t2 = render("t2", dict(zip(range(6), [0.55, 0.1, 0, 0.4, 0.5, 0.5])))
check("Table 3 (built-in) stays finite", np.isfinite(t2).all() and np.abs(t2).max() < 4)
# extremes stay finite
ex = render("ex", dict(zip(range(6), [1.0, 1.0, 0.5, 1.0, 1.0, 1.0])), mode=2)
check("extreme settings stay finite", np.isfinite(ex).all() and np.abs(ex).max() < 8, "%.2f" % np.abs(ex).max())
# the same effect in the oscillator rack of OSC 1 (per voice, memory-light): low pass frame, highs fall
def oscrack(tag, vals, ty=39, osc=0, sl=0):
    sc = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32"); b = 8000 + 272 * osc + 16 * sl
    with open(sc, "w") as f:
        f.write("wt 0 saw\np %d 0\n" % L.pid(0, L.K["fon"]))
        f.write("p %d %d\np %d 1\np %d 1.0\np %d 0\n" % (b, ty, b + 1, b + 2, b + 3))
        for i, v in enumerate(vals): f.write("p %d %s\n" % (b + 4 + i, v))
        f.write("p %d 1\n" % L.pid(0, L.K["fon"]) if False else "")
        f.write("run 0.3\non 45 110\nrun 0.6\noff 45\nrun 0.2\n")
    subprocess.run([args.host, sc, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)[int(0.5 * RATE):int(0.9 * RATE)].astype(np.float64)
# the oscillator source is the saw wavetable; reference = the same without the effect
dr = oscrack("rdry", [0.5] * 6, ty=0)
lr = oscrack("rlp", [0.55, 0.1, 0.0, 0.0, 0.5, 0.5])
check("oscillator rack: Wavefilter low pass", db(band(lr, 6000, 16000), band(lr, 100, 600)) < db(band(dr, 6000, 16000), band(dr, 100, 600)) - 15, "%.1f dB vs dry %.1f dB" % (db(band(lr, 6000, 16000), band(lr, 100, 600)), db(band(dr, 6000, 16000), band(dr, 100, 600))))
sys.exit(1 if fails else 0)
