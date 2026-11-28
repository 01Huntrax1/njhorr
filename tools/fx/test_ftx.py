#!/usr/bin/env python3
"""Filter Table effect (FX type 41, FFT filter): built-in frames shape the spectrum, Cutoff moves it, Reso, Gain, Mix, latency 1024.   python3 tools/fx/test_ftx.py --host <dsp_host>"""
import argparse, math, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="ftx"); RATE = 48000; fails = 0
def check(n, ok, x=""):
    global fails; print(("PASS " if ok else "FAIL ") + n + (("  (" + x + ")") if x else "")); fails += (not ok)
def base(slot): return 541 + 10 * slot + (10 if slot >= 10 else 0) + (10 if slot >= 20 else 0)
def render(tag, p=None, fxon=True, mode=0, mix=1.0):
    sc = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32"); b = base(0)
    vals = [(p or {}).get(i, d) for i, d in enumerate([0.55, 0.0, 0.0, 0.0, 0.583, 0.5])]
    with open(sc, "w") as f:
        f.write("wt 0 saw\np %d 0\n" % L.pid(0, L.K["fon"]))
        if fxon:
            f.write("p %d 41\np %d 1\np %d %s\np %d %d\n" % (b, b + 1, b + 2, mix, b + 3, mode))
            for i, v in enumerate(vals): f.write("p %d %s\n" % (b + 4 + i, v))
        f.write("run 0.3\non 45 110\nrun 0.8\noff 45\nrun 0.3\n")
    subprocess.run([args.host, sc, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2).astype(np.float64)
def seg(w): return w[int(0.6 * RATE):int(1.0 * RATE)]
def band(w, lo, hi):
    w = seg(w); s = np.abs(np.fft.rfft(w[:, 0] * np.hanning(len(w)))) ** 2; f = np.fft.rfftfreq(len(w), 1 / RATE)
    return s[(f >= lo) & (f < hi)].sum() + 1e-18
def db(a, b): return 10 * math.log10(a / b)
dry = render("dry", fxon=False)
check("dry saw audible", band(dry, 50, 20000) > 1e-4)
lp = render("lp")                       # built-in frame 0 = low pass at the cutoff (~1.5 kHz)
check("frame 0 (low pass): highs far below lows", db(band(lp, 6000, 16000), band(lp, 100, 600)) < db(band(dry, 6000, 16000), band(dry, 100, 600)) - 20, "%.1f dB" % (db(band(lp, 6000, 16000), band(lp, 100, 600)) - db(band(dry, 6000, 16000), band(dry, 100, 600))))
check("lows pass (within 6 dB of the dry level)", abs(db(band(lp, 100, 600), band(dry, 100, 600))) < 6.0, "%.1f dB" % db(band(lp, 100, 600), band(dry, 100, 600)))
lo = render("lo", {0: 0.35})
check("lower Cutoff removes more highs", band(lo, 1500, 8000) < 0.3 * band(lp, 1500, 8000))
hp = render("hp", {2: 5 / 15})          # frame 5 = high pass
check("frame 5 (high pass): lows fall more than highs", db(band(hp, 100, 400), band(dry, 100, 400)) < db(band(hp, 4000, 12000), band(dry, 4000, 12000)) - 12)
re_ = render("re", {1: 1.0})
check("Reso sharpens (steeper low pass)", band(re_, 3000, 12000) < 0.5 * band(lp, 3000, 12000))
g1 = render("g1", {5: 1.0}); g0 = render("g0", {5: 0.0})
check("Gain: +12 dB vs -12 dB", 18 < db(band(g1, 100, 600), band(g0, 100, 600)) < 30, "%.1f dB" % db(band(g1, 100, 600), band(g0, 100, 600)))
m0 = render("m0", mix=0.0)
check("Mix 0 is dry", abs(db(band(m0, 50, 20000), band(dry, 50, 20000))) < 0.5)
# latency 1024 samples
a, b = dry[:, 0], render("neu", {0: 1.0, 4: 1.0, 2: 0.0}, mix=1.0)[:, 0]
cc = np.correlate(b[int(0.5 * RATE):int(0.9 * RATE)], a[int(0.5 * RATE) - 1300:int(0.9 * RATE) + 1300], 'valid'); lag = int(np.argmax(np.abs(cc))) - 1300
check("latency about 1024 samples", abs(abs(lag) - 1024) <= 4, "lag %d" % lag)
st = seg(lp)
check("stereo: both channels carry the signal", np.abs(st[:, 1]).max() > 0.01 and np.corrcoef(st[:, 0], st[:, 1])[0, 1] > 0.95)
dbm = render("dbm", mode=1)
check("dB law finite and audible", np.isfinite(dbm).all() and np.abs(seg(dbm)).max() > 0.005)
ex = render("ex", dict(zip(range(6), [1.0, 1.0, 1.0, 1.0, 1.0, 1.0])))
check("extreme settings stay finite", np.isfinite(ex).all() and np.abs(ex).max() < 8)
sys.exit(1 if fails else 0)
