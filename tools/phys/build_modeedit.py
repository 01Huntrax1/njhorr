#!/usr/bin/env python3
"""Per-mode edits of the modal resonators (Physical source A / B and the Resonator stage), for the native resonator editor.
Run after build_phys.py and build_reso.py.  Idempotent.
Event modLoad (BankChunk): bank = slot * 3 + set (set 0 = Physical A, 1 = Physical B, 2 = Resonator stage), 48 floats = 16 modes x (frequency multiplier,
gain multiplier, decay multiplier); total <= 0 resets the set.  Multipliers are 1 when nothing is edited."""
import os, sys
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "patch", "Eisenpuls_Synth.cmajor")
s = open(PATCH).read()
if "// MODED" in s:
    print("already applied"); sys.exit(0)

def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:70], s.count(old))
    s = s.replace(old, new)

rep("    input event BankChunk tblLoad;", "    input event BankChunk modLoad;       // per-mode edits of the resonators: bank = slot * 3 + set (0 = Physical A, 1 = Physical B, 2 = Resonator stage)  // MODED\n    input event BankChunk tblLoad;")

DSP = '''    // ---------------- resonator mode edits (tools/phys/build_modeedit.py) ----------------
    // modEd[(slot * 3 + set) * 48 + 3 * mode + 0 / 1 / 2] = frequency / gain / decay multiplier of the mode (1 = unchanged); modEdVer[slot] changes with every edit
    // so the voices recompute their coefficients.
    float[1024] modEd;
    float[8]    modEdVer;

    void modEdInit()
    {
        for (int i = 0; i < 1024; ++i)
            modEd.at (i) = 1.0f;
    }

    event modLoad (BankChunk c)
    {
        int b = clamp (c.bank, 0, 17);

        if (c.total <= 0)
        {
            for (int i = 0; i < 48; ++i)
                modEd.at (b * 48 + i) = 1.0f;
        }
        else
        {
            for (int i = 0; i < min (c.count, 256); ++i)
            {
                int pos = c.offset + i;

                if (pos >= 0 && pos < 48)
                    modEd.at (b * 48 + pos) = clamp (c.data.at (i), (pos % 3) == 0 ? 0.1f : 0.0f, 8.0f);
            }
        }

        float v = modEdVer.at (b / 3) + 1.0f;
        modEdVer.at (b / 3) = v > 1000.0f ? 0.0f : v;
    }

'''
a = "    // coefficients of the 16 modes of resonator res"
rep(a, DSP + a)
rep("        fxInit();\n        cvInit();\n", "        fxInit();\n        cvInit();\n        modEdInit();\n")

# Physical source
rep("        int   cb    = o * 176 + 64 + res * 48;\n", "        int   cb    = o * 176 + 64 + res * 48;\n        int   eb    = (o * 3 + res) * 48;\n")
rep("""            float r = phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i));
            float f = f0 * r;
            float g = 0.0f;
            float c1 = 0.0f;
            float c2 = 0.0f;

            if (f < sr * 0.45f)
            {
                float w   = 6.2831853f * f / sr;
                float t60 = max (dec * float (pow (r, -damp)), 0.004f);
                float rr  = float (exp (-6.9078f / (t60 * sr)));
                float am  = abs (float (sin (3.14159265f * hit * float (i + 1)))) / float (pow (float (i + 1), aex));""",
"""            float r = phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i)) * modEd.at (eb + i * 3);
            float f = f0 * r;
            float g = 0.0f;
            float c1 = 0.0f;
            float c2 = 0.0f;

            if (f < sr * 0.45f)
            {
                float w   = 6.2831853f * f / sr;
                float t60 = max (dec * modEd.at (eb + i * 3 + 2) * float (pow (r, -damp)), 0.004f);
                float rr  = float (exp (-6.9078f / (t60 * sr)));
                float am  = abs (float (sin (3.14159265f * hit * float (i + 1)))) / float (pow (float (i + 1), aex)) * modEd.at (eb + i * 3 + 1);""")
rep("                float f = f0 * phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i));\n", "                float f = f0 * phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i)) * modEd.at (eb + i * 3);\n")
rep("+ phq (o, pb, 12) * 23.9f + phq (o, pb, 13) * 0.29f;", "+ phq (o, pb, 12) * 23.9f + phq (o, pb, 13) * 0.29f + modEdVer.at (o) * 0.0731f;")

# Resonator stage
rep("    void resCoefs (int vi, int cb, float f0, int model, float dec, float mat, float hit, float inh)\n    {\n", "    void resCoefs (int vi, int cb, float f0, int model, float dec, float mat, float hit, float inh, int eb)\n    {\n")
rep("""            float r  = phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i));
            float f  = f0 * r;
            float g  = 0.0f;
            float c1 = 0.0f;
            float c2 = 0.0f;

            if (f < sr * 0.45f)
            {
                float w   = 6.2831853f * f / sr;
                float t60 = max (dec * float (pow (r, -damp)), 0.004f);
                float rr  = float (exp (-6.9078f / (t60 * sr)));
                float am  = abs (float (sin (3.14159265f * hit * float (i + 1)))) / float (pow (float (i + 1), aex));""",
"""            float r  = phyRat.at (model * 16 + i) * (1.0f + inh * 0.004f * float (i * i)) * modEd.at (eb + i * 3);
            float f  = f0 * r;
            float g  = 0.0f;
            float c1 = 0.0f;
            float c2 = 0.0f;

            if (f < sr * 0.45f)
            {
                float w   = 6.2831853f * f / sr;
                float t60 = max (dec * modEd.at (eb + i * 3 + 2) * float (pow (r, -damp)), 0.004f);
                float rr  = float (exp (-6.9078f / (t60 * sr)));
                float am  = abs (float (sin (3.14159265f * hit * float (i + 1)))) / float (pow (float (i + 1), aex)) * modEd.at (eb + i * 3 + 1);""")
rep("op.at (ob + 60) * 7.1f + op.at (ob + 61) * 11.3f;", "op.at (ob + 60) * 7.1f + op.at (ob + 61) * 11.3f + modEdVer.at (o) * 0.0731f;")
rep("resCoefs (vi, b + 64, fr, mdl, op.at (ob + 58), op.at (ob + 59), op.at (ob + 60), op.at (ob + 61));", "resCoefs (vi, b + 64, fr, mdl, op.at (ob + 58), op.at (ob + 59), op.at (ob + 60), op.at (ob + 61), (o * 3 + 2) * 48);")
open(PATCH, "w").write(s)
print("ok")
