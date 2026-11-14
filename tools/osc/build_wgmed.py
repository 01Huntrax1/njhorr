#!/usr/bin/env python3
"""Idempotent, marker WG-MEDIEVAL: medieval instruments for the Waveguide source (models 5..16, the old models 0..4 keep their numbers).
 Engines: 0 Karplus-Strong, 1 Bowed, 2 Clarinet (reed), 3 Banded, 4 Drum and the new 5 "blown pipe" (a tuned loop excited by breath noise).
 Characters per instrument: a second string of the course (detuned Karplus-Strong line), a drone (saw an octave below), a buzzing bridge / reed.
 5 Lute, 6 Psaltery, 7 Dulcimer, 8 Rebec, 9 Hurdy-Gurdy, 10 Shawm, 11 Crumhorn, 12 Bagpipe, 13 Recorder, 14 Tabor, 15 Handbell, 16 Medieval Harp."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'patch', 'Eisenpuls_Synth.cmajor'); IP = os.path.join(ROOT, 'patch', 'index.js'); LP = os.path.join(ROOT, 'tools', 'osc', 'layout.py')
src = open(P).read(); idx = open(IP).read(); lay = open(LP).read()
if 'WG-MEDIEVAL' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx, lay
    t = {'src': src, 'idx': idx, 'lay': lay}[s]
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    elif s == 'idx': idx = t
    else: lay = t

NAMES = ["Lute", "Psaltery", "Dulcimer", "Rebec", "Hurdy-Gurdy", "Shawm", "Crumhorn", "Bagpipe", "Recorder", "Tabor", "Handbell", "Medieval Harp"]
#            engine course(ct) drone level buzz
INST = [(0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0), (3, 0, 0, 0), (4, 0, 0, 0),
        (0, 5, 0, 0), (0, 7, 0, 0), (0, 11, 0, 0), (1, 0, 0, 0.15), (1, 0, 0.3, 0.45), (2, 0, 0, 0.25), (2, 0, 0, 0.45), (2, 0, 0.35, 0.1),
        (5, 0, 0, 0), (4, 0, 0, 0), (3, 0, 0, 0), (0, 3, 0, 0)]
# defaults of the parameters 1..15 (decay tone excite pos noise nl stretch attack snare body bodyf vel drive tension keydecay)
DEF = {
 0: [.5, .6, .6, .3, .2, 0, 0, .2, 0, 0, .4, .5, 0, 0, .3], 1: [.5, .6, .6, .3, .2, 0, 0, .2, 0, 0, .4, .5, 0, 0, .3], 2: [.5, .6, .6, .3, .2, 0, 0, .2, 0, 0, .4, .5, 0, 0, .3],
 3: [.5, .6, .6, .3, .2, 0, 0, .2, 0, 0, .4, .5, 0, 0, .3], 4: [.5, .6, .6, .3, .2, 0, 0, .2, 0, 0, .4, .5, 0, 0, .3],
 5: [.55, .45, .55, .22, .1, 0, .15, .2, 0, .55, .3, .6, 0, .1, .4],
 6: [.7, .7, .75, .15, .05, 0, .25, .2, 0, .35, .45, .6, 0, 0, .35],
 7: [.65, .8, .85, .12, .15, 0, .3, .2, 0, .4, .5, .7, 0, 0, .3],
 8: [.35, .55, .5, .22, .3, .3, 0, .35, 0, .6, .55, .5, .1, 0, .3],
 9: [.45, .5, .6, .15, .45, .2, 0, .12, 0, .5, .3, .2, .25, 0, .2],
 10: [.3, .85, .75, .8, .25, .4, 0, .15, 0, .3, .6, .5, .3, 0, .3],
 11: [.35, .4, .65, .85, .35, .6, 0, .25, 0, .2, .4, .4, .35, 0, .3],
 12: [.3, .7, .7, .7, .2, .5, 0, .3, 0, .25, .45, .1, .3, 0, .3],
 13: [.5, .55, .45, .3, .25, .1, 0, .3, 0, .15, .5, .5, 0, 0, .3],
 14: [.3, .5, .6, .4, .3, 0, .2, .2, .7, .6, .2, .7, 0, .3, .1],
 15: [.75, .75, .7, .2, .1, 0, .5, .2, 0, 0, .4, .6, 0, 0, .2],
 16: [.6, .55, .5, .35, .08, 0, .05, .2, 0, .45, .25, .5, 0, 0, .45]}
ENG_LABELS = [
 ["Decay", "Tone", "Hardness", "Pluck Pos", "Pluck Noise", "Saturation", "Stiffness", "", "", "Body", "Body Tune", "Vel > Excite", "Drive", "Tension", "Key Decay"],
 ["Loss", "Bridge Tone", "Bow Pressure", "Bow Pos", "Bow Noise", "Bow Offset", "", "Bow Attack", "", "Body", "Body Tune", "Vel > Bow", "Drive", "", "Key Decay"],
 ["Loss", "Bore Tone", "Breath", "Reed Stiff", "Breath Noise", "Reed Offset", "", "Breath Attack", "", "Body", "Body Tune", "Vel > Breath", "Drive", "", "Key Decay"],
 ["Decay", "Tone", "Hardness", "Strike Pos", "Strike Noise", "", "Mode Ratios", "", "", "Body", "Body Tune", "Vel > Strike", "Drive", "", "Key Decay"],
 ["Decay", "Tone", "Mallet", "Strike Pos", "Stick Noise", "", "Stiffness", "", "Snare", "Shell", "Shell Tune", "Vel > Strike", "Drive", "Tension", "Key Decay"],
 ["Decay", "Bore Tone", "Breath", "", "Air Noise", "Saturation", "", "Breath Attack", "", "Body", "Body Tune", "Vel > Breath", "Drive", "", "Key Decay"]]
ENGS = [i[0] for i in INST]
LABELS = ENG_LABELS[:5] + [ENG_LABELS[e] for e in ENGS[5:]]
MODELS = ["Karplus-Strong", "Bowed String", "Clarinet", "Banded Waveguide", "Drum"] + NAMES

# ---- parameter range
src, n = re.subn(r'(Waveguide Model", min: 0\.0, max: )4\.0', r'\g<1>16.0', src); assert n == 6, n
idx, n = re.subn(r'(\d+, "OSC \d Waveguide Model", 0, )4,', r'\g<1>16,', idx); assert n == 6, n
rep('const WG_MODELS = ["Karplus-Strong", "Bowed String", "Clarinet", "Banded Waveguide", "Drum"];', 'const WG_MODELS = %s;' % repr(MODELS).replace("'", '"'), 'idx')
m = re.search(r'const WG_LABELS = .*?;\n', idx); assert m
idx = idx[:m.start()] + 'const WG_LABELS = %s;\n' % repr(LABELS).replace("'", '"') + idx[m.end():]
rep('WG_MODELS = ["Karplus-Strong", "Bowed String", "Clarinet", "Banded Waveguide", "Drum"]', 'WG_MODELS = %s' % repr(MODELS), 'lay')
rep('(0,  "wmodel",   "Waveguide Model",       "Model",       0, 4, 0,', '(0,  "wmodel",   "Waveguide Model",       "Model",       0, 16, 0,', 'lay')
m = re.search(r'WG_LABELS = \[\n.*?\n\]\n', lay, re.S); assert m
lay = lay[:m.start()] + 'WG_LABELS = [\n' + ''.join(' %s,\n' % repr(l) for l in LABELS) + ']\n' + lay[m.end():]

# ---- tables and the model mapping
rep('    const float[5]  wgOut = (1.1f, 2.0f, 1.0f, 0.8f, 0.4f);                        // output level per model\n',
    '    const float[6]  wgOut = (1.1f, 2.0f, 1.0f, 0.8f, 0.4f, 3.0f);                  // output level per engine\n'
    '    // WG-MEDIEVAL: instrument (model value 0..16) -> engine, second string detune (cents), drone level (saw an octave below), buzz\n'
    '    const int[17]   wgEng    = (%s);\n    const float[17] wgCourse = (%s);\n    const float[17] wgDrone  = (%s);\n    const float[17] wgBuzz   = (%s);\n' % (
        ', '.join(str(i[0]) for i in INST), ', '.join('%.1ff' % i[1] for i in INST), ', '.join('%.2ff' % i[2] for i in INST), ', '.join('%.2ff' % i[3] for i in INST)))
rep('    const float[16] wgHi = (4.0f,', '    const float[16] wgHi = (16.0f,')
rep('        int   mdl  = clamp (int (wgq (o, 0) + 0.5f), 0, 4);\n', '        int   inst = clamp (int (wgq (o, 0) + 0.5f), 0, 16);\n        int   mdl  = wgEng.at (inst);\n')

# wgUpdate: instrument + flute block + second string
rep('    void wgUpdate (int vi, int o, int mdl, float f0, float sr, bool trig)\n    {\n        int   sb   = o * 192;\n',
    '    void wgUpdate (int vi, int o, int mdl, float f0, float sr, bool trig)\n    {\n        int   sb   = o * 192;\n        int   inst = clamp (int (wgq (o, 0) + 0.5f), 0, 16);\n')
rep('            wgPut (vi, sb + 21, cd);\n            wgPut (vi, sb + 28, wgq (o, 6));\n        }\n',
    '''            wgPut (vi, sb + 21, cd);
            wgPut (vi, sb + 28, wgq (o, 6));

            // WG-MEDIEVAL: second string of the course, a few cents away (own delay line, loop low-pass and interpolation allpass)
            float cc = wgCourse.at (inst);

            if (cc > 0.0f)
            {
                float f2   = min (f * float (pow (2.0f, cc / 1200.0f)), sr * 0.45f);
                float T2   = sr / f2;
                float w2   = tp * f2 / sr;
                float rest2 = T2 - wgLpDelay (a, w2);
                float Mf2  = max (floor (rest2 - 0.5f), 1.0f);
                float ta2  = clamp (rest2 - Mf2, 0.3f, 1.7f);
                wgPut (vi, sb + 100, Mf2);
                wgPut (vi, sb + 101, wgApCoef (ta2, w2));
                wgPut (vi, sb + 102, min (float (exp (-6.9078f * T2 / (sr * t60))) / wgLpGain (a, w2), 0.99995f));
                wgPut (vi, sb + 103, a);
            }
            else
                wgPut (vi, sb + 100, 0.0f);
        }
        else if (mdl == 5)
        {
            // blown pipe: a tuned loop (as Karplus-Strong, without stiffness) that is fed with breath noise
            float a    = 0.05f + 0.6f * it;
            float rest = T - wgLpDelay (a, w0);
            float Mf   = max (floor (rest - 0.5f), 2.0f);
            float ta   = clamp (rest - Mf, 0.3f, 1.7f);
            float br   = wgq (o, 3);
            wgPut (vi, sb + 17, Mf);
            wgPut (vi, sb + 18, wgApCoef (ta, w0));
            wgPut (vi, sb + 19, (1.0f + 0.02f + 0.03f * (wgq (o, 1) - 0.3f) + 0.01f * br) / wgLpGain (a, w0));   // Decay sets the loop gain around 1: above 1 it self-oscillates at the tuned pitch (tanh limits)
            wgPut (vi, sb + 20, a);
            wgPut (vi, sb + 21, 0.0f);
            wgPut (vi, sb + 30, 0.004f + 0.05f * br * br * (0.7f + 0.3f * wgGet (vi, sb + 35)));
            wgPut (vi, sb + 31, wgq (o, 5));
            wgPut (vi, sb + 28, wgq (o, 6));
            wgPut (vi, sb + 23, 1.0f - float (exp (-1.0f / (sr * 0.005f * float (pow (200.0f, wgq (o, 8)))))));
        }
''')
# the Drum block was the final else: make it an explicit branch
rep('        else\n        {\n            // Drum: 12 modes of a circular membrane', '        else if (mdl == 4)\n        {\n            // Drum: 12 modes of a circular membrane')

# trigger: fill the second string too
rep('''            float mean = sum / float (M);

            for (int n = 0; n < M; ++n)
            {
                int idx = db + ((w - M + n) & 8191);
                voices.at (vi).wgd.at (idx) = (voices.at (vi).wgd.at (idx) - mean) * 1.6f * vk;
            }
        }
''', '''            float mean = sum / float (M);

            for (int n = 0; n < M; ++n)
            {
                int idx = db + ((w - M + n) & 8191);
                voices.at (vi).wgd.at (idx) = (voices.at (vi).wgd.at (idx) - mean) * 1.6f * vk;
            }

            int M2 = int (wgGet (vi, sb + 100));   // WG-MEDIEVAL: the second string of the course gets its own pluck

            if (M2 > 0)
            {
                lp  = 0.0f;
                sum = 0.0f;

                for (int n = 0; n < M2; ++n)
                {
                    float x   = (float (n) + 0.5f) / float (M2);
                    float tri = x < pos ? x / pos : (1.0f - x) / (1.0f - pos);
                    float e   = (1.0f - nz) * tri + nz * nextNoise() * 0.5f;
                    lp = (1.0f - ae) * e + ae * lp;
                    voices.at (vi).wgd.at (db + 8192 + ((w - M2 + n) & 8191)) = lp;
                    sum += lp;
                }

                float mean2 = sum / float (M2);

                for (int n = 0; n < M2; ++n)
                {
                    int idx = db + 8192 + ((w - M2 + n) & 8191);
                    voices.at (vi).wgd.at (idx) = (voices.at (vi).wgd.at (idx) - mean2) * 1.6f * vk;
                }
            }
        }
''')

# new voices
rep('    float wgBow (int vi, int o)\n', '''    // WG-MEDIEVAL: second string of the course (line at wgd + 8192; coefficients at 100..103, states 105 / 108; shares the write pointer of wgKS)
    float wgKS2 (int vi, int o)
    {
        int   sb  = o * 192;
        int   db  = o * 16384 + 8192;
        int   w   = int (wgGet (vi, sb));
        int   M   = int (wgGet (vi, sb + 100));
        float ci  = wgGet (vi, sb + 101);
        float g   = wgGet (vi, sb + 102);
        float a   = wgGet (vi, sb + 103);
        float v   = voices.at (vi).wgd.at (db + ((w - M) & 8191));
        float lp  = (1.0f - a) * v + a * wgGet (vi, sb + 105);
        wgPut (vi, sb + 105, lp);
        float yi  = ci * lp + wgGet (vi, sb + 108);
        wgPut (vi, sb + 108, lp - ci * yi);
        float y   = yi * g;
        voices.at (vi).wgd.at (db + (w & 8191)) = y;
        return y;
    }

    // WG-MEDIEVAL: blown pipe: the tuned loop plus breath noise (amplitude from Breath, attack from Breath Attack), tanh limited
    float wgFlute (int vi, int o)
    {
        int   sb  = o * 192;
        int   db  = o * 16384;
        int   w   = int (wgGet (vi, sb));
        int   M   = int (wgGet (vi, sb + 17));
        float ci  = wgGet (vi, sb + 18);
        float g   = wgGet (vi, sb + 19);
        float a   = wgGet (vi, sb + 20);
        float env = wgGet (vi, sb + 5);
        env += wgGet (vi, sb + 23) * (1.0f - env);
        wgPut (vi, sb + 5, env);
        float nz  = nextNoise();
        float inj = env * wgGet (vi, sb + 30) * nz;
        float v   = voices.at (vi).wgd.at (db + ((w - M) & 8191));
        float lp  = (1.0f - a) * v + a * wgGet (vi, sb + 14);
        wgPut (vi, sb + 14, lp);
        float yi  = ci * lp + wgGet (vi, sb + 16);
        wgPut (vi, sb + 16, lp - ci * yi);
        float k   = 2.0f + 3.0f * wgGet (vi, sb + 28);
        float y   = float (tanh ((yi * g + inj) * k)) / k;
        voices.at (vi).wgd.at (db + (w & 8191)) = y;
        wgPut (vi, sb, float ((w + 1) & 65535));
        return y + wgGet (vi, sb + 31) * inj * 0.6f;
    }

    float wgBow (int vi, int o)
''')

# step: engines, course, drone, buzz
rep('''        if (mdl == 0)
            y = wgKS (vi, o);
        else if (mdl == 1)''', '''        if (mdl == 0)
        {
            float y2 = wgGet (vi, sb + 100) > 0.5f ? wgKS2 (vi, o) : 0.0f;   // WG-MEDIEVAL: the second string reads before wgKS advances the pointer
            y = wgKS (vi, o);

            if (wgGet (vi, sb + 100) > 0.5f)
                y = (y + y2) * 0.6f;
        }
        else if (mdl == 1)''')
rep('''        else
            y = wgDrum (vi, o, wgPulse (vi, sb, wgq (o, 5)));

        y *= wgOut.at (mdl);''', '''        else if (mdl == 4)
            y = wgDrum (vi, o, wgPulse (vi, sb, wgq (o, 5)));
        else
            y = wgFlute (vi, o);

        y *= wgOut.at (mdl);''')
rep('        float dr = wgGet (vi, sb + 33);\n\n        if (dr > 0.001f)\n        {\n            float gd = 1.0f + dr * 6.0f;',
    '''        // WG-MEDIEVAL: buzzing bridge / reed and the drone (saw an octave below, softened by a one-pole low-pass)
        float bz = wgBuzz.at (inst);

        if (bz > 0.0f)
            y = y * (1.0f - 0.3f * bz) + bz * 0.45f * float (tanh (y * 12.0f));

        float dl = wgDrone.at (inst);

        if (dl > 0.0f)
        {
            float ph = wgGet (vi, sb + 44) + f0 * 0.5f / sr;
            ph -= floor (ph);
            wgPut (vi, sb + 44, ph);
            float dlp = wgGet (vi, sb + 45);
            dlp += 0.12f * ((2.0f * ph - 1.0f) - dlp);
            wgPut (vi, sb + 45, dlp);
            y += dl * dlp;
        }

        float dr = wgGet (vi, sb + 33);

        if (dr > 0.001f)
        {
            float gd = 1.0f + dr * 6.0f;''')
rep('    // WG-DSP-END', '    // WG-MEDIEVAL\n    // WG-DSP-END')
open(P, 'w').write(src); open(IP, 'w').write(idx); open(LP, 'w').write(lay)

# ---- UI tables (native_ui/NjoWg.h)
H = os.path.join(ROOT, 'native_ui', 'NjoWg.h'); h = open(H).read()
a = h.index('    // labels of the parameters 1..15'); b = h.rindex('}')
cpp_lab = ',\n'.join('            { %s }' % ', '.join('"%s"' % x for x in row) for row in LABELS)
cpp_def = ',\n'.join('            { %s }' % ', '.join('%.2ff' % v for v in DEF[i]) for i in range(17))
cpp_names = ', '.join('"%s"' % n for n in MODELS)
h = h[:a] + '''    // labels of the parameters 1..15 for every model ("" = the model does not use the parameter); models 5..16 are the medieval instruments (WG-MEDIEVAL)
    inline const char* label (int model, int j)
    {
        static const char* const t[17][15] = {
''' + cpp_lab + '''
        };
        return j < 1 || j > 15 || model < 0 || model > 16 ? "" : t[model][j - 1];
    }
    // start values of the parameters 1..15 that the model list sets when a model is picked (Karplus-Strong .. Drum keep the values the user has)
    inline float defaultOf (int model, int j)
    {
        static const float t[17][15] = {
''' + cpp_def + '''
        };
        return j < 1 || j > 15 || model < 0 || model > 16 ? 0.0f : t[model][j - 1];
    }
    inline const char* modelName (int model)
    {
        static const char* const n[17] = { ''' + cpp_names + ''' };
        return n[model < 0 ? 0 : (model > 16 ? 16 : model)];
    }
''' + h[b:]
open(H, 'w').write(h)
print('WG-MEDIEVAL applied')
