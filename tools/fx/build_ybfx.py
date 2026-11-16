#!/usr/bin/env python3
"""Idempotent (marker FX-YAYBAHAR): FX type 33 "Yaybahar" - own implementation of the principle of Gorkem Sen's instrument:
 string loop (the input bows / excites it)  ->  long spring waveguide (delay line with dispersion = 4 first-order all-passes, damping, feedback)  ->  membrane resonator
 (6 parallel resonant modes at the ratios of a circular membrane 1, 1.59, 2.14, 2.30, 2.65, 2.92).
 Modes: 0 Single Spring, 1 Dual Spring (second spring 1.37 x as long, L/R spread), 2 Deep (dual spring, big membrane: tuned 0.6 x lower).
 Knobs: Pitch (string 40 Hz - 800 Hz), Spring (length 20 - 250 ms), Decay (string / spring feedback and membrane ring time), Disper (spring dispersion: the chirpy "boing"),
        Membran (fundamental 40 - 250 Hz), Damp (loop low-pass 500 Hz - 8 kHz).
 Only for slots with a big arena (Bus / Main racks, not the per voice slots of the oscillator racks)."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); IP = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-YAYBAHAR' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )32\.0', r'\g<1>33.0', src)
assert n == 144, n
src, n = re.subn(r'(Euro M\d+ FX Type", min: 0\.0, max: )32\.0', r'\g<1>33.0', src)
assert n == 20, n
rep('int nt = clamp (t, 0, 32);', 'int nt = clamp (t, 0, 33);')
rep('        if (ty == 32)\n            fxWgDerive (s);   // FX-WAVEGUIDE\n', '        if (ty == 32)\n            fxWgDerive (s);   // FX-WAVEGUIDE\n\n        if (ty == 33 && s < 48)\n            fxYbDerive (s);   // FX-YAYBAHAR\n')
rep('        else if (ty == 32) y = fxWaveguide (s, x);\n', '        else if (ty == 32) y = fxWaveguide (s, x);\n        else if (ty == 33) y = s < 48 ? fxYaybahar (s, x) : x;   // FX-YAYBAHAR: needs the big arena of the rack slots\n')

CODE = r'''    // ================= FX-YAYBAHAR: string -> spring waveguide -> membrane resonator (FX type 33) =================
    // Arena of the slot (196608 floats): string rings (channel c at c * 8192, 8192 long), spring rings at 16384 + (c * 2 + j) * 32768 (32768 long).
    // fxI: s * 24 string position, + 1 spring position.   fxF (s * 40): 0..1 string low-pass, 2..5 spring low-pass (c * 2 + j), 6..21 dispersion all-pass states ((c * 2 + j) * 4 + stage).
    // fxD (s * 16): 0..1 string delay L / R, 2 string loop gain, 3 string low-pass, 4 input gain, 5..8 spring delay (c * 2 + j), 9 spring gain, 10 spring low-pass, 11 all-pass coefficient,
    //               12 springs, 13 output gain of the spring.
    // csV (s * 1024): 0..23 membrane modes (c1, c2, b, spare) x 6, states from 512 (per channel and mode y1, y2).
    void fxYbDerive (int s)
    {
        float sr   = float (processor.frequency);
        int   db   = s * 16;
        int   pb   = s * 6;
        int   cb   = s * 1024;
        int   md   = clamp (fxMode.at (s), 0, 2);
        float f    = 40.0f * float (pow (20.0f, clamp (fxP.at (pb), 0.0f, 1.0f)));
        float sprT = 0.02f * float (pow (12.5f, clamp (fxP.at (pb + 1), 0.0f, 1.0f)));
        float dec  = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float disp = 0.75f * clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float fm   = 40.0f * float (pow (6.25f, clamp (fxP.at (pb + 4), 0.0f, 1.0f))) * (md == 2 ? 0.6f : 1.0f);
        float fc   = 500.0f * float (pow (16.0f, clamp (fxP.at (pb + 5), 0.0f, 1.0f)));
        float aSp  = float (exp (-6.2831853f * min (fc, sr * 0.45f) / sr));
        float aSt  = float (exp (-6.2831853f * min (fc * 2.0f, sr * 0.45f) / sr));
        float t60  = 0.2f * float (pow (30.0f, dec));
        float fS   = clamp (f, 20.0f, sr * 0.2f);
        float T    = sr / fS;
        float w0   = 6.2831853f * fS / sr;
        float d    = clamp (T - wgLpDelay (aSt, w0), 4.0f, 8000.0f);

        fxD.at (db)     = d;
        fxD.at (db + 1) = clamp (d * 1.004f, 4.0f, 8000.0f);
        fxD.at (db + 2) = min (float (exp (-6.9078f * T / (sr * t60))) / wgLpGain (aSt, w0), 0.9998f);
        fxD.at (db + 3) = aSt;
        fxD.at (db + 4) = 0.5f;

        for (int c = 0; c < 2; ++c)
            for (int j = 0; j < 2; ++j)
            {
                float len = sprT * (j == 1 ? 1.37f : 1.0f) * (c == 1 ? 1.07f : 1.0f);
                fxD.at (db + 5 + c * 2 + j) = clamp (len * sr, 16.0f, 30000.0f);
            }

        fxD.at (db + 9)  = 0.55f + 0.42f * dec;
        fxD.at (db + 10) = aSp;
        fxD.at (db + 11) = disp;
        fxD.at (db + 12) = md == 0 ? 1.0f : 2.0f;
        fxD.at (db + 13) = md == 0 ? 2.0f : 1.5f;
        float t60m = 0.4f + 2.5f * dec;

        for (int k = 0; k < 6; ++k)
        {
            float ratio = k == 0 ? 1.0f : (k == 1 ? 1.593f : (k == 2 ? 2.136f : (k == 3 ? 2.296f : (k == 4 ? 2.653f : 2.918f))));
            float fk    = fm * ratio;
            float tk    = t60m / (1.0f + 0.35f * float (k));
            float r     = float (exp (-6.9078f / (tk * sr)));
            float w     = 6.2831853f * fk / sr;
            bool  ok    = fk < sr * 0.45f;
            csV.at (cb + k * 4)     = ok ? 2.0f * r * float (cos (w)) : 0.0f;
            csV.at (cb + k * 4 + 1) = ok ? r * r : 0.0f;
            csV.at (cb + k * 4 + 2) = ok ? (1.0f - r) * float (sin (w)) * 14.0f / (1.0f + 0.5f * float (k)) : 0.0f;
        }
    }

    float<2> fxYaybahar (int s, float<2> x)
    {
        int   ab  = fxAb (s);
        int   ib  = s * 24;
        int   db  = s * 16;
        int   fb  = s * 40;
        int   cb  = s * 1024;
        int   sp  = fxI.at (ib);
        int   pp  = fxI.at (ib + 1);
        int   ns  = int (fxD.at (db + 12) + 0.5f);
        float aSt = fxD.at (db + 3);
        float gSt = fxD.at (db + 2);
        float ing = fxD.at (db + 4);
        float gSp = fxD.at (db + 9);
        float aSp = fxD.at (db + 10);
        float aAp = fxD.at (db + 11);
        float og  = fxD.at (db + 13);
        float<2> o = float<2> (0.0f, 0.0f);

        for (int c = 0; c < 2; ++c)
        {
            // string loop
            int   sb = ab + c * 8192;
            float rp = float (sp) - fxD.at (db + c);
            int   i0 = int (floor (rp));
            float fr = rp - float (i0);
            float ys = fxArena.at (sb + (i0 & 8191)) * (1.0f - fr) + fxArena.at (sb + ((i0 + 1) & 8191)) * fr;
            float lp = (1.0f - aSt) * ys + aSt * fxF.at (fb + c);
            fxF.at (fb + c) = lp;
            fxArena.at (sb + (sp & 8191)) = clamp (x[c] * ing + lp * gSt, -8.0f, 8.0f);

            // spring(s)
            float sprOut = 0.0f;

            for (int j = 0; j < ns; ++j)
            {
                int   k   = c * 2 + j;
                int   pb  = ab + 16384 + k * 32768;
                float rq  = float (pp) - fxD.at (db + 5 + k);
                int   q0  = int (floor (rq));
                float qf  = rq - float (q0);
                float y   = fxArena.at (pb + (q0 & 32767)) * (1.0f - qf) + fxArena.at (pb + ((q0 + 1) & 32767)) * qf;

                for (int st = 0; st < 4; ++st)   // dispersion: the low frequencies arrive later
                {
                    int   ai = fb + 6 + k * 4 + st;
                    float yo = -aAp * y + fxF.at (ai);
                    fxF.at (ai) = clamp (y + aAp * yo, -16.0f, 16.0f);
                    y = yo;
                }

                float ls = (1.0f - aSp) * y + aSp * fxF.at (fb + 2 + k);
                fxF.at (fb + 2 + k) = ls;
                fxArena.at (pb + (pp & 32767)) = clamp (ys * 0.7f + ls * gSp, -8.0f, 8.0f);
                sprOut += ls;
            }

            sprOut *= og;

            // membrane
            float mem = 0.0f;

            for (int k = 0; k < 6; ++k)
            {
                int   mi = cb + 512 + (c * 6 + k) * 2;
                float yv = csV.at (cb + k * 4) * csV.at (mi) - csV.at (cb + k * 4 + 1) * csV.at (mi + 1) + csV.at (cb + k * 4 + 2) * sprOut;
                yv = clamp (yv, -16.0f, 16.0f);
                csV.at (mi + 1) = csV.at (mi);
                csV.at (mi)     = yv;
                mem += yv;
            }

            o[c] = float (tanh (sprOut * 0.7f + mem * 0.8f));
        }

        fxI.at (ib)     = (sp + 1) & 8191;
        fxI.at (ib + 1) = (pp + 1) & 32767;
        return o;
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')

entry = '''    // FX-YAYBAHAR: string -> spring waveguide -> membrane resonator (FX type 33)
    { n: "Yaybahar", mix: 0.6, modes: ["Single Spring", "Dual Spring", "Deep"],
      p: [["Pitch", fxHz(40, 800), 0.4], ["Spring", fxMs(20, 250), 0.5], ["Decay", fxPct, 0.5], ["Disper", fxPct, 0.5], ["Membran", fxHz(40, 250), 0.35], ["Damp", fxHz(500, 8000), 0.6]] },
'''
m = re.search(r'\n\];\n// the three racks', idx); assert m
idx = idx[:m.start() + 1] + entry + idx[m.start() + 1:]
rep('L.push([b + 18, n + " FX Type", 0, 32, 0,', 'L.push([b + 18, n + " FX Type", 0, FX_TYPES.length - 1, 0,', 'idx')
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('FX-YAYBAHAR applied')
