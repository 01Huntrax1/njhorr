#!/usr/bin/env python3
"""Audio tests of the Shaper Table distortion (FX type 34).   python3 tools/fx/test_shtab.py --host <dsp_host of patch_fx, built with -DDSP_FX>"""
import argparse, os, subprocess, tempfile, sys, math
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="shTest"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def kn(hz, lo, hi): return math.log(hz / lo) / math.log(hi / lo)
def run(mode=0, drive_db=0.0, pos=0.0, table=0, bias=0.5, tone=1.0, level=0.667, src="sine 0.3 1000", secs=1.0, tag="x"):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    p = [drive_db / 36.0, pos, table / 5.0, bias, tone, level]
    cmds = ["in " + src, "p 541 34", "p 542 1", "p 543 1", "p 544 %d" % mode] + ["p %d %s" % (545 + i, v) for i, v in enumerate(p)]
    with open(script, "w") as f:
        for c in cmds: f.write(c + "\n")
        f.write("run %s\n" % secs)
    subprocess.run([args.host, script, out], check=True, capture_output=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def band(a, lo, hi):
    x = a[int(0.3 * RATE):, 0].astype(np.float64)
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.sum(sp[(f > lo) & (f < hi)])) + 1e-30
rms = lambda a: float(np.sqrt(np.mean(a[int(0.3 * RATE):, 0] ** 2)))
for m, nm in enumerate(["Clip", "Fold", "Wrap", "Rect"]):
    a = run(m, 24.0, 0.3, tag="m%d" % m)
    check("%s: finite, bounded, sounds" % nm, np.isfinite(a).all() and np.abs(a).max() < 4.0 and rms(a) > 0.01, "peak %.2f rms %.3f" % (np.abs(a).max(), rms(a)))
lo = run(0, 0.0, 0.0, tag="d0"); hi = run(0, 30.0, 0.0, tag="d1")
check("Drive adds harmonics (3 kHz)", band(hi, 2900, 3100) > 3 * band(lo, 2900, 3100), "%.1f dB" % (10 * math.log10(band(hi, 2900, 3100) / band(lo, 2900, 3100))))
p0 = run(0, 18.0, 0.0, tag="p0"); p1 = run(0, 18.0, 0.5, tag="p1"); p2 = run(0, 18.0, 1.0, tag="p2")
d01 = np.sqrt(np.mean((p0[10000:, 0] - p1[10000:, 0]) ** 2)); d12 = np.sqrt(np.mean((p1[10000:, 0] - p2[10000:, 0]) ** 2))
check("Pos changes the curve (frames differ)", d01 > 0.01 and d12 > 0.01, "%.3f %.3f" % (d01, d12))
modes = [run(m, 12.0, 0.45, bias=0.65, src="sine 0.5 1000", tag="mm%d" % m) for m in range(4)]
check("the four modes sound different", all(np.sqrt(np.mean((modes[i][10000:, 0] - modes[j][10000:, 0]) ** 2)) > 0.01 for i in range(4) for j in range(i + 1, 4)))
lv0 = run(0, 6.0, 0.0, level=0.0, tag="l0"); lv1 = run(0, 6.0, 0.0, level=1.0, tag="l1")
check("Level spans -24 dB .. +12 dB", 20 * math.log10(rms(lv1) / rms(lv0)) > 30, "%.1f dB" % (20 * math.log10(rms(lv1) / rms(lv0))))
tn = run(0, 30.0, 0.0, tone=0.0, tag="t0")
check("Tone low-passes (6 kHz band lower)", band(tn, 5000, 12000) < 0.3 * band(hi, 5000, 12000))
sil = run(0, 24.0, 0.0, bias=1.0, src="sine 0.0 1000", secs=1.5, tag="sil")
check("bias DC is removed (silence ends at zero)", float(np.abs(sil[-2000:, 0]).max()) < 0.01, "%.4f" % float(np.abs(sil[-2000:, 0]).max()))
print("%d failures" % failures); sys.exit(1 if failures else 0)
