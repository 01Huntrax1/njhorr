#include "NjoFactory.h"
#include <cmath>
#include <complex>

namespace njo
{
    namespace
    {
        using cd = std::complex<double>;
        constexpr int N = 2048, H = N / 2;       // harmonics 1 .. H-1 are used
        constexpr double PEAK = 0.97, PI = 3.14159265358979323846;
        using Vec = std::vector<double>;

        // in-place radix-2 FFT, sign -1 forward / +1 inverse (not normalized)
        void fft (std::vector<cd>& a, int sign)
        {
            const size_t n = a.size();
            for (size_t i = 1, j = 0; i < n; ++i)
            {
                size_t bit = n >> 1;
                for (; j & bit; bit >>= 1) j ^= bit;
                j ^= bit;
                if (i < j) std::swap (a[i], a[j]);
            }
            for (size_t len = 2; len <= n; len <<= 1)
            {
                const double ang = sign * 2.0 * PI / (double) len;
                const cd wl (std::cos (ang), std::sin (ang));
                for (size_t i = 0; i < n; i += len)
                {
                    cd w (1.0, 0.0);
                    for (size_t k = 0; k < len / 2; ++k, w *= wl)
                    {
                        cd u = a[i + k], v = a[i + k + len / 2] * w;
                        a[i + k] = u + v; a[i + k + len / 2] = u - v;
                    }
                }
            }
        }

        Vec normalized (Vec x)
        {
            double m = 0; for (double v : x) m = std::max (m, std::abs (v));
            if (m > 1e-9) for (double& v : x) v = v / m * PEAK;
            return x;
        }

        // one cycle = sum over h of amp[h] * sin (2 pi h n / N + ph[h]); band-limited, normalized
        Vec frame (const Vec& amp, const Vec* ph = nullptr)
        {
            std::vector<cd> c ((size_t) N, cd (0, 0));
            for (int k = 1; k < H; ++k) c[(size_t) k] = std::polar (amp[(size_t) k], ph ? (*ph)[(size_t) k] : 0.0);
            fft (c, +1);
            Vec x ((size_t) N);
            for (int n = 0; n < N; ++n) x[(size_t) n] = c[(size_t) n].imag();
            return normalized (x);
        }

        // spectrum (amplitude / phase) of a one-cycle waveform of any length that is a power of two
        void analyse (const Vec& w, Vec& a, Vec& p)
        {
            std::vector<cd> c (w.size());
            for (size_t i = 0; i < w.size(); ++i) c[i] = cd (w[i], 0.0);
            fft (c, -1);
            a.assign ((size_t) H + 1, 0.0); p.assign ((size_t) H + 1, 0.0);
            for (int k = 1; k < H; ++k)
            {
                a[(size_t) k] = std::abs (c[(size_t) k]) / ((double) w.size() / 2.0);
                p[(size_t) k] = std::arg (c[(size_t) k]) + PI / 2;
            }
        }

        Vec fromWave (const Vec& w) { Vec a, p; analyse (w, a, p); return frame (a, &p); }


        // amplitude recipes (index = harmonic number)
        Vec ampSaw()  { Vec a ((size_t) H + 1, 0.0); for (int k = 1; k < H; ++k) a[(size_t) k] = 1.0 / k; return a; }
        Vec ampSq()   { Vec a ((size_t) H + 1, 0.0); for (int k = 1; k < H; k += 2) a[(size_t) k] = 1.0 / k; return a; }
        Vec ampTri()  { Vec a ((size_t) H + 1, 0.0); for (int k = 1; k < H; k += 2) a[(size_t) k] = 1.0 / ((double) k * k); return a; }
        Vec phTri()   { Vec p ((size_t) H + 1, 0.0); for (int k = 1; k <= H; ++k) p[(size_t) k] = ((k - 1) / 2) % 2 == 0 ? 0.0 : PI; return p; }
        Vec ampSine() { Vec a ((size_t) H + 1, 0.0); a[1] = 1.0; return a; }

        Vec pulse (double w)
        {
            Vec a ((size_t) H + 1, 0.0), p ((size_t) H + 1, 0.0);
            for (int k = 1; k < H; ++k) { a[(size_t) k] = std::sin (PI * k * w) / k; p[(size_t) k] = PI / 2 - PI * k * w; }
            return frame (a, &p);
        }

