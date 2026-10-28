#!/usr/bin/env python3
"""Idempotent: tempo sync for the effects (Sync division per slot, ids 940..969, beat clock locked to the host position), the Trance Gate / Auto-Pan /
random modes of the tremolo and more modes for every effect.  Run after build_fx2.py."""
import os, sys, re
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if '// FX-SYNC' in src:
    print('already applied'); sys.exit(0)

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old[:70], src.count(old))
    src = src.replace(old, new)

def cut(start_marker, end_marker):
    """returns (start, end) indexes of the text from start_marker up to (not including) end_marker"""
    a = src.index(start_marker); b = src.index(end_marker, a)
    return a, b

# ---- declarations, inputs, handlers -------------------------------------------------------------------------------------
rep('    int[32]       fxMode;  // padded to a power of two (cheap index wrap)\n',
    '    int[32]       fxMode;  // padded to a power of two (cheap index wrap)\n'
    '    int[32]       fxSync;  // FX-SYNC: 0 = free, 1..18 = tempo division (the LFO divisions, one per slot)\n'
    '    float64       fxBeat = 0.0;     // FX-SYNC: quarter notes, locked to the host position, advanced with the tempo\n'
    '    float[512]    fxGate;           // FX-SYNC: 24 trance gate patterns x 16 steps\n')
rep('    input event std::timeline::Tempo tempoIn;\n', '    input event std::timeline::Tempo tempoIn;\n    input event std::timeline::Position positionIn;   // FX-SYNC\n')
rep('    event tempoIn (std::timeline::Tempo t) { if (t.bpm > 1.0f) hostBpm = t.bpm; }',
    '''    event tempoIn (std::timeline::Tempo t)
    {
        if (t.bpm > 1.0f && t.bpm != hostBpm)
        {
            hostBpm = t.bpm;

            for (int fs = 0; fs < 30; ++fs)
                fxDirty.at (fs) = true;
        }
    }

    // the host jumped / started: lock the effect beat clock to its position
    event positionIn (std::timeline::Position p) { fxBeat = p.quarterNote; }''')
names = ['Main', 'Bus 1', 'Bus 2']
decl = ''.join('    input event float param%d [[ name: "%s FX %d Sync", min: 0.0, max: 18.0, init: 0.0, step: 1.0 ]];\n' % (940 + rk * 10 + sl, names[rk], sl + 1) for rk in range(3) for sl in range(10))
m = re.search(r'    input event float param881 [^\n]*\n', src)
assert m
src = src[:m.end()] + decl + src[m.end():]

hand = ''.join('    event param%d (float v) { fxSync.at (%d) = clamp (int (v + 0.5f), 0, 18); fxDirty.at (%d) = true; }\n' % (940 + i, i, i) for i in range(30))
rep('    event param536 (float v) { driveAlg    = float (rint (v)); }\n', '    event param536 (float v) { driveAlg    = float (rint (v)); }\n    // FX-SYNC: sync divisions of the effect slots\n' + hand)
rep('        for (int ld = 0; ld < 10; ++ld)\n            mLfoDiv.at (ld) = 8.0f;\n', '        for (int ld = 0; ld < 10; ++ld)\n            mLfoDiv.at (ld) = 8.0f;\n\n        fxGateInit();\n')

# beat clock: one step per sample, before the racks run
rep('            // ----- FX racks: Bus 1 and Bus 2 feed the Main rack, which feeds the output -----',
    '            fxBeat += float64 (syncBpmOver > 1.0f ? syncBpmOver : hostBpm) * processor.period / 60.0;\n\n'
    '            // ----- FX racks: Bus 1 and Bus 2 feed the Main rack, which feeds the output -----')

