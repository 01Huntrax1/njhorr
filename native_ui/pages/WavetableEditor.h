// Wavetable editor: all frames as a waterfall, freehand drawing of the selected frame, harmonic bars, frame add / delete / generate / morph tools.
#pragma once
#include "../NjoPages.h"
#include "../NjoMemory.h"

namespace njo
{
    class WavetableEditor : public juce::Component, private juce::ChangeListener
    {
    public:
        WavetableEditor (Ctx&, SoundMemory&, int osc);
        ~WavetableEditor() override;
        void open();
        std::function<void()> onClose;
        void paint (juce::Graphics&) override;
        void resized() override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;
        void mouseUp (const juce::MouseEvent&) override;
        struct Impl; std::unique_ptr<Impl> impl;
    private:
        void changeListenerCallback (juce::ChangeBroadcaster*) override;
    };
}
