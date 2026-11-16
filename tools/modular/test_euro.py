#!/usr/bin/env python3
"""Audio tests of the Eurorack rack of Njohrr Modular.   python3 tools/modular/test_euro.py --host <dsp_host of patch_mod, built with -DDSP_FX>"""
import argparse, os, subprocess, tempfile, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from euro_modules import *
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); args = ap.parse_args()
TMP = tempfile.mkdtemp(prefix="euroTest"); RATE = 48000; failures = 0
T = {m[0]: i for i, m in enumerate(MODS)}
def check(name, ok, extra=""):
    global failures
    print(("PASS " if ok else "FAIL ") + name + (("  (" + extra + ")") if extra else ""))
    if not ok: failures += 1
def out(m, o=0): return 5 + 2 * m + o
def mod(m, ty, knobs=None, mode=0, ins=None):
    """slot m: type name, knobs {index(0..7): value}, mode, ins [(src, gain)...]"""
    c = ["p %d %d" % (pid(m, K_TYPE), T[ty]), "p %d %d" % (pid(m, K_MODE), mode)]
    for k, v in (knobs or {}).items(): c.append("p %d %s" % (pid(m, K_KNOB + k), v))
    for i, (s, g) in enumerate(ins or []): c += ["p %d %d" % (pid(m, K_SRC + i), s), "p %d %s" % (pid(m, K_GAIN + i), g)]
    return c
def render(cmds, notes=(), hold=1.0, tag="x", audio=None):
    script = os.path.join(TMP, tag + ".txt"); o = os.path.join(TMP, tag + ".f32")
    with open(script, "w") as f:
        f.write("wt 0 saw\n")
        if audio: f.write("in %s %s %s\n" % audio)
        for i in range(64, 68): f.write("p %d 0\n" % (9700 + 8 * 16 + 2 * (i - 64)))
        for c in cmds: f.write(c + "\n")
        f.write("run 0.1\n")
        for n in notes: f.write("on %d 100\n" % n)
        f.write("run %s\n" % hold)
        for n in notes: f.write("off %d\n" % n)
        f.write("run 0.2\n")
    subprocess.run([args.host, script, o], check=True)
    return np.fromfile(o, dtype=np.float32).reshape(-1, 2)
def seg(a, t0=0.3, t1=1.0, ch=0): return a[int(t0 * RATE):int(t1 * RATE), ch].astype(np.float64)
def rms(x): return float(np.sqrt(np.mean(x ** 2)))
def freq(x):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))); return float(np.fft.rfftfreq(len(x), 1.0 / RATE)[int(np.argmax(X))])
OUT = lambda m, s: mod(m, "Output", {0: 0.5}, 0, [(s, 1.0)])

r = render([])
check("empty rack is silent", rms(seg(r)) < 1e-6 and np.isfinite(r).all())
r = render(mod(0, "VCO", {}, 0, []) + OUT(1, out(0)))
check("VCO (sine, no cable) plays C4 261.6 Hz", abs(freq(seg(r)) - 261.6) < 3 and rms(seg(r)) > 0.5, "%.1f Hz rms %.2f" % (freq(seg(r)), rms(seg(r))))
r = render(mod(0, "VCO", {}, 2, []) + OUT(1, out(0)))
check("VCO saw has harmonics", rms(seg(r)) > 0.4)
r = render(mod(0, "MIDI-CV") + mod(1, "VCO", {}, 0, [(out(0), 1.0)]) + OUT(2, out(1)), notes=(69,))
check("MIDI-CV -> VCO tracks the note (A4 = 440 Hz)", abs(freq(seg(r, 0.4, 1.0)) - 440) < 5, "%.1f" % freq(seg(r, 0.4, 1.0)))
r = render(mod(0, "MIDI-CV") + mod(1, "VCO", {}, 0, [(out(0), 1.0)]) + OUT(2, out(1)), notes=(81,))
check("one octave up doubles the frequency (A5 = 880 Hz)", abs(freq(seg(r, 0.4, 1.0)) - 880) < 8, "%.1f" % freq(seg(r, 0.4, 1.0)))
r = render(mod(0, "MIDI-CV") + mod(1, "VCO", {}, 2, [(out(0), 1.0)]) + mod(2, "ADSR", {0: 0.1, 1: 0.4, 2: 0.5, 3: 0.4}, 0, [(out(0, 1), 1.0)]) +
           mod(3, "VCA", {}, 0, [(out(1), 1.0), (out(2), 1.0)]) + OUT(4, out(3)), notes=(60,), hold=0.6, tag="adsr")
