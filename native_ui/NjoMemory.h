// Sample / wavetable memory of the six slots: loading files (any format JUCE can read), keeping the audio for the
// displays and the preset, streaming it to the DSP banks and saving it with the plugin state.
#pragma once
#include "NjoCore.h"

namespace njo
{
    class SoundMemory : public juce::ChangeBroadcaster
    {
    public:
        enum Kind { Wavetable = 0, Sample = 1, FilterTable = 2, ShaperTable = 3, ImpulseResponse = 4, ModeEdit = 5, EqBands = 6, SoundFont = 7 };   // SoundFont: index = oscillator, data = zone table + audio of one preset (NjoSf2.h), stored as float32   // EqBands: index = global FX slot 0..29, 240 values (24 bands x 10, see NjoEq.h)   // ModeEdit: index = slot * 3 + set (Physical A / B / Resonator stage), 48 multipliers (16 modes x frequency, gain, decay)
        //   // impulse response: the index is the FX rack (0..2), up to 96000 samples (2 s) for the convolution reverb's User IR mode
        //   // the two tables: Wavefilter / Wavedistortion (512 points per frame, 64 frames max)
        struct Slot { juce::String name; juce::String libId; std::vector<float> data; mutable unsigned long long sig = 0; juce::String srcPath; int preset = 0; };   // srcPath / preset: the .sf2 file and its preset (SoundFont only)

        explicit SoundMemory (Backend&);                             // lives as long as the plugin instance (the editor window comes and goes)
        explicit SoundMemory (Ctx&);                                 // tests / standalone editor: the status line of the context
        std::function<void (const juce::String&)> onStatus;          // the editor sets it while it is open
        ~SoundMemory() override;

        const Slot* get (Kind, int osc) const;                       // nullptr when empty
        void load (Kind, int osc, const juce::File&, std::function<void (bool ok, const juce::String& message)> done = {}, int preset = -1);   // preset: SoundFont only (-1 = default)
        void set (Kind, int osc, const juce::String& name, const juce::String& libId, std::vector<float> data);   // already decoded audio
        void clear (Kind, int osc);
        // SoundFont source: the presets of the loaded file (empty when the file is gone) and switching to another one
        juce::StringArray soundFontPresets (int osc) const;
        void selectSoundFontPreset (int osc, int preset, std::function<void (bool ok, const juce::String& message)> done = {});
        void relabel (const juce::String& oldPath, const juce::String& newPath);   // a vault file / folder was renamed or moved: fix the stored ids
        void restore();                                              // sends what the DSP does not have yet (nothing when the sounds are already there)
        void reloadFromStored();                                     // the plugin state (or the patch) was replaced: decode the stored sounds again and bring the DSP up to date
        // lists of formats that load, for file choosers
        static juce::String fileWildcard();

    private:
        void status (const juce::String&);
    public:
        struct Impl; std::unique_ptr<Impl> impl;
    };
}
