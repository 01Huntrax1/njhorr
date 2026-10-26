#!/usr/bin/env python3
"""Adds the physical modelling source (Source type 3, modal resonators in the style of RipplerX) to patch/Eisenpuls_Synth.cmajor.
Idempotent: the DSP block, the parameter declarations and the handlers sit between PHYS markers and are replaced on every run.
Parameters of slot o: id PHY_BASE + 32 * o + j (see PHY below).  Usage: build_phys.py [patch.cmajor]"""
import math, re, sys, os
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "patch", "Eisenpuls_Synth.cmajor")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "osc"))
import layout as L
PHY_BASE = L.PHY_BASE
PHY = [(p[0], p[1], p[2], p[4], p[5], p[6], p[7], 1 if p[8] in ("sel", "btn") else None) for p in L.PHY]
def circ():
    # circular membrane (Bessel zeros j_mn / j_01), sorted
    z = [2.4048, 3.8317, 5.1356, 5.5201, 6.3802, 7.0156, 7.5883, 8.4172, 8.6537, 8.7715, 9.7610, 9.9361, 10.1735, 11.0647, 11.0864, 11.7915, 11.6198, 12.2251]
    z = sorted(z)
    return [v / z[0] for v in z][:16]
def square():
    s = sorted(set(round(math.sqrt(m*m + n*n), 6) for m in range(1, 8) for n in range(m, 8)))
    return [v / s[0] for v in s][:16]
def plate():
    s = sorted(set(round(m*m + (n / 1.3) ** 2, 6) for m in range(1, 7) for n in range(1, 7)))
    return [v / s[0] for v in s][:16]
def pad(l): return (l + [l[-1] * 1.12 ** (k + 1) for k in range(16 - len(l))])[:16]
mem = circ()
RAT = [
 [float(n) for n in range(1, 17)],
 [((2 * i + 3) / 3.0) ** 2 for i in range(16)],
 pad(square()),
 pad(mem),
 pad(plate()),
 [1 + (r - 1) * 0.5 for r in mem],
 [1, 4, 10] + [0.88 * (i + 1.5) ** 2 for i in range(3, 16)],
 [float(n) for n in range(1, 17)],
 [float(2 * n - 1) for n in range(1, 17)],
]
AEXP = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.35, 1.0, 1.0]
rat = ", ".join("%.5ff" % v for row in RAT for v in row)
aexp = ", ".join("%.2ff" % v for v in AEXP)

