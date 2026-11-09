#!/usr/bin/env python3
"""Idempotent (marker MOD-ARP303): "303" mode of the arpeggiator (Arp Mode 5).  A 16-step pattern like the TB-303: per step a note (-12..+24 semitones
from the root = the last key pressed), Accent, Slide (tied, glides into the next note) and Gate (off = rest), Length 1..16.
Params: 5200+k note, 5216+k accent, 5232+k slide, 5248+k gate, 5264 length (all `automatable: false`).  The voice is mono and legato in this mode,
a slide uses at least 60 ms glide (the Glide knob if it is longer), steps without slide restart the oscillators and jump to the pitch."""
import os, sys
P = os.path.join(os.path.dirname(__file__), '..', '..', 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'MOD-ARP303' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:80], src.count(old))
    src = src.replace(old, new)

NOTE = [0, 0, 12, 0, 0, 10, 0, 7, 0, 12, 0, 0, 3, 5, 0, 0]
ACC  = [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0]
SLD  = [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0]
GATE = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0]

rep('"Arp Mode", min: 0.0, max: 4.0,', '"Arp Mode", min: 0.0, max: 5.0,')

decl = ''
for k in range(16):
    decl += '    input event float param%d [[ name: "303 Step %d Note", min: -12.0, max: 24.0, init: %d.0, step: 1.0, automatable: false ]];   // MOD-ARP303\n' % (5200 + k, k + 1, NOTE[k])
for k in range(16):
    decl += '    input event float param%d [[ name: "303 Step %d Accent", min: 0.0, max: 1.0, init: %d.0, step: 1.0, automatable: false ]];\n' % (5216 + k, k + 1, ACC[k])
for k in range(16):
    decl += '    input event float param%d [[ name: "303 Step %d Slide", min: 0.0, max: 1.0, init: %d.0, step: 1.0, automatable: false ]];\n' % (5232 + k, k + 1, SLD[k])
for k in range(16):
    decl += '    input event float param%d [[ name: "303 Step %d Gate", min: 0.0, max: 1.0, init: %d.0, step: 1.0, automatable: false ]];\n' % (5248 + k, k + 1, GATE[k])
decl += '    input event float param5264 [[ name: "303 Length", min: 1.0, max: 16.0, init: 16.0, step: 1.0, automatable: false ]];\n'
a = '    input event float param3929 '
i = src.index(a); j = src.index('\n', i) + 1
src = src[:j] + decl + src[j:]

rep('    float       seqKeyStart = 1.0f;', '''    float[16]   a3Note, a3Acc, a3Slide, a3Gate;   // MOD-ARP303
    float       a3Len = 16.0f;
    bool        a3Prev = false;   // the previous step slides into this one
    bool        a3Hard = false;   // this note jumps to its pitch and restarts the oscillators
    float       seqKeyStart = 1.0f;''')

ev = ''
for k in range(16):
    ev += '    event param%d (float v) { a3Note.at (%d) = v; }   // MOD-ARP303\n' % (5200 + k, k)
    ev += '    event param%d (float v) { a3Acc.at (%d) = v; }\n' % (5216 + k, k)
    ev += '    event param%d (float v) { a3Slide.at (%d) = v; }\n' % (5232 + k, k)
    ev += '    event param%d (float v) { a3Gate.at (%d) = v; }\n' % (5248 + k, k)
ev += '    event param5264 (float v) { a3Len = v; }\n'
rep('    event param3920 (float v) { arpOn = v; }', ev + '    event param3920 (float v) { arpOn = v; }')

ini = '        for (int ak = 0; ak < 16; ++ak)   // MOD-ARP303 defaults (same as the parameter defaults)\n        {\n'
ini += '            a3Gate.at (ak) = 1.0f;\n'
for name, arr in (('a3Note', NOTE), ('a3Acc', ACC), ('a3Slide', SLD), ('a3Gate', GATE)):
    ini += '            if (ak == -1) {}\n'
ini = '        // MOD-ARP303 defaults (same as the parameter defaults)\n'
for name, arr in (('a3Note', NOTE), ('a3Acc', ACC), ('a3Slide', SLD), ('a3Gate', GATE)):
    for k, v in enumerate(arr):
        if v != 0:
            ini += '        %s.at (%d) = %d.0f;\n' % (name, k, v)
