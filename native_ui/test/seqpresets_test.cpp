// Factory presets of the modulation sequencers: counts, ranges, Euclid patterns.
#include "../NjoSeqPresets.h"
#include <cstdio>
static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
int main()
{
    using namespace njo::seqpre;
    auto L = all(); CHECK (L.size() >= 90);
    juce::StringArray names; for (auto& p : L) { CHECK (p.len >= 1 && p.len <= 16); for (int k = 0; k < 16; ++k) CHECK (p.v[(size_t) k] >= 0 && p.v[(size_t) k] <= 1 && p.shape[(size_t) k] >= 0 && p.shape[(size_t) k] <= 7); CHECK (! names.contains (p.group + "/" + p.name)); names.add (p.group + "/" + p.name); }
    auto e = euclid (5, 8); int s = 0; for (int v : e) s += v; CHECK (s == 5 && e[0] == 1);
    auto b = euclid (7, 12); s = 0; for (int v : b) s += v; CHECK (s == 7);
    for (auto& p : L) if (p.name.startsWith ("E(")) { int k = p.name.fromFirstOccurrenceOf ("(", false, false).getIntValue(); int h = 0; for (int i = 0; i < p.len; ++i) h += p.v[(size_t) i] > 0.5f; CHECK (h == k); }
    std::printf ("%d presets, %s\n", (int) L.size(), fails ? "FAILED" : "ALL OK");
    return fails ? 1 : 0;
}
