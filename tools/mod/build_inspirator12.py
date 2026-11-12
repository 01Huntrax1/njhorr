#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR12-DSP: Generator 9 = Genre.  The Trance engine (build_inspirator11.py) with per-style tables for ALL 32 styles:
  pluck rhythms (4 per style), bass rhythms (4), arpeggio pattern + step rate (4), lead kinds (4) - Variant % 4 picks one of the four,
  Variant / 4 is the octave figure (bass) or the phrase cell (lead).  Drums use the style's own kit."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR12-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
H = lambda s: [int(x, 16) for x in s.split()]
PLUCK = """1111 5555 4949 0505|5555 5151 1111 4545|0101 0401 4141 0141|0101 0001 0111 0505|0101 4949 0505 0441|4444 2424 4B4B 0909|2222 4444 AAAA 0A0A|0049 0449 1449 2489
0249 0409 4449 0821|0049 4849 0009 0849|0001 0401 0101 0505|0049 0249 2449 4949|0105 0545 4D4D 2565|4444 0404 4C4C 4040|4545 5555 5D5D 4444|1449 0449 0049 1441
1111 5555 0101 5151|0001 0101 0105 0011|4444 5555 4949 EEEE|0001 0441 0449 0101|0249 4949 0449 4C49|2449 0249 6D6D 1449|1111 5555 0101 5757|1111 5555 0101 1515
0505 5555 0101 5D5D|0001 0101 0011 0001|4444 4C4C 0404 5454|0249 4449 0449 2449|0101 0505 0405 5555|0549 5D5D 0101 4949|1111 0101 4444 5555|0049 4849 0009 0849""".replace('\n', '|').split('|')
BASS = """0101 1111 5555 0141|5555 1111 5757 0101|0401 0481 0141 4C81|0001 0081 0401 0C01|0101 0141 0505 0909|4444 5555 6666 4B4B|EEEE 4444 2A2A AAAA|1111 1111 5555 1515
0401 0481 0C41 2421|0049 4849 0849 4B49|0401 0481 0C81 4C85|0141 0949 0541 4949|0405 0C45 4D45 1445|0101 0141 0103 0949|5555 DDDD 1111 5D5D|1449 0449 0009 1041
5555 FFFF 1111 7777|0001 0011 0C45 0401|EEEE 4444 DDDD EEEE|0049 0249 4949 0041|0401 0C41 4C45 0441|0A49 0201 4A4B 0949|5555 1111 FFFF 7777|0101 1111 1515 0111
1111 5555 5D5D 1515|0001 0101 0001 1111|1111 5555 5D5D 1515|0541 0109 4D49 0141|0405 0C45 4D45 0401|1111 0101 1D1D 5555|4444 5555 EEEE 4C4C|0049 4849 0849 4B49""".replace('\n', '|').split('|')
ARP = """0 5 1 7|0 5 7 13|1 7 5 0|0 11 6 1|0 7 1 5|11 12 7 0|11 4 14 12|0 9 10 6|9 10 2 7|0 7 5 1|11 3 6 4|0 7 2 9|11 8 1 2|0 5 7 11|8 11 3 12|9 10 6 0
0 2 6 7|11 14 15 3|0 3 7 11|14 11 5 1|10 1 13 11|6 9 10 2|4 11 6 13|0 5 7 1|0 5 1 7|6 9 15 2|5 1 7 0|9 10 2 13|11 1 7 3|9 6 10 0|11 4 12 3|0 7 5 1""".replace('\n', '|').split('|')
RATE = [2, 2, 2, 1, 2, 1, 1, 2, 2, 2, 1, 2, 1, 2, 1, 2, 1, 1, 1, 1, 1, 2, 1, 2, 2, 2, 2, 2, 1, 2, 1, 2]
LEAD = """0 1 0 2|0 2 1 0|2 0 2 1|2 2 1 0|0 2 0 1|1 2 3 0|3 2 1 2|0 0 2 1|0 2 0 1|0 2 1 0|2 1 3 0|0 2 0 1|2 3 0 2|2 0 1 2|0 1 0 2|0 0 2 1
1 0 2 3|3 2 1 0|0 1 2 3|2 1 2 0|0 2 1 3|0 2 0 1|2 0 1 2|0 0 1 2|0 3 0 2|1 0 2 1|0 2 0 1|0 2 1 0|3 2 0 1|0 0 1 2|1 0 2 3|0 2 1 0""".replace('\n', '|').split('|')
assert len(PLUCK) == len(BASS) == len(ARP) == len(LEAD) == 32, (len(PLUCK), len(BASS), len(ARP), len(LEAD))
def arr(name, rows, hexa):
    vals = []
    for r in rows:
        vals += [('0x%04X' % int(x, 16)) if hexa else x for x in r.split()]
    assert len(vals) == 128, name
    return '        const int[128] t = (%s);\n        return t.at (i);' % ', '.join(vals)
fn = ''
for nm, rows, hx in (('Pluck', PLUCK, True), ('Bass', BASS, True), ('Arp', ARP, False), ('Lead', LEAD, False)):
    fn += '    int ins_g%s (int i)\n    {\n%s\n    }\n\n' % (nm, arr(nm, rows, hx))
