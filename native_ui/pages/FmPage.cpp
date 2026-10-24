// FM / PM / PD matrices (page 0) and RM / AM matrices (page 1): 6 x 6 node grids like the web UI. The letter of a row modulates the letter of the column it meets.
#include "../NjoPages.h"

namespace njo
{
    using namespace theme;

    struct FmPage::Impl : public Ctx::Listener
    {
        struct Kind { const char* title; const char* sub; int base; };
        static constexpr Kind kindsFm[3] = { { "FM", "frequency modulation", FM_BASE }, { "PM", "phase modulation", PM_BASE }, { "PD", "phase distortion", PD_BASE } };
        static constexpr Kind kindsRm[2] = { { "RM", "ring modulation", RM_BASE }, { "AM", "amplitude modulation", AM_BASE } };
        const Kind* kinds; int nk;
        enum Part { None, Cell, Fb, Node };
        struct Hit { int k = -1, s = 0, d = 0; Part part = None; bool operator== (const Hit& o) const { return k == o.k && s == o.s && d == o.d && part == o.part; } };

        Impl (FmPage& p, Ctx& c, int page) : kinds (page == 1 ? kindsRm : kindsFm), nk (page == 1 ? 2 : 3), owner (p), ctx (c) { ctx.addListener (this); }
        ~Impl() override { ctx.removeListener (this); }

        FmPage& owner; Ctx& ctx; int pageNo = 0;
        std::function<void (int)> openOsc;
        juce::Rectangle<float> panel[3], inset[3], grid[3];
        juce::Rectangle<float> noteRect, headRect;
        std::unique_ptr<juce::Component> overlay;
        Hit hover, drag, modHover; bool dragMoved = false; float dragStartV = 0; int dragStartY = 0; bool dragging = false;

        void paramChanged (int n, float) override
        {
            if ((n >= FM_BASE && n < AM_BASE + 36) || (n >= 307 && n <= 336) || (n >= 472 && n <= 501)) owner.repaint();
        }

        int pid (int k, int s, int d) const { return kinds[k].base + 6 * s + d; }
        float val (int k, int s, int d) const { return ctx.get (pid (k, s, d)); }
        static bool on (float v) { return v >= 0.5f; }

        juce::Rectangle<float> cellRect (int k, int s, int d) const
        {
            auto g = grid[k]; float w = g.getWidth() / 6, h = g.getHeight() / 6;
            return { g.getX() + w * d, g.getY() + h * s, w, h };
        }
        // the diagonal cell: letter button on the left, feedback box on the right (centred as a group)
        juce::Rectangle<float> nodeRect (int k, int s) const
        {
            auto c = cellRect (k, s, s);
            float bs = juce::jmin (30.0f, c.getHeight() - 6, c.getWidth() * 0.4f);
            float groupW = bs + 6 + 30;
            return { c.getCentreX() - groupW * 0.5f, c.getCentreY() - bs * 0.5f, bs, bs };
        }
        juce::Rectangle<float> fbRect (int k, int s) const
        {
            auto n = nodeRect (k, s);
            return { n.getRight() + 6, n.getCentreY() - 13, 30, 26 };
        }

        Hit hitTest (juce::Point<float> p) const
        {
            for (int k = 0; k < nk; ++k)
            {
                if (! grid[k].contains (p)) continue;
                int d = juce::jlimit (0, 5, (int) ((p.x - grid[k].getX()) / (grid[k].getWidth() / 6)));
                int s = juce::jlimit (0, 5, (int) ((p.y - grid[k].getY()) / (grid[k].getHeight() / 6)));
                if (s == d)
                {
                    if (nodeRect (k, s).expanded (2).contains (p)) return { k, s, d, Node };
                    return { k, s, d, Fb };   // anything else in the diagonal cell edits the feedback
                }
                return { k, s, d, Cell };
            }
            return {};
        }

