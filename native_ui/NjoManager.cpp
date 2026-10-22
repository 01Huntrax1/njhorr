// The preset bar, the Preset Bank and the Sound Vault (port of MGR_HTML / MGR_OVERLAY_HTML / buildManager of patch/index.js).
// Files: <Backend::rootFolder()>/{Presets,Samples,Wavetables}; the preset file format is shared with the web UI (NjoManagerStore.h).
#include "NjoManager.h"
#include "NjoManagerStore.h"
#include "NjoLfo.h"

using namespace njo;
using namespace njo::mgr;

namespace
{
    const juce::String NAME_BANK = "PRESET BANK", NAME_VAULT = "SOUND VAULT";

    struct SlotDef { juce::String key, label, shortName; int kind, osc; };
    const std::vector<SlotDef>& slotDefs()
    {
        static std::vector<SlotDef> d;
        if (d.empty())
        {
            for (int o = 0; o < OSC_N; ++o) d.push_back ({ "wt" + juce::String (o), "OSC " + juce::String (o + 1) + " WAVETABLE", "OSC" + juce::String (o + 1) + " WT", 0, o });
            for (int o = 0; o < OSC_N; ++o) d.push_back ({ "sm" + juce::String (o), "OSC " + juce::String (o + 1) + " SAMPLER", "OSC" + juce::String (o + 1) + " SMP", 1, o });
        }
        return d;
    }
    juce::String slotKey (int kind, int osc) { return (kind == 0 ? "wt" : "sm") + juce::String (osc); }
    const SlotDef* findSlot (const juce::String& key) { for (auto& s : slotDefs()) if (s.key == key) return &s; return nullptr; }

    struct OneShot : juce::Timer
    {
        std::function<void()> fn;
        void timerCallback() override { stopTimer(); if (fn) fn(); }
    };

    class PbButton : public juce::Button
    {
    public:
        enum Style { Text, Left, Right, Close, Name };
        explicit PbButton (const juce::String& t = {}, Style s = Text) : juce::Button (t), style (s) { setMouseCursor (juce::MouseCursor::PointingHandCursor); }
        bool armed = false;

        void paintButton (juce::Graphics& g, bool hover, bool down) override
        {
            auto r = getLocalBounds().toFloat().reduced (0.5f);
            if (style == Name)
            {
                theme::paintInset (g, r);
                g.setColour (hover ? juce::Colours::white : theme::ink);
                g.setFont (theme::font (10.5f, true));
                g.drawText (getButtonText(), r.reduced (8.0f, 0.0f), juce::Justification::centredLeft, true);
                return;
            }
            bool on = getToggleState() || armed;
            theme::paintButton (g, r, on, hover, down);
            g.setColour (on ? juce::Colours::white : (hover ? theme::ink : theme::dim));
            auto c = r.getCentre();
            if (style == Left || style == Right)
            {
                juce::Path p; float d = style == Left ? -1.0f : 1.0f;
                p.addTriangle (c.x - 3.0f * d, c.y - 4.5f, c.x - 3.0f * d, c.y + 4.5f, c.x + 3.5f * d, c.y);
                g.fillPath (p);
            }
            else if (style == Close)
            {
                g.drawLine (c.x - 4, c.y - 4, c.x + 4, c.y + 4, 1.6f); g.drawLine (c.x - 4, c.y + 4, c.x + 4, c.y - 4, 1.6f);
            }
            else
            {
                g.setFont (theme::font (9.0f, true));
                g.drawText (getButtonText(), r.reduced (2.0f, 0.0f), juce::Justification::centred, true);
            }
        }
    private:
        Style style;
    };

    void styleEditor (juce::TextEditor& e, const juce::String& placeholder, int maxLen)
    {
        e.setFont (theme::font (11.0f));
        e.setColour (juce::TextEditor::backgroundColourId, theme::deep);
        e.setColour (juce::TextEditor::textColourId, theme::ink);
        e.setColour (juce::TextEditor::outlineColourId, theme::line);
        e.setColour (juce::TextEditor::focusedOutlineColourId, theme::red);
        e.setColour (juce::TextEditor::highlightColourId, theme::redDark);
        e.setColour (juce::CaretComponent::caretColourId, theme::red);
        e.setTextToShowWhenEmpty (placeholder, theme::dim);
        e.setMultiLine (false); e.setReturnKeyStartsNewLine (false); e.setScrollbarsShown (false);
        e.setIndents (6, 5);
        if (maxLen > 0) e.setInputRestrictions (maxLen);
    }

    void styleList (juce::ListBox& l)
    {
        l.setColour (juce::ListBox::backgroundColourId, theme::deep);
        l.setColour (juce::ListBox::outlineColourId, theme::line);
        l.setOutlineThickness (1);
        l.getVerticalScrollBar().setColour (juce::ScrollBar::thumbColourId, theme::steel);
    }

    // ------------------------------------------------------------------ overlay frame
    class OverlayBase : public juce::Component
    {
    public:
        OverlayBase (const juce::String& t, int w, int h) : title (t), boxW (w), boxH (h), closeBtn ("", PbButton::Close)
        {
            setWantsKeyboardFocus (true);
            setAlwaysOnTop (true);
            addAndMakeVisible (closeBtn);
            closeBtn.onClick = [this] { if (onClose) onClose(); };
        }
        std::function<void()> onClose;

        juce::Rectangle<int> box() const { return getLocalBounds().withSizeKeepingCentre (juce::jmin (boxW, getWidth() - 20), juce::jmin (boxH, getHeight() - 20)); }
        virtual void layoutBody (juce::Rectangle<int> r) = 0;