DSP = r'''    // ---------------- physical modelling source (modal resonators, tools/phys/build_phys.py) ----------------
    // two resonators A and B of 16 modes each (2-pole resonators per mode), excited by a mallet impulse and / or a noise burst.
    // per slot and voice 176 floats of state in Voice.phs: 0..31 A states (y1, y2 per mode), 32..63 B states, 64..111 A coefficients
    // (c1 [16], c2 [16], gain [16]), 112..159 B coefficients, 160 noise envelope, 161 mallet flag, 162 mallet low-pass, 163 noise low-pass,
    // 164 refresh counter, 165 signature, 166 last frequency, 167 low-pass coefficient, 168 noise decay per sample
    float[192] phyP;      // slot * 32 + parameter
    const float[144] phyRat = (@RAT@);
    const float[9] phyAmpExp = (@AEXP@);

    void phySet (int o, int j, float v)
    {
        phyP.at (o * 32 + j) = v;
    }

    void phyNoteOn (int vi, int o)
    {
        int b = o * 176;

        for (int i = 0; i < 64; ++i)
            voices.at (vi).phs.at (b + i) = 0.0f;

        voices.at (vi).phs.at (b + 160) = 1.0f;
        voices.at (vi).phs.at (b + 161) = 0.0f;
        voices.at (vi).phs.at (b + 162) = 0.0f;
        voices.at (vi).phs.at (b + 163) = 0.0f;
        voices.at (vi).phs.at (b + 164) = 0.0f;
        voices.at (vi).phs.at (b + 165) = -1.0f;
    }

    // coefficients of the 16 modes of resonator res (0 = A, 1 = B)
    void phyCoefs (int vi, int o, int res, float f0, int model, float dec, float mat, float hit, float inh)
    {
        float sr    = float (processor.frequency);
        int   cb    = o * 176 + 64 + res * 48;
        float damp  = 1.6f * (1.0f - mat);
        float aex   = phyAmpExp.at (model);
        float sumSq = 0.0f;

        for (int i = 0; i < 16; ++i)
        {
            float r = phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i));
            float f = f0 * r;
            float g = 0.0f;
            float c1 = 0.0f;
            float c2 = 0.0f;

            if (f < sr * 0.45f)
            {
                float w   = 6.2831853f * f / sr;
                float t60 = max (dec * float (pow (r, -damp)), 0.004f);
                float rr  = float (exp (-6.9078f / (t60 * sr)));
                float am  = abs (float (sin (3.14159265f * hit * float (i + 1)))) / float (pow (float (i + 1), aex));
                c1  = 2.0f * rr * float (cos (w));
                c2  = rr * rr;
                g   = am;
                sumSq += am * am;
            }

            voices.at (vi).phs.at (cb + i)      = c1;
            voices.at (vi).phs.at (cb + 16 + i) = c2;
            voices.at (vi).phs.at (cb + 32 + i) = g;
        }

        float nrm = 0.9f / float (sqrt (max (sumSq, 0.05f)));

        for (int i = 0; i < 16; ++i)
        {
            float g = voices.at (vi).phs.at (cb + 32 + i);

            if (g != 0.0f)
            {
                float f = f0 * phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i));
                voices.at (vi).phs.at (cb + 32 + i) = g * nrm * float (sin (6.2831853f * f / sr));
            }
        }
    }

    // one sample of slot o on voice vi at the note frequency f0 (Hz); modifiers from the mod matrix: hit position, material, noise balance
    float phyStep (int vi, int o, float f0, float hitM, float matM, float noiseM)
    {
        float sr  = float (processor.frequency);
        int   b   = o * 176;
        int   pb  = o * 32;
        float bal = phyP.at (pb + 14);
        bool  ser = phyP.at (pb + 15) > 0.5f;

        // coefficients: every 64 samples, and only when the pitch or a parameter has changed
        float cnt = voices.at (vi).phs.at (b + 164);

        if (cnt <= 0.0f)
        {
            voices.at (vi).phs.at (b + 164) = 64.0f;
            float hA  = clamp (phyP.at (pb + 6)  + hitM * 0.5f, 0.0f, 1.0f);
            float hB  = clamp (phyP.at (pb + 11) + hitM * 0.5f, 0.0f, 1.0f);
            float mA  = clamp (phyP.at (pb + 5)  + matM * 0.5f, 0.0f, 1.0f);
            float mB  = clamp (phyP.at (pb + 10) + matM * 0.5f, 0.0f, 1.0f);
            float sig = phyP.at (pb + 1) * 1.1f + phyP.at (pb + 2) * 0.0013f + phyP.at (pb + 3) * 3.7f + phyP.at (pb + 4) * 0.77f + mA * 5.3f + hA * 7.1f
                      + phyP.at (pb + 7) * 11.3f + phyP.at (pb + 8) * 13.1f + phyP.at (pb + 9) * 0.61f + mB * 17.9f + hB * 19.3f
                      + phyP.at (pb + 12) * 23.9f + phyP.at (pb + 13) * 0.29f;

            if (voices.at (vi).phs.at (b + 165) != sig || abs (voices.at (vi).phs.at (b + 166) - f0) > f0 * 0.0004f)
            {
                voices.at (vi).phs.at (b + 165) = sig;
                voices.at (vi).phs.at (b + 166) = f0;

                int mdA = clamp (int (phyP.at (pb + 3) + 0.5f), 0, 8);
                int mdB = clamp (int (phyP.at (pb + 8) + 0.5f), 0, 8);
                phyCoefs (vi, o, 0, f0, mdA, phyP.at (pb + 4), mA, hA, phyP.at (pb + 7));
                phyCoefs (vi, o, 1, f0 * float (pow (2.0f, phyP.at (pb + 13) / 12.0f)), mdB, phyP.at (pb + 9), mB, hB, phyP.at (pb + 12));

                float cut = 200.0f * float (pow (2.0f, phyP.at (pb + 1) * 7.0f));
                voices.at (vi).phs.at (b + 167) = 1.0f - float (exp (-6.2831853f * min (cut, sr * 0.45f) / sr));
                voices.at (vi).phs.at (b + 168) = float (exp (-6.9078f / (max (phyP.at (pb + 2), 1.0f) * 0.001f * sr)));
            }
        }
        else
            voices.at (vi).phs.at (b + 164) = cnt - 1.0f;

        // exciter
        float lpa = voices.at (vi).phs.at (b + 167);
        float mal = 0.0f;

        if (voices.at (vi).phs.at (b + 161) < 0.5f)
        {
            mal = 1.0f;
            voices.at (vi).phs.at (b + 161) = 1.0f;
        }

        float lm = voices.at (vi).phs.at (b + 162);
        lm += lpa * (mal - lm);
        voices.at (vi).phs.at (b + 162) = abs (lm) < 1.0e-20f ? 0.0f : lm;

        float en = voices.at (vi).phs.at (b + 160);
        float nz = nextNoise() * en;
        voices.at (vi).phs.at (b + 160) = en * voices.at (vi).phs.at (b + 168);
        float ln = voices.at (vi).phs.at (b + 163);
        ln += lpa * (nz - ln);
        voices.at (vi).phs.at (b + 163) = ln;

        float nmix = clamp (phyP.at (pb) + noiseM * 0.5f, 0.0f, 1.0f);
        float exc  = (1.0f - nmix) * lm * 2.0f + nmix * ln * 0.35f;

        // resonators
        float outA = 0.0f;
        float outB = 0.0f;

        if (bal < 0.999f || ser)
        {
            for (int i = 0; i < 16; ++i)
            {
                float g = voices.at (vi).phs.at (b + 96 + i);

                if (g != 0.0f)
                {
                    float y1 = voices.at (vi).phs.at (b + 2 * i);
                    float y2 = voices.at (vi).phs.at (b + 2 * i + 1);
                    float y0 = voices.at (vi).phs.at (b + 64 + i) * y1 - voices.at (vi).phs.at (b + 80 + i) * y2 + g * exc;
                    voices.at (vi).phs.at (b + 2 * i)     = abs (y0) < 1.0e-20f ? 0.0f : y0;
                    voices.at (vi).phs.at (b + 2 * i + 1) = y1;
                    outA += y0;
                }
            }
        }

        if (bal > 0.001f)
        {
            float xb = ser ? outA * 0.7f : exc;

            for (int i = 0; i < 16; ++i)
            {
                float g = voices.at (vi).phs.at (b + 144 + i);

                if (g != 0.0f)
                {
                    float y1 = voices.at (vi).phs.at (b + 32 + 2 * i);
                    float y2 = voices.at (vi).phs.at (b + 32 + 2 * i + 1);
                    float y0 = voices.at (vi).phs.at (b + 112 + i) * y1 - voices.at (vi).phs.at (b + 128 + i) * y2 + g * xb;
                    voices.at (vi).phs.at (b + 32 + 2 * i)     = abs (y0) < 1.0e-20f ? 0.0f : y0;
                    voices.at (vi).phs.at (b + 32 + 2 * i + 1) = y1;
                    outB += y0;
                }
            }
        }

        return outA * (1.0f - bal) + outB * bal;
    }

'''.replace("@RAT@", rat).replace("@AEXP@", aexp)

