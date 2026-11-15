#!/usr/bin/env python3
"""Audio tests of the patch matrix of Njohrr Modular.   python3 tools/modular/test_modplugin.py --host <dsp_host of patch_mod, built with -DDSP_FX>"""
import argparse, os, subprocess, tempfile, sys
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="modTest"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
SRC_SYNTH, SRC_IN = 1, 2
def mod(m): return 3 + m                       # source value of FX module m (0..15)
def cable(dest, c, src, gain=1.0):             # dest 0..15 = module, 16 = Out
    i = 9700 + 8 * dest + 2 * c
    return ["p %d %d" % (i, src), "p %d %s" % (i + 1, gain)]
def slot(m, ty, mode=0, mix=1.0, p=(0.5,) * 6):   # Main rack slot m (0..9 only in these tests)
    b = 541 + 10 * m
    return ["p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d %s" % (b + 2, mix), "p %d %d" % (b + 3, mode)] + ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
def render(cmds, synth=False, inp=("sine", 0.3, 220.0), tag="x", hold=0.6):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 saw\n")
        if inp: f.write("in %s %s %s\n" % inp)
        for c in cmds: f.write(c + "\n")
        f.write("run 0.2\n")
        if synth: f.write("on 57 110\n")
        f.write("run %s\n" % hold)
        if synth: f.write("off 57\nrun 0.2\n")
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def seg(a, t0=0.35, t1=0.75): return a[int(t0 * RATE):int(t1 * RATE), 0].astype(np.float64)
def rms(x): return float(np.sqrt(np.mean(x ** 2)))
def hf(x, f0=600.0):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.fft.rfftfreq(len(x), 1.0 / RATE); return float(np.sqrt(np.sum(X[f > f0] ** 2)) / (np.sqrt(np.sum(X ** 2)) + 1e-12))

base = render([], tag="default"); r0 = rms(seg(base))
check("default patch: Audio In reaches Out (Synth silent)", r0 > 0.05 and np.isfinite(base).all(), "rms %.3f" % r0)
sy = render([], synth=True, inp=None, tag="synth")
check("default patch: Synth reaches Out", rms(seg(sy, 0.3, 0.7)) > 0.01, "rms %.3f" % rms(seg(sy, 0.3, 0.7)))
none = render(cable(16, 0, mod(0)) + cable(16, 1, 0) + cable(0, 0, SRC_IN), tag="thru")
check("In -> module 1 (empty slot) -> Out passes the signal unchanged", abs(rms(seg(none)) / r0 - 1) < 0.02, "%.3f" % (rms(seg(none)) / r0))
half = render(cable(16, 0, mod(0)) + cable(16, 1, 0) + cable(0, 0, SRC_IN, 0.5), tag="half")
check("cable gain 0.5 halves the level", abs(rms(seg(half)) / r0 - 0.5) < 0.02, "%.3f" % (rms(seg(half)) / r0))
par = render(cable(16, 0, SRC_IN) + cable(16, 1, mod(0)) + cable(0, 0, SRC_IN), tag="par")
check("parallel cables into Out add up (2x)", abs(rms(seg(par)) / r0 - 2.0) < 0.05, "%.3f" % (rms(seg(par)) / r0))
nocab = render(cable(16, 0, mod(1)) + cable(16, 1, 0), tag="nocab")
check("module without cables is silent", rms(seg(nocab)) < 1e-6)
dist = render(cable(16, 0, mod(0)) + cable(16, 1, 0) + cable(0, 0, SRC_IN) + slot(0, 1, 0, 1.0, (0.9, 0.5, 0.5, 0.5, 0.5, 0.5)), tag="dist")
check("module 1 as Distortion adds harmonics", hf(seg(dist)) > 3 * hf(seg(base)) + 0.01, "%.3f vs %.3f" % (hf(seg(dist)), hf(seg(base))))
ser = render(cable(16, 0, mod(1)) + cable(16, 1, 0) + cable(0, 0, SRC_IN) + cable(1, 0, mod(0)) + slot(1, 1, 0, 1.0, (0.9, 0.5, 0.5, 0.5, 0.5, 0.5)), tag="ser")
check("serial chain In -> M1 (empty) -> M2 (Distortion) equals In -> M2 directly", rms(seg(ser) - seg(render(cable(16, 0, mod(1)) + cable(16, 1, 0) + cable(1, 0, SRC_IN) + slot(1, 1, 0, 1.0, (0.9, 0.5, 0.5, 0.5, 0.5, 0.5)), tag="ser2"))) < 0.01 * rms(seg(ser)) + 1e-4)
bk = render(cable(16, 0, mod(0)) + cable(16, 1, 0) + cable(1, 0, SRC_IN) + cable(0, 0, mod(1)), tag="back")
check("a cable from a later module (previous sample) still passes the signal", abs(rms(seg(bk)) / r0 - 1) < 0.03, "%.3f" % (rms(seg(bk)) / r0))
fb = render(cable(16, 0, mod(0)) + cable(16, 1, 0) + cable(0, 0, SRC_IN) + cable(0, 1, mod(0), 0.5), tag="fb")
check("feedback loop (module 1 into itself, gain 0.5) is stable and boosts about 2x", np.isfinite(fb).all() and abs(rms(seg(fb)) / r0 - 2.0) < 0.2, "%.3f" % (rms(seg(fb)) / r0))
fh = render(cable(16, 0, mod(0)) + cable(16, 1, 0) + cable(0, 0, SRC_IN) + cable(0, 1, mod(0), 2.0), tag="fbh")
check("feedback with gain 2 stays bounded (limiter)", np.isfinite(fh).all() and np.abs(fh).max() <= 1.0)
sd = render(cable(16, 0, mod(0)) + cable(16, 1, 0) + cable(0, 0, SRC_SYNTH) + slot(0, 1, 0, 1.0, (0.9, 0.5, 0.5, 0.5, 0.5, 0.5)), synth=True, inp=None, tag="sdist")
check("Synth -> module 1 (Distortion) -> Out differs from the plain Synth", rms(seg(sd, 0.3, 0.7) - seg(sy, 0.3, 0.7)) > 0.1 * rms(seg(sy, 0.3, 0.7)))
mx = render(cable(16, 0, mod(0)) + cable(16, 1, 0) + cable(0, 0, SRC_SYNTH) + cable(0, 1, SRC_IN), synth=True, inp=("sine", 0.3, 333.0), tag="mix")
check("Synth and Audio In mix in one module", rms(seg(mx, 0.3, 0.7)) > rms(seg(sy, 0.3, 0.7)) * 0.9 and rms(seg(mx, 0.3, 0.7)) > r0 * 0.9, "%.3f %.3f %.3f (input 333 Hz so that it does not cancel the 220 Hz synth)" % (rms(seg(mx, 0.3, 0.7)), rms(seg(sy, 0.3, 0.7)), r0))
sl = render(cable(16, 0, mod(15)) + cable(16, 1, 0) + cable(15, 0, SRC_IN) + ["p 3250 1", "p 3251 1", "p 3252 1.0", "p 3253 0"] + ["p %d 0.9" % (3254)], tag="m16")
check("module 16 (Main FX slot 16) works and the matrix carries it", np.isfinite(sl).all() and rms(seg(sl)) > 0.01, "rms %.3f" % rms(seg(sl)))
print("%d failures" % failures); sys.exit(1 if failures else 0)
