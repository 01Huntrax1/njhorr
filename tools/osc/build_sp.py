#!/usr/bin/env python3
"""Adds the Spectral source (Source type 11) to patch/Eisenpuls_Synth.cmajor.  Two modes:
 * Resynth: the spectral envelope of the sample memory of the slot (load a sample like for the Sampler) is analysed with a 2048-point FFT, smoothed (4 blur levels on a
   1/24 octave grid) and imposed on a harmonic series (up to 64 phasor partials, like the Additive source) at the pitch of the key: the sound of the sample at any pitch.
   Position / Position B pick two frames, Morph blends them, Scan moves through the sample, Shift moves the envelope (formant shift), Blur smears it.
 * Spectrum: no sample needed: two formant peaks (Position / Position B, Morph blends, Blur = width).
Both: Tilt, Harmonics, Odd / Even, Comb, Contrast, Jitter, Spread (inharmonic), Width, Vel > Pos.
Parameters: ids SP_BASE + 16 * slot + j (layout.py SP), mod destinations 1116 + 16 * slot + j.  State per voice and slot: Voice.sps (slot * 512), laid out like the Additive source.
Analysis cache: 8 frames per slot (spEnv, direct mapped, spKey); a sample load clears it.  Run after build_dk.py.  Idempotent.  Usage: build_sp.py [patch.cmajor]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L, srcgen
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
LO, HI = srcgen.table(L.SP, 0)
DSP = r'''    // ---------------- Spectral source (tools/osc/build_sp.py) ----------------
    float[96]    spP;        // slot * 16 + parameter
    const float[16] spLo = (@LO@);
    const float[16] spHi = (@HI@);
    float[49152] spEnv;      // analysis cache: (slot * 8 + entry) * 1024 + level * 256 + grid point (magnitude)
    int[48]      spKey;      // frame number + 1 of each cache entry (0 = empty)
    float[2048]  spRe;       // FFT scratch
    float[2048]  spIm;
    float[1024]  spCos;
    float[1024]  spSin;
    float[260]   spCum;
    bool         spTwOk = false;

    void spSet (int o, int j, float v)
    {
        spP.at (o * 16 + j) = v;
    }

    float spq (int o, int j)
    {
        float v = spP.at (o * 16 + j);
        float m = vmod.at (1116 + 16 * o + j);

        if (m != 0.0f)
        {
            v += m * 0.5f * (spHi.at (j) - spLo.at (j));
            v = clamp (v, spLo.at (j), spHi.at (j));
        }

        return v;
    }

    void spInvalidate (int o)
    {
        for (int e = 0; e < 8; ++e)
            spKey.at (o * 8 + e) = 0;
    }

    void spNoteOn (int vi, int o)
    {
        if (int (op.at (o * 64) + 0.5f) != 11)
            return;

        for (int i = 0; i < 512; ++i)
            voices.at (vi).sps.at (o * 512 + i) = 0.0f;

        for (int n = 0; n < 64; ++n)
            voices.at (vi).sps.at (o * 512 + 64 + n) = 1.0f;
    }

    // in place radix-2 FFT of spRe / spIm (2048 points)
    void spFft()
    {
        if (! spTwOk)
        {
            for (int i = 0; i < 1024; ++i)
            {
                spCos.at (i) = float (cos (6.283185307179586 * float64 (i) / 2048.0));
                spSin.at (i) = float (-sin (6.283185307179586 * float64 (i) / 2048.0));
            }

            spTwOk = true;
        }

        int j = 0;

        for (int i = 0; i < 2047; ++i)
        {
            if (i < j)
            {
                float tr = spRe.at (i);
                float ti = spIm.at (i);
                spRe.at (i) = spRe.at (j);
                spIm.at (i) = spIm.at (j);
                spRe.at (j) = tr;
                spIm.at (j) = ti;
            }

            int k = 1024;

            while (k <= j)
            {
                j -= k;
                k = k / 2;
            }

            j += k;
        }

        for (int len = 2; len <= 2048; len = len * 2)
        {
            int half = len / 2;
            int step = 2048 / len;

            for (int i = 0; i < 2048; i += len)
            {
                for (int k = 0; k < half; ++k)
                {
                    float wr = spCos.at (k * step);
                    float wi = spSin.at (k * step);
                    int   a  = i + k;
                    int   b  = a + half;
                    float xr = spRe.at (b) * wr - spIm.at (b) * wi;
                    float xi = spRe.at (b) * wi + spIm.at (b) * wr;
                    spRe.at (b) = spRe.at (a) - xr;
                    spIm.at (b) = spIm.at (a) - xi;
                    spRe.at (a) = spRe.at (a) + xr;
                    spIm.at (a) = spIm.at (a) + xi;
                }
            }
        }
    }

    // analyses frame q (1024 samples apart) of the sample of slot o into cache entry e and returns the base offset of the entry
    int spFrame (int o, int q)
    {
        int e    = o * 8 + ((q * 5) & 7);
        int base = e * 1024;

        if (spKey.at (e) == q + 1)
            return base;

        int   len   = smpLen.at (o);
        int   start = clamp (q * 1024, 0, max (len - 2048, 0));
        float sr    = float (processor.frequency);
        int   sb    = o * 96000;

        for (int i = 0; i < 2048; ++i)
        {
            int   p = start + i;
            float w = 0.5f - 0.5f * float (cos (6.283185307179586 * float64 (i) / 2048.0));
            spRe.at (i) = p < len ? smpBuf.at (sb + p) * w : 0.0f;
            spIm.at (i) = 0.0f;
        }

        spFft();

        for (int k = 0; k < 1024; ++k)
            spRe.at (k) = spRe.at (k) * spRe.at (k) + spIm.at (k) * spIm.at (k);

        // level 0: band power on a 1/24 octave grid from 20 Hz (240 points)
        for (int i = 0; i < 240; ++i)
        {
            float f   = 20.0f * float (pow (2.0f, float (i) / 24.0f));
            float bin = f * 2048.0f / sr;
            float hw  = max (bin * 0.0145f, 0.5f);
            int   lo  = clamp (int (bin - hw), 0, 1023);
            int   hi  = clamp (int (bin + hw) + 1, lo, 1023);
            float s   = 0.0f;

            for (int k = lo; k <= hi; ++k)
                s += spRe.at (k);

            s = s / float (hi - lo + 1) + 0.0000000001f;
            spIm.at (i) = s;
        }

        spCum.at (0) = 0.0f;

        for (int i = 0; i < 240; ++i)
            spCum.at (i + 1) = spCum.at (i) + spIm.at (i);

        for (int lv = 0; lv < 4; ++lv)
        {
            int h = lv == 0 ? 0 : (lv == 1 ? 4 : (lv == 2 ? 12 : 36));

            for (int i = 0; i < 256; ++i)
            {
                int   ii = min (i, 239);
                int   a  = max (ii - h, 0);
                int   b  = min (ii + h, 239);
                float m  = (spCum.at (b + 1) - spCum.at (a)) / float (b - a + 1);
                spEnv.at (base + lv * 256 + i) = sqrt (max (m, 0.0f));
            }
        }

        spKey.at (e) = q + 1;
        return base;
    }

    // magnitude of a frame at grid position gi (1/24 octave steps above 20 Hz) and blur level bl (0..3)
    float spEnvAt (int base, float gi, float bl)
    {
        int   i0 = clamp (int (gi), 0, 238);
        float fi = clamp (gi - float (i0), 0.0f, 1.0f);
        int   l0 = clamp (int (bl), 0, 2);
        float fl = clamp (bl - float (l0), 0.0f, 1.0f);
        int   b0 = base + l0 * 256 + i0;
        float a  = spEnv.at (b0) * (1.0f - fi) + spEnv.at (b0 + 1) * fi;
        float b  = spEnv.at (b0 + 256) * (1.0f - fi) + spEnv.at (b0 + 257) * fi;
        return a * (1.0f - fl) + b * fl;
    }

    void spUpdate (int vi, int o, float f0, float sr)
    {
        int   sb   = o * 512;
        int   cnt  = clamp (int (4.0f * float (pow (16.0f, spq (o, 8))) + 0.5f), 1, 64);
        bool  reS  = spq (o, 0) < 0.5f;
        float p1   = spq (o, 1);
        float p2   = spq (o, 2);
        float mo   = spq (o, 3);
        float scan = spq (o, 4);
        float blur = spq (o, 5);
        float shf  = spq (o, 6);
        float tilt = spq (o, 7) * 1.2f;
        float odd  = spq (o, 9);
        float comb = spq (o, 10);
        float cont = spq (o, 11);
        float jit  = spq (o, 12);
        float inh  = spq (o, 13) * spq (o, 13) * 0.02f;
        float vel  = clamp (voices.at (vi).velRaw, 0.0f, 1.0f);
        float t    = voices.at (vi).sps.at (sb + 385);
        int   len  = smpLen.at (o);
        bool  have = reS && smpHas.at (o) && len > 8;
        float bl   = blur * 3.0f;
        float sh   = float (pow (2.0f, shf));
        int   cp   = 2 + clamp (int (comb * 6.9f), 0, 6);
        float ss   = 0.0f;
        float amax = 0.0f;
        int   hi   = 0;
        int   qa0  = 0;
        int   qa1  = 0;
        int   qb0  = 0;
        int   qb1  = 0;
        float fa   = 0.0f;
        float fb   = 0.0f;
        int   baseA0 = 0;
        int   baseA1 = 0;
        int   baseB0 = 0;
        int   baseB1 = 0;

        if (have)
        {
            float adv = scan * t * sr / float (len);
            float vp  = vel * spq (o, 15);
            float pa  = p1 + vp + adv;
            float pb  = p2 + vp + adv;

            if (pa > 1.0f || pa < 0.0f)
                pa = pa - float (floor (pa));

            if (pb > 1.0f || pb < 0.0f)
                pb = pb - float (floor (pb));

            int   mq  = max ((len - 2048) / 1024, 0);
            float qa  = pa * float (max (len - 2048, 0)) / 1024.0f;
            float qb  = pb * float (max (len - 2048, 0)) / 1024.0f;
            qa0 = clamp (int (qa), 0, mq);
            qa1 = min (qa0 + 1, mq);
            fa  = qa - float (int (qa));
            qb0 = clamp (int (qb), 0, mq);
            qb1 = min (qb0 + 1, mq);
            fb  = qb - float (int (qb));
            baseA0 = spFrame (o, qa0);
            baseA1 = spFrame (o, qa1);

            if (mo > 0.001f)
            {
                baseB0 = spFrame (o, qb0);
                baseB1 = spFrame (o, qb1);
            }
        }

        // pass 1: raw amplitude of every partial
        for (int n = 1; n <= 64; ++n)
        {
            float tg = 0.0f;
            float fn = float (n) * f0 * sqrt (1.0f + inh * float (n * n));

            if (n <= cnt && fn < 0.45f * sr && (have || ! reS))
            {
                float fe = float (n) * f0 / sh;
                float a  = 0.0f;

                if (have)
                {
                    float gi = float (log (max (fe, 1.0f) / 20.0f)) * 1.442695f * 24.0f;

                    if (gi >= 0.0f && gi < 239.0f)
                    {
                        float eA = spEnvAt (baseA0, gi, bl) * (1.0f - fa) + spEnvAt (baseA1, gi, bl) * fa;
                        a = eA;

                        if (mo > 0.001f)
                        {
                            float eB = spEnvAt (baseB0, gi, bl) * (1.0f - fb) + spEnvAt (baseB1, gi, bl) * fb;
                            a = eA * (1.0f - mo) + eB * mo;
                        }
                    }
                }
                else
                {
                    float c1 = 100.0f * float (pow (2.0f, p1 * 6.6f));
                    float c2 = 100.0f * float (pow (2.0f, p2 * 6.6f));
                    float sg = 0.12f + blur * 0.9f;
                    float l  = float (log (max (fe, 1.0f))) * 1.442695f;
                    float d1 = (l - float (log (c1)) * 1.442695f) / sg;
                    float d2 = (l - float (log (c2)) * 1.442695f) / sg;
                    a = (1.0f - mo) * float (exp (-0.5f * d1 * d1)) + mo * float (exp (-0.5f * d2 * d2)) + 0.03f / sqrt (float (n));
                    a *= 1.0f / sqrt (float (n));
                }

                a *= float (pow (float (n), tilt));
                a *= (n - (n / 2) * 2) == 1 ? 1.0f + odd : 1.0f - odd;

                if (comb > 0.0f && (n - (n / cp) * cp) == 0)
                    a *= max (1.0f - comb * 4.0f, 0.0f);

                if (jit > 0.0f)
                    a *= max (1.0f + 0.6f * jit * float (sin (6.2831853f * (0.7f + 0.13f * float (n)) * t + float (n) * 2.1f)), 0.0f);

                tg = max (a, 0.0f);
                amax = max (amax, tg);
            }

            voices.at (vi).sps.at (sb + 320 + n - 1) = tg;
        }

        // pass 2: contrast, phasor increments, normalisation
        for (int n = 1; n <= 64; ++n)
        {
            float tg = voices.at (vi).sps.at (sb + 320 + n - 1);
            float fn = float (n) * f0 * sqrt (1.0f + inh * float (n * n));

            if (tg > 0.0f && cont > 0.0f && amax > 0.0f)
                tg = amax * float (pow (tg / amax, 1.0f + cont * 2.5f));

            voices.at (vi).sps.at (sb + 320 + n - 1) = tg;
            ss += tg * tg;

            if (tg > 0.0f || voices.at (vi).sps.at (sb + 256 + n - 1) > 0.001f)
                hi = n;

            float w = 6.2831853f * min (fn, 0.49f * sr) / sr;
            voices.at (vi).sps.at (sb + 128 + n - 1) = float (sin (w));
            voices.at (vi).sps.at (sb + 192 + n - 1) = float (cos (w));
        }

        voices.at (vi).sps.at (sb + 386) = float (hi);
        voices.at (vi).sps.at (sb + 387) = 0.45f / sqrt (ss * 0.5f + 0.000001f);
        voices.at (vi).sps.at (sb + 385) = t + 32.0f / sr;
    }

    float<2> spStep (int vi, int o, float freq)
    {
        float sr  = float (processor.frequency);
        int   sb  = o * 512;
        int   cnt = int (voices.at (vi).sps.at (sb + 384));

        if (cnt <= 0)
        {
            spUpdate (vi, o, freq, sr);
            cnt = 32;

            for (int n = 0; n < 64; ++n)
            {
                float s = voices.at (vi).sps.at (sb + n);
                float c = voices.at (vi).sps.at (sb + 64 + n);
                float r = 1.0f / sqrt (s * s + c * c + 0.0000001f);
                voices.at (vi).sps.at (sb + n) = s * r;
                voices.at (vi).sps.at (sb + 64 + n) = c * r;
            }
        }

        voices.at (vi).sps.at (sb + 384) = float (cnt - 1);

        int   hi   = int (voices.at (vi).sps.at (sb + 386));
        float sOdd = 0.0f;
        float sEvn = 0.0f;

        for (int n = 0; n < hi; ++n)
        {
            float s  = voices.at (vi).sps.at (sb + n);
            float c  = voices.at (vi).sps.at (sb + 64 + n);
            float ds = voices.at (vi).sps.at (sb + 128 + n);
            float dc = voices.at (vi).sps.at (sb + 192 + n);
            float am = voices.at (vi).sps.at (sb + 256 + n);
            float ns = s * dc + c * ds;
            float nc = c * dc - s * ds;
            am += (voices.at (vi).sps.at (sb + 320 + n) - am) * 0.04f;
            voices.at (vi).sps.at (sb + n) = ns;
            voices.at (vi).sps.at (sb + 64 + n) = nc;
            voices.at (vi).sps.at (sb + 256 + n) = am;

            if ((n - (n / 2) * 2) == 0)
                sOdd += ns * am;
            else
                sEvn += ns * am;
        }

        float g  = voices.at (vi).sps.at (sb + 387);
        float wd = (spq (o, 14) - 0.5f) * 2.0f;
        float yL = g * (sOdd * (1.0f + wd) + sEvn * (1.0f - wd)) * 0.5f;
        float yR = g * (sOdd * (1.0f - wd) + sEvn * (1.0f + wd)) * 0.5f;

        return float<2> (clamp (yL, -2.0f, 2.0f), clamp (yR, -2.0f, 2.0f));
    }

'''.replace("@LO@", LO).replace("@HI@", HI)
STEP = '''                    else if (ty == 11)
                    {
                        float<2> sw = spStep (i, o, freq);
                        sL = sw[0];
                        sR = sw[1];
                        stereo = true;
                    }
'''
EXTRAS = [("            smpLen.at (o) = clamp (c.total, 1, 96000);\n            smpHas.at (o) = true;\n",
           "            smpLen.at (o) = clamp (c.total, 1, 96000);\n            smpHas.at (o) = true;\n            spInvalidate (o);   // SP: the spectral analysis cache\n")]
srcgen.install(PATCH, "                    dkNoteOn (v, o);\n", "SP", L.SP, L.sp_id, L.SP_DST_BASE, DSP,
               "        float[4096]   sps;    // Spectral source: partials, slot * 512\n", "                    spNoteOn (v, o);\n", STEP, "spSet", "spP",
               "tools/osc/build_sp.py", "NjoSp.h", "sp", L.SP_BASE, L.SP_STRIDE, EXTRAS)
print("ok")
