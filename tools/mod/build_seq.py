#!/usr/bin/env python3
"""Idempotent: 10 step sequencers as modulation sources 34..43 (marker MOD-SEQ).
Parameters (ids 3600 + 32 * m + k): k 0..15 steps (0..1), 16 Length (1-16), 17 Rate (steps / s), 18 Sync, 19 Division, 20 Glide, 21 Direction
(Forward, Backward, Ping-Pong, Random), 22 Retrig (Off = one global sequencer, On = one per voice that restarts on note-on), 23 Polarity (Unipolar 0..1 / Bipolar -1..1)."""
import os, sys, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
J = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); js = open(J).read()
if 'MOD-SEQ' in src:
    print('already applied'); sys.exit(0)

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old)
    src = src.replace(old, new)

BASE = 3600
# ---- parameter declarations
decl = '\n'.join(sorted(set()))
lines = []
for m in range(10):
    for k in range(16):
        lines.append('    input event float param%d [[ name: "Seq %d Step %d", min: 0.0, max: 1.0, init: %s ]];   // MOD-SEQ' % (BASE + 32 * m + k, m + 1, k + 1, [0.5, 1.0, 0.25, 0.75, 0.0, 0.6, 0.3, 0.9][k % 8]))
    b = BASE + 32 * m
    lines += [
        '    input event float param%d [[ name: "Seq %d Length", min: 1.0, max: 16.0, init: 8.0, step: 1.0 ]];   // MOD-SEQ' % (b + 16, m + 1),
        '    input event float param%d [[ name: "Seq %d Rate", min: 0.05, max: 40.0, init: 4.0, unit: "Hz" ]];   // MOD-SEQ' % (b + 17, m + 1),
        '    input event float param%d [[ name: "Seq %d Sync", min: 0.0, max: 1.0, init: 0.0, step: 1.0 ]];   // MOD-SEQ' % (b + 18, m + 1),
        '    input event float param%d [[ name: "Seq %d Division", min: 0.0, max: 17.0, init: 11.0, step: 1.0 ]];   // MOD-SEQ' % (b + 19, m + 1),
        '    input event float param%d [[ name: "Seq %d Glide", min: 0.0, max: 1.0, init: 0.0 ]];   // MOD-SEQ' % (b + 20, m + 1),
        '    input event float param%d [[ name: "Seq %d Direction", min: 0.0, max: 3.0, init: 0.0, step: 1.0 ]];   // MOD-SEQ' % (b + 21, m + 1),
        '    input event float param%d [[ name: "Seq %d Retrig", min: 0.0, max: 1.0, init: 0.0, step: 1.0 ]];   // MOD-SEQ' % (b + 22, m + 1),
        '    input event float param%d [[ name: "Seq %d Bipolar", min: 0.0, max: 1.0, init: 1.0, step: 1.0 ]];   // MOD-SEQ' % (b + 23, m + 1),
    ]
anchor = '    input event float param3120 [[ name: "Mod LFO 10 Bipolar", min: 0.0, max: 1.0, init: 1.0 ]];   // MOD-LFOBIP\n'
rep(anchor, anchor + '\n'.join(lines) + '\n')

# ---- state
rep('    float[16]   lfoUni;  // MOD-LFOBIP\n',
    '''    float[16]   lfoUni;  // MOD-LFOBIP
    float[256]  seqStep;   // MOD-SEQ: 16 steps of each sequencer (0..1)
    float[16]   seqLen;
    float[16]   seqRate;
    float[16]   seqSync;
    float[16]   seqDiv;
    float[16]   seqGlide;
    float[16]   seqDir;
    float[16]   seqRetrig;
    float[16]   seqPol;    // 1 = bipolar
    int         seqMask = 0;   // bit m: sequencer m is used by the matrix
''')
# SeqS struct before Voice
rep('    struct Voice\n', '''    struct SeqS   // MOD-SEQ: state of one sequencer
    {
        float ph;     // position inside the step (0..1)
        float idx;    // current step
        float dir;    // +1 / -1 (ping-pong)
        float v;      // output 0..1 (after glide)
    }

    struct Voice
''')
rep('        float[16] frqV;       // Freq modulators: output (units of 4 octaves)\n',
    '        float[16] frqV;       // Freq modulators: output (units of 4 octaves)\n        SeqS[16]  seqS;       // MOD-SEQ: per-voice sequencers (Retrig on)\n')
