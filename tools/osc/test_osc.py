#!/usr/bin/env python3
"""Audio tests of the 6-slot oscillator DSP.   python3 tools/osc/test_osc.py --host host_osc"""
import argparse, math, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import layout as L

ap = argparse.ArgumentParser()
ap.add_argument("--host", required=True)
args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="oscTest")
RATE = 48000
failures = 0
K = L.K

def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1

def P(o, key, v): return (L.pid(o, K[key]), v)

def render(cmds, note=69, hold=0.7, tail=0.3, tag="x", vel=100):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds:
            if isinstance(c, str): f.write(c + "\n")
            elif c[0] == "shape": f.write("shape %d %s %s\n" % (c[1], c[2], c[3] if len(c) > 3 else 0))
            else: f.write("p %d %s\n" % (c[0], c[1]))
        f.write("run 0.05\n")
        f.write("on %d %d\nrun %s\noff %d\nrun %s\n" % (note, vel, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)

def seg(a, t0=0.25, t1=0.65):
    return a[int(t0 * RATE):int(t1 * RATE)]

def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))

def spec(x):
    x = x.astype(np.float64); x = x - x.mean()
    w = np.hanning(len(x)); X = np.abs(np.fft.rfft(x * w)); f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return f, X

def peak_freq(x):
    f, X = spec(x); i = int(np.argmax(X))
    if 0 < i < len(X) - 1:
        a, b, c = np.log(X[i - 1] + 1e-12), np.log(X[i] + 1e-12), np.log(X[i + 1] + 1e-12)
        d = 0.5 * (a - c) / (a - 2 * b + c); return f[i] + d * (f[1] - f[0])
    return f[i]

def band(x, f0, f1):
    f, X = spec(x); m = (f >= f0) & (f < f1); return float(np.sqrt(np.sum(X[m] ** 2)))

WT0 = ["wt 0 sine"]
FOFF = lambda o: P(o, "fon", 0)

# ---------------------------------------------------------------- basics
a = render(WT0 + [FOFF(0)], tag="wt_sine")
x = seg(a)
check("wavetable slot plays the note pitch (A4 = 440 Hz)", abs(peak_freq(x[:, 0]) - 440) < 1.0, "%.2f Hz" % peak_freq(x[:, 0]))
check("output is audible and finite", 0.02 < rms(x) < 1.0 and np.isfinite(a).all(), "%.3f" % rms(x))

a = render([], tag="empty")
check("slots without memory are silent", rms(a) < 1e-6)

a = render(["wt 0 sine", FOFF(0), P(0, "oct", 1)], tag="oct")
check("octave +1 doubles the pitch", abs(peak_freq(seg(a)[:, 0]) - 880) < 2)
a = render(["wt 0 sine", FOFF(0), P(0, "semi", 12), P(0, "fine", 0)], tag="semi")
check("semi +12 doubles the pitch", abs(peak_freq(seg(a)[:, 0]) - 880) < 2)
a = render(["wt 0 sine", FOFF(0), P(0, "track", 0), P(0, "root", 57)], note=81, tag="notrack")
check("key track off plays the root note", abs(peak_freq(seg(a)[:, 0]) - 220) < 1.5, "%.1f" % peak_freq(seg(a)[:, 0]))

