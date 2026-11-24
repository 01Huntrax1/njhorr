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

        // ---- Razor (wave slicing): the cycle is cut into up to 8 segments, each plays the source (or a basic shape) with its own level, phase, DC and tuning ----
        struct Razor
        {
            int   n = 1;                 // segments (1 = no change)
            float size = 1.0f;           // length of the source cycle each segment plays (cycles)
            float duty = 0.5f;           // alternating segments get duty / (1 - duty) of their pair
            float mix = 1.0f;
            bool  pol = false;           // constant polarity: every segment keeps the polarity of its level
            bool  all = false;           // apply to all frames
            std::array<float, 8> lvl, ph, dc, semi; std::array<int, 8> shp;
            Razor() { reset(); }
            void reset() { n = 1; size = 1.0f; duty = 0.5f; mix = 1.0f; pol = false; lvl.fill (1.0f); ph.fill (0.0f); dc.fill (0.0f); semi.fill (0.0f); shp.fill (0); }
        };
        constexpr const char* razorShapes[] = { "SRC", "SINE", "SAW", "SQR", "TRI" };
        inline float razorRead (const Frame& q, float p)
        {
            p -= std::floor (p); const float x = p * (float) N; const int i = (int) x; const float f = x - (float) i;
            return q[(size_t) (i % N)] * (1.0f - f) + q[(size_t) ((i + 1) % N)] * f;
        }
        inline float razorShape (const Frame& q, int s, float p)
        {
            if (s == 0) return razorRead (q, p);
            p -= std::floor (p);
            if (s == 1) return std::sin (6.2831853f * p);
            if (s == 2) return 2.0f * p - 1.0f;
            if (s == 3) return p < 0.5f ? 1.0f : -1.0f;
            return p < 0.5f ? 4.0f * p - 1.0f : 3.0f - 4.0f * p;
        }
        void razorRender (const Frame& src, const Razor& r, Frame& out)
        {
            out.assign ((size_t) N, 0.0f);
            const int n = juce::jlimit (1, 8, r.n);
            float w[8], st[8], sum = 0.0f;
            for (int k = 0; k < n; ++k)
            {
                const bool paired = (k | 1) < n;
                w[k] = n == 1 ? 1.0f : paired ? 2.0f / (float) n * ((k & 1) ? 1.0f - r.duty : r.duty) : 1.0f / (float) n;
                sum += w[k];
            }
            float acc = 0.0f;
            for (int k = 0; k < n; ++k) { w[k] /= sum; st[k] = acc; acc += w[k]; }
            float peak = 0.0f; int k = 0;
            for (int i = 0; i < N; ++i)
            {
                const float p = (float) i / (float) N;
                while (k < n - 1 && p >= st[k + 1]) ++k;
                const float t = (p - st[k]) / juce::jmax (1.0e-6f, w[k]);
                float v = razorShape (src, r.shp[(size_t) k], r.ph[(size_t) k] + t * r.size * std::pow (2.0f, r.semi[(size_t) k] / 12.0f));
                if (r.pol) v = std::abs (v) * (r.lvl[(size_t) k] < 0.0f ? -1.0f : 1.0f) * std::abs (r.lvl[(size_t) k]);
                else v *= r.lvl[(size_t) k];
                v += r.dc[(size_t) k];
                v = src[(size_t) i] * (1.0f - r.mix) + v * r.mix;
                out[(size_t) i] = v; peak = std::max (peak, std::abs (v));
            }
            if (peak > 1.0f) for (auto& v : out) v /= peak;
        }

        // the controls of the razor: drag a field horizontally to set it, double-click resets it
        struct RazorPanel : public juce::Component
        {
            Razor r; std::function<void()> onChange, onApply;
            struct Field { juce::Rectangle<int> rc; int kind = 0, idx = 0; };   // kinds: 0 steps, 1 size, 2 duty, 3 mix, 4 lvl, 5 phase, 6 dc, 7 tune, 8 shape, 9 pol, 10 all, 11 apply, 12 reset
            std::vector<Field> fields; int drag = -1;
            void resized() override
            {
                fields.clear(); auto b = getLocalBounds().reduced (6, 4); const int rh = 17, lw = 40;
                auto top = b.removeFromTop (rh); b.removeFromTop (3);
                const int fw = (top.getWidth() - 3 * 4) / 4;
                for (int i = 0; i < 4; ++i) fields.push_back ({ top.removeFromLeft (fw), i, 0 }), top.removeFromLeft (4);
                auto t2 = b.removeFromTop (rh); b.removeFromTop (5);
                const int bw = (t2.getWidth() - 3 * 4) / 4;
                for (int i = 0; i < 4; ++i) fields.push_back ({ t2.removeFromLeft (bw), 9 + i, 0 }), t2.removeFromLeft (4);
                const int cw = (b.getWidth() - lw) / 8;
                const int kinds[] = { 8, 4, 5, 6, 7 };
                for (int row = 0; row < 5; ++row)
                {
                    auto rr = b.removeFromTop (rh); b.removeFromTop (2); rr.removeFromLeft (lw);
                    for (int c = 0; c < 8; ++c) fields.push_back ({ rr.removeFromLeft (cw).reduced (1, 0), kinds[row], c });
                }
            }
            static float lerpv (float u, float a, float b) { return a + (b - a) * juce::jlimit (0.0f, 1.0f, u); }
            float get (const Field& f) const   // 0..1
            {
                switch (f.kind) {
                    case 0: return (float) (r.n - 1) / 7.0f;
                    case 1: return std::log2 (r.size / 0.125f) / 5.0f;
                    case 2: return (r.duty - 0.1f) / 0.8f;
                    case 3: return r.mix;
                    case 4: return (r.lvl[(size_t) f.idx] + 1.0f) * 0.5f;
                    case 5: return r.ph[(size_t) f.idx];
                    case 6: return (r.dc[(size_t) f.idx] + 1.0f) * 0.5f;
                    case 7: return (r.semi[(size_t) f.idx] + 24.0f) / 48.0f;
                }
                return 0.0f;
            }
            void set (const Field& f, float u)
            {
                u = juce::jlimit (0.0f, 1.0f, u);
                switch (f.kind) {
                    case 0: r.n = 1 + juce::roundToInt (u * 7.0f); break;
                    case 1: r.size = 0.125f * std::pow (2.0f, u * 5.0f); r.size = std::round (r.size * 100.0f) / 100.0f; break;
                    case 2: r.duty = std::round ((0.1f + 0.8f * u) * 100.0f) / 100.0f; break;
                    case 3: r.mix = std::round (u * 100.0f) / 100.0f; break;
                    case 4: r.lvl[(size_t) f.idx] = std::round ((u * 2.0f - 1.0f) * 100.0f) / 100.0f; break;
                    case 5: r.ph[(size_t) f.idx] = std::round (u * 100.0f) / 100.0f; break;
                    case 6: r.dc[(size_t) f.idx] = std::round ((u * 2.0f - 1.0f) * 100.0f) / 100.0f; break;
                    case 7: r.semi[(size_t) f.idx] = std::round ((u * 48.0f - 24.0f) * 10.0f) / 10.0f; break;
                }
            }
            void resetField (const Field& f)
            {
                switch (f.kind) {
                    case 0: r.n = 1; break; case 1: r.size = 1.0f; break; case 2: r.duty = 0.5f; break; case 3: r.mix = 1.0f; break;
                    case 4: r.lvl[(size_t) f.idx] = 1.0f; break; case 5: r.ph[(size_t) f.idx] = 0.0f; break;
                    case 6: r.dc[(size_t) f.idx] = 0.0f; break; case 7: r.semi[(size_t) f.idx] = 0.0f; break; case 8: r.shp[(size_t) f.idx] = 0; break;
                }
            }
            juce::String text (const Field& f) const
            {
                switch (f.kind) {
                    case 0: return "STEPS " + juce::String (r.n);
                    case 1: return "SIZE " + juce::String (r.size, 2);
                    case 2: return "DUTY " + juce::String (r.duty, 2);
                    case 3: return "MIX " + juce::String (juce::roundToInt (r.mix * 100.0f)) + "%";
                    case 4: return juce::String (r.lvl[(size_t) f.idx], 2);
                    case 5: return juce::String (r.ph[(size_t) f.idx], 2);
                    case 6: return juce::String (r.dc[(size_t) f.idx], 2);
                    case 7: return juce::String (r.semi[(size_t) f.idx], 1);
                    case 8: return razorShapes[juce::jlimit (0, 4, r.shp[(size_t) f.idx])];
                    case 9: return r.pol ? "CONST POL: ON" : "CONST POL: OFF";
                    case 10: return r.all ? "ALL FRAMES" : "THIS FRAME";
                    case 11: return "APPLY";
                    case 12: return "RESET";
                }
                return {};
            }
            void paint (juce::Graphics& g) override
            {
                g.fillAll (deep); g.setFont (font (8.0f, true));
                for (auto& f : fields)
                    if (f.idx == 0 && f.kind >= 4 && f.kind <= 8)
                    {
                        const char* nm = f.kind == 8 ? "SHAPE" : f.kind == 4 ? "LEVEL" : f.kind == 5 ? "PHASE" : f.kind == 6 ? "DC" : "TUNE";
                        g.setColour (dim); g.drawText (nm, 6, f.rc.getY(), 40, f.rc.getHeight(), juce::Justification::centredLeft);
                    }
                for (auto& f : fields)
                {
                    auto rc = f.rc.toFloat(); const bool dimmed = f.kind >= 4 && f.kind <= 8 && f.idx >= r.n;
                    const bool tog = f.kind >= 9, on = (f.kind == 9 && r.pol) || (f.kind == 10 && r.all) || f.kind == 11;
                    if (tog || f.kind == 8) { paintButton (g, rc.reduced (0.5f), on, false, false, 2.0f); }
                    else
                    {
                        g.setColour (panel2); g.fillRoundedRectangle (rc, 2.0f);
                        const bool bip = f.kind == 4 || f.kind == 6 || f.kind == 7; const float u = get (f), zero = bip ? 0.5f : 0.0f;
                        g.setColour (juce::Colour (0xffff3e30).withAlpha (dimmed ? 0.18f : 0.7f));
                        const float x0 = rc.getX() + rc.getWidth() * juce::jmin (u, zero), x1 = rc.getX() + rc.getWidth() * juce::jmax (u, zero);
                        g.fillRoundedRectangle (x0, rc.getY() + 1.0f, juce::jmax (1.5f, x1 - x0), rc.getHeight() - 2.0f, 1.5f);
                    }
                    g.setColour (on ? juce::Colours::white : dimmed ? dim.withAlpha (0.4f) : ink); g.setFont (font (8.0f, true));
                    g.drawText (text (f), f.rc, juce::Justification::centred);
                }
            }
            int hit (juce::Point<int> p) const { for (size_t i = 0; i < fields.size(); ++i) if (fields[i].rc.contains (p)) return (int) i; return -1; }
            void mouseDown (const juce::MouseEvent& e) override
            {
                drag = hit (e.getPosition()); if (drag < 0) return; auto& f = fields[(size_t) drag];
                if (f.kind == 9) { r.pol = ! r.pol; drag = -1; }
                else if (f.kind == 10) { r.all = ! r.all; drag = -1; }
                else if (f.kind == 11) { drag = -1; if (onApply) onApply(); return; }
                else if (f.kind == 12) { r.reset(); drag = -1; }
                else if (f.kind == 8) { r.shp[(size_t) f.idx] = (r.shp[(size_t) f.idx] + 1) % 5; drag = -1; }
                else if (e.getNumberOfClicks() > 1) { resetField (f); drag = -1; }
                else set (f, (float) (e.x - f.rc.getX()) / (float) f.rc.getWidth());
                repaint(); if (onChange) onChange();
            }
            void mouseDrag (const juce::MouseEvent& e) override
            {
                if (drag < 0) return; auto& f = fields[(size_t) drag];
                set (f, (float) (e.x - f.rc.getX()) / (float) f.rc.getWidth()); repaint(); if (onChange) onChange();
            }
            void mouseUp (const juce::MouseEvent&) override { drag = -1; }
        };
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
            razorBtn = add ("RAZOR", [this] { razor.setVisible (! razor.isVisible()); razorBtn->accent = razor.isVisible(); razorBtn->repaint(); owner.repaint(); });
            add ("UNDO", [this] { if (! undoFr.empty()) { fr = undoFr; undoFr.clear(); sel = juce::jmin (sel, (int) fr.size() - 1); commit(); harmDirty = true; owner.repaint(); } });
            owner.addChildComponent (razor);
            razor.onChange = [this] { owner.repaint(); };
            razor.onApply = [this] { applyRazor(); };
        }

        void applyRazor()
        {
            undoFr = fr;
            for (int f = 0; f < (int) fr.size(); ++f)
                if (razor.r.all || f == sel) { Frame o; razorRender (fr[(size_t) f], razor.r, o); fr[(size_t) f] = std::move (o); }
            commit(); harmDirty = true; owner.repaint();
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
            razor.setBounds (harm);
        }
        float frameX (int x0, int w, int i) const { return (float) x0 + (float) w * (float) i / (float) N; }
        void paintAll (juce::Graphics& g)
        {
            g.fillAll (panel); g.setColour (deep); g.fillRect (water); g.fillRect (draw); g.fillRect (harm);
            g.setFont (font (9.0f, true)); g.setColour (dim);
            g.drawText ("WATERFALL  -  " + juce::String ((int) fr.size()) + " FRAMES  -  CLICK TO SELECT", water.getX(), water.getY() - 13, water.getWidth(), 11, juce::Justification::left);
            g.drawText ("FRAME " + juce::String (sel + 1) + "  -  DRAW WITH THE MOUSE", draw.getX(), draw.getY() - 13, draw.getWidth(), 11, juce::Justification::left);
            g.drawText (razor.isVisible() ? juce::String ("RAZOR  -  CUTS THE CYCLE INTO SEGMENTS  -  DRAG A FIELD, DOUBLE-CLICK RESETS, APPLY BAKES IT") : "HARMONICS 1.." + juce::String (NH) + "  -  DRAG TO SET", harm.getX(), harm.getY() - 13, harm.getWidth(), 11, juce::Justification::left);
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
            if (razor.isVisible())   // live preview of the razor result
            {
                Frame o; razorRender (cur(), razor.r, o); juce::Path pp;
                for (int i = 0; i < N; i += 2) { const float x = frameX (draw.getX(), draw.getWidth(), i), y = (float) draw.getCentreY() - o[(size_t) i] * (float) draw.getHeight() * 0.45f; if (i == 0) pp.startNewSubPath (x, y); else pp.lineTo (x, y); }
                g.setColour (juce::Colours::white.withAlpha (0.8f)); g.strokePath (pp, juce::PathStrokeType (1.2f));
            }
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
        RazorPanel razor; Btn* razorBtn = nullptr; std::vector<Frame> undoFr;
        WavetableEditor& owner; Ctx& ctx; SoundMemory& mem; int os;
        juce::OwnedArray<Btn> buttons; Btn* closeBtn = nullptr;
        std::vector<Frame> fr; int sel = 0; juce::String name;
        std::array<float, NH> mags {}; bool harmDirty = true, dirty = false, selfWrite = false; int mode = 0, lastI = -1; float lastV = 0;
    };

    WavetableEditor::WavetableEditor (Ctx& c, SoundMemory& m, int osc) : impl (new Impl (*this, c, m, osc)) { m.addChangeListener (this); setVisible (false); setName ("wavetableEditor"); }
    WavetableEditor::~WavetableEditor() { impl->mem.removeChangeListener (this); }
    void WavetableEditor::open() { impl->load(); impl->harmDirty = true; setVisible (true); toFront (false); resized(); repaint(); }
    void WavetableEditor::showRazor (bool on) { impl->razor.setVisible (on); impl->razorBtn->accent = on; impl->razorBtn->repaint(); repaint(); }
    void WavetableEditor::setRazor (int steps, float duty, int seg, float semi, float level, float phase, int shape)
    {
        auto& r = impl->razor.r; r.n = steps; r.duty = duty; r.semi[(size_t) seg] = semi; r.lvl[(size_t) seg] = level; r.ph[(size_t) seg] = phase; r.shp[(size_t) seg] = shape; repaint();
    }
    void WavetableEditor::paint (juce::Graphics& g) { impl->paintAll (g); }
    void WavetableEditor::resized() { impl->layout(); }
    void WavetableEditor::changeListenerCallback (juce::ChangeBroadcaster*) { if (isVisible() && ! impl->selfWrite) { impl->load(); impl->harmDirty = true; repaint(); } }
    void WavetableEditor::mouseDown (const juce::MouseEvent& e) { impl->pointer (e.getPosition(), true); }
    void WavetableEditor::mouseDrag (const juce::MouseEvent& e) { impl->pointer (e.getPosition(), false); }
    void WavetableEditor::mouseUp (const juce::MouseEvent&) { if (impl->dirty) { impl->dirty = false; impl->commit(); } impl->mode = 0; }
}
