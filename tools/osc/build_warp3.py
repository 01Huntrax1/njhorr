#!/usr/bin/env python3
"""Warp 3 upgrade.  Idempotent.  Usage: build_warp3.py [patch.cmajor]
 * per-voice modulation destinations 5662+o "OSC n Warp 3 Amount" (vmod slot 1584+o, added to the Amount like Warp 1/2: +-50% at 100%)
 * new warp modes 18..26 (phase: Pinch, Spread, Slice, Twin; amplitude: Cheby 3, Cheby 5, Deadzone, Expand, Compress); 0..17 unchanged
 * patch/index.js: mode names, mode ranges, destination names + group, knob drop targets"""
import os, re, json, sys
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, "..", "..")
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "patch", "Eisenpuls_Synth.cmajor")
JS = os.path.join(R, "patch", "index.js")
NEW = ["Pinch", "Spread", "Slice", "Twin", "Cheby 3", "Cheby 5", "Deadzone", "Expand", "Compress"]
s = open(PATCH).read()
if "// WARP3-DONE" in s:
    print("cmajor already patched")
else:
    def one(a, b):
        global s
        assert s.count(a) == 1, (s.count(a), a[:70]); s = s.replace(a, b)
    one("        return ph;\n    }\n\n    // Amplitude warp (modes 7, 8, 13 .. 17) of one warp slot", '''        if (mode == 18)
        {
            float x = ph * 2.0f - 1.0f;                                   // pinch: the phase is pulled toward the middle of the cycle
            float a = float (pow (abs (x), 1.0f + 3.0f * amt));
            return 0.5f + 0.5f * (x < 0.0f ? -a : a);
        }

        if (mode == 19)
        {
            float x = ph * 2.0f - 1.0f;                                   // spread: the phase is pushed away from the middle
            float a = float (pow (abs (x), 1.0f / (1.0f + 3.0f * amt)));
            return 0.5f + 0.5f * (x < 0.0f ? -a : a);
        }

        if (mode == 20)
            return clamp (ph / (1.0f - 0.9f * amt), 0.0f, 1.0f);           // slice: the cycle is squeezed to its start, then held

        if (mode == 21)
        {
            float x = ph * 2.0f;                                          // twin: two cycles blended in
            return ph + (x - float (floor (x)) - ph) * amt;
        }

        return ph;
    }

    // Amplitude warp (modes 7, 8, 13 .. 17, 22 .. 26) of one warp slot''')
    one("        return y;\n    }\n\n    bool wtIsAmp (int m)", '''        if (mode == 22)
            return y + (4.0f * y * y * y - 3.0f * y - y) * amt;            // Chebyshev T3 (adds the 3rd harmonic)

        if (mode == 23)
        {
            float y2 = y * y;
            return y + (y * (16.0f * y2 * y2 - 20.0f * y2 + 5.0f) - y) * amt;   // Chebyshev T5
        }

        if (mode == 24)
        {
            float d = amt * 0.5f;                                         // deadzone: small values fall to zero
            float a = max (float (abs (y)) - d, 0.0f) / (1.0f - d);
            return y < 0.0f ? -a : a;
        }

        if (mode == 25)
        {
            float a = float (pow (abs (y), 1.0f + 2.0f * amt));           // expand: quiet parts get quieter
            return y < 0.0f ? -a : a;
        }

        if (mode == 26)
        {
            float a = float (pow (abs (y), 1.0f / (1.0f + 2.0f * amt)));  // compress: quiet parts get louder
            return y < 0.0f ? -a : a;
        }

        return y;
    }

    bool wtIsAmp (int m)''')
    one("(m >= 1 && m <= 6) || (m >= 9 && m <= 12);", "(m >= 1 && m <= 6) || (m >= 9 && m <= 12) || (m >= 18 && m <= 21);")
    one("float<2> wtStep (int o, int vi, float freq, float pos, int fl, float pm, float a1m, float a2m)",
        "float<2> wtStep (int o, int vi, float freq, float pos, int fl, float pm, float a1m, float a2m, float a3m)")
    one("int   m1  = clamp (int (opv (o, 18) + 0.5f), 0, 17);", "int   m1  = clamp (int (opv (o, 18) + 0.5f), 0, 26);")
    one("int   m2  = clamp (int (opv (o, 20) + 0.5f), 0, 17);", "int   m2  = clamp (int (opv (o, 20) + 0.5f), 0, 26);")
    one("int   m3  = clamp (int (wtP.at (o * 16) + 0.5f), 0, 17);", "int   m3  = clamp (int (wtP.at (o * 16) + 0.5f), 0, 26);")
    one("float a3  = clamp (wtP.at (o * 16 + 1), 0.0f, 1.0f);", "float a3  = clamp (wtP.at (o * 16 + 1) + a3m * 0.5f, 0.0f, 1.0f);")
    one("vmod.at (dB + 4), vmod.at (dB + 5));", "vmod.at (dB + 4), vmod.at (dB + 5), vmod.at (1584 + o));")
    # voice destinations 5662 .. 5667 -> vmod[1584 + n]
    a = "                if ((dd >= 60 && dd < 168) || (dd >= 186 && dd < 258) || (dd >= 1308 && dd < 1488))   // MXDST-DSP, MATFAST\n                {\n                    mat = true;\n                    srcMask |= matSrcBit (dd);\n                }\n            }\n"
    one(a, a + '''            else if (dd >= 5662 && dd < 5668 && ss > 0)   // WARP3: per-voice Warp 3 Amount of OSC 1 .. 6
            {
                int vd = dd - 4078;
                vmodDirty.at (s) = vd;
                vmod.at (vd) += srcValueVoice (ss, vi) * mmAmt.at (s);
            }
''')
    s = s.replace("clamp (int (v + 0.5f), 0, 5661)", "clamp (int (v + 0.5f), 0, 5667)")
    s = s.replace("(0-5661, see Dest list)\", min: 0.0, max: 5661.0", "(0-5667, see Dest list)\", min: 0.0, max: 5667.0")
    s = re.sub(r'(Warp [123] Mode", min: 0.0, max: )17\.0', r'\g<1>26.0', s)
    s += "\n// WARP3-DONE\n"
    open(PATCH, "w").write(s); print("cmajor patched")
