// Folder tree used by the Preset Bank and the Sound Vault: folders (expand / collapse) with optional leaf items, selection, right click,
// double click on a leaf, and drag and drop of leaf items (and vault rows) onto folders.
#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "NjoTheme.h"

namespace njo
{
    inline float folderTextWidth (const juce::Font& f, const juce::String& t)
    {
        juce::GlyphArrangement ga; ga.addLineOfText (f, t, 0.0f, 0.0f);
        return ga.getBoundingBox (0, -1, true).getWidth();
    }

    class FolderTree : public juce::Component
    {
    public:
        struct Node
        {
            juce::String path;                 // folder path ("samples/Drums") or leaf id
            juce::String label, sub;           // sub: small grey text at the right of leaves
            bool folder = true, current = false;
            int count = 0;                     // files below a folder (shown grey next to the name; < 0 hides it)
            std::vector<Node> kids;
        };

        FolderTree()
        {
            tv.setRootItemVisible (false);
            tv.setDefaultOpenness (false);
            tv.setIndentSize (16);
            tv.setMultiSelectEnabled (false);
            tv.setColour (juce::TreeView::backgroundColourId, theme::deep);
            tv.setColour (juce::TreeView::linesColourId, theme::line);
            tv.getViewport()->getVerticalScrollBar().setColour (juce::ScrollBar::thumbColourId, theme::steel);
            addAndMakeVisible (tv);
        }
        ~FolderTree() override { tv.setRootItem (nullptr); }

        std::function<void (const Node&)> onSelect;                              // the user selected a node
        std::function<void (const Node&)> onActivate;                            // double click on a leaf
        std::function<void (const Node&)> onContext;                             // right click on a node (it is selected first)
        std::function<bool (const juce::String&)> acceptsDrag;                   // drag description -> may be dropped on folders
        std::function<void (const juce::String&, const Node&)> onDropOnFolder;   // drag description, target folder
        std::function<juce::String (const Node&)> dragDescription;               // description of a leaf that is dragged ("" = not draggable)

        void setRoots (std::vector<Node> roots, const juce::String& selectPath, bool reveal = false)
        {
            std::unique_ptr<juce::XmlElement> state (tv.getOpennessState (true));
            bool first = rootsPaths.isEmpty();
            silent = true;
            tv.setRootItem (nullptr);
            rootItem.reset (new Item (*this, Node{}, true));
            for (auto& r : roots) rootItem->addSubItem (new Item (*this, r, false));
            tv.setRootItem (rootItem.get());
            rootsPaths.clear(); for (auto& r : roots) rootsPaths.add (r.path);
            if (state != nullptr) tv.restoreOpennessState (*state, false);
            if (first) for (int i = 0; i < rootItem->getNumSubItems(); ++i) rootItem->getSubItem (i)->setOpen (true);
            selectPath_ (selectPath, reveal);
            silent = false;
        }

        // selects (and reveals) the node with that path
        void select (const juce::String& path) { silent = true; selectPath_ (path, true); silent = false; }
        juce::String selected() const { return selPath; }
        const Node* selectedNode() const { return selNode.path.isEmpty() ? nullptr : &selNode; }

        void resized() override { tv.setBounds (getLocalBounds()); }
        juce::TreeView tv;

    private:
        class Item : public juce::TreeViewItem
        {
        public:
            Item (FolderTree& o, Node nn, bool isRoot) : owner (o), n (std::move (nn)), root (isRoot)
            {
                for (auto& k : n.kids) addSubItem (new Item (o, k, false));
            }
            bool mightContainSubItems() override { return getNumSubItems() > 0; }
            juce::String getUniqueName() const override { return root ? juce::String ("root") : n.path; }
            int getItemHeight() const override { return 24; }
            bool canBeSelected() const override { return ! root; }

