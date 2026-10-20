// STUB: replaced by the real GlobalPage implementation.
#include "../NjoPages.h"
namespace njo
{
    struct GlobalPage::Impl { int idx = 0; };
    GlobalPage::GlobalPage (Ctx& c) : impl (new Impl) {  juce::ignoreUnused (c); }
    GlobalPage::~GlobalPage() = default;
    void GlobalPage::paint (juce::Graphics& g) { theme::paintCard (g, getLocalBounds().toFloat()); g.setColour (theme::dim); g.drawText ("GlobalPage (stub)", getLocalBounds(), juce::Justification::centred); }
    void GlobalPage::resized() {}
}
