// Pattern bank of the 303 arpeggiator mode: a pattern (up to 64 steps of note / accent / slide / gate and the length) is stored as a small text file
// <root>/303 Patterns/<name>.n303.  Header only so the format can be tested without the editor (native_ui/test/a3bank_test.cpp).
#pragma once
#include <juce_core/juce_core.h>
#include <algorithm>
#include <vector>

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

    // compact pattern text: one token per step, "." = rest, otherwise semitone number (-12..24) + optional "a" (accent) and "s" (slide); a "-" token ties nothing, it is just a rest
    inline Pattern fromTokens (const char* text, int len = 0)
    {
        Pattern p; auto t = juce::StringArray::fromTokens (text, " ", ""); t.removeEmptyStrings();
        const int n = juce::jmin (STEPS, t.size());
        for (int k = 0; k < STEPS; ++k)
        {
            if (n == 0) { p.gate[k] = 1; continue; }
            auto tok = t[k % n];
            if (tok.startsWith (".")) { p.gate[k] = 0; continue; }
            p.gate[k] = 1; p.acc[k] = tok.containsChar ('a'); p.slide[k] = tok.containsChar ('s');
            p.note[k] = tok.retainCharacters ("-0123456789").getIntValue();
        }
        p.len = len > 0 ? len : n;
        clampPattern (p);
        return p;
    }

    struct FactoryEntry { const char* name; const char* steps; };
    // original genre-style lines (not copies of songs); 12-step lines sit over a 4/4 kick for the polymetric acid-techno feel
    inline const std::vector<FactoryEntry>& factoryList()
    {
        static const std::vector<FactoryEntry> L = {
            { "Acid House Classic", "0 . 0a 12 . 0 10s 0 . 12a . 0 3 . 5s ." },
            { "Acid House Squelch", "0 0 12a 0 0 0 7s 0 10a . 0 12 0 . 3s 5" },
            { "Acid House Walk", "0 . 3 . 5 . 7a . 5 . 3 . 0 . 12a ." },
            { "Acid House Slider", "0s 3s 5s 7 . 7s 5s 3 . 0s 12a . 10s 7 . ." },
            { "Acid Techno Drive", "0 0 . 0a 0 . 0 0 . 0a 12 . 0 0 . 0" },
            { "Acid Techno Rumble", "0 . 0 0a . 0 0 . 0a 0 . 12 0 . 0a 0" },
            { "Acid Techno 12", "0 . 0a 7 . 0 10s . 0a 12 . 3" },
            { "Acid Techno 12 Slide", "0 0s 12a . 0 7s 10 . 0a 3s 5 ." },
            { "Acid Trance Rolling", "0 0 12 0 0a 0 12 0 0 0 12a 0 0 0 12 7" },
            { "Acid Trance Climb", "0 0 0 0 3 3 3 3 5 5 5 5 7a 7 10 12a" },
            { "Acid Trance Uplift", "0 12 7 12 0 12 7 12 3 15 10 15 5 17a 12 17" },
            { "Acid Trance Gate", "0 0 0 . 0 0 0 . 3 3 3 . 5a 5 5 ." },
            { "Electro Robot", "0a . . 0 . . 0a . 7 . . 5 . 3 . ." },
            { "Electro Funk", "0a . 0 . 12a . 7 . 0 . 3a . 5 . 7 ." },
            { "Electro Zap", "12a 7 . 12 . 5 . 3a 12 . 7 . 5 . 0a ." },
            { "Electro Booty", "0 0 . 0 . 0a 3 . 5 . 5 . 7a . 5 3" },
            { "Dub Techno Pulse", "0 . . . 0 . . . 7a . . . 5 . . ." },
            { "Dub Techno Chord Pulse", "0a . . 0 . . 0 . . 7a . . 5 . . ." },
            { "Dub Skank", ". 0 . 0 . 0a . 0 . 0 . 0 . 7a . 0" },
            { "Deep Minimal 1", "0 . . 0 . . 12a . . 0 . 7 . . 5 ." },
            { "Deep Minimal 2", "0 . 7 . . 0 . 3a . . 5 . 0 . . 7" },
            { "Minimal Pulse", "0 . 0 . 0a . 0 . 0 . 0 . 7a . 0 ." },
            { "Minimal Hop", "0 . . 7a . . 0 . . 12 . . 5a . . ." },
            { "Euclid 3 of 8 Acid", "0a . . 7 . . 12 ." },
            { "Euclid 5 of 8 Acid", "0a . 7 0 . 12a 0 ." },
            { "Euclid 5 of 16 Bossa", "0a . . 7 . . 12 . . 0 . . 5 . . ." },
            { "Euclid 7 of 16 Samba", "0a . 7 . 0 . 12a . 5 . 7 . 0 . 3 ." },
            { "Euclid 9 of 16", "0a . 7 . 0 5 . 12a . 0 7 . 3 . 5 0" },
            { "Euclid 7 of 12 Bell", "0a . 7 . 0 12a . 5 . 7 . 3" },
            { "Aksak 9", "0a . 7 . 0 12a . 5 ." },
            { "Seven Step Bulgarian", "0a 0 7 . 12a 5 ." },
            { "Detroit Bassline", "0 . 0 . 12 . 0 . 10a . 7 . 0 . 5 ." },
            { "Chicago Jack", "0 0 . 0 12a . 0 . 7 . 0 0 . 10s 7 ." },
            { "Hard Acid Stomp", "0a 0 0a 0 0a 0 0a 12 0a 0 0a 0 7a 0 12a 0" },
            { "Slow Acid Burner", "0 . . . 0a . . . 7 . . . 3a . 5 ." },
            { "Octave Machine", "0 12 0 12a 0 12 0 12 0 12 0 12a 0 12 7 12" },
            { "Ping Pong Octaves", "0 12s 0 12s 7 19s 7 19s 5 17s 5 17s 3 15s 3 15" },
            { "Fifth Jumper", "0 7 0 7a 3 10 3 10a 5 12 5 12a 7 14 7 14" },
            { "Chromatic Slither", "0s 1s 2s 3s 4s 5s 6s 7a . 7s 6s 5s 4s 3s 2s 1s" },
            { "Phrygian Crawl", "0 . 1 . 0a . 3 . 1 . 0 . -2a . 0 ." },
            { "Phrygian Drive", "0 0 1 0 0a 3 1 0 0 1 3 5a 3 1 0 -2" },
            { "Dorian Groove", "0 . 3 5 . 7a . 10 12 . 10 7 . 5 3 ." },
            { "Blues Acid", "0 . 3 . 5 6a 7 . 10 . 7 6 5 . 3 0" },
            { "Low Rider", "-12 . -12 -5a . -12 . -7 . -12a -12 . -5 . -7 -10" },
            { "Sub Octave Walk", "-12 . . -12a . . -7 . . -5 . . -3a . -5 ." },
            { "Sub Pulse", "-12 -12 . -12a -12 . -12 -12 . -12a -12 . -7 -12 . -12" },
            { "Rave Stab Line", "0a . . 0a . . 0a . 12a . . 7 . . 5 ." },
            { "Hoover Walk", "0s 0s 3s 3s 5s 5s 7s 7s 10s 10s 7s 7s 5s 5s 3s 3s" },
            { "Slide Cascade 32", "12s 10s 7s 5s 3s 0s -2 . 0s 3s 5s 7s 10s 12s 15 . 12s 10s 7s 5s 3s 0s -2 . -5s -2s 0s 3a 5s 7s 12a ." },
            { "Long Evolve 32", "0 . 0 . 0a . 0 7 0 . 0 . 3a . 5 . 0 . 0 . 0a . 0 10 0 . 12a . 7 . 5 3" },
            { "Long Acid Journey 48", "0 . 0a 12 . 0 10s 0 . 12a . 0 3 . 5s . 0 . 0a 12 . 0 10s 0 . 12a . 0 3 . 7s . 5 . 5a 17 . 5 15s 5 . 17a . 5 3 . 5s . 3 . 3a 15 . 3 12s 3 . 15a . 3 0 . 3s ." },
            { "Long Techno 64", "0 . 0 0a . 0 . 0 0 . 0a . 0 . 0 0 0 . 0 0a . 0 . 0 0 . 7a . 0 . 0 0 . 0 0a . 0 . 0 0 . 0a . 0 . 0 0 0 . 0 0a . 0 . 0 0 . 10a . 12 . 0 3" },
        };
        return L;
    }

    // factory patterns: written once per version (marker file), existing files with the same name are never overwritten, so the folder stays the user's own
    inline void installFactory (const juce::File& root)
    {
        auto dir = folder (root);
        auto marker = dir.getChildFile (".factory2");
        if (marker.existsAsFile()) return;
        dir.createDirectory();
        auto put = [&] (const juce::String& name, const Pattern& p) { auto f = dir.getChildFile (name + ".n303"); if (! f.existsAsFile()) f.replaceWithText (toText (p)); };
        put ("Acid Classic", fromArrays ({ 0, 0, 12, 0, 0, 10, 0, 7, 0, 12, 0, 0, 3, 5, 0, 0 }, { 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0 }, { 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0 }, { 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0 }, 16));
        put ("Octave Bounce", fromArrays ({ 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 7, 12 }, { 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0 }, { 0 }, { 1 }, 16));
        put ("Slide Line 32", fromArrays ({ 0, 3, 5, 7, 10, 12, 10, 7, 5, 3, 0, -5, -7, -5, 0, 12, 0, 7, 12, 19, 12, 10, 7, 5, 3, 5, 7, 3, 0, -2, -5, -12 },
                                         { 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0 },
                                         { 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0 },
                                         { 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0 }, 32));
        for (auto& e : factoryList()) put (e.name, fromTokens (e.steps));
        marker.replaceWithText ("2");
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
