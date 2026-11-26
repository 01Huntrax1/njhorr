// Inspirator presets: a preset is a list of (parameter id, value) pairs of the Inspirator parameters 7001..7144.  Factory presets (about 50, by mode) are built here from the
// settings of the generators; user presets are text files <root>/InspiratorPresets/<name>.nins ("njoins 1", then "id value" per line).  Header only; tested by native_ui/test/inspresets_test.cpp.
#pragma once
#include <juce_core/juce_core.h>
#include <utility>
#include <vector>

namespace njo::inspre
{
    constexpr int kFirst = 7001, kLast = 7144, kOn = 7000, kMidiIn = 7010;
    struct Preset { juce::String group, name; std::vector<std::pair<int, float>> v; };

    inline bool keepsOnSave (int id) { return id >= kFirst && id <= kLast && id != kMidiIn; }

    inline std::vector<Preset> factory()
    {
        std::vector<Preset> L;
        // mode 0 chords 1 lead 2 bass 3 arp 4 drums; style as in the style list; scale 0 Major 1 Minor 2 Dorian 3 Mixolydian 4 Phrygian 5 Lydian 6 Harmonic minor; bars index 0..3 = 1 / 2 / 4 / 8
        // generator 0 Classic 1 Euclid 2 Markov 3 Cellular 4 L-System 6 Walk 7 Permute 8 Trance 9 Genre
        struct B
        {
            Preset p;
            B (const char* g, const char* n, int mode, int style, int key, int scale, int bars, int gen, int variant, int song, int part)
            {
                p.group = g; p.name = n;
                set (7001, (float) mode); set (7002, (float) style); set (7003, (float) key); set (7004, (float) scale); set (7005, (float) song); set (7006, (float) part);
                set (7008, (float) bars); set (7139, (float) gen); set (7140, (float) variant);
            }
            B& set (int id, float v) { for (auto& e : p.v) if (e.first == id) { e.second = v; return *this; } p.v.push_back ({ id, v }); return *this; }
            B& knob (int mode, int k, float v) { return set (7044 + 9 * mode + k, v); }   // k 0 Complexity 1 Density 2 Humanize 3 Octave 4 Range 5 Gate 6 Velocity 7 Vel Random 8 Dur Random
            B& swing (float v) { return set (7009, v); }
        };
        auto add = [&] (B b) { L.push_back (b.p); };
        const char* G[5] = { "Chords", "Lead", "Bass", "Arp", "Drums" };

        add (B (G[0], "Pop Four Chords",           0, 0, 0, 0, 2, 0, 0, 1234, 1).knob (0, 0, 30));
        add (B (G[0], "Neo-Soul Ninths",           0, 8, 3, 1, 2, 0, 0, 4711, 3).knob (0, 0, 88).knob (0, 2, 35).swing (12));
        add (B (G[0], "Jazz ii-V-I",               0, 7, 5, 0, 2, 0, 0, 88, 7).knob (0, 0, 92).knob (0, 2, 30));
        add (B (G[0], "Lo-Fi Dust",                0, 4, 9, 1, 2, 0, 0, 2024, 5).knob (0, 0, 70).knob (0, 2, 40).swing (28));
        add (B (G[0], "Trance Plucks",             0, 18, 9, 1, 2, 8, 3, 1999, 2).knob (0, 0, 25));
        add (B (G[0], "Synthwave Pads",            0, 16, 6, 1, 2, 0, 0, 1984, 4).knob (0, 0, 45).knob (0, 5, 100));
        add (B (G[0], "Gospel Stack",              0, 29, 7, 0, 2, 0, 0, 777, 9).knob (0, 0, 82).knob (0, 2, 25));
        add (B (G[0], "Ambient Drift",             0, 25, 2, 5, 3, 0, 0, 303, 11).knob (0, 0, 60).knob (0, 1, 20).knob (0, 5, 100));
        add (B (G[0], "Bossa Nova Comping",        0, 15, 7, 0, 2, 9, 0, 1962, 6).knob (0, 0, 85).swing (10));
        add (B (G[0], "Dub Skank",                 0, 13, 9, 1, 2, 9, 0, 420, 2).knob (0, 0, 35));
        add (B (G[0], "House Stabs",               0, 5, 11, 1, 2, 9, 1, 909, 8).knob (0, 0, 55));
        add (B (G[0], "Dark Phrygian",             0, 22, 4, 4, 2, 0, 0, 666, 13).knob (0, 0, 35));
        add (B (G[0], "Dorian Funk",               0, 12, 2, 2, 2, 9, 0, 1977, 12).knob (0, 0, 75).swing (8));
        add (B (G[0], "Euclid Chord Hits",         0, 6, 0, 1, 2, 1, 5, 5555, 4).knob (0, 0, 40));

        add (B (G[1], "Call and Response",         1, 18, 9, 1, 2, 8, 0, 1234, 1));
        add (B (G[1], "Focus Note",                1, 18, 9, 1, 2, 8, 4, 1234, 2));
        add (B (G[1], "Micro Phrases",             1, 18, 4, 1, 2, 8, 8, 1234, 3));
        add (B (G[1], "Acid Line",                 1, 6, 0, 1, 2, 8, 12, 303, 4));
        add (B (G[1], "Markov Pop Melody",         1, 0, 0, 0, 2, 2, 0, 321, 1));
        add (B (G[1], "Markov Minor Melody",       1, 4, 9, 1, 2, 2, 1, 321, 2));
        add (B (G[1], "Markov Jazz Lines",         1, 7, 5, 0, 2, 2, 2, 321, 3).knob (1, 0, 70));
        add (B (G[1], "Random Walk Lead",          1, 16, 6, 1, 2, 6, 0, 99, 5));
        add (B (G[1], "Permuted Motif",            1, 12, 2, 2, 2, 7, 0, 64, 5));
        add (B (G[1], "Genre Lead: Salsa",         1, 21, 9, 1, 2, 9, 0, 1, 1));
        add (B (G[1], "Genre Lead: Country",       1, 23, 7, 0, 2, 9, 0, 1, 1));
        add (B (G[1], "Cellular Sparkle",          1, 25, 0, 5, 3, 3, 1, 2, 2));

        add (B (G[2], "Rolling Trance Bass",       2, 18, 9, 1, 2, 8, 0, 1234, 1));
        add (B (G[2], "Offbeat Bass",              2, 18, 9, 1, 2, 8, 1, 1234, 1));
        add (B (G[2], "Gallop Bass",               2, 18, 9, 1, 2, 8, 2, 1234, 1));
        add (B (G[2], "Psy Bass",                  2, 18, 6, 4, 2, 8, 3, 1234, 1));
        add (B (G[2], "Funk Bass",                 2, 12, 4, 2, 2, 9, 0, 1977, 2).swing (8));
        add (B (G[2], "Dub Sub",                   2, 13, 9, 1, 2, 9, 1, 420, 2).knob (2, 5, 100));
        add (B (G[2], "Techno Pulse",              2, 6, 0, 1, 2, 1, 3, 1313, 4));
        add (B (G[2], "Disco Octaves",             2, 14, 7, 1, 2, 9, 0, 1978, 3).set (7141, 2));
        add (B (G[2], "Bossa Walk",                2, 15, 2, 0, 2, 9, 0, 1962, 1));
        add (B (G[2], "Chord Root Bass",           2, 0, 0, 0, 2, 0, 0, 1234, 1).set (7141, 1));

        add (B (G[3], "Trance Arp 16ths",          3, 18, 9, 1, 2, 8, 0, 1234, 1));
        add (B (G[3], "Trance Arp Up/Down",        3, 18, 9, 1, 2, 8, 5, 1234, 1));
        add (B (G[3], "Berlin School",             3, 16, 6, 1, 2, 9, 2, 1984, 3));
        add (B (G[3], "Cellular Arp",              3, 6, 0, 1, 2, 3, 2, 30, 1));
        add (B (G[3], "L-System Arp",              3, 25, 2, 2, 3, 4, 1, 7, 1));
        add (B (G[3], "Euclid Arp",                3, 5, 11, 1, 2, 1, 7, 1313, 2));
        add (B (G[3], "Soul Arp",                  3, 8, 3, 1, 2, 9, 1, 4711, 3));

        add (B (G[4], "House Four on the Floor",   4, 5, 0, 0, 2, 0, 0, 909, 1));
        add (B (G[4], "Techno Kit",                4, 6, 0, 1, 2, 0, 0, 1313, 1));
        add (B (G[4], "Trap Hats",                 4, 3, 0, 1, 2, 0, 0, 808, 2).set (7143, 60));
        add (B (G[4], "Drum and Bass Break",       4, 10, 0, 1, 2, 0, 0, 170, 3));
        add (B (G[4], "UK Garage Shuffle",         4, 20, 0, 1, 2, 0, 0, 2000, 1).swing (40));
        add (B (G[4], "Euclid Poly Percussion",    4, 6, 0, 1, 2, 1, 4, 5555, 1).set (7144, 1));
        add (B (G[4], "Reggaeton Dembow",          4, 9, 0, 1, 2, 0, 0, 2004, 2));
        add (B (G[4], "Amapiano Groove",           4, 27, 0, 1, 2, 0, 0, 2019, 1).swing (14));
        add (B (G[4], "Breakbeat",                 4, 28, 0, 1, 2, 0, 0, 1990, 4));
        add (B (G[4], "Hardstyle Kit",             4, 30, 0, 1, 2, 0, 0, 150, 1));
        add (B (G[4], "Lo-Fi Boom Bap",            4, 4, 0, 1, 2, 0, 0, 2024, 3).swing (30));
        add (B (G[4], "Drill Slides",              4, 19, 0, 1, 2, 0, 0, 140, 2).set (7143, 40));
        add (B (G[4], "Sparse Chance Drums",       4, 25, 0, 1, 3, 0, 0, 12, 1).set (7142, 55));
        return L;
    }

