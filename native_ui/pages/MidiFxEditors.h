// Editors of the MIDI FX page for the arpeggiator modes 9 Plinko, 10 Bounce and 11 Cellular (DSP: tools/mod/build_plinko.py, parameters 6300.., 6320.., 6340..).
// Each editor shows the parameters as knobs and a picture of what the mode does: the Plinko board with the balls the DSP reports, the arcs of the bouncing ball,
// the generations of the cellular automaton.
#pragma once
#include "ModUi.h"
#include "PresetBrowserUi.h"
#include "../NjoPlantPresets.h"
#include <array>
#include <functional>
#include <cmath>
#include <vector>

namespace njo
{
    using namespace theme;

    namespace midifx
    {
        inline int scaleMask (int sc)
        {
            static const int m[12] = { 4095, 2741, 1453, 1709, 1451, 2773, 1717, 2477, 661, 1193, 1257, 1365 };
            return m[juce::jlimit (0, 11, sc)];
        }
        // semitone of scale degree idx inside range (as the DSP: sqScaleNote)
        inline int scaleNote (int mask, int range, int idx)
        {
            int n = 0, last = 0;
            for (int s = 0; s < range; ++s) if ((mask >> (s % 12)) & 1) { last = s; if (n == idx) return s; ++n; }
            return last;
        }
        inline int scaleCount (int mask, int range) { int n = 0; for (int s = 0; s < range; ++s) if ((mask >> (s % 12)) & 1) ++n; return std::max (n, 1); }

        // shared base: the widgets of one mode (ids base + k), selects on a row of their own, the rest as knobs; the picture gets the left part
        struct Base : juce::Component, Ctx::Listener, protected juce::Timer
        {
            Ctx& ctx; int base, count; std::vector<int> selects; juce::OwnedArray<ParamWidget> w; juce::Rectangle<float> pic;
            Base (Ctx& c, int b, int n, std::vector<int> sel) : ctx (c), base (b), count (n), selects (std::move (sel))
            {
                ctx.addListener (this);
                for (int k = 0; k < n; ++k)
                {
                    const bool s = std::find (selects.begin(), selects.end(), k) != selects.end();
                    auto* x = w.add (makeWidget (c, b + k, ! s).release()); if (! s) x->setLook (true); addAndMakeVisible (x);
                }
            }
            ~Base() override { ctx.removeListener (this); }
            float p (int k) const { return ctx.get (base + k); }
            void paramChanged (int n, float) override { if (n >= base && n < base + count) repaint(); }
            void visibilityChanged() override { if (isVisible()) startTimerHz (30); else stopTimer(); }
            void timerCallback() override { if (needsRepaint()) repaint(); }
            virtual bool needsRepaint() { return false; }
            void resized() override
            {
                auto r = getLocalBounds().reduced (6, 4);
                auto left = r.removeFromLeft (r.getWidth() * 11 / 20); r.removeFromLeft (6); pic = left.toFloat().reduced (2.0f);
                auto top = r.removeFromTop (48); const int ns = (int) selects.size();
                for (int i = 0; i < ns; ++i) w[(size_t) selects[(size_t) i]]->setBounds (top.removeFromLeft (r.getWidth() / juce::jmax (1, ns)).reduced (3, 0));
                std::vector<int> kn; for (int k = 0; k < count; ++k) if (std::find (selects.begin(), selects.end(), k) == selects.end()) kn.push_back (k);
                const int cols = 4, rowsN = ((int) kn.size() + cols - 1) / cols, rh = juce::jmin (92, r.getHeight() / juce::jmax (1, rowsN));
                for (size_t i = 0; i < kn.size(); ++i)
                    w[(size_t) kn[i]]->setBounds (r.getX() + (int) (i % cols) * (r.getWidth() / cols), r.getY() + (int) (i / cols) * rh, r.getWidth() / cols, rh);
            }
            void paintBack (juce::Graphics& g, const juce::String& hint)
            {
                g.setColour (juce::Colour (0xff0c0d0e)); g.fillRoundedRectangle (pic, 4.0f);
                g.setColour (dim.withAlpha (0.8f)); g.setFont (font (8.5f));
                g.drawText (hint, pic.toNearestInt().withTrimmedTop (pic.getHeight() > 20 ? (int) pic.getHeight() - 16 : 0).reduced (8, 0), juce::Justification::centredLeft);
            }
        };

        // ---- Plinko: the board, the distribution of the bins, the falling balls (seqPos events of the DSP) ----
        struct Plinko : Base
        {
            Backend& be;
            explicit Plinko (Ctx& c) : Base (c, 6300, 15, { 1, 10 }), be (c.be) {}
            bool needsRepaint() override { const auto now = juce::Time::getMillisecondCounter(); for (auto& b : be.plinkoBalls) if (now - b.ms < 900) return true; return false; }
            // probability of every bin: binomial with the bias, shifted by Drop X with reflection at the walls
            std::vector<float> dist (int rows) const
            {
                const float pr = juce::jlimit (0.02f, 0.98f, 0.5f + p (5) / 200.0f); std::vector<float> d (rows + 1, 0.0f); d[0] = 1.0f;
                for (int r = 0; r < rows; ++r) { std::vector<float> n (rows + 1, 0.0f); for (int k = 0; k <= r; ++k) { n[(size_t) k] += d[(size_t) k] * (1.0f - pr); n[(size_t) k + 1] += d[(size_t) k] * pr; } d = n; }
                const int drop = (int) std::floor (p (4) / 100.0f * (float) rows * 0.5f + 0.5f); std::vector<float> o (rows + 1, 0.0f);
                for (int k = 0; k <= rows; ++k) { int b = k + drop; if (b < 0) b = -b; if (b > rows) b = 2 * rows - b; o[(size_t) juce::jlimit (0, rows, b)] += d[(size_t) k]; }
                return o;
            }
            void paint (juce::Graphics& g) override
            {
                paintBack (g, "Plinko: every row sends the ball left or right (Bias, Momentum); the bin it lands in is a scale degree. Drop X moves the drop point. The root is the last key pressed.");
                const int rows = juce::jlimit (2, 12, juce::roundToInt (p (0))); auto r = pic.reduced (10.0f, 10.0f); r.removeFromBottom (18.0f);
                const float binH = r.getHeight() * 0.22f, top = r.getY() + 6.0f, rowH = (r.getHeight() - binH - 10.0f) / (float) rows;
                const float dx = juce::jmin (r.getWidth() / (float) (rows + 1), rowH * 1.3f), cx = r.getCentreX();
                auto X = [&] (float k, float rowsNow) { return cx + (k - rowsNow * 0.5f) * dx; };
                g.setColour (juce::Colours::white.withAlpha (0.55f));
                for (int rr = 0; rr < rows; ++rr) for (int k = 0; k <= rr; ++k) g.fillEllipse (X ((float) k, (float) rr) - 2.5f, top + (float) rr * rowH - 2.5f, 5.0f, 5.0f);
                // bins: the distribution and the semitone of each bin
                const auto d = dist (rows); float mx = 0.0001f; for (float v : d) mx = juce::jmax (mx, v);
                const int mask = scaleMask (juce::roundToInt (p (1))), range = juce::jlimit (12, 48, juce::roundToInt (p (2))), n = scaleCount (mask, range), shift = juce::roundToInt (p (3));
                const float by = top + (float) rows * rowH + 6.0f;
                for (int b = 0; b <= rows; ++b)
                {
                    const float bx = X ((float) b, (float) rows), bh = binH * d[(size_t) b] / mx;
                    g.setColour (red.withAlpha (0.35f + 0.5f * d[(size_t) b] / mx)); g.fillRect (bx - dx * 0.4f, by + binH - bh, dx * 0.8f, bh);
                    g.setColour (dim); g.setFont (mono (8.0f, false));
                    const int idx = (b * (n - 1) + rows / 2) / juce::jmax (1, rows);
                    g.drawText (juce::String (shift + scaleNote (mask, range, idx)), (int) (bx - dx * 0.5f), (int) (by + binH) + 2, (int) dx, 12, juce::Justification::centred);
                }
                // falling balls
                const auto now = juce::Time::getMillisecondCounter();
                for (auto& b : be.plinkoBalls)
                {
                    const float age = (float) (now - b.ms) / 700.0f; if (age < 0.0f || age > 1.15f) continue;
                    const int rw = juce::jlimit (2, 12, b.rows); if (rw != rows) continue;
                    int pos = 0; for (int i = 0; i < rw; ++i) pos += (b.path >> i) & 1;
                    const float f = juce::jmin (age, 1.0f) * (float) rw; const int t = juce::jmin (rw, (int) f); const float fr = f - (float) t;
                    int k0 = 0; for (int i = 0; i < t; ++i) k0 += (b.path >> i) & 1;
                    const int k1 = k0 + (t < rw ? ((b.path >> t) & 1) : 0); const float off = (float) (b.bin - pos);
                    const float kx = (float) k0 + ((float) k1 - (float) k0) * fr + off * juce::jmin (1.0f, f / (float) rw);
                    const float xx = cx + (kx - f * 0.5f) * dx, yy = top + f * rowH - std::abs (std::sin (fr * juce::MathConstants<float>::pi)) * rowH * 0.25f;
                    g.setColour (juce::Colour (0xffffd24a).withAlpha (age > 1.0f ? 1.0f - (age - 1.0f) / 0.15f : 1.0f)); g.fillEllipse (xx - 4.0f, yy - 4.0f, 8.0f, 8.0f);
                }
            }
        };

