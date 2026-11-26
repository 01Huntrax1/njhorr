#!/usr/bin/env python3
"""Tests of the Plinko / Bounce / Cellular arpeggiator modes (Arp Mode 9..11, tools/mod/build_plinko.py).   python3 tools/mod/test_plinko.py --host <dsp_host>   (build the host with -DSEQPOS_LOG for the ball events)"""
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
rms = lambda x: float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
def stepwin(a, k, t0, t1, dur): return a[int((0.051 + k * dur + t0 * dur) * RATE):int((0.051 + k * dur + t1 * dur) * RATE)]
def hits(a, n, dur, thr=0.05): return [int(rms(stepwin(a, k, 0.05, 0.4, dur)) > thr) for k in range(n)]
def band_e(x, f0, f1):
    sp = np.abs(np.fft.rfft(x.astype(np.float64) * np.hanning(len(x)), n=32768)); fq = np.fft.rfftfreq(32768, 1.0 / RATE)
    return float(np.sum(sp[(fq >= f0) & (fq <= f1)]))
def hz(n): return 440.0 * 2 ** ((n - 69) / 12.0)
DUR = 0.25
AR = lambda mode, **kw: arp(mode=mode, rate=4.0, gate=kw.pop("gate", 0.5), **kw)
PK = lambda k: 6300 + k
BK = lambda k: 6320 + k
CK = lambda k: 6340 + k
note = lambda a, k: midi_of(stepwin(a, k, 0.1, 0.45, DUR))
# ---- Plinko (mode 9): root = the key (48)
P0 = [(PK(1), 0), (PK(2), 24), (PK(0), 4), (PK(8), 100)]       # chromatic, range 24, 4 rows, gate 100 %
a = render(BASE + AR(9) + P0 + [(PK(5), 100)], [48], hold=3.3, tag="pk1")
n1 = [note(a, k) for k in range(12)]
check("Plinko: Bias +100 drops the balls into the last bin (root + 23)", sum(1 for n in n1 if n == 48 + 23) >= 8, str(n1))
a = render(BASE + AR(9) + P0 + [(PK(5), -100)], [48], hold=3.3, tag="pk2")
n2 = [note(a, k) for k in range(12)]
check("Plinko: Bias -100 drops them into the first bin (root)", sum(1 for n in n2 if n == 48) >= 8, str(n2))
a = render(BASE + AR(9) + [(PK(1), 0), (PK(2), 24), (PK(0), 8), (PK(8), 100), (PK(13), 5), (PK(9), 4)], [48], hold=4.3, tag="pk3")
n3 = [note(a, k) for k in range(16)]
check("Plinko: Seed 5 with Loop 4 repeats the same four balls", n3[:4] == n3[4:8] == n3[8:12] == n3[12:16] and None not in n3 and len(set(n3[:4])) >= 2, str(n3))
a = render(BASE + AR(9) + [(PK(1), 0), (PK(2), 24), (PK(0), 8), (PK(8), 100)], [48], hold=6.3, tag="pk4")
n4 = [note(a, k) for k in range(24)]
check("Plinko: random balls spread over several bins, all above the root and inside the range", len(set(n4)) >= 3 and all(n is not None and 48 <= n < 72 for n in n4), str(n4))
a = render(BASE + AR(9) + P0 + [(PK(5), -100), (PK(10), 3)], [48], hold=1.3, tag="pk5")
w = stepwin(a, 0, 0.1, 0.45, DUR); ch = [band_e(w, hz(n) * 0.97, hz(n) * 1.03) for n in (48, 52, 55, 50)]
check("Plinko: Chord Major stacks third and fifth on the ball", ch[0] > 2.5 * ch[3] and ch[1] > 2.5 * ch[3] and ch[2] > 2.5 * ch[3], str([round(c, 1) for c in ch]))
a = render(BASE + AR(9) + P0 + [(PK(12), 100)], [48], hold=2.3, tag="pk6")
check("Plinko: Rest 100 % is silent", rms(a[int(0.2 * RATE):int(2.2 * RATE)]) < 0.01)
a = render(BASE + AR(9) + P0 + [(PK(7), 3), (PK(5), -100)], [48], hold=1.3, tag="pk7"); b = render(BASE + AR(9) + P0 + [(PK(5), -100)], [48], hold=1.3, tag="pk8")
check("Plinko: three balls per step are louder than one", rms(stepwin(a, 1, 0.05, 0.95, DUR)) > 1.15 * rms(stepwin(b, 1, 0.05, 0.95, DUR)), "%.3f vs %.3f" % (rms(stepwin(a, 1, 0.05, 0.95, DUR)), rms(stepwin(b, 1, 0.05, 0.95, DUR))))
# the editor gets every ball: seqPos = 2000000 + bin + 16 * rows + 256 * path  (the host logs v / 16 and v % 16)
script = os.path.join(TMP, "ev.txt"); out = os.path.join(TMP, "ev.f32")
with open(script, "w") as f:
    for c in BASE + AR(9) + [(PK(0), 6), (PK(1), 0), (PK(2), 24), (PK(5), 100)]: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
    f.write("run 0.05\non 48 100\nrun 1.3\noff 48\nrun 0.2\n")
