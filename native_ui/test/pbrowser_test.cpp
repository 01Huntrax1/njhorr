#include "../NjoPresetBrowser.h"
#include <cstdio>
static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
int main()
{
    using namespace njo::pbrowse;
    std::vector<Item> all = { { "a", "Pop Four Chords", "Chords", false }, { "b", "Dark Bass", "Bass", false }, { "c", "My Lead", "Lead", true }, { "d", "Acid Bass", "Bass", true } };
    State st; const juce::String k = "insp";
    CHECK (filter (all, st, k, {}, "").size() == 4);
    CHECK (filter (all, st, k, {}, "bass").size() == 2);
    CHECK (filter (all, st, k, {}, "dark bass").size() == 1);
    CHECK (filter (all, st, k, {}, "chords pop").size() == 1);
    CHECK (filter (all, st, k, { View::Group, "Bass" }, "").size() == 2);
    st.toggleFav (k, "c"); CHECK (st.isFav (k, "c")); CHECK (filter (all, st, k, { View::Favorites, "" }, "").size() == 1);
    st.toggleFav (k, "c"); CHECK (! st.isFav (k, "c"));
    st.setTags (k, "b", "Dark, #heavy;  dark"); CHECK (st.tagsOf (k, "b").size() == 2);
    CHECK (filter (all, st, k, {}, "#heavy").size() == 1 && filter (all, st, k, {}, "#heavy")[0].id == "b");
    CHECK (filter (all, st, k, { View::Tag, "dark" }, "").size() == 1);
    CHECK (filter (all, st, k, {}, "heavy").size() == 1);   // a tag is also found as a word
    st.use (k, "a"); st.use (k, "d"); st.use (k, "a");
    auto r = filter (all, st, k, { View::Recent, "" }, ""); CHECK (r.size() == 2 && r[0].id == "a" && r[1].id == "d");
    st.renamed (k, "d", "e"); st.renamed (k, "b", "z"); CHECK (st.recent[k].contains ("e") && st.tagsOf (k, "z").size() == 2 && st.tagsOf (k, "b").isEmpty());
    st.forget (k, "e"); CHECK (! st.recent[k].contains ("e"));
    for (int i = 0; i < 40; ++i) st.use (k, "x" + juce::String (i)); CHECK (st.recent[k].size() == 30 && st.recent[k][0] == "x39");
    st.toggleFav ("seq", "q");
    auto root = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("pbrowser_test"); st.save (root);
    State s2; s2.load (root); CHECK (s2.isFav ("seq", "q") && s2.tagsOf (k, "z").size() == 2 && s2.recent[k][0] == "x39" && s2.recent[k].size() == 30);
    root.deleteRecursively();
    std::printf (fails ? "FAILED\n" : "ALL OK\n"); return fails ? 1 : 0;
}