        void paint (juce::Graphics& g) override
        {
            g.fillAll (juce::Colours::black.withAlpha (0.68f));
            auto b = box();
            theme::paintCard (g, b.toFloat(), 10.0f);
            g.setColour (theme::ink);
            g.setFont (theme::impact (16.0f));
            g.drawText (title, b.getX() + 18, b.getY() + 10, 400, 24, juce::Justification::centredLeft);
        }
        void resized() override
        {
            auto b = box().reduced (18, 12);
            auto head = b.removeFromTop (28);
            closeBtn.setBounds (head.removeFromRight (28));
            b.removeFromTop (8);
            layoutBody (b.withTrimmedBottom (6));
        }
        void mouseDown (const juce::MouseEvent& e) override { if (! box().contains (e.getPosition()) && onClose) onClose(); }
        bool keyPressed (const juce::KeyPress& k) override
        {
            if (k == juce::KeyPress::escapeKey) { if (onClose) onClose(); return true; }
            return false;
        }
    protected:
        void drawLine (juce::Graphics& g, const juce::String& t, juce::Rectangle<int> r, juce::Colour c, bool mono = false)
        {
            g.setColour (c); g.setFont (mono ? theme::mono (9.5f) : theme::font (9.5f, true));
            g.drawText (t, r, juce::Justification::centredLeft, true);
        }
        juce::String title;
        int boxW, boxH;
        PbButton closeBtn;
    };

    class PresetOverlay;
    class VaultOverlay;
}

// ====================================================================== Impl
struct ManagerBar::Impl : private Ctx::Listener, private juce::ChangeListener, private juce::ComponentListener
{
    Impl (ManagerBar& o, Ctx& c, SoundMemory& m, juce::Component& h);
    ~Impl() override;

    ManagerBar& owner; Ctx& ctx; SoundMemory& memory; juce::Component& host;
    Store store;
    std::shared_ptr<bool> alive = std::make_shared<bool> (true);

    // ---- preset state
    struct Cur { juce::String id, name = "Init"; bool dirty = false; } cur;
    std::vector<PresetRec> presets;
    juce::String sel = "__init";
    bool applying = false;
    int pendingLoads = 0;
    juce::String memSig;
    // ---- vault state
    std::vector<LibRec> lib;
    std::map<juce::String, double> durCache;
    struct SlotRef { juce::String id, name; };
    std::map<juce::String, SlotRef> slotLib;
    int libKind = 1, libTarget = -1;
    juce::String renamingId, armed;
    // ---- bar
    PbButton prev { "", PbButton::Left }, next { "", PbButton::Right }, nameBtn { "Init", PbButton::Name }, save { "SAVE" }, bank { "BANK" }, vault { "VAULT" };
    juce::String infoText; juce::Rectangle<int> infoRect;
    OneShot infoTimer, armTimer;
    // ---- overlays
    std::unique_ptr<PresetOverlay> presetOv;
    std::unique_ptr<VaultOverlay> vaultOv;
    std::unique_ptr<juce::FileChooser> chooser;

    void defer (std::function<void()> f) { auto a = alive; juce::MessageManager::callAsync ([a, f] { if (*a) f(); }); }

    // bar
    void barInfo (const juce::String& t);
    void updateBar();
    void presetDirty();
    // presets
    void presetsRefresh();
    PresetRec collectRec (const juce::String& name);
    bool nameTaken (const juce::String& name, const juce::String& exceptId) const;
    juce::String presetSaveAs (const juce::String& name, const juce::String& id);
    void presetQuickSave();
    void presetApply (const PresetRec& rec, const juce::String& label = {});
    void presetInit();
    void presetStep (int dir);
    const PresetRec* findPreset (const juce::String& id) const { for (auto& p : presets) if (p.id == id) return &p; return nullptr; }
    const PresetRec* selPreset() const { return findPreset (sel); }
    void pmAct (const juce::String& act);
    void pmStatus (const juce::String& t);
    // vault
    void libRefresh();
    const LibRec* findLib (const juce::String& id) const { for (auto& r : lib) if (r.id == id) return &r; return nullptr; }
    void libStatus (const juce::String& t);
    void libImport (const juce::Array<juce::File>& files);
    void libLoad (const juce::String& id, int osc);
    void libRenameDone (const juce::String& id, const juce::String* value);
    void libAct (const juce::String& act, const juce::String& id);
    void arm (const juce::String& key);
    void setSlot (const juce::String& key, const juce::String& id, const juce::String& name);
    void saveSlots();
    void reconcileSlots();
    juce::String signature() const;
    void swapId (const juce::String& oldId, const juce::String& newId);
    void openFolder (int what);       // 0 presets, 1 vault (current kind)
    // overlays
    void openBank();
    void openVault (int kind, int osc);
    void closeAll();
    void layoutOverlays();
    void refreshVault();
    void refreshBank();

private:
    void paramChanged (int, float) override { if (! applying) presetDirty(); }
    void changeListenerCallback (juce::ChangeBroadcaster*) override;
    void componentMovedOrResized (juce::Component&, bool, bool) override { layoutOverlays(); }
};

namespace
{
    // ================================================================== Preset Bank overlay
    class PresetOverlay : public OverlayBase, public juce::ListBoxModel
    {
    public:
        struct Item { juce::String id, name, sub; bool builtin = false, current = false; };

        explicit PresetOverlay (ManagerBar::Impl& im)
            : OverlayBase (NAME_BANK, 860, 560), m (im), list ("presets", this),
              bNew ("SAVE AS NEW"), bOver ("OVERWRITE"), bRen ("RENAME"), bDel ("DELETE"),
              bLoad ("LOAD"), bInit ("INIT SOUND"), bFolder ("OPEN FOLDER"), bRescan ("RESCAN")
        {
            styleEditor (nameIn, "Preset name", 40);
            for (auto* c : { (juce::Component*) &nameIn, (juce::Component*) &list, (juce::Component*) &bNew, (juce::Component*) &bOver, (juce::Component*) &bRen,
                             (juce::Component*) &bDel, (juce::Component*) &bLoad, (juce::Component*) &bInit, (juce::Component*) &bFolder, (juce::Component*) &bRescan })
                addAndMakeVisible (c);
            styleList (list); list.setRowHeight (26);
            nameIn.onEscapeKey = [this] { if (onClose) onClose(); };
            nameIn.onReturnKey = [this] { m.pmAct ("pm-new"); };
            bNew.onClick = [this] { m.pmAct ("pm-new"); };     bOver.onClick = [this] { m.pmAct ("pm-over"); };
            bRen.onClick = [this] { m.pmAct ("pm-ren"); };     bDel.onClick = [this] { m.pmAct ("pm-del"); };
            bLoad.onClick = [this] { m.pmAct ("pm-load"); };   bInit.onClick = [this] { m.pmAct ("pm-init"); };
            bFolder.onClick = [this] { m.pmAct ("open-folder"); };  bRescan.onClick = [this] { m.pmAct ("pm-rescan"); };
        }

