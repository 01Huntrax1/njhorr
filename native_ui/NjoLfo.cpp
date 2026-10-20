// STUB: replaced by the real LFO shape store.
#include "NjoLfo.h"
namespace njo
{
    struct LfoShapes::Impl { std::vector<LfoPoint> pts[10]; };
    LfoShapes::LfoShapes (Ctx&) : impl (new Impl) {}
    std::vector<LfoPoint>& LfoShapes::points (int i) { return impl->pts[juce::jlimit (0, 9, i)]; }
    bool LfoShapes::isDrawn (int) const { return false; }
    void LfoShapes::commit (int, bool) {}
    void LfoShapes::sendAll() {}
    juce::var LfoShapes::toVar() const { return {}; }
    void LfoShapes::fromVar (const juce::var&) {}
    std::vector<float> LfoShapes::table (const std::vector<LfoPoint>&) { return std::vector<float> (256, 0.0f); }
    std::vector<LfoPoint> LfoShapes::builtin (int) { return {}; }
    float LfoShapes::sampleAt (const std::vector<LfoPoint>&, float) { return 0; }
    float LfoShapes::curve (float, float, float, float) { return 0; }
}
