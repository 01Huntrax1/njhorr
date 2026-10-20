// STUB: replaced by the real MatrixPanel implementation.
#include "../NjoPages.h"
namespace njo
{
    struct MatrixPanel::Impl { int idx = 0; };
    MatrixPanel::MatrixPanel (Ctx& c) : impl (new Impl) {  juce::ignoreUnused (c); }
    MatrixPanel::~MatrixPanel() = default;
    void MatrixPanel::paint (juce::Graphics& g) { theme::paintCard (g, getLocalBounds().toFloat()); g.setColour (theme::dim); g.drawText ("MatrixPanel (stub)", getLocalBounds(), juce::Justification::centred); }
    void MatrixPanel::resized() {}
}
namespace njo { void showModPopup (Ctx&, juce::Component&, int) {} }
