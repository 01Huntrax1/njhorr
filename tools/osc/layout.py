"""Single source of truth for the 6-slot oscillator layout (DSP ids, UI specs)."""
OSC_COUNT = 6
BASE = 1000          # first oscillator parameter id
STRIDE = 64          # ids (and op[] entries) per oscillator
FM_BASE = 1400       # 6x6 frequency modulation matrix: FM_BASE + 6*src + dst
PM_BASE = 1440       # 6x6 phase modulation matrix: PM_BASE + 6*src + dst
PD_BASE = 1480       # 6x6 phase distortion matrix: PD_BASE + 6*src + dst
RM_BASE = 1520       # 6x6 ring modulation matrix: RM_BASE + 6*src + dst
AM_BASE = 1560       # 6x6 amplitude modulation matrix: AM_BASE + 6*src + dst
OSC_STRIDE_NAMES = ["OSC %d" % (i + 1) for i in range(OSC_COUNT)]
FILTER_TYPES = ["LP24", "LP12", "HP12", "BP12", "LP6", "LP18", "HP6", "HP18", "HP24", "BP24", "Notch12", "Notch24",
    "Peak", "LowShelf", "HighShelf", "Allpass", "Ladder", "Diode", "Acid", "Dirty LP", "Comb+", "Comb-", "Phaser", "Vowel",
    "MG Low 6", "MG Low 12", "MG Low 18", "MG Low 24", "Flange+", "Flange-"]
