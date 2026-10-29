#!/usr/bin/env python3
"""Idempotent: replaces the Schroeder comb reverb (FX type 8) in patch/Eisenpuls_Synth.cmajor with two reverb engines from the open literature.
  * Zita-rev1 (Fons Adriaensen, GPL; port of the Cmajor ZitaReverb example, GPLv3): 8x8 feedback delay network with a low / mid RT60 split and high-frequency damping.
    Modes Hall, Room, Cathedral, Chamber, Dark, Bright, Infinite.
  * Dattorro plate (J. Dattorro, "Effect Design Part 1", JAES 1997): input diffusion + figure-eight tank with modulated allpasses.  Modes Plate, Ambience.
Slot parameters are unchanged (Size, Damp, PreDly, Width, Low Cut, High Cut).  Run after build_eq.py."""
import os, sys, re
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if '// FX-REV' in src:
    print('already applied'); sys.exit(0)

# ---- engine ---------------------------------------------------------------------------------------------------------------------
a = src.index('    float<2> fxReverb (int s, float<2> x)')
b = src.index("    // one channel of a state-variable filter (Cytomic TPT form); fb is the slot's float state base", a)
engine = r'''    // FX-REV: Zita-rev1 FDN (modes 0 1 3 4 6 7 8) and Dattorro plate (modes 2 5).  One sample counter (fxI[ib]) indexes every ring buffer of a slot.
    // Arena layout: Zita delay-with-feedback lines at i*4096, delay lines at 32768 + i*16384; Dattorro input allpasses at i*2048, tank lines at 8192 + k*16384;
    // pre-delay lines at 172032 / 180480; coefficient / length tables at 180224 (Zita) and 180288 (Dattorro).
    const float[8] zitaD1 = ( 20346e-6f, 24421e-6f, 31604e-6f, 27333e-6f, 22904e-6f, 29291e-6f, 13458e-6f, 19123e-6f );
    const float[8] zitaD2 = ( 153129e-6f, 210389e-6f, 127837e-6f, 256891e-6f, 174713e-6f, 192303e-6f, 125000e-6f, 219991e-6f );
    const int[26]  datLen = ( 142, 107, 379, 277, 672, 4453, 1800, 3720, 908, 4217, 2656, 3163, 266, 2974, 1913, 1996, 1990, 187, 1066, 353, 3627, 1228, 2111, 335, 121, 1990 );

    float rvRd (int base, int mask, int wp, int d)
    {
        return fxArena.at (base + ((wp - d) & mask));
    }

    void rvWr (int base, int mask, int wp, float v)
    {
        fxArena.at (base + (wp & mask)) = v;
    }

    float rvRdF (int base, int mask, int wp, float d)
    {
        int   di = int (d);
        float fr = d - float (di);
        return rvRd (base, mask, wp, di) * (1.0f - fr) + rvRd (base, mask, wp, di + 1) * fr;
    }

    // Schroeder allpass on its own line (reads the tail, writes the head)
    float rvAp (int base, int mask, int wp, int d, float g, float x)
    {
        float z = rvRd (base, mask, wp, d);
        float v = x - g * z;
        rvWr (base, mask, wp, v);
        return z + g * v;
    }

    float rvApMod (int base, int mask, int wp, float d, float g, float x)
    {
        float z = rvRdF (base, mask, wp, d);
        float v = x - g * z;
        rvWr (base, mask, wp, v);
        return z + g * v;
    }

    float<2> fxReverb (int s, float<2> x)
    {
        int   fb = s * 40;
        int   ib = s * 24;
        int   db = s * 16;
        int   ab = s * 196608;
        float dt = float (processor.period);

        float preS = fxD.at (db + 2);
        float rvW  = fxD.at (db + 3);
        int   algo = int (fxD.at (db + 4));
        float wetG = fxD.at (db + 5);
        int   wp   = fxI.at (ib);

        // DC blockers on the inputs: a DC offset would be amplified by the feedback
        float hpA   = 1.0f - clamp (float (twoPi) * 60.0f * dt, 0.0001f, 0.5f);
        float rvL   = x[0] - fxF.at (fb)      + hpA * fxF.at (fb + 1);
        float rvR   = x[1] - fxF.at (fb + 24) + hpA * fxF.at (fb + 25);
        fxF.at (fb)      = x[0];
        fxF.at (fb + 1)  = rvL;
        fxF.at (fb + 24) = x[1];
        fxF.at (fb + 25) = rvR;

        // pre-delay
        rvWr (ab + 172032, 8191, wp, rvL);
        rvWr (ab + 180480, 8191, wp, rvR);
        int   pdI = clamp (int (preS), 0, 8000);
        float pL  = rvRd (ab + 172032, 8191, wp, pdI);
        float pR  = rvRd (ab + 180480, 8191, wp, pdI);

        float tL = 0.0f;
        float tR = 0.0f;

        if (algo == 0)
        {
            // ---- Zita-rev1: 8 delay lines with allpass feedback, Hadamard mixing, per-line RT60 filters ----
            float t0 = 0.3f * pL;
            float t1 = 0.3f * pR;
            float[8] z;

            for (int i = 0; i < 8; ++i)
            {
                float tin = t0;
                if (i >= 2) tin = -t0;
                if (i >= 4) tin = t1;
                if (i >= 6) tin = -t1;

                int   k1 = int (fxArena.at (ab + 180256 + i));
                int   dl = int (fxArena.at (ab + 180264 + i));
                float c  = 0.6f;
                if ((i & 1) != 0) c = -0.6f;

                float xin = rvRd (ab + 32768 + i * 16384, 16383, wp, dl) + tin;
                float zc  = rvRd (ab + i * 4096, 4095, wp, k1);
                xin -= c * zc;
                rvWr (ab + i * 4096, 4095, wp, xin);
                z.at (i) = zc + c * xin;
            }

            for (int st = 1; st < 8; st *= 2)
            {
                for (int i = 0; i < 8; ++i)
                {
                    if ((i & st) == 0)
                    {
                        float va = z.at (i);
                        float vb = z.at (i + st);
                        z.at (i)      = va + vb;
                        z.at (i + st) = va - vb;
                    }
                }
            }

            float wl = fxArena.at (ab + 180272);
            tL = wl * (z.at (1) + z.at (2));
            tR = wl * (z.at (1) - z.at (2));

            for (int i = 0; i < 8; ++i)
            {
                float gmf = fxArena.at (ab + 180224 + i * 4);
                float glo = fxArena.at (ab + 180225 + i * 4);
                float wlo = fxArena.at (ab + 180226 + i * 4);
                float whi = fxArena.at (ab + 180227 + i * 4);
                float v   = 0.35355339f * z.at (i);
                float slo = fxF.at (fb + 6 + i * 2);
                float shi = fxF.at (fb + 7 + i * 2);
                slo += wlo * (v - slo) + 1.0e-10f;
                v   += glo * slo;
                shi += whi * (v - shi);
                fxF.at (fb + 6 + i * 2) = slo;
                fxF.at (fb + 7 + i * 2) = shi;
                rvWr (ab + 32768 + i * 16384, 16383, wp, gmf * shi);
            }
        }
        else
        {
            // ---- Dattorro plate: bandwidth, 4 input allpasses, two cross-coupled tank halves with modulated allpasses ----
            float decay = fxD.at (db + 8);
            float dmp   = fxD.at (db + 9);
            float g2    = clamp (decay + 0.15f, 0.25f, 0.5f);
            float inp   = 0.5f * (pL + pR) * 0.5f;

            float bwS = fxF.at (fb + 28);
            bwS += 0.9995f * (inp - bwS);
            fxF.at (fb + 28) = bwS;

            float d1 = rvAp (ab,        2047, wp, int (fxArena.at (ab + 180288)), 0.75f,  bwS);
            float d2 = rvAp (ab + 2048, 2047, wp, int (fxArena.at (ab + 180289)), 0.75f,  d1);
            float d3 = rvAp (ab + 4096, 2047, wp, int (fxArena.at (ab + 180290)), 0.625f, d2);
            float d4 = rvAp (ab + 6144, 2047, wp, int (fxArena.at (ab + 180291)), 0.625f, d3);

            // slow modulation of the first tank allpasses
            float64 ph0 = fxPh.at (s * 4)     + 0.9 * processor.period;
            float64 ph1 = fxPh.at (s * 4 + 1) + 1.15 * processor.period;
            if (ph0 >= 1.0) ph0 -= 1.0;
            if (ph1 >= 1.0) ph1 -= 1.0;
            fxPh.at (s * 4)     = ph0;
            fxPh.at (s * 4 + 1) = ph1;
            float exc = fxArena.at (ab + 180318);
            float mL  = exc * float (sin (float64 (twoPi) * ph0));
            float mR  = exc * float (sin (float64 (twoPi) * ph1));

            float fbL = fxF.at (fb + 22);
            float fbR = fxF.at (fb + 23);

            // left half: modulated allpass, delay, damping, allpass, delay
            float a1 = rvApMod (ab + 8192, 16383, wp, fxArena.at (ab + 180292) + mL, 0.7f, d4 + fbR);
            rvWr (ab + 24576, 16383, wp, a1);
            float e1 = rvRd (ab + 24576, 16383, wp, int (fxArena.at (ab + 180293)));
            float lpl = (1.0f - dmp) * e1 + dmp * fxF.at (fb + 26) + 1.0e-10f;
            fxF.at (fb + 26) = lpl;
            float a2 = rvAp (ab + 40960, 16383, wp, int (fxArena.at (ab + 180294)), g2, lpl * decay);
            rvWr (ab + 57344, 16383, wp, a2);
            float e2 = rvRd (ab + 57344, 16383, wp, int (fxArena.at (ab + 180295)));

            // right half
            float b1 = rvApMod (ab + 73728, 16383, wp, fxArena.at (ab + 180296) + mR, 0.7f, d4 + fbL);
            rvWr (ab + 90112, 16383, wp, b1);
            float f1 = rvRd (ab + 90112, 16383, wp, int (fxArena.at (ab + 180297)));
            float lpr = (1.0f - dmp) * f1 + dmp * fxF.at (fb + 27) + 1.0e-10f;
            fxF.at (fb + 27) = lpr;
            float b2 = rvAp (ab + 106496, 16383, wp, int (fxArena.at (ab + 180298)), g2, lpr * decay);
            rvWr (ab + 122880, 16383, wp, b2);
            float f2 = rvRd (ab + 122880, 16383, wp, int (fxArena.at (ab + 180299)));

            fxF.at (fb + 22) = e2 * decay;
            fxF.at (fb + 23) = f2 * decay;

            // output taps (Dattorro's table)
            tL = rvRd (ab + 90112, 16383, wp, int (fxArena.at (ab + 180300)))
               + rvRd (ab + 90112, 16383, wp, int (fxArena.at (ab + 180301)))
               - rvRd (ab + 106496, 16383, wp, int (fxArena.at (ab + 180302)))
               + rvRd (ab + 122880, 16383, wp, int (fxArena.at (ab + 180303)))
               - rvRd (ab + 24576, 16383, wp, int (fxArena.at (ab + 180304)))
               - rvRd (ab + 40960, 16383, wp, int (fxArena.at (ab + 180305)))
               - rvRd (ab + 57344, 16383, wp, int (fxArena.at (ab + 180306)));
            tR = rvRd (ab + 24576, 16383, wp, int (fxArena.at (ab + 180307)))
               + rvRd (ab + 24576, 16383, wp, int (fxArena.at (ab + 180308)))
               - rvRd (ab + 40960, 16383, wp, int (fxArena.at (ab + 180309)))
               + rvRd (ab + 57344, 16383, wp, int (fxArena.at (ab + 180310)))
               - rvRd (ab + 90112, 16383, wp, int (fxArena.at (ab + 180311)))
               - rvRd (ab + 106496, 16383, wp, int (fxArena.at (ab + 180312)))
               - rvRd (ab + 122880, 16383, wp, int (fxArena.at (ab + 180313)));
        }

        fxI.at (ib) = (wp + 1) & 16777215;

        float rvMid  = (tL + tR) * 0.5f;
        float rvSide = (tL - tR) * 0.5f * rvW;
        float rawL   = (rvMid + rvSide) * wetG;
        float rawR   = (rvMid - rvSide) * wetG;

        // DC blocker on the output (removes any offset left in the tail)
        float outA = 1.0f - clamp (float (twoPi) * 8.0f * dt, 0.0001f, 0.5f);
        float oL   = rawL - fxF.at (fb + 2) + outA * fxF.at (fb + 3);
        float oR   = rawR - fxF.at (fb + 4) + outA * fxF.at (fb + 5);
        fxF.at (fb + 2) = rawL;
        fxF.at (fb + 3) = oL;
        fxF.at (fb + 4) = rawR;
        fxF.at (fb + 5) = oR;

        return float<2> (x[0] + oL, x[1] + oR);
    }

'''
src = src[:a] + engine + src[b:]

