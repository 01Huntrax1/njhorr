#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR2-DSP: post-stage for the Inspirator (applied on top of build_inspirator.py).
Params 7129-7138 (all automatable:false):
  7129 Lock Bars (bitmask, bar b locked = bit b)   7130 Inversion 0-3     7131 Spread (Close/Open/Wide)
  7132 Strum 0-100            7133 Figure (Block/Up/Down/Up-Down/Alberti)  7134 Ghost notes 0-100
  7135 Chord Pull 0-100       7136 Max Leap 1-12 (12 = off)             7137 Mutate 0-100     7138 Melody Degree 0-7
Order in ins_regenerate: gen* -> ins_post (voicing / figures / strum, melody rules, ghost notes, mutation) -> ins_applyLocks."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
ipath = os.path.join(root, 'patch', 'index.js')
src = open(path).read(); idx = open(ipath).read()
if 'INSPIRATOR2-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

P = [  # id, name, min, max, init, text, label
    (7129, 'Lock Bars', 0, 255, 0, None, 'Lock Bars'),
    (7130, 'Inversion', 0, 3, 0, None, 'Inversion'),
    (7131, 'Spread', 0, 2, 0, 'Close|Open|Wide', 'Spread'),
    (7132, 'Strum', 0, 100, 0, None, 'Strum'),
    (7133, 'Figure', 0, 4, 0, 'Block|Up|Down|Up-Down|Alberti', 'Figure'),
    (7134, 'Ghost Notes', 0, 100, 0, None, 'Ghost Notes'),
    (7135, 'Chord Pull', 0, 100, 0, None, 'Chord Pull'),
    (7136, 'Max Leap', 1, 12, 12, None, 'Max Leap'),
    (7137, 'Mutate', 0, 100, 0, None, 'Mutate'),
    (7138, 'Melody Degree', 0, 7, 0, 'Free|I|II|III|IV|V|VI|VII', 'Degree'),
]
decl = []; specs = []; handlers = []
VAR = {7129: None, 7130: 'ins_pInv', 7131: 'ins_pSpread', 7132: 'ins_pStrum', 7133: 'ins_pFig', 7134: 'ins_pGhost',
       7135: 'ins_pPull', 7136: 'ins_pLeap', 7137: 'ins_pMut', 7138: 'ins_pDegF'}
for (i, nm, lo, hi, ini, txt, lab) in P:
    t = (', text: "%s"' % txt) if txt else ''
    decl.append('    input event float param%d [[ name: "Insp %s", min: %d.0, max: %d.0, init: %d.0, step: 1.0%s, automatable: false ]];' % (i, nm, lo, hi, ini, t))
    if VAR[i]:
        handlers.append('    event param%d (float v) { %s = ins_clampi (ins_roundi (v), %d, %d); ins_dirty = true; }' % (i, VAR[i], lo, hi))
    if txt: specs.append('    [%d, "Insp %s", %d, %d, %d, "", "sel", [%s], 1, "%s", null],' % (i, nm, lo, hi, ini, ', '.join('"%s"' % x for x in txt.split('|')), lab))
    else: specs.append('    [%d, "Insp %s", %d, %d, %d, "", "knb", null, 1, "%s", null],' % (i, nm, lo, hi, ini, lab))

