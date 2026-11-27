#!/usr/bin/env python3
"""Idempotent (marker MOD-HBLM, after build_plinko2.py): two Elektroplankton-style arpeggiator modes.
  Arp Mode 13 "Hanenbow": frogs are launched from a leaf at the bottom and land on up to 8 leaves that are fixed to a plant stem and that you turn.  A frog that lands on a leaf bounces
    off it (a tilted leaf throws it sideways) and every landing plays the note of that leaf.  After `Hits` landings the leaf changes colour (4 states) and its pitch moves by
    `Step` scale degrees.  A frog that comes from below passes through a leaf.  A frog starts at every arpeggiator step (Division / Rate) while fewer than Frogs are alive, from the launch leaf at Spawn X (+- Spread) at the bottom, in the direction Aim (degrees from vertical, positive = to the right).
    Global parameters 6700 + k: Frogs, Speed %, Gravity %, Jump %, Bounce %, Scale, Range, Shift, Gate, Velocity, Chord, Rest, Spawn X, Spread, Hits, Step, Leaf Size, Aim, Stem X.
    Leaves: 6720 + 5 * l + j for l = 0..7, j = On, X (side: below 0.5 = left of the stem, otherwise right; the leaf is fixed to the stem at Stem X), Y (its height), Angle (0..1, 0.5 = horizontal, above = up), Note (scale degree).
  Arp Mode 14 "Luminaria": four walkers on an 8 x 8 grid.  Every `Every` arpeggiator steps each walker moves one cell; a cell holds an arrow (up, right, down, left) or nothing.
    When a walker lands on an arrow it turns that way and plays a note (the pitch follows the column, the row or both); with Rotate the arrow turns clockwise after each visit.
    Global parameters 6760 + k: Every, Scale, Range, Shift, Gate, Velocity, Chord, Rest, Rotate, Pitch By, Wrap.
    Walkers: 6780 + 5 * w + j for w = 0..3, j = On, X (0..7), Y (0..7), Direction (1 up, 2 right, 3 down, 4 left), Octave (-2..2).
    Grid: 6800 + 8 * y + x = 0 nothing, 1..4 arrow.
  Output event seqPos (shared with the sequencer playhead and the Plinko board): 3000000 + leaf = a landing, 4000000 + (frog << 21 | x << 11 | y) = a frog position (every 33 ms),
    30000000 + 100 * walker + cell = a walker moved, 30100000 + 8 * cell + arrow = an arrow was turned, 30200000 + 8 * leaf + state = a leaf changed colour.
All parameters are `automatable: false`."""
import os, sys
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); J = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); js = open(J).read()
if 'MOD-HBLM' in src:
    print('already applied'); sys.exit(0)
assert 'MOD-PLKP' in src, 'run build_plinko2.py first'
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:80], src.count(old))
    src = src.replace(old, new)

rep('"Arp Mode", min: 0.0, max: 12.0,', '"Arp Mode", min: 0.0, max: 14.0,')
HG = [('Frogs', 1, 8, 3), ('Speed', 25, 300, 100), ('Gravity', 20, 300, 100), ('Jump', 40, 200, 120), ('Bounce', 20, 110, 60), ('Scale', 0, 11, 8), ('Range', 12, 48, 24), ('Shift', -24, 24, 0),
      ('Gate', 10, 400, 60), ('Velocity', 1, 127, 100), ('Chord', 0, 8, 0), ('Rest', 0, 100, 0), ('Spawn X', 0, 100, 7), ('Spread', 0, 100, 5), ('Hits', 1, 8, 2), ('Step', -4, 4, 2), ('Leaf Size', 8, 50, 27), ('Aim', -80, 80, 30), ('Stem X', 0, 100, 64)]
LG = [('Every', 1, 8, 1), ('Scale', 0, 11, 8), ('Range', 12, 48, 24), ('Shift', -24, 24, 0), ('Gate', 10, 400, 70), ('Velocity', 1, 127, 100), ('Chord', 0, 8, 0), ('Rest', 0, 100, 0),
      ('Rotate', 0, 1, 0), ('Pitch By', 0, 2, 0), ('Wrap', 0, 1, 1)]
