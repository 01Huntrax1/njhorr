#!/usr/bin/env python3
"""Idempotent, marker MSEG-DSP: the 10 modulation envelopes can run as MSEGs (multi-segment envelopes).
  Per envelope e (base = 7200 + 30 * e), all non-automatable:
    +0 Mode (0 ADSR = old behaviour / old presets, 1 MSEG)   +1 Nodes (2..8)   +2 Sustain node (0 = none, 1..8)
    +3 Loop on   +4 Loop start (1..8)   +5 Loop end (1..8)
    +6 + 3k  node k: time ms to reach it, level 0..1, curve -1..1   (k = 0..7)
  Segment shape: level = from + (to - from) * x^exp(curve * 2.5).  Held: runs through the nodes, stops at the sustain node
  (or loops loop start..end).  Note off: continues with the nodes after the sustain node; without further nodes (or without a
  sustain node) the level falls to 0 with the ADSR release time.  The filter-effect envelope (fxEnvStep) keeps using ADSR."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'MSEG-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

DEF_T = [10, 300, 300, 100, 100, 100, 100, 100]
DEF_L = [1.0, 0.5, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5]
decl = []; hand = []; specs = []
def P(i, nm, lo, hi, ini, step, h, spec):
    decl.append('    input event float param%d [[ name: "%s", min: %s, max: %s, init: %s, step: %s, automatable: false ]];' % (i, nm, lo, hi, ini, step))
    hand.append('    event param%d (float v) { %s }' % (i, h))
    specs.append('    [%d, "%s", %s, %s, %s, "", %s],' % (i, nm, lo, hi, ini, spec))
for e in range(10):
    b = 7200 + 30 * e; n = 'MSEG%d ' % (e + 1)
    P(b, n + 'Mode', '0.0', '1.0', '0.0', '1.0', 'msMode.at (%d) = v > 0.5f ? 1 : 0;' % e, '"sel", ["ADSR", "MSEG"], 1, "Mode", null')
    P(b + 1, n + 'Nodes', '2.0', '8.0', '3.0', '1.0', 'msN.at (%d) = clamp (int (v + 0.5f), 2, 8);' % e, '"knb", null, 1, "Nodes", null')
    P(b + 2, n + 'Sustain', '0.0', '8.0', '2.0', '1.0', 'msSus.at (%d) = clamp (int (v + 0.5f), 0, 8);' % e, '"knb", null, 1, "Sustain", null')
    P(b + 3, n + 'Loop', '0.0', '1.0', '0.0', '1.0', 'msLoopOn.at (%d) = v > 0.5f ? 1 : 0;' % e, '"sel", ["Off", "On"], 1, "Loop", null')
    P(b + 4, n + 'Loop Start', '1.0', '8.0', '1.0', '1.0', 'msLoopS.at (%d) = clamp (int (v + 0.5f), 1, 8);' % e, '"knb", null, 1, "Loop Start", null')
    P(b + 5, n + 'Loop End', '1.0', '8.0', '2.0', '1.0', 'msLoopE.at (%d) = clamp (int (v + 0.5f), 1, 8);' % e, '"knb", null, 1, "Loop End", null')
    for k in range(8):
        q = b + 6 + 3 * k; j = e * 8 + k
        P(q, n + 'Node %d Time' % (k + 1), '0.0', '10000.0', '%.1f' % DEF_T[k], '1.0', 'msT.at (%d) = v;' % j, '"knb", null, 1, "Time", null')
        P(q + 1, n + 'Node %d Level' % (k + 1), '0.0', '1.0', '%.2f' % DEF_L[k], '0.001', 'msL.at (%d) = v;' % j, '"knb", null, 1, "Level", null')
        P(q + 2, n + 'Node %d Curve' % (k + 1), '-1.0', '1.0', '0.0', '0.01', 'msC.at (%d) = v;' % j, '"knb", null, 1, "Curve", null')

d = re.search(r'    input event float param7144 \[\[[^\]]*\]\];', src).group(0)
rep(d, d + '\n    // MSEG-DSP\n' + '\n'.join(decl))
h = re.search(r'    event param7144 \(float v\)[^\n]*', src).group(0)
rep(h, h + '\n' + '\n'.join(hand))
s0 = re.search(r'    \[7144, "Insp Poly"[^\n]*', idx).group(0)
rep(s0, s0 + '\n' + '\n'.join(specs), 'idx')

# state
rep('    float[16]   mEnvR;  // padded to a power of two (cheap index wrap)\n',
    '    float[16]   mEnvR;  // padded to a power of two (cheap index wrap)\n'
    '    // MSEG-DSP\n    int[16]     msMode;\n    int[16]     msN;\n    int[16]     msSus;\n    int[16]     msLoopOn;\n    int[16]     msLoopS;\n    int[16]     msLoopE;\n'
    '    float[128]  msT;\n    float[128]  msL;\n    float[128]  msC;\n')
rep('            mEnvR.at (mi)       = 300.0f;\n',
    '            mEnvR.at (mi)       = 300.0f;\n            msMode.at (mi)      = 0;\n            msN.at (mi)         = 3;\n            msSus.at (mi)       = 2;\n            msLoopOn.at (mi)    = 0;\n            msLoopS.at (mi)     = 1;\n            msLoopE.at (mi)     = 2;\n')
rep('        int[16]   mstage;     // mod envelope stages (0 off, 1 attack, 2 decay/sustain, 3 release)\n',
    '        int[16]   mstage;     // mod envelope stages (0 off, 1 attack, 2 decay/sustain, 3 release)\n'
    '        int[16]   vmNode;     // MSEG-DSP: target node (held node in stage 2)\n        int[16]   vmFlag;     // MSEG-DSP: 0 not released, 1 release through nodes, 2 fallback release, 3 done\n'
    '        float[16] vmT;        // MSEG-DSP: seconds in the current segment\n        float[16] vmFrom;     // MSEG-DSP: level at the segment start\n')
rep('        for (int ms = 0; ms < 10; ++ms)\n            voices.at (v).mstage.at (ms) = 1;\n',
    '        for (int ms = 0; ms < 10; ++ms)\n        {\n            voices.at (v).mstage.at (ms) = 1;\n            voices.at (v).vmNode.at (ms) = 0;\n            voices.at (v).vmFlag.at (ms) = 0;\n            voices.at (v).vmT.at (ms)    = 0.0f;\n            voices.at (v).vmFrom.at (ms) = voices.at (v).menv.at (ms);\n        }\n')

# engine
rep('    // Advances the 10 mod envelopes of one voice by one sample\n', '''    // MSEG-DSP: advances MSEG m of one voice by one sample
    void msStep (int vi, int m, float dtv)
    {
        int   ms  = voices.at (vi).mstage.at (m);
        float me  = voices.at (vi).menv.at (m);
        int   n   = msN.at (m);
        int   sus = msSus.at (m) - 1;
        int   fl  = voices.at (vi).vmFlag.at (m);
        int   k   = voices.at (vi).vmNode.at (m);

        if (ms == 3 && fl == 0)
        {
            fl = 1;
            voices.at (vi).vmFrom.at (m) = me;
            voices.at (vi).vmT.at (m)    = 0.0f;

            if (sus < 0)
                fl = 2;
            else
            {
                if (k <= sus)
                    k = sus + 1;

                if (k >= n)
                    fl = 2;
            }
        }

        if ((ms == 1 || (ms == 3 && fl == 1)) && k < n)
        {
            float tt = max (msT.at (m * 8 + k), 0.0f) * 0.001f;
            float t  = voices.at (vi).vmT.at (m) + dtv;
            float x  = tt <= 0.00002f ? 1.0f : t / tt;
            float lv = msL.at (m * 8 + k);

            if (x >= 1.0f)
            {
                me = lv;
                voices.at (vi).vmFrom.at (m) = me;
                voices.at (vi).vmT.at (m)    = 0.0f;

                if (ms == 1)
                {
                    int le = max (msLoopS.at (m), msLoopE.at (m)) - 1;
                    int ls = min (msLoopS.at (m), msLoopE.at (m)) - 1;

                    if (msLoopOn.at (m) > 0 && k == le && le < n)
                        k = ls;
                    else if (k == sus)
                        ms = 2;
                    else if (k + 1 >= n)
                        ms = 2;
                    else
                        k = k + 1;
                }
                else
                    k = k + 1;
            }
            else
            {
                float sh = float (pow (x, float (exp (msC.at (m * 8 + k) * 2.5f))));
                me = voices.at (vi).vmFrom.at (m) + (lv - voices.at (vi).vmFrom.at (m)) * sh;
                voices.at (vi).vmT.at (m) = t;
            }
        }
        else if (fl == 2)
            me -= me * clamp (dtv * 5.0f / (max (mEnvR.at (m), 1.0f) * 0.001f), 0.0f, 0.99f);

        voices.at (vi).mstage.at (m) = ms;
        voices.at (vi).vmFlag.at (m) = fl;
        voices.at (vi).vmNode.at (m) = k;
        voices.at (vi).menv.at (m)   = me;

        if (me > envMaxNext.at (m))
            envMaxNext.at (m) = me;
    }

    // Advances the 10 mod envelopes of one voice by one sample
''')
rep('        for (int m = 0; m < 10; ++m)\n        {\n            int   ms = voices.at (vi).mstage.at (m);\n',
    '        for (int m = 0; m < 10; ++m)\n        {\n            if (msMode.at (m) == 1)\n            {\n                msStep (vi, m, dtv);\n                continue;\n            }\n\n            int   ms = voices.at (vi).mstage.at (m);\n')
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('MSEG-DSP applied: %d params' % len(decl))
