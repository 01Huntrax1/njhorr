// The curves of the 10 Freq modulators: points {x 0..1 (time), y 0..1 (20 Hz .. 20 kHz on a log axis), c curve -1..1}, sent to the DSP
// as 256 point tables ("frqShapeLoad") and stored under "njo.frq" (same format as the JS UI: see frqCommit / applyFrq in patch/index.js).
#pragma once
#include "NjoCore.h"

namespace njo
{
    class FreqShapes
    {
    public:
        explicit FreqShapes (Ctx&);
        std::vector<LfoPoint>& points (int i);              // the curve (the built-in falling curve until it is edited)
        void commit (int i, bool final);                     // sends the table to the DSP; final: also persists
        juce::var toVar() const;                             // stored state and presets
        void fromVar (const juce::var&);                     // replaces all curves (void clears), sends the tables
        static std::vector<LfoPoint> defaultPoints();
        static std::vector<float> table (const std::vector<LfoPoint>&);   // 256 samples 0..1
        struct Impl; std::shared_ptr<Impl> impl;
    };
}
