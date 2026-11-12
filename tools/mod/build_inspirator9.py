#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR9-DSP: more Inspirator functions.
  7141 Chord Bass (Chords: adds the chord root two octaves below the chord, optionally with its octave)
  7142 Drum Chance (drums: probability of every note, downbeats always play)   7143 Ratchet (hat notes split in 32nds)
  7144 Poly (Euclid drums: hat / open hat / percussion run in loops of 12:5:7, 10:7:9 or 14:5:11 steps against the bar)
  7139 Generator gets 6 = Walk (random walk with momentum) and 7 = Permute (a 4-note motif, bar by bar reversed / inverted)"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR9-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

# ---- parameters
P = [(7141, 'Chord Bass', 0, 2, 0, 'Off|Root|Root+Oct', 'Chord Bass'), (7142, 'Drum Chance', 0, 100, 100, None, 'Chance'),
     (7143, 'Ratchet', 0, 100, 0, None, 'Ratchet'), (7144, 'Poly', 0, 3, 0, 'Off|A 12:5:7|B 10:7:9|C 14:5:11', 'Poly')]
VAR = {7141: 'ins_pCBass', 7142: 'ins_pChance', 7143: 'ins_pRatchet', 7144: 'ins_pPoly'}
decl = []; handlers = []; specs = []
for (i, nm, lo, hi, ini, txt, lab) in P:
    t = (', text: "%s"' % txt) if txt else ''
    decl.append('    input event float param%d [[ name: "Insp %s", min: %d.0, max: %d.0, init: %d.0, step: 1.0%s, automatable: false ]];' % (i, nm, lo, hi, ini, t))
    handlers.append('    event param%d (float v) { %s = ins_clampi (ins_roundi (v), %d, %d); ins_dirty = true; }' % (i, VAR[i], lo, hi))
    if txt: specs.append('    [%d, "Insp %s", %d, %d, %d, "", "sel", [%s], 1, "%s", null],' % (i, nm, lo, hi, ini, ', '.join('"%s"' % x for x in txt.split('|')), lab))
    else: specs.append('    [%d, "Insp %s", %d, %d, %d, "", "knb", null, 1, "%s", null],' % (i, nm, lo, hi, ini, lab))
d = re.search(r'    input event float param7140 \[\[[^\]]*\]\];', src).group(0)
rep(d, d + '\n    // INSPIRATOR9-DSP\n' + '\n'.join(decl))
h = '    event param7140 (float v) { ins_pGenVar = ins_clampi (ins_roundi (v), 0, 15); ins_dirty = true; }'
rep(h, h + '\n' + '\n'.join(handlers))
rep('event param7139 (float v) { ins_pGen = ins_clampi (ins_roundi (v), 0, 5);', 'event param7139 (float v) { ins_pGen = ins_clampi (ins_roundi (v), 0, 7);')
g = re.search(r'input event float param7139 \[\[[^\]]*\]\];', src).group(0)
rep(g, g.replace('max: 5.0', 'max: 7.0').replace('Import"', 'Import|Walk|Permute"'))
rep('[7139, "Insp Generator", 0, 5, 0, "", "sel", ["Classic", "Euclid", "Markov", "Cellular", "L-System", "Import"]', '[7139, "Insp Generator", 0, 7, 0, "", "sel", ["Classic", "Euclid", "Markov", "Cellular", "L-System", "Import", "Walk", "Permute"]', 'idx')
s0 = '    [7140, "Insp Gen Variant", 0, 15, 0, "", "knb", null, 1, "Variant", null],'
rep(s0, s0 + '\n' + '\n'.join(specs), 'idx')

# ---- state
rep('    int ins_pGen = 0;\n', '    int ins_pGen = 0;\n    int ins_pCBass = 0;\n    int ins_pChance = 100;\n    int ins_pRatchet = 0;\n    int ins_pPoly = 0;\n')

# ---- voice leading in the chord post-stage
rep('        if (ins_pInv == 0 && ins_pSpread == 0 && ins_pStrum == 0 && ins_pFig == 0) return;\n        int n0 = ins_nCount;',
    '        if (ins_pInv == 0 && ins_pSpread == 0 && ins_pStrum == 0 && ins_pFig == 0 && ins_pCBass == 0) return;\n        int n0 = ins_nCount;')
rep('            if (n > 1 && n <= 8) ins_voiceGroup (i, n);', '            if (n > 1 && n <= 8) ins_voiceGroup (i, n);\n            if (n >= 1 && ins_pCBass > 0) ins_chordBass (i);')
rep('    void ins_postChords()\n', '''    // bass note on the chord root, two octaves below the chord centre (optionally doubled an octave up)
    void ins_chordBass (int start)
    {
        int g = ins_nGrid.at (start);
        int b = g / ins_maxi (1, ins_barTicks);
        int s = (g % ins_maxi (1, ins_barTicks)) / 24;
        int c = ins_chordAt (b, s);
        int rootPc = ins_posMod (ins_pKey + ins_cRoot.at (c), 12);
        int low = 60 + 12 * ins_pOctave - 24;
        int p = low + ins_posMod (rootPc - low, 12);
        int v = ins_clampi (ins_nVel.at (start) - 8, 1, 127);
        ins_rawAdd (g, ins_nOff.at (start), ins_nLen.at (start), p, v);
        if (ins_pCBass >= 2) ins_rawAdd (g, ins_nOff.at (start), ins_nLen.at (start), p + 12, v - 6);
    }

    void ins_postChords()
''')

