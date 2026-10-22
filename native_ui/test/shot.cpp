// Headless screenshot harness: njo_shot <outDir> [scale]  renders every page of the editor to PNG (software renderer, no display needed).
#include "../NjoEditor.h"
#include "../NjoMock.h"

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
    const char* names[] = { "osc1", "osc2", "osc3", "osc4", "osc5", "osc6", "fm", "global" };
    for (int i = 0; i < 8; ++i) { ed.setSynthPage (i); pump(); save (ed, dir.getChildFile (juce::String (names[i]) + ".png"), scale); }
    ed.setGroup (njo::EditorContent::Effects); pump(); save (ed, dir.getChildFile ("fx.png"), scale);
    ed.setGroup (njo::EditorContent::Modulation); pump(); save (ed, dir.getChildFile ("mod.png"), scale);
    return 0;
}