        std::vector<Vec> morph (const Vec& f0, const Vec& f1, int n)
        {
            std::vector<Vec> out;
            for (int i = 0; i < n; ++i)
            {
                const double t = (double) i / (n - 1);
                Vec x (f0.size());
                for (size_t j = 0; j < x.size(); ++j) x[j] = (1 - t) * f0[j] + t * f1[j];
                out.push_back (normalized (x));
            }
            return out;
        }

        // frames with 1, 2, ... 64 harmonics (the fractional top harmonic fades in)
        std::vector<Vec> grow (const Vec& amp, int n)
        {
            std::vector<Vec> out;
            for (int i = 0; i < n; ++i)
            {
                const double t = (double) i / (n - 1), nh = 1 + t * 63;
                Vec a (amp);
                for (int k = 0; k <= H; ++k) a[(size_t) k] *= std::min (1.0, std::max (0.0, nh - (k - 1)));
                out.push_back (frame (a));
            }
            return out;
        }

        Vec cyc (double (*fn) (double)) { Vec x ((size_t) N); for (int n = 0; n < N; ++n) x[(size_t) n] = fn (2 * PI * n / N); return x; }

        Vec syncFrame (double r)
        {
            const int M = N * 16;
            Vec x ((size_t) M);
            for (int n = 0; n < M; ++n) { double ph = std::fmod ((double) n / M * r, 1.0); x[(size_t) n] = 2 * ph - 1; }
            return fromWave (x);
        }

        Vec fmFrame (double idx)
        {
            Vec x ((size_t) N);
            for (int n = 0; n < N; ++n) { double t = 2 * PI * n / N; x[(size_t) n] = std::sin (t + idx * std::sin (t)); }
            return fromWave (x);
        }

        Vec resoFrame (double pos)
        {
            const double c = 1 + pos * 40, q = 6.0;
            Vec a = ampSaw();
            for (int k = 0; k <= H; ++k)
            {
                double res = 1 + q * std::exp (-0.5 * std::pow ((k - c) / 1.2, 2.0));
                double env = k < c * 3 + 8 ? 1.0 : std::exp (-(k - c * 3 - 8) / 6.0);
                a[(size_t) k] *= res * env;
            }
            return frame (a);
        }

        Vec vowelAmp (int v)
        {
            static const double F[5][3] = { { 800, 1150, 2900 }, { 400, 1600, 2700 }, { 350, 1700, 2700 }, { 450, 800, 2830 }, { 325, 700, 2530 } };   // A E I O U
            static const double BW[3] = { 80, 90, 120 }, G[3] = { 1.0, 0.6, 0.35 };
            Vec a = ampSaw();
            for (int k = 0; k <= H; ++k)
            {
                double f = k * 130.0, e = 0;
                for (int j = 0; j < 3; ++j) e += G[j] * std::exp (-0.5 * std::pow ((f - F[v][j]) / BW[j], 2.0));
                a[(size_t) k] *= e + 0.02;
            }
            return a;
        }

        void add (std::vector<FactoryTable>& out, const char* name, const std::vector<Vec>& frames)
        {
            FactoryTable t; t.name = name;
            for (auto& f : frames) for (double v : f) t.samples.push_back ((float) v);
            out.push_back (std::move (t));
        }

        bool writeWav (const juce::File& f, const std::vector<float>& s)
        {
            juce::MemoryOutputStream o;
            const int bytes = (int) s.size() * 2;
            auto u32 = [&] (int v) { o.writeInt (v); };
            o.write ("RIFF", 4); u32 (36 + bytes); o.write ("WAVE", 4); o.write ("fmt ", 4); u32 (16);
            o.writeShort (1); o.writeShort (1); u32 (44100); u32 (44100 * 2); o.writeShort (2); o.writeShort (16);
            o.write ("data", 4); u32 (bytes);
            for (float v : s) o.writeShort ((short) juce::jlimit (-32768, 32767, (int) std::lround (v * 32767.0f)));
            return f.replaceWithData (o.getData(), o.getDataSize());
        }
    }

