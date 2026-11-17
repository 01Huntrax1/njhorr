#!/usr/bin/env python3
"""Idempotent, marker FX-FILTERS: 13 more filter types (modes 33..45) for the Filter effect (the oscillator voice filters are untouched):
  33 Polivoks LP, 34 Polivoks BP, 35 Polivoks HP   - 12 dB OTA state-variable filter with hard (asymmetric) limiting of the integrators, grainy resonance
  36 OTA LP24 (Jupiter / IR3109), 37 CEM LP24 (Prophet-5 / CEM3320), 38 SSM LP24 (SSM2044, bass thinning resonance)
  39 SEM LP, 40 SEM BP, 41 SEM Notch, 42 SEM HP   - Oberheim SEM 12 dB multimode (soft resonance limit, light saturation)
  43 Diode LP (TB-303 like ladder with stage coupling), 44 Steiner-Parker LP, 45 Steiner-Parker HP
Run after build_scream.py.   build_filters.py [patch dir]"""
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'patch')
path = os.path.join(pdir, 'Eisenpuls_Synth.cmajor')
s = open(path).read()
if 'FX-FILTERS' in s:
    print('already applied'); sys.exit(0)
NMAX = 45
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:70], s.count(old))
    s = s.replace(old, new)

s, n = re.subn(r'(fxMode\.at \([^)]*\) = clamp \(int \(v \+ 0\.5f\), 0, )32\)', r'\g<1>%d)' % NMAX, s); print('clamps', n)
s, n = re.subn(r'(FX \d+ Mode",\s+min: 0\.0, max: )32\.0', r'\g<1>%d.0' % NMAX, s); print('decls', n)

helpers = '''    // FX-FILTERS: OTA style saturation (slope 1 at 0, limit +-2) and an OTA one-pole stage (state at fxF[idx])
    float fxOta (float d)
    {
        return softClip (d * 0.5f) * 2.0f;
    }

    float fxOtaPole (int idx, float x, float g)
    {
        float gg = g / (1.0f + g);
        float st = fxF.at (idx);
        float v  = fxOta (x - st) * gg;
        float lp = v + st;
        fxF.at (idx) = lp + v;
        return lp;
    }

    // Polivoks / Steiner-Parker style state variable stage: the integrator states are limited (asym > 0 makes the limit asymmetric); modes 0 LP, 1 BP, 2 HP, 3 notch
    float fxLimSvf (int idx, float x, float g, float k, float lim, float asym, int mode)
    {
        float a1 = 1.0f / (1.0f + g * (g + k));
        float a2 = g * a1;
        float a3 = g * a2;
        float s1 = fxF.at (idx);
        float s2 = fxF.at (idx + 1);
        float v3 = x - s2;
        float v1 = a1 * s1 + a2 * v3;
        float v2 = s2 + a2 * s1 + a3 * v3;
        float n1 = 2.0f * v1 - s1;
        float n2 = 2.0f * v2 - s2;

        n1 = softClip (n1 / lim + asym * n1 * n1 / (lim * lim)) * lim;
        n2 = softClip (n2 / (lim * 1.6f)) * lim * 1.6f;

        fxF.at (idx)     = n1;
        fxF.at (idx + 1) = n2;

        if (mode == 1) return v1 * k;
        if (mode == 2) return x - k * v1 - v2;
        if (mode == 3) return x - k * v1;
        return v2;
    }

'''
rep('    float fxFilterX (int s, int ch, float x, float g, float k, float res, float fc, int ft)\n', helpers +
    '    float fxFilterX (int s, int ch, float x, float g, float k, float res, float fc, int ft)\n')

