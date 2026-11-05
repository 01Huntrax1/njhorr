#include "NjoVst3Host.h"
#include <cmath>
static int fails = 0;
static void check (const char* n, bool ok, const juce::String& x = {}) { printf ("%s %s %s\n", ok ? "PASS" : "FAIL", n, x.toRawUTF8()); fflush (stdout); if (! ok) ++fails; }
int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    juce::String dir = argc > 1 ? argv[1] : ".";
    static std::unique_ptr<njo::Vst3Host> hp (new njo::Vst3Host()); auto& h = *hp; h.prepare (48000.0);
    constexpr int K = njo::Vst3Host::kChunk;
    static juce::ValueTree st;
    check ("host has no plugin at the start", h.name (0).isEmpty() && h.name (1).isEmpty());
    h.loadFile (1, juce::File (dir).getChildFile ("TestSine.vst3"));
    check ("effect slot refuses an instrument", h.status (1).contains ("instrument") && h.name (1).isEmpty(), h.status (1));
    h.loadFile (0, juce::File (dir).getChildFile ("TestSine.vst3"));
    h.loadFile (1, juce::File (dir).getChildFile ("TestGain.vst3"));
    juce::Timer::callAfterDelay (3000, [&h]
    {
        check ("instrument loaded", h.name (0) == "TestSine", h.name (0) + " / " + h.status (0));
        check ("effect loaded", h.name (1) == "TestGain", h.name (1) + " / " + h.status (1));
        float sl[K], sr[K], rl[K], rr[K], il[K], ir[K];
        double sumRet[8] {};
        for (int b = 0; b < 8; ++b)
        {
            for (int i = 0; i < K; ++i) sl[i] = sr[i] = 1.0f;
            h.fetchReturn (rl, rr, K); h.pushSend (sl, sr, K);
            for (int i = 0; i < K; ++i) sumRet[b] += rl[i];
        }
        check ("effect: first chunk of the return is silent (latency 64)", sumRet[0] == 0.0, juce::String (sumRet[0]));
        check ("effect: later chunks are the send * 0.5", std::abs (sumRet[3] / K - 0.5) < 1e-4, juce::String (sumRet[3] / K));
        juce::MidiBuffer none, on; on.addEvent (juce::MidiMessage::noteOn (1, 69, (juce::uint8) 100), 0);
        h.renderInstrument (none, il, ir, K);
        double e0 = 0; for (int i = 0; i < K; ++i) e0 += std::abs (il[i]);
        h.renderInstrument (on, il, ir, K);
        double e1 = 0; for (int i = 0; i < K; ++i) e1 += std::abs (il[i]);
        check ("instrument: silent before the note", e0 == 0.0, juce::String (e0));
        check ("instrument: sounds after note on", e1 > 1.0, juce::String (e1));
        st = h.saveState();
        check ("state has two slots", st.getNumChildren() == 2, juce::String (st.getNumChildren()));
        h.unload (0); h.unload (1);
        check ("unload clears the names", h.name (0).isEmpty() && h.name (1).isEmpty());
        h.restoreState (st);
        juce::Timer::callAfterDelay (3000, [&h]
        {
            check ("restoreState reloads both", h.name (0) == "TestSine" && h.name (1) == "TestGain", h.name (0) + " / " + h.name (1));
            h.unload (1);
            float sl[K], sr[K], rl[K], rr[K]; double s2 = 0;
            for (int b = 0; b < 4; ++b) { for (int i = 0; i < K; ++i) sl[i] = sr[i] = 1.0f; h.fetchReturn (rl, rr, K); h.pushSend (sl, sr, K); if (b == 3) for (int i = 0; i < K; ++i) s2 += rl[i]; }
            check ("no effect loaded: the send comes back unchanged", std::abs (s2 / K - 1.0) < 1e-4, juce::String (s2 / K));
            juce::MessageManager::getInstance()->stopDispatchLoop();
        });
    });
    juce::MessageManager::getInstance()->runDispatchLoop();
    hp.reset();
    printf (fails ? "FAILURES %d\n" : "ALL OK\n", fails);
    return fails ? 1 : 0;
}
