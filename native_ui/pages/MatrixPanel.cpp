// The modulation matrix (pages of 20 slots) and the amount popup shown after dropping a source on a parameter.
#include "ModUi.h"

namespace njo
{
    using namespace theme;

    struct MatrixPanel::Impl : Ctx::Listener
    {
        static constexpr int PER_PAGE = 20;
        Ctx& ctx; MatrixPanel& owner;
        std::vector<std::unique_ptr<MiniSelect>> src, dst;
        std::vector<std::unique_ptr<SliderWidget>> amt;
        juce::TextButton prev { "<" }, next { ">" };
        int page = 0;
        Impl (Ctx& c, MatrixPanel& o) : ctx (c), owner (o)
        {
            src.resize (MOD_SLOTS); dst.resize (MOD_SLOTS); amt.resize (MOD_SLOTS);
            ctx.addListener (this);
        }
        ~Impl() override { ctx.removeListener (this); }
        static bool isMatrixParam (int n) { return isModSlotParam (n); }
        void paramChanged (int n, float) override { if (isMatrixParam (n)) owner.repaint(); }
        bool active (int s) const { return ctx.get (slotBase (s)) > 0.5f && ctx.get (slotBase (s) + 1) > 0.5f; }
        int used() const { int u = 0; for (int s = 0; s < MOD_SLOTS; ++s) if (active (s)) u = s + 1; return u; }
        int pages() const { return juce::jmin ((MOD_SLOTS + PER_PAGE - 1) / PER_PAGE, used() / PER_PAGE + 1); }

        void build (int s)
        {
            if (src[(size_t) s] != nullptr) return;
            int b = slotBase (s);
            auto* a = (src[(size_t) s] = std::make_unique<MiniSelect>()).get();
            a->names = modSrc(); a->groups = modSrcGroups();
            a->getIndex = [this, b] { return juce::roundToInt (ctx.get (b)); };
            a->setIndex = [this, b] (int i) { ctx.begin (b); ctx.set (b, (float) i); ctx.end (b); };
            owner.addChildComponent (a);
            auto* d = (dst[(size_t) s] = std::make_unique<MiniSelect>()).get();
            d->names = modDst(); d->groups = modDstGroups();
            d->getIndex = [this, b] { return juce::roundToInt (ctx.get (b + 1)); };
            d->setIndex = [this, b] (int i) { ctx.begin (b + 1); ctx.set (b + 1, (float) i); ctx.end (b + 1); };
            owner.addChildComponent (d);
            auto* m = (amt[(size_t) s] = std::make_unique<SliderWidget> (ctx, b + 2)).get();
            m->setLabelOverride (" ");
            m->setValueTextOverride ([] (float v) { return juce::String (juce::roundToInt (v * 100)) + "%"; });
            owner.addChildComponent (m);
        }

        void showPage (int p)
        {
            page = juce::jlimit (0, pages() - 1, p);
            for (int s = 0; s < MOD_SLOTS; ++s)
            {
                bool vis = s / PER_PAGE == page;
                if (vis) build (s);
                if (src[(size_t) s] != nullptr) { src[(size_t) s]->setVisible (vis); dst[(size_t) s]->setVisible (vis); amt[(size_t) s]->setVisible (vis); }
            }
            prev.setEnabled (page > 0); next.setEnabled (page < pages() - 1);
            owner.resized(); owner.repaint();
        }
    };

    MatrixPanel::MatrixPanel (Ctx& c) : impl (new Impl (c, *this))
    {
        for (auto* b : { &impl->prev, &impl->next }) { addAndMakeVisible (b); b->setColour (juce::TextButton::buttonColourId, juce::Colour (0xff202124)); b->setColour (juce::TextButton::textColourOffId, theme::dim); }
        impl->prev.onClick = [this] { impl->showPage (impl->page - 1); };
        impl->next.onClick = [this] { impl->showPage (impl->page + 1); };
        impl->showPage (0);
    }
    MatrixPanel::~MatrixPanel() = default;
    void MatrixPanel::setPage (int page) { impl->showPage (page); }

    static constexpr int NAV_H = 22;

    static juce::Rectangle<int> rowRect (const juce::Rectangle<int>& area, int col, int k)
    {
        int colW = (area.getWidth() - 14) / 2, rowH = (area.getHeight() - 16 - NAV_H) / 10;
        return { area.getX() + col * (colW + 14), area.getY() + 16 + k * rowH, colW, rowH };
    }