# leaves: on, x, y, angle, note
# a plant: the leaves are fixed to the stem (X = side, 0 left / 1 right) at their height and only turn; angle 0.5 = horizontal, above = up (three pairs as in the toy, a fourth pair is off)
LEAVES = [[1, 0.0, 0.69, 0.725, 0], [1, 1.0, 0.69, 0.725, 2], [1, 0.0, 0.50, 0.73, 4], [1, 1.0, 0.50, 0.73, 5], [1, 0.0, 0.33, 0.84, 7], [1, 1.0, 0.33, 0.84, 9],
          [0, 0.0, 0.20, 0.85, 3], [0, 1.0, 0.20, 0.85, 6]]
LNAMES = ['On', 'X', 'Y', 'Angle', 'Note']; LHI = {0: 1, 1: 1, 2: 1, 3: 1, 4: 24}
WALK = [[1, 1, 1, 2, 0], [1, 3, 3, 2, 1], [1, 6, 6, 4, 0], [1, 5, 5, 4, -1]]
WNAMES = ['On', 'X', 'Y', 'Direction', 'Octave']; WLO = {0: 0, 1: 0, 2: 0, 3: 1, 4: -2}; WHI = {0: 1, 1: 7, 2: 7, 3: 4, 4: 2}
GRID = [0] * 64
for (x, y, d) in [(1, 1, 2), (6, 1, 3), (6, 6, 4), (1, 6, 1), (3, 3, 2), (5, 3, 3), (5, 5, 4), (3, 5, 1)]: GRID[y * 8 + x] = d

def num(v): return repr(float(v))
decl = ''; ev = ''; ini = ''
for k, (n, lo, hi, d) in enumerate(HG):
    decl += '    input event float param%d [[ name: "Hanenbow %s", min: %s, max: %s, init: %s, step: 1.0, automatable: false ]];   // MOD-HBLM\n' % (6700 + k, n, num(lo), num(hi), num(d))
    ev += '    event param%d (float v) { hnbG.at (%d) = v; }   // MOD-HBLM\n' % (6700 + k, k)
    ini += '        hnbG.at (%d) = %sf;\n' % (k, num(d))
for l in range(8):
    for j in range(5):
        d = LEAVES[l][j]
        decl += '    input event float param%d [[ name: "Hanenbow Leaf %d %s", min: 0.0, max: %s, init: %s, automatable: false ]];   // MOD-HBLM\n' % (6720 + 5 * l + j, l + 1, LNAMES[j], num(LHI[j]), num(d))
        ev += '    event param%d (float v) { hnbL.at (%d) = v; }\n' % (6720 + 5 * l + j, 5 * l + j)
        if d != 0: ini += '        hnbL.at (%d) = %sf;\n' % (5 * l + j, num(d))
for k, (n, lo, hi, d) in enumerate(LG):
    decl += '    input event float param%d [[ name: "Luminaria %s", min: %s, max: %s, init: %s, step: 1.0, automatable: false ]];   // MOD-HBLM\n' % (6760 + k, n, num(lo), num(hi), num(d))
    ev += '    event param%d (float v) { lmg.at (%d) = v; }   // MOD-HBLM\n' % (6760 + k, k)
    ini += '        lmg.at (%d) = %sf;\n' % (k, num(d))
for w in range(4):
    for j in range(5):
        d = WALK[w][j]
        decl += '    input event float param%d [[ name: "Luminaria Walker %d %s", min: %s, max: %s, init: %s, step: 1.0, automatable: false ]];   // MOD-HBLM\n' % (6780 + 5 * w + j, w + 1, WNAMES[j], num(WLO[j]), num(WHI[j]), num(d))
        extra = ''
        if j == 1: extra = ' lmX.at (%d) = clamp (int (v + 0.5f), 0, 7);' % w
        if j == 2: extra = ' lmY.at (%d) = clamp (int (v + 0.5f), 0, 7);' % w
        if j == 3: extra = ' lmD.at (%d) = clamp (int (v + 0.5f), 1, 4);' % w
        ev += '    event param%d (float v) { lmW.at (%d) = v;%s }\n' % (6780 + 5 * w + j, 5 * w + j, extra)
        if d != 0: ini += '        lmW.at (%d) = %sf;\n' % (5 * w + j, num(d))
    ini += '        lmX.at (%d) = %d;\n        lmY.at (%d) = %d;\n        lmD.at (%d) = %d;\n' % (w, WALK[w][1], w, WALK[w][2], w, WALK[w][3])
