#!/usr/bin/env python3
"""Tests of the Inspirator sequencer (params 7000-7128).   python3 tools/mod/test_inspirator.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="insTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
I = 7000
BASE = ["wt 0 sine", (L.pid(0, K["fon"]), 0)]
def P(n, v): return (I + n, v)
def render(cmds, keys, hold=4.0, tail=0.6, tag="x"):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\n")
        for k in keys: f.write("on %d 100\n" % k)
        f.write("run %s\n" % hold)
        for k in keys: f.write("off %d\n" % k)
        f.write("run %s\n" % tail)
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)[:, 0]
rm = lambda x: float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
def cent(x):
    s = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float((s * f).sum() / (s.sum() + 1e-9))
def mode(m, *extra):
    c = [(I, 1), P(1, m), P(8, 2), P(10, 0)]   # on, mode, 4 bars, MIDI In = Transpose
    return c + [P(k, v) for k, v in extra]
a = render(BASE + [(I, 0)], [60], hold=1.0, tag="off")
check("Inspirator off: the key plays normally", rm(a[int(0.3 * RATE):int(0.9 * RATE)]) > 0.05)
for m, nm in enumerate(["Chords", "Lead", "Bass", "Arp", "Drums"]):
    a = render(BASE + mode(m), [60], tag="m%d" % m)
    body = a[int(0.5 * RATE):int(3.8 * RATE)]
    check("%s: the held key starts the generated pattern (sound, finite, bounded)" % nm, rm(body) > 0.01 and np.isfinite(a).all() and np.abs(a).max() < 6.0, "rms %.3f" % rm(body))
    check("%s: releasing the key stops the pattern" % nm, rm(a[int(4.4 * RATE):]) < 0.2 * max(rm(body), 1e-6) + 0.002, "%.4f" % rm(a[int(4.4 * RATE):]))
a1 = render(BASE + mode(1), [60], tag="s1"); a2 = render(BASE + mode(1), [60], tag="s2")
check("Same seeds give the same pattern", np.abs(a1 - a2).max() < 1e-5)
a3 = render(BASE + mode(1, (6, 77)), [60], tag="s3")
check("Another Part Seed gives another pattern", rm(a3 - a1) > 0.2 * rm(a1))
a4 = render(BASE + mode(1, (5, 4321)), [60], tag="s4")
check("Another Song Seed gives another pattern", rm(a4 - a1) > 0.1 * rm(a1))
for st in range(9):
    a = render(BASE + mode(0, (2, st)), [60], hold=3.0, tag="st%d" % st)
    check("Style %d stays finite and sounds" % st, np.isfinite(a).all() and rm(a[int(0.5 * RATE):int(2.8 * RATE)]) > 0.005 and np.abs(a).max() < 6.0)
lo = render(BASE + mode(2), [60], tag="t60"); hi = render(BASE + mode(2), [64], tag="t64"); dn = render(BASE + mode(2), [67], tag="t67")
r = cent(hi[int(0.5 * RATE):int(3.8 * RATE)]) / cent(lo[int(0.5 * RATE):int(3.8 * RATE)])
check("The key transposes the pattern (key 64 is a major third above key 60)", 1.12 < r < 1.45, "%.2f" % r)
r = cent(dn[int(0.5 * RATE):int(3.8 * RATE)]) / cent(lo[int(0.5 * RATE):int(3.8 * RATE)])
check("Keys above the fold transpose downwards (key 67 = a fourth below, like the original)", 0.6 < r < 0.9, "%.2f" % r)
ch1 = render(BASE + mode(0), [60], tag="cd0"); ch2 = render(BASE + mode(0, (44, 90)), [60], tag="cd1")
check("Chords Complexity changes the pattern", rm(ch2 - ch1) > 0.05 * rm(ch1))
d0 = render(BASE + mode(4, (81, 10)), [60], tag="dd0"); d1 = render(BASE + mode(4, (81, 100)), [60], tag="dd1")
check("Drums Density changes the pattern", rm(d1 - d0) > 0.05 * rm(d0 + 1e-6))
print("all passed" if not failures else "%d FAILED" % failures)
sys.exit(1 if failures else 0)
