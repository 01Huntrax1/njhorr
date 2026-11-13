#!/usr/bin/env python3
"""Tests of the MSEG mode of the 10 modulation envelopes (params 7200 + 30 * e, source 11 + e).
python3 tools/mod/test_mseg.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="msegTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def render(cmds, hold=1.0, tail=1.0, tag="x", note=69):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\non %d 100\nrun %s\noff %d\nrun %s\n" % (note, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def at(a, t, w=0.02):   # rms around time t (t counted from the start of the note)
    s = int((0.05 + t) * RATE); return rms(a[s:s + int(w * RATE)])
BASE = [(21, 4000.0), "wt 0 sine", (L.pid(0, K["fon"]), 0), (L.pid(0, K["level"]), 0.0)]
def route(src, slot=0, dest=1, amt=1.0): return [(307 + 3 * slot, src), (308 + 3 * slot, L.dst_index(0, dest)), (309 + 3 * slot, amt)]
def mseg(e, nodes, sus=0, loop=None, mode=1):
    b = 7200 + 30 * e
    out = [(b, mode), (b + 1, len(nodes)), (b + 2, sus), (b + 3, 1 if loop else 0)]
    if loop: out += [(b + 4, loop[0]), (b + 5, loop[1])]
    for k, (t, l, c) in enumerate(nodes): out += [(b + 6 + 3 * k, t), (b + 7 + 3 * k, l), (b + 8 + 3 * k, c)]
    return out
R = route(11)
# ADSR mode (default) keeps working: A 10 ms, S 0.5 -> a steady tone while held, gone after release
a = render(BASE + R, tag="adsr")
check("ADSR mode (default / old presets): tone while held, silent after release", at(a, 0.8) > 0.02 and at(a, 1.9) < 0.1 * at(a, 0.8), "%.3f %.3f" % (at(a, 0.8), at(a, 1.9)))
# MSEG with sustain: up in 100 ms, down to 0.5 in 100 ms, hold, release 3rd node in 200 ms
n = [(100, 1.0, 0), (100, 0.5, 0), (200, 0.0, 0)]
a = render(BASE + R + mseg(0, n, sus=2), tag="sus")
pk, hd = at(a, 0.1), at(a, 0.7)
check("MSEG: peak at node 1 (level 1), hold at the sustain node (level 0.5)", 0.8 < hd / pk * 2 < 1.2 and pk > 0.02, "peak %.3f hold %.3f" % (pk, hd))
check("MSEG: the sustain node holds (no decay between 0.4 s and 0.95 s)", abs(at(a, 0.4) - at(a, 0.9)) < 0.05 * hd)
check("MSEG: release runs through the nodes after the sustain node (still sounding 100 ms after note off, gone after 400 ms)", at(a, 1.1) > 0.15 * hd and at(a, 1.45) < 0.05 * hd, "%.3f %.3f" % (at(a, 1.1), at(a, 1.45)))
# without a sustain node the envelope runs to the end and holds there
a = render(BASE + R + mseg(0, [(50, 1.0, 0), (50, 0.0, 0)], sus=0), tag="nosus")
check("MSEG without sustain node: runs through the nodes (0 at the end)", at(a, 0.5) < 0.05 * at(a, 0.05), "%.3f" % at(a, 0.5))
# loop
a = render(BASE + R + mseg(0, [(50, 1.0, 0), (50, 0.0, 0)], sus=0, loop=(1, 2)), tag="loop")
seg = [at(a, 0.5 + 0.01 * i, 0.01) for i in range(40)]
check("MSEG loop: still moving after 0.5 s while held (cycle 100 ms)", max(seg) > 0.02 and min(seg) < 0.35 * max(seg), "%.3f %.3f" % (min(seg), max(seg)))
# loop stops after note off
check("MSEG loop: silent at the end after release", at(a, 1.9) < 0.05 * max(seg), "%.3f" % at(a, 1.9))
# curve
c1 = render(BASE + R + mseg(0, [(400, 1.0, 1.0), (10, 1.0, 0)], sus=2), tag="c1", hold=0.6)
c2 = render(BASE + R + mseg(0, [(400, 1.0, -1.0), (10, 1.0, 0)], sus=2), tag="c2", hold=0.6)
check("MSEG curve: +1 starts slowly, -1 starts fast (level at 100 ms)", at(c2, 0.1) > 3 * at(c1, 0.1), "%.3f %.3f" % (at(c1, 0.1), at(c2, 0.1)))
# release time
f = render(BASE + R + mseg(0, [(10, 1.0, 0), (10, 1.0, 0), (20, 0.0, 0)], sus=2), tag="rf")
s = render(BASE + R + mseg(0, [(10, 1.0, 0), (10, 1.0, 0), (800, 0.0, 0)], sus=2), tag="rs")
check("MSEG release node time: 20 ms vs 800 ms (level 200 ms after note off)", at(s, 1.2) > 5 * max(at(f, 1.2), 1e-4), "%.3f %.3f" % (at(f, 1.2), at(s, 1.2)))
# fallback release when there is no node after the sustain node
a = render(BASE + R + mseg(0, [(10, 1.0, 0), (10, 0.6, 0)], sus=2) + [(270, 100.0)], tag="fb")
check("MSEG without release nodes: falls back to the ADSR release time", at(a, 1.0, 0.02) > 0.03 and at(a, 1.9) < 0.1 * at(a, 0.9), "%.3f %.3f" % (at(a, 1.0), at(a, 1.9)))
# 2nd envelope works independently
b = render(BASE + route(12) + mseg(1, n, sus=2), tag="e2")
check("MSEG on envelope 2 (source 12)", at(b, 0.7) > 0.02 and abs(at(b, 0.7) - hd) < 0.1 * hd, "%.3f" % at(b, 0.7))
print("%d failures" % failures); sys.exit(1 if failures else 0)
