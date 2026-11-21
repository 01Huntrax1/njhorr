// Wavetable editor of the LFOs (wave "Table"): all frames of the selected LFO as a waterfall, freehand drawing of the selected frame,
// frame add / delete, generators and tools (normalize, smooth, invert, reverse, morph, from the drawn shape).
#pragma once
#include "../NjoPages.h"
#include "../NjoLfoTable.h"

namespace njo
{
    class LfoTableEditor : public juce::Component
    {
    public:
        explicit LfoTableEditor (Ctx&);
        ~LfoTableEditor() override;
        void open();
        std::function<void()> onClose;
        void paint (juce::Graphics&) override;
        void resized() override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;
        void mouseUp (const juce::MouseEvent&) override;
        void mouseMove (const juce::MouseEvent&) override;
        struct Impl; std::unique_ptr<Impl> impl;
    };
}
