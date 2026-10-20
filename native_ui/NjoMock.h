// In-memory backend for tests and screenshots.
#pragma once
#include "NjoBackend.h"
#include "NjoData.h"

namespace njo
{
    class MockBackend : public Backend
    {
    public:
        MockBackend()
        {
            for (auto& s : allSpecs()) values[s.num] = (float) s.init;
            values[oscId (0, oscKey ("level"))] = 0.8f;
            root = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("njohrr_mock_" + juce::String (juce::Random::getSystemRandom().nextInt64()));
        }

        float getParam (int num) override { auto it = values.find (num); return it == values.end() ? 0.0f : it->second; }
        void setParam (int num, float v) override { values[num] = v; notifyParam (num, v); }
        void sendEvent (const juce::String& ep, const juce::var& v) override { events.push_back ({ ep, v }); }
        juce::var getStored (const juce::String& k) override { auto it = stored.find (k); return it == stored.end() ? juce::var() : it->second; }
        void setStored (const juce::String& k, const juce::var& v) override { if (v.isVoid()) stored.erase (k); else stored[k] = v; }
        juce::File rootFolder() override { return root; }

        std::map<int, float> values;
        std::map<juce::String, juce::var> stored;
        struct Event { juce::String endpoint; juce::var value; };
        std::vector<Event> events;
        juce::File root;
    };
}
