#!/usr/bin/env python3
"""Idempotent (marker MOD-PLINKO): three more arpeggiator modes (Arp Mode 9..11) on the scheduled-note engine of MOD-SQM (the root is the last key pressed):
  9  Plinko        balls fall through a board of pegs: every row sends the ball left or right (Bias, Momentum), the bin it lands in (0..Rows) is a scale degree.
                   Drop X moves the drop point, Balls = balls per step, Loop / Seed repeat the same fall, Chord stacks a chord on every ball.
                   ids 6300 + k: Rows, Scale, Range, Shift, Drop X, Bias, Momentum, Balls, Gate, Loop, Chord, Velocity, Rest, Seed, Vel Spread.
                   Every ball is reported to the editor by the output event seqPos as 2000000 + bin + 16 * rows + 256 * path (bit r = row r went right).
  10 Bounce        a bouncing ball: the gaps between the notes shrink (Decay) like a ball coming to rest, the pitch walks through the scale, then a Pause and again.
                   ids 6320 + k: Start Gap, Decay, Bounces, Pitch Step, Scale, Range, Shift, Vel Decay, Pause, Gate, Chord, Velocity, Rest, Direction.
  11 Cellular      a one dimensional cellular automaton (Wolfram rule 0..255, wrapping row of 4..16 cells): every generation the living cells play the scale
                   degrees of their position (Max Notes limits the chord).  ids 6340 + k: Rule, Cells, Scale, Range, Shift, Mutation, Gate, Velocity, Max Notes, Rest, Every, Chord.
All parameters are `automatable: false`; state is cleared when the arp stops or the mode changes."""
import os, sys
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); J = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); js = open(J).read()
if 'MOD-PLINKO' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:80], src.count(old))
    src = src.replace(old, new)

rep('"Arp Mode", min: 0.0, max: 8.0,', '"Arp Mode", min: 0.0, max: 11.0,')

PL = [('Rows', 2, 12, 8), ('Scale', 0, 11, 9), ('Range', 12, 48, 24), ('Shift', -24, 24, 0), ('Drop X', -100, 100, 0), ('Bias', -100, 100, 0), ('Momentum', 0, 100, 0), ('Balls', 1, 4, 1),
      ('Gate', 10, 400, 80), ('Loop', 0, 64, 0), ('Chord', 0, 8, 0), ('Velocity', 1, 127, 100), ('Rest', 0, 100, 0), ('Seed', 0, 999, 0), ('Vel Spread', 0, 100, 20)]
BN = [('Start Gap', 25, 400, 100), ('Decay', 50, 98, 80), ('Bounces', 2, 16, 8), ('Pitch Step', -4, 4, 1), ('Scale', 0, 11, 2), ('Range', 12, 48, 24), ('Shift', -24, 24, 0), ('Vel Decay', 50, 100, 85),
      ('Pause', 0, 8, 1), ('Gate', 10, 100, 60), ('Chord', 0, 8, 0), ('Velocity', 1, 127, 100), ('Rest', 0, 100, 0), ('Direction', 0, 2, 0)]
CE = [('Rule', 0, 255, 90), ('Cells', 4, 16, 8), ('Scale', 0, 11, 2), ('Range', 12, 48, 24), ('Shift', -24, 24, 0), ('Mutation', 0, 100, 5), ('Gate', 10, 400, 70), ('Velocity', 1, 127, 100),
      ('Max Notes', 1, 8, 3), ('Rest', 0, 100, 0), ('Every', 1, 4, 1), ('Chord', 0, 8, 0)]
GROUPS = [(6300, 'Plinko', PL, 'plk'), (6320, 'Bounce', BN, 'bnc'), (6340, 'Cellular', CE, 'cel')]

decl = ''; ev = ''; ini = ''
for base, nm, lst, arr in GROUPS:
    for k, (n, lo, hi, d) in enumerate(lst):
        decl += '    input event float param%d [[ name: "%s %s", min: %s, max: %s, init: %s, step: 1.0, automatable: false ]];   // MOD-PLINKO\n' % (base + k, nm, n, float(lo), float(hi), float(d))
        ev += '    event param%d (float v) { %s.at (%d) = v; }   // MOD-PLINKO\n' % (base + k, arr, k)
        if d != 0: ini += '        %s.at (%d) = %s;\n' % (arr, k, float(d))
a = '    input event float param3929 '
i = src.index(a); j = src.index('\n', i) + 1
src = src[:j] + decl + src[j:]
rep('    event param3920 (float v) { arpOn = v; }', ev + '    event param3920 (float v) { arpOn = v; }')
rep('        // MOD-SQM defaults\n', '        // MOD-SQM defaults\n' + ini)