        // ---- Bounce: arcs of a ball coming to rest ----
        struct Bounce : Base
        {
            explicit Bounce (Ctx& c) : Base (c, 6320, 14, { 4, 10, 13 }) {}
            void paint (juce::Graphics& g) override
            {
                paintBack (g, "Bounce: the gaps shrink by Decay like a ball coming to rest, the pitch walks through the scale by Pitch Step, then Pause steps and again.");
                auto r = pic.reduced (12.0f, 12.0f); r.removeFromBottom (18.0f);
                const int nb = juce::jlimit (2, 16, juce::roundToInt (p (2))); const float g0 = p (0) / 100.0f, dec = p (1) / 100.0f, vd = p (7) / 100.0f, pause = (float) juce::roundToInt (p (8));
                std::vector<float> gap (nb); float tot = 0.0f, gp = g0; for (int i = 0; i < nb; ++i) { gap[(size_t) i] = gp; tot += gp; gp *= dec; }
                const float cyc = std::ceil (tot) + pause, sx = r.getWidth() / juce::jmax (0.5f, cyc);
                g.setColour (juce::Colours::white.withAlpha (0.12f));
                for (int s = 0; s <= (int) cyc; ++s) g.drawVerticalLine ((int) (r.getX() + (float) s * sx), r.getY(), r.getBottom());
                float t = 0.0f, vel = p (11) / 127.0f; const int dir = juce::roundToInt (p (13)), stp = juce::roundToInt (p (3));
                const int mask = scaleMask (juce::roundToInt (p (4))), range = juce::jlimit (12, 48, juce::roundToInt (p (5))), n = scaleCount (mask, range);
                int idx = dir == 1 ? n - 1 : 0, sgn = dir == 1 ? -1 : 1;
                for (int i = 0; i < nb; ++i)
                {
                    const float x0 = r.getX() + t * sx, x1 = r.getX() + (t + gap[(size_t) i]) * sx, h = r.getHeight() * 0.9f * juce::jmin (1.0f, gap[(size_t) i] / juce::jmax (0.1f, g0));
                    juce::Path a; a.startNewSubPath (x0, r.getBottom());
                    for (int q = 1; q <= 16; ++q) { const float u = (float) q / 16.0f; a.lineTo (x0 + (x1 - x0) * u, r.getBottom() - 4.0f * u * (1.0f - u) * h); }
                    g.setColour (red.withAlpha (0.35f + 0.6f * juce::jlimit (0.0f, 1.0f, vel))); g.strokePath (a, juce::PathStrokeType (1.6f));
                    const float ny = r.getBottom() - 4.0f - (r.getHeight() - 10.0f) * (float) idx / (float) juce::jmax (1, n - 1);   // pitch dot
                    g.setColour (juce::Colour (0xffffd24a)); g.fillEllipse (x0 - 3.0f, ny - 3.0f, 6.0f, 6.0f);
                    t += gap[(size_t) i]; vel *= vd; idx += stp * sgn;
                    if (idx < 0 || idx > n - 1) { if (dir == 2) { sgn = -sgn; idx = juce::jlimit (0, n - 1, idx < 0 ? -idx : 2 * (n - 1) - idx); } else idx = ((idx % n) + n) % n; }
                }
            }
        };

        // ---- Cellular: the generations of the automaton (a preview without mutation) ----
        struct Cellular : Base
        {
            explicit Cellular (Ctx& c) : Base (c, 6340, 12, { 2, 11 }) {}
            void paint (juce::Graphics& g) override
            {
                paintBack (g, "Cellular: a row of cells follows a Wolfram rule; every generation the living cells play the scale degree of their position (Max Notes limits the chord).");
                const int w2 = juce::jlimit (4, 16, juce::roundToInt (p (1))), rule = juce::jlimit (0, 255, juce::roundToInt (p (0))), all = (1 << w2) - 1, maxN = juce::jlimit (1, 8, juce::roundToInt (p (8)));
                auto r = pic.reduced (12.0f, 12.0f); r.removeFromBottom (18.0f);
                auto strip = r.removeFromBottom (26.0f); r.removeFromBottom (6.0f);   // the eight neighbourhoods of the rule
                const float cs = juce::jmin (r.getWidth() / (float) w2, r.getHeight() / 16.0f); const float ox = r.getCentreX() - cs * (float) w2 * 0.5f;
                int s = 1 << (w2 / 2);
                for (int gen = 0; gen < 16; ++gen)
                {
                    int played = 0;
                    for (int c = 0; c < w2; ++c)
                    {
                        const bool on = ((s >> c) & 1) != 0; const bool plays = on && played < maxN; if (plays) ++played;
                        g.setColour (on ? (plays ? red : red.withAlpha (0.35f)) : juce::Colours::white.withAlpha (0.06f));
                        g.fillRect (ox + (float) c * cs + 0.5f, r.getY() + (float) gen * cs + 0.5f, cs - 1.0f, cs - 1.0f);
                    }
                    int nx = 0; for (int c = 0; c < w2; ++c) { const int l = (s >> ((c + w2 - 1) % w2)) & 1, m = (s >> c) & 1, rr = (s >> ((c + 1) % w2)) & 1; nx |= ((rule >> (l * 4 + m * 2 + rr)) & 1) << c; }
                    s = nx & all; if (s == 0) s = 1 << (w2 / 2);
                }
                const float bw = strip.getWidth() / 8.0f;
                for (int q = 7; q >= 0; --q)
                {
                    const float x0 = strip.getX() + (float) (7 - q) * bw + bw * 0.5f - 13.0f;
                    for (int i = 0; i < 3; ++i) { g.setColour (((q >> (2 - i)) & 1) ? juce::Colours::white.withAlpha (0.8f) : juce::Colours::white.withAlpha (0.12f)); g.fillRect (x0 + (float) i * 8.0f, strip.getY(), 7.0f, 7.0f); }
                    g.setColour (((rule >> q) & 1) ? red : juce::Colours::white.withAlpha (0.12f)); g.fillRect (x0 + 8.0f, strip.getY() + 10.0f, 7.0f, 7.0f);
                }
            }
        };