# sampler (sine sample at 261.6256 Hz root 60)
a = render(["smp 1 sine 261.6256", P(1, "type", 1), P(1, "level", 0.8), P(0, "level", 0), FOFF(1)], note=60, tag="smp")
check("sampler slot at its root note", abs(peak_freq(seg(a)[:, 0]) - 261.6) < 1.5 and rms(seg(a)) > 0.02, "%.1f Hz" % peak_freq(seg(a)[:, 0]))
a = render(["smp 1 sine 261.6256", P(1, "type", 1), P(1, "level", 0.8), P(0, "level", 0), FOFF(1)], note=72, tag="smp12")
check("sampler follows the keyboard (+1 octave)", abs(peak_freq(seg(a)[:, 0]) - 523.25) < 3, "%.1f" % peak_freq(seg(a)[:, 0]))
a = render(["smp 1 sine 261.6256", P(1, "type", 1), P(1, "level", 0.8), P(0, "level", 0), FOFF(1), P(1, "sloop", 1)], note=60, hold=1.6, tail=0.1, tag="smploop")
check("sampler loop keeps sounding after the sample end", rms(a[int(1.3 * RATE):int(1.5 * RATE)]) > 0.02)
a = render(["smp 1 sine 261.6256", P(1, "type", 1), P(1, "level", 0.8), P(0, "level", 0), FOFF(1), P(1, "sloop", 0)], note=60, hold=1.6, tail=0.1, tag="smpone")
check("sampler one-shot stops after the sample end", rms(a[int(1.3 * RATE):int(1.5 * RATE)]) < 1e-3)

# independent memories per slot (instance isolation is per view; here: slot isolation)
a = render(["wt 0 sine", "wt 1 saw", P(1, "level", 0.8), P(0, "level", 0), FOFF(0), FOFF(1)], tag="slotiso")
f, X = spec(seg(a)[:, 0])
check("slot 2 has its own wavetable (saw has harmonics, sine none)", band(seg(a)[:, 0], 800, 1000) > 0.1 * band(seg(a)[:, 0], 400, 480))

# ---------------------------------------------------------------- levels, pan, outputs
a = render(WT0 + [FOFF(0), P(0, "pan", -1)], tag="panL")
check("pan hard left", rms(seg(a)[:, 1]) < 0.01 * rms(seg(a)[:, 0]))
a = render(WT0 + [FOFF(0), P(0, "pan", 1)], tag="panR")
check("pan hard right", rms(seg(a)[:, 0]) < 0.01 * rms(seg(a)[:, 1]))
a1 = render(WT0 + [FOFF(0), (28, 0), P(0, "level", 0.1)], tag="lv4"); a2 = render(WT0 + [FOFF(0), (28, 0), P(0, "level", 0.2)], tag="lv8")
check("level scales the output (2x)", abs(rms(seg(a2)) / rms(seg(a1)) - 2.0) < 0.05, "%.3f" % (rms(seg(a2)) / rms(seg(a1))))
for rt, nm in ((0, "Main"), (1, "Bus 1"), (2, "Bus 2")):
    a = render(WT0 + [FOFF(0), P(0, "out", rt)], tag="route%d" % rt)
    check("output routed to %s" % nm, rms(seg(a)) > 0.02, "%.3f" % rms(seg(a)))
am = render(WT0 + [FOFF(0), P(0, "out", 0)], tag="rm"); ab = render(WT0 + [FOFF(0), P(0, "out", 1)], tag="rb")
check("Bus 1 and Main give the same level through empty racks", abs(rms(seg(am)) / rms(seg(ab)) - 1) < 0.02)

# ---------------------------------------------------------------- filter
a_off = render(["wt 0 saw", FOFF(0)], tag="saw_off")
a_lp = render(["wt 0 saw", P(0, "fon", 1), P(0, "ftype", 1), P(0, "fcut", 500), P(0, "fres", 0.1), P(0, "fkey", 0)], tag="saw_lp")
hi_off = band(seg(a_off)[:, 0], 4000, 12000); hi_lp = band(seg(a_lp)[:, 0], 4000, 12000)
check("LP12 at 500 Hz removes the highs", hi_lp < 0.05 * hi_off, "%.3g vs %.3g" % (hi_lp, hi_off))
a_hp = render(["wt 0 saw", P(0, "fon", 1), P(0, "ftype", 2), P(0, "fcut", 3000), P(0, "fres", 0.1), P(0, "fkey", 0)], tag="saw_hp")
check("HP12 at 3 kHz removes the fundamental", band(seg(a_hp)[:, 0], 400, 480) < 0.05 * band(seg(a_off)[:, 0], 400, 480))
ok = True; levels = []
for t in range(30):
    a = render(["wt 0 saw", P(0, "fon", 1), P(0, "ftype", t), P(0, "fcut", 1500), P(0, "fres", 0.5)], hold=0.4, tail=0.1, tag="ft%d" % t)
    r = rms(seg(a, 0.1, 0.4)); levels.append(r)
    if not np.isfinite(a).all() or r < 1e-4 or r > 2.0: ok = False; print("  type", t, "rms", r)
