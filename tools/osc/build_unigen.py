#!/usr/bin/env python3
"""Idempotent: Unison for every oscillator source, marker UNI-ALL.
Wavetable and Alpha Juno have their own unison (several voices of the oscillator).  All other sources (Sampler, Wave Terrain, Physical, Kick,
Waveguide, JP-8080, Granular, Additive, Modal Drum, Spectral, SoundFont) run once per note; their output goes through a detuned-copy stage:
every copy is a two-tap crossfading delay-line pitch shifter (Hann crossfade, window about 35 ms) of the source's mono sum.  The copies use the
unison parameters of the slot (Voices, Detune, Blend, Width, Detune Curve, Drift) through the same tables as the wavetable unison (updateWtUni:
ratio / left and right gain); the side signal (L - R) of a stereo source is kept as it is.  Phase Spread has no meaning here.
State: gUniBuf (voice * 6 + slot) * 4096 mono delay line, gUniPos write position, gUniPh (voice * 6 + slot) * 16 + copy phase."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'UNI-ALL' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)
rep('    // wavetable unison (per slot, up to 7 voices)\n',
    '    // UNI-ALL: delay lines / phases of the generic unison (all sources except Wavetable and Alpha Juno)\n'
    '    float[196608] gUniBuf;\n    int[64]       gUniPos;\n    float[1024]   gUniPh;\n\n'
    '    // wavetable unison (per slot, up to 7 voices)\n')
dsp = r'''    // ---------------- UNI-ALL: generic unison for the other sources ----------------
    float uniTap (int bb, int pos, float d)
    {
        float p  = float (pos) - d;
        int   i  = int (floor (p));
        float fr = p - float (i);
        float a  = gUniBuf.at (bb + (i & 4095));
        float b  = gUniBuf.at (bb + ((i + 1) & 4095));
        return a + (b - a) * fr;
    }

    float<2> uniGeneric (int vi, int o, float sL, float sR, bool stereo)
    {
        int   vo   = vi * 6 + o;
        int   bb   = vo * 4096;
        int   n    = clamp (uniCnt.at (o), 1, 16);
        float m    = stereo ? (sL + sR) * 0.5f : sL;
        float sd   = stereo ? (sL - sR) * 0.5f : 0.0f;
        int   pos  = gUniPos.at (vo);
        float wnd  = clamp (0.035f * float (processor.frequency), 256.0f, 3800.0f);
        float invW = 1.0f / wnd;
        float udr  = clamp (opv (o, 28), 0.0f, 1.0f) * 0.007f;
        float oL   = 0.0f;
        float oR   = 0.0f;

        gUniBuf.at (bb + pos) = m;

        for (int j = 0; j < n; ++j)
        {
            int   si    = o * 16 + j;
            float ratio = uniRatio.at (si) * (1.0f + udr * uniDriftRaw (vi, o, j, udr > 0.0f));
            float v     = m;

            if (abs (ratio - 1.0f) > 0.00005f)
            {
                int   pi2 = vo * 16 + j;
                float phi = gUniPh.at (pi2) + (1.0f - ratio) * invW;
                phi -= float (floor (phi));
                gUniPh.at (pi2) = phi;

                float sn = float (sin (3.14159265f * phi));
                float w1 = sn * sn;
                float w2 = 1.0f - w1;
                float p2 = phi + 0.5f;
                if (p2 >= 1.0f) p2 -= 1.0f;
                v = uniTap (bb, pos, phi * wnd + 2.0f) * w1 + uniTap (bb, pos, p2 * wnd + 2.0f) * w2;
            }

            oL += v * uniGL.at (si);
            oR += v * uniGR.at (si);
        }

        gUniPos.at (vo) = (pos + 1) & 4095;
        return float<2> (oL + sd, oR - sd);
    }

    void uniGenReset (int vi, int o)
    {
        int vo = vi * 6 + o;

        for (int k = 0; k < 4096; ++k)
            gUniBuf.at (vo * 4096 + k) = 0.0f;

        for (int j = 0; j < 16; ++j)
            gUniPh.at (vo * 16 + j) = float (j) / 16.0f;
    }

'''
rep('    // UNI-DSP-END\n', dsp + '    // UNI-DSP-END\n')
rep('                    resetWtUni (v, o);\n                    phyNoteOn (v, o);', '                    resetWtUni (v, o);\n                    uniGenReset (v, o);   // UNI-ALL\n                    phyNoteOn (v, o);')
rep('                    // ----- filter envelope of the slot -----\n',
    '                    if (ty != 0 && ty != 4 && uniCnt.at (o) > 1)   // UNI-ALL: the sources without their own unison\n'
    '                    {\n                        float<2> uw = uniGeneric (i, o, sL, sR, stereo);\n                        sL = uw[0];\n                        sR = uw[1];\n                        stereo = true;\n                    }\n\n'
    '                    // ----- filter envelope of the slot -----\n')
open(path, 'w').write(src)
print('ok')