DIST_TYPES = ["Off", "Soft", "Tube", "Hard", "Fold", "Sine", "Crunch", "Wavedistortion"]
SRC_TYPES = ["Wavetable", "Sampler", "Wave Terrain", "Physical", "Alpha Juno", "Kick"]
TERRAINS = ["Sine Product", "Ripples", "Saddle", "Chebyshev", "Checker", "Spiral", "Diamond", "Interference", "Lattice", "Bumps", "Fractal", "Twist"]
WF_LAWS = ["Linear", "Bipolar", "dB"]
PHY_MODELS = ["String", "Beam", "Squared", "Membrane", "Plate", "Drumhead", "Marimba", "Open Tube", "Closed Tube"]
# order of the three pre-matrix stages (F = filter, D = distortion, R = resonator); index = stage order table row in the DSP
CHAIN_ORDERS = ["Filter > Dist > Reso", "Dist > Filter > Reso", "Filter > Reso > Dist", "Reso > Filter > Dist", "Dist > Reso > Filter", "Reso > Dist > Filter"]
OUTS = ["Main", "Bus 1", "Bus 2"]
# k, key, label, short, min, max, init, unit, kind(sld/btn/sel/stp), step
# kind: sld = continuous, stp = integer stepper, btn = buttons, sel = dropdown
PARAMS = [
 (0,  "type",   "Source",        "Source",    0, 5, 0, "", "sel", SRC_TYPES),
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
 (28, "udrift", "Unison Drift",  "Drift",     0, 1, 0, "", "sld", None),    # slow random pitch wander per unison voice (up to about 12 cents)
 (29, "uphase", "Unison Phase",  "Phase Spread", 0, 1, 0, "", "sld", None), # random start phase per unison voice
 (18, "w1m",    "Warp 1 Mode",   "Warp 1",    0, 8, 0, "", "sel", None),   # labels in UI (WARP_MODES)
 (19, "w1a",    "Warp 1 Amount", "Warp 1 Amt",0, 1, 0.5, "", "sld", None),
 (20, "w2m",    "Warp 2 Mode",   "Warp 2",    0, 8, 0, "", "sel", None),
 (21, "w2a",    "Warp 2 Amount", "Warp 2 Amt",0, 1, 0.5, "", "sld", None),
 (22, "sstart", "Sample Start",  "Start",     0, 1, 0, "", "sld", None),
 (23, "sloop",  "Sample Loop",   "Loop",      0, 1, 0, "", "btn", ["Off", "On"]),
 (24, "tterr",   "Terrain A",     "Terrain",   0, 11, 0, "", "sel", TERRAINS),
 (25, "tscale",  "Terrain Scale", "Scale",     0, 1, 0.5, "", "sld", None),   # 0.25 .. 4 times the terrain's features (exponential)
 (26, "twarp",   "Terrain Warp",  "Warp",      0, 1, 0, "", "sld", None),
 (27, "tfold",   "Terrain Fold",  "Fold",      0, 1, 0, "", "sld", None),
 (30, "fon",    "Filter On",     "Filter",    0, 1, 1, "", "btn", ["Off", "On"]),
 (31, "ftype",  "Filter Type",   "Type",      0, 30, 0, "", "sel", None),
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
 (42, "dtype",  "Distortion Type",  "Type",      0, 7, 0, "", "sel", DIST_TYPES),
 (43, "ddrv",   "Distortion Drive", "Drive",     0, 1, 0.3, "", "sld", None),
 (44, "dmix",   "Distortion Mix",   "Mix",       0, 1, 1, "", "sld", None),
 (48, "freq",   "Frequency", "Frequency", 0, 1, 0, "", "sld", None),   # 0 = Off (key pitch), else fixed 20 Hz .. 20 kHz
 (46, "wfpos",  "Wavefilter Position", "Table Pos", 0, 1, 0, "", "sld", None),
 (47, "wdpos",  "Wavedistortion Position", "Table Pos", 0, 1, 0, "", "sld", None),
 (49, "wfmix",  "Wavefilter Mix",      "Mix",       0, 1, 1, "", "sld", None),
 (50, "wfrange","Wavefilter Range",    "Range",     2, 14, 8, "oct", "sld", None),   # octaves covered by the table frame around the cutoff
 (51, "wfwarp", "Wavefilter Warp",     "Warp",     -1, 1, 0, "", "sld", None),     # bends the frequency axis (+: wider centre, -: wider edges)
 (52, "wfcont", "Wavefilter Contrast", "Contrast", -1, 1, 0, "", "sld", None),     # gains ^ (2 ^ (1.5 * contrast))
 (53, "wftilt", "Wavefilter Tilt",     "Tilt",     -1, 1, 0, "", "sld", None),     # +-6 dB per octave around the cutoff
 (54, "wfspr",  "Wavefilter Spread",   "Spread",    0, 1, 0, "", "sld", None),     # axis shifted down for the left, up for the right channel (+-1 octave)
 (55, "wflaw",  "Wavefilter Gain Law", "Gain Law",  0, 2, 0, "", "sel", WF_LAWS),  # table value -> gain
 (45, "dpos",   "Pre-Matrix Order", "Order", 0, 5, 0, "", "sel", CHAIN_ORDERS),   # order of the three stages between the source and the FM / PM matrix
 # resonator stage: the modal resonators of the Physical source (16 modes) as an effect, tuned to the played key
 (56, "rson",   "Resonator On",           "On",       0, 1, 0, "", "btn", ["Off", "On"]),
 (57, "rsmod",  "Resonator Model",        "Model",    0, 8, 0, "", "sel", PHY_MODELS),
 (58, "rsdec",  "Resonator Decay",        "Decay",    0.02, 20, 1.0, "s", "sld", None),
 (59, "rsmat",  "Resonator Material",     "Material", 0, 1, 0.5, "", "sld", None),
 (60, "rshit",  "Resonator Position",     "Position", 0, 1, 0.3, "", "sld", None),
 (61, "rsinh",  "Resonator Inharmonicity","Inharm",   0, 1, 0, "", "sld", None),
 (62, "rstune", "Resonator Tune",         "Tune",    -24, 24, 0, "st", "sld", None),
 (63, "rsmix",  "Resonator Mix",          "Mix",      0, 1, 0.5, "", "sld", None),
]
K = {p[1]: p[0] for p in PARAMS}

