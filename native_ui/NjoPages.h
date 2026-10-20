// The pages of the editor. Each page is its own component and only talks to Ctx / Backend.
#pragma once
#include "NjoCore.h"
#include "NjoWidgets.h"
#include "NjoMemory.h"

namespace njo
{
    // OSC 1-6: source panel (wavetable / sampler / Plaits), tune + unison, filter, distortion + output
    class OscPage : public juce::Component
    {
    public:
        OscPage (Ctx&, SoundMemory&, int oscIndex);
        ~OscPage() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        std::function<void (ParamWidget&)> onModDropped;
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // FM / PM matrices
    class FmPage : public juce::Component
    {
    public:
        explicit FmPage (Ctx&);
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
        explicit FxPage (Ctx&);
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

    // the 20 slot modulation matrix
    class MatrixPanel : public juce::Component
    {
    public:
        explicit MatrixPanel (Ctx&);
        ~MatrixPanel() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        struct Impl; std::unique_ptr<Impl> impl;
    };

    // popup with the amounts of the sources that modulate one parameter (shown after a drop)
    void showModPopup (Ctx&, juce::Component& target, int paramNum);
}
