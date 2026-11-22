#!/usr/bin/env python3
"""LFO CPU: values that only depend on parameters are cached instead of recomputed per voice and sample (bit-identical).  Idempotent.
 * Key follow ratio  pow (2, oct / semi / fine)   (per LFO, was a pow per voice and sample)
 * Skew exponent     pow (2, skew * 2)
 * Smoothing factor  1 - exp (-dt / (0.0002 + smooth * 0.25))
python3 tools/lfo/build_lfofast.py [patch.cmajor]"""
import os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "patch", "Eisenpuls_Synth.cmajor"); s = open(P).read()
if "LFOFAST-BEGIN" in s: print("already patched"); raise SystemExit
def rep(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a)); s = s.replace(a, b)
rep("    float lfoLag (float state, float x, float smooth, float dtv)\n", '''    // LFOFAST-BEGIN: parameter dependent values are computed when the parameters change, not for every voice and sample
    float[16] lfoKmArg;
    float[16] lfoKmVal;
    int[16]   lfoKmOk;
    float[16] lfoSkArg;
    float[16] lfoSkVal;
    int[16]   lfoSkOk;
    float[16] lfoLgS;
    float[16] lfoLgD;
    float[16] lfoLgK;
    int[16]   lfoLgOk;

    float lfoKeyMul (int m)
    {
        float a = mLfoOct.at (m) - 4.0f + (mLfoSemi.at (m) - 12.0f) / 12.0f + mLfoFine.at (m) / 1200.0f;

        if (lfoKmOk.at (m) == 0 || a != lfoKmArg.at (m))
        {
            lfoKmArg.at (m) = a;
            lfoKmVal.at (m) = float (pow (2.0f, a));
            lfoKmOk.at (m)  = 1;
        }

        return lfoKmVal.at (m);
    }

    float lfoSkewExp (int m, float s)
    {
        if (lfoSkOk.at (m) == 0 || s != lfoSkArg.at (m))
        {
            lfoSkArg.at (m) = s;
            lfoSkVal.at (m) = float (pow (2.0f, s * 2.0f));
            lfoSkOk.at (m)  = 1;
        }

        return lfoSkVal.at (m);
    }

    float lfoLagM (int m, float state, float x, float smooth, float dtv)
    {
        if (smooth <= 0.001f)
            return x;

        if (lfoLgOk.at (m) == 0 || smooth != lfoLgS.at (m) || dtv != lfoLgD.at (m))
        {
            lfoLgS.at (m)  = smooth;
            lfoLgD.at (m)  = dtv;
            lfoLgK.at (m)  = 1.0f - float (exp (-dtv / (0.0002f + smooth * 0.25f)));
            lfoLgOk.at (m) = 1;
        }

        return state + (x - state) * lfoLgK.at (m);
    }
    // LFOFAST-END

    float lfoLag (float state, float x, float smooth, float dtv)
''')
rep("        return float (pow (clamp (p, 0.0f, 1.0f), float (pow (2.0f, s * 2.0f))));", "        return float (pow (clamp (p, 0.0f, 1.0f), lfoSkewExp (m, s)));")
rep("mLfoSm.at (m) = lfoLag (mLfoSm.at (m), val, mLfoSmooth.at (m), dtv);", "mLfoSm.at (m) = lfoLagM (m, mLfoSm.at (m), val, mLfoSmooth.at (m), dtv);")
rep("st = lfoLag (st, val, mLfoSmooth.at (m), dtv);", "st = lfoLagM (m, st, val, mLfoSmooth.at (m), dtv);")
rep("float (pow (2.0f, mLfoOct.at (m) - 4.0f + (mLfoSemi.at (m) - 12.0f) / 12.0f + mLfoFine.at (m) / 1200.0f))", "lfoKeyMul (m)")
open(P, "w").write(s); print("patched")