check("all 30 filter types are finite and audible", ok, " ".join("%.2f" % v for v in levels))
ok = True
for t in range(30):
    a = render(["wt 0 saw", P(0, "fon", 1), P(0, "ftype", t), P(0, "fcut", 18000), P(0, "fres", 1.0), P(0, "fdrv", 1.0), P(0, "dtype", 4), P(0, "ddrv", 1)], hold=0.3, tail=0.05, tag="fx%d" % t)
    if not np.isfinite(a).all() or np.abs(a).max() > 1.0001: ok = False; print("  extreme type", t)
check("all filter types stay bounded at resonance 1 / drive 1", ok)
# filter envelope: EG opens the cutoff on the attack
a = render(["wt 0 saw", P(0, "fon", 1), P(0, "ftype", 1), P(0, "fcut", 300), P(0, "feg", 1), P(0, "fdec", 400), P(0, "fsus", 0), P(0, "fkey", 0)], hold=0.8, tail=0.1, tag="feg")
early = band(a[int(0.06 * RATE):int(0.16 * RATE), 0], 3000, 12000); late = band(a[int(0.6 * RATE):int(0.7 * RATE), 0], 3000, 12000)
check("filter envelope sweeps the cutoff (bright start, dark end)", early > 5 * late, "%.3g / %.3g" % (early, late))
# every slot has its own filter
a = render(["wt 0 saw", "wt 1 saw", P(1, "level", 0.8), P(0, "level", 0), FOFF(0), P(1, "fon", 1), P(1, "ftype", 1), P(1, "fcut", 300), P(1, "fkey", 0)], tag="f2")
check("slot 2 uses its own filter", band(seg(a)[:, 0], 4000, 12000) < 0.05 * hi_off)
a = render(["wt 0 saw", "wt 1 saw", P(1, "level", 0.8), P(0, "level", 0.8), FOFF(0), P(1, "fon", 1), P(1, "ftype", 1), P(1, "fcut", 300), P(1, "fkey", 0)], tag="f2b")
check("slot 1 stays unfiltered next to a filtered slot 2", band(seg(a)[:, 0], 4000, 12000) > 0.4 * hi_off)

# ---------------------------------------------------------------- distortion
a_c = render(WT0 + [FOFF(0)], tag="d_clean"); a_d = render(WT0 + [FOFF(0), P(0, "dtype", 4), P(0, "ddrv", 0.8)], tag="d_fold")
check("distortion adds harmonics to a sine", band(seg(a_d)[:, 0], 1000, 8000) > 20 * band(seg(a_c)[:, 0], 1000, 8000) + 1)
a_o = render(WT0 + [FOFF(0), P(0, "dtype", 0), P(0, "ddrv", 1)], tag="d_off")
check("distortion Off is transparent", np.max(np.abs(a_o - a_c)) < 1e-6)
a_m = render(WT0 + [FOFF(0), P(0, "dtype", 4), P(0, "ddrv", 0.8), P(0, "dmix", 0)], tag="d_mix0")
check("distortion mix 0 is transparent", np.max(np.abs(a_m - a_c)) < 1e-6)
ok = True
for t in range(1, 7):
    a = render(["wt 0 saw", FOFF(0), P(0, "dtype", t), P(0, "ddrv", 1)], hold=0.3, tail=0.05, tag="dt%d" % t)
    if not np.isfinite(a).all() or rms(a) < 1e-3: ok = False; print("  dist type", t)
