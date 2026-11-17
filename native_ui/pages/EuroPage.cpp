// Eurorack rack of Njohrr Modular: 20 module slots shown as panels; the selected module is edited on the right.
// Parameters (tools/modular/build_euro.py): slot m, id = kBase + kStride * m + k: 0 type, 1..8 knobs, 9 mode, 10..13 input source, 14..17 input gain, 18 FX type.
#include "../NjoPages.h"
#include "../NjoFxEx.h"
#include "../NjoTheme.h"
#include "../NjoEuro.h"

namespace njo
{
    using namespace theme;

    namespace
    {
        constexpr int kCols = 5, kRows = 4, kPanelW = 330;
        int pidOf (int m, int k) { return euro::kBase + euro::kStride * m + k; }
        juce::String srcName (int s)
        {
            if (s <= 0) return "-";
            if (s == 1) return "Synth L";
            if (s == 2) return "Synth R";
            if (s == 3) return "Audio L";
            if (s == 4) return "Audio R";
            int m = (s - 5) / 2, o = (s - 5) & 1;
            auto t = juce::jlimit (0, euro::kTypes - 1, 0);
            juce::ignoreUnused (t);
            return "M" + juce::String (m + 1) + (o ? " B" : " A");
        }
    }

    struct EuroPage::Impl : private Ctx::Listener, private juce::AsyncUpdater
    {
        Impl (EuroPage& o, Ctx& c) : owner (o), ctx (c) { ctx.addListener (this); rebuild(); }
        ~Impl() override { cancelPendingUpdate(); ctx.removeListener (this); }

        EuroPage& owner; Ctx& ctx;
        int selected = 0;
        juce::Rectangle<float> grid, side;
        std::vector<std::unique_ptr<ParamWidget>> panel;

        void paramChanged (int num, float) override
        {
            if (num < euro::kBase || num >= euro::kBase + euro::kStride * euro::kSlots) return;
            int m = (num - euro::kBase) / euro::kStride, k = (num - euro::kBase) % euro::kStride;
            if (m == selected && k == 0) triggerAsyncUpdate(); else owner.repaint();
        }
        void handleAsyncUpdate() override { rebuild(); owner.repaint(); }

        int typeOf (int m) const { return juce::jlimit (0, euro::kTypes - 1, juce::roundToInt (ctx.get (pidOf (m, 0)))); }
        juce::Rectangle<float> tile (int m) const
        {
            float w = grid.getWidth() / kCols, h = grid.getHeight() / kRows;
            return juce::Rectangle<float> (grid.getX() + (m % kCols) * w, grid.getY() + (m / kCols) * h, w, h).reduced (4.0f);
        }
        // name of the output / input jacks of the source number s as seen from the wiring
        juce::String jackText (int s) const
        {
            if (s >= 5)
            {
                int m = (s - 5) / 2, o = (s - 5) & 1;
                const auto& md = euro::mods()[typeOf (m)];
                return "M" + juce::String (m + 1) + " " + md.outs[o];
            }
            return srcName (s);
        }

