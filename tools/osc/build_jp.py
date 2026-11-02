#!/usr/bin/env python3
"""Adds the JP-8080 source (Source type 7) to patch/Eisenpuls_Synth.cmajor.  Waveforms of the Roland JP-8000 / JP-8080 oscillator: Saw, Square (PWM), Triangle,
Sine, Noise, Spectrum (additive, 32 harmonics with tilt and a formant peak), Super Saw (7 detuned saws with the detune and mix curves of the analysed JP-8000,
stereo, pitch following high-pass), Feedback Osc (sine whose phase is modulated by its own output) and Tri Mod (triangle with phase modulation by a harmonic
of itself).  Common: noise, sub oscillator (-1 oct square) and drive.  Parameters: ids JP_BASE + 16 * slot + j (layout.py JP), mod destinations 732 + 16 * slot + j.
State per voice and slot: Voice.jps (slot * 64): 0..6 saw phases, 7 phase, 8 PWM LFO phase, 9 / 10 feedback memory, 11 / 12 high-pass memory L / R, 13 sub phase,
14 noise memory, 16 counter, 32..63 spectrum weights.  Run after build_wg.py.  Idempotent.  Usage: build_jp.py [patch.cmajor]"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
K = L.JP
def tab(f): return ", ".join("%sf" % repr(float(f(p))) for p in K)
LO, HI = tab(lambda p: p[4]), tab(lambda p: p[5])
DSP = r'''    // ---------------- JP-8080 source (tools/osc/build_jp.py) ----------------
    float[96] jpP;        // slot * 16 + parameter
    const float[16] jpLo = (@LO@);
    const float[16] jpHi = (@HI@);
    const float[7] jpOff = (-0.11002313f, -0.06288439f, -0.01952356f, 0.0f, 0.01991221f, 0.06216538f, 0.10745242f);   // Super Saw detune of the 7 saws

    void jpSet (int o, int j, float v)
    {
        jpP.at (o * 16 + j) = v;
    }

    float jpq (int o, int j)
    {
        float v = jpP.at (o * 16 + j);
        float m = vmod.at (732 + 16 * o + j);

        if (m != 0.0f)
        {
            v += m * 0.5f * (jpHi.at (j) - jpLo.at (j));
            v = clamp (v, jpLo.at (j), jpHi.at (j));
        }

        return v;
    }

    float jpGet (int vi, int i)
    {
        return voices.at (vi).jps.at (i);
    }

    void jpPut (int vi, int i, float v)
    {
        voices.at (vi).jps.at (i) = v;
    }

    // the analysed detune curve of the JP-8000 Super Saw (Szabo), 0..1 -> 0..1
    float jpDetCurve (float xf)
    {
        float64 x = float64 (clamp (xf, 0.0f, 1.0f));
        float64 y = 10028.7312891634;
        y = y * x - 50818.8652045924;
        y = y * x + 111363.4808729368;
        y = y * x - 138150.6761080548;
        y = y * x + 106649.6679158292;
        y = y * x - 53046.9642751875;
        y = y * x + 17019.9518580080;
        y = y * x - 3425.0836591318;
        y = y * x + 404.2703938388;
        y = y * x - 24.1878824391;
        y = y * x + 0.6717417634;
        y = y * x + 0.0030115596;
        return clamp (float (y), 0.0f, 1.0f);
    }

    void jpNoteOn (int vi, int o)
    {
        if (int (op.at (o * 64) + 0.5f) != 7)
            return;

        for (int i = 0; i < 64; ++i)
            voices.at (vi).jps.at (o * 64 + i) = 0.0f;

        for (int k = 0; k < 7; ++k)
            voices.at (vi).jps.at (o * 64 + k) = nextNoise() * 0.5f + 0.5f;
    }

    // spectrum weights: n ^ -(0.3 + 2.2 * tilt) with a formant peak, normalised to a constant rms
    void jpWeights (int vi, int o)
    {
        int   sb = o * 64;
        float ex = 0.3f + 2.2f * jpq (o, 11);
        float pk = 2.0f + 20.0f * jpq (o, 12);
        float ss = 0.0f;

        for (int n = 1; n <= 32; ++n)
        {
            float d = (float (n) - pk) / (1.0f + 0.15f * pk);
            float a = float (pow (float (n), -ex)) * (1.0f + 3.0f * float (exp (-0.5f * d * d)));
            jpPut (vi, sb + 31 + n, a);
            ss += a * a;
        }

        float g = 0.5f / sqrt (ss * 0.5f + 0.000001f);

        for (int n = 1; n <= 32; ++n)
            jpPut (vi, sb + 31 + n, jpGet (vi, sb + 31 + n) * g);
    }

    float jpTri (float q)
    {
        return q < 0.5f ? 4.0f * q - 1.0f : 3.0f - 4.0f * q;
    }

    float<2> jpStep (int vi, int o, float freq, float pm)
    {
        float sr = float (processor.frequency);
        int   sb = o * 64;
        int   wv = clamp (int (jpq (o, 0) + 0.5f), 0, 8);
        float dt = freq / sr;
        float tp = 6.2831853f;

        // PWM low-frequency oscillator
        float lp = jpGet (vi, sb + 8) + jpq (o, 3) / sr;
        if (lp >= 1.0f) lp -= 1.0f;
        jpPut (vi, sb + 8, lp);
        float lfo = float (sin (tp * lp));

        float ph = jpGet (vi, sb + 7);
        float rp = ph + pm;
        rp = rp - float (floor (rp));

        float yL = 0.0f;
        float yR = 0.0f;

        if (wv == 0)
        {
            yL = 0.9f * junoRamp (rp, dt);
            yR = yL;
        }
        else if (wv == 1)
        {
            float w = clamp (jpq (o, 1) + jpq (o, 2) * 0.45f * lfo, 0.05f, 0.95f);
            yL = 0.8f * junoPulse (rp, w, dt);
            yR = yL;
        }
        else if (wv == 2)
        {
            yL = 0.9f * jpTri (rp);
            yR = yL;
        }
        else if (wv == 3)
        {
            yL = 0.9f * float (sin (tp * rp));
            yR = yL;
        }
        else if (wv == 4)
        {
            yL = 0.7f * nextNoise();
            yR = yL;
        }
        else if (wv == 5)
        {
            int cnt = int (jpGet (vi, sb + 16));

            if (cnt <= 0)
            {
                jpWeights (vi, o);
                cnt = 32;
            }

            jpPut (vi, sb + 16, float (cnt - 1));

            int   nh   = clamp (int (0.45f * sr / freq), 1, 32);
            float th   = tp * rp;
            float c2   = 2.0f * float (cos (th));
            float s1   = float (sin (th));
            float s0   = 0.0f;
            float sum  = 0.0f;

            for (int n = 1; n <= nh; ++n)
            {
                sum += jpGet (vi, sb + 31 + n) * s1;
                float sn = c2 * s1 - s0;
                s0 = s1;
                s1 = sn;
            }

            yL = sum;
            yR = yL;
        }
        else if (wv == 6)
        {
            float dtn = jpDetCurve (jpq (o, 4));
            float mx  = jpq (o, 5);
            float cG  = -0.55366f * mx + 0.99785f;
            float sG  = -0.73764f * mx * mx + 1.2841f * mx + 0.044372f;
            float c   = 0.0f;
            float sl  = 0.0f;
            float sr2 = 0.0f;

            for (int k = 0; k < 7; ++k)
            {
                float f  = freq * (1.0f + jpOff.at (k) * dtn);
                float dk = f / sr;
                float p  = jpGet (vi, sb + k) + dk;
                if (p >= 1.0f) p -= 1.0f;
                jpPut (vi, sb + k, p);
                float q = p + pm;
                q = q - float (floor (q));
                float s = junoRamp (q, dk);

                if (k < 3)       sl += s;
                else if (k == 3) c = s;
                else             sr2 += s;
            }

            float wd  = jpq (o, 6);
            float mid = 0.5f * (sl + sr2);
            float xl  = 0.3f * (cG * c + sG * (mid + wd * (sl - mid)));
            float xr  = 0.3f * (cG * c + sG * (mid + wd * (sr2 - mid)));

            // high-pass that follows the pitch (as in the JP-8000)
            float a  = 1.0f - float (exp (-tp * freq * 0.5f / sr));
            float lL = jpGet (vi, sb + 11);
            float lR = jpGet (vi, sb + 12);
            lL += a * (xl - lL);
            lR += a * (xr - lR);
            jpPut (vi, sb + 11, lL);
            jpPut (vi, sb + 12, lR);
            yL = xl - lL;
            yR = xr - lR;
        }
        else if (wv == 7)
        {
            float k  = jpq (o, 7) * 4.5f;
            float y1 = jpGet (vi, sb + 9);
            float y2 = jpGet (vi, sb + 10);
            float x  = tp * rp + k * 0.5f * (y1 + y2) + jpq (o, 8) * 1.5f * float (sin (2.0f * tp * rp));
            float y  = float (sin (x));
            jpPut (vi, sb + 10, y1);
            jpPut (vi, sb + 9, y);
            yL = 0.9f * y;
            yR = yL;
        }
        else
        {
            float r  = 1.0f + float (floor (jpq (o, 10) * 7.0f + 0.5f));
            float q  = rp + jpq (o, 9) * 0.35f * float (sin (tp * r * rp));
            q = q - float (floor (q));
            yL = 0.9f * jpTri (q);
            yR = yL;
        }

        // common: noise, sub oscillator (-1 octave square), drive
        float nzm = jpq (o, 13);
        float sbm = jpq (o, 15);

        if (wv != 4 && nzm > 0.0005f)
        {
            float ln = jpGet (vi, sb + 14);
            ln += 0.6f * (nextNoise() - ln);
            jpPut (vi, sb + 14, ln);
            yL += nzm * 0.7f * ln;
            yR += nzm * 0.7f * ln;
        }

        float sp = jpGet (vi, sb + 13) + 0.5f * dt;
        if (sp >= 1.0f) sp -= 1.0f;
        jpPut (vi, sb + 13, sp);

        if (sbm > 0.0005f)
        {
            float sub = 0.6f * sbm * junoPulse (sp, 0.5f, 0.5f * dt);
            yL += sub;
            yR += sub;
        }

        float dr = jpq (o, 14);

        if (dr > 0.001f)
        {
            float gd = 1.0f + dr * 6.0f;
            float nrm = 1.0f / float (tanh (gd));
            yL = float (tanh (yL * gd)) * nrm;
            yR = float (tanh (yR * gd)) * nrm;
        }

        ph += dt;
        if (ph >= 1.0f) ph -= 1.0f;
        jpPut (vi, sb + 7, ph);

        return float<2> (clamp (yL, -2.0f, 2.0f), clamp (yR, -2.0f, 2.0f));
    }

'''.replace("@LO@", LO).replace("@HI@", HI)
VOICE = "        float[512]    jps;    // JP-8080 source: state, slot * 64\n"
DECL = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];\n' % (
    L.jp_id(o, p[0]), o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6])), ", step: 1.0" if p[8] == "sel" else "")
    for o in range(L.OSC_COUNT) for p in K)
HAND = "".join("    event param%d (float v) { jpSet (%d, %d, v); }\n" % (L.jp_id(o, p[0]), o, p[0]) for o in range(L.OSC_COUNT) for p in K)
INIT = "".join("            jpP.at (io * 16 + %d) = %sf;\n" % (p[0], repr(float(p[6]))) for p in K)
s = open(PATCH).read()
def block(tag, body, anchor_re, indent="    "):
    global s
    a, z = "%s// JP-%s-BEGIN\n" % (indent, tag), "%s// JP-%s-END\n" % (indent, tag)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", DSP, r"^    // PHYS-DSP-BEGIN")
block("DECL", DECL, r"^    input event float param1600 ")
block("HAND", HAND, r"^    event param1600 ")
block("INIT", INIT, r"^            op\.at \(io \* 64 \+ 11\) = 3\.0f;\n", "            ")
block("VOICE", VOICE, r"^        int     fdlW; ", "        ")
s = re.sub(r'(name: "OSC \d Source", min: 0.0, max: )\d+\.0', r'\g<1>7.0', s)
def rep(old, new):
    global s
    if new in s: return
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("                    wgNoteOn (v, o);\n", "                    wgNoteOn (v, o);\n                    jpNoteOn (v, o);\n")
rep("\n                    // ----- filter envelope of the slot -----\n",
    "                    else if (ty == 7)\n                    {\n                        float<2> jw = jpStep (i, o, freq, pm);\n                        sL = jw[0];\n                        sR = jw[1];\n                        stereo = true;\n                    }\n\n                    // ----- filter envelope of the slot -----\n")
DMAX = L.N_DST_TOTAL - 1
s = re.sub(r"(mmDstI\.at \(\d+\) = clamp \(int \(v \+ 0\.5f\), 0, )\d+\)", lambda m: m.group(1) + "%d)" % DMAX, s)
s = re.sub(r'(Mod Slot \d+ Dest \(0-)\d+(, see Dest list\)", min: 0\.0, max: )\d+(\.0)', lambda m: m.group(1) + "%d" % DMAX + m.group(2) + "%d" % DMAX + m.group(3), s)
open(PATCH, "w").write(s)
print("ok")
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoJp.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/osc/build_jp.py: parameter ids and labels of the JP-8080 source\n#pragma once\n#include <string_view>\nnamespace njo::jp\n{\n")
    f.write("    constexpr int JP_BASE = %d, JP_STRIDE = %d;\n" % (L.JP_BASE, L.JP_STRIDE))
    f.write("    inline int jpId (int o, int j) { return JP_BASE + JP_STRIDE * o + j; }\n")
    f.write("    inline int key (const char* name)   // parameter index j of a key such as \"jdet\"\n    {\n")
    for q in K: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n")
    f.write("    // labels of the parameters 1..15 for every waveform (\"\" = the waveform does not use the parameter)\n    inline const char* label (int wave, int j)\n    {\n        static const char* const t[%d][15] = {\n" % len(L.JP_LABELS))
    for row in L.JP_LABELS:
        assert len(row) == 15
        f.write("            { " + ", ".join('"%s"' % x for x in row) + " },\n")
    f.write("        };\n        return j < 1 || j > 15 || wave < 0 || wave > %d ? \"\" : t[wave][j - 1];\n    }\n}\n" % (len(L.JP_LABELS) - 1))