check("all 6 distortion types work", ok)

# ---------------------------------------------------------------- FM and PM matrices
for MOD, fm in (("FM", L.fm_id), ("PM", L.pm_id), ("PD", L.pd_id)):
    base = [(28, 0), "wt 0 sine", "wt 1 sine", P(0, "level", 0), P(1, "level", 0.8), FOFF(0), FOFF(1)]
    a0 = render(base, tag=MOD+"fm0")
    check(MOD + " without " + MOD + " slot 2 is a pure sine", band(seg(a0)[:, 0], 600, 6000) < 0.05 * band(seg(a0)[:, 0], 400, 480))
    a1 = render(base + [(fm(0, 1), 30)], tag=MOD+"fm1")
    check(MOD + " "+MOD+" from a silent (level 0) slot 1 into slot 2 creates sidebands", band(seg(a1)[:, 0], 600, 6000) > 0.2 * band(seg(a1)[:, 0], 400, 480))
    a2 = render(base + [(fm(0, 1), 60)], tag=MOD+"fm2")
    check(MOD + " more " + MOD + ", more sidebands", band(seg(a2)[:, 0], 600, 6000) > band(seg(a1)[:, 0], 600, 6000))
    a3 = render(base + [(fm(0, 1), 0)], tag=MOD+"fm3")
    check(MOD + " amount 0 is off", np.max(np.abs(a3 - a0)) < 1e-6)
    a4 = render([(28, 0), "wt 0 sine", P(0, "level", 0.8), FOFF(0), (fm(0, 0), 40)], tag=MOD+"fmfb")
    check(MOD + " self feedback (slot 1 into slot 1)", band(seg(a4)[:, 0], 600, 6000) > 0.1 * band(seg(a4)[:, 0], 400, 480) and np.isfinite(a4).all())
    ok = True
    for amt in (100, 100.0):
        cm = ["wt %d morph" % o for o in range(6)] + [P(o, "wsize", 0) for o in range(6)] + [P(o, "level", 0.3) for o in range(6)]
        for s in range(6):
            for d in range(6): cm.append((fm(s, d), amt))
        a = render(cm, hold=0.3, tail=0.05, tag=MOD+"fmall")
        if not np.isfinite(a).all() or np.abs(a).max() > 1.0001: ok = False
    check(MOD + " full 6x6 matrix at 100% stays finite and bounded", ok)
    a5 = render(["smp 0 sine 261.6256", "smp 1 sine 261.6256", P(0, "type", 1), P(1, "type", 1), P(0, "level", 0), P(1, "level", 0.8), FOFF(0), FOFF(1), (fm(0, 1), 30), P(0, "sloop", 1), P(1, "sloop", 1)], note=60, tag=MOD+"fmsmp")
    check(MOD + " sampler slots can " + MOD + " each other", band(seg(a5)[:, 0], 400, 6000) > 0.2 * band(seg(a5)[:, 0], 240, 290) and np.isfinite(a5).all())

# ---------------------------------------------------------------- signal flow: osc -> filter -> distortion -> matrix
fbase = [(28, 0), "wt 0 saw", "wt 1 sine", P(0, "level", 0), P(1, "level", 0.8), FOFF(1), (L.fm_id(0, 1), 50)]
a_raw  = render(fbase + [FOFF(0)], tag="flow0")
a_filt = render(fbase + [P(0, "fon", 1), P(0, "ftype", 1), P(0, "fcut", 150), P(0, "fkey", 0)], tag="flow1")
check("the FM modulator is the filtered slot (closed LP filter on the modulator removes sidebands)",
      band(seg(a_filt)[:, 0], 700, 8000) < 0.5 * band(seg(a_raw)[:, 0], 700, 8000), "%.3g vs %.3g" % (band(seg(a_filt)[:, 0], 700, 8000), band(seg(a_raw)[:, 0], 700, 8000)))
