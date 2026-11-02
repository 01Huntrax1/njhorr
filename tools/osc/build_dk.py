#!/usr/bin/env python3
"""Adds the Modal Drum source (Source type 10) to patch/Eisenpuls_Synth.cmajor: a drum in the manner of the modal drum models (MODO DRUM, V-Drums, Chromaphone):
 - batter head: 12 modes of a circular membrane (Bessel zeros, weighted by the hit position), damping that grows with the mode number (Head Tone), bearing Edge,
   Stick (Hann pulse, soft .. hard) with velocity, tension modulation (the pitch rises with the vibration energy, Marogna / Avanzini / Bank)
 - resonant head: the same 12 modes tuned against the batter head (Reso Tune), excited by the batter head through the air (coupling = Reso Head)
 - shell: 6 modes excited by the batter head; Size and Shell Depth set their pitch and ring time
 - snare wires: noise that only rattles while the resonant head moves faster than a threshold (Snare Tension), with a fast decay
 - sympathetic resonance: the output of the other Modal Drum slots (previous sample, all voices) excites the heads of this slot
Parameters: ids DK_BASE + 16 * slot + j (layout.py DK), mod destinations 1020 + 16 * slot + j.  State per voice and slot: Voice.dks (slot * 192).
Run after build_ad.py.  Idempotent.  Usage: build_dk.py [patch.cmajor]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L, srcgen
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
LO, HI = srcgen.table(L.DK, 0)
DSP = r'''    // ---------------- Modal Drum source (tools/osc/build_dk.py) ----------------
    // state per voice and slot (Voice.dks, slot * 192): 0 pulse left, 1 pulse length, 2 control counter, 3 energy follower, 4 energy peak, 5 velocity factor, 6 / 7 DC blocker,
    // 8 snare noise low-pass, 9 rattle envelope, 12 trigger, 13 batter sum (previous sample), 16.. batter modes (y1 16, y2 28, a1 40, a2 52, b 64, weight 76),
    // 88.. resonant head (y1 88, y2 100, a1 112, a2 124, b 136, direct b 180), 148.. shell modes (y1 148, y2 154, a1 160, a2 166, b 172)
    float[96] dkP;        // slot * 16 + parameter
    const float[16] dkLo = (@LO@);
    const float[16] dkHi = (@HI@);
    const float[6]  dkSR = (1.0f, 1.62f, 2.31f, 3.05f, 3.9f, 4.8f);   // shell mode ratios
    float[8] dkBus;       // output of every Modal Drum slot in the previous sample (all voices)
    float[8] dkAcc;       // sum of the current sample

    void dkSet (int o, int j, float v)
    {
        dkP.at (o * 16 + j) = v;
    }

    float dkq (int o, int j)
    {
        float v = dkP.at (o * 16 + j);
        float m = vmod.at (1020 + 16 * o + j);

        if (m != 0.0f)
        {
            v += m * 0.5f * (dkHi.at (j) - dkLo.at (j));
            v = clamp (v, dkLo.at (j), dkHi.at (j));
        }

        return v;
    }

    float dkGet (int vi, int i)
    {
        return voices.at (vi).dks.at (i);
    }

    void dkPut (int vi, int i, float v)
    {
        voices.at (vi).dks.at (i) = v;
    }

    void dkNoteOn (int vi, int o)
    {
        if (int (op.at (o * 64) + 0.5f) != 10)
            return;

        for (int i = 0; i < 192; ++i)
            voices.at (vi).dks.at (o * 192 + i) = 0.0f;

        voices.at (vi).dks.at (o * 192 + 12) = 1.0f;
    }

    // coefficients of the three mode banks (every 8 samples, and at the note start)
    void dkUpdate (int vi, int o, float f0, float sr, bool trig)
    {
        int   sb   = o * 192;
        float tp   = 6.2831853f;
        float ex   = dkGet (vi, sb + 3) / (dkGet (vi, sb + 4) + 0.000001f);
        float f    = min (f0 * (1.0f + dkq (o, 12) * 0.5f * ex), sr * 0.45f);
        float it   = 1.0f - dkq (o, 1);
        float t60  = max (0.05f * float (pow (160.0f, dkq (o, 0))) * float (pow (261.63f / f0, 0.3f)), 0.02f);
        float rs   = 0.9f * dkq (o, 2);
        float edge = dkq (o, 4);
        float rt   = float (pow (2.0f, dkq (o, 6) * 7.0f / 12.0f));

        for (int k = 0; k < 12; ++k)
        {
            float rk = wgDR.at (k);

            if (trig)
                dkPut (vi, sb + 76 + k, wgBessel (int (wgDM.at (k)), wgDA.at (k) * rs));

            float ef   = 1.0f / (1.0f + edge * 0.12f * (rk * rk - 1.0f));
            float t60k = max (t60 * float (pow (rk, -2.0f * it)), 0.01f);
            float r    = float (exp (-6.9078f / (sr * t60k)));
            float fk   = f * rk;
            float fr   = f * rt * rk * (1.0f + 0.003f * float (k));

            if (fk > sr * 0.45f)
            {
                dkPut (vi, sb + 40 + k, 0.0f);
                dkPut (vi, sb + 52 + k, 0.0f);
                dkPut (vi, sb + 64 + k, 0.0f);
            }
            else
            {
                float wk = tp * fk / sr;
                dkPut (vi, sb + 40 + k, 2.0f * r * float (cos (wk)));
                dkPut (vi, sb + 52 + k, r * r);
                dkPut (vi, sb + 64 + k, float (sin (wk)) * dkGet (vi, sb + 76 + k) * ef);
            }

            if (fr > sr * 0.45f)
            {
                dkPut (vi, sb + 112 + k, 0.0f);
                dkPut (vi, sb + 124 + k, 0.0f);
                dkPut (vi, sb + 136 + k, 0.0f);
                dkPut (vi, sb + 180 + k, 0.0f);
            }
            else
            {
                float wr  = tp * fr / sr;
                float rr  = float (exp (-6.9078f / (sr * t60k * 0.8f)));
                float wgt = wgDM.at (k) < 0.5f ? 1.0f : 0.35f;
                dkPut (vi, sb + 112 + k, 2.0f * rr * float (cos (wr)));
                dkPut (vi, sb + 124 + k, rr * rr);
                dkPut (vi, sb + 136 + k, 2.0f * (1.0f - rr) * float (sin (wr)) * wgt * ef * 0.6f);   // gain 0.6 at the resonance (coupling by the batter head)
                dkPut (vi, sb + 180 + k, float (sin (wr)) * wgt * ef * 0.35f);                           // the air pressure of the stick hit excites the resonant head directly
            }
        }

        if (trig)
        {
            float size  = dkq (o, 15);
            float depth = dkq (o, 7 + 1);
            float fs    = 180.0f * float (pow (2.0f, -1.6f * size - 1.2f * depth));
            float ts    = 0.08f + 0.35f * size;

            for (int k = 0; k < 6; ++k)
            {
                float fk = fs * dkSR.at (k);

                if (fk > sr * 0.45f)
                {
                    dkPut (vi, sb + 160 + k, 0.0f);
                    dkPut (vi, sb + 166 + k, 0.0f);
                    dkPut (vi, sb + 172 + k, 0.0f);
                }
                else
                {
                    float w = tp * fk / sr;
                    float r = float (exp (-6.9078f / (sr * ts / (1.0f + 0.5f * float (k)))));
                    dkPut (vi, sb + 160 + k, 2.0f * r * float (cos (w)));
                    dkPut (vi, sb + 166 + k, r * r);
                    dkPut (vi, sb + 172 + k, 2.0f * (1.0f - r) * float (sin (w)) / (1.0f + 0.4f * float (k)));
                }
            }
        }
    }

    float dkStep (int vi, int o, float freq)
    {
        int   sb  = o * 192;
        float sr  = float (processor.frequency);
        float f0  = clamp (freq, 20.0f, sr * 0.3f);
        bool  trg = dkGet (vi, sb + 12) > 0.5f;
        int   cnt = int (dkGet (vi, sb + 2));

        if (trg)
        {
            float vel  = clamp (voices.at (vi).velRaw, 0.0f, 1.0f);
            float vw   = dkq (o, 13);
            float vk   = (1.0f - vw) + vw * (0.25f + 1.5f * vel);
            float hard = clamp (dkq (o, 3) + vw * (vel - 0.5f) * 0.8f, 0.0f, 1.0f);
            float len  = max (floor (min (sr * (0.0004f + 0.005f * (1.0f - hard) * (1.0f - hard)), 0.5f * sr / f0)), 4.0f);
            dkPut (vi, sb + 1, len);
            dkPut (vi, sb, len);
            dkPut (vi, sb + 5, vk);
            dkPut (vi, sb + 12, 0.0f);
        }

        if (cnt <= 0 || trg)
        {
            dkUpdate (vi, o, f0, sr, trg);
            cnt = 8;
        }

        dkPut (vi, sb + 2, float (cnt - 1));

        // exciter: a smooth pulse of unit area, plus the sympathetic force of the other drums
        float pe   = 0.0f;
        float left = dkGet (vi, sb);

        if (left >= 0.5f)
        {
            float len = dkGet (vi, sb + 1);
            float n   = len - left;
            dkPut (vi, sb, left - 1.0f);
            pe = (0.5f - 0.5f * float (cos (6.2831853f * (n + 0.5f) / len))) * 2.0f / len * dkGet (vi, sb + 5);
        }

        float sym = dkq (o, 11);
        float bus = 0.0f;

        if (sym > 0.001f)
        {
            for (int k = 0; k < 6; ++k)
                if (k != o)
                    bus += dkBus.at (k);

            bus *= sym;
        }

        float bsum = 0.0f;
        float rsum = 0.0f;
        float eb   = pe + 0.0004f * bus;
        float er   = dkGet (vi, sb + 13) + 4.0f * bus;

        for (int k = 0; k < 12; ++k)
        {
            float y1 = dkGet (vi, sb + 16 + k);
            float y2 = dkGet (vi, sb + 28 + k);
            float y  = dkGet (vi, sb + 64 + k) * eb + dkGet (vi, sb + 40 + k) * y1 - dkGet (vi, sb + 52 + k) * y2;
            dkPut (vi, sb + 28 + k, y1);
            dkPut (vi, sb + 16 + k, y);
            bsum += y;

            float z1 = dkGet (vi, sb + 88 + k);
            float z2 = dkGet (vi, sb + 100 + k);
            float z  = dkGet (vi, sb + 136 + k) * er + dkGet (vi, sb + 180 + k) * pe + dkGet (vi, sb + 112 + k) * z1 - dkGet (vi, sb + 124 + k) * z2;
            dkPut (vi, sb + 100 + k, z1);
            dkPut (vi, sb + 88 + k, z);
            rsum += z;
        }

        dkPut (vi, sb + 13, bsum);

        float ssum = 0.0f;
        float shl  = dkq (o, 7);

        if (shl > 0.001)
        {
            float es = 0.3f * bsum;

            for (int k = 0; k < 6; ++k)
            {
                float y1 = dkGet (vi, sb + 148 + k);
                float y2 = dkGet (vi, sb + 154 + k);
                float y  = dkGet (vi, sb + 172 + k) * es + dkGet (vi, sb + 160 + k) * y1 - dkGet (vi, sb + 166 + k) * y2;
                dkPut (vi, sb + 154 + k, y1);
                dkPut (vi, sb + 148 + k, y);
                ssum += y;
            }
        }

        float y = 0.45f * (bsum + dkq (o, 5) * 0.9f * rsum + shl * 1.2f * ssum);

        // energy follower (tension modulation)
        float en = dkGet (vi, sb + 3);
        en += (y * y - en) * 0.002f;
        dkPut (vi, sb + 3, en);
        dkPut (vi, sb + 4, max (dkGet (vi, sb + 4), en));

        // snare wires: they rattle only while the resonant head moves faster than a threshold, then ring out quickly
        float sn = dkq (o, 9);

        if (sn > 0.001f)
        {
            float st  = dkq (o, 10);
            float thr = 0.004f + 0.05f * st;
            float ex  = max (abs (0.4f * rsum + 0.2f * bus) - thr, 0.0f);   // (the head amplitudes are about 1 for a hit of velocity 1)
            float rv  = dkGet (vi, sb + 9);
            rv = max (ex * 6.0f, rv * (1.0f - 1.0f / (sr * (0.18f - 0.14f * st))));
            dkPut (vi, sb + 9, rv);
            float nz = nextNoise();
            float lp = dkGet (vi, sb + 8);
            lp += 0.35f * (nz - lp);
            dkPut (vi, sb + 8, lp);
            y += sn * (nz - lp) * min (rv, 1.0f) * 0.25f;
        }

        float dr = dkq (o, 14);

        if (dr > 0.001f)
        {
            float gd = 1.0f + dr * 6.0f;
            y = float (tanh (y * gd)) / float (tanh (gd));
        }

        // DC blocker
        float x1 = dkGet (vi, sb + 6);
        float y1 = dkGet (vi, sb + 7);
        float yo = y - x1 + 0.995f * y1;
        dkPut (vi, sb + 6, y);
        dkPut (vi, sb + 7, yo);
        dkAcc.at (o) += yo;
        return clamp (yo, -2.0f, 2.0f);
    }

'''.replace("@LO@", LO).replace("@HI@", HI)
STEP = '''                    else if (ty == 10)
                    {
                        sL = dkStep (i, o, freq);
                        sR = sL;
                    }
'''
srcgen.install(PATCH, "                    adNoteOn (v, o);\n", "DK", L.DK, L.dk_id, L.DK_DST_BASE, DSP,
               "        float[2048]   dks;    // Modal Drum source: modes, slot * 192\n", "                    dkNoteOn (v, o);\n", STEP, "dkSet", "dkP",
               "tools/osc/build_dk.py", "NjoDk.h", "dk", L.DK_BASE, L.DK_STRIDE,
               extras=(("    float[1024] vmod;  // padded to a power of two (cheap index wrap)", "    float[2048] vmod;  // padded to a power of two (cheap index wrap)"),
                       ("            // ----- global mod destinations: drive, pan, output gain -----\n",
                        "            for (int dq = 0; dq < 6; ++dq)   // Modal Drum sympathetic bus: this sample's outputs are heard by the next sample\n            {\n                dkBus.at (dq) = dkAcc.at (dq);\n                dkAcc.at (dq) = 0.0f;\n            }\n\n            // ----- global mod destinations: drive, pan, output gain -----\n")))
print("ok")
