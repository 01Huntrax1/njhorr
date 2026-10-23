// Envelope + LFO editors with the drag handles for the modulation sources.
#include "ModUi.h"
#include "../NjoLfo.h"
#include "../NjoFreq.h"

namespace njo
{
    using namespace theme;

    namespace
    {
        const int kGrids[] = { 0, 4, 8, 16, 32 };
        int gGrid = 0;                                    // shared by every editor instance
        std::vector<struct ModEditorsRefresh*> gAll;
        struct ModEditorsRefresh { virtual ~ModEditorsRefresh() = default; virtual void refreshAll() = 0; };

        LfoShapes& shapes (Ctx& c) { if (! c.lfoShapes) c.lfoShapes = std::make_shared<LfoShapes> (c); return *c.lfoShapes; }

        float builtinAt (int w, float p)
        {
            if (w == 0) return std::sin (6.2831853f * p);
            if (w == 1) return 4 * std::abs (p - 0.5f) - 1;
            if (w == 2) return p < 0.5f ? 1.0f : -1.0f;
            if (w == 4) return 2 * p - 1;
            if (w == 5) return 1 - 2 * p;
            return LfoShapes::sampleAt (LfoShapes::builtin (3), p);
        }
    }

    // ------------------------------------------------------------------ source chip (click = select, drag = modulation source)
    struct SourceChip : juce::Component
    {
        int src; bool on = false; std::function<void()> onClick;
        explicit SourceChip (int s) : src (s) { setMouseCursor (juce::MouseCursor::PointingHandCursor); setTooltip ({}); }
        void setTooltip (const juce::String&) {}
        void paint (juce::Graphics& g) override
        {
            auto r = getLocalBounds().toFloat().reduced (0.5f);
            auto col = srcColour (src);
            bool misc = src > 20;
            g.setColour (on ? col : juce::Colour (0xff111214)); g.fillRoundedRectangle (r, r.getHeight() / 2);
            g.setColour (col.withAlpha (on ? 1.0f : 0.8f)); g.drawRoundedRectangle (r, r.getHeight() / 2, 1.2f);
            g.setColour (on ? juce::Colour (0xff111111) : (misc ? col : ink)); g.setFont (font (9.0f, true));
            g.drawText (srcShort (src), getLocalBounds(), juce::Justification::centred);
        }
        void mouseUp (const juce::MouseEvent& e) override { if (! dragged && e.getDistanceFromDragStart() < 4 && onClick) onClick(); dragged = false; }
        void mouseDrag (const juce::MouseEvent& e) override
        {
            if (dragged || e.getDistanceFromDragStart() < 5) return;
            auto* dc = juce::DragAndDropContainer::findParentDragContainerFor (this);
            if (dc == nullptr) return;
            dragged = true;
            juce::Image img (juce::Image::ARGB, 58, 20, true);
            { juce::Graphics g (img);
              g.setColour (srcColour (src)); g.fillRoundedRectangle (0, 0, 58, 20, 10.0f);
              g.setColour (juce::Colours::black); g.setFont (font (10.0f, true)); g.drawText (srcShort (src), 0, 0, 58, 20, juce::Justification::centred); }
            juce::Point<int> off (-29, -10);
            dc->startDragging (kModDrag + juce::String (src), this, juce::ScaledImage (img), true, &off);
        }
        bool dragged = false;
    };

    // ------------------------------------------------------------------ envelope display
    struct EnvCanvas : juce::Component
    {
        Ctx& ctx; EnvCanvas (Ctx& c) : ctx (c) {}
        void paint (juce::Graphics& g) override
        {
            auto bnd = getLocalBounds().toFloat();
            float W = bnd.getWidth(), H = bnd.getHeight(), pad = 10;
            int b = envParam (ctx.selectedEnv);
            float A = ctx.get (b), D = ctx.get (b + 1), S = ctx.get (b + 2), R = ctx.get (b + 3);
            auto t = [] (float ms) { return std::sqrt (juce::jmax (ms, 0.0f) / 5000.0f); };
            float seg[4] = { juce::jmax (t (A), 0.03f), juce::jmax (t (D), 0.05f), 0.18f, juce::jmax (t (R), 0.05f) };
            float tot = seg[0] + seg[1] + seg[2] + seg[3];
            auto X = [&] (float f) { return pad + f / tot * (W - 2 * pad); };
            auto Y = [&] (float a) { return H - pad - a * (H - 2 * pad); };
            g.setColour (juce::Colour (0xff0b0405)); g.fillRoundedRectangle (bnd, 2.0f);
            g.setColour (juce::Colours::white.withAlpha (0.06f));
            for (int k = 1; k < 4; ++k) g.drawHorizontalLine ((int) Y (k / 4.0f), pad, W - pad);
            float x1 = seg[0], x2 = x1 + seg[1], x3 = x2 + seg[2], x4 = x3 + seg[3];
            juce::Path p; p.startNewSubPath (X (0), Y (0)); p.lineTo (X (x1), Y (1));
            for (int k = 1; k <= 20; ++k) { float f = k / 20.0f; p.lineTo (X (x1 + seg[1] * f), Y (S + (1 - S) * std::exp (-4 * f))); }
            p.lineTo (X (x3), Y (S));
            for (int k = 1; k <= 20; ++k) { float f = k / 20.0f; p.lineTo (X (x3 + seg[3] * f), Y (S * std::exp (-4 * f))); }
            p.lineTo (X (x4), Y (0));
            g.setGradientFill (juce::ColourGradient (blue.withAlpha (0.30f), 0, 0, blue.withAlpha (0.03f), 0, H, false)); g.fillPath (p);
            g.setColour (blue); g.strokePath (p, juce::PathStrokeType (2.0f));
            g.setColour (juce::Colours::white.withAlpha (0.4f)); g.setFont (font (11.0f));
            const char* l[4] = { "A", "D", "S", "R" }; float xs[4] = { 0, x1, x2, x3 };
            for (int k = 0; k < 4; ++k) g.drawText (l[k], (int) X (xs[k]) + 4, (int) H - 26, 14, 14, juce::Justification::centredLeft);
        }
    };

