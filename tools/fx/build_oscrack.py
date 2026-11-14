#!/usr/bin/env python3
"""Idempotent, marker OSCFX3-DSP: the per-oscillator pre-matrix rack runs the memory-light effects of the main FX section.
 4 slots per oscillator, ids 6300 + 32*osc + 8*slot + k (k0 type 0..31, k1 mix, k2..7 P1..P6) as before,
 plus Mode 7600 + 2*(osc*4+slot) and On 7601 + 2*(osc*4+slot).
 Every voice owns a virtual main-rack slot 48 + voice*24 + osc*4 + slot (240 slots in all, small 16384-float arena).
 Filter / Distortion / Resonator of the OSC pages remain fixed stages (order = Pre-Matrix Order) in front of the rack."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'OSCFX3-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, cnt=1):
    global src
    assert src.count(old) == cnt, (old[:80], src.count(old))
    src = src.replace(old, new)

# ---- 1. arrays: 48 -> 240 slots
for nm, old, new in [('fxType','int[64]','int[320]'),('fxOn','float[64]','float[320]'),('fxMix','float[64]','float[320]'),('fxMode','int[64]','int[320]'),
    ('fxEnvSus','float[64]','float[320]'),('fxEnvRel','float[64]','float[320]'),('fxEnvLv','float[64]','float[320]'),('fxEnvSt','int[64]','int[320]'),
    ('fxEnvSeen','int[64]','int[320]'),('fxEnvGc','float[64]','float[320]'),('fxFcS','float[64]','float[320]'),('fxEnvCt','int[64]','int[320]'),
    ('fxSync','int[64]','int[320]'),('fxP','float[512]','float[2560]'),('fxDirty','bool[64]','bool[320]'),('fxD','float[1024]','float[5120]'),
    ('fxF','float[2048]','float[10240]'),('awS','float64[2048]','float64[10240]'),('awD','float64[1152]','float64[5760]'),('mgG','float[12288]','float[61440]'),
    ('csV','float[49152]','float[245760]'),('wpV','float[6144]','float[30720]'),('plN','int64[128]','int64[640]'),('awT','float64[2304]','float64[11520]'),
    ('fxI','int[2048]','int[10240]'),('fxPh','float64[256]','float64[1280]'),('fxArena','float[9437184]','float[12582912]'),
    ('peqB','float[11520]','float[57600]'),('peqC','float[15360]','float[76800]'),('peqZ','float[12288]','float[61440]'),('peqCh','int[3072]','int[15360]'),
    ('peqN','int[64]','int[320]'),('peqK','float[4608]','float[23040]')]:
    m = re.search(r'^    %s\s+%s;' % (re.escape(old), nm), src, re.M)
    if not m: m = re.search(r'^    %s\s+%s\s*;' % (re.escape(old), nm), src, re.M)
    assert m, nm
    src = src[:m.start()] + '    %s %s;' % (new, nm) + src[m.end():]

# ---- 2. arena stride
n = len(re.findall(r's \* 196608', src)); print('stride uses', n)
src = src.replace('s * 196608', 'fxAb (s)')
rep('    int fxRk (int s)            {', '    int fxAb (int s)            { return s < 48 ? s * 196608 : 9437184 + (s - 48) * 16384; }   // OSCFX3-DSP\n    int fxRk (int s)            {')
rep('        for (int i = 0; i < 196608; ++i)\n            fxArena.at (ab + i) = 0.0f;', '        int al = s < 48 ? 196608 : 16384;\n\n        for (int i = 0; i < al; ++i)\n            fxArena.at (ab + i) = 0.0f;')
rep('            for (int fs = 0; fs < 48; ++fs)\n                fxDirty.at (fs) = true;', '            for (int fs = 0; fs < 240; ++fs)\n                fxDirty.at (fs) = true;')
# fxInit
rep('''        for (int o = 0; o < 48; ++o)
        {
            fxOrder.at (o) = o - (o / 16) * 16;''', '''        for (int s = 48; s < 240; ++s)   // OSCFX3-DSP: per voice slots of the oscillator racks
        {
            fxType.at (s)  = 0;
            fxOn.at (s)    = 1.0f;
            fxMix.at (s)   = 1.0f;
            fxMode.at (s)  = 0;
            fxDirty.at (s) = true;
            fxSync.at (s)  = 0;
            fxEnvSus.at (s) = 1.0f;
            fxEnvRel.at (s) = 0.3f;

            for (int k = 0; k < 6; ++k)
                fxP.at (s * 6 + k) = 0.5f;
        }

        for (int o = 0; o < 48; ++o)
        {
            fxOrder.at (o) = o - (o / 16) * 16;''')

# ---- 3. params
for o in range(6):
    for q in range(4):
        sl = o * 4 + q
        i = 6300 + 32 * o + 8 * q
        rep('    input event float param%d [[ name: "OSC %d FX %d Type", min: 0.0, max: 7.0, init: %d.0, step: 1.0 ]];' % (i, o + 1, q + 1, [1,2,3,0][q]),
            '    input event float param%d [[ name: "OSC %d FX %d Type", min: 0.0, max: 31.0, init: 0.0, step: 1.0 ]];' % (i, o + 1, q + 1))
decl = []; hand = []; specs = []
for sl in range(24):
    o, q = divmod(sl, 4); nm = 'OSC %d FX %d ' % (o + 1, q + 1)
    decl.append('    input event float param%d [[ name: "%sMode", min: 0.0, max: 32.0, init: 0.0, step: 1.0, automatable: false ]];' % (7600 + 2 * sl, nm))
    decl.append('    input event float param%d [[ name: "%sOn", min: 0.0, max: 1.0, init: 1.0, step: 1.0, automatable: false ]];' % (7601 + 2 * sl, nm))
    hand.append('    event param%d (float v) { rkSet (%d, 8, v); }' % (7600 + 2 * sl, sl))
    hand.append('    event param%d (float v) { rkSet (%d, 9, v); }' % (7601 + 2 * sl, sl))
    specs.append('    [%d, "%sMode", 0, 32, 0, "", "knb", null, 1, "Mode", null],' % (7600 + 2 * sl, nm))
    specs.append('    [%d, "%sOn", 0, 1, 1, "", "sel", ["Off", "On"], 1, "On", null],' % (7601 + 2 * sl, nm))
rep('    // OSCFX2-DSP\n', '    // OSCFX3-DSP\n' + '\n'.join(decl) + '\n    // OSCFX2-DSP\n')
rep('    // RESO-HAND-BEGIN\n', '\n'.join(hand) + '\n    // RESO-HAND-BEGIN\n')

# ---- 4. rkSet
rep('''    void rkSet (int sl, int k, float v)
    {
        rkP.at (sl * 8 + k) = v;
    }
''', '''    // OSCFX3-DSP: light effect types of the main rack that may run per voice (no big delay lines)
    bool oscFxLight (int t)
    {
        return (t >= 1 && t <= 2) || (t >= 4 && t <= 7) || (t >= 9 && t <= 11) || (t >= 14 && t <= 15) || (t >= 17 && t <= 28) || t == 30;
    }

    void rkSet (int sl, int k, float v)
    {
        for (int vi = 0; vi < 8; ++vi)
        {
            int s = 48 + vi * 24 + sl;

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
                fxMix.at (s) = v;
            else if (k == 8)
            {
                fxMode.at (s) = clamp (int (v + 0.5f), 0, 32);
                fxDirty.at (s) = true;
            }
            else if (k == 9)
                fxOn.at (s) = v;
            else
            {
                fxP.at (s * 6 + k - 2) = v;
                fxDirty.at (s) = true;
            }
        }
    }
''')
rep('    float[256]    rkP;        // OSCFX-DSP: 24 slots x (type, mix, p1..p6) at slot * 8 + k\n', '')
# remove old defaults, legacy order mapping, voice state
src = re.sub(r'        for \(int rq = 0; rq < 24; \+\+rq\)   // OSCFX-DSP defaults.*?\n        \}\n\n', '', src, count=1, flags=re.S)
assert 'OSCFX-DSP defaults' not in src
src = re.sub(r'\n        if \(k == 45 && v > 0\.5f\)   // OSCFX-DSP.*?\n        \}\n', '\n', src, count=1, flags=re.S)
assert 'old presets with a different Pre-Matrix' not in src
rep('        float[384]  rkS;', '        // float[384]  rkS;')
src = re.sub(r'        // float\[384\]  rkS;[^\n]*\n        float\[49152\] rkB;[^\n]*\n', '', src)
rep('            for (int rq = 0; rq < 64; ++rq)\n                voices.at (v).rkS.at (o * 64 + rq) = 0.0f;\n',
    '''            for (int fq = 0; fq < 4; ++fq)   // OSCFX3-DSP: fresh effect state at the start of the voice
            {
                int fs = 48 + v * 24 + o * 4 + fq;

                if (fxType.at (fs) != 0)
                    fxResetSlot (fs);
            }
''')

# ---- 5. processing chain
a = src.index('                    for (int chSt = 0; chSt < 4; ++chSt)')
b = src.index('                    // ----- ring modulation (carrier x modulator)')
seg = src[a:b]
f0 = seg.index('                        // ----- filter -----')
f1 = seg.index('                        if (rkTy >= 4)')
body = seg[f0:f1]
new = '''                    for (int chSt = 0; chSt < 3; ++chSt)
                    {
                        int   rkTy    = chainOrder.at (chOrd * 3 + chSt) + 1;   // OSCFX3-DSP: Filter / Distortion / Resonator pages stay fixed stages
                        int   chStage = rkTy - 1;

''' + body.rstrip() + '''
                    }

                    // OSCFX3-DSP: four effects of the main FX section per oscillator (own instance per voice)
                    {
                        int      fb0  = 48 + i * 24 + o * 4;
                        bool     fxAct = false;
                        float<2> fxv  = float<2> (sL, stereo ? sR : sL);

                        for (int fq = 0; fq < 4; ++fq)
                        {
                            int fs = fb0 + fq;

                            if (fxType.at (fs) != 0 && fxOn.at (fs) > 0.5f)
                            {
                                fxv = fxRunSlot (fs, fxv);
                                fxAct = true;
                            }
                        }

                        if (fxAct)
                        {
                            sL = fxv[0];
                            sR = fxv[1];

                            if (fxv[0] != fxv[1])
                                stereo = true;
                        }
                    }

'''
src = src[:a] + new + src[b:]
open(path, 'w').write(src)

# ---- index.js specs
idx = re.sub(r'\[(63\d\d|64\d\d), "OSC (\d) FX (\d) Type", 0, 7, \d, "", "sel", \[[^\]]*\], 1, "Type", null\]',
             lambda m: '[%s, "OSC %s FX %s Type", 0, 31, 0, "", "knb", null, 1, "Type", null]' % (m.group(1), m.group(2), m.group(3)), idx)
open(ipath, 'w').write(idx)
print('applied')
