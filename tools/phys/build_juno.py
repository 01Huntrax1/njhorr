#!/usr/bin/env python3
"""Adds the Alpha Juno style DCO source (Source type 4) to patch/Eisenpuls_Synth.cmajor.  Run tools/phys/build_phys.py first (it declares the
parameters, ids PHY_BASE + 32 * slot + 16..25).  Idempotent.  Usage: build_juno.py [patch.cmajor]"""
import os, re, sys
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "patch", "Eisenpuls_Synth.cmajor")

DSP = r'''    // ---------------- Alpha Juno style DCO (tools/phys/build_juno.py) ----------------
    // saw (with an optional capacitor-like curve), pulse with manual / LFO pulse width, sub oscillator (square one octave down), noise;
    // range 16' / 8' / 4', slow analog drift. Edges are band-limited with PolyBLEP. Parameters: phyP slot * 32 + 16 .. 25.
    // state: Voice.wtUPh slot * 7 (phase), slot * 7 + 1 (PWM LFO phase); Voice.phs slot * 176 + 0 drift counter, 1 drift target, 2 drift value, 3 noise low-pass, 4 sub state
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

    float junoStep (int vi, int o, float freq, float pm, float widthM, float depthM, float subM)
    {
        float sr = float (processor.frequency);
        int   pb = o * 32;
        int   sb = o * 176;
        int   ui = o * 7;

        // drift: a new random target every 2048 samples, followed slowly
        float cnt = voices.at (vi).phs.at (sb);

        if (cnt <= 0.0f)
        {
            cnt = 2048.0f;
            voices.at (vi).phs.at (sb + 1) = nextNoise();
        }

        voices.at (vi).phs.at (sb) = cnt - 1.0f;
        float dr = voices.at (vi).phs.at (sb + 2);
        dr += 0.0006f * (voices.at (vi).phs.at (sb + 1) - dr);
        voices.at (vi).phs.at (sb + 2) = dr;

        int   rg = clamp (int (phyP.at (pb + 23) + 0.5f), 0, 2);
        float f  = freq * (rg == 0 ? 0.5f : (rg == 2 ? 2.0f : 1.0f)) * (1.0f + phyP.at (pb + 24) * dr * 0.0046f);
        f = clamp (f, 1.0f, sr * 0.45f);
        float dt = f * float (processor.period);

        // pulse width
        float64 lph = voices.at (vi).wtUPh.at (ui + 1);
        lph += float64 (phyP.at (pb + 20)) * processor.period;
        if (lph >= 1.0) lph -= 1.0;
        voices.at (vi).wtUPh.at (ui + 1) = lph;
        float tri = float (lph < 0.5 ? lph * 4.0 - 1.0 : 3.0 - lph * 4.0);
        float dep = clamp (phyP.at (pb + 19) + depthM * 0.5f, 0.0f, 1.0f);
        float w   = clamp (phyP.at (pb + 18) + widthM * 0.5f + dep * 0.45f * tri, 0.05f, 0.95f);

        float64 ph = voices.at (vi).wtUPh.at (ui);
        float   rp = float (ph);

        if (pm != 0.0f)
        {
            rp = rp + pm;
            rp = rp - float (floor (rp));
        }

        // saw
        float y = 2.0f * rp - 1.0f;
        float cv = phyP.at (pb + 25) * 4.0f;

        if (cv > 0.01f)
            y = 2.0f * (float (exp (cv * rp)) - 1.0f) / (float (exp (cv)) - 1.0f) - 1.0f;

        float saw = y - junoBlep (rp, dt);

        // pulse
        float wp = rp - w;
        if (wp < 0.0f) wp += 1.0f;
        float pul = (rp < w ? 1.0f : -1.0f) + junoBlep (rp, dt) - junoBlep (wp, dt);

        // sub: square one octave below, toggles on every wrap of the main phase
        float st  = voices.at (vi).phs.at (sb + 4);
        float sg  = st > 0.5f ? 1.0f : -1.0f;
        float sub = sg;
        if (rp < dt)             sub += sg * junoBlep (rp, dt);
        else if (rp > 1.0f - dt) sub -= sg * junoBlep (rp, dt);

        // noise (slightly dark)
        float ln = voices.at (vi).phs.at (sb + 3);
        ln += 0.6f * (nextNoise() - ln);
        voices.at (vi).phs.at (sb + 3) = ln;

        ph += float64 (f) * processor.period;

        if (ph >= 1.0)
        {
            ph -= 1.0;
            voices.at (vi).phs.at (sb + 4) = 1.0f - st;
        }

        voices.at (vi).wtUPh.at (ui) = ph;

        float sl = clamp (phyP.at (pb + 21) + subM * 0.5f, 0.0f, 1.0f);
        return (saw * phyP.at (pb + 16) + pul * phyP.at (pb + 17) + sub * sl + ln * phyP.at (pb + 22)) * 0.5f;
    }

'''
s = open(PATCH).read()
a, z = "    // JUNO-DSP-BEGIN\n", "    // JUNO-DSP-END\n"
s = re.sub(re.escape(a) + r".*?" + re.escape(z), "", s, flags=re.S)
m = re.search(r"^    // ---------------- MIDI ----------------", s, re.M)
s = s[:m.start()] + a + DSP + z + s[m.start():]
if "junoStep (i, o, freq" not in s:
    old = "                    else if (ty == 3)\n                    {\n                        sL = phyStep ("
    assert old in s
    s = s.replace(old, "                    else if (ty == 4)\n                    {\n                        sL = junoStep (i, o, freq, pm, vmod.at (dB + 3), vmod.at (dB + 4), vmod.at (dB + 5));\n                        sR = sL;\n                    }\n" + old, 1)
open(PATCH, "w").write(s)
print("ok")
