#!/usr/bin/env python3
"""Audio tests of the per-oscillator effect rack (OSCFX3-DSP).   python3 tools/fx/test_oscrack.py --host <dsp_host>"""
import argparse, os, subprocess, tempfile, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="orTest"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def fx(o, sl, ty, mix=1.0, p=(0.5,) * 6, mode=0, on=1):
    b = 8000 + 272 * o + 16 * sl
    return ["p %d %d" % (b, ty), "p %d %d" % (b + 1, on), "p %d %s" % (b + 2, mix), "p %d %d" % (b + 3, mode)] + ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
def render(cmds, tag="x", notes=(57,), hold=0.5):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 saw\np %d 0\n" % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        f.write("run 0.3\n")
        for n in notes: f.write("on %d 110\n" % n)
        f.write("run %s\n" % hold)
        for n in notes: f.write("off %d\n" % n)
        f.write("run 0.5\n")
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def seg(a): return a[int(0.4 * RATE):int(0.7 * RATE)]
dry = render([], "dry")
check("dry reference sounds", np.abs(seg(dry)).max() > 0.01)
NAME = {1:"Distortion",2:"BitCrush",4:"Chorus",5:"Flanger",6:"Phaser",7:"Tremolo",9:"Filter",10:"EQ",11:"Compressor",14:"Saturator",17:"Console",18:"Filterbank",19:"PurestDrive",20:"Spiral",21:"Drive",22:"Tube",23:"Density",24:"Console7",25:"Channel",26:"ToTape",27:"MackEQ",28:"Plasma",30:"Warp"}
for t, nm in NAME.items():
    a = render(fx(0, 0, t, 1.0, (0.7, 0.4, 0.6, 0.5, 0.5, 0.5)), "t%d" % t, notes=(57, 64))
    s = seg(a)
    check("%s: finite, bounded, audible" % nm, np.isfinite(a).all() and np.abs(a).max() < 8 and np.abs(s).max() > 1e-3, "peak %.2f" % np.abs(a).max())
# does the effect change the sound at all (distortion vs dry)
a = render(fx(0, 0, 1, 1.0, (0.9, 1.0, 0.5, 0.5, 0.0, 0.0)), "d1")
check("Distortion changes the signal", np.abs(seg(a) - seg(dry)).max() > 0.05)
# mix 0 = dry
a = render(fx(0, 0, 1, 0.0, (0.9, 1.0, 0.5, 0.5, 0.0, 0.0)), "m0")
check("Mix 0 equals dry", np.abs(seg(a) - seg(dry)).max() < 1e-5)
# On = 0 bypasses
a = render(fx(0, 0, 1, 1.0, (0.9, 1.0, 0.5, 0.5, 0.0, 0.0), on=0), "off")
check("On = 0 bypasses", np.abs(seg(a) - seg(dry)).max() < 1e-5)
# heavy type (Delay 3, Reverb 8) is refused
for t in (3, 8, 12, 29, 31):
    a = render(fx(0, 0, t), "h%d" % t)
    check("type %d (per voice too big) stays off" % t, np.abs(seg(a) - seg(dry)).max() < 1e-5)
# chorus makes a mono oscillator stereo
a = render(fx(0, 0, 4, 1.0, (0.5, 0.8, 0.0, 1.0, 0, 0), mode=3), "ch")
check("Chorus widens a mono oscillator", np.abs(seg(a)[:, 0] - seg(a)[:, 1]).max() > 0.01)
# two slots chain (distortion then tremolo differ from distortion only)
a1 = render(fx(0, 0, 1, 1.0, (0.9, 1.0, 0.5, 0.5, 0, 0)), "c1")
a2 = render(fx(0, 0, 1, 1.0, (0.9, 1.0, 0.5, 0.5, 0, 0)) + fx(0, 1, 7, 1.0, (0.5, 1.0, 0, 0, 0.5, 0)), "c2")
check("slot 2 acts after slot 1", np.abs(seg(a1) - seg(a2)).max() > 0.02)
# every voice has its own instance: a chord stays bounded and polyphonic filters do not collide
a = render(fx(0, 0, 9, 1.0, (0.4, 0.6, 0, 0.5, 0.5, 0.5)), "poly", notes=(48, 55, 60, 64, 67, 71, 74, 79))
check("8 voices with a filter stay finite", np.isfinite(a).all() and np.abs(a).max() < 8, "peak %.2f" % np.abs(a).max())
# other oscillator racks are independent
a = render(fx(1, 0, 1, 1.0, (0.9, 1.0, 0.5, 0.5, 0, 0)), "o2")
check("OSC 2 rack does not touch OSC 1", np.abs(seg(a) - seg(dry)).max() < 1e-5)
# 16 slots per oscillator: slot 16 works and the order parameters reorder the chain
a = render(fx(0, 15, 1, 1.0, (0.9, 1.0, 0.5, 0.5, 0, 0)), "s16")
check("slot 16 of an oscillator rack runs", np.abs(seg(a) - seg(dry)).max() > 0.05)
cmd = fx(0, 0, 1, 1.0, (0.9, 1.0, 0.5, 0.5, 0, 0)) + fx(0, 1, 9, 1.0, (0.2, 0.5, 0, 0.5, 0.5, 0.5))
o1 = render(cmd, "ord1")
swap = ["p %d %d" % (8000 + 256, 1), "p %d %d" % (8000 + 257, 0)]
o2 = render(cmd + swap, "ord2")
check("Order parameters change the processing order (Dist > Filter vs Filter > Dist)", np.abs(seg(o1) - seg(o2)).max() > 0.005, "%.4f" % np.abs(seg(o1) - seg(o2)).max())
bad = render(cmd + ["p %d 1" % (8000 + 256), "p %d 1" % (8000 + 257)], "ord3")
check("an order that is not a permutation is ignored", np.abs(seg(bad) - seg(o1)).max() < 0.2 * np.abs(seg(o1) - seg(o2)).max(), "%.5f" % np.abs(seg(bad) - seg(o1)).max())
# Sync and the other main-slot parameters exist (tremolo on a tempo division)
a = render(fx(0, 0, 7, 1.0, (0.5, 1.0, 0, 0, 0.5, 0)) + ["p %d 5" % (8000 + 10)], "sync")
check("Tremolo with a sync division stays finite", np.isfinite(a).all() and np.abs(seg(a)).max() > 1e-3)
print("%d failures" % failures); sys.exit(1 if failures else 0)
