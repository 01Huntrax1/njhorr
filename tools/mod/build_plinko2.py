#!/usr/bin/env python3
"""Idempotent (marker MOD-PLKP, after build_plinko.py): Arp Mode 12 "Plinko", a physics board.  Balls fall under gravity through a board that you draw: up to 48
obstacles (pegs and lines).  Every time a ball hits an obstacle a note plays: the pitch is the scale degree of the x position of the hit (Scale, Range, Shift), the
velocity follows the impact speed.  Obstacle kinds: 0 normal, 1 Spring (bounces harder), 2 Shimmer (adds the octave), 3 Chorus (adds a fifth and a detuned double a
little later), 4 Gate (the ball keeps going but the note is a staccato 1/4 step).  The root is the last key pressed.
  Global parameters 6360 + k: Balls (max alive), Speed %, Bounce %, Sway, Gravity %, Scale, Range, Shift, Gate, Velocity, Chord, Rest, Drop X, Spread, Size.
  The board: 6400 + 6 * e + j for e = 0..47, j = type (0 none, 1 peg, 2 line), x1, y1, x2, y2 (0..1, y down), kind.
  A ball is dropped at every arpeggiator step (Division / Rate) while fewer than Balls are alive; the physics runs at 400 Hz with Speed as time scale.
  Output event seqPos (shared with the sequencer playhead): 3000000 + obstacle = a hit; 4000000 + (ball << 21 | x << 11 | y) with x, y in 0..1023 = a ball position (every 33 ms).
All parameters are `automatable: false`."""
import os, sys
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); J = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); js = open(J).read()
if 'MOD-PLKP' in src:
    print('already applied'); sys.exit(0)
assert 'MOD-PLINKO' in src, 'run build_plinko.py first'
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:80], src.count(old))
    src = src.replace(old, new)

rep('"Arp Mode", min: 0.0, max: 11.0,', '"Arp Mode", min: 0.0, max: 12.0,')
G = [('Balls', 1, 8, 3), ('Speed', 25, 300, 100), ('Bounce', 20, 110, 75), ('Sway', 0, 100, 0), ('Gravity', 20, 300, 100), ('Scale', 0, 11, 9), ('Range', 12, 48, 24), ('Shift', -24, 24, 0),
     ('Gate', 10, 400, 60), ('Velocity', 1, 127, 100), ('Chord', 0, 8, 0), ('Rest', 0, 100, 0), ('Drop X', 0, 100, 50), ('Spread', 0, 100, 20), ('Size', 5, 30, 12)]
NE = 48
# a first board: a funnel of pegs, so a fresh instance already makes music
def default_board():
    b = [[0, 0, 0, 0, 0, 0] for _ in range(NE)]
    k = 0
    for r in range(5):
        for c in range(r + 3):
            if k < NE:
                b[k] = [1, 0.5 + (c - (r + 2) / 2.0) * 0.14, 0.22 + r * 0.12, 0.5 + (c - (r + 2) / 2.0) * 0.14, 0.22 + r * 0.12, 0]; k += 1
    return b
BOARD = default_board()
decl = ''; ev = ''; ini = ''
for k, (n, lo, hi, d) in enumerate(G):
    decl += '    input event float param%d [[ name: "Plinko %s", min: %s, max: %s, init: %s, step: 1.0, automatable: false ]];   // MOD-PLKP\n' % (6360 + k, n, float(lo), float(hi), float(d))
    ev += '    event param%d (float v) { plg.at (%d) = v; }   // MOD-PLKP\n' % (6360 + k, k)
    ini += '        plg.at (%d) = %sf;\n' % (k, float(d))
NAMES = ['Type', 'X1', 'Y1', 'X2', 'Y2', 'Kind']
for e in range(NE):
    for j in range(6):
        hi = {0: 2, 5: 4}.get(j, 1)
        d = BOARD[e][j]
        decl += '    input event float param%d [[ name: "Plinko Obstacle %d %s", min: 0.0, max: %s, init: %s, automatable: false ]];   // MOD-PLKP\n' % (6400 + 6 * e + j, e + 1, NAMES[j], float(hi), float(d))
        ev += '    event param%d (float v) { plkB.at (%d) = v; }\n' % (6400 + 6 * e + j, 6 * e + j)
        if d != 0: ini += '        plkB.at (%d) = %sf;\n' % (6 * e + j, repr(round(float(d), 4)))
a = '    input event float param3929 '
i = src.index(a); j = src.index('\n', i) + 1
src = src[:j] + decl + src[j:]
rep('    event param3920 (float v) { arpOn = v; }', ev + '    event param3920 (float v) { arpOn = v; }')
rep('        // MOD-SQM defaults\n', '        // MOD-SQM defaults\n' + ini)

