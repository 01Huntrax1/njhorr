// Times the parameter part of a preset load with the editor open: current way (set all + touchAll) vs only changed values.
#include "../NjoMock.h"
#include "../NjoEditor.h"
#include <cstdio>
#include <random>
static double ms() { return juce::Time::getMillisecondCounterHiRes(); }
int main()
{
    juce::ScopedJuceInitialiser_GUI init;
    njo::MockBackend be;
    auto ed = std::make_unique<njo::EditorContent> (be);
    ed->setBounds (0, 0, njo::BASE_W, njo::BASE_H);
    juce::MessageManager::getInstance()->runDispatchLoopUntil (50);
    auto& ctx = ed->context();
    std::mt19937 rng (7);
    for (int page : { 0, 6, 8 })
    {
        ed->setSynthPage (page);
        juce::MessageManager::getInstance()->runDispatchLoopUntil (30);
        // a "preset": ~400 values differ from the current ones
        std::map<int, double> rec;
        for (auto& s : njo::allSpecs()) { double v = ctx.get (s.num); if (rng() % 21 == 0) v = s.min + (s.max - s.min) * (rng() % 1000) / 1000.0; rec[s.num] = v; }
        double t = ms();
        for (auto& s : njo::allSpecs()) ctx.set (s.num, (float) rec[s.num]);
        double t1 = ms() - t; t = ms();
        ctx.touchAll();
        double t2 = ms() - t;
        // second preset, changed values only
        std::map<int, double> rec2 = rec;
        for (auto& s : njo::allSpecs()) if (rng() % 21 == 0) rec2[s.num] = s.min + (s.max - s.min) * (rng() % 1000) / 1000.0;
        t = ms(); int n = 0;
        for (auto& s : njo::allSpecs()) { float v = (float) rec2[s.num]; if (std::abs (ctx.get (s.num) - v) > 0.0f) { ctx.set (s.num, v); ++n; } }
        double t3 = ms() - t;
        std::printf ("page %d: set all %7.1f ms + touchAll %7.1f ms   |  changed only (%d) %7.1f ms\n", page, t1, t2, n, t3);
        juce::MessageManager::getInstance()->runDispatchLoopUntil (30);
    }
}
