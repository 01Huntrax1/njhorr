// Interactive transfer-curve editor of the Waveshaper effect (FX type 15): draggable nodes, curvature handles, presets.
#pragma once
#include "../NjoPages.h"
#include "../NjoMemory.h"
#include "../NjoShaper.h"

namespace njo
{
    class ShaperEditor : public juce::Component, private juce::Timer, private Ctx::Listener, private juce::ChangeListener
    {
    public:
        ShaperEditor (Ctx&, SoundMemory&);
        ~ShaperEditor() override;
        void setSlot (int globalSlot, int paramBase);
        void paint (juce::Graphics&) override;
        void mouseMove (const juce::MouseEvent&) override;
        void mouseExit (const juce::MouseEvent&) override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;
        void mouseUp (const juce::MouseEvent&) override;
        void mouseDoubleClick (const juce::MouseEvent&) override;
        struct Impl; std::unique_ptr<Impl> impl;
    private:
        void timerCallback() override;
        void paramChanged (int num, float v) override;
        void changeListenerCallback (juce::ChangeBroadcaster*) override;
    };
}
