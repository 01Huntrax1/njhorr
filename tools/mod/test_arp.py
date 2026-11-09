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
# a Retrig sequencer restarts on every arp note: sequencer (steps 0.2 / 1.0, 2 Hz, arp 4 Hz) -> every note sits on step 1 (low level)
SB = lambda m: 3600 + 32 * m
def seqc(retrig): return [(SB(0) + 0, 0.2), (SB(0) + 1, 1.0), (SB(0) + 16, 2), (SB(0) + 17, 2.0), (L.pid(0, K["level"]), 0.0), (SB(0) + 18, 0), (SB(0) + 22, retrig), (SB(0) + 23, 0),
                          (307, 34), (308, L.dst_index(0, 1)), (309, 1.0)]
a = render(BASE + arp(rate=4.0, gate=0.9) + seqc(1), C, tag="sr1", hold=2.6)
b = render(BASE + arp(rate=4.0, gate=0.9) + seqc(0), C, tag="sr0", hold=2.6)
w_ = lambda x, t: rm(x[int(t * RATE):int((t + 0.2) * RATE)])
hi = max(w_(a, 0.3 + 0.5 * k) for k in range(5)); hb = max(w_(b, 0.3 + 0.5 * k) for k in range(5))
check("Retrig sequencer restarts on each arp note (always the low step); a free one runs on", hi < 0.6 * hb and hb > 0.1, "%.3f vs %.3f" % (hi, hb))
# changing the pattern while playing: switching the arp off releases the note
a = render(BASE + arp(), C, tag="offmid", hold=0.4, tail=1.0, release=False)
check("Output finite when keys stay held", np.isfinite(a).all())
# latch switched off after the keys are up: the held notes go
script = os.path.join(TMP, "lo.txt"); out = os.path.join(TMP, "lo.f32")
open(script, "w").write("\n".join(["wt 0 sine", "p %d 0" % (A + 7), "p %d 1" % A, "p %d 6" % (A + 5), "p %d 0" % (A + 3), "p %d 0.8" % (A + 6), "p %d 1" % (A + 7), "run 0.05"] + ["on %d 100" % k for k in C] + ["run 0.6"] + ["off %d" % k for k in C] + ["run 0.6", "p %d 0" % (A + 7), "run 1.0"]) + "\n")
subprocess.run([args.host, script, out], check=True)
a_ = np.fromfile(out, dtype=np.float32).reshape(-1, 2)[:, 0]
check("Latch switched off after the keys are up stops the arp", rm(a_[int(0.8 * RATE):int(1.2 * RATE)]) > 0.05 and rm(a_[int(1.9 * RATE):]) < 0.01, "%.3f / %.4f" % (rm(a_[int(0.8 * RATE):int(1.2 * RATE)]), rm(a_[int(1.9 * RATE):])))
# ---- 303 mode (Arp Mode 5): default pattern notes 0 0 12 0 0 10 0 7 0 12 0 0 3 5 0 0, rests on steps 6, 12, 16, slides on 4, 8, 13
def seg(a, k, t0, t1, dur=0.5): return a[int((0.051 + k * dur + t0) * RATE):int((0.051 + k * dur + t1) * RATE)]
rms = lambda x: float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)))
a = render(BASE + arp(mode=5, gate=0.5) + [(5264, 8)], [48], hold=5.3, tag="a303")
s = steps(a, 8)
exp = [48, 48, 60, 48, 48, None, 48, 55]
check("303: notes of the default pattern (root = the key, rest = silence)", [x if x is not None else None for x in s[:5]] == exp[:5] and s[6:8] == exp[6:8], str(s))
check("303: a rest is silent", rms(seg(a, 5, 0.15, 0.45)) < 0.2 * rms(seg(a, 4, 0.05, 0.2)), "%.4f vs %.4f" % (rms(seg(a, 5, 0.15, 0.45)), rms(seg(a, 4, 0.05, 0.2))))
check("303: a slide holds the note to the end of the step", rms(seg(a, 3, 0.35, 0.48)) > 3 * rms(seg(a, 1, 0.35, 0.48)), "%.4f vs %.4f" % (rms(seg(a, 3, 0.35, 0.48)), rms(seg(a, 1, 0.35, 0.48))))
check("303: Length 8 repeats the pattern after 8 steps", steps(a, 9)[8] == 48 and steps(a, 10)[9] == 48, str(steps(a, 10)))
b = render(BASE + arp(mode=5, gate=0.5) + [(5264, 3)], [48], hold=3.0, tag="b303")
sb = steps(b, 6)
check("303: Length 3 plays 48 48 60 48 48 60", sb == [48, 48, 60, 48, 48, 60], str(sb))
c = render(BASE + arp(mode=5, gate=0.5) + [(5200, 7), (5201, -5), (5264, 2)], [48], hold=2.5, tag="c303")
sc = steps(c, 4)
check("303: the step notes are editable (+7, -5)", sc == [55, 43, 55, 43], str(sc))
d = render(BASE + arp(mode=5, gate=0.5) + [(5264, 2)], [48, 52], hold=2.0, tag="d303")
check("303: the root is the last key pressed", steps(d, 2) == [52, 52], str(steps(d, 2)))

print("FAILURES: %d" % failures if failures else "ALL OK"); sys.exit(1 if failures else 0)
