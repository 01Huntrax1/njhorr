#!/usr/bin/env python3
"""Adds the Wave Terrain source (Source type 2) to patch/Eisenpuls_Synth.cmajor.  An oscillator that reads a two dimensional terrain z = T(x, y) along a closed orbit
(an ellipse / Lissajous figure around a center) that is traversed once per cycle at the note frequency.  12 terrains, a second terrain with a morph, domain warp, fold,
orbit shape / rotation / ratio / phase, a slowly moving center, drive, bit depth and a smoothing low-pass.  The macro knobs are the slot parameters 24..27
(terrain, scale, warp, fold, ids 1024 + 64 * slot ...), the rest are ids TER_BASE + 16 * slot + j (layout.py TER) with the mod destinations 540 + 16 * slot + j.
Run after build_kick.py.  Idempotent.  Usage: build_ter.py [patch.cmajor]"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
K = L.TER
def tab(f): return ", ".join("%sf" % repr(float(f(p))) for p in K)
LO, HI = tab(lambda p: p[4]), tab(lambda p: p[5])
LOGF = tab(lambda p: 1 if p[1] in ("tratio", "tmrate") else 0)
DSP = r'''    // ---------------- Wave Terrain source (tools/osc/build_ter.py) ----------------
    // z = T (x, y) read along an orbit: x = cx + rx * shape (cos a), y = cy + ry * shape (sin (ratio * a + phase)), a = 2 pi * oscillator phase, the ellipse rotated
    // around its center.  The center can wobble slowly.  State per voice and slot in Voice.phs 2000 + 6 * slot: 0 phase, 1 smoothing low-pass, 2 / 3 DC blocker,
    // 4 phase of the moving center.
    float[96] terP;       // slot * 16 + parameter
    const float[16] trLo  = (@LO@);
    const float[16] trHi  = (@HI@);
    const float[16] trLog = (@LOG@);

    void terSet (int o, int j, float v)
    {
        terP.at (o * 16 + j) = v;
    }

    float terq (int o, int j)
    {
        float v = terP.at (o * 16 + j);
        float m = vmod.at (540 + 16 * o + j);

        if (m != 0.0f)
        {
            if (trLog.at (j) > 0.5f)
                v *= float (pow (2.0f, m * 3.0f));
            else
                v += m * 0.5f * (trHi.at (j) - trLo.at (j));

            v = clamp (v, trLo.at (j), trHi.at (j));
        }

        return v;
    }

    void terNoteOn (int vi, int o)
    {
        for (int i = 0; i < 6; ++i)
            voices.at (vi).phs.at (2000 + 6 * o + i) = 0.0f;
    }

    // the terrains: x, y in -1 .. 1 (the scale knob multiplies them), result in -1 .. 1
    float terFn (int t, float x, float y, float s)
    {
        float u  = x * s;
        float v  = y * s;
        float tp = 6.2831853f;
        float z  = 0.0f;

        if (t == 0)
            z = float (sin (tp * u) * sin (tp * v));
        else if (t == 1)
            z = float (sin (tp * 1.5f * s * sqrt (x * x + y * y)));
        else if (t == 2)
            z = u * u - v * v;
        else if (t == 3)
        {
            float cu = clamp (u, -1.0f, 1.0f);
            float cv = clamp (v, -1.0f, 1.0f);
            z = (4.0f * cu * cu * cu - 3.0f * cu) * (2.0f * cv * cv - 1.0f);
        }
        else if (t == 4)
            z = float (tanh (4.0f * sin (tp * u) * sin (tp * v)));
        else if (t == 5)
            z = float (sin (3.0f * atan2 (y, x) + tp * 1.5f * s * sqrt (x * x + y * y)));
        else if (t == 6)
            z = float (sin (tp * 1.5f * s * (abs (x) + abs (y))));
        else if (t == 7)
            z = float (sin (tp * u) + sin (tp * 1.37f * v) + sin (tp * 0.71f * (u + v))) * 0.3333f;
        else if (t == 8)
            z = float (cos (tp * u) + cos (tp * v)) * 0.5f;
        else if (t == 9)
        {
            float g0 = float (exp (-((u - 0.5f) * (u - 0.5f) + (v - 0.5f) * (v - 0.5f)) * 6.0f));
            float g1 = float (exp (-((u + 0.5f) * (u + 0.5f) + (v - 0.5f) * (v - 0.5f)) * 6.0f));
            float g2 = float (exp (-((u + 0.5f) * (u + 0.5f) + (v + 0.5f) * (v + 0.5f)) * 6.0f));
            float g3 = float (exp (-((u - 0.5f) * (u - 0.5f) + (v + 0.5f) * (v + 0.5f)) * 6.0f));
            z = (g0 - g1 + g2 - g3) * 1.6f;
        }
        else if (t == 10)
        {
            float a = 1.0f;

            for (int k = 0; k < 4; ++k)
            {
                z += float (sin (tp * a * u + float (k) * 1.7f) * sin (tp * a * v + float (k) * 0.9f)) / a;
                a *= 2.0f;
            }

            z *= 0.5333f;
        }
        else
            z = float (sin (tp * u + 3.0f * sin (tp * v)));

        return clamp (z, -1.0f, 1.0f);
    }

    // one sample: f0 = cycles per sample, pm = phase modulation (cycles); macro values come from the slot parameters
    float terStep (int vi, int o, float f0, float pm, int tA, float scale, float warp, float fold)
    {
        int   sb = 2000 + 6 * o;
        float dt = float (processor.period);
        float ph = voices.at (vi).phs.at (sb);
        float tp = 6.2831853f;

        float rp = ph + pm;
        rp = rp - float (floor (rp));
        float a  = tp * rp;

        float shp = terq (o, 7);
        float cs  = float (cos (a));
        float sn  = float (sin (terq (o, 5) * a + tp * terq (o, 6)));

        if (shp > 0.001f)
        {
            float ex = 1.0f - 0.75f * shp;
            cs = cs < 0.0f ? -float (pow (-cs, ex)) : float (pow (cs, ex));
            sn = sn < 0.0f ? -float (pow (-sn, ex)) : float (pow (sn, ex));
        }

        float velK = 1.0f + terq (o, 15) * (clamp (voices.at (vi).velRaw, 0.0f, 1.0f) - 0.5f) * 2.0f;
        float dx   = clamp (terq (o, 2) * velK, 0.0f, 1.0f) * cs;
        float dy   = clamp (terq (o, 3) * velK, 0.0f, 1.0f) * sn;
        float th   = tp * terq (o, 4);
        float x    = terq (o, 0) + dx * float (cos (th)) - dy * float (sin (th));
        float y    = terq (o, 1) + dx * float (sin (th)) + dy * float (cos (th));

        float md = terq (o, 9);

        if (md > 0.0005f)
        {
            float mp = voices.at (vi).phs.at (sb + 4) + terq (o, 8) * dt;
            mp = mp - float (floor (mp));
            voices.at (vi).phs.at (sb + 4) = mp;
            x += md * 0.5f * float (sin (tp * mp));
            y += md * 0.5f * float (cos (tp * 1.3f * mp));
        }

        x = clamp (x, -1.0f, 1.0f);
        y = clamp (y, -1.0f, 1.0f);

        if (warp > 0.001f)
        {
            float x2 = x + warp * 0.5f * float (sin (tp * (y + 0.13f)));
            float y2 = y + warp * 0.5f * float (sin (tp * (1.3f * x + 0.4f)));
            x = clamp (x2, -1.0f, 1.0f);
            y = clamp (y2, -1.0f, 1.0f);
        }

        float s     = 0.25f * float (pow (16.0f, scale));
        float morph = terq (o, 11);
        float z;

        if (morph < 0.001f)
            z = terFn (tA, x, y, s);
        else if (morph > 0.999f)
            z = terFn (clamp (int (terq (o, 10) + 0.5f), 0, 11), x, y, s);
        else
            z = terFn (tA, x, y, s) * (1.0f - morph) + terFn (clamp (int (terq (o, 10) + 0.5f), 0, 11), x, y, s) * morph;

        if (fold > 0.001f)
            z = z * (1.0f - fold) + fold * float (sin (z * (1.0f + 4.0f * fold) * 1.5708f));

        float dr = terq (o, 13);

        if (dr > 0.001f)
        {
            float g = 1.0f + dr * 6.0f;
            z = float (tanh (z * g)) / float (tanh (g));
        }

        float bits = terq (o, 14);

        if (bits < 15.95f)
        {
            float q = float (pow (2.0f, bits - 1.0f));
            z = floor (z * q + 0.5f) / q;
        }

        // smoothing low-pass (cutoff follows the note), then the DC blocker
        float sm = terq (o, 12);
        float om = 1.0f - sm;
        float lg = clamp (1.0f - float (exp (-tp * f0 * (3.0f + 200.0f * om * om * om))), 0.0f, 1.0f);
        float lp = voices.at (vi).phs.at (sb + 1);
        lp += lg * (z - lp);
        voices.at (vi).phs.at (sb + 1) = lp;

        float x1 = voices.at (vi).phs.at (sb + 2);
        float y1 = voices.at (vi).phs.at (sb + 3);
        float yo = lp - x1 + 0.995f * y1;
        voices.at (vi).phs.at (sb + 2) = lp;
        voices.at (vi).phs.at (sb + 3) = yo;

        ph += f0;
        ph = ph - float (floor (ph));
        voices.at (vi).phs.at (sb) = ph;

        return yo * 0.8f;
    }

'''.replace("@LO@", LO).replace("@HI@", HI).replace("@LOG@", LOGF)
DECL = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];\n' % (
    L.ter_id(o, p[0]), o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6])), ", step: 1.0" if p[8] == "sel" else "")
    for o in range(L.OSC_COUNT) for p in K)
HAND = "".join("    event param%d (float v) { terSet (%d, %d, v); }\n" % (L.ter_id(o, p[0]), o, p[0]) for o in range(L.OSC_COUNT) for p in K)
INIT = "".join("            terP.at (io * 16 + %d) = %sf;\n" % (p[0], repr(float(p[6]))) for p in K)
s = open(PATCH).read()
def block(tag, body, anchor_re, indent="    "):
    global s
    a, z = "%s// TER-%s-BEGIN\n" % (indent, tag), "%s// TER-%s-END\n" % (indent, tag)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", DSP, r"^    // PHYS-DSP-BEGIN")
block("DECL", DECL, r"^    input event float param1600 ")
block("HAND", HAND, r"^    event param1600 ")
block("INIT", INIT, r"^            op\.at \(io \* 64 \+ 11\) = 3\.0f;\n", "            ")
# macro parameters 24..27 (were the Plaits engine / harmonics / timbre / morph)
for o in range(L.OSC_COUNT):
    b = L.BASE + 64 * o
    for k, name, lo, hi, init, step in ((24, "Terrain A", 0, 11, 0, True), (25, "Terrain Scale", 0, 1, 0.5, False), (26, "Terrain Warp", 0, 1, 0, False), (27, "Terrain Fold", 0, 1, 0, False)):
        s = re.sub(r'(input event float param%d )\[\[ name: "OSC %d [^"]*", min: [^,]*, max: [^,]*, init: [^,\]]*(, step: 1\.0)? \]\];' % (b + k, o + 1),
                   '\\1[[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];' % (o + 1, name, repr(float(lo)), repr(float(hi)), repr(float(init)), ", step: 1.0" if step else ""), s)
for k, v in ((24, "0.0f"), (25, "0.5f"), (26, "0.0f"), (27, "0.0f")):
    s = re.sub(r"(op\.at \(io \* 64 \+ %d\) = )[0-9.]+f;" % k, r"\g<1>%s;" % v, s)
def rep(old, new):
    global s
    if new in s: return
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("                    phyNoteOn (v, o);\n", "                    phyNoteOn (v, o);\n                    terNoteOn (v, o);\n")
open(PATCH, "w").write(s)
print("ok")
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoTer.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/osc/build_ter.py: parameter ids of the Wave Terrain source\n#pragma once\n#include <cmath>\n#include <string_view>\nnamespace njo::ter\n{\n")
    f.write("    constexpr int TER_BASE = %d, TER_STRIDE = %d;\n" % (L.TER_BASE, L.TER_STRIDE))
    f.write("    inline int terId (int o, int j) { return TER_BASE + TER_STRIDE * o + j; }\n")
    f.write("    inline int key (const char* name)   // parameter index j of a key such as \"trx\"\n    {\n")
    for q in K: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n")
    f.write(r'''    // the terrains exactly as the DSP evaluates them (x, y in -1 .. 1, s = scale factor), result -1 .. 1
    inline double terrain (int t, double x, double y, double s)
    {
        const double u = x * s, v = y * s, tp = 6.283185307179586, r = std::sqrt (x * x + y * y);
        auto cl = [] (double a) { return a < -1.0 ? -1.0 : (a > 1.0 ? 1.0 : a); };
        double z = 0.0;
        switch (t)
        {
            case 0: z = std::sin (tp * u) * std::sin (tp * v); break;
            case 1: z = std::sin (tp * 1.5 * s * r); break;
            case 2: z = u * u - v * v; break;
            case 3: { const double a = cl (u), b = cl (v); z = (4 * a * a * a - 3 * a) * (2 * b * b - 1); break; }
            case 4: z = std::tanh (4.0 * std::sin (tp * u) * std::sin (tp * v)); break;
            case 5: z = std::sin (3.0 * std::atan2 (y, x) + tp * 1.5 * s * r); break;
            case 6: z = std::sin (tp * 1.5 * s * (std::abs (x) + std::abs (y))); break;
            case 7: z = (std::sin (tp * u) + std::sin (tp * 1.37 * v) + std::sin (tp * 0.71 * (u + v))) / 3.0; break;
            case 8: z = (std::cos (tp * u) + std::cos (tp * v)) * 0.5; break;
            case 9: { auto g = [&] (double a, double b) { return std::exp (-((u - a) * (u - a) + (v - b) * (v - b)) * 6.0); }; z = (g (0.5, 0.5) - g (-0.5, 0.5) + g (-0.5, -0.5) - g (0.5, -0.5)) * 1.6; break; }
            case 10: { double a = 1.0; for (int k = 0; k < 4; ++k) { z += std::sin (tp * a * u + k * 1.7) * std::sin (tp * a * v + k * 0.9) / a; a *= 2.0; } z *= 0.5333; break; }
            default: z = std::sin (tp * u + 3.0 * std::sin (tp * v)); break;
        }
        return cl (z);
    }
}
''')
