#!/usr/bin/env python3
"""Idempotent, marker OSCFX-DSP: one effect rack per oscillator (replaces the fixed Filter > Dist > Reso order).
4 slots per oscillator, ids 6300 + 32 * osc + 8 * slot + k, k: 0 type, 1 mix, 2..4 p1..p3.
Types: 0 Off, 1 Filter, 2 Distortion, 3 Resonator (use the existing OSC tabs' parameters), 4 Bitcrush, 5 Fold, 6 Comb, 7 Tilt.
Per voice state, so every voice runs its own effects.  The old 'Pre-Matrix Order' (non default only) maps to the slots."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
jpath = os.path.join(root, 'patch', 'index.js')
src = open(path).read()
if 'OSCFX-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
BASE = 6300
DEF = [1, 2, 3, 0]
decl = ''; hand = ''
for o in range(6):
    for s in range(4):
        for k in range(5):
            i = BASE + 32 * o + 8 * s + k
            n = 'OSC %d FX %d %s' % (o + 1, s + 1, ['Type', 'Mix', 'P1', 'P2', 'P3'][k])
            if k == 0: a = 'min: 0.0, max: 7.0, init: %d.0, step: 1.0' % DEF[s]
            elif k == 1: a = 'min: 0.0, max: 1.0, init: 1.0'
            else: a = 'min: 0.0, max: 1.0, init: 0.5'
            decl += '    input event float param%d [[ name: "%s", %s ]];\n' % (i, n, a)
            hand += '    event param%d (float v) { rkSet (%d, %d, v); }\n' % (i, o * 4 + s, k)
rep('    // RESO-DECL-BEGIN\n', '    // OSCFX-DSP: per oscillator effect rack\n' + decl + '    // RESO-DECL-BEGIN\n')
rep('    // RESO-HAND-BEGIN\n', hand + '    // RESO-HAND-BEGIN\n')
rep('    float[512]    op;  // padded to a power of two (cheap index wrap)\n',
    '    float[512]    op;  // padded to a power of two (cheap index wrap)\n    float[128]    rkP;        // OSCFX-DSP: 24 slots x (type, mix, p1, p2, p3) at slot * 5 + k\n')
rep('    void opSet (int o, int k, float v)\n', '''    void rkSet (int sl, int k, float v)
    {
        rkP.at (sl * 5 + k) = v;
    }

    void opSet (int o, int k, float v)
''')
# legacy Order: non default values map to slot types
rep('        op.at (o * 64 + k) = v;\n\n        if (k >= 13 && k <= 17)',
    '''        op.at (o * 64 + k) = v;

        if (k == 45 && v > 0.5f)   // OSCFX-DSP: old presets with a different Pre-Matrix Order
        {
            int ord = clamp (int (v + 0.5f), 0, 5);
            for (int q = 0; q < 3; ++q)
                rkP.at ((o * 4 + q) * 5) = float (chainOrder.at (ord * 3 + q) + 1);
        }

        if (k >= 13 && k <= 17)''')
rep('        float[8]    fenv;     // filter envelope level per slot\n',
    '''        float[8]    fenv;     // filter envelope level per slot
        float[192]  rkS;      // OSCFX-DSP: per oscillator / slot / channel state (held, counter, write pos, lowpass)
        float[24576] rkB;     // OSCFX-DSP: comb delay lines (6 x 4 x 2 x 512)
''')
rep('            voices.at (v).fstage.at (o) = 1;\n', '''            voices.at (v).fstage.at (o) = 1;
            for (int rq = 0; rq < 32; ++rq)
                voices.at (v).rkS.at (o * 32 + rq) = 0.0f;
''')
rep('''                    for (int chSt = 0; chSt < 3; ++chSt)
                    {
                        int chStage = chainOrder.at (chOrd * 3 + chSt);
''', '''                    for (int chSt = 0; chSt < 4; ++chSt)
                    {
                        int   rkIx  = (o * 4 + chSt) * 5;
                        int   rkTy  = clamp (int (rkP.at (rkIx) + 0.5f), 0, 7);
                        float rkMx  = rkP.at (rkIx + 1);
                        float rk1   = rkP.at (rkIx + 2);
                        float rk2   = rkP.at (rkIx + 3);
                        float rk3   = rkP.at (rkIx + 4);
                        int   chStage = rkTy >= 1 && rkTy <= 3 ? rkTy - 1 : -1;
                        float rkDL  = sL;
                        float rkDR  = sR;

                        if (rkTy == 0 || rkMx <= 0.0f)
                            continue;
''')
# end of stage loop: add new types and mix
rep('''                            sL = rz.at (0);
                            sR = stereo ? rz.at (1) : sL;
                        }
                    }
''', '''                            sL = rz.at (0);
                            sR = stereo ? rz.at (1) : sL;
                        }

                        if (rkTy >= 4)
                        {
                            for (int ch = 0; ch < (stereo ? 2 : 1); ++ch)
                            {
                                int   si = ((o * 4 + chSt) * 2 + ch) * 4;   // inside rkS of this voice: 6 x 4 x 2 x 4 = 192
                                float c  = ch == 0 ? sL : sR;

                                if (rkTy == 4)   // bitcrush: bits and sample rate reduction
                                {
                                    float lv  = float (pow (2.0f, 1.0f + (1.0f - rk1) * 15.0f));
                                    float hold = 1.0f + rk2 * rk2 * 63.0f;
                                    float cnt = voices.at (i).rkS.at (si + 1) + 1.0f;
                                    if (cnt >= hold)
                                    {
                                        cnt -= hold;
                                        voices.at (i).rkS.at (si) = floor (clamp (c, -1.0f, 1.0f) * lv + 0.5f) / lv;
                                    }
                                    voices.at (i).rkS.at (si + 1) = cnt;
                                    c = voices.at (i).rkS.at (si);
                                }
                                else if (rkTy == 5)   // wavefolder: drive and bias
                                {
                                    c = float (sin ((c * (1.0f + rk1 * 9.0f) + (rk2 - 0.5f)) * 1.5707963f));
                                }
                                else if (rkTy == 6)   // comb: delay, feedback, damping
                                {
                                    int   cb = ((o * 4 + chSt) * 2 + ch) * 512;
                                    int   wp = int (voices.at (i).rkS.at (si + 2));
                                    int   dl = clamp (int (2.0f + rk1 * rk1 * 509.0f), 2, 510);
                                    float dv = voices.at (i).rkB.at (cb + ((wp - dl) & 511));
                                    float lp = voices.at (i).rkS.at (si + 3);
                                    lp += (dv - lp) * (1.0f - rk3 * 0.9f);
                                    voices.at (i).rkS.at (si + 3) = lp;
                                    voices.at (i).rkB.at (cb + (wp & 511)) = clamp (c + lp * rk2 * 0.95f, -4.0f, 4.0f);
                                    voices.at (i).rkS.at (si + 2) = float ((wp + 1) & 511);
                                    c = c + dv * 0.5f;
                                }
                                else   // tilt: one pole split, high or low shelf boost
                                {
                                    float fcT = 100.0f * float (pow (100.0f, rk1));
                                    float aT  = 1.0f - float (exp (-6.2831853f * fcT * float (processor.period)));
                                    float lpT = voices.at (i).rkS.at (si + 3);
                                    lpT += (c - lpT) * aT;
                                    voices.at (i).rkS.at (si + 3) = lpT;
                                    c = c + (rk2 - 0.5f) * 4.0f * (c - lpT);
                                }

                                if (ch == 0) sL = c; else sR = c;
                            }
                            if (! stereo)
                                sR = sL;
                        }

                        if (rkMx < 1.0f)
                        {
                            sL = rkDL + (sL - rkDL) * rkMx;
                            sR = rkDR + (sR - rkDR) * rkMx;
                        }
                    }
''')
open(path, 'w').write(src)

# index.js specs
js = open(jpath).read()
anchor = '    [1045, "OSC 1 Pre-Matrix Order"'
assert js.count(anchor) == 1
TYPES = '["Off", "Filter", "Distortion", "Resonator", "Bitcrush", "Fold", "Comb", "Tilt"]'
L = []
P = {4: ('Bits', 'Rate', '-'), 5: ('Drive', 'Bias', '-'), 6: ('Time', 'Feedback', 'Damp'), 7: ('Freq', 'Tilt', '-')}
for o in range(6):
    for s in range(4):
        b = BASE + 32 * o + 8 * s; n = 'OSC %d FX %d ' % (o + 1, s + 1)
        L.append('    [%d, "%sType", 0, 7, %d, "", "sel", %s, 1, "Type", null],' % (b, n, DEF[s], TYPES))
        L.append('    [%d, "%sMix", 0, 1, 1, "", "sld", null, 1, "Mix", null],' % (b + 1, n))
        for k, nm in ((2, 'P1'), (3, 'P2'), (4, 'P3')):
            L.append('    [%d, "%s%s", 0, 1, 0.5, "", "sld", null, 1, "%s", null],' % (b + k, n, nm, nm))
js = js.replace(anchor, '\n'.join(L) + '\n' + anchor)
open(jpath, 'w').write(js)
print('ok')
