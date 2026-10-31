// The preset bar and its dropdown menus (preset browser, sound vault) in the style of Tone2 Icarus: click the name, pick from nested folder menus.
// Files: <Backend::rootFolder()>/{Presets,Samples,Wavetables}; the preset file format is shared with the web UI (NjoManagerStore.h).
#include "NjoManager.h"
#include "NjoFactory.h"
#include "NjoManagerStore.h"
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
        enum Style { Text, Left, Right, Close, Name, Drop };
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
                g.drawText (getButtonText(), r.reduced (8.0f, 0.0f).withTrimmedRight (14.0f), juce::Justification::centredLeft, true);
                drawArrow (g, r, hover);
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
                g.drawText (getButtonText(), r.reduced (2.0f, 0.0f).withTrimmedRight (style == Drop ? 10.0f : 0.0f), juce::Justification::centred, true);
                if (style == Drop) drawArrow (g, r, on || hover);
            }
        }
    private:
        static void drawArrow (juce::Graphics& g, juce::Rectangle<float> r, bool bright)
        {
            g.setColour (bright ? juce::Colours::white : theme::dim);
            juce::Path p; auto cx = r.getRight() - 9.0f, cy = r.getCentreY();
            p.addTriangle (cx - 3.5f, cy - 2.0f, cx + 3.5f, cy - 2.0f, cx, cy + 2.5f);
            g.fillPath (p);
        }
        Style style;
    };

    // a menu under construction: every item gets an id that maps to the action to run
    struct MenuBuilder
    {
        std::map<int, std::function<void()>> acts;
        std::map<int, juce::String> labels;
        int next = 1;
        bool invoke (const juce::String& label)   // test hook: run the action of the item with this label
        {
            for (auto& kv : labels) if (kv.second == label) { acts[kv.first](); return true; }
            return false;
        }
        void item (juce::PopupMenu& m, const juce::String& text, std::function<void()> fn, bool enabled = true, bool ticked = false)
        {
            int id = next++;
            acts[id] = std::move (fn);
            labels[id] = text;
            m.addItem (id, text, enabled, ticked);
        }
    };

    const juce::String STAR = "* ";
    juce::String favKey (char t, const juce::String& id) { return juce::String::charToString ((juce::juce_wchar) t) + ":" + id; }
    char kindChar (int kind) { return kind == 0 ? 'w' : 's'; }
}

// ====================================================================== Impl
struct ManagerBar::Impl : private Ctx::Listener, private juce::ChangeListener
{
    Impl (ManagerBar& o, Ctx& c, SoundMemory& m, juce::Component& h);
    ~Impl() override;

    ManagerBar& owner; Ctx& ctx; SoundMemory& memory; juce::Component& host;
    Store store;
    std::shared_ptr<bool> alive = std::make_shared<bool> (true);

    // ---- preset state
    struct Cur { juce::String id, name = "Init"; bool dirty = false; } cur;
    std::vector<PresetRec> presets;
    bool applying = false;
    int pendingLoads = 0;
    juce::String memSig;
    // ---- vault state
    std::vector<LibRec> lib;
    std::map<juce::String, double> durCache;
    std::map<juce::String, juce::String> hashCache;       // "id|size" -> fileHash
    struct SlotRef { juce::String id, name; };
    std::map<juce::String, SlotRef> slotLib;
    int libTarget = 0;                                    // the oscillator the bar's VAULT menu loads into
    std::map<juce::String, std::vector<juce::String>> folderCache;   // area -> relative folders (also the empty ones)
    std::set<juce::String> favs;
    // ---- bar
    PbButton prev { "", PbButton::Left }, next { "", PbButton::Right }, nameBtn { "Init", PbButton::Name }, save { "SAVE" }, vault { "VAULT", PbButton::Drop };
    juce::String infoText, lastStatus; juce::Rectangle<int> infoRect;
    OneShot infoTimer;
    bool menuOpen = false;
    bool dryRun = false;                                   // test hook: build the menus but do not show them
    std::shared_ptr<MenuBuilder> lastMenu; int lastMenuItems = 0;
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
    bool presetRename (const juce::String& id, const juce::String& newName);
    bool presetDeleteId (const juce::String& id);
    void pmMove (const juce::String& id, const juce::String& destRel);
    const PresetRec* findPreset (const juce::String& id) const { for (auto& p : presets) if (p.id == id) return &p; return nullptr; }
    // folders (area: "presets" / "samples" / "wavetables"; path: "presets/A/B")
    void foldersRefresh();
    bool folderNew (const juce::String& parentPath, const juce::String& name);
    bool folderRen (const juce::String& path, const juce::String& newName);
    bool folderDel (const juce::String& path);
    // vault
    void libRefresh();
    const LibRec* findLib (const juce::String& id) const { for (auto& r : lib) if (r.id == id) return &r; return nullptr; }
    void libImport (const juce::Array<juce::File>& files, const juce::String& destFolderPath);
    void libLoad (const juce::String& id, int osc);
    bool libRenameId (const juce::String& id, const juce::String& newLabel);
    void libMoveTo (const juce::String& id, const juce::String& destPath);
    bool libDeleteId (const juce::String& id);
    juce::String hashOf (const LibRec& r);
    void setSlot (const juce::String& key, const juce::String& id, const juce::String& name);
    void saveSlots();
    void reconcileSlots();
    juce::String signature() const;
    void swapId (const juce::String& oldId, const juce::String& newId);
    void openInFileManager (const juce::String& folderPath);
    // favourites
    bool isFav (const juce::String& key) const { return favs.count (key) > 0; }
    void toggleFav (const juce::String& key);
    void favRemap (const juce::String& oldPrefix, const juce::String& newPrefix);   // newPrefix empty: drop
    // dialogs
    void askName (const juce::String& title, const juce::String& message, const juce::String& initial, std::function<void (const juce::String&)> done);
    void askConfirm (const juce::String& title, const juce::String& message, std::function<void()> yes);
    // menus
    void showPresetMenu (juce::Component* anchor);
    void showVaultMenu (int kind, int osc, juce::Component* anchor);
    void closeAll();

