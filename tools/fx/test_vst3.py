#!/usr/bin/env python3
"""DSP tests of the VST3 host streams (source type 13, FX type 19).   python3 tools/fx/test_vst3.py --host dsp_host_vst
dsp_host_vst is built with -DDSP_VST: it models the plugin wrapper (64-sample chunks, hosted effect = a gain that answers one chunk late)."""
import argparse, os, subprocess, tempfile, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="vstTest"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def render(cmds, tag, note=True):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write(c + "\n")
        f.write("run 0.4\n")
        if note: f.write("on 69 110\n")
        f.write("run 0.5\n")
        if note: f.write("off 69\n")
        f.write("run 0.5\n")
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
W = lambda a, t0, t1: a[int(t0 * RATE):int(t1 * RATE)]
SRC = ["p 1000 13", "p %d 0" % L.pid(0, L.K["fon"])]          # OSC 1: source VST3, filter off

# --- source ---
a = render(SRC + ["hsrc sine 0.5 220"], "src")
check("VST3 source: hosted audio plays while a key is held", rms(W(a, 0.5, 0.85)) > 0.02, "%.4f" % rms(W(a, 0.5, 0.85)))
b = render(SRC, "src0")
check("VST3 source: silent without hosted audio", rms(b) < 1e-4, "%.6f" % rms(b))
c = render(SRC + ["hsrc sine 0.5 220"], "srcnote", note=False)
check("VST3 source: silent without a note (no voice)", rms(c) < 1e-4, "%.6f" % rms(c))
lv = render(SRC + ["hsrc sine 0.5 220", "p 1001 0.5"], "srclv")
check("VST3 source: slot Level scales it", 0.3 < rms(W(lv, 0.5, 0.85)) / rms(W(a, 0.5, 0.85)) < 0.7, "%.3f" % (rms(W(lv, 0.5, 0.85)) / rms(W(a, 0.5, 0.85))))

# --- FX ---
def fxs(ty, mix):
    return ["p 541 %d" % ty, "p 542 1", "p 543 %s" % mix]
WT = ["wt 0 sine", "p %d 0" % L.pid(0, L.K["fon"])]
dry = render(WT, "dry")
f1 = render(WT + fxs(19, 1.0) + ["hfx 1.0 1"], "fx1")
f5 = render(WT + fxs(19, 1.0) + ["hfx 0.5 1"], "fx5")
f0 = render(WT + fxs(19, 1.0) + ["hfx 1.0 0"], "fx0")
d = rms(W(dry, 0.5, 0.85))
check("VST3 FX: dry renders", d > 0.01, "%.4f" % d)
check("VST3 FX: unity effect passes the signal (mix 100%)", 0.9 < rms(W(f1, 0.5, 0.85)) / d < 1.1, "%.3f" % (rms(W(f1, 0.5, 0.85)) / d))
check("VST3 FX: the return is the effect output (gain 0.5)", 0.45 < rms(W(f5, 0.5, 0.85)) / d < 0.55, "%.3f" % (rms(W(f5, 0.5, 0.85)) / d))
check("VST3 FX: no effect loaded and no bypass -> silent wet", rms(W(f0, 0.5, 0.85)) < 1e-4)
# latency: unity effect = dry delayed by 64 samples
x = W(dry, 0.5, 0.8)[:, 0]; y = W(f1, 0.5, 0.8)[:, 0]
best = min(range(0, 200), key=lambda k: np.mean((y[k:k + 6000] - x[:6000]) ** 2))
check("VST3 FX: latency is exactly 64 samples", best == 64, "best %d" % best)
m0 = render(WT + fxs(19, 0.0) + ["hfx 0.5 1"], "m0")
x0 = W(m0, 0.5, 0.8)[:, 0]
best0 = min(range(0, 200), key=lambda k: np.mean((x0[k:k + 6000] - x[:6000]) ** 2))
check("VST3 FX: Mix 0 gives the dry signal, delayed like the wet path", best0 == 64 and rms(W(m0, 0.5, 0.85)) / d > 0.95, "best %d" % best0)
print("ALL OK" if failures == 0 else "FAILURES: %d" % failures); sys.exit(1 if failures else 0)
