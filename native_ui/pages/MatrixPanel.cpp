// The 20 slot modulation matrix and the amount popup shown after dropping a source on a parameter.
#include "ModUi.h"

namespace njo
{
    using namespace theme;

    struct MatrixPanel::Impl : Ctx::Listener
    {
        Ctx& ctx; MatrixPanel& owner;
        juce::OwnedArray<MiniSelect> src, dst;
        juce::OwnedArray<SliderWidget> amt;
        Impl (Ctx& c, MatrixPanel& o) : ctx (c), owner (o) { ctx.addListener (this); }
        ~Impl() override { ctx.removeListener (this); }
        void paramChanged (int n, float) override { if ((n >= 307 && n <= 336) || (n >= 472 && n <= 501)) owner.repaint(); }
        bool active (int s) const { return ctx.get (slotBase (s)) > 0.5f && ctx.get (slotBase (s) + 1) > 0.5f; }
    };

    MatrixPanel::MatrixPanel (Ctx& c) : impl (new Impl (c, *this))
    {
        for (int s = 0; s < MOD_SLOTS; ++s)
        {
            int b = slotBase (s);
            auto* a = impl->src.add (new MiniSelect());
            a->names = modSrc(); a->groups = modSrcGroups();
            a->getIndex = [&c, b] { return juce::roundToInt (c.get (b)); };
            a->setIndex = [&c, b] (int i) { c.begin (b); c.set (b, (float) i); c.end (b); };
            addAndMakeVisible (a);
            auto* d = impl->dst.add (new MiniSelect());
            d->names = modDst(); d->groups = modDstGroups();
            d->getIndex = [&c, b] { return juce::roundToInt (c.get (b + 1)); };
            d->setIndex = [&c, b] (int i) { c.begin (b + 1); c.set (b + 1, (float) i); c.end (b + 1); };
            addAndMakeVisible (d);
            auto* m = impl->amt.add (new SliderWidget (c, b + 2));
            m->setLabelOverride (" ");
            m->setValueTextOverride ([] (float v) { return juce::String (juce::roundToInt (v * 100)) + "%"; });
            addAndMakeVisible (m);
        }
    }
    MatrixPanel::~MatrixPanel() = default;

    static juce::Rectangle<int> rowRect (const juce::Rectangle<int>& area, int col, int k)
    {
        int colW = (area.getWidth() - 14) / 2, rowH = (area.getHeight() - 16) / 10;
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
                int s = col * 10 + k;
                auto r = rowRect (area, col, k);
                if (impl->active (s)) { g.setColour (red.withAlpha (0.13f)); g.fillRoundedRectangle (r.reduced (0, 1).toFloat(), 3.0f); }
                g.setColour (impl->active (s) ? red : dim); g.setFont (font (9.5f, true));
                g.drawText (juce::String (s + 1), r.withWidth (22), juce::Justification::centredRight);
            }
        }
    }

    void MatrixPanel::resized()
    {
        auto area = getLocalBounds().reduced (10, 6);
        for (int col = 0; col < 2; ++col)
            for (int k = 0; k < 10; ++k)
            {
                int s = col * 10 + k;
                auto r = rowRect (area, col, k).reduced (0, 2);
                r.removeFromLeft (28);
                int w = r.getWidth() - 16;
                impl->src[s]->setBounds (r.removeFromLeft ((int) (w * 0.31f)));
                r.removeFromLeft (8);
                impl->dst[s]->setBounds (r.removeFromLeft ((int) (w * 0.36f)));
                r.removeFromLeft (8);
                impl->amt[s]->setBounds (r);
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
