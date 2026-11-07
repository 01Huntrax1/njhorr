#!/usr/bin/env python3
"""Idempotent: 16 effect slots per rack instead of 10, marker FX-SLOTS.
The old ids keep their meaning (slots 1-10 of every rack). Slots 11-16 are new global slots 30..47 (rack rk, extra slot j -> 30 + rk * 6 + j):
  slot parameters  3200 + (rk * 6 + j) * 10 + (0 Type, 1 On, 2 Mix, 3 Mode, 4..9 P1..P6)
  processing order 3380 + rk * 6 + j  (the "FX Order" parameters of the old slots 641.. now run 0..15 and are rack-local slot numbers)
  tempo sync       3400 + rk * 6 + j
Per-slot arrays grow to 48 slots (arena 48 x 196608 floats)."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'FX-SLOTS' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, cnt=1):
    global src
    assert src.count(old) == cnt, (old[:80], src.count(old))
    src = src.replace(old, new)
def resize(name, size):
    global src
    pat = re.compile(r'(\b(?:int|float|bool|float64)\[)(\d+)(\]\s+' + name + r';)')
    assert len(pat.findall(src)) == 1, name
    src = pat.sub(lambda m: m.group(1) + str(size) + m.group(3), src)
for n in ['fxType', 'fxOn', 'fxMix', 'fxMode', 'peqN', 'fxEnvSus', 'fxEnvRel', 'fxEnvLv', 'fxEnvSt', 'fxEnvSeen', 'fxEnvGc', 'fxFcS', 'fxEnvCt', 'fxSync', 'fxDirty', 'fxOrder', 'fxSeq']:
    resize(n, 64)
resize('fxP', 512); resize('fxD', 1024); resize('fxI', 2048); resize('fxPh', 256)
resize('peqB', 11520); resize('peqC', 15360); resize('peqZ', 12288); resize('peqCh', 3072); resize('peqK', 4608)
resize('fxArena', 9437184)
rep('   // 30 slots x 196608 floats', '   // FX-SLOTS: 48 slots x 196608 floats')
# helpers
rep('    // Selects the effect of a slot (its memory is cleared only when the type really changes)\n',
    '    // FX-SLOTS: global slot numbers: 0..29 = slots 1-10 of the racks (rk * 10 + k), 30..47 = slots 11-16 (30 + rk * 6 + j)\n'
    '    int fxRk (int s)            { return s < 30 ? s / 10 : (s - 30) / 6; }\n'
    '    int fxG (int rk, int ls)    { return ls < 10 ? rk * 10 + ls : 30 + rk * 6 + (ls - 10); }\n\n'
    '    // Selects the effect of a slot (its memory is cleared only when the type really changes)\n')
rep('        cvUpdateOwner (s / 10);', '        cvUpdateOwner (fxRk (s));')
rep('            int rk = s / 10;\n\n            if (cvOwner.at (rk) == s)', '            int rk = fxRk (s);\n\n            if (cvOwner.at (rk) == s)')
rep('        int   rk = s / 10;\n\n        if (cvOwner.at (rk) != s)', '        int   rk = fxRk (s);\n\n        if (cvOwner.at (rk) != s)')
rep('''        for (int k = 9; k >= 0; --k)
            if (fxType.at (rk * 10 + k) == 12)
                ow = rk * 10 + k;''', '''        for (int k = 15; k >= 0; --k)
            if (fxType.at (fxG (rk, k)) == 12)
                ow = fxG (rk, k);''')
rep('            for (int fs = 0; fs < 30; ++fs)\n                fxDirty.at (fs) = true;', '            for (int fs = 0; fs < 48; ++fs)\n                fxDirty.at (fs) = true;')
rep('        int b = clamp (c.bank, 0, 29);', '        int b = clamp (c.bank, 0, 47);')
rep('(bank = global slot 0..29, 240 values)', '(bank = global slot 0..47, 240 values)')
rep('slot (0..29) that owns', 'slot (0..47) that owns')
# order
i = src.index('    // Rebuilds the processing order from the 10 "FX Order" values'); j = src.index('    // RBJ biquad of one EQ band')
src = src[:i] + '''    // Rebuilds the processing order from the 16 "FX Order" values of a rack (rack-local slot numbers 0..15); an order that is not a permutation
    // of the 16 slots (for example while the UI is still sending the values one by one) is ignored
    void fxRebuildSeq (int rk)
    {
        int[16] used;
        bool    valid = true;
        int     ob    = rk * 16;

        for (int k = 0; k < 16; ++k)
        {
            int s = clamp (fxOrder.at (ob + k), 0, 15);

            if (used.at (s) != 0)
                valid = false;

            used.at (s) = 1;
        }

        if (valid)
        {
            for (int k = 0; k < 16; ++k)
                fxSeq.at (ob + k) = clamp (fxOrder.at (ob + k), 0, 15);
        }
    }

''' + src[j:]
rep('''        for (int k = 0; k < 10; ++k)
            v = fxRunSlot (rk * 10 + fxSeq.at (rk * 10 + k), v);''', '''        for (int k = 0; k < 16; ++k)
            v = fxRunSlot (fxG (rk, fxSeq.at (rk * 16 + k)), v);''')
rep('''        for (int s = 0; s < 30; ++s)
        {
            fxType.at (s)  = 0;
            fxOn.at (s)    = 1.0f;
            fxMix.at (s)   = 1.0f;
            fxMode.at (s)  = 0;
            fxDirty.at (s) = true;
            fxOrder.at (s) = s - (s / 10) * 10;
            fxSeq.at (s)   = s - (s / 10) * 10;

            for (int k = 0; k < 6; ++k)
                fxP.at (s * 6 + k) = 0.5f;
        }''', '''        for (int s = 0; s < 48; ++s)
        {
            fxType.at (s)  = 0;
            fxOn.at (s)    = 1.0f;
            fxMix.at (s)   = 1.0f;
            fxMode.at (s)  = 0;
            fxDirty.at (s) = true;

            for (int k = 0; k < 6; ++k)
                fxP.at (s * 6 + k) = 0.5f;
        }

        for (int o = 0; o < 48; ++o)
        {
            fxOrder.at (o) = o - (o / 16) * 16;
            fxSeq.at (o)   = o - (o / 16) * 16;
        }''')
# old order handlers: rack-local, stride 16, range 0..15
pat = re.compile(r'event (param\d+)(\s+)\(float v\) \{ fxOrder\.at \((\d+)\) = clamp \(int \(v \+ 0\.5f\), 0, 9\); fxRebuildSeq \((\d)\); \}')
def fix(m):
    n = int(m.group(3)); rk = n // 10; k = n % 10
    assert rk == int(m.group(4))
    return 'event %s%s(float v) { fxOrder.at (%d) = clamp (int (v + 0.5f), 0, 15); fxRebuildSeq (%d); }   // FX-SLOTS' % (m.group(1), m.group(2), rk * 16 + k, rk)
src, n = pat.subn(fix, src); assert n == 30, n
pat = re.compile(r'(name: "[A-Za-z0-9 ]+ FX Order \d+", min: 0\.0, max: )9\.0')
src, n = pat.subn(lambda m: m.group(1) + '15.0', src); assert n == 30, n
# new parameters
RN = ['Main', 'Bus 1', 'Bus 2']
decl = ''; hand = ''
for rk in range(3):
    for j in range(6):
        s = 30 + rk * 6 + j; b = 3200 + (rk * 6 + j) * 10; nm = '%s FX %d' % (RN[rk], 11 + j)
        decl += '    input event float param%d [[ name: "%s Type", min: 0.0, max: 27.0, init: 0.0, step: 1.0 ]];   // FX-SLOTS\n' % (b, nm)
        decl += '    input event float param%d [[ name: "%s On", min: 0.0, max: 1.0, init: 1.0, step: 1.0 ]];\n' % (b + 1, nm)
        decl += '    input event float param%d [[ name: "%s Mix", min: 0.0, max: 1.0, init: 1.0 ]];\n' % (b + 2, nm)
        decl += '    input event float param%d [[ name: "%s Mode", min: 0.0, max: 32.0, init: 0.0, step: 1.0 ]];\n' % (b + 3, nm)
        for k in range(6):
            decl += '    input event float param%d [[ name: "%s P%d", min: 0.0, max: 1.0, init: 0.5 ]];\n' % (b + 4 + k, nm, k + 1)
        hand += '    event param%d (float v) { fxSetType (%d, int (v + 0.5f)); }\n' % (b, s)
        hand += '    event param%d (float v) { fxOn.at (%d) = v; }\n' % (b + 1, s)
        hand += '    event param%d (float v) { fxMix.at (%d) = v; }\n' % (b + 2, s)
        hand += '    event param%d (float v) { fxMode.at (%d) = clamp (int (v + 0.5f), 0, 32); fxDirty.at (%d) = true; }\n' % (b + 3, s, s)
        for k in range(6):
            hand += '    event param%d (float v) { fxP.at (%d) = v; fxDirty.at (%d) = true; }\n' % (b + 4 + k, s * 6 + k, s)
        decl += '    input event float param%d [[ name: "%s Sync", min: 0.0, max: 27.0, init: 0.0, step: 1.0 ]];\n' % (3400 + rk * 6 + j, nm)
        hand += '    event param%d (float v) { fxSync.at (%d) = clamp (int (v + 0.5f), 0, 18); fxDirty.at (%d) = true; }\n' % (3400 + rk * 6 + j, s, s)
        decl += '    input event float param%d [[ name: "%s FX Order %d", min: 0.0, max: 15.0, init: %d, step: 1.0 ]];\n' % (3380 + rk * 6 + j, RN[rk], 11 + j, 10 + j)
        hand += '    event param%d (float v) { fxOrder.at (%d) = clamp (int (v + 0.5f), 0, 15); fxRebuildSeq (%d); }\n' % (3380 + rk * 6 + j, rk * 16 + 10 + j, rk)
m = re.search(r'    input event float param3120 [^\n]*\n', src); assert m
src = src[:m.end()] + decl + src[m.end():]
rep('    // FX-SYNC: sync divisions of the effect slots\n', '    // FX-SLOTS: slots 11-16 of the three racks\n' + hand + '    // FX-SYNC: sync divisions of the effect slots\n')
open(P, 'w').write(src)
print('ok')
