// OSC 1-6 page: source panel (wavetable / sampler / Plaits), tune + unison, filter, distortion + output.
// Port of buildOscPages / updateOscUi / oscPageHTML of the web UI; the layout follows the 1180 x 760 screenshots.
#include "../NjoPages.h"
#include "OscDisplays.h"

namespace njo
{
    using namespace theme;

    namespace
    {
        const char* const WT_DZ_EMPTY  = "DROP A WAVETABLE / CLICK TO LOAD";
        const char* const SMP_DZ_EMPTY = "DROP A SAMPLE / CLICK TO LOAD";

        float textWidth (const juce::Font& f, const juce::String& t)
        {
            juce::GlyphArrangement ga; ga.addLineOfText (f, t, 0, 0);
            return ga.getBoundingBox (0, -1, true).getWidth();
        }

        // minus / plus pair; the label and value are painted above it by the page (like the web UI)
        class OscStepper : public ParamWidget
        {
        public:
            OscStepper (Ctx& c, int n) : ParamWidget (c, n) {}
            void paint (juce::Graphics& g) override
            {
                auto b = getLocalBounds().toFloat().reduced (0, 0.5f);
                const float w = 22.0f;
                auto l = b.removeFromLeft (w), r = b.removeFromRight (w);
                paintButton (g, l, false, hoverSide < 0, false, 2.0f);
                paintButton (g, r, false, hoverSide > 0, false, 2.0f);
                g.setColour (ink); g.setFont (font (11.0f, true));
                g.drawText (juce::CharPointer_UTF8 ("\xe2\x88\x92"), l.toNearestInt(), juce::Justification::centred);
                g.drawText ("+", r.toNearestInt(), juce::Justification::centred);
            }
            void mouseMove (const juce::MouseEvent& e) override { int s = e.x < 24 ? -1 : (e.x > getWidth() - 24 ? 1 : 0); if (s != hoverSide) { hoverSide = s; repaint(); } }
            void mouseExit (const juce::MouseEvent& e) override { hoverSide = 0; ParamWidget::mouseExit (e); }
            void mouseDown (const juce::MouseEvent& e) override
            {
                int d = e.x < 24 ? -1 : (e.x > getWidth() - 24 ? 1 : 0);
                if (d) { ctx.begin (paramNum); setValueFromUser (val + (float) d); ctx.end (paramNum); }
            }
        private:
            int hoverSide = 0;
        };

