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
                    out.refs[kv.name.toString()] = { r->getProperty ("name").toString(), (juce::int64) r->getProperty ("size") };
        out.lfo = o->getProperty ("lfo");
        out.frq = o->getProperty ("frq");
        return true;
    }

    std::vector<PresetRec> Store::presetsList() const
    {
        std::vector<PresetRec> out;
        for (auto& f : presetsDir().findChildFiles (juce::File::findFiles, false, "*" + presetExt))
        {
            if (! f.getFileName().endsWithIgnoreCase (presetExt)) continue;
            PresetRec r;
            if (! fromJson (f.loadFileAsString(), r)) continue;
            r.id = f.getFileName();
            if (r.name.isEmpty()) r.name = stemOf (r.id);
            if (r.saved == 0) r.saved = f.getLastModificationTime().toMilliseconds();
            out.push_back (std::move (r));
        }
        std::sort (out.begin(), out.end(), [] (auto& a, auto& b) { return a.name.compareIgnoreCase (b.name) < 0; });
        return out;
    }

    juce::String Store::presetSave (const PresetRec& rec, const juce::String& prevId)
    {
        auto dir = presetsDir();
        if (! dir.createDirectory()) return {};
        auto fname = safeFile (rec.name) + presetExt;
        // write to a temporary file first so a failed write never destroys the old preset
        auto tmp = dir.getChildFile (fname + ".tmp");
        if (! tmp.replaceWithText (toJson (rec))) { tmp.deleteFile(); return {}; }
        auto dest = dir.getChildFile (fname);
        if (! tmp.moveFileTo (dest)) { tmp.deleteFile(); return {}; }
        if (prevId.isNotEmpty() && prevId != fname) dir.getChildFile (prevId).deleteFile();
        return fname;
    }

    bool Store::presetDelete (const juce::String& id)
    {
        auto f = presetsDir().getChildFile (id);
        return f.getParentDirectory() == presetsDir() && (! f.existsAsFile() || f.deleteFile());
    }

    // ------------------------------------------------------------------ vault
    std::vector<LibRec> Store::libList (std::map<juce::String, double>& durCache) const
    {
        std::vector<LibRec> out;
        for (int kind = 0; kind < 2; ++kind)
        {
            auto folder = juce::String (kind == 0 ? "wavetables" : "samples");
            for (auto& f : kindDir (kind).findChildFiles (juce::File::findFiles, false))
            {
                if (f.isHidden() || ! isAudioName (f.getFileName())) continue;
                LibRec r;
                r.id = folder + "/" + f.getFileName();
                r.kind = kind; r.fname = f.getFileName(); r.label = stemOf (r.fname);
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

    juce::String Store::uniqueName (int kind, const juce::String& fname) const
    {
        auto stem = stemOf (fname), ext = extOf (fname);
        auto out = fname; int n = 2;
        while (kindDir (kind).getChildFile (out).exists()) out = stem + " (" + juce::String (n++) + ")" + ext;
        return out;
    }

    juce::String Store::libAdd (int kind, const juce::File& src, const std::vector<LibRec>& existing, bool& duplicate)
    {
        duplicate = false;
        auto fname = safeFile (src.getFileName(), 120);
        if (fname.isEmpty()) fname = "file";
        if (! isAudioName (fname)) fname += ".wav";
        auto folder = juce::String (kind == 0 ? "wavetables" : "samples");
        for (auto& r : existing)
            if (r.kind == kind && r.size == src.getSize() && (r.fname == fname || r.fname == src.getFileName())) { duplicate = true; return r.id; }
        auto dir = kindDir (kind);
        if (! dir.createDirectory()) return {};
        auto name = uniqueName (kind, fname);
        if (! src.copyFileTo (dir.getChildFile (name))) return {};
        return folder + "/" + name;
    }

    juce::String Store::libRename (const LibRec& r, const juce::String& newLabel)
    {
        auto base = safeFile (newLabel.trim(), 100);
        if (base.isEmpty()) return {};
        auto nn = base + extOf (r.fname);
        auto dest = kindDir (r.kind).getChildFile (nn);
        if (nn != r.fname && dest.exists()) return {};
        if (nn != r.fname && ! fileFor (r).moveFileTo (dest)) return {};
        return juce::String (r.kind == 0 ? "wavetables" : "samples") + "/" + nn;
    }

    juce::String Store::libMoveKind (const LibRec& r)
    {
        int nk = 1 - r.kind;
        auto dir = kindDir (nk);
        if (! dir.createDirectory()) return {};
        auto name = uniqueName (nk, r.fname);
        if (! fileFor (r).moveFileTo (dir.getChildFile (name))) return {};
        return juce::String (nk == 0 ? "wavetables" : "samples") + "/" + name;
    }

    bool Store::libDelete (const LibRec& r)
    {
        auto f = fileFor (r);
        return ! f.existsAsFile() || f.moveToTrash() || f.deleteFile();
    }
}
