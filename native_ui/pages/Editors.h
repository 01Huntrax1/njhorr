// Full-page editors opened from the OSC pages: the Wavefilter / Wavedistortion table editor (draw the frames of the table) and the resonator mode editor
// (frequency, gain and decay of each of the 16 modes of the Physical source A / B and of the Resonator stage).
#pragma once
#include "../NjoPages.h"
#include "../NjoMemory.h"

namespace njo
{
    class TableEditor : public juce::Component, public juce::FileDragAndDropTarget, private juce::Timer, private Ctx::Listener, private juce::ChangeListener
    {
    public:
        TableEditor (Ctx&, SoundMemory&, int osc, bool filter);
        ~TableEditor() override;
        void open();                                 // takes the table from the memory (or the built-in one), shows the editor
        void testApply (const juce::String& generator, int frame, int harmonic = 0, float harmonicValue = 0.0f);   // test hook: generator on a frame, then one Chebyshev term
        std::function<void()> onClose;
        void paint (juce::Graphics&) override;
        void resized() override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;
        void mouseUp (const juce::MouseEvent&) override;
        void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;
        bool isInterestedInFileDrag (const juce::StringArray&) override;   // a dropped table / wave file replaces the table
        void fileDragEnter (const juce::StringArray&, int, int) override;
        void fileDragExit (const juce::StringArray&) override;
        void filesDropped (const juce::StringArray&, int, int) override;
        struct Impl; std::unique_ptr<Impl> impl;
    private:
        void timerCallback() override;
        void paramChanged (int num, float v) override;
        void changeListenerCallback (juce::ChangeBroadcaster*) override;
    };

    class ModeEditor : public juce::Component, private juce::Timer, private Ctx::Listener
    {
    public:
        ModeEditor (Ctx&, SoundMemory&, int osc);
        ~ModeEditor() override;
        void open (int set);                         // 0 = Physical A, 1 = Physical B, 2 = Resonator stage
        std::function<void()> onClose;
        void paint (juce::Graphics&) override;
        void resized() override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;
        void mouseUp (const juce::MouseEvent&) override;
        void mouseDoubleClick (const juce::MouseEvent&) override;
        struct Impl; std::unique_ptr<Impl> impl;
    private:
        void timerCallback() override;
        void paramChanged (int num, float v) override;
    };
}
