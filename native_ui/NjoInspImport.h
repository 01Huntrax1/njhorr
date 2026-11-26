// MIDI import of the Inspirator (Generator = Import): the file is read once into raw notes (track, channel, 96 ticks per quarter), then processed with options: track / channel
// choice, drum channel handling, start bar and length, quantise grid, voices (all / highest / lowest), octave shift, velocity treatment, lead-in trim and key detection
// (Krumhansl-Schmuckler).  Header only; tested by native_ui/test/insimport_test.cpp.
#pragma once
#include <juce_audio_basics/juce_audio_basics.h>
#include <juce_core/juce_core.h>
#include <algorithm>
#include <cmath>
#include <vector>

namespace njo::insimp
{
    // pairs the DSP takes: grid tick, length, pitch, velocity; bars 1 / 2 / 4 / 8
    struct Notes { std::vector<int> grid, len, pitch, vel; int bars = 1; };
    struct Raw { int track, channel, pitch, vel; double tick, len; };
    struct File
    {
        std::vector<Raw> notes; juce::StringArray trackNames; std::vector<int> trackNoteCounts; int numerator = 4, denominator = 4; juce::String error;
    };
    struct Options
    {
        int track = -1;        // -1 all tracks
        int drums = 0;         // channel 10: 0 include, 1 exclude, 2 only
        int startBar = 0;      // first bar taken from the file (0-based)
        int bars = 0;          // 0 auto (1 / 2 / 4 / 8 from the last note), else 1 / 2 / 4 / 8
        int quant = 6;         // ticks of the grid: 6 = 1/64 (almost off), 12 = 1/32, 24 = 1/16, 48 = 1/8, 96 = 1/4
        int voices = 0;        // 0 all, 1 highest note per onset, 2 lowest
        int octave = 0;        // -2 .. +2
        int velocity = 0;      // 0 as played, 1 flat (100), 2 compressed (halfway to 64)
        bool trimLead = false; // drop whole empty bars at the start
        bool detectKey = true; // set Key / Scale from the notes
    };
    struct KeyGuess { int key = 0; bool minor = false; double score = 0; };

    inline File readFile (const juce::File& f)
    {
        File out; juce::FileInputStream in (f); juce::MidiFile mf;
        if (! in.openedOk() || ! mf.readFrom (in)) { out.error = "not a MIDI file"; return out; }
        bool gotTs = false;
        const int tpq = mf.getTimeFormat(); if (tpq <= 0) { out.error = "SMPTE time base is not supported"; return out; }
        for (int t = 0; t < mf.getNumTracks(); ++t)
        {
            juce::MidiMessageSequence seq (*mf.getTrack (t)); seq.updateMatchedPairs();
            juce::String nm; int cnt = 0;
            for (int i = 0; i < seq.getNumEvents(); ++i)
            {
                auto* e = seq.getEventPointer (i); const auto& m = e->message;
                if (m.isTrackNameEvent() && nm.isEmpty()) nm = m.getTextFromTextMetaEvent();
                if (m.isTimeSignatureMetaEvent() && ! gotTs) { m.getTimeSignatureInfo (out.numerator, out.denominator); gotTs = true; }
                if (! m.isNoteOn() || e->noteOffObject == nullptr) continue;
                const double k = 96.0 / tpq;
                out.notes.push_back ({ t, m.getChannel(), m.getNoteNumber(), juce::jlimit (1, 127, (int) m.getVelocity()), m.getTimeStamp() * k, (e->noteOffObject->message.getTimeStamp() - m.getTimeStamp()) * k });
                ++cnt;
            }
            out.trackNames.add (nm.isEmpty() ? "Track " + juce::String (t + 1) : nm); out.trackNoteCounts.push_back (cnt);
        }
        if (out.notes.empty()) out.error = "no notes in the file";
        return out;
    }

