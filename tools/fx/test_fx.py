#!/usr/bin/env python3
"""Audio tests of the FX rack additions.   python3 tools/fx/test_fx.py --host host_fx"""
import argparse, os, subprocess, tempfile
import sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="fxTest"); RATE = 48000; failures = 0

def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1

def base(slot): return 541 + 10 * slot + (10 if slot >= 10 else 0) + (10 if slot >= 20 else 0)

def fx(slot, ty, mode=0, mix=1.0, p=(0.5,) * 6):
    b = base(slot)
    c = ["p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d %s" % (b + 2, mix), "p %d %d" % (b + 3, mode)]
    c += ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
    return c

def render(cmds, hold=0.3, tail=1.5, tag="x"):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 sine\np %d 0\n" % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        f.write("run 0.6\non 69 110\nrun %s\noff 69\nrun %s\n" % (hold, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)

def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
T0 = int((0.6 + 0.3) * RATE)

dry = render([], tag="dry")
check("dry renders sound", rms(dry[int(0.7 * RATE):T0]) > 1e-4)
tail_dry = rms(dry[T0 + int(0.5 * RATE):T0 + int(1.0 * RATE)])

for mode, name in enumerate(["Room", "Hall", "Plate", "Cathedral", "Chamber", "Reverse", "Gated", "Ambience"]):
    a = render(fx(0, 12, mode, 1.0, (0.6, 0.6, 0.3, 0.0, 0.5, 0.5)), tag="cv%d" % mode)
    ok = np.isfinite(a).all() and np.abs(a).max() < 4.0
    check("conv %s finite and bounded" % name, ok, "peak %.2f" % np.abs(a).max())
    w = rms(a[int(0.7 * RATE):T0])
    if mode == 5: w = rms(a[T0:T0 + int(0.6 * RATE)])
    check("conv %s produces output" % name, w > 1e-4, "rms %.4f" % w)
    if mode in (0, 1, 2, 3, 4):
        tl = rms(a[T0 + int(0.15 * RATE):T0 + int(0.35 * RATE)])
        check("conv %s has a tail after note-off" % name, tl > 5 * max(tail_dry, 1e-6) or tl > 1e-3, "tail %.5f" % tl)

# longer decay -> longer tail
s = render(fx(0, 12, 1, 1.0, (0.3, 0.2, 0.3, 0.0, 0.5, 0.5)), tag="short")
l = render(fx(0, 12, 1, 1.0, (0.9, 0.9, 0.3, 0.0, 0.5, 0.5)), tag="long")
ts = rms(s[T0 + int(0.8 * RATE):T0 + int(1.3 * RATE)]); tl = rms(l[T0 + int(0.8 * RATE):T0 + int(1.3 * RATE)])
check("bigger size / decay gives a longer tail", tl > 2 * ts, "%.5f vs %.5f" % (tl, ts))

# user IR: unit impulse at 2000 samples -> wet = dry delayed by 1024 + 2000 (low-passed)
cmds = ["ir 0 impulse 2000"] + fx(0, 12, 8, 1.0, (1.0, 0.5, 0.0, 0.0, 0.5, 0.5))
u = render(cmds, tag="user")
check("user IR finite", np.isfinite(u).all() and np.abs(u).max() < 4.0)
nf = render(fx(0, 0), tag="nofx")
x = nf[:, 0].astype(np.float64); y = u[:, 0].astype(np.float64)
seg = slice(int(0.7 * RATE), int(0.85 * RATE))
def onset(v):
    v = np.abs(v[int(0.55 * RATE):int(1.0 * RATE)]); return int(np.argmax(v > 0.5 * v.max()))
on_x = onset(x); on_y = onset(y)
bl = on_y - on_x; best = 1.0
check("user IR impulse = dry delayed by 1024 + 2000 samples", abs(bl - 3024) <= 40, "lag %d" % bl)

# a second convolution slot in the same rack passes through (one engine per rack)
two = render(fx(0, 12, 1, 1.0) + fx(1, 12, 3, 1.0), tag="two")
check("two conv slots in a rack stay finite", np.isfinite(two).all() and np.abs(two).max() < 4.0)

