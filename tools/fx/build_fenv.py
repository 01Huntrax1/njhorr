#!/usr/bin/env python3
"""Idempotent: ADSR for the FX rack Filter effect (type 9), marker FX-FENV.
The envelope moves the cutoff (Env Amt = P4, +-7 octaves, bipolar, centre = off; Attack = P5; Decay = P6; Sustain and Release are the extra
parameters 3000+g and 3030+g of rack slot g). Gate: any note held; every accepted note-on retriggers from the current level."""
import re, sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'FX-FENV' in src:
    print('already applied'); sys.exit(0)

def rep(old, new, count=1):
    global src
    assert src.count(old) >= 1, old[:70]
    src = src.replace(old, new, count)

names = ['Main', 'Bus 1', 'Bus 2']
decl = ''.join('    input event float param%d [[ name: "%s FX %d Env Sustain", min: 0.0, max: 1.0, init: 1.0 ]];   // FX-FENV\n' % (3000 + rk * 10 + sl, names[rk], sl + 1) for rk in range(3) for sl in range(10))
decl += ''.join('    input event float param%d [[ name: "%s FX %d Env Release", min: 0.0, max: 1.0, init: 0.3 ]];   // FX-FENV\n' % (3030 + rk * 10 + sl, names[rk], sl + 1) for rk in range(3) for sl in range(10))
m = re.search(r'    input event float param881 [^\n]*\n', src); assert m
src = src[:m.end()] + decl + src[m.end():]

hand = ''.join('    event param%d (float v) { fxEnvSus.at (%d) = clamp (v, 0.0f, 1.0f); fxDirty.at (%d) = true; }\n' % (3000 + i, i, i) for i in range(30))
hand += ''.join('    event param%d (float v) { fxEnvRel.at (%d) = clamp (v, 0.0f, 1.0f); fxDirty.at (%d) = true; }\n' % (3030 + i, i, i) for i in range(30))
rep('    // FX-SYNC: sync divisions of the effect slots\n', '    // FX-FENV: sustain / release of the filter effect envelope\n' + hand + '    // FX-SYNC: sync divisions of the effect slots\n')

rep('    int[32]       fxSync;', '''    float[32]     fxEnvSus;  // FX-FENV: sustain level (0..1) and release (0..1 on an exponential 5 ms - 5 s map) of the filter effect envelope, per slot
    float[32]     fxEnvRel;
    float[32]     fxEnvLv;   // envelope level, stage (0 idle, 1 attack, 2 decay, 3 sustain, 4 release), the note counter it has seen, cutoff coefficient cache
    int[32]       fxEnvSt;
    int[32]       fxEnvSeen;
    float[32]     fxEnvGc;
    int[32]       fxEnvCt;
    int           fxNoteSeq = 0;   // counts accepted note-ons
    bool          fxHeld = false;  // any note is held (not yet released)
    int[32]       fxSync;''')

rep('        fxGateInit();\n', '        fxGateInit();\n\n        for (int ei = 0; ei < 32; ++ei)   // FX-FENV defaults\n        {\n            fxEnvSus.at (ei) = 1.0f;\n            fxEnvRel.at (ei) = 0.3f;\n        }\n')

rep('            float vel      = msg.getFloatVelocity();\n', '            fxNoteSeq++;   // FX-FENV: retriggers the filter effect envelopes\n            float vel      = msg.getFloatVelocity();\n')

rep('            // ----- FX racks: Bus 1 and Bus 2 feed the Main rack, which feeds the output -----',
    '            fxGateUpdate();   // FX-FENV\n\n            // ----- FX racks: Bus 1 and Bus 2 feed the Main rack, which feeds the output -----')

# derive
rep('''            fxD.at (db + 4) = 1.0f + 8.0f * p3;
        }
        else if (ty == 10)''', '''            fxD.at (db + 4) = 1.0f + 8.0f * p3;

            // FX-FENV: envelope on the cutoff: amount (+-1 = +-7 octaves), attack / decay / release coefficients, sustain
            fxD.at (db + 5) = (p4 - 0.5f) * 2.0f;
            fxD.at (db + 6) = 1.0f - float (exp (-2.2 / float64 (fxExpMap (p5, 1.0f, 5000.0f) * 0.001f * sr)));
            fxD.at (db + 7) = 1.0f - float (exp (-4.6 / float64 (fxExpMap (p6, 5.0f, 5000.0f) * 0.001f * sr)));
            fxD.at (db + 8) = clamp (fxEnvSus.at (s), 0.0f, 1.0f);
            fxD.at (db + 9) = 1.0f - float (exp (-4.6 / float64 (fxExpMap (clamp (fxEnvRel.at (s), 0.0f, 1.0f), 5.0f, 5000.0f) * 0.001f * sr)));
        }
        else if (ty == 10)''')

