// STUB: replaced by the real ModEditors implementation.
#include "../NjoPages.h"
namespace njo
{
    struct ModEditors::Impl { int idx = 0; };
    ModEditors::ModEditors (Ctx& c) : impl (new Impl) {  juce::ignoreUnused (c); }
    ModEditors::~ModEditors() = default;
    void ModEditors::paint (juce::Graphics& g) { theme::paintCard (g, getLocalBounds().toFloat()); g.setColour (theme::dim); g.drawText ("ModEditors (stub)", getLocalBounds(), juce::Justification::centred); }
    void ModEditors::resized() {}
}
