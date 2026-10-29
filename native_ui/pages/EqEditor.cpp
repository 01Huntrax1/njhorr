#include "EqEditor.h"
#include <algorithm>
#include <cmath>

namespace njo
{
    using namespace theme;

    namespace
    {
        constexpr double kSr = 48000.0, kFLo = 20.0, kFHi = 20000.0, kDbRange = 24.0;

        juce::Colour typeColour (int t) { return juce::Colour::fromHSV ((float) t / 15.0f * 0.85f, 0.62f, 0.98f, 1.0f); }

        // a small framed value box: drag sideways (shift = fine), mouse wheel, double-click resets
        struct Field : public juce::Component
        {
            juce::String label; std::function<double()> get; std::function<void (double)> set; std::function<juce::String (double)> fmt;
            double lo = 0, hi = 1, def = 0; bool logScale = false; int steps = 0; std::function<void()> onBegin, onEnd; bool hover = false, active = false;
            double norm (double v) const { return logScale ? std::log (juce::jlimit (lo, hi, v) / lo) / std::log (hi / lo) : (juce::jlimit (lo, hi, v) - lo) / (hi - lo); }
            double denorm (double n) const
            {
                n = juce::jlimit (0.0, 1.0, n); double v = logScale ? lo * std::pow (hi / lo, n) : lo + n * (hi - lo);
                if (steps > 0) v = lo + std::round ((v - lo) / (double) steps) * steps;
                return juce::jlimit (lo, hi, v);
            }
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintInset (g, r, 3.0f);
                const double v = get ? get() : 0.0;
                g.setColour (red.withAlpha (hover || active ? 0.55f : 0.35f)); g.fillRect (r.getX() + 2, r.getBottom() - 4.0f, (r.getWidth() - 4) * (float) norm (v), 2.0f);
                g.setColour (dim); g.setFont (font (7.5f, true).withExtraKerningFactor (0.12f));
                g.drawText (label, r.withTrimmedLeft (6).withHeight (13), juce::Justification::centredLeft);
                g.setColour (ink); g.setFont (mono (10.5f, true));
                g.drawText (fmt ? fmt (v) : juce::String (v, 2), r.withTrimmedTop (11).reduced (6, 0), juce::Justification::centredLeft);
            }
            void mouseEnter (const juce::MouseEvent&) override { hover = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { hover = false; repaint(); }
            void mouseDown (const juce::MouseEvent&) override { active = true; start = norm (get ? get() : 0.0); if (onBegin) onBegin(); repaint(); }
            void mouseDrag (const juce::MouseEvent& e) override
            {
                const double span = e.mods.isShiftDown() ? 900.0 : 180.0;
                if (set) set (denorm (start + (double) e.getDistanceFromDragStartX() / span));
                repaint();
            }
            void mouseUp (const juce::MouseEvent&) override { active = false; if (onEnd) onEnd(); repaint(); }
            void mouseDoubleClick (const juce::MouseEvent&) override { if (onBegin) onBegin(); if (set) set (def); if (onEnd) onEnd(); repaint(); }
            void mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w) override
            {
                if (onBegin) onBegin();
                const double stepN = steps > 0 ? (double) steps / (hi - lo) : (e.mods.isShiftDown() ? 0.004 : 0.02);
                if (set) set (denorm (norm (get ? get() : 0.0) + (w.deltaY > 0 ? stepN : -stepN)));
                if (onEnd) onEnd(); repaint();
            }
            double start = 0;
        };

        struct Btn : public juce::Component
        {
            juce::String text; bool on = false, over = false; std::function<void()> click;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintButton (g, r, on, over, false, 3.0f);
                g.setColour (ink); g.setFont (font (8.5f, true).withExtraKerningFactor (0.05f));
                g.drawText (text, r.reduced (4, 0).toNearestInt(), juce::Justification::centred, true);
            }
            void mouseEnter (const juce::MouseEvent&) override { over = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { over = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };
    }

