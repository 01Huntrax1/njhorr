#!/usr/bin/env python3
"""Reworks the 10 mod LFOs of patch/Eisenpuls_Synth.cmajor (applied once, asserts on every edit):

  * drawn shapes: every LFO reads a 256-point table (event endpoint lfoShapeLoad); wave 6 = "Drawn", waves 0-5 stay the built-in shapes
  * trigger modes: Free (global, as before), Trig (own phase per voice, restarted on note-on), Env (one-shot per voice, holds its last value)
  * Delay / Rise (fade-in after the delay, Trig and Env modes), Smooth (one-pole lag), start Phase
  * parameters per LFO i (0-9): 882 + 5 i  Mode, Delay, Rise, Smooth, Phase

    python3 tools/lfo/apply_lfo_patch.py patch/Eisenpuls_Synth.cmajor
"""
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
src = path.read_text(encoding="utf-8")
assert "lfoShapeLoad" not in src, "already patched"


def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:90])
    src = src.replace(old, new)


# ---------------------------------------------------------------- endpoint + struct
rep("    // Dedicated loader for the synth sample oscillator (loads into the selected Synth Sample Memory)\n",
    "    // Drawn LFO shapes: one 256-point table per LFO (-1..1)\n    input event LfoShapeChunk lfoShapeLoad;\n\n"
    "    // Dedicated loader for the synth sample oscillator (loads into the selected Synth Sample Memory)\n")
rep("    struct SynthSampleChunk\n", "    struct LfoShapeChunk\n    {\n        int        lfo;\n        float[256] data;\n    }\n\n    struct SynthSampleChunk\n")

# ---------------------------------------------------------------- parameters
n_wave = len(re.findall(r'(name: "Mod LFO \d+ Wave \(Sin/Tri/Sq/S&H/SawUp/SawDn)\)",  ?min: 0\.0, max: 5\.0', src))
assert n_wave == 10, n_wave
src = re.sub(r'(name: "Mod LFO \d+ Wave \(Sin/Tri/Sq/S&H/SawUp/SawDn)\)",(\s+)min: 0\.0, max: 5\.0',
             r'\1/Drawn)",\2min: 0.0, max: 6.0', src)

pd, ph = [], []
for i in range(10):
    b = 882 + 5 * i
    n = i + 1
    pd.append(f'    input event float param{b}    [[ name: "LFO {n} Mode (Free/Trig/Env)", min: 0.0, max: 2.0, init: 0.0, step: 1.0 ]];')
    pd.append(f'    input event float param{b + 1}    [[ name: "LFO {n} Delay", min: 0.0, max: 5000.0, init: 0.0, unit: "ms" ]];')
    pd.append(f'    input event float param{b + 2}    [[ name: "LFO {n} Rise",  min: 0.0, max: 5000.0, init: 0.0, unit: "ms" ]];')
    pd.append(f'    input event float param{b + 3}    [[ name: "LFO {n} Smooth", min: 0.0, max: 1.0, init: 0.0 ]];')
    pd.append(f'    input event float param{b + 4}    [[ name: "LFO {n} Phase", min: 0.0, max: 1.0, init: 0.0 ]];')
    ph.append(f"    event param{b}    (float v) {{ mLfoMode.at ({i}) = v; }}")
    ph.append(f"    event param{b + 1}    (float v) {{ mLfoDelay.at ({i}) = v; }}")
    ph.append(f"    event param{b + 2}    (float v) {{ mLfoRise.at ({i}) = v; }}")
    ph.append(f"    event param{b + 3}    (float v) {{ mLfoSmooth.at ({i}) = v; }}")
    ph.append(f"    event param{b + 4}    (float v) {{ mLfoStart.at ({i}) = v; }}")

m = re.search(r"^\s*input event float param881 .*$", src, re.M)
assert m
src = src[:m.end()] + "\n" + "\n".join(pd) + src[m.end():]
m = re.search(r"^\s*event param881 .*$", src, re.M)
assert m
src = src[:m.end()] + "\n\n    // LFO rework handlers\n" + "\n".join(ph) + "\n" + """
    event lfoShapeLoad (LfoShapeChunk c)
    {
        int m = clamp (c.lfo, 0, 9);

        for (int i = 0; i < 256; ++i)
            lfoTab.at (m * 256 + i) = clamp (c.data.at (i), -1.0f, 1.0f);
    }
""" + src[m.end():]

