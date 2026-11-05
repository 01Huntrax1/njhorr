#!/usr/bin/env python3
"""Idempotent: Polarity switch of the LFOs, marker MOD-LFOBIP.
LFO 1-10 (parameters 3111..3120): 1 = Bipolar (-1..1, as before, default), 0 = Unipolar (0..1 = (v + 1) / 2).
The conversion happens where the matrix reads the source (per voice and global)."""
import re, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'MOD-LFOBIP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
decl = ''.join('    input event float param%d [[ name: "Mod LFO %d Bipolar", min: 0.0, max: 1.0, init: 1.0 ]];   // MOD-LFOBIP\n' % (3111 + i, i + 1) for i in range(10))
m = re.search(r'    input event float param3110 [^\n]*\n', src); assert m
src = src[:m.end()] + decl + src[m.end():]
hand = ''.join('    event param%d (float v) { lfoUni.at (%d) = v > 0.5f ? 0.0f : 1.0f; }\n' % (3111 + i, i) for i in range(10))
rep('    // FX-SYNC: sync divisions of the effect slots\n', '    // MOD-LFOBIP: polarity of LFO 1-10 (state 1 = unipolar; the default 0 = bipolar matches the parameter default)\n' + hand + '    // FX-SYNC: sync divisions of the effect slots\n')
rep('    float[16]   modBip;', '    float[16]   lfoUni;  // MOD-LFOBIP\n    float[16]   modBip;')
rep('''            if (mLfoMode.at (src - 1) > 0.5f)
                return voices.at (vi).lfoV.at (src - 1);
            return mLfoV.at (src - 1);''', '''            if (mLfoMode.at (src - 1) > 0.5f)
                return lfoPol (voices.at (vi).lfoV.at (src - 1), src - 1);   // MOD-LFOBIP
            return lfoPol (mLfoV.at (src - 1), src - 1);''')
rep('''            if (mLfoMode.at (src - 1) > 0.5f)
                return voices.at (lastVoice).lfoV.at (src - 1);
            return mLfoV.at (src - 1);''', '''            if (mLfoMode.at (src - 1) > 0.5f)
                return lfoPol (voices.at (lastVoice).lfoV.at (src - 1), src - 1);   // MOD-LFOBIP
            return lfoPol (mLfoV.at (src - 1), src - 1);''')
rep('    float srcValueVoice (int src, int vi)', '    // MOD-LFOBIP: -1..1 -> 0..1 when the LFO is unipolar\n    float lfoPol (float v, int i)\n    {\n        return lfoUni.at (i) > 0.5f ? v * 0.5f + 0.5f : v;\n    }\n\n    float srcValueVoice (int src, int vi)')
open(P, 'w').write(src)
print('ok')