# ---- derived parameters -----------------------------------------------------------------------------------------------------------
c = src.index('        else if (ty == 8)\n        {\n            // reverb: feedback, damping, pre-delay (samples), width')
d = src.index('        else if (ty == 9)', c)
derive = r'''        else if (ty == 8)
        {
            // reverb: engine and tuning per mode, pre-delay (samples), width, wet tone filters;  FX-REV
            int   md    = fxMode.at (s);
            int   ab    = s * 196608;
            float dsc   = 0.85f;      // delay length scale of the FDN
            float rtLo  = 0.6f;       // RT60 range (s) over the Size knob
            float rtHi  = 8.0f;
            float lowM  = 1.3f;       // low-frequency RT60 multiplier
            float dampM = 1.0f;
            float algo  = 0.0f;

            if (md == 1) { dsc = 0.35f; rtLo = 0.15f; rtHi = 1.3f;  lowM = 1.0f; }                  // room
            if (md == 2) { algo = 1.0f; }                                                            // plate (Dattorro)
            if (md == 3) { dsc = 1.0f;  rtLo = 2.0f;  rtHi = 16.0f; lowM = 1.5f; }                  // cathedral
            if (md == 4) { dsc = 0.55f; rtLo = 0.3f;  rtHi = 2.5f;  lowM = 1.1f; }                  // chamber
            if (md == 5) { algo = 1.0f; }                                                            // ambience (small plate)
            if (md == 6) { dsc = 0.9f;  dampM = 0.3f; lowM = 1.5f; }                                // dark hall
            if (md == 7) { dsc = 0.9f;  dampM = 3.0f; lowM = 0.9f; }                                // bright hall
            if (md == 8) { dsc = 1.0f;  rtLo = 1000.0f; rtHi = 1000.0f; lowM = 1.0f; }              // infinite

            float dampHz = clamp ((1500.0f + 22500.0f * (1.0f - p2) * (1.0f - p2)) * dampM, 800.0f, 24000.0f);

            fxD.at (db)     = 0.0f;
            fxD.at (db + 2) = clamp (p3 * 0.1f * sr, 0.0f, 8000.0f);
            fxD.at (db + 3) = p4;
            fxD.at (db + 4) = algo;
            fxD.at (db + 6) = clamp (float (twoPi) * fxExpMap (p5, 20.0f, 800.0f) * dt, 0.0f, 1.0f);       // wet low cut
            fxD.at (db + 7) = clamp (float (twoPi) * fxExpMap (clamp (fxP.at (pb + 5), 0.0f, 1.0f), 1500.0f, 20000.0f) * dt, 0.0f, 1.0f);   // wet high cut

            if (algo < 0.5f)
            {
                float rtMid = rtLo * float (pow (rtHi / rtLo, p1));
                float rtLow = rtMid * lowM;
                float wlo   = 6.2832f * 200.0f / sr;
                float chi   = 2.0f;
                if (dampHz <= 0.49f * sr) chi = 1.0f - float (cos (6.2832f * dampHz / sr));

                for (int i = 0; i < 8; ++i)
                {
                    float del = zitaD2.at (i) * dsc;
                    float gmf = float (pow (0.001f, del / rtMid));
                    float glo = float (pow (0.001f, del / rtLow)) / gmf - 1.0f;
                    float g   = float (pow (0.001f, del / (0.5f * rtMid))) / gmf;
                    float t   = (1.0f - g * g) / (2.0f * g * g * chi);
                    float whi = (sqrt (1.0f + 4.0f * t) - 1.0f) / (2.0f * t);
                    int   k1  = clamp (int (floor (zitaD1.at (i) * sr * dsc + 0.5f)), 1, 4095);
                    int   k2  = clamp (int (floor (zitaD2.at (i) * sr * dsc + 0.5f)), k1 + 1, 16383 + k1);

                    fxArena.at (ab + 180224 + i * 4) = gmf;
                    fxArena.at (ab + 180225 + i * 4) = glo;
                    fxArena.at (ab + 180226 + i * 4) = wlo;
                    fxArena.at (ab + 180227 + i * 4) = whi;
                    fxArena.at (ab + 180256 + i)     = float (k1);
                    fxArena.at (ab + 180264 + i)     = float (k2 - k1);
                }

                fxArena.at (ab + 180272) = clamp (1.0f / sqrt (rtMid), 0.22f, 1.0f);
                fxD.at (db + 5) = 1.0f;
            }
            else
            {
                float rs2 = sr / 29761.0f;
                float lsc = 0.7f + 0.6f * p1;
                float dec = 0.5f + 0.45f * p1;

                if (md == 5) { lsc = 0.3f + 0.4f * p1; dec = 0.15f + 0.5f * p1; }

                fxD.at (db + 8) = dec;
                fxD.at (db + 9) = clamp (0.9f - 0.9f * clamp (dampHz / 24000.0f, 0.0f, 1.0f) + 0.04f, 0.02f, 0.95f);
                fxD.at (db + 5) = 0.6f;

                for (int k = 0; k < 26; ++k)
                {
                    float scl = rs2;
                    if (k >= 4) scl = rs2 * lsc;
                    fxArena.at (ab + 180288 + k) = float (clamp (int (float (datLen.at (k)) * scl + 0.5f), 1, 16380));
                }

                for (int k = 0; k < 4; ++k)
                    fxArena.at (ab + 180288 + k) = float (clamp (int (float (datLen.at (k)) * rs2 + 0.5f), 1, 2040));

                fxArena.at (ab + 180292) = clamp (fxArena.at (ab + 180292), 24.0f, 16000.0f);
                fxArena.at (ab + 180296) = clamp (fxArena.at (ab + 180296), 24.0f, 16000.0f);
                fxArena.at (ab + 180318) = clamp (8.0f * rs2 * lsc, 1.0f, 20.0f);
            }
        }
'''
src = src[:c] + derive + src[d:]
open(path, 'w').write(src)
print('applied')
