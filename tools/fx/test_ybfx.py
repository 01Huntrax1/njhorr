#!/usr/bin/env python3
"""Audio tests of the Yaybahar effect (FX type 33).   python3 tools/fx/test_ybfx.py --host <dsp_host>"""
import argparse, os, subprocess, tempfile, sys, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="ybfxTest"); RATE = 48000; failures = 0; YB = 33
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def kn(hz, lo, hi): return math.log(hz / lo) / math.log(hi / lo)
def fx(ty, mode=0, mix=1.0, p=(0.5,) * 6, base=541):
    return ["p %d %d" % (base, ty), "p %d 1" % (base + 1), "p %d %s" % (base + 2, mix), "p %d %d" % (base + 3, mode)] + ["p %d %s" % (base + 4 + i, v) for i, v in enumerate(p)]
def render(cmds, hold=0.12, tail=2.0, tag="x", note=60):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 saw\np %d 0\n" % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        f.write("run 0.3\non %d 110\nrun %s\noff %d\nrun %s\n" % (note, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
T0 = int((0.3 + 0.12) * RATE)
def seg(a, t0, t1, ch=0): return a[T0 + int(t0 * RATE):T0 + int(t1 * RATE), ch].astype(np.float64)
def rms(x): return float(np.sqrt(np.mean(x ** 2)))
dry = render(fx(0), tag="dry")
check("dry reference: the note sounds", rms(seg(dry, -0.1, 0.0)) > 0.01 or rms(dry[int(0.35 * RATE):int(0.4 * RATE), 0]) > 0.01)
for mode, nm in enumerate(["Single Spring", "Dual Spring", "Deep"]):
    a = render(fx(YB, mode, 1.0, (kn(110, 40, 800), 0.5, 0.7, 0.5, 0.4, 0.6)), tag="m%d" % mode)
    check("%s: finite and bounded" % nm, np.isfinite(a).all() and np.abs(a).max() < 6.0, "peak %.2f" % np.abs(a).max())
    check("%s: rings on after the input stops (0.3..1.0 s)" % nm, rms(seg(a, 0.3, 1.0)) > 1e-3, "rms %.4f" % rms(seg(a, 0.3, 1.0)))
    check("%s: decays away (tail quieter than 0.3..0.6 s)" % nm, rms(seg(a, 1.6, 2.0)) < rms(seg(a, 0.3, 0.6)) * 1.01, "%.4f vs %.4f" % (rms(seg(a, 1.6, 2.0)), rms(seg(a, 0.3, 0.6))))
    check("%s: stereo channels differ (spring spread)" % nm, rms(seg(a, 0.3, 1.0, 0) - seg(a, 0.3, 1.0, 1)) > 1e-4)
lo = render(fx(YB, 0, 1.0, (kn(110, 40, 800), 0.5, 0.7, 0.5, 0.0, 0.6)), tag="memlo")
hi = render(fx(YB, 0, 1.0, (kn(110, 40, 800), 0.5, 0.7, 0.5, 1.0, 0.6)), tag="memhi")
def band(x, lo_, hi_):
    s_ = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE); return float(np.sum(s_[(f > lo_) & (f < hi_)]))
check("Membran knob down puts more energy below 70 Hz than up", band(seg(lo, 0.2, 1.2), 30, 70) > 1.5 * band(seg(hi, 0.2, 1.2), 30, 70), "%.3g vs %.3g" % (band(seg(lo, 0.2, 1.2), 30, 70), band(seg(hi, 0.2, 1.2), 30, 70)))
sh = render(fx(YB, 0, 1.0, (kn(110, 40, 800), 0.0, 0.8, 0.5, 0.4, 0.6)), tag="short")
lg = render(fx(YB, 0, 1.0, (kn(110, 40, 800), 1.0, 0.8, 0.5, 0.4, 0.6)), tag="long")
d_ = seg(lg, 0.1, 1.5) - seg(sh, 0.1, 1.5)
check("Spring knob changes the sound (short vs long spring differ)", rms(d_) > 0.3 * rms(seg(sh, 0.1, 1.5)), "diff rms %.4f, ref %.4f" % (rms(d_), rms(seg(sh, 0.1, 1.5))))
check("mix 0 = dry", np.allclose(render(fx(YB, 0, 0.0), tag="mix0")[:int(1.0 * RATE)], dry[:int(1.0 * RATE)], atol=1e-4))
print("%d failures" % failures); sys.exit(1 if failures else 0)
