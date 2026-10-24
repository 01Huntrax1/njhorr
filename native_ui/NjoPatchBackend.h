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
            if (auto pp = lookup (num))
            {
                cache[num] = pp->currentValue;
                return pp->currentValue;
            }
            auto it = cache.find (num);
            return it != cache.end() ? it->second : 0.0f;
        }

        void setParam (int num, float v) override
        {
            if (auto pp = lookup (num))
            {
                pp->setValue (v, true, -1, 0);
                v = pp->currentValue;          // snapped / constrained by the patch
            }
            cache[num] = v;
            notifyParam (num, v);              // the UI listens for its own edits too (widgets, page layout, matrix ...)
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
        // the parameter objects are looked up once (string key + hash lookup) and then kept: the poll runs for every parameter the UI has read
        cmaj::PatchParameter* lookup (int num)
        {
            auto it = ptrs.find (num);
            if (it != ptrs.end()) return it->second.get();
            auto pp = patch.findParameter (id (num));
            if (! pp) return nullptr;
            return (ptrs[num] = std::move (pp)).get();
        }

        // host automation / preset changes reach the UI by polling the parameters it has read
        void timerCallback() override
        {
            // a reloaded patch (sample rate / buffer change) has new parameter objects: drop the kept pointers then
            if (auto sentinel = patch.findParameter (id (1000)))
            {
                if (sentinelPtr != sentinel.get()) { ptrs.clear(); sentinelPtr = sentinel.get(); }
            }
            else if (! ptrs.empty()) ptrs.clear();

            for (auto& [num, last] : cache)
                if (auto* pp = lookup (num))
                    if (pp->currentValue != last)
                    {
                        last = pp->currentValue;
                        notifyParam (num, last);
                    }
        }

        cmaj::Patch& patch;
        std::map<int, float> cache;
        std::unordered_map<int, cmaj::PatchParameterPtr> ptrs;
        const cmaj::PatchParameter* sentinelPtr = nullptr;
    };
}
