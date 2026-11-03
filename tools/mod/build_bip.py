#!/usr/bin/env python3
"""Idempotent: Bipolar mode of the unipolar modulators, marker MOD-BIP.
Envelopes ENV 1-10 (parameters 3100..3109) and Velocity (3110): 0 = Unipolar (0..1, as before), 1 = Bipolar (value * 2 - 1, i.e. -1..1).
LFOs, Key and Random are bipolar already. The conversion happens where the matrix reads the source (per voice and global)."""
import re, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'MOD-BIP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
decl = ''.join('    input event float param%d [[ name: "Mod Env %d Bipolar", min: 0.0, max: 1.0, init: 0.0 ]];   // MOD-BIP\n' % (3100 + i, i + 1) for i in range(10))
decl += '    input event float param3110 [[ name: "Mod Velocity Bipolar", min: 0.0, max: 1.0, init: 0.0 ]];   // MOD-BIP\n'
m = re.search(r'    input event float param3059 [^\n]*\n', src); assert m
src = src[:m.end()] + decl + src[m.end():]
hand = ''.join('    event param%d (float v) { modBip.at (%d) = v > 0.5f ? 1.0f : 0.0f; }\n' % (3100 + i, i) for i in range(11))
rep('    // FX-SYNC: sync divisions of the effect slots\n', '    // MOD-BIP: bipolar switches of ENV 1-10 (0..9) and Velocity (10)\n' + hand + '    // FX-SYNC: sync divisions of the effect slots\n')
rep('    float[16]   envMaxNext;', '    float[16]   modBip;  // MOD-BIP: 1 = the source is mapped to -1..1 (ENV 1-10 at 0..9, Velocity at 10)\n    float[16]   envMaxNext;')
rep('            return voices.at (vi).menv.at (src - 11);', '            return bipMap (voices.at (vi).menv.at (src - 11), src - 11);   // MOD-BIP')
rep('            return voices.at (vi).velRaw;\n        if (src == 22)\n            return clamp', '            return bipMap (voices.at (vi).velRaw, 10);   // MOD-BIP\n        if (src == 22)\n            return clamp')
rep('            return envMax.at (src - 11);', '            return bipMap (envMax.at (src - 11), src - 11);   // MOD-BIP')
rep('            return lastVelV;\n        if (src == 22)', '            return bipMap (lastVelV, 10);   // MOD-BIP\n        if (src == 22)')
rep('    float srcValueVoice (int src, int vi)', '    // MOD-BIP: unipolar 0..1 -> bipolar -1..1 when the modulator\'s Bipolar switch is on\n    float bipMap (float v, int i)\n    {\n        return modBip.at (i) > 0.5f ? v * 2.0f - 1.0f : v;\n    }\n\n    float srcValueVoice (int src, int vi)')
open(P, 'w').write(src)
print('ok')
