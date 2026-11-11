#!/usr/bin/env python3
"""Idempotent, marker OSCFX2-DSP: three more parameters per rack slot (k = 5..7 = P4..P6) for Fold and Comb.
Fold: P1 Drive, P2 Bias, P3 Stage 2, P4 Shape (sine > triangle), P5 Asym, P6 Attenuate.
Comb: P1 Time, P2 Feedback, P3 Damp, P4 Polarity (+ > -), P5 Key Track, P6 Mod (delay modulation)."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); jpath = os.path.join(root, 'patch', 'index.js')
src = open(path).read()
if 'OSCFX2-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global src
    assert src.count(old) == n, (old[:70], src.count(old))
    src = src.replace(old, new)
decl = ''
for o in range(6):
    for s in range(4):
        for k, nm in ((5, 'P4'), (6, 'P5'), (7, 'P6')):
            decl += '    input event float param%d [[ name: "OSC %d FX %d %s", min: 0.0, max: 1.0, init: 0.0 ]];\n' % (6300 + 32 * o + 8 * s + k, o + 1, s + 1, nm)
            decl += '    event param%d (float v) { rkSet (%d, %d, v); }\n' % (6300 + 32 * o + 8 * s + k, o * 4 + s, k)
rep('    // RESO-DECL-BEGIN\n', '    // OSCFX2-DSP\n' + ''.join(l for l in decl.splitlines(True) if l.startswith('    input')) + '    // RESO-DECL-BEGIN\n')
rep('    // RESO-HAND-BEGIN\n', ''.join(l for l in decl.splitlines(True) if l.startswith('    event')) + '    // RESO-HAND-BEGIN\n')
rep('float[128]    rkP;        // OSCFX-DSP: 24 slots x (type, mix, p1, p2, p3) at slot * 5 + k', 'float[256]    rkP;        // OSCFX-DSP: 24 slots x (type, mix, p1..p6) at slot * 8 + k')
rep('rkP.at (sl * 5 + k) = v;', 'rkP.at (sl * 8 + k) = v;')
rep('rkP.at ((o * 4 + q) * 5) = float', 'rkP.at ((o * 4 + q) * 8) = float')
rep('        float[192]  rkS;      // OSCFX-DSP: per oscillator / slot / channel state (held, counter, write pos, lowpass)\n        float[24576] rkB;     // OSCFX-DSP: comb delay lines (6 x 4 x 2 x 512)\n',
    '        float[384]  rkS;      // OSCFX-DSP: per oscillator / slot / channel state, 8 floats (held, counter, write pos, lowpass, mod phase)\n        float[49152] rkB;     // OSCFX-DSP: comb delay lines (6 x 4 x 2 x 1024)\n')
rep('''            rkP.at (rq * 5)     = (rq & 3) < 3 ? float ((rq & 3) + 1) : 0.0f;
            rkP.at (rq * 5 + 1) = 1.0f;
            rkP.at (rq * 5 + 2) = 0.5f;
            rkP.at (rq * 5 + 3) = 0.5f;
            rkP.at (rq * 5 + 4) = 0.5f;''','''            rkP.at (rq * 8)     = (rq & 3) < 3 ? float ((rq & 3) + 1) : 0.0f;
            rkP.at (rq * 8 + 1) = 1.0f;
            rkP.at (rq * 8 + 2) = 0.5f;
            rkP.at (rq * 8 + 3) = 0.5f;
            rkP.at (rq * 8 + 4) = 0.5f;''')
rep('''            for (int rq = 0; rq < 32; ++rq)
                voices.at (v).rkS.at (o * 32 + rq) = 0.0f;''','''            for (int rq = 0; rq < 64; ++rq)
                voices.at (v).rkS.at (o * 64 + rq) = 0.0f;''')
rep('int   rkIx  = (o * 4 + chSt) * 5;', 'int   rkIx  = (o * 4 + chSt) * 8;')
rep('                        float rk3   = rkP.at (rkIx + 4);\n', '                        float rk3   = rkP.at (rkIx + 4);\n                        float rk4   = rkP.at (rkIx + 5);\n                        float rk5   = rkP.at (rkIx + 6);\n                        float rk6   = rkP.at (rkIx + 7);\n')
rep('* 2 + ch) * 4;   // inside rkS of this voice: 6 x 4 x 2 x 4 = 192', '* 2 + ch) * 8;   // inside rkS of this voice: 6 x 4 x 2 x 8 = 384')
# fold + comb
i = src.index('                                else if (rkTy == 5)   // wavefolder')
j = src.index('                                else   // tilt')
new = '''                                else if (rkTy == 5)   // wavefolder: two cascaded folds, sine <> triangle shape, asymmetry, output level
                                {
                                    float g1 = 1.0f + rk1 * 9.0f;
                                    float as = (rk5 - 0.0f) * 0.9f;
                                    float y  = c * g1 * (c >= 0.0f ? 1.0f + as : 1.0f - as) + (rk2 - 0.5f);
                                    float f1 = float (sin (y * 1.5707963f)) * (1.0f - rk4) + rk4 * (2.0f / 3.1415927f) * float (asin (clamp (float (sin (y * 1.5707963f)), -1.0f, 1.0f)));
                                    float y2 = f1 * (1.0f + rk3 * 3.0f) * 1.0f;
                                    float f2 = float (sin (y2 * 1.5707963f)) * (1.0f - rk4) + rk4 * (2.0f / 3.1415927f) * float (asin (clamp (float (sin (y2 * 1.5707963f)), -1.0f, 1.0f)));
                                    c = (f1 + (f2 - f1) * rk3) * (1.0f - rk6 * 0.8f);
                                }
                                else if (rkTy == 6)   // comb: delay (optionally tuned to the key), feedback, damping, polarity, delay modulation
                                {
                                    int   cb = ((o * 4 + chSt) * 2 + ch) * 1024;
                                    int   wp = int (voices.at (i).rkS.at (si + 2));
                                    float dk = 2.0f + rk1 * rk1 * 1018.0f;
                                    float kt = clamp ((rk5 - 0.0f), 0.0f, 1.0f);
                                    float dkey = clamp (sr / max (freq, 20.0f), 2.0f, 1018.0f);
                                    float dly = dk + (dkey - dk) * kt;
                                    float mp = voices.at (i).rkS.at (si + 4) + 0.7f * float (processor.period);
                                    if (mp >= 1.0f) mp -= 1.0f;
                                    voices.at (i).rkS.at (si + 4) = mp;
                                    dly = clamp (dly * (1.0f + rk6 * 0.15f * float (sin (mp * 6.2831853f))), 2.0f, 1019.0f);
                                    float rp  = float (wp) - dly;
                                    int   i0  = int (floor (rp));
                                    float fr  = rp - float (i0);
                                    float dv  = voices.at (i).rkB.at (cb + (i0 & 1023)) * (1.0f - fr) + voices.at (i).rkB.at (cb + ((i0 + 1) & 1023)) * fr;
                                    float sg  = 1.0f - 2.0f * rk4;
                                    float lp  = voices.at (i).rkS.at (si + 3);
                                    lp += (dv - lp) * (1.0f - rk3 * 0.9f);
                                    voices.at (i).rkS.at (si + 3) = lp;
                                    voices.at (i).rkB.at (cb + (wp & 1023)) = clamp (c + lp * sg * rk2 * 0.95f, -4.0f, 4.0f);
                                    voices.at (i).rkS.at (si + 2) = float ((wp + 1) & 1023);
                                    c = c + dv * 0.5f * (sg >= 0.0f ? 1.0f : -1.0f) * max (abs (sg), 0.2f);
                                }
'''
src = src[:i] + new + src[j:]
open(path, 'w').write(src)
# specs
js = open(jpath).read()
n = 0
def add(m):
    global n; n += 1
    b = int(m.group(1)); nm = m.group(2)
    return m.group(0) + '\n' + '\n'.join('    [%d, "%s%s", 0, 1, 0, "", "sld", null, 1, "%s", null],' % (b + 1 + k, nm, ['P4', 'P5', 'P6'][k], ['P4', 'P5', 'P6'][k]) for k in range(3))
js = re.sub(r'    \[(\d+), "(OSC \d FX \d )P3", 0, 1, 0\.5, "", "sld", null, 1, "P3", null\],', add, js)
assert n == 24, n
open(jpath, 'w').write(js)
print('ok')