    using MB = MenuBuilder;
private:
    void runMenu (juce::PopupMenu& menu, std::shared_ptr<MB> mb, juce::Component* anchor);
    void presetTree (MB& mb, juce::PopupMenu& menu, const juce::String& rel);
    bool presetTreeHas (const juce::String& rel) const;
    void libTree (MB& mb, juce::PopupMenu& menu, int kind, const juce::String& rel, int osc);
    void folderPick (MB& mb, juce::PopupMenu& menu, const juce::String& area, const juce::String& rel, const juce::String& rootLabel, bool includeRoot,
                     const std::function<void (const juce::String& path)>& pick);
    void fileManageMenu (MB& mb, juce::PopupMenu& menu, const LibRec& r);
    void paramChanged (int, float) override { if (! applying) presetDirty(); }
    void changeListenerCallback (juce::ChangeBroadcaster*) override;
};

namespace
{
    juce::String remapPrefix (const juce::String& s, const juce::String& oldP, const juce::String& newP)
    {
        if (s == oldP) return newP;
        if (s.startsWith (oldP + "/")) return newP + s.substring (oldP.length());
        return s;
    }
}

ManagerBar::Impl::Impl (ManagerBar& o, Ctx& c, SoundMemory& mem, juce::Component& h)
    : owner (o), ctx (c), memory (mem), host (h), store (c.be.rootFolder())
{
    installFactoryWavetables (c.be.rootFolder());   // first start: Wavetables/Factory/*.wav
    for (auto* b : { &prev, &nameBtn, &next, &save, &vault }) owner.addAndMakeVisible (*b);
    prev.onClick = [this] { presetStep (-1); };
    next.onClick = [this] { presetStep (1); };
    nameBtn.onClick = [this] { showPresetMenu (&nameBtn); };
    vault.onClick = [this] { showVaultMenu (-1, -1, &vault); };
    save.onClick = [this] { presetQuickSave(); };
    infoTimer.fn = [this] { infoText = {}; owner.repaint(); };

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
    favs = store.favLoad();
    updateBar();
    presetsRefresh();
    libRefresh();
    memSig = signature();

    ctx.addListener (this);
    memory.addChangeListener (this);
    ctx.onOpenVault = [this] (int kind, int osc, juce::Component* anchor) { showVaultMenu (kind, osc, anchor != nullptr ? anchor : &vault); };
}

ManagerBar::Impl::~Impl()
{
    *alive = false;
    ctx.onOpenVault = nullptr;
    ctx.removeListener (this);
    memory.removeChangeListener (this);
}

// ---------------------------------------------------------------- bar
void ManagerBar::Impl::barInfo (const juce::String& t)
{
    lastStatus = t;
    infoText = t; owner.repaint (infoRect);
    infoTimer.stopTimer();
    if (t.isNotEmpty()) infoTimer.startTimer (4500);
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
}

// ---------------------------------------------------------------- favourites
void ManagerBar::Impl::toggleFav (const juce::String& key)
{
    if (! favs.erase (key)) favs.insert (key);
    store.favSave (favs);
}

void ManagerBar::Impl::favRemap (const juce::String& oldPrefix, const juce::String& newPrefix)
{
    std::set<juce::String> out; bool changed = false;
    for (auto& k : favs)
    {
        auto r = remapPrefix (k, oldPrefix, newPrefix);
        if (r != k) changed = true;
        if (newPrefix.isNotEmpty() || r == k) out.insert (r);
        else if (k == oldPrefix || k.startsWith (oldPrefix + "/")) continue;
        else out.insert (r);
    }
    if (changed) { favs = out; store.favSave (favs); }
}

// ---------------------------------------------------------------- presets
void ManagerBar::Impl::presetsRefresh()
{
    presets = store.presetsList();
    foldersRefresh();
    if (cur.id.isNotEmpty() && ! findPreset (cur.id)) { cur.id = {}; updateBar(); }
}

