#!/usr/bin/env python3
"""Wavetable source rework, patch/Eisenpuls_Synth.cmajor.  Idempotent.  Usage: build_wt2.py [patch.cmajor]
 * up to 256 frames of 2048 samples per slot (was 128): source memory 524288 samples, mip tables 256 frames x 4096
 * frame interpolation (param Morph): Crossfade (as before) / Smooth (cubic over four frames) / Stepped (nearest frame)
 * warp modes 9..17 (Smear, Ripple, Stairs, Fold Phase, Clip, Rectify, Wrap, Asym, Drive) in addition to 1..8, a third warp stage (Warp 3), Tone (darkens the table by reading a lower mip level)
 * parameters: ids WT_BASE (12500) + 16 * slot + j"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
WT_BASE, WT_STRIDE, NMODES = 12500, 16, 18
WARP_NAMES = ["Off", "Bend +", "Bend −", "Sync", "PWM", "Mirror", "Flip", "Quantize", "Fold", "Smear", "Ripple", "Stairs", "Fold Phase", "Clip", "Rectify", "Wrap", "Asym", "Drive"]
# j, key, label, short, min, max, init, unit, kind, labels
WT = [
 (0, "w3m",   "Warp 3 Mode",   "Warp 3",    0, NMODES - 1, 0.0, "", "sel", None),
 (1, "w3a",   "Warp 3 Amount", "Warp 3 Amt",0, 1, 0.5, "", "sld", None),
 (2, "wmorph","WT Morph",      "Morph",     0, 2, 0.0, "", "btn", ["Fade", "Smooth", "Stepped"]),
 (3, "wtone", "WT Tone",       "Tone",      0, 1, 1.0, "", "sld", None),
]
def wt_id(o, j): return WT_BASE + WT_STRIDE * o + j

WARP = r'''    float wtWarpPhase (int mode, float amt, float ph)   // WT2-WARP
    {
        if (mode == 1)
            return float (pow (ph, 1.0f + 3.0f * amt));                    // bend +

        if (mode == 2)
            return 1.0f - float (pow (1.0f - ph, 1.0f + 3.0f * amt));      // bend -

        if (mode == 3)
        {
            float x = ph * (1.0f + 7.0f * amt);                           // sync
            return x - float (floor (x));
        }

        if (mode == 4)
        {
            float w = 0.5f - 0.45f * amt;                                 // pulse width
            if (ph < w) return ph * 0.5f / w;
            return 0.5f + (ph - w) * 0.5f / (1.0f - w);
        }

        if (mode == 5)
        {
            float x = ph * (1.0f + amt);                                  // mirror
            if (x > 1.0f) x = 2.0f - x;
            return clamp (x, 0.0f, 1.0f);
        }

        if (mode == 6)
            return ph * (1.0f - amt) + (1.0f - ph) * amt;                 // flip

        if (mode == 9)
            return ph + amt * 0.159155f * float (sin (6.2831853f * ph));  // smear: a smooth bulge of the phase

        if (mode == 10)
            return ph + amt * 0.05f * float (sin (31.415927f * ph));      // ripple: fast phase wobble (adds harmonics)

        if (mode == 11)
        {
            float x = ph * 4.0f;                                          // stairs: four smoothed steps per cycle
            float i = float (floor (x));
            float f = x - i;
            float s = f * f * (3.0f - 2.0f * f);
            return (i + f + (s - f) * amt) * 0.25f;
        }

        if (mode == 12)
        {
            float x = ph * (1.0f + 3.0f * amt) * 0.5f;                    // fold phase: the phase runs forth and back
            float t = (x - float (floor (x))) * 2.0f;
            return t < 1.0f ? t : 2.0f - t;
        }

        return ph;
    }

    // Amplitude warp (modes 7, 8, 13 .. 17) of one warp slot
    float wtWarpAmp (int mode, float amt, float y)
    {
        if (mode == 7)
        {
            float s = 2.0f + (1.0f - amt) * 254.0f;                       // quantize
            return float (floor (y * s + 0.5f)) / s;
        }

        if (mode == 8)
            return y * (1.0f - amt) + amt * float (sin (y * (1.0f + 4.0f * amt) * 1.5708f));   // fold

        if (mode == 13)
            return clamp (y * (1.0f + 6.0f * amt), -1.0f, 1.0f);           // clip

        if (mode == 14)
            return y + (float (abs (y)) - y) * amt;                        // rectify (the DC is removed afterwards)

        if (mode == 15)
        {
            float z = y * (1.0f + 3.0f * amt);                            // wrap around
            return z - 2.0f * float (floor ((z + 1.0f) * 0.5f));
        }

        if (mode == 16)
            return y > 0.0f ? y : y * (1.0f - 0.9f * amt);                 // asymmetric

        if (mode == 17)
        {
            float d = 1.0f + 6.0f * amt;                                  // soft drive
            return float (tanh (y * d)) / float (tanh (d));
        }

        return y;
    }

    bool wtIsAmp (int m)
    {
        return m == 7 || m == 8 || m >= 13;
    }

    bool wtIsPhase (int m)
    {
        return (m >= 1 && m <= 6) || (m >= 9 && m <= 12);
    }

'''

STEP = r'''    // wavetable read (WT2): frames fa / fb crossfaded by ff, or (fmode 1) the cubic of four frames fm / fa / fb / fc, phase (0..1) scans one cycle of mip level lvl
    float wtRead (int o, int lvl, float64 phase, int fa, int fb, float ff, int fmode, int fm, int fc)
    {
        int   len = 2048 >> lvl;
        int   off = 4096 - (4096 >> lvl);
        float x   = float (phase) * float (len);
        float va  = wtMipRead ((o * 256 + fa) * 4096 + off, len, x);

        if (fb == fa || ff <= 0.0f)
            return va;

        float vb = wtMipRead ((o * 256 + fb) * 4096 + off, len, x);

        if (fmode == 1)
        {
            float p0 = wtMipRead ((o * 256 + fm) * 4096 + off, len, x);
            float p3 = wtMipRead ((o * 256 + fc) * 4096 + off, len, x);
            return va + 0.5f * ff * (vb - p0 + ff * (2.0f * p0 - 5.0f * va + 4.0f * vb - p3 + ff * (3.0f * (va - vb) + p3 - p0)));
        }

        return va + (vb - va) * ff;
    }

    // one step of the wavetable slot o on voice vi; pm = phase modulation in cycles (FM matrix); returns the stereo sum
    float<2> wtStep (int o, int vi, float freq, float pos, int fl, float pm, float a1m, float a2m)
    {
        float sr  = float (processor.frequency);
        int   n   = uniCnt.at (o);
        int   m1  = clamp (int (opv (o, 18) + 0.5f), 0, 17);
        int   m2  = clamp (int (opv (o, 20) + 0.5f), 0, 17);
        int   m3  = clamp (int (wtP.at (o * 16) + 0.5f), 0, 17);
        float a1  = clamp (opv (o, 19) + a1m * 0.5f, 0.0f, 1.0f);
        float a2  = clamp (opv (o, 21) + a2m * 0.5f, 0.0f, 1.0f);
        float a3  = clamp (wtP.at (o * 16 + 1), 0.0f, 1.0f);
        int   fmode = clamp (int (wtP.at (o * 16 + 2) + 0.5f), 0, 2);
        int   lvBias = int ((1.0f - clamp (wtP.at (o * 16 + 3), 0.0f, 1.0f)) * 6.0f + 0.5f);
        float sL  = 0.0f;
        float sR  = 0.0f;

        int   nFr = max (wtFr.at (o), 1);
        float fp  = clamp (pos, 0.0f, 1.0f) * float (nFr - 1);
        int   fa  = clamp (int (fp), 0, nFr - 1);
        int   fb  = min (fa + 1, nFr - 1);
        float ff  = fp - float (fa);

        if (fmode == 2)
        {
            fa = clamp (int (fp + 0.5f), 0, nFr - 1);
            fb = fa;
            ff = 0.0f;
        }

        int fm = max (fa - 1, 0);
        int fc = min (fb + 1, nFr - 1);

        // the unison voices are at most +-50 cents (a ratio of 0.9715 .. 1.0293) apart: when the lowest and the highest fall into the same
        // mip level every voice does, and the level is looked up twice instead of once per voice
        int lvlAll = -1;

        if (n > 2 && opv (o, 17) < 3.5f)
        {
            int lvLo = wtLevel (clamp (freq * 0.9640f, 1.0f, sr * 0.45f));
            int lvHi = wtLevel (clamp (freq * 1.0380f, 1.0f, sr * 0.45f));
            if (lvLo == lvHi)
                lvlAll = lvLo;
        }

        // Aliasing switch: no band-limiting, always the full level
        if (wtAlias.at (o) > 0.5f)
            lvlAll = 0;

        float udr = clamp (opv (o, 28), 0.0f, 1.0f) * 0.007f;

        for (int j = 0; j < n; ++j)
        {
            int     si = o * 16 + j;
            float64 ph = voices.at (vi).wtUPh.at (si);
            float   f  = clamp (freq * uniRatio.at (si) * (1.0f + udr * uniDriftRaw (vi, o, j, udr > 0.0f)), 1.0f, sr * 0.45f);

            float rp = float (ph);
            if (pm != 0.0f)
            {
                rp = rp + pm;
                rp = rp - float (floor (rp));
            }
            if (wtIsPhase (m1)) rp = wtWarpPhase (m1, a1, rp);
            if (wtIsPhase (m2)) rp = wtWarpPhase (m2, a2, rp);
            if (wtIsPhase (m3)) rp = wtWarpPhase (m3, a3, rp);
            float64 rph = float64 (clamp (rp, 0.0f, 0.99999f));

            int lv = lvlAll >= 0 ? lvlAll : wtLevel (f);
            if (lvBias > 0) lv = min (lv + lvBias, 8);
            float y = wtRead (o, lv, rph, fa, fb, ff, fmode, fm, fc);

            if (wtIsAmp (m1)) y = wtWarpAmp (m1, a1, y);
            if (wtIsAmp (m2)) y = wtWarpAmp (m2, a2, y);
            if (wtIsAmp (m3)) y = wtWarpAmp (m3, a3, y);

            sL += y * uniGL.at (si);
            sR += y * uniGR.at (si);

            ph += float64 (f) * processor.period;
            if (ph >= 1.0) ph -= 1.0;
            voices.at (vi).wtUPh.at (si) = ph;
        }

        // warping changes the average level of the cycle: remove the DC it creates (bypassed without warp)
        int zi = o * 4;

        if (m1 != 0 || m2 != 0 || m3 != 0)
        {
            float yl = sL - voices.at (vi).wtDcS.at (zi)     + 0.9995f * voices.at (vi).wtDcS.at (zi + 1);
            float yr = sR - voices.at (vi).wtDcS.at (zi + 2) + 0.9995f * voices.at (vi).wtDcS.at (zi + 3);
            voices.at (vi).wtDcS.at (zi)     = sL;
            voices.at (vi).wtDcS.at (zi + 1) = yl;
            voices.at (vi).wtDcS.at (zi + 2) = sR;
            voices.at (vi).wtDcS.at (zi + 3) = yr;
            sL = yl;
            sR = yr;
        }
        else
        {
            voices.at (vi).wtDcS.at (zi)     = 0.0f;
            voices.at (vi).wtDcS.at (zi + 1) = 0.0f;
            voices.at (vi).wtDcS.at (zi + 2) = 0.0f;
            voices.at (vi).wtDcS.at (zi + 3) = 0.0f;
        }

        return float<2> (sL, sR);
    }

'''

s = open(PATCH).read()
def rep(old, new, cnt=1):
    global s
    if new in s: return
    assert s.count(old) == cnt, (old[:80], s.count(old))
    s = s.replace(old, new)
def block(t, body, anchor_re, indent="    "):
    global s
    a, z = "%s// WT2-%s-BEGIN\n" % (indent, t), "%s// WT2-%s-END\n" % (indent, t)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + t)
    s = s[:m.start()] + a + body + z + s[m.start():]
# warp functions
if "// WT2-WARP" not in s:
    a = s.index("    float wtWarpPhase (int mode, float amt, float ph)")
    b = s.index("    float nextNoise()")
    s = s[:a] + WARP + s[b:]
# wtRead + wtStep
if "WT2): frames fa / fb" not in s:
    a = s.index("    // wavetable read: frames fa / fb crossfaded by ff")
    b = s.index("    // linear-interpolated sample read (mono sum of the memory")
    s = s[:a] + STEP + s[b:]
# memory: 256 frames, 524288 samples per slot
rep("    float[1572864] wtBuf;         // source, slot * 262144\n    float[4194304] wtMip;         // (slot * 128 + frame) * 4096 + level offset\n",
    "    float[4194304] wtBuf;         // source, slot * 524288\n    float[8388608] wtMip;         // (slot * 256 + frame) * 4096 + level offset\n    float[96]      wtP;           // WT2: slot * 16 + parameter (Warp 3, Morph, Tone)\n")
rep("        int base = o * 262144 + f * fl;\n", "        int base = o * 524288 + f * fl;\n")
rep("        int mb = (o * 128 + f) * 4096;\n", "        int mb = (o * 256 + f) * 4096;\n")
rep("        wtFr.at (o)   = clamp (len / fl, 1, 128);\n", "        wtFr.at (o)   = clamp (len / fl, 1, 256);\n")
rep("        int base = o * 262144;\n\n        for (int i = 0; i < cnt; ++i)\n        {\n            int pos = c.offset + i;\n            if (pos >= 0 && pos < 262144)\n                wtBuf.at",
    "        int base = o * 524288;\n\n        for (int i = 0; i < cnt; ++i)\n        {\n            int pos = c.offset + i;\n            if (pos >= 0 && pos < 524288)\n                wtBuf.at")
rep("            wtLen.at (o) = clamp (c.total, 1, 262144);\n", "            wtLen.at (o) = clamp (c.total, 1, 524288);\n")
# parameters
decl = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];\n' % (wt_id(o, p[0]), o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6])), ", step: 1.0" if p[8] in ("sel", "btn") else "") for o in range(6) for p in WT)
hand = "".join("    event param%d (float v) { wtP.at (%d) = v; }\n" % (wt_id(o, p[0]), o * 16 + p[0]) for o in range(6) for p in WT)
init = "".join("            wtP.at (io * 16 + %d) = %sf;\n" % (p[0], repr(float(p[6]))) for p in WT)
block("DECL", decl, r"^    input event float param1600 ")
block("HAND", hand, r"^    event param1600 ")
block("INIT", init, r"^            op\.at \(io \* 64 \+ 11\) = 3\.0f;\n", "            ")
s = re.sub(r'(name: "OSC \d Warp [12] Mode", min: 0\.0, max: )\d+\.0', r'\g<1>%d.0' % (NMODES - 1), s)
open(PATCH, "w").write(s)
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoWt.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/osc/build_wt2.py: parameter ids of the Wavetable extras\n#pragma once\n#include <string_view>\nnamespace njo::wt\n{\n")
    f.write("    constexpr int WT_BASE = %d, WT_STRIDE = %d;\n    inline int wtId (int o, int j) { return WT_BASE + WT_STRIDE * o + j; }\n" % (WT_BASE, WT_STRIDE))
    f.write("    inline int key (const char* name)\n    {\n")
    for q in WT: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n}\n")
print("ok")
