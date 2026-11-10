#!/usr/bin/env python3
"""Idempotent (marker MOD-SQM): three more arpeggiator modes (Arp Mode 6..8) that play polyphonic, scheduled notes instead of one note per step:
  6 Euclid / Poly   4 lanes (On, Steps 1-64, Pulses, Rotation, Offset, Probability, Ratchet); a lane hits step i when ((i + rot) % steps * pulses) % steps < pulses,
                    the lanes run on the same clock with their own lengths (polyrhythm).  ids 5710 + 8 * lane + k (k 0..6).
  7 Melodic         up to 64 steps: note, velocity, length (10-400 % of a step, > 100 % ties into the next), chord type, probability, ratchet (1-4), gate.
                    length id 5800, rows at 5810 + 64 * row + step (row 0 note, 1 vel, 2 len, 3 chord, 4 prob, 5 ratchet, 6 gate).
  8 Generative      Turing machine (shift register of 2-16 bits, mutation %) or random walk, mapped to a scale (12 scales) over a range above the root.
                    ids 5750 + k: type, scale, range, shift, loop, mutation, max step, bias, rest, ratchet.
The root is the last key pressed.  All parameters are `automatable: false`.  Notes are scheduled (events with a start time in steps, sounding notes with an end time),
so chords, ratchets and ties work; state is cleared when the arp stops or the mode changes."""
import os, sys
P = os.path.join(os.path.dirname(__file__), '..', '..', 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'MOD-SQM' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:80], src.count(old))
    src = src.replace(old, new)

rep('"Arp Mode", min: 0.0, max: 5.0,', '"Arp Mode", min: 0.0, max: 8.0,')

# ---------------- parameters
NOTE = [0, 0, 12, 0, 7, 0, 12, 0, 0, 0, 10, 0, 7, 0, 5, 0]
GATE = [1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1]
LANES = [(1, 16, 5, 0, 0), (0, 12, 3, 0, 7), (0, 7, 2, 0, 12), (0, 5, 1, 0, -12)]   # on, steps, pulses, rot, offset
decl = ''
def D(num, name, lo, hi, init):
    global decl
    decl += '    input event float param%d [[ name: "%s", min: %s, max: %s, init: %s, step: 1.0, automatable: false ]];   // MOD-SQM\n' % (num, name, float(lo), float(hi), float(init))
for l, (on, steps, pul, rot, off) in enumerate(LANES):
    b = 5710 + 8 * l
    D(b, 'Euclid Lane %d On' % (l + 1), 0, 1, on); D(b + 1, 'Euclid Lane %d Steps' % (l + 1), 1, 64, steps); D(b + 2, 'Euclid Lane %d Pulses' % (l + 1), 0, 64, pul)
    D(b + 3, 'Euclid Lane %d Rotation' % (l + 1), 0, 63, rot); D(b + 4, 'Euclid Lane %d Offset' % (l + 1), -24, 24, off)
    D(b + 5, 'Euclid Lane %d Probability' % (l + 1), 0, 100, 100); D(b + 6, 'Euclid Lane %d Ratchet' % (l + 1), 1, 4, 1)
GEN = [('Type', 0, 1, 0), ('Scale', 0, 11, 2), ('Range', 12, 48, 24), ('Shift', -24, 24, 0), ('Loop', 2, 16, 8), ('Mutation', 0, 100, 20), ('Max Step', 1, 7, 2), ('Bias', -100, 100, 0), ('Rest', 0, 100, 10), ('Ratchet', 1, 4, 1)]
for k, (nm, lo, hi, ini) in enumerate(GEN):
    D(5750 + k, 'Generative %s' % nm, lo, hi, ini)
D(5800, 'Melodic Length', 1, 64, 16)
ROWS = [('Note', -24, 24), ('Velocity', 1, 127), ('Length', 10, 400), ('Chord', 0, 8), ('Probability', 0, 100), ('Ratchet', 1, 4), ('Gate', 0, 1)]
def rowdef(r, k):
    return [NOTE[k % 16], 100, 80, 0, 100, 1, GATE[k % 16]][r]
for r, (nm, lo, hi) in enumerate(ROWS):
    for k in range(64):
        D(5810 + 64 * r + k, 'Melodic Step %d %s' % (k + 1, nm), lo, hi, rowdef(r, k))
a = '    input event float param5264 '
i = src.index(a); j = src.index('\n', i) + 1
# after the last 303 declaration (steps 17-64 follow it): put the block before the Seq Key Start line instead, which is a stable anchor
a = '    input event float param3929 '
i = src.index(a); j = src.index('\n', i) + 1
src = src[:j] + decl + src[j:]

