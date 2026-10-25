#include "NjoManagerStore.h"
#include <juce_audio_formats/juce_audio_formats.h>
#include <algorithm>

namespace njo::mgr
{
    juce::String safeFile (const juce::String& name, int maxLen)
    {
        juce::String n;
        for (auto c : name) n << ((c < 32 || juce::String ("\\/:*?\"<>|").containsChar (c)) ? juce::juce_wchar ('_') : c);
        n = n.trimCharactersAtStart (". \t").trimCharactersAtEnd (". \t").substring (0, maxLen);
        auto l = n.toLowerCase();
        if (l == "con" || l == "prn" || l == "aux" || l == "nul"
            || ((l.startsWith ("com") || l.startsWith ("lpt")) && l.length() == 4 && l.getLastCharacter() >= '0' && l.getLastCharacter() <= '9'))
            n = "_" + n;
        return n;
    }

    juce::String fmtBytes (juce::int64 n)
    {
        if (n >= 1048576) return juce::String ((double) n / 1048576.0, 1) + " MB";
        if (n <= 0) return "0 KB";
        return juce::String (std::max<juce::int64> (1, (n + 512) / 1024)) + " KB";
    }

    juce::String extOf (const juce::String& f) { int i = f.lastIndexOfChar ('.'); return i > 0 ? f.substring (i) : juce::String(); }
    juce::String stemOf (const juce::String& f) { int i = f.lastIndexOfChar ('.'); return i > 0 ? f.substring (0, i) : f; }

    bool isAudioName (const juce::String& fname)
    {
        static const juce::StringArray exts = juce::StringArray::fromTokens (
            "wav wave w64 rf64 bwf aif aiff aifc afc au snd caf flac mp3 mp2 mpga ogg oga opus spx m4a m4b mp4 aac adts webm mka 3gp amr wma raw pcm sam smp dat bin sd s16", " ", "");
        return exts.contains (extOf (fname).substring (1).toLowerCase());
    }

    juce::String fileHash (const juce::File& f)
    {
        std::unique_ptr<juce::FileInputStream> in (f.createInputStream());
        if (in == nullptr) return {};
        const juce::int64 size = in->getTotalLength();
        juce::uint64 h = 1469598103934665603ull;
        auto feed = [&] (juce::int64 pos)
        {
            char buf[65536];
            in->setPosition (pos);
            auto n = in->read (buf, (int) std::min<juce::int64> (sizeof (buf), size - pos));
            for (int i = 0; i < n; ++i) { h ^= (juce::uint8) buf[i]; h *= 1099511628211ull; }
        };
        feed (0);
        if (size > 65536) feed (size - std::min<juce::int64> (65536, size - 65536));
        h ^= (juce::uint64) size; h *= 1099511628211ull;
        return juce::String::toHexString ((juce::int64) h) + "-" + juce::String (size);
    }

    double audioDuration (const juce::File& f)
    {
        static juce::AudioFormatManager fm;
        if (fm.getNumKnownFormats() == 0) fm.registerBasicFormats();
        std::unique_ptr<juce::AudioFormatReader> r (fm.createReaderFor (f));
        return r != nullptr && r->sampleRate > 0 ? (double) r->lengthInSamples / r->sampleRate : 0.0;
    }

    // ------------------------------------------------------------------ presets
    juce::String Store::toJson (const PresetRec& p)
    {
        auto* o = new juce::DynamicObject();
        o->setProperty ("format", "njohrr-preset");
        o->setProperty ("version", 1);
        o->setProperty ("name", p.name);
        o->setProperty ("saved", (juce::int64) p.saved);
        auto* params = new juce::DynamicObject();
        for (auto& kv : p.params) params->setProperty (juce::Identifier (juce::String (kv.first)), std::round (kv.second * 1e6) / 1e6);
        o->setProperty ("params", juce::var (params));
        auto* refs = new juce::DynamicObject();
        for (auto& kv : p.refs)
        {
            auto* r = new juce::DynamicObject();
            r->setProperty ("name", kv.second.name);
            r->setProperty ("size", (juce::int64) kv.second.size);
            if (kv.second.folder.isNotEmpty()) r->setProperty ("folder", kv.second.folder);
            if (kv.second.hash.isNotEmpty()) r->setProperty ("hash", kv.second.hash);   // extra key, ignored by the web UI
            refs->setProperty (juce::Identifier (kv.first), juce::var (r));
        }
        o->setProperty ("refs", juce::var (refs));
        if (! p.lfo.isVoid()) o->setProperty ("lfo", p.lfo);
        if (! p.frq.isVoid()) o->setProperty ("frq", p.frq);
        return juce::JSON::toString (juce::var (o), true);
    }

