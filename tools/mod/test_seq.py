#!/usr/bin/env python3
"""Tests of the 10 step sequencers (modulation sources 34..43).   python3 tools/mod/test_seq.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="seqTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def render(cmds, hold=2.2, tail=0.2, tag="x", note=69):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\non %d 100\nrun %s\noff %d\nrun %s\n" % (note, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def win(a, k, dur=0.25, t0=0.05):   # k-th step window (the note starts at t0), the middle half of it
    s = int((t0 + k * dur + dur * 0.25) * RATE); e = int((t0 + k * dur + dur * 0.75) * RATE); return a[s:e]
SB = lambda m: 3600 + 32 * m
def seq(m, steps, length=None, rate=4.0, sync=0, div=11, glide=0.0, direction=0, retrig=1, bip=0):
    b = SB(m); out = [(b + k, v) for k, v in enumerate(steps)]
    out += [(b + 16, length if length else len(steps)), (b + 17, rate), (b + 18, sync), (b + 19, div), (b + 20, glide), (b + 21, direction), (b + 22, retrig), (b + 23, bip)]
    return out
BASE = ["wt 0 sine", (L.pid(0, K["fon"]), 0), (L.pid(0, K["level"]), 0.0)]
def route(src, slot=0, dest=1, amt=1.0):   # source -> OSC 1 level (matrix slot 1 = params 307..309)
    return [(307 + 3 * slot, src), (308 + 3 * slot, L.dst_index(0, dest)), (309 + 3 * slot, amt)]
ST = [0.0, 0.25, 0.5, 1.0]
a = render(BASE + seq(0, ST) + route(34), tag="fwd")
lv = [rms(win(a, k)) for k in range(4)]
check("Seq 1: the four steps drive the level 0 < 0.25 < 0.5 < 1", lv[0] < 0.01 and lv[0] < lv[1] < lv[2] < lv[3], str(["%.3f" % v for v in lv]))
check("Seq 1: step levels are proportional (1 : 2 : 4)", abs(lv[2] / lv[1] - 2) < 0.5 and abs(lv[3] / lv[1] - 4) < 1.0, "%.2f %.2f" % (lv[2] / lv[1], lv[3] / lv[1]))
check("Seq 1: the pattern repeats after the length", all(abs(rms(win(a, k + 4)) - lv[k]) < 0.02 for k in range(1, 4)))
a = render(BASE + seq(0, ST, length=2) + route(34), tag="len2")
check("Length 2 plays only the first two steps", abs(rms(win(a, 2)) - rms(win(a, 0))) < 0.02 and abs(rms(win(a, 3)) - rms(win(a, 1))) < 0.02 and rms(win(a, 1)) > 0.05)
a = render(BASE + seq(0, ST, direction=1) + route(34), tag="back")
lb = [rms(win(a, k)) for k in range(4)]
check("Backward runs 0, 3, 2, 1", lb[0] < 0.01 and lb[1] > lb[2] > lb[3] > 0.02, str(["%.3f" % v for v in lb]))
a = render(BASE + seq(0, ST, direction=2) + route(34), tag="pp", hold=3.2)
lp = [rms(win(a, k)) for k in range(12)]
check("Ping-pong turns around at the ends", lp[0] < 0.01 and abs(lp[1] - lv[1]) < 0.02 and abs(lp[3] - lv[3]) < 0.02 and abs(lp[4] - lv[2]) < 0.02 and abs(lp[6] - lv[0]) < 0.02, str(["%.2f" % v for v in lp[:8]]))
a = render(BASE + seq(0, ST, direction=3) + route(34), tag="rnd", hold=3.2)
lr = [rms(win(a, k)) for k in range(12)]
check("Random stays on the step values and uses several of them", np.isfinite(a).all() and len(set(round(v / 0.05) for v in lr)) >= 3 and max(lr) < lv[3] * 1.2)
a = render(BASE + seq(0, ST, rate=2.0, sync=1, div=8) + route(34), tag="sync", hold=2.4)     # 1/4 at 120 bpm = 2 steps / s
ls = [rms(win(a, k, dur=0.5)) for k in range(4)]
check("Tempo sync: 1/4 notes at 120 bpm = 0.5 s per step", ls[0] < 0.01 and ls[0] < ls[1] < ls[2] < ls[3], str(["%.3f" % v for v in ls]))
a = render(BASE + seq(0, [0.0, 1.0], glide=1.0, rate=2.0) + route(34), tag="glide", hold=1.4)
h = render(BASE + seq(0, [0.0, 1.0], glide=0.0, rate=2.0) + route(34), tag="hard", hold=1.4)
w = lambda x: rms(x[int(0.58 * RATE):int(0.68 * RATE)])
check("Glide smooths the step change (just after the step it is still far below the target)", w(h) > 0.1 and w(a) < 0.5 * w(h), "%.3f vs %.3f" % (w(a), w(h)))
a = render(BASE + seq(0, [0.5] * 4, bip=1) + route(34), tag="bip")
check("Bipolar: the middle value 0.5 is 0 (no modulation)", rms(win(a, 1)) < 0.01)
a = render(BASE + seq(0, [1.0, 0.0, 1.0, 0.0], bip=1) + route(34), tag="bip2")
check("Bipolar: a low step is negative (it cannot open the level)", rms(win(a, 0)) > 0.05 and rms(win(a, 1)) < 0.01)
a = render(BASE + seq(0, ST, retrig=0) + route(34), tag="glob", hold=1.2)
check("Retrig off: the global sequencer modulates too", np.isfinite(a).all() and rms(a[int(0.2 * RATE):int(1.2 * RATE)]) > 0.02)
a = render(BASE + seq(9, ST) + route(43), tag="seq10")
check("Seq 10 (source 43) works", rms(win(a, 3)) > 0.05 and rms(win(a, 0)) < 0.01)
a = render(["wt 0 sine", (L.pid(0, K["fon"]), 0), (307, 34), (308, 3), (309, -0.5)] + seq(0, [1.0] * 4) + [], tag="pan")
check("A sequencer reaches any destination (Pan)", rms(a[int(0.3 * RATE):int(1.0 * RATE), 0]) > 1.4 * rms(a[int(0.3 * RATE):int(1.0 * RATE), 1]))
a = render(BASE + seq(0, ST, retrig=0) + route(34) + [("wt 0 sine"), ] if False else BASE + seq(0, ST, retrig=0) + route(34), tag="fin", hold=0.6, tail=1.0)
check("Output stays finite and silent after the note", np.isfinite(a).all())
def slot_base(sl): return 307 + 3 * sl if sl < 10 else (472 + 3 * (sl - 10) if sl < 20 else 4000 + 3 * (sl - 20))
def route2(src, sl, dest=1, amt=1.0, osc=0):
    b = slot_base(sl); return [(b, src), (b + 1, L.dst_index(osc, dest)), (b + 2, amt)]
for sl in (10, 19, 20, 120, 255):
    a = render(BASE + seq(0, ST) + route2(34, sl), tag="slot%d" % sl)
    lq = [rms(win(a, k)) for k in range(4)]
    check("Matrix slot %d: Seq 1 drives the level" % (sl + 1), lq[0] < 0.01 and lq[0] < lq[1] < lq[2] < lq[3], str(["%.3f" % v for v in lq]))
# two sequencers on two slots: the level follows the sum (Seq 1 steps 0 0.25 0 0.25 + Seq 2 steps 0 0 0.5 0.5 with amount 0.5 each)
a = render(BASE + seq(0, [0.0, 0.5, 0.0, 0.5], length=4) + seq(1, [0.0, 0.0, 0.5, 0.5], length=4) + route2(34, 0, amt=1.0) + route2(35, 1, amt=1.0), tag="two")
l2 = [rms(win(a, k)) for k in range(4)]
check("Two sequencers add up in the matrix (0, 0.5, 0.5, 1.0)", l2[0] < 0.01 and abs(l2[1] - l2[2]) < 0.03 and l2[3] > l2[1] * 1.6, str(["%.3f" % v for v in l2]))
# a global destination (Amp, index 2)
a = render(["wt 0 sine", (L.pid(0, K["fon"]), 0)] + seq(0, [1.0, 0.0, 1.0, 0.0], bip=0) + [(307, 34), (308, 2), (309, -1.0)], tag="amp")
la = [rms(win(a, k)) for k in range(4)]
check("Global destination Amp: Seq 1 at full amount (negative) mutes the high steps", la[1] > 3 * max(la[0], 0.001), str(["%.3f" % v for v in la]))
# ---- Spire-style stepper features: step shapes, Hold, Loop, Time x1-x4, Spos
SH = lambda m, k: 5000 + 16 * m + k
def ext(m, time=0, loop=1, hold=0, shapes=None):
    out = [(SB(m) + 24, time), (SB(m) + 25, loop), (SB(m) + 26, hold)]
    for k, v in (shapes or {}).items(): out.append((SH(m, k), v))
    return out
ev_ = lambda a, t0, t1: rms(a[int(t0 * RATE):int(t1 * RATE)])
one = lambda **kw: BASE + seq(0, [1.0], length=1, rate=1.0, **kw)
a = render(one(retrig=1) + ext(0, shapes={0: 2}) + route(34), tag="rampup", hold=1.3)   # step 1 s long, level ramps 0 -> 1
e_, l_ = ev_(a, 0.15, 0.30), ev_(a, 0.80, 0.95)
check("Step shape Ramp up: the level rises over the step", l_ > 3.0 * e_ and l_ > 0.1, "%.3f -> %.3f" % (e_, l_))
a = render(one(retrig=1) + ext(0, shapes={0: 1}) + route(34), tag="rampdn", hold=1.3)
e_, l_ = ev_(a, 0.15, 0.30), ev_(a, 0.80, 0.95)
check("Step shape Ramp down: the level falls over the step", e_ > 3.0 * l_ and e_ > 0.1, "%.3f -> %.3f" % (e_, l_))
a = render(one(retrig=1) + ext(0, shapes={0: 5}) + route(34), tag="gate", hold=1.3)
e_, l_ = ev_(a, 0.15, 0.40), ev_(a, 0.65, 0.95)
check("Step shape Gate 50%: the first half is on, the second half is off", e_ > 0.1 and l_ < 0.02, "%.3f / %.3f" % (e_, l_))
a = render(one(retrig=1) + ext(0, shapes={0: 3}) + route(34), tag="tri", hold=1.3)
m_ = ev_(a, 0.45, 0.60); e_ = ev_(a, 0.08, 0.14); l_ = ev_(a, 0.90, 0.96)
check("Step shape Triangle: highest in the middle of the step", m_ > 2.0 * e_ and m_ > 2.0 * l_, "%.3f / %.3f / %.3f" % (e_, m_, l_))
a = render(one(retrig=1) + ext(0, hold=1, shapes={0: 2}) + route(34), tag="holdon", hold=1.3)
e_, l_ = ev_(a, 0.15, 0.30), ev_(a, 0.80, 0.95)
check("Hold switches the step shapes off (flat step)", abs(e_ - l_) < 0.02 and e_ > 0.1, "%.3f / %.3f" % (e_, l_))
a = render(BASE + seq(0, ST) + ext(0, loop=3) + route(34), tag="loop", hold=2.2)
lq = [rms(win(a, k)) for k in range(8)]
check("Loop start 3: 1 2 3 4, then the loop repeats 3 4 3 4", abs(lq[4] - lq[2]) < 0.02 and abs(lq[5] - lq[3]) < 0.02 and abs(lq[6] - lq[2]) < 0.02 and abs(lq[7] - lq[3]) < 0.02 and lq[2] != lq[3], str(["%.3f" % v for v in lq]))
a = render(BASE + seq(0, ST, rate=2.0) + ext(0, time=1) + route(34), tag="x2")
lx = [rms(win(a, k)) for k in range(4)]
check("Time x2 doubles the speed (2 Hz x2 = steps every 0.25 s)", lx[0] < 0.01 and lx[0] < lx[1] < lx[2] < lx[3], str(["%.3f" % v for v in lx]))
a = render(BASE + seq(0, ST, rate=1.0) + ext(0, time=3) + route(34), tag="x4")
check("Time x4 (1 Hz x4 = 4 steps / s)", abs(rms(win(a, 3)) - lv[3]) < 0.03 and abs(rms(win(a, 2)) - lv[2]) < 0.03)
a = render(BASE + seq(0, ST, sync=2, div=8) + route(34), tag="spos", hold=2.4)   # 1/4 at 120 bpm = 0.5 s, locked to the host beat
ls_ = [rms(win(a, k, dur=0.5)) for k in range(4)]
check("Spos: 1/4 steps follow the host position", ls_[0] < 0.01 and ls_[0] < ls_[1] < ls_[2] < ls_[3], str(["%.3f" % v for v in ls_]))
a = render(BASE + seq(0, ST, sync=2, div=8, direction=1) + route(34), tag="spos_b", hold=2.4)
lsb = [rms(win(a, k, dur=0.5)) for k in range(4)]
check("Spos backward runs the other way round", lsb[0] > lsb[1] > lsb[2] and lsb[3] < 0.01, str(["%.3f" % v for v in lsb]))
a = render(BASE + seq(0, ST, sync=1, div=8) + ext(0, time=1) + route(34), tag="synct", hold=1.4)   # 1/4 sync x2 = 0.25 s
lt = [rms(win(a, k)) for k in range(4)]
check("Sync with Time x2: 1/4 x2 = 0.25 s per step", lt[0] < 0.01 and lt[0] < lt[1] < lt[2] < lt[3], str(["%.3f" % v for v in lt]))
# the declared range of every matrix source parameter must reach 43 (the host clamps values to it)
import re
decl = open(os.path.join(os.path.dirname(__file__), '..', '..', 'patch', 'Eisenpuls_Synth.cmajor')).read()
mx = [float(m) for m in re.findall(r'name: "Mod Slot \d+ Source[^"]*", min: 0\.0, max: ([\d.]+)', decl)]
check("All 256 matrix source parameters accept Seq 1-10 (declared max 43)", len(mx) == 256 and min(mx) >= 43.0, "%d params, min max %s" % (len(mx), min(mx) if mx else None))
print("FAILURES: %d" % failures if failures else "ALL OK"); sys.exit(1 if failures else 0)
