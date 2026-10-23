#include "NjoWidgets.h"

namespace njo
{
    using namespace theme;

    ParamWidget::ParamWidget (Ctx& c, int n) : ctx (c), paramNum (n)
    {
        sp = findSpec (n);
        jassert (sp != nullptr);
        val = ctx.get (n);
        ctx.addListener (this);
        setRepaintsOnMouseActivity (false);
    }

    ParamWidget::~ParamWidget() { ctx.removeListener (this); }

    juce::String ParamWidget::valueString() const
    {
        if (valueText) return valueText (val);
        return formatValue (*sp, val, ctx.fxSlotTypes());
    }

    void ParamWidget::paramChanged (int n, float v)
    {
        if (n == paramNum) { val = v; valueUpdated(); if (hover || dragging) ctx.lcd (sp->label, valueString()); }
        else if (sp->num >= 541 && sp->num < 891 && fxLocate (sp->num).valid) repaint();   // fx knobs depend on the slot type
        else if (ctx.isModTarget (paramNum) && ((n >= 307 && n <= 336) || (n >= 472 && n <= 501))) repaint();   // modulation ring
    }

    void ParamWidget::setValueFromUser (float v)
    {
        v = juce::jlimit ((float) sp->min, (float) sp->max, v);
        if (sp->kind == "btn" || sp->kind == "sel" || sp->kind == "stp") v = (float) juce::roundToInt (v);
        ctx.set (paramNum, v);
        val = ctx.get (paramNum);
        valueUpdated();
        ctx.lcd (sp->label, valueString());
    }

    bool ParamWidget::isInterestedInDragSource (const SourceDetails& d)
    {
        auto desc = d.description.toString();
        return desc.startsWith (kModDrag) && ctx.isModTarget (paramNum)
            && modSourceAllowed (desc.fromFirstOccurrenceOf (kModDrag, false, false).getIntValue(), paramNum);
    }

    void ParamWidget::itemDropped (const SourceDetails& d)
    {
        modHover = false;
        int src = d.description.toString().fromFirstOccurrenceOf (kModDrag, false, false).getIntValue();
        auto t = modTarget().at (paramNum);
        int slot = ctx.modAssign (src, t.first, 0.5f);
        if (slot < 0) ctx.status ("MOD MATRIX FULL (20 SLOTS)");
        else if (onModDropped) onModDropped (*this);
        repaint();
    }

    void ParamWidget::drawModRing (juce::Graphics& g, juce::Rectangle<float> knob)
    {
        if (! ctx.isModTarget (paramNum)) return;
        auto t = modTarget().at (paramNum);
        std::vector<ModSlot> mods;
        for (auto& m : ctx.modsFor (t.first)) if (std::abs (m.amt) > 0.0005f) mods.push_back (m);
        if (modHover) { g.setColour (red.withAlpha (0.35f)); g.fillEllipse (knob.expanded (3)); }
        if (mods.empty()) return;
        float n = (float) sp->toNorm (val);
        auto c = knob.getCentre(); float r = knob.getWidth() * 0.5f + 1.0f;
        float a0 = juce::MathConstants<float>::pi * 1.25f, span = juce::MathConstants<float>::pi * 1.5f;
        for (size_t k = 0; k < mods.size() && k < 3; ++k)
        {
            float n1 = juce::jlimit (0.0f, 1.0f, n + mods[k].amt * t.second);
            juce::Path p; p.addCentredArc (c.x, c.y, r, r, 0.0f, a0 + span * juce::jmin (n, n1), a0 + span * juce::jmax (n, n1), true);
            g.setColour (srcColour (mods[k].src));
            g.strokePath (p, juce::PathStrokeType (3.0f, juce::PathStrokeType::curved, juce::PathStrokeType::rounded));
        }
        // dot with the number of sources
        g.setColour (srcColour (mods[0].src));
        auto d = juce::Rectangle<float> (knob.getRight() - 4, knob.getY() - 2, 9, 9);
        g.fillEllipse (d);
        if (mods.size() > 1) { g.setColour (juce::Colours::black); g.setFont (font (7.0f, true)); g.drawText (juce::String ((int) mods.size()), d, juce::Justification::centred); }
    }

