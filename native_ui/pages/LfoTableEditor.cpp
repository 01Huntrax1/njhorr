#include "LfoTableEditor.h"
#include "../NjoLfo.h"
#include "../NjoLfo2.h"
#include <cmath>
#include <random>

namespace njo
{
    using namespace theme;

    struct LfoTableEditor::Impl
    {
        Ctx& ctx; LfoTableEditor& owner;
        int sel = 0, hover = -1, lastIdx = -1; float lastVal = 0; bool drawing = false;
        juce::Rectangle<int> canvas, water, chipRow;
        struct Btn { juce::String text; juce::Rectangle<int> r; std::function<void()> fn; };
        std::vector<Btn> btns;
        Impl (Ctx& c, LfoTableEditor& o) : ctx (c), owner (o) {}
        LfoTables& T() { if (! ctx.lfoTables) ctx.lfoTables = std::make_shared<LfoTables> (ctx); return *ctx.lfoTables; }
        int lfo() const { return ctx.selectedLfo; }
        int n() { return T().count (lfo()); }
        std::vector<float>& cur() { sel = juce::jlimit (0, n() - 1, sel); return T().frame (lfo(), sel); }
        float pos() const { return ctx.get (lfo2::lfoId (ctx.selectedLfo, 8)); }
        void apply (std::function<void (std::vector<float>&)> fn) { fn (cur()); T().commitFrame (lfo(), sel, true); owner.repaint(); }
        void applyAll() { T().commitAll (lfo()); owner.repaint(); }

        float px (float x) const { return (float) canvas.getX() + x * (float) canvas.getWidth(); }
        float py (float y) const { return (float) canvas.getCentreY() - y * (float) canvas.getHeight() * 0.5f * 0.92f; }
        float iy (float Y) const { return juce::jlimit (-1.0f, 1.0f, ((float) canvas.getCentreY() - Y) / ((float) canvas.getHeight() * 0.5f * 0.92f)); }

        void buildButtons()
        {
            btns.clear();
            auto add = [&] (const char* t, std::function<void()> f) { btns.push_back ({ t, {}, std::move (f) }); };
            add ("+ FRAME", [this] { if (n() < LfoTables::maxFrames) { T().insertCopy (lfo(), sel); ++sel; applyAll(); } });
            add ("- FRAME", [this] { if (n() > 1) { T().erase (lfo(), sel); sel = juce::jmax (0, sel - 1); applyAll(); } });
            add ("SINE",  [this] { apply ([] (std::vector<float>& d) { d = LfoTables::defaultFrame (0); }); });
            add ("TRI",   [this] { apply ([] (std::vector<float>& d) { d = LfoTables::defaultFrame (1); }); });
            add ("SAW",   [this] { apply ([] (std::vector<float>& d) { d = LfoTables::defaultFrame (2); }); });
            add ("SQUARE",[this] { apply ([] (std::vector<float>& d) { d = LfoTables::defaultFrame (3); }); });
            add ("NOISE", [this] { apply ([] (std::vector<float>& d) { static std::mt19937 g (7); std::uniform_real_distribution<float> u (-1, 1); for (auto& v : d) v = u (g); }); });
            add ("NORMALIZE", [this] { apply ([] (std::vector<float>& d) { float m = 0; for (float v : d) m = juce::jmax (m, std::abs (v)); if (m > 1e-4f) for (auto& v : d) v /= m; }); });
            add ("SMOOTH", [this] { apply ([] (std::vector<float>& d) { for (int k = 0; k < 3; ++k) { auto c = d; for (size_t i = 0; i < d.size(); ++i) d[i] = 0.25f * c[(i + d.size() - 1) % d.size()] + 0.5f * c[i] + 0.25f * c[(i + 1) % d.size()]; } }); });
            add ("INVERT", [this] { apply ([] (std::vector<float>& d) { for (auto& v : d) v = -v; }); });
            add ("REVERSE", [this] { apply ([] (std::vector<float>& d) { std::reverse (d.begin(), d.end()); }); });
            add ("MORPH", [this]   // frames between the first and the last one become a linear blend of them
            {
                int k = n(); if (k < 3) return; auto a = T().frame (lfo(), 0), b = T().frame (lfo(), k - 1);
                for (int f = 1; f < k - 1; ++f) { float t = (float) f / (float) (k - 1); auto& d = T().frame (lfo(), f); for (size_t i = 0; i < d.size(); ++i) d[i] = a[i] + (b[i] - a[i]) * t; }
                applyAll();
            });
            add ("FROM DRAWN", [this] { apply ([this] (std::vector<float>& d) { if (ctx.lfoShapes) d = LfoShapes::table (shapes().points (lfo())); }); });
            add ("RESET", [this] { T().reset (lfo()); sel = 0; owner.repaint(); });
            add ("CLOSE", [this] { owner.setVisible (false); if (onCloseFn) onCloseFn(); });
        }
        std::function<void()> onCloseFn;
        LfoShapes& shapes() { return *ctx.lfoShapes; }

