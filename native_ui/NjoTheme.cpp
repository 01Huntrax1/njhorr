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

    // ------------------------------------------------------------------ textures
    namespace
    {
        float hash2 (int x, int y, int seed)
        {
            unsigned h = (unsigned) x * 374761393u + (unsigned) y * 668265263u + (unsigned) seed * 2246822519u;
            h = (h ^ (h >> 13)) * 1274126177u;
            return (float) ((h ^ (h >> 16)) & 0xffffu) / 65535.0f;
        }
        // value noise on a lattice of px * py cells that wraps around (the tile is seamless)
        float vnoise (float x, float y, int px, int py, int seed)
        {
            int x0 = (int) std::floor (x), y0 = (int) std::floor (y);
            float fx = x - (float) x0, fy = y - (float) y0;
            fx = fx * fx * (3.0f - 2.0f * fx); fy = fy * fy * (3.0f - 2.0f * fy);
            auto h = [&] (int a, int b) { return hash2 (((a % px) + px) % px, ((b % py) + py) % py, seed); };
            float a = h (x0, y0), b = h (x0 + 1, y0), c = h (x0, y0 + 1), d = h (x0 + 1, y0 + 1);
            return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fy;
        }
        juce::Colour mix (juce::Colour a, juce::Colour b, float t) { return a.interpolatedWith (b, juce::jlimit (0.0f, 1.0f, t)); }
    }

    const juce::Image& texPlate()
    {
        static juce::Image img = []
        {
            const int N = 256; juce::Image im (juce::Image::ARGB, N, N, true);
            juce::Image::BitmapData bd (im, juce::Image::BitmapData::writeOnly);
            const juce::Colour dark (0xff0a0b0b), mid (0xff1a1c1d), brass (0xff3e4145);
            for (int y = 0; y < N; ++y)
                for (int x = 0; x < N; ++x)
                {
                    float u = (float) x / N, v = (float) y / N;
                    float streak = vnoise (u * 3.0f, v * 160.0f, 3, 160, 11);       // brushed: long horizontal fibres
                    float streak2 = vnoise (u * 9.0f, v * 80.0f, 9, 80, 12);
                    float blotch = vnoise (u * 4.0f, v * 4.0f, 4, 4, 13);            // forged unevenness
                    float grain = hash2 (x, y, 14);
                    float L = 0.42f + 0.26f * (streak - 0.5f) + 0.18f * (streak2 - 0.5f) + 0.30f * (blotch - 0.5f) + 0.10f * (grain - 0.5f);
                    float pit = hash2 (x / 3, y / 3, 15) > 0.985f ? -0.25f : 0.0f;   // pits
                    L = juce::jlimit (0.0f, 1.0f, L + pit);
                    auto col = L < 0.5f ? mix (dark, mid, L * 2.0f) : mix (mid, brass, (L - 0.5f) * 1.6f);
                    bd.setPixelColour (x, y, col);
                }
            return im;
        }();
        return img;
    }

    const juce::Image& texScales()   // brushed steel / aluminium (the name is kept: it is the window background texture)
    {
        static juce::Image img = []
        {
            const int N = 256; juce::Image im (juce::Image::ARGB, N, N, true);
            juce::Image::BitmapData bd (im, juce::Image::BitmapData::writeOnly);
            const juce::Colour lo (0xff2a2d31), mid (0xff4a4f55), hi (0xff868c94);
            for (int y = 0; y < N; ++y)
                for (int x = 0; x < N; ++x)
                {
                    float u = (float) x / N, v = (float) y / N;
                    float f1 = vnoise (u * 2.0f, v * 200.0f, 2, 200, 51);    // long horizontal brushing
                    float f2 = vnoise (u * 6.0f, v * 100.0f, 6, 100, 52);
                    float f3 = vnoise (u * 24.0f, v * 220.0f, 24, 220, 53);
                    float cloud = vnoise (u * 3.0f, v * 3.0f, 3, 3, 54);     // soft sheen
                    float L = 0.45f + 0.20f * (f1 - 0.5f) + 0.16f * (f2 - 0.5f) + 0.12f * (f3 - 0.5f) + 0.22f * (cloud - 0.5f) + 0.05f * (hash2 (x, y, 55) - 0.5f);
                    L = juce::jlimit (0.0f, 1.0f, L);
                    bd.setPixelColour (x, y, L < 0.5f ? mix (lo, mid, L * 2.0f) : mix (mid, hi, (L - 0.5f) * 2.0f));
                }
            return im;
        }();
        return img;
    }

    const juce::Image& texPlasma()
    {
        static juce::Image img = []
        {
            const int N = 128; juce::Image im (juce::Image::ARGB, N, N, true);
            juce::Image::BitmapData bd (im, juce::Image::BitmapData::writeOnly);
            const juce::Colour deepG (0xff520904), midG (0xffc41f14), hotG (0xffff7d73);
            for (int y = 0; y < N; ++y)
                for (int x = 0; x < N; ++x)
                {
                    float u = (float) x / N, v = (float) y / N;
                    float n = 0.55f * vnoise (u * 4.0f, v * 4.0f, 4, 4, 31) + 0.30f * vnoise (u * 8.0f, v * 8.0f, 8, 8, 32) + 0.15f * vnoise (u * 16.0f, v * 16.0f, 16, 16, 33);
                    float ridge = 1.0f - std::abs (2.0f * n - 1.0f);                  // energy veins
                    ridge = ridge * ridge * ridge;
                    float L = 0.30f + 0.50f * n + 0.55f * ridge;
                    auto col = L < 0.6f ? mix (deepG, midG, L / 0.6f) : mix (midG, hotG, (L - 0.6f) / 0.5f);
                    bd.setPixelColour (x, y, col);
                }
            return im;
        }();
        return img;
    }

    const juce::Image& texGlass()
    {
        static juce::Image img = []
        {
            const int N = 64; juce::Image im (juce::Image::ARGB, N, N, true);
            juce::Image::BitmapData bd (im, juce::Image::BitmapData::writeOnly);
            for (int y = 0; y < N; ++y)
                for (int x = 0; x < N; ++x)
                {
                    float n = vnoise ((float) x / 8.0f, (float) y / 8.0f, 8, 8, 41) * 0.6f + hash2 (x, y, 42) * 0.4f;
                    bool line = (y % 4) == 0;
                    bd.setPixelColour (x, y, mix (juce::Colour (0xff070303), juce::Colour (0xff200a09), n * (line ? 0.5f : 1.0f)));
                }
            return im;
        }();
        return img;
    }

    void fillPlate (juce::Graphics& g, const juce::Path& p, juce::Rectangle<float> r, float shade)
    {
        g.saveState();
        g.setTiledImageFill (texPlate(), (int) r.getX() * 3, (int) r.getY() * 5, 1.0f);
        g.fillPath (p);
        g.setGradientFill (juce::ColourGradient (juce::Colours::white.withAlpha (0.07f), r.getX(), r.getY(), juce::Colours::black.withAlpha (0.52f + 0.3f * shade), r.getX(), r.getBottom(), false));
        g.fillPath (p);
        g.restoreState();
    }

    void paintBackground (juce::Graphics& g, juce::Rectangle<int> r)
    {
        g.setTiledImageFill (texScales(), 0, 0, 1.0f);
        g.fillRect (r);
        g.setGradientFill (juce::ColourGradient (juce::Colours::transparentBlack, r.getCentreX() * 1.0f, r.getCentreY() * 1.0f, juce::Colours::black.withAlpha (0.45f), 0.0f, 0.0f, true));   // vignette
        g.fillRect (r);
    }

    juce::ColourGradient vertical (juce::Colour top, juce::Colour bottom, juce::Rectangle<float> r)
    {
        return juce::ColourGradient (top, r.getX(), r.getY(), bottom, r.getX(), r.getBottom(), false);
    }

    // a plate with cut (chamfered) corners: tl, tr, br, bl = size of the cut
    juce::Path chamfer (juce::Rectangle<float> r, float tl, float tr, float br, float bl)
    {
        juce::Path p;
        p.startNewSubPath (r.getX() + tl, r.getY());
        p.lineTo (r.getRight() - tr, r.getY());
        p.lineTo (r.getRight(), r.getY() + tr);
        p.lineTo (r.getRight(), r.getBottom() - br);
        p.lineTo (r.getRight() - br, r.getBottom());
        p.lineTo (r.getX() + bl, r.getBottom());
        p.lineTo (r.getX(), r.getBottom() - bl);
        p.lineTo (r.getX(), r.getY() + tl);
        p.closeSubPath();
        return p;
    }

    void paintCard (juce::Graphics& g, juce::Rectangle<float> r, float cornerTL)
    {
        const float cut = juce::jlimit (6.0f, 16.0f, cornerTL * 1.3f);
        auto p = chamfer (r, cut, 3.0f, cut, 3.0f);
        // hammered bronze plate
        fillPlate (g, p, r);
        g.setColour (juce::Colour (0xff090a0b));   // shadow line inside the frame
        g.strokePath (chamfer (r.reduced (3.0f), cut - 2.0f, 2.0f, cut - 2.0f, 2.0f), juce::PathStrokeType (1.0f));
        g.setColour (juce::Colour (0xff52565c));   // bronze frame
        g.strokePath (p, juce::PathStrokeType (1.3f));
        g.setColour (juce::Colours::white.withAlpha (0.05f));
        g.drawHorizontalLine ((int) r.getY() + 1, r.getX() + cut, r.getRight() - 4.0f);

        // plasma line along the top, with a stepped notch like a claw cut
        float w = r.getWidth();
        g.setGradientFill (juce::ColourGradient (juce::Colours::transparentBlack, r.getX() + cut, 0, redDark, r.getX() + w * 0.14f, 0, false));
        g.fillRect (juce::Rectangle<float> (r.getX() + cut, r.getY(), w * 0.14f - cut + 2.0f, 2.0f));
        g.setColour (red.withAlpha (0.85f));
        g.fillRect (juce::Rectangle<float> (r.getX() + w * 0.14f, r.getY(), w * 0.5f, 2.0f));
        juce::Path claw;   // three descending steps
        float cx = r.getX() + w * 0.64f;
        claw.startNewSubPath (cx, r.getY()); claw.lineTo (cx + 10.0f, r.getY()); claw.lineTo (cx + 14.0f, r.getY() + 3.0f);
        claw.lineTo (cx + 24.0f, r.getY() + 3.0f); claw.lineTo (cx + 28.0f, r.getY() + 6.0f); claw.lineTo (cx + 42.0f, r.getY() + 6.0f);
        g.setColour (red.withAlpha (0.8f)); g.strokePath (claw, juce::PathStrokeType (1.4f));
        g.setGradientFill (juce::ColourGradient (redDark, cx + 42.0f, 0, juce::Colours::transparentBlack, r.getRight() - 6.0f, 0, false));
        g.fillRect (juce::Rectangle<float> (cx + 42.0f, r.getY() + 5.0f, juce::jmax (0.0f, r.getRight() - 6.0f - (cx + 42.0f)), 2.0f));

        // etched cut on the chamfer
        g.setColour (red.withAlpha (0.55f));
        g.drawLine (r.getX() + 1.5f, r.getY() + cut + 5.0f, r.getX() + cut + 5.0f, r.getY() + 1.5f, 1.0f);

        // row of glyph marks along the bottom edge (decoration: short bars of varying length in groups)
        if (r.getHeight() > 200.0f)
        {
            float x0 = juce::jmax (r.getX() + 22.0f, r.getRight() - 150.0f), x = x0, y = r.getBottom() - 5.0f; unsigned seed = (unsigned) (w * 7.0f) + 13u;
            g.setColour (juce::Colour (0xff52565c).withAlpha (0.55f));
            while (x < r.getRight() - 22.0f && (x - x0) < 126.0f)
            {
                seed = seed * 1664525u + 1013904223u;
                float len = 2.0f + (float) ((seed >> 24) % 4) * 2.0f;
                g.fillRect (x, y - (((seed >> 20) & 1) ? 2.0f : 0.0f), 1.6f, ((seed >> 20) & 1) ? 4.0f : 2.0f);
                g.fillRect (x + 2.4f, y, len, 1.2f);
                x += len + 6.0f + (float) ((seed >> 16) % 3) * 2.0f;
            }
        }
        // rivets
        for (float sx : { r.getX() + 7.0f + 0.0f * cut, r.getRight() - 7.0f })
        {
            g.setColour (juce::Colour (0xff090a0b)); g.fillEllipse (sx - 3.0f, r.getBottom() - 10.0f, 6.0f, 6.0f);
            g.setGradientFill (juce::ColourGradient (juce::Colour (0xffb59a62), sx - 1.0f, r.getBottom() - 8.5f, juce::Colour (0xff36393c), sx + 1.5f, r.getBottom() - 5.5f, true));
            g.fillEllipse (sx - 2.0f, r.getBottom() - 9.0f, 4.0f, 4.0f);
        }
    }

    void paintButton (juce::Graphics& g, juce::Rectangle<float> r, bool on, bool hover, bool down, float)
    {
        const float c = juce::jlimit (2.0f, 6.0f, r.getHeight() * 0.28f);
        auto p = chamfer (r, c, 0.0f, c, 0.0f);
        if (on)
        {
            g.setTiledImageFill (texPlasma(), (int) r.getX(), (int) r.getY(), 1.0f); g.fillPath (p);
            g.setGradientFill (vertical (juce::Colours::white.withAlpha (0.10f), juce::Colours::black.withAlpha (0.45f), r)); g.fillPath (p);
            g.setColour (juce::Colour (0xffff9c95)); g.strokePath (p, juce::PathStrokeType (1.0f));
            g.setColour (juce::Colours::white.withAlpha (0.35f)); g.drawHorizontalLine ((int) r.getY() + 1, r.getX() + c, r.getRight() - 2);
            g.setColour (red.withAlpha (0.18f)); g.strokePath (p, juce::PathStrokeType (3.5f));   // plasma glow
        }
        else
        {
            fillPlate (g, p, r, down ? 0.8f : 0.2f);
            g.setColour (hover ? red : juce::Colour (0xff52565c)); g.strokePath (p, juce::PathStrokeType (1.0f));
            g.setColour (juce::Colours::white.withAlpha (0.08f)); g.drawHorizontalLine ((int) r.getY() + 1, r.getX() + c, r.getRight() - 2);
        }
    }

    void paintKnob (juce::Graphics& g, juce::Rectangle<float> r, float n, bool bipolar, bool hover, bool dragging)
    {
        auto c = r.getCentre();
        float rad = juce::jmin (r.getWidth(), r.getHeight()) * 0.5f;
        float a0 = juce::MathConstants<float>::pi * 1.25f, span = juce::MathConstants<float>::pi * 1.5f;
        // etched scale: radial dashes, longer every fifth
        for (int i = 0; i <= 20; ++i)
        {
            float a = a0 + span * (float) i / 20.0f, len = (i % 5 == 0) ? 3.4f : 1.8f;
            float s = std::sin (a), co = -std::cos (a), ro = rad - 0.4f, ri = ro - len;
            g.setColour (juce::Colour (0xff52565c).withAlpha (i % 5 == 0 ? 0.95f : 0.6f));
            g.drawLine (c.x + s * ri, c.y + co * ri, c.x + s * ro, c.y + co * ro, 1.0f);
        }
        // value arc (plasma, with a soft glow)
        float rr = rad - 5.2f;
        float z = bipolar ? 0.5f : 0.0f;
        juce::Path arc;
        float aA = juce::jmin (z, n), aB = juce::jmax (z, n);
        if (aB - aA > 0.002f)
        {
            arc.addCentredArc (c.x, c.y, rr, rr, 0.0f, a0 + span * aA, a0 + span * aB, true);
            g.setColour (red.withAlpha (0.18f));
            g.strokePath (arc, juce::PathStrokeType (4.6f, juce::PathStrokeType::curved, juce::PathStrokeType::butt));
            g.setColour (red.withAlpha (0.95f));
            g.strokePath (arc, juce::PathStrokeType (1.8f, juce::PathStrokeType::curved, juce::PathStrokeType::butt));
        }
        // body: a hexagonal bronze bezel with a dark dished centre
        auto body = r.reduced (rad * 0.26f);
        float br = body.getWidth() * 0.5f;
        juce::Path hex;
        for (int i = 0; i < 6; ++i)
        {
            float a = juce::MathConstants<float>::pi / 6.0f + (float) i * juce::MathConstants<float>::pi / 3.0f;
            float x = c.x + std::sin (a) * br * 1.08f, y = c.y - std::cos (a) * br * 1.08f;
            if (i == 0) hex.startNewSubPath (x, y); else hex.lineTo (x, y);
        }
        hex.closeSubPath();
        g.setTiledImageFill (texPlate(), (int) c.x * 7, (int) c.y * 3, 1.0f); g.fillPath (hex);
        g.setGradientFill (juce::ColourGradient (juce::Colour (0xff757a82).withAlpha (0.55f), c.x - br * 0.8f, c.y - br, juce::Colours::black.withAlpha (0.4f), c.x + br * 0.6f, c.y + br, false));
        g.fillPath (hex);
        g.setColour (dragging ? red : (hover ? juce::Colour (0xffd44d43) : juce::Colour (0xff080808)));
        g.strokePath (hex, juce::PathStrokeType (1.2f));
        auto dish = body.reduced (br * 0.28f);
        g.setGradientFill (juce::ColourGradient (juce::Colour (0xff17181a), dish.getCentreX() - dish.getWidth() * 0.2f, dish.getY(), juce::Colour (0xff040404), dish.getCentreX() + dish.getWidth() * 0.2f, dish.getBottom(), false));
        g.fillEllipse (dish);
        g.setColour (juce::Colours::white.withAlpha (0.10f)); g.drawEllipse (dish, 0.8f);
        // indicator: a blade from the dish towards the rim
        float a = a0 + span * n;
        float s = std::sin (a), co = -std::cos (a);
        juce::Path blade;
        float r0 = br * 0.18f, r1 = br * 1.02f, hw = 1.7f;
        blade.startNewSubPath (c.x + s * r1, c.y + co * r1);
        blade.lineTo (c.x + s * r0 + co * hw, c.y + co * r0 - s * hw);
        blade.lineTo (c.x + s * r0 - co * hw, c.y + co * r0 + s * hw);
        blade.closeSubPath();
        g.setColour (red); g.fillPath (blade);
    }

    void paintLcdBox (juce::Graphics& g, juce::Rectangle<float> r)
    {
        auto p = chamfer (r, 6.0f, 0.0f, 6.0f, 0.0f);
        g.setTiledImageFill (texGlass(), (int) r.getX(), (int) r.getY(), 1.0f); g.fillPath (p);
        g.setColour (juce::Colours::black.withAlpha (0.35f));   // scan lines
        for (float y = r.getY() + 2.0f; y < r.getBottom(); y += 3.0f) g.drawHorizontalLine ((int) y, r.getX() + 4.0f, r.getRight() - 4.0f);
        g.setColour (juce::Colour (0xff52565c)); g.strokePath (p, juce::PathStrokeType (1.2f));
    }

    void paintInset (juce::Graphics& g, juce::Rectangle<float> r, float corner)
    {
        const float c = juce::jlimit (2.0f, 6.0f, corner + 1.0f);
        auto p = chamfer (r, c, 0.0f, c, 0.0f);
        g.setTiledImageFill (texGlass(), (int) r.getX(), (int) r.getY(), 1.0f); g.fillPath (p);
        g.setColour (juce::Colour (0xff6a1e18)); g.strokePath (chamfer (r.reduced (0.5f), c, 0.0f, c, 0.0f), juce::PathStrokeType (1.0f));
    }
}
