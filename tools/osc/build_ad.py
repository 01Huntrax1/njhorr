#!/usr/bin/env python3
"""Adds the Additive source (Source type 9) to patch/Eisenpuls_Synth.cmajor: up to 64 partials, each a rotating phasor (no sine calls per sample), with eight spectra
(Saw, Square, Triangle, Organ, Bell, Vowel, Brass, Hollow) of which two are morphed, Tilt, Odd / Even balance, Inharmonicity (stiff string stretch), a formant bump, Shimmer
(slow random-like amplitude movement per partial), Partial Decay (the high partials die first), stereo Width (odd partials left, even right), velocity brightness and drive.
The amplitudes are recomputed every 32 samples and smoothed.  Parameters: ids AD_BASE + 16 * slot + j (layout.py AD), mod destinations 924 + 16 * slot + j.
State per voice and slot: Voice.ads (slot * 512): partial n at sin n, cos 64 + n, step sin 128 + n, step cos 192 + n, amplitude 256 + n, target 320 + n;
384 counter, 385 time (s), 386 highest partial in use, 387 target level.  Run after build_gr.py.  Idempotent.  Usage: build_ad.py [patch.cmajor]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L, srcgen
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
LO, HI = srcgen.table(L.AD, 0)
DSP = r'''    // ---------------- Additive source (tools/osc/build_ad.py) ----------------
    float[96] adP;        // slot * 16 + parameter
    const float[16] adLo = (@LO@);
    const float[16] adHi = (@HI@);

    void adSet (int o, int j, float v)
    {
        adP.at (o * 16 + j) = v;
    }

    float adq (int o, int j)
    {
        float v = adP.at (o * 16 + j);
        float m = vmod.at (924 + 16 * o + j);

        if (m != 0.0f)
        {
            v += m * 0.5f * (adHi.at (j) - adLo.at (j));
            v = clamp (v, adLo.at (j), adHi.at (j));
        }

        return v;
    }

    void adNoteOn (int vi, int o)
    {
        if (int (op.at (o * 64) + 0.5f) != 9)
            return;

        for (int i = 0; i < 512; ++i)
            voices.at (vi).ads.at (o * 512 + i) = 0.0f;

        for (int n = 0; n < 64; ++n)
            voices.at (vi).ads.at (o * 512 + 64 + n) = 1.0f;
    }

    // amplitude of partial n (1..) in spectrum sh at the fundamental f0
    float adShape (int sh, int n, float f0)
    {
        float fn = float (n);
        int   od = n - (n / 2) * 2;

        if (sh == 0)
            return 1.0f / fn;

        if (sh == 1)
            return od == 1 ? 1.0f / fn : 0.0f;

        if (sh == 2)
            return od == 1 ? 1.0f / (fn * fn) * 1.6f : 0.0f;

        if (sh == 3)
        {
            if (n == 1) return 1.0f;
            if (n == 2) return 0.8f;
            if (n == 3) return 0.7f;
            if (n == 4) return 0.6f;
            if (n == 6) return 0.5f;
            if (n == 8) return 0.4f;
            return 0.0f;
        }

        if (sh == 4)
        {
            float sn = float (sin (fn * 2.3f));
            return float (pow (fn, -0.8f)) * (0.15f + sn * sn);
        }

        if (sh == 5)
        {
            float f = fn * f0;
            float a = float (exp (-0.5f * (f - 650.0f) * (f - 650.0f) / (150.0f * 150.0f))) + 0.7f * float (exp (-0.5f * (f - 1100.0f) * (f - 1100.0f) / (200.0f * 200.0f)))
                      + 0.4f * float (exp (-0.5f * (f - 2600.0f) * (f - 2600.0f) / (300.0f * 300.0f)));
            return (0.04f + a) / sqrt (fn);
        }

        if (sh == 6)
            return float (pow (fn, -0.5f)) * (1.0f - float (exp (-0.6f * fn)));

        return (n - (n / 3) * 3) == 0 ? 0.0f : 1.0f / fn;
    }

    void adUpdate (int vi, int o, float f0, float sr)
    {
        int   sb  = o * 512;
        int   cnt = clamp (int (adq (o, 3) + 0.5f), 1, 64);
        int   shA = clamp (int (adq (o, 0) + 0.5f), 0, 7);
        int   shB = clamp (int (adq (o, 1) + 0.5f), 0, 7);
        float mo  = adq (o, 2);
        float vel = clamp (voices.at (vi).velRaw, 0.0f, 1.0f);
        float ex  = adq (o, 4) * 1.5f - (vel * 2.0f - 1.0f) * adq (o, 14) * 0.8f;
        float odd = adq (o, 5);
        float inh = adq (o, 6) * adq (o, 6) * 0.02f;
        float fc  = adq (o, 7) * 6.0f;
        float fg  = adq (o, 8) * 3.0f;
        float shm = adq (o, 9) * 0.7f;
        float shr = adq (o, 10);
        float dec = adq (o, 11) * adq (o, 11) * 8.0f;
        float t   = voices.at (vi).ads.at (sb + 385);
        float ss  = 0.0f;
        int   hi  = 0;

        for (int n = 1; n <= 64; ++n)
        {
            float tg = 0.0f;
            float fn = float (n) * f0 * sqrt (1.0f + inh * float (n * n));

            if (n <= cnt && fn < 0.45f * sr)
            {
                float a = adShape (shA, n, f0);

                if (mo > 0.0f)
                    a = a * (1.0f - mo) + adShape (shB, n, f0) * mo;

                a *= float (pow (float (n), -ex));
                a *= (n - (n / 2) * 2) == 1 ? 1.0f + odd : 1.0f - odd;

                if (fg > 0.0f)
                {
                    float d = (float (log (float (n))) * 1.442695f - fc) / 0.35f;
                    a *= 1.0f + fg * float (exp (-0.5f * d * d));
                }

                if (dec > 0.0f)
                    a *= float (exp (-t * dec * float (n - 1) / float (cnt)));

                if (shm > 0.0f)
                    a *= max (1.0f + shm * float (sin (6.2831853f * shr * t + float (n) * 1.9f)), 0.0f);

                tg = max (a, 0.0f);
            }

            voices.at (vi).ads.at (sb + 320 + n - 1) = tg;
            ss += tg * tg;

            if (tg > 0.0f || voices.at (vi).ads.at (sb + 256 + n - 1) > 0.001f)
                hi = n;

            float w = 6.2831853f * min (fn, 0.49f * sr) / sr;
            voices.at (vi).ads.at (sb + 128 + n - 1) = float (sin (w));
            voices.at (vi).ads.at (sb + 192 + n - 1) = float (cos (w));
        }

        voices.at (vi).ads.at (sb + 386) = float (hi);
        voices.at (vi).ads.at (sb + 387) = 0.45f / sqrt (ss * 0.5f + 0.000001f);
        voices.at (vi).ads.at (sb + 385) = t + 32.0f / sr;
    }

    float<2> adStep (int vi, int o, float freq)
    {
        float sr  = float (processor.frequency);
        int   sb  = o * 512;
        int   cnt = int (voices.at (vi).ads.at (sb + 384));

        if (cnt <= 0)
        {
            adUpdate (vi, o, freq, sr);
            cnt = 32;

            // keep the phasors on the unit circle
            for (int n = 0; n < 64; ++n)
            {
                float s = voices.at (vi).ads.at (sb + n);
                float c = voices.at (vi).ads.at (sb + 64 + n);
                float r = 1.0f / sqrt (s * s + c * c + 0.0000001f);
                voices.at (vi).ads.at (sb + n) = s * r;
                voices.at (vi).ads.at (sb + 64 + n) = c * r;
            }
        }

        voices.at (vi).ads.at (sb + 384) = float (cnt - 1);

        int   hi   = int (voices.at (vi).ads.at (sb + 386));
        float sOdd = 0.0f;
        float sEvn = 0.0f;

        for (int n = 0; n < hi; ++n)
        {
            float s  = voices.at (vi).ads.at (sb + n);
            float c  = voices.at (vi).ads.at (sb + 64 + n);
            float ds = voices.at (vi).ads.at (sb + 128 + n);
            float dc = voices.at (vi).ads.at (sb + 192 + n);
            float am = voices.at (vi).ads.at (sb + 256 + n);
            float ns = s * dc + c * ds;
            float nc = c * dc - s * ds;
            am += (voices.at (vi).ads.at (sb + 320 + n) - am) * 0.04f;
            voices.at (vi).ads.at (sb + n) = ns;
            voices.at (vi).ads.at (sb + 64 + n) = nc;
            voices.at (vi).ads.at (sb + 256 + n) = am;

            if ((n - (n / 2) * 2) == 0)
                sOdd += ns * am;
            else
                sEvn += ns * am;
        }

        float g  = voices.at (vi).ads.at (sb + 387);
        float wd = adq (o, 13);
        float yL = g * (sOdd * (1.0f + wd) + sEvn * (1.0f - wd)) * 0.5f;
        float yR = g * (sOdd * (1.0f - wd) + sEvn * (1.0f + wd)) * 0.5f;
        float dr = adq (o, 12);

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
STEP = '''                    else if (ty == 9)
                    {
                        float<2> aw = adStep (i, o, freq);
                        sL = aw[0];
                        sR = aw[1];
                        stereo = true;
                    }
'''
srcgen.install(PATCH, "                    grNoteOn (v, o);\n", "AD", L.AD, L.ad_id, L.AD_DST_BASE, DSP,
               "        float[4096]   ads;    // Additive source: partials, slot * 512\n", "                    adNoteOn (v, o);\n", STEP, "adSet", "adP",
               "tools/osc/build_ad.py", "NjoAd.h", "ad", L.AD_BASE, L.AD_STRIDE)
print("ok")
