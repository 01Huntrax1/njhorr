#!/usr/bin/env python3
"""Tests of the arpeggiator.   python3 tools/mod/test_arp.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="arpTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
A = 3920
def arp(on=1, mode=0, octs=1, sync=0, div=11, rate=2.0, gate=0.8, latch=0):
    return [(A + i, v) for i, v in enumerate([on, mode, octs, sync, div, rate, gate, latch])]
BASE = ["wt 0 sine", (L.pid(0, K["fon"]), 0)]
def render(cmds, keys, hold=3.2, tail=0.5, tag="x", release=True):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\n")
        for k in keys: f.write("on %d 100\n" % k)
        f.write("run %s\n" % hold)
        if release:
            for k in keys: f.write("off %d\n" % k)
        f.write("run %s\n" % tail)
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)[:, 0]
def midi_of(x):
    x = x - np.mean(x)
    if np.sqrt(np.mean(x ** 2)) < 0.01: return None
    z = np.where((x[:-1] < 0) & (x[1:] >= 0))[0]
    if len(z) < 8: return None
    f = RATE * (len(z) - 1) / (z[-1] - z[0])
    return int(round(69 + 12 * np.log2(f / 440.0)))
def steps(a, n, dur=0.5):   # note of every step: window 0.1 .. 0.35 s into the step (the first step starts at 0.05 s)
    return [midi_of(a[int((0.051 + k * dur + 0.1) * RATE):int((0.051 + k * dur + 0.35) * RATE)]) for k in range(n)]
C = [60, 64, 67]
s = steps(render(BASE + arp(mode=0), C, tag="up"), 6)
check("Up: 60 64 67 60 64 67", s == [60, 64, 67, 60, 64, 67], str(s))
s = steps(render(BASE + arp(mode=1), C, tag="down"), 4)
check("Down: 67 64 60 67", s == [67, 64, 60, 67], str(s))
s = steps(render(BASE + arp(mode=2), C, tag="ud"), 6)
check("Up / Down: 60 64 67 64 60 64", s == [60, 64, 67, 64, 60, 64], str(s))
s = steps(render(BASE + arp(mode=0, octs=2), C, tag="oct"), 7)
check("Octaves 2: 60 64 67 72 76 79 60", s == [60, 64, 67, 72, 76, 79, 60], str(s))
s = steps(render(BASE + arp(mode=4), [67, 60, 64], tag="asp"), 4)
check("As played: 67 60 64 67", s == [67, 60, 64, 67], str(s))
s = steps(render(BASE + arp(mode=3), C, tag="rnd", hold=5.2), 10)
check("Random uses only the held notes and several of them", None not in s and set(s) <= set(C) and len(set(s)) >= 2, str(s))
s = steps(render(BASE + arp(mode=0, sync=1, div=8), C, tag="sync", hold=3.2), 4, dur=0.5)   # 1/4 at 120 bpm = 0.5 s
check("Tempo sync: 1/4 notes at 120 bpm = 0.5 s per step", s == [60, 64, 67, 60], str(s))
a = render(BASE + arp(gate=0.3), C, tag="gate")
rm = lambda x: float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
on_ = rm(a[int(0.10 * RATE):int(0.17 * RATE)]); off_ = rm(a[int(0.45 * RATE):int(0.54 * RATE)])
check("Gate 0.3: the note is released well before the next step", on_ > 0.05 and off_ < 0.5 * on_, "%.3f vs %.3f" % (on_, off_))
a = render(BASE + arp(on=0), C, tag="off", hold=1.0)
check("Arp off: the keys play as a chord", rm(a[int(0.3 * RATE):int(0.9 * RATE)]) > 0.1)
a = render(BASE + arp(latch=1), C, tag="latch", hold=0.8, tail=2.0)
a2 = render(BASE + arp(latch=0), C, tag="nolatch", hold=0.8, tail=2.0)
check("Latch keeps playing after the keys are released", rm(a[int(1.5 * RATE):int(2.8 * RATE)]) > 0.1 and rm(a2[int(1.8 * RATE):int(2.8 * RATE)]) < 0.01,
      "%.3f / %.3f" % (rm(a[int(1.5 * RATE):int(2.8 * RATE)]), rm(a2[int(1.8 * RATE):int(2.8 * RATE)])))
a = render(BASE + arp(), C, tag="fin", hold=0.6, tail=1.5)
check("Stops after the keys are released, output finite", np.isfinite(a).all() and rm(a[int(1.9 * RATE):]) < 0.01)
s = steps(render(BASE + arp(mode=0), [60, 64, 67], tag="two"), 2)
check("A single held note repeats", steps(render(BASE + arp(mode=0), [64], tag="one"), 4) == [64, 64, 64, 64])
print("FAILURES: %d" % failures if failures else "ALL OK"); sys.exit(1 if failures else 0)
