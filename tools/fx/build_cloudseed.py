#!/usr/bin/env python3
"""Idempotent (marker FX-CLOUDSEED): FX type 31 "CloudSeed" - a port of the CloudSeed algorithmic reverb core
(Ghost Note Audio / Valdemar Erlingsson, MIT licence, https://github.com/GhostNoteAudio/CloudSeedCore) to the effect rack.
Signal flow as in the original: input high / low cut -> pre-delay -> multitap -> early diffuser (modulated allpass chain) -> N modulated
delay lines with feedback, a modulated allpass diffuser, low / high shelf and low-pass in every loop -> early + late output.
Differences to the original (memory per slot is 2 x 98304 floats): at most 32 taps, 6 early stages, 8 lines with 4 diffuser stages each,
delays are capped by the ring sizes (pre-delay 85 ms, taps 170 ms, line 85 ms, diffuser stage 21 ms at 48 kHz); the feedback of a line is delayed
by one sample instead of one block.  The 8 modes are own parameter sets (the internal CloudSeed parameters), the six knobs are Decay, Size, Damp,
PreDly, Mod and Early.  Run after build_mutable.py."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); IP = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-CLOUDSEED' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (t.count(old), old[:80])
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

src, n = re.subn(r'(FX \d+ (?:Type|Sync)",\s*min: 0\.0, max: )30\.0', r'\g<1>31.0', src)
assert n == 48, n
rep('int nt = clamp (t, 0, 30);', 'int nt = clamp (t, 0, 31);')
rep('        if (ty == 29)\n            fxMgDerive (s);   // FX-MUTABLE\n', '        if (ty == 29)\n            fxMgDerive (s);   // FX-MUTABLE\n\n        if (ty == 31)\n            fxCsDerive (s);   // FX-CLOUDSEED\n')
rep('        else if (ty == 30) y = fxWarp      (s, x);\n', '        else if (ty == 30) y = fxWarp      (s, x);\n        else if (ty == 31) y = fxCloudSeed (s, x);\n')
rep('    float[6144]  wpV;', '    float[49152] csV;   // FX-CLOUDSEED: per slot 1024 floats: derived coefficients (0..511) and filter / modulation states (512..1023)\n    float[128]   csTmp;\n    int64        csLcg;\n    float[6144]  wpV;')
rep('        fxFcS.at (s) = 0.0f;   // FX-FENV2\n', '        fxFcS.at (s) = 0.0f;   // FX-FENV2\n\n        for (int i = 0; i < 1024; ++i)   // FX-CLOUDSEED\n            csV.at (s * 1024 + i) = 0.0f;\n')

# ---- the mode presets (scaled units: ms, Hz, dB)
# fields: tapOn tapCount tapDecay tapLen | edOn edStages edDelay edFb edMod edRate | lines ldOn ldStages ldDelay ldFb ldMod ldRate | size lineMod lineRate post
#         lsOn lsFreq lsGain hsOn hsFreq hsGain cross seedTap seedDiff seedDelay seedPost hpOn hpFreq lpOn lpFreq lateGain
F = ['tapOn','tapCount','tapDecay','tapLen','edOn','edStages','edDelay','edFb','edMod','edRate','lines','ldOn','ldStages','ldDelay','ldFb','ldMod','ldRate',
     'size','lineMod','lineRate','post','lsOn','lsFreq','lsGain','hsOn','hsFreq','hsGain','cross','seedTap','seedDiff','seedDelay','seedPost','hpOn','hpFreq','lpOn','lpFreq','lateGain']
MODES = [
 ('Dark Plate',  [0,1,1.0,50,   0,1,10,0.77,0.36,0.6,   8,1,4,20,0.85,0.37,0.06,   40,0.68,0.095,1,   0,200,-3,1,4500,-4.6,0.0,334,185,218,365,   1,340,0,20000,0.9]),
 ('Hall',        [0,1,1.0,50,   1,4,10,0.75,0.3,0.3,    8,1,3,15,0.7,0.5,0.3,     45,1.0,0.4,1,       0,200,-3,1,6000,-3.0,0.5,123,456,789,321,   1,100,0,20000,0.9]),
 ('Room',        [1,12,0.8,40,  1,3,10,0.7,0.2,0.3,     6,1,2,10,0.65,0.3,0.3,    18,0.4,0.3,1,       0,200,-2,1,8000,-2.5,0.4,555,111,222,333,   1,80,0,20000,0.9]),
 ('Chamber',     [1,8,0.6,60,   1,4,10,0.8,0.3,0.3,     8,1,3,12,0.7,0.4,0.3,     30,0.7,0.3,1,       0,200,-2,1,7000,-5.0,0.5,246,135,579,864,   1,120,0,20000,0.9]),
 ('Cathedral',   [0,1,1.0,50,   1,5,15,0.8,0.5,0.25,    8,1,4,20,0.8,0.8,0.2,     70,1.2,0.25,1,      1,200,-3,1,5000,-5.0,0.7,654,321,987,159,   1,60,0,20000,0.9]),
 ('Cloud',       [0,1,1.0,50,   1,4,12,0.75,2.0,0.8,    8,1,4,20,0.8,2.0,1.0,     50,2.4,0.9,0,       0,200,-3,1,9000,-3.0,0.8,777,888,999,666,   1,120,0,20000,0.9]),
 ('Ambience',    [1,24,0.5,80,  1,2,8,0.7,0.2,0.3,      4,1,2,8,0.6,0.3,0.3,      20,0.5,0.3,1,       0,200,-2,1,9000,-2.0,0.3,101,202,303,404,   1,150,0,20000,0.9]),
 ('Echo Space',  [1,6,0.2,170,  1,1,8,0.7,0.2,0.3,      8,1,2,10,0.7,0.4,0.3,     50,0.8,0.3,1,       0,200,-3,1,7000,-4.0,0.6,13,57,91,135,      1,100,0,20000,0.9]),
]
NF = len(F); assert all(len(m[1]) == NF for m in MODES), [len(m[1]) for m in MODES]
TABLE = ', '.join(repr(float(v)) + 'f' for m in MODES for v in m[1])
fi = {n: i for i, n in enumerate(F)}

CODE = r'''    // ================= FX-CLOUDSEED: CloudSeed reverb (FX type 31) =================
    // Arena (per channel, 98304 floats at ab + c * 98304): pre-delay 0 (4096), multitap 4096 (8192), early diffuser 12288 (6 x 1024), lines 18432 (8 x 4096),
    // late diffusers 51200 (8 x 4 x 1024).  One sample counter (fxI[s * 24 + 8]) indexes every ring.
    // csV per slot: derived 0..511 (per channel c: tap offsets 0-31, tap gains 32-63, modulation base 64-109, amount 110-155, rate 156-201 for the units
    // 0-5 early stages, 6-13 lines, 14-45 late stages; line feedback 202-209), global 440..); states 512..1023 (per channel 256: input filters 0-1, phases 2-47,
    // current delays 48-93, line feedback 94-101, low shelf 102-133, high shelf 134-165, low-pass 166-173).
    const float[__TABLE_LEN__] csModes = ( __TABLE__ );

    float csRnd()
    {
        csLcg = (csLcg * 22695477 + 1) & 4294967295L;
        return float (csLcg) / 4294967295.0f;
    }

    // RandomBuffer.Generate (seed, count, crossSeed): two LCG series (seed and ~seed) blended by the cross seed
    void csFill (int seed, int count, float cross)
    {
        csLcg = int64 (seed);

        for (int i = 0; i < count; ++i)
            csTmp.at (i) = csRnd() * (1.0f - cross);

        csLcg = 4294967295L - int64 (seed);

        for (int i = 0; i < count; ++i)
            csTmp.at (i) = csTmp.at (i) + csRnd() * cross;
    }

    float csDb (float d)
    {
        return float (pow (10.0f, d * 0.05f));
    }

    // low / high shelf coefficients (CloudSeed Biquad): b0 b1 b2 a1 a2 into csV at o
    void csShelf (int o, bool high, float fc, float gdb, float sr)
    {
        float V = float (pow (10.0f, abs (gdb) / 20.0f));
        float K = float (tan (3.14159265f * min (fc, sr * 0.45f) / sr));
        float s2 = 1.41421356f, sv = sqrt (2.0f * V);
        float b0, b1, b2, a1, a2, nm;

        if (! high)
        {
            if (gdb >= 0.0f)
            {
                nm = 1.0f / (1.0f + s2 * K + K * K);
                b0 = (1.0f + sv * K + V * K * K) * nm;  b1 = 2.0f * (V * K * K - 1.0f) * nm;  b2 = (1.0f - sv * K + V * K * K) * nm;
                a1 = 2.0f * (K * K - 1.0f) * nm;        a2 = (1.0f - s2 * K + K * K) * nm;
            }
            else
            {
                nm = 1.0f / (1.0f + sv * K + V * K * K);
                b0 = (1.0f + s2 * K + K * K) * nm;      b1 = 2.0f * (K * K - 1.0f) * nm;      b2 = (1.0f - s2 * K + K * K) * nm;
                a1 = 2.0f * (V * K * K - 1.0f) * nm;    a2 = (1.0f - sv * K + V * K * K) * nm;
            }
        }
        else
        {
            if (gdb >= 0.0f)
            {
                nm = 1.0f / (1.0f + s2 * K + K * K);
                b0 = (V + sv * K + K * K) * nm;         b1 = 2.0f * (K * K - V) * nm;         b2 = (V - sv * K + K * K) * nm;
                a1 = 2.0f * (K * K - 1.0f) * nm;        a2 = (1.0f - s2 * K + K * K) * nm;
            }
            else
            {
                nm = 1.0f / (V + sv * K + K * K);
                b0 = (1.0f + s2 * K + K * K) * nm;      b1 = 2.0f * (K * K - 1.0f) * nm;      b2 = (1.0f - s2 * K + K * K) * nm;
                a1 = 2.0f * (K * K - V) * nm;           a2 = (V - sv * K + K * K) * nm;
            }
        }

        csV.at (o) = b0;  csV.at (o + 1) = b1;  csV.at (o + 2) = b2;  csV.at (o + 3) = a1;  csV.at (o + 4) = a2;
    }

    // one-pole coefficient of CloudSeed's Lp1 / Hp1: a1 and b0 = 1 - a1
    float csPoleA (float hz, float sr)
    {
        float x  = 6.2831853f * min (hz, sr * 0.499f) / sr;
        float nn = 2.0f - cos (x);
        return nn - sqrt (nn * nn - 1.0f);
    }

    void fxCsDerive (int s)
    {
        float sr  = float (processor.frequency);
        int   D   = s * 1024;
        int   pb  = s * 6;
        int   md  = clamp (fxMode.at (s), 0, __NMODES__ - 1);
        int   mo  = md * __NF__;
        float p1  = clamp (fxP.at (pb),     0.0f, 1.0f);
        float p2  = clamp (fxP.at (pb + 1), 0.0f, 1.0f);
        float p3  = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float p4  = clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float p5  = clamp (fxP.at (pb + 4), 0.0f, 1.0f);
        float p6  = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        float ms  = sr * 0.001f;
        float sz  = 0.4f + 1.6f * p2;
        float modS = p5 * 2.0f;
        float decay = fxExpMap (p1, 0.2f, 30.0f);
        int   lines = clamp (int (csModes.at (mo + __lines__)), 1, 8);
        int   edSt  = clamp (int (csModes.at (mo + __edStages__)), 1, 6);
        int   ldSt  = clamp (int (csModes.at (mo + __ldStages__)), 1, 4);
        int   nTaps = clamp (int (csModes.at (mo + __tapCount__)), 1, 32);
        int   fl    = 0;

        if (csModes.at (mo + __tapOn__) > 0.5f)   fl += 1;
        if (csModes.at (mo + __edOn__) > 0.5f)    fl += 2;
        if (csModes.at (mo + __ldOn__) > 0.5f)    fl += 4;
        if (csModes.at (mo + __post__) > 0.5f)    fl += 8;
        if (csModes.at (mo + __lsOn__) > 0.5f)    fl += 16;
        if (csModes.at (mo + __hsOn__) > 0.5f)    fl += 32;
        fl += 64;                                                                                  // loop low-pass (Damp)
        if (csModes.at (mo + __hpOn__) > 0.5f)    fl += 128;
        if (csModes.at (mo + __lpOn__) > 0.5f)    fl += 256;

        int G = D + 440;
        csV.at (G)      = min (p4 * 80.0f * ms, 4000.0f);                                       // pre-delay samples
        csV.at (G + 1)  = csPoleA (csModes.at (mo + __hpFreq__), sr);
        csV.at (G + 3)  = csPoleA (csModes.at (mo + __lpFreq__), sr);
        csV.at (G + 5)  = csPoleA (fxExpMap (1.0f - p3, 1500.0f, 20000.0f), sr);                 // loop low-pass
        csShelf (G + 7,  false, csModes.at (mo + __lsFreq__), csModes.at (mo + __lsGain__), sr);
        csShelf (G + 12, true,  csModes.at (mo + __hsFreq__), csModes.at (mo + __hsGain__), sr);
        csV.at (G + 17) = p6 * 1.5f;                                                             // early level
        csV.at (G + 18) = csModes.at (mo + __lateGain__);                                        // late level
        csV.at (G + 19) = 1.0f / sqrt (float (lines));                                           // per-line gain
        csV.at (G + 20) = float (fl);
        csV.at (G + 21) = float (edSt);
        csV.at (G + 22) = float (lines);
        csV.at (G + 23) = float (ldSt);
        csV.at (G + 24) = float (nTaps);
        csV.at (G + 25) = csModes.at (mo + __edFb__);
        csV.at (G + 26) = csModes.at (mo + __ldFb__);

        float cross = csModes.at (mo + __cross__);
        float tapLen = clamp (csModes.at (mo + __tapLen__) * ms, 10.0f, 8190.0f);
        float tapDec = csModes.at (mo + __tapDecay__);
        float edDel  = csModes.at (mo + __edDelay__) * sz * ms;
        float edAmt  = csModes.at (mo + __edMod__) * modS * ms;
        float edRate = csModes.at (mo + __edRate__);
        float ldDel  = csModes.at (mo + __ldDelay__) * sz * ms;
        float ldAmt  = csModes.at (mo + __ldMod__) * modS * ms;
        float ldRate = csModes.at (mo + __ldRate__);
        float lnSize = csModes.at (mo + __size__) * sz * ms;
        float lnAmt  = csModes.at (mo + __lineMod__) * modS * ms;
        float lnRate = csModes.at (mo + __lineRate__);
        float decSamp = decay * sr;

        for (int c = 0; c < 2; ++c)
        {
            int   Dc = D + c * 220;
            float cs = c == 1 ? 0.5f * cross : 1.0f - 0.5f * cross;

            // multitap
            csFill (int (csModes.at (mo + __seedTap__)), 96, cs);
            float lenSc = tapLen / float (nTaps);
            float totG  = 3.0f / sqrt (1.0f + float (nTaps)) * (1.0f + tapDec * 2.0f);

            for (int j = 0; j < 32; ++j)
            {
                float ph  = csTmp.at (j * 3) < 0.5f ? 1.0f : -1.0f;
                float g   = csDb (-20.0f + csTmp.at (j * 3 + 1) * 20.0f) * ph;
                float off = (float (j) + csTmp.at (j * 3 + 2)) * lenSc;
                float de  = float (exp (-off / tapLen * 3.3f)) * tapDec + (1.0f - tapDec);
                csV.at (Dc + j)      = float (clamp (int (off), 0, 8190));
                csV.at (Dc + 32 + j) = j < nTaps ? g * de * totG : 0.0f;
            }

            // early diffuser
            csFill (int (csModes.at (mo + __seedDiff__)), 36, cs);

            for (int k = 0; k < 6; ++k)
            {
                float d = float (clamp (int (edDel * float (pow (10.0f, csTmp.at (k)) * 0.1f)), 2, 1000));
                float a = min (min (edAmt * (0.85f + 0.3f * csTmp.at (12 + k)), d - 1.0f), 1015.0f - d);
                csV.at (Dc + 64 + k)  = d;
                csV.at (Dc + 110 + k) = csModes.at (mo + __edMod__) * modS > 0.5f ? max (a, 0.0f) : 0.0f;
                csV.at (Dc + 156 + k) = edRate * (0.85f + 0.3f * csTmp.at (24 + k)) / sr;
            }

            // late lines
            csFill (int (csModes.at (mo + __seedDelay__)), 36, cs);

            for (int i = 0; i < 8; ++i)
            {
                float a  = lnAmt * (0.7f + 0.3f * csTmp.at (i));
                float r  = lnRate * (0.7f + 0.3f * csTmp.at (12 + i)) / sr;
                float d  = (0.5f + csTmp.at (24 + i)) * lnSize;
                d = max (d, a + 2.0f);
                d = min (d, 4090.0f - a);
                a = min (a, max (d - 2.0f, 0.0f));
                float fb = csDb (d / decSamp * -60.0f);
                csV.at (Dc + 70 + 0 * 0 + 0) = csV.at (Dc + 70);   // (keeps the compiler from folding the index)
                csV.at (Dc + 64 + 6 + i)  = float (int (d));
                csV.at (Dc + 110 + 6 + i) = a;
                csV.at (Dc + 156 + 6 + i) = r;
                csV.at (Dc + 202 + i)     = fb;
            }

            // late diffusers (one seed series per line)
            for (int i = 0; i < 8; ++i)
            {
                csFill (int (csModes.at (mo + __seedPost__)) * (i + 1), 36, cs);

                for (int k = 0; k < 4; ++k)
                {
                    int   u = 14 + i * 4 + k;
                    float d = float (clamp (int (ldDel * float (pow (10.0f, csTmp.at (k)) * 0.1f)), 2, 1000));
                    float a = min (min (ldAmt * (0.85f + 0.3f * csTmp.at (12 + k)), d - 1.0f), 1015.0f - d);
                    csV.at (Dc + 64 + u)  = d;
                    csV.at (Dc + 110 + u) = max (a, 0.0f);
                    csV.at (Dc + 156 + u) = ldRate * (0.85f + 0.3f * csTmp.at (24 + k)) / sr;
                }
            }
        }

        // phases and current delays start at once (first derive of the slot)
        for (int c = 0; c < 2; ++c)
        {
            int Sc = s * 1024 + 512 + c * 256;
            int Dc = D + c * 220;

            for (int u = 0; u < 46; ++u)
            {
                if (csV.at (Sc + 2 + u) == 0.0f)
                    csV.at (Sc + 2 + u) = 0.6180339f * float (u + 1 + c * 7) - floor (0.6180339f * float (u + 1 + c * 7));

                csV.at (Sc + 48 + u) = max (csV.at (Dc + 64 + u), 1.0f);
            }
        }
    }

    // modulated allpass (CloudSeed ModulatedAllpass): unit u, ring at base with mask, feedback gain fbk
    float csAp (int base, int mask, int wp, int Sc, int u, float v, float fbk)
    {
        float tot = min (csV.at (Sc + 48 + u), float (mask - 3));
        int   dA  = int (tot);
        float fr  = tot - float (dA);
        float bo  = rvRd (base, mask, wp, dA) * (1.0f - fr) + rvRd (base, mask, wp, dA + 1) * fr;
        float iv  = v + bo * fbk;
        rvWr (base, mask, wp, iv);
        return bo - iv * fbk;
    }

    // one channel of the reverb; returns (early, late)
    float<2> csChan (int s, int c, float x, int wp)
    {
        int D  = s * 1024;
        int Dc = D + c * 220;
        int G  = D + 440;
        int Sc = D + 512 + c * 256;
        int cb = s * 196608 + c * 98304;
        int fl = int (csV.at (G + 20));
        float v = x;

        // modulation update every 8 samples
        if ((wp & 7) == 0)
        {
            for (int u = 0; u < 46; ++u)
            {
                float a = csV.at (Dc + 110 + u);

                if (a > 0.0f)
                {
                    float ph = csV.at (Sc + 2 + u) + csV.at (Dc + 156 + u) * 8.0f;
                    ph = ph - floor (ph);
                    csV.at (Sc + 2 + u)  = ph;
                    csV.at (Sc + 48 + u) = max (csV.at (Dc + 64 + u) + a * sin (6.2831853f * ph), 1.0f);
                }
            }
        }

        if ((fl & 128) != 0)
        {
            float lo = csV.at (Sc) * csV.at (G + 1) + v * (1.0f - csV.at (G + 1));
            csV.at (Sc) = lo;
            v = v - lo;
        }

        if ((fl & 256) != 0)
        {
            float lo = csV.at (Sc + 1) * csV.at (G + 3) + v * (1.0f - csV.at (G + 3));
            csV.at (Sc + 1) = lo;
            v = lo;
        }

        if (v * v < 0.000000001f)
            v = 0.0f;

        // pre-delay
        rvWr (cb, 4095, wp, v);
        v = rvRd (cb, 4095, wp, int (csV.at (G)));

        // multitap
        if ((fl & 1) != 0)
        {
            rvWr (cb + 4096, 8191, wp, v);
            float acc = 0.0f;
            int   nt  = int (csV.at (G + 24));

            for (int j = 0; j < nt; ++j)
                acc += rvRd (cb + 4096, 8191, wp, int (csV.at (Dc + j))) * csV.at (Dc + 32 + j);

            v = acc;
        }

        // early diffuser
        if ((fl & 2) != 0)
        {
            int ns = int (csV.at (G + 21));

            for (int k = 0; k < ns; ++k)
                v = csAp (cb + 12288 + k * 1024, 1023, wp, Sc, k, v, csV.at (G + 25));
        }

        float eo = v;
        float sum = 0.0f;
        int   nl = int (csV.at (G + 22));
        int   ld = int (csV.at (G + 23));
        bool  post = (fl & 8) != 0;

        for (int i = 0; i < nl; ++i)
        {
            int   lb  = cb + 18432 + i * 4096;
            float tmp = eo + csV.at (Sc + 94 + i) * csV.at (Dc + 202 + i);
            rvWr (lb, 4095, wp, tmp);
            float tot = csV.at (Sc + 48 + 6 + i);
            int   dA  = int (tot);
            float fr  = tot - float (dA);
            float y   = rvRd (lb, 4095, wp, dA) * (1.0f - fr) + rvRd (lb, 4095, wp, dA + 1) * fr;
            float tapped = y;

            if ((fl & 4) != 0)
                for (int k = 0; k < ld; ++k)
                    y = csAp (cb + 51200 + (i * 4 + k) * 1024, 1023, wp, Sc, 14 + i * 4 + k, y, csV.at (G + 26));

            if ((fl & 16) != 0)
            {
                int   o  = Sc + 102 + i * 4;
                int   cf = G + 7;
                float yy = csV.at (cf) * y + csV.at (cf + 1) * csV.at (o) + csV.at (cf + 2) * csV.at (o + 1) - csV.at (cf + 3) * csV.at (o + 2) - csV.at (cf + 4) * csV.at (o + 3);
                csV.at (o + 1) = csV.at (o);  csV.at (o) = y;  csV.at (o + 3) = csV.at (o + 2);  csV.at (o + 2) = yy;
                y = yy;
            }

            if ((fl & 32) != 0)
            {
                int   o  = Sc + 134 + i * 4;
                int   cf = G + 12;
                float yy = csV.at (cf) * y + csV.at (cf + 1) * csV.at (o) + csV.at (cf + 2) * csV.at (o + 1) - csV.at (cf + 3) * csV.at (o + 2) - csV.at (cf + 4) * csV.at (o + 3);
                csV.at (o + 1) = csV.at (o);  csV.at (o) = y;  csV.at (o + 3) = csV.at (o + 2);  csV.at (o + 2) = yy;
                y = yy;
            }

            float lp = csV.at (Sc + 166 + i) * csV.at (G + 5) + y * (1.0f - csV.at (G + 5));
            csV.at (Sc + 166 + i) = lp;
            y = lp;
            csV.at (Sc + 94 + i) = clamp (y, -8.0f, 8.0f);
            sum += post ? y : tapped;
        }

        return float<2> (eo, sum * csV.at (G + 19));
    }

    float<2> fxCloudSeed (int s, float<2> x)
    {
        int   ib = s * 24 + 8;
        int   G  = s * 1024 + 440;
        int   wp = fxI.at (ib);
        float<2> l = csChan (s, 0, x[0], wp);
        float<2> r = csChan (s, 1, x[1], wp);
        fxI.at (ib) = (wp + 1) & 1073741823;
        float eg = csV.at (G + 17), lg = csV.at (G + 18);
        return float<2> (clamp (l[0] * eg + l[1] * lg, -4.0f, 4.0f), clamp (r[0] * eg + r[1] * lg, -4.0f, 4.0f));
    }

'''
for n_, i_ in fi.items():
    CODE = CODE.replace('__%s__' % n_, str(i_))
CODE = CODE.replace('__TABLE_LEN__', str(len(MODES) * NF)).replace('__TABLE__', TABLE).replace('__NMODES__', str(len(MODES))).replace('__NF__', str(NF))
# drop the leftover no-op line
CODE = CODE.replace('                csV.at (Dc + 70 + 0 * 0 + 0) = csV.at (Dc + 70);   // (keeps the compiler from folding the index)\n', '')
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')

# ---- UI spec
m = re.search(r'\n\];\n// the three racks', idx); assert m
entry = '''
    // FX-CLOUDSEED: port of the CloudSeed reverb core (Ghost Note Audio, MIT licence), FX type 31
    { n: "CloudSeed", mix: 0.3, modes: %s,
      p: [["Decay", fxMs(200, 30000), 0.45], ["Size", fxPct, 0.5], ["Damp", fxPct, 0.4], ["PreDly", fxLin(0, 80, 0, "ms"), 0.1], ["Mod", fxPct, 0.3], ["Early", fxPct, 0.3]] },''' % ('[' + ', '.join('"%s"' % m_[0] for m_ in MODES) + ']')
idx = idx[:m.start()] + ',' + entry + idx[m.start():]
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('FX-CLOUDSEED applied')
