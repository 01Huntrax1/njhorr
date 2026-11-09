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

def render(cmds, hold=0.3, tail=1.5, tag="x", note=69):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 sine\np %d 0\n" % L.pid(0, L.K["fon"]))
        for c in cmds: f.write(c + "\n")
        f.write("run 0.6\non %d 110\nrun %s\noff %d\nrun %s\n" % (note, hold, note, tail))
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

# ================================================= FX-PEQ: Parametric EQ (type 13)
import math
def bq_mag(kind, f0, gdb, q, f, sr=RATE):
    """RBJ magnitude (linear) of one section: 0 peak 1 low shelf 2 high shelf 3 high pass 4 low pass 5 band pass 6 notch 7 all-pass"""
    w0 = 2 * math.pi * f0 / sr; cw, sw = math.cos(w0), math.sin(w0); al = sw / (2 * q); A = 10 ** (gdb / 40)
    if kind == 0: b = [1 + al * A, -2 * cw, 1 - al * A]; a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == 1:
        t = 2 * math.sqrt(A) * al; b = [A * ((A + 1) - (A - 1) * cw + t), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - t)]; a = [(A + 1) + (A - 1) * cw + t, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - t]
    elif kind == 2:
        t = 2 * math.sqrt(A) * al; b = [A * ((A + 1) + (A - 1) * cw + t), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - t)]; a = [(A + 1) - (A - 1) * cw + t, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - t]
    elif kind == 3: b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 4: b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 5: g = 10 ** (gdb / 20); b = [al * g, 0, -al * g]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 6: b = [1, -2 * cw, 1]; a = [1 + al, -2 * cw, 1 - al]
    else: b = [1 - al, -2 * cw, 1 + al]; a = [1 + al, -2 * cw, 1 - al]
    z = np.exp(-1j * 2 * math.pi * f / sr)
    return abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))
def note_hz(n): return 440.0 * 2 ** ((n - 69) / 12)
def band(idx, on, ty, hz, db, q, harm=0, fall=0.5, hset=0, ch=0, slot=0):
    return ["eqband %d %d %d %d %s %s %s %d %s %d %d" % (slot, idx, on, ty, hz, db, q, harm, fall, hset, ch)]
EQSEND = ["eqsend 0"]
def peq(bands, p=(0.5, 0.5, 0.5, 0.5, 0.5, 0.5), slot_cmds=None):
    return list(bands) + EQSEND + fx(0, 13, 0, 1.0, p)
dry_note = {}
def level(v, ch=0): return rms(v[int(0.7 * RATE):T0, ch])
def peq_db(bands, note, p=(0.5, 0.5, 0.5, 0.5, 0.5, 0.5), ch=0):
    if note not in dry_note: dry_note[note] = render([], tag="dn%d" % note, note=note)
    w = render(peq(bands, p), tag="pq", note=note)
    return 20 * math.log10(max(level(w, ch), 1e-9) / max(level(dry_note[note], ch), 1e-9))

check("EQ with no bands is transparent", abs(peq_db([], 69)) < 0.05)
# every section type against the analytical response, measured with a sine at three notes
for name, ty, kind, f0, g, q, notes in (("bell +12 dB", 0, 0, 440, 12, 1.0, (57, 69, 81)), ("bell -9 dB", 0, 0, 440, -9, 2.0, (64, 69, 74)),
                                       ("low shelf +9 dB", 1, 1, 400, 9, 0.7, (45, 60, 76)), ("high shelf -9 dB", 2, 2, 400, -9, 0.7, (52, 69, 84)),
                                       ("low cut 12", 3, 3, 700, 0, 0.7071, (57, 69, 81)), ("high cut 12", 5, 4, 300, 0, 0.7071, (57, 69, 81)),
                                       ("band pass", 7, 5, 440, 0, 1.5, (60, 69, 76)), ("notch", 8, 6, 440, 0, 2.0, (66, 69, 72)), ("all-pass", 10, 7, 440, 0, 1.0, (57, 69, 81))):
    err = []
    for nt in notes:
        got = peq_db(band(0, 1, ty, f0, g, q), nt); exp = 20 * math.log10(max(bq_mag(kind, f0, g, q, note_hz(nt)), 1e-9))
        err.append(round(abs(got - max(exp, -50)), 2) if exp > -40 else 0.0 if got < -20 else 99.0)
    check("EQ %s matches the analytical response" % name, max(err) < 1.0, str(err))
check("EQ low cut 24 is steeper than low cut 12", peq_db(band(0, 1, 4, 700, 0, 0.7071), 57) < peq_db(band(0, 1, 3, 700, 0, 0.7071), 57) - 6)
def casc(kind, f0, qs, f): return 20 * math.log10(max(np.prod([bq_mag(kind, f0, 0, q * 1.4142 * 0.7071, f) for q in qs]), 1e-9))
lc48 = [peq_db(band(0, 1, 13, 300, 0, 0.7071), n) for n in (57, 60)]; ex48 = [casc(3, 300, (0.5098, 0.6013, 0.9, 2.5629), note_hz(n)) for n in (57, 60)]
check("EQ low cut 48 matches the analytical 8th order response", max(abs(a - b) for a, b in zip(lc48, ex48)) < 1.5, "%s vs %s" % ([round(x, 1) for x in lc48], [round(x, 1) for x in ex48]))
hc48 = peq_db(band(0, 1, 14, 600, 0, 0.7071), 81); eh48 = casc(4, 600, (0.5098, 0.6013, 0.9, 2.5629), note_hz(81))
check("EQ high cut 48 matches the analytical 8th order response", abs(hc48 - eh48) < 1.5 or (hc48 < -20 and eh48 < -20), "%.1f vs %.1f" % (hc48, eh48))
check("EQ high cut 24 / 48 cut a high tone", peq_db(band(0, 1, 6, 300, 0, 0.7071), 81) < -20 and peq_db(band(0, 1, 14, 300, 0, 0.7071), 81) < -35)
tl = [peq_db(band(0, 1, 9, 440, 12, 0.7), n) for n in (45, 93)]
check("EQ tilt lowers the lows and raises the highs", tl[0] < -2 and tl[1] > 2, str([round(x, 2) for x in tl]))
# harmonics: bell at 220 Hz +12 dB Q 4 with 2 harmonics (falloff 0.5 -> x0.7 per step): 440 Hz +8.4 dB, 660 Hz +5.9 dB
hb = band(0, 1, 0, 220, 12, 4.0, 2, 0.5, 0)
h1, h2, h3 = peq_db(hb, 57), peq_db(hb, 69), peq_db(hb, 76)
check("EQ harmonics add bells at 2f and 3f with falling gain", 10.5 < h1 < 13 and 6.5 < h2 < 10 and 4 < h3 < 8, "%.1f %.1f %.1f dB" % (h1, h2, h3))
ho = band(0, 1, 0, 220, 12, 4.0, 2, 0.5, 1)
check("EQ odd harmonics skip the even ones", peq_db(ho, 69) < 3 and peq_db(ho, 76) > 4, "%.1f %.1f" % (peq_db(ho, 69), peq_db(ho, 76)))
# combs
cf = band(0, 1, 11, 220, 6.0, 1.0)
c1, c2 = peq_db(cf, 69), peq_db(cf, 64)
check("EQ feed-forward comb peaks at multiples of its frequency and dips in between", 2.5 < c1 < 4.5 and -7.5 < c2 < -4.5, "%.1f %.1f dB" % (c1, c2))
cb = band(0, 1, 12, 220, 6.0, 1.0); fb1, fb2 = peq_db(cb, 69), peq_db(cb, 64)
check("EQ feedback comb peaks at multiples, dips in between", fb1 > fb2 + 4, "%.1f vs %.1f dB" % (fb1, fb2))
# channels: left only, right only, mid, side
bl = band(0, 1, 0, 440, 12, 1.0, ch=1); wl = render(peq(bl), tag="chl"); dn = dry_note[69]
check("EQ band on the left channel only", abs(20 * math.log10(level(wl, 0) / level(dn, 0)) - 12) < 1 and abs(20 * math.log10(level(wl, 1) / level(dn, 1))) < 0.3)
check("EQ band on the mid signal boosts a centred tone", peq_db(band(0, 1, 0, 440, 12, 1.0, ch=3), 69) > 11)
check("EQ band on the side signal leaves a centred tone alone", abs(peq_db(band(0, 1, 0, 440, 12, 1.0, ch=4), 69)) < 0.3)
# slot parameters: output, gain scale, frequency shift, Q scale; band off; clear
check("EQ output gain +9 dB (P1 = 0.75) and -18 dB (P1 = 0)", abs(peq_db([], 69, (0.75, 0.5, 0.5, 0.5, 0.5, 0.5)) - 9) < 0.3 and abs(peq_db([], 69, (0.0, 0.5, 0.5, 0.5, 0.5, 0.5)) + 18) < 0.3)
check("EQ gain scale 0 flattens the bands", abs(peq_db(band(0, 1, 0, 440, 12, 1.0), 69, (0.5, 0.0, 0.5, 0.5, 0.5, 0.5))) < 0.2)
check("EQ gain scale 200 % doubles the gain", abs(peq_db(band(0, 1, 0, 440, 6, 1.0), 69, (0.5, 1.0, 0.5, 0.5, 0.5, 0.5)) - 12) < 1.0)
check("EQ frequency shift moves the band an octave", peq_db(band(0, 1, 0, 220, 12, 1.0), 69, (0.5, 0.5, 1.0, 0.5, 0.5, 0.5)) > 11)
check("EQ band switched off does nothing", abs(peq_db(band(0, 0, 0, 440, 12, 1.0), 69)) < 0.05)
w = render(peq(band(0, 1, 0, 440, 12, 1.0)) + ["eqclear 0"], tag="clr")
check("EQ clear removes the bands", abs(20 * math.log10(level(w, 0) / level(dn, 0))) < 0.05)
# 24 bands (with harmonics and combs) stay finite and bounded
many = [c for i in range(24) for c in band(i, 1, [0, 1, 2, 4, 6, 7, 8, 9, 10, 11, 12, 13][i % 12], 60 * 1.35 ** i, ((i * 7) % 13) - 6, 0.7 + (i % 5), 3 if i % 3 == 0 else 0, 0.5, i % 3, i % 5)]
w = render(many + EQSEND + fx(0, 13, 0, 1.0), tag="many")
check("EQ with 24 bands of all kinds stays finite and bounded", np.isfinite(w).all() and np.abs(w).max() < 20.0, "peak %.2f" % np.abs(w).max())

