// Patch page of Njohrr Modular: the nodes (Synth, Audio In, 16 effect modules, Out) and their cables.
// Parameters (tools/modular/build_matrix.py): cable of destination d (0..15 module, 16 Out), cable c: 9700 + 8 * d + 2 * c (+1 gain);
// node n position 9850 + 2 * n (+1 y).  Source values of a cable: 0 off, 1 Synth, 2 Audio In, 3.. module 1..16 (= node + 1).
#include "../NjoPages.h"
#include "../NjoTheme.h"

namespace njo
{
    using namespace theme;

    namespace
    {
        constexpr int kNodes = 19, kPosBase = 9850, kCabBase = 9700, kPanelW = 296;
        constexpr float kNodeW = 116.0f, kNodeH = 36.0f;
        int destOf (int node)            { return node >= 2 ? node - 2 : -1; }
        int cabId (int d, int c)         { return kCabBase + 8 * d + 2 * c; }
        int srcValueOf (int node)        { return node == 0 ? 1 : (node == 1 ? 2 : node + 1); }
        int nodeOfSrc (int v)            { return v == 1 ? 0 : (v == 2 ? 1 : v >= 3 ? v - 1 : -1); }
        int moduleSlotId (int node)      { return fxSlotId (fxG (0, node - 2)); }
        juce::Colour colourOf (int node) { return node == 0 ? orange : (node == 1 ? blue : (node == 18 ? juce::Colour (0xffd9d4cf) : red)); }
    }

    struct PatchPage::Impl : private Ctx::Listener, private juce::AsyncUpdater
    {
        Impl (PatchPage& o, Ctx& c) : owner (o), ctx (c) { ctx.addListener (this); rebuildPanel(); }
        ~Impl() override { cancelPendingUpdate(); ctx.removeListener (this); }

        PatchPage& owner; Ctx& ctx;
        int selected = 18, moving = -1, linkFrom = -1;
        juce::Point<float> grab, mouse;
        std::vector<std::unique_ptr<ParamWidget>> panel;
        juce::Rectangle<float> canvas, side;

        void paramChanged (int num, float) override
        {
            if (num >= kCabBase && num < kPosBase + 2 * kNodes) { owner.repaint(); return; }
            if (selected >= 2 && selected <= 17 && num == moduleSlotId (selected)) { triggerAsyncUpdate(); return; }
            owner.repaint();
        }
        void handleAsyncUpdate() override { rebuildPanel(); owner.repaint(); }

        juce::Rectangle<float> nodeRect (int n) const
        {
            float x = ctx.get (kPosBase + 2 * n), y = ctx.get (kPosBase + 2 * n + 1);
            return { canvas.getX() + x * (canvas.getWidth() - kNodeW), canvas.getY() + y * (canvas.getHeight() - kNodeH), kNodeW, kNodeH };
        }
        juce::Point<float> outPort (int n) const { auto r = nodeRect (n); return { r.getRight(), r.getCentreY() }; }
        juce::Point<float> inPort (int n, int c) const { auto r = nodeRect (n); return { r.getX(), r.getY() + kNodeH * (c + 1) / 5.0f }; }
        static juce::Path cablePath (juce::Point<float> a, juce::Point<float> b)
        {
            float dx = juce::jmax (40.0f, std::abs (b.x - a.x) * 0.5f);
            juce::Path p; p.startNewSubPath (a); p.cubicTo (a.x + dx, a.y, b.x - dx, b.y, b.x, b.y); return p;
        }
        juce::String nodeName (int n) const
        {
            if (n == 0) return "SYNTH";
            if (n == 1) return "AUDIO IN";
            if (n == 18) return "OUT";
            int t = juce::roundToInt (ctx.get (moduleSlotId (n)));
            auto& types = fxTypes();
            return "M" + juce::String (n - 1) + "  " + (t > 0 && t < (int) types.size() ? types[(size_t) t].name : juce::String ("-"));
        }

        template <typename F> void forCables (F f)   // f (dest node, cable, source node, gain)
        {
            for (int d = 0; d < 17; ++d)
                for (int c = 0; c < 4; ++c)
                {
                    int s = nodeOfSrc (juce::roundToInt (ctx.get (cabId (d, c))));
                    if (s >= 0) f (d + 2, c, s, ctx.get (cabId (d, c) + 1));
                }
        }
        bool hitCable (juce::Point<float> p, int& dNode, int& cab) const
        {
            bool hit = false; float best = 7.0f;
            const_cast<Impl*> (this)->forCables ([&] (int dn, int c, int s, float)
            {
                juce::Path path = cablePath (outPort (s), inPort (dn, c));
                for (int i = 0; i <= 32; ++i)
                {
                    auto q = path.getPointAlongPath (path.getLength() * (float) i / 32.0f);
                    float dist = q.getDistanceFrom (p);
                    if (dist < best) { best = dist; dNode = dn; cab = c; hit = true; }
                }
            });
            return hit;
        }
        int nodeAt (juce::Point<float> p) const
        {
            for (int n = kNodes - 1; n >= 0; --n) if (nodeRect (n).contains (p)) return n;
            return -1;
        }