    // ------------------------------------------------------------------ LFO shape canvas
    struct LfoCanvas : juce::Component
    {
        Ctx& ctx; std::function<void()> changed;
        explicit LfoCanvas (Ctx& c) : ctx (c) {}
        static constexpr float pad = 10;
        float px (float x) const { return pad + x * (getWidth() - 2 * pad); }
        float py (float y) const { return getHeight() / 2.0f - y * (getHeight() / 2.0f - pad); }
        float ix (float X) const { return (X - pad) / (getWidth() - 2 * pad); }
        float iy (float Y) const { return (getHeight() / 2.0f - Y) / (getHeight() / 2.0f - pad); }
        int lfo() const { return ctx.selectedLfo; }
        int wave() const { return juce::roundToInt (ctx.get (lfoWaveParam (lfo()))); }
        bool drawn() { return shapes (ctx).isDrawn (lfo()) || wave() >= LFO_DRAWN; }

        void paint (juce::Graphics& g) override
        {
            float W = (float) getWidth(), H = (float) getHeight();
            int i = lfo(), w = wave(); bool dr = drawn();
            const std::vector<LfoPoint>* P = dr ? &shapes (ctx).points (i) : nullptr;
            g.setColour (juce::Colour (0xff0b0405)); g.fillRoundedRectangle (getLocalBounds().toFloat(), 2.0f);
            int grid = kGrids[gGrid], xs = grid ? grid : 8, ys = grid ? juce::jmax (2, grid / 2) : 4;
            for (int k = 0; k <= xs; ++k)
            {
                g.setColour (juce::Colours::white.withAlpha (k % (grid ? juce::jmax (1, xs / 4) : 2) == 0 ? 0.13f : 0.05f));
                g.drawVerticalLine ((int) std::round (px ((float) k / xs)), 0, H);
            }
            for (int k = -ys; k <= ys; ++k)
            {
                g.setColour (juce::Colours::white.withAlpha (k == 0 ? 0.22f : 0.05f));
                g.drawHorizontalLine ((int) std::round (py ((float) k / ys)), 0, W);
            }
            auto fn = [&] (float p) { return P ? LfoShapes::sampleAt (*P, p) : builtinAt (w, p); };
            juce::Path line;
            for (int k = 0; k <= 400; ++k) { float p = k / 400.0f; if (k == 0) line.startNewSubPath (px (p), py (fn (p))); else line.lineTo (px (p), py (fn (p))); }
            juce::Path fill (line); fill.lineTo (px (1), py (0)); fill.lineTo (px (0), py (0)); fill.closeSubPath();
            g.setColour (dr ? juce::Colour::fromFloatRGBA (1, 0.35f, 0.24f, 0.16f) : juce::Colour::fromFloatRGBA (0.63f, 0.63f, 0.67f, 0.10f)); g.fillPath (fill);
            g.setColour (dr ? juce::Colour (0xffff6a4d) : juce::Colour (0xff9a9aa2)); g.strokePath (line, juce::PathStrokeType (2.0f));
            if (P)
            {
                for (size_t k = 0; k + 1 < P->size(); ++k)
                {
                    auto& a = (*P)[k]; auto& b = (*P)[k + 1];
                    if (b.x - a.x < 0.02f) continue;
                    float mx = (a.x + b.x) / 2, my = LfoShapes::curve (a.y, b.y, a.c, 0.5f);
                    juce::Path d; d.addRectangle (-4.0f, -4.0f, 8.0f, 8.0f);
                    d.applyTransform (juce::AffineTransform::rotation (juce::MathConstants<float>::pi / 4).translated (px (mx), py (my)));
                    g.setColour (juce::Colour (0xff2a1210)); g.fillPath (d);
                    g.setColour (juce::Colour (0xffffb09e)); g.strokePath (d, juce::PathStrokeType (1.5f));
                }
                for (auto& q : *P)
                {
                    auto e = juce::Rectangle<float> (11, 11).withCentre ({ px (q.x), py (q.y) });
                    g.setColour (juce::Colour (0xffffd9cf)); g.fillEllipse (e);
                    g.setColour (juce::Colour (0xffff3b30)); g.drawEllipse (e, 2.0f);
                }
            }
            else
            {
                g.setColour (juce::Colours::white.withAlpha (0.35f)); g.setFont (font (11.0f));
                g.drawText ("built-in shape - click to draw your own", 14, (int) H - 24, (int) W - 20, 16, juce::Justification::centredLeft);
            }
        }

