#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR3-DSP: alternative generators for the Inspirator (Lead / Bass / Arp / Drums).
  7139 Generator: Classic | Euclid | Markov | Cellular | L-System      7140 Variant 0-15
Euclid: Bjorklund-style rhythm (pulses from Density, rotation = Variant), chord tones as pitches.
Markov: order-2 chain over scale-step deltas, trained on a built-in corpus (Variant 0-3: Pop / Minor / Jazz / Custom = imported MIDI).
Cellular: elementary automaton (rule 30/90/110/150 from Variant) gives the rhythm; the neighbourhood of a cell gives the melodic step.
L-System: string rewriting (4 rule sets) gives rests and up/down/stay steps.  Drums: Euclid per lane, or automaton hats/percussion."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR3-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

CODE = r'''
    // ---- INSPIRATOR3-DSP: alternative generators ----
    int ins_pGen = 0;
    int ins_pGenVar = 0;
    int[343] ins_mkCnt;
    int[64] ins_imDelta;     // deltas (class 0..6) of an imported melody, for the Custom Markov corpus
    int ins_imDeltaCount = 0;
    int[128] ins_lsStr;
    int ins_lsLen = 0;

    int ins_euclid (int k, int n, int rot)
    {
        int m = 0;
        for (int s = 0; s < n; ++s)
        {
            int ix = ins_posMod (s + rot, n);
            if (((ix * k) % n) < k) m = m | (1 << s);
        }
        return m;
    }

    int ins_corpusDelta (int corpus, int i)
    {
        // three built-in "schools", 32 deltas each (class 3 = repeat, 4 = +1 step, 2 = -1 step ...)
        if (corpus == 0)
        {
            int t0 = 0;
            const int[32] pop = (3,4,4,2,3,4,5,3,2,2,4,3,3,5,1,3,4,4,3,2,3,4,2,3,3,5,4,2,1,3,4,3);
            return pop.at (i % 32);
        }
        if (corpus == 1)
        {
            const int[32] mnr = (3,2,3,4,2,3,3,1,4,3,2,2,4,5,3,2,3,4,3,2,4,3,3,2,4,4,2,2,3,5,3,1);
            return mnr.at (i % 32);
        }
        const int[32] jzz = (5,1,4,2,5,0,4,3,1,5,2,4,1,6,0,3,5,2,4,1,5,3,0,4,2,5,1,3,4,2,6,0);
        return jzz.at (i % 32);
    }

    void ins_trainMarkov()
    {
        for (int i = 0; i < 343; ++i) ins_mkCnt.at (i) = 1;
        int corpus = ins_pGenVar % 4;
        int n = 32;
        if (corpus == 3 && ins_imDeltaCount > 3) n = ins_imDeltaCount;
        int d1 = 3;
        int d2 = 3;
        for (int i = 0; i < n * 2; ++i)
        {
            int d = 3;
            if (corpus == 3)
            {
                if (ins_imDeltaCount > 3) d = ins_imDelta.at (i % n);
            }
            else d = ins_corpusDelta (corpus, i);
            ins_mkCnt.at ((d1 * 7 + d2) * 7 + d) += 4;
            d1 = d2;
            d2 = d;
        }
    }

    int ins_markovNext (int d1, int d2, int key)
    {
        int base = (d1 * 7 + d2) * 7;
        int total = 0;
        for (int k = 0; k < 7; ++k) total += ins_mkCnt.at (base + k);
        int r = ins_rv (360, key) % ins_maxi (1, total);
        for (int k = 0; k < 7; ++k)
        {
            r -= ins_mkCnt.at (base + k);
            if (r < 0) return k;
        }
        return 3;
    }

    void ins_buildLSystem()
    {
        int set = ins_pGenVar % 4;
        const int[48] rules = (0,0,1, 1,2,0, 2,0,3, 3,2,4,
                               0,3,1, 2,1,0, 2,0,0, 0,3,4,
                               0,2,1, 1,1,0, 3,2,0, 0,4,4,
                               0,1,0, 1,0,2, 0,3,2, 1,2,4);
        ins_lsLen = 1;
        ins_lsStr.at (0) = ins_rv (350, 0) % 3;
        int[128] tmp;
        for (int it = 0; it < 4; ++it)
        {
            int w = 0;
            for (int i = 0; i < ins_lsLen; ++i)
            {
                int sym = ins_lsStr.at (i);
                for (int j = 0; j < 3; ++j)
                {
                    int r = rules.at (set * 12 + sym * 3 + j);
                    if (r < 4 && w < 128) { tmp.at (w) = r; w += 1; }
                }
            }
            if (w == 0) { tmp.at (0) = 0; w = 1; }
            for (int i = 0; i < w; ++i) ins_lsStr.at (i) = tmp.at (i);
            ins_lsLen = w;
        }
    }

    // symbols: 0 up, 1 down, 2 stay, 3 rest
    int ins_caNext (int row, int rule, int n)
    {
        int nr = 0;
        for (int i = 0; i < n; ++i)
        {
            int l = (row >> ins_posMod (i - 1, n)) & 1;
            int c = (row >> i) & 1;
            int r = (row >> ins_posMod (i + 1, n)) & 1;
            if (((rule >> (l * 4 + c * 2 + r)) & 1) != 0) nr = nr | (1 << i);
        }
        return nr;
    }

    int ins_caRule()
    {
        int v = ins_pGenVar % 4;
        if (v == 0) return 30;
        if (v == 1) return 90;
        if (v == 2) return 110;
        return 150;
    }

    void ins_genAlt (int role)
    {
        int gen = ins_pGen;
        if (role == 4) { ins_genDrumsAlt(); return; }
        int baseP = 60 + 12 * ins_pOctave + ins_keyOff();
        int centerSi = 7;
        int w = 3 + ins_pRange * 6 / 100;
        if (role == 2) { baseP = 36 + 12 * ins_pOctave + ins_keyOff(); centerSi = 0; w = 4; }
        bool minorish = ins_isMinorish();
        int ns = ins_clampi (ins_stepsBar, 1, 31);
        int fullMask = (1 << ns) - 1;
        int caRow = (ins_rv (340, 0) | 5) & fullMask;
        int caRule = ins_caRule();
        if (gen == 2) ins_trainMarkov();
        if (gen == 4) ins_buildLSystem();
        int cur = centerSi;
        int d1 = 3;
        int d2 = 3;
        int kk = 0;
        int pc = 1 + (ins_pDensity * (ns - 2)) / 100;
        pc = ins_clampi (pc, 1, ns);

        for (int b = 0; b < ins_numBars; ++b)
        {
            int nbar = (b + 1) % ins_maxi (1, ins_numBars);
            bool pushNext = ins_pushInto (nbar);
            int mask = 0;
            if (gen == 1)
            {
                int rot = ins_pGenVar + (b % 2) * (1 + ins_pGenVar % 3);
                mask = ins_euclid (pc, ns, rot);
            }
            else if (gen == 3)
            {
                caRow = ins_caNext (caRow, caRule, ns);
                if (caRow == 0) caRow = 1 << (ins_rv (341, b) % ns);
                mask = caRow & fullMask;
                // density thins the automaton out
                for (int s = 0; s < ns; ++s)
                {
                    if (((mask >> s) & 1) != 0 && (ins_rv (342, b * 32 + s) % 100) >= 40 + ins_pDensity * 60 / 100)
                        mask = mask & (fullMask - (1 << s));
                }
            }
            else if (gen == 4)
            {
                for (int s = 0; s < ns; ++s)
                {
                    int sym = ins_lsStr.at ((b * ns + s) % ins_maxi (1, ins_lsLen));
                    if (sym != 3 && (ins_rv (343, b * 32 + s) % 100) < 30 + ins_pDensity * 70 / 100) mask = mask | (1 << s);
                }
            }
            else
            {
                for (int s = 0; s < ns; ++s)
                {
                    int t = ins_tmpl (s);
                    int wt = 0;
                    if (t >= 0 && (t % 8) == 0)      wt = 95;
                    else if (t >= 0 && (t % 4) == 0) wt = 75;
                    else if (t >= 0 && (t % 2) == 0) wt = 55;
                    else                             wt = 14 + ins_pComplex / 4;
                    if ((ins_rv (344, b * 32 + s) % 100) < wt * (28 + ins_pDensity) / 100) mask = mask | (1 << s);
                }
            }
            if (mask == 0) mask = 1;

            int lastC = ins_chordAt (b, 0);
            for (int s = 0; s < ns; ++s)
            {
                if (((mask >> s) & 1) != 0)
                {
                    int t = ins_tmpl (s);
                    int c = ins_chordAt (b, s);
                    bool strong = (t >= 0 && (t % 8) == 0);
                    if (c != lastC) strong = true;
                    lastC = c;
                    int pitch = 0;

                    if (gen == 1)
                    {
                        // chord tones, up and down through the chord
                        int cnt = ins_maxi (1, ins_cCnt.at (c));
                        int span = cnt * (1 + ins_pRange / 50);
                        int ix = kk % ins_maxi (1, 2 * span - 2 + (span == 1 ? 1 : 0));
                        if (ix >= span) ix = 2 * span - 2 - ix;
                        int ch = ins_posMod (ins_pKey + ins_cRoot.at (c) + ins_cInt.at (c * 5 + (ix % cnt)), 12);
                        int lo = baseP - 5;
                        pitch = lo + ins_posMod (ch - lo, 12) + 12 * (ix / cnt);
                    }
                    else
                    {
                        int dlt = 0;
                        if (gen == 2)
                        {
                            int dc = ins_markovNext (d1, d2, kk + b * 64);
                            d1 = d2;
                            d2 = dc;
                            dlt = dc - 3;
                        }
                        else if (gen == 3)
                        {
                            int nb = (((caRow >> ins_posMod (s - 1, ns)) & 1) << 2) | (((caRow >> s) & 1) << 1) | ((caRow >> ins_posMod (s + 1, ns)) & 1);
                            int tabd = 0;
                            if (nb == 1 || nb == 5) tabd = 1;
                            else if (nb == 2 || nb == 6) tabd = -1;
                            else if (nb == 3) tabd = 2;
                            else if (nb == 4) tabd = -2;
                            dlt = tabd;
                        }
                        else if (gen == 4)
                        {
                            int sym = ins_lsStr.at ((b * ns + s) % ins_maxi (1, ins_lsLen));
                            if (sym == 0) dlt = 1;
                            else if (sym == 1) dlt = -1;
                        }
                        else
                        {
                            dlt = (ins_rv (345, kk) % 5) - 2;
                        }
                        if (kk > 0) cur += dlt;
                        if (cur > centerSi + w) cur = centerSi + w - 1;
                        if (cur < centerSi - w) cur = centerSi - w + 1;
                        if (ins_pComplex < 50 && dlt != 0)
                        {
                            int d7 = ins_posMod (cur, 7);
                            bool avoid = false;
                            if (minorish) avoid = (d7 == 1 || d7 == 5);
                            else          avoid = (d7 == 3 || d7 == 6);
                            if (avoid) cur += dlt;
                        }
                        if (strong) cur = ins_nearestChordTone (cur, c);
                        if (pushNext && s >= ns - 2) cur = ins_nearestChordTone (cur, ins_chordAt (nbar, 0));
                        pitch = baseP + ins_scaleSemi (cur);
                    }

                    int cyc = (b % 2) * 32 + s;
                    int gap = ins_nextHit (mask, s) - s;
                    if (gap > 8) gap = 8;
                    int len = ins_maxi (6, gap * 24 * ins_pGate / 100);
                    len = ins_durLen (len, cyc, gap * 24);
                    int acc = 0;
                    if (strong)              acc = 10;
                    else if (ins_isBeat (s)) acc = 2;
                    else                     acc = 0 - (ins_rv (78, b * 32 + s) % 12);
                    ins_addNote (b * ins_barTicks + s * 24, ins_humanT (ins_nCount), len, pitch,
                                 ins_pVel + acc + ins_humanV (ins_nCount) + ins_velDev (211, cyc, ins_pRVel));
                    kk += 1;
                }
            }
        }
    }

    void ins_genDrumsAlt()
    {
        int ns = ins_clampi (ins_stepsBar, 1, 31);
        int fullMask = (1 << ns) - 1;
        int caRow = (ins_rv (346, 0) | 9) & fullMask;
        int caRule = ins_caRule();
        for (int b = 0; b < ins_numBars; ++b)
        {
            int kick = 0;
            int snare = 0;
            int hat = 0;
            int open = 0;
            int perc = 0;
            int rot = ins_pGenVar;
            if (ins_pGen == 1)
            {
                kick  = ins_euclid (ins_clampi (2 + ins_pDensity * 5 / 100, 2, ns), ns, 0);
                snare = ins_euclid (ins_clampi (2 + ins_pDensity / 50, 2, ns), ns, ns / 4 + (b % 2));
                hat   = ins_euclid (ins_clampi (4 + ins_pDensity * (ns - 4) / 100, 1, ns), ns, rot % 3);
                open  = ins_euclid (ins_clampi (1 + ins_pDensity / 40, 1, ns), ns, ns / 2 + rot % ns);
                perc  = ins_euclid (ins_clampi (1 + ins_pComplex / 20, 1, ns), ns, rot + b);
            }
            else
            {
                caRow = ins_caNext (caRow, caRule, ns);
                if (caRow == 0) caRow = 1 << (ins_rv (347, b) % ns);
                kick  = ins_euclid (4, ns, 0) | (caRow & ins_caNext (caRow, 90, ns) & fullMask);
                snare = ins_euclid (2, ns, ns / 4) ;
                hat   = caRow | ins_euclid (ns / 2, ns, 0);
                open  = ins_caNext (caRow, 30, ns) & ins_caNext (caRow, 110, ns);
                perc  = ins_caNext (ins_caNext (caRow, caRule, ns), 90, ns);
            }
            for (int s = 0; s < ns; ++s)
            {
                int g = b * ins_barTicks + s * 24;
                int cyc = (b % 2) * 32 + s;
                bool strong = ins_isBeat (s);
                if (((kick >> s) & 1) != 0)
                    ins_addNote (g, ins_humanT (ins_nCount), 20, ins_lanePitch.at (0), ins_pVel + 14 + ins_humanV (ins_nCount) + ins_velDev (211, cyc, ins_pRVel));
                if (((snare >> s) & 1) != 0 && ((kick >> s) & 1) == 0)
                    ins_addNote (g, ins_humanT (ins_nCount), 20, ins_lanePitch.at (1), ins_pVel + 10 + ins_humanV (ins_nCount) + ins_velDev (212, cyc, ins_pRVel));
                if (((hat >> s) & 1) != 0 && ((open >> s) & 1) == 0)
                {
                    int hv = ins_pVel - 18 + ins_humanV (ins_nCount) + ins_velDev (213, cyc, ins_pRVel);
                    if (strong) hv += 12;
                    ins_addNote (g, ins_humanT (ins_nCount), 12, ins_lanePitch.at (3), hv);
                }
                if (((open >> s) & 1) != 0 && (s % 2) == 1)
                    ins_addNote (g, ins_humanT (ins_nCount), 36, ins_lanePitch.at (4), ins_pVel - 10 + ins_humanV (ins_nCount));
                if (((perc >> s) & 1) != 0 && ins_pComplex > 25 && ((snare >> s) & 1) == 0)
                    ins_addNote (g, ins_humanT (ins_nCount), 16, ins_lanePitch.at (5), ins_pVel - 22 + ins_humanV (ins_nCount));
            }
        }
    }
'''
rep('    void ins_regenerate()\n', CODE + '\n    void ins_regenerate()\n')
rep('        if (ins_pMode == 0)      ins_genChords();', '        if (ins_pGen > 0 && ins_pMode >= 1) ins_genAlt (ins_pMode);\n        else if (ins_pMode == 0)      ins_genChords();')
a = '    event param7138 (float v) { ins_pDegF = ins_clampi (ins_roundi (v), 0, 7); ins_dirty = true; }'
rep(a, a + '\n    event param7139 (float v) { ins_pGen = ins_clampi (ins_roundi (v), 0, 5); ins_dirty = true; }\n    event param7140 (float v) { ins_pGenVar = ins_clampi (ins_roundi (v), 0, 15); ins_dirty = true; }')
d = '    input event float param7138 [[ name: "Insp Melody Degree", min: 0.0, max: 7.0, init: 0.0, step: 1.0, text: "Free|I|II|III|IV|V|VI|VII", automatable: false ]];'
rep(d, d + '\n    input event float param7139 [[ name: "Insp Generator", min: 0.0, max: 5.0, init: 0.0, step: 1.0, text: "Classic|Euclid|Markov|Cellular|L-System|Import", automatable: false ]];\n    input event float param7140 [[ name: "Insp Gen Variant", min: 0.0, max: 15.0, init: 0.0, step: 1.0, automatable: false ]];')
s = '    [7138, "Insp Melody Degree", 0, 7, 0, "", "sel", ["Free", "I", "II", "III", "IV", "V", "VI", "VII"], 1, "Degree", null],'
rep(s, s + '\n    [7139, "Insp Generator", 0, 5, 0, "", "sel", ["Classic", "Euclid", "Markov", "Cellular", "L-System", "Import"], 1, "Generator", null],\n    [7140, "Insp Gen Variant", 0, 15, 0, "", "knb", null, 1, "Variant", null],', 'idx')
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
