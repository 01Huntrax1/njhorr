// STUB: replaced by the real OscPage implementation.
#include "../NjoPages.h"
namespace njo
{
    struct OscPage::Impl { int idx = 0; };
    OscPage::OscPage (Ctx& c, SoundMemory&, int o) : impl (new Impl) { impl->idx = o; juce::ignoreUnused (c); }
    OscPage::~OscPage() = default;
    void OscPage::paint (juce::Graphics& g) { theme::paintCard (g, getLocalBounds().toFloat()); g.setColour (theme::dim); g.drawText ("OscPage (stub)", getLocalBounds(), juce::Justification::centred); }
    void OscPage::resized() {}
}
