#include "WavetableEditor.h"
#include "../NjoWt.h"
#include "OscDisplays.h"
#include <algorithm>
#include <cmath>
#include <random>

namespace njo
{
    using namespace theme;

    namespace
    {
        constexpr int N = 2048, MAXF = 256, NH = 64;
        struct Btn : public juce::Component
        {
            juce::String text; bool accent = false, over = false; std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintButton (g, r, accent, over, false, 3.0f);
                g.setColour (accent ? juce::Colours::white : ink); g.setFont (font (9.0f, true).withExtraKerningFactor (0.05f));
                g.drawText (text, r.toNearestInt(), juce::Justification::centred);
            }
            void mouseEnter (const juce::MouseEvent&) override { over = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { over = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };
        using Frame = std::vector<float>;
    }

    struct WavetableEditor::Impl
    {
        Impl (WavetableEditor& o, Ctx& c, SoundMemory& m, int osc) : owner (o), ctx (c), mem (m), os (osc)
        {
            auto add = [this] (const juce::String& t, std::function<void()> fn, bool accent = false)
            {
                auto* b = buttons.add (new Btn()); b->text = t; b->click = std::move (fn); b->accent = accent; owner.addAndMakeVisible (b); return b;
            };
            closeBtn = add ("CLOSE", [this] { owner.setVisible (false); if (owner.onClose) owner.onClose(); }, true);
            add ("ADD", [this] { addFrame(); });
            add ("DELETE", [this] { delFrame(); });
            add ("PREV", [this] { sel = juce::jmax (0, sel - 1); owner.repaint(); });
            add ("NEXT", [this] { sel = juce::jmin ((int) fr.size() - 1, sel + 1); owner.repaint(); });
            add ("MORPH TO END", [this] { morphToEnd(); });
            add ("NORMALIZE", [this] { edit ([this] { normalize (cur()); }); });
            add ("SMOOTH", [this] { edit ([this] { smooth (cur()); }); });
            add ("INVERT", [this] { edit ([this] { for (auto& x : cur()) x = -x; }); });
            add ("REVERSE", [this] { edit ([this] { std::reverse (cur().begin(), cur().end()); }); });
            add ("RANDOM", [this] { edit ([this] { randomize (cur()); }); });
            for (auto nm : { "SINE", "SAW", "SQUARE", "TRI", "PULSE", "NOISE" })
                add (nm, [this, nm] { edit ([this, nm] { shape (cur(), nm); }); });
            for (auto b : buttons) if (b->text.length() > 0) {}
        }

        Frame& cur() { return fr[(size_t) sel]; }
        void edit (const std::function<void()>& f) { f(); commit(); owner.repaint(); }

