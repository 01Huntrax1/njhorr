// STUB: replaced by the real FxPage implementation.
#include "../NjoPages.h"
namespace njo
{
    struct FxPage::Impl { int idx = 0; };
    FxPage::FxPage (Ctx& c) : impl (new Impl) {  juce::ignoreUnused (c); }
    FxPage::~FxPage() = default;
    void FxPage::paint (juce::Graphics& g) { theme::paintCard (g, getLocalBounds().toFloat()); g.setColour (theme::dim); g.drawText ("FxPage (stub)", getLocalBounds(), juce::Justification::centred); }
    void FxPage::resized() {}
}
