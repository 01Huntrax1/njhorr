// juce::AudioProcessorEditor hosting the native UI. Scales the fixed 1180 x 760 layout to the window size.
#pragma once
#include <juce_audio_processors/juce_audio_processors.h>
#include "NjoPatchBackend.h"
#include "NjoEditor.h"

namespace njo
{
    class PluginEditor : public juce::AudioProcessorEditor
    {
    public:
        PluginEditor (juce::AudioProcessor& proc, cmaj::Patch& patch, int startWidth = 0)
            : juce::AudioProcessorEditor (proc), backend (patch), content (backend)
        {
            addAndMakeVisible (content);
            content.onScaleRequested = [this] (float s) { setSize (juce::roundToInt (logicalW * s), juce::roundToInt (logicalH * s)); };
            content.restore();

            setResizable (true, true);
            setResizeLimits ((int) (logicalW * 0.5), (int) (logicalH * 0.5), (int) (logicalW * 3), (int) (logicalH * 3));
            if (auto* c = getConstrainer())
                c->setFixedAspectRatio (logicalW / logicalH);

            int w = startWidth >= 400 ? startWidth : (int) logicalW;
            setSize (w, juce::roundToInt (w * logicalH / logicalW));
        }

        void resized() override
        {
            const float s = (float) getWidth() / logicalW;
            content.setBounds (0, 0, (int) logicalW, (int) logicalH);
            content.setTransform (juce::AffineTransform::scale (s));
        }

        void paint (juce::Graphics& g) override { g.fillAll (juce::Colour (0xff0b0b0d)); }

    private:
        static constexpr float logicalW = 1180.0f, logicalH = 760.0f;
        PatchBackend backend;
        EditorContent content;
    };
}
