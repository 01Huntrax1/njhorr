#include "Editors.h"
#include "OscDisplays.h"
#include "../NjoPhys.h"
#include <algorithm>
#include <cmath>

namespace njo
{
    using namespace theme;

    namespace
    {
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

        void header (juce::Graphics& g, juce::Rectangle<int> r, const juce::String& t)
        {
            g.setColour (red); g.fillRect (juce::Rectangle<float> ((float) r.getX() + 12, (float) r.getY() + 13, 7, 7));
            g.setColour (ink); g.setFont (impact (13.0f));
            g.drawText (t.toUpperCase(), r.getX() + 26, r.getY() + 6, 560, 20, juce::Justification::centredLeft);
        }
    }

    // ====================================================================================================================== TableEditor
    struct TableEditor::Impl
    {
        Impl (TableEditor& o, Ctx& c, SoundMemory& m, int osc, bool f) : owner (o), ctx (c), mem (m), os (osc), filter (f)
        {
            auto add = [this] (const juce::String& t, std::function<void()> fn, bool accent = false)
            {
                auto* b = buttons.add (new Btn()); b->text = t; b->click = std::move (fn); b->accent = accent; owner.addAndMakeVisible (b); return b;
            };
            closeBtn = add ("CLOSE", [this] { flush(); owner.setVisible (false); if (owner.onClose) owner.onClose(); }, true);
            add ("PREV", [this] { select (cur - 1); });
            add ("NEXT", [this] { select (cur + 1); });
            add ("ADD FRAME", [this] { addFrame(); });
            add ("DELETE", [this] { delFrame(); });
            add ("MORPH ALL", [this] { morphAll(); });
            add ("SMOOTH", [this] { edit ([this] (float* v) { smooth (v); }); });
            add ("INVERT", [this] { edit ([] (float* v) { for (int i = 0; i < 512; ++i) v[i] = -v[i]; }); });
            add ("FLIP", [this] { edit ([] (float* v) { std::reverse (v, v + 512); }); });
            add ("NORMALIZE", [this] { edit ([] (float* v) { float p = 0; for (int i = 0; i < 512; ++i) p = juce::jmax (p, std::abs (v[i])); if (p > 1.0e-4f) for (int i = 0; i < 512; ++i) v[i] /= p; }); });
            add ("RANDOM", [this] { edit ([this] (float* v) { randomise (v); }); });
            if (filter)
                for (auto* n : { "LOW PASS", "HIGH PASS", "BAND PASS", "NOTCH", "COMB", "FORMANT" })
                    add (n, [this, s = juce::String (n)] { preset (s); });
            else
                for (auto* n : { "LINEAR", "SOFT", "HARD", "FOLD", "ASYM", "STAIRS" })
                    add (n, [this, s = juce::String (n)] { preset (s); });
        }

