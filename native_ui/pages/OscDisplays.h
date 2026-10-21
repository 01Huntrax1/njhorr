// Displays of the OSC page: the wavetable / sample / Plaits panel and the filter response curve.
#pragma once
#include "../NjoPages.h"
#include <complex>

namespace njo
{
    namespace oscmodel
    {
        // analog approximation of the DSP filter types (port of filterH / svfH of the web UI); ft 0-29, fc in Hz, res 0-1
        std::complex<double> filterH (int ft, double fc, double res, double f, double sweep = 1.0);
        float warpPhase (int mode, float amt, float ph);
        float warpAmp (int mode, float amt, float y);
        int pickFrameIndex (int len);                      // frame size index (0-4) that fits a freshly loaded wavetable
        constexpr int frameSizes[5] = { 256, 512, 1024, 2048, 4096 };
    }

    // waveform of the current wavetable frame (with warp), sample waveform with start marker, or the Plaits engine name;
    // the line below the picture says what is shown
    class OscDisplay : public juce::Component, private Ctx::Listener, private juce::ChangeListener
    {
    public:
        OscDisplay (Ctx&, SoundMemory&, int osc);
        ~OscDisplay() override;
        void paint (juce::Graphics&) override;
        static constexpr int pictureH = 70;        // the rest of the component holds the info line
    private:
        void paramChanged (int num, float v) override;
        void changeListenerCallback (juce::ChangeBroadcaster*) override { repaint(); }
        float pv (const char* key) const { return ctx.get (oscId (o, oscKey (key))); }
        Ctx& ctx; SoundMemory& mem; int o;
    };

    class FilterDisplay : public juce::Component, private Ctx::Listener
    {
    public:
        FilterDisplay (Ctx&, int osc);
        ~FilterDisplay() override;
        void paint (juce::Graphics&) override;
    private:
        void paramChanged (int num, float v) override;
        Ctx& ctx; int o;
    };
}
