#!/usr/bin/env python3
"""Idempotent (marker MOD-SEQPOS): the DSP reports the current step of each used sequencer to the UI.
Output event seqPos = m * 16 + step, sent whenever a step changes (global sequencers; with Retrig the most recently started voice)."""
import os, sys
P = os.path.join(os.path.dirname(__file__), '..', '..', 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'MOD-SEQPOS' in src:
    print('already applied'); sys.exit(0)

def rep(old, new):
    global src
    assert src.count(old) == 1, (old, src.count(old))
    src = src.replace(old, new)

rep('    input event std::timeline::Position positionIn;   // FX-SYNC\n',
    '    input event std::timeline::Position positionIn;   // FX-SYNC\n    output event int seqPos;   // MOD-SEQPOS: sequencer * 16 + current step (playhead of the editor)\n')
rep('    int         seqMask = 0;   // bit m: sequencer m is used by the matrix\n',
    '    int         seqMask = 0;   // bit m: sequencer m is used by the matrix\n    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n    int[16]     seqLastPos;        // MOD-SEQPOS\n    float       seqRefresh = 0.0f;\n')
rep('                voices.at (v).seqS.at (lm)   = SeqS (0.0f, 0.0f, 1.0f, seqStep.at (lm * 16));   // MOD-SEQ\n            }\n',
    '                voices.at (v).seqS.at (lm)   = SeqS (0.0f, 0.0f, 1.0f, seqStep.at (lm * 16));   // MOD-SEQ\n            }\n\n            seqRepVoice = v;   // MOD-SEQPOS\n')
rep('            updateSeqGlobal (dt);\n            updateFrqGlobal (dt);\n',
    '''            updateSeqGlobal (dt);
            seqRefresh += dt;
            bool seqForce = seqRefresh > 0.3f;   // every 0.3 s all positions are sent again (an editor opened later, or a slow sequencer, shows its playhead at once)

            if (seqForce)
                seqRefresh = 0.0f;

            for (int m = 0; m < 10; ++m)   // MOD-SEQPOS
            {
                bool useVoice = seqRetrig.at (m) > 0.5f && voices.at (seqRepVoice).active;
                int  sp = int ((useVoice ? voices.at (seqRepVoice).seqS.at (m).idx : seqG.at (m).idx) + 0.5f);

                if (sp != seqLastPos.at (m) || seqForce)
                {
                    seqLastPos.at (m) = sp;
                    seqPos <- m * 16 + sp;
                }
            }
            updateFrqGlobal (dt);
''')

open(P, 'w').write(src)
print('applied')