# param events
ev = []
for m in range(10):
    b = BASE + 32 * m
    for k in range(16):
        ev.append('    event param%d (float v) { seqStep.at (%d) = clamp (v, 0.0f, 1.0f); }   // MOD-SEQ' % (b + k, m * 16 + k))
    ev += [
        '    event param%d (float v) { seqLen.at (%d) = clamp (v, 1.0f, 16.0f); }' % (b + 16, m),
        '    event param%d (float v) { seqRate.at (%d) = v; }' % (b + 17, m),
        '    event param%d (float v) { seqSync.at (%d) = v; }' % (b + 18, m),
        '    event param%d (float v) { seqDiv.at (%d) = v; }' % (b + 19, m),
        '    event param%d (float v) { seqGlide.at (%d) = v; }' % (b + 20, m),
        '    event param%d (float v) { seqDir.at (%d) = v; }' % (b + 21, m),
        '    event param%d (float v) { seqRetrig.at (%d) = v; }' % (b + 22, m),
        '    event param%d (float v) { seqPol.at (%d) = v; }' % (b + 23, m),
    ]
rep('    event param1600 (float v) { frqRate.at (0) = v; }\n', '\n'.join(ev) + '\n\n    event param1600 (float v) { frqRate.at (0) = v; }\n')
# source clamps 33 -> 43
n = src.count('clamp (int (v + 0.5f), 0, 33); mmScan(); }')
assert n == 256, n
src = src.replace('clamp (int (v + 0.5f), 0, 33); mmScan(); }', 'clamp (int (v + 0.5f), 0, 43); mmScan(); }')
# init defaults
rep('''        for (int fm = 0; fm < 10; ++fm)
        {
            frqRate.at (fm)   = 300.0f;''', '''        for (int sm = 0; sm < 10; ++sm)   // MOD-SEQ
        {
            seqLen.at (sm)  = 8.0f;
            seqRate.at (sm) = 4.0f;
            seqDiv.at (sm)  = 11.0f;
            seqPol.at (sm)  = 1.0f;
            seqG.at (sm)    = SeqS (0.0f, 0.0f, 1.0f, 0.5f);

            for (int sk = 0; sk < 16; ++sk)   // default pattern (same as the parameter defaults)
                seqStep.at (sm * 16 + sk) = seqDefault (sk);
        }

        for (int fm = 0; fm < 10; ++fm)
        {
            frqRate.at (fm)   = 300.0f;''')
