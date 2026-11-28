#!/usr/bin/env python3
"""Tests of the Hanenbow and Luminaria arpeggiator modes (Arp Mode 13 / 14, tools/mod/build_hanenbow.py).   python3 tools/mod/test_hanenbow.py --host <dsp_host>  (build with -DSEQPOS_LOG)"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="hbTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
A = 3920
def arp(on=1, mode=0, octs=1, sync=0, div=11, rate=4.0, gate=0.5, latch=0):
    return [(A + i, v) for i, v in enumerate([on, mode, octs, sync, div, rate, gate, latch])]
BASE = ["wt 0 sine", (L.pid(0, K["fon"]), 0)]
def script_of(cmds, keys, hold, tail, tag):
    s = os.path.join(TMP, tag + ".txt"); o = os.path.join(TMP, tag + ".f32")
    with open(s, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\n")
        for k in keys: f.write("on %d 100\n" % k)
        f.write("run %s\n" % hold)
        for k in keys: f.write("off %d\n" % k)
        f.write("run %s\n" % tail)
    return s, o
def render(cmds, keys, hold=3.0, tail=0.3, tag="x"):
    s, o = script_of(cmds, keys, hold, tail, tag)
    subprocess.run([args.host, s, o], check=True, stderr=subprocess.DEVNULL)
    return np.fromfile(o, dtype=np.float32).reshape(-1, 2)[:, 0]
def events(cmds, keys, hold=3.0, tail=0.2, tag="e"):
    s, o = script_of(cmds, keys, hold, tail, tag)
    r = subprocess.run([args.host, s, o], capture_output=True, text=True)
    return [int(l.split("seq=")[1].split()[0]) * 16 + int(l.split("step=")[1]) for l in r.stderr.splitlines() if l.startswith("seqPos") and "seq=" in l]
def midi_of(x):
    x = x - np.mean(x)
    if np.sqrt(np.mean(x ** 2)) < 0.01: return None
    z = np.where((x[:-1] < 0) & (x[1:] >= 0))[0]
    if len(z) < 8: return None
    return int(round(69 + 12 * np.log2(RATE * (len(z) - 1) / (z[-1] - z[0]) / 440.0)))
rms = lambda x: float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
HG = lambda k: 6700 + k
LF = lambda l, j: 6720 + 5 * l + j
LG = lambda k: 6760 + k
WK = lambda w, j: 6780 + 5 * w + j
CL = lambda c: 6800 + c
AR = lambda mode: arp(mode=mode)

# ---- Hanenbow (13): one leaf, flat, in the middle; one frog, no spread, no randomness in x
off_leaves = [(LF(l, 0), 0) for l in range(8)]
one = off_leaves + [(LF(0, 0), 1), (LF(0, 1), 1.0), (LF(0, 2), 0.5), (LF(0, 3), 0.5), (LF(0, 4), 0), (HG(0), 1), (HG(13), 0), (HG(5), 0), (HG(6), 24), (HG(12), 65), (HG(17), 0), (HG(18), 50), (HG(3), 100)]
evs = events(BASE + AR(13) + one, [48], hold=2.5, tag="h1")
hits_ = [v for v in evs if 3000000 <= v < 4000000]; pos = [v - 4000000 for v in evs if 4000000 <= v < 30000000]
check("Hanenbow: a frog lands on leaf 0", len(hits_) >= 1 and all(h == 3000000 for h in hits_), str(hits_[:5]))
ys = [v & 1023 for v in pos]
check("Hanenbow: frogs are reported, they start at the bottom and rise", len(pos) > 5 and ys[0] > 800 and min(ys) < 700, "%d positions, y %s" % (len(pos), ys[:4]))
a = render(BASE + AR(13) + one, [48], hold=2.5, tag="h2")
check("Hanenbow: the landing plays a note", rms(a[int(0.3 * RATE):int(2.5 * RATE)]) > 0.02)
none = off_leaves + [(HG(0), 3)]
a = render(BASE + AR(13) + none, [48], hold=2.5, tag="h3")
check("Hanenbow: no leaves, no notes", rms(a[int(0.1 * RATE):int(2.5 * RATE)]) < 0.01)
# below the leaf: a leaf above the apex of the jump is never reached; a leaf low in the picture is passed from below (frog goes up through it, lands on it on the way down)
a = render(BASE + AR(13) + one + [(HG(14), 1), (HG(15), 3), (LF(0, 4), 0)], [48], hold=4.0, tag="h4")
# colour change: Hits 1, Step 3 -> the pitch moves on after every landing
evs = events(BASE + AR(13) + one + [(HG(14), 1), (HG(15), 3), (HG(16), 50)], [48], hold=5.5, tag="h5")
cs = [v - 30200000 for v in evs if 30200000 <= v < 30300000]
check("Hanenbow: with Hits 1 the leaf changes colour after every landing (0 -> 1 -> 2 -> 3 -> 0)", len(cs) >= 3 and cs[:4] == [1, 2, 3, 0][:len(cs[:4])], str(cs[:6]))
# the pitch follows: first landing root + degree 0, after a change +3 degrees (pentatonic major: 0,2,4,7,9,12 ..: degree 3 = +7)
a = render(BASE + AR(13) + one + [(HG(8), 100), (HG(14), 1), (HG(15), 3), (HG(0), 1)], [48], hold=3.0, tag="h6")
check("Hanenbow: Rest 100 % is silent", rms(render(BASE + AR(13) + one + [(HG(11), 100)], [48], hold=2.5, tag="h7")[int(0.1 * RATE):int(2.5 * RATE)]) < 0.01)
# a tilted leaf throws the frog sideways: with the angle right (1.0) the second landing / the frog leaves, the x position drifts
evs = events(BASE + AR(13) + one + [(LF(0, 3), 0.2)], [48], hold=2.5, tag="h8")
pos = [v - 4000000 for v in evs if 4000000 <= v < 30000000]; xs = [(v >> 11) & 1023 for v in pos]
check("Hanenbow: a tilted leaf throws the frog to the side", len(xs) > 10 and abs(xs[-1] - xs[0]) > 60 or max(xs) - min(xs) > 60, "x %s .. %s" % (min(xs), max(xs)))
# the leaf is fixed to the stem: it follows Stem X
for stem, want in ((30, True), (90, False)):
    evs = events(BASE + AR(13) + one + [(HG(18), stem), (HG(12), 40)], [48], hold=2.5, tag="hs%d" % stem)
    n = len([v for v in evs if 3000000 <= v < 4000000])
    check("Hanenbow: Stem X %d %% %s the leaf under the launch point" % (stem, "puts" if want else "moves away"), (n >= 1) == want, "%d hits" % n)
# tadpoles only disappear in the water: every one that was reported comes down to y > 0.84 (the surface is at 0.82)
evs = events(BASE + AR(13) + off_leaves + [(HG(0), 1), (HG(13), 0), (HG(12), 50), (HG(17), 0), (HG(3), 60)], [48], hold=2.5, tag="hw")
pos = [v - 4000000 for v in evs if 4000000 <= v < 30000000]; ys = [v & 1023 for v in pos]
check("Hanenbow: the tadpole is reported until it has fallen into the water (y > 0.84)", len(ys) > 20 and max(ys[ys.index(min(ys)):]) > 860, "max y after the apex %s" % (max(ys[ys.index(min(ys)):]) if ys else None))
# Aim 45 degrees: the tadpole leaves the launch leaf to the right
evs = events(BASE + AR(13) + off_leaves + [(HG(0), 1), (HG(13), 0), (HG(12), 10), (HG(17), 45)], [48], hold=2.0, tag="h9")
pos = [v - 4000000 for v in evs if 4000000 <= v < 30000000]; xs = [(v >> 11) & 1023 for v in pos]
check("Hanenbow: Aim 45 launches the tadpole from Spawn X (10 %) to the right", len(xs) > 10 and abs(xs[0] - 102) < 40 and max(xs) > xs[0] + 150, "x %s .. %s" % (xs[0] if xs else None, max(xs) if xs else None))
ys9 = [v & 1023 for v in pos]; dx = xs[3] - xs[0]; dy = ys9[0] - ys9[3]
check("Hanenbow: the picture is wider than tall: a 45 degree launch moves 1.3 x as far in x (in picture fractions) as in y", dy > 20 and 0.8 < dx * 1.3 / dy < 1.25, "dx %d dy %d" % (dx, dy))
evs = events(BASE + AR(13) + off_leaves + [(HG(0), 1), (HG(13), 0), (HG(12), 90), (HG(17), -45)], [48], hold=2.0, tag="h10")
pos = [v - 4000000 for v in evs if 4000000 <= v < 30000000]; xs = [(v >> 11) & 1023 for v in pos]
check("Hanenbow: Aim -45 launches it to the left", len(xs) > 10 and min(xs) < xs[0] - 150, "x %s .. %s" % (xs[0] if xs else None, min(xs) if xs else None))
# ---- Luminaria (14): all walkers off except 0 on a single arrow; every visit plays
LM0 = [(CL(c), 0) for c in range(64)] + [(WK(w, 0), 0) for w in range(4)]
# walker 0 at (0,0) moving right along row 0; an arrow right at (4,0) -> plays every 8 moves (wrap)
W0 = LM0 + [(WK(0, 0), 1), (WK(0, 1), 0), (WK(0, 2), 0), (WK(0, 3), 2), (WK(0, 4), 0), (CL(4), 2), (LG(1), 0), (LG(2), 24), (LG(4), 100)]
evs = events(BASE + AR(14) + W0, [48], hold=2.5, tag="l1")
mv = [v - 30000000 for v in evs if 30000000 <= v < 30100000]
check("Luminaria: the walker moves one cell per step along row 0 and wraps", len(mv) >= 9 and [m % 100 for m in mv[:9]] == [1, 2, 3, 4, 5, 6, 7, 0, 1], str([m % 100 for m in mv[:10]]))
a = render(BASE + AR(14) + W0, [48], hold=2.5, tag="l2")
n = midi_of(a[int((0.05 + 4 * 0.25 + 0.05) * RATE):int((0.05 + 4 * 0.25 + 0.22) * RATE)])
check("Luminaria: the arrow at column 4 plays (chromatic: column 4 of 8 -> degree 4 * 23 / 7 = 13)", n is not None and n == 48 + 13, str(n))
a = render(BASE + AR(14) + LM0 + [(LG(1), 0)], [48], hold=2.0, tag="l3")
check("Luminaria: no walker, no notes", rms(a[int(0.1 * RATE):int(2.0 * RATE)]) < 0.01)
a = render(BASE + AR(14) + W0 + [(LG(7), 100)], [48], hold=2.5, tag="l4")
check("Luminaria: Rest 100 % is silent", rms(a[int(0.1 * RATE):int(2.5 * RATE)]) < 0.01)
# an arrow turns the walker: arrow down at (4,0), arrow left at (4,2): the walker goes right, down two, then left along row 2
T = W0 + [(CL(4), 3), (CL(4 + 16), 4)]
evs = events(BASE + AR(14) + T, [48], hold=3.0, tag="l5")
mv = [(v - 30000000) % 100 for v in evs if 30000000 <= v < 30100000]
check("Luminaria: arrows turn the walker (right to column 4, down to row 2, then left)", mv[:8] == [1, 2, 3, 4, 12, 20, 19, 18], str(mv[:10]))
# Rotate: after a visit the arrow turns clockwise, the editor gets the new direction
R = W0 + [(LG(8), 1)]
evs = events(BASE + AR(14) + R, [48], hold=2.5, tag="l6")
tr = [(v - 30100000) for v in evs if 30100000 <= v < 30200000]
check("Luminaria: Rotate turns the arrow clockwise (right -> down) and reports it", len(tr) >= 1 and tr[0] == 4 * 8 + 3, str(tr[:4]))
# Wrap off: the walker turns round at the wall
evs = events(BASE + AR(14) + W0 + [(LG(10), 0)], [48], hold=3.0, tag="l7")
mv = [(v - 30000000) % 100 for v in evs if 30000000 <= v < 30100000]
check("Luminaria: Wrap off turns the walker round at the wall (... 6, 7, 7, 6 ...)", 7 in mv and mv[mv.index(7):mv.index(7) + 3] == [7, 7, 6], str(mv[:14]))
a = render(BASE + AR(14) + W0, [48], hold=0.6, tail=1.5, tag="l8")
check("Luminaria: stops after the key is released", rms(a[int(1.8 * RATE):]) < 0.01)
print("FAILED" if failures else "ALL OK"); sys.exit(1 if failures else 0)
