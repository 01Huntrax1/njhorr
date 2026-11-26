// Frame tools of the Wavefilter / Wavedistortion table editor (512 points per frame, axis s = -1..1): Chebyshev analysis and edit, symmetry, rectify, quantise and the generators.
// Header only; tested by native_ui/test/tableops_test.cpp.
#pragma once
#include <juce_core/juce_core.h>
#include <algorithm>
#include <cmath>
#include <cstring>
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

    // ---- Razor (wave slicing, as in the wavetable editor): the frame is cut into up to 8 segments, each plays the source (or a basic shape) with its own level, phase, DC and tuning ----
    struct Razor
    {
        int n = 1; float size = 1.0f, duty = 0.5f, mix = 1.0f; bool pol = false;
        float lvl[8], ph[8], dc[8], semi[8]; int shp[8];   // shp: 0 source, 1 sine, 2 saw, 3 square, 4 triangle
        Razor() { reset(); }
        void reset() { n = 1; size = 1.0f; duty = 0.5f; mix = 1.0f; pol = false; for (int k = 0; k < 8; ++k) { lvl[k] = 1.0f; ph[k] = dc[k] = semi[k] = 0.0f; shp[k] = 0; } }
        bool active() const { return n > 1 || size != 1.0f || mix != 1.0f; }
    };
    inline float razorShape (const float* q, int s, float p)
    {
        p -= std::floor (p);
        if (s == 0) { const float x = p * (float) FL; const int i = (int) x; const float f = x - (float) i; return q[i % FL] * (1.0f - f) + q[(i + 1) % FL] * f; }
        if (s == 1) return std::sin (6.2831853f * p);
        if (s == 2) return 2.0f * p - 1.0f;
        if (s == 3) return p < 0.5f ? 1.0f : -1.0f;
        return p < 0.5f ? 4.0f * p - 1.0f : 3.0f - 4.0f * p;
    }
    inline void razorRender (const float* src, const Razor& r, float* out)   // src and out: FL points, may not alias
    {
        const int n = juce::jlimit (1, 8, r.n); float w[8], st[8], sum = 0.0f;
        for (int k = 0; k < n; ++k) { const bool paired = (k | 1) < n; w[k] = n == 1 ? 1.0f : paired ? 2.0f / (float) n * ((k & 1) ? 1.0f - r.duty : r.duty) : 1.0f / (float) n; sum += w[k]; }
        float acc = 0.0f; for (int k = 0; k < n; ++k) { w[k] /= sum; st[k] = acc; acc += w[k]; }
        float peak = 0.0f; int k = 0;
        for (int i = 0; i < FL; ++i)
        {
            const float p = (float) i / (float) FL;
            while (k < n - 1 && p >= st[k + 1]) ++k;
            const float t = (p - st[k]) / std::max (1.0e-6f, w[k]);
            float v = razorShape (src, r.shp[k], r.ph[k] + t * r.size * std::pow (2.0f, r.semi[k] / 12.0f));
            v = r.pol ? std::abs (v) * (r.lvl[k] < 0.0f ? -1.0f : 1.0f) * std::abs (r.lvl[k]) : v * r.lvl[k];
            v += r.dc[k]; v = src[i] * (1.0f - r.mix) + v * r.mix;
            out[i] = v; peak = std::max (peak, std::abs (v));
        }
        if (peak > 1.0f) for (int j = 0; j < FL; ++j) out[j] /= peak;
    }

    // ---- preset manager: factory sets (a morph through generators, one frame per step) and user files <root>/TablePresets/<Filter|Shaper>/<name>.njotbl (header "NJOT", frame count, floats) ----
    struct FactorySet { const char* name; std::vector<const char*> keys; };
    inline const std::vector<FactorySet>& factorySets (bool filter)
    {
        static const std::vector<FactorySet> fl = { { "Sweep: Low > Band > High", { "LOW PASS", "BAND PASS", "HIGH PASS" } }, { "Formant Vowels", { "VOWEL", "FORMANT", "DUAL PEAK" } },
            { "Comb Sweep", { "COMB", "SAW COMB", "NOTCH" } }, { "Reso Rise", { "LOW PASS", "RESO LP", "BAND PASS" } }, { "Shelves", { "LOW SHELF", "LOW PASS", "HIGH SHELF" } }, { "Notch to Peak", { "NOTCH", "LOW PASS", "DUAL PEAK" } } };
        static const std::vector<FactorySet> sh = { { "Soft to Hard", { "LINEAR", "SOFT", "HARD" } }, { "Fold Rise", { "LINEAR", "SOFT", "FOLD" } }, { "Chebyshev Climb", { "LINEAR", "CHEBY 2", "CHEBY 3", "CHEBY 5" } },
            { "Analog Warmth", { "LINEAR", "TUBE", "DIODE", "ASYM" } }, { "Digital Crunch", { "LINEAR", "STAIRS", "CRUSH" } }, { "Asym Fold", { "ASYM", "FOLD", "CHEBY 3" } } };
        return filter ? fl : sh;
    }
    inline std::vector<float> buildFactory (bool filter, const FactorySet& fs, int frames = 16)
    {
        std::vector<float> out ((size_t) frames * FL), a (FL), b (FL); const int n = (int) fs.keys.size();
        for (int f = 0; f < frames; ++f)
        {
            const float pos = n == 1 ? 0.0f : (float) f / (float) (frames - 1) * (float) (n - 1); const int k = std::min (n - 2 < 0 ? 0 : n - 2, (int) pos); const float t = n == 1 ? 0.0f : pos - (float) k;
            generate (filter, fs.keys[(size_t) k], a.data()); generate (filter, fs.keys[(size_t) std::min (n - 1, k + 1)], b.data());
            for (int i = 0; i < FL; ++i) out[(size_t) f * FL + i] = a[(size_t) i] + (b[(size_t) i] - a[(size_t) i]) * t;
        }
        return out;
    }
    inline juce::File presetDir (const juce::File& root, bool filter) { return root.getChildFile ("TablePresets").getChildFile (filter ? "Filter" : "Shaper"); }
    inline juce::StringArray userNames (const juce::File& root, bool filter)
    {
        juce::StringArray r; for (auto& f : presetDir (root, filter).findChildFiles (juce::File::findFiles, false, "*.njotbl")) r.add (f.getFileNameWithoutExtension());
        r.sort (true); return r;
    }
    inline bool saveUser (const juce::File& root, bool filter, const juce::String& name, const std::vector<float>& d)
    {
        auto n = juce::File::createLegalFileName (name.trim()); if (n.isEmpty() || d.size() < (size_t) FL) return false;
        auto dir = presetDir (root, filter); dir.createDirectory(); juce::MemoryBlock mb; const int fr = (int) (d.size() / FL);
        mb.append ("NJOT", 4); mb.append (&fr, 4); mb.append (d.data(), (size_t) fr * FL * sizeof (float));
        return dir.getChildFile (n + ".njotbl").replaceWithData (mb.getData(), mb.getSize());
    }
    inline bool loadUser (const juce::File& root, bool filter, const juce::String& name, std::vector<float>& d)
    {
        juce::MemoryBlock mb; if (! presetDir (root, filter).getChildFile (name + ".njotbl").loadFileAsData (mb) || mb.getSize() < 8 || std::memcmp (mb.getData(), "NJOT", 4) != 0) return false;
        int fr = 0; std::memcpy (&fr, (const char*) mb.getData() + 4, 4); if (fr < 1 || fr > 256 || mb.getSize() < 8 + (size_t) fr * FL * sizeof (float)) return false;
        d.resize ((size_t) fr * FL); std::memcpy (d.data(), (const char*) mb.getData() + 8, d.size() * sizeof (float));
        for (auto& v : d) v = juce::jlimit (-1.0f, 1.0f, v);
        return true;
    }
    inline void removeUser (const juce::File& root, bool filter, const juce::String& name) { presetDir (root, filter).getChildFile (name + ".njotbl").deleteFile(); }
}
