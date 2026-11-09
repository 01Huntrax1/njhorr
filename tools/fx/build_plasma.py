#!/usr/bin/env python3
"""Idempotent (marker FX-PLASMA): FX type 28 "Plasma", an asymmetric distortion in the style of Dimethoxy's free "Plasma" plugin
(12 distortion styles, asymmetry, "girth" noise erosion, resonant filter HP / LP / Dual / Peak).  Own implementation from the public feature description,
no code of the original: first-order antiderivative anti-aliasing (ADAA) shapers, a TPT state variable filter, level compensation.
Slot parameters: P1 Drive (0..40 dB), P2 Asym (bias, -100..100 %), P3 Girth (noise), P4 Filter type (HP, LP, Dual, Peak in four steps),
P5 Freq, P6 Reso (Q for HP / LP / Dual, boost for Peak).  State: fxF[s*40 ..]: 0-1 previous shaper input, 2-3 DC blocker, 4-5 previous noise,
6-9 filter A (2 per channel), 10-13 filter B (Dual); plN: noise generator."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'FX-PLASMA' in src:
    print('already applied'); sys.exit(0)

def rep(old, new):
    global src
    assert src.count(old) == 1, (src.count(old), old[:80])
    src = src.replace(old, new)

src, n = re.subn(r'(FX \d+ (?:Type|Sync)",\s*min: 0\.0, max: )27\.0', r'\g<1>28.0', src)
assert n == 48, n
rep('int nt = clamp (t, 0, 27);', 'int nt = clamp (t, 0, 28);')
rep('        if (ty == 15)\n            fxWsDerive (s);\n', '        if (ty == 15)\n            fxWsDerive (s);\n\n        if (ty == 28)\n            fxPlDerive (s);   // FX-PLASMA\n')
rep('        else if (ty == 27) y = fxAwMack    (s, x);\n', '        else if (ty == 27) y = fxAwMack    (s, x);\n        else if (ty == 28) y = fxPlasma    (s, x);\n')
rep('    float64[2304] awT;', '    int64[128]   plN;   // FX-PLASMA: noise generator state (2 per slot)\n    float64[2304] awT;')

CODE = r'''    // ================= FX-PLASMA: asymmetric distortion with girth noise and a resonant filter (FX type 28) =================
    // style m: 0 Soft, 1 Hard, 2 Fold, 3 Half, 4 Fuzz, 5 Diode, 6 Arctan, 7 Rational, 8 Soft Exp, 9 Ripple, 10 Tri Fold, 11 Cubic
    float plLogCosh (float u)
    {
        float a = abs (u);
        return a + float (log (1.0f + exp (-2.0f * a))) - 0.6931472f;
    }

    float plFn (int m, float u)
    {
        float a = abs (u);

        if (m == 0)  return float (tanh (u));
        if (m == 1)  return clamp (u, -1.0f, 1.0f);
        if (m == 2)  return float (sin (u * 1.5707963f));
        if (m == 3)  return u > 0.0f ? float (tanh (u)) : 0.15f * float (tanh (u));
        if (m == 4)  return u < 0.0f ? -(1.0f - float (exp (-2.0f * a))) : (1.0f - float (exp (-2.0f * a)));
        if (m == 5)  return u >= 0.0f ? 1.0f - float (exp (-u)) : 0.3f * (float (exp (u)) - 1.0f);
        if (m == 6)  return float (atan (u)) * 0.63661977f;
        if (m == 7)  return u / float (sqrt (1.0f + u * u));
        if (m == 8)  return u / (1.0f + a);
        if (m == 9)  return 0.9f * float (tanh (u)) + 0.1f * float (sin (8.0f * u));
        if (m == 10) return 0.63661977f * float (asin (clamp (float (sin (u * 1.5707963f)), -1.0f, 1.0f)));

        if (a <= 1.0f)
            return 1.5f * u - 0.5f * u * u * u;

        return u < 0.0f ? -1.0f : 1.0f;
    }

    // antiderivative of plFn with F (0) = 0
    float plAnti (int m, float u)
    {
        float a = abs (u);

        if (m == 0)  return plLogCosh (u);
        if (m == 1)  return a <= 1.0f ? 0.5f * u * u : a - 0.5f;
        if (m == 2)  return 0.63661977f * (1.0f - float (cos (u * 1.5707963f)));
        if (m == 3)  return u > 0.0f ? plLogCosh (u) : 0.15f * plLogCosh (u);
        if (m == 4)  return a + 0.5f * (float (exp (-2.0f * a)) - 1.0f);
        if (m == 5)  return u >= 0.0f ? u + float (exp (-u)) - 1.0f : 0.3f * (float (exp (u)) - 1.0f - u);
        if (m == 6)  return (u * float (atan (u)) - 0.5f * float (log (1.0f + u * u))) * 0.63661977f;
        if (m == 7)  return float (sqrt (1.0f + u * u)) - 1.0f;
        if (m == 8)  return a - float (log (1.0f + a));
        if (m == 9)  return 0.9f * plLogCosh (u) + 0.0125f * (1.0f - float (cos (8.0f * u)));

        if (a <= 1.0f)
            return 0.75f * u * u - 0.125f * u * u * u * u;

        return a - 0.375f;
    }

    void fxPlDerive (int s)
    {
        float sr = float (processor.frequency);
        int   db = s * 16;
        int   pb = s * 6;
        int   m  = clamp (fxMode.at (s), 0, 11);
        float p1 = clamp (fxP.at (pb),     0.0f, 1.0f);
        float g  = float (pow (10.0f, p1 * 40.0f / 20.0f));
        float bi = (clamp (fxP.at (pb + 1), 0.0f, 1.0f) - 0.5f) * 1.6f;
        float f  = fxExpMap (clamp (fxP.at (pb + 4), 0.0f, 1.0f), 20.0f, 20000.0f);
        float rs = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        int   ft = clamp (int (clamp (fxP.at (pb + 3), 0.0f, 1.0f) * 4.0f), 0, 3);
        float fm = 0.45f * sr;

        fxD.at (db)      = g;
        fxD.at (db + 1)  = bi;
        fxD.at (db + 2)  = 0.5f / max (abs (plFn (m, 0.5f * g)), 0.25f);           // level compensation
        fxD.at (db + 3)  = clamp (fxP.at (pb + 2), 0.0f, 1.0f);                    // girth
        fxD.at (db + 4)  = float (ft);
        fxD.at (db + 5)  = float (tan (3.14159265f * min (f, fm) / sr));           // filter A
        fxD.at (db + 6)  = 1.414f - 1.364f * rs;                                   // damping (Q 0.7 .. 20)
        fxD.at (db + 7)  = float (tan (3.14159265f * min (f * 0.4f, fm) / sr));    // Dual: high-pass below
        fxD.at (db + 8)  = float (tan (3.14159265f * min (f * 2.0f, fm) / sr));    // Dual: low-pass above
        fxD.at (db + 9)  = clamp (float (twoPi) * 15.0f / sr, 0.0f, 1.0f);         // DC blocker
        fxD.at (db + 10) = rs * 10.0f;                                             // Peak boost
        fxD.at (db + 11) = plFn (m, bi);                                           // static offset of the bias
    }

    float plNoise (int idx)
    {
        plN.at (idx) = (plN.at (idx) * 1103515245L + 12345L) & 2147483647L;
        return float ((plN.at (idx) >> 8) & 65535L) * 0.0000305176f - 1.0f;
    }

    float plCh (int s, int c, float x)
    {
        int   fb = s * 40;
        int   db = s * 16;
        int   m  = clamp (fxMode.at (s), 0, 11);
        float g  = fxD.at (db);
        float u  = x * g + fxD.at (db + 1);
        float gr = fxD.at (db + 3);

        if (gr > 0.0f)   // girth: high-passed noise that follows the signal level erodes the sound
        {
            float nz = plNoise (s * 2 + c);
            float hp = nz - fxF.at (fb + 4 + c);
            fxF.at (fb + 4 + c) = nz;
            u += gr * 0.6f * hp * min (abs (x) * g, 1.0f);
        }

        float up = fxF.at (fb + c);
        fxF.at (fb + c) = u;
        float du = u - up;
        float y;

        if (m == 10 || abs (du) < 0.0001f)
            y = plFn (m, 0.5f * (u + up));
        else
            y = (plAnti (m, u) - plAnti (m, up)) / du;

        y = (y - fxD.at (db + 11)) * fxD.at (db + 2);

        float dc = fxF.at (fb + 2 + c);
        dc += fxD.at (db + 9) * (y - dc);
        fxF.at (fb + 2 + c) = dc;
        y -= dc;

        int   ft = int (fxD.at (db + 4));
        float k  = fxD.at (db + 6);
        int   ia = fb + 6 + c * 2;
        int   ib = fb + 10 + c * 2;

        if (ft == 0)
            y = fxSvfStage (ia, y, fxD.at (db + 5), k, 2);
        else if (ft == 1)
            y = fxSvfStage (ia, y, fxD.at (db + 5), k, 0);
        else if (ft == 2)
        {
            y = fxSvfStage (ia, y, fxD.at (db + 7), k, 2);
            y = fxSvfStage (ib, y, fxD.at (db + 8), k, 0);
        }
        else
            y += fxSvfStage (ia, y, fxD.at (db + 5), 0.5f, 1) * fxD.at (db + 10);

        return y;
    }

    float<2> fxPlasma (int s, float<2> x)
    {
        return float<2> (plCh (s, 0, x[0]), plCh (s, 1, x[1]));
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
open(P, 'w').write(src)
print('applied')
