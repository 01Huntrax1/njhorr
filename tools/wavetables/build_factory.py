#!/usr/bin/env python3
"""Generates the Njohrr factory wavetables (wavetables/Factory/*.wav).

Format: mono, 16 bit, 44.1 kHz header, frames of 2048 samples (one cycle each), at most 128 frames.
Every frame is built additively (harmonic amplitudes + phases -> inverse FFT), so it is band-limited
(harmonics 1..1023) and loops perfectly. Every frame is DC-free and normalized to the same peak.

    python3 tools/wavetables/build_factory.py [outdir]
"""
import os, sys, wave
import numpy as np

N = 2048
H = N // 2            # harmonics 1..H-1 are usable
PEAK = 0.97

def frame(amp, phase=None):
    """amp[h], phase[h] for h = 0..H (index 0 unused) -> one normalized cycle."""
    spec = np.zeros(H + 1, dtype=complex)
    ph = np.zeros(H + 1) if phase is None else phase
    spec[1:H] = amp[1:H] * np.exp(1j * ph[1:H])
    # sine convention: x[n] = sum a_h sin(2 pi h n / N + phase)
    x = np.fft.irfft(spec * (-1j) * (N / 2), n=N)
    m = np.max(np.abs(x))
    return (x / m * PEAK) if m > 1e-9 else x

h = np.arange(H + 1, dtype=float)
def saw(nh=H - 1):   return np.where((h >= 1) & (h <= nh), 1.0 / np.maximum(h, 1), 0.0)
def sq(nh=H - 1):    return np.where((h >= 1) & (h <= nh) & (h % 2 == 1), 1.0 / np.maximum(h, 1), 0.0)
def tri(nh=H - 1):
    a = np.where((h >= 1) & (h <= nh) & (h % 2 == 1), 1.0 / np.maximum(h, 1) ** 2, 0.0)
    return a
