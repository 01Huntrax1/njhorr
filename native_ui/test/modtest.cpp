// Mod editors test: dumps LFO tables (built-in waves + presets) for comparison with the JS functions; renders the popup.
#include "../NjoEditor.h"
#include "../NjoLfo.h"
#include "../NjoMock.h"
static void save (juce::Component& c, const juce::File& f)
{
    auto img = c.createComponentSnapshot (c.getLocalBounds(), true, 1.0f);
    juce::PNGImageFormat png; f.deleteFile(); juce::FileOutputStream out (f); if (out.openedOk()) png.writeImageToStream (img, out);
}
int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    juce::File dir (argc > 1 ? argv[1] : "shots"); dir.createDirectory();
    njo::MockBackend be; njo::EditorContent ed (be); ed.setBounds (0, 0, njo::BASE_W, njo::BASE_H);
    auto pump = [] { juce::MessageManager::getInstance()->runDispatchLoopUntil (50); };
    pump();
    // tables
    juce::String out;
    auto dump = [&] (const juce::String& n, const std::vector<njo::LfoPoint>& p)
    { out << n; for (float v : njo::LfoShapes::table (p)) out << " " << juce::String (v, 5); out << "\n"; };
    for (int w = 0; w < 6; ++w) dump ("b" + juce::String (w), njo::LfoShapes::builtin (w));
    int i = 0; for (auto& p : njo::lfoPresets()) { if (p.wave < 0) dump ("p" + juce::String (i), p.pts); ++i; }
    dir.getChildFile ("tables.txt").replaceWithText (out);
    // persistence round trip + events
    auto& ctx = ed.context();
    njo::LfoShapes& L = *ctx.lfoShapes;
    L.points (2); L.points (2).insert (L.points (2).begin() + 1, { 0.3f, 0.2f, 0.4f });
    L.commit (2, true);
    auto stored = be.getStored ("njo.lfo");
    njo::LfoShapes L2 (ctx); L2.fromVar (juce::JSON::parse (juce::JSON::toString (stored)));
    std::printf ("wave param after commit: %g, events: %d, roundtrip pts: %d (expected %d), isDrawn(2)=%d isDrawn(0)=%d\n",
                 ctx.get (njo::lfoWaveParam (2)), (int) be.events.size(), (int) L2.points (2).size(), (int) L.points (2).size(), L2.isDrawn (2), L2.isDrawn (0));
    std::printf ("json: %s\n", juce::JSON::toString (stored, true).substring (0, 160).toRawUTF8());
    // modulation: assign + popup
    ed.setSynthPage (7); pump();
    ctx.selectedLfo = 2; ctx.selectedEnv = 1;
    int tn = 0; for (auto& kv : njo::modTarget()) { tn = kv.first; break; }
    int s1 = ctx.modAssign (1, njo::modTarget().at (tn).first, 0.5f);
    int s2 = ctx.modAssign (12, njo::modTarget().at (tn).first, -0.3f);
    std::printf ("slots %d %d target %d\n", s1, s2, tn);
    pump(); save (ed, dir.getChildFile ("drawn_env2.png"));
    ed.setGroup (njo::EditorContent::Modulation); pump(); save (ed, dir.getChildFile ("mod_filled.png"));
    ed.setSynthPage (0); pump();
    njo::showModPopup (ctx, ed, tn); // popup relative to the whole editor (target = ed) just to render
    pump(); save (ed, dir.getChildFile ("popup.png"));
    return 0;
}
