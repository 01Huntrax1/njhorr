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
            elif c[0] == "fshape": f.write("fshape %d %s %s\n" % (c[1], c[2], c[3] if len(c) > 3 else 0))
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

# ---------------------------------------------------------------- ring modulation and amplitude modulation matrices
rbase = [(28, 0), "wt 0 sine", "wt 1 sine", P(0, "level", 0), P(1, "level", 0.8), FOFF(0), FOFF(1)]
r0 = render(rbase, tag="rm_dry")
dry_f = band(seg(r0)[:, 0], 400, 480)
for nm, fn in (("RM", L.rm_id), ("AM", L.am_id)):
    r1 = render(rbase + [(fn(0, 1), 100)], tag=nm + "1")
    f1 = band(seg(r1)[:, 0], 400, 480); h2 = band(seg(r1)[:, 0], 820, 940)
    if nm == "RM":
        check("RM 100% of a sine by the same sine removes the fundamental and makes the 2nd harmonic", f1 < 0.25 * dry_f and h2 > 0.2 * dry_f, "%.3g %.3g vs %.3g" % (f1, h2, dry_f))
    else:
        check("AM 100% keeps the fundamental and adds the 2nd harmonic", f1 > 0.3 * dry_f and h2 > 0.1 * dry_f, "%.3g %.3g vs %.3g" % (f1, h2, dry_f))
    r2 = render(rbase + [(fn(0, 1), 0)], tag=nm + "0")
    check(nm + " amount 0 is off", np.max(np.abs(r2 - r0)) < 1e-6)
    r3 = render(rbase + [(fn(1, 0), 100)], tag=nm + "rev")
    check(nm + " B > A leaves the carrier B alone (only A is modulated)", np.max(np.abs(r3 - r0)) < 1e-6)
    cm = ["wt %d morph" % o for o in range(6)] + [P(o, "level", 0.3) for o in range(6)]
    for a_ in range(6):
        for b_ in range(6): cm.append((fn(a_, b_), 100))
    ra = render(cm, hold=0.3, tail=0.05, tag=nm + "all")
    check(nm + " full 6x6 matrix at 100% stays finite and bounded", np.isfinite(ra).all() and np.abs(ra).max() < 1.5)
off = {"RM": 186, "AM": 222}
for nm, fn in (("RM", L.rm_id), ("AM", L.am_id)):
    a1 = render(rbase + [(307, 1), (308, off[nm] + 1), (309, 1.0), ("shape", 0, "const", 1), (882, 1), (247, 6)], tag="mm" + nm)
    a2 = render(rbase + [(fn(0, 1), 100)], tag="mmref" + nm)
    check("mod matrix destination '%s A > B' opens the %s amount" % (nm, nm), rms(a1 - r0) > 0.2 * rms(r0) and abs(rms(a1) / rms(a2) - 1) < 0.4, "%.3f %.3f" % (rms(a1 - r0), rms(r0)))

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

# ---------------------------------------------------------------- Wavefilter / Wavedistortion (table filter and table shaper)
SAW = ["wt 0 saw"]
dry = seg(render(SAW + [P(0, "fon", 0)], tag="wfdry"))[:, 0]
WF = lambda pos, extra=(): SAW + [P(0, "fon", 1), P(0, "ftype", 30), P(0, "fcut", 1000), P(0, "fres", 0.3), P(0, "fkey", 0), P(0, "wfpos", pos)] + list(extra)
x = seg(render(WF(0, ["tbl 0 ones"]), tag="wfone"))[:, 0]
check("Wavefilter with a flat table passes the signal at about unity gain", abs(20 * math.log10(rms(x) / rms(dry))) < 1.5, "%.2f dB" % (20 * math.log10(rms(x) / rms(dry))))
lp = seg(render(WF(0), tag="wflp"))[:, 0]
check("built-in table 0 acts as a low-pass at the cutoff", band(lp, 3000, 12000) < 0.5 * band(dry, 3000, 12000) and band(lp, 100, 800) > 0.8 * band(dry, 100, 800), "%.1f / %.1f" % (band(lp, 3000, 12000), band(dry, 3000, 12000)))
hp = seg(render(WF(4 / 15), tag="wfhp"))[:, 0]
check("built-in table 4 acts as a high-pass (lows fall away, highs stay)", band(hp, 100, 800) < 0.4 * band(dry, 100, 800) and band(hp, 3000, 12000) > 0.7 * band(dry, 3000, 12000), "%.1f / %.1f" % (band(hp, 100, 800), band(dry, 100, 800)))
check("the table position morphs between the filter shapes", band(lp, 100, 800) > 2 * band(hp, 100, 800))
x = seg(render(WF(0, ["tbl 0 zeros"]), tag="wfzero"))[:, 0]
check("a loaded table replaces the built-in one (gain (0 + 1) / 2 = -6 dB)", abs(20 * math.log10(rms(x) / rms(dry)) + 6.0) < 2.0, "%.2f dB" % (20 * math.log10(rms(x) / rms(dry))))
x = seg(render(WF(0, ["tbl 0 ones", "tbl 0 clear"]), tag="wfclr"))[:, 0]
check("clearing a table restores the built-in one", band(x, 3000, 12000) < 0.5 * band(dry, 3000, 12000))
x = seg(render(WF(0, [P(0, "fres", 1.0), P(0, "fcut", 20000)]), hold=0.4, tail=0.1, tag="wfext"))
check("Wavefilter stays finite with extreme settings", np.isfinite(x).all() and np.abs(x).max() < 4)
x = seg(render(WF(0, [(307, 1), (308, L.N_TBL_DST), (309, -1.0), ("shape", 0, "const", 1), (882, 1), (247, 6), P(0, "wfpos", 4 / 15)]), tag="wfmod"))[:, 0]
check("mod destination 'OSC 1 Wavefilter Pos' moves the table position", band(x, 100, 800) > 2 * band(hp, 100, 800), "%.1f vs %.1f" % (band(x, 100, 800), band(hp, 100, 800)))

