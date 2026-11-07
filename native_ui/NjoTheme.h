// Colours, fonts and drawing helpers shared by all widgets (dark steel + red, like the web UI).
#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

namespace njo::theme
{
    inline const juce::Colour bg    { 0xff0a0c0d }, panel { 0xff201c17 }, panel2 { 0xff2c2720 }, steel { 0xff423b30 };
    inline const juce::Colour ink   { 0xffddd6d2 }, dim { 0xff95886e }, line { 0xff524a3c }, deep { 0xff080b04 };
    inline const juce::Colour red   { 0xffa3ff3a }, orange { 0xffff7a45 }, glow { 0x8ca3ff3a }, redDark { 0xff60a314 };
    inline const juce::Colour blue  { 0xff59b7ff };

    juce::Font font (float height, bool bold = false);
    juce::Font impact (float height);          // heading face
    juce::Font mono (float height, bool bold = false);

    // draws the dark rounded "card" panel background with the red hairline on top and two screws at the bottom
    juce::Path chamfer (juce::Rectangle<float> r, float tl, float tr, float br, float bl);   // plate with cut corners
    void paintCard (juce::Graphics&, juce::Rectangle<float> r, float cornerTopLeft = 10.0f);
    // the red/grey pill button background used by tabs and segment buttons
    void paintButton (juce::Graphics&, juce::Rectangle<float> r, bool on, bool hover, bool down, float corner = 3.0f);
    // a rotary knob body at r (square), value n in 0..1
    void paintKnob (juce::Graphics&, juce::Rectangle<float> r, float n, bool bipolar, bool hover, bool dragging);
    void paintLcdBox (juce::Graphics&, juce::Rectangle<float> r);
    void paintInset (juce::Graphics&, juce::Rectangle<float> r, float corner = 3.0f);   // dark recessed area (displays)
    juce::ColourGradient vertical (juce::Colour top, juce::Colour bottom, juce::Rectangle<float> r);
}
