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
# racks: (name, first slot parameter id, first order parameter id); Main keeps the ids of the first rack release
RACKS = [("Main", 541, 641), ("Bus 1", 651, 751), ("Bus 2", 761, 861)]
for rk, (rname, id0, ord0) in enumerate(RACKS):
    for s in range(10):
        b = id0 + s * 10
        n = s + 1
        g = rk * 10 + s           # global slot
        t = f"{rname} FX {n}"
        pd.append(f'    input event float param{b}     [[ name: "{t} Type",  min: 0.0, max: 11.0, init: 0.0, step: 1.0 ]];')
        pd.append(f'    input event float param{b + 1}     [[ name: "{t} On",    min: 0.0, max: 1.0,  init: 1.0, step: 1.0 ]];')
        pd.append(f'    input event float param{b + 2}     [[ name: "{t} Mix",   min: 0.0, max: 1.0,  init: 1.0 ]];')
        pd.append(f'    input event float param{b + 3}     [[ name: "{t} Mode",  min: 0.0, max: 29.0, init: 0.0, step: 1.0 ]];')
        for k in range(6):
            pd.append(f'    input event float param{b + 4 + k}     [[ name: "{t} P{k + 1}",    min: 0.0, max: 1.0,  init: 0.5 ]];')
        ph.append(f"    event param{b}     (float v) {{ fxSetType ({g}, int (v + 0.5f)); }}")
        ph.append(f"    event param{b + 1}     (float v) {{ fxOn.at ({g}) = v; }}")
        ph.append(f"    event param{b + 2}     (float v) {{ fxMix.at ({g}) = v; }}")
        ph.append(f"    event param{b + 3}     (float v) {{ fxMode.at ({g}) = clamp (int (v + 0.5f), 0, 29); fxDirty.at ({g}) = true; }}")
        for k in range(6):
            ph.append(f"    event param{b + 4 + k}     (float v) {{ fxP.at ({g * 6 + k}) = v; fxDirty.at ({g}) = true; }}")
    for k in range(10):
        pd.append(f'    input event float param{ord0 + k}    [[ name: "{rname} FX Order {k + 1}", min: 0.0, max: 9.0, init: {float(k)}, step: 1.0 ]];')
        ph.append(f"    event param{ord0 + k}    (float v) {{ fxOrder.at ({rk * 10 + k}) = clamp (int (v + 0.5f), 0, 9); fxRebuildSeq ({rk}); }}")

# source routing (which rack a mixer channel feeds) and the two bus levels
ROUTE_NAMES = ["Osc", "Sub", "Noise", "Supersaw", "Sampler 1", "Sampler 2", "WT 1", "WT 2", "WT 3"]
for i, nm in enumerate(ROUTE_NAMES):
    pd.append(f'    input event float param{871 + i}    [[ name: "{nm} Output", min: 0.0, max: 2.0, init: 0.0, step: 1.0 ]];')
    ph.append(f"    event param{871 + i}    (float v) {{ srcRoute.at ({i}) = clamp (int (v + 0.5f), 0, 2); }}")
pd.append('    input event float param880    [[ name: "Bus 1 Level", min: 0.0, max: 1.5, init: 1.0 ]];')
pd.append('    input event float param881    [[ name: "Bus 2 Level", min: 0.0, max: 1.5, init: 1.0 ]];')
ph.append("    event param880    (float v) { busLevel1 = v; }")
ph.append("    event param881    (float v) { busLevel2 = v; }")

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
    int[30]       fxType;
    float[30]     fxOn;
    float[30]     fxMix;
    int[30]       fxMode;
    float[180]    fxP;
    bool[30]      fxDirty;
    int[30]       fxOrder;
    int[30]       fxSeq;
    float[480]    fxD;
    float[1200]   fxF;
    int[720]      fxI;
    float64[120]  fxPh;
    float[5898240] fxArena;   // 30 slots x 196608 floats
    float[6]      busDcX;
    float[6]      busDcY;
    int[9]        srcRoute;   // output rack of each mixer channel: 0 Main, 1 Bus 1, 2 Bus 2
    float         busLevel1 = 1.0f;
    float         busLevel2 = 1.0f;
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

# ---------------------------------------------------------------------------------------------------- main loop: buses + racks
def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:90])
    src = src.replace(old, new)

# --- voice state: three independent filter state sets (one per output bus); filterStepX picks the set through its bank argument
rep("        float[64]   fx;       // extra filter states: filter * 32 + channel * 16 + stage state",
    "        float[192]  fx;       // filter states: (bus * 2 + filter) * 32 + channel * 16 + stage state")
rep("        float[8192] fdl;      // comb filter delay lines: filter * 4096 + channel * 2048 + position",
    "        float[24576] fdl;     // comb filter delay lines: (bus * 2 + filter) * 4096 + channel * 2048 + position")
