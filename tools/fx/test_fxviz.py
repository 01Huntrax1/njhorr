#!/usr/bin/env python3
"""Tests of the live data stream of the effect displays (output event fxViz).
python3 tools/fx/test_fxviz.py --host <dsp_host of patch_fx, built with -DDSP_FX -DFXVIZ_LOG>"""
import argparse, os, subprocess, tempfile, sys, math
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="vizTest"); failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def run(cmds, secs=1.0, tag="x"):
    script = os.path.join(TMP, tag + ".txt")
    with open(script, "w") as f:
        for c in cmds: f.write(c + "\n")
        f.write("run %s\n" % secs)
    r = subprocess.run([args.host, script, os.path.join(TMP, tag + ".f32")], capture_output=True, text=True, check=True)
    vals = [float(l.split()[1]) for l in r.stderr.splitlines() if l.startswith("viz ")]
    pk = []; i = 0
    while i < len(vals):
        if vals[i] == -1.0 and i + 54 <= len(vals): pk.append(vals[i:i + 54]); i += 54
        else: i += 1
    return pk
def band(hz): return int(round(23 * math.log(hz / 40.0) / math.log(400.0)))
fxs = lambda ty, mix=1.0, p=(0.5,) * 6: ["p 541 %d" % ty, "p 542 1", "p 543 %s" % mix, "p 544 0"] + ["p %d %s" % (545 + i, v) for i, v in enumerate(p)]
off = run(["in sine 0.5 1000"] + fxs(1) + ["p 9890 0"], 0.5, "off")
check("no packets while the monitor is off", len(off) == 0)
pk = run(["in sine 0.5 1000"] + fxs(1, 1.0, (0.8, 0.5, 0.5, 0.5, 0.5, 0.5)) + ["p 9890 1"], 1.0, "on")
check("about 18 packets per second", 12 <= len(pk) <= 21, "%d packets" % len(pk))
if pk:
    q = pk[-1]
    check("packet reports slot 0", q[1] == 0.0)
    check("input peak = 0.5 (sine amplitude)", abs(q[2] - 0.5) < 0.03 and abs(q[3] - 0.5) < 0.03, "%.3f %.3f" % (q[2], q[3]))
    inb = np.array(q[6:30]); outb = np.array(q[30:54])
    b = band(1000.0)
    check("input spectrum peaks at the 1 kHz band", abs(int(np.argmax(inb)) - b) <= 1, "band %d expected %d" % (int(np.argmax(inb)), b))
    check("input band level about -6 dB (0.5 amplitude)", 0.80 < inb[int(np.argmax(inb))] < 0.97, "%.2f" % inb[int(np.argmax(inb))])
    hi = outb[min(23, b + 4):].max() if b + 4 < 24 else 0.0
    hi_in = inb[min(23, b + 4):].max() if b + 4 < 24 else 0.0
    check("a Distortion adds harmonics (more energy above 1 kHz than the input has)", hi > hi_in + 0.1, "%.2f vs %.2f" % (hi, hi_in))
sil = run(["in sine 0.0 1000"] + fxs(1) + ["p 9890 1"], 0.5, "sil")
check("silence gives zero levels", len(sil) > 5 and max(sil[-1][2:6]) < 1e-4 and max(sil[-1][6:54]) < 0.02)
other = run(["in sine 0.5 1000"] + fxs(1) + ["p 9890 2"], 0.5, "other")
check("monitoring an empty slot sends nothing", len(other) == 0)
print("%d failures" % failures); sys.exit(1 if failures else 0)
