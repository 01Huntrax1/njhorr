#!/usr/bin/env python3
"""The sequencer playhead events (output event seqPos).  Needs a host built with -DSEQPOS_LOG:
   python3 tools/mod/test_seqpos.py --host <dsp_host built with -DSEQPOS_LOG>"""
import argparse, os, re, subprocess, sys, tempfile
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="seqposTest"); failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def run(lines):
    s = os.path.join(TMP, "s.txt")
    open(s, "w").write("\n".join(lines) + "\n")
    r = subprocess.run([args.host, s, os.path.join(TMP, "o.f32")], capture_output=True, text=True, check=True)
    return [(float(m[0]), int(m[1]), int(m[2])) for m in re.findall(r"seqPos t=([\d.]+) seq=(\d+) step=(\d+)", r.stderr)]
# defaults: Rate 4 Hz, Length 8 -> a step every 0.25 s, no note and no matrix slot needed
ev = run(["wt 0 sine", "run 2.1"])
s1 = [(t, st) for t, q, st in ev if q == 0]
changes = [(t, st) for i, (t, st) in enumerate(s1) if i == 0 or st != s1[i - 1][1]]
check("Seq 1 moves without a note and without a matrix slot (8 steps in 2 s)", len(set(st for _, st in changes)) == 8, str(changes[:9]))
check("All ten sequencers report", {q for _, q, _ in ev} == set(range(10)))
check("Steps advance every 0.25 s", all(abs((changes[i + 1][0] - changes[i][0]) - 0.25) < 0.02 for i in range(len(changes) - 1) if i > 0 and changes[i + 1][1] != 0))
# a slow sequencer (0.5 Hz) is still reported regularly (resend every 0.3 s)
ev = run(["wt 0 sine", "p 3617 0.5", "run 1.5"])
check("A slow sequencer is reported again and again", len([1 for t, q, st in ev if q == 0]) >= 4)
print("FAILURES: %d" % failures if failures else "ALL OK"); sys.exit(1 if failures else 0)
