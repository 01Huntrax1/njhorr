#!/usr/bin/env python3
"""Idempotent, marker FX-YBPARTS: the elements of the Yaybahar as effects of their own (types 35..37):
  35 Yb Spring  - the spring: a dispersive delay line (4 all-passes, damping, feedback) with a slow modulation of its length (Boing); modes Single / Dual (second spring 1.37 x longer) / Stereo
  36 Yb Drum    - the drum membrane: 8 modal resonators of a rectangular membrane (aspect, strike and pick-up position, damping tilt); modes Rect / Two Drums / Stereo (+ Key)
  37 Yb String  - the string: a tuned delay loop with low-pass damping and a bow nonlinearity (tanh), driven by the input; modes Mono / Stereo (detuned pair) / Octave (+ Key)
Key tracking like Yaybahar (modes 3..5 follow the last played note).   build_ybparts.py [patch dir]"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-YBPARTS' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
NT = 37
src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )34\.0', r'\g<1>%d.0' % NT, src); assert n == 144, n
src, n = re.subn(r'(Euro M\d+ FX Type", min: 0\.0, max: )34\.0', r'\g<1>%d.0' % NT, src); assert n == 20, n
rep('int nt = clamp (t, 0, 34);', 'int nt = clamp (t, 0, %d);' % NT)
rep('        else if (ty == 34) y = s < 48 ? fxShTab (s, x) : x;   // FX-SHTAB\n', '''        else if (ty == 34) y = s < 48 ? fxShTab (s, x) : x;   // FX-SHTAB
        else if (ty == 35) y = s < 48 ? fxYbSpring (s, x) : x;   // FX-YBPARTS
        else if (ty == 36) y = s < 48 ? fxYbDrum (s, x) : x;
        else if (ty == 37) y = s < 48 ? fxYbString (s, x) : x;
''')
rep('        if (ty == 33 && s < 48)\n            fxYbDerive (s);   // FX-YAYBAHAR\n', '''        if (ty == 33 && s < 48)
            fxYbDerive (s);   // FX-YAYBAHAR

        if (ty >= 35 && ty <= 37 && s < 48)
            fxYbpDerive (s, ty);   // FX-YBPARTS
''')
rep('if ((kt == 33 && fxMode.at (ks) >= 3) || (kt == 32 && fxMode.at (ks) >= 5))', 'if ((kt == 33 && fxMode.at (ks) >= 3) || (kt == 32 && fxMode.at (ks) >= 5) || (kt >= 36 && kt <= 37 && fxMode.at (ks) >= 3))')

CODE = r'''    // ================= FX-YBPARTS: the elements of the Yaybahar as effects of their own (types 35 spring, 36 drum, 37 string) =================
    // fxD (s * 16): spring: 0..1 delay (samples), 2 loop gain, 3 damping, 4 all-pass coefficient, 5 modulation depth (samples), 6 modulation rate (cycles / sample), 7 level, 8 mode
    //               drum:   8 mode, 9 level, 10 input gain
    //               string: 0..1 delay, 2..3 loop gain, 4 damping, 5 input gain, 6 nonlinearity, 7 level, 8 mode (loop gain of string 1 at 3)
    // spring arena: ring v at v * 32768; string arena: ring u at u * 8192; drum: csV like the Yaybahar (c1, c2, input gain, output weight per mode; states from 512)
    void fxYbpDerive (int s, int ty)
    {
        float sr  = float (processor.frequency);
        int   db  = s * 16;
        int   pb  = s * 6;
        int   cb  = s * 1024;
        float p0  = clamp (fxP.at (pb),     0.0f, 1.0f);
        float p1  = clamp (fxP.at (pb + 1), 0.0f, 1.0f);
        float p2  = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float p3  = clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float p4  = clamp (fxP.at (pb + 4), 0.0f, 1.0f);
        float p5  = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        int   mo  = fxMode.at (s);
        bool  key = ty != 35 && mo >= 3;
        int   md  = clamp (mo >= 3 ? mo - 3 : mo, 0, 2);
        float lvl = float (pow (10.0f, (p5 - 0.5f) * 24.0f / 20.0f));

        if (ty == 35)
        {
            float sprT = 0.02f * float (pow (12.5f, p0));
            fxD.at (db)     = clamp (sprT * sr, 16.0f, 28000.0f);
            fxD.at (db + 1) = clamp (sprT * (md == 2 ? 1.07f : 1.37f) * sr, 16.0f, 28000.0f);
            fxD.at (db + 2) = 0.5f + 0.47f * p1;
            fxD.at (db + 3) = float (exp (-6.2831853f * min (500.0f * float (pow (16.0f, p3)), sr * 0.45f) / sr));
            fxD.at (db + 4) = 0.75f * p2;
            fxD.at (db + 5) = p4 * 0.0015f * sr;
            fxD.at (db + 6) = 0.7f / sr;
            fxD.at (db + 7) = lvl;
            fxD.at (db + 8) = float (md);
        }
        else if (ty == 36)
        {
            float fm = 40.0f * float (pow (6.25f, p0));

            if (key)
                fm = clamp (fxKeyHz() * fm / 261.63f, 20.0f, sr * 0.2f);

            float t60m = 0.4f + 2.5f * p1;
            float asp  = 0.6f + p2;
            float xs   = 0.1f + 0.4f * p3;
            float xp   = 0.1f + 0.4f * p4;
            float dk   = 0.2f + 1.8f * p5;
            float[8] mm = (1.0f, 1.0f, 2.0f, 2.0f, 1.0f, 3.0f, 2.0f, 3.0f);
            float[8] nn = (1.0f, 2.0f, 1.0f, 2.0f, 3.0f, 1.0f, 3.0f, 2.0f);
            float nrm = float (sqrt (1.0f + 1.0f / (asp * asp)));

            fxD.at (db + 8)  = float (md);

            for (int v = 0; v < 2; ++v)
            {
                float tune = v == 0 ? 1.0f : (md == 1 ? 0.5f : 0.94f);

                for (int k = 0; k < 8; ++k)
                {
                    float ratio = float (sqrt (mm.at (k) * mm.at (k) + nn.at (k) * nn.at (k) / (asp * asp))) / nrm;
                    float fk = fm * tune * ratio;
                    float tk = t60m / (1.0f + dk * (ratio - 1.0f));
                    float r  = float (exp (-6.9078f / (tk * sr)));
                    float w  = 6.2831853f * fk / sr;
                    bool  ok = fk < sr * 0.45f;
                    float wi = float (sin (3.14159265f * mm.at (k) * xs) * sin (3.14159265f * nn.at (k) * 0.46f));
                    float wo = float (sin (3.14159265f * mm.at (k) * xp) * sin (3.14159265f * nn.at (k) * 0.45f));
                    int   ci = cb + (v * 8 + k) * 4;
                    csV.at (ci)     = ok ? 2.0f * r * float (cos (w)) : 0.0f;
                    csV.at (ci + 1) = ok ? r * r : 0.0f;
                    csV.at (ci + 2) = ok ? (1.0f - r) * float (sin (w)) * 40.0f * wi : 0.0f;
                    csV.at (ci + 3) = wo;
                }
            }

            fxD.at (db + 9) = lvl;
        }
        else
        {
            float f   = 40.0f * float (pow (20.0f, p0));

            if (key)
                f = fxKeyHz() * f / 261.63f;

            float fc  = 500.0f * float (pow (16.0f, p2));
            float aSt = float (exp (-6.2831853f * min (fc * 2.0f, sr * 0.45f) / sr));
            float t60 = 0.2f * float (pow (30.0f, p1));
            float ct  = float (pow (2.0f, (p4 - 0.5f) * 50.0f / 1200.0f));
            float f1  = md == 2 ? 0.5f * ct : ct;

            for (int u = 0; u < 2; ++u)
            {
                float fS = clamp (u == 0 ? f : f * f1, 20.0f, sr * 0.2f);
                float T  = sr / fS;
                float w0 = 6.2831853f * fS / sr;
                fxD.at (db + u) = clamp (T - wgLpDelay (aSt, w0), 4.0f, 8000.0f);
                fxD.at (db + 2 + u) = min (float (exp (-6.9078f * T / (sr * t60))) / wgLpGain (aSt, w0), 0.9998f);
            }

            fxD.at (db + 4) = aSt;
            fxD.at (db + 5) = 0.25f;
            fxD.at (db + 6) = 1.0f + 4.0f * p3;
            fxD.at (db + 7) = lvl;
            fxD.at (db + 8) = float (md);
        }
    }

    float<2> fxYbSpring (int s, float<2> x)
    {
        int   ab  = fxAb (s);
        int   ib  = s * 24;
        int   db  = s * 16;
        int   fb  = s * 40;
        int   pp  = fxI.at (ib);
        int   md  = int (fxD.at (db + 8) + 0.5f);
        float g   = fxD.at (db + 2);
        float aSp = fxD.at (db + 3);
        float aAp = fxD.at (db + 4);
        float dep = fxD.at (db + 5);
        float inc = fxD.at (db + 6);
        float lvl = fxD.at (db + 7);
        float xm  = 0.5f * (x[0] + x[1]);
        float[2] ys;

        for (int v = 0; v < 2; ++v)
        {
            int   pb = ab + v * 32768;
            float ph = fxF.at (fb + 4 + v) + inc * (1.0f + 0.43f * float (v));
            ph -= float (floor (ph));
            fxF.at (fb + 4 + v) = ph;
            float rq = float (pp) - (fxD.at (db + v) + dep * float (sin (6.2831853f * ph)));
            int   q0 = int (floor (rq));
            float qf = rq - float (q0);
            float y  = fxArena.at (pb + (q0 & 32767)) * (1.0f - qf) + fxArena.at (pb + ((q0 + 1) & 32767)) * qf;

            for (int a = 0; a < 4; ++a)   // dispersion: the low frequencies arrive later
            {
                int   ai = fb + 6 + v * 4 + a;
                float yo = -aAp * y + fxF.at (ai);
                fxF.at (ai) = clamp (y + aAp * yo, -16.0f, 16.0f);
                y = yo;
            }

            float l = (1.0f - aSp) * y + aSp * fxF.at (fb + 2 + v);
            fxF.at (fb + 2 + v) = l;
            ys.at (v) = l;
            fxArena.at (pb + (pp & 32767)) = clamp ((md == 2 ? x[v] : xm) * 0.7f + l * g, -8.0f, 8.0f);
        }

        fxI.at (ib) = (pp + 1) & 32767;

        if (md == 0)
        {
            float o = float (tanh (ys.at (0) * lvl));
            return float<2> (o, o);
        }

        if (md == 1)
            return float<2> (float (tanh ((0.8f * ys.at (0) + 0.2f * ys.at (1)) * lvl)), float (tanh ((0.2f * ys.at (0) + 0.8f * ys.at (1)) * lvl)));

        return float<2> (float (tanh (ys.at (0) * lvl)), float (tanh (ys.at (1) * lvl)));
    }

    float<2> fxYbDrum (int s, float<2> x)
    {
        int   db  = s * 16;
        int   cb  = s * 1024;
        int   md  = int (fxD.at (db + 8) + 0.5f);
        float lvl = fxD.at (db + 9);
        float xm  = 0.5f * (x[0] + x[1]);
        float[2] A;

        for (int v = 0; v < (md == 0 ? 1 : 2); ++v)
        {
            float drive = md == 2 ? x[v] : xm;
            float mem   = 0.0f;

            for (int k = 0; k < 8; ++k)
            {
                int   ci = cb + (v * 8 + k) * 4;
                int   mi = cb + 512 + (v * 8 + k) * 2;
                float yv = clamp (csV.at (ci) * csV.at (mi) - csV.at (ci + 1) * csV.at (mi + 1) + csV.at (ci + 2) * drive, -16.0f, 16.0f);
                csV.at (mi + 1) = csV.at (mi);
                csV.at (mi)     = yv;
                mem += yv * csV.at (ci + 3);
            }

            A.at (v) = mem;
        }

        if (md == 0)
        {
            float o = float (tanh (A.at (0) * lvl));
            return float<2> (o, o);
        }

        if (md == 1)
            return float<2> (float (tanh ((0.8f * A.at (0) + 0.2f * A.at (1)) * lvl)), float (tanh ((0.2f * A.at (0) + 0.8f * A.at (1)) * lvl)));

        return float<2> (float (tanh (A.at (0) * lvl)), float (tanh (A.at (1) * lvl)));
    }

    float<2> fxYbString (int s, float<2> x)
    {
        int   ab  = fxAb (s);
        int   ib  = s * 24;
        int   db  = s * 16;
        int   fb  = s * 40;
        int   sp  = fxI.at (ib);
        float aSt = fxD.at (db + 4);
        float ing = fxD.at (db + 5);
        float nl  = fxD.at (db + 6);
        float lvl = fxD.at (db + 7);
        int   md  = int (fxD.at (db + 8) + 0.5f);
        float xm  = 0.5f * (x[0] + x[1]);
        float[2] ys;

        for (int u = 0; u < (md == 0 ? 1 : 2); ++u)
        {
            int   sb = ab + u * 8192;
            float rp = float (sp) - fxD.at (db + u);
            int   i0 = int (floor (rp));
            float fr = rp - float (i0);
            float y  = fxArena.at (sb + (i0 & 8191)) * (1.0f - fr) + fxArena.at (sb + ((i0 + 1) & 8191)) * fr;
            float lp = (1.0f - aSt) * y + aSt * fxF.at (fb + u);
            fxF.at (fb + u) = lp;
            float w = ((md == 1 ? x[u] : xm) * ing + lp * fxD.at (db + 2 + u)) * nl;
            fxArena.at (sb + (sp & 8191)) = float (tanh (w)) / nl;   // the bow: the friction limits the loop
            ys.at (u) = y;
        }

        fxI.at (ib) = (sp + 1) & 8191;

        if (md == 0)
        {
            float o = float (tanh (ys.at (0) * lvl));
            return float<2> (o, o);
        }

        if (md == 1)
            return float<2> (float (tanh (ys.at (0) * lvl)), float (tanh (ys.at (1) * lvl)));

        return float<2> (float (tanh ((0.8f * ys.at (0) + 0.2f * ys.at (1)) * lvl)), float (tanh ((0.2f * ys.at (0) + 0.8f * ys.at (1)) * lvl)));
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')

entries = '''    // FX-YBPARTS: the elements of the Yaybahar as effects of their own (FX types 35..37)
    { n: "Yb Spring", mix: 0.6, modes: ["Single", "Dual", "Stereo"],
      p: [["Length", fxMs(20, 250), 0.5], ["Decay", fxPct, 0.6], ["Disper", fxPct, 0.5], ["Damp", fxHz(500, 8000), 0.6], ["Boing", fxPct, 0.2], ["Level", fxLin(-12, 12, 1, "dB"), 0.5]] },
    { n: "Yb Drum", mix: 0.6, modes: ["Rect", "Two Drums", "Stereo", "Rect Key", "Two Drums Key", "Stereo Key"],
      p: [["Tune", fxHz(40, 250), 0.5], ["Decay", fxPct, 0.5], ["Aspect", fxLin(0.6, 1.6, 2, ""), 0.52], ["Strike", fxPct, 0.83], ["Pickup", fxPct, 0.63], ["Damp", fxPct, 0.3]] },
    { n: "Yb String", mix: 0.6, modes: ["Mono", "Stereo", "Octave", "Mono Key", "Stereo Key", "Octave Key"],
      p: [["Pitch", fxHz(40, 800), 0.4], ["Decay", fxPct, 0.6], ["Damp", fxHz(500, 8000), 0.5], ["Bow", fxPct, 0.4], ["Detune", fxLin(-25, 25, 0, "ct"), 0.5], ["Level", fxLin(-12, 12, 1, "dB"), 0.5]] },
'''
m = re.search(r'\n\];\n// the three racks', idx); assert m
idx = idx[:m.start() + 1] + entries + idx[m.start() + 1:]

# tools of the new types (FX-EX table): 35 spring: Pre Delay, Duck, Release, Air; 36 drum: Pre HP, Gate, Warmth, Trim; 37 string: Pre HP, Gate, Air, Trim
NEW = {35: [4, 5, 6, 8], 36: [1, 3, 7, 11], 37: [1, 3, 8, 11]}
m = re.search(r'const int\[160\] fxExTab = \(([^)]*)\);', src); assert m
tab = [int(v) for v in m.group(1).split(',')]
for t, v in NEW.items(): tab[4 * t:4 * t + 4] = v
src = src[:m.start(1)] + ', '.join(str(v) for v in tab) + src[m.end(1):]
hp = os.path.join(root, 'native_ui', 'NjoFxEx.h'); h = open(hp).read()
m = re.search(r'static const int tab\[160\] = \{ ([^}]*) \};', h); assert m
h = h[:m.start(1)] + ', '.join(str(v) for v in tab) + h[m.end(1):]
open(hp, 'w').write(h)
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('FX-YBPARTS applied')
