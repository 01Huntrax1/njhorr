#!/usr/bin/env python3
"""Idempotent, marker INSPIRATOR4-DSP: MIDI import for the Inspirator.  The UI quantises a dropped MIDI file to 96 ticks per quarter
and sends it as InsImportChunk events { offset, count, total, bars, data[] } (data = pairs grid*128+pitch, len*128+vel, up to 128 notes
per chunk).  Generator "Import" (7139 = 5) plays the imported notes (all modes), the post-stage (Mutate, Ghost, Voicing ...) varies them;
the pitch steps of the imported melody train the Markov chain when Variant % 4 == 3 ("Custom")."""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(root, 'patch', 'Eisenpuls_Synth.cmajor')
src = open(path).read()
if 'INSPIRATOR4-DSP' in src:
    print('already applied'); sys.exit(0)
def rep(old, new):
    global src
    assert src.count(old) == 1, (old[:70], src.count(old))
    src = src.replace(old, new)

rep('    struct LfoShapeChunk\n', '''    // INSPIRATOR4-DSP
    struct InsImportChunk
    {
        int        offset;
        int        count;
        int        total;
        int        bars;
        float[256] data;
    }

    struct LfoShapeChunk
''')
rep('    input event LfoShapeChunk lfoShapeLoad;', '    input event InsImportChunk insImport;\n    input event LfoShapeChunk lfoShapeLoad;')
CODE = r'''
    // ---- INSPIRATOR4-DSP: imported MIDI pattern ----
    int[512] ins_imGrid;
    int[512] ins_imLen;
    int[512] ins_imPitch;
    int[512] ins_imVel;
    int ins_imCount = 0;
    int ins_imBars = 0;

    int ins_deltaClass (int semis)
    {
        if (semis <= -5) return 0;
        if (semis <= -3) return 1;
        if (semis <= -1) return 2;
        if (semis == 0)  return 3;
        if (semis <= 2)  return 4;
        if (semis <= 4)  return 5;
        return 6;
    }

    event insImport (InsImportChunk c)
    {
        if (c.offset == 0) { ins_imCount = 0; ins_imDeltaCount = 0; }
        ins_imBars = ins_clampi (c.bars, 0, 8);
        for (int i = 0; i < c.count && i < 128; ++i)
        {
            if (ins_imCount < 512)
            {
                int a = ins_roundi (c.data.at (2 * i));
                int b = ins_roundi (c.data.at (2 * i + 1));
                ins_imGrid.at (ins_imCount) = a / 128;
                ins_imPitch.at (ins_imCount) = a % 128;
                ins_imLen.at (ins_imCount) = b / 128;
                ins_imVel.at (ins_imCount) = ins_clampi (b % 128, 1, 127);
                ins_imCount += 1;
            }
        }
        if (c.offset + c.count >= c.total)
        {
            // pitch steps of the melody (lowest voice per onset is good enough) for the Custom Markov corpus
            int prev = -1;
            int lastG = -1;
            for (int i = 0; i < ins_imCount && ins_imDeltaCount < 64; ++i)
            {
                if (ins_imGrid.at (i) != lastG)
                {
                    if (prev >= 0)
                    {
                        ins_imDelta.at (ins_imDeltaCount) = ins_deltaClass (ins_imPitch.at (i) - prev);
                        ins_imDeltaCount += 1;
                    }
                    prev = ins_imPitch.at (i);
                    lastG = ins_imGrid.at (i);
                }
            }
        }
        ins_dirty = true;
    }

    void ins_genImport()
    {
        int shift = 12 * ins_pOctave;
        for (int i = 0; i < ins_imCount; ++i)
        {
            int g = ins_imGrid.at (i);
            if (g >= 0 && g < ins_loopTicks)
            {
                int v = ins_clampi (ins_imVel.at (i) + (ins_pVel - 90) / 2 + ins_humanV (i), 1, 127);
                ins_rawAdd (g, ins_humanT (i), ins_maxi (4, ins_imLen.at (i) * ins_pGate / 100), ins_imPitch.at (i) + shift, v);
            }
        }
    }
'''
rep('    void ins_regenerate()\n', CODE + '\n    void ins_regenerate()\n')
rep('        if (ins_pGen > 0 && ins_pMode >= 1) ins_genAlt (ins_pMode);', '        if (ins_pGen == 5 && ins_imCount > 0) ins_genImport();\n        else if (ins_pGen >= 1 && ins_pGen <= 4 && ins_pMode >= 1) ins_genAlt (ins_pMode);')
open(path, 'w').write(src)
print('applied')
