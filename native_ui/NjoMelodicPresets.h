// Factory presets of the Melodic arpeggiator mode (up to 64 steps of note / velocity / length / chord / probability / ratchet / gate).  Written as compact step text:
//   token per step = note (-24..24) + flags:  . rest (gate off) | ^ accent (vel 127) | , soft (vel 70) | ~ tie (length 150 %) | c<n> chord 0..8 | r<n> ratchet 1..4 | p<n> probability % | l<n> length %
// Original lines and the usual progressions (i-VI-III-VII, Andalusian i-VII-VI-V, I-V-vi-IV, ii-V-I ...), header only, tested by native_ui/test/melpresets_test.cpp.
#pragma once
#include <juce_core/juce_core.h>
#include <array>
#include <vector>

namespace njo::melpre
{
    constexpr int N = 64;
    struct Preset
    {
        juce::String group, name; int len = 16;
        std::array<int, N> note {}, vel {}, length {}, chord {}, prob {}, ratchet {}, gate {};
    };

    inline Preset parse (const char* group, const char* name, const juce::String& text, int len = 0)
    {
        Preset p; p.group = group; p.name = name;
        auto t = juce::StringArray::fromTokens (text, " ", ""); t.removeEmptyStrings();
        const int n = juce::jmax (1, juce::jmin (N, t.size()));
        for (int k = 0; k < N; ++k)
        {
            p.note[(size_t) k] = 0; p.vel[(size_t) k] = 100; p.length[(size_t) k] = 80; p.chord[(size_t) k] = 0; p.prob[(size_t) k] = 100; p.ratchet[(size_t) k] = 1; p.gate[(size_t) k] = 1;
            if (t.isEmpty()) continue;
            auto s = t[k % n]; auto u = (size_t) k;
            int i = 0; auto num = [&] { int sign = 1, v = 0; if (i < s.length() && s[i] == '-') { sign = -1; ++i; } while (i < s.length() && s[i] >= '0' && s[i] <= '9') v = v * 10 + (int) (s[i++] - '0'); return sign * v; };
            if (s[0] == '.') { p.gate[u] = 0; continue; }
            p.note[u] = juce::jlimit (-24, 24, num());
            while (i < s.length())
            {
                auto c = s[i++];
                if (c == '^') p.vel[u] = 127; else if (c == ',') p.vel[u] = 70; else if (c == '~') p.length[u] = 150;
                else if (c == 'c') p.chord[u] = juce::jlimit (0, 8, num()); else if (c == 'r') p.ratchet[u] = juce::jlimit (1, 4, num());
                else if (c == 'p') p.prob[u] = juce::jlimit (0, 100, num()); else if (c == 'l') p.length[u] = juce::jlimit (10, 400, num());
            }
        }
        p.len = len > 0 ? juce::jlimit (1, N, len) : n;
        return p;
    }

    // an arpeggio shape (semitones above the root) played over a chord root progression, `per` steps per root
    inline juce::String over (const std::vector<int>& roots, const std::vector<int>& shape, int per)
    {
        juce::String s;
        for (int r : roots) for (int k = 0; k < per; ++k) s << juce::String (r + shape[(size_t) k % shape.size()]) << ((k % 4) == 0 ? "^" : "") << " ";
        return s;
    }
    // one chord per bar (4 steps): the chord on the first step, held, the rest of the bar silent
    inline juce::String bars (const std::vector<int>& roots, const std::vector<int>& chords, bool pulse = false)
    {
        juce::String s;
        for (size_t b = 0; b < roots.size(); ++b)
        {
            s << juce::String (roots[b]) << "^c" << juce::String (chords[b]) << (pulse ? "l50 " : "l390 ");
            for (int k = 1; k < 4; ++k) s << (pulse ? (juce::String (roots[b]) + (k == 2 ? "c" + juce::String (chords[b]) + "l50 " : ",l30 ")) : juce::String (". "));
        }
        return s;
    }