        void setStatus (const juce::String& s) { status = s; repaint (statusR); }

        void refresh()
        {
            items.clear();
            items.push_back ({ "__init", "Init", "factory", true, m.cur.id.isEmpty() && m.cur.name == "Init" });
            for (auto& p : m.presets)
                items.push_back ({ p.id, p.name, juce::Time (p.saved).toString (true, false), false, p.id == m.cur.id });
            path = "FOLDER  " + m.store.presetsDir().getFullPathName();
            inRefresh = true;
            list.updateContent();
            int row = -1;
            for (int i = 0; i < (int) items.size(); ++i) if (items[(size_t) i].id == m.sel) row = i;
            if (row >= 0) list.selectRow (row, true, true); else list.deselectAllRows();
            inRefresh = false;
            bDel.armed = m.armed == "pm"; bDel.setButtonText (bDel.armed ? "SURE?" : "DELETE"); bDel.repaint();
            list.repaint(); repaint();
        }
        void setName (const juce::String& s) { nameIn.setText (s, false); }
        juce::String name() const { return nameIn.getText(); }

        // ListBoxModel
        int getNumRows() override { return (int) items.size(); }
        void paintListBoxItem (int row, juce::Graphics& g, int w, int h, bool selected) override
        {
            if (row < 0 || row >= (int) items.size()) return;
            auto& it = items[(size_t) row];
            if (selected) { g.setColour (theme::redDark.withAlpha (0.55f)); g.fillRect (0, 0, w, h); }
            else if (row % 2) { g.setColour (juce::Colours::white.withAlpha (0.025f)); g.fillRect (0, 0, w, h); }
            g.setColour (it.current ? theme::red : theme::steel);
            g.fillEllipse (10.0f, h * 0.5f - 3.5f, 7.0f, 7.0f);
            g.setColour (selected ? juce::Colours::white : theme::ink); g.setFont (theme::font (11.0f, true));
            g.drawText (it.name, 26, 0, w - 180, h, juce::Justification::centredLeft, true);
            g.setColour (theme::dim); g.setFont (theme::font (9.5f));
            g.drawText (it.sub, w - 150, 0, 140, h, juce::Justification::centredRight, true);
        }
        void selectedRowsChanged (int row) override
        {
            if (inRefresh || row < 0 || row >= (int) items.size()) return;
            m.sel = items[(size_t) row].id;
            auto* p = m.selPreset();
            setName (p ? p->name : juce::String());
        }
        void listBoxItemDoubleClicked (int row, const juce::MouseEvent&) override
        {
            if (row < 0 || row >= (int) items.size()) return;
            m.sel = items[(size_t) row].id;
            m.defer ([this] { m.pmAct ("pm-load"); });
        }

        void layoutBody (juce::Rectangle<int> r) override
        {
            auto top = r.removeFromTop (28);
            bDel.setBounds (top.removeFromRight (72)); top.removeFromRight (6);
            bRen.setBounds (top.removeFromRight (72)); top.removeFromRight (6);
            bOver.setBounds (top.removeFromRight (88)); top.removeFromRight (6);
            bNew.setBounds (top.removeFromRight (104)); top.removeFromRight (8);
            nameIn.setBounds (top);
            r.removeFromTop (8);
            statusR = r.removeFromBottom (18);
            pathR = r.removeFromBottom (16);
            r.removeFromBottom (4);
            auto bot = r.removeFromBottom (28);
            r.removeFromBottom (8);
            bLoad.setBounds (bot.removeFromLeft (80)); bot.removeFromLeft (6);
            bInit.setBounds (bot.removeFromLeft (100));
            bRescan.setBounds (bot.removeFromRight (80)); bot.removeFromRight (6);
            bFolder.setBounds (bot.removeFromRight (110));
            list.setBounds (r);
        }
        void paint (juce::Graphics& g) override
        {
            OverlayBase::paint (g);
            drawLine (g, path, pathR, theme::dim, true);
            drawLine (g, status, statusR, theme::orange);
        }

        ManagerBar::Impl& m;
        std::vector<Item> items;
        juce::ListBox list;
        juce::TextEditor nameIn;
        PbButton bNew, bOver, bRen, bDel, bLoad, bInit, bFolder, bRescan;
        juce::String status, path;
        juce::Rectangle<int> statusR, pathR;
        bool inRefresh = false;
    };

    // ================================================================== Sound Vault overlay
    class VaultOverlay : public OverlayBase, public juce::ListBoxModel, public juce::FileDragAndDropTarget
    {
    public:
        explicit VaultOverlay (ManagerBar::Impl& im)
            : OverlayBase (NAME_VAULT, 860, 580), m (im), list ("vault", this),
              tabSmp ("SAMPLES"), tabWt ("WAVETABLES"), bAdd ("ADD FILES"), bFolder ("OPEN FOLDER"), bRescan ("RESCAN")
        {
            styleEditor (search, "Search", 0);
            for (auto* c : { (juce::Component*) &search, (juce::Component*) &list, (juce::Component*) &tabSmp, (juce::Component*) &tabWt,
                             (juce::Component*) &bAdd, (juce::Component*) &bFolder, (juce::Component*) &bRescan })
                addAndMakeVisible (c);
            styleList (list); list.setRowHeight (28);
            search.onTextChange = [this] { refresh(); };
            search.onEscapeKey = [this] { if (onClose) onClose(); };
            tabSmp.onClick = [this] { m.libKind = 1; m.libTarget = -1; m.renamingId = {}; refresh(); };
            tabWt.onClick = [this] { m.libKind = 0; m.libTarget = -1; m.renamingId = {}; refresh(); };
            bAdd.onClick = [this] { m.libAct ("lb-import", {}); };
            bFolder.onClick = [this] { m.openFolder (1); };
            bRescan.onClick = [this] { m.libAct ("lb-rescan", {}); };
        }