body = '''        if (ft >= 33)
        {
            // FX-FILTERS: more filter models
            if (ft <= 35)
            {
                // Polivoks: 12 dB OTA state variable filter, hard asymmetric limiting, grainy resonance; 33 LP, 34 BP, 35 HP
                float xi = x * 1.3f + 0.04f * x * x;
                float kp = max (0.03f, 2.0f - 1.97f * res);
                return fxLimSvf (b, xi, g, kp, 0.9f, 0.18f, ft == 33 ? 0 : (ft == 34 ? 1 : 2)) * 1.25f;
            }

            if (ft >= 36 && ft <= 38)
            {
                // four OTA poles with feedback: 36 OTA (Jupiter / IR3109), 37 CEM (Prophet, resonance compensation), 38 SSM (bass thinning resonance)
                float y4p = fxF.at (b + 4);
                float y3p = fxF.at (b + 5);
                float kr  = res * (ft == 37 ? 4.2f : 4.0f);
                float fbv = y4p;

                if (ft == 37) fbv = y4p + 0.15f * (y3p - y4p);
                if (ft == 38) fbv = y4p - fxOnePole (b + 8, y4p, g * 0.15f);   // feedback without lows

                float u  = fxOta (x * (ft == 37 ? 1.1f : 1.0f) - kr * fbv);
                float y1 = fxOtaPole (b, u, g);
                float y2 = fxOtaPole (b + 1, y1, g);
                float y3 = fxOtaPole (b + 2, y2, g);
                float y4 = fxOtaPole (b + 3, y3, g);
                fxF.at (b + 4) = y4;
                fxF.at (b + 5) = y3;

                if (ft == 37) return y4 * (1.0f + 0.5f * kr);
                if (ft == 38) return y4 * (1.0f + 0.15f * kr);
                return y4 * (1.0f + 0.3f * kr);
            }

            if (ft >= 39 && ft <= 42)
            {
                // Oberheim SEM: clean 12 dB multimode, resonance limited below self oscillation, a little saturation; 39 LP, 40 BP, 41 notch, 42 HP
                float ks = 2.0f - 1.8f * res;
                float y  = fxLimSvf (b, x, g, ks, 3.0f, 0.0f, ft == 39 ? 0 : (ft == 40 ? 1 : (ft == 41 ? 3 : 2)));
                return y;
            }

            if (ft == 43)
            {
                // Diode ladder (TB-303 like): four coupled poles, asymmetric input, weak resonance with strong bass loss
                float kr = res * 3.4f;
                float y1p = fxF.at (b + 4);
                float y2p = fxF.at (b + 5);
                float y3p = fxF.at (b + 6);
                float y4p = fxF.at (b + 7);
                float xi  = x * 1.3f - kr * y4p;
                float u   = softClip (xi + 0.12f * xi * xi);
                float y1  = fxOnePole (b,     u  + 0.3f * (y2p - y1p), g);
                float y2  = fxOnePole (b + 1, y1 + 0.3f * (y3p - y2p), g * 0.9f);
                float y3  = fxOnePole (b + 2, y2 + 0.3f * (y4p - y3p), g * 0.8f);
                float y4  = fxOnePole (b + 3, y3, g * 0.7f);
                fxF.at (b + 4) = y1;
                fxF.at (b + 5) = y2;
                fxF.at (b + 6) = y3;
                fxF.at (b + 7) = y4;
                return y4 * (1.0f + 0.35f * kr);
            }

            // 44 / 45 Steiner-Parker: 12 dB with strong, bright resonance; the resonance is fed back before the input stage so that even the high-pass resonates
            float kq = max (0.04f, 2.0f - 1.96f * res);
            return fxLimSvf (b, x * 1.1f, g, kq, 1.4f, 0.0f, ft == 44 ? 0 : 2) * 1.1f;
        }

'''
mk = '        // 23: vowel / formant filter, cutoff sweeps A-E-I-O-U\n'
i = s.index('    float fxFilterX (int s, int ch')
i = s.index(mk, i)
s = s[:i] + body + s[i:]
open(path, 'w').write(s)

# UI side: names, groups, mode ranges
ip = os.path.join(pdir, 'index.js')
j = open(ip).read()
old = 'const FX_FILTER_TYPES = FILTER_TYPES.concat(["Korg35 LP", "Korg35 HP", "Scream"]);'
assert j.count(old) == 1
j = j.replace(old, 'const FX_FILTER_TYPES = FILTER_TYPES.concat(["Korg35 LP", "Korg35 HP", "Scream", "Polivoks LP", "Polivoks BP", "Polivoks HP", "OTA LP24 (Jupiter)", "CEM LP24 (Prophet)", "SSM LP24", "SEM LP", "SEM BP", "SEM Notch", "SEM HP", "Diode LP (303)", "Steiner LP", "Steiner HP"]);   // FX-FILTERS')
old = 'FILTER_GROUPS.concat([[30, "Korg / Scream"]]);'
assert j.count(old) == 1
j = j.replace(old, 'FILTER_GROUPS.concat([[30, "Korg / Scream"], [33, "Polivoks"], [36, "OTA / CEM / SSM"], [39, "Oberheim SEM"], [43, "Diode / Steiner-Parker"]]);')
j, n = re.subn(r'0, 32, 0, "", "sel", FX_FILTER_TYPES', '0, FX_FILTER_TYPES.length - 1, 0, "", "sel", FX_FILTER_TYPES', j); print('rows', n)
open(ip, 'w').write(j)
print('ok')