for c in range(64):
    decl += '    input event float param%d [[ name: "Luminaria Cell %d", min: 0.0, max: 4.0, init: %s, step: 1.0, automatable: false ]];   // MOD-HBLM\n' % (6800 + c, c + 1, num(GRID[c]))
    ev += '    event param%d (float v) { lmGrid.at (%d) = v; lmRt.at (%d) = clamp (int (v + 0.5f), 0, 4); }\n' % (6800 + c, c, c)
    if GRID[c]: ini += '        lmGrid.at (%d) = %sf;\n        lmRt.at (%d) = %d;\n' % (c, num(GRID[c]), c, GRID[c])
a = '    input event float param3929 '
i = src.index(a); j = src.index('\n', i) + 1
src = src[:j] + decl + src[j:]
rep('    event param3920 (float v) { arpOn = v; }', ev + '    event param3920 (float v) { arpOn = v; }')
rep('        // MOD-SQM defaults\n', '        // MOD-SQM defaults\n' + ini)

st = '''    // ---------------- MOD-HBLM: Hanenbow (frogs and leaves) and Luminaria (walkers on a grid) ----------------
    float[20]   hnbG;                 // Hanenbow globals (6700 + k)
    float[40]   hnbL;                 // leaves: 8 x (on, x, y, angle, note)
    float[8]    hnbEx;                // half length of the leaf as a vector (from the angle), recomputed every physics step
    float[8]    hnbEy;
    float[8]    hnbX;                 // frogs
    float[8]    hnbY;
    float[8]    hnbVX;
    float[8]    hnbVY;
    float[8]    hnbCd;
    float[8]    hnbAge;
    float[8]    hnbRest;              // time a frog has hardly moved (stuck on a leaf)
    int[8]      hnbOn;
    int[8]      hnbCnt;               // landings on a leaf since its last colour change
    int[8]      hnbSt;                // colour (0..3) of a leaf
    float       hnbAcc = 0.0f;
    float       hnbViz = 0.0f;
    float[16]   lmg;                  // Luminaria globals (6760 + k)
    float[20]   lmW;                  // walkers: 4 x (on, x, y, dir, octave)
    float[64]   lmGrid;               // the arrows as set by the parameters
    int[64]     lmRt;                 // the arrows while playing (Rotate turns them)
    int[4]      lmX;
    int[4]      lmY;
    int[4]      lmD;
    int         lmDiv = 0;
'''
rep('    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n', st + '    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n')

