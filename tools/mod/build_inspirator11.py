#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR11-DSP: Generator 8 = Trance (inspired by the public feature list of FeelYourSound TranceEngine / SongEngine:
rolling / gallop / offbeat / psy basslines, arpeggio patterns applied to the chords, rhythmic chord plucks, lead hooks with call and response,
focus notes and micro phrases, acid lines).  Written from scratch from the published feature descriptions - no code or data of that product is used.
Variant (7140, 0-15) picks the pattern:
  Chords -> pluck rhythm (16 patterns)          Bass -> type = Variant % 4 (rolling / offbeat / gallop / psy), octave figure = Variant / 4
  Arp -> one of 16 arpeggio patterns            Lead -> kind = Variant / 4 (call and response / focus note / micro phrase / acid), cell = Variant % 4
  Drums -> the Trance style kit (18)"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR11-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

CODE = r'''
    // ---- INSPIRATOR11-DSP: Trance generator family ----
    int ins_tPitchScale (int si)
    {
        return 60 + 12 * ins_pOctave + ins_keyOff() + ins_scaleSemi (si);
    }

    void ins_tNote (int b, int s, int pitch, int len, int acc, int key)
    {
        int cyc = (b % 2) * 32 + s;
        ins_addNote (b * ins_barTicks + s * 24, ins_humanT (ins_nCount), len, pitch,
                     ins_pVel + acc + ins_humanV (ins_nCount) + ins_velDev (214, cyc, ins_pRVel));
    }

    // rhythmic chord plucks
    void ins_genPluck()
    {
        const int[16] pats = (0x4444, 0x5555, 0x4949, 0xFFFF, 0xEEEE, 0x7777, 0xDDDD, 0x1111, 0x2222, 0x6666, 0x0505, 0x5454, 0x1515, 0x0A0A, 0xAAAA, 0x4B4B);
        int ns = ins_clampi (ins_stepsBar, 1, 31);
        int half = ns / 2;
        for (int b = 0; b < ins_numBars; ++b)
        {
            int cA = ins_chordAt (b, 0);
            int cB = ins_chordAt (b, ns - 1);
            int mask = ins_expandMask (pats.at (ins_pGenVar % 16));
            // thin out with Density: low density keeps only every other hit
            for (int s = 1; s < ns; ++s)
                if (((mask >> s) & 1) != 0 && (ins_rv (396, b * 32 + s) % 100) >= 30 + ins_pDensity * 70 / 100) mask = mask & (0 - 1 - (1 << s));
            // the last bar of a 4 bar phrase gets a lift
            if ((b % 4) == 3) mask = mask | (1 << (ns - 2));
            if (cB != cA) mask = mask | (1 << half);
            if (mask == 0) mask = 1;
            int npA = ins_voicing (cA, 0);
            int npB = ins_voicing (cB, 1);
            for (int s = 0; s < ns; ++s)
            {
                if (((mask >> s) & 1) != 0)
                {
                    int slot = 0;
                    int np = npA;
                    if (s >= half && cB != cA) { slot = 1; np = npB; }
                    int gap = ins_nextHit (mask, s) - s;
                    int len = ins_maxi (6, ins_mini (gap, 2) * 24 * ins_pGate / 100);
                    int acc = -4;
                    if (ins_isBeat (s)) acc = 4;
                    for (int i = 0; i < np; ++i)
                        ins_tNote (b, s, ins_vPit.at (slot * 8 + i), len, acc, i);
                }
            }
        }
    }

    // bass lines: rolling / offbeat / gallop / psy, octave figures
    void ins_genTBass()
    {
        int type = ins_pGenVar % 4;
        int opat = ins_pGenVar / 4;
        int ns = ins_clampi (ins_stepsBar, 1, 31);
        int low = 36 + 12 * ins_pOctave;
        for (int b = 0; b < ins_numBars; ++b)
        {
            int k = 0;
            for (int s = 0; s < ns; ++s)
            {
                int q = s % 4;
                bool hit = false;
                if (type == 0 || type == 3) hit = (q != 0);
                else if (type == 1)         hit = (q == 2);
                else                        hit = (q != 1);
                if (hit && (ins_rv (397, b * 32 + s) % 100) >= 55 + ins_pDensity * 45 / 100) hit = false;
                if (hit)
                {
                    int c = ins_chordAt (b, s);
                    int rootPc = ins_posMod (ins_pKey + ins_cRoot.at (c), 12);
                    int p = low + ins_posMod (rootPc - low, 12);
                    int off = 0;
                    int m = k % 4;
                    if (opat == 1)      { if ((k % 2) == 1) off = 12; }
                    else if (opat == 2) { if (m == 2) off = 12; else if (m == 3) off = 7; }
                    else if (opat == 3) { if (m == 1) off = 7; else if (m == 3) off = 12; }
                    else if (type == 3) { if (m == 2) off = 12; }
                    int len = ins_maxi (6, 24 * ins_pGate / 100);
                    if (type == 1) len = ins_maxi (6, 36 * ins_pGate / 100);
                    int acc = (q == 2) ? 8 : 0;
                    ins_tNote (b, s, p + off, len, acc, k);
                    k += 1;
                }
            }
        }
    }

    // arpeggio patterns over the chord tones (index 0-3 = chord tone, +4 = one octave up, +8 = two octaves up)
    void ins_genTArp()
    {
        const int[128] pat = (0,1,2,1,0,1,2,1,  0,2,1,2,0,2,1,2,  0,1,2,5,2,1,0,1,  0,4,1,5,2,6,1,5,
                              0,0,4,4,1,1,5,5,  2,1,0,1,2,1,0,1,  0,1,2,4,5,6,5,4,  0,2,4,2,0,2,4,2,
                              0,4,0,4,2,6,2,6,  0,1,2,1,4,5,6,5,  0,2,1,2,4,6,5,6,  0,0,4,0,0,0,4,0,
                              2,4,6,4,2,4,6,4,  0,4,2,6,1,5,2,6,  0,1,2,0,1,2,0,1,  0,4,8,4,0,4,8,4);
        int ns = ins_clampi (ins_stepsBar, 1, 31);
        int pt = ins_pGenVar % 16;
        int base = 60 + 12 * ins_pOctave - 5;
        for (int b = 0; b < ins_numBars; ++b)
        {
            for (int s = 0; s < ns; ++s)
            {
                if ((ins_rv (398, b * 32 + s) % 100) < 40 + ins_pDensity * 60 / 100)
                {
                    int c = ins_chordAt (b, s);
                    int cnt = ins_maxi (1, ins_cCnt.at (c));
                    int e = pat.at (pt * 8 + (s % 8));
                    int tone = e % 4;
                    int oct = e / 4;
                    if (tone >= cnt) tone = tone % cnt;
                    int pc = ins_posMod (ins_pKey + ins_cRoot.at (c) + ins_cInt.at (c * 5 + tone), 12);
                    int p = base + ins_posMod (pc - base, 12) + 12 * oct;
                    int acc = (s % 4) == 0 ? 8 : ((s % 2) == 0 ? 2 : -4);
                    ins_tNote (b, s, p, ins_maxi (6, 24 * ins_pGate / 100), acc, s);
                }
            }
        }
    }

    // lead hooks: call and response, focus note, micro phrases, acid line
    void ins_genTLead()
    {
        int kind = ins_pGenVar / 4;
        int cellSel = ins_pGenVar % 4;
        int ns = ins_clampi (ins_stepsBar, 1, 31);
        int centerSi = 7;
        int w = 3 + ins_pRange * 6 / 100;
        const int[16] cells = (0,2,1,3,  0,1,0,2,  0,3,2,1,  0,2,4,2);
        int focus = centerSi + (ins_pGenVar % 3) - 1;
        int pc = ins_clampi (3 + ins_pDensity * 5 / 100, 2, ns);
        for (int b = 0; b < ins_numBars; ++b)
        {
            int mask = 0;
            int rot = cellSel + (kind == 1 ? 1 : 0);
            if (kind == 3) mask = (1 << ns) - 1;
            else mask = ins_euclid (pc, ns, rot);
            if (mask == 0) mask = 1;
            bool response = (b % 2) == 1;
            int k = 0;
            for (int s = 0; s < ns; ++s)
            {
                bool on = ((mask >> s) & 1) != 0;
                if (kind == 3 && (ins_rv (399, b * 32 + s) % 100) >= 78) on = false;
                if (on)
                {
                    int c = ins_chordAt (b, s);
                    bool strong = ins_isBeat (s);
                    int si = focus;
                    int extra = 0;
                    int len = ins_maxi (6, 24 * ins_pGate / 100);
                    int acc = strong ? 8 : -2;
                    if (kind == 0)
                    {
                        int d = cells.at (cellSel * 4 + (k % 4));
                        if (response) d = 0 - d;
                        si = focus + d;
                        if (response && ins_nextHit (mask, s) <= s) si = ins_nearestChordTone (focus, c);
                        len = ins_maxi (6, ins_mini (ins_nextHit (mask, s) - s, 4) * 24 * ins_pGate / 100);
                    }
                    else if (kind == 1)
                    {
                        if ((k % 2) == 0) si = focus;
                        else si = centerSi + 1 + (ins_rv (392, b * 8 + k) % 4);
                        if (strong) si = ins_nearestChordTone (si, c);
                    }
                    else if (kind == 2)
                    {
                        const int[3] mc = (0, 2, 1);
                        si = centerSi + mc.at (k % 3) + (b % 2);
                        if (strong) si = ins_nearestChordTone (si, c);
                    }
                    else
                    {
                        si = centerSi - 3 + (ins_rv (395, b * 32 + s) % 7);
                        if ((ins_rv (394, b * 32 + s) % 100) < 20) extra = 12;
                        if ((ins_rv (393, b * 32 + s) % 100) < 25) { acc = 24; len = 40; }
                        else len = 14;
                    }
                    si = ins_clampi (si, centerSi - w - 2, centerSi + w + 2);
                    ins_tNote (b, s, ins_tPitchScale (si) + extra, len, acc, k);
                    k += 1;
                }
            }
        }
    }

    void ins_genTrance (int role)
    {
        if (role == 0)      ins_genPluck();
        else if (role == 1) ins_genTLead();
        else if (role == 2) ins_genTBass();
        else if (role == 3) ins_genTArp();
        else
        {
            int sv = ins_pStyle;
            ins_pStyle = 18;
            ins_genDrums();
            ins_pStyle = sv;
        }
    }
'''
rep('    void ins_regenerate()\n', CODE + '\n    void ins_regenerate()\n')
rep('        if (ins_pGen == 5 && ins_imCount > 0) ins_genImport();', '        if (ins_pGen == 8) ins_genTrance (ins_pMode);\n        else if (ins_pGen == 5 && ins_imCount > 0) ins_genImport();')
rep('event param7139 (float v) { ins_pGen = ins_clampi (ins_roundi (v), 0, 7);', 'event param7139 (float v) { ins_pGen = ins_clampi (ins_roundi (v), 0, 8);')
g = re.search(r'input event float param7139 \[\[[^\]]*\]\];', src).group(0)
rep(g, g.replace('max: 7.0', 'max: 8.0').replace('Walk|Permute"', 'Walk|Permute|Trance"'))
rep('[7139, "Insp Generator", 0, 7, 0, "", "sel", ["Classic", "Euclid", "Markov", "Cellular", "L-System", "Import", "Walk", "Permute"]', '[7139, "Insp Generator", 0, 8, 0, "", "sel", ["Classic", "Euclid", "Markov", "Cellular", "L-System", "Import", "Walk", "Permute", "Trance"]', 'idx')
src = src.replace('    // INSPIRATOR10-DSP marker', '    // INSPIRATOR11-DSP marker\n    // INSPIRATOR10-DSP marker', 1)
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