# ---- helpers (after fxExpMap) ------------------------------------------------------------------------------------------------
PATTERNS = [   # 16 steps: '#' on, '+' soft, '.' off
    ('Eighths',      '#.#.#.#.#.#.#.#.'), ('Quarters',     '#...#...#...#...'), ('Off-beat',     '..#...#...#...#.'), ('Accented 16ths', '#+#+#+#+#+#+#+#+'),
    ('3-3-2',        '#..#..#.#..#..#.'), ('Dotted',       '#..#..#...#..#..'), ('Rolling',      '#.##.#.##.##.#.#'), ('Syncopated',   '#..#.#..#..#.#..'),
    ('Stutter',      '####............'), ('Half time',    '#.......#.......'), ('Gallop',       '#.###.#.###.#.##'), ('Trance',       '#.##.##.#.##.##.'),
    ('Double',       '##..##..##..##..'), ('Ghost notes',  '#+.+#+.+#+.+#+.+'), ('Build',         '#...#...#.#.####'), ('Break',        '#.#.#.#.##..##..'),
    ('Pulse',        '#...#...#...#.#.'), ('Skip',         '#.#...#.#.#...#.'), ('Rapid',         '####.###.###.###'), ('Sparse',       '#.....#...#.....'),
    ('Pump',         '#.+.#.+.#.+.#.+.'), ('Bounce',       '#.#..#.#.#..#.#.'), ('Triplet feel',  '#..#..#..#..#..#'), ('Full',         '################'),
]
assert len(PATTERNS) == 24 and all(len(p) == 16 for _, p in PATTERNS)
calls = ''
for i, (_, p) in enumerate(PATTERNS):
    on = sum(1 << k for k, c in enumerate(p) if c in '#+'); soft = sum(1 << k for k, c in enumerate(p) if c == '+')
    calls += '        fxGateSet (%d, %d, %d);\n' % (i, on, soft)
helpers = '''    // ---- FX-SYNC ----
    // 24 trance gate patterns of 16 steps (bit k of 'on' = step k open, bit k of 'soft' = step k at 45 %)
    void fxGateSet (int p, int on, int soft)
    {
        for (int k = 0; k < 16; ++k)
        {
            float v = 0.0f;

            if (((on >> k) & 1) != 0)
                v = ((soft >> k) & 1) != 0 ? 0.45f : 1.0f;

            fxGate.at (p * 16 + k) = v;
        }
    }

    void fxGateInit()
    {
''' + calls + '''    }

    // Phase 0..1 of the modulation of an effect: free running at its rate, or locked to the beat clock with the slot's division
    float64 fxPhase (int s, int pb, int db)
    {
        int dv = fxSync.at (s);

        if (dv > 0)
        {
            float64 b = fxBeat / float64 (divBeats.at (clamp (dv - 1, 0, 17)));
            return b - floor (b);
        }

        float64 ph = fxPh.at (pb) + float64 (fxD.at (db)) * processor.period;
        if (ph >= 1.0) ph -= 1.0;
        fxPh.at (pb) = ph;
        return ph;
    }

    // linear interpolated read of a circular buffer of n floats at base
    float fxTapN (int base, int n, float pos)
    {
        float p = pos;
        if (p < 0.0f) p += float (n);
        if (p >= float (n)) p -= float (n);
        int i0 = clamp (int (p), 0, n - 1);
        int i1 = i0 + 1;
        if (i1 >= n) i1 = 0;
        float fr = p - float (i0);
        return fxArena.at (base + i0) * (1.0f - fr) + fxArena.at (base + i1) * fr;
    }

    // value of the gate pattern at phase p (0..1 over the 16 steps); swing delays the odd steps by a fraction of a step
    float fxGateAt (int pat, float p, float swing)
    {
        float u  = p * 16.0f;
        int   si = clamp (int (u), 0, 15);
        float f  = u - float (si);

        if ((si & 1) == 1 && f < swing)
            si -= 1;

        return fxGate.at (pat * 16 + si);
    }

'''
# phase of the four modulated effects
rep('''        float64 ph = fxPh.at (pb) + float64 (fxD.at (db)) * processor.period;
        if (ph >= 1.0) ph -= 1.0;
        fxPh.at (pb) = ph;
''', '        float64 ph = fxPhase (s, pb, db);\n', 4)