# functions + source values
FUNCS = r'''    // ---------------- MOD-SEQ: step sequencers (sources 34..43) ----------------
    float seqDefault (int k)   // default step pattern
    {
        float[16] d = (0.5f, 1.0f, 0.25f, 0.75f, 0.0f, 0.6f, 0.3f, 0.9f, 0.5f, 1.0f, 0.25f, 0.75f, 0.0f, 0.6f, 0.3f, 0.9f);
        return d.at (k);
    }

    float seqStepHz (int m)
    {
        return seqSync.at (m) > 0.5f ? syncHz (seqDiv.at (m)) : seqRate.at (m);
    }

    // advances sequencer m by dt seconds
    SeqS seqRun (int m, float dt, SeqS s)
    {
        int   len = clamp (int (seqLen.at (m) + 0.5f), 1, 16);
        int   idx = clamp (int (s.idx + 0.5f), 0, len - 1);
        float hz  = max (seqStepHz (m), 0.01f);
        float ph  = s.ph + hz * dt;
        float dir = s.dir;
        int   md  = int (seqDir.at (m) + 0.5f);

        for (int k = 0; k < 4 && ph >= 1.0f; ++k)
        {
            ph -= 1.0f;

            if (md == 0)
                idx = (idx + 1) % len;
            else if (md == 1)
                idx = (idx + len - 1) % len;
            else if (md == 2)
            {
                int nx = idx + int (dir);

                if (nx >= len || nx < 0)
                    dir = -dir;

                idx = clamp (idx + int (dir), 0, len - 1);
            }
            else
                idx = clamp (int (abs (nextNoise()) * float (len)), 0, len - 1);
        }

        if (ph >= 1.0f)
            ph = 0.0f;

        float tv = seqStep.at (m * 16 + idx);
        float g  = seqGlide.at (m);
        float v  = s.v;

        if (g < 0.002f)
            v = tv;
        else
            v += (tv - v) * (1.0f - float (exp (-dt / max (g * 0.6f / hz, 0.00005f))));

        return SeqS (ph, float (idx), dir, v);
    }

    void updateSeqGlobal (float dt)
    {
        for (int m = 0; m < 10; ++m)
            if ((seqMask & (1 << m)) != 0)
                seqG.at (m) = seqRun (m, dt, seqG.at (m));
    }

    void updateVoiceSeq (int vi, float dt)
    {
        for (int m = 0; m < 10; ++m)
            if ((seqMask & (1 << m)) != 0 && seqRetrig.at (m) > 0.5f)
                voices.at (vi).seqS.at (m) = seqRun (m, dt, voices.at (vi).seqS.at (m));
    }

    float seqPolar (int m, float v)
    {
        return seqPol.at (m) > 0.5f ? v * 2.0f - 1.0f : v;
    }

'''
rep('    // Mod source value for a voice (1-10 LFO, 11-20 envelope, 21 velocity, 22 key, 23 random)\n', FUNCS + '    // Mod source value for a voice (1-10 LFO, 11-20 envelope, 21 velocity, 22 key, 23 random)\n')
rep('            return frqRetrig.at (src - 24) > 0.5f ? voices.at (vi).frqV.at (src - 24) : frqGV.at (src - 24);\n        return 0.0f;',
    '            return frqRetrig.at (src - 24) > 0.5f ? voices.at (vi).frqV.at (src - 24) : frqGV.at (src - 24);\n        if (src >= 34 && src <= 43)   // MOD-SEQ\n            return seqPolar (src - 34, seqRetrig.at (src - 34) > 0.5f ? voices.at (vi).seqS.at (src - 34).v : seqG.at (src - 34).v);\n        return 0.0f;')
rep('            return frqGV.at (src - 24);\n        return 0.0f;',
    '            return frqGV.at (src - 24);\n        if (src >= 34 && src <= 43)   // MOD-SEQ\n            return seqPolar (src - 34, seqG.at (src - 34).v);\n        return 0.0f;')
rep('            if (ss >= 24 && ! ((dd >= 6', '            if (ss >= 24 && ss <= 33 && ! ((dd >= 6')
rep('    float[2560] frqTab;\n', '    float[2560] frqTab;\n    SeqS[16]    seqG;      // MOD-SEQ: global sequencers (Retrig off)\n')
# note-on init
rep('                voices.at (v).frqV.at (lm)   = frqEval (lm, 0.0f);\n',
    '                voices.at (v).frqV.at (lm)   = frqEval (lm, 0.0f);\n                voices.at (v).seqS.at (lm)   = SeqS (0.0f, 0.0f, 1.0f, seqStep.at (lm * 16));   // MOD-SEQ\n')
