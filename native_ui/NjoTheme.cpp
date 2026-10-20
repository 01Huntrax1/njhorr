#include "NjoTheme.h"

namespace njo::theme
{
    juce::Font font (float h, bool bold)
    {
        juce::FontOptions o (juce::Font::getDefaultSansSerifFontName(), h, bold ? juce::Font::bold : juce::Font::plain);
        return juce::Font (o);
    }
    juce::Font impact (float h) { return juce::Font (juce::FontOptions (juce::Font::getDefaultSansSerifFontName(), h, juce::Font::bold)); }
    juce::Font mono (float h, bool bold)
    {
        return juce::Font (juce::FontOptions (juce::Font::getDefaultMonospacedFontName(), h, bold ? juce::Font::bold : juce::Font::plain));
    }

    juce::ColourGradient vertical (juce::Colour top, juce::Colour bottom, juce::Rectangle<float> r)
    {
        return juce::ColourGradient (top, r.getX(), r.getY(), bottom, r.getX(), r.getBottom(), false);
    }

    void paintCard (juce::Graphics& g, juce::Rectangle<float> r, float cornerTL)
    {
        juce::Path p;
        p.addRoundedRectangle (r.getX(), r.getY(), r.getWidth(), r.getHeight(), cornerTL, 2.0f, true, false, false, true);
        p.setUsingNonZeroWinding (true);
        g.setGradientFill (vertical (juce::Colour (0xff292c31), juce::Colour (0xff1f2225), r));
        g.fillPath (p);
        g.setColour (line);
        g.strokePath (p, juce::PathStrokeType (1.0f));
        // red top hairline
        g.setGradientFill (juce::ColourGradient (juce::Colours::transparentBlack, r.getX(), 0, juce::Colour (0xff7a100c), r.getX() + r.getWidth() * 0.12f, 0, false));
        g.fillRect (juce::Rectangle<float> (r.getX() + 6, r.getY(), r.getWidth() * 0.12f, 3.0f));
        g.setColour (red.withAlpha (0.8f));
        g.fillRect (juce::Rectangle<float> (r.getX() + r.getWidth() * 0.12f, r.getY(), r.getWidth() * 0.76f, 2.0f));
        g.setGradientFill (juce::ColourGradient (juce::Colour (0xff7a100c), r.getX() + r.getWidth() * 0.88f, 0, juce::Colours::transparentBlack, r.getRight() - 6, 0, false));
        g.fillRect (juce::Rectangle<float> (r.getX() + r.getWidth() * 0.88f, r.getY(), r.getWidth() * 0.12f - 6, 3.0f));
        // screws
        for (float sx : { r.getX() + 6.0f, r.getRight() - 6.0f })
        {
            g.setColour (juce::Colour (0xff17181a)); g.fillEllipse (sx - 2.6f, r.getBottom() - 8.6f, 5.2f, 5.2f);
            g.setColour (juce::Colour (0xff9aa0a8)); g.fillEllipse (sx - 1.4f, r.getBottom() - 7.4f, 2.8f, 2.8f);
        }
    }

    void paintButton (juce::Graphics& g, juce::Rectangle<float> r, bool on, bool hover, bool down, float corner)
    {
        juce::Path p; p.addRoundedRectangle (r.getX(), r.getY(), r.getWidth(), r.getHeight(), corner, 1.0f, true, false, true, false);
        if (on)
        {
            g.setGradientFill (vertical (juce::Colour (0xffff4a3a), juce::Colour (0xffa3140c), r)); g.fillPath (p);
            g.setColour (juce::Colour (0xffff6a5c)); g.strokePath (p, juce::PathStrokeType (1.0f));
            g.setColour (juce::Colours::white.withAlpha (0.3f)); g.drawHorizontalLine ((int) r.getY() + 1, r.getX() + 3, r.getRight() - 3);
        }
        else
        {
            g.setGradientFill (vertical (down ? juce::Colour (0xff202124) : juce::Colour (0xff303134), juce::Colour (0xff17181a), r)); g.fillPath (p);
            g.setColour (hover ? red : juce::Colour (0xff4c4d51)); g.strokePath (p, juce::PathStrokeType (1.0f));
            g.setColour (juce::Colours::white.withAlpha (0.1f)); g.drawHorizontalLine ((int) r.getY() + 1, r.getX() + 3, r.getRight() - 3);
        }
    }

    void paintKnob (juce::Graphics& g, juce::Rectangle<float> r, float n, bool bipolar, bool hover, bool dragging)
    {
        auto c = r.getCentre();
        float rad = juce::jmin (r.getWidth(), r.getHeight()) * 0.5f;
        float a0 = juce::MathConstants<float>::pi * 1.25f, span = juce::MathConstants<float>::pi * 1.5f;
        // dotted ring
        g.setColour (juce::Colour (0xff4a3a38));
        for (int i = 0; i <= 20; ++i)
        {
            float a = a0 + span * (float) i / 20.0f;
            float x = c.x + std::sin (a) * (rad - 1.2f), y = c.y - std::cos (a) * (rad - 1.2f);
            g.fillEllipse (x - 0.9f, y - 0.9f, 1.8f, 1.8f);
        }
        // value arc
        float rr = rad - 1.2f;
        float z = bipolar ? 0.5f : 0.0f;
        juce::Path arc;
        float aA = juce::jmin (z, n), aB = juce::jmax (z, n);
        if (aB - aA > 0.002f)
        {
            arc.addCentredArc (c.x, c.y, rr, rr, 0.0f, a0 + span * aA, a0 + span * aB, true);
            g.setColour (red.withAlpha (0.9f));
            g.strokePath (arc, juce::PathStrokeType (2.2f, juce::PathStrokeType::curved, juce::PathStrokeType::rounded));
        }
        // body
        auto body = r.reduced (rad * 0.2f);
        g.setGradientFill (juce::ColourGradient (juce::Colour (0xff5b5d62), body.getCentreX() - body.getWidth() * 0.2f, body.getY() + body.getHeight() * 0.1f, juce::Colour (0xff1a1b1e), body.getCentreX() + body.getWidth() * 0.2f, body.getBottom(), true));
        g.fillEllipse (body);
        g.setColour (dragging ? red : (hover ? juce::Colour (0xff8a2a24) : juce::Colour (0xff060606)));
        g.drawEllipse (body, 1.2f);
        g.setColour (juce::Colours::white.withAlpha (0.18f));
        g.drawEllipse (body.reduced (1.2f), 0.8f);
        // indicator
        float a = a0 + span * n;
        float x0 = c.x + std::sin (a) * body.getWidth() * 0.2f, y0 = c.y - std::cos (a) * body.getWidth() * 0.2f;
        float x1 = c.x + std::sin (a) * body.getWidth() * 0.46f, y1 = c.y - std::cos (a) * body.getWidth() * 0.46f;
        g.setColour (red);
        g.drawLine (x0, y0, x1, y1, 2.4f);
    }

    void paintLcdBox (juce::Graphics& g, juce::Rectangle<float> r)
    {
        g.setColour (juce::Colour (0xff110505)); g.fillRoundedRectangle (r, 2.0f);
        g.setColour (line); g.drawRoundedRectangle (r, 2.0f, 1.0f);
    }

    void paintInset (juce::Graphics& g, juce::Rectangle<float> r, float corner)
    {
        g.setColour (juce::Colour (0xff0d0404)); g.fillRoundedRectangle (r, corner);
        g.setColour (juce::Colour (0xff7a1d18)); g.drawRoundedRectangle (r.reduced (0.5f), corner, 1.0f);
    }
}
