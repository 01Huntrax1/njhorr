// The pages of the editor. Each page is its own component and only talks to Ctx / Backend.
#pragma once
#include "NjoCore.h"
#include "NjoWidgets.h"
#include "NjoMemory.h"

namespace njo
{
    // OSC 1-6: source panel (wavetable / sampler / Wave Terrain / ...), tune + unison, filter, distortion + output
    class OscPage : public juce::Component
    {
    public:
        // mode 0 = source / tune / output, 1 = filter + Wavefilter table, 2 = distortion + Wavedistortion table (one page per oscillator and mode)
        OscPage (Ctx&, SoundMemory&, int oscIndex, int mode = 0);
        ~OscPage() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        std::function<void (ParamWidget&)> onModDropped;
        std::function<void (int)> onSelectOsc;     // chip A-F of the filter / distortion page
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // FM / PM / PD matrices (page 0) or the RM / AM matrices (page 1)
    class FmPage : public juce::Component
    {
    public:
        explicit FmPage (Ctx&, int page = 0);
        ~FmPage() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        void setOnOpenOsc (std::function<void (int)> f);   // click on a node letter
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // Voice / Amp EG / Pitch EG / Output
    class GlobalPage : public juce::Component
    {
    public:
        explicit GlobalPage (Ctx&);
        ~GlobalPage() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        std::function<void (ParamWidget&)> onModDropped;
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // the three FX racks (Bus 1, Bus 2, Main) with 10 slots each and the output section
    class FxPage : public juce::Component
    {
    public:
        FxPage (Ctx&, SoundMemory&);
        ~FxPage() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        std::function<void (ParamWidget&)> onModDropped;
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // envelope + LFO editors with the drag handles for the modulation sources (bottom strip, and part of the modulation page)
    class ModEditors : public juce::Component
    {
    public:
        explicit ModEditors (Ctx&);
        ~ModEditors() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // the 10 Freq modulators: a curve of frequency over time (log axis), Retrig / Loop, Rate and Transpose; their handles only reach the
    // cutoff knobs and the oscillator Frequency knobs
    class FreqEditor : public juce::Component
    {
    public:
        explicit FreqEditor (Ctx&);
        ~FreqEditor() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // the modulation matrix (pages of 20 slots)
    class MatrixPanel : public juce::Component
    {
    public:
        explicit MatrixPanel (Ctx&);
        ~MatrixPanel() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        void setPage (int page);
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // popup with the amounts of the sources that modulate one parameter (shown after a drop)
    void showModPopup (Ctx&, juce::Component& target, int paramNum);
}