# ---- Wavefilter controls: Mix / Range / Warp / Contrast / Tilt / Spread / Gain Law
x = seg(render(WF(4 / 15, [P(0, "wfmix", 0.0)]), tag="wfm0"))[:, 0]
check("Wavefilter Mix 0 is the dry signal", abs(rms(x) / rms(dry) - 1) < 0.02 and band(x, 100, 800) > 0.95 * band(dry, 100, 800))
x = seg(render(WF(4 / 15, [P(0, "wfmix", 0.5)]), tag="wfm5"))[:, 0]
check("Wavefilter Mix 0.5 lets half of the cut lows through", 1.5 * band(hp, 100, 800) < band(x, 100, 800) < 0.9 * band(dry, 100, 800), "%.1f" % band(x, 100, 800))
narrow = seg(render(WF(0, [P(0, "wfrange", 2)]), tag="wfr2"))[:, 0]
wide = seg(render(WF(0, [P(0, "wfrange", 14)]), tag="wfr14"))[:, 0]
check("Wavefilter Range: a narrow range makes the slope steeper than a wide one", band(narrow, 3000, 12000) < 0.8 * band(wide, 3000, 12000), "%.1f / %.1f" % (band(narrow, 3000, 12000), band(wide, 3000, 12000)))
c1 = seg(render(WF(0, [P(0, "wfcont", 1.0)]), tag="wfc1"))[:, 0]
c0 = seg(render(WF(0, [P(0, "wfcont", -1.0)]), tag="wfcm"))[:, 0]
check("Wavefilter Contrast sharpens (+) or flattens (-) the curve", band(c1, 1500, 6000) < band(lp, 1500, 6000) < band(c0, 1500, 6000), "%.1f < %.1f < %.1f" % (band(c1, 1500, 6000), band(lp, 1500, 6000), band(c0, 1500, 6000)))
tu = seg(render(WF(0, ["tbl 0 ones", P(0, "wftilt", 1.0)]), tag="wft1"))[:, 0]
td = seg(render(WF(0, ["tbl 0 ones", P(0, "wftilt", -1.0)]), tag="wftm"))[:, 0]
check("Wavefilter Tilt raises the highs (+) or the lows (-)", band(tu, 3000, 12000) / band(tu, 100, 800) > 4 * band(td, 3000, 12000) / band(td, 100, 800), "%.2f vs %.2f" % (band(tu, 3000, 12000) / band(tu, 100, 800), band(td, 3000, 12000) / band(td, 100, 800)))
x = seg(render(WF(0, ["tbl 0 zeros", P(0, "wflaw", 1)]), tag="wflawb"))[:, 0]
check("Gain Law Bipolar: a table of zeros is silence", rms(x) < 0.05 * rms(dry), "%.4f" % rms(x))
x = seg(render(WF(0, ["tbl 0 ones", P(0, "wflaw", 2)]), tag="wflawd"))[:, 0]
check("Gain Law dB: the top of the table is 0 dB", abs(20 * math.log10(rms(x) / rms(dry))) < 1.5, "%.2f dB" % (20 * math.log10(rms(x) / rms(dry))))
x = seg(render(WF(0, ["tbl 0 zeros", P(0, "wflaw", 2)]), tag="wflawz"))[:, 0]
check("Gain Law dB: the middle of the table is about -30 dB", abs(20 * math.log10(rms(x) / rms(dry)) + 30.0) < 4.0, "%.2f dB" % (20 * math.log10(rms(x) / rms(dry))))
a = render(WF(0, [P(0, "wfspr", 1.0), P(0, "wfwarp", 0.7), P(0, "wfcont", 0.5), P(0, "wftilt", 0.4), P(0, "uvox", 3), P(0, "uwid", 1.0)]), tag="wfspr")
sp = seg(a)
check("Wavefilter Spread differs between the channels (stereo sources) and stays finite", np.isfinite(a).all() and abs(band(sp[:, 0], 200, 3000) - band(sp[:, 1], 200, 3000)) > 0.02 * band(sp[:, 0], 200, 3000),
      "%.1f vs %.1f" % (band(sp[:, 0], 200, 3000), band(sp[:, 1], 200, 3000)))
