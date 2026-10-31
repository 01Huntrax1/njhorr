#!/usr/bin/env python3
"""Adds the Waveguide source (Source type 6) to patch/Eisenpuls_Synth.cmajor.  Five physical models: Karplus-Strong (extended: loop damping, stiffness
allpass, saturation, tension modulation), Bowed String (two delay lines + bow friction table), Clarinet (reed table in an inverting bore loop), Banded Waveguide
(four band-pass / delay loops with bar, glass or harmonic mode ratios, struck) and Drum (12 Bessel modes of a circular membrane with strike position, tension
modulation, a snare wire layer).  Common: body resonances, drive, velocity.  Parameters: ids WG_BASE + 16 * slot + j (layout.py WG), mod destinations 636 + 16 * slot + j.
All loops are tuned with the exact phase delay of their filters, so the pitch follows the key.  Delay memory per voice: Voice.wgd (slot * 16384), state Voice.wgs (slot * 192).
Run after build_ter.py.  Idempotent.  Usage: build_wg.py [patch.cmajor]"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
K = L.WG
def tab(f): return ", ".join("%sf" % repr(float(f(p))) for p in K)
LO, HI = tab(lambda p: p[4]), tab(lambda p: p[5])
DSP = r'''    // ---------------- Waveguide source (tools/osc/build_wg.py) ----------------
    // State per voice and slot: Voice.wgs (slot * 192): 0 write pointer, 1 trigger, 2 control counter, 3 energy follower, 4 energy peak, 5 bow / breath envelope,
    // 6 / 7 DC blocker, 8..11 body filter states, 12 snare filter, 13 snare follower, 14 loop low-pass, 15 stiffness allpass, 16 interpolation allpass, 17 delay M (neck),
    // 18 allpass coefficient, 19 loop gain, 20 low-pass coefficient, 21 stiffness coefficient, 22 delay M2 (bridge), 23 envelope rate, 24 / 25 exciter pulse left / length,
    // 28 .. 31 model values, 32 body, 33 drive, 34 snare, 35 excitation scale, 36 .. 41 body filter coefficients, 48.. banded bands, 96.. drum modes, 160.. weights.
    // Delay lines: Voice.wgd (slot * 16384): one line of 8192 (Karplus-Strong, Clarinet), two of 8192 (Bowed), four of 4096 (Banded).
    float[96] wgP;        // slot * 16 + parameter
    const float[16] wgLo = (@LO@);
    const float[16] wgHi = (@HI@);
    const float[5]  wgOut = (1.1f, 2.0f, 1.0f, 0.8f, 0.4f);                        // output level per model
    const float[12] wgDR  = (1.0f, 1.594f, 2.136f, 2.296f, 2.653f, 2.918f, 3.156f, 3.501f, 3.600f, 3.652f, 4.060f, 4.231f);   // membrane mode ratios (Bessel zeros / 2.405)
    const float[12] wgDM  = (0.0f, 1.0f, 2.0f, 0.0f, 3.0f, 1.0f, 4.0f, 2.0f, 0.0f, 5.0f, 3.0f, 1.0f);                         // azimuthal orders
    const float[12] wgDA  = (2.405f, 3.832f, 5.136f, 5.520f, 6.380f, 7.016f, 7.588f, 8.417f, 8.654f, 8.771f, 9.761f, 10.173f); // Bessel zeros

    void wgSet (int o, int j, float v)
    {
        wgP.at (o * 16 + j) = v;
    }

    float wgq (int o, int j)
    {
        float v = wgP.at (o * 16 + j);
        float m = vmod.at (636 + 16 * o + j);

        if (m != 0.0f)
        {
            v += m * 0.5f * (wgHi.at (j) - wgLo.at (j));
            v = clamp (v, wgLo.at (j), wgHi.at (j));
        }

        return v;
    }

    float wgGet (int vi, int i)
    {
        return voices.at (vi).wgs.at (i);
    }

    void wgPut (int vi, int i, float v)
    {
        voices.at (vi).wgs.at (i) = v;
    }

    void wgNoteOn (int vi, int o)
    {
        if (int (op.at (o * 64) + 0.5f) != 6)
            return;

        for (int i = 0; i < 192; ++i)
            voices.at (vi).wgs.at (o * 192 + i) = 0.0f;

        for (int i = 0; i < 16384; ++i)
            voices.at (vi).wgd.at (o * 16384 + i) = 0.0f;

        voices.at (vi).wgs.at (o * 192 + 1) = 1.0f;
    }

    // phase delay (samples) and gain of the one-pole low-pass y = (1 - a) x + a y1 at w = 2 pi f / fs
    float wgLpDelay (float a, float w)
    {
        return float (atan2 (a * float (sin (w)), 1.0f - a * float (cos (w)))) / w;
    }

    float wgLpGain (float a, float w)
    {
        return (1.0f - a) / float (sqrt (1.0f - 2.0f * a * float (cos (w)) + a * a));
    }

    // first order allpass (c + z^-1) / (1 + c z^-1): phase delay at w, and the coefficient that gives the delay tau at w
    float wgApDelay (float c, float w)
    {
        float th = float (atan2 (c * float (sin (w)), 1.0f + c * float (cos (w))));
        return 1.0f - 2.0f * th / w;
    }

    float wgApCoef (float tau, float w)
    {
        float th = w * (1.0f - tau) * 0.5f;
        return clamp (float (sin (th)) / float (sin (w - th)), -0.95f, 0.95f);
    }

    // constant 0 dB peak band-pass: b0, a1, a2 (b1 = 0, b2 = -b0)
    float<3> wgBpC (float fc, float q, float sr)
    {
        float w  = 6.2831853f * fc / sr;
        float al = float (sin (w)) / (2.0f * q);
        float a0 = 1.0f + al;
        return float<3> (al / a0, -2.0f * float (cos (w)) / a0, (1.0f - al) / a0);
    }

    float wgBessel (int m, float x)
    {
        float h    = 0.5f * x;
        float term = 1.0f;

        for (int i = 1; i <= m; ++i)
            term *= h / float (i);

        float s = term;
        float q = -h * h;

        for (int k = 1; k < 24; ++k)
        {
            term *= q / (float (k) * float (k + m));
            s += term;
        }

        return s;
    }

    // control rate (every 8 samples, and at a note start): coefficients of the selected model
    void wgUpdate (int vi, int o, int mdl, float f0, float sr, bool trig)
    {
        int   sb   = o * 192;
        float tp   = 6.2831853f;
        float ex   = wgGet (vi, sb + 3) / (wgGet (vi, sb + 4) + 0.000001f);
        float gl   = wgq (o, 14);
        float mult = 1.0f;

        if (mdl == 0)
            mult = 1.0f + gl * 0.12f * ex;
        else if (mdl == 4)
            mult = 1.0f + gl * 0.5f * ex;

        float f    = min (f0 * mult, sr * 0.45f);
        float T    = sr / f;
        float w0   = tp * f / sr;
        float tone = wgq (o, 2);
        float it   = 1.0f - tone;
        float t60  = max (0.05f * float (pow (400.0f, wgq (o, 1))) * float (pow (261.63f / f0, wgq (o, 15))), 0.02f);
        float gT   = float (exp (-6.9078f * T / (sr * t60)));

        // body resonances, drive, snare amount
        float bm = wgq (o, 10);
        wgPut (vi, sb + 32, bm);
        wgPut (vi, sb + 33, wgq (o, 13));
        wgPut (vi, sb + 34, wgq (o, 9));

        if (bm > 0.001f)
        {
            float fb = 80.0f * float (pow (2.0f, 5.0f * wgq (o, 11)));
            float<3> c1 = wgBpC (fb, 6.0f, sr);
            float<3> c2 = wgBpC (min (fb * 2.3f, sr * 0.45f), 6.0f, sr);
            wgPut (vi, sb + 36, c1[0]); wgPut (vi, sb + 37, c1[1]); wgPut (vi, sb + 38, c1[2]);
            wgPut (vi, sb + 39, c2[0]); wgPut (vi, sb + 40, c2[1]); wgPut (vi, sb + 41, c2[2]);
        }

        if (mdl == 0)
        {
            // Karplus-Strong: delay line + damping low-pass + stiffness allpass + interpolation allpass
            float a    = 0.9f * it * it;
            float rl   = T / 6.0f;
            float cmx  = min (0.9f, (rl - 1.0f) / (rl + 1.0f));
            float cd   = rl > 1.0f ? -cmx * float (pow (wgq (o, 7), 0.6f)) : 0.0f;   // two stages: at most a third of the period
            float rest = T - wgLpDelay (a, w0) - 2.0f * wgApDelay (cd, w0);
            float Mf   = max (floor (rest - 0.5f), 1.0f);
            float ta   = clamp (rest - Mf, 0.3f, 1.7f);
            wgPut (vi, sb + 17, Mf);
            wgPut (vi, sb + 18, wgApCoef (ta, w0));
            wgPut (vi, sb + 19, min (gT / wgLpGain (a, w0), 0.99995f));
            wgPut (vi, sb + 20, a);
            wgPut (vi, sb + 21, cd);
            wgPut (vi, sb + 28, wgq (o, 6));
        }
        else if (mdl == 1)
        {
            // Bowed string: neck line (M1) and bridge line (M2), friction table at the bow
            float a    = 0.02f + 0.7f * it * it;
            float rest = T - wgLpDelay (a, w0);
            float Mt   = max (floor (rest - 0.5f), 8.0f);
            float ta   = clamp (rest - Mt, 0.3f, 1.7f);
            float beta = 0.05f + 0.4f * wgq (o, 4);
            float M2   = clamp (floor (beta * Mt), 2.0f, Mt - 2.0f);
            wgPut (vi, sb + 17, Mt - M2);
            wgPut (vi, sb + 22, M2);
            wgPut (vi, sb + 18, wgApCoef (ta, w0));
            wgPut (vi, sb + 19, min (gT / wgLpGain (a, w0), 0.9995f));
            wgPut (vi, sb + 20, a);
            wgPut (vi, sb + 28, 5.0f - 4.0f * wgq (o, 3));
            wgPut (vi, sb + 29, wgq (o, 6) * 0.15f);
            wgPut (vi, sb + 30, 0.1f + 0.15f * wgGet (vi, sb + 35));
            wgPut (vi, sb + 31, wgq (o, 5));
            wgPut (vi, sb + 23, 1.0f - float (exp (-1.0f / (sr * 0.005f * float (pow (200.0f, wgq (o, 8)))))));
        }
        else if (mdl == 2)
        {
            // Clarinet: inverting bore loop of half the period
            float Th   = T * 0.5f;
            float a    = 0.05f + 0.5f * it;
            float rest = Th - wgLpDelay (a, w0);
            float Mf   = max (floor (rest - 0.5f), 2.0f);
            float ta   = clamp (rest - Mf, 0.3f, 1.7f);
            wgPut (vi, sb + 17, Mf);
            wgPut (vi, sb + 18, wgApCoef (ta, w0));
            wgPut (vi, sb + 19, clamp (float (exp (-6.9078f * Th / (sr * t60))), 0.5f, 0.995f));
            wgPut (vi, sb + 20, a);
            // reed table: output = offset + slope * pressure difference, clipped to +-1.  The loop oscillates for a breath pressure between
            // lo (loop gain 1) and hi (the reed is shut), so Breath runs from just above the threshold to just below the closing pressure.
            float sl  = 0.26f + 0.18f * (1.0f - wgq (o, 4));
            float of  = 0.7f + 0.1f * wgq (o, 6);
            float lo  = (1.005f - of) / (2.0f * sl) * 1.08f;
            float hi  = (1.0f - of) / sl * 0.95f;
            float vkk = wgGet (vi, sb + 35);
            wgPut (vi, sb + 28, -sl);
            wgPut (vi, sb + 29, of);
            wgPut (vi, sb + 30, min ((lo + (hi - lo) * wgq (o, 3)) * (0.85f + 0.15f * vkk), hi));
            wgPut (vi, sb + 31, wgq (o, 5));
            wgPut (vi, sb + 23, 1.0f - float (exp (-1.0f / (sr * 0.005f * float (pow (200.0f, wgq (o, 8)))))));
        }
        else if (mdl == 3)
        {
            // Banded waveguide: four band-pass / delay loops at bar, glass or harmonic mode ratios
            float s = wgq (o, 7);

            for (int k = 0; k < 4; ++k)
            {
                float kb = float (k);
                float rb = k == 0 ? 1.0f : (k == 1 ? 2.756f : (k == 2 ? 5.404f : 8.933f));
                float rg = k == 0 ? 1.0f : (k == 1 ? 2.32f : (k == 2 ? 4.25f : 6.63f));
                float rh = kb + 1.0f;
                float r  = s < 0.5f ? rb + (rg - rb) * s * 2.0f : rg + (rh - rg) * (s - 0.5f) * 2.0f;
                float fk = f * r;

                if (fk > sr * 0.45f)
                {
                    wgPut (vi, sb + 68 + k, 0.0f);
                }
                else
                {
                    float Lk   = sr / fk;
                    float wk   = tp * fk / sr;
                    float Mf   = max (floor (Lk - 0.5f), 1.0f);
                    float ta   = clamp (Lk - Mf, 0.3f, 1.7f);
                    float t60k = max (t60 * float (pow (r, -1.5f * it)), 0.01f);
                    float<3> c = wgBpC (fk, 24.0f, sr);
                    wgPut (vi, sb + 60 + k, Mf);
                    wgPut (vi, sb + 64 + k, wgApCoef (ta, wk));
                    wgPut (vi, sb + 68 + k, min (float (exp (-6.9078f * Lk / (sr * t60k))), 0.99995f));
                    wgPut (vi, sb + 72 + k, c[0]);
                    wgPut (vi, sb + 76 + k, c[1]);
                    wgPut (vi, sb + 80 + k, c[2]);
                    wgPut (vi, sb + 84 + k, 0.5f / c[0]);
                }

                if (trig)
                    wgPut (vi, sb + 160 + k, 0.2f + 0.8f * abs (float (sin (3.14159265f * (kb + 1.0f) * (0.1f + 0.4f * wgq (o, 4))))));
            }
        }
        else
        {
            // Drum: 12 modes of a circular membrane
            float spread = 1.0f + 0.6f * wgq (o, 7);
            float rs     = 0.9f * wgq (o, 4);

            for (int k = 0; k < 12; ++k)
            {
                if (trig)
                    wgPut (vi, sb + 160 + k, wgBessel (int (wgDM.at (k)), wgDA.at (k) * rs));

                float rk = wgDR.at (k);
                float fk = f * (1.0f + (rk - 1.0f) * spread);

                if (fk > sr * 0.45f)
                {
                    wgPut (vi, sb + 144 + k, 0.0f);
                    wgPut (vi, sb + 120 + k, 0.0f);
                    wgPut (vi, sb + 132 + k, 0.0f);
                }
                else
                {
                    float wk   = tp * fk / sr;
                    float t60k = max (t60 * float (pow (rk, -2.0f * it)), 0.01f);
                    float r    = float (exp (-6.9078f / (sr * t60k)));
                    wgPut (vi, sb + 120 + k, 2.0f * r * float (cos (wk)));
                    wgPut (vi, sb + 132 + k, r * r);
                    wgPut (vi, sb + 144 + k, float (sin (wk)) * wgGet (vi, sb + 160 + k));
                }
            }
        }
    }

    // note start: the exciter. Karplus-Strong fills its loop with a plucked shape, the struck models get a smooth pulse (length from the hardness).
    void wgTrigger (int vi, int o, int mdl, float sr, float f0, float vk)
    {
        int   sb   = o * 192;
        int   db   = o * 16384;
        float hard = wgq (o, 3);
        float nz   = wgq (o, 5);
        wgPut (vi, sb + 35, vk);

        if (mdl == 0)
        {
            int   M   = int (wgGet (vi, sb + 17));
            int   w   = int (wgGet (vi, sb));
            float pos = 0.04f + 0.92f * wgq (o, 4);
            float ae  = 0.92f * (1.0f - hard) * (1.0f - hard);
            float lp  = 0.0f;
            float sum = 0.0f;

            for (int n = 0; n < M; ++n)
            {
                float x   = (float (n) + 0.5f) / float (M);
                float tri = x < pos ? x / pos : (1.0f - x) / (1.0f - pos);
                float e   = (1.0f - nz) * tri + nz * nextNoise() * 0.5f;
                lp = (1.0f - ae) * e + ae * lp;
                voices.at (vi).wgd.at (db + ((w - M + n) & 8191)) = lp;
                sum += lp;
            }

            float mean = sum / float (M);

            for (int n = 0; n < M; ++n)
            {
                int idx = db + ((w - M + n) & 8191);
                voices.at (vi).wgd.at (idx) = (voices.at (vi).wgd.at (idx) - mean) * 1.6f * vk;
            }
        }
        else if (mdl == 3 || mdl == 4)
        {
            float len = max (floor (min (sr * (0.0004f + 0.006f * (1.0f - hard) * (1.0f - hard)), 0.5f * sr / f0)), 4.0f);   // never longer than half a period
            wgPut (vi, sb + 24, len);
            wgPut (vi, sb + 25, len);
        }
    }

    // exciter pulse of the struck models: a smooth (Hann) pulse of unit area, mixed with noise
    float wgPulse (int vi, int sb, float nz)
    {
        float left = wgGet (vi, sb + 24);

        if (left < 0.5f)
            return 0.0f;

        float len = wgGet (vi, sb + 25);
        float n   = len - left;
        wgPut (vi, sb + 24, left - 1.0f);
        float hn  = 0.5f - 0.5f * float (cos (6.2831853f * (n + 0.5f) / len));
        return hn * 2.0f / len * ((1.0f - nz) + nz * nextNoise() * 4.0f) * wgGet (vi, sb + 35);
    }

    float wgKS (int vi, int o)
    {
        int   sb  = o * 192;
        int   db  = o * 16384;
        int   w   = int (wgGet (vi, sb));
        int   M   = int (wgGet (vi, sb + 17));
        float ci  = wgGet (vi, sb + 18);
        float g   = wgGet (vi, sb + 19);
        float a   = wgGet (vi, sb + 20);
        float cd  = wgGet (vi, sb + 21);
        float v   = voices.at (vi).wgd.at (db + ((w - M) & 8191));
        float yd  = cd * v + wgGet (vi, sb + 15);
        wgPut (vi, sb + 15, v - cd * yd);
        float yd2 = cd * yd + wgGet (vi, sb + 26);
        wgPut (vi, sb + 26, yd - cd * yd2);
        yd = yd2;
        float lp  = (1.0f - a) * yd + a * wgGet (vi, sb + 14);
        wgPut (vi, sb + 14, lp);
        float yi  = ci * lp + wgGet (vi, sb + 16);
        wgPut (vi, sb + 16, lp - ci * yi);
        float y   = yi * g;
        float sat = wgGet (vi, sb + 28);

        if (sat > 0.001f)
        {
            float k = 1.0f + 3.0f * sat;
            y = float (tanh (y * k)) / k;
        }

        voices.at (vi).wgd.at (db + (w & 8191)) = y;
        wgPut (vi, sb, float ((w + 1) & 65535));
        return y;
    }

    float wgBow (int vi, int o)
    {
        int   sb  = o * 192;
        int   db  = o * 16384;
        int   w   = int (wgGet (vi, sb));
        int   M1  = int (wgGet (vi, sb + 17));
        int   M2  = int (wgGet (vi, sb + 22));
        float ci  = wgGet (vi, sb + 18);
        float g   = wgGet (vi, sb + 19);
        float a   = wgGet (vi, sb + 20);
        float env = wgGet (vi, sb + 5);
        env += wgGet (vi, sb + 23) * (1.0f - env);
        wgPut (vi, sb + 5, env);
        float bv  = env * wgGet (vi, sb + 30) * (1.0f + wgGet (vi, sb + 31) * 0.2f * nextNoise());
        float rN  = voices.at (vi).wgd.at (db + ((w - M1) & 8191));
        float rB  = voices.at (vi).wgd.at (db + 8192 + ((w - M2) & 8191));
        float lp  = (1.0f - a) * rB + a * wgGet (vi, sb + 14);
        wgPut (vi, sb + 14, lp);
        float yi  = ci * lp + wgGet (vi, sb + 16);
        wgPut (vi, sb + 16, lp - ci * yi);
        float bridgeRefl = -g * yi;
        float nutRefl    = -rN;
        float vd  = bv - (bridgeRefl + nutRefl);
        float x   = abs ((vd + wgGet (vi, sb + 29)) * wgGet (vi, sb + 28)) + 0.75f;
        float tab = min (1.0f / (x * x * x * x), 1.0f);
        float nv  = vd * tab;
        voices.at (vi).wgd.at (db + (w & 8191))        = bridgeRefl + nv;
        voices.at (vi).wgd.at (db + 8192 + (w & 8191)) = nutRefl + nv;
        wgPut (vi, sb, float ((w + 1) & 65535));
        return rB;
    }

    float wgClar (int vi, int o)
    {
        int   sb  = o * 192;
        int   db  = o * 16384;
        int   w   = int (wgGet (vi, sb));
        int   M   = int (wgGet (vi, sb + 17));
        float ci  = wgGet (vi, sb + 18);
        float g   = wgGet (vi, sb + 19);
        float a   = wgGet (vi, sb + 20);
        float env = wgGet (vi, sb + 5);
        env += wgGet (vi, sb + 23) * (1.0f - env);
        wgPut (vi, sb + 5, env);
        float breath = env * wgGet (vi, sb + 30) * (1.0f + wgGet (vi, sb + 31) * 0.3f * nextNoise());
        float rb  = voices.at (vi).wgd.at (db + ((w - M) & 8191));
        float lp  = (1.0f - a) * rb + a * wgGet (vi, sb + 14);
        wgPut (vi, sb + 14, lp);
        float yi  = ci * lp + wgGet (vi, sb + 16);
        wgPut (vi, sb + 16, lp - ci * yi);
        float pd  = -g * yi - breath;
        float rt  = clamp (wgGet (vi, sb + 29) + wgGet (vi, sb + 28) * pd, -1.0f, 1.0f);
        voices.at (vi).wgd.at (db + (w & 8191)) = breath + pd * rt;
        wgPut (vi, sb, float ((w + 1) & 65535));
        return rb;
    }

    float wgBand (int vi, int o, float e)
    {
        int   sb  = o * 192;
        int   db  = o * 16384;
        int   w   = int (wgGet (vi, sb));
        float sum = 0.0f;

        for (int k = 0; k < 4; ++k)
        {
            float g = wgGet (vi, sb + 68 + k);

            if (g > 0.0f)
            {
                int   M  = int (wgGet (vi, sb + 60 + k));
                float ci = wgGet (vi, sb + 64 + k);
                float v  = voices.at (vi).wgd.at (db + k * 4096 + ((w - M) & 4095));
                float yi = ci * v + wgGet (vi, sb + 56 + k);
                wgPut (vi, sb + 56 + k, v - ci * yi);
                float b0 = wgGet (vi, sb + 72 + k);
                float yb = b0 * yi + wgGet (vi, sb + 48 + k);
                wgPut (vi, sb + 48 + k, wgGet (vi, sb + 52 + k) - wgGet (vi, sb + 76 + k) * yb);
                wgPut (vi, sb + 52 + k, -b0 * yi - wgGet (vi, sb + 80 + k) * yb);
                voices.at (vi).wgd.at (db + k * 4096 + (w & 4095)) = g * yb + e * wgGet (vi, sb + 160 + k) * wgGet (vi, sb + 84 + k);
                sum += yb;
            }
        }

        wgPut (vi, sb, float ((w + 1) & 65535));
        return sum;
    }

    float wgDrum (int vi, int o, float e)
    {
        int   sb  = o * 192;
        float sum = 0.0f;

        for (int k = 0; k < 12; ++k)
        {
            float y1 = wgGet (vi, sb + 96 + k);
            float y2 = wgGet (vi, sb + 108 + k);
            float y  = wgGet (vi, sb + 144 + k) * e + wgGet (vi, sb + 120 + k) * y1 - wgGet (vi, sb + 132 + k) * y2;
            wgPut (vi, sb + 108 + k, y1);
            wgPut (vi, sb + 96 + k, y);
            sum += y;
        }

        return sum;
    }

    float wgStep (int vi, int o, float freq)
    {
        int   sb   = o * 192;
        float sr   = float (processor.frequency);
        int   mdl  = clamp (int (wgq (o, 0) + 0.5f), 0, 4);
        float f0   = max (freq, sr / 3800.0f);
        float vel  = clamp (voices.at (vi).velRaw, 0.0f, 1.0f);
        float vw   = wgq (o, 12);
        float vk   = (1.0f - vw) + vw * (0.25f + 1.5f * vel);
        bool  trig = wgGet (vi, sb + 1) > 0.5f;
        int   cnt  = int (wgGet (vi, sb + 2));

        if (trig)
            wgPut (vi, sb + 35, vk);

        if (cnt <= 0 || trig)
        {
            wgUpdate (vi, o, mdl, f0, sr, trig);
            cnt = 8;
        }

        wgPut (vi, sb + 2, float (cnt - 1));

        if (trig)
        {
            wgTrigger (vi, o, mdl, sr, f0, vk);
            wgPut (vi, sb + 1, 0.0f);
        }

        float y = 0.0f;

        if (mdl == 0)
            y = wgKS (vi, o);
        else if (mdl == 1)
            y = wgBow (vi, o);
        else if (mdl == 2)
            y = wgClar (vi, o);
        else if (mdl == 3)
            y = wgBand (vi, o, wgPulse (vi, sb, wgq (o, 5)));
        else
            y = wgDrum (vi, o, wgPulse (vi, sb, wgq (o, 5)));

        y *= wgOut.at (mdl);

        // energy follower (tension modulation) before the extra layers
        float en = wgGet (vi, sb + 3);
        en += (y * y - en) * 0.002f;
        wgPut (vi, sb + 3, en);
        wgPut (vi, sb + 4, max (wgGet (vi, sb + 4), en));

        // snare wires: high-passed noise that rattles with the head
        float sn = wgGet (vi, sb + 34);

        if (mdl == 4 && sn > 0.001f)
        {
            float nz = nextNoise();
            float l1 = wgGet (vi, sb + 12);
            l1 += 0.35f * (nz - l1);
            wgPut (vi, sb + 12, l1);
            float fol = wgGet (vi, sb + 13);
            float ay  = abs (y);
            fol += (ay - fol) * (ay > fol ? 0.05f : 0.0004f);
            wgPut (vi, sb + 13, fol);
            y += sn * (nz - l1) * fol * 3.0f;
        }

        // body resonances
        float bm = wgGet (vi, sb + 32);

        if (bm > 0.001f)
        {
            float ba = wgGet (vi, sb + 36) * y + wgGet (vi, sb + 8);
            wgPut (vi, sb + 8, wgGet (vi, sb + 9) - wgGet (vi, sb + 37) * ba);
            wgPut (vi, sb + 9, -wgGet (vi, sb + 36) * y - wgGet (vi, sb + 38) * ba);
            float bb = wgGet (vi, sb + 39) * y + wgGet (vi, sb + 10);
            wgPut (vi, sb + 10, wgGet (vi, sb + 11) - wgGet (vi, sb + 40) * bb);
            wgPut (vi, sb + 11, -wgGet (vi, sb + 39) * y - wgGet (vi, sb + 41) * bb);
            y += bm * 1.5f * (ba + 0.7f * bb);
        }

        float dr = wgGet (vi, sb + 33);

        if (dr > 0.001f)
        {
            float gd = 1.0f + dr * 6.0f;
            y = float (tanh (y * gd)) / float (tanh (gd));
        }

        // DC blocker
        float x1 = wgGet (vi, sb + 6);
        float y1 = wgGet (vi, sb + 7);
        float yo = y - x1 + 0.995f * y1;
        wgPut (vi, sb + 6, y);
        wgPut (vi, sb + 7, yo);

        return clamp (yo, -2.0f, 2.0f);
    }

'''.replace("@LO@", LO).replace("@HI@", HI)
VOICE = "        float[131072] wgd;    // Waveguide source: delay lines, slot * 16384\n        float[2048]   wgs;    // Waveguide source: state, slot * 192\n"
DECL = "".join('    input event float param%d [[ name: "OSC %d %s", min: %s, max: %s, init: %s%s ]];\n' % (
    L.wg_id(o, p[0]), o + 1, p[2], repr(float(p[4])), repr(float(p[5])), repr(float(p[6])), ", step: 1.0" if p[8] == "sel" else "")
    for o in range(L.OSC_COUNT) for p in K)
HAND = "".join("    event param%d (float v) { wgSet (%d, %d, v); }\n" % (L.wg_id(o, p[0]), o, p[0]) for o in range(L.OSC_COUNT) for p in K)
INIT = "".join("            wgP.at (io * 16 + %d) = %sf;\n" % (p[0], repr(float(p[6]))) for p in K)
s = open(PATCH).read()
def block(tag, body, anchor_re, indent="    "):
    global s
    a, z = "%s// WG-%s-BEGIN\n" % (indent, tag), "%s// WG-%s-END\n" % (indent, tag)
    s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
    m = re.search(anchor_re, s, re.M)
    if not m: raise SystemExit("anchor not found: " + tag)
    s = s[:m.start()] + a + body + z + s[m.start():]
block("DSP", DSP, r"^    // PHYS-DSP-BEGIN")
block("DECL", DECL, r"^    input event float param1600 ")
block("HAND", HAND, r"^    event param1600 ")
block("INIT", INIT, r"^            op\.at \(io \* 64 \+ 11\) = 3\.0f;\n", "            ")
block("VOICE", VOICE, r"^        int     fdlW; ", "        ")
s = re.sub(r'(name: "OSC \d Source", min: 0.0, max: )[2345]\.0', r'\g<1>6.0', s)
def rep(old, new):
    global s
    if new in s: return
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)
rep("                    kickNoteOn (v, o);\n", "                    kickNoteOn (v, o);\n                    wgNoteOn (v, o);\n")
rep("\n                    // ----- filter envelope of the slot -----\n",
    "                    else if (ty == 6)\n                    {\n                        sL = wgStep (i, o, freq);\n                        sR = sL;\n                    }\n\n                    // ----- filter envelope of the slot -----\n")
# the destination limit of the 20 original matrix slots (ids 307.. / 472..) follows N_DST_TOTAL as well (the extended slots are set by build_mod.py)
DMAX = L.N_DST_TOTAL - 1
s = re.sub(r"(mmDstI\.at \(\d+\) = clamp \(int \(v \+ 0\.5f\), 0, )\d+\)", lambda m: m.group(1) + "%d)" % DMAX, s)
s = re.sub(r'(Mod Slot \d+ Dest \(0-)\d+(, see Dest list\)", min: 0\.0, max: )\d+(\.0)', lambda m: m.group(1) + "%d" % DMAX + m.group(2) + "%d" % DMAX + m.group(3), s)
open(PATCH, "w").write(s)
print("ok")
hdr = os.path.join(os.path.dirname(os.path.abspath(PATCH)), "..", "native_ui", "NjoWg.h")
with open(hdr, "w") as f:
    f.write("// generated by tools/osc/build_wg.py: parameter ids and labels of the Waveguide source\n#pragma once\n#include <string_view>\nnamespace njo::wg\n{\n")
    f.write("    constexpr int WG_BASE = %d, WG_STRIDE = %d;\n" % (L.WG_BASE, L.WG_STRIDE))
    f.write("    inline int wgId (int o, int j) { return WG_BASE + WG_STRIDE * o + j; }\n")
    f.write("    inline int key (const char* name)   // parameter index j of a key such as \"wdecay\"\n    {\n")
    for q in K: f.write('        if (std::string_view (name) == "%s") return %d;\n' % (q[1], q[0]))
    f.write("        return 0;\n    }\n")
    f.write("    // labels of the parameters 1..15 for every model (\"\" = the model does not use the parameter)\n    inline const char* label (int model, int j) \n    {\n        static const char* const t[%d][15] = {\n" % len(L.WG_LABELS))
    for row in L.WG_LABELS: f.write("            { " + ", ".join('"%s"' % x for x in row) + " },\n")
    f.write("        };\n        return j < 1 || j > 15 || model < 0 || model > %d ? \"\" : t[model][j - 1];\n    }\n}\n" % (len(L.WG_LABELS) - 1))