rep('    // Clears the delay lines and filter memories of one slot\n', helpers + '    // Clears the delay lines and filter memories of one slot\n')

# ---- derive: tremolo extras, delay sync, reverb / EQ / compressor modes ----------------------------------------------------------
rep('''            fxD.at (db)     = fxExpMap (p1, 0.1f, 20.0f);
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = p3;
''', '''            fxD.at (db)     = fxExpMap (p1, 0.1f, 20.0f);
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = p3;
            fxD.at (db + 3) = clamp (p4 * 24.0f, 0.0f, 23.99f);                                     // gate pattern
            fxD.at (db + 4) = clamp (1.0f - float (exp (-dt / fxExpMap (p5, 0.0003f, 0.04f))), 0.0f, 1.0f);   // gate / random smoothing
            fxD.at (db + 5) = clamp (fxP.at (pb + 5), 0.0f, 1.0f) * 0.5f;                           // swing
''')
rep('''            fxD.at (db)     = fxExpMap (p1, 0.1f, 20.0f);
''', '''            fxD.at (db)     = fxExpMap (p1, 0.1f, 20.0f);
''')
# reverb modes are handled in fxReverb; EQ modes
rep('''            // EQ: low shelf 100 Hz, mid bell, high shelf 8 kHz
            fxBiquad (db,      0, (p1 - 0.5f) * 24.0f, 100.0f, 0.7f);
            fxBiquad (db + 5,  1, (p2 - 0.5f) * 24.0f, fxExpMap (p3, 200.0f, 5000.0f), fxExpMap (p5, 0.3f, 4.0f));
            fxBiquad (db + 10, 2, (p4 - 0.5f) * 24.0f, fxExpMap (clamp (fxP.at (pb + 5), 0.0f, 1.0f), 4000.0f, 16000.0f), 0.7f);
''', '''            // EQ: low shelf 100 Hz, mid bell, high shelf 8 kHz; mode 1 tilt (Low = tilt amount, Mid Freq = pivot), 2 loudness contour (Low = amount), 3 presence (wider ranges)
            int em = fxMode.at (s);
            float hiF = fxExpMap (clamp (fxP.at (pb + 5), 0.0f, 1.0f), 4000.0f, 16000.0f);

            if (em == 1)
            {
                float tl = (p1 - 0.5f) * 24.0f;
                float pv = fxExpMap (p3, 200.0f, 5000.0f);
                fxBiquad (db,      0, -tl * 0.5f, pv * 0.6f, 0.6f);
                fxBiquad (db + 5,  1, (p2 - 0.5f) * 24.0f, pv, fxExpMap (p5, 0.3f, 4.0f));
                fxBiquad (db + 10, 2, tl * 0.5f, pv * 1.6f, 0.6f);
            }
            else if (em == 2)
            {
                float am = p1 * 14.0f;
                fxBiquad (db,      0, am, 90.0f, 0.7f);
                fxBiquad (db + 5,  1, (p2 - 0.5f) * 24.0f - am * 0.25f, fxExpMap (p3, 200.0f, 5000.0f), fxExpMap (p5, 0.3f, 4.0f));
                fxBiquad (db + 10, 2, am * 0.7f + (p4 - 0.5f) * 24.0f, hiF, 0.7f);
            }
            else if (em == 3)
            {
                fxBiquad (db,      0, (p1 - 0.5f) * 24.0f, 160.0f, 0.7f);
                fxBiquad (db + 5,  1, (p2 - 0.5f) * 24.0f, fxExpMap (p3, 900.0f, 7000.0f), fxExpMap (p5, 0.5f, 6.0f));
                fxBiquad (db + 10, 2, (p4 - 0.5f) * 24.0f, fxExpMap (clamp (fxP.at (pb + 5), 0.0f, 1.0f), 8000.0f, 18000.0f), 0.6f);
            }
            else
            {
                fxBiquad (db,      0, (p1 - 0.5f) * 24.0f, 100.0f, 0.7f);
                fxBiquad (db + 5,  1, (p2 - 0.5f) * 24.0f, fxExpMap (p3, 200.0f, 5000.0f), fxExpMap (p5, 0.3f, 4.0f));
                fxBiquad (db + 10, 2, (p4 - 0.5f) * 24.0f, hiF, 0.7f);
            }
''')
rep('''            fxD.at (db + 5) = 12.0f * clamp (fxP.at (pb + 5), 0.0f, 1.0f);                       // knee width (dB)
        }
    }
''', '''            fxD.at (db + 5) = 12.0f * clamp (fxP.at (pb + 5), 0.0f, 1.0f);                       // knee width (dB)

            if (fxMode.at (s) == 2)
            {
                // limiter: ratio about 20:1, attack about 0.1 ms
                fxD.at (db + 1) = -0.95f;
                fxD.at (db + 2) = float (exp (-1.0f / (sr * 0.0001f)));
            }
        }

        // FX-SYNC: the delay time follows the tempo division of the slot
        if (ty == 3 && fxSync.at (s) > 0)
        {
            float bpmN = syncBpmOver > 1.0f ? syncBpmOver : hostBpm;
            fxD.at (db) = clamp (divBeats.at (clamp (fxSync.at (s) - 1, 0, 17)) * 60.0f / bpmN * sr, 2.0f, 98000.0f);
        }
    }
''')