        struct Hit { int kind = 0, k = 0; };   // 1 point, 2 curve handle
        Hit hit (const std::vector<LfoPoint>& P, float X, float Y) const
        {
            for (size_t k = 0; k < P.size(); ++k) if (std::hypot (px (P[k].x) - X, py (P[k].y) - Y) < 11) return { 1, (int) k };
            for (size_t k = 0; k + 1 < P.size(); ++k)
            {
                auto& a = P[k]; auto& b = P[k + 1];
                if (b.x - a.x < 0.02f) continue;
                if (std::hypot (px ((a.x + b.x) / 2) - X, py (LfoShapes::curve (a.y, b.y, a.c, 0.5f)) - Y) < 10) return { 2, (int) k };
            }
            return {};
        }
        float snapX (float x) const { int gr = kGrids[gGrid]; return gr ? std::round (x * gr) / gr : x; }
        float snapY (float y) const { int gr = kGrids[gGrid]; if (! gr) return y; int s = juce::jmax (2, gr / 2); return std::round (y * s) / s; }

        Hit dragHit; float y0 = 0, c0 = 0; bool dragging = false;
        void commit (bool final) { shapes (ctx).commit (lfo(), final); if (changed) changed(); }

        void mouseDown (const juce::MouseEvent& e) override
        {
            auto& P = shapes (ctx).points (lfo());
            float X = e.position.x, Y = e.position.y;
            auto h = hit (P, X, Y);
            if (h.kind == 0)
            {
                float x = juce::jlimit (0.004f, 0.996f, snapX (ix (X))), y = juce::jlimit (-1.0f, 1.0f, snapY (iy (Y)));
                size_t k = 0; while (k < P.size() && P[k].x < x) ++k;
                if (k == 0 || k >= P.size()) return;
                P.insert (P.begin() + (long) k, { x, y, 0.0f });
                h = { 1, (int) k };
                commit (false);
            }
            dragHit = h; y0 = Y; c0 = h.kind == 2 ? P[(size_t) h.k].c : 0.0f; dragging = true;
        }
        void mouseDrag (const juce::MouseEvent& e) override
        {
            if (! dragging) return;
            auto& P = shapes (ctx).points (lfo());
            float X = e.position.x, Y = e.position.y;
            if (dragHit.kind == 1)
            {
                auto& q = P[(size_t) dragHit.k];
                q.y = juce::jlimit (-1.0f, 1.0f, snapY (iy (Y)));
                if (dragHit.k > 0 && dragHit.k < (int) P.size() - 1)
                    q.x = juce::jmax (P[(size_t) dragHit.k - 1].x + 0.002f, juce::jmin (P[(size_t) dragHit.k + 1].x - 0.002f, snapX (ix (X))));
            }
            else
            {
                auto& a = P[(size_t) dragHit.k]; auto& b = P[(size_t) dragHit.k + 1];
                float dir = b.y > a.y ? 1.0f : (b.y < a.y ? -1.0f : 1.0f);
                a.c = juce::jlimit (-1.0f, 1.0f, c0 + (Y - y0) / 70.0f * dir);
            }
            commit (false);
        }
        void mouseUp (const juce::MouseEvent&) override { if (dragging) { dragging = false; commit (true); } }
        void mouseDoubleClick (const juce::MouseEvent& e) override
        {
            auto& P = shapes (ctx).points (lfo());
            auto h = hit (P, e.position.x, e.position.y);
            if (h.kind == 1 && h.k > 0 && h.k < (int) P.size() - 1) P.erase (P.begin() + h.k);
            else if (h.kind == 2) P[(size_t) h.k].c = 0;
            else return;
            commit (true);
        }
    };

