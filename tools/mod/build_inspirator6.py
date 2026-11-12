#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR6-DSP: six more Inspirator styles (14 Disco, 15 Bossa Nova, 16 Synthwave, 17 Dubstep, 18 Trance, 19 Drill).
Tables grow from 14 to 20 styles: chordRh / bassRh index = rhVar*60 + style*3 + tier (was *42)."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR6-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src', n=1):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == n, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
for a, b in [('int[56] ins_selMaj;', 'int[80] ins_selMaj;'), ('int[56] ins_selMin;', 'int[80] ins_selMin;'),
             ('int[126] ins_chordRh;', 'int[180] ins_chordRh;'), ('int[126] ins_bassRh;', 'int[180] ins_bassRh;'),
             ('int[112] ins_drumBase;', 'int[160] ins_drumBase;'), ('int[112] ins_drumExtra;', 'int[160] ins_drumExtra;')]:
    rep(a, b)
rep('ins_rhVar (b, 300) * 42 +', 'ins_rhVar (b, 300) * 60 +')
rep('ins_rhVar (b, 310) * 42 +', 'ins_rhVar (b, 310) * 60 +')
def remap(m):
    r = int(m.group(3)); return '%sins_set3 (%s, %d,' % (m.group(1), m.group(2), (r // 14) * 20 + r % 14)
src, n = re.subn(r'(\s)ins_set3 \((\d), (\d+),', remap, src)
assert n == 84, n
new = '\n        // INSPIRATOR6-DSP: styles 14-19 (Disco, Bossa Nova, Synthwave, Dubstep, Trance, Drill)\n'
SEL = {14: ((9, 0, 5, 8), (9, 8, 0, 2)), 15: ((5, 6, 5, 7), (5, 2, 5, 6)), 16: ((0, 5, 10, 8), (8, 10, 0, 8)),
       17: ((11, 0, 5, 8), (11, 8, 8, 10)), 18: ((0, 1, 5, 4), (8, 10, 8, 0)), 19: ((5, 10, 8, 11), (8, 11, 10, 8))}
for s, (a, b) in SEL.items():
    new += '        ins_set4 (2, %d, %s);  ins_set4 (3, %d, %s);\n' % (s, ', '.join(map(str, a)), s, ', '.join(map(str, b)))
CH = {14: [(0x0505, 0x4545, 0x5555), (0x0404, 0x4444, 0x5555), (0x0101, 0x0505, 0x4D4D)],
      15: [(0x0009, 0x0449, 0x1449), (0x0041, 0x0449, 0x1449), (0x0009, 0x0409, 0x1441)],
      16: [(0x0001, 0x0101, 0x1111), (0x0001, 0x0011, 0x1111), (0x0101, 0x1111, 0x5555)],
      17: [(0x0001, 0x0001, 0x0101), (0x0001, 0x0101, 0x0105), (0x0001, 0x0011, 0x0101)],
      18: [(0x0101, 0x5555, 0xDDDD), (0x0001, 0x5555, 0xFFFF), (0x0101, 0x1111, 0x5555)],
      19: [(0x0001, 0x0101, 0x0441), (0x0001, 0x0041, 0x0449), (0x0001, 0x0401, 0x0441)]}
BS = {14: [(0x1111, 0x5555, 0x5555), (0x0505, 0x5555, 0xDDDD), (0x1111, 0x1515, 0x5555)],
      15: [(0x0009, 0x0449, 0x1449), (0x0041, 0x0449, 0x0C49), (0x0009, 0x0049, 0x1441)],
      16: [(0x5555, 0x5555, 0xFFFF), (0x1111, 0x5555, 0x5555), (0x5555, 0xDDDD, 0xFFFF)],
      17: [(0x0001, 0x0011, 0x0C45), (0x0001, 0x0401, 0x0C45), (0x0001, 0x0111, 0x4C45)],
      18: [(0x4444, 0x4444, 0x5555), (0x4444, 0x5555, 0x5555), (0x4444, 0x4C4C, 0xDDDD)],
      19: [(0x0049, 0x0249, 0x4949), (0x0041, 0x0249, 0x4B49), (0x0009, 0x0249, 0x4949)]}
for s in range(14, 20):
    for v in range(3):
        new += '        ins_set3 (0, %d, 0x%04X, 0x%04X, 0x%04X);\n' % ((v * 20 + s,) + CH[s][v])
        new += '        ins_set3 (1, %d, 0x%04X, 0x%04X, 0x%04X);\n' % ((v * 20 + s,) + BS[s][v])
DR = {  # k s cl ch oh rim tom ride
    14: ((0x1111, 0x1010, 0, 0x5555, 0x4444, 0, 0, 0), (0x0000, 0x0200, 0x1010, 0xAAAA, 0x8000, 0, 0, 0)),
    15: ((0x0909, 0, 0, 0x5555, 0, 0x1449, 0, 0), (0x0200, 0, 0, 0xAAAA, 0, 0x0220, 0x0800, 0)),
    16: ((0x1111, 0x1010, 0x1010, 0x5555, 0, 0, 0, 0), (0x0400, 0x8000, 0, 0xAAAA, 0x4000, 0, 0x8800, 0)),
    17: ((0x0001, 0x0100, 0, 0x5555, 0, 0, 0, 0), (0x0400, 0, 0x0100, 0xAAAA, 0x4000, 0, 0, 0)),
    18: ((0x1111, 0, 0x1010, 0, 0x4444, 0, 0, 0), (0, 0x8000, 0, 0xFFFF, 0, 0x2020, 0, 0x5555)),
    19: ((0x0041, 0x0100, 0, 0x5555, 0, 0, 0, 0), (0x2400, 0, 0, 0xAAAA, 0x4000, 0x0020, 0, 0))}
for s, (b, e) in DR.items():
    new += '        ins_dr (0, %d, %s);\n' % (s, ', '.join('0x%04X' % x for x in b))
    new += '        ins_dr (1, %d, %s);\n' % (s, ', '.join('0x%04X' % x for x in e))
anchor = '        ins_dr (1, 13, 0x0001, 0x0000, 0x0000, 0x1111, 0x8800, 0x1010, 0x0000, 0x0000);\n'
rep(anchor, anchor + new)
rep('ins_pStyle = ins_clampi (ins_roundi (v), 0, 13);', 'ins_pStyle = ins_clampi (ins_roundi (v), 0, 19);')
rep('ins_pChordStyle = ins_clampi (x / 2, 0, 13);', 'ins_pChordStyle = ins_clampi (x / 2, 0, 19);')
rep('int x = ins_clampi (ins_roundi (v), 0, 27);', 'int x = ins_clampi (ins_roundi (v), 0, 39);')
m = re.search(r'input event float param7002 \[\[[^\]]*\]\];', src); assert m
rep(m.group(0), m.group(0).replace('max: 13.0', 'max: 19.0').replace('Funk|Dub"', 'Funk|Dub|Disco|Bossa Nova|Synthwave|Dubstep|Trance|Drill"'))
m = re.search(r'input event float param7011 \[\[[^\]]*\]\];', src); assert m
rep(m.group(0), m.group(0).replace('max: 27.0', 'max: 39.0'))
rep('"Funk", "Dub"], 1, "Style"', '"Funk", "Dub", "Disco", "Bossa Nova", "Synthwave", "Dubstep", "Trance", "Drill"], 1, "Style"', 'idx')
rep('[7002, "Insp Style", 0, 13,', '[7002, "Insp Style", 0, 19,', 'idx')
rep('[7011, "Insp Lock Chords", 0, 27,', '[7011, "Insp Lock Chords", 0, 39,', 'idx')
src = src.replace('    // INSPIRATOR5-DSP marker', '    // INSPIRATOR6-DSP marker\n    // INSPIRATOR5-DSP marker', 1)
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