# mix 0 = dry
m0 = render(fx(0, 12, 1, 0.0), tag="m0")
check("mix 0 equals dry", np.allclose(m0, dry, atol=1e-5))

# ---- extended algorithms / parameters of the other effects: every mode, parameters at both extremes
import itertools
MODES = {1: 13, 2: 6, 3: 6, 4: 5, 5: 4, 6: 8, 7: 9, 8: 9, 10: 4, 11: 5}
for ty, nm in MODES.items():
    bad = []
    for md in range(nm):
        for pv in (0.0, 1.0):
            a = render(fx(0, ty, md, 1.0, (pv,) * 6), hold=0.2, tail=0.3, tag="sw")
            if not np.isfinite(a).all() or np.abs(a).max() > 8.0: bad.append((md, pv, float(np.abs(a).max())))
    check("type %d: all %d modes finite and bounded at parameter extremes" % (ty, nm), not bad, str(bad[:3]))

# new distortion modes actually distort (more harmonics than the clean sine)
def thd(v):
    seg = v[int(0.7 * RATE):int(0.85 * RATE), 0].astype(np.float64); X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); k = int(np.argmax(X))
    return 1.0 - X[max(0, k - 3):k + 4].sum() / (X.sum() + 1e-12)
for md, nm in ((6, "Rectify"), (7, "Fuzz"), (8, "Tanh"), (9, "Diode"), (10, "Chebyshev"), (11, "Tape"), (12, "Gated")):
    a = render(fx(0, 1, md, 1.0, (0.8, 1.0, 0.5, 0.5, 0.0, 0.0)), tag="d%d" % md)
    check("distortion %s adds harmonics" % nm, thd(a) > thd(dry) + 0.02, "%.3f vs %.3f" % (thd(a), thd(dry)))

# bias adds even harmonics, DC stays blocked
b0 = render(fx(0, 1, 0, 1.0, (0.8, 1.0, 0.5, 0.5, 0.0, 0.0)), tag="b0"); b1 = render(fx(0, 1, 0, 1.0, (0.8, 1.0, 0.5, 1.0, 0.0, 0.0)), tag="b1")
check("distortion bias changes the spectrum", abs(thd(b0) - thd(b1)) > 0.005 or not np.allclose(b0, b1, atol=1e-3))
check("distortion DC blocked", abs(float(b1[int(0.8 * RATE):int(0.9 * RATE), 0].mean())) < 0.05)

# negative flanger feedback differs from positive; flanger width 0 = mono wet
f0 = render(fx(0, 5, 0, 1.0, (0.3, 0.6, 0.9, 0.5, 0.5, 0.5)), tag="f0"); f1 = render(fx(0, 5, 1, 1.0, (0.3, 0.6, 0.9, 0.5, 0.5, 0.5)), tag="f1")
check("flanger negative mode differs", not np.allclose(f0, f1, atol=1e-3))
fw = render(fx(0, 4, 0, 1.0, (0.5, 0.5, 0.0, 0.0, 0.5, 0.5)), tag="fw")
seg2 = fw[int(0.7 * RATE):int(0.9 * RATE)]
check("chorus width 0 collapses the wet to mono", np.abs(seg2[:, 0] - seg2[:, 1]).max() < 1e-4)

# ducking delay is quieter during the note than the plain delay, and a low cut lowers the echo level
dp = render(fx(0, 3, 0, 1.0, (0.3, 0.6, 1.0, 0.0, 0.0, 0.0)), tag="dp"); dd = render(fx(0, 3, 3, 1.0, (0.3, 0.6, 1.0, 0.0, 0.0, 0.0)), tag="dd")
check("ducking delay differs from the plain delay", not np.allclose(dp, dd, atol=1e-3))

# reverb wet low cut / high cut change the level
r0 = render(fx(0, 8, 0, 1.0, (0.5, 0.5, 0.2, 1.0, 0.0, 1.0)), tag="r0"); r1 = render(fx(0, 8, 0, 1.0, (0.5, 0.5, 0.2, 1.0, 1.0, 0.0)), tag="r1")
check("reverb tone filters narrow the wet signal", rms(r1[T0:]) < 0.8 * rms(r0[T0:]), "%.5f vs %.5f" % (rms(r1[T0:]), rms(r0[T0:])))

