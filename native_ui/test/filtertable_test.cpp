#include "../NjoFilterTableSpectrum.h"
#include <cstdio>
using namespace njo::fts;
static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
int main()
{
    const int L = 2048; std::vector<float> w ((size_t) L * 3);
    for (int i = 0; i < L; ++i)
    {
        w[(size_t) i] = (float) std::sin (2 * M_PI * 24 * i / L);                 // frame 0: harmonic 24 -> centre
        w[(size_t) (L + i)] = (float) std::sin (2 * M_PI * 6 * i / L);            // frame 1: harmonic 6 -> 2 octaves below the centre
        w[(size_t) (2 * L + i)] = (float) std::sin (2 * M_PI * 96 * i / L);       // frame 2: harmonic 96 -> 2 octaves above
    }
    auto c = tableToCurves (w, L, 64);
    CHECK (c.size() == 3 * 512);
    auto argmax = [&] (int f) { int b = 0; for (int i = 0; i < 512; ++i) if (c[(size_t) (f * 512 + i)] > c[(size_t) (f * 512 + b)]) b = i; return b; };
    const double per = 511.0 / kRange;                                             // points per octave
    CHECK (std::abs (argmax (0) - 511 * 0.5) <= 2);
    CHECK (std::abs (argmax (1) - (511 * 0.5 - 2 * per)) <= 3);
    CHECK (std::abs (argmax (2) - (511 * 0.5 + 2 * per)) <= 3);
    for (int f = 0; f < 3; ++f) { float mx = -9, mn = 9; for (int i = 0; i < 512; ++i) { mx = std::max (mx, c[(size_t) (f * 512 + i)]); mn = std::min (mn, c[(size_t) (f * 512 + i)]); } CHECK (std::abs (mx - 1) < 1e-4); CHECK (mn >= -1.0001f); }
    // a saw has 1/k harmonics: the curve falls with about 6 dB (half) per octave... in the band average a factor ~0.5 per octave
    std::vector<float> s (L); for (int i = 0; i < L; ++i) s[(size_t) i] = 2.0f * i / L - 1.0f;
    auto cs = frameToCurve (s.data(), L);
    auto G = [&] (int i) { return 0.5 * (cs[(size_t) i] + 1); };
    CHECK (G (256) > G (256 + 57) * 1.6 && G (256) < G (256 + 57) * 2.6);
    std::printf (fails ? "FAILED\n" : "ALL OK\n"); return fails;
}
