#!/usr/bin/env python3
"""Idempotent: FX type 17 "Console", marker FX-CONSOLE.
Channel strip after the console EQs (Sonic Sweep 2 idea): input transformer drive -> two sweepable parametric mid bands.
P1 Lo-Mid Freq (45 Hz .. 3 kHz), P2 Lo-Mid Gain (+-15 dB), P3 Hi-Mid Freq (500 Hz .. 18 kHz), P4 Hi-Mid Gain (+-15 dB),
P5 Drive (transformer saturation), P6 Age (asymmetric distortion + rounded highs).
Modes = bandwidth of both bands: Wide (Q 0.45), Medium (1.0), Narrow (2.5), Surgical (6).
Mode 4..7 = the same bandwidths with the EQ in front of the saturation (EQ Flip).
State: fxF fb+0..3 lo-mid z, fb+4..7 hi-mid z, fb+8/9 age low-pass; fxD db..db+4 band 1, db+5..db+9 band 2, db+10 drive, db+11 age, db+12 level comp, db+13 lp coeff."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'FX-CONSOLE' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )16\.0', r'\g<1>17.0', src); assert n == 30, n
rep('        int nt = clamp (t, 0, 16);', '        int nt = clamp (t, 0, 17);')
rep('        if (ty == 16)\n            fxUniDerive (s);', '        if (ty == 17)\n            fxConDerive (s);   // FX-CONSOLE\n\n        if (ty == 16)\n            fxUniDerive (s);')
rep('        else if (ty == 16) y = fxUni    (s, x);\n', '        else if (ty == 16) y = fxUni    (s, x);\n        else if (ty == 17) y = fxCon    (s, x);\n')
dsp = r'''    // ================= FX-CONSOLE: Console channel strip (FX type 17) =================
    void fxConDerive (int s)
    {
        int   db = s * 16;
        int   pb = s * 6;
        float sr = float (processor.frequency);
        float dt = float (processor.period);
        float p1 = clamp (fxP.at (pb),     0.0f, 1.0f);
        float p2 = clamp (fxP.at (pb + 1), 0.0f, 1.0f);
        float p3 = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float p4 = clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float p5 = clamp (fxP.at (pb + 4), 0.0f, 1.0f);
        float p6 = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        int   bw = clamp (fxMode.at (s), 0, 7) & 3;
        float q  = 0.45f;
        if (bw == 1) q = 1.0f;
        if (bw == 2) q = 2.5f;
        if (bw == 3) q = 6.0f;

        fxBiquad (db,     1, (p2 - 0.5f) * 30.0f, fxExpMap (p1, 45.0f, 3000.0f),   q);
        fxBiquad (db + 5, 1, (p4 - 0.5f) * 30.0f, fxExpMap (p3, 500.0f, 18000.0f), q);

        float d = 1.0f + 5.0f * p5;
        fxD.at (db + 10) = d;
        fxD.at (db + 11) = p6;
        fxD.at (db + 12) = 1.0f / (1.0f + 0.6f * (d - 1.0f));
        float fc = fxExpMap (1.0f - p6, 7000.0f, 22000.0f);
        fxD.at (db + 13) = fc > 20000.0f ? 1.0f : clamp (1.0f - float (exp (-float (twoPi) * fc * dt)), 0.0f, 1.0f);
    }

    // transformer / op-amp stage: tanh saturation, the age adds an asymmetric bias and rounds the highs
    float fxConSat (int s, int ch, float x)
    {
        int   fb  = s * 40;
        int   db  = s * 16;
        float d   = fxD.at (db + 10);
        float age = fxD.at (db + 11);
        float lc  = fxD.at (db + 13);
        float bias = 0.22f * age;
        float y   = (float (tanh (x * d + bias)) - float (tanh (bias))) * fxD.at (db + 12);
        float st  = fxF.at (fb + 8 + ch);
        st += lc * (y - st);
        fxF.at (fb + 8 + ch) = st;
        return st;
    }

    float fxConEq (int s, int ch, float x)
    {
        int   fb = s * 40;
        int   db = s * 16;
        float y  = x;

        for (int b = 0; b < 2; ++b)
        {
            int   ci = db + b * 5;
            int   zi = fb + b * 4 + ch * 2;
            float yo = fxD.at (ci) * y + fxF.at (zi);
            fxF.at (zi)     = fxD.at (ci + 1) * y - fxD.at (ci + 3) * yo + fxF.at (zi + 1);
            fxF.at (zi + 1) = fxD.at (ci + 2) * y - fxD.at (ci + 4) * yo;
            y = yo;
        }

        return y;
    }

    float<2> fxCon (int s, float<2> x)
    {
        bool flip = fxMode.at (s) >= 4;
        float l = x[0];
        float r = x[1];

        if (flip)
            return float<2> (fxConSat (s, 0, fxConEq (s, 0, l)), fxConSat (s, 1, fxConEq (s, 1, r)));

        return float<2> (fxConEq (s, 0, fxConSat (s, 0, l)), fxConEq (s, 1, fxConSat (s, 1, r)));
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', dsp + '    // One slot: dry/wet mix of the selected effect;')
open(path, 'w').write(src)
print('ok')
