#include "NjoCore.h"

namespace njo
{
    Ctx::Ctx (Backend& b) : be (b)
    {
        for (auto& r : fxRacks())
            for (int sl = 0; sl < 10; ++sl)
            {
                int rk = (int) (&r - &fxRacks()[0]);
                fxTypes[rk * 10 + sl] = juce::roundToInt (be.getParam (r.id + sl * 10));
            }
        be.addListener (this);
    }

    Ctx::~Ctx() { be.removeListener (this); }

    void Ctx::set (int num, float v)
    {
        if (auto* s = findSpec (num)) v = juce::jlimit ((float) s->min, (float) s->max, v);
        be.setParam (num, v);
    }

    void Ctx::paramChanged (int num, float v)
    {
        auto loc = fxLocate (num);
        if (loc.valid && loc.ord < 0 && loc.off == 0) fxTypes[loc.g] = juce::roundToInt (v);
        listeners.call ([&] (Listener& l) { l.paramChanged (num, v); });
    }

    void Ctx::touchAll()
    {
        for (auto& r : fxRacks())
            for (int sl = 0; sl < 10; ++sl)
                fxTypes[(int) (&r - &fxRacks()[0]) * 10 + sl] = juce::roundToInt (be.getParam (r.id + sl * 10));
        for (auto& s : allSpecs()) { float v = be.getParam (s.num); listeners.call ([&] (Listener& l) { l.paramChanged (s.num, v); }); }
    }

    std::vector<ModSlot> Ctx::modSlots() const
    {
        std::vector<ModSlot> out;
        for (int s = 0; s < MOD_SLOTS; ++s)
            out.push_back ({ s, juce::roundToInt (get (slotBase (s))), juce::roundToInt (get (slotBase (s) + 1)), get (slotBase (s) + 2) });
        return out;
    }

    std::vector<ModSlot> Ctx::modsFor (int dst) const
    {
        std::vector<ModSlot> out;
        for (auto& m : modSlots()) if (m.src > 0 && m.dst == dst) out.push_back (m);
        return out;
    }

    int Ctx::modAssign (int src, int dst, float amt)
    {
        auto slots = modSlots();
        const ModSlot* hit = nullptr;
        for (auto& m : slots) if (m.src == src && m.dst == dst) { hit = &m; break; }
        if (! hit) for (auto& m : slots) if (m.src == 0 || m.dst == 0) { hit = &m; break; }
        if (! hit) return -1;
        int s = hit->s;
        if (hit->src != src || hit->dst != dst) { set (slotBase (s), (float) src); set (slotBase (s) + 1, (float) dst); set (slotBase (s) + 2, amt); }
        else set (slotBase (s) + 2, amt);
        return s;
    }

    void Ctx::modClear (int s) { set (slotBase (s) + 2, 0); set (slotBase (s), 0); set (slotBase (s) + 1, 0); }
}
