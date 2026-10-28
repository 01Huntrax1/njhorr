#!/usr/bin/env python3
"""Adds the Alpha Juno style DCO source (Source type 4) to patch/Eisenpuls_Synth.cmajor.  Run tools/phys/build_phys.py first (it declares the
parameters, ids PHY_BASE + 32 * slot + 16..25).  Idempotent.  Usage: build_juno.py [patch.cmajor]"""
import os, re, sys
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "patch", "Eisenpuls_Synth.cmajor")

DSP = r'''    // ---------------- Roland Alpha Juno style DCO (tools/phys/build_juno.py) ----------------
    // One DCO per voice like the Alpha Juno: a pulse wave (Pulse 1-3) and a saw wave (Saw 1-5) that are summed, a sub oscillator (Sub 1-6) and noise;
    // pulse width modulation by the LFO, the amp envelope or by hand, vibrato from the same LFO, range 16' / 8' / 4', slow analog drift. The variants are
    // approximations (the exact Alpha Juno shapes are not documented): Pulse 1 variable width, 2 = 25 %, 3 = 12.5 %; Saw 1 ramp, 2 PWM saw (ramp over the
    // pulse width, then low), 3 saw + saw an octave up, 4 saw + third harmonic saw, 5 soft saw; Sub 1 square -1 oct, 2 pulse 25 % -1 oct, 3 square -2 oct,
    // 4 pulse 25 % -2 oct, 5 squares -1 and -2 oct, 6 triangle -1 oct. Edges are band-limited with PolyBLEP. Parameters: phyP slot * 32 + 16 .. 30.
    // state: see junoStep (Voice.wtUPh phases per unison voice, Voice.phs 1842.. for the LFO phase, noise low-pass and sub counters)
    float junoBlep (float t, float dt)
    {
        if (t < dt)
        {
            float x = t / dt;
            return x + x - x * x - 1.0f;
        }

        if (t > 1.0f - dt)
        {
            float x = (t - 1.0f) / dt;
            return x * x + x + x + 1.0f;
        }

        return 0.0f;
    }

    // band-limited pulse of width w from the phase q (0..1) advancing dt per sample
    float junoPulse (float q, float w, float dt)
    {
        float wp = q - w;
        if (wp < 0.0f) wp += 1.0f;
        return (q < w ? 1.0f : -1.0f) + junoBlep (q, dt) - junoBlep (wp, dt);
    }

    float junoRamp (float q, float dt)
    {
        return 2.0f * q - 1.0f - junoBlep (q, dt);
    }

    // Unison: the voices of Unison Voices / Detune / Blend / Width / Curve (same parameters as the wavetable source) each run a complete DCO; the LFO, the pulse
    // width and the noise are shared. Every voice has its own analog drift (Voice.phs, see uniDriftRaw). Returns the stereo sum.
    // state: Voice.wtUPh slot * 7 + j (phase), Voice.phs 1842 + slot (LFO phase), 1848 + slot (noise low-pass), 1854 + slot * 7 + j (sub counter 0..3)
    float<2> junoStep (int vi, int o, float freq, float pm)
    {
        float sr = float (processor.frequency);
        int   pb = o * 32;
        int   ui = o * 7;
        int   n  = uniCnt.at (o);

        // the LFO (triangle) drives the pulse width and the vibrato
        float64 lph = float64 (voices.at (vi).phs.at (1842 + o));
        lph += float64 (phq (o, pb, 20)) * processor.period;
        if (lph >= 1.0) lph -= 1.0;
        voices.at (vi).phs.at (1842 + o) = float (lph);
        float tri = float (lph < 0.5 ? lph * 4.0 - 1.0 : 3.0 - lph * 4.0);

        int   rg = clamp (int (phq (o, pb, 23) + 0.5f), 0, 2);
        float fb = freq * (rg == 0 ? 0.5f : (rg == 2 ? 2.0f : 1.0f)) * (1.0f + phq (o, pb, 30) * 0.0293f * tri);
        float dA = phq (o, pb, 24) * 0.0046f + opv (o, 28) * 0.007f;

        // pulse width: manual, LFO or amp envelope
        int   src = clamp (int (phq (o, pb, 29) + 0.5f), 0, 2);
        float dep = clamp (phq (o, pb, 19), 0.0f, 1.0f);
        float mod = src == 0 ? tri : (src == 1 ? voices.at (vi).env * 2.0f - 1.0f : 0.0f);
        float w   = clamp (phq (o, pb, 18) + dep * 0.45f * mod, 0.05f, 0.95f);

        float sawL = phq (o, pb, 16);
        float pulL = phq (o, pb, 17);
        float sl   = clamp (phq (o, pb, 21), 0.0f, 1.0f);
        int   stp  = clamp (int (phq (o, pb, 27) + 0.5f), 0, 4);
        int   ptp  = clamp (int (phq (o, pb, 26) + 0.5f), 0, 2);
        int   btp  = clamp (int (phq (o, pb, 28) + 0.5f), 0, 5);
        float cv   = phq (o, pb, 25) * 4.0f;
        float sumL = 0.0f;
        float sumR = 0.0f;

        for (int j = 0; j < n; ++j)
        {
            float dr = uniDriftRaw (vi, o, j, dA > 0.0f);
            float f  = clamp (fb * uniRatio.at (ui + j) * (1.0f + dA * dr), 1.0f, sr * 0.45f);
            float dt = f * float (processor.period);

            float64 ph = voices.at (vi).wtUPh.at (ui + j);
            float   rp = float (ph);

            if (pm != 0.0f)
            {
                rp = rp + pm;
                rp = rp - float (floor (rp));
            }

            // saw wave
            float saw = 0.0f;

            if (sawL > 0.0f)
            {
                if (stp == 0 || stp == 4)
                {
                    float y = 2.0f * rp - 1.0f;

                    if (cv > 0.01f)
                        y = 2.0f * (float (exp (cv * rp)) - 1.0f) / (float (exp (cv)) - 1.0f) - 1.0f;

                    saw = y - junoBlep (rp, dt);

                    if (stp == 4)
                        saw = float (tanh (1.7f * saw)) * 1.12f;
                }
                else if (stp == 1)
                {
                    // PWM saw: the ramp runs over the pulse width and drops to the bottom, DC removed
                    float q  = rp < w ? rp / w : 1.0f;
                    float wp = rp - w;
                    if (wp < 0.0f) wp += 1.0f;
                    saw = (rp < w ? 2.0f * q - 1.0f : -1.0f) - 2.0f * junoBlep (wp, dt) * 0.5f + (1.0f - w) - 0.0f;
                    saw = saw * 0.9f;
                }
                else if (stp == 2)
                {
                    float q2 = rp * 2.0f;
                    q2 = q2 - float (floor (q2));
                    saw = 0.75f * junoRamp (rp, dt) + 0.25f * junoRamp (q2, dt * 2.0f);
                }
                else
                {
                    float q3 = rp * 3.0f;
                    q3 = q3 - float (floor (q3));
                    saw = 0.7f * junoRamp (rp, dt) + 0.3f * junoRamp (q3, dt * 3.0f);
                }
            }

            // pulse wave
            float pul = 0.0f;

            if (pulL > 0.0f)
                pul = junoPulse (rp, ptp == 0 ? w : (ptp == 1 ? 0.25f : 0.125f), dt);

            // sub oscillator
            float s4  = voices.at (vi).phs.at (1854 + ui + j);
            float sub = 0.0f;

            if (sl > 0.0f)
            {
                float st = s4 - 2.0f * float (floor (s4 * 0.5f));
                float q2 = (rp + st) * 0.5f;
                float q4 = (rp + s4) * 0.25f;

                if (btp == 0)      sub = junoPulse (q2, 0.5f, dt * 0.5f);
                else if (btp == 1) sub = junoPulse (q2, 0.25f, dt * 0.5f);
                else if (btp == 2) sub = junoPulse (q4, 0.5f, dt * 0.25f);
                else if (btp == 3) sub = junoPulse (q4, 0.25f, dt * 0.25f);
                else if (btp == 4) sub = 0.5f * (junoPulse (q2, 0.5f, dt * 0.5f) + junoPulse (q4, 0.5f, dt * 0.25f));
                else               sub = q2 < 0.5f ? 4.0f * q2 - 1.0f : 3.0f - 4.0f * q2;
            }

            ph += float64 (f) * processor.period;

            if (ph >= 1.0)
            {
                ph -= 1.0;
                s4 += 1.0f;
                if (s4 > 3.5f) s4 = 0.0f;
                voices.at (vi).phs.at (1854 + ui + j) = s4;
            }

            voices.at (vi).wtUPh.at (ui + j) = ph;

            float v = (saw * sawL + pul * pulL + sub * sl) * 0.5f;
            sumL += v * uniGL.at (ui + j);
            sumR += v * uniGR.at (ui + j);
        }

        // noise (slightly dark), shared by the voices and centred
        float ln = voices.at (vi).phs.at (1848 + o);
        ln += 0.6f * (nextNoise() - ln);
        voices.at (vi).phs.at (1848 + o) = ln;
        float nz = ln * phq (o, pb, 22) * 0.5f;

        return float<2> (sumL + nz, sumR + nz);
    }

'''
s = open(PATCH).read()
a, z = "    // JUNO-DSP-BEGIN\n", "    // JUNO-DSP-END\n"
s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
m = re.search(r"^    // ---------------- MIDI ----------------", s, re.M)
s = s[:m.start()] + a + DSP + z + s[m.start():]
s = s.replace("junoStep (i, o, freq, pm, vmod.at (dB + 3), vmod.at (dB + 4), vmod.at (dB + 5));", "junoStep (i, o, freq, pm);")
if "junoStep (i, o, freq" not in s:
    old = "                    else if (ty == 3)\n                    {\n                        sL = phyStep ("
    assert old in s
    s = s.replace(old, "                    else if (ty == 4)\n                    {\n                        float<2> jw = junoStep (i, o, freq, pm);\n                        sL = jw[0];\n                        sR = jw[1];\n                        stereo = true;\n                    }\n" + old, 1)
open(PATCH, "w").write(s)
print("ok")
