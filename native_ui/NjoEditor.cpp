#include "NjoEditor.h"
#include "NjoLfo.h"
#include "NjoFreq.h"

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
                    if (style == Tab && on)
                    {
                        auto cp = chamfer (r, 4.0f, 0.0f, 4.0f, 0.0f);
                        g.setGradientFill (vertical (juce::Colour (0xff2e3a1c), juce::Colour (0xff171a0e), r)); g.fillPath (cp);
                        g.setColour (red); g.strokePath (cp, juce::PathStrokeType (1.0f));
                        g.fillRect (r.getX() + 4.0f, r.getBottom() - 2.5f, r.getWidth() - 8.0f, 2.0f);
                    }
                    else paintButton (g, r, on, over, false);
                    g.setColour (on ? (style == Tab ? red : juce::Colour (0xff14110e)) : (over ? ink : dim)); g.setFont (font (9.0f, true));
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
        std::unique_ptr<NavButton> stripToggle, sizeButton, stripModBtn, stripFrqBtn, stripSeqBtn, modEnvBtn, modFrqBtn, modSeqBtn;
        juce::Rectangle<int> topBar, lcdRect, stripRect, mainRect, stageRect, subRect, mgrRect;
        juce::Component* shownPage = nullptr;
    };

    EditorContent::EditorContent (Backend& be, SoundMemory* sharedMemory)
        : ctx (be), ownMemory (sharedMemory ? nullptr : std::make_unique<SoundMemory> (ctx)), memory (sharedMemory ? *sharedMemory : *ownMemory), fm (ctx), fmRm (ctx, 1), glob (ctx), fx (ctx, memory), editors (ctx), editorsFull (ctx), freq (ctx), freqFull (ctx), seq (ctx), seqFull (ctx), matrix (ctx), seqArp (ctx), manager (ctx, memory, *this), impl (new Impl)
    {
        if (sharedMemory) memory.onStatus = [this] (const juce::String& t) { ctx.status (t); };
        ctx.lfoShapes = std::make_shared<LfoShapes> (ctx);
        if (! ctx.freqShapes) ctx.freqShapes = std::make_shared<FreqShapes> (ctx);
        ctx.onLcd = [this] (const juce::String& n, const juce::String& v) { lcdName = n.toUpperCase(); lcdValue = v; repaint (impl->lcdRect); };
        ctx.onStatus = [this] (const juce::String& t) { status = t; statusUntil = juce::Time::getMillisecondCounterHiRes() + 2500; repaint (impl->lcdRect); };

        const char* rn[] = { "SYNTH", "EFFECTS", "MODULATION", "SEQ / ARP" };
        for (int i = 0; i < 4; ++i)
        {
            auto* b = impl->rail.add (new NavButton (NavButton::Rail, rn[i], juce::String (i + 1)));
            b->onClick = [this, i] { setGroup ((Group) i); };
            addAndMakeVisible (b);
        }
        for (int i = 0; i < 12; ++i)
        {
            juce::String t = i < 6 ? "OSC " + juce::String (i + 1) : (i == 6 ? "FM / PM / PD" : (i == 7 ? "RM / AM" : (i == 8 ? "GLOBAL" : (i == 9 ? "FILTER" : (i == 10 ? "DIST" : "RESO")))));
            auto* b = impl->tabs.add (new NavButton (NavButton::Tab, t));
            b->onClick = [this, i] { setSynthPage (i == 9 ? 9 + fltOsc : (i == 10 ? 15 + distOsc : (i == 11 ? 21 + resoOsc : i))); };
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
        for (int m = 1; m <= 3; ++m)
            for (int o = 0; o < OSC_N; ++o)
            {
                auto* p = (m == 1 ? fltPages : (m == 2 ? distPages : resoPages)).add (new OscPage (ctx, memory, o, m));
                p->onModDropped = [this] (ParamWidget& w) { showModPopup (ctx, w, w.num()); };
                p->onSelectOsc = [this, m] (int k) { setSynthPage ((m == 1 ? 9 : (m == 2 ? 15 : 21)) + k); };
                addChildComponent (p);
            }
        fm.setOnOpenOsc ([this] (int o) { setSynthPage (o); });
        fmRm.setOnOpenOsc ([this] (int o) { setSynthPage (o); });
        glob.onModDropped = [this] (ParamWidget& w) { showModPopup (ctx, w, w.num()); };
        fx.onModDropped = glob.onModDropped;
        addChildComponent (fm); addChildComponent (fmRm); addChildComponent (glob); addChildComponent (fx);
        addChildComponent (editorsFull); addChildComponent (freqFull); addChildComponent (seqFull); addChildComponent (matrix); addChildComponent (seqArp);
        addChildComponent (freq); addChildComponent (seq);
        addAndMakeVisible (editors);
        // tabs of the bottom strip (MOD / FREQ) and of the top panel of the modulation page (ENV / LFO | FREQ)
        auto mk = [this] (std::unique_ptr<NavButton>& b, const char* t, std::function<void()> f) { b = std::make_unique<NavButton> (NavButton::Mini, t); b->onClick = std::move (f); addChildComponent (*b); };
        mk (impl->stripModBtn, "MOD", [this] { stripTab = 0; stripOpen = true; layoutAll(); });
        mk (impl->stripFrqBtn, "FREQ", [this] { stripTab = 1; stripOpen = true; layoutAll(); });
        mk (impl->stripSeqBtn, "SEQ", [this] { stripTab = 2; stripOpen = true; layoutAll(); });
        mk (impl->modSeqBtn, "SEQ", [this] { modTab = 2; layoutAll(); });
        mk (impl->modEnvBtn, "ENV / LFO", [this] { modTab = 0; layoutAll(); });
        mk (impl->modFrqBtn, "FREQ", [this] { modTab = 1; layoutAll(); });
        addAndMakeVisible (manager);
        setSize (BASE_W, BASE_H);
        setGroup (NJOHRR_FX_ONLY ? Effects : Synth);
        startTimerHz (20);
    }

    EditorContent::~EditorContent() { if (! ownMemory) memory.onStatus = nullptr; }

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
        for (int i = 0; i < 4; ++i) impl->rail[i]->setOn (i == (int) g);
        layoutAll();
    }

    void EditorContent::setSynthPage (int p)
    {
        currentSynthPage = juce::jlimit (0, 26, p);
        if (currentSynthPage >= 9 && currentSynthPage < 15) fltOsc = currentSynthPage - 9;
        else if (currentSynthPage >= 15 && currentSynthPage < 21) distOsc = currentSynthPage - 15;
        else if (currentSynthPage >= 21) resoOsc = currentSynthPage - 21;
        currentGroup = Synth;
        for (int i = 0; i < 4; ++i) impl->rail[i]->setOn (i == 0);
        layoutAll();
    }

    void EditorContent::resized() { layoutAll(); }

    void EditorContent::layoutAll()
    {
        if (NJOHRR_FX_ONLY) currentGroup = Effects;
        auto r = getLocalBounds().reduced (10, 8);
        impl->topBar = r.removeFromTop (44);
        r.removeFromTop (3 + 6);
        if (! NJOHRR_FX_ONLY) { r.removeFromLeft (66); r.removeFromLeft (8); }
        // equal thirds with 6px gaps
        {
            auto rr = juce::Rectangle<int> (10, impl->topBar.getBottom() + 9, 66, r.getHeight());
            int h = (rr.getHeight() - 18) / 4;
            for (int i = 0; i < 4; ++i) { impl->rail[i]->setBounds (rr.getX(), rr.getY() + i * (h + 6), rr.getWidth(), h); impl->rail[i]->setVisible (! NJOHRR_FX_ONLY); }
        }
        impl->mainRect = r;

        bool synth = currentGroup == Synth, mod = currentGroup == Modulation, seqa = currentGroup == Sequencer;
        auto m = r;
        impl->subRect = synth ? m.removeFromTop (24) : juce::Rectangle<int>();
        if (synth) m.removeFromTop (6);
        for (int i = 0; i < impl->tabs.size(); ++i) impl->tabs[i]->setVisible (synth);
        if (synth)
        {
            auto s = impl->subRect; int x = s.getX();
            for (int i = 0; i < 6; ++i) { impl->tabs[i]->setBounds (x, s.getY(), 56, s.getHeight()); x += 59; }
            int rx = s.getRight();
            const int widths[] = { 62, 58, 70, 48, 54, 46 };   // GLOBAL, RM / AM, FM / PM / PD, RESO, DIST, FILTER
            const int order[] = { 8, 7, 6, 11, 10, 9 };
            for (int k = 0; k < 6; ++k) { rx -= widths[k]; impl->tabs[order[k]]->setBounds (rx, s.getY(), widths[k], s.getHeight()); rx -= 3; }
            for (int i = 0; i < 9; ++i) impl->tabs[i]->setOn (i == currentSynthPage);
            impl->tabs[9]->setOn (currentSynthPage >= 9 && currentSynthPage < 15);
            impl->tabs[10]->setOn (currentSynthPage >= 15 && currentSynthPage < 21);
            impl->tabs[11]->setOn (currentSynthPage >= 21);
        }
        impl->mgrRect = m.removeFromTop (24); m.removeFromTop (6);
        manager.setBounds (impl->mgrRect);

        int stripH = (mod || seqa || NJOHRR_FX_ONLY) ? 0 : (stripOpen ? 190 : 26);
        if (! mod && ! seqa) { impl->stripRect = m.removeFromBottom (stripH); m.removeFromBottom (6); }
        impl->stageRect = m;

        for (auto* p : osc) p->setVisible (false);
        for (auto* p : fltPages) p->setVisible (false);
        for (auto* p : distPages) p->setVisible (false);
        for (auto* p : resoPages) p->setVisible (false);
        fm.setVisible (false); fmRm.setVisible (false); glob.setVisible (false); fx.setVisible (false); editorsFull.setVisible (false); matrix.setVisible (false); seqArp.setVisible (false);
        editors.setVisible (false); freq.setVisible (false); freqFull.setVisible (false); seq.setVisible (false); seqFull.setVisible (false);
        for (auto* b : { impl->stripModBtn.get(), impl->stripFrqBtn.get(), impl->stripSeqBtn.get(), impl->modEnvBtn.get(), impl->modFrqBtn.get(), impl->modSeqBtn.get() }) b->setVisible (false);
        if (synth)
        {
            if (currentSynthPage < 6) { osc[currentSynthPage]->setBounds (impl->stageRect); osc[currentSynthPage]->setVisible (true); }
            else if (currentSynthPage == 6) { fm.setBounds (impl->stageRect); fm.setVisible (true); }
            else if (currentSynthPage == 7) { fmRm.setBounds (impl->stageRect); fmRm.setVisible (true); }
            else if (currentSynthPage >= 9 && currentSynthPage < 15) { fltPages[currentSynthPage - 9]->setBounds (impl->stageRect); fltPages[currentSynthPage - 9]->setVisible (true); }
            else if (currentSynthPage >= 15 && currentSynthPage < 21) { distPages[currentSynthPage - 15]->setBounds (impl->stageRect); distPages[currentSynthPage - 15]->setVisible (true); }
            else if (currentSynthPage >= 21) { resoPages[currentSynthPage - 21]->setBounds (impl->stageRect); resoPages[currentSynthPage - 21]->setVisible (true); }
            else { glob.setBounds (impl->stageRect); glob.setVisible (true); }
        }
        else if (currentGroup == Effects) { fx.setBounds (impl->stageRect); fx.setVisible (true); }
        else if (seqa) { seqArp.setBounds (impl->stageRect); seqArp.setVisible (true); }
        else
        {
            // modulation page: editors on top, the matrix below (paged)
            auto area = impl->stageRect;
            impl->stripRect = area.withHeight (0);
            auto top = area.removeFromTop (juce::roundToInt (area.getHeight() * 0.48f));
            area.removeFromTop (6);
            editorsFull.setBounds (top); freqFull.setBounds (top); seqFull.setBounds (top);
            editorsFull.setVisible (modTab == 0); freqFull.setVisible (modTab == 1); seqFull.setVisible (modTab == 2);
            impl->modEnvBtn->setBounds (top.getRight() - 182, top.getY() + 5, 70, 18); impl->modFrqBtn->setBounds (top.getRight() - 108, top.getY() + 5, 46, 18); impl->modSeqBtn->setBounds (top.getRight() - 58, top.getY() + 5, 46, 18);
            impl->modEnvBtn->text = "ENV / LFO"; impl->modEnvBtn->setOn (modTab == 0); impl->modFrqBtn->setOn (modTab == 1); impl->modSeqBtn->setOn (modTab == 2);
            impl->modEnvBtn->setVisible (true); impl->modFrqBtn->setVisible (true); impl->modSeqBtn->setVisible (true);
            matrix.setBounds (area); matrix.setVisible (true);
        }
        if (! mod && ! seqa)
        {
            auto s = impl->stripRect;
            impl->stripToggle->setBounds (s.getRight() - 26, s.getY() + 3, 22, 18);
            impl->stripToggle->text = stripOpen ? juce::String (juce::CharPointer_UTF8 ("\xe2\x96\xbe")) : juce::String (juce::CharPointer_UTF8 ("\xe2\x96\xb4"));
            impl->stripToggle->setVisible (true);
            editors.setBounds (s.withTrimmedTop (26)); freq.setBounds (s.withTrimmedTop (26)); seq.setBounds (s.withTrimmedTop (26));
            editors.setVisible (stripOpen && stripTab == 0); freq.setVisible (stripOpen && stripTab == 1); seq.setVisible (stripOpen && stripTab == 2);
            impl->stripModBtn->setBounds (s.getX() + 8, s.getY() + 4, 46, 18); impl->stripFrqBtn->setBounds (s.getX() + 8 + 49, s.getY() + 4, 46, 18); impl->stripSeqBtn->setBounds (s.getX() + 8 + 98, s.getY() + 4, 46, 18);
            impl->stripModBtn->setOn (stripTab == 0); impl->stripFrqBtn->setOn (stripTab == 1); impl->stripSeqBtn->setOn (stripTab == 2);
            impl->stripModBtn->setVisible (true); impl->stripFrqBtn->setVisible (true); impl->stripSeqBtn->setVisible (true);
        }
        else impl->stripToggle->setVisible (false);
        if (NJOHRR_FX_ONLY)   // no modulation strip in the effects plugin
        {
            impl->stripToggle->setVisible (false); editors.setVisible (false); freq.setVisible (false); seq.setVisible (false);
            impl->stripModBtn->setVisible (false); impl->stripFrqBtn->setVisible (false); impl->stripSeqBtn->setVisible (false);
        }
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
        g.setGradientFill (vertical (juce::Colour (0xff363027), juce::Colour (0xff211d17), t));
        auto tp = chamfer (t, 26.0f, 8.0f, 26.0f, 8.0f);
        g.fillPath (tp);
        g.setColour (juce::Colour (0xff0c0b08)); g.strokePath (chamfer (t.reduced (3), 23.0f, 6.0f, 23.0f, 6.0f), juce::PathStrokeType (1.0f));
        g.setColour (juce::Colour (0xff7a6740)); g.strokePath (tp, juce::PathStrokeType (2.0f));
        g.setColour (red.withAlpha (0.5f)); g.drawLine (t.getX() + 3.0f, t.getY() + 26.0f, t.getX() + 26.0f, t.getY() + 3.0f, 1.2f);    // etched cut
        g.drawLine (t.getRight() - 26.0f - 3.0f, t.getBottom() - 3.0f, t.getRight() - 3.0f, t.getBottom() - 26.0f - 3.0f, 1.2f);
        g.setColour (red); g.setFont (impact (21.0f));
        g.drawText ("NJOHRR", juce::Rectangle<int> (impl->topBar.getX() + 16, impl->topBar.getY(), 130, impl->topBar.getHeight()), juce::Justification::centredLeft);
        auto model = juce::Rectangle<float> (t.getX() + 138, t.getY() + 13, 72, 18);
        g.setColour (red); g.fillRoundedRectangle (model, 1.5f);
        g.setColour (juce::Colour (0xff14110e)); g.setFont (font (10.0f, true)); g.drawText (NJOHRR_FX_ONLY ? "FX" : "SYNTH", model.toNearestInt(), juce::Justification::centred);
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
        g.setColour (juce::Colour (0xff2e4a0e)); g.fillEllipse ((float) impl->lcdRect.getRight() + 12, (float) impl->topBar.getCentreY() - 6, 12, 12);
        // red hairline under the bar
        auto hz = juce::Rectangle<float> (10.0f, (float) impl->topBar.getBottom() + 3, (float) getWidth() - 20.0f, 3.0f);
        g.setGradientFill (juce::ColourGradient (juce::Colours::transparentBlack, hz.getX(), 0, red, hz.getCentreX(), 0, false));
        g.fillRect (hz.withWidth (hz.getWidth() * 0.5f));
        g.setGradientFill (juce::ColourGradient (red, hz.getCentreX(), 0, juce::Colours::transparentBlack, hz.getRight(), 0, false));
        g.fillRect (hz.withTrimmedLeft (hz.getWidth() * 0.5f));
        // bottom strip frame
        if (currentGroup != Modulation && currentGroup != Sequencer && ! NJOHRR_FX_ONLY)
        {
            auto s = impl->stripRect.toFloat();
            g.setGradientFill (vertical (juce::Colour (0xff2d2820), juce::Colour (0xff201c17), s));
            paintCard (g, s);
            auto h = s.removeFromTop (26).reduced (8, 4);
            h.removeFromLeft (46 + 3 + 46 + 3 + 46);
            g.setColour (dim); g.setFont (font (8.5f));
            g.drawText (stripTab == 0 ? "drag an LFO / ENV handle onto a knob  -  click a knob's dot to set the amount"
                                      : stripTab == 1 ? "drag a FREQ handle onto a cutoff or Frequency knob  -  click the knob's dot to set the amount"
                                      : "drag a SEQ handle onto any knob  -  click the knob's dot to set the amount",
                        h.withTrimmedRight (30).toNearestInt(), juce::Justification::centredRight, true);
        }
    }

    void EditorContent::paintOverChildren (juce::Graphics&) {}
}
