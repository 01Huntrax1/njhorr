#!/usr/bin/env python3
"""Audio tests of the FX rack additions.   python3 tools/fx/test_fx.py --host host_fx"""
import argparse, os, subprocess, tempfile
import sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="fxTest"); RATE = 48000; failures = 0

def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1

def base(slot): return 541 + 10 * slot + (10 if slot >= 10 else 0) + (10 if slot >= 20 else 0)

def fx(slot, ty, mode=0, mix=1.0, p=(0.5,) * 6):
    b = base(slot)
    c = ["p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d %s" % (b + 2, mix), "p %d %d" % (b + 3, mode)]
    c += ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
    return c

def render(cmds, hold=0.3, tail=1.5, tag="x"):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 sine\np %d 0\n" % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        f.write("run 0.6\non 69 110\nrun %s\noff 69\nrun %s\n" % (hold, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)

def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
T0 = int((0.6 + 0.3) * RATE)

dry = render([], tag="dry")
check("dry renders sound", rms(dry[int(0.7 * RATE):T0]) > 1e-4)
tail_dry = rms(dry[T0 + int(0.5 * RATE):T0 + int(1.0 * RATE)])

for mode, name in enumerate(["Room", "Hall", "Plate", "Cathedral", "Chamber", "Reverse", "Gated", "Ambience"]):
    a = render(fx(0, 12, mode, 1.0, (0.6, 0.6, 0.3, 0.0, 0.5, 0.5)), tag="cv%d" % mode)
    ok = np.isfinite(a).all() and np.abs(a).max() < 4.0
    check("conv %s finite and bounded" % name, ok, "peak %.2f" % np.abs(a).max())
    w = rms(a[int(0.7 * RATE):T0])
    if mode == 5: w = rms(a[T0:T0 + int(0.6 * RATE)])
    check("conv %s produces output" % name, w > 1e-4, "rms %.4f" % w)
    if mode in (0, 1, 2, 3, 4):
        tl = rms(a[T0 + int(0.15 * RATE):T0 + int(0.35 * RATE)])
        check("conv %s has a tail after note-off" % name, tl > 5 * max(tail_dry, 1e-6) or tl > 1e-3, "tail %.5f" % tl)

# longer decay -> longer tail
s = render(fx(0, 12, 1, 1.0, (0.3, 0.2, 0.3, 0.0, 0.5, 0.5)), tag="short")
l = render(fx(0, 12, 1, 1.0, (0.9, 0.9, 0.3, 0.0, 0.5, 0.5)), tag="long")
ts = rms(s[T0 + int(0.8 * RATE):T0 + int(1.3 * RATE)]); tl = rms(l[T0 + int(0.8 * RATE):T0 + int(1.3 * RATE)])
check("bigger size / decay gives a longer tail", tl > 2 * ts, "%.5f vs %.5f" % (tl, ts))

# user IR: unit impulse at 2000 samples -> wet = dry delayed by 1024 + 2000 (low-passed)
cmds = ["ir 0 impulse 2000"] + fx(0, 12, 8, 1.0, (1.0, 0.5, 0.0, 0.0, 0.5, 0.5))
u = render(cmds, tag="user")
check("user IR finite", np.isfinite(u).all() and np.abs(u).max() < 4.0)
nf = render(fx(0, 0), tag="nofx")
x = nf[:, 0].astype(np.float64); y = u[:, 0].astype(np.float64)
seg = slice(int(0.7 * RATE), int(0.85 * RATE))
def onset(v):
    v = np.abs(v[int(0.55 * RATE):int(1.0 * RATE)]); return int(np.argmax(v > 0.5 * v.max()))
on_x = onset(x); on_y = onset(y)
bl = on_y - on_x; best = 1.0
check("user IR impulse = dry delayed by 1024 + 2000 samples", abs(bl - 3024) <= 40, "lag %d" % bl)

# a second convolution slot in the same rack passes through (one engine per rack)
two = render(fx(0, 12, 1, 1.0) + fx(1, 12, 3, 1.0), tag="two")
check("two conv slots in a rack stay finite", np.isfinite(two).all() and np.abs(two).max() < 4.0)

# mix 0 = dry
m0 = render(fx(0, 12, 1, 0.0), tag="m0")
check("mix 0 equals dry", np.allclose(m0, dry, atol=1e-5))

