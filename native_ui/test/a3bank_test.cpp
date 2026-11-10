// 303 pattern bank: text format round trip, bad files, factory patterns, save / list / load / delete.
//   g++ -std=c++17 ... native_ui/test/a3bank_test.cpp <juce_core objects> && ./a.out
#include "../NjoA3Bank.h"
#include <cstdio>

static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)

int main()
{
    using namespace njo::a3;
    Pattern p; p.len = 37;
    for (int k = 0; k < STEPS; ++k) { p.note[k] = (k * 5) % 37 - 12; p.acc[k] = k % 3 == 0; p.slide[k] = k % 5 == 0; p.gate[k] = k % 7 != 0; }
    Pattern q;
    CHECK (fromText (toText (p), q));
    CHECK (q.len == 37);
    bool same = true; for (int k = 0; k < STEPS; ++k) same = same && q.note[k] == p.note[k] && q.acc[k] == p.acc[k] && q.slide[k] == p.slide[k] && q.gate[k] == p.gate[k];
    CHECK (same);
    Pattern bad; CHECK (! fromText ("hello", bad) && ! fromText ("", bad));
    Pattern c; CHECK (fromText ("njo303 1\nlen 999\nnote 100 -100 5\n", c)); CHECK (c.len == 64 && c.note[0] == 24 && c.note[1] == -12 && c.note[2] == 5 && c.note[3] == 0 && c.gate[63] == 1);   // clamped, short rows keep the defaults

    auto root = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njo_a3_test_" + juce::String (juce::Random::getSystemRandom().nextInt()));
    installFactory (root);
    auto n = names (root);
    CHECK (n.size() == 3 && n.contains ("Acid Classic") && n.contains ("Slide Line 32"));
    Pattern a; CHECK (load (root, "Acid Classic", a)); CHECK (a.len == 16 && a.note[2] == 12 && a.acc[2] == 1 && a.slide[3] == 1 && a.gate[5] == 0 && a.note[18] == 12);   // steps 17.. repeat
    Pattern s; CHECK (load (root, "Slide Line 32", s)); CHECK (s.len == 32 && s.note[31] == -12);
    CHECK (save (root, "My: pattern?", p)); CHECK (names (root).contains ("My_ pattern_"));
    Pattern r; CHECK (load (root, "My: pattern?", r) && r.len == 37 && r.note[10] == p.note[10]);
    installFactory (root); CHECK (names (root).size() == 4);   // a second call leaves the folder alone
    CHECK (remove (root, "My: pattern?") && names (root).size() == 3);
    CHECK (! save (root, "  ...", p));
    root.deleteRecursively();
    std::printf (fails ? "FAILED\n" : "ALL OK\n");
    return fails ? 1 : 0;
}
