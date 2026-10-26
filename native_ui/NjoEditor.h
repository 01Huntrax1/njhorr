// The whole plugin UI as one component of the fixed size 1180 x 760; the plugin editor scales it to the window.
#pragma once
#include "NjoPages.h"
#include "NjoManager.h"

namespace njo
{
    class EditorContent : public juce::Component, public juce::DragAndDropContainer, private juce::Timer
    {
    public:
        EditorContent (Backend&, SoundMemory* sharedMemory = nullptr);   // sharedMemory: owned by the plugin instance, survives the window
        ~EditorContent() override;

        void paint (juce::Graphics&) override;
        void paintOverChildren (juce::Graphics&) override;
        void resized() override;

        enum Group { Synth = 0, Effects = 1, Modulation = 2 };
        void setGroup (Group);
        void setStripTab (int t) { stripTab = t; layoutAll(); }   // bottom strip: 0 = MOD, 1 = FREQ
        void setModTab (int t) { modTab = t; layoutAll(); }       // modulation page: 0 = ENV / LFO, 1 = FREQ
        void setSynthPage (int page);       // 0-5 = OSC 1-6, 6 = FM / PM / PD, 7 = RM / AM, 8 = Global, 9-14 = filter page of OSC 1-6, 15-20 = distortion page of OSC 1-6
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
        std::unique_ptr<SoundMemory> ownMemory;
        SoundMemory& memory;
        Group currentGroup = Synth; int currentSynthPage = 0;
        juce::OwnedArray<OscPage> osc, fltPages, distPages;
        int fltOsc = 0, distOsc = 0;       // the oscillator the FILTER / DIST tabs reopen
        FmPage fm; FmPage fmRm; GlobalPage glob; FxPage fx;
        ModEditors editors, editorsFull; FreqEditor freq, freqFull; MatrixPanel matrix;
        int stripTab = 0, modTab = 0;       // 0 = envelopes / LFOs, 1 = Freq modulators
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