        void setStatus (const juce::String& s) { msg = s; repaint (statusR); }
        void refresh()
        {
            tabSmp.setToggleState (m.libKind == 1, juce::dontSendNotification);
            tabWt.setToggleState (m.libKind == 0, juce::dontSendNotification);
            auto term = search.getText().trim().toLowerCase();
            rows.clear();
            for (auto& r : m.lib)
                if (r.kind == m.libKind && (term.isEmpty() || r.label.toLowerCase().contains (term) || r.fname.toLowerCase().contains (term)))
                    rows.push_back (r);
            path = "FOLDER  " + m.store.kindDir (m.libKind).getFullPathName();
            if (m.libTarget >= 0)
                target = "LOADING INTO: " + findSlot (slotKey (m.libKind, m.libTarget))->label;
            else target = "CHOOSE A TARGET BUTTON ON EACH ROW";
            list.updateContent(); list.repaint(); repaint();
        }
        juce::String statusLine() const
        {
            juce::int64 total = 0; for (auto& r : m.lib) total += r.size;
            return (msg.isNotEmpty() ? msg + "  |  " : juce::String()) + juce::String ((int) m.lib.size()) + " FILES, " + fmtBytes (total);
        }

        int getNumRows() override { return (int) rows.size(); }
        void paintListBoxItem (int, juce::Graphics&, int, int, bool) override {}
        juce::Component* refreshComponentForRow (int row, bool, juce::Component* existing) override;
        void paintOverChildren (juce::Graphics& g) override
        {
            if (rows.empty())
            {
                g.setColour (theme::dim); g.setFont (theme::font (10.0f, true));
                g.drawFittedText (m.lib.empty() ? "EMPTY - ADD FILES, DROP THEM HERE, OR LOAD ONE INTO AN OSCILLATOR AND IT APPEARS HERE" : "NOTHING MATCHES",
                                  list.getBounds().reduced (30), juce::Justification::centred, 3);
            }
            if (dropHover)
            {
                g.setColour (theme::red); g.drawRect (box().reduced (6), 2);
                g.setColour (theme::red.withAlpha (0.12f)); g.fillRect (box().reduced (6));
                g.setColour (juce::Colours::white); g.setFont (theme::impact (20.0f));
                g.drawText ("DROP FILES TO ADD THEM TO THE " + juce::String (m.libKind == 1 ? "SAMPLES" : "WAVETABLES"), box(), juce::Justification::centred);
            }
        }
        void paint (juce::Graphics& g) override
        {
            OverlayBase::paint (g);
            drawLine (g, target, targetR, m.libTarget >= 0 ? theme::red : theme::dim);
            drawLine (g, path, pathR, theme::dim, true);
            drawLine (g, statusLine(), statusR, theme::orange);
        }
        void layoutBody (juce::Rectangle<int> r) override
        {
            auto top = r.removeFromTop (28);
            tabSmp.setBounds (top.removeFromLeft (90)); top.removeFromLeft (4);
            tabWt.setBounds (top.removeFromLeft (110)); top.removeFromLeft (10);
            bRescan.setBounds (top.removeFromRight (80)); top.removeFromRight (6);
            bFolder.setBounds (top.removeFromRight (110)); top.removeFromRight (6);
            bAdd.setBounds (top.removeFromRight (90)); top.removeFromRight (10);
            search.setBounds (top);
            r.removeFromTop (6);
            targetR = r.removeFromTop (16); r.removeFromTop (4);
            statusR = r.removeFromBottom (18);
            pathR = r.removeFromBottom (16);
            r.removeFromBottom (4);
            list.setBounds (r);
        }
        // drag and drop of files onto the overlay
        bool isInterestedInFileDrag (const juce::StringArray&) override { return isVisible(); }
        void fileDragEnter (const juce::StringArray&, int, int) override { dropHover = true; repaint(); }
        void fileDragExit (const juce::StringArray&) override { dropHover = false; repaint(); }
        void filesDropped (const juce::StringArray& files, int, int) override
        {
            dropHover = false; repaint();
            juce::Array<juce::File> fs; for (auto& f : files) fs.add (juce::File (f));
            m.libImport (fs);
        }

        ManagerBar::Impl& m;
        std::vector<LibRec> rows;
        juce::ListBox list;
        juce::TextEditor search;
        PbButton tabSmp, tabWt, bAdd, bFolder, bRescan;
        juce::String msg, path, target;
        juce::Rectangle<int> statusR, pathR, targetR;
        bool dropHover = false;
    };

