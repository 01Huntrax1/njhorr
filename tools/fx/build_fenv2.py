#!/usr/bin/env python3
"""Idempotent, marker FX-FENV2: improved Filter effect (type 9).
* The envelope no longer has its own Attack / Decay / Sustain / Release: it takes the times and the sustain level of one of the modulation envelopes
  (ENV 1-10, parameter P5 "Env Src" = 0..1 -> ENV 1..10) and runs them exactly like that modulator (linear attack, exponential decay / release).
  The gate is still "any note held".  The extra parameters 3000+g / 3030+g (old Sustain / Release) stay declared but are unused.
* P6 is now Key Track: the cutoff follows the last played note (+-4 octaves over the key range at 100 %).
* The cutoff is smoothed (about 5 ms) when it jumps (automation, key track), instead of stepping."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'FX-FENV2' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)

rep('    float[32]     fxEnvGc;\n', '    float[32]     fxEnvGc;\n    float[32]     fxFcS;     // FX-FENV2: smoothed cutoff (Hz) of the filter effect\n')
rep('        for (int i = 0; i < 40; ++i)\n            fxF.at (s * 40 + i) = 0.0f;\n', '        for (int i = 0; i < 40; ++i)\n            fxF.at (s * 40 + i) = 0.0f;\n\n        fxFcS.at (s) = 0.0f;   // FX-FENV2\n')

# derive
i = src.index('            // FX-FENV: envelope on the cutoff: amount')
j = src.index('        else if (ty == 10)', i)
src = src[:i] + '''            // FX-FENV2: envelope amount (+-1 = +-7 octaves), the modulation envelope that supplies the times (0..9), key tracking amount
            fxD.at (db + 5) = (p4 - 0.5f) * 2.0f;
            fxD.at (db + 6) = float (clamp (int (p5 * 9.0f + 0.5f), 0, 9));
            fxD.at (db + 7) = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        }
''' + src[j:]

# envelope step
i = src.index('    float fxEnvStep (int s, int db)')
j = src.index('    float<2> fxFilter (int s, float<2> x)', i)
src = src[:i] + '''    // FX-FENV2: the envelope of the filter effect runs like the modulation envelope e (same times, sustain and curves)
    float fxEnvStep (int s, int db)
    {
        int   st = fxEnvSt.at (s);
        float lv = fxEnvLv.at (s);
        int   e  = clamp (int (fxD.at (db + 6) + 0.5f), 0, 9);
        float dt = float (processor.period);

        if (fxEnvSeen.at (s) != fxNoteSeq)
        {
            fxEnvSeen.at (s) = fxNoteSeq;

            if (fxHeld)
                st = 1;
        }

        if (fxHeld)
        {
            if (st == 0 || st == 4)
                st = 1;
        }
        else if (st >= 1 && st <= 3)
            st = 4;

        if (st == 1)
        {
            lv += dt / max (mEnvA.at (e) * 0.001f, 0.0005f);

            if (lv >= 1.0f)
            {
                lv = 1.0f;
                st = 2;
            }
        }
        else if (st == 2 || st == 3)
        {
            float sus = mEnvS.at (e);
            lv += (sus - lv) * clamp (dt * 5.0f / (max (mEnvD.at (e), 1.0f) * 0.001f), 0.0f, 0.99f);
            st = abs (lv - sus) < 0.0005f ? 3 : 2;
        }
        else if (st == 4)
        {
            lv -= lv * clamp (dt * 5.0f / (max (mEnvR.at (e), 1.0f) * 0.001f), 0.0f, 0.99f);

            if (lv < 0.0001f)
            {
                lv = 0.0f;
                st = 0;
            }
        }

        fxEnvSt.at (s) = st;
        fxEnvLv.at (s) = lv;
        return lv;
    }

''' + src[j:]

# filter body
i = src.index('        float g   = fxD.at (db);\n        float k   = fxD.at (db + 1);', src.index('    float<2> fxFilter (int s, float<2> x)'))
j = src.index('        float yl = fxFilterX (s, 0, inL, g, k, res, fc, ft);', i)
src = src[:i] + '''        float g   = fxD.at (db);
        float k   = fxD.at (db + 1);
        float res = fxD.at (db + 2);
        float fc  = fxD.at (db + 3);
        float eAmt = fxD.at (db + 5);
        float kt   = fxD.at (db + 7);

        // FX-FENV2: key tracking and cutoff smoothing, then the envelope
        float sr   = float (processor.frequency);
        float fcT  = kt > 0.001f ? clamp (fc * float (pow (2.0f, lastKeyV * 4.0f * kt)), 20.0f, sr * 0.45f) : fc;
        float fcS  = fxFcS.at (s);
        bool  mv   = false;

        if (fcS < 1.0f)
            fcS = fcT;

        if (abs (fcT - fcS) > fcT * 0.0003f)
        {
            fcS += (fcT - fcS) * 0.004f;
            mv = true;
        }
        else
            fcS = fcT;

        fxFcS.at (s) = fcS;

        if (abs (eAmt) > 0.001f || mv || kt > 0.001f || abs (fcS - fc) > fc * 0.0003f)
        {
            float lv = abs (eAmt) > 0.001f ? fxEnvStep (s, db) : 0.0f;
            fc = clamp (fcS * float (exp (float64 (eAmt * lv * 7.0f) * 0.6931471805599453)), 20.0f, sr * 0.45f);
            int ec = fxEnvCt.at (s);

            if (ec <= 0)
            {
                fxEnvGc.at (s) = float (tan (float64 (fc) * pi * processor.period));
                ec = 4;
            }

            fxEnvCt.at (s) = ec - 1;
            g = fxEnvGc.at (s);
        }

''' + src[j:]
open(path, 'w').write(src)
print('ok')
