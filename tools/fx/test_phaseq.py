#!/usr/bin/env python3
"""Phase EQ (FX type 38): flat magnitude and the phase of the band types against their analytical responses.   python3 tools/fx/test_phaseq.py --host <dsp_host>"""
import argparse, math, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="phq"); RATE = 48000; fails = 0
def check(n, ok, x=""):
    global fails; print(("PASS " if ok else "FAIL ") + n + (("  (" + x + ")") if x else "")); fails += (not ok)
def base(slot): return 541 + 10 * slot + (10 if slot >= 10 else 0) + (10 if slot >= 20 else 0)
def render(cmds, note, tag, fxon=True, ty=38):
    sc = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32"); b = base(0)
    with open(sc, "w") as f:
        f.write("wt 0 sine\np %d 0\n" % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        if fxon:
            f.write("p %d %d\np %d 1\np %d 1.0\np %d 0\n" % (b, ty, b + 1, b + 2, b + 3))
            for i in range(6): f.write("p %d 0.5\n" % (b + 4 + i))
        f.write("run 0.6\non %d 110\nrun 0.3\noff %d\nrun 0.2\n" % (note, note))
    subprocess.run([args.host, sc, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)[int(0.7 * RATE):int(0.9 * RATE)].astype(np.float64)
def hz(n): return 440.0 * 2 ** ((n - 69) / 12)
def resp(w, d, f, ch=0):   # complex gain wet / dry at frequency f
    n = np.arange(len(w)); e = np.exp(-2j * math.pi * f / RATE * n)
    return (w[:, ch] * e).sum() / (d[:, ch] * e).sum()
def coefs(kind, f0, q):
    w0 = 2 * math.pi * f0 / RATE; cw, sw = math.cos(w0), math.sin(w0); al = sw / (2 * q); K = math.tan(w0 / 2)
    if kind == 7: return [1 - al, -2 * cw, 1 + al], [1 + al, -2 * cw, 1 - al]
    if kind == 12: return [1 - K, -(1 + K), 0], [1 + K, K - 1, 0]
    return [-1, 0, 0], [1, 0, 0]
def secresp(kind, f0, q, f):
    b, a = coefs(kind, f0, q); z = np.exp(-1j * 2 * math.pi * f / RATE)
    return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
def model(ty, f0, q, harm, fall, f):
    h = 1 + 0j
    if ty == 0:
        for _ in range(harm + 1): h *= secresp(7, f0, q, f)
    elif ty == 1:
        for _ in range(harm + 1): h *= secresp(12, f0, q, f)
    elif ty == 2:
        cnt = harm + 2; spr = min(max(fall, 0), 2) * 4
        for i in range(cnt): h *= secresp(7, f0 * 2 ** ((i / (cnt - 1) - 0.5) * spr), q, f)
    else: h *= secresp(13, f0, 1, f)
    return h
dry = {}
def meas(ty, f0, q, harm, fall, note, ch=0, band_ch=0):
    if note not in dry: dry[note] = render([], note, "d%d" % note, fxon=False)
    w = render(["eqband 0 0 1 %d %s 0 %s %d %s 0 %d" % (ty, f0, q, harm, fall, band_ch), "eqsend 0"], note, "t%d_%d_%d" % (ty, note, band_ch))
    return resp(w, dry[note], hz(note), ch)
cases = [("All-Pass 2", 0, 800, 1.0, 0, 0.5, (55, 64, 69, 76, 88)), ("All-Pass 2 x3", 0, 1500, 2.0, 2, 0.5, (60, 72, 80, 88)), ("All-Pass 1", 1, 500, 0.7, 0, 0.5, (48, 60, 69, 84)),
         ("All-Pass 1 x2", 1, 300, 0.7, 1, 0.5, (45, 57, 72)), ("Dispersion", 2, 1200, 0.7, 4, 0.5, (57, 69, 76, 84, 91)), ("Polarity", 3, 1000, 1.0, 0, 0.5, (60, 76))]
for name, ty, f0, q, harm, fall, notes in cases:
    em, ep = [], []
    for nt in notes:
        h = meas(ty, f0, q, harm, fall, nt); e = model(ty, f0, q, harm, fall, hz(nt))
        em.append(abs(20 * math.log10(abs(h) / abs(e)))); ep.append(abs(np.angle(h / e)) * 180 / math.pi)
    check("%s: magnitude as modelled (flat)" % name, max(em) < 0.15, str([round(x, 2) for x in em]))
    check("%s: phase matches the analytical response" % name, max(ep) < 3.0, str([round(x, 1) for x in ep]))
# a left-only band leaves the right channel untouched
h = meas(0, 800, 1.0, 1, 0.5, 64, ch=1, band_ch=1)
check("band set to LEFT leaves the right channel unchanged", abs(h - 1) < 0.02, "%.3f" % abs(h - 1))
h = meas(0, 800, 1.0, 1, 0.5, 64, ch=0, band_ch=1)
check("band set to LEFT does change the left channel", abs(np.angle(h)) > 0.3, "%.2f rad" % abs(np.angle(h)))
# the Parametric EQ (type 13) still behaves: a single bell band of 0 dB is transparent
hb = lambda: None
w = render(["eqband 0 0 1 0 1000 0 1 0 0.5 0 0", "eqsend 0"], 64, "peq0", True, 13); d = dry.get(64) if 64 in dry else render([], 64, "d64x", fxon=False)
check("Parametric EQ unaffected (0 dB bell is transparent)", abs(abs(resp(w, d, hz(64))) - 1) < 0.01)
print("%d failures" % fails); sys.exit(1 if fails else 0)
