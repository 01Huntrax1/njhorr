#!/usr/bin/env python3
"""Module table of the Eurorack-style rack of "Njohrr Modular" (shared by build_euro.py, build_modplugin.py and the native UI table generator).
Signals are mono floats:  audio +-1,  CV in octaves / units (pitch: 0 = C4, +1 = one octave up),  gates 0 / 1.
Slot m (0..19) owns the ids  BASE + STRIDE * m + k :  0 type, 1..8 knobs (0..1), 9 mode, 10..13 source of input 1..4, 14..17 gain of input 1..4, 18 FX type.
Source numbers: 0 off, 1 Synth L, 2 Synth R, 3 Audio In L, 4 Audio In R, 5 + 2 * m + o = output o (0, 1) of slot m."""
NSLOT, BASE, STRIDE = 20, 10000, 32
NSRC = 5 + 2 * NSLOT
def pid(m, k): return BASE + STRIDE * m + k
K_TYPE, K_KNOB, K_MODE, K_SRC, K_GAIN, K_FX = 0, 1, 9, 10, 14, 18
# name, knobs (8, '' = unused), modes (or []), inputs (4), outputs (2)
MODS = [
 ("Empty",    [], [], [], []),
 ("MIDI-CV",  ["Glide >50%", "Transp", "Bend", "", "", "", "", ""], ["Last", "Low", "High"], [], ["Pitch", "Gate"]),
 ("VCO",      ["Coarse", "Fine", "FM", "PW", "Sub", "", "", ""], ["Sine", "Tri", "Saw", "Pulse"], ["V/Oct", "FM", "PWM", ""], ["Wave", "Sub"]),
 ("LFO",      ["Rate", "Depth", "Offset", "Phase", "", "", "", ""], ["Sine", "Tri", "Saw", "Square", "S&H"], ["Rate CV", "Reset", "", ""], ["Bipolar", "Unipolar"]),
 ("ADSR",     ["Attack", "Decay", "Sustain", "Release", "", "", "", ""], ["Normal", "Loop"], ["Gate", "", "", ""], ["Env", "Inverted"]),
 ("VCF",      ["Cutoff", "Reso", "CV Amt", "Drive", "", "", "", ""], ["LP", "HP", "BP", "Notch"], ["Audio", "Cutoff", "Reso", ""], ["Filter", "LP"]),
 ("VCA",      ["Level", "", "", "", "", "", "", ""], ["Linear", "Exp"], ["Audio", "CV", "", ""], ["Out", "Inverted"]),
 ("Mixer",    ["Level 1", "Level 2", "Level 3", "Level 4", "Master", "", "", ""], [], ["In 1", "In 2", "In 3", "In 4"], ["Sum", "Inverted"]),
 ("Noise",    ["Level", "Colour", "", "", "", "", "", ""], [], [], ["White", "Pink"]),
 ("S&H",      ["Slew", "", "", "", "", "", "", ""], ["Sample", "Track"], ["Signal", "Trigger", "", ""], ["Held", "Slewed"]),
 ("Sequencer",["Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6", "Step 7", "Step 8"], ["1 step", "2 steps", "3 steps", "4 steps", "5 steps", "6 steps", "7 steps", "8 steps"], ["Clock", "Reset", "", ""], ["Pitch", "Gate"]),
 ("Clock",    ["Tempo", "Width", "", "", "", "", "", ""], ["x1", "x2", "x4", "/2"], [], ["Clock", "Divided"]),
 ("Attenuverter", ["Scale 1", "Offset 1", "Scale 2", "Offset 2", "", "", "", ""], ["+", "-"], ["In 1", "In 2", "", ""], ["Out 1", "Out 2"]),
 ("Slew",     ["Rise", "Fall", "", "", "", "", "", ""], ["Linear", "Exp"], ["In", "", "", ""], ["Out", "Inverted"]),
 ("Folder",   ["Fold", "Symmetry", "Gain", "", "", "", "", ""], ["Fold", "Clip", "Rectify"], ["Audio", "Fold CV", "", ""], ["Out", "Soft"]),
 ("FX",       ["Param 1", "Param 2", "Param 3", "Param 4", "Param 5", "Param 6", "Mix", ""], [], ["Audio", "", "", ""], ["Left", "Right"]),
 ("Output",   ["Level", "", "", "", "", "", "", ""], ["Mono", "Stereo"], ["In 1", "In 2", "In 3", "In 4"], []),
 ("Ring Mod", ["Level", "", "", "", "", "", "", ""], ["Ring", "Sum"], ["A", "B", "", ""], ["Out", "Inverted"]),
]
NTYPE = len(MODS)
SRC_NAMES = ["Off", "Synth L", "Synth R", "Audio In L", "Audio In R"] + ["M%d %s" % (m + 1, o) for m in range(NSLOT) for o in ("A", "B")]