# mask + global update
rep('''                if (mmSrcI.at (fs) >= 24 && mmDstI.at (fs) > 0)
                    frqMask |= 1 << (mmSrcI.at (fs) - 24);
            updateFrqGlobal (dt);''', '''                if (mmSrcI.at (fs) >= 24 && mmSrcI.at (fs) <= 33 && mmDstI.at (fs) > 0)
                    frqMask |= 1 << (mmSrcI.at (fs) - 24);
            seqMask = 0;   // MOD-SEQ
            for (int fs = 0; fs < mmTop; ++fs)
                if (mmSrcI.at (fs) >= 34 && mmDstI.at (fs) > 0)
                    seqMask |= 1 << (mmSrcI.at (fs) - 34);
            updateSeqGlobal (dt);
            updateFrqGlobal (dt);''')
rep('                updateVoiceFrq (i, dt);\n', '                updateVoiceFrq (i, dt);\n                updateVoiceSeq (i, dt);   // MOD-SEQ\n')
open(P, 'w').write(src)

# ---- index.js
def jrep(old, new):
    global js
    assert js.count(old) == 1, (js.count(old), old)
    js = js.replace(old, new)
jrep('''    Array.from({ length: 10 }, (_, i) => "Freq " + (i + 1))
);''', '''    Array.from({ length: 10 }, (_, i) => "Freq " + (i + 1)),
    Array.from({ length: 10 }, (_, i) => "Seq " + (i + 1))   // MOD-SEQ
);''')
jrep('[24, "Freq"]];', '[24, "Freq"], [34, "Sequencer"]];')
jrep('"Source", 0, 33, 0,', '"Source", 0, 43, 0,') if False else None
js = js.replace('" Source", 0, 33, 0, "", "sel", MOD_SRC', '" Source", 0, 43, 0, "", "sel", MOD_SRC')
jrep('(n >= 24 && n <= 33 ? "FRQ " + (n - 23) : "");', '(n >= 24 && n <= 33 ? "FRQ " + (n - 23) : n >= 34 && n <= 43 ? "SEQ " + (n - 33) : "");')
jrep('n >= 24 ? "#b57bff" : "#c9c24a"', 'n >= 34 ? "#5be08a" : n >= 24 ? "#b57bff" : "#c9c24a"')
specs = '''    // MOD-SEQ: 10 step sequencers (modulation sources 34..43), ids 3600 + 32 * m + k
    for (let m = 0; m < 10; m++) {
        const b = 3600 + 32 * m, n = "Seq " + (m + 1);
        for (let k = 0; k < 16; k++) L.push([b + k, n + " Step " + (k + 1), 0, 1, [0.5, 1, 0.25, 0.75, 0, 0.6, 0.3, 0.9][k % 8], "", "sld", null, 1, "Step " + (k + 1)]);
        L.push([b + 16, n + " Length",    1, 16, 8, "", "stp", null, 1, "Length"]);
        L.push([b + 17, n + " Rate",      0.05, 40, 4, "Hz", "sld", null, 1, "Rate"]);
        L.push([b + 18, n + " Sync",      0, 1, 0, "", "btn", ["Free", "Sync"], 1, "Sync"]);
        L.push([b + 19, n + " Division",  0, 17, 11, "", "sel", SYNC_DIVS, 1, "Division"]);
        L.push([b + 20, n + " Glide",     0, 1, 0, "", "sld", null, 1, "Glide"]);
        L.push([b + 21, n + " Direction", 0, 3, 0, "", "sel", ["Forward", "Backward", "Ping-Pong", "Random"], 1, "Direction"]);
        L.push([b + 22, n + " Retrig",    0, 1, 0, "", "btn", ["Free", "Note"], 1, "Retrig"]);
        L.push([b + 23, n + " Bipolar",    0, 1, 1, "", "btn", ["Unipolar", "Bipolar"], 1, "Polarity"]);
    }
'''
anchor = '    L.push([880, "Bus 1 Level"' 
if js.count(anchor) != 1:
    # bus levels were removed from the UI; anchor on the LFO polarity block instead
    anchor = '    // MOD-LFOBIP: Polarity of every LFO (3111 + i), default Bipolar\n'
jrep(anchor, specs + anchor)
open(J, 'w').write(js)
print('ok')