a_dist = render(["wt 0 sine", "wt 1 sine", P(0, "level", 0), P(1, "level", 0.8), FOFF(1), FOFF(0), P(0, "dtype", 4), P(0, "ddrv", 1), (L.fm_id(0, 1), 0), (L.pm_id(0, 1), 50)], tag="flow2")
a_nod  = render(["wt 0 sine", "wt 1 sine", P(0, "level", 0), P(1, "level", 0.8), FOFF(1), FOFF(0), (L.pm_id(0, 1), 50)], tag="flow3")
check("the matrix modulator is the distorted slot", rms(a_dist - a_nod) > 0.05 * rms(a_nod), "%.3f" % rms(a_dist - a_nod))
order = [ "wt 0 saw", P(0, "level", 0.8), P(0, "fon", 1), P(0, "ftype", 1), P(0, "fcut", 600), P(0, "fkey", 0), P(0, "dtype", 4), P(0, "ddrv", 1)]
a_post = render(order + [P(0, "dpos", 0)], tag="ord0")
a_pre  = render(order + [P(0, "dpos", 1)], tag="ord1")
a_def  = render(order, tag="ord2")
check("distortion position defaults to after the filter", np.max(np.abs(a_post - a_def)) < 1e-6)
check("distortion before the filter sounds different from after", rms(a_post - a_pre) > 0.05 * rms(a_post), "%.3f" % rms(a_post - a_pre))
check("distortion before the filter is darker (filter removes the new harmonics)", band(seg(a_pre)[:, 0], 3000, 12000) < 0.7 * band(seg(a_post)[:, 0], 3000, 12000))

# mod matrix -> FM / PM / PD matrix amounts (destinations 60 + n, 96 + n, 132 + n; n = 6 * src + dst)
for kind, off in (("FM", 60), ("PM", 96), ("PD", 132)):
    mbase = [(28, 0), "wt 0 sine", "wt 1 sine", P(0, "level", 0), P(1, "level", 0.8), FOFF(0), FOFF(1)]
    a0 = render(mbase, tag="mm" + kind + "0")
    a1 = render(mbase + [(307, 1), (308, off + 1), (309, 1.0), ("shape", 0, "const", 1), (882, 1), (247, 6)], tag="mm" + kind + "1")
    check("mod matrix destination '%s A > B' opens the %s amount (sidebands appear)" % (kind, kind),
          band(seg(a1)[:, 0], 600, 6000) > 0.2 * band(seg(a1)[:, 0], 400, 480) and band(seg(a0)[:, 0], 600, 6000) < 0.05 * band(seg(a0)[:, 0], 400, 480))
    a2 = render(mbase + [(307, 1), (308, off + 6), (309, 1.0), ("shape", 0, "const", 1), (882, 1), (247, 6)], tag="mm" + kind + "2")
    check("mod matrix destination '%s B > A' leaves the A > B amount alone" % kind, band(seg(a2)[:, 0], 600, 6000) < 0.05 * band(seg(a2)[:, 0], 400, 480))

# ---------------------------------------------------------------- Vital style wavetables: band-limited mips, 2048 frames, up to 128 frames
def alias_ratio(a, f0):
    f, X = spec(seg(a)[:, 0]); k = np.round(f / f0); near = np.abs(f - k * f0) < 12.0
    return float(np.sqrt(np.sum(X[~near & (f > 100)] ** 2)) / np.sqrt(np.sum(X[near] ** 2)))
for note, name in ((84, "C6"), (96, "C7"), (105, "A7")):
    f0 = 440.0 * 2 ** ((note - 69) / 12.0)
    a = render(["wt 0 saw2k", P(0, "level", 0.8), P(0, "wsize", 3), FOFF(0)], note=note, tag="alias%d" % note)
    r = alias_ratio(a, f0)
    check("band-limited saw at %s has no aliasing" % name, r < 0.03, "residual %.4f" % r)
