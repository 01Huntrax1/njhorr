#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR5-DSP: five more Inspirator styles (9 Reggaeton, 10 Drum & Bass, 11 Afrobeats, 12 Funk, 13 Dub).
Tables grow from 9 to 14 styles: chordRh / bassRh index = rhVar*42 + style*3 + tier (was *27); progressions get 4 more rows (8-11)."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor'); ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR5-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src', n=1):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == n, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
for a, b in [('int[32] ins_progMaj;', 'int[48] ins_progMaj;'), ('int[32] ins_progMin;', 'int[48] ins_progMin;'),
             ('int[36] ins_selMaj;', 'int[56] ins_selMaj;'), ('int[36] ins_selMin;', 'int[56] ins_selMin;'),
             ('int[81] ins_chordRh;', 'int[126] ins_chordRh;'), ('int[81] ins_bassRh;', 'int[126] ins_bassRh;'),
             ('int[72] ins_drumBase;', 'int[112] ins_drumBase;'), ('int[72] ins_drumExtra;', 'int[112] ins_drumExtra;')]:
    rep(a, b)
rep('ins_rhVar (b, 300) * 27 +', 'ins_rhVar (b, 300) * 42 +')
rep('ins_rhVar (b, 310) * 27 +', 'ins_rhVar (b, 310) * 42 +')
# remap existing rhythm rows: row = rhVar*9 + style  ->  rhVar*14 + style
def remap(m):
    r = int(m.group(3)); return '%sins_set3 (%s, %d,' % (m.group(1), m.group(2), (r // 9) * 14 + r % 9)
src, n = re.subn(r'(\s)ins_set3 \((\d), (\d+),', remap, src)
assert n == 54, n
sets = {  # style: (prog sel maj, sel min)
}
new = '''
        // INSPIRATOR5-DSP: styles 9-13 (Reggaeton, Drum & Bass, Afrobeats, Funk, Dub)
        ins_set4 (0, 8, 0, 3, 0, 4);   ins_set4 (0, 9, 1, 4, 0, 0);   ins_set4 (0, 10, 0, 2, 3, 3);  ins_set4 (0, 11, 0, 0, 3, 3);
        ins_set4 (1, 8, 0, 6, 5, 6);   ins_set4 (1, 9, 0, 3, 0, 4);   ins_set4 (1, 10, 0, 5, 2, 6);  ins_set4 (1, 11, 0, 0, 5, 5);
        ins_set4 (2, 9, 5, 10, 8, 0);   ins_set4 (3, 9, 8, 10, 0, 2);
        ins_set4 (2, 10, 8, 9, 11, 5);  ins_set4 (3, 10, 8, 10, 11, 9);
        ins_set4 (2, 11, 10, 0, 5, 8);  ins_set4 (3, 11, 10, 8, 0, 9);
        ins_set4 (2, 12, 9, 8, 4, 0);   ins_set4 (3, 12, 9, 8, 10, 2);
        ins_set4 (2, 13, 11, 0, 8, 5);  ins_set4 (3, 13, 11, 8, 0, 10);
'''
CH = {9: [(0x0009, 0x0049, 0x4949), (0x0009, 0x0089, 0x4889), (0x0001, 0x0049, 0x2449)],
      10: [(0x0001, 0x0001, 0x0101), (0x0001, 0x0041, 0x0101), (0x0001, 0x0401, 0x0441)],
      11: [(0x0009, 0x0049, 0x2449), (0x0041, 0x0249, 0x4949), (0x0009, 0x0409, 0x2489)],
      12: [(0x0105, 0x0545, 0x4D4D), (0x0021, 0x0525, 0x2565), (0x0101, 0x1141, 0x5959)],
      13: [(0x0404, 0x4444, 0x4C4C), (0x0404, 0x4444, 0xCCCC), (0x0400, 0x0404, 0x4444)]}
BS = {9: [(0x0049, 0x4849, 0x4949), (0x0009, 0x0849, 0x4B49), (0x0041, 0x0441, 0x4C49)],
      10: [(0x0401, 0x0481, 0x4C81), (0x0401, 0x0C41, 0x4C45), (0x0001, 0x0401, 0x4489)],
      11: [(0x0141, 0x0949, 0x4949), (0x0101, 0x0541, 0x2949), (0x0009, 0x0149, 0x4B49)],
      12: [(0x0405, 0x0C45, 0x4D4D), (0x0401, 0x1445, 0x5C5D), (0x0105, 0x0505, 0x4D45)],
      13: [(0x0101, 0x0141, 0x0949), (0x0001, 0x0101, 0x0501), (0x0101, 0x0105, 0x2145)]}
for s in range(9, 14):
    for v in range(3):
        new += '        ins_set3 (0, %d, 0x%04X, 0x%04X, 0x%04X);\n' % ((v * 14 + s,) + CH[s][v])
        new += '        ins_set3 (1, %d, 0x%04X, 0x%04X, 0x%04X);\n' % ((v * 14 + s,) + BS[s][v])
DR = {  # style: (base, extra) = k s cl ch oh rim tom ride
    9:  ((0x1111, 0x4848, 0, 0x5555, 0, 0, 0, 0), (0x0408, 0x0020, 0, 0xAAAA, 0x2000, 0x0210, 0, 0)),
    10: ((0x0401, 0x1010, 0, 0x5555, 0, 0, 0, 0), (0x2800, 0x0480, 0, 0xAAAA, 0x4000, 0, 0, 0)),
    11: ((0x0141, 0x0808, 0, 0x5555, 0, 0x2492, 0, 0), (0x4004, 0x0020, 0, 0xAAAA, 0x0200, 0, 0x1000, 0)),
    12: ((0x0405, 0x1010, 0, 0x5555, 0, 0, 0, 0), (0x2008, 0x4480, 0, 0xAAAA, 0x2000, 0, 0, 0)),
    13: ((0x0100, 0x0100, 0, 0x4444, 0, 0, 0, 0), (0x0001, 0, 0, 0x1111, 0x8800, 0x1010, 0, 0))}
for s, (b, e) in DR.items():
    new += '        ins_dr (0, %d, %s);\n' % (s, ', '.join('0x%04X' % x for x in b))
    new += '        ins_dr (1, %d, %s);\n' % (s, ', '.join('0x%04X' % x for x in e))
anchor = '        ins_dr (1, 8, 0x2888, 0x8280, 0x1010, 0xAAAA, 0x4000, 0x0804, 0x0000, 0x0000);\n'
rep(anchor, anchor + new)
rep('event param7002  (float v) { ins_pStyle = ins_clampi (ins_roundi (v), 0, 8);', 'event param7002  (float v) { ins_pStyle = ins_clampi (ins_roundi (v), 0, 13);')
rep('ins_pChordStyle = ins_clampi (x / 2, 0, 8);', 'ins_pChordStyle = ins_clampi (x / 2, 0, 13);')
rep('int x = ins_clampi (ins_roundi (v), 0, 17);', 'int x = ins_clampi (ins_roundi (v), 0, 27);')
m = re.search(r'input event float param7002 \[\[[^\]]*\]\];', src); assert m
rep(m.group(0), m.group(0).replace('max: 8.0', 'max: 13.0').replace('Neo-Soul"', 'Neo-Soul|Reggaeton|Drum & Bass|Afrobeats|Funk|Dub"'))
m = re.search(r'input event float param7011 \[\[[^\]]*\]\];', src); assert m
rep(m.group(0), m.group(0).replace('max: 17.0', 'max: 27.0'))
rep('[7002, "Insp Style", 0, 8, 0, "", "sel", ["Pop", "Rock", "Hip-Hop", "Trap", "Lo-Fi", "House", "Techno", "Jazz", "Neo-Soul"]',
    '[7002, "Insp Style", 0, 13, 0, "", "sel", ["Pop", "Rock", "Hip-Hop", "Trap", "Lo-Fi", "House", "Techno", "Jazz", "Neo-Soul", "Reggaeton", "Drum & Bass", "Afrobeats", "Funk", "Dub"]', 'idx')
rep('[7011, "Insp Lock Chords", 0, 17,', '[7011, "Insp Lock Chords", 0, 27,', 'idx')
src = src.replace('    // ---- INSPIRATOR3-DSP', '    // INSPIRATOR5-DSP marker\n    // ---- INSPIRATOR3-DSP', 1)
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