# ---- distortion algorithms 9..12 ---------------------------------------------------------------------------------------------------
rep('''        else if (al == 8)
        {
            y = float (tanh (xx));
        }
''', '''        else if (al == 8)
        {
            y = float (tanh (xx));
        }
        else if (al == 9)
        {
            // diode: soft on the positive half, harder and weaker on the negative half
            y = xx >= 0.0f ? float (tanh (xx * 1.2f)) : float (tanh (xx * 0.45f)) * 2.1f;
        }
        else if (al == 10)
        {
            // chebyshev: first, third and fifth harmonic mixed in
            float xs = clamp (xx * 0.6f, -1.0f, 1.0f);
            float x2 = xs * xs;
            y = xs * 0.5f + (4.0f * x2 * xs - 3.0f * xs) * 0.3f + (16.0f * x2 * x2 * xs - 20.0f * x2 * xs + 5.0f * xs) * 0.2f;
        }
        else if (al == 11)
        {
            // tape: gentle rational saturation
            float xc = clamp (xx, -3.0f, 3.0f);
            y = xc * (27.0f + xc * xc) / (27.0f + 9.0f * xc * xc);
        }
        else if (al == 12)
        {
            // gated: clipped signal with a dead zone around zero
            float xa = abs (xx);
            y = xa < 0.15f ? 0.0f : (clamp (xx * 1.5f, -1.0f, 1.0f) * (xa < 0.3f ? (xa - 0.15f) / 0.15f : 1.0f));
        }
''')

# ---- bit crush modes 3..5 --------------------------------------------------------------------------------------------------------------
rep('            fxI.at (ib + 2) = max (1, int (fxD.at (db + 1) * (1.0f + fxD.at (db + 4) * (r1 * 2.0f - 1.0f))));',
    '            fxI.at (ib + 2) = cm == 3 ? 1 : max (1, int (fxD.at (db + 1) * (1.0f + fxD.at (db + 4) * (r1 * 2.0f - 1.0f))));')