r = subprocess.run([args.host, script, out], capture_output=True, text=True)
evs = [int(l.split("seq=")[1].split()[0]) * 16 + int(l.split("step=")[1]) for l in r.stderr.splitlines() if l.startswith("seqPos") and "seq=" in l]
evs = [v for v in evs if v >= 2000000]
dec = [(v - 2000000) % 16 for v in evs]; rws = [((v - 2000000) // 16) % 16 for v in evs]; paths = [(v - 2000000) // 256 for v in evs]
check("Plinko: one ball event per step (5 steps in 1.3 s), 6 rows", 4 <= len(evs) <= 7 and all(x == 6 for x in rws), str(evs))
check("Plinko: the bin is the number of right moves of the path", all(bin(p).count("1") == b for p, b in zip(paths, dec)), str(list(zip(paths, dec))))
# ---- Bounce (mode 10)
a = render(BASE + AR(10) + [(BK(0), 100), (BK(1), 98), (BK(2), 2), (BK(3), 0), (BK(8), 2), (BK(9), 100), (BK(4), 0)], [48], hold=2.3, tag="bn1")
h = hits(a, 8, DUR)
check("Bounce: 2 bounces, pause 2: the pattern 1 1 0 0 repeats", h == [1, 1, 0, 0, 1, 1, 0, 0], str(h))
a = render(BASE + AR(10) + [(BK(0), 100), (BK(1), 98), (BK(2), 4), (BK(3), 2), (BK(8), 0), (BK(9), 100), (BK(4), 0), (BK(5), 24)], [48], hold=1.3, tag="bn2")
nb = [note(a, k) for k in range(4)]
check("Bounce: Pitch Step 2 walks up the scale: root, +2, +4, +6", nb == [48, 50, 52, 54], str(nb))
a = render(BASE + AR(10) + [(BK(0), 100), (BK(1), 98), (BK(2), 4), (BK(3), 1), (BK(8), 0), (BK(9), 100), (BK(4), 0), (BK(13), 1)], [48], hold=1.3, tag="bn3")
nb = [note(a, k) for k in range(3)]
check("Bounce: Direction Down starts at the top of the range and goes down", nb[0] is not None and nb[0] > 48 + 12 and nb[1] == nb[0] - 1 and nb[2] == nb[0] - 2, str(nb))
a = render(BASE + AR(10) + [(BK(0), 100), (BK(1), 98), (BK(2), 2), (BK(8), 0), (BK(12), 100)], [48], hold=1.3, tag="bn4")
check("Bounce: Rest 100 % is silent", rms(a[int(0.2 * RATE):int(1.2 * RATE)]) < 0.01)
# ---- Cellular (mode 11): rule 0 kills every cell, so the centre cell is re-seeded each step (cell 4 of 8 -> degree 13 of 24 chromatic)
CB = [(CK(1), 8), (CK(2), 0), (CK(3), 24), (CK(5), 0), (CK(6), 100), (CK(9), 0)]
a = render(BASE + AR(11) + CB + [(CK(0), 0)], [48], hold=1.3, tag="ce1")
nc = [note(a, k) for k in range(4)]
check("Cellular: rule 0 plays the re-seeded centre cell (root + 13) every step", nc == [61, 61, 61, 61], str(nc))
a = render(BASE + AR(11) + CB + [(CK(0), 255), (CK(8), 8)], [48], hold=1.3, tag="ce2"); b = render(BASE + AR(11) + CB + [(CK(0), 255), (CK(8), 1)], [48], hold=1.3, tag="ce3")
check("Cellular: rule 255 fills the row, Max Notes 8 is louder than Max Notes 1", rms(stepwin(a, 2, 0.05, 0.95, DUR)) > 1.3 * rms(stepwin(b, 2, 0.05, 0.95, DUR)), "%.3f vs %.3f" % (rms(stepwin(a, 2, 0.05, 0.95, DUR)), rms(stepwin(b, 2, 0.05, 0.95, DUR))))
a = render(BASE + AR(11) + CB + [(CK(0), 90), (CK(9), 100)], [48], hold=1.3, tag="ce4")
check("Cellular: Rest 100 % is silent", rms(a[int(0.2 * RATE):int(1.2 * RATE)]) < 0.01)
a = render(BASE + AR(11) + CB + [(CK(0), 90)], [48], hold=4.3, tag="ce5")
h = hits(a, 16, DUR)
check("Cellular: rule 90 keeps playing (a Sierpinski pattern, never silent)", sum(h) >= 14 and np.isfinite(a).all(), str(h))
a = render(BASE + AR(11) + CB, [48], hold=0.6, tail=1.5, tag="ce6")
check("Cellular: stops after the keys are released", rms(a[int(1.8 * RATE):]) < 0.01)

# ---- Plinko physics board (mode 12): a single horizontal line across the board (obstacle 1), all default pegs removed
PG = lambda k: 6360 + k
OB = lambda e, j: 6400 + 6 * e + j
clear = [(OB(e, 0), 0) for e in range(48)]
line = [(OB(0, 0), 2), (OB(0, 1), 0.0), (OB(0, 2), 0.5), (OB(0, 3), 1.0), (OB(0, 4), 0.5), (OB(0, 5), 0)]
B0 = clear + line + [(PG(0), 1), (PG(13), 0), (PG(5), 9), (PG(6), 24)]   # 1 ball, no spread, pentatonic minor over 24 st
a = render(BASE + AR(12, ) + B0 + [(PG(12), 50)], [48], hold=3.0, tail=0.3, tag="pp1")
check("Plinko board: silent while the ball falls (0.1 .. 0.8 s)", rms(a[int(0.1 * RATE):int(0.8 * RATE)]) < 0.01, "%.4f" % rms(a[int(0.1 * RATE):int(0.8 * RATE)]))
check("Plinko board: the ball hits the line at about 1.0 s and a note sounds", rms(a[int(1.0 * RATE):int(1.5 * RATE)]) > 0.02, "%.4f" % rms(a[int(1.0 * RATE):int(1.5 * RATE)]))
n = midi_of(a[int(1.06 * RATE):int(1.26 * RATE)])
check("Plinko board: a hit in the middle of the board plays a middle scale degree (root + 10 .. 15, the ball drifts a little)", n is not None and 58 <= n <= 63, str(n))
lo = midi_of(render(BASE + AR(12) + B0 + [(PG(12), 0)], [48], hold=2.0, tail=0.2, tag="pp2")[int(1.06 * RATE):int(1.26 * RATE)])
hi = midi_of(render(BASE + AR(12) + B0 + [(PG(12), 100)], [48], hold=2.0, tail=0.2, tag="pp3")[int(1.06 * RATE):int(1.26 * RATE)])
check("Plinko board: the pitch follows the x position (left low, right high)", lo is not None and hi is not None and lo <= 50 and hi >= 68, "%s / %s" % (lo, hi))
a = render(BASE + AR(12) + clear + [(PG(0), 3)], [48], hold=2.5, tail=0.3, tag="pp4")
check("Plinko board: an empty board is silent", rms(a[int(0.1 * RATE):int(2.5 * RATE)]) < 0.01)
a = render(BASE + AR(12) + B0 + [(PG(12), 50), (PG(11), 100)], [48], hold=2.5, tail=0.3, tag="pp5")
check("Plinko board: Rest 100 % is silent", rms(a[int(0.1 * RATE):int(2.5 * RATE)]) < 0.01)
fast = render(BASE + AR(12) + B0 + [(PG(12), 50), (PG(1), 300)], [48], hold=1.6, tail=0.2, tag="pp6")
check("Plinko board: Speed 300 % makes the ball arrive after about 0.35 s", rms(fast[int(0.1 * RATE):int(0.3 * RATE)]) < 0.01 and rms(fast[int(0.45 * RATE):int(0.8 * RATE)]) > 0.02)
# the editor gets hits (3000000 + obstacle) and ball positions (4000000 + (ball << 21 | x << 11 | y))
script = os.path.join(TMP, "ev2.txt"); out = os.path.join(TMP, "ev2.f32")
with open(script, "w") as f:
    for c in BASE + AR(12) + B0 + [(PG(12), 50)]: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
    f.write("run 0.05\non 48 100\nrun 1.6\noff 48\nrun 0.2\n")
r = subprocess.run([args.host, script, out], capture_output=True, text=True)
evs = [int(l.split("seq=")[1].split()[0]) * 16 + int(l.split("step=")[1]) for l in r.stderr.splitlines() if l.startswith("seqPos") and "seq=" in l]
hits_ = [v for v in evs if 3000000 <= v < 4000000]; pos = [v - 4000000 for v in evs if v >= 4000000]
check("Plinko board: obstacle 0 reports its hit", len(hits_) >= 1 and hits_[0] == 3000000, str(hits_[:4]))
xs = [(v >> 11) & 1023 for v in pos]; ys = [v & 1023 for v in pos]
check("Plinko board: ball positions fall from the top at x = 0.5", len(pos) > 10 and ys[0] < 200 and abs(xs[0] - 512) < 30 and max(ys) > 480, "%d positions, y %s" % (len(pos), ys[:3]))
print("FAILED" if failures else "ALL OK"); sys.exit(1 if failures else 0)