    // ------------------------------------------------------------------ the editor
    struct ModEditors::Impl : Ctx::Listener, ModEditorsRefresh
    {
        Ctx& ctx; ModEditors& owner;
        juce::OwnedArray<SourceChip> lfoChips, envChips, miscChips;
        EnvCanvas envCv; LfoCanvas lfoCv;
        juce::OwnedArray<ParamWidget> envKnobs, lfoKnobs, modeBtn, syncBtn;
        juce::OwnedArray<MiniSelect> divSel;
        MiniSelect shape;
        struct GridButton : juce::Component
        {
            std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                paintButton (g, getLocalBounds().toFloat(), false, false, false, 3.0f);
                g.setColour (ink); g.setFont (font (9.0f, true));
                g.drawText (kGrids[gGrid] ? "GRID 1/" + juce::String (kGrids[gGrid]) : juce::String ("GRID OFF"), getLocalBounds(), juce::Justification::centred);
            }
            void mouseDown (const juce::MouseEvent&) override { if (click) click(); }
        } grid;
        bool full = false; juce::Rectangle<int> helpRect, shapeLabel;

        Impl (Ctx& c, ModEditors& o) : ctx (c), owner (o), envCv (c), lfoCv (c)
        {
            ctx.addListener (this); gAll.push_back (this);
            lfoCv.changed = [] { for (auto* a : gAll) a->refreshAll(); };
            for (int i = 0; i < 10; ++i)
            {
                auto* l = lfoChips.add (new SourceChip (1 + i)); l->onClick = [this, i] { ctx.selectedLfo = i; for (auto* a : gAll) a->refreshAll(); };
                auto* e = envChips.add (new SourceChip (11 + i)); e->onClick = [this, i] { ctx.selectedEnv = i; for (auto* a : gAll) a->refreshAll(); };
                owner.addAndMakeVisible (l); owner.addAndMakeVisible (e);
            }
            for (int n = 21; n <= 23; ++n) { auto* m = miscChips.add (new SourceChip (n)); owner.addAndMakeVisible (m); }
            owner.addAndMakeVisible (envCv); owner.addAndMakeVisible (lfoCv);
            for (int i = 0; i < 10; ++i)
            {
                for (int k = 0; k < 4; ++k) { auto* w = envKnobs.add (makeWidget (ctx, envParam (i) + k, true).release()); w->setLook (true); owner.addChildComponent (w); }
                int ks[5] = { lfoRateParam (i), lfoModeParam (i) + 1, lfoModeParam (i) + 2, lfoModeParam (i) + 3, lfoModeParam (i) + 4 };
                for (int k : ks) { auto* w = lfoKnobs.add (makeWidget (ctx, k, true).release()); w->setLook (true); owner.addChildComponent (w); }
                auto* m = static_cast<ButtonsWidget*> (modeBtn.add (makeWidget (ctx, lfoModeParam (i), false).release())); m->setShowLabel (false); owner.addChildComponent (m);
                auto* s = static_cast<ButtonsWidget*> (syncBtn.add (makeWidget (ctx, lfoSyncParam (i), false).release())); s->setShowLabel (false); owner.addChildComponent (s);
                auto* d = divSel.add (new MiniSelect());
                int dp = lfoDivParam (i);
                d->names = syncDivs();
                d->getIndex = [this, dp] { return juce::roundToInt (ctx.get (dp)); };
                d->setIndex = [this, dp] (int v) { ctx.begin (dp); ctx.set (dp, (float) v); ctx.end (dp); };
                owner.addChildComponent (d);
            }
            // shape menu: built-in waves, drawn presets, "Drawn"
            for (auto& p : lfoPresets()) shape.names.add (p.name);
            shape.extraItem = (int) lfoPresets().size(); shape.extraName = "Drawn";
            shape.getIndex = [this] { int i = ctx.selectedLfo; int w = juce::roundToInt (ctx.get (lfoWaveParam (i)));
                                      return (shapes (ctx).isDrawn (i) || w >= LFO_DRAWN) ? (int) lfoPresets().size() : juce::jlimit (0, (int) lfoPresets().size() - 1, w); };
            shape.setIndex = [this] (int idx) { applyPreset (ctx.selectedLfo, idx); };
            owner.addAndMakeVisible (shape);
            grid.click = [] { gGrid = (gGrid + 1) % 5; for (auto* a : gAll) a->refreshAll(); };
            owner.addAndMakeVisible (grid);
            refreshAll();
        }
        ~Impl() override { ctx.removeListener (this); gAll.erase (std::remove (gAll.begin(), gAll.end(), this), gAll.end()); }

        void applyPreset (int i, int idx)
        {
            auto& L = shapes (ctx);
            auto& ps = lfoPresets();
            if (idx >= (int) ps.size()) { L.points (i); L.commit (i, true); }
            else if (ps[(size_t) idx].wave >= 0)
            {
                L.reset (i);
                ctx.set (lfoWaveParam (i), (float) ps[(size_t) idx].wave);
                ctx.be.setStored ("njo.lfo", L.toVar());
            }
            else { L.setPoints (i, ps[(size_t) idx].pts); L.commit (i, true); }
            for (auto* a : gAll) a->refreshAll();
        }

