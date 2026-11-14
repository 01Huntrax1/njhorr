#!/usr/bin/env python3
"""Idempotent (marker FX-WAVEGUIDE): FX type 32 "Waveguide" - the input excites resonating delay loops (string / tube / drones), usable in the Main rack
and in the oscillator racks (memory-light: 16384 floats of arena).
 Modes: 0 String (Karplus-Strong loop), 1 Tube (inverting loop of half the period: odd harmonics), 2 Dual Strings (second loop slightly detuned),
        3 Fifth Drone (second loop x 1.5), 4 Octave Drone (second loop x 0.5).
 Knobs: Pitch (30 Hz - 2 kHz), Decay (60 dB time 50 ms - 8 s), Damp (loop low-pass 500 Hz - 16 kHz), Detune (cents: L/R spread, or the second string),
        Excite (input gain), Drive (soft saturation in the loop)."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); IP = os.path.join(ROOT, 'patch', 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-WAVEGUIDE' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t

src, n = re.subn(r'(FX \d+ Type",\s*min: 0\.0, max: )31\.0', r'\g<1>32.0', src)
assert n == 144, n
rep('int nt = clamp (t, 0, 31);', 'int nt = clamp (t, 0, 32);')
rep('(t >= 17 && t <= 28) || t == 30;', '(t >= 17 && t <= 28) || t == 30 || t == 32;')
rep('        if (ty == 31)\n            fxCsDerive (s);   // FX-CLOUDSEED\n', '        if (ty == 31)\n            fxCsDerive (s);   // FX-CLOUDSEED\n\n        if (ty == 32)\n            fxWgDerive (s);   // FX-WAVEGUIDE\n')
rep('        else if (ty == 31) y = fxCloudSeed (s, x);\n', '        else if (ty == 31) y = fxCloudSeed (s, x);\n        else if (ty == 32) y = fxWaveguide (s, x);\n')

CODE = r'''    // ================= FX-WAVEGUIDE: resonating string / tube (FX type 32) =================
    // The input excites one or two delay loops (low-pass in the loop, optional soft saturation).  Modes: 0 String, 1 Tube (inverting, half period),
    // 2 Dual Strings (second loop detuned), 3 Fifth Drone (x 1.5), 4 Octave Drone (x 0.5).  P1 Pitch, P2 Decay, P3 Damp, P4 Detune, P5 Excite, P6 Drive.
    // fxD per slot: 0..3 delay (samples) of loop 0 left / right, loop 1 left / right; 4 / 5 loop gain; 6 damping coefficient; 7 input gain; 8 drive; 9 loops; 10 sign; 11 output gain.
    // Arena: channel c at fxAb + c * 8192, loop j at + j * 4096 (ring of 4096); position fxI[s * 24]; low-pass states fxF[s * 40 + c * 2 + j].
    void fxWgDerive (int s)
    {
        float sr   = float (processor.frequency);
        int   db   = s * 16;
        int   pb   = s * 6;
        int   md   = clamp (fxMode.at (s), 0, 4);
        float f    = 30.0f * float (pow (2000.0f / 30.0f, clamp (fxP.at (pb), 0.0f, 1.0f)));
        float t60  = 0.05f * float (pow (160.0f, clamp (fxP.at (pb + 1), 0.0f, 1.0f)));
        float fc   = 500.0f * float (pow (32.0f, clamp (fxP.at (pb + 2), 0.0f, 1.0f)));
        float cent = 50.0f * clamp (fxP.at (pb + 3), 0.0f, 1.0f);
        float exc  = 0.2f + 1.8f * clamp (fxP.at (pb + 4), 0.0f, 1.0f);
        float drv  = clamp (fxP.at (pb + 5), 0.0f, 1.0f);
        float a    = float (exp (-6.2831853f * min (fc, sr * 0.45f) / sr));
        int   nl   = md >= 2 ? 2 : 1;
        float sgn  = md == 1 ? -1.0f : 1.0f;
        float tubeK = md == 1 ? 0.5f : 1.0f;

        for (int j = 0; j < 2; ++j)
        {
            float ratio = 1.0f;

            if (j == 1)
                ratio = md == 2 ? float (pow (2.0f, (3.0f + cent) / 1200.0f)) : (md == 3 ? 1.5f : 0.5f);

            float gj = 0.0f;

            for (int c = 0; c < 2; ++c)
            {
                float sp = md == 2 ? 0.0f : (c == 0 ? -0.5f : 0.5f) * cent;
                float fj = clamp (f * ratio * float (pow (2.0f, sp / 1200.0f)), 12.0f, sr * 0.2f);
                float T  = sr / fj * tubeK;
                float w0 = 6.2831853f * fj / sr;
                float d  = clamp (T - wgLpDelay (a, w0), 4.0f, 4000.0f);
                fxD.at (db + j * 2 + c) = d;
                gj = float (exp (-6.9078f * T / (sr * t60))) / wgLpGain (a, w0);
            }

            fxD.at (db + 4 + j) = min (gj, 0.9998f);
        }

        fxD.at (db + 6)  = a;
        fxD.at (db + 7)  = exc * sqrt (1.0f - fxD.at (db + 4));
        fxD.at (db + 8)  = drv;
        fxD.at (db + 9)  = float (nl);
        fxD.at (db + 10) = sgn;
        fxD.at (db + 11) = nl == 2 ? 0.7f : 1.0f;
    }

    float<2> fxWaveguide (int s, float<2> x)
    {
        int   ab  = fxAb (s);
        int   ib  = s * 24;
        int   db  = s * 16;
        int   fb  = s * 40;
        int   pos = fxI.at (ib);
        int   nl  = int (fxD.at (db + 9) + 0.5f);
        float a   = fxD.at (db + 6);
        float ing = fxD.at (db + 7);
        float drv = fxD.at (db + 8);
        float sgn = fxD.at (db + 10);
        float og  = fxD.at (db + 11);
        float sat = 1.0f + 4.0f * drv;
        float<2> o = float<2> (0.0f, 0.0f);

        for (int c = 0; c < 2; ++c)
        {
            float acc = 0.0f;

            for (int j = 0; j < nl; ++j)
            {
                int   lb = ab + c * 8192 + j * 4096;
                float rp = float (pos) - fxD.at (db + j * 2 + c);
                int   i0 = int (floor (rp));
                float fr = rp - float (i0);
                float y  = fxArena.at (lb + (i0 & 4095)) * (1.0f - fr) + fxArena.at (lb + ((i0 + 1) & 4095)) * fr;
                float lp = fxF.at (fb + c * 2 + j);
                lp = (1.0f - a) * y + a * lp;
                fxF.at (fb + c * 2 + j) = lp;
                float fk = lp * fxD.at (db + 4 + j) * sgn;

                if (drv > 0.001f)
                    fk = float (tanh (fk * sat)) / sat;

                fxArena.at (lb + (pos & 4095)) = clamp (x[c] * ing + fk, -8.0f, 8.0f);
                acc += y;
            }

            o[c] = float (tanh (acc * og));
        }

        fxI.at (ib) = (pos + 1) & 4095;
        return o;
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')

# UI spec
rep('0, 31, 0, "", "sel", FX_TYPES.map(t => t.n).slice(0, 32), 1, "Type"]', '0, FX_TYPES.length - 1, 0, "", "sel", FX_TYPES.map(t => t.n), 1, "Type"]', 'idx')
entry = '''    // FX-WAVEGUIDE: the input excites resonating delay loops (FX type 32)
    { n: "Waveguide", mix: 0.5, modes: ["String", "Tube", "Dual Strings", "Fifth Drone", "Octave Drone"],
      p: [["Pitch", fxHz(30, 2000), 0.45], ["Decay", fxMs(50, 8000), 0.5], ["Damp", fxHz(500, 16000), 0.7], ["Detune", fxLin(0, 50, 0, "ct"), 0.1], ["Excite", fxPct, 0.5], ["Drive", fxPct, 0]] },
'''
m = re.search(r'\n\];\n// the three racks', idx); assert m
idx = idx[:m.start() + 1] + entry + idx[m.start() + 1:]
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('FX-WAVEGUIDE applied')
