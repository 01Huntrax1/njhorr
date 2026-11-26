#include "../NjoInspImport.h"
#include <cstdio>
static int fails = 0;
#define CHECK(c) do { if (! (c)) { std::printf ("FAIL line %d: %s\n", __LINE__, #c); ++fails; } } while (0)
int main()
{
    using namespace njo::insimp;
    // a two-track file: track 0 = melody in D minor (channel 1), track 1 = drums (channel 10), 96 ticks per quarter, 3 bars of 4/4 (a note in bar 3)
    juce::MidiFile mf; mf.setTicksPerQuarterNote (96);
    juce::MidiMessageSequence a, d;
    a.addEvent (juce::MidiMessage::timeSignatureMetaEvent (3, 4)); a.addEvent (juce::MidiMessage::textMetaEvent (3, "Lead"));
    const int mel[] = { 62, 64, 65, 67, 69, 65, 62, 69 };   // D minor scale fragments
    for (int i = 0; i < 8; ++i) { a.addEvent (juce::MidiMessage::noteOn (1, mel[i], (juce::uint8) (80 + i)), 96.0 * i + 5); a.addEvent (juce::MidiMessage::noteOff (1, mel[i]), 96.0 * i + 90); }
    a.addEvent (juce::MidiMessage::noteOn (1, 74, (juce::uint8) 100), 96.0 * 8); a.addEvent (juce::MidiMessage::noteOff (1, 74), 96.0 * 8 + 90);   // bar 3
    a.addEvent (juce::MidiMessage::noteOn (1, 50, (juce::uint8) 90), 96.0 * 8); a.addEvent (juce::MidiMessage::noteOff (1, 50), 96.0 * 8 + 90);   // a lower note at the same onset
    for (int i = 0; i < 4; ++i) { d.addEvent (juce::MidiMessage::noteOn (10, 36, (juce::uint8) 110), 96.0 * i); d.addEvent (juce::MidiMessage::noteOff (10, 36), 96.0 * i + 20); }
    mf.addTrack (a); mf.addTrack (d);
    auto file = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njo_import_test_" + juce::String (juce::Random::getSystemRandom().nextInt()) + ".mid");
    { juce::FileOutputStream o (file); o.setPosition (0); o.truncate(); CHECK (mf.writeTo (o)); }
    auto f = readFile (file); file.deleteFile();
    CHECK (f.error.isEmpty() && f.notes.size() == 14 && f.trackNames.size() == 2 && f.trackNames[0] == "Lead" && f.trackNoteCounts[0] == 10 && f.trackNoteCounts[1] == 4);
    CHECK (f.numerator == 3 && f.denominator == 4);
    Options o; o.detectKey = true;
    auto all = process (f, o, 384);   // 4/4 bars of 384 ticks
    CHECK (all.inFile == 14 && all.kept == 14 && all.notes.bars == 4);
    // quantise: 5 ticks late -> 1/16 grid puts it on the beat
    Options q; q.quant = 24; auto rq = process (f, q, 384); CHECK (rq.notes.grid[0] == 0 && rq.notes.grid[1] % 24 == 0);
    // only the melody track, drums excluded / only
    Options t; t.track = 0; CHECK (process (f, t, 384).kept == 10);
    Options ex; ex.drums = 1; CHECK (process (f, ex, 384).kept == 10);
    Options on; on.drums = 2; CHECK (process (f, on, 384).kept == 4);
    // highest / lowest voice at the shared onset
    Options hi; hi.track = 0; hi.voices = 1; auto rh = process (f, hi, 384); CHECK (rh.kept == 9);
    bool has74 = false, has50 = false; for (int p : rh.notes.pitch) { has74 = has74 || p == 74; has50 = has50 || p == 50; } CHECK (has74 && ! has50);
    Options lo; lo.track = 0; lo.voices = 2; auto rl = process (f, lo, 384); bool l50 = false, l74 = false; for (int p : rl.notes.pitch) { l50 = l50 || p == 50; l74 = l74 || p == 74; } CHECK (l50 && ! l74);
    // octave and velocity
    Options oc; oc.track = 0; oc.octave = 1; oc.velocity = 1; auto ro = process (f, oc, 384); CHECK (ro.notes.pitch[0] == 74 && ro.notes.vel[0] == 100);
    // start bar / length / trim
    Options sb; sb.track = 0; sb.startBar = 2; auto rs = process (f, sb, 384); CHECK (rs.kept == 2 && rs.notes.bars == 1 && rs.notes.grid[0] == 0);
    Options tr; tr.track = 0; tr.trimLead = true; auto rt = process (f, tr, 384); CHECK (rt.kept == 10 && rt.notes.grid[0] == 6);
    Options fl; fl.track = 0; fl.bars = 1; CHECK (process (f, fl, 384).kept < 10);
    // key detection: D minor (the notes are the D natural minor scale)
    auto k = process (f, t, 384); CHECK (k.hasKey && ((k.key.key == 2 && k.key.minor) || (k.key.key == 5 && ! k.key.minor)));
    Options nk; nk.detectKey = false; CHECK (! process (f, nk, 384).hasKey);
    std::printf (fails ? "FAILED\n" : "ALL OK\n"); return fails ? 1 : 0;
}
