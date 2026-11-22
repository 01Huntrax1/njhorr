#!/usr/bin/env python3
"""Wavetable oscillator fast path (bit-identical audio).  Idempotent.  python3 tools/osc/build_wtfast.py
wtStep: when no phase / amplitude warp, no phase modulation, no unison drift and a single mip level for all unison voices, a tight loop runs
(mip level, bases, masks, the sample period and the frame crossfade are hoisted out of the per-unison-voice loop); everything else uses the general loop."""
import os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "patch", "Eisenpuls_Synth.cmajor"); s = open(P).read()
if "WTFAST-BEGIN" in s: print("already patched"); raise SystemExit
a = "        float udr = clamp (opv (o, 28), 0.0f, 1.0f) * 0.007f;\n\n        for (int j = 0; j < n; ++j)\n"
assert s.count(a) == 1
fast = '''        float udr = clamp (opv (o, 28), 0.0f, 1.0f) * 0.007f;

        // WTFAST-BEGIN
        int fastN = 0;
        bool two  = ! (fb == fa || ff <= 0.0f);

        if (lvlAll >= 0 && pm == 0.0f && m1 == 0 && m2 == 0 && m3 == 0 && udr <= 0.0f && (eco || fmode != 1 || ! two))
        {
            int     lvF   = lvlAll;
            if (lvBias > 0) lvF = min (lvF + lvBias, 8);
            int     len   = 2048 >> lvF;
            int     off   = 4096 - (4096 >> lvF);
            float   flen  = float (len);
            int     baseA = (o * 256 + fa) * 4096 + off;
            int     baseB = (o * 256 + fb) * 4096 + off;
            float   fmax  = sr * 0.45f;
            float64 per   = processor.period;

            for (int j = 0; j < n; ++j)
            {
                int     si = o * 16 + j;
                float64 ph = voices.at (vi).wtUPh.at (si);
                float   f  = clamp (freq * uniRatio.at (si), 1.0f, fmax);
                float   x  = clamp (float (ph), 0.0f, 0.99999f) * flen;
                float   y;

                if (eco)
                {
                    y = wtMipReadLin (baseA, len, x);
                    if (two) y = y + (wtMipReadLin (baseB, len, x) - y) * ff;
                }
                else
                {
                    y = wtMipRead (baseA, len, x);
                    if (two) y = y + (wtMipRead (baseB, len, x) - y) * ff;
                }

                sL += y * uniGL.at (si);
                sR += y * uniGR.at (si);

                ph += float64 (f) * per;
                if (ph >= 1.0) ph -= 1.0;
                voices.at (vi).wtUPh.at (si) = ph;
            }

            fastN = n;
        }
        // WTFAST-END

        for (int j = fastN; j < n; ++j)
'''
s = s.replace(a, fast); open(P, "w").write(s); print("patched")