DECL = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];\n' % (
    PHY_BASE + 32 * o + p[0], o + 1, ("Physical " if p[0] < 16 else "") + p[2], repr(float(p[3])), repr(float(p[4])), repr(float(p[5])), ", step: 1.0" if p[7] else "")
    for o in range(6) for p in PHY)
HAND = "".join("    event param%d (float v) { phySet (%d, %d, v); }\n" % (PHY_BASE + 32 * o + p[0], o, p[0]) for o in range(6) for p in PHY)

s = open(PATCH).read()
def block(tag, body, anchor_re, before=True):
    global s
    a, z = "    // PHYS-%s-BEGIN\n" % tag, "    // PHYS-%s-END\n" % tag
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", DSP, r"^    // ---------------- MIDI ----------------")
block("DECL", DECL, r"^    input event float param1600 ")
block("HAND", HAND, r"^    event param1600 ")
# defaults of the physical parameters (the DSP starts from them before the host sends its own values)
INIT = "".join("            phyP.at (io * 32 + %d) = %sf;\n" % (p[0], repr(float(p[5]))) for p in PHY)
a, z = "            // PHYS-INIT-BEGIN\n", "            // PHYS-INIT-END\n"
s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
anchor = "            op.at (io * 64 + 50) = 8.0f;\n"
assert anchor in s
s = s.replace(anchor, anchor + a + INIT + z, 1)
# Voice state, source type range, note-on and voice loop
if "float[2048] phs;" not in s:
    s = s.replace("        int     fdlW;         // comb delay write position\n", "        float[2048] phs;      // physical modelling states: slot * 176 + ...\n        int     fdlW;         // comb delay write position\n", 1)
