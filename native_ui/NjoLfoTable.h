// The wavetables of the 10 LFOs (wave "Table"): up to 16 frames of 256 points, sent to the DSP frame by frame (event lfoTableLoad) and stored
// with the plugin state under "njo.lfowt" (a frame = 256 int16 values as base64). Untouched LFOs keep the default table of the DSP
// (sine, triangle, saw up, square, pulse 25 %) and are not stored.
#pragma once
#include "NjoCore.h"

namespace njo
{
    class LfoTables
    {
    public:
        static constexpr int maxFrames = 16, points = 256;
        explicit LfoTables (Ctx&);
        int  count (int lfo) const;
        std::vector<float>& frame (int lfo, int f);                  // 256 values -1..1
        bool modified (int lfo) const;
        void setCount (int lfo, int n);                              // keeps the first n frames (new frames are copies of the last one)
        void insertCopy (int lfo, int after);                        // duplicates frame `after` behind itself
        void erase (int lfo, int f);
        void reset (int lfo);                                        // back to the default table of the DSP
        void commitFrame (int lfo, int f, bool final);               // sends one frame (throttled while dragging), final: also stores
        void commitAll (int lfo);                                    // sends every frame (after add / delete / tools) and stores
        void sendAll();
        juce::var toVar() const;
        void fromVar (const juce::var&);
        static std::vector<float> defaultFrame (int kind);           // 0 sine, 1 triangle, 2 saw up, 3 square, 4 pulse 25 %
        struct Impl; std::shared_ptr<Impl> impl;
    };
}