        void paramChanged (int n, float) override
        {
            int i = ctx.selectedLfo, e = ctx.selectedEnv;
            if (n >= envParam (e) && n < envParam (e) + 4) envCv.repaint();
            if (n == lfoWaveParam (i)) { lfoCv.repaint(); shape.repaint(); }
            if (n == lfoSyncParam (i)) refreshAll();
        }

        void refreshAll() override
        {
            int li = ctx.selectedLfo, ei = ctx.selectedEnv;
            for (int i = 0; i < 10; ++i)
            {
                lfoChips[i]->on = i == li; lfoChips[i]->repaint();
                envChips[i]->on = i == ei; envChips[i]->repaint();
                for (int k = 0; k < 4; ++k) envKnobs[i * 4 + k]->setVisible (i == ei);
                for (int k = 0; k < 5; ++k) lfoKnobs[i * 5 + k]->setVisible (i == li);
                modeBtn[i]->setVisible (i == li); syncBtn[i]->setVisible (i == li);
                divSel[i]->setVisible (i == li);
                bool sync = ctx.get (lfoSyncParam (i)) > 0.5f;
                divSel[i]->dimmed = ! sync; divSel[i]->repaint();
                lfoKnobs[i * 5]->setAlpha (sync ? 0.45f : 1.0f);
            }
            envCv.repaint(); lfoCv.repaint(); shape.repaint(); grid.repaint();
        }
    };

    ModEditors::ModEditors (Ctx& c) : impl (new Impl (c, *this)) {}
    ModEditors::~ModEditors() = default;

    void ModEditors::paint (juce::Graphics& g)
    {
        if (impl->full)
        {
            paintCard (g, getLocalBounds().toFloat());
            g.setColour (red); g.setFont (impact (11.0f));
            g.drawText ("MODULATION MATRIX", 10, 4, 220, 16, juce::Justification::centredLeft);
        }
        g.setColour (dim.withAlpha (0.8f)); g.setFont (font (8.5f));
        g.drawText (juce::String (juce::CharPointer_UTF8 ("click: add point \xc2\xb7 drag: move \xc2\xb7 dbl-click point: delete \xc2\xb7 drag the diamond: curve")), impl->helpRect, juce::Justification::centredLeft, true);
        g.setFont (font (8.5f, true)); g.setColour (dim);
        g.drawText ("SHAPE", impl->shapeLabel, juce::Justification::topLeft);
    }

    void ModEditors::resized()
    {
        auto& I = *impl;
        I.full = getHeight() > 230;
        auto b = getLocalBounds().reduced (10, I.full ? 6 : 2);
        if (I.full) b.removeFromTop (16);
        int W = b.getWidth(), gap = 10;
        int envW = (int) (W * 0.353f), ctlW = (int) (W * 0.235f), lfoW = W - envW - ctlW - 2 * gap;
        auto envCol = b.removeFromLeft (envW); b.removeFromLeft (gap);
        auto lfoCol = b.removeFromLeft (lfoW); b.removeFromLeft (gap);
        auto ctlCol = b;

        // envelope column: chips (2 rows), canvas, knobs
        {
            auto c = envCol; const int ch = 18, cg = 3;
            int cw = (c.getWidth() - 8 * cg) / 9;
            auto row1 = c.removeFromTop (ch); c.removeFromTop (cg);
            auto row2 = c.removeFromTop (ch); c.removeFromTop (4);
            for (int i = 0; i < 9; ++i) I.envChips[i]->setBounds (row1.getX() + i * (cw + cg), row1.getY(), cw, ch);
            I.envChips[9]->setBounds (row2.getX(), row2.getY(), cw, ch);
            for (int k = 0; k < 3; ++k) I.miscChips[k]->setBounds (row2.getRight() - (3 - k) * cw - (2 - k) * cg, row2.getY(), cw, ch);
            auto knobs = c.removeFromBottom (46);
            c.removeFromBottom (3);
            I.envCv.setBounds (c);
            int kw = knobs.getWidth() / 4;
            for (int i = 0; i < 10; ++i) for (int k = 0; k < 4; ++k) I.envKnobs[i * 4 + k]->setBounds (knobs.getX() + k * kw, knobs.getY(), kw, knobs.getHeight());
        }
        // LFO column: chips, canvas, help line
        {
            auto c = lfoCol; const int ch = 18, cg = 3;
            int cw = (c.getWidth() - 9 * cg) / 10;
            auto row = c.removeFromTop (ch); c.removeFromTop (4);
            for (int i = 0; i < 10; ++i) I.lfoChips[i]->setBounds (row.getX() + i * (cw + cg), row.getY(), cw, ch);
            I.helpRect = c.removeFromBottom (12);
            I.lfoCv.setBounds (c.withTrimmedBottom (2));
        }
        // control column
        {
            auto c = ctlCol; 
            auto top = c.removeFromTop (18); c.removeFromTop (4);
            I.grid.setBounds (top.removeFromRight (66));
            auto sh = c.removeFromTop (12 + 24);
            I.shape.setBounds (sh.withTrimmedTop (12));
            I.shapeLabel = sh.withHeight (12);
            c.removeFromTop (4);
            auto mr = c.removeFromTop (20);
            int half = mr.getWidth() * 3 / 5;
            auto ma = mr.removeFromLeft (half - 3); mr.removeFromLeft (3);
            c.removeFromTop (4);
            auto dr = c.removeFromTop (22).removeFromLeft ((int) (ctlCol.getWidth() * 0.45f));
            auto knobs = c.removeFromBottom (46);
            int kw = knobs.getWidth() / 5;
            for (int i = 0; i < 10; ++i)
            {
                I.modeBtn[i]->setBounds (ma); I.syncBtn[i]->setBounds (mr); I.divSel[i]->setBounds (dr);
                for (int k = 0; k < 5; ++k) I.lfoKnobs[i * 5 + k]->setBounds (knobs.getX() + k * kw, knobs.getY(), kw, knobs.getHeight());
            }
        }
    }
}