# ---------------- state
st = '''    // ---------------- MOD-SQM: Euclid / Melodic / Generative arpeggiator modes ----------------
    float[32]   sqEu;                 // 4 lanes x 8: on, steps, pulses, rotation, offset, probability, ratchet
    float[16]   sqGn;                 // generative: type, scale, range, shift, loop, mutation, max step, bias, rest, ratchet
    float       sqMlLen = 16.0f;
    float[448]  sqMl;                 // melodic: 7 rows x 64 steps (note, velocity, length, chord, probability, ratchet, gate)
    int[16]     sqN;                  // sounding notes
    float64[16] sqEnd;                // ... and the time (in steps) at which they end
    int         sqCnt = 0;
    int[32]     evN;                  // pending note starts
    float[32]   evV;
    float64[32] evT;                  // start time in steps
    float[32]   evL;                  // length in steps
    int         evCnt = 0;
    int         gnReg = 0;            // turing machine shift register
    int         gnDeg = -1;           // random walk position (degree index)
'''
rep('    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n', st + '    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n')

# ---------------- handlers
ev = ''
for l in range(4):
    for k in range(7):
        ev += '    event param%d (float v) { sqEu.at (%d) = v; }   // MOD-SQM\n' % (5710 + 8 * l + k, 8 * l + k)
for k in range(10):
    ev += '    event param%d (float v) { sqGn.at (%d) = v; }\n' % (5750 + k, k)
ev += '    event param5800 (float v) { sqMlLen = v; }\n'
for r in range(7):
    for k in range(64):
        ev += '    event param%d (float v) { sqMl.at (%d) = v; }\n' % (5810 + 64 * r + k, 64 * r + k)
rep('    event param3920 (float v) { arpOn = v; }', ev + '    event param3920 (float v) { arpOn = v; }')

# ---------------- defaults (non zero values of the arrays; the declarations above carry the same init values)
ini = '        // MOD-SQM defaults\n'
for l, (on, steps, pul, rot, off) in enumerate(LANES):
    for k, v in enumerate([on, steps, pul, rot, off, 100, 1]):
        if v != 0: ini += '        sqEu.at (%d) = %d.0f;\n' % (8 * l + k, v)
for k, (nm, lo, hi, v) in enumerate(GEN):
    if v != 0: ini += '        sqGn.at (%d) = %d.0f;\n' % (k, v)
ini += '        for (int mk = 0; mk < 64; ++mk)\n        {\n            sqMl.at (64 + mk)  = 100.0f;\n            sqMl.at (128 + mk) = 80.0f;\n            sqMl.at (256 + mk) = 100.0f;\n            sqMl.at (320 + mk) = 1.0f;\n        }\n\n'
for k in range(64):
    if NOTE[k % 16]: ini += '        sqMl.at (%d) = %d.0f;\n' % (k, NOTE[k % 16])
    if GATE[k % 16]: ini += '        sqMl.at (%d) = 1.0f;\n' % (384 + k)
ini += '\n'
rep('        for (int sm = 0; sm < 10; ++sm)   // MOD-SEQ\n        {\n            seqLen.at (sm)  = 8.0f;', ini + '        for (int sm = 0; sm < 10; ++sm)   // MOD-SEQ\n        {\n            seqLen.at (sm)  = 8.0f;')

