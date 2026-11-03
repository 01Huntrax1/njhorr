#!/usr/bin/env python3
"""Adds the SoundFont source (Source type 12) to patch/Eisenpuls_Synth.cmajor: a multisample player for the zones of one SoundFont preset.
The preset is turned into a zone table + audio by the native editor (NjoSf2.cpp) and streamed into the bank of the slot (event sfBankLoad; layout in layout.py SF_*):
8 floats of preamble (0 = 12345 magic, 1 = zone count), SF_MAX_ZONES records of SF_ZF floats, then the audio (mono, each zone's own sample rate).
A note plays every zone whose key and velocity range contain it (up to 4 layers, e.g. the two halves of a stereo sample): pitch from the key, the zone's root key, tuning and
sample rate; loops (mode 1 loop, 3 loop until the key is released); volume envelope (attack, hold, decay, sustain, release) per zone; zone attenuation and pan.
Parameters: ids SF_BASE + 16 * slot + j (layout.py SF), mod destinations 1212 + 16 * slot + j.  State per voice and slot: Voice.sfl (slot * 96): layer l at l * 24.
Run after build_sp.py.  Idempotent.  Usage: build_sf.py [patch.cmajor]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L, srcgen
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
LO, HI = srcgen.table(L.SF, 0)
DSP = r'''    // ---------------- SoundFont source (tools/osc/build_sf.py) ----------------
    float[96]    sfP;        // slot * 16 + parameter
    const float[16] sfLo = (@LO@);
    const float[16] sfHi = (@HI@);
    float[@BANKTOTAL@] sfBuf;   // slot * @BANK@: preamble, zone records, audio
    bool[8]      sfHas;

    event sfBankLoad (BankChunk c)
    {
        int o = clamp (c.bank, 0, 5);

        if (c.total <= 0)
        {
            sfHas.at (o) = false;
            return;
        }

        if (c.offset == 0)
            sfHas.at (o) = false;

        int cnt  = clamp (c.count, 0, 256);
        int base = o * @BANK@;

        for (int i = 0; i < cnt; ++i)
        {
            int pos = c.offset + i;

            if (pos >= 0 && pos < @BANK@)
                sfBuf.at (base + pos) = c.data.at (i);
        }

        if (c.offset + cnt >= c.total)
            sfHas.at (o) = sfBuf.at (base) == 12345.0f && sfBuf.at (base + 1) > 0.5f;
    }

    void sfSet (int o, int j, float v)
    {
        sfP.at (o * 16 + j) = v;
    }

    float sfq (int o, int j)
    {
        float v = sfP.at (o * 16 + j);
        float m = vmod.at (1212 + 16 * o + j);

        if (m != 0.0f)
        {
            v += m * 0.5f * (sfHi.at (j) - sfLo.at (j));
            v = clamp (v, sfLo.at (j), sfHi.at (j));
        }

        return v;
    }

    // zone field f of zone z of slot o
    float sfZ (int o, int z, int f)
    {
        return sfBuf.at (o * @BANK@ + 8 + z * @ZF@ + f);
    }

    void sfNoteOn (int vi, int o, float vel)
    {
        for (int i = 0; i < 96; ++i)
            voices.at (vi).sfl.at (o * 96 + i) = 0.0f;

        if (int (op.at (o * 64) + 0.5f) != 12)
            return;

        for (int l = 0; l < 4; ++l)
            voices.at (vi).sfl.at (o * 96 + l * 24) = -1.0f;

        if (! sfHas.at (o))
            return;

        int   key   = voices.at (vi).noteNumber;
        int   vi127 = clamp (int (vel * 127.0f + 0.5f), 0, 127);
        int   nz    = clamp (int (sfBuf.at (o * @BANK@ + 1) + 0.5f), 0, @MAXZ@);
        int   nl    = 0;
        float sr    = float (processor.frequency);
        int   lmode = int (sfq (o, 6) + 0.5f);
        float aS    = float (pow (4.0f, sfq (o, 2)));
        float dS    = float (pow (4.0f, sfq (o, 3)));
        float rS    = float (pow (4.0f, sfq (o, 5)));
        float sOff  = sfq (o, 4) * 0.5f;
        float vs    = sfq (o, 1);
        float vg    = (1.0f - vs) + vs * vel * vel;
        float pw    = sfq (o, 7);

        for (int z = 0; z < nz && nl < 4; ++z)
        {
            if (key >= int (sfZ (o, z, 0) + 0.5f) && key <= int (sfZ (o, z, 1) + 0.5f) && vi127 >= int (sfZ (o, z, 2) + 0.5f) && vi127 <= int (sfZ (o, z, 3) + 0.5f))
            {
                int   b    = o * 96 + nl * 24;
                int   len  = int (sfZ (o, z, 5) + 0.5f);
                int   ls   = int (sfZ (o, z, 6) + 0.5f);
                int   le   = int (sfZ (o, z, 7) + 0.5f);
                int   lm   = int (sfZ (o, z, 8) + 0.5f);
                float root = float (std::notes::noteToFrequency (clamp (int (sfZ (o, z, 9) + 0.5f), 0, 127)));
                float tune = float (pow (2.0f, sfZ (o, z, 10) / 1200.0f));
                float srz  = sfZ (o, z, 11);
                float att  = float (pow (10.0f, -sfZ (o, z, 12) / 200.0f));
                float pan  = clamp (sfZ (o, z, 13) / 500.0f, -1.0f, 1.0f) * pw;
                float ang  = (pan + 1.0f) * 0.78539816f;
                float sus  = clamp (float (pow (10.0f, -sfZ (o, z, 17) / 200.0f)) + sOff, 0.0f, 1.0f);
                float aMs  = max (sfZ (o, z, 14) * aS, 0.5f);
                float hMs  = sfZ (o, z, 15);
                float dMs  = max (sfZ (o, z, 16) * dS, 1.0f);
                float rMs  = max (sfZ (o, z, 18) * rS, 1.0f);
                float ss   = clamp (sfq (o, 8), 0.0f, 1.0f);

                if (lmode == 1)
                    lm = 0;
                else if (lmode == 2 && lm == 0 && le > ls + 16)
                    lm = 1;

                if (len > 2 && srz > 100.0f)
                {
                    voices.at (vi).sfl.at (b)      = float (z);
                    voices.at (vi).sfl.at (b + 1)  = float (int (ss * float (len - 2)));
                    voices.at (vi).sfl.at (b + 2)  = 0.0f;
                    voices.at (vi).sfl.at (b + 3)  = tune * srz / (sr * root) * float (pow (root / float (std::notes::noteToFrequency (key)), 1.0f - sfZ (o, z, 19) / 100.0f));
                    voices.at (vi).sfl.at (b + 4)  = 0.0f;
                    voices.at (vi).sfl.at (b + 5)  = 1.0f;
                    voices.at (vi).sfl.at (b + 6)  = 0.0f;
                    voices.at (vi).sfl.at (b + 7)  = float (cos (ang)) * att * vg * 1.41421356f;
                    voices.at (vi).sfl.at (b + 8)  = float (sin (ang)) * att * vg * 1.41421356f;
                    voices.at (vi).sfl.at (b + 9)  = float (lm);
                    voices.at (vi).sfl.at (b + 10) = float (o * @BANK@ + @HDR@) + sfZ (o, z, 4);
                    voices.at (vi).sfl.at (b + 11) = float (len);
                    voices.at (vi).sfl.at (b + 12) = float (ls);
                    voices.at (vi).sfl.at (b + 13) = float (le);
                    voices.at (vi).sfl.at (b + 14) = 1.0f / (aMs * 0.001f * sr);
                    voices.at (vi).sfl.at (b + 15) = hMs * 0.001f * sr;
                    voices.at (vi).sfl.at (b + 16) = 1.0f - float (exp (-4.6f / (dMs * 0.001f * sr)));
                    voices.at (vi).sfl.at (b + 17) = sus;
                    voices.at (vi).sfl.at (b + 18) = 1.0f - float (exp (-4.6f / (rMs * 0.001f * sr)));
                    ++nl;
                }
            }
        }
    }

    // one sample of the SoundFont slot o (cf = key frequency with glide, st = octaves of pitch from tuning and modulation)
    float<2> sfStep (int vi, int o, float cf, float st)
    {
        if (! sfHas.at (o))
            return float<2> (0.0f, 0.0f);

        bool  rel  = voices.at (vi).stage == 3;
        float pr   = st != 0.0f ? float (exp (st * 0.6931471805599453f)) : 1.0f;
        float gain = float (pow (10.0f, sfq (o, 0) * 0.6f));
        float yL   = 0.0f;
        float yR   = 0.0f;

        for (int l = 0; l < 4; ++l)
        {
            int b = o * 96 + l * 24;

            if (voices.at (vi).sfl.at (b) < 0.0f || voices.at (vi).sfl.at (b + 5) < 0.5f)
                continue;

            int stg = int (voices.at (vi).sfl.at (b + 5) + 0.5f);
            float e = voices.at (vi).sfl.at (b + 4);

            if (rel && stg < 5)
                stg = 5;

            if (stg == 1)
            {
                e += voices.at (vi).sfl.at (b + 14);

                if (e >= 1.0f)
                {
                    e = 1.0f;
                    voices.at (vi).sfl.at (b + 6) = voices.at (vi).sfl.at (b + 15);
                    stg = 2;
                }
            }
            else if (stg == 2)
            {
                float t = voices.at (vi).sfl.at (b + 6) - 1.0f;
                voices.at (vi).sfl.at (b + 6) = t;

                if (t <= 0.0f)
                    stg = 3;
            }
            else if (stg == 3 || stg == 4)
            {
                float su = voices.at (vi).sfl.at (b + 17);
                e += (su - e) * voices.at (vi).sfl.at (b + 16);
                stg = 3;
            }
            else
            {
                e -= e * voices.at (vi).sfl.at (b + 18);

                if (e < 0.0003f)
                {
                    voices.at (vi).sfl.at (b + 5) = 0.0f;
                    continue;
                }
            }

            voices.at (vi).sfl.at (b + 4) = e;
            voices.at (vi).sfl.at (b + 5) = float (stg);

            int   pi   = int (voices.at (vi).sfl.at (b + 1));
            float pf   = voices.at (vi).sfl.at (b + 2);
            int   len  = int (voices.at (vi).sfl.at (b + 11));
            int   ls   = int (voices.at (vi).sfl.at (b + 12));
            int   le   = int (voices.at (vi).sfl.at (b + 13));
            int   lm   = int (voices.at (vi).sfl.at (b + 9));
            bool  lp   = (lm == 1 || (lm == 3 && stg < 5)) && le > ls + 2;
            int   a0   = int (voices.at (vi).sfl.at (b + 10)) + clamp (pi, 0, len - 1);
            int   p1   = pi + 1;

            if (lp && p1 >= le)
                p1 = p1 - (le - ls);

            int   a1   = int (voices.at (vi).sfl.at (b + 10)) + clamp (p1, 0, len - 1);
            float s    = sfBuf.at (a0) * (1.0f - pf) + sfBuf.at (a1) * pf;
            float g    = s * e;
            yL += g * voices.at (vi).sfl.at (b + 7);
            yR += g * voices.at (vi).sfl.at (b + 8);

            pf += voices.at (vi).sfl.at (b + 3) * cf * pr;
            int adv = int (pf);
            pf -= float (adv);
            pi += adv;

            if (lp)
            {
                while (pi >= le)
                    pi -= le - ls;
            }
            else if (pi >= len - 1)
            {
                voices.at (vi).sfl.at (b + 5) = 0.0f;
                continue;
            }

            voices.at (vi).sfl.at (b + 1) = float (pi);
            voices.at (vi).sfl.at (b + 2) = pf;
        }

        float dr = sfq (o, 9);

        if (dr > 0.001f)
        {
            float gd  = 1.0f + dr * 6.0f;
            float nrm = 1.0f / float (tanh (gd));
            yL = float (tanh (yL * gd)) * nrm;
            yR = float (tanh (yR * gd)) * nrm;
        }

        return float<2> (clamp (yL * gain, -2.0f, 2.0f), clamp (yR * gain, -2.0f, 2.0f));
    }

'''.replace("@LO@", LO).replace("@HI@", HI).replace("@BANKTOTAL@", str(L.SF_BANK * 6)).replace("@BANK@", str(L.SF_BANK)).replace("@HDR@", str(L.SF_HDR)).replace("@ZF@", str(L.SF_ZF)).replace("@MAXZ@", str(L.SF_MAX_ZONES))
STEP = '''                    else if (ty == 12)
                    {
                        float<2> fw = sfStep (i, o, cf, sExp);
                        sL = fw[0];
                        sR = fw[1];
                        stereo = true;
                    }
'''
EXTRAS = [("    input event BankChunk smpBankLoad;\n", "    input event BankChunk smpBankLoad;\n    input event BankChunk sfBankLoad;    // SoundFont source: bank = slot, preamble + zone table + audio  // SF\n")]
srcgen.install(PATCH, "                    spNoteOn (v, o);\n", "SF", L.SF, L.sf_id, L.SF_DST_BASE, DSP,
               "        float[1024]   sfl;    // SoundFont source: layers, slot * 96\n", "                    sfNoteOn (v, o, vel);\n", STEP, "sfSet", "sfP",
               "tools/osc/build_sf.py", "NjoSf.h", "sf", L.SF_BASE, L.SF_STRIDE, EXTRAS)
print("ok")
