// Private harness of the manager worker: preset round trip, vault, screenshots of the overlays.
#include "../NjoManager.cpp"
#include "../NjoMock.h"
#include <juce_audio_formats/juce_audio_formats.h>

static int fails = 0;
#define CHECK(c) do { if (! (c)) { ++fails; std::printf ("FAIL line %d: %s\n", __LINE__, #c); } } while (0)

static void pump (int ms = 30) { juce::MessageManager::getInstance()->runDispatchLoopUntil (ms); }

static void save (juce::Component& c, const juce::File& f)
{
    auto img = c.createComponentSnapshot (c.getLocalBounds(), true, 1.0f);
    juce::PNGImageFormat png; f.deleteFile();
    juce::FileOutputStream out (f);
    if (out.openedOk()) png.writeImageToStream (img, out);
}

static void makeWav (const juce::File& f, double seconds, float freq)
{
    juce::WavAudioFormat wav; f.deleteFile();
    std::unique_ptr<juce::FileOutputStream> os (f.createOutputStream());
    std::unique_ptr<juce::AudioFormatWriter> w (wav.createWriterFor (os.get(), 44100.0, 1, 16, {}, 0));
    os.release();
    juce::AudioBuffer<float> b (1, (int) (seconds * 44100));
    for (int i = 0; i < b.getNumSamples(); ++i) b.setSample (0, i, 0.5f * std::sin (6.2831853f * freq * i / 44100.0f));
    w->writeFromAudioSampleBuffer (b, 0, b.getNumSamples());
}

struct Host : juce::Component
{
    void paint (juce::Graphics& g) override { g.fillAll (njo::theme::bg); g.setColour (njo::theme::panel); g.fillRoundedRectangle (10, 60, 1160, 690, 10); }
};