    class VRow : public juce::Component
    {
    public:
        VRow (VaultOverlay& o, ManagerBar::Impl& im, const LibRec& r, int index) : ov (o), m (im), rec (r), idx (index)
        {
            auto* mp = &m; auto id = rec.id;
            auto add = [this] (const juce::String& t) -> PbButton& { auto* b = btns.add (new PbButton (t)); addAndMakeVisible (b); return *b; };
            if (m.libTarget >= 0)
            {
                int osc = m.libTarget;
                add ("LOAD").onClick = [mp, id, osc] { mp->defer ([mp, id, osc] { mp->libLoad (id, osc); }); };
            }
            else
                for (int osc = 0; osc < OSC_N; ++osc)
                    add ("OSC" + juce::String (osc + 1)).onClick = [mp, id, osc] { mp->defer ([mp, id, osc] { mp->libLoad (id, osc); }); };
            nSlot = btns.size();
            add ("REN").onClick = [mp, id] { mp->defer ([mp, id] { mp->libAct ("lb-ren", id); }); };
            add (rec.kind == 1 ? "> WT" : "> SMP").onClick = [mp, id] { mp->defer ([mp, id] { mp->libAct ("lb-kind", id); }); };
            auto& del = add (m.armed == "lb:" + id ? "SURE?" : "DEL");
            del.armed = m.armed == "lb:" + id;
            del.onClick = [mp, id] { mp->defer ([mp, id] { mp->libAct ("lb-del", id); }); };

            for (auto& s : m.slotLib) if (s.second.id == rec.id) if (auto* d = findSlot (s.first)) inUse << (inUse.isEmpty() ? "" : " ") << d->shortName;

            if (m.renamingId == rec.id)
            {
                edit.reset (new juce::TextEditor());
                styleEditor (*edit, {}, 60);
                edit->setText (rec.label, false);
                addAndMakeVisible (*edit);
                edit->onReturnKey = [mp, id, e = edit.get()] { auto t = e->getText(); mp->defer ([mp, id, t] { mp->libRenameDone (id, &t); }); };
                edit->onEscapeKey = [mp, id] { mp->defer ([mp, id] { mp->libRenameDone (id, nullptr); }); };
                edit->onFocusLost = [mp, id, e = edit.get()] { auto t = e->getText(); mp->defer ([mp, id, t] { mp->libRenameDone (id, &t); }); };
                juce::Component::SafePointer<juce::TextEditor> sp (edit.get());
                m.defer ([sp] { if (sp != nullptr) { sp->grabKeyboardFocus(); sp->selectAll(); } });
            }
        }
        void paint (juce::Graphics& g) override
        {
            auto r = getLocalBounds();
            if (idx % 2) { g.setColour (juce::Colours::white.withAlpha (0.025f)); g.fillRect (r); }
            g.setColour (inUse.isNotEmpty() ? theme::red : theme::steel);
            g.fillEllipse (10.0f, r.getHeight() * 0.5f - 3.5f, 7.0f, 7.0f);
            if (! edit)
            {
                g.setColour (theme::ink); g.setFont (theme::font (11.0f, true));
                g.drawText (rec.label, nameR, juce::Justification::centredLeft, true);
            }
            g.setColour (theme::dim); g.setFont (theme::font (9.5f));
            g.drawText ((inUse.isNotEmpty() ? inUse + "  " : juce::String()) + (rec.dur > 0 ? juce::String (rec.dur, 2) + " s  " : juce::String()) + fmtBytes (rec.size),
                        subR, juce::Justification::centredRight, true);
        }
        void resized() override
        {
            auto r = getLocalBounds().reduced (4, 3);
            for (int i = btns.size(); --i >= 0;)
            {
                int w = i == btns.size() - 1 ? 44 : (i == btns.size() - 2 ? 46 : (i == btns.size() - 3 ? 36 : (nSlot == 1 ? 50 : 42)));
                btns[i]->setBounds (r.removeFromRight (w)); r.removeFromRight (3);
            }
            subR = r.removeFromRight (190);
            nameR = r.withTrimmedLeft (22);
            if (edit) edit->setBounds (nameR);
        }
        VaultOverlay& ov; ManagerBar::Impl& m; LibRec rec; int idx; int nSlot = 0;
        juce::OwnedArray<PbButton> btns;
        std::unique_ptr<juce::TextEditor> edit;
        juce::String inUse;
        juce::Rectangle<int> nameR, subR;
    };

    juce::Component* VaultOverlay::refreshComponentForRow (int row, bool, juce::Component* existing)
    {
        std::unique_ptr<juce::Component> old (existing);
        if (row < 0 || row >= (int) rows.size()) return nullptr;
        return new VRow (*this, m, rows[(size_t) row], row);
    }
}

// ====================================================================== Impl implementation
ManagerBar::Impl::Impl (ManagerBar& o, Ctx& c, SoundMemory& mem, juce::Component& h)
    : owner (o), ctx (c), memory (mem), host (h), store (c.be.rootFolder())
{
    for (auto* b : { &prev, &nameBtn, &next, &save, &bank, &vault }) owner.addAndMakeVisible (*b);
    prev.onClick = [this] { presetStep (-1); };
    next.onClick = [this] { presetStep (1); };
    nameBtn.onClick = [this] { openBank(); };
    bank.onClick = [this] { openBank(); };
    vault.onClick = [this] { openVault (libKind, -1); };
    save.onClick = [this] { presetQuickSave(); };
    infoTimer.fn = [this] { infoText = {}; owner.repaint(); };
    armTimer.fn = [this] { armed = {}; refreshVault(); refreshBank(); };

    presetOv.reset (new PresetOverlay (*this));
    vaultOv.reset (new VaultOverlay (*this));
    host.addChildComponent (presetOv.get());
    host.addChildComponent (vaultOv.get());
    presetOv->onClose = [this] { closeAll(); };
    vaultOv->onClose = [this] { closeAll(); };
    host.addComponentListener (this);
    layoutOverlays();

    // restore what the project remembered: the current preset name and the vault file of each slot
    auto st = ctx.be.getStored ("njo.preset");
    if (auto* o2 = st.getDynamicObject())
    {
        cur.id = o2->getProperty ("id").toString();
        cur.name = o2->getProperty ("name").toString();
        cur.dirty = (bool) o2->getProperty ("dirty");
        if (cur.name.isEmpty()) cur = {};
    }
    if (auto* so = ctx.be.getStored ("njo.slots").getDynamicObject())
        for (auto& kv : so->getProperties())
            if (kv.value.isString() && findSlot (kv.name.toString())) slotLib[kv.name.toString()] = { kv.value.toString(), {} };
    updateBar();
    presetsRefresh();
    libRefresh();
    memSig = signature();

    ctx.addListener (this);
    memory.addChangeListener (this);
    ctx.onOpenVault = [this] (int kind, int osc) { openVault (kind, osc); };
}

ManagerBar::Impl::~Impl()
{
    *alive = false;
    ctx.onOpenVault = nullptr;
    ctx.removeListener (this);
    memory.removeChangeListener (this);
    host.removeComponentListener (this);
}

void ManagerBar::Impl::layoutOverlays()
{
    if (presetOv) presetOv->setBounds (host.getLocalBounds());
    if (vaultOv) vaultOv->setBounds (host.getLocalBounds());
}

// ---------------------------------------------------------------- bar
void ManagerBar::Impl::barInfo (const juce::String& t)
{
    infoText = t; owner.repaint (infoRect);
    infoTimer.stopTimer();
    if (t.isNotEmpty()) infoTimer.startTimer (4000);
}

void ManagerBar::Impl::updateBar()
{
    nameBtn.setButtonText (cur.name + (cur.dirty ? " *" : ""));
    auto* o = new juce::DynamicObject();
    o->setProperty ("id", cur.id); o->setProperty ("name", cur.name); o->setProperty ("dirty", cur.dirty);
    ctx.be.setStored ("njo.preset", juce::var (o));
}

void ManagerBar::Impl::presetDirty()
{
    if (applying || cur.dirty) return;
    cur.dirty = true;
    updateBar();
    refreshBank();
}

// ---------------------------------------------------------------- presets
void ManagerBar::Impl::presetsRefresh()
{
    presets = store.presetsList();
    if (cur.id.isNotEmpty() && ! findPreset (cur.id)) { cur.id = {}; updateBar(); }
    refreshBank();
}