        // small framed push button (VAULT)
        class PushButton : public juce::Component
        {
        public:
            explicit PushButton (const juce::String& t) : text (t) {}
            std::function<void()> onClick;
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintButton (g, r, false, hover, down, 3.0f);
                g.setColour (ink); g.setFont (font (9.0f, true).withExtraKerningFactor (0.06f));
                g.drawText (text, r.toNearestInt(), juce::Justification::centred);
            }
            void mouseEnter (const juce::MouseEvent&) override { hover = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { hover = false; repaint(); }
            void mouseDown (const juce::MouseEvent&) override { down = true; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override
            {
                down = false; repaint();
                if (getLocalBounds().contains (e.getPosition()) && onClick) onClick();
            }
        private:
            juce::String text; bool hover = false, down = false;
        };

        // the dashed drop zone: drop an audio file or click to pick one; the cross clears the memory
        class DropZone : public juce::Component, public juce::FileDragAndDropTarget
        {
        public:
            enum State { Empty, Busy, Loaded, Err };
            std::function<void (const juce::File&)> onFile;
            std::function<void()> onClick, onClear;

            void setState (State s, const juce::String& t) { state = s; text = t; repaint(); }
            State getState() const { return state; }

            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat();
                juce::Colour border = juce::Colour (0xff5a1a16), txt = dim, fill = juce::Colour (0xff0d0404);
                bool solid = false;
                if (state == Loaded) { border = red; txt = red; fill = juce::Colour (0xff1a0807); solid = true; }
                else if (state == Busy) { border = orange; txt = orange; solid = true; }
                else if (state == Err) { border = red; txt = juce::Colour (0xffff6666); solid = true; }
                if (over || hover) { border = red; txt = red; fill = juce::Colour (0xff1c0907); }
                g.setColour (fill); g.fillRoundedRectangle (r, 1.0f);
                juce::Path p; p.addRectangle (r.reduced (1.0f));
                g.setColour (border);
                if (solid) g.strokePath (p, juce::PathStrokeType (2.0f));
                else
                {
                    juce::Path d; const float dash[2] = { 5.0f, 4.0f };
                    juce::PathStrokeType (2.0f).createDashedStroke (d, p, dash, 2);
                    g.fillPath (d);
                }
                g.setColour (txt);
                g.setFont (font (9.0f, true).withExtraKerningFactor (0.08f));
                g.drawText (text, getLocalBounds().withTrimmedRight (22).withTrimmedLeft (6), juce::Justification::centred, true);
                g.setColour (clearHover ? orange : ink);
                g.setFont (font (15.0f, true));
                g.drawText (juce::CharPointer_UTF8 ("\xc3\x97"), clearRect(), juce::Justification::centred);
            }

            bool isInterestedInFileDrag (const juce::StringArray&) override { return true; }
            void fileDragEnter (const juce::StringArray&, int, int) override { over = true; repaint(); }
            void fileDragExit (const juce::StringArray&) override { over = false; repaint(); }
            void filesDropped (const juce::StringArray& f, int, int) override
            {
                over = false; repaint();
                if (f.size() > 0 && onFile) onFile (juce::File (f[0]));
            }
            void mouseEnter (const juce::MouseEvent&) override { hover = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { hover = false; clearHover = false; repaint(); }
            void mouseMove (const juce::MouseEvent& e) override
            {
                bool c = clearRect().contains (e.getPosition());
                if (c != clearHover) { clearHover = c; repaint(); }
            }
            void mouseUp (const juce::MouseEvent& e) override
            {
                if (! getLocalBounds().contains (e.getPosition())) return;
                if (clearRect().contains (e.getPosition())) { if (onClear) onClear(); }
                else if (onClick) onClick();
            }

        private:
            juce::Rectangle<int> clearRect() const { return getLocalBounds().removeFromRight (24); }
            State state = Empty; juce::String text;
            bool over = false, hover = false, clearHover = false;
        };
    }

    // ============================================================================================ Impl
    struct OscPage::Impl : private Ctx::Listener, private juce::ChangeListener
    {
        Impl (OscPage& p, Ctx& c, SoundMemory& m, int osc)
            : owner (p), ctx (c), mem (m), o (osc), display (c, m, osc), fdisplay (c, m, osc), vault ("VAULT")
        {
            for (auto key : { "type", "wpos", "wsize", "w1m", "w1a", "w2m", "w2a", "root", "sstart", "sloop", "pleng", "pharm", "ptimb", "pmorph",
                              "oct", "semi", "fine", "track", "freq", "phase", "rphase", "uvox", "udet", "ublend", "uwid", "ustyle",
                              "fon", "ftype", "fcut", "fres", "fdrv", "fkey", "feg", "fvel", "fatk", "fdec", "fsus", "frel",
                              "dtype", "dpos", "ddrv", "dmix", "wfpos", "wdpos", "level", "pan", "out" })
            {
                std::unique_ptr<ParamWidget> w;
                if (findSpec (oscId (o, oscKey (key)))->kind == "stp") w = std::make_unique<OscStepper> (ctx, oscId (o, oscKey (key)));
                else w = makeWidget (ctx, oscId (o, oscKey (key)), juce::String (key) != "wdpos");
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            if (auto* t = dynamic_cast<ButtonsWidget*> (W ("type"))) t->setShowLabel (false);
            for (auto key : { "track", "rphase" }) if (auto* b = dynamic_cast<ButtonsWidget*> (W (key))) b->setShowLabel (false);

            owner.addAndMakeVisible (display);
            owner.addAndMakeVisible (fdisplay);
            owner.addAndMakeVisible (dz);
            owner.addAndMakeVisible (vault);
            owner.addAndMakeVisible (dzF);
            owner.addAndMakeVisible (dzS);
            for (auto* t : { &dzF, &dzS })
            {
                auto k = t == &dzF ? SoundMemory::FilterTable : SoundMemory::ShaperTable;
                t->onFile = [this, k] (const juce::File& f) { loadTable (k, f); };
                t->onClick = [this, k]
                {
                    chooser = std::make_shared<juce::FileChooser> ("Load a wavetable as table", juce::File(), SoundMemory::fileWildcard());
                    auto self = juce::Component::SafePointer<OscPage> (&owner);
                    chooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles,
                                          [self, k] (const juce::FileChooser& fc)
                                          { auto f = fc.getResult(); if (self != nullptr && f.existsAsFile()) self->impl->loadTable (k, f); });
                };
                t->onClear = [this, k] { mem.clear (k, o); refreshDz(); };
            }

            dz.onFile = [this] (const juce::File& f) { loadFile (f); };
            dz.onClick = [this] { chooseFile(); };
            dz.onClear = [this] { clearMemory(); };
            vault.onClick = [this] { if (ctx.onOpenVault) ctx.onOpenVault ((int) kind(), o); };

            ctx.addListener (this);
            mem.addChangeListener (this);
            refreshDz();
            updateEngineLabels();
        }

