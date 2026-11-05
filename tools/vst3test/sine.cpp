#include <juce_audio_processors/juce_audio_processors.h>
struct P : juce::AudioProcessor
{
    double sr = 44100, ph = 0; bool on = false;
    P() : AudioProcessor (BusesProperties().withOutput ("out", juce::AudioChannelSet::stereo())) {}
    const juce::String getName() const override { return "TestSine"; }
    void prepareToPlay (double r, int) override { sr = r; }
    void releaseResources() override {}
    void processBlock (juce::AudioBuffer<float>& b, juce::MidiBuffer& m) override
    {
        for (auto md : m) { auto msg = md.getMessage(); if (msg.isNoteOn()) on = true; if (msg.isNoteOff()) on = false; }
        for (int i = 0; i < b.getNumSamples(); ++i)
        {
            float v = on ? (float) (0.5 * std::sin (ph)) : 0.0f; ph += 2 * juce::MathConstants<double>::pi * 440.0 / sr;
            for (int c = 0; c < b.getNumChannels(); ++c) b.setSample (c, i, v);
        }
    }
    juce::AudioProcessorEditor* createEditor() override { return nullptr; }
    bool hasEditor() const override { return false; }
    bool acceptsMidi() const override { return true; } bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0; }
    int getNumPrograms() override { return 1; } int getCurrentProgram() override { return 0; } void setCurrentProgram (int) override {}
    const juce::String getProgramName (int) override { return {}; } void changeProgramName (int, const juce::String&) override {}
    void getStateInformation (juce::MemoryBlock& d) override { d.append ("sine", 4); } void setStateInformation (const void*, int) override {}
};
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new P(); }