PresetRec ManagerBar::Impl::collectRec (const juce::String& name)
{
    PresetRec r;
    r.name = name; r.saved = juce::Time::currentTimeMillis();
    for (auto& s : allSpecs()) r.params[s.num] = ctx.get (s.num);
    for (auto& d : slotDefs())
    {
        auto it = slotLib.find (d.key);
        if (it == slotLib.end()) continue;
        if (auto* l = findLib (it->second.id)) r.refs[d.key] = { l->fname, l->size };
    }
    if (ctx.lfoShapes) r.lfo = ctx.lfoShapes->toVar();
    return r;
}

bool ManagerBar::Impl::nameTaken (const juce::String& name, const juce::String& exceptId) const
{
    auto k = safeFile (name).toLowerCase();
    for (auto& p : presets)
        if (p.id != exceptId && (p.name.equalsIgnoreCase (name) || safeFile (p.name).toLowerCase() == k)) return true;
    return false;
}

juce::String ManagerBar::Impl::presetSaveAs (const juce::String& nameIn, const juce::String& id)
{
    auto name = nameIn.trim().substring (0, 40);
    if (name.isEmpty()) { pmStatus ("TYPE A NAME FIRST"); return {}; }
    if (safeFile (name).isEmpty()) { pmStatus ("THAT NAME HAS NO USABLE CHARACTERS"); return {}; }
    if (name.equalsIgnoreCase ("init")) { pmStatus ("'INIT' IS RESERVED"); return {}; }
    if (nameTaken (name, id)) { pmStatus ("NAME ALREADY USED"); return {}; }
    auto newId = store.presetSave (collectRec (name), id);
    if (newId.isEmpty()) { pmStatus ("SAVE FAILED"); return {}; }
    cur = { newId, name, false };
    sel = newId;
    presetsRefresh();
    updateBar();
    pmStatus ("SAVED '" + name + "'");
    barInfo ("SAVED " + name);
    return newId;
}

void ManagerBar::Impl::presetQuickSave()
{
    if (cur.id.isNotEmpty()) presetSaveAs (cur.name, cur.id);
    else
    {
        openBank();
        presetOv->setName ({});
        presetOv->nameIn.grabKeyboardFocus();
        pmStatus ("NAME YOUR PRESET AND PRESS SAVE AS NEW");
    }
}

void ManagerBar::Impl::presetApply (const PresetRec& rec, const juce::String& label)
{
    applying = true;
    for (auto& s : allSpecs())
    {
        auto it = rec.params.find (s.num);
        double v = it != rec.params.end() && std::isfinite (it->second) ? it->second : s.init;
        ctx.set (s.num, (float) v);
    }
    if (ctx.lfoShapes) ctx.lfoShapes->fromVar (rec.lfo);
    ctx.touchAll();
    applying = false;
    cur = { rec.id, label.isNotEmpty() ? label : rec.name, false };
    updateBar();

    // reload the referenced samples / wavetables from the vault
    libRefresh();
    int missing = 0;
    for (auto& d : slotDefs())
    {
        auto ref = rec.refs.find (d.key);
        if (ref == rec.refs.end()) continue;
        const LibRec* item = nullptr;
        for (auto& r : lib) if (r.kind == d.kind && r.fname == ref->second.name && r.size == ref->second.size) { item = &r; break; }
        if (item == nullptr) { ++missing; continue; }
        auto it = slotLib.find (d.key);
        bool have = it != slotLib.end() && it->second.id == item->id && memory.get ((SoundMemory::Kind) d.kind, d.osc) != nullptr;
        if (have) continue;
        ++pendingLoads;
        auto id = item->id, fname = item->fname, key = d.key; int kind = d.kind, osc = d.osc;
        auto a = alive;
        memory.load ((SoundMemory::Kind) kind, osc, store.fileFor (*item), [this, a, id, fname, key, kind, osc] (bool ok, const juce::String&)
        {
            if (! *a) return;
            --pendingLoads;
            if (ok) { auto* s = memory.get ((SoundMemory::Kind) kind, osc); setSlot (key, id, s ? s->name : fname); }
            memSig = signature();
        });
    }
    barInfo ((label.isNotEmpty() ? label : rec.name) + (missing ? " (" + juce::String (missing) + " FILE(S) NOT IN " + NAME_VAULT + ")" : " LOADED"));
    refreshBank();
}

void ManagerBar::Impl::presetInit()
{
    PresetRec r; r.name = "Init";
    for (auto& s : allSpecs()) r.params[s.num] = s.init;
    presetApply (r);
}

void ManagerBar::Impl::presetStep (int dir)
{
    if (presets.empty()) presetsRefresh();
    if (presets.empty()) { barInfo ("NO SAVED PRESETS"); return; }
    int n = (int) presets.size(), i = -1;
    for (int k = 0; k < n; ++k) if (presets[(size_t) k].id == cur.id) i = k;
    i = i < 0 ? (dir > 0 ? 0 : n - 1) : (i + dir + n) % n;
    sel = presets[(size_t) i].id;
    auto rec = presets[(size_t) i];
    presetApply (rec);
}

void ManagerBar::Impl::pmStatus (const juce::String& t) { if (presetOv) presetOv->setStatus (t); }

