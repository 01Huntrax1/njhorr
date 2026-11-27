// The popup of the preset browser (logic: NjoPresetBrowser.h).  pbrowse::open (anchor, source) shows it over the whole editor; it removes itself when it is closed.
#pragma once
#include "ModUi.h"
#include "../NjoPresetBrowser.h"

namespace njo::pbrowse
{
    using namespace njo::theme;

    class Browser : public juce::Component, private juce::ListBoxModel, private juce::TextEditor::Listener
    {
    public:
        Browser (Source s) : src (std::move (s))
        {
            state.load (src.root); all = src.list ? src.list() : std::vector<Item>();
            if (src.snapshot) restore = src.snapshot();
            setWantsKeyboardFocus (true);
            views.setModel (&viewModel); items.setModel (this);
            for (auto* l : { &views, &items }) { l->setRowHeight (22); l->setColour (juce::ListBox::backgroundColourId, juce::Colour (0xff0c0d0e)); l->setColour (juce::ListBox::outlineColourId, juce::Colour (0xff2a2d31)); l->setOutlineThickness (1); addAndMakeVisible (*l); }
            search.setTextToShowWhenEmpty ("search name, folder or #tag", dim); search.addListener (this); search.setFont (font (12.0f)); addAndMakeVisible (search);
            auto mk = [this] (const juce::String& t, std::function<void()> fn, bool accent = false) { auto* b = btns.add (new Btn()); b->text = t; b->click = std::move (fn); b->accent = accent; addAndMakeVisible (b); return b; };
            mk ("PREV", [this] { step (-1); }); mk ("NEXT", [this] { step (1); }); mk ("RANDOM", [this] { randomPick(); });
            auditBtn = mk ("AUDITION", [this] { audition = ! audition; auditBtn->accent = audition; auditBtn->repaint(); }, true);
            if (src.saveAs) mk ("SAVE AS...", [this] { saveDialog(); });
            if (src.reveal) mk ("FOLDER", [this] { src.reveal(); });
            if (src.more) mk (src.moreLabel, [this] { auto fn = src.more; close (true); fn(); });
            mk ("CANCEL", [this] { close (false); }); mk ("LOAD", [this] { commit(); }, true);
            audition = (bool) src.snapshot; auditBtn->accent = audition; rebuildViews(); refresh();
        }
        ~Browser() override = default;

        void paint (juce::Graphics& g) override
        {
            g.fillAll (juce::Colours::black.withAlpha (0.55f));
            paintCard (g, panel.toFloat());
            g.setColour (red); g.setFont (impact (12.0f)); g.drawText (src.title.toUpperCase(), panel.getX() + 14, panel.getY() + 8, 300, 18, juce::Justification::centredLeft);
            g.setColour (dim); g.setFont (font (9.0f));
            g.drawText (juce::String ((int) shown.size()) + " of " + juce::String ((int) all.size()) + "   -   click = load (audition), double click / Enter = keep, star = favourite, right click = more",
                        panel.getX() + 14, panel.getBottom() - 20, panel.getWidth() - 28, 14, juce::Justification::centredLeft);
        }
        void resized() override
        {
            panel = getLocalBounds().withSizeKeepingCentre (juce::jmin (getWidth() - 40, 820), juce::jmin (getHeight() - 40, 520));
            auto r = panel.reduced (12, 8); r.removeFromTop (22);
            auto top = r.removeFromTop (28); r.removeFromTop (6);
            auto bot = r.removeFromBottom (28); r.removeFromBottom (22);
            auto tb = top; const int bw = 74; for (int i = 3; i >= 0; --i) { btns[(size_t) i]->setBounds (tb.removeFromRight (bw + (i == 3 ? 10 : 0)).reduced (2, 0)); }
            search.setBounds (tb.reduced (2, 2));
            views.setBounds (r.removeFromLeft (190)); r.removeFromLeft (6); items.setBounds (r);
            int x = bot.getRight();
            for (int i = btns.size() - 1; i >= 4; --i) { auto* b = btns[i]; const int w = (b->text == "LOAD" || b->text == "CANCEL") ? 90 : 110; b->setBounds (x - w, bot.getY(), w - 4, bot.getHeight()); x -= w; }
        }
        void mouseDown (const juce::MouseEvent& e) override { if (! panel.contains (e.getPosition())) close (false); }
        bool keyPressed (const juce::KeyPress& k) override
        {
            if (k == juce::KeyPress::escapeKey) { close (false); return true; }
            return false;
        }
        void parentHierarchyChanged() override { if (getParentComponent() != nullptr) { search.grabKeyboardFocus(); } }

