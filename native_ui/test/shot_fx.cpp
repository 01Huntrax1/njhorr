#include "../NjoEditor.h"
#include "../NjoMock.h"
static void save (juce::Component& c, const juce::File& f) { auto img = c.createComponentSnapshot (c.getLocalBounds(), true, 1.0f); juce::PNGImageFormat png; f.deleteFile(); juce::FileOutputStream o (f); if (o.openedOk()) png.writeImageToStream (img, o); }
int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init; juce::File dir (argc > 1 ? argv[1] : "shots"); dir.createDirectory();
    njo::MockBackend be;
    auto set = [&] (int rk, int sl, int type) { int b = njo::fxRacks()[(size_t) rk].id + sl * 10; be.setParam (b, (float) type); auto& t = njo::fxTypes()[(size_t) type]; be.setParam (b + 1, 1); be.setParam (b + 2, t.mix); for (size_t k = 0; k < t.params.size(); ++k) be.setParam (b + 4 + (int) k, t.params[k].def); };
    set (0, 0, 3); set (0, 1, 9); set (0, 2, 8); be.setParam (njo::fxRacks()[0].id + 11, 0);   // slot 2 off
    set (1, 0, 1); set (2, 3, 11); set (2, 5, 10);
    be.setParam (njo::fxRacks()[0].ord + 0, 2); be.setParam (njo::fxRacks()[0].ord + 2, 0);   // swap order of slots 0 and 2
    njo::EditorContent ed (be); ed.setBounds (0, 0, njo::BASE_W, njo::BASE_H);
    auto pump = [] { juce::MessageManager::getInstance()->runDispatchLoopUntil (50); };
    ed.setGroup (njo::EditorContent::Effects); pump(); save (ed, dir.getChildFile ("fx_main.png"));
    // simulate the grip-drag / arrow logic through params: move slot 1 to top via the order params
    return 0;
}
