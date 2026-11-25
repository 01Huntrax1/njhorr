// Frame tools of the Wavefilter / Wavedistortion table editor (512 points per frame, axis s = -1..1): Chebyshev analysis and edit, symmetry, rectify, quantise and the generators.
// Header only; tested by native_ui/test/tableops_test.cpp.
#pragma once
#include <juce_core/juce_core.h>
#include <algorithm>
#include <cmath>
#include <vector>

namespace njo::tblops
{
    constexpr int FL = 512, NH = 16;
    inline float sOf (int i) { return (float) i / (float) (FL - 1) * 2.0f - 1.0f; }
    inline float cheb (int n, float s) { return std::cos ((float) n * std::acos (juce::jlimit (-1.0f, 1.0f, s))); }   // T_n(s)

    // coefficients c_n of f(s) = sum c_n T_n(s): c_n = 2/pi * integral f(cos t) cos(n t) dt (n >= 1)
    inline void chebAnalyse (const float* f, float* c, int nh = NH)
    {
        const int M = 512;
        for (int n = 1; n <= nh; ++n)
        {
            double acc = 0;
            for (int j = 0; j < M; ++j)
            {
                const double t = juce::MathConstants<double>::pi * (j + 0.5) / M, s = std::cos (t);
                const double x = (s + 1.0) * 0.5 * (FL - 1); const int a = juce::jlimit (0, FL - 2, (int) x); const double fr = x - a;
                acc += (f[a] + (f[a + 1] - f[a]) * fr) * std::cos (n * t);
            }
            c[n - 1] = (float) (2.0 * acc / M);
        }
    }
    // moves the n-th Chebyshev term of the frame to the value v, everything else stays
    inline void chebSet (float* f, int n, float v)
    {
        float c[NH]; chebAnalyse (f, c, juce::jmin (NH, n));
        const float d = v - c[n - 1];
        for (int i = 0; i < FL; ++i) f[i] = juce::jlimit (-1.0f, 1.0f, f[i] + d * cheb (n, sOf (i)));
    }

    inline void oddSymmetry (float* f)  { for (int i = 0; i < FL / 2; ++i) { const float a = 0.5f * (f[i] - f[FL - 1 - i]); f[i] = a; f[FL - 1 - i] = -a; } }
    inline void evenSymmetry (float* f) { for (int i = 0; i < FL / 2; ++i) { const float a = 0.5f * (f[i] + f[FL - 1 - i]); f[i] = a; f[FL - 1 - i] = a; } }
    inline void rectify (float* f)      { for (int i = 0; i < FL; ++i) f[i] = std::abs (f[i]); }
    inline void quantise (float* f, int levels = 8) { for (int i = 0; i < FL; ++i) f[i] = std::round (f[i] * (float) levels) / (float) levels; }

    inline const std::vector<const char*>& names (bool filter)
    {
        static const std::vector<const char*> fl = { "LOW PASS", "HIGH PASS", "BAND PASS", "NOTCH", "COMB", "FORMANT", "RESO LP", "LOW SHELF", "HIGH SHELF", "DUAL PEAK", "SAW COMB", "VOWEL" };
        static const std::vector<const char*> sh = { "LINEAR", "SOFT", "HARD", "FOLD", "ASYM", "STAIRS", "CHEBY 2", "CHEBY 3", "CHEBY 5", "DIODE", "TUBE", "CRUSH" };
        return filter ? fl : sh;
    }
    // the generated frame (a name from names())
    inline void generate (bool filter, const juce::String& n, float* v)
    {
        const float pi = juce::MathConstants<float>::pi;
        for (int i = 0; i < FL; ++i)
        {
            const float x = (float) i / (float) (FL - 1), s = x * 2.0f - 1.0f; float y = 0.0f;
            if (filter)
            {
                auto bump = [&] (float c, float w) { return std::exp (-(x - c) * (x - c) / (2.0f * w * w)); };
                auto step = [&] (float c, float w) { return 1.0f / (1.0f + std::exp (-(x - c) / w)); };
                if (n == "LOW PASS")        y = 1.0f / (1.0f + std::exp ((x - 0.5f) * 24.0f)) * 2.0f - 1.0f;
                else if (n == "HIGH PASS")  y = 2.0f / (1.0f + std::exp (-(x - 0.5f) * 24.0f)) - 1.0f;
                else if (n == "BAND PASS")  y = bump (0.5f, 0.06f) * 2.0f - 1.0f;
                else if (n == "NOTCH")      y = 1.0f - bump (0.5f, 0.05f) * 2.0f;
                else if (n == "COMB")       y = std::cos (2.0f * pi * 8.0f * x);
                else if (n == "FORMANT")    y = juce::jmax (bump (0.30f, 0.025f), juce::jmax (bump (0.52f, 0.03f), bump (0.72f, 0.025f))) * 2.0f - 1.0f;
                else if (n == "RESO LP")    y = juce::jlimit (-1.0f, 1.0f, (1.0f / (1.0f + std::exp ((x - 0.5f) * 24.0f))) * 1.6f - 0.8f + bump (0.46f, 0.035f) * 0.9f);
                else if (n == "LOW SHELF")  y = 0.6f - 0.9f * step (0.5f, 0.05f);
                else if (n == "HIGH SHELF") y = -0.6f + 0.9f * step (0.5f, 0.05f);
                else if (n == "DUAL PEAK")  y = juce::jmax (bump (0.3f, 0.03f), bump (0.7f, 0.03f)) * 2.0f - 1.0f;
                else if (n == "SAW COMB")   y = (x * 8.0f - std::floor (x * 8.0f)) * 2.0f - 1.0f;
                else                        y = juce::jmax (bump (0.18f, 0.02f), juce::jmax (bump (0.42f, 0.02f), bump (0.82f, 0.02f))) * 2.0f - 1.0f;   // VOWEL
            }
            else
            {
                if (n == "LINEAR")       y = s;
                else if (n == "SOFT")    y = std::tanh (3.0f * s) / std::tanh (3.0f);
                else if (n == "HARD")    y = juce::jlimit (-1.0f, 1.0f, 2.5f * s);
                else if (n == "FOLD")    y = std::sin (2.5f * pi * s);
                else if (n == "ASYM")    y = s > 0 ? std::tanh (4.0f * s) : 0.55f * s;
                else if (n == "STAIRS")  y = std::round (s * 6.0f) / 6.0f;
                else if (n == "CHEBY 2") y = cheb (2, s);
                else if (n == "CHEBY 3") y = cheb (3, s);
                else if (n == "CHEBY 5") y = cheb (5, s);
                else if (n == "DIODE")   y = s >= 0 ? (1.0f - std::exp (-4.0f * s)) / (1.0f - std::exp (-4.0f)) : 0.25f * (std::exp (4.0f * s) - 1.0f) / (1.0f - std::exp (-4.0f));
                else if (n == "TUBE")    y = (std::tanh (2.5f * s + 0.4f) - std::tanh (0.4f)) / (std::tanh (2.9f) - std::tanh (0.4f));
                else                     y = std::round (s * 4.0f) / 4.0f;   // CRUSH
            }
            v[i] = juce::jlimit (-1.0f, 1.0f, y);
        }
    }
}