rep('        if (fxD.at (db) < 15.5f)\n        {\n            float lv = fxD.at (db + 2);', '        if (fxD.at (db) < 15.5f && cm != 4)\n        {\n            float lv = fxD.at (db + 2);')
rep('''            else
            {
                yl = rint ((yl + dz) * lv) / lv;
                yr = rint ((yr + dz) * lv) / lv;
            }
        }

        return float<2> (yl, yr);''', '''            else if (cm == 5)
            {
                // noise shaped: the quantisation error of the previous sample is fed back
                float ul = yl - fxF.at (fb + 2) * 0.9f + dz;
                float ur = yr - fxF.at (fb + 3) * 0.9f + dz;
                float ql = rint (ul * lv) / lv;
                float qr = rint (ur * lv) / lv;
                fxF.at (fb + 2) = ql - ul;
                fxF.at (fb + 3) = qr - ur;
                yl = ql;
                yr = qr;
            }
            else
            {
                yl = rint ((yl + dz) * lv) / lv;
                yr = rint ((yr + dz) * lv) / lv;
            }
        }

        return float<2> (yl, yr);''')

# ---- delay: reverse (4) and multi-tap (5) --------------------------------------------------------------------------------------------------
rep('''        float dampA = fxD.at (db + 2);
        float sL = fxF.at (fb)     + dampA * (dl - fxF.at (fb));''', '''        if (dty == 4)
        {
            // reverse: two read heads run backwards through the last two delay times, crossfaded with sin^2 windows
            float rt  = clamp (cur, 64.0f, 49000.0f);
            float tt  = float (fxPh.at (pb + 3)) + 1.0f;
            if (tt >= rt) tt -= rt;
            fxPh.at (pb + 3) = float64 (tt);
            float tb  = tt + rt * 0.5f;
            if (tb >= rt) tb -= rt;
            float sa  = float (sin (float (pi) * tt / rt));
            float sb  = float (sin (float (pi) * tb / rt));
            dl = fxTapN (ab, 98304, float (wp) - 2.0f * tt) * sa * sa + fxTapN (ab, 98304, float (wp) - 2.0f * tb) * sb * sb;
            dr = fxTapN (ab + 98304, 98304, float (wp) - 2.0f * tt) * sa * sa + fxTapN (ab + 98304, 98304, float (wp) - 2.0f * tb) * sb * sb;
        }

        float dampA = fxD.at (db + 2);
        float sL = fxF.at (fb)     + dampA * (dl - fxF.at (fb));''')
rep('''        wp += 1;
        if (wp >= 98304) wp = 0;
        fxI.at (ib) = wp;

        return float<2> (x[0] + dl + dl2, x[1] + dr + dr2);''', '''        if (dty == 5)
        {
            // multi-tap: extra taps at 2/3 and 1/3 of the delay time, the right channel swapped
            dl2 = fxTapN (ab, 98304, float (wp) - cur * 0.6667f) * 0.6f + fxTapN (ab + 98304, 98304, float (wp) - cur * 0.3333f) * 0.4f;
            dr2 = fxTapN (ab + 98304, 98304, float (wp) - cur * 0.6667f) * 0.6f + fxTapN (ab, 98304, float (wp) - cur * 0.3333f) * 0.4f;
        }

        wp += 1;
        if (wp >= 98304) wp = 0;
        fxI.at (ib) = wp;

        return float<2> (x[0] + dl + dl2, x[1] + dr + dr2);''')

# ---- chorus: ensemble (3), wide (4) --------------------------------------------------------------------------------------------------------
rep('        float chPhR = chPhL + 0.25f;\n', '        float chPhR = chPhL + (mode == 4 ? 0.5f : 0.25f);\n')
rep('        if (mode == 2) { chBase = 0.007f;  chDep = 0.0045f; }\n',
    '        if (mode == 2) { chBase = 0.007f;  chDep = 0.0045f; }\n        if (mode == 3) { chBase = 0.012f;  chDep = 0.0035f; }\n        if (mode == 4) { chBase = 0.0095f; chDep = 0.005f; }\n')
