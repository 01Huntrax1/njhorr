#!/usr/bin/env python3
"""Audio tests of the CloudSeed reverb (FX type 31).   python3 tools/fx/test_cloudseed.py --host <dsp_host>"""
import argparse, os, subprocess, tempfile, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="csTest"); RATE = 48000; failures = 0; CS = 31
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def fx(slot, ty, mode=0, mix=1.0, p=(0.5,) * 6):
    b = 541 + 10 * slot
    return ["p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d %s" % (b + 2, mix), "p %d %d" % (b + 3, mode)] + ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
def render(cmds, hold=0.3, tail=1.5, tag="x", note=69):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 sine\np %d 0\n(21 5)\n".replace("(21 5)", "p 21 5") % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        f.write("run 0.6\non %d 110\nrun %s\noff %d\nrun %s\n" % (note, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
T0 = int((0.6 + 0.3) * RATE)
def tailr(a, t0, t1): return rms(a[T0 + int(t0 * RATE):T0 + int(t1 * RATE)])
P0 = (0.45, 0.5, 0.4, 0.1, 0.3, 0.3)
NAMES = ["Dark Plate", "Hall", "Room", "Chamber", "Cathedral", "Cloud", "Ambience", "Echo Space"]
for m, nm in enumerate(NAMES):
    a = render(fx(0, CS, m, 1.0, P0), tag="m%d" % m)
    ok = np.isfinite(a).all() and np.abs(a).max() < 4.0
    check("%s: finite and bounded" % nm, ok, "peak %.2f" % np.abs(a).max())
    check("%s: output while playing" % nm, rms(a[int(0.7 * RATE):T0]) > 1e-3, "rms %.4f" % rms(a[int(0.7 * RATE):T0]))
    check("%s: tail after note off" % nm, tailr(a, 0.2, 0.5) > 5e-4, "tail %.5f" % tailr(a, 0.2, 0.5))
# decay knob
lo = render(fx(0, CS, 1, 1.0, (0.1, 0.5, 0.4, 0.1, 0.3, 0.3)), tag="dlo", tail=3.0)
hi = render(fx(0, CS, 1, 1.0, (0.85, 0.5, 0.4, 0.1, 0.3, 0.3)), tag="dhi", tail=3.0)
check("Decay knob: long decay keeps a tail, short decay does not (2 s after note off)", tailr(hi, 1.8, 2.2) > 4 * max(tailr(lo, 1.8, 2.2), 1e-7), "%.5f vs %.5f" % (tailr(hi, 1.8, 2.2), tailr(lo, 1.8, 2.2)))
# stereo decorrelation
h = render(fx(0, CS, 1, 1.0, P0), tag="st")
seg = h[T0:T0 + int(1.0 * RATE)].astype(np.float64)
cor = float(np.corrcoef(seg[:, 0], seg[:, 1])[0, 1])
check("Stereo: left and right are decorrelated", abs(cor) < 0.9, "corr %.2f" % cor)
# knobs change the sound
base = render(fx(0, CS, 1, 1.0, P0), tag="kb")
for i, nm in enumerate(["Decay", "Size", "Damp", "PreDly", "Mod", "Early"]):
    p = list(P0); p[i] = 0.9 if p[i] < 0.8 else 0.1
    a = render(fx(0, CS, 1, 1.0, tuple(p)), tag="k%d" % i)
    d = rms(a[:len(base)] - base[:len(a)]) / max(rms(base), 1e-9)
    check("Knob %s changes the output" % nm, d > 0.03, "diff %.3f" % d)
# stability: maximum decay and size with a long note
x = render(fx(0, CS, 5, 1.0, (1.0, 1.0, 0.0, 0.0, 1.0, 1.0)), hold=4.0, tail=4.0, tag="stab")
check("Extreme settings stay finite and bounded", np.isfinite(x).all() and np.abs(x).max() <= 4.01, "peak %.2f" % np.abs(x).max())
# mix 0 = dry
d0 = render(fx(0, CS, 1, 0.0, P0), tag="dry0"); dr = render([], tag="dryref")
check("Mix 0 leaves the dry signal untouched", rms(d0 - dr[:len(d0)]) < 0.01 * max(rms(dr), 1e-9))
# type switch there and back
sw = render(fx(0, CS, 1, 1.0, P0) + ["p 541 8", "p 541 %d" % CS], tag="sw")
check("Switching the type away and back stays finite", np.isfinite(sw).all())
print("%d failures" % failures); sys.exit(1 if failures else 0)
