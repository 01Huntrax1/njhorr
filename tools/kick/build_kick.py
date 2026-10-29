#!/usr/bin/env python3
"""Adds the Kick source (Source type 5) to patch/Eisenpuls_Synth.cmajor.  A kick drum synth voice in the spirit of the open-source kick synths Geonkick (GPL-3),
Kickmess / LMMS Kicker (sine body with an exponential pitch sweep, click, noise, drive curves) and ChowKick (a resonant body excited by a pulse, drum machine
style): the algorithms are written from scratch, no code was copied.  Parameters: ids KICK_BASE + 16 * slot + j (layout.py KICK), mod destinations 444 + 16 * slot + j.
Run after build_mod.py and build_juno.py.  Idempotent.  Usage: build_kick.py [patch.cmajor]"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "osc"))
import layout as L
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
K = L.KICK
def tab(f): return ", ".join("%sf" % repr(float(f(p))) for p in K)
LO, HI = tab(lambda p: p[4]), tab(lambda p: p[5])
LOGF = tab(lambda p: 1 if p[1] in ("kstime", "kdec", "kcldec") else 0)

DSP = r'''    // ---------------- Kick source (tools/kick/build_kick.py) ----------------
    // One kick per note: a body oscillator whose pitch falls from f * 2^Sweep to the played note, an amplitude envelope, a short noise click, a noise tail,
    // an optional sub oscillator and a drive stage with 6 curves.  Modes: 0 Classic (sine with feedback tone), 1 808 (the pitch follows the decaying body like a
    // resonant circuit, saturated, pulse excited), 2 Punch (two stage pitch fall, second harmonic), 3 Hardstyle (long fall, hard clipped).
    // state per voice and slot in Voice.phs 1900 + 8 * slot: 0 time (s), 1 body phase, 2 sub phase, 3 feedback, 4 click high-pass memory, 5 click low-pass,
    // 6 noise low-pass, 7 unused
    float[96] kickP;      // slot * 16 + parameter
    const float[16] kqLo  = (@LO@);
    const float[16] kqHi  = (@HI@);
    const float[16] kqLog = (@LOG@);

    void kickSet (int o, int j, float v)
    {
        kickP.at (o * 16 + j) = v;
    }

    float kq (int o, int j)
    {
        float v = kickP.at (o * 16 + j);
        float m = vmod.at (444 + 16 * o + j);

        if (m != 0.0f)
        {
            if (kqLog.at (j) > 0.5f)
                v *= float (pow (2.0f, m * 4.0f));
            else
                v += m * 0.5f * (kqHi.at (j) - kqLo.at (j));

            v = clamp (v, kqLo.at (j), kqHi.at (j));
        }

        return v;
    }

    void kickNoteOn (int vi, int o)
    {
        for (int i = 0; i < 8; ++i)
            voices.at (vi).phs.at (1900 + 8 * o + i) = 0.0f;
    }

    // drive curves, normalised so that an input of 1 stays below 1 at any gain: 0 hard clip, 1 tanh, 2 atan, 3 log, 4 exp, 5 cubic
    float kickShape (int c, float x)
    {
        float a = abs (x);
        float s = 1.0f;

        if (c == 0)      s = min (a, 1.0f);
        else if (c == 1) s = float (tanh (a));
        else if (c == 2) s = float (atan (a)) * 0.63662f;
        else if (c == 3) s = float (log (1.0f + 4.0f * a)) * 0.62133f;
        else if (c == 4) s = 1.0f - float (exp (-2.0f * a));
        else
        {
            float u = min (a, 1.5f);
            s = u - 0.148148f * u * u * u;
        }

        return x < 0.0f ? -s : s;
    }

    // one sample of slot o on voice vi at the note frequency f0 (Hz), pm = phase modulation from the matrix
    float kickStep (int vi, int o, float f0, float pm)
    {
        float sr = float (processor.frequency);
        float dt = float (processor.period);
        int   kb = 1900 + 8 * o;
        float t  = voices.at (vi).phs.at (kb);

        int   mode  = clamp (int (kq (o, 0) + 0.5f), 0, 3);
        float sweep = kq (o, 1);
        float tp    = max (kq (o, 2) * 0.001f / (1.0f + 3.0f * kq (o, 3)), 0.0005f);
        float dec   = kq (o, 4) * 0.001f;
        float tone  = kq (o, 5);
        float chr   = kq (o, 15);
        float fend  = clamp (f0 * float (pow (2.0f, kq (o, 13) / 12.0f)), 1.0f, sr * 0.4f);

        // amplitude and pitch envelopes
        float env = float (exp (-t * 4.6f / dec));
        float oct = sweep * float (exp (-t / tp));

        if (mode == 1)      oct = sweep * (0.6f * float (exp (-t / tp)) + 0.4f * env * env);
        else if (mode == 2) oct = sweep * (0.7f * float (exp (-t / tp)) + 0.3f * float (exp (-t / (tp * 6.0f))));
        else if (mode == 3) oct = sweep * float (exp (-t / (tp * 3.0f)));

        float f  = min (fend * float (exp (oct * 0.693147f)), sr * 0.45f);
        float ph = voices.at (vi).phs.at (kb + 1) + f * dt;
        ph = ph - float (floor (ph));
        voices.at (vi).phs.at (kb + 1) = ph;
        float rp = ph + pm;
        rp = rp - float (floor (rp));
        float a2p = 6.2831853f * rp;

        // body
        float fb   = voices.at (vi).phs.at (kb + 3);
        float body = 0.0f;

        if (mode == 0)
        {
            body = float (sin (a2p + tone * 1.6f * fb));
            fb   = body;
        }
        else if (mode == 1)
        {
            float pw    = 0.0003f + 0.002f * chr;
            float pulse = t < pw ? 1.0f - t / pw : 0.0f;
            float gsat  = 1.0f + tone * 3.0f;
            body = float (tanh (float (sin (a2p)) * gsat)) / float (tanh (gsat)) + chr * 0.5f * pulse;
        }
        else if (mode == 2)
        {
            body = float (sin (a2p + tone * 1.0f * fb)) + chr * 0.3f * float (sin (2.0f * a2p)) * env;
            fb   = body;
            body *= 0.8f;
        }
        else
        {
            body = float (sin (a2p + tone * 2.0f * fb));
            fb   = body;
            body = clamp (body * (3.0f + 12.0f * chr), -1.0f, 1.0f);
        }

        voices.at (vi).phs.at (kb + 3) = fb;

        float amp  = env * (1.0f + kq (o, 12) * 3.0f * float (exp (-t / 0.006f)));
        float tail = clamp ((dec * 2.4f - t) / (dec * 0.4f), 0.0f, 1.0f);
        float y    = body * amp * tail * min (1.0f, t / 0.0005f);

        // sub oscillator one octave below the note
        float sub = kq (o, 11);

        if (sub > 0.0f)
        {
            float sp = voices.at (vi).phs.at (kb + 2) + fend * 0.5f * dt;
            sp = sp - float (floor (sp));
            voices.at (vi).phs.at (kb + 2) = sp;
            y += float (sin (6.2831853f * sp)) * sub * float (pow (env, 0.7f)) * tail * min (1.0f, t / 0.0008f);
        }

        // click: high-passed noise burst, low-passed by the click tone
        float nz = nextNoise();
        float cl = kq (o, 6);

        if (cl > 0.0f)
        {
            float hpS = voices.at (vi).phs.at (kb + 4);
            hpS += 0.08f * (nz - hpS);
            voices.at (vi).phs.at (kb + 4) = hpS;
            float ct  = kq (o, 7);
            float lg  = clamp (float (twoPi) * (800.0f + 15000.0f * ct * ct) * dt, 0.001f, 0.95f);
            float lpS = voices.at (vi).phs.at (kb + 5);
            lpS += lg * ((nz - hpS) - lpS);
            voices.at (vi).phs.at (kb + 5) = lpS;
            y += lpS * cl * 1.4f * float (exp (-t / (kq (o, 14) * 0.001f)));
        }

        // noise tail
        float nl = kq (o, 8);

        if (nl > 0.0f)
        {
            float nS = voices.at (vi).phs.at (kb + 6);
            nS += 0.35f * (nz - nS);
            voices.at (vi).phs.at (kb + 6) = nS;
            y += (nz - nS) * nl * 0.5f * float (pow (env, 1.2f)) * tail;
        }

        // drive
        float drv = kq (o, 9);

        if (drv > 0.001f)
        {
            int   dc = clamp (int (kq (o, 10) + 0.5f), 0, 5);
            float g  = 1.0f + drv * (mode == 3 ? 14.0f : 8.0f);
            float sh = kickShape (dc, y * g) / kickShape (dc, g);
            y = y + (sh - y) * clamp (drv * 3.0f, 0.0f, 1.0f);
        }

        voices.at (vi).phs.at (kb) = t + dt;

        return y * 0.7f;
    }

'''.replace("@LO@", LO).replace("@HI@", HI).replace("@LOG@", LOGF)

DECL = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];\n' % (
    L.kick_id(o, p[0]), o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6])), ", step: 1.0" if p[8] in ("sel", "btn") else "")
    for o in range(L.OSC_COUNT) for p in K)
HAND = "".join("    event param%d (float v) { kickSet (%d, %d, v); }\n" % (L.kick_id(o, p[0]), o, p[0]) for o in range(L.OSC_COUNT) for p in K)
INIT = "".join("            kickP.at (io * 16 + %d) = %sf;\n" % (p[0], repr(float(p[6]))) for p in K)

s = open(PATCH).read()
def block(tag, body, anchor_re, indent="    "):
    global s
    a, z = "%s// KICK-%s-BEGIN\n" % (indent, tag), "%s// KICK-%s-END\n" % (indent, tag)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", DSP, r"^    // ---------------- MIDI ----------------")
block("DECL", DECL, r"^    input event float param1600 ")
block("HAND", HAND, r"^    event param1600 ")
block("INIT", INIT, r"^            op\.at \(io \* 64 \+ 11\) = 3\.0f;\n", "            ")
s = re.sub(r'(name: "OSC \d Source", min: 0.0, max: )[234]\.0', r'\g<1>5.0', s)
if "kickNoteOn (v, o);" not in s:
    assert "                    phyNoteOn (v, o);\n" in s
    s = s.replace("                    phyNoteOn (v, o);\n", "                    phyNoteOn (v, o);\n                    kickNoteOn (v, o);\n", 1)
if "kickStep (i, o, freq" not in s:
    old = "                    else if (ty == 4)\n                    {\n                        float<2> jw = junoStep (i, o, freq, pm);"
    assert old in s
    s = s.replace(old, "                    else if (ty == 5)\n                    {\n                        sL = kickStep (i, o, freq, pm);\n                        sR = sL;\n                    }\n" + old, 1)
# mod destinations 0..539
DMAX = L.N_DST_TOTAL - 1
s = s.replace("float[512]  vmod;", "float[1024] vmod;", 1)
s = s.replace("0, 443)", "0, %d)" % DMAX).replace("max: 443.0", "max: %d.0" % DMAX).replace("(0-443, see Dest list)", "(0-%d, see Dest list)" % DMAX)
open(PATCH, "w").write(s)
print("ok")
# ids and key names for the native editor
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoKick.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/kick/build_kick.py: parameter ids of the Kick source\n#pragma once\n#include <string_view>\nnamespace njo::kick\n{\n")
    f.write("    constexpr int KICK_BASE = %d, KICK_STRIDE = %d;\n" % (L.KICK_BASE, L.KICK_STRIDE))
    f.write("    inline int kickId (int o, int j) { return KICK_BASE + KICK_STRIDE * o + j; }\n")
    f.write("    inline int key (const char* name)   // parameter index j of a key such as \"kdec\"\n    {\n")
    for q in K: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n}\n")