rep("                for (int fq = 0; fq < 64; ++fq)\n                    voices.at (v).fx.at (fq) = 0.0f;",
    "                for (int fq = 0; fq < 192; ++fq)\n                    voices.at (v).fx.at (fq) = 0.0f;")
rep("                for (int fd = 0; fd < 8192; ++fd)", "                for (int fd = 0; fd < 24576; ++fd)")

# --- sources are collected per output bus: bInL/R = through the voice filter, bDryL/R = filter bypass
rep("""                float sCom = oscMixed + subS * subLvl + nsS * nsLvl;
                if (anySolo) sCom = 0.0f;
                float sL   = sCom;
                float sR   = sCom;
""", """                float[3] bInL;
                float[3] bInR;
                float[3] bDryL;
                float[3] bDryR;

                if (! anySolo)
                {
                    int rO = srcRoute.at (0);
                    int rS = srcRoute.at (1);
                    int rN = srcRoute.at (2);
                    bInL.at (rO) += oscMixed;
                    bInR.at (rO) += oscMixed;
                    bInL.at (rS) += subS * subLvl;
                    bInR.at (rS) += subS * subLvl;
                    bInL.at (rN) += nsS * nsLvl;
                    bInR.at (rN) += nsS * nsLvl;
                }
""")
rep("""                    sL += ssEqL * ssLvl;
                    sR += ssEqR * ssLvl;""", """                    bInL.at (srcRoute.at (3)) += ssEqL * ssLvl;
                    bInR.at (srcRoute.at (3)) += ssEqR * ssLvl;""")
rep("""                        sL += smpSigS;
                        sR += smpSigS;
                    }
                    else
                    {
                        smpDry = smpSigS;
                    }""", """                        bInL.at (srcRoute.at (4)) += smpSigS;
                        bInR.at (srcRoute.at (4)) += smpSigS;
                    }
                    else
                    {
                        bDryL.at (srcRoute.at (4)) += smpSigS;
                        bDryR.at (srcRoute.at (4)) += smpSigS;
                    }""")
rep("""                        sL += smpSig2;
                        sR += smpSig2;
                    }
                    else
                    {
                        smpDry2 = smpSig2;
                    }""", """                        bInL.at (srcRoute.at (5)) += smpSig2;
                        bInR.at (srcRoute.at (5)) += smpSig2;
                    }
                    else
                    {
                        bDryL.at (srcRoute.at (5)) += smpSig2;
                        bDryR.at (srcRoute.at (5)) += smpSig2;
                    }""")
for tag, idx, nm in [("", 6, "wt"), ("2", 7, "wt2"), ("3", 8, "wt3")]:
    rep(f"""                        sL += {nm}SigL;
                        sR += {nm}SigR;
                    }}
                    else
                    {{
                        {nm}DryL = {nm}SigL;
                        {nm}DryR = {nm}SigR;
                    }}""", f"""                        bInL.at (srcRoute.at ({idx})) += {nm}SigL;
                        bInR.at (srcRoute.at ({idx})) += {nm}SigR;
                    }}
                    else
                    {{
                        bDryL.at (srcRoute.at ({idx})) += {nm}SigL;
                        bDryR.at (srcRoute.at ({idx})) += {nm}SigR;
                    }}""")

# --- the voice filter runs once per bus that has a source routed to it (the Main bus always runs)
rep("""                // pre-filter drive
                float sDryL = sL;
                float sDryR = sR;
""", """                float a = e * voices.at (i).velGain * (1.0f - lfoAmp * (0.5f - 0.5f * lfo)) * clamp (1.0f + vmod.at (4), 0.0f, 2.0f);

                float[3] gOutL;
                float[3] gOutR;

                for (int grp = 0; grp < 3; ++grp)
                {
                    bool grpOn = (grp == 0);
                    for (int rj = 0; rj < 9; ++rj)
                        if (srcRoute.at (rj) == grp) grpOn = true;

                    if (! grpOn)
                        continue;

                float sL = bInL.at (grp);
                float sR = bInR.at (grp);

                // pre-filter drive
                float sDryL = sL;
                float sDryR = sR;
""")
rep("""                if (ft < 4) yL = filterStep (i, 0, sL, g, k, ft);
                else        yL = filterStepX (i, 0, 0, sL, g, k, resEff, fc, ft);""",
    """                yL = filterStepX (i, 0, grp * 2, sL, g, k, resEff, fc, ft);""")
rep("""                    if (ft < 4) yR = filterStep (i, 1, sR, g, k, ft);
                    else        yR = filterStepX (i, 1, 0, sR, g, k, resEff, fc, ft);""",
    """                    yR = filterStepX (i, 1, grp * 2, sR, g, k, resEff, fc, ft);""")
