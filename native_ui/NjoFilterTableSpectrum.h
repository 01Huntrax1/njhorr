// "Filter Table" compatibility of the Wavefilter (Kilohearts style): an ordinary wavetable frame is read as a SPECTRUM, the
// magnitudes of its harmonics become the gain curve of the filter. Cutoff = harmonic 24 of the frame (as in Filter Table),
// the curve runs kRange octaves over the Wavefilter axis (harmonic 1 ... about 540). Header only, no JUCE.
#pragma once
#include <vector>
#include <cmath>
#include <algorithm>
#include <complex>

namespace njo::fts
{
    constexpr int   kPoints = 512;        // points of one table frame
    constexpr float kRange  = 9.0f;       // Range (octaves) the curve is made for; the loader sets the Range parameter to it
    constexpr float kCenter = 24.0f;      // harmonic that sits at the cutoff

    inline void fft (std::vector<std::complex<double>>& a)       // size: power of two
    {
        const size_t n = a.size();
        for (size_t i = 1, j = 0; i < n; ++i)
        {
            size_t bit = n >> 1;
            for (; j & bit; bit >>= 1) j ^= bit;
            j ^= bit; if (i < j) std::swap (a[i], a[j]);
        }
        for (size_t len = 2; len <= n; len <<= 1)
        {
            const double ang = -6.283185307179586 / (double) len;
            const std::complex<double> wl (std::cos (ang), std::sin (ang));
            for (size_t i = 0; i < n; i += len)
            {
                std::complex<double> w (1.0, 0.0);
                for (size_t k = 0; k < len / 2; ++k, w *= wl)
                {
                    auto u = a[i + k], v = a[i + k + len / 2] * w;
                    a[i + k] = u + v; a[i + k + len / 2] = u - v;
                }
            }
        }
    }

    // one frame (any length >= 16, a cycle) -> 512 values v = 2g - 1, g = 0..1 the normalised magnitude along the log axis
    inline std::vector<float> frameToCurve (const float* x, int len)
    {
        int n = 2048; while (n < len && n < 8192) n <<= 1;       // FFT size: at least the frame length (resampled when not a power of two)
        std::vector<std::complex<double>> a ((size_t) n);
        for (int i = 0; i < n; ++i)
        {
            const double p = (double) i * len / n; const int i0 = (int) p, i1 = std::min (i0 + 1, len - 1);
            a[(size_t) i] = (double) x[i0] + ((double) x[i1] - (double) x[i0]) * (p - i0);
        }
        fft (a);
        const int nh = n / 2;
        std::vector<double> mag ((size_t) nh + 1, 0.0);          // magnitude of harmonic k (k cycles per frame)
        for (int k = 1; k <= nh; ++k) mag[(size_t) k] = std::abs (a[(size_t) k]) * 2.0 / n;

        std::vector<double> g (kPoints, 0.0);
        const double halfBand = 0.2;                              // octaves: strongest harmonic within +- 0.2 oct
        double peak = 0.0;
        for (int i = 0; i < kPoints; ++i)
        {
            const double o = ((double) i / (kPoints - 1) - 0.5) * kRange;
            const double lo = kCenter * std::pow (2.0, o - halfBand), hi = kCenter * std::pow (2.0, o + halfBand);
            const int k0 = std::max (1, (int) std::ceil (lo)), k1 = std::min (nh, (int) std::floor (hi));
            double s = 0.0; const double c0 = kCenter * std::pow (2.0, o);
            if (k1 >= k0) { for (int k = k0; k <= k1; ++k) s = std::max (s, mag[(size_t) k] * (1.0 - 0.7 * std::fabs (std::log2 (k / c0) - 0.0) / halfBand)); }   // the strongest harmonic in the band, weighted by its distance to the centre
            else        // between two harmonics: interpolate
            {
                const double c = kCenter * std::pow (2.0, o); const int k = std::clamp ((int) c, 1, nh - 1); const double f = std::clamp (c - k, 0.0, 1.0);
                s = mag[(size_t) k] + (mag[(size_t) k + 1] - mag[(size_t) k]) * f;
            }
            g[(size_t) i] = s; peak = std::max (peak, s);
        }
        std::vector<float> out (kPoints);
        for (int i = 0; i < kPoints; ++i) out[(size_t) i] = peak > 1.0e-9 ? (float) (2.0 * g[(size_t) i] / peak - 1.0) : -1.0f;
        return out;
    }

    // a whole wavetable (mono, frames of frameLen samples) -> frames * 512 values; at most maxFrames frames, picked evenly
    inline std::vector<float> tableToCurves (const std::vector<float>& mono, int frameLen, int maxFrames)
    {
        const int n = (int) mono.size();
        const int fl = std::max (16, std::min (frameLen, n));
        const int nF = std::max (1, n / fl), take = std::min (nF, maxFrames);
        std::vector<float> out;
        for (int t = 0; t < take; ++t)
        {
            const int f = take == 1 ? 0 : (int) std::lround ((double) t * (nF - 1) / (take - 1));
            auto c = frameToCurve (mono.data() + (size_t) f * fl, std::min (fl, n - f * fl));
            out.insert (out.end(), c.begin(), c.end());
        }
        return out;
    }
}
