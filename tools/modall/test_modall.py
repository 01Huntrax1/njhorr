#!/usr/bin/env python3
"""Tests of the generic modulation destinations (tools/modall).   python3 tools/modall/test_modall.py --host <dsp_host>"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__)); ids = json.load(open(os.path.join(HERE, "ids.json"))); K = {r[0]: k for k, r in enumerate(ids)}
TMP = tempfile.mkdtemp(prefix="modall"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def render(cmds, hold=1.5, tag="x", note=69):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\non %d 100\nrun %s\noff %d\nrun 0.3\n" % (note, hold, note))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def track(a, t0, t1, w=0.01): return np.array([rms(a[int((t0 + i * w) * RATE):int((t0 + (i + 1) * w) * RATE)]) for i in range(int((t1 - t0) / w))])
def route(src, dest_id, amt, slot=0): return [(307 + 3 * slot, src), (308 + 3 * slot, 1584 + K[dest_id]), (309 + 3 * slot, amt)]
# parameter 29 = Out Gain? use the main "Master Level"-like generic param: find one by name
name = {r[0]: r[1] for r in ids}
tgt = next(i for i, n in name.items() if n == "Master")
base = ["wt 0 sine", (tgt, 0.5), (13000 + 16 * 0 + 7, 1.0)]
lfo = [(247, 0), (248, 4.0)]    # LFO 1: sine, 4 Hz
a0 = render(base, tag="plain")
a1 = render(base + route(1, tgt, 1.0) + lfo, tag="mod")
t0 = track(a0, 0.3, 1.3); t1 = track(a1, 0.3, 1.3)
check("unmodulated level steady", t0.std() / t0.mean() < 0.05, "%.3f" % (t0.std() / t0.mean()))
check("LFO modulates the generic destination (Master)", t1.std() / t1.mean() > 0.2, "%.3f" % (t1.std() / t1.mean()))
# unrouting restores the base value
script = os.path.join(TMP, "un.txt"); out = os.path.join(TMP, "un.f32")
with open(script, "w") as f:
    for c in base + route(1, tgt, 1.0) + lfo: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
    f.write("run 0.05\non 69 100\nrun 1.0\np 307 0\nrun 1.0\noff 69\nrun 0.3\n")
subprocess.run([args.host, script, out], check=True)
a2 = np.fromfile(out, dtype=np.float32).reshape(-1, 2); t2 = track(a2, 1.4, 2.0)
check("removing the slot restores the base value", abs(t2.mean() - t0.mean()) / t0.mean() < 0.1 and t2.std() / t2.mean() < 0.05, "%.3f vs %.3f" % (t2.mean(), t0.mean()))
print("%d failures" % failures); sys.exit(1 if failures else 0)
