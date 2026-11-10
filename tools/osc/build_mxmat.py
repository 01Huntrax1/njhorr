#!/usr/bin/env python3
"""Idempotent: four more 6 x 6 oscillator matrices, marker MXMAT-DSP: XF (crossfade), FD (fold), XR (xor), CP (comparator).
ids 5300 + 36 * kind + 6 * source + target, 0..100 %.  They work like RM / AM: the previous output sample of the source slot is the
modulator, the target slot's own signal is the carrier (after filter and distortion, before level / pan / routing).  Amount 0 = off.
They replace the old Crossfade / Fold / XOR / Comparator modes of the Warp effect (build_mutable.py)."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'MXMAT-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
KINDS = ['XF', 'FD', 'XR', 'CP']
BASE = 5300
decl = ''.join('    input event float param%d [[ name: "%s %d to %d", min: 0.0, max: 100.0, init: 0.0, step: 1.0 ]];\n' % (BASE + 36 * k + 6 * s + d, KINDS[k], s + 1, d + 1) for k in range(4) for s in range(6) for d in range(6))
rep('    input event float param1560 [[ name: "AM 1 to 1"', '    // MXMAT-DSP: crossfade / fold / xor / comparator matrices\n' + decl + '    input event float param1560 [[ name: "AM 1 to 1"')
hand = ''.join('    event param%d (float v) { mxSet (%d, %d, %d, v * 0.01f); }\n' % (BASE + 36 * k + 6 * s + d, k, s, d) for k in range(4) for s in range(6) for d in range(6))
rep('    event param1560 (float v) { amSet (0, 0, v * 0.01f); }\n', hand + '    event param1560 (float v) { amSet (0, 0, v * 0.01f); }\n')
rep('    float[64]     tzAmt;      // through-zero FM (TZFM-DSP)\n', '    float[64]     tzAmt;      // through-zero FM (TZFM-DSP)\n    float[256]    mxAmt;      // MXMAT-DSP: 4 matrices (crossfade, fold, xor, comparator) x 64\n')
rep('|| amAmt.at (q * 6 + r) != 0.0f || tzAmt.at (q * 6 + r) != 0.0f) u = true;',
    '|| amAmt.at (q * 6 + r) != 0.0f || tzAmt.at (q * 6 + r) != 0.0f\n                    || mxAmt.at (q * 6 + r) != 0.0f || mxAmt.at (64 + q * 6 + r) != 0.0f || mxAmt.at (128 + q * 6 + r) != 0.0f || mxAmt.at (192 + q * 6 + r) != 0.0f) u = true;')
rep('    void tzSet (int s, int d, float v)\n', '    void mxSet (int k, int s, int d, float v)\n    {\n        mxAmt.at (k * 64 + s * 6 + d) = v;\n        updateFmUsed();\n    }\n\n    void tzSet (int s, int d, float v)\n')
rep('                    // the matrix modulators are the processed slot outputs (after filter and distortion)\n', '''                    // ----- MXMAT-DSP: crossfade / fold / xor / comparator matrices (modulator = previous output of the source slot) -----
                    if (fmAny)
                    {
                        for (int xs = 0; xs < 6; ++xs)
                        {
                            int   xi = xs * 6 + o;
                            float axf = mxAmt.at (xi);
                            float afd = mxAmt.at (64 + xi);
                            float axr = mxAmt.at (128 + xi);
                            float acp = mxAmt.at (192 + xi);

                            if (axf == 0.0f && afd == 0.0f && axr == 0.0f && acp == 0.0f)
                                continue;

                            float xm = clamp (rmPrev.at (xs), -1.0f, 1.0f);

                            for (int ch = 0; ch < 2; ++ch)
                            {
                                float c = ch == 0 ? sL : sR;

                                if (axf != 0.0f)   // crossfade, equal power: 100 % = only the modulator
                                    c = c * float (cos (axf * 1.5707963f)) + xm * float (sin (axf * 1.5707963f));

                                if (afd != 0.0f)   // fold: the sum of both is folded harder with the amount
                                    c += afd * (float (sin ((c + xm) * (0.4f + afd * 3.5f) * 1.5707963f)) - c);

                                if (axr != 0.0f)   // xor of the 16 bit values, faded in with the amount
                                {
                                    int ci = int (clamp (c, -1.0f, 0.9999f) * 32768.0f);
                                    int mi = int (clamp (xm, -1.0f, 0.9999f) * 32768.0f);
                                    c += axr * (float (ci ^ mi) / 32768.0f - c);
                                }

                                if (acp != 0.0f)   // comparator: dry > maximum (first half) > gate (modulator above / below the carrier)
                                {
                                    float mx = xm > c ? xm : c;
                                    float gt = xm > c ? 0.7f : -0.7f;
                                    float t  = acp * 2.0f;
                                    c = t < 1.0f ? c + (mx - c) * t : mx + (gt - mx) * (t - 1.0f);
                                }

                                if (ch == 0)
                                    sL = c;
                                else
                                    sR = c;
                            }
                        }
                    }

                    // the matrix modulators are the processed slot outputs (after filter and distortion)
''')
open(path, 'w').write(src)
print('ok')
