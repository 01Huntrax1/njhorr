#!/usr/bin/env python3
"""Idempotent (marker FX-KEYTRACK): key tracking for the pitched effects Waveguide (type 32) and Yaybahar (type 33).
 The modes of both effects get a second set ("... Key"): the Pitch knob then transposes the string relative to the last played note - the knob value
 261.6 Hz = unison with the note, 130.8 Hz = an octave below, and so on.  Waveguide modes 5..9 = modes 0..4 with key tracking, Yaybahar modes 3..5 = modes 0..2.
 Only slots of the Bus / Main racks follow the key (the per voice racks of the oscillators ignore it and play the plain mode).
 Run after build_wgfx.py and build_ybfx.py (tools/fx/build_ybfx.py is run by hand; the result is in patch/)."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); IP = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-KEYTRACK' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
rep('    bool          fxHeld = false;  // any note is held (not yet released)\n', '    bool          fxHeld = false;  // any note is held (not yet released)\n    int           fxLastNote = 60; // FX-KEYTRACK: last played note\n')
rep('    // ---- FX-FENV: ADSR of the filter effect ----\n', '''    // FX-KEYTRACK: a note was played: the key tracking modes of Waveguide (modes 5..9) and Yaybahar (modes 3..5) retune
    void fxKeyDirty()
    {
        for (int ks = 0; ks < 48; ++ks)
        {
            int kt = fxType.at (ks);

            if ((kt == 33 && fxMode.at (ks) >= 3) || (kt == 32 && fxMode.at (ks) >= 5))
                fxDirty.at (ks) = true;
        }
    }

    float fxKeyHz()
    {
        return 440.0f * float (pow (2.0f, float (fxLastNote - 69) / 12.0f));
    }

    // ---- FX-FENV: ADSR of the filter effect ----
''')
rep('        fxNoteSeq++;   // FX-FENV: retriggers the filter effect envelopes\n', '        fxNoteSeq++;   // FX-FENV: retriggers the filter effect envelopes\n        fxLastNote = nn;   // FX-KEYTRACK\n        fxKeyDirty();\n')
# Waveguide
rep('        int   md   = clamp (fxMode.at (s), 0, 4);\n        float f    = 30.0f * float (pow (2000.0f / 30.0f, clamp (fxP.at (pb), 0.0f, 1.0f)));\n',
    '        bool  key  = s < 48 && fxMode.at (s) >= 5;   // FX-KEYTRACK\n        int   md   = clamp (fxMode.at (s) >= 5 ? fxMode.at (s) - 5 : fxMode.at (s), 0, 4);\n        float f    = 30.0f * float (pow (2000.0f / 30.0f, clamp (fxP.at (pb), 0.0f, 1.0f)));\n\n        if (key)\n            f = fxKeyHz() * f / 261.63f;\n\n')
# Yaybahar
rep('        int   md   = clamp (fxMode.at (s), 0, 2);\n        float f    = 40.0f * float (pow (20.0f, clamp (fxP.at (pb), 0.0f, 1.0f)));\n',
    '        bool  key  = fxMode.at (s) >= 3;   // FX-KEYTRACK\n        int   md   = clamp (key ? fxMode.at (s) - 3 : fxMode.at (s), 0, 2);\n        float f    = 40.0f * float (pow (20.0f, clamp (fxP.at (pb), 0.0f, 1.0f)));\n\n        if (key)\n            f = fxKeyHz() * f / 261.63f;\n\n')
rep('modes: ["String", "Tube", "Dual Strings", "Fifth Drone", "Octave Drone"]', 'modes: ["String", "Tube", "Dual Strings", "Fifth Drone", "Octave Drone", "String Key", "Tube Key", "Dual Strings Key", "Fifth Drone Key", "Octave Drone Key"]', 'idx')
rep('modes: ["Classic", "Stereo", "Deep"]', 'modes: ["Classic", "Stereo", "Deep", "Classic Key", "Stereo Key", "Deep Key"]', 'idx')
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('FX-KEYTRACK applied')
