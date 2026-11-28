#include "../NjoFft.h"
#include <cstdio>
int main()
{
    int fails = 0; const int N = 2048;
    std::vector<float> x (N); for (int i = 0; i < N; ++i) x[i] = (float) (0.5 * std::sin (2 * M_PI * 3 * i / N) + 0.25 * std::cos (2 * M_PI * 7 * i / N + 1.0));
    auto m = njo::dsp::harmonicMagnitudes (x, 16);
    if (std::abs (m[2] - 0.5f) > 1e-4 || std::abs (m[6] - 0.25f) > 1e-4 || m[0] > 1e-4 || m[10] > 1e-4) { std::printf ("FAIL magnitudes %f %f\n", m[2], m[6]); ++fails; }
    njo::dsp::editHarmonics (x, [] (int k, njo::dsp::cd& c) { if (k > 4) c = 0; });
    m = njo::dsp::harmonicMagnitudes (x, 16);
    if (std::abs (m[2] - 0.5f) > 1e-4 || m[6] > 1e-4) { std::printf ("FAIL lowpass\n"); ++fails; }
    std::printf (fails ? "FAILED\n" : "ALL OK\n"); return fails;
}