    void MatrixPanel::paint (juce::Graphics& g)
    {
        paintCard (g, getLocalBounds().toFloat());
        auto area = getLocalBounds().reduced (10, 6);
        for (int col = 0; col < 2; ++col)
        {
            auto h = rowRect (area, col, 0).withY (area.getY()).withHeight (14);
            h.removeFromLeft (28);
            int w = h.getWidth() - 16;
            g.setFont (font (8.5f, true)); g.setColour (dim);
            g.drawText ("SOURCE", h.removeFromLeft ((int) (w * 0.31f)), juce::Justification::centred);
            h.removeFromLeft (8);
            g.drawText ("DESTINATION", h.removeFromLeft ((int) (w * 0.36f)), juce::Justification::centred);
            h.removeFromLeft (8);
            g.drawText ("AMOUNT", h, juce::Justification::centred);
            for (int k = 0; k < 10; ++k)
            {
                int s = impl->page * Impl::PER_PAGE + col * 10 + k;
                if (s >= MOD_SLOTS) break;
                auto r = rowRect (area, col, k);
                if (impl->active (s)) { g.setColour (red.withAlpha (0.13f)); g.fillRoundedRectangle (r.reduced (0, 1).toFloat(), 3.0f); }
                g.setColour (impl->active (s) ? red : dim); g.setFont (font (9.5f, true));
                g.drawText (juce::String (s + 1), r.withWidth (22), juce::Justification::centredRight);
            }
        }
        int first = impl->page * Impl::PER_PAGE + 1, last = juce::jmin (MOD_SLOTS, first + Impl::PER_PAGE - 1);
        g.setColour (dim); g.setFont (font (9.0f, true));
        g.drawText ("SLOTS " + juce::String (first) + " - " + juce::String (last) + "   |   PAGE " + juce::String (impl->page + 1) + " / " + juce::String (impl->pages()) + "   |   "
                    + juce::String (impl->used()) + " IN USE, " + juce::String (MOD_SLOTS) + " AVAILABLE",
                    getLocalBounds().removeFromBottom (NAV_H + 6).reduced (60, 0), juce::Justification::centred);
    }

    void MatrixPanel::resized()
    {
        auto area = getLocalBounds().reduced (10, 6);
        auto nav = getLocalBounds().removeFromBottom (NAV_H + 6).reduced (10, 3);
        impl->prev.setBounds (nav.removeFromLeft (40));
        impl->next.setBounds (nav.removeFromRight (40));
        for (int col = 0; col < 2; ++col)
            for (int k = 0; k < 10; ++k)
            {
                int s = impl->page * Impl::PER_PAGE + col * 10 + k;
                if (s >= MOD_SLOTS || impl->src[(size_t) s] == nullptr) continue;
                auto r = rowRect (area, col, k).reduced (0, 2);
                r.removeFromLeft (28);
                int w = r.getWidth() - 16;
                impl->src[(size_t) s]->setBounds (r.removeFromLeft ((int) (w * 0.31f)));
                r.removeFromLeft (8);
                impl->dst[(size_t) s]->setBounds (r.removeFromLeft ((int) (w * 0.36f)));
                r.removeFromLeft (8);
                impl->amt[(size_t) s]->setBounds (r);
            }
    }

    // ------------------------------------------------------------------ amount popup
    namespace
    {
        struct PopRow : juce::Component
        {
            Ctx& ctx; int slot;
            std::function<void()> onRemove;
            PopRow (Ctx& c, int s) : ctx (c), slot (s) {}
            float amt() const { return ctx.get (slotBase (slot) + 2); }
            juce::Rectangle<float> track() const { return { 70.0f, (float) getHeight() / 2 - 3.0f, (float) getWidth() - 70.0f - 74.0f, 6.0f }; }
            void paint (juce::Graphics& g) override
            {
                int src = juce::roundToInt (ctx.get (slotBase (slot)));
                auto pill = juce::Rectangle<float> (0, 3, 60, (float) getHeight() - 6);
                g.setColour (srcColour (src)); g.fillRoundedRectangle (pill, 9.0f);
                g.setColour (juce::Colours::black); g.setFont (font (9.0f, true)); g.drawText (srcShort (src), pill.toNearestInt(), juce::Justification::centred);
                auto t = track();
                g.setColour (juce::Colour (0xff090303)); g.fillRoundedRectangle (t, 2.0f);
                float n = (amt() + 1.0f) * 0.5f;
                g.setColour (red.withAlpha (0.85f)); g.fillRect (juce::jmin (n, 0.5f) * t.getWidth() + t.getX(), t.getY(), std::abs (n - 0.5f) * t.getWidth(), t.getHeight());
                g.setColour (juce::Colour (0xff85868b)); g.fillRoundedRectangle (t.getX() + n * t.getWidth() - 3, t.getY() - 4, 6, t.getHeight() + 8, 1.5f);
                g.setColour (orange); g.setFont (mono (10.0f, true));
                g.drawText (juce::String (juce::roundToInt (amt() * 100)) + "%", juce::Rectangle<int> (getWidth() - 72, 0, 48, getHeight()), juce::Justification::centredRight);
                g.setColour (dim); g.setFont (font (15.0f, true));
                g.drawText (juce::CharPointer_UTF8 ("\xc3\x97"), juce::Rectangle<int> (getWidth() - 20, 0, 20, getHeight()), juce::Justification::centred);
            }
            void setFrom (float x)
            {
                auto t = track();
                float v = juce::jlimit (-1.0f, 1.0f, (x - t.getX()) / t.getWidth() * 2.0f - 1.0f);
                v = std::round (v * 100.0f) / 100.0f;
                ctx.set (slotBase (slot) + 2, v); repaint();
            }
            void mouseDown (const juce::MouseEvent& e) override
            {
                if (e.x > getWidth() - 22) { if (onRemove) onRemove(); return; }
                if (e.x > 64) { ctx.begin (slotBase (slot) + 2); setFrom (e.position.x); }
            }
            void mouseDrag (const juce::MouseEvent& e) override { if (e.getMouseDownX() > 64 && e.getMouseDownX() <= getWidth() - 22) setFrom (e.position.x); }
            void mouseUp (const juce::MouseEvent& e) override { if (e.getMouseDownX() > 64 && e.getMouseDownX() <= getWidth() - 22) ctx.end (slotBase (slot) + 2); }
            void mouseDoubleClick (const juce::MouseEvent& e) override { if (e.x > 64 && e.x <= getWidth() - 22) { ctx.set (slotBase (slot) + 2, 0.0f); repaint(); } }
        };