        // little dot of the modulated cells (top right of the value box); click = amount popup
        juce::Rectangle<float> modDotRect (int k, int s, int d) const
        {
            auto r = s == d ? fbRect (k, s) : cellRect (k, s, d).withSizeKeepingCentre (30.0f, 15.0f);
            return { r.getRight() - 4.0f, r.getY() - 2.0f, 9.0f, 9.0f };
        }
        std::vector<ModSlot> modsOf (int k, int s, int d) const
        {
            std::vector<ModSlot> out;
            int id = pid (k, s, d);
            if (! ctx.isModTarget (id)) return out;
            for (auto& m : ctx.modsFor (modTarget().at (id).first)) if (std::abs (m.amt) > 0.0005f) out.push_back (m);
            return out;
        }

        static juce::String pct (float v) { return juce::String (juce::roundToInt (v)); }

        void setVal (const Hit& h, float v)
        {
            v = juce::jlimit (0.0f, 100.0f, std::round (v));   // 0 = off, 100 = 100 %
            ctx.set (pid (h.k, h.s, h.d), v);
        }

        void describe (const Hit& h)
        {
            if (h.part == None) return;
            static const char* L = "ABCDEF";
            if (h.part == Node) { ctx.lcd (juce::String ("OSC ") + juce::String (h.s + 1), "OPEN"); return; }
            juce::String name = h.s == h.d ? juce::String (L[h.s]) + " FEEDBACK"
                                           : juce::String (L[h.s]) + " > " + juce::String (L[h.d]);
            ctx.lcd (juce::String (kinds[h.k].title) + " " + name, pct (val (h.k, h.s, h.d)) + "%");
        }

        void drawValueBox (juce::Graphics& g, juce::Rectangle<float> r, const juce::String& t, bool neg, bool lit)
        {
            juce::Colour fill = lit ? (neg ? juce::Colour (0xff163e66) : juce::Colour (0xff7d1a14)) : juce::Colours::black.withAlpha (0.5f);
            juce::Colour edge = lit ? (neg ? blue : juce::Colour (0xffff5a4a)) : juce::Colour (0xff4c4d51);
            if (lit) { g.setColour (edge.withAlpha (0.18f)); g.fillRoundedRectangle (r.expanded (3), 6.0f); }
            g.setColour (fill); g.fillRoundedRectangle (r, 4.0f);
            g.setColour (edge); g.drawRoundedRectangle (r.reduced (0.5f), 4.0f, 1.0f);
            g.setColour (lit ? juce::Colours::white : dim); g.setFont (font (9.5f, true));
            g.drawText (t, r.toNearestInt(), juce::Justification::centred);
        }