# ---------------------------------------------------------------- state
rep("    float[10]   mLfoV;\n", """    float[10]   mLfoV;
    float[10]   mLfoMode;     // 0 free (global), 1 trig (per voice, restarts on note-on), 2 env (per voice, one shot)
    float[10]   mLfoDelay;
    float[10]   mLfoRise;
    float[10]   mLfoSmooth;
    float[10]   mLfoStart;
    float[10]   mLfoSm;       // smoothing state of the free-running (global) LFOs
    float[2560] lfoTab;       // drawn shapes, 256 points per LFO
    int         lastVoice = 0;
""")
rep("        float[10] menv;       // mod envelope levels\n", """        float[10] menv;       // mod envelope levels
        float64[10] lfoPh;    // per-voice LFO phases (modes Trig / Env)
        float[10] lfoV;       // per-voice LFO outputs
        float[10] lfoAge;     // seconds since note-on, -1 before the first update
        float[10] lfoSh;      // per-voice sample & hold values
        float[10] lfoSm;      // per-voice smoothing state
""")

# ---------------------------------------------------------------- engine
a = src.index("    void updateModLfos (float dtv)")
b = src.index("    // Moves the per-sample maxima of each mod envelope")
new_engine = '''    // Reads the drawn shape of LFO m at phase p (0..1); looping shapes interpolate from the last point back to the first
    float lfoTabRead (int m, float p, bool wrapEnd)
    {
        float pos = clamp (p, 0.0f, 1.0f) * 256.0f;
        int   i0  = int (pos);
        float fr  = pos - float (i0);
        int   i1  = i0 + 1;

        if (i0 > 255)
        {
            i0 = 255;
            fr = 0.0f;
        }

        if (i1 > 255)
        {
            if (wrapEnd) i1 = 0;
            else      i1 = 255;
        }

        return lfoTab.at (m * 256 + i0) * (1.0f - fr) + lfoTab.at (m * 256 + i1) * fr;
    }

    // Output of LFO m at phase p: waves 0-5 are the built-in shapes, 6 is the drawn table
    float lfoWaveVal (int m, float p, float sh, bool wrapEnd)
    {
        int w = int (mLfoWave.at (m) + 0.5f);

        if (w == 0)
            return float (sin (float (twoPi) * p));
        if (w == 1)
            return 4.0f * abs (p - 0.5f) - 1.0f;
        if (w == 2)
        {
            if (p < 0.5f) return 1.0f;
            return -1.0f;
        }
        if (w == 3)
            return sh;
        if (w == 4)
            return 2.0f * p - 1.0f;
        if (w == 5)
            return 1.0f - 2.0f * p;

        return lfoTabRead (m, p, wrapEnd);
    }

    // one-pole lag of the Smooth control (0 = off, 1 = about 250 ms)
    float lfoLag (float state, float x, float smooth, float dtv)
    {
        if (smooth <= 0.001f)
            return x;

        return state + (x - state) * (1.0f - float (exp (-dtv / (0.0002f + smooth * 0.25f))));
    }

    float lfoRateHz (int m)
    {
        if (mLfoSync.at (m) > 0.5f)
            return syncHz (mLfoDiv.at (m));

        return mLfoRate.at (m);
    }

    // Free-running (global) LFOs: advances all 10 by one sample
    void updateModLfos (float dtv)
    {
        for (int m = 0; m < 10; ++m)
        {
            float64 np = mLfoPhase.at (m) + float64 (lfoRateHz (m)) * processor.period;
            if (np >= 1.0)
            {
                np -= 1.0;
                mLfoSh.at (m) = nextNoise();
            }
            mLfoPhase.at (m) = np;

            float p = float (np) + mLfoStart.at (m);
            if (p >= 1.0f) p -= 1.0f;

            float val = lfoWaveVal (m, p, mLfoSh.at (m), true);
            mLfoSm.at (m) = lfoLag (mLfoSm.at (m), val, mLfoSmooth.at (m), dtv);
            mLfoV.at (m)  = mLfoSm.at (m);
        }
    }

    // Per-voice LFOs (modes Trig and Env): phase restarts on note-on, Delay / Rise fade the output in, Env stops at the end of the shape
    void updateVoiceLfos (int vi, float dtv)
    {
        for (int m = 0; m < 10; ++m)
        {
            float mode = mLfoMode.at (m);
            if (mode < 0.5f)
                continue;

            bool    oneShot = mode > 1.5f;
            float   age     = voices.at (vi).lfoAge.at (m);
            bool    first   = age < 0.0f;
            float64 np      = voices.at (vi).lfoPh.at (m);

            if (first)
                age = 0.0f;
            else
            {
                age += dtv;
                np  += float64 (lfoRateHz (m)) * processor.period;

                if (np >= 1.0)
                {
                    if (oneShot)
                        np = 1.0;
                    else
                    {
                        np -= 1.0;
                        voices.at (vi).lfoSh.at (m) = nextNoise();
                    }
                }
            }

            voices.at (vi).lfoPh.at (m)  = np;
            voices.at (vi).lfoAge.at (m) = age;

            float p = float (np);
            if (! oneShot)
            {
                p += mLfoStart.at (m);
                if (p >= 1.0f) p -= 1.0f;
            }

            float val  = lfoWaveVal (m, p, voices.at (vi).lfoSh.at (m), ! oneShot);
            float fade = 1.0f;
            float dl   = mLfoDelay.at (m) * 0.001f;
            float rs   = mLfoRise.at (m) * 0.001f;

            if (age < dl)
                fade = 0.0f;
            else if (rs > 0.0001f)
                fade = clamp ((age - dl) / rs, 0.0f, 1.0f);

            val *= fade;

            float st = voices.at (vi).lfoSm.at (m);
            if (first)
                st = val;

            st = lfoLag (st, val, mLfoSmooth.at (m), dtv);
            voices.at (vi).lfoSm.at (m) = st;
            voices.at (vi).lfoV.at (m)  = st;
        }
    }

'''
src = src[:a] + new_engine + src[b:]

