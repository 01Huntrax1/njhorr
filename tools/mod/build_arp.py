#!/usr/bin/env python3
"""Idempotent (marker MOD-ARP): arpeggiator in front of the voices. Parameters 3920..3927:
On, Mode (Up / Down / Up-Down / Random / As played), Octaves 1-4, Sync, Division, Rate (Hz), Gate, Latch."""
import os, sys
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); J = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); js = open(J).read()
if 'MOD-ARP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:60], src.count(old))
    src = src.replace(old, new)

# ---- params
B = 3920
decl = [
 ('Arp On', 0, 1, 0, 'step: 1.0'), ('Arp Mode', 0, 4, 0, 'step: 1.0'), ('Arp Octaves', 1, 4, 1, 'step: 1.0'), ('Arp Sync', 0, 1, 1, 'step: 1.0'),
 ('Arp Division', 0, 17, 11, 'step: 1.0'), ('Arp Rate', 0.25, 30, 6, 'unit: "Hz"'), ('Arp Gate', 0.05, 1, 0.6, ''), ('Arp Latch', 0, 1, 0, 'step: 1.0')]
lines = []
for i, (n, lo, hi, ini, ex) in enumerate(decl):
    lines.append('    input event float param%d [[ name: "%s", min: %s, max: %s, init: %s%s ]];   // MOD-ARP' % (B + i, n, float(lo), float(hi), float(ini), (', ' + ex) if ex else ''))
rep('    input event float param3911 [[ name: "Seq 10 Bipolar", min: 0.0, max: 1.0, init: 1.0, step: 1.0 ]];   // MOD-SEQ\n',
    '    input event float param3911 [[ name: "Seq 10 Bipolar", min: 0.0, max: 1.0, init: 1.0, step: 1.0 ]];   // MOD-SEQ\n' + '\n'.join(lines) + '\n')
vars_ = '''    // ---------------- MOD-ARP: arpeggiator ----------------
    float       arpOn = 0.0f, arpMode = 0.0f, arpOct = 1.0f, arpSync = 1.0f, arpDiv = 11.0f, arpRate = 6.0f, arpGate = 0.6f, arpLatch = 0.0f;
    int[16]     arpHN;      // held notes in the order they were pressed
    float[16]   arpHV;
    int[16]     arpSN;      // work copy (sorted)
    float[16]   arpSV;
    int         arpN = 0;   // number of held notes
    int         arpKeys = 0;   // keys physically down
    int         arpCur = -1;   // note currently sounding from the arp
    int         arpStep = 0;
    float       arpPh = 1.0f;
    float       arpCurVel = 1.0f;
'''
rep('    int         seqMask = 0;   // bit m: sequencer m is used by the matrix\n', '    int         seqMask = 0;   // bit m: sequencer m is used by the matrix\n' + vars_)
ev = ['    event param%d (float v) { %s = v; }   // MOD-ARP' % (B + i, n) for i, n in enumerate(['arpOn', 'arpMode', 'arpOct', 'arpSync', 'arpDiv', 'arpRate', 'arpGate', 'arpLatch'])]
rep('    event param1600 ', '\n'.join(ev) + '\n    event param1600 ') if src.count('    event param1600 ') == 1 else None