juce::String ManagerBar::Impl::hashOf (const LibRec& r)
{
    auto key = r.id + "|" + juce::String (r.size);
    auto it = hashCache.find (key);
    if (it == hashCache.end()) it = hashCache.emplace (key, fileHash (store.fileFor (r))).first;
    return it->second;
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
        if (auto* l = findLib (it->second.id)) r.refs[d.key] = { l->fname, l->size, l->folder, hashOf (*l) };
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
    if (name.isEmpty()) { barInfo ("TYPE A NAME FIRST"); return {}; }
    if (safeFile (name).isEmpty()) { barInfo ("THAT NAME HAS NO USABLE CHARACTERS"); return {}; }
    if (name.equalsIgnoreCase ("init")) { barInfo ("'INIT' IS RESERVED"); return {}; }
    if (nameTaken (name, id, folder)) { barInfo ("NAME ALREADY USED IN THIS FOLDER"); return {}; }
    auto newId = store.presetSave (collectRec (name, folder), id);
    if (newId.isEmpty()) { barInfo ("SAVE FAILED"); return {}; }
    if (id.isNotEmpty() && id != newId) favRemap ("p:" + id, "p:" + newId);
    cur = { newId, name, false };
    presetsRefresh();
    updateBar();
    barInfo ("SAVED " + name);
    return newId;
}

void ManagerBar::Impl::presetQuickSave()
{
    if (cur.id.isNotEmpty()) presetSaveAs (cur.name, cur.id, parentRel (cur.id));
    else
        askName ("Save preset", "Name of the new preset (saved in the top folder; use the preset menu to pick a folder):", {},
                 [this] (const juce::String& n) { presetSaveAs (n, {}, {}); });
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
        if (item == nullptr && ref->second.hash.isNotEmpty())   // renamed as well: the content still finds it
            for (auto& r : lib) if (r.kind == d.kind && r.size == ref->second.size && hashOf (r) == ref->second.hash) { item = &r; break; }
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
    barInfo ((label.isNotEmpty() ? label : rec.name) + (missing ? " (" + juce::String (missing) + " FILE(S) NOT IN THE VAULT)" : " LOADED"));
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
    auto rec = presets[(size_t) i];
    presetApply (rec);
}

bool ManagerBar::Impl::presetRename (const juce::String& id, const juce::String& newName)
{
    auto* p = findPreset (id);
    if (! p) { barInfo ("NO SUCH PRESET"); return false; }
    auto nn = newName.trim().substring (0, 40);
    if (nn.isEmpty() || safeFile (nn).isEmpty()) { barInfo ("TYPE THE NEW NAME FIRST"); return false; }
    if (nn.equalsIgnoreCase ("init") || nameTaken (nn, p->id, p->folder)) { barInfo ("NAME ALREADY USED IN THIS FOLDER"); return false; }
    PresetRec r = *p; r.name = nn;
    auto nid = store.presetSave (r, id);
    if (nid.isEmpty()) { barInfo ("RENAME FAILED"); return false; }
    if (nid != id) favRemap ("p:" + id, "p:" + nid);
    if (cur.id == id) cur = { nid, nn, cur.dirty };
    presetsRefresh(); updateBar();
    barInfo ("RENAMED TO " + nn);
    return true;
}

bool ManagerBar::Impl::presetDeleteId (const juce::String& id)
{
    auto* p = findPreset (id);
    if (! p) return false;
    auto nm = p->name;
    if (! store.presetDelete (id)) { barInfo ("COULD NOT DELETE THE PRESET"); return false; }
    favRemap ("p:" + id, {});
    if (cur.id == id) cur.id = {};
    presetsRefresh(); updateBar();
    barInfo ("DELETED " + nm);
    return true;
}

void ManagerBar::Impl::pmMove (const juce::String& id, const juce::String& destRel)
{
    auto* p = findPreset (id);
    if (! p) { barInfo ("NO SUCH PRESET"); return; }
    if (p->folder == destRel) { barInfo ("ALREADY IN THAT FOLDER"); return; }
    auto rec = *p;
    auto nid = store.presetMove (rec, destRel);
    if (nid.isEmpty()) { barInfo ("COULD NOT MOVE (A PRESET WITH THAT FILE NAME EXISTS THERE?)"); return; }
    favRemap ("p:" + id, "p:" + nid);
    if (cur.id == id) cur.id = nid;
    presetsRefresh(); updateBar();
    barInfo ("MOVED " + rec.name + " TO " + (destRel.isEmpty() ? juce::String ("THE TOP FOLDER") : destRel.toUpperCase()));
}

// ---------------------------------------------------------------- folders
void ManagerBar::Impl::foldersRefresh()
{
    for (auto* a : { "presets", "samples", "wavetables" }) folderCache[a] = store.folders (a);
}

bool ManagerBar::Impl::folderNew (const juce::String& parentPath, const juce::String& name)
{
    auto nm = name.trim().isEmpty() ? juce::String ("New folder") : name.trim();
    auto np = store.folderCreate (parentPath, nm);
    if (np.isEmpty()) { barInfo ("COULD NOT CREATE THE FOLDER (NAME ALREADY USED?)"); return false; }
    foldersRefresh();
    barInfo ("CREATED " + np.toUpperCase());
    return true;
}

bool ManagerBar::Impl::folderRen (const juce::String& path, const juce::String& newName)
{
    if (! path.contains ("/")) { barInfo ("SELECT A SUB FOLDER"); return false; }
    auto nm = newName.trim();
    if (nm.isEmpty() || safeFile (nm).isEmpty()) { barInfo ("TYPE THE NEW FOLDER NAME FIRST"); return false; }
    auto np = store.folderRename (path, nm);
    if (np.isEmpty()) { barInfo ("RENAME FAILED (NAME ALREADY USED?)"); return false; }
    auto area = path.upToFirstOccurrenceOf ("/", false, false);
    auto o = path.fromFirstOccurrenceOf ("/", false, false), n2 = np.fromFirstOccurrenceOf ("/", false, false);
    if (area == "presets")
    {
        cur.id = remapPrefix (cur.id, o, n2);
        favRemap ("p:" + o, "p:" + n2);
        updateBar();
        presetsRefresh();
    }
    else
    {
        for (auto& kv : slotLib) kv.second.id = remapPrefix (kv.second.id, path, np);
        memory.relabel (path, np);
        favRemap (favKey (area == "wavetables" ? 'w' : 's', path), favKey (area == "wavetables" ? 'w' : 's', np));
        saveSlots();
        libRefresh();
    }
    barInfo ("RENAMED TO " + np.toUpperCase());
    return true;
}

