// FX page: one rack (Main) of 16 slots, laid out like a modern synth's effect page: the list of the rack's effects on the left
// (processing order, on / off, move, drag), "+ ADD FX" opens a grid of all effect types, and the selected effect has its own page with a display and large knobs.
// Below: the output section. Parameters and the processing order are unchanged (patch/index.js FX rack).
#include <complex>
#include "../NjoPages.h"
#include "OscDisplays.h"
#include "../NjoFxEx.h"
#include "EqEditor.h"
#include "ShaperEditor.h"
#include "Editors.h"
#include <algorithm>
#include <array>
#include <cmath>

namespace njo
{

// response shape of the Filter effect modes in the voice filter model (oscmodel::filterH knows types 0..29): Korg35 LP/HP, Scream, then Polivoks, OTA/CEM/SSM, SEM, Diode, Steiner-Parker
static int fxFilterShape (int mode)
{
    static const int map[] = { 1, 2, 1,            // 30..32
                               1, 3, 2,            // Polivoks LP BP HP
                               0, 0, 0,            // OTA, CEM, SSM LP24
                               1, 3, 10, 2,        // SEM LP BP Notch HP
                               0,                  // Diode
                               1, 2 };             // Steiner LP HP
    return mode >= 30 ? map[juce::jlimit (0, 15, mode - 30)] : juce::jlimit (0, 29, mode);
}
    using namespace theme;

    namespace
    {
        constexpr int kItemH = 28, kLeftW = 214;

        juce::Colour fxColour (int type)
        {
            static const juce::uint32 c[] = { 0xff4e5157, 0xffe0803a, 0xffd860a8, 0xffe0507a, 0xff30d0d8, 0xffe08c40, 0xffa060e0, 0xff80d060, 0xff30c090, 0xff40a0e0, 0xffe8e8e8, 0xffe8c030, 0xff58b8f0, 0xffc8a0f0, 0xfff07a50, 0xfff0a050, 0xff7adf9a, 0xffd8b860, 0xff9ac865, 0xffa0e057, 0xff50c0b0, 0xffd09040, 0xff7a8088, 0xff90c050, 0xffc0a070, 0xff6090d0, 0xffa5d075, 0xff80b0e0, 0xffe04a3c, 0xff7ad8c8, 0xffd87ae0, 0xff6ac0ff, 0xffd8a050, 0xffc08a58, 0xff90c8a0, 0xffd0a878, 0xffb88860, 0xff98a0d8, 0xff78d0c0 , 0xff7fd0a8, 0xff60e0c8, 0xff70b0f0};
            return juce::Colour (c[juce::jlimit (0, 41, type)]);
        }

        class OnToggle : public ParamWidget
        {
        public:
            OnToggle (Ctx& c, int n) : ParamWidget (c, n) {}
            void paint (juce::Graphics& gr) override
            {
                auto r = getLocalBounds().toFloat().reduced (1.0f, 2.0f);
                bool on = val > 0.5f;
                paintButton (gr, r, on, hover, false, 3.0f);
                gr.setColour (on ? juce::Colours::white : dim); gr.setFont (font (9.5f, true));
                gr.drawText (on ? "ON" : "BYPASSED", r.toNearestInt(), juce::Justification::centred);
            }
            void mouseDown (const juce::MouseEvent&) override { ctx.begin (paramNum); setValueFromUser (val > 0.5f ? 0.0f : 1.0f); ctx.end (paramNum); }
        };

