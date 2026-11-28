#!/usr/bin/env python3
"""Idempotent, marker FX-FTAB: FX type 41 "Filter Table", built like the Kilohearts original: the spectrum of a table frame IS the filter response, applied with an FFT filter
(STFT, 1024 point FFT, Hann window, 4x overlap, latency 1024 samples, zero phase gain so the phase of the signal is kept; left and right share one complex FFT).
The frame comes from the filter table of an oscillator (load a wavetable there with FILE > "Load a wavetable as spectrum": harmonic 24 = cutoff, 9 octaves; or the 16 built-in frames).
 P1 Cutoff (frequency of harmonic 24 of the frame, 20 Hz - 20 kHz), P2 Reso (emphasises peaks and troughs: gain ^ 2^(3 r)), P3 Frame (table position), P4 Table (oscillator 1-6),
 P5 Range (octaves of the axis, 2..14, 9 = Filter Table), P6 Gain (+-12 dB).  Modes: Linear (table -1..1 -> 0..1) and dB.   Run after build_sfx.py.   build_ftx.py [patch dir]"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-FTAB' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
NT = 41
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )40\.0', r'\g<1>%d.0' % NT, src); assert n > 100, n
src, n = re.subn(r'(Euro M\d+ FX Type", min: 0\.0, max: )40\.0', r'\g<1>%d.0' % NT, src); assert n == 20, n
rep('int nt = clamp (t, 0, 40);', 'int nt = clamp (t, 0, %d);' % NT)
rep('        else if (ty == 40) y = fxSpec  (s, x);   // FX-SPEC\n', '        else if (ty == 40) y = fxSpec  (s, x);   // FX-SPEC\n        else if (ty == 41) y = fxFtab  (s, x);   // FX-FTAB\n')
rep('        else if (ty == 40)\n        {\n            // FX-SPEC:', '''        else if (ty == 41)
        {
            // FX-FTAB: log2 cutoff, reso exponent, frame position, table bank, range (octaves), output gain
            fxD.at (db)     = float (log (fxExpMap (p1, 20.0f, 20000.0f))) * 1.442695f;
            fxD.at (db + 1) = float (pow (2.0f, p2 * 3.0f));
            fxD.at (db + 2) = p3;
            fxD.at (db + 3) = float (clamp (int (p4 * 5.0f + 0.5f), 0, 5));
            fxD.at (db + 4) = 2.0f + 12.0f * p5;
            fxD.at (db + 5) = float (pow (10.0f, (clamp (fxP.at (pb + 5), 0.0f, 1.0f) * 2.0f - 1.0f) * 0.6f));
        }
        else if (ty == 40)
        {
            // FX-SPEC:''')
rep('    int64        sfxRnd;\n', '''    int64        sfxRnd;
    float[196608] ftxV;  // FX-FTAB: per slot 4096 floats: input ring L / R (0..2047), overlap-add ring L / R (2048..4095)
    float[512]   ftxCos;
    float[512]   ftxSin;
    float[1024]  ftxWin;
    int[1024]    ftxRev;
    float[1024]  ftxZr;
    float[1024]  ftxZi;
    float[520]   ftxG;
    int[64]      ftxP;
    int          ftxInit;
''')
CODE = '''    // ================= FX-FTAB: Filter Table effect (FX type 41) =================
    void fxFtInit()
    {
        for (int i = 0; i < 512; ++i)
        {
            ftxCos.at (i) = float (cos (6.2831853f * float (i) / 1024.0f));
            ftxSin.at (i) = float (sin (6.2831853f * float (i) / 1024.0f));
        }

        for (int i = 0; i < 1024; ++i)
        {
            ftxWin.at (i) = 0.5f - 0.5f * float (cos (6.2831853f * (float (i) + 0.5f) / 1024.0f));

            int j = 0;
            int t = i;

            for (int b = 0; b < 10; ++b)
            {
                j = (j << 1) | (t & 1);
                t = t >> 1;
            }

            ftxRev.at (i) = j;
        }

        ftxInit = 1;
    }

    void fxFtFft (float dir)
    {
        for (int i = 0; i < 1024; ++i)
        {
            int j = ftxRev.at (i);

            if (j > i)
            {
                float tr = ftxZr.at (i);
                float ti = ftxZi.at (i);
                ftxZr.at (i) = ftxZr.at (j);
                ftxZi.at (i) = ftxZi.at (j);
                ftxZr.at (j) = tr;
                ftxZi.at (j) = ti;
            }
        }

        int len = 2;

        for (int st = 0; st < 10; ++st)
        {
            int half = len >> 1;
            int step = 1024 / len;

            for (int i = 0; i < 1024; i += len)
            {
                for (int k = 0; k < half; ++k)
                {
                    float wr = ftxCos.at (k * step);
                    float wi = dir * ftxSin.at (k * step);
                    int   a  = i + k;
                    int   b  = a + half;
                    float vr = ftxZr.at (b) * wr - ftxZi.at (b) * wi;
                    float vi = ftxZr.at (b) * wi + ftxZi.at (b) * wr;
                    float ur = ftxZr.at (a);
                    float ui = ftxZi.at (a);
                    ftxZr.at (a) = ur + vr;
                    ftxZi.at (a) = ui + vi;
                    ftxZr.at (b) = ur - vr;
                    ftxZi.at (b) = ui - vi;
                }
            }

            len = len << 1;
        }
    }

    // the response of the frame: bin k (frequency k * fs / 1024) -> gain; the axis is log2 (f / cutoff) / range around the middle of the frame
    void fxFtGains (int s)
    {
        int   db    = s * 16;
        float lfc   = fxD.at (db);
        float ex    = fxD.at (db + 1);
        float pos   = fxD.at (db + 2);
        int   bank  = int (fxD.at (db + 3) + 0.5f);
        float width = fxD.at (db + 4);
        float og    = fxD.at (db + 5);
        int   law   = clamp (fxMode.at (s), 0, 1);
        float binHz = float (processor.frequency) / 1024.0f;

        for (int k = 0; k < 513; ++k)
        {
            float f = max (float (k), 1.0f) * binHz;
            float x = clamp (0.5f + (float (log (f)) * 1.442695f - lfc) / width, 0.0f, 1.0f);
            float v = tblRead (bank, pos, x);
            float g = law == 0 ? v * 0.5f + 0.5f : float (pow (10.0f, (v - 1.0f) * 1.5f));
            g = max (g, 0.0f);

            if (ex > 1.001f)
                g = float (pow (g, ex));

            ftxG.at (k) = g * og;
        }
    }

    void fxFtFrame (int s, int wp)
    {
        int vb = s * 4096;

        for (int n = 0; n < 1024; ++n)
        {
            int   ix = (wp + n) & 1023;
            float w  = ftxWin.at (n);
            ftxZr.at (n) = ftxV.at (vb + ix) * w;
            ftxZi.at (n) = ftxV.at (vb + 1024 + ix) * w;
        }

        fxFtFft (-1.0f);
        fxFtGains (s);

        // a real, symmetric gain acts on the packed (L + i R) spectrum exactly as on both channels
        for (int k = 0; k < 1024; ++k)
        {
            float g = ftxG.at (k <= 512 ? k : 1024 - k);
            ftxZr.at (k) = ftxZr.at (k) * g;
            ftxZi.at (k) = ftxZi.at (k) * g;
        }

        fxFtFft (1.0f);

        for (int n = 0; n < 1024; ++n)
        {
            int   ix = (wp + n) & 1023;
            float w  = ftxWin.at (n) * 0.00065104167f;   // 1 / (1024 * 1.5)
            ftxV.at (vb + 2048 + ix) += ftxZr.at (n) * w;
            ftxV.at (vb + 3072 + ix) += ftxZi.at (n) * w;
        }
    }

    float<2> fxFtab (int s, float<2> x)
    {
        if (s >= 48)
            return x;

        if (ftxInit == 0)
            fxFtInit();

        int vb = s * 4096;
        int wp = ftxP.at (s);
        ftxV.at (vb + wp)        = x[0];
        ftxV.at (vb + 1024 + wp) = x[1];
        float<2> y = float<2> (ftxV.at (vb + 2048 + wp), ftxV.at (vb + 3072 + wp));
        ftxV.at (vb + 2048 + wp) = 0.0f;
        ftxV.at (vb + 3072 + wp) = 0.0f;
        wp = (wp + 1) & 1023;
        ftxP.at (s) = wp;

        if ((wp & 255) == 0)
            fxFtFrame (s, wp);

        return y;
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
rep('        if (s < 48)   // FX-SPEC\n', '''        if (s < 48)   // FX-FTAB
        {
            for (int i = 0; i < 4096; ++i)
                ftxV.at (s * 4096 + i) = 0.0f;

            ftxP.at (s) = 0;
        }

        if (s < 48)   // FX-SPEC
''')
m = re.search(r'const int\[164\] fxExTab = \(([^)]*)\);', src); assert m
tab = [int(v) for v in m.group(1).split(',')]; assert len(tab) == 164
tab += [3, 7, 8, 11]
src = src[:m.start()] + 'const int[168] fxExTab = (' + ', '.join(str(v) for v in tab) + ');' + src[m.end():]
hp = os.path.join(root, 'native_ui', 'NjoFxEx.h'); h = open(hp).read()
m = re.search(r'static const int tab\[164\] = \{ ([^}]*) \};', h); assert m
h = h[:m.start()] + 'static const int tab[168] = { ' + ', '.join(str(v) for v in tab) + ' };' + h[m.end():]
open(hp, 'w').write(h)
entry = '''    // FX-FTAB: Filter Table as in the Kilohearts original: the spectrum of a table frame is the filter response (FFT filter, FX type 41)
    { n: "Filter Table", mix: 1, modes: ["Linear", "dB"],
      p: [["Cutoff", fxHz(20, 20000), 0.5], ["Reso", fxPct, 0], ["Frame", fxPct, 0], ["Table", fxLin(1, 6, 0, ""), 0], ["Range", fxLin(2, 14, 1, "oct"), 0.583], ["Gain", fxDb(-12, 12), 0.5]] },
'''
mm = re.search(r'\n\];\n// the three racks', idx); assert mm
idx = idx[:mm.start() + 1] + entry + idx[mm.start() + 1:]
src += '\n// FX-FTAB\n'
open(P, 'w').write(src); open(IP, 'w').write(idx); print('FX-FTAB applied')