        // ---- Plinko board (Arp Mode 12): draw pegs and lines, balls fall through them and every hit plays a note (DSP: build_plinko2.py, obstacles 6400 + 6 * e + j) ----
        struct Board : Base
        {
            Backend& be; int tool = 1; juce::OwnedArray<juce::Component> chips; juce::StringArray chipNames;
            juce::Rectangle<float> sq; juce::Point<float> a, b; bool drawing = false;
            struct Chip : juce::Component
            {
                juce::String text; bool on = false; std::function<void()> click;
                void paint (juce::Graphics& g) override { auto r = getLocalBounds().toFloat().reduced (0.5f); paintButton (g, r, on, false, false, 3.0f); g.setColour (on ? juce::Colours::white : ink); g.setFont (font (9.0f, true)); g.drawText (text, getLocalBounds(), juce::Justification::centred); }
                void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
            };
            static constexpr int NE = 48;
            // tools: 0 erase, 1 peg, 2 line, 3 spring, 4 shimmer, 5 chorus, 6 gate
            explicit Board (Ctx& c) : Base (c, 6360, 15, { 5, 10 }), be (c.be)
            {
                static const char* tn[7] = { "ERASE", "PEG", "LINE", "SPRING", "SHIMMER", "CHORUS", "GATE" };
                for (int i = 0; i < 7; ++i) { auto* ch = new Chip(); ch->text = tn[i]; ch->click = [this, i] { tool = i; refreshChips(); }; chips.add (ch); addAndMakeVisible (ch); }
                auto* cl = new Chip(); cl->text = "CLEAR"; cl->click = [this] { setBoard ({}); }; chips.add (cl); addAndMakeVisible (cl);
                auto* pr = new Chip(); pr->text = "PRESETS"; pr->click = [this] { presets(); }; chips.add (pr); addAndMakeVisible (pr);
                refreshChips();
            }
            void refreshChips() { for (int i = 0; i < 7; ++i) static_cast<Chip*> (chips[i])->on = (i == tool); for (auto* c : chips) c->repaint(); }
            int type (int e) const { return juce::roundToInt (ctx.get (6400 + 6 * e)); }
            float val (int e, int j) const { return ctx.get (6400 + 6 * e + j); }
            void put (int e, int ty, float x1, float y1, float x2, float y2, int kind)
            {
                const float v[6] = { (float) ty, x1, y1, x2, y2, (float) kind };
                for (int j = 0; j < 6; ++j) { const int id = 6400 + 6 * e + j; ctx.begin (id); ctx.set (id, v[j]); ctx.end (id); }
            }
            // an obstacle: { type, x1, y1, x2, y2, kind }
            using Ob = std::array<float, 6>;
            void setBoard (const std::vector<Ob>& o) { for (int e = 0; e < NE; ++e) { if (e < (int) o.size()) put (e, (int) o[(size_t) e][0], o[(size_t) e][1], o[(size_t) e][2], o[(size_t) e][3], o[(size_t) e][4], (int) o[(size_t) e][5]); else if (type (e) != 0) put (e, 0, 0, 0, 0, 0, 0); } repaint(); }
            void presets()
            {
                juce::PopupMenu m; const char* n[] = { "Pyramid of pegs", "Comb", "Zigzag ramps", "Funnel and pegs", "Staircase", "Random pegs", "Spring bumpers", "Wind chimes" };
                for (int i = 0; i < 8; ++i) m.addItem (i + 1, n[i]);
                juce::Component::SafePointer<juce::Component> sp (this);
                m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (chips.getLast()), [this, sp] (int r) { if (sp != nullptr && r > 0) setBoard (preset (r - 1)); });
            }
            static std::vector<Ob> preset (int i)
            {
                std::vector<Ob> o; auto peg = [&] (float x, float y, int k = 0) { o.push_back ({ 1, x, y, x, y, (float) k }); }; auto line = [&] (float x1, float y1, float x2, float y2, int k = 0) { o.push_back ({ 2, x1, y1, x2, y2, (float) k }); };
                if (i == 0) { for (int r = 0; r < 8; ++r) for (int c = 0; c <= r && o.size() < 44; ++c) peg (0.5f + ((float) c - (float) r * 0.5f) * 0.11f, 0.15f + (float) r * 0.09f); }
                else if (i == 1) { for (int c = 0; c < 12; ++c) line (0.08f + (float) c * 0.075f, 0.45f, 0.08f + (float) c * 0.075f, 0.62f + 0.02f * (float) (c % 3)); line (0.0f, 0.3f, 1.0f, 0.36f); }
                else if (i == 2) { for (int r = 0; r < 5; ++r) { const bool l = r % 2 == 0; line (l ? 0.0f : 1.0f, 0.15f + (float) r * 0.17f, l ? 0.78f : 0.22f, 0.22f + (float) r * 0.17f); } }
                else if (i == 3) { line (0.0f, 0.2f, 0.42f, 0.42f); line (1.0f, 0.2f, 0.58f, 0.42f); for (int r = 0; r < 4; ++r) for (int c = 0; c < 5; ++c) peg (0.2f + (float) c * 0.15f + (r % 2) * 0.075f, 0.55f + (float) r * 0.1f); }
                else if (i == 4) { for (int k = 0; k < 8; ++k) line (0.05f + (float) k * 0.1f, 0.2f + (float) k * 0.09f, 0.17f + (float) k * 0.1f, 0.24f + (float) k * 0.09f); }
                else if (i == 5) { juce::Random rn (7); for (int k = 0; k < 36; ++k) peg (0.05f + rn.nextFloat() * 0.9f, 0.1f + rn.nextFloat() * 0.8f); }
                else if (i == 6) { for (int r = 0; r < 4; ++r) for (int c = 0; c < 4; ++c) peg (0.15f + (float) c * 0.23f + (r % 2) * 0.1f, 0.2f + (float) r * 0.17f, 1); }
                else { for (int k = 0; k < 10; ++k) line (0.08f + (float) k * 0.093f, 0.3f + 0.1f * (float) (k % 2), 0.08f + (float) k * 0.093f, 0.5f + 0.15f * (float) (k % 3), k % 3 == 0 ? 2 : k % 3 == 1 ? 3 : 0); }
                return o;
            }
            bool needsRepaint() override
            {
                const auto now = juce::Time::getMillisecondCounter();
                for (auto& b : be.boardBalls) if (now - b.ms < 400) return true;
                for (auto t : be.boardHitMs) if (t != 0 && now - t < 400) return true;
                return false;
            }
            void resized() override
            {
                Base::resized();
                auto r = pic.toNearestInt().reduced (2); auto tb = r.removeFromTop (22); r.removeFromTop (4);
                const int n = chips.size(), cw = tb.getWidth() / n; for (auto* c : chips) c->setBounds (tb.removeFromLeft (cw).reduced (1, 0));
                const float side = (float) juce::jmin (r.getWidth(), r.getHeight() - 16); sq = juce::Rectangle<float> (side, side).withCentre ({ (float) r.getCentreX(), (float) r.getY() + side * 0.5f });
            }
            juce::Point<float> toBoard (juce::Point<float> p) const { return { juce::jlimit (0.0f, 1.0f, (p.x - sq.getX()) / sq.getWidth()), juce::jlimit (0.0f, 1.0f, (p.y - sq.getY()) / sq.getHeight()) }; }
            int freeSlot() const { for (int e = 0; e < NE; ++e) if (type (e) == 0) return e; return -1; }
            void eraseAt (juce::Point<float> q)
            {
                int best = -1; float bd = 0.04f;
                for (int e = 0; e < NE; ++e)
                {
                    const int ty = type (e); if (ty == 0) continue;
                    const float x1 = val (e, 1), y1 = val (e, 2), x2 = ty == 1 ? x1 : val (e, 3), y2 = ty == 1 ? y1 : val (e, 4), ex = x2 - x1, ey = y2 - y1, l2 = ex * ex + ey * ey;
                    const float t = l2 > 1.0e-6f ? juce::jlimit (0.0f, 1.0f, ((q.x - x1) * ex + (q.y - y1) * ey) / l2) : 0.0f, d = std::hypot (q.x - (x1 + t * ex), q.y - (y1 + t * ey));
                    if (d < bd) { bd = d; best = e; }
                }
                if (best >= 0) put (best, 0, 0, 0, 0, 0, 0);
            }
            void mouseDown (const juce::MouseEvent& e) override
            {
                if (! sq.contains (e.position)) return;
                const auto q = toBoard (e.position);
                if (e.mods.isRightButtonDown() || tool == 0) { eraseAt (q); repaint(); return; }
                a = b = q; drawing = true; repaint();
            }
            void mouseDrag (const juce::MouseEvent& e) override
            {
                if (tool == 0 || e.mods.isRightButtonDown()) { if (sq.contains (e.position)) { eraseAt (toBoard (e.position)); repaint(); } return; }
                if (drawing) { b = toBoard (e.position); repaint(); }
            }
            void mouseUp (const juce::MouseEvent&) override
            {
                if (! drawing) return; drawing = false;
                const int slot = freeSlot(); if (slot < 0) { repaint(); return; }
                const int kind = tool >= 3 ? tool - 2 : 0;   // spring 1, shimmer 2, chorus 3, gate 4
                const bool asPeg = tool == 1 || std::hypot (b.x - a.x, b.y - a.y) < 0.03f;
                if (asPeg) put (slot, 1, a.x, a.y, a.x, a.y, kind); else put (slot, 2, a.x, a.y, b.x, b.y, kind);
                repaint();
            }
            static juce::Colour kindColour (int k) { static const juce::uint32 c[5] = { 0xffd8dce2, 0xff6fe08a, 0xff6fd0ff, 0xffe070ff, 0xffffa040 }; return juce::Colour (c[juce::jlimit (0, 4, k)]); }
            void paint (juce::Graphics& g) override
            {
                paintBack (g, "Plinko: draw pegs and lines (tool row above), balls fall through the board and every hit plays a note: the x position is the scale degree. Right mouse button erases.");
                g.setColour (juce::Colour (0xff15171a)); g.fillRect (sq); g.setColour (juce::Colours::white.withAlpha (0.08f)); g.drawRect (sq, 1.0f);
                for (int i = 1; i < 8; ++i) { g.drawVerticalLine ((int) (sq.getX() + sq.getWidth() * (float) i / 8.0f), sq.getY(), sq.getBottom()); g.drawHorizontalLine ((int) (sq.getY() + sq.getHeight() * (float) i / 8.0f), sq.getX(), sq.getRight()); }
                auto P = [&] (float x, float y) { return juce::Point<float> (sq.getX() + x * sq.getWidth(), sq.getY() + y * sq.getHeight()); };
                const auto now = juce::Time::getMillisecondCounter();
                // drop point and spread
                const float dx = p (12) / 100.0f, sp = p (13) / 100.0f * 0.5f; g.setColour (red.withAlpha (0.25f)); g.fillRect (P (juce::jmax (0.0f, dx - sp * 0.5f), 0.0f).x, sq.getY(), sq.getWidth() * juce::jmin (1.0f, sp), 6.0f);
                g.setColour (red); g.fillRect (P (dx, 0.0f).x - 1.0f, sq.getY(), 2.0f, 10.0f);
                for (int e = 0; e < NE; ++e)
                {
                    const int ty = type (e); if (ty == 0) continue;
                    const int kind = juce::roundToInt (val (e, 5)); const float flash = be.boardHitMs[e] != 0 ? juce::jlimit (0.0f, 1.0f, 1.0f - (float) (now - be.boardHitMs[e]) / 300.0f) : 0.0f;
                    auto col = kindColour (kind).interpolatedWith (juce::Colours::white, flash);
                    const auto p1 = P (val (e, 1), val (e, 2));
                    if (ty == 1) { g.setColour (col.withAlpha (0.35f * flash)); g.fillEllipse (p1.x - 12.0f, p1.y - 12.0f, 24.0f, 24.0f); g.setColour (col); g.fillEllipse (p1.x - 4.5f, p1.y - 4.5f, 9.0f, 9.0f); }
                    else { const auto p2 = P (val (e, 3), val (e, 4)); g.setColour (col.withAlpha (0.3f * flash)); g.drawLine (p1.x, p1.y, p2.x, p2.y, 8.0f); g.setColour (col); g.drawLine (p1.x, p1.y, p2.x, p2.y, 2.5f); }
                }
                if (drawing) { g.setColour (kindColour (tool >= 3 ? tool - 2 : 0).withAlpha (0.6f)); const auto p1 = P (a.x, a.y), p2 = P (b.x, b.y); if (tool == 1) g.fillEllipse (p1.x - 4.5f, p1.y - 4.5f, 9.0f, 9.0f); else g.drawLine (p1.x, p1.y, p2.x, p2.y, 2.0f); }
                const float rr = p (14) / 1000.0f * sq.getWidth();
                for (auto& bl : be.boardBalls) { if (now - bl.ms > 150) continue; const auto c = P (bl.x, bl.y); g.setColour (juce::Colour (0xffffd24a)); g.fillEllipse (c.x - rr, c.y - rr, rr * 2.0f, rr * 2.0f); }
            }
        };

