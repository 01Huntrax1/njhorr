#!/usr/bin/env python3
"""Idempotent: eight Airwindows effects as FX types 19..26, marker FX-AW.
Ports of Airwindows plugins by Chris Johnson (MIT licence, https://github.com/airwindows/airwindows): PurestDrive, Spiral2, Drive, Tube2, Density2,
Console7Channel, Channel9, ToTape6. The processing is computed in float64 (awS = state, awD = derived values); delay lines (ToTape flutter) use the slot arena."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(P).read()
if 'FX-AW' in src:
    print('already applied'); sys.exit(0)

def rep(old, new):
    global src
    assert src.count(old) == 1, (src.count(old), old)
    src = src.replace(old, new)

rep('    float[2048]   fxF;  // padded to a power of two (cheap index wrap)\n',
    '    float[2048]   fxF;  // padded to a power of two (cheap index wrap)\n'
    '    float64[2048] awS;  // FX-AW: Airwindows effects, state (40 per slot)\n'
    '    float64[1152] awD;  // FX-AW: derived values (24 per slot)\n')
rep('        fxFcS.at (s) = 0.0f;   // FX-FENV2\n',
    '        fxFcS.at (s) = 0.0f;   // FX-FENV2\n'
    '\n'
    '        for (int i = 0; i < 40; ++i)   // FX-AW\n'
    '            awS.at (s * 40 + i) = 0.0;\n'
    '\n'
    '        awS.at (s * 40 + 8)  = -1.0;       // Console 7: gain chase starts at the target\n'
    '        awS.at (s * 40 + 26) = 3.14159265358979;   // ToTape: sweep, rate, next maximum\n'
    '        awS.at (s * 40 + 27) = 0.5;\n'
    '        awS.at (s * 40 + 28) = 0.5;\n'
    '        fxI.at (s * 24 + 21) = 0;\n')
rep('int nt = clamp (t, 0, 18);', 'int nt = clamp (t, 0, 26);')
rep('            fxFbDerive (s);   // FX-FBANK\n',
    '            fxFbDerive (s);   // FX-FBANK\n\n        if (ty >= 19 && ty <= 26)\n            awDerive (s);   // FX-AW\n')
rep('        else if (ty == 18) y = fxFb     (s, x);\n',
    '        else if (ty == 18) y = fxFb     (s, x);\n'
    '        else if (ty == 19) y = fxAwPurest  (s, x);\n'
    '        else if (ty == 20) y = fxAwSpiral  (s, x);\n'
    '        else if (ty == 21) y = fxAwDrive   (s, x);\n'
    '        else if (ty == 22) y = fxAwTube    (s, x);\n'
    '        else if (ty == 23) y = fxAwDensity (s, x);\n'
    '        else if (ty == 24) y = fxAwConsole (s, x);\n'
    '        else if (ty == 25) y = fxAwChannel (s, x);\n'
    '        else if (ty == 26) y = fxAwTape    (s, x);\n')

CODE = r'''    // ================= FX-AW: Airwindows effects (FX types 19..26) =================
    // Ports of Airwindows plugins by Chris Johnson (MIT licence, https://github.com/airwindows/airwindows). Computed in float64; state awS[s * 40 + ...], derived awD[s * 24 + ...].
    // 19 PurestDrive, 20 Spiral2, 21 Drive, 22 Tube2, 23 Density2, 24 Console7Channel, 25 Channel9 (mode = console type), 26 ToTape6.

    float64 awExp (float64 n, float64 lo, float64 hi)
    {
        return lo * pow (hi / lo, n);
    }

    void awDerive (int s)
    {
        int     ty = fxType.at (s);
        int     db = s * 24;
        int     pb = s * 6;
        float64 sr = float64 (processor.frequency);
        float64 os = sr / 44100.0;
        float64 a  = clamp (float64 (fxP.at (pb)),     0.0, 1.0);
        float64 b  = clamp (float64 (fxP.at (pb + 1)), 0.0, 1.0);
        float64 c  = clamp (float64 (fxP.at (pb + 2)), 0.0, 1.0);
        float64 d  = clamp (float64 (fxP.at (pb + 3)), 0.0, 1.0);
        float64 e  = clamp (float64 (fxP.at (pb + 4)), 0.0, 1.0);

        if (ty == 19)
            awD.at (db) = a;

        if (ty == 20)
        {
            awD.at (db)     = pow (a * 2.0, 2.0);
            awD.at (db + 1) = pow (b, 3.0) / os;
            awD.at (db + 2) = c;
            awD.at (db + 3) = d;
        }

        if (ty == 21)
        {
            awD.at (db)     = pow (a * 2.0, 2.0);
            awD.at (db + 1) = pow (b, 3.0) / os;
            awD.at (db + 2) = c;
        }

        if (ty == 22)
        {
            int pf = int (9.0 * (1.0 - b)) + 1;
            awD.at (db)     = a;
            awD.at (db + 1) = float64 (pf);
            awD.at (db + 2) = 1.0 / float64 (pf + 1);
            awD.at (db + 3) = 1.0 + 1.0 / float64 (pf);
            awD.at (db + 4) = os > 1.9 ? 1.0 : 0.0;
        }

        if (ty == 23)
        {
            float64 density = a * 5.0 - 1.0;
            float64 o       = abs (density);

            while (o > 1.0)
                o -= 1.0;

            awD.at (db)     = density * abs (density);
            awD.at (db + 1) = o;
            awD.at (db + 2) = pow (b, 3.0) / os;
            awD.at (db + 3) = c;
        }

        if (ty == 24)
        {
            float64 fc   = min (20000.0 / sr, 0.49);
            float64 q    = 1.618033988749894848;
            float64 k    = tan (3.14159265358979 * fc);
            float64 norm = 1.0 / (1.0 + k / q + k * k);
            awD.at (db)     = a * 1.272019649514069;
            awD.at (db + 1) = k * k * norm;
            awD.at (db + 2) = 2.0 * k * k * norm;
            awD.at (db + 3) = k * k * norm;
            awD.at (db + 4) = 2.0 * (k * k - 1.0) * norm;
            awD.at (db + 5) = (1.0 - k / q + k * k) * norm;
        }

        if (ty == 25)
        {
            int     m   = clamp (fxMode.at (s), 0, 4);
            float64 iir = 0.005832;  float64 thr = 0.33362176;  float64 cut = 28811.0;

            if (m == 1) { iir = 0.004096; thr = 0.59969536; cut = 27216.0; }
            if (m == 2) { iir = 0.004913; thr = 0.84934656; cut = 23011.0; }
            if (m == 3) { iir = 0.009216; thr = 0.149;      cut = 18544.0; }
            if (m == 4) { iir = 0.011449; thr = 0.092;      cut = 19748.0; }

            float64 density  = a * 2.0;
            float64 phattity = max (density - 1.0, 0.0);
            density = min (density, 1.0);

            float64 fc = cut / sr;
            float64 k  = tan (3.14159265358979 * min (fc, 0.49));
            float64 qa = 1.618033988749894848;
            float64 qb = 0.618033988749894848;
            float64 na = 1.0 / (1.0 + k / qa + k * k);
            float64 nb = 1.0 / (1.0 + k / qb + k * k);
            awD.at (db)      = iir / os;
            awD.at (db + 1)  = thr;
            awD.at (db + 2)  = density;
            awD.at (db + 3)  = phattity;
            awD.at (db + 4)  = 5.0 - density;
            awD.at (db + 5)  = b;
            awD.at (db + 6)  = fc < 0.49999 ? 1.0 : 0.0;
            awD.at (db + 7)  = k * k * na;
            awD.at (db + 8)  = 2.0 * (k * k - 1.0) * na;
            awD.at (db + 9)  = (1.0 - k / qa + k * k) * na;
            awD.at (db + 10) = k * k * nb;
            awD.at (db + 11) = 2.0 * (k * k - 1.0) * nb;
            awD.at (db + 12) = (1.0 - k / qb + k * k) * nb;
        }

        if (ty == 26)
        {
            float64 inputgain = pow (10.0, ((a - 0.5) * 24.0) / 20.0);
            float64 soften    = b * b;
            float64 k1        = tan (3.14159265358979 * (0.007 / os));
            float64 q1        = 0.0009;
            float64 n1        = 1.0 / (1.0 + k1 / q1 + k1 * k1);
            float64 k2        = tan (3.14159265358979 * (0.032 / os));
            float64 q2        = 0.0007;
            float64 n2        = 1.0 / (1.0 + k2 / q2 + k2 * k2);
            awD.at (db)      = inputgain;
            awD.at (db + 1)  = (1.0 - soften * 0.45) / os;
            awD.at (db + 2)  = c * 0.25 * inputgain;
            awD.at (db + 3)  = 0.12 / os;
            awD.at (db + 4)  = k1 / q1 * n1;
            awD.at (db + 5)  = 2.0 * (k1 * k1 - 1.0) * n1;
            awD.at (db + 6)  = (1.0 - k1 / q1 + k1 * k1) * n1;
            awD.at (db + 7)  = k2 / q2 * n2;
            awD.at (db + 8)  = 2.0 * (k2 * k2 - 1.0) * n2;
            awD.at (db + 9)  = (1.0 - k2 / q2 + k2 * k2) * n2;
            awD.at (db + 10) = pow (10.0, ((e - 0.5) * 24.0) / 20.0);
            awD.at (db + 11) = d * d * os * 70.0;
            awD.at (db + 12) = (0.0024 * d * d) / os;
        }
    }

    // alternating tiny offset (keeps the filter memories out of the denormal range)
    float64 awNoise (int s)
    {
        return awS.at (s * 40 + 39) > 0.5 ? 1.0e-20 : -1.0e-20;
    }

    void awFlip (int s)
    {
        awS.at (s * 40 + 39) = awS.at (s * 40 + 39) > 0.5 ? 0.0 : 1.0;
    }

    // ---- PurestDrive ----
    float64 awPurestCh (int s, int c, float64 x)
    {
        int     sb = s * 40;
        float64 i  = awD.at (s * 24);
        float64 sn = sin (x);
        float64 ap = (abs (awS.at (sb + c) + sn) * 0.5) * i;
        awS.at (sb + c) = sin (x);
        return x * (1.0 - ap) + sn * ap;
    }

    float<2> fxAwPurest (int s, float<2> x)
    {
        float64 n = awNoise (s);
        float64 l = awPurestCh (s, 0, float64 (x[0]) + n);
        float64 r = awPurestCh (s, 1, float64 (x[1]) + n);
        awFlip (s);
        return float<2> (float (l), float (r));
    }

    // ---- Spiral2 ----
    float64 awSpiralCh (int s, int c, float64 x, bool flip)
    {
        int     sb   = s * 40;
        int     db   = s * 24;
        float64 gain = awD.at (db);
        float64 iir  = awD.at (db + 1);
        float64 pres = awD.at (db + 2);
        float64 outp = awD.at (db + 3);
        float64 dry  = x;
        float64 prev = awS.at (sb + 4 + c);

        if (gain != 1.0)
        {
            x    *= gain;
            prev *= gain;
        }

        if (flip)
        {
            float64 v = awS.at (sb + c) * (1.0 - iir) + x * iir;
            awS.at (sb + c) = v;
            x -= v;
        }
        else
        {
            float64 v = awS.at (sb + 2 + c) * (1.0 - iir) + x * iir;
            awS.at (sb + 2 + c) = v;
            x -= v;
        }

        float64 ps = sin (x * abs (prev)) / (prev == 0.0 ? 1.0 : abs (prev));
        x = sin (x * abs (x)) / (abs (x) == 0.0 ? 1.0 : abs (x));

        if (outp < 1.0)
        {
            x  *= outp;
            ps *= outp;
        }

        if (pres > 0.0)
            x = x * (1.0 - pres) + ps * pres;

        awS.at (sb + 4 + c) = dry;
        return x;
    }

    float<2> fxAwSpiral (int s, float<2> x)
    {
        float64 n = awNoise (s);
        bool    f = awS.at (s * 40 + 39) > 0.5;
        float64 l = awSpiralCh (s, 0, float64 (x[0]) + n, f);
        float64 r = awSpiralCh (s, 1, float64 (x[1]) + n, f);
        awFlip (s);
        return float<2> (float (l), float (r));
    }

    // ---- Drive ----
    float64 awDriveCh (int s, int c, float64 x, bool flip)
    {
        int     sb    = s * 40;
        int     db    = s * 24;
        float64 drive = awD.at (db);
        float64 iir   = awD.at (db + 1);
        float64 outp  = awD.at (db + 2);

        if (flip)
        {
            float64 v = awS.at (sb + c) * (1.0 - iir) + x * iir;
            awS.at (sb + c) = v;
            x -= v;
        }
        else
        {
            float64 v = awS.at (sb + 2 + c) * (1.0 - iir) + x * iir;
            awS.at (sb + 2 + c) = v;
            x -= v;
        }

        x = clamp (x, -1.0, 1.0);

        float64 glitch = 0.60;
        float64 o      = drive;

        while (o > glitch)
        {
            o -= glitch;
            x -= x * (abs (x) * glitch) * (abs (x) * glitch);
            x *= 1.0 + glitch;
        }

        x -= x * (abs (x) * o) * (abs (x) * o);
        x *= 1.0 + o;

        if (outp < 1.0)
            x *= outp;

        return x;
    }

    float<2> fxAwDrive (int s, float<2> x)
    {
        float64 n = awNoise (s);
        bool    f = awS.at (s * 40 + 39) > 0.5;
        float64 l = awDriveCh (s, 0, float64 (x[0]) + n, f);
        float64 r = awDriveCh (s, 1, float64 (x[1]) + n, f);
        awFlip (s);
        return float<2> (float (l), float (r));
    }

    // ---- Tube2 ----
    float64 awTubeCh (int s, int c, float64 x)
    {
        int     sb    = s * 40;
        int     db    = s * 24;
        float64 pad   = awD.at (db);
        int     pf    = int (awD.at (db + 1) + 0.5);
        float64 gs    = awD.at (db + 2);
        float64 os2   = awD.at (db + 3);
        bool    hiSr  = awD.at (db + 4) > 0.5;

        if (pad < 1.0)
            x *= pad;

        if (hiSr)
        {
            float64 st = x;
            x = (x + awS.at (sb + c)) * 0.5;
            awS.at (sb + c) = st;
        }

        x = clamp (x, -1.0, 1.0);

        float64 asym = float64 (pf);
        x /= asym;
        float64 sharpen = -x;
        sharpen = sharpen > 0.0 ? 1.0 + sqrt (sharpen) : 1.0 - sqrt (-sharpen);
        x -= x * abs (x) * sharpen * 0.25;
        x *= asym;

        float64 factor = x;

        for (int k = 0; k < pf; ++k)
            factor *= x;

        if ((pf % 2 == 1) && x != 0.0)
            factor = (factor / x) * abs (x);

        factor *= gs;
        x -= factor;
        x *= os2;

        if (hiSr)
        {
            float64 st = x;
            x = (x + awS.at (sb + 2 + c)) * 0.5;
            awS.at (sb + 2 + c) = st;
        }

        float64 slew = awS.at (sb + 4 + c) - x;

        if (hiSr)
        {
            float64 st = x;
            x = (x + awS.at (sb + 4 + c)) * 0.5;
            awS.at (sb + 4 + c) = st;
        }
        else
            awS.at (sb + 4 + c) = x;

        slew = slew > 0.0 ? 1.0 + sqrt (slew) * 0.5 : 1.0 - sqrt (-slew) * 0.5;
        x -= x * abs (x) * slew * gs;
        x = clamp (x, -0.52, 0.52);
        return x * 1.923076923076923;
    }

    float<2> fxAwTube (int s, float<2> x)
    {
        float64 n = awNoise (s);
        float64 l = awTubeCh (s, 0, float64 (x[0]) + n);
        float64 r = awTubeCh (s, 1, float64 (x[1]) + n);
        awFlip (s);
        return float<2> (float (l), float (r));
    }

    // ---- Density2 ----
    float64 awDensShape (float64 v, float64 density, float64 o)
    {
        float64 count = density;
        float64 br;

        while (count > 1.0)
        {
            br = min (abs (v) * 1.57079633, 1.57079633);
            br = sin (br);
            v  = v > 0.0 ? br : -br;
            count -= 1.0;
        }

        br = min (abs (v) * 1.57079633, 1.57079633);
        br = density > 0.0 ? sin (br) : 1.0 - cos (br);
        return v > 0.0 ? v * (1.0 - o) + br * o : v * (1.0 - o) - br * o;
    }

    float64 awDensityCh (int s, int c, float64 x)
    {
        int     sb      = s * 40 + c * 8;
        int     db      = s * 24;
        float64 density = awD.at (db);
        float64 o       = awD.at (db + 1);
        float64 iir     = awD.at (db + 2);
        float64 outp    = awD.at (db + 3);
        float64 k       = 0.915965594177219015;
        float64 dry     = x;

        float64 half    = (x + awS.at (sb) + ((-awS.at (sb + 1) + awS.at (sb + 2)) * 0.0414213562373095048801688)) * 0.5;
        float64 halfDry = half;
        awS.at (sb + 2) = awS.at (sb + 1);
        awS.at (sb + 1) = awS.at (sb);
        awS.at (sb)     = x;

        awS.at (sb + 4) = awS.at (sb + 4) * (1.0 - iir) + half * iir;
        half -= awS.at (sb + 4);
        half = awDensShape (half, density, o);

        float64 ataC = half - halfDry;
        float64 ataA = awS.at (sb + 5) * k;
        float64 ataB = awS.at (sb + 6) * k;
        ataB += ataC;  ataA -= ataC;  ataC = ataB;
        float64 halfDiff = ataC * k;

        awS.at (sb + 3) = awS.at (sb + 3) * (1.0 - iir) + x * iir;
        x -= awS.at (sb + 3);
        x = awDensShape (x, density, o);

        ataC = x - dry;
        ataA *= k;  ataB *= k;
        ataA += ataC;  ataB -= ataC;  ataC = ataA;
        awS.at (sb + 5) = ataA;
        awS.at (sb + 6) = ataB;
        float64 diff = ataC * k;

        x = dry + ((diff + halfDiff + awS.at (sb + 7)) / 1.187);
        awS.at (sb + 7) = diff * 0.5;
        return x * outp;
    }

    float<2> fxAwDensity (int s, float<2> x)
    {
        float64 n = awNoise (s);
        float64 l = awDensityCh (s, 0, float64 (x[0]) + n);
        float64 r = awDensityCh (s, 1, float64 (x[1]) + n);
        awFlip (s);
        return float<2> (float (l), float (r));
    }

    // ---- Console7Channel ----
    float64 awConsoleCh (int s, int c, float64 x, float64 gc)
    {
        int     sb = s * 40 + c * 4;
        int     db = s * 24;
        float64 o  = awD.at (db + 1) * x + awD.at (db + 2) * awS.at (sb) + awD.at (db + 3) * awS.at (sb + 1)
                     - awD.at (db + 4) * awS.at (sb + 2) - awD.at (db + 5) * awS.at (sb + 3);
        awS.at (sb + 1) = awS.at (sb);
        awS.at (sb)     = x;
        awS.at (sb + 3) = awS.at (sb + 2);
        awS.at (sb + 2) = o;
        x = o;

        if (gc != 1.0)
            x *= gc * gc * gc;

        x = clamp (x, -1.097, 1.097);
        x = ((sin (x * abs (x)) / (abs (x) == 0.0 ? 1.0 : abs (x))) * 0.8) + (sin (x) * 0.2);

        if (gc != 1.0 && gc != 0.0)
            x /= gc;

        return x;
    }

    float<2> fxAwConsole (int s, float<2> x)
    {
        int     sb = s * 40;
        float64 ig = awD.at (s * 24);
        float64 gc = awS.at (sb + 8);

        if (gc < 0.0)
            gc = ig;

        gc = (gc * 64.0 + ig) / 65.0;
        awS.at (sb + 8) = gc;

        float64 n = awNoise (s);
        float64 l = awConsoleCh (s, 0, float64 (x[0]) + n, gc);
        float64 r = awConsoleCh (s, 1, float64 (x[1]) + n, gc);
        awFlip (s);
        return float<2> (float (l), float (r));
    }

    // ---- Channel9 ----
    float64 awChannelCh (int s, int c, float64 x, bool flip)
    {
        int     sb  = s * 40;
        int     db  = s * 24;
        float64 liir = awD.at (db);
        float64 thr  = awD.at (db + 1);
        float64 dens = awD.at (db + 2);
        float64 phat = awD.at (db + 3);
        float64 nl   = awD.at (db + 4);
        float64 outp = awD.at (db + 5);
        bool    bq   = awD.at (db + 6) > 0.5;
        int     ba   = sb + c * 4;
        int     bb   = sb + 8 + c * 4;

        if (bq)
        {
            float64 t = awD.at (db + 7) * x + 2.0 * awD.at (db + 7) * awS.at (ba) + awD.at (db + 7) * awS.at (ba + 1)
                        - awD.at (db + 8) * awS.at (ba + 2) - awD.at (db + 9) * awS.at (ba + 3);
            awS.at (ba + 1) = awS.at (ba);
            awS.at (ba)     = x;
            x = abs (t) < 1.18e-37 ? 0.0 : t;
            awS.at (ba + 3) = awS.at (ba + 2);
            awS.at (ba + 2) = x;
        }

        float64 ds  = abs (2.0 - ((x + nl) / nl));
        int     ii  = flip ? sb + 16 + c * 2 : sb + 17 + c * 2;
        float64 v   = abs (awS.at (ii)) < 1.18e-37 ? 0.0 : awS.at (ii);
        v = v * (1.0 - (liir * ds)) + (x * liir * ds);
        awS.at (ii) = v;
        x -= v;

        float64 dry = x;
        x = clamp (x, -1.0, 1.0);
        float64 phatS = sin (x * 1.57079633);
        x *= 1.2533141373155;
        float64 dist = sin (x * abs (x)) / (abs (x) == 0.0 ? 1.0 : abs (x));
        x = dist;

        if (dens < 1.0)
            x = dry * (1.0 - dens) + dist * dens;

        if (phat > 0.0)
            x = x * (1.0 - phat) + phatS * phat;

        int     la = sb + 20 + c * 3;
        float64 cl = (awS.at (la + 1) - awS.at (la + 2)) * 0.381966011250105;
        cl -= (awS.at (la) - awS.at (la + 1)) * 0.6180339887498948482045;
        cl += x - awS.at (la);
        awS.at (la + 2) = awS.at (la + 1);
        awS.at (la + 1) = awS.at (la);
        awS.at (la)     = x;

        if (cl > thr)  x = awS.at (la + 1) + thr;
        if (-cl > thr) x = awS.at (la + 1) - thr;

        awS.at (la) = awS.at (la) * 0.381966011250105 + x * 0.6180339887498948482045;

        if (outp < 1.0)
            x *= outp;

        if (awD.at (db + 6) > 0.5)
        {
            float64 t = awD.at (db + 10) * x + 2.0 * awD.at (db + 10) * awS.at (bb) + awD.at (db + 10) * awS.at (bb + 1)
                        - awD.at (db + 11) * awS.at (bb + 2) - awD.at (db + 12) * awS.at (bb + 3);
            awS.at (bb + 1) = awS.at (bb);
            awS.at (bb)     = x;
            x = abs (t) < 1.18e-37 ? 0.0 : t;
            awS.at (bb + 3) = awS.at (bb + 2);
            awS.at (bb + 2) = x;
        }

        return x;
    }

    float<2> fxAwChannel (int s, float<2> x)
    {
        float64 n = awNoise (s);
        bool    f = awS.at (s * 40 + 39) > 0.5;
        float64 l = awChannelCh (s, 0, float64 (x[0]) + n, f);
        float64 r = awChannelCh (s, 1, float64 (x[1]) + n, f);
        awFlip (s);
        return float<2> (float (l), float (r));
    }

    // ---- ToTape6 ----
    float64 awTapeBq (int ix, float64 x, float64 b0, float64 a1, float64 a2)
    {
        float64 t = x * b0 + awS.at (ix);
        awS.at (ix)     = -t * a1 + awS.at (ix + 1);
        awS.at (ix + 1) = -x * b0 - t * a2;
        return t;
    }

    float64 awTapeCh (int s, int c, float64 x, bool flip)
    {
        int     sb    = s * 40 + c * 12;
        int     db    = s * 24;
        float64 ig    = awD.at (db);
        float64 roll  = awD.at (db + 1);
        float64 hbc   = awD.at (db + 2);
        float64 hbf   = awD.at (db + 3);
        float64 outg  = awD.at (db + 10);
        float64 vib   = x;
        float64 highs;

        // the mid roller, head bump (two interleaved biquads) and the main biquad (see ToTape6)
        int     im = sb + (flip ? 8 : 9);
        int     ih = sb + (flip ? 10 : 11);
        int     bh = sb + (flip ? 0 : 2);
        int     bm = sb + (flip ? 4 : 6);

        awS.at (im) = awS.at (im) * (1.0 - roll) + x * roll;
        highs = x - awS.at (im);

        float64 hb = awS.at (ih) + x * 0.05;
        hb -= hb * hb * hb * hbf;
        hb = sin (hb);
        hb = awTapeBq (bh, hb, awD.at (db + 4), awD.at (db + 5), awD.at (db + 6));
        hb = asin (clamp (hb, -1.0, 1.0));
        awS.at (ih) = hb;

        x = sin (x);
        x = awTapeBq (bm, x, awD.at (db + 7), awD.at (db + 8), awD.at (db + 9));
        x = asin (clamp (x, -1.0, 1.0));

        float64 ground = vib - x;

        if (ig > 1.0)
            x *= ig;

        float64 soft = 1.0 - cos (min (abs (highs) * 1.57079633, 1.57079633));

        if (highs > 0.0) x -= soft;
        if (highs < 0.0) x += soft;

        float64 suppress = (1.0 - abs (x)) * 0.00013;
        int     ia = sb + 10;
        int     ib = sb + 11;

        if (awS.at (ia) >  suppress) awS.at (ia) -= suppress;
        if (awS.at (ia) < -suppress) awS.at (ia) += suppress;
        if (awS.at (ib) >  suppress) awS.at (ib) -= suppress;
        if (awS.at (ib) < -suppress) awS.at (ib) += suppress;

        x += (awS.at (ia) + awS.at (ib)) * hbc;
        x = clamp (x, -1.0, 1.0);

        float64 mojo = pow (abs (x), 0.25);

        if (mojo > 0.0)
            x = sin (x * mojo * 3.14159265358979 * 0.5) / mojo;

        x += ground;

        if (outg != 1.0)
            x *= outg;

        // ADClip
        float64 refclip = 0.99;
        float64 softn   = 0.618033988749894848204586;
        int     li      = s * 40 + 24 + c;
        float64 last    = awS.at (li);

        if (last >= refclip)  last = x < refclip ? refclip * softn + x * (1.0 - softn) : refclip;
        if (last <= -refclip) last = x > -refclip ? -refclip * softn + x * (1.0 - softn) : -refclip;

        if (x > refclip)  x = last < refclip ? refclip * softn + last * (1.0 - softn) : refclip;
        if (x < -refclip) x = last > -refclip ? -refclip * softn + last * (1.0 - softn) : -refclip;

        awS.at (li) = x;
        return clamp (x, -refclip, refclip);
    }

    float<2> fxAwTape (int s, float<2> x)
    {
        int     sb    = s * 40;
        int     db    = s * 24;
        int     ab    = s * 196608;
        float64 ig    = awD.at (db);
        float64 depth = awD.at (db + 11);
        float64 ft    = awD.at (db + 12);
        float64 n     = awNoise (s);
        float64 l     = float64 (x[0]) + n;
        float64 r     = float64 (x[1]) + n;
        bool    flip  = awS.at (sb + 39) > 0.5;

        if (ig < 1.0)
        {
            l *= ig;
            r *= ig;
        }

        int gc = int (awS.at (sb + 29));

        if (gc < 0 || gc > 499)
            gc = 499;

        fxArena.at (ab + gc)       = float (l);
        fxArena.at (ab + 500 + gc) = float (r);

        if (depth != 0.0)
        {
            float64 rate  = awS.at (sb + 27);
            float64 sweep = awS.at (sb + 26);
            float64 off   = depth + (depth * rate * rate * sin (sweep));
            float64 fl    = floor (off);
            float64 fr    = off - fl;
            int     i0    = (gc + int (fl)) % 500;
            int     i1    = (gc + int (fl) + 1) % 500;
            l = float64 (fxArena.at (ab + i0))       * (1.0 - fr) + float64 (fxArena.at (ab + i1))       * fr;
            r = float64 (fxArena.at (ab + 500 + i0)) * (1.0 - fr) + float64 (fxArena.at (ab + 500 + i1)) * fr;

            rate = rate * (1.0 - ft) + awS.at (sb + 28) * ft;
            sweep += rate * ft;

            if (sweep >= 6.28318530717959)
            {
                sweep -= 3.14159265358979;
                int rs = fxI.at (s * 24 + 21);
                rs = rs * 1664525 + 1013904223;
                fxI.at (s * 24 + 21) = rs;
                awS.at (sb + 28) = 0.24 + float64 ((rs >> 8) & 16777215) / 16777216.0 * 0.74;
            }

            awS.at (sb + 27) = rate;
            awS.at (sb + 26) = sweep;
        }

        awS.at (sb + 29) = float64 (gc - 1);

        float64 yl = awTapeCh (s, 0, l, flip);
        float64 yr = awTapeCh (s, 1, r, flip);
        awFlip (s);
        return float<2> (float (yl), float (yr));
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
open(P, 'w').write(src)
print('ok')
