// One preset browser for every kind of preset (Inspirator, Sequencer, Melodic, Tables, LFO, the synth presets): a popup over the editor with a search field, groups /
// folders, tags, favourites, recently used, audition (a click loads the preset, CANCEL puts the old state back), previous / next / random, rename, delete, move to a
// folder, save as.  A kind plugs in with a `Source` (what it has, how to load / save / rename / delete); favourites, recents and tags are kept per source in
// <root>/PresetBrowser.json.  The logic (State, filter) has no GUI and is tested by native_ui/test/pbrowser_test.cpp.
#pragma once
#include <juce_core/juce_core.h>
#include <algorithm>
#include <functional>
#include <map>
#include <vector>

namespace njo::pbrowse
{
    struct Item { juce::String id, name, group; bool user = false; };

    struct Source
    {
        juce::String key, title;                                   // key: the state file section ("insp", "seq", ...)
        juce::File root;                                           // where PresetBrowser.json lives
        std::function<std::vector<Item>()> list;
        std::function<bool (const Item&)> apply;                   // load it
        std::function<std::function<void()>()> snapshot;           // the current state: returns a function that puts it back (audition / cancel); may be empty
        std::function<void (const juce::String& name, const juce::String& group)> saveAs;   // empty: no saving
        std::function<bool (const Item&, const juce::String& newName)> rename;               // user items only; empty: not possible
        std::function<bool (const Item&)> remove;                  // user items only
        std::function<bool (const Item&, const juce::String& group)> move;                   // user items only: into a folder ("" = root)
        std::function<void()> reveal;
        juce::String moreLabel; std::function<void()> more;      // an extra button (the synth presets: the classic menu with the folder management)                              // open the folder in the file manager
        juce::String defaultName = "My preset";
    };

    // favourites, recents and tags of all sources
    struct State
    {
        std::map<juce::String, juce::StringArray> fav, recent;                       // source key -> item ids (recent: newest first)
        std::map<juce::String, std::map<juce::String, juce::StringArray>> tags;     // source key -> item id -> tags
        static juce::File fileOf (const juce::File& root) { return root.getChildFile ("PresetBrowser.json"); }
        void load (const juce::File& root)
        {
            fav.clear(); recent.clear(); tags.clear();
            auto v = juce::JSON::parse (fileOf (root)); if (! v.isObject()) return;
            auto readList = [] (const juce::var& a) { juce::StringArray r; if (auto* arr = a.getArray()) for (auto& x : *arr) r.add (x.toString()); return r; };
            if (auto* o = v["fav"].getDynamicObject()) for (auto& p : o->getProperties()) fav[p.name.toString()] = readList (p.value);
            if (auto* o = v["recent"].getDynamicObject()) for (auto& p : o->getProperties()) recent[p.name.toString()] = readList (p.value);
            if (auto* o = v["tags"].getDynamicObject()) for (auto& p : o->getProperties())
                if (auto* t = p.value.getDynamicObject()) for (auto& q : t->getProperties()) tags[p.name.toString()][q.name.toString()] = readList (q.value);
        }
        void save (const juce::File& root) const
        {
            auto* o = new juce::DynamicObject(); auto list = [] (const juce::StringArray& s) { juce::Array<juce::var> a; for (auto& x : s) a.add (x); return juce::var (a); };
            auto* f = new juce::DynamicObject(); for (auto& p : fav) f->setProperty (p.first, list (p.second)); o->setProperty ("fav", juce::var (f));
            auto* r = new juce::DynamicObject(); for (auto& p : recent) r->setProperty (p.first, list (p.second)); o->setProperty ("recent", juce::var (r));
            auto* t = new juce::DynamicObject();
            for (auto& p : tags) { auto* q = new juce::DynamicObject(); for (auto& e : p.second) if (! e.second.isEmpty()) q->setProperty (e.first, list (e.second)); t->setProperty (p.first, juce::var (q)); }
            o->setProperty ("tags", juce::var (t));
            root.createDirectory(); fileOf (root).replaceWithText (juce::JSON::toString (juce::var (o)));
        }
        bool isFav (const juce::String& k, const juce::String& id) const { auto it = fav.find (k); return it != fav.end() && it->second.contains (id); }
        void toggleFav (const juce::String& k, const juce::String& id) { auto& a = fav[k]; if (a.contains (id)) a.removeString (id); else a.add (id); }
        void use (const juce::String& k, const juce::String& id) { auto& a = recent[k]; a.removeString (id); a.insert (0, id); while (a.size() > 30) a.remove (a.size() - 1); }
        juce::StringArray tagsOf (const juce::String& k, const juce::String& id) const { auto i = tags.find (k); if (i == tags.end()) return {}; auto j = i->second.find (id); return j == i->second.end() ? juce::StringArray() : j->second; }
        void setTags (const juce::String& k, const juce::String& id, const juce::String& text)
        {
            juce::StringArray t; for (auto& s : juce::StringArray::fromTokens (text.replaceCharacters (",;#", "   "), " ", {})) { auto x = s.trim().toLowerCase(); if (x.isNotEmpty() && ! t.contains (x)) t.add (x); }
            tags[k][id] = t;
        }
        void forget (const juce::String& k, const juce::String& id) { if (fav.count (k)) fav[k].removeString (id); if (recent.count (k)) recent[k].removeString (id); if (tags.count (k)) tags[k].erase (id); }
        void renamed (const juce::String& k, const juce::String& from, const juce::String& to)
        {
            for (auto* a : { &fav[k], &recent[k] }) { int i = a->indexOf (from); if (i >= 0) a->set (i, to); }
            auto& t = tags[k]; auto it = t.find (from); if (it != t.end()) { t[to] = it->second; t.erase (from); }
        }
        juce::StringArray allTags (const juce::String& k) const { juce::StringArray r; auto i = tags.find (k); if (i != tags.end()) for (auto& e : i->second) for (auto& s : e.second) r.addIfNotAlreadyThere (s); r.sort (true); return r; }
    };

    // the views of the left list
    struct View { enum Kind { All, Favorites, Recent, Group, Tag } kind = All; juce::String arg; };

    // the items a view and a search text show; every word of the query must be found in the name, the group or a tag ("#tag" = exactly that tag)
    inline std::vector<Item> filter (const std::vector<Item>& all, const State& st, const juce::String& key, const View& v, const juce::String& query)
    {
        std::vector<Item> out;
        auto words = juce::StringArray::fromTokens (query.trim().toLowerCase(), " ", {});
        for (auto& it : all)
        {
            if (v.kind == View::Favorites && ! st.isFav (key, it.id)) continue;
            if (v.kind == View::Recent) { auto r = st.recent.find (key); if (r == st.recent.end() || ! r->second.contains (it.id)) continue; }
            if (v.kind == View::Group && it.group != v.arg) continue;
            const auto tg = st.tagsOf (key, it.id);
            if (v.kind == View::Tag && ! tg.contains (v.arg)) continue;
            bool ok = true;
            for (auto& w : words)
            {
                if (w.isEmpty()) continue;
                if (w.startsWithChar ('#')) { if (! tg.contains (w.substring (1))) { ok = false; break; } continue; }
                if (! (it.name.toLowerCase().contains (w) || it.group.toLowerCase().contains (w) || tg.joinIntoString (" ").contains (w))) { ok = false; break; }
            }
            if (ok) out.push_back (it);
        }
        if (v.kind == View::Recent)
        {
            auto& r = st.recent.at (key);
            std::stable_sort (out.begin(), out.end(), [&] (const Item& a, const Item& b) { return r.indexOf (a.id) < r.indexOf (b.id); });
        }
        return out;
    }
}
