"""Single source of truth for the 6-slot oscillator layout (DSP ids, UI specs)."""
OSC_COUNT = 6
BASE = 1000          # first oscillator parameter id
STRIDE = 64          # ids (and op[] entries) per oscillator
FM_BASE = 1400       # 6x6 frequency modulation matrix: FM_BASE + 6*src + dst
PM_BASE = 1440       # 6x6 phase modulation matrix: PM_BASE + 6*src + dst
PD_BASE = 1480       # 6x6 phase distortion matrix: PD_BASE + 6*src + dst
OSC_STRIDE_NAMES = ["OSC %d" % (i + 1) for i in range(OSC_COUNT)]
FILTER_TYPES = ["LP24", "LP12", "HP12", "BP12", "LP6", "LP18", "HP6", "HP18", "HP24", "BP24", "Notch12", "Notch24",
    "Peak", "LowShelf", "HighShelf", "Allpass", "Ladder", "Diode", "Acid", "Dirty LP", "Comb+", "Comb-", "Phaser", "Vowel",
    "MG Low 6", "MG Low 12", "MG Low 18", "MG Low 24", "Flange+", "Flange-"]
DIST_TYPES = ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch"]
SRC_TYPES = ["Wavetable", "Sampler", "Plaits"]
OUTS = ["Main", "Bus 1", "Bus 2"]
# k, key, label, short, min, max, init, unit, kind(sld/btn/sel/stp), step
# kind: sld = continuous, stp = integer stepper, btn = buttons, sel = dropdown
PARAMS = [
 (0,  "type",   "Source",        "Source",    0, 2, 0, "", "btn", SRC_TYPES),
 (1,  "level",  "Level",         "Level",     0, 1, 0.0, "", "sld", None),
 (2,  "pan",    "Pan",           "Pan",      -1, 1, 0, "", "sld", None),
 (3,  "out",    "Output",        "Output",    0, 2, 0, "", "btn", OUTS),
 (4,  "oct",    "Octave",        "Octave",   -4, 4, 0, "oct", "stp", None),
 (5,  "semi",   "Semi",          "Semi",    -12, 12, 0, "", "stp", None),
 (6,  "fine",   "Fine",          "Fine",   -100, 100, 0, "ct", "sld", None),
 (7,  "track",  "Key Track",     "Key Track", 0, 1, 1, "", "btn", ["Off", "On"]),
 (8,  "phase",  "Start Phase",   "Phase",     0, 1, 0, "", "sld", None),
 (9,  "rphase", "Random Phase",  "Rand Phase",0, 1, 0, "", "btn", ["Off", "On"]),
 (10, "wpos",   "WT Position",   "Position",  0, 1, 0, "", "sld", None),
 (11, "wsize",  "WT Frame Size", "Frame Size",0, 4, 3, "", "sel", ["256", "512", "1024", "2048", "4096"]),
 (12, "root",   "Root Note",     "Root Note", 0, 127, 60, "", "stp", None),
 (13, "uvox",   "Unison Voices", "Voices",    1, 7, 1, "", "stp", None),
 (14, "udet",   "Unison Detune", "Detune",    0, 1, 0.25, "", "sld", None),
 (15, "ublend", "Unison Blend",  "Blend",     0, 1, 1, "", "sld", None),
 (16, "uwid",   "Unison Width",  "Width",     0, 1, 0.75, "", "sld", None),
 (17, "ustyle", "Unison Style",  "Detune Curve", 0, 3, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd"]),
 (18, "w1m",    "Warp 1 Mode",   "Warp 1",    0, 8, 0, "", "sel", None),   # labels in UI (WARP_MODES)
 (19, "w1a",    "Warp 1 Amount", "Warp 1 Amt",0, 1, 0.5, "", "sld", None),
 (20, "w2m",    "Warp 2 Mode",   "Warp 2",    0, 8, 0, "", "sel", None),
 (21, "w2a",    "Warp 2 Amount", "Warp 2 Amt",0, 1, 0.5, "", "sld", None),
 (22, "sstart", "Sample Start",  "Start",     0, 1, 0, "", "sld", None),
 (23, "sloop",  "Sample Loop",   "Loop",      0, 1, 0, "", "btn", ["Off", "On"]),
 (24, "pleng",  "Plaits Engine", "Engine",    0, 23, 8, "", "sel", None),  # labels in UI (PLAITS_ENGINES)
 (25, "pharm",  "Plaits Harmonics", "Harmonics", 0, 1, 0.5, "", "sld", None),
 (26, "ptimb",  "Plaits Timbre", "Timbre",    0, 1, 0.5, "", "sld", None),
 (27, "pmorph", "Plaits Morph",  "Morph",     0, 1, 0.5, "", "sld", None),
 (30, "fon",    "Filter On",     "Filter",    0, 1, 1, "", "btn", ["Off", "On"]),
 (31, "ftype",  "Filter Type",   "Type",      0, 29, 0, "", "sel", None),
 (32, "fcut",   "Filter Cutoff", "Cutoff",   20, 18000, 8000, "Hz", "sld", None),
 (33, "fres",   "Filter Resonance", "Resonance", 0, 1, 0.25, "", "sld", None),
 (34, "fdrv",   "Filter Drive",  "Drive",     0, 1, 0, "", "sld", None),
 (35, "fkey",   "Filter Key Track", "Key Track", 0, 1, 0.5, "", "sld", None),
 (36, "feg",    "Filter EG Int", "EG Int",   -1, 1, 0, "", "sld", None),
 (37, "fvel",   "Filter Velocity", "Velocity", 0, 1, 0, "", "sld", None),
 (38, "fatk",   "Filter EG Attack",  "Attack",   0, 5000, 0, "ms", "sld", None),
 (39, "fdec",   "Filter EG Decay",   "Decay",   10, 5000, 300, "ms", "sld", None),
 (40, "fsus",   "Filter EG Sustain", "Sustain",  0, 1, 0, "", "sld", None),
 (41, "frel",   "Filter EG Release", "Release",  5, 5000, 250, "ms", "sld", None),
 (42, "dtype",  "Distortion Type",  "Type",      0, 6, 0, "", "sel", DIST_TYPES),
 (43, "ddrv",   "Distortion Drive", "Drive",     0, 1, 0.3, "", "sld", None),
 (44, "dmix",   "Distortion Mix",   "Mix",       0, 1, 1, "", "sld", None),
 (45, "dpos",   "Distortion Position", "Dist vs Filter", 0, 1, 0, "", "btn", ["Post", "Pre"]),   # Post = filter -> distortion, Pre = distortion -> filter
]
K = {p[1]: p[0] for p in PARAMS}

# mod matrix destinations
MOD_DST_GLOBAL = ["Pitch (all)", "Amp", "Pan", "Drive", "Out Gain"]   # indices 1..5
MOD_DST_OSC = ["Pitch", "Level", "Pan", "Position / Harm", "Warp 1 / Timbre", "Warp 2 / Morph", "Cutoff", "Reso", "Dist Drive"]
def dst_index(o, j): return 6 + 9 * o + j
N_DST = 6 + 9 * OSC_COUNT   # 60 (osc / global destinations); 60..167 = FM 60+n, PM 96+n, PD 132+n (n = 6*src + dst)
N_DST_ALL = N_DST + 108
def pid(o, k): return BASE + STRIDE * o + k
def fm_id(src, dst): return FM_BASE + 6 * src + dst
def pm_id(src, dst): return PM_BASE + 6 * src + dst
def pd_id(src, dst): return PD_BASE + 6 * src + dst