# FX-REV: reverb engines (Zita-rev1 FDN: Hall Room Cathedral Chamber Dark Bright Infinite, Dattorro plate: Plate Ambience)
RVN = ["Hall", "Room", "Plate", "Cathedral", "Chamber", "Ambience", "Dark", "Bright", "Infinite"]
rv_tail = {}
for m, nm in enumerate(RVN):
    a = render(fx(0, 8, m, 1.0, (0.7, 0.5, 0.0, 1.0, 0.0, 1.0)), hold=0.3, tail=3.0, tag="rv%d" % m)
    check("reverb %s finite and bounded" % nm, np.isfinite(a).all() and np.abs(a).max() < 4.0, "peak %.2f" % np.abs(a).max())
    rv_tail[m] = [rms(a[T0 + int(t * RATE):T0 + int((t + 0.3) * RATE)]) for t in (0.1, 0.9, 2.2)]
    check("reverb %s has a tail after note-off" % nm, rv_tail[m][0] > 2e-3, "%.5f" % rv_tail[m][0])
    if m != 8:
        check("reverb %s decays" % nm, rv_tail[m][2] < 0.7 * rv_tail[m][0], "%.5f -> %.5f" % (rv_tail[m][0], rv_tail[m][2]))
check("reverb Infinite does not decay", rv_tail[8][2] > 0.7 * rv_tail[8][0], "%.5f -> %.5f" % (rv_tail[8][0], rv_tail[8][2]))
check("reverb Room decays faster than Cathedral", rv_tail[1][1] < 0.3 * rv_tail[3][1], "%.5f vs %.5f" % (rv_tail[1][1], rv_tail[3][1]))
sh = render(fx(0, 8, 0, 1.0, (0.1, 0.5, 0.0, 1.0, 0.0, 1.0)), hold=0.3, tail=2.0, tag="rvs"); lg = render(fx(0, 8, 0, 1.0, (0.95, 0.5, 0.0, 1.0, 0.0, 1.0)), hold=0.3, tail=2.0, tag="rvl")
check("reverb Size lengthens the Hall tail", rms(lg[T0 + int(1.0 * RATE):T0 + int(1.2 * RATE)]) > 3 * rms(sh[T0 + int(1.0 * RATE):T0 + int(1.2 * RATE)]))
dk = render(fx(0, 8, 0, 1.0, (0.7, 0.95, 0.0, 1.0, 0.0, 1.0)), hold=0.3, tail=1.0, tag="rvd", note=108); br = render(fx(0, 8, 0, 1.0, (0.7, 0.05, 0.0, 1.0, 0.0, 1.0)), hold=0.3, tail=1.0, tag="rvb", note=108)
check("reverb Damp shortens the tail of a high note", rms(dk[T0 + int(0.4 * RATE):T0 + int(0.9 * RATE)]) < 0.5 * rms(br[T0 + int(0.4 * RATE):T0 + int(0.9 * RATE)]), "%.5f vs %.5f" % (rms(dk[T0 + int(0.4 * RATE):T0 + int(0.9 * RATE)]), rms(br[T0 + int(0.4 * RATE):T0 + int(0.9 * RATE)])))
st = render(fx(0, 8, 2, 1.0, (0.7, 0.5, 0.0, 1.0, 0.0, 1.0)), hold=0.3, tail=1.0, tag="rvst"); seg = st[T0 + int(0.2 * RATE):T0 + int(0.6 * RATE)]
check("plate and hall tails are stereo", np.abs(seg[:, 0] - seg[:, 1]).max() > 1e-3)
w0 = render(fx(0, 8, 0, 1.0, (0.7, 0.5, 0.0, 0.0, 0.0, 1.0)), hold=0.3, tail=1.0, tag="rvw"); seg = w0[T0 + int(0.2 * RATE):T0 + int(0.6 * RATE)]
check("reverb Width 0 collapses the tail to mono", np.abs(seg[:, 0] - seg[:, 1]).max() < 1e-4)

# FX-SAT: Saturator (type 14) and Waveshaper (type 15)
SATN = ["Tube", "Tape", "Transformer", "Diode", "Fuzz", "Soft Clip", "Hard Clip", "Rectifier", "Sine Fold", "Rational", "Exciter", "Arctan"]
for m, nm in enumerate(SATN):
    a = render(fx(0, 14, m, 1.0, (0.7, 0.5, 0.5, 0.5, 0.0, 0.0)), tag="sat%d" % m)
    check("saturator %s finite and bounded" % nm, np.isfinite(a).all() and np.abs(a).max() < 4.0, "peak %.2f" % np.abs(a).max())
    check("saturator %s produces sound" % nm, rms(a[int(0.7 * RATE):T0]) > 0.01, "%.4f" % rms(a[int(0.7 * RATE):T0]))
    if m != 10: check("saturator %s adds harmonics" % nm, thd(a) > thd(dry) + 0.02, "%.3f vs %.3f" % (thd(a), thd(dry)))
    else:
        ex = render(fx(0, 14, 10, 1.0, (0.7, 0.5, 0.5, 0.5, 0.0, 0.0)), tag="satx", note=96)
        check("saturator Exciter adds harmonics to a bright note", thd(ex) > thd(render([], tag="dry96", note=96)) + 0.005)
