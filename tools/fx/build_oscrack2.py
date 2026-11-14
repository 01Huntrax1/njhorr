#!/usr/bin/env python3
"""Idempotent, marker OSCFX4-DSP: the oscillator FX racks get the layout of the main rack: 16 slots per oscillator, On / Mode / Sync /
filter-effect envelope per slot and a processing order (drag in the list).  Builds on OSCFX3-DSP (virtual slots per voice).
 ids 8000 + 272 * osc + 16 * slot + k (k 0 type, 1 on, 2 mix, 3 mode, 4..9 P1..P6, 10 sync, 11 env sustain, 12 env release),
 order 8000 + 272 * osc + 256 + pos (pos 0..15 holds the slot number).
 Virtual slot of voice v: 48 + v * 96 + osc * 16 + slot (816 slots in all)."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'OSCFX4-DSP' in src:
    print('already applied'); sys.exit(0)
assert 'OSCFX3-DSP' in src
def rep(old, new, cnt=1):
    global src
    assert src.count(old) == cnt, (old[:80], src.count(old))
    src = src.replace(old, new)

# ---- remove the 4-slot parameters (6300.. and 7600..)
n0 = len(src)
src, a = re.subn(r'    input event float param(?:63\d\d|64\d\d|76\d\d) \[\[ name: "OSC \d FX \d [^\n]*\n', '', src)
src, b = re.subn(r'    event param(?:63\d\d|64\d\d|76\d\d) \(float v\) \{ rkSet \([^\n]*\n', '', src)
print('removed', a, b); assert a == 192 + 48 and b == 192 + 48
idx, c = re.subn(r'    \[(?:63\d\d|64\d\d|76\d\d), "OSC \d FX \d [^\n]*\n', '', idx); print('specs removed', c); assert c == 240

# ---- arrays: 816 slots (17 x the 48 of the original sizes)
SIZES = {'fxType':320,'fxOn':320,'fxMix':320,'fxMode':320,'fxEnvSus':320,'fxEnvRel':320,'fxEnvLv':320,'fxEnvSt':320,'fxEnvSeen':320,'fxEnvGc':320,'fxFcS':320,
         'fxEnvCt':320,'fxSync':320,'fxP':2560,'fxDirty':320,'fxD':5120,'fxF':10240,'awS':10240,'awD':5760,'mgG':61440,'csV':245760,'wpV':30720,'plN':640,'awT':11520,
         'fxI':10240,'fxPh':1280,'fxArena':12582912,'peqB':57600,'peqC':76800,'peqZ':61440,'peqCh':15360,'peqN':320,'peqK':23040}
NEW = {'fxType':1088,'fxOn':1088,'fxMix':1088,'fxMode':1088,'fxEnvSus':1088,'fxEnvRel':1088,'fxEnvLv':1088,'fxEnvSt':1088,'fxEnvSeen':1088,'fxEnvGc':1088,'fxFcS':1088,
       'fxEnvCt':1088,'fxSync':1088,'fxP':4992,'fxDirty':1088,'fxD':13056,'fxF':32768,'awS':32768,'awD':19584,'mgG':208896,'csV':835584,'wpV':104448,'plN':1632,'awT':39168,
       'fxI':19584,'fxPh':3264,'fxArena':22020096,'peqB':195840,'peqC':261120,'peqZ':208896,'peqCh':52224,'peqN':1088,'peqK':78336}
for nm, old in SIZES.items():
    m = re.search(r'^    (\w+)\[%d\](\s+)%s;' % (old, nm), src, re.M)
    assert m, nm
    src = src[:m.start()] + '    %s[%d]%s%s;' % (m.group(1), NEW[nm], m.group(2), nm) + src[m.end():]
rep('            for (int fs = 0; fs < 240; ++fs)\n                fxDirty.at (fs) = true;', '            for (int fs = 0; fs < 816; ++fs)\n                fxDirty.at (fs) = true;')
rep('        for (int s = 48; s < 240; ++s)   // OSCFX3-DSP', '        for (int s = 48; s < 816; ++s)   // OSCFX3-DSP')
rep('    int[64]       fxSeq;', '    int[96]       oscOrd;   // OSCFX4-DSP: processing order of the oscillator racks (position -> slot), 16 per oscillator\n    int[96]       oscSeq;\n    int[64]       fxSeq;')
rep('        for (int o = 0; o < 48; ++o)\n        {\n            fxOrder.at (o) = o - (o / 16) * 16;', '        for (int o = 0; o < 96; ++o)   // OSCFX4-DSP\n        {\n            oscOrd.at (o) = o - (o / 16) * 16;\n            oscSeq.at (o) = o - (o / 16) * 16;\n        }\n\n        for (int o = 0; o < 48; ++o)\n        {\n            fxOrder.at (o) = o - (o / 16) * 16;')

# ---- parameters
decl = []; hand = []; specs = []
TY = '        L.push'
def P(i, nm, lo, hi, ini, step, h, auto=False):
    decl.append('    input event float param%d [[ name: "%s", min: %s, max: %s, init: %s, step: %s%s ]];' % (i, nm, lo, hi, ini, step, '' if auto else ', automatable: false'))
    hand.append('    event param%d (float v) { %s }' % (i, h))
for o in range(6):
    for sl in range(16):
        b = 8000 + 272 * o + 16 * sl; n = 'OSC %d FX %d ' % (o + 1, sl + 1)
        P(b,     n + 'Type', '0.0', '31.0', '0.0', '1.0', 'rkSet2 (%d, %d, 0, v);' % (o, sl))
        P(b + 1, n + 'On',   '0.0', '1.0', '1.0', '1.0', 'rkSet2 (%d, %d, 1, v);' % (o, sl))
        P(b + 2, n + 'Mix',  '0.0', '1.0', '1.0', '0.001', 'rkSet2 (%d, %d, 2, v);' % (o, sl), True)
        P(b + 3, n + 'Mode', '0.0', '32.0', '0.0', '1.0', 'rkSet2 (%d, %d, 3, v);' % (o, sl))
        for k in range(6):
            P(b + 4 + k, n + 'P%d' % (k + 1), '0.0', '1.0', '0.5', '0.001', 'rkSet2 (%d, %d, %d, v);' % (o, sl, 4 + k), True)
        P(b + 10, n + 'Sync', '0.0', '18.0', '0.0', '1.0', 'rkSet2 (%d, %d, 10, v);' % (o, sl))
        P(b + 11, n + 'Env Sustain', '0.0', '1.0', '1.0', '0.001', 'rkSet2 (%d, %d, 11, v);' % (o, sl))
        P(b + 12, n + 'Env Release', '0.0', '1.0', '0.3', '0.001', 'rkSet2 (%d, %d, 12, v);' % (o, sl))
    for k in range(16):
        P(8000 + 272 * o + 256 + k, 'OSC %d FX Order %d' % (o + 1, k + 1), '0.0', '15.0', '%d.0' % k, '1.0', 'oscOrd.at (%d) = clamp (int (v + 0.5f), 0, 15); oscRebuild (%d);' % (o * 16 + k, o))
rep('    // OSCFX3-DSP\n', '    // OSCFX4-DSP\n' + '\n'.join(decl) + '\n    // OSCFX3-DSP\n')
rep('    // RESO-HAND-BEGIN\n', '\n'.join(hand) + '\n    // RESO-HAND-BEGIN\n')

# ---- DSP functions
a = src.index('    void rkSet (int sl, int k, float v)'); b = src.index('    void opSet (int o, int k, float v)')
src = src[:a] + '''    // OSCFX4-DSP: parameter k of slot sl of oscillator o, written to the copies of all 8 voices
    //   k 0 type, 1 on, 2 mix, 3 mode, 4..9 P1..P6, 10 sync, 11 env sustain, 12 env release
    void rkSet2 (int o, int sl, int k, float v)
    {
        for (int vi = 0; vi < 8; ++vi)
        {
            int s = 48 + vi * 96 + o * 16 + sl;

            if (k == 0)
            {
                int nt = int (v + 0.5f);
                nt = oscFxLight (nt) ? nt : 0;

                if (nt != fxType.at (s))
                {
                    fxType.at (s) = nt;
                    fxResetSlot (s);
                }

                fxDirty.at (s) = true;
            }
            else if (k == 1)
                fxOn.at (s) = v;
            else if (k == 2)
                fxMix.at (s) = v;
            else if (k == 3)
            {
                fxMode.at (s) = clamp (int (v + 0.5f), 0, 32);
                fxDirty.at (s) = true;
            }
            else if (k == 10)
            {
                fxSync.at (s) = clamp (int (v + 0.5f), 0, 18);
                fxDirty.at (s) = true;
            }
            else if (k == 11)
            {
                fxEnvSus.at (s) = clamp (v, 0.0f, 1.0f);
                fxDirty.at (s) = true;
            }
            else if (k == 12)
            {
                fxEnvRel.at (s) = clamp (v, 0.0f, 1.0f);
                fxDirty.at (s) = true;
            }
            else
            {
                fxP.at (s * 6 + k - 4) = v;
                fxDirty.at (s) = true;
            }
        }
    }

    // processing order of oscillator o: an order that is not a permutation of the 16 slots (UI still sending the values one by one) is ignored
    void oscRebuild (int o)
    {
        int[16] used;
        bool    valid = true;

        for (int k = 0; k < 16; ++k)
        {
            int s = clamp (oscOrd.at (o * 16 + k), 0, 15);

            if (used.at (s) != 0)
                valid = false;

            used.at (s) = 1;
        }

        if (valid)
            for (int k = 0; k < 16; ++k)
                oscSeq.at (o * 16 + k) = clamp (oscOrd.at (o * 16 + k), 0, 15);
    }

''' + src[b:]
rep('(t >= 14 && t <= 15)', '(t == 14)')

# ---- processing and voice start
rep('                        int      fb0  = 48 + i * 24 + o * 4;', '                        int      fb0  = 48 + i * 96 + o * 16;')
rep('''                        for (int fq = 0; fq < 4; ++fq)
                        {
                            int fs = fb0 + fq;
''', '''                        for (int fq = 0; fq < 16; ++fq)
                        {
                            int fs = fb0 + oscSeq.at (o * 16 + fq);
''')
rep('''            for (int fq = 0; fq < 4; ++fq)   // OSCFX3-DSP: fresh effect state at the start of the voice
            {
                int fs = 48 + v * 24 + o * 4 + fq;''', '''            for (int fq = 0; fq < 16; ++fq)   // OSCFX3-DSP: fresh effect state at the start of the voice
            {
                int fs = 48 + v * 96 + o * 16 + fq;''')
open(path, 'w').write(src)

# ---- index.js specs (generated like the main rack ones)
js = '''    // OSCFX4-DSP: oscillator FX racks: ids 8000 + 272 * osc + 16 * slot + k, order 8000 + 272 * osc + 256 + pos
    for (let o = 0; o < 6; o++) {
        for (let sl = 0; sl < 16; sl++) {
            const b = 8000 + 272 * o + 16 * sl, n = "OSC " + (o + 1) + " FX " + (sl + 1);
            L.push([b,     n + " Type", 0, 31, 0, "", "sel", FX_TYPES.map(t => t.n).slice(0, 32), 1, "Type"]);
            L.push([b + 1, n + " On",   0, 1, 1, "", "btn", ["Off", "On"], 1, "On"]);
            L.push([b + 2, n + " Mix",  0, 1, 1, "", "sld", null, 1, "Mix"]);
            L.push([b + 3, n + " Mode", 0, 32, 0, "", "sel", FX_FILTER_TYPES, 1, "Mode"]);
            for (let k = 0; k < 6; k++) L.push([b + 4 + k, n + " P" + (k + 1), 0, 1, 0.5, "", "sld", null, 1, "P" + (k + 1)]);
            L.push([b + 10, n + " Sync", 0, 18, 0, "", "sel", ["Off"].concat(SYNC_DIVS), 1, "Sync"]);
            L.push([b + 11, n + " Env Sustain", 0, 1, 1, "", "sld", null, 1, "Sustain"]);
            L.push([b + 12, n + " Env Release", 0, 1, 0.3, "", "sld", null, 1, "Release"]);
        }
        for (let k = 0; k < 16; k++) L.push([8000 + 272 * o + 256 + k, "OSC " + (o + 1) + " FX Order " + (k + 1), 0, 15, k, "", "stp", null, 1, "Order"]);
    }
'''
m = '    FX_RACKS.forEach((rack, rk) => { for (let sl = 0; sl < 10; sl++) L.push([940 + rk * 10 + sl'
assert idx.count(m) == 1
idx = idx.replace(m, js + m)
open(ipath, 'w').write(idx)
print('applied')
