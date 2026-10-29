// Parametric EQ (FX type 13): the band model shared by the editor and its display. The DSP (tools/fx/build_eq.py) builds the same sections from the same 10 values per band.
#pragma once
#include <juce_core/juce_core.h>
#include <array>
#include <cmath>
#include <vector>

namespace njo::eq
{
    constexpr int MAXB = 24, FIELDS = 10, NTYPES = 15;
    inline const char* typeName (int t)
    {
        static const char* const n[NTYPES] = { "Bell", "Low Shelf", "High Shelf", "Low Cut 12", "Low Cut 24", "High Cut 12", "High Cut 24", "Band Pass", "Notch", "Tilt", "All-Pass", "Comb (feed-forward)", "Comb (feedback)", "Low Cut 48", "High Cut 48" };
        return n[t < 0 ? 0 : (t >= NTYPES ? NTYPES - 1 : t)];
    }
    inline bool hasGain (int t) { return t == 0 || t == 1 || t == 2 || t == 7 || t == 9 || t == 11 || t == 12; }      // types whose gain is meaningful
    inline bool hasHarmonics (int t) { return t == 0 || t == 7 || t == 8; }
    inline bool isComb (int t) { return t == 11 || t == 12; }

    struct Band
    {
        bool used = false, on = false; int type = 0; float hz = 1000.0f, db = 0.0f, q = 1.0f; int harm = 0; float fall = 0.5f; int hset = 0, ch = 0;   // hset: 0 all, 1 odd, 2 even; ch: 0 stereo, 1 L, 2 R, 3 mid, 4 side
    };
    using Bands = std::array<Band, MAXB>;

    inline std::vector<float> encode (const Bands& b)
    {
        std::vector<float> v ((size_t) MAXB * FIELDS, 0.0f);
        for (int i = 0; i < MAXB; ++i)
        {
            auto& x = b[(size_t) i]; float* o = &v[(size_t) i * FIELDS];
            o[0] = x.on ? 1.0f : 0.0f; o[1] = (float) x.type / 16.0f;
            o[2] = (float) (std::log2 (juce::jlimit (20.0f, 20000.0f, x.hz) / 20.0f) / std::log2 (1000.0));
            o[3] = juce::jlimit (-1.0f, 1.0f, x.db / 24.0f);
            o[4] = (float) (std::log2 (juce::jlimit (0.1f, 30.0f, x.q) / 0.1f) / std::log2 (300.0));
            o[5] = (float) x.harm / 16.0f; o[6] = x.fall; o[7] = (float) x.hset / 4.0f; o[8] = (float) x.ch / 4.0f; o[9] = x.used ? 1.0f : 0.0f;
        }
        return v;
    }
    inline Bands decode (const std::vector<float>& v)
    {
        Bands b {};
        for (int i = 0; i < MAXB && (size_t) (i + 1) * FIELDS <= v.size(); ++i)
        {
            const float* o = &v[(size_t) i * FIELDS]; auto& x = b[(size_t) i];
            x.used = o[9] > 0.5f; x.on = o[0] > 0.5f; x.type = juce::jlimit (0, NTYPES - 1, juce::roundToInt (o[1] * 16.0f));
            x.hz = 20.0f * (float) std::pow (1000.0, juce::jlimit (0.0f, 1.0f, o[2]));
            x.db = juce::jlimit (-24.0f, 24.0f, o[3] * 24.0f);
            x.q = 0.1f * (float) std::pow (300.0, juce::jlimit (0.0f, 1.0f, o[4]));
            x.harm = juce::jlimit (0, 16, juce::roundToInt (o[5] * 16.0f)); x.fall = juce::jlimit (0.0f, 1.0f, o[6]);
            x.hset = juce::jlimit (0, 2, juce::roundToInt (o[7] * 4.0f)); x.ch = juce::jlimit (0, 4, juce::roundToInt (o[8] * 4.0f));
        }
        return b;
    }

    struct Sec { int kind; double f, g, q; };   // kind: 0 peak, 1 low shelf, 2 high shelf, 3 high pass, 4 low pass, 5 band pass, 6 notch, 7 all-pass
    struct Scale { double gain = 1.0, shift = 1.0, q = 1.0; };   // slot parameters P2 / P3 / P4 as factors

