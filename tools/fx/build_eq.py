#!/usr/bin/env python3
"""Idempotent: FX type 13 "Parametric EQ" (up to 24 bands per slot, 15 band types incl. combs, harmonics, per-band stereo / mid / side) in
patch/Eisenpuls_Synth.cmajor.  The bands are loaded per slot through the eqLoad endpoint (10 values per band).  Run after build_fx3.py."""
import os, sys, re
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if '// FX-PEQ' in src:
    print('already applied'); sys.exit(0)

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old[:70], src.count(old))
    src = src.replace(old, new)

# ---- declarations / endpoint -------------------------------------------------------------------------------------------------
rep('    int[32]       fxSync;', '''    // FX-PEQ: band table (10 values per band, 24 bands per slot, normalised), biquad sections (64 per slot, 5 coefficients, 4 states), combs (4 values per band)
    float[7200]   peqB;
    float[9600]   peqC;
    float[7680]   peqZ;
    int[1920]     peqCh;
    int[32]       peqN;
    float[2880]   peqK;
    int[32]       fxSync;''')
rep('    input event BankChunk modLoad;', '    input event BankChunk eqLoad;        // FX-PEQ: bands of a Parametric EQ slot (bank = global slot 0..29, 240 values)\n    input event BankChunk modLoad;')
rep('    input event float param881 ', '    input event float param881 ')  # sanity
rep('min: 0.0, max: 12.0, init: 0.0, step: 1.0 ]];', 'min: 0.0, max: 13.0, init: 0.0, step: 1.0 ]];', 30) if src.count('min: 0.0, max: 12.0, init: 0.0, step: 1.0 ]];') == 30 else None
src = re.sub(r'(FX \d+ Type",\s*min: 0\.0, max: )12\.0', r'\g<1>13.0', src)
rep('        int nt = clamp (t, 0, 12);', '        int nt = clamp (t, 0, 13);')
rep('''        for (int i = 0; i < 4; ++i)
            fxPh.at (s * 4 + i) = 0.0;
''', '''        for (int i = 0; i < 4; ++i)
            fxPh.at (s * 4 + i) = 0.0;

        for (int i = 0; i < 256; ++i)       // FX-PEQ: filter memories of the equaliser sections
            peqZ.at (s * 256 + i) = 0.0f;
''')

