#include "NjoEditor.h"
#include "NjoLfo.h"

namespace njo
{
    using namespace theme;

    namespace
    {
        // a flat painted button: used for the page rail, the OSC tabs and small toggles
        class NavButton : public juce::Component
        {
        public:
            enum Style { Rail, Tab, Mini };
            NavButton (Style s, const juce::String& t, const juce::String& big = {}) : style (s), text (t), number (big) { setMouseCursor (juce::MouseCursor::PointingHandCursor); }
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                if (style == Rail)
                {
                    paintButton (g, r, on, over, false, 8.0f);
                    g.setColour (on ? juce::Colours::white.withAlpha (0.85f) : dim); g.setFont (impact (26.0f));
                    g.drawText (number, r.withTrimmedBottom (r.getHeight() * 0.45f).toNearestInt(), juce::Justification::centredBottom);
                    g.setColour (on ? juce::Colours::white : ink); g.setFont (font (8.5f, true));
                    g.drawText (text, r.withTrimmedTop (r.getHeight() * 0.58f).toNearestInt(), juce::Justification::centredTop);
                }
                else
                {
                    if (on) { g.setColour (style == Tab ? panel2 : red); g.fillRoundedRectangle (r, 1.5f); g.setColour (red); g.drawRoundedRectangle (r, 1.5f, 1.0f); }
                    else { g.setColour (panel); g.fillRoundedRectangle (r, 1.5f); g.setColour (over ? red : line); g.drawRoundedRectangle (r, 1.5f, 1.0f); }
                    g.setColour (on ? (style == Tab ? red : juce::Colour (0xff111111)) : (over ? ink : dim)); g.setFont (font (9.0f, true));
                    g.drawText (text, r.toNearestInt(), juce::Justification::centred);
                }
            }
            void mouseEnter (const juce::MouseEvent&) override { over = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { over = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && onClick) onClick(); }
            void setOn (bool b) { if (on != b) { on = b; repaint(); } }
            std::function<void()> onClick;
            Style style; juce::String text, number; bool on = false, over = false;
        };
    }

    struct EditorContent::Impl
    {
        juce::OwnedArray<NavButton> rail, tabs;
        std::unique_ptr<NavButton> stripToggle, sizeButton;
        juce::Rectangle<int> topBar, lcdRect, stripRect, mainRect, stageRect, subRect, mgrRect;
        juce::Component* shownPage = nullptr;
    };

    EditorContent::EditorContent (Backend& be)
        : ctx (be), memory (ctx), fm (ctx), glob (ctx), fx (ctx), editors (ctx), editorsFull (ctx), matrix (ctx), manager (ctx, memory, *this), impl (new Impl)
    {
        ctx.lfoShapes = std::make_shared<LfoShapes> (ctx);
        ctx.onLcd = [this] (const juce::String& n, const juce::String& v) { lcdName = n.toUpperCase(); lcdValue = v; repaint (impl->lcdRect); };
        ctx.onStatus = [this] (const juce::String& t) { status = t; statusUntil = juce::Time::getMillisecondCounterHiRes() + 2500; repaint (impl->lcdRect); };

        const char* rn[] = { "SYNTH", "EFFECTS", "MODULATION" };
        for (int i = 0; i < 3; ++i)
        {
            auto* b = impl->rail.add (new NavButton (NavButton::Rail, rn[i], juce::String (i + 1)));
            b->onClick = [this, i] { setGroup ((Group) i); };
            addAndMakeVisible (b);
        }
        for (int i = 0; i < 8; ++i)
        {
            juce::String t = i < 6 ? "OSC " + juce::String (i + 1) : (i == 6 ? "FM / PM / PD" : "GLOBAL");
            auto* b = impl->tabs.add (new NavButton (NavButton::Tab, t));
            b->onClick = [this, i] { setSynthPage (i); };
            addAndMakeVisible (b);
        }
        impl->stripToggle = std::make_unique<NavButton> (NavButton::Mini, juce::String (juce::CharPointer_UTF8 ("\xe2\x96\xbe")));
        impl->stripToggle->onClick = [this] { stripOpen = ! stripOpen; layoutAll(); };
        addAndMakeVisible (*impl->stripToggle);
        impl->sizeButton = std::make_unique<NavButton> (NavButton::Mini, "100%");
        impl->sizeButton->onClick = [this]
        {
            juce::PopupMenu m;
            for (float s : { 0.75f, 1.0f, 1.25f, 1.5f, 1.75f, 2.0f }) m.addItem (juce::roundToInt (s * 100), juce::String (juce::roundToInt (s * 100)) + "%");
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (impl->sizeButton.get()), [this] (int r)
            {
                if (r > 0 && onScaleRequested) { onScaleRequested ((float) r / 100.0f); impl->sizeButton->text = juce::String (r) + "%"; impl->sizeButton->repaint(); }
            });
        };
        addAndMakeVisible (*impl->sizeButton);

        for (int o = 0; o < OSC_N; ++o)
        {
            auto* p = osc.add (new OscPage (ctx, memory, o));
            p->onModDropped = [this] (ParamWidget& w) { showModPopup (ctx, w, w.num()); };
            addChildComponent (p);
        }
        fm.setOnOpenOsc ([this] (int o) { setSynthPage (o); });
        glob.onModDropped = [this] (ParamWidget& w) { showModPopup (ctx, w, w.num()); };
        fx.onModDropped = glob.onModDropped;
        addChildComponent (fm); addChildComponent (glob); addChildComponent (fx);
        addChildComponent (editorsFull); addChildComponent (matrix);
        addAndMakeVisible (editors);
        addAndMakeVisible (manager);
        setSize (BASE_W, BASE_H);
        setGroup (Synth);
        startTimerHz (20);
    }

    EditorContent::~EditorContent() = default;

    void EditorContent::timerCallback()
    {
        float l = ctx.be.getOutputLevel();
        l = juce::jmax (l, vuLevel * 0.85f);
        if (std::abs (l - vuLevel) > 0.002f) { vuLevel = l; repaint (impl->topBar); }
        if (statusUntil > 0 && juce::Time::getMillisecondCounterHiRes() > statusUntil) { statusUntil = 0; status = {}; repaint (impl->lcdRect); }
    }

    void EditorContent::setGroup (Group g)
    {
        currentGroup = g;
        for (int i = 0; i < 3; ++i) impl->rail[i]->setOn (i == (int) g);
        layoutAll();
    }

    void EditorContent::setSynthPage (int p)
    {
        currentSynthPage = juce::jlimit (0, 7, p);
        currentGroup = Synth;
        for (int i = 0; i < 3; ++i) impl->rail[i]->setOn (i == 0);
        layoutAll();
    }

    void EditorContent::resized() { layoutAll(); }

    void EditorContent::layoutAll()
    {
        auto r = getLocalBounds().reduced (10, 8);
        impl->topBar = r.removeFromTop (44);
        r.removeFromTop (3 + 6);
        r.removeFromLeft (66);
        r.removeFromLeft (8);
        // equal thirds with 6px gaps
        {
            auto rr = juce::Rectangle<int> (10, impl->topBar.getBottom() + 9, 66, r.getHeight());
            int h = (rr.getHeight() - 12) / 3;
            for (int i = 0; i < 3; ++i) impl->rail[i]->setBounds (rr.getX(), rr.getY() + i * (h + 6), rr.getWidth(), h);
        }
        impl->mainRect = r;

        bool synth = currentGroup == Synth, mod = currentGroup == Modulation;
        auto m = r;
        impl->subRect = synth ? m.removeFromTop (24) : juce::Rectangle<int>();
        if (synth) m.removeFromTop (6);
        for (int i = 0; i < impl->tabs.size(); ++i) impl->tabs[i]->setVisible (synth);
        if (synth)
        {
            auto s = impl->subRect; int x = s.getX();
            for (int i = 0; i < 6; ++i) { impl->tabs[i]->setBounds (x, s.getY(), 56, s.getHeight()); x += 59; }
            impl->tabs[7]->setBounds (s.getRight() - 62, s.getY(), 62, s.getHeight());
            impl->tabs[6]->setBounds (s.getRight() - 62 - 3 - 70, s.getY(), 70, s.getHeight());
            for (int i = 0; i < 8; ++i) impl->tabs[i]->setOn (i == currentSynthPage);
        }
        impl->mgrRect = m.removeFromTop (24); m.removeFromTop (6);
        manager.setBounds (impl->mgrRect);

        int stripH = mod ? 0 : (stripOpen ? 190 : 26);
        if (! mod) { impl->stripRect = m.removeFromBottom (stripH); m.removeFromBottom (6); }
        impl->stageRect = m;

        for (auto* p : osc) p->setVisible (false);
        fm.setVisible (false); glob.setVisible (false); fx.setVisible (false); editorsFull.setVisible (false); matrix.setVisible (false);
        editors.setVisible (false);
        if (synth)
        {
            if (currentSynthPage < 6) { osc[currentSynthPage]->setBounds (impl->stageRect); osc[currentSynthPage]->setVisible (true); }
            else if (currentSynthPage == 6) { fm.setBounds (impl->stageRect); fm.setVisible (true); }
            else { glob.setBounds (impl->stageRect); glob.setVisible (true); }
        }
        else if (currentGroup == Effects) { fx.setBounds (impl->stageRect); fx.setVisible (true); }
        else
        {
            // modulation page: editors on top, the 20 slot matrix below
            auto area = impl->stageRect;
            impl->stripRect = area.withHeight (0);
            auto top = area.removeFromTop (juce::roundToInt (area.getHeight() * 0.48f));
            area.removeFromTop (6);
            editorsFull.setBounds (top.withTrimmedTop (0)); editorsFull.setVisible (true);
            matrix.setBounds (area); matrix.setVisible (true);
        }
        if (! mod)
        {
            auto s = impl->stripRect;
            impl->stripToggle->setBounds (s.getRight() - 26, s.getY() + 3, 22, 18);
            impl->stripToggle->text = stripOpen ? juce::String (juce::CharPointer_UTF8 ("\xe2\x96\xbe")) : juce::String (juce::CharPointer_UTF8 ("\xe2\x96\xb4"));
            impl->stripToggle->setVisible (true);
            editors.setBounds (s.withTrimmedTop (26)); editors.setVisible (stripOpen);
        }
        else impl->stripToggle->setVisible (false);
        impl->sizeButton->setBounds (impl->topBar.getRight() - 346, impl->topBar.getY() + 12, 44, 20);
        impl->lcdRect = { impl->topBar.getRight() - 250, impl->topBar.getY() + 6, 214, 32 };
        repaint();
    }

    void EditorContent::paint (juce::Graphics& g)
    {
        g.fillAll (bg);
        // diagonal hatching like the web background
        g.setColour (juce::Colours::white.withAlpha (0.022f));
        for (int i = -BASE_H; i < BASE_W; i += 7) g.drawLine ((float) i, (float) BASE_H, (float) (i + BASE_H), 0.0f, 1.0f);
        // top bar
        auto t = impl->topBar.toFloat();
        g.setGradientFill (vertical (juce::Colour (0xff2c3035), juce::Colour (0xff1b1d20), t));
        g.fillRoundedRectangle (t, 22.0f);
        g.setColour (juce::Colour (0xff55565a)); g.drawRoundedRectangle (t.reduced (1), 22.0f, 2.0f);
        g.setColour (red); g.setFont (impact (21.0f));
        g.drawText ("NJOHRR", juce::Rectangle<int> (impl->topBar.getX() + 16, impl->topBar.getY(), 130, impl->topBar.getHeight()), juce::Justification::centredLeft);
        auto model = juce::Rectangle<float> (t.getX() + 138, t.getY() + 13, 72, 18);
        g.setColour (red); g.fillRoundedRectangle (model, 1.5f);
        g.setColour (juce::Colour (0xff111111)); g.setFont (font (10.0f, true)); g.drawText ("SYNTH", model.toNearestInt(), juce::Justification::centred);
        auto ver = juce::Rectangle<float> (t.getX() + 220, t.getY() + 14, 46, 16);
        g.setColour (line); g.drawRoundedRectangle (ver, 2.0f, 1.0f); g.setColour (dim); g.setFont (mono (8.0f, true)); g.drawText ("V1.0.0", ver.toNearestInt(), juce::Justification::centred);
        // VU
        auto vu = juce::Rectangle<float> (t.getX() + 280, t.getY() + 18, 36, 8);
        g.setColour (deep); g.fillRect (vu); g.setColour (line); g.drawRect (vu, 1.0f);
        g.setGradientFill (juce::ColourGradient (red, vu.getX(), 0, orange, vu.getRight(), 0, false)); g.fillRect (vu.reduced (1).withWidth ((vu.getWidth() - 2) * juce::jlimit (0.0f, 1.0f, vuLevel)));
        // LCD
        paintLcdBox (g, impl->lcdRect.toFloat());
        auto l = impl->lcdRect.reduced (8, 0);
        g.setFont (mono (9.0f, true)); g.setColour (red);
        if (status.isNotEmpty()) g.drawText (status, l, juce::Justification::centredLeft, true);
        else
        {
            g.setColour (red.withAlpha (0.7f)); g.drawText ("OSC", l.removeFromLeft (26), juce::Justification::centredLeft);
            g.setColour (red); g.drawText (lcdName, l.removeFromLeft (110), juce::Justification::centredLeft, true);
            g.setColour (orange); g.setFont (mono (12.0f, true)); g.drawText (lcdValue, l, juce::Justification::centredRight, true);
        }
        g.setColour (juce::Colour (0xff4a0f0b)); g.fillEllipse ((float) impl->lcdRect.getRight() + 12, (float) impl->topBar.getCentreY() - 6, 12, 12);
        // red hairline under the bar
        auto hz = juce::Rectangle<float> (10.0f, (float) impl->topBar.getBottom() + 3, (float) getWidth() - 20.0f, 3.0f);
        g.setGradientFill (juce::ColourGradient (juce::Colours::transparentBlack, hz.getX(), 0, red, hz.getCentreX(), 0, false));
        g.fillRect (hz.withWidth (hz.getWidth() * 0.5f));
        g.setGradientFill (juce::ColourGradient (red, hz.getCentreX(), 0, juce::Colours::transparentBlack, hz.getRight(), 0, false));
        g.fillRect (hz.withTrimmedLeft (hz.getWidth() * 0.5f));
        // bottom strip frame
        if (currentGroup != Modulation)
        {
            auto s = impl->stripRect.toFloat();
            g.setGradientFill (vertical (juce::Colour (0xff25282c), juce::Colour (0xff1a1c1f), s));
            g.fillRoundedRectangle (s, 2.0f); g.setColour (line); g.drawRoundedRectangle (s, 2.0f, 1.0f);
            auto h = s.removeFromTop (26).reduced (8, 4);
            auto tab = h.removeFromLeft (46);
            g.setColour (red); g.fillRoundedRectangle (tab, 1.5f);
            g.setColour (juce::Colour (0xff111111)); g.setFont (font (9.0f, true)); g.drawText ("MOD", tab.toNearestInt(), juce::Justification::centred);
            g.setColour (dim); g.setFont (font (8.5f));
            g.drawText ("drag an LFO / ENV handle onto a knob  -  click a knob's dot to set the amount", h.withTrimmedRight (30).toNearestInt(), juce::Justification::centredRight, true);
        }
    }

    void EditorContent::paintOverChildren (juce::Graphics&) {}
}