st = '''    // ---------------- MOD-PLINKO: Plinko / Bounce / Cellular arpeggiator modes ----------------
    float[16]   plk;                  // plinko parameters (see tools/mod/build_plinko.py)
    float[16]   bnc;                  // bounce parameters
    float[16]   cel;                  // cellular parameters
    int         plkS = 1;             // plinko random state (Seed > 0: the fall repeats every Loop steps)
    int         plkDir = 0;           // direction of the last row of the last ball (momentum)
    int         bnNext = 0;           // step at which the next bounce cycle starts
    int         celS = 0;             // cellular automaton: living cells as bits
    int         celGen = 0;           // generations since the start
'''
rep('    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n', st + '    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n')

ENGINE = r'''    // ---- MOD-PLINKO ----
    float plkRand()
    {
        plkS = plkS * 1103515245 + 12345;
        return float ((plkS >> 8) & 65535) / 65536.0f;
    }

    float plkR()   // the seeded generator while Seed > 0, otherwise the noise of the synth
    {
        return plk.at (13) > 0.5f ? plkRand() : sqRand01();
    }

    void plkAddChord (int base, float vel, float64 t, float len, int ct)
    {
        int cc = sqChordCount (ct);

        for (int c = 0; c < cc; ++c)
            evAdd (base + sqChordInt (ct, c), vel, t, len);
    }

    void plinkoStep (int st)
    {
        int root  = arpHN.at (max (arpN - 1, 0));
        int rows  = clamp (int (plk.at (0) + 0.5f), 2, 12);
        int mask  = sqScaleMask (int (plk.at (1) + 0.5f));
        int range = clamp (int (plk.at (2) + 0.5f), 12, 48);
        int n     = sqScaleCount (mask, range);
        int lp    = int (plk.at (9) + 0.5f);
        int balls = clamp (int (plk.at (7) + 0.5f), 1, 4);
        int ct    = int (plk.at (10) + 0.5f);
        float pr  = clamp (0.5f + plk.at (5) / 200.0f, 0.02f, 0.98f);
        float mom = plk.at (6) / 100.0f;
        int   drop = int (floor (plk.at (4) / 100.0f * float (rows) * 0.5f + 0.5f));

        if (plk.at (13) > 0.5f && (lp > 0 ? (st % lp) == 0 : st == 0))
            plkS = int (plk.at (13)) * 7919 + 13;

        for (int b = 0; b < balls; ++b)
        {
            if (plkR() * 100.0f >= plk.at (12))
            {
                int pos = 0;
                int path = 0;

                for (int r = 0; r < rows; ++r)
                {
                    int right = plkR() < pr ? 1 : 0;

                    if (mom > 0.0f && plkR() < mom)
                        right = plkDir;

                    plkDir = right;
                    pos += right;
                    path |= right << r;
                }

                int bin = pos + drop;

                if (bin < 0)
                    bin = -bin;

                if (bin > rows)
                    bin = 2 * rows - bin;

                bin = clamp (bin, 0, rows);
                int   idx = rows > 0 ? (bin * (n - 1) + rows / 2) / rows : 0;
                int   nn  = root + int (plk.at (3)) + sqScaleNote (mask, range, idx);
                float vel = clamp (plk.at (11) / 127.0f * (1.0f - plk.at (14) / 100.0f * 0.6f * plkR()), 0.05f, 1.0f);

                if (bin == 0 || bin == rows)
                    vel = min (1.0f, vel * 1.25f);

                plkAddChord (nn, vel, float64 (st) + float64 (b) / float64 (balls), plk.at (8) / 100.0f, ct);
                seqPos <- 2000000 + bin + 16 * rows + 256 * path;
            }
        }
    }

    void bounceStep (int st)
    {
        if (st < bnNext)
            return;

        int   root  = arpHN.at (max (arpN - 1, 0));
        int   mask  = sqScaleMask (int (bnc.at (4) + 0.5f));
        int   range = clamp (int (bnc.at (5) + 0.5f), 12, 48);
        int   n     = sqScaleCount (mask, range);
        int   ct    = int (bnc.at (10) + 0.5f);
        int   cc    = sqChordCount (ct);
        int   nb    = clamp (int (bnc.at (2) + 0.5f), 2, 16);
        int   dir   = int (bnc.at (13) + 0.5f);
        int   stp   = int (bnc.at (3) + (bnc.at (3) < 0.0f ? -0.5f : 0.5f));
        float gap   = bnc.at (0) / 100.0f;
        float dec   = bnc.at (1) / 100.0f;
        float vd    = bnc.at (7) / 100.0f;
        float vel   = bnc.at (11) / 127.0f;
        float64 t   = float64 (st);
        int   idx   = dir == 1 ? n - 1 : 0;
        int   sgn   = dir == 1 ? -1 : 1;

        nb = max (1, min (nb, 32 / cc));

        for (int i = 0; i < nb; ++i)
        {
            if (sqRand01() * 100.0f >= bnc.at (12))
                plkAddChord (root + int (bnc.at (6)) + sqScaleNote (mask, range, idx), vel, t, max (gap * bnc.at (9) / 100.0f, 0.03f), ct);

            t   += float64 (gap);
            gap *= dec;
            vel *= vd;
            idx += stp * sgn;

            if (idx < 0 || idx > n - 1)
            {
                if (dir == 2)
                {
                    sgn = -sgn;
                    idx = clamp (idx < 0 ? -idx : 2 * (n - 1) - idx, 0, n - 1);
                }
                else
                    idx = (idx % n + n) % n;
            }
        }

        bnNext = st + max (1, int (ceil (t - float64 (st)))) + int (bnc.at (8) + 0.5f);
    }

    void cellularStep (int st)
    {
        int ev  = clamp (int (cel.at (10) + 0.5f), 1, 4);
        int w   = clamp (int (cel.at (1) + 0.5f), 4, 16);
        int all = (1 << w) - 1;

        if (st % ev != 0)
            return;

        int root  = arpHN.at (max (arpN - 1, 0));
        int mask  = sqScaleMask (int (cel.at (2) + 0.5f));
        int range = clamp (int (cel.at (3) + 0.5f), 12, 48);
        int n     = sqScaleCount (mask, range);
        int ct    = int (cel.at (11) + 0.5f);
        int rule  = clamp (int (cel.at (0) + 0.5f), 0, 255);
        int maxN  = clamp (int (cel.at (8) + 0.5f), 1, 8);

        if ((celS & all) == 0 || celGen == 0)
            celS = 1 << (w / 2);

        int played = 0;

        for (int c = 0; c < w; ++c)
            if (((celS >> c) & 1) != 0 && played < maxN && sqRand01() * 100.0f >= cel.at (9))
            {
                int idx = w > 1 ? (c * (n - 1) + (w - 1) / 2) / (w - 1) : 0;
                plkAddChord (root + int (cel.at (4)) + sqScaleNote (mask, range, idx), clamp (cel.at (7) / 127.0f, 0.05f, 1.0f), float64 (st), cel.at (6) / 100.0f * float (ev), played == 0 ? ct : 0);
                played++;
            }

        int next = 0;

        for (int c = 0; c < w; ++c)
        {
            int l = (celS >> ((c + w - 1) % w)) & 1;
            int m = (celS >> c) & 1;
            int r = (celS >> ((c + 1) % w)) & 1;
            int bit = (rule >> (l * 4 + m * 2 + r)) & 1;

            if (cel.at (5) > 0.0f && sqRand01() * 100.0f < cel.at (5))
                bit = 1 - bit;

            next |= bit << c;
        }

        celS = next & all;
        celGen++;
    }

'''
rep('    void arpTick (float dt)\n    {\n', ENGINE + '    void arpTick (float dt)\n    {\n')
rep('''                else if (amd == 7)
                    sqMelodic (sn);
                else
                    sqGenerative (sn);''', '''                else if (amd == 7)
                    sqMelodic (sn);
                else if (amd == 8)
                    sqGenerative (sn);
                else if (amd == 9)
                    plinkoStep (sn);
                else if (amd == 10)
                    bounceStep (sn);
                else
                    cellularStep (sn);''')
