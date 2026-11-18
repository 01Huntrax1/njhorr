#!/usr/bin/env python3
"""Audio tests of the Yaybahar elements as effects (types 35 Yb Spring, 36 Yb Drum, 37 Yb String).
python3 tools/fx/test_ybparts.py --host <dsp_host of patch_fx, built with -DDSP_FX>"""
import argparse, os, subprocess, tempfile, sys, math
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="ybpTest"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def kn(v, lo, hi): return math.log(v / lo) / math.log(hi / lo)
imp = np.zeros((RATE * 4, 2), np.float32); imp[int(0.1 * RATE)] = 0.8; IMP = os.path.join(TMP, "imp.f32"); imp.tofile(IMP)
def run(ty, mode, p, src="noise 0.3 220", secs=2.0, tag="x"):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    cmds = [("inf " + IMP) if src == "imp" else ("in " + src), "p 541 %d" % ty, "p 542 1", "p 543 1", "p 544 %d" % mode] + ["p %d %s" % (545 + i, v) for i, v in enumerate(p)]
    open(script, "w").write("\n".join(cmds) + "\nrun %s\n" % secs); subprocess.run([args.host, script, out], check=True, capture_output=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def band(a, lo, hi, ch=0, t0=0.3):
    x = a[int(t0 * RATE):, ch].astype(np.float64)
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.sum(sp[(f > lo) & (f < hi)])) + 1e-30
db = lambda a, b: 10 * np.log10(a / b)
rmsw = lambda a, t0, t1: float(np.sqrt(np.mean(a[int(t0 * RATE):int(t1 * RATE), 0] ** 2)))
# ---- spring
for m, nm in enumerate(["Single", "Dual", "Stereo"]):
    a = run(35, m, (0.5, 0.7, 0.5, 0.6, 0.3, 0.5), tag="s%d" % m)
    check("Spring %s: finite, bounded, sounds" % nm, np.isfinite(a).all() and np.abs(a).max() <= 1.0 and rmsw(a, 0.5, 2.0) > 0.01, "peak %.2f" % np.abs(a).max())
check("Spring Stereo: the two springs differ", np.abs(run(35, 2, (0.5, 0.7, 0.5, 0.6, 0.3, 0.5), tag="ss")[24000:, 0] - run(35, 2, (0.5, 0.7, 0.5, 0.6, 0.3, 0.5), tag="ss")[24000:, 1]).max() > 0.01)
L = 0.1; e = run(35, 0, (kn(100, 20, 250), 0.6, 0.0, 1.0, 0.0, 0.5), src="imp", secs=1.0, tag="e"); env = np.abs(e[:, 0])
first = int(0.1 * RATE); win = env[first + int(0.05 * RATE):first + int(0.16 * RATE)]
check("Spring: the impulse comes back after the spring length (100 ms)", abs((int(np.argmax(win)) + int(0.05 * RATE)) / RATE - 0.1) < 0.012, "%.1f ms" % ((int(np.argmax(win)) + int(0.05 * RATE)) / RATE * 1000))
d0 = run(35, 0, (0.5, 0.0, 0.5, 0.6, 0.0, 0.5), src="imp", secs=3.0, tag="d0"); d1 = run(35, 0, (0.5, 1.0, 0.5, 0.6, 0.0, 0.5), src="imp", secs=3.0, tag="d1")
check("Spring: Decay lengthens the tail", rmsw(d1, 1.0, 2.0) > 4 * rmsw(d0, 1.0, 2.0), "%.5f vs %.5f" % (rmsw(d1, 1.0, 2.0), rmsw(d0, 1.0, 2.0)))
disp0 = run(35, 0, (0.5, 0.7, 0.0, 1.0, 0.0, 0.5), src="imp", secs=1.0, tag="di0"); disp1 = run(35, 0, (0.5, 0.7, 1.0, 1.0, 0.0, 0.5), src="imp", secs=1.0, tag="di1")
check("Spring: Disper changes the echo", np.abs(disp0[:, 0] - disp1[:, 0]).max() > 0.02)
# ---- drum
for m, nm in enumerate(["Rect", "Two Drums", "Stereo", "Rect Key", "Two Drums Key", "Stereo Key"]):
    a = run(36, m, (0.5, 0.5, 0.52, 0.83, 0.63, 0.3), tag="dr%d" % m)
    check("Drum %s: finite, bounded, sounds" % nm, np.isfinite(a).all() and np.abs(a).max() <= 1.0 and rmsw(a, 0.5, 2.0) > 0.005, "peak %.2f rms %.3f" % (np.abs(a).max(), rmsw(a, 0.5, 2.0)))