    std::vector<FactoryTable> makeFactoryWavetables()
    {
        std::vector<FactoryTable> out;
        const Vec sine = frame (ampSine()), triP = phTri(), tri = frame (ampTri(), &triP), saw = frame (ampSaw()), sq = frame (ampSq());

        add (out, "Basic Shapes", { sine, tri, saw, sq, pulse (0.25), pulse (0.125),
            fromWave (cyc ([] (double t) { return std::max (std::sin (t), 0.0); })),
            fromWave (cyc ([] (double t) { return std::abs (std::sin (t)); })) });
        add (out, "Sine to Saw",      grow (ampSaw(), 64));
        add (out, "Sine to Square",   grow (ampSq(), 64));
        add (out, "Triangle to Saw",  morph (tri, saw, 64));
        add (out, "Saw to Square",    morph (saw, sq, 64));
        add (out, "Sine to Triangle", morph (sine, tri, 32));

        { std::vector<Vec> f; for (int i = 0; i < 64; ++i) f.push_back (pulse (0.5 - 0.47 * i / 63)); add (out, "PWM", f); }
        { std::vector<Vec> f; for (int i = 0; i < 64; ++i) f.push_back (syncFrame (1 + 7.0 * i / 63)); add (out, "Hard Sync", f); }
        { std::vector<Vec> f; for (int k = 1; k <= 32; ++k) { Vec a ((size_t) H + 1, 0.0); a[(size_t) k] = 1.0; f.push_back (frame (a)); } add (out, "Harmonics", f); }
        {
            Vec a ((size_t) H + 1, 0.0); for (int k = 1; k <= H; k += 2) a[(size_t) k] = 1.0 / std::sqrt ((double) k);
            add (out, "Odd Harmonics", grow (a, 32));   // 32 frames
        }
        { std::vector<Vec> f; for (int i = 0; i < 64; ++i) f.push_back (fmFrame (8.0 * i / 63)); add (out, "FM Sine", f); }
        { std::vector<Vec> f; for (int i = 0; i < 64; ++i) f.push_back (resoFrame ((double) i / 63)); add (out, "Resonant Saw", f); }
        {
            std::vector<Vec> f;
            for (int v = 0; v < 4; ++v)
                for (int i = 0; i < 8; ++i)
                {
                    const double t = i / 8.0; Vec a = vowelAmp (v), b = vowelAmp (v + 1);
                    for (size_t k = 0; k < a.size(); ++k) a[k] = (1 - t) * a[k] + t * b[k];
                    f.push_back (frame (a));
                }
            f.push_back (frame (vowelAmp (4)));
            add (out, "Vowels", f);
        }
        {
            static const int bars[9] = { 1, 2, 3, 4, 6, 8, 10, 12, 16 };
            static const double w[8][9] = { { 1, 0, 0, 0, 0, 0, 0, 0, 0 }, { 1, 1, 0, 0, 0, 0, 0, 0, 0 }, { 1, 1, 1, 0, 0, 0, 0, 0, 0 }, { 1, .8, .6, .8, 0, 0, 0, 0, 0 },
                                            { 1, .8, .6, .8, .5, .4, .3, .2, .2 }, { .8, 1, 1, 1, .8, .6, .5, .4, .3 }, { .5, 1, .3, .8, .2, .6, .1, .4, .1 }, { 0, 1, 0, 1, 0, 1, 0, 1, 0 } };
            std::vector<Vec> f;
            for (auto& row : w) { Vec a ((size_t) H + 1, 0.0); for (int j = 0; j < 9; ++j) a[(size_t) bars[j]] = row[j]; f.push_back (frame (a)); }
            add (out, "Organ", f);
        }
        return out;
    }

    int installFactoryWavetables (const juce::File& root)
    {
        auto dir = root.getChildFile ("Wavetables").getChildFile ("Factory");
        auto marker = dir.getChildFile (".factory-1");
        if (marker.existsAsFile()) return 0;
        if (! dir.createDirectory()) return 0;
        int n = 0;
        for (auto& t : makeFactoryWavetables())
        {
            auto f = dir.getChildFile (t.name + ".wav");
            if (! f.existsAsFile() && writeWav (f, t.samples)) ++n;
        }
        marker.replaceWithText ("factory wavetables installed; delete this file to install them again\n");
        return n;
    }
}