# compressor knee: soft knee reduces the gain below the threshold, hard knee does not
c0 = render(fx(0, 11, 0, 1.0, (0.8, 0.8, 0.1, 0.4, 0.0, 0.0)), tag="c0"); c1 = render(fx(0, 11, 0, 1.0, (0.8, 0.8, 0.1, 0.4, 0.0, 1.0)), tag="c1")
check("compressor soft knee acts below the threshold", rms(c1[int(0.7 * RATE):T0]) < rms(c0[int(0.7 * RATE):T0]) - 1e-4, "%.4f vs %.4f" % (rms(c1[int(0.7 * RATE):T0]), rms(c0[int(0.7 * RATE):T0])))

# ================================================= FX-SYNC: tempo sync, trance gate, more modes
def env(v, win=0.01, t0=0.0, t1=None):
    """RMS envelope of the left channel in windows of 'win' seconds"""
    a = v[:, 0].astype(np.float64); n = int(win * RATE); t1 = len(a) if t1 is None else int(t1 * RATE)
    return np.array([np.sqrt(np.mean(a[i:i + n] ** 2)) for i in range(int(t0 * RATE), t1 - n, n)])
def edges(e, thr):
    on = e > thr; return int(np.sum(on[1:] & ~on[:-1]))
SY = lambda slot, v: ["p %d %d" % (940 + slot, v)]      # sync division of slot (1 = 8/1 ... 9 = 1/4, 12 = 1/8, 15 = 1/16)
BPM = lambda v: ["p 522 %d" % v]

# square tremolo, depth 1, synced to 1/4: 4 cycles in 2 s at 120 BPM, 2 cycles at 60 BPM
q = lambda bpm: render(BPM(bpm) + fx(0, 7, 2, 1.0, (0.5, 1.0, 0.0, 0.5, 0.5, 0.5)) + SY(0, 9), hold=2.0, tail=0.1, tag="sq%d" % bpm)
e120 = env(q(120), t0=0.65, t1=2.55); e60 = env(q(60), t0=0.65, t1=2.55); thr = 0.5 * e120.max()
c120, c60 = edges(e120, thr), edges(e60, 0.5 * e60.max())
check("synced tremolo follows the tempo (120 BPM, 1/4: 3-4 cycles in 1.9 s)", 3 <= c120 <= 5, "%d edges" % c120)
check("half the tempo, half the cycles", 1 <= c60 <= 3 and c60 < c120, "%d edges" % c60)
fr = render(fx(0, 7, 2, 1.0, (0.5, 1.0, 0.0, 0.5, 0.5, 0.5)), hold=2.0, tail=0.1, tag="free")
check("free tremolo (sync off) still modulates", edges(env(fr, t0=0.65, t1=2.55), 0.5 * env(fr, t0=0.65, t1=2.55).max()) >= 1)

# trance gate (mode 5), pattern 1 'Quarters' = 4 open steps of 16, cycle 1/1 = 2 s at 120 BPM
def gate(pat, depth=1.0, smooth=0.0, sw=0.0, stereo=0.0, bpm=120, mode=5, div=4):
    return render(BPM(bpm) + fx(0, 7, mode, 1.0, (0.5, depth, stereo, (pat + 0.5) / 24.0, smooth, sw)) + SY(0, div), hold=2.3, tail=0.1, tag="g%d_%d" % (pat, mode))