namespace njo
{
    using namespace theme;

    namespace
    {
        FreqShapes& freqShapes (Ctx& c) { if (! c.freqShapes) c.freqShapes = std::make_shared<FreqShapes> (c); return *c.freqShapes; }
        const double kFrqAxis[] = { 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000 };
        const char* const kFrqAxisText[] = { "20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "20k" };
        std::vector<struct FreqRefresh*> gFrqAll;
        struct FreqRefresh { virtual ~FreqRefresh() = default; virtual void refreshAll() = 0; };
    }

    // ------------------------------------------------------------------ Freq curve canvas: frequency (log) over time
    struct FreqCanvas : juce::Component
    {
        Ctx& ctx; std::function<void()> changed;
        explicit FreqCanvas (Ctx& c) : ctx (c) {}
        static constexpr float padL = 34, padR = 10, padT = 10, padB = 18;
        float px (float x) const { return padL + x * (getWidth() - padL - padR); }
        float py (float y) const { return getHeight() - padB - y * (getHeight() - padT - padB); }
        float ix (float X) const { return (X - padL) / (getWidth() - padL - padR); }
        float iy (float Y) const { return (getHeight() - padB - Y) / (getHeight() - padT - padB); }
        int sel() const { return ctx.selectedFrq; }

        void paint (juce::Graphics& g) override
        {
            float W = (float) getWidth(), H = (float) getHeight();
            auto& P = freqShapes (ctx).points (sel());
            const float rate = ctx.get (frqParam (sel()));
            g.setColour (juce::Colour (0xff0b0405)); g.fillRoundedRectangle (getLocalBounds().toFloat(), 2.0f);
            g.setFont (font (9.0f));
            for (int k = 0; k < 10; ++k)
            {
                float y = std::floor (py ((float) (std::log (kFrqAxis[k] / 20.0) / std::log (1000.0)))) + 0.5f;
                g.setColour (juce::Colours::white.withAlpha (0.07f)); g.drawHorizontalLine ((int) y, padL, W - padR);
                g.setColour (juce::Colours::white.withAlpha (0.45f));
                g.drawText (kFrqAxisText[k], juce::Rectangle<float> (0, y - 6, padL - 4, 12).toNearestInt(), juce::Justification::centredRight);
            }
            for (int k = 1; k <= 5; ++k)
            {
                float x = std::floor (px (k / 6.0f)) + 0.5f, ms = rate * k / 6.0f;
                g.setColour (juce::Colours::white.withAlpha (0.07f)); g.drawVerticalLine ((int) x, padT, H - padB);
                g.setColour (juce::Colours::white.withAlpha (0.45f));
                g.drawText (ms >= 1000 ? juce::String (ms / 1000, 1) + " s" : juce::String (juce::roundToInt (ms)) + " ms",
                            juce::Rectangle<float> (x - 30, H - 14, 60, 12).toNearestInt(), juce::Justification::centred);
            }
            juce::Path line;
            for (int k = 0; k <= 400; ++k) { float p = k / 400.0f, y = LfoShapes::sampleAt (P, p); if (k == 0) line.startNewSubPath (px (p), py (y)); else line.lineTo (px (p), py (y)); }
            juce::Path fill (line); fill.lineTo (px (1), py (0)); fill.lineTo (px (0), py (0)); fill.closeSubPath();
            g.setColour (juce::Colour::fromFloatRGBA (1, 0.35f, 0.24f, 0.16f)); g.fillPath (fill);
            g.setColour (juce::Colour (0xffff6a4d)); g.strokePath (line, juce::PathStrokeType (2.0f));
            for (size_t k = 0; k + 1 < P.size(); ++k)
            {
                auto& a = P[k]; auto& b = P[k + 1];
                if (b.x - a.x < 0.02f) continue;
                auto e = juce::Rectangle<float> (7, 7).withCentre ({ px ((a.x + b.x) / 2), py (LfoShapes::curve (a.y, b.y, a.c, 0.5f)) });
                g.setColour (juce::Colour (0xff2a1210)); g.fillEllipse (e);
                g.setColour (juce::Colour (0xffffb09e)); g.drawEllipse (e, 1.2f);
            }
            for (auto& q : P)
            {
                auto e = juce::Rectangle<float> (10, 10).withCentre ({ px (q.x), py (q.y) });
                g.setColour (juce::Colour (0xffff8068)); g.fillEllipse (e);
                g.setColour (juce::Colour (0xffffd9cf)); g.drawEllipse (e, 1.5f);
            }
        }

