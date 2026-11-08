// OSC 1-6 page: source panel (wavetable / sampler / Wave Terrain), tune + unison, filter, distortion + output.
// Port of buildOscPages / updateOscUi / oscPageHTML of the web UI; the layout follows the 1180 x 760 screenshots.
#include "../NjoPages.h"
#include "../NjoPhys.h"
#include "../NjoKick.h"
#include "../NjoTer.h"
#include "../NjoWg.h"
#include "../NjoJp.h"
#include "../NjoGr.h"
#include "../NjoAd.h"
#include "../NjoDk.h"
#include "../NjoSp.h"
#include "../NjoSf.h"
#include "OscDisplays.h"
#include "Editors.h"
#include <array>

namespace njo
{
    using namespace theme;

    namespace
    {
        const char* const WT_DZ_EMPTY  = "DROP A WAVETABLE / CLICK TO LOAD";
        const char* const SMP_DZ_EMPTY = "DROP A SAMPLE / CLICK TO LOAD";
        const char* const SF_DZ_EMPTY  = "DROP A SOUNDFONT (.SF2) / CLICK TO LOAD";

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
            void setText (const juce::String& t) { if (t != text) { text = t; repaint(); } }
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
                else if (state == Err) { border = red; txt = juce::Colour (0xffff7167); solid = true; }
                if (over || hover) { border = red; txt = red; fill = juce::Colour (0xff1c0807); }
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
              modeA (pageMode == 2 ? "DISTORTION" : "FILTER"), modeB (pageMode == 2 ? "WAVEDISTORTION" : "WAVEFILTER"), editBtn ("EDIT")
        {
            editBtn.onClick = [this] { openEditor(); };
            owner.addAndMakeVisible (editBtn);
            if (pageMode == 1 || pageMode == 2) tedit = std::make_unique<TableEditor> (c, m, osc, pageMode == 1);
            if (pageMode == 0 || pageMode == 3) medit = std::make_unique<ModeEditor> (c, m, osc);
            for (juce::Component* e : { (juce::Component*) tedit.get(), (juce::Component*) medit.get() })
                if (e) owner.addChildComponent (e);
            if (tedit) tedit->onClose = [this] { layoutChildren(); };
            if (medit) medit->onClose = [this] { layoutChildren(); };
            for (auto key : { "type", "wpos", "wsize", "w1m", "w1a", "w2m", "w2a", "root", "sstart", "sloop", "tterr", "tscale", "twarp", "tfold",
                              "oct", "semi", "fine", "track", "freq", "phase", "rphase", "uvox", "udet", "ublend", "uwid", "udrift", "uphase", "ustyle",
                              "fon", "ftype", "fcut", "fres", "fdrv", "fkey", "feg", "fvel", "fatk", "fdec", "fsus", "frel",
                              "dtype", "dpos", "ddrv", "dmix", "rson", "rsmod", "rsdec", "rsmat", "rshit", "rsinh", "rstune", "rsmix", "wfpos", "wdpos", "wfmix", "wfrange", "wfwarp", "wfcont", "wftilt", "wfspr", "wflaw", "level", "pan" })
            {
                std::unique_ptr<ParamWidget> w;
                if (findSpec (oscId (o, oscKey (key)))->kind == "stp") w = std::make_unique<OscStepper> (ctx, oscId (o, oscKey (key)));
                else w = makeWidget (ctx, oscId (o, oscKey (key)), juce::String (key) != "wdpos");
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            // Wavetable Aliasing switch: ids 2000 + osc
            {
                auto w = makeWidget (ctx, 2000 + o, true);
                owner.addAndMakeVisible (*w);
                widgets["walias"] = std::move (w);
            }
            // Wave Terrain extras: their own id block (TER_BASE + 16 * osc + j)
            for (auto key : terKeys)
            {
                auto w = makeWidget (ctx, ter::terId (o, ter::key (key)), true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            // Waveguide source: its own id block (WG_BASE + 16 * osc + j)
            for (auto key : wgKeys)
            {
                auto w = makeWidget (ctx, wg::wgId (o, wg::key (juce::String (key) == "wgpos" ? "wpos" : key)), true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            // JP-8080 source: its own id block (JP_BASE + 16 * osc + j)
            for (auto key : jpKeys)
            {
                auto w = makeWidget (ctx, jp::jpId (o, jp::key (key)), true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            // Granular and Additive sources: their own id blocks (GR_BASE / AD_BASE + 16 * osc + j)
            for (auto key : grKeys)
            {
                auto w = makeWidget (ctx, gr::grId (o, gr::key (key)), true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            for (auto key : spKeys)
            {
                auto w = makeWidget (ctx, sp::spId (o, sp::key (key)), true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            for (auto key : sfKeys)
            {
                auto w = makeWidget (ctx, sf::sfId (o, sf::key (key)), true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            for (auto key : dkKeys)
            {
                auto w = makeWidget (ctx, dk::dkId (o, dk::key (key)), true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            for (auto key : adKeys)
            {
                auto w = makeWidget (ctx, ad::adId (o, ad::key (key)), true);
                w->onModDropped = [this] (ParamWidget& pw) { if (owner.onModDropped) owner.onModDropped (pw); };
                owner.addAndMakeVisible (*w);
                widgets[key] = std::move (w);
            }
            // Kick source: its own id block (KICK_BASE + 16 * osc + j)
            for (auto key : kickKeys)
            {
                auto w = makeWidget (ctx, kick::kickId (o, kick::key (key)), true);
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
            presetBtn.onClick = [this] { choosePreset(); };
            owner.addChildComponent (presetBtn);
            vault.onClick = [this] { if (ctx.onOpenVault) ctx.onOpenVault ((int) kind(), o, &vault); };

            ctx.addListener (this);
            mem.addChangeListener (this);
            refreshDz();
           
        }

        ~Impl() override { mem.removeChangeListener (this); ctx.removeListener (this); }

        ParamWidget* W (const char* key) { auto it = widgets.find (key); return it == widgets.end() ? nullptr : it->second.get(); }
        void openEditor()
        {
            if (tedit) tedit->open();
            else if (medit) { medit->open (mode == 3 ? 2 : 0); }
            layoutChildren();
        }
        int pnum (const char* key) const { return oscId (o, oscKey (key)); }
        int srcType() const { return juce::jlimit (0, 12, juce::roundToInt (ctx.get (pnum ("type")))); }
        static constexpr const char* terKeys[] = { "tcx", "tcy", "trx", "try", "trot", "tratio", "tphase", "tshape", "tmrate", "tmdep", "tterr2", "tmorph", "tsmooth", "tdrive", "tbits", "tvel" };
        static constexpr const char* wgKeys[] = { "wmodel", "wdecay", "wtone", "wexc", "wgpos", "wnoise", "wnl", "wstretch", "watk", "wsnare", "wbody", "wbodyf", "wvel", "wdrive", "wglide", "wktrack" };   // "wgpos" = the Waveguide Position (plain "wpos" is the wavetable one)
        static constexpr const char* jpKeys[] = { "jpwave", "jppw", "jppwm", "jppwr", "jpdet", "jpmix", "jpwid", "jpfb", "jpfbc", "jptmd", "jptmr", "jpstilt", "jpspk", "jpnz", "jpdrv", "jpsub" };
        static constexpr const char* grKeys[] = { "gpos", "gsize", "gdens", "gspray", "gpitch", "gpan", "gshape", "grev", "gscan", "gjit", "gdrive", "gvel" };
        static constexpr const char* adKeys[] = { "ashape", "ashapeb", "amorph", "acount", "atilt", "aodd", "ainh", "aform", "aformg", "ashim", "ashimr", "adec", "adrive", "awid", "avel" };
        static constexpr const char* spKeys[] = { "smode", "spos", "spos2", "smorph", "sscan", "sblur", "sshift", "stilt", "sharm", "sodd", "scomb", "scont", "sjit", "sspr", "swid", "svel" };
        static constexpr const char* sfKeys[] = { "sfgain", "sfvel", "sfatk", "sfdec", "sfsus", "sfrel", "sfloop", "sfpan", "sfstart", "sfdrive" };
        static constexpr const char* dkKeys[] = { "ddecay", "dtone", "dhit", "dstick", "dedge", "dres", "drtune", "dshell", "ddepth", "dsnare", "dsten", "dsym", "dtens", "dvel", "ddrive", "dsize" };
        static constexpr const char* kickKeys[] = { "kmode", "ksweep", "kstime", "kscurve", "kdec", "ktone", "kclick", "kcltone", "knoise", "kdrive", "kdtype", "ksub", "kpunch", "ktune", "kcldec", "kchar" };
        static constexpr const char* phyKeys[] = { "phmix", "phhard", "phntim", "phmodA", "phdecA", "phmatA", "phhitA", "phinhA", "phmodB", "phdecB", "phmatB", "phhitB", "phinhB", "phtunB", "phbal", "phser",
                                                         "jsaw", "jpulse", "jwidth", "jpwm", "jpwmr", "jsub", "jnoise", "jrange", "jdrift", "jcurve", "jptype", "jstype", "jbtype", "jpwms", "jvib" };
        SoundMemory::Kind kind() const { return srcType() == 12 ? SoundMemory::SoundFont : srcType() == 1 || srcType() == 8 || srcType() == 11 ? SoundMemory::Sample : SoundMemory::Wavetable; }

        // ---- memory / drop zone ----
        void refreshDz()
        {
            refreshTblDz();
            if (dz.getState() == DropZone::Busy) return;
            auto k = kind();
            auto* s = mem.get (k, o);
            if (s != nullptr) dz.setState (DropZone::Loaded, s->name);
            else dz.setState (DropZone::Empty, k == SoundMemory::Wavetable ? WT_DZ_EMPTY : k == SoundMemory::SoundFont ? SF_DZ_EMPTY : SMP_DZ_EMPTY);
            presetBtn.setText (presetLabel());
        }

        // SoundFont: the preset button shows the loaded preset and opens the list of the file's presets
        juce::String presetLabel() const
        {
            auto* s = mem.get (SoundMemory::SoundFont, o);
            return s == nullptr ? juce::String ("PRESET") : "PRESET " + juce::String (s->preset + 1) + " > " + s->name;
        }
        void choosePreset()
        {
            auto names = mem.soundFontPresets (o);
            if (names.isEmpty()) { ctx.status ("SOUNDFONT FILE NOT FOUND"); return; }
            auto* s = mem.get (SoundMemory::SoundFont, o);
            const int cur = s ? s->preset : -1;
            juce::PopupMenu m;
            for (int i = 0; i < names.size(); ++i) m.addItem (i + 1, names[i], true, i == cur);
            juce::Component::SafePointer<OscPage> safe (&owner);
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&presetBtn).withMinimumWidth (presetBtn.getWidth()).withMaximumNumColumns (1),
                             [safe, this] (int r)
                             {
                                 if (r <= 0 || safe == nullptr) return;
                                 mem.selectSoundFontPreset (o, r - 1, [safe] (bool, const juce::String&) { juce::MessageManager::callAsync ([safe] { if (safe != nullptr) safe->impl->refreshDz(); }); });
                             });
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
            chooser = std::make_shared<juce::FileChooser> (kind() == SoundMemory::SoundFont ? "Load a SoundFont" : "Load audio", juce::File(), kind() == SoundMemory::SoundFont ? juce::String ("*.sf2") : SoundMemory::fileWildcard());
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

        // Waveguide: each model names (and uses) its own parameters
        void updateJpLabels()
        {
            const int wave = juce::jlimit (0, 8, juce::roundToInt (ctx.get (jp::jpId (o, jp::key ("jpwave")))));
            for (auto key : jpKeys)
            {
                const int j = jp::key (key);
                if (j < 1) continue;
                auto* w = W (key);
                if (w == nullptr) continue;
                const juce::String lbl (jp::label (wave, j));
                w->setLabelOverride (lbl);
                w->setAlpha (lbl.isEmpty() ? 0.3f : 1.0f);
                w->setEnabled (lbl.isNotEmpty());
            }
        }

        void updateWgLabels()
        {
            const int model = juce::jlimit (0, 4, juce::roundToInt (ctx.get (wg::wgId (o, wg::key ("wmodel")))));
            for (auto key : wgKeys)
            {
                const int j = wg::key (juce::String (key) == "wgpos" ? "wpos" : key);
                if (j < 1) continue;
                auto* w = W (key);
                if (w == nullptr) continue;
                const juce::String lbl (wg::label (model, j));
                w->setLabelOverride (lbl);
                w->setAlpha (lbl.isEmpty() ? 0.3f : 1.0f);
                w->setEnabled (lbl.isNotEmpty());
            }
        }

        // ---- parameter changes ----
        void paramChanged (int num, float) override
        {
            if ((num >= gr::GR_BASE + gr::GR_STRIDE * o && num < gr::GR_BASE + gr::GR_STRIDE * (o + 1)) || (num >= ad::AD_BASE + ad::AD_STRIDE * o && num < ad::AD_BASE + ad::AD_STRIDE * (o + 1)) || (num >= dk::DK_BASE + dk::DK_STRIDE * o && num < dk::DK_BASE + dk::DK_STRIDE * (o + 1)) || (num >= sp::SP_BASE + sp::SP_STRIDE * o && num < sp::SP_BASE + sp::SP_STRIDE * (o + 1)) || (num >= sf::SF_BASE + sf::SF_STRIDE * o && num < sf::SF_BASE + sf::SF_STRIDE * (o + 1))) { owner.repaint(); return; }
            if (num >= jp::JP_BASE + jp::JP_STRIDE * o && num < jp::JP_BASE + jp::JP_STRIDE * (o + 1)) { updateJpLabels(); owner.repaint(); return; }
            if (num >= wg::WG_BASE + wg::WG_STRIDE * o && num < wg::WG_BASE + wg::WG_STRIDE * (o + 1)) { updateWgLabels(); owner.repaint(); return; }
            if (num >= phys::PHY_BASE + phys::PHY_STRIDE * o && num < phys::PHY_BASE + phys::PHY_STRIDE * (o + 1)) { owner.repaint(); return; }
            int k = num - oscId (o, 0);
            if (k < 0 || k >= OSC_STRIDE) return;
            if (k == oscKey ("type")) { if (dz.getState() != DropZone::Busy) dz.setState (DropZone::Empty, ""); refreshDz(); layoutChildren(); }
            else if (k == oscKey ("ftype") || k == oscKey ("dtype")) layoutChildren();
            owner.repaint();
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
                                        (juce::Component*) &presetBtn, (juce::Component*) &modeA, (juce::Component*) &modeB, (juce::Component*) &editBtn })
                c->setVisible (false);
            for (auto& c : chips) c->setVisible (false);
            const int type = srcType();
            const bool wt = type == 0, sm = type == 1, tr = type == 2, ph = type == 3 || type == 4 || type == 5 || type == 6 || type == 7 || type == 8 || type == 9 || type == 10 || type == 11 || type == 12, wgf = type == 6, jpf = type == 7, grf = type == 8, adf = type == 9, dkf = type == 10, spf = type == 11, sff = type == 12;
            const int cw = owner.getWidth(), ch = owner.getHeight();
            const double col = (cw - 88.0) / 12.0;
            auto span = [&] (int c0, int n) { return juce::Rectangle<int> (juce::roundToInt (c0 * (col + 8)), 0, juce::roundToInt (n * col + (n - 1) * 8), ch); };
            if (mode == 0) { cardSrc = span (0, 5); cardTune = span (5, 4); cardOut = span (9, 3); cardFlt = {}; }
            else { cardSrc = cardTune = {}; cardFlt = span (0, 8); cardOut = span (8, 4); }

            // ---- source ----
            if (mode == 0)
            {
                auto c = cardSrc; int w = c.getWidth();
                put ("type", 13, 24, w - 26, 36, c);
                display.setBounds (c.getX() + 13, c.getY() + 64, w - 26, 71);
                display.setVisible (true);
                dz.setBounds (c.getX() + 13, c.getY() + 136, w - 26 - (sff ? 0 : 56), 26);   // the vault has no SoundFont kind: the .sf2 is kept (path + preset + zone table) in the plugin state
                vault.setBounds (c.getX() + w - 13 - 49, c.getY() + 136, 49, 26);
                dz.setVisible (wt || sm || grf || spf || sff); vault.setVisible (wt || sm || grf || spf);
                presetBtn.setBounds (c.getX() + 13, c.getY() + 166, w - 26, 24); presetBtn.setVisible (sff);

                const int colW = (w - 26 - 7) / 2, x2 = 13 + colW + 7;
                put ("wpos", 13 + colW / 2 - 35, 190, 70, 54, c, wt);
                put ("wsize", x2, 202, colW, 36, c, wt);   strip ("wsize", x2, 202, colW, c, false, wt);
                put ("walias", x2, 241, colW, 33, c, wt);
                put ("w1m", 13, 279, colW, 36, c, wt);     strip ("w1m", 13, 279, colW, c, false, wt);
                knob ("w1a", x2 + colW / 2, 269, c, wt);
                put ("w2m", 13, 358, colW, 36, c, wt);     strip ("w2m", 13, 358, colW, c, false, wt);
                knob ("w2a", x2 + colW / 2, 348, c, wt);

                put ("root", 13, grf ? 200 : 248, 106, 17, c, sm || grf);     strip ("root", 13, grf ? 188 : 236, 106, c, true, sm || grf);
                knob ("sstart", 179, 222, c, sm);
                put ("sloop", 13, 337, w - 26, 32, c, sm);

                {   // Wave Terrain: two terrain selectors, then the macro knobs, the orbit and the output, five knobs per row
                    const int cw2 = (w - 26 - 8) / 2;
                    put ("tterr", 13, 146, cw2, 36, c, tr);  strip ("tterr", 13, 146, cw2, c, false, tr);
                    put ("tterr2", 13 + cw2 + 8, 146, cw2, 36, c, tr);  strip ("tterr2", 13 + cw2 + 8, 146, cw2, c, false, tr);
                    const float fw = (float) (w - 26);
                    const char* rows[4][5] = { { "tscale", "twarp", "tfold", "tmorph", "tsmooth" }, { "tcx", "tcy", "trx", "try", "trot" },
                                               { "tratio", "tphase", "tshape", "tmrate", "tmdep" }, { "tdrive", "tbits", "tvel", nullptr, nullptr } };
                    for (int r = 0; r < 4; ++r)
                        for (int i = 0; i < 5; ++i)
                            if (rows[r][i] != nullptr) knob (rows[r][i], 13 + juce::roundToInt (fw * (2 * i + 1) / 10), 192 + 56 * r, c, tr);
                }

                {   // Waveguide: the model selector, then three rows of knobs; labels follow the model, unused knobs are dimmed
                    put ("wmodel", 13, 146, w - 26, 36, c, wgf);  strip ("wmodel", 13, 146, w - 26, c, false, wgf);
                    const float fw = (float) (w - 26);
                    const char* rows[3][5] = { { "wdecay", "wtone", "wexc", "wgpos", "wnoise" }, { "wnl", "wstretch", "watk", "wsnare", "wvel" },
                                               { "wbody", "wbodyf", "wdrive", "wglide", "wktrack" } };
                    for (int r = 0; r < 3; ++r)
                        for (int i = 0; i < 5; ++i)
                            knob (rows[r][i], 13 + juce::roundToInt (fw * (2 * i + 1) / 10), 192 + 62 * r, c, wgf);
                    if (wgf) updateWgLabels();
                }

                {   // JP-8080: the waveform selector, then three rows of knobs; labels follow the waveform, unused knobs are dimmed
                    put ("jpwave", 13, 146, w - 26, 36, c, jpf);  strip ("jpwave", 13, 146, w - 26, c, false, jpf);
                    const float fw = (float) (w - 26);
                    const char* rows[3][5] = { { "jppw", "jppwm", "jppwr", "jpdet", "jpmix" }, { "jpwid", "jpfb", "jpfbc", "jptmd", "jptmr" },
                                               { "jpstilt", "jpspk", "jpnz", "jpsub", "jpdrv" } };
                    for (int r = 0; r < 3; ++r)
                        for (int i = 0; i < 5; ++i)
                            knob (rows[r][i], 13 + juce::roundToInt (fw * (2 * i + 1) / 10), 192 + 62 * r, c, jpf);
                    if (jpf) updateJpLabels();
                }

                {   // Granular: the sample memory (drop zone above) and three rows of knobs
                    const float fw = (float) (w - 26);
                    const char* rows[3][5] = { { "gpos", "gsize", "gdens", "gspray", "gpitch" }, { "gpan", "gshape", "grev", "gscan", "gjit" }, { "gvel", "gdrive", nullptr, nullptr, nullptr } };
                    for (int r = 0; r < 3; ++r)
                        for (int i = 0; i < 5; ++i)
                            if (rows[r][i] != nullptr) knob (rows[r][i], 13 + juce::roundToInt (fw * (2 * i + 1) / 10), 222 + 62 * r, c, grf);
                }

                {   // Additive: two spectrum selectors, then rows of knobs
                    const int cw2 = (w - 26 - 8) / 2;
                    put ("ashape", 13, 146, cw2, 36, c, adf);  strip ("ashape", 13, 146, cw2, c, false, adf);
                    put ("ashapeb", 13 + cw2 + 8, 146, cw2, 36, c, adf);  strip ("ashapeb", 13 + cw2 + 8, 146, cw2, c, false, adf);
                    const float fw = (float) (w - 26);
                    const char* rows[3][5] = { { "amorph", "acount", "atilt", "aodd", "ainh" }, { "aform", "aformg", "ashim", "ashimr", "adec" }, { "awid", "avel", "adrive", nullptr, nullptr } };
                    for (int r = 0; r < 3; ++r)
                        for (int i = 0; i < 5; ++i)
                            if (rows[r][i] != nullptr) knob (rows[r][i], 13 + juce::roundToInt (fw * (2 * i + 1) / 10), 192 + 62 * r, c, adf);
                }

                {   // Spectral: the Resynth / Spectrum switch (sample drop zone above), then three rows of five knobs
                    put ("smode", 13, 168, w - 26, 28, c, spf);
                    const float fw = (float) (w - 26);
                    const char* rows[3][5] = { { "spos", "spos2", "smorph", "sscan", "sblur" }, { "sshift", "stilt", "sharm", "sodd", "scomb" }, { "scont", "sjit", "sspr", "swid", "svel" } };
                    for (int r = 0; r < 3; ++r)
                        for (int i = 0; i < 5; ++i)
                            knob (rows[r][i], 13 + juce::roundToInt (fw * (2 * i + 1) / 10), 222 + 62 * r, c, spf);
                }

                {   // SoundFont: preset button above, the loop switch, then two rows of knobs
                    put ("sfloop", 13, 198, w - 26, 28, c, sff);
                    const float fw = (float) (w - 26);
                    const char* rows[2][5] = { { "sfgain", "sfvel", "sfatk", "sfdec", "sfsus" }, { "sfrel", "sfpan", "sfstart", "sfdrive", nullptr } };
                    for (int r = 0; r < 2; ++r)
                        for (int i = 0; i < 5; ++i)
                            if (rows[r][i] != nullptr) knob (rows[r][i], 13 + juce::roundToInt (fw * (2 * i + 1) / 10), 240 + 66 * r, c, sff);
                }

                {   // Modal Drum: four rows of four knobs
                    const float fw = (float) (w - 26);
                    for (int r = 0; r < 4; ++r)
                        for (int i = 0; i < 4; ++i)
                            knob (dkKeys[r * 4 + i], 13 + juce::roundToInt (fw * (2 * i + 1) / 8), 150 + 62 * r, c, dkf);
                }

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
                // Kick: body, click / noise / sub, drive
                if (type == 5)
                {
                    const int cw2 = (w - 26 - 8) / 2, xb = 13 + cw2 + 8;
                    put ("kmode", 13, 152, cw2, 36, c);  put ("kdtype", xb, 152, cw2, 36, c);
                    const float fwk = (float) (w - 26);
                    const char* r1[4] = { "ksweep", "kstime", "kscurve", "kdec" };
                    const char* r2[4] = { "ktone", "kchar", "ktune", "kpunch" };
                    const char* r3[4] = { "kclick", "kcltone", "kcldec", "knoise" };
                    for (int i = 0; i < 4; ++i)
                    {
                        const int cx = 13 + juce::roundToInt (fwk * (2 * i + 1) / 8);
                        knob (r1[i], cx, 192, c); knob (r2[i], cx, 248, c); knob (r3[i], cx, 304, c);
                    }
                    knob ("ksub", 13 + juce::roundToInt (fwk * 1 / 8), 360, c);
                    knob ("kdrive", 13 + juce::roundToInt (fwk * 3 / 8), 360, c);
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
                int fineTop = 86;   // the unison section below is the same for every source
                knob ("fine", cl, fineTop, c);
                put ("track", rx, fineTop + 24, 72, 18, c); strip ("track", rx, fineTop + 11, 72, c, true);
                int phaseTop = 152;
                knob ("phase", cl, phaseTop, c, ! (tr || ph));
                knob ("freq", cr, 205, c);   // fixed frequency (0 = Off), target of the Freq modulators
                put ("rphase", rx, phaseTop + 24, 72, 18, c, ! (tr || ph)); strip ("rphase", rx, phaseTop + 11, 72, c, true, ! (tr || ph));

                const bool uni = true;      // every source has unison (wavetable and Alpha Juno natively, the others through the detuned-copy stage)
                showUnison = uni;
                const int u0 = 12 + (w - 24) / 6, u1 = 12 + (w - 24) / 2, u2 = 12 + (w - 24) * 5 / 6;
                knob ("udet", u0, 256, c, uni);  knob ("ublend", u1, 256, c, uni);  knob ("uwid", u2, 256, c, uni);
                knob ("udrift", u0, 316, c, uni);  knob ("uphase", u1, 316, c, uni);
                put ("uvox", u2 - 36, 343, 72, 17, c, uni);   strip ("uvox", u2 - 36, 331, 72, c, true, uni);
                put ("ustyle", lx, 383, w - 24, 44, c, uni);
                if (auto* ub = dynamic_cast<ButtonsWidget*> (W ("ustyle"))) ub->setColumns (3);
            }
            // ---- output (oscillator page) ----
            if (mode == 0)
            {
                auto c = cardOut; int w = c.getWidth();
                const int cl = 12 + (w - 24) / 4, cr = 12 + (w - 24) * 3 / 4;
                knob ("level", cl, 60, c); knob ("pan", cr, 60, c);
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
            // edit buttons: the table editor (filter / distortion pages), the resonator editor (Physical source, resonator page)
            {
                const bool tbl = (mode == 1 || mode == 2);
                const bool res = (mode == 3) || (mode == 0 && type == 3);
                if (tbl) { editBtn.setBounds (cardOut.getRight() - 12 - 84, 6, 84, 18); editBtn.setVisible (true); }
                else if (res) { auto& cc = mode == 3 ? cardFlt : cardSrc; editBtn.setBounds (cc.getRight() - 12 - 96, 6, 96, 18); editBtn.setVisible (true); }
                for (juce::Component* e : { (juce::Component*) tedit.get(), (juce::Component*) medit.get() })
                    if (e) { e->setBounds (owner.getLocalBounds()); }
                if ((tedit && tedit->isVisible()) || (medit && medit->isVisible())) editBtn.setVisible (false);
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
        DropZone dz, dzF, dzS; PushButton vault, presetBtn { "PRESET" };
        PushButton modeA, modeB, editBtn; std::unique_ptr<TableEditor> tedit; std::unique_ptr<ModeEditor> medit;
         std::array<std::unique_ptr<PushButton>, OSC_N> chips;
        std::shared_ptr<juce::FileChooser> chooser;
    };

    // ============================================================================================ OscPage
    OscPage::OscPage (Ctx& c, SoundMemory& m, int o, int mode) : impl (new Impl (*this, c, m, o, mode)) {}
    OscPage::~OscPage() = default;

    void OscPage::paint (juce::Graphics& g) { impl->paintAll (g); }
    void OscPage::resized() { impl->layoutChildren(); }
}
