// Parameter widgets: knob, slider, segment buttons, dropdown, stepper. All of them are bound to one parameter number,
// follow host / preset changes through Ctx and are drop targets for modulation sources when the parameter can be modulated.
#pragma once
#include "NjoCore.h"

namespace njo
{
    inline const juce::String kModDrag = "njo.mod:";   // drag description prefix: kModDrag + source number

    class ParamWidget : public juce::Component, public juce::DragAndDropTarget, protected Ctx::Listener
    {
    public:
        ParamWidget (Ctx&, int paramNum);
        ~ParamWidget() override;

        int num() const { return paramNum; }
        const Spec& spec() const { return *sp; }
        float value() const { return val; }
        void setValueFromUser (float v);               // clamps, sends to the backend, repaints
        void setLabelOverride (const juce::String& s) { labelOverride = s; repaint(); }   // e.g. Plaits engine dependent names
        void setValueTextOverride (std::function<juce::String (float)> f) { valueText = std::move (f); repaint(); }
        juce::String labelText() const { return labelOverride.isNotEmpty() ? labelOverride : sp->name(); }
        juce::String valueString() const;
        void setLook (bool compactLabel) { compact = compactLabel; }

        // drag and drop modulation
        bool isInterestedInDragSource (const SourceDetails&) override;
        void itemDragEnter (const SourceDetails&) override { modHover = true; repaint(); }
        void itemDragExit (const SourceDetails&) override  { modHover = false; repaint(); }
        void itemDropped (const SourceDetails&) override;
        std::function<void (ParamWidget&)> onModDropped;     // the shell shows the amount popup

    protected:
        void paramChanged (int n, float v) override;
        virtual void valueUpdated() { repaint(); }
        void drawModRing (juce::Graphics&, juce::Rectangle<float> knob);
        void mouseEnter (const juce::MouseEvent&) override { hover = true; ctx.lcd (spec().label, valueString()); repaint(); }
        void mouseExit (const juce::MouseEvent&) override  { hover = false; repaint(); }

        Ctx& ctx;
        const Spec* sp;
        int paramNum;
        float val = 0;
        bool hover = false, dragging = false, modHover = false, compact = false;
        juce::String labelOverride;
        std::function<juce::String (float)> valueText;
    };

    class KnobWidget : public ParamWidget
    {
    public:
        KnobWidget (Ctx& c, int n) : ParamWidget (c, n) {}
        void paint (juce::Graphics&) override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;
        void mouseUp (const juce::MouseEvent&) override;
        void mouseDoubleClick (const juce::MouseEvent&) override;
        void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;
    private:
        double startN = 0; int startY = 0;
    };

    class SliderWidget : public ParamWidget
    {
    public:
        SliderWidget (Ctx& c, int n) : ParamWidget (c, n) {}
        void paint (juce::Graphics&) override;
        void mouseDown (const juce::MouseEvent& e) override { dragging = true; ctx.begin (paramNum); setFromX (e.position.x); }
        void mouseDrag (const juce::MouseEvent& e) override { setFromX (e.position.x); }
        void mouseUp (const juce::MouseEvent&) override { dragging = false; ctx.end (paramNum); repaint(); }
        void mouseDoubleClick (const juce::MouseEvent&) override { setValueFromUser ((float) sp->init); }
        void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;
        juce::Rectangle<float> trackRect() const;
    private:
        void setFromX (float x);
    };

    // a row of buttons (Poly / Mono, Off / On, Main / Bus 1 / Bus 2 ...); wide lists wrap to several rows
    class ButtonsWidget : public ParamWidget
    {
    public:
        ButtonsWidget (Ctx& c, int n, int columns = 0) : ParamWidget (c, n), cols (columns) {}
        void paint (juce::Graphics&) override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseMove (const juce::MouseEvent&) override;
        void mouseExit (const juce::MouseEvent& e) override { hoverIdx = -1; ParamWidget::mouseExit (e); }
        void setShowLabel (bool b) { showLabel = b; repaint(); }
    private:
        int indexAt (juce::Point<float>) const;
        juce::Rectangle<float> cellRect (int i) const;
        int cols, hoverIdx = -1; bool showLabel = true;
    };

    class SelectWidget : public ParamWidget
    {
    public:
        SelectWidget (Ctx& c, int n);
        void paint (juce::Graphics&) override;
        void resized() override;
        void mouseDown (const juce::MouseEvent&) override;
        void setOptions (const juce::StringArray& names, const std::vector<std::pair<int, juce::String>>& groups = {});   // replaces the spec's options (same value range)
    private:
        void valueUpdated() override { repaint(); }
        juce::StringArray names; std::vector<std::pair<int, juce::String>> groups;
    };

    class StepperWidget : public ParamWidget
    {
    public:
        StepperWidget (Ctx& c, int n) : ParamWidget (c, n) {}
        void paint (juce::Graphics&) override;
        void mouseDown (const juce::MouseEvent&) override;
    };

    // chooses the right widget for a spec: knb/sld-in-knob -> knob etc.
    std::unique_ptr<ParamWidget> makeWidget (Ctx&, int num, bool asKnob);
}