a = run(36, 0, (kn(110, 40, 250), 0.5, 0.52, 0.83, 0.63, 0.3), tag="dt")
check("Drum: the fundamental sits at Tune (110 Hz)", band(a, 100, 120) > 3 * band(a, 125, 140) and band(a, 100, 120) > 3 * band(a, 85, 98), "%.1f dB" % db(band(a, 100, 120), band(a, 125, 140)))
b = run(36, 0, (kn(110, 40, 250), 0.5, 1.0, 0.83, 0.63, 0.3), tag="dasp")
check("Drum: Aspect moves the overtones", abs(db(band(a, 150, 200), band(b, 150, 200))) > 1.5 or np.abs(a[24000:, 0] - b[24000:, 0]).max() > 0.01)
r0 = run(36, 0, (0.5, 0.0, 0.52, 0.83, 0.63, 0.3), src="imp", secs=3.0, tag="r0"); r1 = run(36, 0, (0.5, 1.0, 0.52, 0.83, 0.63, 0.3), src="imp", secs=3.0, tag="r1")
check("Drum: Decay lengthens the ring", rmsw(r1, 1.0, 2.0) > 3 * rmsw(r0, 1.0, 2.0), "%.5f vs %.5f" % (rmsw(r1, 1.0, 2.0), rmsw(r0, 1.0, 2.0)))
# ---- string
for m, nm in enumerate(["Mono", "Stereo", "Octave", "Mono Key", "Stereo Key", "Octave Key"]):
    a = run(37, m, (0.4, 0.6, 0.5, 0.4, 0.5, 0.5), tag="st%d" % m)
    check("String %s: finite, bounded, sounds" % nm, np.isfinite(a).all() and np.abs(a).max() <= 1.0 and rmsw(a, 0.5, 2.0) > 0.01, "peak %.2f rms %.3f" % (np.abs(a).max(), rmsw(a, 0.5, 2.0)))
f0 = 40.0 * 20.0 ** 0.4
a = run(37, 0, (0.4, 0.6, 0.5, 0.4, 0.5, 0.5), tag="sp")
check("String: resonates at the pitch and its harmonics", band(a, f0 * 0.97, f0 * 1.03) > 8 * band(a, f0 * 1.45, f0 * 1.55), "f0 %.0f Hz, %.1f dB" % (f0, db(band(a, f0 * 0.97, f0 * 1.03), band(a, f0 * 1.45, f0 * 1.55))))
check("String: 2nd harmonic is there", band(a, f0 * 1.95, f0 * 2.05) > 4 * band(a, f0 * 1.45, f0 * 1.55))
s0 = run(37, 0, (0.4, 0.0, 0.5, 0.4, 0.5, 0.5), src="imp", secs=3.0, tag="sd0"); s1 = run(37, 0, (0.4, 1.0, 0.5, 0.4, 0.5, 0.5), src="imp", secs=3.0, tag="sd1")
check("String: Decay lengthens the ring", rmsw(s1, 1.0, 2.0) > 3 * rmsw(s0, 1.0, 2.0), "%.5f vs %.5f" % (rmsw(s1, 1.0, 2.0), rmsw(s0, 1.0, 2.0)))
oc = run(37, 2, (0.4, 0.6, 0.5, 0.4, 0.5, 0.5), tag="oc")
check("String Octave: energy an octave below", band(oc, f0 * 0.485, f0 * 0.515) > 4 * band(a, f0 * 0.485, f0 * 0.515))
print("%d failures" % failures); sys.exit(1 if failures else 0)