g1 = gate(1); eg = env(g1, 0.005, 0.65, 2.9); mx = eg.max(); duty = float(np.mean(eg > 0.3 * mx))
check("trance gate: 'Quarters' opens about 25 % of the time", 0.15 < duty < 0.35, "duty %.2f" % duty)
check("trance gate closes fully (depth 1)", float(np.min(eg)) < 0.05 * mx, "min %.4f max %.4f" % (np.min(eg), mx))
g0 = gate(1, depth=0.0); check("trance gate depth 0 passes the signal", rms(g0[int(0.7 * RATE):int(1.5 * RATE)]) > 0.95 * rms(dry[int(0.7 * RATE):int(1.5 * RATE)]))
g16 = gate(23); check("pattern 'Full' leaves the signal open", rms(g16[int(0.8 * RATE):int(1.8 * RATE)]) > 0.9 * rms(dry[int(0.8 * RATE):int(1.8 * RATE)]))
e8 = env(gate(0), 0.005, 0.65, 2.9); check("pattern 'Eighths' has twice the gates of 'Quarters'", edges(e8, 0.3 * e8.max()) >= 2 * edges(eg, 0.3 * mx) - 1, "%d vs %d" % (edges(e8, 0.3 * e8.max()), edges(eg, 0.3 * mx)))
gs = gate(1, smooth=1.0); egs = env(gs, 0.005, 0.65, 2.9); check("gate smoothing softens the edges", float(np.max(np.abs(np.diff(egs)))) < 0.6 * float(np.max(np.abs(np.diff(eg)))), "%.4f vs %.4f" % (np.max(np.abs(np.diff(egs))), np.max(np.abs(np.diff(eg)))))
gst = gate(10, stereo=1.0); l, r = env(gst, 0.005, 0.65, 2.9), env(np.stack([gst[:, 1], gst[:, 0]], 1), 0.005, 0.65, 2.9)
check("gate stereo shifts the right channel against the left", float(np.mean(np.abs(l - r))) > 0.3 * float(np.mean(l)), "%.4f" % float(np.mean(np.abs(l - r))))
ap = gate(0, depth=1.0, mode=6); check("auto-pan: channels differ and stay finite", np.isfinite(ap).all() and float(np.mean(np.abs(ap[int(0.8 * RATE):int(2 * RATE), 0] - ap[int(0.8 * RATE):int(2 * RATE), 1]))) > 0.01)
for md, nm in ((7, "random S&H"), (8, "smooth random")):
    rr = gate(0, mode=md, div=12)
    er = env(rr, 0.02, 0.65, 2.9); check("tremolo %s modulates the level" % nm, float(er.max() / max(er.min(), 1e-9)) > 1.5, "ratio %.2f" % float(er.max() / max(er.min(), 1e-9)))

# delay synced to 1/8 (0.25 s at 120 BPM), feedback 0: the echo starts one eighth after the note
dsy = render(BPM(120) + fx(0, 3, 0, 1.0, (0.5, 0.0, 1.0, 0.0, 0.0, 0.0)) + SY(0, 12), hold=0.05, tail=1.0, tag="dsy")
def echo_gap(v):
    e = env(v, 0.005, 0.5, 1.6); o = int(np.argmax(e > 0.3 * e.max()))
    for i in range(o + 4, len(e)):
        if e[i] > 1.5 * e[i - 1] and e[i] > 0.3 * e.max(): return (i - o) * 0.005
    return -1.0
gap8 = echo_gap(dsy)
dsy4 = render(BPM(120) + fx(0, 3, 0, 1.0, (0.5, 0.0, 1.0, 0.0, 0.0, 0.0)) + SY(0, 9), hold=0.05, tail=1.0, tag="dsy4")
gap4 = echo_gap(dsy4)
check("delay 1/8 echo arrives about 250 ms after the note", gap8 > 0 and abs(gap8 - 0.25) < 0.04, "%.3f s" % gap8)
check("delay 1/4 echo arrives about 500 ms after the note", gap4 > 0 and abs(gap4 - 0.5) < 0.04, "%.3f s" % gap4)

# more modes: each differs audibly from the first mode, reverse delay echoes after the note
def differs(ty, m0, m1, p=(0.5,) * 6, atol=2e-3):
    return not np.allclose(render(fx(0, ty, m0, 1.0, p), hold=0.3, tail=0.3, tag="a"), render(fx(0, ty, m1, 1.0, p), hold=0.3, tail=0.3, tag="b"), atol=atol)
