#!/usr/bin/env python3
"""Audio tests of the reworked Wavetable source (tools/osc/build_wt2.py).   python3 tools/osc/test_wt.py --host host_osc"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="wtTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def P(o, key, v): return (L.pid(o, K[key]), v)
def X(o, j, v): return (12500 + 16 * o + j, v)
W3M, W3A, WMORPH, WTONE = range(4)
def render(cmds, note=60, hold=0.7, tail=0.2, tag="x", vel=100):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds:
            if isinstance(c, str): f.write(c + "\n")
            else: f.write("p %d %s\n" % (c[0], c[1]))
        f.write("run 0.1\non %d %d\nrun %s\noff %d\nrun %s\n" % (note, vel, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def seg(a, t0=0.3, t1=0.7): return a[int(t0 * RATE):int(t1 * RATE)]
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def spec(x):
    x = x.astype(np.float64); x = x - x.mean(); return np.fft.rfftfreq(len(x), 1.0 / RATE), np.abs(np.fft.rfft(x * np.hanning(len(x))))
def peak_freq(x): f, X_ = spec(x); return float(f[int(np.argmax(X_))])
def harm(x, h, f0=261.6256):
    f, X_ = spec(x); m = np.abs(f - f0 * h) < 20; return float(np.sqrt(np.sum(X_[m] ** 2)))
def centroid(x): f, X_ = spec(x); return float(np.sum(f * X_) / (np.sum(X_) + 1e-12))
BASE = [P(0, "level", 0.8), P(0, "fon", 0), P(0, "wsize", 3)]
def wt(cmds, load, **kw): return render([load] + BASE + list(cmds), **kw)

# ---- 256 frames
a = wt([P(0, "wpos", 200 / 255.0)], "wtx 0 256 harm", tag="f200")
check("256 frames: position 200/255 plays frame 200 (harmonic 9)", abs(peak_freq(seg(a)[:, 0]) - 261.6256 * 9) < 15, "%.0f Hz" % peak_freq(seg(a)[:, 0]))
a = wt([P(0, "wpos", 1.0)], "wtx 0 256 harm", tag="f255")
check("256 frames: last frame is frame 255 (harmonic 16)", abs(peak_freq(seg(a)[:, 0]) - 261.6256 * 16) < 20, "%.0f Hz" % peak_freq(seg(a)[:, 0]))
a = wt([P(0, "wpos", 0.0)], "wtx 0 256 harm", tag="f0")
check("256 frames: first frame is the fundamental", abs(peak_freq(seg(a)[:, 0]) - 261.6) < 8)
a = wt([P(0, "wpos", 1.0)], "wtx 0 128 harm", tag="f127")
check("128 frames still work (last frame = frame 127, harmonic 16)", abs(peak_freq(seg(a)[:, 0]) - 261.6256 * 16) < 20)

# ---- frame interpolation between frame 0 (h1) and frame 1 (h2): position 0.3 / 255
pos = 0.3 / 255.0
cf = wt([P(0, "wpos", pos), X(0, WMORPH, 0)], "wtx 0 256 harm", tag="mcf"); sm = wt([P(0, "wpos", pos), X(0, WMORPH, 1)], "wtx 0 256 harm", tag="msm"); st = wt([P(0, "wpos", pos), X(0, WMORPH, 2)], "wtx 0 256 harm", tag="mst")
check("Crossfade blends the two neighbouring frames", harm(seg(cf)[:, 0], 2) > 0.2 * harm(seg(cf)[:, 0], 1) and harm(seg(cf)[:, 0], 1) > 0)
check("Stepped plays the nearest frame only (no second harmonic)", harm(seg(st)[:, 0], 2) < 0.02 * harm(seg(st)[:, 0], 1))
check("Smooth (cubic) is finite and differs from Crossfade", np.isfinite(sm).all() and rms(seg(sm)) > 0.02 and np.abs(seg(sm) - seg(cf)).max() > 1e-4)
mid = wt([P(0, "wpos", 0.5 / 255.0), X(0, WMORPH, 1)], "wtx 0 256 harm", tag="mmid")
check("Smooth: halfway between two frames blends them", harm(seg(mid)[:, 0], 1) > 0.1 * harm(seg(mid)[:, 0], 2) and harm(seg(mid)[:, 0], 2) > 0)

# ---- warp modes
off = wt([], "wtx 0 1 saw", tag="woff")
for m, name in [(9, "Smear"), (10, "Ripple"), (11, "Stairs"), (12, "Fold Phase"), (13, "Clip"), (14, "Rectify"), (15, "Wrap"), (16, "Asym"), (17, "Drive")]:
    a = wt([P(0, "w1m", m), P(0, "w1a", 0.7)], "wtx 0 1 saw", tag="w%d" % m)
    check("Warp mode %d %s: finite, bounded, audible, differs from Off" % (m, name), np.isfinite(a).all() and np.abs(a).max() < 1.5 and rms(seg(a)) > 0.02 and np.abs(seg(a) - seg(off)).max() > 0.01, "rms %.3f" % rms(seg(a)))
w3 = wt([X(0, W3M, 13), X(0, W3A, 1.0)], "wtx 0 1 saw", tag="w3"); w3b = wt([X(0, W3M, 0), X(0, W3A, 1.0)], "wtx 0 1 saw", tag="w3b")
check("Warp 3 (Clip) changes the sound, Warp 3 Off does not", np.abs(seg(w3) - seg(off)).max() > 0.05 and np.abs(seg(w3b) - seg(off)).max() < 1e-4)
w2 = wt([P(0, "w1m", 3), P(0, "w1a", 0.5)], "wtx 0 1 saw", tag="w1only"); w12 = wt([P(0, "w1m", 3), P(0, "w1a", 0.5), X(0, W3M, 13), X(0, W3A, 1.0)], "wtx 0 1 saw", tag="w13")
check("three warp stages chain (Sync then Clip differs from Sync alone)", np.abs(seg(w12) - seg(w2)).max() > 0.02 and np.isfinite(w12).all())
# ---- tone
t1 = wt([], "wtx 0 1 saw", note=48, tag="t1"); t0 = wt([X(0, WTONE, 0.0)], "wtx 0 1 saw", note=48, tag="t0")
check("Tone 0 darkens the table", centroid(seg(t0)[:, 0]) < 0.6 * centroid(seg(t1)[:, 0]) and rms(seg(t0)) > 0.01, "%.0f vs %.0f Hz" % (centroid(seg(t0)[:, 0]), centroid(seg(t1)[:, 0])))
print("ALL OK" if not failures else "FAILED %d" % failures); sys.exit(1 if failures else 0)