def tri_phase():     return np.where(((h - 1) // 2) % 2 == 0, 0.0, np.pi)
def sine():          return np.where(h == 1, 1.0, 0.0)

def from_wave(x):
    """any one-cycle waveform of N samples -> band-limited normalized frame (keeps the phase)."""
    X = np.fft.rfft(x)[:H + 1]
    a = np.abs(X) / (N / 2); a[0] = 0
    p = np.angle(X) + np.pi / 2
    return frame(a, p)

def morph_frames(f0, f1, n):
    out = []
    for i in range(n):
        t = i / (n - 1)
        x = (1 - t) * f0 + t * f1
        m = np.max(np.abs(x)); out.append(x / m * PEAK)
    return out

def grow_harmonics(amp_fn, n, top=H - 1, phase=None):
    """frames with 1, 2, ... harmonics (fractional top harmonic fades in)."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        nh = 1 + t * (min(top, 64) - 1)
        a = amp_fn(H - 1) * np.clip(nh - (h - 1), 0, 1)
        out.append(frame(a, phase))
    return out

tables = {}

# ---- single-cycle basics, 8 frames (use Table Pos to step through them) ----
def pulse_frame(w):
    a = np.sin(np.pi * h * w) / np.maximum(h, 1) * (h >= 1) * (h < H)
    ph = np.where(h >= 1, np.pi / 2 - np.pi * h * w, 0.0)      # keeps the pulse centred
    return frame(a, ph)
tables["Basic Shapes"] = [
    frame(sine()), frame(tri(), tri_phase()), frame(saw()), frame(sq()),
    pulse_frame(0.25), pulse_frame(0.125),
    from_wave(np.maximum(np.sin(2 * np.pi * np.arange(N) / N), 0)),   # half-wave rectified sine
    from_wave(np.abs(np.sin(2 * np.pi * np.arange(N) / N))),          # full-wave rectified sine
]

tables["Sine to Saw"]      = grow_harmonics(saw, 64)
tables["Sine to Square"]   = grow_harmonics(sq, 64)
tables["Triangle to Saw"]  = morph_frames(frame(tri(), tri_phase()), frame(saw()), 64)
tables["Saw to Square"]    = morph_frames(frame(saw()), frame(sq()), 64)
tables["Sine to Triangle"] = morph_frames(frame(sine()), frame(tri(), tri_phase()), 32)

# ---- PWM: pulse width 50 % -> 3 % ----
tables["PWM"] = [pulse_frame(0.5 - 0.47 * i / 63) for i in range(64)]

# ---- hard sync sweep: saw synced to ratio 1 -> 8 (built from a 16x oversampled naive wave, band-limited by FFT) ----
def sync_frame(r):
    M = N * 16
    ph = (np.arange(M) / M * r) % 1.0
    x = 2 * ph - 1
    # wrap the cycle so that the base period starts at the discontinuity
    X = np.fft.rfft(x)[:H + 1]
    a = np.abs(X); p = np.angle(X)
    a[0] = 0; a[H] = 0
    return frame(a / (M / 2), p + np.pi / 2)
tables["Hard Sync"] = [sync_frame(1 + 7 * i / 63) for i in range(64)]

# ---- harmonic series: a single harmonic 1..32, then stacks ----
tables["Harmonics"] = [frame(np.where(h == k, 1.0, 0.0)) for k in range(1, 33)]
tables["Odd Harmonics"] = grow_harmonics(lambda top: np.where(h % 2 == 1, 1.0 / np.maximum(h, 1) ** 0.5, 0.0), 32)

# ---- FM sine: sin(x + I sin(x)), index 0 -> 8 ----
def fm_frame(idx):
    x = np.sin(2 * np.pi * np.arange(N) / N + idx * np.sin(2 * np.pi * np.arange(N) / N))
    return from_wave(x)
tables["FM Sine"] = [fm_frame(8 * i / 63) for i in range(64)]

# ---- resonant saw: a resonance peak sweeps over the harmonics of a saw ----
def reso_frame(pos, q=6.0):
    c = 1 + pos * 40
    res = 1 + q * np.exp(-0.5 * ((h - c) / 1.2) ** 2)
    return frame(saw() * res * np.where(h < c * 3 + 8, 1.0, np.exp(-(h - c * 3 - 8) / 6.0)))
tables["Resonant Saw"] = [reso_frame(i / 63) for i in range(64)]

# ---- vowels: a saw spectrum shaped by formants (fundamental assumed ~ 130 Hz) ----
VOW = {"A": (800, 1150, 2900), "E": (400, 1600, 2700), "I": (350, 1700, 2700), "O": (450, 800, 2830), "U": (325, 700, 2530)}
def vowel_amp(v):
    f = h * 130.0
    e = np.zeros_like(h)
    for fc, bw, g in zip(VOW[v], (80, 90, 120), (1.0, 0.6, 0.35)):
        e += g * np.exp(-0.5 * ((f - fc) / bw) ** 2)
    return saw() * (e + 0.02)
def vowel_morph(order, per=8):
    out = []
    for a, b in zip(order[:-1], order[1:]):
        for i in range(per):
            t = i / per
            out.append(frame((1 - t) * vowel_amp(a) + t * vowel_amp(b)))
    out.append(frame(vowel_amp(order[-1])))
    return out
tables["Vowels"] = vowel_morph(["A", "E", "I", "O", "U"])

# ---- organ: drawbars 16', 8', 5 1/3', 4', 2 2/3', 2', 1 3/5', 1 1/3', 1' = harmonics 1,2,3,4,6,8,10,12,16 (sub-octave omitted) ----
BARS = [1, 2, 3, 4, 6, 8, 10, 12, 16]
def organ_frame(w):
    a = np.zeros_like(h)
    for k, wk in zip(BARS, w): a[k] = wk
    return frame(a)
tables["Organ"] = [organ_frame(w) for w in (
    (1, 0, 0, 0, 0, 0, 0, 0, 0), (1, 1, 0, 0, 0, 0, 0, 0, 0), (1, 1, 1, 0, 0, 0, 0, 0, 0), (1, .8, .6, .8, 0, 0, 0, 0, 0),
    (1, .8, .6, .8, .5, .4, .3, .2, .2), (.8, 1, 1, 1, .8, .6, .5, .4, .3), (.5, 1, .3, .8, .2, .6, .1, .4, .1), (0, 1, 0, 1, 0, 1, 0, 1, 0))]

def write(path, frames):
    d = np.concatenate(frames)
    pcm = np.clip(np.round(d * 32767), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(pcm.tobytes())

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "wavetables", "Factory")
    os.makedirs(out, exist_ok=True)
    for name, fr in tables.items():
        assert 1 <= len(fr) <= 128 and all(len(f) == N for f in fr), name
        write(os.path.join(out, name + ".wav"), fr)
        print("%-18s %3d frames" % (name, len(fr)))
