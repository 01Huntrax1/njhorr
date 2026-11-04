#!/usr/bin/env python3
"""Idempotent: FX type 18 "Filterbank", marker FX-FBANK (after the Sherman Filterbank).
Two multimode state-variable filters (zero-delay feedback).  Response control P3 sweeps LP -> BP -> HP continuously, P4 "Anti-Mix" crossfades
the response towards the notch (LP+HP-BP), filter 2 is tuned P6 semitones (-24..+24) away from filter 1 (harmonic sync) and is slightly more resonant.
P1 Freq (filter 1), P2 Reso, P3 Response, P4 Anti-Mix, P5 Drive (input overdrive, in front of the filters), P6 F2 Offset.
Modes: Parallel, Series, Blend (parallel and series 50:50); the "Mirror" modes run filter 2 with the mirrored response (LP <-> HP).
Modulation of any parameter (also an envelope follower or an LFO) comes from the modulation matrix.
State: fxF fb+0/1 filter 1 left, fb+2/3 filter 2 (parallel), fb+4/5 filter 2 (series), +8 for the right channel."""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'FX-FBANK' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )17\.0', r'\g<1>18.0', src); assert n == 30, n
rep('        int nt = clamp (t, 0, 17);', '        int nt = clamp (t, 0, 18);')
rep('        if (ty == 17)\n            fxConDerive (s);', '        if (ty == 18)\n            fxFbDerive (s);   // FX-FBANK\n\n        if (ty == 17)\n            fxConDerive (s);')
rep('        else if (ty == 17) y = fxCon    (s, x);\n', '        else if (ty == 17) y = fxCon    (s, x);\n        else if (ty == 18) y = fxFb     (s, x);\n')
dsp = r'''    // ================= FX-FBANK: Filterbank (FX type 18) =================
    void fxFbDerive (int s)
    {
        int   db = s * 16;
        int   pb = s * 6;
        float sr = float (processor.frequency);
        float p1 = clamp (fxP.at (pb),     0.0f, 1.0f);
        float p2 = clamp (fxP.at (pb + 1), 0.0f, 1.0f);
        float p3 = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float p4 = clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float p5 = clamp (fxP.at (pb + 4), 0.0f, 1.0f);
        float p6 = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        int   md = clamp (fxMode.at (s), 0, 5);
        int   rt = md % 3;
        bool  mirror = md >= 3;

        float f1 = fxExpMap (p1, 20.0f, 20000.0f);
        float st = float (rint ((p6 - 0.5f) * 48.0f));
        float f2 = f1 * float (pow (2.0f, st / 12.0f));
        float lim = sr * 0.45f;
        f1 = clamp (f1, 20.0f, lim);
        f2 = clamp (f2, 20.0f, lim);

        fxD.at (db)     = float (tan (3.14159265f * f1 / sr));
        fxD.at (db + 1) = float (tan (3.14159265f * f2 / sr));
        fxD.at (db + 2) = 2.0f - 1.84f * p2;
        fxD.at (db + 3) = 2.0f - 1.84f * min (1.0f, p2 * 1.15f);

        float q3 = mirror ? 1.0f - p3 : p3;
        fxD.at (db + 4)  = clamp (1.0f - 2.0f * p3, 0.0f, 1.0f);
        fxD.at (db + 5)  = 1.0f - abs (2.0f * p3 - 1.0f);
        fxD.at (db + 6)  = clamp (2.0f * p3 - 1.0f, 0.0f, 1.0f);
        fxD.at (db + 7)  = p4;
        float d = 1.0f + 7.0f * p5;
        fxD.at (db + 8)  = d;
        fxD.at (db + 9)  = 1.0f / (1.0f + 0.5f * (d - 1.0f));
        fxD.at (db + 10) = clamp (1.0f - 2.0f * q3, 0.0f, 1.0f);
        fxD.at (db + 11) = 1.0f - abs (2.0f * q3 - 1.0f);
        fxD.at (db + 12) = clamp (2.0f * q3 - 1.0f, 0.0f, 1.0f);
        fxD.at (db + 13) = rt == 0 ? 0.0f : (rt == 1 ? 1.0f : 0.5f);
    }

    // one multimode filter (TPT state variable): response mix of low / band / high pass with the anti-mix crossfade to the notch
    float fxFbStage (int zi, float x, float g, float k, float wl, float wb, float wh, float c)
    {
        float s1  = fxF.at (zi);
        float s2  = fxF.at (zi + 1);
        float hp  = (x - (k + g) * s1 - s2) / (1.0f + k * g + g * g);
        float bp  = g * hp + s1;
        float lp  = g * bp + s2;
        fxF.at (zi)     = g * hp + bp;
        fxF.at (zi + 1) = g * bp + lp;
        float bn  = bp * k;
        float y   = wl * lp + wb * bn + wh * hp;
        y += c * (lp + hp - bn - y);
        return float (tanh (y * 0.8f)) * 1.25f;
    }

    float fxFbCh (int s, int ch, float x)
    {
        int   fb = s * 40 + ch * 8;
        int   db = s * 16;
        float d  = fxD.at (db + 8);
        float u  = d > 1.001f ? float (tanh (x * d)) * fxD.at (db + 9) : x;
        float c  = fxD.at (db + 7);
        float a  = fxFbStage (fb,     u, fxD.at (db),     fxD.at (db + 2), fxD.at (db + 4),  fxD.at (db + 5),  fxD.at (db + 6),  c);
        float b2 = fxFbStage (fb + 2, u, fxD.at (db + 1), fxD.at (db + 3), fxD.at (db + 10), fxD.at (db + 11), fxD.at (db + 12), c);
        float sr = fxFbStage (fb + 4, a, fxD.at (db + 1), fxD.at (db + 3), fxD.at (db + 10), fxD.at (db + 11), fxD.at (db + 12), c);
        float ser = fxD.at (db + 13);
        return (1.0f - ser) * 0.5f * (a + b2) + ser * sr;
    }

    float<2> fxFb (int s, float<2> x)
    {
        return float<2> (fxFbCh (s, 0, x[0]), fxFbCh (s, 1, x[1]));
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', dsp + '    // One slot: dry/wet mix of the selected effect;')
open(path, 'w').write(src)
print('ok')