        void connect (int s, int dNode)
        {
            int d = destOf (dNode), v = srcValueOf (s), free = -1;
            for (int c = 0; c < 4; ++c)
            {
                int cur = juce::roundToInt (ctx.get (cabId (d, c)));
                if (cur == v) return;                      // this cable exists
                if (cur == 0 && free < 0) free = c;
            }
            if (free < 0) { ctx.status ("NODE FULL (4 CABLES)"); return; }
            ctx.set (cabId (d, free) + 1, 1.0f);
            ctx.set (cabId (d, free), (float) v);
        }

        void rebuildPanel()
        {
            for (auto& w : panel) owner.removeChildComponent (w.get());
            panel.clear();
            if (side.isEmpty()) return;
            auto add = [this] (std::unique_ptr<ParamWidget> w, juce::Rectangle<int> r) -> ParamWidget*
            {
                w->setBounds (r); owner.addAndMakeVisible (*w); panel.push_back (std::move (w)); return panel.back().get();
            };
            auto r = side.reduced (10, 8).toNearestInt();
            r.removeFromTop (24);
            if (selected >= 2 && selected <= 17)
            {
                const int tid = moduleSlotId (selected);
                const int ty = juce::roundToInt (ctx.get (tid));
                auto& types = fxTypes();
                const auto& t = types[(size_t) juce::jlimit (0, (int) types.size() - 1, ty)];
                add (makeWidget (ctx, tid, false), r.removeFromTop (34)); r.removeFromTop (4);
                auto row = r.removeFromTop (34);
                add (makeWidget (ctx, tid + 1, false), row.removeFromLeft (110)); row.removeFromLeft (6);
                add (makeWidget (ctx, tid + 2, false), row); r.removeFromTop (4);
                if (t.modes.size() > 0)
                {
                    auto* m = add (makeWidget (ctx, tid + 3, false), r.removeFromTop (34));
                    if (auto* s = dynamic_cast<SelectWidget*> (m)) s->setOptions (t.modes, t.groups);
                    r.removeFromTop (4);
                }
                auto kn = r.removeFromTop (130);
                for (int k = 0; k < 6; ++k)
                {
                    if (k >= (int) t.params.size()) continue;
                    auto cell = juce::Rectangle<int> (kn.getX() + (k % 3) * (kn.getWidth() / 3), kn.getY() + (k / 3) * 65, kn.getWidth() / 3, 62);
                    auto* w = add (makeWidget (ctx, tid + 4 + k, true), cell);
                    w->setLabelOverride (t.params[(size_t) k].name);
                }
                r.removeFromTop (6);
            }
            if (selected >= 2)
            {
                const int d = destOf (selected);
                for (int c = 0; c < 4; ++c)
                {
                    auto row = r.removeFromTop (34);
                    add (makeWidget (ctx, cabId (d, c), false), row.removeFromLeft (150)); row.removeFromLeft (6);
                    add (makeWidget (ctx, cabId (d, c) + 1, false), row); r.removeFromTop (3);
                }
            }
        }
    };

    PatchPage::PatchPage (Ctx& c) : impl (new Impl (*this, c)) { setWantsKeyboardFocus (false); }
    PatchPage::~PatchPage() = default;

    void PatchPage::resized()
    {
        auto r = getLocalBounds().toFloat();
        impl->side = r.removeFromRight ((float) kPanelW);
        r.removeFromRight (6.0f);
        impl->canvas = r.reduced (8.0f);
        impl->rebuildPanel();
    }

