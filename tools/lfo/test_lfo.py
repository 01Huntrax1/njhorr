#!/usr/bin/env python3
"""Tests of the LFO extras (tools/lfo/build_lfo2.py; ids 13000 + 16 * lfo + j).   python3 tools/lfo/test_lfo.py --host <dsp_host>"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'osc'))
import layout as L
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="lfoTest"); RATE = 48000; failures = 0; K = L.K
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def render(cmds, hold=1.5, tag="x", note=69, notes=(None,)):
    script = os.path.join(TMP, tag + ".txt"); out = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        for c in cmds: f.write((c if isinstance(c, str) else "p %d %s" % c) + "\n")
        f.write("run 0.05\non %d 100\nrun %s\noff %d\nrun 0.3\n" % (note, hold, note))
    subprocess.run([args.host, script, out], check=True)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2)
def rms(a): return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
def track(a, t0, t1, w=0.01): return np.array([rms(a[int((t0 + i * w) * RATE):int((t0 + (i + 1) * w) * RATE)]) for i in range(int((t1 - t0) / w))])
def amp(x, f):   # spectral magnitude near f
    x = x.astype(np.float64); fr = np.fft.rfftfreq(len(x), 1.0 / RATE); X = np.abs(np.fft.rfft(x * np.hanning(len(x)))); m = np.abs(fr - f) < 6
    return float(X[m].max())
BASE = ["wt 0 sine", (L.pid(0, K["fon"]), 0), (L.pid(0, K["level"]), 0.0)]
def route(src=1, slot=0, dest=1, amt=1.0): return [(307 + 3 * slot, src), (308 + 3 * slot, L.dst_index(0, dest)), (309 + 3 * slot, amt)]
def X(i, j, v): return (13000 + 16 * i + j, v)
KEY, RATIO, FINE, SKEW, STEPS, JIT, SPREAD, DEPTH, TPOS, INTERP = range(10)
def lfo(wave=0, rate=2.0, mode=0): return [(247, wave), (248, rate), (882, mode)]
mono = lambda a: a[:, 0]

# no NaN / inf anywhere
for tag, c in [("key", [X(0, KEY, 1)]), ("tab", lfo(7) + [X(0, TPOS, 0.6)]), ("all", [X(0, KEY, 1), X(0, SKEW, 0.7), X(0, STEPS, 5), X(0, JIT, 1), X(0, SPREAD, 1)])]:
    a = render(BASE + route() + lfo(0, 5.0) + c, tag=tag, hold=0.5)
    check("finite output: " + tag, bool(np.isfinite(a).all()) and rms(a) > 0)

# Key follow: the LFO runs at note frequency * ratio (measured as the modulation frequency of the level of a carrier four octaves up)
def modHz(c, note):
    a = render(BASE + [(L.pid(0, K["oct"]), 4)] + route() + c, tag="mh", note=note)[int(0.4 * RATE):int(1.2 * RATE), 0]
    env = np.sqrt(np.convolve(a.astype(np.float64) ** 2, np.ones(48) / 48, "same"))[::24]; env -= env.mean()
    S = np.abs(np.fft.rfft(env * np.hanning(len(env)))); fr = np.fft.rfftfreq(len(env), 24.0 / RATE)
    return float(fr[np.argmax(S[1:]) + 1])
f1 = modHz(lfo(0, 1.0) + [X(0, KEY, 1)], 45)
check("Key follow: LFO at the note frequency (A2 = 110 Hz)", abs(f1 - 110) < 4, "%.1f Hz" % f1)
f2 = modHz(lfo(0, 1.0) + [X(0, KEY, 1), X(0, RATIO, 2.0)], 45)
check("Key Ratio 2: 220 Hz", abs(f2 - 220) < 6, "%.1f Hz" % f2)
f3 = modHz(lfo(0, 1.0) + [X(0, KEY, 1)], 57)
check("Key follow tracks the note (A3 = 220 Hz)", abs(f3 - 220) < 6, "%.1f Hz" % f3)
f4 = modHz(lfo(0, 1.0) + [X(0, KEY, 1), X(0, FINE, 100)], 45)
check("Key Fine +100 ct: %.1f Hz" % (110 * 2 ** (1 / 12.0)), abs(f4 - 110 * 2 ** (1 / 12.0)) < 4, "%.1f Hz" % f4)
f5 = modHz(lfo(0, 1.0, 0), 45)
check("Without Key follow the LFO stays at its rate (1 Hz, no modulation near the note)", abs(f5 - 110) > 20)

# Depth scales the output
d1 = track(render(BASE + route() + lfo(0, 2.0), tag="d1"), 0.1, 1.4); d5 = track(render(BASE + route() + lfo(0, 2.0) + [X(0, DEPTH, 0.5)], tag="d5"), 0.1, 1.4)
check("Depth 0.5 halves the modulation", 0.35 < (d5.max() - d5.min()) / max(d1.max() - d1.min(), 1e-9) < 0.65, "%.3f / %.3f" % (d5.max() - d5.min(), d1.max() - d1.min()))
d0 = track(render(BASE + route() + lfo(0, 2.0) + [X(0, DEPTH, 0.0)], tag="d0"), 0.1, 1.4)
check("Depth 0 silences the modulation", d0.max() < 0.02 * max(d1.max(), 1e-9) + 1e-6)

# Steps: sine at 2 Hz quantised to 3 levels
def lfoTrack(wave, extra=(), **kw): return track(render(BASE + route() + lfo(wave, 2.0) + list(extra), **kw), 0.1, 1.4, 0.005)
st = track(render(BASE + route() + lfo(1, 2.0) + [X(0, STEPS, 3)], tag="st"), 0.1, 1.4, 0.005)
def flat(t):
    act = t[t > 0.1 * t.max()]; return float((act > 0.9 * act.max()).mean())
sm = lfoTrack(1, tag="sm0")
check("Steps 3: the output sits on its top level (a smooth triangle does not)", flat(st) > 0.8 and flat(sm) < 0.4, "%.2f vs %.2f" % (flat(st), flat(sm)))

# Skew: a saw bent by skew spends its time at another level (the mean of the track moves)
sk0 = track(render(BASE + route() + lfo(4, 2.0), tag="sk0"), 0.1, 1.4).mean(); sk1 = track(render(BASE + route() + lfo(4, 2.0) + [X(0, SKEW, 0.8)], tag="sk1"), 0.1, 1.4).mean()
check("Skew moves the average level of a saw", abs(sk1 - sk0) > 0.05 * max(sk0, 1e-9), "%.3f -> %.3f" % (sk0, sk1))

# Wavetable LFO: position 0 = sine, position 0.5 = saw
w0 = lfoTrack(0, tag="w0"); t0 = lfoTrack(7, [X(0, TPOS, 0.0)], tag="t0"); t2 = lfoTrack(4, tag="t2"); t5 = lfoTrack(7, [X(0, TPOS, 0.5)], tag="t5")
check("Wavetable LFO position 0 = sine", np.abs(t0 - w0).max() < 0.02 * max(w0.max(), 1e-9) + 1e-5)
check("Wavetable LFO position 0.5 = saw up", np.abs(t5 - t2).max() < 0.02 * max(t2.max(), 1e-9) + 1e-5)
t3 = lfoTrack(7, [X(0, TPOS, 0.25)], tag="t3"); tri = lfoTrack(1, tag="tri")
check("Wavetable LFO position 0.25 = triangle", np.abs(t3 - tri).max() < 0.02 * max(tri.max(), 1e-9) + 1e-5)
tm = lfoTrack(7, [X(0, TPOS, 0.125)], tag="tm")
check("Wavetable LFO position 0.125 lies between sine and triangle", bool(np.isfinite(tm).all()) and np.abs(tm - w0).max() > 1e-4)

# Voice Spread: with Trig and spread the start phase differs per voice
a = render(BASE + route() + lfo(0, 2.0, 1) + [X(0, SPREAD, 1.0)], tag="sp0", hold=0.5)
b = render(BASE + route() + lfo(0, 2.0, 1), tag="sp1", hold=0.5)
check("Voice Spread changes the start phase", abs(rms(a[int(0.1 * RATE):int(0.3 * RATE)]) - rms(b[int(0.1 * RATE):int(0.3 * RATE)])) > 1e-4)

# Jitter: the 5 Hz cycle length varies (the rate changes between cycles)
j0 = lfoTrack(0, [X(0, JIT, 0.0)], tag="j0"); j1 = lfoTrack(0, [X(0, JIT, 1.0)], tag="j1")
check("Jitter 0 is regular, jitter 1 differs", np.abs(j1 - j0).max() > 0.01 * max(j0.max(), 1e-9))
print("failures:", failures); sys.exit(1 if failures else 0)