rep('''        fxF.at (fb)     = wetL;
        fxF.at (fb + 1) = wetR;

        pos += 1;
        if (pos >= 8192) pos = 0;''', '''        if (mode == 3)
        {
            // ensemble: three voices 120 degrees apart
            float wl = wetL;
            float wr = wetR;

            for (int ev = 1; ev < 3; ++ev)
            {
                float po = float (ev) * 0.3333f;
                float pl = chPhL + po;  if (pl >= 1.0f) pl -= 1.0f;
                float pr = chPhR + po;  if (pr >= 1.0f) pr -= 1.0f;
                wl += fxTapN (ab, 8192, float (pos) - (chBase + chDep * depth * float (sin (float (twoPi) * pl))) * sr);
                wr += fxTapN (ab + 8192, 8192, float (pos) - (chBase + chDep * depth * float (sin (float (twoPi) * pr))) * sr);
            }

            wetL = wl * 0.5f;
            wetR = wr * 0.5f;
        }

        fxF.at (fb)     = wetL;
        fxF.at (fb + 1) = wetR;

        pos += 1;
        if (pos >= 8192) pos = 0;''')

# ---- flanger: through-zero (2), stereo (3) ---------------------------------------------------------------------------------------------------
a, b = cut('    float<2> fxFlanger (int s, float<2> x)', '    float<2> fxPhaser (int s, float<2> x)')
src = src[:a] + '''    float<2> fxFlanger (int s, float<2> x)
    {
        int   fb = s * 40;
        int   ib = s * 24;
        int   pb = s * 4;
        int   db = s * 16;
        int   ab = s * 196608;
        float sr = float (processor.frequency);
        int   fm = fxMode.at (s);

        float64 ph = fxPhase (s, pb, db);

        float flMod  = 0.5f + 0.5f * float (sin (float (twoPi) * float (ph)));
        float flModR = flMod;

        if (fm == 3)
        {
            float pr = float (ph) + 0.25f;
            if (pr >= 1.0f) pr -= 1.0f;
            flModR = 0.5f + 0.5f * float (sin (float (twoPi) * pr));
        }

        float flDly  = clamp ((0.0008f + 0.0042f * fxD.at (db + 1) * flMod)  * sr, 2.0f, 4000.0f);
        float flDlyR = clamp ((0.0008f + 0.0042f * fxD.at (db + 1) * flModR) * sr, 2.0f, 4000.0f);

        if (fm == 2)
        {
            // through-zero: the wet delay sweeps around the fixed delay of the dry signal
            float tz = float (sin (float (twoPi) * float (ph)));
            flDly  = clamp ((0.003f + 0.0027f * fxD.at (db + 1) * tz) * sr, 2.0f, 4000.0f);
            flDlyR = flDly;
        }

        int pos = fxI.at (ib);
        fxArena.at (ab + pos)        = x[0] + fxF.at (fb)     * fxD.at (db + 2);
        fxArena.at (ab + 4096 + pos) = x[1] + fxF.at (fb + 1) * fxD.at (db + 2);

        float wetL = fxTapN (ab, 4096, float (pos) - flDly);
        float wetR = fxTapN (ab + 4096, 4096, float (pos) - flDlyR);

        fxF.at (fb)     = wetL;
        fxF.at (fb + 1) = wetR;

        float dryL = x[0] * 0.5f;
        float dryR = x[1] * 0.5f;

        if (fm == 2)
        {
            dryL = fxTapN (ab, 4096, float (pos) - 0.003f * sr) * 0.5f;
            dryR = fxTapN (ab + 4096, 4096, float (pos) - 0.003f * sr) * 0.5f;
        }

        pos += 1;
        if (pos >= 4096) pos = 0;
        fxI.at (ib) = pos;

        return float<2> (dryL + wetL * 0.6f, dryR + wetR * 0.6f);
    }

''' + src[b:]