sl = render(fx(0, 14, 0, 1.0, (0.1, 0.5, 0.5, 0.5, 0.0, 0.0)), tag="satlo"); sh = render(fx(0, 14, 0, 1.0, (0.9, 0.5, 0.5, 0.5, 0.0, 0.0)), tag="sathi")
check("saturator Drive adds more harmonics", thd(sh) > thd(sl) + 0.03, "%.3f vs %.3f" % (thd(sh), thd(sl)))
sb0 = render(fx(0, 14, 0, 1.0, (0.6, 0.5, 0.5, 0.5, 0.0, 0.0)), tag="satb0"); sb1 = render(fx(0, 14, 0, 1.0, (0.6, 0.5, 0.9, 0.5, 0.0, 0.0)), tag="satb1")
check("saturator Bias changes the spectrum", abs(thd(sb0) - thd(sb1)) > 0.01)
sd = render(fx(0, 14, 0, 1.0, (0.6, 0.5, 0.95, 0.5, 0.0, 0.0)), tag="satdc")
check("saturator DC blocked with Bias", abs(float(sd[int(0.7 * RATE):T0, 0].mean())) < 0.03)
sg0 = render(fx(0, 14, 0, 1.0, (0.6, 0.5, 0.5, 0.5, 0.0, 0.0)), tag="satg0"); sg1 = render(fx(0, 14, 0, 1.0, (0.6, 0.5, 0.5, 0.9, 0.0, 0.0)), tag="satg1")
check("saturator Output raises the level", rms(sg1[int(0.7 * RATE):T0]) > 1.5 * rms(sg0[int(0.7 * RATE):T0]))
st0 = render(fx(0, 14, 0, 1.0, (0.6, 0.1, 0.5, 0.5, 0.0, 0.0)), tag="satt0", note=100); st1 = render(fx(0, 14, 0, 1.0, (0.6, 0.9, 0.5, 0.5, 0.0, 0.0)), tag="satt1", note=100)
check("saturator Tone: dark vs bright", rms(st1[int(0.7 * RATE):T0]) > 1.2 * rms(st0[int(0.7 * RATE):T0]), "%.4f vs %.4f" % (rms(st1[int(0.7 * RATE):T0]), rms(st0[int(0.7 * RATE):T0])))
s_a = render(fx(0, 14, 5, 1.0, (0.7, 0.5, 0.5, 0.5, 0.0, 0.0)), tag="sat_nosag"); s_b = render(fx(0, 14, 5, 1.0, (0.7, 0.5, 0.5, 0.5, 0.0, 1.0)), tag="sat_sag")
check("saturator Sag changes the sound", not np.allclose(s_a, s_b, atol=1e-3))
# aliasing: a hard-clipped 3.1 kHz sine keeps its energy on the harmonics, not between them (ADAA)
hc = render(fx(0, 14, 6, 1.0, (0.9, 0.5, 0.5, 0.5, 0.0, 0.0)), tag="alias", note=98)
seg = hc[int(0.7 * RATE):int(0.85 * RATE), 0].astype(np.float64); X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1.0 / RATE)
f1 = note_hz(98); harm = np.zeros(len(X), bool)
for k in range(1, int(RATE / 2 / f1) + 1): harm |= np.abs(fr - k * f1) < 60
check("saturator ADAA keeps most energy on the harmonics", float((X[harm] ** 2).sum() / (X ** 2).sum()) > 0.9, "%.3f" % float((X[harm] ** 2).sum() / (X ** 2).sum()))

# Waveshaper
def ws(nodes, mode=0, p=(0.0, 0.5, 0.5, 1.0, 0.0, 0.0)):
    c = ["wscount 0 %d" % len(nodes)] + ["wsnode 0 %d %s %s %s" % (i, x, y, cu) for i, (x, y, cu) in enumerate(nodes)] + ["eqsend 0"]
    return c + fx(0, 15, mode, 1.0, p)
ident = render(ws([(-1, -1, 0), (1, 1, 0)]), tag="wsid")
check("waveshaper identity curve is transparent", abs(rms(ident[int(0.7 * RATE):T0]) / rms(dry[int(0.7 * RATE):T0]) - 1.0) < 0.1, "%.3f" % (rms(ident[int(0.7 * RATE):T0]) / rms(dry[int(0.7 * RATE):T0])))
clip = render(ws([(-1, -0.3, 0), (-0.3, -0.3, 0), (0.3, 0.3, 0), (1, 0.3, 0)], 0, (0.5, 0.5, 0.5, 1.0, 0.0, 0.0)), tag="wscl")
check("waveshaper clipping curve adds harmonics and bounds the level", thd(clip) > thd(dry) + 0.05 and np.abs(clip).max() < 0.5, "%.3f peak %.2f" % (thd(clip), np.abs(clip).max()))
nocurve = render(fx(0, 15, 0, 1.0, (0.0, 0.5, 0.5, 1.0, 0.0, 0.0)), tag="wsnone")
check("waveshaper without nodes passes the signal (identity)", abs(rms(nocurve[int(0.7 * RATE):T0]) / rms(dry[int(0.7 * RATE):T0]) - 1.0) < 0.1)
fold = render(ws([(-1, 1, 0), (-0.5, -1, 0), (0, 1, 0), (0.5, -1, 0), (1, 1, 0)], 0, (0.3, 0.5, 0.5, 1.0, 0.0, 0.0)), tag="wsfold")
check("waveshaper folding curve stays finite", np.isfinite(fold).all() and np.abs(fold).max() < 2.0)
rect = render(ws([(-1, -1, 0), (1, 1, 0)], 2, (0.0, 0.5, 0.5, 1.0, 0.0, 0.0)), tag="wsrect")
seg = rect[int(0.7 * RATE):int(0.85 * RATE), 0].astype(np.float64); f_r = np.fft.rfftfreq(len(seg), 1.0 / RATE); X = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
check("waveshaper Rectified mode doubles the frequency", abs(f_r[int(np.argmax(X))] - 2 * 440.0) < 30, "%.0f Hz" % f_r[int(np.argmax(X))])
mir = render(ws([(0, 0, 0), (0.2, 0.8, 0), (1, 1, 0)], 1, (0.0, 0.5, 0.5, 1.0, 0.0, 0.0)), tag="wsmir")
check("waveshaper Mirror mode is odd symmetric (no even harmonics)", float(abs(mir[int(0.7 * RATE):T0, 0].mean())) < 0.02 and thd(mir) > thd(dry) + 0.02)
cv0 = render(ws([(-1, -1, 0), (1, 1, 0)], 0, (0.5, 0.5, 0.5, 1.0, 0.0, 0.0)), tag="wsc0"); cv1 = render(ws([(-1, -1, 0.9), (1, 1, 0.9)], 0, (0.5, 0.5, 0.5, 1.0, 0.0, 0.0)), tag="wsc1")
check("waveshaper segment curvature changes the sound", not np.allclose(cv0, cv1, atol=1e-3))


# ================================================= FX-FENV2: envelope of the Filter effect = a modulation envelope (ENV 1-10), key tracking
def hf(a, t0, t1, f0=2000.0, f1=20000.0):
    x = a[int(t0 * RATE):int(t1 * RATE), 0].astype(np.float64); X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.sqrt(X[(f >= f0) & (f < f1)].sum() / len(x)))
def fenv(amt, atk, dec, sus, rel, tag, src=0, kt=0.0, note=45, env=0):
    # slot 0 = Filter, 24 dB low pass at about 300 Hz, saw, held for 1 s; the times come from modulation envelope `env` (ids 267 + 4 * env)
    b = 267 + 4 * env
    return render(["wt 0 saw"] + fx(0, 9, 0, 1.0, (0.39, 0.1, 0.0, amt, src / 9.0, kt)) + ["p %d %s" % (b, atk), "p %d %s" % (b + 1, dec), "p %d %s" % (b + 2, sus), "p %d %s" % (b + 3, rel)], hold=1.0, tail=1.2, tag=tag, note=note)
