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
        // Wavefilter / Wavedistortion tables: built-in frame values (mirror of tblDefault in the DSP) and the frame at position pos (0..1),
        // taken from the loaded table (slot, may be null) or the built-in one; out has 512 values
        float tblDefault (bool filter, int frame, int i);
        void tblFrame (const std::vector<float>* loaded, bool filter, float pos, float* out);
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

    class FilterDisplay : public juce::Component, private Ctx::Listener, private juce::ChangeListener
    {
    public:
        FilterDisplay (Ctx&, SoundMemory&, int osc);
        ~FilterDisplay() override;
        void paint (juce::Graphics&) override;
    private:
        void paramChanged (int num, float v) override;
        void changeListenerCallback (juce::ChangeBroadcaster*) override { repaint(); }
        Ctx& ctx; SoundMemory& mem; int o;
    };

    // transfer curve of the distortion of one slot (mirror of oscDist in the DSP)
    class DistDisplay : public juce::Component, private Ctx::Listener, private juce::ChangeListener
    {
    public:
        DistDisplay (Ctx&, SoundMemory&, int osc);
        ~DistDisplay() override;
        void paint (juce::Graphics&) override;
    private:
        float transfer (float x) const;
        void paramChanged (int num, float v) override;
        void changeListenerCallback (juce::ChangeBroadcaster*) override { repaint(); }
        Ctx& ctx; SoundMemory& mem; int o;
    };

    // magnitude response of the slot's resonator stage (16 modes tuned to A3 + Tune)
    class ResoDisplay : public juce::Component, private Ctx::Listener
    {
    public:
        ResoDisplay (Ctx&, int osc);
        ~ResoDisplay() override;
        void paint (juce::Graphics&) override;
    private:
        void paramChanged (int num, float v) override;
        Ctx& ctx; int o;
    };

    // the frames of a Wavefilter / Wavedistortion table behind each other, the frame at Table Pos in front; the line below says which table
    class TableDisplay : public juce::Component, private Ctx::Listener, private juce::ChangeListener
    {
    public:
        TableDisplay (Ctx&, SoundMemory&, int osc, bool filter);
        ~TableDisplay() override;
        void paint (juce::Graphics&) override;
        static constexpr int infoH = 14;
    private:
        void paramChanged (int num, float v) override;
        void changeListenerCallback (juce::ChangeBroadcaster*) override { repaint(); }
        Ctx& ctx; SoundMemory& mem; int o; bool isFilter;
    };
}
