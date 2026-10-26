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
        juce::ListenerList<Listener> listeners;
    };
}
