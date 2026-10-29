#include "ShaperEditor.h"

namespace njo
{
    using namespace theme;

    struct ShaperEditor::Impl
    {
        ShaperEditor& owner; Ctx& ctx; SoundMemory& mem;
        int slot = 0, base = 0, hot = -1, hotSeg = -1, drag = -1, dragSeg = -1; bool dirty = false, dragging = false;
        float segStartC = 0.0f, segStartY = 0.0f;
        shaper::Nodes nodes; std::vector<float> lastData;
        juce::Rectangle<float> area;
        Impl (ShaperEditor& o, Ctx& c, SoundMemory& m) : owner (o), ctx (c), mem (m) {}

        float px (double x) const { return area.getX() + (float) ((x + 1.0) * 0.5) * area.getWidth(); }
        float py (double y) const { return area.getBottom() - (float) ((y + 1.0) * 0.5) * area.getHeight(); }
        double ux (float x) const { return juce::jlimit (-1.0, 1.0, ((x - area.getX()) / area.getWidth()) * 2.0 - 1.0); }
        double uy (float y) const { return juce::jlimit (-1.0, 1.0, ((area.getBottom() - y) / area.getHeight()) * 2.0 - 1.0); }
        int mode() const { return juce::roundToInt (ctx.get (base + 3)); }

        void load()
        {
            nodes.clear();
            if (auto* sl = mem.get (SoundMemory::EqBands, slot)) nodes = shaper::decode (sl->data);
            lastData = shaper::encode (nodes);
        }
        void changed() { dirty = true; owner.repaint(); if (! owner.isTimerRunning()) owner.startTimer (80); }
        void commit()
        {
            dirty = false;
            auto d = shaper::encode (nodes);
            if (nodes.size() < 2) mem.clear (SoundMemory::EqBands, slot); else mem.set (SoundMemory::EqBands, slot, "WS", {}, d);
            lastData = d;
        }
        int nodeAt (juce::Point<float> p) const
        {
            for (int i = (int) nodes.size() - 1; i >= 0; --i)
                if (p.getDistanceFrom ({ px (nodes[(size_t) i].x), py (nodes[(size_t) i].y) }) < 9.0f) return i;
            return -1;
        }
        juce::Point<float> segHandle (int i) const   // the curvature handle sits on the curve at the middle of the segment
        {
            const auto& a = nodes[(size_t) i]; const auto& b = nodes[(size_t) i + 1];
            const double xm = 0.5 * (a.x + b.x);
            return { px (xm), py (shaper::eval (nodes, xm)) };
        }
        int segAt (juce::Point<float> p) const
        {
            for (int i = 0; i + 1 < (int) nodes.size(); ++i)
                if (nodes[(size_t) i + 1].x - nodes[(size_t) i].x > 0.06f && p.getDistanceFrom (segHandle (i)) < 7.0f) return i;
            return -1;
        }
    };

    ShaperEditor::ShaperEditor (Ctx& c, SoundMemory& m) : impl (new Impl (*this, c, m)) { c.addListener (this); m.addChangeListener (this); setName ("shaperEditor"); }
    ShaperEditor::~ShaperEditor() { impl->mem.removeChangeListener (this); impl->ctx.removeListener (this); stopTimer(); if (impl->dirty) impl->commit(); }
    void ShaperEditor::setSlot (int g, int b) { if (impl->dirty) impl->commit(); impl->slot = g; impl->base = b; impl->load(); repaint(); }
    void ShaperEditor::timerCallback() { if (impl->dirty) impl->commit(); stopTimer(); }
    void ShaperEditor::paramChanged (int num, float) { if (isVisible() && num >= impl->base && num < impl->base + 10) repaint(); }
    void ShaperEditor::changeListenerCallback (juce::ChangeBroadcaster*)
    {
        if (impl->dirty || impl->dragging) return;
        auto* sl = impl->mem.get (SoundMemory::EqBands, impl->slot);
        const auto now = sl ? sl->data : std::vector<float>();
        if (now.empty() ? ! impl->nodes.empty() : now != impl->lastData) { impl->load(); repaint(); }
    }

