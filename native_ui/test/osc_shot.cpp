// PRIVATE (osc worker): renders the OSC page standalone in its three source modes (+ the original full editor pages).
#include "../NjoEditor.h"
#include "../NjoMock.h"
#include <cmath>

static void save (juce::Component& c, const juce::File& f, float scale)
{
    auto img = c.createComponentSnapshot (c.getLocalBounds(), true, scale);
    juce::PNGImageFormat png;
    f.deleteFile();
    juce::FileOutputStream out (f);
    if (out.openedOk()) png.writeImageToStream (img, out);
}

struct Stage : juce::Component { void paint (juce::Graphics& g) override { g.fillAll (njo::theme::bg); } };

int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    juce::File dir (argc > 1 ? argv[1] : "shots");
    dir.createDirectory();
    float scale = argc > 2 ? (float) std::atof (argv[2]) : 1.0f;
    njo::MockBackend be;
    njo::Ctx ctx (be);
    njo::SoundMemory mem (ctx);
    auto pump = [] { juce::MessageManager::getInstance()->runDispatchLoopUntil (50); };

    auto P = [&] (int o, const char* k, float v) { ctx.set (njo::oscId (o, njo::oscKey (k)), v); };
    // a wavetable of 8 frames (2048 samples each) morphing sine -> saw
    std::vector<float> wt;
    for (int f = 0; f < 8; ++f)
        for (int i = 0; i < 2048; ++i)
        {
            float ph = (float) i / 2048.0f, a = (float) f / 7.0f;
            wt.push_back ((1 - a) * std::sin (6.2831853f * ph) + a * (2.0f * ph - 1.0f) * 0.8f);
        }
    mem.set (njo::SoundMemory::Wavetable, 0, "SINE-SAW", "", wt);
    // a sample: decaying noisy sine burst
    std::vector<float> sm;
    juce::Random rnd (5);
    for (int i = 0; i < 72000; ++i) { float t = (float) i / 48000.0f; sm.push_back (std::exp (-2.2f * t) * (0.8f * std::sin (6.2831853f * 220 * t) + 0.2f * (rnd.nextFloat() - 0.5f))); }
    mem.set (njo::SoundMemory::Sample, 1, "HIT", "", sm);

    P (0, "wpos", 0.55f); P (0, "w1m", 1); P (0, "w1a", 0.5f); P (0, "uvox", 3);
    P (1, "type", 1); P (1, "sstart", 0.2f); P (1, "sloop", 1);
    P (2, "type", 2); P (2, "tterr", 7);

    for (int o = 0; o < 3; ++o)
    {
        Stage st; st.setBounds (0, 0, 1086, 438);
        njo::OscPage page (ctx, mem, o);
        st.addAndMakeVisible (page); page.setBounds (0, 0, 1086, 438);
        pump();
        const char* names[] = { "osc1", "osc2", "osc3" };
        save (st, dir.getChildFile (juce::String (names[o]) + ".png"), scale);
    }
    // a filter variety: LP24 off, formant, comb
    {
        Stage st; st.setBounds (0, 0, 1086, 438);
        njo::OscPage page (ctx, mem, 3);
        st.addAndMakeVisible (page); page.setBounds (0, 0, 1086, 438);
        P (3, "ftype", 23); P (3, "fres", 0.6f); pump();
        save (st, dir.getChildFile ("osc_formant.png"), scale);
    }
    return 0;
}
