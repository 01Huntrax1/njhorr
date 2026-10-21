// FX page: three racks (Bus 1, Bus 2, Main) of 10 slots + the output section. Port of the FX rack of patch/index.js.
#include "../NjoPages.h"

namespace njo
{
    using namespace theme;

    namespace
    {
        constexpr int kRowH = 31;

        // ---- compact controls used inside a row ----
        class CompactKnob : public ParamWidget
        {
        public:
            CompactKnob (Ctx& c, int n, int slotG, int pIndex) : ParamWidget (c, n), g (slotG), pi (pIndex) {}
            void setUsed (bool u) { used = u; setVisible (u); }
            void paint (juce::Graphics& gr) override
            {
                auto b = getLocalBounds().toFloat();
                auto kr = b.removeFromLeft (26.0f).reduced (1.0f);
                float d = juce::jmin (kr.getWidth(), kr.getHeight());
                auto knob = juce::Rectangle<float> (d, d).withCentre (kr.getCentre());
                paintKnob (gr, knob, (float) sp->toNorm (val), false, hover, dragging);
                gr.setFont (font (8.0f, true)); gr.setColour (dim);
                auto t = fxLabel();
                gr.drawText (t.toUpperCase(), b.removeFromTop (b.getHeight() * 0.5f).toNearestInt(), juce::Justification::bottomLeft, true);
                gr.setFont (mono (8.5f, true)); gr.setColour (orange);
                gr.drawText (valueString(), b.toNearestInt(), juce::Justification::topLeft, true);
            }
            juce::String fxLabel() const
            {
                int ty = ctx.fxSlotTypes()[g];
                auto& t = fxTypes()[(size_t) juce::jlimit (0, (int) fxTypes().size() - 1, ty)];
                if (pi < 0) return "Mix";
                return pi < (int) t.params.size() ? t.params[(size_t) pi].name : juce::String();
            }
            void mouseDown (const juce::MouseEvent& e) override { if (e.mods.isPopupMenu()) { setValueFromUser ((float) sp->init); return; } dragging = true; startN = sp->toNorm (val); startY = e.y; ctx.begin (paramNum); repaint(); }
            void mouseDrag (const juce::MouseEvent& e) override { setValueFromUser ((float) sp->fromNorm (startN + (startY - e.y) * (e.mods.isShiftDown() ? 0.0012 : 0.006))); }
            void mouseUp (const juce::MouseEvent&) override { dragging = false; ctx.end (paramNum); repaint(); }
            void mouseDoubleClick (const juce::MouseEvent&) override { setValueFromUser ((float) sp->init); }
            void mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w) override { setValueFromUser ((float) sp->fromNorm (sp->toNorm (val) + (e.mods.isShiftDown() ? 0.002 : 0.02) * (w.deltaY > 0 ? 1 : -1))); }
            int g, pi; bool used = true; double startN = 0; int startY = 0;
        };

