#!/usr/bin/env python3
"""Idempotent: FX type 16 "Unison", marker FX-UNI.
2..8 detuned copies of the input, every copy a two-tap crossfading delay-line pitch shifter (Hann crossfade, window 10..60 ms), so the input is thickened
like a unison oscillator.  Parameters: P1 Voices (2..8), P2 Detune (0..100 cents, +- at the outer voices), P3 Spread (stereo, 0..100 %), P4 Drift (slow random
detune wobble, 0..12 cents), P5 Window (10..60 ms), P6 Tone (low-pass of the copies, 800 Hz .. 20 kHz = off).  Modes: Classic (evenly spaced), Super (dense
centre, wide edges), Hyper (wide centre spacing), Octaves (every 3rd voice +-1 octave, fine detune on top).
State: fxF fb+0..7 voice phases, fb+8..15 cents, fb+16..23 left gain, fb+24..31 right gain, fb+32/33 tone filter; fxI ib = write position, ib+1 = initialised;
fxPh s*4+1 = drift phase; arena: 2 x 16384 samples."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'FX-UNI' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )15\.0', r'\g<1>16.0', src); assert n == 30, n
rep('        int nt = clamp (t, 0, 15);', '        int nt = clamp (t, 0, 16);')
rep('        if (ty == 15)\n            fxWsDerive (s);\n', '        if (ty == 15)\n            fxWsDerive (s);\n\n        if (ty == 16)\n            fxUniDerive (s);   // FX-UNI\n')
rep('        else if (ty == 15) y = fxWs     (s, x);\n', '        else if (ty == 15) y = fxWs     (s, x);\n        else if (ty == 16) y = fxUni    (s, x);\n')
dsp = r'''    // ================= FX-UNI: Unison (FX type 16) =================
    void fxUniDerive (int s)
    {
        int   db = s * 16;
        int   pb = s * 6;
        int   fb = s * 40;
        float sr = float (processor.frequency);
        float dt = float (processor.period);
        float p1 = clamp (fxP.at (pb),     0.0f, 1.0f);
        float p2 = clamp (fxP.at (pb + 1), 0.0f, 1.0f);
        float p3 = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float p4 = clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float p5 = clamp (fxP.at (pb + 4), 0.0f, 1.0f);
        float p6 = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        int   n    = 2 + int (rint (p1 * 6.0f));
        int   mode = fxMode.at (s);
        float det  = p2 * 100.0f;

        for (int v = 0; v < 8; ++v)
        {
            float lin = n > 1 ? 2.0f * float (v) / float (n - 1) - 1.0f : 0.0f;
            float sg  = lin < 0.0f ? -1.0f : 1.0f;
            float x   = lin;
            float oct = 0.0f;

            if (mode == 1) x = sg * float (pow (abs (lin), 1.5f));
            if (mode == 2) x = sg * float (pow (abs (lin), 0.7f));

            if (mode == 3)
            {
                x = lin * 0.3f;
                if (v % 3 == 1) oct = 1200.0f;
                if (v % 3 == 2) oct = -1200.0f;
            }

            float pan = p3 * lin;
            fxF.at (fb + 8 + v)  = x * det + oct;
            fxF.at (fb + 16 + v) = min (1.0f, 1.4142f * float (cos ((pan + 1.0f) * 0.785398f)));
            fxF.at (fb + 24 + v) = min (1.0f, 1.4142f * float (sin ((pan + 1.0f) * 0.785398f)));
        }

        float w = clamp ((10.0f + 50.0f * p5) * 0.001f * sr, 64.0f, 15000.0f);
        float fc = fxExpMap (p6, 800.0f, 20000.0f);
        fxD.at (db)     = float (n);
        fxD.at (db + 1) = p4 * 12.0f;
        fxD.at (db + 2) = w;
        fxD.at (db + 3) = p6 > 0.995f ? 1.0f : clamp (1.0f - float (exp (-float (twoPi) * fc * dt)), 0.0f, 1.0f);
        fxD.at (db + 4) = 1.0f / float (sqrt (float (n)));
        fxD.at (db + 5) = 1.0f / w;
    }

    float<2> fxUni (int s, float<2> x)
    {
        int   fb    = s * 40;
        int   ib    = s * 24;
        int   db    = s * 16;
        int   ab    = s * 196608;
        int   n     = int (fxD.at (db) + 0.5f);
        float drift = fxD.at (db + 1);
        float wnd   = fxD.at (db + 2);
        float invW  = fxD.at (db + 5);
        int   pos   = fxI.at (ib);

        if (fxI.at (ib + 1) == 0)
        {
            fxI.at (ib + 1) = 1;

            for (int v = 0; v < 8; ++v)
                fxF.at (fb + v) = float (v) / float (n);
        }

        fxArena.at (ab + pos)         = x[0];
        fxArena.at (ab + 16384 + pos) = x[1];

        float64 dph = fxPh.at (s * 4 + 1) + processor.period * 0.2;
        if (dph >= 1.0) dph -= 1.0;
        fxPh.at (s * 4 + 1) = dph;

        float wl = 0.0f;
        float wr = 0.0f;

        for (int v = 0; v < n; ++v)
        {
            float c  = fxF.at (fb + 8 + v);
            float ga = fxF.at (fb + 16 + v);
            float gb = fxF.at (fb + 24 + v);
            float vl = x[0];
            float vr = x[1];

            if (abs (c) > 0.001f || drift > 0.001f)
            {
                if (drift > 0.001f)
                    c += drift * float (sin (float (twoPi) * (float (v + 1) * float (dph) + float (v) * 0.137f)));

                float ratio = float (exp (c * 0.00057762265f));
                float phi   = fxF.at (fb + v) + (1.0f - ratio) * invW;
                phi -= float (floor (phi));
                fxF.at (fb + v) = phi;

                float sn = float (sin (3.14159265f * phi));
                float w1 = sn * sn;
                float w2 = 1.0f - w1;
                float p2 = phi + 0.5f;
                if (p2 >= 1.0f) p2 -= 1.0f;
                float d1 = phi * wnd + 2.0f;
                float d2 = p2 * wnd + 2.0f;

                vl = fxTapN (ab, 16384, float (pos) - d1) * w1 + fxTapN (ab, 16384, float (pos) - d2) * w2;
                vr = fxTapN (ab + 16384, 16384, float (pos) - d1) * w1 + fxTapN (ab + 16384, 16384, float (pos) - d2) * w2;
            }

            wl += vl * ga;
            wr += vr * gb;
        }

        float g  = fxD.at (db + 4);
        float tc = fxD.at (db + 3);
        float l1 = fxF.at (fb + 32) + tc * (wl * g - fxF.at (fb + 32));
        float r1 = fxF.at (fb + 33) + tc * (wr * g - fxF.at (fb + 33));
        fxF.at (fb + 32) = l1;
        fxF.at (fb + 33) = r1;

        pos += 1;
        if (pos >= 16384) pos = 0;
        fxI.at (ib) = pos;

        return float<2> (l1, r1);
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', dsp + '    // One slot: dry/wet mix of the selected effect;')
open(path, 'w').write(src)
print('ok')
