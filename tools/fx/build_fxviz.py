#!/usr/bin/env python3
"""Idempotent (marker FX-VIZ): live data of one effect slot for the editor (output event fxViz).
 The editor sets  param9890 "FX Monitor" (0 = off, 1 + global slot number 0..47);  fxRunSlot then taps the input and the result of that slot:
 24 band pass filters (40 Hz - 16 kHz, log spaced) per signal feed envelope followers, the peaks are held.  Every 1/20 s a packet of 54 floats is streamed
 (one event per 48 samples, about 18 packets per second):  -1 (start), slot, peak in L, in R, out L, out R (linear), 24 input bands, 24 output bands (0..1 = -72 .. 0 dB)."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); IP = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-VIZ' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
rep('    output event int seqPos;', '    output event float fxViz;   // FX-VIZ: live data of the effect slot the editor shows\n    output event int seqPos;')
rep('    // EURO\n', '    input event float param9890 [[ name: "FX Monitor (editor: 0 = none, 1 + slot)", min: 0.0, max: 48.0, init: 0.0, step: 1.0, automatable: false ]];   // FX-VIZ\n    // EURO\n')
rep('    // RESO-HAND-BEGIN\n', '    event param9890 (float v) { fxMon = clamp (int (v + 0.5f), 0, 48) - 1; vzInit(); }   // FX-VIZ\n    // RESO-HAND-BEGIN\n')
rep('    float driveAmt     = 0.1f;\n', '''    float driveAmt     = 0.1f;
    int       fxMon = -1;      // FX-VIZ: effect slot shown by the editor (-1 none)
    float[24] vzB0;
    float[24] vzA1;
    float[24] vzA2;
    float[128] vzZ;
    float[48] vzEnv;
    float[64] vzPkt;
    float[4]  vzP;
    float     vzK = 0.001f;
    int       vzIdx = 99;
    int       vzCount = 0;
    int       vzGap = 0;
''')
CODE = r'''    // ================= FX-VIZ: live data of the monitored effect slot =================
    void vzInit()
    {
        float sr = float (processor.frequency);

        for (int b = 0; b < 24; ++b)
        {
            float fc = 40.0f * float (pow (400.0f, float (b) / 23.0f));
            float w  = 6.2831853f * min (fc, sr * 0.45f) / sr;
            float al = float (sin (w)) / (2.0f * 4.3f);
            float a0 = 1.0f + al;
            vzB0.at (b) = al / a0;
            vzA1.at (b) = -2.0f * float (cos (w)) / a0;
            vzA2.at (b) = (1.0f - al) / a0;
        }

        for (int i = 0; i < 128; ++i)
            vzZ.at (i) = 0.0f;

        for (int i = 0; i < 48; ++i)
            vzEnv.at (i) = 0.0f;

        for (int i = 0; i < 4; ++i)
            vzP.at (i) = 0.0f;

        vzK     = 1.0f - float (exp (-1.0f / (sr * 0.03f)));
        vzIdx   = 99;
        vzCount = 0;
    }

    float vzNorm (float e)
    {
        return clamp ((20.0f * float (log10 (max (e * 1.57f, 0.00001f))) + 72.0f) / 72.0f, 0.0f, 1.0f);
    }

    void vzTap (float<2> xin, float<2> yout)
    {
        vzP.at (0) = max (vzP.at (0), abs (xin[0]));
        vzP.at (1) = max (vzP.at (1), abs (xin[1]));
        vzP.at (2) = max (vzP.at (2), abs (yout[0]));
        vzP.at (3) = max (vzP.at (3), abs (yout[1]));
        float mi = (xin[0] + xin[1]) * 0.5f;
        float mo = (yout[0] + yout[1]) * 0.5f;

        for (int b = 0; b < 24; ++b)
        {
            float b0 = vzB0.at (b);
            float a1 = vzA1.at (b);
            float a2 = vzA2.at (b);
            int   zi = b * 4;
            float yi = b0 * mi + vzZ.at (zi);
            vzZ.at (zi)     = clamp (-a1 * yi + vzZ.at (zi + 1), -64.0f, 64.0f);
            vzZ.at (zi + 1) = clamp (-b0 * mi - a2 * yi, -64.0f, 64.0f);
            float yo = b0 * mo + vzZ.at (zi + 2);
            vzZ.at (zi + 2) = clamp (-a1 * yo + vzZ.at (zi + 3), -64.0f, 64.0f);
            vzZ.at (zi + 3) = clamp (-b0 * mo - a2 * yo, -64.0f, 64.0f);
            vzEnv.at (b)      += vzK * (abs (yi) - vzEnv.at (b));
            vzEnv.at (24 + b) += vzK * (abs (yo) - vzEnv.at (24 + b));
        }

        vzCount++;
        vzGap++;

        if (vzIdx < 54 && vzGap >= 48)   // one event per 48 samples: the host keeps only 32 output events per block
        {
            vzGap = 0;
            fxViz <- vzPkt.at (vzIdx);
            vzIdx++;
        }

        if (vzCount >= int (float (processor.frequency) * 0.05f) && vzIdx >= 54)
        {
            vzCount = 0;
            vzPkt.at (0) = -1.0f;
            vzPkt.at (1) = float (fxMon);

            for (int i = 0; i < 4; ++i)
            {
                vzPkt.at (2 + i) = min (vzP.at (i), 8.0f);
                vzP.at (i) = 0.0f;
            }

            for (int b = 0; b < 48; ++b)
                vzPkt.at (6 + b) = vzNorm (vzEnv.at (b));

            vzIdx = 0;
        }
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
rep('        float mix = clamp (fxMix.at (s), 0.0f, 1.0f);\n        return x + (y - x) * mix;\n', '        float mix = clamp (fxMix.at (s), 0.0f, 1.0f);\n        float<2> res = x + (y - x) * mix;\n\n        if (s == fxMon)\n            vzTap (x, res);   // FX-VIZ\n\n        return res;\n')
rep('    // EURO: Eurorack rack of Njohrr Modular\n', '    L.push([9890, "FX Monitor (editor: 0 = none, 1 + slot)", 0, 48, 0, "", "stp", null, 1, "Monitor"]);   // FX-VIZ\n    // EURO: Eurorack rack of Njohrr Modular\n', 'idx')
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('FX-VIZ applied')