        void setVal (float X, float Y)
        {
            int i = juce::jlimit (0, 255, (int) std::floor ((X - (float) canvas.getX()) / (float) canvas.getWidth() * 256.0f));
            float v = iy (Y); auto& d = cur();
            if (lastIdx < 0) { d[(size_t) i] = v; }
            else
            {
                int a = juce::jmin (lastIdx, i), b = juce::jmax (lastIdx, i);
                for (int k = a; k <= b; ++k) { float t = b > a ? (float) (k - a) / (float) (b - a) : 1.0f; float v0 = a == lastIdx ? lastVal : v, v1 = a == lastIdx ? v : lastVal; d[(size_t) k] = v0 + (v1 - v0) * t; }
            }
            lastIdx = i; lastVal = v;
            T().commitFrame (lfo(), sel, false);
            owner.repaint();
        }
    };

    LfoTableEditor::LfoTableEditor (Ctx& c) : impl (new Impl (c, *this)) { impl->buildButtons(); impl->onCloseFn = [this] { if (onClose) onClose(); }; setVisible (false); }
    LfoTableEditor::~LfoTableEditor() = default;
    void LfoTableEditor::open() { impl->sel = 0; setVisible (true); toFront (false); resized(); repaint(); }

    void LfoTableEditor::resized()
    {
        auto& I = *impl; auto b = getLocalBounds().reduced (12, 10);
        b.removeFromTop (20);
        I.chipRow = b.removeFromTop (22); b.removeFromTop (6);
        // the buttons fill columns of whatever height is left (the editor also opens in the low bottom strip of the synth page)
        const int bw = 72, bh = 22, nB = (int) I.btns.size();
        const int rows = juce::jmax (1, (b.getHeight() + 4) / (bh + 4));
        const int cols = juce::jmax (2, (nB + rows - 1) / rows);
        auto side = b.removeFromRight (cols * (bw + 4) - 4); b.removeFromRight (10);
        const bool lowH = b.getHeight() < 190;
        I.water = lowH ? juce::Rectangle<int>() : b.removeFromBottom (juce::jmin (90, b.getHeight() / 3));
        if (! lowH) b.removeFromBottom (6);
        I.canvas = b;
        int x0 = side.getX(), y0 = side.getY();
        for (size_t k = 0; k < I.btns.size(); ++k)
            I.btns[k].r = cols == 2 ? juce::Rectangle<int> (x0 + (int) (k % 2) * (bw + 4), y0 + (int) (k / 2) * (bh + 4), bw, bh)
                                    : juce::Rectangle<int> (x0 + (int) ((int) k / rows) * (bw + 4), y0 + (int) ((int) k % rows) * (bh + 4), bw, bh);
    }

