#!/usr/bin/env python3
"""Idempotent (marker MOD-SEQ3):
 - fewer host parameters: the sequencer steps, the step shapes and matrix slots 21-256 get `automatable: false` (they stay in the saved state and in the UI)
 - Seq Monitor (param 3928, 0 = none, 1..10 = sequencer): the editor selects the sequencer it shows; only used sequencers and the monitored one run,
   and only the monitored one reports its playhead (output event seqPos), so a closed editor costs no CPU and no events."""
import os, re, sys
P = os.path.join(os.path.dirname(__file__), '..', '..', 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'MOD-SEQ3' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)

# ---- non-automatable parameters
def mark(m):
    line = m.group(0)
    return line.replace(' ]];', ', automatable: false ]];', 1)
src, n1 = re.subn(r'input event float param\d+ \[\[ name: "Seq \d+ Step \d+( Shape)?",[^\]]*\]\];', mark, src)
def slot_ge21(m):
    return mark(m) if int(m.group(1)) >= 21 else m.group(0)
src, n2 = re.subn(r'input event float param\d+ \[\[ name: "Mod Slot (\d+) [^\]]*\]\];', slot_ge21, src)
print('non-automatable: %d seq params, %d matrix params' % (n1, n2))

# ---- monitor
rep('    input event float param3927 [[ name: "Arp Latch", min: 0.0, max: 1.0, init: 0.0, step: 1.0 ]];   // MOD-ARP\n',
    '    input event float param3927 [[ name: "Arp Latch", min: 0.0, max: 1.0, init: 0.0, step: 1.0 ]];   // MOD-ARP\n'
    '    input event float param3928 [[ name: "Seq Monitor (editor: 0 = none, 1-10 = sequencer shown)", min: 0.0, max: 10.0, init: 0.0, step: 1.0, automatable: false ]];   // MOD-SEQ3\n')
rep('    float       seqRefresh = 0.0f;\n', '    float       seqRefresh = 0.0f;\n    int         seqMon = 0;   // MOD-SEQ3: sequencer shown by the editor (1..10), 0 = none\n')
rep('    event param1600 ', '    event param3928 (float v) { seqMon = clamp (int (v + 0.5f), 0, 10); seqRefresh = 1.0f; }   // MOD-SEQ3\n    event param1600 ')
rep('''        for (int m = 0; m < 10; ++m)   // all of them run, so the editor's playhead moves even before a sequencer is routed
            seqG.at (m) = seqRun (m, dt, seqG.at (m));''',
    '''        for (int m = 0; m < 10; ++m)   // the ones used by the matrix and the one the editor shows (its playhead moves before it is routed)
            if ((seqMask & (1 << m)) != 0 || m == seqMon - 1)
                seqG.at (m) = seqRun (m, dt, seqG.at (m));''')
rep('            if ((seqMask & (1 << m)) != 0 && seqRetrig.at (m) > 0.5f)\n                voices.at (vi).seqS',
    '            if (((seqMask & (1 << m)) != 0 || m == seqMon - 1) && seqRetrig.at (m) > 0.5f)\n                voices.at (vi).seqS')
rep('''            for (int m = 0; m < 10; ++m)   // MOD-SEQPOS
            {
                bool useVoice''', '''            for (int m = 0; m < 10; ++m)   // MOD-SEQPOS: only the sequencer the editor shows reports
                if (m == seqMon - 1)
            {
                bool useVoice''')
open(P, 'w').write(src)
print('applied')