        // ---- data ----
        void load()
        {
            fr.clear(); sel = 0;
            if (auto* s = mem.get (SoundMemory::Wavetable, os))
            {
                const int fs = oscmodel::frameSizes[juce::jlimit (0, 4, juce::roundToInt (ctx.get (oscId (os, oscKey ("wsize")))))];
                const int nf = juce::jmax (1, juce::jmin (MAXF, (int) s->data.size() / fs));
                for (int f = 0; f < nf; ++f)
                {
                    Frame q ((size_t) N);
                    for (int i = 0; i < N; ++i)
                    {
                        const float p = (float) i * (float) fs / (float) N; const int i0 = (int) p; const float fr0 = p - (float) i0;
                        const float a = s->data[(size_t) (f * fs + i0 % fs)], b = s->data[(size_t) (f * fs + (i0 + 1) % fs)];
                        q[(size_t) i] = a + (b - a) * fr0;
                    }
                    fr.push_back (std::move (q));
                }
                name = s->name;
            }
            if (fr.empty()) { fr.push_back (Frame ((size_t) N)); shape (fr[0], "SINE"); name = "Custom"; }
        }
        void commit()
        {
            std::vector<float> d; d.reserve (fr.size() * (size_t) N);
            for (auto& q : fr) d.insert (d.end(), q.begin(), q.end());
            selfWrite = true;
            mem.set (SoundMemory::Wavetable, os, name.isEmpty() ? juce::String ("Custom") : name, {}, std::move (d));
            selfWrite = false;
            ctx.set (oscId (os, oscKey ("wsize")), 3.0f);
        }
        void addFrame() { if ((int) fr.size() >= MAXF) return; fr.insert (fr.begin() + sel + 1, cur()); ++sel; commit(); owner.repaint(); }
        void delFrame() { if (fr.size() <= 1) return; fr.erase (fr.begin() + sel); sel = juce::jmin (sel, (int) fr.size() - 1); commit(); owner.repaint(); }
        void morphToEnd()   // fill with crossfaded copies between the selected frame and the last one (or add 7 frames when it is the last)
        {
            const int last = (int) fr.size() - 1;
            if (sel == last)
            {
                const Frame a = cur(); const int add = juce::jmin (7, MAXF - (int) fr.size());
                for (int k = 1; k <= add; ++k) fr.push_back (a);
                commit(); owner.repaint(); return;
            }
            for (int f = sel + 1; f < last; ++f)
            {
                const float t = (float) (f - sel) / (float) (last - sel);
                for (int i = 0; i < N; ++i) fr[(size_t) f][(size_t) i] = fr[(size_t) sel][(size_t) i] * (1.0f - t) + fr[(size_t) last][(size_t) i] * t;
            }
            commit(); owner.repaint();
        }
        static void normalize (Frame& q) { float m = 0; for (float x : q) m = std::max (m, std::abs (x)); if (m > 1.0e-6f) for (auto& x : q) x /= m; }
        static void smooth (Frame& q) { Frame o = q; for (int i = 0; i < N; ++i) q[(size_t) i] = 0.25f * o[(size_t) ((i + N - 1) % N)] + 0.5f * o[(size_t) i] + 0.25f * o[(size_t) ((i + 1) % N)]; }
        static void randomize (Frame& q)
        {
            static std::mt19937 rng (12345); std::uniform_real_distribution<float> u (-1.0f, 1.0f);
            std::fill (q.begin(), q.end(), 0.0f);
            for (int h = 1; h <= 24; ++h) { const float a = u (rng) / (float) h, ph = u (rng) * 3.14159f; for (int i = 0; i < N; ++i) q[(size_t) i] += a * std::sin (6.2831853f * (float) (h * i) / (float) N + ph); }
            normalize (q);
        }
        static void shape (Frame& q, const juce::String& n)
        {
            std::mt19937 rng (777); std::uniform_real_distribution<float> u (-1.0f, 1.0f);
            for (int i = 0; i < N; ++i)
            {
                const float p = (float) i / (float) N; float v = 0;
                if (n == "SINE") v = std::sin (6.2831853f * p);
                else if (n == "SAW") v = 2.0f * p - 1.0f;
                else if (n == "SQUARE") v = p < 0.5f ? 1.0f : -1.0f;
                else if (n == "TRI") v = p < 0.5f ? 4.0f * p - 1.0f : 3.0f - 4.0f * p;
                else if (n == "PULSE") v = p < 0.15f ? 1.0f : -1.0f;
                else v = u (rng);
                q[(size_t) i] = v;
            }
        }
        // harmonic k: amplitude and phase components from a DFT of the frame
        void harmonic (const Frame& q, int k, float& a, float& b) const
        {
            double sa = 0, sb = 0;
            for (int i = 0; i < N; ++i) { const double w = 6.283185307 * (double) ((k * i) % N) / (double) N; sa += q[(size_t) i] * std::cos (w); sb += q[(size_t) i] * std::sin (w); }
            a = (float) (2.0 * sa / N); b = (float) (2.0 * sb / N);
        }
        void setHarmonicMag (int k, float mag)
        {
            float a, b; harmonic (cur(), k, a, b); float m = std::sqrt (a * a + b * b);
            float na, nb; if (m < 1.0e-5f) { na = 0; nb = mag; } else { na = a / m * mag; nb = b / m * mag; }
            const float da = na - a, db = nb - b;
            for (int i = 0; i < N; ++i) { const float w = 6.2831853f * (float) ((k * i) % N) / (float) N; cur()[(size_t) i] += da * std::cos (w) + db * std::sin (w); }
        }

