// What the UI needs from the plugin. The editor talks only to this interface, so it can run against the Cmajor patch
// (NjoPatchBackend, in the plugin) or against an in-memory mock (the screenshot / test harness).
#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

namespace njo
{
    class Backend
    {
    public:
        virtual ~Backend() = default;

        // ---- parameters, addressed by their parameter number (endpoint "param<N>") ----
        virtual float getParam (int num) = 0;
        virtual void  setParam (int num, float value) = 0;          // a user edit: reaches the DSP and the host
        virtual void  beginGesture (int /*num*/) {}
        virtual void  endGesture (int /*num*/) {}

        // ---- events to the DSP: "lfoShapeLoad" { lfo, data[] }, "wtBankLoad" / "smpBankLoad" { bank, offset, count, total, data[] } ----
        virtual void  sendEvent (const juce::String& endpoint, const juce::var& value) = 0;

        // ---- per instance stored state (saved with the project, key -> JSON-like var) ----
        virtual juce::var getStored (const juce::String& key) = 0;
        virtual void      setStored (const juce::String& key, const juce::var& value) = 0;   // void var removes the key

        // ---- the folder with Presets / Samples / Wavetables (Documents/Njohrr by default) ----
        virtual juce::File rootFolder() { return juce::File::getSpecialLocation (juce::File::userDocumentsDirectory).getChildFile ("Njohrr"); }

        // ---- identity of the loaded DSP: changes whenever the patch is (re)loaded and the DSP banks start empty again ----
        virtual unsigned long long dspGeneration() { return 1; }

        // ---- host info for the LCD / meters ----
        virtual float getOutputLevel() { return 0.0f; }

        // ---- playhead of the step sequencers: the DSP reports "sequencer * 16 + step" (output event seqPos); -1 = unknown ----
        int seqStepPos[10] = { -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 };
        void setSeqPos (int v) { int m = v / 16; if (v >= 0 && m < 10) seqStepPos[m] = v % 16; }

        // ---- Inspirator: the DSP streams its generated pattern (output event insDump, see tools/mod/build_inspirator.py) and the playhead step (insPos) ----
        struct InsPattern
        {
            int count = 0, mode = 0, numBars = 4, stepsBar = 16, beatSteps = 4, transpose = 0, pushMask = 0, rate = 1;
            int cInfo[8] = { 0, 0, 0, 0, 0, 0, 0, 0 }, dFill[12] = { 0 };
            std::vector<int> grid, pitch, off, len, vel;
        };
        InsPattern ins;                 // the complete pattern
        unsigned insVersion = 0;        // counts the completed patterns (the editor repaints when it changes)
        int insPlayStep = -1;           // step inside the loop (0 .. bars * steps - 1), -1 = stopped
        void insPush (float f)
        {
            const int v = (int) (f < 0.0f ? f - 0.5f : f + 0.5f);
            if (v < 0) { stage = InsPattern(); insExpect = -v - 1; insIdx = 1; stage.grid.assign ((size_t) insExpect, 0); stage.pitch = stage.off = stage.len = stage.vel = stage.grid; return; }
            if (insIdx < 1) return;
            const int i = insIdx++;
            if (i == 1) stage.mode = v;
            else if (i == 2) { stage.numBars = v & 63; stage.stepsBar = (v >> 6) & 63; stage.beatSteps = v >> 12; }
            else if (i < 11) stage.cInfo[i - 3] = v;
            else if (i == 11) { stage.transpose = (v & 127) - 64; stage.pushMask = (v >> 7) & 255; stage.rate = v >> 15; }
            else if (i < 24) stage.dFill[i - 12] = v;
            else
            {
                const int k = i - 24, n = k / 2;
                if (n < insExpect)
                {
                    if ((k % 2) == 0) { stage.grid[(size_t) n] = v / 128; stage.pitch[(size_t) n] = v % 128; }
                    else { stage.vel[(size_t) n] = v % 128; const int r = v / 128; stage.len[(size_t) n] = r % 1024; stage.off[(size_t) n] = r / 1024 - 64; }
                }
            }
            if (insIdx >= 24 + 2 * insExpect) { stage.count = insExpect; ins = stage; ++insVersion; insIdx = 0; }
        }

        struct Listener
        {
            virtual ~Listener() = default;
            virtual void paramChanged (int num, float value) = 0;   // from the host, automation, presets or the UI itself
        };
        void addListener (Listener* l)    { listeners.add (l); }
        void removeListener (Listener* l) { listeners.remove (l); }

        // implementations call this when a value changed (on the message thread)
        void notifyParam (int num, float v) { listeners.call ([&] (Listener& l) { l.paramChanged (num, v); }); }

    private:
        InsPattern stage; int insExpect = 0, insIdx = 0;
        juce::ListenerList<Listener> listeners;
    };
}
