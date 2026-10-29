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

print("FAILURES: %d" % failures if failures else "ALL OK")
raise SystemExit(1 if failures else 0)