        void paintPanel (juce::Graphics& g, int k)
        {
            // title
            auto tr = panel[k].withHeight (20.0f);
            g.setColour (red); g.setFont (impact (14.0f));
            g.drawText (kinds[k].title, tr.withWidth (30), juce::Justification::centredLeft);
            g.setColour (dim); g.setFont (font (8.5f));
            g.drawText (juce::String (kinds[k].sub).toUpperCase(), tr.withTrimmedLeft (30), juce::Justification::centredLeft);

            // matrix background
            auto in = inset[k];
            g.setGradientFill (juce::ColourGradient (juce::Colour (0xff1c0a0a), in.getCentre(), juce::Colour (0xff0b0404), in.getTopLeft(), true));
            g.fillRoundedRectangle (in, 4.0f);
            g.setColour (line); g.drawRoundedRectangle (in.reduced (0.5f), 4.0f, 1.0f);

            if (hover.k == k && hover.part == Cell)
            {
                g.setColour (juce::Colours::white.withAlpha (0.04f));
                g.fillRect (cellRect (k, hover.s, hover.d));
            }

            // connections (under the nodes)
            for (int s = 0; s < 6; ++s)
                for (int d = 0; d < 6; ++d)
                {
                    if (s == d) continue;
                    float v = val (k, s, d);
                    if (! on (v)) continue;
                    auto a = nodeRect (k, s).getCentre(), m = cellRect (k, s, d).getCentre(), z = nodeRect (k, d).getCentre();
                    juce::Path p; p.startNewSubPath (a); p.lineTo (m); p.lineTo (z);
                    juce::Colour col = juce::Colour (0xffff5a4a);
                    float a1 = 0.45f + 0.5f * v / 100.0f, w = 1.2f + 2.2f * v / 100.0f;
                    juce::PathStrokeType glow (w + 4.0f, juce::PathStrokeType::curved, juce::PathStrokeType::rounded);
                    g.setColour (col.withAlpha (0.10f)); g.strokePath (p, glow);
                    g.setColour (col.withAlpha (a1));
                    g.strokePath (p, juce::PathStrokeType (w, juce::PathStrokeType::curved, juce::PathStrokeType::rounded));
                }

            static const char* L = "ABCDEF";
            for (int s = 0; s < 6; ++s)
                for (int d = 0; d < 6; ++d)
                {
                    float v = val (k, s, d);
                    auto c = cellRect (k, s, d);
                    if (s != d)
                    {
                        if (on (v)) { float w = juce::jmax (22.0f, 8.0f + pct (v).length() * 6.0f); drawValueBox (g, juce::Rectangle<float> (w, 15).withCentre (c.getCentre()), pct (v), false, true); }
                        else { g.setColour (juce::Colour (0xff000000)); g.fillEllipse (juce::Rectangle<float> (7, 7).withCentre (c.getCentre())); g.setColour (juce::Colour (0xff5a2a26)); g.fillEllipse (juce::Rectangle<float> (5, 5).withCentre (c.getCentre())); }
                    }
                    else
                    {
                        bool act = false;
                        for (int j = 0; j < 6 && ! act; ++j) act = on (val (k, s, j)) || on (val (k, j, s));
                        auto n = nodeRect (k, s);
                        bool hv = hover.k == k && hover.s == s && hover.part == Node;
                        if (act) { g.setColour (glow); g.fillRoundedRectangle (n.expanded (4), 9.0f); }
                        g.setGradientFill (act ? juce::ColourGradient (juce::Colour (0xffff4a3a), n.getX(), n.getY(), juce::Colour (0xffa3140c), n.getX(), n.getBottom(), false)
                                               : juce::ColourGradient (juce::Colour (hv ? 0xff3c3d41 : 0xff303134), n.getX(), n.getY(), juce::Colour (0xff17181a), n.getX(), n.getBottom(), false));
                        g.fillRoundedRectangle (n, 6.0f);
                        g.setColour (act ? juce::Colour (0xffff6a5c) : (hv ? red : juce::Colour (0xff4c4d51))); g.drawRoundedRectangle (n.reduced (0.5f), 6.0f, 1.0f);
                        g.setColour (act ? juce::Colours::white : dim); g.setFont (impact (n.getHeight() * 0.55f));
                        g.drawText (juce::String::charToString ((juce::juce_wchar) L[s]), n.toNearestInt(), juce::Justification::centred);

                        auto f = fbRect (k, s);
                        g.setColour (dim); g.setFont (font (7.0f));
                        g.drawText ("FB", f.withHeight (9).toNearestInt(), juce::Justification::centred);
                        drawValueBox (g, f.withTrimmedTop (10).withSizeKeepingCentre (f.getWidth(), 15).withY (f.getY() + 10), pct (v), false, on (v));
                    }

                    // modulation: dot with the colour of the first source, number of sources when more than one
                    auto mods = modsOf (k, s, d);
                    if (! mods.empty())
                    {
                        auto dr = modDotRect (k, s, d);
                        g.setColour (srcColour (mods[0].src)); g.fillEllipse (dr);
                        if (mods.size() > 1) { g.setColour (juce::Colours::black); g.setFont (font (7.0f, true)); g.drawText (juce::String ((int) mods.size()), dr, juce::Justification::centred); }
                    }
                }

            // a modulation source is being dragged over a cell
            if (modHover.k == k && modHover.part != None && modHover.part != Node)
            {
                auto c = cellRect (k, modHover.s, modHover.d).reduced (2);
                g.setColour (red.withAlpha (0.22f)); g.fillRoundedRectangle (c, 5.0f);
                g.setColour (red); g.drawRoundedRectangle (c, 5.0f, 1.5f);
            }
        }
    };
    constexpr FmPage::Impl::Kind FmPage::Impl::kindsFm[3];
    constexpr FmPage::Impl::Kind FmPage::Impl::kindsRm[2];

