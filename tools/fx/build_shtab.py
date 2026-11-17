#!/usr/bin/env python3
"""Idempotent, marker FX-SHTAB: FX type 34 "Shaper Table": a distortion whose transfer curve is a frame of the shaper table of an oscillator
(the same tables as Wavedistortion: 16 built-in frames, or the table loaded on the oscillator's DIST page).
 Drive 0-36 dB, Pos (table position, morphs between the frames), Table (oscillator 1-6), Bias, Tone (low-pass 500 Hz - 20 kHz), Level (-24..+12 dB).
 Modes: Clip (input limited to -1..1), Fold (triangle fold back), Wrap (wraps around), Rect (rectified input reads the upper half of the curve: even symmetric, octave up).
 2x oversampled, DC blocker after the shaper.   build_shtab.py [patch dir]"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-SHTAB' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
NT = 34
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )33\.0', r'\g<1>%d.0' % NT, src); assert n == 144, n
src, n = re.subn(r'(Euro M\d+ FX Type", min: 0\.0, max: )33\.0', r'\g<1>%d.0' % NT, src); assert n == 20, n
rep('int nt = clamp (t, 0, 33);', 'int nt = clamp (t, 0, %d);' % NT)
rep('        else if (ty == 33) y = s < 48 ? fxYaybahar (s, x) : x;', '        else if (ty == 34) y = s < 48 ? fxShTab (s, x) : x;   // FX-SHTAB\n        else if (ty == 33) y = s < 48 ? fxYaybahar (s, x) : x;')
rep('        else if (ty == 10)\n        {\n            // EQ: low shelf 100 Hz,', '''        else if (ty == 34)
        {
            // FX-SHTAB: drive gain, table position, table bank (shaper table of oscillator 1..6 = bank 6..11), bias, tone low-pass coefficient, level
            fxD.at (db)     = float (pow (10.0f, p1 * 36.0f / 20.0f));
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = float (6 + clamp (int (p3 * 5.0f + 0.5f), 0, 5));
            fxD.at (db + 3) = (p4 - 0.5f);
            fxD.at (db + 4) = clamp (float (twoPi) * fxExpMap (p5, 500.0f, 20000.0f) * dt, 0.0f, 1.0f);
            fxD.at (db + 5) = float (pow (10.0f, (clamp (fxP.at (pb + 5), 0.0f, 1.0f) * 36.0f - 24.0f) / 20.0f));
        }
        else if (ty == 10)
        {
            // EQ: low shelf 100 Hz,''')
CODE = '''    // ================= FX-SHTAB: Shaper Table distortion (FX type 34) =================
    // one read of the transfer curve (shaper table of an oscillator): v = input after drive and bias, m = mode
    float fxShRead (int bank, float pos, float v, int m)
    {
        float w = v;

        if (m == 0)
            w = clamp (v, -1.0f, 1.0f);
        else if (m == 1)
        {
            float t = v * 0.25f + 0.25f;
            t -= float (floor (t));
            w = 1.0f - 4.0f * abs (t - 0.5f);
        }
        else if (m == 2)
        {
            float t = (v + 1.0f) * 0.5f;
            t -= float (floor (t));
            w = t * 2.0f - 1.0f;
        }
        else
        {
            float h = tblRead (bank, pos, 0.5f + 0.5f * min (abs (v), 1.0f));
            return h;   // Rect: the upper half of the curve for |v|, even symmetric (octave up)
        }

        return tblRead (bank, pos, w * 0.5f + 0.5f);
    }

    float<2> fxShTab (int s, float<2> x)
    {
        int   db   = s * 16;
        int   fb   = s * 40;
        int   md   = fxMode.at (s);
        float drv  = fxD.at (db);
        float pos  = fxD.at (db + 1);
        int   bank = int (fxD.at (db + 2) + 0.5f);
        float bias = fxD.at (db + 3);
        float lpc  = fxD.at (db + 4);
        float lvl  = fxD.at (db + 5);
        float<2> o;

        for (int c = 0; c < 2; ++c)
        {
            int   cb  = fb + c * 8;
            float xin = x[c];
            float xp  = fxF.at (cb);
            fxF.at (cb) = xin;

            float y  = 0.5f * (fxShRead (bank, pos, (xp + xin) * 0.5f * drv + bias, md) + fxShRead (bank, pos, xin * drv + bias, md));
            float dc = fxF.at (cb + 1);
            dc += 0.0013f * (y - dc);
            fxF.at (cb + 1) = dc;
            y -= dc;
            float ls = fxF.at (cb + 2);
            ls += lpc * (y - ls);
            fxF.at (cb + 2) = ls;
            o[c] = ls * lvl;
        }

        return o;
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
entry = '''    // FX-SHTAB: distortion with the transfer curve of a shaper table frame (FX type 34)
    { n: "Shaper Table", mix: 1, modes: ["Clip", "Fold", "Wrap", "Rect"],
      p: [["Drive", fxLin(0, 36, 1, "dB"), 0.3], ["Pos", fxPct, 0], ["Table", fxLin(1, 6, 0, ""), 0], ["Bias", fxLin(-100, 100, 0, "%"), 0.5], ["Tone", fxHz(500, 20000), 1], ["Level", fxLin(-24, 12, 1, "dB"), 0.667]] },
'''
m = re.search(r'\n\];\n// the three racks', idx); assert m
idx = idx[:m.start() + 1] + entry + idx[m.start() + 1:]
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('FX-SHTAB applied')
