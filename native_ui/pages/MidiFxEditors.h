// Editors of the MIDI FX page for the arpeggiator modes 9 Plinko, 10 Bounce and 11 Cellular (DSP: tools/mod/build_plinko.py, parameters 6300.., 6320.., 6340..).
// Each editor shows the parameters as knobs and a picture of what the mode does: the Plinko board with the balls the DSP reports, the arcs of the bouncing ball,
// the generations of the cellular automaton.
#pragma once
#include "ModUi.h"
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
    }
}
