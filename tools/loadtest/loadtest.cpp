#include "cmajor/helpers/cmaj_Patch.h"
#include "cmajor/helpers/cmaj_GeneratedCppEngine.h"
#include "perf_ns.inc"
#include <cstdio>
#include <thread>
#include <fstream>
#include <chrono>
static double nowMs() { return std::chrono::duration<double, std::milli> (std::chrono::steady_clock::now().time_since_epoch()).count(); }
using namespace cmaj;
using Perf = performer::Eisenpuls_Synth;

static std::string manifestJSON = "{\"CmajorVersion\":1,\"ID\":\"com.test.njhorr\",\"version\":\"1.0\",\"name\":\"x\",\"source\":\"x.cmajor\"}";

static void setupManifest (Patch::LoadParams& lp)
{
    lp.manifest.needsToBuildSource = false;
    lp.manifest.initialiseWithVirtualFile ("x.cmajorpatch",
        [] (const std::string& f) -> std::shared_ptr<std::istream> { if (f == "x.cmajorpatch") return std::make_shared<std::istringstream> (manifestJSON); return {}; },
        [] (const std::string& n) -> std::string { return n; },
        [] (const std::string&) -> std::filesystem::file_time_type { return {}; },
        [] (const std::string& f) { return f == "x.cmajorpatch"; });
}

static double renderRms (Patch& p, int note)
{
    const uint32_t bs = p.getPlaybackParams().blockSize; std::vector<float> l (bs), r (bs); float* ch[2] = { l.data(), r.data() };
    uint8_t on[3] = { 0x90, (uint8_t) note, 100 };
    p.addMIDIMessage (0, on, 3);
    double sum = 0; size_t n = 0;
    for (int b = 0; b < 400 * 128 / (int) bs; ++b)
    {
        p.process (ch, bs, [] (uint32_t, choc::midi::ShortMessage) {});
        if (b > 3 * 128 / (int) bs && b < 100 * 128 / (int) bs) for (uint32_t i = 0; i < bs; ++i) { sum += l[i] * l[i]; ++n; }
    }
    return std::sqrt (sum / (double) n);
}

static void pumpFor (int ms) { for (int i = 0; i < ms / 10; ++i) { choc::messageloop::pump(); std::this_thread::sleep_for (std::chrono::milliseconds (10)); } }

int main (int argc, char** argv)
{
    // args: mode (0 = defaults, 1 = kick via LoadParams, 2 = kick, then a rate change like the host does), rate2
    int mode = argc > 1 ? atoi (argv[1]) : 0;
    auto patch = std::make_shared<Patch>();
    patch->createEngine = +[] { return cmaj::createEngineForGeneratedCppProgram<Perf>(); };
    patch->createContextForPatchWorker = [] (const std::string&) -> std::unique_ptr<Patch::WorkerContext> { return nullptr; };
    patch->setPlaybackParams (Patch::PlaybackParams (44100, 128, 0, 2), true);

    Patch::LoadParams lp; setupManifest (lp);
    // the plugin's constructor: the default state
    double t0 = nowMs();
    patch->loadPatch (lp, true);
    printf ("default build %.0f ms\n", nowMs() - t0);
    printf ("default load: playable=%d\n", (int) patch->isPlayable());
    if (mode >= 8)
    {   // the host thread changes the rate (prepareToPlay) while the message thread applies the project state, both synchronous builds
        int delay = atoi (argv[2]);
        Patch::LoadParams lp2; setupManifest (lp2);
        for (auto& p : patch->getParameterList()) lp2.parameterValues[p->properties.endpointID] = p->properties.defaultValue;
        lp2.parameterValues["param1000"] = 5.0f;
        std::thread host ([&] { patch->setPlaybackParams (Patch::PlaybackParams (48000, 256, 0, 2), true); });
        std::this_thread::sleep_for (std::chrono::milliseconds (delay));
        patch->loadPatch (lp2, true);
        host.join();
        printf ("playable=%d\n", (int) patch->isPlayable());
    }
    if (mode >= 1 && mode < 8 && mode != 4)
    {
        Patch::LoadParams lp2; setupManifest (lp2);
        // like readParametersFromState: every parameter with a value; osc 1 = Kick
        for (auto& p : patch->getParameterList()) lp2.parameterValues[p->properties.endpointID] = p->properties.defaultValue;
        lp2.parameterValues["param1000"] = 5.0f;
        patch->loadPatch (lp2, mode >= 5 ? false : true);
        printf ("state load: playable=%d type=%g\n", (int) patch->isPlayable(), [&] { for (auto& p : patch->getParameterList()) if (p->properties.endpointID == "param1000") return (double) p->currentValue; return -1.0; }());
        if (mode == 5) pumpFor (3000);        // async state build only
        if (mode == 6) { patch->setPlaybackParams (Patch::PlaybackParams (48000, 512, 0, 2), false); pumpFor (6000); }   // host changes rate / block while the state build runs
        if (mode == 7) { pumpFor (3000); patch->setPlaybackParams (Patch::PlaybackParams (48000, 512, 0, 2), false); pumpFor (6000); }   // ... after it finished
        if (mode == 2)
        {
            patch->setPlaybackParams (Patch::PlaybackParams (48000, 256, 0, 2), true);
            for (int i = 0; i < 100 && ! patch->isPlayable(); ++i) std::this_thread::sleep_for (std::chrono::milliseconds (100));
            printf ("after rate change: playable=%d\n", (int) patch->isPlayable());
        }
    }
    if (mode == 4)   // live: default load, then the host sets the parameter
    {
        for (auto& p : patch->getParameterList()) if (p->properties.endpointID == "param1000") p->setValue (5.0f, true, 0, 0);
    }
    if (mode >= 5) { for (auto& p : patch->getParameterList()) if (p->properties.endpointID == "param1000") printf ("final type=%g playable=%d pending=%d\n", (double) p->currentValue, (int) patch->isPlayable(), (int) patch->loadParamsPending); }
    { double t1 = nowMs(); double r = renderRms (*patch, 48); double t2 = nowMs();
      printf ("rms %.5f  render %.0f ms for %d blocks (idle+1 voice)\n", r, t2 - t1, 400 * 128 / (int) patch->getPlaybackParams().blockSize); }
    return 0;
}
cmaj::ProgramPtr cmaj::Library::createProgram() { return {}; }