    private:
        struct Btn : juce::Component
        {
            juce::String text; bool accent = false, over = false; std::function<void()> click;
            void paint (juce::Graphics& g) override { auto r = getLocalBounds().toFloat().reduced (0.5f); paintButton (g, r, accent, over, false, 3.0f); g.setColour (accent ? juce::Colours::white : ink); g.setFont (font (9.0f, true)); g.drawText (text, getLocalBounds(), juce::Justification::centred); }
            void mouseEnter (const juce::MouseEvent&) override { over = true; repaint(); }
            void mouseExit (const juce::MouseEvent&) override { over = false; repaint(); }
            void mouseUp (const juce::MouseEvent& e) override { if (getLocalBounds().contains (e.getPosition()) && click) click(); }
        };
        struct ViewModel : juce::ListBoxModel
        {
            Browser& o; explicit ViewModel (Browser& b) : o (b) {}
            int getNumRows() override { return (int) o.viewList.size(); }
            void paintListBoxItem (int row, juce::Graphics& g, int w, int h, bool sel) override
            {
                if (row < 0 || row >= (int) o.viewList.size()) return;
                if (sel) { g.setColour (red.withAlpha (0.3f)); g.fillRect (0, 0, w, h); }
                g.setColour (sel ? juce::Colours::white : ink); g.setFont (font (11.0f, sel)); g.drawText (o.viewLabels[(size_t) row], 8, 0, w - 12, h, juce::Justification::centredLeft);
            }
            void selectedRowsChanged (int row) override { if (row >= 0 && row < (int) o.viewList.size() && ! o.rebuilding) { o.view = o.viewList[(size_t) row]; o.refresh(); } }
        };

        Source src; State state; std::vector<Item> all, shown; std::function<void()> restore; View view;
        std::vector<View> viewList; std::vector<juce::String> viewLabels; bool rebuilding = false, audition = true, applied = false, committed = false;
        juce::String lastId; juce::Rectangle<int> panel;
        ViewModel viewModel { *this };
        juce::ListBox views, items; juce::TextEditor search; juce::OwnedArray<Btn> btns; Btn* auditBtn = nullptr;

        // ---- list models ----
        int getNumRows() override { return (int) shown.size(); }
        void paintListBoxItem (int row, juce::Graphics& g, int w, int h, bool sel) override
        {
            if (row < 0 || row >= (int) shown.size()) return;
            auto& it = shown[(size_t) row];
            if (sel) { g.setColour (red.withAlpha (0.3f)); g.fillRect (0, 0, w, h); } else if (row % 2) { g.setColour (juce::Colours::white.withAlpha (0.03f)); g.fillRect (0, 0, w, h); }
            const bool fav = state.isFav (src.key, it.id);
            g.setColour (fav ? juce::Colour (0xffffd24a) : dim.withAlpha (0.6f)); g.setFont (font (13.0f)); g.drawText (fav ? juce::String (juce::CharPointer_UTF8 ("\xe2\x98\x85")) : juce::String (juce::CharPointer_UTF8 ("\xe2\x98\x86")), 0, 0, 24, h, juce::Justification::centred);
            g.setColour (it.id == lastId ? juce::Colour (0xffffd24a) : (sel ? juce::Colours::white : ink)); g.setFont (font (11.5f, sel));
            g.drawText (it.name, 28, 0, w / 2 - 20, h, juce::Justification::centredLeft);
            g.setColour (dim); g.setFont (font (9.5f));
            g.drawText (it.group + (it.user ? "  (user)" : ""), w / 2 + 10, 0, w / 5, h, juce::Justification::centredLeft);
            auto tg = state.tagsOf (src.key, it.id); juce::String ts; for (auto& t : tg) ts += "#" + t + " ";
            g.setColour (juce::Colour (0xff6fd0ff).withAlpha (0.85f)); g.drawText (ts, w / 2 + w / 5 + 14, 0, w - (w / 2 + w / 5 + 18), h, juce::Justification::centredLeft);
        }
        void listBoxItemClicked (int row, const juce::MouseEvent& e) override
        {
            if (row < 0 || row >= (int) shown.size()) return;
            if (e.mods.isPopupMenu()) { items.selectRow (row); contextMenu (shown[(size_t) row]); return; }
            if (e.x < 26) { state.toggleFav (src.key, shown[(size_t) row].id); state.save (src.root); refreshKeep(); }
        }
        void selectedRowsChanged (int row) override { if (row >= 0 && row < (int) shown.size() && audition && ! rebuilding) load (shown[(size_t) row]); }
        void listBoxItemDoubleClicked (int row, const juce::MouseEvent&) override { if (row >= 0 && row < (int) shown.size()) { load (shown[(size_t) row]); commit(); } }
        void returnKeyPressed (int) override { commit(); }
        void textEditorTextChanged (juce::TextEditor&) override { refresh(); }
        void textEditorReturnKeyPressed (juce::TextEditor&) override { if (! shown.empty()) { items.selectRow (0); items.grabKeyboardFocus(); } }
        void textEditorEscapeKeyPressed (juce::TextEditor&) override { if (search.isEmpty()) close (false); else { search.clear(); refresh(); } }

