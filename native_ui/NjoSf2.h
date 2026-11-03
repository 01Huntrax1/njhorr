// SoundFont (.sf2) reader for the SoundFont source (source type 12): lists the presets of a file and turns one preset into the zone table + audio that the DSP bank
// (layout.py SF_*, event sfBankLoad) expects: 8 floats of preamble, kSfMaxZones records of kSfZf floats, then the mono audio of every zone's sample.
#pragma once
#include <juce_core/juce_core.h>
#include <vector>

namespace njo::sf2
{
    constexpr int kSfMaxZones = 64, kSfZf = 20, kSfHdr = 8 + kSfMaxZones * kSfZf, kSfAudio = 262144;
    // zone record fields (same order as layout.py SF_ZF)
    enum ZoneField { KeyLo, KeyHi, VelLo, VelHi, Start, Len, LoopS, LoopE, LoopMode, Root, TuneCents, SampleRate, AttenCb, Pan, AttackMs, HoldMs, DecayMs, SustainCb, ReleaseMs, ScaleTuning };

    struct PresetInfo { juce::String name; int bank = 0, program = 0; };

    struct Built
    {
        std::vector<float> data;      // preamble + zone table + audio
        juce::String name;            // the preset name
        juce::String note;            // "" or what had to be reduced (zones merged, samples decimated / shortened)
        int zones = 0, samples = 0;
    };

    class File
    {
    public:
        bool open (const juce::File&, juce::String& error);           // reads the preset / instrument / sample headers (not the audio)
        const std::vector<PresetInfo>& presets() const { return presetList; }
        bool build (int presetIndex, Built& out, juce::String& error) const;   // reads the audio of the preset's zones
        int defaultPreset() const;                                    // bank 0 program 0 (acoustic piano), otherwise the first

    private:
        struct Gen { int oper = 0; int amount = 0; };
        struct Bag { int gen = 0; };
        struct SampleHdr { juce::String name; juce::uint32 start = 0, end = 0, loopStart = 0, loopEnd = 0, rate = 44100; int pitch = 60, correction = 0, type = 1; };
        struct Zone { int g[64]; bool has[64]; };
        juce::File file; juce::int64 smplOffset = 0, smplSize = 0;
        std::vector<PresetInfo> presetList;
        std::vector<int> presetBag, instBag;                         // first bag of every preset / instrument (+ end marker)
        std::vector<Bag> pbag, ibag; std::vector<Gen> pgen, igen; std::vector<SampleHdr> shdr;
    };
}
