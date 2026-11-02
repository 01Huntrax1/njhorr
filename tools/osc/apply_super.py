#!/usr/bin/env python3
"""Unison upgrade: up to 16 voices (was 7) and two new detune curves, Super Saw and Hyper Saw (Unison Style 4 and 5).
 - Super Saw: the voices sit at the detune offsets of the analysed JP-8000 Super Saw (interpolated for fewer / more voices than 7), scaled by its detune curve
   (up to +-11 % = about 1.9 semitones); Blend is the Mix control (centre and side gains of the JP-8000 mix curves).
 - Hyper Saw: a denser, wider spread (up to +-22 % = about 3.4 semitones, detune ^ 1.6, voices packed towards the centre), Blend as usual.
 The wavetable and Alpha Juno sources share the unison.  Unison phases, gains and drift now use 16 voices per slot (Voice.wtUPh slot * 16 + j, Voice.phs 2048 +
 (slot * 16 + j) * 2 for the drift, 2240 + slot * 16 + j for the Juno sub counters).  One-shot on patch/Eisenpuls_Synth.cmajor, patch/index.js and layout.py."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
JS = os.path.join(HERE, "..", "..", "patch", "index.js")
LAY = os.path.join(HERE, "layout.py")
s = open(PATCH).read()
if "Super Saw: the voices sit" in s: raise SystemExit("already applied")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:70], s.count(old))
    s = s.replace(old, new)
rep("float64[64] wtUPh;    // wavetable unison phases: slot * 7 + unison voice", "float64[128] wtUPh;   // wavetable unison phases: slot * 16 + unison voice")
rep("float[2048] phs;      // physical modelling states: slot * 176 + ...", "float[4096] phs;      // physical modelling states: slot * 176 + ...; 2048.. unison drift, 2240.. Juno sub counters")
for n in ("uniRatio", "uniCents", "uniGL", "uniGR"):
    s, k = re.subn(r"float\[64\](\s+)%s;" % n, r"float[128]\1%s;" % n, s); assert k == 1, n
i = s.index("    void updateWtUni (int o)"); j = s.index("    void resetWtUni (int vi, int o)")
NEW = r'''    void updateWtUni (int o)
    {
        int   n     = clamp (int (opv (o, 13) + 0.5f), 1, 16);
        float det   = clamp (opv (o, 14), 0.0f, 1.0f);
        float blend = clamp (opv (o, 15), 0.0f, 1.0f);
        float width = clamp (opv (o, 16), 0.0f, 1.0f);
        int   style = clamp (int (opv (o, 17) + 0.5f), 0, 5);

        uniCnt.at (o) = n;

        float powSum = 0.0f;
        float dtn    = jpDetCurve (det);

        for (int j = 0; j < 16; ++j)
        {
            float pos = 0.0f;
            if (n > 1)
                pos = 2.0f * float (j) / float (n - 1) - 1.0f;

            float ratio = 1.0f;
            float w     = blend + (1.0f - blend) * (1.0f - abs (pos));

            if (style <= 3)
            {
                float dpos = pos;
                if (style == 1)      dpos = pos * abs (pos);
                else if (style == 2) dpos = (pos < 0.0f ? -1.0f : 1.0f) * float (sqrt (abs (pos)));
                else if (style == 3 && n > 1) dpos = uniRandPos (o, j);

                float cents = dpos * det * 50.0f;
                ratio = float (pow (2.0f, cents / 1200.0f));
                uniCents.at (o * 16 + j) = dpos * 50.0f;
            }
            else if (style == 4)
            {
                // Super Saw: the offsets of the seven JP-8000 saws, interpolated over the voices; Blend = the JP-8000 Mix
                float t  = (pos + 1.0f) * 3.0f;
                int   i0 = clamp (int (t), 0, 5);
                float fr = t - float (i0);
                float of = jpOff.at (i0) * (1.0f - fr) + jpOff.at (i0 + 1) * fr;
                ratio = 1.0f + of * dtn;
                uniCents.at (o * 16 + j) = 0.0f;
                float cG = -0.55366f * blend + 0.99785f;
                float sG = -0.73764f * blend * blend + 1.2841f * blend + 0.044372f;
                w = abs (pos) < 0.001f ? cG : sG;
            }
            else
            {
                // Hyper Saw: a wide, dense spread, packed towards the centre
                float dp = pos * (0.55f + 0.45f * abs (pos));
                ratio = 1.0f + dp * 0.22f * float (pow (det, 1.6f));
                uniCents.at (o * 16 + j) = 0.0f;
            }

            uniRatio.at (o * 16 + j) = ratio;

            if (j >= n) w = 0.0f;
            powSum += w * w;

            float pp  = pos * width;
            float ang = (pp + 1.0f) * 0.25f * float (pi);
            uniGL.at (o * 16 + j) = w * float (cos (ang)) * 1.4142f;
            uniGR.at (o * 16 + j) = w * float (sin (ang)) * 1.4142f;
        }

        float norm = 1.0f / float (sqrt (max (powSum, 0.01f)));

        for (int j = 0; j < 16; ++j)
        {
            uniGL.at (o * 16 + j) = uniGL.at (o * 16 + j) * norm;
            uniGR.at (o * 16 + j) = uniGR.at (o * 16 + j) * norm;
        }
    }

'''
s = s[:i] + NEW + s[j:]
i = s.index("    void resetWtUni (int vi, int o)"); j = s.index("    // ALIAS-DSP-BEGIN", i)
seg = s[i:j]
assert seg.count("j < 7") == 1 and seg.count("o * 7 + j") == 1
seg = seg.replace("j < 7", "j < 16").replace("o * 7 + j", "o * 16 + j")
s = s[:i] + seg + s[j:]
rep("            int     si = o * 7 + j;\n", "            int     si = o * 16 + j;\n")
rep("        if (n > 2)\n        {\n            int lvLo = wtLevel", "        if (n > 2 && opv (o, 17) < 3.5f)\n        {\n            int lvLo = wtLevel")
rep("        int   ui = o * 7;\n", "        int   ui = o * 16;\n")
rep("phs.at (1854 + ui + j)", "phs.at (2240 + ui + j)", 2)
i = s.index("    float uniDriftRaw (int vi, int o, int j, bool active)"); j = s.index("    // UNI-DSP-END", i)
seg = s[i:j]
assert seg.count("k < 7") == 1 and seg.count("1752 + (o * 7 + k) * 2 + 1") == 1 and seg.count("1752 + (o * 7 + j) * 2") == 1
seg = seg.replace("k < 7", "k < 16").replace("1752 + (o * 7 + k) * 2 + 1", "2048 + (o * 16 + k) * 2 + 1").replace("1752 + (o * 7 + j) * 2", "2048 + (o * 16 + j) * 2")
s = s[:i] + seg + s[j:]
s, k = re.subn(r'(name: "OSC \d Unison Voices", min: 1.0, max: )7\.0', r'\g<1>16.0', s); assert k == 6, k
s, k = re.subn(r'(name: "OSC \d Unison Style", min: 0.0, max: )3\.0', r'\g<1>5.0', s); assert k == 6, k
s = s.replace("// Super Saw: the offsets", "// Super Saw: the voices sit at the offsets") if False else s
s = s.replace("    // ---------------- wavetable unison ----------------\n", "    // ---------------- wavetable unison ----------------\n    // Unison Style 0..3: the classic detune curves (+-50 cents).  4 Super Saw: the voices sit at the offsets of the JP-8000 Super Saw. 5 Hyper Saw: wide and dense. Up to 16 voices.\n", 1)
open(PATCH, "w").write(s)
js = open(JS).read()
js, k = re.subn(r'(\[\d+, "OSC \d Unison Voices", 1, )7(, 1, "", "stp")', r'\g<1>16\2', js); assert k == 6, k
js, k = re.subn(r'(\[\d+, "OSC \d Unison Style", 0, )3(, 0, "", "btn", )\["Lin", "Exp", "Inv", "Rnd"\]', r'\g<1>5\2["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"]', js); assert k == 6, k
assert js.count('const UNI_STYLES = ["Lin", "Exp", "Inv", "Rnd"];') == 1
js = js.replace('const UNI_STYLES = ["Lin", "Exp", "Inv", "Rnd"];', 'const UNI_STYLES = ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"];')
open(JS, "w").write(js)
lay = open(LAY).read()
a = '(13, "uvox",   "Unison Voices", "Voices",    1, 7, 1,'; b = '(17, "ustyle", "Unison Style",  "Detune Curve", 0, 3, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd"]),'
assert a in lay and b in lay
lay = lay.replace(a, '(13, "uvox",   "Unison Voices", "Voices",    1, 16, 1,').replace(b, '(17, "ustyle", "Unison Style",  "Detune Curve", 0, 5, 0, "", "btn", ["Lin", "Exp", "Inv", "Rnd", "Super", "Hyper"]),')
open(LAY, "w").write(lay)
print("ok")