st = '''    // ---------------- MOD-PLKP: Plinko physics board ----------------
    float[16]   plg;                  // global parameters (6360 + k)
    float[288]  plkB;                 // the board: 48 obstacles x (type, x1, y1, x2, y2, kind)
    float[8]    pbX;                  // balls: position, speed, cooldown of the next trigger, alive flag
    float[8]    pbY;
    float[8]    pbVX;
    float[8]    pbVY;
    float[8]    pbCd;
    int[8]      pbOn;
    float       plkAcc = 0.0f;        // time not yet simulated (s)
    float       plkTime = 0.0f;       // simulated time (s), for the sway
    float       plkViz = 0.0f;        // time since the last position report
'''
rep('    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n', st + '    int         seqRepVoice = 0;   // MOD-SEQPOS: voice reported for sequencers with Retrig\n')

ENGINE = r'''    // ---- MOD-PLKP ----
    void plkClear()
    {
        for (int i = 0; i < 8; ++i)
            pbOn.at (i) = 0;

        plkAcc = 0.0f;
    }

    void plkSpawn()
    {
        int maxB = clamp (int (plg.at (0) + 0.5f), 1, 8);
        int alive = 0;
        int free = -1;

        for (int i = 0; i < 8; ++i)
        {
            if (pbOn.at (i) != 0)
                alive++;
            else if (free < 0)
                free = i;
        }

        if (free < 0 || alive >= maxB)
            return;

        pbX.at (free)  = clamp (plg.at (12) / 100.0f + (sqRand01() - 0.5f) * plg.at (13) / 100.0f, 0.03f, 0.97f);
        pbY.at (free)  = 0.02f;
        pbVX.at (free) = (sqRand01() - 0.5f) * 0.04f;
        pbVY.at (free) = 0.0f;
        pbCd.at (free) = 0.0f;
        pbOn.at (free) = 1;
    }

    void plkHit (int e, int b, float cx, float speed, float64 now)
    {
        if (sqRand01() * 100.0f < plg.at (11))
            return;

        int   root  = arpHN.at (max (arpN - 1, 0));
        int   mask  = sqScaleMask (int (plg.at (5) + 0.5f));
        int   range = clamp (int (plg.at (6) + 0.5f), 12, 48);
        int   n     = sqScaleCount (mask, range);
        int   kind  = int (plkB.at (6 * e + 5) + 0.5f);
        int   idx   = clamp (int (clamp (cx, 0.0f, 1.0f) * float (n - 1) + 0.5f), 0, n - 1);
        int   nn    = root + int (plg.at (7)) + sqScaleNote (mask, range, idx);
        float vel   = clamp (plg.at (9) / 127.0f * (0.35f + 0.9f * min (speed, 1.2f)), 0.05f, 1.0f);
        float len   = kind == 4 ? 0.25f : plg.at (8) / 100.0f;

        plkAddChord (nn, vel, now, len, int (plg.at (10) + 0.5f));

        if (kind == 2)
            evAdd (nn + 12, vel * 0.8f, now, len);
        else if (kind == 3)
        {
            evAdd (nn + 7, vel * 0.7f, now, len);
            evAdd (nn, vel * 0.5f, now + 0.12, len);
        }

        seqPos <- 3000000 + e;
    }

    void plkStep (float h, float64 now)
    {
        float grav = 0.9f * plg.at (4) / 100.0f;
        float e0   = clamp (plg.at (2) / 100.0f, 0.1f, 1.1f);
        float r    = clamp (plg.at (14) / 1000.0f, 0.004f, 0.03f);
        float sway = plg.at (3) / 100.0f;

        plkTime += h;

        for (int b = 0; b < 8; ++b)
            if (pbOn.at (b) != 0)
            {
                float x  = pbX.at (b);
                float y  = pbY.at (b);
                float vx = pbVX.at (b) + sway * 0.6f * sin (plkTime * 4.4f + float (b) * 1.7f) * h;
                float vy = pbVY.at (b) + grav * h;
                float cd = pbCd.at (b) - h;

                x += vx * h;
                y += vy * h;

                if (x < r)      { x = r;       vx = abs (vx) * e0; }
                if (x > 1.0f - r) { x = 1.0f - r; vx = -abs (vx) * e0; }
                if (y < r)      { y = r;       vy = abs (vy) * e0; }

                for (int e = 0; e < 48; ++e)
                {
                    int ty = int (plkB.at (6 * e) + 0.5f);

                    if (ty == 0)
                        continue;

                    float x1 = plkB.at (6 * e + 1);
                    float y1 = plkB.at (6 * e + 2);
                    float ex = ty == 1 ? 0.0f : plkB.at (6 * e + 3) - x1;
                    float ey = ty == 1 ? 0.0f : plkB.at (6 * e + 4) - y1;
                    float l2 = ex * ex + ey * ey;
                    float t  = l2 > 0.000001f ? clamp (((x - x1) * ex + (y - y1) * ey) / l2, 0.0f, 1.0f) : 0.0f;
                    float px = x1 + t * ex;
                    float py = y1 + t * ey;
                    float dx = x - px;
                    float dy = y - py;
                    float re = r + (ty == 1 ? 0.008f : 0.004f);
                    float d2 = dx * dx + dy * dy;

                    if (d2 < re * re)
                    {
                        float d  = sqrt (d2);
                        float nx = d > 0.00001f ? dx / d : 0.0f;
                        float ny = d > 0.00001f ? dy / d : -1.0f;
                        x += nx * (re - d);
                        y += ny * (re - d);
                        float vn = vx * nx + vy * ny;

                        if (vn < 0.0f)
                        {
                            int   kind = int (plkB.at (6 * e + 5) + 0.5f);
                            float eb   = kind == 1 ? min (e0 * 1.4f + 0.15f, 1.25f) : e0;
                            vx -= (1.0f + eb) * vn * nx;
                            vy -= (1.0f + eb) * vn * ny;

                            if (-vn > 0.1f && cd <= 0.0f)
                            {
                                plkHit (e, b, px, -vn, now);
                                cd = 0.06f;
                            }
                        }
                    }
                }

                pbX.at (b)  = x;
                pbY.at (b)  = y;
                pbVX.at (b) = clamp (vx, -3.0f, 3.0f);
                pbVY.at (b) = clamp (vy, -3.0f, 3.0f);
                pbCd.at (b) = cd;

                if (y > 1.05f)
                    pbOn.at (b) = 0;
            }
    }

    void plkPhys (float dt, float64 now)
    {
        plkAcc += dt * plg.at (1) / 100.0f;

        while (plkAcc >= 0.0025f)   // 400 Hz
        {
            plkAcc -= 0.0025f;
            plkStep (0.0025f, now);
        }

        plkViz += dt;

        if (plkViz >= 0.033f)
        {
            plkViz = 0.0f;

            for (int b = 0; b < 8; ++b)
                if (pbOn.at (b) != 0)
                    seqPos <- 4000000 + ((b << 21) | (clamp (int (pbX.at (b) * 1023.0f), 0, 1023) << 11) | clamp (int (pbY.at (b) * 1023.0f), 0, 1023));
        }
    }

'''
rep('    void arpTick (float dt)\n    {\n', ENGINE + '    void arpTick (float dt)\n    {\n')
rep('''                else if (amd == 9)
                    plinkoStep (sn);
                else if (amd == 10)
                    bounceStep (sn);
                else
                    cellularStep (sn);''', '''                else if (amd == 9)
                    plinkoStep (sn);
                else if (amd == 10)
                    bounceStep (sn);
                else if (amd == 11)
                    cellularStep (sn);
                else
                    plkSpawn();''')
