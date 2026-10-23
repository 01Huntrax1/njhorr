#include "NjoFreq.h"
#include "NjoLfo.h"
#include <cmath>

namespace njo
{
    struct FreqShapes::Impl
    {
        Ctx* ctx = nullptr;
        std::vector<LfoPoint> pts[10];
        bool has[10] = {};
        double lastSend = 0;
    };

    static int lim (int i) { return juce::jlimit (0, 9, i); }

    FreqShapes::FreqShapes (Ctx& c) : impl (new Impl)
    {
        impl->ctx = &c;
        fromVar (c.be.getStored ("njo.frq"));
    }

    std::vector<LfoPoint> FreqShapes::defaultPoints()
    {
        const float y[5] = { 1.0f, 0.5625f, 0.25f, 0.0625f, 0.0f };
        std::vector<LfoPoint> p;
        for (int k = 0; k < 5; ++k) p.push_back ({ k / 4.0f, y[k], 0.0f });
        return p;
    }

    std::vector<LfoPoint>& FreqShapes::points (int i)
    {
        i = lim (i);
        if (! impl->has[i]) { impl->pts[i] = defaultPoints(); impl->has[i] = true; }
        return impl->pts[i];
    }

    std::vector<float> FreqShapes::table (const std::vector<LfoPoint>& p)
    {
        auto t = LfoShapes::table (p);
        for (auto& v : t) v = juce::jlimit (0.0f, 1.0f, v);
        return t;
    }

    static void sendTable (Ctx& c, int i, const std::vector<float>& t)
    {
        juce::Array<juce::var> d;
        for (float v : t) d.add ((double) v);
        auto* o = new juce::DynamicObject();
        o->setProperty ("lfo", i);
        o->setProperty ("data", juce::var (d));
        c.be.sendEvent ("frqShapeLoad", juce::var (o));
    }

    void FreqShapes::commit (int i, bool final)
    {
        i = lim (i);
        double now = juce::Time::getMillisecondCounterHiRes();
        if (final || now - impl->lastSend > 50.0)
        {
            impl->lastSend = now;
            sendTable (*impl->ctx, i, table (points (i)));
        }
        if (final) impl->ctx->be.setStored ("njo.frq", toVar());
    }

    static double rnd (double v, double k) { return std::floor (v * k + 0.5) / k; }

    juce::var FreqShapes::toVar() const
    {
        juce::Array<juce::var> out;
        for (int i = 0; i < 10; ++i)
        {
            if (! impl->has[i]) { out.add (juce::var()); continue; }
            juce::Array<juce::var> p;
            for (auto& q : impl->pts[i])
            {
                auto* o = new juce::DynamicObject();
                o->setProperty ("x", rnd (q.x, 1e4)); o->setProperty ("y", rnd (q.y, 1e4)); o->setProperty ("c", rnd (q.c, 1e3));
                p.add (juce::var (o));
            }
            out.add (juce::var (p));
        }
        return juce::var (out);
    }

    void FreqShapes::fromVar (const juce::var& v)
    {
        for (int i = 0; i < 10; ++i)
        {
            impl->pts[i].clear(); impl->has[i] = false;
            auto* arr = v.isArray() ? v[i].getArray() : nullptr;
            if (arr != nullptr && arr->size() >= 2)
            {
                std::vector<LfoPoint> p; bool ok = true;
                for (auto& q : *arr)
                {
                    if (! q.isObject() || ! (q["x"].isDouble() || q["x"].isInt()) || ! (q["y"].isDouble() || q["y"].isInt())) { ok = false; break; }
                    p.push_back ({ juce::jlimit (0.0f, 1.0f, (float) (double) q["x"]), juce::jlimit (0.0f, 1.0f, (float) (double) q["y"]), juce::jlimit (-1.0f, 1.0f, (float) (double) q["c"]) });
                }
                if (ok) { impl->pts[i] = std::move (p); impl->has[i] = true; }
            }
            sendTable (*impl->ctx, i, table (impl->has[i] ? impl->pts[i] : defaultPoints()));
        }
    }
}
