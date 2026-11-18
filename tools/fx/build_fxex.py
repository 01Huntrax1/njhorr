#!/usr/bin/env python3
"""Idempotent, marker FX-EX: four effect specific extra parameters for every effect type (ids 11700 + 4 * g + k, g = global slot like FX-WET).
Every type gets four of these tools (neutral at 0, the effect sounds as before while all four are 0):
  Pre HP / Pre LP (filter the input of the effect), Gate (noise gate on the input), Pre Delay (0-250 ms delay of the input, rack slots only),
  Duck / Release (the wet signal ducks while the input plays), Warmth / Air (low / high shelf boost of the wet signal), Pan Rate / Pan Depth (auto pan of the
  wet signal), Trim (output attenuation 0..-24 dB).
Order of operations: input -> [Pre HP, Pre LP, Gate, Pre Delay] -> effect -> [Duck, Warmth, Air, Pan, Trim] -> FX-WET (P7..P10) -> Mix.
Also writes native_ui/NjoFxEx.h (tool table and texts for the editor).   build_fxex.py [patch dir]"""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
P = os.path.join(pdir, 'Eisenpuls_Synth.cmajor'); IP = os.path.join(pdir, 'index.js')
src = open(P).read(); idx = open(IP).read()
if 'FX-EX: effect specific extra' in src:
    print('already applied'); sys.exit(0)
def rep(old, new, s='src'):
    global src, idx
    t = src if s == 'src' else idx
    assert t.count(old) == 1, (old[:70], t.count(old))
    t = t.replace(old, new)
    if s == 'src': src = t
    else: idx = t
