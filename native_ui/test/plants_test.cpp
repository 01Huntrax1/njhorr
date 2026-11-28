// Tests of the factory plants of Hanenbow (native_ui/NjoPlantPresets.h).   g++ -std=c++17 native_ui/test/plants_test.cpp -o /tmp/plants_test && /tmp/plants_test
#include "../NjoPlantPresets.h"
#include <cstdio>
#include <set>
#include <string>
static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
int main()
{
    const auto& all = njo::plants::all();
    CHECK (all.size() >= 8);
    std::set<std::string> names;
    for (auto& p : all)
    {
        CHECK (names.insert (p.name).second);                                     // unique names
        CHECK (p.stem >= 25 && p.stem <= 90 && p.spawn >= 0 && p.spawn <= 100 && p.aim >= -80 && p.aim <= 80);
        CHECK (p.jump >= 40 && p.jump <= 200 && p.bounce >= 20 && p.bounce <= 110 && p.size >= 8 && p.size <= 50 && p.hits >= 1 && p.hits <= 8 && p.step >= -4 && p.step <= 4 && p.scale >= 0 && p.scale <= 11);
        int on = 0;
        for (auto& l : p.leaf) { CHECK (l.side == 0 || l.side == 1); CHECK (l.y >= 0.1f && l.y <= 0.85f); CHECK (l.angle >= 0 && l.angle <= 1); CHECK (l.note >= 0 && l.note <= 24); on += l.on; }
        CHECK (on >= 1);                                                         // a plant with no leaf makes no music
        const auto v = njo::plants::values (p);
        CHECK (v.size() == 10 + 40);
        for (auto& e : v) CHECK ((e.first >= 6700 && e.first <= 6718) || (e.first >= 6720 && e.first <= 6759));
    }
    CHECK (std::string (all[0].name) == "Classic" && all[0].stem == 64);          // the first one is the default plant of the DSP (tools/mod/build_hanenbow.py)
    std::printf (fails ? "FAILED\n" : "ALL OK\n"); return fails ? 1 : 0;
}
