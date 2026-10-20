// The preset bar (previous / next / name / SAVE / BANK / VAULT) and its overlays (Preset Bank, Sound Vault).
#pragma once
#include "NjoCore.h"
#include "NjoMemory.h"

namespace njo
{
    class ManagerBar : public juce::Component
    {
    public:
        // overlayHost: the component the Bank / Vault overlays are added to (covers the whole editor content)
        ManagerBar (Ctx&, SoundMemory&, juce::Component& overlayHost);
        ~ManagerBar() override;
        void paint (juce::Graphics&) override;
        void resized() override;
        struct Impl; std::unique_ptr<Impl> impl;
    };
}
