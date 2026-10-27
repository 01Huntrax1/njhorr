// OSC 1-6 page: source panel (wavetable / sampler / Plaits), tune + unison, filter, distortion + output.
// Port of buildOscPages / updateOscUi / oscPageHTML of the web UI; the layout follows the 1180 x 760 screenshots.
#include "../NjoPages.h"
#include "../NjoPhys.h"
#include "OscDisplays.h"
#include <array>

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
            bool on = false;
            void setOn (bool b) { if (b != on) { on = b; repaint(); } }
            void paint (juce::Graphics& g) override
            {
                auto r = getLocalBounds().toFloat().reduced (0.5f);
                paintButton (g, r, on, hover, down, 3.0f);
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
        Impl (OscPage& p, Ctx& c, SoundMemory& m, int osc, int pageMode)
            : owner (p), ctx (c), mem (m), o (osc), mode (pageMode), display (c, m, osc), fdisplay (c, m, osc), ddisplay (c, m, osc), rdisplay (c, osc), tdisplay (c, m, osc, pageMode != 2), vault ("VAULT"),
              modeA (pageMode == 2 ? "DISTORTION" : "FILTER"), modeB (pageMode == 2 ? "WAVEDISTORTION" : "WAVEFILTER")
        {
            for (auto key : { "type", "wpos", "wsize", "w1m", "w1a", "w2m", "w2a", "root", "sstart", "sloop", "pleng", "pharm", "ptimb", "pmorph",
                              "oct", "semi", "fine", "track", "freq", "phase", "rphase", "uvox", "udet", "ublend", "uwid", "ustyle",
                              "fon", "ftype", "fcut", "fres", "fdrv", "fkey", "feg", "fvel", "fatk", "fdec", "fsus", "frel",
                              "dtype", "dpos", "ddrv", "dmix", "rson", "rsmod", "rsdec", "rsmat", "rshit", "rsinh", "rstune", "rsmix", "wfpos", "wdpos", "wfmix", "wfrange", "wfwarp", "wfcont", "wftilt", "wfspr", "wflaw", "level", "pan", "out" })
            {
                std::unique_ptr<ParamWidget> w;
                if (juce::String (key) == "type") w = std::make_unique<ButtonsWidget> (ctx, oscId (o, oscKey (key)), 5);   // all five sources in one row
                else if (findSpec (oscId (o, oscKey (key)))->kind == "stp") w = std::make_unique<OscStepper> (ctx, oscId (o, oscKey (key)));
                else w = makeWidget (ctx, oscId (o, oscKey (key)), juce::String (key) != "wdpos");
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            // Physical source: its parameters live in their own id block (PHY_BASE + 32 * osc + j)
            for (auto key : phyKeys)
            {
                const int num = phys::phyId (o, phys::key (key));
                auto w = makeWidget (ctx, num, true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            if (auto* t = dynamic_cast<ButtonsWidget*> (W ("type"))) t->setShowLabel (false);
            for (auto key : { "track", "rphase" }) if (auto* b = dynamic_cast<ButtonsWidget*> (W (key))) b->setShowLabel (false);

            owner.addAndMakeVisible (display);
            owner.addAndMakeVisible (fdisplay);
            owner.addAndMakeVisible (ddisplay);
            owner.addAndMakeVisible (rdisplay);
            owner.addAndMakeVisible (tdisplay);
            owner.addAndMakeVisible (modeA); owner.addAndMakeVisible (modeB);
            for (int i = 0; i < OSC_N; ++i)
            {
                chips[(size_t) i] = std::make_unique<PushButton> (juce::String::charToString ((juce::juce_wchar) ('A' + i)));
                chips[(size_t) i]->onClick = [this, i] { if (owner.onSelectOsc) owner.onSelectOsc (i); };
                owner.addAndMakeVisible (*chips[(size_t) i]);
            }
            // Filter / Wavefilter and Distortion / Wavedistortion: the table types are the last entries of the type lists
            modeA.onClick = [this] { setTableMode (false); };
            modeB.onClick = [this] { setTableMode (true); };
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
            vault.onClick = [this] { if (ctx.onOpenVault) ctx.onOpenVault ((int) kind(), o, &vault); };

            ctx.addListener (this);
            mem.addChangeListener (this);
            refreshDz();
            updateEngineLabels();
        }

        ~Impl() override { mem.removeChangeListener (this); ctx.removeListener (this); }

        ParamWidget* W (const char* key) { auto it = widgets.find (key); return it == widgets.end() ? nullptr : it->second.get(); }
        int pnum (const char* key) const { return oscId (o, oscKey (key)); }
        int srcType() const { return juce::jlimit (0, 4, juce::roundToInt (ctx.get (pnum ("type")))); }
        static constexpr const char* phyKeys[] = { "phmix", "phhard", "phntim", "phmodA", "phdecA", "phmatA", "phhitA", "phinhA", "phmodB", "phdecB", "phmatB", "phhitB", "phinhB", "phtunB", "phbal", "phser",
                                                         "jsaw", "jpulse", "jwidth", "jpwm", "jpwmr", "jsub", "jnoise", "jrange", "jdrift", "jcurve", "jptype", "jstype", "jbtype", "jpwms", "jvib" };
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
                else t->setState (DropZone::Empty, k == SoundMemory::FilterTable ? "DROP A TABLE / CLICK TO LOAD" : "DROP A SHAPER TABLE / CLICK TO LOAD");
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

        // the switch next to the type list: remembers the last normal type and returns to it
        void setTableMode (bool table)
        {
            const char* key = mode == 2 ? "dtype" : "ftype";
            const int tv = mode == 2 ? 7 : 30, n = pnum (key), cur = juce::roundToInt (ctx.get (n));
            if (table == (cur >= tv)) return;
            int target;
            if (table) { lastNormal = cur; target = tv; }
            else target = lastNormal < tv && lastNormal >= (mode == 2 ? 0 : 0) ? lastNormal : (mode == 2 ? 1 : 0);
            ctx.begin (n); ctx.set (n, (float) target); ctx.end (n);
        }

        // ---- parameter changes ----
        void paramChanged (int num, float) override
        {
            if (num >= phys::PHY_BASE + phys::PHY_STRIDE * o && num < phys::PHY_BASE + phys::PHY_STRIDE * (o + 1)) { owner.repaint(); return; }
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
            for (auto& kv : widgets) kv.second->setVisible (false);
            for (juce::Component* c : { (juce::Component*) &display, (juce::Component*) &fdisplay, (juce::Component*) &ddisplay, (juce::Component*) &rdisplay, (juce::Component*) &tdisplay,
                                        (juce::Component*) &dz, (juce::Component*) &dzF, (juce::Component*) &dzS, (juce::Component*) &vault,
                                        (juce::Component*) &modeA, (juce::Component*) &modeB })
                c->setVisible (false);
            for (auto& c : chips) c->setVisible (false);
            const int type = srcType();
            const bool wt = type == 0, sm = type == 1, pl = type == 2, ph = type == 3 || type == 4;
            const int cw = owner.getWidth(), ch = owner.getHeight();
            const double col = (cw - 88.0) / 12.0;
            auto span = [&] (int c0, int n) { return juce::Rectangle<int> (juce::roundToInt (c0 * (col + 8)), 0, juce::roundToInt (n * col + (n - 1) * 8), ch); };
            if (mode == 0) { cardSrc = span (0, 5); cardTune = span (5, 4); cardOut = span (9, 3); cardFlt = {}; }
            else { cardSrc = cardTune = {}; cardFlt = span (0, 8); cardOut = span (8, 4); }

            // ---- source ----
            if (mode == 0)
            {
                auto c = cardSrc; int w = c.getWidth();
                put ("type", 13, 24, w - 26, 19, c);
                display.setBounds (c.getX() + 13, c.getY() + 49, w - 26, 86);
                display.setVisible (true);
                dz.setBounds (c.getX() + 13, c.getY() + 136, w - 26 - 56, 26);
                vault.setBounds (c.getX() + w - 13 - 49, c.getY() + 136, 49, 26);
                dz.setVisible (wt || sm); vault.setVisible (wt || sm);

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

                // Alpha Juno: wave selectors with their levels, noise / character, pulse width
                if (type == 4)
                {
                    const int cw3 = (w - 26 - 16) / 3;
                    const char* ks[3] = { "jstype", "jptype", "jbtype" }; const char* kl[3] = { "jsaw", "jpulse", "jsub" };
                    for (int i = 0; i < 3; ++i)
                    {
                        const int x = 13 + i * (cw3 + 8);
                        put (ks[i], x, 156, cw3, 36, c);  strip (ks[i], x, 156, cw3, c, false);
                        knob (kl[i], x + cw3 / 2, 196, c);
                    }
                    const float fw6 = (float) (w - 26);
                    const char* kc[4] = { "jnoise", "jcurve", "jdrift", "jvib" };
                    for (int i = 0; i < 4; ++i) knob (kc[i], 13 + juce::roundToInt (fw6 * (2 * i + 1) / 8), 276, c);
                    const char* kp[3] = { "jwidth", "jpwm", "jpwmr" };
                    for (int i = 0; i < 3; ++i) knob (kp[i], 13 + juce::roundToInt (fw6 * (2 * i + 1) / 12), 352, c);
                    put ("jpwms", 13 + juce::roundToInt (fw6 * 0.52f), 354, juce::roundToInt (fw6 * 0.48f), 31, c);
                    put ("jrange", 13 + juce::roundToInt (fw6 * 0.52f), 396, juce::roundToInt (fw6 * 0.48f), 31, c);
                }
                // physical: resonators A and B side by side, exciter and balance below
                if (type == 3)
                {
                    const int cw2 = (w - 26 - 8) / 2, xa = 13, xb = 13 + cw2 + 8;
                    put ("phmodA", xa, 156, cw2, 36, c);  strip ("phmodA", xa, 156, cw2, c, false);
                    put ("phmodB", xb, 156, cw2, 36, c);  strip ("phmodB", xb, 156, cw2, c, false);
                    const char* ka[3] = { "phdecA", "phmatA", "phhitA" }; const char* kb[3] = { "phdecB", "phmatB", "phhitB" };
                    for (int i = 0; i < 3; ++i)
                    {
                        knob (ka[i], xa + cw2 * (2 * i + 1) / 6, 200, c);
                        knob (kb[i], xb + cw2 * (2 * i + 1) / 6, 200, c);
                    }
                    knob ("phinhA", xa + cw2 / 6, 258, c);
                    knob ("phinhB", xb + cw2 / 6, 258, c);
                    knob ("phtunB", xb + cw2 / 2, 258, c);
                    const float fw5 = (float) (w - 26);
                    const char* ke[4] = { "phmix", "phhard", "phntim", "phbal" };
                    for (int i = 0; i < 4; ++i) knob (ke[i], 13 + juce::roundToInt (fw5 * (2 * i + 1) / 8), 334, c);
                    put ("phser", 13, 396, w - 26, 31, c);
                }
            }
            // ---- tune ----
            if (mode == 0)
            {
                auto c = cardTune; int w = c.getWidth();
                const int lx = 12, rx = w - 12 - 72, cl = lx + 36, cr = rx + 36;
                put ("oct", lx, 52, 72, 17, c);   strip ("oct", lx, 41, 72, c, true);
                put ("semi", rx, 52, 72, 17, c);  strip ("semi", rx, 41, 72, c, true);
                int fineTop = (wt || ph) ? 86 : (sm ? 191 : 269);
                knob ("fine", cl, fineTop, c);
                put ("track", rx, fineTop + 24, 72, 18, c); strip ("track", rx, fineTop + 11, 72, c, true);
                int phaseTop = wt ? 152 : 309;
                knob ("phase", cl, phaseTop, c, ! (pl || ph));
                knob ("freq", cr, (wt || ph) ? 205 : (sm ? 250 : 330), c);   // fixed frequency (0 = Off), target of the Freq modulators
                put ("rphase", rx, phaseTop + 24, 72, 18, c, ! (pl || ph)); strip ("rphase", rx, phaseTop + 11, 72, c, true, ! (pl || ph));

                showUnison = wt;
                put ("uvox", lx, 283, 72, 17, c, wt);   strip ("uvox", lx, 272, 72, c, true, wt);
                knob ("udet", cr, 256, c, wt);
                knob ("ublend", cl, 319, c, wt);
                knob ("uwid", cr, 319, c, wt);
                put ("ustyle", lx, 387, w - 24, 31, c, wt);
            }
            // ---- output (oscillator page) ----
            if (mode == 0)
            {
                auto c = cardOut; int w = c.getWidth();
                const int cl = 12 + (w - 24) / 4, cr = 12 + (w - 24) * 3 / 4;
                knob ("level", cl, 60, c); knob ("pan", cr, 60, c);
                put ("out", 12, 170, w - 24, 31, c);
            }
            // ---- filter page: response, Filter / Wavefilter switch, controls; table card ----
            if (mode == 1)
            {
                auto c = cardFlt; int w = c.getWidth();
                fdisplay.setBounds (c.getX() + 12, c.getY() + 32, w - 24, 150); fdisplay.setVisible (true);
                const int modeW = 100;
                put ("fon", 12, 196, 162, 31, c);
                const int tx = 12 + 162 + 12, tw = w - 12 - 2 * modeW - 12 - tx;
                put ("ftype", tx, 195, tw, 36, c); strip ("ftype", tx, 195, tw, c, false);
                modeA.setBounds (c.getX() + w - 12 - 2 * modeW, c.getY() + 201, modeW, 26); modeB.setBounds (c.getX() + w - 12 - modeW, c.getY() + 201, modeW, 26);
                modeA.setVisible (true); modeB.setVisible (true);
                const double pitch = (w - 24) / 5.0;
                const char* keys[10] = { "fcut", "fres", "fdrv", "fkey", "feg", "fvel", "fatk", "fdec", "fsus", "frel" };
                for (int i = 0; i < 10; ++i)
                    knob (keys[i], 12 + juce::roundToInt (pitch * (i % 5) + pitch / 2), 262 + 84 * (i / 5), c);
            }
            // ---- distortion page ----
            if (mode == 2)
            {
                auto c = cardFlt; int w = c.getWidth();
                ddisplay.setBounds (c.getX() + 12, c.getY() + 32, w - 24, 150); ddisplay.setVisible (true);
                const int modeW = 118;
                put ("dtype", 12, 195, 220, 36, c); strip ("dtype", 12, 195, 220, c, false);
                put ("dpos", 244, 195, 190, 36, c); strip ("dpos", 244, 195, 190, c, false);
                modeA.setBounds (c.getX() + w - 12 - 2 * modeW, c.getY() + 201, modeW, 26); modeB.setBounds (c.getX() + w - 12 - modeW, c.getY() + 201, modeW, 26);
                modeA.setVisible (true); modeB.setVisible (true);
                knob ("ddrv", 12 + (w - 24) / 3, 275, c); knob ("dmix", 12 + (w - 24) * 2 / 3, 275, c);
            }
            // ---- resonator page: response, On / Model / Order, the six knobs; the right card explains the chain ----
            if (mode == 3)
            {
                auto c = cardFlt; int w = c.getWidth();
                rdisplay.setBounds (c.getX() + 12, c.getY() + 32, w - 24, 150); rdisplay.setVisible (true);
                put ("rson", 12, 196, 120, 31, c);
                const int mw = (w - 24 - 120 - 24) / 2;
                put ("rsmod", 144, 195, mw, 36, c); strip ("rsmod", 144, 195, mw, c, false);
                put ("dpos", 144 + mw + 12, 195, mw, 36, c); strip ("dpos", 144 + mw + 12, 195, mw, c, false);
                const double pitch = (w - 24) / 6.0;
                const char* keys[6] = { "rsdec", "rsmat", "rshit", "rsinh", "rstune", "rsmix" };
                for (int i = 0; i < 6; ++i) knob (keys[i], 12 + juce::roundToInt (pitch * i + pitch / 2), 262, c);
                const int cx0 = cardFlt.getX() + 190;
                for (int i = 0; i < OSC_N; ++i) { chips[(size_t) i]->setBounds (cx0 + i * 25, 6, 23, 18); chips[(size_t) i]->setOn (i == o); chips[(size_t) i]->setVisible (true); }
            }
            // ---- table card (filter / distortion page) ----
            if (mode == 1 || mode == 2)
            {
                auto c = cardOut; int w = c.getWidth();
                const bool wf = mode == 1;
                const bool active = juce::roundToInt (ctx.get (pnum (wf ? "ftype" : "dtype"))) >= (wf ? 30 : 7);
                tdisplay.setBounds (c.getX() + 12, c.getY() + 32, w - 24, wf ? 150 : 220); tdisplay.setVisible (true);
                auto& zone = wf ? dzF : dzS;
                const int zy = wf ? 192 : 262;
                zone.setBounds (c.getX() + 12, c.getY() + zy, w - 24, 26); zone.setVisible (true); zone.setAlpha (active ? 1.0f : 0.45f);
                if (wf)
                {
                    // Table Pos, Mix, Range / Warp, Contrast, Tilt / Spread and the Gain Law list
                    const int x0 = 12 + (w - 24) / 6, x1 = 12 + (w - 24) / 2, x2 = 12 + (w - 24) * 5 / 6;
                    const char* row[3][3] = { { "wfpos", "wfmix", "wfrange" }, { "wfwarp", "wfcont", "wftilt" }, { "wfspr", nullptr, nullptr } };
                    const int xs[3] = { x0, x1, x2 };
                    for (int r = 0; r < 3; ++r)
                        for (int i = 0; i < 3; ++i)
                            if (row[r][i]) knob (row[r][i], xs[i], 226 + 62 * r, c);
                    put ("wflaw", x1 - 70, 226 + 62 * 2 + 8, w - 12 - (x1 - 70), 36, c);
                    for (auto* key : { "wfpos", "wfmix", "wfrange", "wfwarp", "wfcont", "wftilt", "wfspr", "wflaw" })
                        if (auto* k = W (key)) k->setAlpha (active ? 1.0f : 0.45f);
                }
                else { put ("wdpos", 12, 304, w - 24, 30, c); if (auto* k = W ("wdpos")) k->setAlpha (active ? 1.0f : 0.45f); }
                // chips A-F: which oscillator this page shows
                const int cx0 = cardFlt.getX() + (mode == 2 ? 232 : 200);
                for (int i = 0; i < OSC_N; ++i) { chips[(size_t) i]->setBounds (cx0 + i * 25, 6, 23, 18); chips[(size_t) i]->setOn (i == o); chips[(size_t) i]->setVisible (true); }
            }
            modeA.setOn (! (mode == 1 ? juce::roundToInt (ctx.get (pnum ("ftype"))) >= 30 : juce::roundToInt (ctx.get (pnum ("dtype"))) >= 7));
            modeB.setOn (! modeA.on);
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
            for (auto c : { cardSrc, cardTune, cardFlt, cardOut }) if (! c.isEmpty()) paintCard (g, c.toFloat());
            if (mode == 0)
            {
                title (g, "OSC " + juce::String (o + 1) + " Source", cardSrc.getX() + 14, 15, cardSrc.getRight() - 12);
                title (g, "Tune", cardTune.getX() + 14, 15, cardTune.getRight() - 12);
                title (g, "Output", cardOut.getX() + 14, 15, cardOut.getRight() - 12);
                g.setColour (dim); g.setFont (font (8.5f, false));
                g.drawFittedText ("Filter and distortion of this oscillator have their own pages (FILTER, DIST).", cardOut.getX() + 14, 232, cardOut.getWidth() - 28, 40, juce::Justification::topLeft, 3);
            }
            else if (mode == 3)
            {
                title (g, "OSC " + juce::String (o + 1) + " Resonator", cardFlt.getX() + 14, 15, cardFlt.getX() + 186);
                title (g, "Pre-matrix chain", cardOut.getX() + 14, 15, cardOut.getRight() - 12);
                g.setColour (dim); g.setFont (font (8.5f, false));
                g.drawFittedText ("Every oscillator runs its signal through up to three stages before it reaches the FM / PM matrix and the output: the FILTER, the DISTORTION and this RESONATOR. "
                                  "The Order list picks the sequence (also on the DIST page). The resonator is the modal bank of the Physical source (16 modes, 9 models) used as an effect: "
                                  "it is tuned to the played key plus Tune, Decay sets the ring time, Material the damping of the upper modes, Position which modes are heard, "
                                  "Inharm detunes them. Mix blends the dry signal.",
                                  cardOut.getX() + 14, 40, cardOut.getWidth() - 28, 260, juce::Justification::topLeft, 20);
            }
            else
            {
                const bool wf = mode == 1;
                title (g, "OSC " + juce::String (o + 1) + (wf ? " Filter" : " Distortion"), cardFlt.getX() + 14, 15, cardFlt.getX() + (wf ? 196 : 228));
                title (g, wf ? "Wavefilter table" : "Wavedistortion table", cardOut.getX() + 14, 15, cardOut.getRight() - 12);
                g.setColour (dim); g.setFont (font (8.5f, false));
if (! wf)
                    g.drawFittedText ("Every frame is a transfer curve (input -1..1 to output). Drive scales the input, Mix blends with the dry signal, Table Pos morphs between the frames.",
                                      cardOut.getX() + 14, 376, cardOut.getWidth() - 28, 50, juce::Justification::topLeft, 4);
            }
            if (mode == 0 && srcType() == 4)
            {
                g.setColour (orange); g.setFont (font (8.0f, true).withExtraKerningFactor (0.2f));
                g.drawText ("WAVES", cardSrc.getX() + 13, 142, 150, 12, juce::Justification::centredLeft);
                g.drawText ("CHARACTER", cardSrc.getX() + 13, 262, 150, 12, juce::Justification::centredLeft);
                g.drawText ("PULSE WIDTH / PWM SOURCE / RANGE", cardSrc.getX() + 13, 338, 300, 12, juce::Justification::centredLeft);
            }
            if (mode == 0 && srcType() == 3)
            {
                g.setColour (orange); g.setFont (font (8.0f, true).withExtraKerningFactor (0.2f));
                g.drawText ("RESONATOR A", cardSrc.getX() + 13, 142, 150, 12, juce::Justification::centredLeft);
                g.drawText ("RESONATOR B", cardSrc.getX() + 13 + (cardSrc.getWidth() - 26 - 8) / 2 + 8, 142, 150, 12, juce::Justification::centredLeft);
                g.drawText ("EXCITER / MIX", cardSrc.getX() + 13, 322, 150, 12, juce::Justification::centredLeft);
            }
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
        int mode = 0;          // 0 = oscillator page, 1 = filter page, 2 = distortion page
        int lastNormal = -1;
        std::map<juce::String, std::unique_ptr<ParamWidget>> widgets;
        OscDisplay display; FilterDisplay fdisplay; DistDisplay ddisplay;
        ResoDisplay rdisplay; TableDisplay tdisplay;
        DropZone dz, dzF, dzS; PushButton vault;
        PushButton modeA, modeB; std::array<std::unique_ptr<PushButton>, OSC_N> chips;
        std::shared_ptr<juce::FileChooser> chooser;
    };

    // ============================================================================================ OscPage
    OscPage::OscPage (Ctx& c, SoundMemory& m, int o, int mode) : impl (new Impl (*this, c, m, o, mode)) {}
    OscPage::~OscPage() = default;

    void OscPage::paint (juce::Graphics& g) { impl->paintAll (g); }
    void OscPage::resized() { impl->layoutChildren(); }
}