    // the biquad sections of a band, exactly as the DSP builds them (combs give no sections)
    inline std::vector<Sec> sections (const Band& b, const Scale& sc, double sr)
    {
        std::vector<Sec> s;
        const double f = juce::jlimit (10.0, sr * 0.45, (double) b.hz * sc.shift), g = juce::jlimit (-36.0, 36.0, (double) b.db * sc.gain), q = juce::jlimit (0.05, 40.0, (double) b.q * sc.q);
        const double qq = q * 1.4142;
        switch (b.type)
        {
            case 0: s.push_back ({ 0, f, g, q }); break;
            case 1: s.push_back ({ 1, f, g, q }); break;
            case 2: s.push_back ({ 2, f, g, q }); break;
            case 3: s.push_back ({ 3, f, 0, q }); break;
            case 4: s.push_back ({ 3, f, 0, qq * 0.5412 }); s.push_back ({ 3, f, 0, qq * 1.3066 }); break;
            case 5: s.push_back ({ 4, f, 0, q }); break;
            case 6: s.push_back ({ 4, f, 0, qq * 0.5412 }); s.push_back ({ 4, f, 0, qq * 1.3066 }); break;
            case 7: s.push_back ({ 5, f, g, q }); break;
            case 8: s.push_back ({ 6, f, 0, q }); break;
            case 9: s.push_back ({ 1, f, -g * 0.5, 0.5 }); s.push_back ({ 2, f, g * 0.5, 0.5 }); break;
            case 10: s.push_back ({ 7, f, 0, q }); break;
            case 13: for (double k : { 0.5098, 0.6013, 0.9, 2.5629 }) s.push_back ({ 3, f, 0, qq * k }); break;
            case 14: for (double k : { 0.5098, 0.6013, 0.9, 2.5629 }) s.push_back ({ 4, f, 0, qq * k }); break;
            default: break;
        }
        if (hasHarmonics (b.type) && b.harm > 0)
        {
            const double fall = 0.4 + 0.6 * b.fall; double hg = g;
            for (int h = 1; h <= b.harm; ++h)
            {
                int k = h + 1; if (b.hset == 1) k = 2 * h + 1; if (b.hset == 2) k = 2 * h;
                hg *= fall; const double hf = f * k; if (hf > sr * 0.45) break;
                s.push_back (b.type == 8 ? Sec { 6, hf, 0, q } : Sec { b.type == 7 ? 5 : 0, hf, hg, q });
            }
        }
        return s;
    }

    // magnitude (linear) of one RBJ section at frequency fr
    inline double secMag (const Sec& s, double fr, double sr)
    {
        const double pi = juce::MathConstants<double>::pi, w0 = 2 * pi * s.f / sr, cw = std::cos (w0), sw = std::sin (w0), al = sw / (2 * s.q), A = std::pow (10.0, s.g / 40.0);
        double b0 = 1, b1 = 0, b2 = 0, a0 = 1, a1 = 0, a2 = 0;
        switch (s.kind)
        {
            case 0: b0 = 1 + al * A; b1 = -2 * cw; b2 = 1 - al * A; a0 = 1 + al / A; a1 = -2 * cw; a2 = 1 - al / A; break;
            case 1: { const double t = 2 * std::sqrt (A) * al; b0 = A * ((A + 1) - (A - 1) * cw + t); b1 = 2 * A * ((A - 1) - (A + 1) * cw); b2 = A * ((A + 1) - (A - 1) * cw - t);
                      a0 = (A + 1) + (A - 1) * cw + t; a1 = -2 * ((A - 1) + (A + 1) * cw); a2 = (A + 1) + (A - 1) * cw - t; break; }
            case 2: { const double t = 2 * std::sqrt (A) * al; b0 = A * ((A + 1) + (A - 1) * cw + t); b1 = -2 * A * ((A - 1) + (A + 1) * cw); b2 = A * ((A + 1) + (A - 1) * cw - t);
                      a0 = (A + 1) - (A - 1) * cw + t; a1 = 2 * ((A - 1) - (A + 1) * cw); a2 = (A + 1) - (A - 1) * cw - t; break; }
            case 3: b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = b0; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break;
            case 4: b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = b0; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break;
            case 5: { const double gl = std::pow (10.0, s.g / 20.0); b0 = al * gl; b2 = -al * gl; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break; }
            case 6: b0 = 1; b1 = -2 * cw; b2 = 1; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break;
            default: b0 = 1 - al; b1 = -2 * cw; b2 = 1 + al; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break;
        }
        const double w = 2 * pi * fr / sr, c1 = std::cos (w), s1 = std::sin (w), c2 = std::cos (2 * w), s2 = std::sin (2 * w);
        const double nr = b0 + b1 * c1 + b2 * c2, ni = -(b1 * s1 + b2 * s2), dr = a0 + a1 * c1 + a2 * c2, di = -(a1 * s1 + a2 * s2);
        return std::sqrt ((nr * nr + ni * ni) / juce::jmax (1.0e-18, dr * dr + di * di));
    }

    // response of one band in dB (sections and comb)
    inline double bandDb (const Band& b, double fr, const Scale& sc, double sr = 48000.0)
    {
        double db = 0.0;
        for (auto& s : sections (b, sc, sr)) db += 20.0 * std::log10 (juce::jmax (1.0e-9, secMag (s, fr, sr)));
        if (isComb (b.type))
        {
            const double g = juce::jlimit (-36.0, 36.0, (double) b.db * sc.gain), amt = (1.0 - std::pow (10.0, -std::abs (g) / 20.0)) * (b.type == 12 ? 0.97 : 1.0) * (g < 0 ? -1.0 : 1.0);
            const double d = juce::jlimit (2.0, 4000.0, sr / juce::jlimit (10.0, sr * 0.45, (double) b.hz * sc.shift)), w = 2 * juce::MathConstants<double>::pi * fr / sr * d;
            const double re = b.type == 12 ? 1.0 - amt * std::cos (w) : 1.0 + amt * std::cos (w), im = b.type == 12 ? amt * std::sin (w) : -amt * std::sin (w);
            db += 20.0 * std::log10 (juce::jmax (1.0e-9, b.type == 12 ? 1.0 / std::sqrt (juce::jmax (1.0e-9, re * re + im * im)) : std::sqrt (re * re + im * im)));
        }
        return db;
    }
}
