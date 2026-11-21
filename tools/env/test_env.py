#!/usr/bin/env python3
"""Tests of the envelope extras (tools/env/build_env2.py; ids 13300 + 16 * k, k 0..9 mod, 10 amp, 11.. filter).   python3 tools/env/test_env.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="envTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def render(cmds, hold=1.0, tail=0.6, tag="x", note=69, vel=100):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\non %d %d\nrun %s\noff %d\nrun %s\n" % (note, vel, hold, note, tail))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def track(a, t0, t1, w=0.005): return np.array([rms(a[int((t0 + i * w) * RATE):int((t0 + (i + 1) * w) * RATE)]) for i in range(int((t1 - t0) / w))])
def X(k, j, v): return (13300 + 16 * k + j, v)
DELAY, HOLD, AC, DC, RC, VEL, KEY, LOOP, LVL = range(9)
BASE = ["wt 0 sine", (L.pid(0, K["level"]), 0.8), (L.pid(0, K["fon"]), 0)]
AMP = lambda a=2, d=500, s=0.8, r=250: [(18, a), (19, d), (20, s), (21, r)]
def tt(a, thr, t0=0.0, w=0.005):   # first time (s after t0) where the tracked level exceeds thr
    i = int(np.argmax(a > thr)); return t0 + i * w
# defaults sound like before: attack 100 ms, then sustain level 0.8 relative
a = render(BASE + AMP(100, 200, 0.5, 200), tag="def"); t = track(a, 0.05, 2.0)
check("finite and audible", bool(np.isfinite(a).all()) and rms(a) > 0.01)
base_sus = t[int(0.5 / 0.005)]
# Delay
d = render(BASE + AMP(5, 200, 0.5, 200) + [X(10, DELAY, 300)], tag="dly"); td = track(d, 0.05, 1.2)
check("Delay 300 ms: silent first, then rises", td[:int(0.25 / 0.005)].max() < 0.02 * max(td.max(), 1e-9) and td[int(0.5 / 0.005)] > 0.5 * base_sus, "%.3f" % td[:int(0.25 / 0.005)].max())
# Hold: attack 5 ms, decay 100 ms to sustain 0 -> with hold 400 ms the peak stays
nh = render(BASE + AMP(5, 100, 0.0, 200), tag="nh"); hh = render(BASE + AMP(5, 100, 0.0, 200) + [X(10, HOLD, 400)], tag="hh")
tn = track(nh, 0.05, 1.2); th = track(hh, 0.05, 1.2)
check("Hold 400 ms keeps the peak (without hold it decays already)", th[int(0.3 / 0.005)] > 0.9 * th.max() and tn[int(0.3 / 0.005)] < 0.5 * tn.max())
# Attack curve: +1 = fast start, -1 = slow start (level at the middle of the attack)
def mid(ac):
    r = render(BASE + AMP(400, 500, 1.0, 200) + [X(10, AC, ac)], tag="ac", hold=0.9); t = track(r, 0.05, 0.6); return t[int(0.2 / 0.005)] / t.max()
cp, cz, cn = mid(1.0), mid(0.0), mid(-1.0)
check("Attack curve: +1 above linear above -1 at half time", cp > cz + 0.1 and cz > cn + 0.1, "%.2f %.2f %.2f" % (cp, cz, cn))
# Decay / release curves
def relmid(rc):
    r = render(BASE + AMP(2, 500, 1.0, 400) + [X(10, RC, rc)], hold=0.6, tail=0.8, tag="rc"); t = track(r, 0.65, 1.4); return t[int(0.1 / 0.005)] / t.max()
r0, r1, rm = relmid(0.0), relmid(1.0), relmid(-1.0)
check("Release curve: +1 falls faster than 0, -1 slower", r1 < r0 - 0.05 and rm > r0 + 0.05, "%.2f %.2f %.2f" % (r1, r0, rm))
r = render(BASE + AMP(2, 500, 1.0, 400) + [X(10, RC, 0.3)], hold=0.6, tail=1.0, tag="rcend"); t = track(r, 0.65, 1.6)
check("Shaped release ends at silence", t[-5:].max() < 0.01 * t.max())
# Level scales the peak; Key track shortens times for higher notes
lv = render(BASE + AMP(2, 200, 1.0, 200) + [X(10, LVL, 0.5)], tag="lvl"); l1 = render(BASE + AMP(2, 200, 1.0, 200), tag="l1")
check("Level 0.5 halves the amplitude", 0.4 < rms(lv[int(0.3 * RATE):int(0.8 * RATE)]) / rms(l1[int(0.3 * RATE):int(0.8 * RATE)]) < 0.6)
def t50(note, key):
    r = render(BASE + AMP(400, 200, 1.0, 200) + [X(10, KEY, key)], note=note, tag="key", hold=0.9); t = track(r, 0.05, 0.9); return tt(t, 0.5 * t.max())
k0 = t50(81, 0.0); k1 = t50(81, 1.0)
check("Key track +1 at A5 (two octaves up) shortens the attack to about a quarter", k1 < 0.5 * k0, "%.3f vs %.3f s" % (k1, k0))
# Mod envelope (env 1 -> osc level): delay, loop, vel
def route(src, dest=1, amt=1.0): return [(307, src), (308, L.dst_index(0, dest)), (309, amt)]
MB = ["wt 0 sine", (L.pid(0, K["level"]), 0.0), (L.pid(0, K["fon"]), 0)]
def menv(a, d, s, r): return [(267, a), (268, d), (269, s), (270, r)]
m0 = render(MB + route(11) + menv(10, 200, 0.5, 200), tag="m0"); mt0 = track(m0, 0.05, 1.0)
m1 = render(MB + route(11) + menv(10, 200, 0.5, 200) + [X(0, DELAY, 300)], tag="m1"); mt1 = track(m1, 0.05, 1.0)
check("Mod env: Delay 300 ms", mt1[:int(0.25 / 0.005)].max() < 0.1 * mt0.max() and mt0[int(0.1 / 0.005)] > 0.2 * mt0.max())
lp = render(MB + route(11) + menv(10, 150, 0.0, 200) + [X(0, LOOP, 1)], hold=1.2, tag="lp"); tl = track(lp, 0.1, 1.2)
nl = render(MB + route(11) + menv(10, 150, 0.0, 200), hold=1.2, tag="nl"); tn2 = track(nl, 0.1, 1.2)
check("Mod env Loop: keeps cycling while the note is held (without loop it ends at 0)", tl[-40:].max() > 0.3 * tl.max() and tn2[-40:].max() < 0.1 * max(tn2.max(), 1e-9) + 1e-6, "%.3f %.3f" % (tl[-40:].max(), tn2[-40:].max()))
v1 = render(MB + route(11) + menv(10, 300, 1.0, 200) + [X(0, VEL, 1.0)], vel=40, tag="v1"); v2 = render(MB + route(11) + menv(10, 300, 1.0, 200) + [X(0, VEL, 1.0)], vel=127, tag="v2")
check("Mod env Velocity 1.0: harder notes give a higher peak", track(v2, 0.1, 0.5).max() > 1.5 * track(v1, 0.1, 0.5).max())
print("failures:", failures); sys.exit(1 if failures else 0)
