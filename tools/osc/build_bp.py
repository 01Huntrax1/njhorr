#!/usr/bin/env python3
"""Adds the Bagpipe source (Source type 13) to patch/Eisenpuls_Synth.cmajor.  Own implementation after the design that the manual of Quilcom SIM-BP describes
(a spiky reed pulse fed into a tapped waveguide, fixed comb colouration, three fixed-pitch drones with a strike-in, scale tunings, vibrato and blow droop); no code or data of it is used.
 - pipe (chanter and each drone): a delay loop tuned with the exact phase delay of its low-pass (linear interpolated read, so the pitch can glide without clicks); the reed pulse
   (9 shapes, driven by a phase accumulator at the pipe's pitch, with random pitch / amplitude fluctuation) is added to the line at the TAP (Coupling); feedback (Bore) and air noise
   enter at the input.  Single reed = output from the tap, double reed = from the end of the loop; Straight keeps the odd harmonics only (half-period difference).
 - Colouration: feed-forward comb with a fixed delay (100 Hz .. 8 kHz) on the chanter.
 - Drones: up to 3 pipes (chord table) relative to the Key; strike-in = they start flat and settle with an exponential in the time set by Strike-In; slow drift on 2 and 3 (Fluct.).
 - Scale: Equal / Just / Highland (just ratios with the flat seventh 7/4) as cents per semitone above the Key.  Vibrato: a clipped sine that only lowers the pitch (up to the note);
   Blow: a bump every 4 seconds that drops the pitch.
Parameters: ids BP_BASE + 16 * slot + j (layout.py BP), mod destinations 1488 + 16 * slot + j.  State per voice and slot: Voice.bps (slot * 192), lines Voice.bpd (slot * 18432).
Run after build_sf.py.  Idempotent.  Usage: build_bp.py [patch.cmajor]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L, srcgen
PATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "patch", "Eisenpuls_Synth.cmajor")
LO, HI = srcgen.table(L.BP, 0)
DSP = r'''    // ---------------- Bagpipe source (tools/osc/build_bp.py) ----------------
    // state per voice and slot (Voice.bps, slot * 192): 0 trigger, 1 time (samples), 2 control counter, 3.. targets (3 chanter Hz, 4..6 drones Hz), 7 vibrato phase, 8 blow phase,
    // 9..12 DC blockers (L x, L y, R x, R y), 13 comb write position; pipe p (0 chanter, 1..3 drones) at 20 + 20 * p: 0 write, 1 loop length, 2 (unused), 3 loop gain, 4 damping,
    // 5 low-pass state, 6 (unused), 7 reed phase, 8 current Hz, 9 noise low-pass, 10 amplitude, 11 DC x, 12 DC y
    // lines (Voice.bpd, slot * 18432): chanter 0..4095, comb 4096..5119, drone d 5120 + 4096 * d
    float[96] bpP;        // slot * 16 + parameter
    const float[16] bpLo = (@LO@);
    const float[16] bpHi = (@HI@);
    const float[12] bpJust = (0.0f, 11.7f, 3.9f, 15.6f, -13.7f, -2.0f, -9.8f, 2.0f, 13.7f, -15.6f, 17.6f, -11.7f);      // cents against equal temperament above the key (just intonation)
    const float[12] bpHigh = (0.0f, 0.0f, 3.9f, 0.0f, -13.7f, -2.0f, 0.0f, 2.0f, 0.0f, -15.6f, -31.2f, 0.0f);            // Highland scale: 9:8, 5:4, 4:3, 3:2, 5:3 and the flat seventh 7:4
    const float[15] bpChord = (0.0f, 0.0f, 0.0f,  0.0f, 12.0f, 12.0f,  0.0f, 12.0f, 19.0f,  0.0f, 7.0f, 12.0f,  0.0f, 12.0f, 15.0f);   // semitones above the key, 3 drones per chord

    void bpSet (int o, int j, float v)
    {
        bpP.at (o * 16 + j) = v;
    }

    float bpq (int o, int j)
    {
        float v = bpP.at (o * 16 + j);
        float m = vmod.at (1488 + 16 * o + j);

        if (m != 0.0f)
        {
            v += m * 0.5f * (bpHi.at (j) - bpLo.at (j));
            v = clamp (v, bpLo.at (j), bpHi.at (j));
        }

        return v;
    }

    float bpGet (int vi, int i)
    {
        return voices.at (vi).bps.at (i);
    }

    void bpPut (int vi, int i, float v)
    {
        voices.at (vi).bps.at (i) = v;
    }

    void bpNoteOn (int vi, int o)
    {
        if (int (op.at (o * 64) + 0.5f) != 13)
            return;

        for (int i = 0; i < 192; ++i)
            voices.at (vi).bps.at (o * 192 + i) = 0.0f;

        for (int i = 0; i < 18432; ++i)
            voices.at (vi).bpd.at (o * 18432 + i) = 0.0f;

        voices.at (vi).bps.at (o * 192) = 1.0f;
    }

    // the nine reed pulses (peak about 1, DC is removed later)
    float bpReed (int sh, float ph)
    {
        float tp = 6.2831853f;

        if (sh == 0)  return ph < 0.12f ? 0.5f - 0.5f * float (cos (tp * ph / 0.12f)) : 0.0f;
        if (sh == 1)  return ph < 0.3f ? 0.5f - 0.5f * float (cos (tp * ph / 0.3f)) : 0.0f;
        if (sh == 2)  return float (exp (-6.0f * ph));
        if (sh == 3)  return float (exp (-14.0f * ph));
        if (sh == 4)  return ph < 0.35f ? float (sin (3.1415927f * ph / 0.35f)) : 0.0f;
        if (sh == 5)  return ph < 0.2f ? ph / 0.2f : (ph < 0.4f ? (0.4f - ph) / 0.2f : 0.0f);
        if (sh == 6)  return (ph < 0.1f ? 0.5f - 0.5f * float (cos (tp * ph / 0.1f)) : 0.0f) + (ph >= 0.5f && ph < 0.6f ? 0.6f * (0.5f - 0.5f * float (cos (tp * (ph - 0.5f) / 0.1f))) : 0.0f);
        if (sh == 7)  return (ph < 0.08f ? 1.0f - ph / 0.08f : 0.0f) + 0.35f * (ph < 0.5f ? 1.0f - 2.0f * ph : 0.0f);
        float s = float (sin (tp * ph));
        return s > 0.0f ? s * s * s : 0.0f;
    }

    // one pipe: reed pulse -> tapped loop.  f = pitch in Hz, upd = recompute the loop (every 16 samples).  Returns the tapped output (odd filter applied as set by Bore Shape)
    float bpPipe (int vi, int o, int p, float f, bool upd, float amp)
    {
        int   sb   = o * 192;
        int   pb   = sb + 20 + 20 * p;
        int   db   = o * 18432 + (p == 0 ? 0 : 5120 + 4096 * (p - 1));
        float sr   = float (processor.frequency);
        float tp   = 6.2831853f;
        float bore = bpq (o, 5);
        float gT   = 0.93f + 0.065f * bore;

        if (upd)
        {
            float a0   = 0.1f + 0.4f * bore;
            float w0   = tp * f / sr;
            float rest = clamp (sr / f - wgLpDelay (a0, w0), 2.0f, 2600.0f);
            bpPut (vi, pb + 1, rest);
            bpPut (vi, pb + 3, min (gT / wgLpGain (a0, w0), 0.99995f));
            bpPut (vi, pb + 4, a0);
        }

        float M   = bpGet (vi, pb + 1);
        float g   = bpGet (vi, pb + 3);
        float a   = bpGet (vi, pb + 4);
        int   w   = int (bpGet (vi, pb));
        int   li  = int (floor (M));
        float fr  = M - float (li);
        float fl  = bpq (o, 6);
        float nz  = nextNoise();
        float nlp = bpGet (vi, pb + 9);
        nlp += 0.002f * (nz - nlp);
        bpPut (vi, pb + 9, nlp);

        // reed pulse at the (slightly unsteady) pitch
        float ph = bpGet (vi, pb + 7) + f * (1.0f + fl * 0.6f * nlp) / sr;
        ph -= floor (ph);
        bpPut (vi, pb + 7, ph);
        float reed = bpReed (int (bpq (o, 1) + 0.5f), ph) * (1.0f + fl * 3.0f * nlp) * amp;

        // loop: read the end of the line (linear interpolation), low-pass, feedback
        float l0  = voices.at (vi).bpd.at (db + ((w - li) & 4095));
        float l1  = voices.at (vi).bpd.at (db + ((w - li - 1) & 4095));
        float v   = l0 + (l1 - l0) * fr;
        float lp  = (1.0f - a) * v + a * bpGet (vi, pb + 5);
        bpPut (vi, pb + 5, lp);
        float air = bpq (o, 7) * 0.12f * nz;
        voices.at (vi).bpd.at (db + (w & 4095)) = clamp (lp * g + air * (1.0f - gT), -4.0f, 4.0f);

        // the reed excites the line at the tap
        int Mt = clamp (int (bpq (o, 4) * M) + 1, 1, max (li - 1, 1));
        float ex = (1.0f - gT) * 0.9f + 0.02f;
        int ti = db + ((w - Mt) & 4095);
        voices.at (vi).bpd.at (ti) = voices.at (vi).bpd.at (ti) + reed * ex;

        float tap = voices.at (vi).bpd.at (ti);
        float dbl = bpq (o, 2);
        float cn  = bpq (o, 3);
        float y   = (1.0f - dbl) * tap + dbl * v;

        if (cn > 0.001f)
        {
            int   mh   = int (M * 0.5f);
            float tapO = 0.7f * (tap - voices.at (vi).bpd.at (db + ((w - Mt - mh) & 4095)));
            float endO = 0.7f * (v - voices.at (vi).bpd.at (db + ((w - li - mh) & 4095)));
            y = (1.0f - cn) * y + cn * ((1.0f - dbl) * tapO + dbl * endO);
        }

        bpPut (vi, pb, float ((w + 1) & 65535));
        return y;
    }

    float<2> bpStep (int vi, int o, float freq)
    {
        int   sb  = o * 192;
        float sr  = float (processor.frequency);
        float tp  = 6.2831853f;
        int   cnt = int (bpGet (vi, sb + 2));
        bool  upd = cnt <= 0;
        float t   = bpGet (vi, sb + 1);
        int   key = int (bpq (o, 12) + 0.5f);

        if (upd)
        {
            float dt = 16.0f / sr;
            float n  = 69.0f + 12.0f * float (log (clamp (freq, 8.0f, sr * 0.3f) / 440.0f)) / 0.6931472f;
            int   nr = int (floor (n + 0.5f));
            int   pc = ((nr - key) % 12 + 12) % 12;
            int   sc = int (bpq (o, 0) + 0.5f);
            float ct = sc == 1 ? bpJust.at (pc) : (sc == 2 ? bpHigh.at (pc) : 0.0f);

            // vibrato: clipped sine that only lowers the pitch, so the note is approached from below; blow: a bump every 4 s that drops it
            float vph = bpGet (vi, sb + 7) + 5.5f * dt;
            vph -= floor (vph);
            bpPut (vi, sb + 7, vph);
            float vs  = 0.5f + 0.5f * clamp (2.0f * float (sin (tp * vph)), -1.0f, 1.0f);
            float bph = bpGet (vi, sb + 8) + 0.25f * dt;
            bph -= floor (bph);
            bpPut (vi, sb + 8, bph);
            float bump = bph > 0.85f ? float (sin (3.1415927f * (bph - 0.85f) / 0.15f)) : 0.0f;
            float st   = -bpq (o, 14) * 0.7f * (1.0f - vs) - bpq (o, 15) * 0.8f * bump * bump;
            bpPut (vi, sb + 3, clamp (freq, 8.0f, sr * 0.3f) * float (pow (2.0f, (ct * 0.01f + st) / 12.0f)));

            int chord = int (bpq (o, 11) + 0.5f);

            if (chord > 0)
            {
                float stk = 0.05f + 0.9f * bpq (o, 13);
                float fl  = bpq (o, 6);

                for (int d = 0; d < 3; ++d)
                {
                    float semi = bpChord.at ((chord - 1) * 3 + d);
                    int   dpc  = int (semi + 0.5f) % 12;
                    float dct  = sc == 1 ? bpJust.at (dpc) : (sc == 2 ? bpHigh.at (dpc) : 0.0f);
                    float midi = 36.0f + float (key) + semi;
                    float fd   = 440.0f * float (pow (2.0f, (midi - 69.0f + dct * 0.01f) / 12.0f));
                    float off  = -(2.5f + 1.3f * float (d)) * float (exp (-t / (sr * stk * 0.6f)));
                    float dr   = d > 0 ? fl * 0.0015f * float (sin (tp * (0.09f + 0.07f * float (d)) * t / sr)) : 0.0f;
                    bpPut (vi, sb + 4 + d, min (fd * float (pow (2.0f, off / 12.0f)) * (1.0f + dr), sr * 0.3f));
                }
            }

            cnt = 16;
        }

        bpPut (vi, sb + 2, float (cnt - 1));
        bpPut (vi, sb + 1, t + 1.0f);

        float y = bpPipe (vi, o, 0, bpGet (vi, sb + 3), upd, 1.0f) * 2.4f;

        // colouration: feed-forward comb with a fixed delay (the fixed resonances of a pipe)
        float cm = bpq (o, 8);

        if (cm > 0.001f)
        {
            int   cd = clamp (int (sr / (100.0f * float (pow (80.0f, bpq (o, 9))))), 2, 1000);
            int   cw = int (bpGet (vi, sb + 13));
            int   cb = o * 18432 + 4096;
            float dl = voices.at (vi).bpd.at (cb + ((cw - cd) & 1023));
            voices.at (vi).bpd.at (cb + (cw & 1023)) = y;
            bpPut (vi, sb + 13, float ((cw + 1) & 65535));
            y = y * (1.0f - 0.5f * cm) + cm * 0.7f * dl;
        }

        float dL = 0.0f;
        float dR = 0.0f;
        int   ch = int (bpq (o, 11) + 0.5f);
        float dv = bpq (o, 10);

        if (ch > 0 && dv > 0.001f)
        {
            float stk = 0.05f + 0.9f * bpq (o, 13);

            for (int d = 0; d < 3; ++d)
            {
                float amp = 1.0f - float (exp (-t / (sr * stk * 0.4f)));
                float yd  = bpPipe (vi, o, 1 + d, bpGet (vi, sb + 4 + d), upd, amp) * 2.4f;
                float pan = (float (d) - 1.0f) * 0.35f;
                dL += yd * (1.0f - max (pan, 0.0f));
                dR += yd * (1.0f + min (pan, 0.0f));
            }

            dL *= dv * 0.6f;
            dR *= dv * 0.6f;
        }

        // DC blockers (one per channel)
        float xl = y + dL;
        float xr = y + dR;
        float yl = xl - bpGet (vi, sb + 9) + 0.995f * bpGet (vi, sb + 10);
        float yr = xr - bpGet (vi, sb + 11) + 0.995f * bpGet (vi, sb + 12);
        bpPut (vi, sb + 9, xl);
        bpPut (vi, sb + 10, yl);
        bpPut (vi, sb + 11, xr);
        bpPut (vi, sb + 12, yr);
        return float<2> (clamp (yl, -2.0f, 2.0f), clamp (yr, -2.0f, 2.0f));
    }

'''.replace("@LO@", LO).replace("@HI@", HI)
STEP = '''                    else if (ty == 13)
                    {
                        float<2> bw = bpStep (i, o, freq);
                        sL = bw[0];
                        sR = bw[1];
                        stereo = true;
                    }
'''
srcgen.install(PATCH, "                sfNoteOn (v, o, vel);\n", "BP", L.BP, L.bp_id, L.BP_DST_BASE, DSP,
               "        float[2048]   bps;    // Bagpipe source: state, slot * 192\n        float[131072] bpd;    // Bagpipe source: delay lines, slot * 18432\n",
               "                bpNoteOn (v, o);\n", STEP, "bpSet", "bpP", "tools/osc/build_bp.py", "NjoBp.h", "bp", L.BP_BASE, L.BP_STRIDE)
print("ok")
