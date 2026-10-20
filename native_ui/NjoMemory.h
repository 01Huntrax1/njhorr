// Sample / wavetable memory of the six slots: loading files (any format JUCE can read), keeping the audio for the
// displays and the preset, streaming it to the DSP banks and saving it with the plugin state.
#pragma once
#include "NjoCore.h"

namespace njo
{
    class SoundMemory : public juce::ChangeBroadcaster
    {
    public:
        enum Kind { Wavetable = 0, Sample = 1 };
        struct Slot { juce::String name; juce::String libId; std::vector<float> data; };

        explicit SoundMemory (Ctx&);
        ~SoundMemory() override;

        const Slot* get (Kind, int osc) const;                       // nullptr when empty
        void load (Kind, int osc, const juce::File&, std::function<void (bool ok, const juce::String& message)> done = {});
        void set (Kind, int osc, const juce::String& name, const juce::String& libId, std::vector<float> data);   // already decoded audio
        void clear (Kind, int osc);
        void restore();                                              // after the editor opens: stored state -> DSP
        // lists of formats that load, for file choosers
        static juce::String fileWildcard();

        struct Impl; std::unique_ptr<Impl> impl;
    };
}