lo = render(["wt 0 saw2k", P(0, "level", 0.8), P(0, "wsize", 3), FOFF(0)], note=36, tag="wtlow")
check("low note keeps the full saw harmonics", band(seg(lo)[:, 0], 3000, 12000) > 0.15 * band(seg(lo)[:, 0], 60, 3000) * 0.1)
a0 = render(["wt 0 big", P(0, "level", 0.8), P(0, "wsize", 3), P(0, "wpos", 0), FOFF(0)], tag="big0")
a1 = render(["wt 0 big", P(0, "level", 0.8), P(0, "wsize", 3), P(0, "wpos", 1), FOFF(0)], tag="big1")
check("128 frame table: first frame is a sine", band(seg(a0)[:, 0], 600, 6000) < 0.06 * band(seg(a0)[:, 0], 200, 480))
check("128 frame table: last frame is a saw", band(seg(a1)[:, 0], 600, 6000) > 0.3 * band(seg(a1)[:, 0], 200, 480))
am = render(["wt 0 morph2k", P(0, "level", 0.8), P(0, "wsize", 3), P(0, "wpos", 0.5), FOFF(0)], tag="mid")
check("frames crossfade smoothly (middle position is between sine and saw)", band(seg(a0)[:, 0], 600, 6000) < band(seg(am)[:, 0], 600, 6000) < band(seg(a1)[:, 0], 600, 6000))
a2 = render(["wt 0 morph2k", P(0, "level", 0.8), P(0, "wsize", 2), FOFF(0)], tag="fs1024")
check("frame size 1024 re-cuts the table (2x the frames, still plays)", np.isfinite(a2).all() and rms(seg(a2)) > 0.05)
a4 = render(["wt 0 morph2k", P(0, "level", 0.8), P(0, "wsize", 4), FOFF(0)], tag="fs4096")
check("frame size 4096 re-cuts the table (half the frames, still plays)", np.isfinite(a4).all() and rms(seg(a4)) > 0.05)

# ---------------------------------------------------------------- unison / warp
a_u = render(["wt 0 saw", FOFF(0), P(0, "uvox", 5), P(0, "udet", 0.5), P(0, "uwid", 1)], tag="uni")
check("unison widens the stereo image", float(np.corrcoef(seg(a_u)[:, 0], seg(a_u)[:, 1])[0, 1]) < 0.95)
a_n = render(["wt 0 saw", FOFF(0), P(0, "uvox", 1)], tag="uni1")
check("one voice is centred", float(np.corrcoef(seg(a_n)[:, 0], seg(a_n)[:, 1])[0, 1]) > 0.999)
ok = True
for m in range(9):
    a = render(["wt 0 morph", P(0, "wsize", 0), FOFF(0), P(0, "w1m", m), P(0, "w1a", 0.8), P(0, "w2m", (m + 3) % 9), P(0, "w2a", 0.6), P(0, "wpos", 0.5)], hold=0.3, tail=0.05, tag="warp%d" % m)
    if not np.isfinite(a).all() or rms(seg(a, 0.1, 0.3)) < 1e-3: ok = False; print("  warp", m)
check("all 9 warp modes sound", ok)
a_p0 = render(["wt 0 morph", P(0, "wsize", 0), FOFF(0), P(0, "wpos", 0)], tag="p0"); a_p1 = render(["wt 0 morph", P(0, "wsize", 0), FOFF(0), P(0, "wpos", 1)], tag="p1")
check("wavetable position morphs from sine to saw", band(seg(a_p1)[:, 0], 1000, 8000) > 5 * band(seg(a_p0)[:, 0], 1000, 8000))