    struct EqEditor::Impl
    {
        Impl (EqEditor& o, Ctx& c, SoundMemory& m) : owner (o), ctx (c), mem (m)
        {
            auto addBtn = [this] (Btn& b, const juce::String& t, std::function<void()> fn) { b.text = t; b.click = std::move (fn); owner.addAndMakeVisible (b); };
            addBtn (typeBtn, "", [this] { typeMenu(); });
            addBtn (hsetBtn, "", [this] { hsetMenu(); });
            addBtn (chBtn, "", [this] { chMenu(); });
            addBtn (onBtn, "ON", [this] { if (valid()) { b().on = ! b().on; changed(); } });
            addBtn (delBtn, "DELETE", [this] { removeBand (sel); });
            addBtn (addBand, "+ BAND", [this] { addAt (1000.0, 0.0, 0); });
            addBtn (presetBtn, "PRESETS", [this] { presetMenu(); });

            auto bandField = [this] (Field& f, const juce::String& name, double lo, double hi, double def, bool lg, int steps, std::function<double()> get, std::function<void (double)> set, std::function<juce::String (double)> fmt)
            {
                f.label = name; f.lo = lo; f.hi = hi; f.def = def; f.logScale = lg; f.steps = steps; f.get = std::move (get); f.fmt = std::move (fmt);
                f.set = [this, set = std::move (set)] (double v) { if (valid()) { set (v); changed(); } };
                owner.addAndMakeVisible (f);
            };
            bandField (fFreq, "FREQ", 20, 20000, 1000, true, 0, [this] { return valid() ? (double) b().hz : 1000.0; }, [this] (double v) { b().hz = (float) v; }, [] (double v) { return v >= 1000 ? juce::String (v / 1000.0, 2) + " kHz" : juce::String (juce::roundToInt (v)) + " Hz"; });
            bandField (fGain, "GAIN", -24, 24, 0, false, 0, [this] { return valid() ? (double) b().db : 0.0; }, [this] (double v) { b().db = (float) (std::abs (v) < 0.15 ? 0.0 : v); }, [] (double v) { return (v > 0 ? "+" : "") + juce::String (v, 1) + " dB"; });
            bandField (fQ, "Q", 0.1, 30, 1, true, 0, [this] { return valid() ? (double) b().q : 1.0; }, [this] (double v) { b().q = (float) v; }, [] (double v) { return juce::String (v, 2); });
            bandField (fHarm, "HARMONICS", 0, 16, 0, false, 1, [this] { return valid() ? (double) b().harm : 0.0; }, [this] (double v) { b().harm = (int) v; }, [] (double v) { return juce::String ((int) v); });
            bandField (fFall, "FALLOFF", 0, 1, 0.5, false, 0, [this] { return valid() ? (double) b().fall : 0.5; }, [this] (double v) { b().fall = (float) v; }, [] (double v) { return juce::String (juce::roundToInt ((0.4 + 0.6 * v) * 100)) + "% / step"; });

            // slot parameters (P1 output, P2 gain scale, P3 frequency shift, P4 Q scale, mix)
            auto slotField = [this] (Field& f, const juce::String& name, int off, double def, std::function<juce::String (double)> fmt)
            {
                f.label = name; f.lo = 0; f.hi = 1; f.def = def; f.fmt = std::move (fmt);
                f.get = [this, off] { return (double) ctx.get (base + off); };
                f.set = [this, off] (double v) { ctx.set (base + off, (float) v); };
                f.onBegin = [this, off] { ctx.begin (base + off); }; f.onEnd = [this, off] { ctx.end (base + off); };
                owner.addAndMakeVisible (f);
            };
            slotField (fOut, "OUTPUT", 4, 0.5, [] (double v) { const double d = (v - 0.5) * 36.0; return (d > 0 ? "+" : "") + juce::String (d, 1) + " dB"; });
            slotField (fScale, "GAIN SCALE", 5, 0.5, [] (double v) { return juce::String (juce::roundToInt (v * 200)) + "%"; });
            slotField (fShift, "FREQ SHIFT", 6, 0.5, [] (double v) { const double o = (v - 0.5) * 2.0; return (o > 0 ? "+" : "") + juce::String (o, 2) + " oct"; });
            slotField (fQs, "Q SCALE", 7, 0.5, [] (double v) { return "x" + juce::String (0.25 * std::pow (16.0, v), 2); });
            slotField (fMix, "MIX", 2, 1.0, [] (double v) { return juce::String (juce::roundToInt (v * 100)) + "%"; });
        }