check("distortion Diode / Chebyshev / Tape / Gated differ from Soft", all(differs(1, 0, m, (0.8, 1.0, 0.5, 0.5, 0.0, 0.0)) for m in (9, 10, 11, 12)))
check("bit crush Bits Only / Rate Only / Noise Shaped differ from Round", all(differs(2, 0, m, (0.9, 0.3, 0.0, 0.0)) for m in (3, 4, 5)))
check("delay Reverse and Multi-tap differ from Digital", all(differs(3, 0, m, (0.3, 0.5, 1.0, 0.0, 0.0, 0.0)) for m in (4, 5)))
rv = render(fx(0, 3, 4, 1.0, (0.3, 0.5, 1.0, 0.0, 0.0, 0.0)), hold=0.3, tail=1.0, tag="rev")
check("reverse delay produces echoes after note-off", rms(rv[T0 + int(0.1 * RATE):T0 + int(0.6 * RATE)]) > 2e-3)
check("chorus Ensemble and Wide differ from Classic", all(differs(4, 0, m) for m in (3, 4)))
check("flanger Through-Zero and Stereo differ from Positive", all(differs(5, 0, m, (0.3, 0.8, 0.6, 0.5, 0.5, 0.5)) for m in (2, 3)))
check("phaser 10 / 12 stages and the inverted modes differ from 2 stages", all(differs(6, 0, m) for m in (4, 5, 6, 7)))
check("reverb Chamber / Ambience / Dark / Bright / Infinite differ from Hall", all(differs(8, 0, m, (0.5, 0.5, 0.0, 1.0, 0.0, 1.0)) for m in (4, 5, 6, 7, 8)))
tl0 = render(fx(0, 8, 8, 1.0, (0.5, 0.5, 0.0, 1.0, 0.0, 1.0)), hold=0.3, tail=1.5, tag="inf"); th0 = render(fx(0, 8, 0, 1.0, (0.5, 0.5, 0.0, 1.0, 0.0, 1.0)), hold=0.3, tail=1.5, tag="hall")
check("reverb Infinite rings longer than Hall", rms(tl0[T0 + int(1.0 * RATE):T0 + int(1.4 * RATE)]) > 1.5 * rms(th0[T0 + int(1.0 * RATE):T0 + int(1.4 * RATE)]))
t_lo = render(fx(0, 10, 1, 1.0, (0.0, 0.5, 0.5, 0.5, 0.5, 0.5)), tag="tl"); t_hi = render(fx(0, 10, 1, 1.0, (1.0, 0.5, 0.5, 0.5, 0.5, 0.5)), tag="th")
check("EQ tilt: the tilt amount moves the level of a low tone in opposite directions", rms(t_lo[int(0.7 * RATE):T0]) > 1.2 * rms(t_hi[int(0.7 * RATE):T0]), "%.4f vs %.4f" % (rms(t_lo[int(0.7 * RATE):T0]), rms(t_hi[int(0.7 * RATE):T0])))
check("EQ Loudness / Presence differ from Classic", all(differs(10, 0, m, (0.8, 0.8, 0.5, 0.8, 0.5, 0.5)) for m in (2, 3)))
lim = render(fx(0, 11, 2, 1.0, (0.1, 0.9, 0.1, 0.4, 0.0, 0.0)), tag="lim"); cmp_ = render(fx(0, 11, 0, 1.0, (0.1, 0.9, 0.1, 0.4, 0.0, 0.0)), tag="cmp")
check("compressor Limiter holds the level lower than the compressor", np.abs(lim[int(0.7 * RATE):T0]).max() <= np.abs(cmp_[int(0.7 * RATE):T0]).max() + 1e-6)
gt = render(fx(0, 11, 4, 1.0, (0.9, 0.8, 0.1, 0.4, 0.0, 0.0)), tag="gt")
check("compressor Gate closes on a signal below the threshold", rms(gt[int(0.7 * RATE):T0]) < 0.3 * rms(dry[int(0.7 * RATE):T0]), "%.5f vs %.5f" % (rms(gt[int(0.7 * RATE):T0]), rms(dry[int(0.7 * RATE):T0])))

print("FAILURES: %d" % failures if failures else "ALL OK")
raise SystemExit(1 if failures else 0)