rep("""                    if (ft >= 4)
                    {
                        for (int fq = 0; fq < 16; ++fq)
                            voices.at (i).fx.at (16 + fq) = voices.at (i).fx.at (fq);
                    }
""", """                    for (int fq = 0; fq < 16; ++fq)
                        voices.at (i).fx.at (grp * 64 + 16 + fq) = voices.at (i).fx.at (grp * 64 + fq);
""")
rep("""                    voices.at (i).ic1c = voices.at (i).ic1a;
                    voices.at (i).ic2c = voices.at (i).ic2a;
                    voices.at (i).ic1d = voices.at (i).ic1b;
                    voices.at (i).ic2d = voices.at (i).ic2b;
""", "")
rep("float zL = filterStepX (i, 0, 1, inL, g2, k2, res2, fc2, ft2);", "float zL = filterStepX (i, 0, grp * 2 + 1, inL, g2, k2, res2, fc2, ft2);")
rep("zR = filterStepX (i, 1, 1, inR, g2, k2, res2, fc2, ft2);", "zR = filterStepX (i, 1, grp * 2 + 1, inR, g2, k2, res2, fc2, ft2);")
rep("voices.at (i).fx.at (48 + fq) = voices.at (i).fx.at (32 + fq);", "voices.at (i).fx.at (grp * 64 + 48 + fq) = voices.at (i).fx.at (grp * 64 + 32 + fq);")
rep("""                voices.at (i).fdlW = (voices.at (i).fdlW + 1) & 2047;

                float a = e * voices.at (i).velGain * (1.0f - lfoAmp * (0.5f - 0.5f * lfo)) * clamp (1.0f + vmod.at (4), 0.0f, 2.0f);
                float dryMono = smpDry + smpDry2;
                mixSynthL += (yL + dryMono + wtDryL + wt2DryL + wt3DryL) * a;
                mixSynthR += (yR + dryMono + wtDryR + wt2DryR + wt3DryR) * a;
""", """                gOutL.at (grp) = yL;
                gOutR.at (grp) = yR;
                }

                voices.at (i).fdlW = (voices.at (i).fdlW + 1) & 2047;

                for (int mg = 0; mg < 3; ++mg)
                {
                    mixSynthL.at (mg) += (gOutL.at (mg) + bDryL.at (mg)) * a;
                    mixSynthR.at (mg) += (gOutR.at (mg) + bDryR.at (mg)) * a;
                }
""")
rep("""            float mixSynthL = 0.0f;
            float mixSynthR = 0.0f;""", """            float[3] mixSynthL;
            float[3] mixSynthR;""")

# --- after the voices: drive, pan and DC blocker per bus, the two bus racks, then everything into the Main rack
a0 = src.index("            // ----- synth drive / soft clip -----")
b0 = src.index("            // ----- stereo width (mid/side) -----")
assert a0 < b0
src = (src[:a0] + """            // ----- synth drive / soft clip, pan and DC blocker, once per bus -----
            float synDcA = 1.0f - clamp (float (twoPi) * 5.0f * dt, 0.0001f, 0.5f);
            float[3] busInL;
            float[3] busInR;

            for (int bg = 0; bg < 3; ++bg)
            {
                float rawL = shapeSig (mixSynthL.at (bg) * 0.35f, driveEff) * gPanL;
                float rawR = shapeSig (mixSynthR.at (bg) * 0.35f, driveEff) * gPanR;

                // always-on DC blocker (about 5 Hz): asymmetric shapers, ring mod and loaded samples can carry DC
                // that the delay / chorus / flanger / reverb feedback loops would amplify
                float dcL = rawL - busDcX.at (bg * 2)     + synDcA * busDcY.at (bg * 2);
                float dcR = rawR - busDcX.at (bg * 2 + 1) + synDcA * busDcY.at (bg * 2 + 1);
                busDcX.at (bg * 2)     = rawL;
                busDcY.at (bg * 2)     = dcL;
                busDcX.at (bg * 2 + 1) = rawR;
                busDcY.at (bg * 2 + 1) = dcR;
                busInL.at (bg) = dcL * masterLevel;
                busInR.at (bg) = dcR * masterLevel;
            }

            // ----- FX racks: Bus 1 and Bus 2 feed the Main rack, which feeds the output -----
            float<2> bus1 = fxRunRack (1, float<2> (busInL.at (1), busInR.at (1))) * busLevel1;
            float<2> bus2 = fxRunRack (2, float<2> (busInL.at (2), busInR.at (2))) * busLevel2;
            float<2> rack = fxRunRack (0, float<2> (busInL.at (0) + bus1[0] + bus2[0], busInR.at (0) + bus1[1] + bus2[1]));
            float outL = rack[0];
            float outR = rack[1];

""" + src[b0:])
# the shaper and pan variables used above are computed before this block: keep them, drop the old scalar shaper lines (they were inside a0..b0)

a = src.index("            // ----- sample rate reduction -----")
b = src.index("            outL = clamp (outL, -1.0f, 1.0f);")
assert a < b
src = src[:a] + src[b:]

path.write_text(src, encoding="utf-8")
print("patched", path, "- removed", removed_decl, "params,", removed_handler, "handlers,", n_state, "state vars")
