#!/usr/bin/env python3
"""Envelope generator rework (DSP), patch/Eisenpuls_Synth.cmajor.  Idempotent.  Usage: build_env2.py [patch.cmajor]
One shared stage machine (envX) for the 10 mod envelopes (k 0..9), the amp envelope (k 10) and the 6 filter envelopes (k 11..16):
 * Delay, Hold (after the attack), Level (peak), Vel (velocity -> peak level), Key (key tracking of the times, +-1 = time x 2^(-+octaves above C4))
 * curves of Attack (power law), Decay and Release (shaped fall; 0 = the old exponential), Loop (attack - decay cycles while the note is held; mod / filter envelopes)
 * all defaults sound like the old envelopes.   parameters: ids ENV2_BASE (13300) + 16 * k + j"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
BASE, STRIDE, NK = 13300, 16, 17
# j, key, array, label, short, min, max, init, unit, kind, labels
E2 = [
 (0, "delay", "xeDelay", "Delay",       "Delay",  0, 5000, 0.0, "ms", "sld", None),
 (1, "hold",  "xeHold",  "Hold",        "Hold",   0, 5000, 0.0, "ms", "sld", None),
 (2, "ac",    "xeAC",    "Attack Curve","A Curve",-1, 1,    0.0, "",   "sld", None),
 (3, "dc",    "xeDC",    "Decay Curve", "D Curve",-1, 1,    0.0, "",   "sld", None),
 (4, "rc",    "xeRC",    "Release Curve","R Curve",-1, 1,   0.0, "",   "sld", None),
 (5, "vel",   "xeVel",   "Velocity",    "Vel",    0, 1,    0.0, "",   "sld", None),
 (6, "key",   "xeKey",   "Key Track",   "Key",   -1, 1,    0.0, "",   "sld", None),
 (7, "loop",  "xeLoop",  "Loop",        "Loop",   0, 1,    0.0, "",   "btn", ["Loop Off", "Loop On"]),
 (8, "lvl",   "xeLvl",   "Level",       "Level",  0, 1,    1.0, "",   "sld", None),
]
def eid(k, j): return BASE + STRIDE * k + j
def ename(k): return "Mod Env %d" % (k + 1) if k < 10 else ("Amp Env" if k == 10 else "OSC %d Filter Env" % (k - 10))

CODE = r'''    // ENV2-BEGIN
    struct EnvR
    {
        int   st;
        float lv;
    }

    // remaining fraction (1 -> 0) of a shaped fall at progress q (0..1); c = 0 is about the old exponential (99 % at the end), -1 nearly linear, +1 very snappy
    float envFall (float q, float c)
    {
        float k = 5.0f + 6.0f * c;

        if (q >= 1.0f)
            return 0.0f;

        if (abs (k) < 0.01f)
            return 1.0f - q;

        return (float (exp (-k * q)) - float (exp (-k))) / (1.0f - float (exp (-k)));
    }

    // true while every extra of envelope k is at its default
    void xeRefresh (int k)
    {
        xeSimple.at (k) = xeDelay.at (k) == 0.0f && xeHold.at (k) == 0.0f && xeAC.at (k) == 0.0f && xeDC.at (k) == 0.0f && xeRC.at (k) == 0.0f
                          && xeVel.at (k) == 0.0f && xeKey.at (k) == 0.0f && xeLvl.at (k) == 1.0f && xeLoop.at (k) < 0.5f;
    }

    // One sample of envelope k of voice vi. st: 0 idle, 1 attack (delay, rise, hold), 2 decay / sustain, 3 release
    EnvR envX (int vi, int k, int st, float lv, float dt, float a, float d, float sus, float r)
    {
        EnvR o;
        o.st = st;
        o.lv = lv;

        if (st == 0)
            return o;

        // all extras at their defaults: exactly the old envelope (cheap path)
        if (xeSimple.at (k))
        {
            voices.at (vi).exPrev.at (k) = 0;

            if (st == 1)
            {
                o.lv = lv + dt / max (a * 0.001f, 0.0005f);
                if (o.lv >= 1.0f) { o.lv = 1.0f; o.st = 2; }
            }
            else if (st == 2)
                o.lv = lv + (sus - lv) * clamp (dt * 5.0f / (max (d, 1.0f) * 0.001f), 0.0f, 0.99f);
            else
                o.lv = lv - lv * clamp (dt * 5.0f / (max (r, 1.0f) * 0.001f), 0.0f, 0.99f);

            return o;
        }

        float kt   = xeKey.at (k);
        float ts   = 1.0f;
        if (kt != 0.0f)
            ts = float (pow (2.0f, -kt * (float (voices.at (vi).noteNumber) - 60.0f) / 12.0f));

        float va   = 0.0f;
        if (k != 10)
            va = xeVel.at (k);
        float peak = xeLvl.at (k) * (1.0f - va + va * voices.at (vi).velRaw);
        float susE = sus * peak;
        float ac   = xeAC.at (k);
        float dc   = xeDC.at (k);
        float rc   = xeRC.at (k);
        bool  isLoop = k != 10 && xeLoop.at (k) > 0.5f;

        // entering a stage: timers reset, progress of the attack continues from the current level
        if (st != voices.at (vi).exPrev.at (k))
        {
            voices.at (vi).exPrev.at (k) = st;
            voices.at (vi).exT.at (k)    = 0.0f;
            voices.at (vi).exSub.at (k)  = 0;
            voices.at (vi).exL.at (k)    = lv;
            voices.at (vi).exQ.at (k)    = 0.0f;

            if (st == 1)
            {
                float x = 1.0f;
                if (peak > 0.0001f)
                    x = clamp (lv / peak, 0.0f, 1.0f);
                if (ac != 0.0f)
                    x = float (pow (x, float (pow (4.0f, ac))));
                voices.at (vi).exQ.at (k) = x;
            }
        }

        if (st == 1)
        {
            if (voices.at (vi).exSub.at (k) == 0)
            {
                float t = voices.at (vi).exT.at (k);

                if (t < xeDelay.at (k) * 0.001f)
                    voices.at (vi).exT.at (k) = t + dt;
                else
                {
                    float q = voices.at (vi).exQ.at (k) + dt / max (a * ts * 0.001f, 0.0005f);

                    if (q >= 1.0f)
                    {
                        q    = 1.0f;
                        o.lv = peak;

                        if (xeHold.at (k) > 0.0f)
                        {
                            voices.at (vi).exSub.at (k) = 1;
                            voices.at (vi).exT.at (k)   = 0.0f;
                        }
                        else
                        {
                            o.st = 2;
                            voices.at (vi).exPrev.at (k) = 2;
                            voices.at (vi).exL.at (k)    = peak;
                            voices.at (vi).exQ.at (k)    = 0.0f;
                            voices.at (vi).exT.at (k)    = 0.0f;
                            voices.at (vi).exSub.at (k)  = 0;
                            return o;
                        }
                    }
                    else if (ac != 0.0f)
                        o.lv = peak * float (pow (q, float (pow (4.0f, -ac))));
                    else
                        o.lv = peak * q;

                    voices.at (vi).exQ.at (k) = q;
                }
            }
            else
            {
                float t = voices.at (vi).exT.at (k) + dt;
                o.lv = peak;
                voices.at (vi).exT.at (k) = t;

                if (t >= xeHold.at (k) * 0.001f)
                {
                    o.st = 2;
                    voices.at (vi).exPrev.at (k) = 2;
                    voices.at (vi).exL.at (k)    = peak;
                    voices.at (vi).exQ.at (k)    = 0.0f;
                    voices.at (vi).exT.at (k)    = 0.0f;
                    voices.at (vi).exSub.at (k)  = 0;
                }
            }
        }
        else if (st == 2)
        {
            if (dc == 0.0f && ! isLoop)
                o.lv = lv + (susE - lv) * clamp (dt * 5.0f / (max (d * ts, 1.0f) * 0.001f), 0.0f, 0.99f);
            else
            {
                float q = voices.at (vi).exQ.at (k) + dt / max (d * ts * 0.001f, 0.0005f);
                voices.at (vi).exQ.at (k) = min (q, 1.0f);
                o.lv = susE + (voices.at (vi).exL.at (k) - susE) * envFall (q, dc);

                if (q >= 1.0f && isLoop)
                {
                    o.st = 1;
                    voices.at (vi).exPrev.at (k) = 1;
                    voices.at (vi).exSub.at (k)  = 0;
                    voices.at (vi).exT.at (k)    = xeDelay.at (k) * 0.001f;
                    voices.at (vi).exL.at (k)    = o.lv;
                    float x = 1.0f;
                    if (peak > 0.0001f)
                        x = clamp (o.lv / peak, 0.0f, 1.0f);
                    if (ac != 0.0f)
                        x = float (pow (x, float (pow (4.0f, ac))));
                    voices.at (vi).exQ.at (k) = x;
                }
            }
        }
        else
        {
            if (rc == 0.0f)
                o.lv = lv - lv * clamp (dt * 5.0f / (max (r * ts, 1.0f) * 0.001f), 0.0f, 0.99f);
            else
            {
                float q = voices.at (vi).exQ.at (k) + dt / max (r * ts * 0.001f, 0.0005f);
                voices.at (vi).exQ.at (k) = min (q, 1.0f);
                o.lv = voices.at (vi).exL.at (k) * envFall (q, rc);
            }
        }

        return o;
    }
    // ENV2-END

'''

s = open(PATCH).read()
def rep(old, new, cnt=1):
    global s
    if new in s: return
    assert s.count(old) == cnt, (old[:80], s.count(old))
    s = s.replace(old, new)
def block(t, body, anchor_re, indent="    "):
    global s
    a, z = "%s// ENV2-%s-BEGIN\n" % (indent, t), "%s// ENV2-%s-END\n" % (indent, t)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + t)
    s = s[:m.start()] + a + body + z + s[m.start():]
if "    // ENV2-BEGIN" in s:
    s = re.sub(r"    // ENV2-BEGIN\n.*?    // ENV2-END\n\n", lambda m: CODE, s, flags=re.S)
else:
    a = s.index("    // Advances the 10 mod envelopes of one voice by one sample")
    s = s[:a] + CODE + s[a:]
# state
rep("    float[16]   mLfoSm;       // smoothing state of the free-running (global) LFOs\n", "    float[16]   mLfoSm;       // smoothing state of the free-running (global) LFOs\n" + "".join("    float[32]   %s;       // ENV2\n" % q[2] for q in E2), 1) if False else None
if "float[32]   xeDelay;" not in s:
    rep("    float[16]   mEnvA;  // padded to a power of two (cheap index wrap)\n", "".join("    float[32]   %s;       // ENV2: extra envelope parameter, index = envelope (0..9 mod, 10 amp, 11..16 filter)\n" % q[2] for q in E2) + "    float[16]   mEnvA;  // padded to a power of two (cheap index wrap)\n")
if "bool[32]    xeSimple;" not in s:
    rep("    float[16]   mEnvA;  // padded to a power of two (cheap index wrap)\n", "    bool[32]    xeSimple;       // ENV2: every extra of the envelope is at its default\n    float[16]   mEnvA;  // padded to a power of two (cheap index wrap)\n")
rep("        int[16]   mstage;     // mod envelope stages (0 off, 1 attack, 2 decay/sustain, 3 release)\n",
    "        int[16]   mstage;     // mod envelope stages (0 off, 1 attack, 2 decay/sustain, 3 release)\n        float[32] exT;        // ENV2: stage timer\n        float[32] exQ;        // ENV2: progress of the stage (0..1)\n        float[32] exL;        // ENV2: level at the start of the stage\n        int[32]   exSub;      // ENV2: sub stage (attack: 0 delay / rise, 1 hold)\n        int[32]   exPrev;     // ENV2: stage seen on the previous sample (0 = restart)\n")
rep("            voices.at (v).mstage.at (ms) = 1;\n", "            voices.at (v).mstage.at (ms) = 1;\n            voices.at (v).exPrev.at (ms) = 0;\n")
rep("        voices.at (v).stage = 1;\n\n        for (int o = 0; o < 6; ++o)\n        {\n            voices.at (v).fstage.at (o) = 1;\n",
    "        voices.at (v).stage = 1;\n        voices.at (v).exPrev.at (10) = 0;\n\n        for (int o = 0; o < 6; ++o)\n        {\n            voices.at (v).fstage.at (o) = 1;\n            voices.at (v).exPrev.at (11 + o) = 0;\n")
# amp envelope
rep("""                if (st == 1)
                {
                    e += dt / max (ampAttack * 0.001f, 0.0005f);
                    if (e >= 1.0f) { e = 1.0f; st = 2; }
                }
                else if (st == 2)
                {
                    e += (ampSustain - e) * clamp (dt * 5.0f / (max (ampDecay, 1.0f) * 0.001f), 0.0f, 0.99f);
                }
                else
                {
                    e -= e * clamp (dt * 5.0f / (max (ampRelease, 1.0f) * 0.001f), 0.0f, 0.99f);
                    if (e < 0.0003f)
                    {
                        e = 0.0f;
                        voices.at (i).active = false;
                    }
                }