rep('            gnReg   = 0;       // MOD-SQM\n', '            gnReg   = 0;       // MOD-SQM\n            bnNext  = 0;       // MOD-PLINKO\n            celS    = 0;\n            celGen  = 0;\n')
open(P, 'w').write(src)

# ---- UI table (patch/index.js)
SC = '["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"]'
CH = '["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"]'
UN = {'Shift': 'st', 'Range': 'st', 'Gate': '%', 'Bias': '%', 'Drop X': '%', 'Momentum': '%', 'Rest': '%', 'Vel Spread': '%', 'Start Gap': '%', 'Decay': '%', 'Vel Decay': '%', 'Mutation': '%', 'Pitch Step': '', 'Pause': ''}
rows = ''
for base, nm, lst, arr in GROUPS:
    for k, (n, lo, hi, d) in enumerate(lst):
        if n == 'Scale': t, items = 'sel', SC
        elif n == 'Chord': t, items = 'sel', CH
        elif n == 'Direction': t, items = 'sel', '["Up", "Down", "Ping Pong"]'
        else: t, items = 'knb', 'null'
        rows += '        L.push([%d, "%s %s", %s, %s, %s, "%s", "%s", %s, 1, "%s"]);\n' % (base + k, nm, n, lo, hi, d, UN.get(n, ''), t, items, n)
old = '"Euclid / Poly", "Melodic", "Generative"], 1, "Mode"]);'
assert js.count(old) == 1
js = js.replace(old, '"Euclid / Poly", "Melodic", "Generative", "Plinko", "Bounce", "Cellular"], 1, "Mode"]);').replace('L.push([3921, "Arp Mode",     0, 8, 0,', 'L.push([3921, "Arp Mode",     0, 11, 0,')
anchor = '        L.push([5800, "Melodic Length",'
assert js.count(anchor) == 1
js = js.replace(anchor, '        // MOD-PLINKO\n' + rows + anchor)
open(J, 'w').write(js)
print('applied')