rep('''        if (src >= 1 && src <= 10)
            return mLfoV.at (src - 1);
        if (src >= 11 && src <= 20)
            return voices.at (vi).menv.at (src - 11);''', '''        if (src >= 1 && src <= 10)
        {
            if (mLfoMode.at (src - 1) > 0.5f)
                return voices.at (vi).lfoV.at (src - 1);
            return mLfoV.at (src - 1);
        }
        if (src >= 11 && src <= 20)
            return voices.at (vi).menv.at (src - 11);''')
rep('''        if (src >= 1 && src <= 10)
            return mLfoV.at (src - 1);
        if (src >= 11 && src <= 20)
            return envMax.at (src - 11);''', '''        if (src >= 1 && src <= 10)
        {
            if (mLfoMode.at (src - 1) > 0.5f)
                return voices.at (lastVoice).lfoV.at (src - 1);
            return mLfoV.at (src - 1);
        }
        if (src >= 11 && src <= 20)
            return envMax.at (src - 11);''')

# note-on: restart the per-voice LFOs
rep('''            voices.at (v).modRand = nextNoise();
            lastVelV  = vel;''', '''            voices.at (v).modRand = nextNoise();
            lastVoice = v;

            for (int lm = 0; lm < 10; ++lm)
            {
                voices.at (v).lfoPh.at (lm)  = 0.0;
                voices.at (v).lfoAge.at (lm) = -1.0f;
                voices.at (v).lfoSh.at (lm)  = nextNoise();
                voices.at (v).lfoV.at (lm)   = 0.0f;
            }

            lastVelV  = vel;''')
rep('''                updateModEnvs (i, dt);
                computeVoiceMod (i);''', '''                updateModEnvs (i, dt);
                updateVoiceLfos (i, dt);
                computeVoiceMod (i);''')

# default shape: sine
m = re.search(r"(        fxInit\(\);\n)", src)
assert m
src = src[:m.end()] + '''
        for (int lm = 0; lm < 10; ++lm)
            for (int li = 0; li < 256; ++li)
                lfoTab.at (lm * 256 + li) = float (sin (float (twoPi) * float (li) / 256.0f));
''' + src[m.end():]

path.write_text(src, encoding="utf-8")
print("patched", path)
