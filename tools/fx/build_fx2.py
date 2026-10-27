#!/usr/bin/env python3
"""Idempotent: extra algorithms / parameters of the existing effects (distortion, bit crush, delay, chorus, flanger, phaser,
reverb, EQ, compressor) in patch/Eisenpuls_Synth.cmajor.  Run after build_fx.py."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if '// FX-EXT' in src:
    print('already applied'); sys.exit(0)

def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:60], src.count(old))
    src = src.replace(old, new)

# ---- shaper algorithms 6..8
rep('''        else if (al == 5)
        {
            // crunch''', '''        else if (al == 6)
        {
            // rectify (FX-EXT): half-wave, even harmonics
            y = xx > 0.0f ? xx / (1.0f + xx) * 1.4f : 0.0f;
        }
        else if (al == 7)
        {
            // fuzz: gated hard clip with a square-ish core
            float g3 = clamp (xx * 3.0f, -1.0f, 1.0f);
            y = g3 * (0.6f + 0.4f * abs (g3)) * (abs (xx) < 0.02f ? abs (xx) * 50.0f : 1.0f);
        }
        else if (al == 8)
        {
            y = float (tanh (xx));
        }
        else if (al == 5)
        {
            // crunch''')

# ---- derive
rep('''            fxD.at (db + 2) = p3 * 2.0f;
        }
        else if (ty == 2)''', '''            fxD.at (db + 2) = p3 * 2.0f;
            fxD.at (db + 3) = (clamp (fxP.at (pb + 3), 0.0f, 1.0f) - 0.5f) * 1.2f;                                   // bias
            fxD.at (db + 4) = clamp (float (twoPi) * fxExpMap (p5, 10.0f, 800.0f) * dt, 0.0f, 1.0f);                // low cut
            fxD.at (db + 5) = clamp (fxP.at (pb + 5), 0.0f, 1.0f) * 1.5f;                                            // presence
        }
        else if (ty == 2)''')
rep('''            fxD.at (db + 2) = float (pow (2.0f, fxD.at (db) - 1.0f));
        }''', '''            fxD.at (db + 2) = float (pow (2.0f, fxD.at (db) - 1.0f));
            fxD.at (db + 3) = p3;      // dither
            fxD.at (db + 4) = p4;      // jitter
        }''')
rep('''            fxD.at (db + 3) = p4;
        }
        else if (ty == 4)
        {
            fxD.at (db)     = fxExpMap (p1, 0.05f, 5.0f);
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = 0.9f * p3;
        }
        else if (ty == 5)
        {
            fxD.at (db)     = fxExpMap (p1, 0.05f, 5.0f);
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = 0.95f * p3;
        }
        else if (ty == 6)
        {
            fxD.at (db)     = fxExpMap (p1, 0.05f, 8.0f);
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = 0.9f * p3;
        }''', '''            fxD.at (db + 3) = p4;
            fxD.at (db + 4) = p5 * 0.004f * sr;                                                           // time modulation (samples)
            fxD.at (db + 5) = clamp (float (twoPi) * fxExpMap (clamp (fxP.at (pb + 5), 0.0f, 1.0f), 20.0f, 1000.0f) * dt, 0.0f, 1.0f);   // feedback low cut
        }
        else if (ty == 4)
        {
            fxD.at (db)     = fxExpMap (p1, 0.05f, 5.0f);
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = 0.9f * p3;
            fxD.at (db + 6) = p4 * 2.0f;      // width of the wet signal
        }
        else if (ty == 5)
        {
            fxD.at (db)     = fxExpMap (p1, 0.05f, 5.0f);
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = (fxMode.at (s) == 1 ? -0.95f : 0.95f) * p3;     // mode 1: negative feedback
            fxD.at (db + 6) = p4 * 2.0f;
        }
        else if (ty == 6)
        {
            fxD.at (db)     = fxExpMap (p1, 0.05f, 8.0f);
            fxD.at (db + 1) = p2;
            fxD.at (db + 2) = 0.9f * p3;
            fxD.at (db + 6) = p4 * 2.0f;
        }''')
# reverb tone filters, in derive
rep('''            fxD.at (db + 3) = p4;
        }
        else if (ty == 9)''', '''            fxD.at (db + 3) = p4;
            fxD.at (db + 6) = clamp (float (twoPi) * fxExpMap (p5, 20.0f, 800.0f) * dt, 0.0f, 1.0f);       // wet low cut
            fxD.at (db + 7) = clamp (float (twoPi) * fxExpMap (clamp (fxP.at (pb + 5), 0.0f, 1.0f), 1500.0f, 20000.0f) * dt, 0.0f, 1.0f);   // wet high cut
        }
        else if (ty == 9)''')
rep("fxBiquad (db + 10, 2, (p4 - 0.5f) * 24.0f, 8000.0f, 0.7f);", "fxBiquad (db + 10, 2, (p4 - 0.5f) * 24.0f, fxExpMap (clamp (fxP.at (pb + 5), 0.0f, 1.0f), 4000.0f, 16000.0f), 0.7f);")
rep('''            fxD.at (db + 4) = float (pow (10.0f, 24.0f * p5 / 20.0f));
        }''', '''            fxD.at (db + 4) = float (pow (10.0f, 24.0f * p5 / 20.0f));
            fxD.at (db + 5) = 12.0f * clamp (fxP.at (pb + 5), 0.0f, 1.0f);                       // knee width (dB)
        }''')

# ---- distortion
rep('''        float yl = shapeSigAlg (x[0] * 0.5f, d, al) * 2.0f;
        float yr = shapeSigAlg (x[1] * 0.5f, d, al) * 2.0f;

        float tl = fxF.at (fb)     + a * (yl - fxF.at (fb));
        float tr = fxF.at (fb + 1) + a * (yr - fxF.at (fb + 1));
        fxF.at (fb)     = tl;
        fxF.at (fb + 1) = tr;

        return float<2> (tl * g, tr * g);''', '''        // low cut before the shaper, bias into it
        float lc  = fxD.at (db + 4);
        float lpl = fxF.at (fb + 30) + lc * (x[0] - fxF.at (fb + 30));
        float lpr = fxF.at (fb + 31) + lc * (x[1] - fxF.at (fb + 31));
        fxF.at (fb + 30) = lpl;
        fxF.at (fb + 31) = lpr;
        float bias = fxD.at (db + 3);

        float yl = shapeSigAlg ((x[0] - lpl) * 0.5f + bias * 0.5f, d, al) * 2.0f;
        float yr = shapeSigAlg ((x[1] - lpr) * 0.5f + bias * 0.5f, d, al) * 2.0f;

        float tl = fxF.at (fb)     + a * (yl - fxF.at (fb));
        float tr = fxF.at (fb + 1) + a * (yr - fxF.at (fb + 1));
        fxF.at (fb)     = tl;
        fxF.at (fb + 1) = tr;

        // presence: the part above about 2.3 kHz boosted
        float pl = fxF.at (fb + 32) + 0.3f * (tl - fxF.at (fb + 32));
        float pr = fxF.at (fb + 33) + 0.3f * (tr - fxF.at (fb + 33));
        fxF.at (fb + 32) = pl;
        fxF.at (fb + 33) = pr;
        float pres = fxD.at (db + 5);
        tl = tl + pres * (tl - pl);
        tr = tr + pres * (tr - pr);

        // DC blocker (bias and rectification add an offset)
        float dl = fxF.at (fb + 28) + 0.0015f * (tl - fxF.at (fb + 28));
        float dr = fxF.at (fb + 29) + 0.0015f * (tr - fxF.at (fb + 29));
        fxF.at (fb + 28) = dl;
        fxF.at (fb + 29) = dr;

        return float<2> ((tl - dl) * g, (tr - dr) * g);''')

# ---- bit crush
rep('''        int cnt = fxI.at (ib) + 1;

        if (cnt >= int (fxD.at (db + 1)))
        {
            cnt = 0;
            fxF.at (fb)     = x[0];
            fxF.at (fb + 1) = x[1];
        }

        fxI.at (ib) = cnt;

        float yl = fxF.at (fb);
        float yr = fxF.at (fb + 1);

        if (fxD.at (db) < 15.5f)
        {
            float lv = fxD.at (db + 2);
            yl = rint (yl * lv) / lv;
            yr = rint (yr * lv) / lv;
        }
''', '''        int cnt = fxI.at (ib) + 1;
        int cm  = fxMode.at (s);

        // small LCG for dither / jitter
        int rs = (fxI.at (ib + 1) * 1103515245 + 12345) & 0x7fffffff;
        int rt = (rs * 1103515245 + 12345) & 0x7fffffff;
        fxI.at (ib + 1) = rt;
        float r1 = float (rs) / 2147483648.0f;
        float r2 = float (rt) / 2147483648.0f;

        if (fxI.at (ib + 2) < 1)
            fxI.at (ib + 2) = 1;

        if (cnt >= fxI.at (ib + 2))
        {
            cnt = 0;
            fxF.at (fb)     = x[0];
            fxF.at (fb + 1) = x[1];
            fxI.at (ib + 2) = max (1, int (fxD.at (db + 1) * (1.0f + fxD.at (db + 4) * (r1 * 2.0f - 1.0f))));
        }

        fxI.at (ib) = cnt;

        float yl = fxF.at (fb);
        float yr = fxF.at (fb + 1);

        if (fxD.at (db) < 15.5f)
        {
            float lv = fxD.at (db + 2);
            float dz = fxD.at (db + 3) * (r1 - r2) / lv;

            if (cm == 1)
            {
                // mu-law: companded quantiser (finer steps for quiet signals)
                float mu = 60.0f;
                float cl = (yl < 0.0f ? -1.0f : 1.0f) * float (log (1.0f + mu * min (1.0f, abs (yl)))) / float (log (1.0f + mu));
                float cr = (yr < 0.0f ? -1.0f : 1.0f) * float (log (1.0f + mu * min (1.0f, abs (yr)))) / float (log (1.0f + mu));
                cl = rint ((cl + dz) * lv) / lv;
                cr = rint ((cr + dz) * lv) / lv;
                yl = (cl < 0.0f ? -1.0f : 1.0f) * (float (exp (abs (cl) * float (log (1.0f + mu)))) - 1.0f) / mu;
                yr = (cr < 0.0f ? -1.0f : 1.0f) * (float (exp (abs (cr) * float (log (1.0f + mu)))) - 1.0f) / mu;
            }
            else if (cm == 2)
            {
                // floor: truncating quantiser (asymmetric, gritty)
                yl = floor ((yl + dz) * lv) / lv;
                yr = floor ((yr + dz) * lv) / lv;
            }
            else
            {
                yl = rint ((yl + dz) * lv) / lv;
                yr = rint ((yr + dz) * lv) / lv;
            }
        }
''')

# ---- delay: time modulation + feedback low cut
rep('''        int   wp   = fxI.at (ib);
        float rpos = float (wp) - cur - tapeMod;''', '''        float dmod = 0.0f;

        if (fxD.at (db + 4) > 0.5f)
        {
            float64 t3 = fxPh.at (pb + 2) + 0.7 * processor.period;
            if (t3 >= 1.0) t3 -= 1.0;
            fxPh.at (pb + 2) = t3;
            dmod = fxD.at (db + 4) * float (sin (float (twoPi) * float (t3)));
        }

        int   wp   = fxI.at (ib);
        float rpos = float (wp) - cur - tapeMod - dmod;''')
rep('''        float fbSendL = fbSameL;
        float fbSendR = fbSameR;
''', '''        float hpc     = fxD.at (db + 5);
        float hpl     = fxF.at (fb + 34) + hpc * (fbSameL - fxF.at (fb + 34));
        float hpr     = fxF.at (fb + 35) + hpc * (fbSameR - fxF.at (fb + 35));
        fxF.at (fb + 34) = hpl;
        fxF.at (fb + 35) = hpr;
        float fbSendL = fbSameL - hpl;
        float fbSendR = fbSameR - hpr;
''')

# ---- post processing of the wet signal (width of the modulation effects, reverb tone, delay ducking)
rep('''        else if (ty == 12) y = fxConv   (s, x);
''', '''        else if (ty == 12) y = fxConv   (s, x);

        // FX-EXT: wet-signal post processing
        if (ty >= 4 && ty <= 6)
        {
            float md = (y[0] + y[1]) * 0.5f;
            float sd = (y[0] - y[1]) * 0.5f * fxD.at (s * 16 + 6);
            y = float<2> (md + sd, md - sd);
        }
        else if (ty == 8)
        {
            int   fb = s * 40;
            int   db = s * 16;
            float l1 = fxF.at (fb + 36) + fxD.at (db + 7) * (y[0] - fxF.at (fb + 36));
            float r1 = fxF.at (fb + 37) + fxD.at (db + 7) * (y[1] - fxF.at (fb + 37));
            fxF.at (fb + 36) = l1;
            fxF.at (fb + 37) = r1;
            float l2 = fxF.at (fb + 38) + fxD.at (db + 6) * (l1 - fxF.at (fb + 38));
            float r2 = fxF.at (fb + 39) + fxD.at (db + 6) * (r1 - fxF.at (fb + 39));
            fxF.at (fb + 38) = l2;
            fxF.at (fb + 39) = r2;
            y = float<2> (l1 - l2, r1 - r2);
        }
        else if (ty == 3 && fxMode.at (s) == 3)
        {
            // ducking delay: the echoes drop while the input plays and swell back when it stops
            int   fb  = s * 40;
            float det = max (abs (x[0]), abs (x[1]));
            float en  = fxF.at (fb + 36);
            en += (det > en ? 0.01f : 0.0002f) * (det - en);
            fxF.at (fb + 36) = en;
            y = y * (1.0f / (1.0f + en * 12.0f));
        }
''')

# ---- compressor soft knee
rep('''        float gain = 1.0f;
        if (lvl > th)
            gain = float (pow (lvl / th, fxD.at (db + 1)));
''', '''        float gain = 1.0f;
        float kw   = fxD.at (db + 5);

        if (kw < 0.1f)
        {
            if (lvl > th)
                gain = float (pow (lvl / th, fxD.at (db + 1)));
        }
        else if (lvl > 0.00001f)
        {
            // quadratic soft knee in the dB domain
            float lv  = 8.6859f * float (log (lvl / th));
            float ex  = fxD.at (db + 1);
            float red = 0.0f;

            if (lv * 2.0f > kw)
                red = ex * lv;
            else if (lv * 2.0f > -kw)
                red = ex * (lv + kw * 0.5f) * (lv + kw * 0.5f) / (2.0f * kw);

            gain = float (exp (red / 8.6859f));
        }
''')
rep("    // ---------------- one function per effect", "    // FX-EXT marker\n    // ---------------- one function per effect") if False else None
src += ''
open(path, 'w').write(src.replace('// FX-CONV', '// FX-CONV', 1) + '') if False else None
src = src.replace('    // FX-EXT: wet', '    // FX-EXT: wet', 1)
open(path, 'w').write(src)
print('ok')