        // small toggle / action button of the toolbar rows
        struct FxChip : juce::Component
        {
            juce::String text; bool on = false; juce::Colour tint = juce::Colours::transparentBlack; std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f); paintButton (g, r, on, false, false, 3.0f);
                if (tint.getAlpha() > 0) { g.setColour (tint); g.fillEllipse (r.getX() + 5.0f, r.getCentreY() - 3.0f, 6.0f, 6.0f); }
                g.setColour (on ? juce::Colours::white : ink); g.setFont (font (9.0f, true)); g.drawText (text, getLocalBounds().withTrimmedLeft (tint.getAlpha() > 0 ? 8 : 0), juce::Justification::centred);
            }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };

        // ---- Hanenbow (Arp Mode 13): tadpoles are launched from a leaf at the bottom (Spawn X, Aim) onto the leaves of a plant; the leaves are fixed to the stem and only turn (DSP: build_hanenbow.py, parameters 6700.., leaves 6720 + 5 * l + j) ----
        struct Hanenbow : Base
        {
            static constexpr float AR = 1.3f;   // the picture is wider than tall (as in the toy); world x runs 0..AR, y 0..1 (like the DSP)
            Backend& be; juce::Rectangle<float> sq; int sel = -1; int launch = 0; juce::Point<float> grab; juce::OwnedArray<FxChip> chips; juce::Point<float> prevB[8];
            static int lf (int l, int j) { return 6720 + 5 * l + j; }
            float lv (int l, int j) const { return ctx.get (lf (l, j)); }
            void setP (int id, float v) { ctx.begin (id); ctx.set (id, v); ctx.end (id); }
            void putLeaf (int l, float on, float side, float y, float a, float n) { const float v[5] = { on, side, y, a, n }; for (int j = 0; j < 5; ++j) setP (lf (l, j), v[(size_t) j]); }
            static juce::Colour stateColour (int s) { static const juce::uint32 c[4] = { 0xff3fe03a, 0xffe8e84a, 0xffffa040, 0xffff7aa8 }; return juce::Colour (c[s & 3]); }
            // a leaf like in the toy: round at the stem, a pointed tip, the upper half light and the lower half dark, a grey vein between them
            static void drawLeaf (juce::Graphics& g, juce::Point<float> p1, juce::Point<float> p2, juce::Colour light, juce::Colour dark, float alpha)
            {
                const float L = std::hypot (p2.x - p1.x, p2.y - p1.y); if (L < 1.0f) return;
                const juce::Point<float> d ((p2.x - p1.x) / L, (p2.y - p1.y) / L); juce::Point<float> n (-d.y, d.x); if (n.y > 0) n = { -n.x, -n.y };   // n: to the upper side
                auto at = [&] (float a, float b) { return juce::Point<float> (p1.x + d.x * a * L + n.x * b * L, p1.y + d.y * a * L + n.y * b * L); };
                juce::Path whole, upper;
                upper.startNewSubPath (p1); upper.cubicTo (at (0.08f, 0.27f), at (0.58f, 0.24f), p2); upper.closeSubPath();
                whole.startNewSubPath (p1); whole.cubicTo (at (0.08f, 0.27f), at (0.58f, 0.24f), p2); whole.cubicTo (at (0.58f, -0.20f), at (0.08f, -0.22f), p1); whole.closeSubPath();
                g.setColour (dark.withAlpha (alpha)); g.fillPath (whole);
                const auto m = at (0.4f, 0.15f); g.setGradientFill (juce::ColourGradient (light.withAlpha (alpha), m.x, m.y, light.interpolatedWith (dark, 0.55f).withAlpha (alpha), p1.x, p1.y, true)); g.fillPath (upper);
                g.setColour (juce::Colour (0xff86948a).withAlpha (alpha)); g.drawLine (p1.x, p1.y, p2.x, p2.y, 2.0f);
            }
            explicit Hanenbow (Ctx& c) : Base (c, 6700, 19, { 5, 10 }), be (c.be)
            {
                auto add = [this] (const char* t, std::function<void()> f) { auto* ch = new FxChip(); ch->text = t; ch->click = std::move (f); chips.add (ch); addAndMakeVisible (ch); };
                add ("CLEAR", [this] { for (int l = 0; l < 8; ++l) setP (lf (l, 0), 0.0f); repaint(); });
                add ("PLANT", [this] { setDefault(); });
                add ("RANDOM", [this] { setRandom(); });
                add ("PRESETS", [this] { presets(); });
            }
            void applyPlant (const njo::plants::Plant& pl) { for (auto& e : njo::plants::values (pl)) setP (e.first, e.second); repaint(); }
            void setDefault() { applyPlant (njo::plants::all()[0]); }   // a plant as in the toy: three pairs of leaves, a fourth pair off; the launch leaf at the bottom left
            // the preset browser: the factory plants and the user plants (<root>/PlantPresets/*.nplant: all Hanenbow parameters and the 8 leaves)
            void presets()
            {
                njo::pbrowse::ParamSourceSpec sp; sp.key = "hnb"; sp.title = "Hanenbow plants"; sp.subdir = "PlantPresets"; sp.ext = "nplant"; sp.defaultName = "My plant"; sp.root = ctx.be.rootFolder();
                const auto& L = njo::plants::all();
                for (size_t i = 0; i < L.size(); ++i) sp.factory.push_back ({ "f:" + juce::String ((int) i), L[i].name, L[i].group, false });
                sp.applyFactory = [this] (int n) { applyPlant (njo::plants::all()[(size_t) n]); };
                sp.ids = [] { std::vector<int> v; for (int k = 0; k < 19; ++k) v.push_back (6700 + k); for (int k = 0; k < 40; ++k) v.push_back (6720 + k); return v; };
                sp.get = [this] (int id) { return ctx.get (id); };
                sp.set = [this] (int id, float v) { setP (id, v); };
                njo::pbrowse::open (*this, njo::pbrowse::makeParamSource (sp));
            }
            void setRandom()
            {
                juce::Random rn;
                for (int l = 0; l < 8; ++l) putLeaf (l, l < 4 || rn.nextBool() ? 1.0f : 0.0f, (float) (l % 2), 0.78f - 0.08f * (float) (l / 2) * 1.8f, 0.4f + rn.nextFloat() * 0.5f, (float) rn.nextInt (10));
                setP (6712, 4.0f + rn.nextFloat() * 20.0f); setP (6717, 15.0f + rn.nextFloat() * 40.0f); setP (6718, 45.0f + rn.nextFloat() * 30.0f); setP (6716, 30.0f + rn.nextFloat() * 10.0f); repaint();
            }
            bool active() const { const auto now = juce::Time::getMillisecondCounter(); for (auto& b : be.boardBalls) if (now - b.ms < 1000) return true; return false; }
            bool needsRepaint() override { return isShowing(); }   // the bubbles and the water move all the time
            void resized() override
            {
                Base::resized();
                auto r = pic.toNearestInt().reduced (2); auto tb = r.removeFromTop (22); r.removeFromTop (4);
                const int n = chips.size(), cw = juce::jmin (90, tb.getWidth() / juce::jmax (1, n)); for (auto* c : chips) c->setBounds (tb.removeFromLeft (cw).reduced (1, 0));
                const float w = juce::jmin ((float) r.getWidth(), ((float) r.getHeight() - 16.0f) * AR), h = w / AR; sq = juce::Rectangle<float> (w, h).withCentre ({ (float) r.getCentreX(), (float) r.getY() + h * 0.5f });
            }
            float halfLen() const { return juce::jlimit (0.06f, 0.5f, p (16) / 100.0f) * 0.5f; }
            static float elevOf (float a) { return (a - 0.5f) * 2.4f; }
            // a leaf is fixed to the stem at (x, y): it points left (x < 0.5) or right, turned up by its angle
            void leafSeg (int l, juce::Point<float>& b0, juce::Point<float>& t0) const
            {
                const float el = elevOf (lv (l, 3)), sd = lv (l, 1) < 0.5f ? -1.0f : 1.0f, hl = halfLen();
                b0 = { p (18) / 100.0f * AR, lv (l, 2) }; t0 = { b0.x + sd * std::cos (el) * 2.0f * hl, b0.y - std::sin (el) * 2.0f * hl };
            }
            // the launch leaf: its base is the launch point (Spawn X, bottom), it points along Aim
            void launchSeg (juce::Point<float>& b0, juce::Point<float>& t0) const
            {
                const float a = p (17) * juce::MathConstants<float>::pi / 180.0f; b0 = { p (12) / 100.0f * AR, 0.93f }; t0 = { b0.x + std::sin (a) * 0.27f, b0.y - std::cos (a) * 0.27f };
            }
            static float segDist (juce::Point<float> q, juce::Point<float> a, juce::Point<float> b, float* tOut = nullptr)
            {
                const float sx = b.x - a.x, sy = b.y - a.y, l2 = sx * sx + sy * sy, t = juce::jlimit (0.0f, 1.0f, ((q.x - a.x) * sx + (q.y - a.y) * sy) / juce::jmax (l2, 1.0e-6f));
                if (tOut) *tOut = t; return std::hypot (q.x - (a.x + t * sx), q.y - (a.y + t * sy));
            }
            juce::Point<float> toBoard (juce::Point<float> q) const { return { juce::jlimit (0.0f, AR, (q.x - sq.getX()) / sq.getWidth() * AR), juce::jlimit (0.0f, 1.0f, (q.y - sq.getY()) / sq.getHeight()) }; }
            int leafAt (juce::Point<float> q) const
            {
                int best = -1; float bd = 0.05f;
                for (int l = 0; l < 8; ++l) { if (lv (l, 0) < 0.5f) continue; juce::Point<float> a, b; leafSeg (l, a, b); const float d = segDist (q, a, b); if (d < bd) { bd = d; best = l; } }
                return best;
            }
            juce::Point<float> slotPos (int l) const { return { p (18) / 100.0f * AR + (lv (l, 1) < 0.5f ? -0.03f : 0.03f), lv (l, 2) }; }
            int slotAt (juce::Point<float> q) const   // a switched-off leaf: its place on the stem
            {
                for (int l = 0; l < 8; ++l) if (lv (l, 0) < 0.5f && std::hypot (q.x - slotPos (l).x, q.y - slotPos (l).y) < 0.045f) return l;
                return -1;
            }
            void mouseDown (const juce::MouseEvent& e) override
            {
                launch = 0; sel = -1; if (! sq.contains (e.position)) return;
                const auto q = toBoard (e.position);
                { juce::Point<float> a, b; launchSeg (a, b); float t = 0; if (segDist (q, a, b, &t) < 0.05f) { launch = t > 0.4f ? 1 : 2; return; } }
                const int l = leafAt (q);
                if (e.mods.isRightButtonDown()) { if (l >= 0) setP (lf (l, 0), 0.0f); repaint(); return; }
                if (l >= 0) { sel = l; return; }
                const int k = slotAt (q); if (k >= 0) { setP (lf (k, 0), 1.0f); repaint(); return; }
                if (std::abs (q.x - p (18) / 100.0f * AR) < 0.03f && q.y > 0.08f && q.y < 0.9f) launch = 3;   // the stem: move the whole plant
            }
            void mouseDrag (const juce::MouseEvent& e) override
            {
                if (e.mods.isRightButtonDown()) return;
                const auto q = toBoard (e.position);
                if (launch == 1) { juce::Point<float> a, b; launchSeg (a, b); const float dg = std::atan2 (q.x - a.x, a.y - q.y) * 180.0f / juce::MathConstants<float>::pi; setP (6717, (float) juce::jlimit (-80, 80, juce::roundToInt (dg))); repaint(); }
                else if (launch == 2) { setP (6712, (float) juce::jlimit (0, 100, juce::roundToInt (q.x / AR * 100.0f))); repaint(); }
                else if (launch == 3) { setP (6718, (float) juce::jlimit (25, 90, juce::roundToInt (q.x / AR * 100.0f))); repaint(); }
                else if (sel >= 0)   // turn the leaf around its fixed end
                {
                    juce::Point<float> b0, t0; leafSeg (sel, b0, t0); const float sd = lv (sel, 1) < 0.5f ? -1.0f : 1.0f, vx = (q.x - b0.x) * sd, vy = q.y - b0.y;
                    if (std::hypot (vx, vy) > 0.01f) setP (lf (sel, 3), juce::jlimit (0.0f, 1.0f, 0.5f + juce::jlimit (-1.2f, 1.2f, std::atan2 (-vy, vx)) / 2.4f));
                    repaint();
                }
            }
            void mouseUp (const juce::MouseEvent&) override { sel = -1; launch = 0; }
            void mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w) override
            {
                if (! sq.contains (e.position)) return;
                const auto q = toBoard (e.position); const float dlt = w.deltaY > 0 ? 1.0f : -1.0f;
                { juce::Point<float> a, b; launchSeg (a, b); if (segDist (q, a, b) < 0.05f) { setP (6717, juce::jlimit (-80.0f, 80.0f, p (17) + dlt * 2.0f)); repaint(); return; } }
                const int l = leafAt (q); if (l < 0) return;
                if (e.mods.isShiftDown()) setP (lf (l, 4), juce::jlimit (0.0f, 24.0f, lv (l, 4) + dlt)); else setP (lf (l, 3), juce::jlimit (0.0f, 1.0f, lv (l, 3) + dlt * 0.04f));
                repaint();
            }
            void paint (juce::Graphics& g) override
            {
                paintBack (g, "Drag a leaf = turn (Shift + wheel = note), right click = off, dot on the stem = on, drag the stem = move. Launch leaf: tip = aim.");
                const auto now = juce::Time::getMillisecondCounter(); const float tm = (float) (now % 600000) / 1000.0f;
                juce::Graphics::ScopedSaveState ss (g);
                juce::Path clip; clip.addRoundedRectangle (sq, 6.0f); g.reduceClipRegion (clip);
                auto P = [&] (float x, float y) { return juce::Point<float> (sq.getX() + x / AR * sq.getWidth(), sq.getY() + y * sq.getHeight()); };   // world -> screen
                const float W = sq.getHeight();   // sizes are in units of the picture height
                g.setGradientFill (juce::ColourGradient (juce::Colour (0xff52c400), sq.getX(), sq.getY(), juce::Colour (0xff2c9a12), sq.getX(), sq.getBottom(), false)); g.fillRect (sq);
                // bubbles
                for (int i = 0; i < 16; ++i)
                {
                    const float s1 = std::fmod (std::sin ((float) i * 12.9898f) * 43758.5f, 1.0f), s2 = std::fmod (std::sin ((float) i * 78.233f) * 12345.6f, 1.0f);
                    const float bx = std::abs (s1), spd = 0.025f + 0.04f * std::abs (s2), by = 1.0f - std::fmod (tm * spd + std::abs (s2) * 3.0f, 1.0f), r = 2.0f + 3.5f * std::abs (std::fmod (s1 * 7.0f, 1.0f));
                    const auto c = P ((bx + 0.012f * std::sin (tm * 1.3f + (float) i)) * AR, by);
                    g.setColour (juce::Colours::white.withAlpha (0.10f)); g.fillEllipse (c.x - r, c.y - r, r * 2.0f, r * 2.0f); g.setColour (juce::Colours::white.withAlpha (0.38f)); g.drawEllipse (c.x - r, c.y - r, r * 2.0f, r * 2.0f, 1.0f);
                }
                // the stem: thick at the water, narrowing in steps up to a thin tip
                const float stemX = p (18) / 100.0f * AR;
                { juce::Path stem; const auto a0 = P (stemX, 1.0f), b0 = P (stemX, 0.085f), m0 = P (stemX, 0.62f), m1 = P (stemX, 0.30f); const float w0 = W * 0.040f, w1 = W * 0.028f, w2 = W * 0.014f, w3 = W * 0.004f;
                  stem.startNewSubPath (a0.x - w0, a0.y); stem.lineTo (m0.x - w1, m0.y); stem.lineTo (m1.x - w2, m1.y); stem.lineTo (b0.x - w3, b0.y); stem.lineTo (b0.x + w3, b0.y); stem.lineTo (m1.x + w2, m1.y); stem.lineTo (m0.x + w1, m0.y); stem.lineTo (a0.x + w0, a0.y); stem.closeSubPath();
                  g.setGradientFill (juce::ColourGradient (juce::Colour (0xff8a2e10), a0.x - w0, 0.0f, juce::Colour (0xffb04a1c), a0.x + w0, 0.0f, false)); g.fillPath (stem); }
                const bool act = active();
                for (int l = 0; l < 8; ++l)
                {
                    if (lv (l, 0) < 0.5f) { const auto d = P (slotPos (l).x, slotPos (l).y); g.setColour (juce::Colours::white.withAlpha (0.35f)); g.fillEllipse (d.x - 3.0f, d.y - 3.0f, 6.0f, 6.0f); continue; }
                    juce::Point<float> b0, t0; leafSeg (l, b0, t0); const auto p1 = P (b0.x, b0.y), p2 = P (t0.x, t0.y), pc = (p1 + p2) * 0.5f;
                    const float len = std::hypot (p2.x - p1.x, p2.y - p1.y), wd = len * 0.30f; const juce::Point<float> nrm (-(p2.y - p1.y) / len * wd, (p2.x - p1.x) / len * wd);
                    const float t = be.boardHitMs[l] != 0 ? (float) (now - be.boardHitMs[l]) / 500.0f : 1.0f, flash = juce::jlimit (0.0f, 1.0f, 1.0f - t * 1.6f);
                    const auto col = stateColour (act ? be.leafState[l] : 0).interpolatedWith (juce::Colours::white, flash * 0.6f);
                    drawLeaf (g, p1, p2, col, col.darker (0.55f), 1.0f);
                    if (t < 1.0f) { const float rr = len * 0.45f * (0.4f + 0.9f * t); g.setColour (juce::Colours::white.withAlpha (0.7f * (1.0f - t))); g.drawEllipse (pc.x - rr, pc.y - rr, rr * 2.0f, rr * 2.0f, 1.6f); }
                    g.setColour (juce::Colour (0xff0e3a10).withAlpha (0.8f)); g.setFont (font (8.5f, true)); g.drawText (juce::String (juce::roundToInt (lv (l, 4))), (int) pc.x - 12, (int) pc.y - 6, 24, 11, juce::Justification::centred);
                    if (sel == l) { g.setColour (juce::Colours::white.withAlpha (0.8f)); g.fillEllipse (p2.x - 3.0f, p2.y - 3.0f, 6.0f, 6.0f); }
                }
                // the launch leaf (bottom left): the tadpoles start at its base and fly along its direction
                {
                    juce::Point<float> b0, t0; launchSeg (b0, t0); const auto p1 = P (b0.x, b0.y), p2 = P (t0.x, t0.y), pc = (p1 + p2) * 0.5f;
                    const float len = std::hypot (p2.x - p1.x, p2.y - p1.y), wd = len * 0.30f; const juce::Point<float> nrm (-(p2.y - p1.y) / len * wd, (p2.x - p1.x) / len * wd);
                    drawLeaf (g, p1, p2, juce::Colour (0xff5fe0c0), juce::Colour (0xff1f8f78), 0.7f);
                    g.setColour (juce::Colours::white.withAlpha (launch == 1 ? 0.8f : 0.4f)); g.drawEllipse (p2.x - W * 0.045f, p2.y - W * 0.045f, W * 0.09f, W * 0.09f, 2.0f);
                    g.setColour (juce::Colours::white.withAlpha (0.85f)); g.setFont (font (8.5f, true)); g.drawText (juce::String (juce::roundToInt (p (17))) + juce::String (juce::CharPointer_UTF8 ("\xc2\xb0")), (int) pc.x - 14, (int) pc.y - 6, 28, 11, juce::Justification::centred);
                }
                // tadpoles
                for (int b = 0; b < 8; ++b)
                {
                    auto& bl = be.boardBalls[b]; if (now - bl.ms > 150) { prevB[b] = { -1.0f, -1.0f }; continue; }
                    const auto c = P (bl.x * AR, bl.y); juce::Point<float> d (0.0f, 1.0f);
                    if (prevB[b].x >= 0 && (prevB[b].x != bl.x || prevB[b].y != bl.y)) { d = { (prevB[b].x - bl.x) * AR, prevB[b].y - bl.y }; const float n = std::hypot (d.x, d.y); d = { d.x / n, d.y / n }; }
                    prevB[b] = { bl.x, bl.y };
                    g.setColour (juce::Colour (0xffff6fa8)); g.drawLine (c.x, c.y, c.x + d.x * 11.0f, c.y + d.y * 11.0f, 2.0f);
                    g.setColour (juce::Colour (0xffffa0c8)); g.fillEllipse (c.x - 4.0f, c.y - 4.0f, 8.0f, 8.0f); g.setColour (juce::Colour (0xff3a1030)); g.fillEllipse (c.x - 1.2f, c.y - 1.8f, 2.4f, 2.4f);
                }
                // the water (surface at 0.82, as in the DSP)
                juce::Path water; { const float y0 = 0.82f; water.startNewSubPath (sq.getX(), sq.getBottom()); const int n = 40;
                    for (int i = 0; i <= n; ++i) { const float x = (float) i / (float) n, spike = (i % 2 == 0 ? 0.0f : -0.016f) * (0.7f + 0.3f * std::sin (tm * 2.0f + (float) i)); water.lineTo (P (x * AR, y0 + spike + 0.005f * std::sin (tm * 1.6f + (float) i * 0.7f))); }
                    water.lineTo (sq.getRight(), sq.getBottom()); water.closeSubPath(); }
                g.setGradientFill (juce::ColourGradient (juce::Colour (0xdd20c0b8), sq.getX(), P (0, 0.82f).y, juce::Colour (0xee22349a), sq.getX(), sq.getBottom(), false)); g.fillPath (water);
                { juce::Graphics::ScopedSaveState ws (g); g.reduceClipRegion (water); g.setColour (juce::Colours::black.withAlpha (0.07f)); for (float yy = P (0, 0.82f).y; yy < sq.getBottom(); yy += 5.0f) g.drawHorizontalLine ((int) yy, sq.getX(), sq.getRight()); }
                g.setColour (juce::Colours::black.withAlpha (0.35f)); g.drawRect (sq, 1.0f);
            }
        };

        // ---- Luminaria (Arp Mode 14): four walkers on an 8 x 8 grid of arrows (DSP: build_hanenbow.py, parameters 6760.., walkers 6780 + 5 * w + j, cells 6800 + 8 * y + x) ----
        struct Luminaria : Base
        {
            Backend& be; juce::Rectangle<float> sq; int tool = 0; juce::OwnedArray<FxChip> chips;
            static juce::Colour wc (int w) { static const juce::uint32 c[4] = { 0xffffd24a, 0xff6fd0ff, 0xff6fe08a, 0xffe070ff }; return juce::Colour (c[w & 3]); }
            static int wk (int w, int j) { return 6780 + 5 * w + j; }
            static int cellId (int c) { return 6800 + c; }
            void setP (int id, float v) { ctx.begin (id); ctx.set (id, v); ctx.end (id); }
            int wv (int w, int j) const { return juce::roundToInt (ctx.get (wk (w, j))); }
            int cellVal (int c) const { return juce::jlimit (0, 4, juce::roundToInt (ctx.get (cellId (c)))); }
            void setCell (int c, int v) { setP (cellId (c), (float) v); be.lumDir[(size_t) c] = -1; }
            void putWalker (int w, int on, int x, int y, int d, int o) { const int v[5] = { on, x, y, d, o }; for (int j = 0; j < 5; ++j) setP (wk (w, j), (float) v[j]); }
            explicit Luminaria (Ctx& c) : Base (c, 6760, 11, { 1, 6, 8, 9, 10 }), be (c.be)
            {
                auto add = [this] (const juce::String& t, std::function<void()> f) { auto* ch = new FxChip(); ch->text = t; ch->click = std::move (f); chips.add (ch); addAndMakeVisible (ch); return ch; };
                add ("ARROWS", [this] { tool = 0; refreshChips(); });
                for (int w = 0; w < 4; ++w) { auto* ch = add ("WALKER " + juce::String (w + 1), [this, w] { tool = w + 1; refreshChips(); }); ch->tint = wc (w); }
                add ("CLEAR", [this] { for (int k = 0; k < 64; ++k) if (cellVal (k) != 0) setCell (k, 0); repaint(); });
                add ("PRESETS", [this] { presets(); });
                refreshChips();
            }
            void refreshChips() { for (int i = 0; i < 5; ++i) chips[i]->on = (i == tool); for (auto* c : chips) c->repaint(); }
            void setGrid (const std::vector<std::array<int, 3>>& a) { for (int k = 0; k < 64; ++k) setCell (k, 0); for (auto& e : a) setCell (e[1] * 8 + e[0], e[2]); }
            void presets()
            {
                juce::PopupMenu m; const char* n[] = { "Two loops", "One big loop", "Spiral inwards", "Random" };
                for (int i = 0; i < 4; ++i) m.addItem (i + 1, n[i]);
                juce::Component::SafePointer<juce::Component> sp (this);
                m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (chips.getLast()), [this, sp] (int r) { if (sp != nullptr && r > 0) preset (r - 1); });
            }
            void preset (int i)
            {
                if (i == 0)
                {
                    setGrid ({ { 1, 1, 2 }, { 6, 1, 3 }, { 6, 6, 4 }, { 1, 6, 1 }, { 3, 3, 2 }, { 5, 3, 3 }, { 5, 5, 4 }, { 3, 5, 1 } });
                    putWalker (0, 1, 1, 1, 2, 0); putWalker (1, 1, 3, 3, 2, 1); putWalker (2, 1, 6, 6, 4, 0); putWalker (3, 1, 5, 5, 4, -1);
                }
                else if (i == 1)
                {
                    setGrid ({ { 0, 0, 2 }, { 7, 0, 3 }, { 7, 7, 4 }, { 0, 7, 1 } });
                    putWalker (0, 1, 0, 0, 2, 0); putWalker (1, 1, 7, 0, 3, 0); putWalker (2, 1, 7, 7, 4, 0); putWalker (3, 1, 0, 7, 1, 0);
                }
                else if (i == 2)
                {
                    setGrid ({ { 0, 0, 2 }, { 7, 0, 3 }, { 7, 7, 4 }, { 1, 7, 1 }, { 1, 1, 2 }, { 6, 1, 3 }, { 6, 6, 4 }, { 2, 6, 1 }, { 2, 2, 2 }, { 5, 2, 3 }, { 5, 5, 4 }, { 3, 5, 1 }, { 3, 3, 2 }, { 4, 3, 3 }, { 4, 4, 4 }, { 3, 4, 1 } });
                    putWalker (0, 1, 0, 0, 2, 0); putWalker (1, 0, 0, 0, 2, 0); putWalker (2, 0, 0, 0, 2, 0); putWalker (3, 0, 0, 0, 2, 0);
                }
                else
                {
                    juce::Random rn; std::vector<std::array<int, 3>> a; for (int k = 0; k < 12; ++k) a.push_back ({ rn.nextInt (8), rn.nextInt (8), 1 + rn.nextInt (4) });
                    setGrid (a); for (int w = 0; w < 4; ++w) putWalker (w, 1, rn.nextInt (8), rn.nextInt (8), 1 + rn.nextInt (4), w == 3 ? -1 : 0);
                }
                repaint();
            }
            bool running() const
            {
                const auto now = juce::Time::getMillisecondCounter(); bool r = false;
                for (int w = 0; w < 4; ++w) if (be.lumWalkMs[w] != 0 && now - be.lumWalkMs[w] < 1500) r = true;
                if (! r) for (auto& d : be.lumDir) d = -1;   // stopped: the DSP starts again from the parameters
                return r;
            }
            bool needsRepaint() override
            {
                const auto now = juce::Time::getMillisecondCounter();
                for (int w = 0; w < 4; ++w) if (be.lumWalkMs[w] != 0 && now - be.lumWalkMs[w] < 1500) return true;
                return false;
            }
            void resized() override
            {
                Base::resized();
                auto r = pic.toNearestInt().reduced (2); auto tb = r.removeFromTop (22); r.removeFromTop (4);
                const int n = chips.size(), cw = juce::jmin (96, tb.getWidth() / juce::jmax (1, n)); for (auto* c : chips) c->setBounds (tb.removeFromLeft (cw).reduced (1, 0));
                const float side = (float) juce::jmin (r.getWidth(), r.getHeight() - 16); sq = juce::Rectangle<float> (side, side).withCentre ({ (float) r.getCentreX(), (float) r.getY() + side * 0.5f });
            }
            int cellAt (juce::Point<float> q) const { if (! sq.contains (q)) return -1; const int x = juce::jlimit (0, 7, (int) ((q.x - sq.getX()) / sq.getWidth() * 8.0f)), y = juce::jlimit (0, 7, (int) ((q.y - sq.getY()) / sq.getHeight() * 8.0f)); return y * 8 + x; }
            void mouseDown (const juce::MouseEvent& e) override
            {
                const int c = cellAt (e.position); if (c < 0) return;
                const int x = c % 8, y = c / 8;
                if (tool == 0) { setCell (c, e.mods.isRightButtonDown() ? 0 : (cellVal (c) + 1) % 5); repaint(); return; }
                const int w = tool - 1;
                if (e.mods.isRightButtonDown()) { setP (wk (w, 0), 0.0f); repaint(); return; }
                if (wv (w, 0) == 1 && wv (w, 1) == x && wv (w, 2) == y) setP (wk (w, 3), (float) (wv (w, 3) % 4 + 1));   // the same cell again: turn the start direction
                else { setP (wk (w, 0), 1.0f); setP (wk (w, 1), (float) x); setP (wk (w, 2), (float) y); }
                repaint();
            }
            void mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w) override
            {
                if (tool == 0 || ! sq.contains (e.position)) return;
                setP (wk (tool - 1, 4), (float) juce::jlimit (-2, 2, wv (tool - 1, 4) + (w.deltaY > 0 ? 1 : -1))); repaint();
            }
            void paint (juce::Graphics& g) override
            {
                paintBack (g, "ARROWS: click turns an arrow, right click clears. WALKER: click = start cell (again = turn), wheel = octave.");
                g.setColour (juce::Colour (0xff15171a)); g.fillRect (sq); g.setColour (juce::Colours::white.withAlpha (0.08f)); g.drawRect (sq, 1.0f);
                const float cs = sq.getWidth() / 8.0f; const auto now = juce::Time::getMillisecondCounter(); const bool run = running();
                for (int i = 1; i < 8; ++i) { g.drawVerticalLine ((int) (sq.getX() + cs * (float) i), sq.getY(), sq.getBottom()); g.drawHorizontalLine ((int) (sq.getY() + cs * (float) i), sq.getX(), sq.getRight()); }
                for (int c = 0; c < 64; ++c)
                {
                    int a = cellVal (c); if (run && be.lumDir[(size_t) c] >= 1) a = be.lumDir[(size_t) c];
                    const float cx = sq.getX() + (float) (c % 8) * cs + cs * 0.5f, cy = sq.getY() + (float) (c / 8) * cs + cs * 0.5f;
                    const float flash = be.lumFlashMs[c] != 0 ? juce::jlimit (0.0f, 1.0f, 1.0f - (float) (now - be.lumFlashMs[c]) / 350.0f) : 0.0f;
                    if (a == 0) { if (flash > 0) { g.setColour (juce::Colours::white.withAlpha (0.12f * flash)); g.fillRect (cx - cs * 0.5f + 1, cy - cs * 0.5f + 1, cs - 2, cs - 2); } continue; }
                    g.setColour (juce::Colour (0xffffd24a).withAlpha (0.12f + 0.35f * flash)); g.fillRect (cx - cs * 0.5f + 1, cy - cs * 0.5f + 1, cs - 2, cs - 2);
                    const float rot = (float) (a - 1) * juce::MathConstants<float>::halfPi, s = cs * 0.28f;
                    juce::Path ph; ph.addTriangle (0.0f, -s, s * 0.8f, s * 0.7f, -s * 0.8f, s * 0.7f); ph.applyTransform (juce::AffineTransform::rotation (rot).translated (cx, cy));
                    g.setColour (juce::Colour (0xffffd24a).interpolatedWith (juce::Colours::white, flash)); g.fillPath (ph);
                }
                for (int w = 0; w < 4; ++w)
                {
                    if (wv (w, 0) != 1) continue;
                    int cell = wv (w, 2) * 8 + wv (w, 1); if (run && be.lumWalkMs[w] != 0 && now - be.lumWalkMs[w] < 1500 && be.lumWalkCell[w] >= 0) cell = be.lumWalkCell[w];
                    const float cx = sq.getX() + (float) (cell % 8) * cs + cs * 0.5f + (float) (w % 2 - 0.5f) * cs * 0.18f, cy = sq.getY() + (float) (cell / 8) * cs + cs * 0.5f + (float) (w / 2 - 0.5f) * cs * 0.18f, r = cs * 0.2f;
                    g.setColour (wc (w).withAlpha (0.35f)); g.fillEllipse (cx - r * 1.6f, cy - r * 1.6f, r * 3.2f, r * 3.2f); g.setColour (wc (w)); g.fillEllipse (cx - r, cy - r, r * 2.0f, r * 2.0f);
                    if (! run) { g.setColour (juce::Colour (0xff101112)); g.setFont (font (8.5f, true)); g.drawText (wv (w, 4) == 0 ? juce::String (w + 1) : (wv (w, 4) > 0 ? "+" : "") + juce::String (wv (w, 4)), (int) (cx - r), (int) (cy - r), (int) (r * 2), (int) (r * 2), juce::Justification::centred); }
                }
            }
        };
    }
}
