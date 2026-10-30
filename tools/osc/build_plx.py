#!/usr/bin/env python3
"""Adds the Plaits extras (accent, aux mix, envelope / velocity / key modulation of Harmonics-Timbre-Morph, low-pass gate, drive, bit / rate crush, pitch envelope)
to patch/Eisenpuls_Synth.cmajor.  Parameters: ids PLX_BASE + 16 * slot + j (layout.py PLX), mod destinations 540 + 16 * slot + j.  Run after build_kick.py / build_alias.py.  Idempotent."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
K = L.PLX
def tab(f): return ", ".join("%sf" % repr(float(f(p))) for p in K)
LO, HI = tab(lambda p: p[4]), tab(lambda p: p[5])
LOGF = tab(lambda p: 1 if p[1] in ("xedec", "xlpgdec") else 0)
DSP = r'''    // ---------------- Plaits extras (tools/osc/build_plx.py) ----------------
    // Wrapper around plaitsStep: accent, aux output mix, a decaying envelope (and velocity / key) that modulates Harmonics, Timbre and Morph, a pitch envelope,
    // a low-pass gate (vactrol style: one pole low-pass plus VCA that follow a decaying envelope), drive and a bit / rate crusher.  State per instance (voice * 6 + slot).
    float[96] plxP;       // slot * 16 + parameter
    const float[16] pxLo  = (@LO@);
    const float[16] pxHi  = (@HI@);
    const float[16] pxLog = (@LOG@);
    float[48] plxEnv;     // decaying envelope (1 -> 0) of the note
    float[48] plxLe;      // LPG envelope
    float[48] plxLp;      // LPG low-pass state
    float[48] plxHold;    // sample and hold of the rate reducer
    float[48] plxHc;      // counter of the rate reducer
    float plLastAux = 0.0f;

    void plxSet (int o, int j, float v)
    {
        plxP.at (o * 16 + j) = v;
    }

    float plxq (int o, int j)
    {
        float v = plxP.at (o * 16 + j);
        float m = vmod.at (540 + 16 * o + j);

        if (m != 0.0f)
        {
            if (pxLog.at (j) > 0.5f)
                v *= float (pow (2.0f, m * 4.0f));
            else
                v += m * 0.5f * (pxHi.at (j) - pxLo.at (j));

            v = clamp (v, pxLo.at (j), pxHi.at (j));
        }

        return v;
    }

    float plxStep (int vi, int o, int eng, float f0, float pm, float harm, float timb, float morph, bool gate)
    {
        int   inst = vi * 6 + o;
        float dt   = float (processor.period);

        float env = plxEnv.at (inst);
        env -= env * clamp (dt * 4.6f / (plxq (o, 2) * 0.001f), 0.0f, 1.0f);
        plxEnv.at (inst) = env;

        float vel = clamp (voices.at (vi).velRaw, 0.0f, 1.0f);
        float key = clamp ((float (voices.at (vi).noteNumber) - 60.0f) / 48.0f, -1.0f, 1.0f);

        float h = clamp (harm  + plxq (o, 3) * env, 0.0f, 1.0f);
        float t = clamp (timb  + plxq (o, 4) * env + plxq (o, 6) * (vel - 0.5f) * 2.0f + plxq (o, 15) * key, 0.0f, 1.0f);
        float m = clamp (morph + plxq (o, 5) * env + plxq (o, 7) * (vel - 0.5f) * 2.0f, 0.0f, 1.0f);

        float y = plaitsStep (vi, o, eng, f0, pm + plxq (o, 14) * env / 12.0f, h, t, m, gate, plxq (o, 0));

        float ax = plxq (o, 1);

        if (ax > 0.0f)
            y += plLastAux * ax * 0.7f;

        // low-pass gate
        float lg = plxq (o, 8);

        if (lg > 0.0f)
        {
            float le  = plxLe.at (inst);
            le -= le * clamp (dt * 4.6f / (plxq (o, 9) * 0.001f), 0.0f, 1.0f);
            plxLe.at (inst) = le;
            float k   = 1.0f - lg * (1.0f - le);
            float col = plxq (o, 10);
            float kk  = max (k, 0.0f);
            float gc  = 0.002f + 0.998f * float (pow (kk, 0.5f + 2.0f * col));
            float lp  = plxLp.at (inst);
            lp += gc * (y - lp);
            plxLp.at (inst) = lp;
            y = lp * float (pow (kk, 1.5f - col));
        }

        float dr = plxq (o, 11);

        if (dr > 0.001f)
        {
            float g = 1.0f + dr * 9.0f;
            y = float (tanh (y * g)) / float (tanh (g * 0.5f)) * 0.5f;
        }

        float bits = plxq (o, 12);

        if (bits < 15.95f)
        {
            float q = float (pow (2.0f, bits - 1.0f));
            y = floor (y * q + 0.5f) / q;
        }

        float rt = plxq (o, 13);

        if (rt > 0.001f)
        {
            float c = plxHc.at (inst) - 1.0f;

            if (c <= 0.0f)
            {
                plxHold.at (inst) = y;
                c = 1.0f + rt * 31.0f;
            }

            plxHc.at (inst) = c;
            y = plxHold.at (inst);
        }

        return y;
    }

'''.replace("@LO@", LO).replace("@HI@", HI).replace("@LOG@", LOGF)
DECL = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s ]];\n' % (
    L.plx_id(o, p[0]), o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6]))) for o in range(L.OSC_COUNT) for p in K)
HAND = "".join("    event param%d (float v) { plxSet (%d, %d, v); }\n" % (L.plx_id(o, p[0]), o, p[0]) for o in range(L.OSC_COUNT) for p in K)
INIT = "".join("            plxP.at (io * 16 + %d) = %sf;\n" % (p[0], repr(float(p[6]))) for p in K)
s = open(PATCH).read()
def block(tag, body, anchor_re, indent="    "):
    global s
    a, z = "%s// PLX-%s-BEGIN\n" % (indent, tag), "%s// PLX-%s-END\n" % (indent, tag)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", DSP, r"^    // PHYS-DSP-BEGIN")
block("DECL", DECL, r"^    input event float param1600 ")
block("HAND", HAND, r"^    event param1600 ")
block("INIT", INIT, r"^            op\.at \(io \* 64 \+ 11\) = 3\.0f;\n", "            ")
def rep(old, new):
    global s
    if new in s: return
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
# plaitsStep: accent argument, aux of the played sample, state reset on a new engine / note
rep("float plaitsStep (int vi, int o, int eng, float f0, float pm, float harm, float timb, float morph, bool gate)",
    "float plaitsStep (int vi, int o, int eng, float f0, float pm, float harm, float timb, float morph, bool gate, float accent)")
rep("plRenderBlock (inst, clamp (eng, 0, 23), trig, note, harm, timb, morph, 0.8f);", "plRenderBlock (inst, clamp (eng, 0, 23), trig, note, harm, timb, morph, accent);")
rep("        plPos.at (inst) = pos + 1;\n        return plOut.at (inst * 12 + pos);",
    "        plPos.at (inst) = pos + 1;\n        plLastAux = plAux.at (inst * 12 + pos);\n        return plOut.at (inst * 12 + pos);")
rep("            plLimPeak.at (inst) = 0.5f;\n            plInitEngine (inst, eng);",
    "            plLimPeak.at (inst) = 0.5f;\n            for (int i = 0; i < 12; ++i)\n                plAux.at (inst * 12 + i) = 0.0f;\n            plInitEngine (inst, eng);")
rep("        plTrigPending.at (inst) = 1;\n        plPos.at (inst) = 12;",
    "        plTrigPending.at (inst) = 1;\n        plxEnv.at (inst) = 1.0f;\n        plxLe.at (inst) = 1.0f;\n        plxHc.at (inst) = 0.0f;\n        plPos.at (inst) = 12;")
rep("sL = plaitsStep (i, o, int (op.at (ob + 24) + 0.5f)", "sL = plxStep (i, o, int (op.at (ob + 24) + 0.5f)")
# mod destinations 0..635
DMAX = L.N_DST_TOTAL - 1
s = s.replace("0, 539)", "0, %d)" % DMAX).replace("max: 539.0", "max: %d.0" % DMAX).replace("(0-539, see Dest list)", "(0-%d, see Dest list)" % DMAX)
open(PATCH, "w").write(s)
print("ok")
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoPlx.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/osc/build_plx.py: parameter ids of the Plaits extras\n#pragma once\n#include <string_view>\nnamespace njo::plx\n{\n")
    f.write("    constexpr int PLX_BASE = %d, PLX_STRIDE = %d;\n" % (L.PLX_BASE, L.PLX_STRIDE))
    f.write("    inline int plxId (int o, int j) { return PLX_BASE + PLX_STRIDE * o + j; }\n")
    f.write("    inline int key (const char* name)   // parameter index j of a key such as \"xlpg\"\n    {\n")
    for q in K: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n}\n")
