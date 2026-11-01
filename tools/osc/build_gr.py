#!/usr/bin/env python3
"""Adds the Granular source (Source type 8) to patch/Eisenpuls_Synth.cmajor.  It plays grains of the sample memory of its slot (load a sample like for the Sampler):
Position (+ Scan, Spray, Vel > Position), Size, Density, Timing Jitter, Pitch Spread, Pan Spread, Window, Reverse, Drive.  The grains are pitched by the key relative to the
Root note of the sample, 12 grains per voice at the same time.  Parameters: ids GR_BASE + 16 * slot + j (layout.py GR), mod destinations 828 + 16 * slot + j.
State per voice and slot: Voice.grs (slot * 96): grain g (0..11) at g * 6: length (0 = free), age, start position, rate, gain L, gain R; 72 timer, 73 scan position.
Run after build_jp.py.  Idempotent.  Usage: build_gr.py [patch.cmajor]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L, srcgen
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
LO, HI = srcgen.table(L.GR, 0)
DSP = r'''    // ---------------- Granular source (tools/osc/build_gr.py) ----------------
    float[96] grP;        // slot * 16 + parameter
    const float[16] grLo = (@LO@);
    const float[16] grHi = (@HI@);

    void grSet (int o, int j, float v)
    {
        grP.at (o * 16 + j) = v;
    }

    float grq (int o, int j)
    {
        float v = grP.at (o * 16 + j);
        float m = vmod.at (828 + 16 * o + j);

        if (m != 0.0f)
        {
            v += m * 0.5f * (grHi.at (j) - grLo.at (j));
            v = clamp (v, grLo.at (j), grHi.at (j));
        }

        return v;
    }

    void grNoteOn (int vi, int o)
    {
        if (int (op.at (o * 64) + 0.5f) != 8)
            return;

        for (int i = 0; i < 96; ++i)
            voices.at (vi).grs.at (o * 96 + i) = 0.0f;
    }

    // one sample of the granular slot o (st = octaves of pitch from tuning and modulation); returns the stereo sum of the grains
    float<2> grStep (int vi, int o, float cf, float st)
    {
        int   len = smpLen.at (o);

        if (! smpHas.at (o) || len < 2)
            return float<2> (0.0f, 0.0f);

        float sr = float (processor.frequency);
        int   sb = o * 96;
        float fl = float (len);

        // scan: at 1 the position moves through the sample in real time
        float scan = grq (o, 8);
        float acc  = voices.at (vi).grs.at (sb + 73);

        if (scan != 0.0f)
        {
            acc += scan / fl;
            acc = acc - float (floor (acc));
            voices.at (vi).grs.at (sb + 73) = acc;
        }

        float timer = voices.at (vi).grs.at (sb + 72) - 1.0f;

        if (timer <= 0.0f)
        {
            float dens  = float (pow (200.0f, grq (o, 2)));
            float glenF = max (5.0f * float (pow (100.0f, grq (o, 1))) * 0.001f * sr, 16.0f);
            int   g     = -1;

            for (int k = 0; k < 12; ++k)
            {
                if (voices.at (vi).grs.at (sb + k * 6) <= 0.0f)
                {
                    g = k;
                    break;
                }
            }

            if (g >= 0)
            {
                float vel   = clamp (voices.at (vi).velRaw, 0.0f, 1.0f);
                float pos   = grq (o, 0) + grq (o, 11) * vel + acc + grq (o, 3) * 0.5f * nextNoise();
                pos = pos - float (floor (pos));
                float semi  = grq (o, 4) * 12.0f * nextNoise();
                float rate  = clamp (cf / max (float (std::notes::noteToFrequency (int (opv (o, 12) + 0.5f))), 1.0f) * float (pow (2.0f, st + semi / 12.0f)), 0.02f, 16.0f);

                if (nextNoise() * 0.5f + 0.5f < grq (o, 7))
                    rate = -rate;

                float pn    = grq (o, 5) * nextNoise();
                float ang   = (pn + 1.0f) * 0.78539816f;
                float norm  = 1.0f / sqrt (max (1.0f, glenF / sr * dens));
                int   gb    = sb + g * 6;
                voices.at (vi).grs.at (gb)     = glenF;
                voices.at (vi).grs.at (gb + 1) = 0.0f;
                voices.at (vi).grs.at (gb + 2) = pos * fl;
                voices.at (vi).grs.at (gb + 3) = rate;
                voices.at (vi).grs.at (gb + 4) = float (cos (ang)) * norm;
                voices.at (vi).grs.at (gb + 5) = float (sin (ang)) * norm;
            }

            timer = max (sr / dens * (1.0f + grq (o, 9) * 0.9f * nextNoise()), 1.0f);
        }

        voices.at (vi).grs.at (sb + 72) = timer;

        float sh = grq (o, 6);
        float yL = 0.0f;
        float yR = 0.0f;

        for (int k = 0; k < 12; ++k)
        {
            int   gb = sb + k * 6;
            float gl = voices.at (vi).grs.at (gb);

            if (gl > 0.0f)
            {
                float age = voices.at (vi).grs.at (gb + 1);
                float u   = age / gl;
                float hn  = 0.5f - 0.5f * float (cos (6.2831853f * u));
                float tr  = clamp (8.0f * min (u, 1.0f - u), 0.0f, 1.0f);
                float w   = hn * (1.0f - sh) + tr * sh;
                float p   = voices.at (vi).grs.at (gb + 2) + voices.at (vi).grs.at (gb + 3) * age;
                p = p - fl * float (floor (p / fl));
                float s   = smpRead (o, float64 (p)) * w;
                yL += s * voices.at (vi).grs.at (gb + 4);
                yR += s * voices.at (vi).grs.at (gb + 5);
                age += 1.0f;
                voices.at (vi).grs.at (gb + 1) = age;

                if (age >= gl)
                    voices.at (vi).grs.at (gb) = 0.0f;
            }
        }

        float dr = grq (o, 10);

        if (dr > 0.001f)
        {
            float gd  = 1.0f + dr * 6.0f;
            float nrm = 1.0f / float (tanh (gd));
            yL = float (tanh (yL * gd)) * nrm;
            yR = float (tanh (yR * gd)) * nrm;
        }

        return float<2> (clamp (yL, -2.0f, 2.0f), clamp (yR, -2.0f, 2.0f));
    }

'''.replace("@LO@", LO).replace("@HI@", HI)
STEP = '''                    else if (ty == 8)
                    {
                        float<2> gw = grStep (i, o, cf, sExp);
                        sL = gw[0];
                        sR = gw[1];
                        stereo = true;
                    }
'''
srcgen.install(PATCH, "                    jpNoteOn (v, o);\n", "GR", L.GR, L.gr_id, L.GR_DST_BASE, DSP,
               "        float[1024]   grs;    // Granular source: grains, slot * 96\n", "                    grNoteOn (v, o);\n", STEP, "grSet", "grP",
               "tools/osc/build_gr.py", "NjoGr.h", "gr", L.GR_BASE, L.GR_STRIDE)
print("ok")
