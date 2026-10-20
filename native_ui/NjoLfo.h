// The drawn LFO shapes (10 LFOs): points {x 0..1, y -1..1, c curve -1..1}, sent to the DSP as 256 point tables and stored with the
// plugin state under "njo.lfo" (same format as the JS UI: see lfoPersist / lfoLoad in patch/index.js).
#pragma once
#include "NjoCore.h"

namespace njo
{
    class LfoShapes
    {
    public:
        explicit LfoShapes (Ctx&);
        // the shape of LFO i as points (a built-in wave is converted to points the first time it is edited)
        std::vector<LfoPoint>& points (int lfo);
        bool isDrawn (int lfo) const;                    // has an edited / loaded point list
        void commit (int lfo, bool final);              // sets wave = Drawn, sends the table to the DSP; final: also persists
        void sendAll();                                  // table of every drawn LFO to the DSP (editor start, preset load)
        juce::var toVar() const;                         // for the stored state and presets
        void fromVar (const juce::var&);                 // replaces all shapes (null / void clears), sends tables
        static std::vector<float> table (const std::vector<LfoPoint>&);   // 256 samples, identical to lfoTableFromPts
        static std::vector<LfoPoint> builtin (int wave);                  // lfoBuiltinPts
        static float sampleAt (const std::vector<LfoPoint>&, float phase);
        static float curve (float y0, float y1, float c, float t);
        struct Impl; std::shared_ptr<Impl> impl;
    };
}
