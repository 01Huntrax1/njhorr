// Headless screenshot harness: njo_shot <outDir> [scale]  renders every page of the editor to PNG (software renderer, no display needed).
#include "../NjoPhys.h"
#include "../NjoEditor.h"
#include "../NjoMock.h"
#include "../NjoFreq.h"

static void save (juce::Component& c, const juce::File& f, float scale)
{
    auto img = c.createComponentSnapshot (c.getLocalBounds(), true, scale);
    juce::PNGImageFormat png;
    f.deleteFile();
    juce::FileOutputStream out (f);
    if (out.openedOk()) png.writeImageToStream (img, out);
}

int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    juce::File dir (argc > 1 ? argv[1] : "shots");
    dir.createDirectory();
    float scale = argc > 2 ? (float) std::atof (argv[2]) : 1.0f;
    njo::MockBackend be;
    njo::EditorContent ed (be);
    ed.setBounds (0, 0, njo::BASE_W, njo::BASE_H);
    auto pump = [] { juce::MessageManager::getInstance()->runDispatchLoopUntil (50); };
    pump();
    be.setParam (njo::fmId (0, 1), 60); be.setParam (njo::fmId (2, 2), 35); be.setParam (njo::pmId (1, 3), 100); be.setParam (njo::pdId (0, 2), 45); be.setParam (njo::pdId (3, 4), 8);
    be.setParam (njo::oscId (1, njo::oscKey ("ftype")), 30); be.setParam (njo::oscId (1, njo::oscKey ("wfpos")), 0.35f); be.setParam (njo::oscId (1, njo::oscKey ("fon")), 1);
    be.setParam (njo::oscId (1, njo::oscKey ("dtype")), 7); be.setParam (njo::oscId (1, njo::oscKey ("wdpos")), 0.3f);
    be.setParam (njo::oscId (0, njo::oscKey ("freq")), 0.55f);
    ed.context().modAssign (24, 12, 0.6f); ed.context().modAssign (25, 180, 0.4f);
    {
        auto& P = ed.context().freqShapes->points (0);
        P = { { 0, 0.95f, 0 }, { 0.12f, 0.7f, 0 }, { 0.25f, 0.5f, 0 }, { 0.5f, 0.3f, 0 }, { 1, 0.1f, 0 } };
    }
    const char* names[] = { "osc1", "osc2", "osc3", "osc4", "osc5", "osc6", "fm", "rmam", "global" };
    for (int i = 0; i < 9; ++i) { ed.setSynthPage (i); pump(); save (ed, dir.getChildFile (juce::String (names[i]) + ".png"), scale); }
    {
        auto& cx = ed.context();
        ed.setSynthPage (9); pump(); save (ed, dir.getChildFile ("flt.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("ftype")), 30.0f); cx.set (njo::oscId (0, njo::oscKey ("wfwarp")), 0.5f); cx.set (njo::oscId (0, njo::oscKey ("wfcont")), 0.4f); cx.set (njo::oscId (0, njo::oscKey ("wftilt")), -0.3f); ed.setSynthPage (9); pump(); save (ed, dir.getChildFile ("flt_wf.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("ftype")), 0.0f);
        ed.setSynthPage (15); pump(); save (ed, dir.getChildFile ("dist.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("dtype")), 7.0f); ed.setSynthPage (15); pump(); save (ed, dir.getChildFile ("dist_wd.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("dtype")), 0.0f);
        // Physical source
        cx.set (njo::oscId (0, njo::oscKey ("type")), 3.0f); cx.set (njo::phys::phyId (0, njo::phys::key ("phmodA")), 6.0f); cx.set (njo::phys::phyId (0, njo::phys::key ("phmodB")), 3.0f);
        ed.setSynthPage (0); pump(); save (ed, dir.getChildFile ("osc1_phys.png"), scale);
        cx.set (njo::oscId (0, njo::oscKey ("type")), 0.0f);
    }
    ed.setSynthPage (0); ed.setStripTab (1); pump (); save (ed, dir.getChildFile ("frq_strip.png"), scale); ed.setStripTab (0);
    {
        // FX page: empty rack (type grid), a chain of three effects, and one screenshot per effect type
        auto& cx = ed.context();
        ed.setGroup (njo::EditorContent::Effects); pump(); save (ed, dir.getChildFile ("fx_empty.png"), scale);
        const int base = njo::fxRacks()[0].id;
        auto setFx = [&] (int slot, int type)
        {
            const int b = base + slot * 10;
            cx.set (b, (float) type);
            if (type > 0)
            {
                auto& t = njo::fxTypes()[(size_t) type];
                cx.set (b + 1, 1.0f); cx.set (b + 2, t.mix); cx.set (b + 3, type == 9 ? 1.0f : 0.0f);
                for (size_t k = 0; k < t.params.size(); ++k) cx.set (b + 4 + (int) k, t.params[k].def);
            }
        };
        for (int t = 1; t <= 11; ++t)
        {
            setFx (0, t); pump();
            save (ed, dir.getChildFile ("fx_type" + juce::String (t) + ".png"), scale);
        }
        setFx (0, 9); setFx (1, 3); setFx (2, 8); setFx (3, 11); pump();
        save (ed, dir.getChildFile ("fx.png"), scale);
        for (int sl = 0; sl < 4; ++sl) setFx (sl, 0);
        pump();
    }
    ed.setGroup (njo::EditorContent::Modulation); pump(); save (ed, dir.getChildFile ("mod.png"), scale);
    ed.setModTab (1); pump(); save (ed, dir.getChildFile ("frq_mod.png"), scale);
    return 0;
}
