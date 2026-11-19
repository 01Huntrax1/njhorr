#include "SampleEditor.h"
#include "../NjoSm.h"
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
        enum Marker { None = -1, Start = 0, End, LoopStart, LoopEnd };
    }

    struct SampleEditor::Impl
    {
        Impl (SampleEditor& o, Ctx& c, SoundMemory& m, int osc) : owner (o), ctx (c), mem (m), os (osc)
        {
            auto add = [this] (const juce::String& t, std::function<void()> fn, bool accent = false)
            {
                auto* b = buttons.add (new Btn()); b->text = t; b->click = std::move (fn); b->accent = accent; owner.addAndMakeVisible (b); return b;
            };
            closeBtn = add ("CLOSE", [this] { owner.setVisible (false); if (owner.onClose) owner.onClose(); }, true);
            add ("ZOOM ALL", [this] { v0 = 0.0f; v1 = 1.0f; peaksKey = 0; owner.repaint(); });
            add ("NORMALIZE", [this] { normalize(); });
            add ("TRIM", [this] { trim(); });
            add ("RESET MARKERS", [this] { resetMarkers(); });
            for (auto key : { "sstart", "send", "slps", "slpe", "sxf", "sgain", "svst", "swid" })
                addWidget (key, true);
            for (auto key : { "sloop", "spp", "srev", "sint" }) addWidget (key, false);
            addWidget ("sslice", false); addWidget ("root", false);
        }

        void addWidget (const juce::String& key, bool knob)
        {
            const int id = key == "sstart" ? oscId (os, oscKey ("sstart")) : key == "sloop" ? oscId (os, oscKey ("sloop")) : key == "root" ? oscId (os, oscKey ("root")) : sm::smId (os, sm::key (key.toRawUTF8()));
            auto w = makeWidget (ctx, id, knob);
            owner.addAndMakeVisible (*w);
            widgets[key] = std::move (w);
        }
        ParamWidget* W (const char* k) { auto it = widgets.find (k); return it == widgets.end() ? nullptr : it->second.get(); }

        int idOf (const char* key) const
        {
            const juce::String k (key);
            return k == "sstart" ? oscId (os, oscKey ("sstart")) : k == "sloop" ? oscId (os, oscKey ("sloop")) : sm::smId (os, sm::key (key));
        }
        float P (const char* key) const { return ctx.get (idOf (key)); }
        const SoundMemory::Slot* slot() const { return mem.get (SoundMemory::Sample, os); }
        int length() const { auto* s = slot(); return s ? (int) s->data.size() : 0; }

        // ---- geometry ----
        juce::Rectangle<int> canvas, ctrl;
        void layout()
        {
            auto all = owner.getLocalBounds();
            closeBtn->setBounds (all.getRight() - 12 - 70, 7, 70, 20);
            int bx = all.getRight() - 12 - 70 - 8;
            for (int i = buttons.size() - 1; i >= 1; --i) { int w = buttons[i]->text.length() > 9 ? 104 : 80; bx -= w; buttons[i]->setBounds (bx, 7, w, 20); bx -= 6; }
            canvas = juce::Rectangle<int> (12, 40, all.getWidth() - 24, 186);
            ctrl = juce::Rectangle<int> (12, canvas.getBottom() + 24, all.getWidth() - 24, all.getHeight() - canvas.getBottom() - 26);
            // knob row 1: Start, End, Loop Start, Loop End, Crossfade; row 2: Gain, Width, Vel > Start; buttons + steppers on the right
            const int cw = 96; int x = ctrl.getX() + 6, y = ctrl.getY() + 2;
            const char* r1[] = { "sstart", "send", "slps", "slpe", "sxf" };
            for (int i = 0; i < 5; ++i) if (auto* w = W (r1[i])) w->setBounds (x + i * (cw + 6), y, cw, 58);
            const char* r2[] = { "sgain", "swid", "svst" };
            for (int i = 0; i < 3; ++i) if (auto* w = W (r2[i])) w->setBounds (x + i * (cw + 6), y + 66, cw, 58);
            const int bx2 = x + 5 * (cw + 6) + 24; const int bw = 160;
            if (auto* w = W ("sloop")) w->setBounds (bx2, y, bw, 32);
            if (auto* w = W ("spp"))   w->setBounds (bx2 + bw + 8, y, bw, 32);
            if (auto* w = W ("srev"))  w->setBounds (bx2, y + 40, bw, 32);
            if (auto* w = W ("sint"))  w->setBounds (bx2 + bw + 8, y + 40, bw, 32);
            if (auto* w = W ("sslice")) w->setBounds (bx2, y + 92, bw, 26);
            if (auto* w = W ("root"))   w->setBounds (bx2 + bw + 8, y + 92, bw, 26);
        }

        // ---- view / peaks ----
        float v0 = 0.0f, v1 = 1.0f;                       // visible part of the sample (0..1)
        std::vector<float> pk;                            // min / max pairs per pixel and lane
        unsigned long long peaksKey = 0;
        int lanes() const { auto* s = slot(); return s && ! s->dataR.empty() ? 2 : 1; }
        void buildPeaks()
        {
            auto* s = slot(); if (s == nullptr) { pk.clear(); return; }
            const int W = juce::jmax (1, canvas.getWidth() - 20), n = (int) s->data.size(), L = lanes();
            unsigned long long key = (unsigned long long) n * 1000003ull ^ (unsigned long long) (v0 * 1e5f) * 7919ull ^ (unsigned long long) (v1 * 1e5f) * 104729ull ^ (unsigned long long) W * 31ull ^ (unsigned long long) L;
            if (key == peaksKey && ! pk.empty()) return;
            peaksKey = key;
            pk.assign ((size_t) (W * L * 2), 0.0f);
            const double a = v0 * n, b = v1 * n;
            for (int l = 0; l < L; ++l)
            {
                const auto& d = l == 0 ? s->data : s->dataR;
                for (int x = 0; x < W; ++x)
                {
                    int i0 = juce::jlimit (0, n - 1, (int) (a + (b - a) * x / W)), i1 = juce::jlimit (i0 + 1, n, (int) (a + (b - a) * (x + 1) / W));
                    float mn = 1, mx = -1;
                    for (int i = i0; i < i1; ++i) { float v = d[(size_t) i]; mn = juce::jmin (mn, v); mx = juce::jmax (mx, v); }
                    if (mx < mn) mn = mx = 0;
                    pk[(size_t) ((l * W + x) * 2)] = mn; pk[(size_t) ((l * W + x) * 2 + 1)] = mx;
                }
            }
        }

        // x of a position (0..1 of the whole sample)
        float xOf (float pos) const { return (float) canvas.getX() + 10.0f + (pos - v0) / juce::jmax (1.0e-6f, v1 - v0) * (float) (canvas.getWidth() - 20); }
        float posOf (float x) const { return v0 + (x - (float) canvas.getX() - 10.0f) / (float) (canvas.getWidth() - 20) * (v1 - v0); }
        // absolute positions of the markers (0..1 of the sample)
        float absStart() const { return juce::jlimit (0.0f, 1.0f, P ("sstart")); }
        float absEnd() const { return juce::jlimit (absStart(), 1.0f, P ("send")); }
        float absLoopS() const { return absStart() + juce::jlimit (0.0f, 1.0f, P ("slps")) * (absEnd() - absStart()); }
        float absLoopE() const { return absStart() + juce::jlimit (0.0f, 1.0f, P ("slpe")) * (absEnd() - absStart()); }
        float markerPos (int m) const { return m == Start ? absStart() : m == End ? absEnd() : m == LoopStart ? absLoopS() : absLoopE(); }
        bool sliceMode() const { return P ("sslice") > 1.5f; }

        int hit (juce::Point<int> p) const
        {
            if (! canvas.contains (p)) return None;
            int best = None; float bd = 7.0f;
            const bool loop = P ("sloop") > 0.5f;
            for (int m = 0; m < 4; ++m)
            {
                if (sliceMode()) break;
                if (m >= LoopStart && ! loop) continue;
                float d = std::abs (xOf (markerPos (m)) - (float) p.x);
                if (d < bd) { bd = d; best = m; }
            }
            return best;
        }

        void setParam (const char* key, float v) { const int id = idOf (key); ctx.begin (id); ctx.set (id, v); ctx.end (id); }
        void dragTo (int m, float pos)
        {
            pos = juce::jlimit (0.0f, 1.0f, pos);
            const float s = absStart(), e = absEnd(), span = juce::jmax (1.0e-4f, e - s);
            if (m == Start)
            {
                const float ns = juce::jmin (pos, e - 1.0e-3f);
                // keep the loop markers where they are on the sample: their parameters are relative to Start / End
                const float ls = absLoopS(), le = absLoopE(), nspan = juce::jmax (1.0e-4f, e - ns);
                setParam ("sstart", ns);
                setParam ("slps", juce::jlimit (0.0f, 1.0f, (ls - ns) / nspan)); setParam ("slpe", juce::jlimit (0.0f, 1.0f, (le - ns) / nspan));
            }
            else if (m == End)
            {
                const float ne = juce::jmax (pos, s + 1.0e-3f);
                const float ls = absLoopS(), le = absLoopE(), nspan = juce::jmax (1.0e-4f, ne - s);
                setParam ("send", ne);
                setParam ("slps", juce::jlimit (0.0f, 1.0f, (ls - s) / nspan)); setParam ("slpe", juce::jlimit (0.0f, 1.0f, (le - s) / nspan));
            }
            else if (m == LoopStart) setParam ("slps", juce::jlimit (0.0f, juce::jmax (0.0f, P ("slpe") - 0.001f), (pos - s) / span));
            else if (m == LoopEnd)   setParam ("slpe", juce::jlimit (juce::jmin (1.0f, P ("slps") + 0.001f), 1.0f, (pos - s) / span));
        }

        void resetMarkers() { setParam ("sstart", 0.0f); setParam ("send", 1.0f); setParam ("slps", 0.0f); setParam ("slpe", 1.0f); owner.repaint(); }

        void normalize()
        {
            auto* s = slot(); if (! s) return;
            auto l = s->data, r = s->dataR; float pkv = 0;
            for (float v : l) pkv = juce::jmax (pkv, std::abs (v)); for (float v : r) pkv = juce::jmax (pkv, std::abs (v));
            if (pkv < 1.0e-5f) return;
            const float g = 0.95f / pkv;
            for (auto& v : l) v *= g; for (auto& v : r) v *= g;
            mem.set (SoundMemory::Sample, os, s->name, s->libId, std::move (l), std::move (r));
            peaksKey = 0; owner.repaint();
        }
        void trim()   // Start / End to the first / last sample above -54 dB
        {
            auto* s = slot(); if (! s) return;
            const int n = (int) s->data.size(); const float th = 0.002f;
            int a = 0, b = n - 1;
            auto loud = [&] (int i) { return std::abs (s->data[(size_t) i]) > th || (! s->dataR.empty() && std::abs (s->dataR[(size_t) i]) > th); };
            while (a < n - 1 && ! loud (a)) ++a;
            while (b > a && ! loud (b)) --b;
            setParam ("sstart", (float) a / (float) n); setParam ("send", juce::jmin (1.0f, (float) (b + 1) / (float) n));
            setParam ("slps", 0.0f); setParam ("slpe", 1.0f);
            owner.repaint();
        }

        void paintAll (juce::Graphics& g)
        {
            auto all = owner.getLocalBounds();
            paintCard (g, all.toFloat());
            g.setColour (red); g.fillRect (juce::Rectangle<float> (12.0f, 13.0f, 7.0f, 7.0f));
            auto* s = slot();
            g.setColour (ink); g.setFont (impact (13.0f));
            g.drawText (("Sample editor  -  OSC " + juce::String (os + 1) + "  -  " + (s ? s->name : juce::String ("NO SAMPLE"))).toUpperCase(), 26, 6, 560, 20, juce::Justification::centredLeft);
            paintInset (g, canvas.toFloat(), 4.0f);
            if (s == nullptr || s->data.empty())
            {
                g.setColour (dim); g.setFont (font (11.0f, true)); g.drawText ("LOAD A SAMPLE INTO THIS OSCILLATOR (DROP A FILE ON THE SOURCE PANEL OR USE THE VAULT)", canvas, juce::Justification::centred);
                return;
            }
            buildPeaks();
            const int L = lanes(), Wd = canvas.getWidth() - 20;
            const float laneH = (float) (canvas.getHeight() - 24) / (float) L;
            const float top = (float) canvas.getY() + 12.0f;
            const float xs = xOf (absStart()), xe = xOf (absEnd());
            const bool slices = sliceMode(), loop = P ("sloop") > 0.5f;
            // regions: outside the play region is dimmed, the loop region is tinted
            g.setColour (juce::Colours::black.withAlpha (0.28f));
            if (! slices)
            {
                g.fillRect (juce::Rectangle<float> ((float) canvas.getX() + 10.0f, top, juce::jmax (0.0f, xs - ((float) canvas.getX() + 10.0f)), laneH * (float) L));
                g.fillRect (juce::Rectangle<float> (xe, top, juce::jmax (0.0f, (float) canvas.getRight() - 10.0f - xe), laneH * (float) L));
                if (loop) { g.setColour (juce::Colour (0xff4fd0a0).withAlpha (0.12f)); g.fillRect (juce::Rectangle<float> (xOf (absLoopS()), top, xOf (absLoopE()) - xOf (absLoopS()), laneH * (float) L)); }
            }
            for (int l = 0; l < L; ++l)
            {
                const float cy = top + laneH * ((float) l + 0.5f);
                g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawHorizontalLine ((int) cy, (float) canvas.getX() + 10.0f, (float) canvas.getRight() - 10.0f);
                juce::Path p;
                for (int x = 0; x < Wd; ++x)
                {
                    const float mn = pk[(size_t) ((l * Wd + x) * 2)], mx = pk[(size_t) ((l * Wd + x) * 2 + 1)];
                    p.startNewSubPath ((float) canvas.getX() + 10.0f + (float) x, cy - mx * (laneH * 0.5f - 3)); p.lineTo ((float) canvas.getX() + 10.0f + (float) x, cy - mn * (laneH * 0.5f - 3) + 0.6f);
                }
                g.setColour (juce::Colour (0xffff3e30)); g.strokePath (p, juce::PathStrokeType (1.2f));
            }
            // time ruler
            const double secs = (double) s->data.size() / 48000.0;
            g.setFont (font (8.0f, true)); g.setColour (dim);
            const double span = (double) (v1 - v0) * secs; const double step = span > 6 ? 1.0 : span > 2.5 ? 0.5 : span > 1 ? 0.2 : span > 0.4 ? 0.1 : 0.02;
            for (double t = std::ceil ((double) v0 * secs / step) * step; t <= (double) v1 * secs; t += step)
            {
                const float x = xOf ((float) (t / secs));
                g.drawVerticalLine ((int) x, (float) canvas.getBottom() - 12.0f, (float) canvas.getBottom() - 8.0f);
                g.drawText (juce::String (t, step < 0.1 ? 2 : 1) + "s", (int) x + 2, canvas.getBottom() - 13, 40, 11, juce::Justification::left);
            }
            if (slices)   // slice grid over the whole sample: slice k plays on the key root + k
            {
                const int n = juce::roundToInt (P ("sslice"));
                for (int k = 0; k <= n; ++k)
                {
                    const float x = xOf ((float) k / (float) n);
                    g.setColour (juce::Colour (0xff7fd0ff).withAlpha (0.8f)); g.drawVerticalLine ((int) x, top, top + laneH * (float) L);
                    if (k < n) { g.setFont (font (8.0f, true)); g.drawText (juce::String (k + 1), (int) x + 3, (int) top, 24, 11, juce::Justification::left); }
                }
            }
            else
            {
                auto flag = [&] (int m, juce::Colour c, const char* t, bool up)
                {
                    const float x = xOf (markerPos (m));
                    g.setColour (c); g.drawLine (x, top - 6.0f, x, top + laneH * (float) L, drag == m ? 2.5f : 1.5f);
                    juce::Path tri; const float y0 = up ? top - 6.0f : top + laneH * (float) L;
                    const float dx = (m == Start || m == LoopStart) ? 9.0f : -9.0f;
                    tri.addTriangle (x, y0, x + dx, y0, x, y0 + (up ? 9.0f : -9.0f)); g.fillPath (tri);
                    g.setFont (font (8.0f, true));
                    g.drawText (t, (int) (dx > 0 ? x + 3 : x - 43), (int) (up ? top - 8.0f : top + laneH * (float) L - 12.0f), 40, 10, dx > 0 ? juce::Justification::left : juce::Justification::right);
                };
                flag (Start, juce::Colour (0xffffc8be), "START", true);
                flag (End, juce::Colour (0xffffc8be), "END", true);
                if (loop) { flag (LoopStart, juce::Colour (0xff4fd0a0), "LOOP", false); flag (LoopEnd, juce::Colour (0xff4fd0a0), "LOOP", false); }
            }
            g.setColour (dim); g.setFont (font (9.0f, true));
            for (auto k : { "sslice", "root" })
                if (auto* w = W (k)) g.drawText (juce::String (k) == "root" ? "ROOT NOTE" : "SLICES", w->getX(), w->getY() - 12, w->getWidth(), 11, juce::Justification::left);
            auto sec = [&] (float p) { return juce::String ((double) p * secs, 3) + " S"; };
            g.drawText (juce::String (secs, 2) + " S  /  " + (L == 2 ? "STEREO" : "MONO") + "  /  START " + sec (absStart()) + "  END " + sec (absEnd()) + (loop ? "  LOOP " + sec (absLoopS()) + " - " + sec (absLoopE()) : juce::String())
                        + (slices ? "  /  " + juce::String (juce::roundToInt (P ("sslice"))) + " SLICES (KEY ROOT + 0..)" : juce::String()) + "     WHEEL = ZOOM, RIGHT DRAG = SCROLL", ctrl.getX(), ctrl.getY() - 12, ctrl.getWidth(), 11, juce::Justification::left);
        }

        SampleEditor& owner; Ctx& ctx; SoundMemory& mem; int os;
        juce::OwnedArray<Btn> buttons; Btn* closeBtn = nullptr;
        std::map<juce::String, std::unique_ptr<ParamWidget>> widgets;
        int drag = None; float panStartV0 = 0, panStartX = 0; bool panning = false;
    };

    SampleEditor::SampleEditor (Ctx& c, SoundMemory& m, int osc) : impl (new Impl (*this, c, m, osc)) { c.addListener (this); m.addChangeListener (this); setVisible (false); setName ("sampleEditor"); }
    SampleEditor::~SampleEditor() { impl->ctx.removeListener (this); impl->mem.removeChangeListener (this); }
    void SampleEditor::open() { impl->v0 = 0.0f; impl->v1 = 1.0f; impl->peaksKey = 0; setVisible (true); toFront (false); resized(); repaint(); }
    void SampleEditor::paint (juce::Graphics& g) { impl->paintAll (g); }
    void SampleEditor::resized() { impl->layout(); }
    void SampleEditor::paramChanged (int, float) { if (isVisible()) repaint(); }
    void SampleEditor::changeListenerCallback (juce::ChangeBroadcaster*) { impl->peaksKey = 0; if (isVisible()) repaint(); }
    void SampleEditor::mouseMove (const juce::MouseEvent& e) { setMouseCursor (impl->hit (e.getPosition()) != None ? juce::MouseCursor::LeftRightResizeCursor : juce::MouseCursor::NormalCursor); }
    void SampleEditor::mouseDown (const juce::MouseEvent& e)
    {
        if (e.mods.isRightButtonDown() || e.mods.isMiddleButtonDown()) { impl->panning = true; impl->panStartV0 = impl->v0; impl->panStartX = (float) e.x; return; }
        impl->drag = impl->hit (e.getPosition());
        if (impl->drag != None) { impl->dragTo (impl->drag, impl->posOf ((float) e.x)); repaint(); }
    }
    void SampleEditor::mouseDrag (const juce::MouseEvent& e)
    {
        if (impl->panning)
        {
            const float span = impl->v1 - impl->v0;
            const float dv = -((float) e.x - impl->panStartX) / (float) juce::jmax (1, impl->canvas.getWidth() - 20) * span;
            float n0 = juce::jlimit (0.0f, 1.0f - span, impl->panStartV0 + dv); impl->v0 = n0; impl->v1 = n0 + span; impl->peaksKey = 0; repaint(); return;
        }
        if (impl->drag != None) { impl->dragTo (impl->drag, impl->posOf ((float) e.x)); repaint(); }
    }
    void SampleEditor::mouseUp (const juce::MouseEvent&) { impl->drag = None; impl->panning = false; repaint(); }
    void SampleEditor::mouseDoubleClick (const juce::MouseEvent&) { impl->v0 = 0.0f; impl->v1 = 1.0f; impl->peaksKey = 0; repaint(); }
    void SampleEditor::mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w)
    {
        if (! impl->canvas.contains (e.getPosition())) return;
        const float c = impl->posOf ((float) e.x), f = w.deltaY > 0 ? 0.8f : 1.25f;
        float span = juce::jlimit (0.0005f, 1.0f, (impl->v1 - impl->v0) * f);
        const float rel = (c - impl->v0) / juce::jmax (1.0e-6f, impl->v1 - impl->v0);
        float n0 = juce::jlimit (0.0f, 1.0f - span, c - rel * span);
        impl->v0 = n0; impl->v1 = n0 + span; impl->peaksKey = 0; repaint();
    }
}