CODE = r'''
    // ---- INSPIRATOR2-DSP: post-stage (voicing, figures, strum, melody rules, ghost notes, mutation) and bar locks ----
    int ins_pLockBars = 0;
    int ins_pInv = 0;
    int ins_pSpread = 0;
    int ins_pStrum = 0;
    int ins_pFig = 0;
    int ins_pGhost = 0;
    int ins_pPull = 0;
    int ins_pLeap = 12;
    int ins_pMut = 0;
    int ins_pDegF = 0;
    bool ins_generated = false;
    int[512] ins_fzGrid;
    int[512] ins_fzOff;
    int[512] ins_fzLen;
    int[512] ins_fzPitch;
    int[512] ins_fzVel;
    int ins_fzCount = 0;
    int ins_fzMode = -1;
    int ins_fzValid = 0;

    void ins_rawAdd (int grid, int off, int len, int pitch, int vel)
    {
        if (ins_nCount >= 512) return;
        int o = ins_clampi (off, -60, 60);
        ins_nGrid.at (ins_nCount) = grid;
        ins_nOff.at (ins_nCount) = o;
        ins_nTick.at (ins_nCount) = ins_posMod (grid + o, ins_loopTicks);
        ins_nLen.at (ins_nCount) = ins_clampi (len, 1, 1000);
        ins_nPitch.at (ins_nCount) = ins_clampi (pitch, 0, 127);
        ins_nVel.at (ins_nCount) = ins_clampi (vel, 1, 127);
        ins_nCount += 1;
    }

    void ins_retick (int i)
    {
        ins_nOff.at (i) = ins_clampi (ins_nOff.at (i), -60, 60);
        ins_nTick.at (i) = ins_posMod (ins_nGrid.at (i) + ins_nOff.at (i), ins_loopTicks);
    }

    // remove notes whose velocity was set to 0
    void ins_compact()
    {
        int w = 0;
        for (int i = 0; i < ins_nCount; ++i)
        {
            if (ins_nVel.at (i) > 0)
            {
                if (w != i)
                {
                    ins_nGrid.at (w) = ins_nGrid.at (i);
                    ins_nOff.at (w) = ins_nOff.at (i);
                    ins_nTick.at (w) = ins_nTick.at (i);
                    ins_nLen.at (w) = ins_nLen.at (i);
                    ins_nPitch.at (w) = ins_nPitch.at (i);
                    ins_nVel.at (w) = ins_nVel.at (i);
                }
                w += 1;
            }
        }
        ins_nCount = w;
    }

    // pitch moved by scale steps (stays in the scale of the key)
    int ins_scaleShift (int pitch, int steps)
    {
        int rel = pitch - 60 - ins_keyOff();
        int best = 0;
        int bd = 1000;
        for (int k = -40; k <= 45; ++k)
        {
            int d = ins_scaleSemi (k) - rel;
            if (d < 0) d = 0 - d;
            if (d < bd) { bd = d; best = k; }
        }
        return ins_clampi (60 + ins_keyOff() + ins_scaleSemi (best + steps), 0, 127);
    }

    int ins_snapChord (int pitch, int c)
    {
        for (int k = 0; k < 7; ++k)
        {
            int d = (k + 1) / 2;
            if ((k % 2) == 1) d = 0 - d;
            if (ins_inChord (pitch + d - ins_keyOff(), c)) return pitch + d;
        }
        return pitch;
    }

    int ins_snapDegree (int pitch, int deg)
    {
        int target = ins_posMod (ins_keyOff() + ins_scaleSemi (deg), 12);
        for (int k = 0; k < 7; ++k)
        {
            if (ins_posMod (pitch + k, 12) == target) return pitch + k;
            if (ins_posMod (pitch - k, 12) == target) return pitch - k;
        }
        return pitch;
    }

    // sort the first n entries of ord by pitch (ascending)
    void ins_sortOrd (int[8]& ord, int n)
    {
        for (int a = 0; a < n - 1; ++a)
        {
            for (int b = a + 1; b < n; ++b)
            {
                if (ins_nPitch.at (ord.at (b)) < ins_nPitch.at (ord.at (a)))
                {
                    int t = ord.at (a);
                    ord.at (a) = ord.at (b);
                    ord.at (b) = t;
                }
            }
        }
    }

    // one chord (n simultaneous notes, entries start..start+n-1)
    void ins_voiceGroup (int start, int n)
    {
        int[8] ord;
        for (int k = 0; k < n; ++k) ord.at (k) = start + k;
        ins_sortOrd (ord, n);

        int inv = ins_minValue (ins_pInv, n - 1);
        for (int k = 0; k < inv; ++k) ins_nPitch.at (ord.at (k)) = ins_clampi (ins_nPitch.at (ord.at (k)) + 12, 0, 127);
        ins_sortOrd (ord, n);

        if (ins_pSpread >= 1 && n >= 3)
        {
            ins_nPitch.at (ord.at (n - 2)) = ins_clampi (ins_nPitch.at (ord.at (n - 2)) - 12, 0, 127);
            if (ins_pSpread >= 2)
            {
                if (n >= 4) ins_nPitch.at (ord.at (n - 4)) = ins_clampi (ins_nPitch.at (ord.at (n - 4)) - 12, 0, 127);
                else        ins_nPitch.at (ord.at (0)) = ins_clampi (ins_nPitch.at (ord.at (0)) - 12, 0, 127);
            }
            ins_sortOrd (ord, n);
        }

        int baseGrid = ins_nGrid.at (start);
        int gl = ins_nLen.at (ord.at (0));
        if (ins_pFig > 0 && n >= 3)
        {
            int[16] seq;
            int m = 0;
            if (ins_pFig == 1)      { for (int k = 0; k < n; ++k) { seq.at (m) = k; m += 1; } }
            else if (ins_pFig == 2) { for (int k = 0; k < n; ++k) { seq.at (m) = n - 1 - k; m += 1; } }
            else if (ins_pFig == 3)
            {
                for (int k = 0; k < n; ++k) { seq.at (m) = k; m += 1; }
                for (int k = n - 2; k >= 1; --k) { seq.at (m) = k; m += 1; }
            }
            else
            {
                seq.at (0) = 0; seq.at (1) = n - 1; seq.at (2) = n / 2; seq.at (3) = n - 1; m = 4;
            }
            int step = ins_clampi ((gl / ins_maxi (1, m) / 12) * 12, 12, 48);
            int slen = ins_maxi (6, step * ins_pGate / 100);
            int[8] pit;
            int[8] vel;
            int[8] off;
            int[8] used;
            for (int k = 0; k < n; ++k)
            {
                pit.at (k) = ins_nPitch.at (ord.at (k));
                vel.at (k) = ins_nVel.at (ord.at (k));
                off.at (k) = ins_nOff.at (ord.at (k));
            }
            int slots = ins_minValue (ins_maxi (m, gl / step), 64);
            for (int j = 0; j < slots; ++j)
            {
                int q = seq.at (j % m);
                int g = baseGrid + j * step;
                if (g < baseGrid + gl && used.at (q) == 0)
                {
                    used.at (q) = 1;
                    int e = ord.at (q);
                    ins_nGrid.at (e) = g;
                    ins_nLen.at (e) = slen;
                    ins_retick (e);
                }
                else if (g < baseGrid + gl)
                {
                    ins_rawAdd (g, off.at (q), slen, pit.at (q), vel.at (q) - (j % 2) * 4);
                }
            }
            // notes that never got a slot (shorter than the chord): silence them
            for (int k = 0; k < n; ++k)
            {
                if (used.at (k) == 0) ins_nVel.at (ord.at (k)) = 0;
            }
        }

        if (ins_pStrum > 0)
        {
            int st = ins_pStrum * 8 / 100;
            for (int k = 0; k < n; ++k)
            {
                ins_nOff.at (ord.at (k)) = ins_nOff.at (ord.at (k)) + k * st;
                ins_retick (ord.at (k));
            }
        }
    }

    int ins_minValue (int a, int b)
    {
        if (a < b) return a;
        return b;
    }

    void ins_postChords()
    {
        if (ins_pInv == 0 && ins_pSpread == 0 && ins_pStrum == 0 && ins_pFig == 0) return;
        int n0 = ins_nCount;
        int i = 0;
        while (i < n0)
        {
            int j = i;
            while (j + 1 < n0 && ins_nGrid.at (j + 1) == ins_nGrid.at (i)) j += 1;
            int n = j - i + 1;
            if (n > 1 && n <= 8) ins_voiceGroup (i, n);
            i = j + 1;
        }
    }

    void ins_postLead()
    {
        int prev = -1;
        for (int i = 0; i < ins_nCount; ++i)
        {
            int g = ins_nGrid.at (i);
            int b = g / ins_maxi (1, ins_barTicks);
            int s = (g % ins_maxi (1, ins_barTicks)) / 24;
            int c = ins_chordAt (b, s);
            int p = ins_nPitch.at (i);
            bool strong = (g % 96) == 0;
            if (ins_pDegF > 0 && ! strong && (ins_rv (320, i) % 100) < 35) p = ins_snapDegree (p, ins_pDegF - 1);
            if ((g % 48) == 0 && (ins_rv (321, i) % 100) < ins_pPull) p = ins_snapChord (p, c);
            if (ins_pLeap < 12 && prev >= 0)
            {
                for (int k = 0; k < 3; ++k)
                {
                    if (p - prev > ins_pLeap) p -= 12;
                    else if (prev - p > ins_pLeap) p += 12;
                }
                if (p - prev > ins_pLeap) p = ins_scaleShift (prev + ins_pLeap, 0);
                if (prev - p > ins_pLeap) p = ins_scaleShift (prev - ins_pLeap, 0);
            }
            p = ins_clampi (p, 0, 127);
            ins_nPitch.at (i) = p;
            prev = p;
        }
    }

    void ins_ghostDrums()
    {
        int sn = ins_lanePitch.at (1);
        int ki = ins_lanePitch.at (0);
        int n0 = ins_nCount;
        for (int b = 0; b < ins_numBars; ++b)
        {
            for (int s = 0; s < ins_stepsBar; ++s)
            {
                if ((s % 4) != 0)
                {
                    int g = b * ins_barTicks + s * 24;
                    bool occ = false;
                    for (int i = 0; i < n0; ++i)
                    {
                        if (ins_nGrid.at (i) == g && (ins_nPitch.at (i) == sn || ins_nPitch.at (i) == ki)) occ = true;
                    }
                    int pr = ins_pGhost * 45 / 100;
                    if ((s % 2) == 0) pr = ins_pGhost * 20 / 100;
                    if (! occ && (ins_rv (310, b * 32 + s) % 100) < pr)
                        ins_addNote (g, ins_humanT (ins_nCount), 8, sn, 14 + (ins_rv (311, b * 32 + s) % 16));
                }
            }
        }
    }

    void ins_ghostBass()
    {
        int n0 = ins_nCount;
        for (int b = 0; b < ins_numBars; ++b)
        {
            for (int s = 0; s < ins_stepsBar; ++s)
            {
                int g = b * ins_barTicks + s * 24;
                bool occ = false;
                int lastG = -1;
                int lastP = -1;
                for (int i = 0; i < n0; ++i)
                {
                    int ng = ins_nGrid.at (i);
                    if (ng >= g && ng < g + 24) occ = true;
                    if (ng < g && ng >= b * ins_barTicks && ng > lastG) { lastG = ng; lastP = ins_nPitch.at (i); }
                }
                int pr = ins_pGhost * 35 / 100;
                if ((s % 2) == 0) pr = ins_pGhost * 12 / 100;
                if (! occ && lastP >= 0 && (ins_rv (312, b * 32 + s) % 100) < pr)
                    ins_addNote (g, ins_humanT (ins_nCount), 10, lastP, 22 + (ins_rv (313, b * 32 + s) % 14));
            }
        }
    }

    void ins_postMutate()
    {
        for (int i = 0; i < ins_nCount; ++i)
        {
            if ((ins_rv (330, i) % 100) < ins_pMut)
            {
                int r = ins_rv (331, i) % 6;
                if (ins_pMode == 4)
                {
                    if (r < 2) ins_nVel.at (i) = 0;
                    else ins_nVel.at (i) = ins_clampi (ins_nVel.at (i) + (ins_rv (332, i) % 31) - 15, 1, 127);
                }
                else if (ins_pMode == 0)
                {
                    ins_nVel.at (i) = ins_clampi (ins_nVel.at (i) + (ins_rv (332, i) % 31) - 15, 1, 127);
                }
                else
                {
                    if (r == 0)      ins_nPitch.at (i) = ins_scaleShift (ins_nPitch.at (i), 1);
                    else if (r == 1) ins_nPitch.at (i) = ins_scaleShift (ins_nPitch.at (i), -1);
                    else if (r == 2) ins_nPitch.at (i) = ins_scaleShift (ins_nPitch.at (i), 2);
                    else if (r == 3) ins_nPitch.at (i) = ins_clampi (ins_nPitch.at (i) + 12 - 24 * (ins_rv (333, i) % 2), 0, 127);
                    else if (r == 4) ins_nVel.at (i) = 0;
                    else             ins_nVel.at (i) = ins_clampi (ins_nVel.at (i) + (ins_rv (332, i) % 31) - 15, 1, 127);
                }
            }
        }
    }

    void ins_post()
    {
        if (ins_pMode == 0)      ins_postChords();
        else if (ins_pMode == 1) ins_postLead();
        if (ins_pGhost > 0)
        {
            if (ins_pMode == 4)      ins_ghostDrums();
            else if (ins_pMode == 2) ins_ghostBass();
        }
        if (ins_pMut > 0) ins_postMutate();
        ins_compact();
    }

    // ---- bar locks: locked bars keep the notes they had when they were locked ----
    void ins_fzRemoveBars (int mask)
    {
        int w = 0;
        for (int i = 0; i < ins_fzCount; ++i)
        {
            int b = ins_fzGrid.at (i) / ins_maxi (1, ins_barTicks);
            bool drop = b < 8 && ((mask >> b) & 1) != 0;
            if (! drop)
            {
                ins_fzGrid.at (w) = ins_fzGrid.at (i);
                ins_fzOff.at (w) = ins_fzOff.at (i);
                ins_fzLen.at (w) = ins_fzLen.at (i);
                ins_fzPitch.at (w) = ins_fzPitch.at (i);
                ins_fzVel.at (w) = ins_fzVel.at (i);
                w += 1;
            }
        }
        ins_fzCount = w;
        ins_fzValid = ins_fzValid & (255 - mask);
    }

    event param7129 (float v)
    {
        int nm = ins_clampi (ins_roundi (v), 0, 255);
        int added = nm & (255 - ins_pLockBars);
        int removed = ins_pLockBars & (255 - nm);
        if (ins_fzMode != ins_pMode && added != 0)
        {
            ins_fzCount = 0;
            ins_fzValid = 0;
            ins_fzMode = ins_pMode;
        }
        ins_fzRemoveBars (removed | added);
        if (ins_generated && ins_fzMode == ins_pMode)
        {
            for (int i = 0; i < ins_nCount; ++i)
            {
                int b = ins_nGrid.at (i) / ins_maxi (1, ins_barTicks);
                if (b < 8 && ((added >> b) & 1) != 0 && ins_fzCount < 512)
                {
                    ins_fzGrid.at (ins_fzCount) = ins_nGrid.at (i);
                    ins_fzOff.at (ins_fzCount) = ins_nOff.at (i);
                    ins_fzLen.at (ins_fzCount) = ins_nLen.at (i);
                    ins_fzPitch.at (ins_fzCount) = ins_nPitch.at (i);
                    ins_fzVel.at (ins_fzCount) = ins_nVel.at (i);
                    ins_fzCount += 1;
                }
            }
            ins_fzValid = ins_fzValid | added;
        }
        ins_pLockBars = nm;
        ins_dirty = true;
    }

    void ins_applyLocks()
    {
        if (ins_pLockBars == 0 || ins_fzMode != ins_pMode) return;
        int m = ins_pLockBars & ins_fzValid;
        if (m == 0) return;
        for (int i = 0; i < ins_nCount; ++i)
        {
            int b = ins_nGrid.at (i) / ins_maxi (1, ins_barTicks);
            if (b < 8 && ((m >> b) & 1) != 0) ins_nVel.at (i) = 0;
        }
        ins_compact();
        for (int i = 0; i < ins_fzCount; ++i)
        {
            int b = ins_fzGrid.at (i) / ins_maxi (1, ins_barTicks);
            if (b < ins_numBars && b < 8 && ((m >> b) & 1) != 0)
                ins_rawAdd (ins_fzGrid.at (i), ins_fzOff.at (i), ins_fzLen.at (i), ins_fzPitch.at (i), ins_fzVel.at (i));
        }
    }
'''

# declarations after param7128
a = '    input event float param7128 [[ name: "Insp Fill Every", min: 0.0, max: 3.0, init: 2.0, step: 1.0, text: "Off|2 Bars|4 Bars|8 Bars", automatable: false ]];'
rep(a, a + '\n    // INSPIRATOR2-DSP\n' + '\n'.join(decl))
rep('    void ins_regenerate()\n', CODE + '\n    void ins_regenerate()\n')
rep('        else                 ins_genDrums();\n', '        else                 ins_genDrums();\n\n        ins_post();\n        ins_applyLocks();\n        ins_generated = true;\n')
h = '    event param7128 (float v) { ins_pFill = ins_clampi (ins_roundi (v), 0, 3); ins_dirty = true; }'
rep(h, h + '\n' + '\n'.join(handlers))
s = '    [7128, "Insp Fill Every", 0, 3, 2, "", "sel", ["Off", "2 Bars", "4 Bars", "8 Bars"], 1, "Fill Every", null],'
rep(s, s + '\n' + '\n'.join(specs), 'idx')
open(path, 'w').write(src); open(ipath, 'w').write(idx)
print('applied')