# ---- phaser: 10 / 12 stages, inverted ---------------------------------------------------------------------------------------------------------
rep('        int stages = 2 * (fxMode.at (s) + 1);\n        for (int ps = 0; ps < stages; ++ps)',
    '        int pm = fxMode.at (s);\n        int stages = pm <= 5 ? 2 * (pm + 1) : (pm == 6 ? 4 : 8);\n        for (int ps = 0; ps < stages; ++ps)')
rep('            float yR = phCoef * xR + fxF.at (fb + 10 + ps);\n            fxF.at (fb + 10 + ps) = xR - phCoef * yR;',
    '            float yR = phCoef * xR + fxF.at (fb + 14 + ps);\n            fxF.at (fb + 14 + ps) = xR - phCoef * yR;')
rep('        return float<2> (x[0] * 0.5f + xL * 0.5f, x[1] * 0.5f + xR * 0.5f);\n    }\n\n    float<2> fxTrem',
    '        if (pm >= 6)\n            return float<2> (x[0] * 0.5f - xL * 0.5f, x[1] * 0.5f - xR * 0.5f);\n\n        return float<2> (x[0] * 0.5f + xL * 0.5f, x[1] * 0.5f + xR * 0.5f);\n    }\n\n    float<2> fxTrem')

# ---- tremolo: rewrite with trance gate (5), auto-pan (6), random S&H (7), smooth random (8) ----------------------------------------------------------
a, b = cut('    float<2> fxTrem (int s, float<2> x)', '    float<2> fxReverb (int s, float<2> x)')
src = src[:a] + '''    float<2> fxTrem (int s, float<2> x)
    {
        int pb = s * 4;
        int db = s * 16;
        int fb = s * 40;
        int ib = s * 24;

        float64 ph = fxPhase (s, pb, db);

        float pL = float (ph);
        float pR = pL + 0.5f * fxD.at (db + 2);
        if (pR >= 1.0f) pR -= 1.0f;

        int   wv    = fxMode.at (s);
        float depth = fxD.at (db + 1);
        float lL    = 0.0f;
        float lR    = 0.0f;

        if (wv == 5)
        {
            // trance gate: 16 step pattern per cycle, the right channel shifted by up to half a pattern, smoothed edges
            int   pat = clamp (int (fxD.at (db + 3)), 0, 23);
            float sw  = fxD.at (db + 5);
            float gL  = 1.0f - fxGateAt (pat, pL, sw);
            float gR  = 1.0f - fxGateAt (pat, pR, sw);
            float cf  = fxD.at (db + 4);
            lL = fxF.at (fb)     + cf * (gL - fxF.at (fb));
            lR = fxF.at (fb + 1) + cf * (gR - fxF.at (fb + 1));
            fxF.at (fb)     = lL;
            fxF.at (fb + 1) = lR;
        }
        else if (wv == 6)
        {
            // auto-pan: equal power pan sweep, depth = width of the sweep
            float pp = 0.5f + 0.5f * depth * float (sin (float (twoPi) * pL));
            return float<2> (x[0] * float (cos (pp * 1.5708f)) * 1.4142f, x[1] * float (sin (pp * 1.5708f)) * 1.4142f);
        }
        else if (wv == 7 || wv == 8)
        {
            // random: a new value every cycle (7 sample & hold with slew, 8 interpolated)
            float prev = float (fxPh.at (pb + 1));

            if (pL < prev)
            {
                int rs = fxI.at (ib);
                if (rs == 0) rs = 12345;
                rs = (rs * 1103515245 + 12345) & 0x7fffffff;
                float r1 = float (rs) / 2147483648.0f;
                rs = (rs * 1103515245 + 12345) & 0x7fffffff;
                float r2 = float (rs) / 2147483648.0f;
                fxI.at (ib) = rs;
                fxF.at (fb + 4) = fxF.at (fb + 2);
                fxF.at (fb + 5) = fxF.at (fb + 3);
                fxF.at (fb + 2) = r1;
                fxF.at (fb + 3) = r1 + (r2 - r1) * fxD.at (db + 2);
            }

            fxPh.at (pb + 1) = float64 (pL);

            if (wv == 7)
            {
                float cf = fxD.at (db + 4);
                lL = fxF.at (fb)     + cf * (fxF.at (fb + 2) - fxF.at (fb));
                lR = fxF.at (fb + 1) + cf * (fxF.at (fb + 3) - fxF.at (fb + 1));
                fxF.at (fb)     = lL;
                fxF.at (fb + 1) = lR;
            }
            else
            {
                float sm = pL * pL * (3.0f - 2.0f * pL);
                lL = fxF.at (fb + 4) + (fxF.at (fb + 2) - fxF.at (fb + 4)) * sm;
                lR = fxF.at (fb + 5) + (fxF.at (fb + 3) - fxF.at (fb + 5)) * sm;
            }
        }
        else if (wv == 0)
        {
            lL = 0.5f - 0.5f * float (sin (float (twoPi) * pL));
            lR = 0.5f - 0.5f * float (sin (float (twoPi) * pR));
        }
        else if (wv == 1)
        {
            lL = abs (2.0f * pL - 1.0f);
            lR = abs (2.0f * pR - 1.0f);
        }
        else if (wv == 2)
        {
            if (pL < 0.5f) lL = 0.0f; else lL = 1.0f;
            if (pR < 0.5f) lR = 0.0f; else lR = 1.0f;
        }
        else if (wv == 3)
        {
            lL = 1.0f - pL;
            lR = 1.0f - pR;
        }
        else
        {
            lL = pL;
            lR = pR;
        }

        return float<2> (x[0] * (1.0f - depth * lL), x[1] * (1.0f - depth * lR));
    }

''' + src[b:]