        ~Impl() override { mem.removeChangeListener (this); ctx.removeListener (this); }

        ParamWidget* W (const char* key) { auto it = widgets.find (key); return it == widgets.end() ? nullptr : it->second.get(); }
        int pnum (const char* key) const { return oscId (o, oscKey (key)); }
        int srcType() const { return juce::jlimit (0, 2, juce::roundToInt (ctx.get (pnum ("type")))); }
        SoundMemory::Kind kind() const { return srcType() == 1 ? SoundMemory::Sample : SoundMemory::Wavetable; }

        // ---- memory / drop zone ----
        void refreshDz()
        {
            refreshTblDz();
            if (dz.getState() == DropZone::Busy) return;
            auto k = kind();
            auto* s = mem.get (k, o);
            if (s != nullptr) dz.setState (DropZone::Loaded, s->name);
            else dz.setState (DropZone::Empty, k == SoundMemory::Wavetable ? WT_DZ_EMPTY : SMP_DZ_EMPTY);
        }

        // Wavefilter / Wavedistortion tables (a wavetable file whose frames are filter curves / transfer curves)
        void loadTable (SoundMemory::Kind k, const juce::File& f)
        {
            mem.load (k, o, f, {});
            refreshDz();
        }
        void refreshTblDz()
        {
            for (auto* t : { &dzF, &dzS })
            {
                auto k = t == &dzF ? SoundMemory::FilterTable : SoundMemory::ShaperTable;
                if (auto* s = mem.get (k, o)) t->setState (DropZone::Loaded, s->name);
                else t->setState (DropZone::Empty, k == SoundMemory::FilterTable ? "+ TABLE" : "DROP SHAPER TABLE");
            }
        }

        void loadFile (const juce::File& f)
        {
            auto k = kind();
            dz.setState (DropZone::Busy, "DECODING...");
            juce::Component::SafePointer<OscPage> safe (&owner);
            mem.load (k, o, f, [safe, k] (bool ok, const juce::String& msg)
            {
                juce::MessageManager::callAsync ([safe, k, ok, msg]
                {
                    if (safe == nullptr) return;
                    safe->impl->loaded (k, ok, msg);
                });
            });
        }

        void loaded (SoundMemory::Kind k, bool ok, const juce::String&)
        {
            dz.setState (DropZone::Empty, "");
            if (! ok) { dz.setState (DropZone::Err, "UNSUPPORTED FILE"); return; }
            if (auto* s = mem.get (k, o))
            {
                if (k == SoundMemory::Wavetable) ctx.set (pnum ("wsize"), (float) oscmodel::pickFrameIndex ((int) s->data.size()));
                if (ctx.get (pnum ("level")) < 0.05f) ctx.set (pnum ("level"), 0.8f);
                ctx.status ("LOADED " + s->name);
            }
            refreshDz();
        }

        void chooseFile()
        {
            chooser = std::make_shared<juce::FileChooser> ("Load audio", juce::File(), SoundMemory::fileWildcard());
            auto self = juce::Component::SafePointer<OscPage> (&owner);
            chooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles,
                                  [self] (const juce::FileChooser& fc)
                                  {
                                      auto f = fc.getResult();
                                      if (self != nullptr && f.existsAsFile()) self->impl->loadFile (f);
                                  });
        }

