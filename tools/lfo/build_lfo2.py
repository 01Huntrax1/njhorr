#!/usr/bin/env python3
"""LFO rework, stage 2 (DSP), patch/Eisenpuls_Synth.cmajor.  Idempotent.  Usage: build_lfo2.py [patch.cmajor]
 * Key follow: the LFO runs per voice at note frequency * Ratio * Fine (audio rate, up to 16 x), also with Mode Free
 * Wave 7 = Wavetable LFO: Position scans the frames Sine, Triangle, Saw, Square, Drawn
 * Skew (phase bend), Steps (quantizer), Jitter (random rate per cycle), Voice Spread (start phase per voice), Depth
 * Interp: linear or cubic read of the drawn shape; saw / square get polyBLEP at audio rate
 * parameters: ids LFO2_BASE (13000) + 16 * lfo + j"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
BASE, STRIDE = 13000, 16
# j, key, array, label, short, min, max, init, unit, kind, labels
L2 = [
 (0, "key",    "mLfoKey",    "Key Follow", "Key",    0, 1,   0.0, "",   "btn", ["Key Off", "Key On"]),
 (1, "ratio",  "mLfoRatio",  "Key Ratio",  "Ratio",  0.25, 16, 1.0, "x", "sld", None),
 (2, "fine",   "mLfoFine",   "Key Fine",   "Fine",   -100, 100, 0.0, "ct", "sld", None),
 (3, "skew",   "mLfoSkew",   "Skew",       "Skew",   -1, 1,  0.0, "",   "sld", None),
 (4, "steps",  "mLfoSteps",  "Steps",      "Steps",  0, 32,  0.0, "",   "sel", None),
 (5, "jitter", "mLfoJit",    "Jitter",     "Jitter", 0, 1,   0.0, "",   "sld", None),
 (6, "spread", "mLfoSpread", "Voice Spread","Spread",0, 1,   0.0, "",   "sld", None),
 (7, "depth",  "mLfoDepth",  "Depth",      "Depth",  0, 1,   1.0, "",   "sld", None),
 (8, "tpos",   "mLfoTpos",   "Table Pos",  "Pos",    0, 1,   0.0, "",   "sld", None),
 (9, "interp", "mLfoCubic",  "Interp",     "Interp", 0, 1,   1.0, "",   "btn", ["Linear", "Cubic"]),
]
def lid(i, j): return BASE + STRIDE * i + j

CODE = r'''    // LFO2-BEGIN
    // Reads the drawn shape of LFO m at phase p (0..1); looping shapes interpolate from the last point back to the first (linear or cubic)
    float lfoTabRead (int m, float p, bool wrapEnd)
    {
        float pos = clamp (p, 0.0f, 1.0f) * 256.0f;
        int   i0  = int (pos);
        float fr  = pos - float (i0);

        if (i0 > 255)
        {
            i0 = 255;
            fr = 0.0f;
        }

        int i1 = i0 + 1;
        int im = i0 - 1;
        int i2 = i0 + 2;

        if (wrapEnd)
        {
            i1 = i1 & 255;
            im = im & 255;
            i2 = i2 & 255;
        }
        else
        {
            i1 = min (i1, 255);
            im = max (im, 0);
            i2 = min (i2, 255);
        }

        float y0 = lfoTab.at (m * 256 + i0);
        float y1 = lfoTab.at (m * 256 + i1);

        if (mLfoCubic.at (m) < 0.5f)
            return y0 + (y1 - y0) * fr;

        float ym = lfoTab.at (m * 256 + im);
        float y2 = lfoTab.at (m * 256 + i2);
        return clamp (y0 + 0.5f * fr * (y1 - ym + fr * (2.0f * ym - 5.0f * y0 + 4.0f * y1 - y2 + fr * (3.0f * (y0 - y1) + y2 - ym))), -1.0f, 1.0f);
    }

    float lfoFrac (float x)
    {
        return x - float (floor (x));
    }

    // polyBLEP residual for a discontinuity at phase 0 (p = phase, dp = phase increment per sample)
    float lfoBlep (float p, float dp)
    {
        if (dp <= 0.0f || dp >= 0.5f)
            return 0.0f;

        if (p < dp)
        {
            float t = p / dp;
            return t + t - t * t - 1.0f;
        }

        if (p > 1.0f - dp)
        {
            float t = (p - 1.0f) / dp;
            return t * t + t + t + 1.0f;
        }

        return 0.0f;
    }

    // the basic shapes: 0 sine, 1 triangle, 2 square, 3 S&H, 4 saw up, 5 saw down, 6 drawn
    float lfoBasic (int w, int m, float p, float sh, bool wrapEnd, float dp)
    {
        if (w == 0)
            return float (sin (float (twoPi) * p));
        if (w == 1)
            return 4.0f * abs (p - 0.5f) - 1.0f;
        if (w == 2)
        {
            float q = p + 0.5f;
            if (q >= 1.0f) q -= 1.0f;
            float y = 1.0f;
            if (p >= 0.5f) y = -1.0f;
            return y + lfoBlep (p, dp) - lfoBlep (q, dp);
        }
        if (w == 3)
            return sh;
        if (w == 4)
            return 2.0f * p - 1.0f - lfoBlep (p, dp);
        if (w == 5)
            return 1.0f - 2.0f * p + lfoBlep (p, dp);

        return lfoTabRead (m, p, wrapEnd);
    }

    // Output of LFO m at phase p; wave 7 = wavetable (Position scans sine, triangle, saw, square, drawn)
    float lfoWaveVal (int m, float p, float sh, bool wrapEnd, float dp)
    {
        int w = int (mLfoWave.at (m) + 0.5f);

        if (w == 7)
        {
            float fp = clamp (mLfoTpos.at (m), 0.0f, 1.0f) * 4.0f;
            int   fa = min (int (fp), 3);
            float ff = fp - float (fa);
            int   wa = 0;
            int   wb = 1;

            if (fa == 1) { wa = 1; wb = 4; }
            if (fa == 2) { wa = 4; wb = 2; }
            if (fa == 3) { wa = 2; wb = 6; }

            float a = lfoBasic (wa, m, p, sh, wrapEnd, dp);
            return a + (lfoBasic (wb, m, p, sh, wrapEnd, dp) - a) * ff;
        }

        return lfoBasic (w, m, p, sh, wrapEnd, dp);
    }

    // phase bend (Skew), quantizer (Steps) and Depth of LFO m applied to the raw value
    float lfoSkewPhase (int m, float p)
    {
        float s = mLfoSkew.at (m);

        if (s > -0.001f && s < 0.001f)
            return p;

        return float (pow (clamp (p, 0.0f, 1.0f), float (pow (2.0f, s * 2.0f))));
    }

    float lfoShape (int m, float v)
    {
        float n = mLfoSteps.at (m);

        if (n >= 1.5f)
        {
            float q = float (floor ((v * 0.5f + 0.5f) * n - 0.0001f));
            v = clamp (q, 0.0f, n - 1.0f) / (n - 1.0f) * 2.0f - 1.0f;
        }

        return v * mLfoDepth.at (m);
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

    // true when LFO m runs per voice (Trig / Env or Key follow)
    bool lfoPerVoice (int m)
    {
        return mLfoMode.at (m) > 0.5f || mLfoKey.at (m) > 0.5f;
    }

    // Free-running (global) LFOs: advances all 10 by one sample
    void updateModLfos (float dtv)
    {
        for (int m = 0; m < 10; ++m)
        {
            if (mLfoKey.at (m) > 0.5f)
                continue;

            float rate = lfoRateHz (m) * (1.0f + mLfoJit.at (m) * 0.5f * mLfoJ.at (m));
            float64 np = mLfoPhase.at (m) + float64 (rate) * processor.period;
            if (np >= 1.0)
            {
                np -= 1.0;
                mLfoSh.at (m) = nextNoise();
                mLfoJ.at (m)  = nextNoise();
            }
            mLfoPhase.at (m) = np;

            float p = float (np) + mLfoStart.at (m);
            if (p >= 1.0f) p -= 1.0f;

            float val = lfoShape (m, lfoWaveVal (m, lfoSkewPhase (m, p), mLfoSh.at (m), true, rate * float (processor.period)));
            mLfoSm.at (m) = lfoLag (mLfoSm.at (m), val, mLfoSmooth.at (m), dtv);
            mLfoV.at (m)  = mLfoSm.at (m);
        }
    }

    // Per-voice LFOs (Trig, Env, Key follow): phase restarts on note-on, Delay / Rise fade the output in, Env stops at the end of the shape
    void updateVoiceLfos (int vi, float dtv)
    {
        for (int m = 0; m < 10; ++m)
        {
            if (! lfoPerVoice (m))
                continue;

            bool    oneShot = mLfoMode.at (m) > 1.5f;
            bool    keyed   = mLfoKey.at (m) > 0.5f;
            float   age     = voices.at (vi).lfoAge.at (m);
            bool    first   = age < 0.0f;
            float64 np      = voices.at (vi).lfoPh.at (m);
            float   rate    = lfoRateHz (m);

            if (keyed)
                rate = clamp (voices.at (vi).curFreq * mLfoRatio.at (m) * float (pow (2.0f, mLfoFine.at (m) / 1200.0f)), 0.001f, float (processor.frequency) * 0.45f);

            rate *= 1.0f + mLfoJit.at (m) * 0.5f * voices.at (vi).lfoJ.at (m);

            if (first)
            {
                age = 0.0f;
                np  = float64 (mLfoSpread.at (m) * lfoFrac (float (vi) * 0.618034f + 0.137f));
            }
            else
            {
                age += dtv;
                np  += float64 (rate) * processor.period;

                if (np >= 1.0)
                {
                    if (oneShot)
                        np = 1.0;
                    else
                    {
                        np -= 1.0;
                        voices.at (vi).lfoSh.at (m) = nextNoise();
                        voices.at (vi).lfoJ.at (m)  = nextNoise();
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

            float val  = lfoShape (m, lfoWaveVal (m, lfoSkewPhase (m, p), voices.at (vi).lfoSh.at (m), ! oneShot, rate * float (processor.period)));
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
    // LFO2-END

'''

s = open(PATCH).read()
def rep(old, new, cnt=1):
    global s
    if new in s: return
    assert s.count(old) == cnt, (old[:80], s.count(old))
    s = s.replace(old, new)
def block(t, body, anchor_re, indent="    "):
    global s
    a, z = "%s// LFO2-%s-BEGIN\n" % (indent, t), "%s// LFO2-%s-END\n" % (indent, t)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + t)
    s = s[:m.start()] + a + body + z + s[m.start():]

# DSP functions: replace lfoTabRead .. updateVoiceLfos (first time) or the marked region
if "// LFO2-BEGIN" in s:
    s = re.sub(r"    // LFO2-BEGIN\n.*?    // LFO2-END\n\n", lambda m: CODE, s, flags=re.S)
else:
    a = s.index("    // Reads the drawn shape of LFO m at phase p")
    b = s.index("    // Moves the per-sample maxima of each mod envelope")
    s = s[:a] + CODE + s[b:]
# state
rep("    float[16]   mLfoSm;       // smoothing state of the free-running (global) LFOs\n",
    "    float[16]   mLfoSm;       // smoothing state of the free-running (global) LFOs\n    float[16]   mLfoJ;        // LFO2: jitter draw of the current cycle (global LFOs)\n" +
    "".join("    float[16]   %s;\n" % a for a in sorted({q[2] for q in L2})))
rep("        float[16] lfoSm;      // per-voice smoothing state\n", "        float[16] lfoSm;      // per-voice smoothing state\n        float[16] lfoJ;       // LFO2: per-voice jitter draw\n")
rep("            voices.at (v).lfoSh.at (lm)  = nextNoise();\n", "            voices.at (v).lfoSh.at (lm)  = nextNoise();\n            voices.at (v).lfoJ.at (lm)   = nextNoise();\n")
# routing: per-voice when Trig / Env / Key
rep("            if (mLfoMode.at (src - 1) > 0.5f)\n                return lfoPol (voices.at (vi)", "            if (lfoPerVoice (src - 1))\n                return lfoPol (voices.at (vi)")
rep("            if (mLfoMode.at (src - 1) > 0.5f)\n                return lfoPol (voices.at (lastVoice)", "            if (lfoPerVoice (src - 1))\n                return lfoPol (voices.at (lastVoice)")
# wave range 0..7
s = re.sub(r'(name: "Mod LFO \d+ Wave \(Sin/Tri/Sq/S&H/SawUp/SawDn/Drawn)\)",(\s+)min: 0\.0, max: 6\.0', r'\1/Table)",\2min: 0.0, max: 7.0', s)
# parameters
decl = "".join('    input event float param%d [[ name: "LFO %d %s", min: %s, max: %s, init: %s%s ]];\n' % (lid(i, q[0]), i + 1, q[3], repr(float(q[5])), repr(float(q[6])), repr(float(q[7])), ", step: 1.0" if q[9] in ("sel", "btn") else "") for i in range(10) for q in L2)
hand = "".join("    event param%d (float v) { %s.at (%d) = v; }\n" % (lid(i, q[0]), q[2], i) for i in range(10) for q in L2)
init = "".join("            %s.at (il) = %sf;\n" % (a, repr(float(v))) for a, v in sorted({(q[2], q[7]) for q in L2}))
block("DECL", decl, r"^    input event float param1600 ")
block("HAND", hand, r"^    event param1600 ")
block("INIT", "        for (int il = 0; il < 10; ++il)\n        {\n" + init + "        }\n", r"^        fxGateInit\(\);\n", "        ")
open(PATCH, "w").write(s)
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoLfo2.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/lfo/build_lfo2.py: parameter ids of the LFO extras\n#pragma once\n#include <string_view>\nnamespace njo::lfo2\n{\n")
    f.write("    constexpr int BASE = %d, STRIDE = %d;\n    inline int lfoId (int i, int j) { return BASE + STRIDE * i + j; }\n" % (BASE, STRIDE))
    f.write("    inline int key (const char* name)\n    {\n")
    for q in L2: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n}\n")
print("ok")
