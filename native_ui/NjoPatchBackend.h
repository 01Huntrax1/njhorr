// Backend implementation over a cmaj::Patch (used by the plugin editor). Header only, included from the Cmajor plugin header.
#pragma once
#include "NjoBackend.h"

namespace njo
{
    class PatchBackend : public Backend, private juce::Timer
    {
    public:
        explicit PatchBackend (cmaj::Patch& p) : patch (p) { startTimerHz (30); }
        ~PatchBackend() override { stopTimer(); }

        float getParam (int num) override
        {
            if (auto pp = find (num))
            {
                cache[num] = pp->currentValue;
                return pp->currentValue;
            }
            return cache.count (num) ? cache[num] : 0.0f;
        }

        void setParam (int num, float v) override
        {
            cache[num] = v;
            if (auto pp = find (num))
                pp->setValue (v, true, -1, 0);
        }

        void beginGesture (int num) override { patch.sendGestureStart (id (num)); }
        void endGesture (int num) override   { patch.sendGestureEnd (id (num)); }

        void sendEvent (const juce::String& endpoint, const juce::var& value) override
        {
            try
            {
                auto v = choc::json::parse (juce::JSON::toString (value, true).toStdString());
                patch.sendEventOrValueToPatch (cmaj::EndpointID::create (endpoint.toStdString()), v, -1, 0);
            }
            catch (...) {}
        }

        juce::var getStored (const juce::String& key) override
        {
            auto& all = patch.getStoredStateValues();
            auto it = all.find (key.toStdString());
            if (it == all.end() || ! it->second.isObject() && ! it->second.isArray() && ! it->second.isString()
                                 && ! it->second.isFloat() && ! it->second.isInt() && ! it->second.isBool())
                return {};
            return juce::JSON::parse (juce::String (choc::json::toString (it->second)));
        }

        void setStored (const juce::String& key, const juce::var& value) override
        {
            try
            {
                if (value.isVoid())
                    patch.setStoredStateValue (key.toStdString(), choc::value::Value());
                else
                    patch.setStoredStateValue (key.toStdString(), choc::json::parse (juce::JSON::toString (value, true).toStdString()));
            }
            catch (...) {}
        }

    private:
        static cmaj::EndpointID id (int num) { return cmaj::EndpointID::create ("param" + std::to_string (num)); }
        cmaj::PatchParameterPtr find (int num) const { return patch.findParameter (id (num)); }

        // host automation / preset changes reach the UI by polling the parameters it has read
        void timerCallback() override
        {
            for (auto& [num, last] : cache)
                if (auto pp = find (num))
                    if (pp->currentValue != last)
                    {
                        last = pp->currentValue;
                        notifyParam (num, last);
                    }
        }

        cmaj::Patch& patch;
        std::map<int, float> cache;
    };
}
