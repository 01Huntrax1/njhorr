#include "../NjoTableOps.h"
#include <cstdio>
static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
int main()
{
    using namespace njo::tblops;
    float f[FL], c[NH];
    for (int i = 0; i < FL; ++i) f[i] = 0.5f * cheb (3, sOf (i)) + 0.25f * cheb (2, sOf (i));
    chebAnalyse (f, c);
    CHECK (std::abs (c[2] - 0.5f) < 0.01f && std::abs (c[1] - 0.25f) < 0.01f && std::abs (c[0]) < 0.01f && std::abs (c[4]) < 0.01f);
    chebSet (f, 5, 0.4f); chebAnalyse (f, c);
    CHECK (std::abs (c[4] - 0.4f) < 0.02f && std::abs (c[2] - 0.5f) < 0.02f && std::abs (c[1] - 0.25f) < 0.02f);
    // a Chebyshev T3 curve driven by a sine gives the third harmonic
    for (int i = 0; i < FL; ++i) f[i] = cheb (3, sOf (i));
    double a1 = 0, a3 = 0; for (int k = 0; k < 1024; ++k) { double t = 2 * M_PI * k / 1024; double s = std::sin (t); float y = f[juce::jlimit (0, FL - 1, (int) std::lround ((s + 1) * 0.5 * (FL - 1)))]; a1 += y * std::sin (t); a3 += y * std::sin (3 * t); }
    CHECK (std::abs (a1) < 0.03 * 512 && std::abs (a3) > 0.9 * 512 * 0.9 * 0.0 + 400);
    generate (false, "SOFT", f); oddSymmetry (f); CHECK (std::abs (f[10] + f[FL - 11]) < 1e-5f);
    generate (false, "ASYM", f); evenSymmetry (f); CHECK (std::abs (f[10] - f[FL - 11]) < 1e-5f);
    generate (false, "FOLD", f); rectify (f); bool pos = true; for (float x : f) pos = pos && x >= 0; CHECK (pos);
    generate (false, "LINEAR", f); quantise (f, 4); CHECK (std::abs (f[FL - 1] - 1.0f) < 1e-5f && std::abs (f[FL / 2 + 100] * 4 - std::round (f[FL / 2 + 100] * 4)) < 1e-5f);
    for (bool flt : { false, true }) for (auto n : names (flt)) { generate (flt, n, f); bool ok = true, var = false; for (int i = 0; i < FL; ++i) { ok = ok && std::isfinite (f[i]) && std::abs (f[i]) <= 1.0f; var = var || std::abs (f[i] - f[0]) > 0.05f; } CHECK (ok); CHECK (var); }
    generate (false, "LINEAR", f); CHECK (std::abs (f[0] + 1) < 1e-5f && std::abs (f[FL - 1] - 1) < 1e-5f);
    std::printf (fails ? "FAILED\n" : "ALL OK\n"); return fails ? 1 : 0;
}
