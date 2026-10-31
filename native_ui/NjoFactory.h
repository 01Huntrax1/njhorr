// Factory wavetables: generated in code (port of tools/wavetables/build_factory.py) and written once into <root>/Wavetables/Factory.
#pragma once
#include <juce_core/juce_core.h>
#include <vector>

namespace njo
{
    struct FactoryTable { juce::String name; std::vector<float> samples; };   // mono, frames of 2048 samples, each frame normalized to a peak of 0.97

    std::vector<FactoryTable> makeFactoryWavetables();

    // Writes the 16 bit WAV files into <root>/Wavetables/Factory the first time (a marker file remembers it, so files the user
    // deleted do not come back). Returns the number of files written.
    int installFactoryWavetables (const juce::File& root);
}