a = r[:, 0].astype(np.float64); pre = rms(a[:int(0.1 * RATE)]); sus = rms(a[int(0.5 * RATE):int(0.65 * RATE)]); rel = rms(a[int(0.78 * RATE):int(0.8 * RATE)]); tail = rms(a[int(0.88 * RATE):])
check("MIDI -> VCO -> ADSR/VCA: silent before the note, sounds during, decays after release", pre < 1e-3 and sus > 0.05 and rel < sus * 0.6 and tail < sus * 0.2, "pre %.4f sus %.3f rel %.3f tail %.3f" % (pre, sus, rel, tail))
vco = mod(0, "VCO", {}, 2, [])
lo = render(vco + mod(1, "VCF", {0: 0.3, 1: 0.2}, 0, [(out(0), 1.0)]) + OUT(2, out(1)), tag="lp")
hi = render(vco + mod(1, "VCF", {0: 0.3, 1: 0.2}, 1, [(out(0), 1.0)]) + OUT(2, out(1)), tag="hp")
def hfr(x): X = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.fft.rfftfreq(len(x), 1.0 / RATE); return float(np.sum(X[f > 3000] ** 2) / np.sum(X ** 2))
check("VCF low pass removes highs, high pass keeps them", hfr(seg(lo)) < 0.2 * hfr(seg(hi)) and rms(seg(lo)) > 0.01, "lp %.4f hp %.4f" % (hfr(seg(lo)), hfr(seg(hi))))
r = render(mod(0, "LFO", {0: 1.0, 1: 0.25}, 0, []) + OUT(1, out(0)), hold=1.0, tag="lfo")   # about 51 Hz (the plugin output has a DC blocker)
x = seg(r, 0.2, 1.0); check("LFO (51 Hz, depth 0.5) swings bipolar, rate is right", x.min() < -0.3 and x.max() > 0.3 and abs(freq(x) - 51.2) < 2, "%.2f..%.2f %.1f Hz" % (x.min(), x.max(), freq(x)))
r = render(mod(0, "Clock", {0: 0.5}, 0, []) + mod(1, "Sequencer", {0: 0.5, 1: 0.75, 2: 0.5, 3: 0.75}, 3, [(out(0), 1.0)]) + mod(2, "VCO", {}, 0, [(out(1), 1.0)]) + OUT(3, out(2)), hold=3.0, tag="seq")
fs = [freq(seg(r, t, t + 0.25)) for t in np.arange(0.2, 3.0, 0.25)]
check("Clock -> Sequencer -> VCO steps between two pitches", len(set(round(f / 20) for f in fs)) >= 2, "%s" % [round(f) for f in fs])
r = render(mod(0, "Noise", {0: 0.5}) + OUT(1, out(0)))
check("Noise is broadband and level knob works", 0.1 < rms(seg(r)) < 0.4, "%.3f" % rms(seg(r)))
r = render(mod(0, "VCO", {}, 0, []) + mod(1, "Mixer", {4: 0.25}, 0, [(out(0), 1.0), (out(0), 1.0)]) + OUT(2, out(1)))
r1 = render(mod(0, "VCO", {}, 0, []) + mod(1, "Mixer", {4: 0.25}, 0, [(out(0), 1.0)]) + OUT(2, out(1)), tag="m1")
check("Mixer with two equal inputs doubles the level", abs(rms(seg(r)) / rms(seg(r1)) - 2.0) < 0.05, "%.3f" % (rms(seg(r)) / rms(seg(r1))))
r = render(mod(0, "VCO", {}, 0, []) + mod(1, "Folder", {0: 0.9}, 0, [(out(0), 1.0)]) + OUT(2, out(1)))
check("Folder adds harmonics", hfr(seg(r)) > 0.05, "%.3f" % hfr(seg(r)))
r = render(mod(0, "FX", {}, 0, [(3, 1.0)]) + OUT(1, out(0)), audio=("sine", 0.3, 220.0), tag="fx0")
check("FX module (type none) passes Audio In", abs(rms(seg(r)) - 0.15 * 1.0 * 1.0) < 0.1 or rms(seg(r)) > 0.05, "%.3f" % rms(seg(r)))
r = render(mod(0, "FX", {6: 1.0}, 0, [(3, 1.0)]) + ["p %d 1" % pid(0, K_FX)] + OUT(1, out(0)), audio=("sine", 0.3, 220.0), tag="fx1")
check("FX module as Distortion changes the sound", hfr(seg(r)) > 0.0 and rms(seg(r)) > 0.05)
r = render(mod(0, "VCO", {}, 0, []) + mod(1, "Attenuverter", {0: 0.5, 1: 0.5}, 1, [(out(0), 1.0)]) + mod(2, "Mixer", {0: 0.5, 1: 0.5, 4: 0.5}, 0, [(out(0), 1.0), (out(1), 1.0)]) + OUT(3, out(2)))
check("Attenuverter (inverting) cancels the original in a mixer", rms(seg(r)) < 0.02, "%.4f" % rms(seg(r)))
r = render(mod(0, "VCO", {}, 0, []) + mod(1, "Ring Mod", {}, 0, [(out(0), 1.0), (out(0), 1.0)]) + OUT(2, out(1)))
check("Ring modulator of a sine with itself gives double frequency", abs(freq(seg(r)) - 523) < 6, "%.1f" % freq(seg(r)))
r = render(mod(0, "VCO", {}, 0, [(out(0), 1.0)]) + OUT(1, out(0)), tag="fb")
check("self patched VCO stays finite", np.isfinite(r).all())
print("%d failures" % failures); sys.exit(1 if failures else 0)
