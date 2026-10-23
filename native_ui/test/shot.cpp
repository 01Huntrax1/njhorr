// Headless screenshot harness: njo_shot <outDir> [scale]  renders every page of the editor to PNG (software renderer, no display needed).
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
    const char* names[] = { "osc1", "osc2", "osc3", "osc4", "osc5", "osc6", "fm", "global" };
    for (int i = 0; i < 8; ++i) { ed.setSynthPage (i); pump(); save (ed, dir.getChildFile (juce::String (names[i]) + ".png"), scale); }
    ed.setSynthPage (0); ed.setStripTab (1); pump (); save (ed, dir.getChildFile ("frq_strip.png"), scale); ed.setStripTab (0);
    ed.setGroup (njo::EditorContent::Effects); pump(); save (ed, dir.getChildFile ("fx.png"), scale);
    ed.setGroup (njo::EditorContent::Modulation); pump(); save (ed, dir.getChildFile ("mod.png"), scale);
    ed.setModTab (1); pump(); save (ed, dir.getChildFile ("frq_mod.png"), scale);
    return 0;
}
