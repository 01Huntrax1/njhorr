#!/usr/bin/env python3
"""Idempotent, marker EURO: parameters of the Eurorack-style rack of "Njohrr Modular" (ids from tools/modular/euro_modules.py; the engine is added
to patch_mod/ by build_modplugin.py).  Per slot: type, 8 knobs, mode, 4 input sources, 4 input gains, FX type."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from euro_modules import *
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'EURO' in src:
    print('already applied'); sys.exit(0)
assert 'MODMAT' in src, 'run build_matrix.py first'
def rep(t, old, new):
    assert t.count(old) == 1, (old[:60], t.count(old)); return t.replace(old, new)
decl, hand = [], []
def D(i, name, lo, hi, ini, step):
    decl.append('    input event float param%d [[ name: "%s", min: %s, max: %s, init: %s, step: %s, automatable: false ]];' % (i, name, lo, hi, ini, step))
for m in range(NSLOT):
    n = 'Euro M%d' % (m + 1)
    D(pid(m, K_TYPE), n + ' Type', '0.0', '%d.0' % (NTYPE - 1), '0.0', '1.0')
    hand.append('    event param%d (float v) { eType.at (%d) = clamp (int (v + 0.5f), 0, %d); eRst.at (%d) = 1; }' % (pid(m, K_TYPE), m, NTYPE - 1, m))
    for k in range(8):
        D(pid(m, K_KNOB + k), '%s Knob %d' % (n, k + 1), '0.0', '1.0', '0.5', '0.001')
        extra = ''
        if k < 6: extra = ' fxP.at (%d) = v; fxDirty.at (%d) = true;' % ((10 + m) * 6 + k, 10 + m)
        elif k == 6: extra = ' fxMix.at (%d) = v;' % (10 + m)
        hand.append('    event param%d (float v) { eK.at (%d) = v;%s }' % (pid(m, K_KNOB + k), m * 8 + k, extra))
    D(pid(m, K_MODE), n + ' Mode', '0.0', '7.0', '0.0', '1.0')
    hand.append('    event param%d (float v) { eMode.at (%d) = clamp (int (v + 0.5f), 0, 7); }' % (pid(m, K_MODE), m))
    for c in range(4):
        D(pid(m, K_SRC + c), '%s In %d Src' % (n, c + 1), '0.0', '%d.0' % (NSRC - 1), '0.0', '1.0')
        hand.append('    event param%d (float v) { eSrc.at (%d) = clamp (int (v + 0.5f), 0, %d); }' % (pid(m, K_SRC + c), m * 4 + c, NSRC - 1))
        D(pid(m, K_GAIN + c), '%s In %d Gain' % (n, c + 1), '0.0', '2.0', '1.0', '0.001')
        hand.append('    event param%d (float v) { eGain.at (%d) = clamp (v, 0.0f, 2.0f); }' % (pid(m, K_GAIN + c), m * 4 + c))
    D(pid(m, K_FX), n + ' FX Type', '0.0', '32.0', '0.0', '1.0')
    hand.append('    event param%d (float v) { fxSetType (%d, int (v + 0.5f)); }' % (pid(m, K_FX), 10 + m))
src = rep(src, '    // MODMAT\n', '    // EURO\n' + '\n'.join(decl) + '\n    // MODMAT\n')
src = rep(src, '    float[68] mrGain;\n', '    float[68] mrGain;\n    int[20]   eType;    // EURO: Eurorack rack (see build_euro.py)\n    int[20]   eMode;\n    int[20]   eRst;\n    int[80]   eSrc;\n    float[80] eGain;\n    float[160] eK;\n')
src = rep(src, '    // RESO-HAND-BEGIN\n', '\n'.join(hand) + '\n    // RESO-HAND-BEGIN\n')
src = rep(src, '        fxInit();\n        cvInit();\n', '''        for (int ei = 0; ei < 20; ++ei)   // EURO: start values
            eRst.at (ei) = 1;

        for (int ei = 0; ei < 160; ++ei)
            eK.at (ei) = 0.5f;

        for (int ei = 0; ei < 80; ++ei)
            eGain.at (ei) = 1.0f;

        fxInit();
        for (int ei = 0; ei < 20; ++ei)
            fxMix.at (10 + ei) = 0.5f;

        cvInit();
''')
js = '''    // EURO: Eurorack rack of Njohrr Modular
    {
        const ESRC = ["Off", "Synth L", "Synth R", "Audio In L", "Audio In R"];
        for (let m = 0; m < %d; m++) ESRC.push("M" + (m + 1) + " A", "M" + (m + 1) + " B");
        const ETYPE = %s;
        for (let m = 0; m < %d; m++) {
            const b = %d + %d * m, n = "Euro M" + (m + 1);
            L.push([b, n + " Type", 0, %d, 0, "", "sel", ETYPE, 1, "Type"]);
            for (let k = 0; k < 8; k++) L.push([b + 1 + k, n + " Knob " + (k + 1), 0, 1, 0.5, "", "sld", null, 1, "K" + (k + 1)]);
            L.push([b + 9, n + " Mode", 0, 7, 0, "", "sel", ["1", "2", "3", "4", "5", "6", "7", "8"], 1, "Mode"]);
            for (let c = 0; c < 4; c++) {
                L.push([b + 10 + c, n + " In " + (c + 1) + " Src", 0, %d, 0, "", "sel", ESRC, 1, "Src"]);
                L.push([b + 14 + c, n + " In " + (c + 1) + " Gain", 0, 2, 1, "", "sld", null, 1, "Gain"]);
            }
            L.push([b + 18, n + " FX Type", 0, 32, 0, "", "sel", FX_TYPES.map(t => t.n), 1, "FX"]);
        }
    }
''' % (NSLOT, str([x[0] for x in MODS]).replace("'", '"'), NSLOT, BASE, STRIDE, NTYPE - 1, NSRC - 1)
idx = rep(idx, '    // MODMAT: patch matrix of Njohrr Modular\n', js + '    // MODMAT: patch matrix of Njohrr Modular\n')
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('EURO applied')
