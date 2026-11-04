#!/usr/bin/env python3
"""Idempotent, marker FX-KORG: three more types of the FX Filter effect (mode numbers 30..32; the oscillator filter is unchanged):
  30 Korg35 LP  - 12 dB Sallen-Key low-pass (MS-20 / Korg35 style): the resonance is positive feedback that saturates with the level, so it screams
                  when pushed and self-oscillates at the top of the Reso range
  31 Korg35 HP  - the matching 12 dB high-pass
  32 Scream     - a hotter relative: asymmetric input drive, resonance beyond self-oscillation held in a limit cycle by the saturating damping, and a
                  distorted low-pass + band-pass output
Both are zero-delay-feedback state variable filters whose damping depends on the band state: k = (2 - kr) + kr * (1 - 1 / sqrt(1 + (sat * |band|)^2)),
kr = Reso * 1.96 (Korg35) or * 2.3 (Scream), so the loop is stable at every level."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'FX-KORG' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
src, n = re.subn(r'(FX \d+ Mode",\s*min: 0\.0, max: )29\.0', r'\g<1>32.0', src); assert n == 30, n
src, n = re.subn(r'(fxMode\.at \(\d+\) = clamp \(int \(v \+ 0\.5f\), 0, )29\)', r'\g<1>32)', src); assert n == 30, n
fn = r'''    // FX-KORG: state variable filter whose damping grows with the band level (saturating positive feedback); mode 0 low-pass, 1 high-pass, 2 band-pass
    float fxSatSvf (int idx, float x, float g, float kr, float sat, int mode)
    {
        float s1 = fxF.at (idx);
        float s2 = fxF.at (idx + 1);
        float a  = abs (s1) * sat;
        float k  = 2.0f - kr + kr * (1.0f - 1.0f / float (sqrt (1.0f + a * a)));
        float a1 = 1.0f / (1.0f + g * (g + k));
        float a2 = g * a1;
        float a3 = g * a2;
        float v3 = x - s2;
        float v1 = a1 * s1 + a2 * v3;
        float v2 = s2 + a2 * s1 + a3 * v3;

        fxF.at (idx)     = 2.0f * v1 - s1;
        fxF.at (idx + 1) = 2.0f * v2 - s2;

        if (mode == 1) return x - k * v1 - v2;
        if (mode == 2) return v1;
        return v2;
    }

'''
rep('    float fxFilterX (int s, int ch, float x, float g, float k, float res, float fc, int ft)', fn + '    float fxFilterX (int s, int ch, float x, float g, float k, float res, float fc, int ft)')
ANCH = '            fxF.at (b + 8) = a;\n            return 0.5f * (x + a);\n        }\n\n'
rep(ANCH + '        // 23: vowel / formant filter, cutoff sweeps A-E-I-O-U\n', ANCH + r'''        if (ft == 30 || ft == 31)
        {
            // Korg35 low-pass / high-pass (12 dB Sallen-Key, saturating resonance)
            return fxSatSvf (b, x, g, res * 1.96f, 1.4f, ft == 31 ? 1 : 0);
        }

        if (ft == 32)
        {
            // Scream: driven input, resonance past self-oscillation, distorted low-pass + band-pass
            float xi = softClip (x * 1.8f + 0.12f * x * x);
            float lp = fxSatSvf (b, xi, g, res * 2.3f, 2.5f, 0);
            float bp = fxF.at (b) * g;
            return softClip (2.2f * (lp + 0.6f * res * bp * 4.0f)) * 0.7f;
        }

        // 23: vowel / formant filter, cutoff sweeps A-E-I-O-U
''')
open(path, 'w').write(src)
print('ok')