        // ---- model ----
        bool valid() const { return sel >= 0 && sel < eq::MAXB && bands[(size_t) sel].used; }
        eq::Band& b() { return bands[(size_t) sel]; }
        int usedCount() const { int n = 0; for (auto& x : bands) if (x.used) ++n; return n; }
        eq::Scale scale() const
        {
            eq::Scale s; s.gain = ctx.get (base + 5) * 2.0; s.shift = std::pow (2.0, (ctx.get (base + 6) - 0.5) * 2.0); s.q = 0.25 * std::pow (16.0, (double) ctx.get (base + 7)); return s;
        }
        void load()
        {
            bands = {};
            if (auto* sl = mem.get (SoundMemory::EqBands, slot)) bands = eq::decode (sl->data);
            if (! valid()) { sel = -1; for (int i = 0; i < eq::MAXB; ++i) if (bands[(size_t) i].used) { sel = i; break; } }
            lastData = eq::encode (bands);
        }
        void changed() { dirty = true; owner.repaint(); if (! owner.isTimerRunning()) owner.startTimer (100); }
        void commit()
        {
            dirty = false;
            auto d = eq::encode (bands);
            if (usedCount() == 0) mem.clear (SoundMemory::EqBands, slot); else mem.set (SoundMemory::EqBands, slot, "EQ", {}, d);
            lastData = d;
        }
        int freeIndex() const { for (int i = 0; i < eq::MAXB; ++i) if (! bands[(size_t) i].used) return i; return -1; }
        void addAt (double hz, double db, int type)
        {
            const int i = freeIndex(); if (i < 0) return;
            eq::Band nb; nb.used = true; nb.on = true; nb.type = type; nb.hz = (float) juce::jlimit (20.0, 20000.0, hz); nb.db = (float) juce::jlimit (-24.0, 24.0, db); nb.q = (type == 3 || type == 5 || type == 4 || type == 6) ? 0.7071f : 1.0f;
            if (type == 11 || type == 12) { nb.db = 6.0f; nb.hz = 220.0f; }
            bands[(size_t) i] = nb; sel = i; changed();
        }
        void removeBand (int i) { if (i < 0 || i >= eq::MAXB) return; bands[(size_t) i] = {}; if (sel == i) { sel = -1; for (int k = 0; k < eq::MAXB; ++k) if (bands[(size_t) k].used) { sel = k; break; } } changed(); }

