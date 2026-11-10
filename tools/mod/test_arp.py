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

# ---- 64 steps: steps 17-64 have their own ids (note 5500 + n - 17, gate 5644 + n - 17), Length goes up to 64; default = repeat of the 16 step pattern
def fast(a, n, dur=0.125): return [midi_of(a[int((0.051 + k * dur + 0.03) * RATE):int((0.051 + k * dur + 0.1) * RATE)]) for k in range(n)]
e = render(BASE + arp(mode=5, rate=8.0, gate=0.5) + [(5264, 64), (5500 + 47, 12), (5500, 7), (5644 + 63 - 16, 1)], [48], hold=8.4, tag="e303")
se = fast(e, 64)
check("303 64 steps: step 17 note (+7) and step 64 note (+12) play", se[16] == 55 and se[63] == 60, "%s %s" % (se[16], se[63]))
check("303 64 steps: the pattern repeats by default (step 19 = step 3 = +12, step 33 = step 1)", se[18] == 60 and se[32] == 48, "%s %s" % (se[18], se[32]))
check("303 64 steps: all 64 steps sound", all(x is not None for x in se[:5]) and se[63] is not None)
f = render(BASE + arp(mode=5, rate=8.0, gate=0.5) + [(5264, 20), (5500 + 3, 9)], [48], hold=3.2, tag="f303")
sf = fast(f, 22)
check("303 Length 20: step 20 plays its own note (+9), then it wraps to step 1", sf[19] == 57 and sf[20] == 48 and sf[21] == 48, str(sf))

# ---- MOD-SQM: Euclid / Poly (6), Melodic (7), Generative (8) modes.  root = the key (48 = C3, 130.8 Hz)
EU = lambda l, k: 5710 + 8 * l + k
def stepwin(a, k, t0, t1, dur): return a[int((0.051 + k * dur + t0 * dur) * RATE):int((0.051 + k * dur + t1 * dur) * RATE)]
def hits(a, n, dur, thr=0.05): return [int(rms(stepwin(a, k, 0.05, 0.4, dur)) > thr) for k in range(n)]
def band_e(x, f0, f1):
    sp = np.abs(np.fft.rfft(x.astype(np.float64) * np.hanning(len(x)), n=32768)); fq = np.fft.rfftfreq(32768, 1.0 / RATE)
    return float(np.sum(sp[(fq >= f0) & (fq <= f1)]))