void ManagerBar::Impl::pmAct (const juce::String& act)
{
    auto name = [this] { return presetOv->name(); };
    if (act == "open-folder") { openFolder (0); return; }
    if (act == "pm-rescan") { presetsRefresh(); pmStatus (juce::String ((int) presets.size()) + " SAVED PRESET(S)"); return; }
    if (act == "pm-new") { presetSaveAs (name(), {}); return; }
    if (act == "pm-over")
    {
        auto* p = selPreset();
        if (! p) { pmStatus ("SELECT A SAVED PRESET FIRST"); return; }
        auto pn = p->name, pid = p->id;
        presetSaveAs (pn, pid);
        return;
    }
    if (act == "pm-ren")
    {
        auto* p = selPreset();
        if (! p) { pmStatus ("SELECT A SAVED PRESET FIRST"); return; }
        auto nn = name().trim().substring (0, 40);
        if (nn.isEmpty() || safeFile (nn).isEmpty()) { pmStatus ("TYPE THE NEW NAME FIRST"); return; }
        if (nn.equalsIgnoreCase ("init") || nameTaken (nn, p->id)) { pmStatus ("NAME ALREADY USED"); return; }
        PresetRec r = *p; r.name = nn;
        auto pid = p->id;
        auto nid = store.presetSave (r, pid);
        if (nid.isEmpty()) { pmStatus ("RENAME FAILED"); return; }
        if (cur.id == pid) cur = { nid, nn, cur.dirty };
        sel = nid;
        presetsRefresh(); updateBar();
        pmStatus ("RENAMED");
        return;
    }
    if (act == "pm-del")
    {
        auto* p = selPreset();
        if (! p) { pmStatus ("SELECT A SAVED PRESET FIRST"); return; }
        if (armed != "pm") { arm ("pm"); refreshBank(); return; }
        armed = {};
        auto pid = p->id, pn = p->name;
        store.presetDelete (pid);
        if (cur.id == pid) cur.id = {};
        sel = {};
        presetsRefresh(); updateBar();
        pmStatus ("DELETED '" + pn + "'");
        return;
    }
    if (act == "pm-load")
    {
        if (sel == "__init") { presetInit(); return; }
        if (auto* p = selPreset()) { auto r = *p; presetApply (r); }
        else pmStatus ("SELECT A PRESET FIRST");
        return;
    }
    if (act == "pm-init") { presetInit(); pmStatus ("INIT SOUND LOADED"); return; }
}

void ManagerBar::Impl::arm (const juce::String& key) { armed = key; armTimer.startTimer (2500); }

void ManagerBar::Impl::openFolder (int what)
{
    auto dir = what == 0 ? store.presetsDir() : store.kindDir (libKind);
    dir.createDirectory();
    bool ok = dir.startAsProcess();
    auto msg = ok ? "OPENED " + dir.getFullPathName() : "COULD NOT OPEN THE FOLDER: " + dir.getFullPathName();
    if (what == 0) pmStatus (msg); else libStatus (msg);
}

// ---------------------------------------------------------------- vault
void ManagerBar::Impl::libRefresh()
{
    lib = store.libList (durCache);
    refreshVault();
}

void ManagerBar::Impl::libStatus (const juce::String& t) { if (vaultOv) { vaultOv->setStatus (t); vaultOv->repaint(); } }

void ManagerBar::Impl::libImport (const juce::Array<juce::File>& files)
{
    int n = 0, bad = 0;
    for (auto& f : files)
    {
        if (! f.existsAsFile() || ! isAudioName (f.getFileName())) { ++bad; continue; }
        bool dup = false;
        auto id = store.libAdd (libKind, f, lib, dup);
        if (id.isEmpty()) { ++bad; continue; }
        if (! dup) { ++n; libRefresh(); }
    }
    libRefresh();
    libStatus ("ADDED " + juce::String (n) + " FILE(S)" + (bad ? ", " + juce::String (bad) + " UNSUPPORTED/FAILED" : juce::String()));
}

void ManagerBar::Impl::setSlot (const juce::String& key, const juce::String& id, const juce::String& name)
{
    slotLib[key] = { id, name };
    saveSlots();
    refreshVault();
}

void ManagerBar::Impl::saveSlots()
{
    if (slotLib.empty()) { ctx.be.setStored ("njo.slots", juce::var()); return; }
    auto* o = new juce::DynamicObject();
    for (auto& kv : slotLib) o->setProperty (juce::Identifier (kv.first), kv.second.id);
    ctx.be.setStored ("njo.slots", juce::var (o));
}

void ManagerBar::Impl::libLoad (const juce::String& id, int osc)
{
    auto* r = findLib (id);
    if (! r || ! store.fileFor (*r).existsAsFile()) { libStatus ("FILE MISSING - PRESS RESCAN"); return; }
    int kind = r->kind;
    auto key = slotKey (kind, osc);
    auto label = r->label, fname = r->fname;
    auto a = alive;
    memory.load ((SoundMemory::Kind) kind, osc, store.fileFor (*r), [this, a, id, key, kind, osc, label, fname] (bool ok, const juce::String& msg)
    {
        if (! *a) return;
        if (ok)
        {
            auto* s = memory.get ((SoundMemory::Kind) kind, osc);
            setSlot (key, id, s ? s->name : fname);
            memSig = signature();
            presetDirty();
            libStatus ("LOADED '" + label + "' INTO " + findSlot (key)->label);
        }
        else libStatus (msg.isNotEmpty() ? msg.toUpperCase() : juce::String ("COULD NOT LOAD THAT FILE"));
    });
}

void ManagerBar::Impl::swapId (const juce::String& oldId, const juce::String& newId)
{
    for (auto& kv : slotLib) if (kv.second.id == oldId) kv.second.id = newId;
    saveSlots();
}

void ManagerBar::Impl::libRenameDone (const juce::String& id, const juce::String* value)
{
    if (renamingId != id) return;
    renamingId = {};
    auto* r = findLib (id);
    if (r && value && value->trim().isNotEmpty() && value->trim() != r->label)
    {
        auto copy = *r; auto nv = value->trim();
        bool clash = false;
        for (auto& x : lib) if (x.id != id && x.kind == copy.kind && safeFile (x.label).equalsIgnoreCase (safeFile (nv))) clash = true;
        if (clash) libStatus ("NAME ALREADY USED");
        else
        {
            auto nid = store.libRename (copy, nv);
            if (nid.isNotEmpty()) { if (nid != id) swapId (id, nid); libRefresh(); libStatus ("RENAMED"); }
            else libStatus ("RENAME FAILED");
        }
    }
    refreshVault();
}