        struct DotTab : public juce::Component
        {
            juce::String text; bool on = false, used = false, over = false; std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintButton (g, r, on, over, false, 2.0f);
                g.setColour (on ? juce::Colour (0xff101112) : ink); g.setFont (font (9.5f, true));
                g.drawText (text.toUpperCase(), r.withTrimmedRight (12).toNearestInt(), juce::Justification::centred);
                auto d = juce::Rectangle<float> (r.getRight() - 12, r.getCentreY() - 3, 6, 6);
                g.setColour (used ? (on ? juce::Colour (0xff101112) : orange) : juce::Colour (0xff3a1e1c)); g.fillEllipse (d);
            }
            void mouseEnter (const juce::MouseEvent&) override { over = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { over = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };

        struct FxButton : public juce::Component
        {
            juce::String text; bool over = false, accent = false; std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintButton (g, r, accent, over, false, 3.0f);
                g.setColour (accent ? juce::Colours::white : ink); g.setFont (font (9.5f, true).withExtraKerningFactor (0.05f));
                g.drawText (text, r.toNearestInt(), juce::Justification::centred);
            }
            void mouseEnter (const juce::MouseEvent&) override { over = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { over = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };
    }

    struct FxPage::Impl : public Ctx::Listener
    {
        // ---- the list of the rack's effects ----
        struct ListComp : public juce::Component
        {
            explicit ListComp (Impl& i) : im (i) {}
            Impl& im; int dragIdx = -1;
            juce::Rectangle<int> itemR (int i) const { return { 0, i * kItemH, getWidth(), kItemH }; }
            void paint (juce::Graphics& g) override
            {
                auto used = im.usedSlots (im.current);
                if (used.empty())
                {
                    g.setColour (dim); g.setFont (font (9.5f));
                    g.drawFittedText ("No effects in this rack.\nUse + ADD FX.", getLocalBounds().withHeight (60).reduced (8, 0), juce::Justification::centred, 3);
                    return;
                }
                for (int i = 0; i < (int) used.size(); ++i)
                {
                    int sl = used[(size_t) i], gi = fxG (im.current, sl), ty = im.ctx.fxSlotTypes()[gi];
                    bool on = im.ctx.get (im.slotBase (gi) + 1) > 0.5f, selected = im.sel[im.current] == sl && ! im.adding;
                    auto r = itemR (i).toFloat().reduced (0, 1.5f);
                    g.setColour (dragIdx == i ? juce::Colour (0xff3a1815) : (selected ? juce::Colour (0xff2a2020) : juce::Colour (0xff121315))); g.fillRoundedRectangle (r, 3.0f);
                    if (selected) { g.setColour (red.withAlpha (0.8f)); g.drawRoundedRectangle (r.reduced (0.5f), 3.0f, 1.0f); }
                    g.setColour (fxColour (ty).withAlpha (on ? 1.0f : 0.3f)); g.fillRect (r.getX() + 1, r.getY() + 3, 3.0f, r.getHeight() - 6);
                    // on / off dot
                    auto dot = juce::Rectangle<float> (r.getX() + 12, r.getCentreY() - 4, 8, 8);
                    g.setColour (on ? fxColour (ty) : juce::Colour (0xff36383c)); g.fillEllipse (dot);
                    g.setColour (on ? ink : dim); g.setFont (font (11.0f, true));
                    g.drawText (fxTypes()[(size_t) ty].name, juce::Rectangle<int> (30, (int) r.getY(), getWidth() - 30 - 44, (int) r.getHeight()), juce::Justification::centredLeft, true);
                    // arrows
                    g.setColour (dim);
                    auto up = upR (i).toFloat(), dn = dnR (i).toFloat();
                    juce::Path p; p.addTriangle (up.getX() + 1, up.getBottom() - 1, up.getRight() - 1, up.getBottom() - 1, up.getCentreX(), up.getY() + 1); g.fillPath (p);
                    juce::Path q; q.addTriangle (dn.getX() + 1, dn.getY() + 1, dn.getRight() - 1, dn.getY() + 1, dn.getCentreX(), dn.getBottom() - 1); g.fillPath (q);
                    auto gr = gripR (i).toFloat(); g.setColour (dim.withAlpha (0.8f));
                    for (int a = 0; a < 3; ++a) for (int b = 0; b < 2; ++b) g.fillEllipse (gr.getX() + 2 + b * 5, gr.getY() + 8 + a * 4.5f, 2.0f, 2.0f);
                }
            }
            juce::Rectangle<int> upR (int i) const { auto r = itemR (i); return { r.getRight() - 40, r.getY() + 3, 11, 10 }; }
            juce::Rectangle<int> dnR (int i) const { auto r = itemR (i); return { r.getRight() - 40, r.getBottom() - 13, 11, 10 }; }
            juce::Rectangle<int> gripR (int i) const { auto r = itemR (i); return { r.getRight() - 24, r.getY(), 16, r.getHeight() }; }
            juce::Rectangle<int> dotR (int i) const { auto r = itemR (i); return { r.getX() + 6, r.getY(), 24, r.getHeight() }; }
            void mouseDown (const juce::MouseEvent& e) override
            {
                auto used = im.usedSlots (im.current);
                int i = e.y / kItemH; if (i < 0 || i >= (int) used.size()) return;
                int sl = used[(size_t) i], gi = fxG (im.current, sl);
                auto p = e.getPosition();
                if (upR (i).expanded (3).contains (p)) im.moveUsed (im.current, sl, -1);
                else if (dnR (i).expanded (3).contains (p)) im.moveUsed (im.current, sl, +1);
                else if (gripR (i).contains (p)) { dragIdx = i; im.select (im.current, sl); }
                else if (dotR (i).contains (p)) { int n = im.slotBase (gi) + 1; im.ctx.begin (n); im.ctx.set (n, im.ctx.get (n) > 0.5f ? 0.0f : 1.0f); im.ctx.end (n); }
                else im.select (im.current, sl);
                repaint();
            }
            void mouseDrag (const juce::MouseEvent& e) override
            {
                if (dragIdx < 0) return;
                auto used = im.usedSlots (im.current);
                int to = juce::jlimit (0, (int) used.size() - 1, e.y / kItemH);
                if (to != dragIdx) { int sl = used[(size_t) dragIdx]; im.moveUsed (im.current, sl, to - dragIdx); dragIdx = to; }
            }
            void mouseUp (const juce::MouseEvent&) override { dragIdx = -1; repaint(); }
        };

        // ---- grid of all effect types ("+ ADD FX"), sorted into categories; the dropdown in the header filters one category ----
        struct Chooser : public juce::Component
        {
            explicit Chooser (Impl& i) : im (i) {}
            Impl& im; int over = -1; int scroll = 0; int category = -1;   // -1 = all
            static constexpr int cols = 3, bw = 190, bh = 40, gap = 14, headH = 54;
            static const std::vector<juce::String>& categories() { return fxCategories(); }
            static int categoryOf (int type) { return fxCategoryOf (type); }
            // effect types (1..) of the shown category, in category order
            std::vector<int> vis() const
            {
                std::vector<int> v;
                for (int c = 0; c < (int) categories().size(); ++c)
                    if (category < 0 || category == c)
                        for (int t = 1; t < (int) fxTypes().size(); ++t) if (categoryOf (t) == c) v.push_back (t);
                return v;
            }
            bool available (int type) const { return im.osc < 0 || fxVoiceType (type); }   // the per voice racks of the oscillators only take the types that run per voice
            juce::Rectangle<int> dropRect() const { return { getWidth() - 214, 8, 200, 24 }; }
            int contentH() const { int n = (int) vis().size(), rows = (n + cols - 1) / cols; return rows * bh + (rows - 1) * gap + 40; }
            int maxScroll() const { return juce::jmax (0, contentH() - (getHeight() - headH)); }
            juce::Rectangle<int> cell (int i) const
            {
                int n = (int) vis().size(), rows = (n + cols - 1) / cols;
                int totalW = cols * bw + (cols - 1) * gap, totalH = rows * bh + (rows - 1) * gap;
                int x0 = (getWidth() - totalW) / 2, y0 = headH + juce::jmax (0, (getHeight() - headH - totalH) / 2 - 10) - scroll;
                return { x0 + (i % cols) * (bw + gap), y0 + (i / cols) * (bh + gap), bw, bh };
            }
            void resized() override { scroll = juce::jlimit (0, maxScroll(), scroll); }
            void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails& w) override
            {
                int ns = juce::jlimit (0, maxScroll(), scroll - juce::roundToInt (w.deltaY * (w.isReversed ? -1.0f : 1.0f) * 160.0f));
                if (ns != scroll) { scroll = ns; repaint(); }
            }
            void paint (juce::Graphics& g) override
            {
                bool full = im.freeSlot (im.current) < 0;
                g.setColour (ink); g.setFont (impact (14.0f));
                g.drawText (full ? "THIS RACK IS FULL (16 EFFECTS)" : "ADD AN EFFECT TO " + (im.osc >= 0 ? "OSC " + juce::String (im.osc + 1) : fxRacks()[(size_t) im.current].name).toUpperCase(), getLocalBounds().withHeight (28).withTrimmedTop (6), juce::Justification::centred);
                g.setColour (dim); g.setFont (font (9.5f));
                g.drawText (full ? "Remove an effect first." : "The effect is appended to the end of the chain. Drag it in the list to move it.   " + juce::String ((int) fxTypes().size() - 1) + " effects" + (im.osc >= 0 ? ", " + juce::String ([&] { int n = 0; for (int t = 1; t < (int) fxTypes().size(); ++t) n += fxVoiceType (t) ? 1 : 0; return n; }()) + " run per voice" : juce::String()), getLocalBounds().withTop (30).withHeight (18), juce::Justification::centred);
                {   // category dropdown
                    auto d = dropRect().toFloat();
                    g.setColour (dim); g.setFont (font (8.5f, true)); g.drawText ("CATEGORY", d.withHeight (10).translated (0, -9).toNearestInt(), juce::Justification::topLeft);
                    paintButton (g, d, false, dropOver, false, 3.0f);
                    g.setColour (ink); g.setFont (font (11.0f, true));
                    g.drawText (category < 0 ? juce::String ("All effects") : categories()[(size_t) category], d.reduced (8, 0).toNearestInt(), juce::Justification::centredLeft, true);
                    juce::Path t; auto a = juce::Rectangle<float> (d.getRight() - 16, d.getCentreY() - 3, 9, 6);
                    t.addTriangle (a.getX(), a.getY(), a.getRight(), a.getY(), a.getCentreX(), a.getBottom());
                    g.setColour (red); g.fillPath (t);
                }
                g.saveState();
                g.reduceClipRegion (getLocalBounds().withTrimmedTop (headH - 4));
                auto v = vis();
                for (int i = 0; i < (int) v.size(); ++i)
                {
                    auto r = cell (i).toFloat();
                    if (r.getBottom() < headH - 4 || r.getY() > getHeight()) continue;
                    const bool ok = available (v[(size_t) i]);
                    g.setColour (juce::Colour (over == i && ! full && ok ? 0xff282a2d : 0xff161719)); g.fillRoundedRectangle (r, 3.0f);
                    g.setColour (fxColour (v[(size_t) i]).withAlpha (full || ! ok ? 0.3f : 1.0f)); g.fillRect (r.getX(), r.getY(), 4.0f, r.getHeight());
                    g.setColour (full || ! ok ? dim : ink); g.setFont (font (12.0f, true));
                    g.drawText (fxTypes()[(size_t) v[(size_t) i]].name, r.withTrimmedLeft (16).toNearestInt(), juce::Justification::centredLeft);
                    if (! ok)
                    {
                        g.setColour (dim.withAlpha (0.8f)); g.setFont (font (8.0f));
                        g.drawText ("MAIN / BUS RACKS ONLY", r.withTrimmedRight (6).withTrimmedTop (r.getHeight() - 13).toNearestInt(), juce::Justification::bottomRight);
                    }
                    else if (category < 0)
                    {
                        g.setColour (dim.withAlpha (0.8f)); g.setFont (font (8.0f));
                        g.drawText (categories()[(size_t) categoryOf (v[(size_t) i])], r.withTrimmedRight (6).withTrimmedTop (r.getHeight() - 13).toNearestInt(), juce::Justification::bottomRight);
                    }
                }
                g.restoreState();
                if (maxScroll() > 0)   // scroll bar
                {
                    float trackH = (float) (getHeight() - headH - 8), th = juce::jmax (24.0f, trackH * (float) (getHeight() - headH) / (float) contentH());
                    float ty = (float) headH + 4.0f + (trackH - th) * (float) scroll / (float) maxScroll();
                    g.setColour (juce::Colours::white.withAlpha (0.18f)); g.fillRoundedRectangle ((float) getWidth() - 8.0f, ty, 4.0f, th, 2.0f);
                }
            }
            bool dropOver = false;
            void mouseMove (const juce::MouseEvent& e) override
            {
                int o = hit (e.getPosition()); bool d = dropRect().contains (e.getPosition());
                if (o != over || d != dropOver) { over = o; dropOver = d; repaint(); }
            }
            void mouseExit (const juce::MouseEvent&) override { over = -1; dropOver = false; repaint(); }
            void openMenu()
            {
                juce::PopupMenu m;
                m.addItem (1, "All effects  (" + juce::String ((int) fxTypes().size() - 1) + ")", true, category < 0);
                m.addSeparator();
                for (int c = 0; c < (int) categories().size(); ++c)
                {
                    int n = 0; for (int t = 1; t < (int) fxTypes().size(); ++t) if (categoryOf (t) == c) ++n;
                    m.addItem (c + 2, categories()[(size_t) c] + "  (" + juce::String (n) + ")", true, category == c);
                }
                auto self = juce::Component::SafePointer<Chooser> (this);
                m.showMenuAsync (juce::PopupMenu::Options().withTargetScreenArea (localAreaToGlobal (dropRect())).withMinimumWidth (dropRect().getWidth()),
                                 [self] (int r) { if (self != nullptr && r > 0) { self->category = r - 2; self->scroll = 0; self->repaint(); } });
            }
            void mouseUp (const juce::MouseEvent& e) override
            {
                if (dropRect().contains (e.getPosition())) { openMenu(); return; }
                int i = hit (e.getPosition()); if (i >= 0 && available (vis()[(size_t) i])) im.addEffect (vis()[(size_t) i]);
            }
            int hit (juce::Point<int> p) const { if (p.y < headH - 4) return -1; int n = (int) vis().size(); for (int i = 0; i < n; ++i) if (cell (i).contains (p)) return i; return -1; }
        };

        // ---- display of the selected effect (schematic: follows the knobs, not the exact DSP) ----
        struct Display : public juce::Component, private Ctx::Listener, private juce::Timer
        {
            explicit Display (Impl& i) : im (i) { im.ctx.addListener (this); setInterceptsMouseClicks (false, false); startTimerHz (30); }
            ~Display() override { stopTimer(); if (monSent > 0) im.ctx.be.setParam (9890, 0.0f); im.ctx.removeListener (this); }
            void paramChanged (int, float) override { repaint(); }
            // live data (FX-VIZ): the DSP only measures the slot the editor shows
            void timerCallback() override
            {
                int sl = im.sel[im.current], want = 0;
                if (isShowing() && sl >= 0 && im.osc < 0) { int gi = fxG (im.current, sl); if (gi < 48 && im.ctx.fxSlotTypes()[gi] != 0) want = gi + 1; }
                if (want != monSent) { monSent = want; im.ctx.be.setParam (9890, (float) want); }
                auto& v = im.ctx.be.fxViz;
                const bool live = want > 0 && v.slot == want - 1 && juce::Time::getMillisecondCounter() - v.stamp < 400;
                if (monSent != histSlot) { hist.clear(); histSlot = monSent; }
                if (live && v.stamp != lastStamp) { hist.push_back ({ juce::jmax (v.pk[0], v.pk[1]), juce::jmax (v.pk[2], v.pk[3]) }); if (hist.size() > 80) hist.erase (hist.begin()); }
                if (live || wasLive || v.stamp != lastStamp) repaint();
                wasLive = live; lastStamp = v.stamp;
            }
            int monSent = 0, histSlot = 0; bool wasLive = false; juce::uint32 lastStamp = 0;
            std::vector<std::pair<float, float>> hist;   // in / out peak of the last packets (about 4 s)
            Impl& im;
            void paint (juce::Graphics& g) override
            {
                auto box = getLocalBounds().toFloat();
                paintInset (g, box, 4.0f);
                int sl = im.sel[im.current]; if (sl < 0) return;
                int gi = fxG (im.current, sl), ty = im.ctx.fxSlotTypes()[gi], b = im.slotBase (gi);
                auto col = fxColour (ty);
                auto P = [&] (int k) { return (double) juce::jlimit (0.0f, 1.0f, im.ctx.get (b + 4 + k)); };
                const int mode = juce::roundToInt (im.ctx.get (b + 3));
                const float mix = im.ctx.get (b + 2);
                auto r = box.reduced (10, 8); const float W = r.getWidth(), H = r.getHeight();
                auto X = [&] (double t) { return r.getX() + (float) t * W; };
                auto Y = [&] (double v) { return r.getY() + (float) (1.0 - v) * H; };   // v in 0..1, 1 = top
                // grid
                g.setColour (juce::Colours::white.withAlpha (0.06f));
                for (int i = 1; i < 8; ++i) g.drawVerticalLine ((int) X (i / 8.0), r.getY(), r.getBottom());
                for (int i = 1; i < 4; ++i) g.drawHorizontalLine ((int) Y (i / 4.0), r.getX(), r.getRight());
                auto stroke = [&] (const juce::Path& p, float a = 1.0f, float w = 2.0f) { g.setColour (col.withAlpha (a)); g.strokePath (p, juce::PathStrokeType (w)); };
                auto fill = [&] (juce::Path p, double baseV) { p.lineTo (X (1), Y (baseV)); p.lineTo (X (0), Y (baseV)); p.closeSubPath(); g.setColour (col.withAlpha (0.14f)); g.fillPath (p); };
                auto label = [&] (const juce::String& t, juce::Justification j = juce::Justification::topLeft) { g.setColour (dim); g.setFont (font (9.0f, true)); g.drawText (t, r.toNearestInt().reduced (4, 2), j, false); };
                const double pi = juce::MathConstants<double>::pi;
                const int syncIdx = juce::roundToInt (im.ctx.get (fxSyncId (gi)));
                const juce::String syncName = (syncIdx > 0 && findSpec (fxSyncId (gi)) != nullptr && syncIdx < findSpec (fxSyncId (gi))->labels.size()) ? findSpec (fxSyncId (gi))->labels[syncIdx] : juce::String();

                auto freqAxis = [&]
                {
                    g.setFont (font (9.0f, true));
                    for (auto [f, t] : { std::pair<double, const char*> { 20.0, "20 Hz" }, { 100.0, "100" }, { 1000.0, "1 kHz" }, { 10000.0, "10 kHz" } })
                    {
                        float x = X (std::log (f / 20.0) / std::log (1000.0));
                        g.setColour (juce::Colours::white.withAlpha (0.08f)); g.drawVerticalLine ((int) x, r.getY(), r.getBottom());
                        g.setColour (dim); g.drawText (t, juce::Rectangle<float> (x + 3, r.getBottom() - 14, 50, 12), juce::Justification::bottomLeft, false);
                    }
                };
                auto curve = [&] (std::function<double (double)> f, int n = 240)
                {
                    juce::Path p;
                    for (int i = 0; i <= n; ++i) { double t = (double) i / n, v = f (t); if (i == 0) p.startNewSubPath (X (t), Y (v)); else p.lineTo (X (t), Y (v)); }
                    return p;
                };

                // transfer curve helper (input -1..1 -> output -1..1, normalised so that full scale stays at full scale)
                auto xfer = [&] (std::function<double (double)> f, const juce::String& txt)
                {
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight()); g.drawVerticalLine ((int) X (0.5), r.getY(), r.getBottom());
                    g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawLine (X (0), Y (0), X (1), Y (1));
                    stroke (curve ([&] (double t) { return 0.5 + 0.5 * juce::jlimit (-1.0, 1.0, f (t * 2 - 1)); }));
                    label (txt);
                };
                auto sgn = [] (double v) { return v < 0 ? -1.0 : 1.0; };
                auto dbAxis = [&]   // frequency curve with a 0 dB line, +-18 dB
                {
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight());
                    freqAxis();
                };
                auto dbCurve = [&] (std::function<double (double)> db) { auto p = curve ([&] (double t) { return (juce::jlimit (-18.0, 18.0, db (20.0 * std::pow (1000.0, t))) + 18.0) / 36.0; }); fill (p, 0.5); stroke (p); };

                if (ty == 9)   // Filter: response
                {
                    const double fc = 20.0 * std::pow (1000.0, P (0)), res = P (1);
                    auto p = curve ([&] (double t)
                    {
                        double f = 20.0 * std::pow (1000.0, t);
                        double db = 20.0 * std::log10 (juce::jmax (1e-5, std::abs (oscmodel::filterH (fxFilterShape (mode), fc, res, f))));
                        return (juce::jlimit (-48.0, 24.0, db) + 48.0) / 72.0;
                    });
                    fill (p, 0.0); stroke (p);
                    g.setColour (col.withAlpha (0.35f)); g.drawVerticalLine ((int) X (std::log (fc / 20.0) / std::log (1000.0)), r.getY(), r.getBottom());
                    g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawHorizontalLine ((int) Y ((0 + 48.0) / 72.0), r.getX(), r.getRight());
                    freqAxis();
                    if (std::abs (P (3) - 0.5) > 0.004)   // the modulation envelope that drives the cutoff
                    {
                        const int e = juce::jlimit (0, 9, juce::roundToInt (P (4) * 9.0)), eb = envParam (e);
                        label ("ENV " + juce::String (e + 1) + "   A " + juce::String (juce::roundToInt (im.ctx.get (eb))) + " ms   D " + juce::String (juce::roundToInt (im.ctx.get (eb + 1))) + " ms   S "
                               + juce::String (juce::roundToInt (im.ctx.get (eb + 2) * 100.0f)) + "%   R " + juce::String (juce::roundToInt (im.ctx.get (eb + 3))) + " ms", juce::Justification::topRight);
                    }
                }
                else if (ty == 10)   // EQ: sum of low shelf, peak, high shelf
                {
                    double gL = -12 + 24 * P (0), gM = -12 + 24 * P (1), fM = 200.0 * std::pow (25.0, P (2)), gH = -12 + 24 * P (3), q = 0.3 * std::pow (4.0 / 0.3, P (4));
                    if (mode == 1) { const double tl = -12 + 24 * P (0); gL = -tl * 0.5; gH = tl * 0.5; }                       // tilt
                    else if (mode == 2) { gL = P (0) * 14.0; gM -= gL * 0.25; gH = gL * 0.7 + (P (3) - 0.5) * 24; }              // loudness
                    else if (mode == 3) { fM = 900.0 * std::pow (7.78, P (2)); q = 0.5 * std::pow (12.0, P (4)); }              // presence
                    auto db = [&] (double f)
                    {
                        double lo = gL / (1.0 + std::pow (f / 200.0, 2.0)), hi = gH / (1.0 + std::pow (4000.0 / f, 2.0));
                        double x = std::log2 (f / fM) * q * 1.6, mid = gM / (1.0 + x * x);
                        return lo + mid + hi;
                    };
                    auto p = curve ([&] (double t) { return (juce::jlimit (-18.0, 18.0, db (20.0 * std::pow (1000.0, t))) + 18.0) / 36.0; });
                    fill (p, 0.5); stroke (p);
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight());
                    freqAxis();
                }
                else if (ty == 17)   // Console: two bells (Lo-Mid / Hi-Mid)
                {
                    static const double qs[] = { 0.45, 1.0, 2.5, 6.0 };
                    const double q = qs[mode & 3];
                    const double f1 = 45.0 * std::pow (3000.0 / 45.0, P (0)), g1 = (P (1) - 0.5) * 30.0;
                    const double f2 = 500.0 * std::pow (18000.0 / 500.0, P (2)), g2 = (P (3) - 0.5) * 30.0;
                    auto bell = [&] (double f, double fc, double gd) { const double x = std::log2 (f / fc) * q * 1.6; return gd / (1.0 + x * x); };
                    auto p = curve ([&] (double t) { const double f = 20.0 * std::pow (1000.0, t); return (juce::jlimit (-18.0, 18.0, bell (f, f1, g1) + bell (f, f2, g2)) + 18.0) / 36.0; });
                    fill (p, 0.5); stroke (p);
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight());
                    freqAxis();
                }
                else if (ty == 18)   // Filterbank: magnitude response of the two multimode filters
                {
                    using C = std::complex<double>;
                    const double fc1 = 20.0 * std::pow (1000.0, P (0)), st = std::round ((P (5) - 0.5) * 48.0), fc2 = fc1 * std::pow (2.0, st / 12.0);
                    const double k1 = 2.0 - 1.84 * P (1), k2 = 2.0 - 1.84 * juce::jmin (1.0, P (1) * 1.15), c = P (3);
                    const int rt = mode % 3; const bool mir = mode >= 3;
                    auto resp = [&] (double f, double fc, double k, double p3)
                    {
                        const C jw (0.0, f / fc), den = jw * jw + k * jw + 1.0;
                        const C lp = 1.0 / den, bp = k * jw / den, hp = (jw * jw) / den;
                        const double wl = juce::jlimit (0.0, 1.0, 1.0 - 2.0 * p3), wh = juce::jlimit (0.0, 1.0, 2.0 * p3 - 1.0), wb = 1.0 - std::abs (2.0 * p3 - 1.0);
                        const C y = wl * lp + wb * bp + wh * hp;
                        return y + c * (lp + hp - bp - y);
                    };
                    auto p = curve ([&] (double t)
                    {
                        const double f = 20.0 * std::pow (1000.0, t);
                        const C a = resp (f, fc1, k1, P (2)), b = resp (f, fc2, k2, mir ? 1.0 - P (2) : P (2));
                        const double par = 0.5 * std::abs (a + b), ser = std::abs (a * b);
                        const double m = rt == 0 ? par : rt == 1 ? ser : 0.5 * (par + ser);
                        return juce::jlimit (0.0, 1.0, 0.1 + 0.8 * (20.0 * std::log10 (juce::jmax (1e-4, m)) + 36.0) / 48.0);
                    });
                    fill (p, 0.0); stroke (p);
                    freqAxis();
                }
                else if (ty == 1)   // Distortion: transfer curve
                {
                    const double drive = 1.0 + 11.0 * P (0), outg = 2.0 * P (2);
                    auto shape = [&] (double x)
                    {
                        switch (juce::jlimit (0, 12, mode))
                        {
                            case 9: return x >= 0 ? std::tanh (x * 1.2) : std::tanh (x * 0.45) * 2.1;
                            case 10: { double xs = juce::jlimit (-1.0, 1.0, x * 0.6), x2 = xs * xs; return xs * 0.5 + (4 * x2 * xs - 3 * xs) * 0.3 + (16 * x2 * x2 * xs - 20 * x2 * xs + 5 * xs) * 0.2; }
                            case 11: { double xc = juce::jlimit (-3.0, 3.0, x); return xc * (27.0 + xc * xc) / (27.0 + 9.0 * xc * xc); }
                            case 12: { double xa = std::abs (x); return xa < 0.15 ? 0.0 : juce::jlimit (-1.0, 1.0, x * 1.5) * (xa < 0.3 ? (xa - 0.15) / 0.15 : 1.0); }
                            case 6: return x > 0 ? x / (1.0 + x) * 1.4 : 0.0;
                            case 7: { double g3 = juce::jlimit (-1.0, 1.0, x * 3.0); return g3 * (0.6 + 0.4 * std::abs (g3)); }
                            case 8: return std::tanh (x);
                            case 0: return std::tanh (x);
                            case 1: return x >= 0 ? 1.0 - std::exp (-x) : -(1.0 - std::exp (x * 0.7)) * 0.85;
                            case 2: return juce::jlimit (-1.0, 1.0, x);
                            case 3: { double y = x; while (y > 1 || y < -1) y = y > 1 ? 2 - y : -2 - y; return y; }
                            case 4: return std::sin (x * 1.5708);
                            default: return std::tanh (x * 2.0) * 0.7 + std::sin (x * 3.0) * 0.12;
                        }
                    };
                    auto p = curve ([&] (double t) { double x = (t * 2 - 1); double y = shape (x * drive + (P (3) - 0.5) * 1.2 * drive * 0.5) * outg; return 0.5 + 0.5 * juce::jlimit (-1.0, 1.0, y); });
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight()); g.drawVerticalLine ((int) X (0.5), r.getY(), r.getBottom());
                    g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawLine (X (0), Y (0), X (1), Y (1)); 
                    stroke (p); label ("INPUT -> OUTPUT");
                }
                else if (ty == 39)   // Wavefilter: gain along the frequency axis = frame of the filter table of the chosen oscillator (FX-WFILT)
                {
                    const int osc = juce::jlimit (0, 5, juce::roundToInt (P (3) * 5.0));
                    float tbl[512];
                    auto* sl = im.mem.get (SoundMemory::FilterTable, osc);
                    oscmodel::tblFrame (sl ? &sl->data : nullptr, true, (float) P (2), tbl);
                    const double lfc = std::log2 (20.0 * std::pow (1000.0, P (0))), width = 2.0 + 12.0 * P (4), cont = P (5) * 2.0 - 1.0, ex = std::pow (2.0, cont * 1.5);
                    auto p = curve ([&] (double t)
                    {
                        const double f = 20.0 * std::pow (1000.0, t), tt = juce::jlimit (-1.0, 1.0, (std::log2 (f) - lfc) * 2.0 / width), x = (0.5 + 0.5 * tt) * 511.0;
                        const int i0 = (int) x, i1 = juce::jmin (i0 + 1, 511); const double v = tbl[i0] + (tbl[i1] - tbl[i0]) * (x - i0);
                        double gain = mode == 0 ? v * 0.5 + 0.5 : mode == 2 ? std::pow (10.0, (v - 1.0) * 1.5) : v;
                        gain = std::pow (std::abs (gain), ex) * 0.64 * 24.0 * 0.28;
                        return (juce::jlimit (-48.0, 12.0, 20.0 * std::log10 (juce::jmax (1.0e-5, gain))) + 48.0) / 60.0;
                    });
                    fill (p, 0.0); stroke (p);
                    g.setColour (col.withAlpha (0.35f)); g.drawVerticalLine ((int) X (std::log (20.0 * std::pow (1000.0, P (0)) / 20.0) / std::log (1000.0)), r.getY(), r.getBottom());
                    freqAxis(); label ("TABLE OSC " + juce::String (osc + 1) + "   (approximate response)");
                }
                else if (ty == 41)   // Filter Table (FX-FTAB): the response of the frame of the chosen oscillator's filter table, as the FFT filter applies it
                {
                    const int osc = juce::jlimit (0, 5, juce::roundToInt (P (3) * 5.0));
                    float tbl[512];
                    auto* sl = im.mem.get (SoundMemory::FilterTable, osc);
                    oscmodel::tblFrame (sl ? &sl->data : nullptr, true, (float) P (2), tbl);
                    const double lfc = std::log2 (20.0 * std::pow (1000.0, P (0))), width = 2.0 + 12.0 * P (4), ex = std::pow (2.0, P (1) * 3.0), og = std::pow (10.0, (P (5) * 2.0 - 1.0) * 0.6);
                    auto p = curve ([&] (double t)
                    {
                        const double f = 20.0 * std::pow (1000.0, t), tt = juce::jlimit (0.0, 1.0, 0.5 + (std::log2 (f) - lfc) / width), x = tt * 511.0;
                        const int i0 = (int) x, i1 = juce::jmin (i0 + 1, 511); const double v = tbl[i0] + (tbl[i1] - tbl[i0]) * (x - i0);
                        double gain = mode == 0 ? v * 0.5 + 0.5 : std::pow (10.0, (v - 1.0) * 1.5);
                        gain = std::pow (juce::jmax (0.0, gain), ex > 1.001 ? ex : 1.0) * og;
                        return (juce::jlimit (-48.0, 12.0, 20.0 * std::log10 (juce::jmax (1.0e-5, gain))) + 48.0) / 60.0;
                    });
                    fill (p, 0.0); stroke (p);
                    g.setColour (col.withAlpha (0.35f)); g.drawVerticalLine ((int) X (std::log (20.0 * std::pow (1000.0, P (0)) / 20.0) / std::log (1000.0)), r.getY(), r.getBottom());
                    freqAxis (); label ("FILTER TABLE  OSC " + juce::String (osc + 1) + "   frame " + juce::String (P (2) * 100.0, 0) + " %   (FFT filter, zero phase)");
                }
                else if (ty == 40)   // Spectral (FFT effect, FX-SPEC): the frequency response of Tilt / Lo Cut / Hi Cut (bins of the 512 point FFT, 93.75 Hz each at 48 kHz), Shift as a marker, mode specific hints
                {
                    const double tilt = P (1) * 2.0 - 1.0, lo = P (3) * P (3) * 200.0, hi = 256.0 * std::pow (0.03125, P (4)), rat = std::pow (2.0, P (2) * 2.0 - 1.0);
                    auto p = curve ([&] (double t)
                    {
                        const double f = 20.0 * std::pow (1000.0, t), k = f / 93.75;
                        double gain = (k < lo || k > hi) ? 1.0e-5 : (tilt != 0.0 ? juce::jlimit (0.0, 8.0, std::pow (juce::jmax (k, 0.05) * 0.0625, tilt)) : 1.0);
                        return (juce::jlimit (-48.0, 12.0, 20.0 * std::log10 (juce::jmax (1.0e-5, gain))) + 48.0) / 60.0;
                    });
                    fill (p, 0.0); stroke (p);
                    if (mode == 0 && std::abs (rat - 1.0) > 0.01)    // Shift: arrows from the fundamental region to where it goes
                    {
                        g.setColour (col.withAlpha (0.55f));
                        for (double f0 : { 110.0, 440.0, 1760.0 })
                        {
                            const double f1 = f0 * rat, t0 = std::log (f0 / 20.0) / std::log (1000.0), t1 = std::log (juce::jlimit (20.0, 20000.0, f1) / 20.0) / std::log (1000.0);
                            g.drawArrow (juce::Line<float> (X (t0), Y (0.2), X (t1), Y (0.2)), 1.5f, 6.0f, 6.0f);
                        }
                    }
                    freqAxis();
                    static const char* nm[] = { "SHAPE   (cuts, tilt, shift; FFT 512)", "FREEZE   (Amount > 50 % holds the spectrum)", "GATE   (bins below the threshold drop to Floor)", "ROBOT   (all phases zero)", "WHISPER   (random phases)" };
                    label (nm[juce::jlimit (0, 4, mode)]);
                }
                else if (ty == 34)   // Shaper Table: transfer curve = frame of the shaper table of the chosen oscillator (FX-SHTAB)
                {
                    const int osc = juce::jlimit (0, 5, juce::roundToInt (P (2) * 5.0));
                    float tbl[512];
                    auto* sl = im.mem.get (SoundMemory::ShaperTable, osc);
                    oscmodel::tblFrame (sl ? &sl->data : nullptr, false, (float) P (1), tbl);
                    const double drive = std::pow (10.0, P (0) * 36.0 / 20.0), bias = P (3) - 0.5;
                    auto read = [&] (double u) { double x = juce::jlimit (0.0, 1.0, u) * 511.0; int i0 = (int) x, i1 = juce::jmin (i0 + 1, 511); return (double) (tbl[i0] + (tbl[i1] - tbl[i0]) * (float) (x - i0)); };
                    auto shape = [&] (double v)
                    {
                        if (mode == 0) return read (juce::jlimit (-1.0, 1.0, v) * 0.5 + 0.5);
                        if (mode == 1) { double q = v * 0.25 + 0.25; q -= std::floor (q); return read ((1.0 - 4.0 * std::abs (q - 0.5)) * 0.5 + 0.5); }
                        if (mode == 2) { double q = (v + 1.0) * 0.5; q -= std::floor (q); return read (q); }
                        const double h = read (0.5 + 0.5 * juce::jmin (std::abs (v), 1.0)); return h;
                    };
                    auto p = curve ([&] (double t) { const double x = t * 2 - 1; return 0.5 + 0.5 * juce::jlimit (-1.0, 1.0, shape (x * drive + bias)); });
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight()); g.drawVerticalLine ((int) X (0.5), r.getY(), r.getBottom());
                    g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawLine (X (0), Y (0), X (1), Y (1));
                    stroke (p); label ("TABLE OSC " + juce::String (osc + 1) + "   INPUT -> OUTPUT");
                }
                else if (ty == 14)   // Saturator: transfer curve of the model
                {
                    const double drive = std::pow (10.0, P (0) * 36.0 / 20.0), bias = (P (2) - 0.5);
                    auto shape = [&] (double u)
                    {
                        switch (juce::jlimit (0, 11, mode))
                        {
                            case 0: return u >= 0 ? std::tanh (u) : std::tanh (u * 0.75) / 0.75;
                            case 1: return 1.05 * std::tanh (0.9 * u);
                            case 2: return std::tanh (u * 1.2);
                            case 3: return std::asinh (u * 2.0) / 1.5;
                            case 4: return juce::jlimit (-0.6, 1.0, 4.0 * u);
                            case 5: { double c = juce::jlimit (-1.0, 1.0, u); return 1.5 * (c - c * c * c / 3.0); }
                            case 6: return juce::jlimit (-1.0, 1.0, u);
                            case 7: return std::abs (u);
                            case 8: return std::sin (2.0 * u);
                            case 9: return u / (1.0 + std::abs (u));
                            case 10: return u + 0.5 * std::tanh (3.0 * u);
                            default: return std::atan (u * 1.5708) / 1.5708 * 1.3;
                        }
                    };
                    const double ref = std::max (0.05, std::abs (shape (0.5 * drive)));
                    auto p = curve ([&] (double t) { double x = t * 2 - 1; double y = (shape (x * drive + bias * drive) - shape (bias * drive)) * (0.5 / ref); return 0.5 + 0.5 * juce::jlimit (-1.0, 1.0, y); });
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight()); g.drawVerticalLine ((int) X (0.5), r.getY(), r.getBottom());
                    g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawLine (X (0), Y (0), X (1), Y (1));
                    stroke (p); label ("INPUT -> OUTPUT   " + juce::String (36.0 * P (0), 1) + " dB DRIVE");
                }
                else if (ty == 2)   // Bit crusher: staircase of a sine
                {
                    const double bits = 16.0 - 12.0 * P (0); const int hold = 1 + juce::roundToInt (P (1) * 31);
                    const double levels = std::pow (2.0, juce::jmax (1.5, bits)) / 2.0;
                    auto sine = [&] (double t) { return std::sin (t * 2 * pi * 2.0); };
                    g.setColour (juce::Colours::white.withAlpha (0.18f)); g.strokePath (curve ([&] (double t) { return 0.5 + 0.45 * sine (t); }), juce::PathStrokeType (1.0f));
                    auto p = curve ([&] (double t) { double tt = std::floor (t * 240.0 / hold) * hold / 240.0; double v = std::round (sine (tt) * levels) / levels; return 0.5 + 0.45 * v; }, 480);
                    stroke (p); label (juce::String (bits, 1) + " BIT   1/" + juce::String (hold));
                }
                else if (ty == 3)   // Delay: taps
                {
                    const double ms = 10.0 * std::pow (100.0, P (0)), fb = 0.95 * P (1); const bool pp = P (3) > 0.5;
                    int taps = 1; while (taps < 14 && std::pow (fb, taps) > 0.03) ++taps;
                    const double span = ms * (taps + 0.5);
                    g.setColour (col); 
                    auto bar = [&] (double t, double a, bool top) { float x = X (t / span); g.setColour (col.withAlpha (0.35f + 0.65f * (float) a)); g.fillRect (x - 2, top ? Y (0.5 + 0.45 * a) : Y (0.5), 4.0f, (float) (0.45 * a * H)); };
                    g.setColour (ink.withAlpha (0.8f)); g.fillRect (X (0) - 2, Y (0.95), 4.0f, (float) (0.45 * H));
                    for (int k = 1; k <= taps; ++k) bar (ms * k, std::pow (fb, k - 1) * (0.2 + 0.8 * (mix)), ! pp || (k % 2 == 1));
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight());
                    label ((syncName.isNotEmpty() ? syncName + "  (tempo sync)" : juce::String (juce::roundToInt (ms)) + " ms") + (pp ? "   PING-PONG" : ""));
                }
                else if (ty == 4 || ty == 5 || ty == 6)   // Chorus / Flanger / Phaser: modulation
                {
                    const double rate = (ty == 6 ? 0.05 * std::pow (160.0, P (0)) : 0.05 * std::pow (100.0, P (0))), depth = P (1);
                    auto lfo = [&] (double t) { return std::sin (t * 2.5 * 2 * pi * std::sqrt (rate)); };
                    auto p = curve ([&] (double t) { return 0.5 + 0.42 * depth * lfo (t); });
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (0.5), r.getX(), r.getRight());
                    if (ty == 6)
                    {
                        // notch comb: stages = mode + 1 pairs
                        const int notches = juce::jlimit (1, 4, mode + 1);
                        g.setColour (col.withAlpha (0.45f));
                        for (int n = 0; n < notches; ++n) { double c = (n + 0.5) / notches * (0.6 + 0.3 * lfo (0.25)); g.fillRect (X (c) - 1.0f, r.getY() + 6, 2.0f, H - 12); }
                    }
                    stroke (p); label ((syncName.isNotEmpty() ? syncName + "  (tempo sync)" : juce::String (rate, 2) + " Hz") + "  (shape only)");
                }
                else if (ty == 7)   // Tremolo
                {
                    const double rate = 0.1 * std::pow (200.0, P (0)), depth = P (1);
                    if (mode == 5)
                    {
                        // trance gate: the 16 steps of the pattern (left channel solid, the shifted right channel as an outline)
                        auto& pt = fxGatePatterns(); const int pi2 = juce::jlimit (0, (int) pt.size() - 1, (int) (P (3) * (double) pt.size()));
                        const double sw = P (5) * 0.5, sm = P (4);
                        const float sw16 = W / 16.0f;
                        auto step = [&] (int k) { auto c = pt[(size_t) pi2].second[k]; return c == '#' ? 1.0 : (c == '+' ? 0.45 : 0.0); };
                        for (int k = 0; k < 16; ++k)
                        {
                            const double lvl = 1.0 - depth * (1.0 - step (k));
                            const float x0 = r.getX() + sw16 * (float) k + ((k & 1) ? (float) sw * sw16 : 0.0f), wd = sw16 - ((k & 1) ? (float) sw * sw16 : 0.0f) + ((k & 1) == 0 ? (float) sw * sw16 : 0.0f);
                            g.setColour (col.withAlpha (0.18f + 0.6f * (float) step (k)));
                            g.fillRect (x0 + 1.5f, Y (0.08 + 0.84 * lvl), juce::jmax (2.0f, wd - 3.0f), (float) (0.84 * lvl * H));
                            if (P (2) > 0.01) { const int ks = (k + (int) std::lround (8.0 * P (2))) % 16; const double lr = 1.0 - depth * (1.0 - step (ks)); g.setColour (ink.withAlpha (0.55f)); g.drawRect (x0 + 1.5f, Y (0.08 + 0.84 * lr), juce::jmax (2.0f, wd - 3.0f), (float) (0.84 * lr * H), 1.0f); }
                        }
                        g.setColour (juce::Colours::white.withAlpha (0.12f));
                        for (int k = 0; k < 16; k += 4) g.drawVerticalLine ((int) (r.getX() + sw16 * (float) k), r.getY(), r.getBottom());
                        label (pt[(size_t) pi2].first + "   " + (syncName.isNotEmpty() ? syncName + " per pattern (tempo sync)" : juce::String (rate, 1) + " Hz per pattern") + (sm > 0.7 ? "   soft edges" : ""));
                    }
                    else if (mode == 6)
                    {
                        const double cycles = juce::jlimit (1.0, 4.0, rate * 0.6);
                        auto pl = curve ([&] (double t) { double pp = 0.5 + 0.5 * depth * std::sin (2 * pi * t * cycles); return 0.08 + 0.84 * std::cos (pp * pi * 0.5) * 1.4142 * 0.7071; }, 480);
                        auto pr = curve ([&] (double t) { double pp = 0.5 + 0.5 * depth * std::sin (2 * pi * t * cycles); return 0.08 + 0.84 * std::sin (pp * pi * 0.5) * 1.4142 * 0.7071; }, 480);
                        stroke (pl); stroke (pr, 0.5f); label ((syncName.isNotEmpty() ? syncName + "  (tempo sync)" : juce::String (rate, 1) + " Hz") + "   L / R");
                    }
                    else if (mode == 7 || mode == 8)
                    {
                        const int n = 8; juce::Random rng (3); double v[n + 1]; for (double& x : v) x = rng.nextDouble();
                        auto p = curve ([&] (double t)
                        {
                            const int i = juce::jmin (n - 1, (int) (t * n)); const double f = t * n - i;
                            const double lv = mode == 7 ? v[i] : v[i] + (v[i + 1] - v[i]) * f * f * (3 - 2 * f);
                            return 0.08 + 0.84 * (1.0 - depth * lv);
                        }, 480);
                        fill (p, 0.0); stroke (p); label ((syncName.isNotEmpty() ? syncName + "  (tempo sync)" : juce::String (rate, 1) + " Hz") + (mode == 7 ? "   SAMPLE & HOLD" : "   SMOOTH RANDOM"));
                    }
                    else
                    {
                    auto wav = [&] (double ph)
                    {
                        ph -= std::floor (ph);
                        switch (juce::jlimit (0, 4, mode))
                        {
                            case 0: return 0.5 - 0.5 * std::cos (2 * pi * ph);
                            case 1: return ph < 0.5 ? ph * 2 : 2 - ph * 2;
                            case 2: return ph < 0.5 ? 1.0 : 0.0;
                            case 3: return 1.0 - ph;
                            default: return ph;
                        }
                    };
                    const double cycles = juce::jlimit (1.0, 8.0, rate * 0.6);
                    auto p = curve ([&] (double t) { return 0.08 + 0.84 * (1.0 - depth * (1.0 - wav (t * cycles))); }, 480);
                    fill (p, 0.0); stroke (p); label (syncName.isNotEmpty() ? syncName + "  (tempo sync)" : juce::String (rate, 1) + " Hz");
                    }
                }
                else if (ty == 16)   // Unison: the detune of every voice (x, in cents) and its stereo position (height)
                {
                    const int nv = 2 + juce::roundToInt (P (0) * 6.0), um = mode;
                    const double det = P (1) * 100.0;
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawVerticalLine ((int) X (0.5), r.getY(), r.getBottom());
                    for (int v = 0; v < nv; ++v)
                    {
                        const double lin = nv > 1 ? 2.0 * v / (nv - 1) - 1.0 : 0.0, sg = lin < 0 ? -1.0 : 1.0;
                        double xx = lin, oct = 0.0;
                        if (um == 1) xx = sg * std::pow (std::abs (lin), 1.5);
                        if (um == 2) xx = sg * std::pow (std::abs (lin), 0.7);
                        if (um == 3) { xx = lin * 0.3; oct = v % 3 == 1 ? 1200.0 : (v % 3 == 2 ? -1200.0 : 0.0); }
                        const double cents = xx * det + oct, span = um == 3 ? 1300.0 : juce::jmax (30.0, det * 1.2);
                        const double t = juce::jlimit (0.03, 0.97, 0.5 + 0.5 * cents / span), yl = 0.5 - 0.35 * P (2) * lin;
                        g.setColour (col.withAlpha (0.8f)); g.fillRect (X (t) - 1.5f, Y (yl) - 14.0f, 3.0f, 28.0f);
                    }
                    label (juce::String (nv) + " VOICES   +-" + juce::String (juce::roundToInt (det)) + " ct" + (um == 3 ? "   OCTAVES" : juce::String()));
                }
                else if (ty == 8)   // Reverb: decay
                {
                    const double size = P (0), damp = P (1), pre = P (2) * 0.12, tail = 0.3 + 0.7 * size;
                    juce::Path p; p.startNewSubPath (X (0), Y (0.04));
                    juce::Random rng (7);
                    for (int i = 0; i < 200; ++i)
                    {
                        double t = (double) i / 200; if (t < pre) continue;
                        double e = std::exp (-(t - pre) * (3.0 + 6.0 * damp) / tail) * (0.6 + 0.4 * rng.nextDouble());
                        g.setColour (col.withAlpha (0.25f + 0.5f * (float) e)); g.fillRect (X (t), Y (0.04 + 0.9 * e), 2.0f, (float) (0.9 * e * H));
                    }
                    g.setColour (ink.withAlpha (0.8f)); g.fillRect (X (0), Y (0.95), 2.0f, (float) (0.9 * H));
                    label (juce::String (juce::roundToInt (P (2) * 100)) + " ms pre-delay");
                }
                else if (ty == 12)   // Convolution reverb: the impulse response envelope of the selected mode
                {
                    static const double t60Base[] = { 0.15, 0.5, 0.4, 1.2, 0.3, 0.4, 0.2, 0.08, 0.5 }, t60Size[] = { 0.85, 1.3, 1.3, 1.5, 0.9, 1.1, 0.5, 0.25, 1.0 };
                    const int m = juce::jlimit (0, 8, mode);
                    const double t60 = (t60Base[m] + t60Size[m] * P (0)) * (0.35 + 1.3 * P (1)), len = juce::jlimit (0.05, 1.5, t60 * 1.15), pre = P (3) * 0.2;
                    const double span = 1.6, dmp = P (2);
                    juce::Random rng (11);
                    for (int i = 0; i < 240; ++i)
                    {
                        double t = (double) i / 240 * span - pre * 0.0, tt = t - pre; if (tt < 0 || tt > len) continue;
                        double e = std::exp (-6.9 * tt / t60);
                        if (m == 5) e = std::exp (-6.9 * (len - tt) / t60);
                        else if (m == 6) e = tt < len - 0.02 ? 1.0 : 0.0;
                        e *= (0.65 + 0.35 * rng.nextDouble()) * (1.0 - 0.3 * dmp * tt / len);
                        g.setColour (col.withAlpha (0.25f + 0.6f * (float) e)); g.fillRect (X (t / span), Y (0.04 + 0.88 * e), 2.0f, (float) (0.88 * e * H));
                    }
                    if (m != 5) { g.setColour (ink.withAlpha (0.8f)); g.fillRect (X (pre / span), Y (0.95), 2.0f, (float) (0.9 * H)); }
                    label (juce::String (t60, 2) + " s decay   " + juce::String (juce::roundToInt (len * 1000)) + " ms IR");
                }
                else if (ty == 11)   // Compressor: transfer curve (input dB -> output dB, -60..0)
                {
                    const double th = -60.0 + 60.0 * P (0), ratio = 1.0 + 19.0 * P (1) * P (1), mk = 24.0 * P (4);
                    auto p = curve ([&] (double t) { double in = -60.0 + 60.0 * t, kw = 12.0 * P (5), d = in - th, out = d * 2.0 < -kw ? in : (d * 2.0 > kw ? th + d / ratio : in + (1.0 / ratio - 1.0) * (d + kw * 0.5) * (d + kw * 0.5) / (2.0 * juce::jmax (kw, 0.001))); return juce::jlimit (0.0, 1.0, (out + mk + 60.0) / 60.0); });
                    g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawLine (X (0), Y (0), X (1), Y (1));
                    g.setColour (col.withAlpha (0.35f)); g.drawVerticalLine ((int) X ((th + 60.0) / 60.0), r.getY(), r.getBottom());
                    stroke (p); label ("THRESH " + juce::String (th, 1) + " dB   " + juce::String (ratio, 1) + ":1");
                }
                else if (ty == 19)   // AW PurestDrive
                {
                    const double gn = 0.5 + 2.5 * P (0);
                    xfer ([&] (double x) { return std::sin (juce::jlimit (-1.5708, 1.5708, x * gn)) / std::sin (juce::jlimit (-1.5708, 1.5708, gn)); }, "INPUT -> OUTPUT   DRIVE " + juce::String (juce::roundToInt (P (0) * 100)) + "%");
                }
                else if (ty == 20)   // AW Spiral
                {
                    const double gn = 0.2 + 3.0 * P (0), og = P (3);
                    xfer ([&] (double x) { return og * std::sin (juce::jlimit (-1.5708, 1.5708, x * gn)) / std::sin (juce::jlimit (-1.5708, 1.5708, gn)); },
                          "INPUT -> OUTPUT   IN " + juce::String (juce::roundToInt (P (0) * 100)) + "%   HP " + juce::String (juce::roundToInt (P (1) * 100)) + "%   PRESENCE " + juce::String (juce::roundToInt (P (2) * 100)) + "%");
                }
                else if (ty == 21)   // AW Drive
                {
                    const double gn = 1.0 + 11.0 * P (0), og = P (2);
                    xfer ([&] (double x) { return og * std::tanh (x * gn) / std::tanh (gn); }, "INPUT -> OUTPUT   DRIVE " + juce::String (juce::roundToInt (P (0) * 100)) + "%   HP " + juce::String (juce::roundToInt (P (1) * 100)) + "%");
                }
                else if (ty == 22)   // AW Tube: asymmetric, even harmonics
                {
                    const double gn = 0.5 + 3.0 * P (0), tb = P (1);
                    auto sh = [&] (double u) { return u >= 0 ? std::tanh (u * (1.0 + 1.5 * tb)) : std::tanh (u * (1.0 - 0.5 * tb)) * (1.0 - 0.25 * tb); };
                    xfer ([&] (double x) { return sh (x * gn) / sh (gn); }, "INPUT -> OUTPUT   TUBE " + juce::String (juce::roundToInt (P (1) * 100)) + "%");
                }
                else if (ty == 23)   // AW Density: low levels are raised
                {
                    const double dn = 1.0 + 3.0 * P (0), og = P (2);
                    xfer ([&] (double x) { return og * sgn (x) * (1.0 - std::pow (1.0 - std::abs (x), dn)); }, "INPUT -> OUTPUT   DENSITY " + juce::String (juce::roundToInt (P (0) * 100)) + "%");
                }
                else if (ty == 24)   // AW Console 7: fader law
                {
                    const double fd = P (0);
                    auto gdb = [&] (double f) { return 20.0 * std::log10 (juce::jmax (1e-4, std::pow (f / 0.772, 2.2))); };
                    auto p = curve ([&] (double t) { return juce::jlimit (0.0, 1.0, (gdb (t) + 60.0) / 72.0); });
                    fill (p, 0.0); stroke (p);
                    g.setColour (juce::Colours::white.withAlpha (0.15f)); g.drawHorizontalLine ((int) Y (60.0 / 72.0), r.getX(), r.getRight());
                    const float px = X (fd), py = Y (juce::jlimit (0.0, 1.0, (gdb (fd) + 60.0) / 72.0));
                    g.setColour (ink); g.fillEllipse (px - 4, py - 4, 8, 8);
                    label ("FADER " + juce::String (juce::jmax (-60.0, gdb (fd)), 1) + " dB");
                }
                else if (ty == 25)   // AW Channel: console flavour
                {
                    const double gn = 1.0 + 7.0 * P (0), og = P (1);
                    auto sh = [&] (double u)
                    {
                        switch (juce::jlimit (0, 4, mode))
                        {
                            case 0: return std::tanh (u);                                              // Neve: round
                            case 1: return u / std::pow (1.0 + std::pow (std::abs (u), 3.0), 1.0 / 3.0);   // API: harder knee
                            case 2: return std::tanh (u * 1.4) * 0.96 + 0.04 * u / (1.0 + std::abs (u));  // SSL: tight
                            case 3: return u >= 0 ? std::tanh (u * 0.8) : std::tanh (u * 1.1);             // Teac: tape-like asymmetry
                            default: return std::atan (u * 1.2) / 1.2 * 0.9;                                 // Mackie: soft
                        }
                    };
                    xfer ([&] (double x) { return og * sh (x * gn) / sh (gn); }, juce::String ("CHANNEL ") + (mode == 0 ? "NEVE" : mode == 1 ? "API" : mode == 2 ? "SSL" : mode == 3 ? "TEAC" : "MACKIE") + "   DRIVE " + juce::String (juce::roundToInt (P (0) * 100)) + "%");
                }
                else if (ty == 26)   // AW ToTape: head bump and soft high end
                {
                    const double bump = 8.0 * P (2), soft = P (1);
                    dbAxis();
                    dbCurve ([&] (double f)
                    {
                        double x = std::log2 (f / 70.0), b = bump * std::exp (-x * x * 0.9);
                        double hi = -10.0 * soft * (1.0 - 1.0 / (1.0 + std::pow (f / (14000.0 - 9000.0 * soft), 2.0)));
                        return b + hi - 0.5 * (0.5 - P (3)) * 0;   // flutter does not change the response
                    });
                    label ("BUMP " + juce::String (bump, 1) + " dB   SOFT " + juce::String (juce::roundToInt (soft * 100)) + "%   FLUTTER " + juce::String (juce::roundToInt (P (3) * 100)) + "%");
                }
                else if (ty == 27)   // AW MackEQ: low and high shelf
                {
                    const double gL = (P (2) - 0.5) * 24.0, gH = (P (1) - 0.5) * 24.0;
                    dbAxis();
                    dbCurve ([&] (double f) { return gL / (1.0 + std::pow (f / 100.0, 2.0)) + gH / (1.0 + std::pow (8000.0 / f, 2.0)); });
                    label ("LO " + juce::String (gL, 1) + " dB   HI " + juce::String (gH, 1) + " dB   TRIM " + juce::String (juce::roundToInt (P (0) * 100)) + "%");
                }
                else if (ty == 28)   // Plasma: transfer curve of the style, with drive and asymmetry
                {
                    const double gn = std::pow (10.0, 40.0 * P (0) / 20.0), bias = (P (1) - 0.5) * 2.0 * 0.6;
                    auto sh = [&] (double u)
                    {
                        switch (juce::jlimit (0, 11, mode))
                        {
                            case 0: return std::tanh (u);
                            case 1: return juce::jlimit (-1.0, 1.0, u);
                            case 2: { double y = u; while (y > 1 || y < -1) y = y > 1 ? 2 - y : -2 - y; return y; }
                            case 3: return u > 0 ? std::tanh (u) : 0.0;
                            case 4: return u >= 0 ? std::tanh (u * 2.0) : juce::jlimit (-0.6, 0.0, u * 3.0);
                            case 5: return u >= 0 ? 1.0 - std::exp (-u) : -(1.0 - std::exp (u * 0.7)) * 0.85;
                            case 6: return std::atan (u * 1.5708) / 1.5708;
                            case 7: return u / (1.0 + std::abs (u));
                            case 8: return u >= 0 ? 1.0 - std::exp (-u * 1.2) : std::exp (u * 1.2) - 1.0;
                            case 9: return std::tanh (u) * 0.85 + 0.15 * std::sin (u * 6.0);
                            case 10: { double y = std::asin (std::sin (u * 1.5708)) / 1.5708; return y; }
                            default: { double c = juce::jlimit (-1.0, 1.0, u); return 1.5 * (c - c * c * c / 3.0) / 1.0; }
                        }
                    };
                    const double ref = std::max (0.05, std::abs (sh (gn)));
                    xfer ([&] (double x) { return (sh (x * gn + bias * gn) - sh (bias * gn)) / ref; },
                          "INPUT -> OUTPUT   " + juce::String (40.0 * P (0), 1) + " dB   ASYM " + juce::String (juce::roundToInt ((P (1) - 0.5) * 200)) + "%   " + juce::String (std::initializer_list<const char*> { "HP", "LP", "DUAL", "PEAK" }.begin()[juce::jmin (3, (int) (P (3) * 4))]));
                }
                else if (ty == 29)   // Granular: grains in the buffer
                {
                    const double pos = P (0), sizeMs = 20.0 * std::pow (30.0, P (1)), semis = (P (2) - 0.5) * 48.0, dens = P (3), tex = P (4), fb = P (5);
                    const double span = 1.2;   // seconds shown
                    g.setColour (col.withAlpha (0.18f)); g.strokePath (curve ([&] (double t) { return 0.5 + 0.28 * std::sin (t * 2 * pi * 9.0) * (0.55 + 0.45 * std::sin (t * 2 * pi * 2.3)); }, 480), juce::PathStrokeType (1.0f));
                    juce::Random rng (5);
                    const int n = mode == 1 ? 6 : 3 + juce::roundToInt (dens * 18.0);
                    const double cx = mode == 3 ? 0.5 : pos;
                    for (int k = 0; k < n; ++k)
                    {
                        double t0 = juce::jlimit (0.0, 0.95, cx + (rng.nextDouble() - 0.5) * (0.04 + 0.6 * tex));
                        double wd = juce::jlimit (0.015, 0.6, sizeMs / 1000.0 / span);
                        double fr = 5.0 * std::pow (2.0, semis / 12.0) * (mode == 2 ? 1.0 : 0.85 + 0.3 * rng.nextDouble());
                        double yc = 0.5 + (rng.nextDouble() - 0.5) * 0.5;
                        juce::Path gp;
                        for (int i = 0; i <= 40; ++i)
                        {
                            double u = (double) i / 40, win = 0.5 - 0.5 * std::cos (2 * pi * u);
                            double xx = t0 + u * wd; if (xx > 1.0) break;
                            double yy = yc + 0.22 * win * std::sin (u * 2 * pi * fr);
                            if (i == 0) gp.startNewSubPath (X (xx), Y (yy)); else gp.lineTo (X (xx), Y (yy));
                        }
                        stroke (gp, 0.35f + 0.5f * (float) (1.0 - (double) k / n), 1.4f);
                    }
                    if (fb > 0.02 && mode != 2)   // feedback: faint repeats of the grain cloud
                    {
                        g.setColour (col.withAlpha (0.25f)); for (int k = 1; k < 4; ++k) g.fillRect (X (juce::jmin (1.0, cx + 0.12 * k)), Y (0.5 + 0.35 * std::pow (fb, k)), 2.0f, (float) (0.7 * std::pow (fb, k) * H));
                    }
                    g.setColour (ink.withAlpha (0.8f)); g.fillRect (X (cx), r.getY(), 2.0f, H);
                    label (juce::String (std::initializer_list<const char*> { "GRANULAR", "FREEZE", "PITCH SHIFT", "LOOPING DELAY" }.begin()[juce::jlimit (0, 3, mode)]) + "   " + juce::String (juce::roundToInt (sizeMs)) + " ms grains   " + juce::String (semis, 1) + " st");
                }
                else if (ty == 30)   // Warp: the four modes
                {
                    const double amt = P (0), ratio = 0.5 + 6.0 * P (2), shape = P (3);
                    if (mode <= 1)
                    {
                        auto in = [&] (double t) { return std::sin (t * 2 * pi * 3.0); };
                        auto md = [&] (double t) { return std::sin (t * 2 * pi * 3.0 * ratio); };
                        g.setColour (juce::Colours::white.withAlpha (0.18f)); g.strokePath (curve ([&] (double t) { return 0.5 + 0.4 * in (t); }, 480), juce::PathStrokeType (1.0f));
                        auto p = curve ([&] (double t)
                        {
                            double m = md (t); if (mode == 1) m = juce::jlimit (-1.0, 1.0, m * (1.0 + 4.0 * shape));
                            return 0.5 + 0.4 * ((1.0 - amt) * in (t) + amt * in (t) * m);
                        }, 480);
                        stroke (p); label (juce::String (mode == 0 ? "ANALOG RING MOD" : "DIGITAL RING MOD") + "   x" + juce::String (ratio, 2) + " pitch ratio   " + juce::String (juce::roundToInt (amt * 100)) + "% amount");
                    }
                    else if (mode == 2)
                    {
                        juce::Random rng (11);
                        for (int k = 0; k < 20; ++k)
                        {
                            double e = (0.25 + 0.75 * rng.nextDouble()) * (0.35 + 0.65 * amt) * (1.0 - 0.5 * std::abs (k / 19.0 - 0.35));
                            g.setColour (col.withAlpha (0.3f + 0.6f * (float) e)); g.fillRect (X ((k + 0.15) / 20.0), Y (0.04 + 0.9 * e), W / 20.0f * 0.7f, (float) (0.9 * e * H));
                        }
                        label ("VOCODER   20 bands   " + juce::String (juce::roundToInt (amt * 100)) + "% amount");
                    }
                    else
                    {
                        const double sh2 = (P (2) - 0.5) * 0.5;
                        for (int k = 1; k <= 8; ++k)
                        {
                            double a = 1.0 / k, x0 = 0.08 + 0.1 * k;
                            g.setColour (juce::Colours::white.withAlpha (0.25f)); g.fillRect (X (x0), Y (0.04 + 0.8 * a), 2.0f, (float) (0.8 * a * H));
                            double x1 = x0 + sh2; if (x1 > 0 && x1 < 1) { g.setColour (col.withAlpha (0.85f)); g.fillRect (X (x1), Y (0.04 + 0.8 * a), 2.5f, (float) (0.8 * a * H)); }
                        }
                        label ("FREQUENCY SHIFT   " + juce::String (juce::roundToInt ((P (2) - 0.5) * 2.0 * 2000.0)) + " Hz (shape only)");
                    }
                }
                else if (ty == 31)   // CloudSeed: impulse response
                {
                    const double dec = 0.2 * std::pow (150.0, P (0)), size = P (1), damp = P (2), pre = P (3) * 0.08, mod = P (4), early = P (5);
                    const double span = juce::jmin (dec * 1.15, 12.0) + pre;
                    juce::Random rng (9);
                    const int n = 160;
                    for (int i = 0; i < n; ++i)
                    {
                        double t = (double) i / n * span; if (t < pre) continue;
                        double tt = t - pre, e = std::pow (10.0, -3.0 * tt / dec);
                        double dens = juce::jlimit (0.15, 1.0, tt / (0.25 + 0.5 * size));   // the echo density grows
                        if (rng.nextDouble() > 0.35 + 0.65 * dens) continue;
                        e *= (0.5 + 0.5 * rng.nextDouble()) * (1.0 - 0.35 * damp * (tt / dec)) * (1.0 + 0.2 * mod * std::sin (tt * 25.0));
                        g.setColour (col.withAlpha (0.25f + 0.6f * (float) e)); g.fillRect (X (t / span), Y (0.04 + 0.9 * e), 2.0f, (float) (0.9 * juce::jlimit (0.0, 1.0, e) * H));
                    }
                    const int ne = 4 + juce::roundToInt (early * 9.0);   // early reflections
                    for (int k = 0; k < ne; ++k)
                    {
                        double t = pre + (0.004 + 0.07 * size) * (k + 1) / ne * (0.8 + 0.4 * rng.nextDouble());
                        g.setColour (ink.withAlpha (0.8f)); g.fillRect (X (t / span), Y (0.04 + 0.9 * (0.4 + 0.5 * early) * std::pow (0.8, k)), 2.0f, (float) (0.9 * (0.4 + 0.5 * early) * std::pow (0.8, k) * H));
                    }
                    g.setColour (ink.withAlpha (0.8f)); g.fillRect (X (pre / span), Y (0.95), 2.0f, (float) (0.9 * H));
                    label (juce::String (dec, 2) + " s decay   " + juce::String (juce::roundToInt (P (3) * 80)) + " ms pre-delay");
                }
                else if (ty == 32)   // Waveguide: the resonances of the loop
                {
                    const int mm = mode >= 5 ? mode - 5 : mode;
                    const bool key = mode >= 5;
                    const double f0 = 30.0 * std::pow (2000.0 / 30.0, P (0)), t60 = 0.05 * std::pow (160.0, P (1)), fc = 500.0 * std::pow (32.0, P (2)), cent = 50.0 * P (3);
                    auto x = [&] (double f) { return std::log (f / 20.0) / std::log (1000.0); };
                    auto bars = [&] (double base, double w, float al)
                    {
                        for (int n = 1; n < 80; ++n)
                        {
                            if (mm == 1 && (n % 2) == 0) continue;
                            double f = base * n; if (f > 20000.0) break;
                            double a = juce::jlimit (0.0, 1.0, w / (n * std::sqrt (1.0 + (f / fc) * (f / fc))) * (0.5 + 0.5 * std::min (1.0, t60 / 2.0)));
                            g.setColour (col.withAlpha (al)); g.fillRect (X (x (f)) - 1.0f, Y (0.04 + 0.92 * std::sqrt (a)), 2.0f, (float) (0.92 * std::sqrt (a) * H));
                        }
                    };
                    freqAxis();
                    bars (f0, 1.0, 0.9f);
                    if (mm == 2) bars (f0 * std::pow (2.0, (3.0 + cent) / 1200.0), 0.9, 0.5f);
                    else if (mm == 3) bars (f0 * 1.5, 0.8, 0.5f);
                    else if (mm == 4) bars (f0 * 0.5, 0.8, 0.5f);
                    label ((key ? juce::String ("KEY TRACK  ") : juce::String()) + juce::String (f0, 1) + " Hz   T60 " + juce::String (t60, 2) + " s");
                }
                else if (ty == 33)   // Yaybahar: string -> springs -> drums
                {
                    const bool key = mode >= 3; const int mm = key ? mode - 3 : mode;
                    const double f0 = 40.0 * std::pow (20.0, P (0)), sprMs = 20.0 * std::pow (12.5, P (1)), dec = P (2), disp = P (3), fm = 40.0 * std::pow (6.25, P (4)), damp = P (5);
                    // string
                    const float sx0 = X (0.02), sx1 = X (0.2), cy = Y (0.5);
                    g.setColour (ink.withAlpha (0.6f)); g.drawLine (sx0, cy, sx1, cy, 1.5f);
                    juce::Path sp; for (int i = 0; i <= 60; ++i) { float u = (float) i / 60.0f, yy = cy + (float) (0.18 * H * std::sin (u * pi) * std::sin (u * 2 * pi * 2.0 + 0.0)); if (i == 0) sp.startNewSubPath (sx0 + u * (sx1 - sx0), yy); else sp.lineTo (sx0 + u * (sx1 - sx0), yy); }
                    stroke (sp, 0.9f, 1.8f);
                    // two springs: the turns get longer with the spring time, the dispersion spreads them
                    auto spring = [&] (float y0, float y1, float len, int v)
                    {
                        const int turns = 6 + juce::roundToInt ((v == 1 && mm != 1 ? 1.37 : 1.0) * 14.0 * P (1));
                        juce::Path p; const float x0 = X (0.24), x1 = x0 + (X (0.62) - x0) * len;
                        for (int i = 0; i <= turns * 12; ++i)
                        {
                            float u = (float) i / (float) (turns * 12), uu = (float) std::pow ((double) u, 1.0 + 0.8 * disp);
                            float xx = x0 + uu * (x1 - x0), yb = y0 + (y1 - y0) * u, yy = yb + 0.07f * H * (float) std::sin (u * turns * 2 * pi);
                            if (i == 0) p.startNewSubPath (xx, yy); else p.lineTo (xx, yy);
                        }
                        stroke (p, 0.9f, 1.6f); return x1;
                    };
                    const float ya = Y (0.5) - 0.0f;
                    const float xa = spring (cy, Y (0.74), 0.72f + 0.28f * (float) dec, 0);
                    const float xb = spring (cy, Y (0.26), 0.72f + 0.28f * (float) dec, 1);
                    g.setColour (ink.withAlpha (0.35f)); g.drawLine (sx1, cy, X (0.24), cy, 1.2f); juce::ignoreUnused (ya);
                    // drums: the lower the tuning, the bigger the drum
                    auto drum = [&] (float cx, float cyy, double hz)
                    {
                        float rr = (float) juce::jlimit (0.06, 0.22, 0.30 - 0.16 * std::log (hz / 20.0) / std::log (20.0)) * H;
                        juce::Rectangle<float> e (cx - rr * 1.2f, cyy - rr, rr * 2.4f, rr * 2.0f);
                        g.setColour (col.withAlpha (0.08f + 0.18f * (float) dec)); g.fillEllipse (e);
                        g.setColour (col.withAlpha (0.9f)); g.drawEllipse (e, 2.0f);
                        g.setColour (col.withAlpha (0.45f)); g.drawEllipse (e.reduced (rr * 0.55f), 1.0f); g.drawLine (e.getX(), cyy, e.getRight(), cyy, 0.8f);
                    };
                    drum (X (0.77), Y (0.74), fm * (mm == 2 ? 0.6 : 1.0));
                    drum (X (0.77), Y (0.26), fm * (mm == 0 ? 0.5 : (mm == 1 ? 0.94 : 0.3)));
                    juce::ignoreUnused (xa, xb, damp);
                    label ((key ? juce::String ("KEY TRACK  ") : juce::String()) + juce::String (juce::roundToInt (f0)) + " Hz string   " + juce::String (juce::roundToInt (sprMs)) + " ms spring   " + juce::String (juce::roundToInt (fm)) + " Hz drum");
                }
                else if (ty == 35)   // Yb Spring: the dispersive spring (FX-YBPARTS)
                {
                    const double sprMs = 20.0 * std::pow (12.5, P (0)), dec = P (1), disp = P (2), damp = P (3), boing = P (4);
                    const int two = (mode % 3) == 1 ? 2 : 1;
                    for (int v = 0; v < ((mode % 3) == 0 ? 1 : 2); ++v)
                    {
                        const float cy = (mode % 3) == 0 ? Y (0.5) : Y (v == 0 ? 0.32 : 0.68);
                        const int turns = 8 + juce::roundToInt ((v == 1 && (mode % 3) != 2 ? 1.37 : 1.0) * 16.0 * P (0));
                        juce::Path p; const float x0 = X (0.08), x1 = x0 + (X (0.92) - x0) * (0.55f + 0.45f * (float) dec);
                        for (int i = 0; i <= turns * 12; ++i)
                        {
                            float u = (float) i / (float) (turns * 12), uu = (float) std::pow ((double) u, 1.0 + 0.8 * disp);
                            float amp = (0.10f - 0.05f * (float) damp * u) * H, wob = (float) boing * 0.05f * H * (float) std::sin (u * 9.0 + v);
                            float xx = x0 + uu * (x1 - x0), yy = cy + wob + amp * (float) std::sin (u * turns * 2 * pi);
                            if (i == 0) p.startNewSubPath (xx, yy); else p.lineTo (xx, yy);
                        }
                        stroke (p, 0.9f, 1.8f);
                        g.setColour (ink.withAlpha (0.5f)); g.drawLine (X (0.02), cy, x0, cy, 1.4f);
                    }
                    juce::ignoreUnused (two);
                    label (juce::String (juce::roundToInt (sprMs)) + " ms spring   " + juce::String (juce::roundToInt (dec * 100.0)) + "% decay");
                }
                else if (ty == 36)   // Yb Drum: rectangular membrane, mode bars
                {
                    const bool key = mode >= 3; const int mm = key ? mode - 3 : mode;
                    const double fm = 40.0 * std::pow (6.25, P (0)), asp = 0.6 + P (2), xs = 0.1 + 0.4 * P (3), xp = 0.1 + 0.4 * P (4), dk = 0.2 + 1.8 * P (5), t60 = 0.4 + 2.5 * P (1);
                    static const int mmv[8] = { 1, 1, 2, 2, 1, 3, 2, 3 }, nnv[8] = { 1, 2, 1, 2, 3, 1, 3, 2 };
                    const double nrm = std::sqrt (1.0 + 1.0 / (asp * asp));
                    const int drums = mm == 0 ? 1 : 2;
                    for (int v = 0; v < drums; ++v)
                    {
                        const double tune = v == 0 ? 1.0 : (mm == 1 ? 0.5 : 0.94);
                        const float base = drums == 1 ? Y (0.92) : (v == 0 ? Y (0.48) : Y (0.94));
                        const float hh = drums == 1 ? 0.8f * H : 0.4f * H;
                        for (int k = 0; k < 8; ++k)
                        {
                            const double ratio = std::sqrt ((double) (mmv[k] * mmv[k]) + (double) (nnv[k] * nnv[k]) / (asp * asp)) / nrm, f = fm * tune * ratio;
                            const double w = std::abs (std::sin (pi * mmv[k] * xs) * std::sin (pi * nnv[k] * 0.46) * std::sin (pi * mmv[k] * xp) * std::sin (pi * nnv[k] * 0.45));
                            const double tk = t60 / (1.0 + dk * (ratio - 1.0));
                            const float x = X (std::log (f / 30.0) / std::log (2000.0 / 30.0)), a = (float) juce::jlimit (0.04, 1.0, w * 1.4) * hh;
                            g.setColour (col.withAlpha ((float) juce::jlimit (0.25, 0.95, tk / (t60 + 0.01) + 0.2))); g.fillRect (x - 2.0f, base - a, 4.0f, a);
                        }
                    }
                    label ((key ? juce::String ("KEY TRACK  ") : juce::String()) + juce::String (juce::roundToInt (fm)) + " Hz drum   aspect " + juce::String (asp, 2));
                }
                else if (ty == 37)   // Yb String: string loop with harmonic bars
                {
                    const bool key = mode >= 3; const int mm = key ? mode - 3 : mode;
                    const double f0 = 40.0 * std::pow (20.0, P (0)), dec = P (1), damp = P (2), bow = P (3), ct = (P (4) - 0.5) * 50.0;
                    const float cy = Y (0.3);
                    g.setColour (ink.withAlpha (0.6f)); g.drawLine (X (0.04), cy, X (0.96), cy, 1.5f);
                    juce::Path sp; for (int i = 0; i <= 80; ++i) { float u = (float) i / 80.0f, yy = cy + (float) (0.14 * H * (0.4 + 0.6 * bow) * std::sin (u * pi) * std::sin (u * 2 * pi * 3.0)); if (i == 0) sp.startNewSubPath (X (0.04) + u * (X (0.96) - X (0.04)), yy); else sp.lineTo (X (0.04) + u * (X (0.96) - X (0.04)), yy); }
                    stroke (sp, 0.9f, 1.8f);
                    const float base = Y (0.92);
                    for (int s2 = 0; s2 < (mm == 0 ? 1 : 2); ++s2)
                        for (int h = 1; h <= 24; ++h)
                        {
                            const double f = f0 * h * (s2 == 0 ? 1.0 : (mm == 2 ? 0.5 : 1.0) * std::pow (2.0, ct / 1200.0));
                            if (f > 18000.0) break;
                            const double a = std::pow (0.5 + 0.5 * dec, h) * (1.0 / (1.0 + h * (1.2 - damp)));
                            const float x = X (std::log (f / 30.0) / std::log (18000.0 / 30.0)), hh = (float) juce::jlimit (0.02, 1.0, a * 2.0) * 0.5f * H;
                            g.setColour (col.withAlpha (s2 == 0 ? 0.9f : 0.5f)); g.fillRect (x - 1.5f, base - hh, 3.0f, hh);
                        }
                    label ((key ? juce::String ("KEY TRACK  ") : juce::String()) + juce::String (juce::roundToInt (f0)) + " Hz string");
                }

                // ---- live data of the DSP (FX-VIZ): spectrum strip (output filled, input as ticks), level meters and the operating point on transfer curves ----
                {
                    auto& v = im.ctx.be.fxViz;
                    if (v.slot == gi && gi < 48 && juce::Time::getMillisecondCounter() - v.stamp < 400)
                    {
                        const float sh = H * 0.30f; const auto strip = juce::Rectangle<float> (r.getX(), r.getBottom() - sh, W - 34.0f, sh);
                        g.setColour (juce::Colours::black.withAlpha (0.28f)); g.fillRect (strip);
                        const float bw = strip.getWidth() / 24.0f;
                        for (int b = 0; b < 24; ++b)
                        {
                            const float ho = v.outB[b] * strip.getHeight(), hi = v.inB[b] * strip.getHeight();
                            g.setColour (col.withAlpha (0.6f)); g.fillRect (strip.getX() + bw * (float) b + 1.0f, strip.getBottom() - ho, bw - 2.0f, ho);
                            g.setColour (ink.withAlpha (0.75f)); g.fillRect (strip.getX() + bw * (float) b + 1.0f, strip.getBottom() - hi - 1.0f, bw - 2.0f, 1.5f);
                        }
                        g.setColour (dim); g.setFont (font (8.0f, true)); g.drawText ("LIVE  40 Hz - 16 kHz   bars = out, ticks = in", strip.toNearestInt().reduced (3, 1), juce::Justification::topRight, false);
                        // level meters: in L, in R, out L, out R (-60 .. 0 dB)
                        for (int k = 0; k < 4; ++k)
                        {
                            const float nrm = juce::jlimit (0.0f, 1.0f, (20.0f * std::log10 (juce::jmax (1e-4f, v.pk[k])) + 60.0f) / 60.0f);
                            const float mx = r.getRight() - 30.0f + 7.0f * (float) k, mh = H - 6.0f;
                            g.setColour (juce::Colours::black.withAlpha (0.4f)); g.fillRect (mx, r.getY() + 3.0f, 5.0f, mh);
                            g.setColour (v.pk[k] > 0.98f ? juce::Colour (0xffff4040) : (k < 2 ? ink.withAlpha (0.7f) : col)); g.fillRect (mx, r.getY() + 3.0f + mh * (1.0f - nrm), 5.0f, mh * nrm);
                        }
                        g.setColour (dim); g.setFont (font (7.5f, true)); g.drawText ("IN   OUT", juce::Rectangle<float> (r.getRight() - 32.0f, r.getBottom() - 11.0f, 34.0f, 10.0f).toNearestInt(), juce::Justification::centred, false);
                        // time based effects: the real level over the last 4 seconds (echoes, tremolo, reverb tail, grains ...)
                        if (ty == 3 || (ty >= 4 && ty <= 8) || ty == 12 || (ty >= 29 && ty <= 33) || (ty >= 35 && ty <= 37) || ty == 16)
                        {
                            const float th = H * 0.34f, ty0 = r.getY() + 4.0f;
                            auto lv = [&] (float a) { return juce::jlimit (0.0f, 1.0f, (20.0f * std::log10 (juce::jmax (1e-4f, a)) + 60.0f) / 60.0f); };
                            juce::Path pin, pout;
                            const int n = (int) hist.size();
                            for (int i = 0; i < n; ++i)
                            {
                                const float x = r.getX() + (W - 36.0f) * (float) (80 - n + i) / 79.0f;
                                const float yi = ty0 + th * (1.0f - lv (hist[(size_t) i].first)), yo = ty0 + th * (1.0f - lv (hist[(size_t) i].second));
                                if (i == 0) { pin.startNewSubPath (x, yi); pout.startNewSubPath (x, yo); } else { pin.lineTo (x, yi); pout.lineTo (x, yo); }
                            }
                            g.setColour (juce::Colours::black.withAlpha (0.28f)); g.fillRect (r.getX(), ty0 - 2.0f, W - 36.0f, th + 4.0f);
                            g.setColour (ink.withAlpha (0.5f)); g.strokePath (pin, juce::PathStrokeType (1.0f));
                            g.setColour (col); g.strokePath (pout, juce::PathStrokeType (1.8f));
                            g.setColour (dim); g.setFont (font (8.0f, true)); g.drawText ("LEVEL, last 4 s   grey = in, colour = out", juce::Rectangle<float> (r.getX() + 4.0f, ty0, W - 44.0f, 11.0f).toNearestInt(), juce::Justification::topRight, false);
                        }
                        // operating point on a transfer curve: where the loudest input of the last 50 ms ends up
                        const float inA = juce::jmax (v.pk[0], v.pk[1]), outA = juce::jmax (v.pk[2], v.pk[3]);
                        auto dot = [&] (double x, double y) { g.setColour (juce::Colours::white); g.fillEllipse (X (x) - 4.0f, Y (y) - 4.0f, 8.0f, 8.0f); g.setColour (col); g.drawEllipse (X (x) - 6.0f, Y (y) - 6.0f, 12.0f, 12.0f, 1.5f); };
                        if (ty == 1 || ty == 14 || (ty >= 19 && ty <= 25) || ty == 28)
                            dot (0.5 + 0.5 * juce::jlimit (0.0f, 1.0f, inA), 0.5 + 0.5 * juce::jlimit (0.0f, 1.0f, outA));
                        else if (ty == 11)
                        {
                            auto nd = [] (float a) { return juce::jlimit (0.0, 1.0, (20.0 * std::log10 (juce::jmax (1e-4f, a)) + 60.0) / 60.0); };
                            dot (nd (inA), nd (outA));
                        }
                    }
                }
            }
        };

        // ====================================================================================================================
        Impl (FxPage& o, Ctx& c, SoundMemory& m, int oscIdx) : owner (o), ctx (c), mem (m), osc (oscIdx), rkLo (oscIdx < 0 ? 0 : 3 + oscIdx), rkHi (oscIdx < 0 ? 3 : 4 + oscIdx), gLo (oscIdx < 0 ? 0 : kFxMain + oscIdx * 16), gHi (oscIdx < 0 ? kFxMain : kFxMain + oscIdx * 16 + 16), list (*this), chooser (*this), display (*this)
        {
            for (int g = gLo; g < gHi; ++g)
            {
                int b = slotBase (g);
                onT[g] = std::make_unique<OnToggle> (ctx, b + 1);
                mixK[g] = makeWidget (ctx, b + 2, true);
                modeS[g] = makeWidget (ctx, b + 3, false);
                syncS[g] = makeWidget (ctx, fxSyncId (g), false);
                envS[g] = makeWidget (ctx, fxEnvSusId (g), true); envR[g] = makeWidget (ctx, fxEnvRelId (g), true);   // Filter effect: Sustain / Release
                for (int k = 0; k < 6; ++k) pK[g][k] = makeWidget (ctx, b + 4 + k, true);
                for (int k = 0; k < 4; ++k)   // FX-EX: four effect specific extra knobs (meaning by effect type)
                {
                    exK[g][k] = makeWidget (ctx, fxExId (g, k), true);
                    exK[g][k]->setValueTextOverride ([this, g, k] (float v) { return fxExText (fxExTools (ctx.fxSlotTypes()[g])[k], v); });
                    owner.addChildComponent (*exK[g][k]);
                    exK[g][k]->onModDropped = [this] (ParamWidget& w) { if (owner.onModDropped) owner.onModDropped (w); };
                }
                for (int k = 0; k < 4; ++k)   // FX-WET: Low Cut, High Cut, Width, Sat of every effect
                {
                    wK[g][k] = makeWidget (ctx, fxWetId (g, k), true);
                    wK[g][k]->setValueTextOverride ([k] (float v)
                    {
                        if (k == 0) return v < 0.002f ? juce::String ("Off") : juce::String (juce::roundToInt (20.0 * std::pow (50.0, (double) v))) + " Hz";
                        if (k == 1) return v > 0.998f ? juce::String ("Off") : juce::String (juce::roundToInt (1500.0 * std::pow (13.3333, (double) v))) + " Hz";
                        return juce::String (juce::roundToInt (v * (k == 2 ? 200 : 100))) + "%";
                    });
                    owner.addChildComponent (*wK[g][k]);
                    wK[g][k]->onModDropped = [this] (ParamWidget& w) { if (owner.onModDropped) owner.onModDropped (w); };
                }
                for (auto* w : { (ParamWidget*) onT[g].get(), mixK[g].get(), modeS[g].get(), syncS[g].get(), envS[g].get(), envR[g].get() }) owner.addChildComponent (w);
                for (auto& w : pK[g]) owner.addChildComponent (*w);
                auto drop = [this] (ParamWidget& p) { if (owner.onModDropped) owner.onModDropped (p); };
                mixK[g]->onModDropped = drop; for (auto& w : pK[g]) w->onModDropped = drop;
                pos[fxRkOf (g) * kFxPer + fxSlOf (g)] = fxSlOf (g);
                refreshSlot (g);
            }
            if (osc < 0)
            for (int num : { 175, 221, 222, 11600, 11601 })   // MASTER-OUT: Drive and Tone are gone
            {
                auto w = makeWidget (ctx, num, true);
                w->onModDropped = [this] (ParamWidget& p) { if (owner.onModDropped) owner.onModDropped (p); };
                owner.addAndMakeVisible (*w); outs.add (w.release());
            }
            listVp.setViewedComponent (&list, false); listVp.setScrollBarsShown (true, false); listVp.setScrollBarThickness (8); owner.addAndMakeVisible (listVp); owner.addChildComponent (chooser); owner.addChildComponent (display);
            eqEd = std::make_unique<EqEditor> (ctx, mem); owner.addChildComponent (*eqEd);
            shEd = std::make_unique<ShaperEditor> (ctx, mem); owner.addChildComponent (*shEd);
            addBtn.text = "+ ADD FX"; addBtn.click = [this] { adding = true; layoutCentre(); owner.repaint(); refreshList(); };
            removeBtn.text = "REMOVE"; removeBtn.click = [this] { removeSelected(); };
            tblPick.click = [this] { pickTable(); }; owner.addChildComponent (tblPick);
            tblBtn.text = "EDIT TABLE"; tblBtn.click = [this] { openTable(); };
            owner.addAndMakeVisible (addBtn); owner.addChildComponent (removeBtn); owner.addChildComponent (tblBtn);
            for (int rk = 0; rk < kFxRacks; ++rk) { sel[rk] = -1; }
            loadIr.text = "LOAD IR"; clearIr.text = "CLEAR";
            loadIr.click = [this]
            {
                chooser2 = std::make_shared<juce::FileChooser> ("Load an impulse response", juce::File(), SoundMemory::fileWildcard());
                auto self = juce::Component::SafePointer<FxPage> (&owner);
                int rk = current;
                chooser2->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles,
                                       [self, rk] (const juce::FileChooser& fc)
                                       { auto f = fc.getResult(); if (self != nullptr && f.existsAsFile()) { self->impl->mem.load (SoundMemory::ImpulseResponse, rk, f, {}); self->repaint(); } });
            };
            clearIr.click = [this] { mem.clear (SoundMemory::ImpulseResponse, current); owner.repaint(); };
            owner.addChildComponent (loadIr); owner.addChildComponent (clearIr);
            ctx.addListener (this);
            applyOrders();
            for (int rk = rkLo; rk < rkHi; ++rk) autoSelect (rk);
            showRack (rkLo);
        }
        ~Impl() override { ctx.removeListener (this); }

        int slotBase (int g) const { return fxSlotId (g); }

        // the list lives in a viewport (16 effects do not fit): its height follows the number of effects, the selected one is kept in view
        void refreshList()
        {
            auto u = usedSlots (current);
            list.setSize (juce::jmax (10, listVp.getMaximumVisibleWidth()), juce::jmax (listVp.getHeight(), (int) u.size() * kItemH));
            if (! adding && sel[current] >= 0)
            {
                int idx = (int) (std::find (u.begin(), u.end(), sel[current]) - u.begin());
                if (idx < (int) u.size())
                {
                    const int y = idx * kItemH, vy = listVp.getViewPositionY();
                    if (y < vy) listVp.setViewPosition (0, y);
                    else if (y + kItemH > vy + listVp.getHeight()) listVp.setViewPosition (0, y + kItemH - listVp.getHeight());
                }
            }
            list.repaint();
        }

        // ---- order bookkeeping (16 order parameters per rack: position k holds the rack-local slot number) ----
        using Order = std::array<int, kFxPer>;
        Order orderNow (int rk) const
        {
            Order o {};
            for (int k = 0; k < kFxPer; ++k) o[(size_t) k] = juce::roundToInt (ctx.get (fxOrdId (rk, k)));
            return o;
        }
        void applyOrders() { for (int rk = rkLo; rk < rkHi; ++rk) applyOrder (rk); }
        void applyOrder (int rk)
        {
            auto order = orderNow (rk);
            int p[kFxPer]; for (int& x : p) x = -1;
            for (int k = 0; k < kFxPer; ++k) if (order[(size_t) k] >= 0 && order[(size_t) k] < kFxPer && p[order[(size_t) k]] < 0) p[order[(size_t) k]] = k;
            int spare = kFxPer; for (int sl = 0; sl < kFxPer; ++sl) if (p[sl] < 0) p[sl] = spare++;
            for (int sl = 0; sl < kFxPer; ++sl) pos[rk * kFxPer + sl] = p[sl];
            refreshList();
        }
        void commit (int rk, const Order& order)
        {
            auto cur = orderNow (rk);
            for (int k = 0; k < kFxPer; ++k) if (order[(size_t) k] != cur[(size_t) k]) ctx.set (fxOrdId (rk, k), (float) order[(size_t) k]);
            applyOrder (rk);
        }
        std::vector<int> usedSlots (int rk) const
        {
            std::vector<int> v;
            for (int sl = 0; sl < kFxPer; ++sl) if (ctx.fxSlotTypes()[fxG (rk, sl)] > 0) v.push_back (sl);
            std::sort (v.begin(), v.end(), [&] (int a, int b) { return pos[rk * kFxPer + a] < pos[rk * kFxPer + b]; });
            return v;
        }
        int freeSlot (int rk) const { for (int sl = 0; sl < kFxPer; ++sl) if (ctx.fxSlotTypes()[fxG (rk, sl)] == 0) return sl; return -1; }

        // moves an effect by `dir` places among the used ones (swapping the processing positions)
        void moveUsed (int rk, int sl, int dir)
        {
            auto used = usedSlots (rk);
            int idx = (int) (std::find (used.begin(), used.end(), sl) - used.begin());
            int to = juce::jlimit (0, (int) used.size() - 1, idx + dir); if (idx >= (int) used.size() || to == idx) return;
            auto order = orderNow (rk);
            std::vector<int> v (order.begin(), order.end());
            int target = pos[rk * kFxPer + used[(size_t) to]];
            v.erase (std::find (v.begin(), v.end(), sl)); v.insert (v.begin() + juce::jlimit (0, kFxPer - 1, target), sl);
            Order n; for (int k = 0; k < kFxPer; ++k) n[(size_t) k] = v[(size_t) k];
            commit (rk, n);
        }

        // ---- selection / add / remove ----
        void select (int rk, int sl) { sel[rk] = sl; adding = false; layoutCentre(); refreshList(); owner.repaint(); }
        void autoSelect (int rk) { auto u = usedSlots (rk); if (sel[rk] < 0 || ctx.fxSlotTypes()[fxG (rk, sel[rk])] == 0) sel[rk] = u.empty() ? -1 : u.back(); }
        void showRack (int rk) { current = rk; adding = false; autoSelect (rk); updateTabs(); layoutCentre(); refreshList(); owner.repaint(); }
        void updateTabs()
        {
            const int tabRk[] = { rkLo };
            for (int i = 0; i < tabs.size(); ++i) { tabs[i]->used = ! usedSlots (tabRk[i]).empty(); tabs[i]->on = tabRk[i] == current; tabs[i]->repaint(); }
        }

        void addEffect (int type)
        {
            int rk = current, sl = freeSlot (rk); if (sl < 0) return;
            auto used = usedSlots (rk);
            std::vector<int> v = used; v.push_back (sl);
            for (int s : Order (orderNow (rk))) if (std::find (v.begin(), v.end(), s) == v.end()) v.push_back (s);
            Order n; for (int k = 0; k < kFxPer; ++k) n[(size_t) k] = v[(size_t) k];
            int b = slotBase (fxG (rk, sl));
            ctx.begin (b); ctx.set (b, (float) type); ctx.end (b);
            applyTypeDefaults (fxG (rk, sl), type);
            commit (rk, n);
            sel[rk] = sl; adding = false;
            refreshSlot (fxG (rk, sl)); updateTabs(); layoutCentre(); refreshList(); owner.repaint();
        }
        void removeSelected()
        {
            int rk = current, sl = sel[rk]; if (sl < 0) return;
            int b = slotBase (fxG (rk, sl));
            ctx.begin (b); ctx.set (b, 0.0f); ctx.end (b);
            sel[rk] = -1; autoSelect (rk); updateTabs(); layoutCentre(); refreshList(); owner.repaint();
        }

        // a new effect starts from its own sensible settings (user changes only)
        void applyTypeDefaults (int g, int type)
        {
            int b = slotBase (g);
            auto& t = fxTypes()[(size_t) juce::jlimit (0, (int) fxTypes().size() - 1, type)];
            ctx.set (b + 1, 1.0f); ctx.set (b + 2, t.mix); ctx.set (b + 3, 0.0f);
            for (size_t k = 0; k < t.params.size(); ++k) ctx.set (b + 4 + (int) k, t.params[k].def);
            { const float wd[4] = { 0.0f, 1.0f, 0.5f, 0.0f }; for (int k = 0; k < 4; ++k) ctx.set (fxWetId (g, k), wd[k]); }   // FX-WET
            for (int k = 0; k < 4; ++k) ctx.set (fxExId (g, k), 0.0f);   // FX-EX
        }

        // labels / mode list of the widgets of one slot follow its effect type
        void refreshSlot (int g)
        {
            auto& t = fxTypes()[(size_t) juce::jlimit (0, (int) fxTypes().size() - 1, ctx.fxSlotTypes()[g])];
            if (auto* s = dynamic_cast<SelectWidget*> (modeS[g].get())) s->setOptions (t.modes, t.groups);
            for (int k = 0; k < 6; ++k) if (k < (int) t.params.size()) pK[g][k]->setLabelOverride (t.params[(size_t) k].name);
            for (int k = 0; k < 4; ++k) { exK[g][k]->setLabelOverride (fxExName (fxExTools (ctx.fxSlotTypes()[g])[k])); exK[g][k]->repaint(); }   // FX-EX
            if (ctx.fxSlotTypes()[g] == 9 && juce::roundToInt (ctx.get (slotBase (g) + 3)) == 32)
                pK[g][2]->setLabelOverride ("Scream");   // Drive knob = Scream amount
        }

        void paramChanged (int num, float) override
        {
            if ((num >= 940 && num < 970) || (num >= 3000 && num < 3060) || (num >= 3400 && num < 3418)) { layoutCentre(); owner.repaint(); return; }
            if (osc >= 0 && num >= kOscFxBase + kOscFxStride * osc + 10 && num < kOscFxBase + kOscFxStride * (osc + 1) && num < kOscFxBase + kOscFxStride * osc + 256 && (num - kOscFxBase) % 16 >= 10) { layoutCentre(); owner.repaint(); return; }
            auto loc = fxLocate (num);
            if (! loc.valid || loc.rk < rkLo || loc.rk >= rkHi) return;
            if (loc.ord >= 0) { applyOrder (loc.rk); return; }
            if (loc.off == 3) refreshSlot (loc.g);
            if (loc.off == 3 && loc.rk == current) { layoutCentre(); owner.repaint(); }
            if (loc.off == 0)
            {
                refreshSlot (loc.g);
                if (sel[loc.rk] == loc.sl && ctx.fxSlotTypes()[loc.g] == 0) sel[loc.rk] = -1;
                autoSelect (loc.rk); updateTabs();
                if (loc.rk == current) { layoutCentre(); owner.repaint(); }
            }
            refreshList();
        }

        // ---- centre area ----
        void layoutCentre()
        {
            for (int g = gLo; g < gHi; ++g)
            {
                onT[g]->setVisible (false); mixK[g]->setVisible (false); modeS[g]->setVisible (false); syncS[g]->setVisible (false); envS[g]->setVisible (false); envR[g]->setVisible (false);
                for (auto& w : pK[g]) w->setVisible (false);
                for (auto& w : wK[g]) w->setVisible (false);   // FX-WET
                for (auto& w : exK[g]) w->setVisible (false);   // FX-EX
            }
            int sl = sel[current];
            bool effectPage = ! adding && sl >= 0 && ctx.fxSlotTypes()[fxG (current, sl)] > 0;
            chooser.setVisible (! effectPage); display.setVisible (false); eqEd->setVisible (false); shEd->setVisible (false); removeBtn.setVisible (effectPage); tblBtn.setVisible (false); tblPick.setVisible (false);
            loadIr.setVisible (false); clearIr.setVisible (false); irRect = {};
            chooser.setBounds (centre);
            addBtn.setBounds (addRect);
            if (! effectPage) return;
            int g = fxG (current, sl), ty = ctx.fxSlotTypes()[g];
            auto& t = fxTypes()[(size_t) ty];
            auto c = centre;
            auto head = c.removeFromTop (34);
            removeBtn.setBounds (head.removeFromRight (84).reduced (0, 4));
            head.removeFromRight (8);
            onT[g]->setBounds (head.removeFromRight (96).reduced (0, 3)); onT[g]->setVisible (true);
            head.removeFromRight (8);
            titleRect = head.removeFromLeft (220);
            syncRect = {};
            if (t.modes.size() > 0) { modeS[g]->setBounds (head.removeFromLeft (150).reduced (0, 2)); modeS[g]->setVisible (true); }
            if (ty >= 3 && ty <= 7)
            {
                head.removeFromLeft (8);
                syncRect = head.removeFromLeft (100);
                syncS[g]->setBounds (syncRect.withTrimmedLeft (34).reduced (0, 2)); syncS[g]->setVisible (true);
            }
            if (ty == 12 && juce::roundToInt (ctx.get (slotBase (g) + 3)) == 8)
            {
                head.removeFromLeft (10);
                loadIr.setBounds (head.removeFromLeft (84).reduced (0, 4)); loadIr.setVisible (true);
                head.removeFromLeft (6);
                clearIr.setBounds (head.removeFromLeft (64).reduced (0, 4)); clearIr.setVisible (true);
                head.removeFromLeft (8);
                irRect = head;
            }
            if (ty == 34 || ty == 39)
            {
                head.removeFromLeft (8);
                tblBtn.setBounds (head.removeFromLeft (96).reduced (0, 4)); tblBtn.setVisible (true);
            }
            if (ty == 13 || ty == 38)
            {
                eqEd->setBounds (c); eqEd->setSlot (g, slotBase (g), ty == 38); eqEd->setVisible (true);
                return;
            }
            auto knobs2 = c.removeFromBottom (84);   // FX-EX: second row: the four effect specific knobs and the four wet knobs
            c.removeFromBottom (4);
            auto knobs = c.removeFromBottom (84);
            c.removeFromBottom (6);
            if (ty == 15) { shEd->setBounds (c); shEd->setSlot (g, slotBase (g)); shEd->setVisible (true); }
            else { display.setVisible (true); display.setBounds (c); }
            int n = 1 + (int) t.params.size(), colW = juce::jmin (120, knobs.getWidth() / juce::jmax (1, n));
            int x0 = knobs.getX() + (knobs.getWidth() - colW * n) / 2;
            auto put = [&] (ParamWidget& w, int i) { w.setBounds (x0 + i * colW + (colW - 70) / 2, knobs.getY() + 12, 70, 62); w.setVisible (true); };
            put (*mixK[g], 0);
            for (int k = 0; k < (int) t.params.size(); ++k)
            {
                if ((ty == 39 && k == 3) || (ty == 34 && k == 2))   // the Table knob is a menu: which oscillator's table the effect reads
                {
                    tblG = g; tblK = k; const int o = juce::jlimit (0, 5, juce::roundToInt (ctx.get (slotBase (g) + 4 + k) * 5.0f));
                    tblPick.text = "TABLE: OSC " + juce::String (o + 1) + "  v";
                    tblPick.setBounds (x0 + (k + 1) * colW + (colW - 104) / 2, knobs.getY() + 26, 104, 28); tblPick.setVisible (true);
                    continue;
                }
                put (*pK[g][k], k + 1);
            }
            {
                const int n2 = 9, c2 = juce::jmin (120, knobs2.getWidth() / n2), x2 = knobs2.getX() + (knobs2.getWidth() - c2 * n2) / 2;
                auto put2 = [&] (ParamWidget& w, int i) { w.setBounds (x2 + i * c2 + (c2 - 70) / 2, knobs2.getY() + 12, 70, 62); w.setVisible (true); };
                for (int k = 0; k < 4; ++k) put2 (*exK[g][k], k);
                for (int k = 0; k < 4; ++k) put2 (*wK[g][k], 5 + k);   // FX-WET
            }
            // controls that do nothing right now are dimmed: the rate / time follows the sync division, the gate knobs only matter for their modes
            const int md = juce::roundToInt (ctx.get (slotBase (g) + 3)), sy = juce::roundToInt (ctx.get (fxSyncId (g)));
            for (int k = 0; k < 6; ++k) pK[g][k]->setAlpha (1.0f);
            if (sy > 0 && ty >= 3 && ty <= 7) pK[g][0]->setAlpha (0.35f);
            if (ty == 9)
            {
                const float ea = std::abs (ctx.get (slotBase (g) + 7) - 0.5f) < 0.004f ? 0.35f : 1.0f;   // Env Amt in the middle = no envelope
                pK[g][4]->setAlpha (ea);   // Env Src only matters with an Env Amt
            }
            if (ty == 7)
            {
                pK[g][2]->setAlpha (md == 6 || md == 8 ? 0.35f : 1.0f);
                pK[g][3]->setAlpha (md == 5 ? 1.0f : 0.35f);
                pK[g][4]->setAlpha (md == 5 || md == 7 ? 1.0f : 0.35f);
                pK[g][5]->setAlpha (md == 5 ? 1.0f : 0.35f);
            }
        }

        // the table editor (Wavedistortion table for the Shaper Table, Wavefilter table for the Wavefilter) of the oscillator chosen in the Table knob
        bool tableSlotSelected() const { const int sl = sel[current]; if (sl < 0) return false; const int ty = ctx.fxSlotTypes()[fxG (current, sl)]; return ty == 34 || ty == 39; }
        void dropOnTable (const juce::StringArray& f) { if (! tableSlotSelected()) return; openTable(); for (auto& e : tblEd) if (e && e->isVisible()) { e->filesDropped (f, 0, 0); break; } }
        void openTable()
        {
            const int sl = sel[current]; if (sl < 0) return;
            const int g = fxG (current, sl), ty = ctx.fxSlotTypes()[g];
            if (ty != 34 && ty != 39) return;
            const int osc = juce::jlimit (0, 5, juce::roundToInt (ctx.get (slotBase (g) + 4 + (ty == 39 ? 3 : 2)) * 5.0f));
            auto& e = tblEd[(ty == 39 ? 6 : 0) + osc];
            if (! e) { e = std::make_unique<TableEditor> (ctx, mem, osc, ty == 39); owner.addChildComponent (*e); e->onClose = [this] { layoutCentre(); owner.repaint(); }; }
            e->setBounds (owner.getLocalBounds()); e->open();
        }
        FxButton tblPick; int tblG = -1, tblK = 0;
        void pickTable()
        {
            if (tblG < 0) return; juce::PopupMenu m; const int cur = juce::jlimit (0, 5, juce::roundToInt (ctx.get (slotBase (tblG) + 4 + tblK) * 5.0f));
            for (int i = 0; i < 6; ++i) m.addItem (i + 1, "Table of oscillator " + juce::String (i + 1), true, cur == i);
            const int g = tblG, k = tblK; juce::Component::SafePointer<juce::Component> sp (&owner);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&tblPick), [this, sp, g, k] (int r)
            {
                if (sp == nullptr || r <= 0) return; const int id = slotBase (g) + 4 + k;
                ctx.begin (id); ctx.set (id, (float) (r - 1) / 5.0f); ctx.end (id); layoutCentre(); owner.repaint();
            });
        }
        FxPage& owner; Ctx& ctx; SoundMemory& mem;
        std::unique_ptr<EqEditor> eqEd; std::unique_ptr<ShaperEditor> shEd;
        FxButton loadIr, clearIr; juce::Rectangle<int> irRect; std::shared_ptr<juce::FileChooser> chooser2;
        juce::Viewport listVp; ListComp list; Chooser chooser; Display display; FxButton addBtn, removeBtn, tblBtn; std::unique_ptr<TableEditor> tblEd[12];
        std::unique_ptr<OnToggle> onT[kFxTotal]; std::unique_ptr<ParamWidget> mixK[kFxTotal], modeS[kFxTotal], syncS[kFxTotal], envS[kFxTotal], envR[kFxTotal], pK[kFxTotal][6], wK[kFxTotal][4], exK[kFxTotal][4]; juce::Rectangle<int> syncRect;
        juce::OwnedArray<DotTab> tabs; juce::OwnedArray<ParamWidget> outs;
        juce::Rectangle<int> mainCard, outCard, listRect, addRect, centre, titleRect;
        int osc, rkLo, rkHi, gLo, gHi;   // osc >= 0: the rack page of that oscillator (rack 3 + osc, global slots 48 + 16 * osc ..)
        juce::OwnedArray<DotTab> chips;
        int current = 0, sel[kFxRacks] = {}, pos[kFxRacks * kFxPer] = {}; bool adding = false;
    };

    FxPage::FxPage (Ctx& c, SoundMemory& m, int osc) : impl (new Impl (*this, c, m, osc))
    {
        if (osc >= 0)
            for (int i = 0; i < OSC_N; ++i)
            {
                auto* b = impl->chips.add (new DotTab());
                b->text = juce::String::charToString ((juce::juce_wchar) ('A' + i)); b->on = i == osc; b->used = false;
                b->click = [this, i] { if (onSelectOsc) onSelectOsc (i); };
                addAndMakeVisible (b);
            }
    }
    FxPage::~FxPage() = default;
    bool FxPage::isInterestedInFileDrag (const juce::StringArray& f) { if (! impl->tableSlotSelected()) return false; for (auto& n : f) if (juce::File (n).hasFileExtension ("wav;aif;aiff;flac;ogg;mp3;vitaltable")) return true; return false; }
    void FxPage::filesDropped (const juce::StringArray& f, int, int) { impl->dropOnTable (f); }

    void FxPage::resized()
    {
        auto b = getLocalBounds();
        if (impl->osc < 0) { impl->outCard = b.removeFromBottom (84); b.removeFromBottom (6); }
        impl->mainCard = b;
        auto m = impl->mainCard.reduced (12, 8);
        auto head = m.removeFromTop (22);
        head.removeFromLeft (110);
        int x = head.getX();
        for (auto* t : impl->tabs) { t->setBounds (x, head.getY(), 76, 20); x += 80; }
        for (auto* t : impl->chips) { t->setBounds (x, head.getY(), 26, 20); x += 30; }
        m.removeFromTop (8);
        auto left = m.removeFromLeft (kLeftW); m.removeFromLeft (14);
        impl->addRect = left.removeFromBottom (28); left.removeFromBottom (6);
        impl->listRect = left;
        impl->listVp.setBounds (impl->listRect);
        impl->refreshList();
        impl->centre = m;
        impl->layoutCentre();
        auto o = impl->outCard.reduced (12, 6); o.removeFromTop (18);
        int w = o.getWidth() / 6;
        for (int i = 0; i < impl->outs.size(); ++i) impl->outs[i]->setBounds (o.getX() + i * w + 6, o.getY(), w - 12, o.getHeight());
    }

    void FxPage::paint (juce::Graphics& g)
    {
        paintCard (g, impl->mainCard.toFloat());
        if (impl->osc < 0) paintCard (g, impl->outCard.toFloat());
        auto head = [&] (juce::Rectangle<int> card, const juce::String& t)
        {
            g.setColour (red); g.fillRect (juce::Rectangle<float> ((float) card.getX() + 12, (float) card.getY() + 13, 7, 7));
            g.setFont (impact (11.0f)); g.drawText (t, card.getX() + 24, card.getY() + 8, 90, 16, juce::Justification::centredLeft);
        };
        head (impl->mainCard, impl->osc < 0 ? juce::String ("FX") : "OSC " + juce::String (impl->osc + 1) + " FX"); if (impl->osc < 0) head (impl->outCard, "OUTPUT");
        g.setColour (dim); g.setFont (font (8.5f));
        g.drawText ("Signal runs top to bottom", impl->mainCard.withTrimmedLeft (320).withHeight (30).reduced (10, 0), juce::Justification::centredRight, true);
        // panel behind the list and the centre area
        paintInset (g, impl->listRect.toFloat().expanded (4, 4).withTrimmedBottom (-34), 4.0f);
        g.setColour (dim); g.setFont (font (8.0f, true).withExtraKerningFactor (0.2f));
        // effect page title
        int sl = impl->sel[impl->current];
        if (! impl->adding && sl >= 0 && impl->ctx.fxSlotTypes()[fxG (impl->current, sl)] > 0)
        {
            int ty = impl->ctx.fxSlotTypes()[fxG (impl->current, sl)];
            g.setColour (fxColour (ty)); g.fillRect (impl->titleRect.getX(), impl->titleRect.getY() + 6, 4, impl->titleRect.getHeight() - 12);
            g.setColour (ink); g.setFont (impact (19.0f));
            g.drawText (fxTypes()[(size_t) ty].name.toUpperCase(), impl->titleRect.withTrimmedLeft (14), juce::Justification::centredLeft, true);
            if (! impl->syncRect.isEmpty())
            {
                g.setColour (dim); g.setFont (font (8.0f, true).withExtraKerningFactor (0.15f));
                g.drawText ("SYNC", impl->syncRect.withWidth (34), juce::Justification::centredLeft);
            }
            if (! impl->irRect.isEmpty())
            {
                auto* s = impl->mem.get (SoundMemory::ImpulseResponse, impl->current);
                g.setColour (s ? ink : dim); g.setFont (font (9.5f, true));
                g.drawText (s ? s->name : juce::String ("NO FILE LOADED"), impl->irRect, juce::Justification::centredLeft, true);
            }
        }
    }
}