        class CompactSelect : public ParamWidget
        {
        public:
            CompactSelect (Ctx& c, int n, bool isType) : ParamWidget (c, n), type (isType) {}
            std::function<void (int)> onUserChange;
            juce::StringArray names; std::vector<std::pair<int, juce::String>> groups;
            void paint (juce::Graphics& gr) override
            {
                auto r = getLocalBounds().toFloat().reduced (0, 3.0f);
                paintButton (gr, r, false, hover, false, 3.0f);
                gr.setColour (ink); gr.setFont (font (11.0f, true));
                int idx = juce::roundToInt (val - sp->min);
                gr.drawText (idx >= 0 && idx < names.size() ? names[idx] : valueString(), r.reduced (7, 0).toNearestInt(), juce::Justification::centredLeft, true);
                juce::Path t; auto a = juce::Rectangle<float> (r.getRight() - 15, r.getCentreY() - 3, 9, 6);
                t.addTriangle (a.getX(), a.getY(), a.getRight(), a.getY(), a.getCentreX(), a.getBottom());
                gr.setColour (red); gr.fillPath (t);
            }
            void mouseDown (const juce::MouseEvent&) override
            {
                juce::PopupMenu m; size_t gi = 0;
                for (int i = 0; i < names.size(); ++i)
                {
                    while (gi < groups.size() && groups[gi].first == i) { if (groups[gi].second.isNotEmpty()) m.addSectionHeader (groups[gi].second); ++gi; }
                    m.addItem (i + 1, names[i], true, juce::roundToInt (val - sp->min) == i);
                }
                auto self = juce::Component::SafePointer<CompactSelect> (this);
                m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (this).withMinimumWidth (getWidth()).withMaximumNumColumns (type ? 1 : 3), [self] (int r)
                {
                    if (self == nullptr || r <= 0) return;
                    self->ctx.begin (self->paramNum); self->setValueFromUser ((float) (self->sp->min + r - 1)); self->ctx.end (self->paramNum);
                    if (self->onUserChange) self->onUserChange (r - 1);
                });
            }
            bool type;
        };

        class OnToggle : public ParamWidget
        {
        public:
            OnToggle (Ctx& c, int n) : ParamWidget (c, n) {}
            void paint (juce::Graphics& gr) override
            {
                auto r = getLocalBounds().toFloat().reduced (1.0f, 5.0f);
                bool on = val > 0.5f;
                paintButton (gr, r, on, hover, false, 3.0f);
                gr.setColour (on ? juce::Colours::white : dim); gr.setFont (font (9.0f, true));
                gr.drawText (on ? "ON" : "OFF", r.toNearestInt(), juce::Justification::centred);
            }
            void mouseDown (const juce::MouseEvent&) override { ctx.begin (paramNum); setValueFromUser (val > 0.5f ? 0.0f : 1.0f); ctx.end (paramNum); }
        };

        struct Row : public juce::Component
        {
            int rk = 0, sl = 0, g = 0;
            std::unique_ptr<OnToggle> on; std::unique_ptr<CompactSelect> ty, md; std::unique_ptr<CompactKnob> mix; std::unique_ptr<CompactKnob> ps[6];
            int pos = 0; bool empty = true, off = false, dragging = false;
            juce::Rectangle<int> upR, dnR, gripR;
            void paint (juce::Graphics& gr) override
            {
                auto r = getLocalBounds().toFloat().reduced (0, 1.0f);
                gr.setColour (dragging ? juce::Colour (0xff3a1815) : juce::Colour (0xff131415)); gr.fillRoundedRectangle (r, 2.0f);
                if (! empty) { gr.setColour (red.withAlpha (off ? 0.0f : 0.5f)); gr.fillRect (r.getX(), r.getY() + 2, 2.0f, r.getHeight() - 4); }
                gr.setColour (empty ? dim.withAlpha (0.5f) : orange); gr.setFont (mono (11.0f, true));
                gr.drawText (juce::String (pos + 1), juce::Rectangle<int> (16, 0, 12, getHeight()), juce::Justification::centred);
                gr.setColour (dim);
                for (auto& a : { upR, dnR })
                {
                    juce::Path p; auto c = a.toFloat();
                    if (&a == &upR) p.addTriangle (c.getX() + 1, c.getBottom() - 2, c.getRight() - 1, c.getBottom() - 2, c.getCentreX(), c.getY() + 2);
                    else p.addTriangle (c.getX() + 1, c.getY() + 2, c.getRight() - 1, c.getY() + 2, c.getCentreX(), c.getBottom() - 2);
                    gr.fillPath (p);
                }
                gr.setColour (dim.withAlpha (0.8f));
                for (int i = 0; i < 3; ++i) for (int j = 0; j < 2; ++j) gr.fillEllipse ((float) gripR.getX() + 2 + j * 5, (float) gripR.getY() + 8 + i * 5.0f, 2.2f, 2.2f);
                if (off && ! empty) { gr.setColour (juce::Colours::black.withAlpha (0.35f)); gr.fillRoundedRectangle (r.withTrimmedLeft (60), 2.0f); }
            }
            void resized() override
            {
                auto b = getLocalBounds();
                upR = { 2, 3, 12, 11 }; dnR = { 2, getHeight() - 14, 12, 11 };
                gripR = { 30, 0, 14, getHeight() };
                int x = 48;
                on->setBounds (x, 0, 40, getHeight()); x += 44;
                ty->setBounds (x, 0, 128, getHeight()); x += 134;
                md->setBounds (x, 0, 100, getHeight()); x += 106;
                mix->setBounds (x, 0, 78, getHeight()); x += 84;
                int w = juce::jmax (60, (b.getWidth() - x - 6) / 6);
                for (int k = 0; k < 6; ++k) ps[k]->setBounds (x + k * w, 0, w - 4, getHeight());
            }
        };

        struct DotTab : public juce::Component
        {
            juce::String text; bool on = false, used = false, over = false; std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintButton (g, r, on, over, false, 2.0f);
                g.setColour (on ? juce::Colour (0xff111111) : ink); g.setFont (font (9.5f, true));
                g.drawText (text.toUpperCase(), r.withTrimmedRight (12).toNearestInt(), juce::Justification::centred);
                auto d = juce::Rectangle<float> (r.getRight() - 12, r.getCentreY() - 3, 6, 6);
                g.setColour (used ? (on ? juce::Colour (0xff111111) : orange) : juce::Colour (0xff3a1f1c)); g.fillEllipse (d);
            }
            void mouseEnter (const juce::MouseEvent&) override { over = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { over = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };
    }

    struct FxPage::Impl : public Ctx::Listener
    {
        Impl (FxPage& o, Ctx& c) : owner (o), ctx (c)
        {
            for (int rk = 0; rk < 3; ++rk)
                for (int sl = 0; sl < 10; ++sl)
                {
                    auto* r = new Row(); rows.add (r);
                    r->rk = rk; r->sl = sl; r->g = rk * 10 + sl;
                    int b = fxRacks()[(size_t) rk].id + sl * 10;
                    r->on  = std::make_unique<OnToggle> (ctx, b + 1);
                    r->ty  = std::make_unique<CompactSelect> (ctx, b, true);
                    r->md  = std::make_unique<CompactSelect> (ctx, b + 3, false);
                    r->mix = std::make_unique<CompactKnob> (ctx, b + 2, r->g, -1);
                    for (int k = 0; k < 6; ++k) r->ps[k] = std::make_unique<CompactKnob> (ctx, b + 4 + k, r->g, k);
                    for (auto* ch : std::initializer_list<juce::Component*> { r->on.get(), r->ty.get(), r->md.get(), r->mix.get() }) r->addAndMakeVisible (ch);
                    for (auto& p : r->ps) r->addAndMakeVisible (*p);
                    r->ty->names = fxNames();
                    r->ty->onUserChange = [this, g = r->g] (int) { applyTypeDefaults (g); };
                    owner.addChildComponent (r);
                    r->addMouseListener (&dragRelay, false);
                    refreshRow (*r);
                }
            const int tabRk[] = { 1, 2, 0 };
            for (int i = 0; i < 3; ++i)
            {
                auto* t = tabs.add (new DotTab()); t->text = fxRacks()[(size_t) tabRk[i]].name;
                t->click = [this, rk = tabRk[i]] { showRack (rk); };
                owner.addAndMakeVisible (t);
            }
            for (int num : { 28, 536, 175, 189, 221, 222 })
            {
                auto w = makeWidget (ctx, num, true);
                w->onModDropped = [this] (ParamWidget& p) { if (owner.onModDropped) owner.onModDropped (p); };
                owner.addAndMakeVisible (*w); outs.add (w.release());
            }
            ctx.addListener (this);
            showRack (0);
            applyOrders();
        }
        ~Impl() override { ctx.removeListener (this); }

        static juce::StringArray fxNames() { juce::StringArray a; for (auto& t : fxTypes()) a.add (t.name); return a; }

        void paramChanged (int num, float) override
        {
            auto loc = fxLocate (num);
            if (loc.valid)
            {
                if (loc.ord >= 0) applyOrder (loc.rk);
                else refreshRow (*rows[loc.g]);
                updateTabs();
            }
        }

        void refreshRow (Row& r)
        {
            int ty = ctx.fxSlotTypes()[r.g];
            auto& t = fxTypes()[(size_t) juce::jlimit (0, (int) fxTypes().size() - 1, ty)];
            r.empty = ty == 0;
            r.off = ctx.get (r.on->num()) < 0.5f;
            r.md->names = t.modes; r.md->groups = t.groups;
            bool hasMode = t.modes.size() > 0;
            r.on->setVisible (! r.empty); r.md->setVisible (! r.empty && hasMode); r.mix->setVisible (! r.empty);
            for (int k = 0; k < 6; ++k) r.ps[k]->setVisible (! r.empty && k < (int) t.params.size());
            r.repaint(); for (auto* c : { (juce::Component*) r.ty.get(), (juce::Component*) r.md.get(), (juce::Component*) r.mix.get() }) c->repaint();
            for (auto& p : r.ps) p->repaint();
        }

        // a new effect starts from its own sensible settings (user changes only)
        void applyTypeDefaults (int g)
        {
            int rk = g / 10, sl = g % 10, b = fxRacks()[(size_t) rk].id + sl * 10;
            auto& t = fxTypes()[(size_t) juce::jlimit (0, (int) fxTypes().size() - 1, ctx.fxSlotTypes()[g])];
            ctx.set (b + 1, 1.0f); ctx.set (b + 2, t.mix); ctx.set (b + 3, 0.0f);
            for (size_t k = 0; k < t.params.size(); ++k) ctx.set (b + 4 + (int) k, t.params[k].def);
            refreshRow (*rows[g]);
        }

        std::array<int, 10> orderNow (int rk) const
        {
            std::array<int, 10> o {};
            for (int k = 0; k < 10; ++k) o[(size_t) k] = juce::roundToInt (ctx.get (fxRacks()[(size_t) rk].ord + k));
            return o;
        }

        void applyOrders() { for (int rk = 0; rk < 3; ++rk) applyOrder (rk); }
        void applyOrder (int rk, const std::array<int, 10>* preview = nullptr)
        {
            auto order = preview ? *preview : orderNow (rk);
            int pos[10]; for (int& p : pos) p = -1;
            for (int k = 0; k < 10; ++k) if (order[(size_t) k] >= 0 && order[(size_t) k] < 10 && pos[order[(size_t) k]] < 0) pos[order[(size_t) k]] = k;
            int spare = 10; for (int sl = 0; sl < 10; ++sl) if (pos[sl] < 0) pos[sl] = spare++;
            for (int sl = 0; sl < 10; ++sl) { rows[rk * 10 + sl]->pos = pos[sl]; }
            layoutRows(); 
        }

        void commit (int rk, const std::array<int, 10>& order)
        {
            auto cur = orderNow (rk);
            for (int k = 0; k < 10; ++k) if (order[(size_t) k] != cur[(size_t) k]) ctx.set (fxRacks()[(size_t) rk].ord + k, (float) order[(size_t) k]);
            applyOrder (rk);
        }

        void move (int rk, int sl, int to)
        {
            auto order = orderNow (rk);
            int from = -1; for (int k = 0; k < 10; ++k) if (order[(size_t) k] == sl) from = k;
            if (from < 0) return;
            to = juce::jlimit (0, 9, to); if (to == from) return;
            std::vector<int> v (order.begin(), order.end()); v.erase (v.begin() + from); v.insert (v.begin() + to, sl);
            std::array<int, 10> n; for (int k = 0; k < 10; ++k) n[(size_t) k] = v[(size_t) k];
            commit (rk, n);
        }

        void showRack (int rk) { current = rk; for (auto* t : tabs) {} updateTabs(); layoutRows(); }
        void updateTabs()
        {
            const int tabRk[] = { 1, 2, 0 };
            for (int i = 0; i < 3; ++i)
            {
                bool used = false; for (int s = 0; s < 10; ++s) if (ctx.fxSlotTypes()[tabRk[i] * 10 + s] > 0) used = true;
                tabs[i]->used = used; tabs[i]->on = tabRk[i] == current; tabs[i]->repaint();
            }
        }

        void layoutRows()
        {
            auto list = rowsArea;
            for (auto* r : rows)
            {
                bool vis = r->rk == current;
                r->setVisible (vis);
                if (vis) r->setBounds (list.getX(), list.getY() + r->pos * kRowH, list.getWidth(), kRowH);
            }
        }

        // drag the grip / use the arrows
        struct Relay : public juce::MouseListener
        {
            Impl& im; Row* dragRow = nullptr;
            explicit Relay (Impl& i) : im (i) {}
            Row* rowOf (const juce::MouseEvent& e) { for (auto* c = e.eventComponent; c; c = c->getParentComponent()) if (auto* r = dynamic_cast<Row*> (c)) return r; return nullptr; }
            void mouseDown (const juce::MouseEvent& e) override
            {
                auto* r = dynamic_cast<Row*> (e.eventComponent); if (! r) return;
                auto p = e.getPosition();
                if (r->upR.expanded (2).contains (p)) im.move (r->rk, r->sl, r->pos - 1);
                else if (r->dnR.expanded (2).contains (p)) im.move (r->rk, r->sl, r->pos + 1);
                else if (r->gripR.contains (p)) { dragRow = r; r->dragging = true; r->toFront (false); r->repaint(); }
            }
            void mouseDrag (const juce::MouseEvent& e) override
            {
                if (! dragRow) return;
                auto pt = e.getEventRelativeTo (&im.owner).getPosition();
                int to = juce::jlimit (0, 9, (pt.y - im.rowsArea.getY()) / kRowH);
                auto order = im.orderNow (dragRow->rk);
                std::vector<int> v (order.begin(), order.end());
                v.erase (std::find (v.begin(), v.end(), dragRow->sl)); v.insert (v.begin() + to, dragRow->sl);
                std::array<int, 10> n; for (int k = 0; k < 10; ++k) n[(size_t) k] = v[(size_t) k];
                im.preview = n; im.hasPreview = true; im.applyOrder (dragRow->rk, &n);
            }
            void mouseUp (const juce::MouseEvent&) override
            {
                if (! dragRow) return;
                dragRow->dragging = false; dragRow->repaint();
                int rk = dragRow->rk; dragRow = nullptr;
                if (im.hasPreview) im.commit (rk, im.preview); else im.applyOrder (rk);
                im.hasPreview = false;
            }
        } dragRelay { *this };

        FxPage& owner; Ctx& ctx;
        juce::OwnedArray<Row> rows; juce::OwnedArray<DotTab> tabs; juce::OwnedArray<ParamWidget> outs;
        juce::Rectangle<int> rowsArea, mainCard, outCard;
        int current = 0; std::array<int, 10> preview {}; bool hasPreview = false;
    };

    FxPage::FxPage (Ctx& c) : impl (new Impl (*this, c)) {}
    FxPage::~FxPage() = default;

    void FxPage::resized()
    {
        auto b = getLocalBounds();
        impl->outCard = b.removeFromBottom (84); b.removeFromBottom (6);
        impl->mainCard = b;
        auto m = impl->mainCard.reduced (12, 8);
        auto head = m.removeFromTop (22);
        head.removeFromLeft (110);
        int x = head.getX();
        for (auto* t : impl->tabs) { t->setBounds (x, head.getY(), 76, 20); x += 80; }
        m.removeFromTop (6);
        impl->rowsArea = m.withHeight (kRowH * 10);
        impl->layoutRows();
        auto o = impl->outCard.reduced (12, 6); o.removeFromTop (18);
        int w = o.getWidth() / 6;
        for (int i = 0; i < impl->outs.size(); ++i) impl->outs[i]->setBounds (o.getX() + i * w + 6, o.getY(), w - 12, o.getHeight());
    }

    void FxPage::paint (juce::Graphics& g)
    {
        paintCard (g, impl->mainCard.toFloat());
        paintCard (g, impl->outCard.toFloat());
        auto head = [&] (juce::Rectangle<int> card, const juce::String& t)
        {
            g.setColour (red); g.fillRect (juce::Rectangle<float> ((float) card.getX() + 12, (float) card.getY() + 13, 7, 7));
            g.setFont (impact (11.0f)); g.drawText (t, card.getX() + 24, card.getY() + 8, 90, 16, juce::Justification::centredLeft);
        };
        head (impl->mainCard, "FX"); head (impl->outCard, "OUTPUT");
        g.setColour (dim); g.setFont (font (8.5f));
        g.drawText ("Bus 1 + Bus 2 feed Main  -  signal runs top to bottom", impl->mainCard.withTrimmedLeft (320).withHeight (30).reduced (10, 0), juce::Justification::centredRight, true);
    }
}
