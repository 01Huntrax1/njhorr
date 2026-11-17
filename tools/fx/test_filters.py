#!/usr/bin/env python3
"""Audio tests of the new Filter effect types 33..45 (FX-FILTERS).
python3 tools/fx/test_filters.py --host <dsp_host of patch_fx, built with -DDSP_FX>"""
import argparse, os, subprocess, tempfile, sys, math
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="filtTest"); RATE = 48000; failures = 0
NAMES = {33: "Polivoks LP", 34: "Polivoks BP", 35: "Polivoks HP", 36: "OTA LP24", 37: "CEM LP24", 38: "SSM LP24", 39: "SEM LP", 40: "SEM BP", 41: "SEM Notch", 42: "SEM HP", 43: "Diode LP", 44: "Steiner LP", 45: "Steiner HP"}
KIND = {33: "lp", 34: "bp", 35: "hp", 36: "lp", 37: "lp", 38: "lp", 39: "lp", 40: "bp", 41: "notch", 42: "hp", 43: "lp", 44: "lp", 45: "hp"}
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def kn(hz): return math.log(hz / 20.0) / math.log(1000.0)
def run(mode, fc=1000.0, res=0.3, drive=0.0, src="noise 0.3 220", secs=1.5, tag="x"):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    cmds = ["in " + src, "p 541 9", "p 542 1", "p 543 1", "p 544 %d" % mode, "p 545 %s" % kn(fc), "p 546 %s" % res, "p 547 %s" % drive, "p 548 0.5", "p 549 0", "p 550 0"]
    with open(script, "w") as f:
        for c in cmds: f.write(c + "\n")
        f.write("run %s\n" % secs)
    subprocess.run([args.host, script, out], check=True, capture_output=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def band(a, lo, hi):
    x = a[int(0.5 * RATE):, 0].astype(np.float64)
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.mean(sp[(f > lo) & (f < hi)])) + 1e-30
db = lambda a, b: 10 * math.log10(a / b)
res_ = {}
for m in range(33, 46):
    a = run(m, tag="m%d" % m); res_[m] = a; nm = NAMES[m]; k = KIND[m]
    lo, mid, hi = band(a, 80, 250), band(a, 800, 1250), band(a, 5000, 12000)
    check("%s: finite and bounded" % nm, np.isfinite(a).all() and np.abs(a).max() < 8.0, "peak %.2f" % np.abs(a).max())
    check("%s: sounds (rms > 0.005)" % nm, float(np.sqrt(np.mean(a[int(0.5 * RATE):, 0] ** 2))) > 0.005)
    if k == "lp": check("%s: low-pass (lows > highs by 12 dB)" % nm, db(lo, hi) > 12, "%.1f dB" % db(lo, hi))
    if k == "hp": check("%s: high-pass (highs > lows by 12 dB)" % nm, db(hi, lo) > 12, "%.1f dB" % db(hi, lo))
    if k == "bp": check("%s: band-pass (middle above lows and highs)" % nm, mid > lo and mid > hi, "%.1f/%.1f dB" % (db(mid, lo), db(mid, hi)))
    if k == "notch":
        side = (band(a, 200, 500) + band(a, 2200, 4500)) / 2
        check("%s: notch (centre quieter than the sides)" % nm, db(side, mid) > 3, "%.1f dB" % db(side, mid))
# resonance and cutoff behaviour
for m in (33, 36, 37, 38, 39, 43, 44):
    lo_r = band(run(m, res=0.1, tag="r0"), 800, 1250); hi_r = band(run(m, res=0.85, tag="r1"), 800, 1250)
    check("%s: resonance raises the level at the cutoff" % NAMES[m], hi_r > 2 * lo_r, "%.1f dB" % db(hi_r, lo_r))
a24 = [m for m in (36, 37, 38)]; a12 = [33, 39, 44]
for m in a24: check("%s: 24 dB steeper than a 12 dB filter (%s)" % (NAMES[m], NAMES[39]), db(band(res_[m], 800, 1250), band(res_[m], 5000, 12000)) > db(band(res_[39], 800, 1250), band(res_[39], 5000, 12000)) + 3)
# stability: full resonance, loud saw, fast cutoff changes
for m in range(33, 46):
    for fc in (60.0, 1000.0, 12000.0):
        a = run(m, fc=fc, res=1.0, drive=1.0, src="saw 0.9 110", secs=0.6, tag="s")
        if not (np.isfinite(a).all() and np.abs(a).max() < 40.0): check("%s fc=%d res=1 drive=1 stable" % (NAMES[m], fc), False, "peak %.1f" % np.nanmax(np.abs(a))); break
    else: check("%s: stable at full resonance and drive" % NAMES[m], True)
check("cutoff tracks: higher cutoff passes more highs (Polivoks LP)", band(run(33, fc=4000.0, tag="c"), 3000, 8000) > 5 * band(res_[33], 3000, 8000))
print("%d failures" % failures); sys.exit(1 if failures else 0)
