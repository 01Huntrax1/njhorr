// Factory presets of the ten 16-step modulation sequencers: step values (0..1), step shapes, length and optionally direction / polarity.  Generated at start from
// a few rules (waves, Euclidean rhythms after Toussaint, arpeggio levels, gates), so the list stays small in code.  Header only (tested by native_ui/test/seqpresets_test.cpp).
#pragma once
#include <juce_core/juce_core.h>
#include <array>
#include <cmath>
#include <functional>
#include <vector>

namespace njo::seqpre
{
    struct Preset
    {
        juce::String group, name; int len = 16; std::array<float, 16> v {}; std::array<int, 16> shape {}; int dir = -1, bipolar = -1, glide = -1;   // -1: leave the setting alone
    };

    // Bjorklund / Euclid: k hits spread as evenly as possible over n steps (a hit on step 0)
    inline std::vector<int> euclid (int k, int n)
    {
        std::vector<int> r ((size_t) n, 0);
        for (int i = 0; i < k; ++i) r[(size_t) ((i * n) / juce::jmax (1, k))] = 1;
        return r;
    }

    inline std::vector<Preset> all()
    {
        std::vector<Preset> L;
        auto add = [&] (const char* g, const char* n, int len, const std::function<float (int)>& f, int dir = -1, int bip = -1, int glide = -1)
        {
            Preset p; p.group = g; p.name = n; p.len = len; p.dir = dir; p.bipolar = bip; p.glide = glide;
            for (int k = 0; k < 16; ++k) p.v[(size_t) k] = juce::jlimit (0.0f, 1.0f, f (k % juce::jmax (1, len)));
            L.push_back (p); return &L.back();
        };
        const float pi = juce::MathConstants<float>::pi;
        auto rnd = [] (int seed, int k) { unsigned x = (unsigned) (seed * 2654435761u + (unsigned) k * 40503u + 12345u); x ^= x >> 13; x *= 1274126177u; x ^= x >> 16; return (float) (x & 1023u) / 1023.0f; };

        // ---- Waves ----
        add ("Waves", "Ramp Up", 16, [] (int k) { return k / 15.0f; });
        add ("Waves", "Ramp Down", 16, [] (int k) { return 1.0f - k / 15.0f; });
        add ("Waves", "Triangle", 16, [] (int k) { return k < 8 ? k / 7.0f : (15 - k) / 7.0f; });
        add ("Waves", "Sine", 16, [=] (int k) { return 0.5f + 0.5f * std::sin (2 * pi * k / 16.0f); });
        add ("Waves", "Sine x2", 16, [=] (int k) { return 0.5f + 0.5f * std::sin (4 * pi * k / 16.0f); });
        add ("Waves", "Sine x4", 16, [=] (int k) { return 0.5f + 0.5f * std::sin (8 * pi * k / 16.0f + 0.5f); });
        add ("Waves", "Square", 16, [] (int k) { return k < 8 ? 1.0f : 0.0f; });
        add ("Waves", "Pulse 25 %", 16, [] (int k) { return k < 4 ? 1.0f : 0.0f; });
        add ("Waves", "Pulse 12 %", 16, [] (int k) { return k < 2 ? 1.0f : 0.0f; });
        add ("Waves", "Stairs Up (4)", 16, [] (int k) { return (k / 4) / 3.0f; });
        add ("Waves", "Stairs Down (4)", 16, [] (int k) { return 1.0f - (k / 4) / 3.0f; });
        add ("Waves", "Stairs Up (8)", 16, [] (int k) { return (k / 2) / 7.0f; });
        add ("Waves", "Saw x2", 16, [] (int k) { return (k % 8) / 7.0f; });
        add ("Waves", "Saw x4", 16, [] (int k) { return (k % 4) / 3.0f; });
        add ("Waves", "Exponential Rise", 16, [] (int k) { return std::pow (k / 15.0f, 2.5f); });
        add ("Waves", "Exponential Fall", 16, [] (int k) { return std::pow (1.0f - k / 15.0f, 2.5f); });
        add ("Waves", "Half Sine", 16, [=] (int k) { return std::sin (pi * (k + 0.5f) / 16.0f); });
        add ("Waves", "Bounce", 16, [] (int k) { const float t = (k % 8) / 8.0f; return 1.0f - 4.0f * (t - 0.5f) * (t - 0.5f) * 1.0f; });
        add ("Waves", "Ping-Pong Zigzag", 16, [] (int k) { static const float z[8] = { 0, 1, 0.15f, 0.85f, 0.3f, 0.7f, 0.45f, 0.55f }; return z[k % 8]; });
        add ("Waves", "Alternate High / Low", 16, [] (int k) { return (k & 1) ? 0.15f : 0.85f; });
        add ("Waves", "Swing (long / short)", 16, [] (int k) { return (k & 1) ? 0.35f : 0.75f; });
        add ("Waves", "Center Out", 16, [] (int k) { return std::abs (k - 7.5f) / 7.5f; });
        add ("Waves", "Edges In", 16, [] (int k) { return 1.0f - std::abs (k - 7.5f) / 7.5f; });

        // ---- Random / sample and hold ----
        for (int s = 1; s <= 4; ++s)
        {
            auto name = juce::String ("Sample & Hold ") + juce::String (s);
            auto* p = add ("Random", "x", 16, [=] (int k) { return rnd (s, k); });
            p->name = name; for (int k = 0; k < 16; ++k) p->shape[(size_t) k] = 0;
        }
        add ("Random", "Smooth Random 1", 16, [=] (int k) { return 0.5f * (rnd (11, k) + rnd (11, (k + 1) % 16)); });
        add ("Random", "Smooth Random 2", 16, [=] (int k) { return 0.5f * (rnd (12, k) + rnd (12, (k + 1) % 16)); }, -1, -1, 1);
        add ("Random", "Sparse Hits", 16, [=] (int k) { return rnd (21, k) > 0.7f ? 0.5f + 0.5f * rnd (22, k) : 0.0f; });
        add ("Random", "Dense Hits", 16, [=] (int k) { return rnd (31, k) > 0.3f ? 0.4f + 0.6f * rnd (32, k) : 0.0f; });
        add ("Random", "Random Walk", 16, [=] (int k) { float x = 0.5f; for (int i = 0; i <= k; ++i) x += (rnd (41, i) - 0.5f) * 0.4f, x = juce::jlimit (0.0f, 1.0f, x); return x; });

        // ---- Rhythms (hits = 1) ----
        auto rh = [&] (const char* name, int k, int n, bool accent = false)
        {
            auto e = euclid (k, n);
            add ("Rhythm (Euclid)", name, n, [e, accent] (int s) { return e[(size_t) s] ? (accent && s == 0 ? 1.0f : (accent ? 0.7f : 1.0f)) : 0.0f; });
        };
        rh ("E(2,5) Persian", 2, 5); rh ("E(3,4) Cumbia", 3, 4); rh ("E(3,7) Ruchenitza", 3, 7); rh ("E(3,8) Tresillo", 3, 8); rh ("E(4,7) Bulgarian", 4, 7);
        rh ("E(4,9) Aksak", 4, 9); rh ("E(5,6) York-Samai", 5, 6); rh ("E(5,7) Nawakhat", 5, 7); rh ("E(5,8) Cinquillo", 5, 8); rh ("E(5,9) Agsag-Samai", 5, 9);
        rh ("E(5,12) Venda", 5, 12); rh ("E(5,16) Bossa Nova", 5, 16); rh ("E(7,8) Malian", 7, 8); rh ("E(7,12) West African Bell", 7, 12); rh ("E(7,16) Samba", 7, 16);
        rh ("E(9,16) Central African", 9, 16); rh ("E(11,16) Dense", 11, 16); rh ("E(13,16) Almost Full", 13, 16);
        auto pat = [&] (const char* g, const char* name, const char* s, bool acc = false)
        {
            std::string t (s); const int n = (int) t.size();
            add (g, name, n, [t, acc] (int k) { char c = t[(size_t) k]; return c == 'x' ? 1.0f : c == 'o' ? (acc ? 0.55f : 1.0f) : c == '-' ? 0.25f : 0.0f; });
        };
        pat ("Rhythm", "Four on the Floor", "x...x...x...x...");
        pat ("Rhythm", "Offbeat", "..x...x...x...x.");
        pat ("Rhythm", "Backbeat", "....x.......x...");
        pat ("Rhythm", "Eighths", "x.x.x.x.x.x.x.x.");
        pat ("Rhythm", "Sixteenths", "xxxxxxxxxxxxxxxx");
        pat ("Rhythm", "Son Clave 3-2", "x..x..x...x.x...");
        pat ("Rhythm", "Rumba Clave 3-2", "x..x...x..x.x...");
        pat ("Rhythm", "Bossa Clave", "x..x..x...x..x..");
        pat ("Rhythm", "Shiko", "x...x.x...x.x...");
        pat ("Rhythm", "Gahu", "x..x..x...x...x.");
        pat ("Rhythm", "Breakbeat", "x.....x...x.x...");
        pat ("Rhythm", "Techno Kick Fill", "x...x...x...x.xx");
        pat ("Rhythm", "Dub Chop", "..x...x...x...xx");
        pat ("Rhythm", "Trance Gate", "xxx.xxx.xxx.xxx.");
        pat ("Rhythm", "Rolling 16ths (accented)", "xoooxoooxoooxooo", true);
        pat ("Rhythm", "Syncopated 3+3+3+3+4", "x..x..x..x..x...");
        pat ("Rhythm", "Waltz 6 / 8", "x..x.x", false);
        pat ("Rhythm", "12 over 4/4 (acid techno)", "x.xxx.xx.xx.");

        // ---- Arpeggio levels (a full scale of 1.0 is one octave, route to Pitch unipolar with the amount at 100 %) ----
        auto arp = [&] (const char* name, std::vector<int> semis, int dir = -1)
        {
            const int n = (int) semis.size();
            add ("Arpeggio (semitones / 12)", name, juce::jmin (16, n), [semis] (int k) { return semis[(size_t) k] / 12.0f; }, dir, 0);
        };
        arp ("Minor Arp Up", { 0, 3, 7, 12, 0, 3, 7, 12, 0, 3, 7, 12, 0, 3, 7, 12 });
        arp ("Major Arp Up", { 0, 4, 7, 12, 0, 4, 7, 12, 0, 4, 7, 12, 0, 4, 7, 12 });
        arp ("Minor 7 Arp", { 0, 3, 7, 10, 12, 10, 7, 3, 0, 3, 7, 10, 12, 10, 7, 3 });
        arp ("Octaves", { 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12, 0, 12 });
        arp ("Octave + Fifth", { 0, 7, 12, 7, 0, 7, 12, 7, 0, 7, 12, 7, 0, 7, 12, 7 });
        arp ("Fifths Up", { 0, 7, 0, 7, 3, 10, 3, 10, 5, 12, 5, 12, 7, 12, 7, 12 });
        arp ("Pentatonic Run", { 0, 3, 5, 7, 10, 12, 10, 7, 5, 3, 0, 3, 5, 7, 10, 12 });
        arp ("Chromatic Run", { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 11, 10, 9 });
        arp ("Whole Tone", { 0, 2, 4, 6, 8, 10, 12, 10, 8, 6, 4, 2, 0, 2, 4, 6 });
        arp ("Phrygian Climb", { 0, 1, 3, 5, 7, 8, 10, 12, 10, 8, 7, 5, 3, 1, 0, 1 });
        arp ("Dorian Dance", { 0, 2, 3, 5, 7, 9, 10, 12, 10, 9, 7, 5, 3, 2, 0, 2 });
        arp ("Blues Lick", { 0, 3, 5, 6, 7, 10, 12, 10, 7, 6, 5, 3, 0, 3, 5, 3 });
        arp ("Berlin School 8", { 0, 7, 12, 7, 3, 10, 15, 10 });
        arp ("Berlin School 16", { 0, 7, 3, 12, 7, 10, 3, 15, 0, 7, 3, 12, 10, 7, 3, 0 });
        arp ("Trance Pluck", { 0, 12, 7, 12, 0, 12, 7, 12, 3, 15, 10, 15, 5, 17, 12, 17 }, -1);
        arp ("Minor Triad Down", { 12, 7, 3, 0, 12, 7, 3, 0, 10, 7, 3, 0, 10, 7, 3, 0 });
        arp ("Octave Jumps (Bass)", { 0, 0, 12, 0, 0, 12, 0, 10, 0, 0, 12, 0, 7, 0, 12, 10 });
        arp ("Root and Seventh", { 0, 0, 0, 10, 0, 0, 0, 10, 0, 0, 0, 10, 0, 0, 7, 10 });

        // ---- Modulation shapes (filter, volume, wobble) ----
        add ("Modulation", "Pumping (sidechain)", 16, [] (int k) { return (k % 4) / 3.0f * 0.9f + 0.1f; });
        add ("Modulation", "Pumping Fast", 8, [] (int k) { return (k % 2) ? 1.0f : 0.1f; });
        add ("Modulation", "Acid Cutoff Sweep", 16, [] (int k) { return 0.15f + 0.85f * (k / 15.0f) * (0.6f + 0.4f * ((k & 3) == 3 ? 1.0f : 0.5f)); });
        add ("Modulation", "Acid Accent Wave", 16, [=] (int k) { return 0.45f + 0.35f * std::sin (2 * pi * k / 16.0f) + ((k % 4) == 2 ? 0.2f : 0.0f); });
        add ("Modulation", "Wobble 1/4", 16, [=] (int k) { return 0.5f + 0.5f * std::sin (2 * pi * k / 4.0f); });
        add ("Modulation", "Wobble 1/8", 16, [=] (int k) { return 0.5f + 0.5f * std::sin (2 * pi * k / 8.0f); });
        add ("Modulation", "Build Up", 16, [] (int k) { return std::pow (k / 15.0f, 1.8f); });
        add ("Modulation", "Drop", 16, [] (int k) { return k < 12 ? 1.0f : (15 - k) / 4.0f; });
        add ("Modulation", "Stutter Ramp", 16, [] (int k) { return ((k % 2) ? 0.0f : 1.0f) * (0.3f + 0.7f * k / 15.0f); });
        add ("Modulation", "Breathing", 16, [=] (int k) { return 0.15f + 0.85f * std::pow (0.5f + 0.5f * std::sin (2 * pi * k / 16.0f - pi / 2), 1.5f); });
        add ("Modulation", "Gate Chop 3 / 16", 12, [] (int k) { return (k % 3) == 0 ? 1.0f : 0.0f; });
        add ("Modulation", "Slow Swell and Cut", 16, [] (int k) { return k < 12 ? k / 11.0f : 0.0f; });

        // step shapes of a few presets: ramps inside the steps make them glide / decay
        for (auto& p : L)
        {
            if (p.name == "Pumping (sidechain)" || p.name == "Pumping Fast") for (int k = 0; k < 16; ++k) p.shape[(size_t) k] = 2;   // ramp up inside each step
            if (p.name == "Dub Chop" || p.name == "Techno Kick Fill") for (int k = 0; k < 16; ++k) p.shape[(size_t) k] = 7;           // decay
        }
        return L;
    }
}
