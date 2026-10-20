// STUB: replaced by the real preset bar / bank / vault.
#include "NjoManager.h"
namespace njo
{
    struct ManagerBar::Impl {};
    ManagerBar::ManagerBar (Ctx&, SoundMemory&, juce::Component&) : impl (new Impl) {}
    ManagerBar::~ManagerBar() = default;
    void ManagerBar::paint (juce::Graphics& g) { g.setColour (theme::dim); g.setFont (theme::font (9.0f, true)); g.drawText ("PRESET   Init", getLocalBounds(), juce::Justification::centredLeft); }
    void ManagerBar::resized() {}
}
