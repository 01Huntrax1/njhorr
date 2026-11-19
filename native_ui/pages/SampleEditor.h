// Sampler waveform editor: big waveform (stereo lanes) with draggable Start / End / Loop markers, slice grid, zoom, normalize / trim and all sampler controls.
#pragma once
#include "../NjoPages.h"
#include "../NjoMemory.h"

namespace njo
{
    class SampleEditor : public juce::Component, private Ctx::Listener, private juce::ChangeListener
    {
    public:
        SampleEditor (Ctx&, SoundMemory&, int osc);
        ~SampleEditor() override;
        void open();
        std::function<void()> onClose;
        void paint (juce::Graphics&) override;
        void resized() override;
        void mouseMove (const juce::MouseEvent&) override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;
        void mouseUp (const juce::MouseEvent&) override;
        void mouseDoubleClick (const juce::MouseEvent&) override;
        void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;
        struct Impl; std::unique_ptr<Impl> impl;
    private:
        void paramChanged (int num, float v) override;
        void changeListenerCallback (juce::ChangeBroadcaster*) override;
    };
}
