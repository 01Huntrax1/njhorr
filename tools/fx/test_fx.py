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

print("FAILURES: %d" % failures if failures else "ALL OK")
raise SystemExit(1 if failures else 0)