    void PatchPage::paint (juce::Graphics& g)
    {
        auto& m = *impl;
        paintCard (g, m.canvas.expanded (8.0f));
        paintCard (g, m.side);
        g.setColour (red); g.setFont (impact (14.0f));
        g.drawText (m.nodeName (m.selected), m.side.reduced (12, 8).removeFromTop (22).toNearestInt(), juce::Justification::centredLeft);
        // cables
        g.saveState(); g.reduceClipRegion (m.canvas.expanded (8.0f).toNearestInt());
        m.forCables ([&] (int dn, int c, int s, float gain)
        {
            auto path = Impl::cablePath (m.outPort (s), m.inPort (dn, c));
            bool sel = dn == m.selected;
            g.setColour (colourOf (s).withAlpha (sel ? 0.95f : 0.6f));
            g.strokePath (path, juce::PathStrokeType (sel ? 2.4f : 1.6f));
            if (std::abs (gain - 1.0f) > 0.005f)
            {
                auto mid = path.getPointAlongPath (path.getLength() * 0.5f);
                g.setColour (ink); g.setFont (mono (8.0f, true));
                g.drawText (juce::String (gain, 2), juce::Rectangle<float> (mid.x - 18, mid.y - 14, 36, 11).toNearestInt(), juce::Justification::centred);
            }
        });
        if (m.linkFrom >= 0)
        {
            g.setColour (colourOf (m.linkFrom).withAlpha (0.9f));
            g.strokePath (Impl::cablePath (m.outPort (m.linkFrom), m.mouse), juce::PathStrokeType (2.0f, juce::PathStrokeType::curved));
        }
        g.restoreState();
        // nodes
        for (int n = 0; n < kNodes; ++n)
        {
            auto r = m.nodeRect (n);
            bool isMod = n >= 2 && n <= 17;
            bool off = isMod && m.ctx.get (moduleSlotId (n) + 1) < 0.5f;
            g.setGradientFill (vertical (juce::Colour (0xff2c2e32), juce::Colour (0xff1c1d20), r));
            g.fillRoundedRectangle (r, 5.0f);
            g.setColour (n == m.selected ? red : line); g.drawRoundedRectangle (r, 5.0f, n == m.selected ? 2.0f : 1.0f);
            g.setColour (colourOf (n)); g.fillRect (r.getX() + 6, r.getY() + 5, 3.0f, r.getHeight() - 10);
            g.setColour (off ? dim : ink); g.setFont (font (10.5f, true));
            g.drawText (m.nodeName (n), r.withTrimmedLeft (16).withTrimmedRight (14).toNearestInt(), juce::Justification::centredLeft, true);
            if (n < 18) { g.setColour (colourOf (n)); g.fillEllipse (m.outPort (n).x - 5, m.outPort (n).y - 5, 10, 10); }
            if (n >= 2) { g.setColour (dim); for (int c = 0; c < 4; ++c) g.fillEllipse (m.inPort (n, c).x - 2.5f, m.inPort (n, c).y - 2.5f, 5, 5); }
        }
        g.setColour (dim); g.setFont (font (8.5f));
        g.drawText ("drag from a node's round output onto another node to connect  -  right-click a cable to remove it  -  drag a node to move it",
                    m.canvas.removeFromBottom (14).toNearestInt(), juce::Justification::centredLeft, true);
    }

    void PatchPage::select (int node) { impl->selected = juce::jlimit (0, kNodes - 1, node); impl->rebuildPanel(); repaint(); }

    void PatchPage::mouseDown (const juce::MouseEvent& e)
    {
        auto& m = *impl; auto p = e.position; m.mouse = p;
        int dn = 0, cab = 0;
        if (e.mods.isPopupMenu())
        {
            if (m.hitCable (p, dn, cab)) { m.ctx.set (cabId (destOf (dn), cab), 0.0f); repaint(); }
            return;
        }
        for (int n = 0; n < 18; ++n)
            if (m.outPort (n).getDistanceFrom (p) < 9.0f) { m.linkFrom = n; return; }
        int n = m.nodeAt (p);
        if (n >= 0)
        {
            m.moving = n; m.grab = p - m.nodeRect (n).getPosition();
            if (m.selected != n) { m.selected = n; m.rebuildPanel(); repaint(); }
        }
        else if (m.hitCable (p, dn, cab)) { m.selected = dn; m.rebuildPanel(); repaint(); }
    }

    void PatchPage::mouseDrag (const juce::MouseEvent& e)
    {
        auto& m = *impl; m.mouse = e.position;
        if (m.moving >= 0)
        {
            float x = (e.position.x - m.grab.x - m.canvas.getX()) / (m.canvas.getWidth() - kNodeW);
            float y = (e.position.y - m.grab.y - m.canvas.getY()) / (m.canvas.getHeight() - kNodeH);
            m.ctx.set (kPosBase + 2 * m.moving, juce::jlimit (0.0f, 1.0f, x));
            m.ctx.set (kPosBase + 2 * m.moving + 1, juce::jlimit (0.0f, 1.0f, y));
        }
        if (m.linkFrom >= 0 || m.moving >= 0) repaint();
    }

    void PatchPage::mouseUp (const juce::MouseEvent& e)
    {
        auto& m = *impl;
        if (m.linkFrom >= 0)
        {
            int n = m.nodeAt (e.position);
            if (n >= 2) { m.connect (m.linkFrom, n); m.selected = n; m.rebuildPanel(); }
            m.linkFrom = -1;
        }
        m.moving = -1; repaint();
    }
}