x = seg(render(WF(0, [P(0, "wfrange", 14), P(0, "wfwarp", -1), P(0, "wfcont", 1), P(0, "wftilt", 1), P(0, "fres", 1.0), P(0, "wflaw", 1)]), hold=0.4, tail=0.1, tag="wfext2"))
check("Wavefilter stays finite with every control at its extreme", np.isfinite(x).all() and np.abs(x).max() < 8)

SH = lambda pos, extra=(), ty=7: SAW + [P(0, "fon", 0), P(0, "dtype", ty), P(0, "ddrv", 0.0), P(0, "dmix", 1.0), P(0, "wdpos", pos)] + list(extra)
x = seg(render(SH(0), tag="shid"))[:, 0]
check("Wavedistortion table 0 (identity) leaves the signal alone", abs(rms(x) / rms(dry) - 1) < 0.03 and band(x, 100, 800) > 0.95 * band(dry, 100, 800))
x = seg(render(SH(0, ["tbl 6 lin"]), tag="shlin"))[:, 0]
check("a loaded linear table does the same", abs(rms(x) / rms(dry) - 1) < 0.03)
x = seg(render(SH(5 / 15, [P(0, "ddrv", 0.6)]), tag="shfold"))[:, 0]
check("a fold / sine table reshapes the waveform", rms(x - dry) > 0.15 * rms(dry), "%.3f / %.3f" % (rms(x - dry), rms(dry)))
x = seg(render(SH(0, [P(0, "dmix", 0.0), P(0, "ddrv", 0.5)]), tag="shmix"))[:, 0]
check("mix 0 is the dry signal", abs(rms(x) / rms(dry) - 1) < 0.02)
x = seg(render(SH(0, [(307, 1), (308, L.N_TBL_DST + 1), (309, 1.0), ("shape", 0, "const", 1), (882, 1), (247, 6)]), tag="shmod"))[:, 0]
check("mod destination 'OSC 1 Wavedistortion Pos' moves the table position", rms(x - dry) > 0.15 * rms(dry), "%.3f / %.3f" % (rms(x - dry), rms(dry)))
a = render(SH(0, ["tbl 6 clear", "tbl 6 ones"]), tag="shdc")
check("Wavedistortion with a constant table stays finite and DC free", np.isfinite(a).all() and abs(float(np.mean(seg(a)))) < 0.01)
x = seg(render(SH(0, [P(0, "dpos", 1), P(0, "ftype", 1), P(0, "fon", 1), P(0, "fcut", 600), P(0, "ddrv", 0.5), P(0, "wdpos", 5 / 15)]), tag="shpre"))[:, 0]
check("Wavedistortion honours the Pre / Post switch", np.isfinite(x).all() and rms(x) > 0.01)