# ---- split the MIDI handler
a = src.index('    event midiIn (std::midi::Message msg)\n')
z = src.index('    // ---------------- AUDIO ----------------')
old = src[a:z]
on_start = old.index('            int   nn       = msg.getNoteNumber();\n') + len('            int   nn       = msg.getNoteNumber();\n')
on_end = old.index('        }\n        else if (msg.isNoteOff())')
off_start = old.index('            int nn = msg.getNoteNumber();\n') + len('            int nn = msg.getNoteNumber();\n')
off_end = old.rindex('        }\n    }\n')
on_body = old[on_start:on_end]; off_body = old[off_start:off_end]
assert 'msg.getFloatVelocity()' in on_body
on_body = on_body.replace('            float vel      = msg.getFloatVelocity();\n', '')
assert 'msg.' not in on_body and 'msg.' not in off_body
ded = lambda t: ''.join((l[4:] if l.startswith('    ') else l) for l in t.splitlines(True))
new = '''    // MOD-ARP: the voice start / release code of the MIDI handler, shared by the keys and the arpeggiator
    void voiceNoteOn (int nn, float vel)
    {
''' + ded(on_body) + '''    }

    void voiceNoteOff (int nn)
    {
''' + ded(off_body) + '''    }

    // ---- arpeggiator ----
    void arpPress (int nn, float vel)
    {
        if (arpLatch > 0.5f && arpKeys <= 0)
            arpN = 0;

        arpKeys++;

        for (int i = 0; i < arpN; ++i)
            if (arpHN.at (i) == nn)
            {
                arpHV.at (i) = vel;
                return;
            }

        if (arpN < 16)
        {
            arpHN.at (arpN) = nn;
            arpHV.at (arpN) = vel;
            arpN++;
        }
    }

    void arpRelease (int nn)
    {
        arpKeys = max (arpKeys - 1, 0);

        if (arpLatch > 0.5f)
            return;

        for (int i = 0; i < arpN; ++i)
            if (arpHN.at (i) == nn)
            {
                for (int j = i; j < arpN - 1; ++j)
                {
                    arpHN.at (j) = arpHN.at (j + 1);
                    arpHV.at (j) = arpHV.at (j + 1);
                }

                arpN--;
                return;
            }
    }

    int arpNote (int step)
    {
        for (int i = 0; i < arpN; ++i)
        {
            arpSN.at (i) = arpHN.at (i);
            arpSV.at (i) = arpHV.at (i);
        }

        int md = int (arpMode + 0.5f);

        if (md != 4)   // sorted ascending unless "As played"
            for (int i = 1; i < arpN; ++i)
                for (int j = i; j > 0 && arpSN.at (j - 1) > arpSN.at (j); --j)
                {
                    int   tn = arpSN.at (j);
                    float tv = arpSV.at (j);
                    arpSN.at (j) = arpSN.at (j - 1);  arpSV.at (j) = arpSV.at (j - 1);
                    arpSN.at (j - 1) = tn;            arpSV.at (j - 1) = tv;
                }

        int n     = max (arpN, 1);
        int total = n * clamp (int (arpOct + 0.5f), 1, 4);
        int i     = step % total;

        if (md == 1)
            i = total - 1 - i;
        else if (md == 2)
        {
            int per = max (2 * total - 2, 1);
            int p   = step % per;
            i = p < total ? p : per - p;
        }
        else if (md == 3)
            i = clamp (int (abs (nextNoise()) * float (total)), 0, total - 1);

        arpCurVel = arpSV.at (i % n);
        return clamp (arpSN.at (i % n) + 12 * (i / n), 0, 127);
    }

    void arpTick (float dt)
    {
        if (arpOn < 0.5f || arpN == 0)
        {
            if (arpCur >= 0)
            {
                voiceNoteOff (arpCur);
                arpCur = -1;
            }

            if (arpOn < 0.5f)
            {
                arpN = 0;
                arpKeys = 0;
            }

            arpPh   = 1.0f;
            arpStep = 0;
            return;
        }

        float hz = arpSync > 0.5f ? syncHz (arpDiv) : arpRate;
        arpPh += max (hz, 0.01f) * dt;

        if (arpPh >= 1.0f)
        {
            arpPh -= 1.0f;

            if (arpPh >= 1.0f)
                arpPh = 0.0f;

            if (arpCur >= 0)
                voiceNoteOff (arpCur);

            arpCur = arpNote (arpStep);
            arpStep++;
            voiceNoteOn (arpCur, arpCurVel);
        }
        else if (arpCur >= 0 && arpPh >= arpGate)
        {
            voiceNoteOff (arpCur);
            arpCur = -1;
        }
    }

    event midiIn (std::midi::Message msg)
    {
        if (msg.isNoteOn())
        {
            if (arpOn > 0.5f)
                arpPress (msg.getNoteNumber(), msg.getFloatVelocity());
            else
                voiceNoteOn (msg.getNoteNumber(), msg.getFloatVelocity());
        }
        else if (msg.isNoteOff())
        {
            int nn = msg.getNoteNumber();

            if (arpOn > 0.5f)
                arpRelease (nn);

            if (arpOn < 0.5f || arpCur != nn)
                voiceNoteOff (nn);
        }
    }

'''
src = src[:a] + new + src[z:]
rep('            wtBuildTick();\n            updateModLfos (dt);\n', '            wtBuildTick();\n            arpTick (dt);   // MOD-ARP\n            updateModLfos (dt);\n')
open(P, 'w').write(src)

# ---- index.js specs
def jrep(old, new):
    global js
    assert js.count(old) == 1, (old[:60], js.count(old))
    js = js.replace(old, new)
specs = '''    // MOD-ARP: arpeggiator, ids 3920..3927
    L.push([3920, "Arp On",       0, 1, 0, "", "btn", ["Off", "On"], 1, "Arp"]);
    L.push([3921, "Arp Mode",     0, 4, 0, "", "sel", ["Up", "Down", "Up / Down", "Random", "As played"], 1, "Mode"]);
    L.push([3922, "Arp Octaves",  1, 4, 1, "", "stp", null, 1, "Octaves"]);
    L.push([3923, "Arp Sync",     0, 1, 1, "", "btn", ["Free", "Sync"], 1, "Sync"]);
    L.push([3924, "Arp Division", 0, 17, 11, "", "sel", SYNC_DIVS, 1, "Division"]);
    L.push([3925, "Arp Rate",     0.25, 30, 6, "Hz", "sld", null, 1, "Rate"]);
    L.push([3926, "Arp Gate",     0.05, 1, 0.6, "", "sld", null, 1, "Gate"]);
    L.push([3927, "Arp Latch",    0, 1, 0, "", "btn", ["Off", "On"], 1, "Latch"]);
'''
anchor = '    // MOD-LFOBIP: Polarity of every LFO (3111 + i), default Bipolar\n'
jrep(anchor, specs + anchor)
open(J, 'w').write(js)
print('applied')