# mod matrix destinations
MOD_DST_GLOBAL = ["Pitch (all)", "Amp", "Pan", "Drive", "Out Gain"]   # indices 1..5
MOD_DST_OSC = ["Pitch", "Level", "Pan", "Position / Harm", "Warp 1 / Timbre", "Warp 2 / Morph", "Cutoff", "Reso", "Dist Drive"]
def dst_index(o, j): return 6 + 9 * o + j
N_DST = 6 + 9 * OSC_COUNT   # 60 (osc / global destinations); 60..167 = FM 60+n, PM 96+n, PD 132+n (n = 6*src + dst)
N_TBL_DST = N_DST + 108   # 168..179: Wavefilter / Wavedistortion table position of OSC 1..6 (168 + 2 * o, 169 + 2 * o)
N_FREQ_DST = N_TBL_DST + 12    # 180..185: oscillator Frequency knob of OSC 1..6 (the Freq modulators only reach these and the cutoffs)
N_RM_DST = N_FREQ_DST + 6      # 186..221: RM 186 + n, 222..257: AM 222 + n (n = 6 * src + dst)
N_DST_ALL = N_DST + 108 + 12 + 6 + 72
FRQ_BASE = 1600                 # Freq modulator m: rate (ms), transpose (semitones), retrig, loop = FRQ_BASE + 4 * m + 0..3
def pid(o, k): return BASE + STRIDE * o + k
def fm_id(src, dst): return FM_BASE + 6 * src + dst
def pm_id(src, dst): return PM_BASE + 6 * src + dst
def pd_id(src, dst): return PD_BASE + 6 * src + dst
def rm_id(src, dst): return RM_BASE + 6 * src + dst
def am_id(src, dst): return AM_BASE + 6 * src + dst

# Physical modelling source (Source = Physical, modal resonators in the style of RipplerX), implemented by tools/phys/build_phys.py.
# Parameter id of slot o: PHY_BASE + PHY_STRIDE * o + j.  j, key, name, short, min, max, init, unit, kind, options
PHY_BASE = 1700
PHY_STRIDE = 32
PHY_COUPLING = ["Parallel", "Serial"]
JUNO_RANGES = ["16'", "8'", "4'"]
JUNO_PULSE = ["Pulse 1", "Pulse 2", "Pulse 3"]
JUNO_SAW = ["Saw 1", "Saw 2", "Saw 3", "Saw 4", "Saw 5"]
JUNO_SUB = ["Sub 1", "Sub 2", "Sub 3", "Sub 4", "Sub 5", "Sub 6"]
JUNO_PWMS = ["LFO", "Env", "Manual"]
PHY = [
 (0,  "phmix",  "Noise vs Mallet",      "Noise",     0, 1, 0.25, "", "sld", None),
 (1,  "phhard", "Mallet Hardness",      "Hardness",  0, 1, 0.6, "", "sld", None),
 (2,  "phntim", "Noise Time",           "Noise Time", 2, 3000, 60, "ms", "sld", None),
 (3,  "phmodA", "A Model",              "Model",     0, 8, 0, "", "sel", PHY_MODELS),
 (4,  "phdecA", "A Decay",              "Decay",     0.02, 20, 2.5, "s", "sld", None),
 (5,  "phmatA", "A Material",           "Material",  0, 1, 0.5, "", "sld", None),
 (6,  "phhitA", "A Hit Position",       "Hit",       0, 1, 0.3, "", "sld", None),
 (7,  "phinhA", "A Inharmonicity",      "Inharm",    0, 1, 0.0, "", "sld", None),
 (8,  "phmodB", "B Model",              "Model",     0, 8, 3, "", "sel", PHY_MODELS),
 (9,  "phdecB", "B Decay",              "Decay",     0.02, 20, 1.5, "s", "sld", None),
 (10, "phmatB", "B Material",           "Material",  0, 1, 0.5, "", "sld", None),
 (11, "phhitB", "B Hit Position",       "Hit",       0, 1, 0.3, "", "sld", None),
 (12, "phinhB", "B Inharmonicity",      "Inharm",    0, 1, 0.0, "", "sld", None),
 (13, "phtunB", "B Tune",               "Tune",      -24, 24, 12, "st", "sld", None),
 (14, "phbal",  "A / B Balance",        "A / B",     0, 1, 0.35, "", "sld", None),
 (15, "phser",  "Coupling",             "Coupling",  0, 1, 0, "", "btn", PHY_COUPLING),
 # Alpha Juno style DCO (Source = Juno DCO), implemented by tools/phys/build_juno.py; the second half of the same id block
 (16, "jsaw",   "Juno Saw Level",       "Saw",       0, 1, 0.8, "", "sld", None),
 (17, "jpulse", "Juno Pulse Level",     "Pulse",     0, 1, 0.0, "", "sld", None),
 (18, "jwidth", "Juno Pulse Width",     "Width",     0, 1, 0.5, "", "sld", None),
 (19, "jpwm",   "Juno PWM Depth",       "PWM Depth", 0, 1, 0.0, "", "sld", None),
 (20, "jpwmr",  "Juno PWM Rate",        "PWM Rate",  0.1, 20, 1.5, "Hz", "sld", None),
 (21, "jsub",   "Juno Sub Level",       "Sub",       0, 1, 0.5, "", "sld", None),
 (22, "jnoise", "Juno Noise Level",     "Noise",     0, 1, 0.0, "", "sld", None),
 (23, "jrange", "Juno Range",           "Range",     0, 2, 1, "", "btn", JUNO_RANGES),
 (24, "jdrift", "Juno Drift",           "Drift",     0, 1, 0.2, "", "sld", None),
 (25, "jcurve", "Juno Saw Curve",       "Curve",     0, 1, 0.3, "", "sld", None),
 (26, "jptype", "Juno Pulse Wave",      "Pulse Wave", 0, 2, 0, "", "sel", JUNO_PULSE),
 (27, "jstype", "Juno Saw Wave",        "Saw Wave",  0, 4, 0, "", "sel", JUNO_SAW),
 (28, "jbtype", "Juno Sub Wave",        "Sub Wave",  0, 5, 0, "", "sel", JUNO_SUB),
 (29, "jpwms",  "Juno PWM Source",      "PWM Source", 0, 2, 0, "", "btn", JUNO_PWMS),
 (30, "jvib",   "Juno Vibrato",         "Vibrato",   0, 1, 0.0, "", "sld", None),
]
def phy_id(o, j): return PHY_BASE + PHY_STRIDE * o + j

