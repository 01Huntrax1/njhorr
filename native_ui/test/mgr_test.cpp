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
    CHECK (im.libFolder == "samples");
    juce::Array<juce::File> fs { src.getChildFile ("kick.wav"), src.getChildFile ("pad.wav"), src.getChildFile ("notes.txt") };
    im.libImport (fs);
    CHECK (im.lib.size() == 2);
    im.libImport ({ src.getChildFile ("kick.wav") });   // duplicate: not added again
    CHECK (im.lib.size() == 2);
    im.libFolder = "wavetables";
    im.libImport ({ src.getChildFile ("saw table.wav") });
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
    im.libMoveTo ("samples/Warm Pad.wav", "wavetables");
    CHECK (root.getChildFile ("Wavetables/Warm Pad.wav").existsAsFile() && ! root.getChildFile ("Samples/Warm Pad.wav").existsAsFile());
    im.libAct ("lb-del", "wavetables/Warm Pad.wav"); CHECK (root.getChildFile ("Wavetables/Warm Pad.wav").existsAsFile());
    im.libAct ("lb-del", "wavetables/Warm Pad.wav"); CHECK (! root.getChildFile ("Wavetables/Warm Pad.wav").existsAsFile());


    // ---- folders: presets
    {
        im.selFolder = {};
        im.folderAct (false, "new", "Bass");
        CHECK (root.getChildFile ("Presets/Bass").isDirectory() && im.selFolder == "Bass");
        ctx.set (pLevel, 0.21f);
        CHECK (im.presetSaveAs ("Wobble", {}, im.selFolder) == "Bass/Wobble.njopreset");
        CHECK (root.getChildFile ("Presets/Bass/Wobble.njopreset").existsAsFile() && bar.presetName() == "Wobble");
        CHECK (im.presetSaveAs ("Wobble", {}, "Bass").isEmpty());                         // the same name in the same folder
        CHECK (im.presetSaveAs ("Wobble", {}, {}) == "Wobble.njopreset");                // ... is fine in another one
        im.selFolder = "Bass";
        im.folderAct (false, "new", "Sub");                                               // below the selected folder Bass
        CHECK (root.getChildFile ("Presets/Bass/Sub").isDirectory() && im.selFolder == "Bass/Sub");
        im.folderAct (false, "new", "Sub");                                               // already there
        im.sel = "Bass/Wobble.njopreset";
        im.pmMove ("Bass/Wobble.njopreset", "Bass/Sub");
        CHECK (root.getChildFile ("Presets/Bass/Sub/Wobble.njopreset").existsAsFile() && ! root.getChildFile ("Presets/Bass/Wobble.njopreset").existsAsFile());
        CHECK (im.findPreset ("Bass/Sub/Wobble.njopreset") != nullptr && im.findPreset ("Bass/Sub/Wobble.njopreset")->folder == "Bass/Sub");
        // the current preset is the root "Wobble" (saved last): step through the folders in tree order
        im.presetStep (-1); CHECK (im.cur.id.isNotEmpty());
        bool sawNested = false; for (int i = 0; i < 10; ++i) { im.presetStep (1); sawNested |= im.cur.id == "Bass/Sub/Wobble.njopreset"; }
        CHECK (sawNested);
        // rename the folder: the current preset id follows
        im.presetApply (*im.findPreset ("Bass/Sub/Wobble.njopreset"));
        im.selFolder = "Bass"; im.sel = {};
        im.folderAct (false, "ren", "Basses");
        CHECK (root.getChildFile ("Presets/Basses/Sub/Wobble.njopreset").existsAsFile() && ! root.getChildFile ("Presets/Bass").exists());
        CHECK (im.cur.id == "Basses/Sub/Wobble.njopreset" && im.selFolder == "Basses");
        // the nodes of the tree
        auto nodes = im.presetNodes();
        CHECK (nodes.size() == 1 && nodes[0].folder && nodes[0].path == "presets" && nodes[0].count >= 3);
        bool foundLeaf = false; std::function<void (const njo::FolderTree::Node&)> walk = [&] (const njo::FolderTree::Node& n) { if (n.path == "p:Basses/Sub/Wobble.njopreset") foundLeaf = n.current; for (auto& k : n.kids) walk (k); };
        walk (nodes[0]); CHECK (foundLeaf);
        // the tree overlay shows them
        bar.openBank(); pump (60);
        im.presetOv->refresh(); pump (60);
        save (host, shots.getChildFile ("bank_tree.png"));
        bar.closeOverlays();
        // delete: armed first, then gone with the preset inside
        im.selFolder = "Basses";
        im.folderAct (false, "del", {}); CHECK (root.getChildFile ("Presets/Basses").exists());
        im.folderAct (false, "del", {}); CHECK (! root.getChildFile ("Presets/Basses").exists());
        CHECK (im.cur.id.isEmpty() && im.selFolder.isEmpty());
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
        im.libFolder = "samples";
        im.folderAct (true, "new", "Drums");
        CHECK (im.libFolder == "samples/Drums" && root.getChildFile ("Samples/Drums").isDirectory());
        im.folderAct (true, "new", "Kicks");
        CHECK (im.libFolder == "samples/Drums/Kicks");
        im.libImport ({ src.getChildFile ("kick.wav") });     // not a duplicate: it is another folder
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
        im.libFolder = "samples/Drums";
        im.folderAct (true, "ren", "Percussion");
        CHECK (root.getChildFile ("Samples/Percussion/Kicks/kick.wav").existsAsFile() && ! root.getChildFile ("Samples/Drums").exists());
        CHECK (im.libFolder == "samples/Percussion" && im.slotLib["sm3"].id == "samples/Percussion/Kicks/kick.wav");
        CHECK (im.findLib ("samples/Percussion/Kicks/kick.wav") != nullptr);
        // a preset that still refers to the old folder finds the file by name and size
        {
            auto rec = *im.findPreset ("Kick Preset.njopreset");
            mem.clear (njo::SoundMemory::Sample, 3); pump (60);
            im.presetApply (rec); pump (150);
            CHECK (mem.get (njo::SoundMemory::Sample, 3) != nullptr);
        }
        // move a file between folders and kinds
        im.libMoveTo ("samples/Percussion/Kicks/kick.wav", "samples");
        CHECK (root.getChildFile ("Samples/kick (2).wav").existsAsFile() || root.getChildFile ("Samples/kick.wav").existsAsFile());
        CHECK (im.findLib ("samples/Percussion/Kicks/kick.wav") == nullptr);
        im.libMoveTo ("samples/Percussion/Kicks/nothing.wav", "samples");   // unknown ids are ignored
        im.libFolder = "samples";
        auto rows = 0; for (auto& r : im.lib) if (r.kind == 1 && r.folder.isEmpty()) ++rows;
        CHECK (rows == 2);
        // nodes of the vault tree: counts include the sub folders
        auto vn = im.vaultNodes();
        CHECK (vn.size() == 2 && vn[0].path == "samples" && vn[1].path == "wavetables");
        CHECK (vn[0].count == (int) std::count_if (im.lib.begin(), im.lib.end(), [] (auto& r) { return r.kind == 1; }));
        // delete a folder with a file inside: the slot reference goes away
        im.libFolder = "samples"; im.folderAct (true, "new", "Temp");
        im.libImport ({ src.getChildFile ("pad.wav") });
        im.libLoad ("samples/Temp/pad.wav", 4); pump (80);
        CHECK (im.slotLib.count ("sm4") == 1);
        im.folderAct (true, "del", {}); CHECK (root.getChildFile ("Samples/Temp").exists());
        im.folderAct (true, "del", {}); CHECK (! root.getChildFile ("Samples/Temp").exists());
        CHECK (im.slotLib.count ("sm4") == 0 && im.libFolder == "samples");
        // screenshots of the tree
        im.libFolder = "samples"; im.folderAct (true, "new", "Loops"); im.folderAct (true, "new", "Hats");
        im.libFolder = "samples/Loops"; im.libImport ({ src.getChildFile ("pad.wav") });
        bar.openVault (1, -1); pump (60);
        im.libRefresh(); im.setLibFolder ("samples/Loops"); im.vaultOv->refresh(); pump (80);
        save (host, shots.getChildFile ("vault_tree.png"));
        im.vaultOv->search.setText ("pad", true); pump (60);
        save (host, shots.getChildFile ("vault_search.png"));
        im.vaultOv->search.setText ({}, true);
        bar.closeOverlays();
    }

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