    inline juce::File folder (const juce::File& root) { return root.getChildFile ("InspiratorPresets"); }
    inline juce::String safeName (const juce::String& n)
    {
        juce::String s; for (auto c : n) s << ((c < 32 || juce::String ("\\/:*?\"<>|").containsChar (c)) ? juce::juce_wchar ('_') : c);
        return s.trimCharactersAtStart (". \t").trimCharactersAtEnd (". \t").substring (0, 60);
    }
    inline juce::String toText (const std::vector<std::pair<int, float>>& v)
    {
        juce::String s ("njoins 1\n"); for (auto& e : v) s << e.first << " " << juce::String (e.second, 3) << "\n"; return s;
    }
    inline bool fromText (const juce::String& text, std::vector<std::pair<int, float>>& out)
    {
        auto lines = juce::StringArray::fromLines (text);
        if (lines.isEmpty() || ! lines[0].trim().startsWith ("njoins")) return false;
        out.clear();
        for (int i = 1; i < lines.size(); ++i)
        {
            auto t = juce::StringArray::fromTokens (lines[i], " \t", ""); t.removeEmptyStrings();
            if (t.size() < 2) continue;
            const int id = t[0].getIntValue(); if (id >= kFirst && id <= kLast) out.push_back ({ id, t[1].getFloatValue() });
        }
        return true;
    }
    inline juce::StringArray names (const juce::File& root)
    {
        juce::StringArray o; for (auto& f : folder (root).findChildFiles (juce::File::findFiles, false, "*.nins")) o.add (f.getFileNameWithoutExtension());
        o.sort (true); return o;
    }
    inline bool save (const juce::File& root, const juce::String& name, const std::vector<std::pair<int, float>>& v)
    {
        auto n = safeName (name); if (n.isEmpty()) return false;
        folder (root).createDirectory(); return folder (root).getChildFile (n + ".nins").replaceWithText (toText (v));
    }
    inline bool load (const juce::File& root, const juce::String& name, std::vector<std::pair<int, float>>& v) { return fromText (folder (root).getChildFile (safeName (name) + ".nins").loadFileAsString(), v); }
    inline bool remove (const juce::File& root, const juce::String& name) { return folder (root).getChildFile (safeName (name) + ".nins").deleteFile(); }
}