        // ---- menus ----
        void typeMenu()
        {
            if (! valid()) return;
            juce::PopupMenu m;
            for (int t = 0; t < eq::NTYPES; ++t) m.addItem (t + 1, eq::typeName (t), true, b().type == t);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&typeBtn), [this] (int r) { if (r > 0 && valid()) { b().type = r - 1; if (eq::isComb (b().type) && b().db == 0) b().db = 6; changed(); } });
        }
        void hsetMenu()
        {
            if (! valid()) return;
            juce::PopupMenu m; const char* n[] = { "All harmonics", "Odd harmonics (3f, 5f ...)", "Even harmonics (2f, 4f ...)" };
            for (int i = 0; i < 3; ++i) m.addItem (i + 1, n[i], true, b().hset == i);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&hsetBtn), [this] (int r) { if (r > 0 && valid()) { b().hset = r - 1; changed(); } });
        }
        void chMenu()
        {
            if (! valid()) return;
            juce::PopupMenu m; const char* n[] = { "Stereo", "Left", "Right", "Mid", "Side" };
            for (int i = 0; i < 5; ++i) m.addItem (i + 1, n[i], true, b().ch == i);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&chBtn), [this] (int r) { if (r > 0 && valid()) { b().ch = r - 1; changed(); } });
        }
        void setBands (std::vector<eq::Band> v) { bands = {}; for (size_t i = 0; i < v.size() && i < (size_t) eq::MAXB; ++i) { bands[i] = v[i]; bands[i].used = true; bands[i].on = true; } sel = v.empty() ? -1 : 0; changed(); }
        static eq::Band mk (int type, float hz, float db, float q, int harm = 0, float fall = 0.5f, int hset = 0, int ch = 0) { eq::Band x; x.type = type; x.hz = hz; x.db = db; x.q = q; x.harm = harm; x.fall = fall; x.hset = hset; x.ch = ch; return x; }
        void presetMenu()
        {
            juce::PopupMenu m;
            m.addItem (1, "Clear all bands"); m.addSeparator();
            m.addItem (2, "Vocal clean-up"); m.addItem (3, "Smile curve"); m.addItem (4, "Telephone"); m.addItem (5, "Warm harmonic bass (harmonics)"); m.addItem (6, "Comb flange (comb filter)");
            m.addItem (7, "Air and clarity"); m.addItem (8, "Mid / side widener"); m.addItem (9, "Tilt darker");
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&presetBtn), [this] (int r)
            {
                switch (r)
                {
                    case 1: setBands ({}); break;
                    case 2: setBands ({ mk (4, 90, 0, 0.7071f), mk (0, 300, -3, 1.2f), mk (0, 3200, 2.5f, 0.9f), mk (2, 11000, 2.0f, 0.7f) }); break;
                    case 3: setBands ({ mk (1, 120, 5, 0.7f), mk (0, 900, -3, 0.8f), mk (2, 7500, 5, 0.7f) }); break;
                    case 4: setBands ({ mk (4, 450, 0, 0.9f), mk (6, 3400, 0, 0.7071f), mk (0, 1500, 5, 1.0f) }); break;
                    case 5: setBands ({ mk (0, 70, 6, 3.0f, 6, 0.75f, 0), mk (3, 30, 0, 0.7071f) }); break;
                    case 6: setBands ({ mk (11, 220, 8, 1.0f) }); break;
                    case 7: setBands ({ mk (3, 40, 0, 0.7071f), mk (0, 5000, 2, 0.8f), mk (2, 12000, 4, 0.6f) }); break;
                    case 8: setBands ({ mk (0, 250, -3, 0.8f, 0, 0.5f, 0, 4), mk (2, 9000, 4, 0.7f, 0, 0.5f, 0, 4), mk (1, 120, 2, 0.7f, 0, 0.5f, 0, 3) }); break;
                    case 9: setBands ({ mk (9, 800, -6, 0.5f) }); break;
                    default: break;
                }
            });
        }

        // ---- geometry ----
        juce::Rectangle<int> curve, chipRow, bandRow, slotRow;
        void layout()
        {
            auto r = owner.getLocalBounds();
            slotRow = r.removeFromBottom (40); r.removeFromBottom (4);
            bandRow = r.removeFromBottom (40); r.removeFromBottom (4);
            chipRow = r.removeFromBottom (24); r.removeFromBottom (4);
            curve = r;
            int x = bandRow.getX();
            auto take = [&] (juce::Component& c, int w) { c.setBounds (x, bandRow.getY(), w, bandRow.getHeight()); x += w + 6; };
            take (typeBtn, 112); take (fFreq, 88); take (fGain, 80); take (fQ, 60); take (fHarm, 76); take (fFall, 92); take (hsetBtn, 56); take (chBtn, 64); take (onBtn, 40); take (delBtn, 60);
            for (auto* bt : { &typeBtn, &hsetBtn, &chBtn, &onBtn, &delBtn }) bt->setBounds (bt->getBounds().reduced (0, 6));
            x = slotRow.getX(); const int sw = (slotRow.getWidth() - 4 * 6) / 5;
            for (auto* f : { &fOut, &fScale, &fShift, &fQs, &fMix }) { f->setBounds (x, slotRow.getY(), sw, slotRow.getHeight()); x += sw + 6; }
            presetBtn.setBounds (chipRow.getRight() - 76, chipRow.getY(), 76, chipRow.getHeight());
            addBand.setBounds (chipRow.getRight() - 76 - 6 - 70, chipRow.getY(), 70, chipRow.getHeight());
        }
        juce::Rectangle<float> plot() const { return curve.toFloat().reduced (34.0f, 10.0f).withTrimmedBottom (8.0f); }
        float xOf (double f) const { auto p = plot(); return p.getX() + (float) (std::log (juce::jlimit (kFLo, kFHi, f) / kFLo) / std::log (kFHi / kFLo)) * p.getWidth(); }
        float yOf (double db) const { auto p = plot(); return p.getY() + (float) (0.5 - 0.5 * juce::jlimit (-kDbRange, kDbRange, db) / kDbRange) * p.getHeight(); }
        double fOfX (float x) const { auto p = plot(); return kFLo * std::pow (kFHi / kFLo, juce::jlimit (0.0, 1.0, (double) (x - p.getX()) / p.getWidth())); }
        double dbOfY (float y) const { auto p = plot(); return (0.5 - (double) (y - p.getY()) / p.getHeight()) * 2.0 * kDbRange; }
        // where a band's node sits: at its effective frequency and gain (the slot's gain scale and frequency shift applied)
        juce::Point<float> nodeOf (const eq::Band& x) const
        {
            auto sc = scale();
            return { xOf (x.hz * sc.shift), yOf (eq::hasGain (x.type) ? x.db * sc.gain : 0.0) };
        }
        int nodeAt (juce::Point<float> p) const
        {
            int best = -1; float bd = 12.0f * 12.0f;
            for (int i = 0; i < eq::MAXB; ++i)
                if (bands[(size_t) i].used) { auto n = nodeOf (bands[(size_t) i]); float d = n.getDistanceSquaredFrom (p); if (d < bd) { bd = d; best = i; } }
            return best;
        }

        void paintAll (juce::Graphics& g)
        {
            auto p = plot();
            paintInset (g, curve.toFloat(), 4.0f);
            auto sc = scale();
            // grid
            g.setFont (mono (7.5f, false));
            for (double f : { 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0, 8000.0, 9000.0, 10000.0, 20000.0 })
            {
                const bool major = (f == 20 || f == 100 || f == 1000 || f == 10000);
                g.setColour (juce::Colours::white.withAlpha (major ? 0.14f : 0.05f)); g.drawVerticalLine ((int) xOf (f), p.getY(), p.getBottom());
            }
            for (double f : { 20.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0, 10000.0, 20000.0 })
            {
                g.setColour (dim); g.drawText (f >= 1000 ? juce::String (f / 1000.0, f >= 10000 ? 0 : 0) + "k" : juce::String ((int) f), juce::Rectangle<float> (xOf (f) - 16, p.getBottom() - 11, 32, 10), juce::Justification::centred);
            }
            for (int d = -24; d <= 24; d += 6)
            {
                g.setColour (juce::Colours::white.withAlpha (d == 0 ? 0.25f : 0.06f)); g.drawHorizontalLine ((int) yOf (d), p.getX(), p.getRight());
                g.setColour (dim); g.drawText ((d > 0 ? "+" : "") + juce::String (d), juce::Rectangle<float> (curve.getX() + 2.0f, yOf (d) - 5, 28, 10), juce::Justification::centredRight);
            }
            // selected band curve
            const int N = 360;
            auto pathOf = [&] (const std::function<double (double)>& dbAt)
            {
                juce::Path path;
                for (int i = 0; i <= N; ++i) { const double f = kFLo * std::pow (kFHi / kFLo, (double) i / N); const float x = p.getX() + p.getWidth() * (float) i / N, y = yOf (dbAt (f)); if (i == 0) path.startNewSubPath (x, y); else path.lineTo (x, y); }
                return path;
            };
            if (valid() && b().on)
            {
                auto bp = pathOf ([&] (double f) { return eq::bandDb (b(), f, sc, kSr); });
                g.setColour (typeColour (b().type).withAlpha (0.55f)); g.strokePath (bp, juce::PathStrokeType (1.2f));
            }
            // total response
            auto total = pathOf ([&] (double f) { double s = 0; for (auto& x : bands) if (x.used && x.on) s += eq::bandDb (x, f, sc, kSr); return s; });
            juce::Path fill (total); fill.lineTo (p.getRight(), yOf (0)); fill.lineTo (p.getX(), yOf (0)); fill.closeSubPath();
            g.setColour (red.withAlpha (0.13f)); g.fillPath (fill);
            g.setColour (red.withAlpha (0.28f)); g.strokePath (total, juce::PathStrokeType (5.0f));
            g.setColour (juce::Colour (0xffff7864)); g.strokePath (total, juce::PathStrokeType (1.8f));
            // harmonic markers of the selected band
            if (valid() && eq::hasHarmonics (b().type) && b().harm > 0 && b().on)
            {
                for (auto& s : eq::sections (b(), sc, kSr)) { g.setColour (typeColour (b().type).withAlpha (0.5f)); g.drawLine (xOf (s.f), p.getBottom() - 14, xOf (s.f), yOf (s.g), 1.0f); }
            }
            // nodes
            for (int i = 0; i < eq::MAXB; ++i)
            {
                auto& x = bands[(size_t) i]; if (! x.used) continue;
                auto n = nodeOf (x); const bool isSel = i == sel, isHot = i == hot;
                const auto col = typeColour (x.type).withAlpha (x.on ? 1.0f : 0.35f);
                g.setColour (juce::Colours::black.withAlpha (0.6f)); g.fillEllipse (n.x - 8.5f, n.y - 8.5f, 17.0f, 17.0f);
                g.setColour (col); g.drawEllipse (n.x - 7.5f, n.y - 7.5f, 15.0f, 15.0f, isSel ? 2.6f : (isHot ? 2.0f : 1.4f));
                if (isSel) { g.setColour (col.withAlpha (0.35f)); g.fillEllipse (n.x - 7.5f, n.y - 7.5f, 15.0f, 15.0f); }
                g.setColour (juce::Colours::white.withAlpha (x.on ? 0.95f : 0.4f)); g.setFont (mono (8.0f, true));
                g.drawText (juce::String (i + 1), juce::Rectangle<float> (n.x - 8, n.y - 6, 16, 12), juce::Justification::centred);
            }
            g.setColour (dim); g.setFont (font (8.0f, false));
            g.drawText ("double-click: add band  -  drag a node: frequency and gain (Q for cuts)  -  wheel: Q  -  shift + wheel: harmonics  -  double-click a node: delete  -  right-click: menu",
                        curve.withTrimmedLeft (36).withHeight (14).translated (0, 1), juce::Justification::centredLeft, true);
            // band chips
            int cx = chipRow.getX();
            for (int i = 0; i < eq::MAXB; ++i)
            {
                auto& x = bands[(size_t) i]; if (! x.used) continue;
                juce::Rectangle<float> r ((float) cx, (float) chipRow.getY(), 26.0f, (float) chipRow.getHeight());
                paintButton (g, r, i == sel, false, false, 3.0f);
                g.setColour (typeColour (x.type).withAlpha (x.on ? 1.0f : 0.3f)); g.fillRect (r.getX() + 3, r.getBottom() - 4, r.getWidth() - 6, 2.0f);
                g.setColour (ink); g.setFont (font (9.0f, true)); g.drawText (juce::String (i + 1), r, juce::Justification::centred);
                chipX[i] = cx; cx += 28;
            }
            if (usedCount() == 0) { g.setColour (dim); g.setFont (font (9.0f, false)); g.drawText ("No bands yet: double-click the curve, use + BAND or load a preset.", chipRow.withWidth (chipRow.getWidth() - 170), juce::Justification::centredLeft); }
        }

        void syncUi()
        {
            const bool v = valid();
            typeBtn.text = v ? eq::typeName (b().type) : "-";
            hsetBtn.text = v ? (const char* const[]) { "ALL", "ODD", "EVEN" }[b().hset] : "-";
            chBtn.text = v ? (const char* const[]) { "STEREO", "LEFT", "RIGHT", "MID", "SIDE" }[b().ch] : "-";
            onBtn.on = v && b().on;
            const bool gain = v && eq::hasGain (b().type), harm = v && eq::hasHarmonics (b().type);
            fGain.setAlpha (gain ? 1.0f : 0.35f); fHarm.setAlpha (harm ? 1.0f : 0.35f); fFall.setAlpha (harm ? 1.0f : 0.35f); hsetBtn.setAlpha (harm ? 1.0f : 0.35f);
            for (auto* c : std::initializer_list<juce::Component*> { &typeBtn, &fFreq, &fGain, &fQ, &fHarm, &fFall, &hsetBtn, &chBtn, &onBtn, &delBtn }) c->setEnabled (v);
            fQ.setAlpha (v && ! eq::isComb (b().type) ? 1.0f : 0.35f);
        }

        EqEditor& owner; Ctx& ctx; SoundMemory& mem;
        int slot = 0, base = 0, sel = -1, hot = -1; bool dirty = false, dragging = false;
        eq::Bands bands {}; std::vector<float> lastData; int chipX[eq::MAXB] = {};
        Btn typeBtn, hsetBtn, chBtn, onBtn, delBtn, addBand, presetBtn;
        Field fFreq, fGain, fQ, fHarm, fFall, fOut, fScale, fShift, fQs, fMix;
    };

    EqEditor::EqEditor (Ctx& c, SoundMemory& m) : impl (new Impl (*this, c, m)) { c.addListener (this); m.addChangeListener (this); setName ("eqEditor"); }
    EqEditor::~EqEditor() { impl->mem.removeChangeListener (this); impl->ctx.removeListener (this); stopTimer(); if (impl->dirty) impl->commit(); }
    void EqEditor::setSlot (int g, int base) { if (impl->dirty) impl->commit(); impl->slot = g; impl->base = base; impl->load(); impl->syncUi(); resized(); repaint(); }
    void EqEditor::paint (juce::Graphics& g) { impl->syncUi(); impl->paintAll (g); }
    void EqEditor::resized() { impl->layout(); }
    void EqEditor::timerCallback() { if (impl->dirty) impl->commit(); stopTimer(); }
    void EqEditor::paramChanged (int num, float) { if (isVisible() && num >= impl->base && num < impl->base + 10) repaint(); }
    void EqEditor::changeListenerCallback (juce::ChangeBroadcaster*)
    {
        if (impl->dirty || impl->dragging) return;
        auto* sl = impl->mem.get (SoundMemory::EqBands, impl->slot);
        const auto now = sl ? sl->data : std::vector<float>();
        if (now.empty() ? impl->usedCount() != 0 : now != impl->lastData) { impl->load(); repaint(); }
    }
    void EqEditor::mouseMove (const juce::MouseEvent& e) { const int h = impl->nodeAt (e.position); if (h != impl->hot) { impl->hot = h; repaint(); } }
    void EqEditor::mouseExit (const juce::MouseEvent&) { if (impl->hot != -1) { impl->hot = -1; repaint(); } }
    void EqEditor::mouseDown (const juce::MouseEvent& e)
    {
        auto& I = *impl;
        // band chips
        if (I.chipRow.contains (e.getPosition()))
        {
            for (int i = 0; i < eq::MAXB; ++i) if (I.bands[(size_t) i].used && e.x >= I.chipX[i] && e.x < I.chipX[i] + 26) { I.sel = i; repaint(); return; }
            return;
        }
        if (! I.curve.contains (e.getPosition())) return;
        const int n = I.nodeAt (e.position);
        if (e.mods.isPopupMenu())
        {
            if (n >= 0)
            {
                I.sel = n; repaint();
                juce::PopupMenu m; m.addItem (1, I.b().on ? "Switch off" : "Switch on"); m.addItem (2, "Duplicate"); m.addItem (3, "Delete");
                m.showMenuAsync (juce::PopupMenu::Options(), [this, n] (int r)
                {
                    auto& I2 = *impl; if (! I2.bands[(size_t) n].used) return;
                    if (r == 1) { I2.bands[(size_t) n].on = ! I2.bands[(size_t) n].on; I2.changed(); }
                    else if (r == 2) { const int f = I2.freeIndex(); if (f >= 0) { I2.bands[(size_t) f] = I2.bands[(size_t) n]; I2.bands[(size_t) f].hz = juce::jmin (20000.0f, I2.bands[(size_t) f].hz * 1.2f); I2.sel = f; I2.changed(); } }
                    else if (r == 3) I2.removeBand (n);
                });
            }
            else
            {
                const double hz = I.fOfX (e.position.x), db = I.dbOfY (e.position.y);
                juce::PopupMenu m; for (int t = 0; t < eq::NTYPES; ++t) m.addItem (t + 1, juce::String ("Add ") + eq::typeName (t));
                m.showMenuAsync (juce::PopupMenu::Options(), [this, hz, db] (int r) { if (r > 0) impl->addAt (hz / impl->scale().shift, db, r - 1); });
            }
            return;
        }
        if (n >= 0) { I.sel = n; I.dragging = true; repaint(); }
    }
    void EqEditor::mouseDrag (const juce::MouseEvent& e)
    {
        auto& I = *impl;
        if (! I.dragging || ! I.valid()) return;
        auto sc = I.scale();
        auto& b = I.b();
        b.hz = (float) juce::jlimit (20.0, 20000.0, I.fOfX (e.position.x) / sc.shift);
        if (eq::hasGain (b.type))
        {
            double gs = std::abs (sc.gain) < 0.05 ? 1.0 : sc.gain;
            double v = juce::jlimit (-24.0, 24.0, I.dbOfY (e.position.y) / gs);
            b.db = (float) (std::abs (v) < 0.3 ? 0.0 : v);
        }
        else
        {
            const double q = 0.1 * std::pow (300.0, juce::jlimit (0.0, 1.0, 0.5 - (double) (e.position.y - I.plot().getCentreY()) / I.plot().getHeight() * 1.0 + 0.1));
            b.q = (float) juce::jlimit (0.1, 30.0, q);
        }
        I.changed();
    }
    void EqEditor::mouseUp (const juce::MouseEvent&) { impl->dragging = false; if (impl->dirty) impl->commit(); }
    void EqEditor::mouseDoubleClick (const juce::MouseEvent& e)
    {
        auto& I = *impl;
        if (! I.curve.contains (e.getPosition())) return;
        const int n = I.nodeAt (e.position);
        if (n >= 0) { I.removeBand (n); return; }
        I.addAt (I.fOfX (e.position.x) / I.scale().shift, I.dbOfY (e.position.y) / (std::abs (I.scale().gain) < 0.05 ? 1.0 : I.scale().gain), 0);
    }
    void EqEditor::mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w)
    {
        auto& I = *impl;
        int n = I.nodeAt (e.position); if (n < 0) n = I.sel;
        if (n < 0 || ! I.bands[(size_t) n].used) return;
        I.sel = n; auto& b = I.b();
        if (e.mods.isShiftDown() && eq::hasHarmonics (b.type)) b.harm = juce::jlimit (0, 16, b.harm + (w.deltaY > 0 ? 1 : -1));
        else b.q = (float) juce::jlimit (0.1, 30.0, b.q * (w.deltaY > 0 ? 1.12 : 1.0 / 1.12));
        I.changed();
    }
}
