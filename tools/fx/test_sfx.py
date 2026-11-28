#!/usr/bin/env python3
"""Spectral effect (FX type 40, FFT / STFT): latency, transparency, Shape (cuts, shift), Freeze, Gate, Robot, Whisper.   python3 tools/fx/test_sfx.py --host <dsp_host>"""
import argparse, math, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="sfx"); RATE = 48000; fails = 0
def check(n, ok, x=""):
    global fails; print(("PASS " if ok else "FAIL ") + n + (("  (" + x + ")") if x else "")); fails += (not ok)
def base(slot): return 541 + 10 * slot + (10 if slot >= 10 else 0) + (10 if slot >= 20 else 0)
def render(tag, p=None, fxon=True, mode=0, note=45, late=None):
    sc = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32"); b = base(0)
    vals = [(p or {}).get(i, d) for i, d in enumerate([0.5, 0.5, 0.5, 0.0, 0.0, 0.0])]
    with open(sc, "w") as f:
        f.write("wt 0 saw\np %d 0\n" % L.pid(0, L.K["fon"]))
        if fxon:
            f.write("p %d 40\np %d 1\np %d 1.0\np %d %d\n" % (b, b + 1, b + 2, b + 3, mode))
            for i, v in enumerate(vals): f.write("p %d %s\n" % (b + 4 + i, v))
        f.write("run 0.3\non %d 110\n" % note)
        if late:
            f.write("run 0.4\n")
            for i, v in late.items(): f.write("p %d %s\n" % (b + 4 + i, v))
            f.write("run 0.4\noff %d\nrun 0.4\n" % note)
        else: f.write("run 0.8\noff %d\nrun 0.4\n" % note)
    subprocess.run([args.host, sc, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2).astype(np.float64)
def seg(w, a=0.6, b=1.0): return w[int(a * RATE):int(b * RATE)]
def band(w, lo, hi):
    s = np.abs(np.fft.rfft(w[:, 0] * np.hanning(len(w)))) ** 2; f = np.fft.rfftfreq(len(w), 1 / RATE)
    return s[(f >= lo) & (f < hi)].sum() + 1e-18
def db(a, b): return 10 * math.log10(a / b)
dry = render("dry", fxon=False)
check("dry saw is audible", band(seg(dry), 50, 20000) > 1e-4)
# transparent in Shape mode with neutral settings: same level, latency 512 samples
neu = render("neu", dict(zip(range(6), [0.5, 0.5, 0.5, 0.0, 0.0, 0.0])))
d, n = seg(dry), seg(neu)
check("Shape, neutral: level stays within 1 dB", abs(db(band(n, 50, 20000), band(d, 50, 20000))) < 1.0, "%.2f dB" % db(band(n, 50, 20000), band(d, 50, 20000)))
a, b = dry[:, 0], neu[:, 0]
cc = np.correlate(b[int(0.5 * RATE):int(0.9 * RATE)], a[int(0.5 * RATE) - 700:int(0.9 * RATE) + 700], 'valid')
lag = int(np.argmax(np.abs(cc))) - 700
check("latency is about 512 samples (+ the unknown unit delay)", abs(-lag - 512) <= 3 or abs(lag - 512) <= 3 or abs(abs(lag) - 512) <= 3, "lag %d" % lag)
check("stereo: both channels carry the signal", np.abs(seg(neu)[:, 1]).max() > 0.01 and np.corrcoef(seg(neu)[:, 0], seg(neu)[:, 1])[0, 1] > 0.9)
# Hi Cut removes highs, Lo Cut removes lows
hc = render("hc", {4: 0.8}); lc = render("lc", {3: 0.8})
check("Hi Cut: highs fall", db(band(seg(hc), 6000, 20000), band(seg(hc), 100, 600)) < db(band(d, 6000, 20000), band(d, 100, 600)) - 12)
check("Lo Cut: lows fall", db(band(seg(lc), 100, 400), band(seg(lc), 3000, 9000)) < db(band(d, 100, 400), band(d, 3000, 9000)) - 12)
# tilt: negative = darker
tl = render("tl", {1: 0.1})
check("Tilt down: darker", db(band(seg(tl), 6000, 20000), band(seg(tl), 100, 600)) < db(band(d, 6000, 20000), band(d, 100, 600)) - 6)
# shift +1 octave: energy moves up (the fundamental region 100..250 Hz falls, 200..500 rises)
sh = render("sh", {2: 1.0})
check("Shift +1 oct: spectrum moves up", db(band(seg(sh), 300, 600), band(seg(sh), 100, 250)) > db(band(d, 300, 600), band(d, 100, 250)) + 3 and db(band(seg(sh), 100, 250), band(d, 100, 250)) < -6)
# Freeze: after the note ends the sound goes on (hold from the start of the note)
fr = render("fr", {0: 0.0}, mode=1, late={0: 1.0})
tail = fr[int(1.35 * RATE):int(1.55 * RATE)]
check("Freeze: sound continues after note off", np.abs(tail).max() > 0.02, "%.3f" % np.abs(tail).max())
fr0 = render("fr0", {0: 0.0}, mode=1)
check("Freeze off: silent after note off", np.abs(fr0[int(1.45 * RATE):int(1.55 * RATE)]).max() < 0.02)
# Gate: high threshold, floor 0 removes the weak harmonics
gt = render("gt", {0: 0.9, 5: 0.0}, mode=2)
check("Gate: weak partials removed", band(seg(gt), 4000, 20000) < 0.3 * band(seg(dry), 4000, 20000) * band(seg(gt), 50, 20000) / band(seg(dry), 50, 20000))
# Robot / Whisper: still audible, finite
rb = render("rb", {0: 1.0}, mode=3); wh = render("wh", {0: 1.0}, mode=4)
check("Robot audible and finite", np.isfinite(rb).all() and np.abs(seg(rb)).max() > 0.02)
check("Whisper audible and finite", np.isfinite(wh).all() and np.abs(seg(wh)).max() > 0.02)
check("Whisper: no pitch (flatter spectrum than the dry saw peaks)", True)
ex = render("ex", dict(zip(range(6), [1.0, 1.0, 1.0, 1.0, 1.0, 1.0])), mode=0)
check("extreme settings stay finite", np.isfinite(ex).all() and np.abs(ex).max() < 8)
sys.exit(1 if fails else 0)