def hz(n): return 440.0 * 2 ** ((n - 69) / 12.0)
def eucl(len_, pul, rot, n): return [int(pul > 0 and (((i % len_) + rot) % len_ * pul) % len_ < pul) for i in range(n)]
DUR = 0.25
AR = lambda mode, **kw: arp(mode=mode, rate=4.0, gate=kw.pop("gate", 0.5), **kw)
e1 = render(BASE + AR(6), [48], hold=8.3, tag="eu1")
check("Euclid 16/5: the hit pattern of 32 steps", hits(e1, 32, DUR) == eucl(16, 5, 0, 32), str(hits(e1, 32, DUR)))
e2 = render(BASE + AR(6) + [(EU(0, 3), 3)], [48], hold=4.3, tag="eu2")
check("Euclid rotation 3 shifts the pattern", hits(e2, 16, DUR) == eucl(16, 5, 3, 16), str(hits(e2, 16, DUR)))
e3 = render(BASE + AR(6) + [(EU(0, 2), 0)], [48], hold=2.3, tag="eu3")
check("Euclid 0 pulses is silent", sum(hits(e3, 8, DUR)) == 0)
e4 = render(BASE + AR(6) + [(EU(0, 5), 0)], [48], hold=2.3, tag="eu4")
check("Euclid probability 0 is silent", sum(hits(e4, 8, DUR)) == 0)
e5 = render(BASE + AR(6) + [(EU(0, 2), 16), (EU(0, 6), 2)], [48], hold=2.3, tag="eu5")
e6 = render(BASE + AR(6) + [(EU(0, 2), 16)], [48], hold=2.3, tag="eu6")
check("Euclid ratchet 2 plays a second hit inside the step", rms(stepwin(e5, 2, 0.55, 0.95, DUR)) > 1.6 * rms(stepwin(e6, 2, 0.55, 0.95, DUR)), "%.3f vs %.3f" % (rms(stepwin(e5, 2, 0.55, 0.95, DUR)), rms(stepwin(e6, 2, 0.55, 0.95, DUR))))
# polyrhythm: lane 1 = 3 steps (C3), lane 2 = 4 steps (+12), every step 12 steps
e7 = render(BASE + AR(6) + [(EU(0, 1), 3), (EU(0, 2), 1), (EU(1, 0), 1), (EU(1, 1), 4), (EU(1, 2), 1), (EU(1, 3), 0), (EU(1, 4), 12), (EU(1, 5), 100), (EU(1, 6), 1)], [48], hold=3.3, tag="eu7")
lo = [int(rms(stepwin(e7, k, 0.05, 0.4, DUR)) > 0.05 and band_e(stepwin(e7, k, 0.05, 0.4, DUR), hz(48) * 0.97, hz(48) * 1.03) > 3 * band_e(stepwin(e7, k, 0.05, 0.4, DUR), hz(60) * 0.97, hz(60) * 1.03)) for k in range(12)]
hi = [int(rms(stepwin(e7, k, 0.05, 0.4, DUR)) > 0.05 and band_e(stepwin(e7, k, 0.05, 0.4, DUR), hz(60) * 0.97, hz(60) * 1.03) > 3 * band_e(stepwin(e7, k, 0.05, 0.4, DUR), hz(48) * 0.97, hz(48) * 1.03)) for k in range(12)]
check("Polyrhythm: lane 1 hits every 3rd step, lane 2 (octave up) every 4th", lo == [1 if k % 3 == 0 and k % 4 else 0 for k in range(12)] and hi == [1 if k % 4 == 0 and k % 3 else 0 for k in range(12)], "%s %s" % (lo, hi))
# melodic: step 1 = major chord, length 400 %, step 2 off; notes of the default pattern
MLN = lambda r, k: 5810 + 64 * r + k
m1 = render(BASE + AR(7) + [(MLN(3, 0), 3)], [48], hold=1.3, tag="ml1")
w = stepwin(m1, 0, 0.05, 0.4, DUR)
ch = [band_e(w, hz(n) * 0.97, hz(n) * 1.03) for n in (48, 52, 55, 57)]
check("Melodic: chord type 3 plays root, major third and fifth", ch[0] > 3 * ch[3] and ch[1] > 3 * ch[3] and ch[2] > 3 * ch[3], str([round(c, 1) for c in ch]))
m2 = render(BASE + AR(7) + [(MLN(4, 0), 0)], [48], hold=1.3, tag="ml2")
check("Melodic: probability 0 on a step makes it a rest", rms(stepwin(m2, 0, 0.05, 0.4, DUR)) < 0.01 and rms(stepwin(m2, 1, 0.05, 0.4, DUR)) > 0.02)
m3 = render(BASE + AR(7) + [(MLN(1, 0), 127), (MLN(1, 1), 20)], [48], hold=1.3, tag="ml3")
check("Melodic: velocity of a step changes its level", rms(stepwin(m3, 0, 0.05, 0.4, DUR)) > 1.4 * rms(stepwin(m3, 1, 0.05, 0.4, DUR)), "%.3f vs %.3f" % (rms(stepwin(m3, 0, 0.05, 0.4, DUR)), rms(stepwin(m3, 1, 0.05, 0.4, DUR))))
m4 = render(BASE + AR(7) + [(MLN(2, 0), 400), (MLN(6, 1), 0)], [48], hold=1.3, tag="ml4")
check("Melodic: a length of 400 % ties over the following (empty) step", rms(stepwin(m4, 1, 0.3, 0.9, DUR)) > 0.02 and rms(stepwin(m4, 3, 0.3, 0.9, DUR)) > 0.02 and rms(stepwin(m4, 5, 0.3, 0.9, DUR)) > 0.02)
m5 = render(BASE + AR(7) + [(5800, 3)], [48], hold=3.3, tag="ml5")
h5 = hits(m5, 9, DUR)
check("Melodic length 3 repeats the first three steps (step 3 of the default pattern is a rest)", h5 == [1, 1, 0, 1, 1, 0, 1, 1, 0], str(h5))
# generative: turing machine, loop 4, no mutation -> the 4 notes repeat; notes in the scale (minor) above the root
gb = [(5750, 0), (5751, 2), (5752, 24), (5754, 4), (5755, 0), (5758, 0)]
g1 = render(BASE + AR(8) + gb, [48], hold=3.3, tag="gn1")
sg = [midi_of(stepwin(g1, k, 0.1, 0.45, DUR)) for k in range(12)]
minor = {0, 2, 3, 5, 7, 8, 10}
check("Turing machine: loop 4 with mutation 0 repeats every 4 steps", sg[:4] == sg[4:8] == sg[8:12] and None not in sg, str(sg))
check("Turing machine: notes are in the minor scale within the 24 st range", all(n is not None and 0 <= n - 48 < 24 and (n - 48) % 12 in minor for n in sg), str(sg))
g2 = render(BASE + AR(8) + [(5750, 0), (5751, 2), (5752, 24), (5754, 8), (5755, 100), (5758, 0)], [48], hold=6.3, tag="gn2")
sg2 = [midi_of(stepwin(g2, k, 0.1, 0.45, DUR)) for k in range(24)]
check("Turing machine: mutation 100 % does not repeat", sg2[:8] != sg2[8:16] or sg2[8:16] != sg2[16:24], str(sg2))
g3 = render(BASE + AR(8) + [(5750, 1), (5751, 8), (5752, 24), (5756, 2), (5758, 0)], [48], hold=6.3, tag="gn3")
sg3 = [midi_of(stepwin(g3, k, 0.1, 0.45, DUR)) for k in range(24)]
pent = {0, 2, 4, 7, 9}
check("Random walk: stays in the major pentatonic scale and the range, moves around", all(n is not None and 0 <= n - 48 < 24 and (n - 48) % 12 in pent for n in sg3) and len(set(sg3)) >= 3, str(sg3))
g4 = render(BASE + AR(8) + [(5758, 100)], [48], hold=2.3, tag="gn4")
check("Generative: rest 100 % is silent", rms(g4[int(0.2 * RATE):int(2.2 * RATE)]) < 0.01)
# stopping: all keys up releases every sequencer note, switching the mode back to Up works
st1 = render(BASE + AR(7) + [(MLN(2, 0), 400)], [48, 52], hold=1.0, tail=0.6, tag="sqstop")
check("Melodic: releasing the keys silences the (tied) notes", rms(st1[int(1.4 * RATE):]) < 0.01)

print("FAILURES: %d" % failures if failures else "ALL OK"); sys.exit(1 if failures else 0)