helpers = '''    // ---- FX-FENV: ADSR of the filter effect ----
    void fxGateUpdate()
    {
        bool h = false;

        for (int fv = 0; fv < 8; ++fv)
            if (voices.at (fv).active && voices.at (fv).stage != 3)
                h = true;

        fxHeld = h;
    }

    float fxEnvStep (int s, int db)
    {
        int   st = fxEnvSt.at (s);
        float lv = fxEnvLv.at (s);

        if (fxEnvSeen.at (s) != fxNoteSeq)
        {
            fxEnvSeen.at (s) = fxNoteSeq;

            if (fxHeld)
                st = 1;
        }

        if (fxHeld)
        {
            if (st == 0 || st == 4)
                st = 1;
        }
        else if (st >= 1 && st <= 3)
            st = 4;

        float sus = fxD.at (db + 8);

        if (st == 1)
        {
            lv += (1.25f - lv) * fxD.at (db + 6);

            if (lv >= 1.0f)
            {
                lv = 1.0f;
                st = 2;
            }
        }
        else if (st == 2 || st == 3)
        {
            lv += (sus - lv) * fxD.at (db + 7);
            st = abs (lv - sus) < 0.0005f ? 3 : 2;
        }
        else if (st == 4)
        {
            lv -= lv * fxD.at (db + 9);

            if (lv < 0.0001f)
            {
                lv = 0.0f;
                st = 0;
            }
        }

        fxEnvSt.at (s) = st;
        fxEnvLv.at (s) = lv;
        return lv;
    }

'''
rep('    float<2> fxFilter (int s, float<2> x)\n', helpers + '    float<2> fxFilter (int s, float<2> x)\n')

rep('''        float fc  = fxD.at (db + 3);

        float yl = fxFilterX (s, 0, inL, g, k, res, fc, ft);''', '''        float fc  = fxD.at (db + 3);
        float eAmt = fxD.at (db + 5);

        if (abs (eAmt) > 0.001f)   // FX-FENV
        {
            float lv = fxEnvStep (s, db);
            fc = clamp (fc * float (exp (float64 (eAmt * lv * 7.0f) * 0.6931471805599453)), 20.0f, float (processor.frequency) * 0.45f);
            int ec = fxEnvCt.at (s);

            if (ec <= 0)
            {
                fxEnvGc.at (s) = float (tan (float64 (fc) * pi * processor.period));
                ec = 4;
            }

            fxEnvCt.at (s) = ec - 1;
            g = fxEnvGc.at (s);
        }

        float yl = fxFilterX (s, 0, inL, g, k, res, fc, ft);''')

rep('    float fxFilterX (int s, int ch', '    // FX-FENV (helpers below)\n    float fxFilterX (int s, int ch') if False else None
open(P, 'w').write(src)

# ---- index.js: Filter effect params + the extra spec rows
J = os.path.join(ROOT, 'patch', 'index.js')
js = open(J).read()
old = '''p: [["Cutoff", fxHz(20, 20000), 0.67], ["Reso", fxPct, 0.2], ["Drive", fxPct, 0]] },'''
new = '''p: [["Cutoff", fxHz(20, 20000), 0.67], ["Reso", fxPct, 0.2], ["Drive", fxPct, 0], ["Env Amt", fxLin(-100, 100, 0, "%"), 0.5], ["Attack", fxMs(1, 5000), 0.1], ["Decay", fxMs(5, 5000), 0.5]] },'''
assert old in js
js = js.replace(old, new, 1)
row = '''    // ADSR of the Filter effect: Sustain and Release (ids 3000+g / 3030+g); Env Amt, Attack and Decay are P4..P6
    FX_RACKS.forEach((rack, rk) => { for (let sl = 0; sl < 10; sl++) { L.push([3000 + rk * 10 + sl, rack.name + " FX " + (sl + 1) + " Env Sustain", 0, 1, 1, "", "sld", null, 1, "Sustain"]); L.push([3030 + rk * 10 + sl, rack.name + " FX " + (sl + 1) + " Env Release", 0, 1, 0.3, "", "sld", null, 1, "Release"]); } });
'''
anchor = '    L.push([880, "Bus 1 Level"'
assert anchor in js
js = js.replace(anchor, row + anchor, 1)
open(J, 'w').write(js)
print('applied')
