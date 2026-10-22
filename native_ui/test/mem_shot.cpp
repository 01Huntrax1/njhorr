// PRIVATE (memory worker): SoundMemory round trip checks + FM / Global page screenshots.
#include "../NjoEditor.h"
#include "../NjoMock.h"
#include <cstdio>
static int fails = 0;
#define CHECK(c) do { if (! (c)) { ++fails; std::printf ("FAIL line %d: %s\n", __LINE__, #c); } } while (0)
static void save (juce::Component& c, const juce::File& f)
{
    auto img = c.createComponentSnapshot (c.getLocalBounds(), true, 1.0f);
    juce::PNGImageFormat png; f.deleteFile(); juce::FileOutputStream out (f); if (out.openedOk()) png.writeImageToStream (img, out);
}
int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    juce::File dir (argc > 1 ? argv[1] : "shots"), audio (argc > 2 ? argv[2] : "audio");
    dir.createDirectory();
    auto pump = [] (int ms = 50) { juce::MessageManager::getInstance()->runDispatchLoopUntil (ms); };
    using namespace njo;
    MockBackend be; Ctx ctx (be);
    {
        SoundMemory mem (ctx);
        const char* files[] = { "t.wav", "t.aiff", "t.flac", "t.ogg", "t24.wav", "t.au", "tf.wav", "t.raw", "bad.wav" };
        for (int i = 0; i < 9; ++i)
        {
            bool ok = false; juce::String msg;
            mem.load (i % 2 ? SoundMemory::Sample : SoundMemory::Wavetable, i % 6, audio.getChildFile (files[i]), [&] (bool o, const juce::String& m) { ok = o; msg = m; });
            auto* s = mem.get (i % 2 ? SoundMemory::Sample : SoundMemory::Wavetable, i % 6);
            std::printf ("%-9s ok=%d %s len=%d name=%s\n", files[i], (int) ok, msg.toRawUTF8(), s ? (int) s->data.size() : -1, s ? s->name.toRawUTF8() : "-");
            if (std::string (files[i]) == "bad.wav") CHECK (! ok); else CHECK (ok && s && ! s->data.empty());
            if (s) { float pk = 0; for (float v : s->data) pk = std::max (pk, std::abs (v)); CHECK (std::abs (pk - 0.9f) < 0.01f || std::string (files[i]) == "t.raw"); }
        }
        pump (400);
        // chunk events for osc 0 wavetable (t.wav 0.5s @44.1k -> 24000 samples @48k)
        int chunks = 0; size_t last = 0; bool ordered = true; int total = 0;
        for (auto& e : be.events) if (e.endpoint == "wtBankLoad" && (int) e.value["bank"] == 0)
        { if ((int) e.value["offset"] != (int) last && chunks) ordered = false; ++chunks; last = (size_t) ((int) e.value["offset"] + 256); total = e.value["total"]; CHECK (e.value["data"].size() == 256); }
        std::printf ("wt0 chunks=%d total=%d ordered=%d\n", chunks, total, (int) ordered);
        CHECK (total > 0 && chunks == (total + 255) / 256 && ordered);   // wavetables are not resampled to 48 kHz any more
        CHECK (be.stored.count ("njo.mem.osc0.wt") == 1);
        // Vital wavetable (.vitaltable): two keyframes (sine at 0, saw at 255) -> 128 frames of 2048
        {
            auto f32 = [] (std::function<float (float)> fn)
            {
                juce::MemoryOutputStream mo; for (int i = 0; i < 2048; ++i) mo.writeFloat (fn ((float) i / 2048.0f));   // little endian
                return juce::Base64::toBase64 (mo.getData(), mo.getDataSize());
            };
            auto* root = new juce::DynamicObject(); juce::var vroot (root);
            root->setProperty ("name", "Test Table");
            auto* kf0 = new juce::DynamicObject(); kf0->setProperty ("position", 0); kf0->setProperty ("wave_data", f32 ([] (float p) { return std::sin (6.2831853f * p); }));
            auto* kf1 = new juce::DynamicObject(); kf1->setProperty ("position", 255); kf1->setProperty ("wave_data", f32 ([] (float p) { return 2 * p - 1; }));
            auto* comp = new juce::DynamicObject(); comp->setProperty ("type", "Wave Source"); comp->setProperty ("keyframes", juce::Array<juce::var> { juce::var (kf0), juce::var (kf1) });
            auto* grp = new juce::DynamicObject(); grp->setProperty ("components", juce::Array<juce::var> { juce::var (comp) });
            root->setProperty ("groups", juce::Array<juce::var> { juce::var (grp) });
            auto vf = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njo_test.vitaltable");
            vf.replaceWithText (juce::JSON::toString (vroot));
            bool ok = false; juce::String msg;
            mem.load (SoundMemory::Wavetable, 2, vf, [&] (bool o, const juce::String& m) { ok = o; msg = m; });
            auto* s = mem.get (SoundMemory::Wavetable, 2);
            CHECK (ok && s && s->data.size() == 128 * 2048 && s->name == "TEST TABLE");
            if (s) { CHECK (std::abs (s->data[512] - 0.9f) < 0.02f); CHECK (std::abs (s->data[127 * 2048 + 512] - 0.9f * (2 * 0.25f - 1)) < 0.02f); }
            vf.deleteFile();
        }
        // clear
        mem.clear (SoundMemory::Wavetable, 0);
        CHECK (mem.get (SoundMemory::Wavetable, 0) == nullptr);
        CHECK (be.stored.count ("njo.mem.osc0.wt") == 0);
        CHECK (be.events.back().endpoint == "wtBankLoad" && (int) be.events.back().value["count"] == 0);
        // set() with decoded data
        std::vector<float> d (2048 * 3); for (size_t i = 0; i < d.size(); ++i) d[i] = std::sin (i * 0.05f) * 0.9f;
        mem.set (SoundMemory::Wavetable, 2, "MYTABLE", "lib:1", d);
    }
    // new instance over the same stored state: displays have it at once, restore() streams it
    pump (100);
    be.events.clear();
    {
        SoundMemory mem2 (ctx);
        auto* s = mem2.get (SoundMemory::Wavetable, 2);
        CHECK (s && s->name == "MYTABLE" && s->libId == "lib:1" && s->data.size() == 2048 * 3);
        if (s) { float err = 0; for (size_t i = 0; i < s->data.size(); ++i) err = std::max (err, std::abs (s->data[i] - std::sin (i * 0.05f) * 0.9f)); CHECK (err < 0.0005f); }
        CHECK (mem2.get (SoundMemory::Sample, 1) != nullptr);
        mem2.restore(); pump (1500);
        int n = 0; for (auto& e : be.events) if (e.endpoint == "wtBankLoad" || e.endpoint == "smpBankLoad") ++n;
        std::printf ("restore events=%d\n", n);
        CHECK (n > 20);
    }
    // FM / GLOBAL pages
    MockBackend be2; EditorContent ed (be2);
    ed.setBounds (0, 0, BASE_W, BASE_H); pump();
    auto F = [&] (int k, int s, int d, float v) { be2.setParam ((k ? PM_BASE : FM_BASE) + 6 * s + d, v); };
    F (0, 0, 1, 0.5f); F (0, 1, 2, -0.35f); F (0, 2, 0, 0.8f); F (0, 3, 3, 0.25f); F (0, 4, 5, 1.0f);
    F (1, 0, 3, 0.4f); F (1, 5, 1, -0.6f); F (1, 2, 2, -0.2f);
    ed.setSynthPage (6); pump(); save (ed, dir.getChildFile ("fm.png"));
    ed.setSynthPage (7); pump(); save (ed, dir.getChildFile ("global.png"));
    std::printf ("%s (%d failures)\n", fails ? "FAILED" : "ALL OK", fails);
    return fails ? 1 : 0;
}
