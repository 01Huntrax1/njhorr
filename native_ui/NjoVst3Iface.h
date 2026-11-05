// What the UI needs from the VST3 host of the plugin (include/cmajor/helpers/NjoVst3Host.h). The UI only knows this interface, so the
// screenshot / test harness builds without the JUCE plugin hosting module. Slot 0 = instrument (OSC source "VST3"), slot 1 = effect (FX type "VST3").
#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

namespace njo
{
    struct Vst3Control
    {
        enum Slot { Instrument = 0, Effect = 1 };
        virtual ~Vst3Control() = default;

        virtual bool isAvailable() const { return true; }
        virtual juce::String name (int slot) const = 0;            // loaded plugin, empty when nothing is loaded
        virtual juce::String status (int slot) const = 0;          // "Loading ...", an error, or empty
        virtual juce::StringArray known (int slot) = 0;            // plugins found by the last scan (instruments for slot 0, effects for slot 1)
        virtual bool scanning() const { return false; }
        virtual void rescan() = 0;                                  // asynchronous; onChanged fires when it is done
        virtual void loadKnown (int slot, int index) = 0;           // index into known (slot)
        virtual void loadFile (int slot, const juce::File& vst3) = 0;
        virtual void unload (int slot) = 0;
        virtual bool hasEditor (int slot) const = 0;
        virtual void openEditor (int slot) = 0;
        virtual int  latencySamples (int /*slot*/) const { return 0; }

        std::function<void()> onChanged;                            // message thread: name / status / list changed
    };
}
