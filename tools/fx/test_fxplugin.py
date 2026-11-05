#!/usr/bin/env python3
"""Tests of the effects-only plugin DSP (patch_fx).   python3 tools/fx/test_fxplugin.py --host dsp_host_fx   (dsp_host built with -DDSP_FX from the generated patch_fx class)"""
import argparse, os, subprocess, tempfile, sys
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="fxpTest"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def base(slot): return 541 + 10 * slot + (10 if slot >= 10 else 0) + (10 if slot >= 20 else 0)   # Main rack slot, 10 per rack (+ 10 id gap)
def fx(slot, ty, mode=0, mix=1.0, p=(0.5,) * 6):
    b = base(slot)
    return ["p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d %s" % (b + 2, mix), "p %d %d" % (b + 3, mode)] + ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
def run(cmds, kind="sine", amp=0.5, freq=440.0, secs=1.0, tag="x", midi=False):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    lines = list(cmds) + ["in %s %s %s" % (kind, amp, freq), "run 0.05"]
    if midi: lines += ["on 60 100"]
    lines += ["run %s" % secs]
    open(script, "w").write("\n".join(lines) + "\n")
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def tail(a): return a[int(0.3 * RATE):]
def band(a, f0, f1):
    x = tail(a)[:, 0].astype(np.float64); X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.sqrt(X[(f >= f0) & (f < f1)].sum() / len(x)))

d = run([], tag="dry")
check("empty racks: the input passes with unity gain (stereo identical)", abs(rms(tail(d)) / (0.5 / np.sqrt(2)) - 1) < 0.03 and np.allclose(d[:, 0], d[:, 1], atol=1e-6), "rms %.4f vs %.4f" % (rms(tail(d)), 0.5 / np.sqrt(2)))
s = run([], kind="off", tag="sil")
check("silent input gives silence", float(np.abs(s).max()) < 1e-4)
m = run([], kind="off", tag="midi", midi=True)
check("MIDI notes do not play the synth (it is an effect)", float(np.abs(m).max()) < 1e-4)
h = run([], amp=1.5, tag="hot")
check("a hot input is not clipped at 0 dBFS", float(np.abs(tail(h)).max()) > 1.3, "peak %.3f" % float(np.abs(tail(h)).max()))
sw = run([], kind="saw", amp=0.4, freq=110.0, tag="saw")
lp = run(fx(0, 9, 1, 1.0, (0.4, 0.2, 0.0, 0.5, 0.0, 0.0)), kind="saw", amp=0.4, freq=110.0, tag="lp")
check("Main rack: a low-pass filter effect removes the highs of the input", band(lp, 3000, 20000) < 0.2 * band(sw, 3000, 20000), "%.4f vs %.4f" % (band(lp, 3000, 20000), band(sw, 3000, 20000)))
di = run(fx(0, 1, 0, 1.0, (0.9, 1.0, 0.5, 0.5, 0.0, 0.0)), kind="sine", amp=0.4, tag="dist")
check("Main rack: distortion adds harmonics", band(di, 1000, 8000) > 5 * band(d, 1000, 8000) + 1e-6)
b1 = run([] + ["p %d 9" % base(10), "p %d 1" % (base(10) + 1), "p %d 1.0" % (base(10) + 2), "p %d 1" % (base(10) + 3)] + ["p %d %s" % (base(10) + 4 + i, v) for i, v in enumerate((0.3, 0.1, 0.0, 0.5, 0.0, 0.0))], kind="saw", amp=0.4, freq=110.0, tag="b1off")
check("Bus 1 rack is silent at its default return level 0", abs(rms(tail(b1)) / rms(tail(sw)) - 1) < 0.03, "%.4f vs %.4f" % (rms(tail(b1)), rms(tail(sw))))
b2 = run(["p 880 1.0"] + ["p %d 9" % base(10), "p %d 1" % (base(10) + 1), "p %d 1.0" % (base(10) + 2), "p %d 1" % (base(10) + 3)] + ["p %d %s" % (base(10) + 4 + i, v) for i, v in enumerate((0.3, 0.1, 0.0, 0.5, 0.0, 0.0))], kind="saw", amp=0.4, freq=110.0, tag="b1on")
check("Bus 1 rack runs in parallel once its return is up (Main = input + filtered copy: the lows add up, the highs stay)", rms(tail(b2)) > 1.15 * rms(tail(sw)) and abs(band(b2, 3000, 20000) / band(sw, 3000, 20000) - 1) < 0.1, "rms %.3f vs %.3f, highs %.4f vs %.4f" % (rms(tail(b2)), rms(tail(sw)), band(b2, 3000, 20000), band(sw, 3000, 20000)))
nz = run(fx(0, 8, 0, 0.5), kind="noise", amp=0.3, tag="rvb")
check("Reverb in the Main rack stays finite and bounded", bool(np.isfinite(nz).all()) and float(np.abs(nz).max()) < 4.0)
print("ALL OK" if not failures else "FAILURES: %d" % failures); sys.exit(1 if failures else 0)