j = open(JS).read()
if "Cheby 3" in j:
    print("index.js already patched")
else:
    a = '"Asym", "Drive"];'; assert j.count(a) == 1
    j = j.replace(a, '"Asym", "Drive", ' + ", ".join(json.dumps(n) for n in NEW) + "];")
    n = [0]
    def mode(m): n[0] += 1; return m.group(1) + "0, 26," + m.group(3)
    j = re.sub(r'(\[\d+, "OSC \d Warp [123] Mode", )(0, 17,)(.*)', lambda m: m.group(1) + "0, 26," + m.group(3), j)
    assert len(re.findall(r'Warp [123] Mode", 0, 26,', j)) == 18
    m = re.search(r"const MOD_DST = (\[.*?\]);\n", j); d = json.loads(m.group(1)); assert len(d) == 5662
    d += ["OSC %d Warp 3 Amount" % (o + 1) for o in range(6)]
    j = j[:m.start(1)] + json.dumps(d) + j[m.end(1):]
    m = re.search(r"const MOD_DST_GROUPS = (\[.*?\]);\n", j); g = json.loads(m.group(1)); g.append([5662, "Warp 3 (per voice)"])
    j = j[:m.start(1)] + json.dumps(g) + j[m.end(1):]
    m = re.search(r"const MOD_TARGET = (\{.*?\});", j); t = json.loads(m.group(1))
    for o in range(6): t[str(12501 + 16 * o)] = [5662 + o, 0.5]
    j = j[:m.start(1)] + json.dumps(t) + j[m.end(1):]
    open(JS, "w").write(j); print("index.js patched")
