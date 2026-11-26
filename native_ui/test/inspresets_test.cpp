#include "../NjoInspPresets.h"
#include <cstdio>
static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
int main()
{
    using namespace njo::inspre;
    auto L = factory(); CHECK (L.size() >= 50);
    juce::StringArray seen;
    for (auto& p : L)
    {
        auto key = p.group + "/" + p.name; CHECK (! seen.contains (key)); seen.add (key);
        bool hasMode = false, hasStyle = false; for (auto& e : p.v) { CHECK (e.first >= kFirst && e.first <= kLast); hasMode = hasMode || e.first == 7001; hasStyle = hasStyle || e.first == 7002; if (e.first == 7002) CHECK (e.second >= 0 && e.second <= 31); if (e.first == 7001) CHECK (e.second >= 0 && e.second <= 4); if (e.first == 7008) CHECK (e.second >= 0 && e.second <= 3); if (e.first == 7139) CHECK (e.second >= 0 && e.second <= 9); if (e.first == 7140) CHECK (e.second >= 0 && e.second <= 15); if (e.first == 7004) CHECK (e.second >= 0 && e.second <= 6); if (e.first == 7003) CHECK (e.second >= 0 && e.second <= 11); }
        CHECK (hasMode && hasStyle);
    }
    std::vector<std::pair<int, float>> v = { { 7001, 2 }, { 7002, 18 }, { 7009, 12.5f } }, w;
    CHECK (fromText (toText (v), w) && w.size() == 3 && w[2].first == 7009 && std::abs (w[2].second - 12.5f) < 1e-3f);
    CHECK (! fromText ("hello", w));
    CHECK (fromText ("njoins 1\n99 1\n7001 3\nx\n", w) && w.size() == 1 && w[0].first == 7001);
    auto root = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njo_ins_test_" + juce::String (juce::Random::getSystemRandom().nextInt()));
    CHECK (save (root, "My: Preset?", v) && names (root).contains ("My_ Preset_"));
    std::vector<std::pair<int, float>> r; CHECK (load (root, "My: Preset?", r) && r.size() == 3);
    CHECK (remove (root, "My: Preset?") && names (root).isEmpty());
    root.deleteRecursively();
    std::printf (fails ? "FAILED\n" : "ALL OK\n"); return fails ? 1 : 0;
}