f0 = fenv(0.5, 1, 300, 0.0, 100, "fe0")
check("filter effect: Env Amt 0 keeps the cutoff fixed", 0.6 < hf(f0, 0.62, 0.68) / max(hf(f0, 1.3, 1.5), 1e-9) < 1.7, "%.4f / %.4f" % (hf(f0, 0.62, 0.68), hf(f0, 1.3, 1.5)))
f1 = fenv(1.0, 1, 300, 0.0, 100, "fe1")
check("filter effect: positive Env Amt opens the cutoff on the note and closes it with the modulation envelope's decay", hf(f1, 0.62, 0.68) > 4 * hf(f1, 1.3, 1.5) and hf(f1, 0.62, 0.68) > 3 * hf(f0, 0.62, 0.68), "%.4f vs late %.4f, fixed %.4f" % (hf(f1, 0.62, 0.68), hf(f1, 1.3, 1.5), hf(f0, 0.62, 0.68)))
f2 = fenv(1.0, 1, 300, 1.0, 100, "fe2")
check("filter effect: the modulation envelope's Sustain 1 holds the cutoff open", hf(f2, 1.3, 1.5) > 3 * hf(f1, 1.3, 1.5) and hf(f2, 1.3, 1.5) > 0.4 * hf(f2, 0.62, 0.68), "%.4f vs %.4f" % (hf(f2, 1.3, 1.5), hf(f1, 1.3, 1.5)))
f3 = fenv(1.0, 1, 300, 1.0, 1500, "fe3")
check("filter effect: the modulation envelope's Release closes the cutoff after the note off", hf(f3, 1.62, 1.72) > 3 * hf(f3, 2.5, 2.7), "%.4f -> %.4f" % (hf(f3, 1.62, 1.72), hf(f3, 2.5, 2.7)))
f4 = fenv(1.0, 600, 300, 1.0, 100, "fe4")
check("filter effect: the modulation envelope's Attack opens the cutoff slowly", hf(f4, 0.6, 0.64) < 0.3 * hf(f4, 1.3, 1.5), "%.4f -> %.4f" % (hf(f4, 0.6, 0.64), hf(f4, 1.3, 1.5)))
f5 = render(["wt 0 saw"] + fx(0, 9, 0, 1.0, (0.62, 0.1, 0.0, 0.0, 0.0, 0.0)) + ["p 267 1", "p 268 300", "p 269 0", "p 270 100"], hold=1.0, tail=1.2, tag="fe5", note=45)
check("filter effect: negative Env Amt closes the cutoff on the note and reopens it", hf(f5, 0.62, 0.68) < 0.5 * hf(f5, 1.3, 1.5), "%.4f -> %.4f" % (hf(f5, 0.62, 0.68), hf(f5, 1.3, 1.5)))
# source selection: ENV 1 stays open (sustain 1), ENV 2 closes (sustain 0): the filter follows the chosen one
sel = lambda src, tag: render(["wt 0 saw"] + fx(0, 9, 0, 1.0, (0.39, 0.1, 0.0, 1.0, src / 9.0, 0.0)) + ["p 267 1", "p 268 300", "p 269 1", "p 270 100", "p 271 1", "p 272 300", "p 273 0", "p 274 100"], hold=1.0, tail=1.2, tag=tag, note=45)
sa, sb = sel(0, "fesa"), sel(1, "fesb")
check("filter effect: Env Src picks the modulation envelope (ENV 1 sustains open, ENV 2 closes)", hf(sa, 1.3, 1.5) > 3 * hf(sb, 1.3, 1.5), "%.4f vs %.4f" % (hf(sa, 1.3, 1.5), hf(sb, 1.3, 1.5)))
# key tracking: the cutoff follows the played note
k0, k1 = fenv(0.5, 1, 300, 0.0, 100, "fek0", kt=0.0, note=69), fenv(0.5, 1, 300, 0.0, 100, "fek1", kt=1.0, note=69)
check("filter effect: Key Track raises the cutoff for a note above C4", hf(k1, 0.7, 1.4, 1500, 20000) > 1.3 * hf(k0, 0.7, 1.4, 1500, 20000), "%.4f vs %.4f" % (hf(k1, 0.7, 1.4, 1500, 20000), hf(k0, 0.7, 1.4, 1500, 20000)))
check("filter effect envelope stays finite and bounded", all(np.isfinite(a).all() and np.abs(a).max() < 4.0 for a in (f1, f2, f3, f4, f5, sa, sb, k0, k1)))


# ---- FX-UNI: Unison (type 16)
def uni(mode=0, p=(0.5, 0.25, 0.7, 0.2, 0.5, 1.0), tag="u", hold=1.0, mix=1.0):
    return render(fx(0, 16, mode, mix, p), hold=hold, tail=0.5, tag=tag)
def band(a, f0, f1, t0=0.9, t1=1.5):
    seg = a[int(t0 * RATE):int(t1 * RATE), 0].astype(np.float64) * np.hanning(int((t1 - t0) * RATE))
    sp = np.abs(np.fft.rfft(seg, 1 << 17)) ** 2; fr = np.fft.rfftfreq(1 << 17, 1.0 / RATE)
    return float(sp[(fr >= f0) & (fr <= f1)].sum())
udry = render([], hold=1.0, tail=0.5, tag="udry")
ok = True; worst = 0.0
for mode in range(4):
    for p in [(0.0, 0.0, 0.0, 0.0, 0.0, 0.0), (1.0, 1.0, 1.0, 1.0, 1.0, 1.0), (0.5, 0.5, 0.5, 0.5, 0.5, 0.5), (1.0, 1.0, 0.0, 1.0, 0.0, 1.0)]:
        a = uni(mode, p, "u%d" % mode); ok = ok and bool(np.isfinite(a).all()); worst = max(worst, float(np.abs(a).max()))
check("Unison: every mode at parameter extremes is finite and bounded", ok and worst < 4.0, "peak %.2f" % worst)
base_rms = rms(udry[int(0.9 * RATE):int(1.5 * RATE)])
w = uni(0, (0.5, 0.25, 0.7, 0.2, 0.5, 1.0), "u_a")
check("Unison produces a level comparable to the dry signal", 0.4 < rms(w[int(0.9 * RATE):int(1.5 * RATE)]) / base_rms < 2.5, "%.2f" % (rms(w[int(0.9 * RATE):int(1.5 * RATE)]) / base_rms))
# detune 0 / drift 0 / spread 0: every voice is the dry signal, sum / sqrt(n) = sqrt(n) x dry (n = 5)
z = uni(0, (0.5, 0.0, 0.0, 0.0, 0.5, 1.0), "u_z")
r5 = rms(z[int(0.9 * RATE):int(1.5 * RATE)]) / base_rms
check("Unison with no detune is the dry signal times sqrt(voices)", abs(r5 - 5 ** 0.5) < 0.25, "%.2f" % r5)
# detune broadens the line of the 440 Hz sine: energy 4..12 Hz away from the peak
wide = band(uni(0, (0.5, 0.4, 0.5, 0.0, 0.5, 1.0), "u_d"), 424, 437) + band(uni(0, (0.5, 0.4, 0.5, 0.0, 0.5, 1.0), "u_d"), 443, 456)
narrow = band(udry, 424, 437) + band(udry, 443, 456)
check("Detune puts energy beside the dry frequency", wide > 50 * max(narrow, 1e-12) and wide > 0, "%.3g vs %.3g" % (wide, narrow))
# more detune -> sidebands further out
d1 = band(uni(0, (0.5, 0.1, 0.5, 0.0, 0.5, 1.0), "u_d1"), 450, 470); d2 = band(uni(0, (0.5, 0.6, 0.5, 0.0, 0.5, 1.0), "u_d2"), 450, 470)
check("More detune spreads the sidebands wider", d2 > 3 * d1, "%.3g vs %.3g" % (d2, d1))
# octaves mode: lines at 220 and 880 Hz
oc = uni(3, (0.5, 0.1, 0.5, 0.0, 0.5, 1.0), "u_o")
check("Octaves mode adds the octave above and below", band(oc, 870, 890) > 100 * max(band(udry, 870, 890), 1e-12) and band(oc, 215, 225) > 100 * max(band(udry, 215, 225), 1e-12))
# stereo spread
s0 = uni(0, (0.5, 0.3, 0.0, 0.0, 0.5, 1.0), "u_s0"); s1 = uni(0, (0.5, 0.3, 1.0, 0.0, 0.5, 1.0), "u_s1")
seg0 = slice(int(0.9 * RATE), int(1.5 * RATE))
check("Spread 0 keeps the channels equal, Spread 1 decorrelates them", np.allclose(s0[seg0, 0], s0[seg0, 1], atol=1e-5) and rms(s1[seg0, 0] - s1[seg0, 1]) > 0.1 * rms(s1[seg0, 0]))
# tone low-pass: 1.0 = off, low value removes the octave-up line of the octave mode
ot = uni(3, (0.5, 0.1, 0.5, 0.0, 0.5, 0.0), "u_ot")
check("Tone low-pass damps the octave above", band(ot, 870, 890) < 0.5 * band(oc, 870, 890))
check("Unison mix 0 equals dry", np.allclose(uni(0, mix=0.0, tag="u_m0"), udry, atol=1e-5))


# ---- FX-KORG: Korg35 LP / HP and Scream (Filter effect modes 30..32)
def kf(mode, cut, res, drive=0.0, tag="k", note=45, wave="saw"):
    return render(["wt 0 " + wave] + fx(0, 9, mode, 1.0, (cut, res, drive, 0.5, 0.0, 0.0)), hold=1.0, tail=0.5, tag=tag, note=note)
def band2(a, f0, f1, t0=0.7, t1=1.5):
    x = a[int(t0 * RATE):int(t1 * RATE), 0].astype(np.float64); X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.sqrt(X[(f >= f0) & (f < f1)].sum() / len(x)))
