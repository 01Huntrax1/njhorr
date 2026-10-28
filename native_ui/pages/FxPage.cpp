// FX page: three racks (Bus 1, Bus 2, Main) of 10 slots, laid out like a modern synth's effect page: the list of the rack's effects on the left
// (processing order, on / off, move, drag), "+ ADD FX" opens a grid of all effect types, and the selected effect has its own page with a display and large knobs.
// Below: the output section. Parameters and the processing order are unchanged (patch/index.js FX rack).
#include "../NjoPages.h"
#include "OscDisplays.h"
#include <algorithm>
#include <array>
#include <cmath>

namespace njo
{
    using namespace theme;

    namespace
    {
        constexpr int kItemH = 28, kLeftW = 214;

        juce::Colour fxColour (int type)
        {
            static const juce::uint32 c[] = { 0xff555555, 0xffe0803a, 0xffd860a8, 0xffe0507a, 0xff30d0d8, 0xffe08c40, 0xffa060e0, 0xff80d060, 0xff30c090, 0xff40a0e0, 0xffe8e8e8, 0xffe8c030, 0xff58b8f0 };
            return juce::Colour (c[juce::jlimit (0, 12, type)]);
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
                g.setColour (on ? juce::Colour (0xff111111) : ink); g.setFont (font (9.5f, true));
                g.drawText (text.toUpperCase(), r.withTrimmedRight (12).toNearestInt(), juce::Justification::centred);
                auto d = juce::Rectangle<float> (r.getRight() - 12, r.getCentreY() - 3, 6, 6);
                g.setColour (used ? (on ? juce::Colour (0xff111111) : orange) : juce::Colour (0xff3a1f1c)); g.fillEllipse (d);
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
                    int sl = used[(size_t) i], gi = im.current * 10 + sl, ty = im.ctx.fxSlotTypes()[gi];
                    bool on = im.ctx.get (im.slotBase (gi) + 1) > 0.5f, selected = im.sel[im.current] == sl && ! im.adding;
                    auto r = itemR (i).toFloat().reduced (0, 1.5f);
                    g.setColour (dragIdx == i ? juce::Colour (0xff3a1815) : (selected ? juce::Colour (0xff2a2020) : juce::Colour (0xff131415))); g.fillRoundedRectangle (r, 3.0f);
                    if (selected) { g.setColour (red.withAlpha (0.8f)); g.drawRoundedRectangle (r.reduced (0.5f), 3.0f, 1.0f); }
                    g.setColour (fxColour (ty).withAlpha (on ? 1.0f : 0.3f)); g.fillRect (r.getX() + 1, r.getY() + 3, 3.0f, r.getHeight() - 6);
                    // on / off dot
                    auto dot = juce::Rectangle<float> (r.getX() + 12, r.getCentreY() - 4, 8, 8);
                    g.setColour (on ? fxColour (ty) : juce::Colour (0xff3a3a3d)); g.fillEllipse (dot);
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
                int sl = used[(size_t) i], gi = im.current * 10 + sl;
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

        // ---- grid of all effect types ("+ ADD FX") ----
        struct Chooser : public juce::Component
        {
            explicit Chooser (Impl& i) : im (i) {}
            Impl& im; int over = -1;
            static constexpr int cols = 3, bw = 190, bh = 40, gap = 14;
            juce::Rectangle<int> cell (int i) const
            {
                int n = (int) fxTypes().size() - 1, rows = (n + cols - 1) / cols;
                int totalW = cols * bw + (cols - 1) * gap, totalH = rows * bh + (rows - 1) * gap;
                int x0 = (getWidth() - totalW) / 2, y0 = 54 + juce::jmax (0, (getHeight() - 54 - totalH) / 2 - 10);
                return { x0 + (i % cols) * (bw + gap), y0 + (i / cols) * (bh + gap), bw, bh };
            }
            void paint (juce::Graphics& g) override
            {
                bool full = im.freeSlot (im.current) < 0;
                g.setColour (ink); g.setFont (impact (14.0f));
                g.drawText (full ? "THIS RACK IS FULL (10 EFFECTS)" : "ADD AN EFFECT TO " + fxRacks()[(size_t) im.current].name.toUpperCase(), getLocalBounds().withHeight (28).withTrimmedTop (6), juce::Justification::centred);
                g.setColour (dim); g.setFont (font (9.5f));
                g.drawText (full ? "Remove an effect first." : "The effect is appended to the end of the chain. Drag it in the list to move it.", getLocalBounds().withTop (30).withHeight (18), juce::Justification::centred);
                for (int i = 0; i < (int) fxTypes().size() - 1; ++i)
                {
                    auto r = cell (i).toFloat();
                    g.setColour (juce::Colour (over == i && ! full ? 0xff2a2c2f : 0xff17181a)); g.fillRoundedRectangle (r, 3.0f);
                    g.setColour (fxColour (i + 1).withAlpha (full ? 0.3f : 1.0f)); g.fillRect (r.getX(), r.getY(), 4.0f, r.getHeight());
                    g.setColour (full ? dim : ink); g.setFont (font (12.0f, true));
                    g.drawText (fxTypes()[(size_t) i + 1].name, r.withTrimmedLeft (16).toNearestInt(), juce::Justification::centredLeft);
                }
            }
            void mouseMove (const juce::MouseEvent& e) override { int o = hit (e.getPosition()); if (o != over) { over = o; repaint(); } }
            void mouseExit (const juce::MouseEvent&) override { over = -1; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { int i = hit (e.getPosition()); if (i >= 0) im.addEffect (i + 1); }
            int hit (juce::Point<int> p) const { for (int i = 0; i < (int) fxTypes().size() - 1; ++i) if (cell (i).contains (p)) return i; return -1; }
        };

        // ---- display of the selected effect (schematic: follows the knobs, not the exact DSP) ----
        struct Display : public juce::Component, private Ctx::Listener
        {
            explicit Display (Impl& i) : im (i) { im.ctx.addListener (this); setInterceptsMouseClicks (false, false); }
            ~Display() override { im.ctx.removeListener (this); }
            void paramChanged (int, float) override { repaint(); }
            Impl& im;
            void paint (juce::Graphics& g) override
            {
                auto box = getLocalBounds().toFloat();
                paintInset (g, box, 4.0f);
                int sl = im.sel[im.current]; if (sl < 0) return;
                int gi = im.current * 10 + sl, ty = im.ctx.fxSlotTypes()[gi], b = im.slotBase (gi);
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

                if (ty == 9)   // Filter: response
                {
                    const double fc = 20.0 * std::pow (1000.0, P (0)), res = P (1);
                    auto p = curve ([&] (double t)
                    {
                        double f = 20.0 * std::pow (1000.0, t);
                        double db = 20.0 * std::log10 (juce::jmax (1e-5, std::abs (oscmodel::filterH (juce::jlimit (0, 29, mode), fc, res, f))));
                        return (juce::jlimit (-48.0, 24.0, db) + 48.0) / 72.0;
                    });
                    fill (p, 0.0); stroke (p);
                    g.setColour (col.withAlpha (0.35f)); g.drawVerticalLine ((int) X (std::log (fc / 20.0) / std::log (1000.0)), r.getY(), r.getBottom());
                    g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawHorizontalLine ((int) Y ((0 + 48.0) / 72.0), r.getX(), r.getRight());
                    freqAxis();
                }
                else if (ty == 10)   // EQ: sum of low shelf, peak, high shelf
                {
                    const double gL = -12 + 24 * P (0), gM = -12 + 24 * P (1), fM = 200.0 * std::pow (25.0, P (2)), gH = -12 + 24 * P (3), q = 0.3 * std::pow (4.0 / 0.3, P (4));
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
                else if (ty == 1)   // Distortion: transfer curve
                {
                    const double drive = 1.0 + 11.0 * P (0), outg = 2.0 * P (2);
                    auto shape = [&] (double x)
                    {
                        switch (juce::jlimit (0, 8, mode))
                        {
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
                    label (juce::String (juce::roundToInt (ms)) + " ms" + (pp ? "   PING-PONG" : ""));
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
                    stroke (p); label (juce::String (rate, 2) + " Hz  (shape only)");
                }
                else if (ty == 7)   // Tremolo
                {
                    const double rate = 0.1 * std::pow (200.0, P (0)), depth = P (1);
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
                    fill (p, 0.0); stroke (p); label (juce::String (rate, 1) + " Hz");
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
            }
        };

        // ====================================================================================================================
        Impl (FxPage& o, Ctx& c, SoundMemory& m) : owner (o), ctx (c), mem (m), list (*this), chooser (*this), display (*this)
        {
            for (int g = 0; g < 30; ++g)
            {
                int b = slotBase (g);
                onT[g] = std::make_unique<OnToggle> (ctx, b + 1);
                mixK[g] = makeWidget (ctx, b + 2, true);
                modeS[g] = makeWidget (ctx, b + 3, false);
                for (int k = 0; k < 6; ++k) pK[g][k] = makeWidget (ctx, b + 4 + k, true);
                for (auto* w : { (ParamWidget*) onT[g].get(), mixK[g].get(), modeS[g].get() }) owner.addChildComponent (w);
                for (auto& w : pK[g]) owner.addChildComponent (*w);
                auto drop = [this] (ParamWidget& p) { if (owner.onModDropped) owner.onModDropped (p); };
                mixK[g]->onModDropped = drop; for (auto& w : pK[g]) w->onModDropped = drop;
                pos[g] = g % 10;
                refreshSlot (g);
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
            owner.addAndMakeVisible (list); owner.addChildComponent (chooser); owner.addChildComponent (display);
            addBtn.text = "+ ADD FX"; addBtn.click = [this] { adding = true; layoutCentre(); owner.repaint(); list.repaint(); };
            removeBtn.text = "REMOVE"; removeBtn.click = [this] { removeSelected(); };
            owner.addAndMakeVisible (addBtn); owner.addChildComponent (removeBtn);
            for (int rk = 0; rk < 3; ++rk) { sel[rk] = -1; }
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
            for (int rk = 0; rk < 3; ++rk) autoSelect (rk);
            showRack (0);
        }
        ~Impl() override { ctx.removeListener (this); }

        int slotBase (int g) const { return fxRacks()[(size_t) (g / 10)].id + (g % 10) * 10; }

        // ---- order bookkeeping (same data as before: 10 order parameters per rack) ----
        std::array<int, 10> orderNow (int rk) const
        {
            std::array<int, 10> o {};
            for (int k = 0; k < 10; ++k) o[(size_t) k] = juce::roundToInt (ctx.get (fxRacks()[(size_t) rk].ord + k));
            return o;
        }
        void applyOrders() { for (int rk = 0; rk < 3; ++rk) applyOrder (rk); }
        void applyOrder (int rk)
        {
            auto order = orderNow (rk);
            int p[10]; for (int& x : p) x = -1;
            for (int k = 0; k < 10; ++k) if (order[(size_t) k] >= 0 && order[(size_t) k] < 10 && p[order[(size_t) k]] < 0) p[order[(size_t) k]] = k;
            int spare = 10; for (int sl = 0; sl < 10; ++sl) if (p[sl] < 0) p[sl] = spare++;
            for (int sl = 0; sl < 10; ++sl) pos[rk * 10 + sl] = p[sl];
            list.repaint();
        }
        void commit (int rk, const std::array<int, 10>& order)
        {
            auto cur = orderNow (rk);
            for (int k = 0; k < 10; ++k) if (order[(size_t) k] != cur[(size_t) k]) ctx.set (fxRacks()[(size_t) rk].ord + k, (float) order[(size_t) k]);
            applyOrder (rk);
        }
        std::vector<int> usedSlots (int rk) const
        {
            std::vector<int> v;
            for (int sl = 0; sl < 10; ++sl) if (ctx.fxSlotTypes()[rk * 10 + sl] > 0) v.push_back (sl);
            std::sort (v.begin(), v.end(), [&] (int a, int b) { return pos[rk * 10 + a] < pos[rk * 10 + b]; });
            return v;
        }
        int freeSlot (int rk) const { for (int sl = 0; sl < 10; ++sl) if (ctx.fxSlotTypes()[rk * 10 + sl] == 0) return sl; return -1; }

        // moves an effect by `dir` places among the used ones (swapping the processing positions)
        void moveUsed (int rk, int sl, int dir)
        {
            auto used = usedSlots (rk);
            int idx = (int) (std::find (used.begin(), used.end(), sl) - used.begin());
            int to = juce::jlimit (0, (int) used.size() - 1, idx + dir); if (idx >= (int) used.size() || to == idx) return;
            auto order = orderNow (rk);
            std::vector<int> v (order.begin(), order.end());
            int target = pos[rk * 10 + used[(size_t) to]];
            v.erase (std::find (v.begin(), v.end(), sl)); v.insert (v.begin() + juce::jlimit (0, 9, target), sl);
            std::array<int, 10> n; for (int k = 0; k < 10; ++k) n[(size_t) k] = v[(size_t) k];
            commit (rk, n);
        }

        // ---- selection / add / remove ----
        void select (int rk, int sl) { sel[rk] = sl; adding = false; layoutCentre(); list.repaint(); owner.repaint(); }
        void autoSelect (int rk) { auto u = usedSlots (rk); if (sel[rk] < 0 || ctx.fxSlotTypes()[rk * 10 + sel[rk]] == 0) sel[rk] = u.empty() ? -1 : u.back(); }
        void showRack (int rk) { current = rk; adding = false; autoSelect (rk); updateTabs(); layoutCentre(); list.repaint(); owner.repaint(); }
        void updateTabs()
        {
            const int tabRk[] = { 1, 2, 0 };
            for (int i = 0; i < 3; ++i) { tabs[i]->used = ! usedSlots (tabRk[i]).empty(); tabs[i]->on = tabRk[i] == current; tabs[i]->repaint(); }
        }

        void addEffect (int type)
        {
            int rk = current, sl = freeSlot (rk); if (sl < 0) return;
            auto used = usedSlots (rk);
            std::vector<int> v = used; v.push_back (sl);
            for (int s : std::array<int, 10> (orderNow (rk))) if (std::find (v.begin(), v.end(), s) == v.end()) v.push_back (s);
            std::array<int, 10> n; for (int k = 0; k < 10; ++k) n[(size_t) k] = v[(size_t) k];
            int b = slotBase (rk * 10 + sl);
            ctx.begin (b); ctx.set (b, (float) type); ctx.end (b);
            applyTypeDefaults (rk * 10 + sl, type);
            commit (rk, n);
            sel[rk] = sl; adding = false;
            refreshSlot (rk * 10 + sl); updateTabs(); layoutCentre(); list.repaint(); owner.repaint();
        }
        void removeSelected()
        {
            int rk = current, sl = sel[rk]; if (sl < 0) return;
            int b = slotBase (rk * 10 + sl);
            ctx.begin (b); ctx.set (b, 0.0f); ctx.end (b);
            sel[rk] = -1; autoSelect (rk); updateTabs(); layoutCentre(); list.repaint(); owner.repaint();
        }

        // a new effect starts from its own sensible settings (user changes only)
        void applyTypeDefaults (int g, int type)
        {
            int b = slotBase (g);
            auto& t = fxTypes()[(size_t) juce::jlimit (0, (int) fxTypes().size() - 1, type)];
            ctx.set (b + 1, 1.0f); ctx.set (b + 2, t.mix); ctx.set (b + 3, 0.0f);
            for (size_t k = 0; k < t.params.size(); ++k) ctx.set (b + 4 + (int) k, t.params[k].def);
        }

        // labels / mode list of the widgets of one slot follow its effect type
        void refreshSlot (int g)
        {
            auto& t = fxTypes()[(size_t) juce::jlimit (0, (int) fxTypes().size() - 1, ctx.fxSlotTypes()[g])];
            if (auto* s = dynamic_cast<SelectWidget*> (modeS[g].get())) s->setOptions (t.modes, t.groups);
            for (int k = 0; k < 6; ++k) if (k < (int) t.params.size()) pK[g][k]->setLabelOverride (t.params[(size_t) k].name);
        }

        void paramChanged (int num, float) override
        {
            auto loc = fxLocate (num);
            if (! loc.valid) return;
            if (loc.ord >= 0) { applyOrder (loc.rk); return; }
            if (loc.off == 3 && loc.rk == current) { layoutCentre(); owner.repaint(); }
            if (loc.off == 0)
            {
                refreshSlot (loc.g);
                if (sel[loc.rk] == loc.sl && ctx.fxSlotTypes()[loc.g] == 0) sel[loc.rk] = -1;
                autoSelect (loc.rk); updateTabs();
                if (loc.rk == current) { layoutCentre(); owner.repaint(); }
            }
            list.repaint();
        }

        // ---- centre area ----
        void layoutCentre()
        {
            for (int g = 0; g < 30; ++g)
            {
                onT[g]->setVisible (false); mixK[g]->setVisible (false); modeS[g]->setVisible (false);
                for (auto& w : pK[g]) w->setVisible (false);
            }
            int sl = sel[current];
            bool effectPage = ! adding && sl >= 0 && ctx.fxSlotTypes()[current * 10 + sl] > 0;
            chooser.setVisible (! effectPage); display.setVisible (effectPage); removeBtn.setVisible (effectPage);
            loadIr.setVisible (false); clearIr.setVisible (false); irRect = {};
            chooser.setBounds (centre);
            addBtn.setBounds (addRect);
            if (! effectPage) return;
            int g = current * 10 + sl, ty = ctx.fxSlotTypes()[g];
            auto& t = fxTypes()[(size_t) ty];
            auto c = centre;
            auto head = c.removeFromTop (34);
            removeBtn.setBounds (head.removeFromRight (84).reduced (0, 4));
            head.removeFromRight (8);
            onT[g]->setBounds (head.removeFromRight (96).reduced (0, 3)); onT[g]->setVisible (true);
            head.removeFromRight (8);
            titleRect = head.removeFromLeft (220);
            if (t.modes.size() > 0) { modeS[g]->setBounds (head.removeFromLeft (150).reduced (0, 2)); modeS[g]->setVisible (true); }
            if (ty == 12 && juce::roundToInt (ctx.get (slotBase (g) + 3)) == 8)
            {
                head.removeFromLeft (10);
                loadIr.setBounds (head.removeFromLeft (84).reduced (0, 4)); loadIr.setVisible (true);
                head.removeFromLeft (6);
                clearIr.setBounds (head.removeFromLeft (64).reduced (0, 4)); clearIr.setVisible (true);
                head.removeFromLeft (8);
                irRect = head;
            }
            auto knobs = c.removeFromBottom (84);
            c.removeFromBottom (6);
            display.setBounds (c);
            int n = 1 + (int) t.params.size(), colW = juce::jmin (120, knobs.getWidth() / juce::jmax (1, n));
            int x0 = knobs.getX() + (knobs.getWidth() - colW * n) / 2;
            auto put = [&] (ParamWidget& w, int i) { w.setBounds (x0 + i * colW + (colW - 70) / 2, knobs.getY() + 12, 70, 62); w.setVisible (true); };
            put (*mixK[g], 0);
            for (int k = 0; k < (int) t.params.size(); ++k) put (*pK[g][k], k + 1);
        }

        FxPage& owner; Ctx& ctx; SoundMemory& mem;
        FxButton loadIr, clearIr; juce::Rectangle<int> irRect; std::shared_ptr<juce::FileChooser> chooser2;
        ListComp list; Chooser chooser; Display display; FxButton addBtn, removeBtn;
        std::unique_ptr<OnToggle> onT[30]; std::unique_ptr<ParamWidget> mixK[30], modeS[30], pK[30][6];
        juce::OwnedArray<DotTab> tabs; juce::OwnedArray<ParamWidget> outs;
        juce::Rectangle<int> mainCard, outCard, listRect, addRect, centre, titleRect;
        int current = 0, sel[3] = { -1, -1, -1 }, pos[30] = {}; bool adding = false;
    };

    FxPage::FxPage (Ctx& c, SoundMemory& m) : impl (new Impl (*this, c, m)) {}
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
        m.removeFromTop (8);
        auto left = m.removeFromLeft (kLeftW); m.removeFromLeft (14);
        impl->addRect = left.removeFromBottom (28); left.removeFromBottom (6);
        impl->listRect = left;
        impl->list.setBounds (impl->listRect.withHeight (juce::jmin (impl->listRect.getHeight(), 10 * kItemH)));
        impl->centre = m;
        impl->layoutCentre();
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
        // panel behind the list and the centre area
        paintInset (g, impl->listRect.toFloat().expanded (4, 4).withTrimmedBottom (-34), 4.0f);
        g.setColour (dim); g.setFont (font (8.0f, true).withExtraKerningFactor (0.2f));
        // effect page title
        int sl = impl->sel[impl->current];
        if (! impl->adding && sl >= 0 && impl->ctx.fxSlotTypes()[impl->current * 10 + sl] > 0)
        {
            int ty = impl->ctx.fxSlotTypes()[impl->current * 10 + sl];
            g.setColour (fxColour (ty)); g.fillRect (impl->titleRect.getX(), impl->titleRect.getY() + 6, 4, impl->titleRect.getHeight() - 12);
            g.setColour (ink); g.setFont (impact (19.0f));
            g.drawText (fxTypes()[(size_t) ty].name.toUpperCase(), impl->titleRect.withTrimmedLeft (14), juce::Justification::centredLeft, true);
            if (! impl->irRect.isEmpty())
            {
                auto* s = impl->mem.get (SoundMemory::ImpulseResponse, impl->current);
                g.setColour (s ? ink : dim); g.setFont (font (9.5f, true));
                g.drawText (s ? s->name : juce::String ("NO FILE LOADED"), impl->irRect, juce::Justification::centredLeft, true);
            }
        }
    }
}