        struct ModPopup : juce::Component
        {
            struct Panel : juce::Component
            {
                juce::String title; juce::OwnedArray<PopRow> rows;
                void paint (juce::Graphics& g) override
                {
                    g.setColour (juce::Colour (0xff17181a)); g.fillRoundedRectangle (getLocalBounds().toFloat(), 6.0f);
                    g.setColour (red.withAlpha (0.7f)); g.drawRoundedRectangle (getLocalBounds().toFloat().reduced (0.5f), 6.0f, 1.0f);
                    g.setColour (red); g.setFont (font (9.0f, true));
                    g.drawText (title.toUpperCase(), 10, 4, getWidth() - 20, 16, juce::Justification::centredLeft);
                }
            } panel;
            juce::Component::SafePointer<juce::Component> keep;
            void mouseDown (const juce::MouseEvent& e) override
            {
                if (! panel.getBounds().contains (e.getPosition())) close();
            }
            void close() { juce::Component::SafePointer<ModPopup> me (this); juce::MessageManager::callAsync ([me] { if (me) delete me.getComponent(); }); setVisible (false); }
        };
        juce::Component::SafePointer<ModPopup> current;
    }

    void showModPopup (Ctx& ctx, juce::Component& target, int paramNum)
    {
        if (current != nullptr) { delete current.getComponent(); current = nullptr; }
        if (! ctx.isModTarget (paramNum)) return;
        auto mods = ctx.modsFor (modTarget().at (paramNum).first);
        if (mods.empty()) return;
        juce::Component* host = nullptr;
        if (auto* dc = juce::DragAndDropContainer::findParentDragContainerFor (&target)) host = dynamic_cast<juce::Component*> (dc);
        if (host == nullptr) host = target.getTopLevelComponent();
        if (host == nullptr) return;

        auto* pop = new ModPopup();
        current = pop;
        auto* sp = findSpec (paramNum);
        pop->panel.title = (sp ? sp->name() : juce::String()) + " modulation";
        const int rowH = 24, pw = 270, ph = 24 + (int) mods.size() * rowH + 6;
        for (auto& m : mods)
        {
            auto* r = pop->panel.rows.add (new PopRow (ctx, m.s));
            int slot = m.s;
            r->onRemove = [&ctx, pop, slot] { ctx.modClear (slot); pop->close(); };
            pop->panel.addAndMakeVisible (r);
        }
        pop->addAndMakeVisible (pop->panel);
        host->addAndMakeVisible (pop);
        pop->setBounds (host->getLocalBounds());
        auto tb = host->getLocalArea (&target, target.getLocalBounds());
        int x = juce::jlimit (4, juce::jmax (4, host->getWidth() - pw - 4), tb.getCentreX() - pw / 2);
        int y = juce::jmin (host->getHeight() - ph - 4, tb.getBottom() + 6);
        pop->panel.setBounds (x, y, pw, ph);
        for (int i = 0; i < pop->panel.rows.size(); ++i) pop->panel.rows[i]->setBounds (8, 22 + i * rowH, pw - 16, rowH);
        pop->toFront (false);
    }
}