    void ShaperEditor::paint (juce::Graphics& g)
    {
        auto& I = *impl;
        auto box = getLocalBounds().toFloat(); paintInset (g, box, 4.0f);
        I.area = box.reduced (14, 12);
        const auto col = juce::Colour (0xfff0a050);
        g.setColour (juce::Colours::white.withAlpha (0.06f));
        for (int i = 1; i < 8; ++i) { g.drawVerticalLine ((int) (I.area.getX() + I.area.getWidth() * i / 8.0f), I.area.getY(), I.area.getBottom()); g.drawHorizontalLine ((int) (I.area.getY() + I.area.getHeight() * i / 8.0f), I.area.getX(), I.area.getRight()); }
        g.setColour (juce::Colours::white.withAlpha (0.2f)); g.drawHorizontalLine ((int) I.py (0), I.area.getX(), I.area.getRight()); g.drawVerticalLine ((int) I.px (0), I.area.getY(), I.area.getBottom());
        g.setColour (juce::Colours::white.withAlpha (0.12f)); g.drawLine (I.px (-1), I.py (-1), I.px (1), I.py (1));
        const int md = I.mode(); 
        // the transfer function the DSP applies for this mode (nodes in the editor are the curve of the positive / full range)
        juce::Path p;
        for (int i = 0; i <= 400; ++i)
        {
            const double x = -1.0 + 2.0 * i / 400.0, y = shaper::shape (I.nodes, md, x);
            if (i == 0) p.startNewSubPath (I.px (x), I.py (y)); else p.lineTo (I.px (x), I.py (y));
        }
        g.setColour (col); g.strokePath (p, juce::PathStrokeType (2.0f));
        if (md != 0)
        {
            g.setColour (dim); g.setFont (font (9.0f, true));
            g.drawText (md == 1 ? "MIRROR: THE CURVE'S RIGHT HALF IS MIRRORED (ODD)" : "RECTIFIED: THE INPUT IS FOLDED TO ITS ABSOLUTE VALUE", getLocalBounds().reduced (16, 12), juce::Justification::topLeft);
        }
        else if (I.nodes.size() < 2)
        {
            g.setColour (dim); g.setFont (font (9.0f, true));
            g.drawText ("DOUBLE-CLICK TO ADD NODES  -  RIGHT-CLICK FOR PRESETS", getLocalBounds().reduced (16, 12), juce::Justification::topLeft);
        }
        else
        {
            g.setColour (dim); g.setFont (font (9.0f, true));
            g.drawText ("INPUT -> OUTPUT   DRAG NODES, DRAG DIAMONDS FOR CURVATURE, DOUBLE-CLICK ADDS / REMOVES", getLocalBounds().reduced (16, 12), juce::Justification::topLeft);
        }
        for (int i = 0; i + 1 < (int) I.nodes.size(); ++i)
        {
            if (I.nodes[(size_t) i + 1].x - I.nodes[(size_t) i].x <= 0.06f) continue;
            auto h = I.segHandle (i); const bool hi = I.hotSeg == i || I.dragSeg == i;
            juce::Path d; d.addQuadrilateral (h.x, h.y - 5, h.x + 5, h.y, h.x, h.y + 5, h.x - 5, h.y);
            g.setColour (hi ? col : col.withAlpha (0.5f)); g.fillPath (d);
        }
        for (int i = 0; i < (int) I.nodes.size(); ++i)
        {
            const float x = I.px (I.nodes[(size_t) i].x), y = I.py (I.nodes[(size_t) i].y); const bool hi = I.hot == i || I.drag == i;
            g.setColour (juce::Colour (0xff131415)); g.fillEllipse (x - 6, y - 6, 12, 12);
            g.setColour (hi ? juce::Colours::white : col); g.drawEllipse (x - 6, y - 6, 12, 12, 2.0f);
        }
    }

    void ShaperEditor::mouseMove (const juce::MouseEvent& e)
    {
        auto& I = *impl; const int h = I.nodeAt (e.position), s = h >= 0 ? -1 : I.segAt (e.position);
        if (h != I.hot || s != I.hotSeg) { I.hot = h; I.hotSeg = s; repaint(); }
    }
    void ShaperEditor::mouseExit (const juce::MouseEvent&) { impl->hot = impl->hotSeg = -1; repaint(); }

