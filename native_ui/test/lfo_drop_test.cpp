// LFO wavetable import by file drop and the ENV / LFO views of the strip.  lfo_drop_test <shot folder>
#include "../NjoMock.h"
#include "../NjoPages.h"
#include "../NjoLfoTable.h"
#include <juce_audio_formats/juce_audio_formats.h>
#include <cstdio>

static int fails = 0;
#define CHECK(c) do { if (! (c)) { ++fails; std::printf ("FAIL line %d: %s\n", __LINE__, #c); } } while (0)
static void save (juce::Component& c, const juce::File& f) { auto img = c.createComponentSnapshot (c.getLocalBounds(), true, 1.0f); juce::PNGImageFormat png; f.deleteFile(); juce::FileOutputStream out (f); if (out.openedOk()) png.writeImageToStream (img, out); }
struct Stage : juce::Component { void paint (juce::Graphics& g) override { g.fillAll (njo::theme::bg); } };
static juce::File makeWav (const juce::File& dir, const juce::String& name, int n, int frameLen, bool perFrameHarmonic)
{
    auto f = dir.getChildFile (name); f.deleteFile();
    juce::WavAudioFormat wav; std::unique_ptr<juce::FileOutputStream> os (f.createOutputStream());
    std::unique_ptr<juce::AudioFormatWriter> w (wav.createWriterFor (os.get(), 44100.0, 1, 16, {}, 0)); os.release();
    juce::AudioBuffer<float> b (1, n);
    for (int i = 0; i < n; ++i) { int fr = i / frameLen; float ph = (float) (i % frameLen) / frameLen; b.setSample (0, i, 0.5f * std::sin (6.2831853f * ph * (perFrameHarmonic ? fr + 1 : 1))); }
    w->writeFromAudioSampleBuffer (b, 0, n);
    return f;
}
int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    juce::File dir (argc > 1 ? argv[1] : "/tmp/lfo_drop"); dir.createDirectory();
    njo::MockBackend be; njo::Ctx ctx (be);
    auto pump = [] { juce::MessageManager::getInstance()->runDispatchLoopUntil (50); };
    njo::LfoTables T (ctx); juce::String msg;

    // 4 frames of 2048 samples, frame k = harmonic k + 1
    CHECK (T.importFile (0, makeWav (dir, "wt4.wav", 4 * 2048, 2048, true), msg));
    CHECK (T.count (0) == 4);
    float peak = 0, err = 0;
    for (int k = 0; k < 4; ++k) for (int i = 0; i < 256; ++i) { float e = std::sin (6.2831853f * (float) i / 256 * (k + 1)); peak = juce::jmax (peak, std::abs (T.frame (0, k)[(size_t) i])); err = juce::jmax (err, std::abs (T.frame (0, k)[(size_t) i] - e)); }
    CHECK (std::abs (peak - 1.0f) < 1e-3f);   // normalised
    CHECK (err < 0.03f);
    std::printf ("4 frames: %s, max error %.4f\n", msg.toRawUTF8(), err);
    // 100 frames of 256 -> 16 frames, evenly spread
    CHECK (T.importFile (1, makeWav (dir, "wt100.wav", 100 * 256, 256, true), msg)); CHECK (T.count (1) == 16);
    // one cycle of 600 samples
    CHECK (T.importFile (2, makeWav (dir, "cycle.wav", 600, 600, false), msg)); CHECK (T.count (2) == 1);
    float e2 = 0; for (int i = 0; i < 256; ++i) e2 = juce::jmax (e2, std::abs (T.frame (2, 0)[(size_t) i] - std::sin (6.2831853f * (float) i / 256)));
    CHECK (e2 < 0.03f);
    // not an audio file
    auto bad = dir.getChildFile ("bad.wav"); bad.replaceWithText ("hello");
    CHECK (! T.importFile (3, bad, msg)); std::printf ("bad file: %s\n", msg.toRawUTF8());

    // drop on the editor
    { Stage st; st.setBounds (0, 0, 1086, 200); njo::ModEditors ed (ctx); st.addAndMakeVisible (ed); ed.setBounds (0, 0, 1086, 200);
      ed.setView (1); pump(); CHECK (! ed.isInterestedInFileDrag (juce::StringArray (dir.getChildFile ("wt4.wav").getFullPathName())));   // ENV view: no LFO to drop on
      save (st, dir.getChildFile ("strip_env.png"));
      ed.setView (2); pump(); CHECK (ed.isInterestedInFileDrag (juce::StringArray (dir.getChildFile ("wt4.wav").getFullPathName())));
      ctx.selectedLfo = 3; ctx.set (njo::lfoWaveParam (3), 0);
      ed.fileDragEnter (juce::StringArray (dir.getChildFile ("wt4.wav").getFullPathName()), 200, 80); pump(); save (st, dir.getChildFile ("strip_lfo_drop.png"));
      ed.filesDropped (juce::StringArray (dir.getChildFile ("wt4.wav").getFullPathName()), 200, 80); pump();
      CHECK (juce::roundToInt (ctx.get (njo::lfoWaveParam (3))) == njo::LFO_TABLE);
      CHECK (ctx.lfoTables && ctx.lfoTables->count (3) == 4);
      save (st, dir.getChildFile ("strip_lfo.png")); }
    { Stage st; st.setBounds (0, 0, 1086, 438); njo::ModEditors ed (ctx); st.addAndMakeVisible (ed); ed.setBounds (0, 0, 1086, 438); pump(); save (st, dir.getChildFile ("full.png")); }
    std::printf (fails ? "%d FAILURES\n" : "ALL OK\n", fails);
    return fails ? 1 : 0;
}