    bool Store::fromJson (const juce::String& text, PresetRec& out)
    {
        auto v = juce::JSON::parse (text);
        auto* o = v.getDynamicObject();
        if (o == nullptr) return false;
        auto* params = o->getProperty ("params").getDynamicObject();
        if (params == nullptr) return false;
        out.name = o->getProperty ("name").toString();
        out.saved = (juce::int64) o->getProperty ("saved");
        for (auto& kv : params->getProperties())
        {
            auto k = kv.name.toString();
            if (k.isEmpty() || ! k.containsOnly ("0123456789")) continue;
            if (! (kv.value.isDouble() || kv.value.isInt() || kv.value.isInt64() || kv.value.isString())) continue;
            double d = (double) kv.value;
            if (std::isfinite (d)) out.params[k.getIntValue()] = d;
        }
        if (auto* refs = o->getProperty ("refs").getDynamicObject())
            for (auto& kv : refs->getProperties())
                if (auto* r = kv.value.getDynamicObject())
                    out.refs[kv.name.toString()] = { r->getProperty ("name").toString(), (juce::int64) r->getProperty ("size"), r->getProperty ("folder").toString(), r->getProperty ("hash").toString() };
        out.lfo = o->getProperty ("lfo");
        out.frq = o->getProperty ("frq");
        return true;
    }

    // ------------------------------------------------------------------ paths and folders
    bool safeRel (const juce::String& rel)
    {
        if (rel.isEmpty()) return true;
        if (rel.startsWithChar ('/') || rel.containsChar ('\\') || rel.containsChar (':')) return false;
        for (auto& seg : juce::StringArray::fromTokens (rel, "/", ""))
            if (seg.isEmpty() || seg == "." || seg == ".." || seg != safeFile (seg, 100)) return false;
        return true;
    }
    juce::String joinRel (const juce::String& folder, const juce::String& name) { return folder.isEmpty() ? name : folder + "/" + name; }
    juce::String parentRel (const juce::String& rel) { int i = rel.lastIndexOfChar ('/'); return i < 0 ? juce::String() : rel.substring (0, i); }
    juce::String leafRel (const juce::String& rel) { int i = rel.lastIndexOfChar ('/'); return i < 0 ? rel : rel.substring (i + 1); }

    juce::File Store::dirOf (const juce::String& folderPath) const
    {
        auto area = folderPath.upToFirstOccurrenceOf ("/", false, false);
        auto rel = folderPath.fromFirstOccurrenceOf ("/", false, false);
        if (! safeRel (rel)) return {};
        juce::File base;
        if (area == "presets") base = presetsDir();
        else if (area == "samples") base = kindDir (1);
        else if (area == "wavetables") base = kindDir (0);
        else return {};
        return rel.isEmpty() ? base : base.getChildFile (rel);
    }

    std::vector<juce::String> Store::folders (const juce::String& area) const
    {
        std::vector<juce::String> out;
        auto base = dirOf (area);
        if (base == juce::File() || ! base.isDirectory()) return out;
        for (auto& d : base.findChildFiles (juce::File::findDirectories, true))
        {
            if (d.isHidden()) continue;
            auto rel = d.getRelativePathFrom (base).replaceCharacter ('\\', '/');
            bool hiddenPart = false;
            for (auto& seg : juce::StringArray::fromTokens (rel, "/", "")) if (seg.startsWithChar ('.')) hiddenPart = true;
            if (! hiddenPart && safeRel (rel)) out.push_back (rel);
        }
        std::sort (out.begin(), out.end(), [] (auto& a, auto& b) { return a.compareIgnoreCase (b) < 0; });
        return out;
    }

    juce::String Store::folderCreate (const juce::String& parentPath, const juce::String& nameIn)
    {
        auto name = safeFile (nameIn.trim(), 60);
        auto parent = dirOf (parentPath);
        if (name.isEmpty() || parent == juce::File()) return {};
        if (! parent.createDirectory()) return {};
        auto dir = parent.getChildFile (name);
        if (dir.exists()) return {};
        if (! dir.createDirectory()) return {};
        return parentPath + "/" + name;
    }