    void ShaperEditor::mouseDown (const juce::MouseEvent& e)
    {
        auto& I = *impl;
        if (e.mods.isPopupMenu())
        {
            const int n = I.nodeAt (e.position);
            juce::PopupMenu m;
            if (n >= 0) m.addItem (1000, "Delete node");
            else m.addItem (1001, "Reset curvature of all segments");
            m.addSeparator();
            for (int i = 0; i < 7; ++i) m.addItem (1 + i, juce::String ("Preset: ") + shaper::presetName (i));
            m.addItem (900, "Clear (no nodes = identity)");
            m.showMenuAsync (juce::PopupMenu::Options(), [this, n] (int r)
            {
                auto& J = *impl;
                if (r >= 1 && r <= 7) J.nodes = shaper::preset (r - 1);
                else if (r == 900) J.nodes.clear();
                else if (r == 1000 && n >= 0 && n < (int) J.nodes.size()) J.nodes.erase (J.nodes.begin() + n);
                else if (r == 1001) for (auto& q : J.nodes) q.c = 0.0f;
                else return;
                J.changed();
            });
            return;
        }
        I.dragging = true;
        I.drag = I.nodeAt (e.position); I.dragSeg = I.drag >= 0 ? -1 : I.segAt (e.position);
        if (I.dragSeg >= 0) { I.segStartC = I.nodes[(size_t) I.dragSeg].c; I.segStartY = e.position.y; }
    }
    void ShaperEditor::mouseDrag (const juce::MouseEvent& e)
    {
        auto& I = *impl;
        if (I.drag >= 0 && I.drag < (int) I.nodes.size())
        {
            auto n = I.nodes[(size_t) I.drag]; const bool fine = e.mods.isShiftDown();
            double x = I.ux (e.position.x), y = I.uy (e.position.y);
            if (fine) { x = std::round (x * 20.0) / 20.0; y = std::round (y * 20.0) / 20.0; }
            n.x = (float) x; n.y = (float) y; I.nodes[(size_t) I.drag] = n;
            // keep the list sorted while dragging, follow the node
            const auto moved = n;
            std::stable_sort (I.nodes.begin(), I.nodes.end(), [] (const shaper::Node& a, const shaper::Node& b) { return a.x < b.x; });
            for (int i = 0; i < (int) I.nodes.size(); ++i) if (I.nodes[(size_t) i].x == moved.x && I.nodes[(size_t) i].y == moved.y) { I.drag = i; break; }
            I.changed();
        }
        else if (I.dragSeg >= 0 && I.dragSeg + 1 < (int) I.nodes.size())
        {
            // dragging the handle up bends the segment toward its end value first, down the other way (sign follows the segment direction)
            const bool rising = I.nodes[(size_t) I.dragSeg + 1].y >= I.nodes[(size_t) I.dragSeg].y;
            const float dy = (I.segStartY - e.position.y) / (I.area.getHeight() * 0.35f);
            I.nodes[(size_t) I.dragSeg].c = juce::jlimit (-1.0f, 1.0f, I.segStartC + (rising ? -dy : dy));
            I.changed();
        }
    }
    void ShaperEditor::mouseUp (const juce::MouseEvent&) { impl->dragging = false; impl->drag = impl->dragSeg = -1; if (impl->dirty) impl->commit(); repaint(); }
    void ShaperEditor::mouseDoubleClick (const juce::MouseEvent& e)
    {
        auto& I = *impl; const int n = I.nodeAt (e.position);
        if (n >= 0) I.nodes.erase (I.nodes.begin() + n);
        else if ((int) I.nodes.size() < shaper::MAXN)
        {
            if (I.nodes.size() < 2 && I.nodes.empty()) { I.nodes.push_back ({ -1.0f, -1.0f, 0.0f }); I.nodes.push_back ({ 1.0f, 1.0f, 0.0f }); }
            const double x = I.ux (e.position.x);
            I.nodes.push_back ({ (float) x, (float) I.uy (e.position.y), 0.0f });
            std::stable_sort (I.nodes.begin(), I.nodes.end(), [] (const shaper::Node& a, const shaper::Node& b) { return a.x < b.x; });
        }
        else return;
        I.changed();
    }
}