    static void refreshHover (FmPage& p, FmPage::Impl& i, juce::Point<float> pos)
    {
        auto h = i.hitTest (pos);
        if (! (h == i.hover)) { i.hover = h; p.repaint(); i.describe (h); }
        p.setMouseCursor (h.part == FmPage::Impl::Cell || h.part == FmPage::Impl::Fb ? juce::MouseCursor::UpDownResizeCursor
                          : h.part == FmPage::Impl::Node ? juce::MouseCursor::PointingHandCursor : juce::MouseCursor::NormalCursor);
    }

        struct Overlay : public juce::Component, public juce::DragAndDropTarget
        {
            Overlay (FmPage& p, FmPage::Impl& i) : page (p), im (i)
            {
                setInterceptsMouseClicks (true, false);
                addChildComponent (anchor); anchor.setInterceptsMouseClicks (false, false);
            }
            FmPage& page; FmPage::Impl& im;
            juce::Component anchor;   // invisible, parked over a cell so the amount popup opens next to it

            // ---- drop of a modulation source (LFO / ENV / VEL / KEY / RND handle) onto a cell ----
            bool isInterestedInDragSource (const SourceDetails& d) override
            {
                auto t = d.description.toString();   // Freq modulators only reach the cutoff and Frequency knobs
                return t.startsWith (kModDrag) && t.fromFirstOccurrenceOf (kModDrag, false, false).getIntValue() < 24;
            }
            void setModHover (juce::Point<int> p)
            {
                auto h = im.hitTest (p.toFloat());
                if (h.part == FmPage::Impl::Node) h = {};
                if (! (h == im.modHover)) { im.modHover = h; page.repaint(); }
            }
            void itemDragEnter (const SourceDetails& d) override { setModHover (d.localPosition); }
            void itemDragMove (const SourceDetails& d) override  { setModHover (d.localPosition); }
            void itemDragExit (const SourceDetails&) override    { im.modHover = {}; page.repaint(); }
            void itemDropped (const SourceDetails& d) override
            {
                auto h = im.hitTest (d.localPosition.toFloat());
                im.modHover = {}; page.repaint();
                if (h.part == FmPage::Impl::None || h.part == FmPage::Impl::Node) return;
                int id = im.pid (h.k, h.s, h.d);
                if (! im.ctx.isModTarget (id)) return;
                int src = d.description.toString().fromFirstOccurrenceOf (kModDrag, false, false).getIntValue();
                if (im.ctx.modAssign (src, modTarget().at (id).first, 0.5f) < 0) { im.ctx.status ("MOD MATRIX FULL (20 SLOTS)"); return; }
                openPopup (h);
            }
            void openPopup (const FmPage::Impl::Hit& h)
            {
                anchor.setBounds (im.cellRect (h.k, h.s, h.d).toNearestInt());
                showModPopup (im.ctx, anchor, im.pid (h.k, h.s, h.d));
            }

