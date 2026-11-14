#!/usr/bin/env python3
"""Audio tests of the Waveguide effect (FX type 32).   python3 tools/fx/test_wgfx.py --host <dsp_host>"""
import argparse, os, subprocess, tempfile, sys, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="wgfxTest"); RATE = 48000; failures = 0; WG = 32
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def pitchN(hz): return math.log(hz / 30.0) / math.log(2000.0 / 30.0)
def fx(ty, mode=0, mix=1.0, p=(0.5,) * 6, base=541):
    return ["p %d %d" % (base, ty), "p %d 1" % (base + 1), "p %d %s" % (base + 2, mix), "p %d %d" % (base + 3, mode)] + ["p %d %s" % (base + 4 + i, v) for i, v in enumerate(p)]
def render(cmds, hold=0.12, tail=1.2, tag="x", note=60):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 saw\np %d 0\n" % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        f.write("run 0.3\non %d 110\nrun %s\noff %d\nrun %s\n" % (note, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
T0 = int((0.3 + 0.12) * RATE)
def tail(a, t0=0.25, t1=0.9):
    return a[T0 + int(t0 * RATE):T0 + int(t1 * RATE), 0].astype(np.float64)
def spec(x):
    w = np.hanning(len(x)); s = np.abs(np.fft.rfft(x * w)); fr = np.fft.rfftfreq(len(x), 1.0 / RATE); return fr, s
def peakNear(x, hz, width=0.06):
    fr, s = spec(x); m = (fr > hz * (1 - width)) & (fr < hz * (1 + width)); return s[m].max(), fr[m][np.argmax(s[m])]
for mode, nm in enumerate(["String", "Tube", "Dual Strings", "Fifth Drone", "Octave Drone"]):
    a = render(fx(WG, mode, 1.0, (pitchN(220.0), 0.75, 0.8, 0.1, 0.6, 0.0)), tag="m%d" % mode)
    check("%s: finite and bounded" % nm, np.isfinite(a).all() and np.abs(a).max() < 6.0, "peak %.2f" % np.abs(a).max())
    t = tail(a)
    check("%s: rings after the input stops" % nm, np.sqrt(np.mean(t ** 2)) > 1e-3, "rms %.4f" % np.sqrt(np.mean(t ** 2)))
    if mode in (0, 1, 2):
        pk, fq = peakNear(t, 220.0)
        check("%s: rings at the Pitch knob (220 Hz)" % nm, abs(fq - 220.0) < 4.0, "%.1f Hz" % fq)
a = render(fx(WG, 3, 1.0, (pitchN(200.0), 0.75, 0.8, 0.1, 0.6, 0.0)), tag="fifth"); t = tail(a)
p1, f1 = peakNear(t, 200.0); p2, f2 = peakNear(t, 300.0)
check("Fifth Drone rings at f and 1.5 f", abs(f1 - 200) < 5 and abs(f2 - 300) < 6 and p2 > 0.1 * p1, "%.1f / %.1f Hz" % (f1, f2))
a = render(fx(WG, 4, 1.0, (pitchN(240.0), 0.75, 0.8, 0.1, 0.6, 0.0)), tag="oct"); t = tail(a)
p1, f1 = peakNear(t, 240.0); p2, f2 = peakNear(t, 120.0)
check("Octave Drone rings at f and f / 2", abs(f1 - 240) < 6 and abs(f2 - 120) < 4 and p2 > 0.03 * p1, "%.1f / %.1f Hz" % (f1, f2))
# Decay knob
lo = render(fx(WG, 0, 1.0, (pitchN(220.0), 0.2, 0.8, 0.1, 0.6, 0.0)), tag="dl", tail=2.5)
hi = render(fx(WG, 0, 1.0, (pitchN(220.0), 0.9, 0.8, 0.1, 0.6, 0.0)), tag="dh", tail=2.5)
def rr(a, t0, t1): return float(np.sqrt(np.mean(a[T0 + int(t0 * RATE):T0 + int(t1 * RATE), 0].astype(np.float64) ** 2)))
check("Decay knob: long decay keeps the ring, short decay does not (1.5 s after the note)", rr(hi, 1.5, 2.0) > 5 * max(rr(lo, 1.5, 2.0), 1e-7), "%.5f vs %.5f" % (rr(hi, 1.5, 2.0), rr(lo, 1.5, 2.0)))
# mix 0 = dry
dry = render([], tag="dry"); m0 = render(fx(WG, 0, 0.0, (0.5,) * 6), tag="m0")
check("Mix 0 equals dry", np.abs(m0[:T0] - dry[:T0]).max() < 1e-5)
# stereo spread: Detune moves left and right apart
sp = render(fx(WG, 0, 1.0, (pitchN(220.0), 0.75, 0.8, 1.0, 0.6, 0.0)), tag="sp"); t = sp[T0 + int(0.25 * RATE):T0 + int(0.9 * RATE)]
check("Detune spreads the strings left / right", np.abs(t[:, 0] - t[:, 1]).max() > 0.01)
# drive keeps it bounded at full excite
dv = render(fx(WG, 0, 1.0, (pitchN(220.0), 0.95, 0.9, 0.1, 1.0, 1.0)), tag="dv")
check("Drive 100 % and long decay stay bounded", np.isfinite(dv).all() and np.abs(dv).max() < 8.0, "peak %.2f" % np.abs(dv).max())
# oscillator rack: type 32 in an OSC slot (ids 8000 + 16 * slot + k)
def oscfx(sl, ty, mode, p):
    b = 8000 + 16 * sl
    return ["p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d 1.0" % (b + 2), "p %d %d" % (b + 3, mode)] + ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
o = render(oscfx(0, WG, 0, (pitchN(220.0), 0.75, 0.8, 0.1, 0.6, 0.0)), hold=0.6, tag="osc")
w = o[int((0.3 + 0.2) * RATE):int((0.3 + 0.6) * RATE), 0].astype(np.float64)
d0 = render([], hold=0.6, tag="osc0")[int((0.3 + 0.2) * RATE):int((0.3 + 0.6) * RATE), 0].astype(np.float64)
r1 = peakNear(w, 220.0, 0.03)[0] / (peakNear(d0, 220.0, 0.03)[0] + 1e-9)
check("Oscillator rack: Waveguide rings at 220 Hz inside the voice (boosts the 220 Hz region)", np.isfinite(o).all() and r1 > 3.0, "x%.1f" % r1)
print("%d failures" % failures); sys.exit(1 if failures else 0)
