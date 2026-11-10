#!/usr/bin/env python3
"""Idempotent (marker MOD-ARP64): the 303 pattern grows from 16 to 64 steps.  Steps 1-16 keep their ids (5200 note, 5216 accent, 5232 slide, 5248 gate,
5264 length - max now 64); steps 17-64 are new: note 5500 + (n - 17), accent 5548 + .., slide 5596 + .., gate 5644 + .. (all `automatable: false`).
Steps 17-64 default to a repeat of the 16 step pattern."""
import os, sys
P = os.path.join(os.path.dirname(__file__), '..', '..', 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'MOD-ARP64' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:80], src.count(old))
    src = src.replace(old, new)

NOTE = [0, 0, 12, 0, 0, 10, 0, 7, 0, 12, 0, 0, 3, 5, 0, 0]
ACC  = [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0]
SLD  = [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0]
GATE = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0]
BASES = (5500, 5548, 5596, 5644)

rep('input event float param5264 [[ name: "303 Length", min: 1.0, max: 16.0, init: 16.0,', 'input event float param5264 [[ name: "303 Length", min: 1.0, max: 64.0, init: 16.0,')
rep('    float[16]   a3Note, a3Acc, a3Slide, a3Gate;   // MOD-ARP303', '    float[64]   a3Note, a3Acc, a3Slide, a3Gate;   // MOD-ARP303 / MOD-ARP64')
rep('int   si    = arpStep % clamp (int (a3Len + 0.5f), 1, 16);', 'int   si    = arpStep % clamp (int (a3Len + 0.5f), 1, 64);')

decl = ''
names = ('Note', 'Accent', 'Slide', 'Gate')
for r in range(4):
    for k in range(16, 64):
        init = (NOTE, ACC, SLD, GATE)[r][k % 16]
        lo, hi = ('-12.0', '24.0') if r == 0 else ('0.0', '1.0')
        decl += '    input event float param%d [[ name: "303 Step %d %s", min: %s, max: %s, init: %d.0, step: 1.0, automatable: false ]];   // MOD-ARP64\n' % (BASES[r] + k - 16, k + 1, names[r], lo, hi, init)
a = '    input event float param5264 '
i = src.index(a); j = src.index('\n', i) + 1
src = src[:j] + decl + src[j:]

ev = ''
arrs = ('a3Note', 'a3Acc', 'a3Slide', 'a3Gate')
for r in range(4):
    for k in range(16, 64):
        ev += '    event param%d (float v) { %s.at (%d) = v; }   // MOD-ARP64\n' % (BASES[r] + k - 16, arrs[r], k)
rep('    event param5264 (float v) { a3Len = v; }\n', '    event param5264 (float v) { a3Len = v; }\n' + ev)

ini = '        // MOD-ARP64: steps 17-64 repeat the default pattern\n'
for name, arr in zip(arrs, (NOTE, ACC, SLD, GATE)):
    for k in range(16, 64):
        if arr[k % 16] != 0:
            ini += '        %s.at (%d) = %d.0f;\n' % (name, k, arr[k % 16])
ini += '\n'
rep('        for (int sm = 0; sm < 10; ++sm)   // MOD-SEQ\n        {\n            seqLen.at (sm)  = 8.0f;', ini + '        for (int sm = 0; sm < 10; ++sm)   // MOD-SEQ\n        {\n            seqLen.at (sm)  = 8.0f;')
open(P, 'w').write(src)
print('applied')