        int frames() const { return (int) d.size() / 512; }
        void load()
        {
            if (auto* sl = mem.get (filter ? SoundMemory::FilterTable : SoundMemory::ShaperTable, os); sl && sl->data.size() >= 512)
            {
                d = sl->data; d.resize ((d.size() / 512) * 512); name = sl->name;
            }
            else
            {
                d.assign (16 * 512, 0.0f); name = "EDITED";
                for (int f = 0; f < 16; ++f) for (int i = 0; i < 512; ++i) d[(size_t) (f * 512 + i)] = oscmodel::tblDefault (filter, f, i);
                fromBuiltIn = true;
            }
            const float pos = ctx.get (posId());
            cur = juce::jlimit (0, frames() - 1, juce::roundToInt (pos * (float) (frames() - 1)));
        }
        int posId() const { return oscId (os, oscKey (filter ? "wfpos" : "wdpos")); }
        void setPos() { ctx.begin (posId()); ctx.set (posId(), frames() <= 1 ? 0.0f : (float) cur / (float) (frames() - 1)); ctx.end (posId()); }
        void select (int f) { cur = juce::jlimit (0, frames() - 1, f); setPos(); owner.repaint(); }
        float* frame() { return d.data() + (size_t) cur * 512; }
        void commit() { dirty = false; mem.set (filter ? SoundMemory::FilterTable : SoundMemory::ShaperTable, os, name, {}, d); }
        void flush() { if (dirty) commit(); owner.stopTimer(); }
        void touch() { dirty = true; owner.repaint(); if (! owner.isTimerRunning()) owner.startTimer (250); }
        void edit (const std::function<void (float*)>& fn) { fn (frame()); for (int i = 0; i < 512; ++i) frame()[i] = juce::jlimit (-1.0f, 1.0f, frame()[i]); touch(); commit(); }
        static void smooth (float* v)
        {
            float t[512];
            for (int pass = 0; pass < 2; ++pass)
            {
                for (int i = 0; i < 512; ++i) t[i] = 0.25f * v[juce::jmax (0, i - 1)] + 0.5f * v[i] + 0.25f * v[juce::jmin (511, i + 1)];
                std::copy (t, t + 512, v);
            }
        }
        void randomise (float* v)
        {
            juce::Random r;
            float k[9]; for (float& x : k) x = r.nextFloat() * 2.0f - 1.0f;
            for (int i = 0; i < 512; ++i)
            {
                float x = (float) i / 511.0f * 8.0f; int a = (int) x; float f = x - (float) a;
                float w = f * f * (3.0f - 2.0f * f);
                v[i] = k[a] + (k[juce::jmin (8, a + 1)] - k[a]) * w;
            }
        }
        void preset (const juce::String& n)
        {
            edit ([this, &n] (float* v)
            {
                const float pi = juce::MathConstants<float>::pi;
                for (int i = 0; i < 512; ++i)
                {
                    const float x = (float) i / 511.0f, s = x * 2.0f - 1.0f;
                    float y = 0.0f;
                    if (filter)
                    {
                        auto bump = [&] (float c, float w) { return std::exp (-(x - c) * (x - c) / (2.0f * w * w)); };
                        if (n == "LOW PASS")       y = 1.0f - 2.0f / (1.0f + std::exp (-(0.5f - x) * 24.0f)) + 1.0f - 1.0f;
                        else if (n == "HIGH PASS") y = 2.0f / (1.0f + std::exp (-(x - 0.5f) * 24.0f)) - 1.0f;
                        else if (n == "BAND PASS") y = bump (0.5f, 0.06f) * 2.0f - 1.0f;
                        else if (n == "NOTCH")     y = 1.0f - bump (0.5f, 0.05f) * 2.0f;
                        else if (n == "COMB")      y = std::cos (2.0f * pi * 8.0f * x);
                        else                       y = juce::jmax (bump (0.30f, 0.025f), juce::jmax (bump (0.52f, 0.03f), bump (0.72f, 0.025f))) * 2.0f - 1.0f;
                        if (n == "LOW PASS") y = 1.0f / (1.0f + std::exp ((x - 0.5f) * 24.0f)) * 2.0f - 1.0f;
                    }
                    else
                    {
                        if (n == "LINEAR")      y = s;
                        else if (n == "SOFT")   y = std::tanh (3.0f * s) / std::tanh (3.0f);
                        else if (n == "HARD")   y = juce::jlimit (-1.0f, 1.0f, 2.5f * s);
                        else if (n == "FOLD")   y = std::sin (2.5f * pi * s);
                        else if (n == "ASYM")   y = s > 0 ? std::tanh (4.0f * s) : 0.55f * s;
                        else                    y = std::round (s * 6.0f) / 6.0f;
                    }
                    v[i] = y;
                }
            });
        }
        void addFrame()
        {
            if (frames() >= 64) return;
            std::vector<float> copy (frame(), frame() + 512);
            d.insert (d.begin() + (cur + 1) * 512, copy.begin(), copy.end());
            ++cur; setPos(); touch(); commit();
        }
        void delFrame()
        {
            if (frames() <= 1) return;
            d.erase (d.begin() + cur * 512, d.begin() + (cur + 1) * 512);
            cur = juce::jmin (cur, frames() - 1); setPos(); touch(); commit();
        }
        // the frames between the first and the last one become a linear blend of the two
        void morphAll()
        {
            const int n = frames(); if (n < 3) return;
            for (int f = 1; f < n - 1; ++f)
                for (int i = 0; i < 512; ++i)
                    d[(size_t) (f * 512 + i)] = d[(size_t) i] + (d[(size_t) ((n - 1) * 512 + i)] - d[(size_t) i]) * (float) f / (float) (n - 1);
            touch(); commit();
        }