HP, LP, GATE, PD, DUCK, REL, WARM, AIR, PRATE, PDEP, TRIM = range(1, 12)
DIST = [HP, LP, GATE, TRIM]; TIME = [PD, DUCK, REL, AIR]; MOD = [PRATE, PDEP, WARM, AIR]; FLT = [GATE, WARM, AIR, TRIM]
TAB = {t: DIST for t in (1, 2, 14, 15, 19, 20, 21, 22, 28, 34)}
TAB.update({t: TIME for t in (3, 8, 12, 29, 31, 32, 33)})
TAB.update({t: MOD for t in (4, 5, 6, 7, 16)})
TAB.update({t: FLT for t in (9, 10, 13, 17, 18, 23, 24, 25, 26, 27)})
TAB[11] = [HP, GATE, AIR, TRIM]; TAB[30] = [DUCK, WARM, AIR, TRIM]
TAB[35] = [PD, DUCK, REL, AIR]; TAB[36] = [HP, GATE, WARM, TRIM]; TAB[37] = [HP, GATE, AIR, TRIM]   # Yaybahar parts (build_ybparts.py)
assert sorted(TAB) == list(range(1, 38))
NTY = 40
flat = []
for t in range(NTY): flat += TAB.get(t, [0, 0, 0, 0])
RN = ['Main', 'Bus 1', 'Bus 2']
def name(g):
    if g < 30: return '%s FX %d' % (RN[g // 10], g % 10 + 1)
    if g < 48: return '%s FX %d' % (RN[(g - 30) // 6], 11 + (g - 30) % 6)
    return 'OSC %d FX %d' % ((g - 48) // 16 + 1, (g - 48) % 16 + 1)
decl = ''; hand = ''
for g in range(144):
    for k in range(4):
        i = 11700 + 4 * g + k
        decl += '    input event float param%d [[ name: "%s Ext %d", min: 0.0, max: 1.0, init: 0.0 ]];   // FX-EX\n' % (i, name(g), k + 1)
        hand += '    event param%d (float v) { %s (%d, %d, v); }\n' % (i, 'fxExSet' if g < 48 else 'fxExSetO', g, k)
rep('    // EURO\n', decl + '    // EURO\n')
rep('    // RESO-HAND-BEGIN\n', hand + '    // RESO-HAND-BEGIN\n')
rep('    float[4992] fxP;', '''    float[8704] fxE;    // FX-EX: per slot 8 floats: 4 values, active flag, dirty flag, type of the last coefficient calculation
    float[8704] fxEc;   // FX-EX: coefficients per slot (4 per tool, duck release, pan increment, shelf coefficients)
    float[17408] fxW;   // FX-EX: filter / envelope states (16 per slot)
    float[1572864] fxPd; // FX-EX: pre delay lines of the 48 rack slots (2 x 16384)
    const int[160] fxExTab = (%s);
    float[4992] fxP;''' % ', '.join(str(v) for v in flat))
CODE = '''    // ================= FX-EX: effect specific extra parameters =================
    void fxExSet (int s, int k, float v)
    {
        int q = s * 8;
        fxE.at (q + k) = v;
        fxE.at (q + 5) = 1.0f;
        bool act = false;

        for (int i = 0; i < 4; ++i)
            if (fxE.at (q + i) > 0.002f)
                act = true;

        fxE.at (q + 4) = act ? 1.0f : 0.0f;
    }

    void fxExSetO (int g, int k, float v)
    {
        for (int vi = 0; vi < 8; ++vi)
            fxExSet (48 + vi * 96 + (g - 48), k, v);
    }

    float fxExVal (int s, int ty, int tool)
    {
        for (int k = 0; k < 4; ++k)
            if (fxExTab.at (ty * 4 + k) == tool)
                return fxE.at (s * 8 + k);

        return 0.0f;
    }

    float fxExA (float hz)
    {
        return 1.0f - float (exp (-6.283185307f * hz / float (processor.frequency)));
    }

    void fxExRecalc (int s, int ty)
    {
        int   q  = s * 8;
        int   cq = s * 8;
        float sr = float (processor.frequency);

        for (int k = 0; k < 4; ++k)
        {
            int   tool = fxExTab.at (ty * 4 + k);
            float v    = fxE.at (q + k);
            float c    = 0.0f;

            if (tool == 1)      c = fxExA (20.0f * float (pow (50.0f, v)));
            else if (tool == 2) c = fxExA (20000.0f * float (pow (0.075f, v)));
            else if (tool == 3) c = float (pow (10.0f, (-70.0f + 50.0f * v) / 20.0f));
            else if (tool == 4) c = clamp (v * 0.25f * sr, 0.0f, 16000.0f);
            else if (tool == 7 || tool == 8) c = float (pow (10.0f, 9.0f * v / 20.0f)) - 1.0f;
            else if (tool == 11) c = float (pow (10.0f, -24.0f * v / 20.0f));

            fxEc.at (cq + k) = c;
        }

        float rv  = fxExVal (s, ty, 6);
        float ms  = fxExTab.at (ty * 4) == 6 || fxExTab.at (ty * 4 + 1) == 6 || fxExTab.at (ty * 4 + 2) == 6 || fxExTab.at (ty * 4 + 3) == 6 ? 40.0f * float (pow (37.5f, rv)) : 250.0f;
        fxEc.at (cq + 4) = 1.0f - float (exp (-1.0f / (ms * 0.001f * sr)));
        fxEc.at (cq + 5) = 0.1f * float (pow (80.0f, fxExVal (s, ty, 9))) / sr;
        fxEc.at (cq + 6) = fxExA (200.0f);
        fxEc.at (cq + 7) = fxExA (6000.0f);
        fxE.at (q + 5) = 0.0f;
        fxE.at (q + 6) = float (ty);
    }

    // input side: Pre HP, Pre LP, Gate, Pre Delay
    float<2> fxExPre (int s, float<2> x)
    {
        int ty = fxType.at (s);
        int q  = s * 8;
        int wb = s * 16;

        if (fxE.at (q + 5) > 0.5f || fxE.at (q + 6) != float (ty))
            fxExRecalc (s, ty);

        float l = x[0];
        float r = x[1];

        for (int k = 0; k < 4; ++k)
        {
            int tool = fxExTab.at (ty * 4 + k);

            if (tool < 1 || tool > 4 || fxE.at (q + k) <= 0.002f)
                continue;

            float c = fxEc.at (q + k);

            if (tool == 1)
            {
                fxW.at (wb)     += c * (l - fxW.at (wb));
                fxW.at (wb + 1) += c * (r - fxW.at (wb + 1));
                l -= fxW.at (wb);
                r -= fxW.at (wb + 1);
            }
            else if (tool == 2)
            {
                fxW.at (wb + 2) += c * (l - fxW.at (wb + 2));
                fxW.at (wb + 3) += c * (r - fxW.at (wb + 3));
                fxW.at (wb + 4) += c * (fxW.at (wb + 2) - fxW.at (wb + 4));
                fxW.at (wb + 5) += c * (fxW.at (wb + 3) - fxW.at (wb + 5));
                l = fxW.at (wb + 4);
                r = fxW.at (wb + 5);
            }
            else if (tool == 3)
            {
                float det = max (abs (l), abs (r));
                float en  = fxW.at (wb + 6);
                en += (det > en ? 0.05f : 0.0005f) * (det - en);
                fxW.at (wb + 6) = en;
                float gt = fxW.at (wb + 7);
                gt += ((en > c ? 1.0f : 0.0f) - gt) * (en > c ? 0.01f : 0.001f);
                fxW.at (wb + 7) = gt;
                l *= gt;
                r *= gt;
            }
            else if (s < 48)
            {
                int base = s * 32768;
                int pos  = int (fxW.at (wb + 8));
                fxPd.at (base + pos)         = l;
                fxPd.at (base + 16384 + pos) = r;
                int rp = (pos - int (c)) & 16383;
                l = fxPd.at (base + rp);
                r = fxPd.at (base + 16384 + rp);
                fxW.at (wb + 8) = float ((pos + 1) & 16383);
            }
        }

        return float<2> (l, r);
    }

    // output side: Duck, Warmth, Air, Pan, Trim (x0 = the input of the slot)
    float<2> fxExPost (int s, float<2> y, float<2> x0)
    {
        int ty = fxType.at (s);
        int q  = s * 8;
        int wb = s * 16;
        float l = y[0];
        float r = y[1];

        for (int k = 0; k < 4; ++k)
        {
            int tool = fxExTab.at (ty * 4 + k);

            if (tool < 5 || fxE.at (q + k) <= 0.002f)
                continue;

            float v = fxE.at (q + k);
            float c = fxEc.at (q + k);

            if (tool == 5)
            {
                float det = max (abs (x0[0]), abs (x0[1]));
                float en  = fxW.at (wb + 9);
                en += (det > en ? 0.01f : fxEc.at (q + 4)) * (det - en);
                fxW.at (wb + 9) = en;
                float dg = 1.0f - v * clamp (en * 6.0f, 0.0f, 1.0f);
                l *= dg;
                r *= dg;
            }
            else if (tool == 7)
            {
                fxW.at (wb + 10) += fxEc.at (q + 6) * (l - fxW.at (wb + 10));
                fxW.at (wb + 11) += fxEc.at (q + 6) * (r - fxW.at (wb + 11));
                l += fxW.at (wb + 10) * c;
                r += fxW.at (wb + 11) * c;
            }
            else if (tool == 8)
            {
                fxW.at (wb + 12) += fxEc.at (q + 7) * (l - fxW.at (wb + 12));
                fxW.at (wb + 13) += fxEc.at (q + 7) * (r - fxW.at (wb + 13));
                l += (l - fxW.at (wb + 12)) * c;
                r += (r - fxW.at (wb + 13)) * c;
            }
            else if (tool == 10)
            {
                float ph = fxW.at (wb + 14) + fxEc.at (q + 5);
                ph -= float (floor (ph));
                fxW.at (wb + 14) = ph;
                float pn = v * float (sin (6.283185307f * ph));
                l *= pn > 0.0f ? 1.0f - pn : 1.0f;
                r *= pn < 0.0f ? 1.0f + pn : 1.0f;
            }
            else if (tool == 11)
            {
                l *= c;
                r *= c;
            }
        }

        return float<2> (l, r);
    }

'''
rep('    // One slot: dry/wet mix of the selected effect;', CODE + '    // One slot: dry/wet mix of the selected effect;')
rep('        float<2> y = x;\n\n        if (ty == 1)       y = fxDist   (s, x);', '        float<2> x0 = x;   // FX-EX\n        bool     exOn = fxE.at (s * 8 + 4) > 0.5f;\n\n        if (exOn)\n            x = fxExPre (s, x);\n\n        float<2> y = x;\n\n        if (ty == 1)       y = fxDist   (s, x);')
rep('        y = fxWet (s, y);   // FX-WET\n\n        float mix = clamp (fxMix.at (s), 0.0f, 1.0f);\n        float<2> res = x + (y - x) * mix;', '        if (exOn)\n            y = fxExPost (s, y, x0);   // FX-EX\n\n        y = fxWet (s, y);   // FX-WET\n\n        float mix = clamp (fxMix.at (s), 0.0f, 1.0f);\n        float<2> res = x0 + (y - x0) * mix;')
rep('            vzTap (x, res);   // FX-VIZ', '            vzTap (x0, res);   // FX-VIZ')
rep('        for (int i = 0; i < 8; ++i)   // FX-WET\n            fxX.at (s * 8 + i) = 0.0f;\n', '        for (int i = 0; i < 8; ++i)   // FX-WET\n            fxX.at (s * 8 + i) = 0.0f;\n\n        for (int i = 0; i < 16; ++i)   // FX-EX\n            fxW.at (s * 16 + i) = 0.0f;\n')
SP = '''    // FX-EX: effect specific extra parameters, ids 11700 + 4 * g + k (g like FX-WET); the meaning follows the effect type (native_ui/NjoFxEx.h)
    for (let g = 0; g < 144; g++) for (let k = 0; k < 4; k++) L.push([11700 + 4 * g + k, wetName(g) + " Ext " + (k + 1), 0, 1, 0, "", "sld", null, 1, "Ext " + (k + 1)]);
'''
rep('    // EURO: Eurorack rack of Njohrr Modular\n', SP + '    // EURO: Eurorack rack of Njohrr Modular\n', 'idx')
open(P, 'w').write(src); open(IP, 'w').write(idx)

names = {HP: 'Pre HP', LP: 'Pre LP', GATE: 'Gate', PD: 'Pre Delay', DUCK: 'Duck', REL: 'Release', WARM: 'Warmth', AIR: 'Air', PRATE: 'Pan Rate', PDEP: 'Pan Depth', TRIM: 'Trim'}
hdr = '''// FX-EX (generated by tools/fx/build_fxex.py): the four effect specific extra parameters of every effect type.  Tool numbers: 1 Pre HP, 2 Pre LP, 3 Gate,
// 4 Pre Delay, 5 Duck, 6 Release, 7 Warmth, 8 Air, 9 Pan Rate, 10 Pan Depth, 11 Trim
#pragma once
#include <juce_core/juce_core.h>
#include <cmath>
namespace njo
{
    inline int fxExId (int g, int k) { return 11700 + 4 * g + k; }
    inline const int* fxExTools (int ty)
    {
        static const int tab[%d] = { %s };
        return tab + 4 * juce::jlimit (0, %d, ty);
    }
    inline const char* fxExName (int tool)
    {
        static const char* n[] = { "", %s };
        return n[juce::jlimit (0, 11, tool)];
    }
    inline juce::String fxExText (int tool, float v)
    {
        if (tool == 1) return v < 0.002f ? juce::String ("Off") : juce::String (juce::roundToInt (20.0 * std::pow (50.0, (double) v))) + " Hz";
        if (tool == 2) return v < 0.002f ? juce::String ("Off") : juce::String (juce::roundToInt (20000.0 * std::pow (0.075, (double) v))) + " Hz";
        if (tool == 3) return v < 0.002f ? juce::String ("Off") : juce::String (juce::roundToInt (-70.0 + 50.0 * v)) + " dB";
        if (tool == 4) return juce::String (juce::roundToInt (v * 250.0f)) + " ms";
        if (tool == 5) return juce::String (juce::roundToInt (v * 100.0f)) + "%%";
        if (tool == 6) return juce::String (juce::roundToInt (40.0 * std::pow (37.5, (double) v))) + " ms";
        if (tool == 7 || tool == 8) return "+" + juce::String (v * 9.0f, 1) + " dB";
        if (tool == 9) return juce::String (0.1 * std::pow (80.0, (double) v), 2) + " Hz";
        if (tool == 10) return juce::String (juce::roundToInt (v * 100.0f)) + "%%";
        if (tool == 11) return "-" + juce::String (v * 24.0f, 1) + " dB";
        return juce::String (v, 2);
    }
}
''' % (NTY * 4, ', '.join(str(v) for v in flat), NTY - 1, ', '.join('"%s"' % names[i] for i in range(1, 12)))
open(os.path.join(root, 'native_ui', 'NjoFxEx.h'), 'w').write(hdr)
print('ok')
