// Pattern bank of the 303 arpeggiator mode: a pattern (up to 64 steps of note / accent / slide / gate and the length) is stored as a small text file
// <root>/303 Patterns/<name>.n303.  Header only so the format can be tested without the editor (native_ui/test/a3bank_test.cpp).
#pragma once
#include <juce_core/juce_core.h>
#include <algorithm>

namespace njo::a3
{
    constexpr int STEPS = 64;
    struct Pattern
    {
        int len = 16;
        int note[STEPS] = {}, acc[STEPS] = {}, slide[STEPS] = {}, gate[STEPS] = {};
    };

    inline void clampPattern (Pattern& p)
    {
        p.len = juce::jlimit (1, STEPS, p.len);
        for (int k = 0; k < STEPS; ++k)
        {
            p.note[k] = juce::jlimit (-12, 24, p.note[k]);
            p.acc[k] = p.acc[k] != 0; p.slide[k] = p.slide[k] != 0; p.gate[k] = p.gate[k] != 0;
        }
    }

    inline juce::String toText (const Pattern& p)
    {
        auto row = [] (const char* tag, const int* v) { juce::String s (tag); for (int k = 0; k < STEPS; ++k) s << " " << v[k]; return s + "\n"; };
        return "njo303 1\nlen " + juce::String (p.len) + "\n" + row ("note", p.note) + row ("acc", p.acc) + row ("slide", p.slide) + row ("gate", p.gate);
    }

    // false = not a 303 pattern file; rows that are missing or short keep the defaults (note 0, accent / slide off, gate on)
    inline bool fromText (const juce::String& text, Pattern& out)
    {
        auto lines = juce::StringArray::fromLines (text);
        if (lines.isEmpty() || ! lines[0].trim().startsWith ("njo303")) return false;
        Pattern p;
        for (int k = 0; k < STEPS; ++k) p.gate[k] = 1;
        for (int i = 1; i < lines.size(); ++i)
        {
            auto t = juce::StringArray::fromTokens (lines[i], " \t", "");
            t.removeEmptyStrings();
            if (t.size() < 2) continue;
            int* dst = t[0] == "note" ? p.note : t[0] == "acc" ? p.acc : t[0] == "slide" ? p.slide : t[0] == "gate" ? p.gate : nullptr;
            if (t[0] == "len") p.len = t[1].getIntValue();
            else if (dst != nullptr) for (int k = 0; k < STEPS && k + 1 < t.size(); ++k) dst[k] = t[k + 1].getIntValue();
        }
        clampPattern (p);
        out = p;
        return true;
    }

    inline juce::File folder (const juce::File& root) { return root.getChildFile ("303 Patterns"); }

    inline juce::String safeName (const juce::String& name)
    {
        juce::String n;
        for (auto c : name) n << ((c < 32 || juce::String ("\\/:*?\"<>|").containsChar (c)) ? juce::juce_wchar ('_') : c);
        return n.trimCharactersAtStart (". \t").trimCharactersAtEnd (". \t").substring (0, 60);
    }

    inline Pattern fromArrays (std::initializer_list<int> note, std::initializer_list<int> acc, std::initializer_list<int> slide, std::initializer_list<int> gate, int len)
    {
        Pattern p; p.len = len;
        auto fill = [] (int* d, std::initializer_list<int> v, int dflt) { int n = (int) v.size(); int k = 0; for (int x : v) d[k++] = x; for (; k < STEPS; ++k) d[k] = n > 0 ? d[k % n] : dflt; };
        fill (p.note, note, 0); fill (p.acc, acc, 0); fill (p.slide, slide, 0); fill (p.gate, gate, 1);
        clampPattern (p);
        return p;
    }

    // the three patterns written the first time the folder is created
    inline void installFactory (const juce::File& root)
    {
        auto dir = folder (root);
        if (dir.exists()) return;
        dir.createDirectory();
        auto put = [&] (const char* name, const Pattern& p) { dir.getChildFile (juce::String (name) + ".n303").replaceWithText (toText (p)); };
        put ("Acid Classic", fromArrays ({ 0, 0, 12, 0, 0, 10, 0, 7, 0, 12, 0, 0, 3, 5, 0, 0 }, { 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0 }, { 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0 }, { 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0 }, 16));
        put ("Octave Bounce", fromArrays ({ 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 7, 12 }, { 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0 }, { 0 }, { 1 }, 16));
        put ("Slide Line 32", fromArrays ({ 0, 3, 5, 7, 10, 12, 10, 7, 5, 3, 0, -5, -7, -5, 0, 12, 0, 7, 12, 19, 12, 10, 7, 5, 3, 5, 7, 3, 0, -2, -5, -12 },
                                         { 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0 },
                                         { 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0 },
                                         { 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0 }, 32));
    }

    inline juce::StringArray names (const juce::File& root)
    {
        juce::StringArray out;
        for (auto& f : folder (root).findChildFiles (juce::File::findFiles, false, "*.n303")) out.add (f.getFileNameWithoutExtension());
        out.sort (true);
        return out;
    }
    inline bool load (const juce::File& root, const juce::String& name, Pattern& p) { return fromText (folder (root).getChildFile (safeName (name) + ".n303").loadFileAsString(), p); }
    inline bool save (const juce::File& root, const juce::String& name, const Pattern& p)
    {
        auto n = safeName (name);
        if (n.isEmpty()) return false;
        folder (root).createDirectory();
        return folder (root).getChildFile (n + ".n303").replaceWithText (toText (p));
    }
    inline bool remove (const juce::File& root, const juce::String& name) { return folder (root).getChildFile (safeName (name) + ".n303").deleteFile(); }
}
