#!/usr/bin/env python3
"""Turns the fixed FX chain of patch/Eisenpuls_Synth.cmajor into the modular FX rack.

One-shot migration, kept for reference and review: it asserts on every edit, so it refuses to run twice or on a
source it does not recognise.

    python3 tools/rack/apply_rack_patch.py patch/Eisenpuls_Synth.cmajor
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = Path(sys.argv[1])
src = path.read_text(encoding="utf-8")
assert "FX RACK" not in src, "already patched"

# ---------------------------------------------------------------------------------------------------- parameters
# old fixed-chain parameters that disappear (their sound now lives in the rack)
REMOVED = [30, 31, 32, 60, 61, 62] + list(range(164, 175)) + list(range(177, 189)) + [191, 537, 538, 539, 540]
# kept: 28 Drive, 29 Pan, 36 Master, 63 Tune, 175 Width, 189 Tone, 190 Out Gain, 221/222 DC block, 536 Drive algorithm

lines = src.split("\n")
out = []
removed_decl = removed_handler = 0
for ln in lines:
    m = re.match(r"\s*input event float param(\d+)\s", ln)
    if m and int(m.group(1)) in REMOVED:
        removed_decl += 1
        continue
    m = re.match(r"\s*event param(\d+)\s*\(float v\)\s*\{.*\}\s*$", ln)
    if m and int(m.group(1)) in REMOVED:
        removed_handler += 1
        continue
    out.append(ln)
assert removed_decl == len(REMOVED), (removed_decl, len(REMOVED))
assert removed_handler == len(REMOVED), (removed_handler, len(REMOVED))
src = "\n".join(out)

# ---------------------------------------------------------------------------------------------------- old state
OLD_STATE = """delayMs delayFb delayDepth delayDamp crushBits srrAmt chorusMix chorusRate chorusDepth phaserMix phaserRate phaserDepth
reverbMix reverbFb reverbDamp tremDepth tremRate chorusFb phaserFb reverbPreMs reverbWidth tremWave delayType chorusMode phaserStg
reverbType tremStereo delayMixAmt delayPing flangMix flangRate flangDepth flangFb crushMix chBufL chBufR chPos chPhase chFbL chFbR
flBufL flBufR flPos flPhase flFbL flFbR phZL phZR phFbL phFbR phPhase trPhase tpPhase tpPhase2 pdBuf pdPos rvInX rvInY rvOxL rvOyL
rvOxR rvOyR combBuf combPos combStore apBuf apPos bufL bufR writePos delayCur dampStL dampStR srrCount heldL heldR""".split()
decl = re.compile(r"^\s*(?:float64|float|int)(?:\[\d+\])?\s+(%s)\s*(?:=[^;]*)?;.*$" % "|".join(OLD_STATE))
out, n_state = [], 0
for ln in src.split("\n"):
    if decl.match(ln):
        n_state += 1
        continue
    out.append(ln)
assert n_state == len(OLD_STATE), (n_state, len(OLD_STATE))
src = "\n".join(out)

# ---------------------------------------------------------------------------------------------------- new params
pd = []   # declarations
ph = []   # handlers
ID0 = 541
for s in range(10):
    b = ID0 + s * 10
    n = s + 1
    pd.append(f'    input event float param{b}     [[ name: "FX {n} Type",  min: 0.0, max: 11.0, init: 0.0, step: 1.0 ]];')
    pd.append(f'    input event float param{b + 1}     [[ name: "FX {n} On",    min: 0.0, max: 1.0,  init: 1.0, step: 1.0 ]];')
    pd.append(f'    input event float param{b + 2}     [[ name: "FX {n} Mix",   min: 0.0, max: 1.0,  init: 1.0 ]];')
    pd.append(f'    input event float param{b + 3}     [[ name: "FX {n} Mode",  min: 0.0, max: 5.0,  init: 0.0, step: 1.0 ]];')
    for k in range(6):
        pd.append(f'    input event float param{b + 4 + k}     [[ name: "FX {n} P{k + 1}",    min: 0.0, max: 1.0,  init: 0.5 ]];')
    ph.append(f"    event param{b}     (float v) {{ fxSetType ({s}, int (v + 0.5f)); }}")
    ph.append(f"    event param{b + 1}     (float v) {{ fxOn.at ({s}) = v; }}")
    ph.append(f"    event param{b + 2}     (float v) {{ fxMix.at ({s}) = v; }}")
    ph.append(f"    event param{b + 3}     (float v) {{ fxMode.at ({s}) = clamp (int (v + 0.5f), 0, 5); fxDirty.at ({s}) = true; }}")
    for k in range(6):
        ph.append(f"    event param{b + 4 + k}     (float v) {{ fxP.at ({s * 6 + k}) = v; fxDirty.at ({s}) = true; }}")
for k in range(10):
    pd.append(f'    input event float param{641 + k}    [[ name: "FX Order {k + 1}", min: 0.0, max: 9.0, init: {float(k)}, step: 1.0 ]];')
    ph.append(f"    event param{641 + k}    (float v) {{ fxOrder.at ({k}) = clamp (int (v + 0.5f), 0, 9); fxRebuildSeq(); }}")

# declarations go after the last remaining algorithm parameter (536) block
anchor = re.search(r"^\s*input event float param536 .*$", src, re.M)
assert anchor
decl_block = "\n    // ---------------- FX RACK (10 slots, see the rack section below for the meaning of P1-P6) ----------------\n" + "\n".join(pd)
src = src[:anchor.end()] + decl_block + src[anchor.end():]

# handlers go after the Drive algorithm handler
anchor = re.search(r"^\s*event param536 .*$", src, re.M)
assert anchor
src = src[:anchor.end()] + "\n\n    // FX rack handlers\n" + "\n".join(ph) + src[anchor.end():]

# ---------------------------------------------------------------------------------------------------- new state
state = """
    // ---------------- FX RACK STATE ----------------
    int[10]       fxType;
    float[10]     fxOn;
    float[10]     fxMix;
    int[10]       fxMode;
    float[60]     fxP;
    bool[10]      fxDirty;
    int[10]       fxOrder;
    int[10]       fxSeq;
    float[160]    fxD;
    float[400]    fxF;
    int[240]      fxI;
    float64[40]   fxPh;
    float[1966080] fxArena;   // 10 slots x 196608 floats
