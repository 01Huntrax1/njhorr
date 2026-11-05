// Panel of the VST3 host: the loaded plugin, LOAD (list of the scanned plugins, browse, rescan), EDIT (plugin window) and UNLOAD.
// Used on the OSC page (source "VST3", instrument) and on the effects page (effect type "VST3").
#pragma once
#include "../NjoCore.h"
#include "../NjoVst3Iface.h"

namespace njo
{
    class Vst3Panel : public juce::Component
    {
    public:
        Vst3Panel (Ctx&, int slot);
        ~Vst3Panel() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        void refresh();
    private:
        struct Impl; std::unique_ptr<Impl> impl;
    };
}