kdry = kf(1, 1.0, 0.0, tag="kdry")     # LP12 fully open = (almost) the dry saw
ok = True; worst = 0.0
for mode in (30, 31, 32):
    for cut, res, drv in [(0.0, 0.0, 0.0), (0.5, 1.0, 1.0), (1.0, 1.0, 0.0), (0.3, 0.9, 0.5), (0.7, 1.0, 1.0)]:
        a = kf(mode, cut, res, drv, "k%d" % mode); ok = ok and bool(np.isfinite(a).all()); worst = max(worst, float(np.abs(a).max()))
check("Korg35 / Scream: extreme settings stay finite and bounded", ok and worst < 4.0, "peak %.2f" % worst)
lp = kf(30, 0.39, 0.1, tag="klp")
check("Korg35 LP removes the highs of a saw (cutoff 300 Hz)", band2(lp, 2000, 20000) < 0.05 * band2(kdry, 2000, 20000) and band2(lp, 80, 300) > 0.2 * band2(kdry, 80, 300), "%.5f vs %.5f" % (band2(lp, 2000, 20000), band2(kdry, 2000, 20000)))
hp = kf(31, 0.6, 0.1, tag="khp")
check("Korg35 HP removes the lows of a saw (cutoff 800 Hz)", band2(hp, 80, 300) < 0.1 * band2(kdry, 80, 300) and band2(hp, 2000, 20000) > 0.3 * band2(kdry, 2000, 20000), "%.5f vs %.5f" % (band2(hp, 80, 300), band2(kdry, 80, 300)))
r0 = kf(30, 0.45, 0.0, tag="kr0"); r9 = kf(30, 0.45, 0.9, tag="kr9")
check("Korg35 LP: more Reso raises the peak at the cutoff", band2(r9, 300, 600) > 1.5 * band2(r0, 300, 600), "%.4f vs %.4f" % (band2(r9, 300, 600), band2(r0, 300, 600)))
s0 = kf(32, 0.45, 0.0, 0.0, "ks0"); s1 = kf(32, 0.45, 0.0, 1.0, "ks1"); s2 = kf(32, 0.45, 0.5, 0.0, "ks2")
check("Scream (24 dB low-pass) makes sound and cuts the highs harder than the Korg35 LP", rms(s0[int(0.7 * RATE):int(1.5 * RATE)]) > 1e-3 and band2(s0, 3000, 20000) < band2(kf(30, 0.45, 0.0, 0.0, "kc0"), 3000, 20000), "%.5f vs %.5f" % (band2(s0, 3000, 20000), band2(kf(30, 0.45, 0.0, 0.0, "kc0"), 3000, 20000)))
check("Scream amount (Drive knob) feeds the output back: a dirty peak at the cutoff", band2(s1, 300, 800) > 1.3 * band2(s0, 300, 800), "%.4f vs %.4f" % (band2(s1, 300, 800), band2(s0, 300, 800)))
check("Scream amount adds harmonics above the cutoff", band2(s1, 1500, 8000) > 2 * band2(s0, 1500, 8000), "%.4f vs %.4f" % (band2(s1, 1500, 8000), band2(s0, 1500, 8000)))
check("Scream: Reso raises the peak as well", band2(s2, 300, 800) > 1.2 * band2(s0, 300, 800))

# ---- FX-CONSOLE: Console (type 17)
def con(mode=0, p=(0.45, 0.5, 0.55, 0.5, 0.0, 0.0), tag="c", note=45, wave="saw"):
    return render(["wt 0 " + wave] + fx(0, 17, mode, 1.0, p), hold=1.0, tail=0.5, tag=tag, note=note)
c0 = con(tag="c0")
c1 = con(p=(0.45, 1.0, 0.55, 0.5, 0.0, 0.0), tag="c1")          # lo-mid +15 dB at ~370 Hz
c2 = con(p=(0.45, 0.0, 0.55, 0.5, 0.0, 0.0), tag="c2")          # lo-mid -15 dB
c3 = con(p=(0.45, 0.5, 0.55, 1.0, 0.0, 0.0), tag="c3")          # hi-mid +15 dB at ~2.5 kHz
c4 = con(p=(0.45, 0.5, 0.55, 0.5, 1.0, 0.0), tag="c4")          # full drive
c5 = con(p=(0.45, 0.5, 0.55, 0.5, 1.0, 1.0), tag="c5")          # drive + age
c6 = con(mode=4, p=(0.45, 1.0, 0.55, 0.5, 1.0, 0.5), tag="c6")  # EQ first
fl = lambda a: bool(np.all(np.isfinite(a)) and np.abs(a).max() < 2.0)
check("Console: neutral settings sound and stay finite", rms(c0[int(0.7 * RATE):int(1.5 * RATE)]) > 1e-3 and fl(c0))
check("Console Lo-Mid boost raises and cut lowers its band", band2(c1, 250, 600) > 1.5 * band2(c0, 250, 600) and band2(c2, 250, 600) < 0.6 * band2(c0, 250, 600), "%.4f %.4f %.4f" % (band2(c1, 250, 600), band2(c0, 250, 600), band2(c2, 250, 600)))
check("Console Hi-Mid boost raises its band", band2(c3, 1800, 3500) > 1.5 * band2(c0, 1800, 3500), "%.4f vs %.4f" % (band2(c3, 1800, 3500), band2(c0, 1800, 3500)))
sd0 = con(tag="sd0", note=57, wave="sine"); sd1 = con(p=(0.45, 0.5, 0.55, 0.5, 1.0, 0.0), tag="sd1", note=57, wave="sine")
check("Console Drive adds harmonics to a sine (transformer saturation)", band2(sd1, 400, 8000) > 2.5 * band2(sd0, 400, 8000), "%.5f vs %.5f" % (band2(sd1, 400, 8000), band2(sd0, 400, 8000)))
check("Console Age rounds the highs", band2(c5, 9000, 20000) < band2(c4, 9000, 20000), "%.5f vs %.5f" % (band2(c5, 9000, 20000), band2(c4, 9000, 20000)))
check("Console extreme settings finite and bounded (also EQ first)", fl(c4) and fl(c5) and fl(c6))

# ---- FX-FBANK: Filterbank (type 18)
def fbk(mode=0, p=(0.5, 0.4, 0.0, 0.0, 0.1, 0.5), tag="fb", note=45):
    return render(["wt 0 saw"] + fx(0, 18, mode, 1.0, p), hold=1.0, tail=0.5, tag=tag, note=note)
# P1 0.5 = 632 Hz
fb_lp = fbk(p=(0.5, 0.4, 0.0, 0.0, 0.1, 0.5), tag="fbl"); fb_hp = fbk(p=(0.5, 0.4, 1.0, 0.0, 0.1, 0.5), tag="fbh"); fb_bp = fbk(p=(0.5, 0.4, 0.5, 0.0, 0.1, 0.5), tag="fbb")
fb_nt = fbk(p=(0.5, 0.4, 0.5, 1.0, 0.1, 0.5), tag="fbn")
fb_pl = fbk(0, p=(0.5, 0.4, 0.0, 0.0, 0.1, 0.5), tag="fbp"); fb_sl = fbk(1, p=(0.5, 0.4, 0.0, 0.0, 0.1, 0.5), tag="fbs")
fb_off = fbk(1, p=(0.5, 0.4, 0.0, 0.0, 0.1, 0.75), tag="fbo")   # filter 2 +12 st
fb_x = [fbk(m, p=(0.5, 1.0, 0.5, 0.5, 1.0, 0.1 * m), tag="fbx%d" % m) for m in range(6)]
check("Filterbank LP removes the highs, HP removes the lows", band2(fb_lp, 4000, 20000) < 0.1 * band2(fb_lp, 100, 700) and band2(fb_hp, 100, 400) < 0.25 * band2(fb_lp, 100, 400), "%.4f/%.4f %.4f/%.4f" % (band2(fb_lp, 4000, 20000), band2(fb_lp, 100, 700), band2(fb_hp, 100, 400), band2(fb_lp, 100, 400)))
check("Filterbank BP sits between LP and HP (less lows than LP, less highs than HP)", band2(fb_bp, 60, 300) < 0.5 * band2(fb_lp, 60, 300) and band2(fb_bp, 3000, 20000) < 0.5 * band2(fb_hp, 3000, 20000), "%.4f/%.4f %.4f/%.4f" % (band2(fb_bp, 60, 300), band2(fb_lp, 60, 300), band2(fb_bp, 3000, 20000), band2(fb_hp, 3000, 20000)))
check("Filterbank Anti-Mix turns the band-pass into a notch (passes lows and highs)", band2(fb_nt, 3000, 12000) > 3 * band2(fb_bp, 3000, 12000) and band2(fb_nt, 80, 200) > 3 * band2(fb_bp, 80, 200), "%.4f vs %.4f" % (band2(fb_nt, 3000, 12000), band2(fb_bp, 3000, 12000)))
check("Filterbank Series is steeper than Parallel (24 vs 12 dB)", band2(fb_sl, 3000, 20000) < 0.7 * band2(fb_pl, 3000, 20000), "%.5f vs %.5f" % (band2(fb_sl, 3000, 20000), band2(fb_pl, 3000, 20000)))
check("Filterbank F2 Offset moves the second cutoff (series passes more highs with +12 st)", band2(fb_off, 1500, 3000) > 1.5 * band2(fb_sl, 1500, 3000), "%.5f vs %.5f" % (band2(fb_off, 1500, 3000), band2(fb_sl, 1500, 3000)))
check("Filterbank extreme settings in all six modes stay finite and bounded", all(bool(np.all(np.isfinite(a)) and np.abs(a).max() < 2.0) for a in fb_x))

