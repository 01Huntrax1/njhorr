#!/usr/bin/env python3
"""Idempotent: FX type 14 "Saturator" (12 analog style saturation models) and FX type 15 "Waveshaper" (transfer curve from up to 16 nodes) in
patch/Eisenpuls_Synth.cmajor.  Both shape with first-order antiderivative anti-aliasing (ADAA: y = (F(u) - F(u_prev)) / (u - u_prev), the technique used by
ChowDSP and others) instead of oversampling.  The Waveshaper nodes are stored like the Parametric EQ bands (eqLoad, peqB[slot * 240 ...]: 0 = node count / 16,
then x, y, curve per node, all -1..1).  Run after build_eq.py / build_reverb.py."""
import os, sys, re
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if '// FX-SAT' in src:
    print('already applied'); sys.exit(0)

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old[:70], src.count(old))
    src = src.replace(old, new)

src = re.sub(r'(FX \d+ Type",\s*min: 0\.0, max: )13\.0', r'\g<1>15.0', src)
rep('        int nt = clamp (t, 0, 13);', '        int nt = clamp (t, 0, 15);')
rep('        if (ty == 13)\n            fxPeqDerive (s);\n', '        if (ty == 13)\n            fxPeqDerive (s);\n\n        if (ty == 14)\n            fxSatDerive (s);   // FX-SAT\n\n        if (ty == 15)\n            fxWsDerive (s);\n')
rep('        else if (ty == 13) y = fxPeq    (s, x);\n', '        else if (ty == 13) y = fxPeq    (s, x);\n        else if (ty == 14) y = fxSat    (s, x);\n        else if (ty == 15) y = fxWs     (s, x);\n')