        juce::Rectangle<int> canvas;
        void paintAll (juce::Graphics& g)
        {
            auto all = owner.getLocalBounds();
            paintCard (g, all.toFloat());
            header (g, all, juce::String (filter ? "Wavefilter editor" : "Wavedistortion editor") + "  -  OSC " + juce::String (os + 1) + "  -  " + name);
            paintInset (g, canvas.toFloat(), 4.0f);
            auto r = canvas.toFloat().reduced (10.0f, 8.0f);
            auto X = [&] (float t) { return r.getX() + t * r.getWidth(); };
            auto Y = [&] (float v) { return r.getY() + (0.5f - 0.5f * v) * r.getHeight(); };
            g.setColour (juce::Colours::white.withAlpha (0.07f));
            for (int i = 1; i < 8; ++i) g.drawVerticalLine ((int) X ((float) i / 8.0f), r.getY(), r.getBottom());
            for (int i = 1; i < 4; ++i) g.drawHorizontalLine ((int) Y (-1.0f + (float) i * 0.5f), r.getX(), r.getRight());
            g.setColour (juce::Colours::white.withAlpha (0.20f)); g.drawHorizontalLine ((int) Y (0.0f), r.getX(), r.getRight()); g.drawVerticalLine ((int) X (0.5f), r.getY(), r.getBottom());
            if (! filter) { g.setColour (juce::Colours::white.withAlpha (0.14f)); g.drawLine (X (0), Y (-1), X (1), Y (1)); }
            auto path = [&] (int f)
            {
                juce::Path p;
                for (int i = 0; i < 512; ++i)
                {
                    float x = X ((float) i / 511.0f), y = Y (d[(size_t) (f * 512 + i)]);
                    if (i == 0) p.startNewSubPath (x, y); else p.lineTo (x, y);
                }
                return p;
            };
            if (cur > 0) { g.setColour (juce::Colour (0xffa0968f).withAlpha (0.28f)); g.strokePath (path (cur - 1), juce::PathStrokeType (1.0f)); }
            if (cur < frames() - 1) { g.setColour (juce::Colour (0xffa0968f).withAlpha (0.28f)); g.strokePath (path (cur + 1), juce::PathStrokeType (1.0f)); }
            auto p = path (cur);
            g.setColour (juce::Colour (0xffff3b30).withAlpha (0.25f)); g.strokePath (p, juce::PathStrokeType (6.0f));
            g.setColour (juce::Colour (0xffff7864)); g.strokePath (p, juce::PathStrokeType (2.0f));
            g.setColour (dim); g.setFont (mono (8.5f, false));
            if (filter)
            {
                const float range = ctx.get (oscId (os, oscKey ("wfrange")));
                g.drawText (juce::String (-range * 0.5f, 1) + " oct", canvas.reduced (12, 10), juce::Justification::bottomLeft);
                g.drawText ("CUTOFF", canvas.reduced (12, 10), juce::Justification::centredBottom);
                g.drawText ("+" + juce::String (range * 0.5f, 1) + " oct", canvas.reduced (12, 10), juce::Justification::bottomRight);
                g.drawText ("+1", canvas.reduced (12, 10), juce::Justification::topLeft);
                g.drawText ("-1", canvas.reduced (12, 24), juce::Justification::bottomLeft);
            }
            else
            {
                g.drawText ("OUTPUT +1", canvas.reduced (12, 10), juce::Justification::topLeft);
                g.drawText ("INPUT -1", canvas.reduced (12, 24), juce::Justification::bottomLeft);
                g.drawText ("INPUT +1", canvas.reduced (12, 24), juce::Justification::bottomRight);
            }
            g.drawText ("FRAME " + juce::String (cur + 1) + " / " + juce::String (frames()) + (fromBuiltIn ? "   (built-in table: editing creates your own)" : "") + "   draw with the mouse, wheel = frame",
                        canvas.reduced (12, 10), juce::Justification::topRight);
        }
        void layout()
        {
            auto b = owner.getLocalBounds().reduced (12, 8);
            auto head = b.removeFromTop (28);
            closeBtn->setBounds (head.removeFromRight (80).reduced (0, 2));
            const int toolsH = 64;
            auto tools = b.removeFromBottom (toolsH);
            b.removeFromBottom (8);
            canvas = b;
            // two rows of buttons: frame / edit tools, presets
            int n1 = 10, x = tools.getX(); const int bw = 92, gap = 6;
            for (int i = 1; i < buttons.size(); ++i)
            {
                int row = i <= n1 ? 0 : 1, col = i <= n1 ? i - 1 : i - n1 - 1;
                buttons[i]->setBounds (tools.getX() + col * (bw + gap), tools.getY() + row * 32, bw, 26);
            }
            (void) x;
        }
        TableEditor& owner; Ctx& ctx; SoundMemory& mem; int os; bool filter;
        std::vector<float> d; juce::String name; int cur = 0; bool dirty = false, fromBuiltIn = false;
        juce::OwnedArray<Btn> buttons; Btn* closeBtn = nullptr; int lastIdx = -1; float lastV = 0.0f;
    };

