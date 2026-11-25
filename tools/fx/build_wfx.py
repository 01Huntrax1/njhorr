#!/usr/bin/env python3
"""Idempotent, marker FX-WFILT: FX type 39 "Wavefilter": the Wavefilter of the oscillators as an effect.  24 band-pass filters (0.4 octave apart) whose gains come from a frame of the
filter table of an oscillator (the 16 built-in frames or the table loaded on that oscillator) along a frequency axis centred on the cutoff.
 P1 Cutoff (20 Hz - 20 kHz), P2 Reso (narrows the bands), P3 Pos (table position), P4 Table (oscillator 1-6), P5 Range (2..14 octaves), P6 Contrast (gains ^ 2^(1.5 c)).
 Modes = Gain Law: Linear (table -1..1 -> 0..1), Bipolar (raw value), dB.   build_wfx.py [patch dir]"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-WFILT' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
NT = 39
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )38\.0', r'\g<1>%d.0' % NT, src); assert n == 144, n
src, n = re.subn(r'(Euro M\d+ FX Type", min: 0\.0, max: )38\.0', r'\g<1>%d.0' % NT, src); assert n == 20, n
rep('int nt = clamp (t, 0, 38);', 'int nt = clamp (t, 0, %d);' % NT)
rep('        else if (ty == 38) y = fxPeq    (s, x);   // PHASEQ\n', '        else if (ty == 38) y = fxPeq    (s, x);   // PHASEQ\n        else if (ty == 39) y = fxWfilt (s, x);   // FX-WFILT\n')
rep('        else if (ty == 10)\n        {\n            // EQ: low shelf 100 Hz,', '''        else if (ty == 39)
        {
            // FX-WFILT: log2 cutoff, band width factor, table position, table bank (filter table of oscillator 1..6 = bank 0..5), range (octaves), contrast exponent
            fxD.at (db)     = float (log (fxExpMap (p1, 20.0f, 20000.0f))) * 1.442695f;
            fxD.at (db + 1) = 1.0f / (0.9f + p2 * 7.0f);
            fxD.at (db + 2) = p3;
            fxD.at (db + 3) = float (clamp (int (p4 * 5.0f + 0.5f), 0, 5));
            fxD.at (db + 4) = 2.0f + 12.0f * p5;
            fxD.at (db + 5) = clamp (fxP.at (pb + 5), 0.0f, 1.0f) * 2.0f - 1.0f;
        }
        else if (ty == 10)
        {
            // EQ: low shelf 100 Hz,''')
rep('    float[32768] fxF;  // padded to a power of two (cheap index wrap)\n', '''    float[32768] fxF;  // padded to a power of two (cheap index wrap)
    float[131072] wfxS;  // FX-WFILT: state of the 24 band filters (48 per channel, slot * 2 + channel; all 816 slots incl. the per voice slots of the oscillator racks)
    float[32768] wfxG;   // FX-WFILT: smoothed band gains (24 per slot)
    float[32768] wfxT;   // FX-WFILT: wanted band gains
    int[1024]    wfxC;   // FX-WFILT: sample counter per slot
''')
CODE = '''    // ================= FX-WFILT: Wavefilter effect (FX type 39) =================
    // gains of the 24 bands from the filter table frame (every 8 samples), followed by a one pole smoother; the bands are the same as in the oscillator Wavefilter
    void fxWfTargets (int s, float lfc, float pos, int bank, float width, float cont, int law)
    {
        float ex = cont != 0.0f ? float (pow (2.0f, cont * 1.5f)) : 1.0f;

        for (int b = 0; b < 24; ++b)
        {
            float r = wfL.at (b) - lfc;
            float t = clamp (r * 2.0f / width, -1.0f, 1.0f);
            float v = tblRead (bank, pos, 0.5f + 0.5f * t);
            float g = v;

            if (law == 0)
                g = v * 0.5f + 0.5f;
            else if (law == 2)
                g = float (pow (10.0f, (v - 1.0f) * 1.5f));

            if (ex != 1.0f)
            {
                float ga = float (pow (abs (g), ex));
                g = g < 0.0f ? -ga : ga;
            }

            wfxT.at (s * 24 + b) = g;
        }
    }

    float<2> fxWfilt (int s, float<2> x)
    {
        int   db  = s * 16;
        float k   = fxD.at (db + 1);
        int   cn  = wfxC.at (s);
        float<2> acc;

        wfxC.at (s) = cn + 1;

        if ((cn & 7) == 0)
            fxWfTargets (s, fxD.at (db), fxD.at (db + 2), int (fxD.at (db + 3) + 0.5f), fxD.at (db + 4), fxD.at (db + 5), clamp (fxMode.at (s), 0, 2));

        for (int b = 0; b < 24; ++b)
        {
            float gc = wfxG.at (s * 24 + b);
            gc += (wfxT.at (s * 24 + b) - gc) * 0.2f;
            wfxG.at (s * 24 + b) = gc;

            float g  = wfG.at (b);
            float a1 = 1.0f / (1.0f + g * (g + k));
            float a2 = g * a1;
            float a3 = g * a2;

            for (int c = 0; c < 2; ++c)
            {
                int   sb = (s * 2 + c) * 48 + b * 2;
                float s1 = wfxS.at (sb);
                float s2 = wfxS.at (sb + 1);
                float v3 = x[c] - s2;
                float v1 = a1 * s1 + a2 * v3;
                float v2 = s2 + a2 * s1 + a3 * v3;
                wfxS.at (sb)     = 2.0f * v1 - s1;
                wfxS.at (sb + 1) = 2.0f * v2 - s2;
                acc[c] += gc * k * v1;
            }
        }

        return acc * 0.64f;
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
rep('        fxFcS.at (s) = 0.0f;   // FX-FENV2\n', '''        fxFcS.at (s) = 0.0f;   // FX-FENV2

        for (int i = 0; i < 96; ++i)   // FX-WFILT
            wfxS.at (s * 96 + i) = 0.0f;

        for (int i = 0; i < 24; ++i)
        {
            wfxG.at (s * 24 + i) = 0.0f;
            wfxT.at (s * 24 + i) = 0.0f;
        }

        wfxC.at (s) = 0;
''')
rep('(t >= 17 && t <= 28) || t == 30 || t == 32;', '(t >= 17 && t <= 28) || t == 30 || t == 32 || t == 39;')   # per voice in the oscillator racks too
# the effect specific tools of type 39: same as the Parametric EQ's neighbour (Pre HP, Pre LP, Gate, Trim)
m = re.search(r'const int\[160\] fxExTab = \(([^)]*)\);', src); assert m
tab = [int(v) for v in m.group(1).split(',')]
tab[4 * 39:4 * 39 + 4] = [3, 7, 8, 11]
src = src[:m.start(1)] + ', '.join(str(v) for v in tab) + src[m.end(1):]
hp = os.path.join(root, 'native_ui', 'NjoFxEx.h'); h = open(hp).read()
m = re.search(r'static const int tab\[160\] = \{ ([^}]*) \};', h); assert m
h = h[:m.start(1)] + ', '.join(str(v) for v in tab) + h[m.end(1):]
open(hp, 'w').write(h)
entry = '''    // FX-WFILT: the Wavefilter of the oscillators as an effect (FX type 39), table = filter table of an oscillator
    { n: "Wavefilter", mix: 1, modes: ["Linear", "Bipolar", "dB"],
      p: [["Cutoff", fxHz(20, 20000), 0.5], ["Reso", fxPct, 0.2], ["Pos", fxPct, 0], ["Table", fxLin(1, 6, 0, ""), 0], ["Range", fxLin(2, 14, 1, "oct"), 0.5], ["Contrast", fxLin(-100, 100, 0, "%"), 0.5]] },
'''
m = re.search(r'\n\];\n// the three racks', idx); assert m
idx = idx[:m.start() + 1] + entry + idx[m.start() + 1:]
src += '\n// FX-WFILT\n'
open(P, 'w').write(src); open(IP, 'w').write(idx); print('FX-WFILT applied')