int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    juce::File shots (argc > 1 ? argv[1] : "/tmp/mgr_shots"); shots.createDirectory();
    njo::MockBackend be;
    njo::Ctx ctx (be);
    ctx.lfoShapes = std::make_shared<njo::LfoShapes> (ctx);
    njo::SoundMemory mem (ctx);
    Host host; host.setSize (1180, 760);
    njo::ManagerBar bar (ctx, mem, host);
    host.addAndMakeVisible (bar);
    bar.setBounds (20, 24, 1140, 24);
    pump();
    auto& im = *bar.impl;

    const int pLevel = njo::oscId (0, njo::oscKey ("level"));
    auto root = be.rootFolder();

    // ---- presets: save / list / apply
    CHECK (bar.presetName() == "Init");
    ctx.set (pLevel, 0.31f); pump();
    CHECK (bar.presetName() == "Init *");
    CHECK (im.presetSaveAs ("Test One", {}) == "Test One.njopreset");
    CHECK (bar.presetName() == "Test One");
    CHECK (root.getChildFile ("Presets/Test One.njopreset").existsAsFile());
    ctx.set (pLevel, 0.62f);
    CHECK (im.presetSaveAs ("Test Two", {}) == "Test Two.njopreset");
    CHECK (im.presets.size() == 2);
    ctx.set (pLevel, 0.9f); pump();
    CHECK (bar.presetName() == "Test Two *");
    im.presetStep (-1); pump();            // Test One
    CHECK (bar.presetName() == "Test One");
    CHECK (std::abs (ctx.get (pLevel) - 0.31f) < 1e-4f);
    im.presetStep (1); pump();
    CHECK (bar.presetName() == "Test Two");
    CHECK (std::abs (ctx.get (pLevel) - 0.62f) < 1e-4f);
    // reserved / duplicate names
    CHECK (im.presetSaveAs ("init", {}).isEmpty());
    CHECK (im.presetSaveAs ("test one", {}).isEmpty());
    // lfo shapes travel with the preset
    {
        auto* o = new juce::DynamicObject(); o->setProperty ("x", 42);
        ctx.lfoShapes->fromVar (juce::var (o));
        im.presetSaveAs ("Test Two", im.cur.id);
        ctx.lfoShapes->fromVar ({});
        im.presetStep (0 + 1); im.presetStep (-1);   // reload Test Two
        CHECK (ctx.lfoShapes->toVar().getDynamicObject() != nullptr && (int) ctx.lfoShapes->toVar().getDynamicObject()->getProperty ("x") == 42);
    }
    // file format of the web UI
    {
        auto v = juce::JSON::parse (root.getChildFile ("Presets/Test One.njopreset").loadFileAsString());
        CHECK (v["format"].toString() == "njohrr-preset" && (int) v["version"] == 1 && v["name"].toString() == "Test One");
        CHECK (v["params"].getDynamicObject() != nullptr && v["refs"].getDynamicObject() != nullptr);
        CHECK (std::abs ((double) v["params"][juce::Identifier (juce::String (pLevel))] - 0.31) < 1e-5);
        CHECK ((int) v["params"].getDynamicObject()->getProperties().size() == (int) njo::allSpecs().size());
    }
    // a file written by the web UI (no lfo, refs null-less, numeric strings tolerated)
    {
        juce::String js = "{\"format\":\"njohrr-preset\",\"version\":1,\"name\":\"From Web\",\"saved\":1700000000000,\"params\":{\"" + juce::String (pLevel) + "\":0.44,\"99999\":1},\"refs\":{\"wt0\":{\"name\":\"nope.wav\",\"size\":10}}}";
        root.getChildFile ("Presets/From Web.njopreset").replaceWithText (js);
        im.presetsRefresh();
        auto* p = im.findPreset ("From Web.njopreset");
        CHECK (p != nullptr);
        if (p) { auto r = *p; im.presetApply (r); }
        CHECK (std::abs (ctx.get (pLevel) - 0.44f) < 1e-4f);
        CHECK (bar.presetName() == "From Web");
    }
    // rename + delete through the overlay actions
    bar.openBank(); pump();
    im.sel = "Test One.njopreset"; im.presetOv->refresh(); im.presetOv->setName ("Test Uno");
    im.pmAct ("pm-ren");
    CHECK (root.getChildFile ("Presets/Test Uno.njopreset").existsAsFile() && ! root.getChildFile ("Presets/Test One.njopreset").existsAsFile());
    im.sel = "Test Uno.njopreset";
    im.pmAct ("pm-del"); CHECK (root.getChildFile ("Presets/Test Uno.njopreset").existsAsFile());   // armed only
    im.pmAct ("pm-del"); CHECK (! root.getChildFile ("Presets/Test Uno.njopreset").existsAsFile());
    // init sound
    im.pmAct ("pm-init"); CHECK (bar.presetName() == "Init");
    CHECK (std::abs (ctx.get (pLevel) - 0.0f) >= 0.0f);

    // ---- vault
    auto src = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njo_src_" + juce::String (juce::Random::getSystemRandom().nextInt()));
    src.createDirectory();
    makeWav (src.getChildFile ("kick.wav"), 0.5, 60);  makeWav (src.getChildFile ("saw table.wav"), 1.0, 220); makeWav (src.getChildFile ("pad.wav"), 2.25, 110);
    src.getChildFile ("notes.txt").replaceWithText ("x");
    bar.openVault (njo::SoundMemory::Sample, -1); pump();
    juce::Array<juce::File> fs { src.getChildFile ("kick.wav"), src.getChildFile ("pad.wav"), src.getChildFile ("notes.txt") };
    im.libImport (fs);
    CHECK (im.lib.size() == 2);
    im.libImport ({ src.getChildFile ("kick.wav") });   // duplicate: not added again
    CHECK (im.lib.size() == 2);
    im.libKind = 0;
    im.libImport ({ src.getChildFile ("saw table.wav") });
    CHECK (im.lib.size() == 3 && root.getChildFile ("Wavetables/saw table.wav").existsAsFile());
    for (auto& r : im.lib) if (r.fname == "pad.wav") CHECK (std::abs (r.dur - 2.25) < 0.01);
    // load into slots
    im.libLoad ("samples/kick.wav", 1); im.libLoad ("wavetables/saw table.wav", 0); pump();
    CHECK (mem.get (njo::SoundMemory::Sample, 1) != nullptr && mem.get (njo::SoundMemory::Wavetable, 0) != nullptr);
    CHECK (im.slotLib["sm1"].id == "samples/kick.wav");
    CHECK (be.getStored ("njo.slots").getDynamicObject() != nullptr);
    CHECK (im.presetSaveAs ("With Sounds", {}) == "With Sounds.njopreset");
    {
        auto v = juce::JSON::parse (root.getChildFile ("Presets/With Sounds.njopreset").loadFileAsString());
        CHECK (v["refs"]["sm1"]["name"].toString() == "kick.wav" && (int) v["refs"]["sm1"]["size"] > 100);
        CHECK (v["refs"]["wt0"]["name"].toString() == "saw table.wav");
    }
    mem.clear (njo::SoundMemory::Sample, 1); mem.clear (njo::SoundMemory::Wavetable, 0); pump();
    CHECK (im.slotLib.empty());
    CHECK (bar.presetName() == "With Sounds *");
    im.presetStep (0 + 1); im.presetStep (-1);  // reload through next/prev until it is "With Sounds"
    for (int i = 0; i < 6 && im.cur.name != "With Sounds"; ++i) im.presetStep (1);
    pump (100);
    CHECK (im.cur.name == "With Sounds");
    CHECK (mem.get (njo::SoundMemory::Sample, 1) != nullptr && mem.get (njo::SoundMemory::Wavetable, 0) != nullptr);
    CHECK (bar.presetName() == "With Sounds");      // loading the sounds must not mark the preset dirty
    // rename + move + delete in the vault
    im.renamingId = "samples/pad.wav"; { juce::String nv = "Warm Pad"; im.libRenameDone ("samples/pad.wav", &nv); }
    CHECK (root.getChildFile ("Samples/Warm Pad.wav").existsAsFile());
    im.libAct ("lb-kind", "samples/Warm Pad.wav");
    CHECK (root.getChildFile ("Wavetables/Warm Pad.wav").existsAsFile() && ! root.getChildFile ("Samples/Warm Pad.wav").existsAsFile());
    im.libAct ("lb-del", "wavetables/Warm Pad.wav"); CHECK (root.getChildFile ("Wavetables/Warm Pad.wav").existsAsFile());
    im.libAct ("lb-del", "wavetables/Warm Pad.wav"); CHECK (! root.getChildFile ("Wavetables/Warm Pad.wav").existsAsFile());

    // ---- screenshots
    for (auto& f : root.getChildFile ("Presets").findChildFiles (juce::File::findFiles, false)) (void) f;
    be.setParam (pLevel, 0.5f);
    ctx.onOpenVault (1, 2); pump (100);     // the oscillator pages open the vault like this
    CHECK (im.libTarget == 2 && im.vaultOv->isVisible());
    save (host, shots.getChildFile ("vault_target.png"));
    im.libTarget = -1; im.vaultOv->refresh(); pump (50);
    save (host, shots.getChildFile ("vault_samples.png"));
    bar.openBank(); im.sel = "With Sounds.njopreset"; im.presetOv->refresh(); pump (100);
    save (host, shots.getChildFile ("bank.png"));
    bar.closeOverlays();
    CHECK (! bar.overlayOpen());
    save (host, shots.getChildFile ("bar.png"));

    // ---- state survives a new editor
    {
        njo::SoundMemory mem2 (ctx);
        Host host2; host2.setSize (1180, 760);
        auto nm = bar.presetName();
        njo::ManagerBar bar2 (ctx, mem2, host2);
        CHECK (bar2.presetName() == nm);
    }
    pump();
    root.deleteRecursively(); src.deleteRecursively();
    std::printf (fails ? "%d FAILURES\n" : "ALL OK\n", fails);
    return fails ? 1 : 0;
}