ENGINE = r'''    // ---- MOD-HBLM ----
    void hnbClear()
    {
        for (int i = 0; i < 8; ++i)
        {
            hnbOn.at (i)  = 0;
            hnbCnt.at (i) = 0;
            hnbSt.at (i)  = 0;
        }

        hnbAcc = 0.0f;
    }

    void lumClear()
    {
        for (int w = 0; w < 4; ++w)
        {
            lmX.at (w) = clamp (int (lmW.at (5 * w + 1) + 0.5f), 0, 7);
            lmY.at (w) = clamp (int (lmW.at (5 * w + 2) + 0.5f), 0, 7);
            lmD.at (w) = clamp (int (lmW.at (5 * w + 3) + 0.5f), 1, 4);
        }

        for (int c = 0; c < 64; ++c)
            lmRt.at (c) = clamp (int (lmGrid.at (c) + 0.5f), 0, 4);

        lmDiv = 0;
    }

    void hnbSpawn()
    {
        int maxB  = clamp (int (hnbG.at (0) + 0.5f), 1, 8);
        int alive = 0;
        int free  = -1;

        for (int i = 0; i < 8; ++i)
        {
            if (hnbOn.at (i) != 0)
                alive++;
            else if (free < 0)
                free = i;
        }

        if (free < 0 || alive >= maxB)
            return;

        float jump = hnbG.at (3) / 100.0f;
        float gr   = max (hnbG.at (2) / 100.0f, 0.2f);

        hnbX.at (free)   = clamp (hnbG.at (12) / 100.0f + (sqRand01() - 0.5f) * hnbG.at (13) / 100.0f, 0.03f, 0.97f);
        hnbY.at (free)   = 0.93f;      // under the water, at the launch leaf
        float aim = hnbG.at (17) * 0.0174533f + (sqRand01() - 0.5f) * 0.05f;
        float spd = (1.1f + (sqRand01() - 0.5f) * 0.15f) * jump * sqrt (gr);
        hnbVX.at (free)  = spd * sin (aim);
        hnbVY.at (free)  = -spd * cos (aim);
        hnbCd.at (free)  = 0.0f;
        hnbAge.at (free) = 0.0f;
        hnbRest.at (free) = 0.0f;
        hnbOn.at (free)  = 1;
    }

    void hnbHit (int l, float speed, float64 now)
    {
        if (sqRand01() * 100.0f >= hnbG.at (11))
        {
            int   root  = arpHN.at (max (arpN - 1, 0));
            int   mask  = sqScaleMask (int (hnbG.at (5) + 0.5f));
            int   range = clamp (int (hnbG.at (6) + 0.5f), 12, 48);
            int   n     = sqScaleCount (mask, range);
            int   deg   = int (hnbL.at (5 * l + 4) + 0.5f) + hnbSt.at (l) * int (hnbG.at (15));
            deg = ((deg % n) + n) % n;
            int   nn    = root + int (hnbG.at (7)) + sqScaleNote (mask, range, deg);
            float vel   = clamp (hnbG.at (9) / 127.0f * (0.35f + 0.9f * min (speed, 1.2f)), 0.05f, 1.0f);

            plkAddChord (nn, vel, now, hnbG.at (8) / 100.0f, int (hnbG.at (10) + 0.5f));
        }

        seqPos <- 3000000 + l;
        hnbCnt.at (l) = hnbCnt.at (l) + 1;

        if (hnbCnt.at (l) >= int (hnbG.at (14) + 0.5f))
        {
            hnbCnt.at (l) = 0;
            hnbSt.at (l)  = (hnbSt.at (l) + 1) % 4;
            seqPos <- 30200000 + l * 8 + hnbSt.at (l);
        }
    }

    void hnbStep (float h, float64 now)
    {
        float grav = 0.9f * hnbG.at (2) / 100.0f;
        float e0   = clamp (hnbG.at (4) / 100.0f, 0.1f, 1.1f);
        float hl   = clamp (hnbG.at (16) / 100.0f, 0.06f, 0.5f) * 0.5f;
        float r    = 0.012f;

        for (int l = 0; l < 8; ++l)
        {
            float el = (hnbL.at (5 * l + 3) - 0.5f) * 2.4f;                // elevation of the leaf: 0.5 = horizontal, above 0.5 = up
            float sd = hnbL.at (5 * l + 1) < 0.5f ? -1.0f : 1.0f;          // left or right of the stem (X of the leaf is its side)
            hnbEx.at (l) = sd * cos (el) * hl;
            hnbEy.at (l) = -sin (el) * hl;
        }

        for (int b = 0; b < 8; ++b)
            if (hnbOn.at (b) != 0)
            {
                float x  = hnbX.at (b);
                float y  = hnbY.at (b);
                float vx = hnbVX.at (b);
                float vy = hnbVY.at (b) + grav * h;
                float cd = hnbCd.at (b) - h;

                x += vx * h;
                y += vy * h;

                if (x < r)        { x = r;        vx = abs (vx) * e0; }
                if (x > 1.0f - r) { x = 1.0f - r; vx = -abs (vx) * e0; }
                if (y < r)        { y = r;        vy = abs (vy) * e0; }

                for (int l = 0; l < 8; ++l)
                {
                    if (hnbL.at (5 * l) < 0.5f)
                        continue;

                    float ex = hnbEx.at (l);
                    float ey = hnbEy.at (l);
                    float x1 = hnbG.at (18) / 100.0f;   // the leaf is fixed to the stem here and turns around this point
                    float y1 = hnbL.at (5 * l + 2);
                    float sx = 2.0f * ex;
                    float sy = 2.0f * ey;
                    float l2 = sx * sx + sy * sy;
                    float t  = clamp (((x - x1) * sx + (y - y1) * sy) / max (l2, 0.000001f), 0.0f, 1.0f);
                    float dx = x - (x1 + t * sx);
                    float dy = y - (y1 + t * sy);
                    float re = r + 0.006f;
                    float d2 = dx * dx + dy * dy;

                    if (d2 < re * re)
                    {
                        float d  = sqrt (d2);
                        float nx = d > 0.00001f ? dx / d : 0.0f;
                        float ny = d > 0.00001f ? dy / d : -1.0f;

                        if (ny < -0.15f)   // only from above: a frog coming from below passes the leaf
                        {
                            x += nx * (re - d);
                            y += ny * (re - d);
                            float vn = vx * nx + vy * ny;

                            if (vn < 0.0f)
                            {
                                vx -= (1.0f + e0) * vn * nx;
                                vy -= (1.0f + e0) * vn * ny;

                                if (-vn > 0.08f && cd <= 0.0f)
                                {
                                    hnbHit (l, -vn, now);
                                    cd = 0.06f;
                                }
                            }
                        }
                    }
                }

                hnbX.at (b)   = x;
                hnbY.at (b)   = y;
                hnbVX.at (b)  = clamp (vx, -3.0f, 3.0f);
                hnbVY.at (b)  = clamp (vy, -3.0f, 3.0f);
                hnbCd.at (b)  = cd;
                hnbAge.at (b) = hnbAge.at (b) + h;

                // a frog that hardly moves (stuck in the angle between leaf and stem) gets a push now and then
                if (abs (vx) + abs (vy) < 0.12f && y < 0.8f)
                    hnbRest.at (b) = hnbRest.at (b) + h;
                else
                    hnbRest.at (b) = 0.0f;

                if (hnbRest.at (b) > 1.0f)
                {
                    hnbRest.at (b) = 0.0f;
                    hnbVX.at (b)   = (sqRand01() - 0.5f) * 1.2f;
                    hnbVY.at (b)   = -0.5f;
                }

                // a frog only disappears when it has fallen into the water (surface at 0.82)
                if ((y > 0.86f && vy > 0.0f) || hnbAge.at (b) > 30.0f)
                    hnbOn.at (b) = 0;
            }
    }

    void hnbPhys (float dt, float64 now)
    {
        hnbAcc += dt * hnbG.at (1) / 100.0f;

        while (hnbAcc >= 0.0025f)   // 400 Hz
        {
            hnbAcc -= 0.0025f;
            hnbStep (0.0025f, now);
        }

        hnbViz += dt;

        if (hnbViz >= 0.033f)
        {
            hnbViz = 0.0f;

            for (int b = 0; b < 8; ++b)
                if (hnbOn.at (b) != 0)
                    seqPos <- 4000000 + ((b << 21) | (clamp (int (hnbX.at (b) * 1023.0f), 0, 1023) << 11) | clamp (int (hnbY.at (b) * 1023.0f), 0, 1023));
        }
    }

    void lumStep (int st)
    {
        int every = clamp (int (lmg.at (0) + 0.5f), 1, 8);
        lmDiv++;

        if (lmDiv < every)
            return;

        lmDiv = 0;

        int   root  = arpHN.at (max (arpN - 1, 0));
        int   mask  = sqScaleMask (int (lmg.at (1) + 0.5f));
        int   range = clamp (int (lmg.at (2) + 0.5f), 12, 48);
        int   n     = sqScaleCount (mask, range);
        int   pby   = int (lmg.at (9) + 0.5f);
        bool  wrap  = lmg.at (10) > 0.5f;

        for (int w = 0; w < 4; ++w)
        {
            if (lmW.at (5 * w) < 0.5f)
                continue;

            int x = lmX.at (w);
            int y = lmY.at (w);
            int d = lmD.at (w);
            int nx = x + (d == 2 ? 1 : (d == 4 ? -1 : 0));
            int ny = y + (d == 3 ? 1 : (d == 1 ? -1 : 0));

            if (nx < 0 || nx > 7 || ny < 0 || ny > 7)
            {
                if (wrap)
                {
                    nx = (nx + 8) % 8;
                    ny = (ny + 8) % 8;
                }
                else   // the wall: turn round on the spot
                {
                    d  = d == 1 ? 3 : (d == 3 ? 1 : (d == 2 ? 4 : 2));
                    nx = x;
                    ny = y;
                }
            }

            x = nx;
            y = ny;

            int cell = y * 8 + x;
            int ar   = lmRt.at (cell);

            if (ar > 0)
            {
                d = ar;

                if (sqRand01() * 100.0f >= lmg.at (7))
                {
                    int idx = pby == 0 ? x * (n - 1) / 7 : (pby == 1 ? (7 - y) * (n - 1) / 7 : (x + 7 - y) * (n - 1) / 14);
                    int nn  = root + int (lmg.at (3)) + sqScaleNote (mask, range, clamp (idx, 0, n - 1)) + 12 * int (lmW.at (5 * w + 4));
                    float va  = pby == 1 ? float (x) : float (7 - y);
                    float vel = clamp (lmg.at (5) / 127.0f * (0.65f + 0.35f * va / 7.0f), 0.05f, 1.0f);

                    plkAddChord (nn, vel, float64 (st), lmg.at (4) / 100.0f, int (lmg.at (6) + 0.5f));
                }

                if (lmg.at (8) > 0.5f)
                {
                    lmRt.at (cell) = ar % 4 + 1;
                    seqPos <- 30100000 + cell * 8 + lmRt.at (cell);
                }
            }

            lmX.at (w) = x;
            lmY.at (w) = y;
            lmD.at (w) = d;
            seqPos <- 30000000 + w * 100 + cell;
        }
    }

'''
rep('    void arpTick (float dt)\n    {\n', ENGINE + '    void arpTick (float dt)\n    {\n')
rep('''                else
                    plkSpawn();''', '''                else if (amd == 12)
                    plkSpawn();
                else if (amd == 13)
                    hnbSpawn();
                else
                    lumStep (sn);''')
