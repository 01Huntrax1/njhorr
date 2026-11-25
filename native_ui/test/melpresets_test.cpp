// Melodic arp factory presets: parser flags, ranges, chord bars.
#include "../NjoMelodicPresets.h"
#include <cstdio>
static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
int main()
{
    using namespace njo::melpre;
    auto p = parse ("g", "n", "0^ . -5c4l390 7r3p50 12~ 3,", 0);
    CHECK (p.len == 6 && p.vel[0] == 127 && p.gate[1] == 0 && p.note[2] == -5 && p.chord[2] == 4 && p.length[2] == 390 && p.ratchet[3] == 3 && p.prob[3] == 50 && p.length[4] == 150 && p.vel[5] == 70 && p.note[6] == 0);
    auto L = all(); CHECK (L.size() >= 60);
    juce::StringArray names;
    for (auto& e : L)
    {
        CHECK (e.len >= 1 && e.len <= N); auto key = e.group + "/" + e.name; CHECK (! names.contains (key)); names.add (key);
        for (int k = 0; k < N; ++k) { auto u = (size_t) k; CHECK (e.note[u] >= -24 && e.note[u] <= 24 && e.vel[u] >= 1 && e.vel[u] <= 127 && e.length[u] >= 10 && e.length[u] <= 400 && e.chord[u] >= 0 && e.chord[u] <= 8 && e.prob[u] <= 100 && e.ratchet[u] >= 1 && e.ratchet[u] <= 4); }
        bool any = false; for (int k = 0; k < e.len; ++k) any = any || e.gate[(size_t) k]; CHECK (any);
    }
    for (auto& e : L) if (e.name.startsWith ("i - VI - III")) CHECK (e.len == 16 && e.chord[0] == 4 && e.note[4] == -4 && e.chord[4] == 3 && e.gate[1] == 0 && e.length[0] == 390);
    std::printf ("%d presets, %s\n", (int) L.size(), fails ? "FAILED" : "ALL OK");
    return fails ? 1 : 0;
}