bool ManagerBar::Impl::folderDel (const juce::String& path)
{
    if (! path.contains ("/")) { barInfo ("THE TOP FOLDERS CANNOT BE DELETED"); return false; }
    if (! store.folderDelete (path)) { barInfo ("COULD NOT DELETE THE FOLDER"); return false; }
    auto area = path.upToFirstOccurrenceOf ("/", false, false);
    if (area == "presets")
    {
        auto rel = path.fromFirstOccurrenceOf ("/", false, false);
        if (cur.id.startsWith (rel + "/")) { cur.id = {}; updateBar(); }
        favRemap ("p:" + rel, {});
        presetsRefresh();
    }
    else
    {
        for (auto it = slotLib.begin(); it != slotLib.end();) { if (it->second.id.startsWith (path + "/")) it = slotLib.erase (it); else ++it; }
        favRemap (favKey (area == "wavetables" ? 'w' : 's', path), {});
        saveSlots();
        libRefresh();
    }
    barInfo ("DELETED " + path.toUpperCase());
    return true;
}

void ManagerBar::Impl::openInFileManager (const juce::String& folderPath)
{
    auto dir = store.dirOf (folderPath);
    if (dir == juce::File()) return;
    dir.createDirectory();
    bool ok = dir.startAsProcess();
    barInfo (ok ? "OPENED " + dir.getFullPathName() : "COULD NOT OPEN " + dir.getFullPathName());
}

// ---------------------------------------------------------------- vault
void ManagerBar::Impl::libRefresh()
{
    lib = store.libList (durCache);
    foldersRefresh();
}

void ManagerBar::Impl::libImport (const juce::Array<juce::File>& files, const juce::String& destFolderPath)
{
    int kind = destFolderPath.startsWith ("wavetables") ? 0 : 1;
    auto rel = destFolderPath.fromFirstOccurrenceOf ("/", false, false);
    int n = 0, bad = 0;
    for (auto& f : files)
    {
        if (! f.existsAsFile() || ! isAudioName (f.getFileName())) { ++bad; continue; }
        bool dup = false;
        auto id = store.libAdd (kind, rel, f, lib, dup);
        if (id.isEmpty()) { ++bad; continue; }
        if (! dup) { ++n; libRefresh(); }
    }
    libRefresh();
    barInfo ("ADDED " + juce::String (n) + " FILE(S) TO " + destFolderPath.toUpperCase() + (bad ? ", " + juce::String (bad) + " UNSUPPORTED/FAILED" : juce::String()));
}

void ManagerBar::Impl::setSlot (const juce::String& key, const juce::String& id, const juce::String& name)
{
    slotLib[key] = { id, name };
    saveSlots();
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
    if (! r || ! store.fileFor (*r).existsAsFile()) { barInfo ("FILE MISSING - RESCAN FROM THE VAULT MENU"); return; }
    if (osc < 0 || osc >= OSC_N) osc = 0;
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
            barInfo ("LOADED " + label + " INTO " + findSlot (key)->label);
        }
        else barInfo (msg.isNotEmpty() ? msg.toUpperCase() : juce::String ("COULD NOT LOAD THAT FILE"));
    });
}

void ManagerBar::Impl::swapId (const juce::String& oldId, const juce::String& newId)
{
    for (auto& kv : slotLib) if (kv.second.id == oldId) kv.second.id = newId;
    memory.relabel (oldId, newId);
    auto kc = oldId.startsWith ("wavetables") ? 'w' : 's';
    favRemap (favKey (kc, oldId), favKey (newId.startsWith ("wavetables") ? 'w' : 's', newId));
    saveSlots();
}

bool ManagerBar::Impl::libRenameId (const juce::String& id, const juce::String& newLabel)
{
    auto* r = findLib (id);
    auto nv = newLabel.trim();
    if (! r || nv.isEmpty()) return false;
    auto copy = *r;
    if (nv == copy.label) return true;
    for (auto& x : lib) if (x.id != id && x.kind == copy.kind && x.folder == copy.folder && safeFile (x.label).equalsIgnoreCase (safeFile (nv))) { barInfo ("NAME ALREADY USED"); return false; }
    auto nid = store.libRename (copy, nv);
    if (nid.isEmpty()) { barInfo ("RENAME FAILED"); return false; }
    if (nid != id) swapId (id, nid);
    libRefresh();
    barInfo ("RENAMED TO " + nv);
    return true;
}