# ---------------------------------------------------------------- mod matrix with the new destinations
# slot 1 source = LFO 1 (src 1) -> destination: slot 1 level (6 + 1), amount 1; LFO 1 const shape +1 -> level up by 1
dsti = lambda o, j: L.dst_index(o, j)
a = render(["wt 0 sine", FOFF(0), P(0, "level", 0.0), (307, 1), (308, dsti(0, 1)), (309, 0.8), ("shape", 0, "const", 1), (882, 1), (247, 6)], tag="modlvl")
check("matrix destination 'slot 1 Level' opens a silent slot", rms(seg(a)) > 0.05, "%.3f" % rms(seg(a)))
a = render(["wt 0 saw", P(0, "fon", 1), P(0, "ftype", 1), P(0, "fcut", 200), P(0, "fkey", 0), (307, 1), (308, dsti(0, 6)), (309, 1.0), ("shape", 0, "const", 1), (882, 1), (247, 6)], tag="modcut")
check("matrix destination 'slot 1 Cutoff' opens the filter", band(seg(a)[:, 0], 2000, 12000) > 10 * hi_lp, "%.3g" % band(seg(a)[:, 0], 2000, 12000))
a = render(["wt 0 sine", FOFF(0), (307, 1), (308, 3), (309, -0.5), ("shape", 0, "const", 1), (882, 1), (247, 6)], tag="modpan")
check("matrix destination 'Pan (global)' still works", rms(seg(a)[:, 0]) > 1.5 * rms(seg(a)[:, 1]))

# ---------------------------------------------------------------- polyphony, release, extremes
a = render(WT0 + [FOFF(0), P(0, "level", 0.8)], note=60, tag="poly")
script = os.path.join(TMP, "chord.txt"); out = os.path.join(TMP, "chord.f32")
with open(script, "w") as f:
    f.write("wt 0 saw\np %d 0\nrun 0.05\n" % L.pid(0, K["fon"]))
    for n in (48, 55, 60, 64, 67, 72, 76, 79): f.write("on %d 100\n" % n)
    f.write("run 0.5\n")
    for n in (48, 55, 60, 64, 67, 72, 76, 79): f.write("off %d\n" % n)
    f.write("run 1.5\n")
subprocess.run([args.host, script, out], check=True)
c = np.fromfile(out, dtype=np.float32).reshape(-1, 2)
check("8 voices play and release to silence", np.isfinite(c).all() and rms(c[int(0.2 * RATE):int(0.5 * RATE)]) > 0.05 and rms(c[-int(0.2 * RATE):]) < 1e-3)
ok = True
for t in range(3):
    a = render(["wt 0 saw", "smp 1 saw", "smp 2 noise", P(1, "type", 1), P(2, "type", 2), P(1, "level", 1), P(2, "level", 1), P(0, "level", 1),
                P(0, "fres", 1), P(1, "fres", 1), P(0, "ftype", 8 * t), P(1, "ftype", 20 + t), P(0, "ddrv", 1), P(0, "dtype", 5)], hold=0.3, tail=0.05, tag="ext%d" % t)
    if not np.isfinite(a).all(): ok = False
check("extreme settings stay finite", ok)

# ---------------------------------------------------------------- Plaits slot
for eng in range(24):
    a = render([P(0, "type", 2), P(0, "pleng", eng), P(0, "level", 0.8), FOFF(0)], note=57, hold=0.6, tail=0.2, tag="pl%d" % eng)
    good = np.isfinite(a).all() and rms(a[int(0.05 * RATE):int(0.6 * RATE)]) > 1e-3 and np.abs(a).max() < 4
    check("Plaits engine %d sounds and stays finite" % eng, good, "rms %.3f peak %.2f" % (rms(a), np.abs(a).max()))
a = render([P(0, "type", 2), P(0, "pleng", 10), P(0, "pharm", 0), P(0, "ptimb", 0), P(0, "pmorph", 0), P(0, "level", 0.8), FOFF(0)], note=69, tag="plpitch")
check("Plaits slot follows the keyboard pitch (A4)", abs(peak_freq(seg(a)[:, 0]) - 440) < 3, "%.1f" % peak_freq(seg(a)[:, 0]))
print("all passed" if not failures else "%d FAILED" % failures)
sys.exit(1 if failures else 0)
