// One radix-2 FFT for the whole UI side (wavetable editor tools, factory wavetables, Filter Table spectrum). Header only, no JUCE.
#pragma once
#include <vector>
#include <complex>
#include <cmath>
#include <functional>
#include <utility>

namespace njo::dsp
{
    using cd = std::complex<double>;

    // in-place, size must be a power of two; sign -1 forward / +1 inverse (not normalised)
    inline void fft (std::vector<cd>& a, int sign)
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
            const double ang = sign * 6.283185307179586 / (double) len;
            const cd wl (std::cos (ang), std::sin (ang));
            for (size_t i = 0; i < n; i += len)
            {
                cd w (1.0, 0.0);
                for (size_t k = 0; k < len / 2; ++k, w *= wl)
                {
                    const cd u = a[i + k], v = a[i + k + len / 2] * w;
                    a[i + k] = u + v; a[i + k + len / 2] = u - v;
                }
            }
        }
    }

    // spectral edit of one cycle (power of two length): edit (harmonic k = 1 .. n/2 - 1, its complex coefficient) may change it; DC is removed
    template <class Real>
    inline void editHarmonics (std::vector<Real>& x, const std::function<void (int, cd&)>& edit)
    {
        const size_t n = x.size(); std::vector<cd> c (n);
        for (size_t i = 0; i < n; ++i) c[i] = cd ((double) x[i], 0.0);
        fft (c, -1);
        c[0] = 0; c[n / 2] = 0;
        for (size_t k = 1; k < n / 2; ++k) { edit ((int) k, c[k]); c[n - k] = std::conj (c[k]); }
        fft (c, +1);
        for (size_t i = 0; i < n; ++i) x[i] = (Real) (c[i].real() / (double) n);
    }

    // amplitude of the harmonics 1 .. count of one cycle (sine of amplitude 1 -> 1), any length (resampled to a power of two)
    inline std::vector<float> harmonicMagnitudes (const std::vector<float>& x, int count)
    {
        size_t n = 1; while (n < x.size()) n <<= 1;
        std::vector<cd> c (n);
        for (size_t i = 0; i < n; ++i) { const double p = (double) i * x.size() / n; const size_t i0 = (size_t) p, i1 = std::min (i0 + 1, x.size() - 1); c[i] = (double) x[i0] + ((double) x[i1] - x[i0]) * (p - (double) i0); }
        fft (c, -1);
        std::vector<float> m ((size_t) count, 0.0f);
        for (int k = 1; k <= count && (size_t) k < n / 2; ++k) m[(size_t) k - 1] = (float) (std::abs (c[(size_t) k]) * 2.0 / (double) n);
        return m;
    }
}