void ManagerBar::Impl::libMoveTo (const juce::String& id, const juce::String& destPath)
{
    auto* r = findLib (id);
    if (! r) return;
    auto rec = *r;
    if (destPath.startsWith ("presets")) return;
    auto nid = store.libMove (rec, destPath);
    if (nid.isEmpty()) { barInfo ("COULD NOT MOVE THE FILE"); return; }
    if (nid == id) { barInfo ("ALREADY IN THAT FOLDER"); return; }
    bool kindChanged = (destPath.startsWith ("wavetables") ? 0 : 1) != rec.kind;
    if (kindChanged)
    {
        for (auto it = slotLib.begin(); it != slotLib.end();) { if (it->second.id == id) it = slotLib.erase (it); else ++it; }   // the slot kind no longer matches
        favRemap (favKey (kindChar (rec.kind), id), {});
        saveSlots();
    }
    else swapId (id, nid);
    libRefresh();
    barInfo ("MOVED " + rec.label + " TO " + destPath.toUpperCase());
}

bool ManagerBar::Impl::libDeleteId (const juce::String& id)
{
    auto* r = findLib (id);
    if (! r) return false;
    auto rec = *r;
    if (! store.libDelete (rec)) { barInfo ("COULD NOT DELETE THE FILE"); return false; }
    for (auto it = slotLib.begin(); it != slotLib.end();) { if (it->second.id == id) it = slotLib.erase (it); else ++it; }
    favRemap (favKey (kindChar (rec.kind), id), {});
    saveSlots();
    libRefresh();
    barInfo ("DELETED " + rec.label);
    return true;
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
    if (changed) saveSlots();
}

void ManagerBar::Impl::changeListenerCallback (juce::ChangeBroadcaster*)
{
    auto sig = signature();
    bool differs = sig != memSig;
    memSig = sig;
    reconcileSlots();
    if (differs && pendingLoads == 0 && ! applying) presetDirty();
}

// ---------------------------------------------------------------- dialogs
void ManagerBar::Impl::askName (const juce::String& title, const juce::String& message, const juce::String& initial, std::function<void (const juce::String&)> done)
{
    auto* w = new juce::AlertWindow (title, message, juce::MessageBoxIconType::NoIcon);
    w->addTextEditor ("n", initial, {});
    if (auto* te = w->getTextEditor ("n")) { te->setInputRestrictions (60); te->selectAll(); }
    w->addButton ("OK", 1, juce::KeyPress (juce::KeyPress::returnKey));
    w->addButton ("Cancel", 0, juce::KeyPress (juce::KeyPress::escapeKey));
    host.addAndMakeVisible (w);
    w->setCentrePosition (host.getLocalBounds().getCentre());
    auto a = alive;
    w->enterModalState (true, juce::ModalCallbackFunction::create ([a, w, done] (int r)
    {
        if (*a && r == 1 && done) done (w->getTextEditorContents ("n"));
    }), true);
}

void ManagerBar::Impl::askConfirm (const juce::String& title, const juce::String& message, std::function<void()> yes)
{
    auto* w = new juce::AlertWindow (title, message, juce::MessageBoxIconType::WarningIcon);
    w->addButton ("Delete", 1, juce::KeyPress (juce::KeyPress::returnKey));
    w->addButton ("Cancel", 0, juce::KeyPress (juce::KeyPress::escapeKey));
    host.addAndMakeVisible (w);
    w->setCentrePosition (host.getLocalBounds().getCentre());
    auto a = alive;
    w->enterModalState (true, juce::ModalCallbackFunction::create ([a, yes] (int r) { if (*a && r == 1 && yes) yes(); }), true);
}

// ---------------------------------------------------------------- menus
void ManagerBar::Impl::runMenu (juce::PopupMenu& menu, std::shared_ptr<MB> mb, juce::Component* anchor)
{
    lastMenu = mb; lastMenuItems = menu.getNumItems();
    if (dryRun) { menuOpen = true; return; }
    menuOpen = true;
    auto a = alive;
    auto opts = juce::PopupMenu::Options().withMinimumWidth (anchor != nullptr ? juce::jmax (anchor->getWidth(), 200) : 200).withMaximumNumColumns (1);
    if (anchor != nullptr) opts = opts.withTargetComponent (anchor);
    menu.showMenuAsync (opts, [this, a, mb] (int r)
    {
        if (! *a) return;
        menuOpen = false;
        auto it = mb->acts.find (r);
        if (r > 0 && it != mb->acts.end()) { auto fn = it->second; defer (fn); }
    });
}

// the folders of one area as nested submenus; pick (path) is called for the chosen folder. includeRoot: the area folder itself can be picked.
void ManagerBar::Impl::folderPick (MB& mb, juce::PopupMenu& menu, const juce::String& area, const juce::String& rel, const juce::String& rootLabel, bool includeRoot,
                                   const std::function<void (const juce::String&)>& pick)
{
    auto& fl = folderCache[area];
    auto pathOf = [&] (const juce::String& r) { return r.isEmpty() ? area : area + "/" + r; };
    bool first = true;
    if (rel.isEmpty() && includeRoot) { auto p = pathOf (rel); mb.item (menu, rootLabel, [pick, p] { pick (p); }); }
    else if (! rel.isEmpty()) { auto p = pathOf (rel); mb.item (menu, "[ " + leafRel (rel) + " ]", [pick, p] { pick (p); }); }
    else first = false;
    bool any = false;
    for (auto& f : fl)
    {
        if (parentRel (f) != rel) continue;
        if (! any && ! first) menu.addSeparator();
        any = true;
        bool hasKids = false;
        for (auto& g : fl) if (parentRel (g) == f) hasKids = true;
        if (hasKids) { juce::PopupMenu sub; folderPick (mb, sub, area, f, {}, true, pick); menu.addSubMenu (leafRel (f), sub); }
        else { auto p = pathOf (f); mb.item (menu, leafRel (f), [pick, p] { pick (p); }); }
    }
    if (! any && rel.isEmpty() && ! includeRoot) mb.item (menu, "(no folders yet)", [] {}, false);
}

