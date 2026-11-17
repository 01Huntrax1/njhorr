#!/usr/bin/env python3
"""Audio tests of the effect specific extra parameters (FX-EX) and the master limiter (MASTER-OUT).
python3 tools/fx/test_fxex.py --host <dsp_host of patch_fx, built with -DDSP_FX>"""
import argparse, os, subprocess, tempfile, sys
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="exTest"); RATE = 48000; failures = 0
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def run(ty, ex=(), p=(0.5,) * 6, src="noise 0.3 220", secs=1.5, mode=0, extra_cmds=(), tag="x", slot=0):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32"); b = 541 + 10 * slot
    cmds = ["in " + src, "p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d 1" % (b + 2), "p %d %d" % (b + 3, mode)] + ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
    cmds += ["p %d %s" % (11700 + 4 * slot + k, v) for k, v in ex] + list(extra_cmds)
    with open(script, "w") as f:
        for c in cmds: f.write(c + "\n")
        f.write("run %s\n" % secs)
    subprocess.run([args.host, script, out], check=True, capture_output=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def band(a, lo, hi, ch=0):
    x = a[int(0.5 * RATE):, ch].astype(np.float64)
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.mean(sp[(f > lo) & (f < hi)])) + 1e-30
db = lambda a, b: 10 * np.log10(a / b)
rms = lambda a: float(np.sqrt(np.mean(a[int(0.5 * RATE):, 0] ** 2)))
# neutral
for ty in (14, 3, 4, 10, 11):
    check("type %d: all four extras at 0 change nothing" % ty, np.allclose(run(ty, tag="n0"), run(ty, [(0, 0), (1, 0), (2, 0), (3, 0)], tag="n1"), atol=1e-7))
# distortion family (Saturator 14): Pre HP, Pre LP, Gate, Trim
base = run(14, tag="d")
hp = run(14, [(0, 1.0)], tag="hp"); check("Saturator Pre HP removes lows before the effect", db(band(base, 40, 120), band(hp, 40, 120)) > 12, "%.1f dB" % db(band(base, 40, 120), band(hp, 40, 120)))
lp = run(14, [(1, 1.0)], tag="lp"); check("Saturator Pre LP removes highs before the effect", db(band(base, 6000, 12000), band(lp, 6000, 12000)) > 12, "%.1f dB" % db(band(base, 6000, 12000), band(lp, 6000, 12000)))
quiet = run(14, src="noise 0.003 220", tag="q0"); gate = run(14, [(2, 1.0)], src="noise 0.003 220", tag="q1")
check("Gate closes on a quiet input", rms(gate) < 0.1 * rms(quiet), "%.5f vs %.5f" % (rms(gate), rms(quiet)))
loud = run(14, [(2, 1.0)], tag="g2"); check("Gate stays open for a loud input", rms(loud) > 0.8 * rms(base))
tr = run(14, [(3, 1.0)], tag="tr"); check("Trim attenuates by 24 dB", abs(20 * np.log10(rms(tr) / rms(base)) + 24) < 1.0, "%.1f dB" % (20 * np.log10(rms(tr) / rms(base))))
# time family (Delay 3): Pre Delay, Duck, Release, Air
imp = np.zeros((RATE * 2, 2), np.float32); imp[int(0.1 * RATE)] = 0.8; ip = os.path.join(TMP, "imp.f32"); imp.tofile(ip)
def echo(ex, tag):
    a = run(3, ex, p=(0.3, 0.0, 0.5, 0.5, 0.5, 0.5), src="off 0 0", secs=1.5, extra_cmds=[], tag=tag) if False else None
script = os.path.join(TMP, "echo.txt")
def runimp(ex, tag):
    s = os.path.join(TMP, tag + ".txt"); o = os.path.join(TMP, tag + ".f32")
    cmds = ["inf " + ip, "p 541 3", "p 542 1", "p 543 1", "p 544 0", "p 545 0.3", "p 546 0", "p 547 0.5", "p 548 0.5", "p 549 0.5", "p 550 0.5"] + ["p %d %s" % (11700 + k, v) for k, v in ex]
    open(s, "w").write("\n".join(cmds) + "\nrun 1.5\n"); subprocess.run([args.host, s, o], check=True, capture_output=True)
    a = np.fromfile(o, dtype=np.float32).reshape(-1, 2); return a
e0 = runimp([], "e0"); e1 = runimp([(0, 0.4)], "e1")
i0 = int(np.argmax(np.abs(e0[:, 0]))); i1 = int(np.argmax(np.abs(e1[:, 0])))   # the click itself (the delay passes the dry signal too)
check("Pre Delay 40 % delays the input by about 100 ms", abs((i1 - i0) / RATE - 0.1) < 0.005, "%.1f ms" % ((i1 - i0) / RATE * 1000))
d0 = run(3, p=(0.3, 0.3, 0.5, 0.5, 0.5, 0.5), tag="du0"); d1 = run(3, [(1, 1.0)], p=(0.3, 0.3, 0.5, 0.5, 0.5, 0.5), tag="du1")
check("Duck pulls the wet signal down while the input plays", rms(d1) < 0.35 * rms(d0), "%.4f vs %.4f" % (rms(d1), rms(d0)))
a0 = run(3, p=(0.3, 0.3, 0.5, 0.5, 0.5, 0.5), tag="a0"); a1 = run(3, [(3, 1.0)], p=(0.3, 0.3, 0.5, 0.5, 0.5, 0.5), tag="a1")
check("Air lifts the highs of the wet signal", db(band(a1, 8000, 14000), band(a0, 8000, 14000)) > 3, "%.1f dB" % db(band(a1, 8000, 14000), band(a0, 8000, 14000)))
# modulation family (Chorus 4): Pan Rate, Pan Depth, Warmth, Air
pn = run(4, [(0, 0.45), (1, 1.0)], tag="pn")
x = pn[int(0.5 * RATE):]; env = lambda c: np.array([np.sqrt(np.mean(x[i:i + 2400, c] ** 2)) for i in range(0, len(x) - 2400, 2400)])
ratio = (env(0) + 1e-9) / (env(1) + 1e-9)
check("Pan Depth moves the wet signal left and right", ratio.max() / ratio.min() > 3, "%.1f" % (ratio.max() / ratio.min()))
w0 = run(4, tag="w0"); w1 = run(4, [(2, 1.0)], tag="w1")
check("Warmth lifts the lows of the wet signal", db(band(w1, 60, 160), band(w0, 60, 160)) > 4, "%.1f dB" % db(band(w1, 60, 160), band(w0, 60, 160)))
# master limiter (rack passes through; no effect)
def master(extra, tag):
    s = os.path.join(TMP, tag + ".txt"); o = os.path.join(TMP, tag + ".f32")
    open(s, "w").write("\n".join(["in sine 0.9 1000"] + extra) + "\nrun 0.6\n"); subprocess.run([args.host, s, o], check=True, capture_output=True)
    return np.fromfile(o, dtype=np.float32).reshape(-1, 2)
m_on = master(["p 11601 -6"], "mo"); m_off = master(["p 11600 0"], "mf")
pk = lambda a: float(np.abs(a[int(0.2 * RATE):]).max())
check("limiter holds the output at the ceiling (-6 dB = 0.50)", pk(m_on) < 0.51, "%.3f" % pk(m_on))
check("limiter off: the signal passes at full level", pk(m_off) > 0.2, "%.3f" % pk(m_off))
print("%d failures" % failures); sys.exit(1 if failures else 0)
