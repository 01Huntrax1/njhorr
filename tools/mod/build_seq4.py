#!/usr/bin/env python3
"""Idempotent (marker MOD-SEQ4): Seq Key Start (param 3929, default On): the global sequencers (not the per-voice ones) only run while a voice sounds
and restart from step 1 with the first note."""
import os, sys
P = os.path.join(os.path.dirname(__file__), '..', '..', 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'MOD-SEQ4' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
rep('    int         seqMon = 0;', '    float       seqKeyStart = 1.0f;   // MOD-SEQ4\n    bool        seqGate = false;\n    int         seqMon = 0;')
a = '    input event float param3928 '
i = src.index(a); j = src.index('\n', i) + 1
src = src[:j] + '    input event float param3929 [[ name: "Seq Key Start (1 = the sequencers only run while a note sounds)", min: 0.0, max: 1.0, init: 1.0, step: 1.0 ]];   // MOD-SEQ4\n' + src[j:]
rep('    event param3928 (float v)', '    event param3929 (float v) { seqKeyStart = v; }   // MOD-SEQ4\n    event param3928 (float v)')
rep('''    void updateSeqGlobal (float dt)
    {
''', '''    void updateSeqGlobal (float dt)
    {
        bool gate = seqKeyStart < 0.5f;   // MOD-SEQ4: without Key Start they run all the time

        for (int dv = 0; dv < 8; ++dv)
            if (voices.at (dv).active)
                gate = true;

        if (gate && ! seqGate)            // the first note: every sequencer starts at step 1
            for (int m = 0; m < 10; ++m)
                seqG.at (m) = SeqS (0.0f, 0.0f, 1.0f, seqStep.at (m * 16));

        seqGate = gate;

        if (! gate)
            return;

''')
open(P, 'w').write(src); print('applied')