    // ------------------------------------------------------------------ knob
    void KnobWidget::paint (juce::Graphics& g)
    {
        auto b = getLocalBounds().toFloat();
        float labelH = 12.0f;
        auto kr = b.withTrimmedBottom (labelH).reduced (3.0f);
        float d = juce::jmin (kr.getWidth(), kr.getHeight());
        auto knob = juce::Rectangle<float> (d, d).withCentre (kr.getCentre());
        paintKnob (g, knob.reduced (2.0f), (float) sp->toNorm (val), sp->min < 0 && sp->max > 0, hover, dragging);
        drawModRing (g, knob.reduced (1.0f));
        g.setColour (dragging || hover ? ink : dim);
        g.setFont (font (compact ? 8.0f : 9.0f, true));
        auto lb = b.removeFromBottom (labelH);
        juce::String t = (dragging ? valueString() : labelText()).toUpperCase();
        g.drawText (t, lb.toNearestInt(), juce::Justification::centred, true);
    }

    void KnobWidget::mouseDown (const juce::MouseEvent& e)
    {
        if (e.mods.isPopupMenu()) { setValueFromUser ((float) sp->init); return; }
        dragging = true; startN = sp->toNorm (val); startY = e.y; ctx.begin (paramNum);
        setMouseCursor (juce::MouseCursor::NoCursor); repaint();
    }

    void KnobWidget::mouseDrag (const juce::MouseEvent& e)
    {
        double sens = e.mods.isShiftDown() ? 0.0012 : 0.006;
        setValueFromUser ((float) sp->fromNorm (startN + (startY - e.y) * sens));
    }

    void KnobWidget::mouseUp (const juce::MouseEvent&)
    {
        dragging = false; ctx.end (paramNum); setMouseCursor (juce::MouseCursor::NormalCursor); repaint();
    }

    void KnobWidget::mouseDoubleClick (const juce::MouseEvent&) { setValueFromUser ((float) sp->init); }

