// File side of the Preset Bank / Sound Vault: <root>/{Presets,Samples,Wavetables}.
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

    struct Ref { juce::String name; juce::int64 size = 0; };

    struct PresetRec
    {
        juce::String id, name;
        juce::int64 saved = 0;
        std::map<int, double> params;
        std::map<juce::String, Ref> refs;     // slot key (wt0..wt5, sm0..sm5); absent = null
        juce::var lfo;
    };

    struct LibRec
    {
        juce::String id;                      // "samples/name.wav" / "wavetables/name.wav" (same ids as the web UI)
        int kind = 1;                         // 0 wavetable, 1 sample (SoundMemory::Kind)
        juce::String fname, label;
        juce::int64 size = 0, added = 0;
        double dur = 0;
    };

    class Store
    {
    public:
        explicit Store (juce::File rootFolder) : root (std::move (rootFolder)) {}

        juce::File presetsDir() const { return root.getChildFile ("Presets"); }
        juce::File kindDir (int kind) const { return root.getChildFile (kind == 0 ? "Wavetables" : "Samples"); }
        juce::File fileFor (const LibRec& r) const { return kindDir (r.kind).getChildFile (r.fname); }

        // presets
        std::vector<PresetRec> presetsList() const;                       // sorted by name
        juce::String presetSave (const PresetRec&, const juce::String& prevId);   // new id (file name) or "" on failure
        bool presetDelete (const juce::String& id);
        static juce::String toJson (const PresetRec&);
        static bool fromJson (const juce::String& text, PresetRec& out);

        // vault
        std::vector<LibRec> libList (std::map<juce::String, double>& durCache) const;
        juce::String uniqueName (int kind, const juce::String& fname) const;
        juce::String libAdd (int kind, const juce::File& src, const std::vector<LibRec>& existing, bool& duplicate);  // id or ""
        juce::String libRename (const LibRec&, const juce::String& newLabel);   // new id or ""
        juce::String libMoveKind (const LibRec&);                               // new id or ""
        bool libDelete (const LibRec&);

    private:
        juce::File root;
    };
}