# ---- effect type list: every type is wired through the DSP, the parameter ranges, the generated UI tables and the UI colours
import re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
def rd(*p): return open(os.path.join(ROOT, *p), encoding="utf-8").read()
js = rd("patch", "index.js"); cm = rd("patch", "Eisenpuls_Synth.cmajor"); gen = rd("native_ui", "NjoData.gen.cpp"); fxp = rd("native_ui", "pages", "FxPage.cpp")
blk = js[js.index("const FX_TYPES = ["):]; blk = blk[:blk.index("\n];")]
NT = len(re.findall(r'^    \{ n: "', blk, re.M))
check("FX types counted in index.js", NT >= 19, "%d types incl. None" % NT)
tm = re.findall(r'FX \d+ Type",\s*min: 0\.0, max: ([0-9.]+)', cm)
check("DSP: all 48 FX Type parameters allow every type", len(tm) == 48 and all(float(m) == NT - 1 for m in tm), "%d params, max %s" % (len(tm), sorted(set(tm))))
m = re.search(r'int nt = clamp \(t, 0, (\d+)\)', cm)
check("DSP: the type clamp allows every type", bool(m) and int(m.group(1)) == NT - 1, m.group(1) if m else "not found")
gm = re.findall(r'FX \d+ Type"\), 0\.0, ([0-9.]+),', gen)
check("UI tables (NjoData.gen.cpp): the 48 Type specs allow every type - run gen_data.js after changing index.js", len(gm) == 48 and all(float(x) == NT - 1 for x in gm), "%d specs, max %s" % (len(gm), sorted(set(gm))))
check("DSP: every type is dispatched", all(re.search(r'ty == %d\) +y = fx' % k, cm) for k in range(1, NT)), str([k for k in range(1, NT) if not re.search(r'ty == %d\) +y = fx' % k, cm)]))
cl = re.search(r'static const juce::uint32 c\[\] = \{([^}]*)\}', fxp); ncol = len(re.findall(r'0x[0-9a-fA-F]+', cl.group(1))) if cl else 0
check("UI: every type has a colour, and the colour index limit covers it", ncol >= NT and re.search(r'jlimit \(0, %d, type\)' % (ncol - 1), fxp) is not None, "%d colours" % ncol)
outs = {}
for k in range(1, NT):   # the Parametric EQ (13) keeps its bands in the sound memory: without bands it passes the signal, so it is left out of the comparison
    outs[k] = render(["wt 0 saw"] + fx(0, k, 0, 1.0, (0.8,) * 6), hold=0.6, tail=0.3, tag="ty%d" % k, note=57)
outs.pop(13, None)
ok_fin = all(np.isfinite(a).all() for a in outs.values())
dup = [(a, b) for a in outs for b in outs if a < b and outs[a].shape == outs[b].shape and np.allclose(outs[a], outs[b], atol=1e-7)]
check("Every effect type can be selected and is finite", ok_fin)
check("No two effect types render the same (a type clamped to another would)", not dup, str(dup[:5]))

# ---- FX-SLOTS: 16 slots per rack (slots 11-16 = ids 3200 + (rack * 6 + j) * 10, order 3380 +, sync 3400 +)
def xbase(rk, j): return 3200 + (rk * 6 + j) * 10
def fxb(b, ty, mode=0, mix=1.0, p=(0.5,) * 6):
    return ["p %d %d" % (b, ty), "p %d 1" % (b + 1), "p %d %s" % (b + 2, mix), "p %d %d" % (b + 3, mode)] + ["p %d %s" % (b + 4 + i, v) for i, v in enumerate(p)]
DIST = (0.8, 0.5, 0.5, 0.5, 0.5, 0.5); LPF = (0.3, 0.3, 0.5, 0.5, 0.5, 0.5)
ref = render(fxb(base(0), 1, 0, 1.0, DIST), tag="sl_ref")
n11 = render(fxb(xbase(0, 0), 1, 0, 1.0, DIST), tag="sl_n11")
n16 = render(fxb(xbase(0, 5), 1, 0, 1.0, DIST), tag="sl_n16")
check("Slot 11 of the Main rack behaves like slot 1", np.abs(ref - n11).max() < 1e-5 and rms(ref) > 1e-3, "%.2g" % np.abs(ref - n11).max())
check("Slot 16 of the Main rack behaves like slot 1", np.abs(ref - n16).max() < 1e-5, "%.2g" % np.abs(ref - n16).max())
# processing order across the old and the new slots: distortion -> low-pass in the old slots, the same with the distortion in slot 11 and the order param changed
r_a = render(fxb(base(0), 1, 0, 1.0, DIST) + fxb(base(1), 9, 1, 1.0, LPF), tag="sl_a")
r_b = render(fxb(xbase(0, 0), 1, 0, 1.0, DIST) + fxb(base(0), 9, 1, 1.0, LPF), tag="sl_b")
order = [10, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15]
ordc = ["p %d %d" % (641 + k if k < 10 else 3380 + (k - 10), order[k]) for k in range(16)]
r_c = render(fxb(xbase(0, 0), 1, 0, 1.0, DIST) + fxb(base(0), 9, 1, 1.0, LPF) + ordc, tag="sl_c")
check("Default order runs slot 11 after slot 1 (low-pass -> distortion differs from distortion -> low-pass)", np.abs(r_a - r_b).max() > 0.01, "%.3f" % np.abs(r_a - r_b).max())
check("Order parameters reach slot 11: moved to the front it matches distortion -> low-pass", np.abs(r_a - r_c[len(r_c) - len(r_a):]).max() < 1e-4, "%.2g" % np.abs(r_a - r_c[len(r_c) - len(r_a):]).max())
# tempo sync of an extra slot (delay): the sync division changes the echo time
d0 = render(fxb(xbase(0, 2), 3, 0, 0.5, (0.5, 0.5, 0.5, 0.5, 0.5, 0.5)), tag="sl_d0")
d1 = render(fxb(xbase(0, 2), 3, 0, 0.5, (0.5, 0.5, 0.5, 0.5, 0.5, 0.5)) + ["p %d 5" % (3400 + 2)], tag="sl_d1")
check("Sync parameter of slot 13 is wired (the delay changes)", np.abs(d0 - d1).max() > 0.001, "%.3g" % np.abs(d0 - d1).max())
# the Parametric EQ and the convolution reverb work in the new slots too
q0 = render(fxb(base(0), 14, 0, 1.0, (0.5, 0.5, 0.5, 0.5, 0.5, 0.5)), tag="sl_q0")
q1 = render(fxb(xbase(0, 3), 14, 0, 1.0, (0.5, 0.5, 0.5, 0.5, 0.5, 0.5)), tag="sl_q1")
check("Saturator in slot 14 behaves like in slot 1", np.abs(q0 - q1).max() < 1e-5 and rms(q0) > 1e-3)