"""
anchor = re.search(r"^\s*// Sample memory manager \(autosave\) state", src, re.M)
assert anchor
src = src[:anchor.start()] + state.lstrip("\n") + "\n" + src[anchor.start():]

# ---------------------------------------------------------------------------------------------------- drive shaper with explicit algorithm
old = "    float shapeSig (float x, float d)\n    {\n        float gd = 1.0f + d * 8.0f;\n        float xx = x * gd;\n        int   al = int (driveAlg + 0.5f);\n"
assert src.count(old) == 1
new = ("    float shapeSig (float x, float d)\n    {\n        return shapeSigAlg (x, d, int (driveAlg + 0.5f));\n    }\n\n"
       "    // drive shaper with an explicit algorithm (0 Soft, 1 Tube, 2 Hard, 3 Fold, 4 Sine, 5 Crunch)\n"
       "    float shapeSigAlg (float x, float d, int al)\n    {\n        float gd = 1.0f + d * 8.0f;\n        float xx = x * gd;\n")
src = src.replace(old, new)

# ---------------------------------------------------------------------------------------------------- rack code before the mixer EQ helpers
rack = (HERE / "rack_dsp.cmajor.part").read_text(encoding="utf-8")
anchor = "    // ---------------- MIXER EQ HELPERS (processor scope) ----------------"
assert src.count(anchor) == 1
src = src.replace(anchor, rack + anchor)

# init: start values of the rack
m = re.search(r"(        apLen\.at \(3\) = [^\n]*\n)(    \})", src)
assert m
src = src[:m.end(1)] + "\n        fxInit();\n" + src[m.start(2):]

# ---------------------------------------------------------------------------------------------------- main loop: replace the fixed chain
a = src.index("            float dryL = synL;")
b = src.index("            // ----- stereo width (mid/side) -----")
assert a < b
src = (src[:a]
       + "            // ----- FX rack (10 slots, user order); the master level sits in front of it -----\n"
         "            float<2> rack = fxRunRack (float<2> (synL * masterLevel, synR * masterLevel));\n"
         "            float outL = rack[0];\n"
         "            float outR = rack[1];\n\n"
       + src[b:])

a = src.index("            // ----- sample rate reduction -----")
b = src.index("            outL = clamp (outL, -1.0f, 1.0f);")
assert a < b
src = src[:a] + src[b:]

path.write_text(src, encoding="utf-8")
print("patched", path, "- removed", removed_decl, "params,", removed_handler, "handlers,", n_state, "state vars")
