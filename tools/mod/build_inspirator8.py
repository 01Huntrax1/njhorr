#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR8-DSP: six more Inspirator styles (26 Ska, 27 Amapiano, 28 Breakbeat, 29 Gospel, 30 Hardstyle, 31 Moombahton).
Tables grow from 26 to 32 styles: chordRh / bassRh index = rhVar*96 + style*3 + tier (was *78)."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR8-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src', n=1):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == n, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
for a, b in [('int[104] ins_selMaj;', 'int[128] ins_selMaj;'), ('int[104] ins_selMin;', 'int[128] ins_selMin;'),
             ('int[234] ins_chordRh;', 'int[288] ins_chordRh;'), ('int[234] ins_bassRh;', 'int[288] ins_bassRh;'),
             ('int[208] ins_drumBase;', 'int[256] ins_drumBase;'), ('int[208] ins_drumExtra;', 'int[256] ins_drumExtra;')]:
    rep(a, b)
rep('ins_rhVar (b, 300) * 78 +', 'ins_rhVar (b, 300) * 96 +')
rep('ins_rhVar (b, 310) * 78 +', 'ins_rhVar (b, 310) * 96 +')
def remap(m):
    r = int(m.group(3)); return '%sins_set3 (%s, %d,' % (m.group(1), m.group(2), (r // 26) * 32 + r % 26)
src, n = re.subn(r'(\s)ins_set3 \((\d), (\d+),', remap, src)
assert n == 156, n
new = '\n        // INSPIRATOR8-DSP: styles 26-31 (Ska, Amapiano, Breakbeat, Gospel, Hardstyle, Moombahton)\n'
SEL = {26: ((8, 0, 8, 5), (9, 8, 8, 10)), 27: ((9, 10, 0, 5), (8, 10, 9, 11)), 28: ((0, 3, 8, 5), (8, 0, 10, 8)),
       29: ((0, 5, 9, 0), (8, 9, 10, 8)), 30: ((0, 5, 10, 8), (8, 10, 8, 0)), 31: ((5, 10, 8, 0), (8, 10, 0, 8))}
for s, (a, b) in SEL.items():
    new += '        ins_set4 (2, %d, %s);  ins_set4 (3, %d, %s);\n' % (s, ', '.join(map(str, a)), s, ', '.join(map(str, b)))
CH = {26: [(0x0404, 0x4444, 0x5454), (0x0404, 0x4444, 0x4C4C), (0x0400, 0x0404, 0x4444)],
      27: [(0x0049, 0x0249, 0x2449), (0x0009, 0x0449, 0x2489), (0x0041, 0x0249, 0x4949)],
      28: [(0x0001, 0x0101, 0x0505), (0x0001, 0x0401, 0x0505), (0x0101, 0x0505, 0x5555)],
      29: [(0x0101, 0x0549, 0x5D5D), (0x0009, 0x0449, 0x5555), (0x0101, 0x1111, 0x5555)],
      30: [(0x0001, 0x0101, 0x1111), (0x0001, 0x0011, 0x1111), (0x0101, 0x1111, 0x5555)],
      31: [(0x0009, 0x0049, 0x4949), (0x0009, 0x0089, 0x4889), (0x0001, 0x0049, 0x2449)]}
BS = {26: [(0x1111, 0x5555, 0x5555), (0x1111, 0x5555, 0x5D5D), (0x0101, 0x1111, 0x5555)],
      27: [(0x0109, 0x0549, 0x4D49), (0x0101, 0x0149, 0x4949), (0x0109, 0x0541, 0x4D45)],
      28: [(0x0405, 0x0C45, 0x4D45), (0x0401, 0x0C45, 0x4C45), (0x0405, 0x0405, 0x5D45)],
      29: [(0x0101, 0x1111, 0x1D1D), (0x0101, 0x1111, 0x5555), (0x0101, 0x0111, 0x1515)],
      30: [(0x4444, 0x4444, 0x5555), (0x4444, 0x5555, 0x5555), (0x4444, 0x4C4C, 0xDDDD)],
      31: [(0x0049, 0x0849, 0x4B49), (0x0009, 0x0849, 0x4849), (0x0041, 0x0441, 0x4C49)]}
for s in range(26, 32):
    for v in range(3):
        new += '        ins_set3 (0, %d, 0x%04X, 0x%04X, 0x%04X);\n' % ((v * 32 + s,) + CH[s][v])
        new += '        ins_set3 (1, %d, 0x%04X, 0x%04X, 0x%04X);\n' % ((v * 32 + s,) + BS[s][v])
DR = {  # k s cl ch oh rim tom ride
    26: ((0x1111, 0x1010, 0, 0x5555, 0, 0, 0, 0), (0, 0, 0, 0xAAAA, 0x4000, 0x0200, 0, 0)),
    27: ((0x1111, 0, 0x1010, 0x5555, 0, 0, 0, 0), (0x0400, 0, 0x0808, 0xAAAA, 0x4000, 0x0420, 0x0100, 0)),
    28: ((0x0405, 0x1090, 0, 0x5555, 0, 0, 0, 0), (0x2000, 0x4400, 0, 0xAAAA, 0x4000, 0, 0, 0)),
    29: ((0x0101, 0x1010, 0, 0x5555, 0, 0, 0, 0), (0x0404, 0, 0x1010, 0, 0x4000, 0x0200, 0x8000, 0)),
    30: ((0x1111, 0, 0x1010, 0, 0x4444, 0, 0, 0), (0x0008, 0x8000, 0, 0x5555, 0, 0x2020, 0, 0)),
    31: ((0x1111, 0x0848, 0, 0x5555, 0, 0, 0, 0), (0x0400, 0x4000, 0x0101, 0xAAAA, 0x2000, 0x0220, 0, 0))}
for s, (b, e) in DR.items():
    new += '        ins_dr (0, %d, %s);\n' % (s, ', '.join('0x%04X' % x for x in b))
    new += '        ins_dr (1, %d, %s);\n' % (s, ', '.join('0x%04X' % x for x in e))
anchor = '        ins_dr (1, 25, 0x0000, 0x0100, 0x0000, 0x0000, 0x0000, 0x2020, 0x0000, 0x4444);\n'
rep(anchor, anchor + new)
rep('ins_pStyle = ins_clampi (ins_roundi (v), 0, 25);', 'ins_pStyle = ins_clampi (ins_roundi (v), 0, 31);')
rep('ins_pChordStyle = ins_clampi (x / 2, 0, 25);', 'ins_pChordStyle = ins_clampi (x / 2, 0, 31);')
rep('int x = ins_clampi (ins_roundi (v), 0, 51);', 'int x = ins_clampi (ins_roundi (v), 0, 63);')
m = re.search(r'input event float param7002 \[\[[^\]]*\]\];', src); assert m
rep(m.group(0), m.group(0).replace('max: 25.0', 'max: 31.0').replace('Blues|Ambient"', 'Blues|Ambient|Ska|Amapiano|Breakbeat|Gospel|Hardstyle|Moombahton"'))
m = re.search(r'input event float param7011 \[\[[^\]]*\]\];', src); assert m
rep(m.group(0), m.group(0).replace('max: 51.0', 'max: 63.0'))
rep('"Blues", "Ambient"], 1, "Style"', '"Blues", "Ambient", "Ska", "Amapiano", "Breakbeat", "Gospel", "Hardstyle", "Moombahton"], 1, "Style"', 'idx')
rep('[7002, "Insp Style", 0, 25,', '[7002, "Insp Style", 0, 31,', 'idx')
rep('[7011, "Insp Lock Chords", 0, 51,', '[7011, "Insp Lock Chords", 0, 63,', 'idx')
src = src.replace('    // INSPIRATOR7-DSP marker', '    // INSPIRATOR8-DSP marker\n    // INSPIRATOR7-DSP marker', 1)
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