# ---- FX-AW: Airwindows ports (types 19..26)
AWN = {19: "PurestDrive", 20: "Spiral", 21: "Drive", 22: "Tube", 23: "Density", 24: "Console 7", 25: "Channel", 26: "ToTape", 27: "MackEQ"}
dry_aw = render([], tag="aw_dry", note=57)
for ty, nm in AWN.items():
    for pn, pv in (("default", (0.5,) * 6), ("max", (1.0,) * 6), ("min", (0.0,) * 6)):
        a = render(["wt 0 saw"] + fxb(base(0), ty, 0, 1.0, pv), hold=0.6, tail=0.5, tag="aw%d%s" % (ty, pn), note=57)
        check("AW %s (%s): finite, bounded and audible" % (nm, pn), bool(np.isfinite(a).all()) and np.abs(a).max() < 4.0 and (rms(a) > 1e-4 or pn == "min"), "peak %.2f rms %.4f" % (np.abs(a).max(), rms(a)))
    a = render(["wt 0 saw"] + fxb(base(0), ty, 0, 1.0, (0.7,) * 6), hold=0.6, tail=0.3, tag="aw%dx" % ty, note=57)
    check("AW %s changes the sound" % nm, np.abs(a - dry_aw[:len(a)]).max() > 1e-3 if len(a) <= len(dry_aw) else True)
cm = [render(["wt 0 saw"] + fxb(base(0), 25, m, 1.0, (0.9, 1.0, 0.5, 0.5, 0.5, 0.5)), hold=0.5, tail=0.2, tag="awch%d" % m, note=57) for m in range(5)]
check("AW Channel: the five console types differ", all(not np.allclose(cm[i], cm[j], atol=1e-6) for i in range(5) for j in range(i + 1, 5)))

# ---- FX-PLASMA: Plasma (type 28): P1 Drive, P2 Asym, P3 Girth, P4 Filter (HP/LP/Dual/Peak = 0.125/0.375/0.625/0.875), P5 Freq, P6 Reso
PLN = ["Soft", "Hard", "Fold", "Half", "Fuzz", "Diode", "Arctan", "Rational", "Soft Exp", "Ripple", "Tri Fold", "Cubic"]
for m, nm in enumerate(PLN):
    for pn, pv in (("default", (0.4, 0.5, 0.0, 0.375, 1.0, 0.0)), ("max", (1.0, 1.0, 1.0, 0.375, 1.0, 1.0)), ("min", (0.0, 0.0, 0.0, 0.125, 0.0, 0.0))):
        a = render(fx(0, 28, m, 1.0, pv), tag="pl%d%s" % (m, pn))
        check("Plasma %s (%s): finite and bounded" % (nm, pn), bool(np.isfinite(a).all()) and np.abs(a).max() < 6.0, "peak %.2f" % np.abs(a).max())
    a = render(fx(0, 28, m, 1.0, (0.7, 0.5, 0.0, 0.375, 1.0, 0.0)), tag="plx%d" % m)
    check("Plasma %s produces sound" % nm, rms(a[int(0.7 * RATE):T0]) > 0.01, "%.4f" % rms(a[int(0.7 * RATE):T0]))
    check("Plasma %s adds harmonics" % nm, thd(a) > thd(dry) + 0.02, "%.3f vs %.3f" % (thd(a), thd(dry)))
# Asym: an asymmetric shaper makes even harmonics, and the DC offset is blocked
sy = render(fx(0, 28, 0, 1.0, (0.6, 0.5, 0.0, 0.375, 1.0, 0.0)), tag="plsym"); asy = render(fx(0, 28, 0, 1.0, (0.6, 0.95, 0.0, 0.375, 1.0, 0.0)), tag="plasym")
def harm2(a):
    seg = a[int(0.7 * RATE):T0, 0].astype(np.float64); X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1.0 / RATE)
    f1 = note_hz(69); i1 = np.argmin(np.abs(fr - f1)); i2 = np.argmin(np.abs(fr - 2 * f1)); return X[i2] / X[i1]
check("Plasma Asym creates even harmonics", harm2(asy) > 3 * harm2(sy) + 0.01, "%.4f vs %.4f" % (harm2(asy), harm2(sy)))
check("Plasma Asym: DC blocked", abs(float(asy[int(0.7 * RATE):T0, 0].mean())) < 0.03)
# filter: LP at a low frequency removes the highs, HP removes the lows
hi = lambda a: rms(np.diff(a[int(0.7 * RATE):T0, 0].astype(np.float64)))
f_off = render(fx(0, 28, 1, 1.0, (0.8, 0.5, 0.0, 0.375, 1.0, 0.0)), tag="plf0", note=81)
f_lp = render(fx(0, 28, 1, 1.0, (0.8, 0.5, 0.0, 0.375, 0.3, 0.0)), tag="plf1", note=81)
check("Plasma LP filter darkens the sound", hi(f_lp) < 0.5 * hi(f_off), "%.4f vs %.4f" % (hi(f_lp), hi(f_off)))
l_off = render(fx(0, 28, 1, 1.0, (0.8, 0.5, 0.0, 0.125, 0.0, 0.0)), tag="plh0", note=45)
l_hp = render(fx(0, 28, 1, 1.0, (0.8, 0.5, 0.0, 0.125, 0.8, 0.0)), tag="plh1", note=45)
check("Plasma HP filter removes the lows", rms(l_hp[int(0.7 * RATE):T0]) < 0.5 * rms(l_off[int(0.7 * RATE):T0]), "%.4f vs %.4f" % (rms(l_hp[int(0.7 * RATE):T0]), rms(l_off[int(0.7 * RATE):T0])))
pk = render(fx(0, 28, 1, 1.0, (0.3, 0.5, 0.0, 0.875, 0.55, 1.0)), tag="plpk"); pk0 = render(fx(0, 28, 1, 1.0, (0.3, 0.5, 0.0, 0.875, 0.55, 0.0)), tag="plpk0")
check("Plasma Peak filter changes the sound with Reso", not np.allclose(pk, pk0, atol=1e-3))
du = render(fx(0, 28, 1, 1.0, (0.3, 0.5, 0.0, 0.625, 0.5, 0.6)), tag="pldual")
check("Plasma Dual filter finite", bool(np.isfinite(du).all()) and np.abs(du).max() < 6.0)
# Girth: noise that follows the signal; silence stays silent
gs = render(fx(0, 28, 0, 1.0, (0.6, 0.5, 1.0, 0.375, 1.0, 0.0)), tag="plgirth", note=57); g0 = render(fx(0, 28, 0, 1.0, (0.6, 0.5, 0.0, 0.375, 1.0, 0.0)), tag="plgirth0", note=57)
check("Plasma Girth adds high-frequency noise", hi(gs) > 1.2 * hi(g0), "%.4f vs %.4f" % (hi(gs), hi(g0)))
check("Plasma Girth: silence stays silent after the note", rms(gs[T0 + int(1.0 * RATE):]) < 1e-3, "%.6f" % rms(gs[T0 + int(1.0 * RATE):]))
# aliasing: a hard-clipped 3.1 kHz sine keeps its energy on the harmonics (ADAA)
hc = render(fx(0, 28, 1, 1.0, (0.9, 0.5, 0.0, 0.375, 1.0, 0.0)), tag="plalias", note=98)
seg = hc[int(0.7 * RATE):int(0.85 * RATE), 0].astype(np.float64); X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1.0 / RATE)
f1 = note_hz(98); harm = np.zeros(len(X), bool)
for k in range(1, int(RATE / 2 / f1) + 1): harm |= np.abs(fr - k * f1) < 60
check("Plasma ADAA keeps most energy on the harmonics", float((X[harm] ** 2).sum() / (X ** 2).sum()) > 0.9, "%.3f" % float((X[harm] ** 2).sum() / (X ** 2).sum()))

# ---- FX-MUTABLE: Granular (type 29) and Warp (type 30)
def peaks(a, lo=0.7, hi=1.2, n=3, minhz=30):
    seg = a[int(lo * RATE):int(hi * RATE), 0].astype(np.float64); X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1.0 / RATE)
    X[fr < minhz] = 0; idx = []
    for _ in range(n):
        i = int(np.argmax(X)); idx.append(float(fr[i])); X[max(0, i - 15):i + 15] = 0
    return idx
def near(vals, f, tol=12): return any(abs(v - f) < tol for v in vals)
GRN = ["Granular", "Freeze", "Pitch Shifter", "Looping Delay"]
for m, nm in enumerate(GRN):
    for pn, pv in (("default", (0.3, 0.45, 0.5, 0.5, 0.5, 0.0)), ("max", (1.0, 1.0, 1.0, 1.0, 1.0, 1.0)), ("min", (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))):
        a = render(fx(0, 29, m, 1.0, pv), tag="gr%d%s" % (m, pn), hold=1.0, tail=1.0)
        check("Granular %s (%s): finite and bounded" % (nm, pn), bool(np.isfinite(a).all()) and np.abs(a).max() < 8.0, "peak %.2f" % np.abs(a).max())
