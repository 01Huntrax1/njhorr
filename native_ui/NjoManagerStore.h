// File side of the Preset Bank / Sound Vault: <root>/{Presets,Samples,Wavetables}, each with any number of nested folders.
// Ids are paths relative to <root>: presets "Folder/Sub/name.njopreset", vault files "samples/Folder/file.wav" (flat files of older versions
// are simply the files of the root folder). A "folder path" is "<area>/<relative folder>" with area presets / samples / wavetables.
// A preset is a plain-text .njopreset (JSON), the same format as the web UI writes:
//   { "format":"njohrr-preset", "version":1, "name":..., "saved":<ms>, "params":{"<num>":value,...},
//     "refs":{"wt0":{"name":file,"size":bytes}|null,...}, "lfo":[...] (extra key, ignored by the web UI) }
#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include <map>

namespace njo::mgr
{
    inline const juce::String presetExt = ".njopreset";

    juce::String safeFile (const juce::String& name, int maxLen = 100);   // a name that is safe on Windows, macOS and Linux
    juce::String fmtBytes (juce::int64 n);
    juce::String stemOf (const juce::String& fname);
    juce::String extOf (const juce::String& fname);                       // with the dot, or ""
    bool isAudioName (const juce::String& fname);                         // the AUDIO_EXT list of the web UI
    double audioDuration (const juce::File&);                             // seconds, 0 when JUCE cannot read the header

    struct Ref { juce::String name; juce::int64 size = 0; juce::String folder; };   // folder: relative folder of the vault file (optional)

    struct PresetRec
    {
        juce::String id, name, folder;        // id = relative path of the file, folder = its relative folder ("" = root)
        juce::int64 saved = 0;
        std::map<int, double> params;
        std::map<juce::String, Ref> refs;     // slot key (wt0..wt5, sm0..sm5); absent = null
        juce::var lfo, frq;
    };

    struct LibRec
    {
        juce::String id;                      // "samples/name.wav" / "wavetables/name.wav" (same ids as the web UI)
        int kind = 1;                         // 0 wavetable, 1 sample (SoundMemory::Kind)
        juce::String folder;                  // relative folder inside the kind folder ("" = root)
        juce::String fname, label;
        juce::int64 size = 0, added = 0;
        double dur = 0;
    };

    // "Drums/Kicks" -> true; rejects "..", absolute paths and characters that are not allowed in a folder name
    bool safeRel (const juce::String& rel);
    juce::String joinRel (const juce::String& folder, const juce::String& name);        // "A/B" + "c" -> "A/B/c"
    juce::String parentRel (const juce::String& rel);                                    // "A/B" -> "A", "A" -> ""
    juce::String leafRel (const juce::String& rel);                                      // "A/B" -> "B"

    class Store
    {
    public:
        explicit Store (juce::File rootFolder) : root (std::move (rootFolder)) {}

        juce::File presetsDir() const { return root.getChildFile ("Presets"); }
        juce::File kindDir (int kind) const { return root.getChildFile (kind == 0 ? "Wavetables" : "Samples"); }
        juce::File fileFor (const LibRec& r) const { return kindDir (r.kind).getChildFile (joinRel (r.folder, r.fname)); }
        static juce::String areaOf (int kind) { return kind == 0 ? "wavetables" : "samples"; }

        // folders: a folder path is "presets", "presets/A/B", "samples/Drums", "wavetables" ...
        juce::File dirOf (const juce::String& folderPath) const;                           // invalid / unsafe paths give File()
        std::vector<juce::String> folders (const juce::String& area) const;                // every folder below the area (relative, sorted, nested ones included)
        juce::String folderCreate (const juce::String& parentPath, const juce::String& name);   // new folder path or ""
        juce::String folderRename (const juce::String& folderPath, const juce::String& newName);
        bool folderDelete (const juce::String& folderPath);                                 // the area folders themselves cannot be deleted
        int folderFileCount (const juce::String& folderPath) const;                         // files inside (recursive), for the "are you sure" text

        // presets
        std::vector<PresetRec> presetsList() const;                       // recursive, sorted by folder then name
        juce::String presetSave (const PresetRec&, const juce::String& prevId);   // new id (relative path) or "" on failure; the folder is rec.folder
        bool presetDelete (const juce::String& id);
        juce::String presetMove (const PresetRec&, const juce::String& destFolder);   // new id or ""
        static juce::String toJson (const PresetRec&);
        static bool fromJson (const juce::String& text, PresetRec& out);

        // vault
        std::vector<LibRec> libList (std::map<juce::String, double>& durCache) const;   // recursive
        juce::String uniqueName (int kind, const juce::String& folder, const juce::String& fname) const;
        juce::String libAdd (int kind, const juce::String& folder, const juce::File& src, const std::vector<LibRec>& existing, bool& duplicate);  // id or ""
        juce::String libRename (const LibRec&, const juce::String& newLabel);   // new id or ""
        juce::String libMove (const LibRec&, const juce::String& destFolderPath);   // to "samples/A" / "wavetables" ...: new id or ""
        bool libDelete (const LibRec&);

    private:
        juce::File root;
    };
}