        void clearMemory()
        {
            mem.clear (kind(), o);
            ctx.status ("OSC " + juce::String (o + 1) + " CLEARED");
            dz.setState (DropZone::Empty, "");
            refreshDz();
        }

        void changeListenerCallback (juce::ChangeBroadcaster*) override { refreshDz(); }

        // ---- parameter changes ----
        void paramChanged (int num, float) override
        {
            int k = num - oscId (o, 0);
            if (k < 0 || k >= OSC_STRIDE) return;
            if (k == oscKey ("type")) { if (dz.getState() != DropZone::Busy) dz.setState (DropZone::Empty, ""); refreshDz(); updateEngineLabels(); layoutChildren(); }
            else if (k == oscKey ("pleng")) updateEngineLabels();
            else if (k == oscKey ("ftype") || k == oscKey ("dtype")) layoutChildren();
            owner.repaint();
        }

        void updateEngineLabels()
        {
            int eng = juce::jlimit (0, plaitsEngines().size() - 1, juce::roundToInt (ctx.get (pnum ("pleng"))));
            auto& pp = plaitsParams();
            const char* keys[3] = { "pharm", "ptimb", "pmorph" };
            for (int i = 0; i < 3; ++i)
                if (auto* w = W (keys[i]); w != nullptr && eng < (int) pp.size() && i < pp[(size_t) eng].size()) w->setLabelOverride (pp[(size_t) eng][i]);
            // the dropdown lists the engines in groups
            if (auto* sel = dynamic_cast<SelectWidget*> (W ("pleng"))) sel->setOptions (plaitsEngines(), plaitsGroups());
        }

        // ---- layout ----
        struct Strip { ParamWidget* w; juce::Rectangle<int> r; bool withLabel; };
        std::vector<Strip> strips;
        juce::Rectangle<int> cardSrc, cardTune, cardFlt, cardOut;
        bool showUnison = false;
        int outTitleY = 231;

        void put (const char* key, int x, int y, int w, int h, juce::Rectangle<int> card, bool visible = true)
        {
            if (auto* c = W (key)) { c->setBounds (x + card.getX(), y + card.getY(), w, h); c->setVisible (visible); }
        }
        void knob (const char* key, int cx, int top, juce::Rectangle<int> card, bool visible = true) { put (key, cx - 35, top, 70, 54, card, visible); }
        void strip (const char* key, int x, int y, int w, juce::Rectangle<int> card, bool withLabel, bool visible = true)
        {
            if (! visible) return;
            if (auto* c = W (key)) strips.push_back ({ c, { x + card.getX(), y + card.getY(), w, 11 }, withLabel });
        }