        struct Hit { int kind = 0, k = 0; };   // 1 point, 2 curve handle
        Hit hit (const std::vector<LfoPoint>& P, float X, float Y) const
        {
            for (size_t k = 0; k < P.size(); ++k) if (std::hypot (px (P[k].x) - X, py (P[k].y) - Y) < 11) return { 1, (int) k };
            for (size_t k = 0; k + 1 < P.size(); ++k)
            {
                auto& a = P[k]; auto& b = P[k + 1];
                if (b.x - a.x < 0.02f) continue;
                if (std::hypot (px ((a.x + b.x) / 2) - X, py (LfoShapes::curve (a.y, b.y, a.c, 0.5f)) - Y) < 10) return { 2, (int) k };
            }
            return {};
        }
        Hit dragHit; float y0 = 0, c0 = 0; bool dragging = false;
        void commit (bool final) { freqShapes (ctx).commit (sel(), final); if (changed) changed(); }

        void mouseDown (const juce::MouseEvent& e) override
        {
            auto& P = freqShapes (ctx).points (sel());
            float X = e.position.x, Y = e.position.y;
            auto h = hit (P, X, Y);
            if (h.kind == 0)
            {
                float x = juce::jlimit (0.004f, 0.996f, ix (X)), y = juce::jlimit (0.0f, 1.0f, iy (Y));
                size_t k = 0; while (k < P.size() && P[k].x < x) ++k;
                if (k == 0 || k >= P.size()) return;
                P.insert (P.begin() + (long) k, { x, y, 0.0f });
                h = { 1, (int) k };
                commit (false);
            }
            dragHit = h; y0 = Y; c0 = h.kind == 2 ? P[(size_t) h.k].c : 0.0f; dragging = true;
        }
        void mouseDrag (const juce::MouseEvent& e) override
        {
            if (! dragging) return;
            auto& P = freqShapes (ctx).points (sel());
            float X = e.position.x, Y = e.position.y;
            if (dragHit.kind == 1)
            {
                auto& q = P[(size_t) dragHit.k];
                q.y = juce::jlimit (0.0f, 1.0f, iy (Y));
                if (dragHit.k > 0 && dragHit.k < (int) P.size() - 1)
                    q.x = juce::jmax (P[(size_t) dragHit.k - 1].x + 0.002f, juce::jmin (P[(size_t) dragHit.k + 1].x - 0.002f, ix (X)));
            }
            else
            {
                auto& a = P[(size_t) dragHit.k]; auto& b = P[(size_t) dragHit.k + 1];
                float dir = b.y > a.y ? 1.0f : (b.y < a.y ? -1.0f : 1.0f);
                a.c = juce::jlimit (-1.0f, 1.0f, c0 + (Y - y0) / 70.0f * dir);
            }
            commit (false);
        }
        void mouseUp (const juce::MouseEvent&) override { if (dragging) { dragging = false; commit (true); } }
        void mouseDoubleClick (const juce::MouseEvent& e) override
        {
            auto& P = freqShapes (ctx).points (sel());
            auto h = hit (P, e.position.x, e.position.y);
            if (h.kind == 1 && h.k > 0 && h.k < (int) P.size() - 1) P.erase (P.begin() + h.k);
            else if (h.kind == 2) P[(size_t) h.k].c = 0;
            else return;
            commit (true);
        }
    };

    struct FreqEditor::Impl : Ctx::Listener, FreqRefresh
    {
        Ctx& ctx; FreqEditor& owner;
        juce::OwnedArray<SourceChip> chips;
        FreqCanvas cv;
        juce::OwnedArray<ParamWidget> knobs, retrig, loop;
        bool full = false; juce::Rectangle<int> helpRect, btnLabels[2];

