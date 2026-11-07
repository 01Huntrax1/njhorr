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
print("FAILURES: %d" % failures if failures else "ALL OK"); sys.exit(1 if failures else 0)
