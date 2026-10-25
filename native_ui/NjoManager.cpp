// The preset bar, the Preset Bank and the Sound Vault (port of MGR_HTML / MGR_OVERLAY_HTML / buildManager of patch/index.js).
// Files: <Backend::rootFolder()>/{Presets,Samples,Wavetables}; the preset file format is shared with the web UI (NjoManagerStore.h).
#include "NjoManager.h"
#include "NjoManagerStore.h"
#include "NjoFolderTree.h"
#include "NjoLfo.h"
#include "NjoFreq.h"

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
    juce::String libFolder = "samples";       // the folder shown in the vault: "samples", "samples/Drums", "wavetables/Pads" ...
    int libTarget = -1;
    int libKind() const { return libFolder.startsWith ("wavetables") ? 0 : 1; }
    juce::String libRel() const { return libFolder.fromFirstOccurrenceOf ("/", false, false); }
    juce::String selFolder;                   // the folder of the Preset Bank that "save as new" writes to ("" = root)
    std::map<juce::String, std::vector<juce::String>> folderCache;   // area -> relative folders (also the empty ones)
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
    PresetRec collectRec (const juce::String& name, const juce::String& folder);
    bool nameTaken (const juce::String& name, const juce::String& exceptId, const juce::String& folder) const;
    juce::String presetSaveAs (const juce::String& name, const juce::String& id, const juce::String& folder);
    void presetQuickSave();
    void presetApply (const PresetRec& rec, const juce::String& label = {});
    void presetInit();
    void presetStep (int dir);
    const PresetRec* findPreset (const juce::String& id) const { for (auto& p : presets) if (p.id == id) return &p; return nullptr; }
    const PresetRec* selPreset() const { return findPreset (sel); }
    void pmAct (const juce::String& act);
    void pmStatus (const juce::String& t);
    juce::String presetFolderPath() const { return selFolder.isEmpty() ? juce::String ("presets") : "presets/" + selFolder; }
    std::vector<FolderTree::Node> presetNodes() const;
    void pmMove (const juce::String& id, const juce::String& destRel);
    void pmTreeSelect (const FolderTree::Node& n);
    // folders (shared by both overlays; vaultSide: the folder is a vault folder, else a preset folder)
    juce::String currentFolderPath (bool vaultSide) const { return vaultSide ? libFolder : presetFolderPath(); }
    void folderAct (bool vaultSide, const juce::String& act, const juce::String& name);
    void folderStatus (bool vaultSide, const juce::String& t) { if (vaultSide) libStatus (t); else pmStatus (t); }
    void foldersRefresh();
    void addFolderMenu (juce::PopupMenu&, const std::vector<juce::String>&, const juce::String& area, const juce::String& rel, const juce::String& label,
                        std::map<int, juce::String>& ids, int& nextId) const;
    void showMoveMenu (bool vaultSide, const juce::String& id, juce::Component* anchor);
    void showFolderMenu (bool vaultSide, const FolderTree::Node& n);
    void libMoveTo (const juce::String& id, const juce::String& destPath);
    std::vector<FolderTree::Node> vaultNodes() const;
    void setLibFolder (const juce::String& path);
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
    void openFolder (int what);       // 0 presets, 1 vault (the selected folder)
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
    // a small "name" + "v" dropdown button text
    const juce::String DOWN = juce::String::fromUTF8 (" \xe2\x96\xbe");

    // ================================================================== Preset Bank overlay
    class PresetOverlay : public OverlayBase
    {
    public:
        explicit PresetOverlay (ManagerBar::Impl& im)
            : OverlayBase (NAME_BANK, 900, 620), m (im),
              bNew ("SAVE AS NEW"), bOver ("OVERWRITE"), bRen ("RENAME"), bDel ("DELETE"),
              bLoad ("LOAD"), bInit ("INIT SOUND"), bFolder ("OPEN FOLDER"), bRescan ("RESCAN"),
              fNew ("NEW FOLDER"), fRen ("REN FOLDER"), fDel ("DEL FOLDER"), bMove ("MOVE TO" + DOWN)
        {
            styleEditor (nameIn, "Name (preset or folder)", 40);
            for (auto* c : std::initializer_list<juce::Component*> { &nameIn, &tree, &bNew, &bOver, &bRen, &bDel, &bLoad, &bInit, &bFolder, &bRescan, &fNew, &fRen, &fDel, &bMove })
                addAndMakeVisible (c);
            nameIn.onEscapeKey = [this] { if (onClose) onClose(); };
            nameIn.onReturnKey = [this] { m.pmAct ("pm-new"); };
            bNew.onClick = [this] { m.pmAct ("pm-new"); };     bOver.onClick = [this] { m.pmAct ("pm-over"); };
            bRen.onClick = [this] { m.pmAct ("pm-ren"); };     bDel.onClick = [this] { m.pmAct ("pm-del"); };
            bLoad.onClick = [this] { m.pmAct ("pm-load"); };   bInit.onClick = [this] { m.pmAct ("pm-init"); };
            bFolder.onClick = [this] { m.pmAct ("open-folder"); };  bRescan.onClick = [this] { m.pmAct ("pm-rescan"); };
            fNew.onClick = [this] { m.folderAct (false, "new", name()); };
            fRen.onClick = [this] { m.folderAct (false, "ren", name()); };
            fDel.onClick = [this] { m.folderAct (false, "del", name()); };
            bMove.onClick = [this] { m.showMoveMenu (false, m.sel, &bMove); };

            tree.onSelect = [this] (const FolderTree::Node& n) { m.pmTreeSelect (n); };
            tree.onActivate = [this] (const FolderTree::Node&) { m.defer ([this] { m.pmAct ("pm-load"); }); };
            tree.onContext = [this] (const FolderTree::Node& n) { m.defer ([this, n] { m.showFolderMenu (false, n); }); };
            tree.acceptsDrag = [] (const juce::String& d) { return d.startsWith ("pre:"); };
            tree.onDropOnFolder = [this] (const juce::String& d, const FolderTree::Node& n)
            {
                auto id = d.fromFirstOccurrenceOf ("pre:", false, false);
                auto rel = n.path.fromFirstOccurrenceOf ("/", false, false);
                m.defer ([this, id, rel] { m.pmMove (id, rel); });
            };
            tree.dragDescription = [] (const FolderTree::Node& n)
            {
                return n.path.startsWith ("p:") && n.path != "p:__init" ? "pre:" + n.path.substring (2) : juce::String();
            };
        }

        void setStatus (const juce::String& s) { status = s; repaint (statusR); }

        bool reveal = false;   // the next refresh opens the folders above the selection
        void refresh()
        {
            tree.setRoots (m.presetNodes(), m.sel.isNotEmpty() ? "p:" + m.sel : m.presetFolderPath(), reveal);
            reveal = false;
            updateLabels();
            bDel.armed = m.armed == "pm"; bDel.setButtonText (bDel.armed ? "SURE?" : "DELETE"); bDel.repaint();
            fDel.armed = m.armed == "fd"; fDel.setButtonText (fDel.armed ? "SURE?" : "DEL FOLDER"); fDel.repaint();
        }
        void updateLabels()
        {
            path = "FOLDER  " + m.store.dirOf (m.presetFolderPath()).getFullPathName();
            into = "SAVE INTO  " + m.presetFolderPath().toUpperCase();
            repaint();
        }
        void setName (const juce::String& s) { nameIn.setText (s, false); }
        juce::String name() const { return nameIn.getText(); }

        void layoutBody (juce::Rectangle<int> r) override
        {
            auto top = r.removeFromTop (28);
            bDel.setBounds (top.removeFromRight (72)); top.removeFromRight (6);
            bRen.setBounds (top.removeFromRight (72)); top.removeFromRight (6);
            bOver.setBounds (top.removeFromRight (88)); top.removeFromRight (6);
            bNew.setBounds (top.removeFromRight (104)); top.removeFromRight (8);
            nameIn.setBounds (top);
            r.removeFromTop (6);
            auto row2 = r.removeFromTop (26);
            bMove.setBounds (row2.removeFromRight (96)); row2.removeFromRight (6);
            fDel.setBounds (row2.removeFromRight (92)); row2.removeFromRight (6);
            fRen.setBounds (row2.removeFromRight (92)); row2.removeFromRight (6);
            fNew.setBounds (row2.removeFromRight (92));
            intoR = row2.withTrimmedRight (8);
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
            tree.setBounds (r);
        }
        void paint (juce::Graphics& g) override
        {
            OverlayBase::paint (g);
            drawLine (g, into, intoR, theme::red);
            drawLine (g, path, pathR, theme::dim, true);
            drawLine (g, status, statusR, theme::orange);
        }

        ManagerBar::Impl& m;
        FolderTree tree;
        juce::TextEditor nameIn;
        PbButton bNew, bOver, bRen, bDel, bLoad, bInit, bFolder, bRescan, fNew, fRen, fDel, bMove;
        juce::String status, path, into;
        juce::Rectangle<int> statusR, pathR, intoR;
    };

    // ================================================================== Sound Vault overlay
    class VaultOverlay : public OverlayBase, public juce::ListBoxModel, public juce::FileDragAndDropTarget
    {
    public:
        explicit VaultOverlay (ManagerBar::Impl& im)
            : OverlayBase (NAME_VAULT, 1000, 620), m (im), list ("vault", this),
              bAdd ("ADD FILES"), bFolder ("OPEN FOLDER"), bRescan ("RESCAN"), fNew ("NEW"), fRen ("RENAME"), fDel ("DELETE")
        {
            styleEditor (search, "Search this folder and below", 0);
            styleEditor (folderName, "Folder name (for NEW / RENAME)", 60);
            for (auto* c : std::initializer_list<juce::Component*> { &search, &folderName, &tree, &list, &bAdd, &bFolder, &bRescan, &fNew, &fRen, &fDel })
                addAndMakeVisible (c);
            styleList (list); list.setRowHeight (28);
            search.onTextChange = [this] { refresh(); };
            search.onEscapeKey = [this] { if (onClose) onClose(); };
            folderName.onReturnKey = [this] { m.folderAct (true, "new", folderName.getText()); };
            folderName.onEscapeKey = [this] { if (onClose) onClose(); };
            bAdd.onClick = [this] { m.libAct ("lb-import", {}); };
            bFolder.onClick = [this] { m.openFolder (1); };
            bRescan.onClick = [this] { m.libAct ("lb-rescan", {}); };
            fNew.onClick = [this] { m.folderAct (true, "new", folderName.getText()); };
            fRen.onClick = [this] { m.folderAct (true, "ren", folderName.getText()); };
            fDel.onClick = [this] { m.folderAct (true, "del", folderName.getText()); };

            tree.onSelect = [this] (const FolderTree::Node& n) { m.setLibFolder (n.path); };
            tree.onContext = [this] (const FolderTree::Node& n) { m.defer ([this, n] { m.showFolderMenu (true, n); }); };
            tree.acceptsDrag = [] (const juce::String& d) { return d.startsWith ("lib:"); };
            tree.onDropOnFolder = [this] (const juce::String& d, const FolderTree::Node& n)
            {
                auto id = d.fromFirstOccurrenceOf ("lib:", false, false), dest = n.path;
                m.defer ([this, id, dest] { m.libMoveTo (id, dest); });
            };
        }

        void setStatus (const juce::String& s) { msg = s; repaint (statusR); }
        bool reveal = false;
        void refresh()
        {
            auto term = search.getText().trim().toLowerCase();
            auto rel = m.libRel();
            rows.clear();
            searching = term.isNotEmpty();
            for (auto& r : m.lib)
            {
                if (r.kind != m.libKind()) continue;
                if (searching)
                {
                    bool inside = rel.isEmpty() || r.folder == rel || r.folder.startsWith (rel + "/");
                    if (inside && (r.label.toLowerCase().contains (term) || r.fname.toLowerCase().contains (term) || r.folder.toLowerCase().contains (term))) rows.push_back (r);
                }
                else if (r.folder == rel) rows.push_back (r);
            }
            tree.setRoots (m.vaultNodes(), m.libFolder, reveal);
            reveal = false;
            path = "FOLDER  " + m.store.dirOf (m.libFolder).getFullPathName();
            if (m.libTarget >= 0)
                target = "LOADING INTO: " + findSlot (slotKey (m.libKind(), m.libTarget))->label;
            else target = "CHOOSE A TARGET BUTTON ON EACH ROW  |  DRAG A ROW ONTO A FOLDER TO MOVE IT";
            fDel.armed = m.armed == "fd"; fDel.setButtonText (fDel.armed ? "SURE?" : "DELETE"); fDel.repaint();
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
                g.drawFittedText (searching ? "NOTHING MATCHES" : (m.lib.empty() ? "EMPTY - ADD FILES, DROP THEM HERE, OR LOAD ONE INTO AN OSCILLATOR AND IT APPEARS HERE"
                                                                                : "THIS FOLDER HAS NO FILES - ADD FILES, DROP THEM HERE OR DRAG FILES IN FROM ANOTHER FOLDER"),
                                  list.getBounds().reduced (30), juce::Justification::centred, 3);
            }
            if (dropHover)
            {
                g.setColour (theme::red); g.drawRect (box().reduced (6), 2);
                g.setColour (theme::red.withAlpha (0.12f)); g.fillRect (box().reduced (6));
                g.setColour (juce::Colours::white); g.setFont (theme::impact (20.0f));
                g.drawText ("DROP FILES TO ADD THEM TO  " + m.libFolder.toUpperCase(), box(), juce::Justification::centred);
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
            bRescan.setBounds (top.removeFromRight (80)); top.removeFromRight (6);
            bFolder.setBounds (top.removeFromRight (110)); top.removeFromRight (6);
            bAdd.setBounds (top.removeFromRight (90)); top.removeFromRight (10);
            search.setBounds (top);
            r.removeFromTop (6);
            targetR = r.removeFromTop (16); r.removeFromTop (4);
            statusR = r.removeFromBottom (18);
            pathR = r.removeFromBottom (16);
            r.removeFromBottom (4);
            auto left = r.removeFromLeft (240);
            r.removeFromLeft (8);
            folderName.setBounds (left.removeFromTop (26)); left.removeFromTop (4);
            auto fb = left.removeFromTop (26);
            const int bw = (fb.getWidth() - 8) / 3;
            fNew.setBounds (fb.removeFromLeft (bw)); fb.removeFromLeft (4);
            fRen.setBounds (fb.removeFromLeft (bw)); fb.removeFromLeft (4);
            fDel.setBounds (fb);
            left.removeFromTop (6);
            tree.setBounds (left);
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
        FolderTree tree;
        std::vector<LibRec> rows;
        juce::ListBox list;
        juce::TextEditor search, folderName;
        PbButton bAdd, bFolder, bRescan, fNew, fRen, fDel;
        juce::String msg, path, target;
        juce::Rectangle<int> statusR, pathR, targetR;
        bool dropHover = false, searching = false;
    };

    class VRow : public juce::Component
    {
    public:
        VRow (VaultOverlay& o, ManagerBar::Impl& im, const LibRec& r, int index, bool showFolder) : ov (o), m (im), rec (r), idx (index), withFolder (showFolder)
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
            auto& mv = add ("MOVE" + DOWN);
            mv.onClick = [mp, id, b = &mv] { mp->defer ([mp, id, b] { mp->showMoveMenu (true, id, b); }); };
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
        void mouseDrag (const juce::MouseEvent& e) override
        {
            if (edit || e.getDistanceFromDragStart() < 6) return;
            if (auto* dc = juce::DragAndDropContainer::findParentDragContainerFor (this))
                if (! dc->isDragAndDropActive())
                {
                    juce::Image img (juce::Image::ARGB, juce::jmax (1, getWidth() / 2), getHeight(), true);
                    {
                        juce::Graphics g (img);
                        g.setColour (theme::redDark.withAlpha (0.8f)); g.fillRoundedRectangle (img.getBounds().toFloat(), 4.0f);
                        g.setColour (juce::Colours::white); g.setFont (theme::font (11.0f, true));
                        g.drawText (rec.label, img.getBounds().reduced (8, 0), juce::Justification::centredLeft, true);
                    }
                    dc->startDragging ("lib:" + rec.id, this, juce::ScaledImage (img), true);
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
                auto fnt = theme::font (11.0f, true);
                g.setFont (fnt);
                auto nr = nameR;
                if (withFolder && rec.folder.isNotEmpty())
                {
                    auto pre = rec.folder + " / ";
                    int pw = juce::jmin ((int) folderTextWidth (fnt, pre), nr.getWidth() / 2);
                    g.setColour (theme::dim);
                    g.drawText (pre, nr.removeFromLeft (pw), juce::Justification::centredLeft, true);
                }
                g.setColour (theme::ink);
                g.drawText (rec.label, nr, juce::Justification::centredLeft, true);
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
                int w = i == btns.size() - 1 ? 40 : (i == btns.size() - 2 ? 56 : (i == btns.size() - 3 ? 34 : (nSlot == 1 ? 50 : 40)));
                btns[i]->setBounds (r.removeFromRight (w)); r.removeFromRight (3);
            }
            subR = r.removeFromRight (150);
            nameR = r.withTrimmedLeft (22);
            if (edit) edit->setBounds (nameR);
        }
        VaultOverlay& ov; ManagerBar::Impl& m; LibRec rec; int idx; int nSlot = 0; bool withFolder = false;
        juce::OwnedArray<PbButton> btns;
        std::unique_ptr<juce::TextEditor> edit;
        juce::String inUse;
        juce::Rectangle<int> nameR, subR;
    };

    juce::Component* VaultOverlay::refreshComponentForRow (int row, bool, juce::Component* existing)
    {
        std::unique_ptr<juce::Component> old (existing);
        if (row < 0 || row >= (int) rows.size()) return nullptr;
        return new VRow (*this, m, rows[(size_t) row], row, searching);
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
    vault.onClick = [this] { openVault (libKind(), -1); };
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
    foldersRefresh();
    if (sel.isNotEmpty() && sel != "__init" && ! findPreset (sel)) sel = {};
    if (cur.id.isNotEmpty() && ! findPreset (cur.id)) { cur.id = {}; updateBar(); }
    refreshBank();
}

PresetRec ManagerBar::Impl::collectRec (const juce::String& name, const juce::String& folder)
{
    PresetRec r;
    r.name = name; r.folder = folder; r.saved = juce::Time::currentTimeMillis();
    for (auto& s : allSpecs()) r.params[s.num] = ctx.get (s.num);
    for (auto& d : slotDefs())
    {
        auto it = slotLib.find (d.key);
        if (it == slotLib.end()) continue;
        if (auto* l = findLib (it->second.id)) r.refs[d.key] = { l->fname, l->size, l->folder };
    }
    if (ctx.lfoShapes) r.lfo = ctx.lfoShapes->toVar();
    if (ctx.freqShapes) r.frq = ctx.freqShapes->toVar();
    return r;
}

bool ManagerBar::Impl::nameTaken (const juce::String& name, const juce::String& exceptId, const juce::String& folder) const
{
    auto k = safeFile (name).toLowerCase();
    for (auto& p : presets)
        if (p.id != exceptId && p.folder == folder && (p.name.equalsIgnoreCase (name) || safeFile (p.name).toLowerCase() == k)) return true;
    return false;
}

juce::String ManagerBar::Impl::presetSaveAs (const juce::String& nameIn, const juce::String& id, const juce::String& folder)
{
    auto name = nameIn.trim().substring (0, 40);
    if (name.isEmpty()) { pmStatus ("TYPE A NAME FIRST"); return {}; }
    if (safeFile (name).isEmpty()) { pmStatus ("THAT NAME HAS NO USABLE CHARACTERS"); return {}; }
    if (name.equalsIgnoreCase ("init")) { pmStatus ("'INIT' IS RESERVED"); return {}; }
    if (nameTaken (name, id, folder)) { pmStatus ("NAME ALREADY USED IN THIS FOLDER"); return {}; }
    auto newId = store.presetSave (collectRec (name, folder), id);
    if (newId.isEmpty()) { pmStatus ("SAVE FAILED"); return {}; }
    cur = { newId, name, false };
    sel = newId; selFolder = folder;
    if (presetOv) presetOv->reveal = true;
    presetsRefresh();
    updateBar();
    pmStatus ("SAVED '" + name + "'");
    barInfo ("SAVED " + name);
    return newId;
}

void ManagerBar::Impl::presetQuickSave()
{
    if (cur.id.isNotEmpty()) presetSaveAs (cur.name, cur.id, parentRel (cur.id));
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
    if (ctx.freqShapes) ctx.freqShapes->fromVar (rec.frq);
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
        for (auto& r : lib) if (r.kind == d.kind && r.fname == ref->second.name && r.size == ref->second.size && r.folder == ref->second.folder) { item = &r; break; }
        if (item == nullptr)   // the file was moved to another folder: the name and size still find it
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
    if (act == "pm-new") { presetSaveAs (name(), {}, selFolder); return; }
    if (act == "pm-over")
    {
        auto* p = selPreset();
        if (! p) { pmStatus ("SELECT A SAVED PRESET FIRST"); return; }
        auto pn = p->name, pid = p->id;
        presetSaveAs (pn, pid, p->folder);
        return;
    }
    if (act == "pm-ren")
    {
        auto* p = selPreset();
        if (! p) { pmStatus ("SELECT A SAVED PRESET FIRST"); return; }
        auto nn = name().trim().substring (0, 40);
        if (nn.isEmpty() || safeFile (nn).isEmpty()) { pmStatus ("TYPE THE NEW NAME FIRST"); return; }
        if (nn.equalsIgnoreCase ("init") || nameTaken (nn, p->id, p->folder)) { pmStatus ("NAME ALREADY USED IN THIS FOLDER"); return; }
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
    auto dir = store.dirOf (what == 0 ? presetFolderPath() : libFolder);
    if (dir == juce::File()) return;
    dir.createDirectory();
    bool ok = dir.startAsProcess();
    auto msg = ok ? "OPENED " + dir.getFullPathName() : "COULD NOT OPEN THE FOLDER: " + dir.getFullPathName();
    if (what == 0) pmStatus (msg); else libStatus (msg);
}

// ---------------------------------------------------------------- vault
void ManagerBar::Impl::libRefresh()
{
    lib = store.libList (durCache);
    foldersRefresh();
    if (libFolder.contains ("/"))   // the selected folder was removed outside the plugin
    {
        auto& fl = folderCache[libFolder.upToFirstOccurrenceOf ("/", false, false)];
        if (std::find (fl.begin(), fl.end(), libRel()) == fl.end()) libFolder = libFolder.upToFirstOccurrenceOf ("/", false, false);
    }
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
        auto id = store.libAdd (libKind(), libRel(), f, lib, dup);
        if (id.isEmpty()) { ++bad; continue; }
        if (! dup) { ++n; libRefresh(); }
    }
    libRefresh();
    libStatus ("ADDED " + juce::String (n) + " FILE(S) TO " + libFolder.toUpperCase() + (bad ? ", " + juce::String (bad) + " UNSUPPORTED/FAILED" : juce::String()));
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
    memory.relabel (oldId, newId);
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
        for (auto& x : lib) if (x.id != id && x.kind == copy.kind && x.folder == copy.folder && safeFile (x.label).equalsIgnoreCase (safeFile (nv))) clash = true;
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


// ---------------------------------------------------------------- folders (tree, menus, actions)
namespace
{
    juce::String remapPrefix (const juce::String& s, const juce::String& oldP, const juce::String& newP)
    {
        if (s == oldP) return newP;
        if (s.startsWith (oldP + "/")) return newP + s.substring (oldP.length());
        return s;
    }
    bool underFolder (const juce::String& rel, const juce::String& folder)   // rel inside (or equal to) folder; folder "" = everything
    {
        return folder.isEmpty() || rel == folder || rel.startsWith (folder + "/");
    }
}

void ManagerBar::Impl::foldersRefresh()
{
    for (auto* a : { "presets", "samples", "wavetables" }) folderCache[a] = store.folders (a);
}

std::vector<FolderTree::Node> ManagerBar::Impl::presetNodes() const
{
    static const std::vector<juce::String> none;
    auto itF = folderCache.find ("presets");
    auto& flist = itF != folderCache.end() ? itF->second : none;
    std::function<FolderTree::Node (const juce::String&)> build = [&] (const juce::String& rel)
    {
        FolderTree::Node n;
        n.folder = true; n.path = rel.isEmpty() ? juce::String ("presets") : "presets/" + rel;
        n.label = rel.isEmpty() ? juce::String ("ALL PRESETS") : leafRel (rel);
        if (rel.isEmpty())
        {
            FolderTree::Node init; init.folder = false; init.path = "p:__init"; init.label = "Init"; init.sub = "factory";
            init.current = cur.id.isEmpty() && cur.name == "Init";
            n.kids.push_back (init);
        }
        for (auto& f : flist) if (parentRel (f) == rel) n.kids.push_back (build (f));
        int cnt = 0;
        for (auto& p : presets)
        {
            if (underFolder (p.folder, rel)) ++cnt;
            if (p.folder != rel) continue;
            FolderTree::Node l; l.folder = false; l.path = "p:" + p.id; l.label = p.name;
            l.sub = juce::Time (p.saved).toString (true, false); l.current = p.id == cur.id;
            n.kids.push_back (l);
        }
        n.count = cnt;
        return n;
    };
    return { build ({}) };
}

std::vector<FolderTree::Node> ManagerBar::Impl::vaultNodes() const
{
    static const std::vector<juce::String> none;
    std::vector<FolderTree::Node> roots;
    for (auto* area : { "samples", "wavetables" })
    {
        auto itF = folderCache.find (area);
        auto& flist = itF != folderCache.end() ? itF->second : none;
        int kind = juce::String (area) == "wavetables" ? 0 : 1;
        std::function<FolderTree::Node (const juce::String&)> build = [&] (const juce::String& rel)
        {
            FolderTree::Node n;
            n.folder = true; n.path = rel.isEmpty() ? juce::String (area) : juce::String (area) + "/" + rel;
            n.label = rel.isEmpty() ? juce::String (kind == 1 ? "SAMPLES" : "WAVETABLES") : leafRel (rel);
            for (auto& f : flist) if (parentRel (f) == rel) n.kids.push_back (build (f));
            int cnt = 0;
            for (auto& r : lib) if (r.kind == kind && underFolder (r.folder, rel)) ++cnt;
            n.count = cnt;
            return n;
        };
        roots.push_back (build ({}));
    }
    return roots;
}

void ManagerBar::Impl::setLibFolder (const juce::String& path)
{
    if (path == libFolder) return;
    libFolder = path; renamingId = {};
    if (vaultOv && vaultOv->isVisible()) { vaultOv->refresh(); }
}

void ManagerBar::Impl::pmTreeSelect (const FolderTree::Node& n)
{
    armed = {};
    if (n.folder)
    {
        selFolder = n.path.fromFirstOccurrenceOf ("/", false, false);
        sel = {};
    }
    else
    {
        sel = n.path.substring (2);
        selFolder = sel == "__init" ? juce::String() : parentRel (sel);
        auto* p = selPreset();
        presetOv->setName (p ? p->name : juce::String());
    }
    presetOv->updateLabels();
}

void ManagerBar::Impl::pmMove (const juce::String& id, const juce::String& destRel)
{
    auto* p = findPreset (id);
    if (! p) { pmStatus ("SELECT A SAVED PRESET FIRST"); return; }
    if (p->folder == destRel) { pmStatus ("ALREADY IN THAT FOLDER"); return; }
    auto rec = *p;
    auto nid = store.presetMove (rec, destRel);
    if (nid.isEmpty()) { pmStatus ("COULD NOT MOVE (A PRESET WITH THAT FILE NAME EXISTS THERE?)"); return; }
    if (cur.id == id) cur.id = nid;
    sel = nid; selFolder = destRel;
    presetOv->reveal = true;
    presetsRefresh(); updateBar();
    pmStatus ("MOVED '" + rec.name + "' TO " + (destRel.isEmpty() ? juce::String ("THE ROOT FOLDER") : destRel.toUpperCase()));
}

void ManagerBar::Impl::addFolderMenu (juce::PopupMenu& menu, const std::vector<juce::String>& flist, const juce::String& area, const juce::String& rel,
                                      const juce::String& label, std::map<int, juce::String>& ids, int& nextId) const
{
    auto pathOf = [&] (const juce::String& r) { return r.isEmpty() ? area : area + "/" + r; };
    int id = nextId++; ids[id] = pathOf (rel);
    menu.addItem (id, rel.isEmpty() ? label : "[ " + label + " ]");
    bool any = false;
    for (auto& f : flist)
    {
        if (parentRel (f) != rel) continue;
        if (! any) { menu.addSeparator(); any = true; }
        bool hasKids = false;
        for (auto& g : flist) if (parentRel (g) == f) hasKids = true;
        if (hasKids)
        {
            juce::PopupMenu sub;
            addFolderMenu (sub, flist, area, f, leafRel (f), ids, nextId);
            menu.addSubMenu (leafRel (f), sub);
        }
        else { int cid = nextId++; ids[cid] = pathOf (f); menu.addItem (cid, leafRel (f)); }
    }
}

void ManagerBar::Impl::showMoveMenu (bool vaultSide, const juce::String& id, juce::Component* anchor)
{
    if (id.isEmpty() || id == "__init") { folderStatus (vaultSide, vaultSide ? "NOTHING TO MOVE" : "SELECT A SAVED PRESET FIRST"); return; }
    if (! vaultSide && ! findPreset (id)) { pmStatus ("SELECT A SAVED PRESET FIRST"); return; }
    if (vaultSide && ! findLib (id)) return;
    auto ids = std::make_shared<std::map<int, juce::String>>();
    int next = 1;
    juce::PopupMenu menu;
    menu.addSectionHeader (vaultSide ? "MOVE TO FOLDER" : "MOVE PRESET TO FOLDER");
    if (vaultSide)
    {
        for (auto* area : { "samples", "wavetables" })
        {
            juce::PopupMenu sub;
            addFolderMenu (sub, folderCache[area], area, {}, juce::String (area) == "samples" ? "SAMPLES" : "WAVETABLES", *ids, next);
            menu.addSubMenu (juce::String (area) == "samples" ? "Samples" : "Wavetables", sub);
        }
    }
    else addFolderMenu (menu, folderCache["presets"], "presets", {}, "ALL PRESETS (ROOT)", *ids, next);
    auto a = alive;
    menu.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (anchor).withMinimumWidth (160), [this, a, ids, id, vaultSide] (int r)
    {
        if (! *a || r <= 0 || ids->find (r) == ids->end()) return;
        auto dest = (*ids)[r];
        if (vaultSide) libMoveTo (id, dest);
        else pmMove (id, dest.fromFirstOccurrenceOf ("/", false, false));
    });
}

void ManagerBar::Impl::showFolderMenu (bool vaultSide, const FolderTree::Node& n)
{
    juce::PopupMenu m;
    bool isRoot = n.folder && ! n.path.contains ("/");
    auto nameOf = [this, vaultSide] { return vaultSide ? vaultOv->folderName.getText() : presetOv->name(); };
    if (n.folder)
    {
        m.addItem (1, "New folder inside");
        m.addItem (2, "Rename to the name field", ! isRoot);
        m.addItem (3, "Delete folder and its files", ! isRoot);
        m.addSeparator();
        m.addItem (4, "Open in the file manager");
    }
    else
    {
        m.addItem (5, "Load");
        m.addItem (6, "Delete preset", n.path != "p:__init");
        m.addSeparator();
        m.addItem (7, "Open folder in the file manager");
    }
    auto a = alive;
    m.showMenuAsync (juce::PopupMenu::Options(), [this, a, vaultSide, nameOf] (int r)
    {
        if (! *a || r <= 0) return;
        if (r == 1) folderAct (vaultSide, "new", nameOf());
        else if (r == 2) folderAct (vaultSide, "ren", nameOf());
        else if (r == 3) { armed = "fd"; folderAct (vaultSide, "del", nameOf()); }
        else if (r == 4 || r == 7) openFolder (vaultSide ? 1 : 0);
        else if (r == 5) pmAct ("pm-load");
        else if (r == 6) { armed = "pm"; pmAct ("pm-del"); }
    });
}

void ManagerBar::Impl::folderAct (bool vaultSide, const juce::String& act, const juce::String& nameIn)
{
    auto path = currentFolderPath (vaultSide);
    if (presetOv) presetOv->reveal = true;
    if (vaultOv) vaultOv->reveal = true;
    auto status = [this, vaultSide] (const juce::String& t) { folderStatus (vaultSide, t); };
    auto refreshAll = [this, vaultSide]
    {
        if (vaultSide) libRefresh(); else presetsRefresh();
    };
    if (act == "new")
    {
        auto nm = nameIn.trim().isEmpty() ? juce::String ("New folder") : nameIn.trim();
        auto np = store.folderCreate (path, nm);
        if (np.isEmpty()) { status ("COULD NOT CREATE THE FOLDER (NAME ALREADY USED?)"); return; }
        if (vaultSide) { libFolder = np; } else { selFolder = np.fromFirstOccurrenceOf ("/", false, false); sel = {}; }
        refreshAll();
        status ("CREATED " + np.toUpperCase());
        return;
    }
    if (! path.contains ("/")) { status ("SELECT A SUB FOLDER FIRST"); return; }
    if (act == "ren")
    {
        auto nm = nameIn.trim();
        if (nm.isEmpty() || safeFile (nm).isEmpty()) { status ("TYPE THE NEW FOLDER NAME FIRST"); return; }
        auto np = store.folderRename (path, nm);
        if (np.isEmpty()) { status ("RENAME FAILED (NAME ALREADY USED?)"); return; }
        if (vaultSide)
        {
            for (auto& kv : slotLib) kv.second.id = remapPrefix (kv.second.id, path, np);
            memory.relabel (path, np);
            libFolder = remapPrefix (libFolder, path, np);
            saveSlots();
        }
        else
        {
            auto o = path.fromFirstOccurrenceOf ("/", false, false), n2 = np.fromFirstOccurrenceOf ("/", false, false);
            cur.id = remapPrefix (cur.id, o, n2); sel = remapPrefix (sel, o, n2); selFolder = remapPrefix (selFolder, o, n2);
            updateBar();
        }
        refreshAll();
        status ("RENAMED TO " + np.toUpperCase());
        return;
    }
    if (act == "del")
    {
        int files = store.folderFileCount (path);
        if (armed != "fd")
        {
            arm ("fd");
            status ("PRESS AGAIN TO DELETE " + path.toUpperCase() + " AND " + juce::String (files) + " FILE(S)");
            refreshVault(); refreshBank();
            return;
        }
        armed = {};
        if (! store.folderDelete (path)) { status ("COULD NOT DELETE THE FOLDER"); refreshVault(); refreshBank(); return; }
        auto parent = path.contains ("/") ? path.upToLastOccurrenceOf ("/", false, false) : path;
        if (vaultSide)
        {
            for (auto it = slotLib.begin(); it != slotLib.end();) { if (it->second.id.startsWith (path + "/")) it = slotLib.erase (it); else ++it; }
            libFolder = parent;
            saveSlots();
        }
        else
        {
            auto rel = path.fromFirstOccurrenceOf ("/", false, false);
            if (cur.id.startsWith (rel + "/")) { cur.id = {}; updateBar(); }
            selFolder = parent.fromFirstOccurrenceOf ("/", false, false); sel = {};
        }
        refreshAll();
        status ("DELETED " + path.toUpperCase());
    }
}

void ManagerBar::Impl::libMoveTo (const juce::String& id, const juce::String& destPath)
{
    auto* r = findLib (id);
    if (! r) return;
    auto rec = *r;
    if (destPath.startsWith ("presets")) return;
    auto nid = store.libMove (rec, destPath);
    if (nid.isEmpty()) { libStatus ("COULD NOT MOVE THE FILE"); return; }
    if (nid == id) { libStatus ("ALREADY IN THAT FOLDER"); return; }
    bool kindChanged = (destPath.startsWith ("wavetables") ? 0 : 1) != rec.kind;
    if (kindChanged)
    {
        for (auto it = slotLib.begin(); it != slotLib.end();) { if (it->second.id == id) it = slotLib.erase (it); else ++it; }   // the slot kind no longer matches
        saveSlots();
    }
    else swapId (id, nid);
    libRefresh();
    libStatus ("MOVED '" + rec.label + "' TO " + destPath.toUpperCase());
}

// ---------------------------------------------------------------- overlays
void ManagerBar::Impl::refreshBank() { if (presetOv && presetOv->isVisible()) presetOv->refresh(); }
void ManagerBar::Impl::refreshVault() { if (vaultOv && vaultOv->isVisible()) vaultOv->refresh(); }

void ManagerBar::Impl::openBank()
{
    vaultOv->setVisible (false);
    armed = {}; renamingId = {};
    sel = cur.id.isNotEmpty() ? cur.id : juce::String ("__init");
    selFolder = cur.id.isNotEmpty() ? parentRel (cur.id) : juce::String();
    layoutOverlays();
    presetOv->reveal = true;
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
    if (kind == 0 && libKind() != 0) libFolder = "wavetables";
    else if (kind != 0 && libKind() != 1) libFolder = "samples";
    libTarget = osc >= 0 && osc < OSC_N ? osc : -1;
    layoutOverlays();
    vaultOv->reveal = true;
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