    inline std::vector<Preset> all()
    {
        std::vector<Preset> L;
        auto add = [&] (const char* g, const char* n, const juce::String& t, int len = 0) { L.push_back (parse (g, n, t, len)); };
        // chord numbers: 1 octave, 2 fifth, 3 major, 4 minor, 5 sus4, 6 maj7, 7 min7, 8 dim

        add ("Arpeggios", "Minor Up", "0^ 3 7 12 0 3 7 12", 8);
        add ("Arpeggios", "Major Up", "0^ 4 7 12 0 4 7 12", 8);
        add ("Arpeggios", "Minor Up / Down", "0^ 3 7 12 7 3", 6);
        add ("Arpeggios", "Minor 7 Ladder", "0^ 3 7 10 12 10 7 3", 8);
        add ("Arpeggios", "Major 7 Dream", "0^ 4 7 11 12 11 7 4", 8);
        add ("Arpeggios", "Sus4 Float", "0^ 5 7 12 7 5", 6);
        add ("Arpeggios", "Pentatonic Run", "0^ 3 5 7 10 12 10 7 5 3 0 3 5 7 10 12", 16);
        add ("Arpeggios", "Trance Pluck", "0^ 12 7 12 0 12 7 12 3 15 10 15 5 17 12 17", 16);
        add ("Arpeggios", "Berlin School", "0^ 7 3 12 7 10 3 15 0 7 3 12 10 7 3 0", 16);
        add ("Arpeggios", "Berlin School Slow", "0^ . 7 . 3 . 12 . 7 . 10 . 3 . 15 .", 16);
        add ("Arpeggios", "Dorian Dance", "0^ 2 3 5 7 9 10 12 10 9 7 5 3 2 0 2", 16);
        add ("Arpeggios", "Phrygian Dark", "0^ 1 3 5 7 8 10 12 10 8 7 5 3 1 0 1", 16);
        add ("Arpeggios", "Harmonic Minor Run", "0^ 2 3 5 7 8 11 12 11 8 7 5 3 2 0 2", 16);
        add ("Arpeggios", "Whole Tone Dream", "0^ 2 4 6 8 10 12 10 8 6 4 2", 12);
        add ("Arpeggios", "Octave Jumps", "0^ 12 0 12 0 12 7 12", 8);
        add ("Arpeggios", "Fifths and Octaves", "0^ 7 12 7 0 7 12 19", 8);
        add ("Arpeggios", "Gallop (3 + 3 + 2)", "0^ 12 7 0 12 7 0 12", 8);
        add ("Arpeggios", "Cascade Down", "24^ 19 15 12 7 3 0 -5 -9 -12", 10);
        add ("Arpeggios", "Zigzag 5 Notes", "0^ 7 3 10 5", 5);
        add ("Arpeggios", "Polymeter 7", "0^ 3 7 10 12 15 19", 7);

        add ("Bass lines", "Offbeat Bass (Psy)", ". 0 0 0 . 0 0 0 . 0 0 0 . 0 0 0", 16);
        add ("Bass lines", "Rolling 16th Bass", "0^ 0, 0, 0, 0^ 0, 0, 0, 0^ 0, 0, 0, 7^ 0, 0, 0,", 16);
        add ("Bass lines", "Disco Octaves", "0^ 12 0 12 0^ 12 0 12", 8);
        add ("Bass lines", "Synthwave Eighths", "0^ 0 0 0 -2^ -2 -2 -2 -4^ -4 -4 -4 -5^ -5 -5 -5", 16);
        add ("Bass lines", "Moroder Pulse", "0^ 0, 12 0, 0^ 0, 12 0, 0^ 0, 12 0, 7^ 0, 12 0,", 16);
        add ("Bass lines", "Dub Bass", "0^l200 . . . 0l100 . 7^l150 . . . . . 5l200 . . .", 16);
        add ("Bass lines", "Funk Pocket", "0^ . 0, . 12^ . 7, . 0^ . 0, 10 . 12^ 7, .", 16);
        add ("Bass lines", "Walking Minor", "0^ 3 5 6 7 10 7 5", 8);
        add ("Bass lines", "Sub Pedal", "-12^l390 . . . -12l390 . . . -7^l390 . . . -5l390 . . .", 16);
        add ("Bass lines", "Ratchet Bass", "0^ . 0r2 . 0^ . 7r3 . 0^ . 0r2 . 10^ . 12r4 .", 16);

        add ("Chord progressions", "i - VI - III - VII (Am F C G)", bars ({ 0, -4, 3, -2 }, { 4, 3, 3, 3 }), 16);
        add ("Chord progressions", "Andalusian i - VII - VI - V", bars ({ 0, -2, -4, -5 }, { 4, 3, 3, 3 }), 16);
        add ("Chord progressions", "i - VII - VI - VII", bars ({ 0, -2, -4, -2 }, { 4, 3, 3, 3 }), 16);
        add ("Chord progressions", "i - iv - v - i", bars ({ 0, 5, 7, 0 }, { 4, 4, 4, 4 }), 16);
        add ("Chord progressions", "i - iv - VII - III", bars ({ 0, 5, -2, 3 }, { 4, 4, 3, 3 }), 16);
        add ("Chord progressions", "I - V - vi - IV", bars ({ 0, -5, -3, -7 }, { 3, 3, 4, 3 }), 16);
        add ("Chord progressions", "I - vi - IV - V", bars ({ 0, -3, -7, -5 }, { 3, 4, 3, 3 }), 16);
        add ("Chord progressions", "ii - V - I - I (jazz)", bars ({ 2, -5, 0, 0 }, { 7, 3, 6, 6 }), 16);
        add ("Chord progressions", "i7 - iv7 - i7 - VII", bars ({ 0, 5, 0, -2 }, { 7, 7, 7, 3 }), 16);
        add ("Chord progressions", "Sus Drift", bars ({ 0, -2, -4, -2 }, { 5, 5, 5, 5 }), 16);
        add ("Chord progressions", "Octave Power Chords", bars ({ 0, -4, 3, -2 }, { 1, 1, 1, 1 }), 16);
        add ("Chord progressions", "Fifth Power Chords", bars ({ 0, -4, 3, -2 }, { 2, 2, 2, 2 }), 16);
        add ("Chord progressions", "Trance Pulse i - VI - III - VII", bars ({ 0, -4, 3, -2 }, { 4, 3, 3, 3 }, true), 16);
        add ("Chord progressions", "Stabs Offbeat (minor)", ". 0^c4l40 . 0c4l40 . 0^c4l40 . 0c4l40", 8);
        add ("Chord progressions", "House Stabs", "0^c7l40 . . 0c7l40 . . 0^c7l40 . . . 5c7l40 . . .", 16);
        add ("Chord progressions", "Dim Tension", bars ({ 0, 1, 0, -1 }, { 8, 8, 8, 8 }), 16);

        add ("Long (32 / 64 steps)", "Berlin Journey 32 (Am F)", over ({ 0, -4 }, { 0, 7, 3, 12 }, 16), 32);
        add ("Long (32 / 64 steps)", "Trance Arp 64 (Am F C G)", over ({ 0, -4, 3, -2 }, { 0, 7, 12, 7 }, 16), 64);
        add ("Long (32 / 64 steps)", "Minor Climb 64", over ({ 0, 3, 5, 7 }, { 0, 3, 7, 10 }, 16), 64);
        add ("Long (32 / 64 steps)", "Andalusian Arp 64", over ({ 0, -2, -4, -5 }, { 0, 7, 3, 12, 7, 3, 10, 7 }, 16), 64);
        add ("Long (32 / 64 steps)", "Sus Arp 32", over ({ 0, 5 }, { 0, 5, 7, 12 }, 16), 32);

        add ("Probability / ratchet", "Evolving Pluck", "0^ 3p70 7p70 12p50 7p70 3p60 10p40 12p30", 16);
        add ("Probability / ratchet", "Sparse Melody", "0^ . 7p60 . 3p50 . 10p60 . 12p50 . 5p70 . 7p60 . 3p50 .", 16);
        add ("Probability / ratchet", "Ghost Notes", "0^ 0,p40 7 0,p40 3 0,p40 10 0,p40", 8);
        add ("Probability / ratchet", "Ratchet Rolls", "0^ 0r2 7r3 12r4 3^ 3r2 10r3 12r4", 8);
        add ("Probability / ratchet", "Trap Hats Pitch", "0^ 0,r2 0, 0,r3 12^ 12,r2 12, 12,r4", 8);
        add ("Probability / ratchet", "Stutter Fifths", "0^r2 7r2 0r3 7r3", 4);

        add ("Melodies", "Rising Question", "0 2 3 5 7 . 5 .", 8);
        add ("Melodies", "Call and Response", "0^ 3 5 7 . . 7 5 3 0 . . 5 3 0 .", 16);
        add ("Melodies", "Minor Hook", "7^ . 7 10 12~ . 10 7 5^ . 5 7 3~ . 0 .", 16);
        add ("Melodies", "Lead Sighs", "12^~ . . . 10 . . . 7~ . . . 3 . 5 .", 16);
        add ("Melodies", "Lullaby (3 / 4 feel)", "0^ 4 7 0, 4 7", 6);
        add ("Melodies", "Chiptune Hop", "0^ 12 7 12 3 15 10 15 5 17 12 17 -2 10 7 10", 16);
        return L;
    }
}
