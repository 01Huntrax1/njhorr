#!/usr/bin/env python3
"""Idempotent: through-zero FM matrix (TZFM), marker TZFM-DSP.  6 x 6 amounts (ids 2900 + 6 * modulator + carrier, 0..100 %), like the FM matrix.
Linear FM with a signed frequency: the modulator is integrated into a phase offset (cycles) that is added to the carrier's phase input, so the
carrier's instantaneous frequency is f * (1 + 4 * amount * modulator) and runs backwards (through zero) when that factor gets negative.
Only sources that take a phase input follow it (Wavetable, Sampler, Wave Terrain, Alpha Juno, Kick, JP-8080), like PM and PD.
State: Voice.tzPh per slot (reset on a new voice)."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'TZFM-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
decl = ''.join('    input event float param%d [[ name: "TZFM %d to %d", min: 0.0, max: 100.0, init: 0.0, step: 1.0 ]];\n' % (2900 + 6 * s + d, s + 1, d + 1) for s in range(6) for d in range(6))
rep('    input event float param1560 [[ name: "AM 1 to 1"', '    // TZFM-DSP: through-zero FM matrix\n' + decl + '    input event float param1560 [[ name: "AM 1 to 1"')
hand = ''.join('    event param%d (float v) { tzSet (%d, %d, v * 0.01f); }\n' % (2900 + 6 * s + d, s, d) for s in range(6) for d in range(6))
rep('    event param1560 (float v) { amSet (0, 0, v * 0.01f); }\n', hand + '    event param1560 (float v) { amSet (0, 0, v * 0.01f); }\n')
rep('    float[64]     amAmt;      // amplitude modulation (carrier x unipolar modulator)\n', '    float[64]     amAmt;      // amplitude modulation (carrier x unipolar modulator)\n    float[64]     tzAmt;      // through-zero FM (TZFM-DSP)\n')
rep('                    || rmAmt.at (q * 6 + r) != 0.0f || amAmt.at (q * 6 + r) != 0.0f) u = true;', '                    || rmAmt.at (q * 6 + r) != 0.0f || amAmt.at (q * 6 + r) != 0.0f || tzAmt.at (q * 6 + r) != 0.0f) u = true;')
rep('    void amSet (int s, int d, float v)\n', '    void tzSet (int s, int d, float v)\n    {\n        tzAmt.at (s * 6 + d) = v;\n        updateFmUsed();\n    }\n\n    void amSet (int s, int d, float v)\n')
rep('        float[8]    fmPrev;   // last output of every slot (FM source)\n', '        float[8]    fmPrev;   // last output of every slot (FM source)\n        float[8]    tzPh;     // through-zero FM: integrated modulator phase per slot (cycles)\n')
rep('                    voices.at (v).fmPrev.at (o) = 0.0f;\n            }\n', '                    voices.at (v).fmPrev.at (o) = 0.0f;\n\n                for (int tz = 0; tz < 8; ++tz)\n                    voices.at (v).tzPh.at (tz) = 0.0f;\n            }\n')
rep('                float[6] pdIn;\n', '                float[6] pdIn;\n                float[6] tzIn;\n')
rep('                    float acd = 0.0f;\n                    for (int fs = 0; fs < 6; ++fs)\n', '                    float acd = 0.0f;\n                    float acz = 0.0f;\n                    for (int fs = 0; fs < 6; ++fs)\n')
rep('                        if (ad != 0.0f)\n                            acd += ad * voices.at (i).fmPrev.at (fs);\n', '                        if (ad != 0.0f)\n                            acd += ad * voices.at (i).fmPrev.at (fs);\n                        float az = tzAmt.at (mi);\n                        if (az != 0.0f)\n                            acz += az * voices.at (i).fmPrev.at (fs);\n')
rep('                    pdIn.at (fd) = acd;\n', '                    pdIn.at (fd) = acd;\n                    tzIn.at (fd) = acz;\n')
rep('                    float pm    = pmIn.at (o);\n', '''                    float pm    = pmIn.at (o);

                    // TZFM-DSP: the modulator is integrated into a phase offset: frequency f * (1 + 4 * amount * modulator), negative values run backwards
                    if (fmAny)
                    {
                        float tzv = tzIn.at (o);
                        float tzp = voices.at (i).tzPh.at (o);

                        if (tzv != 0.0f || tzp != 0.0f)
                        {
                            tzp += clamp (tzv, -2.0f, 2.0f) * 4.0f * freq / sr;
                            tzp -= float (floor (tzp));
                            voices.at (i).tzPh.at (o) = tzp;
                            pm += tzp;
                        }
                    }
''')
open(path, 'w').write(src)
print('ok')