            void paintOpenCloseButton (juce::Graphics& g, const juce::Rectangle<float>& area, juce::Colour, bool over) override
            {
                juce::Path p; auto c = area.getCentre();
                if (isOpen()) p.addTriangle (c.x - 4, c.y - 2.5f, c.x + 4, c.y - 2.5f, c.x, c.y + 3.5f);
                else          p.addTriangle (c.x - 2.5f, c.y - 4, c.x - 2.5f, c.y + 4, c.x + 3.5f, c.y);
                g.setColour (over ? juce::Colours::white : theme::dim);
                g.fillPath (p);
            }
            void paintItem (juce::Graphics& g, int w, int h) override
            {
                if (root) return;
                bool sel = isSelected();
                if (sel) { g.setColour (theme::redDark.withAlpha (0.6f)); g.fillRect (0, 0, w, h); }
                float x = 4;
                if (n.folder)
                {
                    juce::Path f;   // little folder glyph
                    f.addRoundedRectangle (x, h * 0.5f - 4.0f, 13.0f, 9.0f, 1.5f);
                    f.addRectangle (x, h * 0.5f - 6.0f, 6.0f, 3.0f);
                    g.setColour (sel ? juce::Colours::white : (n.path.contains ("/") ? theme::orange.withAlpha (0.85f) : theme::red));
                    g.fillPath (f);
                    x += 19;
                }
                else
                {
                    g.setColour (n.current ? theme::red : theme::steel);
                    g.fillEllipse (x + 2, h * 0.5f - 3.5f, 7.0f, 7.0f);
                    x += 17;
                }
                g.setColour (sel ? juce::Colours::white : theme::ink);
                g.setFont (theme::font (n.folder ? 10.5f : 11.0f, true));
                int subW = n.folder ? 0 : juce::jmin (130, w / 2);
                g.drawText (n.label, (int) x, 0, w - (int) x - subW - 4, h, juce::Justification::centredLeft, true);
                g.setColour (theme::dim); g.setFont (theme::font (9.5f));
                if (n.folder && n.count >= 0)
                {
                    auto lw = (int) folderTextWidth (theme::font (10.5f, true), n.label);
                    g.drawText (juce::String (n.count), (int) x + lw + 6, 0, 48, h, juce::Justification::centredLeft, false);
                }
                else if (! n.folder) g.drawText (n.sub, w - subW - 4, 0, subW, h, juce::Justification::centredRight, true);
            }
            void itemSelectionChanged (bool isNowSelected) override
            {
                if (! isNowSelected || root) return;
                owner.selPath = n.path; owner.selNode = n;
                if (! owner.silent && owner.onSelect) owner.onSelect (n);
            }
            void itemClicked (const juce::MouseEvent& e) override
            {
                if (root) return;
                if (e.mods.isPopupMenu())
                {
                    owner.silent = true; setSelected (true, true); owner.silent = false;
                    owner.selPath = n.path; owner.selNode = n;
                    if (owner.onSelect) owner.onSelect (n);
                    if (owner.onContext) owner.onContext (n);
                }
            }
            void itemDoubleClicked (const juce::MouseEvent&) override
            {
                if (n.folder) setOpen (! isOpen());
                else if (owner.onActivate) owner.onActivate (n);
            }
            juce::var getDragSourceDescription() override
            {
                if (n.folder || ! owner.dragDescription) return {};
                auto d = owner.dragDescription (n);
                return d.isEmpty() ? juce::var() : juce::var (d);
            }
            bool isInterestedInDragSource (const juce::DragAndDropTarget::SourceDetails& d) override
            {
                return ! root && n.folder && owner.acceptsDrag && owner.acceptsDrag (d.description.toString());
            }
            void itemDropped (const juce::DragAndDropTarget::SourceDetails& d, int) override
            {
                if (owner.onDropOnFolder) owner.onDropOnFolder (d.description.toString(), n);
            }

            FolderTree& owner; Node n; bool root;
        };

        Item* find (Item* it, const juce::String& path)
        {
            if (it == nullptr) return nullptr;
            for (int i = 0; i < it->getNumSubItems(); ++i)
            {
                auto* s = static_cast<Item*> (it->getSubItem (i));
                if (s->n.path == path) return s;
                if (auto* r = find (s, path)) return r;
            }
            return nullptr;
        }
        void selectPath_ (const juce::String& path, bool reveal)
        {
            selPath = {}; selNode = {};
            if (path.isEmpty()) { tv.clearSelectedItems(); return; }
            if (auto* it = find (rootItem.get(), path))
            {
                if (reveal) for (auto* p = it->getParentItem(); p != nullptr; p = p->getParentItem()) p->setOpen (true);
                it->setSelected (true, true);
                selPath = it->n.path; selNode = it->n;
                if (reveal) tv.scrollToKeepItemVisible (it);
            }
            else tv.clearSelectedItems();
        }

        std::unique_ptr<Item> rootItem;
        juce::StringArray rootsPaths;
        juce::String selPath; Node selNode;
        bool silent = false;
    };
}