    inline KeyGuess detectKey (const Notes& n)
    {
        static const double maj[12] = { 6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88 }, mnr[12] = { 6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17 };
        double h[12] = {}; for (size_t i = 0; i < n.pitch.size(); ++i) h[(n.pitch[i] % 12 + 12) % 12] += (double) juce::jmin (n.len[i], 96) * (0.5 + n.vel[i] / 254.0);
        KeyGuess best; best.score = -2;
        auto corr = [&] (const double* prof, int rot)
        {
            double mh = 0, mp = 0; for (int i = 0; i < 12; ++i) { mh += h[i]; mp += prof[i]; } mh /= 12; mp /= 12;
            double sxy = 0, sxx = 0, syy = 0; for (int i = 0; i < 12; ++i) { const double x = h[(i + rot) % 12] - mh, y = prof[i] - mp; sxy += x * y; sxx += x * x; syy += y * y; }
            return sxx > 0 && syy > 0 ? sxy / std::sqrt (sxx * syy) : 0.0;
        };
        for (int r = 0; r < 12; ++r)
        {
            const double a = corr (maj, r), b = corr (mnr, r);
            if (a > best.score) { best.score = a; best.key = r; best.minor = false; }
            if (b > best.score) { best.score = b; best.key = r; best.minor = true; }
        }
        return best;
    }

    // result of process(): the notes and how many the file had / the options let through
    struct Result { Notes notes; int inFile = 0, kept = 0; KeyGuess key; bool hasKey = false; };
    inline Result process (const File& f, const Options& o, int barTicks)
    {
        Result r; r.inFile = (int) f.notes.size(); barTicks = juce::jmax (6, barTicks);
        struct N { int g, l, p, v; }; std::vector<N> v;
        const int q = juce::jmax (1, o.quant);
        for (auto& n : f.notes)
        {
            if (o.track >= 0 && n.track != o.track) continue;
            const bool dr = n.channel == 10;
            if ((o.drums == 1 && dr) || (o.drums == 2 && ! dr)) continue;
            int g = (int) std::lround (n.tick / q) * q;
            int l = juce::jlimit (6, 1000, (int) std::lround (n.len)); if (q >= 24) l = juce::jmax (q / 2, (int) std::lround (n.len / 6.0) * 6);
            int p = juce::jlimit (0, 127, n.pitch + 12 * o.octave), vel = n.vel;
            if (o.velocity == 1) vel = 100; else if (o.velocity == 2) vel = juce::jlimit (1, 127, 64 + (vel - 64) / 2);
            v.push_back ({ g, l, p, vel });
        }
        std::stable_sort (v.begin(), v.end(), [] (const N& a, const N& b) { return a.g < b.g; });
        if (o.voices != 0)
        {
            std::vector<N> m;
            for (size_t i = 0; i < v.size();)
            {
                size_t j = i; N pick = v[i]; while (j < v.size() && v[j].g == v[i].g) { if ((o.voices == 1 && v[j].p > pick.p) || (o.voices == 2 && v[j].p < pick.p)) pick = v[j]; ++j; }
                m.push_back (pick); i = j;
            }
            v = m;
        }
        int shift = o.startBar * barTicks;
        if (o.trimLead && ! v.empty()) shift = juce::jmax (shift, (v.front().g / barTicks) * barTicks);
        for (auto& n : v) n.g -= shift;
        v.erase (std::remove_if (v.begin(), v.end(), [] (const N& n) { return n.g < 0; }), v.end());
        int last = 0; for (auto& n : v) last = juce::jmax (last, n.g);
        const int need = last / barTicks + 1;
        r.notes.bars = o.bars > 0 ? o.bars : (need <= 1 ? 1 : need <= 2 ? 2 : need <= 4 ? 4 : 8);
        for (auto& n : v) if (n.g < r.notes.bars * barTicks && (int) r.notes.grid.size() < 512) { r.notes.grid.push_back (n.g); r.notes.len.push_back (n.l); r.notes.pitch.push_back (n.p); r.notes.vel.push_back (n.v); }
        r.kept = (int) r.notes.grid.size();
        if (r.kept > 0 && o.detectKey) { r.key = detectKey (r.notes); r.hasKey = true; }
        return r;
    }
}