    juce::String Store::folderRename (const juce::String& folderPath, const juce::String& newName)
    {
        if (! folderPath.containsChar ('/')) return {};      // the area folders keep their names
        auto name = safeFile (newName.trim(), 60);
        auto dir = dirOf (folderPath);
        if (name.isEmpty() || dir == juce::File() || ! dir.isDirectory()) return {};
        auto dest = dir.getSiblingFile (name);
        if (dest == dir) return folderPath;
        if (dest.exists() && dest.getFullPathName().compareIgnoreCase (dir.getFullPathName()) != 0) return {};
        if (! dir.moveFileTo (dest)) return {};
        return parentRel (folderPath) + "/" + name;
    }

    bool Store::folderDelete (const juce::String& folderPath)
    {
        if (! folderPath.containsChar ('/')) return false;
        auto dir = dirOf (folderPath);
        if (dir == juce::File() || ! dir.isDirectory()) return false;
        return dir.moveToTrash() || dir.deleteRecursively();
    }

    int Store::folderFileCount (const juce::String& folderPath) const
    {
        auto dir = dirOf (folderPath);
        return dir == juce::File() ? 0 : (int) dir.findChildFiles (juce::File::findFiles, true).size();
    }

    // ------------------------------------------------------------------ presets
    std::vector<PresetRec> Store::presetsList() const
    {
        std::vector<PresetRec> out;
        auto base = presetsDir();
        for (auto& f : base.findChildFiles (juce::File::findFiles, true, "*" + presetExt))
        {
            if (! f.getFileName().endsWithIgnoreCase (presetExt) || f.isHidden()) continue;
            auto rel = f.getRelativePathFrom (base).replaceCharacter ('\\', '/');
            if (! safeRel (parentRel (rel))) continue;
            PresetRec r;
            if (! fromJson (f.loadFileAsString(), r)) continue;
            r.id = rel; r.folder = parentRel (rel);
            if (r.name.isEmpty()) r.name = stemOf (leafRel (rel));
            if (r.saved == 0) r.saved = f.getLastModificationTime().toMilliseconds();
            out.push_back (std::move (r));
        }
        std::sort (out.begin(), out.end(), [] (auto& a, auto& b)
        {
            int c = a.folder.compareIgnoreCase (b.folder);
            return c != 0 ? c < 0 : a.name.compareIgnoreCase (b.name) < 0;
        });
        return out;
    }

    juce::String Store::presetSave (const PresetRec& rec, const juce::String& prevId)
    {
        if (! safeRel (rec.folder)) return {};
        auto dir = rec.folder.isEmpty() ? presetsDir() : presetsDir().getChildFile (rec.folder);
        if (! dir.createDirectory()) return {};
        auto fname = safeFile (rec.name) + presetExt;
        // write to a temporary file first so a failed write never destroys the old preset
        auto tmp = dir.getChildFile (fname + ".tmp");
        if (! tmp.replaceWithText (toJson (rec))) { tmp.deleteFile(); return {}; }
        auto dest = dir.getChildFile (fname);
        if (! tmp.moveFileTo (dest)) { tmp.deleteFile(); return {}; }
        auto id = joinRel (rec.folder, fname);
        if (prevId.isNotEmpty() && prevId != id) presetDelete (prevId);
        return id;
    }

    bool Store::presetDelete (const juce::String& id)
    {
        if (! safeRel (parentRel (id)) || ! id.endsWithIgnoreCase (presetExt)) return false;
        auto f = presetsDir().getChildFile (id);
        return ! f.existsAsFile() || f.deleteFile();
    }

    juce::String Store::presetMove (const PresetRec& r, const juce::String& destFolder)
    {
        if (! safeRel (destFolder) || ! safeRel (parentRel (r.id))) return {};
        auto src = presetsDir().getChildFile (r.id);
        auto dir = destFolder.isEmpty() ? presetsDir() : presetsDir().getChildFile (destFolder);
        if (! dir.createDirectory()) return {};
        auto fname = leafRel (r.id);
        auto dest = dir.getChildFile (fname);
        if (dest == src) return r.id;
        if (dest.exists()) return {};
        return src.moveFileTo (dest) ? joinRel (destFolder, fname) : juce::String();
    }

    // ------------------------------------------------------------------ favourites
    std::set<juce::String> Store::favLoad() const
    {
        std::set<juce::String> out;
        auto v = juce::JSON::parse (root.getChildFile ("library.json"));
        if (auto* a = v.getProperty ("favorites", juce::var()).getArray())
            for (auto& e : *a) if (e.toString().isNotEmpty()) out.insert (e.toString());
        return out;
    }