# ---------------------------------------------------------------- Frequency knob and Freq modulators
FQ = lambda v: ["wt 0 sine", FOFF(0), P(0, "freq", v)]
x = seg(render(FQ(0.5), note=45, tag="fq1"))[:, 0]
check("Frequency knob sets a fixed oscillator frequency (0.5 = 632.5 Hz, any key)", abs(peak_freq(x) - 632.5) < 4, "%.1f Hz" % peak_freq(x))
x = seg(render(FQ(0.0), note=69, tag="fq0"))[:, 0]
check("Frequency knob at 0 is off (key pitch)", abs(peak_freq(x) - 440) < 2)
DFQ = lambda o: L.N_FREQ_DST + o
x = seg(render(FQ(0.5) + [(307, 24), (308, DFQ(0)), (309, 0.25), ("fshape", 0, "const", 1.0)], note=45, tag="fq2"))[:, 0]
exp = 632.5 * 2 ** (0.25 * 9.9658)
check("Freq modulator 1 on the Frequency knob (curve 1.0, amount 0.25 = +2.49 octaves)", abs(peak_freq(x) / exp - 1) < 0.04, "%.0f Hz, expected %.0f" % (peak_freq(x), exp))
x = seg(render(FQ(0.0) + [(307, 24), (308, DFQ(0)), (309, 0.1), ("fshape", 0, "const", 1.0)], note=57, tag="fq3"))[:, 0]
exp = 220 * 2 ** (0.1 * 9.9658)
check("with the knob off the Freq modulator adds octaves to the key pitch", abs(peak_freq(x) / exp - 1) < 0.04, "%.0f Hz, expected %.0f" % (peak_freq(x), exp))
CUT = ["wt 0 saw", P(0, "fon", 1), P(0, "ftype", 1), P(0, "fcut", 200), P(0, "fkey", 0), P(0, "fres", 0.1)]
a0 = seg(render(CUT, tag="fqc0"))[:, 0]
a1 = seg(render(CUT + [(307, 24), (308, L.dst_index(0, 6)), (309, 0.4), ("fshape", 0, "const", 1.0)], tag="fqc1"))[:, 0]
check("Freq modulator on the cutoff opens the filter", band(a1, 2000, 10000) > 3 * band(a0, 2000, 10000), "%.1f vs %.1f" % (band(a1, 2000, 10000), band(a0, 2000, 10000)))
a2 = seg(render(["wt 0 sine", FOFF(0), P(0, "level", 0.4), (307, 24), (308, L.dst_index(0, 1)), (309, 1.0), ("fshape", 0, "const", 1.0)], tag="fql"))[:, 0]
a3 = seg(render(["wt 0 sine", FOFF(0), P(0, "level", 0.4)], tag="fql0"))[:, 0]
check("Freq modulators do nothing on other destinations", abs(rms(a2) / rms(a3) - 1) < 0.01)
r = render(FQ(0.5) + [(307, 24), (308, DFQ(0)), (309, 0.25), ("fshape", 0, "ramp"), (1600, 400), (1602, 1)], note=45, hold=0.6, tail=0.1, tag="fq4")
e1, e2 = r[int(0.1 * RATE):int(0.2 * RATE), 0], r[int(0.4 * RATE):int(0.5 * RATE), 0]
check("a rising curve sweeps the pitch up over its Rate", peak_freq(e2) > 1.8 * peak_freq(e1), "%.0f -> %.0f Hz" % (peak_freq(e1), peak_freq(e2)))
r = render(FQ(0.5) + [(307, 24), (308, DFQ(0)), (309, 0.25), ("fshape", 0, "ramp"), (1600, 100), (1603, 1)], note=45, hold=0.9, tail=0.1, tag="fq5")
y1, y2 = r[int(0.3 * RATE):int(0.35 * RATE), 0], r[int(0.8 * RATE):int(0.85 * RATE), 0]
check("Loop repeats the curve, one shot holds its end", np.isfinite(r).all() and peak_freq(y1) > 0 and peak_freq(y2) > 0)
# ---------------------------------------------------------------- duplicated notes are ignored
def render_script(lines, tag):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    open(script, "w").write("\n".join(lines) + "\n")
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
base = ["wt 0 saw", "p %d 0" % L.pid(0, K["fon"]), "run 0.05"]
one = render_script(base + ["on 72 100", "run 0.4"], "dup1")
two = render_script(base + ["on 72 100", "on 72 100", "on 72 100", "run 0.4"], "dup3")
check("the same note pressed again while it sounds is ignored (one voice)", abs(rms(seg(two, 0.2, 0.4)) / rms(seg(one, 0.2, 0.4)) - 1) < 0.01, "%.4f vs %.4f" % (rms(seg(two, 0.2, 0.4)), rms(seg(one, 0.2, 0.4))))
oct2 = render_script(base + ["on 72 100", "on 60 100", "run 0.4"], "dup_other")
check("different notes still play together", rms(seg(oct2, 0.2, 0.4)) > 1.2 * rms(seg(one, 0.2, 0.4)))
rt = render_script(base + ["on 72 100", "run 0.2", "off 72", "run 0.5", "on 72 100", "run 0.4"], "dup_re")
check("after the release the note plays again", rms(rt[int(1.0 * RATE):int(1.15 * RATE)]) > 0.02)

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

