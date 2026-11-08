#!/usr/bin/env python3
"""Idempotent (marker MOD-SEQ2): Spire-style stepper features for the 10 sequencers:
per-step wave shape (8 shapes: flat, ramp down, ramp up, triangle, half sine, gate 50 %, gate 25 %, decay), Hold (shapes off),
Loop start step, Time x1-x4, Sync mode Spos (position locked to the host).
Parameters: +24 Time, +25 Loop, +26 Hold of 3600 + 32 * m, shapes 5000 + 16 * m + k, Sync (+18) now 0 Free / 1 Sync / 2 Spos."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); J = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); js = open(J).read()
if 'MOD-SEQ2' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)

# ---- declarations
src, n = re.subn(r'(name: "Seq \d+ Sync", min: 0\.0, )max: 1\.0', r'\g<1>max: 2.0', src); assert n == 10, n
decl = []
for m in range(10):
    b = 3600 + 32 * m
    decl.append('    input event float param%d [[ name: "Seq %d Time", min: 0.0, max: 3.0, init: 0.0, step: 1.0 ]];   // MOD-SEQ2' % (b + 24, m + 1))
    decl.append('    input event float param%d [[ name: "Seq %d Loop", min: 1.0, max: 16.0, init: 1.0, step: 1.0 ]];   // MOD-SEQ2' % (b + 25, m + 1))
    decl.append('    input event float param%d [[ name: "Seq %d Hold", min: 0.0, max: 1.0, init: 0.0, step: 1.0 ]];   // MOD-SEQ2' % (b + 26, m + 1))
for m in range(10):
    for k in range(16):
        decl.append('    input event float param%d [[ name: "Seq %d Step %d Shape", min: 0.0, max: 7.0, init: 0.0, step: 1.0 ]];   // MOD-SEQ2' % (5000 + 16 * m + k, m + 1, k + 1))
rep('    input event float param3911 [[ name: "Seq 10 Bipolar", min: 0.0, max: 1.0, init: 1.0, step: 1.0 ]];   // MOD-SEQ\n',
    '    input event float param3911 [[ name: "Seq 10 Bipolar", min: 0.0, max: 1.0, init: 1.0, step: 1.0 ]];   // MOD-SEQ\n' + '\n'.join(decl) + '\n')

# ---- state
rep('    float[16]   seqPol;    // 1 = bipolar\n',
    '    float[16]   seqPol;    // 1 = bipolar\n    float[16]   seqTime;   // MOD-SEQ2: rate multiplier 0..3 = x1..x4\n    float[16]   seqLoop;   // MOD-SEQ2: first step of the loop (1..16)\n    float[16]   seqHold;   // MOD-SEQ2: 1 = step shapes off (flat steps)\n    float[160]  seqShape;  // MOD-SEQ2: wave shape of every step\n')
rep('            seqPol.at (sm)  = 1.0f;\n', '            seqPol.at (sm)  = 1.0f;\n            seqLoop.at (sm) = 1.0f;   // MOD-SEQ2\n')
ev = []
for m in range(10):
    b = 3600 + 32 * m
    ev.append('    event param%d (float v) { seqTime.at (%d) = v; }   // MOD-SEQ2' % (b + 24, m))
    ev.append('    event param%d (float v) { seqLoop.at (%d) = v; }   // MOD-SEQ2' % (b + 25, m))
    ev.append('    event param%d (float v) { seqHold.at (%d) = v; }   // MOD-SEQ2' % (b + 26, m))
for m in range(10):
    for k in range(16):
        ev.append('    event param%d (float v) { seqShape.at (%d) = v; }   // MOD-SEQ2' % (5000 + 16 * m + k, m * 16 + k))
rep('    event param1600 ', '\n'.join(ev) + '\n    event param1600 ')

# ---- DSP
a = src.index('    float seqStepHz (int m)'); z = src.index('    void updateSeqGlobal (float dt)')
FUNCS = r'''    float seqMult (int m)   // MOD-SEQ2: Time x1..x4
    {
        return float (clamp (int (seqTime.at (m) + 0.5f), 0, 3) + 1);
    }

    float seqStepHz (int m)
    {
        return (seqSync.at (m) > 0.5f ? syncHz (seqDiv.at (m)) : seqRate.at (m)) * seqMult (m);
    }

    // shape of one step over its length (ph 0..1): 0 flat, 1 ramp down, 2 ramp up, 3 triangle, 4 half sine, 5 gate 50 %, 6 gate 25 %, 7 decay
    float seqShapeVal (int sh, float ph)
    {
        if (sh == 1) return 1.0f - ph;
        if (sh == 2) return ph;
        if (sh == 3) return 1.0f - abs (2.0f * ph - 1.0f);
        if (sh == 4) return float (sin (3.14159265f * ph));
        if (sh == 5) return ph < 0.5f ? 1.0f : 0.0f;
        if (sh == 6) return ph < 0.25f ? 1.0f : 0.0f;
        if (sh == 7) return float (exp (-4.0f * ph));
        return 1.0f;
    }

    // advances sequencer m by dt seconds
    SeqS seqRun (int m, float dt, SeqS s)
    {
        int   len = clamp (int (seqLen.at (m) + 0.5f), 1, 16);
        int   lp  = clamp (int (seqLoop.at (m) + 0.5f) - 1, 0, len - 1);   // MOD-SEQ2: first step of the loop
        int   idx = clamp (int (s.idx + 0.5f), 0, len - 1);
        float hz  = max (seqStepHz (m), 0.01f);
        float ph  = s.ph + hz * dt;
        float dir = s.dir;
        int   md  = int (seqDir.at (m) + 0.5f);

        if (seqSync.at (m) > 1.5f)   // MOD-SEQ2: Spos, the position follows the host (loop region only)
        {
            float64 sb  = float64 (divBeats.at (clamp (int (seqDiv.at (m) + 0.5f), 0, 17))) / float64 (seqMult (m));
            float64 pos = fxBeat / sb;
            int     n   = int (floor (pos));
            int     reg = len - lp;
            int     per = max (2 * reg - 2, 1);
            int     k   = ((n % reg) + reg) % reg;

            ph = float (pos - float64 (n));

            if (md == 1)
                idx = len - 1 - k;
            else if (md == 2)
            {
                int p = ((n % per) + per) % per;
                idx = lp + (p < reg ? p : per - p);
            }
            else
                idx = lp + k;
        }
        else
        {
            for (int k = 0; k < 4 && ph >= 1.0f; ++k)
            {
                ph -= 1.0f;

                if (md == 0)
                    idx = idx + 1 >= len ? lp : idx + 1;
                else if (md == 1)
                    idx = idx - 1 < lp ? len - 1 : idx - 1;
                else if (md == 2)
                {
                    int nx = idx + int (dir);

                    if (nx >= len || nx < lp)
                        dir = -dir;

                    idx = clamp (idx + int (dir), lp, len - 1);
                }
                else
                    idx = lp + clamp (int (abs (nextNoise()) * float (len - lp)), 0, len - lp - 1);
            }

            if (ph >= 1.0f)
                ph = 0.0f;
        }

        float lvl = seqStep.at (m * 16 + idx);
        int   sh  = seqHold.at (m) > 0.5f ? 0 : int (seqShape.at (m * 16 + idx) + 0.5f);
        float shp = seqShapeVal (sh, ph);
        float tv  = seqPol.at (m) > 0.5f ? 0.5f + (lvl - 0.5f) * shp : lvl * shp;
        float g   = seqGlide.at (m);
        float v   = s.v;

        if (g < 0.002f)
            v = tv;
        else
            v += (tv - v) * (1.0f - float (exp (-dt / max (g * 0.6f / hz, 0.00005f))));

        return SeqS (ph, float (idx), dir, v);
    }

'''
src = src[:a] + FUNCS + src[z:]
open(P, 'w').write(src)

# ---- index.js specs
def jrep(old, new):
    global js
    assert js.count(old) == 1, (old[:70], js.count(old))
    js = js.replace(old, new)
jrep('L.push([b + 18, n + " Sync",      0, 1, 0, "", "btn", ["Free", "Sync"], 1, "Sync"]);', 'L.push([b + 18, n + " Sync",      0, 2, 0, "", "sel", ["Free", "Sync", "Spos"], 1, "Sync"]);')
specs = '''        L.push([b + 24, n + " Time",      0, 3, 0, "", "sel", ["x1", "x2", "x3", "x4"], 1, "Time"]);   // MOD-SEQ2
        L.push([b + 25, n + " Loop",      1, 16, 1, "", "stp", null, 1, "Loop"]);
        L.push([b + 26, n + " Hold",      0, 1, 0, "", "btn", ["Off", "On"], 1, "Hold"]);
        for (let k = 0; k < 16; k++) L.push([5000 + 16 * m + k, n + " Step " + (k + 1) + " Shape", 0, 7, 0, "", "sel", SEQ_SHAPES, 1, "Shape"]);
'''
anchor = '        L.push([b + 23, n + " Bipolar",    0, 1, 1, "", "btn", ["Unipolar", "Bipolar"], 1, "Polarity"]);\n'
jrep(anchor, anchor + specs)
jrep('const SYNC_DIVS = [', 'const SEQ_SHAPES = ["Flat", "Ramp down", "Ramp up", "Triangle", "Half sine", "Gate 50%", "Gate 25%", "Decay"];   // MOD-SEQ2\nconst SYNC_DIVS = [')
open(J, 'w').write(js)
print('applied')