bool ManagerBar::Impl::presetTreeHas (const juce::String& rel) const
{
    for (auto& p : presets) if (p.folder == rel || p.folder.startsWith (rel + "/")) return true;
    return false;
}

void ManagerBar::Impl::presetTree (MB& mb, juce::PopupMenu& menu, const juce::String& rel)
{
    bool any = false;
    for (auto& f : folderCache["presets"])
    {
        if (parentRel (f) != rel) continue;
        juce::PopupMenu sub;
        presetTree (mb, sub, f);
        bool hasCur = cur.id.startsWith (f + "/");
        if (! presetTreeHas (f)) mb.item (sub, "(empty)", [] {}, false);
        menu.addSubMenu (leafRel (f), sub, true, nullptr, hasCur);
        any = true;
    }
    if (any) {}
    for (auto& p : presets)
    {
        if (p.folder != rel) continue;
        auto id = p.id;
        mb.item (menu, (isFav ("p:" + id) ? STAR : juce::String()) + p.name, [this, id] { if (auto* q = findPreset (id)) { auto r = *q; presetApply (r); } }, true, id == cur.id);
    }
}

void ManagerBar::Impl::showPresetMenu (juce::Component* anchor)
{
    presetsRefresh();
    auto mb = std::make_shared<MB>();
    juce::PopupMenu menu;
    mb->item (menu, "Init", [this] { presetInit(); }, true, cur.id.isEmpty() && cur.name == "Init");

    // favourites
    juce::PopupMenu favMenu; bool anyFav = false;
    for (auto& p : presets)
        if (isFav ("p:" + p.id)) { auto id = p.id; mb->item (favMenu, p.name, [this, id] { if (auto* q = findPreset (id)) { auto r = *q; presetApply (r); } }, true, id == cur.id); anyFav = true; }
    if (! anyFav) mb->item (favMenu, "(none yet - use 'Add to favorites' below)", [] {}, false);
    menu.addSubMenu ("Favorites", favMenu);
    menu.addSeparator();

    presetTree (*mb, menu, {});
    if (presets.empty() && folderCache["presets"].empty()) mb->item (menu, "(no saved presets yet)", [] {}, false);
    menu.addSeparator();

    // manage
    bool has = cur.id.isNotEmpty();
    auto id = cur.id;
    mb->item (menu, has ? "Save '" + cur.name + "'" : "Save...", [this] { presetQuickSave(); });
    {
        juce::PopupMenu sub;
        folderPick (*mb, sub, "presets", {}, "Top folder", true, [this] (const juce::String& path)
        {
            auto rel = path.fromFirstOccurrenceOf ("/", false, false);
            askName ("Save preset as", "Name of the new preset in " + (rel.isEmpty() ? juce::String ("the top folder") : rel) + ":", cur.id.isEmpty() && cur.name == "Init" ? juce::String() : cur.name,
                     [this, rel] (const juce::String& n) { presetSaveAs (n, {}, rel); });
        });
        menu.addSubMenu ("Save as new in", sub);
    }
    mb->item (menu, "Rename preset...", [this, id] { if (auto* p = findPreset (id)) askName ("Rename preset", "New name:", p->name, [this, id] (const juce::String& n) { presetRename (id, n); }); }, has);
    {
        juce::PopupMenu sub;
        folderPick (*mb, sub, "presets", {}, "Top folder", true, [this, id] (const juce::String& path) { pmMove (id, path.fromFirstOccurrenceOf ("/", false, false)); });
        menu.addSubMenu ("Move preset to", sub, has);
    }
    mb->item (menu, has && isFav ("p:" + id) ? "Remove from favorites" : "Add to favorites", [this, id] { toggleFav ("p:" + id); }, has);
    mb->item (menu, "Delete preset...", [this, id] { if (auto* p = findPreset (id)) askConfirm ("Delete preset", "Delete the preset '" + p->name + "'?", [this, id] { presetDeleteId (id); }); }, has);
    menu.addSeparator();

    // folders
    {
        juce::PopupMenu sub, a, b, c;
        folderPick (*mb, a, "presets", {}, "Top folder", true, [this] (const juce::String& parent)
        {
            askName ("New folder", "Name of the new folder inside " + parent + ":", {}, [this, parent] (const juce::String& n) { folderNew (parent, n); });
        });
        sub.addSubMenu ("New folder in", a);
        folderPick (*mb, b, "presets", {}, {}, false, [this] (const juce::String& path)
        {
            askName ("Rename folder", "New name for " + path + ":", leafRel (path), [this, path] (const juce::String& n) { folderRen (path, n); });
        });
        sub.addSubMenu ("Rename folder", b, ! folderCache["presets"].empty());
        folderPick (*mb, c, "presets", {}, {}, false, [this] (const juce::String& path)
        {
            int n = store.folderFileCount (path);
            askConfirm ("Delete folder", "Delete the folder " + path + " and its " + juce::String (n) + " file(s)?", [this, path] { folderDel (path); });
        });
        sub.addSubMenu ("Delete folder", c, ! folderCache["presets"].empty());
        menu.addSubMenu ("Folders", sub);
    }
    mb->item (menu, "Show presets folder", [this] { openInFileManager ("presets"); });
    mb->item (menu, "Rescan", [this] { presetsRefresh(); barInfo (juce::String ((int) presets.size()) + " SAVED PRESET(S)"); });
    runMenu (menu, mb, anchor);
}