# ---- generators 6 / 7
rep('        else if (ins_pGen >= 1 && ins_pGen <= 4 && ins_pMode >= 1) ins_genAlt (ins_pMode);', '        else if (ins_pGen >= 1 && ins_pGen != 5 && ins_pMode >= 1) ins_genAlt (ins_pMode);')
rep('''                        else if (gen == 4)
                        {
                            int sym = ins_lsStr.at ((b * ns + s) % ins_maxi (1, ins_lsLen));
                            if (sym == 0) dlt = 1;
                            else if (sym == 1) dlt = -1;
                        }
''', '''                        else if (gen == 4)
                        {
                            int sym = ins_lsStr.at ((b * ns + s) % ins_maxi (1, ins_lsLen));
                            if (sym == 0) dlt = 1;
                            else if (sym == 1) dlt = -1;
                        }
                        else if (gen == 6)
                        {
                            // random walk with momentum: keeps its direction 70 % of the time
                            if ((ins_rv (371, kk) % 100) >= 70) walkDir = 0 - walkDir;
                            dlt = walkDir;
                            if ((ins_rv (372, kk) % 100) < 15) dlt = 2 * walkDir;
                            if ((ins_rv (373, kk) % 100) < 12) dlt = 0;
                        }
                        else if (gen == 7)
                        {
                            // 4-note motif, transformed bar by bar: original, reversed, inverted, inverted + reversed
                            int mi = kk % 4;
                            int tr = b % 4;
                            int pos = mi;
                            if (tr == 1 || tr == 3) pos = 3 - mi;
                            int mv = (ins_rv (374, pos) % 7) - 3;
                            if (tr >= 2) mv = 0 - mv;
                            cur = centerSi + mv;
                        }
''')
rep('        int d1 = 3;\n        int d2 = 3;\n        int kk = 0;\n        int pc = 1 +', '        int d1 = 3;\n        int d2 = 3;\n        int kk = 0;\n        int walkDir = 1;\n        int pc = 1 +')

# ---- Euclid poly drums
rep('''            for (int s = 0; s < ns; ++s)
            {
                int g = b * ins_barTicks + s * 24;
                int cyc = (b % 2) * 32 + s;
                bool strong = ins_isBeat (s);''', '''            if (ins_pGen == 1 && ins_pPoly > 0)
            {
                int l1 = 12; int l2 = 5; int l3 = 7;
                if (ins_pPoly == 2) { l1 = 10; l2 = 7; l3 = 9; }
                else if (ins_pPoly == 3) { l1 = 14; l2 = 5; l3 = 11; }
                int e1 = ins_euclid (ins_clampi (3 + ins_pDensity * (l1 - 3) / 100, 1, l1), l1, rot % 3);
                int e2 = ins_euclid (ins_clampi (1 + ins_pDensity / 40, 1, l2), l2, rot % l2);
                int e3 = ins_euclid (ins_clampi (1 + ins_pComplex / 25, 1, l3), l3, rot % l3);
                hat = 0; open = 0; perc = 0;
                for (int s = 0; s < ns; ++s)
                {
                    int gi = b * ns + s;
                    if (((e1 >> (gi % l1)) & 1) != 0) hat = hat | (1 << s);
                    if (((e2 >> (gi % l2)) & 1) != 0) open = open | (1 << s);
                    if (((e3 >> (gi % l3)) & 1) != 0) perc = perc | (1 << s);
                }
            }
            for (int s = 0; s < ns; ++s)
            {
                int g = b * ins_barTicks + s * 24;
                int cyc = (b % 2) * 32 + s;
                bool strong = ins_isBeat (s);''')

# ---- drum chance + ratchet
rep('    void ins_post()\n', '''    void ins_postDrumsProb()
    {
        if (ins_pChance < 100)
        {
            for (int i = 0; i < ins_nCount; ++i)
                if ((ins_nGrid.at (i) % 96) != 0 && (ins_rv (380, i) % 100) >= ins_pChance) ins_nVel.at (i) = 0;
        }
        if (ins_pRatchet > 0)
        {
            int n0 = ins_nCount;
            int hp = ins_lanePitch.at (3);
            for (int i = 0; i < n0; ++i)
            {
                if (ins_nVel.at (i) > 0 && ins_nPitch.at (i) == hp && ins_nGrid.at (i) + 12 < ins_loopTicks && (ins_rv (381, i) % 100) < ins_pRatchet)
                {
                    ins_rawAdd (ins_nGrid.at (i) + 12, ins_nOff.at (i), 8, hp, ins_nVel.at (i) - 14);
                    if ((ins_rv (382, i) % 100) < ins_pRatchet / 2 && ins_nGrid.at (i) + 18 < ins_loopTicks)
                        ins_rawAdd (ins_nGrid.at (i) + 18, ins_nOff.at (i), 6, hp, ins_nVel.at (i) - 22);
                }
            }
        }
    }

    void ins_post()
''')
rep('        if (ins_pMut > 0) ins_postMutate();', '        if (ins_pMode == 4) ins_postDrumsProb();\n        if (ins_pMut > 0) ins_postMutate();')
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
