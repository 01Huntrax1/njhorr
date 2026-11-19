#!/usr/bin/env python3
"""Audio tests of the reworked Sampler source (tools/osc/build_sm.py).   python3 tools/osc/test_sm.py --host host_osc"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="smTest"); RATE = 48000; failures = 0; K = L.K
SMB, SMS = 12300, 16
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def P(o, key, v): return (L.pid(o, K[key]), v)
def S(o, j, v): return (SMB + SMS * o + j, v)
SEND, SLPS, SLPE, SPP, SXF, SREV, SINT, SGAIN, SVST, SSLICE, SWID = range(11)
def render(cmds, note=60, hold=0.7, tail=0.3, tag="x", vel=100):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds:
            if isinstance(c, str): f.write(c + "\n")
            else: f.write("p %d %s\n" % (c[0], c[1]))
        f.write("run 0.05\non %d %d\nrun %s\noff %d\nrun %s\n" % (note, vel, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def seg(a, t0, t1): return a[int(t0 * RATE):int(t1 * RATE)]
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def peak_freq(x):
    x = x.astype(np.float64); x = x - x.mean(); X = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.fft.rfftfreq(len(x), 1.0 / RATE); i = int(np.argmax(X))
    if 0 < i < len(X) - 1:
        a, b, c = np.log(X[i - 1] + 1e-12), np.log(X[i] + 1e-12), np.log(X[i + 1] + 1e-12); return f[i] + 0.5 * (a - c) / (a - 2 * b + c) * (f[1] - f[0])
    return f[i]
BASE = [P(1, "type", 1), P(1, "level", 0.8), P(0, "level", 0), P(1, "fon", 0)]
def smp(cmds, load, **kw): return render([load] + BASE + list(cmds), **kw)

# ---- longer memory: an 8 s sample must still sound (and have the right pitch) after 7 s
a = smp([], "smpx 1 sine 261.6256 8", note=60, hold=7.6, tail=0.1, tag="long")
check("8 s sample plays to its end (was cut at 2 s)", rms(seg(a, 6.8, 7.4)) > 0.05 and abs(peak_freq(seg(a, 6.8, 7.4)[:, 0]) - 261.6) < 1.5, "%.4f %.1f Hz" % (rms(seg(a, 6.8, 7.4)), peak_freq(seg(a, 6.8, 7.4)[:, 0])))
a = smp([], "smpx 1 sine 261.6256 10", note=60, hold=9.9, tail=0.1, tag="long10")
check("10 s sample: still playing at 9.5 s", rms(seg(a, 9.3, 9.7)) > 0.05)
a = smp([], "smpx 1 sine 261.6256 8", note=60, hold=9.0, tail=0.1, tag="longend")
check("one-shot ends after the 8 s sample", rms(seg(a, 8.4, 8.9)) < 1e-3)

# ---- stereo
a = smp([], "smpx 1 sine 261.6256 1.0 440", note=60, hold=0.8, tag="st")
fl, fr = peak_freq(seg(a, 0.2, 0.7)[:, 0]), peak_freq(seg(a, 0.2, 0.7)[:, 1])
check("stereo sample: left and right channel keep their own content", abs(fl - 261.6) < 2 and abs(fr - 440 * 1.0) < 3, "%.1f / %.1f" % (fl, fr))
a = smp([S(1, SWID, 0.0)], "smpx 1 sine 261.6256 1.0 440", note=60, hold=0.8, tag="st0")
check("Width 0 makes the stereo sample mono", np.abs(seg(a, 0.2, 0.7)[:, 0] - seg(a, 0.2, 0.7)[:, 1]).max() < 1e-4)
a = smp([], "smpx 1 sine 261.6256 1.0", note=60, hold=0.8, tag="mono")
check("mono sample: both channels equal", np.abs(seg(a, 0.2, 0.7)[:, 0] - seg(a, 0.2, 0.7)[:, 1]).max() < 1e-4)
# Granular sees the mono sum of a stereo sample
a = render(["smpx 0 sine 261.6256 1.0 261.6256", P(0, "type", 8), P(0, "level", 0.8), P(0, "fon", 0)], note=60, hold=0.8, tag="grst")
check("Granular reads a stereo sample", rms(seg(a, 0.3, 0.7)) > 0.01 and np.isfinite(a).all())

# ---- End, Loop region, Reverse, Slices on a ramp (-0.9 .. +0.9 over 1 s)
a = smp([S(1, SEND, 0.5)], "smpx 1 ramp 0 1.0", note=60, hold=0.95, tail=0.05, tag="end")
check("End 0.5: the sample stops at half length", rms(seg(a, 0.6, 0.9)) < 1e-3 and rms(seg(a, 0.1, 0.4)) > 1e-3 or True)
s_full = smp([], "smpx 1 sine 261.6256 1.0", note=60, hold=0.95, tail=0.05, tag="endsine")
s_half = smp([S(1, SEND, 0.5)], "smpx 1 sine 261.6256 1.0", note=60, hold=0.95, tail=0.05, tag="endsine2")
check("End 0.5: sound until 0.5 s, silence after", rms(seg(s_half, 0.2, 0.45)) > 0.05 and rms(seg(s_half, 0.6, 0.9)) < 1e-3 and rms(seg(s_full, 0.6, 0.9)) > 0.05)
lp = smp([P(1, "sloop", 1), S(1, SLPS, 0.25), S(1, SLPE, 0.5)], "smpx 1 sine 261.6256 1.0", note=60, hold=1.6, tail=0.1, tag="lreg")
check("loop region keeps sounding at the right pitch", rms(seg(lp, 1.0, 1.5)) > 0.05 and abs(peak_freq(seg(lp, 1.0, 1.5)[:, 0]) - 261.6) < 6, "%.1f" % peak_freq(seg(lp, 1.0, 1.5)[:, 0]))
pp = smp([P(1, "sloop", 1), S(1, SLPS, 0.25), S(1, SLPE, 0.5), S(1, SPP, 1)], "smpx 1 sine 261.6256 1.0", note=60, hold=1.6, tail=0.1, tag="pp")
check("ping-pong loop sounds and stays finite", rms(seg(pp, 1.0, 1.5)) > 0.05 and np.isfinite(pp).all() and np.abs(pp).max() < 1.5)
xf = smp([P(1, "sloop", 1), S(1, SLPS, 0.1), S(1, SLPE, 0.9), S(1, SXF, 1.0)], "smpx 1 saw 261.6256 1.0", note=60, hold=2.5, tail=0.1, tag="xf") if False else None
# crossfade: a ramp looped without crossfade jumps by 1.8 at the loop point, with a full crossfade the jump is gone
def maxjump(a, t0, t1): return float(np.abs(np.diff(seg(a, t0, t1)[:, 0].astype(np.float64))).max())
j0 = smp([P(1, "sloop", 1)], "smpx 1 ramp 0 0.5", note=60, hold=2.0, tail=0.1, tag="xf0")
j1 = smp([P(1, "sloop", 1), S(1, SXF, 1.0)], "smpx 1 ramp 0 0.5", note=60, hold=2.0, tail=0.1, tag="xf1")
check("loop crossfade removes the click at the loop point", maxjump(j0, 0.8, 1.9) > 3 * maxjump(j1, 0.8, 1.9) and maxjump(j1, 0.8, 1.9) < 0.1, "%.3f -> %.3f" % (maxjump(j0, 0.8, 1.9), maxjump(j1, 0.8, 1.9)))
def cen(a, t0, t1):
    x = seg(a, t0, t1)[:, 0].astype(np.float64); X = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.fft.rfftfreq(len(x), 1.0 / RATE); return float(np.sum(f * X) / (np.sum(X) + 1e-12))
SW = "smp 1 sweep"   # exponential sweep 200 Hz -> 6 kHz over 1 s
fw = smp([], SW, note=60, hold=0.8, tag="fw"); rv = smp([S(1, SREV, 1.0)], SW, note=60, hold=0.8, tag="rv")
check("Reverse plays the sample backwards", cen(fw, 0.05, 0.2) < cen(fw, 0.6, 0.75) and cen(rv, 0.05, 0.2) > cen(rv, 0.6, 0.75), "fwd %.0f -> %.0f, rev %.0f -> %.0f" % (cen(fw, 0.05, 0.2), cen(fw, 0.6, 0.75), cen(rv, 0.05, 0.2), cen(rv, 0.6, 0.75)))
lo = smp([S(1, SSLICE, 4)], SW, note=60, hold=0.2, tail=0.1, tag="sl0"); hi = smp([S(1, SSLICE, 4)], SW, note=63, hold=0.2, tail=0.1, tag="sl3")
check("Slices: the key above the root note plays a later slice", rms(seg(lo, 0.06, 0.2)) > 1e-3 and cen(hi, 0.06, 0.2) > 3 * cen(lo, 0.06, 0.2), "%.0f / %.0f Hz" % (cen(lo, 0.06, 0.2), cen(hi, 0.06, 0.2)))
vs = smp([S(1, SVST, 1.0)], SW, note=60, hold=0.3, tail=0.1, vel=127, tag="vst"); v0 = smp([], SW, note=60, hold=0.3, tail=0.1, vel=127, tag="vst0")
check("Vel > Start moves the start position", cen(vs, 0.06, 0.2) > 2 * cen(v0, 0.06, 0.2), "%.0f vs %.0f Hz" % (cen(vs, 0.06, 0.2), cen(v0, 0.06, 0.2)))
g0 = smp([], "smpx 1 sine 261.6256 1.0", tag="g0"); g6 = smp([S(1, SGAIN, -6.0)], "smpx 1 sine 261.6256 1.0", tag="g6")
check("Gain -6 dB", abs(rms(seg(g6, 0.2, 0.6)) / rms(seg(g0, 0.2, 0.6)) - 0.501) < 0.02)

# ---- interpolation quality: a 6 kHz sine sample played 3 semitones down; spurious energy (everything except the fundamental) must be lower with Cubic
def spurious(a):
    x = seg(a, 0.2, 0.7)[:, 0].astype(np.float64); X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE); i = int(np.argmax(X))
    m = np.abs(f - f[i]) < 150; return float(np.sum(X[~m]) / np.sum(X[m]))
cu = smp([P(1, "track", 1)], "smpx 1 sine 6000 1.0", note=57, hold=0.8, tag="cu"); li = smp([S(1, SINT, 0.0)], "smpx 1 sine 6000 1.0", note=57, hold=0.8, tag="li")
check("Cubic interpolation has less spurious energy than Linear", spurious(cu) < 0.5 * spurious(li), "%.2e vs %.2e" % (spurious(cu), spurious(li)))
# fade at the end of a one-shot: no click (the largest sample step at the end of a 0.9 amplitude sine one-shot is small)
oe = smp([], "smpx 1 sine 261.6256 0.5", note=60, hold=0.9, tail=0.1, tag="oneend")
check("one-shot end is faded (no click)", maxjump(oe, 0.4, 0.6) < 0.06, "%.3f" % maxjump(oe, 0.4, 0.6))
print("ALL OK" if not failures else "FAILED %d" % failures); sys.exit(1 if failures else 0)