        Impl (Ctx& c, FreqEditor& o) : ctx (c), owner (o), cv (c)
        {
            ctx.addListener (this); gFrqAll.push_back (this);
            freqShapes (ctx);
            cv.changed = [] { for (auto* a : gFrqAll) a->refreshAll(); };
            for (int i = 0; i < 10; ++i)
            {
                auto* ch = chips.add (new SourceChip (24 + i)); ch->onClick = [this, i] { ctx.selectedFrq = i; for (auto* a : gFrqAll) a->refreshAll(); };
                owner.addAndMakeVisible (ch);
                for (int k = 0; k < 2; ++k) { auto* w = knobs.add (makeWidget (ctx, frqParam (i) + k, true).release()); w->setLook (true); owner.addChildComponent (w); }
                auto* r = static_cast<ButtonsWidget*> (retrig.add (makeWidget (ctx, frqParam (i) + 2, false).release())); r->setShowLabel (false); owner.addChildComponent (r);
                auto* l = static_cast<ButtonsWidget*> (loop.add (makeWidget (ctx, frqParam (i) + 3, false).release())); l->setShowLabel (false); owner.addChildComponent (l);
            }
            owner.addAndMakeVisible (cv);
            refreshAll();
        }
        ~Impl() override { ctx.removeListener (this); gFrqAll.erase (std::remove (gFrqAll.begin(), gFrqAll.end(), this), gFrqAll.end()); }

        void paramChanged (int n, float) override { if (n == frqParam (ctx.selectedFrq)) cv.repaint(); }

        void refreshAll() override
        {
            int s = ctx.selectedFrq;
            for (int i = 0; i < 10; ++i)
            {
                chips[i]->on = i == s; chips[i]->repaint();
                knobs[i * 2]->setVisible (i == s); knobs[i * 2 + 1]->setVisible (i == s);
                retrig[i]->setVisible (i == s); loop[i]->setVisible (i == s);
            }
            cv.repaint();
        }
    };

    FreqEditor::FreqEditor (Ctx& c) : impl (new Impl (c, *this)) {}
    FreqEditor::~FreqEditor() = default;

    void FreqEditor::paint (juce::Graphics& g)
    {
        auto& I = *impl;
        if (I.full)
        {
            paintCard (g, getLocalBounds().toFloat());
            g.setColour (red); g.setFont (impact (11.0f));
            g.drawText ("FREQUENCY MODULATORS", 10, 4, 260, 16, juce::Justification::centredLeft);
        }
        g.setColour (dim.withAlpha (0.8f)); g.setFont (font (8.5f));
        g.drawText (juce::String (juce::CharPointer_UTF8 ("click: add point \xc2\xb7 drag: move \xc2\xb7 dbl-click point: delete \xc2\xb7 drag the diamond: curve")), I.helpRect, juce::Justification::centredLeft, true);
        g.setFont (font (8.5f, true)); g.setColour (dim);
        g.drawText ("RETRIG", I.btnLabels[0], juce::Justification::topLeft);
        g.drawText ("LOOP", I.btnLabels[1], juce::Justification::topLeft);
        if (! I.full)
        {
            g.setColour (srcColour (24).withAlpha (0.8f));
            g.drawText ("only onto the cutoff and Frequency knobs", getLocalBounds().reduced (10, 4).removeFromTop (18).removeFromRight (230), juce::Justification::centredRight, true);
        }
    }

    void FreqEditor::resized()
    {
        auto& I = *impl;
        I.full = getHeight() > 230;
        auto b = getLocalBounds().reduced (10, I.full ? 6 : 2);
        if (I.full) b.removeFromTop (16);
        const int ch = 18, cg = 3;
        auto row = b.removeFromTop (ch); b.removeFromTop (4);
        int cw = juce::jmin (60, (juce::jmin (row.getWidth(), 640) - 9 * cg) / 10);
        for (int i = 0; i < 10; ++i) I.chips[i]->setBounds (row.getX() + i * (cw + cg), row.getY(), cw, ch);
        auto right = b.removeFromRight (230); b.removeFromRight (10);
        I.helpRect = b.removeFromBottom (12);
        I.cv.setBounds (b.withTrimmedBottom (2));
        // right column: Retrig / Loop and the two knobs
        auto c = right;
        auto lab = c.removeFromTop (12); I.btnLabels[0] = lab.removeFromLeft (lab.getWidth() / 2); I.btnLabels[1] = lab;
        auto br = c.removeFromTop (20);
        auto ra = br.removeFromLeft (br.getWidth() / 2 - 3); br.removeFromLeft (3);
        c.removeFromTop (6);
        auto knobs = c.removeFromBottom (juce::jmin (c.getHeight(), 60));
        int kw = knobs.getWidth() / 2;
        for (int i = 0; i < 10; ++i)
        {
            I.retrig[i]->setBounds (ra); I.loop[i]->setBounds (br);
            for (int k = 0; k < 2; ++k) I.knobs[i * 2 + k]->setBounds (knobs.getX() + k * kw, knobs.getY(), kw, knobs.getHeight());
        }
    }
}