        void rebuild()
        {
            for (auto& w : panel) owner.removeChildComponent (w.get());
            panel.clear();
            if (side.isEmpty()) return;
            auto add = [this] (std::unique_ptr<ParamWidget> w, juce::Rectangle<int> r) -> ParamWidget*
            {
                w->setBounds (r); owner.addAndMakeVisible (*w); panel.push_back (std::move (w)); return panel.back().get();
            };
            auto r = side.reduced (10, 8).toNearestInt();
            r.removeFromTop (24);
            const int m = selected, ty = typeOf (m);
            const auto& md = euro::mods()[ty];
            add (makeWidget (ctx, pidOf (m, 0), false), r.removeFromTop (34)); r.removeFromTop (4);
            if (ty == 0) return;
            if (md.nModes > 0)
            {
                juce::StringArray names;
                for (int i = 0; i < md.nModes; ++i) names.add (md.modes[i]);
                auto* w = add (makeWidget (ctx, pidOf (m, 9), false), r.removeFromTop (34));
                if (auto* s = dynamic_cast<SelectWidget*> (w)) s->setOptions (names);
                r.removeFromTop (4);
            }
            if (ty == 15) { add (makeWidget (ctx, pidOf (m, 18), false), r.removeFromTop (34)); r.removeFromTop (4); }
            int nk = 0; for (int k = 0; k < 8; ++k) if (md.knobs[k][0]) nk = k + 1;
            auto kn = r.removeFromTop (((nk + 3) / 4) * 64);
            for (int k = 0; k < 8; ++k)
            {
                if (! md.knobs[k][0]) continue;
                auto cell = juce::Rectangle<int> (kn.getX() + (k % 4) * (kn.getWidth() / 4), kn.getY() + (k / 4) * 64, kn.getWidth() / 4, 62);
                add (makeWidget (ctx, pidOf (m, 1 + k), true), cell)->setLabelOverride (md.knobs[k]);
            }
            if (ty == 15)   // FX-EX: the four effect specific knobs of the effect in rack slot 10 + m
            {
                auto er = r.removeFromTop (64);
                const int fty = ctx.fxSlotTypes()[10 + m];
                for (int k = 0; k < 4; ++k)
                {
                    auto* w = add (makeWidget (ctx, fxExId (10 + m, k), true), juce::Rectangle<int> (er.getX() + k * (er.getWidth() / 4), er.getY(), er.getWidth() / 4, 62));
                    w->setLabelOverride (fxExName (fxExTools (fty)[k]));
                    w->setValueTextOverride ([this, m, k] (float v) { return fxExText (fxExTools (ctx.fxSlotTypes()[10 + m])[k], v); });
                }
            }
            if (ty == 15)   // FX-WET: Low Cut, High Cut, Width, Sat of the FX module (its effect runs in rack slot 10 + m)
            {
                auto wr = r.removeFromTop (64);
                static const char* wl[4] = { "Low Cut", "High Cut", "Width", "Sat" };
                for (int k = 0; k < 4; ++k)
                {
                    auto* w = add (makeWidget (ctx, fxWetId (10 + m, k), true), juce::Rectangle<int> (wr.getX() + k * (wr.getWidth() / 4), wr.getY(), wr.getWidth() / 4, 62));
                    w->setLabelOverride (wl[k]);
                    w->setValueTextOverride ([k] (float v)
                    {
                        if (k == 0) return v < 0.002f ? juce::String ("Off") : juce::String (juce::roundToInt (20.0 * std::pow (50.0, (double) v))) + " Hz";
                        if (k == 1) return v > 0.998f ? juce::String ("Off") : juce::String (juce::roundToInt (1500.0 * std::pow (13.3333, (double) v))) + " Hz";
                        return juce::String (juce::roundToInt (v * (k == 2 ? 200 : 100))) + "%";
                    });
                }
            }
            r.removeFromTop (8);
            for (int c = 0; c < 4; ++c)
            {
                if (! md.ins[c][0]) continue;
                auto row = r.removeFromTop (34);
                add (makeWidget (ctx, pidOf (m, 10 + c), false), row.removeFromLeft (200))->setLabelOverride (md.ins[c]);
                row.removeFromLeft (6);
                add (makeWidget (ctx, pidOf (m, 14 + c), false), row);
                r.removeFromTop (3);
            }
        }
    };

    EuroPage::EuroPage (Ctx& c) : impl (new Impl (*this, c)) { setWantsKeyboardFocus (false); }
    EuroPage::~EuroPage() = default;

    void EuroPage::resized()
    {
        auto r = getLocalBounds().toFloat();
        impl->side = r.removeFromRight ((float) kPanelW);
        r.removeFromRight (6.0f);
        impl->grid = r.reduced (4.0f);
        impl->rebuild();
    }

    void EuroPage::paint (juce::Graphics& g)
    {
        auto& m = *impl;
        paintCard (g, m.grid.expanded (4.0f));
        paintCard (g, m.side);
        const auto* tbl = euro::mods();
        g.setColour (red); g.setFont (impact (14.0f));
        g.drawText ("M" + juce::String (m.selected + 1) + "  " + tbl[m.typeOf (m.selected)].name, m.side.reduced (12, 8).removeFromTop (22).toNearestInt(), juce::Justification::centredLeft);
        for (int i = 0; i < euro::kSlots; ++i)
        {
            auto r = m.tile (i); int ty = m.typeOf (i); const auto& md = tbl[ty];
            g.setGradientFill (vertical (juce::Colour (0xff2c2e32), juce::Colour (0xff1c1d20), r));
            g.fillRoundedRectangle (r, 5.0f);
            g.setColour (i == m.selected ? red : line); g.drawRoundedRectangle (r, 5.0f, i == m.selected ? 2.0f : 1.0f);
            auto in = r.reduced (8, 6);
            g.setColour (ty == 0 ? dim : ink); g.setFont (font (11.0f, true));
            g.drawText (juce::String (i + 1) + "  " + md.name, in.removeFromTop (16).toNearestInt(), juce::Justification::centredLeft, true);
            g.setFont (mono (8.5f));
            for (int c = 0; c < 4 && ty != 0; ++c)
            {
                if (! md.ins[c][0]) continue;
                int s = juce::roundToInt (m.ctx.get (pidOf (i, 10 + c)));
                g.setColour (s > 0 ? ink : dim);
                g.drawText (juce::String (md.ins[c]) + " <- " + m.jackText (s), in.removeFromTop (11).toNearestInt(), juce::Justification::centredLeft, true);
            }
            if (ty != 0 && md.outs[0][0])
            {
                g.setColour (orange);
                g.drawText (juce::String ("out: ") + md.outs[0] + (md.outs[1][0] ? juce::String (" / ") + md.outs[1] : juce::String()), r.reduced (8, 4).removeFromBottom (11).toNearestInt(), juce::Justification::centredLeft, true);
            }
        }
    }

    void EuroPage::mouseDown (const juce::MouseEvent& e)
    {
        auto& m = *impl;
        for (int i = 0; i < euro::kSlots; ++i)
            if (m.tile (i).contains (e.position)) { m.selected = i; m.rebuild(); repaint(); return; }
    }
}
