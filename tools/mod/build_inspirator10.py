#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR10-DSP: genre-typical chord progressions for the styles 9-31.
Every style picks one of 4 progressions per scale type (major / minor) by the Song Seed.  The progression tables grow from 12 to up to 64 rows
(rows are deduplicated, degrees 0-6 = I-VII of the scale)."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'INSPIRATOR10-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
R = {'I': 0, 'II': 1, 'III': 2, 'IV': 3, 'V': 4, 'VI': 5, 'VII': 6}
def prog(t): return tuple(R[x.upper()] for x in t.split())
# style: (4 major progressions, 4 minor progressions)
G = {
 9:  ('I V vi IV|vi IV I V|I vi IV V|IV V I vi', 'i VII VI VII|i iv VII III|i VI III VII|i VII VI v'),                 # Reggaeton
 10: ('I V vi IV|vi IV I V|IV I V vi|I iii vi IV', 'i VI III VII|i VII VI VII|i iv i v|VI VII i i'),                   # Drum & Bass
 11: ('I IV vi V|I vi IV V|IV I V vi|vi IV I V', 'i VI iv VII|i iv VII III|i VII iv v|VI VII i i'),                    # Afrobeats
 12: ('I IV I V|ii V I vi|I vi ii V|IV I IV I', 'i iv i v|i VII iv iv|i iv VII III|i VI VII i'),                       # Funk
 13: ('I I IV IV|I IV I V|I V I IV|I vi I IV', 'i i iv iv|i VII i VII|i VI VII VII|i iv i VII'),                        # Dub
 14: ('I vi ii V|ii V I vi|I IV ii V|IV V iii vi', 'i iv VII III|i VI iv v|i VII VI v|i iv VII VI'),                   # Disco
 15: ('ii V I vi|I vi ii V|iii vi ii V|I IV ii V', 'ii v i i|i iv VII III|i VI ii v|i iv ii v'),                       # Bossa Nova
 16: ('vi IV I V|I V vi IV|I iii IV V|IV V vi vi', 'i VI III VII|i VII VI VII|i iv VI VII|VI VII i i'),                # Synthwave
 17: ('vi IV I V|I V vi IV|I I V V|vi vi IV V', 'i VI III VII|i VII VI VII|i i VI VII|i iv i VII'),                    # Dubstep
 18: ('vi IV I V|I V vi IV|IV I V vi|vi V IV V', 'i VI III VII|i VII VI VII|i VI iv VII|i iv VI VII'),                 # Trance
 19: ('vi IV I V|I V vi IV|I vi IV V|vi vi IV V', 'i VI VII i|i VII VI VII|i iv i VII|i VI III VII'),                  # Drill
 20: ('ii V I vi|I vi IV V|vi IV I V|IV V iii vi', 'i VI III VII|i iv VII III|VI VII i i|i VII VI VII'),               # UK Garage
 21: ('ii V I I|I IV V IV|I vi ii V|ii V I vi', 'i iv v i|i VII VI v|i iv VII III|i VI VII i'),                         # Salsa
 22: ('I IV V IV|I V vi IV|I IV I V|vi IV I V', 'i VI VII i|i VII VI VII|i iv VI v|i III VII VI'),                     # Metal
 23: ('I IV V I|I IV I V|I V IV I|I vi IV V', 'i iv v i|i VI VII i|i VII VI VII|i iv VII III'),                        # Country
 24: ('I IV I V|I I IV V|I IV V IV|I vi IV V', 'i iv i v|i i iv v|i iv v iv|i VI iv v'),                               # Blues
 25: ('I iii IV vi|I IV I IV|vi IV I iii|I vi iii IV', 'i III VI VII|i VI i VI|i iv i iv|VI VII i III'),               # Ambient
 26: ('I IV V IV|I vi IV V|I IV I V|I V IV I', 'i iv v i|i VII VI VII|i VI VII VII|i iv VII III'),                     # Ska
 27: ('ii V I vi|vi IV I V|IV I V vi|I iii vi IV', 'i iv VII III|i VI iv VII|i VII VI v|VI VII i i'),                  # Amapiano
 28: ('I IV V IV|I V vi IV|vi IV I V|I vi IV V', 'i VII VI VII|i VI III VII|i iv i VII|i iv VII III'),                 # Breakbeat
 29: ('I vi ii V|I IV ii V|ii V I vi|IV V iii vi', 'i iv VII III|i VI iv VII|i iv v i|i VII VI v'),                    # Gospel
 30: ('vi IV I V|I V vi IV|IV I V vi|I vi IV V', 'i VI III VII|i VII VI VII|i iv VI VII|VI VII i i'),                  # Hardstyle
 31: ('I V vi IV|vi IV I V|I vi IV V|IV V I vi', 'i VII VI VII|i VI III VII|i iv VII III|i VII VI v'),                 # Moombahton
}
# existing progression rows
rows = {0: {}, 1: {}}
for m in re.finditer(r'ins_set4 \(([01]), (\d+), (\d), (\d), (\d), (\d)\)', src):
    rows[int(m.group(1))][int(m.group(2))] = tuple(int(m.group(k)) for k in range(3, 7))
for w in (0, 1): assert len(rows[w]) == 12, (w, len(rows[w]))
def row_of(w, p):
    for r, v in rows[w].items():
        if v == p: return r
    r = max(rows[w]) + 1
    rows[w][r] = p
    return r
new = '\n        // INSPIRATOR10-DSP: genre progressions\n'
sel = ''
for st, (mj, mn) in sorted(G.items()):
    a = [row_of(0, prog(t)) for t in mj.split('|')]
    b = [row_of(1, prog(t)) for t in mn.split('|')]
    sel += '        ins_set4 (2, %d, %s);  ins_set4 (3, %d, %s);\n' % (st, ', '.join(map(str, a)), st, ', '.join(map(str, b)))
for w in (0, 1):
    for r in sorted(rows[w]):
        if r >= 12: new += '        ins_set4 (%d, %d, %s);\n' % (w, r, ', '.join(map(str, rows[w][r])))
assert max(rows[0]) < 64 and max(rows[1]) < 64
anchor = '        ins_dr (1, 31, 0x0400, 0x4000, 0x0101, 0xAAAA, 0x2000, 0x0220, 0x0000, 0x0000);\n'
rep(anchor, anchor + new + sel)
rep('int[48] ins_progMaj;', 'int[256] ins_progMaj;'); rep('int[48] ins_progMin;', 'int[256] ins_progMin;')
src = src.replace('    // INSPIRATOR8-DSP marker', '    // INSPIRATOR10-DSP marker\n    // INSPIRATOR8-DSP marker', 1)
open(path, 'w').write(src)
print('applied; rows maj %d, min %d' % (len(rows[0]), len(rows[1])))
