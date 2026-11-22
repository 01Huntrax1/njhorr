#!/usr/bin/env python3
"""Wavetable "Eco" quality mode: the per-oscillator Aliasing switch (ids 2000 + osc) becomes a selector Clean / Alias / Eco.  Idempotent.
Eco = band-limited mip levels like Clean, but linear instead of cubic interpolation (and a linear frame crossfade): about 30 % cheaper per unison voice.
Presets stay valid (0 = Clean, 1 = Alias).   python3 tools/osc/build_wteco.py"""
import os, re
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P = os.path.join(R, "patch", "Eisenpuls_Synth.cmajor"); J = os.path.join(R, "patch", "index.js")
s = open(P).read(); done = "wtMipReadLin" in s
def rep(a, b, cnt=1):
    global s
    assert s.count(a) == cnt, (a[:60], s.count(a)); s = s.replace(a, b)
if not done:
    rep("    // wavetable read (WT2): frames fa / fb", '''    // linear read of one cycle (Eco quality)
    float wtMipReadLin (int base, int len, float x)
    {
        int   mask = len - 1;
        int   i    = int (x);
        float t    = x - float (i);
        float p1   = wtMip.at (base + (i & mask));
        float p2   = wtMip.at (base + ((i + 1) & mask));
        return p1 + t * (p2 - p1);
    }

    float wtReadEco (int o, int lvl, float64 phase, int fa, int fb, float ff)
    {
        int   len = 2048 >> lvl;
        int   off = 4096 - (4096 >> lvl);
        float x   = float (phase) * float (len);
        float va  = wtMipReadLin ((o * 256 + fa) * 4096 + off, len, x);

        if (fb == fa || ff <= 0.0f)
            return va;

        float vb = wtMipReadLin ((o * 256 + fb) * 4096 + off, len, x);
        return va + (vb - va) * ff;
    }

    // wavetable read (WT2): frames fa / fb''')
    rep("        if (wtAlias.at (o) > 0.5f)\n            lvlAll = 0;", "        float alv = wtAlias.at (o);\n        bool  eco = alv > 1.5f;\n\n        if (alv > 0.5f && ! eco)\n            lvlAll = 0;")
    rep("            float y = wtRead (o, lv, rph, fa, fb, ff, fmode, fm, fc);", "            float y = eco ? wtReadEco (o, lv, rph, fa, fb, ff) : wtRead (o, lv, rph, fa, fb, ff, fmode, fm, fc);")
    rep("    float[6] wtAlias;     // Wavetable Aliasing switch per slot (ids 2000 + slot)", "    float[6] wtAlias;     // Wavetable quality per slot (ids 2000 + slot): 0 Clean, 1 Alias, 2 Eco")
    open(P, "w").write(s)
    # declarations: max 2
    s = open(P).read()
    s, n = re.subn(r'(param200[0-5] \[\[ name: "OSC \d WT )Aliasing(", min: 0.0, max: )1\.0', r'\1Quality\g<2>2.0', s); assert n == 6, n
    open(P, "w").write(s)
j = open(J).read()
j, n = re.subn(r'\[(200[0-5]), "(OSC \d) WT Aliasing", 0, 1, 0, "", "btn", \["Off", "On"\], 1, "Aliasing", null\]',
               r'[\1, "\2 WT Quality", 0, 2, 0, "", "sel", ["Clean", "Alias", "Eco"], 1, "Quality", null]', j)
print("cmajor", "already" if done else "patched", "| index.js rows:", n); open(J, "w").write(j)