void ManagerBar::Impl::libTree (MB& mb, juce::PopupMenu& menu, int kind, const juce::String& rel, int osc)
{
    auto area = Store::areaOf (kind);
    for (auto& f : folderCache[area])
    {
        if (parentRel (f) != rel) continue;
        juce::PopupMenu sub;
        libTree (mb, sub, kind, f, osc);
        bool any = false;
        for (auto& r : lib) if (r.kind == kind && (r.folder == f || r.folder.startsWith (f + "/"))) { any = true; break; }
        if (! any) mb.item (sub, "(empty)", [] {}, false);
        bool hasCur = false;
        for (auto& kv : slotLib) if (kv.second.id.startsWith (area + "/" + f + "/")) hasCur = true;
        menu.addSubMenu (leafRel (f), sub, true, nullptr, hasCur);
    }
    auto key = slotKey (kind, osc);
    for (auto& r : lib)
    {
        if (r.kind != kind || r.folder != rel) continue;
        auto id = r.id;
        auto it = slotLib.find (key);
        bool tick = it != slotLib.end() && it->second.id == id;
        mb.item (menu, (isFav (favKey (kindChar (kind), id)) ? STAR : juce::String()) + r.label + (r.dur > 0 ? "   " + juce::String (r.dur, 2) + " s" : juce::String()),
                 [this, id, osc] { libLoad (id, osc); }, true, tick);
    }
}

void ManagerBar::Impl::fileManageMenu (MB& mb, juce::PopupMenu& menu, const LibRec& r)
{
    auto id = r.id; auto fk = favKey (kindChar (r.kind), id);
    mb.item (menu, "Rename...", [this, id] { if (auto* x = findLib (id)) askName ("Rename file", "New name:", x->label, [this, id] (const juce::String& n) { libRenameId (id, n); }); });
    {
        juce::PopupMenu sub;
        for (auto* area : { "samples", "wavetables" })
        {
            juce::PopupMenu s2;
            folderPick (mb, s2, area, {}, juce::String (area) == "samples" ? "Top folder" : "Top folder", true, [this, id] (const juce::String& path) { libMoveTo (id, path); });
            sub.addSubMenu (juce::String (area) == "samples" ? "Samples" : "Wavetables", s2);
        }
        menu.addSubMenu ("Move to", sub);
    }
    mb.item (menu, isFav (fk) ? "Remove from favorites" : "Add to favorites", [this, fk] { toggleFav (fk); });
    mb.item (menu, "Delete file...", [this, id] { if (auto* x = findLib (id)) askConfirm ("Delete file", "Delete '" + x->fname + "' from the vault? Presets that use it will no longer find it.", [this, id] { libDeleteId (id); }); });
}

