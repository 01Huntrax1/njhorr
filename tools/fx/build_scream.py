#!/usr/bin/env python3
"""Idempotent, marker FX-SCREAM: the Scream type (mode 32) of the Filter effect rebuilt after Massive's Scream (a low-pass with additional internal feedback):
24 dB low-pass (saturating-resonance 12 dB stage + plain 12 dB stage); the Drive knob becomes the Scream amount: the saturated, asymmetrically shaped output is fed back
(negatively, like a ladder) to the input, which turns into a dirty resonance peak that screams at higher settings.  Reso is the normal resonance.
Run after build_korg.py.   build_scream.py [patch file]"""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
s = open(path).read()
if 'FX-SCREAM' in s:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:70], s.count(old))
    s = s.replace(old, new)
i = s.index('        if (ft == 32)\n        {\n            // Scream: driven input')
j = s.index('        // 23: vowel / formant filter', i)
s = s[:i] + '''        if (ft == 32)
        {
            // Scream (after Massive): 24 dB low-pass (saturating-resonance stage + plain 12 dB stage) with extra internal feedback of the saturated output
            // back to the input; the Drive knob is the Scream amount (fxD db + 4 = 1 + 8 * knob), Reso is the normal resonance
            float sc = clamp ((fxD.at (s * 16 + 4) - 1.0f) * 0.125f, 0.0f, 1.0f);
            float yp = fxF.at (b + 4);
            float fb = softClip (yp * 2.0f + 0.25f * yp * yp);   // FX-SCREAM: asymmetric saturation of the fed-back output
            float u  = softClip (x * (1.0f + 0.6f * sc) - sc * 3.0f * fb);
            float y1 = fxSatSvf (b, u, g, res * 1.5f, 1.4f, 0);
            float y2 = fxSvfStage (b + 2, y1, g, 1.2f, 0);
            fxF.at (b + 4) = y2;
            return y2 * (1.0f + 0.3f * sc);
        }

''' + s[j:]
rep('        if (gd > 1.01f)\n        {\n            inL = softClip (inL * gd);\n            inR = softClip (inR * gd);\n        }\n\n        float g   = fxD.at (db);\n        float k   = fxD.at (db + 1);', '        if (gd > 1.01f && ft != 32)   // FX-SCREAM: in Scream mode Drive is the Scream (feedback) amount\n        {\n            inL = softClip (inL * gd);\n            inR = softClip (inR * gd);\n        }\n\n        float g   = fxD.at (db);\n        float k   = fxD.at (db + 1);')
open(path, 'w').write(s)
print('ok')