# ---- the processor -------------------------------------------------------------------------------------------------------------------
dsp = r'''
    // ================= FX-PEQ: Parametric EQ (FX type 13) =================
    // Band values (normalised, 10 per band at peqB[(slot * 24 + band) * 10 + k]):
    //   0 on, 1 type / 16, 2 frequency (0..1 = 20 Hz .. 20 kHz, log), 3 gain / 24 dB (-1..1), 4 Q (0..1 = 0.1 .. 30, log), 5 harmonics / 16, 6 harmonic falloff (0..1), 7 harmonic set / 4 (0 all, 1 odd, 2 even),
    //   8 channel / 4 (0 stereo, 1 left, 2 right, 3 mid, 4 side), 9 spare
    // Types: 0 bell, 1 low shelf, 2 high shelf, 3 low cut 12, 4 low cut 24, 5 high cut 12, 6 high cut 24, 7 band pass, 8 notch, 9 tilt, 10 all-pass, 11 comb (feed-forward), 12 comb (feedback),
    //        13 low cut 48, 14 high cut 48.   Harmonics (extra bells at 2f, 3f ... with falling gain) are available for bell, band pass, notch.
    // Slot parameters: P1 output (+-18 dB), P2 gain scale (0..200 %), P3 frequency shift (+-1 octave), P4 Q scale (x0.25 .. x4)

    // one RBJ biquad section of a slot: kind 0 peak, 1 low shelf, 2 high shelf, 3 high pass, 4 low pass, 5 band pass (gain = peak gain), 6 notch, 7 all-pass
    int peqAddSec (int s, int n, int kind, float f, float gDb, float q, int ch)
    {
        if (n >= 64)
            return n;

        float sr  = float (processor.frequency);
        float ff  = clamp (f, 10.0f, sr * 0.45f);
        float w0  = float (twoPi) * ff / sr;
        float cw  = float (cos (w0));
        float sw  = float (sin (w0));
        float al  = sw / (2.0f * clamp (q, 0.05f, 40.0f));
        float A   = float (pow (10.0f, gDb / 40.0f));
        float b0  = 1.0f;
        float b1  = 0.0f;
        float b2  = 0.0f;
        float a0  = 1.0f;
        float a1  = 0.0f;
        float a2  = 0.0f;

        if (kind == 0)
        {
            b0 = 1.0f + al * A;  b1 = -2.0f * cw;  b2 = 1.0f - al * A;
            a0 = 1.0f + al / A;  a1 = -2.0f * cw;  a2 = 1.0f - al / A;
        }
        else if (kind == 1)
        {
            float t = 2.0f * float (sqrt (A)) * al;
            b0 = A * ((A + 1.0f) - (A - 1.0f) * cw + t);
            b1 = 2.0f * A * ((A - 1.0f) - (A + 1.0f) * cw);
            b2 = A * ((A + 1.0f) - (A - 1.0f) * cw - t);
            a0 = (A + 1.0f) + (A - 1.0f) * cw + t;
            a1 = -2.0f * ((A - 1.0f) + (A + 1.0f) * cw);
            a2 = (A + 1.0f) + (A - 1.0f) * cw - t;
        }
        else if (kind == 2)
        {
            float t = 2.0f * float (sqrt (A)) * al;
            b0 = A * ((A + 1.0f) + (A - 1.0f) * cw + t);
            b1 = -2.0f * A * ((A - 1.0f) + (A + 1.0f) * cw);
            b2 = A * ((A + 1.0f) + (A - 1.0f) * cw - t);
            a0 = (A + 1.0f) - (A - 1.0f) * cw + t;
            a1 = 2.0f * ((A - 1.0f) - (A + 1.0f) * cw);
            a2 = (A + 1.0f) - (A - 1.0f) * cw - t;
        }
        else if (kind == 3)
        {
            b0 = (1.0f + cw) * 0.5f;  b1 = -(1.0f + cw);  b2 = b0;
            a0 = 1.0f + al;  a1 = -2.0f * cw;  a2 = 1.0f - al;
        }
        else if (kind == 4)
        {
            b0 = (1.0f - cw) * 0.5f;  b1 = 1.0f - cw;  b2 = b0;
            a0 = 1.0f + al;  a1 = -2.0f * cw;  a2 = 1.0f - al;
        }
        else if (kind == 5)
        {
            float gl = float (pow (10.0f, gDb / 20.0f));
            b0 = al * gl;  b1 = 0.0f;  b2 = -al * gl;
            a0 = 1.0f + al;  a1 = -2.0f * cw;  a2 = 1.0f - al;
        }
        else if (kind == 6)
        {
            b0 = 1.0f;  b1 = -2.0f * cw;  b2 = 1.0f;
            a0 = 1.0f + al;  a1 = -2.0f * cw;  a2 = 1.0f - al;
        }
        else
        {
            b0 = 1.0f - al;  b1 = -2.0f * cw;  b2 = 1.0f + al;
            a0 = 1.0f + al;  a1 = -2.0f * cw;  a2 = 1.0f - al;
        }

        int ci = (s * 64 + n) * 5;
        float ia = 1.0f / a0;
        peqC.at (ci)     = b0 * ia;
        peqC.at (ci + 1) = b1 * ia;
        peqC.at (ci + 2) = b2 * ia;
        peqC.at (ci + 3) = a1 * ia;
        peqC.at (ci + 4) = a2 * ia;
        peqCh.at (s * 64 + n) = ch;
        return n + 1;
    }

    // turns the bands and the four slot parameters of an EQ slot into sections and combs (runs when a parameter or the bands changed)
    void fxPeqDerive (int s)
    {
        float sr     = float (processor.frequency);
        int   pb     = s * 6;
        float outDb  = (clamp (fxP.at (pb), 0.0f, 1.0f) - 0.5f) * 36.0f;
        float gScale = clamp (fxP.at (pb + 1), 0.0f, 1.0f) * 2.0f;
        float fShift = float (pow (2.0f, (clamp (fxP.at (pb + 2), 0.0f, 1.0f) - 0.5f) * 2.0f));
        float qScale = 0.25f * float (pow (16.0f, clamp (fxP.at (pb + 3), 0.0f, 1.0f)));
        int   n      = 0;

        fxD.at (s * 16) = float (pow (10.0f, outDb / 20.0f));

        for (int b = 0; b < 24; ++b)
        {
            int ek = (s * 24 + b) * 4;
            peqK.at (ek) = 0.0f;
        }

        for (int b = 0; b < 24; ++b)
        {
            int   bi   = (s * 24 + b) * 10;

            if (peqB.at (bi) < 0.5f)
                continue;

            int   ty   = clamp (int (peqB.at (bi + 1) * 16.0f + 0.5f), 0, 14);
            float f    = clamp (20.0f * float (pow (1000.0f, clamp (peqB.at (bi + 2), 0.0f, 1.0f))) * fShift, 10.0f, sr * 0.45f);
            float g    = clamp (peqB.at (bi + 3) * 24.0f * gScale, -36.0f, 36.0f);
            float q    = clamp (0.1f * float (pow (300.0f, clamp (peqB.at (bi + 4), 0.0f, 1.0f))) * qScale, 0.05f, 40.0f);
            int   harm = clamp (int (peqB.at (bi + 5) * 16.0f + 0.5f), 0, 16);
            float fall = 0.4f + 0.6f * clamp (peqB.at (bi + 6), 0.0f, 1.0f);
            int   hset = clamp (int (peqB.at (bi + 7) * 4.0f + 0.5f), 0, 2);
            int   ch   = clamp (int (peqB.at (bi + 8) * 4.0f + 0.5f), 0, 4);

            if (ty == 0)       n = peqAddSec (s, n, 0, f, g, q, ch);
            else if (ty == 1)  n = peqAddSec (s, n, 1, f, g, q, ch);
            else if (ty == 2)  n = peqAddSec (s, n, 2, f, g, q, ch);
            else if (ty == 3)  n = peqAddSec (s, n, 3, f, 0.0f, q, ch);
            else if (ty == 4)  { float qq = q * 1.4142f; n = peqAddSec (s, n, 3, f, 0.0f, qq * 0.5412f, ch); n = peqAddSec (s, n, 3, f, 0.0f, qq * 1.3066f, ch); }
            else if (ty == 5)  n = peqAddSec (s, n, 4, f, 0.0f, q, ch);
            else if (ty == 6)  { float qq = q * 1.4142f; n = peqAddSec (s, n, 4, f, 0.0f, qq * 0.5412f, ch); n = peqAddSec (s, n, 4, f, 0.0f, qq * 1.3066f, ch); }
            else if (ty == 7)  n = peqAddSec (s, n, 5, f, g, q, ch);
            else if (ty == 8)  n = peqAddSec (s, n, 6, f, 0.0f, q, ch);
            else if (ty == 9)  { n = peqAddSec (s, n, 1, f, -g * 0.5f, 0.5f, ch); n = peqAddSec (s, n, 2, f, g * 0.5f, 0.5f, ch); }
            else if (ty == 10) n = peqAddSec (s, n, 7, f, 0.0f, q, ch);
            else if (ty == 13) { float qq = q * 1.4142f; n = peqAddSec (s, n, 3, f, 0.0f, qq * 0.5098f, ch); n = peqAddSec (s, n, 3, f, 0.0f, qq * 0.6013f, ch); n = peqAddSec (s, n, 3, f, 0.0f, qq * 0.9f, ch); n = peqAddSec (s, n, 3, f, 0.0f, qq * 2.5629f, ch); }
            else if (ty == 14) { float qq = q * 1.4142f; n = peqAddSec (s, n, 4, f, 0.0f, qq * 0.5098f, ch); n = peqAddSec (s, n, 4, f, 0.0f, qq * 0.6013f, ch); n = peqAddSec (s, n, 4, f, 0.0f, qq * 0.9f, ch); n = peqAddSec (s, n, 4, f, 0.0f, qq * 2.5629f, ch); }
            else
            {
                // comb: feed-forward (11) or feedback (12) at multiples of the frequency, the gain sets how deep / strong
                int   ek  = (s * 24 + b) * 4;
                float amt = 1.0f - float (pow (10.0f, -abs (g) / 20.0f));
                peqK.at (ek)     = (g < 0.0f ? -amt : amt) * (ty == 12 ? 0.97f : 1.0f);
                peqK.at (ek + 1) = clamp (sr / f, 2.0f, 4000.0f);
                peqK.at (ek + 2) = ty == 12 ? 1.0f : 0.0f;
                peqK.at (ek + 3) = float (ch);
            }

            if ((ty == 0 || ty == 7 || ty == 8) && harm > 0)
            {
                float hg = g;

                for (int h = 1; h <= harm; ++h)
                {
                    int k = h + 1;

                    if (hset == 1) k = 2 * h + 1;
                    if (hset == 2) k = 2 * h;

                    hg = hg * fall;
                    float hf = f * float (k);

                    if (hf > sr * 0.45f)
                        break;

                    if (ty == 8)
                        n = peqAddSec (s, n, 6, hf, 0.0f, q, ch);
                    else
                        n = peqAddSec (s, n, ty == 7 ? 5 : 0, hf, hg, q, ch);
                }
            }
        }

        peqN.at (s) = n;
    }

    float<2> fxPeq (int s, float<2> x)
    {
        int   n = peqN.at (s);
        float l = x[0];
        float r = x[1];

        for (int i = 0; i < n; ++i)
        {
            int   si = s * 64 + i;
            int   ci = si * 5;
            int   zi = si * 4;
            int   ch = peqCh.at (si);
            float b0 = peqC.at (ci);
            float b1 = peqC.at (ci + 1);
            float b2 = peqC.at (ci + 2);
            float a1 = peqC.at (ci + 3);
            float a2 = peqC.at (ci + 4);

            if (ch >= 3)
            {
                float m  = (l + r) * 0.5f;
                float sd = (l - r) * 0.5f;
                float v  = ch == 3 ? m : sd;
                int   zz = ch == 3 ? zi : zi + 2;
                float y  = b0 * v + peqZ.at (zz);
                peqZ.at (zz)     = b1 * v - a1 * y + peqZ.at (zz + 1);
                peqZ.at (zz + 1) = b2 * v - a2 * y;

                if (ch == 3) m = y; else sd = y;

                l = m + sd;
                r = m - sd;
            }
            else
            {
                if (ch != 2)
                {
                    float y = b0 * l + peqZ.at (zi);
                    peqZ.at (zi)     = b1 * l - a1 * y + peqZ.at (zi + 1);
                    peqZ.at (zi + 1) = b2 * l - a2 * y;
                    l = y;
                }

                if (ch != 1)
                {
                    float y = b0 * r + peqZ.at (zi + 2);
                    peqZ.at (zi + 2) = b1 * r - a1 * y + peqZ.at (zi + 3);
                    peqZ.at (zi + 3) = b2 * r - a2 * y;
                    r = y;
                }
            }
        }

        // combs: a delay line of 4096 samples per channel in the slot's arena, the write position of band b in fxI
        int ab = s * 196608;

        for (int b = 0; b < 24; ++b)
        {
            int   ek = (s * 24 + b) * 4;
            float cg = peqK.at (ek);

            if (cg == 0.0f)
                continue;

            int   wp = fxI.at (s * 24 + b);
            int   cb = ab + b * 8192;
            float dl = peqK.at (ek + 1);
            float fb = peqK.at (ek + 2);
            int   ch = int (peqK.at (ek + 3));
            float rp = float (wp) - dl;
            float cl = fxTapN (cb, 4096, rp);
            float cr = fxTapN (cb + 4096, 4096, rp);
            float yl = l;
            float yr = r;

            if (ch != 2) yl = l + cg * cl;
            if (ch != 1) yr = r + cg * cr;

            fxArena.at (cb + wp)        = fb > 0.5f ? yl : l;
            fxArena.at (cb + 4096 + wp) = fb > 0.5f ? yr : r;
            wp += 1;
            if (wp >= 4096) wp = 0;
            fxI.at (s * 24 + b) = wp;
            l = yl;
            r = yr;
        }

        float og = fxD.at (s * 16);
        return float<2> (l * og, r * og);
    }

    event eqLoad (BankChunk c)
    {
        int b = clamp (c.bank, 0, 29);

        if (c.total <= 0)
        {
            for (int i = 0; i < 240; ++i)
                peqB.at (b * 240 + i) = 0.0f;
        }
        else
        {
            for (int i = 0; i < min (c.count, 256); ++i)
            {
                int pos = c.offset + i;

                if (pos >= 0 && pos < 240)
                    peqB.at (b * 240 + pos) = clamp (c.data.at (i), -1.0f, 1.0f);
            }
        }

        fxDirty.at (b) = true;
    }

'''
rep('    // Clears the delay lines and filter memories of one slot\n', dsp + '    // Clears the delay lines and filter memories of one slot\n')

rep('        else if (ty == 12) y = fxConv   (s, x);\n', '        else if (ty == 12) y = fxConv   (s, x);\n        else if (ty == 13) y = fxPeq    (s, x);\n')
rep('        // FX-SYNC: the delay time follows the tempo division of the slot\n', '        if (ty == 13)\n            fxPeqDerive (s);\n\n        // FX-SYNC: the delay time follows the tempo division of the slot\n')
open(path, 'w').write(src)
print('ok')
