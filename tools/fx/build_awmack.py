#!/usr/bin/env python3
"""Idempotent: Airwindows MackEQ as FX type 27 (marker FX-AW-MACK). Port of MackEQ by Chris Johnson (MIT licence, https://github.com/airwindows/airwindows).
State: awT (48 float64 per slot: two channels of 6 one-pole filters and 4 biquads), derived values in awD (like the other AW types)."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'FX-AW-MACK' in src:
    print('already applied'); sys.exit(0)

def rep(old, new):
    global src
    assert src.count(old) == 1, (src.count(old), old)
    src = src.replace(old, new)

rep('    float64[1152] awD;  // FX-AW: derived values (24 per slot)\n',
    '    float64[1152] awD;  // FX-AW: derived values (24 per slot)\n    float64[2304] awT;  // FX-AW-MACK: MackEQ state (48 per slot)\n')
rep('        awS.at (s * 40 + 8)  = -1.0;', '        for (int i = 0; i < 48; ++i)   // FX-AW-MACK\n            awT.at (s * 48 + i) = 0.0;\n\n        awS.at (s * 40 + 8)  = -1.0;')
rep('int nt = clamp (t, 0, 26);', 'int nt = clamp (t, 0, 27);')
rep('        if (ty >= 19 && ty <= 26)\n            awDerive (s);', '        if (ty >= 19 && ty <= 27)\n            awDerive (s);')
rep('        else if (ty == 26) y = fxAwTape    (s, x);\n', '        else if (ty == 26) y = fxAwTape    (s, x);\n        else if (ty == 27) y = fxAwMack    (s, x);\n')
# derive: before the end of awDerive (after the ty == 26 block, which ends with the flutter trim line)
rep('            awD.at (db + 12) = (0.0024 * d * d) / os;\n        }\n',
    '''            awD.at (db + 12) = (0.0024 * d * d) / os;
        }

        if (ty == 27)   // FX-AW-MACK
        {
            float64 fc = min (19160.0 / sr, 0.49);
            float64 k  = tan (3.14159265358979 * fc);
            float64 q0 = 0.431684981684982;
            float64 q1 = 1.1582298;
            float64 q2 = 0.657027382751269;
            float64 q3 = 1.076210852946577;
            float64 n0 = 1.0 / (1.0 + k / q0 + k * k);
            float64 n1 = 1.0 / (1.0 + k / q1 + k * k);
            float64 n2 = 1.0 / (1.0 + k / q2 + k * k);
            float64 n3 = 1.0 / (1.0 + k / q3 + k * k);
            float64 tr = a * 10.0;
            awD.at (db)      = tr * tr;
            awD.at (db + 1)  = pow (b, 2.0) * 4.0;
            awD.at (db + 2)  = sqrt (b);
            awD.at (db + 3)  = pow (c, 2.0) * 4.0;
            awD.at (db + 4)  = sqrt (c);
            awD.at (db + 5)  = d;
            awD.at (db + 6)  = 0.001860867 / os;
            awD.at (db + 7)  = 0.000287496 / os;
            awD.at (db + 8)  = 0.159 / os;
            awD.at (db + 9)  = 0.236 / os;
            awD.at (db + 10) = k * k * n0;  awD.at (db + 11) = 2.0 * (k * k - 1.0) * n0;  awD.at (db + 12) = (1.0 - k / q0 + k * k) * n0;
            awD.at (db + 13) = k * k * n1;  awD.at (db + 14) = 2.0 * (k * k - 1.0) * n1;  awD.at (db + 15) = (1.0 - k / q1 + k * k) * n1;
            awD.at (db + 16) = k * k * n2;  awD.at (db + 17) = 2.0 * (k * k - 1.0) * n2;  awD.at (db + 18) = (1.0 - k / q2 + k * k) * n2;
            awD.at (db + 19) = k * k * n3;  awD.at (db + 20) = 2.0 * (k * k - 1.0) * n3;  awD.at (db + 21) = (1.0 - k / q3 + k * k) * n3;
        }
''')
CODE = r'''    // ---- MackEQ (FX type 27): state per channel c at awT[s * 48 + c * 24]: 0..5 one-pole filters A-F, 6 + 4 * f .. biquads A-D (x1, x2, y1, y2) ----
    float64 awMackBq (int ix, float64 x, int cf)
    {
        float64 b0 = awD.at (cf);
        float64 o  = b0 * x + 2.0 * b0 * awT.at (ix) + b0 * awT.at (ix + 1) - awD.at (cf + 1) * awT.at (ix + 2) - awD.at (cf + 2) * awT.at (ix + 3);
        awT.at (ix + 1) = awT.at (ix);
        awT.at (ix)     = x;
        awT.at (ix + 3) = awT.at (ix + 2);
        awT.at (ix + 2) = o;
        return o;
    }

    float64 awMackSat (float64 x)
    {
        x = clamp (x, -1.0, 1.0);
        return x - pow (x, 5.0) * 0.1768;
    }

    float64 awMackIir (int ix, float64 x, float64 amt)
    {
        float64 v = abs (awT.at (ix)) < 1.18e-37 ? 0.0 : awT.at (ix);
        v = v * (1.0 - amt) + x * amt;
        awT.at (ix) = v;
        return v;
    }

    float64 awMackCh (int s, int c, float64 x)
    {
        int     sb = s * 48 + c * 24;
        int     db = s * 24;
        float64 inTrim = awD.at (db),     gainHigh = awD.at (db + 1), outHigh = awD.at (db + 2);
        float64 gainBass = awD.at (db + 3), outBass = awD.at (db + 4), outPad = awD.at (db + 5);
        float64 iirA = awD.at (db + 6), iirB = awD.at (db + 7), iirBM = awD.at (db + 8), iirMH = awD.at (db + 9);

        x -= awMackIir (sb, x, iirA);

        if (inTrim != 1.0)
            x *= inTrim;

        x = awMackBq (sb + 6, x, db + 10);
        x = awMackSat (x);
        x = awMackBq (sb + 10, x, db + 13);
        x -= awMackIir (sb + 1, x, iirB);

        float64 bass = awMackIir (sb + 2, x, iirBM);
        float64 mid  = x - bass;

        if (gainBass != 1.0)
            bass *= gainBass;

        bass = awMackSat (bass);
        bass = awMackIir (sb + 3, bass, iirBM);

        float64 e    = awMackIir (sb + 4, mid, iirMH);
        float64 high = mid - e;
        mid = e;
        high -= awMackIir (sb + 5, high, iirMH);

        if (gainHigh != 1.0)
            high *= gainHigh;

        high = awMackSat (high);
        x = ((bass * outBass) + mid + (high * outHigh)) * 4.0;

        x = awMackBq (sb + 14, x, db + 16);
        x = awMackSat (x);
        x = awMackBq (sb + 18, x, db + 19);

        if (outPad != 1.0)
            x *= outPad;

        return x;
    }

    float<2> fxAwMack (int s, float<2> x)
    {
        float64 n = awNoise (s);
        float64 l = awMackCh (s, 0, float64 (x[0]) + n);
        float64 r = awMackCh (s, 1, float64 (x[1]) + n);
        awFlip (s);
        return float<2> (float (l), float (r));
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
open(P, 'w').write(src)
print('ok')
