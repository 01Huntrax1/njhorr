#!/usr/bin/env python3
"""Idempotent, marker FX-WET: four more parameters for EVERY effect slot (P7..P10), applied to the wet signal after the effect and before the dry/wet mix:
   Low Cut  (one pole high-pass 20 Hz - 1 kHz, off at 0)      High Cut (12 dB low-pass 20 kHz - 1.5 kHz, off at 1)
   Width    (mid/side, 0 = mono, 0.5 = unchanged, 1 = double)   Sat (wet soft saturation, off at 0)
 ids 11000 + 4 * g + k  for the global slot g (0..47 racks, 48.. oscillator racks like the other parameters: g = 48 + 16 * osc + slot), k 0..3.
 DSP: fxQ (8 floats per slot: 4 values, 2 coefficients, active flag), fxX (states).   build_fxwet.py [patch dir]"""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-WET' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

RN = ['Main', 'Bus 1', 'Bus 2']
def name(g):
    if g < 30: return '%s FX %d' % (RN[g // 10], g % 10 + 1)
    if g < 48: return '%s FX %d' % (RN[(g - 30) // 6], 11 + (g - 30) % 6)
    return 'OSC %d FX %d' % ((g - 48) // 16 + 1, (g - 48) % 16 + 1)
LAB = ['Low Cut', 'High Cut', 'Width', 'Sat']; DEF = ['0.0', '1.0', '0.5', '0.0']; DEFN = [0, 1, 0.5, 0]
decl = ''; hand = ''
for g in range(144):
    for k in range(4):
        i = 11000 + 4 * g + k
        decl += '    input event float param%d [[ name: "%s %s", min: 0.0, max: 1.0, init: %s ]];   // FX-WET\n' % (i, name(g), LAB[k], DEF[k])
        hand += '    event param%d (float v) { %s (%d, %d, v); }\n' % (i, 'fxWetSet' if g < 48 else 'fxWetSetO', g, k)
rep('    // EURO\n', decl + '    // EURO\n')
rep('    // RESO-HAND-BEGIN\n', hand + '    // RESO-HAND-BEGIN\n')
rep('    float[4992] fxP;', '    float[8704] fxQ;   // FX-WET: per slot 8 floats: low cut, high cut, width, sat, low cut coefficient, high cut coefficient, active flag\n    float[8704] fxX;   // FX-WET: filter states (8 per slot)\n    float[4992] fxP;')
CODE = '''    // FX-WET: wet signal post processing of every slot (P7..P10: Low Cut, High Cut, Width, Sat)
    void fxWetSet (int s, int k, float v)
    {
        int q = s * 8;
        fxQ.at (q + k) = v;
        float sr = float (processor.frequency);
        fxQ.at (q + 4) = 1.0f - float (exp (-6.283185307f * 20.0f * float (pow (50.0f, fxQ.at (q))) / sr));
        fxQ.at (q + 5) = 1.0f - float (exp (-6.283185307f * 1500.0f * float (pow (13.3333f, fxQ.at (q + 1))) / sr));
        bool act = fxQ.at (q) > 0.002f || fxQ.at (q + 1) < 0.998f || abs (fxQ.at (q + 2) - 0.5f) > 0.002f || fxQ.at (q + 3) > 0.002f;
        fxQ.at (q + 6) = act ? 1.0f : 0.0f;
    }

    // the same for an oscillator rack slot g (48 + 16 * osc + slot): written to the copies of all 8 voices
    void fxWetSetO (int g, int k, float v)
    {
        for (int vi = 0; vi < 8; ++vi)
            fxWetSet (48 + vi * 96 + (g - 48), k, v);
    }

    float<2> fxWet (int s, float<2> y)
    {
        int q = s * 8;

        if (fxQ.at (q + 6) < 0.5f)
            return y;

        float l = y[0];
        float r = y[1];

        if (fxQ.at (q) > 0.002f)
        {
            float c = fxQ.at (q + 4);
            fxX.at (q)     += c * (l - fxX.at (q));
            fxX.at (q + 1) += c * (r - fxX.at (q + 1));
            l -= fxX.at (q);
            r -= fxX.at (q + 1);
        }

        if (fxQ.at (q + 1) < 0.998f)
        {
            float c = fxQ.at (q + 5);
            fxX.at (q + 2) += c * (l - fxX.at (q + 2));
            fxX.at (q + 3) += c * (r - fxX.at (q + 3));
            fxX.at (q + 4) += c * (fxX.at (q + 2) - fxX.at (q + 4));
            fxX.at (q + 5) += c * (fxX.at (q + 3) - fxX.at (q + 5));
            l = fxX.at (q + 4);
            r = fxX.at (q + 5);
        }

        float sa = fxQ.at (q + 3);

        if (sa > 0.002f)
        {
            float gs = 1.0f + 6.0f * sa;
            float nr = 1.0f / sqrt (gs);
            l = float (tanh (l * gs)) * nr;
            r = float (tanh (r * gs)) * nr;
        }

        float wd = fxQ.at (q + 2);

        if (abs (wd - 0.5f) > 0.002f)
        {
            float md = (l + r) * 0.5f;
            float sd = (l - r) * 0.5f * (wd * 2.0f);
            l = md + sd;
            r = md - sd;
        }

        return float<2> (l, r);
    }

'''
rep('    float<2> fxRunSlot (int s, float<2> x)\n', CODE + '    float<2> fxRunSlot (int s, float<2> x)\n')
rep('        float mix = clamp (fxMix.at (s), 0.0f, 1.0f);\n        float<2> res = x + (y - x) * mix;', '        y = fxWet (s, y);   // FX-WET\n\n        float mix = clamp (fxMix.at (s), 0.0f, 1.0f);\n        float<2> res = x + (y - x) * mix;')
INIT = '''            fxQ.at (s * 8 + 1) = 1.0f;   // FX-WET: defaults High Cut open, Width 0.5 (unchanged)
            fxQ.at (s * 8 + 2) = 0.5f;
'''
rep('''            fxMode.at (s)  = 0;
            fxDirty.at (s) = true;

            for (int k = 0; k < 6; ++k)
                fxP.at (s * 6 + k) = 0.5f;
        }
''', '''            fxMode.at (s)  = 0;
            fxDirty.at (s) = true;
''' + INIT + '''
            for (int k = 0; k < 6; ++k)
                fxP.at (s * 6 + k) = 0.5f;
        }
''')
rep('''            fxSync.at (s)  = 0;
            fxEnvSus.at (s) = 1.0f;
            fxEnvRel.at (s) = 0.3f;
''', '''            fxSync.at (s)  = 0;
            fxEnvSus.at (s) = 1.0f;
            fxEnvRel.at (s) = 0.3f;
''' + INIT)
rep('        fxFcS.at (s) = 0.0f;   // FX-FENV2\n', '        fxFcS.at (s) = 0.0f;   // FX-FENV2\n\n        for (int i = 0; i < 8; ++i)   // FX-WET\n            fxX.at (s * 8 + i) = 0.0f;\n')

# parameter specs
SP = '''    // FX-WET: P7..P10 of every effect slot: ids 11000 + 4 * g + k (g = global slot: 0..47 racks, 48 + 16 * osc + slot for the oscillator racks)
    const wetName = g => g < 30 ? FX_RACKS[Math.floor(g / 10)].name + " FX " + (g % 10 + 1) : g < 48 ? FX_RACKS[Math.floor((g - 30) / 6)].name + " FX " + (11 + (g - 30) % 6) : "OSC " + (Math.floor((g - 48) / 16) + 1) + " FX " + ((g - 48) % 16 + 1);
    for (let g = 0; g < 144; g++) [["Low Cut", 0], ["High Cut", 1], ["Width", 0.5], ["Sat", 0]].forEach((w, k) => L.push([11000 + 4 * g + k, wetName(g) + " " + w[0], 0, 1, w[1], "", "sld", null, 1, w[0]]));
'''
rep('    // EURO: Eurorack rack of Njohrr Modular\n', SP + '    // EURO: Eurorack rack of Njohrr Modular\n', 'idx')
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('ok')
