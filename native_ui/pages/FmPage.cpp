// STUB: replaced by the real FmPage implementation.
#include "../NjoPages.h"
namespace njo
{
    struct FmPage::Impl { int idx = 0; };
    FmPage::FmPage (Ctx& c) : impl (new Impl) {  juce::ignoreUnused (c); }
    FmPage::~FmPage() = default;
    void FmPage::paint (juce::Graphics& g) { theme::paintCard (g, getLocalBounds().toFloat()); g.setColour (theme::dim); g.drawText ("FmPage (stub)", getLocalBounds(), juce::Justification::centred); }
    void FmPage::resized() {}
}
namespace njo { void FmPage::setOnOpenOsc (std::function<void (int)>) {} }
