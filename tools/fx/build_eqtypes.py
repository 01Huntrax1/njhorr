#!/usr/bin/env python3
"""Parametric EQ: ten more band types (15..24).  Idempotent.  Run after build_eq.py.  Usage: build_eqtypes.py [patch.cmajor]
  15 Low Cut 6, 16 High Cut 6 (first order), 17 Low Shelf 6, 18 High Shelf 6 (first order shelves), 19 Low Shelf 24, 20 High Shelf 24 (two shelves),
  21 Notch 24, 22 Band Pass 24 (two sections), 23 Band Pass Flat (high pass + low pass, Q sets the width), 24 Formant (three peaks at f, 2.5 f, 3.6 f)
The type is stored as type / 16 (up to 1.5 now), so the eqLoad clamp is +-2 instead of +-1."""
import os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "patch", "Eisenpuls_Synth.cmajor")
s = open(PATCH).read()
if "// EQTYPES" in s:
    print("already applied"); sys.exit(0)
def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70]); s = s.replace(a, b)
rep("        else\n        {\n            b0 = 1.0f - al;  b1 = -2.0f * cw;  b2 = 1.0f + al;", '''        else if (kind >= 8 && kind <= 11)   // EQTYPES: first order sections (the biquad keeps b2 = a2 = 0)
        {
            float K = float (tan (w0 * 0.5f));
            float V = float (pow (10.0f, gDb / 20.0f));
            a0 = 1.0f + K;  a1 = K - 1.0f;
            if (kind == 8)       { b0 = K;  b1 = K; }
            else if (kind == 9)  { b0 = 1.0f;  b1 = -1.0f; }
            else if (kind == 10) { b0 = 1.0f + V * K;  b1 = V * K - 1.0f; }
            else                 { b0 = V + K;  b1 = K - V; }
        }
        else
        {
            b0 = 1.0f - al;  b1 = -2.0f * cw;  b2 = 1.0f + al;''')
rep("int   ty   = clamp (int (peqB.at (bi + 1) * 16.0f + 0.5f), 0, 14);", "int   ty   = clamp (int (peqB.at (bi + 1) * 16.0f + 0.5f), 0, 24);")
rep("            else\n            {\n                // comb: feed-forward (11) or feedback (12)", '''            else if (ty == 15) n = peqAddSec (s, n, 9, f, 0.0f, q, ch);
            else if (ty == 16) n = peqAddSec (s, n, 8, f, 0.0f, q, ch);
            else if (ty == 17) n = peqAddSec (s, n, 10, f, g, q, ch);
            else if (ty == 18) n = peqAddSec (s, n, 11, f, g, q, ch);
            else if (ty == 19) { n = peqAddSec (s, n, 1, f, g * 0.5f, q, ch); n = peqAddSec (s, n, 1, f, g * 0.5f, q, ch); }
            else if (ty == 20) { n = peqAddSec (s, n, 2, f, g * 0.5f, q, ch); n = peqAddSec (s, n, 2, f, g * 0.5f, q, ch); }
            else if (ty == 21) { n = peqAddSec (s, n, 6, f, 0.0f, q, ch); n = peqAddSec (s, n, 6, f, 0.0f, q, ch); }
            else if (ty == 22) { n = peqAddSec (s, n, 5, f, g * 0.5f, q, ch); n = peqAddSec (s, n, 5, f, g * 0.5f, q, ch); }
            else if (ty == 23)
            {
                float r = clamp (float (pow (2.0f, 0.5f / q)), 1.01f, 8.0f);
                n = peqAddSec (s, n, 3, max (f / r, 10.0f), 0.0f, 0.7071f, ch);
                n = peqAddSec (s, n, 4, min (f * r, sr * 0.45f), 0.0f, 0.7071f, ch);
            }
            else if (ty == 24)
            {
                float fg = g;
                n = peqAddSec (s, n, 0, f, fg, q, ch);
                if (f * 2.5f < sr * 0.45f) n = peqAddSec (s, n, 0, f * 2.5f, fg * 0.8f, q, ch);
                if (f * 3.6f < sr * 0.45f) n = peqAddSec (s, n, 0, f * 3.6f, fg * 0.64f, q, ch);
            }
            else
            {
                // comb: feed-forward (11) or feedback (12)''')
rep("peqB.at (b * 240 + pos) = clamp (c.data.at (i), -1.0f, 1.0f);", "peqB.at (b * 240 + pos) = clamp (c.data.at (i), -2.0f, 2.0f);   // EQTYPES: the type is type / 16")
s += "\n// EQTYPES\n"
open(PATCH, "w").write(s); print("patched")
