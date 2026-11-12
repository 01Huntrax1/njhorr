#!/usr/bin/env python3
"""Tests of the Inspirator sequencer (params 7000-7128).   python3 tools/mod/test_inspirator.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="insTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
I = 7000
BASE = ["wt 0 sine", (L.pid(0, K["fon"]), 0)]
def P(n, v): return (I + n, v)
def render(cmds, keys, hold=4.0, tail=0.6, tag="x"):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\n")
        for k in keys: f.write("on %d 100\n" % k)
        f.write("run %s\n" % hold)
        for k in keys: f.write("off %d\n" % k)
        f.write("run %s\n" % tail)
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)[:, 0]
rm = lambda x: float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
def cent(x):
    s = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float((s * f).sum() / (s.sum() + 1e-9))
def mode(m, *extra):
    c = [(I, 1), P(1, m), P(8, 2), P(10, 0)]   # on, mode, 4 bars, MIDI In = Transpose
    return c + [P(k, v) for k, v in extra]
a = render(BASE + [(I, 0)], [60], hold=1.0, tag="off")
check("Inspirator off: the key plays normally", rm(a[int(0.3 * RATE):int(0.9 * RATE)]) > 0.05)
for m, nm in enumerate(["Chords", "Lead", "Bass", "Arp", "Drums"]):
    a = render(BASE + mode(m), [60], tag="m%d" % m)
    body = a[int(0.5 * RATE):int(3.8 * RATE)]
    check("%s: the held key starts the generated pattern (sound, finite, bounded)" % nm, rm(body) > 0.01 and np.isfinite(a).all() and np.abs(a).max() < 6.0, "rms %.3f" % rm(body))
    check("%s: releasing the key stops the pattern" % nm, rm(a[int(4.4 * RATE):]) < 0.2 * max(rm(body), 1e-6) + 0.002, "%.4f" % rm(a[int(4.4 * RATE):]))
a1 = render(BASE + mode(1), [60], tag="s1"); a2 = render(BASE + mode(1), [60], tag="s2")
check("Same seeds give the same pattern", np.abs(a1 - a2).max() < 1e-5)
a3 = render(BASE + mode(1, (6, 77)), [60], tag="s3")
check("Another Part Seed gives another pattern", rm(a3 - a1) > 0.2 * rm(a1))
a4 = render(BASE + mode(1, (5, 4321)), [60], tag="s4")
check("Another Song Seed gives another pattern", rm(a4 - a1) > 0.1 * rm(a1))
for st in range(9):
    a = render(BASE + mode(0, (2, st)), [60], hold=3.0, tag="st%d" % st)
    check("Style %d stays finite and sounds" % st, np.isfinite(a).all() and rm(a[int(0.5 * RATE):int(2.8 * RATE)]) > 0.005 and np.abs(a).max() < 6.0)
lo = render(BASE + mode(2), [60], tag="t60"); hi = render(BASE + mode(2), [64], tag="t64"); dn = render(BASE + mode(2), [67], tag="t67")
r = cent(hi[int(0.5 * RATE):int(3.8 * RATE)]) / cent(lo[int(0.5 * RATE):int(3.8 * RATE)])
check("The key transposes the pattern (key 64 is a major third above key 60)", 1.12 < r < 1.45, "%.2f" % r)
r = cent(dn[int(0.5 * RATE):int(3.8 * RATE)]) / cent(lo[int(0.5 * RATE):int(3.8 * RATE)])
check("Keys above the fold transpose downwards (key 67 = a fourth below, like the original)", 0.6 < r < 0.9, "%.2f" % r)
ch1 = render(BASE + mode(0), [60], tag="cd0"); ch2 = render(BASE + mode(0, (44, 90)), [60], tag="cd1")
check("Chords Complexity changes the pattern", rm(ch2 - ch1) > 0.05 * rm(ch1))
d0 = render(BASE + mode(4, (81, 10)), [60], tag="dd0"); d1 = render(BASE + mode(4, (81, 100)), [60], tag="dd1")
check("Drums Density changes the pattern", rm(d1 - d0) > 0.05 * rm(d0 + 1e-6))
# ---- post-stage (7129-7138) ----
def differs(name, base_cmds, alt, key=60, thr=0.03):
    x = render(BASE + base_cmds, [key], tag="pa"); y = render(BASE + alt, [key], tag="pb")
    check(name, np.isfinite(y).all() and np.abs(y).max() < 6.0 and rm(y - x) > thr * rm(x) and rm(y[int(0.5 * RATE):int(3.8 * RATE)]) > 0.005, "d %.3f" % (rm(y - x) / max(rm(x), 1e-6)))
differs("Inversion changes the chords", mode(0), mode(0, (130, 2)))
differs("Spread changes the chords", mode(0), mode(0, (131, 2)))
differs("Strum changes the chords", mode(0), mode(0, (132, 100)))
for f, nm in [(1, "Up"), (2, "Down"), (3, "Up-Down"), (4, "Alberti")]:
    differs("Figure %s changes the chords" % nm, mode(0), mode(0, (133, f)))
differs("Ghost notes change the drums", mode(4), mode(4, (134, 100)))
differs("Ghost notes change the bass", mode(2), mode(2, (134, 100)))
differs("Chord pull changes the lead", mode(1), mode(1, (135, 100)))
differs("Max leap changes the lead", mode(1), mode(1, (136, 2)))
differs("Melody degree changes the lead", mode(1), mode(1, (138, 5)))
differs("Mutate changes the lead", mode(1), mode(1, (137, 80)))
differs("Mutate changes the drums", mode(4), mode(4, (137, 80)))
# locks: lock all bars while running, then change the Part Seed: the pattern must stay the same
def render_live(cmds, lock, seed, tag):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in BASE + cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\non 60 100\nrun 0.5\n")
        if lock: f.write("p %d 255\n" % (I + 129))
        f.write("run 0.1\np %d %d\nrun 3.4\noff 60\nrun 0.3\n" % (I + 6, seed))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)[:, 0]
seg = slice(int(1.2 * RATE), int(3.5 * RATE))
ref = render_live(mode(1), False, 1, "lkr"); unl = render_live(mode(1), False, 77, "lku"); lck = render_live(mode(1), True, 77, "lkl")
check("Seed change without lock changes the pattern", rm(unl[seg] - ref[seg]) > 0.1 * rm(ref[seg]))
check("Locked bars survive a seed change", rm(lck[seg] - ref[seg]) < 0.02 * rm(ref[seg]) + 1e-4, "%.4f" % (rm(lck[seg] - ref[seg]) / max(rm(ref[seg]), 1e-6)))
# ---- generators (7139/7140) ----
for g, nm in [(1, "Euclid"), (2, "Markov"), (3, "Cellular"), (4, "L-System")]:
    for m, mn in [(1, "Lead"), (2, "Bass"), (3, "Arp"), (4, "Drums")]:
        differs("%s generator changes %s" % (nm, mn), mode(m), mode(m, (139, g)))
differs("Generator variant changes Euclid lead", mode(1, (139, 1)), mode(1, (139, 1), (140, 5)))
differs("Generator variant changes Markov lead", mode(1, (139, 2)), mode(1, (139, 2), (140, 2)))
differs("Generator variant changes Cellular lead", mode(1, (139, 3)), mode(1, (139, 3), (140, 1)))
differs("Generator variant changes L-System lead", mode(1, (139, 4)), mode(1, (139, 4), (140, 1)))
# ---- MIDI import (7139 = 5) ----
imp = lambda k, *e: ["insimp " + k] + mode(1, (139, 5), *e)
a = render(BASE + imp("up"), [60], tag="im0"); b = render(BASE + imp("down"), [60], tag="im1")
check("Import plays the imported notes", np.isfinite(a).all() and rm(a[int(0.5 * RATE):int(3.8 * RATE)]) > 0.01)
check("A different imported melody sounds different", rm(a - b) > 0.1 * rm(a))
c = render(BASE + imp("up", (137, 80)), [60], tag="im2")
check("Mutate varies the imported pattern", rm(c - a) > 0.05 * rm(a))
m1 = render(BASE + ["insimp up"] + mode(1, (139, 2), (140, 3)), [60], tag="im3"); m2 = render(BASE + ["insimp down"] + mode(1, (139, 2), (140, 3)), [60], tag="im4")
check("Markov Custom corpus is trained by the import", np.isfinite(m1).all() and rm(m1 - m2) > 0.02 * rm(m1))
# ---- styles 9-13 ----
for st, nm in [(9, "Reggaeton"), (10, "Drum & Bass"), (11, "Afrobeats"), (12, "Funk"), (13, "Dub"), (14, "Disco"), (15, "Bossa Nova"), (16, "Synthwave"), (17, "Dubstep"), (18, "Trance"), (19, "Drill"), (20, "UK Garage"), (21, "Salsa"), (22, "Metal"), (23, "Country"), (24, "Blues"), (25, "Ambient"), (26, "Ska"), (27, "Amapiano"), (28, "Breakbeat"), (29, "Gospel"), (30, "Hardstyle"), (31, "Moombahton")]:
    for m, mn in enumerate(["Chords", "Lead", "Bass", "Arp", "Drums"]):
        a = render(BASE + mode(m, (2, st)), [60], hold=3.0, tag="ns")
        check("%s / %s sounds, finite" % (nm, mn), np.isfinite(a).all() and rm(a[int(0.5 * RATE):int(2.8 * RATE)]) > 0.005 and np.abs(a).max() < 6.0)
    x = render(BASE + mode(4, (2, st)), [60], tag="nsa"); y = render(BASE + mode(4, (2, 0)), [60], tag="nsb")
    check("%s drums differ from Pop" % nm, rm(x - y) > 0.1 * rm(y))
# ---- chord bass, drum chance, ratchet, poly, Walk / Permute (7139 = 6 / 7, 7141-7144) ----
differs("Chord bass adds a root note", mode(0), mode(0, (141, 1)))
differs("Chord bass with octave differs", mode(0, (141, 1)), mode(0, (141, 2)))
differs("Drum chance thins the drums", mode(4), mode(4, (142, 40)))
differs("Ratchet changes the drums", mode(4), mode(4, (143, 100)))
differs("Poly A changes the Euclid drums", mode(4, (139, 1)), mode(4, (139, 1), (144, 1)))
differs("Poly C changes the Euclid drums", mode(4, (139, 1)), mode(4, (139, 1), (144, 3)))
for g, nm in [(6, "Walk"), (7, "Permute")]:
    for m, mn in [(1, "Lead"), (2, "Bass"), (3, "Arp")]:
        differs("%s generator changes %s" % (nm, mn), mode(m), mode(m, (139, g)))
# ---- genre progressions: different Song Seeds pick different progressions of the style (major and minor) ----
for st in (9, 13, 15, 21, 24, 29):
    for sc, sn in ((0, "major"), (1, "minor")):
        outs = [render(BASE + mode(0, (2, st), (4, sc), (5, sd)), [60], hold=8.2, tag="gp%d" % sd) for sd in (11, 22, 33, 44, 55)]
        spread = max(rm(o - outs[0]) for o in outs[1:]) / max(rm(outs[0]), 1e-6)
        check("Style %d (%s): the Song Seed picks different progressions" % (st, sn), spread > 0.05, "%.2f" % spread)
# ---- Trance generator (7139 = 8) ----
for m, mn in enumerate(["Chords (pluck)", "Lead", "Bass", "Arp", "Drums"]):
    differs("Trance generator changes %s" % mn, mode(m), mode(m, (139, 8)))
for m, mn, vs in [(0, "pluck rhythm", (0, 4, 9)), (1, "lead kind", (0, 4, 8, 12)), (2, "bass type", (0, 1, 2, 3)), (3, "arp pattern", (0, 5, 11))]:
    for v in vs[1:]:
        differs("Trance %s: variant %d differs from variant %d" % (mn, v, vs[0]), mode(m, (139, 8), (140, vs[0])), mode(m, (139, 8), (140, v)))
differs("Trance bass: octave figure changes the line", mode(2, (139, 8)), mode(2, (139, 8), (140, 4)))
print("all passed" if not failures else "%d FAILED" % failures)
sys.exit(1 if failures else 0)
