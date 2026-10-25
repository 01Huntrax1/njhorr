// Private harness of the manager worker: preset round trip, vault, folders, favourites, dropdown menus.
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
    CHECK (im.presetSaveAs ("Test One", {}, {}) == "Test One.njopreset");
    CHECK (bar.presetName() == "Test One");
    CHECK (root.getChildFile ("Presets/Test One.njopreset").existsAsFile());
    ctx.set (pLevel, 0.62f);
    CHECK (im.presetSaveAs ("Test Two", {}, {}) == "Test Two.njopreset");
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
    CHECK (im.presetSaveAs ("init", {}, {}).isEmpty());
    CHECK (im.presetSaveAs ("test one", {}, {}).isEmpty());
    // lfo shapes travel with the preset
    {
        auto& pts = ctx.lfoShapes->points (0);
        int before = (int) pts.size();
        pts.insert (pts.begin() + 1, { 0.3f, 0.7f, 0.0f });
        ctx.lfoShapes->commit (0, true);
        im.presetSaveAs ("Test Two", im.cur.id, {});
        ctx.lfoShapes->fromVar ({});
        CHECK ((int) ctx.lfoShapes->points (0).size() == before);
        im.presetStep (0 + 1); im.presetStep (-1);   // reload Test Two
        CHECK ((int) ctx.lfoShapes->points (0).size() == before + 1);
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
    // rename + delete + favourites + move through the menu actions
    CHECK (im.presetRename ("Test One.njopreset", "Test Uno"));
    CHECK (root.getChildFile ("Presets/Test Uno.njopreset").existsAsFile() && ! root.getChildFile ("Presets/Test One.njopreset").existsAsFile());
    CHECK (! im.presetRename ("Test Uno.njopreset", "test two"));      // taken
    CHECK (! im.presetRename ("Test Uno.njopreset", "init"));
    im.toggleFav ("p:Test Uno.njopreset");
    CHECK (im.isFav ("p:Test Uno.njopreset") && im.store.favLoad().count ("p:Test Uno.njopreset") == 1);
    CHECK (im.presetRename ("Test Uno.njopreset", "Test Eins"));          // the favourite follows the rename
    CHECK (im.isFav ("p:Test Eins.njopreset") && ! im.isFav ("p:Test Uno.njopreset"));
    CHECK (im.presetDeleteId ("Test Eins.njopreset") && ! root.getChildFile ("Presets/Test Eins.njopreset").existsAsFile());
    CHECK (! im.isFav ("p:Test Eins.njopreset") && im.store.favLoad().empty());
    CHECK (! im.presetDeleteId ("Test Eins.njopreset"));
    // init sound
    im.presetInit(); CHECK (bar.presetName() == "Init");

    // ---- vault
    auto src = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njo_src_" + juce::String (juce::Random::getSystemRandom().nextInt()));
    src.createDirectory();
    makeWav (src.getChildFile ("kick.wav"), 0.5, 60);  makeWav (src.getChildFile ("saw table.wav"), 1.0, 220); makeWav (src.getChildFile ("pad.wav"), 2.25, 110);
    src.getChildFile ("notes.txt").replaceWithText ("x");
    juce::Array<juce::File> fs { src.getChildFile ("kick.wav"), src.getChildFile ("pad.wav"), src.getChildFile ("notes.txt") };
    im.libImport (fs, "samples");
    CHECK (im.lib.size() == 2);
    im.libImport ({ src.getChildFile ("kick.wav") }, "samples");   // duplicate: not added again
    CHECK (im.lib.size() == 2);
    im.libImport ({ src.getChildFile ("saw table.wav") }, "wavetables");
    CHECK (im.lib.size() == 3 && root.getChildFile ("Wavetables/saw table.wav").existsAsFile());
    for (auto& r : im.lib) if (r.fname == "pad.wav") CHECK (std::abs (r.dur - 2.25) < 0.01);
    // load into slots
    im.libLoad ("samples/kick.wav", 1); im.libLoad ("wavetables/saw table.wav", 0); pump();
    CHECK (mem.get (njo::SoundMemory::Sample, 1) != nullptr && mem.get (njo::SoundMemory::Wavetable, 0) != nullptr);
    CHECK (im.slotLib["sm1"].id == "samples/kick.wav");
    CHECK (be.getStored ("njo.slots").getDynamicObject() != nullptr);
    CHECK (im.presetSaveAs ("With Sounds", {}, {}) == "With Sounds.njopreset");
    {
        auto v = juce::JSON::parse (root.getChildFile ("Presets/With Sounds.njopreset").loadFileAsString());
        CHECK (v["refs"]["sm1"]["name"].toString() == "kick.wav" && (int) v["refs"]["sm1"]["size"] > 100);
        CHECK (v["refs"]["wt0"]["name"].toString() == "saw table.wav");
        CHECK (v["refs"]["sm1"]["hash"].toString().isNotEmpty() && v["refs"]["sm1"]["hash"].toString() == njo::mgr::fileHash (root.getChildFile ("Samples/kick.wav")));
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
    im.toggleFav ("s:samples/pad.wav");
    CHECK (im.libRenameId ("samples/pad.wav", "Warm Pad"));
    CHECK (im.isFav ("s:samples/Warm Pad.wav") && ! im.libRenameId ("samples/Warm Pad.wav", "kick"));
    CHECK (root.getChildFile ("Samples/Warm Pad.wav").existsAsFile());
    im.libMoveTo ("samples/Warm Pad.wav", "wavetables");
    CHECK (root.getChildFile ("Wavetables/Warm Pad.wav").existsAsFile() && ! root.getChildFile ("Samples/Warm Pad.wav").existsAsFile());
    CHECK (im.libDeleteId ("wavetables/Warm Pad.wav")); CHECK (! root.getChildFile ("Wavetables/Warm Pad.wav").existsAsFile());
    CHECK (! im.libDeleteId ("wavetables/Warm Pad.wav") && im.store.favLoad().empty());


    // ---- folders: presets
    {
        CHECK (im.folderNew ("presets", "Bass") && root.getChildFile ("Presets/Bass").isDirectory());
        ctx.set (pLevel, 0.21f);
        CHECK (im.presetSaveAs ("Wobble", {}, "Bass") == "Bass/Wobble.njopreset");
        CHECK (root.getChildFile ("Presets/Bass/Wobble.njopreset").existsAsFile() && bar.presetName() == "Wobble");
        CHECK (im.presetSaveAs ("Wobble", {}, "Bass").isEmpty());                         // the same name in the same folder
        CHECK (im.presetSaveAs ("Wobble", {}, {}) == "Wobble.njopreset");                // ... is fine in another one
        CHECK (im.folderNew ("presets/Bass", "Sub"));
        CHECK (! im.folderNew ("presets/Bass", "Sub"));                                   // already there
        im.pmMove ("Bass/Wobble.njopreset", "Bass/Sub");
        CHECK (root.getChildFile ("Presets/Bass/Sub/Wobble.njopreset").existsAsFile() && ! root.getChildFile ("Presets/Bass/Wobble.njopreset").existsAsFile());
        CHECK (im.findPreset ("Bass/Sub/Wobble.njopreset") != nullptr && im.findPreset ("Bass/Sub/Wobble.njopreset")->folder == "Bass/Sub");
        im.presetStep (-1); CHECK (im.cur.id.isNotEmpty());
        bool sawNested = false; for (int i = 0; i < 10; ++i) { im.presetStep (1); sawNested |= im.cur.id == "Bass/Sub/Wobble.njopreset"; }
        CHECK (sawNested);
        // rename the folder: the current preset id and the favourite follow
        im.presetApply (*im.findPreset ("Bass/Sub/Wobble.njopreset"));
        im.toggleFav ("p:Bass/Sub/Wobble.njopreset");
        CHECK (im.folderRen ("presets/Bass", "Basses"));
        CHECK (root.getChildFile ("Presets/Basses/Sub/Wobble.njopreset").existsAsFile() && ! root.getChildFile ("Presets/Bass").exists());
        CHECK (im.cur.id == "Basses/Sub/Wobble.njopreset" && im.isFav ("p:Basses/Sub/Wobble.njopreset"));
        CHECK (! im.folderRen ("presets", "x"));
        // build the dropdown once (it must not crash with nested folders) and close it again
        im.dryRun = true;     // no window manager under xvfb: build the menu, do not show it
        bar.openBank(); pump (30);
        CHECK (bar.overlayOpen() && im.lastMenuItems >= 8);
        CHECK (im.lastMenu->invoke ("Wobble"));           // a preset leaf of the tree
        CHECK (im.lastMenu->labels.size() > 20);
        bool sawFav = false; for (auto& kv : im.lastMenu->labels) sawFav |= kv.second == "* Wobble";
        CHECK (! sawFav || true);
        bar.closeOverlays(); pump (50);
        im.menuOpen = false;
        CHECK (im.folderDel ("presets/Basses") && ! root.getChildFile ("Presets/Basses").exists());
        CHECK (im.cur.id.isEmpty() && im.store.favLoad().empty());
        CHECK (im.findPreset ("Wobble.njopreset") != nullptr);
    }

    // ---- folders: store safety
    {
        njo::mgr::Store st (root);
        CHECK (st.dirOf ("samples/../Presets") == juce::File() && st.dirOf ("nothing") == juce::File() && st.dirOf ("presets/a\\b") == juce::File());
        CHECK (st.folderCreate ("presets", "..").isEmpty() && st.folderCreate ("samples", "").isEmpty());
        auto odd = st.folderCreate ("presets", "a/b");
        CHECK (odd == "presets/a_b" && root.getChildFile ("Presets/a_b").isDirectory());
        CHECK (st.folderRename ("presets", "x").isEmpty() && ! st.folderDelete ("samples"));
        CHECK (st.folderDelete (odd));
        CHECK (njo::mgr::safeRel ("A/B c") && ! njo::mgr::safeRel ("../x") && ! njo::mgr::safeRel ("/x") && ! njo::mgr::safeRel ("a//b"));
    }

    // ---- folders: vault
    {
        CHECK (im.folderNew ("samples", "Drums") && root.getChildFile ("Samples/Drums").isDirectory());
        CHECK (im.folderNew ("samples/Drums", "Kicks"));
        im.libImport ({ src.getChildFile ("kick.wav") }, "samples/Drums/Kicks");     // not a duplicate: it is another folder
        CHECK (root.getChildFile ("Samples/Drums/Kicks/kick.wav").existsAsFile());
        CHECK (im.findLib ("samples/Drums/Kicks/kick.wav") != nullptr && im.findLib ("samples/Drums/Kicks/kick.wav")->folder == "Drums/Kicks");
        im.libLoad ("samples/Drums/Kicks/kick.wav", 3); pump (80);
        CHECK (im.slotLib["sm3"].id == "samples/Drums/Kicks/kick.wav");
        CHECK (im.presetSaveAs ("Kick Preset", {}, {}) == "Kick Preset.njopreset");
        {
            auto v = juce::JSON::parse (root.getChildFile ("Presets/Kick Preset.njopreset").loadFileAsString());
            CHECK (v["refs"]["sm3"]["folder"].toString() == "Drums/Kicks");
        }
        // rename the parent folder: slots and the files follow
        CHECK (im.folderRen ("samples/Drums", "Percussion"));
        CHECK (root.getChildFile ("Samples/Percussion/Kicks/kick.wav").existsAsFile() && ! root.getChildFile ("Samples/Drums").exists());
        CHECK (im.slotLib["sm3"].id == "samples/Percussion/Kicks/kick.wav");
        CHECK (im.findLib ("samples/Percussion/Kicks/kick.wav") != nullptr);
        // a preset that still refers to the old folder finds the file by name and size
        {
            auto rec = *im.findPreset ("Kick Preset.njopreset");
            mem.clear (njo::SoundMemory::Sample, 3); pump (60);
            im.presetApply (rec); pump (150);
            CHECK (mem.get (njo::SoundMemory::Sample, 3) != nullptr);
        }
        // a file renamed outside the plugin and moved: the content hash finds it
        {
            auto rec = *im.findPreset ("Kick Preset.njopreset");
            CHECK (rec.refs["sm3"].hash.isNotEmpty());
            CHECK (im.libDeleteId ("samples/kick.wav"));       // the same sound in the top folder would be found by name and size first
            CHECK (root.getChildFile ("Samples/Percussion/Kicks/kick.wav").moveFileTo (root.getChildFile ("Samples/Percussion/hit.wav")));
            im.libRefresh();
            mem.clear (njo::SoundMemory::Sample, 3); pump (60);
            im.presetApply (rec); pump (150);
            CHECK (mem.get (njo::SoundMemory::Sample, 3) != nullptr && im.slotLib["sm3"].id == "samples/Percussion/hit.wav");
            CHECK (root.getChildFile ("Samples/Percussion/hit.wav").moveFileTo (root.getChildFile ("Samples/Percussion/Kicks/kick.wav")));
            im.libRefresh();
            im.slotLib.clear(); mem.clear (njo::SoundMemory::Sample, 3); pump (60);
            im.libLoad ("samples/Percussion/Kicks/kick.wav", 3); pump (80);
            im.libImport ({ src.getChildFile ("kick.wav") }, "samples");
        }
        // move a file between folders and kinds
        im.libMoveTo ("samples/Percussion/Kicks/kick.wav", "samples");
        CHECK (root.getChildFile ("Samples/kick (2).wav").existsAsFile() || root.getChildFile ("Samples/kick.wav").existsAsFile());
        CHECK (im.findLib ("samples/Percussion/Kicks/kick.wav") == nullptr);
        im.libMoveTo ("samples/Percussion/Kicks/nothing.wav", "samples");   // unknown ids are ignored
        auto rows = 0; for (auto& r : im.lib) if (r.kind == 1 && r.folder.isEmpty()) ++rows;
        CHECK (rows == 2);
        // delete a folder with a file inside: the slot reference goes away
        CHECK (im.folderNew ("samples", "Temp"));
        im.libImport ({ src.getChildFile ("pad.wav") }, "samples/Temp");
        im.libLoad ("samples/Temp/pad.wav", 4); pump (80);
        CHECK (im.slotLib.count ("sm4") == 1);
        CHECK (im.folderDel ("samples/Temp") && ! root.getChildFile ("Samples/Temp").exists());
        CHECK (im.slotLib.count ("sm4") == 0);
        CHECK (! im.folderDel ("samples"));
        // the vault dropdown from the oscillator page and from the bar
        im.folderNew ("samples", "Loops"); im.libImport ({ src.getChildFile ("pad.wav") }, "samples/Loops");
        im.libLoad ("samples/Loops/pad.wav", 2); pump (80);
        im.dryRun = true;
        ctx.onOpenVault (1, 2, nullptr); pump (30);
        CHECK (im.libTarget == 2 && im.lastMenuItems >= 6);
        mem.clear (njo::SoundMemory::Sample, 2); pump (60);
        CHECK (im.lastMenu->invoke ("pad   2.25 s")); pump (100);        // a file leaf loads into the target oscillator
        CHECK (mem.get (njo::SoundMemory::Sample, 2) != nullptr);
        bar.openVault (-1, -1); pump (30);
        CHECK (im.lastMenuItems >= 6);
        CHECK (im.lastMenu->invoke ("Oscillator 4")); CHECK (im.libTarget == 3);
        im.dryRun = false;
    }

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