rep('            sqTick (float64 (arpStep - 1) + float64 (arpPh));\n            return;', '            if (amd == 12)   // MOD-PLKP\n                plkPhys (dt, float64 (arpStep - 1) + float64 (arpPh));\n\n            sqTick (float64 (arpStep - 1) + float64 (arpPh));\n            return;')
rep('            bnNext  = 0;       // MOD-PLINKO\n', '            bnNext  = 0;       // MOD-PLINKO\n            plkClear();        // MOD-PLKP\n')
open(P, 'w').write(src)

# ---- UI table
SC = '["Chromatic", "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Harm. Minor", "Pent. Major", "Pent. Minor", "Blues", "Whole Tone"]'
CH = '["None", "Octave", "Fifth", "Major", "Minor", "Sus4", "Maj7", "Min7", "Dim"]'
UN = {'Shift': 'st', 'Range': 'st', 'Gate': '%', 'Speed': '%', 'Bounce': '%', 'Sway': '%', 'Gravity': '%', 'Rest': '%', 'Drop X': '%', 'Spread': '%'}
rows = ''
for k, (n, lo, hi, d) in enumerate(G):
    t, items = ('sel', SC) if n == 'Scale' else ('sel', CH) if n == 'Chord' else ('knb', 'null')
    rows += '        L.push([%d, "Plinko %s", %s, %s, %s, "%s", "%s", %s, 1, "%s"]);\n' % (6360 + k, n, lo, hi, d, UN.get(n, ''), t, items, n)
for e in range(NE):
    for j in range(6):
        hi = {0: 2, 5: 4}.get(j, 1)
        rows += '        L.push([%d, "Plinko Obstacle %d %s", 0, %s, %s, "", "knb", null, 1, "%s"]);\n' % (6400 + 6 * e + j, e + 1, NAMES[j], hi, BOARD[e][j], NAMES[j])
js = js.replace('"Plinko", "Bounce", "Cellular"], 1, "Mode"]);', '"Galton", "Bounce", "Cellular", "Plinko"], 1, "Mode"]);').replace('L.push([3921, "Arp Mode",     0, 11, 0,', 'L.push([3921, "Arp Mode",     0, 12, 0,')
anchor = '        L.push([5800, "Melodic Length",'
assert js.count(anchor) == 1
js = js.replace(anchor, '        // MOD-PLKP\n' + rows + anchor)
open(J, 'w').write(js)
print('applied')
