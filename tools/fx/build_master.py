#!/usr/bin/env python3
"""Idempotent, marker MASTER-OUT: the master output loses Synth Drive, Drive Algorithm and Tone (they no longer act: the synth sum is not shaped
and the tilt filter is gone; the parameters stay declared so that old presets load) and gets a look-ahead limiter instead of the hard clip:
 Limiter (on / off, default on) and Ceiling (-6..0 dB, default -0.3 dB).  1 ms look-ahead, the gain falls to the peak in time and recovers over about 80 ms,
 a last clamp stays as the safety net.  Ids 11600 (Limiter), 11601 (Ceiling).   build_master.py [patch dir]"""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'MASTER-OUT' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src', cnt=1):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == cnt, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
rep('    // EURO\n', '''    input event float param11600 [[ name: "Out Limiter", min: 0.0, max: 1.0, init: 1.0, step: 1.0 ]];   // MASTER-OUT
    input event float param11601 [[ name: "Out Ceiling", min: -6.0, max: 0.0, init: -0.3 ]];
    // EURO
''')
rep('    // RESO-HAND-BEGIN\n', '    event param11600 (float v) { limOn = v; }   // MASTER-OUT\n    event param11601 (float v) { limCeil = float (pow (10.0f, v / 20.0f)); }\n    // RESO-HAND-BEGIN\n')
rep('    float stereoWidth  = 1.0f;\n', '''    float stereoWidth  = 1.0f;
    float limOn        = 1.0f;     // MASTER-OUT: look-ahead limiter
    float limCeil      = 0.9658f;
    float limGain      = 1.0f;
    float[64] limBufL;
    float[64] limBufR;
    int   limPos       = 0;
''')
rep('float rawL = shapeSig (mixSynthL.at (bg) * 0.35f, driveEff) * gPanL;', 'float rawL = mixSynthL.at (bg) * 0.35f * gPanL;   // MASTER-OUT: no drive shaper any more')
rep('float rawR = shapeSig (mixSynthR.at (bg) * 0.35f, driveEff) * gPanR;', 'float rawR = mixSynthR.at (bg) * 0.35f * gPanR;')
old = src[src.index('            // ----- output tone (tilt: dark <-> bright) and output gain -----'):src.index('            outL = outL * outGain * outGainMod;')]
src = src.replace(old, '            // ----- output gain (MASTER-OUT: the tone tilt is gone) -----\n')
rep('''            outL = clamp (outL, -1.0f, 1.0f);
            outR = clamp (outR, -1.0f, 1.0f);

            out <- float<2> (outL, outR);''', '''            // ----- MASTER-OUT: look-ahead limiter (48 samples), then the safety clamp -----
            limBufL.at (limPos) = outL;
            limBufR.at (limPos) = outR;

            if (limOn > 0.5f)
            {
                float pk = 0.0f;

                for (int li = 0; li < 48; ++li)
                    pk = max (pk, max (abs (limBufL.at ((limPos - li) & 63)), abs (limBufR.at ((limPos - li) & 63))));

                float tg = pk > limCeil ? limCeil / pk : 1.0f;
                limGain += tg < limGain ? (tg - limGain) * 0.15f : (tg - limGain) * 0.00026f;
                int   dp = (limPos - 47) & 63;
                float ga = min (limGain, tg);
                outL = limBufL.at (dp) * ga;
                outR = limBufR.at (dp) * ga;
            }

            limPos = (limPos + 1) & 63;

            outL = clamp (outL, -1.0f, 1.0f);
            outR = clamp (outR, -1.0f, 1.0f);

            out <- float<2> (outL, outR);''')
# UI table
rep('const FX_OUT = [28, 536, 175, 189, 221, 222];', 'const FX_OUT = [175, 221, 222, 11600, 11601];   // MASTER-OUT: Synth Drive, Drive Algorithm and Tone are gone', 'idx')
rep('    // EURO: Eurorack rack of Njohrr Modular\n', '''    L.push([11600, "Out Limiter", 0, 1, 1, "", "btn", ["Off", "On"], 1, "Limiter"]);   // MASTER-OUT
    L.push([11601, "Out Ceiling", -6, 0, -0.3, "dB", "sld", null, 1, "Ceiling"]);
    // EURO: Eurorack rack of Njohrr Modular
''', 'idx')
open(P, 'w').write(src); open(IP, 'w').write(idx)
print('ok')