    TableEditor::TableEditor (Ctx& c, SoundMemory& m, int osc, bool f) : impl (new Impl (*this, c, m, osc, f)) { c.addListener (this); setVisible (false); setName ("tableEditor"); }
    TableEditor::~TableEditor() { impl->ctx.removeListener (this); }
    void TableEditor::open() { impl->fromBuiltIn = false; impl->load(); setVisible (true); toFront (false); resized(); repaint(); }
    void TableEditor::paint (juce::Graphics& g) { impl->paintAll (g); }
    void TableEditor::resized() { impl->layout(); }
    void TableEditor::timerCallback() { if (impl->dirty) impl->commit(); else stopTimer(); }
    void TableEditor::paramChanged (int num, float v)
    {
        if (isVisible() && num == impl->posId() && impl->frames() > 0)
        {
            int f = juce::jlimit (0, impl->frames() - 1, juce::roundToInt (v * (float) (impl->frames() - 1)));
            if (f != impl->cur) { impl->cur = f; repaint(); }
        }
    }
    void TableEditor::mouseDown (const juce::MouseEvent& e)
    {
        if (! impl->canvas.contains (e.getPosition())) return;
        impl->lastIdx = -1; mouseDrag (e);
    }
    void TableEditor::mouseDrag (const juce::MouseEvent& e)
    {
        auto r = impl->canvas.toFloat().reduced (10.0f, 8.0f);
        if (! impl->canvas.contains (e.getMouseDownPosition())) return;
        float t = juce::jlimit (0.0f, 1.0f, (e.position.x - r.getX()) / r.getWidth());
        float v = juce::jlimit (-1.0f, 1.0f, 1.0f - 2.0f * (e.position.y - r.getY()) / r.getHeight());
        int idx = juce::roundToInt (t * 511.0f);
        float* f = impl->frame();
        if (impl->lastIdx < 0) { f[idx] = v; impl->lastV = v; }
        else
        {
            int a = impl->lastIdx, b = idx; float va = impl->lastV, vb = v;
            if (a > b) { std::swap (a, b); std::swap (va, vb); }
            for (int i = a; i <= b; ++i) f[i] = b == a ? vb : va + (vb - va) * (float) (i - a) / (float) (b - a);
        }
        impl->lastIdx = idx; impl->lastV = v; impl->fromBuiltIn = false; impl->touch();
    }
    void TableEditor::mouseUp (const juce::MouseEvent&) { impl->lastIdx = -1; if (impl->dirty) impl->commit(); }
    void TableEditor::mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails& w) { impl->select (impl->cur + (w.deltaY > 0 ? -1 : 1)); }

    // ====================================================================================================================== ModeEditor
    struct ModeEditor::Impl
    {
        Impl (ModeEditor& o, Ctx& c, SoundMemory& m, int osc) : owner (o), ctx (c), mem (m), os (osc)
        {
            auto add = [this] (const juce::String& t, std::function<void()> fn, bool accent = false)
            {
                auto* b = buttons.add (new Btn()); b->text = t; b->click = std::move (fn); b->accent = accent; owner.addAndMakeVisible (b); return b;
            };
            closeBtn = add ("CLOSE", [this] { flush(); owner.setVisible (false); if (owner.onClose) owner.onClose(); }, true);
            add ("RESET ALL", [this] { std::fill (v.begin(), v.end(), 1.0f); changed(); });
            add ("ODD MODES", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3 + 1] = (i % 2 == 0) ? 1.0f : 0.0f; changed(); });
            add ("EVEN MODES", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3 + 1] = (i % 2 == 1) ? 1.0f : 0.0f; changed(); });
            add ("STRETCH", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3] = juce::jlimit (0.5f, 2.0f, v[(size_t) i * 3] * (1.0f + 0.012f * (float) i)); changed(); });
            add ("SQUEEZE", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3] = juce::jlimit (0.5f, 2.0f, v[(size_t) i * 3] / (1.0f + 0.012f * (float) i)); changed(); });
            add ("RANDOMISE", [this] { juce::Random r; for (int i = 0; i < 16; ++i) { v[(size_t) i * 3] = std::pow (2.0f, (r.nextFloat() - 0.5f) * 0.3f); v[(size_t) i * 3 + 1] = r.nextFloat() * 1.6f + 0.1f; v[(size_t) i * 3 + 2] = std::pow (2.0f, (r.nextFloat() - 0.5f) * 3.0f); } changed(); });
            add ("DECAY TILT", [this] { for (int i = 0; i < 16; ++i) v[(size_t) i * 3 + 2] = juce::jlimit (0.1f, 4.0f, v[(size_t) i * 3 + 2] * std::pow (0.85f, (float) i * 0.5f)); changed(); });
            tabA = add ("PHYSICAL A", [this] { openSet (0); }); tabB = add ("PHYSICAL B", [this] { openSet (1); });
            v.assign (48, 1.0f);
        }
        int idx() const { return os * 3 + set; }
        void openSet (int s)
        {
            flush(); set = s;
            v.assign (48, 1.0f);
            if (auto* sl = mem.get (SoundMemory::ModeEdit, idx()); sl && sl->data.size() == 48) v = sl->data;
            owner.repaint();
        }
        bool isDefault() const { return std::all_of (v.begin(), v.end(), [] (float x) { return std::abs (x - 1.0f) < 1.0e-4f; }); }
        void commit()
        {
            dirty = false;
            if (isDefault()) mem.clear (SoundMemory::ModeEdit, idx()); else mem.set (SoundMemory::ModeEdit, idx(), "EDIT", {}, v);
        }
        void flush() { if (dirty) commit(); owner.stopTimer(); }
        void changed() { dirty = true; owner.repaint(); if (! owner.isTimerRunning()) owner.startTimer (120); }

        // base values of the mode set from the parameters (before the edits)
        struct Base { float f[16], a[16]; };
        Base base() const
        {
            Base b {};
            auto P = [&] (const char* k) { return ctx.get (set == 2 ? oscId (os, oscKey (k)) : phys::phyId (os, phys::key (k))); };
            int model; float hit, inh, tune;
            if (set == 0)      { model = juce::roundToInt (P ("phmodA")); hit = P ("phhitA"); inh = P ("phinhA"); tune = 0.0f; }
            else if (set == 1) { model = juce::roundToInt (P ("phmodB")); hit = P ("phhitB"); inh = P ("phinhB"); tune = P ("phtunB"); }
            else               { model = juce::roundToInt (P ("rsmod")); hit = P ("rshit"); inh = P ("rsinh"); tune = P ("rstune"); }
            model = juce::jlimit (0, 8, model);
            const float f0 = 220.0f * std::pow (2.0f, tune / 12.0f);
            float amax = 1.0e-4f;
            for (int i = 0; i < 16; ++i)
            {
                float r = phys::RAT[model][i] * (1.0f + inh * 0.004f * (float) (i * i));
                b.f[i] = f0 * r;
                b.a[i] = std::abs (std::sin (3.14159265f * hit * (float) (i + 1))) / std::pow ((float) (i + 1), phys::AEXP[model]);
                amax = juce::jmax (amax, b.a[i]);
            }
            for (float& a : b.a) a /= amax;
            return b;
        }

        // layout: spectrum on top, then three editable rows (frequency, gain, decay), mode numbers / Hz at the bottom
        juce::Rectangle<int> area, spec, rows[3];
        void layout()
        {
            auto b = owner.getLocalBounds().reduced (12, 8);
            auto head = b.removeFromTop (28);
            closeBtn->setBounds (head.removeFromRight (80).reduced (0, 2));
            const bool phy = ctx.get (oscId (os, oscKey ("type"))) > 2.5f && ctx.get (oscId (os, oscKey ("type"))) < 3.5f;
            tabA->setVisible (phy); tabB->setVisible (phy);
            head.removeFromRight (10); tabB->setBounds (head.removeFromRight (110).reduced (0, 2)); head.removeFromRight (4); tabA->setBounds (head.removeFromRight (110).reduced (0, 2));
            tabA->accent = set == 0; tabB->accent = set == 1;
            auto tools = b.removeFromBottom (34);
            for (int i = 1, x = tools.getX(); i <= 7; ++i, x += 104) buttons[i]->setBounds (x, tools.getY() + 4, 98, 26);
            b.removeFromBottom (6);
            area = b;
            auto c = b.withTrimmedLeft (86).withTrimmedBottom (26);
            spec = c.removeFromTop (juce::jmin (130, c.getHeight() / 3)); c.removeFromTop (8);
            const int rh = (c.getHeight() - 16) / 3;
            for (int i = 0; i < 3; ++i) { rows[i] = c.removeFromTop (rh); c.removeFromTop (8); }
        }
        float colX (int i) const { return (float) rows[0].getX() + ((float) i + 0.5f) * (float) rows[0].getWidth() / 16.0f; }
        // editable value <-> normalised position (0 bottom .. 1 top)
        static float toPos (int row, float x)
        {
            if (row == 0) return juce::jlimit (0.0f, 1.0f, 0.5f + std::log2 (juce::jmax (0.01f, x)) / 2.0f);        // 0.5 .. 2 on a log scale (centre = 1)
            if (row == 1) return juce::jlimit (0.0f, 1.0f, x / 2.0f);                                                  // 0 .. 2
            return juce::jlimit (0.0f, 1.0f, 0.5f + std::log2 (juce::jmax (0.01f, x)) / 6.64f);                        // 0.1 .. 10 on a log scale (centre = 1)
        }
        static float fromPos (int row, float p)
        {
            p = juce::jlimit (0.0f, 1.0f, p);
            if (row == 0) return std::pow (2.0f, (p - 0.5f) * 2.0f);
            if (row == 1) return p * 2.0f;
            return std::pow (2.0f, (p - 0.5f) * 6.64f);
        }
        void paintAll (juce::Graphics& g)
        {
            auto all = owner.getLocalBounds();
            paintCard (g, all.toFloat());
            static const char* setName[3] = { "Physical resonator A", "Physical resonator B", "Resonator stage" };
            header (g, all, juce::String ("Resonator editor  -  OSC ") + juce::String (os + 1) + "  -  " + setName[set] + (isDefault() ? "" : "  (edited)"));
            auto b = base();
            // spectrum
            paintInset (g, spec.toFloat(), 4.0f);
            {
                const float fLo = 30.0f, fHi = 16000.0f;
                auto xOf = [&] (float f) { return (float) spec.getX() + 8.0f + std::log (f / fLo) / std::log (fHi / fLo) * ((float) spec.getWidth() - 16.0f); };
                g.setColour (juce::Colours::white.withAlpha (0.07f));
                for (float f : { 100.0f, 1000.0f, 10000.0f }) { g.drawVerticalLine ((int) xOf (f), (float) spec.getY(), (float) spec.getBottom()); }
                g.setColour (dim); g.setFont (mono (8.0f, false));
                g.drawText ("100", (int) xOf (100) + 3, spec.getBottom() - 14, 40, 12, juce::Justification::left); g.drawText ("1k", (int) xOf (1000) + 3, spec.getBottom() - 14, 40, 12, juce::Justification::left);
                g.drawText ("10k", (int) xOf (10000) + 3, spec.getBottom() - 14, 40, 12, juce::Justification::left);
                g.drawText ("MODES: KEY A3 = 220 Hz + TUNE   (grey = unedited)", spec.reduced (8, 4), juce::Justification::topLeft);
                for (int i = 0; i < 16; ++i)
                {
                    const float fe = b.f[i] * v[(size_t) i * 3], ge = b.a[i] * v[(size_t) i * 3 + 1];
                    const float hmax = (float) spec.getHeight() - 30.0f;
                    if (b.f[i] < 18000.0f) { g.setColour (juce::Colour (0xffa0968f).withAlpha (0.35f)); g.drawLine (xOf (b.f[i]), (float) spec.getBottom() - 6, xOf (b.f[i]), (float) spec.getBottom() - 6 - hmax * b.a[i], 2.0f); }
                    if (fe < 18000.0f) { g.setColour (juce::Colour (0xffff3b30)); g.drawLine (xOf (fe), (float) spec.getBottom() - 6, xOf (fe), (float) spec.getBottom() - 6 - hmax * juce::jmin (1.0f, ge * 0.5f + 0.0f) , 3.0f); }
                }
            }
            static const char* rowName[3] = { "FREQUENCY\nx0.5 .. x2", "GAIN\n0 .. 2", "DECAY\nx0.1 .. x10" };
            for (int r = 0; r < 3; ++r)
            {
                auto rc = rows[r];
                paintInset (g, rc.toFloat(), 4.0f);
                g.setColour (orange); g.setFont (font (8.0f, true).withExtraKerningFactor (0.15f));
                g.drawFittedText (rowName[r], area.getX(), rc.getY(), 82, rc.getHeight(), juce::Justification::centredLeft, 2);
                // centre line (value 1)
                const float y1 = (float) rc.getBottom() - toPos (r, 1.0f) * (float) rc.getHeight();
                g.setColour (juce::Colours::white.withAlpha (0.18f)); g.drawHorizontalLine ((int) y1, (float) rc.getX(), (float) rc.getRight());
                for (int i = 0; i < 16; ++i)
                {
                    const float x = colX (i), w = (float) rc.getWidth() / 16.0f * 0.62f;
                    const float val = v[(size_t) i * 3 + (size_t) r];
                    const float y = (float) rc.getBottom() - toPos (r, val) * (float) rc.getHeight();
                    const bool edited = std::abs (val - 1.0f) > 1.0e-3f;
                    g.setColour (edited ? juce::Colour (0xffff3b30).withAlpha (0.85f) : juce::Colour (0xff8a817c).withAlpha (0.65f));
                    if (r == 1) g.fillRect (juce::Rectangle<float> (x - w * 0.5f, y, w, (float) rc.getBottom() - y));
                    else g.fillRect (juce::Rectangle<float> (x - w * 0.5f, juce::jmin (y, y1), w, juce::jmax (2.0f, std::abs (y - y1))));
                    g.setColour (juce::Colours::white.withAlpha (0.85f)); g.fillRect (juce::Rectangle<float> (x - w * 0.5f, y - 1.0f, w, 2.0f));
                }
            }
            g.setColour (dim); g.setFont (mono (8.0f, false));
            for (int i = 0; i < 16; ++i)
            {
                auto cell = juce::Rectangle<float> (colX (i) - 24.0f, (float) rows[2].getBottom() + 3, 48.0f, 22.0f);
                g.drawText (juce::String (i + 1), cell.withHeight (10), juce::Justification::centred);
                const float fe = b.f[i] * v[(size_t) i * 3];
                g.drawText (fe >= 1000.0f ? juce::String (fe / 1000.0f, 2) + "k" : juce::String (juce::roundToInt (fe)), cell.withTrimmedTop (10), juce::Justification::centred);
            }
            g.drawFittedText ("drag across the bars to draw  -  double-click a bar to reset it\nthe sound follows while you draw", juce::Rectangle<int> (area.getX() + 730, area.getBottom() + 6, area.getWidth() - 730, 30), juce::Justification::centredRight, 2);
        }
        int hitRow (juce::Point<int> p) const { for (int r = 0; r < 3; ++r) if (rows[r].expanded (0, 4).contains (p)) return r; return -1; }
        void draw (const juce::MouseEvent& e)
        {
            if (dragRow < 0) return;
            auto rc = rows[dragRow];
            int col = juce::jlimit (0, 15, (int) ((e.position.x - (float) rc.getX()) / ((float) rc.getWidth() / 16.0f)));
            float p = ((float) rc.getBottom() - e.position.y) / (float) rc.getHeight();
            float val = fromPos (dragRow, p);
            if (std::abs (p - toPos (dragRow, 1.0f)) < 0.015f) val = 1.0f;      // snap to "unchanged"
            v[(size_t) col * 3 + (size_t) dragRow] = val;
            changed();
        }
        ModeEditor& owner; Ctx& ctx; SoundMemory& mem; int os; int set = 0;
        std::vector<float> v; bool dirty = false; juce::OwnedArray<Btn> buttons; Btn *closeBtn = nullptr, *tabA = nullptr, *tabB = nullptr; int dragRow = -1;
    };

    ModeEditor::ModeEditor (Ctx& c, SoundMemory& m, int osc) : impl (new Impl (*this, c, m, osc)) { c.addListener (this); setVisible (false); setName ("modeEditor"); }
    ModeEditor::~ModeEditor() { impl->ctx.removeListener (this); }
    void ModeEditor::open (int set) { impl->set = set; impl->openSet (set); setVisible (true); toFront (false); resized(); repaint(); }
    void ModeEditor::paint (juce::Graphics& g) { impl->paintAll (g); }
    void ModeEditor::resized() { impl->layout(); }
    void ModeEditor::timerCallback() { if (impl->dirty) impl->commit(); stopTimer(); }
    void ModeEditor::paramChanged (int, float) { if (isVisible()) repaint(); }
    void ModeEditor::mouseDown (const juce::MouseEvent& e) { impl->dragRow = impl->hitRow (e.getPosition()); impl->draw (e); }
    void ModeEditor::mouseDrag (const juce::MouseEvent& e) { impl->draw (e); }
    void ModeEditor::mouseUp (const juce::MouseEvent&) { impl->dragRow = -1; impl->flush(); }
    void ModeEditor::mouseDoubleClick (const juce::MouseEvent& e)
    {
        int r = impl->hitRow (e.getPosition()); if (r < 0) return;
        int col = juce::jlimit (0, 15, (int) ((e.position.x - (float) impl->rows[r].getX()) / ((float) impl->rows[r].getWidth() / 16.0f)));
        impl->v[(size_t) col * 3 + (size_t) r] = 1.0f; impl->changed();
    }
}
