#!/usr/bin/env python3
"""Unison for the Alpha Juno source and two new unison parameters for every source (Unison Drift k=28, Unison Phase k=29).
Run after build_phys / build_juno (it converts the junoStep call site) and before build_mod.  Idempotent."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import layout as L
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "patch", "Eisenpuls_Synth.cmajor")
s = open(PATCH).read()
UK = [p for p in L.PARAMS if p[0] in (28, 29)]

DECL = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s ]];\n' % (
    1000 + 64 * o + p[0], o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6]))) for o in range(6) for p in UK)
HAND = "".join("    event param%d (float v) { opSet (%d, %d, v); }\n" % (1000 + 64 * o + p[0], o, p[0]) for o in range(6) for p in UK)

DSP = r'''    // ---------------- unison drift (tools/osc/build_uni.py) ----------------
    // Every unison voice of every slot wanders slowly (a new random target every 2048 samples, followed with a one-pole smoother): analog style detune movement.
    // Voice.phs 1752 + (slot * 7 + j) * 2 value, + 1 target, 1836 + slot countdown. Returns the value (-1..1) of unison voice j; call it for j = 0 first each sample.
    float uniDriftRaw (int vi, int o, int j, bool active)
    {
        if (! active)
            return 0.0f;

        if (j == 0)
        {
            float cnt = voices.at (vi).phs.at (1836 + o);

            if (cnt <= 0.0f)
            {
                cnt = 2048.0f;

                for (int k = 0; k < 7; ++k)
                    voices.at (vi).phs.at (1752 + (o * 7 + k) * 2 + 1) = nextNoise();
            }

            voices.at (vi).phs.at (1836 + o) = cnt - 1.0f;
        }

        int   di = 1752 + (o * 7 + j) * 2;
        float v  = voices.at (vi).phs.at (di);
        v += 0.0006f * (voices.at (vi).phs.at (di + 1) - v);
        voices.at (vi).phs.at (di) = v;
        return v;
    }

'''

def block(tag, body, anchor_re, indent="    "):
    global s
    a, z = indent + "// UNI-%s-BEGIN\n" % tag, indent + "// UNI-%s-END\n" % tag
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", DSP, r"^    // ---------------- MIDI ----------------")
block("DECL", DECL, r"^    input event float param1600 ")
block("HAND", HAND, r"^    event param1600 ")

# start phases: Unison Phase spreads the start phases of the voices (voice 0 keeps the Start Phase)
a = s.index("    void resetWtUni (int vi, int o)")
b = s.index("    // mip level for a note frequency", a)
s = s[:a] + '''    void resetWtUni (int vi, int o)
    {
        float spread = clamp (opv (o, 29), 0.0f, 1.0f);

        for (int j = 0; j < 7; ++j)
        {
            float64 rp = float64 (clamp (opv (o, 8), 0.0f, 1.0f));
            if (opv (o, 9) > 0.5f)
                rp = float64 (nextNoise() * 0.5f + 0.5f);
            else if (j > 0 && spread > 0.0f)
            {
                rp = rp + float64 (spread * (nextNoise() * 0.5f + 0.5f));
                rp = rp - float64 (floor (float (rp)));
            }

            voices.at (vi).wtUPh.at (o * 7 + j) = rp;
        }
    }

''' + s[b:]

# wavetable voices: drift
old = "            float   f  = clamp (freq * uniRatio.at (si), 1.0f, sr * 0.45f);"
new = "            float   f  = clamp (freq * uniRatio.at (si) * (1.0f + udr * uniDriftRaw (vi, o, j, udr > 0.0f)), 1.0f, sr * 0.45f);"
if old in s:
    s = s.replace(old, new, 1)
    old2 = "        for (int j = 0; j < n; ++j)\n        {\n            int     si = o * 7 + j;\n            float64 ph = voices"
    assert old2 in s
    s = s.replace(old2, "        float udr = clamp (opv (o, 28), 0.0f, 1.0f) * 0.007f;\n\n" + old2, 1)
    s = s.replace("freq * 0.9710f", "freq * 0.9640f").replace("freq * 1.0300f", "freq * 1.0380f")

# the junoStep call site (stereo)
old = "                        sL = junoStep (i, o, freq, pm);\n                        sR = sL;\n"
if old in s:
    s = s.replace(old, "                        float<2> jw = junoStep (i, o, freq, pm);\n                        sL = jw[0];\n                        sR = jw[1];\n                        stereo = true;\n", 1)
open(PATCH, "w").write(s)
print("ok")