    void LfoTableEditor::paint (juce::Graphics& g)
    {
        auto& I = *impl;
        paintCard (g, getLocalBounds().toFloat());
        g.setColour (red); g.setFont (impact (11.0f));
        g.drawText ("LFO " + juce::String (I.lfo() + 1) + " WAVETABLE", 14, 6, 300, 16, juce::Justification::centredLeft);
        const int N = I.n(); I.sel = juce::jlimit (0, N - 1, I.sel);
        // frame chips
        { int cw = juce::jmin (34, (I.chipRow.getWidth() - 4 * 15) / juce::jmax (1, LfoTables::maxFrames)); float fp = I.pos() * (float) (N - 1);
          for (int f = 0; f < N; ++f)
          {
              auto r = juce::Rectangle<float> ((float) (I.chipRow.getX() + f * (cw + 4)), (float) I.chipRow.getY(), (float) cw, (float) I.chipRow.getHeight());
              paintButton (g, r, f == I.sel, false, false, 3.0f);
              g.setColour (ink); g.setFont (font (9.0f, true)); g.drawText (juce::String (f + 1), r.toNearestInt(), juce::Justification::centred);
              if (std::abs (fp - (float) f) < 0.5f) { g.setColour (juce::Colour (0xff7be07a)); g.fillRect (r.getX() + 3, r.getBottom() - 3, r.getWidth() - 6, 2.0f); }
          } }
        // canvas
        g.setColour (juce::Colour (0xff0b0404)); g.fillRoundedRectangle (I.canvas.toFloat(), 2.0f);
        for (int k = 0; k <= 8; ++k) { g.setColour (juce::Colours::white.withAlpha (k % 2 == 0 ? 0.12f : 0.05f)); g.drawVerticalLine ((int) I.px ((float) k / 8), (float) I.canvas.getY(), (float) I.canvas.getBottom()); }
        g.setColour (juce::Colours::white.withAlpha (0.22f)); g.drawHorizontalLine ((int) I.py (0), (float) I.canvas.getX(), (float) I.canvas.getRight());
        auto path = [&] (const std::vector<float>& d, juce::Rectangle<float> r, float amp)
        {
            juce::Path p;
            for (int i = 0; i <= 256; ++i) { float v = d[(size_t) (i & 255)]; float x = r.getX() + r.getWidth() * (float) i / 256.0f, y = r.getCentreY() - v * r.getHeight() * 0.5f * amp; if (i == 0) p.startNewSubPath (x, y); else p.lineTo (x, y); }
            return p;
        };
        auto cr = I.canvas.toFloat().reduced (0, 0);
        if (I.sel > 0) { g.setColour (juce::Colours::white.withAlpha (0.14f)); g.strokePath (path (I.T().frame (I.lfo(), I.sel - 1), cr, 0.92f), juce::PathStrokeType (1.2f)); }
        if (I.sel + 1 < N) { g.setColour (juce::Colours::white.withAlpha (0.14f)); g.strokePath (path (I.T().frame (I.lfo(), I.sel + 1), cr, 0.92f), juce::PathStrokeType (1.2f)); }
        auto line = path (I.T().frame (I.lfo(), I.sel), cr, 0.92f);
        juce::Path fill (line); fill.lineTo (cr.getRight(), (float) I.py (0)); fill.lineTo (cr.getX(), (float) I.py (0)); fill.closeSubPath();
        g.setColour (juce::Colour::fromFloatRGBA (1, 0.35f, 0.24f, 0.16f)); g.fillPath (fill);
        g.setColour (juce::Colour (0xffff594e)); g.strokePath (line, juce::PathStrokeType (2.0f));
        g.setColour (juce::Colours::white.withAlpha (0.4f)); g.setFont (font (9.0f));
        g.drawText ("draw with the mouse - frame " + juce::String (I.sel + 1) + " of " + juce::String (N) + " - the LFO position knob scans the frames", I.canvas.getX() + 8, I.canvas.getBottom() - 18, I.canvas.getWidth() - 16, 14, juce::Justification::centredLeft);
        // waterfall: every frame behind the next, the scan position in green
        if (! I.water.isEmpty()) { g.setColour (juce::Colour (0xff0b0404)); g.fillRoundedRectangle (I.water.toFloat(), 2.0f); }
        for (int f = I.water.isEmpty() ? -1 : N - 1; f >= 0; --f)
        {
            float t = N > 1 ? (float) f / (float) (N - 1) : 0.0f;
            auto r = I.water.toFloat().reduced (8, 6).translated (t * 36.0f, -t * 14.0f).withTrimmedRight (40).withTrimmedTop (14);
            g.setColour (f == I.sel ? juce::Colour (0xffff594e) : juce::Colours::white.withAlpha (0.28f));
            g.strokePath (path (I.T().frame (I.lfo(), f), r, 0.9f), juce::PathStrokeType (f == I.sel ? 1.8f : 1.0f));
        }
        for (auto& b : I.btns)
        {
            paintButton (g, b.r.toFloat(), false, false, false, 3.0f);
            g.setColour (ink); g.setFont (font (8.5f, true)); g.drawText (b.text, b.r, juce::Justification::centred);
        }
    }

    void LfoTableEditor::mouseDown (const juce::MouseEvent& e)
    {
        auto& I = *impl;
        for (auto& b : I.btns) if (b.r.contains (e.getPosition())) { if (b.fn) b.fn(); repaint(); return; }
        if (I.chipRow.contains (e.getPosition()))
        {
            int cw = juce::jmin (34, (I.chipRow.getWidth() - 4 * 15) / LfoTables::maxFrames);
            int f = (e.x - I.chipRow.getX()) / (cw + 4);
            if (f >= 0 && f < I.n()) { I.sel = f; repaint(); }
            return;
        }
        if (I.canvas.contains (e.getPosition())) { I.drawing = true; I.lastIdx = -1; I.setVal (e.position.x, e.position.y); }
    }
    void LfoTableEditor::mouseDrag (const juce::MouseEvent& e) { if (impl->drawing) impl->setVal (juce::jlimit ((float) impl->canvas.getX(), (float) impl->canvas.getRight() - 1, e.position.x), e.position.y); }
    void LfoTableEditor::mouseUp (const juce::MouseEvent&) { if (impl->drawing) { impl->drawing = false; impl->lastIdx = -1; impl->T().commitFrame (impl->lfo(), impl->sel, true); } }
    void LfoTableEditor::mouseMove (const juce::MouseEvent&) {}
}