// kind < 0: both kinds; osc < 0: the target oscillator of the bar (libTarget)
void ManagerBar::Impl::showVaultMenu (int kind, int osc, juce::Component* anchor)
{
    libRefresh();
    auto mb = std::make_shared<MB>();
    juce::PopupMenu menu;
    bool fromBar = osc < 0 || osc >= OSC_N;
    if (fromBar) osc = juce::jlimit (0, OSC_N - 1, libTarget); else libTarget = osc;
    int tgt = osc;

    if (fromBar)
    {
        juce::PopupMenu t;
        for (int o = 0; o < OSC_N; ++o) mb->item (t, "Oscillator " + juce::String (o + 1), [this, o] { libTarget = o; barInfo ("VAULT LOADS INTO OSC " + juce::String (o + 1)); }, true, o == tgt);
        menu.addSubMenu ("Load into: OSC " + juce::String (tgt + 1), t);
    }
    else menu.addSectionHeader ("Load into OSC " + juce::String (osc + 1));
    menu.addSeparator();

    // favourites
    {
        juce::PopupMenu favMenu; bool anyFav = false;
        for (auto& r : lib)
        {
            if (kind >= 0 && r.kind != kind) continue;
            if (! isFav (favKey (kindChar (r.kind), r.id))) continue;
            auto id = r.id;
            mb->item (favMenu, r.label, [this, id, tgt] { libLoad (id, tgt); }); anyFav = true;
        }
        if (! anyFav) mb->item (favMenu, "(none yet - use 'Add to favorites' below)", [] {}, false);
        menu.addSubMenu ("Favorites", favMenu);
    }

    auto kinds = kind >= 0 ? std::vector<int> { kind, 1 - kind } : std::vector<int> { 1, 0 };
    for (size_t i = 0; i < kinds.size(); ++i)
    {
        int k = kinds[i];
        juce::PopupMenu sub;
        libTree (*mb, sub, k, {}, tgt);
        bool any = false; for (auto& r : lib) if (r.kind == k) { any = true; break; }
        if (! any && folderCache[Store::areaOf (k)].empty()) mb->item (sub, "(empty - use Add files)", [] {}, false);
        if (i == 0 && kind >= 0)   // the kind of the oscillator page: listed directly
        {
            menu.addSeparator();
            if (! any && folderCache[Store::areaOf (k)].empty()) mb->item (menu, k == 0 ? "(no wavetables yet - use Add files)" : "(no samples yet - use Add files)", [] {}, false);
            else libTree (*mb, menu, k, {}, tgt);
            menu.addSeparator();
        }
        else menu.addSubMenu (k == 0 ? "Wavetables" : "Samples", sub);
    }
    menu.addSeparator();

    // add files / manage the file that is loaded in the target oscillator
    {
        juce::PopupMenu add;
        for (auto* area : { "samples", "wavetables" })
        {
            juce::PopupMenu s2;
            folderPick (*mb, s2, area, {}, "Top folder", true, [this] (const juce::String& path)
            {
                chooser.reset (new juce::FileChooser ("Add sounds to " + path, juce::File(), SoundMemory::fileWildcard()));
                auto a = alive;
                chooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles | juce::FileBrowserComponent::canSelectMultipleItems,
                                      [this, a, path] (const juce::FileChooser& fc) { if (*a && fc.getResults().size() > 0) libImport (fc.getResults(), path); });
            });
            add.addSubMenu (juce::String (area) == "samples" ? "to Samples" : "to Wavetables", s2);
        }
        menu.addSubMenu ("Add files", add);
    }
    {
        juce::PopupMenu manage; bool anyLoaded = false;
        for (int k : { 1, 0 })
        {
            if (kind >= 0 && k != kind) continue;
            auto it = slotLib.find (slotKey (k, tgt));
            auto* r = it != slotLib.end() ? findLib (it->second.id) : nullptr;
            if (! r) continue;
            juce::PopupMenu fm; fileManageMenu (*mb, fm, *r);
            manage.addSubMenu ((k == 0 ? "Wavetable: " : "Sample: ") + r->label, fm);
            anyLoaded = true;
        }
        if (! anyLoaded) mb->item (manage, "(load a file into OSC " + juce::String (tgt + 1) + " first)", [] {}, false);
        menu.addSubMenu ("Loaded file of OSC " + juce::String (tgt + 1), manage);
    }
    {
        juce::PopupMenu sub, a, b, c;
        for (auto* area : { "samples", "wavetables" })
        {
            juce::PopupMenu aa, bb, cc; bool nonRoot = ! folderCache[area].empty();
            folderPick (*mb, aa, area, {}, "Top folder", true, [this] (const juce::String& parent)
            {
                askName ("New folder", "Name of the new folder inside " + parent + ":", {}, [this, parent] (const juce::String& n) { folderNew (parent, n); });
            });
            folderPick (*mb, bb, area, {}, {}, false, [this] (const juce::String& path)
            {
                askName ("Rename folder", "New name for " + path + ":", leafRel (path), [this, path] (const juce::String& n) { folderRen (path, n); });
            });
            folderPick (*mb, cc, area, {}, {}, false, [this] (const juce::String& path)
            {
                int n = store.folderFileCount (path);
                askConfirm ("Delete folder", "Delete the folder " + path + " and its " + juce::String (n) + " file(s)?", [this, path] { folderDel (path); });
            });
            auto nm = juce::String (area) == "samples" ? "Samples" : "Wavetables";
            a.addSubMenu (nm, aa); b.addSubMenu (nm, bb, nonRoot); c.addSubMenu (nm, cc, nonRoot);
        }
        sub.addSubMenu ("New folder in", a); sub.addSubMenu ("Rename folder", b); sub.addSubMenu ("Delete folder", c);
        menu.addSubMenu ("Folders", sub);
    }
    mb->item (menu, "Show vault folder", [this, kind, tgt] { openInFileManager (kind == 0 ? "wavetables" : "samples"); });
    mb->item (menu, "Rescan", [this] { libRefresh(); barInfo (juce::String ((int) lib.size()) + " FILE(S) IN THE VAULT"); });
    runMenu (menu, mb, anchor);
}

void ManagerBar::Impl::closeAll()
{
    juce::PopupMenu::dismissAllActiveMenus();
    menuOpen = false;
}

// ====================================================================== ManagerBar
ManagerBar::ManagerBar (Ctx& c, SoundMemory& m, juce::Component& overlayHost) : impl (new Impl (*this, c, m, overlayHost)) {}
ManagerBar::~ManagerBar() { impl->closeAll(); }

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
    impl->nameBtn.setBounds (r.removeFromLeft (230)); r.removeFromLeft (4);
    impl->next.setBounds (r.removeFromLeft (24)); r.removeFromLeft (10);
    impl->save.setBounds (r.removeFromLeft (56));
    impl->vault.setBounds (r.removeFromRight (74)); r.removeFromRight (10);
    impl->infoRect = r.withTrimmedLeft (10);
}

void ManagerBar::openBank() { impl->showPresetMenu (&impl->nameBtn); }
void ManagerBar::openVault (int kind, int osc) { impl->showVaultMenu (kind, osc, &impl->vault); }
void ManagerBar::closeOverlays() { impl->closeAll(); }
bool ManagerBar::overlayOpen() const { return impl->menuOpen; }
juce::String ManagerBar::presetName() const { return impl->nameBtn.getButtonText(); }