        void layoutChildren()
        {
            strips.clear();
            const int type = srcType();
            const bool wt = type == 0, sm = type == 1, pl = type == 2;
            const int cw = owner.getWidth(), ch = owner.getHeight();
            const double col = (cw - 88.0) / 12.0;
            auto span = [&] (int c0, int n) { return juce::Rectangle<int> (juce::roundToInt (c0 * (col + 8)), 0, juce::roundToInt (n * col + (n - 1) * 8), ch); };
            cardSrc = span (0, 4); cardTune = span (4, 2); cardFlt = span (6, 4); cardOut = span (10, 2);

            // ---- source ----
            {
                auto c = cardSrc; int w = c.getWidth();
                put ("type", 13, 24, w - 26, 19, c);
                display.setBounds (c.getX() + 13, c.getY() + 49, w - 26, 86);
                dz.setBounds (c.getX() + 13, c.getY() + 136, w - 26 - 56, 26);
                vault.setBounds (c.getX() + w - 13 - 49, c.getY() + 136, 49, 26);
                dz.setVisible (! pl); vault.setVisible (! pl);

                const int colW = (w - 26 - 7) / 2, x2 = 13 + colW + 7;
                put ("wpos", 13 + colW / 2 - 35, 190, 70, 54, c, wt);
                put ("wsize", x2, 202, colW, 36, c, wt);   strip ("wsize", x2, 202, colW, c, false, wt);
                put ("w1m", 13, 279, colW, 36, c, wt);     strip ("w1m", 13, 279, colW, c, false, wt);
                knob ("w1a", x2 + colW / 2, 269, c, wt);
                put ("w2m", 13, 358, colW, 36, c, wt);     strip ("w2m", 13, 358, colW, c, false, wt);
                knob ("w2a", x2 + colW / 2, 348, c, wt);

                put ("root", 13, 248, 106, 17, c, sm);     strip ("root", 13, 236, 106, c, true, sm);
                knob ("sstart", 179, 222, c, sm);
                put ("sloop", 13, 337, w - 26, 32, c, sm);

                put ("pleng", 13, 203, w - 26, 36, c, pl); strip ("pleng", 13, 203, w - 26, c, false, pl);
                const float fw = (float) (w - 26);
                knob ("pharm", 13 + juce::roundToInt (fw / 6), 302, c, pl);
                knob ("ptimb", 13 + juce::roundToInt (fw / 2), 302, c, pl);
                knob ("pmorph", 13 + juce::roundToInt (fw * 5 / 6), 302, c, pl);
            }
            // ---- tune ----
            {
                auto c = cardTune; int w = c.getWidth();
                const int lx = 12, rx = w - 12 - 72, cl = lx + 36, cr = rx + 36;
                put ("oct", lx, 52, 72, 17, c);   strip ("oct", lx, 41, 72, c, true);
                put ("semi", rx, 52, 72, 17, c);  strip ("semi", rx, 41, 72, c, true);
                int fineTop = wt ? 86 : (sm ? 191 : 269);
                knob ("fine", cl, fineTop, c);
                put ("track", rx, fineTop + 24, 72, 18, c); strip ("track", rx, fineTop + 11, 72, c, true);
                int phaseTop = wt ? 152 : 309;
                knob ("phase", cl, phaseTop, c, ! pl);
                knob ("freq", cr, wt ? 198 : (sm ? 250 : 330), c);   // fixed frequency (0 = Off), target of the Freq modulators
                put ("rphase", rx, phaseTop + 24, 72, 18, c, ! pl); strip ("rphase", rx, phaseTop + 11, 72, c, true, ! pl);

                showUnison = wt;
                put ("uvox", lx, 283, 72, 17, c, wt);   strip ("uvox", lx, 272, 72, c, true, wt);
                knob ("udet", cr, 256, c, wt);
                knob ("ublend", cl, 319, c, wt);
                knob ("uwid", cr, 319, c, wt);
                put ("ustyle", lx, 387, w - 24, 31, c, wt);
            }
            // ---- filter ----
            {
                auto c = cardFlt; int w = c.getWidth();
                fdisplay.setBounds (c.getX() + 12, c.getY() + 29, w - 24, 71);
                put ("fon", 12, 132, 162, 31, c);
                put ("ftype", w - 12 - 162, 131, 162, 36, c); strip ("ftype", w - 12 - 162, 131, 162, c, false);
                const double pitch = (w - 24) / 4.0;
                const char* keys[10] = { "fcut", "fres", "fdrv", "fkey", "feg", "fvel", "fatk", "fdec", "fsus", "frel" };
                for (int i = 0; i < 10; ++i)
                    knob (keys[i], 12 + juce::roundToInt (pitch * (i % 4) + pitch / 2), 192 + 79 * (i / 4), c);
                // Wavefilter: table position knob and table drop zone take the two free places of the last row
                const bool wf = juce::roundToInt (ctx.get (pnum ("ftype"))) >= 30;
                knob ("wfpos", 12 + juce::roundToInt (pitch * 2 + pitch / 2), 192 + 79 * 2, c, wf);
                dzF.setBounds (c.getX() + 12 + juce::roundToInt (pitch * 3) + 2, c.getY() + 192 + 79 * 2 + 14, juce::roundToInt (pitch) - 4, 26);
                dzF.setVisible (wf);
            }
            // ---- distortion / output ----
            {
                auto c = cardOut; int w = c.getWidth();
                put ("dtype", 12, 54, w - 24, 34, c); strip ("dtype", 12, 54, w - 24, c, false);
                put ("dpos", 12, 94, w - 24, 26, c);
                // Wavedistortion: table drop zone and position slider (the rest moves down)
                const bool wd = juce::roundToInt (ctx.get (pnum ("dtype"))) >= 7;
                const int dy = wd ? 30 : 0;
                dzS.setBounds (c.getX() + 12, c.getY() + 124, w - 24, 22);
                dzS.setVisible (wd);
                put ("wdpos", 12, 150, w - 24, 30, c, wd);
                const int cl = 12 + (w - 24) / 4, cr = 12 + (w - 24) * 3 / 4;
                knob ("ddrv", cl, 160 + dy, c); knob ("dmix", cr, 160 + dy, c);
                outTitleY = 231 + dy;
                knob ("level", cl, 270 + dy, c); knob ("pan", cr, 270 + dy, c);
                put ("out", 12, 362 + dy, w - 24, 31, c);
            }
        }

