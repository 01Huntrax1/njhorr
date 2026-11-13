#!/usr/bin/env python3
"""Idempotent, marker RND-DSP: 10 random modulators (RND 1 = source 23 as before, RND 2..10 = sources 44..52).
  Per RND r (base = 7500 + 8 * r), all non-automatable:
    +0 Mode (Note = one value per note | S&H | Glide | Walk)   +1 Rate Hz   +2 Sync   +3 Division (SYNC_DIVS index)
    +4 Smooth (slew)   +5 Distribution (Uniform | Gauss | Binary | Steps)   +6 Polarity (Bipolar | Unipolar)
    +7 Seed (0 = new random values for every note, 1..16 = the same value sequence on every note)
  The defaults of every RND are the old behaviour: one bipolar uniform value per note."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'RND-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src', n=1):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == n, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

# ---- the mod matrix accepts sources up to 52
assert src.count('max: 43.0') == 256
src = src.replace('max: 43.0', 'max: 52.0')
src = src.replace(', 0, 43); mmScan(); }', ', 0, 52); mmScan(); }')
assert src.count(', 0, 52); mmScan(); }') == 256
rep('L.push([b,     "Slot " + (i + 1) + " Source", 0, 43, 0,', 'L.push([b,     "Slot " + (i + 1) + " Source", 0, 52, 0,', 'idx')
rep('["Velocity", "Key", "Random"],', '["Velocity", "Key", "Random 1"],', 'idx')
rep('    Array.from({ length: 10 }, (_, i) => "Seq " + (i + 1))   // MOD-SEQ\n', '    Array.from({ length: 10 }, (_, i) => "Seq " + (i + 1)),   // MOD-SEQ\n    Array.from({ length: 9 }, (_, i) => "Random " + (i + 2))   // RND-DSP\n', 'idx')
rep('[34, "Sequencer"]];', '[34, "Sequencer"], [44, "Random"]];', 'idx')

# ---- parameters
MODES = 'Note|S&H|Glide|Walk'; DISTS = 'Uniform|Gauss|Binary|Steps'
decl = []; hand = []; specs = []
def P(i, nm, lo, hi, ini, step, h, spec):
    decl.append('    input event float param%d [[ name: "%s", min: %s, max: %s, init: %s, step: %s, automatable: false ]];' % (i, nm, lo, hi, ini, step))
    hand.append('    event param%d (float v) { %s }' % (i, h))
    specs.append('    [%d, "%s", %s, %s, %s, "", %s],' % (i, nm, lo, hi, ini, spec))
def sel(txt, lab=''): return '"sel", [%s], 1, "%s", null' % (', '.join('"%s"' % x for x in txt.split('|')), lab)
SYNC = ["8/1", "4/1", "2/1", "1/1", "1/2.", "1/2", "1/2T", "1/4.", "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16", "1/16T", "1/32", "1/32T"]
for r in range(10):
    b = 7500 + 8 * r; n = 'RND%d ' % (r + 1)
    P(b, n + 'Mode', '0.0', '3.0', '0.0', '1.0', 'rMode.at (%d) = clamp (int (v + 0.5f), 0, 3);' % r, sel(MODES, 'Mode'))
    P(b + 1, n + 'Rate', '0.05', '50.0', '4.0', '0.01', 'rRate.at (%d) = v;' % r, '"knb", null, 1, "Rate", null')
    P(b + 2, n + 'Sync', '0.0', '1.0', '0.0', '1.0', 'rSync.at (%d) = v > 0.5f ? 1 : 0;' % r, sel('Free|Sync', 'Sync'))
    P(b + 3, n + 'Division', '0.0', '17.0', '8.0', '1.0', 'rDiv.at (%d) = v;' % r, sel('|'.join(SYNC)))
    P(b + 4, n + 'Smooth', '0.0', '1.0', '0.0', '0.001', 'rSmooth.at (%d) = v;' % r, '"knb", null, 1, "Smooth", null')
    P(b + 5, n + 'Distribution', '0.0', '3.0', '0.0', '1.0', 'rDist.at (%d) = clamp (int (v + 0.5f), 0, 3);' % r, sel(DISTS, 'Distribution'))
    P(b + 6, n + 'Polarity', '0.0', '1.0', '0.0', '1.0', 'rUni.at (%d) = v > 0.5f ? 1 : 0;' % r, sel('Bipolar|Unipolar', 'Polarity'))
    P(b + 7, n + 'Seed', '0.0', '16.0', '0.0', '1.0', 'rSeed.at (%d) = clamp (int (v + 0.5f), 0, 16);' % r, '"knb", null, 1, "Seed", null')
d = re.search(r'    input event float param7499 \[\[[^\]]*\]\];', src).group(0)
rep(d, d + '\n    // RND-DSP\n' + '\n'.join(decl))
h = re.search(r'    event param7499 \(float v\)[^\n]*', src).group(0)
rep(h, h + '\n' + '\n'.join(hand))
s0 = re.search(r'    \[7499, "MSEG10 Node 8 Curve"[^\n]*', idx).group(0)
rep(s0, s0 + '\n' + '\n'.join(specs), 'idx')

# ---- state
rep('    // MSEG-DSP\n    int[16]     msMode;\n',
    '    // RND-DSP\n    int[16]     rMode;\n    float[16]   rRate;\n    int[16]     rSync;\n    float[16]   rDiv;\n    float[16]   rSmooth;\n    int[16]     rDist;\n    int[16]     rUni;\n    int[16]     rSeed;\n'
    '    // MSEG-DSP\n    int[16]     msMode;\n')
rep('            msLoopE.at (mi)     = 2;\n', '            msLoopE.at (mi)     = 2;\n            rMode.at (mi)       = 0;\n            rRate.at (mi)       = 4.0f;\n            rSync.at (mi)       = 0;\n            rDiv.at (mi)        = 8.0f;\n            rSmooth.at (mi)     = 0.0f;\n            rDist.at (mi)       = 0;\n            rUni.at (mi)        = 0;\n            rSeed.at (mi)       = 0;\n')
rep('        int[16]   vmNode;     // MSEG-DSP: target node (held node in stage 2)\n',
    '        int[16]   vmNode;     // MSEG-DSP: target node (held node in stage 2)\n        int[16]   rS;         // RND-DSP: random state\n        float[16] rV;         // RND-DSP: output (-1..1)\n        float[16] rPrev;      // RND-DSP: previous value\n        float[16] rTgt;       // RND-DSP: next value\n        float[16] rPh;        // RND-DSP: phase 0..1\n')

# ---- engine
rep('    // MSEG-DSP: advances MSEG m of one voice by one sample\n', '''    // RND-DSP: one uniform random number -1..1 from the state of RND r of voice vi
    float rndUni (int vi, int r)
    {
        int s = (voices.at (vi).rS.at (r) * 1103515245 + 12345) & 0x7fffffff;
        voices.at (vi).rS.at (r) = s;
        return (float (s) / 2147483647.0f) * 2.0f - 1.0f;
    }

    // RND-DSP: a random value with the distribution of RND r
    float rndDraw (int vi, int r)
    {
        float a = rndUni (vi, r);
        int   d = rDist.at (r);

        if (d == 1)
            a = clamp ((a + rndUni (vi, r) + rndUni (vi, r)) * 0.6667f, -1.0f, 1.0f);   // bell shaped
        else if (d == 2)
            a = a >= 0.0f ? 1.0f : -1.0f;
        else if (d == 3)
            a = floor (a * 2.0f + 0.5f) * 0.5f;   // 5 levels: -1 -0.5 0 0.5 1

        return a;
    }

    // RND-DSP: note on, every RND draws its first value
    void rndNoteOn (int vi)
    {
        for (int r = 0; r < 10; ++r)
        {
            int sd = rSeed.at (r);
            voices.at (vi).rS.at (r) = sd > 0 ? ((sd * 7919 + r * 104729 + 12345) & 0x7fffffff) : ((noiseState * 69069 + r * 7919 + 1) & 0x7fffffff);
            float v = rndDraw (vi, r);
            voices.at (vi).rV.at (r)    = v;
            voices.at (vi).rPrev.at (r) = v;
            voices.at (vi).rTgt.at (r)  = v;
            voices.at (vi).rPh.at (r)   = 0.0f;
        }
    }

    // RND-DSP: advances the 10 random modulators of one voice by one sample (Note mode keeps its value)
    void updateVoiceRnd (int vi, float dtv)
    {
        for (int r = 0; r < 10; ++r)
        {
            int mode = rMode.at (r);

            if (mode == 0)
                continue;

            float hz = rSync.at (r) > 0 ? syncHz (rDiv.at (r)) : rRate.at (r);
            float ph = voices.at (vi).rPh.at (r) + dtv * hz;

            if (ph >= 1.0f)
            {
                ph = ph - floor (ph);
                voices.at (vi).rPrev.at (r) = voices.at (vi).rTgt.at (r);
                voices.at (vi).rTgt.at (r)  = mode == 3 ? clamp (voices.at (vi).rTgt.at (r) + rndDraw (vi, r) * 0.35f, -1.0f, 1.0f) : rndDraw (vi, r);
            }

            voices.at (vi).rPh.at (r) = ph;

            float target = voices.at (vi).rTgt.at (r);

            if (mode == 2)
                target = voices.at (vi).rPrev.at (r) + (target - voices.at (vi).rPrev.at (r)) * (ph * ph * (3.0f - 2.0f * ph));

            float sm = rSmooth.at (r);
            float cur = voices.at (vi).rV.at (r);
            voices.at (vi).rV.at (r) = sm <= 0.001f ? target : cur + (target - cur) * clamp (dtv / (sm * sm * 0.5f + 0.0001f), 0.0f, 1.0f);
        }
    }

    float rndOut (int vi, int r)
    {
        float v = voices.at (vi).rV.at (r);
        return rUni.at (r) > 0 ? v * 0.5f + 0.5f : v;
    }

    // MSEG-DSP: advances MSEG m of one voice by one sample
''')
rep('        if (src == 23)\n            return voices.at (vi).modRand;\n', '        if (src == 23)\n            return rndOut (vi, 0);\n        if (src >= 44 && src <= 52)\n            return rndOut (vi, src - 43);\n')
rep('        if (src == 23)\n            return lastRandV;\n', '        if (src == 23)\n            return rndOut (lastVoice, 0);\n        if (src >= 44 && src <= 52)\n            return rndOut (lastVoice, src - 43);\n')
rep('        voices.at (v).modRand = nextNoise();\n', '        voices.at (v).modRand = nextNoise();\n        rndNoteOn (v);\n')
rep('                updateModEnvs (i, dt);\n', '                updateModEnvs (i, dt);\n                updateVoiceRnd (i, dt);\n')
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('RND-DSP applied: %d params' % len(decl))