        // ---- logic ----
        void rebuildViews()
        {
            rebuilding = true; viewList.clear(); viewLabels.clear();
            auto add = [this] (View v, const juce::String& l) { viewList.push_back (v); viewLabels.push_back (l); };
            add ({ View::All, "" }, "All"); add ({ View::Favorites, "" }, juce::String (juce::CharPointer_UTF8 ("\xe2\x98\x85")) + " Favorites"); add ({ View::Recent, "" }, "Recently used");
            juce::StringArray gs; for (auto& it : all) gs.addIfNotAlreadyThere (it.group); 
            for (auto& g : gs) add ({ View::Group, g }, g.isEmpty() ? juce::String ("(no folder)") : g);
            for (auto& t : state.allTags (src.key)) add ({ View::Tag, t }, "#" + t);
            views.updateContent(); int sel = 0; for (size_t i = 0; i < viewList.size(); ++i) if (viewList[i].kind == view.kind && viewList[i].arg == view.arg) sel = (int) i;
            views.selectRow (sel, false, true); views.repaint(); rebuilding = false;
        }
        void refresh()
        {
            rebuilding = true; shown = filter (all, state, src.key, view, search.getText()); items.updateContent(); items.deselectAllRows();
            for (size_t i = 0; i < shown.size(); ++i) if (shown[i].id == lastId) items.selectRow ((int) i, false, true);
            items.repaint(); rebuilding = false; repaint();
        }
        void refreshKeep() { const int s = items.getSelectedRow(); refresh(); if (s >= 0) { rebuilding = true; items.selectRow (juce::jmin (s, (int) shown.size() - 1), false, true); rebuilding = false; } }
        void reloadAll() { all = src.list ? src.list() : std::vector<Item>(); rebuildViews(); refresh(); }
        void load (const Item& it) { if (src.apply && src.apply (it)) { lastId = it.id; applied = true; items.repaint(); } }
        void step (int d)
        {
            if (shown.empty()) return; int cur = items.getSelectedRow(); if (cur < 0) cur = d > 0 ? -1 : 0; cur = (cur + d + (int) shown.size()) % (int) shown.size();
            items.selectRow (cur, false, true); load (shown[(size_t) cur]); items.scrollToEnsureRowIsOnscreen (cur);
        }
        void randomPick() { if (shown.empty()) return; const int r = juce::Random::getSystemRandom().nextInt ((int) shown.size()); items.selectRow (r, false, true); load (shown[(size_t) r]); items.scrollToEnsureRowIsOnscreen (r); }
        void commit()
        {
            const int r = items.getSelectedRow();
            if (! applied && r >= 0 && r < (int) shown.size()) load (shown[(size_t) r]);
            committed = true; if (lastId.isNotEmpty()) { state.use (src.key, lastId); state.save (src.root); }
            close (true);
        }
        void close (bool keep)
        {
            if (! keep && applied && restore) restore();   // cancel: the state from before the audition
            juce::Component::SafePointer<Browser> sp (this);
            juce::MessageManager::callAsync ([sp] { if (sp != nullptr) { if (auto* p = sp->getParentComponent()) p->removeChildComponent (sp.getComponent()); delete sp.getComponent(); } });
        }
        void askText (const juce::String& title, const juce::String& msg, const juce::String& init, std::function<void (const juce::String&)> ok)
        {
            auto* w = new juce::AlertWindow (title, msg, juce::MessageBoxIconType::NoIcon, this);
            w->addTextEditor ("t", init, {}); w->addButton ("OK", 1, juce::KeyPress (juce::KeyPress::returnKey)); w->addButton ("Cancel", 0, juce::KeyPress (juce::KeyPress::escapeKey));
            juce::Component::SafePointer<Browser> sp (this);
            w->enterModalState (true, juce::ModalCallbackFunction::create ([sp, w, ok] (int r) { if (r == 1 && sp != nullptr) ok (w->getTextEditorContents ("t")); }), true);
        }
        void saveDialog()
        {
            juce::StringArray folders; for (auto& it : all) if (it.user && it.group.isNotEmpty()) folders.addIfNotAlreadyThere (it.group);
            askText ("Save " + src.title, "Name of the preset:", src.defaultName, [this] (const juce::String& n) { if (n.trim().isNotEmpty()) { src.saveAs (n.trim(), view.kind == View::Group ? view.arg : juce::String()); reloadAll(); } });
        }
        void contextMenu (const Item& it)
        {
            juce::PopupMenu m, mv; m.addItem (1, "Load"); m.addItem (2, state.isFav (src.key, it.id) ? "Remove from favourites" : "Add to favourites"); m.addItem (3, "Edit tags...");
            const bool u = it.user; juce::StringArray fs; for (auto& x : all) if (x.user && x.group.isNotEmpty()) fs.addIfNotAlreadyThere (x.group);
            if (u && src.rename) m.addItem (4, "Rename...");
            if (u && src.move) { mv.addItem (50, "(no folder)"); for (int i = 0; i < fs.size(); ++i) mv.addItem (51 + i, fs[i]); mv.addItem (49, "New folder..."); m.addSubMenu ("Move to folder", mv); }
            if (u && src.remove) m.addItem (5, "Delete...");
            juce::Component::SafePointer<Browser> sp (this); const Item copy = it;
            m.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&items), [sp, copy, fs] (int r)
            {
                if (sp == nullptr || r <= 0) return; auto& b = *sp;
                if (r == 1) b.load (copy);
                else if (r == 2) { b.state.toggleFav (b.src.key, copy.id); b.state.save (b.src.root); b.refreshKeep(); }
                else if (r == 3) b.askText ("Tags", "Tags of " + copy.name + " (separated by spaces or commas):", b.state.tagsOf (b.src.key, copy.id).joinIntoString (" "), [sp, copy] (const juce::String& t) { sp->state.setTags (sp->src.key, copy.id, t); sp->state.save (sp->src.root); sp->rebuildViews(); sp->refresh(); });
                else if (r == 4) b.askText ("Rename", "New name:", copy.name, [sp, copy] (const juce::String& n)
                    { if (n.trim().isNotEmpty() && sp->src.rename (copy, n.trim())) { const auto old = copy.id; sp->reloadAll(); for (auto& x : sp->all) if (x.name == n.trim() && x.group == copy.group) sp->state.renamed (sp->src.key, old, x.id); sp->state.save (sp->src.root); sp->reloadAll(); } });
                else if (r == 5)
                {
                    if (juce::AlertWindow::showOkCancelBox (juce::MessageBoxIconType::QuestionIcon, "Delete preset", "Delete \"" + copy.name + "\"?", "Delete", "Keep", &b))
                    { if (b.src.remove (copy)) { b.state.forget (b.src.key, copy.id); b.state.save (b.src.root); b.reloadAll(); } }
                }
                else if (r == 49) b.askText ("New folder", "Name of the folder:", "", [sp, copy] (const juce::String& n) { if (n.trim().isNotEmpty() && sp->src.move (copy, n.trim())) sp->reloadAll(); });
                else if (r == 50) { if (b.src.move (copy, {})) b.reloadAll(); }
                else if (r >= 51 && r - 51 < fs.size()) { if (b.src.move (copy, fs[r - 51])) b.reloadAll(); }
            });
        }
    };


    // a source for presets that are lists of parameter values: factory entries come from the caller, user presets are files <root>/<subdir>/[<folder>/]<name>.<ext>
    // (header "njopar 1", the count, then one value per line, in the order of ids()); folders are real folders, so rename / move / delete work on the files.
    struct ParamSourceSpec
    {
        juce::String key, title, subdir, ext, defaultName;
        juce::File root;
        std::vector<Item> factory;                                  // id "f:<n>"
        std::function<void (int)> applyFactory;                     // n
        std::function<std::vector<int>()> ids;                      // the parameters a user preset holds
        std::function<float (int)> get;
        std::function<void (int, float)> set;
    };
    inline juce::File paramDir (const ParamSourceSpec& p) { return p.root.getChildFile (p.subdir); }
    inline Source makeParamSource (const ParamSourceSpec& p)
    {
        Source s; s.key = p.key; s.title = p.title; s.root = p.root; s.defaultName = p.defaultName;
        auto dir = paramDir (p); const auto ext = p.ext;
        auto fileOf = [dir, ext] (const juce::String& id) { return dir.getChildFile (id.substring (2) + "." + ext); };
        s.list = [p, dir, ext]
        {
            auto L = p.factory;
            auto files = dir.findChildFiles (juce::File::findFiles, true, "*." + ext); files.sort();
            for (auto& f : files)
            {
                auto rel = f.getRelativePathFrom (dir).replaceCharacter ('\\', '/'); rel = rel.dropLastCharacters (ext.length() + 1);
                const auto folder = rel.contains ("/") ? rel.upToLastOccurrenceOf ("/", false, false) : juce::String();
                L.push_back ({ "u:" + rel, f.getFileNameWithoutExtension(), folder.isEmpty() ? juce::String ("User") : "User/" + folder, true });
            }
            return L;
        };
        s.apply = [p, fileOf] (const Item& it)
        {
            if (it.id.startsWith ("f:")) { p.applyFactory (it.id.substring (2).getIntValue()); return true; }
            auto lines = juce::StringArray::fromLines (fileOf (it.id).loadFileAsString()); const auto ids = p.ids();
            if (lines.size() < 2 || ! lines[0].startsWith ("njopar")) return false;
            for (int i = 0; i < ids.size() && i + 2 < lines.size() + 0; ++i) p.set (ids[(size_t) i], lines[i + 2].getFloatValue());
            return true;
        };
        s.snapshot = [p] { const auto ids = p.ids(); std::vector<float> v; for (int id : ids) v.push_back (p.get (id)); return std::function<void()> ([p, ids, v] { for (size_t i = 0; i < ids.size(); ++i) p.set (ids[i], v[i]); }); };
        s.saveAs = [p, dir, ext] (const juce::String& n, const juce::String& group)
        {
            juce::String body = "njopar 1\n"; const auto ids = p.ids(); body += juce::String ((int) ids.size()) + "\n"; for (int id : ids) body += juce::String (p.get (id), 6) + "\n";
            auto folder = group.startsWith ("User/") ? group.substring (5) : juce::String(); auto d = folder.isEmpty() ? dir : dir.getChildFile (folder); d.createDirectory();
            d.getChildFile (juce::File::createLegalFileName (n) + "." + ext).replaceWithText (body);
        };
        s.rename = [fileOf, ext] (const Item& it, const juce::String& n) { auto f = fileOf (it.id); return f.moveFileTo (f.getSiblingFile (juce::File::createLegalFileName (n) + "." + ext)); };
        s.remove = [fileOf] (const Item& it) { return fileOf (it.id).deleteFile(); };
        s.move = [fileOf, dir, ext] (const Item& it, const juce::String& group)
        {
            auto f = fileOf (it.id); auto folder = group.startsWith ("User/") ? group.substring (5) : (group == "User" ? juce::String() : group); auto d = folder.isEmpty() ? dir : dir.getChildFile (juce::File::createLegalFileName (folder)); d.createDirectory();
            return f.moveFileTo (d.getChildFile (f.getFileName()));
        };
        s.reveal = [dir] { dir.createDirectory(); dir.revealToUser(); };
        return s;
    }

    // shows the browser over the whole editor that contains the anchor
    inline void open (juce::Component& anchor, Source src)
    {
        auto* top = anchor.getTopLevelComponent(); if (top == nullptr) return;
        auto* b = new Browser (std::move (src)); top->addAndMakeVisible (b); b->setBounds (top->getLocalBounds()); b->toFront (true);
    }
}