fn += '    int ins_gRate (int sty)\n    {\n        const int[32] t = (%s);\n        return t.at (sty);\n    }\n\n' % ', '.join(map(str, RATE))
rep('    // ---- INSPIRATOR11-DSP: Trance generator family ----\n', '    // ---- INSPIRATOR12-DSP: per-style tables for the Genre generator ----\n    int ins_gSty = 0;\n\n' + fn + '    // ---- INSPIRATOR11-DSP: Trance generator family ----\n')
# pluck
rep('int mask = ins_expandMask (pats.at (ins_pGenVar % 16));', 'int mask = ins_expandMask (pats.at (ins_pGenVar % 16));\n            if (ins_gSty != 0) mask = ins_expandMask (ins_gPluck (ins_pStyle * 4 + (ins_pGenVar % 4)));')
# bass
rep('        int type = ins_pGenVar % 4;\n        int opat = ins_pGenVar / 4;', '        int type = ins_pGenVar % 4;\n        int opat = ins_pGenVar / 4;\n        int bmask = 0;\n        if (ins_gSty != 0) { type = 0; bmask = ins_expandMask (ins_gBass (ins_pStyle * 4 + (ins_pGenVar % 4))); }')
rep('                if (hit && (ins_rv (397, b * 32 + s) % 100) >= 55', '                if (ins_gSty != 0) hit = ((bmask >> s) & 1) != 0;\n                if (hit && (ins_rv (397, b * 32 + s) % 100) >= 55')
rep('                    int len = ins_maxi (6, 24 * ins_pGate / 100);\n                    if (type == 1) len = ins_maxi (6, 36 * ins_pGate / 100);', '                    int len = ins_maxi (6, 24 * ins_pGate / 100);\n                    if (type == 1) len = ins_maxi (6, 36 * ins_pGate / 100);\n                    if (ins_gSty != 0) len = ins_maxi (6, ins_mini (ins_nextHit (bmask, s) - s, 4) * 24 * ins_pGate / 100);')
# arp
rep('        int pt = ins_pGenVar % 16;\n        int base = 60 + 12 * ins_pOctave - 5;', '        int pt = ins_pGenVar % 16;\n        int rate = 1;\n        if (ins_gSty != 0) { pt = ins_gArp (ins_pStyle * 4 + (ins_pGenVar % 4)); rate = ins_gRate (ins_pStyle); }\n        int base = 60 + 12 * ins_pOctave - 5;')
rep('                if ((ins_rv (398, b * 32 + s) % 100) < 40 + ins_pDensity * 60 / 100)', '                if ((s % rate) == 0 && (ins_rv (398, b * 32 + s) % 100) < 40 + ins_pDensity * 60 / 100)')
rep('ins_tNote (b, s, p, ins_maxi (6, 24 * ins_pGate / 100), acc, s);', 'ins_tNote (b, s, p, ins_maxi (6, rate * 24 * ins_pGate / 100), acc, s);')
# lead
rep('        int kind = ins_pGenVar / 4;\n        int cellSel = ins_pGenVar % 4;', '        int kind = ins_pGenVar / 4;\n        int cellSel = ins_pGenVar % 4;\n        if (ins_gSty != 0) { kind = ins_gLead (ins_pStyle * 4 + (ins_pGenVar % 4)); cellSel = ins_pGenVar / 4; }')
rep('            int rot = cellSel + (kind == 1 ? 1 : 0);', '            int rot = cellSel + (kind == 1 ? 1 : 0);\n            if (ins_gSty != 0) rot += (ins_pStyle % 5) + (ins_pStyle / 8);')
# drums / dispatch
rep('        else\n        {\n            int sv = ins_pStyle;\n            ins_pStyle = 18;', '        else if (ins_gSty != 0) ins_genDrums();\n        else\n        {\n            int sv = ins_pStyle;\n            ins_pStyle = 18;')
rep('        if (ins_pGen == 8) ins_genTrance (ins_pMode);', '        if (ins_pGen == 8 || ins_pGen == 9)\n        {\n            ins_gSty = ins_pGen == 9 ? 1 : 0;\n            ins_genTrance (ins_pMode);\n        }')
rep('event param7139 (float v) { ins_pGen = ins_clampi (ins_roundi (v), 0, 8);', 'event param7139 (float v) { ins_pGen = ins_clampi (ins_roundi (v), 0, 9);')
g = re.search(r'input event float param7139 \[\[[^\]]*\]\];', src).group(0)
rep(g, g.replace('max: 8.0', 'max: 9.0').replace('Permute|Trance"', 'Permute|Trance|Genre"'))
rep('[7139, "Insp Generator", 0, 8, 0, "", "sel", ["Classic", "Euclid", "Markov", "Cellular", "L-System", "Import", "Walk", "Permute", "Trance"]', '[7139, "Insp Generator", 0, 9, 0, "", "sel", ["Classic", "Euclid", "Markov", "Cellular", "L-System", "Import", "Walk", "Permute", "Trance", "Genre"]', 'idx')
src = src.replace('    // INSPIRATOR11-DSP marker', '    // INSPIRATOR12-DSP marker\n    // INSPIRATOR11-DSP marker', 1)
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
