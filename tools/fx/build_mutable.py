#!/usr/bin/env python3
"""Idempotent (marker FX-MUTABLE): two effects in the spirit of Mutable Instruments (Emilie Gillet, MIT licence) modules, FX types 29 and 30.
Own implementations after the public manuals, no code of the originals:
 29 "Granular" (like Clouds): 4 modes Granular / Freeze / Pitch Shifter / Looping Delay.  P1 Position, P2 Size, P3 Pitch, P4 Density, P5 Texture, P6 Feedback.
 30 "Warp" (like Warps): the input is the modulator, an internal oscillator the carrier; 8 algorithms Crossfade / Fold / Analog RM / Digital RM / XOR / Comparator /
    Vocoder / Freq Shift.  P1 Amount, P2 Level, P3 Pitch (carrier / shift in Hz), P4 Shape, P5 Drive, P6 Release (Vocoder) / direction (Freq Shift).
State: mgG (32 grains x 8 floats per slot), wpV (128 floats per slot), the delay-style stereo buffer of the slot arena (2 x 98304)."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'FX-MUTABLE' in src:
    print('already applied'); sys.exit(0)

def rep(old, new):
    global src
    assert src.count(old) == 1, (src.count(old), old[:80])
    src = src.replace(old, new)

src, n = re.subn(r'(FX \d+ (?:Type|Sync)",\s*min: 0\.0, max: )28\.0', r'\g<1>30.0', src)
assert n == 48, n
rep('int nt = clamp (t, 0, 28);', 'int nt = clamp (t, 0, 30);')
rep('        if (ty == 28)\n            fxPlDerive (s);   // FX-PLASMA\n', '        if (ty == 28)\n            fxPlDerive (s);   // FX-PLASMA\n\n        if (ty == 29)\n            fxMgDerive (s);   // FX-MUTABLE\n\n        if (ty == 30)\n            fxWpDerive (s);\n')
rep('        else if (ty == 28) y = fxPlasma    (s, x);\n', '        else if (ty == 28) y = fxPlasma    (s, x);\n        else if (ty == 29) y = fxGranular  (s, x);\n        else if (ty == 30) y = fxWarp      (s, x);\n')
rep('    int64[128]   plN;', '    float[12288] mgG;   // FX-MUTABLE: grains of the Granular effect (32 per slot, 8 floats: active, position, increment, age, length, gain L, gain R)\n    float[6144]  wpV;   // FX-MUTABLE: filter memories of the Warp effect (128 per slot)\n    int64[128]   plN;')
rep('        fxFcS.at (s) = 0.0f;   // FX-FENV2\n', '        fxFcS.at (s) = 0.0f;   // FX-FENV2\n\n        for (int i = 0; i < 256; ++i)   // FX-MUTABLE\n            mgG.at (s * 256 + i) = 0.0f;\n\n        for (int i = 0; i < 128; ++i)\n            wpV.at (s * 128 + i) = 0.0f;\n')

CODE = r'''    // ================= FX-MUTABLE: Granular (FX type 29) and Warp (FX type 30) =================
    // ---- Granular: a stereo recording buffer (2 x 98304 samples of the slot arena) read by up to 32 overlapping grains
    float mgWindow (float p, float sh)
    {
        float hann = 0.5f - 0.5f * float (cos (6.2831853f * p));
        float rect = clamp (min (p, 1.0f - p) * 20.0f, 0.0f, 1.0f);
        float q    = (p - 0.5f) / 0.16f;
        float gau  = float (exp (-0.5f * q * q));

        if (sh < 0.5f)
            return rect + (hann - rect) * (sh * 2.0f);

        return hann + (gau - hann) * ((sh - 0.5f) * 2.0f);
    }

    void fxMgDerive (int s)
    {
        float sr = float (processor.frequency);
        int   db = s * 16;
        int   pb = s * 6;
        int   md = clamp (fxMode.at (s), 0, 3);
        float p1 = clamp (fxP.at (pb),     0.0f, 1.0f);
        float p2 = clamp (fxP.at (pb + 1), 0.0f, 1.0f);
        float p3 = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float p4 = clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float p5 = clamp (fxP.at (pb + 4), 0.0f, 1.0f);
        float p6 = clamp (fxP.at (pb + 5), 0.0f, 1.0f);

        fxD.at (db)      = p1 * 90000.0f;                                                       // position: how far behind the write head the grains start
        fxD.at (db + 1)  = clamp (fxExpMap (p2, 0.02f, 0.6f) * sr, 64.0f, 40000.0f);              // grain length
        fxD.at (db + 2)  = float (pow (2.0f, (p3 - 0.5f) * 4.0f));                              // pitch ratio, +-24 semitones
        fxD.at (db + 3)  = 0.3f * float (pow (26.0f, p4));                                      // overlap (grains sounding at once)
        fxD.at (db + 4)  = p5;                                                                  // texture: window shape
        fxD.at (db + 5)  = p6 * (md == 3 ? 0.98f : 0.9f);                                       // feedback
        fxD.at (db + 6)  = p5 * 0.25f * 90000.0f;                                               // texture: scatter of the start position
        fxD.at (db + 7)  = clamp (fxExpMap (p2, 0.05f, 2.0f) * sr, 256.0f, 98300.0f);             // loop length of the looping delay
    }

    float<2> fxGranular (int s, float<2> x)
    {
        int   ib  = s * 24;
        int   fb  = s * 40;
        int   ab  = s * 196608;
        int   gb  = s * 256;
        int   db  = s * 16;
        int   md  = clamp (fxMode.at (s), 0, 3);
        int   N   = 98304;
        int   wp  = fxI.at (ib + 4);
        float fbk = fxD.at (db + 5);

        if (md == 3)   // looping delay: the input is written into a loop that runs round with feedback
        {
            int L = int (fxD.at (db + 7));

            if (wp >= L)
                wp = 0;

            float oL = fxArena.at (ab + wp);
            float oR = fxArena.at (ab + N + wp);
            fxArena.at (ab + wp)     = clamp (x[0] + fbk * oL, -2.0f, 2.0f);
            fxArena.at (ab + N + wp) = clamp (x[1] + fbk * oR, -2.0f, 2.0f);
            wp++;

            if (wp >= L)
                wp = 0;

            fxI.at (ib + 4) = wp;
            return float<2> (oL, oR);
        }

        float ratio   = fxD.at (db + 2);
        float len     = min (fxD.at (db + 1), 0.45f * float (N) / max (ratio, 1.0f));
        float ovl     = fxD.at (db + 3);
        float tex     = fxD.at (db + 4);
        bool  shifter = md == 2;

        if (shifter)
        {
            ovl = 2.0f;
            tex = 0.5f;
        }

        float tim = fxF.at (fb) - 1.0f;

        if (tim <= 0.0f)
        {
            int gi = -1;

            for (int g = 0; g < 32; ++g)
                if (gi < 0 && mgG.at (gb + g * 8) < 0.5f)
                    gi = g;

            if (gi >= 0)
            {
                float minOff = md == 1 ? 4.0f : max (len * (ratio - 1.0f), 0.0f) + 4.0f;
                float off    = fxD.at (db) * (shifter ? 0.3f : 1.0f);

                if (! shifter)
                    off += fxD.at (db + 6) * (nextNoise() * 0.5f + 0.5f);

                off = clamp (max (off, minOff), 4.0f, float (N) - len * max (ratio, 1.0f) - 8.0f);

                float pan = shifter ? 0.5f : 0.5f + 0.35f * nextNoise();
                float gn  = 1.4142136f / float (sqrt (max (ovl, 1.0f)));
                float st  = float (wp) - off;

                if (st < 0.0f)
                    st += float (N);

                int g8 = gb + gi * 8;
                mgG.at (g8)     = 1.0f;
                mgG.at (g8 + 1) = st;
                mgG.at (g8 + 2) = ratio;
                mgG.at (g8 + 3) = 0.0f;
                mgG.at (g8 + 4) = len;
                mgG.at (g8 + 5) = float (cos (pan * 1.5707963f)) * gn;
                mgG.at (g8 + 6) = float (sin (pan * 1.5707963f)) * gn;
            }

            tim += max (len / ovl * (1.0f + (shifter ? 0.0f : 0.4f) * nextNoise()), 8.0f);
        }

        fxF.at (fb) = tim;

        float aL = 0.0f;
        float aR = 0.0f;

        for (int g = 0; g < 32; ++g)
        {
            int g8 = gb + g * 8;

            if (mgG.at (g8) > 0.5f)
            {
                float pos = mgG.at (g8 + 1);
                float age = mgG.at (g8 + 3);
                float gl  = mgG.at (g8 + 4);
                float w   = mgWindow (age / gl, tex);
                int   i0  = clamp (int (pos), 0, N - 1);
                int   i1  = i0 + 1 >= N ? 0 : i0 + 1;
                float fr  = pos - float (i0);
                aL += (fxArena.at (ab + i0)     * (1.0f - fr) + fxArena.at (ab + i1)     * fr) * w * mgG.at (g8 + 5);
                aR += (fxArena.at (ab + N + i0) * (1.0f - fr) + fxArena.at (ab + N + i1) * fr) * w * mgG.at (g8 + 6);
                pos += mgG.at (g8 + 2);

                if (pos >= float (N))
                    pos -= float (N);

                age += 1.0f;
                mgG.at (g8 + 1) = pos;
                mgG.at (g8 + 3) = age;

                if (age >= gl)
                    mgG.at (g8) = 0.0f;
            }
        }

        if (md != 1)   // Freeze stops the recording
        {
            fxArena.at (ab + wp)     = clamp (x[0] + fbk * aL, -2.0f, 2.0f);
            fxArena.at (ab + N + wp) = clamp (x[1] + fbk * aR, -2.0f, 2.0f);
            wp++;

            if (wp >= N)
                wp = 0;

            fxI.at (ib + 4) = wp;
        }

        return float<2> (aL, aR);
    }

    // ---- Warp: the input is the modulator, an internal oscillator the carrier
    float wpShape (float ph, float sh)
    {
        float sn = float (sin (6.2831853f * ph));
        float tr = 4.0f * abs (ph - 0.5f) - 1.0f;
        float sw = 2.0f * ph - 1.0f;
        float sq = ph < 0.5f ? 1.0f : -1.0f;
        float k  = clamp (sh, 0.0f, 1.0f) * 3.0f;

        if (k < 1.0f) return sn + (tr - sn) * k;
        if (k < 2.0f) return tr + (sw - tr) * (k - 1.0f);
        return sw + (sq - sw) * (k - 2.0f);
    }

    void fxWpDerive (int s)
    {
        int   db = s * 16;
        int   pb = s * 6;
        float p1 = clamp (fxP.at (pb),     0.0f, 1.0f);
        float p2 = clamp (fxP.at (pb + 1), 0.0f, 1.0f);
        float p3 = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float p4 = clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float p5 = clamp (fxP.at (pb + 4), 0.0f, 1.0f);
        float p6 = clamp (fxP.at (pb + 5), 0.0f, 1.0f);

        fxD.at (db)      = fxExpMap (p3, 20.0f, 4000.0f);                                  // carrier frequency / shift in Hz
        fxD.at (db + 1)  = p1;                                                              // amount
        fxD.at (db + 2)  = p2 * 2.0f;                                                       // level
        fxD.at (db + 3)  = p4;                                                              // carrier shape
        fxD.at (db + 4)  = float (pow (10.0f, (p5 - 0.5f) * 24.0f / 20.0f));                // modulator gain
        fxD.at (db + 5)  = p6;
    }

    float wpAp (int idx, float x, float a2)   // one all-pass section of the Hilbert pair: y = a2 x - x[n-2] + a2 y[n-2]
    {
        float y = a2 * x - wpV.at (idx + 1) + a2 * wpV.at (idx + 3);
        wpV.at (idx + 1) = wpV.at (idx);
        wpV.at (idx)     = x;
        wpV.at (idx + 3) = wpV.at (idx + 2);
        wpV.at (idx + 2) = y;
        return y;
    }

    float wpBp (int idx, float x, float g, float k)   // band-pass of a TPT state variable filter, unity gain at the centre
    {
        float a1 = 1.0f / (1.0f + g * (g + k));
        float a2 = g * a1;
        float a3 = g * a2;
        float s1 = wpV.at (idx);
        float s2 = wpV.at (idx + 1);
        float v3 = x - s2;
        float v1 = a1 * s1 + a2 * v3;
        float v2 = s2 + a2 * s1 + a3 * v3;
        wpV.at (idx)     = 2.0f * v1 - s1;
        wpV.at (idx + 1) = 2.0f * v2 - s2;
        return v1 * k;
    }

    // algorithms 0..5 (carrier c, modulator m, amount a)
    float wpAlg (int md, float a, float c, float m)
    {
        if (md == 0)   // crossfade, equal power
            return c * float (cos (a * 1.5707963f)) + m * float (sin (a * 1.5707963f));

        if (md == 1)   // fold: the sum of both is folded harder with the amount
            return float (sin ((c + m) * (0.4f + a * 3.5f) * 1.5707963f));

        if (md == 2)   // analog ring modulator: the difference of two diode-like curves, the amount makes them harder (more saturation, harsher products)
        {
            float k = 1.0f + 5.0f * a;
            float u = c + m;
            float v = c - m;
            return 0.5f * (u * float (tanh (k * u)) - v * float (tanh (k * v))) / k;
        }

        if (md == 3)   // digital ring modulator: the product, folded with the amount
            return float (sin (c * m * (1.0f + a * 3.0f) * 1.5707963f * 2.0f));

        if (md == 4)   // xor of the 16 bit values, the amount fades from the sum to the xor
        {
            int ci = int (clamp (c, -1.0f, 0.9999f) * 32768.0f);
            int mi = int (clamp (m, -1.0f, 0.9999f) * 32768.0f);
            float xr = float (ci ^ mi) / 32768.0f;
            return (1.0f - a) * (c + m) * 0.5f + a * xr;
        }

        // comparator: modulator above / below the carrier: maximum, minimum, gate
        float mx = m > c ? m : c;
        float mn = m > c ? c : m;
        float gt = m > c ? 0.7f : -0.7f;
        float t  = a * 2.0f;

        if (t < 1.0f)
            return mx + (mn - mx) * t;

        return mn + (gt - mn) * (t - 1.0f);
    }

    float<2> fxWarp (int s, float<2> x)
    {
        int   pb = s * 4;
        int   db = s * 16;
        int   wb = s * 128;
        int   md = clamp (fxMode.at (s), 0, 7);
        float sr = float (processor.frequency);
        float f  = fxD.at (db);
        float a  = fxD.at (db + 1);
        float lv = fxD.at (db + 2);
        float gm = fxD.at (db + 4);
        float p6 = fxD.at (db + 5);
        float64 ph = fxPh.at (pb) + float64 (f / sr);

        if (ph >= 1.0)
            ph -= 1.0;

        fxPh.at (pb) = ph;
        float c  = wpShape (float (ph), fxD.at (db + 3));
        float m0 = x[0] * gm;
        float m1 = x[1] * gm;

        if (md == 7)   // frequency shifter: Hilbert pair and a quadrature oscillator at the shift frequency
        {
            float64 sp = fxPh.at (pb + 1) + float64 ((p6 < 0.5f ? f : -f) / sr);

            if (sp >= 1.0) sp -= 1.0;
            if (sp < 0.0)  sp += 1.0;

            fxPh.at (pb + 1) = sp;
            float cs = float (cos (6.2831853f * float (sp)));
            float sn = float (sin (6.2831853f * float (sp)));
            float yo0 = 0.0f;
            float yo1 = 0.0f;

            for (int ch = 0; ch < 2; ++ch)
            {
                int   hb = wb + ch * 40;
                float v  = ch == 0 ? m0 : m1;
                float ia = wpAp (hb,      v,  0.47942553f);
                ia       = wpAp (hb + 4,  ia, 0.87625358f);
                ia       = wpAp (hb + 8,  ia, 0.97660297f);
                ia       = wpAp (hb + 12, ia, 0.99749985f);
                float qb = wpAp (hb + 16, v,  0.16176015f);
                qb       = wpAp (hb + 20, qb, 0.73297800f);
                qb       = wpAp (hb + 24, qb, 0.94539700f);
                qb       = wpAp (hb + 28, qb, 0.99059050f);
                float id = wpV.at (hb + 32);   // the in-phase path is delayed by one sample
                wpV.at (hb + 32) = ia;
                float o  = id * cs - qb * sn;

                if (ch == 0) yo0 = o; else yo1 = o;
            }

            return float<2> (yo0 * lv, yo1 * lv);
        }

        if (md == 6)   // vocoder: ten bands, the envelopes of the input shape the same bands of the carrier
        {
            float mm  = 0.5f * (m0 + m1);
            float rel = 1.0f - float (exp (-1.0f / (sr * (0.005f + p6 * p6 * 0.4f))));
            float att = 1.0f - float (exp (-1.0f / (sr * 0.002f)));
            float acc = 0.0f;

            for (int b = 0; b < 10; ++b)
            {
                float fc = 150.0f * float (pow (1.5025f, float (b)));
                float g  = float (tan (3.14159265f * min (fc, 0.45f * sr) / sr));
                int   bi = wb + b * 5;
                float mb = wpBp (bi,     mm, g, 0.3f);
                float cb = wpBp (bi + 2, c,  g, 0.3f);
                float en = wpV.at (bi + 4);
                float ab = abs (mb);
                en += (ab > en ? att : rel) * (ab - en);
                wpV.at (bi + 4) = en;
                acc += cb * en;
            }

            float o = acc * 6.0f * lv;
            return float<2> (o, o);
        }

        return float<2> (wpAlg (md, a, c, m0) * lv, wpAlg (md, a, c, m1) * lv);
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
open(P, 'w').write(src)
print('applied')