# ---------------- engine
ENGINE = r'''    // ---- MOD-SQM: scheduled notes for the Euclid / Melodic / Generative modes ----
    bool sqHas (int nn)
    {
        for (int i = 0; i < sqCnt; ++i)
            if (sqN.at (i) == nn)
                return true;

        return false;
    }

    void sqAllOff()
    {
        for (int i = 0; i < sqCnt; ++i)
            voiceNoteOff (sqN.at (i));

        sqCnt = 0;
        evCnt = 0;
    }

    void evAdd (int nn, float vel, float64 t, float len)
    {
        if (evCnt >= 32)
            return;

        evN.at (evCnt) = clamp (nn, 0, 127);
        evV.at (evCnt) = vel;
        evT.at (evCnt) = t;
        evL.at (evCnt) = max (len, 0.02f);
        evCnt++;
    }

    void sqFire (int nn, float vel, float64 endT)
    {
        for (int i = 0; i < sqCnt; ++i)
            if (sqN.at (i) == nn)   // the same note again: restart it
            {
                voiceNoteOff (nn);
                voiceNoteOn (nn, vel);
                sqEnd.at (i) = endT;
                return;
            }

        if (sqCnt >= 16)   // full: the oldest note makes room
        {
            voiceNoteOff (sqN.at (0));

            for (int j = 0; j < 15; ++j)
            {
                sqN.at (j)   = sqN.at (j + 1);
                sqEnd.at (j) = sqEnd.at (j + 1);
            }

            sqCnt = 15;
        }

        sqN.at (sqCnt)   = nn;
        sqEnd.at (sqCnt) = endT;
        sqCnt++;
        voiceNoteOn (nn, vel);
    }

    void sqTick (float64 now)
    {
        for (int i = evCnt - 1; i >= 0; --i)
            if (evT.at (i) <= now)
            {
                sqFire (evN.at (i), evV.at (i), evT.at (i) + float64 (evL.at (i)));
                evCnt--;
                evN.at (i) = evN.at (evCnt);
                evV.at (i) = evV.at (evCnt);
                evT.at (i) = evT.at (evCnt);
                evL.at (i) = evL.at (evCnt);
            }

        for (int i = sqCnt - 1; i >= 0; --i)
            if (sqEnd.at (i) <= now)
            {
                voiceNoteOff (sqN.at (i));
                sqCnt--;
                sqN.at (i)   = sqN.at (sqCnt);
                sqEnd.at (i) = sqEnd.at (sqCnt);
            }
    }

    float sqRand01()
    {
        return nextNoise() * 0.5f + 0.5f;
    }

    int sqChordCount (int t)
    {
        if (t == 0) return 1;
        if (t <= 2 || t == 0) return 2;
        if (t == 6 || t == 7) return 4;
        return 3;
    }

    int sqChordInt (int t, int i)
    {
        if (i == 0) return 0;
        if (t == 1) return 12;
        if (t == 2) return 7;
        if (t == 3) return i == 1 ? 4 : 7;
        if (t == 4) return i == 1 ? 3 : 7;
        if (t == 5) return i == 1 ? 5 : 7;
        if (t == 6) return i == 1 ? 4 : (i == 2 ? 7 : 11);
        if (t == 7) return i == 1 ? 3 : (i == 2 ? 7 : 10);
        return i == 1 ? 3 : 6;
    }

    int sqScaleMask (int sc)
    {
        if (sc == 1)  return 2741;   // major
        if (sc == 2)  return 1453;   // minor
        if (sc == 3)  return 1709;   // dorian
        if (sc == 4)  return 1451;   // phrygian
        if (sc == 5)  return 2773;   // lydian
        if (sc == 6)  return 1717;   // mixolydian
        if (sc == 7)  return 2477;   // harmonic minor
        if (sc == 8)  return 661;    // major pentatonic
        if (sc == 9)  return 1193;   // minor pentatonic
        if (sc == 10) return 1257;   // blues
        if (sc == 11) return 1365;   // whole tone
        return 4095;                 // chromatic
    }

    int sqScaleCount (int mask, int range)
    {
        int n = 0;

        for (int s = 0; s < range; ++s)
            if (((mask >> (s % 12)) & 1) != 0)
                n++;

        return max (n, 1);
    }

    int sqScaleNote (int mask, int range, int idx)
    {
        int n = 0;
        int last = 0;

        for (int s = 0; s < range; ++s)
            if (((mask >> (s % 12)) & 1) != 0)
            {
                last = s;

                if (n == idx)
                    return s;

                n++;
            }

        return last;
    }

    void sqEuclid (int st)
    {
        int root = arpHN.at (max (arpN - 1, 0));

        for (int l = 0; l < 4; ++l)
        {
            int b = l * 8;

            if (sqEu.at (b) < 0.5f)
                continue;

            int len = clamp (int (sqEu.at (b + 1) + 0.5f), 1, 64);
            int pul = clamp (int (sqEu.at (b + 2) + 0.5f), 0, len);
            int rot = max (int (sqEu.at (b + 3) + 0.5f), 0);
            int idx = st % len;
            int j   = (idx + rot) % len;

            if (pul <= 0 || (j * pul) % len >= pul)
                continue;

            if (sqEu.at (b + 5) < 99.5f && sqRand01() * 100.0f >= sqEu.at (b + 5))
                continue;

            int   rat = clamp (int (sqEu.at (b + 6) + 0.5f), 1, 4);
            int   nn  = root + int (sqEu.at (b + 4));
            float vel = idx == 0 ? 1.0f : 0.7f;

            for (int r = 0; r < rat; ++r)
                evAdd (nn, vel, float64 (st) + float64 (r) / float64 (rat), arpGate / float (rat));
        }
    }

    void sqMelodic (int st)
    {
        int si = st % clamp (int (sqMlLen + 0.5f), 1, 64);

        if (sqMl.at (384 + si) < 0.5f)
            return;

        if (sqMl.at (256 + si) < 99.5f && sqRand01() * 100.0f >= sqMl.at (256 + si))
            return;

        int   root = arpHN.at (max (arpN - 1, 0));
        int   nn   = root + int (sqMl.at (si));
        float vel  = clamp (sqMl.at (64 + si) / 127.0f, 0.01f, 1.0f);
        float len  = sqMl.at (128 + si) * 0.01f;
        int   ct   = clamp (int (sqMl.at (192 + si) + 0.5f), 0, 8);
        int   rat  = clamp (int (sqMl.at (320 + si) + 0.5f), 1, 4);
        int   cn   = sqChordCount (ct);

        for (int r = 0; r < rat; ++r)
            for (int c = 0; c < cn; ++c)
                evAdd (nn + sqChordInt (ct, c), vel, float64 (st) + float64 (r) / float64 (rat), len / float (rat));
    }

    void sqGenerative (int st)
    {
        int   root  = arpHN.at (max (arpN - 1, 0));
        int   type  = int (sqGn.at (0) + 0.5f);
        int   mask  = sqScaleMask (int (sqGn.at (1) + 0.5f));
        int   range = clamp (int (sqGn.at (2) + 0.5f), 12, 48);
        int   n     = sqScaleCount (mask, range);
        int   idx   = 0;
        float accent = 0.0f;

        if (type == 0)   // turing machine
        {
            int ll   = clamp (int (sqGn.at (4) + 0.5f), 2, 16);
            int msk  = (1 << ll) - 1;

            if (gnReg == 0)
                gnReg = (11354 & msk) | 1;

            int bit = (gnReg >> (ll - 1)) & 1;

            if (sqRand01() * 100.0f < sqGn.at (5))
                bit = 1 - bit;

            gnReg = ((gnReg << 1) | bit) & msk;
            idx   = clamp (int (float (gnReg) / float (msk) * float (n)), 0, n - 1);
            accent = float ((gnReg >> 1) & 1);
        }
        else   // random walk
        {
            int ms = clamp (int (sqGn.at (6) + 0.5f), 1, 7);

            if (gnDeg < 0)
                gnDeg = n / 2;

            int d  = int (sqRand01() * float (2 * ms + 1)) - ms;
            float bs = sqGn.at (7);

            if (bs > 0.0f && sqRand01() * 100.0f < bs)
                d = abs (d);
            else if (bs < 0.0f && sqRand01() * 100.0f < -bs)
                d = -abs (d);

            gnDeg += d;

            if (gnDeg < 0)
                gnDeg = -gnDeg;

            if (gnDeg > n - 1)
                gnDeg = max (2 * (n - 1) - gnDeg, 0);

            gnDeg  = clamp (gnDeg, 0, n - 1);
            idx    = gnDeg;
            accent = d != 0 && abs (d) >= ms ? 1.0f : 0.0f;
        }

        if (sqRand01() * 100.0f < sqGn.at (8))   // rest
            return;

        int nn  = root + int (sqGn.at (3)) + sqScaleNote (mask, range, idx);
        int rat = clamp (int (sqGn.at (9) + 0.5f), 1, 4);

        for (int r = 0; r < rat; ++r)
            evAdd (nn, accent > 0.5f ? 1.0f : 0.65f, float64 (st) + float64 (r) / float64 (rat), arpGate / float (rat));
    }

'''
rep('    void arpTick (float dt)\n    {\n', ENGINE + '    void arpTick (float dt)\n    {\n        int amd = int (arpMode + 0.5f);   // MOD-SQM\n\n        if (amd < 6 && (sqCnt > 0 || evCnt > 0))\n            sqAllOff();\n\n')
rep('''            arpPh   = 1.0f;
            arpStep = 0;
            a3Prev  = false;   // MOD-ARP303
            return;''', '''            arpPh   = 1.0f;
            arpStep = 0;
            a3Prev  = false;   // MOD-ARP303
            gnReg   = 0;       // MOD-SQM
            gnDeg   = -1;

            if (sqCnt > 0 || evCnt > 0)
                sqAllOff();

            return;''')
rep('''        float hz = arpSync > 0.5f ? syncHz (arpDiv) : arpRate;
        arpPh += max (hz, 0.01f) * dt;
''', '''        float hz = arpSync > 0.5f ? syncHz (arpDiv) : arpRate;
        arpPh += max (hz, 0.01f) * dt;

        if (amd >= 6)   // MOD-SQM: Euclid / Melodic / Generative
        {
            if (arpPh >= 1.0f)
            {
                arpPh -= 1.0f;

                if (arpPh >= 1.0f)
                    arpPh = 0.0f;

                int sn = arpStep;
                arpStep++;

                if (amd == 6)
                    sqEuclid (sn);
                else if (amd == 7)
                    sqMelodic (sn);
                else
                    sqGenerative (sn);
            }

            sqTick (float64 (arpStep - 1) + float64 (arpPh));
            return;
        }
''')
rep('            if (arpOn < 0.5f || arpCur != nn)\n                voiceNoteOff (nn);', '            if (arpOn < 0.5f || (arpCur != nn && ! sqHas (nn)))   // MOD-SQM: a sequencer note with the same number keeps sounding\n                voiceNoteOff (nn);')
open(P, 'w').write(src)
print('applied')
