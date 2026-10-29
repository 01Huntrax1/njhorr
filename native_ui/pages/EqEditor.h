// Interactive editor of the Parametric EQ effect (FX type 13): response curve with draggable band nodes, band list, band and slot controls.
#pragma once
#include "../NjoPages.h"
#include "../NjoMemory.h"
#include "../NjoEq.h"

namespace njo
{
    class EqEditor : public juce::Component, private juce::Timer, private Ctx::Listener, private juce::ChangeListener
    {
    public:
        EqEditor (Ctx&, SoundMemory&);
        ~EqEditor() override;
        void setSlot (int globalSlot, int paramBase);     // the slot to edit and the id of its Type parameter
        void paint (juce::Graphics&) override;
        void resized() override;
        void mouseMove (const juce::MouseEvent&) override;
        void mouseExit (const juce::MouseEvent&) override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;
        void mouseUp (const juce::MouseEvent&) override;
        void mouseDoubleClick (const juce::MouseEvent&) override;
        void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;
        struct Impl; std::unique_ptr<Impl> impl;
    private:
        void timerCallback() override;
        void paramChanged (int num, float v) override;
        void changeListenerCallback (juce::ChangeBroadcaster*) override;
    };
}