rep('            if (amd == 12)   // MOD-PLKP\n                plkPhys (dt, float64 (arpStep - 1) + float64 (arpPh));\n',
    '            if (amd == 12)   // MOD-PLKP\n                plkPhys (dt, float64 (arpStep - 1) + float64 (arpPh));\n            else if (amd == 13)   // MOD-HBLM\n                hnbPhys (dt, float64 (arpStep - 1) + float64 (arpPh));\n')
rep('            plkClear();        // MOD-PLKP\n', '            plkClear();        // MOD-PLKP\n            hnbClear();        // MOD-HBLM\n\n            if (amd == 14)\n                lumClear();\n\n')
open(P, 'w').write(src)

# ---- UI table
SC = '["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"]'
CH = '["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"]'
OO = '["Off", "On"]'; PB = '["Column", "Row", "Both"]'
UN = {'Shift': 'st', 'Range': 'st', 'Gate': '%', 'Speed': '%', 'Gravity': '%', 'Jump': '%', 'Bounce': '%', 'Rest': '%', 'Spawn X': '%', 'Spread': '%', 'Leaf Size': '%', 'Aim': 'deg'}
def kind(n):
    return ('sel', SC) if n == 'Scale' else ('sel', CH) if n == 'Chord' else ('sel', OO) if n in ('Rotate', 'Wrap') else ('sel', PB) if n == 'Pitch By' else ('knb', 'null')
