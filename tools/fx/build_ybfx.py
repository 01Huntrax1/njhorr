#!/usr/bin/env python3
"""Idempotent (marker FX-YAYBAHAR): FX type 33 "Yaybahar" - own implementation (written from the published architecture of the instrument, no code taken over) of
 Gorkem Sen's Yaybahar: a string drives two springs, each spring drives a drum membrane, spring and drum act back on the string / spring.
 string loop (the input bows / excites it) -> spring (delay line, 4 dispersion all-passes, damping, feedback) -> rectangular membrane (8 modal resonators of a 1.12 : 1 rectangle,
 driven and picked up off-centre).
 Modes: 0 Classic (mono string, spring 2 is 1.37 x as long, drum 2 one octave lower, outputs panned 80 / 20), 1 Stereo (string, spring and drum per channel), 2 Deep (Classic, drums tuned lower).
 Knobs: Pitch (string 40 Hz - 800 Hz), Spring (length 20 - 250 ms), Decay (string / spring feedback and drum ring time), Disper (spring dispersion: the chirpy "boing"),
        Membran (fundamental of drum 1, 40 - 250 Hz), Damp (loop low-pass 500 Hz - 8 kHz).
 Only for slots with a big arena (Bus / Main racks, not the per voice slots of the oscillator racks)."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); IP = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-YAYBAHAR' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )32\.0', r'\g<1>33.0', src)
assert n == 144, n
src, n = re.subn(r'(Euro M\d+ FX Type", min: 0\.0, max: )32\.0', r'\g<1>33.0', src)
assert n == 20, n
rep('int nt = clamp (t, 0, 32);', 'int nt = clamp (t, 0, 33);')
rep('        if (ty == 32)\n            fxWgDerive (s);   // FX-WAVEGUIDE\n', '        if (ty == 32)\n            fxWgDerive (s);   // FX-WAVEGUIDE\n\n        if (ty == 33 && s < 48)\n            fxYbDerive (s);   // FX-YAYBAHAR\n')
rep('        else if (ty == 32) y = fxWaveguide (s, x);\n', '        else if (ty == 32) y = fxWaveguide (s, x);\n        else if (ty == 33) y = s < 48 ? fxYaybahar (s, x) : x;   // FX-YAYBAHAR: needs the big arena of the rack slots\n')

CODE = r'''    // ================= FX-YAYBAHAR: string -> two springs -> two drum membranes (FX type 33) =================
    // Own implementation after the architecture of the instrument (a string drives two springs, every spring drives a drum membrane; the springs and drums act back on the string):
    //   string loop (bowed by the input)  ->  spring (delay line with dispersion all-passes, damping, feedback)  ->  rectangular membrane (8 modal resonators)
    // Modes: 0 Classic (mono string, spring 2 is 1.37 x as long, drum 2 one octave lower, outputs panned 80 / 20), 1 Stereo (a string, spring and drum per channel), 2 Deep (Classic, drums tuned lower).
    // Arena of the slot (196608 floats): string rings (string u at u * 8192, 8192 long), spring rings at 16384 + v * 32768 (32768 long).
    // fxI: s * 24 string position, + 1 spring position.   fxF (s * 40): 0..1 string low-pass, 2..3 spring low-pass, 6..13 dispersion all-pass states (v * 4 + stage).
    // fxD (s * 16): 0..1 string delay, 2 string loop gain, 3 string low-pass, 4 input gain, 5..6 spring delay, 7 spring -> string coupling, 8 drum -> spring coupling, 9 spring gain,
    //               10 spring low-pass, 11 all-pass coefficient, 12 mode, 13 output gain, 14 pan.
    // csV (s * 1024): membrane v mode k at (v * 8 + k) * 4: c1, c2, input gain, output weight; states from 512 + (v * 8 + k) * 2; 600 + v last membrane output.
    void fxYbDerive (int s)
    {
        float sr   = float (processor.frequency);
        int   db   = s * 16;
        int   pb   = s * 6;
        int   cb   = s * 1024;
        int   md   = clamp (fxMode.at (s), 0, 2);
        float f    = 40.0f * float (pow (20.0f, clamp (fxP.at (pb), 0.0f, 1.0f)));
        float sprT = 0.02f * float (pow (12.5f, clamp (fxP.at (pb + 1), 0.0f, 1.0f)));
        float dec  = clamp (fxP.at (pb + 2), 0.0f, 1.0f);
        float disp = 0.75f * clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float fm   = 40.0f * float (pow (6.25f, clamp (fxP.at (pb + 4), 0.0f, 1.0f)));
        float fc   = 500.0f * float (pow (16.0f, clamp (fxP.at (pb + 5), 0.0f, 1.0f)));
        float aSp  = float (exp (-6.2831853f * min (fc, sr * 0.45f) / sr));
        float aSt  = float (exp (-6.2831853f * min (fc * 2.0f, sr * 0.45f) / sr));
        float t60  = 0.2f * float (pow (30.0f, dec));
        float fS   = clamp (f, 20.0f, sr * 0.2f);
        float T    = sr / fS;
        float w0   = 6.2831853f * fS / sr;
        float d    = clamp (T - wgLpDelay (aSt, w0), 4.0f, 8000.0f);
        float gSp  = 0.55f + 0.42f * dec;

        fxD.at (db)      = d;
        fxD.at (db + 1)  = clamp (d * 1.004f, 4.0f, 8000.0f);
        float gS = min (float (exp (-6.9078f * T / (sr * t60))) / wgLpGain (aSt, w0), 0.9998f);
        fxD.at (db + 2)  = gS;
        fxD.at (db + 3)  = aSt;
        fxD.at (db + 4)  = 0.5f;
        fxD.at (db + 5)  = clamp (sprT * sr, 16.0f, 30000.0f);
        fxD.at (db + 6)  = clamp (sprT * (md == 1 ? 1.07f : 1.37f) * sr, 16.0f, 30000.0f);
        fxD.at (db + 7)  = 0.3f * (1.0f - gS) * (1.0f - gSp);   // the return must stay below the loss of the string loop, or the string runs away
        fxD.at (db + 8)  = 0.01f * (1.0f - gSp);   // drum resonance gain (up to 5) x spring resonance (1 / (1 - gSp)) x output gain stays below unity
        fxD.at (db + 9)  = gSp;
        fxD.at (db + 10) = aSp;
        fxD.at (db + 11) = disp;
        fxD.at (db + 12) = float (md);
        fxD.at (db + 13) = 1.4f;
        fxD.at (db + 14) = 0.8f;
        float t60m = 0.4f + 2.5f * dec;
        float[8] ratio = (1.0f, 1.634f, 1.527f, 2.0f, 2.335f, 2.133f, 2.604f, 2.494f);   // rectangular membrane (1,1) (1,2) (2,1) (2,2) (1,3) (3,1) (2,3) (3,2), aspect 1.12
        float[8] win   = (0.968f, 0.243f, 0.422f, 0.106f, -0.908f, -0.784f, -0.395f, -0.197f);   // drive at (0.43, 0.46)
        float[8] wout  = (0.880f, 0.275f, 0.799f, 0.250f, -0.794f, -0.155f, -0.721f, -0.048f);   // pick-up at (0.35, 0.45)

        for (int v = 0; v < 2; ++v)
        {
            float tune = v == 0 ? (md == 2 ? 0.6f : 1.0f) : (md == 0 ? 0.5f : (md == 1 ? 0.94f : 0.3f));

            for (int k = 0; k < 8; ++k)
            {
                float fk = fm * tune * ratio.at (k);
                float tk = t60m / (1.0f + 0.5f * (ratio.at (k) - 1.0f));
                float r  = float (exp (-6.9078f / (tk * sr)));
                float w  = 6.2831853f * fk / sr;
                bool  ok = fk < sr * 0.45f;
                int   ci = cb + (v * 8 + k) * 4;
                csV.at (ci)     = ok ? 2.0f * r * float (cos (w)) : 0.0f;
                csV.at (ci + 1) = ok ? r * r : 0.0f;
                csV.at (ci + 2) = ok ? (1.0f - r) * float (sin (w)) * 10.0f * win.at (k) : 0.0f;
                csV.at (ci + 3) = wout.at (k);
            }
        }
    }

    float<2> fxYaybahar (int s, float<2> x)
    {
        int   ab   = fxAb (s);
        int   ib   = s * 24;
        int   db   = s * 16;
        int   fb   = s * 40;
        int   cb   = s * 1024;
        int   sp   = fxI.at (ib);
        int   pp   = fxI.at (ib + 1);
        bool  st   = int (fxD.at (db + 12) + 0.5f) == 1;
        float aSt  = fxD.at (db + 3);
        float gSt  = fxD.at (db + 2);
        float ing  = fxD.at (db + 4);
        float kc   = fxD.at (db + 7);
        float kb   = fxD.at (db + 8);
        float gSp  = fxD.at (db + 9);
        float aSp  = fxD.at (db + 10);
        float aAp  = fxD.at (db + 11);
        float og   = fxD.at (db + 13);
        float pan  = fxD.at (db + 14);
        float xm   = 0.5f * (x[0] + x[1]);
        float[2] ys;
        float[2] fk;
        float[2] ls;
        float[2] ret;
        float[2] A;

        // read the strings
        for (int u = 0; u < (st ? 2 : 1); ++u)
        {
            int   sb = ab + u * 8192;
            float rp = float (sp) - fxD.at (db + u);
            int   i0 = int (floor (rp));
            float fr = rp - float (i0);
            float y  = fxArena.at (sb + (i0 & 8191)) * (1.0f - fr) + fxArena.at (sb + ((i0 + 1) & 8191)) * fr;
            float lp = (1.0f - aSt) * y + aSt * fxF.at (fb + u);
            fxF.at (fb + u) = lp;
            ys.at (u) = y;
            fk.at (u) = lp * gSt;
            ret.at (u) = 0.0f;
        }

        // springs: read, dispersion, damping; write with the string signal and the drum motion
        for (int v = 0; v < 2; ++v)
        {
            int   u   = st ? v : 0;
            int   pb  = ab + 16384 + v * 32768;
            float rq  = float (pp) - fxD.at (db + 5 + v);
            int   q0  = int (floor (rq));
            float qf  = rq - float (q0);
            float y   = fxArena.at (pb + (q0 & 32767)) * (1.0f - qf) + fxArena.at (pb + ((q0 + 1) & 32767)) * qf;

            for (int a = 0; a < 4; ++a)   // dispersion: the low frequencies arrive later
            {
                int   ai = fb + 6 + v * 4 + a;
                float yo = -aAp * y + fxF.at (ai);
                fxF.at (ai) = clamp (y + aAp * yo, -16.0f, 16.0f);
                y = yo;
            }

            float l = (1.0f - aSp) * y + aSp * fxF.at (fb + 2 + v);
            fxF.at (fb + 2 + v) = l;
            ls.at (v) = l;
            ret.at (u) += l * kc;
            fxArena.at (pb + (pp & 32767)) = clamp (ys.at (u) * 0.7f + csV.at (cb + 600 + v) * kb + l * gSp, -8.0f, 8.0f);
        }

        // write the strings (input, loop and the return of the springs)
        for (int u = 0; u < (st ? 2 : 1); ++u)
            fxArena.at (ab + u * 8192 + (sp & 8191)) = clamp ((st ? x[u] : xm) * ing + fk.at (u) + ret.at (u), -8.0f, 8.0f);

        // drum membranes, driven by the end of the springs
        for (int v = 0; v < 2; ++v)
        {
            float drive = ls.at (v) * og;
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

            csV.at (cb + 600 + v) = mem;
            A.at (v) = drive * 0.7f + mem * 0.8f;
        }

        fxI.at (ib)     = (sp + 1) & 8191;
        fxI.at (ib + 1) = (pp + 1) & 32767;

        if (st)
            return float<2> (float (tanh (A.at (0))), float (tanh (A.at (1))));

        return float<2> (float (tanh (pan * A.at (0) + (1.0f - pan) * A.at (1))), float (tanh ((1.0f - pan) * A.at (0) + pan * A.at (1))));
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')

entry = '''    // FX-YAYBAHAR: string -> two springs -> two drum membranes (FX type 33)
    { n: "Yaybahar", mix: 0.6, modes: ["Classic", "Stereo", "Deep"],
      p: [["Pitch", fxHz(40, 800), 0.4], ["Spring", fxMs(20, 250), 0.5], ["Decay", fxPct, 0.5], ["Disper", fxPct, 0.5], ["Membran", fxHz(40, 250), 0.35], ["Damp", fxHz(500, 8000), 0.6]] },
'''
m = re.search(r'\n\];\n// the three racks', idx); assert m
idx = idx[:m.start() + 1] + entry + idx[m.start() + 1:]
rep('L.push([b + 18, n + " FX Type", 0, 32, 0,', 'L.push([b + 18, n + " FX Type", 0, FX_TYPES.length - 1, 0,', 'idx')
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('FX-YAYBAHAR applied')