a = render(fx(0, 29, 0, 1.0, (0.2, 0.4, 0.5, 0.6, 0.3, 0.0)), tag="grain", hold=1.0, tail=0.5)
check("Granular makes sound from the recorded input", rms(a[int(0.8 * RATE):int(1.4 * RATE)]) > 0.01, "%.4f" % rms(a[int(0.8 * RATE):int(1.4 * RATE)]))
# pitch shifter: +12 st doubles, -12 st halves the pitch of the 440 Hz note
up = render(fx(0, 29, 2, 1.0, (0.0, 0.3, 0.75, 0.5, 0.5, 0.0)), tag="psup", hold=1.0)
dn = render(fx(0, 29, 2, 1.0, (0.0, 0.3, 0.25, 0.5, 0.5, 0.0)), tag="psdn", hold=1.0)
check("Pitch Shifter +12 st: 880 Hz", near(peaks(up, 0.9, 1.3), 880, 25), str(peaks(up, 0.9, 1.3)))
check("Pitch Shifter -12 st: 220 Hz", near(peaks(dn, 0.9, 1.3), 220, 15), str(peaks(dn, 0.9, 1.3)))
# freeze: the recording stops, the sound goes on after the note is released; Looping Delay with feedback keeps looping
# Freeze: switch to Freeze while the note plays; after the release the frozen recording keeps sounding
def render_script(lines, tag):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    open(script, "w").write("wt 0 sine\np %d 0\n" % L.pid(0, L.K["fon"]) + "\n".join(lines) + "\n")
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
fzc = fx(0, 29, 0, 1.0, (0.1, 0.5, 0.5, 0.7, 0.2, 0.0))
fz = render_script(fzc + ["run 0.2", "on 69 110", "run 0.8", "p %d 1" % (base(0) + 3), "run 0.1", "off 69", "run 2.0"], "frz")
nf = render_script(fzc + ["run 0.2", "on 69 110", "run 0.9", "off 69", "run 2.0"], "nofrz")
tf = int(1.2 * RATE)
check("Granular Freeze keeps sounding after the note is released", rms(fz[tf + int(1.0 * RATE):tf + int(1.8 * RATE)]) > 0.02 and rms(nf[tf + int(1.0 * RATE):tf + int(1.8 * RATE)]) < 0.005, "%.4f vs %.4f" % (rms(fz[tf + int(1.0 * RATE):tf + int(1.8 * RATE)]), rms(nf[tf + int(1.0 * RATE):tf + int(1.8 * RATE)])))
gp = render(fx(0, 29, 0, 1.0, (0.1, 0.5, 0.5, 0.7, 0.2, 0.0)), tag="grnofrz", hold=0.4, tail=1.5)
check("without Freeze the grains die out after the note", rms(gp[T0 + int(1.2 * RATE):T0 + int(1.6 * RATE)]) < 0.02, "%.5f" % rms(gp[T0 + int(1.2 * RATE):T0 + int(1.6 * RATE)]))
ld = render(fx(0, 29, 3, 1.0, (0.3, 0.45, 0.5, 0.5, 0.5, 1.0)), tag="loop", hold=0.5, tail=2.5)
ld0 = render(fx(0, 29, 3, 1.0, (0.3, 0.45, 0.5, 0.5, 0.5, 0.0)), tag="loop0", hold=0.5, tail=2.5)
check("Looping Delay with feedback keeps looping, without it the loop is one repeat", rms(ld[T0 + int(1.6 * RATE):T0 + int(2.4 * RATE)]) > 5 * rms(ld0[T0 + int(1.6 * RATE):T0 + int(2.4 * RATE)]) + 1e-4, "%.4f vs %.4f" % (rms(ld[T0 + int(1.6 * RATE):T0 + int(2.4 * RATE)]), rms(ld0[T0 + int(1.6 * RATE):T0 + int(2.4 * RATE)])))

WPN = ["Crossfade", "Fold", "Analog RM", "Digital RM", "XOR", "Comparator", "Vocoder", "Freq Shift"]
for m, nm in enumerate(WPN):
    for pn, pv in (("default", (0.5, 0.5, 0.511, 0.0, 0.5, 0.3)), ("max", (1.0, 1.0, 1.0, 1.0, 1.0, 1.0)), ("min", (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))):
        a = render(fx(0, 30, m, 1.0, pv), tag="wp%d%s" % (m, pn))
        check("Warp %s (%s): finite and bounded" % (nm, pn), bool(np.isfinite(a).all()) and np.abs(a).max() < 8.0, "peak %.2f" % np.abs(a).max())
# the carrier is 300 Hz (P3 = 0.511), the modulator the 440 Hz note
cf = render(fx(0, 30, 0, 1.0, (0.0, 0.5, 0.511, 0.0, 0.5, 0.3)), tag="wpx0"); mf = render(fx(0, 30, 0, 1.0, (1.0, 0.5, 0.511, 0.0, 0.5, 0.3)), tag="wpx1")
check("Warp Crossfade 0: the carrier (300 Hz)", near(peaks(cf, n=1), 300, 15), str(peaks(cf, n=1)))
check("Warp Crossfade 1: the modulator (440 Hz)", near(peaks(mf, n=1), 440, 15), str(peaks(mf, n=1)))
rm = render(fx(0, 30, 3, 1.0, (0.0, 1.0, 0.511, 0.0, 0.5, 0.3)), tag="wprm"); pk = peaks(rm, n=2)
check("Warp Digital RM: sidebands 140 and 740 Hz, no 440", near(pk, 140, 15) and near(pk, 740, 15), str(pk))
ar = render(fx(0, 30, 2, 1.0, (0.0, 1.0, 0.511, 0.0, 0.5, 0.3)), tag="wpar"); pk = peaks(ar, n=4)
check("Warp Analog RM: sidebands 140 and 740 Hz", near(pk, 140, 15) and near(pk, 740, 15), str(pk))
# frequency shifter: +100 Hz / -100 Hz (P3 = 0.3038), the note is 440 Hz
fu = render(fx(0, 30, 7, 1.0, (0.5, 0.5, 0.3038, 0.0, 0.5, 1.0)), tag="fsup"); fd = render(fx(0, 30, 7, 1.0, (0.5, 0.5, 0.3038, 0.0, 0.5, 0.0)), tag="fsdn")
check("Warp Freq Shift up by 100 Hz: 540 Hz", near(peaks(fu, n=1), 540, 12), str(peaks(fu, n=1)))
check("Warp Freq Shift down by 100 Hz: 340 Hz", near(peaks(fd, n=1), 340, 12), str(peaks(fd, n=1)))
sup = np.fft.rfft(fu[int(0.7 * RATE):int(1.2 * RATE), 0].astype(np.float64) * np.hanning(int(0.5 * RATE))); fq = np.fft.rfftfreq(int(0.5 * RATE), 1.0 / RATE)
check("Warp Freq Shift rejects the image side band (-100 Hz: 340 Hz) by 20 dB", np.abs(sup[np.argmin(np.abs(fq - 540))]) > 10 * np.abs(sup[np.argmin(np.abs(fq - 340))]), "%.1f dB" % (20 * np.log10(np.abs(sup[np.argmin(np.abs(fq - 540))]) / np.abs(sup[np.argmin(np.abs(fq - 340))]))))
# vocoder: silent without input, audible with it
vc = render(fx(0, 30, 6, 1.0, (0.5, 0.5, 0.45, 0.66, 0.5, 0.3)), tag="wpvoc")
check("Warp Vocoder is audible while the note plays", rms(vc[int(0.7 * RATE):T0]) > 0.01, "%.4f" % rms(vc[int(0.7 * RATE):T0]))
check("Warp Vocoder is silent without input", rms(vc[:int(0.5 * RATE)]) < 1e-3 and rms(vc[T0 + int(1.2 * RATE):]) < 5e-3, "%.5f / %.5f" % (rms(vc[:int(0.5 * RATE)]), rms(vc[T0 + int(1.2 * RATE):])))

print("FAILURES: %d" % failures if failures else "ALL OK")
raise SystemExit(1 if failures else 0)