        // ---- geometry ----
        juce::Rectangle<int> water, draw, harm, strip;
        void layout()
        {
            auto all = owner.getLocalBounds();
            closeBtn->setBounds (all.getRight() - 82, 7, 70, 20);
            int x = 12, y = 7, w = all.getRight() - 100;
            for (int i = 1; i < buttons.size(); ++i)
            {
                const int bw = buttons[i]->text.length() > 8 ? 100 : 56;
                if (x + bw > w) { x = 12; y += 24; }
                buttons[i]->setBounds (x, y, bw, 20); x += bw + 5;
            }
            const int top = y + 34, h = all.getHeight() - top - 12, half = (all.getWidth() - 36) / 2;
            water = { 12, top, half, h - 36 }; draw = { 24 + half, top, half, (h - 36) / 2 - 6 };
            harm = { 24 + half, draw.getBottom() + 18, half, (h - 36) - draw.getHeight() - 18 };
            strip = { 12, water.getBottom() + 10, half, 26 };
        }
        float frameX (int x0, int w, int i) const { return (float) x0 + (float) w * (float) i / (float) N; }
        void paintAll (juce::Graphics& g)
        {
            g.fillAll (panel); g.setColour (deep); g.fillRect (water); g.fillRect (draw); g.fillRect (harm);
            g.setFont (font (9.0f, true)); g.setColour (dim);
            g.drawText ("WATERFALL  -  " + juce::String ((int) fr.size()) + " FRAMES  -  CLICK TO SELECT", water.getX(), water.getY() - 13, water.getWidth(), 11, juce::Justification::left);
            g.drawText ("FRAME " + juce::String (sel + 1) + "  -  DRAW WITH THE MOUSE", draw.getX(), draw.getY() - 13, draw.getWidth(), 11, juce::Justification::left);
            g.drawText ("HARMONICS 1.." + juce::String (NH) + "  -  DRAG TO SET", harm.getX(), harm.getY() - 13, harm.getWidth(), 11, juce::Justification::left);
            // waterfall: back frame first, shifted up-right per frame; the selected frame in red
            const int nf = (int) fr.size();
            const float dx = juce::jmin (3.0f, 90.0f / (float) nf), dy = juce::jmin (6.0f, (float) water.getHeight() * 0.5f / (float) nf);
            const float ww = (float) water.getWidth() - dx * (float) nf - 4.0f, amp = juce::jmin (26.0f, (float) water.getHeight() * 0.2f);
            const int step = 8;
            for (int f = nf - 1; f >= 0; --f)
            {
                const float ox = (float) water.getX() + 2.0f + dx * (float) f, oy = (float) water.getBottom() - 10.0f - amp - dy * (float) f;
                juce::Path p; auto& q = fr[(size_t) f];
                for (int i = 0; i <= N; i += step) { const float v = q[(size_t) (i % N)]; const float px = ox + ww * (float) i / (float) N, py = oy - v * amp; if (i == 0) p.startNewSubPath (px, py); else p.lineTo (px, py); }
                juce::Path fill (p); fill.lineTo (ox + ww, oy + amp); fill.lineTo (ox, oy + amp); fill.closeSubPath();
                g.setColour (deep.withAlpha (0.9f)); g.fillPath (fill);
                g.setColour (f == sel ? juce::Colour (0xffff3e30) : juce::Colour (0xffc9c2be).withAlpha (0.35f + 0.4f * (float) f / (float) juce::jmax (1, nf)));
                g.strokePath (p, juce::PathStrokeType (f == sel ? 1.6f : 0.8f));
            }
            // frame strip
            g.setColour (panel2); g.fillRect (strip);
            for (int f = 0; f < nf; ++f)
            {
                const float x0 = (float) strip.getX() + (float) strip.getWidth() * (float) f / (float) nf, x1 = (float) strip.getX() + (float) strip.getWidth() * (float) (f + 1) / (float) nf;
                g.setColour (f == sel ? juce::Colour (0xffff3e30) : line); g.fillRect (x0 + 0.5f, (float) strip.getY() + 2.0f, juce::jmax (1.0f, x1 - x0 - 1.0f), (float) strip.getHeight() - 4.0f);
            }
            // selected frame
            g.setColour (line); g.drawHorizontalLine (draw.getCentreY(), (float) draw.getX(), (float) draw.getRight());
            juce::Path p;
            for (int i = 0; i < N; i += 2) { const float x = frameX (draw.getX(), draw.getWidth(), i), y = (float) draw.getCentreY() - cur()[(size_t) i] * (float) draw.getHeight() * 0.45f; if (i == 0) p.startNewSubPath (x, y); else p.lineTo (x, y); }
            g.setColour (juce::Colour (0xffff3e30)); g.strokePath (p, juce::PathStrokeType (1.4f));
            // harmonics
            if (harmDirty) { for (int k = 1; k <= NH; ++k) { float a, b; harmonic (cur(), k, a, b); mags[(size_t) k - 1] = std::sqrt (a * a + b * b); } harmDirty = false; }
            const float bw = (float) harm.getWidth() / (float) NH;
            for (int k = 0; k < NH; ++k)
            {
                const float v = juce::jlimit (0.0f, 1.0f, mags[(size_t) k]), h = v * ((float) harm.getHeight() - 4.0f);
                g.setColour (juce::Colour (0xff7fd0ff).withAlpha (0.85f)); g.fillRect ((float) harm.getX() + bw * (float) k + 1.0f, (float) harm.getBottom() - 2.0f - h, juce::jmax (1.0f, bw - 2.0f), h);
            }
        }
        void pointer (juce::Point<int> pt, bool first)
        {
            if (strip.expanded (0, 6).contains (pt) && first) { sel = juce::jlimit (0, (int) fr.size() - 1, (pt.x - strip.getX()) * (int) fr.size() / strip.getWidth()); harmDirty = true; owner.repaint(); mode = 1; return; }
            if (first)
            {
                mode = draw.contains (pt) ? 2 : harm.contains (pt) ? 3 : water.contains (pt) ? 4 : 0;
                lastI = -1;
            }
            if (mode == 1) { sel = juce::jlimit (0, (int) fr.size() - 1, (pt.x - strip.getX()) * (int) fr.size() / strip.getWidth()); harmDirty = true; owner.repaint(); }
            else if (mode == 2)
            {
                const int i = juce::jlimit (0, N - 1, (pt.x - draw.getX()) * N / draw.getWidth());
                const float v = juce::jlimit (-1.0f, 1.0f, (float) (draw.getCentreY() - pt.y) / ((float) draw.getHeight() * 0.45f));
                if (lastI < 0) { cur()[(size_t) i] = v; }
                else { const int a = juce::jmin (i, lastI), b = juce::jmax (i, lastI); for (int j = a; j <= b; ++j) { const float t = b == a ? 1.0f : (float) (j - lastI) / (float) (i - lastI); cur()[(size_t) j] = lastV + (v - lastV) * juce::jlimit (0.0f, 1.0f, t); } }
                lastI = i; lastV = v; harmDirty = true; dirty = true; owner.repaint();
            }
            else if (mode == 3)
            {
                const int k = juce::jlimit (0, NH - 1, (pt.x - harm.getX()) * NH / harm.getWidth());
                const float m = juce::jlimit (0.0f, 1.0f, (float) (harm.getBottom() - pt.y) / (float) harm.getHeight());
                setHarmonicMag (k + 1, m); harmDirty = true; dirty = true; owner.repaint();
            }
            else if (mode == 4)   // water: pick the frame whose shifted baseline is nearest in height
            {
                const int nf = (int) fr.size(); const float dy = juce::jmin (6.0f, (float) water.getHeight() * 0.5f / (float) nf);
                const float amp = juce::jmin (26.0f, (float) water.getHeight() * 0.2f);
                const int f = juce::jlimit (0, nf - 1, juce::roundToInt (((float) water.getBottom() - 10.0f - amp - (float) pt.y) / juce::jmax (0.1f, dy)));
                sel = f; harmDirty = true; owner.repaint();
            }
        }
        WavetableEditor& owner; Ctx& ctx; SoundMemory& mem; int os;
        juce::OwnedArray<Btn> buttons; Btn* closeBtn = nullptr;
        std::vector<Frame> fr; int sel = 0; juce::String name;
        std::array<float, NH> mags {}; bool harmDirty = true, dirty = false, selfWrite = false; int mode = 0, lastI = -1; float lastV = 0;
    };

    WavetableEditor::WavetableEditor (Ctx& c, SoundMemory& m, int osc) : impl (new Impl (*this, c, m, osc)) { m.addChangeListener (this); setVisible (false); setName ("wavetableEditor"); }
    WavetableEditor::~WavetableEditor() { impl->mem.removeChangeListener (this); }
    void WavetableEditor::open() { impl->load(); impl->harmDirty = true; setVisible (true); toFront (false); resized(); repaint(); }
    void WavetableEditor::paint (juce::Graphics& g) { impl->paintAll (g); }
    void WavetableEditor::resized() { impl->layout(); }
    void WavetableEditor::changeListenerCallback (juce::ChangeBroadcaster*) { if (isVisible() && ! impl->selfWrite) { impl->load(); impl->harmDirty = true; repaint(); } }
    void WavetableEditor::mouseDown (const juce::MouseEvent& e) { impl->pointer (e.getPosition(), true); }
    void WavetableEditor::mouseDrag (const juce::MouseEvent& e) { impl->pointer (e.getPosition(), false); }
    void WavetableEditor::mouseUp (const juce::MouseEvent&) { if (impl->dirty) { impl->dirty = false; impl->commit(); } impl->mode = 0; }
}