void ManagerBar::Impl::libAct (const juce::String& act, const juce::String& id)
{
    if (act == "lb-rescan") { libRefresh(); libStatus ("RESCANNED"); return; }
    if (act == "lb-ren") { renamingId = id; refreshVault(); return; }
    if (act == "lb-import")
    {
        chooser.reset (new juce::FileChooser ("Add sounds to the " + NAME_VAULT.toLowerCase(), juce::File(), SoundMemory::fileWildcard()));
        auto a = alive;
        chooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles | juce::FileBrowserComponent::canSelectMultipleItems,
                              [this, a] (const juce::FileChooser& fc) { if (*a && fc.getResults().size() > 0) libImport (fc.getResults()); });
        return;
    }
    auto* r = findLib (id);
    if (! r) return;
    auto rec = *r;
    if (act == "lb-kind")
    {
        auto nid = store.libMoveKind (rec);
        if (nid.isEmpty()) { libStatus ("COULD NOT MOVE THE FILE"); return; }
        for (auto it = slotLib.begin(); it != slotLib.end();) { if (it->second.id == id) it = slotLib.erase (it); else ++it; }   // the slot kind no longer matches
        saveSlots();
        libRefresh();
        libStatus ("MOVED TO " + juce::String (rec.kind == 1 ? "WAVETABLES" : "SAMPLES"));
        return;
    }
    if (act == "lb-del")
    {
        if (armed != "lb:" + id) { arm ("lb:" + id); refreshVault(); return; }
        armed = {};
        if (! store.libDelete (rec)) { libStatus ("COULD NOT DELETE THE FILE"); refreshVault(); return; }
        for (auto it = slotLib.begin(); it != slotLib.end();) { if (it->second.id == id) it = slotLib.erase (it); else ++it; }
        saveSlots();
        libRefresh();
        libStatus ("DELETED '" + rec.label + "'");
    }
}

juce::String ManagerBar::Impl::signature() const
{
    juce::String s;
    for (int k = 0; k < 2; ++k)
        for (int o = 0; o < OSC_N; ++o)
        {
            auto* sl = memory.get ((SoundMemory::Kind) k, o);
            s << (sl ? sl->name + ":" + juce::String ((int) sl->data.size()) : juce::String ("-")) << "|";
        }
    return s;
}

void ManagerBar::Impl::reconcileSlots()
{
    bool changed = false;
    for (auto& d : slotDefs())
    {
        auto* s = memory.get ((SoundMemory::Kind) d.kind, d.osc);
        auto it = slotLib.find (d.key);
        if (! s) { if (it != slotLib.end()) { slotLib.erase (it); changed = true; } continue; }
        if (s->libId.isNotEmpty()) { if (it == slotLib.end() || it->second.id != s->libId) { slotLib[d.key] = { s->libId, s->name }; changed = true; } continue; }
        if (it != slotLib.end() && it->second.name == s->name) continue;
        juce::String id;
        for (auto& r : lib)
            if (r.kind == d.kind && (r.fname == s->name || r.label == s->name || stemOf (r.fname) == stemOf (s->name))) { id = r.id; break; }
        if (id.isNotEmpty()) { slotLib[d.key] = { id, s->name }; changed = true; }
        else if (it != slotLib.end()) { slotLib.erase (it); changed = true; }
    }
    if (changed) { saveSlots(); refreshVault(); }
}

void ManagerBar::Impl::changeListenerCallback (juce::ChangeBroadcaster*)
{
    auto sig = signature();
    bool differs = sig != memSig;
    memSig = sig;
    reconcileSlots();
    if (differs && pendingLoads == 0 && ! applying) presetDirty();
}

// ---------------------------------------------------------------- overlays
void ManagerBar::Impl::refreshBank() { if (presetOv && presetOv->isVisible()) presetOv->refresh(); }
void ManagerBar::Impl::refreshVault() { if (vaultOv && vaultOv->isVisible()) vaultOv->refresh(); }

void ManagerBar::Impl::openBank()
{
    vaultOv->setVisible (false);
    armed = {}; renamingId = {};
    sel = cur.id.isNotEmpty() ? cur.id : juce::String ("__init");
    layoutOverlays();
    presetOv->setVisible (true);
    presetOv->toFront (true);
    presetOv->setName (cur.id.isNotEmpty() ? cur.name : juce::String());
    presetsRefresh();
    presetOv->refresh();
    pmStatus (juce::String ((int) presets.size()) + " SAVED PRESET(S)");
    presetOv->grabKeyboardFocus();
}

void ManagerBar::Impl::openVault (int kind, int osc)
{
    presetOv->setVisible (false);
    armed = {}; renamingId = {};
    libKind = kind == 0 ? 0 : 1;
    libTarget = osc >= 0 && osc < OSC_N ? osc : -1;
    layoutOverlays();
    vaultOv->setVisible (true);
    vaultOv->toFront (true);
    vaultOv->search.setText ({}, false);
    libRefresh();
    libStatus ({});
    vaultOv->refresh();
    vaultOv->grabKeyboardFocus();
}

void ManagerBar::Impl::closeAll()
{
    presetOv->setVisible (false);
    vaultOv->setVisible (false);
    armed = {}; renamingId = {};
}

// ====================================================================== ManagerBar
ManagerBar::ManagerBar (Ctx& c, SoundMemory& m, juce::Component& overlayHost) : impl (new Impl (*this, c, m, overlayHost)) {}
ManagerBar::~ManagerBar() = default;

void ManagerBar::paint (juce::Graphics& g)
{
    g.setColour (theme::dim); g.setFont (theme::font (9.0f, true));
    g.drawText ("PRESET", 0, 0, 54, getHeight(), juce::Justification::centredLeft);
    if (impl->infoText.isNotEmpty())
    {
        g.setColour (theme::orange); g.setFont (theme::font (9.5f, true));
        g.drawText (impl->infoText, impl->infoRect, juce::Justification::centredRight, true);
    }
}

void ManagerBar::resized()
{
    auto r = getLocalBounds();
    r.removeFromLeft (56);
    impl->prev.setBounds (r.removeFromLeft (24)); r.removeFromLeft (4);
    impl->nameBtn.setBounds (r.removeFromLeft (210)); r.removeFromLeft (4);
    impl->next.setBounds (r.removeFromLeft (24)); r.removeFromLeft (10);
    impl->save.setBounds (r.removeFromLeft (56)); r.removeFromLeft (4);
    impl->bank.setBounds (r.removeFromLeft (56));
    impl->vault.setBounds (r.removeFromRight (64)); r.removeFromRight (10);
    impl->infoRect = r.withTrimmedLeft (10);
}

void ManagerBar::openBank() { impl->openBank(); }
void ManagerBar::openVault (int kind, int osc) { impl->openVault (kind, osc); }
void ManagerBar::closeOverlays() { impl->closeAll(); }
bool ManagerBar::overlayOpen() const { return impl->presetOv->isVisible() || impl->vaultOv->isVisible(); }
juce::String ManagerBar::presetName() const { return impl->nameBtn.getButtonText(); }
