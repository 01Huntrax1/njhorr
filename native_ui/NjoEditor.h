// The whole plugin UI as one component of the fixed size 1180 x 760; the plugin editor scales it to the window.
#pragma once
#include "NjoPages.h"
#include "NjoManager.h"

namespace njo
{
    class EditorContent : public juce::Component, public juce::DragAndDropContainer, private juce::Timer
    {
    public:
        EditorContent (Backend&);
        ~EditorContent() override;

        void paint (juce::Graphics&) override;
        void paintOverChildren (juce::Graphics&) override;
        void resized() override;

        enum Group { Synth = 0, Effects = 1, Modulation = 2 };
        void setGroup (Group);
        void setSynthPage (int page);       // 0-5 = OSC 1-6, 6 = FM / PM, 7 = Global
        Group group() const { return currentGroup; }
        int synthPage() const { return currentSynthPage; }
        Ctx& context() { return ctx; }
        void restore() { memory.restore(); }   // once after the editor opens: stored sounds -> DSP

        std::function<void (float scale)> onScaleRequested;   // the size dropdown (0.75 ... 2.0)

        bool isDragAndDropActive() const { return juce::DragAndDropContainer::isDragAndDropActive(); }

    private:
        void timerCallback() override;
        void layoutAll();

        Ctx ctx;
        SoundMemory memory;
        Group currentGroup = Synth; int currentSynthPage = 0;
        juce::OwnedArray<OscPage> osc;
        FmPage fm; GlobalPage glob; FxPage fx;
        ModEditors editors, editorsFull; MatrixPanel matrix;
        ManagerBar manager;
        juce::OwnedArray<juce::TextButton> railButtons, subButtons;   // plain buttons, painted by us
        struct Impl; std::unique_ptr<Impl> impl;
        juce::String lcdName = "--", lcdValue = "--", status;
        double statusUntil = 0;
        bool stripOpen = true;
        float vuLevel = 0;
        friend struct Impl;
    };
}
