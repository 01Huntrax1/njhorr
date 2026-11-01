// Times what happens when the editor opens: first access to the tables, building every page, showing each page.
//   open_time [rounds] [installed]   (a second argument pretends the factory wavetables are installed already)
#include "../NjoMock.h"
#include "../NjoEditor.h"
#include <cstdio>

static double ms() { return juce::Time::getMillisecondCounterHiRes(); }

int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    const int rounds = argc > 1 ? std::atoi (argv[1]) : 3;
    double t = ms();
    njo::MockBackend be;
    if (argc > 2) { auto m = be.rootFolder().getChildFile ("Wavetables/Factory/.factory-1"); m.create(); }   // factory wavetables already installed (the normal case)
    std::printf ("MockBackend (allSpecs, defaults)       %7.1f ms\n", ms() - t);
    for (int r = 0; r < rounds; ++r)
    {
        t = ms();
        auto ed = std::make_unique<njo::EditorContent> (be);
        const double tc = ms() - t; t = ms();
        ed->setBounds (0, 0, njo::BASE_W, njo::BASE_H);
        const double tb = ms() - t; t = ms();
        juce::MessageManager::getInstance()->runDispatchLoopUntil (20);
        std::printf ("round %d: construct %7.1f ms   setBounds %7.1f ms   first dispatch %7.1f ms\n", r, tc, tb, ms() - t);
        double tot = 0; double worst = 0; int worstPage = 0;
        for (int p = 0; p < 18; ++p)
        {
            t = ms(); ed->setSynthPage (p); juce::Image img (juce::Image::ARGB, njo::BASE_W, njo::BASE_H, true); juce::Graphics g (img); ed->paintEntireComponent (g, false);
            const double d = ms() - t; tot += d; if (d > worst) { worst = d; worstPage = p; }
        }
        std::printf ("         18 pages: total %7.1f ms (show + paint), slowest page %d: %.1f ms\n", tot, worstPage, worst);
        t = ms(); ed.reset(); std::printf ("         destroy %7.1f ms\n", ms() - t);
    }
}