ini += '\n'
rep('        for (int sm = 0; sm < 10; ++sm)   // MOD-SEQ\n        {\n            seqLen.at (sm)  = 8.0f;', ini + '        for (int sm = 0; sm < 10; ++sm)   // MOD-SEQ\n        {\n            seqLen.at (sm)  = 8.0f;')

# voice: mono + legato in 303 mode, hard restart for steps without slide, minimum glide for slides
rep('        bool  monoMode = voiceMode > 0.5f;\n        bool  legato   = monoMode && legatoOn > 0.5f;',
    '        bool  monoMode = voiceMode > 0.5f || (arpOn > 0.5f && int (arpMode + 0.5f) == 5);   // MOD-ARP303: the 303 pattern plays mono\n        bool  legato   = monoMode && legatoOn > 0.5f && ! a3Hard;')
rep('        if (! (monoMode && wasActive))\n            voices.at (v).curFreq = target;', '        if (! (monoMode && wasActive) || a3Hard)\n            voices.at (v).curFreq = target;')
rep('''                if (glideMs > 0.5f)
                    gc = clamp (dt * 5.0f / (glideMs * 0.001f), 0.0f, 1.0f);''', '''                float gms = glideMs;

                if (arpOn > 0.5f && int (arpMode + 0.5f) == 5)   // MOD-ARP303: a slide is at least 60 ms
                    gms = max (gms, 60.0f);

                if (gms > 0.5f)
                    gc = clamp (dt * 5.0f / (gms * 0.001f), 0.0f, 1.0f);''')

# arpTick
rep('''            if (arpCur >= 0)
                voiceNoteOff (arpCur);

            arpCur = arpNote (arpStep);
            arpStep++;
            voiceNoteOn (arpCur, arpCurVel);
        }
        else if (arpCur >= 0 && arpPh >= arpGate)''', '''            if (int (arpMode + 0.5f) == 5)   // MOD-ARP303
            {
                int   si    = arpStep % clamp (int (a3Len + 0.5f), 1, 16);
                int   root  = arpHN.at (max (arpN - 1, 0));
                bool  tied  = a3Prev && arpCur >= 0;   // the step before slid into this one
                int   old   = arpCur;
                arpStep++;

                if (a3Gate.at (si) > 0.5f)
                {
                    int nn = clamp (root + int (a3Note.at (si)), 0, 127);

                    if (tied)
                    {
                        if (nn != old)   // the new note starts before the old one ends: the voice glides
                        {
                            arpCur = nn;
                            voiceNoteOn (nn, a3Acc.at (si) > 0.5f ? 1.0f : 0.6f);
                            voiceNoteOff (old);
                        }
                    }
                    else
                    {
                        if (old >= 0)
                            voiceNoteOff (old);

                        arpCur = nn;
                        a3Hard = true;
                        voiceNoteOn (nn, a3Acc.at (si) > 0.5f ? 1.0f : 0.6f);
                        a3Hard = false;
                    }

                    a3Prev = a3Slide.at (si) > 0.5f;
                }
                else   // rest
                {
                    if (old >= 0)
                        voiceNoteOff (old);

                    arpCur = -1;
                    a3Prev = false;
                }

                return;
            }

            if (arpCur >= 0)
                voiceNoteOff (arpCur);

            arpCur = arpNote (arpStep);
            arpStep++;
            voiceNoteOn (arpCur, arpCurVel);
        }
        else if (int (arpMode + 0.5f) == 5 && arpCur >= 0 && ! a3Prev && arpPh >= arpGate)   // MOD-ARP303: a slide holds the note until the next step
        {
            voiceNoteOff (arpCur);
            arpCur = -1;
        }
        else if (int (arpMode + 0.5f) != 5 && arpCur >= 0 && arpPh >= arpGate)''')
rep('            arpPh   = 1.0f;\n            arpStep = 0;\n            return;', '            arpPh   = 1.0f;\n            arpStep = 0;\n            a3Prev  = false;   // MOD-ARP303\n            return;')
open(P, 'w').write(src)
print('applied')