dsp = r'''
    // ================= FX-SAT: Saturator (FX type 14) and Waveshaper (FX type 15) =================
    // Saturator models (mode): 0 Tube (asymmetric tanh), 1 Tape (soft tanh, head bump, high-frequency loss), 2 Transformer (low frequencies driven harder),
    // 3 Diode (asinh), 4 Fuzz (asymmetric hard clip), 5 Soft Clip (cubic), 6 Hard Clip, 7 Rectifier (tanh + half-wave), 8 Sine Fold, 9 Rational (x / (1 + |x|)),
    // 10 Exciter (saturated high band added back), 11 Arctan.
    // Slot parameters: P1 Drive (0..36 dB), P2 Tone (tilt), P3 Bias, P4 Output (+-12 dB), P5 Low Cut (before the shaper), P6 Sag (level dependent drive loss).
    // Waveshaper: P1 Drive (0..30 dB), P2 Bias, P3 Output (+-12 dB), P4 Tone (post low-pass), P5 Low Cut; modes 0 Curve, 1 Mirror (odd symmetric), 2 Rectified.
    // fxD: Saturator db 0 drive gain, 1 bias, 2 output gain, 3 tone, 4 low-cut coefficient, 5 sag, 6 tone low-pass coefficient, 7 dc coefficient, 8 transformer low-pass,
    // 9 tape low-pass, 10 exciter low-pass, 11 envelope attack, 12 envelope release, 13 tape bump low-pass.  fxF per channel c: c low cut, 2 + c previous input,
    // 4 + c tone low-pass, 6 + c dc, 8 + c transformer, 10 + c post low-pass, 12 + c tape, 14 + c bump / exciter, 16 + c envelope.

    float satLogCosh (float x)
    {
        float a = abs (x);
        return a + float (log (1.0f + float (exp (-2.0f * a)))) - 0.6931472f;
    }

    float satf (int m, float u)
    {
        float a = abs (u);

        if (m == 0)  return u >= 0.0f ? float (tanh (u)) : 0.75f * float (tanh (u / 0.75f));
        if (m == 1)  return 1.05f * float (tanh (0.9f * u));
        if (m == 3)  return float (log (a + sqrt (a * a + 1.0f))) * (u < 0.0f ? -1.0f : 1.0f);
        if (m == 4)  return clamp (4.0f * u, -0.6f, 1.0f);
        if (m == 5)  return a <= 1.0f ? 1.5f * (u - u * u * u * 0.333333f) : (u < 0.0f ? -1.0f : 1.0f);
        if (m == 6)  return clamp (u, -1.0f, 1.0f);
        if (m == 7)  return 0.6f * (float (tanh (u)) + 0.7f * abs (float (tanh (u))));
        if (m == 8)  return float (sin (2.0f * u));
        if (m == 9)  return u / (1.0f + a);
        if (m == 11) return 0.63662f * float (atan (1.6f * u));

        return float (tanh (u));
    }

    // antiderivative of satf (F(0) = 0)
    float satF (int m, float u)
    {
        float a = abs (u);

        if (m == 0)  return u >= 0.0f ? satLogCosh (u) : 0.5625f * satLogCosh (u / 0.75f);
        if (m == 1)  return 1.1666667f * satLogCosh (0.9f * u);
        if (m == 3)  return a * (float (log (a + sqrt (a * a + 1.0f)))) - sqrt (u * u + 1.0f) + 1.0f;

        if (m == 4)
        {
            if (u < -0.15f) return 0.045f - 0.6f * (u + 0.15f);
            if (u > 0.25f)  return 0.125f + (u - 0.25f);
            return 2.0f * u * u;
        }

        if (m == 5)  return a <= 1.0f ? 1.5f * (u * u * 0.5f - u * u * u * u * 0.083333f) : 0.625f + (a - 1.0f);
        if (m == 6)  return a <= 1.0f ? u * u * 0.5f : a - 0.5f;
        if (m == 7)  return 0.6f * satLogCosh (u) * (u < 0.0f ? 0.3f : 1.7f);
        if (m == 8)  return 0.5f * (1.0f - float (cos (2.0f * u)));
        if (m == 9)  return a - float (log (1.0f + a));
        if (m == 11) return 0.63662f * (u * float (atan (1.6f * u)) - float (log (1.0f + 2.56f * u * u)) * 0.3125f);

        return satLogCosh (u);
    }

    float satAdaa (int m, float u, float up)
    {
        float du = u - up;

        if (abs (du) < 0.0001f)
            return satf (m, 0.5f * (u + up));

        return (satF (m, u) - satF (m, up)) / du;
    }

    void fxSatDerive (int s)
    {
        float sr = float (processor.frequency);
        float dt = float (processor.period);
        int   db = s * 16;
        int   pb = s * 6;
        int   m  = fxMode.at (s);
        float p1 = clamp (fxP.at (pb),     0.0f, 1.0f);
        float g  = float (pow (10.0f, p1 * 36.0f / 20.0f));
        float cp = 1.0f;

        if (m != 10)
            cp = 0.5f / max (abs (satf (m, 0.5f * g)), 0.05f);

        fxD.at (db)      = g;
        fxD.at (db + 1)  = (clamp (fxP.at (pb + 2), 0.0f, 1.0f) - 0.5f) * 1.0f;
        fxD.at (db + 2)  = float (pow (10.0f, (clamp (fxP.at (pb + 3), 0.0f, 1.0f) - 0.5f) * 24.0f / 20.0f)) * cp;
        fxD.at (db + 3)  = (clamp (fxP.at (pb + 1), 0.0f, 1.0f) - 0.5f) * 2.0f;
        fxD.at (db + 4)  = clamp (float (twoPi) * fxExpMap (clamp (fxP.at (pb + 4), 0.0f, 1.0f), 10.0f, 800.0f) * dt, 0.0f, 1.0f);
        fxD.at (db + 5)  = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        fxD.at (db + 6)  = clamp (float (twoPi) * 2500.0f * dt, 0.0f, 1.0f);
        fxD.at (db + 7)  = clamp (float (twoPi) * 18.0f * dt, 0.0f, 1.0f);
        fxD.at (db + 8)  = clamp (float (twoPi) * 130.0f * dt, 0.0f, 1.0f);
        fxD.at (db + 9)  = clamp (float (twoPi) * 11000.0f * dt, 0.0f, 1.0f);
        fxD.at (db + 10) = clamp (float (twoPi) * 3000.0f * dt, 0.0f, 1.0f);
        fxD.at (db + 11) = clamp (1.0f - float (exp (-1.0f / (sr * 0.001f))), 0.0f, 1.0f);
        fxD.at (db + 12) = clamp (1.0f - float (exp (-1.0f / (sr * 0.12f))), 0.0f, 1.0f);
        fxD.at (db + 13) = clamp (float (twoPi) * 90.0f * dt, 0.0f, 1.0f);
    }

    // one channel of the Saturator
    float satCh (int s, int c, float x)
    {
        int   fb  = s * 40;
        int   db  = s * 16;
        int   m   = fxMode.at (s);
        float g   = fxD.at (db);
        float bi  = fxD.at (db + 1);

        // low cut before the shaper
        float lcs = fxF.at (fb + c);
        lcs += fxD.at (db + 4) * (x - lcs);
        fxF.at (fb + c) = lcs;
        float xi = x - lcs;

        // sag: the louder the input, the less drive
        float env = fxF.at (fb + 16 + c);
        float ae  = abs (xi);
        env += (ae > env ? fxD.at (db + 11) : fxD.at (db + 12)) * (ae - env);
        fxF.at (fb + 16 + c) = env;
        float ge = g / (1.0f + fxD.at (db + 5) * 8.0f * env);

        float y = 0.0f;

        if (m == 10)
        {
            // exciter: the high band saturated and added back
            float lp = fxF.at (fb + 14 + c);
            lp += fxD.at (db + 10) * (xi - lp);
            fxF.at (fb + 14 + c) = lp;
            float hp = xi - lp;
            y = xi + 0.7f * float (tanh (min (ge, 30.0f) * hp * 4.0f)) * 0.5f;
        }
        else
        {
            float u = xi * ge + bi;

            if (m == 2)
            {
                float l = fxF.at (fb + 8 + c);
                l += fxD.at (db + 8) * (u - l);
                fxF.at (fb + 8 + c) = l;
                u += 1.2f * l;
            }

            float up = fxF.at (fb + 2 + c);
            fxF.at (fb + 2 + c) = u;
            y = satAdaa (m, u, up);

            if (m == 2)
            {
                float l2 = fxF.at (fb + 10 + c);
                l2 += fxD.at (db + 8) * (y - l2);
                fxF.at (fb + 10 + c) = l2;
                y -= 0.4f * l2;
            }
            else if (m == 1)
            {
                float t = fxF.at (fb + 12 + c);
                t += fxD.at (db + 9) * (y - t);
                fxF.at (fb + 12 + c) = t;
                float bp = fxF.at (fb + 14 + c);
                bp += fxD.at (db + 13) * (t - bp);
                fxF.at (fb + 14 + c) = bp;
                y = t + 0.35f * bp;
            }
        }

        // DC blocker (bias and asymmetric models add an offset)
        float dc = fxF.at (fb + 6 + c);
        dc += fxD.at (db + 7) * (y - dc);
        fxF.at (fb + 6 + c) = dc;
        y -= dc;

        // tone: below the middle a low-pass blend, above it the highs boosted
        float tn = fxD.at (db + 3);
        float tl = fxF.at (fb + 4 + c);
        tl += fxD.at (db + 6) * (y - tl);
        fxF.at (fb + 4 + c) = tl;

        if (tn >= 0.0f)  y += tn * 1.5f * (y - tl);
        else             y = y * (1.0f + tn) + tl * (-tn);

        return y * fxD.at (db + 2);
    }

    float<2> fxSat (int s, float<2> x)
    {
        return float<2> (satCh (s, 0, x[0]), satCh (s, 1, x[1]));
    }

    // ---- Waveshaper: the transfer curve table of a slot lives in the arena: f at ab + 0 .. 1024, antiderivative F (F(0) = 0) at ab + 1100 .. 2124, input -1 .. 1 ----
    float wsNodeCurve (int s, float x)
    {
        int   nb = s * 240;
        int   n  = clamp (int (peqB.at (nb) * 16.0f + 0.5f), 0, 16);

        if (n < 2)
            return x;

        float[16] nx;
        float[16] ny;
        float[16] nc;

        for (int i = 0; i < n; ++i)
        {
            nx.at (i) = peqB.at (nb + 1 + 3 * i);
            ny.at (i) = peqB.at (nb + 2 + 3 * i);
            nc.at (i) = peqB.at (nb + 3 + 3 * i);
        }

        // insertion sort by x
        for (int i = 1; i < n; ++i)
        {
            float kx = nx.at (i);
            float ky = ny.at (i);
            float kc = nc.at (i);
            int   j  = i - 1;

            while (j >= 0 && nx.at (j) > kx)
            {
                nx.at (j + 1) = nx.at (j);
                ny.at (j + 1) = ny.at (j);
                nc.at (j + 1) = nc.at (j);
                j -= 1;
            }

            nx.at (j + 1) = kx;
            ny.at (j + 1) = ky;
            nc.at (j + 1) = kc;
        }

        if (x <= nx.at (0))
            return ny.at (0);

        for (int i = 0; i < n - 1; ++i)
        {
            if (x <= nx.at (i + 1))
            {
                float w = nx.at (i + 1) - nx.at (i);
                float t = w > 0.00001f ? (x - nx.at (i)) / w : 1.0f;
                float p = float (pow (2.0f, nc.at (i) * 3.0f));
                return ny.at (i) + (ny.at (i + 1) - ny.at (i)) * float (pow (clamp (t, 0.0f, 1.0f), p));
            }
        }

        return ny.at (n - 1);
    }

    void fxWsDerive (int s)
    {
        float dt = float (processor.period);
        int   db = s * 16;
        int   pb = s * 6;
        int   ab = s * 196608;

        fxD.at (db)     = float (pow (10.0f, clamp (fxP.at (pb), 0.0f, 1.0f) * 30.0f / 20.0f));
        fxD.at (db + 1) = (clamp (fxP.at (pb + 1), 0.0f, 1.0f) - 0.5f) * 1.0f;
        fxD.at (db + 2) = float (pow (10.0f, (clamp (fxP.at (pb + 2), 0.0f, 1.0f) - 0.5f) * 24.0f / 20.0f));
        fxD.at (db + 3) = clamp (float (twoPi) * fxExpMap (clamp (fxP.at (pb + 3), 0.0f, 1.0f), 500.0f, 20000.0f) * dt, 0.0f, 1.0f);
        fxD.at (db + 4) = clamp (float (twoPi) * fxExpMap (clamp (fxP.at (pb + 4), 0.0f, 1.0f), 10.0f, 800.0f) * dt, 0.0f, 1.0f);
        fxD.at (db + 7) = clamp (float (twoPi) * 18.0f * dt, 0.0f, 1.0f);

        float acc = 0.0f;
        float prev = 0.0f;

        for (int i = 0; i <= 1024; ++i)
        {
            float x  = float (i - 512) / 512.0f;
            float fy = clamp (wsNodeCurve (s, x), -1.0f, 1.0f);
            fxArena.at (ab + i) = fy;

            if (i > 0)
                acc += 0.5f * (prev + fy) / 512.0f;

            prev = fy;
            fxArena.at (ab + 1100 + i) = acc;
        }

        // F(0) = 0
        float f0 = fxArena.at (ab + 1100 + 512);

        for (int i = 0; i <= 1024; ++i)
            fxArena.at (ab + 1100 + i) -= f0;
    }

    float wsTabF (int ab, float u)
    {
        float a = clamp (u, -1.0f, 1.0f);
        float p = (a + 1.0f) * 512.0f;
        int   i = clamp (int (p), 0, 1023);
        float fr = p - float (i);
        float v = fxArena.at (ab + 1100 + i) * (1.0f - fr) + fxArena.at (ab + 1101 + i) * fr;

        if (u > 1.0f)       v += fxArena.at (ab + 1024) * (u - 1.0f);
        else if (u < -1.0f) v += fxArena.at (ab) * (u + 1.0f);

        return v;
    }

    float wsTabf (int ab, float u)
    {
        float a = clamp (u, -1.0f, 1.0f);
        float p = (a + 1.0f) * 512.0f;
        int   i = clamp (int (p), 0, 1023);
        float fr = p - float (i);
        return fxArena.at (ab + i) * (1.0f - fr) + fxArena.at (ab + 1 + i) * fr;
    }

    // value and antiderivative of the shaped function for mode md (0 curve, 1 odd mirror, 2 rectified)
    float wsFn (int ab, int md, float u)
    {
        if (md == 1) return u < 0.0f ? -wsTabf (ab, -u) : wsTabf (ab, u);
        if (md == 2) return wsTabf (ab, abs (u));
        return wsTabf (ab, u);
    }

    float wsAnti (int ab, int md, float u)
    {
        if (md == 1) return wsTabF (ab, abs (u));
        if (md == 2) return u < 0.0f ? -wsTabF (ab, -u) : wsTabF (ab, u);
        return wsTabF (ab, u);
    }

    float wsCh (int s, int c, float x)
    {
        int   fb = s * 40;
        int   db = s * 16;
        int   ab = s * 196608;
        int   md = fxMode.at (s);

        float lcs = fxF.at (fb + c);
        lcs += fxD.at (db + 4) * (x - lcs);
        fxF.at (fb + c) = lcs;

        float u  = (x - lcs) * fxD.at (db) + fxD.at (db + 1);
        float up = fxF.at (fb + 2 + c);
        fxF.at (fb + 2 + c) = u;
        float du = u - up;
        float y  = abs (du) < 0.0001f ? wsFn (ab, md, 0.5f * (u + up)) : (wsAnti (ab, md, u) - wsAnti (ab, md, up)) / du;

        float dc = fxF.at (fb + 6 + c);
        dc += fxD.at (db + 7) * (y - dc);
        fxF.at (fb + 6 + c) = dc;
        y -= dc;

        float tl = fxF.at (fb + 4 + c);
        tl += fxD.at (db + 3) * (y - tl);
        fxF.at (fb + 4 + c) = tl;

        return tl * fxD.at (db + 2);
    }

    float<2> fxWs (int s, float<2> x)
    {
        return float<2> (wsCh (s, 0, x[0]), wsCh (s, 1, x[1]));
    }

'''
rep('    float<2> fxCrush (int s, float<2> x)\n', dsp.replace('FX-SAT: Saturator', 'FX-SAT: Saturator') + '    float<2> fxCrush (int s, float<2> x)\n')
open(path, 'w').write(src)
print('applied')
