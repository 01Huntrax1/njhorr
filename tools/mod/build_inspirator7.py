#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR7-DSP: six more Inspirator styles (20 UK Garage, 21 Salsa, 22 Metal, 23 Country, 24 Blues, 25 Ambient).
Tables grow from 20 to 26 styles: chordRh / bassRh index = rhVar*78 + style*3 + tier (was *60)."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR7-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src', n=1):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == n, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
for a, b in [('int[80] ins_selMaj;', 'int[104] ins_selMaj;'), ('int[80] ins_selMin;', 'int[104] ins_selMin;'),
             ('int[180] ins_chordRh;', 'int[234] ins_chordRh;'), ('int[180] ins_bassRh;', 'int[234] ins_bassRh;'),
             ('int[160] ins_drumBase;', 'int[208] ins_drumBase;'), ('int[160] ins_drumExtra;', 'int[208] ins_drumExtra;')]:
    rep(a, b)
rep('ins_rhVar (b, 300) * 60 +', 'ins_rhVar (b, 300) * 78 +')
rep('ins_rhVar (b, 310) * 60 +', 'ins_rhVar (b, 310) * 78 +')
def remap(m):
    r = int(m.group(3)); return '%sins_set3 (%s, %d,' % (m.group(1), m.group(2), (r // 20) * 26 + r % 20)
src, n = re.subn(r'(\s)ins_set3 \((\d), (\d+),', remap, src)
assert n == 120, n
new = '\n        // INSPIRATOR7-DSP: styles 20-25 (UK Garage, Salsa, Metal, Country, Blues, Ambient)\n'
SEL = {20: ((9, 5, 8, 10), (8, 10, 9, 8)), 21: ((9, 0, 9, 5), (8, 9, 8, 10)), 22: ((0, 3, 5, 8), (8, 10, 8, 0)),
       23: ((8, 0, 5, 3), (8, 5, 10, 2)), 24: ((8, 8, 8, 9), (9, 8, 8, 10)), 25: ((11, 10, 0, 5), (11, 10, 8, 11))}
for s, (a, b) in SEL.items():
    new += '        ins_set4 (2, %d, %s);  ins_set4 (3, %d, %s);\n' % (s, ', '.join(map(str, a)), s, ', '.join(map(str, b)))
CH = {20: [(0x0009, 0x0249, 0x4949), (0x0009, 0x0049, 0x2449), (0x0041, 0x0449, 0x4C49)],
      21: [(0x0049, 0x2449, 0x6D6D), (0x0049, 0x0249, 0x2D2D), (0x0009, 0x0449, 0x1449)],
      22: [(0x0001, 0x1111, 0x5555), (0x0001, 0x0101, 0x1111), (0x0101, 0x1111, 0x5555)],
      23: [(0x0101, 0x1111, 0x5555), (0x0101, 0x1111, 0x1515), (0x0101, 0x5151, 0x5555)],
      24: [(0x0101, 0x0505, 0x5555), (0x0001, 0x0101, 0x0505), (0x0101, 0x1111, 0x5555)],
      25: [(0x0001, 0x0001, 0x0101), (0x0001, 0x0101, 0x0101), (0x0001, 0x0001, 0x0011)]}
BS = {20: [(0x0401, 0x0C41, 0x4C45), (0x0401, 0x0441, 0x4C41), (0x0001, 0x0401, 0x0C45)],
      21: [(0x0201, 0x0A49, 0x4A4B), (0x0141, 0x0949, 0x4949), (0x0201, 0x0A41, 0x4A49)],
      22: [(0x1111, 0x5555, 0x5555), (0x5555, 0x5555, 0xFFFF), (0x1111, 0x1515, 0x5555)],
      23: [(0x0101, 0x1111, 0x1515), (0x0101, 0x1111, 0x5555), (0x0101, 0x0111, 0x1515)],
      24: [(0x1111, 0x5555, 0x5D5D), (0x1111, 0x5555, 0x5555), (0x0101, 0x1111, 0x5555)],
      25: [(0x0001, 0x0001, 0x0101), (0x0001, 0x0101, 0x0101), (0x0001, 0x0011, 0x0101)]}
for s in range(20, 26):
    for v in range(3):
        new += '        ins_set3 (0, %d, 0x%04X, 0x%04X, 0x%04X);\n' % ((v * 26 + s,) + CH[s][v])
        new += '        ins_set3 (1, %d, 0x%04X, 0x%04X, 0x%04X);\n' % ((v * 26 + s,) + BS[s][v])
DR = {  # k s cl ch oh rim tom ride
    20: ((0x0401, 0x1010, 0, 0x5555, 0, 0, 0, 0), (0x0020, 0x0480, 0, 0xAAAA, 0x4000, 0x0200, 0, 0)),
    21: ((0x0111, 0, 0, 0x5555, 0, 0x1449, 0x2424, 0x5555), (0x2000, 0, 0, 0xAAAA, 0, 0x0220, 0x4848, 0xAAAA)),
    22: ((0x5555, 0x1010, 0, 0x1111, 0, 0, 0, 0), (0xAAAA, 0, 0, 0x4444, 0, 0, 0x8888, 0)),
    23: ((0x0101, 0x1010, 0, 0x1111, 0, 0, 0, 0), (0x0404, 0x4040, 0, 0x4444, 0, 0x0200, 0, 0)),
    24: ((0x0101, 0x1010, 0, 0x5555, 0, 0, 0, 0), (0x0400, 0x0040, 0, 0xAAAA, 0x4000, 0, 0, 0)),
    25: ((0x0001, 0, 0, 0, 0, 0, 0, 0x1111), (0, 0x0100, 0, 0, 0, 0x2020, 0, 0x4444))}
for s, (b, e) in DR.items():
    new += '        ins_dr (0, %d, %s);\n' % (s, ', '.join('0x%04X' % x for x in b))
    new += '        ins_dr (1, %d, %s);\n' % (s, ', '.join('0x%04X' % x for x in e))
anchor = '        ins_dr (1, 19, 0x2400, 0x0000, 0x0000, 0xAAAA, 0x4000, 0x0020, 0x0000, 0x0000);\n'
rep(anchor, anchor + new)
rep('ins_pStyle = ins_clampi (ins_roundi (v), 0, 19);', 'ins_pStyle = ins_clampi (ins_roundi (v), 0, 25);')
rep('ins_pChordStyle = ins_clampi (x / 2, 0, 19);', 'ins_pChordStyle = ins_clampi (x / 2, 0, 25);')
rep('int x = ins_clampi (ins_roundi (v), 0, 39);', 'int x = ins_clampi (ins_roundi (v), 0, 51);')
m = re.search(r'input event float param7002 \[\[[^\]]*\]\];', src); assert m
rep(m.group(0), m.group(0).replace('max: 19.0', 'max: 25.0').replace('Trance|Drill"', 'Trance|Drill|UK Garage|Salsa|Metal|Country|Blues|Ambient"'))
m = re.search(r'input event float param7011 \[\[[^\]]*\]\];', src); assert m
rep(m.group(0), m.group(0).replace('max: 39.0', 'max: 51.0'))
rep('"Trance", "Drill"], 1, "Style"', '"Trance", "Drill", "UK Garage", "Salsa", "Metal", "Country", "Blues", "Ambient"], 1, "Style"', 'idx')
rep('[7002, "Insp Style", 0, 19,', '[7002, "Insp Style", 0, 25,', 'idx')
rep('[7011, "Insp Lock Chords", 0, 39,', '[7011, "Insp Lock Chords", 0, 51,', 'idx')
src = src.replace('    // INSPIRATOR6-DSP marker', '    // INSPIRATOR7-DSP marker\n    // INSPIRATOR6-DSP marker', 1)
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