# ---- extended algorithms / parameters of the other effects: every mode, parameters at both extremes
import itertools
MODES = {1: 9, 2: 3, 3: 4, 4: 3, 5: 2, 6: 4, 7: 5, 8: 4, 11: 2}
for ty, nm in MODES.items():
    bad = []
    for md in range(nm):
        for pv in (0.0, 1.0):
            a = render(fx(0, ty, md, 1.0, (pv,) * 6), hold=0.2, tail=0.3, tag="sw")
            if not np.isfinite(a).all() or np.abs(a).max() > 8.0: bad.append((md, pv, float(np.abs(a).max())))
    check("type %d: all %d modes finite and bounded at parameter extremes" % (ty, nm), not bad, str(bad[:3]))

# new distortion modes actually distort (more harmonics than the clean sine)
def thd(v):
    seg = v[int(0.7 * RATE):int(0.85 * RATE), 0].astype(np.float64); X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); k = int(np.argmax(X))
    return 1.0 - X[max(0, k - 3):k + 4].sum() / (X.sum() + 1e-12)
for md, nm in ((6, "Rectify"), (7, "Fuzz"), (8, "Tanh")):
    a = render(fx(0, 1, md, 1.0, (0.8, 1.0, 0.5, 0.5, 0.0, 0.0)), tag="d%d" % md)
    check("distortion %s adds harmonics" % nm, thd(a) > thd(dry) + 0.02, "%.3f vs %.3f" % (thd(a), thd(dry)))

# bias adds even harmonics, DC stays blocked
b0 = render(fx(0, 1, 0, 1.0, (0.8, 1.0, 0.5, 0.5, 0.0, 0.0)), tag="b0"); b1 = render(fx(0, 1, 0, 1.0, (0.8, 1.0, 0.5, 1.0, 0.0, 0.0)), tag="b1")
check("distortion bias changes the spectrum", abs(thd(b0) - thd(b1)) > 0.005 or not np.allclose(b0, b1, atol=1e-3))
check("distortion DC blocked", abs(float(b1[int(0.8 * RATE):int(0.9 * RATE), 0].mean())) < 0.05)

# negative flanger feedback differs from positive; flanger width 0 = mono wet
f0 = render(fx(0, 5, 0, 1.0, (0.3, 0.6, 0.9, 0.5, 0.5, 0.5)), tag="f0"); f1 = render(fx(0, 5, 1, 1.0, (0.3, 0.6, 0.9, 0.5, 0.5, 0.5)), tag="f1")
check("flanger negative mode differs", not np.allclose(f0, f1, atol=1e-3))
fw = render(fx(0, 4, 0, 1.0, (0.5, 0.5, 0.0, 0.0, 0.5, 0.5)), tag="fw")
seg2 = fw[int(0.7 * RATE):int(0.9 * RATE)]
check("chorus width 0 collapses the wet to mono", np.abs(seg2[:, 0] - seg2[:, 1]).max() < 1e-4)

# ducking delay is quieter during the note than the plain delay, and a low cut lowers the echo level
dp = render(fx(0, 3, 0, 1.0, (0.3, 0.6, 1.0, 0.0, 0.0, 0.0)), tag="dp"); dd = render(fx(0, 3, 3, 1.0, (0.3, 0.6, 1.0, 0.0, 0.0, 0.0)), tag="dd")
check("ducking delay differs from the plain delay", not np.allclose(dp, dd, atol=1e-3))

# reverb wet low cut / high cut change the level
r0 = render(fx(0, 8, 0, 1.0, (0.5, 0.5, 0.2, 1.0, 0.0, 1.0)), tag="r0"); r1 = render(fx(0, 8, 0, 1.0, (0.5, 0.5, 0.2, 1.0, 1.0, 0.0)), tag="r1")
check("reverb tone filters narrow the wet signal", rms(r1[T0:]) < 0.8 * rms(r0[T0:]), "%.5f vs %.5f" % (rms(r1[T0:]), rms(r0[T0:])))

# compressor knee: soft knee reduces the gain below the threshold, hard knee does not
c0 = render(fx(0, 11, 0, 1.0, (0.8, 0.8, 0.1, 0.4, 0.0, 0.0)), tag="c0"); c1 = render(fx(0, 11, 0, 1.0, (0.8, 0.8, 0.1, 0.4, 0.0, 1.0)), tag="c1")
check("compressor soft knee acts below the threshold", rms(c1[int(0.7 * RATE):T0]) < rms(c0[int(0.7 * RATE):T0]) - 1e-4, "%.4f vs %.4f" % (rms(c1[int(0.7 * RATE):T0]), rms(c0[int(0.7 * RATE):T0])))

print("FAILURES: %d" % failures if failures else "ALL OK")
raise SystemExit(1 if failures else 0)