            void mouseMove (const juce::MouseEvent& e) override { refreshHover (page, im, e.position); }
            void mouseExit (const juce::MouseEvent&) override { im.hover = {}; page.repaint(); }
            void mouseDown (const juce::MouseEvent& e) override
            {
                auto h = im.hitTest (e.position);
                im.drag = h; im.dragMoved = false; im.dragging = false;
                if (h.part == FmPage::Impl::None) return;
                if (h.part != FmPage::Impl::Node && ! im.modsOf (h.k, h.s, h.d).empty() && im.modDotRect (h.k, h.s, h.d).expanded (3).contains (e.position))
                { im.drag = {}; openPopup (h); return; }
                if (h.part == FmPage::Impl::Node) return;
                if (e.mods.isPopupMenu()) { im.setVal (h, 0); return; }
                int id = im.pid (h.k, h.s, h.d);
                im.dragStartV = im.ctx.get (id); im.dragStartY = e.getMouseDownY(); im.dragging = true;
                im.ctx.begin (id);
            }
            void mouseDrag (const juce::MouseEvent& e) override
            {
                if (! im.dragging) return;
                if (std::abs (e.y - im.dragStartY) > 3) im.dragMoved = true;
                if (im.dragMoved) im.setVal (im.drag, im.dragStartV + (float) (im.dragStartY - e.y) * (e.mods.isShiftDown() ? 0.2f : 0.8f));
            }
            void mouseUp (const juce::MouseEvent& e) override
            {
                auto h = im.drag;
                if (h.part == FmPage::Impl::Node)
                {
                    if (im.hitTest (e.position) == h && ! e.mods.isPopupMenu() && im.openOsc) im.openOsc (h.s);
                    im.drag = {};
                    return;
                }
                if (im.dragging)
                {
                    int id = im.pid (h.k, h.s, h.d);
                    if (! im.dragMoved && im.ctx.get (id) < 0.5f) im.setVal (h, 50.0f);
                    im.ctx.end (id);
                }
                im.dragging = false; im.drag = {};
            }
            void mouseDoubleClick (const juce::MouseEvent& e) override
            {
                auto h = im.hitTest (e.position);
                if (h.part == FmPage::Impl::Cell || h.part == FmPage::Impl::Fb) im.setVal (h, 0);
            }
            void mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w) override
            {
                auto h = im.hitTest (e.position);
                if (h.part != FmPage::Impl::Cell && h.part != FmPage::Impl::Fb) return;
                float d = w.deltaY > 0 ? 2.0f : (w.deltaY < 0 ? -2.0f : 0.0f);
                if (d != 0.0f) im.setVal (h, im.val (h.k, h.s, h.d) + d);
            }
        };

    FmPage::FmPage (Ctx& c, int page) : impl (new Impl (*this, c, page)) { impl->pageNo = page; impl->overlay.reset (new Overlay (*this, *impl)); addAndMakeVisible (*impl->overlay); }
    FmPage::~FmPage() = default;
    void FmPage::setOnOpenOsc (std::function<void (int)> f) { impl->openOsc = std::move (f); }

    void FmPage::resized()
    {
        auto r = getLocalBounds().toFloat();
        impl->headRect = r.withHeight (30).reduced (12, 0);
        auto body = r.reduced (12, 0).withTrimmedTop (34).withTrimmedBottom (28);
        impl->noteRect = r.withTrimmedTop (r.getHeight() - 26).reduced (14, 2);
        float gap = 12, w = (body.getWidth() - (impl->nk - 1) * gap) / impl->nk;
        impl->overlay->setBounds (getLocalBounds());
        for (int k = 0; k < impl->nk; ++k)
        {
            auto p = juce::Rectangle<float> (body.getX() + k * (w + gap), body.getY(), w, body.getHeight());
            impl->panel[k] = p;
            impl->inset[k] = p.withTrimmedTop (22);
            impl->grid[k] = impl->inset[k].reduced (6);
        }
    }

    void FmPage::paint (juce::Graphics& g)
    {
        paintCard (g, getLocalBounds().toFloat());
        g.setColour (red); g.fillRect (juce::Rectangle<float> (12, 13, 7, 7));
        g.setFont (impact (11.0f)); g.drawText (impl->pageNo == 1 ? "RING / AMPLITUDE MODULATION MATRIX" : "FM / PM / PD MATRIX", 24, 8, 320, 16, juce::Justification::centredLeft);
        g.setColour (dim); g.setFont (font (8.0f));
        g.drawText (impl->pageNo == 1
                        ? "The letter in a row modulates the letter in the column it meets. RM = ring modulation (carrier x modulator), AM = amplitude modulation (carrier x 0..1 modulator). "
                          "0 = off, 100 = 100%. Click a dot to connect, drag up / down (Shift = fine), double-click to clear. FB = self modulation. Click a letter to open that oscillator."
                        : "The letter in a row modulates the letter in the column it meets. FM = carrier pitch (+-4 octaves at 100%), PM = phase shift, PD = phase distortion. 0 = off, 100 = 100%. "
                          "Click a dot to connect, drag up / down (Shift = fine), double-click to clear. FB = self feedback. Click a letter to open that oscillator.",
                    impl->noteRect.toNearestInt(), juce::Justification::centredLeft, 2);
        for (int k = 0; k < impl->nk; ++k) impl->paintPanel (g, k);
    }
}