# ---------------------------------------------------------------- physical modelling slot
def PH(o, key, v): return (L.phy_id(o, [q[0] for q in L.PHY if q[1] == key][0]), v)
PHYS = [P(0, "type", 3), P(0, "level", 0.8), FOFF(0)]
for m, name in enumerate(L.PHY_MODELS):
    a = render(PHYS + [PH(0, "phmodA", m), PH(0, "phbal", 0)], note=57, hold=0.8, tail=0.3, tag="phy%d" % m)
    x = a[:, 0]
    good = np.isfinite(x).all() and rms(x[int(0.05 * RATE):int(0.5 * RATE)]) > 0.01 and np.abs(x).max() < 2
    check("Physical model %s sounds and stays finite" % name, good, "rms %.3f peak %.2f" % (rms(x[int(0.05 * RATE):int(0.5 * RATE)]), np.abs(x).max()))
    if m in (0, 7): check("Physical %s plays the keyboard pitch (A3)" % name, abs(peak_freq(x[int(0.05 * RATE):int(0.5 * RATE)]) - 220) < 2.5, "%.1f" % peak_freq(x[int(0.05 * RATE):int(0.5 * RATE)]))
a = render(PHYS + [PH(0, "phbal", 0), PH(0, "phdecA", 0.15)], note=57, hold=1.0, tail=0.2, tag="phydec1")[:, 0]
b = render(PHYS + [PH(0, "phbal", 0), PH(0, "phdecA", 4.0)], note=57, hold=1.0, tail=0.2, tag="phydec2")[:, 0]
check("Decay sets how long the resonator rings", rms(b[int(0.8 * RATE):int(0.9 * RATE)]) > 20 * rms(a[int(0.8 * RATE):int(0.9 * RATE)]), "%.5f vs %.5f" % (rms(b[int(0.8 * RATE):int(0.9 * RATE)]), rms(a[int(0.8 * RATE):int(0.9 * RATE)])))
a = render(PHYS + [PH(0, "phbal", 0), PH(0, "phhitA", 0.5), PH(0, "phmix", 0)], note=57, hold=0.6, tail=0.1, tag="phyhit")[:, 0]
h1, h2 = band(a[int(0.05 * RATE):int(0.5 * RATE)], 210, 230), band(a[int(0.05 * RATE):int(0.5 * RATE)], 430, 450)
check("Hit position 0.5 on a string removes the even harmonics", h2 < 0.05 * h1, "%.1f / %.1f" % (h2, h1))
a = render(PHYS + [PH(0, "phbal", 1), PH(0, "phmodB", 7), PH(0, "phtunB", 12)], note=57, hold=0.6, tail=0.1, tag="phyB")[:, 0]
check("Resonator B follows B Tune (open tube, +12 st)", abs(peak_freq(a[int(0.05 * RATE):int(0.5 * RATE)]) - 440) < 5, "%.1f" % peak_freq(a[int(0.05 * RATE):int(0.5 * RATE)]))
a = render(PHYS + [PH(0, "phbal", 0.5), PH(0, "phser", 0)], note=57, hold=0.6, tail=0.1, tag="phypar")[:, 0]
b = render(PHYS + [PH(0, "phbal", 0.5), PH(0, "phser", 1)], note=57, hold=0.6, tail=0.1, tag="physer")[:, 0]
check("Serial coupling sounds and differs from parallel", np.isfinite(b).all() and rms(b[int(0.05 * RATE):int(0.5 * RATE)]) > 0.005 and np.abs(a[:int(0.5 * RATE)] - b[:int(0.5 * RATE)]).max() > 0.01)
a = render(PHYS + [PH(0, "phmix", 1), PH(0, "phntim", 2000), PH(0, "phbal", 0)], note=57, hold=0.8, tail=0.1, tag="phynz")[:, 0]
check("Noise exciter with a long Noise Time keeps the resonator sounding", rms(a[int(0.5 * RATE):int(0.7 * RATE)]) > 0.01, "%.4f" % rms(a[int(0.5 * RATE):int(0.7 * RATE)]))
ok = True
for t in range(4):
    a = render(PHYS + [PH(0, "phmodA", 2 * t), PH(0, "phmodB", 8 - t), PH(0, "phdecA", 20), PH(0, "phdecB", 20), PH(0, "phinhA", 1), PH(0, "phinhB", 1), PH(0, "phmatA", t % 2), PH(0, "phbal", 0.5),
                    PH(0, "phser", t % 2), PH(0, "phhard", 1), PH(0, "phmix", 0.5), P(0, "level", 1)], note=24 + 40 * (t % 2) + 20 * (t // 2), hold=0.4, tail=0.05, tag="phyext%d" % t)
    if not np.isfinite(a).all() or np.abs(a).max() > 8: ok = False
check("Physical slot stays finite and bounded at extreme settings", ok)

# ---------------------------------------------------------------- Alpha Juno DCO slot
JUNO = [P(0, "type", 4), P(0, "level", 0.8), FOFF(0)]
def JU(key, v): return PH(0, key, v)
only = lambda **kw: JUNO + [JU("jsaw", kw.get("saw", 0)), JU("jpulse", kw.get("pulse", 0)), JU("jsub", kw.get("sub", 0)), JU("jnoise", kw.get("noise", 0)), JU("jdrift", 0), JU("jcurve", kw.get("curve", 0))]
def jpk(cmds, note=57, tag="ju"):
    a = render(cmds, note=note, hold=0.8, tail=0.1, tag=tag)[:, 0]
    return peak_freq(a[int(0.1 * RATE):int(0.6 * RATE)]), a
f, a = jpk(only(saw=1), tag="jusaw")
check("Juno DCO saw plays the keyboard pitch (A3)", abs(f - 220) < 1.0 and rms(a[int(0.1 * RATE):int(0.6 * RATE)]) > 0.02, "%.2f Hz" % f)
f, a = jpk(only(pulse=1) + [JU("jwidth", 0.3)], tag="jupul")
check("Juno DCO pulse plays the keyboard pitch", abs(f - 220) < 1.0, "%.2f Hz" % f)
f, a = jpk(only(sub=1), tag="jusub")
check("Juno DCO sub oscillator sounds one octave below", abs(f - 110) < 1.0, "%.2f Hz" % f)
f, a = jpk(only(saw=1) + [JU("jrange", 0)], tag="ju16")
check("Range 16' is an octave down", abs(f - 110) < 1.0, "%.2f Hz" % f)
f, a = jpk(only(saw=1) + [JU("jrange", 2)], tag="ju4")
check("Range 4' is an octave up", abs(f - 440) < 2.0, "%.2f Hz" % f)
f, a = jpk(only(noise=1), tag="junz")
check("Juno DCO noise is broadband", rms(a[int(0.1 * RATE):int(0.6 * RATE)]) > 0.02 and band(a[int(0.1 * RATE):int(0.6 * RATE)], 5000, 15000) > 0.2 * band(a[int(0.1 * RATE):int(0.6 * RATE)], 100, 3000))
a = render(only(pulse=1) + [JU("jwidth", 0.5)], note=57, hold=0.6, tail=0.1, tag="jusq")[:, 0]
h1, h2 = band(a[int(0.1 * RATE):int(0.5 * RATE)], 210, 230), band(a[int(0.1 * RATE):int(0.5 * RATE)], 430, 450)
check("A pulse of width 50 % has no even harmonics", h2 < 0.05 * h1, "%.1f / %.1f" % (h2, h1))
a = render(only(pulse=1) + [JU("jwidth", 0.2)], note=57, hold=0.6, tail=0.1, tag="jun")[:, 0]
h2n = band(a[int(0.1 * RATE):int(0.5 * RATE)], 430, 450)
check("A narrow pulse has even harmonics", h2n > 0.15 * band(a[int(0.1 * RATE):int(0.5 * RATE)], 210, 230))
a0 = render(only(pulse=1) + [JU("jwidth", 0.5), JU("jpwm", 0)], note=57, hold=0.8, tail=0.1, tag="jupw0")[:, 0]
a1 = render(only(pulse=1) + [JU("jwidth", 0.5), JU("jpwm", 1), JU("jpwmr", 4)], note=57, hold=0.8, tail=0.1, tag="jupw1")[:, 0]
e0 = [band(a0[int(t * RATE):int((t + 0.1) * RATE)], 430, 450) for t in (0.1, 0.2, 0.3, 0.4)]
e1 = [band(a1[int(t * RATE):int((t + 0.1) * RATE)], 430, 450) for t in (0.1, 0.2, 0.3, 0.4)]
check("PWM moves the pulse width over time", max(e1) > 5 * (max(e0) + 1e-6) and max(e1) > 1.5 * min(e1), "%.1f..%.1f vs %.2f" % (min(e1), max(e1), max(e0)))
for st in range(5):
    f, a = jpk(only(saw=1) + [JU("jstype", st)], tag="jusaw%d" % st)
    check("Alpha Juno Saw %d plays the keyboard pitch" % (st + 1), abs(f - 220) < 1.5 and rms(a[int(0.1 * RATE):int(0.6 * RATE)]) > 0.02 and np.isfinite(a).all(), "%.2f Hz" % f)
for pt in range(3):
    f, a = jpk(only(pulse=1) + [JU("jptype", pt)], tag="jupt%d" % pt)
    check("Alpha Juno Pulse %d plays the keyboard pitch" % (pt + 1), abs(f - 220) < 1.5, "%.2f Hz" % f)
for bt, want in ((0, 110), (1, 110), (2, 55), (3, 55), (4, 110), (5, 110)):
    f, a = jpk(only(sub=1) + [JU("jbtype", bt)], tag="jubt%d" % bt)
    check("Alpha Juno Sub %d sounds at %d Hz" % (bt + 1, want), abs(f - want) < 1.5 and rms(a[int(0.1 * RATE):int(0.6 * RATE)]) > 0.02, "%.2f Hz" % f)
a = render(only(saw=1) + [JU("jstype", 1), JU("jwidth", 0.5), JU("jpwm", 1), JU("jpwms", 1)], note=57, hold=0.8, tail=0.1, tag="jupwe")[:, 0]
check("PWM saw with the envelope as PWM source stays finite", np.isfinite(a).all() and rms(a[int(0.1 * RATE):int(0.6 * RATE)]) > 0.02)
a0 = render(only(saw=1), note=57, hold=0.8, tail=0.1, tag="juvib0")[:, 0]
a1 = render(only(saw=1) + [JU("jvib", 1), JU("jpwmr", 5)], note=57, hold=0.8, tail=0.1, tag="juvib1")[:, 0]
g0 = [peak_freq(a0[int(t * RATE):int((t + 0.08) * RATE)]) for t in np.arange(0.1, 0.6, 0.05)]
g1 = [peak_freq(a1[int(t * RATE):int((t + 0.08) * RATE)]) for t in np.arange(0.1, 0.6, 0.05)]
check("Vibrato moves the pitch with the LFO", (max(g1) - min(g1)) > 3 and (max(g0) - min(g0)) < 1.0, "%.1f vs %.1f Hz spread" % (max(g1) - min(g1), max(g0) - min(g0)))
ok = True
for t, nt in enumerate((24, 60, 96, 120)):
    a = render(JUNO + [JU("jsaw", 1), JU("jpulse", 1), JU("jsub", 1), JU("jnoise", 1), JU("jcurve", 1), JU("jdrift", 1), JU("jpwm", 1), JU("jvib", 1), JU("jstype", 1 + t), JU("jbtype", t + 2), JU("jptype", t % 3), P(0, "level", 1)], note=nt, hold=0.3, tail=0.05, tag="juext%d" % t)
    if not np.isfinite(a).all() or np.abs(a).max() > 4: ok = False
check("Juno DCO stays finite and bounded at extreme settings", ok)

# ---------------------------------------------------------------- mod matrix: Physical / Alpha Juno destinations and slots 21..256
CONST1 = [("shape", 0, "const", 1), (882, 1), (247, 6)]
def MM(slot, src, dst, amt):   # slot is 0-based
    b = L.mod_slot_base(slot)
    return [(b, src), (b + 1, dst), (b + 2, amt)]
# slot 1 (matrix slot 1, LFO 1 constant +1) -> Juno Saw Level of OSC 1 (j = 16): a silent saw becomes audible
a0 = render(only(saw=0.0), tag="mdj0")
a1 = render(only(saw=0.0) + MM(0, 1, L.phydst(0, 16), 1.0) + CONST1, tag="mdj1")
check("Mod destination 'Juno Saw Level' of OSC 1 opens a silent saw", rms(seg(a0)) < 0.002 and rms(seg(a1)) > 0.02, "%.4f -> %.4f" % (rms(seg(a0)), rms(seg(a1))))
# the same destination of OSC 2 does not touch OSC 1
a2 = render(only(saw=0.0) + MM(0, 1, L.phydst(1, 16), 1.0) + CONST1, tag="mdj2")
check("Mod destination of OSC 2 leaves OSC 1 alone", rms(seg(a2)) < 0.002)
# Physical Material of OSC 1 (j = 5) changes the sound
pa = render(PHYS + [PH(0, "phbal", 0)], note=57, hold=0.6, tail=0.1, tag="mdp0")[:, 0]
pb = render(PHYS + [PH(0, "phbal", 0)] + MM(0, 1, L.phydst(0, 5), 1.0) + CONST1, note=57, hold=0.6, tail=0.1, tag="mdp1")[:, 0]
d = np.abs(pa[:int(0.5 * RATE)] - pb[:int(0.5 * RATE)]).max()
check("Mod destination 'Physical A Material' changes the sound", d > 0.01 and np.isfinite(pb).all(), "diff %.3f" % d)
# a slot far beyond the original 20 works: slot 21, 100 and 256
for sl in (20, 99, 255):
    a = render(only(saw=0.0) + MM(sl, 1, L.phydst(0, 16), 1.0) + CONST1, tag="mdslot%d" % sl)
    check("Mod matrix slot %d works" % (sl + 1), rms(seg(a)) > 0.02, "%.4f" % rms(seg(a)))
# 30 slots summing into one destination: 30 * 0.02 = 0.6, which moves a linear parameter by 0.6 * 50 % = 0.3
cmds = []
for sl in range(30): cmds += MM(sl, 1, L.phydst(0, 16), 0.02)
a = render(only(saw=0.0) + cmds + CONST1, tag="mdsum")
b = render(only(saw=0.3), tag="mdsum2")
check("30 mod slots add up on one destination", abs(rms(seg(a)) - rms(seg(b))) < 0.15 * rms(seg(b)) + 1e-4, "%.4f vs %.4f" % (rms(seg(a)), rms(seg(b))))
# clearing a high slot removes the modulation again
a = render(only(saw=0.0) + MM(99, 1, L.phydst(0, 16), 1.0) + MM(99, 0, 0, 0.0) + CONST1, tag="mdclr")
check("Clearing a high slot removes its modulation", rms(seg(a)) < 0.002)

# ---------------------------------------------------------------- per-slot Resonator stage and the pre-matrix order
RS = lambda key, v: P(0, key, v)
SAW = ["wt 0 saw", RS("level", 0.5), FOFF(0)]
base = SAW + [RS("rson", 0)]
a0 = render(base, note=45, hold=0.8, tail=0.1, tag="rs0")[:, 0]
a1 = render(SAW + [RS("rson", 1), RS("rsmod", 0), RS("rsdec", 3.0), RS("rsmix", 1.0), RS("rstune", 12)], note=45, hold=0.8, tail=0.1, tag="rs1")[:, 0]
w0, w1 = a0[int(0.2 * RATE):int(0.7 * RATE)], a1[int(0.2 * RATE):int(0.7 * RATE)]
r0 = band(w0, 210, 230) / (band(w0, 105, 115) + 1e-9); r1 = band(w1, 210, 230) / (band(w1, 105, 115) + 1e-9)
check("Resonator tuned an octave up (+12 st) emphasises 220 Hz over 110 Hz on a 110 Hz saw", r1 > 4 * r0 and np.isfinite(a1).all(), "%.2f -> %.2f" % (r0, r1))
a2 = render(SAW + [RS("rson", 1), RS("rsmix", 0.0)], note=45, hold=0.6, tail=0.1, tag="rs2")[:, 0]
check("Resonator mix 0 leaves the sound alone", np.abs(a2[:int(0.6 * RATE)] - a0[:int(0.6 * RATE)]).max() < 1e-4)
for m in range(9):
    a = render(SAW + [RS("rson", 1), RS("rsmod", m), RS("rsdec", 20), RS("rsmix", 1), RS("rsinh", 1)], note=45 + 3 * m, hold=0.4, tail=0.05, tag="rsm%d" % m)
    check("Resonator model %s stays finite and bounded" % L.PHY_MODELS[m], np.isfinite(a).all() and np.abs(a).max() < 4)
# order: distortion before / after the resonator differs
DST = [RS("dtype", 3), RS("ddrv", 1.0), RS("dmix", 1.0)]
RES = [RS("rson", 1), RS("rsdec", 1.0), RS("rsmix", 1.0)]
o1 = render(SAW + DST + RES + [RS("dpos", 2)], note=45, hold=0.6, tail=0.1, tag="ord2")[:, 0]   # Filter > Reso > Dist
o2 = render(SAW + DST + RES + [RS("dpos", 0)], note=45, hold=0.6, tail=0.1, tag="ord0")[:, 0]   # Filter > Dist > Reso
check("Pre-matrix order changes the result (Dist > Reso vs Reso > Dist)", np.abs(o1[:int(0.5 * RATE)] - o2[:int(0.5 * RATE)]).max() > 0.02 and np.isfinite(o1).all() and np.isfinite(o2).all())
ok = True
for t in range(6):
    a = render(SAW + DST + RES + [RS("fon", 1), RS("fcut", 800), RS("dpos", t), RS("rsdec", 20)], note=33 + 20 * (t % 3), hold=0.3, tail=0.05, tag="rsord%d" % t)
    if not np.isfinite(a).all() or np.abs(a).max() > 6: ok = False
check("All six pre-matrix orders stay finite and bounded", ok)
print("all passed" if not failures else "%d FAILED" % failures)
sys.exit(1 if failures else 0)
