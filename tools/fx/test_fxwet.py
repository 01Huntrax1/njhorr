#!/usr/bin/env python3
"""Audio tests of the wet post processing P7..P10 (Low Cut, High Cut, Width, Sat) of every effect slot (FX-WET).
python3 tools/fx/test_fxwet.py --host <dsp_host of patch_fx, built with -DDSP_FX>"""
import argparse, os, subprocess, tempfile, sys
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="wetTest"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def run(ty, extra=(), src="noise 0.3 220", secs=1.5, slot=0, tag="x"):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    b = 541 + 10 * slot
    cmds = ["in " + src, "p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d 1" % (b + 2), "p %d 0" % (b + 3)] + ["p %d %s" % (11000 + 4 * slot + k, v) for k, v in extra]
    with open(script, "w") as f:
        for c in cmds: f.write(c + "\n")
        f.write("run %s\n" % secs)
    subprocess.run([args.host, script, out], check=True, capture_output=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def band(a, lo, hi, ch=0):
    x = a[int(0.5 * RATE):, ch].astype(np.float64)
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.mean(sp[(f > lo) & (f < hi)])) + 1e-30
db = lambda a, b: 10 * np.log10(a / b)
base = run(14, tag="base")
check("defaults leave the effect unchanged", np.allclose(base, run(14, [(0, 0), (1, 1), (2, 0.5), (3, 0)], tag="def"), atol=1e-6))
lc = run(14, [(0, 1.0)], tag="lc")
check("Low Cut removes the lows", db(band(base, 30, 100), band(lc, 30, 100)) > 15, "%.1f dB" % db(band(base, 30, 100), band(lc, 30, 100)))
check("Low Cut keeps the highs", abs(db(band(base, 4000, 9000), band(lc, 4000, 9000))) < 1.0)
hc = run(14, [(1, 0.0)], tag="hc")
check("High Cut removes the highs", db(band(base, 6000, 12000), band(hc, 6000, 12000)) > 20, "%.1f dB" % db(band(base, 6000, 12000), band(hc, 6000, 12000)))
check("High Cut keeps the lows", abs(db(band(base, 80, 300), band(hc, 80, 300))) < 1.0)
rv = run(8, tag="rv"); rv0 = run(8, [(2, 0.0)], tag="rv0"); rv1 = run(8, [(2, 1.0)], tag="rv1")
side = lambda a: float(np.sqrt(np.mean((a[int(0.5 * RATE):, 0] - a[int(0.5 * RATE):, 1]) ** 2)))
check("Reverb is stereo", side(rv) > 1e-3, "%.4f" % side(rv))
check("Width 0 gives mono", side(rv0) < 1e-6, "%.2g" % side(rv0))
check("Width 1 doubles the side signal", 1.8 < side(rv1) / side(rv) < 2.2, "%.2f" % (side(rv1) / side(rv)))
sine = run(14, src="sine 0.4 1000", tag="s0"); sat = run(14, [(3, 1.0)], src="sine 0.4 1000", tag="s1")
check("Sat adds harmonics (3 kHz band)", db(band(sat, 2900, 3100), band(sine, 2900, 3100)) > 6, "%.1f dB" % db(band(sat, 2900, 3100), band(sine, 2900, 3100)))
o3 = run(14, [(0, 1.0)], slot=3, tag="o3"); check("slot 3 has its own parameters (Low Cut works)", db(band(base, 30, 100), band(o3, 30, 100)) > 15)
print("%d failures" % failures); sys.exit(1 if failures else 0)