        // ---- painting ----
        static void title (juce::Graphics& g, const juce::String& text, int x, int y, int right)
        {
            juce::Path d; d.addRectangle (-3.0f, -3.0f, 6.0f, 6.0f);
            g.setColour (red); g.fillPath (d, juce::AffineTransform::rotation (juce::MathConstants<float>::pi / 4).translated ((float) x + 3, (float) y));
            auto f = font (10.5f, true).withExtraKerningFactor (0.17f);
            g.setColour (ink); g.setFont (f);
            g.drawText (text.toUpperCase(), x + 12, y - 8, right - x, 16, juce::Justification::centredLeft, false);
            int lx = x + 12 + (int) textWidth (f, text.toUpperCase()) + 12;
            if (lx < right - 30)
            {
                g.setGradientFill (juce::ColourGradient (red.withAlpha (0.8f), (float) lx, 0, red.withAlpha (0.0f), (float) right, 0, false));
                g.fillRect ((float) lx, (float) y, (float) (right - lx), 1.0f);
            }
        }

        void paintAll (juce::Graphics& g)
        {
            for (auto c : { cardSrc, cardTune, cardFlt, cardOut }) paintCard (g, c.toFloat());
            title (g, "OSC " + juce::String (o + 1) + " Source", cardSrc.getX() + 14, 15, cardSrc.getRight() - 12);
            title (g, "Tune", cardTune.getX() + 14, 15, cardTune.getRight() - 12);
            title (g, "Filter", cardFlt.getX() + 14, 15, cardFlt.getRight() - 12);
            title (g, "Distortion / Out", cardOut.getX() + 14, 15, cardOut.getRight() - 12);
            title (g, "Output", cardOut.getX() + 14, outTitleY, cardOut.getRight() - 12);
            if (showUnison)
            {
                g.setColour (orange); g.setFont (font (8.0f, true).withExtraKerningFactor (0.2f));
                g.drawText ("UNISON", cardTune.getX() + 12, 233, 100, 12, juce::Justification::centredLeft);
            }
            for (auto& s : strips)
            {
                if (! s.w->isVisible()) continue;
                auto value = s.w->valueString();
                auto vf = mono (8.5f, true);
                g.setFont (vf); g.setColour (orange);
                g.drawText (value, s.r, juce::Justification::centredRight, false);
                if (s.withLabel)
                {
                    auto lf = font (8.5f, true);
                    g.setFont (lf); g.setColour (dim);
                    int lw = juce::jmax (0, s.r.getWidth() - (int) textWidth (vf, value) - 5);
                    g.drawText (s.w->labelText().toUpperCase(), s.r.withWidth (lw), juce::Justification::centredLeft, true);
                }
            }
        }

        OscPage& owner; Ctx& ctx; SoundMemory& mem; int o;
        std::map<juce::String, std::unique_ptr<ParamWidget>> widgets;
        OscDisplay display; FilterDisplay fdisplay;
        DropZone dz, dzF, dzS; PushButton vault;
        std::shared_ptr<juce::FileChooser> chooser;
    };

    // ============================================================================================ OscPage
    OscPage::OscPage (Ctx& c, SoundMemory& m, int o) : impl (new Impl (*this, c, m, o)) {}
    OscPage::~OscPage() = default;

    void OscPage::paint (juce::Graphics& g) { impl->paintAll (g); }
    void OscPage::resized() { impl->layoutChildren(); }
}