    bool Store::favSave (const std::set<juce::String>& favs) const
    {
        juce::Array<juce::var> a;
        for (auto& s : favs) a.add (s);
        auto* o = new juce::DynamicObject();
        o->setProperty ("format", "njohrr-library");
        o->setProperty ("favorites", juce::var (a));
        root.createDirectory();
        return root.getChildFile ("library.json").replaceWithText (juce::JSON::toString (juce::var (o), true));
    }

    // ------------------------------------------------------------------ vault
    std::vector<LibRec> Store::libList (std::map<juce::String, double>& durCache) const
    {
        std::vector<LibRec> out;
        for (int kind = 0; kind < 2; ++kind)
        {
            auto base = kindDir (kind);
            for (auto& f : base.findChildFiles (juce::File::findFiles, true))
            {
                if (f.isHidden() || ! isAudioName (f.getFileName())) continue;
                auto rel = f.getRelativePathFrom (base).replaceCharacter ('\\', '/');
                if (! safeRel (parentRel (rel))) continue;
                LibRec r;
                r.kind = kind; r.fname = f.getFileName(); r.folder = parentRel (rel);
                r.id = areaOf (kind) + "/" + rel;
                r.label = stemOf (r.fname);
                r.size = f.getSize(); r.added = f.getLastModificationTime().toMilliseconds();
                auto key = r.id + "|" + juce::String (r.size);
                auto it = durCache.find (key);
                if (it == durCache.end()) it = durCache.emplace (key, audioDuration (f)).first;
                r.dur = it->second;
                out.push_back (std::move (r));
            }
        }
        std::sort (out.begin(), out.end(), [] (auto& a, auto& b) { return a.label.compareIgnoreCase (b.label) < 0; });
        return out;
    }

    juce::String Store::uniqueName (int kind, const juce::String& folder, const juce::String& fname) const
    {
        auto stem = stemOf (fname), ext = extOf (fname);
        auto dir = folder.isEmpty() ? kindDir (kind) : kindDir (kind).getChildFile (folder);
        auto out = fname; int n = 2;
        while (dir.getChildFile (out).exists()) out = stem + " (" + juce::String (n++) + ")" + ext;
        return out;
    }

    juce::String Store::libAdd (int kind, const juce::String& folder, const juce::File& src, const std::vector<LibRec>& existing, bool& duplicate)
    {
        duplicate = false;
        if (! safeRel (folder)) return {};
        auto fname = safeFile (src.getFileName(), 120);
        if (fname.isEmpty()) fname = "file";
        if (! isAudioName (fname)) fname += ".wav";
        for (auto& r : existing)
            if (r.kind == kind && r.folder == folder && r.size == src.getSize() && (r.fname == fname || r.fname == src.getFileName())) { duplicate = true; return r.id; }
        auto dir = folder.isEmpty() ? kindDir (kind) : kindDir (kind).getChildFile (folder);
        if (! dir.createDirectory()) return {};
        auto name = uniqueName (kind, folder, fname);
        if (! src.copyFileTo (dir.getChildFile (name))) return {};
        return areaOf (kind) + "/" + joinRel (folder, name);
    }

    juce::String Store::libRename (const LibRec& r, const juce::String& newLabel)
    {
        auto base = safeFile (newLabel.trim(), 100);
        if (base.isEmpty()) return {};
        auto nn = base + extOf (r.fname);
        auto dest = fileFor (r).getSiblingFile (nn);
        if (nn != r.fname && dest.exists()) return {};
        if (nn != r.fname && ! fileFor (r).moveFileTo (dest)) return {};
        return areaOf (r.kind) + "/" + joinRel (r.folder, nn);
    }

    juce::String Store::libMove (const LibRec& r, const juce::String& destFolderPath)
    {
        auto dir = dirOf (destFolderPath);
        if (dir == juce::File() || destFolderPath.startsWith ("presets")) return {};
        int nk = destFolderPath.startsWith ("wavetables") ? 0 : 1;
        auto folder = destFolderPath.fromFirstOccurrenceOf ("/", false, false);
        if (! dir.createDirectory()) return {};
        auto src = fileFor (r);
        if (dir == src.getParentDirectory()) return r.id;
        auto name = uniqueName (nk, folder, r.fname);
        if (! src.moveFileTo (dir.getChildFile (name))) return {};
        return areaOf (nk) + "/" + joinRel (folder, name);
    }

    bool Store::libDelete (const LibRec& r)
    {
        auto f = fileFor (r);
        return ! f.existsAsFile() || f.moveToTrash() || f.deleteFile();
    }
}