s = re.sub(r'(name: "OSC \d Source", min: 0.0, max: )[23]\.0', r'\g<1>4.0', s)
if "phyNoteOn (v, o);" not in s:
    s = s.replace("                    plaitsNoteOn (v, o);\n", "                    plaitsNoteOn (v, o);\n                    phyNoteOn (v, o);\n", 1)
if "phyStep (i, o, freq" not in s:
    old = "                    else\n                    {\n                        sL = plaitsStep ("
    assert old in s
    s = s.replace(old, "                    else if (ty == 3)\n                    {\n                        sL = phyStep (i, o, freq, vmod.at (dB + 3), vmod.at (dB + 4), vmod.at (dB + 5));\n                        sR = sL;\n                    }\n" + old.replace("                    else\n", "                    else\n"), 1)
open(PATCH, "w").write(s)
# the same mode tables for the native editor's display
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoPhys.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/phys/build_phys.py: mode frequency ratios and amplitude exponents of the Physical source models (same tables as the DSP)\n#pragma once\n#include <string_view>\nnamespace njo::phys\n{\n")
    f.write("    constexpr float RAT[9][16] = {\n" + ",\n".join("        { " + ", ".join("%.5ff" % v for v in row) + " }" for row in RAT) + " };\n")
    f.write("    constexpr float AEXP[9] = { " + ", ".join("%.2ff" % v for v in AEXP) + " };\n")
    f.write("    constexpr int PHY_BASE = %d, PHY_STRIDE = %d;\n" % (L.PHY_BASE, L.PHY_STRIDE))
    f.write("    inline int phyId (int o, int j) { return PHY_BASE + PHY_STRIDE * o + j; }\n")
    f.write("    inline int key (const char* name)   // parameter index j of a key such as \"phhitA\"\n    {\n")
    for q in L.PHY: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n")
    f.write("    inline const char* model (int m)\n    {\n        static const char* const n[9] = { %s };\n        return n[m < 0 ? 0 : (m > 8 ? 8 : m)];\n    }\n}\n" % ", ".join('"%s"' % m for m in L.PHY_MODELS))
print("ok")