""", """                EnvR ae = envX (i, 10, st, e, dt, ampAttack, ampDecay, ampSustain, ampRelease);   // ENV2
                st = ae.st;
                e  = ae.lv;

                if (st == 3 && e < 0.0003f)
                {
                    e = 0.0f;
                    voices.at (i).active = false;
                }
""")
# filter envelope
rep("""                    if (fst == 1)
                    {
                        fe += dt / max (op.at (ob + 38) * 0.001f, 0.0005f);
                        if (fe >= 1.0f) { fe = 1.0f; fst = 2; }
                    }
                    else if (fst == 2)
                    {
                        fe += (op.at (ob + 40) - fe) * clamp (dt * 5.0f / (max (op.at (ob + 39), 1.0f) * 0.001f), 0.0f, 0.99f);
                    }
                    else
                    {
                        fe -= fe * clamp (dt * 5.0f / (max (op.at (ob + 41), 1.0f) * 0.001f), 0.0f, 0.99f);
                    }
""", """                    EnvR fr = envX (i, 11 + o, fst, fe, dt, op.at (ob + 38), op.at (ob + 39), op.at (ob + 40), op.at (ob + 41));   // ENV2
                    fst = fr.st;
                    fe  = fr.lv;
""")
# mod envelopes
if "EnvR me2 = envX" not in s:
    a = s.index("            int   ms = voices.at (vi).mstage.at (m);\n            float me = voices.at (vi).menv.at (m);\n\n            if (ms == 1)")
    b = s.index("            voices.at (vi).menv.at (m)   = me;\n            voices.at (vi).mstage.at (m) = ms;\n", a)
    s = s[:a] + "            int   ms = voices.at (vi).mstage.at (m);\n            float me = voices.at (vi).menv.at (m);\n\n            EnvR me2 = envX (vi, m, ms, me, dtv, mEnvA.at (m), mEnvD.at (m), mEnvS.at (m), mEnvR.at (m));   // ENV2\n            ms = me2.st;\n            me = me2.lv;\n\n" + s[b:]
# mod envelopes that no matrix slot uses are not advanced (CPU)
rep("    int         frqMask = 0;  // bit m: Freq modulator m is used by the matrix\n", "    int         frqMask = 0;  // bit m: Freq modulator m is used by the matrix\n    int         envMask = 0;  // ENV2: bit m: mod envelope m is a source of a matrix slot\n")
if "envMask = 0;   // ENV2" not in s: rep("            frqMask = 0;\n", "            envMask = 0;   // ENV2\n            for (int es = 0; es < mmTop; ++es)\n                if (mmSrcI.at (es) >= 11 && mmSrcI.at (es) <= 20 && mmDstI.at (es) > 0)\n                    envMask |= 1 << (mmSrcI.at (es) - 11);\n            frqMask = 0;\n")
rep("            int   ms = voices.at (vi).mstage.at (m);\n            float me = voices.at (vi).menv.at (m);\n\n            EnvR me2", "            if ((envMask & (1 << m)) == 0)\n                continue;\n\n            int   ms = voices.at (vi).mstage.at (m);\n            float me = voices.at (vi).menv.at (m);\n\n            EnvR me2")
# parameters
decl = "".join('    input event float param%d [[ name: "%s %s", min: %s, max: %s, init: %s%s ]];\n' % (eid(k, q[0]), ename(k), q[3], repr(float(q[5])), repr(float(q[6])), repr(float(q[7])), ", step: 1.0" if q[9] == "btn" else "") for k in range(NK) for q in E2)
hand = "".join("    event param%d (float v) { %s.at (%d) = v; xeRefresh (%d); }\n" % (eid(k, q[0]), q[2], k, k) for k in range(NK) for q in E2)
init = "".join("            %s.at (ie) = %sf;\n" % (a, repr(float(v))) for a, v in sorted({(q[2], q[7]) for q in E2})) + "            xeSimple.at (ie) = true;\n"
block("DECL", decl, r"^    input event float param1600 ")
block("HAND", hand, r"^    event param1600 ")
block("INIT", "        for (int ie = 0; ie < 32; ++ie)\n        {\n" + init + "        }\n", r"^        fxGateInit\(\);\n", "        ")
open(PATCH, "w").write(s)
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoEnv2.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/env/build_env2.py: parameter ids of the envelope extras (k: 0..9 mod, 10 amp, 11..16 filter of OSC 1..6)\n#pragma once\n#include <string_view>\nnamespace njo::env2\n{\n")
    f.write("    constexpr int BASE = %d, STRIDE = %d;\n    inline int envId (int k, int j) { return BASE + STRIDE * k + j; }\n" % (BASE, STRIDE))
    f.write("    inline int key (const char* name)\n    {\n")
    for q in E2: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n}\n")
print("ok")
