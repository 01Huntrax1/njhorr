#!/usr/bin/env python3
"""Idempotent, marker MODMAT: parameters of the patch matrix of the plugin "Njohrr Modular" (the router itself is added to patch_mod/ by build_modplugin.py).
 Nodes: 0 Synth, 1 Audio In, 2..17 FX module 1..16 (the 16 slots of the Main rack), 18 Out.
 Cable sources (value of a Src parameter): 0 off, 1 Synth, 2 Audio In, 3..18 FX module 1..16.
 ids 9700 + 8 * dest + 2 * cable + (0 src, 1 gain); dest 0..15 = FX module, 16 = Out; 4 cables each.
 node positions 9850 + 2 * node + (0 x, 1 y) in 0..1 (editor layout only, no DSP)."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'MODMAT' in src:
    print('already applied'); sys.exit(0)
def rep(t, old, new):
    assert t.count(old) == 1, (old[:60], t.count(old)); return t.replace(old, new)
decl, hand, js = [], [], []
def nm(d): return 'Out' if d == 16 else 'M%d' % (d + 1)
for d in range(17):
    for c in range(4):
        i = 9700 + 8 * d + 2 * c; k = d * 4 + c
        ini = 1 if (d == 16 and c == 0) else (2 if (d == 16 and c == 1) else 0)
        decl.append('    input event float param%d [[ name: "Patch %s Cable %d Src", min: 0.0, max: 18.0, init: %d.0, step: 1.0, automatable: false ]];' % (i, nm(d), c + 1, ini))
        decl.append('    input event float param%d [[ name: "Patch %s Cable %d Gain", min: 0.0, max: 2.0, init: 1.0, step: 0.001, automatable: false ]];' % (i + 1, nm(d), c + 1))
        hand.append('    event param%d (float v) { mrSrc.at (%d) = clamp (int (v + 0.5f), 0, 18); }' % (i, k))
        hand.append('    event param%d (float v) { mrGain.at (%d) = clamp (v, 0.0f, 2.0f); }' % (i + 1, k))
POS = [(0.0, 0.2), (0.0, 0.7)] + [(0.2 + 0.2 * (m % 4), 0.08 + 0.24 * (m // 4)) for m in range(16)] + [(1.0, 0.45)]
for n, (x, y) in enumerate(POS):
    for a, v in enumerate((x, y)):
        decl.append('    input event float param%d [[ name: "Patch Node %d %s", min: 0.0, max: 1.0, init: %.3f, step: 0.001, automatable: false ]];' % (9850 + 2 * n + a, n + 1, 'XY'[a], v))
        hand.append('    event param%d (float v) { }' % (9850 + 2 * n + a))
src = rep(src, '    // OSCFX4-DSP\n', '    // MODMAT\n' + '\n'.join(decl) + '\n    // OSCFX4-DSP\n')
src = rep(src, '    float driveAmt     = 0.1f;\n', '    float driveAmt     = 0.1f;\n    int[68]   mrSrc;    // MODMAT: source of every cable (see build_matrix.py)\n    float[68] mrGain;\n')
src = rep(src, '    // RESO-HAND-BEGIN\n', '\n'.join(hand) + '\n    // RESO-HAND-BEGIN\n')
js = '''    // MODMAT: patch matrix of Njohrr Modular
    {
        const MSRC = ["Off", "Synth", "Audio In"].concat(Array.from({ length: 16 }, (_, i) => "Module " + (i + 1)));
        const MPOS = %s;
        for (let d = 0; d < 17; d++) for (let c = 0; c < 4; c++) {
            const nm = d === 16 ? "Out" : "M" + (d + 1), i = 9700 + 8 * d + 2 * c;
            L.push([i,     "Patch " + nm + " Cable " + (c + 1) + " Src", 0, 18, d === 16 && c < 2 ? c + 1 : 0, "", "sel", MSRC, 1, "Src"]);
            L.push([i + 1, "Patch " + nm + " Cable " + (c + 1) + " Gain", 0, 2, 1, "", "sld", null, 1, "Gain"]);
        }
        for (let n = 0; n < 19; n++) for (let a = 0; a < 2; a++)
            L.push([9850 + 2 * n + a, "Patch Node " + (n + 1) + " " + "XY"[a], 0, 1, MPOS[n][a], "", "sld", null, 1, "XY"[a]]);
    }
''' % repr([[round(x, 3), round(y, 3)] for x, y in POS]).replace("'", '"')
m = '    FX_RACKS.forEach((rack, rk) => { for (let sl = 0; sl < 10; sl++) L.push([940 + rk * 10 + sl'
idx = rep(idx, m, js + m)
src = rep(src, '        fxInit();\n        cvInit();\n', '        for (int mi = 0; mi < 68; ++mi)   // MODMAT: start values (Synth and Audio In to Out, all cable gains 1)\n        {\n            mrSrc.at (mi)  = mi == 64 ? 1 : (mi == 65 ? 2 : 0);\n            mrGain.at (mi) = 1.0f;\n        }\n\n' + '        fxInit();\n        cvInit();\n')
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('MODMAT applied')