# ---- reverb modes 4..8 ---------------------------------------------------------------------------------------------------------------------------
rep('        if (rvTy == 3) { rvScale = 2.2f;  rvFbE = min (rvFb + 0.01f, 0.985f); }\n',
    '        if (rvTy == 3) { rvScale = 2.2f;  rvFbE = min (rvFb + 0.01f, 0.985f); }\n'
    '        if (rvTy == 4) { rvScale = 0.5f;  rvFbE = rvFb * 0.94f; rvDmpE = rvDamp * 0.7f; }              // chamber\n'
    '        if (rvTy == 5) { rvScale = 0.18f; rvFbE = rvFb * 0.82f; }                                      // ambience\n'
    '        if (rvTy == 6) { rvScale = 1.2f;  rvDmpE = min (rvDamp * 1.6f, 0.95f); }                       // dark hall\n'
    '        if (rvTy == 7) { rvScale = 0.8f;  rvDmpE = rvDamp * 0.25f; }                                   // bright\n'
    '        if (rvTy == 8) { rvScale = 2.2f;  rvFbE = 0.997f; rvDmpE = min (rvDamp, 0.6f); }               // infinite\n')

# ---- compressor: expander (3) and gate (4) ------------------------------------------------------------------------------------------------------
rep('        return x * (gain * fxD.at (db + 4));\n    }',
    '''        int cmd = fxMode.at (s);

        if (cmd >= 3)
        {
            // downward expander / gate: below the threshold the level is pushed further down (ratio = strength)
            float st = (1.0f / (1.0f + fxD.at (db + 1)) - 1.0f) * (cmd == 3 ? 0.5f : 2.0f);
            gain = 1.0f;

            if (lvl < th)
                gain = max (float (pow (max (lvl, 0.000001f) / th, st)), 0.0001f);
        }

        return x * (gain * fxD.at (db + 4));
    }''')

rep('        // FX-EXT: wet-signal post processing\n', '        // FX-EXT: wet-signal post processing   // FX-SYNC\n')
open(path, 'w').write(src)
print('ok')
