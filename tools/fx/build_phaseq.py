#!/usr/bin/env python3
"""Idempotent, marker PHASEQ: FX type 38 "Phase EQ" - the band engine of the Parametric EQ (24 bands, per band stereo / L / R / mid / side) with phase-only bands:
  band types: 0 All-Pass 2 (second order, Q = width; Stages = 1 + HARMONICS cascaded), 1 All-Pass 1 (first order, Stages), 2 Dispersion (2 + HARMONICS all-passes spread
  around the frequency, FALLOFF = spread, slot parameter P2 scales it), 3 Polarity (inverts the channel).  Slot parameters as the EQ: P1 output, P2 spread scale, P3 frequency shift, P4 Q scale.
  build_phaseq.py [patch dir]"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if '// PHASEQ' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
NT = 38
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )37\.0', r'\g<1>%d.0' % NT, src); assert n == 144, n
src, n = re.subn(r'(Euro M\d+ FX Type", min: 0\.0, max: )37\.0', r'\g<1>%d.0' % NT, src); assert n == 20, n
rep('int nt = clamp (t, 0, 37);', 'int nt = clamp (t, 0, %d);' % NT)
rep('        else if (ty == 37) y = s < 48 ? fxYbString (s, x) : x;\n', '        else if (ty == 37) y = s < 48 ? fxYbString (s, x) : x;\n        else if (ty == 38) y = fxPeq    (s, x);   // PHASEQ\n')
rep('        if (ty == 13)\n            fxPeqDerive (s);\n', '        if (ty == 13 || ty == 38)\n            fxPeqDerive (s, ty);   // PHASEQ\n')
rep('    void fxPeqDerive (int s)\n', '    void fxPeqDerive (int s, int fxt)\n')
rep("        else\n        {\n            b0 = 1.0f - al;  b1 = -2.0f * cw;  b2 = 1.0f + al;", '''        else if (kind == 12)   // PHASEQ: first order all-pass
        {
            float K = float (tan (w0 * 0.5f));
            b0 = 1.0f - K;  b1 = -(1.0f + K);
            a0 = 1.0f + K;  a1 = K - 1.0f;
        }
        else if (kind == 13)   // PHASEQ: polarity
        {
            b0 = -1.0f;
        }
        else
        {
            b0 = 1.0f - al;  b1 = -2.0f * cw;  b2 = 1.0f + al;''')
rep('    // turns the bands and the four slot parameters of an EQ slot into sections', '''    // PHASEQ: the sections of one band of a Phase EQ (type 0 all-pass 2, 1 all-pass 1, 2 dispersion, 3 polarity); spread = falloff field * slot P2 (0..2)
    int peqPhaseBand (int s, int n, int ty, float f, float q, int harm, float spread, int ch)
    {
        if (ty == 0)
        {
            for (int i = 0; i <= harm; ++i)
                n = peqAddSec (s, n, 7, f, 0.0f, q, ch);
        }
        else if (ty == 1)
        {
            for (int i = 0; i <= harm; ++i)
                n = peqAddSec (s, n, 12, f, 0.0f, q, ch);
        }
        else if (ty == 2)
        {
            int   cnt = harm + 2;
            float spr = clamp (spread, 0.0f, 2.0f) * 4.0f;

            for (int i = 0; i < cnt; ++i)
            {
                float u = float (i) / float (cnt - 1) - 0.5f;
                n = peqAddSec (s, n, 7, f * float (pow (2.0f, u * spr)), 0.0f, q, ch);
            }
        }
        else
            n = peqAddSec (s, n, 13, f, 0.0f, 1.0f, ch);

        return n;
    }

    // turns the bands and the four slot parameters of an EQ slot into sections''')
rep('            if (ty == 0)       n = peqAddSec (s, n, 0, f, g, q, ch);', '            if (fxt == 38)\n                n = peqPhaseBand (s, n, ty, f, q, harm, clamp (peqB.at (bi + 6), 0.0f, 1.0f) * gScale, ch);\n            else if (ty == 0)  n = peqAddSec (s, n, 0, f, g, q, ch);')
rep('            if ((ty == 0 || ty == 7 || ty == 8) && harm > 0)', '            if (fxt != 38 && (ty == 0 || ty == 7 || ty == 8) && harm > 0)')
# the effect specific tools of type 38: same as the Parametric EQ
m = re.search(r'const int\[160\] fxExTab = \(([^)]*)\);', src); assert m
tab = [int(v) for v in m.group(1).split(',')]
tab[4 * 38:4 * 38 + 4] = tab[4 * 13:4 * 13 + 4]
src = src[:m.start(1)] + ', '.join(str(v) for v in tab) + src[m.end(1):]
hp = os.path.join(root, 'native_ui', 'NjoFxEx.h'); h = open(hp).read()
m = re.search(r'static const int tab\[160\] = \{ ([^}]*) \};', h); assert m
h = h[:m.start(1)] + ', '.join(str(v) for v in tab) + h[m.end(1):]
open(hp, 'w').write(h)
entry = '''    // PHASEQ: phase-only EQ (FX type 38), the band editor shows the phase response
    { n: "Phase EQ", mix: 1, modes: [],
      p: [["Output", fxDb(-18, 18), 0.5], ["Spread Scale", fxPctOf(2), 0.5], ["Freq Shift", fxLin(-1, 1, 2, "oct"), 0.5], ["Q Scale", n => "x" + (0.25 * Math.pow(16, n)).toFixed(2), 0.5]] },
'''
m = re.search(r'\n\];\n// the three racks', idx); assert m
idx = idx[:m.start() + 1] + entry + idx[m.start() + 1:]
src += '\n// PHASEQ\n'
open(P, 'w').write(src); open(IP, 'w').write(idx); print('patched')