# ---- mod matrix: 20 original slots (ids 307.. / 472..) + slots 21..MOD_SLOTS_MAX at MODX_BASE + 3 * (s - 20)  (s = 0-based slot index)
MOD_SLOTS_MAX = 256
MODX_BASE = 4000
def mod_slot_base(s): return 307 + 3 * s if s < 10 else (472 + 3 * (s - 10) if s < 20 else MODX_BASE + 3 * (s - 20))
# destinations 258..443: Physical / Alpha Juno parameter j (0..30) of slot o  ->  258 + 31 * o + j
PHY_DST_BASE = 258
def phydst(o, j): return PHY_DST_BASE + 31 * o + j
# Kick source (tools/kick/build_kick.py): parameter j (0..15) of slot o has the id KICK_BASE + 16 * o + j and the mod destination 444 + 16 * o + j
KICK_BASE = 1900
KICK_STRIDE = 16
KICK_MODES = ["Classic", "808", "Punch", "Hardstyle"]
KICK_CURVES = ["Hard Clip", "Tanh", "Atan", "Log", "Exp", "Poly"]
KICK = [
 (0,  "kmode",   "Kick Mode",          "Mode",        0, 3, 0, "", "sel", KICK_MODES),
 (1,  "ksweep",  "Kick Pitch Sweep",   "Sweep",       0, 6, 2.5, "oct", "sld", None),
 (2,  "kstime",  "Kick Sweep Time",    "Sweep Time",  5, 1000, 60, "ms", "sld", None),
 (3,  "kscurve", "Kick Sweep Curve",   "Curve",       0, 1, 0.5, "", "sld", None),
 (4,  "kdec",    "Kick Decay",         "Decay",       20, 3000, 450, "ms", "sld", None),
 (5,  "ktone",   "Kick Tone",          "Tone",        0, 1, 0.3, "", "sld", None),
 (6,  "kclick",  "Kick Click Level",   "Click",       0, 1, 0.35, "", "sld", None),
 (7,  "kcltone", "Kick Click Tone",    "Click Tone",  0, 1, 0.5, "", "sld", None),
 (8,  "knoise",  "Kick Noise Level",   "Noise",       0, 1, 0.0, "", "sld", None),
 (9,  "kdrive",  "Kick Drive",         "Drive",       0, 1, 0.2, "", "sld", None),
 (10, "kdtype",  "Kick Drive Curve",   "Curve",       0, 5, 1, "", "sel", KICK_CURVES),
 (11, "ksub",    "Kick Sub Level",     "Sub",         0, 1, 0.0, "", "sld", None),
 (12, "kpunch",  "Kick Punch",         "Punch",       0, 1, 0.3, "", "sld", None),
 (13, "ktune",   "Kick Tune",          "Tune",       -24, 24, 0, "st", "sld", None),
 (14, "kcldec",  "Kick Click Decay",   "Click Decay", 1, 40, 6, "ms", "sld", None),
 (15, "kchar",   "Kick Character",     "Character",   0, 1, 0.5, "", "sld", None),
]
def kick_id(o, j): return KICK_BASE + KICK_STRIDE * o + j
KICK_DST_BASE = PHY_DST_BASE + 31 * OSC_COUNT   # 444
def kickdst(o, j): return KICK_DST_BASE + KICK_STRIDE * o + j
# Wave Terrain extras (tools/osc/build_ter.py): parameter j (0..15) of slot o has the id TER_BASE + 16 * o + j and the mod destination 540 + 16 * o + j
TER_BASE = 2100
TER_STRIDE = 16
TER = [
 (0,  "tcx",     "Terrain Orbit Center X", "Center X",   -1, 1, 0.0, "", "sld", None),
 (1,  "tcy",     "Terrain Orbit Center Y", "Center Y",   -1, 1, 0.0, "", "sld", None),
 (2,  "trx",     "Terrain Orbit Radius X", "Radius X",    0, 1, 0.6, "", "sld", None),
 (3,  "try",     "Terrain Orbit Radius Y", "Radius Y",    0, 1, 0.6, "", "sld", None),
 (4,  "trot",    "Terrain Orbit Rotation", "Rotation",    0, 1, 0.0, "", "sld", None),
 (5,  "tratio",  "Terrain Orbit Ratio",    "Y : X",       0.25, 8, 1.0, "", "sld", None),
 (6,  "tphase",  "Terrain Orbit Phase",    "Phase",       0, 1, 0.0, "", "sld", None),
 (7,  "tshape",  "Terrain Orbit Shape",    "Shape",       0, 1, 0.0, "", "sld", None),
 (8,  "tmrate",  "Terrain Move Rate",      "Move Rate",   0.05, 20, 1.0, "Hz", "sld", None),
 (9,  "tmdep",   "Terrain Move Depth",     "Move Depth",  0, 1, 0.0, "", "sld", None),
 (10, "tterr2",  "Terrain B",              "Terrain B",   0, 11, 1, "", "sel", TERRAINS),
 (11, "tmorph",  "Terrain Morph A to B",   "Morph",       0, 1, 0.0, "", "sld", None),
 (12, "tsmooth", "Terrain Smooth",         "Smooth",      0, 1, 0.3, "", "sld", None),
 (13, "tdrive",  "Terrain Drive",          "Drive",       0, 1, 0.0, "", "sld", None),
 (14, "tbits",   "Terrain Bit Depth",      "Bits",        2, 16, 16, "", "sld", None),
 (15, "tvel",    "Terrain Velocity to Radius", "Vel > Radius", -1, 1, 0.0, "", "sld", None),
]
def ter_id(o, j): return TER_BASE + TER_STRIDE * o + j
TER_DST_BASE = KICK_DST_BASE + KICK_STRIDE * OSC_COUNT   # 540
def terdst(o, j): return TER_DST_BASE + TER_STRIDE * o + j
N_DST_TOTAL = TER_DST_BASE + TER_STRIDE * OSC_COUNT   # 636
