// STUB: replaced by the real sound memory.
#include "NjoMemory.h"
namespace njo
{
    struct SoundMemory::Impl {};
    SoundMemory::SoundMemory (Ctx&) : impl (new Impl) {}
    SoundMemory::~SoundMemory() = default;
    const SoundMemory::Slot* SoundMemory::get (Kind, int) const { return nullptr; }
    void SoundMemory::load (Kind, int, const juce::File&, std::function<void (bool, const juce::String&)> d) { if (d) d (false, "not implemented"); }
    void SoundMemory::set (Kind, int, const juce::String&, const juce::String&, std::vector<float>) {}
    void SoundMemory::clear (Kind, int) {}
    void SoundMemory::restore() {}
    juce::String SoundMemory::fileWildcard() { return "*.wav;*.aif;*.aiff;*.flac;*.mp3;*.ogg"; }
}
