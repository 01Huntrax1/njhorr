#!/usr/bin/env python3
"""Audio regression test of the FX rack DSP.

Builds nothing itself. Needs two scripted hosts (see dsp_host.cpp), one compiled from the DSP before the rack
(`--old`, the fixed FX chain) and one from the rack DSP (`--new`):

    python3 tools/rack/test_rack.py --old host_old --new host_new

1. every effect that existed in the fixed chain is rendered by the old chain and by a rack slot with equivalent
   settings; the outputs must match
2. the new effects (filter, EQ, compressor) do what they should
3. routing: order, bypass, mix, an invalid order, extreme settings
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--old", required=True)
ap.add_argument("--new", required=True)
args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="rackTest")
RATE = 48000
failures = 0


def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok:
        failures += 1


def render(host, params, note=60, hold=0.8, tail=0.8, tag="x"):
    """params: list of (paramNumber, value); returns float32 array (frames, 2)"""
    script = os.path.join(TMP, tag + ".txt")
    out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for n, v in params:
            f.write(f"p {n} {v}\n")
        f.write("run 0.05\n")                      # let every parameter event land before the note
        f.write(f"on {note} 100\nrun {hold}\noff {note}\nrun {tail}\n")
    subprocess.run([host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)


def rms(a):
    return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))


def rel_err(a, b):
    n = min(len(a), len(b))
    return rms(a[:n] - b[:n]) / max(rms(a[:n]), 1e-9)


def lognorm(v, lo, hi):
    return math.log(v / lo) / math.log(hi / lo)


def slot(s, ty, mode=0, mix=1.0, p=(), on=1):
    """parameter list for rack slot s (0-9)"""
    b = 541 + s * 10
    ps = list(p) + [0.5] * (6 - len(p))
    out = [(b, ty), (b + 1, on), (b + 2, mix), (b + 3, mode)]
    out += [(b + 4 + k, ps[k]) for k in range(6)]
    return out


# ------------------------------------------------------------------------------------------------ 1. old chain vs rack
# name -> (legacy parameters, rack parameters, allowed relative error)
SCEN = {}
for ty, name in enumerate(["digital", "tape", "dual"]):
    SCEN["delay " + name] = (
        [(32, 1), (183, 0.5), (30, 375), (31, 0.4), (60, 8000), (184, 0.7), (537, ty)],
        slot(0, 3, ty, 0.5, [lognorm(375, 10, 1000), 0.4 / 0.95, lognorm(8000, 500, 18000), 0.7]), 2e-3 if ty != 1 else 2e-2)   # tape: float rounding of the modulated read position
for m, name in enumerate(["classic", "dimension", "vibrato"]):
    SCEN["chorus " + name] = (
        [(164, 0.6), (165, 0.8), (166, 0.6), (177, 0.2), (538, m)],
        slot(0, 4, m, 0.6, [lognorm(0.8, 0.05, 5), 0.6, 0.2 / 0.9]), 2e-3)
SCEN["flanger"] = ([(185, 0.6), (186, 0.3), (187, 0.6), (188, 0.5)],
                   slot(0, 5, 0, 0.6, [lognorm(0.3, 0.05, 5), 0.6, 0.5 / 0.95]), 2e-3)
for st in range(4):
    SCEN[f"phaser {2 * (st + 1)} stages"] = (
        [(167, 0.6), (168, 0.4), (169, 0.5), (178, 0.5), (539, st)],
        slot(0, 6, st, 0.6, [lognorm(0.4, 0.05, 8), 0.5, 0.5 / 0.9]), 2e-3)
for w, name in enumerate(["sin", "tri", "square", "saw down", "saw up"]):
    SCEN["tremolo " + name] = (
        [(173, 0.7), (174, 5), (181, w), (182, 0.5)],
        slot(0, 7, w, 1.0, [lognorm(5, 0.1, 20), 0.7, 0.5]), 2e-3 if w < 2 else 3e-2)   # hard edges: sub-sample timing differences
for t, name in enumerate(["hall", "room", "plate", "cathedral"]):
    SCEN["reverb " + name] = (
        [(170, 0.5), (171, 0.5), (172, 0.5), (179, 20), (180, 1.0), (540, t)],
        slot(0, 8, t, 0.5, [0.5, 0.5, 20 / 100, 1.0]), 2e-3)
# the old bit crusher sat after the output gain / DC blocker, the rack one sits before them: close, not identical
SCEN["bit crush"] = ([(61, 8), (62, 4), (191, 0.7)],
                     slot(0, 2, 0, 0.7, [(16 - 8) / 12, 3 / 31]), 0.08)

print("== old fixed chain vs rack slot")
for name, (old, new, tol) in SCEN.items():
    a = render(args.old, old, tag="o")
    b = render(args.new, new, tag="n")
    e = rel_err(a, b)
    check(f"{name} matches the old chain", e < tol, f"rel err {e:.2e}, level {rms(a):.4f}")

# ------------------------------------------------------------------------------------------------ 2. new effects
print("== new effects")
dry = render(args.new, [], tag="d")
check("empty rack passes the old dry signal", rel_err(render(args.old, [], tag="od"), dry) < 1e-6)


def band(a, lo, hi):
    """energy of a signal between lo and hi Hz"""
    x = a[:, 0].astype(np.float64)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(spec[(f >= lo) & (f < hi)].sum()) + 1e-12


eq0 = render(args.new, slot(0, 10, 0, 1.0, [0.5, 0.5, 0.5, 0.5, 0.5]), tag="e0")
check("EQ at 0 dB is transparent", rel_err(dry, eq0) < 1e-4, f"{rel_err(dry, eq0):.2e}")
lo_dry = render(args.new, [], note=36, tag="l0")
lo_eq = render(args.new, slot(0, 10, 0, 1.0, [1.0, 0.5, 0.5, 0.5, 0.5]), note=36, tag="l1")
g = 10 * math.log10(band(lo_eq, 30, 200) / band(lo_dry, 30, 200))
check("EQ low shelf +12 dB boosts the low band", 6 < g < 14, f"{g:.1f} dB")
hi_dry = render(args.new, [], note=96, tag="h0")
hi_eq = render(args.new, slot(0, 10, 0, 1.0, [0.5, 0.5, 0.5, 0.0, 0.5]), note=96, tag="h1")
g = 10 * math.log10(band(hi_eq, 12000, 20000) / band(hi_dry, 12000, 20000))
check("EQ high shelf -12 dB cuts the high band", -14 < g < -4, f"{g:.1f} dB")

hi_note = 84
ref = render(args.new, [], note=hi_note, tag="f0")
lp = render(args.new, slot(0, 9, 0, 1.0, [lognorm(300, 20, 20000), 0.2, 0.0]), note=hi_note, tag="f1")
hp = render(args.new, slot(0, 9, 2, 1.0, [lognorm(300, 20, 20000), 0.2, 0.0]), note=36, tag="f2")
ref_lo = render(args.new, [], note=36, tag="f3")
check("filter low-pass at 300 Hz darkens a high note", rms(lp) < 0.35 * rms(ref), f"{rms(lp) / rms(ref):.2f}x")
check("filter high-pass at 300 Hz thins a low note", rms(hp) < 0.5 * rms(ref_lo), f"{rms(hp) / rms(ref_lo):.2f}x")
bp = render(args.new, slot(0, 9, 3, 1.0, [lognorm(1000, 20, 20000), 0.5, 0.0]), tag="f4")
nt = render(args.new, slot(0, 9, 10, 1.0, [lognorm(1000, 20, 20000), 0.5, 0.0]), tag="f5")
check("filter band-pass and notch produce different signals", rel_err(bp, nt) > 0.2)

# every one of the 30 filter types of the Filter page: the rack filter must sound like the voice filter
FT = ["LP24", "LP12", "HP12", "BP12", "LP6", "LP18", "HP6", "HP18", "HP24", "BP24", "Notch12", "Notch24", "Peak", "LowShelf", "HighShelf",
      "Allpass", "Ladder", "Diode", "Acid", "Dirty LP", "Comb+", "Comb-", "Phaser", "Vowel", "MG Low 6", "MG Low 12", "MG Low 18", "MG Low 24",
      "Flange+", "Flange-"]
NOISE = [(4, 4), (37, 0), (38, 0)]
OPEN = [(12, 1), (13, 18000), (14, 0), (15, 0), (17, 0), (43, 0), (44, 0)]          # voice filter: LP12 wide open, no modulation


def third_octave(a):
    x = a[int(0.3 * RATE):int(1.1 * RATE), 0].astype(np.float64)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    cs = [100 * 2 ** (i / 3) for i in range(18)]                                 # 100 Hz .. ~5 kHz
    return np.array([10 * math.log10(spec[(f >= c) & (f < c * 2 ** (1 / 3))].sum() + 1e-12) for c in cs])


for t, name in enumerate(FT):
    voice = render(args.new, NOISE + [(12, t), (13, 1000), (14, 0.5), (15, 0), (17, 0), (43, 0), (44, 0)], tag="v")
    rackf = render(args.new, NOISE + OPEN + slot(0, 9, t, 1.0, [lognorm(1000, 20, 20000), 0.5, 0.0]), tag="r")
    finite = np.isfinite(rackf).all() and np.abs(rackf).max() <= 1.0
    # Compare the spectral shape. The voice filter sits in front of the amp envelope and the rack behind it, so the deep stopband (the
    # envelope leaks into it) and the overall level of the saturating types differ by design: ignore bands more than 35 dB below
    # the loudest one and any constant level offset.
    tv, tr = third_octave(voice), third_octave(rackf)
    keep = tv > tv.max() - 35
    diff = (tv - tr)[keep]
    dev = float(np.abs(diff - np.median(diff)).mean()) if rms(voice) > 1e-4 else 99.0
    check(f"rack filter type {t} {name} sounds like the voice filter", finite and rms(rackf) > 1e-4 and dev < 2.5, f"mean band deviation {dev:.2f} dB")

comp_off = render(args.new, slot(0, 11, 0, 1.0, [1.0, 0.0, 0.2, 0.5, 0.0]), tag="c0")        # threshold 0 dB: no gain reduction
comp_on = render(args.new, slot(0, 11, 0, 1.0, [0.3, 1.0, 0.1, 0.5, 0.0]), tag="c1")          # -42 dB, 20:1
check("compressor above the threshold is transparent", rel_err(dry, comp_off) < 1e-3)
check("compressor reduces the level", rms(comp_on) < 0.6 * rms(dry), f"{rms(comp_on) / rms(dry):.2f}x")
comp_mk = render(args.new, slot(0, 11, 0, 1.0, [0.3, 1.0, 0.1, 0.5, 0.5]), tag="c2")         # +12 dB make-up
check("compressor make-up gain raises the level", rms(comp_mk) > 2.5 * rms(comp_on), f"{rms(comp_mk) / rms(comp_on):.2f}x")

for m, name in enumerate(["soft", "tube", "hard", "fold", "sine", "crunch"]):
    d = render(args.new, slot(0, 1, m, 1.0, [0.8, 1.0, 0.5]), tag="x")
    check(f"distortion {name} is finite and alters the sound", np.isfinite(d).all() and rel_err(dry, d) > 0.02, f"rel diff {rel_err(dry, d):.2f}")

# ------------------------------------------------------------------------------------------------ 3. routing
print("== routing")
dly = slot(0, 3, 0, 0.6, [0.6, 0.5, 0.8, 0.5])
dst = slot(1, 1, 3, 1.0, [0.9, 1.0, 0.5])
ab = render(args.new, dly + dst, tag="ab")
ba = render(args.new, dly + dst + [(641 + 0, 1), (641 + 1, 0)], tag="ba")              # order: slot 1 first, then slot 0
check("order matters (delay -> distortion differs from distortion -> delay)", rel_err(ab, ba) > 0.05, f"{rel_err(ab, ba):.2f}")
# the same two effects placed in the other slots with the default order must sound exactly like the swapped order
swapped = render(args.new, slot(1, 3, 0, 0.6, [0.6, 0.5, 0.8, 0.5]) + slot(0, 1, 3, 1.0, [0.9, 1.0, 0.5]), tag="sw")
check("reordering equals physically swapping the slots", rel_err(swapped, ba) < 1e-5, f"{rel_err(swapped, ba):.2e}")
bad = render(args.new, dly + dst + [(641 + 0, 1), (641 + 1, 1)], tag="bad")             # not a permutation: ignored
check("an order that is not a permutation is ignored", rel_err(ab, bad) < 1e-6)
perm = [3, 1, 0, 2, 9, 8, 7, 6, 5, 4]
pm = render(args.new, dly + dst + [(641 + k, v) for k, v in enumerate(perm)], tag="pm")
check("a full permutation of all 10 positions is accepted and stable", np.isfinite(pm).all() and rms(pm) > 0.01)
off = render(args.new, slot(0, 3, 0, 0.6, [0.6, 0.5, 0.8, 0.5], on=0), tag="off")
check("bypassed slot is transparent", rel_err(dry, off) < 1e-6)
m0 = render(args.new, slot(0, 8, 0, 0.0, [0.5, 0.5, 0.2, 1.0]), tag="m0")
check("mix 0 is transparent", rel_err(dry, m0) < 1e-6)
chain = []
for s, ty in enumerate([1, 9, 10, 11, 4, 5, 6, 7, 3, 8]):
    chain += slot(s, ty, 0, 0.5, [0.5, 0.5, 0.5, 0.5, 0.5])
full = render(args.new, chain, tag="full")
check("all 10 slots in use at once renders cleanly", np.isfinite(full).all() and 0 < abs(full).max() < 4, f"peak {abs(full).max():.2f}")

print("== extreme settings (stability)")
for ty in range(1, 12):
    for val in (0.0, 1.0):
        for mode in range(0, 6):
            a = render(args.new, slot(0, ty, mode, 1.0, [val] * 6), hold=0.5, tail=0.4, tag="ex")
            ok = np.isfinite(a).all() and abs(a).max() <= 1.0 + 1e-6
            if not ok:
                check(f"type {ty} mode {mode} all params {val}", False, f"peak {np.nanmax(abs(a)):.2f}")
                break
        else:
            continue
        break
    else:
        check(f"type {ty}: every mode with all params at 0 and at 1 stays finite and clipped to +-1", True)

print()
print("FAILURES: %d" % failures if failures else "ALL PASSED")
sys.exit(1 if failures else 0)