rows = ''
for k, (n, lo, hi, d) in enumerate(HG):
    t, items = kind(n)
    rows += '        L.push([%d, "Hanenbow %s", %s, %s, %s, "%s", "%s", %s, 1, "%s"]);\n' % (6700 + k, n, lo, hi, d, UN.get(n, ''), t, items, n)
for l in range(8):
    for j in range(5):
        rows += '        L.push([%d, "Hanenbow Leaf %d %s", 0, %s, %s, "", "knb", null, 1, "%s"]);\n' % (6720 + 5 * l + j, l + 1, LNAMES[j], LHI[j], LEAVES[l][j], LNAMES[j])
for k, (n, lo, hi, d) in enumerate(LG):
    t, items = kind(n)
    rows += '        L.push([%d, "Luminaria %s", %s, %s, %s, "%s", "%s", %s, 1, "%s"]);\n' % (6760 + k, n, lo, hi, d, UN.get(n, ''), t, items, n)
for w in range(4):
    for j in range(5):
        rows += '        L.push([%d, "Luminaria Walker %d %s", %s, %s, %s, "", "knb", null, 1, "%s"]);\n' % (6780 + 5 * w + j, w + 1, WNAMES[j], WLO[j], WHI[j], WALK[w][j], WNAMES[j])
for c in range(64):
    rows += '        L.push([%d, "Luminaria Cell %d", 0, 4, %s, "", "knb", null, 1, "Cell"]);\n' % (6800 + c, c + 1, GRID[c])
assert js.count('"Cellular", "Plinko"], 1, "Mode"]);') == 1
js = js.replace('"Cellular", "Plinko"], 1, "Mode"]);', '"Cellular", "Plinko", "Hanenbow", "Luminaria"], 1, "Mode"]);').replace('L.push([3921, "Arp Mode",     0, 12, 0,', 'L.push([3921, "Arp Mode",     0, 14, 0,')
anchor = '        L.push([5800, "Melodic Length",'
assert js.count(anchor) == 1
js = js.replace(anchor, '        // MOD-HBLM\n' + rows + anchor)
open(J, 'w').write(js)
print('applied')
