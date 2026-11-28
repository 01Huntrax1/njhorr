#!/usr/bin/env python3
"""Idempotent, marker FX-SPEC: FX type 40 "Spectral": an FFT effect (STFT, 512 point FFT, Hann window, 4x overlap, hop 128, latency 512 samples).
Left and right are packed into ONE complex FFT (re = L, im = R) and separated again in the spectrum, so one forward and one inverse FFT per hop serve both channels.
Modes: Shape (tilt, shift, low / high cut), Freeze (holds the spectrum while Amount > 50 %, phases keep running), Gate (spectral gate), Robot (zero phase), Whisper (random phase).
 P1 Amount (Freeze: hold above 50 %, Gate: threshold, Robot / Whisper: blend), P2 Tilt, P3 Shift (+-1 octave, bin remap), P4 Lo Cut, P5 Hi Cut, P6 Floor (Gate: level of the gated bins).
Only the global slots (0..47) have the memory for it (4096 floats per slot); in the per voice racks of the oscillators and the Euro modules the type passes the signal through.   build_sfx.py [patch dir]"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-SPEC' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
NT = 40
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )39\.0', r'\g<1>%d.0' % NT, src); assert n > 100, n
src, n = re.subn(r'(Euro M\d+ FX Type", min: 0\.0, max: )39\.0', r'\g<1>%d.0' % NT, src); assert n == 20, n
rep('int nt = clamp (t, 0, 39);', 'int nt = clamp (t, 0, %d);' % NT)
rep('        else if (ty == 39) y = fxWfilt (s, x);   // FX-WFILT\n', '        else if (ty == 39) y = fxWfilt (s, x);   // FX-WFILT\n        else if (ty == 40) y = fxSpec  (s, x);   // FX-SPEC\n')
rep('        else if (ty == 39)\n        {\n            // FX-WFILT:', '''        else if (ty == 40)
        {
            // FX-SPEC: amount, tilt exponent, shift ratio, low cut bin, high cut bin, floor
            fxD.at (db)     = p1;
            fxD.at (db + 1) = p2 * 2.0f - 1.0f;
            fxD.at (db + 2) = float (pow (2.0f, p3 * 2.0f - 1.0f));
            fxD.at (db + 3) = p4 * p4 * 200.0f;
            fxD.at (db + 4) = 256.0f * float (pow (0.03125f, p5));
            fxD.at (db + 5) = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        }
        else if (ty == 39)
        {
            // FX-WFILT:''')
rep('    float[32768] fxF;  // padded to a power of two (cheap index wrap)\n', '''    float[32768] fxF;  // padded to a power of two (cheap index wrap)
    float[196608] sfxV;  // FX-SPEC: per slot 4096 floats: input ring L / R (0..1023), overlap-add ring L / R (1024..2047), held magnitudes (2048..2561) and phases (2562..3075), freeze flag (3080)
    float[256]   sfxCos;
    float[256]   sfxSin;
    float[512]   sfxWin;
    int[512]     sfxRev;
    float[512]   sfxZr;
    float[512]   sfxZi;
    float[520]   sfxXr;  // the two channels split from the FFT (260 per channel), processed in place
    float[520]   sfxXi;
    float[520]   sfxOr;
    float[520]   sfxOi;
    int[64]      sfxP;   // write position per slot
    int          sfxInit;
    int64        sfxRnd;
''')
CODE = '''    // ================= FX-SPEC: Spectral effect (FX type 40) =================
    void fxSpecInit()
    {
        for (int i = 0; i < 256; ++i)
        {
            sfxCos.at (i) = float (cos (6.2831853f * float (i) / 512.0f));
            sfxSin.at (i) = float (sin (6.2831853f * float (i) / 512.0f));
        }

        for (int i = 0; i < 512; ++i)
        {
            sfxWin.at (i) = 0.5f - 0.5f * float (cos (6.2831853f * (float (i) + 0.5f) / 512.0f));

            int j = 0;
            int t = i;

            for (int b = 0; b < 9; ++b)
            {
                j = (j << 1) | (t & 1);
                t = t >> 1;
            }

            sfxRev.at (i) = j;
        }

        sfxRnd = 12345L;
        sfxInit = 1;
    }

    // in place on sfxZr / sfxZi (512 points); dir -1 forward, +1 inverse, not normalised
    void fxSpecFft (float dir)
    {
        for (int i = 0; i < 512; ++i)
        {
            int j = sfxRev.at (i);

            if (j > i)
            {
                float tr = sfxZr.at (i);
                float ti = sfxZi.at (i);
                sfxZr.at (i) = sfxZr.at (j);
                sfxZi.at (i) = sfxZi.at (j);
                sfxZr.at (j) = tr;
                sfxZi.at (j) = ti;
            }
        }

        int len = 2;

        for (int st = 0; st < 9; ++st)
        {
            int half = len >> 1;
            int step = 512 / len;

            for (int i = 0; i < 512; i += len)
            {
                for (int k = 0; k < half; ++k)
                {
                    float wr = sfxCos.at (k * step);
                    float wi = dir * sfxSin.at (k * step);
                    int   a  = i + k;
                    int   b  = a + half;
                    float vr = sfxZr.at (b) * wr - sfxZi.at (b) * wi;
                    float vi = sfxZr.at (b) * wi + sfxZi.at (b) * wr;
                    float ur = sfxZr.at (a);
                    float ui = sfxZi.at (a);
                    sfxZr.at (a) = ur + vr;
                    sfxZi.at (a) = ui + vi;
                    sfxZr.at (b) = ur - vr;
                    sfxZi.at (b) = ui - vi;
                }
            }

            len = len << 1;
        }
    }

    float sfxRand()
    {
        sfxRnd = (sfxRnd * 22695477L + 1L) & 4294967295L;
        return float (sfxRnd) / 4294967295.0f;
    }

    // one channel of the spectrum (260 values at o in sfxXr / sfxXi) -> sfxOr / sfxOi
    void fxSpecProc (int s, int c, int mode)
    {
        int   db   = s * 16;
        int   o    = c * 260;
        int   vb   = s * 4096;
        float amt  = fxD.at (db);
        float tilt = fxD.at (db + 1);
        float rat  = fxD.at (db + 2);
        float lo   = fxD.at (db + 3);
        float hi   = fxD.at (db + 4);
        float flo  = fxD.at (db + 5);
        float peak = 0.0f;
        bool  held = mode == 1 && amt > 0.5f;
        bool  cap  = held && sfxV.at (vb + 3080) < 0.5f;

        for (int k = 0; k < 257; ++k)
        {
            sfxOr.at (o + k) = 0.0f;
            sfxOi.at (o + k) = 0.0f;
        }

        if (mode == 2)
        {
            for (int k = 1; k < 257; ++k)
                peak = max (peak, sqrt (sfxXr.at (o + k) * sfxXr.at (o + k) + sfxXi.at (o + k) * sfxXi.at (o + k)));
        }

        for (int k = 1; k < 257; ++k)
        {
            float g = 1.0f;

            if (float (k) < lo || float (k) > hi)
                g = 0.0f;
            else if (tilt != 0.0f)
                g = clamp (float (pow (float (k) * 0.0625f, tilt)), 0.0f, 8.0f);

            float xr  = sfxXr.at (o + k);
            float xi  = sfxXi.at (o + k);
            float mag = sqrt (xr * xr + xi * xi);

            if (mode == 0)
            {
                int k2 = int (float (k) * rat + 0.5f);

                if (k2 >= 1 && k2 < 257)
                {
                    sfxOr.at (o + k2) += xr * g;
                    sfxOi.at (o + k2) += xi * g;
                }
            }
            else if (mode == 1)
            {
                int mi = vb + 2048 + c * 257 + k;
                int pi = vb + 2562 + c * 257 + k;

                if (cap)
                {
                    sfxV.at (mi) = mag;
                    sfxV.at (pi) = float (atan2 (xi, xr));
                }

                if (held)
                {
                    float ph = sfxV.at (pi) + 1.5707963f * float (k);
                    ph = ph - 6.2831853f * float (int (ph * 0.15915494f));
                    sfxV.at (pi) = ph;
                    sfxOr.at (o + k) = sfxV.at (mi) * g * float (cos (ph));
                    sfxOi.at (o + k) = sfxV.at (mi) * g * float (sin (ph));
                }
                else
                {
                    sfxOr.at (o + k) = xr * g;
                    sfxOi.at (o + k) = xi * g;
                }
            }
            else if (mode == 2)
            {
                float thr = peak * amt * amt * 0.5f;
                float gg  = mag < thr ? flo * flo : 1.0f;
                sfxOr.at (o + k) = xr * g * gg;
                sfxOi.at (o + k) = xi * g * gg;
            }
            else if (mode == 3)
            {
                float tg = (k & 1) == 1 ? -mag : mag;   // zero phase, shifted by half a frame so the pulse sits in the middle of the window
                sfxOr.at (o + k) = (xr + (tg - xr) * amt) * g;
                sfxOi.at (o + k) = xi * (1.0f - amt) * g;
            }
            else
            {
                float rp = 6.2831853f * sfxRand();
                sfxOr.at (o + k) = (xr + (mag * float (cos (rp)) - xr) * amt) * g;
                sfxOi.at (o + k) = (xi + (mag * float (sin (rp)) - xi) * amt) * g;
            }
        }

        if (mode == 1)
            sfxV.at (vb + 3080) = held ? 1.0f : 0.0f;
    }

    void fxSpecFrame (int s, int wp, int mode)
    {
        int vb = s * 4096;

        for (int n = 0; n < 512; ++n)
        {
            int   ix = (wp + n) & 511;
            float w  = sfxWin.at (n);
            sfxZr.at (n) = sfxV.at (vb + ix) * w;
            sfxZi.at (n) = sfxV.at (vb + 512 + ix) * w;
        }

        fxSpecFft (-1.0f);

        for (int k = 0; k < 257; ++k)
        {
            int k2 = (512 - k) & 511;
            sfxXr.at (k)       = 0.5f * (sfxZr.at (k) + sfxZr.at (k2));
            sfxXi.at (k)       = 0.5f * (sfxZi.at (k) - sfxZi.at (k2));
            sfxXr.at (260 + k) = 0.5f * (sfxZi.at (k) + sfxZi.at (k2));
            sfxXi.at (260 + k) = -0.5f * (sfxZr.at (k) - sfxZr.at (k2));
        }

        fxSpecProc (s, 0, mode);
        fxSpecProc (s, 1, mode);

        // Y = YL + i YR (and the mirrored half as the conjugate pair)
        for (int k = 0; k < 257; ++k)
        {
            float lr = sfxOr.at (k);
            float li = sfxOi.at (k);
            float rr = sfxOr.at (260 + k);
            float ri = sfxOi.at (260 + k);
            sfxZr.at (k) = lr - ri;
            sfxZi.at (k) = li + rr;

            if (k > 0 && k < 256)
            {
                sfxZr.at (512 - k) = lr + ri;
                sfxZi.at (512 - k) = rr - li;
            }
        }

        fxSpecFft (1.0f);

        for (int n = 0; n < 512; ++n)
        {
            int   ix = (wp + n) & 511;
            float w  = sfxWin.at (n) * 0.0013020833f;   // 1 / (512 * 1.5)
            sfxV.at (vb + 1024 + ix) += sfxZr.at (n) * w;
            sfxV.at (vb + 1536 + ix) += sfxZi.at (n) * w;
        }
    }

    float<2> fxSpec (int s, float<2> x)
    {
        if (s >= 48)
            return x;

        if (sfxInit == 0)
            fxSpecInit();

        int vb = s * 4096;
        int wp = sfxP.at (s);
        sfxV.at (vb + wp)       = x[0];
        sfxV.at (vb + 512 + wp) = x[1];
        float<2> y = float<2> (sfxV.at (vb + 1024 + wp), sfxV.at (vb + 1536 + wp));
        sfxV.at (vb + 1024 + wp) = 0.0f;
        sfxV.at (vb + 1536 + wp) = 0.0f;
        wp = (wp + 1) & 511;
        sfxP.at (s) = wp;

        if ((wp & 127) == 0)
            fxSpecFrame (s, wp, clamp (fxMode.at (s), 0, 4));

        return y;
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
rep('        fxFcS.at (s) = 0.0f;   // FX-FENV2\n', '''        fxFcS.at (s) = 0.0f;   // FX-FENV2

        if (s < 48)   // FX-SPEC
        {
            for (int i = 0; i < 4096; ++i)
                sfxV.at (s * 4096 + i) = 0.0f;

            sfxP.at (s) = 0;
        }
''')
# tool table: 40 types x 4 -> 41 x 4 (same tools as the Wavefilter: Pre HP, Pre LP, Gate, Trim)
m = re.search(r'const int\[160\] fxExTab = \(([^)]*)\);', src); assert m
tab = [int(v) for v in m.group(1).split(',')]; assert len(tab) == 160
tab += [3, 7, 8, 11]
src = src[:m.start()] + 'const int[164] fxExTab = (' + ', '.join(str(v) for v in tab) + ');' + src[m.end():]
hp = os.path.join(root, 'native_ui', 'NjoFxEx.h'); h = open(hp).read()
m = re.search(r'static const int tab\[160\] = \{ ([^}]*) \};', h); assert m
h = h[:m.start()] + 'static const int tab[164] = { ' + ', '.join(str(v) for v in tab) + ' };' + h[m.end():]
open(hp, 'w').write(h)
entry = '''    // FX-SPEC: FFT effect (FX type 40), STFT with 512 points, latency 512 samples
    { n: "Spectral", mix: 1, modes: ["Shape", "Freeze", "Gate", "Robot", "Whisper"],
      p: [["Amount", fxPct, 0.5], ["Tilt", fxLin(-100, 100, 0, "%"), 0.5], ["Shift", fxLin(-12, 12, 0, "st"), 0.5], ["Lo Cut", fxPct, 0], ["Hi Cut", fxPct, 0], ["Floor", fxPct, 0]] },
'''
mm = re.search(r'\n\];\n// the three racks', idx); assert mm
idx = idx[:mm.start() + 1] + entry + idx[mm.start() + 1:]
src += '\n// FX-SPEC\n'
open(P, 'w').write(src); open(IP, 'w').write(idx); print('FX-SPEC applied')
