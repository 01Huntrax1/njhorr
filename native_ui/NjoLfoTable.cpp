#include "NjoLfoTable.h"
#include <cmath>

namespace njo
{
    struct LfoTables::Impl
    {
        Ctx* ctx = nullptr;
        std::vector<std::vector<float>> fr[10];
        bool mod[10] = {};
        double lastSend = 0;
    };

    static int lim (int i) { return juce::jlimit (0, 9, i); }

    std::vector<float> LfoTables::defaultFrame (int kind)
    {
        std::vector<float> d (points);
        for (int i = 0; i < points; ++i)
        {
            float p = (float) i / points;
            d[(size_t) i] = kind == 0 ? std::sin (6.2831853f * p) : kind == 1 ? 4.0f * std::abs (p - 0.5f) - 1.0f : kind == 2 ? 2.0f * p - 1.0f : kind == 3 ? (p < 0.5f ? 1.0f : -1.0f) : (p < 0.25f ? 1.0f : -1.0f);
        }
        return d;
    }

    static void defaults (std::vector<std::vector<float>>& f) { f.clear(); for (int k = 0; k < 5; ++k) f.push_back (LfoTables::defaultFrame (k)); }

    LfoTables::LfoTables (Ctx& c) : impl (new Impl)
    {
        impl->ctx = &c;
        for (auto& f : impl->fr) defaults (f);
        fromVar (c.be.getStored ("njo.lfowt"));
    }

    int LfoTables::count (int l) const { return (int) impl->fr[lim (l)].size(); }
    std::vector<float>& LfoTables::frame (int l, int f) { auto& v = impl->fr[lim (l)]; return v[(size_t) juce::jlimit (0, (int) v.size() - 1, f)]; }
    bool LfoTables::modified (int l) const { return impl->mod[lim (l)]; }

    void LfoTables::setCount (int l, int n)
    {
        l = lim (l); n = juce::jlimit (1, maxFrames, n); auto& v = impl->fr[l];
        while ((int) v.size() > n) v.pop_back();
        while ((int) v.size() < n) v.push_back (v.back());
        impl->mod[l] = true;
    }

    void LfoTables::insertCopy (int l, int after)
    {
        l = lim (l); auto& v = impl->fr[l];
        if ((int) v.size() >= maxFrames) return;
        auto c = v[(size_t) juce::jlimit (0, (int) v.size() - 1, after)];
        v.insert (v.begin() + juce::jlimit (0, (int) v.size() - 1, after) + 1, c);
        impl->mod[l] = true;
    }

    void LfoTables::erase (int l, int f)
    {
        l = lim (l); auto& v = impl->fr[l];
        if (v.size() <= 1) return;
        v.erase (v.begin() + juce::jlimit (0, (int) v.size() - 1, f));
        impl->mod[l] = true;
    }

    void LfoTables::reset (int l)
    {
        l = lim (l); defaults (impl->fr[l]); impl->mod[l] = false;
        commitAll (l);
        impl->mod[l] = false;
        impl->ctx->be.setStored ("njo.lfowt", toVar());
    }

    static void sendFrame (LfoTables& t, Ctx& c, int l, int f)
    {
        juce::Array<juce::var> d;
        for (float v : t.frame (l, f)) d.add ((double) v);
        auto* o = new juce::DynamicObject();
        o->setProperty ("lfo", l); o->setProperty ("frame", f); o->setProperty ("frames", t.count (l)); o->setProperty ("data", juce::var (d));
        c.be.sendEvent ("lfoTableLoad", juce::var (o));
    }

    void LfoTables::commitFrame (int l, int f, bool final)
    {
        l = lim (l); impl->mod[l] = true;
        double now = juce::Time::getMillisecondCounterHiRes();
        if (final || now - impl->lastSend > 40.0) { impl->lastSend = now; sendFrame (*this, *impl->ctx, l, f); }
        if (final) impl->ctx->be.setStored ("njo.lfowt", toVar());
    }

    void LfoTables::commitAll (int l)
    {
        l = lim (l); impl->mod[l] = true;
        for (int f = 0; f < count (l); ++f) sendFrame (*this, *impl->ctx, l, f);
        impl->ctx->be.setStored ("njo.lfowt", toVar());
    }

    void LfoTables::sendAll()
    {
        for (int l = 0; l < 10; ++l) if (impl->mod[l]) for (int f = 0; f < count (l); ++f) sendFrame (*this, *impl->ctx, l, f);
    }

    juce::var LfoTables::toVar() const
    {
        juce::Array<juce::var> out;
        for (int l = 0; l < 10; ++l)
        {
            if (! impl->mod[l]) { out.add (juce::var()); continue; }
            juce::Array<juce::var> frames;
            for (auto& f : impl->fr[l])
            {
                std::vector<juce::int16> q (points);
                for (int i = 0; i < points; ++i) q[(size_t) i] = (juce::int16) juce::roundToInt (juce::jlimit (-1.0f, 1.0f, f[(size_t) i]) * 32000.0f);
                frames.add (juce::Base64::toBase64 (q.data(), q.size() * sizeof (juce::int16)));
            }
            out.add (juce::var (frames));
        }
        return juce::var (out);
    }

    void LfoTables::fromVar (const juce::var& v)
    {
        for (int l = 0; l < 10; ++l)
        {
            defaults (impl->fr[l]); impl->mod[l] = false;
            auto* arr = v.isArray() ? v[l].getArray() : nullptr;
            if (arr == nullptr || arr->isEmpty()) continue;
            std::vector<std::vector<float>> fs;
            for (auto& s : *arr)
            {
                juce::MemoryOutputStream mo; if (! juce::Base64::convertFromBase64 (mo, s.toString()) || mo.getDataSize() != (size_t) points * sizeof (juce::int16)) { fs.clear(); break; }
                auto* q = static_cast<const juce::int16*> (mo.getData()); std::vector<float> d (points);
                for (int i = 0; i < points; ++i) d[(size_t) i] = (float) q[i] / 32000.0f;
                fs.push_back (std::move (d)); if ((int) fs.size() >= maxFrames) break;
            }
            if (fs.empty()) continue;
            impl->fr[l] = std::move (fs); impl->mod[l] = true;
        }
        sendAll();
    }
}