    void KnobWidget::mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w)
    {
        double step = (e.mods.isShiftDown() ? 0.002 : 0.02) * (w.deltaY > 0 ? 1 : -1);
        setValueFromUser ((float) sp->fromNorm (sp->toNorm (val) + step));
    }

    // ------------------------------------------------------------------ slider
    juce::Rectangle<float> SliderWidget::trackRect() const
    {
        auto b = getLocalBounds().toFloat();
        return b.withTrimmedTop (b.getHeight() - 14.0f).reduced (0, 3.0f);
    }

    void SliderWidget::paint (juce::Graphics& g)
    {
        auto b = getLocalBounds().toFloat();
        g.setFont (font (8.5f, true)); g.setColour (hover || dragging ? ink : dim);
        g.drawText (labelText().toUpperCase(), b.withHeight (11).toNearestInt(), juce::Justification::topLeft, true);
        g.setFont (mono (8.5f, true)); g.setColour (orange);
        g.drawText (valueString(), b.withHeight (11).toNearestInt(), juce::Justification::topRight, true);
        auto t = trackRect();
        g.setColour (juce::Colour (0xff090303)); g.fillRoundedRectangle (t, 2.0f);
        g.setColour (juce::Colour (0xff3a1a17)); g.drawRoundedRectangle (t, 2.0f, 1.0f);
        float n = (float) sp->toNorm (val);
        float z = (sp->min < 0 && sp->max > 0) ? (float) (-sp->min / (sp->max - sp->min)) : 0.0f;
        float x0 = t.getX() + t.getWidth() * juce::jmin (n, z), x1 = t.getX() + t.getWidth() * juce::jmax (n, z);
        g.setColour (red.withAlpha (0.85f)); g.fillRoundedRectangle (x0, t.getY() + 1, juce::jmax (1.0f, x1 - x0), t.getHeight() - 2, 1.5f);
        if (ctx.isModTarget (paramNum))
        {
            auto tg = modTarget().at (paramNum);
            auto mods = ctx.modsFor (tg.first);
            for (auto& m : mods) if (std::abs (m.amt) > 0.0005f)
            {
                float a = n, b2 = juce::jlimit (0.0f, 1.0f, n + m.amt * tg.second);
                g.setColour (srcColour (m.src).withAlpha (0.9f));
                g.fillRect (t.getX() + t.getWidth() * juce::jmin (a, b2), t.getY() - 1, juce::jmax (1.5f, t.getWidth() * std::abs (b2 - a)), 3.0f);
                break;
            }
            if (modHover) { g.setColour (red.withAlpha (0.3f)); g.fillRoundedRectangle (getLocalBounds().toFloat(), 3.0f); }
        }
        float tx = t.getX() + t.getWidth() * n;
        g.setColour (juce::Colour (0xff85868b)); g.fillRoundedRectangle (tx - 3.0f, t.getY() - 3.0f, 6.0f, t.getHeight() + 6.0f, 1.5f);
        g.setColour (red); g.fillRect (tx - 3.0f, t.getY() + t.getHeight() * 0.36f, 6.0f, 2.0f);
    }

    void SliderWidget::setFromX (float x)
    {
        auto t = trackRect();
        double n = t.getWidth() > 0 ? juce::jlimit (0.0, 1.0, (double) ((x - t.getX()) / t.getWidth())) : 0.0;
        setValueFromUser ((float) sp->fromNorm (n));
    }

    void SliderWidget::mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w)
    {
        double step = (e.mods.isShiftDown() ? 0.002 : 0.02) * (w.deltaY > 0 ? 1 : -1);
        setValueFromUser ((float) sp->fromNorm (sp->toNorm (val) + step));
    }

    // ------------------------------------------------------------------ buttons
    juce::Rectangle<float> ButtonsWidget::cellRect (int i) const
    {
        auto b = getLocalBounds().toFloat();
        if (showLabel) b = b.withTrimmedTop (13.0f);
        int n = sp->labels.size(), c = cols > 0 ? cols : (n > 3 ? juce::jmin (n, 4) : n);
        int rows = (n + c - 1) / c;
        float w = b.getWidth() / (float) c, h = b.getHeight() / (float) rows;
        return { b.getX() + (float) (i % c) * w, b.getY() + (float) (i / c) * h, w, h };
    }

    int ButtonsWidget::indexAt (juce::Point<float> p) const
    {
        for (int i = 0; i < sp->labels.size(); ++i) if (cellRect (i).contains (p)) return i;
        return -1;
    }

    void ButtonsWidget::paint (juce::Graphics& g)
    {
        auto b = getLocalBounds().toFloat();
        if (showLabel)
        {
            g.setFont (font (8.5f, true)); g.setColour (dim);
            g.drawText (labelText().toUpperCase(), b.withHeight (11).toNearestInt(), juce::Justification::topLeft, true);
            g.setFont (mono (8.5f, true)); g.setColour (orange);
            g.drawText (valueString(), b.withHeight (11).toNearestInt(), juce::Justification::topRight, true);
        }
        int cur = juce::roundToInt (val - sp->min);
        for (int i = 0; i < sp->labels.size(); ++i)
        {
            auto r = cellRect (i).reduced (0.5f);
            paintButton (g, r, i == cur, i == hoverIdx, false, 2.0f);
            g.setColour (i == cur ? juce::Colours::white : ink);
            g.setFont (font (9.0f, true));
            g.drawText (sp->labels[i], r.toNearestInt(), juce::Justification::centred, true);
        }
    }

    void ButtonsWidget::mouseDown (const juce::MouseEvent& e)
    {
        int i = indexAt (e.position);
        if (i >= 0) { ctx.begin (paramNum); setValueFromUser ((float) (sp->min + i)); ctx.end (paramNum); }
    }

    void ButtonsWidget::mouseMove (const juce::MouseEvent& e) { int i = indexAt (e.position); if (i != hoverIdx) { hoverIdx = i; repaint(); } }

    // ------------------------------------------------------------------ dropdown
    SelectWidget::SelectWidget (Ctx& c, int n) : ParamWidget (c, n)
    {
        names = sp->labels; groups = sp->groups;
    }

    void SelectWidget::setOptions (const juce::StringArray& n, const std::vector<std::pair<int, juce::String>>& g) { names = n; groups = g; repaint(); }
    void SelectWidget::resized() {}

    void SelectWidget::paint (juce::Graphics& g)
    {
        auto b = getLocalBounds().toFloat();
        g.setFont (font (8.5f, true)); g.setColour (dim);
        g.drawText (labelText().toUpperCase(), b.withHeight (11).toNearestInt(), juce::Justification::topLeft, true);
        auto r = b.withTrimmedTop (12.0f).reduced (0, 0.5f);
        paintButton (g, r, false, hover, false, 3.0f);
        g.setColour (ink); g.setFont (font (11.0f, true));
        int idx = juce::jlimit (0, juce::jmax (0, names.size() - 1), juce::roundToInt (val - sp->min));
        g.drawText (names.size() ? names[idx] : valueString(), r.reduced (7, 0).toNearestInt(), juce::Justification::centredLeft, true);
        juce::Path t; auto a = juce::Rectangle<float> (r.getRight() - 15, r.getCentreY() - 3, 9, 6);
        t.addTriangle (a.getX(), a.getY(), a.getRight(), a.getY(), a.getCentreX(), a.getBottom());
        g.setColour (red); g.fillPath (t);
    }

    void SelectWidget::mouseDown (const juce::MouseEvent&)
    {
        juce::PopupMenu m;
        size_t gi = 0;
        for (int i = 0; i < names.size(); ++i)
        {
            while (gi < groups.size() && groups[gi].first == i) { if (groups[gi].second.isNotEmpty()) m.addSectionHeader (groups[gi].second); ++gi; }
            m.addItem (i + 1, names[i], true, juce::roundToInt (val - sp->min) == i);
        }
        auto self = juce::Component::SafePointer<SelectWidget> (this);
        m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (this).withMinimumWidth (getWidth()).withMaximumNumColumns (3),
                         [self] (int r) { if (self != nullptr && r > 0) { self->ctx.begin (self->paramNum); self->setValueFromUser ((float) (self->sp->min + r - 1)); self->ctx.end (self->paramNum); } });
    }

    // ------------------------------------------------------------------ stepper
    void StepperWidget::paint (juce::Graphics& g)
    {
        auto b = getLocalBounds().toFloat().reduced (0, 1.0f);
        float w = 18.0f;
        paintButton (g, b.removeFromLeft (w), false, false, false, 2.0f);
        paintButton (g, b.removeFromRight (w), false, false, false, 2.0f);
        g.setColour (ink); g.setFont (font (11.0f, true));
        g.drawText (juce::CharPointer_UTF8 ("\xe2\x88\x92"), getLocalBounds().removeFromLeft ((int) w), juce::Justification::centred);
        g.drawText ("+", getLocalBounds().removeFromRight ((int) w), juce::Justification::centred);
        g.setColour (orange); g.setFont (mono (10.0f, true));
        g.drawText (valueString(), b.toNearestInt(), juce::Justification::centred);
    }

    void StepperWidget::mouseDown (const juce::MouseEvent& e)
    {
        int d = e.x < 20 ? -1 : (e.x > getWidth() - 20 ? 1 : 0);
        if (d) { ctx.begin (paramNum); setValueFromUser (val + (float) d); ctx.end (paramNum); }
    }

    std::unique_ptr<ParamWidget> makeWidget (Ctx& c, int num, bool asKnob)
    {
        auto* s = findSpec (num);
        jassert (s);
        if (s->kind == "btn") return std::make_unique<ButtonsWidget> (c, num);
        if (s->kind == "sel") return std::make_unique<SelectWidget> (c, num);
        if (s->kind == "stp") return std::make_unique<StepperWidget> (c, num);
        if (asKnob || s->kind == "knb") return std::make_unique<KnobWidget> (c, num);
        return std::make_unique<SliderWidget> (c, num);
    }
}
